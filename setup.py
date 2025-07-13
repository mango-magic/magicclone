from setuptools import setup

APP = ['workflow_tracker.py']  # Use the filename of your main script
DATA_FILES = []
OPTIONS = {
    'argv_emulation': True,
    'packages': ['rumps', 'pynput', 'requests'],
    'includes': ['AppKit', 'Foundation', 'Quartz'],  # Added Foundation if needed
    'iconfile': 'Magic Clone.png',  # Path to the PNG icon in the repo root; py2app converts to .icns
    'plist': {
        'CFBundleDisplayName': 'Magic Clone',
        'CFBundleName': 'MagicClone'
    }
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
