from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SessionSelection:
    year: int
    event_name: str
    session_type: str


@dataclass(frozen=True)
class DriverSelection:
    driver1_name: str
    driver2_name: str


@dataclass(frozen=True)
class AnalysisSelection:
    session_type: str
    analysis_type: str
    driver1_code: str
    driver2_code: str
    driver_for_map: str | None
    use_fastest_laps: bool
    driver1_lap: int | None
    driver2_lap: int | None
    generate_plot: bool
