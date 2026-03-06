# plugins/clipboard_watcher.py
# Smart Clipboard Integration
import os
import subprocess
import threading
import time
import re
from plugins.base import Plugin

try:
    import pyperclip
except ImportError:
    pyperclip = None

last_clipboard = ""
clipboard_history = []
MAX_HISTORY = 20

PATTERNS = {
    "github_repo": {
        "regex": r"https://github\.com/[\w-]+/[\w.-]+",
        "actions": ["clone", "star", "read_readme", "open_in_browser"]
    },
    "url": {
        "regex": r"https?://\S+",
        "actions": ["open_in_browser", "download", "archive"]
    },
    "ip_address": {
        "regex": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
        "actions": ["ping", "ssh", "open_in_browser"]
    },
    "file_path": {
        "regex": r"^[~/][\w\-/\.]+\.\w+$",
        "actions": ["open", "move", "info"]
    },
    "error_message": {
        "regex": r"(error|exception|traceback|failed):",
        "actions": ["search_stackoverflow", "save_to_notes"]
    },
    "color_code": {
        "regex": r"#[0-9a-fA-F]{6}",
        "actions": ["show_color", "convert_to_rgb"]
    },
}

def detect_content_type(text):
    text = text.strip()
    if not text:
        return None, []
    for content_type, pattern in PATTERNS.items():
        if re.search(pattern["regex"], text, re.IGNORECASE | re.MULTILINE):
            return content_type, pattern["actions"]
    return "text", ["search_web", "save_to_notes"]

def get_clipboard():
    if not pyperclip:
        return None
    try:
        content = pyperclip.paste()
        return content if content else None
    except:
        return None

def watch_clipboard_loop():
    global last_clipboard
    while True:
        try:
            current = get_clipboard()
            if current and current != last_clipboard and len(current) > 3:
                last_clipboard = current
                clipboard_history.insert(0, {
                    "content": current[:200],
                    "type": detect_content_type(current)[0],
                    "time": time.strftime("%H:%M:%S")
                })
                if len(clipboard_history) > MAX_HISTORY:
                    clipboard_history.pop()
            time.sleep(2)
        except:
            time.sleep(5)

if pyperclip:
    watcher_thread = threading.Thread(target=watch_clipboard_loop, daemon=True)
    watcher_thread.start()

def execute_action(content, action):
    try:
        if action == "clone":
            repo_name = content.split("/")[-1].replace(".git", "")
            path = os.path.expanduser("~/code/" + repo_name)
            os.makedirs(os.path.expanduser("~/code"), exist_ok=True)
            result = subprocess.run("git clone " + content + " " + path, shell=True, capture_output=True, text=True)
            return "Cloned to: " + path if not result.returncode else result.stderr
        elif action == "open_in_browser":
            subprocess.Popen("xdg-open " + content, shell=True)
            return "Opened in browser"
        elif action == "ping":
            result = subprocess.run("ping -c 4 " + content, shell=True, capture_output=True, text=True)
            return result.stdout[:500]
        elif action == "ssh":
            return "To SSH: ssh user@" + content
        elif action == "open":
            subprocess.Popen("xdg-open " + content, shell=True)
            return "Opening: " + content
        elif action == "info":
            if os.path.exists(os.path.expanduser(content)):
                result = subprocess.run("ls -lh " + os.path.expanduser(content), shell=True, capture_output=True, text=True)
                return result.stdout
            return "File not found"
        elif action == "search_stackoverflow":
            query = content.replace(" ", "+")
            url = "https://stackoverflow.com/search?q=" + query
            subprocess.Popen("xdg-open " + url, shell=True)
            return "Searching StackOverflow..."
        elif action == "save_to_notes":
            notes_file = os.path.expanduser("~/myclaw_notes.md")
            with open(notes_file, "a") as f:
                f.write("\n\n" + time.strftime("%Y-%m-%d %H:%M") + "\n" + content + "\n")
            return "Added to notes"
        elif action == "search_web":
            query = content.replace(" ", "+")
            subprocess.Popen("xdg-open https://www.google.com/search?q=" + query, shell=True)
            return "Searching web..."
        elif action == "download":
            download_path = os.path.expanduser("~/Downloads/")
            result = subprocess.run("wget -P " + download_path + " " + content, shell=True, capture_output=True, text=True)
            return "Downloaded to ~/Downloads" if not result.returncode else result.stderr
        elif action == "show_color":
            color = re.search(r"#[0-9a-fA-F]{6}", content)
            if color:
                color = color.group()
                r = int(color[1:3], 16)
                g = int(color[3:5], 16)
                b = int(color[5:7], 16)
                return "Color: " + color + "\nRGB: (" + str(r) + ", " + str(g) + ", " + str(b) + ")"
            return "No color code found"
        elif action == "read_readme":
            import tempfile
            temp_dir = tempfile.mkdtemp()
            subprocess.run("git clone --depth 1 " + content + " " + temp_dir, shell=True, capture_output=True)
            for name in ["README.md", "README", "readme.md"]:
                path = os.path.join(temp_dir, name)
                if os.path.exists(path):
                    with open(path, "r") as f:
                        readme = f.read()[:2000]
                    return "README Preview:\n\n" + readme + "\n\n... (truncated)"
            return "No README found"
        else:
            return "Action '" + action + "' not implemented yet"
    except Exception as e:
        return "Error: " + str(e)

class ClipboardWatcherPlugin(Plugin):
    name = "CLIPBOARD"
    description = "Smart clipboard integration. Auto-detects GitHub repos, URLs, IPs, file paths, errors and offers intelligent actions."
    triggers = ["clipboard", "what did i copy", "clipboard history", "paste", "last copied", "show clipboard"]
    
    def execute(self, value: str) -> tuple:
        try:
            if not pyperclip:
                return "Clipboard watcher not available. Install: pip install pyperclip", None
            val = value.lower().strip()
            if any(w in val for w in ["history", "show clipboard", "what did i copy"]):
                if not clipboard_history:
                    return "Clipboard history is empty.", None
                result = "*Clipboard History:*\n\n"
                for i, item in enumerate(clipboard_history[:10], 1):
                    result += str(i) + ". [" + item["time"] + "] (" + item["type"] + ")\n   " + item["content"][:80] + "\n\n"
                return result, None
            current = get_clipboard()
            if not current:
                return "Clipboard is empty.", None
            content_type, actions = detect_content_type(current)
            result = "*Clipboard Content:*\n" + current[:200] + "\n\n*Detected as:* " + content_type + "\n\n*Available actions:*\n"
            for i, action in enumerate(actions, 1):
                result += str(i) + ". " + action.replace("_", " ").title() + "\n"
            result += "\nTo execute: 'clipboard " + actions[0] + "'"
            for action in actions:
                if action in val or action.replace("_", " ") in val:
                    action_result = execute_action(current, action)
                    return action_result, None
            return result, None
        except Exception as e:
            return "Clipboard error: " + str(e), None
