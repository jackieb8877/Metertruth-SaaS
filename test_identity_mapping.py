import pytest
from identity_mapping import parse_identity_mapping_rows, apply_identity_mapping


def test_parse_mapping_and_aliases():
    rows = [
        {"workspace_id":"ws_1", "stripe_id":"cus_a"},
        {"workspace_id":"ws_2", "stripe_id":"cus_b"},
    ]
    assert parse_identity_mapping_rows(rows) == {"ws_1":"cus_a", "ws_2":"cus_b"}


def test_conflicting_mapping_rejected():
    rows = [
        {"internal_customer_id":"acct_1", "stripe_customer_id":"cus_a"},
        {"internal_customer_id":"acct_1", "stripe_customer_id":"cus_b"},
    ]
    with pytest.raises(ValueError, match="Conflicting mapping"):
        parse_identity_mapping_rows(rows)


def test_many_internal_to_one_stripe_rejected():
    rows = [
        {"internal_customer_id":"acct_1", "stripe_customer_id":"cus_a"},
        {"internal_customer_id":"acct_2", "stripe_customer_id":"cus_a"},
    ]
    with pytest.raises(ValueError, match="multiple internal customers"):
        parse_identity_mapping_rows(rows)


def test_apply_mapping_reports_unmapped_and_passthrough():
    raw = [
        {"customer_id":"acct_1", "quantity":1},
        {"customer_id":"acct_missing", "quantity":2},
        {"customer_id":"cus_direct", "quantity":3},
    ]
    mapped, meta = apply_identity_mapping(raw, {"acct_1":"cus_a"})
    assert [r["customer_id"] for r in mapped] == ["cus_a", "cus_direct"]
    assert mapped[0]["source_customer_id"] == "acct_1"
    assert meta["mapped_internal_customers"] == 1
    assert meta["passthrough_stripe_customers"] == 1
    assert meta["unmapped_ids"] == ["acct_missing"]


def test_apply_mapping_strict_rejects_unmapped():
    with pytest.raises(ValueError, match="Unmapped internal customer IDs"):
        apply_identity_mapping([{"customer_id":"acct_1"}], {}, strict=True)
