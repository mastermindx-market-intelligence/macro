"""Uncalibrated research-priority ordering (MO-DELTA-006).

A reading order over theme nodes, computed only from already-recorded evidence
dates and a within-date row count. This module is PURE: it never consults a
clock, the network, the disk, or another process. Given identical frozen inputs
it returns identical JSON-safe values.

Authority ceiling is research_priority_only. Calibrated fields stay held.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

SCHEMA = "mastermind.research_priority_ordering.v1"
ORDERING_RULE_ID = "evidence_recency_then_daily_count_then_name"
AUTHORITY_CEILING = "research_priority_only"
LEDGER_ROW = "MO-DELTA-006"
MAX_ITEMS = 12                      # rendered cap; see §2.11
DOES_NOT_CLAIM: tuple[str, ...] = (
    "probability", "confidence", "conviction", "expected impact",
    "expected return", "priced-in percentage", "direction", "rank", "score",
    "gate", "size", "trade instruction",
)
#: Store columns this module refuses to read. Every one is held behind K5 + Eval-OS
#: by MO-DELTA-006. Named here so the guard test can assert the refusal mechanically.
HELD_COLUMNS: frozenset[str] = frozenset({
    "economic_share", "trading_beta", "attention_share",
    "economic_share_formula_id", "trading_beta_formula_id", "attention_share_formula_id",
    "economic_share_display", "trading_beta_display", "attention_share_display",
    "confidence_basis",
})
#: Payload key names that may never exist at any depth of the emitted JSON.
FORBIDDEN_PAYLOAD_KEYS: frozenset[str] = frozenset({
    "rank", "ranking", "score", "priority_value", "probability", "prob",
    "confidence", "conviction", "certainty", "expected_impact", "expected_return",
    "expected_value", "priced_in", "priced_pct", "priced_percent", "direction",
    "directional", "edge", "percentile", "zscore", "z_score", "weight", "weighted",
    "gate", "sizing", "position_size", "upside", "downside", "win_rate",
    "opportunity_score", "conviction_score", "impact",
})

_DATE_HEAD = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
_ALLOWED_STATES = frozenset({"ok", "empty", "unavailable"})


@dataclass(frozen=True, slots=True)
class ThemeEvidence:
    """One theme node's already-read, current-belief evidence facts.

    Every field is an ADDRESS or an OBSERVED FACT. There is no measure here.
    """
    node_id: str
    name_en: str
    name_zh: str
    recorded_dates: tuple[str, ...]   # 'YYYY-MM-DD' per current-view edge; may be empty


@dataclass(frozen=True, slots=True)
class PriorityItem:
    position: int                  # 1-based place in this reading order. Not a rank.
    node_id: str
    name_en: str
    name_zh: str
    last_recorded_date: str | None  # None => the undated bucket
    statements_recorded: int        # rows recorded on last_recorded_date; 0 when undated


def _as_calendar_date(value: str) -> str | None:
    """Return YYYY-MM-DD or None. Malformed input is skipped, never coerced."""
    text = (value or "").strip()
    match = _DATE_HEAD.match(text)
    if not match:
        return None
    year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
    try:
        datetime(year, month, day)
    except ValueError:
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def order_items(themes: Sequence[ThemeEvidence]) -> tuple[PriorityItem, ...]:
    """Apply §2.1's rule. Total, permutation-invariant, no measure computed."""
    dated: list[tuple[str, int, str, str, ThemeEvidence]] = []
    undated: list[ThemeEvidence] = []
    for theme in themes:
        usable: list[str] = []
        for raw in theme.recorded_dates:
            parsed = _as_calendar_date(str(raw) if raw is not None else "")
            if parsed is not None:
                usable.append(parsed)
        if not usable:
            undated.append(theme)
            continue
        last = max(usable)
        count = sum(1 for item in usable if item == last)
        dated.append((last, count, theme.name_en, theme.node_id, theme))

    # Date and count descend; name and node_id ascend. One total key, no input order.
    dated.sort(key=lambda row: ((-_date_key(row[0])), -row[1], row[2], row[3]))
    undated.sort(key=lambda theme: (theme.name_en, theme.node_id))

    out: list[PriorityItem] = []
    for last, count, _name, _nid, theme in dated:
        out.append(
            PriorityItem(
                position=len(out) + 1,
                node_id=theme.node_id,
                name_en=theme.name_en,
                name_zh=theme.name_zh,
                last_recorded_date=last,
                statements_recorded=count,
            )
        )
    for theme in undated:
        out.append(
            PriorityItem(
                position=len(out) + 1,
                node_id=theme.node_id,
                name_en=theme.name_en,
                name_zh=theme.name_zh,
                last_recorded_date=None,
                statements_recorded=0,
            )
        )
    return tuple(out)


def _date_key(value: str) -> int:
    year, month, day = value.split("-")
    return int(year) * 10000 + int(month) * 100 + int(day)


def to_payload(items: Sequence[PriorityItem], *, asof: str, state: str) -> dict:
    """JSON-safe payload per §2.4. `asof` and `state` are supplied by the caller;
    this module never asks a clock and never decides whether a store exists."""
    if state not in _ALLOWED_STATES:
        state = "unavailable"
    seq = tuple(items)
    n_total = len(seq)
    shown = seq[:MAX_ITEMS]
    if state in {"empty", "unavailable"}:
        shown = ()
        n_total = 0
    elif not shown:
        state = "empty"
        n_total = 0
    return {
        "schema": SCHEMA,
        "ordering_rule_id": ORDERING_RULE_ID,
        "authority_ceiling": AUTHORITY_CEILING,
        "ledger_row": LEDGER_ROW,
        "asof": asof,
        "state": state,
        "max_items": MAX_ITEMS,
        "n_total": n_total,
        "items": [
            {
                "position": item.position,
                "node_id": item.node_id,
                "name_en": item.name_en,
                "name_zh": item.name_zh,
                "last_recorded_date": item.last_recorded_date,
                "statements_recorded": item.statements_recorded,
            }
            for item in shown
        ],
    }
