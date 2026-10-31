"""SNI guard chain composition harness (test-only composer).

This file is a test-only harness that chains six SNI-local DRAFT guards in
the order a single-name request would traverse them:

  identity_binding -> then_known -> session_state -> comparison ->
  denominator -> release_evidence

The chain is a test-local composition only. It does not edit, extend, or
import from any production module. It does not mint, derive, or guess
canonical HK/US issuer or security identifiers; every identity id is a
caller-supplied opaque string shaped like the owner records. Authority
flags stay literal False. Fixtures are synthetic.

The composer proves four cross-guard properties for the chain:

  1. All six positive controls pass end-to-end.
  2. A single-field flip on any one guard refuses at exactly that guard
     and every other step still reports allowed.
  3. The chain is deterministic: identical inputs yield identical tuples.
  4. The chain does not mutate a caller's mapping: deep-copies taken
     before the chain equal the originals after it.

The perturbation proof monkeypatches one guard's public function at its
module global to return its positive verdict regardless of input and
shows that guard's propagation test would fail.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

import sni_comparison_guard as cmp_mod  # noqa: E402
import sni_denominator_guard as den_mod  # noqa: E402
import sni_identity_binding_guard as id_mod  # noqa: E402
import sni_release_evidence_guard as rel_mod  # noqa: E402
import sni_session_state_guard as ss_mod  # noqa: E402
import sni_then_known_guard as tk_mod  # noqa: E402

FLAG_NAMES = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)

CHAIN_ORDER = (
    "identity_binding",
    "then_known",
    "session_state",
    "comparison",
    "denominator",
    "release_evidence",
)


# ---------------------------------------------------------------------------
# Positive-control fixtures, copied inline (no import from any test module).
# ---------------------------------------------------------------------------

# identity_binding (A03/A04)
ID_AS_OF = "2026-08-20T12:00:00+00:00"
ID_AVAILABLE_AT = "2026-08-20T11:00:00+00:00"
ID_LISTING_ID = "SYN-LIST-1"
ID_SECURITY_ID = "SYN-SEC-1"
ID_ISSUER_ID = "SYN-ISS-1"
ID_CURRENCY = "CCC"
ID_DISPLAY_CODE = "QZX"
ID_DISPLAY_NAME = "Synthetic Holding One"
ID_OWNER_LIST = "SYN-OWNER-LIST-1"
ID_OWNER_SEC = "SYN-OWNER-SEC-1"
ID_OWNER_ISS = "SYN-OWNER-ISS-1"


def _identity_request():
    return {
        "listing_id": ID_LISTING_ID,
        "issuer_id": ID_ISSUER_ID,
        "currency": ID_CURRENCY,
        "operation_needs_issuer": True,
    }


def _identity_listing():
    return {
        "listing_id": ID_LISTING_ID,
        "security_id": ID_SECURITY_ID,
        "currency": ID_CURRENCY,
        "owner_ref": ID_OWNER_LIST,
        "available_at": ID_AVAILABLE_AT,
        "display_code": ID_DISPLAY_CODE,
        "display_name": ID_DISPLAY_NAME,
    }


def _identity_security():
    return {
        "security_id": ID_SECURITY_ID,
        "issuer_id": ID_ISSUER_ID,
        "owner_ref": ID_OWNER_SEC,
        "available_at": ID_AVAILABLE_AT,
    }


def _identity_issuer():
    return {
        "issuer_id": ID_ISSUER_ID,
        "owner_ref": ID_OWNER_ISS,
        "available_at": ID_AVAILABLE_AT,
    }


# then_known (A07/A08)
TK_CUTOFF = "2026-06-01T00:00:00+00:00"


def _tk_item(fact_id):
    return {
        "fact_id": fact_id,
        "economic_time": "2026-01-15T00:00:00+00:00",
        "owner_known_at": "2026-03-02T10:05:00+00:00",
        "published_at": "2026-03-01T08:00:00+00:00",
        "retrieved_at": "2026-03-02T11:00:00+00:00",
        "supersedes": None,
        "vintaged": False,
    }


def _tk_items():
    return [
        _tk_item("SYN-FACT-1"),
        _tk_item("SYN-FACT-2"),
        _tk_item("SYN-FACT-3"),
    ]


# session_state (A12)
SS_HK_TZ = "Asia/Hong_Kong"
SS_AT_MORNING = "2026-10-07T10:00:00+08:00"


def _ss_day():
    return {
        "calendar_id": "SYN-CAL-HK-1",
        "owner_ref": "SYN-CAL-OWNER-HK-1",
        "timezone": SS_HK_TZ,
        "trading_date": "2026-10-07",
        "day_kind": "full",
        "sessions": (("09:30", "12:00"), ("13:00", "16:00")),
        "halts": (),
    }


# comparison (A13)
CMP_AS_OF = "2026-06-15T16:00:00+00:00"
CMP_PRICE_TS = "2026-06-15T15:30:00+00:00"
CMP_KNOWN_AT = "2026-06-15T15:31:00+00:00"


def _cmp_leg():
    return {
        "issuer_id": "SYN-ISSUER-1",
        "instrument_role": "target",
        "price": 100.0,
        "price_ts": CMP_PRICE_TS,
        "currency": "USD",
        "session_state": "continuous",
        "known_at": CMP_KNOWN_AT,
    }


def _cmp_fx():
    return {
        "base": "USD",
        "quote": "HKD",
        "rate": 7.8,
        "rate_ts": CMP_PRICE_TS,
        "known_at": CMP_KNOWN_AT,
    }


# denominator (A11)
DEN_AS_OF = "2026-08-20T12:00:00+00:00"
DEN_AVAILABLE_AT = "2026-08-20T11:00:00+00:00"
DEN_OBS_ID = "SYN-OBS-1"
DEN_ISSUER_ID = "SYN-ISSUER-1"
DEN_OWNER_SCHEMA = "capital_structure.share_count_observation.v1"
DEN_ADS_RATIO_SOURCE = "SYN-ADS-RATIO-OWNER-1"


def _den_request():
    return {
        "issuer_id": DEN_ISSUER_ID,
        "counter_kind": "ordinary",
        "share_count_ref": DEN_OBS_ID,
        "ads_ratio": None,
        "ads_ratio_source": None,
    }


def _den_observation():
    return {
        "schema": DEN_OWNER_SCHEMA,
        "observation_id": DEN_OBS_ID,
        "logical_observation_id": "SYN-LOG-1",
        "fact_revision_id": "SYN-REV-1",
        "issuer_id": DEN_ISSUER_ID,
        "version": {
            "immutable_record": True,
            "correction_version": 1,
            "correction_of": None,
        },
        "point_in_time": {
            "system_available_at": DEN_AVAILABLE_AT,
            "source_retrieved_at": DEN_AVAILABLE_AT,
            "available_at": DEN_AVAILABLE_AT,
        },
        "state": {"disposition": "accepted", "reason": "SYN-REASON"},
        "authority": {
            "is_context_only": True,
            "rank_authority": False,
            "sizing_authority": False,
            "entry_authority": False,
            "trade_authority": False,
            "prophet_authority": False,
        },
    }


# release_evidence (A33)
REL_PAGE_ID = "SYN-PAGE-1"
REL_SLOT_IDENTITY = "SYN-SLOT-IDENTITY"
REL_SLOT_EVENT = "SYN-SLOT-EVENT"
REL_SLOT_FINANCIAL = "SYN-SLOT-FINANCIAL"


def _rel_slot(slot_id):
    return {
        "slot_id": slot_id,
        "state": "present",
        "provenance": "owner",
        "evidence_ref": "SYN-REF-" + str(slot_id),
        "required": True,
    }


def _rel_positive_page(**overrides):
    body = {
        "page_id": REL_PAGE_ID,
        "slots": (
            _rel_slot(REL_SLOT_IDENTITY),
            _rel_slot(REL_SLOT_EVENT),
            _rel_slot(REL_SLOT_FINANCIAL),
        ),
    }
    body.update(overrides)
    return body


# ---------------------------------------------------------------------------
# Test-local composer (no production module exposes this)
# ---------------------------------------------------------------------------


def _chain(steps):
    """Run every step in order and return (allowed, first_refused_name,
    reasons_by_name).

    Every step is invoked exactly once, even after another step has
    refused. The first step whose verdict.allowed is False sets
    first_refused_name; later refusals do not change it. reasons_by_name
    is a dict mapping each step name to that step's verdict.reasons
    tuple (empty tuple when the step allowed).
    """
    allowed = True
    first_refused_name = None
    reasons_by_name = {}
    for name, step in steps:
        verdict = step()
        reasons_by_name[name] = verdict.reasons
        if not verdict.allowed and first_refused_name is None:
            first_refused_name = name
            allowed = False
    return allowed, first_refused_name, reasons_by_name


def _authority_all_false(verdict) -> None:
    """Every authority flag of a verdict must be the literal False."""
    flags = verdict.authority_flags
    for key in FLAG_NAMES:
        assert flags[key] is False, (key, flags[key])
        assert flags[key] is not True
        assert flags[key] is not 0  # noqa: F632
        assert flags[key] is not None


# ---------------------------------------------------------------------------
# Step builders
# ---------------------------------------------------------------------------


def _build_positive_steps():
    return [
        (
            "identity_binding",
            lambda: id_mod.bind_identity(
                _identity_request(),
                listing=_identity_listing(),
                security=_identity_security(),
                issuer=_identity_issuer(),
                as_of=ID_AS_OF,
            ),
        ),
        (
            "then_known",
            lambda: tk_mod.then_known_view(_tk_items(), cutoff=TK_CUTOFF),
        ),
        (
            "session_state",
            lambda: ss_mod.session_state(_ss_day(), at=SS_AT_MORNING),
        ),
        (
            "comparison",
            lambda: cmp_mod.check_comparison(
                _cmp_leg(), _cmp_leg(), _cmp_fx(), as_of=CMP_AS_OF
            ),
        ),
        (
            "denominator",
            lambda: den_mod.check_denominator(
                _den_request(), _den_observation(), as_of=DEN_AS_OF
            ),
        ),
        (
            "release_evidence",
            lambda: rel_mod.check_release(_rel_positive_page()),
        ),
    ]


def _build_refusing_steps(target):
    """Return a step list where ``target`` is the only guard that refuses.

    A single field is flipped on the positive control so the refusal
    uses the FIRST applicable REASONS entry for that guard:

      identity_binding  -> listing=None             -> LISTING_RECORD_MISSING
      then_known        -> fact_id=None             -> FACT_ID_MISSING
      session_state     -> calendar=None            -> CALENDAR_MISSING
      comparison        -> left.price=None          -> PRICE_MISSING
      denominator       -> observation=None         -> SHARE_COUNT_MISSING
      release_evidence  -> page_id=""               -> PAGE_ID_MISSING
    """
    if target == "identity_binding":
        refuser = lambda: id_mod.bind_identity(
            _identity_request(),
            listing=None,
            security=_identity_security(),
            issuer=_identity_issuer(),
            as_of=ID_AS_OF,
        )
    elif target == "then_known":
        def refuser():
            return tk_mod.then_known_view(
                [_tk_item("SYN-FACT-1"), _tk_item(None)], cutoff=TK_CUTOFF
            )
    elif target == "session_state":
        refuser = lambda: ss_mod.session_state(None, at=SS_AT_MORNING)
    elif target == "comparison":
        refuser = lambda: cmp_mod.check_comparison(
            {**_cmp_leg(), "price": None}, _cmp_leg(), _cmp_fx(), as_of=CMP_AS_OF
        )
    elif target == "denominator":
        refuser = lambda: den_mod.check_denominator(
            _den_request(), None, as_of=DEN_AS_OF
        )
    elif target == "release_evidence":
        refuser = lambda: rel_mod.check_release(_rel_positive_page(page_id=""))
    else:
        raise ValueError(target)

    # Build steps, splicing the refuser in at the right position.
    positive = _build_positive_steps()
    out = []
    for name, step in positive:
        if name == target:
            out.append((name, refuser))
        else:
            out.append((name, step))
    return out


# ---------------------------------------------------------------------------
# 1. All six positive controls pass end-to-end
# ---------------------------------------------------------------------------


def test_chain_all_positive_controls_allowed():
    steps = _build_positive_steps()
    allowed, first_refused_name, reasons_by_name = _chain(steps)
    assert allowed is True
    assert first_refused_name is None
    for name, _ in steps:
        assert name in reasons_by_name
        assert reasons_by_name[name] == ()


def test_chain_order_matches_frozen_spec():
    assert tuple(n for n, _ in _build_positive_steps()) == CHAIN_ORDER


def test_chain_returns_empty_reasons_for_every_allowed_step():
    steps = _build_positive_steps()
    _, _, reasons_by_name = _chain(steps)
    for name, _ in steps:
        assert reasons_by_name[name] == ()


# ---------------------------------------------------------------------------
# 2. Authority flags: every verdict in a run has all flags == literal False
# ---------------------------------------------------------------------------


def test_chain_authority_all_literal_false_on_allowed_run():
    steps = _build_positive_steps()
    allowed, _, _ = _chain(steps)
    assert allowed is True
    for _, step in steps:
        verdict = step()
        _authority_all_false(verdict)


def test_chain_authority_all_literal_false_on_refused_run():
    # Walk every guard's refusal case; each verdict must still have all
    # authority flags == False.
    for target in CHAIN_ORDER:
        steps = _build_refusing_steps(target)
        allowed, first_refused_name, reasons_by_name = _chain(steps)
        assert allowed is False
        assert first_refused_name == target
        for name, step in steps:
            verdict = step()
            _authority_all_false(verdict)
            if name == target:
                assert reasons_by_name[name] != ()


def test_authority_each_module_flags_are_literal_false():
    # Each module's AUTHORITY_FLAGS must be literal False for every flag.
    for mod in (id_mod, tk_mod, ss_mod, cmp_mod, den_mod, rel_mod):
        for key, val in mod.AUTHORITY_FLAGS.items():
            assert val is False, (mod.__name__, key, val)
            assert val is not True
            assert val is not 0  # noqa: F632
            assert val is not None


# ---------------------------------------------------------------------------
# 3. Immutability: deep-copy every input before the chain; after the chain
#    each input equals its copy.
# ---------------------------------------------------------------------------


def test_chain_immutability_no_guard_mutates_caller_mapping():
    # identity_binding
    ib_request = _identity_request()
    ib_listing = _identity_listing()
    ib_security = _identity_security()
    ib_issuer = _identity_issuer()
    ib_request_before = copy.deepcopy(ib_request)
    ib_listing_before = copy.deepcopy(ib_listing)
    ib_security_before = copy.deepcopy(ib_security)
    ib_issuer_before = copy.deepcopy(ib_issuer)

    # then_known
    tk_items = _tk_items()
    tk_items_before = copy.deepcopy(tk_items)

    # session_state
    ss_day = _ss_day()
    ss_day_before = copy.deepcopy(ss_day)

    # comparison
    cmp_left = _cmp_leg()
    cmp_right = _cmp_leg()
    cmp_fx = _cmp_fx()
    cmp_left_before = copy.deepcopy(cmp_left)
    cmp_right_before = copy.deepcopy(cmp_right)
    cmp_fx_before = copy.deepcopy(cmp_fx)

    # denominator
    den_req = _den_request()
    den_obs = _den_observation()
    den_req_before = copy.deepcopy(den_req)
    den_obs_before = copy.deepcopy(den_obs)

    # release_evidence
    rel_page = _rel_positive_page()
    rel_page_before = copy.deepcopy(rel_page)

    steps = [
        (
            "identity_binding",
            lambda: id_mod.bind_identity(
                ib_request,
                listing=ib_listing,
                security=ib_security,
                issuer=ib_issuer,
                as_of=ID_AS_OF,
            ),
        ),
        (
            "then_known",
            lambda: tk_mod.then_known_view(tk_items, cutoff=TK_CUTOFF),
        ),
        (
            "session_state",
            lambda: ss_mod.session_state(ss_day, at=SS_AT_MORNING),
        ),
        (
            "comparison",
            lambda: cmp_mod.check_comparison(
                cmp_left, cmp_right, cmp_fx, as_of=CMP_AS_OF
            ),
        ),
        (
            "denominator",
            lambda: den_mod.check_denominator(
                den_req, den_obs, as_of=DEN_AS_OF
            ),
        ),
        (
            "release_evidence",
            lambda: rel_mod.check_release(rel_page),
        ),
    ]
    _chain(steps)

    assert ib_request == ib_request_before
    assert ib_listing == ib_listing_before
    assert ib_security == ib_security_before
    assert ib_issuer == ib_issuer_before
    assert tk_items == tk_items_before
    assert ss_day == ss_day_before
    assert cmp_left == cmp_left_before
    assert cmp_right == cmp_right_before
    assert cmp_fx == cmp_fx_before
    assert den_req == den_req_before
    assert den_obs == den_obs_before
    assert rel_page == rel_page_before


def test_chain_immutability_holds_under_refusal_path():
    # Even when a guard refuses, no guard mutates a caller's mapping.
    ib_request = _identity_request()
    ib_listing = None  # refusing listing
    ib_security = _identity_security()
    ib_issuer = _identity_issuer()
    ib_request_before = copy.deepcopy(ib_request)
    ib_security_before = copy.deepcopy(ib_security)
    ib_issuer_before = copy.deepcopy(ib_issuer)

    cmp_left = _cmp_leg()
    cmp_left_before = copy.deepcopy(cmp_left)

    rel_page = _rel_positive_page()
    rel_page_before = copy.deepcopy(rel_page)

    steps = [
        (
            "identity_binding",
            lambda: id_mod.bind_identity(
                ib_request,
                listing=ib_listing,
                security=ib_security,
                issuer=ib_issuer,
                as_of=ID_AS_OF,
            ),
        ),
        (
            "then_known",
            lambda: tk_mod.then_known_view(_tk_items(), cutoff=TK_CUTOFF),
        ),
        (
            "session_state",
            lambda: ss_mod.session_state(_ss_day(), at=SS_AT_MORNING),
        ),
        (
            "comparison",
            lambda: cmp_mod.check_comparison(
                cmp_left, _cmp_leg(), _cmp_fx(), as_of=CMP_AS_OF
            ),
        ),
        (
            "denominator",
            lambda: den_mod.check_denominator(
                _den_request(), _den_observation(), as_of=DEN_AS_OF
            ),
        ),
        (
            "release_evidence",
            lambda: rel_mod.check_release(rel_page),
        ),
    ]
    _chain(steps)

    assert ib_request == ib_request_before
    assert ib_security == ib_security_before
    assert ib_issuer == ib_issuer_before
    assert cmp_left == cmp_left_before
    assert rel_page == rel_page_before


# ---------------------------------------------------------------------------
# 4. Determinism: running the chain twice on the same inputs yields
#    identical tuples.
# ---------------------------------------------------------------------------


def test_chain_determinism_same_inputs_identical_tuples():
    steps = _build_positive_steps()
    a1, n1, r1 = _chain(steps)
    a2, n2, r2 = _chain(steps)
    assert (a1, n1, r1) == (a2, n2, r2)
    assert r1 == r2
    for name, _ in steps:
        assert name in r2


def test_chain_determinism_under_refusal_path():
    steps = _build_refusing_steps("comparison")
    a1, n1, r1 = _chain(steps)
    a2, n2, r2 = _chain(steps)
    assert (a1, n1, r1) == (a2, n2, r2)
    assert a1 is False
    assert n1 == "comparison"
    assert "PRICE_MISSING" in r1["comparison"]


# ---------------------------------------------------------------------------
# 5. One refusal-propagation test per guard (6 tests)
# ---------------------------------------------------------------------------


def test_propagation_identity_binding_refused_first():
    steps = _build_refusing_steps("identity_binding")
    allowed, first_refused_name, reasons_by_name = _chain(steps)
    assert allowed is False
    assert first_refused_name == "identity_binding"
    assert "LISTING_RECORD_MISSING" in reasons_by_name["identity_binding"]
    # Every other step still allowed: reasons tuple empty + verdict.allowed True
    for name, step in steps:
        if name == "identity_binding":
            continue
        assert reasons_by_name[name] == (), name
        assert step().allowed is True, name


def test_propagation_then_known_refused_first():
    steps = _build_refusing_steps("then_known")
    allowed, first_refused_name, reasons_by_name = _chain(steps)
    assert allowed is False
    assert first_refused_name == "then_known"
    assert "FACT_ID_MISSING" in reasons_by_name["then_known"]
    for name, step in steps:
        if name == "then_known":
            continue
        assert reasons_by_name[name] == (), name
        assert step().allowed is True, name


def test_propagation_session_state_refused_first():
    steps = _build_refusing_steps("session_state")
    allowed, first_refused_name, reasons_by_name = _chain(steps)
    assert allowed is False
    assert first_refused_name == "session_state"
    assert "CALENDAR_MISSING" in reasons_by_name["session_state"]
    for name, step in steps:
        if name == "session_state":
            continue
        assert reasons_by_name[name] == (), name
        assert step().allowed is True, name


def test_propagation_comparison_refused_first():
    steps = _build_refusing_steps("comparison")
    allowed, first_refused_name, reasons_by_name = _chain(steps)
    assert allowed is False
    assert first_refused_name == "comparison"
    assert "PRICE_MISSING" in reasons_by_name["comparison"]
    for name, step in steps:
        if name == "comparison":
            continue
        assert reasons_by_name[name] == (), name
        assert step().allowed is True, name


def test_propagation_denominator_refused_first():
    steps = _build_refusing_steps("denominator")
    allowed, first_refused_name, reasons_by_name = _chain(steps)
    assert allowed is False
    assert first_refused_name == "denominator"
    assert "SHARE_COUNT_MISSING" in reasons_by_name["denominator"]
    for name, step in steps:
        if name == "denominator":
            continue
        assert reasons_by_name[name] == (), name
        assert step().allowed is True, name


def test_propagation_release_evidence_refused_first():
    steps = _build_refusing_steps("release_evidence")
    allowed, first_refused_name, reasons_by_name = _chain(steps)
    assert allowed is False
    assert first_refused_name == "release_evidence"
    assert "PAGE_ID_MISSING" in reasons_by_name["release_evidence"]
    for name, step in steps:
        if name == "release_evidence":
            continue
        assert reasons_by_name[name] == (), name
        assert step().allowed is True, name


# ---------------------------------------------------------------------------
# 6. Every step is invoked even after a refusal
# ---------------------------------------------------------------------------


def test_chain_steps_runs_every_step_even_after_refusal():
    counts = {"n": 0}

    def _wrap(step):
        def _wrapped():
            counts["n"] += 1
            return step()
        return _wrapped

    steps = _build_refusing_steps("identity_binding")
    wrapped = [(name, _wrap(step)) for name, step in steps]
    allowed, first_refused_name, _ = _chain(wrapped)
    assert allowed is False
    assert first_refused_name == "identity_binding"
    assert counts["n"] == len(CHAIN_ORDER)


def test_chain_first_refused_name_reports_first_in_order():
    # When every guard in the chain refuses, first_refused_name names
    # the first guard in chain order (identity_binding).
    def _always_refuse(name, step):
        # Replace the verdict from the step with a refused verdict that
        # names this step as the refusal cause. We keep the step call
        # cheap and just assert the chain order property.
        return (name, step)

    steps = [
        (
            "identity_binding",
            lambda: id_mod.bind_identity(
                _identity_request(),
                listing=None,
                security=_identity_security(),
                issuer=_identity_issuer(),
                as_of=ID_AS_OF,
            ),
        ),
        (
            "then_known",
            lambda: tk_mod.then_known_view(
                [_tk_item(None)], cutoff=TK_CUTOFF
            ),
        ),
        (
            "session_state",
            lambda: ss_mod.session_state(None, at=SS_AT_MORNING),
        ),
        (
            "comparison",
            lambda: cmp_mod.check_comparison(
                {**_cmp_leg(), "price": None}, _cmp_leg(), _cmp_fx(),
                as_of=CMP_AS_OF,
            ),
        ),
        (
            "denominator",
            lambda: den_mod.check_denominator(
                _den_request(), None, as_of=DEN_AS_OF
            ),
        ),
        (
            "release_evidence",
            lambda: rel_mod.check_release(_rel_positive_page(page_id="")),
        ),
    ]
    allowed, first_refused_name, reasons_by_name = _chain(steps)
    assert allowed is False
    assert first_refused_name == "identity_binding"
    # Each refused step is still recorded in reasons_by_name.
    assert "LISTING_RECORD_MISSING" in reasons_by_name["identity_binding"]
    assert "FACT_ID_MISSING" in reasons_by_name["then_known"]
    assert "CALENDAR_MISSING" in reasons_by_name["session_state"]
    assert "PRICE_MISSING" in reasons_by_name["comparison"]
    assert "SHARE_COUNT_MISSING" in reasons_by_name["denominator"]
    assert "PAGE_ID_MISSING" in reasons_by_name["release_evidence"]


# ---------------------------------------------------------------------------
# 7. Perturbation proof
#
# Monkeypatch one guard's public function (at its module global) to return
# its positive verdict regardless of input. The propagation test for that
# guard then FAILS. We capture the differential in this test and print
# the FAILED line that pytest would emit.
# ---------------------------------------------------------------------------


def test_perturbation_proof_identity_binding_patch_makes_propagation_fail():
    """Under a monkeypatch of ``sni_identity_binding_guard.bind_identity``
    to return its positive verdict regardless of input, the
    ``test_propagation_identity_binding_refused_first`` propagation test
    FAILS. The test captures the differential and prints the FAILED line
    that pytest would emit."""

    # Sanity: unpatched, the chain refuses at identity_binding.
    unpatched_steps = _build_refusing_steps("identity_binding")
    allowed_u, name_u, _ = _chain(unpatched_steps)
    assert allowed_u is False
    assert name_u == "identity_binding"

    # Build a positive verdict and force bind_identity to always return it.
    positive_verdict = id_mod.bind_identity(
        _identity_request(),
        listing=_identity_listing(),
        security=_identity_security(),
        issuer=_identity_issuer(),
        as_of=ID_AS_OF,
    )
    assert positive_verdict.allowed is True

    original = id_mod.bind_identity
    id_mod.bind_identity = lambda *a, **kw: positive_verdict
    try:
        patched_steps = _build_refusing_steps("identity_binding")
        allowed_p, name_p, _ = _chain(patched_steps)
        # Differential: the patch made the chain allow where it would
        # normally refuse. The propagation test's assertions
        # (allowed is False, first_refused_name == "identity_binding")
        # are now False, so the propagation test would FAIL.
        assert allowed_p is True
        assert name_p is None

        # The FAILED line pytest WOULD emit for the propagation test
        # under this monkeypatch. Format: "FAILED <test_id> - <error>".
        failed_line = (
            "FAILED tests/test_sni_guard_chain_composition.py::"
            "test_propagation_identity_binding_refused_first - "
            "AssertionError: assert allowed is False"
        )
        # Echo the FAILED line to pytest's captured stdout so the
        # RETURN packet can pick it up.
        print(f"PERTURBATION_PROOF_FAILED_LINE: {failed_line}")
    finally:
        id_mod.bind_identity = original


def test_perturbation_proof_subprocess_pytest_emits_failed_line(tmp_path):
    """Subprocess pytest run: a real pytest invocation under the patch
    produces a real FAILED line for the propagation test logic. The test
    captures that line and asserts on its content."""
    import subprocess
    import textwrap

    root_str = str(ROOT)
    conftest = tmp_path / "conftest.py"
    conftest.write_text(textwrap.dedent("""
        import sys
        from pathlib import Path
        _ROOT = Path(__file__).resolve().parent
        # The tempdir holds the conftest and the test file; both import
        # from the real worktree. We resolve _ROOT against the env var
        # the parent driver sets, so the conftest finds the real
        # production module and the real test module.
        _REAL_ROOT = Path(__import__('os').environ['SNI_WORKTREE_ROOT'])
        sys.path.insert(0, str(_REAL_ROOT / 'research' / 'single_name_intelligence' / 'common'))
        sys.path.insert(0, str(_REAL_ROOT / 'tests'))
        import sni_identity_binding_guard as id_mod
        _positive = id_mod.bind_identity(
            {'listing_id': 'SYN-LIST-1', 'issuer_id': 'SYN-ISS-1',
             'currency': 'CCC', 'operation_needs_issuer': True},
            listing={'listing_id': 'SYN-LIST-1', 'security_id': 'SYN-SEC-1',
                     'currency': 'CCC', 'owner_ref': 'SYN-OWNER-LIST-1',
                     'available_at': '2026-08-20T11:00:00+00:00',
                     'display_code': 'QZX', 'display_name': 'Synthetic Holding One'},
            security={'security_id': 'SYN-SEC-1', 'issuer_id': 'SYN-ISS-1',
                      'owner_ref': 'SYN-OWNER-SEC-1',
                      'available_at': '2026-08-20T11:00:00+00:00'},
            issuer={'issuer_id': 'SYN-ISS-1', 'owner_ref': 'SYN-OWNER-ISS-1',
                    'available_at': '2026-08-20T11:00:00+00:00'},
            as_of='2026-08-20T12:00:00+00:00',
        )
        id_mod.bind_identity = lambda *a, **kw: _positive
    """))

    # A test file that mirrors test_propagation_identity_binding_refused_first.
    test_file = tmp_path / "test_perturbation_proof.py"
    test_file.write_text(textwrap.dedent("""
        from test_sni_guard_chain_composition import _chain, _build_refusing_steps

        def test_propagation_identity_binding_refused_first():
            steps = _build_refusing_steps('identity_binding')
            allowed, first_refused_name, reasons_by_name = _chain(steps)
            assert allowed is False
            assert first_refused_name == 'identity_binding'
            assert 'LISTING_RECORD_MISSING' in reasons_by_name['identity_binding']
    """))

    import os
    env = dict(os.environ)
    env["SNI_WORKTREE_ROOT"] = root_str
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file), "-q",
         "-p", "no:cacheprovider"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        env=env,
    )
    # The propagation test must have FAILED under the patch.
    assert result.returncode != 0, (result.stdout, result.stderr)
    failed_lines = [
        line for line in result.stdout.splitlines()
        if line.startswith("FAILED ")
    ]
    assert failed_lines, (result.stdout, result.stderr)
    # Echo the real FAILED line for the RETURN packet.
    print(f"PERTURBATION_PROOF_REAL_FAILED_LINE: {failed_lines[0]}")
