from __future__ import annotations

import fastf1 as ff1
import matplotlib
import numpy as np
import pandas as pd
import seaborn as sns
from fastf1 import plotting as ff1_plotting, utils
from matplotlib import pyplot as plt
from matplotlib.collections import LineCollection

from app.services.sessions import get_team_color


def plot_laptime(session, driver1, driver2):
    laps_d1 = session.laps.pick_driver(driver1)
    laps_d2 = session.laps.pick_driver(driver2)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(
        laps_d1["LapNumber"],
        laps_d1["LapTime"],
        color=get_team_color(session, driver1),
        label=driver1,
    )
    ax.plot(
        laps_d2["LapNumber"],
        laps_d2["LapTime"],
        color=get_team_color(session, driver2),
        label=driver2,
    )
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

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(
        tel_d1["Distance"],
        tel_d1["Speed"],
        color=get_team_color(session, driver1),
        label=driver1,
    )
    ax.plot(
        tel_d2["Distance"],
        tel_d2["Speed"],
        color=get_team_color(session, driver2),
        label=driver2,
    )
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

    color1 = get_team_color(session, driver1)
    color2 = get_team_color(session, driver2)

    fig, axes = plt.subplots(6, 1, figsize=(12, 16), sharex=True)
    axes[0].plot(ref_tel["Distance"], delta_time, color=color1)
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
        axis.plot(tel_d1["Distance"], tel_d1[column], color=color1, label=driver1)
        axis.plot(tel_d2["Distance"], tel_d2[column], color=color2, label=driver2)
        axis.set_ylabel(label)

    axes[-1].set_xlabel("Distance (m)")
    axes[0].legend([driver1, driver2])
    fig.suptitle(
        f"Full Telemetry Comparison\n{session.event.year} {session.event['EventName']}"
    )
    return fig


def plot_sectors(session, driver1, driver2):
    laps_d1 = session.laps.pick_driver(driver1)
    laps_d2 = session.laps.pick_driver(driver2)
    color1 = get_team_color(session, driver1)
    color2 = get_team_color(session, driver2)

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
        style = ff1_plotting.get_driver_style(
            identifier=abb, style=["color", "linestyle"], session=session
        )
        ax.plot(drv_laps["LapNumber"], drv_laps["Position"], label=abb, linewidth=2, **style)

    ax.set_ylim([20.5, 0.5])
    ax.set_yticks([1, 5, 10, 15, 20])
    ax.set_xlabel("Lap")
    ax.set_ylabel("Position")
    ax.legend(bbox_to_anchor=(1.0, 1.02))
    fig.suptitle(f"{session.event.year} {session.event['EventName']} Position Changes")
    plt.tight_layout()
    return fig
