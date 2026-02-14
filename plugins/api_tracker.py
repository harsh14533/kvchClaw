# plugins/api_tracker.py
# Personal API Cost and Usage Tracker
# Tracks Groq, Gemini, Mistral free tier usage
# Warns before you hit limits

import os
import sqlite3
from datetime import datetime, timedelta
from plugins.base import Plugin

DB_PATH = os.path.expanduser("~/myclaw/api_tracker.db")

# Free tier limits
API_LIMITS = {
    "groq":    {"daily": 14400, "label": "Groq (llama-3.3-70b)"},
    "gemini":  {"daily": 1500,  "label": "Gemini (gemini-2.0-flash)"},
    "mistral": {"daily": 500,   "label": "Mistral (mistral-small)"},
    "local":   {"daily": 99999, "label": "Local Ollama"},
}

# ── Database ──────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS api_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            date TEXT,
            api_name TEXT,
            tokens_used INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            api_name TEXT,
            total_calls INTEGER DEFAULT 0,
            UNIQUE(date, api_name)
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ── Track Usage ───────────────────────────────────────────
def record_api_call(api_name: str, tokens: int = 0):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Insert raw call
        c.execute("""
            INSERT INTO api_usage (timestamp, date, api_name, tokens_used)
            VALUES (?, ?, ?, ?)
        """, (now, today, api_name, tokens))

        # Update daily summary
        c.execute("""
            INSERT INTO daily_summary (date, api_name, total_calls)
            VALUES (?, ?, 1)
            ON CONFLICT(date, api_name)
            DO UPDATE SET total_calls = total_calls + 1
        """, (today, api_name))

        conn.commit()
        conn.close()
    except Exception as e:
        print("API tracker error: " + str(e))

# ── Query Usage ───────────────────────────────────────────
def get_today_usage():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        c.execute("""
            SELECT api_name, total_calls
            FROM daily_summary
            WHERE date = ?
        """, (today,))
        rows = c.fetchall()
        conn.close()
        return {row[0]: row[1] for row in rows}
    except:
        return {}

def get_week_usage():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        c.execute("""
            SELECT date, api_name, total_calls
            FROM daily_summary
            WHERE date >= ?
            ORDER BY date DESC
        """, (week_ago,))
        rows = c.fetchall()
        conn.close()
        return rows
    except:
        return []

def get_hourly_usage(api_name: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        hour_ago = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        c.execute("""
            SELECT COUNT(*)
            FROM api_usage
            WHERE api_name = ? AND timestamp >= ?
        """, (api_name, hour_ago))
        count = c.fetchone()[0]
        conn.close()
        return count
    except:
        return 0

def check_limits_warning():
    today_usage = get_today_usage()
    warnings = []
    for api, usage in today_usage.items():
        if api not in API_LIMITS:
            continue
        limit = API_LIMITS[api]["daily"]
        if limit == 99999:
            continue
        percent = (usage / limit) * 100
        if percent >= 80:
            warnings.append(
                api.capitalize() + ": " +
                str(usage) + "/" + str(limit) +
                " (" + str(round(percent, 1)) + "%) WARNING"
            )
    return warnings

# ── Report Generator ──────────────────────────────────────
def generate_today_report():
    today_usage = get_today_usage()
    now = datetime.now().strftime("%H:%M")
    report = "*API Usage Today (" + now + ")*\n\n"

    if not today_usage:
        report += "No API calls recorded yet today.\n"
        report += "kvchClaw tracks usage automatically as you use it."
        return report

    total_calls = 0
    for api_name, limit_info in API_LIMITS.items():
        calls = today_usage.get(api_name, 0)
        total_calls += calls
        limit = limit_info["daily"]
        label = limit_info["label"]

        if limit == 99999:
            report += label + ": " + str(calls) + " calls (unlimited)\n"
            continue

        percent = round((calls / limit) * 100, 1)
        remaining = limit - calls

        # Progress bar
        filled = int(percent / 10)
        bar = "[" + "#" * filled + "-" * (10 - filled) + "]"

        # Status emoji
        if percent >= 90:
            status = "CRITICAL"
        elif percent >= 80:
            status = "WARNING"
        elif percent >= 50:
            status = "MODERATE"
        else:
            status = "HEALTHY"

        report += (
            label + "\n" +
            bar + " " + str(percent) + "%\n" +
            str(calls) + " used / " +
            str(remaining) + " remaining\n" +
            "Status: " + status + "\n\n"
        )

    report += "Total calls today: " + str(total_calls) + "\n"

    # Projection
    hour = datetime.now().hour
    if hour > 0 and total_calls > 0:
        rate_per_hour = total_calls / hour
        projected = int(rate_per_hour * 24)
        report += "Projected daily total: " + str(projected) + " calls"

    return report

def generate_week_report():
    rows = get_week_usage()
    if not rows:
        return "No usage data for this week yet."

    report = "*API Usage This Week*\n\n"

    # Group by date
    by_date = {}
    for date, api, calls in rows:
        if date not in by_date:
            by_date[date] = {}
        by_date[date][api] = calls

    for date in sorted(by_date.keys(), reverse=True):
        day_data = by_date[date]
        total = sum(day_data.values())
        report += date + " — " + str(total) + " total calls\n"
        for api, calls in sorted(day_data.items()):
            report += "  " + api + ": " + str(calls) + "\n"
        report += "\n"

    return report

def generate_recommendation():
    today_usage = get_today_usage()
    if not today_usage:
        return "No usage data yet to make recommendations."

    report = "*API Optimization Tips*\n\n"
    groq = today_usage.get("groq", 0)
    gemini = today_usage.get("gemini", 0)
    mistral = today_usage.get("mistral", 0)

    groq_pct = (groq / 14400) * 100
    gemini_pct = (gemini / 1500) * 100

    if gemini_pct > groq_pct * 2:
        report += "Gemini is being used more than Groq. "
        report += "Groq has a much higher limit (14,400 vs 1,500). "
        report += "Consider using Groq as primary.\n\n"
    elif groq_pct > 70:
        report += "Groq usage is high. Gemini and Mistral can handle overflow.\n\n"
    else:
        report += "Your API usage is well balanced. No changes needed.\n\n"

    # Best API for time of day
    hour = datetime.now().hour
    if 9 <= hour <= 17:
        report += "Peak hours: Groq recommended (fastest response)\n"
    else:
        report += "Off-peak hours: Any API works well\n"

    return report

# ── Plugin Class ──────────────────────────────────────────
class APITrackerPlugin(Plugin):
    name = "API_TRACKER"
    description = (
        "Track API usage and free tier limits for Groq, Gemini and Mistral. "
        "Shows how many requests used today, weekly summary, "
        "warns before hitting free tier limits."
    )
    triggers = [
        "api usage", "api cost", "api tracker", "free tier",
        "how much api", "api limit", "groq usage", "gemini usage",
        "mistral usage", "api health", "api status today",
        "how many requests", "api this week", "api recommendation"
    ]

    def execute(self, value: str) -> tuple:
        try:
            val = value.lower().strip()

            if "week" in val:
                return generate_week_report(), None

            if "recommend" in val or "tip" in val or "optimize" in val:
                return generate_recommendation(), None

            if "warn" in val or "limit" in val or "critical" in val:
                warnings = check_limits_warning()
                if warnings:
                    return "API Limit Warnings:\n\n" + "\n".join(warnings), None
                return "All APIs are within safe limits.", None

            # Default — today's report
            return generate_today_report(), None

        except Exception as e:
            return "API tracker error: " + str(e), None
