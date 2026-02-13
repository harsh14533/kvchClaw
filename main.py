import os
import subprocess
import psutil
import ollama
import chromadb
import asyncio
from groq import Groq
from github import Github
from datetime import datetime
from telegram import Update, Bot
from telegram.ext import (
    Application, MessageHandler,
    filters, ContextTypes
)
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import whisper

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

# ── Load Whisper Model (once at startup) ──────────────────
print("🎤 Loading voice model...")
whisper_model = whisper.load_model("base")
print("✅ Voice model ready")

# ── Memory Setup ──────────────────────────────────────────
memory_client = chromadb.PersistentClient(path="./memory")
conversation_memory = memory_client.get_or_create_collection("conversations")
facts_memory = memory_client.get_or_create_collection("facts")
# ── Short Term Conversation History ───────────────────────
# Keeps last 10 messages in memory for context
conversation_history = []
MAX_HISTORY = 10

def add_to_history(role: str, content: str):
    """Add message to short term history"""
    conversation_history.append({
        "role": role,
        "content": content
    })
    # Keep only last MAX_HISTORY messages
    if len(conversation_history) > MAX_HISTORY:
        conversation_history.pop(0)

def get_history() -> list:
    """Get current conversation history"""
    return conversation_history.copy()

def clear_history():
    """Clear conversation history"""
    conversation_history.clear()

def save_conversation(user_msg: str, bot_reply: str):
    timestamp = str(datetime.now().timestamp())
    conversation_memory.add(
        documents=[f"User: {user_msg}\nkvchClaw: {bot_reply}"],
        ids=[timestamp],
        metadatas={"time": str(datetime.now()),
                   "date": datetime.now().strftime("%Y-%m-%d")}
    )

def save_fact(text: str):
    facts_memory.add(
        documents=[text],
        ids=[str(datetime.now().timestamp())],
        metadatas={"time": str(datetime.now())}
    )

def search_conversations(query: str) -> str:
    try:
        results = conversation_memory.query(
            query_texts=[query], n_results=4
        )
        if results["documents"][0]:
            return "Past conversations:\n" + \
                   "\n---\n".join(results["documents"][0])
    except:
        pass
    return ""

def search_facts(query: str) -> str:
    try:
        results = facts_memory.query(
            query_texts=[query], n_results=3
        )
        if results["documents"][0]:
            return "\n".join(results["documents"][0])
    except:
        pass
    return ""

# ── Voice Transcription ───────────────────────────────────
async def transcribe_voice(file_path: str) -> str:
    """Transcribe voice message using Whisper"""
    try:
        result = whisper_model.transcribe(file_path)
        return result["text"].strip()
    except Exception as e:
        return f"Could not transcribe: {str(e)}"

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

        raw = "\n\n---\n\n".join(results)
        prompt = f"""Summarize these search results for: "{query}"
{raw}
Write clean bullet points. Be concise."""

        if groq_client:
            try:
                response = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1024
                )
                return f"🌐 *{query}*\n\n" + \
                       response.choices[0].message.content.strip()
            except:
                pass
        return f"🌐 *{query}*:\n\n" + "\n\n".join(results[:3])
    except Exception as e:
        return f"❌ Search failed: {str(e)}"

# ── Screenshot ────────────────────────────────────────────
def take_screenshot() -> str:
    try:
        path = os.path.expanduser("~/myclaw_screenshot.png")
        subprocess.run(
            f"DISPLAY=:0 scrot {path}",
            shell=True, capture_output=True
        )
        return path if os.path.exists(path) else None
    except:
        return None

# ── PC Control ────────────────────────────────────────────
def control_pc(command: str) -> str:
    try:
        import re
        cmd = command.lower()

        if "volume" in cmd:
            nums = re.findall(r'\d+', cmd)
            if "up" in cmd or "increase" in cmd:
                subprocess.run(
                    "pactl set-sink-volume @DEFAULT_SINK@ +10%",
                    shell=True)
                return "🔊 Volume increased 10%"
            elif "down" in cmd or "decrease" in cmd:
                subprocess.run(
                    "pactl set-sink-volume @DEFAULT_SINK@ -10%",
                    shell=True)
                return "🔉 Volume decreased 10%"
            elif "mute" in cmd:
                subprocess.run(
                    "pactl set-sink-mute @DEFAULT_SINK@ toggle",
                    shell=True)
                return "🔇 Volume toggled mute"
            elif nums:
                subprocess.run(
                    f"pactl set-sink-volume @DEFAULT_SINK@ {nums[0]}%",
                    shell=True)
                return f"🔊 Volume set to {nums[0]}%"

        elif "lock" in cmd:
            subprocess.run("DISPLAY=:0 i3lock", shell=True)
            return "🔒 Screen locked"

        elif "open" in cmd:
            app = cmd.replace("open", "").strip()
            subprocess.Popen(f"DISPLAY=:0 {app}", shell=True)
            return f"✅ Opening {app}"

        elif "close" in cmd or "kill" in cmd:
            app = cmd.replace("close","").replace("kill","").strip()
            subprocess.run(f"pkill {app}", shell=True)
            return f"✅ Closed {app}"

        elif "workspace" in cmd:
            nums = re.findall(r'\d+', cmd)
            if nums:
                subprocess.run(
                    f"DISPLAY=:0 i3-msg workspace {nums[0]}",
                    shell=True)
                return f"✅ Switched to workspace {nums[0]}"

        else:
            result = subprocess.run(
                f"DISPLAY=:0 {command}",
                shell=True, capture_output=True,
                text=True, timeout=10
            )
            return result.stdout or result.stderr or "✅ Done"

    except Exception as e:
        return f"❌ Control failed: {str(e)}"

# ── GitHub Tools ──────────────────────────────────────────
def github_push_code(filename: str, code: str,
                     repo_name: str = None,
                     commit_msg: str = None) -> str:
    if not github_client:
        return "❌ GitHub not configured"
    try:
        user = github_client.get_user()
        if repo_name:
            repo = user.get_repo(repo_name)
        else:
            repos = list(user.get_repos())
            if not repos:
                return "❌ No repos found"
            repo = repos[0]

        message = commit_msg or \
                  f"kvchClaw: add {filename} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        try:
            existing = repo.get_contents(filename)
            repo.update_file(existing.path, message, code, existing.sha)
            return f"✅ Updated `{filename}` in `{repo.name}`"
        except:
            repo.create_file(filename, message, code)
            return (
                f"✅ Pushed `{filename}` to `{repo.name}`\n"
                f"🔗 https://github.com/{GITHUB_USERNAME}/{repo.name}"
            )
    except Exception as e:
        return f"❌ GitHub error: {str(e)}"

def auto_git_commit(filepath: str, code: str) -> str:
    """Auto commit generated code to kvchClaw repo"""
    if not github_client:
        return ""
    try:
        filename = f"generated_code/{os.path.basename(filepath)}"
        result = github_push_code(
            filename, code,
            repo_name="kvchClaw",
            commit_msg=f"auto: generated code {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        return f"\n\n🐙 {result}"
    except:
        return ""

def list_github_repos() -> str:
    if not github_client:
        return "❌ GitHub not configured"
    try:
        user = github_client.get_user()
        repos = list(user.get_repos())
        repo_list = "\n".join([
            f"• {r.name} ⭐{r.stargazers_count}"
            for r in repos[:10]
        ])
        return f"📁 Your repos:\n{repo_list}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

# ── System Tools ──────────────────────────────────────────
def run_command(command: str) -> str:
    dangerous = ["rm -rf /", "mkfs", "dd if=", ":(){:|:&};:"]
    for d in dangerous:
        if d in command:
            return "❌ Blocked dangerous command"
    try:
        result = subprocess.run(
            command, shell=True,
            capture_output=True, text=True, timeout=30
        )
        output = result.stdout or result.stderr
        return output[:3000] if output else "No output"
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
            shell=True, capture_output=True,
            text=True, timeout=30
        )
        output = result.stdout or result.stderr or "No output"

        # Auto commit to GitHub
        git_result = auto_git_commit(filepath, code)

        return (
            f"✅ Saved: `{filepath}`\n\n"
            f"```python\n{code}\n```\n\n"
            f"📤 Output:\n```\n{output[:2000]}\n```"
            f"{git_result}"
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

def get_top_processes() -> str:
    processes = []
    for proc in psutil.process_iter(
        ['pid', 'name', 'cpu_percent', 'memory_percent']
    ):
        try:
            processes.append(proc.info)
        except:
            pass
    top = sorted(
        processes, key=lambda x: x['cpu_percent'], reverse=True
    )[:5]
    result = "⚡ *Top Processes:*\n"
    for p in top:
        result += (
            f"• {p['name']} (PID:{p['pid']}) "
            f"CPU:{p['cpu_percent']:.1f}% "
            f"RAM:{p['memory_percent']:.1f}%\n"
        )
    return result

# ── Scheduled Tasks ───────────────────────────────────────
async def scheduled_system_check(bot: Bot):
    """Runs every hour — warns if system is stressed"""
    try:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        warnings = []
        if cpu > 85:
            warnings.append(f"⚠️ CPU is very high: {cpu}%")
        if ram.percent > 85:
            warnings.append(f"⚠️ RAM is very high: {ram.percent}%")
        if disk.percent > 90:
            warnings.append(f"⚠️ Disk is almost full: {disk.percent}%")

        if warnings:
            message = "🚨 *System Alert*\n\n" + "\n".join(warnings)
            await bot.send_message(
                chat_id=ALLOWED_USER_ID,
                text=message,
                parse_mode='Markdown'
            )
            print(f"⚠️ System alert sent: {warnings}")
    except Exception as e:
        print(f"❌ Scheduled check failed: {e}")

async def scheduled_morning_summary(bot: Bot):
    """Runs every morning at 9am"""
    try:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        message = f"""🌅 *Good Morning!*

📊 Your system is looking like this:
🔲 CPU: {cpu}%
💾 RAM: {ram.percent}% used
💿 Disk: {disk.percent}% used

kvchClaw is running and ready.
What do you want to do today?"""

        await bot.send_message(
            chat_id=ALLOWED_USER_ID,
            text=message,
            parse_mode='Markdown'
        )
        print("🌅 Morning summary sent")
    except Exception as e:
        print(f"❌ Morning summary failed: {e}")

# ── AI Brain ──────────────────────────────────────────────
def think(user_message: str) -> dict:
    past_convos = search_conversations(user_message)
    known_facts = search_facts(user_message)

    memory_context = ""
    if known_facts:
        memory_context += f"\nKnown facts:\n{known_facts}\n"
    if past_convos:
        memory_context += f"\n{past_convos}\n"

    system = f"""You are kvchClaw, an autonomous AI agent on Ubuntu Linux.
You control the user's PC, search web, manage GitHub, remember things.
{memory_context}

Reply ONLY in this exact format:

ACTION: <action>
VALUE: <value>

Actions:
- RUN_COMMAND: bash/terminal command
- GET_STATS: system CPU/RAM/disk
- GET_PROCESSES: top processes
- WRITE_AND_RUN_CODE: write complete python code
- WEB_SEARCH: search internet
- TAKE_SCREENSHOT: screenshot
- CONTROL_PC: open/close apps, volume, workspace, lock
- GITHUB_LIST: list repos
- GITHUB_PUSH: push code (VALUE: filename|code|repo)
- REMEMBER_FACT: save fact about user
- CHAT: general conversation
"""

    # Build messages with full conversation history
    messages = [{"role": "system", "content": system}]
    
    # Add last 10 messages for context
    messages.extend(get_history())
    
    # Add current message
    messages.append({"role": "user", "content": user_message})

    if groq_client:
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                max_tokens=1024
            )
            reply = response.choices[0].message.content.strip()
            print("✅ Used Groq (fast)")
        except Exception as e:
            print(f"⚠️ Groq failed: {e} — using local")
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
        return ("📸 Screenshot taken!", path) if path \
               else ("❌ Screenshot failed", None)
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
        return "❌ Invalid GitHub push format", None
    elif action == "REMEMBER_FACT":
        save_fact(value)
        return f"📝 Remembered:\n_{value}_", None
    elif action == "CHAT":
        return value, None
    elif action == "CLEAR_HISTORY":
        clear_history()
        return "🧹 Conversation history cleared! Fresh start.", None
    else:
        return value, None

# ── Send Reply With Retry ─────────────────────────────────
async def send_reply(update: Update, text: str,
                     file_path: str = None, retries: int = 3):
    for attempt in range(retries):
        try:
            if file_path and os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    await update.message.reply_photo(f)

            if len(text) > 4000:
                chunks = [text[i:i+4000]
                         for i in range(0, len(text), 4000)]
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
                print(f"⚠️ Retry {attempt + 1}...")
                await asyncio.sleep(2)
            else:
                try:
                    await update.message.reply_text(text[:4000])
                except:
                    print("❌ Failed to send message")

# ── Text Message Handler ──────────────────────────────────
async def handle_message(update: Update,
                         context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        return

    user_message = update.message.text
    await send_reply(update, "🤔 thinking...")

    try:
        # Add user message to history BEFORE thinking
        add_to_history("user", user_message)
        
        decision = think(user_message)
        text_result, file_path = execute(decision)
        
        # Add AI response to history AFTER thinking
        add_to_history("assistant", text_result[:500])
        
        # Save to long term memory too
        save_conversation(user_message, text_result)
        
        await send_reply(update, text_result, file_path)
    except Exception as e:
        await send_reply(update, f"❌ Error: {str(e)}")

# ── Voice Message Handler ─────────────────────────────────
async def handle_voice(update: Update,
                       context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        return

    await send_reply(update, "🎤 Transcribing your voice...")

    try:
        # Download voice file from Telegram
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        voice_path = os.path.expanduser("~/myclaw_voice.ogg")
        await file.download_to_drive(voice_path)

        # Transcribe with Whisper
        text = await transcribe_voice(voice_path)
        await send_reply(update, f"🎤 I heard: _{text}_")

       # Add transcribed voice to history
        add_to_history("user", f"[Voice] {text}")
        
        decision = think(text)
        text_result, file_path = execute(decision)
        
        # Add response to history
        add_to_history("assistant", text_result[:500])
        
        save_conversation(f"[Voice] {text}", text_result)
        await send_reply(update, text_result, file_path) 

    except Exception as e:
        await send_reply(update, f"❌ Voice error: {str(e)}")

# ── Start ─────────────────────────────────────────────────
async def post_init(application: Application):
    """Runs after event loop starts — safe place to start scheduler"""
    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        scheduled_system_check,
        'interval',
        hours=1,
        args=[application.bot]
    )

    scheduler.add_job(
        scheduled_morning_summary,
        'cron',
        hour=9,
        minute=0,
        args=[application.bot]
    )

    scheduler.start()
    print("⏰ Scheduler running:")
    print("   • System health check every hour")
    print("   • Morning summary every day at 9am")

def main():
    print("=" * 40)
    print("🤖 kvchClaw Agent Starting...")
    print(f"⚡ Groq: {'Connected' if groq_client else 'Not configured'}")
    print(f"🐙 GitHub: {'Connected' if github_client else 'Not configured'}")
    print("🎤 Voice: Ready (Whisper)")
    print("⏰ Scheduler: Starting...")
    print("=" * 40)

    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .post_init(post_init)
        .build()
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    app.add_handler(
        MessageHandler(filters.VOICE, handle_voice)
    )

    print("✅ Ready! Send a message or voice note.")
    app.run_polling()

if __name__ == "__main__":
    main()
  