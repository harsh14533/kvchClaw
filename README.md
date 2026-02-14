# kvchClaw

> Control your Linux PC from your phone using Telegram — powered by local AI with zero cloud dependency. Built for low to mid-end hardware.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Platform](https://img.shields.io/badge/Platform-Linux-orange)
![License](https://img.shields.io/badge/License-MIT-green)
![AI](https://img.shields.io/badge/AI-Groq%20%2B%20Gemini%20%2B%20Mistral%20%2B%20Local-purple)
![Plugins](https://img.shields.io/badge/Plugins-5%20built--in-yellow)

---

## What is kvchClaw?

kvchClaw is a personal AI agent that runs on your Linux machine and lets you control it from anywhere using Telegram. It uses a smart API pool (Groq, Gemini, Mistral) with local Ollama as fallback so it works fast even on weak hardware, and works offline when there is no internet.

Send a message from your phone. Your PC thinks, acts, and replies.

```
You: organize my downloads folder
kvchClaw: sorted 47 files into 6 categories

You: why is my PC slow right now?
kvchClaw: Chrome is using 4.2GB RAM and your CPU
          has been at 78% for the last 20 minutes

You: write a script to backup my code folder
kvchClaw: wrote it, ran it, committed to GitHub

You: what is the latest AI news today?
kvchClaw: searched web and summarized results
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

---

## Hardware Requirements

| Spec | Minimum | Tested On |
|------|---------|-----------|
| CPU | Any 4-core | Intel i7-7700 |
| RAM | 8GB | 16GB |
| GPU | Not needed | GT 710 (ignored) |
| OS | Ubuntu 20.04+ | Ubuntu 24.04.3 LTS |
| Storage | 5GB free | — |

---

## Features

### Core Agent
- Telegram interface — control PC from phone anywhere
- Multi API brain — Groq + Gemini + Mistral + Local fallback
- Persistent memory — remembers facts and conversations forever
- Conversation context — remembers last 10 messages for smart replies
- Voice messages — send voice note, it understands and acts on it
- Web search — searches internet and summarizes results intelligently
- Screenshot — see your screen from your phone
- PC control — open/close apps, volume, workspaces, lock screen
- Code writer and runner — writes and executes Python code
- GitHub integration — push generated code directly to repos
- System monitor — CPU, RAM, disk, top processes
- Self healing — restarts automatically if it crashes
- Auto start on boot via systemd

### Built-in Plugins
- Smart File Organizer — organize any folder by file type
- SysWhisper — explain PC behavior in plain English using history
- Weather — get weather for any city
- Notes — save and search personal notes
- System Cleaner — free up disk space and clear cache

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

## Quick Start

### 1. Clone
```bash
git clone https://github.com/harsh14533/kvchClaw.git
cd kvchClaw
```

### 2. Install Ollama (optional, for offline use)
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

```
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_USER_ID=your_user_id
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key
MISTRAL_API_KEY=your_mistral_key
GITHUB_TOKEN=your_github_token
GITHUB_USERNAME=your_github_username
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

## Usage Examples

### System
```
check my system stats
what processes are using most CPU
lock my screen
```

### PC Control
```
open firefox
increase volume
set volume to 60%
switch to workspace 3
```

### File Management
```
organize my downloads folder
organize ~/Desktop
list files in my home folder
read my main.py file
```

### PC Intelligence
```
why is my PC slow?
what is using my internet right now?
is anything suspicious running?
what happened in the last hour?
```

### Coding
```
write a python script to rename all jpg files
write a script to find large files on my system
```

### Web Search
```
latest AI news today
what is the weather in Surat
```

### Memory
```
my name is Harsh
remember my projects are in ~/code
what do you know about me?
```

### Voice
Hold mic in Telegram and speak. kvchClaw transcribes and acts on it like text.

---

## Plugin System

Add a new tool in one file. Drop it in plugins/ folder. Restart. It works.

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
├── watchdog.sh          - self healing script
├── plugins/
│   ├── base.py          - plugin base class
│   ├── loader.py        - auto discovery
│   ├── organizer.py     - smart file organizer
│   ├── syswhisper.py    - PC intelligence layer
│   ├── weather.py       - weather lookup
│   ├── notes.py         - personal notes
│   ├── cleaner.py       - system cleaner
│   └── PLUGIN_GUIDE.md  - how to contribute plugins
├── .env.example
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Roadmap

- Smart Cron — schedule tasks in plain English
- Attention Guardian — daily focus and distraction report
- Personal Changelog — auto document what you worked on each day
- Offline Translator — translate files without internet
- Web dashboard — browser UI accessible from any device
- MCP server — use kvchClaw tools inside Claude and Cursor

---

## Contributing

Contributions welcome especially:
- Testing on different hardware specs
- New plugin ideas and implementations
- Bug fixes and stability improvements

1. Fork the repo
2. Create branch: git checkout -b feature/my-feature
3. Commit: git commit -m 'Add my feature'
4. Push: git push origin feature/my-feature
5. Open a Pull Request

---

## License

MIT License — free to use, modify and distribute.

---

## Built By

Harsh Savaliya — built on Ubuntu 24.04 with i3 window manager, running on Intel i7-7700 with no GPU.

Proof that you do not need expensive hardware to run a powerful personal AI agent.

If this helped you, give it a star on GitHub!
