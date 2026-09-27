import pytest

from multi_scan import scan_stripe_customers
from stripe_client import StripeReadError

RAW = [
    {"customer_id":"cus_a","timestamp":"2026-09-27T00:05:00Z","timestamp_epoch":1790467500,"quantity":10,"metric":"api"},
    {"customer_id":"cus_b","timestamp":"2026-09-27T00:06:00Z","timestamp_epoch":1790467560,"quantity":4,"metric":"api"},
    {"customer_id":"cus_c","timestamp":"2026-09-27T00:07:00Z","timestamp_epoch":1790467620,"quantity":8,"metric":"api"},
    {"customer_id":"internal_1","timestamp":"2026-09-27T00:08:00Z","timestamp_epoch":1790467680,"quantity":99,"metric":"api"},
    {"customer_id":"cus_a","timestamp":"2026-09-27T02:00:00Z","timestamp_epoch":1790474400,"quantity":99,"metric":"api"},
]

class FakeClient:
    def list_meter_event_summaries(self, **kwargs):
        customer = kwargs["customer_id"]
        if customer == "cus_c":
            raise StripeReadError("temporary Stripe failure")
        actual = {"cus_a": 7, "cus_b": 4}[customer]
        return [{
            "id": "sum_" + customer,
            "meter": kwargs["meter_id"],
            "customer_id": customer,
            "start_time": 1790467200,
            "end_time": 1790470800,
            "aggregated_value": actual,
        }]

def test_multi_customer_rollup_and_partial_failure():
    report = scan_stripe_customers(
        RAW, client=FakeClient(), meter_id="mtr_1", metric="api",
        start_time=1790467200, end_time=1790470800, grouping="hour",
        unit_price=0.10,
    )
    s = report["summary"]
    assert s["customers_discovered"] == 3
    assert s["customers_scanned"] == 2
    assert s["customers_failed"] == 1
    assert s["customers_with_findings"] == 1
    assert s["period_exposure_eur"] == 0.30
    assert report["customers"][0]["customer_id"] == "cus_a"
    assert report["customers"][0]["status"] == "LEAKAGE"
    assert report["customers"][1]["status"] == "CLEAN"
    assert report["errors"][0]["customer_id"] == "cus_c"


def test_customer_limit_is_enforced():
    rows = [{"customer_id":f"cus_{i}","timestamp":"2026-09-27T00:00:00Z","timestamp_epoch":1790467200,"quantity":1,"metric":"api"} for i in range(3)]
    with pytest.raises(ValueError, match="MVP limit"):
        scan_stripe_customers(rows, client=FakeClient(), meter_id="mtr_1", metric="api", start_time=1790467200, end_time=1790470800, max_customers=2)


def test_requires_stripe_customer_ids():
    rows = [{"customer_id":"acct_1","timestamp":"2026-09-27T00:00:00Z","timestamp_epoch":1790467200,"quantity":1,"metric":"api"}]
    with pytest.raises(ValueError, match="cus_\\*"):
        scan_stripe_customers(rows, client=FakeClient(), meter_id="mtr_1", metric="api", start_time=1790467200, end_time=1790470800)


def test_decimal_customer_rollup_is_cent_exact():
    rows = [
        {"customer_id":f"cus_{letter}","timestamp":"2026-09-27T00:05:00Z",
         "timestamp_epoch":1790467500,"quantity":"1","metric":"api"}
        for letter in "abc"
    ]

    class EmptyStripe:
        def list_meter_event_summaries(self, **kwargs):
            return []

    report = scan_stripe_customers(
        rows, client=EmptyStripe(), meter_id="mtr_1", metric="api",
        start_time=1790467200, end_time=1790470800, unit_price="0.005",
    )
    assert report["summary"]["potential_underbilling_eur"] == 0.03
    assert report["summary"]["period_exposure_eur"] == 0.03
