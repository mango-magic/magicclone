import time
import json
import os
import threading
import subprocess
import requests
import rumps
import uuid
import mss
import pytesseract
import webbrowser
from PIL import Image

# --- Configuration ---
N8N_WEBHOOK_URL = 'https://automations.manymangoes.com.au/webhook/f846efd5-6f36-4d5e-9dd9-b69e128f04da'
N8N_NOTIFY_URL = 'YOUR_NEW_N8N_WEBHOOK_URL_HERE' 
LOG_FILE = 'activity.log'
ARCHIVE_DIR = 'activity_archives'
CONFIG_FILE = 'config.json'
SEND_INTERVAL = 900  # 15 minutes
POLL_INTERVAL = 60   # Check for notifications every 60 seconds
OCR_INTERVAL = 30    # Capture screen text every 30 seconds

# --- Icon Files ---
ICON_ACTIVE = 'icon_active.png'
ICON_INACTIVE = 'icon_inactive.png'

# --- Global State ---
current_word = ''
active_app = None
tracking_active = False
USER_ID = None

# --- Setup ---
os.makedirs(ARCHIVE_DIR, exist_ok=True)
if not os.path.exists(LOG_FILE):
    open(LOG_FILE, 'w').close()

def load_or_create_user_id():
    global USER_ID
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            USER_ID = json.load(f).get('user_id')
    if not USER_ID:
        USER_ID = str(uuid.uuid4())
        with open(CONFIG_FILE, 'w') as f:
            json.dump({'user_id': USER_ID}, f)

# --- Core Functions ---

def capture_screen_text():
    """Captures a screenshot and uses OCR to extract text."""
    if not tracking_active: return
    try:
        with mss.mss() as sct:
            monitor_number = 1
            mon = sct.monitors[monitor_number]
            sct_img = sct.grab(mon)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            text = pytesseract.image_to_string(img)
            
            if text and text.strip():
                log_action('screen_text', text.strip())
                
    except Exception as e:
        print(f"OCR failed: {e}")

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
    from pynput import keyboard
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
            pass

def log_action(action_type, data, app_override=None, url_override=None):
    if not tracking_active: return
    
    app_name = app_override if app_override is not None else (active_app or 'Unknown')
    url = url_override if url_override is not None else get_browser_url(app_name)

    entry = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'app': app_name,
        'action': action_type,
        'data': data,
        'url': url
    }
    with open(LOG_FILE, 'a') as f:
        f.write(json.dumps(entry) + '\n')

def monitor_apps():
    global active_app, current_word
    from AppKit import NSWorkspace
    while True:
        if tracking_active:
            new_app = (NSWorkspace.sharedWorkspace().frontmostApplication().localizedName() or 'Unknown')
            if new_app != active_app:
                if current_word:
                    previous_url = get_browser_url(active_app)
                    log_action('typed_word', current_word, app_override=active_app, url_override=previous_url)
                    current_word = ''
                
                log_action('app_switch', new_app)
                active_app = new_app
        time.sleep(1)

def send_to_webhook():
    if not os.path.exists(LOG_FILE) or os.stat(LOG_FILE).st_size == 0: return
    try:
        with open(LOG_FILE, 'r') as f:
            logs = [json.loads(line.strip()) for line in f if line.strip()]
        
        payload = {'user_id': USER_ID, 'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'), 'logs': logs}
        requests.post(N8N_WEBHOOK_URL, json=payload)
        
        dated_file = os.path.join(ARCHIVE_DIR, f'activity_{time.strftime("%Y%m%d_%H%M%S")}.log')
        os.rename(LOG_FILE, dated_file)
        open(LOG_FILE, 'w').close()
    except Exception as e:
        print(f"Webhook send failed: {e}")

def check_for_notifications(timer):
    if not N8N_NOTIFY_URL or 'YOUR_NEW_N8N_WEBHOOK_URL' in N8N_NOTIFY_URL:
        return
    try:
        params = {'user_id': USER_ID}
        response = requests.get(N8N_NOTIFY_URL, params=params, timeout=10)
        
        if response.status_code == 200:
            for notification in response.json():
                rumps.notification(
                    title=notification.get('title', 'New Message from Magic Clone'),
                    message=notification.get('body', '')
                )
    except requests.RequestException as e:
        print(f"Could not check for notifications: {e}")

# --- Main Application Class ---
class WorkflowTrackerApp(rumps.App):
    def __init__(self):
        super(WorkflowTrackerApp, self).__init__("Mango Clone", quit_button=None)
        load_or_create_user_id()
        self.icon = ICON_INACTIVE
        
        def open_link(sender):
            webbrowser.open(sender.url)

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

        self.menu['My Automations'].url = 'https://setup.manymangoes.com.au/automations'
        self.menu['Help & Resources']['Quickstart Guide'].url = 'https://setup.manymangoes.com.au/quickstart'
        self.menu['Help & Resources']['Documentation'].url = 'https://setup.manymangoes.com.au/docs'
        self.menu['Help & Resources']['Courses'].url = 'https://setup.manymangoes.com.au/courses'
        self.menu['Help & Resources']['Community Forum'].url = 'https://setup.manymangoes.com.au/forum'
        self.menu['About Mango Clone'].url = 'https://setup.manymangoes.com.au/about'
        self.menu['Report a Bug'].url = 'https://setup.manymangoes.com.au/report-bug'
        
        from pynput import keyboard
        self.listener = keyboard.Listener(on_press=on_press)
        self.app_thread = threading.Thread(target=monitor_apps, daemon=True)
        self.app_thread.start()
        self.send_timer = rumps.Timer(send_to_webhook, SEND_INTERVAL)
        self.notification_poll_timer = rumps.Timer(check_for_notifications, POLL_INTERVAL)
        self.ocr_timer = rumps.Timer(lambda _: capture_screen_text(), OCR_INTERVAL)
        self.start_tracking(None)

    def start_tracking(self, _):
        global tracking_active
        if tracking_active: return
        tracking_active = True
        self.icon = ICON_ACTIVE
        if not self.listener.is_alive():
            self.listener.start()
        self.send_timer.start()
        self.notification_poll_timer.start()
        self.ocr_timer.start()

    def pause_tracking(self, _):
        global tracking_active
        if not tracking_active: return
        tracking_active = False
        self.icon = ICON_INACTIVE
        self.listener.stop()
        from pynput import keyboard
        self.listener = keyboard.Listener(on_press=on_press)
        self.send_timer.stop()
        self.notification_poll_timer.stop()
        self.ocr_timer.stop()

    def open_log_directory(self, _):
        log_dir_path = os.path.abspath(ARCHIVE_DIR)
        subprocess.run(['open', log_dir_path])

if __name__ == "__main__":
    WorkflowTrackerApp().run()
