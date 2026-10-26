"""Run with: streamlit run app.py"""
import os
from datetime import datetime, timedelta, timezone
from html import escape

import folium
from folium.plugins import HeatMapWithTime
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from core import fetch_firms, SOURCES

st.set_page_config(page_title="Wildfire Observations", page_icon="🌎", layout="wide")

REGIONS = {
    "Texas and surrounding area (bounding box)": ("-107,25,-93,37", [31, -100], 6),
    "California and surrounding area (bounding box)": ("-125,32,-113,43", [37, -119], 6),
    "Western US (bounding box)": ("-125,31,-102,49", [40, -114], 5),
    "Contiguous US (bounding box)": ("-125,24,-66,50", [39, -98], 4),
    "India and surrounding area (bounding box)": ("68,6,98,37", [22, 79], 5),
}
CONFIDENCE = {"Low": "l", "Nominal": "n", "High": "h"}
CONF_COLORS = {"l": "#fbbf24", "n": "#2563eb", "h": "#dc2626"}


def get_map_key():
    from_env = os.environ.get("FIRMS_MAP_KEY", "").strip()
    if from_env:
        return from_env
    try:
        return str(st.secrets.get("FIRMS_MAP_KEY", "")).strip()
    except (FileNotFoundError, KeyError):
        return ""


@st.cache_data(ttl=900, show_spinner="Fetching satellite observations from NASA...")
def cached_fetch(key, source, bbox, days, current_date):
    return fetch_firms(key, source, bbox, days, today=current_date)


def make_map(df, center, zoom, coloring, animated, days, utc_today):
    m = folium.Map(location=center, zoom_start=zoom, tiles="CartoDB positron", control_scale=True)
    if df.empty:
        return m

    if animated:
        # This is an animation of detection density, not fire spread or perimeter.
        dates = [(utc_today - timedelta(days=i)) for i in reversed(range(days))]
        max_frp = max(1.0, float(df["frp"].quantile(0.95)))
        frames = []
        for day in dates:
            segment = df.loc[df["observed_utc"].dt.date == day]
            frames.append([
                [float(r.latitude), float(r.longitude),
                 min(1.0, max(0.1, float(r.frp) / max_frp)) if pd.notna(r.frp) else 0.1]
                for r in segment.itertuples(index=False)
            ])
        HeatMapWithTime(
            data=frames,
            index=[d.isoformat() + " UTC" for d in dates],
            radius=12, min_opacity=0.1, max_opacity=0.75, auto_play=False,
            name="Daily hotspot density",
        ).add_to(m)
    else:
        if coloring == "Confidence":
            color_for = lambda row: CONF_COLORS.get(row.confidence, "#6b7280")
        else:
            # Fixed FRP color bands are visual encodings, NOT danger categories.
            color_for = lambda row: ("#b91c1c" if pd.notna(row.frp) and row.frp >= 100
                                     else "#ea580c" if pd.notna(row.frp) and row.frp >= 20
                                     else "#0284c7")
        for r in df.itertuples(index=False):
            frp_text = "unavailable" if pd.isna(r.frp) else f"{r.frp:.1f} MW"
            obs = r.observed_utc.strftime("%Y-%m-%d %H:%M UTC")
            conf_text = {"l": "low", "n": "nominal", "h": "high"}.get(r.confidence, str(r.confidence))
            popup = folium.Popup(
                f"<b>Satellite thermal anomaly</b><br>"
                f"Observed: {escape(obs)}<br>"
                f"FRP: {escape(frp_text)}<br>"
                f"Confidence category: {escape(conf_text)}<br>"
                f"Coordinates: {r.latitude:.4f}, {r.longitude:.4f}",
                max_width=320,
            )
            folium.CircleMarker(
                [float(r.latitude), float(r.longitude)],
                radius=4, weight=1, fill=True, fill_opacity=0.75,
                color=color_for(r), fill_color=color_for(r),
                popup=popup,
            ).add_to(m)
    return m


st.title("Satellite Wildfire Observations")
st.caption("NASA FIRMS / VIIRS | Near-real-time thermal detections. Not a public safety alert system.")

map_key = get_map_key()
if not map_key:
    st.error("FIRMS API key missing. Set FIRMS_MAP_KEY in your environment or Streamlit secrets.")
    st.stop()

with st.sidebar:
    st.header("Observation filters")
    region = st.selectbox("Area", list(REGIONS))
    bbox, center, zoom = REGIONS[region]
    source = st.selectbox("Sensor", SOURCES, index=0)
    days = st.slider("UTC calendar days", min_value=1, max_value=7, value=3)
    confidence_labels = st.multiselect("NASA confidence categories", list(CONFIDENCE),
                                      default=list(CONFIDENCE))
    min_frp = st.number_input("Minimum radiative power (MW)", min_value=0.0,
                              value=0.0, step=5.0)
    coloring = st.radio("Marker color", ["Confidence", "Fire radiative power (FRP)"])
    animated = st.checkbox("Animate daily hotspot density", value=False)
    if st.button("Refresh NASA feed", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

utc_today = datetime.now(timezone.utc).date()
try:
    raw = cached_fetch(map_key, source, bbox, days, utc_today)
except (RuntimeError, ValueError) as exc:
    st.error(str(exc))
    st.stop()

filtered = raw.copy()
selected_codes = {CONFIDENCE[label] for label in confidence_labels}
filtered = filtered[filtered["confidence"].isin(selected_codes)]
if min_frp > 0:
    filtered = filtered[filtered["frp"] >= min_frp]

col1, col2, col3 = st.columns(3)
col1.metric("Satellite detections in feed", f"{len(raw):,}")
col2.metric("Detections passing filters", f"{len(filtered):,}")
col3.metric("Dates covered", f"{days}")

if len(filtered) > 8000 and not animated:
    st.warning("Many individual markers may make the browser slow. Narrow the area or dates.")
if filtered.empty:
    st.info("No matching detections were returned for these settings.")
else:
    if animated:
        st.info("Animation shows daily detection density, not the movement or boundaries of a wildfire.")
    else:
        st.caption("Confidence: yellow = low, blue = nominal, red = high. "
                   "For FRP mode: blue <20 MW, orange 20–99.9 MW, red ≥100 MW. "
                   "These are display bands, not validated risk levels.")
    m = make_map(filtered, center, zoom, coloring, animated, days, utc_today)
    st_folium(m, height=600, width=1100, returned_objects=[], key="firemap")
    chart = filtered.groupby(filtered["observed_utc"].dt.date).size().rename("Detections")
    st.subheader("Observations by date (UTC)")
    st.bar_chart(chart)

st.download_button("Download filtered records (CSV)", data=filtered.to_csv(index=False).encode(),
                   file_name="firms_observations.csv", mime="text/csv", disabled=filtered.empty)
st.caption("Each point is a detected thermal anomaly, not necessarily a unique or confirmed wildfire. "
           "Clouds, satellite overpass timing, vegetation cover, and other factors can cause missed detections. "
           "Data refresh on button press or when Streamlit's 15-minute cache expires on a subsequent interaction.")
st.markdown("Data: [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/). "
            "Do not use this educational dashboard for emergency decisions.")
