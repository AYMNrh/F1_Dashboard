import fastf1 as ff1
import matplotlib
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st
from fastf1 import plotting, utils
from matplotlib import pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D

# Enable cache and setup plotting
ff1.Cache.enable_cache("cache")
ff1.plotting.setup_mpl(
    mpl_timedelta_support=True, misc_mpl_mods=False, color_scheme="fastf1"
)


def get_available_events(year):
    """Get all events for a given year"""
    schedule = ff1.get_event_schedule(year)
    return schedule["EventName"].tolist()


def get_drivers_in_session(session):
    """Get all drivers that participated in a session with their proper codes"""
    drivers_info = {}

    # Get driver info from session results
    for driver in session.drivers:
        try:
            driver_info = session.get_driver(driver)
            if driver_info is not None and not driver_info.empty:
                # Get the first row if multiple entries exist
                if isinstance(driver_info, pd.DataFrame):
                    driver_info = driver_info.iloc[0]

                code = driver_info["Abbreviation"]
                first_name = driver_info["FirstName"]
                last_name = driver_info["LastName"]

                # Create driver display name
                name = f"{first_name} {last_name} ({code})"
                drivers_info[name] = code
        except Exception as e:
            st.warning(f"Could not get info for driver {driver}: {str(e)}")
            continue

    return drivers_info


def get_team_color(session, driver_code):
    """Get team color for a driver"""
    driver_info = session.get_driver(driver_code)
    if isinstance(driver_info, pd.DataFrame):
        driver_info = driver_info.iloc[0]
    team = driver_info["TeamName"]
    return ff1.plotting.team_color(team)


def plot_laptime(session, driver1, driver2):
    """Plot laptimes comparison between two drivers"""
    plt.clf()
    laps_d1 = session.laps.pick_driver(driver1)
    laps_d2 = session.laps.pick_driver(driver2)

    color1 = get_team_color(session, driver1)
    color2 = get_team_color(session, driver2)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(laps_d1["LapNumber"], laps_d1["LapTime"], color=color1, label=driver1)
    ax.plot(laps_d2["LapNumber"], laps_d2["LapTime"], color=color2, label=driver2)

    ax.set_xlabel("Lap Number")
    ax.set_ylabel("Lap Time")
    ax.legend()
    plt.suptitle(
        f"Lap Time Comparison\n{session.event.year} {session.event['EventName']}"
    )

    return fig


def get_sectors(average_speed, driver1, driver2):
    """Calculate fastest sectors"""
    sectors_combined = (
        average_speed.groupby(["Driver", "Minisector"])["Speed"].mean().reset_index()
    )
    final = pd.DataFrame({"Driver": [], "Minisector": [], "Speed": []})

    d1 = sectors_combined.loc[sectors_combined["Driver"] == driver1]
    d2 = sectors_combined.loc[sectors_combined["Driver"] == driver2]

    for i in range(min(len(d1), len(d2))):
        d1_sector = d1.iloc[[i]].values.tolist()
        d1_speed = d1_sector[0][2]
        d2_sector = d2.iloc[[i]].values.tolist()
        d2_speed = d2_sector[0][2]
        final.loc[len(final)] = d1_sector[0] if d1_speed > d2_speed else d2_sector[0]

    return final


def plot_fastest_lap(session, driver1, driver2):
    """Plot fastest lap comparison with detailed telemetry"""
    plt.clf()
    fastest_d1 = session.laps.pick_driver(driver1).pick_fastest()
    fastest_d2 = session.laps.pick_driver(driver2).pick_fastest()

    tel_d1 = fastest_d1.get_car_data().add_distance()
    tel_d2 = fastest_d2.get_car_data().add_distance()

    color1 = get_team_color(session, driver1)
    color2 = get_team_color(session, driver2)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(tel_d1["Distance"], tel_d1["Speed"], color=color1, label=driver1)
    ax.plot(tel_d2["Distance"], tel_d2["Speed"], color=color2, label=driver2)

    ax.set_xlabel("Distance (m)")
    ax.set_ylabel("Speed (km/h)")
    ax.legend()
    plt.suptitle(
        f"Fastest Lap Comparison\n{session.event.year} {session.event['EventName']}"
    )

    return fig


def plot_fastest_sectors(session, driver1, driver2, lap_selection="fastest"):
    """Plot track map with fastest sectors"""
    plt.clf()
    laps = session.laps
    telemetry = pd.DataFrame()

    if lap_selection == "fastest":
        # Get fastest laps for both drivers
        lap_d1 = laps.pick_driver(driver1).pick_fastest()
        lap_d2 = laps.pick_driver(driver2).pick_fastest()
    else:
        # Get specific lap numbers for each driver
        lap_d1 = laps.pick_driver(driver1).pick_lap(lap_selection[0])
        lap_d2 = laps.pick_driver(driver2).pick_lap(lap_selection[1])

    # Get telemetry data
    tel_d1 = lap_d1.get_telemetry().add_distance()
    tel_d2 = lap_d2.get_telemetry().add_distance()

    # Add driver identifiers
    tel_d1["Driver"] = driver1
    tel_d2["Driver"] = driver2

    # Combine telemetry
    telemetry = pd.concat([tel_d1, tel_d2])

    # Create minisectors
    total_minisectors = 25
    telemetry["Minisector"] = (
        pd.cut(telemetry["Distance"], total_minisectors, labels=False) + 1
    )

    # Calculate average speed per minisector for each driver
    average_speed = (
        telemetry.groupby(["Driver", "Minisector"])["Speed"].mean().reset_index()
    )

    # Compare speeds and determine fastest driver for each minisector
    telemetry["Fastest Driver"] = ""
    telemetry["Fastest Driver int"] = 0

    for minisector in range(1, total_minisectors + 1):
        speed_d1 = average_speed[
            (average_speed["Driver"] == driver1)
            & (average_speed["Minisector"] == minisector)
        ]["Speed"].values[0]
        speed_d2 = average_speed[
            (average_speed["Driver"] == driver2)
            & (average_speed["Minisector"] == minisector)
        ]["Speed"].values[0]

        fastest = driver1 if speed_d1 > speed_d2 else driver2
        telemetry.loc[telemetry["Minisector"] == minisector, "Fastest Driver"] = fastest
        telemetry.loc[telemetry["Minisector"] == minisector, "Fastest Driver int"] = (
            1 if fastest == driver1 else 2
        )

    # Plotting
    plt.rcParams["figure.figsize"] = (18, 10)

    # Create segments for colored line
    x = np.array(telemetry["X"].values)
    y = np.array(telemetry["Y"].values)
    points = np.array([x, y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)

    # Create array of fastest driver for coloring
    fastest_driver_array = telemetry["Fastest Driver int"].to_numpy().astype(float)

    # Get team colors
    color1 = get_team_color(session, driver1)
    color2 = get_team_color(session, driver2)

    # Create custom colormap from team colors
    colors = [matplotlib.colors.to_rgb(color1), matplotlib.colors.to_rgb(color2)]
    cmap = matplotlib.colors.ListedColormap(colors)

    # Create the line collection
    lc_comp = LineCollection(segments, norm=plt.Normalize(1, cmap.N + 1), cmap=cmap)
    lc_comp.set_array(fastest_driver_array)
    lc_comp.set_linewidth(5)

    # Create the plot
    fig, ax = plt.subplots(figsize=(18, 10))
    ax.add_collection(lc_comp)
    ax.axis("equal")
    ax.tick_params(labelleft=False, left=False, labelbottom=False, bottom=False)

    # Add colorbar as legend
    cbar = plt.colorbar(mappable=lc_comp, boundaries=np.arange(1, 4))
    cbar.set_ticks([1.5, 2.5])
    cbar.set_ticklabels([driver1, driver2])

    # Add title
    lap_text = (
        "Fastest Laps"
        if lap_selection == "fastest"
        else f"Laps: {driver1}:{lap_selection[0]}, {driver2}:{lap_selection[1]}"
    )
    plt.suptitle(
        f"Fastest Sectors Comparison - {lap_text}\n{session.event.year} {session.event['EventName']}"
    )

    return fig


def plot_full_telemetry(session, driver1, driver2):
    """Plot detailed telemetry comparison"""
    plt.clf()
    fastest_d1 = session.laps.pick_driver(driver1).pick_fastest()
    fastest_d2 = session.laps.pick_driver(driver2).pick_fastest()

    tel_d1 = fastest_d1.get_car_data().add_distance()
    tel_d2 = fastest_d2.get_car_data().add_distance()

    delta_time, ref_tel, compare_tel = utils.delta_time(fastest_d1, fastest_d2)

    color1 = get_team_color(session, driver1)
    color2 = get_team_color(session, driver2)

    fig, axes = plt.subplots(6, 1, figsize=(12, 16), sharex=True)

    # Delta
    axes[0].plot(ref_tel["Distance"], delta_time, color=color1)
    axes[0].axhline(y=0, color="white", linestyle="-", alpha=0.5)
    axes[0].set_ylabel("Delta (s)")

    # Speed
    axes[1].plot(tel_d1["Distance"], tel_d1["Speed"], color=color1, label=driver1)
    axes[1].plot(tel_d2["Distance"], tel_d2["Speed"], color=color2, label=driver2)
    axes[1].set_ylabel("Speed (km/h)")

    # Throttle
    axes[2].plot(tel_d1["Distance"], tel_d1["Throttle"], color=color1)
    axes[2].plot(tel_d2["Distance"], tel_d2["Throttle"], color=color2)
    axes[2].set_ylabel("Throttle (%)")

    # Brake
    axes[3].plot(tel_d1["Distance"], tel_d1["Brake"], color=color1)
    axes[3].plot(tel_d2["Distance"], tel_d2["Brake"], color=color2)
    axes[3].set_ylabel("Brake")

    # RPM
    axes[4].plot(tel_d1["Distance"], tel_d1["RPM"], color=color1)
    axes[4].plot(tel_d2["Distance"], tel_d2["RPM"], color=color2)
    axes[4].set_ylabel("RPM")

    # Gear
    axes[5].plot(tel_d1["Distance"], tel_d1["nGear"], color=color1)
    axes[5].plot(tel_d2["Distance"], tel_d2["nGear"], color=color2)
    axes[5].set_ylabel("Gear")
    axes[5].set_xlabel("Distance (m)")

    plt.suptitle(
        f"Full Telemetry Comparison\n{session.event.year} {session.event['EventName']}"
    )
    axes[0].legend([driver1, driver2])

    return fig


def plot_sectors(session, driver1, driver2):
    """Plot sector times comparison between two drivers"""
    plt.clf()

    laps_d1 = session.laps.pick_driver(driver1)
    laps_d2 = session.laps.pick_driver(driver2)

    color1 = get_team_color(session, driver1)
    color2 = get_team_color(session, driver2)

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 5))

    sectors = ["Sector1Time", "Sector2Time", "Sector3Time"]
    axes = [ax1, ax2, ax3]

    for sector, ax in zip(sectors, axes):
        sector_times_d1 = laps_d1[sector].dt.total_seconds()
        sector_times_d2 = laps_d2[sector].dt.total_seconds()

        box_data = [sector_times_d1, sector_times_d2]
        bp = ax.boxplot(box_data, patch_artist=True)

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

    plt.suptitle(
        f"Sector Times Comparison\n{session.event.year} {session.event['EventName']}"
    )

    return fig


def plot_speed_map(session, driver):
    """Plot speed visualization on track map for a single driver"""
    plt.clf()

    # Get fastest lap for the driver
    lap = session.laps.pick_driver(driver).pick_fastest()

    # Get telemetry data
    x = lap.telemetry["X"]  # values for x-axis
    y = lap.telemetry["Y"]  # values for y-axis
    color = lap.telemetry["Speed"]  # value to base color gradient on

    # Create line segments
    points = np.array([x, y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)

    # Create the plot
    fig, ax = plt.subplots(sharex=True, sharey=True, figsize=(12, 6.75))

    # Set title
    fig.suptitle(
        f'{session.event["EventName"]} {session.event.year}\n{driver} - Speed',
        size=24,
        y=0.97,
    )

    # Adjust margins and turn off axis
    plt.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.12)
    ax.axis("off")

    # Create background track line
    ax.plot(
        lap.telemetry["X"],
        lap.telemetry["Y"],
        color="black",
        linestyle="-",
        linewidth=16,
        zorder=0,
    )

    # Create a continuous norm to map from data points to colors
    norm = plt.Normalize(color.min(), color.max())
    lc = LineCollection(segments, cmap="plasma", norm=norm, linestyle="-", linewidth=5)

    # Set the values used for colormapping
    lc.set_array(color)

    # Merge all line segments together
    line = ax.add_collection(lc)

    # Add colorbar
    cbaxes = fig.add_axes([0.25, 0.05, 0.5, 0.05])
    normlegend = matplotlib.colors.Normalize(vmin=color.min(), vmax=color.max())
    legend = matplotlib.colorbar.ColorbarBase(
        cbaxes, norm=normlegend, cmap="plasma", orientation="horizontal"
    )
    legend.set_label("Speed (km/h)", size=12)

    return fig


def plot_lap_distribution(session):
    """Plot lap time distributions for top 10 finishers with tire compounds"""
    plt.clf()

    # Get all the laps for the point finishers only
    point_finishers = session.drivers[:10]
    driver_laps = session.laps.pick_drivers(point_finishers).pick_quicklaps()
    driver_laps = driver_laps.reset_index()

    # Get finishing order abbreviations
    finishing_order = [session.get_driver(i)["Abbreviation"] for i in point_finishers]

    # Create the figure
    fig, ax = plt.subplots(figsize=(18, 10))

    # Convert timedelta to float (seconds) for seaborn compatibility
    driver_laps["LapTime(s)"] = driver_laps["LapTime"].dt.total_seconds()

    # Create violin plot for lap time distributions
    sns.violinplot(
        data=driver_laps,
        x="Driver",
        y="LapTime(s)",
        hue="Driver",
        inner=None,
        density_norm="area",
        order=finishing_order,
        palette=ff1.plotting.get_driver_color_mapping(session=session),
    )

    # Get unique compounds in the session
    compounds = driver_laps["Compound"].unique()

    # Add swarm plot for tire compounds
    sns.swarmplot(
        data=driver_laps,
        x="Driver",
        y="LapTime(s)",
        order=finishing_order,
        hue="Compound",
        palette=ff1.plotting.get_compound_mapping(session=session),
        hue_order=compounds,  # Use actual compounds from session
        linewidth=0,
        size=4,
    )

    # Customize plot appearance
    ax.set_xlabel("Driver")
    ax.set_ylabel("Lap Time (s)")
    plt.suptitle(
        f"{session.event.year} {session.event['EventName']} Lap Time Distributions"
    )
    sns.despine(left=True, bottom=True)

    plt.tight_layout()
    return fig


def plot_position_changes(session):
    """Plot position changes throughout the race for all drivers"""
    plt.clf()

    # Create the figure
    fig, ax = plt.subplots(figsize=(15, 8))

    # Plot each driver's position
    for drv in session.drivers:
        drv_laps = session.laps.pick_drivers(drv)

        # Skip if no laps or position data
        if (
            drv_laps.empty
            or "Position" not in drv_laps.columns
            or drv_laps["Position"].isna().all()
        ):
            continue

        # Get driver abbreviation and style
        abb = drv_laps["Driver"].iloc[0]
        style = ff1.plotting.get_driver_style(
            identifier=abb, style=["color", "linestyle"], session=session
        )

        # Plot position changes
        ax.plot(
            drv_laps["LapNumber"], drv_laps["Position"], label=abb, linewidth=2, **style
        )

    # Customize plot appearance
    ax.set_ylim([20.5, 0.5])  # Reverse y-axis to show P1 at top
    ax.set_yticks([1, 5, 10, 15, 20])
    ax.set_xlabel("Lap")
    ax.set_ylabel("Position")
    ax.legend(bbox_to_anchor=(1.0, 1.02))

    plt.suptitle(f"{session.event.year} {session.event['EventName']} Position Changes")
    plt.tight_layout()

    return fig


def main():
    st.title("F1 Session Analysis Dashboard")

    # Create two columns with different widths (1:3 ratio for more plot space)
    col1, col2 = st.columns([1, 3])

    # Put all selections in the left column with a more compact layout
    with col1:
        st.markdown("### Settings")  # Smaller header

        # Create tabs for better organization
        settings_tab, driver_tab, analysis_tab = st.tabs(
            ["Session", "Drivers", "Analysis"]
        )

        with settings_tab:
            year = st.selectbox("Year", range(2010, 2025), label_visibility="collapsed")
            events = get_available_events(year)
            gp = st.selectbox("Grand Prix", events, label_visibility="collapsed")
            session_type = st.selectbox(
                "Session",
                ["FP1", "FP2", "FP3", "Sprint", "Q", "R"],
                label_visibility="collapsed",
            )

        try:
            session = ff1.get_session(year, gp, session_type)
            session.load()

            with driver_tab:
                # Driver selection
                drivers_info = get_drivers_in_session(session)
                driver1_name = st.selectbox(
                    "Driver 1", list(drivers_info.keys()), label_visibility="collapsed"
                )
                remaining_drivers = {
                    k: v for k, v in drivers_info.items() if k != driver1_name
                }
                driver2_name = st.selectbox(
                    "Driver 2",
                    list(remaining_drivers.keys()),
                    label_visibility="collapsed",
                )

                # Get the driver codes for the selected names
                driver1 = drivers_info[driver1_name]
                driver2 = drivers_info[driver2_name]

            with analysis_tab:
                # Analysis type selection
                analysis_types = {
                    "Lap Times": plot_laptime,
                    "Sector Comparison": plot_sectors,
                    "Fastest Lap": plot_fastest_lap,
                    "Fastest Sectors": plot_fastest_sectors,
                    "Full Telemetry": plot_full_telemetry,
                    "Speed Map": plot_speed_map,
                    "Lap Time Distribution": plot_lap_distribution,
                    "Position Changes": plot_position_changes,
                }

                analysis_type = st.selectbox(
                    "Analysis Type",
                    list(analysis_types.keys()),
                    label_visibility="collapsed",
                )

                # Add lap selection for Fastest Sectors analysis
                if analysis_type == "Fastest Sectors":
                    use_fastest = st.checkbox("Use Fastest Laps", value=True)
                    if not use_fastest:
                        laps_d1 = session.laps.pick_driver(driver1)[
                            "LapNumber"
                        ].tolist()
                        lap_d1 = st.selectbox(
                            f"Lap ({driver1})", laps_d1, label_visibility="collapsed"
                        )
                        laps_d2 = session.laps.pick_driver(driver2)[
                            "LapNumber"
                        ].tolist()
                        lap_d2 = st.selectbox(
                            f"Lap ({driver2})", laps_d2, label_visibility="collapsed"
                        )

                # Add driver selection for Speed Map
                if analysis_type == "Speed Map":
                    selected_driver = st.radio(
                        "Driver for Speed Map",
                        [driver1_name, driver2_name],
                        horizontal=True,
                    )
                    driver_for_map = drivers_info[selected_driver]

                generate_plot = st.button("Generate Plot", use_container_width=True)

        except Exception as e:
            st.error(f"Error loading data: {str(e)}")
            return

    # Put the plot in the right column with more space
    with col2:
        if "generate_plot" in locals() and generate_plot:
            with st.spinner("Generating plot..."):
                try:
                    if analysis_type == "Fastest Sectors":
                        lap_selection = "fastest" if use_fastest else (lap_d1, lap_d2)
                        fig = plot_fastest_sectors(
                            session, driver1, driver2, lap_selection
                        )
                    elif analysis_type == "Speed Map":
                        fig = plot_speed_map(session, driver_for_map)
                    elif analysis_type == "Lap Time Distribution":
                        fig = plot_lap_distribution(session)
                    elif analysis_type == "Position Changes":
                        fig = plot_position_changes(session)
                    else:
                        fig = analysis_types[analysis_type](session, driver1, driver2)

                    # Use the full width of the column for the plot
                    st.pyplot(fig, use_container_width=True)
                    plt.close()
                except Exception as e:
                    st.error(f"Error generating plot: {str(e)}")


if __name__ == "__main__":
    main()
