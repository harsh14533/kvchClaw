# plugins/notes.py
import os
from datetime import datetime
from plugins.base import Plugin

NOTES_FILE = os.path.expanduser("~/myclaw_notes.md")

class NotesPlugin(Plugin):
    name = "NOTES"
    description = "Save and retrieve personal notes"
    triggers = ["note", "notes", "write down", "remember this",
                "save note", "show notes", "my notes"]
    
    def execute(self, value: str) -> tuple:
        try:
            cmd = value.lower().strip()
            
            # Show all notes
            if cmd in ["show", "list", "all", "show notes", "my notes"]:
                if not os.path.exists(NOTES_FILE):
                    return "📝 No notes yet. Say 'note: something' to add one.", None
                with open(NOTES_FILE, 'r') as f:
                    content = f.read()
                return f"📝 *Your Notes:*\n\n{content[:3000]}", None
            
            # Add new note
            else:
                # Remove common prefixes
                note_text = value
                for prefix in ["note:", "note ", "add note ", "write "]:
                    if note_text.lower().startswith(prefix):
                        note_text = note_text[len(prefix):]
                
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                with open(NOTES_FILE, 'a') as f:
                    f.write(f"\n## {timestamp}\n{note_text}\n")
                
                return f"📝 Note saved:\n_{note_text}_", None
                
        except Exception as e:
            return f"❌ Notes error: {str(e)}", None
