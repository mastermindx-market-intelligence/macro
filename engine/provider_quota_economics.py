"""Read-only quota economics for the existing Shared AI Provider Control owner.

This is a planning calculator, NOT capacity truth, a scheduler, or an admission
API. It never acquires credentials, stores usage, starts workers, or changes
provider_capacity.v1. Every forecast is conditional on supplied observations and
representative task costs. Executive claim-time integration remains separately gated.
"""
from __future__ import annotations

import dataclasses
import heapq
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Optional, Tuple

SCHEMA = "mastermind.quota_economics_preview/v1"
INPUT_SCHEMA = "mastermind.quota_economics_preview_input/v1"
_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
MAX_JOBS = 512
MAX_HORIZON_SECONDS = 32 * 86400


class QuotaEconomicsError(ValueError):
    """Bounded, secret-free input refusal."""


def number(value: Any) -> Decimal:
    if isinstance(value, bool) or value is None or len(str(value)) > 40:
        raise QuotaEconomicsError("INVALID_NUMBER")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise QuotaEconomicsError("INVALID_NUMBER") from None
    if not result.is_finite() or result < 0 or result > Decimal("1e15"):
        raise QuotaEconomicsError("INVALID_NUMBER")
    if result.as_tuple().exponent < -12:
        raise QuotaEconomicsError("NUMBER_PRECISION_EXCEEDED")
    return result


def instant(value: str) -> float:
    if not isinstance(value, str) or len(value) > 40:
        raise QuotaEconomicsError("INVALID_TIMESTAMP")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError()
        return parsed.astimezone(timezone.utc).timestamp()
    except (ValueError, OverflowError, OSError):
        raise QuotaEconomicsError("INVALID_TIMESTAMP") from None


def identity(value: Any) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise QuotaEconomicsError("INVALID_REFERENCE")
    return value


@dataclasses.dataclass(frozen=True)
class Resource:
    resource_id: str
    entitlement_generation: str
    applies_to: Tuple[str, ...]
    unit: str
    window_type: str
    horizon: str
    limit: Optional[float]
    remaining: Optional[float]
    observed_at: str
    valid_until: str
    evidence: str
    reset_at: Optional[str] = None
    window_seconds: Optional[int] = None
    unobserved_holds: float = 0
    reserves: Mapping[str, float] = dataclasses.field(default_factory=dict)
    releases: Tuple[Mapping[str, Any], ...] = ()
    release_schedule_complete: bool = False


@dataclasses.dataclass(frozen=True)
class Option:
    option_id: str
    provider: str
    model_alias: str
    model_family: str
    costs: Mapping[str, Mapping[str, Any]]
    duration_seconds: int
    marginal_cash: Optional[float]
    permitted: Optional[bool]
    harness_ready: Optional[bool]
    usage_allowed: Optional[bool]
    useful_jobs_per_hour: Optional[float] = None


@dataclasses.dataclass(frozen=True)
class Task:
    kind: str
    state: str
    authorized: bool
    ready_jobs: int
    suitability_tiers: Tuple[Mapping[str, Any], ...]
    excluded_families: Tuple[str, ...] = ()
    deadline_at: Optional[str] = None


@dataclasses.dataclass(frozen=True)
class Policy:
    burst_cap: int = 1
    paid_spend_allowed: bool = False
    provider_precedence: Tuple[Mapping[str, Any], ...] = ()


def _integer(value: Any, maximum: int) -> None:
    if type(value) is not int or not 0 <= value <= maximum:
        raise QuotaEconomicsError("INVALID_INTEGER")


def _validate(resources, options, task, policy, now):
    if len(resources) > 256 or len(options) > 64:
        raise QuotaEconomicsError("INPUT_TOO_LARGE")
    ids = [identity(r.resource_id) for r in resources]
    option_ids = [identity(o.option_id) for o in options]
    if len(set(ids)) != len(ids) or len(set(option_ids)) != len(option_ids):
        raise QuotaEconomicsError("DUPLICATE_IDENTITY")
    _integer(task.ready_jobs, MAX_JOBS)
    _integer(policy.burst_cap, 128)
    if not policy.burst_cap or type(task.authorized) is not bool or type(policy.paid_spend_allowed) is not bool:
        raise QuotaEconomicsError("INVALID_POLICY")
    identity(task.kind)
    if task.state not in {"READY", "STARTED", "EFFECT_UNKNOWN", "NOT_READY"}:
        raise QuotaEconomicsError("INVALID_TASK_STATE")
    if task.deadline_at is not None:
        instant(task.deadline_at)
    aliases = []
    tier_ids = []
    for tier in task.suitability_tiers:
        if set(tier) != {"tier_id", "model_aliases"} or not tier["model_aliases"]:
            raise QuotaEconomicsError("INVALID_SUITABILITY_TIER")
        tier_ids.append(identity(tier["tier_id"]))
        aliases.extend(identity(a) for a in tier["model_aliases"])
    if len(set(aliases)) != len(aliases) or len(set(tier_ids)) != len(tier_ids):
        raise QuotaEconomicsError("DUPLICATE_SUITABILITY_IDENTITY")
    for family in task.excluded_families:
        identity(family)
    for r in resources:
        identity(r.entitlement_generation)
        identity(r.unit)
        identity(r.horizon)
        if r.window_type not in {"fixed", "rolling", "billing_cycle", "instant", "nonexpiring", "unknown"}:
            raise QuotaEconomicsError("INVALID_WINDOW_TYPE")
        if r.evidence not in {"exact", "provider_reported", "estimated", "unknown"}:
            raise QuotaEconomicsError("INVALID_EVIDENCE")
        if not r.applies_to or len(set(r.applies_to)) != len(r.applies_to) or set(r.applies_to) - set(option_ids):
            raise QuotaEconomicsError("INVALID_RESOURCE_BINDING")
        if instant(r.valid_until) <= instant(r.observed_at):
            raise QuotaEconomicsError("INVALID_FRESHNESS_INTERVAL")
        if r.reset_at is not None:
            instant(r.reset_at)
        if r.window_seconds is not None:
            _integer(r.window_seconds, MAX_HORIZON_SECONDS)
            if r.window_seconds == 0:
                raise QuotaEconomicsError("INVALID_WINDOW_DURATION")
        if r.limit is not None and number(r.limit) == 0:
            raise QuotaEconomicsError("INVALID_LIMIT")
        if r.remaining is not None:
            number(r.remaining)
            if r.limit is not None and number(r.remaining) > number(r.limit):
                raise QuotaEconomicsError("INCONSISTENT_BALANCE")
        number(r.unobserved_holds)
        for alias, reserve in r.reserves.items():
            identity(alias)
            number(reserve)
        if type(r.release_schedule_complete) is not bool or len(r.releases) > 1024:
            raise QuotaEconomicsError("INVALID_RELEASE_SCHEDULE")
        released = Decimal(0)
        for release in r.releases:
            if set(release) != {"at", "amount"}:
                raise QuotaEconomicsError("INVALID_RELEASE")
            if instant(release["at"]) <= instant(r.observed_at):
                raise QuotaEconomicsError("INVALID_RELEASE_TIME")
            released += number(release["amount"])
        if r.limit is not None and r.remaining is not None and released > number(r.limit) - number(r.remaining):
            raise QuotaEconomicsError("RELEASE_EXCEEDS_OBSERVED_USAGE")
    for o in options:
        for value in (o.provider, o.model_alias, o.model_family):
            identity(value)
        _integer(o.duration_seconds, MAX_HORIZON_SECONDS)
        if not o.duration_seconds:
            raise QuotaEconomicsError("INVALID_TASK_DURATION")
        for value in (o.permitted, o.harness_ready, o.usage_allowed):
            if value is not None and type(value) is not bool:
                raise QuotaEconomicsError("INVALID_GATE")
        if o.marginal_cash is not None:
            number(o.marginal_cash)
        if o.useful_jobs_per_hour is not None:
            number(o.useful_jobs_per_hour)
        required = {r.resource_id for r in resources if o.option_id in r.applies_to}
        if not required or set(o.costs) != required:
            raise QuotaEconomicsError("INCOMPLETE_RESOURCE_COSTS")
        for r in resources:
            if r.resource_id not in required:
                continue
            cost = o.costs[r.resource_id]
            if set(cost) != {"amount", "unit"} or cost["unit"] != r.unit or not number(cost["amount"]):
                raise QuotaEconomicsError("INVALID_NATIVE_COST")
    if len(policy.provider_precedence) > 64:
        raise QuotaEconomicsError("PRECEDENCE_TOO_LARGE")
    for edge in policy.provider_precedence:
        if set(edge) != {"preferred", "fallback", "task_kinds"}:
            raise QuotaEconomicsError("INVALID_PRECEDENCE")
        identity(edge["preferred"])
        identity(edge["fallback"])
        if edge["preferred"] == edge["fallback"] or not edge["task_kinds"]:
            raise QuotaEconomicsError("INVALID_PRECEDENCE")
        if not isinstance(edge["task_kinds"], (tuple, list)) or len(edge["task_kinds"]) > 64:
            raise QuotaEconomicsError("INVALID_PRECEDENCE_KINDS")
        for kind in edge["task_kinds"]:
            identity(kind)
    _precedence_reachability(policy, task.kind)


def _precedence_reachability(policy, kind):
    graph = {}
    for edge in policy.provider_precedence:
        if kind in edge["task_kinds"]:
            graph.setdefault(edge["preferred"], set()).add(edge["fallback"])
    reach = {key: set(values) for key, values in graph.items()}
    for _ in range(len(graph) + 1):
        changed = False
        for key, targets in reach.items():
            expanded = set(targets)
            for target in tuple(targets):
                expanded.update(reach.get(target, ()))
            if key in expanded:
                raise QuotaEconomicsError("CYCLIC_PROVIDER_PRECEDENCE")
            if expanded != targets:
                reach[key] = expanded
                changed = True
        if not changed:
            return reach
    raise QuotaEconomicsError("PRECEDENCE_DID_NOT_CONVERGE")


def _protected(r: Resource, o: Option) -> Decimal:
    return number(r.unobserved_holds) + sum(
        (number(value) for alias, value in r.reserves.items() if alias != o.model_alias), Decimal(0)
    )


def _balance(r: Resource, o: Option) -> Decimal:
    return max(Decimal(0), number(r.remaining) - _protected(r, o))


def _forecast(resources, option, now, until, ready_jobs, burst_cap):
    """Conditional front-loaded-cost simulation, never a future admission receipt."""
    until = min(until, now + MAX_HORIZON_SECONDS)
    balances = {r.resource_id: _balance(r, option) for r in resources}
    caps = {r.resource_id: max(Decimal(0), number(r.limit) - _protected(r, option))
            for r in resources if r.limit is not None}
    costs = {key: number(value["amount"]) for key, value in option.costs.items()}
    by_id = {r.resource_id: r for r in resources}
    events = []
    sequence = 0
    notes = set()
    def event(at, kind, key, value):
        nonlocal sequence
        sequence += 1
        heapq.heappush(events, (at, sequence, kind, key, value))
    for r in resources:
        if r.window_type in {"rolling", "instant"}:
            if r.limit is None or (number(r.remaining) < number(r.limit) and not r.release_schedule_complete):
                notes.add("UNKNOWN_PRIOR_RELEASES_CONSERVATIVELY_OMITTED")
            for release in r.releases:
                if now < instant(release["at"]) < until:
                    event(instant(release["at"]), "release", r.resource_id, number(release["amount"]))
        if r.window_type in {"fixed", "billing_cycle"} and r.reset_at is not None:
            at = instant(r.reset_at)
            if now < at < until and r.limit is not None:
                event(at, "reset", r.resource_id, Decimal(0))
                notes.add("FUTURE_REFILL_IS_FORECAST_NOT_OBSERVED_CAPACITY")
    started = 0
    active = 0
    t = now
    steps = 0
    while started < ready_jobs and t + option.duration_seconds <= until:
        steps += 1
        if steps > 4096:
            notes.add("FORECAST_EVENT_BUDGET_EXHAUSTED_CONSERVATIVE_PARTIAL")
            break
        while events and events[0][0] <= t:
            at, _, kind, key, value = heapq.heappop(events)
            if kind == "finish":
                active -= 1
            elif kind == "release":
                balances[key] += value
                if key in caps:
                    balances[key] = min(balances[key], caps[key])
            else:
                balances[key] = caps[key]
                r = by_id[key]
                if r.window_type == "fixed" and r.window_seconds is not None and at + r.window_seconds < until:
                    event(at + r.window_seconds, "reset", key, Decimal(0))
        fit = min((int(balances[key] // cost) for key, cost in costs.items()), default=0)
        count = min(fit, burst_cap - active, ready_jobs - started)
        if count > 0:
            for key, cost in costs.items():
                balances[key] -= cost * count
                r = by_id[key]
                if r.window_type == "instant":
                    event(t + option.duration_seconds, "release", key, cost * count)
                elif r.window_type == "rolling" and r.window_seconds is not None:
                    event(t + r.window_seconds, "release", key, cost * count)
            for _ in range(count):
                event(t + option.duration_seconds, "finish", "", Decimal(0))
            started += count
            active += count
        if not events:
            break
        t = events[0][0]
    return started, sorted(notes)


def preview(resources, options, task, policy, *, as_of: str):
    """Explain a next-task preference inside supplied Model Router suitability tiers.

    Input bindings/gates are declarations, not independently verified authority.
    Options are alternative scenarios: their forecasts MUST NOT be summed.
    """
    now = instant(as_of)
    _validate(resources, options, task, policy, now)
    result = {"schema": SCHEMA, "as_of": as_of, "authority": "NONE_PREVIEW_ONLY",
              "binding_verification": "NOT_PERFORMED", "live_admission": False,
              "claim_time_revalidation_required": True, "suggested_option": None,
              "selected_tier": None, "options": [], "warnings": []}
    if task.state != "READY" or not task.authorized or task.ready_jobs == 0:
        result["status"] = "RECONCILE_EXISTING_ATTEMPT" if task.state in {"STARTED", "EFFECT_UNKNOWN"} else "NO_AUTHORIZED_READY_WORK"
        return result
    tiers = {alias: (index, tier["tier_id"]) for index, tier in enumerate(task.suitability_tiers)
             for alias in tier["model_aliases"]}
    assessed = []
    for o in sorted(options, key=lambda item: item.option_id):
        rows = [r for r in resources if o.option_id in r.applies_to]
        reasons = []
        if o.model_alias not in tiers:
            reasons.append("OUTSIDE_APPROVED_SUITABILITY_TIERS")
        if o.model_family in task.excluded_families:
            reasons.append("REVIEW_INDEPENDENCE")
        for value, reason in ((o.permitted, "AUTHORITY_GATE"), (o.harness_ready, "HARNESS_GATE"),
                              (o.usage_allowed, "PROVIDER_TERMS_GATE")):
            if value is not True:
                reasons.append(reason)
        if o.marginal_cash is None:
            reasons.append("CASH_COST_UNKNOWN")
        elif number(o.marginal_cash) > 0 and not policy.paid_spend_allowed:
            reasons.append("PAID_SPEND_NOT_APPROVED")
        if task.deadline_at is not None and now + o.duration_seconds > instant(task.deadline_at):
            reasons.append("DEADLINE_UNREACHABLE")
        if not any(r.window_type == "instant" and r.unit == "concurrent_sessions" for r in rows):
            reasons.append("CONCURRENCY_OBSERVATION_MISSING")
        for r in rows:
            if r.evidence not in {"exact", "provider_reported"} or r.remaining is None:
                reasons.append("QUOTA_UNKNOWN:" + r.resource_id)
            if not instant(r.observed_at) <= now < instant(r.valid_until):
                reasons.append("QUOTA_STALE_OR_FUTURE:" + r.resource_id)
            if r.window_type == "unknown":
                reasons.append("WINDOW_SEMANTICS_UNKNOWN:" + r.resource_id)
            if r.reset_at is not None and r.window_type in {"fixed", "billing_cycle"} and now >= instant(r.reset_at):
                reasons.append("RESET_REOBSERVATION_REQUIRED:" + r.resource_id)
            if r.remaining is not None and _balance(r, o) < number(o.costs[r.resource_id]["amount"]):
                reasons.append("QUOTA_OR_RESERVE_EXHAUSTED:" + r.resource_id)
        record = {"option_id": o.option_id, "provider": o.provider, "model_alias": o.model_alias,
                  "eligible_in_preview": not reasons, "reasons": sorted(set(reasons)),
                  "estimated_startable_jobs": 0, "suggested_parallelism": 0,
                  "expiry_pressure_jobs_per_hour": None, "forecasts": []}
        pressure = Decimal(0)
        if not reasons:
            fit = min(int(_balance(r, o) // number(o.costs[r.resource_id]["amount"])) for r in rows)
            record["estimated_startable_jobs"] = min(fit, task.ready_jobs)
            record["suggested_parallelism"] = min(fit, task.ready_jobs, policy.burst_cap)
            for r in rows:
                if r.window_type not in {"fixed", "billing_cycle"} or r.reset_at is None:
                    continue
                until = min(instant(r.reset_at), now + MAX_HORIZON_SECONDS)
                if task.deadline_at is not None:
                    until = min(until, instant(task.deadline_at))
                jobs, notes = _forecast(rows, o, now, until, task.ready_jobs, policy.burst_cap)
                cost = number(o.costs[r.resource_id]["amount"])
                hours = Decimal(str((until - now) / 3600))
                target_rate = Decimal(jobs) / hours
                baseline = None if o.useful_jobs_per_hour is None else number(o.useful_jobs_per_hour)
                acceleration = None if baseline is None else max(Decimal(0), target_rate - baseline)
                if acceleration is not None:
                    pressure = max(pressure, acceleration)
                record["forecasts"].append({"resource_id": r.resource_id, "unit": r.unit,
                    "completion_horizon": datetime.fromtimestamp(until, timezone.utc).isoformat(),
                    "jobs_under_declared_scenario": jobs,
                    "unspent_under_declared_scenario": str(max(Decimal(0), _balance(r, o) - cost * jobs)),
                    "target_useful_jobs_per_hour": str(target_rate.quantize(Decimal("0.000001"))),
                    "notes": notes})
            if o.useful_jobs_per_hour is not None:
                record["expiry_pressure_jobs_per_hour"] = str(pressure.quantize(Decimal("0.000001")))
            else:
                record["reasons"].append("USEFUL_THROUGHPUT_BASELINE_UNKNOWN_NO_URGENCY_INFERENCE")
            assessed.append((o, record, pressure))
        result["options"].append(record)
    if not assessed:
        result["status"] = "NO_ELIGIBLE_OPTION"
        return result
    tier_index = min(tiers[o.model_alias][0] for o, _, _ in assessed)
    choices = [entry for entry in assessed if tiers[entry[0].model_alias][0] == tier_index]
    reach = _precedence_reachability(policy, task.kind)
    available_providers = {o.provider for o, _, _ in choices}
    deferred = set().union(*(reach.get(provider, set()) for provider in available_providers))
    for o, record, _ in choices:
        if o.provider in deferred:
            record["reasons"].append("PREFERRED_PROVIDER_AVAILABLE")
            result["warnings"].append("STRICT_PREFERENCE_MAY_STRAND_FALLBACK_CAPACITY:" + o.provider)
    choices = [entry for entry in choices if entry[0].provider not in deferred]
    if not choices:
        result["status"] = "POLICY_PRECEDENCE_CONFLICT"
        return result
    # Prepaid first; useful depletion opportunity next; stable ID last. This is
    # an explainable initial heuristic, not a claim of global optimality.
    choices.sort(key=lambda entry: (number(entry[0].marginal_cash) > 0,
                                   number(entry[0].marginal_cash), -entry[2], entry[0].option_id))
    winner = choices[0][0]
    result.update(status="PREVIEW_READY", suggested_option=winner.option_id,
                  selected_tier=tiers[winner.model_alias][1])
    result["warnings"].append("ALTERNATIVE_SCENARIOS_NOT_ADDITIVE_NO_WORKER_SELECTED")
    return result


def preview_document(document: Mapping[str, Any]):
    if not isinstance(document, Mapping) or set(document) != {"schema", "as_of", "resources", "options", "task", "policy"}:
        raise QuotaEconomicsError("INVALID_INPUT_DOCUMENT")
    if document["schema"] != INPUT_SCHEMA:
        raise QuotaEconomicsError("INVALID_INPUT_SCHEMA")
    try:
        return preview(tuple(Resource(**row) for row in document["resources"]),
                       tuple(Option(**row) for row in document["options"]),
                       Task(**document["task"]), Policy(**document["policy"]), as_of=document["as_of"])
    except (TypeError, KeyError, AttributeError) as exc:
        raise QuotaEconomicsError("INVALID_INPUT_SHAPE") from None


def native_usage_amount(row: Mapping[str, Any]):
    """Consume a PR #7103 parser row without turning percentages into tokens.

    This does not bind accounts, deduplicate shared pools, select reset semantics,
    or establish coverage. The canonical owner must supply those facts separately.
    """
    if row.get("status") not in {"limited", "exhausted"}:
        return {"remaining": None, "limit": None, "unit": identity(row["metric"])}
    remaining, limit = row.get("remaining"), row.get("limit")
    if row.get("status") == "exhausted":
        if limit is not None and number(limit) > 0:
            return {"remaining": "0", "limit": str(number(limit)), "unit": identity(row["metric"])}
        return {"remaining": "0", "limit": "100", "unit": "percentage_points"}
    if remaining is not None and limit is not None:
        if number(remaining) > number(limit) or not number(limit):
            raise QuotaEconomicsError("INCONSISTENT_SOURCE_BALANCE")
        return {"remaining": str(number(remaining)), "limit": str(number(limit)), "unit": identity(row["metric"])}
    percent = row.get("reported_remaining_percent")
    if percent is not None:
        if number(percent) > 100:
            raise QuotaEconomicsError("INVALID_SOURCE_PERCENT")
        return {"remaining": str(number(percent)), "limit": "100", "unit": "percentage_points"}
    return {"remaining": None, "limit": None, "unit": identity(row["metric"])}
