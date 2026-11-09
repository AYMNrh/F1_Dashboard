"""Discover existing recordings without copying or rewriting race data."""
import hashlib
import json
import logging
import sqlite3
import time
import zlib
from collections import OrderedDict
from contextlib import closing
from datetime import datetime
from pathlib import Path

from .data import ROOT, Replay

TERMINAL = {"Finished", "Finalised", "Finalized", "Ends", "Ended"}


class SessionLibrary:
    def __init__(self, default, root=None):
        self.default = Path(default).resolve()
        self.root = Path(root) if root else ROOT / "data"
        self.entries = []
        self.paths = {}
        self.cache = OrderedDict()
        self.updated = 0

    def sessions(self):
        if time.monotonic() - self.updated < 2:
            return self.entries
        entries, paths = [], {}
        candidates = {path.resolve() for path in self.root.rglob("*.sqlite")}
        candidates.add(self.default)
        for path in sorted(candidates):
            if not path.is_file():
                continue
            try:
                with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=2)) as db:
                    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='captures'").fetchone():
                        continue
                    first = db.execute("SELECT id,received_utc FROM captures ORDER BY id LIMIT 1").fetchone()
                    last = db.execute("SELECT id,received_utc,session_key FROM captures ORDER BY id DESC LIMIT 1").fetchone()
                    if not first or not last:
                        continue
                    fields = {name: json.loads(zlib.decompress(blob)) for name, blob in db.execute(
                        "SELECT t.name,p.json_zlib FROM topics t JOIN payloads p ON p.hash=t.payload_hash "
                        "WHERE capture_id=? AND t.name IN ('SessionInfo','SessionStatus')", (last[0],))}
                    info = fields.get("SessionInfo")
                    if not info:
                        continue
                    count = db.execute("SELECT count(*) FROM captures").fetchone()[0]
                    lap_row = db.execute("SELECT p.json_zlib FROM topics t JOIN payloads p ON p.hash=t.payload_hash "
                                         "WHERE capture_id=? AND t.name='LapCount'", (first[0],)).fetchone()
                    first_lap = (json.loads(zlib.decompress(lap_row[0])) or {}).get("CurrentLap") if lap_row else None
                identifier = hashlib.sha256(str(path).encode()).hexdigest()[:16]
                status = (fields.get("SessionStatus") or {}).get("Status") or info.get("SessionStatus", "Unknown")
                completed = status in TERMINAL or info.get("SessionStatus") in TERMINAL
                entry = {"id": identifier, "key": str(last[2]), "meeting": info.get("Meeting", {}).get("Name", "Unknown meeting"),
                    "name": info.get("Name", "Session"), "date": info.get("StartDate", first[1])[:10],
                    "start": datetime.fromisoformat(first[1]).timestamp(), "end": datetime.fromisoformat(last[1]).timestamp(),
                    "first_lap": first_lap, "captures": count, "status": status, "completed": completed,
                    "default": path == self.default, "bytes": path.stat().st_size}
                entries.append(entry)
                paths[identifier] = path
            except (sqlite3.Error, ValueError, KeyError, OSError) as exc:
                logging.warning("Unable to inspect recording %s: %s", path.name, exc)
        self.entries = sorted(entries, key=lambda entry: (entry["date"], entry["start"]), reverse=True)
        self.paths = paths
        self.updated = time.monotonic()
        return self.entries

    def resolve(self, identifier=None, key=None):
        entries = self.sessions()
        entry = next((row for row in entries if row["id"] == identifier), None) if identifier else None
        if identifier and entry is None:
            raise ValueError("Unknown saved session")
        if entry is None and key:
            entry = next((row for row in entries if row["key"] == key), None)
        if entry is None and not key:
            entry = next((row for row in entries if row["default"]), None)
        if entry is None:
            raise ValueError("No recorded captures available for this session yet")
        identifier = entry["id"]
        if identifier not in self.cache:
            self.cache[identifier] = Replay(self.paths[identifier])
            while len(self.cache) > 2:
                self.cache.popitem(last=False)
        self.cache.move_to_end(identifier)
        return self.cache[identifier], entry
