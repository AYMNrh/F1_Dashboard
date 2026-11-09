"""Replay and 4 Hz collection. No third-party Python dependencies."""
from __future__ import annotations

import bisect
import hashlib
import json
import logging
import sqlite3
import threading
import time
import zlib
from collections import OrderedDict
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from record_race import query

ROOT = Path(__file__).resolve().parents[1]
TOPICS = ["ArchiveStatus", "CarData", "ChampionshipPrediction", "DriverList",
          "ExtrapolatedClock", "Heartbeat", "LapCount", "LapSeries", "PitLaneTimeCollection",
          "Position", "RaceControlMessages", "SessionData", "SessionInfo", "SessionStatus",
          "TeamRadio", "TimingAppData", "TimingData", "TimingStats", "TrackStatus",
          "WeatherData", "WeatherDataSeries", "TopThree", "AudioStreams", "ContentStreams"]


def seconds(value):
    if isinstance(value, dict):
        value = value.get("Value")
    try:
        parts = str(value).lstrip("+").split(":")
        return sum(float(part) * 60 ** i for i, part in enumerate(reversed(parts)))
    except (TypeError, ValueError):
        return None


def items(value):
    """F1 collections can arrive as arrays or numeric-keyed objects."""
    return list(value.values()) if isinstance(value, dict) else (value or [])


class History:
    def __init__(self):
        self.laps = {}

    def ingest(self, state, marker):
        flag = (state.get("TrackStatus") or {}).get("Status", "1")
        apps = (state.get("TimingAppData") or {}).get("Lines", {})
        for number, line in (state.get("TimingData") or {}).get("Lines", {}).items():
            lap = line.get("NumberOfLaps", 0)
            lap_time = seconds(line.get("LastLapTime"))
            if not lap or not lap_time:
                continue
            stints = items(apps.get(number, {}).get("Stints"))
            stint = stints[-1] if stints else {}
            row = {"lap": lap, "time": lap_time,
                   "crossing": line.get("NumberOfLapsTs"),
                   "compound": stint.get("Compound", "UNKNOWN"),
                   "stint": len(stints), "age": stint.get("TotalLaps"),
                   "flag": flag, "pit": bool(line.get("InPit") or line.get("PitOut")),
                   "deleted": bool((line.get("LastLapTime") or {}).get("Deleted"))}
            key = (number, lap)
            changes = self.laps.setdefault(key, [])
            # Only lap-time/crossing revisions need another history version.
            if not changes or (changes[-1][1]["time"], changes[-1][1]["crossing"]) != (lap_time, row["crossing"]):
                changes.append((marker, row))

    def at(self, marker):
        result = {}
        for (number, lap), changes in self.laps.items():
            index = bisect.bisect_right(changes, marker, key=lambda value: value[0]) - 1
            if index >= 0:
                result.setdefault(number, []).append(changes[index][1])
        return {number: sorted(rows, key=lambda row: row["lap"]) for number, rows in result.items()}


class Replay:
    def __init__(self, path):
        self.path = Path(path)
        self.history = History()
        self.cache = OrderedDict()
        self.captures = []
        self.previous = {}
        self.history_state = {}
        self.refreshed = 0
        self.refresh()
        if not self.captures:
            raise ValueError("Replay database contains no captures")

    def refresh(self):
        """Incrementally index committed captures while a live recording grows."""
        if time.monotonic() - self.refreshed < 1:
            return
        marker = self.captures[-1][0] if self.captures else 0
        with self.connect() as db:
            new = db.execute("SELECT id,received_utc FROM captures WHERE id>? ORDER BY id", (marker,)).fetchall()
            if not new:
                self.refreshed = time.monotonic()
                return
            # Read only timing/tyre/flag changes; never load the telemetry archive into RAM.
            for cid, name, digest, blob in db.execute(
                "WITH changes AS (SELECT capture_id,name,payload_hash, "
                "LAG(payload_hash) OVER(PARTITION BY name ORDER BY capture_id) AS previous "
                "FROM topics WHERE capture_id>? AND capture_id<=? "
                "AND name IN ('TimingData','TimingAppData','TrackStatus')) "
                "SELECT t.capture_id,t.name,t.payload_hash,p.json_zlib FROM changes t "
                "JOIN payloads p ON p.hash=t.payload_hash "
                "WHERE t.previous IS NULL OR t.previous<>t.payload_hash ORDER BY t.capture_id,t.name", (marker, new[-1][0])):
                if self.previous.get(name) == digest:
                    continue
                self.previous[name] = digest
                self.history_state[name] = json.loads(zlib.decompress(blob))
                if name == "TimingData":
                    self.history.ingest(self.history_state, cid)
        self.captures.extend(new)
        self.timestamps = [datetime.fromisoformat(utc).timestamp() for _, utc in self.captures]
        self.refreshed = time.monotonic()

    def connect(self):
        return closing(sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True))

    def frame(self, progress, target=None):
        self.refresh()
        target = target if target is not None else self.timestamps[0] + progress / 100 * (self.timestamps[-1] - self.timestamps[0])
        index = max(0, bisect.bisect_right(self.timestamps, target) - 1)
        cid, utc = self.captures[index]
        if cid not in self.cache:
            with self.connect() as db:
                self.cache[cid] = {name: json.loads(zlib.decompress(blob)) for name, blob in db.execute(
                    "SELECT t.name,p.json_zlib FROM topics t JOIN payloads p ON p.hash=t.payload_hash "
                    "WHERE capture_id=?", (cid,))}
            while len(self.cache) > 8:
                self.cache.popitem(last=False)
        state = self.cache[cid]
        return state, self.history.at(cid), {"capture": cid, "received": utc,
                "duration": self.timestamps[-1] - self.timestamps[0], "progress": progress,
                "start": self.timestamps[0], "end": self.timestamps[-1],
                "session_key": str(state["SessionInfo"]["Key"]), "samples": len(self.captures)}


class LiveStore:
    """One writer; hash-identical topic blobs are compressed only once."""
    def __init__(self, key, path=None):
        path = Path(path) if path else ROOT / "data" / "live" / f"session-{key}.sqlite"
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.executescript("""
          PRAGMA journal_mode=WAL;
          CREATE TABLE IF NOT EXISTS captures(id INTEGER PRIMARY KEY,received_utc TEXT,session_key TEXT,clock_json TEXT,version TEXT);
          CREATE TABLE IF NOT EXISTS payloads(hash TEXT PRIMARY KEY,json_zlib BLOB);
          CREATE TABLE IF NOT EXISTS topics(capture_id INTEGER,name TEXT,payload_hash TEXT,PRIMARY KEY(capture_id,name));
          CREATE TABLE IF NOT EXISTS samples(session_key TEXT,topic TEXT,sample_utc TEXT,first_capture_id INTEGER,json_zlib BLOB,PRIMARY KEY(session_key,topic,sample_utc));
          CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT);
        """)
        self.known = set(row[0] for row in self.db.execute("SELECT hash FROM payloads"))
        self.key = key
        row = self.db.execute("SELECT received_utc FROM captures ORDER BY id LIMIT 1").fetchone()
        self.started = datetime.fromisoformat(row[0]).timestamp() if row else None
        self.session_metadata = None

    def write(self, data, received):
        if self.started is None:
            self.started = datetime.fromisoformat(received).timestamp()
        with self.db:
            cid = self.db.execute("INSERT INTO captures(received_utc,session_key,clock_json,version) VALUES(?,?,?,?)",
                (received, self.key, json.dumps(data.get("f1LiveTimingClock")), data.get("version"))).lastrowid
            for name, value in data["f1LiveTimingState"].items():
                raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
                digest = hashlib.sha256(raw).hexdigest()
                if digest not in self.known:
                    self.db.execute("INSERT OR IGNORE INTO payloads VALUES(?,?)", (digest, zlib.compress(raw)))
                    self.known.add(digest)
                self.db.execute("INSERT INTO topics VALUES(?,?,?)", (cid, name, digest))
                if name in ("CarData", "Position") and isinstance(value, dict):
                    entry_key, time_key = ("Entries", "Utc") if name == "CarData" else ("Position", "Timestamp")
                    for sample in items(value.get(entry_key)):
                        if sample.get(time_key):
                            self.db.execute("INSERT OR IGNORE INTO samples VALUES(?,?,?,?,?)",
                                (self.key, name, sample[time_key], cid, zlib.compress(json.dumps(sample).encode())))
            state = data["f1LiveTimingState"]
            info = state.get("SessionInfo") or {}
            status = (state.get("SessionStatus") or {}).get("Status") or info.get("SessionStatus")
            metadata = json.dumps({"info": info, "status": status}, sort_keys=True)
            if metadata != self.session_metadata:
                self.db.execute("INSERT OR REPLACE INTO metadata VALUES('session',?)", (metadata,))
                if status in {"Finished", "Finalised", "Finalized", "Ends", "Ended"} or info.get("SessionStatus") in {"Finalised", "Finalized"}:
                    self.db.execute("INSERT OR IGNORE INTO metadata VALUES('completed_utc',?)", (received,))
                self.session_metadata = metadata

    def close(self):
        self.db.execute("PRAGMA wal_checkpoint(PASSIVE)")
        self.db.close()


class Live:
    def __init__(self, endpoint="http://127.0.0.1:10101/api/graphql"):
        self.endpoint = endpoint
        self.lock = threading.Lock()
        self.history = History()
        self.state = None
        self.error = "Connecting to MultiViewer"
        self.metrics = {}
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        document = None
        store = None
        key = None
        failures = 0
        try:
            while not self.stop.is_set():
                start = time.perf_counter()
                try:
                    if document is None:
                        schema = query(self.endpoint, '{ __type(name:"F1LiveTimingState") { fields { name } } }')
                        names = [field["name"] for field in schema["__type"]["fields"]]
                        document = ('{ version f1LiveTimingClock { paused systemTime trackTime } '
                                    'f1LiveTimingState { ' + ' '.join(names) + ' } }')
                    data = query(self.endpoint, document)
                    poll_ms = (time.perf_counter() - start) * 1000
                    received = datetime.now(timezone.utc).isoformat()
                    state = data.get("f1LiveTimingState")
                    if not state or not state.get("SessionInfo"):
                        raise RuntimeError("Open a session's Live Timing window in MultiViewer")
                    current_key = str(state["SessionInfo"]["Key"])
                    if current_key != key:
                        if store:
                            store.close()
                        key = current_key
                        store = LiveStore(key)
                        with self.lock:
                            self.history = History()
                    store.write(data, received)
                    with self.lock:
                        self.state = state
                        self.history.ingest(state, start)
                        self.error = None
                        self.metrics = {"received": received, "poll_ms": round(poll_ms, 2),
                            "cycle_ms": round((time.perf_counter() - start) * 1000, 2),
                            "interval_ms": 250, "failures": failures,
                            "session_key": key, "start": store.started,
                            "end": datetime.fromisoformat(received).timestamp(),
                            "clock": data.get("f1LiveTimingClock"), "recording": f"data/live/session-{key}.sqlite"}
                except (OSError, ValueError, RuntimeError, sqlite3.Error, KeyError) as exc:
                    failures += 1
                    with self.lock:
                        self.error = str(exc)
                    if failures == 1 or failures % 20 == 0:
                        logging.warning("MultiViewer collection: %s", exc)
                self.stop.wait(max(0.01, (1.0 if self.error else 0.25) - (time.perf_counter() - start)))
        finally:
            if store:
                store.close()

    def frame(self):
        with self.lock:
            return self.state, self.history.at(float("inf")), {**self.metrics, "error": self.error}
