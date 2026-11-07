"""X9 guard red-team after the FAMILY TEXT RULE v2 rewrites (INT7).

SNI-local DRAFT contract tests. They consume owner-supplied opaque identity
strings (Stock Identity / Data OS) and never mint issuer or security ids.
HISTORICAL-DESCRIPTIVE only: rank_authority, gate_authority, size_authority,
signal_authority, escalation_authority and trade_authority stay literal
False. Fixtures are synthetic.

This module pins the repaired behaviour for each X9 finding (currency `!=`
on absent values; `level` unhashable raised; `issuer_id` Python-equality
collisions; `_pair_shape_ok` admitted whitespace). X9-02 was closed by the
JGP-01 join-guard fix; X9-01/03/04/05 by FAMILY TEXT RULE v2 equality
(only between two text-present values). Each plain PIN test asserts an
attack the guards refute and must keep refuting.

This module does not register, validate, or feed a ranker, gate, sizer,
signal, escalation, or trade path.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

# ---------------------------------------------------------------------------
# Imports — one sym-path insert per module, no sys.modules mutation. Each
# import mirrors the existing per-guard test files in this lane.
# ---------------------------------------------------------------------------

from sni_identity_binding_guard import (  # noqa: E402
    bind_identity,
)

from sni_join_guard import (  # noqa: E402
    validate_fact,
    REASONS as JOIN_REASONS,
)

from sni_ads_ratio_guard import (  # noqa: E402
    check_ads_ratio,
    REASONS as ADS_REASONS,
)

from sni_counter_relation_guard import (  # noqa: E402
    check_counter_relation,
    REASONS as CR_REASONS,
)

from sni_class_duplicate_guard import (  # noqa: E402
    _pair_shape_ok,
)

# ---------------------------------------------------------------------------
# X9-01 — identity_binding currency bare `!=`
# ---------------------------------------------------------------------------


def _identity_bind_inputs(currency_request, currency_listing):
    """Shared shape for the bind_identity currency negative."""
    as_of = "2026-08-20T12:00:00+00:00"
    av = "2026-08-20T11:00:00+00:00"
    return dict(
        request={"listing_id": "SYN-LIST-1",
                 "issuer_id": "SYN-ISS-1",
                 "currency": currency_request,
                 "operation_needs_issuer": True},
        listing={"listing_id": "SYN-LIST-1",
                 "security_id": "SYN-SEC-1",
                 "currency": currency_listing,
                 "owner_ref": "O", "available_at": av,
                 "display_code": "D", "display_name": "Name"},
        security={"security_id": "SYN-SEC-1",
                  "issuer_id": "SYN-ISS-1",
                  "owner_ref": "O", "available_at": av},
        issuer={"issuer_id": "SYN-ISS-1",
                "owner_ref": "O", "available_at": av},
        as_of=as_of,
    )


def test_x9_01_identity_binding_currency_untext_equal() -> None:
    """Both currencies must be text-present for the equality check to apply.

    Per FAMILY TEXT RULE v2: 'Equality is checked only between two
    present values.' Two ABSENT currencies must refuse; today the guard
    says they match.
    """
    inputs = _identity_bind_inputs(None, None)
    v = bind_identity(**inputs)
    assert "CURRENCY_MISMATCH" in v.reasons, (
        f"expected CURRENCY_MISMATCH for two ABSENT currencies, got {v.reasons}"
    )


def test_x9_01b_identity_binding_currency_bool_int_equal() -> None:
    """`True == 1` collision under Python equality must be refused."""
    inputs = _identity_bind_inputs(True, 1)
    v = bind_identity(**inputs)
    assert "CURRENCY_MISMATCH" in v.reasons, (
        f"True and 1 are NOT text-present values; got {v.reasons}"
    )


# ---------------------------------------------------------------------------
# X9-02 — join_guard level raises TypeError on unhashable
# ---------------------------------------------------------------------------


_BASE_FACT = dict(
    issuer_id="SYN-ISSUER-1", level="issuer", metric="net_income",
    period_type="annual", period_start="2025-04-01",
    period_end="2026-03-31", basis="reported", currency="USD",
    source_reported_currency="USD", scale=1, segment="seg-1",
    segment_scheme_version="v1", share_denominator="ORD",
    ads_ratio=1.0, version="1", supersedes=None,
    known_at="2026-04-01T00:00:00+00:00", source_owner="src",
    value=100,
)


def test_x9_02_join_guard_level_unhashable_raises() -> None:
    """`level=["issuer"]` must not raise; today it raises TypeError."""
    bad = {**_BASE_FACT, "level": ["issuer"]}
    out = validate_fact(bad)
    assert "LEVEL_UNKNOWN" in out, (
        f"unhashable level must surface as LEVEL_UNKNOWN, got {out}"
    )


# ---------------------------------------------------------------------------
# X9-03 — ads_ratio issuer_id bare equality
# ---------------------------------------------------------------------------


def _ads_inputs(request_issuer, rec_issuer):
    """Shared shape for the ads_ratio issuer_id negative."""
    return dict(
        request={"issuer_id": request_issuer, "on_date": "2015-01-15"},
        records=[{"ratio_record_id": "rr-1",
                  "issuer_id": rec_issuer,
                  "ordinary_per_ads": 8,
                  "valid_from": "2010-01-01", "valid_to": None,
                  "source_ref": "src",
                  "available_at": "2019-07-10T00:00:00+00:00"}],
        as_of="2021-06-01T00:00:00+00:00",
    )


def test_x9_03_ads_ratio_issuer_id_untext_equal() -> None:
    """`request.issuer_id=1 (int)` and `rec.issuer_id=1 (int)` are NOT
    text-present; today the guard lets the cover match silently."""
    v = check_ads_ratio(**_ads_inputs(1, 1))
    assert "ISSUER_MISMATCH" in v.reasons, (
        f"expected ISSUER_MISMATCH for two non-text issuers, got {v.reasons}"
    )


# ---------------------------------------------------------------------------
# X9-04 — counter_relation issuer_id bare equality
# ---------------------------------------------------------------------------


def _cr_inputs(req_issuer, rel_issuer):
    return dict(
        request={"issuer_id": req_issuer,
                 "left_listing_id": "SYN-LISTING-a1",
                 "right_listing_id": "SYN-LISTING-b1"},
        relations=({"relation_id": "SYN-REL-1",
                    "issuer_id": rel_issuer,
                    "source_ref": "SYN-SRC-1",
                    "available_at": "2026-05-01T00:00:00+00:00",
                    "members": (
                        {"listing_id": "SYN-LISTING-a1",
                         "counter_kind": "ordinary",
                         "currency": "HKD"},
                        {"listing_id": "SYN-LISTING-b1",
                         "counter_kind": "ads",
                         "currency": "USD"}),},),
        as_of="2026-06-01T00:00:00+00:00",
    )


def test_x9_04_counter_relation_issuer_id_untext_equal() -> None:
    """`True == 1` issuer_id collision must refuse with ISSUER_MISMATCH."""
    v = check_counter_relation(**_cr_inputs(True, 1))
    assert "ISSUER_MISMATCH" in v.reasons, (
        f"expected ISSUER_MISMATCH for True/1 collision, got {v.reasons}"
    )


# ---------------------------------------------------------------------------
# X9-05 — class_duplicate _pair_shape_ok accepts whitespace
# ---------------------------------------------------------------------------


def test_x9_05_pair_shape_ok_accepts_whitespace() -> None:
    """`_pair_shape_ok((" ", "X"))` must be False; today it's True.

    The helper's docstring promises "exactly two distinct non-blank
    strings"; whitespace-only sids are not blank under FAMILY TEXT
    RULE v2 but `_blank` only catches `None` / `""`.
    """
    assert _pair_shape_ok((" ", "X")) is False


# ---------------------------------------------------------------------------
# Plain PIN tests for probes that held (each must PASS today; if a future
# change breaks one, the seat sees a real regression).
# ---------------------------------------------------------------------------


def test_x9_pin_join_level_int_one_unknown() -> None:
    """`level=1` (int) is correctly refused as LEVEL_UNKNOWN, no raise."""
    bad = {**_BASE_FACT, "level": 1}
    out = validate_fact(bad)
    assert "LEVEL_UNKNOWN" in out


def test_x9_pin_join_level_blank_unknown() -> None:
    """`level=""` (blank) is correctly refused as LEVEL_UNKNOWN."""
    bad = {**_BASE_FACT, "level": ""}
    out = validate_fact(bad)
    assert "LEVEL_UNKNOWN" in out


def test_x9_pin_ads_issuer_mismatch_str_int() -> None:
    """`request.issuer_id='SYN-1'` (str) vs `rec.issuer_id=1` (int) is
    correctly refused (mixed-type issuers are never equal in `==`)."""
    v = check_ads_ratio(**_ads_inputs("SYN-1", 1))
    assert "ISSUER_MISMATCH" in v.reasons


def test_x9_pin_cr_issuer_mismatch_str_int() -> None:
    """Symmetric to above for counter_relation."""
    v = check_counter_relation(**_cr_inputs("SYN-1", 1))
    assert "ISSUER_MISMATCH" in v.reasons


def test_x9_pin_ads_issuer_match_str_str_allowed() -> None:
    """The canonical positive: both issuer_ids are real strings."""
    v = check_ads_ratio(**_ads_inputs("SYN-1", "SYN-1"))
    # Today's positive result is allowed; no ISSUER_MISMATCH.
    assert "ISSUER_MISMATCH" not in v.reasons


def test_x9_pin_join_unhashable_dict_level() -> None:
    """`level={}` (dict) must also surface as LEVEL_UNKNOWN, never raise."""
    bad = {**_BASE_FACT, "level": {}}
    # JGP-01 gates membership on isinstance(str), so this refuses, never raises.
    out = validate_fact(bad)
    assert "LEVEL_UNKNOWN" in out


def test_x9_pin_identity_binding_currency_match_str_str() -> None:
    """Sanity: two present equal currencies must NOT refuse."""
    inputs = _identity_bind_inputs("USD", "USD")
    v = bind_identity(**inputs)
    assert "CURRENCY_MISMATCH" not in v.reasons
