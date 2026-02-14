#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# kvchClaw Terminal Interface
# Usage: python ask.py <your question>
# Or:    ./ask.py <your question>

import sys
import os
from dotenv import load_dotenv

# Load environment
load_dotenv(os.path.expanduser("~/myclaw/.env"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

def think(question):
    system = (
        "You are kvchClaw, a personal AI agent on Ubuntu Linux.\n"
        "Answer the user's question directly and concisely.\n"
        "If they ask to run a command, show the exact command.\n"
        "If they ask to write code, write complete working code.\n"
        "Keep answers short and practical for terminal use.\n"
        "No markdown formatting — plain text only.\n"
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": question}
    ]

    # Try Groq first
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
        except Exception as e:
            print("Groq failed, trying next...")

    # Try Gemini
    if GEMINI_API_KEY:
        try:
            from google import genai as google_genai
            client = google_genai.Client(api_key=GEMINI_API_KEY)
            prompt = system + "\n\nUser: " + question
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            print("Gemini failed, trying next...")

    # Try Mistral
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
        except Exception as e:
            print("Mistral failed, trying local...")

    # Try local Ollama
    try:
        import ollama
        response = ollama.chat(
            model="qwen2.5-coder:7b",
            messages=messages
        )
        return response["message"]["content"].strip()
    except:
        return "All APIs unavailable. Check your .env file."

def interactive_mode():
    print("kvchClaw Terminal — type your question or 'exit' to quit")
    print("-" * 50)
    while True:
        try:
            question = input("You: ").strip()
            if not question:
                continue
            if question.lower() in ["exit", "quit", "bye"]:
                print("Goodbye!")
                break
            print("kvchClaw: thinking...")
            answer = think(question)
            print("kvchClaw: " + answer)
            print()
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break

def single_question_mode(question):
    answer = think(question)
    print(answer)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Direct question mode: ask.py what is my ip
        question = " ".join(sys.argv[1:])
        single_question_mode(question)
    else:
        # Interactive chat mode
        interactive_mode()
