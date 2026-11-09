"""Record every MultiViewer F1 timing topic into replayable SQLite snapshots."""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sqlite3
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


def query(endpoint, document):
    request = Request(endpoint, json.dumps({"query": document}).encode(),
                      {"Content-Type": "application/json"})
    with urlopen(request, timeout=15) as response:
        result = json.load(response)
    if result.get("errors"):
        raise RuntimeError(json.dumps(result["errors"]))
    return result["data"]


def record(endpoint, output, interval, duration):
    output.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(output) as db:
        db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS captures (
                id INTEGER PRIMARY KEY, received_utc TEXT NOT NULL,
                session_key TEXT NOT NULL, clock_json TEXT, version TEXT);
            CREATE TABLE IF NOT EXISTS payloads (
                hash TEXT PRIMARY KEY, json_zlib BLOB NOT NULL);
            CREATE TABLE IF NOT EXISTS topics (
                capture_id INTEGER NOT NULL, name TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                PRIMARY KEY(capture_id, name),
                FOREIGN KEY(capture_id) REFERENCES captures(id),
                FOREIGN KEY(payload_hash) REFERENCES payloads(hash));
            CREATE TABLE IF NOT EXISTS failures (
                received_utc TEXT NOT NULL, message TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE IF NOT EXISTS samples (
                session_key TEXT NOT NULL, topic TEXT NOT NULL,
                sample_utc TEXT NOT NULL, first_capture_id INTEGER NOT NULL,
                json_zlib BLOB NOT NULL,
                PRIMARY KEY(session_key, topic, sample_utc));
        """)
        schema = query(endpoint, '{ __type(name:"F1LiveTimingState") { fields { name } } }')
        names = [field["name"] for field in schema["__type"]["fields"]]
        db.execute("INSERT OR REPLACE INTO metadata VALUES (?, ?)",
                   ("topic_names", json.dumps(names)))
        db.execute("INSERT OR REPLACE INTO metadata VALUES (?, ?)", ("endpoint", endpoint))
        db.execute("INSERT OR REPLACE INTO metadata VALUES (?, ?)", ("poll_interval_seconds", str(interval)))
        db.commit()
        document = ('{ version f1LiveTimingClock { paused systemTime trackTime } '
                    'f1LiveTimingState { ' + ' '.join(names) + ' } }')
        session_key = None
        deadline = time.monotonic() + duration if duration else float("inf")
        logging.info("Recording %s topics to %s", len(names), output.resolve())
        while time.monotonic() < deadline:
            started = time.monotonic()
            received = datetime.now(timezone.utc).isoformat()
            try:
                data = query(endpoint, document)
                state = data.get("f1LiveTimingState")
                if not state or not state.get("SessionInfo"):
                    raise RuntimeError("No active F1 timing session")
                current_key = str(state["SessionInfo"]["Key"])
                if session_key is not None and current_key != session_key:
                    logging.info("Session changed; recording stopped to avoid mixing races")
                    break
                session_key = current_key
                with db:
                    capture = db.execute(
                        "INSERT INTO captures(received_utc, session_key, clock_json, version) VALUES (?,?,?,?)",
                        (received, session_key, json.dumps(data.get("f1LiveTimingClock")), data.get("version")))
                    for name, value in state.items():
                        raw = json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
                        digest = hashlib.sha256(raw).hexdigest()
                        db.execute("INSERT OR IGNORE INTO payloads VALUES (?,?)",
                                   (digest, zlib.compress(raw)))
                        db.execute("INSERT INTO topics VALUES (?,?,?)", (capture.lastrowid, name, digest))
                        if name in {"CarData", "Position"} and isinstance(value, dict):
                            entries_key, time_key = (
                                ("Entries", "Utc") if name == "CarData"
                                else ("Position", "Timestamp")
                            )
                            for sample in value.get(entries_key, []):
                                sample_utc = sample.get(time_key)
                                if not sample_utc:
                                    raise ValueError(f"{name} sample has no {time_key}")
                                sample_raw = json.dumps(sample, separators=(",", ":"), sort_keys=True).encode()
                                db.execute(
                                    "INSERT OR IGNORE INTO samples VALUES (?,?,?,?,?)",
                                    (session_key, name, sample_utc, capture.lastrowid,
                                     zlib.compress(sample_raw)))
                if capture.lastrowid == 1 or capture.lastrowid % 60 == 0:
                    logging.info("Capture %s, lap %s, status %s", capture.lastrowid,
                                 state.get("LapCount"), state.get("SessionStatus"))
            except (OSError, ValueError, RuntimeError) as exc:
                logging.error("Capture failed: %s", exc)
                with db:
                    db.execute("INSERT INTO failures VALUES (?,?)", (received, str(exc)))
            time.sleep(max(0, interval - (time.monotonic() - started)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="http://127.0.0.1:10101/api/graphql")
    parser.add_argument("--output", type=Path, default=Path("data/2026-10-25-austin/race.sqlite"))
    parser.add_argument("--interval", type=float, default=0.25)
    parser.add_argument("--duration", type=float, default=0, help="Seconds; 0 records until interrupted")
    args = parser.parse_args()
    if args.interval <= 0 or args.duration < 0:
        parser.error("interval must be positive and duration must be nonnegative")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    record(args.endpoint, args.output, args.interval, args.duration)
