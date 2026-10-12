"""Identity-bound runtime source adapter for Prophet B4 Availability.

This module does not decide whether a candidate is attractive, rank anything, or
recompute incumbent owner arithmetic.  It binds the already-canonical B3 episode
identity to the incumbent live quote/basis and entry-geometry facts that B4 needs.
Facts that do not yet have an explicitly supplied owner verdict remain UNKNOWN, so
``engine.prophet_entry_availability`` fails closed instead of minting ENTRY_OPEN.

Important identity law: symbols are routing aliases, never identity.  The adapter
resolves the current ``store`` symbol from canonical ``security_id`` for the market
session through Data OS and verifies the reverse mapping before reading ticker-keyed
runtime artifacts.  There is intentionally no ticker-equality fallback.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from lib.nyse_calendar import expected_last_session, session_n_forward
from hashlib import sha256
import json
from math import isfinite
from typing import Mapping, Sequence

from engine.prophet_entry_availability import evaluate_entry_availability
from engine.prophet_entry_policy import evaluate_session_eligibility
from engine.prophet_live.interval import ADJUSTED, UNADJUSTED
from engine.signal_gate import is_buyable as signal_gate_is_buyable

LIVE_SYMBOL_VENDOR = "store"

_GATE_DEFAULTS = {
    "owner_confluence": "UNKNOWN",
    "risk_ceiling": "UNKNOWN",
    "liquidity_fillability": "UNKNOWN",
    "gap_velocity": "UNKNOWN",
    "source_health": "PASS",
    "corporate_action_basis": "RESOLVED",
    "session_eligibility": "UNKNOWN",
    "event_status": "UNKNOWN",
    "structural_invalidation": "UNKNOWN",
}
_METRIC_KEYS = frozenset({"first_trigger_price", "anchor_price", "atr"})


class RuntimeOwnerFactError(ValueError):
    """Raised when canonical owner facts cannot be bound without guessing."""


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise RuntimeOwnerFactError(f"runtime owner fact is not canonical JSON: {exc}") from exc


def _sha_receipt(value: object) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or any(ord(ch) < 32 for ch in value):
        raise RuntimeOwnerFactError(f"{field} must be non-empty text")
    return value


def _positive(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeOwnerFactError(f"{field} must be numeric")
    number = float(value)
    if not isfinite(number) or number <= 0:
        raise RuntimeOwnerFactError(f"{field} must be finite and > 0")
    return number


def _nonnegative(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeOwnerFactError(f"{field} must be numeric")
    number = float(value)
    if not isfinite(number) or number < 0:
        raise RuntimeOwnerFactError(f"{field} must be finite and >= 0")
    return number


def _utc(value: object, field: str) -> datetime:
    text = _text(value, field)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeOwnerFactError(f"{field} must be an ISO timestamp") from exc
    if parsed.tzinfo is None:
        raise RuntimeOwnerFactError(f"{field} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _candidate_row(candidate_projection: Mapping[str, object], episode_id: str) -> Mapping[str, object]:
    if not isinstance(candidate_projection, Mapping):
        raise RuntimeOwnerFactError("candidate_projection must be an object")
    rows = candidate_projection.get("rows")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise RuntimeOwnerFactError("candidate_projection.rows must be a list")
    matches = [row for row in rows if isinstance(row, Mapping) and row.get("episode_id") == episode_id]
    if len(matches) != 1:
        raise RuntimeOwnerFactError("episode_id must resolve to exactly one canonical B3 row")
    return matches[0]


def _resolve_store_symbol(alias_table: object, security_id: str, market_session: str) -> str:
    try:
        on = date.fromisoformat(market_session)
    except (TypeError, ValueError) as exc:
        raise RuntimeOwnerFactError("market_session must be YYYY-MM-DD") from exc
    vendor_symbol_for = getattr(alias_table, "vendor_symbol_for", None)
    resolve = getattr(alias_table, "resolve", None)
    if not callable(vendor_symbol_for) or not callable(resolve):
        raise RuntimeOwnerFactError("alias_table must implement Data OS vendor_symbol_for/resolve")
    symbol = vendor_symbol_for(LIVE_SYMBOL_VENDOR, security_id, on)
    if not isinstance(symbol, str) or not symbol:
        raise RuntimeOwnerFactError("canonical security_id has no store alias for market_session")
    if resolve(LIVE_SYMBOL_VENDOR, symbol, on) != security_id:
        raise RuntimeOwnerFactError("store alias does not round-trip to canonical security_id")
    return symbol


def _entry_signal_for_symbol(entry_rows_by_symbol: Mapping[str, object], symbol: str) -> Mapping[str, object]:
    row = entry_rows_by_symbol.get(symbol)
    if not isinstance(row, Mapping):
        raise RuntimeOwnerFactError("entry geometry owner has no row for canonical store symbol")
    signal = row.get("entry_signal") if "entry_signal" in row else row
    if not isinstance(signal, Mapping):
        raise RuntimeOwnerFactError("entry geometry owner row has no entry_signal object")
    return signal


def _iso_session(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _confluence_result(
    verdict: str,
    reason: str | None = None,
    *,
    source_session: str | None = None,
    verdict_asof: str | None = None,
    pair_id: str | None = None,
    emitted_at: str | None = None,
) -> tuple[str, str | None]:
    if verdict != "PASS":
        assert reason is not None
        return "UNKNOWN", f"reason:{reason}"
    assert None not in {source_session, verdict_asof, pair_id, emitted_at}
    return (
        "PASS",
        f"signal-gate-pair:{pair_id}@{source_session}"
        f" verdict_asof={verdict_asof} emitted_at={emitted_at}",
    )


def _bind_owner_confluence(
    signal_gate_artifact: Mapping[str, object] | None,
    *,
    symbol: str,
    market_session: str,
    decision_clock: datetime,
) -> tuple[str, str | None]:
    """Bind a prior-session incumbent confluence verdict under validity/v1.

    Artifact content is evidence, not an input-validation failure: every missing,
    stale, expired, relabelled, or malformed artifact condition degrades to a
    typed UNKNOWN so B4 itself can fail closed.  Only non-artifact caller inputs
    retain injection refusal.
    """
    if signal_gate_artifact is None:
        return "UNKNOWN", None
    if not isinstance(signal_gate_artifact, Mapping):
        return _confluence_result("UNKNOWN", "confluence_malformed")

    as_of = signal_gate_artifact.get("as_of")
    validity = signal_gate_artifact.get("validity")
    if not isinstance(validity, Mapping):
        return _confluence_result(
            "UNKNOWN",
            "confluence_no_validity_block" if validity is None else "confluence_legacy_artifact",
        )
    if validity.get("schema") != "signal_gate.validity/v1":
        return _confluence_result("UNKNOWN", "confluence_legacy_artifact")

    source_session_value = validity.get("source_session")
    source_session = _iso_session(source_session_value)
    if source_session is None or source_session_value != as_of:
        if source_session_value is None:
            return _confluence_result("UNKNOWN", "confluence_no_source_session")
        return _confluence_result("UNKNOWN", "confluence_session_mismatch")

    emit = signal_gate_artifact.get("emit")
    if not isinstance(emit, Mapping):
        return _confluence_result("UNKNOWN", "confluence_malformed")
    pair_id = emit.get("pair_id")
    writer = emit.get("writer")
    at_utc = emit.get("at_utc")
    if not isinstance(pair_id, str) or not pair_id or any(ord(char) < 32 for char in pair_id):
        return _confluence_result("UNKNOWN", "confluence_malformed")
    if writer != "build_stock_library":
        return _confluence_result("UNKNOWN", "confluence_writer_mismatch")
    try:
        emitted_clock = _utc(at_utc, "signal_gate.emit.at_utc")
    except RuntimeOwnerFactError:
        return _confluence_result("UNKNOWN", "confluence_malformed")

    if validity.get("emitted_at") != at_utc:
        return _confluence_result("UNKNOWN", "confluence_malformed")
    if emitted_clock > decision_clock:
        return _confluence_result("UNKNOWN", "confluence_late_emission")

    valid_sessions = validity.get("valid_for_decision_sessions")
    if not isinstance(valid_sessions, list) or market_session not in valid_sessions:
        return _confluence_result("UNKNOWN", "confluence_expired")
    next_session = session_n_forward(source_session, 1)
    if next_session is None or next_session.isoformat() != market_session:
        return _confluence_result("UNKNOWN", "confluence_session_mismatch")

    expected_session = expected_last_session(emitted_clock)
    if expected_session != source_session:
        return _confluence_result(
            "UNKNOWN",
            "confluence_stale_source" if expected_session > source_session
            else "confluence_unsettled_source",
        )
    producer_lag = validity.get("lag_sessions")
    if isinstance(producer_lag, bool) or not isinstance(producer_lag, int) or producer_lag != 0:
        return _confluence_result("UNKNOWN", "confluence_malformed")
    if validity.get("settled") is not True:
        return _confluence_result("UNKNOWN", "confluence_malformed")

    if validity.get("lineage_token") != pair_id:
        return _confluence_result("UNKNOWN", "confluence_lineage_mismatch")

    verdicts = signal_gate_artifact.get("verdicts")
    verdict = verdicts.get(symbol) if isinstance(verdicts, Mapping) else None
    if not isinstance(verdict, Mapping):
        return _confluence_result("UNKNOWN", "confluence_row_missing")
    if verdict.get("eligible") is not True or not signal_gate_is_buyable(dict(verdict)):
        return _confluence_result("UNKNOWN", "confluence_row_missing")
    verdict_asof = verdict.get("asof")
    if verdict_asof != source_session_value:
        return _confluence_result("UNKNOWN", "confluence_tape_stale")

    return _confluence_result(
        "PASS",
        source_session=source_session_value,
        verdict_asof=verdict_asof,
        pair_id=pair_id,
        emitted_at=at_utc,
    )


def _bind_event_status_from_candidate(
    row: Mapping[str, object],
) -> tuple[str, str | None]:
    """Bind ACTIVE only from a current B1 relation already proven by B3.

    B3's TURN WATCH emergence source is built from the atomic B1 event ledger and
    excludes any relation withdrawn by ``RETRACTED.correction_of``.  Therefore a
    TRIGGERED row whose source is an exact content-addressed B1 relation can prove
    that *that relation* is active at the B3 projection cut.  Missing/unestimable
    emergence remains UNKNOWN; this adapter never infers ACTIVE from episode
    lifecycle alone and never manufactures RETRACTED from absence.
    """
    emergence = row.get("emergence_state")
    if not isinstance(emergence, Mapping):
        raise RuntimeOwnerFactError("candidate emergence_state must be an object")
    if emergence.get("state") != "TRIGGERED":
        return "UNKNOWN", None
    if emergence.get("source_system") != "turn_watch":
        return "UNKNOWN", None
    if emergence.get("source_token") not in {"B1_OPENED", "B1_OBSERVED"}:
        return "UNKNOWN", None
    source_ref = emergence.get("source_ref")
    if (
        not isinstance(source_ref, str)
        or not source_ref.startswith("pee:")
        or len(source_ref) != 68
        or any(ch not in "0123456789abcdef" for ch in source_ref[4:])
    ):
        raise RuntimeOwnerFactError(
            "triggered TURN WATCH emergence has no exact B1 relation receipt"
        )
    return "ACTIVE", source_ref


def _live_state_for_symbol(live_state_artifact: Mapping[str, object], symbol: str, market_session: str) -> Mapping[str, object]:
    if not isinstance(live_state_artifact, Mapping):
        raise RuntimeOwnerFactError("live_state_artifact must be an object")
    meta = live_state_artifact.get("meta")
    if not isinstance(meta, Mapping) or meta.get("session_et") != market_session:
        raise RuntimeOwnerFactError("live-state artifact session does not match B4 market_session")
    states = live_state_artifact.get("states")
    state = states.get(symbol) if isinstance(states, Mapping) else None
    if not isinstance(state, Mapping):
        raise RuntimeOwnerFactError("live-state owner has no row for canonical store symbol")
    if state.get("state") == "dark":
        raise RuntimeOwnerFactError("live-state owner marks canonical store symbol dark")
    if state.get("basis_status") != "RESOLVED":
        raise RuntimeOwnerFactError("live-state owner has no positive per-name basis resolution")
    receipt = state.get("basis_receipt")
    if not isinstance(receipt, str) or not receipt.startswith("sha256:"):
        raise RuntimeOwnerFactError("live-state owner has no positive per-name basis receipt")
    return state


def compose_runtime_owner_facts(
    candidate_projection: Mapping[str, object],
    *,
    episode_id: str,
    decision_at: str,
    market_session: str,
    alias_table: object,
    quotes_by_symbol: Mapping[str, object],
    live_state_artifact: Mapping[str, object],
    entry_rows_by_symbol: Mapping[str, object],
    metric_inputs: Mapping[str, object],
    strategy_definition: Mapping[str, object] | None = None,
    signal_gate_artifact: Mapping[str, object] | None = None,
    owner_gate_facts: Mapping[str, object] | None = None,
    owner_source_receipts: Sequence[str] = (),
) -> dict[str, object]:
    """Bind runtime owner facts for one canonical B3 episode without guessing.

    The function intentionally leaves all not-yet-wired gate owners UNKNOWN.
    Generic external PASS/ACTIVE/CLEAR injection is refused: every future gate must
    be wired from its incumbent owner together with its native clock and receipt.
    Source health and corporate-action basis are bound here from the quote/live-state
    owners and cannot be overridden by the caller.
    """
    episode_id = _text(episode_id, "episode_id")
    row = _candidate_row(candidate_projection, episode_id)
    security_id = _text(row.get("security_id"), "candidate.security_id")
    symbol = _resolve_store_symbol(alias_table, security_id, market_session)

    quote_row = quotes_by_symbol.get(symbol) if isinstance(quotes_by_symbol, Mapping) else None
    if not isinstance(quote_row, Mapping):
        raise RuntimeOwnerFactError("live quote owner has no row for canonical store symbol")
    if quote_row.get("quote_ts_synthetic") is not False:
        raise RuntimeOwnerFactError("live quote has no real source-market timestamp")
    quote_price = _positive(quote_row.get("price"), "quote.price")
    quote_clock = _utc(quote_row.get("quote_ts"), "quote.quote_ts")
    quote_asof = quote_clock.isoformat(timespec="seconds").replace("+00:00", "Z")
    decision_clock = _utc(decision_at, "decision_at")
    if quote_clock > decision_clock:
        raise RuntimeOwnerFactError("live quote timestamp cannot be after B4 decision clock")

    live_state = _live_state_for_symbol(live_state_artifact, symbol, market_session)
    live_meta = live_state_artifact.get("meta")
    assert isinstance(live_meta, Mapping)  # guaranteed by _live_state_for_symbol
    live_pass_clock = _utc(live_meta.get("pass_ts"), "live_state.meta.pass_ts")
    if live_pass_clock != decision_clock:
        raise RuntimeOwnerFactError("live-state pass_ts must equal B4 decision clock")
    live_price = _positive(live_state.get("price"), "live_state.price")
    if round(live_price, 4) != round(quote_price, 4):
        raise RuntimeOwnerFactError("live quote and basis-audited live state disagree on price")
    owner_quote_age_min = _nonnegative(live_state.get("quote_age_min"), "live_state.quote_age_min")
    bound_quote_age_min = round((live_pass_clock - quote_clock).total_seconds() / 60.0, 1)
    if abs(owner_quote_age_min - bound_quote_age_min) > 1e-9:
        raise RuntimeOwnerFactError(
            "live quote timestamp does not match live-state owner quote_age_min at decision clock"
        )

    signal = _entry_signal_for_symbol(entry_rows_by_symbol, symbol)
    zone = signal.get("buy_zone")
    if not isinstance(zone, Mapping):
        raise RuntimeOwnerFactError("entry geometry owner has no buy_zone")
    owner_status = _text(signal.get("status"), "entry_signal.status")
    zone_low = _positive(zone.get("low"), "entry_signal.buy_zone.low")
    zone_high = _positive(zone.get("high"), "entry_signal.buy_zone.high")
    chase_above = _positive(signal.get("chase_above"), "entry_signal.chase_above")
    invalidation = _positive(signal.get("stop"), "entry_signal.stop")

    if not isinstance(metric_inputs, Mapping) or set(metric_inputs) != _METRIC_KEYS:
        raise RuntimeOwnerFactError("metric_inputs fields are not closed")
    metrics = {key: _positive(metric_inputs.get(key), f"metric_inputs.{key}") for key in sorted(_METRIC_KEYS)}

    gates = dict(_GATE_DEFAULTS)
    # source_health is hardcoded PASS upstream and does not cover confluence tape staleness; (7b) is the only guard.
    owner_confluence, confluence_receipt = _bind_owner_confluence(
        signal_gate_artifact,
        symbol=symbol,
        market_session=market_session,
        decision_clock=decision_clock,
    )
    gates["owner_confluence"] = owner_confluence
    event_status, event_status_receipt = _bind_event_status_from_candidate(row)
    gates["event_status"] = event_status

    session_receipt: str | None = None
    if strategy_definition is not None:
        session_fact = evaluate_session_eligibility(
            strategy_definition=strategy_definition,
            decision_at=decision_clock.isoformat(timespec="seconds").replace("+00:00", "Z"),
            market_session=market_session,
        )
        session_verdict = session_fact.get("verdict")
        if session_verdict not in {"PASS", "FAIL"}:
            raise RuntimeOwnerFactError("session policy owner returned an invalid verdict")
        gates["session_eligibility"] = session_verdict
        session_receipt = _text(
            session_fact.get("fact_receipt"),
            "session_policy.fact_receipt",
        )

    if owner_gate_facts not in (None, {}):
        raise RuntimeOwnerFactError(
            "owner_gate_facts cannot inject gate verdicts without native owner evidence"
        )
    if owner_source_receipts:
        raise RuntimeOwnerFactError(
            "owner_source_receipts cannot be attached without a bound native owner fact"
        )

    quote_receipt = _sha_receipt({
        "schema": "prophet.b4.quote_binding/v1",
        "security_id": security_id,
        "store_symbol": symbol,
        "market_session": market_session,
        "decision_at": decision_clock.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "quote": dict(quote_row),
        "live_state_pass_ts": live_pass_clock.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "live_state_quote_age_min": owner_quote_age_min,
    })
    geometry_receipt = _sha_receipt({
        "schema": "prophet.b4.geometry_binding/v1",
        "security_id": security_id,
        "store_symbol": symbol,
        "market_session": market_session,
        "entry_signal": dict(signal),
    })

    receipts: list[str] = [
        _text(candidate_projection.get("projection_id"), "candidate_projection.projection_id"),
        _text(live_state.get("basis_receipt"), "live_state.basis_receipt"),
    ]
    if confluence_receipt is not None:
        receipts.append(confluence_receipt)
    if event_status_receipt is not None:
        receipts.append(event_status_receipt)
    if session_receipt is not None:
        receipts.append(session_receipt)

    return {
        "decision_at": decision_clock.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "market_session": market_session,
        "quote": {
            "price": quote_price,
            "asof": quote_asof,
            "freshness": "FRESH",
            "basis_version": UNADJUSTED,
            "source_receipt": quote_receipt,
        },
        "geometry": {
            "owner_status": owner_status,
            "zone_low": zone_low,
            "zone_high": zone_high,
            "chase_above": chase_above,
            "invalidation_price": invalidation,
            "basis_version": ADJUSTED,
            "source_receipt": geometry_receipt,
        },
        "deterministic_gates": gates,
        "metric_inputs": metrics,
        "source_receipts": sorted(set(receipts)),
    }


def evaluate_runtime_entry_availability(
    candidate_projection: Mapping[str, object],
    *,
    episode_id: str,
    strategy_definition: Mapping[str, object],
    **source_kwargs: object,
) -> dict[str, object]:
    """Compose bound owner facts, then delegate the only Availability decision to B4."""
    facts = compose_runtime_owner_facts(
        candidate_projection,
        episode_id=episode_id,
        strategy_definition=strategy_definition,
        **source_kwargs,
    )
    return evaluate_entry_availability(
        candidate_projection,
        episode_id=episode_id,
        strategy_definition=strategy_definition,
        facts=facts,
    )
