# How To Create a kvchClaw Plugin

Anyone can add a new tool to kvchClaw by creating a single Python file.

## Basic Template

Create a new file in the `plugins/` folder:
```python
from plugins.base import Plugin

class MyPlugin(Plugin):
    name = "MY_PLUGIN"          # ACTION name the AI will use
    description = "What it does in plain English"
    triggers = ["keyword1", "keyword2"]  # phrases that hint at this plugin
    
    def execute(self, value: str) -> tuple:
        # Do your thing here
        result = f"Did something with: {value}"
        
        # Always return (text_result, file_path_or_None)
        return result, None
```

## Rules
- File goes in `plugins/` folder
- Class must inherit from `Plugin`
- Must implement `execute()` 
- `execute()` always returns a tuple: `(str, str_or_None)`
- Second return value is a file path (for images/files) or None

## Examples Already In This Repo
- `weather.py` — search web for weather
- `notes.py` — save and read personal notes
- `cleaner.py` — clean system junk

## That's It!
Drop your file in `plugins/`, restart kvchClaw, your plugin is live.
