# Deferred optional calendar-default enhancement

The automatic-default source patch was platform-blocked before execution. Same-carrier
reconciliation confirmed the implemented API still requires an explicit session window
and calendar reference. That original API and its existing short-session tests remain.
The two newly drafted tests below target the unimplemented optional default only. They
are preserved, not represented as passing, skipped, or part of the delivered capability.
No blocked source write was retried. Current callers may supply an explicit window from
the existing engine.session_digest.session_window_et owner as already designed.

```python
def test_outcomes_default_window_reuses_the_existing_calendar_owners():
    from engine.exposure_outlook_outcomes import label_price_outcomes
    out = label_price_outcomes(_outcome_payload(), root='SPY', session='2026-09-18',
        origin='2026-09-18T14:00:00Z', as_of='2026-09-18T21:00:00Z')
    assert out['session_window']['qualification'] == 'canonical_owner'
    assert out['session_window']['open'] == '2026-09-18T13:30:00+00:00'
    assert out['session_window']['close'] == '2026-09-18T20:00:00+00:00'


def test_outcomes_canonical_short_session_and_winter_timezone():
    from datetime import datetime, timezone
    from engine.exposure_outlook_outcomes import label_price_outcomes
    p = _outcome_payload(); start = int(datetime(2026, 11, 27, 9, 30, tzinfo=timezone.utc).timestamp())
    for i, b in enumerate(p['bars']):
        b[0] = start+i*300
    p['session_date'] = '2026-11-27'
    p['source_evidence']['response_scope']['requested_date'] = '2026-11-27'
    _refresh_outcome_scope(p)
    out = label_price_outcomes(p, root='SPY', session='2026-11-27',
        origin='2026-11-27T17:30:00Z', as_of='2026-11-27T22:00:00Z')
    assert out['session_window']['close'] == '2026-11-27T18:00:00+00:00'
    assert _outcome(out, 30)['endpoint_status'] == 'observed'
    assert _outcome(out, 60)['reason_codes'] == ['HORIZON_BEYOND_SESSION']

```
