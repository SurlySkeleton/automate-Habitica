#!/usr/bin/env python3
"""
Create simple weekday To-Dos in Habitica with a formatted title,
a stylized checklist, hard difficulty, and a short daily quote in the notes.

Config via environment variables:
- HABITICA_USER_ID
- HABITICA_API_TOKEN
- DAYS_AHEAD (optional, default 7)
- QUOTES_SOURCE (optional) -> 'repo' to read quotes.json in repo root (default)
- DEBUG (optional) -> 'true' to print debug info
"""

import os
import json
import requests
import random
from datetime import datetime, timedelta, time

# ─── CONFIG ─────────────────────────────────────────────────────────────────
USER_ID = os.getenv("HABITICA_USER_ID")
API_TOKEN = os.getenv("HABITICA_API_TOKEN")

DAYS_AHEAD = int(os.getenv("DAYS_AHEAD", "1"))  # change to 1 for quick tests
QUOTES_SOURCE = os.getenv("QUOTES_SOURCE", "repo").lower()  # default to repo
DEBUG = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")

API_URL = "https://habitica.com/api/v3/tasks/user"
REPO_QUOTES_PATH = "quotes.json"  # file in repo root

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

# A small fallback pool of fun/short quotes if repo file is missing or invalid.
LOCAL_QUOTES = [
    "Tiny wins are still progress — celebrate them.",
    "Do the thing you told yourself you'd do yesterday.",
    "Progress > perfection. One step counts.",
    "Breathe. Focus. Ship something small.",
    "Treat today like a project you can finish."
]


# ─── QUOTE FETCHER (reads repo file) ─────────────────────────────────────────
def fetch_quote(source="repo"):
    """
    Read a random quote. If source == 'repo', try to load REPO_QUOTES_PATH.
    Falls back to LOCAL_QUOTES on any failure.
    """
    if source == "repo":
        try:
            if DEBUG:
                print(f"DEBUG: Attempting to read quotes from {REPO_QUOTES_PATH} ...")
            with open(REPO_QUOTES_PATH, "r", encoding="utf-8") as f:
                pool = json.load(f)
            if isinstance(pool, list) and pool:
                quote = random.choice(pool)
                if DEBUG:
                    print(f"DEBUG: Selected quote from repo: {quote}")
                return quote
            else:
                if DEBUG:
                    print("DEBUG: Repo quotes file parsed but was not a non-empty list.")
        except Exception as e:
            if DEBUG:
                print(f"DEBUG: Failed to read/parse {REPO_QUOTES_PATH}: {e}")
    # final fallback
    if DEBUG:
        print("DEBUG: Falling back to LOCAL_QUOTES...")
    return random.choice(LOCAL_QUOTES)


# ─── PAYLOAD HELPERS ────────────────────────────────────────────────────────
def make_task_payload(due_date):
    """
    due_date: a datetime.date representing the target calendar day.
    We will set the task 'date' to noon UTC on that day to avoid timezone shifts
    that can make clients display the previous local day.
    """
    weekday = due_date.strftime("%A").upper()            # e.g. SUNDAY
    title = f"# {weekday}"                               # e.g. "# SUNDAY"
    notes = fetch_quote(QUOTES_SOURCE)

    # set date-time to 12:00:00 UTC on that calendar day
    dt_noon_utc = datetime.combine(due_date, time(hour=12))
    iso_dt = dt_noon_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    checklist_payload = [{"text": item} for item in CHECKLIST_ITEMS]

    return {
        "type": "todo",
        "text": title,
        "notes": notes,
        "date": iso_dt,
        "checklist": checklist_payload,
        "priority": 2,   # Hard
    }


def create_task(payload):
    if DEBUG:
        print("DEBUG: Sending payload to Habitica:")
        print(payload)
    resp = requests.post(API_URL, json=payload, headers=HEADERS, timeout=15)
    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        # Print Habitica's response body for debugging before re-raising
        print("ERROR response from Habitica:", resp.text)
        raise e
    return resp.json()


def main():
    if not USER_ID or not API_TOKEN:
        print("ERROR: Set HABITICA_USER_ID and HABITICA_API_TOKEN environment variables.")
        exit(1)

    # Using UTC date here (datetime.utcnow().date()) — we then set task time to noon UTC
    # which prevents clients in negative timezones from displaying the previous day.
    today_utc = datetime.utcnow().date()
    for offset in range(1, DAYS_AHEAD + 1):
        due = today_utc + timedelta(days=offset)
        payload = make_task_payload(due)
        result = create_task(payload)
        print(f"Created: {payload['text']} → {result['data']['id']}")


if __name__ == "__main__":
    main()
