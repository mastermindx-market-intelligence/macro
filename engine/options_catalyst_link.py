"""Catalyst-linkage read-model over the live_flow event plane.

Tier: ``research_expression_only`` under ExpressionCandidate law (MO-PAID-070
``source_rights``; MO-DELTA-035). Zero entry authority and zero scoring
authority — does not rank, size, gate, originate a signal, or escalate. Every
emitted record carries ``engine.stock_identity.authority.authority_block()``
(five false booleans). No LLM originates, ranks, or escalates a binding
(Neural Web A7).

This is a **read-model** over the existing flow plane — no second option chain,
surface, Greeks, flow, or strategy-pricing engine. Scope: flow-event →
catalyst / ticker / expiry leg ONLY (exposure-map + structure legs deferred to
A-F03-W2-5).

Hermetic: no network, no clock reads, no ``data/`` I/O. Every input is injected
by the caller (mirrors ``engine.live_flow`` display-tier discipline).

Identity is exact membership of the option root (after ``.upper()``) in the
caller-supplied ``known_symbols`` set. There is no alias, share-class, or
adjusted-root map: ``BRK.B``, ``BRKB``, and ``AAPL1`` are distinct keys. A
recycled OCC root binds to whatever the current set and catalyst table say —
this layer does not recover issuer history. ``stock_identity.plane.symbols_on_plane``
is the cited authority for the *set*, not a root-to-symbol join.

Staleness reuses ``engine.earnings_catalyst``'s tri-state contract
(``STALE_AGE_TD``, ``fields_from_assessment``): ``stale=False`` is fresh only
when ``as_of_age_td`` accompanies it; ``True`` and ``None`` are untrustworthy.
This module does not re-derive a stale verdict from a wall clock.

Limitation: this layer does **not** adjust for splits or non-standard
multipliers. It binds the contract key as ``live_flow`` emitted it; a
mis-multiplied contract is out of scope and must not be silently corrected.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date, timedelta
from typing import (
    AbstractSet,
    Any,
    Iterable,
    Mapping,
    Sequence,
)

from engine.earnings_catalyst import STALE_AGE_TD
from engine.event_calendar import is_quad_witching, third_friday
from engine.stock_identity.authority import authority_block

SCHEMA = "options.catalyst_link/v1"
SPEC_VERSION = "v1"

# ── typed binding states (the ONLY legal values of binding_state) ─────────────
BOUND = "BOUND"
UNBOUND_NO_CATALYST = "UNBOUND_NO_CATALYST"
AMBIGUOUS_MULTIPLE = "AMBIGUOUS_MULTIPLE"
STALE_CATALYST = "STALE_CATALYST"
IDENTITY_UNRESOLVED = "IDENTITY_UNRESOLVED"
EXPIRY_MISMATCH = "EXPIRY_MISMATCH"
EXPIRY_BEFORE_ASOF = "EXPIRY_BEFORE_ASOF"
SAME_DAY_UNORDERED = "SAME_DAY_UNORDERED"
BINDING_STATES: tuple[str, ...] = (
    BOUND,
    UNBOUND_NO_CATALYST,
    AMBIGUOUS_MULTIPLE,
    STALE_CATALYST,
    IDENTITY_UNRESOLVED,
    EXPIRY_MISMATCH,
    EXPIRY_BEFORE_ASOF,
    SAME_DAY_UNORDERED,
)

DEFAULT_HORIZON_DAYS = 63  # calendar days of forward catalyst lookahead

_KIND_TIEBREAK: tuple[str, ...] = (
    "earnings",
    "fomc",
    "cpi",
    "ppi",
    "nfp",
    "pce",
    "gdp",
)

_EXPECTED_RECORD_KEYS: frozenset[str] = frozenset(
    {
        "schema",
        "spec_version",
        "session_date",
        "asof",
        "asof_vs_session",
        "horizon_days",
        "event_id",
        "contract",
        "binding_state",
        "identity",
        "catalyst",
        "catalyst_state",
        "catalyst_reason",
        "candidates",
        "expiry",
        "evidence",
        "source_rights",
        "authority",
        "is_context_only",
    }
)


class ContractKeyError(ValueError):
    """A live_flow event whose contract key cannot be reconstructed. FAIL LOUD."""


@dataclass(frozen=True)
class CatalystCandidate:
    kind: str  # "earnings" | "cpi" | "ppi" | "nfp" | "gdp" | "pce" | "fomc" | ...
    date: date  # the catalyst's dated occurrence
    source: str  # evidence source module, e.g. "engine.earnings_catalyst"
    artifact: str  # evidence artifact, e.g. "earnings_store"
    stale: bool | None  # TRI-STATE; None = never asked
    known_as_of: date | None = None  # when the catalyst became knowable; None = never asked
    as_of_age_td: int | None = None
    label: str | None = None  # human name, e.g. "Q3 results"
    locator: str | None = None  # producer locator, e.g. "earnings_blackout.assess"


@dataclass(frozen=True)
class CalendarContext:
    """Injected expiry-calendar facts. Pure; no network, no clock."""

    is_third_friday: bool | None
    is_quad_witching: bool | None
    macro_catalysts: tuple[CatalystCandidate, ...] = ()


@dataclass(frozen=True)
class CatalystLink:
    record: dict  # the JSON-serialisable link record
    binding_state: str  # one of BINDING_STATES (== record["binding_state"])


def _is_canonical_date(value: Any) -> bool:
    """YYYY-MM-DD that round-trips through ``date.fromisoformat`` (live_flow rule)."""
    if type(value) is not str:
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def contract_key(event: Mapping[str, Any]) -> tuple[str, str, float, str]:
    """(root, exp, strike, right) — the SAME tuple shape live_flow uses.

    Raises ContractKeyError when any leg is missing, empty, non-finite or
    non-canonical. Never returns a partial or defaulted key.
    """
    if "id" not in event or event["id"] is None or event["id"] == "":
        raise ContractKeyError("event identity (id) is required")

    root_raw = event.get("root")
    if root_raw is None or (isinstance(root_raw, str) and root_raw.strip() == ""):
        raise ContractKeyError("contract root is missing or empty")
    root = str(root_raw).upper()
    if not root:
        raise ContractKeyError("contract root is missing or empty")

    exp_raw = event.get("exp")
    if exp_raw is None or exp_raw == "":
        raise ContractKeyError("contract exp is missing or empty")
    # Non-canonical / unparseable exp is typed EXPIRY_MISMATCH in bind_event
    # Step 2 — contract_key only fails loud on a missing/empty exp leg.
    exp = str(exp_raw)

    if "strike" not in event or event["strike"] is None or event["strike"] == "":
        raise ContractKeyError("contract strike is missing")
    try:
        strike = float(event["strike"])
    except (TypeError, ValueError) as exc:
        raise ContractKeyError("contract strike is non-numeric") from exc
    if not (strike > 0.0 and strike < float("inf")):
        raise ContractKeyError("contract strike must be finite and positive")

    right_raw = event.get("right")
    if right_raw is None or right_raw == "":
        raise ContractKeyError("contract right is missing or empty")
    right = str(right_raw).strip().upper()[:1]
    if right not in ("C", "P"):
        raise ContractKeyError("contract right must be C or P")

    return (root, exp, strike, right)


def expiry_context(exp: date) -> dict:
    """``{'is_third_friday': bool, 'is_quad_witching': bool}`` via event_calendar."""
    return {
        "is_third_friday": exp == third_friday(exp.year, exp.month),
        "is_quad_witching": is_quad_witching(exp),
    }


def _canonical_session_date(raw: Any) -> str | None:
    if isinstance(raw, date) and type(raw) is date:
        return raw.isoformat()
    if isinstance(raw, str) and _is_canonical_date(raw):
        return raw
    return None


def _resolve_session_date(
    event: Mapping[str, Any],
    session_date: Any,
) -> str | None:
    """Producer session date only. Never ``observed_at``, ``ts``, or ``asof``.

    ``live_flow`` hashes the session into ``id`` and does not emit ``session_date``
    on the event dict, so the caller must pass it (kwarg or injected field).
    Absence is ``None`` — never fabricated.
    """
    for raw in (session_date, event.get("session_date")):
        resolved = _canonical_session_date(raw)
        if resolved is not None:
            return resolved
    return None


def _event_clock_date(event: Mapping[str, Any]) -> date | None:
    """Calendar date of the producer's ``ts`` (UTC ISO8601Z from live_flow)."""
    ts = event.get("ts")
    if isinstance(ts, str) and len(ts) >= 10 and _is_canonical_date(ts[:10]):
        return date.fromisoformat(ts[:10])
    return None


def _asof_vs_session(asof: date, session_date: str | None) -> str:
    if session_date is None:
        return "session_date_null"
    sess = date.fromisoformat(session_date)
    if asof < sess:
        return "asof_before_session"
    return "ok"


def _asof_vs_event(asof: date, event_date: date | None) -> str:
    if event_date is None:
        return "event_ts_untyped"
    if asof < event_date:
        return "asof_before_event"
    return "ok"


def _candidate_sort_key(c: CatalystCandidate) -> tuple:
    return (c.date.isoformat(), c.kind, c.source, c.artifact, c.label or "", c.locator or "")


def _kind_rank(kind: str) -> tuple:
    try:
        return (0, _KIND_TIEBREAK.index(kind))
    except ValueError:
        return (1, kind)


def _pick_co_dated(
    trusted_in_window: Sequence[CatalystCandidate],
) -> tuple[CatalystCandidate, list[CatalystCandidate]]:
    """Tie-break on identical dates — not a ranking. Frozen kind then source order."""
    ordered = sorted(
        trusted_in_window,
        key=lambda c: (_kind_rank(c.kind), c.kind, c.source, c.artifact),
    )
    winner = ordered[0]
    rest = [c for c in ordered[1:]]
    return winner, rest


def _stale_untrustworthy(c: CatalystCandidate) -> bool:
    """Same tri-state as ``earnings_catalyst.fields_from_assessment``.

    ``False`` is fresh only when an age accompanies it; ``True`` and ``None``
    are untrustworthy. Does not re-derive ``stale`` from ``STALE_AGE_TD``.
    """
    if c.stale is True or c.stale is None:
        return True
    if c.stale is False and c.as_of_age_td is None:
        return True
    return False


def _lookahead_excluded(c: CatalystCandidate, event_date: date | None) -> bool:
    """Unknowable at the event clock: ``known_as_of`` missing or after ``ts``."""
    if c.known_as_of is None:
        return True
    if event_date is None:
        return True
    return c.known_as_of > event_date


def _is_untrustworthy(c: CatalystCandidate, event_date: date | None) -> bool:
    return _stale_untrustworthy(c) or _lookahead_excluded(c, event_date)


def _candidate_row(
    c: CatalystCandidate,
    *,
    in_window: bool,
    event_date: date | None,
) -> dict[str, Any]:
    lookahead = _lookahead_excluded(c, event_date)
    trusted = not _is_untrustworthy(c, event_date)
    row: dict[str, Any] = {
        "kind": c.kind,
        "date": c.date.isoformat(),
        "source": c.source,
        "artifact": c.artifact,
        "stale": c.stale,
        "known_as_of": c.known_as_of.isoformat() if c.known_as_of is not None else None,
        "in_window": in_window,
        "trusted": trusted,
        "exclusion_reason": "LOOKAHEAD_EXCLUDED" if lookahead else None,
    }
    if c.stale is None:
        row["stale_reason"] = "never_checked"
    if c.as_of_age_td is not None:
        row["as_of_age_td"] = c.as_of_age_td
    if c.label is not None:
        row["label"] = c.label
    if c.locator is not None:
        row["locator"] = c.locator
    return row


def _catalyst_payload(
    c: CatalystCandidate,
    *,
    exp_date: date | None,
) -> dict[str, Any]:
    days_delta = None
    if exp_date is not None:
        days_delta = (exp_date - c.date).days
    payload: dict[str, Any] = {
        "kind": c.kind,
        "date": c.date.isoformat(),
        "source": c.source,
        "artifact": c.artifact,
        "label": c.label,
        "stale": c.stale,
        "known_as_of": c.known_as_of.isoformat() if c.known_as_of is not None else None,
        "as_of_age_td": c.as_of_age_td,
        "days_expiry_minus_catalyst": days_delta,
    }
    return payload


def _build_evidence(
    *,
    event_id: str,
    session_date: str | None,
    asof: date,
    event: Mapping[str, Any],
    identity_state: str,
    catalyst_state: str,
    catalyst: CatalystCandidate | None,
    expiry_state: str,
    exp_str: str | None,
    event_date: date | None,
) -> list[dict[str, Any]]:
    asof_s = asof.isoformat()
    observed = event.get("observed_at")
    if session_date is None:
        locator: str | None = None
        locator_state = "session_date_untyped"
    else:
        locator = f"data/live_flow_state/events/{session_date}.jsonl#{event_id}"
        locator_state = "ok"

    evt_ref: dict[str, Any] = {
        "ref_id": f"evt:{event_id}",
        "leg": "event",
        "source": "engine.live_flow",
        "artifact": "live_flow.event_stage/v1",
        "locator": locator,
        "locator_state": locator_state,
        "asof": asof_s,
        "observed_at": observed,
        "event_ts_date": event_date.isoformat() if event_date is not None else None,
        "asof_vs_event": _asof_vs_event(asof, event_date),
        "tier": "display",
    }

    if catalyst is None:
        cat_source: str | None = None
        cat_artifact: str | None = None
        cat_locator: str | None = None
        cat_known: str | None = None
        cat_age = None
        cat_stale = None
    else:
        cat_source = catalyst.source
        cat_artifact = catalyst.artifact
        cat_locator = catalyst.locator
        cat_known = (
            catalyst.known_as_of.isoformat() if catalyst.known_as_of is not None else None
        )
        cat_age = catalyst.as_of_age_td
        cat_stale = catalyst.stale

    cat_ref: dict[str, Any] = {
        "ref_id": (
            f"cat:{catalyst.kind}:{catalyst.date.isoformat()}"
            if catalyst is not None
            else f"cat:{catalyst_state}"
        ),
        "leg": "catalyst",
        "source": cat_source,
        "artifact": cat_artifact,
        "locator": cat_locator,
        "asof": asof_s,
        "known_as_of": cat_known,
        "as_of_age_td": cat_age,
        "stale": cat_stale,
        "tier": "display",
    }
    if catalyst_state != BOUND:
        cat_ref["state"] = catalyst_state
        if catalyst is None:
            cat_ref["locator"] = None

    exp_ref: dict[str, Any] = {
        "ref_id": f"exp:{exp_str}" if exp_str else f"exp:{expiry_state}",
        "leg": "expiry",
        "source": "engine.event_calendar",
        "artifact": "expiry_calendar/v1",
        "locator": "third_friday|is_quad_witching" if expiry_state == "OK" else None,
        "asof": asof_s,
        "tier": "display",
    }
    if expiry_state != "OK":
        exp_ref["state"] = expiry_state

    if identity_state != "RESOLVED":
        # Identity has no dedicated evidence leg in §6; trail stays on the three
        # declared legs. Unresolved identity is recorded via catalyst NOT_ATTEMPTED.
        pass

    return [evt_ref, cat_ref, exp_ref]


def _reduce_binding_state(
    *,
    identity_state: str,
    expiry_state: str,
    catalyst_state: str,
) -> str:
    if identity_state == IDENTITY_UNRESOLVED:
        return IDENTITY_UNRESOLVED
    if expiry_state == EXPIRY_MISMATCH:
        return EXPIRY_MISMATCH
    if expiry_state == EXPIRY_BEFORE_ASOF:
        return EXPIRY_BEFORE_ASOF
    if catalyst_state == AMBIGUOUS_MULTIPLE:
        return AMBIGUOUS_MULTIPLE
    if catalyst_state == SAME_DAY_UNORDERED:
        return SAME_DAY_UNORDERED
    if catalyst_state == STALE_CATALYST:
        return STALE_CATALYST
    if catalyst_state == UNBOUND_NO_CATALYST:
        return UNBOUND_NO_CATALYST
    if (
        identity_state == "RESOLVED"
        and expiry_state == "OK"
        and catalyst_state == BOUND
    ):
        return BOUND
    # Defensive: catalyst NOT_ATTEMPTED with resolved identity should not occur.
    if catalyst_state == "NOT_ATTEMPTED":
        return IDENTITY_UNRESOLVED
    return UNBOUND_NO_CATALYST


def bind_event(
    event: Mapping[str, Any],
    *,
    asof: date,
    catalysts: Mapping[str, Sequence[CatalystCandidate]],
    calendar: CalendarContext,
    known_symbols: AbstractSet[str],
    horizon_days: int = DEFAULT_HORIZON_DAYS,
    session_date: date | str | None = None,
) -> CatalystLink:
    """Deterministically bind ONE live_flow event to a catalyst/ticker/expiry tuple."""
    root, exp_str, strike, right = contract_key(event)
    event_id = str(event["id"])
    resolved_session = _resolve_session_date(event, session_date)
    event_date = _event_clock_date(event)
    asof_vs_session = _asof_vs_session(asof, resolved_session)

    # ── Step 1: identity ──────────────────────────────────────────────────────
    root_norm = root
    if root_norm in known_symbols:
        identity_state = "RESOLVED"
        resolved_symbol: str | None = root_norm
    else:
        identity_state = IDENTITY_UNRESOLVED
        resolved_symbol = None

    # ── Step 2: expiry ────────────────────────────────────────────────────────
    exp_date: date | None = None
    expiry_reason: str | None = None
    if not _is_canonical_date(exp_str):
        expiry_state = EXPIRY_MISMATCH
        expiry_reason = "expiry_unparseable"
        cal_block = {
            "is_third_friday": None,
            "is_quad_witching": None,
            "dte_calendar_days": None,
        }
    else:
        exp_date = date.fromisoformat(exp_str)
        ctx = expiry_context(exp_date)
        cal_block = {
            "is_third_friday": ctx["is_third_friday"],
            "is_quad_witching": ctx["is_quad_witching"],
            "dte_calendar_days": (exp_date - asof).days,
        }
        if exp_date < asof:
            expiry_state = EXPIRY_BEFORE_ASOF
            expiry_reason = "expiry_before_asof"
        else:
            expiry_state = "OK"

    # ── Steps 3–6: catalyst (skipped when identity unresolved) ────────────────
    catalyst_obj: CatalystCandidate | None = None
    catalyst_payload: dict[str, Any] | None = None
    catalyst_state: str
    catalyst_reason: str | None = None
    candidate_rows: list[dict[str, Any]] = []
    co_dated: list[CatalystCandidate] = []

    if identity_state == IDENTITY_UNRESOLVED:
        catalyst_state = "NOT_ATTEMPTED"
        catalyst_reason = None
    else:
        # Step 3 — pool: single-name for this root + market-wide macros
        root_cands = list(catalysts.get(root_norm, ()))
        macro_cands = list(calendar.macro_catalysts)
        concatenated = root_cands + macro_cands
        seen: set[tuple] = set()
        pool: list[CatalystCandidate] = []
        for c in concatenated:
            key = (c.kind, c.date.isoformat(), c.source, c.artifact, c.label, c.locator)
            if key in seen:
                continue
            seen.add(key)
            pool.append(c)
        pool.sort(key=_candidate_sort_key)

        horizon_end = asof + timedelta(days=horizon_days)
        if exp_date is not None:
            window_end = min(exp_date, horizon_end)
        else:
            window_end = horizon_end

        def _in_window(c: CatalystCandidate) -> bool:
            return asof <= c.date <= window_end

        if not pool:
            catalyst_state = UNBOUND_NO_CATALYST
            catalyst_reason = "no_candidates_for_root"
            candidate_rows = []
        else:
            in_window_list = [c for c in pool if _in_window(c)]
            candidate_rows = [
                _candidate_row(
                    c,
                    in_window=_in_window(c),
                    event_date=event_date,
                )
                for c in pool
            ]
            if not in_window_list:
                catalyst_state = UNBOUND_NO_CATALYST
                if exp_date is not None and all(c.date > exp_date for c in pool):
                    catalyst_reason = "all_candidates_after_expiry"
                else:
                    catalyst_reason = "no_candidate_in_window"
            else:
                trusted_in_window = [
                    c for c in in_window_list if not _is_untrustworthy(c, event_date)
                ]
                if not trusted_in_window:
                    catalyst_state = STALE_CATALYST
                    if in_window_list and all(
                        _lookahead_excluded(c, event_date) for c in in_window_list
                    ):
                        catalyst_reason = "LOOKAHEAD_EXCLUDED"
                    else:
                        catalyst_reason = None
                else:
                    distinct_dates = sorted({c.date for c in trusted_in_window})
                    if len(distinct_dates) >= 2:
                        catalyst_state = AMBIGUOUS_MULTIPLE
                        catalyst_reason = None
                        catalyst_obj = None
                    else:
                        catalyst_obj, co_dated = _pick_co_dated(trusted_in_window)
                        catalyst_payload = _catalyst_payload(
                            catalyst_obj, exp_date=exp_date
                        )
                        if co_dated:
                            catalyst_payload["co_dated"] = [
                                {
                                    "kind": c.kind,
                                    "date": c.date.isoformat(),
                                    "source": c.source,
                                    "artifact": c.artifact,
                                    "label": c.label,
                                }
                                for c in co_dated
                            ]
                        if event_date is not None and catalyst_obj.date == event_date:
                            catalyst_state = SAME_DAY_UNORDERED
                            catalyst_reason = "same_day_unordered"
                        elif event_date is None and catalyst_obj.date == asof:
                            catalyst_state = SAME_DAY_UNORDERED
                            catalyst_reason = "same_day_unordered"
                        else:
                            catalyst_state = BOUND
                            catalyst_reason = None

    binding_state = _reduce_binding_state(
        identity_state=identity_state,
        expiry_state=expiry_state,
        catalyst_state=catalyst_state,
    )

    evidence = _build_evidence(
        event_id=event_id,
        session_date=resolved_session,
        asof=asof,
        event=event,
        identity_state=identity_state,
        catalyst_state=catalyst_state,
        catalyst=catalyst_obj,
        expiry_state=expiry_state,
        exp_str=exp_str if _is_canonical_date(exp_str) else None,
        event_date=event_date,
    )

    record: dict[str, Any] = {
        "schema": SCHEMA,
        "spec_version": SPEC_VERSION,
        "session_date": resolved_session,
        "asof": asof.isoformat(),
        "asof_vs_session": asof_vs_session,
        "horizon_days": horizon_days,
        "event_id": event_id,
        "contract": {
            "root": root_norm,
            "exp": exp_str,
            "strike": strike,
            "right": right,
        },
        "binding_state": binding_state,
        "identity": {
            "state": identity_state,
            "resolved_symbol": resolved_symbol,
            "authority_source": "stock_identity.plane.symbols_on_plane",
            "match": "exact_root_upper",
        },
        "catalyst": catalyst_payload,
        "catalyst_state": catalyst_state,
        "catalyst_reason": catalyst_reason,
        "candidates": candidate_rows,
        "expiry": {
            "state": expiry_state,
            "reason": expiry_reason,
            "exp": exp_str,
            "dte_calendar_days": cal_block["dte_calendar_days"],
            "is_third_friday": cal_block["is_third_friday"],
            "is_quad_witching": cal_block["is_quad_witching"],
            "calendar_source": "engine.event_calendar",
        },
        "evidence": evidence,
        "source_rights": "research_expression_only",
        "authority": authority_block(),
        "is_context_only": True,
    }

    keys = set(record)
    if keys != _EXPECTED_RECORD_KEYS:
        raise ValueError(
            "catalyst-link record key set drifted: "
            f"extra={sorted(keys - _EXPECTED_RECORD_KEYS)} "
            f"missing={sorted(_EXPECTED_RECORD_KEYS - keys)}"
        )

    return CatalystLink(record=record, binding_state=binding_state)


def bind_events(
    events: Iterable[Mapping[str, Any]],
    *,
    asof: date,
    catalysts: Mapping[str, Sequence[CatalystCandidate]],
    calendar: CalendarContext,
    known_symbols: AbstractSet[str],
    horizon_days: int = DEFAULT_HORIZON_DAYS,
    session_date: date | str | None = None,
) -> list[CatalystLink]:
    """bind_event over an iterable, in input order. Propagates ContractKeyError."""
    return [
        bind_event(
            ev,
            asof=asof,
            catalysts=catalysts,
            calendar=calendar,
            known_symbols=known_symbols,
            horizon_days=horizon_days,
            session_date=session_date,
        )
        for ev in events
    ]


def write_links(path: os.PathLike[str] | str, links: Sequence[CatalystLink]) -> int:
    """Write link records as JSONL to an EXPLICIT path. Returns rows written.

    Replaces the file (idempotent re-run of the same links). Never derives a
    path from config; refuses the repo ``data/`` tree. Tests pass tmp_path only.
    """
    out = os.fspath(path)
    abs_out = os.path.abspath(out)
    repo_data = os.path.abspath("data")
    if abs_out == repo_data or abs_out.startswith(repo_data + os.sep):
        raise ValueError("write_links refuses repo data/ paths (no data/ I/O)")
    parent = os.path.dirname(out)
    if parent:
        os.makedirs(parent, exist_ok=True)
    n = 0
    with open(out, "w", encoding="utf-8") as fh:
        for link in links:
            fh.write(json.dumps(link.record, sort_keys=True, separators=(",", ":")) + "\n")
            n += 1
    return n


__all__ = (
    "SCHEMA",
    "SPEC_VERSION",
    "BOUND",
    "UNBOUND_NO_CATALYST",
    "AMBIGUOUS_MULTIPLE",
    "STALE_CATALYST",
    "IDENTITY_UNRESOLVED",
    "EXPIRY_MISMATCH",
    "EXPIRY_BEFORE_ASOF",
    "SAME_DAY_UNORDERED",
    "BINDING_STATES",
    "DEFAULT_HORIZON_DAYS",
    "STALE_AGE_TD",
    "ContractKeyError",
    "CatalystCandidate",
    "CalendarContext",
    "CatalystLink",
    "contract_key",
    "expiry_context",
    "bind_event",
    "bind_events",
    "write_links",
)
