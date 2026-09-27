from beta_readiness import build_preflight, executive_summary


def _rows():
    return [
        {"customer_id":"workspace_a","timestamp":"2026-09-27T00:10:00Z","timestamp_epoch":1790467800,"quantity":10.0,"metric":"api"},
        {"customer_id":"workspace_b","timestamp":"2026-09-27T00:20:00Z","timestamp_epoch":1790468400,"quantity":4.0,"metric":"api"},
    ]


def test_preflight_ready_with_mapping():
    p = build_preflight(_rows(), identity_map={"workspace_a":"cus_a","workspace_b":"cus_b"})
    assert p["readiness"] == "READY"
    assert p["stripe_customers_ready"] == 2
    assert p["identity_mapping"]["unmapped_internal_customers"] == 0
    assert p["recommended"]["metric"] == "api"


def test_preflight_reports_unmapped_but_keeps_ready_subset():
    p = build_preflight(_rows(), identity_map={"workspace_a":"cus_a"})
    assert p["readiness"] == "READY"
    assert p["stripe_customers_ready"] == 1
    assert p["identity_mapping"]["unmapped_internal_customers"] == 1
    assert p["warnings"]


def test_preflight_blocks_when_no_customer_can_map():
    p = build_preflight(_rows(), identity_map=None)
    assert p["readiness"] == "BLOCKED"
    assert p["stripe_customers_ready"] == 0
    assert p["blockers"]


def test_executive_summary_is_conservative_and_actionable():
    report = {
        "summary": {"period_exposure_eur": 3.5, "potential_underbilling_eur": 2.0, "potential_overbilling_eur": 1.5,
                    "customers_with_findings": 2, "customers_scanned": 3, "customers_failed": 1},
        "customers": [
            {"customer_id":"cus_a","period_exposure_eur":2.0},
            {"customer_id":"cus_b","period_exposure_eur":1.5},
            {"customer_id":"cus_c","period_exposure_eur":0.0},
        ],
    }
    e = executive_summary(report)
    assert "€3.50" in e["headline"]
    assert len(e["top_customers"]) == 2
    assert "not a booked financial loss" in e["scope_note"]
    assert len(e["recommended_actions"]) == 3
