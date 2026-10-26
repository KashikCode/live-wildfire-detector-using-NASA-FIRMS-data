# NASA FIRMS Wildfire Observation Dashboard

A learning project written in Python with **pandas, requests, folium, Streamlit, and NASA FIRMS**.

## What it does
- Retrieves VIIRS NOAA-21 or NOAA-20 near-real-time thermal detections from NASA FIRMS.
- Uses the FIRMS Area API to obtain up to seven days (two requests are needed for days 1–7).
- Validates coordinates, parses acquisition times as UTC, and removes identical duplicate rows.
- Maps each filtered thermal observation, with a popup, and allows filtering by NASA's confidence categories and fire radiative power (FRP).
- Creates an optional animated daily **heat map of detection density**, not a simulation of fire propagation.
- Exports filtered observations as a CSV, with a daily count chart.
- Has a **separate** evaluation script for when you have independent ground-truth wildfire labels and model prediction scores.

## Setup

1. Install Python 3.11+.
2. Create a free [NASA FIRMS MAP_KEY](https://firms.modaps.eosdis.nasa.gov/api/map_key).
3. In this directory, run:

```bash
python -m venv .venv
# On macOS/Linux:
source .venv/bin/activate
# On Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

4. Supply your API key as an environment variable (macOS/Linux):

```bash
export FIRMS_MAP_KEY="YOUR_PRIVATE_MAP_KEY"
streamlit run app.py
```

On Windows PowerShell:

```powershell
$env:FIRMS_MAP_KEY="YOUR_PRIVATE_MAP_KEY"
streamlit run app.py
```

Or copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`, edit the value, and ensure this file never gets committed to GitHub.

## Publish on GitHub / Streamlit Community Cloud

- Push all code files to a new GitHub repository, excluding `.streamlit/secrets.toml`.
- Deploy `app.py` through Streamlit Community Cloud.
- Add `FIRMS_MAP_KEY` in the deployed app's **Secrets** settings, not the public repository.
- Do not expect GitHub Pages to run a Python/Streamlit backend. GitHub can host the source, but a Python hosting service is needed for the live dashboard.

## Research question and error asymmetry

> For real-time wildfire detection, classical errors carried asymmetric costs: false negatives risked missing fires, while false positives generated unnecessary alerts. I realized that class imbalance and precision-recall tradeoff mattered beyond aggregate accuracy.

This sentence describes **motivation**, not a completed evaluation. NASA, not this dashboard, runs the upstream detection algorithm. This project does not establish actual error rates or create an alerting system. When you obtain external ground-truth labels, run:

```bash
python evaluate_alerts.py your_independently_labeled_predictions.csv --threshold 0.4
```

The file needs `y_true` (0/1 independent verified outcome) and `y_score` (0–1 probability from your own calibrated detector). To calculate **false negatives**, your evaluation population must include true fire events that the detector missed. You cannot determine them from FIRMS positive detections alone.

Do not substitute FIRMS's `l` / `n` / `h` confidence categories or FRP as though they are calibrated wildfire probabilities. For proper evaluation, split training and evaluation by time and geography, avoid spatial duplicates/leakage, and inspect subgroup performance.

## Safety and data limitations

- This is **not** a tool for emergency response or official wildfire alerts.
- FIRMS thermal anomalies are not all wildfires. Signals may arise from other hot sources, and clouds, canopy, overpass timing, and detection thresholds may prevent observations of real fires.
- Multiple observations may correspond to one wildfire; counts measure observed pixels, not numbers of fires.
- Selection regions are **rectangular bounding boxes** (not exact administrative boundaries).
- "Near real-time" is satellite-dependent, not continuous monitoring. The Streamlit cache is 15 minutes and refreshes on user interaction.
- Map data require an internet connection, and FIRMS API requests require a valid private key.

NASA primary sources:
- [FIRMS Area API](https://firms.modaps.eosdis.nasa.gov/api/area)
- [VIIRS data attributes and limits](https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_VIIRS_Firehotspots.html)
