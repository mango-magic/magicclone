#!/bin/bash

# Install dependencies if not already (safe to rerun)
pip3 install -r requirements.txt

# Build the app
echo "Building the app..."
python3 setup.py py2app

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