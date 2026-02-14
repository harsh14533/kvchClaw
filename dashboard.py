#!/home/cia/myclaw/venv/bin/python3
# -*- coding: utf-8 -*-
# kvchClaw Web Dashboard
# Run: python dashboard.py
# Open: http://localhost:5000

import os
import sys
import psutil
import json
import threading
from datetime import datetime
from flask import Flask, render_template_string, jsonify, request
from flask_socketio import SocketIO, emit

sys.path.insert(0, os.path.expanduser("~/myclaw"))
os.chdir(os.path.expanduser("~/myclaw"))

from dotenv import load_dotenv
load_dotenv(os.path.expanduser("~/myclaw/.env"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
ALLOWED_USER_ID = os.getenv("TELEGRAM_USER_ID")

from plugins.loader import load_plugins, find_plugin
PLUGINS = load_plugins()

app = Flask(__name__)
app.config["SECRET_KEY"] = "kvclaw_dashboard_2026"
socketio = SocketIO(app, cors_allowed_origins="*")

# Chat history for dashboard
chat_history = []

# ── AI Brain ──────────────────────────────────────────────
def call_ai(messages):
    if GROQ_API_KEY:
        try:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                max_tokens=1024
            )
            return response.choices[0].message.content.strip()
        except:
            pass
    if GEMINI_API_KEY:
        try:
            from google import genai as google_genai
            client = google_genai.Client(api_key=GEMINI_API_KEY)
            prompt = "\n".join([m["content"] for m in messages])
            response = client.models.generate_content(
                model="gemini-2.0-flash", contents=prompt
            )
            return response.text.strip()
        except:
            pass
    if MISTRAL_API_KEY:
        try:
            from mistralai import Mistral
            client = Mistral(api_key=MISTRAL_API_KEY)
            response = client.chat.complete(
                model="mistral-small-latest",
                messages=messages, max_tokens=1024
            )
            return response.choices[0].message.content.strip()
        except:
            pass
    return "All APIs unavailable."

def handle_message(user_message):
    plugin_keywords = {
        "CHANGELOG": ["changelog", "what did i work on", "weekly summary", "work summary"],
        "ORGANIZE_FOLDER": ["organize", "sort files", "tidy up"],
        "SYSWHISPER": ["why is my pc", "suspicious", "what happened", "pc report"],
        "WEATHER": ["weather", "temperature", "forecast"],
        "NOTES": ["note", "my notes", "show notes"],
        "CLEAN_SYSTEM": ["clean system", "free space", "clear cache"],
    }
    msg_lower = user_message.lower()
    for plugin_name, keywords in plugin_keywords.items():
        for keyword in keywords:
            if keyword in msg_lower:
                plugin = find_plugin(PLUGINS, plugin_name, user_message)
                if plugin:
                    result, _ = plugin.execute(user_message)
                    return result

    system = (
        "You are kvchClaw, a personal AI agent on Ubuntu Linux. "
        "Answer concisely and helpfully."
    )
    messages = [{"role": "system", "content": system}]
    for msg in chat_history[-6:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})
    return call_ai(messages)

# ── API Routes ────────────────────────────────────────────
@app.route("/")
def index():
    return render_template_string(DASHBOARD_HTML)

@app.route("/api/stats")
def get_stats():
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    processes = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            processes.append(proc.info)
        except:
            pass
    top = sorted(processes, key=lambda x: x["cpu_percent"], reverse=True)[:5]
    return jsonify({
        "cpu": cpu,
        "ram": ram.percent,
        "ram_used": round(ram.used / (1024**3), 1),
        "ram_total": round(ram.total / (1024**3), 1),
        "disk": disk.percent,
        "disk_used": round(disk.used / (1024**3), 1),
        "disk_total": round(disk.total / (1024**3), 1),
        "time": datetime.now().strftime("%H:%M:%S"),
        "date": datetime.now().strftime("%A, %d %B %Y"),
        "processes": top
    })

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"response": "Empty message"})
    chat_history.append({"role": "user", "content": user_message})
    response = handle_message(user_message)
    chat_history.append({"role": "assistant", "content": response})
    if len(chat_history) > 20:
        chat_history.pop(0)
        chat_history.pop(0)
    return jsonify({"response": response})

@app.route("/api/quick/<action>")
def quick_action(action):
    import subprocess
    actions = {
        "screenshot": lambda: subprocess.run("DISPLAY=:0 scrot ~/myclaw_screenshot.png", shell=True),
        "lock": lambda: subprocess.run("DISPLAY=:0 i3lock", shell=True),
        "vol_up": lambda: subprocess.run("pactl set-sink-volume @DEFAULT_SINK@ +10%", shell=True),
        "vol_down": lambda: subprocess.run("pactl set-sink-volume @DEFAULT_SINK@ -10%", shell=True),
    }
    if action in actions:
        actions[action]()
        return jsonify({"status": "done", "action": action})
    return jsonify({"status": "unknown action"})

# ── Dashboard HTML ─────────────────────────────────────────
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>kvchClaw Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600;700&family=Syne:wght@400;700;800&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0a0a0f;
    --surface: #111118;
    --surface2: #1a1a24;
    --border: #2a2a3a;
    --accent: #00ff88;
    --accent2: #7c3aed;
    --accent3: #f59e0b;
    --text: #e2e8f0;
    --text2: #94a3b8;
    --danger: #ef4444;
    --glow: 0 0 20px rgba(0,255,136,0.15);
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'JetBrains Mono', monospace;
    min-height: 100vh;
    overflow-x: hidden;
  }
  /* Animated background grid */
  body::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image:
      linear-gradient(rgba(0,255,136,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0,255,136,0.03) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
    z-index: 0;
  }
  .container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 24px;
    position: relative;
    z-index: 1;
  }
  /* Header */
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 32px;
    padding-bottom: 20px;
    border-bottom: 1px solid var(--border);
  }
  .logo {
    font-family: 'Syne', sans-serif;
    font-size: 28px;
    font-weight: 800;
    letter-spacing: -1px;
  }
  .logo span { color: var(--accent); }
  .status-dot {
    width: 8px; height: 8px;
    background: var(--accent);
    border-radius: 50%;
    display: inline-block;
    margin-right: 8px;
    animation: pulse 2s infinite;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(0,255,136,0.4); }
    50% { opacity: 0.8; box-shadow: 0 0 0 6px rgba(0,255,136,0); }
  }
  .header-right {
    text-align: right;
    font-size: 12px;
    color: var(--text2);
  }
  #live-time {
    font-size: 20px;
    color: var(--accent);
    font-weight: 600;
  }
  /* Grid Layout */
  .grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    grid-template-rows: auto;
    gap: 16px;
  }
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    transition: border-color 0.2s;
  }
  .card:hover { border-color: var(--accent2); }
  .card-title {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 3px;
    color: var(--text2);
    margin-bottom: 16px;
  }
  /* Stat Cards */
  .stat-value {
    font-family: 'Syne', sans-serif;
    font-size: 48px;
    font-weight: 800;
    line-height: 1;
    margin-bottom: 8px;
  }
  .stat-label { font-size: 12px; color: var(--text2); }
  .stat-bar {
    height: 4px;
    background: var(--surface2);
    border-radius: 2px;
    margin-top: 12px;
    overflow: hidden;
  }
  .stat-bar-fill {
    height: 100%;
    border-radius: 2px;
    transition: width 0.8s ease;
  }
  .cpu-color { background: var(--accent); }
  .ram-color { background: var(--accent2); }
  .disk-color { background: var(--accent3); }
  /* Color coding */
  .green { color: var(--accent); }
  .purple { color: var(--accent2); }
  .amber { color: var(--accent3); }
  .red { color: var(--danger); }
  /* Chat */
  .chat-card {
    grid-column: span 2;
    grid-row: span 2;
    display: flex;
    flex-direction: column;
    height: 500px;
  }
  .chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 12px 0;
    display: flex;
    flex-direction: column;
    gap: 12px;
    scrollbar-width: thin;
    scrollbar-color: var(--border) transparent;
  }
  .message {
    padding: 10px 14px;
    border-radius: 8px;
    font-size: 13px;
    line-height: 1.6;
    max-width: 85%;
    animation: fadeIn 0.2s ease;
  }
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(4px); }
    to { opacity: 1; transform: translateY(0); }
  }
  .message.user {
    background: var(--accent2);
    color: white;
    align-self: flex-end;
  }
  .message.bot {
    background: var(--surface2);
    border: 1px solid var(--border);
    align-self: flex-start;
    white-space: pre-wrap;
  }
  .message.thinking {
    background: var(--surface2);
    border: 1px solid var(--border);
    align-self: flex-start;
    color: var(--text2);
  }
  .chat-input-row {
    display: flex;
    gap: 8px;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--border);
  }
  .chat-input {
    flex: 1;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 14px;
    color: var(--text);
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    outline: none;
    transition: border-color 0.2s;
  }
  .chat-input:focus { border-color: var(--accent); }
  .chat-input::placeholder { color: var(--text2); }
  .send-btn {
    background: var(--accent);
    color: var(--bg);
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.2s;
  }
  .send-btn:hover { opacity: 0.8; }
  /* Processes */
  .process-list { display: flex; flex-direction: column; gap: 8px; }
  .process-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    background: var(--surface2);
    border-radius: 6px;
    font-size: 12px;
  }
  .process-name { color: var(--text); flex: 1; }
  .process-stats { color: var(--text2); font-size: 11px; }
  /* Quick Actions */
  .quick-actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }
  .quick-btn {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px;
    color: var(--text);
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    cursor: pointer;
    text-align: center;
    transition: all 0.2s;
  }
  .quick-btn:hover {
    border-color: var(--accent);
    color: var(--accent);
    background: rgba(0,255,136,0.05);
  }
  .quick-btn.active {
    border-color: var(--accent);
    color: var(--accent);
  }
  /* Plugins */
  .plugin-list { display: flex; flex-direction: column; gap: 6px; }
  .plugin-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 0;
    font-size: 12px;
    color: var(--text2);
  }
  .plugin-dot {
    width: 6px; height: 6px;
    background: var(--accent);
    border-radius: 50%;
  }
  /* Span utilities */
  .span-2 { grid-column: span 2; }
  .span-3 { grid-column: span 3; }
  /* Responsive */
  @media (max-width: 900px) {
    .grid { grid-template-columns: 1fr 1fr; }
    .chat-card { grid-column: span 2; }
    .span-2 { grid-column: span 2; }
  }
  @media (max-width: 600px) {
    .grid { grid-template-columns: 1fr; }
    .chat-card, .span-2, .span-3 { grid-column: span 1; }
    .stat-value { font-size: 36px; }
  }
</style>
</head>
<body>
<div class="container">
  <header>
    <div class="logo">
      kvch<span>Claw</span>
      <span class="status-dot" style="margin-left:12px"></span>
      <span style="font-size:13px;font-weight:400;color:var(--text2)">online</span>
    </div>
    <div class="header-right">
      <div id="live-time">--:--:--</div>
      <div id="live-date" style="margin-top:4px">Loading...</div>
    </div>
  </header>

  <div class="grid">

    <!-- CPU -->
    <div class="card">
      <div class="card-title">CPU Usage</div>
      <div class="stat-value green" id="cpu-val">0%</div>
      <div class="stat-label">processor load</div>
      <div class="stat-bar">
        <div class="stat-bar-fill cpu-color" id="cpu-bar" style="width:0%"></div>
      </div>
    </div>

    <!-- RAM -->
    <div class="card">
      <div class="card-title">Memory</div>
      <div class="stat-value purple" id="ram-val">0%</div>
      <div class="stat-label" id="ram-detail">0GB / 0GB</div>
      <div class="stat-bar">
        <div class="stat-bar-fill ram-color" id="ram-bar" style="width:0%"></div>
      </div>
    </div>

    <!-- Disk -->
    <div class="card">
      <div class="card-title">Disk</div>
      <div class="stat-value amber" id="disk-val">0%</div>
      <div class="stat-label" id="disk-detail">0GB / 0GB</div>
      <div class="stat-bar">
        <div class="stat-bar-fill disk-color" id="disk-bar" style="width:0%"></div>
      </div>
    </div>

    <!-- Chat -->
    <div class="card chat-card">
      <div class="card-title">Chat with kvchClaw</div>
      <div class="chat-messages" id="chat-messages">
        <div class="message bot">kvchClaw ready. Ask me anything or use the quick actions.</div>
      </div>
      <div class="chat-input-row">
        <input
          class="chat-input"
          id="chat-input"
          type="text"
          placeholder="ask anything..."
          autocomplete="off"
        />
        <button class="send-btn" onclick="sendMessage()">Send</button>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="card">
      <div class="card-title">Quick Actions</div>
      <div class="quick-actions">
        <button class="quick-btn" onclick="quickAction('vol_up')">VOL UP</button>
        <button class="quick-btn" onclick="quickAction('vol_down')">VOL DOWN</button>
        <button class="quick-btn" onclick="quickAction('screenshot')">SCREENSHOT</button>
        <button class="quick-btn" onclick="quickAction('lock')">LOCK</button>
        <button class="quick-btn" onclick="chatAsk('check my system stats')">SYS STATS</button>
        <button class="quick-btn" onclick="chatAsk('what did i work on today')">CHANGELOG</button>
        <button class="quick-btn" onclick="chatAsk('show my notes')">NOTES</button>
        <button class="quick-btn" onclick="chatAsk('is anything suspicious running')">SECURITY</button>
      </div>
    </div>

    <!-- Top Processes -->
    <div class="card">
      <div class="card-title">Top Processes</div>
      <div class="process-list" id="process-list">
        <div class="process-item">
          <span class="process-name">Loading...</span>
        </div>
      </div>
    </div>

    <!-- Plugins -->
    <div class="card">
      <div class="card-title">Active Plugins</div>
      <div class="plugin-list" id="plugin-list">
        Loading...
      </div>
    </div>

  </div>
</div>

<script>
// Update stats every 5 seconds
async function updateStats() {
  try {
    const res = await fetch('/api/stats');
    const data = await res.json();

    // Time
    document.getElementById('live-time').textContent = data.time;
    document.getElementById('live-date').textContent = data.date;

    // CPU
    const cpu = data.cpu;
    document.getElementById('cpu-val').textContent = cpu + '%';
    document.getElementById('cpu-bar').style.width = cpu + '%';
    document.getElementById('cpu-val').className = 'stat-value ' + (cpu > 80 ? 'red' : 'green');

    // RAM
    const ram = data.ram;
    document.getElementById('ram-val').textContent = ram + '%';
    document.getElementById('ram-bar').style.width = ram + '%';
    document.getElementById('ram-detail').textContent = data.ram_used + 'GB / ' + data.ram_total + 'GB';
    document.getElementById('ram-val').className = 'stat-value ' + (ram > 85 ? 'red' : 'purple');

    // Disk
    const disk = data.disk;
    document.getElementById('disk-val').textContent = disk + '%';
    document.getElementById('disk-bar').style.width = disk + '%';
    document.getElementById('disk-detail').textContent = data.disk_used + 'GB / ' + data.disk_total + 'GB';
    document.getElementById('disk-val').className = 'stat-value ' + (disk > 90 ? 'red' : 'amber');

    // Processes
    const pl = document.getElementById('process-list');
    pl.innerHTML = data.processes.map(p =>
      '<div class="process-item">' +
      '<span class="process-name">' + p.name + '</span>' +
      '<span class="process-stats">CPU ' + p.cpu_percent.toFixed(1) + '% | RAM ' + p.memory_percent.toFixed(1) + '%</span>' +
      '</div>'
    ).join('');

  } catch(e) {
    console.log('Stats error:', e);
  }
}

// Load plugins list
async function loadPlugins() {
  const res = await fetch('/api/stats');
  const plugins = [
    'File Organizer',
    'SysWhisper',
    'Changelog',
    'Weather',
    'Notes',
    'Cleaner'
  ];
  document.getElementById('plugin-list').innerHTML = plugins.map(p =>
    '<div class="plugin-item"><div class="plugin-dot"></div>' + p + '</div>'
  ).join('');
}

// Chat
async function sendMessage() {
  const input = document.getElementById('chat-input');
  const message = input.value.trim();
  if (!message) return;

  addMessage(message, 'user');
  input.value = '';

  const thinking = addMessage('thinking...', 'thinking');

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message})
    });
    const data = await res.json();
    thinking.remove();
    addMessage(data.response, 'bot');
  } catch(e) {
    thinking.remove();
    addMessage('Error connecting to kvchClaw', 'bot');
  }
}

function addMessage(text, type) {
  const container = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'message ' + type;
  div.textContent = text;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return div;
}

function chatAsk(question) {
  document.getElementById('chat-input').value = question;
  sendMessage();
}

async function quickAction(action) {
  const btn = event.target;
  btn.classList.add('active');
  try {
    await fetch('/api/quick/' + action);
    setTimeout(() => btn.classList.remove('active'), 1000);
  } catch(e) {
    btn.classList.remove('active');
  }
}

// Enter key to send
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('chat-input').addEventListener('keydown', e => {
    if (e.key === 'Enter') sendMessage();
  });
  loadPlugins();
  updateStats();
  setInterval(updateStats, 5000);
});
</script>
</body>
</html>"""

if __name__ == "__main__":
    print("=" * 40)
    print("kvchClaw Web Dashboard")
    print("Local:   http://localhost:5000")
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        print("Network: http://" + ip + ":5000")
    except:
        pass
    print("=" * 40)
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)
