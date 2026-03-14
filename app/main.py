from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from app.models.state import AnalysisSelection, SessionSelection
from app.plots.comparison import (
    export_data_for_analysis,
    figure_to_png_bytes,
    plot_corner_annotated_speed_trace,
    plot_fastest_lap,
    plot_fastest_sectors,
    plot_full_telemetry,
    plot_gear_shifts_on_track,
    plot_lap_distribution,
    plot_laptime,
    plot_position_changes,
    plot_weather_track_evolution,
    plot_qualifying_overview,
    plot_sectors,
    plot_speed_map,
    plot_team_pace,
    plot_tyre_strategy,
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
from app.ui.summary import render_session_summary
from app.utils.validation import validate_analysis_selection


PLOT_HANDLERS = {
    "Lap Times": plot_laptime,
    "Sector Comparison": plot_sectors,
    "Fastest Lap": plot_fastest_lap,
    "Fastest Sectors": plot_fastest_sectors,
    "Full Telemetry": plot_full_telemetry,
    "Gear Shifts On Track": plot_gear_shifts_on_track,
    "Corner-Annotated Speed Trace": plot_corner_annotated_speed_trace,
    "Qualifying Overview": plot_qualifying_overview,
    "Speed Map": plot_speed_map,
    "Lap Time Distribution": plot_lap_distribution,
    "Position Changes": plot_position_changes,
    "Team Pace Comparison": plot_team_pace,
    "Tyre Strategy": plot_tyre_strategy,
    "Weather and Track Evolution": plot_weather_track_evolution,
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

    if selection.analysis_type == "Gear Shifts On Track":
        return plot_gear_shifts_on_track(session, selection.driver_for_map)

    if selection.analysis_type == "Corner-Annotated Speed Trace":
        return plot_corner_annotated_speed_trace(session, selection.driver_for_map)

    if selection.analysis_type == "Lap Time Distribution":
        return plot_lap_distribution(session)

    if selection.analysis_type == "Position Changes":
        return plot_position_changes(session)

    if selection.analysis_type == "Qualifying Overview":
        return plot_qualifying_overview(session)

    if selection.analysis_type == "Team Pace Comparison":
        return plot_team_pace(session)

    if selection.analysis_type == "Tyre Strategy":
        return plot_tyre_strategy(session)

    if selection.analysis_type == "Weather and Track Evolution":
        return plot_weather_track_evolution(session)

    handler = PLOT_HANDLERS[selection.analysis_type]
    return handler(session, selection.driver1_code, selection.driver2_code)


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    export_df = df.copy()
    for column in export_df.columns:
        if pd.api.types.is_timedelta64_dtype(export_df[column]):
            export_df[column] = export_df[column].astype(str)
    return export_df.to_csv(index=False).encode("utf-8")


def render_export_actions(session, selection: AnalysisSelection, fig):
    export_col1, export_col2 = st.columns(2)
    png_bytes = figure_to_png_bytes(fig)
    with export_col1:
        st.download_button(
            "Download PNG",
            data=png_bytes,
            file_name=f"{selection.analysis_type.lower().replace(' ', '_')}.png",
            mime="image/png",
            use_container_width=True,
        )

    export_df = export_data_for_analysis(session, selection)
    with export_col2:
        if export_df is not None and not export_df.empty:
            st.download_button(
                "Download CSV",
                data=dataframe_to_csv_bytes(export_df),
                file_name=f"{selection.analysis_type.lower().replace(' ', '_')}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.button("Download CSV", disabled=True, use_container_width=True)


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

        render_session_summary(session, session_selection.session_type)

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
                    render_export_actions(session, analysis_selection, fig)
                    plt.close(fig)
                except Exception as exc:
                    st.error(f"Error generating plot: {exc}")
