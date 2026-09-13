"""Shared merge for the US breadth wide close caches — freshest column wins.

WHY THIS EXISTS (2026-08-06, generalising
research/ADJUDICATION_20260803_UNIVERSE_SIDE_STORE_FRESHNESS.md §4 chip (3)).

``data/{breadth,smallcap_breadth,midcap_breadth,russell_breadth}/_closes_cache.parquet``
are UNION-FOREVER archives by design (survivorship-honest; #4643 R4 — never prune).
A name that LEAVES an index keeps its column in that tier's cache, frozen on its exit
date, while the tier it JOINED carries a live column for the same ticker.

Every consumer merged the tiers with the same idiom — concat in a fixed tier order,
then ``~columns.duplicated()`` / ``setdefault`` — which keeps the FIRST occurrence.
For an index migrant that is the DEAD column, and the LIVE one, sitting in the very
same concat, is discarded. Measured on the 2026-07-31 caches:

  * order (breadth, smallcap, midcap)  -> 6 dead-picked: CAG CPB POOL SANM SMTC VIAV
  * order (breadth, midcap, smallcap)  -> 7 dead-picked: BLKB CAG CNXC COTY CPB GT POOL

This is NOT the generic staleness case (a genuinely dead feed, which is what #4643's
scan demotion handles). It is a merge defect: the panel already contains the right
answer and the reader throws it away. Downstream receipts at that vintage —
``engine.equity_factors._closes("broad")`` feeds site/factordata/factors.json,
site/factordata/alpha.json AND scripts/grade_us_board.py's price panel, so VIAV
ranked sector-leader #9/221 on a column that had stopped 23 days earlier while its
live column stood 9.2% lower.

CONTRACT — the naive repair (take the freshest column whole) trades one defect for
another: a migrant's NEW tier column starts on the migration date, so it carries only
26-51 observations against the dead column's 300-770, and every window factor that
needs history (vol / beta at min_price_history_d=150) goes NaN. Measured: all 9
rescued names would have lost their vol and beta legs, and VIAV's composite with them.

So the join is MEASUREMENT-GATED rather than assumed. Two tiers can carry the same
ticker on different adjustment bases (measured: CPB's two columns differ by a constant
1.69%, a dividend-adjustment gap), and stitching across that would manufacture exactly
the #2120 intra-series seam the adjudication forbids (R4/§4). But agreement is a thing
we can TEST, not guess: where the two columns are bit-identical on their overlapping
sessions they are the same series observed by two collector lanes, and combining them
is a gap-fill, not a basis mix. At the 2026-07-31 vintage 8 of the 9 overlaps are
identical to 0.000e+00 and stitch; CPB alone fails the test and falls back to the whole
live column, seam-free, accepting the shorter history rather than inventing a rebase.

Column COVERAGE is invariant: the merged panel carries the same ticker set as the
keep-first merge it replaces, so no admission lane loses its price source
(tests/test_us_board_ledger_continuity.py Section 1).
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

# Agreement bar for stitching a migrant's two tier columns into one series. Deliberately
# at float-noise level, NOT a tolerance band: anything a real adjustment difference would
# produce (CPB's 1.69%) must fail, and only lanes writing the identical series pass.
_STITCH_MAX_REL_DIFF = 1e-6
# Minimum overlapping sessions before the agreement test carries any evidence — one or
# two coincidentally-equal closes are not proof that two series share a basis.
_STITCH_MIN_OVERLAP = 5

# The canonical US tiers, in the historical naming-priority order. Callers pass
# their own order; a ticker's NAME/sector metadata still follows tier priority,
# only the PRICE column now follows freshness.
US_TIERS = ("breadth", "smallcap_breadth", "midcap_breadth", "russell_breadth")


def _last_valid(panel: pd.DataFrame) -> pd.Series:
    """ticker -> last non-NaN index label (NaT when the column is empty)."""
    if panel.empty:
        return pd.Series(dtype="datetime64[ns]")
    return panel.apply(lambda s: s.last_valid_index())


def _stitch_ok(dead: pd.Series, live: pd.Series) -> tuple[bool, int, float]:
    """Are these two columns the SAME series seen by two collector lanes?

    True only when they overlap on at least ``_STITCH_MIN_OVERLAP`` sessions AND agree
    to within float noise there. That is the whole seam argument: columns equal on every
    shared session cannot introduce a discontinuity when combined, whereas a genuine
    adjustment-basis difference (CPB's constant 1.69%) fails and is never spliced.

    Returns (ok, n_overlap, max_rel_diff)."""
    both = pd.concat([dead.rename("d"), live.rename("l")], axis=1).dropna()
    if len(both) < _STITCH_MIN_OVERLAP:
        return False, len(both), float("nan")
    rel = ((both["d"] / both["l"]) - 1.0).abs().max()
    if not pd.notna(rel):
        return False, len(both), float("nan")
    return bool(rel <= _STITCH_MAX_REL_DIFF), len(both), float(rel)


def choose_column(caches: dict, ticker: str, order) -> tuple[pd.Series | None, str | None]:
    """Freshest column for ONE ticker across already-loaded per-tier frames, with the
    same measurement-gated history stitch as :func:`merge_close_caches`.

    For callers that keep a {tier: DataFrame} dict rather than a merged panel
    (scripts/build_chart_data.py). ``order`` breaks freshness ties, preserving each
    caller's existing tier priority for every non-migrant ticker.

    Returns ``(series, source_tier)``, or ``(None, None)`` when no tier carries the
    ticker with any data.
    """
    have = [(g, caches[g][ticker]) for g in order
            if g in caches and caches[g] is not None and ticker in caches[g].columns]
    have = [(g, s) for g, s in have if s.notna().any()]
    if not have:
        return None, None
    best_g, best_s = have[0]
    for g, s in have[1:]:
        if s.last_valid_index() > best_s.last_valid_index():
            best_g, best_s = g, s
    for g, s in have:
        if g == best_g or s.notna().sum() <= best_s.notna().sum():
            continue
        ok, _n, _rel = _stitch_ok(s, best_s)
        if ok:
            best_s = best_s.combine_first(s)
            break
    return best_s, best_g


def merge_close_caches(
    groups,
    kind: str = "_closes_cache",
    data_dir: Path | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Merge the per-tier wide caches into one panel, FRESHEST column per ticker.

    ``groups`` is the tier order (used only to break freshness TIES, so behaviour is
    unchanged for every ticker that is not an index migrant). ``kind`` selects the
    cache file stem (``_closes_cache`` / ``_volume_cache`` / ``_high_cache`` / …).

    A missing or unreadable tier is skipped with a log line — never fatal, so one
    corrupt restored cache cannot blank a page (CSP-R1).

    Returns ``(panel, meta)``. ``meta`` carries:
      ``raw_tip``  -- maximum source index label, even when no ticker was observed there,
      ``tip``      -- latest returned row with at least one actual observation, or None,
      ``all_null_rows`` -- source-calendar rows where the merged population is wholly null,
      ``dropped_all_null_tail_rows`` -- the all-null suffix removed from the panel,
      ``behind``   -- {ticker: calendar days its chosen column lags effective ``tip``},
      ``source``   -- {ticker: tier the chosen column came from},
      ``rescued``  -- {ticker: (dead_tier, dead_days, live_tier)} for every ticker
                      where freshness overrode tier order — i.e. the columns this
                      merge saved from the keep-first defect. Never silent: the
                      caller discloses the count.
      ``stitched`` -- {ticker: (donor_tier, n_overlap, max_rel_diff)} for tickers whose
                      pre-migration history was restored from another tier AFTER that
                      tier's column was proven bit-identical on the overlap. A ticker
                      absent here kept a single intact column.
    """
    if data_dir is None:
        from lib import config
        data_dir = config.data_dir()

    frames: dict[str, pd.DataFrame] = {}
    for grp in groups:
        p = Path(data_dir) / grp / f"{kind}.parquet"
        if not p.exists():
            continue
        try:
            d = pd.read_parquet(p)
        except Exception as e:  # noqa: BLE001 — a corrupt cache must never kill a page
            log.warning("closes_panel: %s/%s unreadable (%s) — tier skipped", grp, kind, e)
            continue
        if d.empty:
            continue
        d = d.loc[:, ~d.columns.duplicated()]
        d.index = pd.to_datetime(d.index)
        frames[grp] = d.sort_index()

    if not frames:
        return pd.DataFrame(), {"raw_tip": None, "tip": None, "all_null_rows": [],
                                "dropped_all_null_tail_rows": [], "behind": {},
                                "source": {}, "rescued": {}, "stitched": {}}

    lasts = {g: _last_valid(d) for g, d in frames.items()}
    raw_tip = max(d.index.max() for d in frames.values())
    index = pd.to_datetime(sorted({i for d in frames.values() for i in d.index}))

    # Choose a source tier per ticker: freshest last-valid bar wins; ties (including
    # two all-empty columns) fall back to the caller's tier order, so this is a strict
    # refinement of the previous keep-first behaviour.
    chosen: dict[str, str] = {}
    for grp in groups:
        d = frames.get(grp)
        if d is None:
            continue
        for tk in d.columns:
            cur = chosen.get(tk)
            if cur is None:
                chosen[tk] = grp
                continue
            a, b = lasts[cur].get(tk), lasts[grp].get(tk)
            # NaT sorts last: a column with any data beats an all-empty one.
            a_ok, b_ok = pd.notna(a), pd.notna(b)
            if (b_ok and not a_ok) or (a_ok and b_ok and b > a):
                chosen[tk] = grp

    rescued: dict[str, tuple] = {}
    stitched: dict[str, tuple] = {}
    cols: dict[str, pd.Series] = {}
    for tk, grp in chosen.items():
        live = frames[grp][tk].reindex(index)
        # Any OTHER tier carrying this ticker with a staler tip is a candidate donor of
        # pre-migration history. Longest first: one donor is enough in practice, and a
        # deterministic order keeps the merge reproducible.
        donors = [g for g in groups
                  if g != grp and g in frames and tk in frames[g].columns]
        donors.sort(key=lambda g: -int(frames[g][tk].notna().sum()))
        for dg in donors:
            dead = frames[dg][tk].reindex(index)
            if dead.notna().sum() <= live.notna().sum():
                continue                      # donor adds no history worth testing
            ok, n_overlap, rel = _stitch_ok(dead, live)
            if not ok:
                continue      # too little overlap, or a different adjustment basis
            # Same series, two lanes: live wins wherever it exists, the donor only fills
            # sessions the live column never covered. No seam — the columns are equal on
            # every session they share.
            live = live.combine_first(dead)
            stitched[tk] = (dg, n_overlap, rel)
            break
        cols[tk] = live
        # Record the migrants whose price tip the old keep-first merge would have taken
        # from a dead column (i.e. tier order disagreed with freshness).
        first_by_order = next((g for g in groups
                               if g in frames and tk in frames[g].columns), None)
        if first_by_order is not None and first_by_order != grp:
            prev = lasts[first_by_order].get(tk)
            # The lag is filled after the effective panel tip is known. A raw source
            # calendar can contain a terminal all-null row, which is not a trading
            # observation and must not add a phantom day to the rescue receipt.
            rescued[tk] = (first_by_order, None, grp)

    out = pd.DataFrame(cols, index=index).sort_index()
    all_null_rows = list(out.index[out.isna().all(axis=1)]) if len(out.index) else []
    observed_rows = out.notna().any(axis=1) if len(out.index) else pd.Series(dtype=bool)
    if bool(observed_rows.any()):
        last_observed_pos = int(observed_rows.to_numpy().nonzero()[0][-1])
        dropped_tail = list(out.index[last_observed_pos + 1:])
        if dropped_tail:
            out = out.iloc[: last_observed_pos + 1]
        tip = out.index[-1]
    else:
        dropped_tail = list(out.index)
        out = out.iloc[0:0]
        tip = None

    for tk, (dead_tier, _dead_days, live_tier) in list(rescued.items()):
        prev = lasts[dead_tier].get(tk)
        rescued[tk] = (
            dead_tier,
            int((tip - prev).days) if tip is not None and pd.notna(prev) else None,
            live_tier,
        )

    behind: dict[str, int] = {}
    for tk in chosen:
        lv = out[tk].last_valid_index() if tk in out.columns else None
        behind[tk] = int((tip - lv).days) if tip is not None and pd.notna(lv) else -1
    return out, {"raw_tip": raw_tip, "tip": tip,
                 "all_null_rows": all_null_rows,
                 "dropped_all_null_tail_rows": dropped_tail,
                 "behind": behind, "source": chosen,
                 "rescued": rescued, "stitched": stitched}


def _date_text(value) -> str | None:
    """ISO date for an index label, or None without inventing a clock."""
    if value is None or pd.isna(value):
        return None
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def _normalise_frame_index(panel: pd.DataFrame) -> pd.DataFrame:
    out = panel.copy()
    out.index = pd.to_datetime(out.index)
    out = out.loc[~out.index.duplicated(keep="last")]
    return out.sort_index()


def _normalise_series_index(series: pd.Series) -> pd.Series:
    out = series.copy()
    out.index = pd.to_datetime(out.index)
    out = out.loc[~out.index.duplicated(keep="last")]
    return out.sort_index()


def align_latest_common_observation(
    panel: pd.DataFrame,
    benchmark_close: pd.Series,
) -> tuple[pd.DataFrame, pd.Series, dict]:
    """Trim a panel and benchmark to their latest EXACT shared observation.

    The benchmark must carry a real close on the selected date. We deliberately do
    not terminal-forward-fill it: a calendar label present only in one input is not
    a common market observation. Historical holes inside the retained window remain
    holes for the caller's incumbent return construction to handle.
    """
    p = _normalise_frame_index(panel)
    b = _normalise_series_index(benchmark_close)
    panel_raw_tip = p.index.max() if len(p.index) else None
    benchmark_raw_tip = b.index.max() if len(b.index) else None
    panel_obs = p.notna().any(axis=1) if len(p.index) else pd.Series(dtype=bool)
    panel_observed_tip = panel_obs[panel_obs].index.max() if bool(panel_obs.any()) else None
    b_valid = b.dropna()
    benchmark_observed_tip = b_valid.index.max() if not b_valid.empty else None

    common = p.index.intersection(b_valid.index)
    if len(common):
        valid = panel_obs.reindex(common).fillna(False)
        candidates = common[valid.to_numpy(dtype=bool)]
    else:
        candidates = common
    effective = candidates.max() if len(candidates) else None

    if effective is None:
        aligned = p.iloc[0:0]
        bench = b.reindex(aligned.index)
        dropped = list(p.index)
        status = "unavailable"
    else:
        aligned = p.loc[p.index <= effective].copy()
        bench = b.reindex(aligned.index)
        dropped = list(p.index[p.index > effective])
        status = "ok"

    meta = {
        "status": status,
        "panel_raw_tip": _date_text(panel_raw_tip),
        "panel_observed_tip": _date_text(panel_observed_tip),
        "benchmark_raw_tip": _date_text(benchmark_raw_tip),
        "benchmark_observed_tip": _date_text(benchmark_observed_tip),
        "effective_as_of": _date_text(effective),
        "dropped_panel_rows_after_effective": [_date_text(x) for x in dropped],
        "basis": "latest_exact_panel_and_benchmark_observation",
    }
    return aligned, bench, meta


def resolve_thematic_close_panel(
    primary: pd.DataFrame,
    supplemental: pd.DataFrame | None,
    tickers,
) -> tuple[pd.DataFrame, dict]:
    """Resolve thematic member closes on the already-frozen primary calendar.

    Source selection is whole-column: the source with the later actual observation
    wins, with ``baskets_extras`` winning exact ties.  The losing source may donate
    older history only when :func:`_stitch_ok` proves both columns are the same
    measured series on a sufficient overlap.  Supplemental rows outside the primary
    calendar are discarded before selection, so this helper can widen population but
    can never advance the desk clock.
    """
    p = _normalise_frame_index(primary)
    if supplemental is None or supplemental.empty:
        s = pd.DataFrame(index=p.index)
    else:
        s = _normalise_frame_index(supplemental).reindex(p.index)

    names = list(dict.fromkeys(str(t) for t in tickers if t))
    cols: dict[str, pd.Series] = {}
    price_source: dict[str, str] = {}
    reason: dict[str, str] = {}
    source_last: dict[str, dict[str, str | None]] = {}
    stitched: dict[str, dict] = {}
    unresolved: list[str] = []
    counts = {"primary_breadth": 0, "baskets_extras": 0}

    for ticker in names:
        ps = p[ticker] if ticker in p.columns else None
        ss = s[ticker] if ticker in s.columns else None
        p_ok = ps is not None and bool(ps.notna().any())
        s_ok = ss is not None and bool(ss.notna().any())
        p_last = ps.last_valid_index() if p_ok else None
        s_last = ss.last_valid_index() if s_ok else None
        source_last[ticker] = {
            "primary_breadth": _date_text(p_last),
            "baskets_extras": _date_text(s_last),
        }

        if not p_ok and not s_ok:
            unresolved.append(ticker)
            continue
        if s_ok and not p_ok:
            winner, winner_source, why, donor, donor_source = (
                ss.copy(), "baskets_extras", "supplemental_only", None, None)
        elif p_ok and not s_ok:
            winner, winner_source, why, donor, donor_source = (
                ps.copy(), "primary_breadth", "primary_only", None, None)
        elif s_last > p_last:
            winner, winner_source, why, donor, donor_source = (
                ss.copy(), "baskets_extras", "supplemental_fresher", ps, "primary_breadth")
        elif p_last > s_last:
            winner, winner_source, why, donor, donor_source = (
                ps.copy(), "primary_breadth", "primary_fresher", ss, "baskets_extras")
        else:
            winner, winner_source, why, donor, donor_source = (
                ss.copy(), "baskets_extras", "tie_supplemental", ps, "primary_breadth")

        if donor is not None and donor.notna().sum() > winner.notna().sum():
            ok, n_overlap, rel = _stitch_ok(donor, winner)
            if ok:
                winner = winner.combine_first(donor)
                stitched[ticker] = {
                    "donor_source": donor_source,
                    "n_overlap": int(n_overlap),
                    "max_rel_diff": float(rel),
                }

        cols[ticker] = winner.reindex(p.index)
        price_source[ticker] = winner_source
        reason[ticker] = why
        counts[winner_source] += 1

    out = pd.DataFrame(cols, index=p.index)
    receipt = {
        "effective_as_of": _date_text(p.index.max()) if len(p.index) else None,
        "calendar_basis": "primary_panel_only_supplement_cannot_advance",
        "requested_n": len(names),
        "resolved_n": len(cols),
        "unresolved_n": len(unresolved),
        "unresolved_tickers": unresolved,
        "chosen_counts": counts,
        "price_source": price_source,
        "selection_reason": reason,
        "source_last_observation": source_last,
        "stitched": stitched,
        "source_basis": {
            "primary_breadth": "closes_cache_UNADJUSTED",
            "baskets_extras": "tradj",
        },
        "adjustment_vintage": "unrecorded",
        "authority": "measurement_only",
    }
    return out, receipt


def population_observation(
    panel: pd.DataFrame,
    members: list[dict],
    as_of,
    *,
    min_members: int = 3,
    min_coverage: float = 0.60,
) -> dict:
    """Observation receipt for one dated basket population at ``as_of``.

    Membership eligibility, column presence and an actual close are intentionally
    separate counts. This is measurement admission only; it carries no market or
    recommendation authority.
    """
    p = _normalise_frame_index(panel)
    when = pd.Timestamp(as_of)
    configured: list[str] = []
    seen: set[str] = set()
    for member in members or []:
        ticker = member.get("ticker") or member.get("symbol")
        if not ticker or ticker in seen:
            continue
        added = member.get("added")
        removed = member.get("removed")
        if added and when < pd.Timestamp(added):
            continue
        if removed and when >= pd.Timestamp(removed):
            continue
        seen.add(str(ticker))
        configured.append(str(ticker))

    in_panel = [ticker for ticker in configured if ticker in p.columns]
    missing_columns = [ticker for ticker in configured if ticker not in p.columns]
    if when in p.index:
        row = p.loc[when]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[-1]
        observed = [ticker for ticker in in_panel if pd.notna(row.get(ticker))]
    else:
        observed = []
    missing_at_asof = [ticker for ticker in in_panel if ticker not in set(observed)]

    configured_n = len(configured)
    observed_n = len(observed)
    coverage = (observed_n / configured_n) if configured_n else None
    eligible = bool(configured_n and observed_n >= int(min_members)
                    and coverage is not None and coverage >= float(min_coverage))
    if configured_n and observed_n == configured_n:
        status = "complete"
    elif eligible:
        status = "partial"
    else:
        status = "insufficient"

    return {
        "effective_as_of": _date_text(when),
        "configured_members": configured,
        "configured_n": configured_n,
        "in_panel_members": in_panel,
        "in_panel_n": len(in_panel),
        "observed_members": observed,
        "observed_n": observed_n,
        "missing_columns": missing_columns,
        "missing_at_asof": missing_at_asof,
        "coverage": round(float(coverage), 4) if coverage is not None else None,
        "status": status,
        "aggregate_eligible": eligible,
        "min_members": int(min_members),
        "min_coverage": float(min_coverage),
        "basis": "exact_close_at_effective_as_of",
        "authority": "measurement_only",
    }


_DISCLOSED: set = set()


def disclose_merge(meta: dict, label: str) -> None:
    """Emit line-start Actions warnings for material merge corrections, once each.

    Bare print, never the logger: every builder here logs with a prefixing format,
    so ``log.warning("::warning ...")`` emits ``WARNING ::warning ...`` and GitHub
    silently drops it (repo annotation law, tests/test_gh_annotation_line_start.py).

    Calendar-tail correction and stale-tier rescue are independent facts. Each gets a
    separate dedupe identity so an all-null terminal session is disclosed even when no
    ticker needed source-tier rescue, and callers that share `_closes()` do not repeat it.
    """
    dropped_tail = tuple(meta.get("dropped_all_null_tail_rows") or ())
    if dropped_tail:
        raw_tip = meta.get("raw_tip")
        tip = meta.get("tip")
        calendar_key = (label, "observation_calendar", raw_tip, tip, dropped_tail)
        if calendar_key not in _DISCLOSED:
            _DISCLOSED.add(calendar_key)
            dates = ", ".join(_date_text(d) or "unknown" for d in dropped_tail[:6])
            more = "" if len(dropped_tail) <= 6 else f" (+{len(dropped_tail) - 6} more)"
            print(
                f"::warning title={label} observation calendar::"
                f"raw source calendar reached {_date_text(raw_tip) or 'unknown'}, but "
                f"{dates}{more} carried no prices; effective {_date_text(tip) or 'unavailable'}",
                flush=True,
            )

    rescued = meta.get("rescued") or {}
    if not rescued:
        return
    rescue_key = (label, "stale_tier", tuple(sorted(rescued)))
    if rescue_key in _DISCLOSED:
        return
    _DISCLOSED.add(rescue_key)
    names = ", ".join(f"{t}({d[0]}->{d[2]})" for t, d in sorted(rescued.items())[:12])
    more = "" if len(rescued) <= 12 else f" (+{len(rescued) - 12} more)"
    print(f"::warning title={label} stale-tier column overridden::{len(rescued)} ticker(s) "
          f"carried a FROZEN column in an earlier tier and a live one in a later tier — "
          f"index migrants whose old tier's column stopped on index exit; the live "
          f"column now wins: {names}{more}", flush=True)
