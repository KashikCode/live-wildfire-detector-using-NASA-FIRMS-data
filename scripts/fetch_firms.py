"""Export NASA FIRMS VIIRS NRT observations for a static GitHub Pages site.

NASA's FIRMS Area API accepts 1-5 days per request. We fetch the current
five-day window and the preceding two-day window for each satellite.
Credentials are read only from the FIRMS_MAP_KEY environment variable.
"""

from __future__ import annotations

import csv
import io
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

API_ROOT = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
SOURCES = ("VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT")
BBOX = (-125, 24, -66, 50)  # Continental US bounding box; not a polygon.
OUTPUT = Path(__file__).resolve().parent.parent / "site" / "data" / "observations.json"
FIELDS = ("latitude", "longitude", "acq_date", "acq_time", "frp", "confidence")


def parse_viirs_csv(body: str, source: str) -> list[dict]:
    """Parse a NASA VIIRS CSV, rejecting invalid rows without inventing values."""
    data = csv.DictReader(io.StringIO(body.lstrip("\ufeff")))
    if not data.fieldnames or not set(FIELDS).issubset(set(data.fieldnames)):
        raise ValueError("Unexpected FIRMS CSV schema (or a service error).")
    parsed = []
    for row in data:
        try:
            lat, lon = float(row["latitude"]), float(row["longitude"])
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                continue
            frp = float(row["frp"])
            if frp < 0:
                continue
            clock = str(row["acq_time"]).strip().zfill(4)
            if len(clock) != 4 or not clock.isdigit():
                continue
            observed = datetime.strptime(
                f"{row['acq_date']} {clock}", "%Y-%m-%d %H%M"
            ).replace(tzinfo=timezone.utc)
            conf = str(row["confidence"]).lower().strip()
            if conf not in ("l", "n", "h"):
                continue
            parsed.append({
                "lat": round(lat, 5),
                "lon": round(lon, 5),
                "frp": round(frp, 2),
                "confidence": conf,
                "time": observed.isoformat().replace("+00:00", "Z"),
                "satellite": "NOAA-20" if "NOAA20" in source else "NOAA-21",
                "daynight": row.get("daynight", "").strip().upper() if row.get("daynight") else "",
            })
        except (ValueError, TypeError, KeyError, OverflowError):
            continue
    return parsed


def fetch_csv(key: str, source: str, days: int, start: str | None = None) -> str:
    if source not in SOURCES or not (1 <= days <= 5):
        raise ValueError("Invalid FIRMS request")
    area = ",".join(map(str, BBOX))
    url = f"{API_ROOT}/{key}/{source}/{area}/{days}"
    if start:
        url += f"/{start}"
    request = urllib.request.Request(url, headers={"User-Agent": "TerraSignal/1.0 educational satellite dashboard"})
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return response.read().decode("utf-8-sig")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        # Never print the requested URL: it contains the private MAP_KEY.
        raise RuntimeError(f"NASA FIRMS request failed for {source}; check key and connectivity.") from None


def collect_observations(key: str, today: datetime | None = None) -> dict:
    today = (today or datetime.now(timezone.utc)).astimezone(timezone.utc)
    earlier = (today.date() - timedelta(days=6)).isoformat()
    rows = []
    for source in SOURCES:
        rows.extend(parse_viirs_csv(fetch_csv(key, source, 5), source))
        rows.extend(parse_viirs_csv(fetch_csv(key, source, 2, earlier), source))

    # FIRMS can revise or reissue observations; remove exact repeated points.
    unique = {}
    for row in rows:
        signature = (row["satellite"], row["time"], row["lat"], row["lon"])
        unique[signature] = row
    observations = sorted(unique.values(), key=lambda x: x["time"], reverse=True)
    stamp = today.isoformat(timespec="seconds").replace("+00:00", "Z")
    return {
        "status": "live",
        "generated_at_utc": stamp,
        "coverage": "Contiguous United States bounding box",
        "bbox": list(BBOX),
        "sources": list(SOURCES),
        "count": len(observations),
        "note": "NASA FIRMS VIIRS satellite thermal anomalies, not confirmed wildfire incidents or alerts.",
        "observations": observations,
    }


def main() -> int:
    key = os.getenv("FIRMS_MAP_KEY", "").strip()
    if not key:
        print("FIRMS_MAP_KEY not provided: deploying clearly labeled demonstration data.")
        return 0
    if not key.isalnum() or len(key) < 12:
        print("Invalid map key format; refusing to replace data.", file=sys.stderr)
        return 1
    try:
        payload = collect_observations(key)
    except (RuntimeError, ValueError) as exc:
        # Retain the previous successful deployment if the API fails.
        print(f"NASA feed unavailable: {exc}", file=sys.stderr)
        return 1
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(f"Prepared {payload['count']} observations. Credentials not saved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
