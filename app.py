"""Flask microservice that stores calendar events, one JSON file per calendar."""

from flask import Flask, abort, jsonify, request
from werkzeug.exceptions import HTTPException
from storage import EventStore
from pathlib import Path
from datetime import datetime, timedelta, timezone
import re
import uuid

app = Flask(__name__)

stores = {}
RESTORE_WINDOW_SECONDS = 10
DATA_DIR = Path(__file__).parent / "data" / "events"
REQUIRED_FIELDS = ("title", "start", "timeZone", "durationMinutes")
EDITABLE_FIELDS = {"title", "participants", "description", "start", "timeZone", "durationMinutes", "location", "status"}


### CALENDAR FUNCTIONS ###

def get_store(calendar_id):
    """
    Return the EventStore for `calendar_id`, or abort with 404 if the calendar doesn't exist.
    """
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
    """
    Remove events that were deleted more than RESTORE_WINDOW_SECONDS ago.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=RESTORE_WINDOW_SECONDS)
    events[:] = [
        e for e in events
        if e.get("deletedAt") is None
        #Convert Z for older python versions
        or datetime.fromisoformat(e["deletedAt"].replace("Z", "+00:00")) > cutoff
    ]

def find_event(events, uid, include_deleted=False):
    for e in events:
        if e["uid"] == uid and (include_deleted or e.get("deletedAt") is None):
            return e
    abort(404, description="Event not found")

def read_event_fields(required=()):
    """
    Abort with 400 if the object isn't JSON or is missing `required` fields.
    """
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        abort(400, description="Request body must be a JSON object")

    missing = [field for field in required if field not in body]
    if missing:
        abort(400, description=f"Missing fields: {', '.join(missing)}")

    return body


### ERROR HANDLING ###

@app.errorhandler(HTTPException)
def json_error(e):
    return jsonify(error=e.description), e.code


### API ENDPOINTS ###

# LIST EVENTS
@app.get("/calendars/<calendar_id>/events")
def list_events(calendar_id):
    """
    Return all events on the calendar that aren't deleted.
    """
    events = get_store(calendar_id).load()
    return jsonify([event for event in events if event.get("deletedAt") is None])

# GET ONE EVENT
@app.get("/calendars/<calendar_id>/events/<uid>")
def get_event(calendar_id, uid):
    """
    Return one event, or 404 if it doesn't exist or is deleted.
    """
    events = get_store(calendar_id).load()
    return jsonify(find_event(events, uid))

# CREATE EVENT
@app.post("/calendars/<calendar_id>/events")
def create_event(calendar_id):
    """
    Create an event from the JSON body and return it with status 201.
    """
    store = get_store(calendar_id)
    body = read_event_fields(required=REQUIRED_FIELDS)

    def change(events):
        purge_deleted(events)
        now = utc_now()
        event = {
            "@type": "calendarEvent",
            "uid": str(uuid.uuid4()),
            "updated": now,
            "title": body["title"],
            "participants": body.get("participants", []),
            "description": body.get("description", ""),
            "start": body["start"],
            "timeZone": body["timeZone"],
            "durationMinutes": body["durationMinutes"],
            "location": body.get("location", ""),
            "status": body.get("status", "confirmed"),
            "deletedAt": None,
        }
        events.append(event)
        return event

    return jsonify(store.update(change)), 201

# UPDATE EVENT
@app.patch("/calendars/<calendar_id>/events/<uid>")
def update_event(calendar_id, uid):
    """
    Change only the fields in the JSON body and return the updated event
    """
    store = get_store(calendar_id)
    body = read_event_fields()

    def change(events):
        purge_deleted(events)
        event = find_event(events, uid)
        event.update({key: value for key, value in body.items() if key in EDITABLE_FIELDS})
        event["updated"] = utc_now()
        return event

    return jsonify(store.update(change))

# DELETE EVENT
@app.delete("/calendars/<calendar_id>/events/<uid>")
def delete_event(calendar_id, uid):
    """
    Soft-delete an event by setting deletedAt, and return it.
    The event can be restored within the restore window.
    """
    store = get_store(calendar_id)

    def change(events):
        purge_deleted(events)
        event = find_event(events, uid)
        now = utc_now()
        event["deletedAt"] = now
        event["updated"] = now
        return event

    return jsonify(store.update(change))

# RESTORE SOFT-DELETED EVENT
@app.post("/calendars/<calendar_id>/events/<uid>/restore")
def restore_event(calendar_id, uid):
    """
    Undo a delete and return the event, or 404 if it isn't deleted or the window has passed.
    """
    store = get_store(calendar_id)

    def change(events):
        purge_deleted(events)
        event = find_event(events, uid, include_deleted=True)
        if event.get("deletedAt") is None:
            abort(404, description="No deleted event to restore")
        event["deletedAt"] = None
        event["updated"] = utc_now()
        return event

    return jsonify(store.update(change))

if __name__ == "__main__":
    app.run(debug=True, port=8000)
