from __future__ import annotations

from pathlib import Path

import fastf1 as ff1
from fastf1 import plotting as ff1_plotting
import pandas as pd
import streamlit as st


@st.cache_resource(show_spinner=False)
def initialize_fastf1():
    cache_dir = Path("cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    ff1.Cache.enable_cache(str(cache_dir))
    ff1_plotting.setup_mpl(mpl_timedelta_support=True, color_scheme="fastf1")


@st.cache_data(show_spinner=False)
def get_available_events(year: int) -> list[str]:
    initialize_fastf1()
    schedule = ff1.get_event_schedule(year)
    return schedule["EventName"].tolist()


@st.cache_resource(show_spinner=False)
def get_session(year: int, event_name: str, session_type: str):
    initialize_fastf1()
    session = ff1.get_session(year, event_name, session_type)
    session.load()
    return session


def get_drivers_in_session(session) -> dict[str, str]:
    drivers_info: dict[str, str] = {}

    for driver in session.drivers:
        try:
            driver_info = session.get_driver(driver)
            if driver_info is None or getattr(driver_info, "empty", False):
                continue

            if isinstance(driver_info, pd.DataFrame):
                driver_info = driver_info.iloc[0]

            code = driver_info["Abbreviation"]
            first_name = driver_info["FirstName"]
            last_name = driver_info["LastName"]
            drivers_info[f"{first_name} {last_name} ({code})"] = code
        except Exception as exc:
            st.warning(f"Could not get info for driver {driver}: {exc}")

    return drivers_info


def get_team_color(session, driver_code: str) -> str:
    driver_info = session.get_driver(driver_code)
    if isinstance(driver_info, pd.DataFrame):
        driver_info = driver_info.iloc[0]

    return ff1_plotting.get_team_color(driver_info["TeamName"], session=session)


def get_driver_color(session, driver_code: str) -> str:
    return ff1_plotting.get_driver_color(driver_code, session=session)


def get_driver_style(session, driver_code: str, style=None) -> dict:
    style_keys = style or ["color", "linestyle"]
    return ff1_plotting.get_driver_style(
        identifier=driver_code,
        style=style_keys,
        session=session,
    )
