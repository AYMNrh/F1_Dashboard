from __future__ import annotations

import matplotlib.pyplot as plt
import streamlit as st

from app.models.state import AnalysisSelection, SessionSelection
from app.plots.comparison import (
    plot_fastest_lap,
    plot_fastest_sectors,
    plot_full_telemetry,
    plot_lap_distribution,
    plot_laptime,
    plot_position_changes,
    plot_sectors,
    plot_speed_map,
)
from app.services.sessions import (
    get_available_events,
    get_drivers_in_session,
    get_session,
)
from app.ui.controls import (
    get_analysis_options,
    render_analysis_controls,
    render_driver_controls,
    render_session_controls,
)
from app.utils.validation import validate_analysis_selection


PLOT_HANDLERS = {
    "Lap Times": plot_laptime,
    "Sector Comparison": plot_sectors,
    "Fastest Lap": plot_fastest_lap,
    "Fastest Sectors": plot_fastest_sectors,
    "Full Telemetry": plot_full_telemetry,
    "Speed Map": plot_speed_map,
    "Lap Time Distribution": plot_lap_distribution,
    "Position Changes": plot_position_changes,
}


def render_plot(session, selection: AnalysisSelection):
    if selection.analysis_type == "Fastest Sectors":
        lap_selection = (
            "fastest"
            if selection.use_fastest_laps
            else (selection.driver1_lap, selection.driver2_lap)
        )
        return plot_fastest_sectors(
            session, selection.driver1_code, selection.driver2_code, lap_selection
        )

    if selection.analysis_type == "Speed Map":
        return plot_speed_map(session, selection.driver_for_map)

    if selection.analysis_type == "Lap Time Distribution":
        return plot_lap_distribution(session)

    if selection.analysis_type == "Position Changes":
        return plot_position_changes(session)

    handler = PLOT_HANDLERS[selection.analysis_type]
    return handler(session, selection.driver1_code, selection.driver2_code)


def main():
    st.set_page_config(page_title="F1 Session Analysis Dashboard", layout="wide")
    st.title("F1 Session Analysis Dashboard")

    col1, col2 = st.columns([1, 3])

    with col1:
        st.markdown("### Settings")

        session_tab, driver_tab, analysis_tab = st.tabs(
            ["Session", "Drivers", "Analysis"]
        )

        with session_tab:
            session_selection = render_session_controls(get_available_events)

        try:
            session = get_session(
                session_selection.year,
                session_selection.event_name,
                session_selection.session_type,
            )
        except Exception as exc:
            st.error(f"Error loading data: {exc}")
            return

        drivers_info = get_drivers_in_session(session)
        if len(drivers_info) < 2:
            st.warning("Not enough drivers were found in this session.")
            return

        with driver_tab:
            driver_selection = render_driver_controls(drivers_info)

        with analysis_tab:
            analysis_options = get_analysis_options(session_selection.session_type)
            analysis_selection = render_analysis_controls(
                session=session,
                session_type=session_selection.session_type,
                drivers_info=drivers_info,
                driver1_name=driver_selection.driver1_name,
                driver2_name=driver_selection.driver2_name,
                analysis_options=analysis_options,
            )

    with col2:
        if analysis_selection.generate_plot:
            error = validate_analysis_selection(analysis_selection)
            if error:
                st.error(error)
                return

            with st.spinner("Generating plot..."):
                try:
                    fig = render_plot(session, analysis_selection)
                    st.pyplot(fig, use_container_width=True)
                    plt.close(fig)
                except Exception as exc:
                    st.error(f"Error generating plot: {exc}")
