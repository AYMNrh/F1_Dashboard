# Pitwall

Local React + Python timing dashboard. The Python service uses only the standard
library (Python 3.10+). The existing Streamlit analysis app is unchanged.

## Start

On this Windows checkout, run `./Start-Pitwall.ps1` from the repository root.
It uses the bundled Python runtime when available and builds the frontend if
needed. The full manual setup is below.

From the repository root, first build the frontend:

```powershell
cd dashboard/frontend
npm install
npm run build
cd ../..
py -3 -m dashboard.server
```

Open **http://127.0.0.1:8765**. On systems with a different Python command,
replace `py -3` with `python`. Node 20.19+ or 22.12+ is needed for Vite.
Use `--port 8766` to choose a different dashboard port. Stop with Ctrl+C.

For frontend development, keep the Python service running, then run `npm run dev`
inside `dashboard/frontend`. Vite proxies `/api` to port 8765.

## Historical and live data

- **Historical / mock** uses the real Austin SQLite recording. Seek, pause, or play
  at 1–60× speed. Capture timestamps, not invented laps, drive the replay.
- The **hamburger menu** beside PITWALL opens all saved races and sessions,
  including live recordings under `data/live/`. Select a session to replay it.
  Completed sessions are labeled **Saved / finished** and remain available after
  restarting the dashboard. Existing Austin and Mexico City files are discovered
  automatically; no copying or conversion is required.
- **Live data** connects to MultiViewer's local GraphQL API at
  `http://127.0.0.1:10101/api/graphql`. Open a session's **Live Timing** window in
  MultiViewer. No credentials are copied to the dashboard.
- The collector discovers every F1 timing topic and polls once per 250 ms target
  cycle. It runs independently of browser tabs and display mode. Successful live
  states are recorded in `data/live/session-<session key>.sqlite` with compressed,
  deduplicated payloads and timestamp-deduplicated CarData/Position samples.
- Session changes create a new recording and clear live lap history. Network
  failures show an explicit disconnected banner and retain the last successful
  capture. Failed collection attempts are logged in the server output.
- Stop the Python server to stop collection. Data is local and excluded from Git.

The replay bar also appears in **Live data**. Pause or drag the timeline to seek
through the current session's captured history while recording continues. Press
**Go live** to return to the newest update, or play the replay at 1–60× to catch up.
The earliest seek point is when this recorder first connected, not necessarily the
official session start. Finished/ended status is retained in SQLite metadata;
the library also reads final status from older recordings that lack that metadata.
Each session key has its own persistent SQLite file, so switching sessions appends
to the appropriate recording without overwriting another session.

## Views

- Timing tower: positions, gaps, last laps, sectors, tyres, pit and knockout status.
- Overview: lap-time comparisons, recent pace, car positions and pit scenarios.
- Qualifying: session/part best laps, cutoff margins in Q1/Q2, sector matrix,
  theoretical ideal laps and a flying-lap estimate. Historical race data remains
  clearly labeled; it does not pretend to be qualifying data.
- Strategy: adjustable total pit loss and laps until stop, relative gap history,
  compound/stint bars. Catch forecasts require enough recent clean laps.
- Telemetry: speed, throttle and brake traces against time, plus RPM and gear.
  Comparisons are time-aligned, not distance-aligned fastest-lap overlays.
- Race control: filter flags or incidents. Export downloads the visible frame as
  JSON; internal SQLite snapshots retain every discovered topic.

Click a tower driver to select car 1, Shift-click for car 2, or use the selectors.

## Performance and limits

One background thread collects and writes; all clients consume its shared state
via Server-Sent Events. SQLite uses WAL. Historical replay indexes only lap
observations; it reads selected captures and small telemetry windows on demand.
Prediction inputs are restricted to observations at or before the selected
capture, including lap-time revisions. The server reports processing and live
collection durations separately; a 250 ms target is not a hard real-time guarantee.

The Austin recording begins on lap 20. It contains some earlier retained state,
but not the full opening laps. The circuit outline is reconstructed from recorded
GPS positions and is only shown for that replay. Live mode shows current car
positions without inventing circuit geometry.

Recent pace is the median of up to five observed laps in the current stint, after
an initial warmup lap, excluding laps flagged as pitting, deleted, caution-affected
or more than 5% away from the recent median. At least three are required. Feed
fields can update asynchronously, so these are descriptive estimates rather than
official validated lap results.

Pit scenarios use relative numeric race gaps, an editable total pit-loss assumption,
and (when waiting) the difference in recent pace. They do not model future fuel,
traffic, warmup or additional stops. Caution suspends catch/delayed-stop pace
forecasts. A ±2 s sensitivity range is **not** a confidence interval. Qualifying
time gaps are never treated as on-track race gaps.

Ideal laps sum personal best sectors. Flying-lap estimates use completed live
sectors plus personal-best remaining sectors. Q1/Q2 cutoffs use the reported
qualifying part, current-part times when supplied, and the field size. No
advancement probability is fabricated when the feed lacks data.

## Validation

```powershell
py -3 -m unittest dashboard.test_dashboard
```

## Design references

These are public engineering concepts; private FIA/team interfaces are not copied.

- [ATLAS waveform displays](https://docs.atlas.mclarenapplied.com/key-functionality/analyse/viewer/displays/waveform/): telemetry against time or distance.
- [FIA cyber-stewarding](https://www.fia.com/news/cyber-stewarding): timing and GPS monitoring.
- [F1 tyre performance](https://www.formula1.com/en/latest/article/explaining-the-new-tyre-performance-graphics-seen-on-tv.21CVJlHg0St8zrzaaVbU4L): tyre and battle analysis.
- [2026 FIA sporting regulations](https://www.fia.com/system/files/documents/fia_2026_f1_regulations_-_section_b_sporting_-_iss_06_-_2026-04-28.pdf): qualifying format.
