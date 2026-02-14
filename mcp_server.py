#!/home/cia/myclaw/venv/bin/python3
# -*- coding: utf-8 -*-
# kvchClaw MCP Server
# Exposes kvchClaw tools to any MCP compatible AI
# Works with Claude Desktop, Cursor, VS Code Cline, and more
#
# Setup in Claude Desktop:
# Add to claude_desktop_config.json:
# {
#   "mcpServers": {
#     "kvclaw": {
#       "command": "/home/YOUR_USER/myclaw/mcp_server.py"
#     }
#   }
# }

import os
import sys
import subprocess
import psutil
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/myclaw"))
os.chdir(os.path.expanduser("~/myclaw"))

from dotenv import load_dotenv
load_dotenv(os.path.expanduser("~/myclaw/.env"))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

# Load plugins
from plugins.loader import load_plugins, find_plugin
PLUGINS = load_plugins()

app = Server("kvclaw")

# ── Tool Definitions ──────────────────────────────────────

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    tools = [
        types.Tool(
            name="run_command",
            description="Run a bash command on the Linux PC and return output",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to run"
                    }
                },
                "required": ["command"]
            }
        ),
        types.Tool(
            name="get_system_stats",
            description="Get current CPU, RAM and disk usage of the Linux PC",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="get_top_processes",
            description="Get the top processes using most CPU and RAM",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="read_file",
            description="Read the contents of a file on the Linux PC",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Full path to the file to read"
                    }
                },
                "required": ["filepath"]
            }
        ),
        types.Tool(
            name="list_files",
            description="List files and folders in a directory on the Linux PC",
            inputSchema={
                "type": "object",
                "properties": {
                    "dirpath": {
                        "type": "string",
                        "description": "Full path to the directory"
                    }
                },
                "required": ["dirpath"]
            }
        ),
        types.Tool(
            name="write_file",
            description="Write content to a file on the Linux PC",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Full path to the file to write"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    }
                },
                "required": ["filepath", "content"]
            }
        ),
        types.Tool(
            name="web_search",
            description="Search the internet and return summarized results",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="control_pc",
            description="Control the PC - open or close apps, change volume, switch workspace, lock screen",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Control command like: open firefox, increase volume, lock screen, switch to workspace 2"
                    }
                },
                "required": ["command"]
            }
        ),
        types.Tool(
            name="run_python",
            description="Write and execute Python code on the Linux PC",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute"
                    }
                },
                "required": ["code"]
            }
        ),
        types.Tool(
            name="get_changelog",
            description="Get a summary of what the user worked on today or this week",
            inputSchema={
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "description": "today, yesterday, or week",
                        "enum": ["today", "yesterday", "week"]
                    }
                }
            }
        ),
        types.Tool(
            name="organize_folder",
            description="Organize a folder by automatically sorting files into subfolders by type",
            inputSchema={
                "type": "object",
                "properties": {
                    "folder": {
                        "type": "string",
                        "description": "Folder path to organize, e.g. ~/Downloads or downloads"
                    }
                },
                "required": ["folder"]
            }
        ),
        types.Tool(
            name="pc_intelligence",
            description="Explain what is happening on the PC in plain English - why is it slow, suspicious activity, network usage",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Question about PC behavior"
                    }
                },
                "required": ["question"]
            }
        ),
    ]
    return tools

# ── Tool Implementations ──────────────────────────────────

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:

    def result(text):
        return [types.TextContent(type="text", text=str(text))]

    try:

        if name == "run_command":
            command = arguments["command"]
            dangerous = ["rm -rf /", "mkfs", "dd if=", ":(){:|:&};:"]
            for d in dangerous:
                if d in command:
                    return result("Blocked: dangerous command")
            try:
                output = subprocess.run(
                    command, shell=True,
                    capture_output=True, text=True, timeout=30
                )
                return result(output.stdout or output.stderr or "No output")
            except subprocess.TimeoutExpired:
                return result("Timed out after 30 seconds")

        elif name == "get_system_stats":
            cpu = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            return result(
                "System Stats\n"
                "CPU: " + str(cpu) + "%\n"
                "RAM: " + str(ram.used // (1024**3)) + "GB / "
                + str(ram.total // (1024**3)) + "GB ("
                + str(ram.percent) + "%)\n"
                "Disk: " + str(disk.used // (1024**3)) + "GB / "
                + str(disk.total // (1024**3)) + "GB ("
                + str(disk.percent) + "%)\n"
                "Time: " + datetime.now().strftime("%A %d %B %H:%M:%S")
            )

        elif name == "get_top_processes":
            processes = []
            for proc in psutil.process_iter(
                ["pid", "name", "cpu_percent", "memory_percent"]
            ):
                try:
                    processes.append(proc.info)
                except:
                    pass
            top = sorted(
                processes,
                key=lambda x: x["cpu_percent"],
                reverse=True
            )[:5]
            lines = ["Top Processes:"]
            for p in top:
                lines.append(
                    p["name"] + " CPU:" +
                    str(round(p["cpu_percent"], 1)) + "% RAM:" +
                    str(round(p["memory_percent"], 1)) + "%"
                )
            return result("\n".join(lines))

        elif name == "read_file":
            filepath = os.path.expanduser(arguments["filepath"])
            if not os.path.exists(filepath):
                return result("File not found: " + filepath)
            with open(filepath, "r") as f:
                content = f.read()
            lines = content.split("\n")
            if len(lines) > 100:
                preview = "\n".join(lines[:100])
                return result(preview + "\n\n... " + str(len(lines) - 100) + " more lines")
            return result(content)

        elif name == "list_files":
            dirpath = os.path.expanduser(arguments["dirpath"])
            if not os.path.exists(dirpath):
                return result("Directory not found: " + dirpath)
            items = os.listdir(dirpath)
            dirs = sorted(["[DIR] " + i for i in items if os.path.isdir(os.path.join(dirpath, i))])
            files = sorted(["[FILE] " + i for i in items if os.path.isfile(os.path.join(dirpath, i))])
            return result(dirpath + "\n\n" + "\n".join(dirs + files))

        elif name == "write_file":
            filepath = os.path.expanduser(arguments["filepath"])
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w") as f:
                f.write(arguments["content"])
            return result("Written to: " + filepath)

        elif name == "web_search":
            try:
                from ddgs import DDGS
                results = []
                with DDGS() as ddgs:
                    for r in ddgs.text(arguments["query"], max_results=5):
                        results.append(r["title"] + "\n" + r["body"] + "\n" + r["href"])
                return result("\n\n---\n\n".join(results))
            except Exception as e:
                return result("Search failed: " + str(e))

        elif name == "control_pc":
            command = arguments["command"].lower()
            import re
            if "volume" in command:
                nums = re.findall(r"\d+", command)
                if "up" in command or "increase" in command:
                    subprocess.run("pactl set-sink-volume @DEFAULT_SINK@ +10%", shell=True)
                    return result("Volume increased")
                elif "down" in command or "decrease" in command:
                    subprocess.run("pactl set-sink-volume @DEFAULT_SINK@ -10%", shell=True)
                    return result("Volume decreased")
                elif nums:
                    subprocess.run("pactl set-sink-volume @DEFAULT_SINK@ " + nums[0] + "%", shell=True)
                    return result("Volume set to " + nums[0] + "%")
            elif "lock" in command:
                subprocess.run("DISPLAY=:0 i3lock", shell=True)
                return result("Screen locked")
            elif "open" in command:
                app = command.replace("open", "").strip()
                subprocess.Popen("DISPLAY=:0 " + app, shell=True)
                return result("Opening " + app)
            elif "workspace" in command:
                nums = re.findall(r"\d+", command)
                if nums:
                    subprocess.run("DISPLAY=:0 i3-msg workspace " + nums[0], shell=True)
                    return result("Switched to workspace " + nums[0])
            return result("Command executed: " + command)

        elif name == "run_python":
            code = arguments["code"]
            filename = "mcp_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".py"
            filepath = os.path.expanduser("~/myclaw_code/" + filename)
            os.makedirs(os.path.expanduser("~/myclaw_code"), exist_ok=True)
            with open(filepath, "w") as f:
                f.write(code)
            output = subprocess.run(
                "python3 " + filepath,
                shell=True, capture_output=True,
                text=True, timeout=30
            )
            return result(output.stdout or output.stderr or "No output")

        elif name == "get_changelog":
            from plugins.changelog import generate_report
            period = arguments.get("period", "today")
            days = 7 if period == "week" else 2 if period == "yesterday" else 1
            return result(generate_report(days=days))

        elif name == "organize_folder":
            plugin = find_plugin(PLUGINS, "ORGANIZE_FOLDER", arguments["folder"])
            if plugin:
                result_text, _ = plugin.execute(arguments["folder"])
                return result(result_text)
            return result("Organizer plugin not found")

        elif name == "pc_intelligence":
            plugin = find_plugin(PLUGINS, "SYSWHISPER", arguments["question"])
            if plugin:
                result_text, _ = plugin.execute(arguments["question"])
                return result(result_text)
            return result("SysWhisper plugin not found")

        else:
            return result("Unknown tool: " + name)

    except Exception as e:
        return result("Error: " + str(e))

# ── Run Server ────────────────────────────────────────────
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
