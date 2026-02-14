# kvchClaw

> Control your Linux PC from your phone using Telegram and terminal — powered by local AI with zero cloud dependency. Built specifically for low to mid-end hardware.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Platform](https://img.shields.io/badge/Platform-Linux-orange)
![License](https://img.shields.io/badge/License-MIT-green)
![AI](https://img.shields.io/badge/AI-Groq%20%2B%20Gemini%20%2B%20Mistral%20%2B%20Local-purple)
![Plugins](https://img.shields.io/badge/Plugins-6%20built--in-yellow)

---

## One Command Install
```bash
curl -fsSL https://raw.githubusercontent.com/harsh14533/kvchClaw/main/install.sh | bash
```

The installer automatically detects your hardware, downloads the right AI model for your RAM, sets everything up and starts the bot. No manual steps needed.

---

## What is kvchClaw?

kvchClaw is a personal AI agent that runs on your Linux machine and lets you control it from anywhere using Telegram or directly from your terminal. It uses a smart API pool with Groq, Gemini and Mistral as primary brains with local Ollama as offline fallback.

Send a message from your phone or terminal. Your PC thinks, acts, and replies.
```
You: organize my downloads folder
kvchClaw: sorted 47 files into 6 categories

You: why is my PC slow right now?
kvchClaw: Chrome is using 4.2GB RAM and your CPU
          has been at 78% for the last 20 minutes

You: what did I work on today?
kvchClaw: Modified main.py, created 2 plugins,
          made 3 git commits in kvchClaw project

You: write a script to backup my code folder
kvchClaw: wrote it, ran it, committed to GitHub
```

---

## What Makes kvchClaw Different

Most AI agent projects assume you have an expensive GPU and fast internet. kvchClaw is built for the majority of users who do not.

- Uses free cloud APIs so no GPU needed at all
- Falls back to local Ollama if internet is unavailable
- Automatically switches APIs if one fails or hits rate limits
- Runs on 8GB RAM minimum, tested on 16GB with no GPU
- Plugin system means anyone can add new tools in 10 lines
- Self healing watchdog so the bot never stays dead
- Works from both Telegram and your terminal

---

## Hardware Requirements

| Spec | Minimum | Tested On |
|------|---------|-----------|
| CPU | Any 4-core | Intel i7-7700 |
| RAM | 8GB | 16GB |
| GPU | Not needed | GT 710 (ignored) |
| OS | Ubuntu 20.04+ | Ubuntu 24.04.3 LTS |
| Storage | 6GB free | — |

---

## How The Smart API Pool Works
```
Message arrives
      |
Try Groq first (fastest, free 14400 requests/day)
      | if fails
Try Gemini (free 1500 requests/day)
      | if fails
Try Mistral (free tier)
      | if all fail
Use Local Ollama (works offline, no internet needed)
```

Load spreads across multiple free tiers automatically. Effectively unlimited free AI for personal use.

---

## Features

### Core Agent
- Telegram interface — control PC from phone anywhere
- Terminal interface — type ask anything directly in terminal
- Multi API brain — Groq + Gemini + Mistral + Local fallback
- Persistent memory — remembers facts and conversations forever
- Conversation context — remembers last 10 messages for smart replies
- Voice messages — send voice note, it understands and acts on it
- Web search — searches internet and summarizes results
- Screenshot — see your screen from your phone
- PC control — open/close apps, volume, workspaces, lock screen
- Code writer and runner — writes and executes Python code
- GitHub integration — push generated code directly to repos
- System monitor — CPU, RAM, disk, top processes
- Self healing — restarts automatically if it crashes
- Auto start on boot via systemd

### Built-in Plugins
- Smart File Organizer — organize any folder by file type automatically
- SysWhisper — explain PC behavior in plain English using historical data
- Personal Changelog — auto track what you worked on each day
- Weather — get weather for any city
- Notes — save and search personal notes
- System Cleaner — free up disk space and clear cache

---

## Usage Examples

### From Telegram
```
check my system stats
open firefox
organize my downloads folder
why is my PC slow?
what did I work on today?
write a python script to find large files
latest AI news today
my name is Harsh, remember this
take a screenshot
```

### From Terminal
```bash
ask why is my ram high
ask what did i work on today
ask organize my downloads
ask weather in surat
ask write a hello world script
ask          # opens interactive chat mode
```

---

## Plugin System

Add a new tool in one file. Drop it in the plugins/ folder. Restart. It works automatically.
```python
from plugins.base import Plugin

class MyPlugin(Plugin):
    name = "MY_PLUGIN"
    description = "What it does in plain English"
    triggers = ["keyword1", "keyword2"]

    def execute(self, value: str) -> tuple:
        result = "Did something with: " + value
        return result, None
```

See plugins/PLUGIN_GUIDE.md for full documentation.

---

## Project Structure
```
kvchClaw/
├── main.py              - core agent
├── ask.py               - terminal interface
├── install.sh           - one command installer
├── watchdog.sh          - self healing script
├── plugins/
│   ├── base.py          - plugin base class
│   ├── loader.py        - auto discovery
│   ├── organizer.py     - smart file organizer
│   ├── syswhisper.py    - PC intelligence layer
│   ├── changelog.py     - personal changelog
│   ├── weather.py       - weather lookup
│   ├── notes.py         - personal notes
│   ├── cleaner.py       - system cleaner
│   └── PLUGIN_GUIDE.md  - how to contribute
├── .env.example
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Manual Install

If you prefer to install manually instead of using the installer script:

### 1. Clone
```bash
git clone https://github.com/harsh14533/kvchClaw.git
cd kvchClaw
```

### 2. Install Ollama
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5-coder:7b
```

### 3. Setup environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Get your Telegram bot
1. Search @BotFather on Telegram
2. Send /newbot and follow instructions
3. Copy your bot token
4. Search @userinfobot to get your user ID

### 5. Get free API keys
- Groq: https://console.groq.com (free, no credit card)
- Gemini: https://aistudio.google.com/apikey (free)
- Mistral: https://console.mistral.ai (free tier)

### 6. Configure
```bash
cp .env.example .env
nano .env
```

### 7. Run
```bash
python main.py
```

---

## Auto Start on Boot
```bash
sudo nano /etc/systemd/system/kvclaw.service
```
```ini
[Unit]
Description=kvchClaw AI Agent Watchdog
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/kvchClaw
ExecStart=/home/YOUR_USERNAME/kvchClaw/watchdog.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload
sudo systemctl enable kvclaw
sudo systemctl start kvclaw
```

---

## Roadmap

- Smart Cron — schedule tasks in plain English
- Attention Guardian — daily focus and distraction report
- Web dashboard — browser UI accessible from any device
- Offline Translator — translate files without internet
- MCP server — use kvchClaw tools inside Claude and Cursor

---

## Contributing

Contributions welcome especially from people with different hardware specs. The easiest way to contribute is to write a new plugin.

1. Fork the repo
2. Create branch: git checkout -b feature/my-plugin
3. Write your plugin in plugins/my_plugin.py
4. Commit: git commit -m 'Add my plugin'
5. Push and open a Pull Request

---

## License

MIT License — free to use, modify and distribute.

---

## Built By

Harsh Savaliya — built on Ubuntu 24.04 with i3 window manager, running on Intel i7-7700 with no GPU.

Proof that you do not need expensive hardware to run a powerful personal AI agent.

If this helped you, give it a star on GitHub!
