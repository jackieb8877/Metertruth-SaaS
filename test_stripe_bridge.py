from stripe_bridge import aggregate_raw_usage, reconcile_stripe_summaries

RAW = [
    {"customer_id":"cus_A","metric":"api","timestamp":"2026-09-27T10:02:00Z","quantity":4},
    {"customer_id":"cus_A","metric":"api","timestamp":"2026-09-27T10:42:00Z","quantity":6},
    {"customer_id":"cus_A","metric":"api","timestamp":"2026-09-27T11:02:00Z","quantity":5},
]

def test_aggregate_hourly():
    a=aggregate_raw_usage(RAW, grouping='hour')
    assert sorted(a.values()) == [5.0,10.0]

def test_stripe_summary_reconcile_under_and_over():
    stripe=[
      {"customer_id":"cus_A","meter":"mtr_api","start_time":1790503200,"aggregated_value":8},
      {"customer_id":"cus_A","meter":"mtr_api","start_time":1790506800,"aggregated_value":7},
    ]
    # Use bucket epochs produced by helper to avoid hardcoding date conversion assumptions.
    agg=aggregate_raw_usage(RAW, grouping='hour')
    starts=sorted(k[2] for k in agg)
    stripe[0]['start_time']=starts[0]
    stripe[1]['start_time']=starts[1]
    r=reconcile_stripe_summaries(RAW,stripe,meter_to_metric={'mtr_api':'api'},grouping='hour',unit_prices={'api':0.10})
    assert r['summary']['findings']==2
    assert r['summary']['potential_underbilling_eur']==0.2
    assert r['summary']['potential_overbilling_eur']==0.2

def test_unknown_meter_rejected():
    try:
        reconcile_stripe_summaries(RAW,[{"customer_id":"cus_A","meter":"unknown","start_time":0,"aggregated_value":1}],meter_to_metric={})
    except ValueError as e:
        assert 'No metric mapping' in str(e)
    else:
        raise AssertionError('expected error')
