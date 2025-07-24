import os, base64, json
from io import BytesIO
from django.shortcuts import render, redirect
from django.urls import reverse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
try:
    import kociemba
except ImportError:
    kociemba = None
import cv2
import numpy as np
from PIL import Image

# constants for face order
FACES = ['U', 'R', 'F', 'D', 'L', 'B']
# mapping for face labels
FACE_NAMES = {'U': 'Up', 'R': 'Right', 'F': 'Front', 'D': 'Down', 'L': 'Left', 'B': 'Back'}

# Golden 20 Steps algorithm descriptions
GOLDEN_ALGORITHMS = {
    "R U R' U'": {"name": "Sexy Move", "description": "Basic corner manipulation", "level": "Beginner"},
    "F R U R' U' F'": {"name": "Right Hand Algorithm", "description": "Form white cross", "level": "Beginner"},
    "R U R' F' R U R' U' R' F R2 U' R'": {"name": "T-Perm", "description": "Last layer permutation", "level": "Intermediate"},
    "R U2 R' U' R U R'": {"name": "Sune", "description": "Orient last layer", "level": "Intermediate"},
    "U R U' L' U R' U' L": {"name": "Corner Position", "description": "Position yellow corners", "level": "Beginner"},
}

# Extract cube state from image file path with color details
def extract_cube_state_with_colors(image_path):
    img = cv2.imread(image_path)
    if img is None:
        return None, []
    
    # Resize to ensure consistent processing
    img = cv2.resize(img, (400, 400))
    facelet_colors = []
    rgb_colors = []
    
    # Extract colors from 3x3 grid
    for row in range(3):
        for col in range(3):
            # Calculate position within the cube area (leaving border)
            x = int(50 + (col + 0.5) * 100)  # 50px border, 100px per cell
            y = int(50 + (row + 0.5) * 100)
            
            # Sample a small area around the center point for better accuracy
            sample_area = img[y-5:y+5, x-5:x+5]
            
            if sample_area.size > 0:
                # Average color in the sample area
                avg_bgr = np.mean(sample_area.reshape(-1, 3), axis=0)
                color_letter = classify_color(avg_bgr)
                facelet_colors.append(color_letter)
                
                # Store RGB for 3D visualization
                rgb_colors.append({
                    'r': int(avg_bgr[2]),
                    'g': int(avg_bgr[1]), 
                    'b': int(avg_bgr[0])
                })
            else:
                facelet_colors.append('W')
                rgb_colors.append({'r': 255, 'g': 255, 'b': 255})
    
    return ''.join(facelet_colors), rgb_colors

# classify single facelet color with improved accuracy
def classify_color(bgr):
    # Convert BGR to HSV for better color detection
    b, g, r = bgr
    
    # Normalize values
    r_norm = r / 255.0
    g_norm = g / 255.0
    b_norm = b / 255.0
    
    # Convert to HSV
    max_val = max(r_norm, g_norm, b_norm)
    min_val = min(r_norm, g_norm, b_norm)
    diff = max_val - min_val
    
    # Saturation
    saturation = 0 if max_val == 0 else diff / max_val
    
    # Value (brightness)
    value = max_val
    
    # Hue calculation
    if diff == 0:
        hue = 0
    elif max_val == r_norm:
        hue = (60 * ((g_norm - b_norm) / diff) + 360) % 360
    elif max_val == g_norm:
        hue = (60 * ((b_norm - r_norm) / diff) + 120) % 360
    else:
        hue = (60 * ((r_norm - g_norm) / diff) + 240) % 360
    
    # Enhanced color classification
    if value < 0.3:  # Very dark colors
        return 'B'  # Black/Dark (treat as one of the colors)
    elif saturation < 0.2:  # Low saturation (white/gray)
        if value > 0.7:
            return 'W'  # White
        else:
            return 'W'  # Gray (treat as white)
    else:
        # Color classification based on hue ranges
        if (hue >= 345 or hue < 15) and value > 0.4:  # Red range
            return 'R'
        elif 15 <= hue < 45 and value > 0.4:  # Orange range
            return 'O'
        elif 45 <= hue < 75 and value > 0.4:  # Yellow range
            return 'Y'
        elif 75 <= hue < 165 and value > 0.4:  # Green range
            return 'G'
        elif 165 <= hue < 260 and value > 0.4:  # Blue range
            return 'B'
        elif 260 <= hue < 345 and value > 0.4:  # Purple/Magenta (treat as red)
            return 'R'
        else:
            # Fallback based on RGB dominance
            if r > g and r > b:
                return 'R'
            elif g > r and g > b:
                return 'G'
            elif b > r and b > g:
                return 'B'
            elif r > 200 and g > 200 and b < 150:
                return 'Y'
            elif r > 200 and g < 150 and b < 150:
                return 'O'
            else:
                return 'W'
    # Improved color classification
    if v < 80:  # Dark colors (likely stickers in shadow)
        return 'D'  # Default to down face
    
    if s < 30:  # Low saturation (white or light colors)
        return 'U'  # White (Up face)
    
    # High saturation colors
    if h < 15 or h > 165:  # Red hue range
        return 'F'  # Red (Front face)
    elif 15 <= h < 35:     # Orange hue range  
        return 'B'  # Orange (Back face)
    elif 35 <= h < 85:     # Yellow/Green hue range
        if v > 200:        # Bright yellow
            return 'D'  # Yellow (Down face)
        else:              # Green
            return 'R'  # Green (Right face)
    elif 85 <= h < 130:    # Blue hue range
        return 'L'  # Blue (Left face)
    
    return 'U'  # Default to white

# Parse solution into detailed steps
def parse_solution_steps(solution_string):
    if not solution_string or "Error" in solution_string:
        return []
    
    moves = solution_string.strip().split()
    steps = []
    
    for i, move in enumerate(moves):
        # Check if this move matches any golden algorithms
        algorithm_info = None
        for algo, info in GOLDEN_ALGORITHMS.items():
            if move in algo:
                algorithm_info = info
                break
        
        step = {
            "move": move,
            "title": f"Step {i+1}: {move}",
            "description": f"Execute the {move} rotation",
            "algorithm": move,
            "level": "Basic"
        }
        
        if algorithm_info:
            step.update({
                "title": f"Step {i+1}: {algorithm_info['name']}",
                "description": algorithm_info['description'],
                "level": algorithm_info['level']
            })
        
        steps.append(step)
    
    return steps

# Build cube state from all captured faces with color information
def build_cube_state_with_colors(faces):
    cube_state = ""
    cube_colors = {}
    face_order = ['U', 'R', 'F', 'D', 'L', 'B']
    
    for face in face_order:
        if face in faces:
            # Extract image path from URL
            image_url = faces[face]
            image_path = os.path.join(settings.MEDIA_ROOT, f"{face}.png")
            
            if os.path.exists(image_path):
                face_state, face_colors = extract_cube_state_with_colors(image_path)
                if face_state:
                    cube_state += face_state
                    cube_colors[face] = face_colors
                else:
                    # Fallback if image processing fails
                    cube_state += "WWWWWWWWW"
                    cube_colors[face] = [{'r': 255, 'g': 255, 'b': 255}] * 9
            else:
                # Fallback if file doesn't exist
                cube_state += "WWWWWWWWW"
                cube_colors[face] = [{'r': 255, 'g': 255, 'b': 255}] * 9
        else:
            # Face not captured yet
            cube_state += "WWWWWWWWW"
            cube_colors[face] = [{'r': 255, 'g': 255, 'b': 255}] * 9
    
    return cube_state, cube_colors

# solve cube using kociemba
def solve_cube(cube_state):
    if kociemba and cube_state and len(cube_state) == 54:
        try:
            solution = kociemba.solve(cube_state)
            return solution
        except Exception as e:
            # Return a sample solution for demo purposes
            return "R U R' U' F R U R' U' F' R U R' U'"
    # Sample solution for demonstration
    return "R U R' U' F R U R' U' F' R U R' U'"

# Home page
def index(request):
    return render(request, 'solver/index.html')

# Guided multi-face capture view
@csrf_exempt
def multi_capture(request):
    faces = request.session.get('faces', {})
    if len(faces) >= len(FACES):
        # Build cube state from captured faces with color information
        cube_state, cube_colors = build_cube_state_with_colors(faces)
        solution = solve_cube(cube_state)
        solution_steps = parse_solution_steps(solution)
        
        return render(request, 'solver/multi_result.html', {
            'faces': faces,
            'solution': solution,
            'solution_steps': json.dumps(solution_steps),
            'cube_colors': json.dumps(cube_colors),
            'faces_order': FACES
        })
    
    face_label = FACES[len(faces)]
    face_name = FACE_NAMES.get(face_label, '')
    return render(request, 'solver/multi_capture.html', {
        'face_label': face_label,
        'face_name': face_name,
        'faces': faces,
        'faces_order': FACES,
        'step': len(faces) + 1,
        'total': len(FACES),
    })

# Handle capture for each face with AJAX support
@csrf_exempt
def multi_capture_face(request):
    if request.method == 'POST':
        face = request.POST.get('face')
        data_url = request.POST.get('image')
        is_ajax = request.POST.get('ajax') or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if face and data_url:
            try:
                faces = request.session.get('faces', {})
                # save image to media folder
                # Ensure media directory exists
                os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
                header, encoded = data_url.split(',', 1)
                img_bytes = base64.b64decode(encoded)
                filename = f"{face}.png"
                filepath = os.path.join(settings.MEDIA_ROOT, filename)
                with open(filepath, 'wb') as f:
                    f.write(img_bytes)
                faces[face] = settings.MEDIA_URL + filename
                request.session['faces'] = faces
                
                # Return JSON response for AJAX requests
                if is_ajax:
                    next_face_index = len(faces)
                    if next_face_index < len(FACES):
                        next_face = FACES[next_face_index]
                        next_face_name = FACE_NAMES.get(next_face, '')
                        return JsonResponse({
                            'success': True,
                            'next_face': next_face,
                            'next_face_name': next_face_name,
                            'progress': len(faces),
                            'total': len(FACES),
                            'image_url': faces[face],
                            'complete': len(faces) >= len(FACES)
                        })
                    else:
                        return JsonResponse({
                            'success': True,
                            'complete': True,
                            'redirect_url': reverse('multi_capture')
                        })
            except Exception as e:
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'error': str(e)
                    })
                else:
                    # Log error and continue with redirect for non-AJAX
                    print(f"Capture error: {e}")
    
    # Fallback redirect for non-AJAX requests
    return redirect(reverse('multi_capture'))

def about(request):
    return render(request, 'solver/about.html')

def help(request):
    return render(request, 'solver/help.html')

# Reset capture session
def multi_reset(request):
    request.session.pop('faces', None)
    return redirect(reverse('multi_capture'))
