"""Editorial preview checks, not backend or conversion tests.
Run: python -m unittest discover -s copywriting/pilot-01 -p 'test_*.py' -v
"""
from html.parser import HTMLParser
from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parent
HTML = (ROOT / "index.html").read_text(encoding="utf-8")

class Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.text = []
    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
    def handle_data(self, data):
        self.text.append(data)

class PreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = Elements()
        cls.doc.feed(HTML)
        cls.copy = " ".join(cls.doc.text)
    def test_language_and_viewport(self):
        self.assertIn(("html", {"lang": "en"}), self.doc.tags)
        self.assertTrue(any(t == "meta" and a.get("name") == "viewport" for t,a in self.doc.tags))
    def test_one_main_heading(self):
        self.assertEqual(sum(t == "h1" for t,a in self.doc.tags), 1)
        self.assertEqual(sum(t == "main" for t,a in self.doc.tags), 1)
    def test_all_fragment_links_resolve(self):
        ids = [a["id"] for t,a in self.doc.tags if "id" in a]
        self.assertEqual(len(ids), len(set(ids)))
        for tag, attrs in self.doc.tags:
            href = attrs.get("href", "")
            if tag == "a" and href.startswith("#"):
                self.assertIn(href[1:], ids)
    def test_no_collection_or_scripts(self):
        self.assertFalse(any(t in {"script", "form", "input", "iframe"} for t,a in self.doc.tags))
        self.assertFalse(any(k.startswith("on") for t,a in self.doc.tags for k in a))
        self.assertNotIn("@import", HTML)
        self.assertNotIn("url(", HTML)
    def test_beta_link_explicit(self):
        external = [a["href"] for t,a in self.doc.tags if t == "a" and a.get("href", "").startswith("http")]
        self.assertEqual(external, ["https://metertruth-saa-s.vercel.app/"])
        self.assertIn("Live access was not verified", self.copy)
    def test_synthetic_aggregate_fixture_label(self):
        for text in ["SYNTHETIC DATA", "aggregate differences", "200", "190", "220", "€0.20", "€0.40", "not recovered revenue"]:
            self.assertIn(text, self.copy)
    def test_production_data_and_storage_limits(self):
        for text in ["do not upload production customer data", "server—not your browser", "Evidence can contain sensitive information", "may disappear on restart"]:
            self.assertIn(text, self.copy)
    def test_invoice_checks_not_implied_by_two_files(self):
        self.assertIn("requires additional files", self.copy)
        self.assertIn("does not issue invoices", self.copy)
    def test_accessibility_affordances(self):
        self.assertIn("Skip to content", self.copy)
        self.assertTrue(any(t == "th" and a.get("scope") == "col" for t,a in self.doc.tags))
        self.assertTrue(any(t == "th" and a.get("scope") == "row" for t,a in self.doc.tags))
        self.assertIn("prefers-reduced-motion", HTML)
        self.assertIn(":focus-visible", HTML)
        self.assertEqual(sum(t == "summary" for t,a in self.doc.tags), 4)
    def test_manifest_not_applied(self):
        data = json.loads((ROOT / "copy_changes.json").read_text(encoding="utf-8"))
        self.assertEqual(data["status"], "PROPOSED_NOT_APPLIED")
        self.assertEqual(data["scope"], "home() only")
        self.assertEqual(len(data["expected_blob_sha"]), 40)
        self.assertEqual(len(data["replacements"]), 13)
        self.assertTrue(all(item["before"] != item["after"] for item in data["replacements"]))

if __name__ == "__main__":
    unittest.main()
