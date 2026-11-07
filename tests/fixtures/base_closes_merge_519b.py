"""Literal pre-extraction merge source for independent compatibility comparisons.
Source: 519b2ae0060c40db6ae01b928157ca304ff4d7c8:lib/closes_panel.py
Whole source SHA256: 4d0388506ac93f5dddac6dc50545cb4029b567ea4986e49df202d346f370634e
"""
from __future__ import annotations
import logging
from pathlib import Path
import pandas as pd
log = logging.getLogger(__name__)
_STITCH_MAX_REL_DIFF = 1e-6
_STITCH_MIN_OVERLAP = 5

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
