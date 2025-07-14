from setuptools import setup

# --- Application Details ---
APP = ['workflow_tracker.py']
DATA_FILES = ['Magic Clone.png', 'icon_active.png', 'icon_inactive.png']

# --- py2app Options ---
# This section is updated to match the application's actual needs.
# It removes outdated packages (cv2, numpy, pytesseract) and adds the 'Vision' framework.
OPTIONS = {
    'argv_emulation': False,
    'packages': ['rumps', 'pynput', 'requests', 'mss', 'PIL'],
    'includes': ['AppKit', 'Foundation', 'Quartz', 'Vision', 'imp'],
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
