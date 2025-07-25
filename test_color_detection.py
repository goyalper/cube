#!/usr/bin/env python3
"""
Test script to verify the improved color detection and cube solving functionality
"""

import os
import sys
import numpy as np

# Add the project directory to Python path
sys.path.append('/workspaces/cube')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cube_project.settings')

import django
django.setup()

from solver.views import classify_color, reset_color_counts, get_color_counts, solve_cube, convert_to_kociemba_notation

def test_color_classification():
    """Test that color classification works with 6 rigid colors"""
    print("🎨 Testing Color Classification...")
    
    # Reset color counts
    reset_color_counts()
    
    # Test colors (BGR format for OpenCV)
    test_colors = [
        # White variations
        ([255, 255, 255], 'W'),  # Pure white
        ([240, 240, 240], 'W'),  # Light gray
        ([200, 200, 200], 'W'),  # Medium gray
        
        # Red variations  
        ([0, 0, 255], 'R'),      # Pure red
        ([0, 50, 200], 'R'),     # Dark red
        ([50, 50, 255], 'R'),    # Bright red
        
        # Orange variations
        ([0, 165, 255], 'O'),    # Pure orange
        ([0, 140, 255], 'O'),    # Dark orange
        ([50, 180, 255], 'O'),   # Light orange
        
        # Yellow variations
        ([0, 255, 255], 'Y'),    # Pure yellow
        ([0, 200, 200], 'Y'),    # Dark yellow
        ([50, 255, 255], 'Y'),   # Bright yellow
        
        # Green variations
        ([0, 255, 0], 'G'),      # Pure green
        ([0, 200, 0], 'G'),      # Dark green
        ([50, 255, 50], 'G'),    # Light green
        
        # Blue variations
        ([255, 0, 0], 'B'),      # Pure blue
        ([200, 0, 0], 'B'),      # Dark blue
        ([255, 50, 50], 'B'),    # Light blue
    ]
    
    results = []
    for bgr, expected in test_colors:
        detected = classify_color(np.array(bgr))
        results.append((bgr, expected, detected, detected == expected))
        print(f"BGR {bgr} -> Expected: {expected}, Got: {detected} {'✅' if detected == expected else '❌'}")
    
    # Check color counts
    counts = get_color_counts()
    print(f"\n📊 Color Counts: {counts}")
    
    success_rate = sum(1 for _, _, _, correct in results if correct) / len(results)
    print(f"🎯 Success Rate: {success_rate:.1%}")
    
    return success_rate > 0.7  # At least 70% should be correct

def test_color_limits():
    """Test that color counting limits work correctly"""
    print("\n🔢 Testing Color Count Limits...")
    
    reset_color_counts()
    
    # Try to classify 15 white colors (should limit to 9)
    white_bgr = np.array([255, 255, 255])
    white_count = 0
    
    for i in range(15):
        color = classify_color(white_bgr)
        if color == 'W':
            white_count += 1
    
    counts = get_color_counts()
    print(f"Attempted 15 white classifications, got {white_count} whites")
    print(f"Final counts: {counts}")
    
    # Should not exceed 9 for any color
    max_count = max(counts.values()) if counts else 0
    success = max_count <= 9
    print(f"Max count check: {max_count} <= 9 {'✅' if success else '❌'}")
    
    return success

def test_cube_solution():
    """Test the cube solution algorithm"""
    print("\n🧩 Testing Cube Solution Algorithm...")
    
    # Create a valid cube state (each color appears exactly 9 times)
    # This represents a solved cube in our color notation
    valid_cube_state = "WWWWWWWWWRRRRRRRRROOOOOOOOOYYYYYYYYY" + "GGGGGGGGGBBBBBBBBB"
    
    print(f"Cube state length: {len(valid_cube_state)}")
    print(f"Color distribution: {dict((c, valid_cube_state.count(c)) for c in 'WROYGB')}")
    
    # Test kociemba conversion
    kociemba_state = convert_to_kociemba_notation(valid_cube_state)
    if kociemba_state:
        print(f"Kociemba state: {kociemba_state[:20]}...")
    
    # Test solution
    solution = solve_cube(valid_cube_state)
    print(f"Solution: {solution}")
    
    success = not solution.startswith("Invalid") and not solution.startswith("Error")
    print(f"Solution valid: {'✅' if success else '❌'}")
    
    return success

def test_invalid_cube():
    """Test handling of invalid cube states"""
    print("\n🚫 Testing Invalid Cube Handling...")
    
    # Invalid cube: too many of one color
    invalid_cube_state = "WWWWWWWWWWWWWWWWWWRRRRRRRRROOOOOOOOO" + "YYYYYYYYYGGGGGGGGBBBBBBBBB"
    
    solution = solve_cube(invalid_cube_state)
    print(f"Invalid cube solution: {solution}")
    
    success = "Invalid" in solution or "Error" in solution
    print(f"Correctly rejected invalid cube: {'✅' if success else '❌'}")
    
    return success

def main():
    """Run all tests"""
    print("🧪 CubeMaster Pro - Color Detection & Solving Tests\n")
    print("=" * 60)
    
    tests = [
        ("Color Classification", test_color_classification),
        ("Color Count Limits", test_color_limits),
        ("Cube Solution", test_cube_solution),
        ("Invalid Cube Handling", test_invalid_cube),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 30)
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY:")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)
    print(f"\nOverall: {total_passed}/{total_tests} tests passed ({total_passed/total_tests:.1%})")
    
    if total_passed == total_tests:
        print("🎉 All tests passed! The cube solver is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the issues above.")

if __name__ == "__main__":
    main()
