# F1 Race Analysis Dashboard

A dynamic Formula 1 data analysis dashboard built with Streamlit and FastF1 API. This project provides real-time analysis and visualization of Formula 1 race data, enabling detailed comparisons of driver performances, lap times, and race strategies.

## Features

- **Session Selection**: Choose any F1 session from 2010 to 2024
- **Driver Comparison**: Compare any two drivers in the selected session
- **Multiple Analysis Types**:
  - Lap Time Analysis
  - Sector Comparisons
  - Fastest Lap Analysis
  - Track Position Changes
  - Full Telemetry Data
  - Speed Maps
  - Lap Time Distribution

## Technology Stack

- **FastF1**: Official Formula 1 timing data API
- **Streamlit**: Web application framework
- **Pandas**: Data manipulation and analysis
- **Matplotlib & Seaborn**: Data visualization
- **NumPy**: Numerical computing

## Examples

### Lap Time Comparison
Comparison of lap times between Max Verstappen and Charles Leclerc during the 2024 São Paulo Grand Prix.

![Lap Time Comparison](img/lap_times.jpg)

### Fastest Lap Analysis
Speed comparison of the fastest laps between Verstappen and Leclerc.

![Fastest Lap Comparison](img/fast_lap.jpg)

### Fastest Sectors Comparison
Track visualization showing which driver was faster in each sector during their fastest laps.

![Fastest Sectors](img/fast_sect.jpg)

### Full Telemetry Analysis
Detailed comparison of speed, throttle, brake, RPM, and gear usage throughout their fastest laps.

![Full Telemetry](img/full_telemetry.jpg)

### Race Position Changes
Visualization of position changes for all drivers throughout the race, showing overtakes and strategy impacts.

![Position Changes](img/position_changes.jpg)

## Installation

### Prerequisites
- Python 3.9 or higher
- Poetry (Python package manager)

```bash
# Install Poetry if you haven't already
curl -sSL https://install.python-poetry.org | python3 -

# Clone the repository
git clone https://github.com/yourusername/f1-analysis-dashboard.git
cd f1-analysis-dashboard

# Install dependencies using Poetry
poetry install

# Activate the virtual environment
poetry shell
```

## Usage

```bash
# Make sure you're in the Poetry shell
poetry shell

# Run the dashboard
streamlit run analysis.py

# Alternatively, run directly through Poetry
poetry run streamlit run analysis.py
```


## Data Processing

The dashboard processes Formula 1 data in real-time:
1. Fetches session data using FastF1 API
2. Cleans and processes timing data
3. Generates interactive visualizations
4. Handles both dry and wet race conditions
5. Processes telemetry data for detailed analysis

## Features in Detail

### Lap Time Analysis
- Compares lap times between two drivers
- Shows performance trends throughout the session
- Highlights fastest and slowest laps

### Sector Comparison
- Breaks down performance by track sectors
- Shows where each driver gains or loses time
- Visualizes sector time distributions

### Telemetry Analysis
- Speed traces
- Throttle and brake application
- Gear changes
- RPM data
- Delta time comparison

### Position Tracking
- Real-time position changes
- Strategy impact visualization
- Overtaking analysis

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- FastF1 API for providing access to Formula 1 timing data
- Formula 1 for the underlying data
- The F1 community for inspiration and support