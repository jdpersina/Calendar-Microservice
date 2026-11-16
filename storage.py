import json
import os
import tempfile
import threading
from pathlib import Path


class EventStore:

    def __init__(self, path):
        self.path = Path(path)
        self._lock = threading.Lock() #Lock to prevent overwriting files for multiple requests at once

    def load(self):
        """
        Return the calendar's events as a list of dicts.
        """
        with self._lock:
            return self._read()

    def update(self, change):
        """
        Read the events, apply `change`, save them, and return.
        """
        with self._lock:
            events = self._read()
            result = change(events)
            self._write(events)
            return result

    def _read(self):
        """
        Load events from the file
        """
        if not self.path.exists():
            return []
        with self.path.open(encoding="utf-8") as f:
            return json.load(f)

    def _write(self, events):
        """
        Save events to a temp file, then swap it into place so a crash can't leave a half-written file.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=self.path.parent, prefix=".events-", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2, ensure_ascii=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, self.path)
