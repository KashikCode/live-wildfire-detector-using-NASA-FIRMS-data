"""NASA FIRMS ingestion and cleaning, independent of the web interface."""
from datetime import datetime, timedelta, timezone
from io import StringIO

import pandas as pd
import requests

FIRMS_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
SOURCES = ("VIIRS_NOAA21_NRT", "VIIRS_NOAA20_NRT")
REQUIRED = {"latitude", "longitude", "acq_date", "acq_time", "confidence", "frp"}


def normalize_firms(raw: pd.DataFrame) -> pd.DataFrame:
    """Coerce numeric columns and create UTC observation timestamps."""
    df = raw.copy()
    df.columns = [str(col).strip().lower() for col in df.columns]
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ValueError(f"NASA CSV missing expected columns: {', '.join(sorted(missing))}")

    for name in ("latitude", "longitude", "frp", "bright_ti4"):
        if name in df.columns:
            df[name] = pd.to_numeric(df[name], errors="coerce")

    # FIRMS sends UTC observation times as integers, e.g. 631 = 06:31.
    hhmm = df["acq_time"].astype("string").str.replace(r"\.0$", "", regex=True).str.zfill(4)
    df["observed_utc"] = pd.to_datetime(
        df["acq_date"].astype("string") + hhmm,
        format="%Y-%m-%d%H%M", utc=True, errors="coerce"
    )
    df["confidence"] = df["confidence"].astype("string").str.strip().str.lower()

    df = df.dropna(subset=["latitude", "longitude", "observed_utc"])
    df = df[df["latitude"].between(-90, 90) & df["longitude"].between(-180, 180)]
    # A detection is not a unique fire. This drops exact duplicate rows only.
    df = df.drop_duplicates().sort_values("observed_utc").reset_index(drop=True)
    return df


def fetch_firms(map_key: str, source: str, bbox: str, days: int, today=None) -> pd.DataFrame:
    """Fetch last 1-7 UTC calendar dates in chunks of <=5 days."""
    if source not in SOURCES:
        raise ValueError("Unsupported sensor source")
    if not 1 <= days <= 7:
        raise ValueError("Days must be between 1 and 7")
    if not map_key or '/' in map_key:
        raise ValueError("Set a valid FIRMS_MAP_KEY in your environment or Streamlit secrets")

    today = today or datetime.now(timezone.utc).date()
    start = today - timedelta(days=days - 1)
    results = []
    offset = 0

    while offset < days:
        chunk = min(5, days - offset)
        first_date = (start + timedelta(days=offset)).isoformat()
        # Explicit date makes the 5-day and 2-day requests nonoverlapping.
        url = f"{FIRMS_URL}/{map_key}/{source}/{bbox}/{chunk}/{first_date}"
        try:
            response = requests.get(url, timeout=50)
            response.raise_for_status()
        except requests.RequestException as exc:
            # Avoid including the request URL, which contains the API key.
            raise RuntimeError("NASA FIRMS could not be reached. Check your key and connection.") from None

        if not response.text.strip():
            offset += chunk
            continue
        try:
            block = pd.read_csv(StringIO(response.text))
        except pd.errors.EmptyDataError:
            offset += chunk
            continue
        # Non-CSV error responses can have HTTP 200. Check schema in normalize_firms.
        if not block.empty:
            results.append(normalize_firms(block))
        offset += chunk

    if not results:
        return pd.DataFrame(columns=["latitude", "longitude", "frp", "confidence", "observed_utc"])
    df = pd.concat(results, ignore_index=True).drop_duplicates()
    return df.sort_values("observed_utc").reset_index(drop=True)
