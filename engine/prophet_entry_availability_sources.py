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

It also hosts :func:`read_native_b4_owner_inputs` — the bounded native reader that
resolves ONE ``us_prophet_rank.candidates/v1`` source key inside a validated candidate
episode generation and reads the two fixed private owner files (the root-readable
quotes snapshot and the served live-state artifact) under byte attestation.  The
reader NEVER evaluates B4, mints availability, invents metrics, or writes anything:
its result always carries ``availability=None``, and ``quote_input`` appears only when
every source, identity, basis, clock and session check qualifies.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from lib.nyse_calendar import expected_last_session, is_session, session_n_forward
from hashlib import sha256
import json
from math import isfinite
from typing import Mapping, Sequence

from engine.prophet_entry_availability import evaluate_entry_availability
from engine.prophet_entry_policy import evaluate_session_eligibility
from engine.prophet_live import live_states as _live_states
from engine.prophet_live.interval import ADJUSTED, LIVE_QUOTE_ADJUSTMENT, UNADJUSTED
from engine.signal_gate import is_buyable as signal_gate_is_buyable
from engine.us_candidate_episode import (
    ACTIVE_STATE,
    TERMINAL_STATES,
    CandidateEpisodeStoreSnapshot,
    EpisodeContractError,
    attest_candidate_episode_store_bytes,
    canonical_json as _episode_canonical_json,
    load_candidate_episode_store_snapshot,
)

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

# ── Native basis-relation material (engine.prophet_live.live_states) ─────────
#: The measured material a RESOLVED live-state row publishes beside its receipt.
#: ``compose_runtime_owner_facts`` and the native reader both verify a row against
#: it: an opaque ``basis_receipt`` alone commits to nothing a consumer can check.
_BASIS_RELATION_SCHEMA = "prophet_live.basis_relation/v1"
_BASIS_MATERIAL_KEYS = frozenset(_live_states.BASIS_RELATION_FIELDS)

#: The vendor RUNG axis a private quote row discloses under ``basis`` — deliberately
#: a DIFFERENT axis from the price-adjustment family the live owner measures (see
#: ``engine.prophet_live.interval``: rung vs adjustment family are distinct axes).
#: Only genuine vendor rungs are accepted; anything else (a fabricated label, an
#: adjusted-family string, a placeholder) refuses the quote row.
_QUOTE_RUNGS = frozenset({"trade", "minute", "day", "prev", "regular"})
#: The estate's real quote vendors. A public/worker or self-labelled row ("snapshot",
#: "test", "quotes", …) is not a native quote source.
_REAL_QUOTE_SOURCES = frozenset({"polygon", "yahoo"})

#: The live owner's OWN disclosed staleness ceiling
#: (``engine.prophet_live.live_states`` stamps ``meta.quote_freshness_policy`` on
#: every artifact).  The reader re-ages the quote at its OWN read completion
#: against THIS policy — never against an in-code default, and never against
#: today's config substituted for a historical artifact.
_LIVE_FRESHNESS_POLICY_KEY = "quote_freshness_policy"
_LIVE_POLICY_RESOLUTIONS = frozenset({"explicit", "derived", "fallback"})

# ── Native B4 owner reader boundaries (fixed, trusted operator roots) ────────
NATIVE_READ_SCHEMA = "prophet.b4.native_owner_read/v1"
_QUOTE_INPUT_SCHEMA = "prophet.daily_brief_quote_input/v1"
_EPISODE_STORE_PARTS = ("data", "us_prophet_rank", "episodes")
_QUOTES_FULL_PARTS = ("state", "quotes_full.json")
_LIVE_ARTIFACT_PARTS = ("public", "live", "prophet_live.json")
#: The live artifact's ownership identity, stamped by its producing script.
_LIVE_OWNER_PRODUCER = "scripts/prophet_live_evaluator.py"
_LIVE_STATES_SCHEMA = "prophet_live.states/v1"
_CANDIDATE_SOURCE_SYSTEM = "candidate"
_CANDIDATE_SOURCE_SCHEMA = "us_prophet_rank.candidates/v1"


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


def _basis_family_declared(state: Mapping[str, object], live_meta: Mapping[str, object]) -> str:
    """The levels basis this ROW actually declares, per the live lane's own law.

    A row that carries ``levels_adjustment`` is an explicit exception to the
    artifact-level basis; a row without it sits on ``meta.price_adjustment.levels``.
    Key presence is the declaration — nothing is derived (module law in
    ``engine.prophet_live.live_states``).
    """
    adjustment_block = live_meta.get("price_adjustment")
    if not isinstance(adjustment_block, Mapping):
        raise RuntimeOwnerFactError("live-state artifact states no price_adjustment block")
    declared = state.get("levels_adjustment", adjustment_block.get("levels"))
    if not isinstance(declared, str) or not declared:
        raise RuntimeOwnerFactError("live-state artifact declares no levels basis")
    return declared


def _measured_basis_material(
    state: Mapping[str, object], symbol: str, live_meta: Mapping[str, object]
) -> dict[str, object]:
    """Validate the row's measured basis relation and return its resolved families.

    The material must re-hash to the row's own receipt, bind THIS symbol and the
    artifact's own pack cut, agree with the row/meta basis declaration, and record a
    genuinely positive measurement (tolerance > 0, measured gap inside it, disclosed
    input pair reproducing the recorded gap).  Missing or unverifiable material is a
    hard refusal — an old receipt without material is UNAVAILABLE, never a historical
    fallback.
    """
    material = state.get("basis_relation")
    if not isinstance(material, Mapping) or set(material) != _BASIS_MATERIAL_KEYS:
        raise RuntimeOwnerFactError(
            "live-state owner has no measured basis relation material beside its receipt"
        )
    if material.get("schema") != _BASIS_RELATION_SCHEMA:
        raise RuntimeOwnerFactError("basis relation material schema is not the lane's own")
    if material.get("state") != "RESOLVED":
        raise RuntimeOwnerFactError("basis relation material does not record a RESOLVED state")
    if material.get("subject") != symbol:
        raise RuntimeOwnerFactError("basis relation material binds a different subject")
    if material.get("pack_as_of") != str(live_meta.get("pack_as_of")):
        raise RuntimeOwnerFactError("basis relation material does not bind the live pack cut")
    if _live_states.basis_relation_receipt(dict(material)) != state.get("basis_receipt"):
        raise RuntimeOwnerFactError("basis relation material does not reproduce its receipt")
    adjustment_block = live_meta.get("price_adjustment")
    if not isinstance(adjustment_block, Mapping):
        raise RuntimeOwnerFactError("live-state artifact states no price_adjustment block")
    if material.get("quote_adjustment") != adjustment_block.get("quote"):
        raise RuntimeOwnerFactError(
            "basis relation material quote family contradicts the artifact's stated quote basis"
        )
    if material.get("levels_adjustment") != _basis_family_declared(state, live_meta):
        raise RuntimeOwnerFactError(
            "basis relation material levels family contradicts the row/meta basis declaration"
        )
    gap = material.get("gap_pct")
    tol = material.get("tol_pct")
    for value, field in ((gap, "basis gap_pct"), (tol, "basis tol_pct")):
        if isinstance(value, bool) or not isinstance(value, (int, float)) \
                or not isfinite(float(value)):
            raise RuntimeOwnerFactError(f"basis relation material {field} is not a finite number")
    if float(tol) <= 0.0 or abs(float(gap)) > float(tol):
        raise RuntimeOwnerFactError(
            "basis relation material is not a positive measurement inside the tolerance"
        )
    as_of_close = state.get("basis_as_of_close")
    prev_close = state.get("basis_prev_close")
    measured_close = _positive(as_of_close, "live_state.basis_as_of_close")
    measured_prev = _positive(prev_close, "live_state.basis_prev_close")
    recomputed = round(100.0 * (measured_close / measured_prev - 1.0), 6)
    if recomputed != float(gap):
        raise RuntimeOwnerFactError(
            "basis relation disclosure does not reproduce the measured basis gap"
        )
    return {
        "material": dict(material),
        "levels_family": str(material["levels_adjustment"]),
        "quote_family": str(material["quote_adjustment"]),
        "as_of_close": measured_close,
        "prev_close": measured_prev,
    }


def _private_quote_rung(quote_row: Mapping[str, object]) -> str:
    """The vendor rung a private quote row declares, on either owner spelling."""
    rung = quote_row.get("basis", quote_row.get("price_basis"))
    if not isinstance(rung, str) or rung not in _QUOTE_RUNGS:
        raise RuntimeOwnerFactError(
            "live quote row does not declare a real vendor rung for its price"
        )
    return rung


def _private_quote_prev_close(quote_row: Mapping[str, object], measured_prev: float) -> float:
    """The row's previous close, proven against the live owner's measured disclosure."""
    prev = quote_row.get("prevClose", quote_row.get("prev_close"))
    if isinstance(prev, bool) or not isinstance(prev, (int, float)) or not isfinite(float(prev)):
        raise RuntimeOwnerFactError("live quote row does not disclose a real previous close")
    if round(float(prev), 4) != round(measured_prev, 4):
        raise RuntimeOwnerFactError(
            "live quote previous close does not match the live-state owner's measured "
            "previous close"
        )
    return float(prev)


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
    # The measured basis material must sit beside the receipt and check out against
    # the row/meta declaration, the pack cut and THIS symbol before either family is
    # propagated. A legacy row with only an opaque receipt is UNAVAILABLE here — an
    # unverifiable digest is not a positive basis fact, and there is no historical
    # fallback to an assumed basis.
    resolved_basis = _measured_basis_material(live_state, symbol, live_meta)
    _private_quote_rung(quote_row)
    _private_quote_prev_close(quote_row, resolved_basis["prev_close"])
    # The measured relation covers the armed pack and this quote only. The entry
    # signal is independently produced and has no native geometry/OHLC basis
    # evidence here. Neither equal numbers nor its declared family extends that
    # receipt to the signal. Keep its basis and the combined relation unknown.
    quote_basis_family = resolved_basis["quote_family"]
    geometry_basis_family = "UNKNOWN"

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
    gates["corporate_action_basis"] = "UNKNOWN"
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
            "basis_version": quote_basis_family,
            "source_receipt": quote_receipt,
        },
        "geometry": {
            "owner_status": owner_status,
            "zone_low": zone_low,
            "zone_high": zone_high,
            "chase_above": chase_above,
            "invalidation_price": invalidation,
            "basis_version": geometry_basis_family,
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


# ─────────────────────────────────────────────────────────────────────────────
# Native B4 owner reader — one candidate source key, two fixed owner files.
# ─────────────────────────────────────────────────────────────────────────────

def _trusted_root(value: object, field: str) -> Path:
    """Coerce and vet a TRUSTED operator root (never a public request/body path)."""
    if isinstance(value, str):
        value = Path(value)
    if not isinstance(value, Path) or not value.is_absolute() or not value.is_dir():
        raise RuntimeOwnerFactError(f"{field} must be an existing absolute operator directory")
    return value


def _contained(root: Path, child: Path) -> bool:
    """True when ``child`` (symlinks resolved) stays inside ``root``."""
    try:
        return child.resolve().is_relative_to(root.resolve())
    except OSError:  # pragma: no cover - unreadable path component
        return False


def _parse_candidate_source_key(value: object) -> tuple[str, str, str] | None:
    """``candidate:{YYYY-MM-DD}:{ticker}:{board_definition}`` — strictly validated.

    The day must be a real, canonical calendar day; the ticker and board definition
    must be non-empty and control-free.  ``board_definition`` may itself contain
    ``:`` (split limited to three).  ``None`` when the key is not this shape.
    """
    if not isinstance(value, str) or not value or any(ord(ch) < 32 for ch in value):
        return None
    parts = value.split(":", 3)
    if len(parts) != 4 or parts[0] != "candidate":
        return None
    day_text, ticker, board = parts[1], parts[2], parts[3]
    if len(day_text) != 10 or not all(ch.isdigit() for ch in (day_text[:4] + day_text[5:7] + day_text[8:])) \
            or day_text[4] != "-" or day_text[7] != "-":
        return None
    try:
        parsed_day = date.fromisoformat(day_text)
    except ValueError:
        return None
    if parsed_day.isoformat() != day_text:
        return None
    if not ticker or not board or any(ord(ch) < 32 for ch in ticker + board):
        return None
    return day_text, ticker, board


def _sha256_receipt(payload: bytes) -> str:
    return "sha256:" + sha256(payload).hexdigest()


def _read_owner_bytes(path: Path) -> bytes:
    """One read of one fixed owner file.  Module-level so a test can interpose."""
    return path.read_bytes()


def _now_utc() -> datetime:
    """The reader's OWN clock — read completion, and the future-clock anchor.

    One module-level seam so a test can pin read completion truthfully.  Every own
    clock relation (future-owner rejection, own-read re-age, own-read session)
    reads THIS clock, so a pinned test clock tightens them together and weakens
    none.
    """
    return datetime.now(timezone.utc)


#: The closed field set of one published quote_input receipt.  ``source_receipt``
#: hashes EXACTLY these keys and nothing else: both owner files as actually read,
#: the live policy the read was re-aged against, the native binding and both read
#: clocks.  A receipt over the quote file alone would not commit to the policy the
#: CURRENT verdict was re-aged under.
_QUOTE_INPUT_RECEIPT_FIELDS: tuple[str, ...] = (
    "schema", "owner_ref", "live_owner_ref", "quotes_source_receipt",
    "live_source_receipt", "live_policy", "security_id", "episode_id",
    "candidate_generation_id", "market_session", "observed_at", "read_completed_at",
)


def quote_input_receipt(quote_input: Mapping[str, object]) -> str:
    """Re-hash a published quote_input's binding fields to its composite receipt.

    ONE definition of the digest (the same closed field set the reader hashed), so
    a downstream validator re-hashes exactly what was committed without trusting an
    opaque digest.
    """
    missing = [field for field in _QUOTE_INPUT_RECEIPT_FIELDS
               if field not in quote_input]
    if missing:
        raise RuntimeOwnerFactError(f"quote_input receipt material missing {missing}")
    material = {field: quote_input[field] for field in _QUOTE_INPUT_RECEIPT_FIELDS}
    blob = json.dumps(material, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")
    return "sha256:" + sha256(blob).hexdigest()


def _canonical_snapshot_part(value: object) -> str:
    try:
        return _episode_canonical_json(value)
    except EpisodeContractError as exc:
        raise RuntimeOwnerFactError(f"native snapshot part is not canonical JSON: {exc}") from exc


def read_native_b4_owner_inputs(
    repo_root: object,
    snapshot: object,
    *,
    candidate_source_event_id: object,
    candidate_source_receipt: object,
    native_live_root: object,
    alias_table: object,
) -> dict[str, object]:
    """Read the native B4 quote/basis owner facts for ONE canonical candidate.

    WHAT IT IS.  A read-only boundary between the canonical candidate episode store
    and the two fixed private owner files the live lanes publish.  It resolves the
    caller's exact ``us_prophet_rank.candidates/v1`` source key (id + sha256 digest,
    never a ticker) inside a fully revalidated HEAD-backed generation, re-derives the
    binding (security_id, episode_id, candidate_generation_id, market_session) from
    the native rows themselves, reads
    ``<native_live_root>/state/quotes_full.json`` and
    ``<native_live_root>/public/live/prophet_live.json`` exactly once each under byte
    attestation, and returns an honestly typed result.

    WHAT IT NEVER DOES.  No network, scoring, writes, cache or public quote fallback.
    It does not evaluate B4, does not mint a ``candidate_state_projection_id``, and
    invents no first-trigger/ATR/risk/liquidity number — the opened anchor is carried
    as evidence and nothing else.  ``availability`` is ALWAYS ``None`` in this initial
    unit: real availability needs the future same-read B3 projection and native
    geometry/metric owner facts, which do not exist yet.

    ``quote_input`` (schema ``prophet.daily_brief_quote_input/v1``) is published ONLY
    when every source, identity, basis, clock, session and OWN-READ freshness check
    qualifies.  Its ``state`` uses the existing consumer's vocabulary
    (``engine.prophet_daily_brief`` accepts CURRENT/STALE/UNAVAILABLE): a qualified
    read is CURRENT — the owner's own freshness gate passed at its pass, AND the
    quote still re-ages fresh at the reader's OWN read completion against the
    ceiling the artifact itself discloses (``meta.quote_freshness_policy``), with
    the read's own completion ET session still the candidate's representable
    market session.  A historical artifact without that disclosure has no lawful
    ceiling here — today's config is never substituted for it — and any failed
    check degrades to a typed reason in ``unavailable_reasons`` with
    ``quote_input=None``; nothing is fabricated in place of a measurement.  The
    input's ``source_receipt`` is the composite binding of
    :func:`quote_input_receipt` — both owner files as actually read, that disclosed
    policy, the native binding and both read clocks — not the quote file alone.

    The basis published for the quote is the MEASURED native quote family from the
    live owner's basis relation material (the private quote row's own ``basis`` names
    the vendor RUNG, a different axis), and the row's previous close must match the
    owner's disclosed measurement.  Failure of any check returns a result, never
    raises — caller-contract violations (wrong types for the trusted roots or the
    snapshot) are the one exception and raise TypeError/ValueError.
    """
    repo_root = _trusted_root(repo_root, "repo_root")
    live_root = _trusted_root(native_live_root, "native_live_root")
    if not isinstance(snapshot, CandidateEpisodeStoreSnapshot):
        raise TypeError(
            "snapshot must be an actual engine.us_candidate_episode.CandidateEpisodeStoreSnapshot"
        )

    result: dict[str, object] = {
        "schema": NATIVE_READ_SCHEMA,
        "availability": None,
        "quote_input": None,
        "quote_freshness": None,
        "binding": None,
        "native": None,
        "owner_reads": None,
        "clocks": None,
        "basis": None,
        "observed": None,
        "unavailable_reasons": [],
        "notes": [],
    }
    reasons: list[str] = result["unavailable_reasons"]
    notes: list[str] = result["notes"]

    def fail(reason: str, note: str | None = None) -> dict[str, object]:
        reasons.append(reason)
        if note:
            notes.append(note)
        return result

    generation = snapshot.generation
    generation_id = snapshot.generation_id

    # ── Fixed episode root: the supplied snapshot must BE this store's HEAD cut ──
    store_root = repo_root.joinpath(*_EPISODE_STORE_PARTS)
    expected_generation_dir = store_root / "generations" / generation_id
    if not _contained(repo_root, store_root) or not store_root.is_dir():
        return fail("EPISODE_ROOT_MISSING", str(store_root))
    supplied_path = Path(generation.path)
    if supplied_path.resolve() != expected_generation_dir.resolve():
        return fail(
            "SNAPSHOT_GENERATION_PATH_MISMATCH",
            f"{supplied_path} != {expected_generation_dir}",
        )

    # ── Fully load the canonical HEAD-backed snapshot and compare it to the cut ──
    try:
        fresh = load_candidate_episode_store_snapshot(store_root)
    except EpisodeContractError as exc:
        return fail("EPISODE_STORE_UNREADABLE", str(exc))
    if fresh.generation_id != generation_id:
        return fail("SNAPSHOT_DIVERGED_FROM_HEAD", fresh.generation_id)
    for field in ("events", "suppressions", "episodes"):
        mine = _canonical_snapshot_part(tuple(getattr(generation, field)))
        theirs = _canonical_snapshot_part(tuple(getattr(fresh.generation, field)))
        if mine != theirs:
            return fail("SNAPSHOT_DIVERGED_FROM_HEAD", field)
    if _canonical_snapshot_part(dict(generation.receipt)) != _canonical_snapshot_part(
        dict(fresh.generation.receipt)
    ):
        return fail("SNAPSHOT_DIVERGED_FROM_HEAD", "receipt")

    # ── Byte attestation BEFORE any owner read ──
    try:
        token_before = attest_candidate_episode_store_bytes(store_root)
    except EpisodeContractError as exc:
        return fail("EPISODE_STORE_ATTESTATION_FAILED", str(exc))
    if token_before.generation_id != generation_id:
        return fail("SNAPSHOT_DIVERGED_FROM_HEAD", token_before.generation_id)

    # ── Candidate source key + digest resolve ONE native event ──
    parsed_key = _parse_candidate_source_key(candidate_source_event_id)
    if parsed_key is None:
        return fail("CANDIDATE_SOURCE_KEY_INVALID", str(candidate_source_event_id))
    market_session, _key_ticker, board_definition = parsed_key
    source_receipt = candidate_source_receipt
    if not isinstance(source_receipt, str) or len(source_receipt) != len("sha256:") + 64 \
            or not source_receipt.startswith("sha256:") \
            or any(ch not in "0123456789abcdef" for ch in source_receipt[len("sha256:"):]):
        return fail("CANDIDATE_SOURCE_RECEIPT_INVALID")

    matches = [
        event for event in generation.events
        if event.get("source_system") == _CANDIDATE_SOURCE_SYSTEM
        and event.get("source_schema") == _CANDIDATE_SOURCE_SCHEMA
        and event.get("source_event_id") == candidate_source_event_id
        and event.get("source_receipt") == source_receipt
        and event.get("event_type") in ("OPENED", "OBSERVED")
    ]
    if len(matches) > 1:
        return fail("CANDIDATE_SOURCE_EVENT_AMBIGUOUS")
    if not matches:
        suppressed_key = any(
            suppression.get("source_system") == _CANDIDATE_SOURCE_SYSTEM
            and suppression.get("source_schema") == _CANDIDATE_SOURCE_SCHEMA
            and suppression.get("source_event_id") == candidate_source_event_id
            for suppression in generation.suppressions
        )
        return fail(
            "CANDIDATE_SOURCE_KEY_SUPPRESSED" if suppressed_key
            else "CANDIDATE_SOURCE_EVENT_NOT_FOUND"
        )
    event = matches[0]
    event_id_text = str(event["event_id"])
    episode_id_text = str(event["episode_id"])
    if any(
        item.get("event_type") == "RETRACTED" and item.get("correction_of") == event_id_text
        for item in generation.events
    ):
        return fail("CANDIDATE_SOURCE_EVENT_RETRACTED", event_id_text)

    episode_rows = [
        row for row in generation.episodes if row.get("episode_id") == episode_id_text
    ]
    if len(episode_rows) != 1:
        return fail("CANDIDATE_EPISODE_ROW_MISSING", episode_id_text)
    current_row = episode_rows[0]
    # This is the native B1 row, not the B3 display projection. Consume its
    # unchanged owner state law; ACTIVE alone does not confer future eligibility.
    lifecycle_state = current_row.get("episode_state")
    if not isinstance(lifecycle_state, str) or lifecycle_state not in {ACTIVE_STATE, *TERMINAL_STATES} or any(
        field not in current_row for field in ("terminal_reason", "superseded_by")
    ):
        return fail("CANDIDATE_EPISODE_STATE_MALFORMED", episode_id_text)
    terminal_reason = current_row["terminal_reason"]
    if ((lifecycle_state == ACTIVE_STATE and terminal_reason is not None)
            or (lifecycle_state in TERMINAL_STATES and
                (not isinstance(terminal_reason, str) or not terminal_reason))):
        return fail("CANDIDATE_EPISODE_STATE_MALFORMED", episode_id_text)
    successor = current_row["superseded_by"]
    if successor is not None:
        if not isinstance(successor, str) or not successor or successor == episode_id_text:
            return fail("CANDIDATE_EPISODE_STATE_MALFORMED", episode_id_text)
        return fail("CANDIDATE_EPISODE_SUPERSEDED", episode_id_text)
    if lifecycle_state in TERMINAL_STATES:
        return fail("CANDIDATE_EPISODE_TERMINAL", f"{episode_id_text}:{lifecycle_state}")

    security_id = current_row.get("security_id")
    if not isinstance(security_id, str) or not security_id:
        return fail("CANDIDATE_EPISODE_IDENTITY_MISSING", episode_id_text)
    try:
        symbol = _resolve_store_symbol(alias_table, security_id, market_session)
    except RuntimeOwnerFactError as exc:
        return fail("IDENTITY_ALIAS_UNRESOLVED", str(exc))

    corrections = sorted(
        str(item["event_id"]) for item in generation.events
        if item.get("event_type") == "CORRECTED"
        and (item.get("correction_of") == event_id_text
             or item.get("episode_id") == episode_id_text)
    )

    # ── The two fixed owner files, each read exactly once ──
    quotes_path = live_root.joinpath(*_QUOTES_FULL_PARTS)
    live_path = live_root.joinpath(*_LIVE_ARTIFACT_PARTS)
    for path in (quotes_path, live_path):
        if not _contained(live_root, path) or not path.is_file():
            return fail("OWNER_FILE_MISSING", str(path))
    file_bytes: dict[str, bytes] = {}
    try:
        file_bytes["quotes_full"] = _read_owner_bytes(quotes_path)
        file_bytes["prophet_live"] = _read_owner_bytes(live_path)
    except OSError as exc:
        return fail("OWNER_FILE_UNREADABLE", str(exc))
    file_digests = {name: _sha256_receipt(payload) for name, payload in file_bytes.items()}
    try:
        quote_envelope = json.loads(file_bytes["quotes_full"])
        live_artifact = json.loads(file_bytes["prophet_live"])
    except json.JSONDecodeError as exc:
        return fail("OWNER_PAYLOAD_MALFORMED", str(exc))

    # ── Private quotes envelope (scripts.build_live_quotes private shape) ──
    if not isinstance(quote_envelope, Mapping) or quote_envelope.get("source") != "snapshot":
        return fail("QUOTE_ENVELOPE_UNTRUSTED")
    envelope_ts = quote_envelope.get("ts")
    envelope_sessions = quote_envelope.get("sessions")
    envelope_meta = quote_envelope.get("meta")
    envelope_offline = envelope_meta.get("offline") if isinstance(envelope_meta, Mapping) else None
    if not isinstance(envelope_sessions, Mapping) or not isinstance(envelope_meta, Mapping) \
            or isinstance(envelope_ts, bool) or not isinstance(envelope_ts, int) \
            or not isinstance(envelope_offline, bool):
        return fail("QUOTE_ENVELOPE_MALFORMED")
    try:
        snapshot_clock = _utc(quote_envelope.get("asof"), "quotes_full.asof")
        snapshot_ts_clock = datetime.fromtimestamp(envelope_ts / 1000.0, tz=timezone.utc)
    except (RuntimeOwnerFactError, OSError, OverflowError) as exc:
        return fail("QUOTE_ENVELOPE_MALFORMED", str(exc))
    if envelope_offline:
        return fail("QUOTE_ENVELOPE_OFFLINE")

    # ── Live state artifact: schema, status, producer, meta, session law ──
    if not isinstance(live_artifact, Mapping) or live_artifact.get("schema") != _LIVE_STATES_SCHEMA:
        return fail("LIVE_OWNER_MALFORMED")
    if live_artifact.get("status") != "live":
        return fail("LIVE_OWNER_NOT_LIVE", str(live_artifact.get("status")))
    live_meta = live_artifact.get("meta")
    if not isinstance(live_meta, Mapping):
        return fail("LIVE_OWNER_MALFORMED")
    if live_meta.get("producer") != _LIVE_OWNER_PRODUCER:
        return fail("LIVE_OWNER_PRODUCER_MISMATCH", str(live_meta.get("producer")))
    try:
        pass_clock = _utc(live_meta.get("pass_ts"), "live.pass_ts")
    except RuntimeOwnerFactError as exc:
        return fail("LIVE_OWNER_MALFORMED", str(exc))
    session_et = live_meta.get("session_et")
    pack_as_of = live_meta.get("pack_as_of")
    if session_et != market_session or _live_states.session_et(pass_clock) != market_session \
            or not is_session(date.fromisoformat(market_session)):
        # The candidate tuple's market_session is the ORIGINAL source day.  A later
        # quote/pass session is never relabelled onto it — the relation is simply not
        # representable in v1 and no quote_input may be produced.
        return fail(
            "SESSION_RELATION_UNREPRESENTABLE",
            f"candidate source day {market_session} vs live session {session_et}",
        )
    if str(pack_as_of) != str(live_meta.get("expected_session")):
        return fail("LIVE_OWNER_STALE_PACK", f"pack_as_of={pack_as_of}")

    # ── The live owner's OWN disclosed staleness ceiling (the read's policy) ──
    # The reader re-ages the quote at its own read completion against the ceiling
    # the producing pass actually gated on, disclosed in the artifact's meta by
    # engine.prophet_live.live_states.  A historical artifact that predates the
    # disclosure has no lawful ceiling here: today's config is NOT substituted for
    # it (no fallback), the read simply types unavailable.  The bound must be a
    # finite positive NON-BOOL number under a known resolution class.
    policy_block = live_meta.get(_LIVE_FRESHNESS_POLICY_KEY)
    if not isinstance(policy_block, Mapping) \
            or policy_block.get("schema") != _live_states.FRESHNESS_POLICY_SCHEMA:
        return fail("LIVE_FRESHNESS_POLICY_MISSING", repr(policy_block)[:200])
    disclosed_limit_raw = policy_block.get("quote_max_age_min")
    if isinstance(disclosed_limit_raw, bool) \
            or not isinstance(disclosed_limit_raw, (int, float)) \
            or not isfinite(float(disclosed_limit_raw)) \
            or float(disclosed_limit_raw) <= 0.0:
        return fail("LIVE_FRESHNESS_POLICY_MALFORMED", repr(disclosed_limit_raw))
    disclosed_resolution = policy_block.get("resolution")
    if disclosed_resolution not in _LIVE_POLICY_RESOLUTIONS:
        return fail("LIVE_FRESHNESS_POLICY_MALFORMED", repr(disclosed_resolution))
    disclosed_limit = float(disclosed_limit_raw)
    disclosed_policy = {
        "schema": _live_states.FRESHNESS_POLICY_SCHEMA,
        "quote_max_age_min": disclosed_limit,
        "resolution": disclosed_resolution,
    }

    # ── Live state row: non-dark, genuinely RESOLVED with measured material ──
    live_states_rows = live_artifact.get("states")
    live_state = live_states_rows.get(symbol) if isinstance(live_states_rows, Mapping) else None
    if not isinstance(live_state, Mapping):
        return fail("LIVE_ROW_MISSING", symbol)
    if live_state.get("state") == "dark":
        return fail("LIVE_ROW_DARK", str(live_state.get("reason")))
    try:
        resolved_basis = _measured_basis_material(live_state, symbol, live_meta)
        state_price = _positive(live_state.get("price"), "live_state.price")
        state_age = _nonnegative(live_state.get("quote_age_min"), "live_state.quote_age_min")
    except RuntimeOwnerFactError as exc:
        return fail("LIVE_BASIS_NOT_RESOLVED", str(exc))

    # ── Private quote row for the canonical store symbol ──
    quote_rows = quote_envelope.get("quotes")
    quote_row = quote_rows.get(symbol) if isinstance(quote_rows, Mapping) else None
    if not isinstance(quote_row, Mapping):
        return fail("QUOTE_ROW_MISSING", symbol)
    if "quote_ts" not in quote_row or "quote_ts_synthetic" not in quote_row:
        return fail("QUOTE_PRIVATE_PROVENANCE_MISSING", symbol)
    if quote_row.get("quote_ts_synthetic") is not False:
        return fail("QUOTE_TS_SYNTHETIC", symbol)
    try:
        quote_clock = _utc(quote_row.get("quote_ts"), "quote.quote_ts")
    except RuntimeOwnerFactError as exc:
        return fail("QUOTE_CLOCK_MALFORMED", str(exc))
    quote_source = quote_row.get("source")
    if not isinstance(quote_source, str) or quote_source not in _REAL_QUOTE_SOURCES:
        return fail("QUOTE_SOURCE_UNTRUSTED", str(quote_source))
    try:
        _private_quote_rung(quote_row)
    except RuntimeOwnerFactError as exc:
        return fail("QUOTE_RUNG_UNTRUSTED", str(exc))
    quote_price = quote_row.get("price")
    if isinstance(quote_price, bool) or not isinstance(quote_price, (int, float)) \
            or not isfinite(float(quote_price)) or float(quote_price) <= 0:
        return fail("QUOTE_PRICE_MALFORMED")
    row_ts = quote_row.get("ts")
    if row_ts is not None:
        if isinstance(row_ts, bool) or not isinstance(row_ts, int) \
                or row_ts != int(quote_clock.timestamp() * 1000):
            return fail("QUOTE_TS_INCONSISTENT")

    # ── Clock relations (observation < snapshot < pass, same ET session) ──
    if quote_clock > pass_clock:
        return fail("QUOTE_AFTER_PASS")
    if quote_clock > snapshot_clock:
        return fail("QUOTE_AFTER_SNAPSHOT")
    if _live_states.session_et(quote_clock) != market_session:
        return fail("SESSION_RELATION_UNREPRESENTABLE", "quote session")

    # ── The quote must be the measurement the live owner read ──
    if round(state_price, 4) != round(float(quote_price), 4):
        return fail("QUOTE_PRICE_MISMATCH")
    bound_quote_age_min = round((pass_clock - quote_clock).total_seconds() / 60.0, 1)
    if abs(state_age - bound_quote_age_min) > 1e-9:
        return fail("QUOTE_AGE_MISMATCH")
    try:
        quote_prev_close = _private_quote_prev_close(quote_row, resolved_basis["prev_close"])
    except RuntimeOwnerFactError as exc:
        return fail("QUOTE_PREV_CLOSE_MISMATCH", str(exc))

    # ── Native source clocks, read from the exact event ──
    try:
        occurred_clock = _utc(event.get("occurred_at"), "event.occurred_at")
        known_clock = _utc(event.get("known_at"), "event.known_at")
        recorded_clock = _utc(event.get("recorded_at"), "event.recorded_at")
    except RuntimeOwnerFactError as exc:
        return fail("SOURCE_CLOCK_MALFORMED", str(exc))

    # ── Re-read both files once after assembly; re-attest the episode store ──
    for name, path in (("quotes_full", quotes_path), ("prophet_live", live_path)):
        try:
            reread = _read_owner_bytes(path)
        except OSError as exc:
            return fail("OWNER_FILE_UNREADABLE", str(exc))
        if reread != file_bytes[name]:
            return fail("OWNER_BYTES_CHANGED", name)
    try:
        token_after = attest_candidate_episode_store_bytes(store_root)
    except EpisodeContractError as exc:
        return fail("EPISODE_STORE_ATTESTATION_FAILED", str(exc))
    if token_after != token_before:
        return fail("STORE_BYTES_CHANGED")

    # ── Future clocks are rejected against the reader's OWN completion clock ──
    read_completed_at = _now_utc()
    read_completed_iso = read_completed_at.isoformat(timespec="seconds").replace(
        "+00:00", "Z")
    for label, clock in (
        ("source.occurred_at", occurred_clock),
        ("source.known_at", known_clock),
        ("source.recorded_at", recorded_clock),
        ("quotes_full.asof", snapshot_clock),
        ("quotes_full.ts", snapshot_ts_clock),
        ("live.pass_ts", pass_clock),
        ("quote.quote_ts", quote_clock),
    ):
        if clock > read_completed_at:
            return fail("FUTURE_OWNER_CLOCK", label)

    # ── Re-age the quote at the reader's OWN read completion (same-read law) ──
    # The pass-time freshness verdict belongs to the pass that produced it.  A read
    # that completes minutes — or weeks — later answers the SAME question at its
    # own completion clock, with the SAME raw-age > limit comparison and the SAME
    # 1-dp disclosed rounding the lane itself uses, and its own completion ET
    # session must still be the one session the candidate/source/quote/decision
    # tuple is representable in.  Aged-out and cross-session reads publish
    # NOTHING: no restamp, no renewal, and no assumption that today's policy
    # describes the artifact being read.
    read_session_et = _live_states.session_et(read_completed_at)
    own_age_raw = (read_completed_at - quote_clock).total_seconds() / 60.0
    own_reasons: list[str] = []
    if read_session_et != market_session:
        own_reasons.append("READ_SESSION_CROSS_SESSION")
    if own_age_raw > disclosed_limit:
        own_reasons.append("QUOTE_STALE_AT_OWN_READ")
    if own_reasons:
        own_note = (
            f"quote {quote_row.get('quote_ts')} re-aged at own read completion "
            f"{read_completed_iso}: {round(own_age_raw, 1)} min vs disclosed limit "
            f"{disclosed_limit} min; read ET session {read_session_et} vs market "
            f"session {market_session}")
        for reason in own_reasons:
            fail(reason, own_note)
        return result

    result["binding"] = {
        "security_id": security_id,
        "episode_id": episode_id_text,
        "candidate_generation_id": generation_id,
        "market_session": market_session,
        "store_symbol": symbol,
    }
    result["native"] = {
        "source_system": event.get("source_system"),
        "source_schema": event.get("source_schema"),
        "source_event_id": event.get("source_event_id"),
        "source_receipt": event.get("source_receipt"),
        "source_event_type": event.get("event_type"),
        "source_event_ref": event_id_text,
        "board_definition": board_definition,
        "episode_lifecycle_state": lifecycle_state,
        "anchor": dict(current_row.get("structural_anchor") or {}),
        "corrections": corrections,
        "retracted": False,
        "suppressed": False,
        "generation_suppressions_n": len(generation.suppressions),
        "store_byte_token": {
            "generation_id": token_before.generation_id,
            "manifest_sha256": token_before.manifest_sha256,
            "head_sha256": token_before.head_sha256,
        },
    }
    result["owner_reads"] = {
        "quotes_full": {
            "path": str(quotes_path),
            "sha256": file_digests["quotes_full"],
            "envelope_asof": quote_envelope.get("asof"),
            "envelope_ts": envelope_ts,
            "envelope_offline": envelope_offline,
        },
        "prophet_live": {
            "path": str(live_path),
            "sha256": file_digests["prophet_live"],
            "pass_ts": live_meta.get("pass_ts"),
            "producer": live_meta.get("producer"),
            "pack_as_of": pack_as_of,
            "session_et": session_et,
            "quote_freshness_policy": dict(disclosed_policy),
        },
    }
    result["clocks"] = {
        "source_observed_at": event.get("occurred_at"),
        "source_known_at": event.get("known_at"),
        "snapshot_asof": quote_envelope.get("asof"),
        "snapshot_ts": snapshot_ts_clock.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "live_pass_ts": live_meta.get("pass_ts"),
        "quote_observed_at": quote_row.get("quote_ts"),
        "read_completed_at": read_completed_iso,
        "read_session_et": read_session_et,
    }
    result["basis"] = {
        "receipt": live_state.get("basis_receipt"),
        "material": resolved_basis["material"],
        "levels_family": resolved_basis["levels_family"],
        "quote_family": resolved_basis["quote_family"],
        "as_of_close": resolved_basis["as_of_close"],
        "prev_close": resolved_basis["prev_close"],
    }
    result["observed"] = {
        "price": float(quote_price),
        "quote_source": quote_source,
        "quote_rung": quote_row.get("basis", quote_row.get("price_basis")),
        "prev_close": quote_prev_close,
        "quote_age_min": bound_quote_age_min,
        "quote_age_at_own_read_min": round(own_age_raw, 1),
    }
    # The owner's own gate passed at its pass AND the quote re-aged fresh at the
    # reader's own read completion against the owner's own disclosed ceiling, so
    # the qualified read is fresh; the quote_input's ``state`` carries the existing
    # consumer's vocabulary for that (CURRENT).  The receipt binds BOTH owner files
    # as read, that disclosed policy and the native binding — not the quote file
    # alone — so the CURRENT verdict is re-checkable without today's config.
    result["quote_freshness"] = "FRESH"
    quote_input: dict[str, object] = {
        "schema": _QUOTE_INPUT_SCHEMA,
        "owner_ref": "/".join(_QUOTES_FULL_PARTS),
        "live_owner_ref": "/".join(_LIVE_ARTIFACT_PARTS),
        "asof": read_completed_iso,
        "quotes_source_receipt": file_digests["quotes_full"],
        "live_source_receipt": file_digests["prophet_live"],
        "live_policy": dict(disclosed_policy),
        "state": "CURRENT",
        "security_id": security_id,
        "episode_id": episode_id_text,
        "candidate_generation_id": generation_id,
        "market_session": market_session,
        "observed_at": quote_row.get("quote_ts"),
        "read_completed_at": read_completed_iso,
        "price": float(quote_price),
        "basis": resolved_basis["quote_family"],
        "quote_age_at_own_read_min": round(own_age_raw, 1),
    }
    quote_input["source_receipt"] = quote_input_receipt(quote_input)
    result["quote_input"] = quote_input
    return result
