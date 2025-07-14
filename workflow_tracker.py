import time
import json
import os
import threading
import subprocess
import requests
import rumps
import webbrowser
import uuid # Used for the unique ID

# --- Configuration ---
N8N_WEBHOOK_URL = 'https://automations.manymangoes.com.au/webhook/f846efd5-6f36-4d5e-9dd9-b69e128f04da'
# !!! ADD YOUR NEW N8N WEBHOOK URL FOR FETCHING NOTIFICATIONS HERE !!!
N8N_NOTIFY_URL = 'YOUR_NEW_N8N_WEBHOOK_URL_HERE' # e.g., https://automations.manymangoes.com.au/webhook/get-notifications

LOG_FILE = 'activity.log'
ARCHIVE_DIR = 'activity_archives'
CONFIG_FILE = 'config.json'
SEND_INTERVAL = 900  # 15 minutes
POLL_INTERVAL = 60   # Check for notifications every 60 seconds

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
    """Loads a unique user ID from config.json, or creates and saves one if it doesn't exist."""
    global USER_ID
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            USER_ID = config.get('user_id')
    if not USER_ID:
        USER_ID = str(uuid.uuid4())
        with open(CONFIG_FILE, 'w') as f:
            json.dump({'user_id': USER_ID}, f)

# --- Core Functions ---
def get_browser_url(app_name):
    # (This function is unchanged)
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
    # (This function is unchanged)
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
    # (This function is unchanged)
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
    # (This function is unchanged)
    global active_app
    while True:
        if tracking_active:
            new_app = (NSWorkspace.sharedWorkspace().frontmostApplication().localizedName() or 'Unknown')
            if new_app != active_app:
                log_action('app_switch', new_app)
                active_app = new_app
        time.sleep(1)

def send_to_webhook():
    """Sends the activity log to n8n, now including the user ID."""
    if not os.path.exists(LOG_FILE) or os.stat(LOG_FILE).st_size == 0: return
    try:
        with open(LOG_FILE, 'r') as f:
            logs = [json.loads(line.strip()) for line in f if line.strip()]
        
        # Add the unique user ID to the payload
        payload = {'user_id': USER_ID, 'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'), 'logs': logs}
        requests.post(N8N_WEBHOOK_URL, json=payload)
        
        dated_file = os.path.join(ARCHIVE_DIR, f'activity_{time.strftime("%Y%m%d_%H%M%S")}.log')
        os.rename(LOG_FILE, dated_file)
        open(LOG_FILE, 'w').close()
    except Exception as e:
        print(f"Webhook send failed: {e}")

def check_for_notifications(timer):
    """Polls the n8n notification webhook for new messages."""
    if not N8N_NOTIFY_URL or 'YOUR_NEW_N8N_WEBHOOK_URL' in N8N_NOTIFY_URL:
        return # Don't run if the URL isn't set
    try:
        # Ask the webhook for notifications for our specific user ID
        params = {'user_id': USER_ID}
        response = requests.get(N8N_NOTIFY_URL, params=params, timeout=10)
        
        if response.status_code == 200:
            notifications = response.json()
            # The n8n workflow should return a list, even if it's empty
            for notification in notifications:
                rumps.notification(
                    title=notification.get('title', 'New Message from Magic Clone'),
                    subtitle=None,
                    message=notification.get('body', '')
                )
    except requests.RequestException as e:
        print(f"Could not check for notifications: {e}")

# --- Main Application Class ---
class WorkflowTrackerApp(rumps.App):
    def __init__(self):
        super(WorkflowTrackerApp, self).__init__("Mango Clone", quit_button=None)
        load_or_create_user_id() # Ensure we have a user ID on start
        self.icon = ICON_INACTIVE
        self.menu = [
            # (Menu is unchanged)
            rumps.MenuItem('Start Tracking', callback=self.start_tracking),
            rumps.MenuItem('Pause Tracking', callback=self.pause_tracking),
            rumps.separator,
            rumps.MenuItem('View Activity Logs', callback=self.open_log_directory),
            rumps.separator,
            # ... other menu items
        ]
        
        # --- Initialize Threads and Timers ---
        self.listener = None
        self.app_thread = threading.Thread(target=monitor_apps, daemon=True)
        self.app_thread.start()
        self.send_timer = rumps.Timer(self.send_callback, SEND_INTERVAL)
        
        # --- NEW: Timer for polling notifications ---
        self.notification_poll_timer = rumps.Timer(check_for_notifications, POLL_INTERVAL)
        
        self.start_tracking(None)

    def start_tracking(self, _):
        global tracking_active
        if tracking_active: return
        tracking_active = True
        self.icon = ICON_ACTIVE
        self.listener = keyboard.Listener(on_press=on_press)
        self.listener.start()
        self.send_timer.start()
        self.notification_poll_timer.start() # Start polling when tracking starts

    def pause_tracking(self, _):
        global tracking_active
        if not tracking_active: return
        tracking_active = False
        self.icon = ICON_INACTIVE
        if self.listener:
            self.listener.stop()
        self.send_timer.stop()
        self.notification_poll_timer.stop() # Stop polling when paused

    def open_log_directory(self, _):
        # (This function is unchanged)
        log_dir_path = os.path.abspath(ARCHIVE_DIR)
        subprocess.run(['open', log_dir_path])

    def send_callback(self, timer):
        # (This function is unchanged)
        if tracking_active:
            send_to_webhook()

if __name__ == "__main__":
    WorkflowTrackerApp().run()
