# What To Add

## Done

Completed already:

1. Tyre strategy view
2. Team pace comparison
3. Qualifying overview
4. Gear shifts on track
5. Corner-annotated speed trace
6. Weather and track evolution
7. Session summary header
8. Export buttons for PNG and CSV

These were the first priority additions and are now implemented in the dashboard.

## Next 5 Tasks

Recommended next build order:

1. Modernize styling with FastF1 plotting helpers
2. Add stronger validation and safer data handling
3. Improve caching and load performance
4. Add disabled unsupported analyses in the UI
5. Add per-analysis help text and guidance

This order keeps the app focused on high-value analysis first, then improves usability and presentation.

## Recommended Enhancements

### 1. Gear Shifts On Track

Add a track map showing gear usage through the lap:
- fastest lap for a selected driver
- color-coded gear changes around the circuit
- useful for understanding cornering and traction zones

Why:
- gives a true telemetry-style track analysis that is visually strong
- one of the most recognizable and useful FastF1-style visualizations

### 2. Corner-Annotated Speed Trace

Add a speed trace with corner markers:
- fastest-lap speed profile
- corner labels overlaid or referenced along the distance axis
- optional driver comparison mode later

Why:
- makes the speed comparison much easier to interpret
- helps identify braking and acceleration differences by corner

### 3. Weather And Track Evolution

Add a weather/session conditions analysis:
- air temperature
- track temperature
- rainfall if available
- wind and track evolution over session time

Why:
- adds valuable race weekend context
- explains pace and strategy shifts more clearly

### 4. Session Summary Header

Add a reusable summary block at the top of the page:
- event name
- year
- circuit
- session type
- top result or pole sitter
- conditions if available

Why:
- improves clarity immediately when opening a session
- makes the app feel more complete and polished

### 5. Export Buttons For PNG And CSV

Add download actions for:
- chart image export
- processed chart data export
- selected session data tables where relevant

Why:
- makes the dashboard more useful for sharing and reporting
- increases practical value without changing the stack

## Earlier Recommendations

### Tyre Strategy View

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

### Team Pace Comparison

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

### Qualifying Overview

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

After the next 5, consider adding:
- season summary heatmap
- championship standings view
- lap delta trends over a stint
- driver consistency analysis
- qualifying gap-to-pole distribution

## Suggested Build Order

1. Gear shifts on track
2. Corner-annotated speed trace
3. Weather and track evolution
4. Session summary header
5. Export buttons for PNG and CSV
6. Modernize styling with FastF1 plotting helpers
7. Add stronger validation and safer data handling
8. Improve caching and load performance
