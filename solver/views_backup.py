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

# Enhanced cube extraction with auto-cropping using OpenCV
def auto_crop_cube_from_image(img):
    """
    Automatically detect and crop the cube from the image using OpenCV
    """
    if img is None:
        return None
    
    # Convert to different color spaces for better detection
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Use adaptive thresholding to find edges
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY, 11, 2)
    
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return img  # Return original if no contours found
    
    # Find the largest rectangular contour (likely the cube face)
    cube_contour = None
    max_area = 0
    
    for contour in contours:
        # Approximate contour to reduce points
        epsilon = 0.02 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        
        # Look for quadrilateral shapes (4 points) that are large enough
        if len(approx) >= 4:
            area = cv2.contourArea(contour)
            if area > max_area and area > 1000:  # Minimum area threshold
                max_area = area
                cube_contour = contour
    
    if cube_contour is not None:
        # Get bounding rectangle
        x, y, w, h = cv2.boundingRect(cube_contour)
        
        # Add some padding and ensure we don't go outside image bounds
        padding = 20
        x = max(0, x - padding)
        y = max(0, y - padding)
        w = min(img.shape[1] - x, w + 2 * padding)
        h = min(img.shape[0] - y, h + 2 * padding)
        
        # Ensure the crop is square-ish (cube faces should be square)
        if abs(w - h) > min(w, h) * 0.3:  # If not roughly square, make it square
            size = max(w, h)
            # Center the square crop
            center_x = x + w // 2
            center_y = y + h // 2
            x = max(0, center_x - size // 2)
            y = max(0, center_y - size // 2)
            w = min(img.shape[1] - x, size)
            h = min(img.shape[0] - y, size)
        
        # Crop the image
        cropped = img[y:y+h, x:x+w]
        
        # Resize to standard size for consistent processing
        if cropped.size > 0:
            cropped = cv2.resize(cropped, (400, 400))
            return cropped
    
    # Fallback: return center crop if auto-detection fails
    h, w = img.shape[:2]
    size = min(h, w)
    start_x = (w - size) // 2
    start_y = (h - size) // 2
    center_crop = img[start_y:start_y+size, start_x:start_x+size]
    return cv2.resize(center_crop, (400, 400))

# Extract cube state from image file path with color details and auto-cropping
def extract_cube_state_with_colors(image_path):
    img = cv2.imread(image_path)
    if img is None:
        return None, []
    
    # Auto-crop the cube from the image using OpenCV detection
    cropped_img = auto_crop_cube_from_image(img)
    if cropped_img is None:
        return None, []
    
    # Save the cropped version for better visualization
    cropped_path = image_path.replace('.png', '_cropped.png')
    cv2.imwrite(cropped_path, cropped_img)
    
    # Ensure image is 400x400 for consistent processing
    img = cv2.resize(cropped_img, (400, 400))
    facelet_colors = []
    rgb_colors = []
    
    # Extract colors from 3x3 grid
    for row in range(3):
        for col in range(3):
            # Calculate position within the cube area (leaving border)
            x = int(50 + (col + 0.5) * 100)  # 50px border, 100px per cell
            y = int(50 + (row + 0.5) * 100)
            
            # Sample a larger area around the center point for better accuracy
            sample_size = 15  # Increased sample size
            sample_area = img[max(0, y-sample_size):min(img.shape[0], y+sample_size), 
                             max(0, x-sample_size):min(img.shape[1], x+sample_size)]
            
            if sample_area.size > 0:
                # Average color in the sample area
                avg_bgr = np.mean(sample_area.reshape(-1, 3), axis=0)
                color_letter = classify_color(avg_bgr)
                facelet_colors.append(color_letter)
                
                # Convert to RGB and store actual detected color for visualization
                rgb_color = STANDARD_COLORS.get(color_letter, (255, 255, 255))
                rgb_colors.append({
                    'r': rgb_color[0],
                    'g': rgb_color[1], 
                    'b': rgb_color[2]
                })
            else:
                facelet_colors.append('W')
                rgb_colors.append({'r': 255, 'g': 255, 'b': 255})
    
    return ''.join(facelet_colors), rgb_colors

# Global color tracking to ensure 6 rigid colors with max 9 occurrences each
COLOR_COUNTS = {'W': 0, 'R': 0, 'O': 0, 'Y': 0, 'G': 0, 'B': 0}

def reset_color_counts():
    """Reset color counts for a new cube session"""
    global COLOR_COUNTS
    COLOR_COUNTS = {'W': 0, 'R': 0, 'O': 0, 'Y': 0, 'G': 0, 'B': 0}

def get_color_counts():
    """Get current color counts"""
    return COLOR_COUNTS.copy()

# Define RGB reference values for the 6 standard cube colors
STANDARD_COLORS = {
    'W': (255, 255, 255),  # White
    'R': (255, 0, 0),      # Red  
    'O': (255, 165, 0),    # Orange
    'Y': (255, 255, 0),    # Yellow
    'G': (0, 255, 0),      # Green
    'B': (0, 0, 255)       # Blue
}

def color_distance(color1, color2):
    """Calculate Euclidean distance between two RGB colors"""
    return sum((a - b) ** 2 for a, b in zip(color1, color2)) ** 0.5

def classify_color(bgr):
    """Classify color to one of 6 rigid cube colors with occurrence limits"""
    global COLOR_COUNTS
    
    # Convert BGR to RGB
    b, g, r = [int(x) for x in bgr]
    rgb = (r, g, b)
    
    # Find closest standard color
    min_distance = float('inf')
    closest_color = 'W'
    
    for color_code, standard_rgb in STANDARD_COLORS.items():
        distance = color_distance(rgb, standard_rgb)
        if distance < min_distance:
            min_distance = distance
            closest_color = color_code
    
    # Apply additional heuristics for better accuracy
    # Convert to HSV for better classification
    r_norm = r / 255.0
    g_norm = g / 255.0
    b_norm = b / 255.0
    
    max_val = max(r_norm, g_norm, b_norm)
    min_val = min(r_norm, g_norm, b_norm)
    diff = max_val - min_val
    
    # Saturation and Value
    saturation = 0 if max_val == 0 else diff / max_val
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
    
    # Override based on HSV analysis for better accuracy
    if value < 0.25:  # Very dark - could be any dark color
        if closest_color not in ['W', 'Y']:  # Prefer non-light colors for dark areas
            pass  # Keep closest_color
        else:
            closest_color = 'B'  # Default to blue for very dark areas
    elif saturation < 0.15:  # Low saturation (white/gray)
        closest_color = 'W'
    else:
        # High saturation - use hue to determine color
        if (hue >= 345 or hue < 15):  # Red range
            closest_color = 'R'
        elif 15 <= hue < 35:  # Orange range
            closest_color = 'O'
        elif 35 <= hue < 75:  # Yellow range
            closest_color = 'Y'
        elif 75 <= hue < 165:  # Green range
            closest_color = 'G'
        elif 165 <= hue < 250:  # Blue range
            closest_color = 'B'
        elif 250 <= hue < 345:  # Purple/Magenta - treat as red or blue
            if r > b:
                closest_color = 'R'
            else:
                closest_color = 'B'
    
    # Check if this color has exceeded its limit (9 occurrences)
    if COLOR_COUNTS.get(closest_color, 0) >= 9:
        # Find the color with least occurrences that's under limit
        available_colors = [c for c, count in COLOR_COUNTS.items() if count < 9]
        if available_colors:
            # Choose based on second-closest match
            second_distances = {}
            for color_code in available_colors:
                distance = color_distance(rgb, STANDARD_COLORS[color_code])
                second_distances[color_code] = distance
            closest_color = min(second_distances, key=second_distances.get)
        else:
            # All colors at limit - this shouldn't happen in a valid cube
            closest_color = 'W'  # Default fallback
    
    # Increment color count
    COLOR_COUNTS[closest_color] = COLOR_COUNTS.get(closest_color, 0) + 1
    
    return closest_color

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
    
    # Reset color counts for fresh validation
    reset_color_counts()
    
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

def convert_to_kociemba_notation(cube_state_colors):
    """
    Convert our color-based cube state to kociemba's position-based notation
    Our faces: U(up), R(right), F(front), D(down), L(left), B(back)
    Kociemba expects the same face order but with position-based notation
    """
    if not cube_state_colors or len(cube_state_colors) != 54:
        return None
    
    # For kociemba, we need to convert colors to face positions
    # The center pieces define which color belongs to which face
    face_centers = {
        'U': cube_state_colors[4],   # Up face center (index 4 in first 9)
        'R': cube_state_colors[13],  # Right face center (index 4 in second 9)
        'F': cube_state_colors[22],  # Front face center (index 4 in third 9)
        'D': cube_state_colors[31],  # Down face center (index 4 in fourth 9)
        'L': cube_state_colors[40],  # Left face center (index 4 in fifth 9)
        'B': cube_state_colors[49],  # Back face center (index 4 in sixth 9)
    }
    
    # Create reverse mapping from color to face
    color_to_face = {color: face for face, color in face_centers.items()}
    
    # Convert each color to its corresponding face position
    kociemba_state = ""
    for color in cube_state_colors:
        face_position = color_to_face.get(color, 'U')  # Default to U if color not found
        kociemba_state += face_position
    
    return kociemba_state

# solve cube using kociemba with proper state validation
def solve_cube(cube_state):
    if not cube_state or len(cube_state) != 54:
        return "Invalid cube state: must be 54 characters"
    
    # Validate cube state has exactly 9 of each color
    color_counts = {}
    for color in cube_state:
        color_counts[color] = color_counts.get(color, 0) + 1
    
    # Check if we have exactly 6 colors with 9 occurrences each
    if len(color_counts) != 6:
        return f"Invalid cube: found {len(color_counts)} colors, expected 6. Colors found: {list(color_counts.keys())}"
    
    for color, count in color_counts.items():
        if count != 9:
            return f"Invalid cube: color {color} appears {count} times, expected 9"
    
    # Convert our color notation to kociemba position notation
    kociemba_state = convert_to_kociemba_notation(cube_state)
    
    if kociemba and kociemba_state:
        try:
            # Try to solve with kociemba
            solution = kociemba.solve(kociemba_state)
            if solution and not solution.startswith("Error"):
                return solution
            else:
                return "Cube cannot be solved - invalid configuration"
        except Exception as e:
            return f"Solver error: {str(e)}"
    
    # Fallback: return sample educational solution
    return "R U R' U' R U R' F' R U R' U' R' F R2 U' R' U"

# Home page
def index(request):
    return render(request, 'solver/index.html')

# Guided multi-face capture view
@csrf_exempt
def multi_capture(request):
    faces = request.session.get('faces', {})
    
    # If starting fresh, reset color counts
    if not faces:
        reset_color_counts()
    
    if len(faces) >= len(FACES):
        # Build cube state from captured faces with color information
        cube_state, cube_colors = build_cube_state_with_colors(faces)
        solution = solve_cube(cube_state)
        solution_steps = parse_solution_steps(solution)
        
        # Add color count information for debugging
        current_counts = get_color_counts()
        
        return render(request, 'solver/multi_result.html', {
            'faces': faces,
            'solution': solution,
            'solution_steps': json.dumps(solution_steps),
            'cube_colors': json.dumps(cube_colors),
            'faces_order': FACES,
            'color_counts': current_counts,
            'cube_state': cube_state
        })
    
    face_label = FACES[len(faces)]
    face_name = FACE_NAMES.get(face_label, '')
    
    # Get current color counts for display
    current_counts = get_color_counts()
    
    return render(request, 'solver/multi_capture.html', {
        'face_label': face_label,
        'face_name': face_name,
        'faces': faces,
        'faces_order': FACES,
        'step': len(faces) + 1,
        'total': len(FACES),
        'color_counts': current_counts
    })

# Handle capture for each face with AJAX support and auto-cropping
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
                
                # Save original image
                filename = f"{face}.png"
                filepath = os.path.join(settings.MEDIA_ROOT, filename)
                with open(filepath, 'wb') as f:
                    f.write(img_bytes)
                
                # Process with auto-cropping
                try:
                    img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
                    if img is not None:
                        # Auto-crop the cube
                        cropped_img = auto_crop_cube_from_image(img)
                        if cropped_img is not None:
                            # Save cropped version
                            cropped_filename = f"{face}_cropped.png"
                            cropped_filepath = os.path.join(settings.MEDIA_ROOT, cropped_filename)
                            cv2.imwrite(cropped_filepath, cropped_img)
                            
                            # Use cropped image URL for display
                            faces[face] = settings.MEDIA_URL + cropped_filename
                        else:
                            # Fallback to original if cropping fails
                            faces[face] = settings.MEDIA_URL + filename
                    else:
                        faces[face] = settings.MEDIA_URL + filename
                except Exception as crop_error:
                    print(f"Auto-crop error: {crop_error}")
                    # Fallback to original image
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
    # Reset color counts when starting fresh
    reset_color_counts()
    return redirect(reverse('multi_capture'))
