# kvchClaw 🤖

> Control your Linux PC from your phone using Telegram — powered by local AI with zero cloud dependency.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Platform](https://img.shields.io/badge/Platform-Linux-orange)
![License](https://img.shields.io/badge/License-MIT-green)
![AI](https://img.shields.io/badge/AI-Local%20%2B%20Groq-purple)

---

## What is kvchClaw?

kvchClaw is a personal AI agent that runs on your Linux machine and lets you control it from anywhere using Telegram. Built specifically for **low to mid-end hardware** — no expensive GPU required.

Send a message from your phone. Your PC thinks, acts, and replies.

```
You (Telegram) → "take a screenshot"
kvchClaw       → 📸 sends your screen to your phone

You (Telegram) → "what's using my CPU?"
kvchClaw       → ⚡ shows top processes instantly

You (Telegram) → "write a script to backup my code folder"
kvchClaw       → 🐍 writes it, runs it, shows output

You (Telegram) → "latest AI news today"
kvchClaw       → 🌐 searches web and summarizes results
```

---

## Features

- 📱 **Telegram Interface** — talk to your PC from your phone
- ⚡ **Hybrid AI Brain** — uses Groq (fast) with local Ollama fallback (private)
- 🧠 **Persistent Memory** — remembers facts and past conversations forever
- 🌐 **Web Search** — searches internet and summarizes results
- 📸 **Screenshot** — see your screen from anywhere
- 🖥️ **PC Control** — open/close apps, volume, workspaces, lock screen
- 💻 **Code Writer + Runner** — writes and executes Python code
- 🐙 **GitHub Integration** — push generated code directly to your repos
- 📊 **System Monitor** — CPU, RAM, disk, top processes
- 🔒 **Secure** — only responds to your Telegram account

---

## Built For Low-End Hardware

Most AI agent projects assume you have an expensive GPU. kvchClaw is different.

| Spec | Minimum | Tested On |
|------|---------|-----------|
| CPU | Any 4-core | Intel i7-7700 |
| RAM | 8GB | 16GB |
| GPU | Not needed | GT 710 (ignored) |
| OS | Ubuntu 20.04+ | Ubuntu 24.04.3 LTS |
| Storage | 10GB free | — |

**No GPU needed. Runs entirely on CPU.**

---

## How It Works

```
Your Phone (Telegram)
        ↓
  Telegram Bot API
        ↓
  kvchClaw Agent (Python)
        ↓
  Smart Brain Router
     ↙         ↘
Groq API     Local Ollama
(fast+smart) (private+offline)
        ↓
  Tools Layer
  ├── System Control
  ├── Web Search
  ├── Code Runner
  ├── GitHub
  ├── Screenshot
  └── Memory (ChromaDB)
```

---

## Quick Start

### 1. Clone The Repo
```bash
git clone https://github.com/YOUR_USERNAME/kvchClaw.git
cd kvchClaw
```

### 2. Install Ollama
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5-coder:7b
```

### 3. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Create Your Telegram Bot
1. Open Telegram and search `@BotFather`
2. Send `/newbot` and follow instructions
3. Copy your bot token
4. Search `@userinfobot` to get your user ID

### 5. Get Free Groq API Key
1. Go to [console.groq.com](https://console.groq.com)
2. Sign up free — no credit card needed
3. Create an API key

### 6. Configure .env
```bash
cp .env.example .env
```
Edit `.env` with your values:
```
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_USER_ID=your_telegram_user_id
GROQ_API_KEY=your_groq_api_key
GITHUB_TOKEN=your_github_token (optional)
GITHUB_USERNAME=your_github_username (optional)
```

### 7. Run It
```bash
python main.py
```

---

## Usage Examples

Send these messages to your Telegram bot:

### System Control
```
check my system stats
what processes are using most CPU
kill the process using most memory
lock my screen
```

### PC Control
```
open firefox
close spotify
increase volume
set volume to 60%
switch to workspace 3
```

### Code
```
write a python script to rename all jpg files in downloads
write a script to find duplicate files in my home folder
```

### Web Search
```
latest AI news today
what is the weather in my city
latest geopolitics news this week
```

### Memory
```
my name is Cia
remember my projects are in ~/code
what do you know about me?
what did we talk about yesterday?
```

### Screenshot
```
take a screenshot
show me my screen
```

### GitHub
```
list my github repos
push my last generated code to github
```

---

## Auto Start on Boot

```bash
sudo nano /etc/systemd/system/kvclaw.service
```

Paste:
```ini
[Unit]
Description=kvchClaw AI Agent
After=network.target ollama.service

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/kvchClaw
ExecStart=/home/YOUR_USERNAME/kvchClaw/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable kvclaw
sudo systemctl start kvclaw
```

---

## Requirements

```
python-telegram-bot
ollama
psutil
chromadb
groq
PyGithub
ddgs
python-dotenv
```

---

## Roadmap

- [ ] Voice message support (send voice note on Telegram)
- [ ] File manager (read, move, rename files from phone)
- [ ] Scheduled tasks and reminders
- [ ] Image understanding (send photo and ask questions)
- [ ] Multi-language support
- [ ] Web UI dashboard
- [ ] Plugin system for community contributions

---

## Contributing

Contributions are welcome! This project is especially looking for:
- People with different hardware to test on
- New tool/plugin ideas
- Bug fixes and improvements

1. Fork the repo
2. Create your branch: `git checkout -b feature/amazing-feature`
3. Commit: `git commit -m 'Add amazing feature'`
4. Push: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## License

MIT License — free to use, modify and distribute.

---

## Made By

**cia** — built on Ubuntu 24.04 with i3, running entirely on CPU.
Proof that you don't need expensive hardware to run powerful local AI.

---

*If this helped you, give it a ⭐ on GitHub!*
