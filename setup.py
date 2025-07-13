{\rtf1\ansi\ansicpg1252\cocoartf2822
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 from setuptools import setup\
\
APP = ['workflow_tracker.py']  # Use the filename of your main script\
DATA_FILES = []\
OPTIONS = \{\
    'argv_emulation': True,\
    'packages': ['rumps', 'pynput', 'pyobjc', 'requests'],\
    'includes': ['AppKit', 'Foundation'],  # Added Foundation if needed\
    'plist': \{\
        'CFBundleDisplayName': 'Workflow Tracker',\
        'CFBundleName': 'WorkflowTracker'\
    \}\
\}\
\
setup(\
    app=APP,\
    data_files=DATA_FILES,\
    options=\{'py2app': OPTIONS\},\
    setup_requires=['py2app'],\
)}