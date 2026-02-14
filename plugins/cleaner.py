# plugins/cleaner.py
import os
import subprocess
from plugins.base import Plugin

class CleanerPlugin(Plugin):
    name = "CLEAN_SYSTEM"
    description = "Clean system junk, clear cache, free up disk space"
    triggers = ["clean", "cleanup", "free space", "clear cache",
                "clean system", "remove junk"]
    
    def execute(self, value: str) -> tuple:
        results = []
        freed = 0
        
        try:
            # Clear apt cache
            r = subprocess.run(
                "sudo apt clean",
                shell=True, capture_output=True, text=True
            )
            results.append("✅ Cleared apt cache")
            
            # Clear thumbnail cache
            thumb_path = os.path.expanduser("~/.cache/thumbnails")
            if os.path.exists(thumb_path):
                r = subprocess.run(
                    f"rm -rf {thumb_path}/*",
                    shell=True, capture_output=True, text=True
                )
                results.append("✅ Cleared thumbnail cache")
            
            # Clear trash
            trash_path = os.path.expanduser("~/.local/share/Trash")
            if os.path.exists(trash_path):
                r = subprocess.run(
                    f"rm -rf {trash_path}/*",
                    shell=True, capture_output=True, text=True
                )
                results.append("✅ Emptied trash")
            
            # Clear old logs
            r = subprocess.run(
                "sudo journalctl --vacuum-time=7d",
                shell=True, capture_output=True, text=True
            )
            results.append("✅ Cleared logs older than 7 days")
            
            # Show current disk usage
            r = subprocess.run(
                "df -h /",
                shell=True, capture_output=True, text=True
            )
            disk_info = r.stdout.strip()
            
            result = "🧹 *System Cleaned!*\n\n"
            result += "\n".join(results)
            result += f"\n\n💿 Disk now:\n```\n{disk_info}\n```"
            return result, None
            
        except Exception as e:
            return f"❌ Cleaner error: {str(e)}", None
