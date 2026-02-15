# plugins/context_switcher.py
import os
import sqlite3
import subprocess
from datetime import datetime
from plugins.base import Plugin

DB_PATH = os.path.expanduser("~/myclaw/context_switcher.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS contexts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            project TEXT,
            summary TEXT,
            open_files TEXT,
            last_commands TEXT,
            git_status TEXT,
            notes TEXT,
            active INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

def get_open_files():
    try:
        result = subprocess.run(
            "lsof -u $(whoami) 2>/dev/null | grep -E \\.py|\\.js|\\.md | awk '{print $9}' | sort -u | head -10",
            shell=True, capture_output=True, text=True
        )
        files = []
        for line in result.stdout.strip().split("\n"):
            if line and os.path.exists(line):
                files.append(os.path.basename(line))
        return ", ".join(files[:5]) if files else "none detected"
    except:
        return "none detected"

def get_recent_commands():
    try:
        history_file = os.path.expanduser("~/.zsh_history")
        if not os.path.exists(history_file):
            history_file = os.path.expanduser("~/.bash_history")
        if not os.path.exists(history_file):
            return "history not available"
        with open(history_file, "rb") as f:
            content = f.read().decode("utf-8", errors="ignore")
        lines = content.strip().split("\n")
        commands = []
        for line in reversed(lines):
            line = line.strip()
            if line.startswith(":"):
                parts = line.split(";", 1)
                if len(parts) > 1:
                    line = parts[1].strip()
            if line and not line.startswith("#") and len(line) > 3:
                if line not in commands:
                    commands.append(line)
            if len(commands) >= 5:
                break
        return " | ".join(commands) if commands else "none"
    except:
        return "none"

def get_git_context():
    try:
        path = os.path.expanduser("~/myclaw")
        result = subprocess.run(
            "git status --short 2>/dev/null",
            shell=True, capture_output=True, text=True, cwd=path
        )
        branch = subprocess.run(
            "git branch --show-current 2>/dev/null",
            shell=True, capture_output=True, text=True, cwd=path
        )
        status = result.stdout.strip()
        br = branch.stdout.strip()
        if status:
            lines = status.split("\n")
            return "branch:" + br + " | " + str(len(lines)) + " modified files"
        return "branch:" + br + " | clean"
    except:
        return "no git info"

def detect_current_project():
    try:
        home = os.path.expanduser("~")
        projects = []
        for name in os.listdir(home):
            path = os.path.join(home, name)
            if os.path.isdir(path) and os.path.exists(os.path.join(path, ".git")):
                mtime = os.path.getmtime(path)
                projects.append((name, mtime, path))
        if projects:
            projects.sort(key=lambda x: x[1], reverse=True)
            return projects[0][0], projects[0][2]
        return "unknown", home
    except:
        return "unknown", os.path.expanduser("~")

def save_context(project_name=None, notes=""):
    try:
        if not project_name:
            project_name, _ = detect_current_project()
        open_files = get_open_files()
        last_commands = get_recent_commands()
        git_status = get_git_context()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        summary_parts = []
        if open_files != "none detected":
            summary_parts.append("working on " + open_files)
        if git_status != "no git info":
            summary_parts.append(git_status)
        if notes:
            summary_parts.append(notes)
        summary = " | ".join(summary_parts) if summary_parts else "general work session"
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE contexts SET active = 0")
        c.execute("""
            INSERT INTO contexts
            (timestamp, project, summary, open_files, last_commands, git_status, notes, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """, (timestamp, project_name, summary, open_files, last_commands, git_status, notes))
        conn.commit()
        conn.close()
        return (
            "Context saved for " + project_name + "\n\n"
            "Snapshot:\n"
            "- Files: " + open_files + "\n"
            "- Git: " + git_status + "\n"
            "- Last commands: " + last_commands[:100] + "\n"
            "- Time: " + timestamp
        )
    except Exception as e:
        return "Error saving context: " + str(e)

def load_context(project_name=None):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        if project_name:
            c.execute("""
                SELECT timestamp, project, summary, open_files, last_commands, git_status, notes
                FROM contexts WHERE project LIKE ? ORDER BY timestamp DESC LIMIT 1
            """, ("%" + project_name + "%",))
        else:
            c.execute("""
                SELECT timestamp, project, summary, open_files, last_commands, git_status, notes
                FROM contexts ORDER BY timestamp DESC LIMIT 1
            """)
        row = c.fetchone()
        conn.close()
        if not row:
            return "No saved context found. Say save context first."
        timestamp, project, summary, open_files, last_commands, git_status, notes = row
        saved_time = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        delta = datetime.now() - saved_time
        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        time_ago = (str(hours) + "h " + str(minutes) + "m ago") if hours > 0 else (str(minutes) + "m ago")
        result = "*Restoring Context: " + project + "*\n"
        result += "Saved: " + time_ago + "\n\n"
        result += "When you left off:\n"
        result += "- Summary: " + summary + "\n"
        result += "- Files: " + open_files + "\n"
        result += "- Git: " + git_status + "\n"
        result += "- Last commands: " + last_commands[:150] + "\n"
        if notes:
            result += "- Notes: " + notes + "\n"
        result += "\nPick up right where you left off!"
        return result
    except Exception as e:
        return "Error loading context: " + str(e)

def list_contexts():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT timestamp, project, summary FROM contexts ORDER BY timestamp DESC LIMIT 10")
        rows = c.fetchall()
        conn.close()
        if not rows:
            return "No contexts saved yet."
        result = "*Saved Contexts:*\n\n"
        for timestamp, project, summary in rows:
            saved_time = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            delta = datetime.now() - saved_time
            hours = int(delta.total_seconds() // 3600)
            if hours > 24:
                time_ago = str(hours // 24) + "d ago"
            elif hours > 0:
                time_ago = str(hours) + "h ago"
            else:
                time_ago = str(int(delta.total_seconds() // 60)) + "m ago"
            result += project + " — " + time_ago + "\n"
            result += "  " + summary[:80] + "\n\n"
        return result
    except Exception as e:
        return "Error: " + str(e)

class ContextSwitcherPlugin(Plugin):
    name = "CONTEXT_SWITCH"
    description = (
        "AI context switcher. Save your current work context and restore it later. "
        "Never lose track of what you were working on when switching projects or taking breaks."
    )
    triggers = [
        "save context", "restore context", "load context",
        "switching to", "switch to", "what was i working on",
        "where was i", "show contexts", "list contexts",
        "taking a break", "resume", "pick up where",
        "context snapshot", "my contexts"
    ]

    def execute(self, value: str) -> tuple:
        try:
            val = value.lower().strip()
            if any(w in val for w in ["list context", "show context", "my context"]):
                return list_contexts(), None
            if any(w in val for w in ["restore", "load context", "where was i",
                                       "what was i working on", "resume", "pick up"]):
                project = None
                skip = ["restore", "load", "context", "what", "was", "i",
                        "working", "on", "where", "resume", "pick", "up"]
                for word in val.split():
                    if word not in skip and len(word) > 2:
                        project = word
                        break
                return load_context(project), None
            if any(w in val for w in ["switching to", "switch to"]):
                to_project = val
                for word in ["switching", "switch", "to", "now", "context"]:
                    to_project = to_project.replace(word, "").strip()
                save_context()
                return load_context(to_project), None
            notes = ""
            for phrase in ["save context", "save my context",
                           "taking a break", "context snapshot"]:
                if phrase in val:
                    notes = val.replace(phrase, "").strip()
                    break
            project, _ = detect_current_project()
            return save_context(project, notes), None
        except Exception as e:
            return "Context switcher error: " + str(e), None
