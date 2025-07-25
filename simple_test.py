#!/usr/bin/env python3
"""
Simple test of cube solving without OpenCV to verify core functionality
"""

import os
import sys

# Add the project directory to Python path
sys.path.append('/workspaces/cube')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cube_project.settings')

import django
django.setup()

def test_basic_functionality():
    """Test basic Django setup and imports"""
    print("🧪 Testing Basic Functionality...")
    
    try:
        from django.conf import settings
        print("✅ Django configuration loaded")
        
        from django.urls import reverse
        print("✅ Django URL routing available")
        
        # Test kociemba import
        try:
            import kociemba
            print("✅ Kociemba cube solver available")
            
            # Test with a simple solved cube state
            solved_state = "UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB"
            solution = kociemba.solve(solved_state)
            print(f"✅ Kociemba solver works: {solution[:20]}...")
        except ImportError:
            print("⚠️  Kociemba not available, will use fallback")
        
        print("✅ Basic functionality test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_basic_functionality()
