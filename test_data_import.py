import json
import unittest

from data_import import parse_data_bytes


class DataImportTests(unittest.TestCase):
    def test_csv_utf8_bom_and_empty_cell(self):
        rows = parse_data_bytes("\ufeffevent_id,quantity\ne1,\n".encode(), "usage.csv")
        self.assertEqual(rows, [{"event_id": "e1", "quantity": ""}])

    def test_json_array_and_wrapped_events(self):
        payload = json.dumps({"events": [{"event_id": "e1", "quantity": 3}, {"event_id": "e2", "quantity": None}]})
        rows = parse_data_bytes(payload.encode(), "usage.json")
        self.assertEqual(rows, [{"event_id": "e1", "quantity": "3"}, {"event_id": "e2", "quantity": ""}])

    def test_json_single_object(self):
        rows = parse_data_bytes(b'{"event_id":"e1","quantity":3}', "one.json")
        self.assertEqual(rows, [{"event_id": "e1", "quantity": "3"}])

    def test_json_lines_even_when_suffix_csv_is_not_used(self):
        rows = parse_data_bytes(b'{"event_id":"e1"}\n{"event_id":"e2"}\n', "events.jsonl")
        self.assertEqual([row["event_id"] for row in rows], ["e1", "e2"])

    def test_invalid_json_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Invalid JSON"):
            parse_data_bytes(b'{"event_id":', "bad.json")

    def test_non_object_json_rows_rejected(self):
        with self.assertRaisesRegex(ValueError, "JSON must be"):
            parse_data_bytes(b'[1,2,3]', "bad.json")

    def test_oversize_rejected(self):
        with self.assertRaisesRegex(ValueError, "5 MB"):
            parse_data_bytes(b"x" * (5 * 1024 * 1024 + 1), "large.csv")


if __name__ == "__main__":
    unittest.main()
