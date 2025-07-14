#!/bin/bash

# This script provides a user-friendly installer for the Mango Clone Workflow Tracker.
# It displays a pop-up message and then runs the entire build process silently in the background.

# --- Main Build Logic ---
run_build_process() {
    command_exists() {
        command -v "$1" >/dev/null 2>&1
    }

    # --- Environment Setup ---
    echo "Setting up the build environment..."

    if ! command_exists brew; then
        echo "Homebrew not found. Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi

    echo "Updating Homebrew..."
    brew update

    # Install Python 3.11
    if ! command_exists python3.11; then
        echo "Python 3.11 not found. Installing via Homebrew..."
        brew install python@3.11
    fi

    PYTHON_BIN="/opt/homebrew/bin/python3.11"

    # --- SOURCE CODE CLEANUP ---
    echo "Cleaning extended attributes from the source directory..."
    xattr -cr .

    # --- Build Preparation ---
    echo "Preparing a clean build environment..."
    rm -rf build dist
    if [ ! -d "venv" ]; then
        $PYTHON_BIN -m venv venv
    fi
    source venv/bin/activate

    echo "Installing dependencies from requirements.txt..."
    pip install -r requirements.txt

    # --- Create setup.py configuration ---
    echo "Creating correct setup.py configuration..."
    cat << EOF > setup.py
from setuptools import setup

# --- Application Details ---
APP = ['workflow_tracker.py']
DATA_FILES = ['Magic Clone.png', 'icon_active.png', 'icon_inactive.png']

# --- py2app Options ---
OPTIONS = {
    'argv_emulation': False,
    'packages': ['rumps', 'pynput', 'requests', 'mss', 'PIL'],
    'includes': ['AppKit', 'Foundation', 'Quartz', 'Vision', 'CoreGraphics', 'imp'], # <-- The fix is here
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
EOF
    echo "setup.py created successfully."

    # Build the application
    echo "Building the app..."
    python setup.py py2app

    # --- Final Check and Launch ---
    if [ -d "dist/MangoClone.app" ]; then
        echo "Build successful!"
        xattr -cr dist/MangoClone.app
        rm -rf /Applications/MangoClone.app
        cp -R dist/MangoClone.app /Applications/
        echo "App built and copied to /Applications/MangoClone.app"
        echo "Launching the app..."
        open /Applications/MangoClone.app
    else
        echo "Build failed. Check for errors above."
    fi

    echo "Setup complete!"
    deactivate
}

# --- User Interface ---
show_startup_message() {
    osascript -e 'display dialog "✨ The cloning process is about to begin. Your app is now using Apple’s native OCR for a faster, more reliable experience. By your third sip of coffee, we can get started 🪄" with title "Mango Clone Setup" buttons {"Begin Installation"} default button "Begin Installation"'
}

# --- Script Execution ---
show_startup_message
run_build_process > /dev/null 2>&1 &
