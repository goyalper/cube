from flask import Flask, render_template, request, redirect, url_for
import os
import cv2
import numpy as np
try:
    import kociemba
except ImportError:
    kociemba = None

import base64
from io import BytesIO
from PIL import Image

app = Flask(__name__)


# Main entry: live camera
@app.route('/')
def camera():
    return render_template('camera.html')

# Secondary: upload page
@app.route('/upload_page')
def upload_page():
    return render_template('upload.html')


# Handle image upload (secondary)
@app.route('/upload', methods=['POST'])
def upload():
    if 'image' not in request.files:
        return redirect(url_for('upload_page'))
    image = request.files['image']
    if image.filename == '':
        return redirect(url_for('upload_page'))
    image_path = os.path.join('static', image.filename)
    image.save(image_path)
    cube_state = extract_cube_state(image_path)
    solution = solve_cube(cube_state)
    return render_template('result.html', image_path=image_path, solution=solution)

# Handle camera image (main)
@app.route('/camera_upload', methods=['POST'])
def camera_upload():
    data_url = request.form.get('image')
    if not data_url:
        return redirect(url_for('camera'))
    # Decode base64 image
    header, encoded = data_url.split(',', 1)
    img_bytes = base64.b64decode(encoded)
    img = Image.open(BytesIO(img_bytes)).convert('RGB')
    image_path = os.path.join('static', 'camera_capture.png')
    img.save(image_path)
    cube_state = extract_cube_state(image_path)
    solution = solve_cube(cube_state)
    return render_template('result.html', image_path=image_path, solution=solution)


# Extract cube state from image
def extract_cube_state(image_path):
    img = cv2.imread(image_path)
    if img is None:
        return None
    img = cv2.resize(img, (300, 300))
    facelet_colors = []
    for row in range(3):
        for col in range(3):
            x = int((col + 0.5) * 100)
            y = int((row + 0.5) * 100)
            bgr = img[y, x]
            color = classify_color(bgr)
            facelet_colors.append(color)
    cube_state = ''.join(facelet_colors * 6)
    return cube_state

def classify_color(bgr):
    hsv = cv2.cvtColor(np.uint8([[bgr]]), cv2.COLOR_BGR2HSV)[0][0]
    h, s, v = hsv
    if v < 50:
        return 'D'
    if s < 50:
        return 'U'
    if h < 10 or h > 160:
        return 'R'
    if 10 < h < 35:
        return 'F'
    if 35 < h < 85:
        return 'L'
    if 85 < h < 130:
        return 'B'
    return 'U'

# Solve cube using kociemba
def solve_cube(cube_state):
    if kociemba and cube_state:
        try:
            return kociemba.solve(cube_state)
        except Exception as e:
            return f"Error solving cube: {e}"
    else:
        return "Could not extract cube state or kociemba not installed."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
