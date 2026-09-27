from pathlib import Path
from fastapi.testclient import TestClient
from app import app, config_from_form, normalize_raw_for_stripe
import re

ROOT=Path(__file__).parent
client=TestClient(app)

def test_home_and_health():
    assert client.get('/').status_code == 200
    assert 'MeterTruth' in client.get('/').text
    assert client.get('/health').json()['status'] == 'ok'

def test_stripe_input_normalization_preserves_decimal_precision():
    rows = normalize_raw_for_stripe([{
        'customer_id':'cus_1','timestamp':'2026-09-27T00:00:00Z',
        'quantity':'0.123456789123456789','metric':'api'
    }])
    assert rows[0]['quantity'] == '0.123456789123456789'
    cfg = config_from_form('0.000000000000000123', '24', '0.000000000000000003', '12',
                           '{"api":{"unit_price":0.000000000000000123}}')
    assert cfg['price_per_unit'] == '0.000000000000000123'
    assert cfg['quantity_tolerance'] == '0.000000000000000003'
    assert cfg['pricing']['api']['unit_price'] == '0.000000000000000123'

def test_demo_analysis_and_export():
    with open(ROOT/'demo_raw.csv','rb') as a, open(ROOT/'demo_metered.csv','rb') as b:
        r=client.post('/analyze',files={'raw_file':('raw.csv',a,'text/csv'),'metered_file':('metered.csv',b,'text/csv')},data={'price_per_unit':'0.01','late_hours':'24','quantity_tolerance':'0','annualization_periods':'12','pricing_json':''})
    assert r.status_code == 200
    assert 'confirmed findings' in r.text
    assert 'Underbilling' in r.text
    assert 'MISSING_USAGE' in r.text
    assert 'DUPLICATE_USAGE' in r.text
    assert 'Export JSON' in r.text

def test_bad_csv_gets_400():
    r=client.post('/analyze',files={'raw_file':('raw.csv',b'hello\n','text/csv'),'metered_file':('metered.csv',b'hello\n','text/csv')},data={})
    assert r.status_code == 400
    assert 'Could not analyze files' in r.text


def test_json_upload_creates_reopenable_history_report(tmp_path, monkeypatch):
    monkeypatch.setenv('METERTRUTH_DB_PATH', str(tmp_path/'scans.sqlite3'))
    raw=b'{"events":[{"id":"e1","account_id":"cus_json","occurred_at":"2026-09-27T00:10:00Z","qty":10,"metric":"api"}]}'
    metered=b'event_id,customer_id,timestamp,quantity,metric\ne1,cus_json,2026-09-27T00:10:00Z,9,api\n'
    r=client.post('/analyze',files={
        'raw_file':('raw.json',raw,'application/json'),
        'metered_file':('metered.csv',metered,'text/csv'),
    },data={'price_per_unit':'0.01','late_hours':'24','quantity_tolerance':'0','annualization_periods':'12','pricing_json':''})
    assert r.status_code == 200
    assert '1 confirmed findings' in r.text
    match=re.search(r'href="/history/(\d+)"',r.text)
    assert match
    scan_id=match.group(1)
    report=client.get(f'/history/{scan_id}')
    assert report.status_code == 200
    assert 'Revenue Leak Report' in report.text
    assert 'WRONG_QUANTITY' in report.text
    history=client.get('/history')
    assert 'raw.json' in history.text and 'metered.csv' in history.text


def test_invoice_and_credit_import_reports_downstream_deltas_without_double_counting(tmp_path, monkeypatch):
    monkeypatch.setenv('METERTRUTH_DB_PATH', str(tmp_path/'ledger.sqlite3'))
    raw=b'event_id,customer_id,timestamp,quantity,metric\ne1,cus_1,2026-09-27T00:10:00Z,10,api\n'
    metered=b'event_id,customer_id,timestamp,quantity,metric\ne1,cus_1,2026-09-27T00:10:00Z,9,api\n'
    invoice=b'invoice_id,customer_id,metric,line_type,amount\ni1,cus_1,api,usage,0.80\ni1,cus_1,,credit,-0.20\n'
    credits=b'customer_id,credit_amount\ncus_1,0.30\n'
    r=client.post('/analyze',files={
        'raw_file':('raw.csv',raw,'text/csv'), 'metered_file':('metered.csv',metered,'text/csv'),
        'invoice_file':('invoice.csv',invoice,'text/csv'), 'credit_file':('credits.csv',credits,'text/csv'),
    },data={'price_per_unit':'0.10','late_hours':'24','quantity_tolerance':'0','annualization_periods':'12','pricing_json':''})
    assert r.status_code == 200
    assert 'INVOICE_MISMATCH' in r.text and 'CREDIT_MISMATCH' in r.text
    assert '<b>Invoice:</b>' in r.text and 'amount' in r.text
    match=re.search(r'href="/history/(\d+)"',r.text)
    report=client.get(f'/history/{match.group(1)}').text
    assert 'Revenue Leak Report' in report
    # Core usage still reports the 1 missing metered unit (€0.10); invoice
    # exposure is calculated from metered usage (expected €0.90 vs €0.80).
    assert 'Potential underbilling</span><strong>€0.10' in report
    assert 'INVOICE_MISMATCH' in report and 'CREDIT_MISMATCH' in report
    assert '€0.20' in report  # ledger underbilling is kept in a separate evidence row


def test_credit_upload_requires_invoice_file():
    raw=b'event_id,customer_id,timestamp,quantity\ne1,cus_1,2026-09-27T00:10:00Z,1\n'
    credits=b'customer_id,credit_amount\ncus_1,1.00\n'
    r=client.post('/analyze',files={
        'raw_file':('raw.csv',raw,'text/csv'),
        'metered_file':('metered.csv',raw,'text/csv'),
        'credit_file':('credits.csv',credits,'text/csv'),
    },data={})
    assert r.status_code == 400
    assert 'Upload invoice lines' in r.text


def test_invoice_tier_rating_aggregates_split_metered_rows_before_pricing():
    from ledger_reconciliation import reconcile_ledgers
    metered=[
        {'event_id':'e1','customer_id':'cus_1','timestamp':'2026-09-27T00:00:00Z','quantity':'2','metric':'api'},
        {'event_id':'e2','customer_id':'cus_1','timestamp':'2026-09-27T00:01:00Z','quantity':'2','metric':'api'},
    ]
    invoice=[{'invoice_id':'i1','customer_id':'cus_1','metric':'api','line_type':'usage','amount':'0.30'}]
    result=reconcile_ledgers(metered,invoice,None,{
        'price_per_unit':'0.10',
        'pricing':{'api':{'tiers':[{'up_to':2,'unit_price':'0.10'},{'up_to':None,'unit_price':'0.05'}]}},
    })
    assert result['findings'] == []  # 2×€0.10 + 2×€0.05 = €0.30


def test_invoice_omitted_metric_is_safe_only_for_single_metered_metric():
    from ledger_reconciliation import reconcile_ledgers
    metered=[
        {'event_id':'e1','customer_id':'cus_1','timestamp':'2026-09-27T00:00:00Z','quantity':'2','metric':'api'},
        {'event_id':'e2','customer_id':'cus_1','timestamp':'2026-09-27T00:01:00Z','quantity':'3','metric':'tokens'},
    ]
    invoice=[{'invoice_id':'i1','customer_id':'cus_1','line_type':'usage','amount':'0.05'}]
    try:
        reconcile_ledgers(metered,invoice,None,{'price_per_unit':'0.01','pricing':{}})
    except ValueError as exc:
        assert 'needs a metric column' in str(exc)
    else:
        assert False, 'ambiguous invoice line must not create misleading findings'


def test_invoice_reconciliation_separates_periods_and_uses_half_open_boundaries():
    from ledger_reconciliation import reconcile_ledgers
    metered=[
        {'event_id':'e1','customer_id':'cus_1','timestamp':'2026-09-27T23:59:59Z','quantity':'1','metric':'api'},
        {'event_id':'e2','customer_id':'cus_1','timestamp':'2026-09-28T00:00:00Z','quantity':'1','metric':'api'},
    ]
    invoice=[
        {'invoice_id':'i1','customer_id':'cus_1','metric':'api','line_type':'usage','amount':'0.05',
         'period_start':'2026-09-27T00:00:00Z','period_end':'2026-09-28T00:00:00Z'},
        {'invoice_id':'i2','customer_id':'cus_1','metric':'api','line_type':'usage','amount':'0.15',
         'period_start':'2026-09-28T00:00:00Z','period_end':'2026-09-29T00:00:00Z'},
    ]
    result=reconcile_ledgers(metered,invoice,None,{'price_per_unit':'0.10','pricing':{}})
    assert [f['code'] for f in result['findings']] == ['INVOICE_MISMATCH','INVOICE_MISMATCH']
    assert [f['impact_eur'] for f in result['findings']] == [0.05,-0.05]
    assert result['summary']['potential_underbilling_eur'] == 0.05
    assert result['summary']['potential_overbilling_eur'] == 0.05


def test_invoice_credit_reconciliation_uses_the_matching_billing_period():
    from ledger_reconciliation import reconcile_ledgers
    period={'period_start':'2026-09-27T00:00:00Z','period_end':'2026-09-28T00:00:00Z'}
    metered=[{'event_id':'e1','customer_id':'cus_1','timestamp':'2026-09-27T10:00:00Z','quantity':'1','metric':'api'}]
    invoice=[
        {'invoice_id':'i1','customer_id':'cus_1','metric':'api','line_type':'usage','amount':'0.10',**period},
        {'invoice_id':'i1','customer_id':'cus_1','line_type':'credit','amount':'-0.10',**period},
    ]
    credits=[{'customer_id':'cus_1','credit_amount':'0.20',**period}]
    result=reconcile_ledgers(metered,invoice,credits,{'price_per_unit':'0.10','pricing':{}})
    assert [f['code'] for f in result['findings']] == ['CREDIT_MISMATCH']
    assert result['findings'][0]['impact_eur'] == 0.10


def test_invoice_period_overlap_is_rejected_instead_of_double_matching():
    from ledger_reconciliation import reconcile_ledgers
    metered=[{'event_id':'e1','customer_id':'cus_1','timestamp':'2026-09-27T10:00:00Z','quantity':'1','metric':'api'}]
    invoice=[
        {'customer_id':'cus_1','metric':'api','amount':'0.10','period_start':'2026-09-27T00:00:00Z','period_end':'2026-09-28T00:00:00Z'},
        {'customer_id':'cus_1','metric':'api','amount':'0.10','period_start':'2026-09-27T12:00:00Z','period_end':'2026-09-28T12:00:00Z'},
    ]
    try:
        reconcile_ledgers(metered,invoice,None,{'price_per_unit':'0.10','pricing':{}})
    except ValueError as exc:
        assert 'periods overlap' in str(exc)
    else:
        assert False, 'overlapping invoice windows must not double count metered usage'


def test_period_invoice_upload_shows_separate_period_findings_in_saved_report(tmp_path, monkeypatch):
    monkeypatch.setenv('METERTRUTH_DB_PATH', str(tmp_path/'period-scan.sqlite3'))
    events=(
        b'event_id,customer_id,timestamp,quantity,metric\n'
        b'e1,cus_1,2026-09-27T23:59:59Z,1,api\n'
        b'e2,cus_1,2026-09-28T00:00:00Z,1,api\n'
    )
    invoice=(
        b'invoice_id,customer_id,metric,line_type,amount,period_start,period_end\n'
        b'i1,cus_1,api,usage,0.05,2026-09-27T00:00:00Z,2026-09-28T00:00:00Z\n'
        b'i2,cus_1,api,usage,0.15,2026-09-28T00:00:00Z,2026-09-29T00:00:00Z\n'
    )
    r=client.post('/analyze',files={
        'raw_file':('raw.csv',events,'text/csv'), 'metered_file':('metered.csv',events,'text/csv'),
        'invoice_file':('invoice.csv',invoice,'text/csv'),
    },data={'price_per_unit':'0.10','late_hours':'24','quantity_tolerance':'0','annualization_periods':'12','pricing_json':''})
    assert r.status_code == 200
    assert r.text.count('<b>INVOICE_MISMATCH</b>') == 2
    match=re.search(r'href="/history/(\d+)"',r.text)
    saved=client.get(f'/history/{match.group(1)}').text
    assert '[2026-09-27' in saved and '[2026-09-28' in saved
    assert 'Excluded from usage exposure cards' in saved


def test_jsonl_and_bad_json_upload(tmp_path, monkeypatch):
    monkeypatch.setenv('METERTRUTH_DB_PATH', str(tmp_path/'scans.sqlite3'))
    raw=b'{"event_id":"e1","customer_id":"cus_1","timestamp":"2026-09-27T00:10:00Z","quantity":2}\n'
    metered=b'{"events":[{"event_id":"e1","customer_id":"cus_1","timestamp":"2026-09-27T00:10:00Z","quantity":2}]}'
    good=client.post('/analyze',files={
        'raw_file':('raw.ndjson',raw,'application/x-ndjson'),
        'metered_file':('metered.json',metered,'application/json'),
    },data={})
    assert good.status_code == 200
    assert '0 confirmed findings' in good.text
    bad=client.post('/analyze',files={
        'raw_file':('bad.json',b'{broken','application/json'),
        'metered_file':('metered.json',metered,'application/json'),
    },data={})
    assert bad.status_code == 400
    assert 'Invalid JSON' in bad.text


def test_stripe_page_and_mock_reconciliation(monkeypatch):
    assert client.get('/stripe').status_code == 200
    assert 'read only' in client.get('/stripe').text.lower()
    class FakeStripe:
        def __init__(self, key):
            assert key == 'rk_test_secret'
        def list_meter_event_summaries(self, **kwargs):
            return [{
                'id':'sum_1','meter':kwargs['meter_id'],'customer_id':kwargs['customer_id'],
                'start_time':1790467200,'end_time':1790470800,'aggregated_value':4
            }]
    monkeypatch.setattr('app.StripeReadClient', FakeStripe)
    raw=b'event_id,customer_id,timestamp,quantity,metric\ne1,cus_123,2026-09-27T00:10:00Z,5,api\n'
    r=client.post('/stripe/analyze', files={'raw_file':('raw.csv',raw,'text/csv')}, data={
        'api_key':'rk_test_secret','meter_id':'mtr_123','customer_id':'cus_123','metric':'api',
        'unit_price':'0.10','start_time':'2026-09-27T00:00:00','end_time':'2026-09-27T01:00:00',
        'grouping':'hour','tolerance':'0'
    })
    assert r.status_code == 200
    assert '1 aggregate findings' in r.text
    assert '€0.10' in r.text
    assert 'rk_test_secret' not in r.text


def test_stripe_multi_customer_scan_route(monkeypatch, tmp_path):
    monkeypatch.setenv('METERTRUTH_DB_PATH', str(tmp_path/'scans.sqlite3'))
    class FakeStripe:
        def __init__(self, key):
            assert key == 'rk_test_secret'
        def list_meter_event_summaries(self, **kwargs):
            actual = {'cus_a': 7, 'cus_b': 4}[kwargs['customer_id']]
            return [{
                'id':'sum_'+kwargs['customer_id'],'meter':kwargs['meter_id'],'customer_id':kwargs['customer_id'],
                'start_time':1790467200,'end_time':1790470800,'aggregated_value':actual
            }]
    monkeypatch.setattr('app.StripeReadClient', FakeStripe)
    raw=(
        b'event_id,customer_id,timestamp,quantity,metric\n'
        b'e1,cus_a,2026-09-27T00:10:00Z,10,api\n'
        b'e2,cus_b,2026-09-27T00:12:00Z,4,api\n'
    )
    r=client.post('/stripe/scan', files={'raw_file':('raw.csv',raw,'text/csv')}, data={
        'api_key':'rk_test_secret','meter_id':'mtr_123','metric':'api','unit_price':'0.10',
        'start_time':'2026-09-27T00:00:00','end_time':'2026-09-27T01:00:00','grouping':'hour','tolerance':'0'
    })
    assert r.status_code == 200
    assert '1 customers with leakage signals' in r.text
    assert 'cus_a' in r.text and 'cus_b' in r.text
    assert '€0.30' in r.text
    assert 'rk_test_secret' not in r.text
    assert 'Export JSON' in r.text
    match=re.search(r'href="/history/(\d+)"',r.text)
    assert match
    saved=client.get(f'/history/{match.group(1)}')
    assert saved.status_code == 200
    assert 'cus_a' in saved.text and 'cus_b' in saved.text


def test_stripe_multi_customer_scan_with_identity_mapping(monkeypatch):
    class FakeStripe:
        def __init__(self, key):
            assert key == 'rk_test_secret'
        def list_meter_event_summaries(self, **kwargs):
            actual = {'cus_a': 8, 'cus_b': 4}[kwargs['customer_id']]
            return [{
                'id':'sum_'+kwargs['customer_id'],'meter':kwargs['meter_id'],'customer_id':kwargs['customer_id'],
                'start_time':1790467200,'end_time':1790470800,'aggregated_value':actual
            }]
    monkeypatch.setattr('app.StripeReadClient', FakeStripe)
    raw=(
        b'event_id,workspace_id,timestamp,quantity,metric\n'
        b'e1,workspace_alpha,2026-09-27T00:10:00Z,10,api\n'
        b'e2,workspace_beta,2026-09-27T00:12:00Z,4,api\n'
        b'e3,workspace_missing,2026-09-27T00:14:00Z,9,api\n'
    )
    mapping=(
        b'internal_customer_id,stripe_customer_id\n'
        b'workspace_alpha,cus_a\n'
        b'workspace_beta,cus_b\n'
    )
    r=client.post('/stripe/scan', files={
        'raw_file':('raw.csv',raw,'text/csv'),
        'mapping_file':('mapping.csv',mapping,'text/csv'),
    }, data={
        'api_key':'rk_test_secret','meter_id':'mtr_123','metric':'api','unit_price':'0.10',
        'start_time':'2026-09-27T00:00:00','end_time':'2026-09-27T01:00:00','grouping':'hour','tolerance':'0'
    })
    assert r.status_code == 200
    assert 'workspace_alpha' in r.text and 'cus_a' in r.text
    assert 'workspace_missing' in r.text
    assert '1 internal customers were not mapped' in r.text
    assert '€0.20' in r.text
    assert 'rk_test_secret' not in r.text


def test_private_beta_onboarding_and_demo_routes():
    r = client.get('/start')
    assert r.status_code == 200
    assert 'First scan' in r.text or 'FIRST SCAN' in r.text
    assert 'Preflight your files' in r.text
    d = client.get('/demo')
    assert d.status_code == 200
    assert '€0.60' in d.text
    assert 'Synthetic' in d.text or 'synthetic' in d.text


def test_preflight_route_ready_and_unmapped_warning():
    raw=(
        b'event_id,workspace_id,timestamp,quantity,metric\n'
        b'e1,workspace_alpha,2026-09-27T00:10:00Z,10,api\n'
        b'e2,workspace_missing,2026-09-27T00:14:00Z,9,api\n'
    )
    mapping=(
        b'internal_customer_id,stripe_customer_id\n'
        b'workspace_alpha,cus_a\n'
    )
    r=client.post('/preflight', files={
        'raw_file':('raw.csv',raw,'text/csv'),
        'mapping_file':('mapping.csv',mapping,'text/csv'),
    })
    assert r.status_code == 200
    assert '>READY<' in r.text
    assert 'Stripe-ready' in r.text
    assert 'workspace_missing' not in r.text  # avoid leaking raw identifiers into generic summary
    assert '1 internal customer IDs are unmapped' in r.text


def test_preflight_route_blocks_without_mapping_for_internal_ids():
    raw=(
        b'event_id,workspace_id,timestamp,quantity,metric\n'
        b'e1,workspace_alpha,2026-09-27T00:10:00Z,10,api\n'
    )
    r=client.post('/preflight', files={'raw_file':('raw.csv',raw,'text/csv')})
    assert r.status_code == 200
    assert '>BLOCKED<' in r.text
    assert 'No Stripe customer IDs are available' in r.text
