from engine.market_navigator import Receipt
from engine.market_navigator_sources import snapshot

CUT = '2026-10-21T22:00:00Z'
STATE = {'schema':'market_state.v1','asof':'2026-10-21','verdict':'MIXED','is_display_only':True,'market':'us'}


def receipt(**changes):
    d=dict(source_ref='fixture:state',revision='v1',observed_at='2026-10-21T20:00:00Z',
      received_at='2026-10-21T20:00:01Z',available_at='2026-10-21T20:00:02Z',valid_until='2026-10-22T02:00:00Z')
    return Receipt(**(d|changes))


def read(**changes):
    d=dict(subject='SPY:ARCX',horizon='swing',as_of=CUT,load_state=lambda:dict(STATE))
    return snapshot(**(d|changes))


def test_actual_loader_contract_without_availability_cannot_claim_current():
    x=read()
    assert x['source_admission']=='receipt_missing'
    assert x['reported_state_date']=='2026-10-21'
    assert x['context']['canonical_market']['verdict'] is None


def test_receipt_type_does_not_self_authenticate():
    x=read(state_receipt=receipt())
    assert x['source_admission']=='receipt_verifier_unbound'
    assert x['context']['canonical_market']['verdict'] is None


def test_bound_owner_can_admit_receipt_not_trading():
    calls=[]
    def check(state,r):
        calls.append(r.revision)
        return True
    x=read(state_receipt=receipt(),verify_state_receipt=check)
    assert calls==['v1']
    assert x['source_admission']=='verified_by_bound_owner'
    assert x['context']['canonical_market']['verdict']=='MIXED'
    assert not any(x['context']['authority'].values())
    assert not x['production_binding_proven']


def test_negative_or_truthy_nonboolean_verifier_refuses():
    for result in (False,'yes',1):
        x=read(state_receipt=receipt(),verify_state_receipt=lambda state,r:result)
        assert x['source_admission']=='receipt_not_verified'


def test_read_failure_is_not_neutral_market():
    def broken(): raise OSError('fixture read failure')
    x=read(load_state=broken)
    assert x['source_admission']=='read_failed'
    assert x['context']['canonical_market']['verdict'] is None


def test_missing_and_malformed_are_distinct():
    assert read(load_state=lambda:None)['source_admission']=='unavailable'
    assert read(load_state=lambda:['bad'])['source_admission']=='malformed'


def test_explicit_receipt_does_not_hide_stale_daily_state():
    old=receipt(observed_at='2026-10-09T20:00:00Z',received_at='2026-10-09T20:00:01Z',available_at='2026-10-09T20:00:02Z')
    x=read(load_state=lambda:STATE|{'asof':'2026-10-09'},state_receipt=old,verify_state_receipt=lambda state,r:True)
    assert x['context']['canonical_market']['status']=='stale'


def test_calendar_floor_during_settle_buffer_needs_explicit_completion():
    x=read(as_of='2026-10-21T20:01:00Z',state_receipt=receipt(),verify_state_receipt=lambda state,r:True)
    assert x['expected_daily_session_floor']=='2026-10-20'
    assert x['context']['canonical_market']['status']=='session_completion_unverified'
    y=read(as_of='2026-10-21T20:01:00Z',state_receipt=receipt(),verify_state_receipt=lambda state,r:True,canonical_session_complete=True)
    assert y['context']['canonical_market']['status']=='current'


def test_canary_subject_is_not_a_general_security_master():
    def forbidden_read(): raise AssertionError("unsupported subject must not load state")
    x=read(subject="HSI:XHKG",load_state=forbidden_read)
    assert x["source_admission"]=="unsupported_subject"
    assert x["context"]["canonical_market"]["verdict"] is None
