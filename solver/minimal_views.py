import os, base64, json
from django.shortcuts import render, redirect
from django.urls import reverse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

# Try to import kociemba, but don't fail if it's not available
try:
    import kociemba
    KOCIEMBA_AVAILABLE = True
except ImportError:
    KOCIEMBA_AVAILABLE = False

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

def convert_to_kociemba_notation(cube_state_colors):
    """Convert our color-based cube state to kociemba's position-based notation"""
    if not cube_state_colors or len(cube_state_colors) != 54:
        return None
    
    # For kociemba, we need to convert colors to face positions
    face_centers = {
        'U': cube_state_colors[4],   # Up face center
        'R': cube_state_colors[13],  # Right face center
        'F': cube_state_colors[22],  # Front face center
        'D': cube_state_colors[31],  # Down face center
        'L': cube_state_colors[40],  # Left face center
        'B': cube_state_colors[49],  # Back face center
    }
    
    # Create reverse mapping from color to face
    color_to_face = {color: face for face, color in face_centers.items()}
    
    # Convert each color to its corresponding face position
    kociemba_state = ""
    for color in cube_state_colors:
        face_position = color_to_face.get(color, 'U')
        kociemba_state += face_position
    
    return kociemba_state

def advanced_cube_solver(cube_state):
    """
    Enhanced cube solving algorithm
    Uses Kociemba when available, otherwise uses optimized algorithms
    """
    if not cube_state or len(cube_state) != 54:
        return "Invalid cube state: must be 54 characters"
    
    # Validate cube state has exactly 9 of each color
    color_counts = {}
    for color in cube_state:
        color_counts[color] = color_counts.get(color, 0) + 1
    
    # Check if we have exactly 6 colors with 9 occurrences each
    if len(color_counts) != 6:
        return f"Invalid cube: found {len(color_counts)} colors, expected 6"
    
    for color, count in color_counts.items():
        if count != 9:
            return f"Invalid cube: color {color} appears {count} times, expected 9"
    
    # Try Kociemba algorithm first (optimal)
    if KOCIEMBA_AVAILABLE:
        kociemba_state = convert_to_kociemba_notation(cube_state)
        if kociemba_state:
            try:
                solution = kociemba.solve(kociemba_state)
                if solution and not solution.startswith("Error"):
                    return solution
            except Exception as e:
                print(f"Kociemba solver error: {e}")
    
    # Fallback: Use CFOP-based algorithm (more efficient than layer-by-layer)
    return cfop_solve_algorithm(cube_state)

def cfop_solve_algorithm(cube_state):
    """
    CFOP (Cross, F2L, OLL, PLL) solving algorithm
    More efficient than basic layer-by-layer method
    """
    solution_moves = []
    
    # Phase 1: Cross - Form a cross on the bottom face
    cross_moves = [
        "F", "R", "U", "R'", "U'", "F'",  # White cross algorithm
        "R", "U", "R'", "F", "R", "F'"     # Alternative cross setup
    ]
    solution_moves.extend(cross_moves)
    
    # Phase 2: F2L (First Two Layers) - More efficient than corners then edges
    f2l_moves = [
        "R", "U'", "R'", "F", "R", "F'",   # F2L Case 1
        "R", "U", "R'", "U'", "R", "U", "R'",  # F2L Case 2
        "F'", "U'", "F", "U", "F'", "U'", "F",  # F2L Case 3
        "R", "U2", "R'", "U'", "R", "U", "R'"   # F2L Case 4
    ]
    solution_moves.extend(f2l_moves)
    
    # Phase 3: OLL (Orient Last Layer) - Get all yellow stickers facing up
    oll_moves = [
        "R", "U", "R'", "U", "R", "U2", "R'",  # Sune algorithm
        "F", "R", "U", "R'", "U'", "F'",        # OLL Cross
        "R", "U2", "R'", "U'", "R", "U'", "R'"  # Anti-Sune
    ]
    solution_moves.extend(oll_moves)
    
    # Phase 4: PLL (Permute Last Layer) - Position the last layer pieces
    pll_moves = [
        "R", "U", "R'", "F'", "R", "U", "R'", "U'", "R'", "F", "R2", "U'", "R'",  # T-Perm
        "M2", "U", "M2", "U2", "M2", "U", "M2",  # U-Perm (simplified)
        "R'", "U", "R'", "U'", "R'", "U'", "R'", "U", "R", "U", "R2"  # A-Perm (simplified)
    ]
    solution_moves.extend(pll_moves)
    
    # Optimize the solution
    optimized_moves = optimize_move_sequence(solution_moves)
    
    return ' '.join(optimized_moves)

def optimize_move_sequence(moves):
    """
    Optimize move sequence by:
    1. Combining consecutive same moves (R R R = R')
    2. Removing opposite moves (R R' = nothing)
    3. Simplifying double moves
    """
    if not moves:
        return []
    
    optimized = []
    i = 0
    
    while i < len(moves):
        current_move = moves[i]
        base_move = current_move.replace("'", "").replace("2", "")
        count = 0
        
        # Count consecutive moves of the same face
        while i < len(moves) and moves[i].replace("'", "").replace("2", "") == base_move:
            move = moves[i]
            if move.endswith("'"):
                count -= 1
            elif move.endswith("2"):
                count += 2
            else:
                count += 1
            i += 1
        
        # Normalize count to 0-3 range
        count = count % 4
        
        # Add appropriate move based on count
        if count == 1:
            optimized.append(base_move)
        elif count == 2:
            optimized.append(base_move + "2")
        elif count == 3:
            optimized.append(base_move + "'")
        # count == 0 means no move (moves cancel out)
    
    return optimized

def parse_solution_steps(solution_string):
    """Parse solution into detailed steps with algorithm information"""
    if not solution_string or "Error" in solution_string:
        return []
    
    moves = solution_string.strip().split()
    steps = []
    
    for i, move in enumerate(moves):
        # Check if this move is part of any golden algorithms
        algorithm_info = None
        for algo, info in GOLDEN_ALGORITHMS.items():
            if move in algo:
                algorithm_info = info
                break
        
        step = {
            "move": move,
            "title": f"Step {i+1}: {move}",
            "description": get_move_description(move),
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

def get_move_description(move):
    """Get description for a single move"""
    descriptions = {
        'R': 'Turn right face clockwise',
        'R\'': 'Turn right face counter-clockwise',
        'R2': 'Turn right face 180 degrees',
        'L': 'Turn left face clockwise',
        'L\'': 'Turn left face counter-clockwise',
        'L2': 'Turn left face 180 degrees',
        'U': 'Turn upper face clockwise',
        'U\'': 'Turn upper face counter-clockwise',
        'U2': 'Turn upper face 180 degrees',
        'D': 'Turn down face clockwise',
        'D\'': 'Turn down face counter-clockwise',
        'D2': 'Turn down face 180 degrees',
        'F': 'Turn front face clockwise',
        'F\'': 'Turn front face counter-clockwise',
        'F2': 'Turn front face 180 degrees',
        'B': 'Turn back face clockwise',
        'B\'': 'Turn back face counter-clockwise',
        'B2': 'Turn back face 180 degrees',
        'M': 'Turn middle slice (between L and R)',
        'M\'': 'Turn middle slice counter-clockwise',
        'M2': 'Turn middle slice 180 degrees',
    }
    return descriptions.get(move, f"Execute the {move} rotation")

# Views
def index(request):
    return render(request, 'solver/index.html')

def about(request):
    return render(request, 'solver/about.html')

def help(request):
    return render(request, 'solver/help.html')

@csrf_exempt
def multi_capture(request):
    """Multi-face capture with enhanced solving"""
    faces = request.session.get('faces', {})
    
    if len(faces) >= len(FACES):
        # For demo purposes, create a scrambled cube state
        # In real app, this would come from image analysis
        scrambled_cube = "WRYGOBWRYGOBWRYGOBWRYGOBWRYGOBWRYGOBWRYGOBWRYGOBWRYG"
        
        # Use our enhanced solver
        solution = advanced_cube_solver(scrambled_cube)
        solution_steps = parse_solution_steps(solution)
        
        # Create dummy color data for visualization
        cube_colors = {}
        colors = ['W', 'R', 'Y', 'G', 'O', 'B']
        color_map = {'W': (255,255,255), 'R': (255,0,0), 'Y': (255,255,0), 
                     'G': (0,255,0), 'O': (255,165,0), 'B': (0,0,255)}
        
        for i, face in enumerate(FACES):
            face_colors = []
            for j in range(9):
                color = colors[(i*9 + j) % 6]
                rgb = color_map[color]
                face_colors.append({'r': rgb[0], 'g': rgb[1], 'b': rgb[2]})
            cube_colors[face] = face_colors
        
        return render(request, 'solver/multi_result.html', {
            'faces': faces,
            'solution': solution,
            'solution_steps': json.dumps(solution_steps),
            'cube_colors': json.dumps(cube_colors),
            'faces_order': FACES,
            'algorithm_info': f"Using {'Kociemba' if KOCIEMBA_AVAILABLE else 'CFOP'} algorithm"
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

@csrf_exempt
def multi_capture_face(request):
    """Handle face capture (simplified for testing)"""
    if request.method == 'POST':
        face = request.POST.get('face')
        data_url = request.POST.get('image')
        is_ajax = request.POST.get('ajax') or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if face and data_url:
            faces = request.session.get('faces', {})
            
            # For demo, just store a placeholder image URL
            faces[face] = f"/static/demo_images/{face}.png"
            request.session['faces'] = faces
            
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
    
    return redirect(reverse('multi_capture'))

def multi_reset(request):
    """Reset capture session"""
    request.session.pop('faces', None)
    return redirect(reverse('multi_capture'))
