"""The deferred-papers ledger — what the download cap made us leave behind.

MarketDesk publishes ~200 papers/day; one account can pull ~70. Everything the
allocator does not reach stays a candidate (DISCOVERED / BLOB_FOUND) forever, and
that residue IS the backfill plan for the day we add more accounts. This module
turns it into a report: how big is it, how far back does it go, who published it,
and — the part that decides what a new account should pull first — what are the
highest-scoring papers still waiting.

Everything here is PURE in the same sense as ``allocator.py``: functions take an
open sqlite ``Connection`` plus an injected ``now`` (tz-aware UTC), never read the
clock, and never touch the network — so the whole report is unit-testable against
a temp DB. Rendering is separated from computation so ``--json`` and the printed
report are guaranteed to describe the same snapshot.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import allocator

#: Candidate statuses — kept identical to the allocator's, since the point of the
#: report is "what the allocator could still pull".
CANDIDATE_STATUSES = allocator.CANDIDATE_STATUSES

DEFAULT_TOP_N = 30
DAY_HISTOGRAM_DAYS = 14
TOP_INSTITUTIONS = 15


@dataclass
class BacklogReport:
    """A point-in-time snapshot of the deferred-candidate pool."""

    generated_at: str
    new_window_hours: int
    total: int = 0
    new_count: int = 0
    backfill_count: int = 0
    #: (YYYY-MM-DD, count) for the last ``DAY_HISTOGRAM_DAYS`` days, newest first.
    by_day: list[tuple[str, int]] = field(default_factory=list)
    #: (institution, count) for the busiest publishers, biggest first.
    by_institution: list[tuple[str, int]] = field(default_factory=list)
    #: highest-value candidates, ``score DESC, published_at DESC``.
    top: list[dict] = field(default_factory=list)
    #: EVERY candidate in the same order — the payload ``--json`` exports.
    candidates: list[dict] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"backlog: {self.total} candidates "
            f"(new={self.new_count} backfill={self.backfill_count}) "
            f"as of {self.generated_at}"
        )


def _row_to_candidate(row: sqlite3.Row) -> dict:
    """One candidate in the stable export shape (also the future backfill input)."""
    return {
        "blob_id": row["blob_id"],
        "title": row["title"],
        "institution": row["institution"],
        "published_at": row["published_at"],
        "score": int(row["local_priority_score"] or 0),
        "status": row["status"],
    }


def build_report(
    conn: sqlite3.Connection,
    now: datetime,
    *,
    new_window_hours: int,
    top_n: int = DEFAULT_TOP_N,
) -> BacklogReport:
    """Compute the backlog snapshot. Reads only; no writes, no clock, no network.

    Candidates are ordered exactly the way a fresh account would drain them
    (``score DESC, published_at DESC``), so ``top`` and the ``--json`` export are
    a literal work queue rather than a listing.
    """
    q = ",".join("?" for _ in CANDIDATE_STATUSES)
    rows = conn.execute(
        f"SELECT blob_id, title, institution, published_at, local_priority_score, "
        f"status FROM papers WHERE status IN ({q}) "
        "ORDER BY COALESCE(local_priority_score, 0) DESC, published_at DESC",
        CANDIDATE_STATUSES,
    ).fetchall()

    rep = BacklogReport(
        generated_at=now.astimezone(timezone.utc).isoformat(),
        new_window_hours=new_window_hours,
    )
    rep.candidates = [_row_to_candidate(r) for r in rows]
    rep.total = len(rep.candidates)
    rep.top = rep.candidates[:top_n]

    cutoff = allocator.new_cutoff_iso(now, new_window_hours)
    for c in rep.candidates:
        pub = c["published_at"]
        if pub and pub >= cutoff:
            rep.new_count += 1
        else:
            rep.backfill_count += 1

    # --- by published day, last N days (zero-count days are shown, so a gap in
    #     the feed is visible instead of silently absent) ---
    day_counts: dict[str, int] = {}
    for c in rep.candidates:
        d = (c["published_at"] or "")[:10]
        if d:
            day_counts[d] = day_counts.get(d, 0) + 1
    today = now.astimezone(timezone.utc).date()
    rep.by_day = [
        ((today - timedelta(days=i)).isoformat(),
         day_counts.get((today - timedelta(days=i)).isoformat(), 0))
        for i in range(DAY_HISTOGRAM_DAYS)
    ]

    # --- by institution, biggest first (name ascending breaks ties so the
    #     report is deterministic across runs) ---
    inst_counts: dict[str, int] = {}
    for c in rep.candidates:
        name = (c["institution"] or "").strip() or "(unknown)"
        inst_counts[name] = inst_counts.get(name, 0) + 1
    rep.by_institution = sorted(
        inst_counts.items(), key=lambda kv: (-kv[1], kv[0])
    )[:TOP_INSTITUTIONS]

    return rep


def render(rep: BacklogReport) -> str:
    """Human-readable report body (the ``marketdesk backlog`` stdout)."""
    lines: list[str] = [
        rep.summary(),
        f"  new window: {rep.new_window_hours}h "
        f"(new = still fresh, backfill = older history)",
        "",
        f"by published day (last {DAY_HISTOGRAM_DAYS}):",
    ]
    for day, n in rep.by_day:
        lines.append(f"  {day}  {n:>5}")
    lines += ["", f"by institution (top {TOP_INSTITUTIONS}):"]
    if not rep.by_institution:
        lines.append("  (none)")
    for name, n in rep.by_institution:
        lines.append(f"  {n:>5}  {name}")
    lines += ["", f"top {len(rep.top)} deferred candidates (score, then newest):"]
    if not rep.top:
        lines.append("  (none)")
    for c in rep.top:
        day = (c["published_at"] or "")[:10] or "??????????"
        inst = (c["institution"] or "?")[:18]
        title = (c["title"] or "(untitled)")[:80]
        lines.append(f"  {c['score']:>4}  {inst:<18}  {day}  {title}")
    return "\n".join(lines)


def export_json(rep: BacklogReport, path: str | Path) -> Path:
    """Write the FULL candidate list (not just the top N) for backfill tooling.

    The envelope carries the snapshot metadata so a consumer can tell how stale a
    dumped ledger is without re-deriving it.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": rep.generated_at,
        "new_window_hours": rep.new_window_hours,
        "total": rep.total,
        "new_count": rep.new_count,
        "backfill_count": rep.backfill_count,
        "candidates": rep.candidates,
    }
    p.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return p
