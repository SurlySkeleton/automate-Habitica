#!/usr/bin/env python3
"""
Create simple weekday To-Dos in Habitica with a formatted title,
a stylized checklist, hard difficulty, and a short daily quote in the notes.

Config via environment variables:
- HABITICA_USER_ID
- HABITICA_API_TOKEN
- DAYS_AHEAD (optional, default 7)
- QUOTES_SOURCE (optional) -> 'quotable' to fetch from https://api.quotable.io/random
"""

import os
import requests
import random
from datetime import datetime, timedelta

# ─── CONFIG ─────────────────────────────────────────────────────────────────
USER_ID = os.getenv("HABITICA_USER_ID")
API_TOKEN = os.getenv("HABITICA_API_TOKEN")

DAYS_AHEAD = int(os.getenv("DAYS_AHEAD", "7"))  # change to 1 for quick tests
QUOTES_SOURCE = os.getenv("QUOTES_SOURCE", "").lower()  # 'quotable' to fetch remote quote

API_URL = "https://habitica.com/api/v3/tasks/user"

HEADERS = {
    "x-api-user": USER_ID,
    "x-api-key": API_TOKEN,
    "x-client": f"{USER_ID}-habitica-seeder",
    "Content-Type": "application/json",
}

# Checklist exactly as you requested
CHECKLIST_ITEMS = [
    "## Life",
    "—",
    "## Work",
    "——— 🍅",
    "## Family",
    "—",
    "## Friends",
    "—",
    "## Health",
    "—",
]

# A small fallback pool of fun/short quotes if you don't enable a quotes API.
LOCAL_QUOTES = [
    "Tiny wins are still progress — celebrate them.",
    "Do the thing you told yourself you'd do yesterday.",
    "Progress > perfection. One step counts.",
    "Breathe. Focus. Ship something small.",
    "Treat today like a project you can finish."
]

# ─── QUOTE FETCHER ───────────────────────────────────────────────────────────
def fetch_quote(source="local"):
    if source == "quotable":
        try:
            print("DEBUG: Attempting to fetch quote from Quotable...")
            response = requests.get("https://api.quotable.io/random", timeout=10)
            print(f"DEBUG: Response status = {response.status_code}")
            response.raise_for_status()
            data = response.json()
            quote = f"{data['content']} — {data['author']}"
            print(f"DEBUG: Successfully fetched quote: {quote}")
            return quote
        except Exception as e:
            print(f"DEBUG: Failed to fetch from Quotable: {e}")
    # fallback
    print("DEBUG: Falling back to local quote...")
    return random.choice(LOCAL_QUOTES)


# ─── PAYLOAD HELPERS ────────────────────────────────────────────────────────
def make_task_payload(due_dt):
    weekday = due_dt.strftime("%A").upper()            # e.g. SUNDAY
    title = f"# {weekday}"                             # e.g. "# SUNDAY"
    notes = get_quote()                                # fun notes / quote

    checklist_payload = [{"text": item} for item in CHECKLIST_ITEMS]

    return {
        "type": "todo",
        "text": title,
        "notes": notes,
        "date": due_dt.strftime("%Y-%m-%dT00:00:00.000Z"),
        "checklist": checklist_payload,
        "priority": 2,   # Hard
    }

def create_task(payload):
    print("DEBUG: Sending payload to Habitica:")
    print(payload)
    resp = requests.post(API_URL, json=payload, headers=HEADERS, timeout=15)
    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print("ERROR response from Habitica:", resp.text)
        raise e
    return resp.json()

def main():
    if not USER_ID or not API_TOKEN:
        print("ERROR: Set HABITICA_USER_ID and HABITICA_API_TOKEN environment variables.")
        exit(1)

    today = datetime.utcnow().date()
    for offset in range(1, DAYS_AHEAD + 1):
        dt = today + timedelta(days=offset)
        payload = make_task_payload(dt)
        result = create_task(payload)
        print(f"Created: {payload['text']} → {result['data']['id']}")

if __name__ == "__main__":
    main()
