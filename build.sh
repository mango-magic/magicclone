#!/bin/bash

# Check if Python 3 is installed (avoids running the macOS stub to prevent installer prompt)
if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 is not installed. Please install it from https://www.python.org/downloads/ or via Homebrew (brew install python)."
    exit 1
elif [ -x /usr/bin/python3 ] && strings /usr/bin/python3 2>/dev/null | grep -q "Command Line Developer Tools"; then
    echo "Python 3 is not fully installed (macOS stub detected). Please run 'python3' in Terminal to install via Command Line Tools, or use https://www.python.org/downloads/ or Homebrew (brew install python)."
    exit 1
fi

# Create venv if not exists (avoids global pip issues)
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# Install dependencies if not already (safe to rerun)
pip install -r requirements.txt

# Build the app
echo "Building the app..."
python setup.py py2app

if [ -d "dist/WorkflowTracker.app" ]; then
    cp -R dist/WorkflowTracker.app /Applications/
    echo "App built and copied to /Applications/WorkflowTracker.app"
    echo "Launching the app..."
    open /Applications/WorkflowTracker.app
else
    echo "Build failed. Check for errors above."
fi

echo "Setup complete! The app is now in your Applications folder. Double-click to run it anytime."
echo "Grant Accessibility permissions when prompted in System Settings > Privacy & Security > Accessibility."

deactivate  # Exit venv