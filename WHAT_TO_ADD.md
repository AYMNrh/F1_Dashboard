# What To Add

## Priority First

Start with these 3 additions:

1. Tyre strategy view
2. Team pace comparison
3. Qualifying overview

These add the most value because they expand the dashboard beyond direct driver-vs-driver telemetry and make the app more useful for race and session analysis.

## Recommended Enhancements

### 1. Tyre Strategy View

Add a race or sprint strategy chart showing:
- stint lengths per driver
- tyre compounds used during the session
- pit stop timing

Why:
- this is one of the most useful race-analysis views
- it gives strategy context that the current app is missing

FastF1 direction:
- use lap and compound data from the session
- make this available only for race-like sessions

### 2. Team Pace Comparison

Add a team-level pace comparison chart showing:
- average lap times by team
- optional filtering for quick laps only
- spread or consistency per team

Why:
- helps compare overall car performance, not just drivers
- complements the current driver comparison tools

FastF1 direction:
- use current plotting helpers and team mappings
- support boxplot or violin plot modes

### 3. Qualifying Overview

Add a qualifying view showing:
- Q1, Q2, Q3 progression
- final gaps to pole
- eliminated drivers by session phase

Why:
- qualifying is a major use case and deserves its own dedicated page
- the current app does not summarize quali structure well

FastF1 direction:
- use session results and lap data
- show this only for qualifying sessions

## Additional Improvements

### Use Modern FastF1 Plotting Helpers

Update comparison charts to use modern FastF1 styling:
- prefer `get_driver_style(...)`
- prefer `get_driver_color(...)`
- prefer `get_team_color(...)`

Why:
- newer FastF1 versions no longer follow the old helper patterns
- teammates should be separated by style, not color only

### Add Safer Data Handling

Improve robustness for:
- sessions where `pick_fastest()` returns `None`
- missing telemetry segments
- partial or unavailable 2025 and 2026 data
- unsupported chart and session combinations

### Improve Performance

Optimize loading by:
- using lighter `session.load(...)` options when possible
- caching processed plot inputs, not only FastF1 initialization
- avoiding full telemetry loading for charts that do not need it

### Improve UI and UX

Add:
- clear chart descriptions
- disabled analysis options when unsupported
- loading feedback per analysis
- export buttons for PNG and CSV
- empty-state and error-state messages with guidance

### Add More Plot Types Later

After the first 3, consider adding:
- gear shifts on track
- corner-annotated speed trace
- season summary heatmap
- championship standings view
- weather and track evolution view
- lap delta trends over a stint

## Suggested Build Order

1. Tyre strategy
2. Team pace comparison
3. Qualifying overview
4. Modernize styling with FastF1 plotting helpers
5. Add stronger validation and safer data handling
6. Improve caching and load performance
7. Add export features and better UX
