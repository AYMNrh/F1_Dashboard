from __future__ import annotations

import pandas as pd
import streamlit as st


def _get_session_leader_label(session, session_type: str) -> tuple[str, str]:
    results = getattr(session, "results", None)
    if results is None or results.empty:
        return ("Top Result", "Unavailable")

    try:
        top_row = results.sort_values("Position").iloc[0]
    except Exception:
        return ("Top Result", "Unavailable")

    driver = top_row.get("FullName") or top_row.get("Abbreviation") or "Unknown"
    if session_type == "Q":
        return ("Pole", str(driver))
    if session_type in {"R", "Sprint"}:
        return ("Winner", str(driver))
    return ("Top Result", str(driver))


def render_session_summary(session, session_type: str):
    event = session.event
    event_name = event.get("EventName", "Unknown Event")
    location = event.get("Location", "Unknown Location")
    event_date = event.get("EventDate")
    event_date_text = (
        pd.to_datetime(event_date).strftime("%Y-%m-%d")
        if pd.notna(event_date)
        else "Unknown Date"
    )

    lead_label, lead_value = _get_session_leader_label(session, session_type)

    weather = getattr(session, "weather_data", None)
    if weather is not None and not weather.empty:
        avg_air_temp = weather["AirTemp"].dropna().mean() if "AirTemp" in weather else None
        avg_track_temp = (
            weather["TrackTemp"].dropna().mean() if "TrackTemp" in weather else None
        )
    else:
        avg_air_temp = None
        avg_track_temp = None

    metric_columns = st.columns(5)
    metric_columns[0].metric("Event", str(event_name))
    metric_columns[1].metric("Location", str(location))
    metric_columns[2].metric("Date", event_date_text)
    metric_columns[3].metric(lead_label, lead_value)

    condition_value = "Unavailable"
    if avg_air_temp is not None or avg_track_temp is not None:
        parts = []
        if avg_air_temp is not None:
            parts.append(f"Air {avg_air_temp:.1f}C")
        if avg_track_temp is not None:
            parts.append(f"Track {avg_track_temp:.1f}C")
        condition_value = " | ".join(parts)
    metric_columns[4].metric("Conditions", condition_value)

    st.caption(f"Session: {session_type}")
