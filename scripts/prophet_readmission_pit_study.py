#!/usr/bin/env python3
"""Read-only, descriptive repeat-admission audit over an EXISTING Prophet artifact.

Never promote this historical selection into a gate.  Candidate features must
exist at the board decision clock; prior RESOLVED outcome may appear only in the
separately tagged hindsight diagnostic.  The original artifact has no per-date
proof of every stored prior mark's observation clock, so marks remain provisional
until regenerated/verified by the canonical producer.

Usage:
  python -m scripts.prophet_readmission_pit_study --artifact data/prophet_postmortem/summary.json
  python -m scripts.prophet_readmission_pit_study --format json

Nothing here writes a file, regrades a return, ranks, vetoes or sizes a stock.
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import random
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT = ROOT / "data/prophet_postmortem/summary.json"
SCHEMA = "prophet_postmortem/v1"
HEADWINDS = frozenset(("avoid", "trim"))
# This threshold is the standing postmortem definition, not fit from July.
STANDING_OPEN_DRAWDOWN_PCT = -8.0


def _number(x: Any) -> float | None:
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    value = float(x)
    return value if math.isfinite(value) else None


def _context(row: dict) -> tuple[str | None, str | None]:
    ctx = row.get("entry_context") or {}
    if not isinstance(ctx, dict):
        return (None, None)
    basket = ctx.get("sector_basket") or {}
    plan = ctx.get("entry_plan") or {}
    return (
        basket.get("reco") if isinstance(basket, dict) else None,
        plan.get("status") if isinstance(plan, dict) else None,
    )


def _hindsight_label(row: dict) -> bool:
    # Existing historical labels are read, NEVER reverse-engineered from a
    # future outcome and then promoted as an entry-time feature.
    return any(
        isinstance(label, dict) and label.get("label") == "re_admission"
        and isinstance(label.get("trigger"), dict)
        and label["trigger"].get("leg") == "prior_episode_loss"
        for label in (row.get("labels") or [])
    )


def _metrics(rows: list[dict]) -> dict:
    graded = [r for r in rows if _number(r.get("outcome_pct")) is not None]
    loser = [r for r in graded if r.get("cohort") == "loser"]
    winner = [r for r in graded if r.get("cohort") == "winner"]
    neutral = [r for r in graded if r.get("cohort") == "neutral"]
    returns = [float(r["outcome_pct"]) for r in graded]
    return {
        "n": len(rows),
        "n_with_return": len(graded),
        "n_missing_return": len(rows) - len(graded),
        "n_distinct_entry_dates": len({str(r["entry_date"]) for r in rows}),
        "losers": len(loser), "winners": len(winner),
        "neutral": len(neutral),
        "other_cohort": len(graded) - len(loser) - len(winner) - len(neutral),
        "mean_return_pct": round(sum(returns) / len(returns), 4)
        if returns else None,
        "total_return_pp": round(sum(returns), 4),
        # Symmetric, outcome-only diagnostic. Neutral return exposure is
        # explicitly separate, not silently considered 0 in a "veto net".
        "loser_return_pp": round(sum(float(r["outcome_pct"]) for r in loser), 4),
        "winner_return_pp": round(sum(float(r["outcome_pct"]) for r in winner), 4),
        "neutral_return_pp": round(sum(float(r["outcome_pct"]) for r in neutral), 4),
    }


def _mean(rows: list[dict]) -> float | None:
    values = [_number(r.get("outcome_pct")) for r in rows]
    values = [v for v in values if v is not None]
    return (sum(values) / len(values)) if values else None


def _date_block_interval(rows: list[dict], *, seed: int = 20261112,
                         draws: int = 2000) -> dict:
    """Exploratory repeat-vs-other mean difference, resampling board DATES."""
    by_date: dict[str, list[dict]] = {}
    for r in rows:
        by_date.setdefault(str(r.get("entry_date")), []).append(r)
    dates = sorted(by_date)
    if len(dates) < 2 or draws < 1:
        return {"interval": None, "reason": "insufficient_dates_or_draws"}
    rng = random.Random(seed)
    stats = []
    for _ in range(draws):
        sample = [r for d in (rng.choice(dates) for _ in dates)
                  for r in by_date[d]]
        repeated = [r for r in sample if isinstance(r.get("prior_episode"), dict)]
        other = [r for r in sample if r.get("prior_episode") is None]
        a, b = _mean(repeated), _mean(other)
        if a is not None and b is not None:
            stats.append(a - b)
    if not stats:
        return {"interval": None, "reason": "empty_comparison"}
    stats.sort()
    return {
        "method": "same-entry-date-cluster-bootstrap_exploratory",
        "draws_usable": len(stats), "seed": seed, "n_dates": len(dates),
        "difference_repeat_minus_other_pp": round(
            (_mean([r for r in rows if isinstance(r.get("prior_episode"), dict)])
             or 0) -
            (_mean([r for r in rows if r.get("prior_episode") is None]) or 0), 4),
        "interval_95_pp": [round(stats[int((len(stats) - 1) * q)], 3)
                           for q in (0.025, 0.975)],
        "promotion_grade": False,
    }


def study(doc: dict, *, seed: int = 20261112, draws: int = 2000) -> dict:
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise ValueError("requires an existing prophet_postmortem/v1 artifact")
    as_of = doc.get("as_of")
    if not isinstance(as_of, str) or len(as_of) != 10:
        raise ValueError("requires a canonical as_of date (YYYY-MM-DD)")
    try:
        if datetime.date.fromisoformat(as_of).isoformat() != as_of:
            raise ValueError
    except ValueError:
        raise ValueError("requires a canonical as_of date (YYYY-MM-DD)") from None
    source_rows = doc.get("episodes")
    if not isinstance(source_rows, list) or not source_rows:
        raise ValueError("requires non-empty artifact episodes")
    matured = [r for r in source_rows
               if isinstance(r, dict) and r.get("maturity") == "matured"
               and isinstance(r.get("entry_date"), str)]
    # Select the nearest previous BOARD appearance by chronology, never the
    # prior_episode.selected_by field: that pointer can be selected using a
    # future *resolved* loss and would leak hindsight into a PIT candidate.
    historical: dict[str, list[dict]] = {}
    for row in source_rows:
        if isinstance(row, dict) and isinstance(row.get("entry_date"), str):
            historical.setdefault(str(row.get("ticker")), []).append(row)
    for history in historical.values():
        history.sort(key=lambda row: row["entry_date"])
    repeated = [r for r in matured if isinstance(r.get("prior_episode"), dict)]
    other = [r for r in matured if r.get("prior_episode") is None]
    marked = [r for r in repeated
              if _number(r["prior_episode"].get("mark_at_readmit_pct")) is not None]
    underwater = [r for r in marked
                  if float(r["prior_episode"]["mark_at_readmit_pct"])
                  <= STANDING_OPEN_DRAWDOWN_PCT]
    sector = [r for r in repeated if _context(r)[0] in HEADWINDS]
    actionable = [r for r in repeated if _context(r)[1] == "buy_now"]
    sector_shift = []
    for r in sector:
        earlier = [
            row for row in historical.get(str(r.get("ticker")), [])
            if row["entry_date"] < r["entry_date"]
            and isinstance(row.get("board_exit_date"), str)
            and row["board_exit_date"] <= r["entry_date"]
        ]
        prev_row = earlier[-1] if earlier else None
        if prev_row and _context(prev_row)[0] is not None and (
            _context(prev_row)[0] not in HEADWINDS):
            sector_shift.append(r)
    groups = {
        "repeat_admission": _metrics(repeated),
        "no_recent_prior_recorded": _metrics(other),
        "repeat_with_known_prior_mark": _metrics(marked),
        "repeat_open_mark_le_minus8_pit_candidate": _metrics(underwater),
        "repeat_sector_avoid_or_trim_pit_candidate": _metrics(sector),
        "repeat_sector_shift_into_headwind_pit_candidate": _metrics(sector_shift),
        "repeat_entry_status_buy_now_not_execution_proof": _metrics(actionable),
        "prior_resolved_loss_hindsight_ONLY": _metrics(
            [r for r in repeated if _hindsight_label(r)]),
    }
    return {
        "schema": "prophet_readmission_pit_exploratory/v1",
        "source_as_of": as_of, "source_schema": SCHEMA,
        "authority": "descriptive_only_no_ranking_no_veto_no_trading",
        "board_appearance_not_executed_trade": True,
        "cohort_integrity": ("provided_not_adjudicated"
                             if doc.get("cohort_integrity") else
                             "MISSING_no_confirmatory_cross_era_claims"),
        "prior_mark_clock": "stored_mark_provisional_until_close_date_PIT_audit",
        "independent_out_of_sample": "NOT_AVAILABLE_in_this_historical_artifact",
        "definition": {
            "prior_window": "pre-existing artifact comparison; no invented prior",
            "open_drawdown_threshold_pct": STANDING_OPEN_DRAWDOWN_PCT,
            "headwind_sector_rec": sorted(HEADWINDS),
            "actionable_status_proxy": "buy_now_only_not_execution_proof",
        },
        "matured_population": _metrics(matured),
        "groups": groups,
        "date_block_exploratory": _date_block_interval(
            matured, seed=seed, draws=draws),
        "caveats": [
            "Uses matured rows only, but outcomes come from future bars.",
            "Only prior open MARK / sector state / entry status are entry-time candidates; prior resolved loss is HINDSIGHT.",
            "Stored marks have no per-bar timestamp proof in this artifact and are not promoted as PIT-verified.",
            "No board-definition-era controlled or independent forward-period study is available from this historical artifact.",
            "Multi-label groups overlap; percentages are NOT portfolio returns, backtests or trading rules.",
            "Missing sector/entry state is unknown, not clean; case windows overlap and share board dates.",
            "An entry status is not an actual transaction; no sizing, costs, stop or portfolio construction are simulated.",
        ],
    }


def render_markdown(result: dict) -> str:
    g = result["groups"]
    lines = [
        "# Prophet re-admission — exploratory PIT-readiness audit",
        "",
        f"Source snapshot: **{result['source_as_of']}** · **DESCRIPTIVE ONLY**; "
        "no executable veto, new score weight or trade.",
        "",
        "**DO NOT PROMOTE:** the source's previous-episode resolved losses "
        "are hindsight, and stored prior marks require observation-clock audit. "
        "Board appearances are not trades.",
        "",
        "| Condition | Episodes | Dates | Losers | Winners | Neutral | Mean return | All returns, pp |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for key, m in g.items():
        avg = "—" if m["mean_return_pct"] is None else f"{m['mean_return_pct']:+.2f}%"
        lines.append(
            f"| {key} | {m['n']} | {m['n_distinct_entry_dates']} "
            f"| {m['losers']} | {m['winners']} | {m['neutral']} "
            f"| {avg} | {m['total_return_pp']:+.2f} |")
    ci = result["date_block_exploratory"]
    lines += [
        "", "## Date-blocked descriptive contrast", "",
        (f"Repeat-minus-other average: **{ci['difference_repeat_minus_other_pp']:+.2f} pp**; "
         f"exploratory 95% date-cluster bootstrap "
         f"**[{ci['interval_95_pp'][0]:+.2f}, {ci['interval_95_pp'][1]:+.2f}] pp**, "
         f"{ci['n_dates']} dates, {ci['draws_usable']} usable draws. "
         "Not an out-of-sample result."
         if ci.get("interval_95_pp") else "Insufficient data for interval."),
        "", "## Missing proof and release disposition", "",
        *[f"- {c}" for c in result["caveats"]],
        "", "No promotion or live filter. Fresh PIT clocks, reliable original "
        "board-definition partitions, pre-registered thresholds and independent "
        "future cohorts are required before any policy proposal.",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--format", choices=("markdown", "json"),
                        default="markdown")
    parser.add_argument("--seed", type=int, default=20261112)
    parser.add_argument("--draws", type=int, default=2000)
    args = parser.parse_args(argv)
    result = study(json.loads(args.artifact.read_text(encoding="utf-8")),
                   seed=args.seed, draws=args.draws)
    if args.format == "json":
        print(json.dumps(result, sort_keys=True, indent=2))
    else:
        print(render_markdown(result), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
