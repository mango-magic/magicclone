import time
import json
import os
import threading
import subprocess
import requests
import rumps
import plistlib
from AppKit import NSAppleScript, NSWorkspace, NSBundle
from pynput import keyboard

# --- Configuration ---
N8N_WEBHOOK_URL = 'https://automations.manymangoes.com.au/webhook/f846efd5-6f36-4d5e-9dd9-b69e128f04da'
ACTIVE_ICON = 'Magic Clone.png'
INACTIVE_ICON = 'Mango Clone Inactive.png'
LOG_FILE = 'activity.log'
ARCHIVE_DIR = 'activity_archives'
SEND_INTERVAL = 900  # 15 minutes

# --- Global State ---
current_word = ''
active_app = None
tracking_active = False
last_send_time = None

# --- Setup ---
os.makedirs(ARCHIVE_DIR, exist_ok=True)
if not os.path.exists(LOG_FILE):
    open(LOG_FILE, 'w').close()

# --- Core Functions ---

def get_browser_url(app_name):
    script = None
    if 'Safari' in app_name:
        script = 'tell application "Safari" to return URL of current tab of window 1'
    elif 'Chrome' in app_name:
        script = 'tell application "Google Chrome" to return URL of active tab of window 1'
    
    if not script:
        return None
        
    try:
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, check=False)
        return result.stdout.strip()
    except Exception:
        return None

def on_press(key):
    global current_word
    if not tracking_active: return
    try:
        if key.char:
            current_word += key.char
    except AttributeError:
        if key in [keyboard.Key.space, keyboard.Key.enter]:
            if current_word:
                log_action('typed_word', current_word)
                current_word = ''
        else:
            log_action('keystroke', str(key))

def log_action(action_type, data):
    if not tracking_active: return
    
    active_app_name = (NSWorkspace.sharedWorkspace().frontmostApplication().localizedName() or 'Unknown')
    url = get_browser_url(active_app_name)
    
    entry = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'app': active_app_name,
        'action': action_type,
        'data': data,
        'url': url
    }
    with open(LOG_FILE, 'a') as f:
        f.write(json.dumps(entry) + '\n')

def monitor_apps():
    global active_app
    while True:
        if tracking_active:
            new_app = (NSWorkspace.sharedWorkspace().frontmostApplication().localizedName() or 'Unknown')
            if new_app != active_app:
                log_action('app_switch', new_app)
                active_app = new_app
        time.sleep(1)

def send_to_webhook():
    global last_send_time
    if not os.path.exists(LOG_FILE) or os.stat(LOG_FILE).st_size == 0: return
    try:
        with open(LOG_FILE, 'r') as f:
            logs = [json.loads(line.strip()) for line in f if line.strip()]
        
        payload = {'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'), 'logs': logs}
        requests.post(N8N_WEBHOOK_URL, json=payload).raise_for_status()
        last_send_time = time.time()
        
        dated_file = os.path.join(ARCHIVE_DIR, f'activity_{time.strftime("%Y%m%d_%H%M%S")}.log')
        os.rename(LOG_FILE, dated_file)
        open(LOG_FILE, 'w').close()
        rumps.notification("Workflow Tracker", "Data Sent!", "Your workflows are being analyzed!")
    except Exception as e:
        rumps.notification("Workflow Tracker", "Send Failed", f"Error: {e}. Check connection.")

def add_to_login_items():
    app_path = NSBundle.mainBundle().bundlePath()
    script = f'tell application "System Events" to make login item at end with properties {{path:"{app_path}", hidden:false}}'
    try:
        subprocess.run(['osascript', '-e', script], check=True)
    except Exception as e:
        print(f"Could not add to login items: {e}")

# --- Main Application Class ---

class WorkflowTrackerApp(rumps.App):
    def __init__(self):
        super(WorkflowTrackerApp, self).__init__("MagicClone", icon=INACTIVE_ICON, quit_button=None)
        self.menu = [
            rumps.MenuItem('Start Tracking', callback=self.start_tracking),
            rumps.MenuItem('Pause Tracking', callback=self.pause_tracking),
            rumps.separator,
            rumps.MenuItem('Status', callback=self.show_status),
            rumps.MenuItem('View Logs Folder', callback=self.view_logs),
            rumps.MenuItem('About', callback=self.about),
            rumps.separator,
            rumps.MenuItem('Quit', callback=self.quit_app)
        ]
        self.listener = None
        self.app_thread = threading.Thread(target=monitor_apps, daemon=True)
        self.app_thread.start()
        self.send_timer = rumps.Timer(self.send_callback, SEND_INTERVAL)
        self.show_consent_dialog()

    def show_consent_dialog(self):
        message = (
            "Welcome to Workflow Tracker! We'll capture your common workflows to help automate mundane tasks in Magic Clone.\n\n"
            "Data stays local and is sent securely every 15 minutes. The app will start automatically on login. You can pause or quit anytime.\n\n"
            "Please grant Accessibility permissions when prompted.\n\nDo you agree to start?"
        )
        response = rumps.alert(title="Workflow Tracker Consent", message=message, ok="Yes, Let's Automate!", cancel="No, Quit")
        if response == 1:
            add_to_login_items()
            self.start_tracking(None)
        else:
            rumps.quit_application()

    def start_tracking(self, _):
        global tracking_active
        if tracking_active: return
        tracking_active = True
        self.icon = ACTIVE_ICON
        self.listener = keyboard.Listener(on_press=on_press)
        self.listener.start()
        self.send_timer.start()
        self.menu['Start Tracking'].set_callback(None)
        self.menu['Pause Tracking'].set_callback(self.pause_tracking)
        rumps.notification("Workflow Tracker", "Tracking Started!", "Capturing your workflows.")

    def pause_tracking(self, _):
        global tracking_active
        if not tracking_active: return
        tracking_active = False
        self.icon = INACTIVE_ICON
        if self.listener:
            self.listener.stop()
        self.send_timer.stop()
        self.menu['Start Tracking'].set_callback(self.start_tracking)
        self.menu['Pause Tracking'].set_callback(None)
        rumps.notification("Workflow Tracker", "Tracking Paused", "Your automations await when you resume.")

    def send_callback(self, timer):
        if tracking_active:
            send_to_webhook()
            self.show_status(None)

    @rumps.clicked('Status')
    def show_status(self, _):
        status = "Tracking: " + ("Active" if tracking_active else "Paused")
        if last_send_time:
            mins_ago = (time.time() - last_send_time) / 60
            status += f"\nLast Send: {mins_ago:.0f} min ago"
        else:
            status += "\nNo data sent yet."
        rumps.alert(title="Status", message=status)

    @rumps.clicked('View Logs Folder')
    def view_logs(self, _):
        subprocess.run(['open', ARCHIVE_DIR])

    @rumps.clicked('About')
    def about(self, _):
        rumps.alert("Workflow Tracker for Magic Clone", "This app captures your workflows to help automate repetitive tasks.")

    def quit_app(self, _):
        if self.listener and self.listener.is_alive():
            self.listener.stop()
        rumps.quit_application()

if __name__ == "__main__":
    WorkflowTrackerApp().run()
