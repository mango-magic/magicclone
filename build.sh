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

# --- CRITICAL FIX: Patch setup.py ---
# This section automatically fixes the known issues in the setup.py file.
echo "Patching setup.py for modern macOS compatibility..."
sed -i.bak "s/'argv_emulation': True,/'argv_emulation': False,/" setup.py
sed -i.bak "s/'includes': \['AppKit', 'Foundation'\]/'includes': \['AppKit', 'Foundation', 'Quartz'\]/" setup.py

echo "--- Verifying Patches ---"
cat setup.py
echo "-------------------------"

# Build the application using the patched setup.py
echo "Building the app..."
python setup.py py2app

# --- DIAGNOSTIC STEP ---
# This section will help us identify the root cause of the launch error.
if [ -d "dist/MagicClone.app" ]; then
    echo "-------------------------------------------------------------"
    echo "BUILD PAUSED FOR DIAGNOSTICS"
    echo "The app has been built but not yet signed or moved."
    echo "Please open a NEW terminal window, navigate to this directory:"
    echo "cd \"$(pwd)\""
    echo "Then run the following command and paste the entire output back to me:"
    echo
    echo "xattr -lr dist/MagicClone.app"
    echo
    read -p "After you have copied the output, press Enter here to continue..."
    # --- End of Diagnostic Step ---

    # --- FINAL FIX: Clean Extended Attributes ---
    echo "Cleaning the app bundle for code signing..."
    xattr -cr dist/MagicClone.app
    # --- End of Final Fix ---

    echo "Build successful!"
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
echo "If it failed again, please provide the output from the diagnostic step."

# Exit the virtual environment
deactivate
