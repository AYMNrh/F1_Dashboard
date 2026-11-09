"""Local-only Python server: python -m dashboard.server [--port 8765]."""
from __future__ import annotations

import argparse
import json
import logging
import mimetypes
import threading
import time
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .analytics import summarize
from .data import ROOT, Live, items
from .library import SessionLibrary


class Service:
    def __init__(self, path):
        self.library = SessionLibrary(path)
        self.replay_lock = threading.Lock()
        self.live = Live()

    def recorded(self, params, key=None):
        identifier = params.get("session", [None])[0] if key is None else None
        replay, entry = self.library.resolve(identifier, key)
        progress = min(100, max(0, float(params.get("progress", ["8"])[0])))
        target = float(params["at"][0]) if "at" in params else None
        state, history, meta = replay.frame(progress, target)
        meta["library_id"] = entry["id"]
        meta["coverage"] = f"{entry['meeting']} · {entry['name']}"
        meta["first_lap"] = entry["first_lap"]
        meta["completed"] = entry["completed"]
        with replay.connect() as db:
            session_key = str(state["SessionInfo"]["Key"])
            telemetry = [json.loads(zlib.decompress(blob)) for blob, in db.execute(
                "SELECT json_zlib FROM samples WHERE session_key=? AND topic='CarData' "
                "AND first_capture_id<=? ORDER BY sample_utc DESC LIMIT 140", (session_key, meta["capture"]))][::-1]
            if not hasattr(replay, "track"):
                replay.track = []
                for blob, in db.execute("SELECT json_zlib FROM samples WHERE topic='Position' ORDER BY sample_utc LIMIT 650"):
                    entries = json.loads(zlib.decompress(blob)).get("Entries", {})
                    car = entries.get("12") or next(iter(entries.values()), {})
                    if car.get("X") is not None and car.get("Y") is not None:
                        replay.track.append([car["X"], car["Y"]])
        if not telemetry:
            telemetry = items((state.get("CarData") or {}).get("Entries"))
        return state, history, meta, telemetry, replay.track

    def frame(self, params):
        mode = params.get("mode", ["replay"])[0]
        if mode not in ("replay", "live"):
            raise ValueError("Unknown data mode")
        selected = params.get("drivers", ["12,3"])[0].split(",")[:2]
        start = time.perf_counter()
        track = []
        if mode == "live":
            state, history, meta = self.live.frame()
            telemetry = items((state.get("CarData") or {}).get("Entries")) if state else []
            if params.get("replay", ["0"])[0] == "1" and meta.get("session_key"):
                live_meta = meta
                with self.replay_lock:
                    state, history, meta, telemetry, track = self.recorded(params, key=live_meta["session_key"])
                meta.update({"timeshift": True, "live_end": live_meta.get("end"), "error": live_meta.get("error")})
        else:
            with self.replay_lock:
                state, history, meta, telemetry, track = self.recorded(params)
        result = summarize(state, history, {**meta, "mode": mode})
        result["telemetry"] = [{"utc": entry.get("Utc"), **{n: (entry.get("Cars", {}).get(n, {}).get("Channels", {})) for n in selected}}
                               for entry in telemetry]
        result["track"] = track
        result["meta"]["processing_ms"] = round((time.perf_counter() - start) * 1000, 2)
        return result


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        if args and str(args[0]).startswith("GET /api/"):
            return
        logging.info(fmt, *args)

    def send_json(self, value, status=200):
        raw = json.dumps(value, allow_nan=False, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        try:
            if parsed.path == "/api/health":
                return self.send_json({"ok": True, "interval_ms": 250, "replay": str(self.server.service.library.default)})
            if parsed.path == "/api/sessions":
                with self.server.service.replay_lock:
                    sessions = self.server.service.library.sessions()
                return self.send_json({"sessions": sessions})
            if parsed.path == "/api/frame":
                return self.send_json(self.server.service.frame(params))
            if parsed.path == "/api/stream":
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.end_headers()
                self.close_connection = True
                while True:
                    started = time.perf_counter()
                    frame = self.server.service.frame(params)
                    self.wfile.write(("data:" + json.dumps(frame, allow_nan=False, separators=(",", ":")) + "\n\n").encode())
                    self.wfile.flush()
                    time.sleep(max(0.01, 0.25 - (time.perf_counter() - started)))
            else:
                root = ROOT / "dashboard" / "frontend" / "dist"
                path = (root / parsed.path.lstrip("/")).resolve()
                if not path.is_relative_to(root.resolve()):
                    return self.send_json({"error": "Invalid path"}, 403)
                if not path.is_file():
                    path = root / "index.html"
                if not path.is_file():
                    return self.send_json({"error": "Build frontend first: cd dashboard/frontend && npm run build"}, 503)
                raw = path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", mimetypes.guess_type(str(path))[0] or "application/octet-stream")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass  # A browser closing its stream is an expected disconnect.
        except (ValueError, KeyError) as exc:
            self.send_json({"error": str(exc)}, 400)
        except Exception:
            logging.exception("Dashboard request failed")
            if parsed.path != "/api/stream":
                self.send_json({"error": "Request failed; inspect the server log"}, 500)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--replay", default=str(ROOT / "data/2026-10-25-austin/race.sqlite"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.service = Service(args.replay)
    logging.info("Pitwall ready at http://127.0.0.1:%s", args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Stopping dashboard")
    finally:
        server.service.live.stop.set()
        server.server_close()


if __name__ == "__main__":
    main()
