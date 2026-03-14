from __future__ import annotations

import streamlit as st

from app.models.state import AnalysisSelection, DriverSelection, SessionSelection
from app.utils.validation import RACE_ONLY_ANALYSES


def render_session_controls(get_available_events):
    year = st.selectbox("Year", range(2010, 2027), label_visibility="collapsed")
    events = get_available_events(year)
    event_name = st.selectbox("Grand Prix", events, label_visibility="collapsed")
    session_type = st.selectbox(
        "Session",
        ["FP1", "FP2", "FP3", "Sprint", "Q", "R"],
        label_visibility="collapsed",
    )
    return SessionSelection(year=year, event_name=event_name, session_type=session_type)


def render_driver_controls(drivers_info: dict[str, str]) -> DriverSelection:
    driver_names = list(drivers_info.keys())
    driver1_name = st.selectbox(
        "Driver 1", driver_names, label_visibility="collapsed"
    )
    remaining_drivers = [name for name in driver_names if name != driver1_name]
    driver2_name = st.selectbox(
        "Driver 2", remaining_drivers, label_visibility="collapsed"
    )
    return DriverSelection(driver1_name=driver1_name, driver2_name=driver2_name)


def get_analysis_options(session_type: str) -> list[str]:
    base_options = [
        "Lap Times",
        "Sector Comparison",
        "Fastest Lap",
        "Fastest Sectors",
        "Full Telemetry",
        "Speed Map",
    ]
    if session_type in {"Sprint", "R"}:
        return base_options + ["Lap Time Distribution", "Position Changes"]
    return base_options


def render_analysis_controls(
    session,
    session_type: str,
    drivers_info: dict[str, str],
    driver1_name: str,
    driver2_name: str,
    analysis_options: list[str],
) -> AnalysisSelection:
    driver1_code = drivers_info[driver1_name]
    driver2_code = drivers_info[driver2_name]
    analysis_type = st.selectbox(
        "Analysis Type", analysis_options, label_visibility="collapsed"
    )

    use_fastest_laps = True
    driver1_lap = None
    driver2_lap = None
    driver_for_map = None

    if analysis_type == "Fastest Sectors":
        use_fastest_laps = st.checkbox("Use Fastest Laps", value=True)
        if not use_fastest_laps:
            laps_d1 = session.laps.pick_driver(driver1_code)["LapNumber"].dropna().astype(int)
            laps_d2 = session.laps.pick_driver(driver2_code)["LapNumber"].dropna().astype(int)
            driver1_lap = st.selectbox(
                f"Lap ({driver1_code})",
                laps_d1.tolist(),
                label_visibility="collapsed",
            )
            driver2_lap = st.selectbox(
                f"Lap ({driver2_code})",
                laps_d2.tolist(),
                label_visibility="collapsed",
            )

    if analysis_type == "Speed Map":
        selected_driver = st.radio(
            "Driver for Speed Map", [driver1_name, driver2_name], horizontal=True
        )
        driver_for_map = drivers_info[selected_driver]

    if analysis_type in RACE_ONLY_ANALYSES and session_type not in {"Sprint", "R"}:
        st.caption("This analysis is only available for race-like sessions.")

    generate_plot = st.button("Generate Plot", use_container_width=True)

    return AnalysisSelection(
        session_type=session_type,
        analysis_type=analysis_type,
        driver1_code=driver1_code,
        driver2_code=driver2_code,
        driver_for_map=driver_for_map,
        use_fastest_laps=use_fastest_laps,
        driver1_lap=driver1_lap,
        driver2_lap=driver2_lap,
        generate_plot=generate_plot,
    )
