# plugins/organizer.py
# Smart File Organizer Plugin
# Organizes any folder by file type automatically

import os
import shutil
from datetime import datetime
from plugins.base import Plugin

# File type categories
CATEGORIES = {
    "Images": [
        ".jpg", ".jpeg", ".png", ".gif",
        ".webp", ".svg", ".ico", ".bmp", ".tiff"
    ],
    "Documents": [
        ".pdf", ".doc", ".docx", ".txt", ".md",
        ".odt", ".rtf", ".xlsx", ".xls", ".csv",
        ".ppt", ".pptx", ".epub"
    ],
    "Videos": [
        ".mp4", ".mkv", ".avi", ".mov", ".wmv",
        ".flv", ".webm", ".m4v", ".3gp"
    ],
    "Audio": [
        ".mp3", ".wav", ".flac", ".aac", ".ogg",
        ".wma", ".m4a", ".opus"
    ],
    "Archives": [
        ".zip", ".tar", ".gz", ".rar", ".7z",
        ".bz2", ".xz", ".tar.gz", ".tar.bz2"
    ],
    "Code": [
        ".py", ".js", ".ts", ".html", ".css",
        ".java", ".c", ".cpp", ".h", ".sh",
        ".json", ".yaml", ".yml", ".xml",
        ".sql", ".php", ".rb", ".go", ".rs"
    ],
    "Installers": [
        ".deb", ".rpm", ".appimage", ".exe",
        ".msi", ".dmg", ".snap"
    ],
    "Fonts": [
        ".ttf", ".otf", ".woff", ".woff2"
    ]
}

def get_category(filename):
    ext = os.path.splitext(filename)[1].lower()
    for category, extensions in CATEGORIES.items():
        if ext in extensions:
            return category
    return "Other"

def get_folder_path(dirpath):
    dirpath = dirpath.strip()
    # Handle common shortcuts
    shortcuts = {
        "downloads": "~/Downloads",
        "desktop": "~/Desktop",
        "documents": "~/Documents",
        "pictures": "~/Pictures",
        "videos": "~/Videos",
        "music": "~/Music",
        "home": "~"
    }
    lower = dirpath.lower()
    for shortcut, path in shortcuts.items():
        if lower == shortcut or lower == shortcut + "s":
            return os.path.expanduser(path)
    return os.path.expanduser(dirpath)

class OrganizerPlugin(Plugin):
    name = "ORGANIZE_FOLDER"
    description = "Organize a folder by automatically sorting files into subfolders by type"
    triggers = [
        "organize", "sort files", "clean folder",
        "organize downloads", "sort my", "tidy up",
        "organize my", "clean up my", "sort downloads"
    ]

    def execute(self, value: str) -> tuple:
        try:
            # Get the folder path
            folder_path = get_folder_path(value)

            if not os.path.exists(folder_path):
                return f"Folder not found: {folder_path}", None

            if not os.path.isdir(folder_path):
                return f"That is not a folder: {folder_path}", None

            # Scan all files
            all_files = [
                f for f in os.listdir(folder_path)
                if os.path.isfile(os.path.join(folder_path, f))
            ]

            if not all_files:
                return f"No files found in {folder_path}", None

            # Count files per category before moving
            preview = {}
            for filename in all_files:
                cat = get_category(filename)
                if cat not in preview:
                    preview[cat] = []
                preview[cat].append(filename)

            # Do the organization
            moved = {}
            skipped = []
            errors = []

            for filename in all_files:
                # Skip hidden files
                if filename.startswith("."):
                    skipped.append(filename)
                    continue

                category = get_category(filename)
                source = os.path.join(folder_path, filename)
                dest_dir = os.path.join(folder_path, category)

                try:
                    # Create category folder if needed
                    os.makedirs(dest_dir, exist_ok=True)
                    dest = os.path.join(dest_dir, filename)

                    # Handle duplicates
                    if os.path.exists(dest):
                        name, ext = os.path.splitext(filename)
                        timestamp = datetime.now().strftime("%H%M%S")
                        dest = os.path.join(
                            dest_dir,
                            f"{name}_{timestamp}{ext}"
                        )

                    shutil.move(source, dest)

                    if category not in moved:
                        moved[category] = 0
                    moved[category] += 1

                except Exception as e:
                    errors.append(f"{filename}: {str(e)}")

            # Build report
            total_moved = sum(moved.values())
            report = f"*Folder Organized: {folder_path}*\n\n"
            report += f"Total files processed: {total_moved}\n\n"

            if moved:
                report += "*Files sorted into:*\n"
                for category, count in sorted(moved.items()):
                    report += f"- {category}/: {count} files\n"

            if skipped:
                report += f"\nSkipped {len(skipped)} hidden files"

            if errors:
                report += f"\n\nErrors ({len(errors)}):\n"
                for err in errors[:5]:
                    report += f"- {err}\n"

            report += f"\n\nDone! Your {os.path.basename(folder_path)} folder is now organized."

            return report, None

        except Exception as e:
            return f"Organizer error: {str(e)}", None
