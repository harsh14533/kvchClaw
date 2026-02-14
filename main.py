# -*- coding: utf-8 -*-
import os
import subprocess
import psutil
import chromadb
import asyncio
import threading
import time
from groq import Groq
from github import Github, Auth
from datetime import datetime
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import whisper
from google import genai as google_genai
from mistralai import Mistral
from plugins.loader import load_plugins, get_plugin_prompts, find_plugin

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ALLOWED_USER_ID = int(os.getenv("TELEGRAM_USER_ID"))
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
gemini_client = google_genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
mistral_client = Mistral(api_key=MISTRAL_API_KEY) if MISTRAL_API_KEY else None
github_client = Github(auth=Auth.Token(GITHUB_TOKEN)) if GITHUB_TOKEN else None

api_stats = {
    "groq": {"calls": 0, "fails": 0},
    "gemini": {"calls": 0, "fails": 0},
    "mistral": {"calls": 0, "fails": 0},
    "local": {"calls": 0, "fails": 0}
}

print("Loading voice model...")
whisper_model = whisper.load_model("base")
print("Voice model ready")

PLUGINS = load_plugins()
print(str(len(PLUGINS)) + " plugins loaded")

health_status = {
    "last_heartbeat": datetime.now(),
    "messages_handled": 0,
    "errors": 0,
    "start_time": datetime.now()
}

def update_heartbeat():
    health_status["last_heartbeat"] = datetime.now()

def get_uptime():
    delta = datetime.now() - health_status["start_time"]
    hours = int(delta.total_seconds() // 3600)
    minutes = int((delta.total_seconds() % 3600) // 60)
    return str(hours) + "h " + str(minutes) + "m"

def health_check_loop():
    while True:
        time.sleep(60)
        last = health_status["last_heartbeat"]
        seconds_since = (datetime.now() - last).total_seconds()
        if seconds_since > 300:
            print("Bot frozen. Restarting...")
            os._exit(1)

health_thread = threading.Thread(target=health_check_loop, daemon=True)
health_thread.start()

conversation_history = []
MAX_HISTORY = 10

def add_to_history(role, content):
    conversation_history.append({"role": role, "content": content})
    if len(conversation_history) > MAX_HISTORY:
        conversation_history.pop(0)

def get_history():
    return conversation_history.copy()

def clear_history():
    conversation_history.clear()

memory_client = chromadb.PersistentClient(path="./memory")
conversation_memory = memory_client.get_or_create_collection("conversations")
facts_memory = memory_client.get_or_create_collection("facts")

def save_conversation(user_msg, bot_reply):
    timestamp = str(datetime.now().timestamp())
    conversation_memory.add(
        documents=["User: " + user_msg + "\nkvchClaw: " + bot_reply],
        ids=[timestamp],
        metadatas={"time": str(datetime.now()), "date": datetime.now().strftime("%Y-%m-%d")}
    )

def save_fact(text):
    facts_memory.add(
        documents=[text],
        ids=[str(datetime.now().timestamp())],
        metadatas={"time": str(datetime.now())}
    )

def search_conversations(query):
    try:
        results = conversation_memory.query(query_texts=[query], n_results=4)
        if results["documents"][0]:
            return "Past conversations:\n" + "\n---\n".join(results["documents"][0])
    except:
        pass
    return ""

def search_facts(query):
    try:
        results = facts_memory.query(query_texts=[query], n_results=3)
        if results["documents"][0]:
            return "\n".join(results["documents"][0])
    except:
        pass
    return ""

def call_groq(messages):
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=1024
    )
    try:
        from plugins.api_tracker import record_api_call
        record_api_call("groq")
    except:
        pass
    return response.choices[0].message.content.strip()

def call_gemini(messages):
    prompt = ""
    for msg in messages:
        if msg["role"] == "system":
            prompt += "System: " + msg["content"] + "\n\n"
        elif msg["role"] == "user":
            prompt += "User: " + msg["content"] + "\n"
        elif msg["role"] == "assistant":
            prompt += "Assistant: " + msg["content"] + "\n"
    response = gemini_client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )
    try:
        from plugins.api_tracker import record_api_call
        record_api_call("gemini")
    except:
        pass
    return response.text.strip()

def call_mistral(messages):
    response = mistral_client.chat.complete(
        model="mistral-small-latest",
        messages=messages,
        max_tokens=1024
    )
    try:
        from plugins.api_tracker import record_api_call
        record_api_call("mistral")
    except:
        pass
    return response.choices[0].message.content.strip()

def call_local(messages):
    try:
        import ollama
        response = ollama.chat(model="qwen2.5-coder:7b", messages=messages)
        return response["message"]["content"].strip()
    except Exception as e:
        return "All APIs failed: " + str(e)

def get_system_stats():
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return (
        "*System Stats*\n"
        "CPU: " + str(cpu) + "%\n"
        "RAM: " + str(ram.used // (1024**3)) + "GB / " + str(ram.total // (1024**3)) + "GB (" + str(ram.percent) + "%)\n"
        "Disk: " + str(disk.used // (1024**3)) + "GB / " + str(disk.total // (1024**3)) + "GB (" + str(disk.percent) + "%)\n"
        "Time: " + datetime.now().strftime("%A %d %B, %H:%M:%S")
    )

def get_top_processes():
    processes = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            processes.append(proc.info)
        except:
            pass
    top = sorted(processes, key=lambda x: x["cpu_percent"], reverse=True)[:5]
    result = "*Top Processes:*\n"
    for p in top:
        result += "- " + str(p["name"]) + " CPU:" + str(round(p["cpu_percent"],1)) + "% RAM:" + str(round(p["memory_percent"],1)) + "%\n"
    return result

def get_api_status():
    lines = ["*API Status:*"]
    for name, client in [("Groq", groq_client), ("Gemini", gemini_client), ("Mistral", mistral_client)]:
        key = name.lower()
        s = api_stats[key]
        status = "Connected" if client else "Not configured"
        lines.append(name + ": " + status + " (" + str(s["calls"]) + " calls, " + str(s["fails"]) + " fails)")
    s = api_stats["local"]
    lines.append("Local Ollama: fallback (" + str(s["calls"]) + " calls)")
    return "\n".join(lines)

def get_bot_status():
    uptime = get_uptime()
    msgs = health_status["messages_handled"]
    errors = health_status["errors"]
    last = health_status["last_heartbeat"].strftime("%H:%M:%S")
    return (
        "*kvchClaw Status*\n\n"
        "Status: Alive and healthy\n"
        "Uptime: " + uptime + "\n"
        "Messages handled: " + str(msgs) + "\n"
        "Errors: " + str(errors) + "\n"
        "Last heartbeat: " + last + "\n\n" +
        get_api_status()
    )

def run_command(command):
    dangerous = ["rm -rf /", "mkfs", "dd if=", ":(){:|:&};:"]
    for d in dangerous:
        if d in command:
            return "Blocked dangerous command"
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        output = result.stdout or result.stderr
        return output[:3000] if output else "No output"
    except subprocess.TimeoutExpired:
        return "Timed out after 30 seconds"
    except Exception as e:
        return "Error: " + str(e)

def run_python_code(code):
    filename = "generated_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".py"
    filepath = os.path.expanduser("~/myclaw_code/" + filename)
    os.makedirs(os.path.expanduser("~/myclaw_code"), exist_ok=True)
    with open(filepath, "w") as f:
        f.write(code)
    try:
        result = subprocess.run("python3 " + filepath, shell=True, capture_output=True, text=True, timeout=30)
        output = result.stdout or result.stderr or "No output"
        git_result = auto_git_commit(filepath, code)
        return "Saved: " + filepath + "\n\n```python\n" + code + "\n```\n\nOutput:\n```\n" + output[:2000] + "\n```" + git_result
    except Exception as e:
        return "Saved: " + filepath + "\nError: " + str(e)

def take_screenshot():
    try:
        path = os.path.expanduser("~/myclaw_screenshot.png")
        subprocess.run("DISPLAY=:0 scrot " + path, shell=True, capture_output=True)
        return path if os.path.exists(path) else None
    except:
        return None

def read_file(filepath):
    try:
        path = os.path.expanduser(filepath)
        if not os.path.exists(path):
            return "File not found: " + filepath
        with open(path, "r") as f:
            content = f.read()
        lines = content.split("\n")
        preview = "\n".join(lines[:50])
        result = "*" + filepath + "*\n```\n" + preview + "\n```"
        if len(lines) > 50:
            result += "\n\n..." + str(len(lines)-50) + " more lines"
        return result
    except Exception as e:
        return "Could not read file: " + str(e)

def list_files(dirpath):
    try:
        path = os.path.expanduser(dirpath)
        if not os.path.exists(path):
            return "Directory not found: " + dirpath
        items = os.listdir(path)
        dirs = ["[DIR] " + i for i in items if os.path.isdir(os.path.join(path, i))]
        files = ["[FILE] " + i for i in items if os.path.isfile(os.path.join(path, i))]
        return "*" + dirpath + "*\n\n" + "\n".join(sorted(dirs) + sorted(files))[:3000]
    except Exception as e:
        return "Could not list directory: " + str(e)

def control_pc(command):
    try:
        import re
        cmd = command.lower()
        if "volume" in cmd:
            nums = re.findall(r"\d+", cmd)
            if "up" in cmd or "increase" in cmd:
                subprocess.run("pactl set-sink-volume @DEFAULT_SINK@ +10%", shell=True)
                return "Volume increased 10%"
            elif "down" in cmd or "decrease" in cmd:
                subprocess.run("pactl set-sink-volume @DEFAULT_SINK@ -10%", shell=True)
                return "Volume decreased 10%"
            elif "mute" in cmd:
                subprocess.run("pactl set-sink-mute @DEFAULT_SINK@ toggle", shell=True)
                return "Volume toggled mute"
            elif nums:
                subprocess.run("pactl set-sink-volume @DEFAULT_SINK@ " + nums[0] + "%", shell=True)
                return "Volume set to " + nums[0] + "%"
        elif "lock" in cmd:
            subprocess.run("DISPLAY=:0 i3lock", shell=True)
            return "Screen locked"
        elif "open" in cmd:
            app = cmd.replace("open", "").strip()
            subprocess.Popen("DISPLAY=:0 " + app, shell=True)
            return "Opening " + app
        elif "close" in cmd or "kill" in cmd:
            app = cmd.replace("close", "").replace("kill", "").strip()
            subprocess.run("pkill " + app, shell=True)
            return "Closed " + app
        elif "workspace" in cmd:
            nums = re.findall(r"\d+", cmd)
            if nums:
                subprocess.run("DISPLAY=:0 i3-msg workspace " + nums[0], shell=True)
                return "Switched to workspace " + nums[0]
        else:
            result = subprocess.run("DISPLAY=:0 " + command, shell=True, capture_output=True, text=True, timeout=10)
            return result.stdout or result.stderr or "Done"
    except Exception as e:
        return "Control failed: " + str(e)

def web_search(query):
    try:
        from ddgs import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=6):
                results.append(r["title"] + "\n" + r["body"] + "\n" + r["href"])
        if not results:
            return "No results found"
        raw = "\n\n---\n\n".join(results)
        prompt = "Summarize these results for: " + query + "\n" + raw + "\nBe concise with bullet points."
        summary_messages = [{"role": "user", "content": prompt}]
        for api_func in [call_groq, call_gemini, call_mistral]:
            try:
                summary = api_func(summary_messages)
                return "*Web Search: " + query + "*\n\n" + summary
            except:
                continue
        return "*" + query + "*:\n\n" + "\n\n".join(results[:3])
    except Exception as e:
        return "Search failed: " + str(e)

def auto_git_commit(filepath, code):
    if not github_client:
        return ""
    try:
        filename = "generated_code/" + os.path.basename(filepath)
        user = github_client.get_user()
        repo = user.get_repo("kvchClaw")
        message = "auto: " + os.path.basename(filepath)
        try:
            existing = repo.get_contents(filename)
            repo.update_file(existing.path, message, code, existing.sha)
        except:
            repo.create_file(filename, message, code)
        return "\n\nAuto committed to GitHub"
    except:
        return ""

def github_push_code(filename, code, repo_name=None, commit_msg=None):
    if not github_client:
        return "GitHub not configured"
    try:
        user = github_client.get_user()
        repo = user.get_repo(repo_name) if repo_name else list(user.get_repos())[0]
        message = commit_msg or "kvchClaw: " + filename
        try:
            existing = repo.get_contents(filename)
            repo.update_file(existing.path, message, code, existing.sha)
            return "Updated " + filename + " in " + repo.name
        except:
            repo.create_file(filename, message, code)
            return "Pushed " + filename + " to " + repo.name
    except Exception as e:
        return "GitHub error: " + str(e)

def list_github_repos():
    if not github_client:
        return "GitHub not configured"
    try:
        user = github_client.get_user()
        repos = list(user.get_repos())
        repo_list = "\n".join(["- " + r.name + " (" + str(r.stargazers_count) + " stars)" for r in repos[:10]])
        return "*Your repos:*\n" + repo_list
    except Exception as e:
        return "Error: " + str(e)

def think(user_message):
    past_convos = search_conversations(user_message)
    known_facts = search_facts(user_message)
    memory_context = ""
    if known_facts:
        memory_context += "\nKnown facts:\n" + known_facts + "\n"
    if past_convos:
        memory_context += "\n" + past_convos + "\n"
    plugin_actions = get_plugin_prompts(PLUGINS)
    system = (
        "You are kvchClaw, an autonomous AI agent on Ubuntu Linux.\n"
        "You control the user's PC, search web, manage GitHub, and remember things.\n"
        + memory_context +
        "\nReply ONLY in this exact format:\n\n"
        "ACTION: <action>\n"
        "VALUE: <value>\n\n"
        "Built-in actions:\n"
        "- RUN_COMMAND: run bash/terminal command\n"
        "- GET_STATS: system CPU/RAM/disk info\n"
        "- GET_PROCESSES: show top processes\n"
        "- WRITE_AND_RUN_CODE: write and run python code\n"
        "- WEB_SEARCH: search the internet\n"
        "- TAKE_SCREENSHOT: take screenshot\n"
        "- CONTROL_PC: control PC apps volume workspace lock\n"
        "- FILE_READ: read a file\n"
        "- FILE_LIST: list files in directory\n"
        "- GITHUB_LIST: list github repos\n"
        "- GITHUB_PUSH: push code filename|code|repo\n"
        "- REMEMBER_FACT: save fact about user\n"
        "- CLEAR_HISTORY: clear conversation history\n"
        "- API_STATUS: show API status\n"
        "- BOT_STATUS: show bot health\n"
        "- CHAT: general conversation\n"
        "\nPlugin actions:\n" + plugin_actions + "\n"
    )
    messages = [{"role": "system", "content": system}]
    messages.extend(get_history())
    messages.append({"role": "user", "content": user_message})
    apis = []
    if groq_client:
        apis.append(("groq", call_groq))
    if gemini_client:
        apis.append(("gemini", call_gemini))
    if mistral_client:
        apis.append(("mistral", call_mistral))
    apis.append(("local", call_local))
    for api_name, api_func in apis:
        try:
            reply = api_func(messages)
            api_stats[api_name]["calls"] += 1
            print("Used " + api_name)
            return _parse_reply(reply)
        except Exception as e:
            api_stats[api_name]["fails"] += 1
            print(api_name + " failed: " + str(e))
            continue
    return {"action": "CHAT", "value": "All APIs unavailable."}

def _parse_reply(reply):
    action = "CHAT"
    value = reply
    value_lines = []
    found_value = False
    for line in reply.split("\n"):
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

def execute(decision):
    action = decision["action"]
    value = decision["value"]
    if action == "GET_STATS":
        return get_system_stats(), None
    elif action == "GET_PROCESSES":
        return get_top_processes(), None
    elif action == "RUN_COMMAND":
        return "Ran: " + value + "\n\n" + run_command(value), None
    elif action == "WRITE_AND_RUN_CODE":
        return run_python_code(value), None
    elif action == "WEB_SEARCH":
        return web_search(value), None
    elif action == "TAKE_SCREENSHOT":
        path = take_screenshot()
        return ("Screenshot taken!", path) if path else ("Screenshot failed", None)
    elif action == "CONTROL_PC":
        return control_pc(value), None
    elif action == "FILE_READ":
        return read_file(value), None
    elif action == "FILE_LIST":
        return list_files(value), None
    elif action == "GITHUB_LIST":
        return list_github_repos(), None
    elif action == "GITHUB_PUSH":
        parts = value.split("|")
        if len(parts) >= 2:
            return github_push_code(parts[0].strip(), parts[1].strip(), parts[2].strip() if len(parts) > 2 else None), None
        return "Invalid GitHub push format", None
    elif action == "REMEMBER_FACT":
        save_fact(value)
        return "Remembered: " + value, None
    elif action == "CLEAR_HISTORY":
        clear_history()
        return "History cleared!", None
    elif action == "API_STATUS":
        return get_api_status(), None
    elif action == "BOT_STATUS":
        return get_bot_status(), None
    elif action == "CHAT":
        return value, None
    else:
        plugin = find_plugin(PLUGINS, action, value)
        if plugin:
            return plugin.execute(value)
        return value, None

async def transcribe_voice(file_path):
    try:
        result = whisper_model.transcribe(file_path)
        return result["text"].strip()
    except Exception as e:
        return "Could not transcribe: " + str(e)

async def send_reply(update, text, file_path=None, retries=3):
    for attempt in range(retries):
        try:
            if file_path and os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    await update.message.reply_photo(f)
            if len(text) > 4000:
                chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
                for chunk in chunks:
                    await update.message.reply_text(chunk, parse_mode="Markdown")
            else:
                await update.message.reply_text(text, parse_mode="Markdown")
            return
        except Exception as e:
            if attempt < retries - 1:
                await asyncio.sleep(2)
            else:
                try:
                    await update.message.reply_text(text[:4000])
                except:
                    print("Failed to send message")

async def handle_message(update, context):
    if update.effective_user.id != ALLOWED_USER_ID:
        return
    user_message = update.message.text
    await send_reply(update, "Thinking...")
    try:
        update_heartbeat()
        health_status["messages_handled"] += 1
        add_to_history("user", user_message)
        decision = think(user_message)
        text_result, file_path = execute(decision)
        add_to_history("assistant", text_result[:500])
        save_conversation(user_message, text_result)
        await send_reply(update, text_result, file_path)
    except Exception as e:
        health_status["errors"] += 1
        await send_reply(update, "Error: " + str(e))

async def handle_voice(update, context):
    if update.effective_user.id != ALLOWED_USER_ID:
        return
    await send_reply(update, "Transcribing your voice...")
    try:
        update_heartbeat()
        health_status["messages_handled"] += 1
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        voice_path = os.path.expanduser("~/myclaw_voice.ogg")
        await file.download_to_drive(voice_path)
        text = await transcribe_voice(voice_path)
        await send_reply(update, "I heard: " + text)
        add_to_history("user", "[Voice] " + text)
        decision = think(text)
        text_result, file_path = execute(decision)
        add_to_history("assistant", text_result[:500])
        save_conversation("[Voice] " + text, text_result)
        await send_reply(update, text_result, file_path)
    except Exception as e:
        health_status["errors"] += 1
        await send_reply(update, "Voice error: " + str(e))

async def scheduled_system_check(bot):
    try:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        warnings = []
        if cpu > 85:
            warnings.append("CPU very high: " + str(cpu) + "%")
        if ram.percent > 85:
            warnings.append("RAM very high: " + str(ram.percent) + "%")
        if disk.percent > 90:
            warnings.append("Disk almost full: " + str(disk.percent) + "%")
        if warnings:
            await bot.send_message(chat_id=ALLOWED_USER_ID, text="System Alert\n\n" + "\n".join(warnings))
    except Exception as e:
        print("Scheduled check failed: " + str(e))
async def scheduled_morning_summary(bot):
    try:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        msg = (
            "Good Morning!\n\n"
            "System status:\n"
            "CPU: " + str(cpu) + "%\n"
            "RAM: " + str(ram.percent) + "% used\n"
            "Disk: " + str(disk.percent) + "% used\n\n"
            "kvchClaw is ready. What do you want to do today?"
        )
        await bot.send_message(chat_id=ALLOWED_USER_ID, text=msg)
    except Exception as e:
        print("Morning summary failed: " + str(e))

async def scheduled_evening_changelog(bot):
    try:
        from plugins.changelog import generate_report
        report = generate_report(days=1)
        await bot.send_message(
            chat_id=ALLOWED_USER_ID,
            text="Evening Summary\n\n" + report
        )
    except Exception as e:
        print("Evening changelog failed: " + str(e))

async def scheduled_api_check(bot):
    try:
        from plugins.api_tracker import check_limits_warning
        warnings = check_limits_warning()
        if warnings:
            msg = "API Limit Warning\n\n" + "\n".join(warnings)
            await bot.send_message(chat_id=ALLOWED_USER_ID, text=msg)
    except Exception as e:
        print("API check failed: " + str(e))

async def post_init(application):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        scheduled_system_check, "interval",
        hours=1, args=[application.bot]
    )
    scheduler.add_job(
        scheduled_morning_summary, "cron",
        hour=9, minute=0, args=[application.bot]
    )
    scheduler.add_job(
        scheduled_evening_changelog, "cron",
        hour=23, minute=0, args=[application.bot]
    )
    scheduler.add_job(
        scheduled_api_check, "interval",
        hours=3, args=[application.bot]
    )
    scheduler.start()
    print("Scheduler running")

def main():
    print("=" * 40)
    print("kvchClaw Starting...")
    print("Groq:    " + ("OK" if groq_client else "NOT SET"))
    print("Gemini:  " + ("OK" if gemini_client else "NOT SET"))
    print("Mistral: " + ("OK" if mistral_client else "NOT SET"))
    print("GitHub:  " + ("OK" if github_client else "NOT SET"))
    print("Voice:   OK")
    print("Plugins: " + str(len(PLUGINS)) + " loaded")
    print("=" * 40)
    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .connect_timeout(60)
        .read_timeout(60)
        .write_timeout(60)
        .pool_timeout(60)
        .post_init(post_init)
        .build()
    )
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    print("Ready! Send a message or voice note.")
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
