import os
import subprocess
import psutil
import ollama
import chromadb
import asyncio
from groq import Groq
from github import Github
from datetime import datetime
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# ── Load Config ───────────────────────────────────────────
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ALLOWED_USER_ID = int(os.getenv("TELEGRAM_USER_ID"))
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")

# ── Setup Clients ─────────────────────────────────────────
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
github_client = Github(GITHUB_TOKEN) if GITHUB_TOKEN else None

# ── Memory Setup ──────────────────────────────────────────
memory_client = chromadb.PersistentClient(path="./memory")
conversation_memory = memory_client.get_or_create_collection("conversations")
facts_memory = memory_client.get_or_create_collection("facts")

def save_conversation(user_msg: str, bot_reply: str):
    timestamp = str(datetime.now().timestamp())
    conversation_memory.add(
        documents=[f"User: {user_msg}\nMyClaw: {bot_reply}"],
        ids=[timestamp],
        metadatas={"time": str(datetime.now()), "date": datetime.now().strftime("%Y-%m-%d")}
    )

def save_fact(text: str):
    facts_memory.add(
        documents=[text],
        ids=[str(datetime.now().timestamp())],
        metadatas={"time": str(datetime.now())}
    )

def search_conversations(query: str) -> str:
    try:
        results = conversation_memory.query(query_texts=[query], n_results=4)
        if results["documents"][0]:
            return "Relevant past conversations:\n" + "\n---\n".join(results["documents"][0])
    except:
        pass
    return ""

def search_facts(query: str) -> str:
    try:
        results = facts_memory.query(query_texts=[query], n_results=3)
        if results["documents"][0]:
            return "\n".join(results["documents"][0])
    except:
        pass
    return ""

# ── Screenshot Tool ───────────────────────────────────────
def take_screenshot() -> str:
    """Take screenshot and return file path"""
    try:
        path = os.path.expanduser("~/myclaw_screenshot.png")
        result = subprocess.run(
            f"DISPLAY=:0 scrot {path}",
            shell=True, capture_output=True, text=True
        )
        if os.path.exists(path):
            return path
        return None
    except Exception as e:
        return None

# ── PC Control Tool ───────────────────────────────────────
def control_pc(command: str) -> str:
    """Control PC using xdotool and i3 commands"""
    try:
        # Volume control
        if "volume" in command.lower():
            if "up" in command.lower() or "increase" in command.lower():
                subprocess.run("pactl set-sink-volume @DEFAULT_SINK@ +10%",
                    shell=True)
                return "🔊 Volume increased by 10%"
            elif "down" in command.lower() or "decrease" in command.lower():
                subprocess.run("pactl set-sink-volume @DEFAULT_SINK@ -10%",
                    shell=True)
                return "🔉 Volume decreased by 10%"
            elif "mute" in command.lower():
                subprocess.run("pactl set-sink-mute @DEFAULT_SINK@ toggle",
                    shell=True)
                return "🔇 Volume muted/unmuted"
            # Set specific volume level
            import re
            nums = re.findall(r'\d+', command)
            if nums:
                subprocess.run(
                    f"pactl set-sink-volume @DEFAULT_SINK@ {nums[0]}%",
                    shell=True)
                return f"🔊 Volume set to {nums[0]}%"

        # Lock screen
        elif "lock" in command.lower():
            subprocess.run("DISPLAY=:0 i3lock", shell=True)
            return "🔒 Screen locked"

        # Open application
        elif "open" in command.lower():
            app = command.lower().replace("open", "").strip()
            subprocess.Popen(
                f"DISPLAY=:0 {app}",
                shell=True
            )
            return f"✅ Opening {app}"

        # Close/kill application
        elif "close" in command.lower() or "kill" in command.lower():
            app = command.lower().replace("close", "").replace("kill", "").strip()
            subprocess.run(f"pkill {app}", shell=True)
            return f"✅ Closed {app}"

        # Switch workspace in i3
        elif "workspace" in command.lower():
            import re
            nums = re.findall(r'\d+', command)
            if nums:
                subprocess.run(
                    f"DISPLAY=:0 i3-msg workspace {nums[0]}",
                    shell=True)
                return f"✅ Switched to workspace {nums[0]}"

        # Kill highest CPU process
        elif "cpu" in command.lower() and "kill" in command.lower():
            result = subprocess.run(
                "ps aux --sort=-%cpu | awk 'NR==2{print $2, $11}'",
                shell=True, capture_output=True, text=True
            )
            if result.stdout:
                pid, name = result.stdout.strip().split(' ', 1)
                subprocess.run(f"kill {pid}", shell=True)
                return f"✅ Killed {name} (PID: {pid})"

        # Run any i3 command directly
        elif "i3" in command.lower():
            cmd = command.lower().replace("i3", "").strip()
            subprocess.run(f"DISPLAY=:0 i3-msg {cmd}", shell=True)
            return f"✅ i3 command sent: {cmd}"

        else:
            # Try running as direct command
            result = subprocess.run(
                f"DISPLAY=:0 {command}",
                shell=True, capture_output=True, text=True, timeout=10
            )
            return result.stdout or result.stderr or "✅ Done"

    except Exception as e:
        return f"❌ Control failed: {str(e)}"

# ── GitHub Tool ───────────────────────────────────────────
def github_push_code(filename: str, code: str, repo_name: str = None,
                     commit_msg: str = None) -> str:
    """Push code to GitHub"""
    if not github_client:
        return "❌ GitHub not configured. Add GITHUB_TOKEN to .env"
    try:
        user = github_client.get_user()

        # Use first repo or specified repo
        if repo_name:
            repo = user.get_repo(repo_name)
        else:
            repos = list(user.get_repos())
            if not repos:
                return "❌ No repos found on your GitHub"
            repo = repos[0]

        message = commit_msg or f"MyClaw: add {filename}"

        # Check if file exists to update or create
        try:
            existing = repo.get_contents(filename)
            repo.update_file(
                existing.path,
                message,
                code,
                existing.sha
            )
            return f"✅ Updated `{filename}` in `{repo.name}`"
        except:
            repo.create_file(filename, message, code)
            return (
                f"✅ Pushed `{filename}` to `{repo.name}`\n"
                f"🔗 https://github.com/{GITHUB_USERNAME}/{repo.name}"
            )
    except Exception as e:
        return f"❌ GitHub error: {str(e)}"

def list_github_repos() -> str:
    """List all GitHub repos"""
    if not github_client:
        return "❌ GitHub not configured"
    try:
        user = github_client.get_user()
        repos = list(user.get_repos())
        repo_list = "\n".join([
            f"• {r.name} {'⭐' * r.stargazers_count if r.stargazers_count else ''}"
            for r in repos[:10]
        ])
        return f"📁 Your GitHub repos:\n{repo_list}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

# ── Process Manager ───────────────────────────────────────
def get_top_processes() -> str:
    """Get top processes by CPU and RAM"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            processes.append(proc.info)
        except:
            pass

    # Sort by CPU
    top_cpu = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:5]

    result = "⚡ Top Processes by CPU:\n"
    for p in top_cpu:
        result += f"• {p['name']} (PID:{p['pid']}) CPU:{p['cpu_percent']:.1f}% RAM:{p['memory_percent']:.1f}%\n"

    return result

# ── Web Search ────────────────────────────────────────────
def web_search(query: str) -> str:
    try:
        from ddgs import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=6):
                results.append(
                    f"📰 {r['title']}\n{r['body']}\n🔗 {r['href']}"
                )

        if not results:
            return "❌ No results found"

        raw_results = "\n\n---\n\n".join(results)
        summary_prompt = f"""Based on these search results, give a clear 
organized summary answering: "{query}"

{raw_results}

Write clean bullet points. Be concise but complete."""

        if groq_client:
            try:
                response = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": summary_prompt}],
                    max_tokens=1024
                )
                return f"🌐 *{query}*\n\n{response.choices[0].message.content.strip()}"
            except:
                pass

        return f"🌐 *{query}*:\n\n" + "\n\n".join(results[:3])
    except Exception as e:
        return f"❌ Search failed: {str(e)}"

# ── System Tools ──────────────────────────────────────────
def run_command(command: str) -> str:
    dangerous = ["rm -rf /", "mkfs", "dd if=", ":(){:|:&};:"]
    for d in dangerous:
        if d in command:
            return f"❌ Blocked dangerous command"
    try:
        result = subprocess.run(
            command, shell=True,
            capture_output=True, text=True, timeout=30
        )
        output = result.stdout or result.stderr
        return output[:3000] if output else "Command ran with no output"
    except subprocess.TimeoutExpired:
        return "⏰ Timed out after 30 seconds"
    except Exception as e:
        return f"❌ Error: {str(e)}"

def run_python_code(code: str) -> str:
    filename = f"generated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
    filepath = os.path.expanduser(f"~/myclaw_code/{filename}")
    os.makedirs(os.path.expanduser("~/myclaw_code"), exist_ok=True)

    with open(filepath, 'w') as f:
        f.write(code)

    try:
        result = subprocess.run(
            f"python3 {filepath}",
            shell=True, capture_output=True, text=True, timeout=30
        )
        output = result.stdout or result.stderr or "No output"
        return (
            f"✅ Saved: `{filepath}`\n\n"
            f"```python\n{code}\n```\n\n"
            f"📤 Output:\n```\n{output[:2000]}\n```"
        )
    except Exception as e:
        return f"✅ Saved: {filepath}\n❌ Error: {str(e)}"

def get_system_stats() -> str:
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    return f"""📊 *System Stats*
🔲 CPU: {cpu}%
💾 RAM: {ram.used // (1024**3)}GB / {ram.total // (1024**3)}GB ({ram.percent}%)
💿 Disk: {disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB ({disk.percent}%)
⏰ {datetime.now().strftime('%A %d %B, %H:%M:%S')}""".strip()

# ── AI Brain ──────────────────────────────────────────────
def think(user_message: str) -> dict:
    past_convos = search_conversations(user_message)
    known_facts = search_facts(user_message)

    memory_context = ""
    if known_facts:
        memory_context += f"\nKnown facts about user:\n{known_facts}\n"
    if past_convos:
        memory_context += f"\n{past_convos}\n"

    system = f"""You are MyClaw, an autonomous AI agent on Ubuntu Linux.
You control the user's PC, search web, manage GitHub, and remember things.
{memory_context}

Reply ONLY in this exact format:

ACTION: <action>
VALUE: <value>

Available actions:
- RUN_COMMAND: run bash/terminal command
- GET_STATS: show CPU/RAM/disk
- GET_PROCESSES: show top processes
- WRITE_AND_RUN_CODE: write and run complete python code
- WEB_SEARCH: search the internet
- TAKE_SCREENSHOT: take screenshot of screen
- CONTROL_PC: control PC (open/close apps, volume, workspace, lock)
- GITHUB_LIST: list github repos
- GITHUB_PUSH: push code to github (VALUE format: filename|code|repo_name)
- REMEMBER_FACT: save important fact about user
- CHAT: general conversation

Examples:
User: take a screenshot
ACTION: TAKE_SCREENSHOT
VALUE: none

User: open firefox
ACTION: CONTROL_PC
VALUE: open firefox

User: increase volume
ACTION: CONTROL_PC
VALUE: volume up

User: switch to workspace 2
ACTION: CONTROL_PC
VALUE: workspace 2

User: push my last generated code to github
ACTION: GITHUB_PUSH
VALUE: latest_code.py|code here|repo_name

User: list my repos
ACTION: GITHUB_LIST
VALUE: none

User: what processes are using most cpu
ACTION: GET_PROCESSES
VALUE: none
"""

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_message}
    ]

    # Try Groq first
    if groq_client:
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                max_tokens=1024
            )
            reply = response.choices[0].message.content.strip()
            print(f"✅ Used Groq (fast)")
        except Exception as e:
            print(f"⚠️ Groq failed: {e} — falling back to local")
            reply = _local_think(messages)
    else:
        reply = _local_think(messages)

    return _parse_reply(reply)

def _local_think(messages: list) -> str:
    print("🔄 Using local model...")
    response = ollama.chat(
        model="qwen2.5-coder:7b",
        messages=messages
    )
    return response["message"]["content"].strip()

def _parse_reply(reply: str) -> dict:
    action = "CHAT"
    value = reply
    value_lines = []
    found_value = False

    for line in reply.split('\n'):
        if line.startswith("ACTION:"):
            action = line.replace("ACTION:", "").strip()
        elif line.startswith("VALUE:"):
            value = line.replace("VALUE:", "").strip()
            found_value = True
        elif found_value:
            value_lines.append(line)

    if value_lines:
        value = value + "\n" + "\n".join(value_lines)

    return {"action": action, "value": value}

# ── Execute ───────────────────────────────────────────────
def execute(decision: dict) -> tuple:
    """Returns (text_result, file_path_or_None)"""
    action = decision["action"]
    value = decision["value"]

    if action == "GET_STATS":
        return get_system_stats(), None

    elif action == "GET_PROCESSES":
        return get_top_processes(), None

    elif action == "RUN_COMMAND":
        return f"✅ Ran: `{value}`\n\n{run_command(value)}", None

    elif action == "WRITE_AND_RUN_CODE":
        return run_python_code(value), None

    elif action == "WEB_SEARCH":
        return web_search(value), None

    elif action == "TAKE_SCREENSHOT":
        path = take_screenshot()
        if path:
            return "📸 Screenshot taken!", path
        return "❌ Screenshot failed. Is DISPLAY set?", None

    elif action == "CONTROL_PC":
        return control_pc(value), None

    elif action == "GITHUB_LIST":
        return list_github_repos(), None

    elif action == "GITHUB_PUSH":
        parts = value.split("|")
        if len(parts) >= 2:
            fname = parts[0].strip()
            code = parts[1].strip()
            repo = parts[2].strip() if len(parts) > 2 else None
            return github_push_code(fname, code, repo), None
        return "❌ Invalid format for GitHub push", None

    elif action == "REMEMBER_FACT":
        save_fact(value)
        return f"📝 Remembered:\n_{value}_", None

    elif action == "CHAT":
        return value, None

    else:
        return value, None

# ── Send Reply With Retry ─────────────────────────────────
async def send_reply(update: Update, text: str, file_path: str = None,
                     retries: int = 3):
    for attempt in range(retries):
        try:
            # Send photo if screenshot
            if file_path and os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    await update.message.reply_photo(f)

            # Send text in chunks if too long
            if len(text) > 4000:
                chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
                for chunk in chunks:
                    await update.message.reply_text(
                        chunk, parse_mode='Markdown'
                    )
            else:
                await update.message.reply_text(
                    text, parse_mode='Markdown'
                )
            return
        except Exception as e:
            if attempt < retries - 1:
                print(f"⚠️ Send attempt {attempt + 1} failed, retrying...")
                await asyncio.sleep(2)
            else:
                try:
                    await update.message.reply_text(text[:4000])
                except:
                    print("❌ Failed to send message")

# ── Telegram Handler ──────────────────────────────────────
async def handle_message(update: Update,
                         context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        return

    user_message = update.message.text
    await send_reply(update, "🤔 thinking...")

    try:
        decision = think(user_message)
        text_result, file_path = execute(decision)
        save_conversation(user_message, text_result)
        await send_reply(update, text_result, file_path)
    except Exception as e:
        await send_reply(update, f"❌ Error: {str(e)}")

# ── Start ─────────────────────────────────────────────────
def main():
    print("=" * 40)
    print("🤖 MyClaw Agent Starting...")
    print(f"⚡ Groq: {'Connected' if groq_client else 'Not configured'}")
    print(f"🐙 GitHub: {'Connected' if github_client else 'Not configured'}")
    print("📱 Message your Telegram bot!")
    print("=" * 40)

    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .build()
    )
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    print("✅ Ready!")
    app.run_polling()

if __name__ == "__main__":
    main()