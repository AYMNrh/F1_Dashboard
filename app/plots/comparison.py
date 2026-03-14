from __future__ import annotations

from io import BytesIO

import fastf1 as ff1
import matplotlib
import numpy as np
import pandas as pd
import seaborn as sns
from fastf1 import plotting as ff1_plotting, utils
from matplotlib import pyplot as plt
from matplotlib.collections import LineCollection

from app.services.sessions import get_driver_color, get_driver_style, get_team_color


def plot_laptime(session, driver1, driver2):
    laps_d1 = session.laps.pick_driver(driver1)
    laps_d2 = session.laps.pick_driver(driver2)
    style1 = get_driver_style(session, driver1, ["color", "linestyle"])
    style2 = get_driver_style(session, driver2, ["color", "linestyle"])

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(laps_d1["LapNumber"], laps_d1["LapTime"], label=driver1, linewidth=2, **style1)
    ax.plot(laps_d2["LapNumber"], laps_d2["LapTime"], label=driver2, linewidth=2, **style2)
    ax.set_xlabel("Lap Number")
    ax.set_ylabel("Lap Time")
    ax.legend()
    fig.suptitle(f"Lap Time Comparison\n{session.event.year} {session.event['EventName']}")
    return fig


def plot_fastest_lap(session, driver1, driver2):
    fastest_d1 = session.laps.pick_driver(driver1).pick_fastest()
    fastest_d2 = session.laps.pick_driver(driver2).pick_fastest()
    tel_d1 = fastest_d1.get_car_data().add_distance()
    tel_d2 = fastest_d2.get_car_data().add_distance()
    style1 = get_driver_style(session, driver1, ["color", "linestyle"])
    style2 = get_driver_style(session, driver2, ["color", "linestyle"])

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(tel_d1["Distance"], tel_d1["Speed"], label=driver1, linewidth=2, **style1)
    ax.plot(tel_d2["Distance"], tel_d2["Speed"], label=driver2, linewidth=2, **style2)
    ax.set_xlabel("Distance (m)")
    ax.set_ylabel("Speed (km/h)")
    ax.legend()
    fig.suptitle(
        f"Fastest Lap Comparison\n{session.event.year} {session.event['EventName']}"
    )
    return fig


def plot_fastest_sectors(session, driver1, driver2, lap_selection="fastest"):
    laps = session.laps
    if lap_selection == "fastest":
        lap_d1 = laps.pick_driver(driver1).pick_fastest()
        lap_d2 = laps.pick_driver(driver2).pick_fastest()
    else:
        lap_d1 = laps.pick_driver(driver1).pick_lap(lap_selection[0])
        lap_d2 = laps.pick_driver(driver2).pick_lap(lap_selection[1])

    tel_d1 = lap_d1.get_telemetry().add_distance().copy()
    tel_d2 = lap_d2.get_telemetry().add_distance().copy()
    tel_d1["Driver"] = driver1
    tel_d2["Driver"] = driver2
    telemetry = pd.concat([tel_d1, tel_d2], ignore_index=True)

    total_minisectors = 25
    telemetry["Minisector"] = (
        pd.cut(telemetry["Distance"], total_minisectors, labels=False, duplicates="drop")
        + 1
    )

    average_speed = (
        telemetry.groupby(["Driver", "Minisector"], dropna=False)["Speed"]
        .mean()
        .reset_index()
    )

    speed_lookup = average_speed.pivot(
        index="Minisector", columns="Driver", values="Speed"
    )
    valid_minisectors = speed_lookup.dropna(subset=[driver1, driver2]).index.tolist()
    telemetry = telemetry[telemetry["Minisector"].isin(valid_minisectors)].copy()

    telemetry["Fastest Driver"] = telemetry["Minisector"].map(
        lambda sector: driver1
        if speed_lookup.loc[sector, driver1] > speed_lookup.loc[sector, driver2]
        else driver2
    )
    telemetry["Fastest Driver int"] = telemetry["Fastest Driver"].map(
        {driver1: 1, driver2: 2}
    )

    x = np.array(telemetry["X"].values)
    y = np.array(telemetry["Y"].values)
    points = np.array([x, y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)

    colors = [
        matplotlib.colors.to_rgb(get_team_color(session, driver1)),
        matplotlib.colors.to_rgb(get_team_color(session, driver2)),
    ]
    cmap = matplotlib.colors.ListedColormap(colors)

    fig, ax = plt.subplots(figsize=(18, 10))
    lc_comp = LineCollection(segments, norm=plt.Normalize(1, cmap.N + 1), cmap=cmap)
    lc_comp.set_array(telemetry["Fastest Driver int"].to_numpy().astype(float))
    lc_comp.set_linewidth(5)

    ax.add_collection(lc_comp)
    ax.axis("equal")
    ax.tick_params(labelleft=False, left=False, labelbottom=False, bottom=False)

    cbar = plt.colorbar(mappable=lc_comp, boundaries=np.arange(1, 4))
    cbar.set_ticks([1.5, 2.5])
    cbar.set_ticklabels([driver1, driver2])

    lap_text = (
        "Fastest Laps"
        if lap_selection == "fastest"
        else f"Laps: {driver1}:{lap_selection[0]}, {driver2}:{lap_selection[1]}"
    )
    fig.suptitle(
        f"Fastest Sectors Comparison - {lap_text}\n"
        f"{session.event.year} {session.event['EventName']}"
    )
    return fig


def plot_full_telemetry(session, driver1, driver2):
    fastest_d1 = session.laps.pick_driver(driver1).pick_fastest()
    fastest_d2 = session.laps.pick_driver(driver2).pick_fastest()

    tel_d1 = fastest_d1.get_car_data().add_distance()
    tel_d2 = fastest_d2.get_car_data().add_distance()
    delta_time, ref_tel, _ = utils.delta_time(fastest_d1, fastest_d2)

    style1 = get_driver_style(session, driver1, ["color", "linestyle"])
    style2 = get_driver_style(session, driver2, ["color", "linestyle"])

    fig, axes = plt.subplots(6, 1, figsize=(12, 16), sharex=True)
    axes[0].plot(ref_tel["Distance"], delta_time, linewidth=2, **style1)
    axes[0].axhline(y=0, color="white", linestyle="-", alpha=0.5)
    axes[0].set_ylabel("Delta (s)")

    plot_pairs = [
        ("Speed", "Speed (km/h)"),
        ("Throttle", "Throttle (%)"),
        ("Brake", "Brake"),
        ("RPM", "RPM"),
        ("nGear", "Gear"),
    ]
    for axis, (column, label) in zip(axes[1:], plot_pairs):
        axis.plot(tel_d1["Distance"], tel_d1[column], linewidth=2, label=driver1, **style1)
        axis.plot(tel_d2["Distance"], tel_d2[column], linewidth=2, label=driver2, **style2)
        axis.set_ylabel(label)

    axes[-1].set_xlabel("Distance (m)")
    axes[1].legend()
    fig.suptitle(
        f"Full Telemetry Comparison\n{session.event.year} {session.event['EventName']}"
    )
    return fig


def plot_sectors(session, driver1, driver2):
    laps_d1 = session.laps.pick_driver(driver1)
    laps_d2 = session.laps.pick_driver(driver2)
    color1 = get_driver_color(session, driver1)
    color2 = get_driver_color(session, driver2)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    sectors = ["Sector1Time", "Sector2Time", "Sector3Time"]

    for sector, ax in zip(sectors, axes):
        bp = ax.boxplot(
            [
                laps_d1[sector].dt.total_seconds().dropna(),
                laps_d2[sector].dt.total_seconds().dropna(),
            ],
            patch_artist=True,
        )
        bp["boxes"][0].set_facecolor(color1)
        bp["boxes"][1].set_facecolor(color2)

        for box in bp["boxes"]:
            box.set_edgecolor("white")
        for whisker in bp["whiskers"]:
            whisker.set_color("white")
        for cap in bp["caps"]:
            cap.set_color("white")
        for median in bp["medians"]:
            median.set_color("white")

        ax.set_xticklabels([driver1, driver2])
        ax.set_title(f"{sector[:-4]} {sector[-4:]}")
        ax.grid(True, alpha=0.2)

    fig.suptitle(
        f"Sector Times Comparison\n{session.event.year} {session.event['EventName']}"
    )
    return fig


def plot_speed_map(session, driver):
    lap = session.laps.pick_driver(driver).pick_fastest()
    x = lap.telemetry["X"]
    y = lap.telemetry["Y"]
    speed = lap.telemetry["Speed"]

    points = np.array([x, y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)

    fig, ax = plt.subplots(sharex=True, sharey=True, figsize=(12, 6.75))
    fig.suptitle(
        f'{session.event["EventName"]} {session.event.year}\n{driver} - Speed',
        size=24,
        y=0.97,
    )
    plt.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.12)
    ax.axis("off")
    ax.plot(x, y, color="black", linestyle="-", linewidth=16, zorder=0)

    norm = plt.Normalize(speed.min(), speed.max())
    line_collection = LineCollection(
        segments, cmap="plasma", norm=norm, linestyle="-", linewidth=5
    )
    line_collection.set_array(speed)
    ax.add_collection(line_collection)

    cbaxes = fig.add_axes([0.25, 0.05, 0.5, 0.05])
    legend = matplotlib.colorbar.ColorbarBase(
        cbaxes,
        norm=matplotlib.colors.Normalize(vmin=speed.min(), vmax=speed.max()),
        cmap="plasma",
        orientation="horizontal",
    )
    legend.set_label("Speed (km/h)", size=12)
    return fig


def plot_gear_shifts_on_track(session, driver):
    lap = session.laps.pick_driver(driver).pick_fastest()
    if lap is None:
        raise ValueError("No fastest lap is available for this driver in the selected session.")

    telemetry = lap.get_telemetry().copy()
    telemetry = telemetry.dropna(subset=["X", "Y", "nGear"])
    if telemetry.empty:
        raise ValueError("No telemetry is available for gear shift analysis.")

    x = telemetry["X"].to_numpy()
    y = telemetry["Y"].to_numpy()
    gear = telemetry["nGear"].astype(int).to_numpy()

    points = np.array([x, y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)

    fig, ax = plt.subplots(figsize=(12, 6.75))
    fig.suptitle(
        f'{session.event["EventName"]} {session.event.year}\n{driver} - Gear Shifts',
        size=22,
        y=0.97,
    )

    ax.axis("off")
    ax.plot(x, y, color="black", linestyle="-", linewidth=12, zorder=0)

    cmap = plt.cm.get_cmap("Paired", 8)
    line_collection = LineCollection(
        segments,
        cmap=cmap,
        norm=plt.Normalize(1, 8),
        linewidth=5,
    )
    line_collection.set_array(gear[:-1])
    ax.add_collection(line_collection)
    ax.axis("equal")

    cbaxes = fig.add_axes([0.25, 0.05, 0.5, 0.05])
    colorbar = matplotlib.colorbar.ColorbarBase(
        cbaxes,
        cmap=cmap,
        norm=matplotlib.colors.Normalize(vmin=1, vmax=8),
        orientation="horizontal",
    )
    colorbar.set_ticks(range(1, 9))
    colorbar.set_label("Gear", size=12)

    plt.tight_layout()
    return fig


def plot_corner_annotated_speed_trace(session, driver):
    lap = session.laps.pick_driver(driver).pick_fastest()
    if lap is None:
        raise ValueError("No fastest lap is available for this driver in the selected session.")

    telemetry = lap.get_car_data().add_distance().copy()
    telemetry = telemetry.dropna(subset=["Distance", "Speed"])
    if telemetry.empty:
        raise ValueError("No telemetry is available for speed trace analysis.")

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(
        telemetry["Distance"],
        telemetry["Speed"],
        color=get_driver_color(session, driver),
        linewidth=2.5,
        label=driver,
    )

    try:
        circuit_info = session.get_circuit_info()
        corners = circuit_info.corners.copy()
    except Exception:
        corners = pd.DataFrame()

    if not corners.empty and {"Distance", "Number", "Letter"}.issubset(corners.columns):
        corners = corners.dropna(subset=["Distance"])
        max_speed = telemetry["Speed"].max()

        for _, corner in corners.iterrows():
            distance = float(corner["Distance"])
            label = f"{int(corner['Number'])}{corner['Letter'] or ''}".strip()
            ax.axvline(distance, color="white", linestyle="--", linewidth=0.7, alpha=0.25)
            ax.text(
                distance,
                max_speed + 2,
                label,
                fontsize=8,
                ha="center",
                va="bottom",
                rotation=90,
            )

    ax.set_xlabel("Distance (m)")
    ax.set_ylabel("Speed (km/h)")
    ax.set_title("Corner-Annotated Speed Trace")
    ax.grid(axis="x", alpha=0.2)
    ax.legend()
    fig.suptitle(
        f'{session.event["EventName"]} {session.event.year}\n{driver} - Corner Speed Trace'
    )
    plt.tight_layout()
    return fig


def plot_weather_track_evolution(session):
    weather = getattr(session, "weather_data", None)
    if weather is None or weather.empty:
        raise ValueError("No weather data is available for this session.")

    weather = weather.copy()
    if "Time" not in weather.columns:
        raise ValueError("Weather data does not include time information.")

    weather_seconds = weather["Time"].dt.total_seconds()
    metrics = [
        ("TrackTemp", "Track Temp (C)"),
        ("AirTemp", "Air Temp (C)"),
        ("Humidity", "Humidity (%)"),
        ("WindSpeed", "Wind Speed"),
    ]
    available_metrics = [(col, label) for col, label in metrics if col in weather.columns]

    if not available_metrics:
        raise ValueError("No supported weather metrics are available for this session.")

    fig, axes = plt.subplots(len(available_metrics), 1, figsize=(14, 3.2 * len(available_metrics)), sharex=True)
    if len(available_metrics) == 1:
        axes = [axes]

    for ax, (column, label) in zip(axes, available_metrics):
        ax.plot(weather_seconds, weather[column], linewidth=2)
        ax.set_ylabel(label)
        ax.grid(axis="x", alpha=0.2)

    if "Rainfall" in weather.columns:
        rainfall = weather["Rainfall"].fillna(False).astype(bool)
        rain_times = weather_seconds[rainfall]
        if not rain_times.empty:
            for ax in axes:
                for timestamp in rain_times:
                    ax.axvline(timestamp, color="#4da6ff", linewidth=0.8, alpha=0.15)

    axes[-1].set_xlabel("Session Time (s)")
    fig.suptitle(
        f"{session.event.year} {session.event['EventName']} Weather and Track Evolution"
    )
    plt.tight_layout()
    return fig


def plot_lap_distribution(session):
    point_finishers = session.drivers[:10]
    driver_laps = session.laps.pick_drivers(point_finishers).pick_quicklaps().reset_index()
    driver_laps["LapTime(s)"] = driver_laps["LapTime"].dt.total_seconds()
    finishing_order = [session.get_driver(i)["Abbreviation"] for i in point_finishers]

    fig, ax = plt.subplots(figsize=(18, 10))
    sns.violinplot(
        data=driver_laps,
        x="Driver",
        y="LapTime(s)",
        hue="Driver",
        inner=None,
        density_norm="area",
        order=finishing_order,
        palette=ff1_plotting.get_driver_color_mapping(session=session),
        ax=ax,
    )
    if ax.legend_ is not None:
        ax.legend_.remove()

    compounds = driver_laps["Compound"].dropna().unique()
    sns.swarmplot(
        data=driver_laps,
        x="Driver",
        y="LapTime(s)",
        order=finishing_order,
        hue="Compound",
        palette=ff1_plotting.get_compound_mapping(session=session),
        hue_order=compounds,
        linewidth=0,
        size=4,
        ax=ax,
    )

    ax.set_xlabel("Driver")
    ax.set_ylabel("Lap Time (s)")
    fig.suptitle(
        f"{session.event.year} {session.event['EventName']} Lap Time Distributions"
    )
    sns.despine(left=True, bottom=True)
    plt.tight_layout()
    return fig


def plot_tyre_strategy(session):
    laps = session.laps[["Driver", "Stint", "Compound", "LapNumber"]].copy()
    laps = laps.dropna(subset=["Driver", "Stint", "Compound", "LapNumber"])
    laps["Stint"] = laps["Stint"].astype(int)

    stint_data = (
        laps.groupby(["Driver", "Stint", "Compound"])
        .size()
        .reset_index(name="StintLength")
    )

    if hasattr(session, "results") and session.results is not None and not session.results.empty:
        driver_order = (
            session.results["Abbreviation"].dropna().astype(str).tolist()
        )
    else:
        driver_order = sorted(stint_data["Driver"].unique().tolist())

    compound_colors = ff1_plotting.get_compound_mapping(session=session)

    fig, ax = plt.subplots(figsize=(14, max(6, len(driver_order) * 0.45)))

    for row_index, driver in enumerate(driver_order):
        driver_stints = stint_data[stint_data["Driver"] == driver].sort_values("Stint")
        stint_start = 0

        for _, stint in driver_stints.iterrows():
            compound = str(stint["Compound"])
            ax.barh(
                y=row_index,
                width=stint["StintLength"],
                left=stint_start,
                color=compound_colors.get(compound, "#888888"),
                edgecolor="black",
                height=0.8,
            )
            stint_start += stint["StintLength"]

    ax.set_yticks(range(len(driver_order)))
    ax.set_yticklabels(driver_order)
    ax.invert_yaxis()
    ax.set_xlabel("Laps")
    ax.set_ylabel("Driver")
    ax.set_title("Tyre Strategy")
    ax.grid(axis="x", alpha=0.2)

    legend_compounds = [
        compound for compound in ["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"]
        if compound in compound_colors
    ]
    if legend_compounds:
        handles = [
            plt.Rectangle((0, 0), 1, 1, color=compound_colors[compound])
            for compound in legend_compounds
        ]
        ax.legend(handles, legend_compounds, title="Compound", loc="upper right")

    fig.suptitle(f"{session.event.year} {session.event['EventName']} Tyre Strategy")
    plt.tight_layout()
    return fig


def plot_team_pace(session):
    laps = session.laps.pick_quicklaps().copy()
    laps = laps.dropna(subset=["Team", "LapTime"])

    if laps.empty:
        raise ValueError("No quick laps available for team pace analysis.")

    laps["LapTimeSeconds"] = laps["LapTime"].dt.total_seconds()

    team_order = (
        laps.groupby("Team")["LapTimeSeconds"]
        .median()
        .sort_values()
        .index
        .tolist()
    )

    fig, ax = plt.subplots(figsize=(14, max(6, len(team_order) * 0.45)))
    palette = {team: ff1_plotting.get_team_color(team, session=session) for team in team_order}

    sns.boxplot(
        data=laps,
        x="LapTimeSeconds",
        y="Team",
        order=team_order,
        palette=palette,
        linewidth=1,
        fliersize=0,
        ax=ax,
    )

    sns.stripplot(
        data=laps,
        x="LapTimeSeconds",
        y="Team",
        order=team_order,
        color="white",
        alpha=0.35,
        size=2.5,
        ax=ax,
    )

    ax.set_xlabel("Lap Time (s)")
    ax.set_ylabel("Team")
    ax.set_title("Team Pace Comparison")
    ax.grid(axis="x", alpha=0.2)
    fig.suptitle(f"{session.event.year} {session.event['EventName']} Team Pace")
    plt.tight_layout()
    return fig


def plot_qualifying_overview(session):
    if not hasattr(session, "results") or session.results is None or session.results.empty:
        raise ValueError("No qualifying results are available for this session.")

    results = session.results.copy()
    results = results.dropna(subset=["Abbreviation"])

    columns = ["Abbreviation", "Position", "Q1", "Q2", "Q3"]
    for column in columns:
        if column not in results.columns:
            raise ValueError("This qualifying session does not include complete Q1/Q2/Q3 data.")

    quali = results[columns].copy()
    quali["Position"] = pd.to_numeric(quali["Position"], errors="coerce")
    quali = quali.dropna(subset=["Position"]).sort_values("Position")

    q_columns = ["Q1", "Q2", "Q3"]
    for column in q_columns:
        quali[column] = pd.to_timedelta(quali[column], errors="coerce").dt.total_seconds()

    plot_data = quali.melt(
        id_vars=["Abbreviation", "Position"],
        value_vars=q_columns,
        var_name="SessionPart",
        value_name="LapTimeSeconds",
    ).dropna(subset=["LapTimeSeconds"])

    if plot_data.empty:
        raise ValueError("No qualifying lap times are available to plot.")

    driver_order = quali["Abbreviation"].tolist()
    fig, ax = plt.subplots(figsize=(14, max(6, len(driver_order) * 0.45)))

    sns.pointplot(
        data=plot_data,
        x="LapTimeSeconds",
        y="Abbreviation",
        hue="SessionPart",
        order=driver_order,
        dodge=0.5,
        join=False,
        markers=["o", "s", "D"],
        errorbar=None,
        ax=ax,
    )

    ax.set_xlabel("Lap Time (s)")
    ax.set_ylabel("Driver")
    ax.set_title("Qualifying Overview")
    ax.grid(axis="x", alpha=0.2)
    ax.legend(title="Session")
    fig.suptitle(f"{session.event.year} {session.event['EventName']} Qualifying Overview")
    plt.tight_layout()
    return fig


def plot_position_changes(session):
    fig, ax = plt.subplots(figsize=(15, 8))
    for drv in session.drivers:
        drv_laps = session.laps.pick_drivers(drv)
        if (
            drv_laps.empty
            or "Position" not in drv_laps.columns
            or drv_laps["Position"].isna().all()
        ):
            continue

        abb = drv_laps["Driver"].iloc[0]
        style = get_driver_style(session, abb, ["color", "linestyle"])
        ax.plot(drv_laps["LapNumber"], drv_laps["Position"], label=abb, linewidth=2, **style)

    ax.set_ylim([20.5, 0.5])
    ax.set_yticks([1, 5, 10, 15, 20])
    ax.set_xlabel("Lap")
    ax.set_ylabel("Position")
    ax.legend(bbox_to_anchor=(1.0, 1.02))
    fig.suptitle(f"{session.event.year} {session.event['EventName']} Position Changes")
    plt.tight_layout()
    return fig


def figure_to_png_bytes(fig):
    buffer = BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", dpi=200)
    buffer.seek(0)
    return buffer.getvalue()


def export_data_for_analysis(session, selection):
    analysis_type = selection.analysis_type

    if analysis_type == "Tyre Strategy":
        laps = session.laps[["Driver", "Stint", "Compound", "LapNumber"]].copy()
        laps = laps.dropna(subset=["Driver", "Stint", "Compound", "LapNumber"])
        return (
            laps.groupby(["Driver", "Stint", "Compound"])
            .size()
            .reset_index(name="StintLength")
        )

    if analysis_type == "Team Pace Comparison":
        laps = session.laps.pick_quicklaps().copy()
        laps = laps.dropna(subset=["Team", "LapTime"])
        laps["LapTimeSeconds"] = laps["LapTime"].dt.total_seconds()
        return laps[["Driver", "Team", "LapNumber", "LapTimeSeconds", "Compound"]]

    if analysis_type == "Qualifying Overview":
        results = session.results.copy()
        return results[[col for col in ["Abbreviation", "Position", "Q1", "Q2", "Q3"] if col in results.columns]]

    if analysis_type == "Weather and Track Evolution":
        return getattr(session, "weather_data", pd.DataFrame()).copy()

    if analysis_type in {"Speed Map", "Gear Shifts On Track", "Corner-Annotated Speed Trace"}:
        lap = session.laps.pick_driver(selection.driver_for_map).pick_fastest()
        if lap is None:
            return None
        telemetry = lap.get_telemetry().copy()
        return telemetry

    if analysis_type == "Lap Times":
        laps_1 = session.laps.pick_driver(selection.driver1_code).copy()
        laps_2 = session.laps.pick_driver(selection.driver2_code).copy()
        return pd.concat([laps_1, laps_2], ignore_index=True)

    return None
