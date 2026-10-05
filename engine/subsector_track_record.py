"""Falsifiable forward TRACK-RECORD for the Subsector Rotation read — measure, don't assert.

The rotation engine ranks 268 subsectors by ``emerging_score`` and labels each
emerging / fading / neutral. Those are CLAIMS about the future. This harness
records them daily and, once a horizon elapses, grades them against realized
forward returns — so the page can show whether the read has ANY edge, and so an
unproven signal is flagged rather than trusted.

Structure mirrors engine.hub_track_record (Pattern B) with one real change: a
subsector has no price series, so its forward return is the **equal-weight mean
forward return of its FROZEN member tickers**, SPY-relative. Members are frozen
at snapshot time. Every frozen member must have a finite covered return;
missing members leave the whole basket unscored. Historical source availability
and adjusted-price provenance remain separate qualification requirements.

  1. snapshot(subsectors, member_map, today) — append today's per-subsector
     {date, key, score, stage, lean, members} to data/subsector_rotation/
     snapshots.jsonl. Idempotent by (date, key), where `date` is the NYSE SESSION
     the read describes, never the calendar day of the run (_session_stamp) —
     the nightly fires seven nights a week against an EOD board, so a weekend
     stamp would slip a re-description of Friday past that idempotency.
  2. compute(today) — for each horizon (5/10/21/63d) mature the snapshots old
     enough AND price-covered, compute member-EW SPY-relative forward returns,
     then: by-stage hit-rate (do 'emerging' subsectors outperform & 'fading'
     underperform?) + cross-sectional emerging_score IC (Newey-West HAC t) + an
     ERROR LEDGER of recently falsified calls.
  3. "proven" only with enough matured obs AND a significant positive HAC-t AND a graded
     span covering >= 6 non-overlapping horizon-length windows (_MIN_INDEP_WINDOWS). The
     window floor is the one that bites: matured rows count a 268-name cross-section, so a
     single date clears the row bar while buying no independent evidence at all.

CONTEXT-ONLY · DEGRADE-NEVER-RAISE — no matured data ⇒ a valid 'accruing'
payload, never an exception. Nothing here sizes a position.
"""
from __future__ import annotations

import json
import logging
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from engine.ai_desk import _level_asof              # price helpers — do NOT reinvent
from engine.ai_desk_scorer import _close_at, _covers
from engine import validation as V
from lib import config, nyse_calendar

log = logging.getLogger(__name__)

SCHEMA = "subsector_rotation.track_record.v1"
_SNAP = ("data", "subsector_rotation", "snapshots.jsonl")
_HORIZONS = (5, 10, 21, 63)
_BENCH = "SPY"
_MIN_PRICED = 3              # a subsector needs ≥ this many priceable members to be scored
_MIN_PROVEN_N = 40          # matured cross-sectional ROWS before a horizon can be called "proven"
# Conservative observation-window floor, not statistical independence proof.
# Rows from one cross-section are not independent market episodes. Use the
# exact-session span AND the observed disjoint forward-window count, whichever
# is smaller. Six remains the existing minimum; no promotion threshold is lowered.
_MIN_INDEP_WINDOWS = 6.0
_TD_TO_CALENDAR = 7.0 / 5.0  # compatibility only; no longer used to count trading days → calendar days


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_date(value) -> date | None:
    """`value` as a plain date, or None when it cannot be read as one."""
    if isinstance(value, datetime):          # datetime subclasses date — check it first
        return value.date()
    if isinstance(value, date):
        return value
    try:
        ts = pd.Timestamp(value)
    except (TypeError, ValueError):
        return None
    return None if pd.isna(ts) else ts.date()


def _session_stamp(today: date | str | None) -> str:
    """Normalize a ledger stamp onto the DATA PLANE: the NYSE session it describes.

    Every date in this module is a claim about a tape, and a non-session date cannot
    describe one. The stamp arrives here from ``build_subsector_rotation`` as the
    Finviz snapshot's ``asof``, and daily.yml fires ~22:30 UTC SEVEN nights a week
    against an end-of-day board — so the Saturday and Sunday runs re-read Friday's
    unchanged numbers. Clock-stamped, each weekend night looked like a brand-new day
    to the (date,key) dedup below, appended a full ~269-row set, and handed
    ``compute()`` up to three copies of one Friday to grade as independent IC days.

    NORMALIZATION, NEVER REFUSAL. A weekend/holiday stamp maps to the prior session:
      * re-run case — Friday's rows are already there, so the existing (date,key)
        idempotency turns the weekend pass into a clean no-op;
      * recovery case — Friday's fetch FAILED and Saturday's run is the only record
        of that board, so the rows still log, dated to the session they describe.
    Refusing weekend calls outright would throw the second case away.

    An unparseable stamp passes through unchanged: this module is
    degrade-never-raise, and inventing a session for a string we cannot read would
    be a fabrication rather than a heal.
    """
    if not today:
        return nyse_calendar.session_date().isoformat()
    try:
        d = _as_date(today)
        if d is None:
            return today.isoformat() if hasattr(today, "isoformat") else str(today)
        if not nyse_calendar.is_session(d):
            d = nyse_calendar.last_session_on_or_before(d)
        return d.isoformat()
    except Exception as e:  # noqa: BLE001 — a calendar surprise degrades to the
        # old clock-stamp behaviour; it never raises into a never-raises caller.
        log.warning("session stamp normalization failed for %r (%s) — using it as-is",
                    today, e)
        return today.isoformat() if hasattr(today, "isoformat") else str(today)


def _path(root: Path) -> Path:
    return root.joinpath(*_SNAP)


def _load(root: Path) -> list[dict]:
    p = _path(root)
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except Exception:  # noqa: BLE001
            continue
    return out


# --------------------------------------------------------------------------- #
# snapshot accrual
# --------------------------------------------------------------------------- #
def _stage_lean(s: dict, emerging: set, fading: set) -> tuple[str, int]:
    k = s.get("key")
    if k in emerging:
        return "emerging", 1
    if k in fading:
        return "fading", -1
    return "neutral", 0


# Turn states that are directional CLAIMS, mapped onto the incumbent stage vocabulary so
# both reads are graded by exactly the same rule (hit = emerging up / fading down).
_V2_STAGE = {"turn_up": "emerging", "bottoming": "emerging",
             "turn_down": "fading", "topping": "fading"}


def _stage_v2(s: dict) -> str | None:
    """The turn engine's stage for this row, or None when the turn read is absent."""
    st = s.get("turn_state")
    if not st:
        return None
    return _V2_STAGE.get(st, "neutral")


def snapshot(payload: dict, member_map: dict | None = None,
             today: date | str | None = None, root: Path | None = None) -> int:
    """Append today's per-subsector reading. Idempotent by (date, key). Never raises."""
    try:
        root = Path(root) if root else config.ROOT
        member_map = member_map or {}
        # SESSION, not calendar day (see _session_stamp): a weekend re-read of
        # Friday's EOD board must land on Friday, where (date,key) dedup can see it.
        today_str = _session_stamp(today)
        existing = {f"{r.get('date')}|{r.get('key')}" for r in _load(root)
                    if isinstance(r, dict)}
        # Observer capture time is NOT the session label or source-publication time.
        # Keep old rows untouched; no historical availability is backfilled.
        recorded_at_utc = _now_iso()
        emerging = set((payload.get("highlights") or {}).get("emerging") or [])
        fading = set((payload.get("highlights") or {}).get("fading") or [])
        new = []
        for s in payload.get("subsectors", []):
            k = s.get("key")
            if not k or f"{today_str}|{k}" in existing:
                continue
            stage, lean = _stage_lean(s, emerging, fading)
            members = [str(t).strip().upper() for t in (member_map.get(k) or []) if str(t).strip()]
            new.append({"date": today_str, "key": k, "name": s.get("name"),
                        "recorded_at_utc": recorded_at_utc,
                        "recording_time_basis": "observer_wall_clock",
                        "theme": s.get("theme"), "score": s.get("emerging_score"),
                        "rs_mom": s.get("rs_mom"), "accel": s.get("accel"),
                        "quadrant": s.get("quadrant"), "stage": stage, "lean": lean,
                        # HEAD-TO-HEAD (engine/subsector_turn.py): the turn engine's own
                        # rank and stage, logged beside the incumbent so the ledger — not an
                        # argument about which arithmetic is nicer — decides which read is
                        # better. Absent on rows logged before the turn engine shipped;
                        # those rows simply don't accrue to the v2 columns.
                        "score_v2": s.get("rank_score_v2"),
                        "stage_v2": _stage_v2(s),
                        "turn_state": s.get("turn_state"),
                        "members": members})
            existing.add(f"{today_str}|{k}")
        if not new:
            return 0
        p = _path(root)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a") as fh:
            for r in new:
                fh.write(json.dumps(r, separators=(",", ":")) + "\n")
        return len(new)
    except Exception as e:  # noqa: BLE001
        log.warning("subsector track snapshot failed: %s", e)
        return 0


# --------------------------------------------------------------------------- #
# maturation + member-EW forward returns
# --------------------------------------------------------------------------- #
def _session_horizon_end(start: date | str, horizon_sessions: int) -> str:
    """NYSE session exactly horizon_sessions after the observation session.

    The track-record contract describes 5/10/21/63-session outcomes. Calendar-day
    arithmetic matures Friday observations too early across weekends/holidays and
    grades a different economic horizon. Legacy non-session stamps are normalized
    to the last real session before stepping forward.
    """
    if isinstance(horizon_sessions, bool) or not isinstance(horizon_sessions, int) or horizon_sessions <= 0:
        raise ValueError("horizon_sessions must be a positive integer")
    d = _as_date(start)
    if d is None:
        raise ValueError(f"unparseable session: {start!r}")
    d = nyse_calendar.last_session_on_or_before(d)
    remaining = horizon_sessions
    while remaining:
        d += timedelta(days=1)
        if nyse_calendar.is_session(d):
            remaining -= 1
    return d.isoformat()

def _finite_number(value):
    """Finite numeric evidence, never booleans or numeric-looking strings."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except (ValueError, TypeError, OverflowError):
        return False

def _ic_by_date(rows: list, fields: tuple[str, ...]) -> tuple[dict, int, int]:
    """One shared finite-row AND nonconstant-date population for all fields."""
    grouped = {}
    for row in rows:
        if (isinstance(row, dict) and isinstance(row.get('date'), str)
                and _finite_number(row.get('fwd'))
                and all(_finite_number(row.get(field)) for field in fields)):
            grouped.setdefault(row['date'], []).append(row)
    counts = sum(len(day) for day in grouped.values())
    by_date, used = {}, 0
    for stamp, day in sorted(grouped.items()):
        outcomes = [row['fwd'] for row in day]
        if len(day) < 10 or len(set(outcomes)) < 2:
            continue
        values = [[row[field] for row in day] for field in fields]
        if any(len(set(xs)) < 2 for xs in values):
            continue
        correlations = [V.rank_ic(xs, outcomes) for xs in values]
        if not all(_finite_number(value) for value in correlations):
            continue
        by_date[stamp] = correlations
        used += len(day)
    return by_date, counts, used

def _summarize_ic(by_date: dict, horizon_d: int, column: int) -> dict:
    values = [row[column] for row in by_date.values()]
    summary = (V.ic_summary(values, periods_per_year=2 * horizon_d)
               if len(values) >= 6 else {'n_days': len(values)})
    # Undefined statistics must serialize as unavailable, not JavaScript NaN.
    summary = {key: (None if isinstance(value, float) and not math.isfinite(value)
                     else value) for key, value in summary.items()}
    summary.update(_window_span(list(by_date), horizon_d))
    summary['ic_dates'] = list(by_date)
    return summary

def _paired_daily_ic(rows: list, horizon_d: int) -> dict:
    """Paired comparisons never average different finite-IC date sets."""
    by_date, candidate_rows, used_rows = _ic_by_date(rows, ('score', 'score_v2'))
    baseline = _summarize_ic(by_date, horizon_d, 0)
    challenger = _summarize_ic(by_date, horizon_d, 1)
    return {
        'n_paired': candidate_rows,
        'n_scored_paired': used_rows,
        'n_paired_ic_dates': len(by_date),
        'paired_ic_dates': list(by_date),
        'score_ic': baseline.get('mean_ic'),
        'score_ic_v2': challenger.get('mean_ic'),
        'score_ic_t_hac': baseline.get('t_hac'),
        'score_ic_t_hac_v2': challenger.get('t_hac'),
    }


def _member_ret(ticker: str, root: Path, start: str, end: str) -> float | None:
    # Exact session prices: do not carry an earlier close into this horizon.
    p0 = _level_asof(ticker, root, start, max_stale_days=0)
    p1 = _close_at(ticker, root, end, max_stale_days=0)
    if not _finite_number(p0) or not _finite_number(p1) or p0 <= 0 or p1 < 0:
        return None
    value = p1 / p0 - 1.0
    return float(value) if _finite_number(value) else None


def _fwd_basket(members: list, root: Path, start: str, horizon_d: int,
                *, diagnostic: dict | None = None) -> float | None:
    """Complete frozen basket, with an optional first-failing-gate diagnostic."""
    def finish(status, value=None):
        if diagnostic is not None:
            diagnostic['status'] = status
        return value
    try:
        if not isinstance(members, list) or len(members) < _MIN_PRICED:
            return finish('invalid_population')
        if any(not isinstance(t, str) or not t or t != t.strip().upper() for t in members):
            return finish('invalid_population')
        if len(set(members)) != len(members):
            return finish('invalid_population')
        end = _session_horizon_end(start, horizon_d)
        rets = []
        for ticker in members:
            if not _covers(ticker, root, end):
                return finish('member_unavailable')
            value = _member_ret(ticker, root, start, end)
            if not _finite_number(value) or value < -1:
                return finish('member_unavailable')
            rets.append(value)
        if not _covers(_BENCH, root, end):
            return finish('benchmark_unavailable')
        benchmark = _member_ret(_BENCH, root, start, end)
        if not _finite_number(benchmark) or benchmark < -1:
            return finish('benchmark_unavailable')
        result = math.fsum(r / len(members) for r in rets) - benchmark
        if not _finite_number(result):
            return finish('nonfinite_outcome')
        return finish('measured', float(result))
    except Exception:  # noqa: BLE001 - preserve the public no-raise contract
        return finish('pricing_error')

def _matured(rows: list, root: Path, horizon_d: int, today: date,
             *, coverage: dict | None = None) -> list[dict]:
    """Measure complete baskets and account for every parsed input row once.

    Counts are not a correction for missing-not-at-random selection. Reasons name
    the first failed gate, not every fault a row might contain. Pending rows do
    not read prices; invalid rows are not invented as due observations.
    """
    statuses = ('measured', 'pending', 'invalid_record', 'invalid_population',
                'benchmark_unavailable', 'member_unavailable', 'nonfinite_outcome',
                'pricing_error', 'unavailable_unclassified')
    counts = dict.fromkeys(statuses, 0)
    stages = {s: dict.fromkeys(statuses, 0)
              for s in ('emerging', 'fading', 'neutral', 'unknown')}
    out = []
    for row in rows:
        stage = row.get('stage') if isinstance(row, dict) else None
        stage = stage if isinstance(stage, str) and stage in stages else 'unknown'
        status = 'invalid_record'
        try:
            if not isinstance(row, dict):
                raise ValueError('invalid record')
            key = row.get('key')
            if not isinstance(key, str) or not key.strip() or key != key.strip():
                raise ValueError('invalid group identity')
            if any(row.get(f) is not None and not isinstance(row.get(f), str)
                   for f in ('stage', 'stage_v2')):
                raise ValueError('invalid stage')
            end = _session_horizon_end(row['date'], horizon_d)
        except Exception:  # noqa: BLE001 - invalid data has its own denominator
            end = None
        if end is not None:
            if today < date.fromisoformat(end):
                status = 'pending'
            else:
                try:
                    if not _covers(_BENCH, root, end):
                        status = 'benchmark_unavailable'
                    else:
                        diagnostic = {}
                        fwd = _fwd_basket(row.get('members'), root, row['date'],
                                          horizon_d, diagnostic=diagnostic)
                        if _finite_number(fwd):
                            out.append({**row, 'fwd': fwd})
                            status = 'measured'
                        else:
                            status = diagnostic.get('status', 'unavailable_unclassified')
                            if status not in statuses or status in ('measured', 'pending', 'invalid_record'):
                                status = 'unavailable_unclassified'
                except Exception:  # noqa: BLE001
                    status = 'pricing_error'
        counts[status] += 1
        stages[stage][status] += 1
    if coverage is not None:
        def totals(c):
            n = sum(c.values())
            due = n - c['pending'] - c['invalid_record']
            return {'input_rows': n, 'due_rows': due, 'measured_rows': c['measured'],
                    'unavailable_due_rows': due - c['measured'],
                    'pending_rows': c['pending'], 'invalid_rows': c['invalid_record'],
                    'measured_fraction_of_due': c['measured'] / due if due else None,
                    'status_counts': c}
        coverage.clear()
        coverage.update(totals(counts))
        coverage.update({'population_basis': 'parsed_snapshot_rows',
                         'reason_policy': 'first_failing_gate',
                         'selection_bias_corrected': False,
                         'by_stage': {s: totals(c) for s, c in stages.items()}})
    return out

def _window_span(ic_dates: list, horizon_d: int) -> dict:
    """Session span capped by observed nonoverlapping forward windows.

    This is a conservative sample-size guard, not proof of statistical independence.
    Empty years between two observed dates do not create additional observations.
    """
    empty = {"ic_first_date": None, "ic_last_date": None, "ic_span_days": 0,
             "ic_span_sessions": 0, "span_windows": 0.0,
             "nonoverlapping_ic_observations": 0, "indep_windows": 0.0}
    if not ic_dates:
        return empty
    try:
        if isinstance(horizon_d, bool) or not isinstance(horizon_d, int) or horizon_d <= 0:
            return empty
        parsed = [_as_date(d) for d in ic_dates]
        if any(d is None for d in parsed):
            return empty
        dates = sorted({nyse_calendar.last_session_on_or_before(d) for d in parsed})
        first, last = dates[0], dates[-1]
        span_sessions = max(0, len(nyse_calendar.sessions_between(first, last)) - 1)
        count, prior_end = 0, None
        for stamp in dates:
            if prior_end is None or stamp >= prior_end:
                count += 1
                prior_end = date.fromisoformat(_session_horizon_end(stamp, horizon_d))
        windows = span_sessions / horizon_d
        return {"ic_first_date": first.isoformat(), "ic_last_date": last.isoformat(),
                "ic_span_days": (last-first).days, "ic_span_sessions": span_sessions,
                "span_windows": windows, "nonoverlapping_ic_observations": count,
                "indep_windows": min(windows, float(count))}
    except Exception:  # noqa: BLE001
        return empty

def _iid_t(ic: dict) -> float | None:
    """Plain iid t of the per-date IC series — mean / (sd / sqrt(n)). The NO-correction
    baseline a HAC t is supposed to sit below on an overlapping-window series."""
    mean, sd, n = ic.get("mean_ic"), ic.get("ic_vol"), ic.get("n")
    try:
        if mean is None or sd is None or not n or int(n) < 2 or float(sd) <= 0:
            return None
        return float(mean) / (float(sd) / math.sqrt(float(n)))
    except (TypeError, ValueError):  # noqa: BLE001
        return None


def _gate_t(ic: dict, horizon_d: int) -> tuple[float | None, bool]:
    """(t the promotion gate is allowed to read, hac_was_anticonservative).

    Newey-West is a CORRECTION: on a positively-overlapping series it widens the standard
    error and pushes |t| DOWN from the iid baseline. When it does the opposite — t_hac
    exceeds |t_iid|, which happens when the Bartlett long-run variance lands below gamma0/n
    on a short series — the "corrected" t is anticonservative BY CONSTRUCTION and is not
    evidence of anything. Measured 2026-08-03 on this very ledger: 1.392>1.208 @5d,
    4.638>3.600 @10d, 4.850>3.179 @21d, all three horizons inverted.

    The gate then reads the iid t (the weaker of the two). This can only ever WITHDRAW a
    promotion, never grant one, and the substitution is announced on the Actions log
    whenever it touches a t that would otherwise have cleared the bar.
    """
    t_hac = ic.get("t_hac")
    t_iid = _iid_t(ic)
    if t_hac is None:
        return (t_iid, False)
    if t_iid is None:
        return (float(t_hac), False)
    if float(t_hac) > abs(t_iid):
        if float(t_hac) >= 2.0:
            # Bare print at line start + flush — a logger prefix makes GitHub drop the
            # annotation silently (CLAUDE.md, tests/test_gh_annotation_line_start.py).
            print(f"::warning title=subsector_track_record::hac anticonservative at {horizon_d}d "
                  f"— t_hac={float(t_hac):.3f} exceeds |t_iid|={abs(t_iid):.3f} on n="
                  f"{ic.get('n')} overlapping IC-days (effective lag "
                  f"{ic.get('hac_lags')} of {ic.get('hac_lags_requested')} requested); "
                  f"promotion gate reads the iid t instead", flush=True)
        return (abs(t_iid) if float(t_hac) > 0 else -abs(t_iid), True)
    return (float(t_hac), False)


def _daily_ic(rows: list, horizon_d: int, field: str = 'score') -> dict:
    by_date, _, _ = _ic_by_date(rows, (field,))
    return _summarize_ic(by_date, horizon_d, 0)


def _hit_bounds(hits, measured, due) -> dict:
    """Logical limits over logged due calls, not a statistical confidence interval.

    Unknown binary outcomes may all miss or all hit. Do not impute them, infer
    returns, or interpret the interval as a probability for a future trade.
    """
    result = {'method': 'unknown_binary_outcomes_extremes',
              'population_basis': 'parsed_due_directional_calls',
              'status': 'UNKNOWN', 'lower': None, 'upper': None,
              'observed_hits': None, 'measured_calls': None, 'due_calls': None,
              'unmeasured_calls': None, 'is_confidence_interval': False,
              'selection_bias_corrected': False}
    if any(isinstance(v, bool) or not isinstance(v, int) or v < 0
           for v in (hits, measured, due)) or not hits <= measured <= due:
        return result
    unknown = due - measured
    result.update(observed_hits=hits, measured_calls=measured,
                  due_calls=due, unmeasured_calls=unknown)
    if not due:
        result['status'] = 'EMPTY'
        return result
    result.update(status='BOUNDED' if unknown else 'COMPLETE',
                  lower=hits / due, upper=(hits + unknown) / due)
    return result


def _stage_hit_bounds(stats: dict, coverage: dict) -> dict:
    """Bind exact hit counts to the same stage's disclosed due denominator."""
    result = {}
    by_stage = coverage.get('by_stage', {}) if isinstance(coverage, dict) else {}
    for stage in ('emerging', 'fading'):
        unavailable = _hit_bounds(None, None, None)
        c = by_stage.get(stage) if isinstance(by_stage, dict) else None
        s = stats.get(stage, {'n': 0, 'hit_count': 0}) if isinstance(stats, dict) else None
        if not isinstance(c, dict) or not isinstance(s, dict):
            result[stage] = unavailable
            continue
        measured, due, unknown = (c.get(k) for k in
                                 ('measured_rows', 'due_rows', 'unavailable_due_rows'))
        if (any(isinstance(v, bool) or not isinstance(v, int) or v < 0
                for v in (measured, due, unknown))
                or isinstance(s.get('n'), bool) or not isinstance(s.get('n'), int)
                or measured + unknown != due or s.get('n') != measured):
            result[stage] = unavailable
            continue
        result[stage] = _hit_bounds(s.get('hit_count'), measured, due)
    return result


def _by_stage(rows: list, field: str = "stage") -> dict:
    out: dict[str, dict] = {}
    by: dict[str, list] = {}
    for r in rows:
        if r.get(field) is None:
            continue
        by.setdefault(r.get(field) or "?", []).append(r["fwd"])
    for st, fwds in by.items():
        n = len(fwds)
        mean = sum(fwds) / n if n else 0.0
        hits = (sum(1 for f in fwds if f > 0) if st == "emerging" else
                sum(1 for f in fwds if f < 0) if st == "fading" else None)
        hit = hits / n if hits is not None and n else None
        out[st] = {"n": n, "hit_count": hits, "mean_fwd_rel": round(mean, 4),
                   "hit_rate": round(hit, 3) if hit is not None else None}
    return out


def _recent_misses(rows: list, horizon_d: int, k: int = 8) -> list[dict]:
    """ERROR LEDGER: directional calls that were FALSIFIED — emerging that underperformed,
    fading that outperformed — most recent first. The system's own logged mistakes."""
    miss = []
    for r in rows:
        st, fwd = r.get("stage"), r.get("fwd")
        if st == "emerging" and fwd < 0:
            miss.append(r)
        elif st == "fading" and fwd > 0:
            miss.append(r)
    miss.sort(key=lambda r: (r["date"], abs(r["fwd"])), reverse=True)
    return [{"date": r["date"], "key": r["key"], "name": r.get("name"),
             "theme": r.get("theme"), "stage": r["stage"], "fwd_rel": round(r["fwd"], 4),
             "horizon_d": horizon_d} for r in miss[:k]]


def _head_to_head(out_h: dict) -> dict:
    """Paired incumbent-vs-turn scoreboard by horizon; deliberately no global winner.

    Each horizon compares only rows carrying both score fields. The legacy implementation
    displayed incumbent IC on all incumbent rows beside v2 IC on a smaller subset and then
    overwrote a global leader while iterating horizons. That was neither paired nor
    order-invariant. Keep the legacy key for consumers, but leave it null.
    """
    rows = {}
    for h, e in out_h.items():
        v2 = e.get("v2") or {}
        pair = e.get("comparison") or {}
        a, b = pair.get("score_ic"), pair.get("score_ic_v2")
        rows[h] = {
            "n": e.get("n_matured"),
            "n_v2": v2.get("n_matured"),
            "n_paired": pair.get("n_paired"),
            "n_scored_paired": pair.get("n_scored_paired"),
            "n_paired_ic_dates": pair.get("n_paired_ic_dates"),
            "paired_ic_dates": pair.get("paired_ic_dates"),
            "ic": a,
            "ic_v2": b,
            "gap": (round(b - a, 4) if (a is not None and b is not None) else None),
            "t_hac": pair.get("score_ic_t_hac"),
            "t_hac_v2": pair.get("score_ic_t_hac_v2"),
        }
    return {
        "by_horizon": rows,
        "leader": None,
        "note": ("Paired same-row, same-valid-date ICs are reported separately by horizon. No global winner "
                 "is declared from unequal populations or horizon iteration order."),
        "note_zh": ("各周期仅报告同一批成对样本的信息系数；不再根据不等样本或周期遍历顺序"
                    "给出全局胜者。"),
    }

# --------------------------------------------------------------------------- #
# FRONT-FACING NOTE — one table, one guard
#
# The note is the only sentence from this ledger a reader actually sees (it renders through
# scripts/build_subsector_rotation.py -> site/marketdata/subsector_rotation.json ->
# templates/subsector_rotation.js -> sector_central.html). Exactly ONE of these strings
# claims significance, and it is reachable from exactly one verdict.
#
# The strings live in a table rather than inline in compute() so `note_violation` can audit a
# STORED payload against them — the claim gate (scripts/check_validated_claims.py) cannot see
# this sentence at all: it never uses the word "validated", and it reaches the page through a
# runtime fetch of a 758 KB single-line JSON that no SCAN_GLOB covers (and whose
# `"verdict": "validated"` field is a _STRUCTURAL skip by design). The 2026-08-03 audit found
# the significance claim shipped for weeks with nothing able to fail because of it.
# --------------------------------------------------------------------------- #
_NOTES: dict[str, tuple[str, str]] = {
    "accruing": (
        "No complete-basket outcomes are measured yet; observations may be pending "
        "or unavailable. The forward edge is unmeasured. Context-only.",
        "尚无完整组合结果可供测量；记录可能待到期或数据不可用。前瞻优势未经测量，仅供参考。"),
    "measuring": (
        "Accruing forward observations; no horizon clears the Newey-West significance "
        "bar yet. Early numbers are provisional, context-only.",
        "正在累积前瞻观测；尚无周期通过 Newey-West 显著性检验。早期数据为暂定，仅供参考。"),
    # THE ONLY significance claim in this module. Reachable only when honest_verdict()
    # returns "validated" off the payload's own disclosed numbers.
    "validated": (
        "Emerging-score IC is significant at the {h}d horizon (measured). "
        "Context-only — informs the read, never sizes.",
        "升温评分的信息系数在 {h} 天周期上显著（已测得）。仅供参考——辅助研判，从不用于仓位。"),
}


def _note_for(verdict: str, lead_time: int | None) -> tuple[str, str]:
    en, zh = _NOTES.get(verdict) or _NOTES["accruing"]
    return en.format(h=lead_time), zh.format(h=lead_time)


def honest_verdict(payload: dict) -> str:
    """Re-derive the verdict from a payload's OWN disclosed per-horizon numbers.

    Pure function of the artifact — it reads no prices and no snapshots — so a STORED
    track-record payload can be audited long after the run that produced it, by a test or by
    the builder that is about to publish it.
    """
    hz = payload.get("horizons") or {}
    if not any((e.get("n_matured") or 0) > 0 for e in hz.values()):
        return "accruing"
    for e in hz.values():
        t = e.get("score_ic_t_gate")
        if ((e.get("n_matured") or 0) >= _MIN_PROVEN_N
                and float(e.get("indep_windows") or 0.0) >= _MIN_INDEP_WINDOWS
                and t is not None and float(t) >= 2.0
                and (e.get("score_ic") or 0) > 0):
            return "validated"
    return "measuring"


def note_violation(payload: dict) -> str | None:
    """None when a track-record payload's front-facing note is backed by its own numbers;
    a one-line description of the violation otherwise.

    Two independent things must hold, and BOTH are checked against the payload alone:
      1. the stated verdict is the one honest_verdict() derives from the disclosed numbers;
      2. the note pair is verbatim the _NOTES entry for that verdict.

    (2) is what actually pins the significance sentence: it exists in exactly one table row,
    so a note carrying it can only pass while the verdict is "validated" — and (1) will not
    let the verdict be "validated" unless a horizon really cleared both floors. Wording drift
    is caught too, which matters because the honest 'measuring' copy legitimately contains
    "significance"/"显著" inside a NEGATION ("no horizon clears the ... bar yet"); a token
    grep would either miss the claim or flag the disclaimer.
    """
    stated = payload.get("verdict")
    honest = honest_verdict(payload)
    if stated != honest:
        hz = payload.get("horizons") or {}
        detail = "; ".join(
            f"{h}d: n={e.get('n_matured')}, ic={e.get('score_ic')}, "
            f"t_gate={e.get('score_ic_t_gate')}, indep_windows={e.get('indep_windows')}"
            for h, e in sorted(hz.items(), key=lambda kv: int(kv[0])))
        return (f"verdict={stated!r} but the payload's own numbers support {honest!r} "
                f"(floors: n>={_MIN_PROVEN_N}, indep_windows>={_MIN_INDEP_WINDOWS}, "
                f"t>=2.0, ic>0) — {detail}")
    if payload.get("compute_error"):
        return None                    # degrade-safe payload: claims nothing, copy is the error
    want_en, want_zh = _note_for(honest, payload.get("lead_time_d"))
    if (payload.get("note") or "") != want_en or (payload.get("note_zh") or "") != want_zh:
        return (f"note copy does not match the canonical {honest!r} note "
                f"(lead_time_d={payload.get('lead_time_d')!r}) — got "
                f"{(payload.get('note') or '')[:90]!r}")
    return None


def withdraw_unbacked_note(payload: dict) -> str | None:
    """De-escalate a payload IN PLACE to the note its own numbers support.

    Returns the violation string when anything was withdrawn (the caller announces it), None
    when the note was already backed. DE-ESCALATION ONLY: honest_verdict never returns
    "validated" unless both floors cleared, so this can strip a claim and never mint one.
    """
    viol = note_violation(payload)
    if viol is None:
        return None
    payload["verdict"] = honest_verdict(payload)
    if payload["verdict"] != "validated":
        payload["lead_time_d"] = None
        payload["peak_score_ic"] = None
    payload["note"], payload["note_zh"] = _note_for(payload["verdict"],
                                                    payload.get("lead_time_d"))
    payload["note_withdrawn"] = viol
    return viol


def compute(today: date | str | None = None, root: Path | None = None,
            horizons=_HORIZONS) -> dict:
    """Grade every matured snapshot across all horizons. Never raises; degrades to 'accruing'."""
    try:
        root = Path(root) if root else config.ROOT
        # The maturity clock runs on SESSIONS (see _session_stamp). There is no
        # session between Friday's close and a Sunday run, so this only stops
        # phantom weekend aging; `as_of` becomes the session date (TS-R2 display
        # semantics). An unreadable stamp still raises here into the degrade-safe
        # payload below, exactly as pd.Timestamp() used to.
        today_dt = date.fromisoformat(_session_stamp(today))
        rows = _load(root)
        n_days = len({r.get("date") for r in rows
                      if isinstance(r, dict) and isinstance(r.get("date"), str)})
        out_h: dict[str, dict] = {}
        peak_ic, lead_time = None, None
        misses: list[dict] = []
        for h in horizons:
            coverage = {}
            mat = _matured(rows, root, h, today_dt, coverage=coverage)
            ic = _daily_ic(mat, h)
            # HEAD-TO-HEAD: the turn engine's rank graded on the SAME matured rows, same
            # rule, same HAC lag. Only rows carrying score_v2 accrue, so the two columns can
            # legitimately disagree on n — that is disclosed, not averaged away.
            mat_v2 = [r for r in mat if r.get("score_v2") is not None]
            ic_v2 = _daily_ic(mat_v2, h, field="score_v2")
            # Head-to-head claims must use an identical population. Keep standalone
            # incumbent/v2 diagnostics above; both fields share valid rows AND IC dates.
            pair = _paired_daily_ic(mat, h)
            t_gate, anticon = _gate_t(ic, h)
            stage_stats = _by_stage(mat)
            out_h[str(h)] = {
                "n_matured": len(mat),
                "coverage": coverage,
                "score_ic": ic.get("mean_ic"),
                "score_ic_t_hac": ic.get("t_hac"),
                # what the promotion gate actually reads, and why it may differ from t_hac
                "score_ic_t_gate": (round(t_gate, 3) if t_gate is not None else None),
                "score_ic_t_iid": (round(_iid_t(ic), 3) if _iid_t(ic) is not None else None),
                "hac_anticonservative": anticon,
                # independent-window disclosure — the honest n of a time-series gate
                "ic_span_days": ic.get("ic_span_days"),
                "ic_span_sessions": ic.get("ic_span_sessions"),
                "indep_windows": ic.get("indep_windows"),
                "indep_windows_required": _MIN_INDEP_WINDOWS,
                "score_ic_detail": ic,
                "by_stage": stage_stats,
                "logged_call_hit_bounds": _stage_hit_bounds(stage_stats, coverage),
                "v2": {
                    "n_matured": len(mat_v2),
                    "score_ic": ic_v2.get("mean_ic"),
                    "score_ic_t_hac": ic_v2.get("t_hac"),
                    "by_stage": _by_stage(mat_v2, field="stage_v2"),
                },
                "comparison": pair,
            }
            if h == 21:                                  # error ledger from the 21d window
                misses = _recent_misses(mat, h)

        proven = {}
        for h, e in out_h.items():
            t = e.get("score_ic_t_gate")
            proven[h] = bool(e["n_matured"] >= _MIN_PROVEN_N
                             # the honest n: independent windows, not cross-sectional rows
                             and (e.get("indep_windows") or 0.0) >= _MIN_INDEP_WINDOWS
                             and t is not None and t >= 2.0
                             and (e.get("score_ic") or 0) > 0)
        # lead_time is picked FROM the proven set, so the headline horizon can never name one
        # the gate refused (it used to be selected on a bare t>=2.0, ignoring both floors).
        for h, e in out_h.items():
            mic = e.get("score_ic")
            if proven.get(h) and mic is not None and (peak_ic is None or mic > peak_ic):
                peak_ic, lead_time = mic, int(h)
        any_matured = any(e["n_matured"] > 0 for e in out_h.values())
        verdict = ("accruing" if not any_matured
                   else "validated" if any(proven.values())
                   else "measuring")
        note, note_zh = _note_for(verdict, lead_time)
        return {
            "schema": SCHEMA, "as_of": today_dt.isoformat(), "generated_at": _now_iso(),
            "is_context_only": True,
            "evaluation_basis": "closed_session_information_content",
            "outcome_coverage_policy": "all_frozen_members_required",
            "price_endpoint_policy": "exact_session_close_no_asof_carry",
            "comparison_population_policy": "same_rows_same_valid_ic_dates",
            "price_provenance_qualification": "NOT_ESTABLISHED_BY_THIS_EVALUATOR", "n_snapshots": len(rows), "n_days": n_days,
            "horizons": out_h, "lead_time_d": lead_time, "peak_score_ic": peak_ic,
            "proven": proven, "any_matured": any_matured, "verdict": verdict,
            "note": note, "note_zh": note_zh,
            "recent_misses": misses,
            "head_to_head": _head_to_head(out_h),
            "disclaimer": ("An accountable scorecard of the rotation read's own calls — "
                           "emerging_score rank and emerging/fading labels graded against "
                           "realized member-equal-weight SPY-relative forward returns. A horizon "
                           "stays 'measuring' until it clears a Newey-West significance bar AND "
                           "its graded days span at least six non-overlapping windows of that "
                           "length — many readings of one stretch of market are one reading, not "
                           "many. Every stored member requires exact-session prices or the whole "
                           "outcome is excluded. Historical availability and price provenance "
                           "remain unqualified. Exclusions can bias results. Nothing here sizes a position."),
            "disclaimer_zh": ("对轮动研判自身研判的可问责记分卡——升温评分排名与升温/退潮标签，"
                              "以成分股等权、相对 SPY 的实际前瞻收益进行评分。某周期须同时通过 "
                              "Newey-West 显著性检验，且其评分日跨度覆盖至少六段互不重叠的同长度窗口，"
                              "才会脱离「测量中」——同一段行情读十遍仍只是一遍。成分股按时间点冻结，"
                              "每个成分均须具备对应交易日价格，否则整个结果不计入。排除可能造成偏差，历史可知时间与价格来源仍待验证。此处任何内容都不用于确定仓位。"),
        }
    except Exception as e:  # noqa: BLE001
        log.warning("subsector track compute failed: %s", e)
        return {"schema": SCHEMA, "as_of": _session_stamp(today), "generated_at": _now_iso(),
                "is_context_only": True,
                "evaluation_basis": "closed_session_information_content",
                "outcome_coverage_policy": "all_frozen_members_required",
                "price_endpoint_policy": "exact_session_close_no_asof_carry",
                "comparison_population_policy": "same_rows_same_valid_ic_dates",
                "price_provenance_qualification": "NOT_ESTABLISHED_BY_THIS_EVALUATOR", "n_snapshots": 0, "n_days": 0, "horizons": {},
                "lead_time_d": None, "peak_score_ic": None, "proven": {}, "any_matured": False,
                "verdict": "accruing", "note": f"compute error ({e}) — accruing, degrade-safe.",
                "note_zh": f"计算出错（{e}）——累积中，降级安全。",
                # names the degradation so note_violation exempts the copy check rather than
                # alarming on it — a payload that claims nothing cannot overclaim
                "compute_error": str(e),
                "recent_misses": []}
