#!/bin/bash

# This script automates the entire setup and build process for the MagicClone Workflow Tracker.
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
# We create the file directly to guarantee correctness.
echo "Creating correct setup.py configuration..."
cat << EOF > setup.py
from setuptools import setup

# --- Application Details ---
APP = ['workflow_tracker.py']
# Include both icon files in the application bundle
DATA_FILES = ['Magic Clone.png', 'Mango Clone Inactive.png']

# --- py2app Options ---
# This dictionary contains all the configurations for py2app to build the app correctly.
OPTIONS = {
    'argv_emulation': False,
    'packages': ['rumps', 'pynput', 'requests'],
    'includes': ['AppKit', 'Foundation', 'Quartz', 'imp'],
    'iconfile': 'Magic Clone.png', # Main app icon in Finder
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
