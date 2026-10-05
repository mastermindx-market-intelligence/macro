"""Cycle Capture funding and original-equity transmission.

Pure, network-free consumer over existing source-qualified finance facts.

This module answers a narrower question than a stock score:

    Can the issuer reach the assumed recovery date under the supplied funding
    path, and if the business recovers, what value reaches the original common
    shareholder after financing and claim changes?

It deliberately does NOT collect filings, infer financing availability, estimate
probabilities, rank candidates, size positions, create trades, or splice a
replacement security into the historical return of a cancelled security.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from math import isclose, isfinite
from typing import Any, Mapping, Sequence

SCHEMA = "prophet.cycle_equity_case/v1"
FUNDING_PATH_SCHEMA = "prophet.cycle_funding_path/v1"
RECOVERY_SCHEMA = "prophet.cycle_equity_recovery/v1"
INVENTORY_SALES_SCHEMA = "prophet.cycle_inventory_sales_diagnostic/v1"

_AUTHORITY = {
    "rank_authority": False,
    "entry_authority": False,
    "sizing_authority": False,
    "trade_authority": False,
    "policy_authority": False,
}

_EVENT_KINDS = frozenset({
    "operating_cash_change",
    "cash_obligation",
    "restricted_cash_release",
    "equity_raise",
    "debt_draw",
    "debt_repayment",
    "debt_conversion",
})

_EVENT_STATUS = frozenset({"observed", "scenario_assumption"})
_RESTRICTED_STATES = frozenset({"observed", "not_applicable", "unknown"})


class CycleEquityError(ValueError):
    """A requested Cycle equity calculation would change or overstate meaning."""


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CycleEquityError(name)
    return value.strip()


def _number(value: Any, name: str, *, nonnegative: bool = False, positive: bool = False) -> float:
    if isinstance(value, bool) or value is None:
        raise CycleEquityError(name)
    try:
        out = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise CycleEquityError(name) from exc
    if not isfinite(out):
        raise CycleEquityError(name)
    if nonnegative and out < 0:
        raise CycleEquityError(name)
    if positive and out <= 0:
        raise CycleEquityError(name)
    return out


def _utc(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise CycleEquityError(name)
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CycleEquityError(name) from exc
    if dt.tzinfo is None:
        raise CycleEquityError(name)
    return dt.astimezone(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _false_authority(value: Mapping[str, Any], name: str) -> None:
    authority = value.get("authority")
    if not isinstance(authority, Mapping):
        raise CycleEquityError(f"{name}_authority_missing")
    for key, enabled in authority.items():
        if key.endswith("authority") and enabled is not False:
            raise CycleEquityError(f"{name}_authority_escalation")
    if authority.get("class") not in (None, "context_only"):
        raise CycleEquityError(f"{name}_authority_escalation")


def _capital_need(capital_need: Mapping[str, Any], *, issuer_id: str, security_id: str) -> dict[str, Any]:
    if not isinstance(capital_need, Mapping) or capital_need.get("schema") != "capital_need.v1":
        raise CycleEquityError("capital_need_v1_required")
    _false_authority(capital_need, "capital_need")
    issuer = capital_need.get("issuer")
    if not isinstance(issuer, Mapping):
        raise CycleEquityError("capital_need_issuer_missing")
    if issuer.get("issuer_id") not in (None, issuer_id):
        raise CycleEquityError("capital_need_issuer_mismatch")
    if issuer.get("security_id") not in (None, security_id):
        raise CycleEquityError("capital_need_security_mismatch")

    reported = capital_need.get("reported")
    if not isinstance(reported, Mapping):
        raise CycleEquityError("capital_need_reported_missing")
    cash = reported.get("cash")
    debt = reported.get("debt_due")
    cash_value = None
    debt_value = None
    debt_complete = False
    if isinstance(cash, Mapping) and cash.get("state") == "observed":
        cash_value = _number(cash.get("value"), "capital_need_cash_invalid", nonnegative=True)
    if isinstance(debt, Mapping) and debt.get("state") == "observed":
        debt_value = _number(debt.get("total_reported_usd"), "capital_need_debt_invalid", nonnegative=True)
        debt_complete = debt.get("ladder_complete") is True

    status = capital_need.get("status")
    if status not in {"complete", "partial", "unknown"}:
        raise CycleEquityError("capital_need_status_invalid")
    coverage = capital_need.get("coverage")
    reasons = []
    if isinstance(coverage, Mapping) and isinstance(coverage.get("reasons"), list):
        reasons = [str(x) for x in coverage["reasons"]]

    return {
        "status": status,
        "cash": cash_value,
        "debt": debt_value,
        "debt_ladder_complete": debt_complete,
        "coverage_reasons": reasons,
        "source_clock": deepcopy(dict(capital_need.get("source_clock") or {})),
    }


def _share_count(observation: Mapping[str, Any], *, issuer_id: str, decision: datetime) -> dict[str, Any]:
    if not isinstance(observation, Mapping):
        raise CycleEquityError("share_count_observation_required")
    schema = observation.get("schema")
    if schema not in {
        "capital_structure.share_count_observation.v1",
        "capital_structure.share_count_observation.v2",
    }:
        raise CycleEquityError("share_count_observation_schema_invalid")
    if observation.get("issuer_id") != issuer_id:
        raise CycleEquityError("share_count_issuer_mismatch")
    metric = observation.get("metric")
    if not isinstance(metric, Mapping) or metric.get("kind") != "common_shares_outstanding":
        raise CycleEquityError("common_share_count_required")
    normalized = observation.get("normalized")
    if not isinstance(normalized, Mapping) or normalized.get("state") != "observed":
        raise CycleEquityError("share_count_not_observed")
    if normalized.get("unit") != "shares":
        raise CycleEquityError("share_count_unit_invalid")
    shares = _number(normalized.get("value"), "share_count_value_invalid", positive=True)
    pit = observation.get("point_in_time")
    if not isinstance(pit, Mapping):
        raise CycleEquityError("share_count_point_in_time_missing")
    available = _utc(pit.get("available_at"), "share_count_available_at_invalid")
    if available > decision:
        raise CycleEquityError("share_count_future_at_decision")
    _false_authority(observation, "share_count")
    return {
        "shares": shares,
        "observation_id": _text(observation.get("observation_id"), "share_count_observation_id_invalid"),
        "available_at": _iso(available),
    }


def _restricted_cash(value: Mapping[str, Any] | None, *, decision: datetime) -> dict[str, Any]:
    if value is None:
        return {
            "state": "unknown",
            "amount": None,
            "included_in_reported_cash": None,
            "source_ref": None,
            "available_at": None,
        }
    if not isinstance(value, Mapping):
        raise CycleEquityError("restricted_cash_invalid")
    state = value.get("state")
    if state not in _RESTRICTED_STATES:
        raise CycleEquityError("restricted_cash_state_invalid")
    if state == "unknown":
        if value.get("amount") is not None:
            raise CycleEquityError("unknown_restricted_cash_has_value")
        return {
            "state": "unknown",
            "amount": None,
            "included_in_reported_cash": None,
            "source_ref": None,
            "available_at": None,
        }
    source_ref = _text(value.get("source_ref"), "restricted_cash_source_ref_required")
    available = _utc(value.get("available_at"), "restricted_cash_available_at_invalid")
    if available > decision:
        raise CycleEquityError("restricted_cash_future_at_decision")
    included = value.get("included_in_reported_cash")
    if not isinstance(included, bool):
        raise CycleEquityError("restricted_cash_inclusion_unknown")
    amount = _number(value.get("amount", 0.0), "restricted_cash_amount_invalid", nonnegative=True)
    if state == "not_applicable" and amount != 0:
        raise CycleEquityError("not_applicable_restricted_cash_nonzero")
    return {
        "state": state,
        "amount": amount,
        "included_in_reported_cash": included,
        "source_ref": source_ref,
        "available_at": _iso(available),
    }


def _event(raw: Mapping[str, Any], *, decision: datetime) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise CycleEquityError("funding_event_invalid")
    event_id = _text(raw.get("event_id"), "funding_event_id_invalid")
    kind = raw.get("kind")
    if kind not in _EVENT_KINDS:
        raise CycleEquityError("funding_event_kind_invalid")
    status = raw.get("status")
    if status not in _EVENT_STATUS:
        raise CycleEquityError("funding_event_status_invalid")
    available = _utc(raw.get("available_at"), "funding_event_available_at_invalid")
    effective = _utc(raw.get("effective_at"), "funding_event_effective_at_invalid")
    if available > decision:
        raise CycleEquityError("funding_event_future_knowledge")
    source_ref = _text(raw.get("source_ref"), "funding_event_source_ref_invalid")
    event = {
        "event_id": event_id,
        "kind": kind,
        "status": status,
        "available_at": _iso(available),
        "effective_at": _iso(effective),
        "source_ref": source_ref,
    }

    if kind == "operating_cash_change":
        event["amount"] = _number(raw.get("amount"), "funding_event_amount_invalid")
    elif kind in {"cash_obligation", "restricted_cash_release"}:
        event["amount"] = _number(raw.get("amount"), "funding_event_amount_invalid", nonnegative=True)
    elif kind == "equity_raise":
        gross = _number(raw.get("gross_proceeds"), "equity_gross_proceeds_invalid", positive=True)
        fees = _number(raw.get("fees", 0), "equity_fees_invalid", nonnegative=True)
        price = _number(raw.get("issue_price"), "equity_issue_price_invalid", positive=True)
        shares = _number(raw.get("shares_issued"), "equity_shares_issued_invalid", positive=True)
        if fees >= gross:
            raise CycleEquityError("equity_fees_consume_proceeds")
        if not isclose(gross, price * shares, rel_tol=1e-9, abs_tol=1e-6 * max(1.0, gross)):
            raise CycleEquityError("equity_raise_terms_do_not_reconcile")
        subscribed = _number(
            raw.get("original_cohort_subscribed_shares", 0),
            "cohort_subscribed_shares_invalid",
            nonnegative=True,
        )
        contribution = _number(
            raw.get("original_cohort_cash_contribution", 0),
            "cohort_cash_contribution_invalid",
            nonnegative=True,
        )
        if subscribed > shares:
            raise CycleEquityError("cohort_subscription_exceeds_issue")
        if not isclose(contribution, subscribed * price, rel_tol=1e-9, abs_tol=1e-6 * max(1.0, contribution)):
            raise CycleEquityError("cohort_subscription_cash_mismatch")
        event.update(
            gross_proceeds=gross,
            fees=fees,
            issue_price=price,
            shares_issued=shares,
            original_cohort_subscribed_shares=subscribed,
            original_cohort_cash_contribution=contribution,
        )
    elif kind == "debt_draw":
        principal = _number(raw.get("principal"), "debt_draw_principal_invalid", positive=True)
        fees = _number(raw.get("fees", 0), "debt_draw_fees_invalid", nonnegative=True)
        if fees >= principal:
            raise CycleEquityError("debt_draw_fees_consume_proceeds")
        event.update(principal=principal, fees=fees)
    elif kind == "debt_repayment":
        event["principal"] = _number(raw.get("principal"), "debt_repayment_principal_invalid", positive=True)
    elif kind == "debt_conversion":
        principal = _number(raw.get("principal"), "debt_conversion_principal_invalid", positive=True)
        shares = _number(raw.get("shares_issued"), "debt_conversion_shares_invalid", positive=True)
        conversion_price = _number(raw.get("conversion_price"), "debt_conversion_price_invalid", positive=True)
        if not isclose(principal, shares * conversion_price, rel_tol=1e-9, abs_tol=1e-6 * max(1.0, principal)):
            raise CycleEquityError("debt_conversion_terms_do_not_reconcile")
        event.update(principal=principal, shares_issued=shares, conversion_price=conversion_price)
    return event


def build_funding_path(
    *,
    capital_need: Mapping[str, Any],
    share_count_observation: Mapping[str, Any],
    issuer_id: str,
    security_id: str,
    decision_at: str,
    recovery_at: str,
    funding_events: Sequence[Mapping[str, Any]],
    original_cohort_shares: float,
    minimum_operating_cash: float = 0.0,
    restricted_cash: Mapping[str, Any] | None = None,
    schedule_complete_through: str | None = None,
) -> dict[str, Any]:
    """Simulate an explicit dated path without inventing financing availability."""
    issuer = _text(issuer_id, "issuer_id_invalid")
    security = _text(security_id, "security_id_invalid")
    decision = _utc(decision_at, "decision_at_invalid")
    recovery = _utc(recovery_at, "recovery_at_invalid")
    if recovery <= decision:
        raise CycleEquityError("recovery_must_follow_decision")

    need = _capital_need(capital_need, issuer_id=issuer, security_id=security)
    shares = _share_count(share_count_observation, issuer_id=issuer, decision=decision)
    cohort_shares = _number(original_cohort_shares, "original_cohort_shares_invalid", positive=True)
    if cohort_shares > shares["shares"]:
        raise CycleEquityError("original_cohort_exceeds_reported_shares")
    cash_floor = _number(minimum_operating_cash, "minimum_operating_cash_invalid", nonnegative=True)
    restricted = _restricted_cash(restricted_cash, decision=decision)

    limitations: list[str] = []
    if need["cash"] is None:
        limitations.append("starting_cash_unavailable")
    if need["debt"] is None:
        limitations.append("starting_debt_unavailable")
    if not need["debt_ladder_complete"]:
        limitations.append("debt_ladder_incomplete")
    if need["status"] != "complete":
        limitations.extend(f"capital_need:{reason}" for reason in need["coverage_reasons"])
    if restricted["state"] == "unknown":
        limitations.append("restricted_cash_unknown")

    complete_through = None
    if schedule_complete_through is None:
        limitations.append("funding_schedule_completeness_unestablished")
    else:
        complete_through = _utc(schedule_complete_through, "schedule_complete_through_invalid")
        if complete_through < recovery:
            limitations.append("funding_schedule_does_not_cover_recovery")

    starting_cash = need["cash"]
    accessible_cash = starting_cash
    restricted_balance = restricted["amount"] if restricted["amount"] is not None else 0.0
    if accessible_cash is not None and restricted["state"] == "observed" and restricted["included_in_reported_cash"]:
        accessible_cash -= restricted_balance
        if accessible_cash < 0:
            raise CycleEquityError("restricted_cash_exceeds_reported_cash")
    starting_accessible_cash = accessible_cash

    debt = need["debt"]
    total_shares = shares["shares"]
    original_ending_shares = cohort_shares
    cohort_contributions = 0.0
    breaches: list[dict[str, Any]] = []
    timeline: list[dict[str, Any]] = []

    parsed = [_event(item, decision=decision) for item in funding_events]
    ids = [item["event_id"] for item in parsed]
    if len(ids) != len(set(ids)):
        raise CycleEquityError("duplicate_funding_event_id")
    parsed.sort(key=lambda item: (item["effective_at"], item["event_id"]))

    for event in parsed:
        when = _utc(event["effective_at"], "funding_event_effective_at_invalid")
        if when > recovery:
            continue
        if accessible_cash is None or debt is None:
            # We retain the event record but cannot pretend a path is quantitative.
            timeline.append({**deepcopy(event), "cash_after": None, "debt_after": None, "shares_after": total_shares})
            continue

        kind = event["kind"]
        if kind == "operating_cash_change":
            accessible_cash += event["amount"]
        elif kind == "cash_obligation":
            accessible_cash -= event["amount"]
        elif kind == "restricted_cash_release":
            if restricted["state"] != "observed":
                raise CycleEquityError("restricted_cash_release_without_observed_balance")
            if event["amount"] > restricted_balance:
                raise CycleEquityError("restricted_cash_release_exceeds_balance")
            restricted_balance -= event["amount"]
            accessible_cash += event["amount"]
        elif kind == "equity_raise":
            accessible_cash += event["gross_proceeds"] - event["fees"]
            total_shares += event["shares_issued"]
            original_ending_shares += event["original_cohort_subscribed_shares"]
            cohort_contributions += event["original_cohort_cash_contribution"]
        elif kind == "debt_draw":
            accessible_cash += event["principal"] - event["fees"]
            debt += event["principal"]
        elif kind == "debt_repayment":
            accessible_cash -= event["principal"]
            debt -= event["principal"]
            if debt < -1e-6:
                raise CycleEquityError("debt_repayment_exceeds_modeled_debt")
            debt = max(debt, 0.0)
        elif kind == "debt_conversion":
            debt -= event["principal"]
            if debt < -1e-6:
                raise CycleEquityError("debt_conversion_exceeds_modeled_debt")
            debt = max(debt, 0.0)
            total_shares += event["shares_issued"]

        headroom = accessible_cash - cash_floor
        if headroom < 0:
            breaches.append({
                "event_id": event["event_id"],
                "effective_at": event["effective_at"],
                "shortfall_to_operating_cash_floor": -headroom,
            })
        timeline.append({
            **deepcopy(event),
            "cash_after": accessible_cash,
            "restricted_cash_after": restricted_balance if restricted["state"] == "observed" else None,
            "debt_after": debt,
            "shares_after": total_shares,
            "original_cohort_shares_after": original_ending_shares,
            "cash_floor_headroom_after": headroom,
        })

    quantitative = accessible_cash is not None and debt is not None
    qualified = quantitative and not limitations
    path_state = (
        "UNAVAILABLE"
        if not qualified
        else "BREACHED_BEFORE_RECOVERY"
        if breaches
        else "FUNDED_TO_RECOVERY"
    )

    return {
        "schema": FUNDING_PATH_SCHEMA,
        "issuer_id": issuer,
        "security_id": security,
        "decision_at": _iso(decision),
        "recovery_at": _iso(recovery),
        "path_state": path_state,
        "starting": {
            "accessible_cash": starting_accessible_cash,
            "reported_cash": need["cash"],
            "reported_debt": need["debt"],
            "reported_common_shares": shares["shares"],
            "original_cohort_shares": cohort_shares,
            "minimum_operating_cash": cash_floor,
            "restricted_cash": deepcopy(restricted),
        },
        "ending": {
            "accessible_cash": accessible_cash,
            "restricted_cash": restricted_balance if restricted["state"] == "observed" else None,
            "reported_debt_model": debt,
            "common_shares": total_shares,
            "original_cohort_shares": original_ending_shares,
            "original_cohort_additional_contributions": cohort_contributions,
        },
        "timeline": timeline,
        "breaches": breaches,
        "schedule_complete_through": _iso(complete_through) if complete_through is not None else None,
        "limitations": sorted(set(limitations)),
        "source_refs": {
            "share_count_observation_id": shares["observation_id"],
            "capital_need_source_clock": deepcopy(need["source_clock"]),
        },
        **_AUTHORITY,
    }


def recovery_scenario(
    funding_path: Mapping[str, Any],
    *,
    enterprise_value: float,
    other_senior_claims: float = 0.0,
    original_purchase_price_per_share: float | None = None,
    security_state: str = "continuing",
    replacement_distribution: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Map an assumed recovered enterprise value to the original shareholder."""
    if not isinstance(funding_path, Mapping) or funding_path.get("schema") != FUNDING_PATH_SCHEMA:
        raise CycleEquityError("funding_path_required")
    for key in _AUTHORITY:
        if funding_path.get(key) is not False:
            raise CycleEquityError("funding_path_authority_escalation")
    ev = _number(enterprise_value, "enterprise_value_invalid", nonnegative=True)
    senior = _number(other_senior_claims, "other_senior_claims_invalid", nonnegative=True)
    if security_state not in {"continuing", "canceled"}:
        raise CycleEquityError("security_state_invalid")

    ending = funding_path.get("ending")
    if not isinstance(ending, Mapping):
        raise CycleEquityError("funding_path_ending_missing")
    cash = ending.get("accessible_cash")
    debt = ending.get("reported_debt_model")
    shares = ending.get("common_shares")
    cohort_shares = ending.get("original_cohort_shares")
    additional = _number(
        ending.get("original_cohort_additional_contributions", 0),
        "cohort_contributions_invalid",
        nonnegative=True,
    )

    limitations = list(funding_path.get("limitations") or [])
    terminal_available = (
        funding_path.get("path_state") == "FUNDED_TO_RECOVERY"
        and cash is not None and debt is not None and shares is not None and cohort_shares is not None
    )
    terminal_value = None
    common_equity = None
    per_share = None

    if security_state == "continuing" and terminal_available:
        cash_v = _number(cash, "ending_cash_invalid")
        debt_v = _number(debt, "ending_debt_invalid", nonnegative=True)
        shares_v = _number(shares, "ending_shares_invalid", positive=True)
        cohort_v = _number(cohort_shares, "cohort_ending_shares_invalid", positive=True)
        common_equity = max(ev + cash_v - debt_v - senior, 0.0)
        per_share = common_equity / shares_v
        terminal_value = per_share * cohort_v
    elif security_state == "canceled":
        if replacement_distribution is None:
            limitations.append("original_security_canceled_distribution_unestablished")
        else:
            if not isinstance(replacement_distribution, Mapping):
                raise CycleEquityError("replacement_distribution_invalid")
            source_ref = _text(
                replacement_distribution.get("source_ref"),
                "replacement_distribution_source_ref_invalid",
            )
            distribution_status = replacement_distribution.get("status")
            decision = _utc(funding_path.get("decision_at"), "funding_path_decision_at_invalid")
            if distribution_status is None:
                # Backward-compatible scenario inputs are allowed only as explicit
                # assumptions. Missing metadata never upgrades them to observed evidence.
                distribution_status = "scenario_assumption"
                distribution_available = decision
                limitations.append("replacement_distribution_status_unestablished_scenario_only")
            elif distribution_status not in _EVENT_STATUS:
                raise CycleEquityError("replacement_distribution_status_invalid")
            else:
                distribution_available = _utc(
                    replacement_distribution.get("available_at"),
                    "replacement_distribution_available_at_invalid",
                )
                if distribution_available > decision:
                    raise CycleEquityError("replacement_distribution_future_at_decision")
            cash_per_old = _number(
                replacement_distribution.get("cash_per_old_share", 0),
                "cash_per_old_share_invalid",
                nonnegative=True,
            )
            new_per_old = _number(
                replacement_distribution.get("new_shares_per_old_share", 0),
                "new_shares_per_old_share_invalid",
                nonnegative=True,
            )
            new_share_value = replacement_distribution.get("new_share_value")
            if new_per_old > 0 and new_share_value is None:
                limitations.append("replacement_new_share_value_unestablished")
            else:
                new_value = 0.0 if new_per_old == 0 else _number(
                    new_share_value, "replacement_new_share_value_invalid", nonnegative=True
                )
                original = _number(
                    funding_path["starting"]["original_cohort_shares"],
                    "original_cohort_shares_invalid",
                    positive=True,
                )
                terminal_value = original * (cash_per_old + new_per_old * new_value)
            limitations.append(f"replacement_distribution_source:{source_ref}")

    purchase_price = None
    original_purchase_cost = None
    total_contributed = None
    scenario_return = None
    required_ev_original = None
    required_ev_total = None
    if original_purchase_price_per_share is not None:
        purchase_price = _number(
            original_purchase_price_per_share,
            "original_purchase_price_invalid",
            positive=True,
        )
        original_shares = _number(
            funding_path["starting"]["original_cohort_shares"],
            "original_cohort_shares_invalid",
            positive=True,
        )
        original_purchase_cost = purchase_price * original_shares
        total_contributed = original_purchase_cost + additional
        if terminal_value is not None:
            scenario_return = (terminal_value - total_contributed) / total_contributed

        if security_state == "continuing" and terminal_available:
            ending_shares = _number(shares, "ending_shares_invalid", positive=True)
            cohort_ending = _number(cohort_shares, "cohort_ending_shares_invalid", positive=True)
            cash_v = _number(cash, "ending_cash_invalid")
            debt_v = _number(debt, "ending_debt_invalid", nonnegative=True)
            required_equity_original = (original_purchase_cost / cohort_ending) * ending_shares
            required_equity_total = (total_contributed / cohort_ending) * ending_shares
            required_ev_original = max(required_equity_original - cash_v + debt_v + senior, 0.0)
            required_ev_total = max(required_equity_total - cash_v + debt_v + senior, 0.0)

    return {
        "schema": RECOVERY_SCHEMA,
        "issuer_id": funding_path.get("issuer_id"),
        "security_id": funding_path.get("security_id"),
        "funding_path_state": funding_path.get("path_state"),
        "security_state": security_state,
        "assumed_enterprise_value": ev,
        "other_senior_claims": senior,
        "common_equity_value": common_equity,
        "ending_value_per_continuing_common_share": per_share,
        "original_cohort_terminal_value": terminal_value,
        "original_purchase_price_per_share": purchase_price,
        "original_purchase_cost": original_purchase_cost,
        "original_cohort_additional_contributions": additional,
        "original_cohort_total_contributed": total_contributed,
        "scenario_return_on_total_contributed": scenario_return,
        "enterprise_value_required_to_recover_original_purchase": required_ev_original,
        "enterprise_value_required_to_recover_total_contributed": required_ev_total,
        "limitations": sorted(set(limitations)),
        "interpretation": (
            "Scenario arithmetic only. Enterprise value, financing availability, terminal share value, "
            "and purchase economics are assumptions unless separately source-qualified."
        ),
        **_AUTHORITY,
    }


def inventory_sales_diagnostic(
    *,
    prior_inventory: float,
    current_inventory: float,
    prior_sales: float,
    current_sales: float,
) -> dict[str, Any]:
    """Detect when falling inventory merely reflects even faster demand deterioration."""
    pi = _number(prior_inventory, "prior_inventory_invalid", nonnegative=True)
    ci = _number(current_inventory, "current_inventory_invalid", nonnegative=True)
    ps = _number(prior_sales, "prior_sales_invalid", positive=True)
    cs = _number(current_sales, "current_sales_invalid", positive=True)
    inventory_change = ci / pi - 1 if pi > 0 else None
    sales_change = cs / ps - 1
    prior_ratio = pi / ps
    current_ratio = ci / cs
    ratio_change = current_ratio / prior_ratio - 1 if prior_ratio > 0 else None

    if inventory_change is not None and inventory_change < 0 and sales_change < inventory_change:
        state = "INVENTORY_DOWN_SALES_DOWN_FASTER"
    elif inventory_change is not None and inventory_change < 0 and ratio_change is not None and ratio_change < 0:
        state = "DESTOCKING_WITH_IMPROVING_INVENTORY_SALES_RATIO"
    else:
        state = "MIXED_OR_OTHER"

    return {
        "schema": INVENTORY_SALES_SCHEMA,
        "state": state,
        "inventory_change": inventory_change,
        "sales_change": sales_change,
        "prior_inventory_to_sales": prior_ratio,
        "current_inventory_to_sales": current_ratio,
        "inventory_to_sales_change": ratio_change,
        "interpretation": (
            "Inventory and sales must be interpreted jointly; lower inventory alone is not demand recovery."
        ),
        **_AUTHORITY,
    }


def build_cycle_equity_case(
    *,
    capital_need: Mapping[str, Any],
    share_count_observation: Mapping[str, Any],
    issuer_id: str,
    security_id: str,
    decision_at: str,
    recovery_at: str,
    funding_events: Sequence[Mapping[str, Any]],
    original_cohort_shares: float,
    enterprise_value: float,
    minimum_operating_cash: float = 0.0,
    restricted_cash: Mapping[str, Any] | None = None,
    schedule_complete_through: str | None = None,
    other_senior_claims: float = 0.0,
    original_purchase_price_per_share: float | None = None,
    security_state: str = "continuing",
    replacement_distribution: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compose the B17 funding and original-equity view without adding authority."""
    funding = build_funding_path(
        capital_need=capital_need,
        share_count_observation=share_count_observation,
        issuer_id=issuer_id,
        security_id=security_id,
        decision_at=decision_at,
        recovery_at=recovery_at,
        funding_events=funding_events,
        original_cohort_shares=original_cohort_shares,
        minimum_operating_cash=minimum_operating_cash,
        restricted_cash=restricted_cash,
        schedule_complete_through=schedule_complete_through,
    )
    recovery = recovery_scenario(
        funding,
        enterprise_value=enterprise_value,
        other_senior_claims=other_senior_claims,
        original_purchase_price_per_share=original_purchase_price_per_share,
        security_state=security_state,
        replacement_distribution=replacement_distribution,
    )
    return {
        "schema": SCHEMA,
        "issuer_id": issuer_id,
        "security_id": security_id,
        "decision_at": decision_at,
        "recovery_at": recovery_at,
        "funding": funding,
        "recovery": recovery,
        "user_question": (
            "Can the issuer reach recovery, and if it does, what value reaches the original common shareholder?"
        ),
        "not_established": sorted(set([
            "recovery_probability",
            "financing_availability_probability",
            "fair_value",
            "position_size",
            "current_market_permission",
            "automatic_average_down_permission",
        ])),
        **_AUTHORITY,
    }


def cycle_equity_brief(case: Mapping[str, Any]) -> dict[str, Any]:
    """Turn the B17 calculation into a bounded user explanation.

    This is presentation logic over one already-built case. It performs no source
    lookup and creates no recommendation, probability, score, or position action.
    """
    if not isinstance(case, Mapping) or case.get("schema") != SCHEMA:
        raise CycleEquityError("cycle_equity_case_required")
    for key in _AUTHORITY:
        if case.get(key) is not False:
            raise CycleEquityError("cycle_equity_case_authority_escalation")
    funding = case.get("funding")
    recovery = case.get("recovery")
    if not isinstance(funding, Mapping) or funding.get("schema") != FUNDING_PATH_SCHEMA:
        raise CycleEquityError("cycle_funding_path_required")
    if not isinstance(recovery, Mapping) or recovery.get("schema") != RECOVERY_SCHEMA:
        raise CycleEquityError("cycle_recovery_required")

    facts: list[dict[str, Any]] = []
    counters: list[dict[str, Any]] = []
    missing = set(case.get("not_established") or [])
    for limitation in funding.get("limitations") or []:
        missing.add(str(limitation))
    for limitation in recovery.get("limitations") or []:
        if not str(limitation).startswith("replacement_distribution_source:"):
            missing.add(str(limitation))

    def add(target: list[dict[str, Any]], code: str, text: str, values: Mapping[str, Any] | None = None) -> None:
        target.append({"code": code, "text": text, "values": deepcopy(dict(values or {}))})

    state = funding.get("path_state")
    breaches = funding.get("breaches")
    if not isinstance(breaches, list):
        raise CycleEquityError("funding_breaches_invalid")
    if state == "BREACHED_BEFORE_RECOVERY":
        first = breaches[0] if breaches else {}
        add(
            counters,
            "FUNDING_GAP_BEFORE_RECOVERY",
            "The modeled funding path falls below the required operating-cash floor before the recovery date.",
            {
                "event_id": first.get("event_id"),
                "effective_at": first.get("effective_at"),
                "shortfall": first.get("shortfall_to_operating_cash_floor"),
            },
        )
    elif state == "FUNDED_TO_RECOVERY":
        add(
            facts,
            "MODELED_FUNDING_PATH_REACHES_RECOVERY",
            "The explicit modeled funding schedule reaches the recovery date without breaching the stated operating-cash floor.",
        )
    elif state == "UNAVAILABLE":
        missing.add("QUALIFIED_FUNDING_PATH_TO_RECOVERY")
    else:
        raise CycleEquityError("funding_path_state_invalid")

    start = funding.get("starting")
    end = funding.get("ending")
    if not isinstance(start, Mapping) or not isinstance(end, Mapping):
        raise CycleEquityError("funding_start_end_invalid")
    start_shares = _number(start.get("reported_common_shares"), "brief_start_shares_invalid", positive=True)
    end_shares = end.get("common_shares")
    if end_shares is not None:
        end_shares_value = _number(end_shares, "brief_end_shares_invalid", positive=True)
        change = end_shares_value / start_shares - 1
        if change > 0:
            add(
                counters,
                "COMMON_SHARE_COUNT_INCREASED",
                "The modeled financing path increases common shares outstanding; business recovery and per-share recovery are not the same question.",
                {"share_count_change_fraction": change},
            )

    security_state = recovery.get("security_state")
    terminal = recovery.get("original_cohort_terminal_value")
    contributed = recovery.get("original_cohort_total_contributed")
    scenario_return = recovery.get("scenario_return_on_total_contributed")
    if security_state == "canceled":
        if terminal is None:
            missing.add("ORIGINAL_SECURITY_DISTRIBUTION_VALUE")
        else:
            add(
                counters if scenario_return is not None and scenario_return < 0 else facts,
                "ORIGINAL_SECURITY_CANCELED_AND_MAPPED",
                "The original security is canceled; its modeled recovery comes only from the explicit distribution mapping, not from splicing replacement-security performance.",
                {"terminal_value": terminal, "scenario_return_on_total_contributed": scenario_return},
            )
    elif terminal is not None and contributed is not None:
        if scenario_return is None:
            raise CycleEquityError("brief_terminal_return_missing")
        if scenario_return < 0:
            add(
                counters,
                "BUSINESS_RECOVERY_DOES_NOT_RECOVER_ORIGINAL_CAPITAL",
                "The assumed business recovery still leaves the original cohort below its modeled contributed capital after financing.",
                {
                    "terminal_value": terminal,
                    "total_contributed": contributed,
                    "scenario_return_on_total_contributed": scenario_return,
                },
            )
        else:
            add(
                facts,
                "MODELED_RECOVERY_REACHES_ORIGINAL_COMMON",
                "Under the stated assumptions, the modeled recovery reaches the original common-share cohort after financing.",
                {
                    "terminal_value": terminal,
                    "total_contributed": contributed,
                    "scenario_return_on_total_contributed": scenario_return,
                },
            )

    hurdle = recovery.get("enterprise_value_required_to_recover_total_contributed")
    if hurdle is not None:
        add(
            facts if recovery.get("assumed_enterprise_value", 0) >= hurdle else counters,
            "ENTERPRISE_VALUE_RECOVERY_HURDLE",
            "The recovery hurdle reflects the modeled cash, debt, senior claims, share count, and original-cohort capital contributions.",
            {
                "assumed_enterprise_value": recovery.get("assumed_enterprise_value"),
                "required_enterprise_value": hurdle,
            },
        )

    if state == "UNAVAILABLE":
        summary_state = "EVIDENCE_INCOMPLETE"
    elif state == "BREACHED_BEFORE_RECOVERY":
        summary_state = "FUNDING_GAP"
    elif counters:
        summary_state = "RECOVERY_WITH_MATERIAL_EQUITY_RISK"
    else:
        summary_state = "SCENARIO_REACHES_ORIGINAL_COMMON"

    return {
        "schema": "prophet.cycle_equity_brief/v1",
        "issuer_id": case.get("issuer_id"),
        "security_id": case.get("security_id"),
        "decision_at": case.get("decision_at"),
        "summary_state": summary_state,
        "supporting_facts": facts,
        "counterevidence": counters,
        "not_established": sorted(str(x) for x in missing),
        "next_step": (
            "Verify missing financing terms, source clocks and current market/portfolio permission before treating the scenario as actionable."
        ),
        "interpretation": (
            "Cycle recovery explanation only; scenario arithmetic is not a calibrated probability, fair value, position size or buy permission."
        ),
        **_AUTHORITY,
    }
