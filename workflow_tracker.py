import time
import json
import os
import threading
import subprocess
import requests
import rumps
import webbrowser
from AppKit import NSWorkspace
from pynput import keyboard

# --- Configuration ---
N8N_WEBHOOK_URL = 'https://automations.manymangoes.com.au/webhook/f846efd5-6f36-4d5e-9dd9-b69e128f04da'
LOG_FILE = 'activity.log'
ARCHIVE_DIR = 'activity_archives'
SEND_INTERVAL = 900  # 15 minutes

# --- Icon Files ---
ICON_ACTIVE = 'icon_active.png'
ICON_INACTIVE = 'icon_inactive.png'

# --- Global State ---
current_word = ''
active_app = None
tracking_active = False

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
    if not os.path.exists(LOG_FILE) or os.stat(LOG_FILE).st_size == 0: return
    try:
        with open(LOG_FILE, 'r') as f:
            logs = [json.loads(line.strip()) for line in f if line.strip()]
        payload = {'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'), 'logs': logs}
        requests.post(N8N_WEBHOOK_URL, json=payload)
        dated_file = os.path.join(ARCHIVE_DIR, f'activity_{time.strftime("%Y%m%d_%H%M%S")}.log')
        os.rename(LOG_FILE, dated_file)
        open(LOG_FILE, 'w').close()
    except Exception as e:
        print(f"Webhook send failed: {e}")

# --- Main Application Class ---
class WorkflowTrackerApp(rumps.App):
    def __init__(self):
        super(WorkflowTrackerApp, self).__init__("Mango Clone", quit_button=None) # Quit button handled manually
        self.icon = ICON_INACTIVE
        
        # --- Menu Callbacks ---
        def open_link(sender):
            webbrowser.open(sender.url)

        # --- Menu Structure ---
        self.menu = [
            rumps.MenuItem('Start Tracking', callback=self.start_tracking),
            rumps.MenuItem('Pause Tracking', callback=self.pause_tracking),
            rumps.separator,
            rumps.MenuItem('View Activity Logs', callback=self.open_log_directory),
            rumps.separator,
            rumps.MenuItem('My Automations', callback=open_link),
            ('Help & Resources', [
                rumps.MenuItem('Quickstart Guide', callback=open_link),
                rumps.MenuItem('Documentation', callback=open_link),
                rumps.MenuItem('Courses', callback=open_link),
                rumps.MenuItem('Community Forum', callback=open_link),
            ]),
            rumps.separator,
            rumps.MenuItem('About Mango Clone', callback=open_link),
            rumps.MenuItem('Report a Bug', callback=open_link),
            rumps.separator,
            rumps.MenuItem('Quit', callback=rumps.quit_application)
        ]

        # --- Set URLs for Menu Items ---
        self.menu['My Automations'].url = 'https://setup.manymangoes.com.au/automations'
        self.menu['Help & Resources']['Quickstart Guide'].url = 'https://setup.manymangoes.com.au/quickstart'
        self.menu['Help & Resources']['Documentation'].url = 'https://setup.manymangoes.com.au/docs'
        self.menu['Help & Resources']['Courses'].url = 'https://setup.manymangoes.com.au/courses'
        self.menu['Help & Resources']['Community Forum'].url = 'https://setup.manymangoes.com.au/forum'
        self.menu['About Mango Clone'].url = 'https://setup.manymangoes.com.au/about'
        self.menu['Report a Bug'].url = 'https://setup.manymangoes.com.au/report-bug'

        # --- Initialize Threads and Timers ---
        self.listener = None
        self.app_thread = threading.Thread(target=monitor_apps, daemon=True)
        self.app_thread.start()
        self.send_timer = rumps.Timer(self.send_callback, SEND_INTERVAL)
        self.start_tracking(None)

    def start_tracking(self, _):
        global tracking_active
        if tracking_active: return
        tracking_active = True
        self.icon = ICON_ACTIVE
        self.listener = keyboard.Listener(on_press=on_press)
        self.listener.start()
        self.send_timer.start()

    def pause_tracking(self, _):
        global tracking_active
        if not tracking_active: return
        tracking_active = False
        self.icon = ICON_INACTIVE
        if self.listener:
            self.listener.stop()
        self.send_timer.stop()

    def open_log_directory(self, _):
        log_dir_path = os.path.abspath(ARCHIVE_DIR)
        subprocess.run(['open', log_dir_path])

    def send_callback(self, timer):
        if tracking_active:
            send_to_webhook()

if __name__ == "__main__":
    WorkflowTrackerApp().run()
