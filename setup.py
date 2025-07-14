from setuptools import setup
import os
import cv2
import glob

# --- Find and prepare OpenCV data files ---
cv2_data_path = os.path.join(os.path.dirname(cv2.__file__), 'data')
cv2_data_files = glob.glob(os.path.join(cv2_data_path, '*.xml'))

# --- Application Details ---
APP = ['workflow_tracker.py']
DATA_FILES = [
    'Magic Clone.png', 'icon_active.png', 'icon_inactive.png',
    ('data', cv2_data_files) # Include the OpenCV data files
]

# --- py2app Options ---
OPTIONS = {
    'argv_emulation': False,
    # Add cv2 and numpy to the packages list
    'packages': ['rumps', 'pynput', 'requests', 'mss', 'pytesseract', 'PIL', 'cv2', 'numpy'],
    'includes': ['AppKit', 'Foundation', 'Quartz', 'imp'],
    'iconfile': 'Magic Clone.png',
    'plist': {
        'CFBundleDisplayName': 'Mango Clone',
        'CFBundleName': 'MangoClone',
        'LSUIElement': True,
    }
}

# --- Setup Configuration ---
setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
