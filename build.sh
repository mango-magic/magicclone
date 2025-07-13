#!/bin/bash

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install Homebrew if not present (may prompt for password)
if ! command_exists brew; then
    echo "Homebrew not found. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # Add Homebrew to PATH (in case not already)
    eval "$(/opt/homebrew/bin/brew shellenv)"
fi

# Update Homebrew
echo "Updating Homebrew..."
brew update

# Install Python 3.11 if not present (py2app compatible; may prompt for password)
if ! command_exists python3.11; then
    echo "Python 3.11 not found. Installing via Homebrew..."
    brew install python@3.11
fi

# Use Homebrew's Python 3.11
PYTHON_BIN="/opt/homebrew/bin/python3.11"

# Create venv if not exists (avoids global pip issues)
if [ ! -d "venv" ]; then
    $PYTHON_BIN -m venv venv
fi
source venv/bin/activate

# Install dependencies if not already (safe to rerun)
pip install -r requirements.txt

# Build the app
echo "Building the app..."
$PYTHON_BIN setup.py py2app

if [ -d "dist/MagicClone.app" ]; then
    cp -R dist/MagicClone.app /Applications/
    echo "App built and copied to /Applications/MagicClone.app"
    echo "Launching the app..."
    open /Applications/MagicClone.app
else
    echo "Build failed. Check for errors above."
fi

echo "Setup complete! The app is now in your Applications folder. Double-click to run it anytime."
echo "Grant Accessibility permissions when prompted in System Settings > Privacy & Security > Accessibility."

# Exit venv
deactivate
