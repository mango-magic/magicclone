from setuptools import setup

APP = ['workflow_tracker.py']  # Use the filename of your main script
DATA_FILES = []
OPTIONS = {
    'argv_emulation': True,
    'packages': ['rumps', 'pynput', 'pyobjc', 'requests'],
    'includes': ['AppKit', 'Foundation'],  # Added Foundation if needed
    'plist': {
        'CFBundleDisplayName': 'Workflow Tracker',
        'CFBundleName': 'WorkflowTracker'
    }
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)