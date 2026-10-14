"""M7D mutation-sweep killing tests for two SNI DRAFT guard modules.

Targets mutants that survived the existing suite in
research/single_name_intelligence/common/sni_ads_ratio_guard.py and
research/single_name_intelligence/common/sni_identity_binding_guard.py
(sweep record: research/single_name_intelligence/reviews/
MUTATION_SWEEP_M7D_2026-10-14.md). Each test names the exact mutant in its
docstring (file:line, original -> mutated) and kills exactly that mutant;
all pass on unmutated code.

SNI-local DRAFT contract tests. They consume owner-supplied opaque identity
strings (Stock Identity / Data OS) and synthetic depositary-ratio interval
records; they never mint issuer or security ids or ratios.
HISTORICAL-DESCRIPTIVE only: rank_authority, gate_authority, size_authority,
signal_authority, escalation_authority and trade_authority stay literal
False. Fixtures are synthetic.

This module does not register, validate, or feed a ranker, gate, sizer,
signal, escalation, or trade path.
"""
from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMMON = ROOT / "research" / "single_name_intelligence" / "common"
sys.path.insert(0, str(COMMON))

from sni_ads_ratio_guard import (  # noqa: E402
    _as_date,
    _as_datetime,
    _blank,
    check_ads_ratio,
)
from sni_identity_binding_guard import (  # noqa: E402
    _as_date as idb_as_date,
    _as_datetime as idb_as_datetime,
    _available_as_of,
    _id_looks_derived,
    bind_identity,
)

ADS_AS_OF = "2021-06-01T00:00:00+00:00"
ADS_AVAILABLE = "2019-07-10T00:00:00+00:00"

IDB_AS_OF = "2026-08-20T12:00:00+00:00"
IDB_AVAILABLE_AT = "2026-08-20T11:00:00+00:00"


def _ads_later(**overrides):
    """Synthetic open-ended ratio record covering on/after 2019-07-10."""
    rec = {
        "ratio_record_id": "rr-002",
        "issuer_id": "iss-001",
        "ordinary_per_ads": 4,
        "valid_from": "2019-07-10",
        "valid_to": None,
        "source_ref": "src-cs-002",
        "available_at": ADS_AVAILABLE,
    }
    rec.update(overrides)
    return {k: v for k, v in rec.items() if v is not Ellipsis}


def _ads_early(**overrides):
    """Synthetic closed ratio record 2010-01-01..2019-07-10, ratio 8."""
    rec = {
        "ratio_record_id": "rr-001",
        "issuer_id": "iss-001",
        "ordinary_per_ads": 8,
        "valid_from": "2010-01-01",
        "valid_to": "2019-07-10",
        "source_ref": "src-cs-001",
        "available_at": ADS_AVAILABLE,
    }
    rec.update(overrides)
    return {k: v for k, v in rec.items() if v is not Ellipsis}


def _ads_request(**overrides):
    req = {
        "issuer_id": "iss-001",
        "on_date": "2020-01-15",
    }
    req.update(overrides)
    return req


def _idb_request(**overrides):
    body = {
        "listing_id": "SYN-LIST-1",
        "issuer_id": "SYN-ISS-1",
        "currency": "CCC",
        "operation_needs_issuer": True,
    }
    body.update(overrides)
    return body


def _idb_listing(**overrides):
    body = {
        "listing_id": "SYN-LIST-1",
        "security_id": "SYN-SEC-1",
        "currency": "CCC",
        "owner_ref": "SYN-OWNER-LIST-1",
        "available_at": IDB_AVAILABLE_AT,
    }
    body.update(overrides)
    return body


def _idb_security(**overrides):
    body = {
        "security_id": "SYN-SEC-1",
        "issuer_id": "SYN-ISS-1",
        "owner_ref": "SYN-OWNER-SEC-1",
        "available_at": IDB_AVAILABLE_AT,
    }
    body.update(overrides)
    return body


def _idb_issuer(**overrides):
    body = {
        "issuer_id": "SYN-ISS-1",
        "owner_ref": "SYN-OWNER-ISS-1",
        "available_at": IDB_AVAILABLE_AT,
    }
    body.update(overrides)
    return body


# ---------------------------------------------------------------------------
# sni_ads_ratio_guard.py survivors
# ---------------------------------------------------------------------------


def test_m7d_ads_ratio_guard__ack_ids_02():
    """Mutant sni_ads_ratio_guard_02: sni_ads_ratio_guard.py:244
    `_ack_ids` `return ()` -> `return None` (no acknowledged_ratio_changes).

    An unacknowledged window ratio change must report
    RATIO_CHANGE_UNACKNOWLEDGED, never raise TypeError (`in None`).
    """
    req = _ads_request(window_start="2012-06-01")  # no acknowledged_ratio_changes
    verdict = check_ads_ratio(req, [_ads_early(), _ads_later()], as_of=ADS_AS_OF)
    assert verdict.allowed is False, verdict.reasons
    assert "RATIO_CHANGE_UNACKNOWLEDGED" in verdict.reasons, verdict.reasons
    assert verdict.ratio_record_id == "rr-002"


def test_m7d_ads_ratio_guard__as_date_03():
    """Mutant sni_ads_ratio_guard_03: sni_ads_ratio_guard.py:126
    `_as_date` `return date.fromisoformat(text[:10])` -> `return None`.
    """
    assert _as_date("2019-07-10") == date(2019, 7, 10)
    assert _as_date("not-a-date") is None


def test_m7d_ads_ratio_guard__as_datetime_04():
    """Mutant sni_ads_ratio_guard_04: sni_ads_ratio_guard.py:138
    `_as_datetime` `return datetime(parsed.year, ...)` -> `return None`.
    """
    assert _as_datetime("2019-07-10") == datetime(2019, 7, 10)


def test_m7d_ads_ratio_guard__as_date_21():
    """Mutant sni_ads_ratio_guard_21: sni_ads_ratio_guard.py:126
    `text[:10]` -> `text[:11]` (slice constant 10 -> 11 in `_as_date`).
    """
    assert _as_date("2019-07-10T05:00") == date(2019, 7, 10)


def test_m7d_ads_ratio_guard__as_datetime_22():
    """Mutant sni_ads_ratio_guard_22: sni_ads_ratio_guard.py:134
    `if len(text) == 10:` -> `== 11` in `_as_datetime`.
    """
    assert _as_datetime("2019-07-10T") is None
    assert _as_datetime("2019-07-10") == datetime(2019, 7, 10)


def test_m7d_ads_ratio_guard__blank_25():
    """Mutant sni_ads_ratio_guard_25: sni_ads_ratio_guard.py:107
    `_blank` `if value is None: return True` -> `return False`.

    A record whose `source_ref` key is entirely absent is unsourced.
    """
    assert _blank(None) is True
    rec = _ads_later()
    del rec["source_ref"]
    verdict = check_ads_ratio(_ads_request(), [rec], as_of=ADS_AS_OF)
    assert verdict.allowed is False, verdict.reasons
    assert "RATIO_RECORD_UNSOURCED" in verdict.reasons, verdict.reasons


def test_m7d_ads_ratio_guard__covers_day_issuer_hardening():
    """Hardening for the undrawn `_covers_day` issuer-mismatch site
    (sni_ads_ratio_guard.py:221-222; not among the 30 drawn mutants).

    Mutant sni_ads_ratio_guard_26 (line 225 `return False` -> `return True`)
    was re-verified EQUIVALENT instead: line 225 sits under
    `if not ok or start is None:`, which is unreachable-true because the
    preceding `_interval_usable` check already returned False for exactly
    those records -- see the review's equivalence arguments.

    A wrong-issuer record covering on_date is NOT coverage: the verdict
    keeps NO_INTERVAL_COVERS_DATE and carries no ratio record id.
    """
    other = {
        "ratio_record_id": "rr-009",
        "issuer_id": "iss-other",
        "ordinary_per_ads": 8,
        "valid_from": "2010-01-01",
        "valid_to": None,
        "source_ref": "src-cs-009",
        "available_at": ADS_AVAILABLE,
    }
    verdict = check_ads_ratio(_ads_request(), [other], as_of=ADS_AS_OF)
    assert verdict.allowed is False, verdict.reasons
    assert "ISSUER_MISMATCH" in verdict.reasons, verdict.reasons
    assert "NO_INTERVAL_COVERS_DATE" in verdict.reasons, verdict.reasons
    assert verdict.ratio_record_id is None
    assert verdict.ordinary_per_ads is None


# ---------------------------------------------------------------------------
# sni_identity_binding_guard.py survivors
# ---------------------------------------------------------------------------


def test_m7d_identity_binding_guard__as_date_02():
    """Mutant sni_identity_binding_guard_02: sni_identity_binding_guard.py:131
    `_as_date` `return date.fromisoformat(text[:10])` -> `return None`.
    """
    assert idb_as_date("2019-07-10") == date(2019, 7, 10)


def test_m7d_identity_binding_guard__as_datetime_03():
    """Mutant sni_identity_binding_guard_03: sni_identity_binding_guard.py:143
    `_as_datetime` `return datetime(parsed.year, ...)` -> `return None`.
    """
    assert idb_as_datetime("2019-07-10") == datetime(2019, 7, 10)


def test_m7d_identity_binding_guard__available_as_of_04():
    """Mutant sni_identity_binding_guard_04: sni_identity_binding_guard.py:172
    `_available_as_of` missing-side `return False` -> `return None`.

    The refusal is the literal boolean False (falsy-by-contract), not None.
    """
    assert _available_as_of(None, IDB_AS_OF) is False
    assert _available_as_of(IDB_AVAILABLE_AT, None) is False
    assert _available_as_of(IDB_AVAILABLE_AT, IDB_AS_OF) is True


def test_m7d_identity_binding_guard__id_looks_derived_10():
    """Mutant sni_identity_binding_guard_10: sni_identity_binding_guard.py:221
    `_id_looks_derived` empty-needles `return False` -> `return True`.

    A listing without display_code/display_name has no derivation needles;
    a fully consistent bind stays allowed.
    """
    verdict = bind_identity(
        _idb_request(),
        listing=_idb_listing(),
        security=_idb_security(),
        issuer=_idb_issuer(),
        as_of=IDB_AS_OF,
    )
    assert verdict.allowed is True, verdict.reasons
    assert "ID_LOOKS_DERIVED" not in verdict.reasons, verdict.reasons


def test_m7d_identity_binding_guard__opaque_id_11():
    """Mutant sni_identity_binding_guard_11: sni_identity_binding_guard.py:180
    `_opaque_id` `isinstance(value, str) and not _blank(value)` ->
    `... or ...`.

    A non-string or blank listing_id yields verdict.listing_id None, never
    the raw non-opaque value.
    """
    verdict_int = bind_identity(
        _idb_request(),
        listing=_idb_listing(listing_id=12345),
        security=_idb_security(),
        issuer=_idb_issuer(),
        as_of=IDB_AS_OF,
    )
    assert verdict_int.listing_id is None, verdict_int.listing_id
    verdict_blank = bind_identity(
        _idb_request(),
        listing=_idb_listing(listing_id=""),
        security=_idb_security(),
        issuer=_idb_issuer(),
        as_of=IDB_AS_OF,
    )
    assert verdict_blank.listing_id is None, verdict_blank.listing_id


def test_m7d_identity_binding_guard__as_date_18():
    """Mutant sni_identity_binding_guard_18: sni_identity_binding_guard.py:131
    `text[:10]` -> `text[:11]` (slice constant 10 -> 11 in `_as_date`).
    """
    assert idb_as_date("2019-07-10T05:00") == date(2019, 7, 10)


def test_m7d_identity_binding_guard__as_datetime_19():
    """Mutant sni_identity_binding_guard_19: sni_identity_binding_guard.py:139
    `if len(text) == 10:` -> `== 11` in `_as_datetime`.
    """
    assert idb_as_datetime("2019-07-10T") is None
    assert idb_as_datetime("2019-07-10") == datetime(2019, 7, 10)


def test_m7d_identity_binding_guard__id_looks_derived_24():
    """Mutant sni_identity_binding_guard_24: sni_identity_binding_guard.py:218
    `_id_looks_derived` `if listing is None: return False` ->
    `return None`.

    The no-listing answer is the literal boolean False.
    """
    assert _id_looks_derived({}, None, None, None) is False


def test_m7d_identity_binding_guard__as_date_29():
    """Mutant sni_identity_binding_guard_29: sni_identity_binding_guard.py:128
    `len(text) < 10` -> `len(text) < 11` in `_as_date`.

    A full 10-character ISO date still parses.
    """
    assert idb_as_date("2019-07-10") == date(2019, 7, 10)
    assert idb_as_date("2019-07-1") is None
