{\rtf1\ansi\ansicpg1252\cocoartf2822
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 #!/bin/bash\
\
# Install dependencies if not already (safe to rerun)\
pip3 install -r requirements.txt\
\
# Build the app\
echo "Building the app..."\
python3 setup.py py2app\
\
if [ -d "dist/WorkflowTracker.app" ]; then\
    cp -R dist/WorkflowTracker.app /Applications/\
    echo "App built and copied to /Applications/WorkflowTracker.app"\
    echo "Launching the app..."\
    open /Applications/WorkflowTracker.app\
else\
    echo "Build failed. Check for errors above."\
fi\
\
echo "Setup complete! The app is now in your Applications folder. Double-click to run it anytime."\
echo "Grant Accessibility permissions when prompted in System Settings > Privacy & Security > Accessibility."}