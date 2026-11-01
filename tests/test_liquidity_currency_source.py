"""Validate the retained native source, independently of generated fixtures."""
import json
from datetime import date, datetime, timezone
from pathlib import Path
from engine.liquidity_profile import _expected_sessions
from engine.liquidity_currency import qualify_currency


def test_retained_mu_source_has_twenty_separate_dated_currency_observations():
    root=Path(__file__).resolve().parents[1]
    receipt=json.loads((root/'data/stock_currency/MU.json').read_bytes())
    observations=receipt['observations']
    sessions=_expected_sessions(date.fromisoformat(observations[-1]['session']),20)
    result=qualify_currency(receipt,ticker='MU',sessions=sessions,recorded_at=datetime.now(timezone.utc))
    assert result is not None and result['currency']=='USD'
    assert result['dated_sessions']==[day.isoformat() for day in sessions]
    assert result['known_at'] is None and result['published_at'] is None
    assert 'valid_from' not in result and 'valid_through' not in result
    assert result['basis']=='retrospective_dated_reference'
