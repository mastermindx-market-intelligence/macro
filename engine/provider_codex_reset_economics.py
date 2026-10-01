"""Pure Codex reset counterfactuals for Shared AI Provider Control.

This supplements, never replaces, provider_quota_economics. It consumes a frozen,
owner-qualified task prefix and native observations; it has no I/O, credentials,
clock, queue, claims, reset endpoint or dispatch path. Every result is advisory.
A forecast never establishes a real balance, entitlement, identity or permission.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction
from functools import lru_cache
import hashlib
import json
import re

SCHEMA = "mastermind.codex_reset_economics_preview/v1"
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


class ResetEconomicsError(ValueError):
    """Invalid, ambiguous, or unbounded owner input."""


@dataclass(frozen=True)
class Window:
    capacity: int
    remaining: int
    reserve: int
    reset_at: int
    period_seconds: int


@dataclass(frozen=True)
class BankedReset:
    reset_id: str
    expires_at: int


@dataclass(frozen=True)
class TaskQuote:
    task_id: str
    ready_at: int
    deadline: int
    duration_seconds: int | None
    short_cost: int | None
    weekly_cost: int | None
    utility: int = 1


@dataclass(frozen=True)
class AccountObservation:
    account_id: str
    shared_resource_id: str
    provider_model: str
    suitability_tier: str
    observation_id: str
    calibration_id: str
    observed_at: int
    valid_until: int
    short: Window
    weekly: Window
    banked_resets: tuple[BankedReset, ...]
    tasks: tuple[TaskQuote, ...]
    binding_verified: bool = False
    eligible: bool = False
    active_claims: int = 0
    effect_state: str = "UNKNOWN"
    evidence_kind: str = "unknown"
    # Forecast semantics must be supplied by the qualified native owner.
    renewal_semantics: str = "unknown"


@dataclass(frozen=True)
class PreviewPolicy:
    urgency_seconds: int = 86400
    max_observation_age_seconds: int = 600
    reset_latency_seconds: int = 30
    max_forecast_seconds: int = 604800
    max_states_per_account: int = 20000


@dataclass(frozen=True)
class _Path:
    steps: tuple[tuple[str, int, int, str | None], ...] = ()
    utility: int = 0
    nonexpiring_resets_spent: int = 0
    resets_spent: int = 0
    rescued_value: Fraction = Fraction(0)
    latency: int = 0
    normalized_burn: Fraction = Fraction(0)

    def score(self) -> tuple:
        return (self.utility, len(self.steps), -self.nonexpiring_resets_spent,
                self.rescued_value, -self.resets_spent, -self.normalized_burn, -self.latency)


def _integer(value: object, label: str, minimum: int = 0, maximum: int = 10**12) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ResetEconomicsError(f"invalid {label}")
    return value


def _identity(value: str) -> str:
    if not isinstance(value, str) or _ID.fullmatch(value) is None:
        raise ResetEconomicsError("invalid identity")
    return value


def _window(w: Window) -> None:
    if type(w) is not Window:
        raise ResetEconomicsError("invalid window")
    _integer(w.capacity, "capacity", 1)
    _integer(w.remaining, "remaining", maximum=w.capacity)
    _integer(w.reserve, "reserve", maximum=w.capacity)
    _integer(w.reset_at, "reset_at", 1)
    _integer(w.period_seconds, "period_seconds", 1, 2678400)


def _validate(a: AccountObservation, now: int, tier: str, policy: PreviewPolicy) -> str | None:
    if type(a) is not AccountObservation:
        raise ResetEconomicsError("invalid account observation")
    for value in (a.account_id, a.shared_resource_id, a.provider_model,
                  a.suitability_tier, a.observation_id, a.calibration_id):
        _identity(value)
    _window(a.short)
    _window(a.weekly)
    _integer(a.observed_at, "observed_at")
    _integer(a.valid_until, "valid_until")
    _integer(a.active_claims, "active_claims")
    if type(a.banked_resets) is not tuple or len(a.banked_resets) > 8:
        raise ResetEconomicsError("banked resets must be an explicit bounded tuple")
    for reset in a.banked_resets:
        if type(reset) is not BankedReset:
            raise ResetEconomicsError("invalid banked reset")
        _identity(reset.reset_id)
        _integer(reset.expires_at, "reset expiry", 1)
    if len({x.reset_id for x in a.banked_resets}) != len(a.banked_resets):
        raise ResetEconomicsError("duplicate banked reset")
    if type(a.tasks) is not tuple or len(a.tasks) > 12:
        raise ResetEconomicsError("task prefix must be a bounded tuple")
    measurements_unknown = False
    for task in a.tasks:
        if type(task) is not TaskQuote:
            raise ResetEconomicsError("invalid task quote")
        _identity(task.task_id)
        for name in ("ready_at", "deadline"):
            _integer(getattr(task, name), name)
        _integer(task.utility, "utility", 1, 10**6)
        if task.deadline < task.ready_at or task.deadline > now + policy.max_forecast_seconds:
            raise ResetEconomicsError("invalid or unbounded task horizon")
        if any(x is None for x in (task.duration_seconds, task.short_cost, task.weekly_cost)):
            measurements_unknown = True
        for name in ("duration_seconds", "short_cost", "weekly_cost"):
            if getattr(task, name) is not None:
                _integer(getattr(task, name), name, 1)
    if measurements_unknown:
        return "COST_OR_DURATION_UNKNOWN"
    if a.suitability_tier != tier:
        return "OUTSIDE_FIRST_LAWFUL_TIER"
    if a.binding_verified is not True or a.eligible is not True:
        return "BINDING_OR_ELIGIBILITY_UNPROVEN"
    if a.evidence_kind not in {"provider_reported", "exact"}:
        return "NATIVE_QUOTA_UNPROVEN"
    if a.effect_state != "CLEAR" or a.active_claims:
        return "ACCOUNT_EFFECT_OR_CLAIM_BUSY"
    if a.renewal_semantics != "first_use_after_reset":
        return "RENEWAL_SEMANTICS_UNKNOWN"
    if not a.observed_at <= now < a.valid_until or now - a.observed_at > policy.max_observation_age_seconds:
        return "STALE_OR_FUTURE_OBSERVATION"
    if min(a.short.reset_at, a.weekly.reset_at) <= now:
        return "OBSERVATION_CROSSED_RESET_BOUNDARY"
    return None


def _forecast(a: AccountObservation, now: int, policy: PreviewPolicy) -> _Path:
    """Compare work-conserving natural waits versus finite banked resets.

    Tasks retain the owner's order; only this idle account's forecast changes.
    Neither reordering the task queue nor multi-worker scheduling happens here.
    The state cap refuses the candidate instead of returning a truncated optimum.
    """
    horizon = max((t.deadline for t in a.tasks), default=now)
    credits = tuple(sorted(a.banked_resets, key=lambda c: (c.expires_at, c.reset_id)))
    expanded = 0

    def urgency(deadline: int) -> Fraction:
        return Fraction(max(0, policy.urgency_seconds - max(0, deadline - now)), policy.urgency_seconds)

    def refresh(balance: int, reset_at: int, start: int, window: Window) -> tuple[int, int]:
        # Zero is forecast-only: timer awaits first use, never a native observation.
        return (window.capacity, 0) if reset_at and start >= reset_at else (balance, reset_at)

    @lru_cache(maxsize=None)
    def visit(i: int, t: int, sr: int, sa: int, wr: int, wa: int, mask: int, original_window: bool) -> _Path:
        nonlocal expanded
        expanded += 1
        if expanded > policy.max_states_per_account:
            raise ResetEconomicsError("FORECAST_STATE_BUDGET_EXCEEDED")
        if i == len(a.tasks):
            return _Path()
        task = a.tasks[i]
        cost_s, cost_w, duration = task.short_cost, task.weekly_cost, task.duration_seconds
        assert cost_s is not None and cost_w is not None and duration is not None
        if cost_s > a.short.capacity - a.short.reserve or cost_w > a.weekly.capacity - a.weekly.reserve:
            return _Path()
        ready = max(t, task.ready_at)
        latest = task.deadline - duration
        options: list[tuple[int, int, int, int, int, int, str | None, Fraction, int]] = []
        # Earliest natural availability; an expired timer only starts on use.
        ns, nsa = refresh(sr, sa, ready, a.short)
        nw, nwa = refresh(wr, wa, ready, a.weekly)
        natural = ready
        if ns - a.short.reserve < cost_s:
            natural = max(natural, nsa)
        if nw - a.weekly.reserve < cost_w:
            natural = max(natural, nwa)
        ns, nsa = refresh(sr, sa, natural, a.short)
        nw, nwa = refresh(wr, wa, natural, a.weekly)
        if natural <= latest and ns - a.short.reserve >= cost_s and nw - a.weekly.reserve >= cost_w:
            options.append((natural, ns, nsa, nw, nwa, mask, None, Fraction(0), 0))
        # Reset immediately before useful demand, never just to start a timer.
        for ci, credit in enumerate(credits):
            start = ready + policy.reset_latency_seconds
            if not mask & (1 << ci) or start >= credit.expires_at or start > latest:
                continue
            bs, bsa = refresh(sr, sa, ready, a.short)
            bw, bwa = refresh(wr, wa, ready, a.weekly)
            if bs == a.short.capacity and bw == a.weekly.capacity:
                continue  # provider would not consume a no-op reset
            # Resource score is task-equivalent capacity, not cash or percentages
            # compared across unlike plans. Cap rescue at actual remaining demand.
            demand = sum(t.weekly_cost or 0 for t in a.tasks[i:])
            gain = Fraction(min(a.weekly.capacity - bw, demand), cost_w)
            forfeited = Fraction(bw, cost_w)
            lost_near_refill = Fraction(min(a.weekly.capacity, demand), cost_w) * urgency(bwa) if bwa else Fraction(0)
            rescue = gain * urgency(credit.expires_at) - forfeited - lost_near_refill
            options.append((start, a.short.capacity, 0, a.weekly.capacity, 0,
                            mask ^ (1 << ci), credit.reset_id, rescue,
                            int(credit.expires_at > horizon)))
        best = _Path()
        for start, bs, bsa, bw, bwa, next_mask, credit_id, rescue, nonexpiring in options:
            end = start + duration
            tail = visit(i + 1, end, bs - cost_s,
                         bsa or start + a.short.period_seconds,
                         bw - cost_w, bwa or start + a.weekly.period_seconds, next_mask,
                         original_window and credit_id is None and start < a.weekly.reset_at)
            # Only rescue capacity from the original, observed weekly window.
            saved = Fraction(cost_w, cost_w) * urgency(a.weekly.reset_at) if original_window and credit_id is None and start < a.weekly.reset_at else Fraction(0)
            candidate = _Path(((task.task_id, start, end, credit_id),) + tail.steps,
                              task.utility + tail.utility,
                              nonexpiring + tail.nonexpiring_resets_spent,
                              int(credit_id is not None) + tail.resets_spent,
                              rescue + saved + tail.rescued_value,
                              task.utility * (end - task.ready_at) + tail.latency,
                              max(Fraction(cost_s, a.short.capacity), Fraction(cost_w, a.weekly.capacity)) + tail.normalized_burn)
            if candidate.score() > best.score():
                best = candidate
        return best

    return visit(0, now, a.short.remaining, a.short.reset_at, a.weekly.remaining,
                 a.weekly.reset_at, (1 << len(credits)) - 1, True)


def preview_codex_resets(observations: tuple[AccountObservation, ...], *, now: int,
                         first_lawful_tier: str, preferred_account_id: str | None = None,
                         policy: PreviewPolicy = PreviewPolicy()) -> dict:
    """Return replayable projections; the native owner must revalidate and claim.

    Missing live evidence refuses a candidate. Structural ambiguity refuses the
    entire request. A banked-reset proposal is not permission to press the button.
    """
    _integer(now, "now")
    _identity(first_lawful_tier)
    if preferred_account_id is not None:
        _identity(preferred_account_id)
    if type(policy) is not PreviewPolicy:
        raise ResetEconomicsError("invalid policy")
    for name, value in asdict(policy).items():
        _integer(value, name, 1, 2678400)
    if policy.max_observation_age_seconds > 600 or policy.max_states_per_account > 100000 or policy.max_forecast_seconds > 604800:
        raise ResetEconomicsError("policy exceeds hard safety bounds")
    if type(observations) is not tuple or len(observations) > 32:
        raise ResetEconomicsError("observations must be a bounded tuple")
    if any(type(a) is not AccountObservation for a in observations):
        raise ResetEconomicsError("invalid account observation")
    reasons = {a.account_id: _validate(a, now, first_lawful_tier, policy) for a in observations}
    for field in ("account_id", "shared_resource_id"):
        if len({getattr(a, field) for a in observations}) != len(observations):
            raise ResetEconomicsError("duplicate account or shared quota resource")
    # Models may differ within an already qualified tier, never task identity,
    # queue order, readiness, deadline or value. Only native cost/duration varies.
    signatures = {tuple((t.task_id, t.ready_at, t.deadline, t.utility) for t in a.tasks) for a in observations}
    if len(signatures) > 1:
        raise ResetEconomicsError("task prefixes do not describe the same owner demand")
    if observations and len({t.task_id for t in observations[0].tasks}) != len(observations[0].tasks):
        raise ResetEconomicsError("duplicate task identity")
    ordered = tuple(sorted(observations, key=lambda a: a.account_id))
    inputs = {"observations": [asdict(a) | {"banked_resets": [asdict(c) for c in sorted(a.banked_resets, key=lambda c: (c.expires_at, c.reset_id))]} for a in ordered], "now": now,
              "first_lawful_tier": first_lawful_tier, "preferred_account_id": preferred_account_id,
              "policy": asdict(policy)}
    digest = hashlib.sha256(json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    candidates, ranked = [], []
    for a in ordered:
        reason = reasons[a.account_id]
        path = _Path()
        if not reason and a.tasks:
            try:
                path = _forecast(a, now, policy)
            except ResetEconomicsError as exc:
                reason = str(exc)
        if not reason and not path.steps:
            reason = "NO_APPROVED_DEMAND" if not a.tasks else "NO_TASK_FITS_BEFORE_DEADLINE"
        row = {"account_id": a.account_id, "provider_model": a.provider_model,
               "observation_id": a.observation_id, "calibration_id": a.calibration_id,
               "eligible_for_preview": reason is None, "reason": reason,
               "weekly_remaining": a.weekly.remaining, "weekly_capacity": a.weekly.capacity,
               "short_remaining": a.short.remaining, "short_capacity": a.short.capacity,
               "weekly_reset_at": a.weekly.reset_at, "short_reset_at": a.short.reset_at,
               "banked_reset_count": len([c for c in a.banked_resets if c.expires_at > now]),
               "nearest_banked_expiry": min((c.expires_at for c in a.banked_resets if c.expires_at > now), default=None),
               "completed_utility_forecast": path.utility, "completed_tasks_forecast": len(path.steps),
               "banked_resets_spent_forecast": path.resets_spent,
               "resource_value_forecast": str(path.rescued_value),
               "normalized_burn_forecast": str(path.normalized_burn),
               "steps_forecast": [{"task_id": tid, "start_at": start, "finish_at": end,
                                   "banked_reset_id": reset} for tid, start, end, reset in path.steps]}
        candidates.append(row)
        if reason is None:
            # Existing focus is only a final tie breaker, never a priority gate.
            ranked.append((path.score() + (a.account_id == preferred_account_id,
                                           -Fraction(a.weekly.remaining, a.weekly.capacity)), a.account_id))
    ranked.sort(key=lambda r: r[1])
    ranked.sort(key=lambda r: r[0], reverse=True)
    selected = ranked[0][1] if ranked else None
    row = next((r for r in candidates if r["account_id"] == selected), None)
    step = row["steps_forecast"][0] if row else None
    action = "NONE"
    if step:
        action = "PROPOSE_BANKED_RESET_THEN_RUN" if step["banked_reset_id"] else ("RUN_CANDIDATE" if step["start_at"] == now else "WAIT_FOR_NATIVE_WINDOW_OR_DEMAND")
    result = {"schema": SCHEMA, "authority": "NONE_PREVIEW_ONLY", "live_admission": False,
              "revalidate_before_effect": True, "input_digest": digest,
              "status": "PREVIEW_READY" if selected else "NO_ELIGIBLE_CANDIDATE",
              "selected_account_id": selected, "proposed_action": action,
              "first_lawful_tier": first_lawful_tier, "candidates": candidates}
    result["preview_digest"] = hashlib.sha256(json.dumps(result, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return result
