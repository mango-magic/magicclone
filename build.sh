#!/bin/bash

# This script provides a user-friendly installer for the MagicClone Workflow Tracker.
# It displays a pop-up message and then runs the entire build process silently in the background.

# --- Main Build Logic ---
# This function contains the entire installation and build process.
run_build_process() {
    # Function to check if a command exists
    command_exists() {
        command -v "$1" >/dev/null 2>&1
    }

    # --- Environment Setup ---
    echo "Setting up the build environment..."

    # Install Homebrew if not present
    if ! command_exists brew; then
        echo "Homebrew not found. Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        # Add Homebrew to PATH for this session
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi

    # Update Homebrew
    echo "Updating Homebrew..."
    brew update

    # Install Python 3.11 if not present
    if ! command_exists python3.11; then
        echo "Python 3.11 not found. Installing via Homebrew..."
        brew install python@3.11
    fi

    # Define the Python binary path for consistency
    PYTHON_BIN="/opt/homebrew/bin/python3.11"

    # --- SOURCE CODE CLEANUP ---
    # This removes macOS metadata from downloaded files that can interfere with code signing.
    echo "Cleaning extended attributes from the source directory..."
    xattr -cr .
    echo "Source directory cleaned."


    # --- Build Preparation ---
    echo "Preparing a clean build environment..."

    # Remove old build artifacts to ensure a fresh start
    rm -rf build dist

    # Create and activate a virtual environment
    if [ ! -d "venv" ]; then
        $PYTHON_BIN -m venv venv
    fi
    source venv/bin/activate

    # Install required Python packages
    echo "Installing dependencies..."
    pip install -r requirements.txt

    # --- CRITICAL FIX: Overwrite setup.py with correct configuration ---
    # Instead of patching, we now create the file directly to guarantee correctness.
    echo "Creating correct setup.py configuration..."
    cat << EOF > setup.py
from setuptools import setup

# --- Application Details ---
APP = ['workflow_tracker.py']
DATA_FILES = []

# --- py2app Options ---
# This dictionary contains all the configurations for py2app to build the app correctly.
OPTIONS = {
    # 'argv_emulation': False
    # This is the critical fix. The original value 'True' relies on the obsolete
    # 'Carbon' framework, which no longer exists in modern macOS, causing the crash.
    'argv_emulation': False,

    # 'packages': [...]
    # Explicitly tells py2app to include these entire packages in the app bundle.
    'packages': ['rumps', 'pynput', 'requests'],

    # 'includes': [...]
    # Explicitly includes specific macOS frameworks and Python modules.
    # - Quartz is required by 'pynput' for listening to keyboard and mouse events.
    # - 'imp' is a deprecated module required by this version of pyobjc, but is not
    #   found automatically by py2app. Including it resolves the ModuleNotFoundError.
    'includes': ['AppKit', 'Foundation', 'Quartz', 'imp'],

    # 'iconfile': ...
    # Specifies the application icon.
    # Note: The original JPG will not work; py2app requires a .icns file.
    # A default icon will be used, which does not affect functionality.
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
EOF
    echo "setup.py created successfully."

    # Build the application using the new setup.py
    echo "Building the app..."
    python setup.py py2app

    # --- Final Check and Launch ---
    if [ -d "dist/MagicClone.app" ]; then
        echo "Build successful!"
        # The xattr -cr command is run again on the final bundle as a safeguard.
        echo "Final cleaning of the app bundle..."
        xattr -cr dist/MagicClone.app
        
        # Remove any old version from /Applications and copy the new one
        rm -rf /Applications/MagicClone.app
        cp -R dist/MagicClone.app /Applications/
        echo "App built and copied to /Applications/MagicClone.app"
        echo "Launching the app..."
        open /Applications/MagicClone.app
    else
        echo "Build failed. Check for errors above."
    fi

    echo "Setup complete!"
    echo "If the app launched, grant Accessibility permissions when prompted."

    # Exit the virtual environment
    deactivate
}

# --- User Interface ---
# Displays a friendly pop-up message to the user using AppleScript.
show_startup_message() {
    osascript -e 'display dialog "✨ The cloning process is about to begin.  By your third sip of coffee, we can get started 🪄" with title "MagicClone Setup" buttons {"Begin Installation"} default button "Begin Installation"'
}

# --- Script Execution ---

# 1. Show the initial message to the user.
show_startup_message

# 2. Run the main build process in the background.
# The '&' at the end sends the function to run in the background.
# All output (stdout and stderr) is redirected to /dev/null to keep the terminal clean.
run_build_process > /dev/null 2>&1 &

# The terminal will immediately return to the user's prompt,
# while the installation happens silently in the background.
