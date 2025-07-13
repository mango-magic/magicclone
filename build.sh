#!/bin/bash

# Function to check if command exists
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

# Define the Python binary path
PYTHON_BIN="/opt/homebrew/bin/python3.11"

# Create and activate a virtual environment
if [ ! -d "venv" ]; then
    $PYTHON_BIN -m venv venv
fi
source venv/bin/activate

# Install required Python packages
echo "Installing dependencies..."
pip install -r requirements.txt

# --- CRITICAL FIX: Patch setup.py ---
# This section automatically fixes the known issues in the setup.py file.
echo "Patching setup.py for modern macOS compatibility..."

# Fix 1: Disable 'argv_emulation' to prevent the obsolete Carbon framework error.
# This command finds the line "'argv_emulation': True" and replaces it.
sed -i.bak "s/'argv_emulation': True,/'argv_emulation': False,/" setup.py

# Fix 2: Add 'Quartz' to the 'includes' list, which is required by pynput.
# This command finds the 'includes' line and adds the missing framework.
sed -i.bak "s/'includes': \['AppKit', 'Foundation'\]/'includes': \['AppKit', 'Foundation', 'Quartz'\]/" setup.py

echo "Patching complete."
# --- End of Patch ---


# Build the application using the patched setup.py
echo "Building the app..."
python setup.py py2app

# Check if the build was successful and handle the final app
if [ -d "dist/MagicClone.app" ]; then
    echo "Build successful!"
    # Remove any old version from the Applications folder
    rm -rf /Applications/MagicClone.app
    # Copy the new version
    cp -R dist/MagicClone.app /Applications/
    echo "App built and copied to /Applications/MagicClone.app"
    echo "Launching the app..."
    open /Applications/MagicClone.app
else
    echo "Build failed. Check for errors above."
fi

echo "Setup complete! The app is now in your Applications folder. Double-click to run it anytime."
echo "Grant Accessibility permissions when prompted in System Settings > Privacy & Security > Accessibility."

# Exit the virtual environment
deactivate
