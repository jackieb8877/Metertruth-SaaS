from urllib.parse import parse_qs, urlparse
import pytest

from stripe_client import StripeReadClient, StripeReadError, validate_secret_key


def test_key_validation():
    assert validate_secret_key('sk_test_abc') == 'sk_test_abc'
    assert validate_secret_key('rk_live_abc') == 'rk_live_abc'
    with pytest.raises(ValueError):
        validate_secret_key('pk_test_nope')


def test_fetch_and_paginate_read_only():
    calls=[]
    responses=[
      {'data':[{'id':'sum_1','meter':'mtr_123','start_time':100,'aggregated_value':3}], 'has_more':True},
      {'data':[{'id':'sum_2','meter':'mtr_123','start_time':200,'aggregated_value':4}], 'has_more':False},
    ]
    def fake_get(url, headers, timeout):
        calls.append((url,headers,timeout))
        return responses[len(calls)-1]
    c=StripeReadClient('rk_test_abc', get_json=fake_get)
    rows=c.list_meter_event_summaries(meter_id='mtr_123',customer_id='cus_123',start_time=0,end_time=3600,grouping='hour')
    assert len(rows)==2
    assert all(x['customer_id']=='cus_123' for x in rows)
    assert all(call[0].startswith('https://api.stripe.com/v1/billing/meters/mtr_123/event_summaries?') for call in calls)
    q2=parse_qs(urlparse(calls[1][0]).query)
    assert q2['starting_after']==['sum_1']
    assert calls[0][1]['Authorization']=='Bearer rk_test_abc'


def test_bad_ids_and_ranges_rejected():
    c=StripeReadClient('sk_test_abc', get_json=lambda *a: {})
    with pytest.raises(ValueError):
        c.list_meter_event_summaries(meter_id='price_1',customer_id='cus_1',start_time=0,end_time=1)
    with pytest.raises(ValueError):
        c.list_meter_event_summaries(meter_id='mtr_1',customer_id='acct_1',start_time=0,end_time=1)
    with pytest.raises(ValueError):
        c.list_meter_event_summaries(meter_id='mtr_1',customer_id='cus_1',start_time=1,end_time=1)


def test_pagination_safety_limit():
    def endless(url, headers, timeout):
        return {'data':[{'id':'sum_1','meter':'mtr_1','start_time':0,'aggregated_value':1}], 'has_more':True}
    c=StripeReadClient('sk_test_abc', get_json=endless)
    with pytest.raises(StripeReadError):
        c.list_meter_event_summaries(meter_id='mtr_1',customer_id='cus_1',start_time=0,end_time=3600,max_pages=2)


def test_grouping_alignment_validation():
    c=StripeReadClient('sk_test_abc', get_json=lambda *a: {'data':[], 'has_more':False})
    with pytest.raises(ValueError, match='exact UTC hours'):
        c.list_meter_event_summaries(meter_id='mtr_1',customer_id='cus_1',start_time=60,end_time=3600,grouping='hour')
    with pytest.raises(ValueError, match='00:00 UTC'):
        c.list_meter_event_summaries(meter_id='mtr_1',customer_id='cus_1',start_time=3600,end_time=86400,grouping='day')
