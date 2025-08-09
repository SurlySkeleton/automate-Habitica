import os
import requests
from datetime import datetime, timedelta

USER_ID = os.getenv("HABITICA_USER_ID")
API_TOKEN = os.getenv("HABITICA_API_TOKEN")

DAYS_AHEAD = 7
CHECKLIST_ITEMS = ["Life", "Work", "Family", "Friends"]
API_URL = "https://habitica.com/api/v3/tasks/user"

HEADERS = {
    "x-api-user": USER_ID,
    "x-api-key": API_TOKEN,
    "x-client": f"{USER_ID}-habitica-seeder",  # required by Habitica
    "Content-Type": "application/json",
}

def iso_date(dt):
    return dt.strftime("%Y-%m-%dT00:00:00.000Z")

def make_task_payload(due_dt):
    weekday = due_dt.strftime("%A").upper()
    date_str = due_dt.strftime("%m/%d/%Y")
    return {
        "type": "todo",
        "text": f"{weekday} {date_str}",
        "notes": "Auto-generated checklist for daily review.",
        "date": iso_date(due_dt),
        "checklist": [{"text": item} for item in CHECKLIST_ITEMS],
        "priority": 1.5,
    }

def create_task(payload):
    print("DEBUG: Sending payload to Habitica:")
    print(payload)
    resp = requests.post(API_URL, json=payload, headers=HEADERS)
    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print("ERROR response from Habitica:", resp.text)
        raise e
    return resp.json()

def main():
    today = datetime.utcnow().date()
    for offset in range(1, DAYS_AHEAD + 1):
        dt = today + timedelta(days=offset)
        payload = make_task_payload(dt)
        result = create_task(payload)
        print(f"Created: {payload['text']} → {result['data']['id']}")

if __name__ == "__main__":
    if not USER_ID or not API_TOKEN:
        print("ERROR: Set HABITICA_USER_ID and HABITICA_API_TOKEN environment variables.")
        exit(1)
    main()
