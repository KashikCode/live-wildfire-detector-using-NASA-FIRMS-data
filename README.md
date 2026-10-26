# TerraSignal · NASA FIRMS Wildfire Observation Monitor

**Source repository:** [KashikCode/live-wildfire-detector-using-NASA-FIRMS-data](https://github.com/KashikCode/live-wildfire-detector-using-NASA-FIRMS-data)

A responsive interactive map of **NASA FIRMS VIIRS near-real-time thermal observations**, designed for GitHub Pages. The browser never receives your NASA MAP_KEY. A scheduled GitHub Actions job fetches and publishes a JSON snapshot from NOAA-20 and NOAA-21 when a private repository secret is configured.

## Important status distinction

The committed `site/data/observations.json` intentionally contains **synthetic demonstration data**, prominently labeled as such in the dashboard. This is **not a live feed until the repository secret is configured and a successful scheduled/manual deployment completes**. Do not present demo coordinates as real fires. NASA observes *thermal anomalies*, which are not synonymous with confirmed wildfire incidents.

## Start a local demonstration

```bash
python -m http.server 8000 --directory site
```

Visit http://localhost:8000. The controls, map, chart, observation activity log, and CSV export work immediately using unmistakably labeled **synthetic observations**. Internet access is required for map tiles and Leaflet CDN assets.

## Publish as a public, updating GitHub Pages site

1. Open **Settings → Pages** in this GitHub repository. In **Build and deployment**, choose **Source: GitHub Actions**. This is a one-time repository setting; committing files alone does not enable GitHub Pages.
2. Get a free private [NASA FIRMS MAP_KEY](https://firms.modaps.eosdis.nasa.gov/api/map_key).
3. In the repository, open **Settings → Secrets and variables → Actions → New repository secret**. Set **Name: `FIRMS_MAP_KEY`** and **Secret: your personal key**. **Never include the key in source code, screenshots, or commits.**
4. Open **Actions → Build and publish TerraSignal → Run workflow** to initiate the first fresh-data deployment. The workflow also runs every three hours (GitHub cron scheduling can be delayed).
5. When the `deploy` job succeeds and GitHub Pages is enabled, the normal project URL is:
   `https://kashikcode.github.io/live-wildfire-detector-using-NASA-FIRMS-data/`
   Verify this link after deployment; it is not guaranteed to exist before the Pages configuration and workflow succeed.

**GitHub Actions does not expose the API key to JavaScript.** The key is used server-side in `scripts/fetch_firms.py`; only sanitized observation attributes are copied to the publicly served JSON. If the key is absent, the demo remains in place. If NASA fails when a key is configured, the build fails rather than silently publishing fake observations as live.

## Data engineering

- Coverage: **contiguous United States rectangular bounding box** `-125,24,-66,50` (not exact state boundaries).
- Sources: `VIIRS_NOAA20_NRT`, `VIIRS_NOAA21_NRT`.
- NASA FIRMS Area API: maximum five days per request. The script requests **five recent days plus the preceding two days**, for each sensor, deduplicates by sensor/time/location, then publishes a seven-day observation snapshot.
- The status timestamp tells you when the dataset was generated. This is **near-real-time**, not continuous real-time tracking. Delays depend on satellite coverage, processing and GitHub Actions scheduling.
- Browser filters by region bounding box, rolling time window, satellite, categorical confidence (`l`, `n`, `h`) and FRP threshold. The map displays up to 5,000 point symbols for performance; metrics and downloads use all filtered observations.
- Observation counts represent *satellite pixels*, not confirmed separate fires. `frp` is fire radiative power in megawatts, not a hazard ranking. Confidence categories are not calibrated probabilities.

## Tests

```bash
python -m unittest discover -s tests -v
```

Tests mock the NASA API; they confirm date parsing, input validation and multi-window deduplication. A **live** end-to-end feed test requires a valid NASA key and network access.

## Scientific limits and precision-recall analysis

For real-time wildfire detection, classical errors carried asymmetric costs: false negatives risk missing fires, while false positives generate unnecessary alerts. Class imbalance and precision-recall tradeoffs can matter more than aggregate accuracy. However, **this website does not estimate precision, recall or false-negative rates**. Evaluating those requires independently labeled ground truth, including unreported events missed by FIRMS. NASA, not this website, runs the actual upstream detection models.

This is an independent educational visualization and is **not intended for emergency decisions**.

### Authoritative sources

- [NASA FIRMS Area API](https://firms.modaps.eosdis.nasa.gov/api/area)
- [NASA FIRMS overview](https://firms.modaps.eosdis.nasa.gov/)
- [GitHub Pages publishing with Actions](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
