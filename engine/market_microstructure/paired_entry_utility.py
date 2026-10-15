"""C15 paired *hypothetical* entry utility, over independently frozen source receipts.

This pure research leaf has no source ownership, clock oracle, trial ledger,
policy selector, broker/execution path, or publication authority. Original
candidate decisions, policy freezes, source/quote availability, qualified
calendar, and actual consumer delivery must all be proved by their owners.

For same-candidate comparison the 30-trading-minute endpoint comes from the
original study/calendar owner. The asserted elapsed_minutes and receipt here
ARE NOT calendar authentication. Simulated quote crossing is NOT an actual fill.
No statistical promotion, alert, ranking, live execution, or sizing authority.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone, time
from zoneinfo import ZoneInfo
from lib.nyse_calendar import is_session
from decimal import Decimal, InvalidOperation
from fractions import Fraction

from engine.market_microstructure.pressure_response import MODES, _bounded_decimal

SCHEMA = "equity.c15_paired_entry_utility_research/v0"
SHA = re.compile(r"^[a-f0-9]{64}$")
SYMBOL = re.compile(r"^[A-Z][A-Z0-9.-]{0,19}$")
FIXED = re.compile(r"^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
STATES = frozenset({"SIMULATED_FULL", "FROZEN_ABSTAIN", "UNOBSERVABLE"})
REASONS = frozenset({"QUOTE_MISSING", "SOURCE_GAP", "UNQUALIFIED_MARKET", "CANCEL_UNRESOLVED"})
MINUTE_NS = 60_000_000_000
MAX_QUOTE_AGE_NS = 5_000_000_000

# The original candidate's economics and receipt vintages must remain fixed
# between the incumbent frozen denominator and each later outcome report.
# Input availability, direction, intended Q0, M0, deadline and original
# midpoint quote are all part of candidate identity; a candidate_id/source
# SHA alone cannot prevent retroactive policy/opportunity selection.
COHORT_CANDIDATE_FREEZE_FIELDS = (
    "candidate_source_available_ns", "deadline_ns", "direction",
    "research_quantity", "initial_midpoint_usd", "max_quote_age_ns",
    "anchor_quote_event_ns", "anchor_quote_available_ns",
    "anchor_quote_receipt_sha256", "anchor_bid_usd", "anchor_ask_usd",
    "anchor_bid_size_shares", "anchor_ask_size_shares",
)

# Original study registration binds policy/control receipts and scalar research
# fee assumptions independently of the later outcome. State (entry/abstain/
# missing) may develop through the allowed decision window; the POLICY freeze
# and execution-fee schedule may not be retuned after observing that outcome.
COHORT_POLICY_FREEZE_FIELDS = (
    "baseline_policy_receipt_sha256", "baseline_policy_frozen_ns",
    "challenger_policy_receipt_sha256", "challenger_policy_frozen_ns",
    "challenger_consumer_receipt_sha256", "challenger_consumer_available_ns",
    "baseline_fees_usd", "challenger_fees_usd",
)


def _dict(value, keys, label):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError(label + ": unexpected/missing fields")
    return value


def _sha(value, label):
    if type(value) is not str or not SHA.fullmatch(value):
        raise ValueError(label + ": digest missing")
    return value


def _clock(value, label):
    if type(value) is not int or not 0 < value <= (1 << 63) - 1:
        raise ValueError(label + ": native clock invalid")
    return value


def _money(value, label, *, positive=False):
    # Accepted R0 input width and fixed-point resource policy; no float JSON.
    if type(value) is not str or not FIXED.fullmatch(value) or len(value) > 128:
        raise ValueError(label + ": expected bounded nonnegative fixed decimal")
    try:
        dec = Decimal(value)
        _bounded_decimal(dec, label)
    except (ValueError, InvalidOperation) as exc:
        raise ValueError(label + ": invalid source decimal") from exc
    if positive and dec <= 0:
        raise ValueError(label + ": must be positive")
    return Fraction(dec)


def _exact_bp(value):
    """Exact rational source, bounded 12dp display with integer half-even.

    No Decimal context/quantize precision cliff even for accepted 1024-digit
    evidence ratios. The display may round to signed zero; exact numerator and
    denominator always remain unrounded and authoritative for research math.
    """
    scale = 10 ** 12
    scaled, remainder = divmod(abs(value.numerator) * scale, value.denominator)
    double_rem = remainder * 2
    if double_rem > value.denominator or (
        double_rem == value.denominator and scaled % 2 == 1
    ):
        scaled += 1
    whole, fractional = divmod(scaled, scale)
    prefix = "-" if value.numerator < 0 else ""
    return {
        "numerator": str(value.numerator), "denominator": str(value.denominator),
        "display_bps_12dp": f"{prefix}{whole}.{fractional:012d}",
        "display_only_rounded": True,
    }


def _best_quote(row, prefix, label):
    bid = _money(row[prefix + "_bid_usd"], label+".bid", positive=True)
    ask = _money(row[prefix + "_ask_usd"], label+".ask", positive=True)
    bid_size = _money(row[prefix + "_bid_size_shares"], label+".bid_size", positive=True)
    ask_size = _money(row[prefix + "_ask_size_shares"], label+".ask_size", positive=True)
    if bid >= ask:
        raise ValueError(label+": locked or crossed quote")
    return bid, ask, bid_size, ask_size


def _policy(row, *, role, candidate, cutoff_ns, max_quote_age_ns, anchor, size):
    quote_fields = tuple(prefix + "_" + suffix for prefix in ("entry", "exit")
        for suffix in ("bid_usd", "ask_usd", "bid_size_shares", "ask_size_shares"))
    keys = {
        "candidate_id", "role", "state", "policy_receipt_sha256", "policy_frozen_ns",
        "consumer_available_ns", "consumer_receipt_sha256", "entry_decision_ns",
        "entry_quote_event_ns", "entry_quote_available_ns",
        "entry_quote_receipt_sha256", "exit_quote_event_ns",
        "exit_quote_available_ns", "exit_quote_receipt_sha256",
        "fees_usd", "abstain_receipt_sha256", "abstain_available_ns",
        "unobservable_reason", *quote_fields,
    }
    p = _dict(row, keys, role)
    if p["candidate_id"] != candidate["candidate_id"] or p["role"] != role:
        raise ValueError(role + ": unrelated candidate or policy")
    _sha(p["policy_receipt_sha256"], role + ".policy")
    frozen = _clock(p["policy_frozen_ns"], role + ".freeze")
    if frozen >= candidate["decision_ns"]:
        raise ValueError(role + ": policy not frozen before candidate")
    consumer = p["consumer_available_ns"]
    if role == "challenger":
        if consumer is None or p["consumer_receipt_sha256"] is None:
            return None, "OVERLAY_CONSUMER_AVAILABILITY_NOT_PROVEN"
        _sha(p["consumer_receipt_sha256"], role+".consumer_receipt")
        _clock(consumer, role + ".consumer")
        if consumer >= candidate["decision_ns"]:
            return None, "OVERLAY_ARRIVED_AFTER_ORIGINAL_DECISION"
    elif consumer is not None or p["consumer_receipt_sha256"] is not None:
        raise ValueError("baseline: overlay claim forbidden")
    status = p["state"]
    if type(status) is not str or status not in STATES:
        raise ValueError(role + ": invalid state")
    forbidden_for_source_gap = (
        "entry_decision_ns", "entry_quote_event_ns", "entry_quote_available_ns",
        "entry_quote_receipt_sha256", "exit_quote_event_ns",
        "exit_quote_available_ns", "exit_quote_receipt_sha256",
        "fees_usd", "abstain_receipt_sha256", "abstain_available_ns",
        *quote_fields,
    )
    if status == "UNOBSERVABLE":
        reason = p["unobservable_reason"]
        if type(reason) is not str or reason not in REASONS:
            raise ValueError(role + ": missing typed source failure")
        if any(p[k] is not None for k in forbidden_for_source_gap):
            raise ValueError(role + ": source-failure masquerades as fill/abstain")
        return None, p["unobservable_reason"]
    if status == "FROZEN_ABSTAIN":
        _sha(p["abstain_receipt_sha256"], role + ".abstain")
        when = _clock(p["entry_decision_ns"], role + ".abstain_decision")
        available = _clock(p["abstain_available_ns"], role + ".abstain_available")
        if not candidate["decision_ns"] <= when <= available < candidate["deadline_ns"]:
            raise ValueError(role + ": abstention not knowable within frozen deadline")
        if any(p[k] is not None for k in (
            "entry_quote_event_ns", "entry_quote_available_ns", "entry_quote_receipt_sha256",
            "exit_quote_event_ns", "exit_quote_available_ns", "exit_quote_receipt_sha256",
            "fees_usd", "unobservable_reason", *quote_fields,
        )):
            raise ValueError(role + ": source unknown cannot be coded as abstention")
        return Fraction(0), None
    # Quote-crossing research simulation; no actual execution/order filled.
    if (p["abstain_receipt_sha256"] is not None or
            p["abstain_available_ns"] is not None or
            p["unobservable_reason"] is not None):
        raise ValueError(role + ": incompatible fill state")
    start = _clock(p["entry_decision_ns"], role + ".entry")
    event = _clock(p["entry_quote_event_ns"], role + ".entry_quote_event")
    available = _clock(p["entry_quote_available_ns"], role + ".entry_quote_receipt_time")
    exit_event = _clock(p["exit_quote_event_ns"], role + ".exit_quote_event")
    exit_avail = _clock(p["exit_quote_available_ns"], role + ".exit_quote_receipt_time")
    _sha(p["entry_quote_receipt_sha256"], role + ".entry_receipt")
    _sha(p["exit_quote_receipt_sha256"], role + ".exit_receipt")
    if not (candidate["decision_ns"] <= start <= candidate["deadline_ns"]
            < candidate["horizon_end_ns"]):
        raise ValueError(role + ": entry out of preregistered window")
    if not (event < start and event <= available < start and
            0 <= start - event <= max_quote_age_ns):
        return None, "ENTRY_QUOTE_NOT_KNOWABLE_OR_STALE"
    if not (exit_event < candidate["horizon_end_ns"]
            and exit_event <= exit_avail < candidate["horizon_end_ns"]
            and exit_avail < cutoff_ns
            and 0 <= candidate["horizon_end_ns"] - exit_event <= max_quote_age_ns):
        return None, "EXIT_QUOTE_NOT_KNOWABLE_OR_STALE"
    eb,ea,ebsize,easize = _best_quote(p,"entry",role+".entry")
    xb,xa,xbsize,xasize = _best_quote(p,"exit",role+".exit")
    if candidate["direction"] == 1:
        entry,exit_price = ea,xb
        enough = easize >= size and xbsize >= size
    else:
        entry,exit_price = eb,xa
        enough = ebsize >= size and xasize >= size
    if not enough:
        return None, "INSUFFICIENT_DISPLAYED_TOP_SIZE"
    fees = _money(p["fees_usd"], role + ".fees")
    # The same Q0 and M0 are frozen once for both legs. Quote-side crossing
    # includes spread once; do not re-charge spread through the fees field.
    delta = Fraction(candidate["direction"]) * size * (exit_price - entry) - fees
    return Fraction(10000) * delta / (size * anchor), None


def _policy_freeze_snapshot(policy, role, candidate):
    """Conserve caller-supplied original study policy receipts for every outcome.

    These are asserted identities only, NEVER source/authentication receipts
    verified against actual original bytes or a new trial registration plane.
    """
    if (type(policy) is not dict
            or policy.get("candidate_id") != candidate["candidate_id"]
            or policy.get("role") != role):
        raise ValueError(role + ": original frozen policy identity invalid")
    state = policy.get("state")
    if type(state) is not str or state not in STATES:
        raise ValueError(role + ": invalid state")
    receipt = _sha(policy.get("policy_receipt_sha256"), role + ".policy")
    frozen = _clock(policy.get("policy_frozen_ns"), role + ".freeze")
    if frozen >= candidate["decision_ns"]:
        raise ValueError(role + ": policy not frozen before original candidate")
    fee = policy.get("fees_usd")
    if state == "SIMULATED_FULL":
        _money(fee, role + ".frozen_fees")
    # Do not preempt the established, more specific _policy errors for
    # malformed missing/abstention states. In mature NORMAL paths _policy
    # rejects any fee when there was no simulated fill; the cohort also
    # refuses charging fees for a reported frozen abstention.
    result = {
        role + "_policy_receipt_sha256": receipt,
        role + "_policy_frozen_ns": frozen,
        role + "_policy_state": state,
        role + "_fees_usd": fee,
    }
    consumer = policy.get("consumer_available_ns")
    consumer_receipt = policy.get("consumer_receipt_sha256")
    if role == "baseline":
        if consumer is not None or consumer_receipt is not None:
            raise ValueError("baseline: overlay claim forbidden")
    else:
        # A missing or AFTER-T overlay is still an UNOBSERVABLE/late source,
        # not a zero-PnL policy action. Preserve the actual claimed values.
        if consumer is not None:
            _clock(consumer, "challenger.consumer")
        if consumer_receipt is not None:
            _sha(consumer_receipt, "challenger.consumer_receipt")
        result["challenger_consumer_available_ns"] = consumer
        result["challenger_consumer_receipt_sha256"] = consumer_receipt
    return result


def evaluate_same_candidate(*, candidate, baseline, challenger,
                            evaluation_cutoff_ns, source_watermark_ns,
                            watermark_received_ns, market_health,
                            market_health_receipt_sha256):
    """Calculate paired *research-only* utility without any live authority.

    The caller must obtain original receipts, candidate/policy freeze, and
    qualified source/NYSE trading-time evidence externally. This function
    validates consistency but cannot authenticate market data or simulated fills.
    """
    keys = {
        "candidate_id", "ticker", "session", "source_mode",
        "source_receipt_sha256", "candidate_source_available_ns",
        "decision_ns", "deadline_ns", "horizon_end_ns",
        "horizon_trading_minutes", "calendar_receipt_sha256",
        "direction", "research_quantity", "initial_midpoint_usd",
        "anchor_quote_event_ns", "anchor_quote_available_ns",
        "anchor_quote_receipt_sha256", "anchor_bid_usd", "anchor_ask_usd",
        "anchor_bid_size_shares", "anchor_ask_size_shares",
        "max_quote_age_ns",
    }
    c = _dict(candidate, keys, "candidate")
    if (type(c["candidate_id"]) is not str or not 0 < len(c["candidate_id"]) <= 128
            or type(c["ticker"]) is not str or not SYMBOL.fullmatch(c["ticker"])
            or type(c["session"]) is not str or not re.fullmatch(r"\d{4}-\d{2}-\d{2}:RTH", c["session"])):
        raise ValueError("candidate: invalid frozen identity")
    if type(c["source_mode"]) is not str or c["source_mode"] not in MODES:
        raise ValueError("candidate: invalid source mode")
    _sha(c["source_receipt_sha256"], "candidate.receipt")
    source_available = _clock(c["candidate_source_available_ns"], "candidate.source_available")
    _sha(c["calendar_receipt_sha256"], "calendar.receipt")
    _sha(market_health_receipt_sha256, "market_health.receipt")
    decision = _clock(c["decision_ns"], "candidate.decision")
    if source_available >= decision:
        raise ValueError("candidate: original source arrived after decision")
    deadline = _clock(c["deadline_ns"], "candidate.deadline")
    endpoint = _clock(c["horizon_end_ns"], "candidate.endpoint")
    if not decision <= deadline < endpoint:
        raise ValueError("candidate: invalid entry deadline/horizon")
    if endpoint - decision != 30 * MINUTE_NS:
        raise ValueError("candidate: nominal same-session 30-minute horizon mismatch")
    # Reuse incumbent full-session holiday reference (no duplicate calendar).
    # Its early-close/one-off coverage is deliberately NOT source certification.
    et = ZoneInfo("America/New_York")
    def nominal_rth(ns):
        local = datetime.fromtimestamp(ns // 1_000_000_000, timezone.utc).astimezone(et)
        return local, local.timetz().replace(tzinfo=None)
    opened, from_time = nominal_rth(decision)
    closed, to_time = nominal_rth(endpoint)
    if (not is_session(opened.date()) or opened.date() != closed.date()
            or c["session"] != opened.date().isoformat() + ":RTH"
            or not time(9, 30) <= from_time < time(16, 0)
            or not time(9, 30) < to_time <= time(16, 0)):
        raise ValueError("candidate: outside nominal NYSE RTH session")
    # This is an external calendar assertion, NOT a verified 30-min horizon.
    if type(c["horizon_trading_minutes"]) is not int or c["horizon_trading_minutes"] != 30:
        raise ValueError("candidate: unexpected trading-minute horizon")
    if type(c["direction"]) is not int or c["direction"] not in (-1, 1):
        raise ValueError("candidate: direction must come from incumbent")
    maxage = _clock(c["max_quote_age_ns"], "candidate.max_quote_age")
    if maxage > MAX_QUOTE_AGE_NS:
        raise ValueError("candidate: quote freshness exceeds five seconds")
    size = _money(c["research_quantity"], "research_quantity", positive=True)
    anchor = _money(c["initial_midpoint_usd"], "initial_midpoint", positive=True)
    # The initial *notional denominator* must be grounded to a single
    # source-identified quote at the ORIGINAL candidate cutoff. A caller
    # cannot change M0 independently to alter the reported utility bps.
    anchor_event = _clock(c["anchor_quote_event_ns"], "candidate.anchor_event")
    anchor_available = _clock(c["anchor_quote_available_ns"], "candidate.anchor_available")
    _sha(c["anchor_quote_receipt_sha256"], "candidate.anchor_receipt")
    if not (anchor_event < decision and anchor_event <= anchor_available < decision
            and decision - anchor_event <= maxage):
        raise ValueError("candidate: anchor quote not knowable at original decision")
    anchor_bid, anchor_ask, _, _ = _best_quote(c, "anchor", "candidate.anchor")
    if anchor != (anchor_bid + anchor_ask) / 2:
        raise ValueError("candidate: anchor midpoint differs from source quote")
    cutoff = _clock(evaluation_cutoff_ns, "evaluation_cutoff")
    through = _clock(source_watermark_ns, "source_watermark")
    arrived = _clock(watermark_received_ns, "watermark_received")
    if arrived < through:
        raise ValueError("watermark receipt before native source time")
    if market_health not in ("NORMAL", "HALTED", "UNKNOWN"):
        raise ValueError("market health outside frozen source categories")
    policy_freeze = {
        **_policy_freeze_snapshot(baseline, "baseline", c),
        **_policy_freeze_snapshot(challenger, "challenger", c),
    }
    identity = dict(
        schema=SCHEMA, candidate_id=c["candidate_id"], ticker=c["ticker"],
        session=c["session"], source_mode=c["source_mode"],
        candidate_source_receipt_sha256=c["source_receipt_sha256"],
        calendar_receipt_sha256=c["calendar_receipt_sha256"],
        **{key: c[key] for key in COHORT_CANDIDATE_FREEZE_FIELDS},
        **policy_freeze,
        horizon_trading_minutes=30, original_decision_ns=decision,
        horizon_end_ns=endpoint, evaluation_cutoff_ns=cutoff,
        policy_count=2, forward_outcome_available_to_original_decision=False,
        source_authenticated=False, simulated_execution_not_fill=True,
        calendar_qualified_by_this_function=False, actual_consumer_delivery_proven=False,
        predictive_rank_trading_alert_authority=False, prospective_promotion=False,
        supplied_input_first_knowable_ns=None,
        supplied_input_first_knowable_not_consumer_receipt=True,
        primary_policy_authority="RESEARCH_DIAGNOSTIC_ONLY",
    )
    if cutoff <= endpoint or through < endpoint or arrived >= cutoff:
        return {**identity, "state":"NOT_MATURE", "reason":"HORIZON_OR_WATERMARK_NOT_KNOWABLE",
                "baseline_bps":None, "challenger_bps":None, "delta_bps":None}
    if market_health != "NORMAL":
        return {**identity, "state":"CENSORED", "reason":"HALTED_OR_UNKNOWN_MARKET",
                "baseline_bps":None, "challenger_bps":None, "delta_bps":None}
    b,br = _policy(baseline,role="baseline",candidate=c,cutoff_ns=cutoff,
                   max_quote_age_ns=maxage,anchor=anchor,size=size)
    h,hr = _policy(challenger,role="challenger",candidate=c,cutoff_ns=cutoff,
                   max_quote_age_ns=maxage,anchor=anchor,size=size)
    if br or hr:
        return {**identity,"state":"UNOBSERVABLE", "reason":{"baseline":br,"challenger":hr},
                "baseline_bps":None,"challenger_bps":None,"delta_bps":None}
    if baseline["state"] == "SIMULATED_FULL" and challenger["state"] == "SIMULATED_FULL":
        # Both arms liquidate at the SAME H, same source generation and market.
        # Different terminal quotes create a fake policy delta.
        terminal_fields = (
            "exit_quote_event_ns", "exit_quote_available_ns",
            "exit_quote_receipt_sha256", "exit_bid_usd", "exit_ask_usd",
            "exit_bid_size_shares", "exit_ask_size_shares",
        )
        if any(baseline[k] != challenger[k] for k in terminal_fields):
            raise ValueError("policy arms contradict common terminal quote")
    assert b is not None and h is not None
    # Only the supplied input-component arrival lower bound; never pretend
    # a real Terminal consumer received the result at this clock.
    ready_times = [arrived]
    for policy in (baseline, challenger):
        ready_times.append(
            policy["exit_quote_available_ns"] if policy["state"] == "SIMULATED_FULL"
            else policy["abstain_available_ns"]
        )
    return {**identity,"state":"PAIRED_RESEARCH_UTILITY", "reason":None,
            "supplied_input_first_knowable_ns":max(ready_times),
            "baseline_bps":_exact_bp(b),"challenger_bps":_exact_bp(h),
            "delta_bps":_exact_bp(h-b)}



# C15's externally frozen candidate registry is the denominator owner.
# This is a pure research-only reconciliation, NOT another trial ledger, source
# registry, verification signature, causal estimator, or rank/trade control.
COHORT_SCHEMA = "equity.c15_paired_utility_accounting_research/v0"
MAX_COHORT_CANDIDATES = 1000
COHORT_STATES = frozenset({
    "PAIRED_RESEARCH_UTILITY", "NOT_MATURE", "CENSORED", "UNOBSERVABLE",
})
_CANON_SIGNED = re.compile(r"^(?:0|[1-9][0-9]*|-[1-9][0-9]*)$")


def _frozen_paired_rational(value, label):
    row = _dict(value, {
        "numerator", "denominator", "display_bps_12dp",
        "display_only_rounded",
    }, label)
    numerator, denominator = row["numerator"], row["denominator"]
    if (type(numerator) is not str or type(denominator) is not str
            or len(numerator) > 1024 or len(denominator) > 1024
            or _CANON_SIGNED.fullmatch(numerator) is None
            or not re.fullmatch(r"[1-9][0-9]*", denominator)):
        raise ValueError(label + ": noncanonical bounded exact ratio")
    ratio = Fraction(int(numerator), int(denominator))
    if row != _exact_bp(ratio):
        raise ValueError(label + ": ratio/display incompatible")
    return ratio


def reconcile_frozen_candidate_cohort(*, expected_candidates,
                                      supplied_evaluations,
                                      frozen_manifest_sha256):
    """Account for EVERY externally frozen incumbent candidate.

    Missing candidates and censored/immature/unknown paths remain in the
    original denominator, never quietly discarded as favorable abstentions.
    Completed-pair mean is *measured subset only*: no population inference,
    trial ledger write, market/source authentication, or trading promotion.
    """
    _sha(frozen_manifest_sha256, "cohort.manifest")
    if (type(expected_candidates) not in (tuple, list)
            or not 1 <= len(expected_candidates) <= MAX_COHORT_CANDIDATES
            or type(supplied_evaluations) not in (tuple, list)
            or len(supplied_evaluations) > len(expected_candidates)):
        raise ValueError("cohort: invalid frozen denominator or report budget")

    expected = {}
    modes = set()
    for candidate in expected_candidates:
        e = _dict(candidate, {
            "candidate_id", "ticker", "session", "source_mode",
            "original_decision_ns", "horizon_end_ns",
            "source_receipt_sha256", "calendar_receipt_sha256",
            *COHORT_CANDIDATE_FREEZE_FIELDS,
            *COHORT_POLICY_FREEZE_FIELDS,
        }, "frozen_candidate")
        key = e["candidate_id"]
        if (type(key) is not str or not 0 < len(key) <= 128
                or key in expected
                or type(e["ticker"]) is not str or SYMBOL.fullmatch(e["ticker"]) is None
                or type(e["session"]) is not str
                or re.fullmatch(r"\d{4}-\d{2}-\d{2}:RTH", e["session"]) is None):
            raise ValueError("cohort: duplicate/invalid original candidate")
        _sha(e["source_receipt_sha256"], "candidate.source")
        _sha(e["calendar_receipt_sha256"], "candidate.calendar")
        start = _clock(e["original_decision_ns"], "candidate.decision")
        end = _clock(e["horizon_end_ns"], "candidate.horizon")
        if (end - start != 30 * MINUTE_NS
                or type(e["source_mode"]) is not str
                or e["source_mode"] not in MODES):
            raise ValueError("cohort: original horizon or source mode inconsistent")
        source_available = _clock(
            e["candidate_source_available_ns"], "frozen_candidate.source_available"
        )
        deadline = _clock(e["deadline_ns"], "frozen_candidate.deadline")
        maxage = _clock(e["max_quote_age_ns"], "frozen_candidate.max_quote_age")
        if (not source_available < start <= deadline < end
                or maxage > MAX_QUOTE_AGE_NS):
            raise ValueError("cohort: frozen candidate timing constraints invalid")
        if type(e["direction"]) is not int or e["direction"] not in (-1, 1):
            raise ValueError("cohort: frozen candidate incumbent direction invalid")
        _money(e["research_quantity"], "frozen_candidate.research_quantity", positive=True)
        anchor = _money(
            e["initial_midpoint_usd"], "frozen_candidate.initial_midpoint", positive=True
        )
        event = _clock(e["anchor_quote_event_ns"], "frozen_candidate.anchor_event")
        available = _clock(
            e["anchor_quote_available_ns"], "frozen_candidate.anchor_available"
        )
        _sha(e["anchor_quote_receipt_sha256"], "frozen_candidate.anchor_receipt")
        if (not event < start or not event <= available < start
                or start - event > maxage):
            raise ValueError("cohort: frozen candidate original quote is not prior")
        original_bid, original_ask, _, _ = _best_quote(
            e, "anchor", "frozen_candidate.anchor"
        )
        if anchor != (original_bid + original_ask) / 2:
            raise ValueError("cohort: frozen candidate original midpoint disagrees")
        for role in ("baseline", "challenger"):
            _sha(e[role + "_policy_receipt_sha256"], "frozen_policy."+role)
            policy_frozen = _clock(
                e[role + "_policy_frozen_ns"], "frozen_policy."+role+".frozen"
            )
            if policy_frozen >= start:
                raise ValueError("cohort: frozen policy after original candidate")
            _money(e[role + "_fees_usd"], "frozen_policy."+role+".fees")
        consumer = e["challenger_consumer_available_ns"]
        consumer_receipt = e["challenger_consumer_receipt_sha256"]
        if consumer is not None:
            _clock(consumer, "frozen_policy.challenger.consumer")
        if consumer_receipt is not None:
            _sha(consumer_receipt, "frozen_policy.challenger.consumer_receipt")
        modes.add(e["source_mode"])
        expected[key] = e
    if len(modes) != 1:
        # FINAL_VINTAGE and ACTUAL_AS_SEEN are fundamentally different evidence
        # strata. A pooled research mean must not hide a mixed source mode.
        raise ValueError("cohort: source modes must not be pooled")
    mode = next(iter(modes))
    matched = set()
    counts = {state: 0 for state in sorted(COHORT_STATES)}
    paired_exact = Fraction(0)
    for evaluation in supplied_evaluations:
        row = _dict(evaluation, {
            "schema", "candidate_id", "ticker", "session", "source_mode",
            "candidate_source_receipt_sha256", "calendar_receipt_sha256",
            *COHORT_CANDIDATE_FREEZE_FIELDS,
            *COHORT_POLICY_FREEZE_FIELDS,
            "baseline_policy_state", "challenger_policy_state",
            "horizon_trading_minutes", "original_decision_ns", "horizon_end_ns",
            "evaluation_cutoff_ns", "policy_count",
            "forward_outcome_available_to_original_decision",
            "source_authenticated", "simulated_execution_not_fill",
            "calendar_qualified_by_this_function",
            "actual_consumer_delivery_proven",
            "predictive_rank_trading_alert_authority", "prospective_promotion",
            "supplied_input_first_knowable_ns",
            "supplied_input_first_knowable_not_consumer_receipt",
            "primary_policy_authority", "state", "reason",
            "baseline_bps", "challenger_bps", "delta_bps",
        }, "evaluation")
        key = row["candidate_id"]
        if type(key) is not str or key not in expected or key in matched:
            raise ValueError("cohort: unknown, duplicate or unregistered result")
        identity = expected[key]
        if any(row[name] != identity[name]
               for name in COHORT_CANDIDATE_FREEZE_FIELDS):
            raise ValueError("cohort: frozen candidate economic basis or source-clock drift")
        # The registered policy version and claimant's original consumer receipt
        # never change after enrolment. Per-policy realized fee is checked only
        # when a hypothetical trade actually occurs: frozen abstention/missing
        # evidence legitimately incurs no research fill fee.
        for role in ("baseline", "challenger"):
            freeze_fields = (role+"_policy_receipt_sha256", role+"_policy_frozen_ns")
            if any(row[name] != identity[name] for name in freeze_fields):
                raise ValueError("cohort: frozen policy receipt/timing changed")
            state = row[role+"_policy_state"]
            if type(state) is not str or state not in STATES:
                raise ValueError("cohort: frozen policy reported invalid action state")
            fee = row[role+"_fees_usd"]
            if state == "SIMULATED_FULL":
                if fee != identity[role+"_fees_usd"]:
                    raise ValueError("cohort: frozen policy fee assumption changed")
            elif fee is not None:
                raise ValueError("cohort: frozen policy charges fee without fill")
        if any(
            row[name] != identity[name] for name in (
                "challenger_consumer_receipt_sha256",
                "challenger_consumer_available_ns",
            )
        ):
            raise ValueError("cohort: frozen policy challenger consumer receipt changed")
        if any((
            row["schema"] != SCHEMA,
            row["ticker"] != identity["ticker"],
            row["session"] != identity["session"],
            row["source_mode"] != mode,
            row["candidate_source_receipt_sha256"] != identity["source_receipt_sha256"],
            row["calendar_receipt_sha256"] != identity["calendar_receipt_sha256"],
            row["original_decision_ns"] != identity["original_decision_ns"],
            row["horizon_end_ns"] != identity["horizon_end_ns"],
            row["horizon_trading_minutes"] != 30,
            row["policy_count"] != 2,
            row["primary_policy_authority"] != "RESEARCH_DIAGNOSTIC_ONLY",
            row["forward_outcome_available_to_original_decision"] is not False,
            row["source_authenticated"] is not False,
            row["simulated_execution_not_fill"] is not True,
            row["calendar_qualified_by_this_function"] is not False,
            row["actual_consumer_delivery_proven"] is not False,
            row["predictive_rank_trading_alert_authority"] is not False,
            row["prospective_promotion"] is not False,
            row["supplied_input_first_knowable_not_consumer_receipt"] is not True,
        )):
            raise ValueError("cohort: source identity or authority changed")
        _clock(row["evaluation_cutoff_ns"], "evaluation.cutoff")
        state = row["state"]
        if type(state) is not str or state not in COHORT_STATES:
            raise ValueError("cohort: unrecognized evaluation outcome")
        if state == "PAIRED_RESEARCH_UTILITY":
            if row["reason"] is not None:
                raise ValueError("cohort: paired output cannot have refusal reason")
            if any(row[role+"_policy_state"] == "UNOBSERVABLE"
                   for role in ("baseline", "challenger")):
                raise ValueError("cohort: paired policy state cannot be unobservable")
            original = _frozen_paired_rational(row["baseline_bps"], "baseline")
            new = _frozen_paired_rational(row["challenger_bps"], "challenger")
            delta = _frozen_paired_rational(row["delta_bps"], "delta")
            if (row["baseline_policy_state"] == "FROZEN_ABSTAIN" and original != 0
                    or row["challenger_policy_state"] == "FROZEN_ABSTAIN" and new != 0):
                raise ValueError("cohort: nonzero abstention is false economic utility")
            if new - original != delta:
                raise ValueError("cohort: paired delta not conserved")
            first_knowable = _clock(
                row["supplied_input_first_knowable_ns"], "cohort.first_knowable"
            )
            if not (identity["horizon_end_ns"] <= first_knowable
                    < row["evaluation_cutoff_ns"]):
                raise ValueError("cohort: forward outcome chronologically impossible")
            paired_exact += delta
        elif (row["baseline_bps"] is not None
              or row["challenger_bps"] is not None
              or row["delta_bps"] is not None
              or row["supplied_input_first_knowable_ns"] is not None
              or row["reason"] is None):
            raise ValueError("cohort: absent outcome dressed as measured utility")
        if state == "NOT_MATURE" and row["reason"] != "HORIZON_OR_WATERMARK_NOT_KNOWABLE":
            raise ValueError("cohort: false immature reason")
        if state == "CENSORED" and row["reason"] != "HALTED_OR_UNKNOWN_MARKET":
            raise ValueError("cohort: false market censorship")
        if state == "UNOBSERVABLE":
            r = _dict(row["reason"], {"baseline", "challenger"}, "cohort.unobservable")
            allowed = REASONS | {
                "OVERLAY_CONSUMER_AVAILABILITY_NOT_PROVEN",
                "OVERLAY_ARRIVED_AFTER_ORIGINAL_DECISION",
                "ENTRY_QUOTE_NOT_KNOWABLE_OR_STALE",
                "EXIT_QUOTE_NOT_KNOWABLE_OR_STALE",
                "INSUFFICIENT_DISPLAYED_TOP_SIZE",
            }
            if (r["baseline"] is None and r["challenger"] is None
                    or any(reason is not None
                           and (type(reason) is not str or reason not in allowed)
                           for reason in r.values())):
                raise ValueError("cohort: invalid typed unobservable reasons")
        matched.add(key)
        counts[state] += 1

    missing = sorted(set(expected) - matched)
    usable = counts["PAIRED_RESEARCH_UTILITY"]
    return {
        "schema": COHORT_SCHEMA,
        "state": ("ALL_FROZEN_CANDIDATES_ACCOUNTED_SOFTWARE_ONLY" if not missing
                  else "MISSING_EXPECTED_CANDIDATE_REPORTS"),
        "frozen_manifest_sha256": frozen_manifest_sha256,
        "source_mode": mode,
        "n_expected": len(expected),
        "n_supplied": len(matched),
        "n_missing": len(missing),
        "missing_candidate_ids_private_only": missing,
        "by_state": counts,
        "n_complete_software_pairs": usable,
        "observed_pair_subset_mean_bps": (
            _exact_bp(paired_exact / usable) if usable else None
        ),
        "primary_population_mean_bps": None,
        "denominator_and_missingness_proven_by_this_function": False,
        "source_authenticated": False,
        "actual_consumer_delivery_proven": False,
        "empirical_source_qualified": False,
        "inference_or_power_established": False,
        "trial_ledger_written": False,
        "prospective_promotion": False,
        "predictive_rank_trading_alert_authority": False,
    }
