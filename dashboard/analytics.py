"""Descriptive timing views and explicit, limited prediction models."""
from __future__ import annotations

import re
import statistics
from .data import items, seconds


def number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def summarize(state, history, meta):
    if not state:
        return {"available": False, "meta": meta}
    timing = (state.get("TimingData") or {}).get("Lines", {})
    stats = (state.get("TimingStats") or {}).get("Lines", {})
    apps = (state.get("TimingAppData") or {}).get("Lines", {})
    driver_list = state.get("DriverList") or {}
    deleted = set()
    messages = items((state.get("RaceControlMessages") or {}).get("Messages"))
    info = state.get("SessionInfo") or {}
    series = items((state.get("SessionData") or {}).get("Series"))
    part = next((int(row["QualifyingPart"]) for row in reversed(series) if row.get("QualifyingPart")), None)
    part = part or number((state.get("TimingData") or {}).get("SessionPart"))
    part = int(part) if part else None
    qualifying = info.get("Type") == "Qualifying" or "qualifying" in info.get("Name", "").lower()
    for message in messages:
        if message.get("SubCategory") == "LapTimeDeleted":
            match = re.search(r"CAR (\d+).*?\bLAP (\d+)", message.get("Message", ""))
            if match:
                deleted.add((match[1], int(match[2])))
    drivers = []
    for n, line in timing.items():
        if not isinstance(line, dict):
            continue
        identity = driver_list.get(n, {})
        personal = stats.get(n, {})
        stints = items(apps.get(n, {}).get("Stints"))
        stint = stints[-1] if stints else {}
        sectors = items(personal.get("BestSectors"))
        best_sectors = [seconds(sector) for sector in sectors[:3]]
        best = seconds(line.get("BestLapTime")) or seconds(personal.get("PersonalBestLapTime"))
        part_times = items(line.get("BestLapTimes"))
        if qualifying and part and len(part_times) >= part:
            best = seconds(part_times[part - 1])
        ideal = sum(best_sectors) if len(best_sectors) == 3 and all(x is not None for x in best_sectors) else None
        laps = [{**row, "deleted": row.get("deleted") or (n, row["lap"]) in deleted} for row in history.get(n, [])]
        # A new tyre stint must build its own sample; do not mix old/new compound pace.
        stint_start = sum(int(s.get("TotalLaps", 0)) for s in stints[:-1])
        recent = [row["time"] for row in laps if row["lap"] > stint_start + 1
                  and row["flag"] == "1" and not row["deleted"] and not row["pit"]][-7:]
        if recent:
            median = statistics.median(recent)
            recent = [value for value in recent if abs(value - median) < median * 0.05]
        pace = statistics.median(recent[-5:]) if len(recent) >= 3 else None
        spread = statistics.median(abs(v - pace) for v in recent[-5:]) if pace is not None else None
        gap = None if qualifying else (0.0 if str(line.get("Position")) == "1" else seconds(line.get("GapToLeader")))
        live_sectors = items(line.get("Sectors"))[:3]
        completed = [seconds(s.get("Value")) for s in live_sectors]
        projected = None
        if len(completed) == 3 and ideal and completed[0] is not None and not line.get("InPit") and not line.get("PitOut"):
            projected = sum(value if value is not None else best_sectors[i] for i, value in enumerate(completed))
        drivers.append({"number": n, "code": identity.get("Tla") or identity.get("TLA") or n,
            "name": identity.get("FullName") or (identity.get("FirstName", "") + " " + identity.get("LastName", "")).strip(),
            "team": identity.get("TeamName", ""), "color": "#" + identity.get("TeamColour", "9099aa").lstrip("#"),
            "position": int(line.get("Position") or 99), "gap": gap, "gapLabel": line.get("GapToLeader", ""),
            "interval": (line.get("IntervalToPositionAhead") or {}).get("Value", ""),
            "last": seconds(line.get("LastLapTime")), "best": best, "ideal": ideal,
            "potential": max(0, best - ideal) if best is not None and ideal is not None else None,
            "bestSectors": best_sectors, "sectors": completed, "projected": projected,
            "sectorStatus": [s.get("OverallFastest", False) for s in live_sectors],
            "compound": stint.get("Compound", "UNKNOWN"), "tyreAge": stint.get("TotalLaps"),
            "stints": stints, "stops": line.get("NumberOfPitStops", 0),
            "inPit": bool(line.get("InPit")), "outlap": bool(line.get("PitOut") or (line.get("MVStatus") or {}).get("Outlap")),
            "retired": bool(line.get("Retired")), "knockedOut": bool(line.get("KnockedOut") or (line.get("MVStatus") or {}).get("KnockedOut")),
            "finished": bool((line.get("MVStatus") or {}).get("TakenChequered")),
            "lapsCompleted": line.get("NumberOfLaps", 0), "laps": laps,
            "pace": pace, "paceSamples": min(5, len(recent)), "paceSpread": spread,
            "speedTrap": number(((personal.get("BestSpeeds") or {}).get("ST") or {}).get("Value"))})
    drivers.sort(key=lambda d: d["position"])
    # Derive Q1/Q2 cutoff from the session's actual field size; Q3 is a pole fight.
    cutoff_position = (len(drivers) + 10) // 2 if part == 1 else 10 if part == 2 else None
    active_times = sorted(d["best"] for d in drivers if d["best"] is not None and not d["knockedOut"])
    threshold = active_times[cutoff_position - 1] if cutoff_position and len(active_times) >= cutoff_position else None
    for driver in drivers:
        driver["cutoffMargin"] = driver["best"] - threshold if threshold is not None and driver["best"] is not None and not driver["knockedOut"] else None
    positions = items((state.get("Position") or {}).get("Position"))
    car_entries = items((state.get("CarData") or {}).get("Entries"))
    return {"available": True, "meta": meta, "session": info,
            "qualifying": qualifying, "qualifyingPart": part, "cutoffPosition": cutoff_position,
            "lapCount": state.get("LapCount") or {}, "trackStatus": state.get("TrackStatus") or {},
            "sessionStatus": state.get("SessionStatus") or {}, "clock": state.get("ExtrapolatedClock") or {},
            "weather": state.get("WeatherData") or {}, "drivers": drivers,
            "messages": messages[-80:], "radio": items((state.get("TeamRadio") or {}).get("Captures"))[-12:],
            "positions": positions[-1].get("Entries", {}) if positions else {},
            "cars": car_entries[-1].get("Cars", {}) if car_entries else {},
            "topics": list(state)}
