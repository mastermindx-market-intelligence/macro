"""Historical SEC comparisons remain external context, never receipt credit."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import pytest
from engine.debt_maturity import BUCKETS
from engine.press.issuer_baseline import issuer_baseline_context


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def baseline_inputs(root):
    period = dict(end="2025-12-31", accn="0000064803-26-000010", fy=2025,
                  fp="FY", form="10-K", filed="2026-02-10")
    facts = {}
    def add(tag, value, duration=False):
        row = dict(period, val=value)
        if duration: row["start"] = "2025-01-01"
        facts[tag] = {"units": {"USD": [row]}}
    add("CashAndCashEquivalentsAtCarryingValue", 8453000000)
    add("NetCashProvidedByUsedInOperatingActivities", 10639000000, True)
    add("PaymentsToAcquirePropertyPlantAndEquipment", 2832000000, True)
    for (_, tag, _, _), value in zip(BUCKETS, [4007, 3379, 5008, 3758, 4258, 43299]):
        add(tag, value * 1000000)
    cache = {"cik": 64803, "fetched_at": "2026-09-23T08:01:58+00:00",
             "facts": {"us-gaap": facts}}
    cache_path = root / "data/debt_maturity/cache/CIK0000064803.json"
    identity = root / "data/edgar/ticker_cik_ledger.json"
    review = dict(ticker="CVS", cik="0000064803", cache_sha256=dump(cache_path, cache),
                  identity_sha256=dump(identity, {"tickers": {"CVS": {"cik": "0000064803"}}}),
                  event_quantity_literal="$315 million",
                  relevance="Historical scale comparison only, not current liquidity or price impact.")
    return dict(review=review, root=root, as_of=datetime(2026, 10, 14, 4, tzinfo=timezone.utc),
                reviewed_tickers={"CVS": "CVS Pharmacy Inc."},
                reviewed_claims=[{"quantity_literal": "$315 million"}])


@pytest.fixture
def inputs(tmp_path):
    return baseline_inputs(tmp_path)


def invoke(inputs):
    return issuer_baseline_context(**inputs)


def test_exact_arithmetic_keeps_external_tier_and_filing_clocks(inputs):
    before = {str(p): p.read_bytes() for p in inputs['root'].rglob('*') if p.is_file()}
    facts, revisions = invoke(inputs)
    by_id = {f['id']: f for f in facts}
    assert by_id['issuer_CVS_fcf']['values'] == ['7807000000.0']
    assert by_id['issuer_CVS_cover']['values'] == ['210.96']
    assert by_id['issuer_CVS_near_share']['values'] == ['6.29']
    assert by_id['issuer_CVS_event_cash']['values'] == ['3.73']
    assert by_id['issuer_CVS_event_fcf']['values'] == ['4.03']
    assert all(f['tier'] == 'third_party' for f in facts)
    assert sum(f['derived_from_external'] for f in facts) == 5
    assert all(f['dated'] == '2025-12-31' and f['period']['filed'] == '2026-02-10' for f in facts)
    assert all('2025-12-31' in f['text'] and '2026-02-10' in f['text'] for f in facts)
    assert 'not current liquidity' in by_id['issuer_CVS_event_cash']['text']
    assert len(revisions) == 6
    assert before == {str(p): p.read_bytes() for p in inputs['root'].rglob('*') if p.is_file()}


@pytest.mark.parametrize('field,value', [('ticker','BAC'), ('cik','../64803'),
    ('event_quantity_literal','$315 billion'), ('event_quantity_literal',None),
    ('relevance',''), ('cache_sha256','0'*64), ('identity_sha256','0'*64)])
def test_unqualified_review_refuses(inputs, field, value):
    inputs['review'][field] = value
    with pytest.raises(ValueError): invoke(inputs)


@pytest.mark.parametrize('mutation', ['missing_cik','wrong_cik','bool_cik','future_fetch','same_day_future_fetch',
    'naive_fetch','missing_fetch','foreign_currency','zero_cash','negative_fcf','mismatched_period'])
def test_rebound_invalid_companyfacts_refuse(inputs, mutation):
    p = inputs['root'] / 'data/debt_maturity/cache/CIK0000064803.json'
    d = json.loads(p.read_text()); tags = d['facts']['us-gaap']
    if mutation == 'missing_cik': del d['cik']
    elif mutation == 'wrong_cik': d['cik'] = 123
    elif mutation == 'bool_cik': d['cik'] = True
    elif mutation == 'future_fetch': d['fetched_at'] = '2026-10-15T00:00:00Z'
    elif mutation == 'same_day_future_fetch': d['fetched_at'] = '2026-10-14T23:00:00Z'
    elif mutation == 'naive_fetch': d['fetched_at'] = '2026-10-14T00:00:00'
    elif mutation == 'missing_fetch': del d['fetched_at']
    elif mutation == 'foreign_currency':
        units = tags['CashAndCashEquivalentsAtCarryingValue']['units']
        units['EUR'] = units.pop('USD')
    elif mutation == 'zero_cash': tags['CashAndCashEquivalentsAtCarryingValue']['units']['USD'][0]['val'] = 0
    elif mutation == 'negative_fcf': tags['PaymentsToAcquirePropertyPlantAndEquipment']['units']['USD'][0]['val'] = 20000000000
    elif mutation == 'mismatched_period': tags['NetCashProvidedByUsedInOperatingActivities']['units']['USD'][0]['accn'] = 'different'
    inputs['review']['cache_sha256'] = dump(p, d)
    with pytest.raises(ValueError): invoke(inputs)


def test_wrong_ticker_ledger_and_symlink_refuse(inputs, tmp_path):
    p = inputs['root'] / 'data/edgar/ticker_cik_ledger.json'
    inputs['review']['identity_sha256'] = dump(p, {'CVS': '0000000001'})
    with pytest.raises(ValueError, match='mismatch'): invoke(inputs)
    inputs['review']['identity_sha256'] = dump(p, {'CVS': '0000064803'})
    target = tmp_path / 'outside.json'; target.write_bytes(p.read_bytes())
    p.unlink(); p.symlink_to(target)
    with pytest.raises(ValueError, match='symlink'): invoke(inputs)


def test_stale_and_not_yet_filed_baselines_refuse(inputs):
    for asof in [datetime(2026, 1, 1, tzinfo=timezone.utc), datetime(2028, 10, 14, tzinfo=timezone.utc)]:
        inputs['as_of'] = asof
        with pytest.raises(ValueError): invoke(inputs)
