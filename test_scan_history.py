import os
import tempfile
import unittest

import scan_history


class ScanHistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["METERTRUTH_DB_PATH"] = os.path.join(self.tmp.name, "scans.sqlite3")

    def tearDown(self):
        os.environ.pop("METERTRUTH_DB_PATH", None)
        self.tmp.cleanup()

    def test_saves_report_and_sanitizes_names_without_raw_uploads(self):
        report = {
            "created_at": "2026-09-27T10:00:00+00:00",
            "summary": {"findings": 1, "potential_underbilling_eur": 2.5, "potential_overbilling_eur": 0.0},
            "findings": [{"type": "MISSING", "event_id": "e1"}],
        }
        scan_id = scan_history.save(report, "../../raw.csv", "metered.json")
        saved = scan_history.get_scan(scan_id)
        rows = scan_history.list_scans()
        self.assertEqual(saved, report)
        self.assertEqual(rows[0]["source_name"], "raw.csv")
        self.assertEqual(rows[0]["metered_name"], "metered.json")
        self.assertEqual(rows[0]["underbilling"], 2.5)
        self.assertNotIn("raw_text", rows[0])

    def test_unknown_scan_returns_none(self):
        self.assertIsNone(scan_history.get_scan(999))


if __name__ == "__main__":
    unittest.main()
