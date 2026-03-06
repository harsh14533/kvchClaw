#!/home/cia/myclaw/venv/bin/python3
# -*- coding: utf-8 -*-
# kvchClaw Interactive TUI
# Full screen terminal interface like Claude Code
# Run: python tui.py

import os
import sys
sys.path.insert(0, os.path.expanduser("~/myclaw"))
os.chdir(os.path.expanduser("~/myclaw"))

from dotenv import load_dotenv
load_dotenv(os.path.expanduser("~/myclaw/.env"))

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.columns import Columns
from rich.markdown import Markdown
from rich import box
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.styles import Style
from datetime import datetime
import threading

console = Console()

# Available models
MODELS = {
    "1": {
        "name": "Groq — llama-3.3-70b",
        "api": "groq",
        "description": "Fastest, 14400 req/day free"
    },
    "2": {
        "name": "Gemini — gemini-2.0-flash",
        "api": "gemini",
        "description": "Smart, 1500 req/day free"
    },
    "3": {
        "name": "Mistral — mistral-small",
        "api": "mistral",
        "description": "Balanced, free tier"
    },
    "4": {
        "name": "Local — qwen2.5-coder:7b",
        "api": "local",
        "description": "Offline, no internet needed"
    },
}

# Current selected model
current_model = {"key": "1", "api": "groq", "name": "Groq"}

# Chat history for TUI
tui_history = []

def clear_screen():
    os.system("clear")

def print_header():
    now = datetime.now().strftime("%H:%M:%S")
    header = Text()
    header.append("kvchClaw ", style="bold green")
    header.append("v2.6.0", style="dim green")
    header.append("  |  ", style="dim")
    header.append("Model: ", style="dim")
    header.append(current_model["name"], style="bold cyan")
    header.append("  |  ", style="dim")
    header.append(now, style="dim")
    console.print(Panel(header, box=box.HORIZONTALS, style="green"))

def print_help():
    table = Table(
        title="kvchClaw Commands",
        box=box.ROUNDED,
        style="green",
        title_style="bold green"
    )
    table.add_column("Command", style="cyan", width=20)
    table.add_column("Description", style="white")

    commands = [
        ("/help", "Show this help menu"),
        ("/model", "Switch AI model or API"),
        ("/status", "Show bot health and API usage"),
        ("/clear", "Clear chat history"),
        ("/history", "Show recent conversations"),
        ("/plugins", "List all available plugins"),
        ("/stats", "Show system CPU RAM disk"),
        ("/git", "Show git status of all repos"),
        ("/context", "Save or restore work context"),
        ("/exit or /quit", "Exit kvchClaw"),
        ("", ""),
        ("organize downloads", "Sort files in downloads folder"),
        ("take screenshot", "Capture your screen"),
        ("web search X", "Search the internet"),
        ("what did i work on today", "Show daily changelog"),
        ("api usage today", "Show API consumption"),
        ("git status all", "Check all your git repos"),
        ("save context", "Save current work context"),
        ("weather in X", "Get weather for any city"),
        ("/terminal", "Show live financial markets terminal"),
    ]

    for cmd, desc in commands:
        table.add_row(cmd, desc)

    console.print(table)

def print_model_selector():
    table = Table(
        title="Select AI Model",
        box=box.ROUNDED,
        style="cyan",
        title_style="bold cyan"
    )
    table.add_column("No.", style="bold yellow", width=5)
    table.add_column("Model", style="bold white", width=30)
    table.add_column("Details", style="dim white")

    for key, model in MODELS.items():
        marker = " (active)" if key == current_model["key"] else ""
        table.add_row(key, model["name"] + marker, model["description"])

    console.print(table)
    console.print("[dim]Enter number to select (or Enter to cancel):[/dim] ", end="")

def print_plugins():
    try:
        from plugins.loader import load_plugins
        plugins = load_plugins()
        table = Table(
            title="Active Plugins (" + str(len(plugins)) + ")",
            box=box.ROUNDED,
            style="green",
            title_style="bold green"
        )
        table.add_column("Plugin", style="cyan", width=20)
        table.add_column("Description", style="white")
        table.add_column("Triggers", style="dim", width=30)

        for p in plugins:
            triggers = ", ".join(p.triggers[:3])
            if len(p.triggers) > 3:
                triggers += "..."
            table.add_row(p.name, p.description[:60], triggers)

        console.print(table)
    except Exception as e:
        console.print("[red]Error loading plugins: " + str(e) + "[/red]")

def get_ai_response(user_message):
    try:
        import main as agent

        # Override which API to use based on current model
        original_apis = None

        if current_model["api"] == "groq":
            agent.api_stats  # just access to verify
            response_apis = [("groq", agent.call_groq)] if agent.groq_client else []
        elif current_model["api"] == "gemini":
            response_apis = [("gemini", agent.call_gemini)] if agent.gemini_client else []
        elif current_model["api"] == "mistral":
            response_apis = [("mistral", agent.call_mistral)] if agent.mistral_client else []
        else:
            response_apis = [("local", agent.call_local)]

        # Add fallbacks
        all_apis = [("groq", agent.call_groq), ("gemini", agent.call_gemini),
                    ("mistral", agent.call_mistral), ("local", agent.call_local)]
        for api in all_apis:
            if api not in response_apis:
                response_apis.append(api)

        decision = agent.think(user_message)
        text_result, file_path = agent.execute(decision)
        return text_result, file_path
    except Exception as e:
        return "Error: " + str(e), None

def print_message(role, content, file_path=None):
    if role == "user":
        console.print()
        console.print("[bold cyan]You:[/bold cyan] " + content)
    elif role == "assistant":
        console.print()
        console.print("[bold green]kvchClaw:[/bold green]")
        # Try to render as markdown
        try:
            console.print(Markdown(content))
        except:
            console.print(content)
        if file_path and os.path.exists(file_path):
            console.print("[dim]File saved: " + file_path + "[/dim]")
    elif role == "thinking":
        console.print("[dim green]Thinking...[/dim green]", end="\r")
    elif role == "system":
        console.print("[dim yellow]" + content + "[/dim yellow]")

def print_footer():
    footer = Text()
    footer.append("/help", style="bold cyan")
    footer.append("  /model  /status  /plugins  /clear  /exit", style="dim cyan")
    console.print(Panel(footer, box=box.HORIZONTALS, style="dim green"))

def handle_slash_command(cmd):
    cmd = cmd.strip().lower()

    if cmd in ["/exit", "/quit", "/q"]:
        console.print()
        console.print(Panel(
            "[bold green]Goodbye! kvchClaw shutting down.[/bold green]",
            box=box.ROUNDED
        ))
        sys.exit(0)

    elif cmd == "/help":
        print_help()
        return True

    elif cmd == "/model":
        print_model_selector()
        choice = input().strip()
        if choice in MODELS:
            current_model["key"] = choice
            current_model["api"] = MODELS[choice]["api"]
            current_model["name"] = MODELS[choice]["name"].split(" — ")[0]
            console.print("[green]Switched to: " + MODELS[choice]["name"] + "[/green]")
        else:
            console.print("[dim]No change.[/dim]")
        return True

    elif cmd == "/status":
        try:
            import main as agent
            result = agent.get_bot_status()
            console.print(Panel(result, title="Status", style="green"))
        except Exception as e:
            console.print("[red]Error: " + str(e) + "[/red]")
        return True

    elif cmd == "/stats":
        try:
            import main as agent
            result = agent.get_system_stats()
            console.print(Panel(result, title="System", style="green"))
        except Exception as e:
            console.print("[red]Error: " + str(e) + "[/red]")
        return True

    elif cmd == "/plugins":
        print_plugins()
        return True

    elif cmd == "/clear":
        try:
            import main as agent
            agent.clear_history()
        except:
            pass
        tui_history.clear()
        clear_screen()
        print_header()
        console.print("[dim]History cleared.[/dim]")
        return True

    elif cmd == "/git":
        response, _ = get_ai_response("git status of all projects")
        print_message("assistant", response)
        return True

    elif cmd == "/context":
        response, _ = get_ai_response("save context")
        print_message("assistant", response)
        return True
    elif cmd == "/terminal" or cmd == "/markets":
        try:
            from plugins.financial_terminal import format_terminal_display
            import time
            console.print("[dim]Fetching live market data...[/dim]")
            time.sleep(2)  # Give background thread time
            response = format_terminal_display()
            print_message("assistant", response)
        except Exception as e:
            console.print("[red]Error: " + str(e) + "[/red]")
        return True

    elif cmd == "/history":
        if not tui_history:
            console.print("[dim]No history yet.[/dim]")
        else:
            for item in tui_history[-6:]:
                console.print("[dim cyan]You:[/dim cyan] " + item["user"][:80])
                console.print("[dim green]kvchClaw:[/dim green] " + item["bot"][:80])
                console.print()
        return True

    return False

def main():
    clear_screen()
    print_header()

    # Welcome message
    console.print()
    console.print(Panel(
        "[bold green]Welcome to kvchClaw![/bold green]\n\n"
        "Your personal AI agent for Linux.\n"
        "Type [cyan]/help[/cyan] to see all commands.\n"
        "Type anything to chat or give commands.",
        title="Ready",
        box=box.ROUNDED,
        style="green"
    ))
    console.print()

    # Show model selector on first start
    console.print("[dim]Current model: [cyan]" + current_model["name"] + "[/cyan] — type /model to change[/dim]")
    console.print()

    print_footer()

    # Setup prompt session with history
    history_file = os.path.expanduser("~/myclaw/.tui_history")
    session = PromptSession(
        history=FileHistory(history_file),
        auto_suggest=AutoSuggestFromHistory(),
        style=Style.from_dict({
            "prompt": "bold ansicyan",
        })
    )

    while True:
        try:
            # Get input
            user_input = session.prompt("\nYou: ").strip()

            if not user_input:
                continue

            # Handle slash commands
            if user_input.startswith("/"):
                handle_slash_command(user_input)
                continue

            # Show thinking
            print_message("thinking", "")

            # Get response
            response, file_path = get_ai_response(user_input)

            # Store in history
            tui_history.append({"user": user_input, "bot": response})

            # Print response
            print_message("assistant", response, file_path)

            # Update header time
            console.print()

        except KeyboardInterrupt:
            console.print()
            console.print("[dim]Use /exit to quit.[/dim]")
            continue
        except EOFError:
            console.print()
            console.print("[bold green]Goodbye![/bold green]")
            break
        except Exception as e:
            console.print("[red]Error: " + str(e) + "[/red]")
            continue

if __name__ == "__main__":
    main()
