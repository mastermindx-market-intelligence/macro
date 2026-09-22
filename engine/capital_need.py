"""Compose the bounded issuer capital-need read model.

This module is deliberately a pure adapter over the existing
``debt_maturity.v1`` and ``cash_runway.v1`` producer outputs.  It does not
load facts, infer issuer identity from a ticker, estimate financing access, or
turn investor-held bond par into issuer debt.  The only combined arithmetic is
cash on hand versus the next-12-month principal bucket when both producer
outputs describe the same canonical CIK and exact filing period.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from typing import Any, Mapping


_COMBINABLE_STATUSES = frozenset({"reported"})
_ISSUER_SCOPES = frozenset({"issuer", "issuer_reported", "consolidated"})
_PERIOD_KEYS = ("accn", "end", "form", "fp", "fy")


def _canonical_cik(value: object) -> str | None:
    raw = str(value or "").strip()
    if not raw.isdigit() or len(raw) > 10 or int(raw) == 0:
        return None
    return raw.zfill(10)


def _iso(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _period(block: Mapping[str, Any] | None) -> dict[str, Any] | None:
    raw = (block or {}).get("period")
    return deepcopy(raw) if isinstance(raw, Mapping) else None


def _period_key(period: Mapping[str, Any] | None) -> tuple[Any, ...] | None:
    if not period or any(period.get(key) in (None, "") for key in _PERIOD_KEYS):
        return None
    return tuple(period.get(key) for key in _PERIOD_KEYS)


def _same_period(left: Mapping[str, Any] | None, right: Mapping[str, Any] | None) -> bool:
    left_key = _period_key(left)
    right_key = _period_key(right)
    return left_key is not None and left_key == right_key


def _filed_after_as_of(period: Mapping[str, Any] | None, as_of: object) -> bool:
    """Return true when a filing is not available at the requested cutoff."""
    if not period or as_of is None or not period.get("filed"):
        return False
    try:
        filed = date.fromisoformat(str(period["filed"]))
        cutoff = as_of.date() if isinstance(as_of, datetime) else as_of
        if isinstance(cutoff, str):
            cutoff = date.fromisoformat(cutoff)
        return isinstance(cutoff, date) and filed > cutoff
    except (TypeError, ValueError):
        return True


def _empty_result(
    *,
    status: str,
    cik: str | None,
    issuer_id: str | None,
    security_id: str | None,
    as_of: object,
    reasons: list[str],
) -> dict[str, Any]:
    return {
        "schema": "capital_need.v1",
        "version": 1,
        "status": status,
        "issuer": {
            "issuer_id": issuer_id,
            "security_id": security_id,
            "cik": cik,
            "scope": "issuer",
        },
        "as_of": _iso(as_of),
        "coverage": {"state": status, "reasons": reasons},
        "reported": {
            "debt_due": None,
            "cash": None,
            "operating_cash_flow": None,
            "capex": None,
        },
        "derived": {
            "free_cash_flow": None,
            "scenario_runway": None,
            "near_term_cash_cover": None,
            "near_term_cash_gap_usd": None,
        },
        "authority": {"class": "context_only", "display_only": True},
        "source_clock": {"as_of": _iso(as_of)},
    }


def _source_scope(block: Mapping[str, Any]) -> str:
    scope = block.get("scope") or block.get("source_scope")
    return str(scope or "issuer_reported")


def _fact_view(
    block: Mapping[str, Any],
    *,
    value_key: str,
    basis: str,
    state: str = "observed",
) -> dict[str, Any]:
    period = _period(block)
    return {
        "state": state,
        "value": block.get(value_key) if state == "observed" else None,
        "unit": "USD",
        "currency": "USD",
        "basis": basis,
        "period": period,
        "scope": _source_scope(block),
        "source_schema": block.get("schema"),
        "source_as_of": block.get("as_of"),
    }


def _debt_view(debt: Mapping[str, Any], *, available: bool = True) -> dict[str, Any]:
    buckets = []
    for bucket in debt.get("buckets") or []:
        reported = bool(bucket.get("reported")) and available
        buckets.append(
            {
                "key": bucket.get("key"),
                "value": bucket.get("usd") if reported else None,
                "unit": "USD",
                "currency": "USD",
                "state": "observed" if reported else "unknown",
                "drop_reason": bucket.get("drop_reason"),
                "tag": bucket.get("tag"),
            }
        )
    return {
        "state": "observed" if debt.get("status") == "reported" and available else "unknown",
        "unit": debt.get("unit") or "USD",
        "currency": "USD",
        "period": _period(debt),
        "scope": _source_scope(debt),
        "issuer_debt_outstanding_only": True,
        "buckets": buckets,
        "total_reported_usd": debt.get("total_reported_usd") if available else None,
        "source_schema": debt.get("schema"),
        "source_as_of": debt.get("as_of"),
    }


def assemble_capital_need(
    debt_maturity: Mapping[str, Any] | None,
    cash_runway: Mapping[str, Any] | None,
    *,
    issuer_id: str | None = None,
    security_id: str | None = None,
    as_of: object = None,
) -> dict[str, Any]:
    """Build a conservative capital-need view from two existing read models.

    A combined result is complete only when both blocks are reported for the
    same CIK and exact annual filing identity.  A valid cash-flow scenario may
    still be exposed when the debt block is missing, but all coverage and
    funding-gap fields stay null.  This is intentionally a read model: the
    result carries no financing forecast, recommendation, rank, or authority
    to act.
    """
    debt = debt_maturity or {}
    cash = cash_runway or {}
    debt_cik = _canonical_cik(debt.get("cik"))
    cash_cik = _canonical_cik(cash.get("cik"))
    cik = debt_cik or cash_cik
    base = _empty_result(
        status="unknown",
        cik=cik,
        issuer_id=issuer_id,
        security_id=security_id,
        as_of=as_of,
        reasons=[],
    )
    reasons: list[str] = []

    if debt.get("status") == "not_applicable" or cash.get("status") == "not_applicable":
        return _empty_result(
            status="not_applicable",
            cik=None,
            issuer_id=issuer_id,
            security_id=security_id,
            as_of=as_of,
            reasons=["issuer_not_applicable"],
        )

    if debt_cik and cash_cik and debt_cik != cash_cik:
        return _empty_result(
            status="identity_mismatch",
            cik=None,
            issuer_id=issuer_id,
            security_id=security_id,
            as_of=as_of,
            reasons=["debt_cash_cik_mismatch"],
        )
    if not cik:
        reasons.append("issuer_cik_unknown")

    for label, block in (("debt", debt), ("cash", cash)):
        if not block:
            reasons.append(f"{label}_missing")
            continue
        if _source_scope(block) not in _ISSUER_SCOPES:
            reasons.append(f"{label}_investor_held_scope_rejected")
        if block.get("status") == "identity_mismatch":
            reasons.append(f"{label}_identity_mismatch")

    debt_scope_ok = _source_scope(debt) in _ISSUER_SCOPES if debt else False
    cash_scope_ok = _source_scope(cash) in _ISSUER_SCOPES if cash else False
    cash_period = _period(cash)
    debt_period = _period(debt)
    debt_pit_valid = not _filed_after_as_of(debt_period, as_of)
    cash_pit_valid = not _filed_after_as_of(cash_period, as_of)
    if debt and debt_scope_ok:
        base["reported"]["debt_due"] = _debt_view(debt, available=debt_pit_valid)
    if cash and cash_scope_ok:
        cash_state = (
            "observed"
            if cash.get("status") == "reported" and cash_pit_valid
            else "unknown"
        )
        base["reported"]["cash"] = _fact_view(
            cash, value_key="cash_usd", basis="instant", state=cash_state
        )
        base["reported"]["operating_cash_flow"] = _fact_view(
            cash, value_key="ocf_usd", basis="duration", state=cash_state
        )
        base["reported"]["capex"] = _fact_view(
            cash, value_key="capex_usd", basis="duration", state=cash_state
        )

    cash_reported = cash.get("status") in _COMBINABLE_STATUSES and cash_scope_ok
    debt_reported = debt.get("status") in _COMBINABLE_STATUSES and debt_scope_ok
    exact_period = _same_period(debt_period, cash_period)
    if debt and cash and not exact_period:
        reasons.append("debt_cash_period_mismatch")
    if debt and debt.get("unit") not in (None, "USD"):
        reasons.append("debt_unit_unknown")
    if cash and cash_reported and (cash.get("period") or {}).get("stale"):
        reasons.append("cash_period_stale")
    if debt and debt_reported and (debt.get("period") or {}).get("stale"):
        reasons.append("debt_period_stale")
    if not debt_pit_valid:
        reasons.append("debt_filed_after_as_of")
    if not cash_pit_valid:
        reasons.append("cash_filed_after_as_of")

    # Preserve the already bounded cash-flow scenario as a scenario, never as
    # a reported financing fact.  A stale filing remains visible but is marked
    # stale so the panel cannot present it as current coverage.
    if cash_reported and cash_pit_valid:
        base["derived"]["free_cash_flow"] = {
            "state": "derived",
            "value": cash.get("free_cash_flow_usd"),
            "unit": "USD",
            "currency": "USD",
            "formula": "operating_cash_flow - capex_outflow",
            "period": cash_period,
        }
        scenario_state = "stale" if cash_period and cash_period.get("stale") else "scenario"
        base["derived"]["scenario_runway"] = {
            "state": scenario_state,
            "value_months": cash.get("runway_months"),
            "unit": "months" if cash.get("runway_months") is not None else None,
            "display": cash.get("runway_display"),
            "annual_burn_usd": cash.get("annual_burn_usd"),
            "monthly_burn_usd": cash.get("monthly_burn_usd"),
            "assumptions": {
                "annual_filing_only": True,
                "no_refinancing_forecast": True,
                "issuer_debt_payments_included": False,
            },
            "excludes": [
                "financing_access",
                "restricted_cash",
                "investor_held_par",
                "valuation",
                "covenant",
                "trade_recommendation",
            ],
        }
    elif cash_reported:
        reasons.append("cash_source_unavailable_at_as_of")
    else:
        reasons.append("cash_flow_scenario_unavailable")

    y1 = None
    if debt_reported:
        y1 = next((b for b in debt.get("buckets") or [] if b.get("key") == "y1"), None)
    same_period_fresh = (
        debt_reported
        and cash_reported
        and debt_pit_valid
        and cash_pit_valid
        and exact_period
        and not (debt_period or {}).get("stale")
        and not (cash_period or {}).get("stale")
    )
    if same_period_fresh and y1 and y1.get("reported") and y1.get("usd") is not None:
        y1_usd = y1["usd"]
        cash_usd = cash.get("cash_usd")
        if y1_usd and cash_usd is not None:
            cover = round(100 * cash_usd / y1_usd)
            base["derived"]["near_term_cash_cover"] = {
                "state": "derived",
                "value_pct": cover,
                "formula": "cash / y1_debt_due * 100",
                "period": cash_period,
            }
            base["derived"]["near_term_cash_gap_usd"] = max(y1_usd - cash_usd, 0)
        else:
            reasons.append("y1_debt_zero_or_cash_unknown")
    else:
        reasons.append("near_term_cover_requires_exact_fresh_period")

    if debt_reported and cash_reported and exact_period and not reasons:
        status = "complete"
    elif reasons and (debt_reported or cash_reported):
        status = "partial"
    else:
        status = "unknown"
    base["status"] = status
    base["coverage"] = {"state": status, "reasons": reasons}
    base["source_clock"] = {
        "as_of": _iso(as_of),
        "debt_as_of": debt.get("as_of"),
        "cash_as_of": cash.get("as_of"),
        "debt_filed": debt_period.get("filed") if debt_period else None,
        "cash_filed": cash_period.get("filed") if cash_period else None,
    }
    return base
