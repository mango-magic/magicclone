from setuptools import setup

# --- Application Details ---
APP = ['workflow_tracker.py']
DATA_FILES = []

# --- py2app Options ---
# This dictionary contains all the configurations for py2app to build the app correctly.
OPTIONS = {
    # 'argv_emulation': False
    # This is the critical fix. It was set to True, which enables an old feature
    # for opening files dropped on the app icon. This feature relies on the obsolete
    # 'Carbon' framework, which no longer exists in modern macOS, causing the crash.
    # Disabling it resolves the launch error.
    'argv_emulation': False,

    # 'packages': [...]
    # Explicitly tells py2app to include these entire packages in the app bundle.
    # This is necessary for libraries that py2app might not fully detect on its own.
    'packages': ['rumps', 'pynput', 'requests'],

    # 'includes': [...]
    # Explicitly includes specific macOS frameworks that are required by the libraries.
    # - AppKit and Foundation are standard for any GUI app.
    # - Quartz is required by 'pynput' for listening to keyboard and mouse events.
    #   Without this, the app would crash when trying to start the listeners.
    'includes': ['AppKit', 'Foundation', 'Quartz'],

    # 'iconfile': ...
    # Specifies the application icon. Make sure 'Magic Clone.png' exists in the folder.
    'iconfile': 'Magic Clone.png',

    # 'plist': {...}
    # Sets application metadata, like the name displayed in Finder and the menu bar.
    'plist': {
        'CFBundleDisplayName': 'Magic Clone',
        'CFBundleName': 'MagicClone',
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
