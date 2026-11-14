# CS 361 Calendar Microservice

A Flask service that stores calendar events for multiple client apps. Each client gets its own calendar, and clients talk to the service over HTTP

## Requirements

- Python 3.10 or newer (3.11+ recommended)
- Flask 2.2 or newer (see `requirements.txt`)

## Setup

Use a separate environment for this service. Pick **one** of the options below.

**venv**
```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**conda**
```bash
conda create -n calendar-svc python=3.13
conda activate calendar-svc
pip install -r requirements.txt
```

## Running

```bash
python app.py
```

The service runs at `http://localhost:8000`.

## Calendars

Each calendar is one JSON file in `data/events/`, named by its calendar ID:

```
data/events/
  example.json    ← sample data
  persinaj.json
  holmanm.json
  oladokuni.json
  caudillj.json
```

- **The files are the list of calendars.** If there is no file for an ID, requests for that ID return `404 Calendar not found`.
- **Calendar IDs** must be lowercase letters, numbers, `-` or `_` only (for example `persinaj`). Any other ID returns `404`.

### Adding a calendar

Create a file containing an empty JSON array:

```bash
echo "[]" > data/events/<calendar_id>.json
```

The service picks it up on the next request. No restart is needed.

## Event format

Events are modeled on JSCalendar ([RFC 8984](https://www.rfc-editor.org/rfc/rfc8984)):

```json
{
  "@type": "calendarEvent",
  "uid": "a8df6573-0474-496d-8496-033ad45d7fea",
  "updated": "2026-11-01T12:00:00Z",
  "title": "Team Planning Meeting",
  "participants": ["Dan", "Liv"],
  "description": "Weekly sync.",
  "start": "2026-11-05T10:00:00",
  "timeZone": "America/New_York",
  "durationMinutes": 60,
  "location": "Conference Room B",
  "status": "confirmed",
  "deletedAt": null
}
```

| Field | Notes |
|---|---|
| `uid` | Unique ID, created by the service |
| `updated` | UTC timestamp of the last change, set by the service |
| `start` | Local date and time, with no offset; read it together with `timeZone` |
| `timeZone` | IANA name, e.g. `America/New_York` |
| `durationMinutes` | Whole minutes |
| `status` | `confirmed`, `tentative`, or `cancelled` |
| `deletedAt` | `null`, or the UTC time the event was deleted (see below) |

## Delete and restore

Deletes are **soft deletes**. A deleted event is hidden right away but stays restorable for **10 seconds** (`RESTORE_WINDOW_SECONDS` in `app.py`). After that, the service permanently removes it the next time that calendar is saved.

**For client apps:** if you show an Undo button, make sure it disappears *before* 10 seconds, and leave some margin for network delay.

## API

**In progress.** All routes are scoped to a calendar:

```
/calendars/<calendar_id>/events
```

Full endpoint documentation will be added as each route is finished.
