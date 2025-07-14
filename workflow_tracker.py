import time
import json
import os
import threading
import subprocess
import requests
import rumps
import uuid
import mss
import webbrowser
from PIL import Image

# Import Apple-specific frameworks for native OCR
from AppKit import NSBitmapImageRep, NSImage
from Quartz import CGImageCreateWithImageInRect, CGMainDisplayID, CGDisplayCreateImage
from Vision import VNRecognizeTextRequest, VNImageRequestHandler

# --- Configuration ---
N8N_WEBHOOK_URL = 'https://automations.manymangoes.com.au/webhook/f846efd5-6f36-4d5e-9dd9-b69e128f04da'
N8N_NOTIFY_URL = 'https://automations.manymangoes.com.au/webhook/d0cd7119-551d-453d-873c-5f9b9c0fd846'
LOG_FILE = 'activity.log'
ARCHIVE_DIR = 'activity_archives'
CONFIG_FILE = 'config.json'
SEND_INTERVAL = 900
POLL_INTERVAL = 60
OCR_INTERVAL = 30

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
    """Loads the user ID from the config file, or creates a new one."""
    global USER_ID
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                USER_ID = json.load(f).get('user_id')
        except (json.JSONDecodeError, AttributeError):
            USER_ID = None # Handle corrupted or empty config file
            
    if not USER_ID:
        USER_ID = str(uuid.uuid4())
        with open(CONFIG_FILE, 'w') as f:
            json.dump({'user_id': USER_ID}, f)

# --- Core Functions ---

def capture_screen_text():
    """Captures the screen and uses native macOS Vision OCR to extract text."""
    if not tracking_active: return
    try:
        # Create a full-screen CGImage
        main_display_id = CGMainDisplayID()
        cg_image = CGDisplayCreateImage(main_display_id)
        if not cg_image:
            print("Could not create screen image.")
            return

        # Create a request handler
        handler = VNImageRequestHandler.alloc().initWithCGImage_options_(cg_image, None)
        
        # Create a text recognition request
        request = VNRecognizeTextRequest.alloc().init()
        request.setRecognitionLevel_(1) # 1 = "accurate", 0 = "fast"
        
        # Perform the request
        success, error = handler.performRequests_error_([request], None)
        if not success:
            print(f"OCR request failed: {error}")
            return
            
        # Process results
        all_text = [
            top_candidate.string()
            for observation in request.results()
            for top_candidate in observation.topCandidates_(1)
        ]
            
        full_text = "\n".join(all_text)
        if full_text and full_text.strip():
            log_action('screen_text', full_text.strip())
            
    except Exception as e:
        print(f"An error occurred during native OCR: {e}")

def get_browser_url(app_name):
    """Gets the URL from the frontmost tab of Safari or Chrome."""
    script = None
    if 'Safari' in app_name:
        script = 'tell application "Safari" to return URL of current tab of window 1'
    elif 'Chrome' in app_name:
        script = 'tell application "Google Chrome" to return URL of active tab of window 1'
    
    if not script: return None
    
    try:
        # Execute the AppleScript and capture the output
        result = subprocess.run(
            ['osascript', '-e', script], 
            capture_output=True, text=True, check=False, timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except (subprocess.TimeoutExpired, Exception) as e:
        print(f"Could not get browser URL: {e}")
        return None

def on_press(key):
    """Handles key press events to log typed words."""
    global current_word
    from pynput import keyboard
    if not tracking_active: return
    
    try:
        if key == keyboard.Key.backspace:
            # Handle backspace by removing the last character
            current_word = current_word[:-1]
            return

        if hasattr(key, 'char') and key.char:
            # Append character to the current word
            current_word += key.char
        elif key in [keyboard.Key.space, keyboard.Key.enter, keyboard.Key.tab]:
            # Log the word when a separator key is pressed
            if current_word:
                log_action('typed_word', current_word)
                current_word = ''
    except Exception as e:
        print(f"Error in on_press: {e}")


def log_action(action_type, data, app_override=None, url_override=None):
    """Logs an action to the log file."""
    if not tracking_active: return
    
    app_name = app_override if app_override is not None else (active_app or 'Unknown')
    url = url_override if url_override is not None else get_browser_url(app_name)

    entry = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'user_id': USER_ID,
        'app': app_name, 
        'action': action_type, 
        'data': data, 
        'url': url
    }
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    except IOError as e:
        print(f"Could not write to log file: {e}")

def monitor_apps():
    """Monitors for application switches and logs the active application."""
    global active_app, current_word
    from AppKit import NSWorkspace
    
    while True:
        if tracking_active:
            try:
                new_app_instance = NSWorkspace.sharedWorkspace().frontmostApplication()
                new_app = new_app_instance.localizedName() if new_app_instance else 'Unknown'
                
                if new_app != active_app:
                    # If there's a pending word, log it before switching context
                    if current_word:
                        log_action('typed_word', current_word, app_override=active_app)
                        current_word = ''
                    
                    active_app = new_app
                    log_action('app_switch', new_app)
            except Exception as e:
                print(f"Error monitoring apps: {e}")
        time.sleep(1) # Check every second

def send_to_webhook(_):
    """Sends the contents of the log file to the webhook and archives it."""
    if not os.path.exists(LOG_FILE) or os.stat(LOG_FILE).st_size == 0:
        return
        
    # Create a unique filename for the archive before sending
    dated_file = os.path.join(ARCHIVE_DIR, f'activity_{time.strftime("%Y%m%d_%H%M%S")}.log')
    
    try:
        # Rename the file first. If sending fails, the data is safe in the archive.
        os.rename(LOG_FILE, dated_file)
        open(LOG_FILE, 'w').close() # Create a new empty log file immediately

        with open(dated_file, 'r') as f:
            logs = [json.loads(line) for line in f if line.strip()]
        
        if not logs: return

        payload = {'user_id': USER_ID, 'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'), 'logs': logs}
        
        response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=20)
        response.raise_for_status() # Raise an exception for bad status codes
        
    except requests.exceptions.RequestException as e:
        print(f"Webhook send failed: A network error occurred: {e}")
        # Note: The file is already archived, so data is not lost.
    except (IOError, json.JSONDecodeError) as e:
        print(f"Error reading or processing log file {dated_file}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred in send_to_webhook: {e}")

def check_for_notifications(timer):
    """Polls the notification webhook for new messages to display."""
    if not N8N_NOTIFY_URL or 'YOUR_NEW_N8N_WEBHOOK_URL' in N8N_NOTIFY_URL: return
    try:
        response = requests.get(N8N_NOTIFY_URL, params={'user_id': USER_ID}, timeout=10)
        if response.status_code == 200:
            for notification in response.json():
                rumps.notification(
                    title=notification.get('title', 'New Message'),
                    subtitle=notification.get('subtitle', ''),
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
        self.listener = None
        
        def open_link(sender):
            if hasattr(sender, 'url'):
                webbrowser.open(sender.url)

        # --- Menu Definition ---
        self.menu = [
            rumps.MenuItem('Start Tracking', callback=self.start_tracking),
            rumps.MenuItem('Pause Tracking', callback=self.pause_tracking),
            rumps.separator,
            ('Manage Permissions', [
                rumps.MenuItem('Grant Permissions...', callback=self.manage_grant_permissions),
                rumps.MenuItem('Revoke Permissions...', callback=self.manage_revoke_permissions),
            ]),
            rumps.separator,
            rumps.MenuItem('View Activity Logs', callback=self.open_log_directory),
            rumps.separator,
            rumps.MenuItem('My Automations', callback=open_link),
            ('Help & Resources', [
                rumps.MenuItem('Quickstart Guide', callback=open_link),
                rumps.MenuItem('Documentation', callback=open_link),
                rumps.MenuItem('Community Forum', callback=open_link),
            ]),
            rumps.separator,
            rumps.MenuItem('About Mango Clone', callback=open_link),
            rumps.MenuItem('Report a Bug', callback=open_link),
            rumps.separator,
            rumps.MenuItem('Quit', callback=rumps.quit_application)
        ]
        
        # Set URLs for menu items that open links
        self.menu['My Automations'].url = 'https://setup.manymangoes.com.au/automations'
        self.menu['Help & Resources']['Quickstart Guide'].url = 'https://setup.manymangoes.com.au/quickstart'
        self.menu['Help & Resources']['Documentation'].url = 'https://setup.manymangoes.com.au/docs'
        self.menu['Help & Resources']['Community Forum'].url = 'https://setup.manymangoes.com.au/forum'
        self.menu['About Mango Clone'].url = 'https://setup.manymangoes.com.au/about'
        self.menu['Report a Bug'].url = 'https://setup.manymangoes.com.au/report-bug'
        
        # --- Timers and Threads ---
        self.app_monitor_thread = threading.Thread(target=monitor_apps, daemon=True)
        self.app_monitor_thread.start()
        
        self.send_timer = rumps.Timer(send_to_webhook, SEND_INTERVAL)
        self.notification_poll_timer = rumps.Timer(check_for_notifications, POLL_INTERVAL)
        self.ocr_timer = rumps.Timer(lambda _: capture_screen_text(), OCR_INTERVAL)
        
        # Start tracking automatically on launch
        self.start_tracking(None)

    def start_tracking(self, _):
        """Starts the key listener and all timers."""
        global tracking_active
        if tracking_active: 
            print("Tracking is already active.")
            return
        
        print("Starting tracking...")
        tracking_active = True
        self.icon = ICON_ACTIVE
        
        from pynput import keyboard
        self.listener = keyboard.Listener(on_press=on_press)
        self.listener.start()
        
        # Send any logs that might exist from a previous session
        send_to_webhook(None)
        
        self.send_timer.start()
        self.notification_poll_timer.start()
        self.ocr_timer.start()

    def pause_tracking(self, _):
        """Stops the key listener and all timers."""
        global tracking_active
        if not tracking_active: 
            print("Tracking is already paused.")
            return

        print("Pausing tracking...")
        tracking_active = False
        self.icon = ICON_INACTIVE
        
        if self.listener: 
            self.listener.stop()
            self.listener = None
        
        self.send_timer.stop()
        self.notification_poll_timer.stop()
        self.ocr_timer.stop()
        
        # On pause, send any remaining logs
        send_to_webhook(None)

    def open_log_directory(self, _):
        """Opens the activity log archive directory in Finder."""
        log_dir_path = os.path.abspath(ARCHIVE_DIR)
        subprocess.run(['open', log_dir_path])

    def manage_grant_permissions(self, _):
        """Shows instructions on how to grant necessary permissions."""
        response = rumps.alert(
            title="Grant Required Permissions",
            message=(
                "For full functionality, Mango Clone needs your permission.\n\n"
                "macOS requires you to manually enable:\n"
                "1.  **Accessibility:** To detect app switches and typed text.\n"
                "2.  **Screen Recording:** To capture on-screen text.\n"
                "3.  **Automation:** To get the URL from your web browser.\n\n"
                "Click 'Open System Settings' to go to the 'Privacy & Security' pane. "
                "You will need to find Mango Clone in each of the sections above and enable it."
            ),
            ok="Open System Settings",
            cancel="Cancel"
        )
        if response == 1: # OK button was clicked
            # This URL opens the main Privacy & Security pane
            webbrowser.open('x-apple.systempreferences:com.apple.preference.security')

    def manage_revoke_permissions(self, _):
        """Shows instructions on how to revoke permissions."""
        response = rumps.alert(
            title="Revoke Permissions",
            message=(
                "To revoke permissions, you must manually disable or remove Mango Clone from the 'Accessibility', 'Screen Recording', and 'Automation' sections in your system's 'Privacy & Security' settings.\n\n"
                "Click 'Open System Settings' to manage your permissions."
            ),
            ok="Open System Settings",
            cancel="Cancel"
        )
        if response == 1: # OK button was clicked
            webbrowser.open('x-apple.systempreferences:com.apple.preference.security')


if __name__ == "__main__":
    app = WorkflowTrackerApp()
    app.run()
