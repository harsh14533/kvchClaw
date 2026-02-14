#!/home/cia/myclaw/venv/bin/python3
# -*- coding: utf-8 -*-
import sys
import os
sys.path.insert(0, os.path.expanduser("~/myclaw"))
os.chdir(os.path.expanduser("~/myclaw"))

from dotenv import load_dotenv
load_dotenv(os.path.expanduser("~/myclaw/.env"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# Load plugins
from plugins.loader import load_plugins, find_plugin
PLUGINS = load_plugins()

def call_ai(question):
    messages = [
        {
            "role": "system",
            "content": (
                "You are kvchClaw, a personal AI agent on Ubuntu Linux.\n"
                "Answer directly and concisely for terminal use.\n"
                "Plain text only, no markdown formatting.\n"
            )
        },
        {"role": "user", "content": question}
    ]

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
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=messages[0]["content"] + "\n\n" + question
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
                messages=messages,
                max_tokens=1024
            )
            return response.choices[0].message.content.strip()
        except:
            pass

    try:
        import ollama
        response = ollama.chat(
            model="qwen2.5-coder:7b",
            messages=messages
        )
        return response["message"]["content"].strip()
    except:
        return "All APIs unavailable."

def handle_question(question):
    # Check plugins first
    plugin_keywords = {
        "changelog": ["changelog", "what did i work on", "weekly summary",
                      "daily summary", "work summary", "what did i do"],
        "ORGANIZE_FOLDER": ["organize", "sort files", "tidy up"],
        "SYSWHISPER": ["why is my pc", "suspicious", "what happened",
                       "pc report", "pc intelligence", "network activity"],
        "WEATHER": ["weather", "temperature", "forecast"],
        "NOTES": ["note", "my notes", "show notes"],
        "CLEAN_SYSTEM": ["clean system", "free space", "clear cache"],
    }

    question_lower = question.lower()

    for plugin_name, keywords in plugin_keywords.items():
        for keyword in keywords:
            if keyword in question_lower:
                plugin = find_plugin(PLUGINS, plugin_name, question)
                if plugin:
                    result, _ = plugin.execute(question)
                    return result

    # Fall back to AI
    return call_ai(question)

def interactive_mode():
    print("kvchClaw Terminal - type your question or 'exit' to quit")
    print("-" * 50)
    while True:
        try:
            question = input("You: ").strip()
            if not question:
                continue
            if question.lower() in ["exit", "quit", "bye"]:
                print("Goodbye!")
                break
            print("thinking...")
            answer = handle_question(question)
            print("kvchClaw: " + answer)
            print()
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break

def single_question_mode(question):
    answer = handle_question(question)
    print(answer)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        single_question_mode(question)
    else:
        interactive_mode()
