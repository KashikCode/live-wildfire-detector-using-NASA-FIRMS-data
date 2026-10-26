import pandas as pd
from core import normalize_firms


def test_normalizes_firms_time_and_coordinates():
    raw = pd.DataFrame({
        "latitude": [30.0, 91.0], "longitude": [-97.0, -98.0],
        "acq_date": ["2026-10-26", "2026-10-26"],
        "acq_time": [631, 1230], "confidence": ["n", "h"],
        "frp": [15, 20], "bright_ti4": [330, 340],
    })
    result = normalize_firms(raw)
    assert len(result) == 1
    assert result.iloc[0]["observed_utc"].strftime("%H:%M") == "06:31"
    assert result.iloc[0]["frp"] == 15


def test_rejects_missing_columns():
    try:
        normalize_firms(pd.DataFrame({"latitude": [30]}))
    except ValueError as e:
        assert "missing" in str(e).lower()
    else:
        raise AssertionError("Expected ValueError")


def test_seven_days_uses_two_nonoverlapping_requests(monkeypatch):
    from datetime import date
    from core import fetch_firms

    seen = []
    class Response:
        text = 'latitude,longitude,acq_date,acq_time,confidence,frp\n30,-97,2026-10-26,631,n,15\n'
        def raise_for_status(self):
            pass
    def mock_get(url, timeout):
        seen.append(url)
        return Response()
    monkeypatch.setattr('core.requests.get', mock_get)
    result = fetch_firms('FAKEKEY', 'VIIRS_NOAA21_NRT', '-107,25,-93,37', 7, today=date(2026, 10, 26))
    assert len(seen) == 2
    assert seen[0].endswith('/5/2026-10-20')
    assert seen[1].endswith('/2/2026-10-25')
    assert len(result) == 1  # identical mocked records are deduplicated
