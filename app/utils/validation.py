from __future__ import annotations

from app.models.state import AnalysisSelection


RACE_ONLY_ANALYSES = {
    "Lap Time Distribution",
    "Position Changes",
    "Team Pace Comparison",
    "Tyre Strategy",
}

QUALIFYING_ONLY_ANALYSES = {"Qualifying Overview"}


def validate_analysis_selection(selection: AnalysisSelection) -> str | None:
    if (
        selection.analysis_type in RACE_ONLY_ANALYSES
        and selection.session_type not in {"Sprint", "R"}
    ):
        return "This analysis is only available for Sprint and Race sessions."

    if (
        selection.analysis_type in QUALIFYING_ONLY_ANALYSES
        and selection.session_type != "Q"
    ):
        return "This analysis is only available for Qualifying sessions."

    if (
        selection.analysis_type
        in {"Speed Map", "Gear Shifts On Track", "Corner-Annotated Speed Trace"}
        and not selection.driver_for_map
    ):
        return "Please select a driver for this single-driver track analysis."

    if selection.analysis_type == "Fastest Sectors" and not selection.use_fastest_laps:
        if selection.driver1_lap is None or selection.driver2_lap is None:
            return "Please choose a lap for both drivers."

    return None
