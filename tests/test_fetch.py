import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from scripts.fetch_firms import parse_viirs_csv, collect_observations

CSV = ("latitude,longitude,acq_date,acq_time,frp,confidence,daynight\n"
       "33.1,-97.2,2026-10-25,54,15.2,n,D\n"
       "33.1,-97.2,2026-10-25,54,15.2,n,D\n"
       "91,-97.2,2026-10-25,54,9,h,D\n"
       "32,-96,2026-10-25,2300,20,h,N\n")

class FIRMSParserTests(unittest.TestCase):
    def test_parses_and_rejects_invalid_coords(self):
        data = parse_viirs_csv(CSV, "VIIRS_NOAA21_NRT")
        self.assertEqual(len(data), 3)
        self.assertEqual(data[0]["time"], "2026-10-25T00:54:00Z")
        self.assertEqual(data[0]["satellite"], "NOAA-21")

    def test_rejects_error_html(self):
        with self.assertRaises(ValueError):
            parse_viirs_csv("<html>Invalid MAP_KEY</html>", "VIIRS_NOAA20_NRT")

    @patch("scripts.fetch_firms.fetch_csv", return_value=CSV)
    def test_seven_days_two_requests_per_sensor_deduplicated(self, fake_fetch):
        output = collect_observations("valid-placeholder", datetime(2026, 10, 26, tzinfo=timezone.utc))
        self.assertEqual(fake_fetch.call_count, 4)
        self.assertEqual(output["count"], 4)  # two unique coordinates, two satellites
        self.assertEqual(fake_fetch.call_args_list[1].args[-1], "2026-10-20")
        self.assertEqual(output["status"], "live")

if __name__ == "__main__":
    unittest.main()
