"""Nightly catalyst-links producer — first production caller of bind_events.

Reads the date-keyed live-flow events stage the episode builder already
reads, binds each event to an earnings date and to FOMC decision dates, and
writes a context-only histogram. It does not rank, size, gate, originate a
signal, or open a second collector. The page that would show these links is
a later packet.

F03-W3-2 ADDITIVE CONSUMER (A-F03-W3-2):
The envelope's new `macro_calendar` key is consumed by
`scripts/build_options_command.py::load_catalyst_links`, which compares the
calendar's FOMC dates to each index-card payoff-lab expiry and surfaces a
small "Fed decision before this expiry" chip on the SPY/QQQ/IWM fold. The
chip is display-only context — same envelope, same authority block, no new
collector. The calendar is built from the SAME `_macro_candidates(asof,
horizon)` list the binder already reads (the producer never opens a second
calendar reader), so the chip's "is a Fed decision inside this expiry?"
answer is one comparison of two dates this artifact hands the page.

LAG (one nightly, by design):
In `.github/workflows/daily.yml` this producer step runs AFTER
`build_options_command`, so the page reads the PREVIOUS nightly's calendar.
The chip's tooltip prints the calendar's as-of date so the reader can see
which nightly's calendar the chip is reading. Moving the step to run before
the page builder is out of scope for this packet (`.github/**` excluded).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine import earnings_blackout
from engine.earnings_catalyst import fields_from_assessment
from engine.event_calendar import fomc_decision_dates
from engine.options_catalyst_link import (
    BINDING_STATES,
    SPEC_VERSION,
    CalendarContext,
    CatalystCandidate,
    bind_events,
    write_links,
)
from engine.stock_identity.authority import authority_block
from engine.stock_identity.plane import PLANE_STOCKS, symbols_on_plane
from scripts.build_options_signal_episode import (
    discover_event_sessions,
    fetch_event_stage,
)

ENVELOPE_SCHEMA = "mastermind.options_catalyst_links/v1"
IDENTITY_SOURCE = "stock_identity.plane:stocks"
EVENT_STAGE_SCHEMA = "live_flow.event_stage/v1"
_NO_EARNINGS_REASONS = frozenset({"next_date_missing", "ticker_not_in_store"})
_STORE_MISSING_REASON = "store_missing_or_empty"
_MAX_ENVELOPE_BYTES = 2 * 1024 * 1024


def utc_today() -> date:
    """The UTC calendar day the nightly binds against."""
    return datetime.now(timezone.utc).date()


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bind one session of live-flow events to earnings and FOMC catalysts."
    )
    parser.add_argument("--session", default=None, help="Session date YYYY-MM-DD. Default: latest retained date on or before today.")
    parser.add_argument("--out", default="site/options_catalyst_links", help="Directory for the JSONL and latest.json envelope.")
    parser.add_argument("--horizon-days", type=int, default=63, help="Forward calendar days of catalyst lookahead.")
    return parser.parse_args(argv)


def _canonical_session(raw: str) -> str:
    try:
        parsed = date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"Session {raw!r} is not a calendar date.") from exc
    if parsed.isoformat() != raw:
        raise ValueError(f"Session {raw!r} is not a calendar date.")
    return raw


def resolve_session(explicit: str | None, today: date) -> str | None:
    """Latest retained events date on or before today, unless --session is set."""
    if explicit is not None and explicit != "":
        return _canonical_session(explicit)
    today_iso = today.isoformat()
    eligible = [s for s in discover_event_sessions() if s <= today_iso]
    if not eligible:
        return None
    return max(eligible)


def _has_id_root_exp(event: Mapping[str, Any]) -> bool:
    if "id" not in event or event["id"] is None or event["id"] == "":
        return False
    root = event.get("root")
    if root is None or (isinstance(root, str) and root.strip() == ""):
        return False
    exp = event.get("exp")
    if exp is None or exp == "":
        return False
    return True


def _classify_row(row: Any) -> tuple[str, dict[str, Any] | None]:
    """Split a stage line into an event, a drop, or a non-event receipt.

    Production lines are decision receipts (``kind=decision``, the live-flow
    dict under ``event``) plus a paired availability receipt. Availability is
    not an event. Bare event dicts, which the tests inject, are accepted as-is.
    """
    if not isinstance(row, dict):
        return "drop", None
    if row.get("schema") == EVENT_STAGE_SCHEMA and row.get("kind") == "availability":
        return "skip", None
    if row.get("schema") == EVENT_STAGE_SCHEMA and row.get("kind") == "decision":
        event = row.get("event")
        if isinstance(event, dict) and _has_id_root_exp(event):
            return "event", event
        return "drop", None
    if _has_id_root_exp(row):
        return "event", dict(row)
    return "drop", None


def _split_stage(rows: list[Any]) -> tuple[list[dict[str, Any]], int]:
    kept: list[dict[str, Any]] = []
    dropped = 0
    for row in rows:
        kind, event = _classify_row(row)
        if kind == "event" and event is not None:
            kept.append(event)
        elif kind == "drop":
            dropped += 1
    return kept, dropped


def _parse_catalyst_date(raw: Any) -> date | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if len(text) < 10:
        return None
    head = text[:10]
    try:
        parsed = date.fromisoformat(head)
    except ValueError:
        return None
    if parsed.isoformat() != head:
        return None
    return parsed


def _age_days(age: Any) -> int | None:
    if isinstance(age, bool) or not isinstance(age, int) or age < 0:
        return None
    return age


def _known_as_of_from_business_day_age(asof: date, age: int) -> date | None:
    """Date ``age`` index steps before ``asof`` on the calendar ``assess`` uses.

    ``as_of_age_td`` is ``searchsorted(asof) - searchsorted(known)`` on that
    weekday index. A weekend already sits on the next weekday, and a weekday
    holiday stays on the index, so age 1 on Saturday or on Labor Day is the
    Friday the row was known. Walking NYSE sessions back from the last session
    stamps the day before that Friday. ``None`` when the index cannot reach
    the step.
    """
    calendar = earnings_blackout._build_td_calendar()
    if len(calendar) == 0:
        return None
    pos = int(calendar.searchsorted(pd.Timestamp(asof), side="left"))
    known_pos = pos - age
    if pos >= len(calendar) or known_pos < 0:
        return None
    return pd.Timestamp(calendar[known_pos]).date()


def _earnings_candidate(root: str, asof: date, assessment: Any) -> tuple[CatalystCandidate | None, bool]:
    """One earnings candidate, plus whether the store itself was missing."""
    if not isinstance(assessment, dict):
        return None, False
    reason = assessment.get("reason")
    if reason == _STORE_MISSING_REASON:
        return None, True
    if reason in _NO_EARNINGS_REASONS:
        return None, False
    fields = fields_from_assessment(assessment, asof)
    catalyst_date = _parse_catalyst_date(assessment.get("next_date"))
    if catalyst_date is None:
        return None, False
    age = _age_days(fields.get("as_of_age_td"))
    stale = fields.get("stale")
    if stale not in (True, False, None):
        stale = None
    known_as_of = _known_as_of_from_business_day_age(asof, age) if age is not None else None
    return CatalystCandidate(
        kind="earnings",
        date=catalyst_date,
        source="earnings_blackout",
        artifact=str(earnings_blackout._STORE_PATH),
        stale=stale,
        known_as_of=known_as_of,
        as_of_age_td=age,
        label="earnings",
        locator=f"earnings_blackout:{root}",
    ), False


def _earnings_for_roots(
    roots: list[str], asof: date,
) -> tuple[dict[str, tuple[CatalystCandidate, ...]], int, bool]:
    mapping: dict[str, tuple[CatalystCandidate, ...]] = {}
    built = 0
    store_missing = False
    for root in roots:
        candidate, missing = _earnings_candidate(
            root, asof, earnings_blackout.assess(root, today=asof),
        )
        store_missing = store_missing or missing
        if candidate is None:
            continue
        mapping[root] = (candidate,)
        built += 1
    return mapping, built, store_missing


def _macro_candidates(asof: date, horizon_days: int) -> list[CatalystCandidate]:
    """FOMC dates go on the shared calendar, never into a per-root map.

    ``known_as_of`` is 1 June of the prior year because the Fed publishes that
    year's decision calendar in advance. ``as_of_age_td`` is 0 so a published
    date is fresh: this is not an earnings-store age.
    """
    end = asof + timedelta(days=horizon_days)
    candidates: list[CatalystCandidate] = []
    for day in fomc_decision_dates(asof, end):
        candidates.append(CatalystCandidate(
            kind="fomc",
            date=day,
            source="event_calendar",
            artifact="engine.event_calendar._FOMC",
            stale=False,
            known_as_of=date(day.year - 1, 6, 1),
            as_of_age_td=0,
            label="FOMC rate decision",
            locator=f"event_calendar:fomc:{day.isoformat()}",
        ))
    return candidates


def _macro_calendar(asof: date, horizon_days: int,
                     candidates: list[CatalystCandidate] | None = None) -> dict[str, Any]:
    """A-F03-W3-2 — the envelope's `macro_calendar` key.

    Built from the SAME `_macro_candidates(asof, horizon_days)` list the
    binder reads; the producer never opens a second calendar reader. The
    page's catalyst-chip helper compares two dates from this dict to the
    payoff-lab card's expiry, so the dict is intentionally flat and
    date-only (no `known_as_of`, no `as_of_age_td`, no `locator` — none of
    those fields change the chip's answer and none belong on the page).

    `candidates` accepts the SAME `_macro_candidates(asof, horizon_days)`
    list the binder already built (computed once per call site, shared by
    the binder AND this calendar writer) so the envelope and the JSONL
    links agree byte-for-byte and the producer only opens
    `engine.event_calendar` once per nightly. When omitted, the helper
    rebuilds the list itself — used by `_emit_no_stage` on the
    events-outage path where no binder call exists to share with.

    Shape:
      {
        "asof":        "<asof iso>",          # the producer's own as-of date
        "horizon_end": "<(asof + horizon_days) iso>",
        "source":      "engine.event_calendar", # the same source the binder reads
        "fomc": [
          {"date": "YYYY-MM-DD", "label": "Fed rate decision"},
          ...
        ],                                     # sorted by date, possibly empty
      }
    """
    if candidates is None:
        candidates = _macro_candidates(asof, horizon_days)
    horizon_end = asof + timedelta(days=horizon_days)
    # The envelope key is named `fomc` and labels each entry "Fed rate
    # decision" — the consumer renders both names on the page, so any
    # non-fomc candidate would print as a non-Fed date to users.  The
    # current `_macro_candidates` emits fomc-only, but the filter is the
    # load-bearing guard: a second contributor of kind `cpi`, `nfp`, or
    # anything else would otherwise leak through with a Fed label.
    return {
        "asof": asof.isoformat(),
        "horizon_end": horizon_end.isoformat(),
        "source": "engine.event_calendar",
        "fomc": [
            {"date": cand.date.isoformat(), "label": "Fed rate decision"}
            for cand in candidates
            if getattr(cand, "kind", None) == "fomc"
        ],
    }


def _distinct_roots(events: list[Mapping[str, Any]]) -> list[str]:
    roots: list[str] = []
    seen: set[str] = set()
    for event in events:
        root = str(event.get("root") or "").strip().upper()
        if root and root not in seen:
            seen.add(root)
            roots.append(root)
    return roots


def _zero_states() -> dict[str, int]:
    return {state: 0 for state in BINDING_STATES}


def _warn(message: str) -> None:
    print(f"::warning title=options_catalyst_links::{message}", flush=True)


def _print_summary(session: str | None, events: int, bound: int, unbound: int, unresolved: int) -> None:
    session_text = session if session else "none"
    print(
        "options_catalyst_links: "
        f"session={session_text} events={events} bound={bound} "
        f"unbound={unbound} unresolved={unresolved}",
        flush=True,
    )


def _write_envelope(out_dir: Path, envelope: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    text = json.dumps(envelope, indent=2) + "\n"
    encoded = text.encode("utf-8")
    if len(encoded) > _MAX_ENVELOPE_BYTES:
        raise ValueError("The catalyst links envelope is larger than 2 MB.")
    target = out_dir / "latest.json"
    tmp = out_dir / "latest.json.tmp"
    tmp.write_bytes(encoded)
    os.replace(tmp, target)


def _source_block(session: str | None) -> dict[str, str]:
    if session:
        events = f"r2:live_flow/events/{session}.jsonl"
    else:
        events = "r2:live_flow/events/"
    return {
        "events": events,
        "earnings": "engine.earnings_blackout",
        "macro": "engine.event_calendar",
        "identity": IDENTITY_SOURCE,
    }


def _envelope(
    *,
    session: str | None,
    asof: date,
    horizon_days: int,
    counts: dict[str, Any],
    states: list[str],
    links_path: str | None,
    include_empty_links: bool,
    macro_calendar: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema": ENVELOPE_SCHEMA,
        "spec_version": SPEC_VERSION,
        "session_date": session,
        "asof": asof.isoformat(),
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "horizon_days": horizon_days,
        "source": _source_block(session),
        "counts": counts,
        "authority": authority_block(),
        "is_context_only": True,
        "states": states,
        "links_path": links_path,
        # A-F03-W3-2 — chip-on-the-page calendar (built from the SAME
        # `_macro_candidates` list the binder reads).  The optional kwarg lets
        # the no-stage path pass an empty-`fomc` calendar without re-reading
        # the calendar reader, and the call sites that already have a real
        # `_macro_candidates` list pass it in.
        "macro_calendar": (
            macro_calendar
            if macro_calendar is not None
            else _macro_calendar(asof, horizon_days)
        ),
        # _macro_calendar is appended below on the events-present path —
        # the binder's already-built `macros` list is shared with the
        # calendar writer so the producer opens engine.event_calendar
        # exactly once per nightly.
    }
    if include_empty_links:
        payload["links"] = []
    return payload


def _empty_counts() -> dict[str, Any]:
    return {
        "events": 0,
        "dropped_malformed": 0,
        "known_symbols": 0,
        "candidates_earnings": 0,
        "candidates_macro": 0,
        "by_state": _zero_states(),
    }


def _emit_no_stage(out_dir: Path, session: str | None, asof: date, horizon_days: int) -> None:
    links_path = None
    if session is not None:
        jsonl = out_dir / f"{session}.jsonl"
        write_links(jsonl, [])
        links_path = jsonl.name
    envelope = _envelope(
        session=session,
        asof=asof,
        horizon_days=horizon_days,
        counts=_empty_counts(),
        states=["no_event_stage"],
        links_path=links_path,
        include_empty_links=True,
        # On an events outage the chip must not vanish from the page; the
        # calendar is built from the same engine.event_calendar reader the
        # binder uses, so a missing events stage does NOT mean a missing
        # FOMC calendar.  Passing it explicitly here (rather than letting
        # `_envelope` build a fresh one) keeps the no-stage envelope and
        # the events-present envelope on the SAME calendar read.
        macro_calendar=_macro_calendar(asof, horizon_days),
    )
    _write_envelope(out_dir, envelope)
    _warn("No event stage was found for this session. 这一交易日没有找到事件阶段。")
    _print_summary(session, 0, 0, 0, 0)


def _states_for_run(*, identity_absent: bool, store_missing: bool) -> list[str]:
    states = ["ok"]
    if identity_absent:
        states.append("identity_plane_absent")
    if store_missing:
        states.append("earnings_store_missing")
    return states


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.horizon_days < 0:
        raise ValueError("Horizon days cannot be negative.")
    asof = utc_today()
    horizon = args.horizon_days
    out_dir = Path(args.out)
    session = resolve_session(args.session, asof)
    if session is None:
        _emit_no_stage(out_dir, None, asof, horizon)
        return 0

    rows = fetch_event_stage(session)
    if rows is None:
        _emit_no_stage(out_dir, session, asof, horizon)
        return 0

    kept, dropped = _split_stage(list(rows))
    known_symbols = {symbol.upper() for symbol in symbols_on_plane(PLANE_STOCKS)}
    identity_absent = len(known_symbols) == 0
    roots = _distinct_roots(kept)
    catalysts, n_earnings, store_missing = _earnings_for_roots(roots, asof)
    macros = _macro_candidates(asof, horizon)
    # One calendar is shared by every event. Third-Friday and quad-witching are
    # per expiry, so they stay None here. bind_event computes them from the
    # event expiry and records None when that expiry does not parse.
    calendar = CalendarContext(
        is_third_friday=None,
        is_quad_witching=None,
        macro_catalysts=tuple(macros),
    )
    links = bind_events(
        kept,
        asof=asof,
        catalysts=catalysts,
        calendar=calendar,
        known_symbols=known_symbols,
        horizon_days=horizon,
        session_date=session,
    )
    jsonl = out_dir / f"{session}.jsonl"
    write_links(jsonl, links)

    by_state = _zero_states()
    for link in links:
        by_state[link.binding_state] = by_state.get(link.binding_state, 0) + 1
    counts = {
        "events": len(kept) + dropped,
        "dropped_malformed": dropped,
        "known_symbols": len(known_symbols),
        "candidates_earnings": n_earnings,
        "candidates_macro": len(macros),
        "by_state": by_state,
    }
    if sum(by_state.values()) != counts["events"] - counts["dropped_malformed"]:
        raise RuntimeError("The binding-state histogram does not match the events that were bound.")

    envelope = _envelope(
        session=session,
        asof=asof,
        horizon_days=horizon,
        counts=counts,
        states=_states_for_run(identity_absent=identity_absent, store_missing=store_missing),
        links_path=jsonl.name,
        include_empty_links=False,
        # Pass the SAME candidate list the binder already built so the
        # envelope and the JSONL links agree byte-for-byte AND the
        # producer opens engine.event_calendar exactly once per nightly.
        macro_calendar=_macro_calendar(asof, horizon, candidates=macros),
    )
    _write_envelope(out_dir, envelope)
    if identity_absent:
        _warn("The stock identity plane has no symbols, so every event stays unresolved. 股票身份平面没有代码，所以每条事件都无法对应到股票。")
    if store_missing:
        _warn("The earnings store has no rows, so no earnings catalyst was built. 盈利数据不存在，所以没有生成盈利催化剂。")
    if dropped:
        _warn("Some event rows were dropped because they had no id, root, or expiry. 部分事件行缺少编号、标的或到期日，已经丢弃。")
    _print_summary(
        session,
        counts["events"],
        by_state["BOUND"],
        by_state["UNBOUND_NO_CATALYST"],
        by_state["IDENTITY_UNRESOLVED"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
