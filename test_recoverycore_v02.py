import unittest
from copy import deepcopy
from recoverycore_v02 import DEFAULT_CONFIG, price_for_quantity, reconcile, round_money


def row(event_id, customer, ts, qty, metric="api", **extra):
    d = {"event_id": event_id, "customer_id": customer, "timestamp": ts, "quantity": str(qty), "metric": metric}
    d.update(extra)
    return d


class RecoveryCoreV02Tests(unittest.TestCase):
    def cfg(self, **updates):
        c = deepcopy(DEFAULT_CONFIG)
        c.update(updates)
        return c

    def test_clean_match(self):
        r = [row("e1", "c1", "2026-09-01T00:00:00Z", 10)]
        m = [row("e1", "c1", "2026-09-01T00:01:00Z", 10)]
        out = reconcile(r, m, self.cfg())
        self.assertEqual(out["summary"]["findings"], 0)

    def test_missing(self):
        r = [row("e1", "c1", "2026-09-01T00:00:00Z", 10), row("e2", "c2", "2026-09-01T00:00:00Z", 1)]
        m = [row("e2", "c2", "2026-09-01T00:00:01Z", 1)]
        out = reconcile(r, m, self.cfg(price_per_unit=2))
        f = [x for x in out["findings"] if x["type"] == "MISSING"]
        self.assertEqual(f[0]["impact_eur"], 20)

    def test_canonical_machine_codes_preserve_legacy_types(self):
        raw = [
            row("e1", "c1", "2026-09-01T00:00:00Z", 10),
            row("e2", "c1", "2026-09-01T00:00:00Z", 2),
            row("e3", "c1", "2026-09-01T00:00:00Z", 1),
        ]
        metered = [
            row("e1", "c1", "2026-09-01T00:01:00Z", 6),
            row("e1", "c1", "2026-09-01T00:02:00Z", 4),
            row("e3", "c1", "2026-09-02T01:00:00Z", 1),
            row("orphan", "c1", "2026-09-01T00:00:00Z", 3),
        ]
        out = reconcile(raw, metered, self.cfg(late_hours=24))
        codes_by_type = {}
        for item in out["findings"]:
            codes_by_type[item["type"]] = item["code"]

        self.assertEqual(codes_by_type["MISSING"], "MISSING_USAGE")
        self.assertEqual(codes_by_type["DUPLICATE"], "DUPLICATE_USAGE")
        self.assertEqual(codes_by_type["ORPHAN_METERED"], "ORPHAN_METERED_EVENT")
        self.assertEqual(codes_by_type["LATE_EVENT"], "LATE_EVENT")

    def test_decimal_quantity_sum_avoids_false_mismatch(self):
        raw = [row("e1", "c1", "2026-09-01T00:00:00Z", "0.3")]
        metered = [
            row("e1", "c1", "2026-09-01T00:00:01Z", "0.1"),
            row("e1", "c1", "2026-09-01T00:00:02Z", "0.2"),
        ]
        out = reconcile(raw, metered, self.cfg())
        self.assertTrue(any(x["type"] == "DUPLICATE" for x in out["findings"]))
        self.assertFalse(any(x["type"] == "WRONG_QUANTITY" for x in out["findings"]))

    def test_financial_rounding_is_decimal_half_up(self):
        self.assertEqual(round_money("0.125"), 0.13)
        self.assertEqual(round_money("-0.125"), -0.13)
        raw = [row("e1", "c1", "2026-09-01T00:00:00Z", 1)]
        out = reconcile(raw, [row("other", "c1", "2026-09-01T00:00:01Z", 1)],
                        self.cfg(price_per_unit="0.125"))
        missing = next(x for x in out["findings"] if x["type"] == "MISSING")
        self.assertEqual(missing["impact_eur"], 0.13)
        self.assertEqual(out["summary"]["potential_underbilling_eur"], 0.13)

    def test_tiered_decimal_arithmetic_at_boundary(self):
        cfg = self.cfg(pricing={"api": {"tiers": [
            {"up_to": "0.3", "unit_price": "0.10"},
            {"up_to": None, "unit_price": "0.20"},
        ]}})
        self.assertEqual(price_for_quantity("api", "0.4", cfg), 0.05)

    def test_duplicate_does_not_double_count_quantity(self):
        r = [row("e1", "c1", "2026-09-01T00:00:00Z", 10)]
        m = [row("e1", "c1", "2026-09-01T00:01:00Z", 10), row("e1", "c1", "2026-09-01T00:02:00Z", 10)]
        out = reconcile(r, m, self.cfg(price_per_unit=1))
        economic = [x for x in out["findings"] if x["type"] in {"DUPLICATE", "WRONG_QUANTITY"}]
        self.assertEqual(len(economic), 1)
        self.assertEqual(economic[0]["impact_eur"], -10)
        self.assertEqual(out["summary"]["potential_overbilling_eur"], 10)

    def test_duplicate_with_net_underbilling(self):
        r = [row("e1", "c1", "2026-09-01T00:00:00Z", 10)]
        m = [row("e1", "c1", "2026-09-01T00:01:00Z", 2), row("e1", "c1", "2026-09-01T00:02:00Z", 3)]
        out = reconcile(r, m, self.cfg(price_per_unit=1))
        f = [x for x in out["findings"] if x["type"] == "DUPLICATE"][0]
        self.assertEqual(f["impact_eur"], 5)

    def test_metric_and_customer_mismatch(self):
        r = [row("e1", "c1", "2026-09-01T00:00:00Z", 10, "api")]
        m = [row("e1", "c2", "2026-09-01T00:01:00Z", 10, "tokens")]
        out = reconcile(r, m, self.cfg())
        kinds = {x["type"] for x in out["findings"]}
        self.assertIn("CUSTOMER_MISMATCH", kinds)
        self.assertIn("METRIC_MISMATCH", kinds)

    def test_late_and_period(self):
        r = [row("e1", "c1", "2026-09-30T23:00:00Z", 1)]
        m = [row("e1", "c1", "2026-10-02T01:00:00Z", 1)]
        cfg = self.cfg(late_hours=24, billing_period={"start":"2026-09-01T00:00:00Z","end":"2026-10-01T00:00:00Z"})
        out = reconcile(r, m, cfg)
        kinds = [x["type"] for x in out["findings"]]
        self.assertIn("LATE_EVENT", kinds)
        self.assertIn("OUT_OF_PERIOD", kinds)

    def test_malformed_is_unverifiable(self):
        r = [row("e1", "c1", "not-a-date", 10), row("e2", "c2", "2026-09-01T00:00:00Z", 1)]
        m = [row("e1", "c1", "2026-09-01T00:00:00Z", 10), row("e2", "c2", "2026-09-01T00:00:00Z", 1)]
        out = reconcile(r, m, self.cfg())
        f = [x for x in out["findings"] if x["event_id"] == "e1"][0]
        self.assertEqual(f["status"], "UNVERIFIABLE")
        self.assertEqual(f["impact_eur"], 0)

    def test_orphan(self):
        r = [row("e1", "c1", "2026-09-01T00:00:00Z", 1)]
        m = [row("e1", "c1", "2026-09-01T00:00:00Z", 1), row("eX", "c9", "2026-09-01T00:00:00Z", 4)]
        out = reconcile(r, m, self.cfg(price_per_unit=2))
        f = [x for x in out["findings"] if x["type"] == "ORPHAN_METERED"][0]
        self.assertEqual(f["impact_eur"], -8)

    def test_tiered_pricing(self):
        cfg = self.cfg(pricing={"api": {"tiers": [{"up_to":100,"unit_price":1.0},{"up_to":None,"unit_price":0.5}]}})
        self.assertEqual(price_for_quantity("api", 150, cfg), 125)
        r = [row("e1", "c1", "2026-09-01T00:00:00Z", 150)]
        m = [row("e1", "c1", "2026-09-01T00:00:00Z", 100)]
        out = reconcile(r, m, cfg)
        f = [x for x in out["findings"] if x["type"] == "WRONG_QUANTITY"][0]
        self.assertEqual(f["impact_eur"], 25)

    def test_quantity_tolerance(self):
        r = [row("e1", "c1", "2026-09-01T00:00:00Z", 10)]
        m = [row("e1", "c1", "2026-09-01T00:00:00Z", 10.05)]
        out = reconcile(r, m, self.cfg(quantity_tolerance=0.1))
        self.assertFalse(any(x["type"] == "WRONG_QUANTITY" for x in out["findings"]))

    def test_duplicate_source_id_is_unverifiable(self):
        r = [row("e1", "c1", "2026-09-01T00:00:00Z", 5), row("e1", "c1", "2026-09-01T00:00:01Z", 5)]
        m = [row("e1", "c1", "2026-09-01T00:00:00Z", 5)]
        out = reconcile(r, m, self.cfg())
        self.assertTrue(any(x["status"] == "UNVERIFIABLE" for x in out["findings"]))

    def test_idempotency_collision_is_suspected_no_impact(self):
        r = [row("e1", "c1", "2026-09-01T00:00:00Z", 5), row("e2", "c1", "2026-09-01T00:00:01Z", 5)]
        m = [row("e1", "c1", "2026-09-01T00:00:00Z", 5, idempotency_key="same"),
             row("e2", "c1", "2026-09-01T00:00:01Z", 5, idempotency_key="same")]
        out = reconcile(r, m, self.cfg())
        f = [x for x in out["findings"] if x["type"] == "IDEMPOTENCY_COLLISION"][0]
        self.assertEqual(f["status"], "SUSPECTED")
        self.assertEqual(f["impact_eur"], 0)
        self.assertEqual(out["summary"]["suspected_findings"], 1)


if __name__ == "__main__":
    unittest.main()
