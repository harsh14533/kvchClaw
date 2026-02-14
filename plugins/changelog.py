# plugins/changelog.py
# Personal Changelog Plugin
# Watches your project folders and auto-generates
# a daily summary of everything you worked on

import os
import sqlite3
import subprocess
import threading
import time
from datetime import datetime, timedelta
from plugins.base import Plugin

DB_PATH = os.path.expanduser("~/myclaw/changelog.db")

# Folders to watch — customize these
WATCH_FOLDERS = [
    os.path.expanduser("~/myclaw"),
    os.path.expanduser("~/code"),
    os.path.expanduser("~/projects"),
    os.path.expanduser("~/Documents"),
    os.path.expanduser("~/Desktop"),
]

# File extensions to track
TRACK_EXTENSIONS = [
    ".py", ".js", ".ts", ".html", ".css",
    ".java", ".c", ".cpp", ".go", ".rs",
    ".md", ".txt", ".json", ".yaml", ".yml",
    ".sh", ".sql", ".php", ".rb"
]

# ── Database ──────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS file_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            filepath TEXT,
            filename TEXT,
            project TEXT,
            action TEXT,
            size_bytes INTEGER
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS git_commits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            repo TEXT,
            message TEXT,
            files_changed INTEGER
        )
    """)
    conn.commit()
    conn.close()

# ── File Watcher ──────────────────────────────────────────
# Stores last seen state of files
file_cache = {}

def get_project_name(filepath):
    for folder in WATCH_FOLDERS:
        if filepath.startswith(folder):
            relative = filepath[len(folder):].lstrip("/")
            parts = relative.split("/")
            if len(parts) > 1:
                return parts[0]
            return os.path.basename(folder)
    return "other"

def scan_folders():
    global file_cache
    new_cache = {}
    changes = []

    for folder in WATCH_FOLDERS:
        if not os.path.exists(folder):
            continue
        try:
            for root, dirs, files in os.walk(folder):
                # Skip hidden and venv folders
                dirs[:] = [
                    d for d in dirs
                    if not d.startswith(".")
                    and d not in ["venv", "node_modules", "__pycache__", ".git"]
                ]
                for filename in files:
                    ext = os.path.splitext(filename)[1].lower()
                    if ext not in TRACK_EXTENSIONS:
                        continue
                    filepath = os.path.join(root, filename)
                    try:
                        mtime = os.path.getmtime(filepath)
                        size = os.path.getsize(filepath)
                        new_cache[filepath] = {"mtime": mtime, "size": size}

                        if filepath in file_cache:
                            old = file_cache[filepath]
                            if mtime > old["mtime"]:
                                changes.append({
                                    "filepath": filepath,
                                    "filename": filename,
                                    "project": get_project_name(filepath),
                                    "action": "modified",
                                    "size": size
                                })
                        else:
                            # New file
                            today = datetime.now().date()
                            created_time = datetime.fromtimestamp(
                                os.path.getctime(filepath)
                            ).date()
                            if created_time == today:
                                changes.append({
                                    "filepath": filepath,
                                    "filename": filename,
                                    "project": get_project_name(filepath),
                                    "action": "created",
                                    "size": size
                                })
                    except:
                        pass
        except:
            pass

    file_cache = new_cache
    return changes

def scan_git_commits():
    commits = []
    for folder in WATCH_FOLDERS:
        if not os.path.exists(folder):
            continue
        try:
            result = subprocess.run(
                'git log --since="24 hours ago" --oneline --format="%H|%s|%ai"',
                shell=True, capture_output=True,
                text=True, cwd=folder
            )
            if result.stdout.strip():
                for line in result.stdout.strip().split("\n"):
                    if "|" in line:
                        parts = line.split("|")
                        if len(parts) >= 2:
                            commits.append({
                                "repo": os.path.basename(folder),
                                "message": parts[1].strip()
                            })
        except:
            pass
    return commits

def save_changes(changes):
    if not changes:
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for change in changes:
        c.execute("""
            INSERT INTO file_activity
            (timestamp, filepath, filename, project, action, size_bytes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            change["filepath"],
            change["filename"],
            change["project"],
            change["action"],
            change["size"]
        ))
    conn.commit()
    conn.close()

def save_commits(commits):
    if not commits:
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for commit in commits:
        c.execute("""
            INSERT INTO git_commits
            (timestamp, repo, message, files_changed)
            VALUES (?, ?, ?, ?)
        """, (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            commit["repo"],
            commit["message"],
            0
        ))
    conn.commit()
    conn.close()

# ── Background Scanner ────────────────────────────────────
def background_loop():
    init_db()
    # Initial scan to build cache without recording changes
    scan_folders()
    print("Changelog: watching your project folders")

    while True:
        time.sleep(120)  # Check every 2 minutes
        try:
            changes = scan_folders()
            if changes:
                save_changes(changes)
            commits = scan_git_commits()
            if commits:
                save_commits(commits)
        except Exception as e:
            print("Changelog scan error: " + str(e))

changelog_thread = threading.Thread(target=background_loop, daemon=True)
changelog_thread.start()

# ── Report Generator ──────────────────────────────────────
def generate_report(days=1):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

        # Get file activity
        c.execute("""
            SELECT project, filename, action, COUNT(*) as edits
            FROM file_activity
            WHERE timestamp > ?
            GROUP BY project, filename, action
            ORDER BY project, edits DESC
        """, (since,))
        file_rows = c.fetchall()

        # Get git commits
        c.execute("""
            SELECT repo, message
            FROM git_commits
            WHERE timestamp > ?
            ORDER BY timestamp DESC
        """, (since,))
        commit_rows = c.fetchall()

        conn.close()

        if not file_rows and not commit_rows:
            return "No activity recorded yet. Give it a few minutes to start tracking."

        # Build report
        today = datetime.now().strftime("%B %d, %Y")
        report = "*Personal Changelog - " + today + "*\n\n"

        if file_rows:
            # Group by project
            projects = {}
            for row in file_rows:
                project, filename, action, edits = row
                if project not in projects:
                    projects[project] = {"modified": [], "created": []}
                if action == "modified" and filename not in projects[project]["modified"]:
                    projects[project]["modified"].append(filename)
                elif action == "created" and filename not in projects[project]["created"]:
                    projects[project]["created"].append(filename)

            report += "*Files worked on:*\n"
            for project, data in sorted(projects.items()):
                report += "\n" + project + "/\n"
                if data["created"]:
                    report += "  Created: " + ", ".join(data["created"][:5]) + "\n"
                if data["modified"]:
                    report += "  Modified: " + ", ".join(data["modified"][:5]) + "\n"

            total_files = len(set([r[1] for r in file_rows]))
            report += "\nTotal files touched: " + str(total_files) + "\n"

        if commit_rows:
            report += "\n*Git commits:*\n"
            seen = set()
            for repo, message in commit_rows[:10]:
                key = repo + message
                if key not in seen:
                    seen.add(key)
                    report += "- [" + repo + "] " + message + "\n"

        return report

    except Exception as e:
        return "Changelog error: " + str(e)

def add_watch_folder(folder_path):
    global WATCH_FOLDERS
    path = os.path.expanduser(folder_path)
    if os.path.exists(path) and path not in WATCH_FOLDERS:
        WATCH_FOLDERS.append(path)
        return "Now watching: " + path
    elif not os.path.exists(path):
        return "Folder not found: " + folder_path
    else:
        return "Already watching: " + path

# ── Plugin Class ──────────────────────────────────────────
class ChangelogPlugin(Plugin):
    name = "CHANGELOG"
    description = "Show what you worked on today or this week. Personal changelog of file changes and git commits across your projects."
    triggers = [
        "changelog", "what did i work on", "what did i do today",
        "show my work", "daily summary", "work summary",
        "what files did i change", "what did i build today",
        "my progress today", "show changelog", "weekly summary",
        "watch folder", "track folder"
    ]

    def execute(self, value: str) -> tuple:
        try:
            val = value.lower().strip()

            # Add new folder to watch
            if "watch" in val or "track" in val:
                folder = value.strip()
                for word in ["watch", "track", "folder", "add"]:
                    folder = folder.replace(word, "").strip()
                return add_watch_folder(folder), None

            # Weekly report
            if "week" in val:
                report = generate_report(days=7)
                return report, None

            # Yesterday
            if "yesterday" in val:
                report = generate_report(days=2)
                return report, None

            # Default — today
            report = generate_report(days=1)
            return report, None

        except Exception as e:
            return "Changelog error: " + str(e), None

