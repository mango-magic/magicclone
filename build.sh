#!/bin/bash

# This script automates the setup and build process for the MagicClone Workflow Tracker.
# It runs directly in the terminal to ensure a stable build environment.

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

PYTHON_BIN="/opt/homebrew/bin/python3.11"

# --- Build Preparation ---
echo "Preparing a clean build environment..."
rm -rf build dist

if [ ! -d "venv" ]; then
    $PYTHON_BIN -m venv venv
fi
source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

# --- Create Correct setup.py ---
echo "Creating correct setup.py configuration..."
cat << EOF > setup.py
from setuptools import setup

APP = ['workflow_tracker.py']
# Include both icon files in the application bundle
DATA_FILES = ['Magic Clone.png', 'Mango Clone Inactive.png']
OPTIONS = {
    'argv_emulation': False,
    'packages': ['rumps', 'pynput', 'requests'],
    'includes': ['AppKit', 'Foundation', 'Quartz', 'imp'],
    'iconfile': 'Magic Clone.png', # Main app icon in Finder
    'plist': {
        'CFBundleDisplayName': 'MagicClone',
        'CFBundleName': 'MagicClone',
        'LSUIElement': True,
    }
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
EOF
echo "setup.py created successfully."

# --- Build the App ---
echo "Building the app..."
# Explicitly use the python from the virtual environment.
./venv/bin/python setup.py py2app

# --- Final Check and Launch ---
if [ -d "dist/MagicClone.app" ]; then
    echo "Build successful!"
    rm -rf /Applications/MagicClone.app
    cp -R dist/MagicClone.app /Applications/
    echo "App built and copied to /Applications/MagicClone.app"
    echo "Launching the app..."
    open /Applications/MagicClone.app
else
    echo "Build failed. Check for errors above."
fi

echo "Setup complete. Please grant Accessibility permissions when prompted."
deactivate
