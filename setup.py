from setuptools import setup

# --- Application Details ---
APP = ['workflow_tracker.py']
# Include all icon files in the application bundle
DATA_FILES = ['Magic Clone.png', 'icon_active.png', 'icon_inactive.png']

# --- py2app Options ---
# This dictionary contains all the configurations for py2app to build the app correctly.
OPTIONS = {
    'argv_emulation': False,
    'packages': ['rumps', 'pynput', 'requests'],
    'includes': ['AppKit', 'Foundation', 'Quartz', 'imp'],
    
    # Set the main application icon (this is the one you see in Finder)
    'iconfile': 'Magic Clone.png',

    # Sets application metadata, like the name displayed in Finder and the menu bar.
    'plist': {
        'CFBundleDisplayName': 'Mango Clone',
        'CFBundleName': 'MangoClone',
        'LSUIElement': True,  # This hides the app's icon from the Dock
    }
}

# --- Setup Configuration ---
setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
