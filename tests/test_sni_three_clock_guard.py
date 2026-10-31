"""A08 three-clock classifier tests: economic / owner-known / publication stay distinct.

SNI-local DRAFT contract tests. They consume owner-supplied opaque
identity strings and an owner-supplied field map; the field names come
from the owner, the labels come from the caller. They never mint
canonical HK/US issuer or security identifiers. HISTORICAL-DESCRIPTIVE
only: rank_authority, gate_authority, size_authority, signal_authority,
escalation_authority and trade_authority stay literal False. Fixtures
are synthetic.

This module does not register, validate, or feed a ranker, gate, sizer,
signal, escalation, or trade path.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

from sni_three_clock_guard import (  # noqa: E402
    AUTHORITY_FLAGS,
    CLOCKS,
    KINDS,
    LABELS,
    REASONS,
    ThreeClockVerdict,
    classify_clocks,
    refuse_nonfalse_authority,
)

MODULE_PATH = (
    ROOT
    / "research"
    / "single_name_intelligence"
    / "common"
    / "sni_three_clock_guard.py"
)

FLAG_NAMES = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)

FORBIDDEN_TOKENS = (
    "datetime.now",
    "utcnow",
    "date.today",
    "time.time",
    "open(",
)

FORBIDDEN_TICKERS = (
    "BABA",
    "TCEHY",
    "AAPL",
    "MSFT",
    "NVDA",
    "GOOGL",
    "AMZN",
    "META",
    "TSLA",
)

ECON = "2026-06-30"
ECON_DT = "2026-06-30T00:00:00+00:00"
PUB = "2026-07-15T08:30:00+00:00"
KNOWN = "2026-07-10T16:00:00+00:00"
INGESTED = "2026-07-15T17:00:00+00:00"
FILED = "2026-07-15T08:30:00+00:00"
PERIOD_END = "2026-06-30"

# A baseline positive control: an "actual" earnings-shaped record with one
# field per clock. Each test mutates exactly one slot to flip exactly one
# reason.
_BASE_FIELD_MAP = {
    "period_end": "ECONOMIC",
    "filed_at": "PUBLICATION",
    "ingested_at": "OWNER_KNOWN",
}


def _base_record(**overrides):
    rec = {
        "period_end": PERIOD_END,
        "filed_at": FILED,
        "ingested_at": INGESTED,
    }
    rec.update(overrides)
    return rec


def _assert_allowed(verdict: ThreeClockVerdict) -> None:
    assert verdict.allowed is True, verdict
    assert verdict.reasons == (), verdict


def _assert_refused(verdict: ThreeClockVerdict, *codes: str) -> None:
    assert verdict.allowed is False, verdict
    for code in codes:
        assert code in verdict.reasons, (code, verdict.reasons)
    for code in verdict.reasons:
        assert code in REASONS, (code, verdict.reasons)


# ---------------------------------------------------------------------------
# Positive controls
# ---------------------------------------------------------------------------


def test_a08g_positive_actual_earnings():
    record = _base_record()
    verdict = classify_clocks(record, _BASE_FIELD_MAP, kind="actual")
    _assert_allowed(verdict)
    assert verdict.economic == PERIOD_END
    assert verdict.publication == FILED
    assert verdict.owner_known == INGESTED


def test_a08g_positive_estimate_publication_before_economic():
    # A forward estimate: publication lands well before the economic date.
    record = {
        "period_end": "2026-12-31",
        "filed_at": "2026-01-05T08:30:00+00:00",
        "ingested_at": "2026-01-05T16:00:00+00:00",
    }
    verdict = classify_clocks(record, _BASE_FIELD_MAP, kind="estimate")
    _assert_allowed(verdict)


# ---------------------------------------------------------------------------
# Single-flip tests: one REASONS entry per test.
# ---------------------------------------------------------------------------


def test_a08g_field_map_missing_none():
    record = _base_record()
    verdict = classify_clocks(record, None, kind="actual")
    _assert_refused(verdict, "FIELD_MAP_MISSING")
    assert verdict.economic is None
    assert verdict.owner_known is None
    assert verdict.publication is None


def test_a08g_field_map_missing_empty():
    record = _base_record()
    verdict = classify_clocks(record, {}, kind="actual")
    _assert_refused(verdict, "FIELD_MAP_MISSING")
    assert verdict.economic is None


def test_a08g_kind_unknown():
    record = _base_record()
    verdict = classify_clocks(record, _BASE_FIELD_MAP, kind="not_a_kind")
    _assert_refused(verdict, "KIND_UNKNOWN")


def test_a08g_clock_unknown_string():
    field_map = {
        "period_end": "ECONOMIC",
        "filed_at": "PUBLICATION",
        "ingested_at": "GIBBERISH",
    }
    verdict = classify_clocks(_base_record(), field_map, kind="actual")
    _assert_refused(verdict, "CLOCK_UNKNOWN")


def test_a08g_clock_substituted_tuple():
    field_map = {
        "period_end": "ECONOMIC",
        "filed_at": ("PUBLICATION", "OWNER_KNOWN"),
    }
    verdict = classify_clocks(_base_record(), field_map, kind="actual")
    _assert_refused(verdict, "CLOCK_SUBSTITUTED")


def test_a08g_clock_substituted_list():
    field_map = {
        "period_end": "ECONOMIC",
        "filed_at": ["PUBLICATION", "OWNER_KNOWN"],
    }
    verdict = classify_clocks(_base_record(), field_map, kind="actual")
    _assert_refused(verdict, "CLOCK_SUBSTITUTED")


def test_a08g_clock_substituted_set():
    field_map = {
        "period_end": "ECONOMIC",
        "filed_at": {"PUBLICATION", "OWNER_KNOWN"},
    }
    verdict = classify_clocks(_base_record(), field_map, kind="actual")
    _assert_refused(verdict, "CLOCK_SUBSTITUTED")


def test_a08g_clock_substituted_none_value():
    field_map = {
        "period_end": "ECONOMIC",
        "filed_at": None,
    }
    verdict = classify_clocks(_base_record(), field_map, kind="actual")
    _assert_refused(verdict, "CLOCK_SUBSTITUTED")


def test_a08g_clock_field_ambiguous():
    field_map = {
        "period_end": "ECONOMIC",
        "filed_at": "PUBLICATION",
        "extra_filed": "PUBLICATION",
        "ingested_at": "OWNER_KNOWN",
    }
    record = {
        "period_end": PERIOD_END,
        "filed_at": FILED,
        "extra_filed": "2026-07-15T08:30:00+00:00",
        "ingested_at": INGESTED,
    }
    verdict = classify_clocks(record, field_map, kind="actual")
    _assert_refused(verdict, "CLOCK_FIELD_AMBIGUOUS")


def test_a08g_economic_missing():
    field_map = {
        "filed_at": "PUBLICATION",
        "ingested_at": "OWNER_KNOWN",
    }
    record = {
        "filed_at": FILED,
        "ingested_at": INGESTED,
    }
    verdict = classify_clocks(record, field_map, kind="actual")
    _assert_refused(verdict, "ECONOMIC_MISSING")
    assert verdict.economic is None


def test_a08g_owner_known_missing():
    field_map = {
        "period_end": "ECONOMIC",
        "filed_at": "PUBLICATION",
    }
    record = {
        "period_end": PERIOD_END,
        "filed_at": FILED,
    }
    verdict = classify_clocks(record, field_map, kind="actual")
    _assert_refused(verdict, "OWNER_KNOWN_MISSING")
    assert verdict.owner_known is None


def test_a08g_publication_missing():
    field_map = {
        "period_end": "ECONOMIC",
        "ingested_at": "OWNER_KNOWN",
    }
    record = {
        "period_end": PERIOD_END,
        "ingested_at": INGESTED,
    }
    verdict = classify_clocks(record, field_map, kind="actual")
    _assert_refused(verdict, "PUBLICATION_MISSING")
    assert verdict.publication is None


def test_a08g_timestamp_invalid_economic():
    field_map = {
        "period_end": "ECONOMIC",
        "filed_at": "PUBLICATION",
        "ingested_at": "OWNER_KNOWN",
    }
    record = {
        "period_end": "not-a-date",
        "filed_at": FILED,
        "ingested_at": INGESTED,
    }
    verdict = classify_clocks(record, field_map, kind="actual")
    _assert_refused(verdict, "TIMESTAMP_INVALID")


def test_a08g_timestamp_invalid_owner_known_naive():
    field_map = {
        "period_end": "ECONOMIC",
        "filed_at": "PUBLICATION",
        "ingested_at": "OWNER_KNOWN",
    }
    record = {
        "period_end": PERIOD_END,
        "filed_at": FILED,
        "ingested_at": "2026-07-10T16:00:00",
    }
    verdict = classify_clocks(record, field_map, kind="actual")
    _assert_refused(verdict, "TIMESTAMP_INVALID")


def test_a08g_timestamp_invalid_publication():
    field_map = {
        "period_end": "ECONOMIC",
        "filed_at": "PUBLICATION",
        "ingested_at": "OWNER_KNOWN",
    }
    record = {
        "period_end": PERIOD_END,
        "filed_at": 12345,
        "ingested_at": INGESTED,
    }
    verdict = classify_clocks(record, field_map, kind="actual")
    _assert_refused(verdict, "TIMESTAMP_INVALID")


def test_a08g_publication_before_economic_actual():
    field_map = {
        "period_end": "ECONOMIC",
        "filed_at": "PUBLICATION",
        "ingested_at": "OWNER_KNOWN",
    }
    record = {
        "period_end": PERIOD_END,
        "filed_at": "2026-06-29T08:30:00+00:00",
        "ingested_at": INGESTED,
    }
    verdict = classify_clocks(record, field_map, kind="actual")
    _assert_refused(verdict, "PUBLICATION_BEFORE_ECONOMIC")


def test_a08g_publication_before_economic_estimate_allowed():
    field_map = {
        "period_end": "ECONOMIC",
        "filed_at": "PUBLICATION",
        "ingested_at": "OWNER_KNOWN",
    }
    record = {
        "period_end": "2026-12-31",
        "filed_at": "2026-01-05T08:30:00+00:00",
        "ingested_at": "2026-01-05T16:00:00+00:00",
    }
    verdict = classify_clocks(record, field_map, kind="estimate")
    assert "PUBLICATION_BEFORE_ECONOMIC" not in verdict.reasons
    _assert_allowed(verdict)


def test_a08g_owner_known_before_publication():
    field_map = {
        "period_end": "ECONOMIC",
        "filed_at": "PUBLICATION",
        "ingested_at": "OWNER_KNOWN",
    }
    record = {
        "period_end": PERIOD_END,
        "filed_at": "2026-07-15T08:30:00+00:00",
        "ingested_at": "2026-07-15T07:00:00+00:00",
    }
    verdict = classify_clocks(record, field_map, kind="actual")
    _assert_refused(verdict, "OWNER_KNOWN_BEFORE_PUBLICATION")


# ---------------------------------------------------------------------------
# CLOCK_SUBSTITUTED contract: one field, two clocks -> no clock is filled
# from it. The untouched clocks stay MISSING.
# ---------------------------------------------------------------------------


def test_a08g_substituted_field_fills_neither_clock():
    field_map = {
        "period_end": "ECONOMIC",
        "filed_at": ("PUBLICATION", "OWNER_KNOWN"),
    }
    record = {
        "period_end": PERIOD_END,
        "filed_at": FILED,
    }
    verdict = classify_clocks(record, field_map, kind="actual")
    _assert_refused(verdict, "CLOCK_SUBSTITUTED", "OWNER_KNOWN_MISSING", "PUBLICATION_MISSING")
    assert verdict.owner_known is None
    assert verdict.publication is None


def test_a08g_publication_only_owner_known_missing_never_filled():
    field_map = {
        "period_end": "ECONOMIC",
        "filed_at": "PUBLICATION",
    }
    record = {
        "period_end": PERIOD_END,
        "filed_at": FILED,
    }
    verdict = classify_clocks(record, field_map, kind="actual")
    _assert_refused(verdict, "OWNER_KNOWN_MISSING")
    assert verdict.owner_known is None
    assert verdict.publication == FILED


# ---------------------------------------------------------------------------
# SESSION_ANCHOR: a record whose only date-like field is a session anchor
# never satisfies ECONOMIC.
# ---------------------------------------------------------------------------


def test_a08g_session_anchor_only_economic_missing():
    field_map = {
        "anchor_session_date": "SESSION_ANCHOR",
    }
    record = {
        "anchor_session_date": "2026-07-15",
    }
    verdict = classify_clocks(record, field_map, kind="actual")
    _assert_refused(verdict, "ECONOMIC_MISSING", "OWNER_KNOWN_MISSING", "PUBLICATION_MISSING")
    assert verdict.economic is None


def test_a08g_session_anchor_ignored_when_economic_present():
    field_map = {
        "period_end": "ECONOMIC",
        "anchor_session_date": "SESSION_ANCHOR",
        "filed_at": "PUBLICATION",
        "ingested_at": "OWNER_KNOWN",
    }
    record = {
        "period_end": PERIOD_END,
        "anchor_session_date": "2026-07-15",
        "filed_at": FILED,
        "ingested_at": INGESTED,
    }
    verdict = classify_clocks(record, field_map, kind="actual")
    _assert_allowed(verdict)
    assert verdict.economic == PERIOD_END


# ---------------------------------------------------------------------------
# Boundary ordering: equal date allowed; one microsecond / one day earlier
# refused for actual, allowed for estimate; owner_known == publication
# allowed, one microsecond earlier refused.
# ---------------------------------------------------------------------------


def test_a08g_boundary_publication_equal_economic_date():
    field_map = {
        "period_end": "ECONOMIC",
        "filed_at": "PUBLICATION",
        "ingested_at": "OWNER_KNOWN",
    }
    record = {
        "period_end": PERIOD_END,
        "filed_at": "2026-06-30T23:59:59+00:00",
        "ingested_at": INGESTED,
    }
    verdict = classify_clocks(record, field_map, kind="actual")
    _assert_allowed(verdict)


def test_a08g_boundary_publication_one_day_before_actual_refused():
    field_map = {
        "period_end": "ECONOMIC",
        "filed_at": "PUBLICATION",
        "ingested_at": "OWNER_KNOWN",
    }
    record = {
        "period_end": PERIOD_END,
        "filed_at": "2026-06-29T08:30:00+00:00",
        "ingested_at": INGESTED,
    }
    verdict = classify_clocks(record, field_map, kind="actual")
    _assert_refused(verdict, "PUBLICATION_BEFORE_ECONOMIC")


def test_a08g_boundary_publication_one_day_before_estimate_allowed():
    field_map = {
        "period_end": "ECONOMIC",
        "filed_at": "PUBLICATION",
        "ingested_at": "OWNER_KNOWN",
    }
    record = {
        "period_end": "2026-12-31",
        "filed_at": "2026-06-29T08:30:00+00:00",
        "ingested_at": "2026-06-29T16:00:00+00:00",
    }
    verdict = classify_clocks(record, field_map, kind="estimate")
    _assert_allowed(verdict)


def test_a08g_boundary_owner_known_equal_publication():
    field_map = {
        "period_end": "ECONOMIC",
        "filed_at": "PUBLICATION",
        "ingested_at": "OWNER_KNOWN",
    }
    record = {
        "period_end": PERIOD_END,
        "filed_at": "2026-07-15T08:30:00+00:00",
        "ingested_at": "2026-07-15T08:30:00+00:00",
    }
    verdict = classify_clocks(record, field_map, kind="actual")
    _assert_allowed(verdict)


def test_a08g_boundary_owner_known_one_microsecond_before_refused():
    field_map = {
        "period_end": "ECONOMIC",
        "filed_at": "PUBLICATION",
        "ingested_at": "OWNER_KNOWN",
    }
    record = {
        "period_end": PERIOD_END,
        "filed_at": "2026-07-15T08:30:00+00:00",
        "ingested_at": "2026-07-15T08:29:59.999999+00:00",
    }
    verdict = classify_clocks(record, field_map, kind="actual")
    _assert_refused(verdict, "OWNER_KNOWN_BEFORE_PUBLICATION")


def test_a08g_boundary_owner_known_one_microsecond_after_allowed():
    field_map = {
        "period_end": "ECONOMIC",
        "filed_at": "PUBLICATION",
        "ingested_at": "OWNER_KNOWN",
    }
    record = {
        "period_end": PERIOD_END,
        "filed_at": "2026-07-15T08:30:00+00:00",
        "ingested_at": "2026-07-15T08:30:00.000001+00:00",
    }
    verdict = classify_clocks(record, field_map, kind="actual")
    _assert_allowed(verdict)


# ---------------------------------------------------------------------------
# Raw-value pass-through: the verdict's three values are the exact record
# strings (identity, not re-formatted).
# ---------------------------------------------------------------------------


def test_a08g_raw_value_passthrough_identity():
    field_map = {
        "period_end": "ECONOMIC",
        "filed_at": "PUBLICATION",
        "ingested_at": "OWNER_KNOWN",
    }
    record = {
        "period_end": "2026-06-30",
        "filed_at": "2026-07-15T08:30:00+00:00",
        "ingested_at": "2026-07-15T17:00:00+00:00",
    }
    verdict = classify_clocks(record, field_map, kind="actual")
    _assert_allowed(verdict)
    assert verdict.economic is record["period_end"]
    assert verdict.publication is record["filed_at"]
    assert verdict.owner_known is record["ingested_at"]


def test_a08g_raw_value_passthrough_unusual_spacing():
    field_map = {
        "period_end": "ECONOMIC",
        "filed_at": "PUBLICATION",
        "ingested_at": "OWNER_KNOWN",
    }
    econ_raw = "2026-06-30"
    pub_raw = "2026-07-15T08:30:00.000000+00:00"
    known_raw = "2026-07-15T17:00:00.000000+00:00"
    record = {
        "period_end": econ_raw,
        "filed_at": pub_raw,
        "ingested_at": known_raw,
    }
    verdict = classify_clocks(record, field_map, kind="actual")
    _assert_allowed(verdict)
    assert verdict.economic == econ_raw
    assert verdict.publication == pub_raw
    assert verdict.owner_known == known_raw


# ---------------------------------------------------------------------------
# Census field names: each is accepted; none appears in the module source.
# ---------------------------------------------------------------------------


CENSUS_ECONOMIC = (
    "valid_from",
    "valid_to",
    "event_date",
    "period_end",
    "effective_at",
)

CENSUS_OWNER_KNOWN = (
    "as_of",
    "ingested_at",
    "known_at",
    "identity_resolved_as_of",
    "detected_at",
    "observed_at_utc",
)

CENSUS_PUBLICATION = (
    "opener_t_avail_utc",
    "t_avail",
    "filed_at",
    "published_at",
    "announced_at",
    "disclosure_date",
)

CENSUS_ALL = (
    *((name, "ECONOMIC") for name in CENSUS_ECONOMIC),
    *((name, "OWNER_KNOWN") for name in CENSUS_OWNER_KNOWN),
    *((name, "PUBLICATION") for name in CENSUS_PUBLICATION),
)


def _value_for(clock: str) -> str:
    if clock == "ECONOMIC":
        return PERIOD_END
    if clock == "OWNER_KNOWN":
        return INGESTED
    return FILED


def _complement_map(keep: str) -> dict[str, str]:
    """Build a 1-clock-per-row map covering the other two clocks with the
    canonical baseline field names so the row passes the rest of the
    contract."""
    econ = "period_end" if keep != "ECONOMIC" else None
    known = "ingested_at" if keep != "OWNER_KNOWN" else None
    pub = "filed_at" if keep != "PUBLICATION" else None
    out: dict[str, str] = {}
    if econ is not None:
        out[econ] = "ECONOMIC"
    if known is not None:
        out[known] = "OWNER_KNOWN"
    if pub is not None:
        out[pub] = "PUBLICATION"
    return out


@pytest.mark.parametrize("field_name,clock", CENSUS_ALL)
def test_a08g_census_field_names_parametrized(field_name: str, clock: str):
    field_map = _complement_map(clock)
    field_map[field_name] = clock
    record = {
        "period_end": PERIOD_END,
        "filed_at": FILED,
        "ingested_at": INGESTED,
        field_name: _value_for(clock),
    }
    verdict = classify_clocks(record, field_map, kind="actual")
    _assert_allowed(verdict)


@pytest.mark.parametrize("field_name", [name for name, _ in CENSUS_ALL])
def test_a08g_census_field_name_not_in_module_source(field_name: str):
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert field_name not in source, (
        f"census field name {field_name!r} appears in module source; "
        "the module must be driven by the field map only"
    )


# ---------------------------------------------------------------------------
# Authority: refuse_nonfalse_authority raises on True, 0, None, ""; every
# value `is False`; the verdict's authority_flags is AUTHORITY_FLAGS; item
# assignment on the frozen map raises TypeError.
# ---------------------------------------------------------------------------


def test_a08g_authority_flags_frozen_assignment_raises():
    with pytest.raises(TypeError):
        AUTHORITY_FLAGS["rank_authority"] = True


def test_a08g_authority_flags_all_literal_false():
    for name in FLAG_NAMES:
        assert AUTHORITY_FLAGS[name] is False
        assert AUTHORITY_FLAGS[name] is not True


def test_a08g_authority_refuse_nonfalse_signature():
    refuse_nonfalse_authority()
    refuse_nonfalse_authority(AUTHORITY_FLAGS)
    refuse_nonfalse_authority(dict(AUTHORITY_FLAGS))
    with pytest.raises(ValueError):
        refuse_nonfalse_authority({"rank_authority": True})
    with pytest.raises(ValueError):
        refuse_nonfalse_authority({"rank_authority": 0})
    with pytest.raises(ValueError):
        refuse_nonfalse_authority({"gate_authority": None})
    with pytest.raises(ValueError):
        refuse_nonfalse_authority({"size_authority": ""})
    for name in FLAG_NAMES:
        with pytest.raises(ValueError):
            refuse_nonfalse_authority({name: True})


def test_a08g_authority_verdict_flags_property():
    verdict = classify_clocks(_base_record(), _BASE_FIELD_MAP, kind="actual")
    assert verdict.authority_flags is AUTHORITY_FLAGS
    for name in FLAG_NAMES:
        assert verdict.authority_flags[name] is False


# ---------------------------------------------------------------------------
# Static scan: every REASONS string appears; forbidden tickers, wall-clock
# names, and open() do not appear; no HK-stock code regex match.
# ---------------------------------------------------------------------------


def test_a08g_static_scan_module():
    source = MODULE_PATH.read_text(encoding="utf-8")
    for code in REASONS:
        assert code in source, f"REASONS entry {code!r} missing from module source"
    for token in FORBIDDEN_TOKENS:
        assert token not in source, f"forbidden token {token!r} in module source"
    for ticker in FORBIDDEN_TICKERS:
        assert ticker not in source, f"forbidden ticker {ticker!r} in module source"
    assert not re.search(r"\b\d{4,5}\.HK\b", source), "HK stock-code regex matched"
    tree = ast.parse(source)
    fn_names = {
        n.name
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "classify_clocks" in fn_names
    # every wall-clock constructor call is banned
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            if attr in ("now", "utcnow", "today"):
                raise AssertionError(
                    f"wall-clock call {attr} at line {node.lineno}"
                )


# ---------------------------------------------------------------------------
# De-dup and order: an input that triggers at least three reasons returns
# them in REASONS order with no duplicates.
# ---------------------------------------------------------------------------


def test_a08g_dedup_order_three_reasons():
    field_map = {
        "period_end": "ECONOMIC",
        "filed_at": ("PUBLICATION", "OWNER_KNOWN"),  # CLOCK_SUBSTITUTED
    }
    record = {
        "period_end": "not-a-date",  # TIMESTAMP_INVALID
    }
    verdict = classify_clocks(record, field_map, kind="not_a_kind")  # KIND_UNKNOWN
    reasons = verdict.reasons
    assert "KIND_UNKNOWN" in reasons
    assert "CLOCK_SUBSTITUTED" in reasons
    assert "TIMESTAMP_INVALID" in reasons
    assert len(reasons) == len(set(reasons)), reasons
    # The three named reasons must be in REASONS order relative to each
    # other (KIND_UNKNOWN < CLOCK_SUBSTITUTED < TIMESTAMP_INVALID).
    named = [r for r in reasons if r in ("KIND_UNKNOWN", "CLOCK_SUBSTITUTED", "TIMESTAMP_INVALID")]
    assert named == sorted(named, key=REASONS.index), named
    # And every reason must keep its position in REASONS.
    indices = [REASONS.index(r) for r in reasons]
    assert indices == sorted(indices), reasons


def test_a08g_dedup_no_duplicate_when_multiple_kinds():
    # Same reason triggered twice (via two substituted fields) still
    # surfaces once.
    field_map = {
        "period_end": "ECONOMIC",
        "filed_at": ("PUBLICATION", "OWNER_KNOWN"),
        "published_at": ("PUBLICATION", "OWNER_KNOWN"),
    }
    record = {
        "period_end": PERIOD_END,
        "filed_at": FILED,
        "published_at": FILED,
    }
    verdict = classify_clocks(record, field_map, kind="actual")
    assert verdict.reasons.count("CLOCK_SUBSTITUTED") == 1


# ---------------------------------------------------------------------------
# Adversarial id cases: trailing space, case change, Cyrillic look-alike.
# These rely on the field map being caller-supplied; the module does not
# normalise the record values, so a mismatched record value vs field map
# is a TIMESTAMP_INVALID refusal.
# ---------------------------------------------------------------------------


def test_a08g_adversarial_trailing_space_in_value():
    field_map = {
        "period_end": "ECONOMIC",
        "filed_at": "PUBLICATION",
        "ingested_at": "OWNER_KNOWN",
    }
    record = {
        "period_end": "2026-06-30 ",
        "filed_at": FILED,
        "ingested_at": INGESTED,
    }
    verdict = classify_clocks(record, field_map, kind="actual")
    _assert_refused(verdict, "TIMESTAMP_INVALID")


def test_a08g_adversarial_case_change_in_value():
    field_map = {
        "period_end": "ECONOMIC",
        "filed_at": "PUBLICATION",
        "ingested_at": "OWNER_KNOWN",
    }
    # The field map says "filed_at"; the record uses uppercase "FILED_AT".
    # The module never case-folds; the field is absent and PUBLICATION
    # stays MISSING.
    record = {
        "period_end": PERIOD_END,
        "FILED_AT": FILED,
        "ingested_at": INGESTED,
    }
    verdict = classify_clocks(record, field_map, kind="actual")
    _assert_refused(verdict, "PUBLICATION_MISSING")
    assert verdict.publication is None


def test_a08g_adversarial_cyrillic_lookalike_offset():
    # The Cyrillic "а" U+0430 is a homograph of the Latin "a". The module
    # treats it as a non-string offset and refuses.
    field_map = {
        "period_end": "ECONOMIC",
        "filed_at": "PUBLICATION",
        "ingested_at": "OWNER_KNOWN",
    }
    cyrillic_offset = "2026-07-10T16:00:00+а00:00"
    record = {
        "period_end": PERIOD_END,
        "filed_at": FILED,
        "ingested_at": cyrillic_offset,
    }
    verdict = classify_clocks(record, field_map, kind="actual")
    _assert_refused(verdict, "TIMESTAMP_INVALID")


# ---------------------------------------------------------------------------
# Frozen spec: REASONS / CLOCKS / LABELS / KINDS tuples are stable.
# ---------------------------------------------------------------------------


def test_a08g_frozen_reasons_tuple():
    assert REASONS == (
        "FIELD_MAP_MISSING",
        "KIND_UNKNOWN",
        "CLOCK_UNKNOWN",
        "CLOCK_SUBSTITUTED",
        "CLOCK_FIELD_AMBIGUOUS",
        "ECONOMIC_MISSING",
        "OWNER_KNOWN_MISSING",
        "PUBLICATION_MISSING",
        "TIMESTAMP_INVALID",
        "PUBLICATION_BEFORE_ECONOMIC",
        "OWNER_KNOWN_BEFORE_PUBLICATION",
    )
    assert len(REASONS) == len(set(REASONS))
    for code in REASONS:
        assert isinstance(code, str)


def test_a08g_frozen_clock_constants():
    assert CLOCKS == ("ECONOMIC", "OWNER_KNOWN", "PUBLICATION")
    assert LABELS == (
        "ECONOMIC",
        "OWNER_KNOWN",
        "PUBLICATION",
        "SESSION_ANCHOR",
    )
    assert KINDS == ("actual", "estimate")
