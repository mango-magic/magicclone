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

# Check Python version (targeting 3.11 for py2app compatibility)
REQUIRED_PYTHON="3.11"
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    if [[ "$(echo -e "$PYTHON_VERSION\n$REQUIRED_PYTHON" | sort -V | head -n1)" != "$REQUIRED_PYTHON" ]]; then
        echo "Python version $PYTHON_VERSION is not 3.11 or newer. Installing Python 3.11..."
        brew install python@3.11
    else
        echo "Python $PYTHON_VERSION is sufficient."
    fi
else
    echo "Python not found. Installing Python 3.11..."
    brew install python@3.11
fi

# Ensure python3.11 is used (Homebrew's version)
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

deactivate  # Exit venv
