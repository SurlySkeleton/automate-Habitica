#!/usr/bin/env python3
"""
Habitica seeder — single daily forward-populator based on Pacific time.

Behavior:
- Each run creates exactly ONE Todo for (today in America/Los_Angeles) + OFFSET_DAYS.
- Keeps existing formatting: "# WEEKDAY" title, checklist, priority=Hard (2).
- Notes pulled from quotes.json in repo root when QUOTES_SOURCE == "repo".
- Task timestamp is set to 12:00:00 UTC on the due date to avoid timezone off-by-one visuals.

Env/config:
- HABITICA_USER_ID
- HABITICA_API_TOKEN
- OFFSET_DAYS (optional, default 30)  <- number of days ahead (30 for your requested behavior)
- QUOTES_SOURCE (optional, default "repo")
- DEBUG (optional) -> 'true' to print debug info
"""

import os
import json
import requests
import random
from datetime import datetime, timedelta, time
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except Exception:
    ZoneInfo = None

# ─── CONFIG ─────────────────────────────────────────────────────────────────
USER_ID = os.getenv("HABITICA_USER_ID")
API_TOKEN = os.getenv("HABITICA_API_TOKEN")

# Number of days forward relative to today IN PACIFIC TIME. Default 30.
OFFSET_DAYS = int(os.getenv("OFFSET_DAYS", "30"))

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
    "## Work",
    "——— 🍅",
    "## Family",
    "—",
    "## Friends",
    "—",
    "## Health",
    "—",
]

# Fallback quotes if repo file missing
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
    We set the task 'date' to noon UTC on that day to avoid timezone shifts
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
    resp = requests.post(API_URL, json=payload, headers=HEADERS, timeout=20)
    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        # Print Habitica's response body for debugging before re-raising
        print("ERROR response from Habitica:", resp.text)
        raise e
    return resp.json()


# ─── MAIN ───────────────────────────────────────────────────────────────────
def main():
    if not USER_ID or not API_TOKEN:
        print("ERROR: Set HABITICA_USER_ID and HABITICA_API_TOKEN environment variables.")
        exit(1)

    # Determine "today" in Pacific time.
    if ZoneInfo is not None:
        try:
            pacific_tz = ZoneInfo("America/Los_Angeles")
            now_pacific = datetime.now(pacific_tz)
            if DEBUG:
                print(f"DEBUG: Now in Pacific tz = {now_pacific.isoformat()}")
            today_pacific = now_pacific.date()
        except Exception as e:
            if DEBUG:
                print(f"DEBUG: zoneinfo error, falling back to UTC for 'today': {e}")
            today_pacific = datetime.utcnow().date()
    else:
        if DEBUG:
            print("DEBUG: zoneinfo not available; falling back to UTC for 'today'.")
        today_pacific = datetime.utcnow().date()

    # Compute the single due date: today (Pacific) + OFFSET_DAYS
    due = today_pacific + timedelta(days=OFFSET_DAYS)
    if DEBUG:
        print(f"DEBUG: OFFSET_DAYS={OFFSET_DAYS}. Creating task for due={due.isoformat()} (Pacific-based).")

    payload = make_task_payload(due)
    result = create_task(payload)
    print(f"Created: {payload['text']} → {result['data']['id']}")


if __name__ == "__main__":
    main()
