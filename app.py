from flask import Flask, abort, jsonify, request
from storage import EventStore
from pathlib import Path
from datetime import datetime, timedelta, timezone
import re

app = Flask(__name__)

RESTORE_WINDOW_SECONDS = 7
DATA_DIR = Path(__file__).parent / "data" / "events"
stores = {}

def get_store(calendar_id):
    #Preventing unsafe ID input
    if not re.fullmatch(r"[a-z0-9_-]+", calendar_id):
        abort(404, description="Calendar not found")
    
    #Checking if the calendar exists
    path = DATA_DIR / f"{calendar_id}.json"
    if not path.exists():
        abort(404, description="Calendar not found")

    return stores.setdefault(calendar_id, EventStore(path))

def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def purge_deleted(events):
    #Soft-deleted events stay in the file for the undo window, then get dropped the next time anything is saved
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=RESTORE_WINDOW_SECONDS)
    events[:] = [
        e for e in events
        if e.get("deletedAt") is None
        #Convert Z for older python versions
        or datetime.fromisoformat(e["deletedAt"].replace("Z", "+00:00")) > cutoff
    ]

def find_event(events, uid):
    for e in events:
        if e["uid"] == uid:
            return e
    abort(404)

if __name__ == "__main__":
    app.run(debug=True, port=8000)
