"""Self-grader for the China Sector Central engine — the piece that makes Phase 2's predictive
power MEASURED, not asserted (the gap the allocation_china audit exposed: nothing in the
rotation stack grades its own calls).

Two halves:
  • append_central_log(data) — append today's per-sector/basket central CALL (conviction score +
    direction + the as-of price level) to an append-only, point-in-time store
    (data/china_sector_central/calls.parquet), keep-FIRST per (date, id) so a past day's stamped
    call is never rewritten.
  • grade(horizons) — for every logged call old enough to have a realized outcome, join the
    forward return (sector = Shenwan close; basket = equal-weight level), and score the engine:
    directional hit-rate (overall + by conviction tier), cross-sectional rank-IC of the
    conviction score vs forward return, and forward return vs the Shanghai Composite. Returns a
    scorecard the dashboard renders honestly (sparse until it accrues).

Display/research-only — the log is NEVER read back into a live score. Additive / fail-soft.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from engine.ledger_lane import asia_advance_enabled as _ledger_advance_enabled
from lib import config

log = logging.getLogger(__name__)

_HORIZONS_D = (21, 63, 126)        # ~1/3/6 months — the horizons the audit showed matter
_STORE = ("china_sector_central", "calls.parquet")

# ── SIC-D-B07 (grader schema v2): the interpretable reading BESIDE the legacy rate ──
# Masterplan §6.2 "Grader denominator": legacy dir_hit_rate divides correct up+down
# calls by ALL graded rows — Neutral included — so it is neither a conditional
# directional hit rate nor a win rate.  The helpers below ADD directional coverage, a
# conditional rate with date-clustered uncertainty, Neutral outcomes, matured/
# excluded/accruing counts, IC/excess distributions and call-month cohort maturity,
# mirroring sector_central_grader field-for-field.  The legacy value and its formula
# stay byte-identical; no existing key is renamed or removed.  Descriptive statistics
# over correlated observations — the log is never read back into a live score and
# none of this is trading P&L.

_SCHEMA_V2 = 2
_DIR_HIT_RATE_DEFINITION = (
    "legacy: correct up + correct down calls / all graded rows including Neutral "
    "(not a conditional hit rate, not a win rate)")
_INTERPRETATION = (
    "descriptive evaluation over correlated observations; not a win rate, "
    "not trading P&L")


def _month_key(date) -> str | None:
    """Call-date month key ("YYYY-MM") for cohort maturity, or None when unparseable."""
    try:
        ts = pd.Timestamp(date)
    except Exception:  # noqa: BLE001
        return None
    return None if pd.isna(ts) else ts.strftime("%Y-%m")


def _session_calendar_cn(bench, basket_lvl: dict):
    """Sorted union of every price session the grader can see (benchmark + frozen
    basket levels) — the 'latest available price session' reference that splits
    too-young calls (accruing) from old calls with no forward price (excluded)."""
    parts = []
    if bench is not None and len(bench.index):
        parts.append(pd.DatetimeIndex(bench.index))
    for s, _vs in basket_lvl.values():
        if s is not None and len(s.index):
            parts.append(pd.DatetimeIndex(s.index))
    if not parts:
        return None
    cal = parts[0]
    for extra in parts[1:]:
        cal = cal.union(extra)
    return cal


def _horizon_end_after_latest_session_cn(date, h: int, cal) -> bool:
    """True iff the call's h-bar horizon extends past the latest available session —
    the call is TOO YOUNG to grade (accruing) rather than an old call whose forward
    price is missing (excluded_no_forward).  Mirrors _fwd_return's same-bar maturity
    convention on the union calendar: matured iff the calendar supplies >= h bars
    strictly after the call's own session bar (one-bar conservative when the call
    date falls between sessions)."""
    if cal is None or not len(cal):
        return True          # no visible price data — nothing can have matured yet
    d0 = pd.Timestamp(date)
    loc = int(np.searchsorted(cal.values, d0.to_datetime64(), side="right")) - 1
    if loc < 0:
        return False         # the call predates every visible session — long past due
    return (len(cal) - (loc + 1)) < h


def _v2_counts(n_matured, n_membership, n_pre_chain, n_no_forward, n_accruing) -> dict:
    """Maturity partition of the logged calls at one horizon (schema v2)."""
    return {
        "matured": int(n_matured),
        "excluded_membership": int(n_membership),
        "excluded_pre_chain": int(n_pre_chain),
        "excluded_no_forward": int(n_no_forward),
        "accruing": int(n_accruing),
    }


def _v2_cohort_months(row_status) -> dict:
    """Call-month cohort maturity: {YYYY-MM: {n_logged, n_matured, n_accruing, n_excluded}}."""
    out: dict[str, dict] = {}
    for month, status in row_status:
        if month is None:
            continue
        c = out.setdefault(month, {"n_logged": 0, "n_matured": 0, "n_accruing": 0, "n_excluded": 0})
        c["n_logged"] += 1
        c["n_matured" if status == "matured" else
          "n_accruing" if status == "accruing" else "n_excluded"] += 1
    return dict(sorted(out.items()))


def _v2_directional_stats(g: pd.DataFrame) -> dict:
    """Directional coverage, the conditional directional hit rate with its
    date-clustered SE, and the Neutral-outcome summary for one graded horizon.

    The correctness rule matches the legacy numerator exactly: an up call is correct
    iff fwd > 0, a down call iff fwd < 0 — a flat (== 0) forward return is correct
    for neither side.  The SE freezes the cluster-robust form

        se = sqrt( G/(G-1) * sum_dates (sum_{i in date} r_i)^2 ) / n_directional

    with r_i = correct_i - p over directional rows only and G the number of dates
    holding >= 1 directional row (None when G < 2).  Deterministic — no random draws."""
    dir_mask = g["dir"].isin(["up", "down"])
    up = g[g["dir"] == "up"]
    dn = g[g["dir"] == "down"]
    n = len(g)
    n_correct = int((up["fwd"] > 0).sum() + (dn["fwd"] < 0).sum())
    n_dir = int(dir_mask.sum())
    n_neutral = int(n - n_dir)
    rate = None
    se = None
    if n_dir:
        p = n_correct / n_dir
        rate = round(p, 4)
        dg = g[dir_mask]
        correct = (((dg["dir"] == "up") & (dg["fwd"] > 0))
                   | ((dg["dir"] == "down") & (dg["fwd"] < 0))).astype(float)
        cluster = (correct - p).groupby(dg["date"]).sum()
        G = int(cluster.size)
        if G >= 2:
            se = round(float(np.sqrt(G / (G - 1) * float((cluster ** 2).sum())) / n_dir), 4)
    ng = g[~dir_mask]
    return {
        "n_directional": n_dir,
        "n_neutral": n_neutral,
        "n_correct_directional": n_correct,
        "directional_coverage": round(n_dir / n, 4) if n else None,
        "conditional_directional_hit_rate": rate,
        "conditional_hit_rate_se": se,
        "uncertainty_method": "date_clustered_se",
        "neutral_outcomes": {
            "n": n_neutral,
            "mean_fwd": round(float(ng["fwd"].mean()), 4) if n_neutral else None,
            "mean_abs_fwd": round(float(ng["fwd"].abs().mean()), 4) if n_neutral else None,
            "mean_excess": (round(float(ng["excess"].dropna().mean()), 4)
                            if n_neutral and ng["excess"].notna().any() else None),
        },
    }


def _v2_dist_summary(arr) -> dict:
    """Shared {mean, median, p25, p75, share_positive} shape (None fields when empty)
    for the per-date IC and per-row excess distributions."""
    if arr is None or len(arr) == 0:
        return {"mean": None, "median": None, "p25": None, "p75": None, "share_positive": None}
    a = np.asarray(arr, dtype=float)
    return {
        "mean": round(float(a.mean()), 4),
        "median": round(float(np.median(a)), 4),
        "p25": round(float(np.percentile(a, 25)), 4),
        "p75": round(float(np.percentile(a, 75)), 4),
        "share_positive": round(float((a > 0).mean()), 4),
    }


def _v2_rank_ic_distribution(ics: list) -> dict:
    """Distribution of the existing per-date rank ICs (same >= 3 distinct-score rule
    as the rank_ic mean; the mean key itself is left untouched in grade())."""
    return {"n_dates": len(ics), **_v2_dist_summary(ics)}


def _v2_excess_distribution(g: pd.DataFrame) -> dict:
    """Distribution of non-null excess (forward return vs the benchmark) for one horizon."""
    ex = g["excess"].dropna()
    return {"n": int(len(ex)), **_v2_dist_summary(ex.to_numpy() if len(ex) else None)}


def _level_for(row: dict) -> float | None:
    """The as-of price level for a call (sector = Shenwan close; basket = EW level)."""
    try:
        from engine import china_sector_index as csi
        if row.get("kind") == "sector" and row.get("shenwan_code"):
            s = csi.sw_close(row["shenwan_code"])
            return float(s.iloc[-1]) if s is not None and not s.empty else None
    except Exception:  # noqa: BLE001
        pass
    return None


def append_central_log(data: dict) -> int:
    # House law: nightly is the SOLE advancer of data/ forward ledgers — but for THIS
    # store the advancing lane is ASIA, not US-nightly. Its only caller is
    # scripts.build_china_sector_central in asia-close.yml band 2, whose step env sets
    # CN_LANE=asia and NO job-wide COLLECT_LANE; gating on nightly_advance_enabled()
    # would close this gate forever (the "gate accidentally always closed" class).
    # Keep-FIRST per (date, id): an off-lane append displaces the stamped row for good.
    if not _ledger_advance_enabled():
        return 0
    asof = (data or {}).get("as_of")
    if not asof:
        return 0
    rows = []
    for rec in (data.get("sectors", []) + data.get("baskets", [])):
        conv = rec.get("conviction") or {}
        fwd = rec.get("forward") or {}
        rows.append({
            "date": asof, "id": rec.get("id"), "kind": rec.get("kind"),
            "shenwan_code": rec.get("shenwan_code"), "basket_id": rec.get("basket_id"),
            "name": rec.get("name"),
            "score": conv.get("score"), "label": conv.get("label_en"), "dir": conv.get("dir"),
            "confluence": (conv.get("confluence") or {}).get("agree"),
            "fwd_cond_rate": fwd.get("cond_rate"), "fwd_lift": fwd.get("lift"),
            "gate_factor": (rec.get("components") or {}).get("gate_factor"),
            "level": _level_for(rec),
        })
    if not rows:
        return 0
    try:
        new = pd.DataFrame(rows)
        p = config.data_dir() / _STORE[0] / _STORE[1]
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists():
            prior = pd.read_parquet(p)
            combined = pd.concat([prior, new], ignore_index=True).drop_duplicates(
                subset=["date", "id"], keep="first")
        else:
            combined = new
        combined.to_parquet(p, index=False)
        return len(new)
    except Exception as e:  # noqa: BLE001
        log.warning("central grader: append failed: %s", e)
        return 0


def _mhash_stable_cn(basket_id: str, d0: pd.Timestamp, h: int, frozen_df) -> bool:
    """Return True iff the China/THS basket's membership hash is stable over [d0, d0+h].

    Checks both 'china' and 'china_ths' domains (whichever has the basket).
    Returns False when uncertain (no frozen data) — grade is dropped rather than silently
    scored across a composition change.
    """
    if frozen_df is None:
        return False
    col = f"{basket_id}__mhash"
    if col not in frozen_df.columns:
        return False
    window = frozen_df.loc[
        (frozen_df.index >= d0) & (frozen_df.index <= d0 + pd.Timedelta(days=h * 2))
    ][col].dropna()
    if window.empty:
        return False
    return window.nunique() == 1


def _basket_levels_cn() -> tuple[dict, object]:
    """Basket level series from the FROZEN store for China + THS domains.

    W3.8: replaces the live compute_china_baskets() path.  Returns
    ({bid: (series, return_valid_start)}, merged_frozen_df).  Before the first freeze
    both are empty/None and the grader reports 'accruing from <freeze_start>'.

    2026-08 (chain fix): the frozen series is a RETURN series only from its chain
    anchor onward — rows written before the chain-linked writer each sat on that
    night's rolling-window base.  Each basket is clamped to
    ``basket_freeze.return_valid_start()`` (per DOMAIN, since anchors are per-store)
    and a basket with no anchor at all is EXCLUDED outright.
    """
    out: dict = {}
    merged_frozen = None
    try:
        # _return_valid_start_from: the public return_valid_start() contract against
        # the frame we already read (one parquet read per domain, not per basket).
        from engine.basket_freeze import read_frozen, _return_valid_start_from
        for domain in ("china", "china_ths"):
            df = read_frozen(domain)
            if df is None or df.empty:
                continue
            # Merge for mhash checks (union of both domain columns)
            if merged_frozen is None:
                merged_frozen = df
            else:
                merged_frozen = pd.concat([merged_frozen, df], axis=1)
            for col in df.columns:
                if not col.endswith("__level_tr"):
                    continue
                bid = col[: -len("__level_tr")]
                s = df[col].dropna()
                if s.empty:
                    continue
                vs = _return_valid_start_from(df, bid)
                if vs is None:
                    log.info("basket_levels_cn[%s]: %s has no chain anchor — excluded", domain, bid)
                    continue
                s = s[s.index >= pd.Timestamp(vs)]
                if s.empty:
                    continue
                out[bid] = (s, vs)
    except Exception as e:  # noqa: BLE001
        log.warning("basket_levels_cn: frozen read failed: %s", e)
    return out, merged_frozen


def _fwd_return(row: pd.Series, h: int, basket_lvl: dict,
                frozen_df=None) -> tuple[float | None, str | None]:
    """Realized return from the call date to call_date + h trading days (sector = Shenwan;
    basket = EW level), or (None, None) if the horizon hasn't elapsed / series missing.

    W3.8: basket calls additionally check membership-hash stability over the forward
    window.  Returns (return_float | None, invalidation_reason | None).

    2026-08: basket calls dated BEFORE the basket's chain anchor are invalidated
    ('pre_chain_anchor').  The check is load-bearing on its own — clamping the series
    truncates the window but cannot express the error: without it, a pre-anchor call
    would be graded against a window that silently STARTS at the anchor while still
    wearing the call's own (earlier) date.
    """
    try:
        from engine import china_sector_index as csi
        d0 = pd.Timestamp(row["date"])
        if row.get("kind") == "sector" and pd.notna(row.get("shenwan_code")):
            s = csi.sw_close(row["shenwan_code"])
            if s is None or s.empty:
                return None, None
            s = s[s.index >= d0]
            if len(s) <= h:
                return None, None
            return float(s.iloc[h] / s.iloc[0] - 1.0), None
        else:
            bid = row.get("basket_id")
            entry = basket_lvl.get(bid)
            if entry is None:
                # Not in the chained set: no frozen series at all (accruing — honest
                # null) or present-but-unanchored, which is a pre-anchor read.
                cols = getattr(frozen_df, "columns", ())
                if f"{bid}__level_tr" in cols:
                    return None, "pre_chain_anchor"
                return None, None
            s, vs = entry
            if s is None or s.empty:
                return None, None
            if vs is None or d0 < pd.Timestamp(vs):
                return None, "pre_chain_anchor"
            # W3.8: membership-hash stability check
            if not _mhash_stable_cn(bid, d0, h, frozen_df):
                return None, "membership_changed"
            s = s[s.index >= d0]
            if len(s) <= h:
                return None, None
            return float(s.iloc[h] / s.iloc[0] - 1.0), None
    except Exception:  # noqa: BLE001
        return None, None


def grade() -> dict | None:
    """Score every matured call. Returns a scorecard {n_calls, n_graded, dates, by_horizon}.

    W3.8 changes:
    - Basket forward returns read from the FROZEN store (data/basket_levels/{china,china_ths}
      .parquet) only.  The live compute_china_baskets() path is gone.
    - Grades whose forward window spans a membership-hash change are INVALIDATED
      (dropped with reason 'membership_changed'; counted in invalidated_membership).
    - Pre-freeze basket calls are NOT graded: the scorecard reports
      'accruing from <freeze_start>' — the permanent survivorship hole (D4-N3 / R1).

    2026-08 (chain fix): basket calls dated before the basket's chain anchor are
    INVALIDATED (dropped with reason 'pre_chain_anchor'; counted in
    invalidated_pre_chain).  The scorecard exposes basket_return_valid_start — the
    newest chain anchor among gradable baskets.
    """
    p = config.data_dir() / _STORE[0] / _STORE[1]
    if not p.exists():
        return {"available": False, "note": "no calls logged yet"}
    try:
        df = pd.read_parquet(p)
    except Exception as e:  # noqa: BLE001
        return {"available": False, "note": f"unreadable: {e}"}
    if df.empty:
        return {"available": False, "note": "empty"}

    # W3.8: basket level series from FROZEN store only (no live recompute)
    basket_lvl, frozen_df = _basket_levels_cn()

    # Freeze-start for transparency reporting (earliest frozen date across china + china_ths)
    freeze_start = None
    try:
        from engine.basket_freeze import freeze_start_date
        starts = [freeze_start_date(d) for d in ("china", "china_ths")]
        valid_starts = [s for s in starts if s]
        freeze_start = min(valid_starts) if valid_starts else None
    except Exception:  # noqa: BLE001
        pass

    bench = None
    try:
        from engine import china_sector_index as csi
        # W0.3 / D4 benchmark basis-match: use price-basis benchmark so that
        # excess = sector_price − bench_price (same basis). benchmark_close_price()
        # prefers 'close_price' (D4-W1 dual-basis) with a logged fallback to 'close'
        # (TR) — for 000001.SS these are empirically identical (no dividend adjustment
        # on equity indices), so the fallback is safe while D4-W1 is pending.
        bench = csi.benchmark_close_price()
    except Exception:  # noqa: BLE001
        pass

    # 2026-08: newest chain anchor across the baskets we can actually grade.
    _valid_starts = [vs for _s, vs in basket_lvl.values() if vs]
    basket_valid_start = max(_valid_starts) if _valid_starts else None

    out = {
        "available": True, "n_calls": int(len(df)),
        # SIC-D-B07 (grader schema v2): versioned, interpretable reading — see the
        # helper block above the grade() docstring history for what v2 adds.
        "grader_schema_version": _SCHEMA_V2,
        "interpretation": _INTERPRETATION,
        "dates": sorted(df["date"].dropna().unique().tolist()),
        "horizons_d": list(_HORIZONS_D), "by_horizon": {},
        # W3.8 transparency fields
        "freeze_start": freeze_start,
        "basket_return_valid_start": basket_valid_start,
        "pre_freeze_note": (
            f"Basket grading accruing from {freeze_start} (W3.8 freeze date). "
            "Pre-freeze basket calls are not graded: the series before this date is "
            "permanently survivorship-contaminated (D4-N3)."
            if freeze_start else
            "Basket grading not yet started (no frozen store). "
            "Basket calls will accrue once the first freeze runs."
        ) + (
            " Basket return math re-anchored 2026-08 after the moving-base freeze "
            "defect; grades accrue from the chain anchor"
            + (f" ({basket_valid_start})." if basket_valid_start else ".")
        ),
    }
    # SIC-D-B07: the union price calendar behind the accruing-vs-excluded split.
    cal = _session_calendar_cn(bench, basket_lvl)
    for h in _HORIZONS_D:
        recs = []
        n_invalidated_membership = 0
        n_invalidated_pre_chain = 0
        n_excluded_no_forward = 0
        n_accruing = 0
        row_status: list[tuple[str | None, str]] = []
        for _i, row in df.iterrows():
            fr, inv_reason = _fwd_return(row, h, basket_lvl, frozen_df=frozen_df)
            if inv_reason == "pre_chain_anchor":
                n_invalidated_pre_chain += 1
                row_status.append((_month_key(row.get("date")), "excluded"))
                continue
            if inv_reason == "membership_changed":
                n_invalidated_membership += 1
                row_status.append((_month_key(row.get("date")), "excluded"))
                continue
            if fr is None:
                # too young (horizon end after the latest session) vs old-but-unpriceable
                if _horizon_end_after_latest_session_cn(row["date"], h, cal):
                    n_accruing += 1
                    row_status.append((_month_key(row.get("date")), "accruing"))
                else:
                    n_excluded_no_forward += 1
                    row_status.append((_month_key(row.get("date")), "excluded"))
                continue
            row_status.append((_month_key(row.get("date")), "matured"))
            br = None
            if bench is not None:
                d0 = pd.Timestamp(row["date"]); bb = bench[bench.index >= d0]
                if len(bb) > h:
                    br = float(bb.iloc[h] / bb.iloc[0] - 1.0)
            recs.append({"date": row["date"], "score": row.get("score"), "dir": row.get("dir"),
                         "label": row.get("label"), "fwd": fr,
                         "excess": (fr - br) if br is not None else None})
        by_cohort_month = _v2_cohort_months(row_status)
        counts_v2 = _v2_counts(len(recs), n_invalidated_membership, n_invalidated_pre_chain,
                               n_excluded_no_forward, n_accruing)
        if len(recs) < 3:
            out["by_horizon"][f"{h}d"] = {
                "n": len(recs), "note": "accruing",
                "invalidated_membership": n_invalidated_membership,
                "invalidated_pre_chain": n_invalidated_pre_chain,
                # SIC-D-B07: while the horizon accrues, the counts that exist.
                "counts": counts_v2,
                "by_cohort_month": by_cohort_month,
            }
            continue
        g = pd.DataFrame(recs)
        # directional hit-rate (up call → positive fwd; down call → negative)
        up = g[g["dir"] == "up"]; dn = g[g["dir"] == "down"]
        hit = float(((up["fwd"] > 0).sum() + (dn["fwd"] < 0).sum()) / len(g)) if len(g) else None
        # cross-sectional rank-IC per date (score vs fwd), averaged
        ics = []
        for d, sub in g.groupby("date"):
            if sub["score"].nunique() >= 3:
                ics.append(float(sub["score"].rank().corr(sub["fwd"].rank())))
        # by tier
        by_tier = {}
        for lab, sub in g.groupby("label"):
            if len(sub) >= 3:
                by_tier[lab] = {"n": int(len(sub)), "mean_fwd": round(float(sub["fwd"].mean()), 4),
                                "mean_excess": (round(float(sub["excess"].dropna().mean()), 4)
                                                if sub["excess"].notna().any() else None),
                                "pos_rate": round(float((sub["fwd"] > 0).mean()), 3)}
        out["by_horizon"][f"{h}d"] = {
            "n": int(len(g)), "dir_hit_rate": round(hit, 3) if hit is not None else None,
            "rank_ic": round(float(np.mean(ics)), 4) if ics else None, "n_ic_dates": len(ics),
            "mean_excess_vs_bench": (round(float(g["excess"].dropna().mean()), 4)
                                     if g["excess"].notna().any() else None),
            "by_tier": by_tier,
            "invalidated_membership": n_invalidated_membership,
            "invalidated_pre_chain": n_invalidated_pre_chain,
            # ── SIC-D-B07 (grader schema v2): the interpretable reading, added ──
            "dir_hit_rate_definition": _DIR_HIT_RATE_DEFINITION,
            **_v2_directional_stats(g),
            "counts": counts_v2,
            "rank_ic_distribution": _v2_rank_ic_distribution(ics),
            "excess_distribution": _v2_excess_distribution(g),
            "by_cohort_month": by_cohort_month,
        }
    out["n_graded"] = max((v.get("n", 0) for v in out["by_horizon"].values()), default=0)
    return out
