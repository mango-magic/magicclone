{\rtf1\ansi\ansicpg1252\cocoartf2822
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 import time\
import json\
import os\
import threading\
import subprocess\
import requests  # pip install requests\
import rumps  # pip install rumps\
import plistlib\
from AppKit import NSAppleScript, NSWorkspace, NSBundle  # Requires pyobjc: pip install pyobjc\
from pynput import keyboard\
\
# Magic Clone webhook URL\
N8N_WEBHOOK_URL = 'https://automations.manymangoes.com.au/webhook/f846efd5-6f36-4d5e-9dd9-b69e128f04da'  # Your provided URL\
\
log_file = 'activity.log'  # Local JSON lines file\
archive_dir = 'activity_archives'  # Folder for archived logs\
current_word = ''  # Buffer for typed words\
active_app = None\
SEND_INTERVAL = 900  # 15 minutes in seconds\
tracking_active = False\
last_send_time = None\
\
# Ensure directories exist\
os.makedirs(archive_dir, exist_ok=True)\
if not os.path.exists(log_file):\
    open(log_file, 'w').close()\
\
# Function to get current URL if browser is active\
def get_browser_url(app_name):\
    if 'Safari' in app_name:\
        script = 'tell application "Safari" to return URL of current tab of window 1'\
    elif 'Chrome' in app_name:\
        script = 'tell application "Google Chrome" to return URL of active tab of window 1'\
    else:\
        return None\
    try:\
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)\
        return result.stdout.strip()\
    except:\
        return None\
\
# Keystroke listener\
def on_press(key):\
    global current_word\
    if not tracking_active:\
        return\
    try:\
        char = key.char\
        if char:\
            current_word += char\
    except AttributeError:\
        # Special keys (e.g., space, enter) end word\
        if key == keyboard.Key.space or key == keyboard.Key.enter:\
            if current_word:\
                log_action('typed_word', current_word)\
                current_word = ''\
        else:\
            log_action('keystroke', str(key))\
\
# Log action to file\
def log_action(action_type, data, url=None):\
    if not tracking_active:\
        return\
    active = NSWorkspace.sharedWorkspace().frontmostApplication().localizedName() or 'Unknown'\
    entry = \{\
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),\
        'app': active,\
        'action': action_type,\
        'data': data,\
        'url': url or get_browser_url(active) if 'browser' in active.lower() else None\
    \}\
    with open(log_file, 'a') as f:\
        f.write(json.dumps(entry) + '\\n')\
\
# Monitor active app changes (runs in thread)\
def monitor_apps():\
    global active_app\
    while tracking_active:\
        new_app = NSWorkspace.sharedWorkspace().frontmostApplication().localizedName() or 'Unknown'\
        if new_app != active_app:\
            log_action('app_switch', new_app)\
            active_app = new_app\
        time.sleep(1)\
\
# Function to send the log data via webhook as JSON\
def send_to_webhook():\
    global last_send_time\
    if not os.path.exists(log_file) or os.stat(log_file).st_size == 0:\
        return\
\
    try:\
        with open(log_file, 'r') as f:\
            logs = [json.loads(line.strip()) for line in f if line.strip()]\
\
        payload = \{\
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),\
            'logs': logs\
        \}\
        response = requests.post(N8N_WEBHOOK_URL, json=payload)\
        response.raise_for_status()\
        last_send_time = time.time()\
\
        # Archive the sent log file locally and create a new one\
        dated_file = os.path.join(archive_dir, f'activity_\{time.strftime("%Y%m%d_%H%M")\}.log')\
        os.rename(log_file, dated_file)\
        open(log_file, 'w').close()\
\
        rumps.notification("Workflow Tracker", "Data Sent!", "Your workflows are being analyzed\'97soon, mundane tasks will automate themselves!")\
\
    except Exception as e:\
        rumps.notification("Workflow Tracker", "Send Failed", f"Error: \{e\}. Check your connection.")\
\
# Function to add app to Login Items (auto-start on login)\
def add_to_login_items():\
    app_path = NSBundle.mainBundle().bundlePath()\
    script = f'''\
    tell application "System Events"\
        if not (exists (login items whose path is "\{app_path\}")) then\
            make login item at end with properties \{\{path:"\{app_path\}", hidden:false\}\}\
        end if\
    end tell\
    '''\
    try:\
        subprocess.run(['osascript', '-e', script], check=True)\
        rumps.notification("Workflow Tracker", "Auto-Start Enabled", "The app will now start automatically on login!")\
    except Exception as e:\
        rumps.alert(title="Error", message=f"Failed to add to Login Items: \{e\}")\
\
# Function to enable daily launch at 5 AM via launch agent\
def enable_daily_start():\
    home = os.path.expanduser('~')\
    agents_dir = os.path.join(home, 'Library', 'LaunchAgents')\
    plist_path = os.path.join(agents_dir, 'com.workflowtracker.daily.plist')\
    app_path = NSBundle.mainBundle().bundlePath()\
\
    if os.path.exists(plist_path):\
        rumps.alert(title="Already Enabled", message="Daily start at 5 AM is already set up.")\
        return\
\
    plist = \{\
        'Label': 'com.workflowtracker.daily',\
        'ProgramArguments': ['/usr/bin/open', '-a', app_path],\
        'StartCalendarInterval': \{\
            'Hour': 5,\
            'Minute': 0\
        \},\
        'RunAtLoad': False\
    \}\
\
    os.makedirs(agents_dir, exist_ok=True)\
    with open(plist_path, 'wb') as f:\
        plistlib.dump(plist, f)\
\
    try:\
        subprocess.run(['launchctl', 'load', plist_path], check=True)\
        rumps.notification("Workflow Tracker", "Daily Start Enabled", "The app will launch at 5 AM every day if your Mac is on!")\
    except Exception as e:\
        rumps.alert(title="Error", message=f"Failed to enable daily start: \{e\}")\
\
class WorkflowTrackerApp(rumps.App):\
    def __init__(self):\
        super(WorkflowTrackerApp, self).__init__("Tracker", quit_button=None)  # Custom quit\
        self.menu = [\
            rumps.MenuItem('Start Tracking', callback=self.start_tracking),\
            rumps.MenuItem('Pause Tracking', callback=self.pause_tracking),\
            rumps.separator,\
            rumps.MenuItem('Enable Auto-Start on Login', callback=lambda _: add_to_login_items()),\
            rumps.MenuItem('Enable Daily Start at 5 AM', callback=lambda _: enable_daily_start()),\
            rumps.separator,\
            rumps.MenuItem('Status', callback=self.show_status),\
            rumps.MenuItem('View Logs Folder', callback=self.view_logs),\
            rumps.MenuItem('About', callback=self.about),\
            rumps.separator,\
            rumps.MenuItem('Quit', callback=self.quit_app)\
        ]\
        self.listener = None\
        self.app_thread = None\
        self.send_timer = rumps.Timer(self.send_callback, SEND_INTERVAL)\
        self.show_consent_dialog()\
\
    def show_consent_dialog(self):\
        message = (\
            "Welcome to Workflow Tracker! We'll capture your common workflows\'97like app switches, typing patterns, and site visits\'97to recreate virtual versions in Magic Clone. "\
            "The goal? Automate those mundane, boring tasks so you can focus on what matters!\\\\n\\\\n"\
            "Data stays local until sent securely via HTTPS to your Magic Clone webhook every 15 minutes. You control everything\'97pause or quit anytime. "\
            "Grant Accessibility for keystrokes when prompted.\\\\n\\\\nDo you agree to start?"\
        )\
        if rumps.alert(title="Workflow Tracker Consent", message=message, ok="Yes, Let's Automate!", cancel="No, Quit") == 0:\
            rumps.quit_application()\
        else:\
            self.menu['Start Tracking'].set_callback(None)  # Disable until started\
            self.start_tracking(None)\
\
    @rumps.clicked('Start Tracking')\
    def start_tracking(self, _):\
        global tracking_active\
        if tracking_active:\
            return\
        tracking_active = True\
        self.listener = keyboard.Listener(on_press=on_press)\
        self.listener.start()\
        self.app_thread = threading.Thread(target=monitor_apps, daemon=True)\
        self.app_thread.start()\
        self.send_timer.start()\
        self.menu['Start Tracking'].title = 'Tracking Active (Resume)'\
        self.menu['Pause Tracking'].set_callback(self.pause_tracking)\
        rumps.notification("Workflow Tracker", "Tracking Started!", "Capturing your workflows\'97get ready to ditch the drudgery!")\
\
    @rumps.clicked('Pause Tracking')\
    def pause_tracking(self, _):\
        global tracking_active\
        tracking_active = False\
        if self.listener:\
            self.listener.stop()\
        self.send_timer.stop()\
        self.menu['Start Tracking'].set_callback(self.start_tracking)\
        self.menu['Start Tracking'].title = 'Resume Tracking'\
        self.menu['Pause Tracking'].set_callback(None)\
        rumps.notification("Workflow Tracker", "Tracking Paused", "Take a break\'97your automations await when you resume.")\
\
    def send_callback(self, timer):\
        send_to_webhook()\
        self.show_status(None)  # Update status after send\
\
    @rumps.clicked('Status')\
    def show_status(self, _):\
        status = "Tracking: " + ("Active" if tracking_active else "Paused")\
        if last_send_time:\
            mins_ago = (time.time() - last_send_time) / 60\
            status += f"\\\\nLast Send: \{mins_ago:.0f\} min ago"\
        else:\
            status += "\\\\nNo sends yet"\
        rumps.alert(title="Status", message=status)\
\
    @rumps.clicked('View Logs Folder')\
    def view_logs(self, _):\
        subprocess.run(['open', archive_dir])\
\
    @rumps.clicked('About')\
    def about(self, _):\
        message = (\
            "Workflow Tracker turns your daily routines into smart Magic Clone automations!\\\\n\\\\n"\
            "By tracking common workflows, we recreate virtual versions of what you do\'97automating the mundane so you never have to. "\
            "Imagine: No more boring tasks, just more time for the fun stuff. You're going to love it!"\
        )\
        rumps.alert(title="About Workflow Tracker", message=message)\
\
    @rumps.clicked('Quit')\
    def quit_app(self, _):\
        if tracking_active:\
            self.pause_tracking(None)\
        rumps.quit_application()\
\
if __name__ == "__main__":\
    WorkflowTrackerApp().run()}