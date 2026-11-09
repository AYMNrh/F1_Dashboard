import json
import sqlite3
import tempfile
import unittest
import zlib
from contextlib import closing
from pathlib import Path

from dashboard.analytics import summarize
from dashboard.data import History, LiveStore, Replay
from dashboard.library import SessionLibrary


class DashboardTests(unittest.TestCase):
    @staticmethod
    def session_frame(key, lap=1, status="Started"):
        return {"f1LiveTimingState": {
            "SessionInfo": {"Key": key, "Name": "Race", "StartDate": "2026-11-01T15:00:00",
                            "Meeting": {"Name": f"Meeting {key}"}},
            "SessionStatus": {"Status": status}, "LapCount": None,
            "TimingData": {"Lines": {"12": {"NumberOfLaps": lap,
                "NumberOfLapsTs": lap * 100000, "LastLapTime": {"Value": "1:40.000"}}}},
            "TimingAppData": {"Lines": {}}, "TrackStatus": {"Status": "1"}}}

    def test_library_discovers_multiple_sessions_and_rejects_unknown_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for key in (1, 2):
                store = LiveStore(str(key), root / f"{key}.sqlite")
                store.write(self.session_frame(key), "2026-11-01T15:00:00+00:00")
                store.close()
            library = SessionLibrary(root / "1.sqlite", root)
            self.assertEqual({row["key"] for row in library.sessions()}, {"1", "2"})
            replay, entry = library.resolve(key="2")
            self.assertEqual(replay.frame(0)[0]["SessionInfo"]["Key"], 2)
            self.assertIsNone(entry["first_lap"])
            with self.assertRaises(ValueError):
                library.resolve("../../other.sqlite")

    def test_replay_refreshes_growing_recording_without_using_future_history(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "race.sqlite"
            store = LiveStore("1", path)
            store.write(self.session_frame(1), "2026-11-01T15:00:00+00:00")
            replay = Replay(path)
            store.write(self.session_frame(1, lap=2), "2026-11-01T15:01:40+00:00")
            replay.refreshed = 0
            old_state, old_history, _ = replay.frame(0)
            new_state, new_history, _ = replay.frame(100)
            self.assertEqual(old_state["TimingData"]["Lines"]["12"]["NumberOfLaps"], 1)
            self.assertEqual([row["lap"] for row in old_history["12"]], [1])
            self.assertEqual(len(new_history["12"]), 2)
            self.assertEqual(new_state["TimingData"]["Lines"]["12"]["NumberOfLaps"], 2)
            store.close()

    def test_completed_session_is_saved_and_can_be_reopened_after_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "race.sqlite"
            store = LiveStore("1", path)
            store.write(self.session_frame(1), "2026-11-01T15:00:00+00:00")
            store.write(self.session_frame(1, 2, "Ends"), "2026-11-01T15:01:40+00:00")
            store.close()
            library = SessionLibrary(path, root)
            entry = library.sessions()[0]
            self.assertTrue(entry["completed"])
            replay, _ = library.resolve(entry["id"])
            self.assertEqual(replay.frame(100)[0]["SessionStatus"]["Status"], "Ends")
            with closing(sqlite3.connect(path)) as db:
                self.assertEqual(db.execute("SELECT value FROM metadata WHERE key='completed_utc'").fetchone()[0], "2026-11-01T15:01:40+00:00")
                self.assertEqual(db.execute("SELECT count(*) FROM captures").fetchone()[0], 2)

    def test_replay_history_never_uses_future_laps_or_revisions(self):
        history = History()
        def frame(lap, value):
            return {"TimingData": {"Lines": {"12": {"NumberOfLaps": lap,
                    "LastLapTime": {"Value": value}, "NumberOfLapsTs": lap * 100000}}}}
        history.ingest(frame(20, "1:41.000"), 10)
        history.ingest(frame(20, "1:40.900"), 11)
        history.ingest(frame(21, "1:40.000"), 20)
        self.assertEqual(history.at(10)["12"][0]["time"], 101)
        self.assertEqual([r["lap"] for r in history.at(11)["12"]], [20])
        self.assertEqual(history.at(11)["12"][0]["time"], 100.9)
        self.assertEqual(len(history.at(20)["12"]), 2)

    def test_qualifying_uses_current_part_times_for_cutoff_and_no_race_gap(self):
        lines = {str(i): {"Position": str(i), "BestLapTime": {"Value": "1:10"},
                         "BestLapTimes": [{"Value": str(90 + i / 10)}, {"Value": str(80 + i / 10)}]}
                 for i in range(1, 23)}
        state = {"SessionInfo": {"Type": "Qualifying"}, "TimingData": {"Lines": lines},
                 "SessionData": {"Series": [{"QualifyingPart": 1}]}}
        result = summarize(state, {}, {})
        self.assertEqual(result["cutoffPosition"], 16)
        self.assertAlmostEqual(result["drivers"][16]["cutoffMargin"], 0.1)
        self.assertIsNone(result["drivers"][0]["gap"])
        state["SessionData"]["Series"].append({"QualifyingPart": 2})
        result = summarize(state, {}, {})
        self.assertEqual(result["cutoffPosition"], 10)
        self.assertAlmostEqual(result["drivers"][0]["best"], 80.1)

    def test_live_recording_preserves_snapshots_and_deduplicates_source_samples(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "live.sqlite"
            store = LiveStore("123", path)
            sample = {"Utc": "2026-10-31T20:00:00Z", "Cars": {"12": {"Channels": {"2": 250}}}}
            data = {"version": "test", "f1LiveTimingState": {"CarData": {"Entries": [sample]}}}
            store.write(data, "2026-10-31T20:00:00+00:00")
            store.write(data, "2026-10-31T20:00:01+00:00")
            store.close()
            with closing(sqlite3.connect(path)) as db:
                self.assertEqual(db.execute("SELECT count(*) FROM captures").fetchone()[0], 2)
                self.assertEqual(db.execute("SELECT count(*) FROM payloads").fetchone()[0], 1)
                first, blob = db.execute("SELECT first_capture_id,json_zlib FROM samples").fetchone()
                self.assertEqual(first, 1)
                self.assertEqual(json.loads(zlib.decompress(blob)), sample)
                self.assertEqual(db.execute("SELECT count(*) FROM samples").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
