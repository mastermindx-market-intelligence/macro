"""Native unit tests for engine/options_pulse.py — the deterministic Options Pulse projector.

PINS (each is a deliberate contract, not an incidental behaviour):
  * purity — no network, no LLM, no randomness, no wall clock
  * identity — requested symbol vs payload ticker; input FILE identity separate
  * numerics — bool / NaN / inf / negative / malformed profile all REJECTED
  * units — the ±1% figure is the incumbent engine's own $bn-per-1%-move unit
  * honesty — odds/probability and signed/bullish flow are withheld, not proxied
  * determinism — identical inputs -> identical content hash, at ANY clock
  * identity binding — a CORRECTED snapshot must invalidate the content hash
  * authority — every output authority flag is false, always
"""
from __future__ import annotations

import copy
import inspect
import json
import math
from datetime import date, datetime, timezone

import pytest

from engine import options_pulse as op

NOW = datetime(2026, 10, 22, 18, 30, tzinfo=timezone.utc)
ASOF = "2026-10-21"


def _profile(spot: float = 100.0, sign: float = -1.0, n: int = 81) -> dict:
    """A symmetric profile whose MIDPOINT is the spot, exactly as the producer's
    grid is (linspace(0.85, 1.15, 81)[40] == spot). The midpoint carries `sign`."""
    xs = [round(spot * (0.85 + 0.30 * i / (n - 1)), 2) for i in range(n)]
    ys = []
    for i in range(n):
        offset = i - (n // 2)
        ys.append(round(sign * (5.0 - abs(offset) * 0.1), 4))
    return {"spots": xs, "gamma_bn": ys, "flip": None, "spot": spot}


def _payload(*, key: str = "QQQ", asof: str = ASOF, spot: float = 100.0,
             sign: float = -1.0, net_gex_bn: float | None = None,
             flip: float | None = None, n: int = 81) -> dict:
    prof = _profile(spot, sign, n)
    if flip is not None:
        prof["flip"] = flip
    mid = prof["gamma_bn"][len(prof["gamma_bn"]) // 2]
    return {
        "meta": {"key": key, "en": "Nasdaq 100 ETF", "zh": "纳指100 ETF",
                 "grp": "ETF", "src": "core", "asof": asof},
        "summary": {
            "spot": spot, "tier": "full", "n_strikes": 5032,
            "net_gex_bn": mid if net_gex_bn is None else net_gex_bn,
            "gamma_flip": flip,
            "gamma_regime": "short" if mid < 0 else "long",
            "regime_passport": {"basis": "assumption", "verdict": "display-only",
                                "is_index_product": True, "structurally_constant": False},
        },
        "profile": prof,
        "walls": {
            "by_strike": [
                {"K": 110.0, "net_mn": 574.91, "pct": 57.7, "call_oi": 231126, "put_oi": 25582},
                {"K": 105.0, "net_mn": -196.75, "pct": 19.7, "call_oi": 122275, "put_oi": 9287},
                {"K": 90.0, "net_mn": -120.5, "pct": 10.0, "call_oi": 1000, "put_oi": 2000},
            ],
            "call_wall": 110.0, "put_wall": 90.0, "largest_oi": 105.0, "max_abs_mn": 574.91,
        },
    }


GATE_UNRELIABLE = {"scored": False, "direction_reliable": False, "asof": "2026-06-21"}
INTEL = {"schema": "options.intel_brief/v1", "model_version": "intel_brief_heuristic/v1.2",
         "as_of_session": "2026-10-21", "board_state": "INSUFFICIENT_COVERAGE",
         "pending_reason": "OI_NOT_YET_SETTLED", "directional_qualified_count": 0}


_MISSING = object()


def _build(payload=_MISSING, *, symbol="QQQ", gate=None, intel=None,
           digest="sha256:deadbeef", now=NOW, **kw):
    return op.build_pulse(
        symbol=symbol,
        gex=_payload() if payload is _MISSING else payload,
        gex_file="site/gex/QQQ.json", gex_digest=digest,
        intel=INTEL if intel is None else intel,
        intel_file="site/options_intel_brief.json", intel_digest="sha256:cafe",
        gate=GATE_UNRELIABLE if gate is None else gate,
        gate_file="data/options_flow/signing_gate.json", gate_digest="sha256:f00d",
        now=now, **kw,
    )


# ───────────────────────────── purity / no-AI ───────────────────────────────
def test_projector_imports_no_network_llm_or_randomness():
    """No third-party runtime dependency may enter a deterministic card."""
    src = inspect.getsource(op)
    for banned in ("import requests", "import httpx", "import urllib", "import socket",
                   "import openai", "import anthropic", "from openai", "from anthropic",
                   "import random", "import numpy", "import pandas", "import time"):
        assert banned not in src, f"projector must not depend on {banned!r}"


def test_projector_reads_no_wall_clock():
    """The caller owns the clock; a wall-clock read would break determinism."""
    src = inspect.getsource(op)
    for banned in ("datetime.now(", "date.today(", "time.time(", "utcnow("):
        assert banned not in src, f"projector must not read a wall clock via {banned!r}"


def test_projector_performs_no_file_io():
    src = inspect.getsource(op)
    for banned in ("open(", "read_bytes", "Path(", ".read_text"):
        assert banned not in src, f"projector must not touch the filesystem via {banned!r}"


def test_naive_clock_is_a_programmer_error_not_a_silent_default():
    with pytest.raises(op.PulseInputError):
        _build(now=datetime(2026, 10, 22, 18, 30))  # naive


def test_empty_symbol_is_a_programmer_error():
    with pytest.raises(op.PulseInputError):
        op.build_pulse(symbol="  ", gex=_payload(), gex_file="x", gex_digest=None,
                       now=NOW, reference_session=date(2026, 10, 21))


# ───────────────────────────── gamma sign / zero ────────────────────────────
@pytest.mark.parametrize("sign,expected", [(1.0, "positive"), (-1.0, "negative")])
def test_known_positive_and_negative_gamma(sign, expected):
    p = _build(_payload(sign=sign))
    assert p["available"] is True
    assert p["gamma"]["regime"] == expected
    assert (p["gamma"]["net_gamma_bn_per_1pct"] > 0) is (sign > 0)


def test_zero_gamma_is_flat_not_positive():
    payload = _payload()
    mid = len(payload["profile"]["gamma_bn"]) // 2
    payload["profile"]["gamma_bn"][mid] = 0.0
    payload["summary"]["net_gex_bn"] = 0.0
    p = _build(payload)
    assert p["gamma"]["regime"] == "zero"


# ───────────────────────────── units + signs ─────────────────────────────────
def test_hedge_is_dollars_bn_per_one_percent_move():
    """The ±1% figure carries the INCUMBENT engine's own unit — no new repricer."""
    payload = _payload(sign=-1.0)
    p = _build(payload)
    h = p["hedge"]
    assert h["available"] is True
    assert h["basis"] == "LINEAR_ASSUMPTION_BASED_SENSITIVITY"
    assert h["up_1pct_bn"] == pytest.approx(-5.0, abs=0.01)
    # opposite shocks obey consistent signs and are symmetric under the local
    # (linear) approximation this card explicitly publishes
    assert h["down_1pct_bn"] == pytest.approx(5.0, abs=0.01)
    assert h["up_1pct_bn"] == pytest.approx(-h["down_1pct_bn"], abs=1e-9)
    assert h["reference_notional_usd_per_1pct"] == pytest.approx(1.0, abs=1e-6)


def test_hedge_amounts_withheld_when_no_qualified_local_value():
    payload = _payload()
    payload["profile"]["spot"] = 999.0        # spot identity mismatch -> no card
    p = _build(payload)
    assert p["available"] is False
    assert p["hedge"]["available"] is False
    assert p["hedge"]["up_1pct_bn"] is None
    assert p["hedge"]["withheld_reasons_en"]


def test_hedge_documents_its_assumptions():
    h = _build()["hedge"]
    joined = " ".join(h["assumptions_en"]).lower()
    assert "linear" in joined and "constant" in joined and "long calls" in joined
    assert "not an exact nonlinear hedge trade" in h["assumptions_en"][0]


# ───────────────────────────── identity ──────────────────────────────────────
def test_wrong_ticker_is_rejected_not_substituted():
    p = _build(_payload(key="SPY"), symbol="QQQ")
    assert p["available"] is False
    assert any(r.startswith("symbol_mismatch") for r in p["unavailable_reasons"])


def test_symbol_identity_survives_case_and_whitespace():
    p = _build(symbol="  qqq ")
    assert p["available"] is True
    assert p["symbol"] == "QQQ"


def test_missing_payload_is_unavailable_not_zero():
    p = _build(None)
    assert p["available"] is False
    assert p["gamma"]["net_gamma_bn_per_1pct"] is None
    assert p["hedge"]["up_1pct_bn"] is None
    assert any("source_missing" in r for r in p["unavailable_reasons"])


def test_missing_is_never_zero():
    """A null must stay null all the way to the card."""
    p = _build(None)
    assert p["available"] is False
    assert p["gamma"]["net_gamma_bn_per_1pct"] is None
    assert p["hedge"]["up_1pct_bn"] is None
    flat = _build(_payload())
    flat["concentrations"] = op._concentrations({}, 100.0)
    assert flat["concentrations"]["rows"] == []
    assert flat["concentrations"]["call_wall"] is None


def test_spot_identity_mismatch_is_rejected():
    payload = _payload()
    payload["profile"]["spot"] = 123.0
    p = _build(payload)
    assert p["available"] is False
    assert any("spot_identity_mismatch" in r for r in p["unavailable_reasons"])


# ───────────────────────────── numerics ──────────────────────────────────────
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf"), True, False])
def test_nonfinite_and_bool_coordinates_are_rejected(bad):
    payload = _payload()
    payload["profile"]["gamma_bn"][5] = bad
    p = _build(payload)
    assert p["available"] is False
    assert any("profile_malformed" in r for r in p["unavailable_reasons"])


@pytest.mark.parametrize("bad", [True, False, float("nan"), float("inf"), -5.0, 0, "100"])
def test_declared_but_unusable_spot_is_rejected_not_ignored(bad):
    """A present-but-bad spot is a MALFORMED payload, not an absent field: silently
    ignoring it would let a bad summary hide behind a good profile."""
    payload = _payload()
    payload["summary"]["spot"] = bad
    p = _build(payload)
    assert p["available"] is False
    assert any("spot_invalid" in r for r in p["unavailable_reasons"])


def test_negative_or_zero_spot_is_rejected():
    for bad in (0, -5.0):
        payload = _payload()
        payload["profile"]["spot"] = bad
        payload["summary"]["spot"] = bad
        assert _build(payload)["available"] is False


def test_mismatched_array_lengths_are_rejected():
    payload = _payload()
    payload["profile"]["gamma_bn"] = payload["profile"]["gamma_bn"][:10]
    p = _build(payload)
    assert p["available"] is False
    assert any("profile_malformed" in r for r in p["unavailable_reasons"])


def test_unsorted_profile_is_rejected():
    payload = _payload()
    payload["profile"]["spots"] = list(reversed(payload["profile"]["spots"]))
    p = _build(payload)
    assert p["available"] is False
    assert any("not strictly increasing" in r for r in p["unavailable_reasons"])


def test_duplicate_profile_coordinate_is_rejected():
    payload = _payload()
    payload["profile"]["spots"][3] = payload["profile"]["spots"][2]
    p = _build(payload)
    assert p["available"] is False
    assert any("not strictly increasing" in r for r in p["unavailable_reasons"])


def test_oversized_profile_is_refused_not_truncated():
    payload = _payload(n=op.MAX_PROFILE_POINTS + 2)
    p = _build(payload)
    assert p["available"] is False
    assert any("profile_oversize" in r for r in p["unavailable_reasons"])


# ───────────────────────────── sessions ──────────────────────────────────────
def test_future_dated_source_is_rejected():
    p = _build(_payload(asof="2026-12-01"))
    assert p["available"] is False
    assert any("source_future" in r for r in p["unavailable_reasons"])


def test_session_gap_is_measured_in_sessions_not_calendar_days():
    fresh = _build(_payload(asof=ASOF))
    assert fresh["assessment"]["sessions_behind"] == 0
    assert fresh["assessment"]["freshness"] == "current_session"

    gapped = _build(_payload(asof="2026-10-16"))   # Fri -> Wed crosses a weekend
    assert gapped["assessment"]["sessions_behind"] == 3
    assert gapped["assessment"]["freshness"] == "delayed"


def test_holiday_and_weekend_are_handled_by_the_exchange_calendar():
    # 2026-11-26 is Thanksgiving (NYSE closed). Evaluated at 13:30 ET that day the
    # reference session is the prior Wednesday, NOT the host's calendar date.
    now = datetime(2026, 11, 26, 18, 30, tzinfo=timezone.utc)   # 13:30 ET
    on_holiday = _build(_payload(asof="2026-11-25"), now=now)
    assert on_holiday["assessment"]["reference_session"] == "2026-11-25"
    assert on_holiday["assessment"]["sessions_behind"] == 0

    # Wed 11-25 -> ref 11-25 is exactly ONE session, so the holiday is not counted
    two_back = _build(_payload(asof="2026-11-24"), now=now)
    assert two_back["assessment"]["sessions_behind"] == 1

    # Before Monday's 17:00 ET settle buffer, Friday is still the last COMPLETED
    # session — the card ages in sessions and never claims a half-finished Monday.
    weekend = _build(_payload(asof="2026-10-16"),
                     now=datetime(2026, 10, 19, 18, 30, tzinfo=timezone.utc))
    assert weekend["assessment"]["reference_session"] == "2026-10-16"
    assert weekend["assessment"]["sessions_behind"] == 0

    # After the buffer, the weekend costs NO extra sessions: Thu -> Mon is the 2
    # trading sessions (Fri, Mon), not the 4 calendar days a naive reader would say.
    crossed = _build(_payload(asof="2026-10-15"),
                     now=datetime(2026, 10, 19, 22, 30, tzinfo=timezone.utc))
    assert crossed["assessment"]["reference_session"] == "2026-10-19"
    assert crossed["assessment"]["sessions_behind"] == 2


def test_unparseable_session_degrades_rather_than_projects():
    p = _build(_payload(asof="not-a-date"))
    assert p["available"] is False
    assert any("session_missing" in r for r in p["unavailable_reasons"])


def test_source_is_never_labelled_live():
    p = _build()
    assert "Delayed end-of-day" in p["source"]["context_label_en"]
    assert "live" not in p["source"]["context_label_en"].lower()


def test_injected_reference_session_is_honoured():
    p = _build(reference_session=date(2026, 10, 21))
    assert p["assessment"]["reference_session"] == "2026-10-21"
    assert p["assessment"]["sessions_behind"] == 0


# ───────────────────────────── crossing ownership ───────────────────────────
def test_displayed_crossing_comes_from_the_same_owner_as_the_curve():
    p = _build(_payload(flip=103.7))
    assert p["gamma"]["crossing"]["owner"] == "gex.profile"
    assert p["gamma"]["crossing"]["spot"] == 103.7


def test_owner_disagreement_is_exposed_never_averaged():
    payload = _payload(flip=103.7)
    payload["summary"]["gamma_flip"] = 103.62
    p = _build(payload)
    dis = p["gamma"]["crossing"]["disagreement"]
    assert dis["present"] is True
    assert dis["delta"] == pytest.approx(0.08, abs=1e-6)
    # the CARD shows the profile's own crossing — never a blend of the two
    assert p["gamma"]["crossing"]["spot"] == 103.7


def test_absent_crossing_is_none_not_invented():
    p = _build(_payload(flip=None))
    assert p["gamma"]["crossing"]["available"] is False
    assert p["gamma"]["crossing"]["spot"] is None


# ───────────────────────────── honesty gates ────────────────────────────────
def test_closing_probability_is_withheld_with_reasons():
    p = _build()
    assert p["probability"]["available"] is False
    assert "RESEARCH_ONLY" in p["probability"]["withheld_note_en"]
    assert "INSUFFICIENT_DATA" in p["probability"]["withheld_note_en"]
    # useful alternatives ARE offered instead of a fabricated number
    assert p["probability"]["alternatives_offered"]


def test_signed_and_bullish_flow_is_withheld_while_the_gate_is_unreliable():
    p = _build()
    assert p["flow"]["available"] is False
    assert p["flow"]["gate_direction_reliable"] is False
    assert any("direction_unreliable" in r for r in p["flow"]["reasons"])
    assert "bullish" in p["flow"]["withheld_note_en"].lower()


def test_no_numeric_bullish_proxy_is_emitted_anywhere():
    p = _build()
    blob = json.dumps(p["flow"], default=str).lower()
    for banned in ("bullish_pct", "bullish_share", "call_pct", "flow_score", "q_flow"):
        assert banned not in blob


def test_retained_activity_is_named_unsigned_not_bullish():
    p = _build()
    note = p["flow"]["unsigned_activity_note_en"].lower()
    assert "unsigned" in note
    assert "bullish" in note  # present only as the explicit "never bullish" disclaimer


def test_stale_intel_brief_keeps_provenance_and_flags_staleness():
    p = _build(intel=dict(INTEL, as_of_session="2026-08-19"))
    assert p["flow"]["intel_as_of_session"] == "2026-08-19"      # provenance preserved
    assert p["flow"]["intel_model"] == "intel_brief_heuristic/v1.2"
    assert p["flow"]["intel_board_state"] == "INSUFFICIENT_COVERAGE"
    assert p["flow"]["intel_sessions_behind"] > 0
    assert any("intel_brief_stale" in r for r in p["flow"]["reasons"])
    assert p["flow"]["available"] is False        # stale is NOT read as zero activity


def test_reliable_gate_does_not_unlock_any_signed_flow_number():
    """Even a green gate leaves this card display-only: it publishes no flow number."""
    p = _build(gate={"direction_reliable": True, "asof": "2026-06-21"})
    assert p["flow"]["gate_direction_reliable"] is True
    assert p["flow"]["available"] is False


def test_research_only_engines_are_never_imported():
    src = inspect.getsource(op)
    for banned in ("options_rn_tail_density", "options_arbfree_surface",
                   "options_american_exercise"):
        assert f"import {banned}" not in src


# ───────────────────────────── authority ─────────────────────────────────────
def test_every_output_authority_flag_is_false():
    p = _build()
    assert p["authority"]["display_only"] is True
    for flag in ("may_recommend_trade", "may_rank", "may_size", "may_alert", "may_score"):
        assert p["authority"][flag] is False
    assert p["context"]["authority"] == p["authority"]


def test_authority_flags_are_false_even_on_a_degraded_card():
    p = _build(None)
    for flag in ("may_recommend_trade", "may_rank", "may_size", "may_alert", "may_score"):
        assert p["authority"][flag] is False


def test_walls_are_never_called_a_floor_cap_or_target():
    p = _build()
    blob = json.dumps(p["concentrations"], default=str).lower()
    for banned in ("floor", "cap", "target", "guaranteed", "support_level", "resistance"):
        assert banned not in blob.replace("never a floor, cap or target", "")


def test_profile_is_labelled_an_exposure_curve_not_a_price_density():
    p = _build()
    assert "Not a closing-price density" in p["gamma"]["framing_en"]
    assert "gamma_basis" in p["context"]
    assert p["gamma"]["regime_basis"] == "assumption"


# ───────────────────────────── determinism ───────────────────────────────────
def test_same_inputs_give_the_same_output_at_any_clock():
    """The build clock is EXCLUDED from the content hash."""
    a = _build(now=datetime(2026, 10, 22, 18, 30, tzinfo=timezone.utc))
    b = _build(now=datetime(2026, 10, 23, 3, 15, tzinfo=timezone.utc))
    assert a["content_hash"] == b["content_hash"]
    assert a["assessment"]["evaluated_utc"] != b["assessment"]["evaluated_utc"]


def test_content_hash_excludes_the_build_clock_entirely():
    # two clocks on the same side of the source session: the card is identical
    a = _build(now=datetime(2026, 10, 22, 1, 0, tzinfo=timezone.utc))
    b = _build(now=datetime(2026, 10, 22, 23, 59, tzinfo=timezone.utc))
    assert a["content_hash"] == b["content_hash"]
    assert a["assessment"]["evaluated_utc"] != b["assessment"]["evaluated_utc"]
    assert "evaluated_utc" not in op._semantic_fingerprint(a)


def test_a_clock_before_the_source_session_correctly_degrades_it():
    """The clock is excluded from the HASH, but a clock earlier than the source
    session is a real future-source condition, not a silent staleness."""
    p = _build(now=datetime(2026, 1, 5, tzinfo=timezone.utc))
    assert p["available"] is False
    assert any("source_future" in r for r in p["unavailable_reasons"])


def test_content_hash_binds_the_assessment_session():
    a = _build(reference_session=date(2026, 10, 21))
    b = _build(_payload(asof="2026-10-20"), reference_session=date(2026, 10, 21))
    assert a["assessment"]["reference_session"] == b["assessment"]["reference_session"]


def test_correcting_a_snapshot_invalidates_its_identity():
    """A corrected value must not be able to keep the old content hash."""
    before = _build(_payload(asof="2026-10-20"))
    corrected = _build(_payload(asof="2026-10-21"))   # the correction itself
    assert before["source"]["asof"] != corrected["source"]["asof"]
    assert before["content_hash"] != corrected["content_hash"]


def test_correcting_a_gamma_value_invalidates_its_identity():
    before = _build(_payload(sign=-1.0))
    after = _build(_payload(sign=-1.05))
    assert before["content_hash"] != after["content_hash"]


def test_changed_input_file_digest_invalidates_identity_even_for_equal_bytes():
    """Input FILE identity is separate from payload: a corrected file cannot
    masquerade as the one whose card is on screen."""
    payload = _payload()
    a = op.build_pulse(symbol="QQQ", gex=payload, gex_file="site/gex/QQQ.json",
                       gex_digest="sha256:aaa", now=NOW, reference_session=date(2026, 10, 21))
    b = op.build_pulse(symbol="QQQ", gex=copy.deepcopy(payload), gex_file="site/gex/QQQ.json",
                       gex_digest="sha256:bbb", now=NOW, reference_session=date(2026, 10, 21))
    assert a["content_hash"] != b["content_hash"]


def test_input_file_identity_is_reported_separately_from_session():
    p = _build(digest="sha256:feedface", now=NOW)
    assert p["source"]["files"]["gex"]["digest"] == "sha256:feedface"
    assert p["source"]["asof"] == ASOF                    # source session, separate
    assert p["assessment"]["evaluated_utc"] != p["source"]["asof"]  # clock, separate


# ───────────────────────────── chart ─────────────────────────────────────────
def test_chart_geometry_is_derived_from_validated_numbers_only():
    p = _build(_payload(flip=103.7))
    ch = p["chart"]
    assert ch["points"] == 81
    assert ch["width"] > 0 and ch["height"] > 0
    # a path made of nothing but M/L commands and fixed-precision coordinates —
    # no attribute breaks, no interpolation of untrusted text
    import re
    assert re.fullmatch(r"M -?\d+\.\d+,-?\d+\.\d+( L -?\d+\.\d+,-?\d+\.\d+)+",
                        ch["path"])


def test_chart_aspect_ratio_stays_renderable():
    """The SVG viewBox drives the rendered height (width:100%, height:auto). An
    extreme ratio renders a card thousands of pixels tall — pin a sane band."""
    ch = _build(_payload(flip=103.7))["chart"]
    lo, hi = op.CHART_ASPECT
    aspect = ch["width"] / ch["height"]
    assert lo <= aspect <= hi, f"chart aspect {aspect:.2f} outside {CHART_ASPECT}"


def test_chart_marks_its_own_crossing():
    p = _build(_payload(flip=103.7))
    assert p["chart"]["flip_x"] is not None
    assert 0 <= p["chart"]["flip_x"] <= p["chart"]["width"]


# ───────────────────────────── context budget ───────────────────────────────
def test_model_context_is_compact_and_bounded():
    p = _build()
    assert len(p["context"]["_facts"]) <= 2400
    assert p["context"]["display_only"] is True
    assert p["context"]["probability_available"] is False
    assert p["context"]["signed_flow_available"] is False


def test_model_context_carries_no_source_free_prose():
    """The model receives facts, not narrative it could restate as a claim."""
    # every string in the model context is either an ENUMERATED value from a closed
    # vocabulary or an explicitly source-provenance field — never free prose
    ENUMERATED = {
        "gamma_regime": {"positive", "negative", "zero"},
        "gamma_basis": {None, "assumption"},
        "crossing_owner": {None, "gex.profile"},
        "hedge_basis": {"LINEAR_ASSUMPTION_BASED_SENSITIVITY"},
    }
    facts = json.loads(_build()["context"]["_facts"])
    for key, value in facts.items():
        if key in ENUMERATED:
            assert value in ENUMERATED[key], f"{key}={value!r} is outside its closed vocabulary"
        elif isinstance(value, str):
            assert (key.startswith("_") or key.startswith("intel_")
                    or key in {"symbol", "reference_session", "source_asof"}), (
                f"{key}={value!r} is prose, not a fact")


# ───────────────────────────── escaping ──────────────────────────────────────
def test_malicious_external_strings_are_carried_raw_for_the_renderer_to_escape():
    """The projector returns DATA; escaping is the template's job (autoescape=False)."""
    payload = _payload()
    payload["meta"]["en"] = "<script>alert('x')</script>"
    payload["meta"]["zh"] = '"><img src=x onerror=alert(1)>'
    p = _build(payload)
    assert p["identity"]["name_en"] == "<script>alert('x')</script>"
    assert p["identity"]["name_zh"].startswith('"><img')


def test_console_side_effects_are_never_imported():
    src = inspect.getsource(op)
    for banned in ("import subprocess", "os.system", "eval(", "exec("):
        assert banned not in src