"""B1 — Statistics computation.

Precomputes month→row-index maps for each (variant, era, column) group, then
runs 1000-iteration month-cluster bootstraps in numpy.

Reproducible RNG: a single numpy SeedSequence(20261004) is built at import time, and
every per-cell RNG is `.spawn(stable_int_index)` from a sorted cell order — NEVER
``hash((str, str))`` (D3; Python per-process str hashing would otherwise break
byte-identical result.json across runs with different PYTHONHASHSEED).

Verdict rule (D9): grain_effect_3d REAL iff
  (a) ≥ 2 phases of 3D.p − 1D.M3 each have BOTH eras with the SAME sign AND
      a CI excluding zero, AND
  (b) those ≥ 2 qualifying phases all share a common sign among themselves.
memory_effect_3 REAL iff Δ(1D.M3 − 1D) has the same sign in both eras and
both eras' CIs exclude zero (one phase, two eras; same-sign already implied by
"in both eras").

NOT SUPPORTED iff every phase has at least one zero-including CI AND every
contrast cell (both arms × both eras) has n_events ≥ 300 and n_months ≥ 24.
INSUFFICIENT otherwise.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_THIS_FILE = Path(__file__).resolve()
CODE_DIR = _THIS_FILE.parent
RESULTS_DIR = CODE_DIR.parent
REPO = RESULTS_DIR.parent.parent.parent.parent.parent
sys.path.insert(0, str(REPO))

from engine import session_anchor  # noqa: E402  G3: SPY session position for tolerant Jaccard

RNG_SEED = 20261004
N_BOOTSTRAP = 1000
H10 = "excess_h10_net"
H21 = "excess_h21_net"
VARIANTS = ("1D", "2D.p0", "2D.p1", "3D.p0", "3D.p1", "3D.p2", "1D.M2", "1D.M3", "3D.K1")
ERAS = ("2014-2019", "2020-2026")

# Master SeedSequence → distinct children per cell (D3 + G7).
# G7: build the sorted list of all cell labels BEFORE any bootstrap, call
# SeedSequence(RNG_SEED).spawn(len(cells)) exactly once, and map label → child
# by sorted index. No registry, no encounter-order dependency → byte-identical
# result.json across two processes.
_MASTER_SS = np.random.SeedSequence(RNG_SEED)
_GLOBAL_RNG = np.random.default_rng(_MASTER_SS)

# G7: a single sorted-cell spawn produces distinct streams for every label.
_CELL_RNG_CACHE: dict[str, np.random.Generator] = {}
_CELL_TO_INDEX: dict[str, int] = {}
_CHILDREN: list[np.random.SeedSequence] = []


def _build_cell_streams(sorted_labels: list[str]) -> None:
    """Build one SeedSequence.spawn() over a STABLE sorted list of labels.

    Call once, BEFORE any bootstrap. Reset state, then spawn `len(labels)` distinct
    children and map label → child by sorted index. The sorted-label ordering is
    the only source of label → index stability across processes — encounter order
    was unsafe (F8/G7).

    G7: Spawning from a persistent SeedSequence mutates its internal entropy and
    makes subsequent spawns non-reproducible. Re-create the parent on each call from
    the deterministic integer entropy (SeedSequence(RNG_SEED)) — same parent state
    across calls (and across processes), so the children are byte-identical.
    """
    global _CHILDREN, _CELL_TO_INDEX, _CELL_RNG_CACHE
    _CELL_RNG_CACHE.clear()
    _CELL_TO_INDEX.clear()
    parent_ss = np.random.SeedSequence(RNG_SEED)
    _CHILDREN = list(parent_ss.spawn(len(sorted_labels)))
    for i, label in enumerate(sorted_labels):
        _CELL_TO_INDEX[label] = i
        _CELL_RNG_CACHE[label] = np.random.default_rng(_CHILDREN[i])


def _spawn_rng(label: str) -> np.random.Generator:
    """Look up the per-cell RNG by label. If the streams haven't been built yet,
    return a no-op default_rng (placeholder; compute_all builds them first)."""
    cached = _CELL_RNG_CACHE.get(label)
    if cached is not None:
        return cached
    return _GLOBAL_RNG


def reset_registry() -> None:
    """For tests that build stats fresh."""
    _CELL_RNG_CACHE.clear()
    _CELL_TO_INDEX.clear()
    _CHILDREN.clear()


# ---------------------------------------------------------------------- index
class MonthIndex:
    """Pre-built month→row-indices map for one (variant, era, column) subset."""

    def __init__(self, panel: pd.DataFrame, variant: str, era: str, col: str):
        self.variant = variant
        self.era = era
        self.col = col
        m = (panel["variant"] == variant) & (panel["era"] == era)
        if not m.any():
            self.row_idx = np.array([], dtype=np.int64)
            self.months = np.array([], dtype="U7")
            self.vals = np.array([], dtype=np.float64)
            self._sorted_months = np.array([], dtype="U7")
            self._month_to_rows = {}
            return
        sub = panel.loc[m]
        self.row_idx = sub.index.to_numpy()
        self.months = sub["entry_month"].to_numpy()
        self.vals = sub[col].to_numpy(dtype=np.float64)
        unique_months = np.sort(pd.unique(self.months))
        self._sorted_months = unique_months
        self._month_to_rows = {m_label: np.flatnonzero(self.months == m_label)
                               for m_label in unique_months}

    @property
    def sorted_months(self) -> np.ndarray:
        return self._sorted_months

    def n_months(self) -> int:
        return len(self._sorted_months)

    def n_events(self) -> int:
        return len(self.row_idx)

    def n_names(self, panel: pd.DataFrame) -> int:
        if len(self.row_idx) == 0:
            return 0
        return int(panel.loc[self.row_idx, "name"].nunique())

    def point_mean(self) -> float:
        v = self.vals[np.isfinite(self.vals)]
        return float(v.mean()) if len(v) else float("nan")

    def bootstrap(self, rng: np.random.Generator, n_bootstrap: int = N_BOOTSTRAP):
        """Month-cluster bootstrap. Returns (point, lo, hi)."""
        point = self.point_mean()
        months = self._sorted_months
        if len(months) == 0:
            return float(point), float("nan"), float("nan")
        per_month_sum = np.zeros(len(months), dtype=np.float64)
        per_month_count = np.zeros(len(months), dtype=np.int64)
        for i, m_label in enumerate(months):
            rows = self._month_to_rows[m_label]
            v = self.vals[rows]
            finite = np.isfinite(v)
            per_month_count[i] = int(finite.sum())
            per_month_sum[i] = float(v[finite].sum()) if per_month_count[i] else 0.0

        means = np.empty(n_bootstrap, dtype=np.float64)
        for b in range(n_bootstrap):
            drawn = rng.integers(0, len(months), size=len(months))
            ts = per_month_sum[drawn].sum()
            tc = per_month_count[drawn].sum()
            means[b] = ts / tc if tc > 0 else float("nan")
        means = means[np.isfinite(means)]
        if len(means) == 0:
            return float(point), float("nan"), float("nan")
        lo, hi = np.percentile(means, [2.5, 97.5])
        return float(point), float(lo), float(hi)


def _mi_from_subset(sub: pd.DataFrame, col: str) -> MonthIndex:
    """Construct an ad-hoc MonthIndex from a pre-filtered subset."""
    mi = MonthIndex.__new__(MonthIndex)
    mi.row_idx = sub.index.to_numpy()
    mi.months = sub["entry_month"].to_numpy()
    mi.vals = sub[col].to_numpy(dtype=np.float64)
    mi._sorted_months = np.sort(pd.unique(mi.months))
    mi._month_to_rows = {m_label: np.flatnonzero(mi.months == m_label)
                         for m_label in mi._sorted_months}
    return mi


def _build_indices(panel: pd.DataFrame):
    indices = {}
    for v in VARIANTS:
        for era in ERAS:
            for col in (H10, H21):
                indices[(v, era, col)] = MonthIndex(panel, v, era, col)
    return indices


def _variant_stats(panel, indices, variant):
    sub = panel[panel["variant"] == variant]
    rng = _spawn_rng(f"variant:{variant}")

    overall = {}
    for col, label in [(H10, "h10"), (H21, "h21")]:
        all_mi = _mi_from_subset(sub, col)
        point, lo, hi = all_mi.bootstrap(rng)
        overall[f"mean_{label}_net"] = point
        overall[f"ci_{label}"] = [lo, hi]
    overall["n_events"] = int(len(sub))
    overall["n_months"] = int(sub["entry_month"].nunique())
    overall["n_names"] = int(sub["name"].nunique())
    overall["hit_rate_h10"] = float((sub[H10] > 0).mean()) if len(sub) else float("nan")
    overall["median_mfe21"] = float(sub["mfe21"].dropna().median()) if sub["mfe21"].notna().any() else float("nan")
    overall["median_mae21"] = float(sub["mae21"].dropna().median()) if sub["mae21"].notna().any() else float("nan")

    by_era = {}
    for era in ERAS:
        era_d = {}
        for col, label in [(H10, "h10"), (H21, "h21")]:
            mi = indices[(variant, era, col)]
            point, lo, hi = mi.bootstrap(rng)
            era_d[f"mean_{label}_net"] = point
            era_d[f"ci_{label}"] = [lo, hi]
        esub = sub[sub["era"] == era]
        era_d["n_events"] = int(len(esub))
        era_d["n_months"] = int(esub["entry_month"].nunique())
        era_d["n_names"] = int(esub["name"].nunique())
        era_d["hit_rate_h10"] = float((esub[H10] > 0).mean()) if len(esub) else float("nan")
        era_d["median_mfe21"] = float(esub["mfe21"].dropna().median()) if esub["mfe21"].notna().any() else float("nan")
        era_d["median_mae21"] = float(esub["mae21"].dropna().median()) if esub["mae21"].notna().any() else float("nan")
        by_era[era] = era_d
    return {"overall": overall, "by_era": by_era}


def _phase_dispersion(panel, indices, n_grain):
    """Phase dispersion for a grain (n_grain ∈ {2, 3}).

    Two events from different phases of the same grain are the SAME event when
    their 1D signal sessions lie within n_grain − 1 SPY sessions (G3: matched on
    SPY session POSITION with |Δpos| ≤ n-1, one-to-one greedy matching in date
    order within each name, divided by |A ∪ B| = |A| + |B| − matched). The exact-
    date Jaccard is mechanically 0 (different phases' bar end-dates never coincide)
    and is kept for the record (F13).
    """
    grain_variants = [f"{n_grain}D.p{i}" for i in range(n_grain)]
    rng = _spawn_rng(f"phase_dispersion:{n_grain}D")

    phase_mi = {}
    for v in grain_variants:
        sub = panel[panel["variant"] == v]
        phase_mi[v] = _mi_from_subset(sub, H10)

    means_h10 = {v: phase_mi[v].point_mean() for v in grain_variants}
    rng_val = max(means_h10.values()) - min(means_h10.values())

    # Exact-date Jaccard (mechanically 0 — phases' bar end-dates never coincide)
    sets_exact = {v: set(zip(panel.loc[panel["variant"] == v, "name"].astype(str),
                              panel.loc[panel["variant"] == v, "signal_date"].astype(str)))
                  for v in grain_variants}
    jacc_exact = {}
    for i in range(n_grain):
        for j in range(i + 1, n_grain):
            a, b = grain_variants[i], grain_variants[j]
            inter = len(sets_exact[a] & sets_exact[b])
            union = len(sets_exact[a] | sets_exact[b])
            jacc_exact[f"p{i}-p{j}"] = inter / union if union else float("nan")

    # G3: tolerant Jaccard on SPY session POSITION, |Δpos| ≤ n-1, one-to-one
    # greedy matching in date order within each name. Union = |A| + |B| − matched.
    # Build per-(variant, name) sorted-list of SPY session positions. signal_date
    # is on the SPY calendar (events come from the inner-joined close_1d).
    rel_pos = {}
    for v in grain_variants:
        sub = panel[panel["variant"] == v][["name", "signal_date"]].copy()
        sub["spy_pos"] = session_anchor.session_positions(
            pd.DatetimeIndex(sub["signal_date"]), market="US")
        rel_pos[v] = sub

    def _greedy_match(df_a: pd.DataFrame, df_b: pd.DataFrame, tol: int) -> tuple[int, int]:
        """Greedy one-to-one matching by date order. Returns (matched, union)."""
        sa = df_a.sort_values(["name", "signal_date"]).reset_index(drop=True)
        sb = df_b.sort_values(["name", "signal_date"]).reset_index(drop=True)
        b_used = np.zeros(len(sb), dtype=bool)
        # group sb by name for fast candidate lookup
        sb_by_name: dict[str, np.ndarray] = {}
        sb_pos_by_name: dict[str, np.ndarray] = {}
        for nm, group in sb.groupby("name"):
            sb_by_name[nm] = group.index.to_numpy()
            sb_pos_by_name[nm] = group["spy_pos"].to_numpy()
        matched = 0
        for _, row_a in sa.iterrows():
            nm = row_a["name"]
            pa = int(row_a["spy_pos"])
            cand = sb_by_name.get(nm)
            if cand is None:
                continue
            free = ~b_used[cand]
            cand_free_idx = cand[free]
            if len(cand_free_idx) == 0:
                continue
            pos_arr = sb_pos_by_name[nm][free]
            dpos = np.abs(pos_arr - pa)
            in_tol = np.where(dpos <= tol)[0]
            if len(in_tol) == 0:
                continue
            best = in_tol[np.argmin(dpos[in_tol])]
            b_used[cand_free_idx[best]] = True
            matched += 1
        union = len(sa) + len(sb) - matched
        return matched, union

    tol = n_grain - 1
    jacc_tol = {}
    for i in range(n_grain):
        for j in range(i + 1, n_grain):
            a, b = grain_variants[i], grain_variants[j]
            matched, union = _greedy_match(rel_pos[a], rel_pos[b], tol)
            jacc_tol[f"p{i}-p{j}"] = matched / union if union else float("nan")

    pooled = pd.concat([panel[panel["variant"] == v] for v in grain_variants], ignore_index=True)
    pooled_mi = _mi_from_subset(pooled, H10)
    pooled_mean, lo_c, hi_c = pooled_mi.bootstrap(rng)
    ci_width = (hi_c - lo_c) if (np.isfinite(hi_c) and np.isfinite(lo_c)) else float("nan")
    fragile = bool(np.isfinite(rng_val) and np.isfinite(ci_width) and (rng_val > ci_width))

    return {
        "range_h10": float(rng_val),
        "jaccard": jacc_exact,                # exact-date Jaccard (mechanically 0)
        "jaccard_tolerant": jacc_tol,          # tolerant Jaccard (G3: session position)
        "jaccard_tolerance_sessions": n_grain - 1,
        "pooled_mean_h10": float(pooled_mean),
        "pooled_ci": [float(lo_c), float(hi_c)],
        "fragile": fragile,
        "means_by_phase": means_h10,
    }


# ----- paired delta bootstrap (used for contrasts + verdict) ------------------
def _paired_arrays(panel, a_variant, b_variant, era, col):
    """Build per-month sum/count for variant a and variant b in era, on column col.
    `era=None` means overall (across both eras). Returns
    (all_months_sorted, a_sum, a_cnt, b_sum, b_cnt, a_n, b_n).
    """
    if era is None:
        a_sub = panel[panel["variant"] == a_variant]
        b_sub = panel[panel["variant"] == b_variant]
    else:
        a_sub = panel[(panel["variant"] == a_variant) & (panel["era"] == era)]
        b_sub = panel[(panel["variant"] == b_variant) & (panel["era"] == era)]
    all_months = np.union1d(a_sub["entry_month"].unique(), b_sub["entry_month"].unique())
    all_months = np.sort(all_months)
    a_months_arr = a_sub["entry_month"].to_numpy()
    a_vals = a_sub[col].to_numpy(dtype=np.float64)
    b_months_arr = b_sub["entry_month"].to_numpy()
    b_vals = b_sub[col].to_numpy(dtype=np.float64)

    def pack(months_arr, vals):
        sum_ = np.zeros(len(all_months), dtype=np.float64)
        cnt = np.zeros(len(all_months), dtype=np.int64)
        for i, m_label in enumerate(all_months):
            mask = months_arr == m_label
            if not mask.any():
                continue
            v = vals[mask]
            finite = np.isfinite(v)
            cnt[i] = int(finite.sum())
            sum_[i] = float(v[finite].sum()) if cnt[i] else 0.0
        return sum_, cnt

    a_sum, a_cnt = pack(a_months_arr, a_vals)
    b_sum, b_cnt = pack(b_months_arr, b_vals)
    a_total_n = int(a_cnt.sum())
    b_total_n = int(b_cnt.sum())
    return all_months, a_sum, a_cnt, b_sum, b_cnt, a_total_n, b_total_n


# L3: last bootstrap month-index draw from `_delta_bootstrap_pair` (tests only).
_LAST_PAIR_DRAWN: np.ndarray | None = None
_LAST_PAIR_N_CONSTANT_DRAWS: int = 0


def _delta_bootstrap_pair(panel, a_variant, b_variant, era, rng, col):
    """Δ(a − b) on `col` with shared month-cluster bootstrap (single era or overall)."""
    global _LAST_PAIR_DRAWN, _LAST_PAIR_N_CONSTANT_DRAWS
    (all_months, a_sum, a_cnt, b_sum, b_cnt, a_n, b_n) = _paired_arrays(
        panel, a_variant, b_variant, era, col)
    if len(all_months) == 0:
        _LAST_PAIR_DRAWN = None
        _LAST_PAIR_N_CONSTANT_DRAWS = 0
        return float("nan"), float("nan"), float("nan"), 0, 0
    a_total = a_sum.sum(); b_total = b_sum.sum()
    point = (a_total / a_n - b_total / b_n) if (a_n > 0 and b_n > 0) else float("nan")

    deltas = np.empty(N_BOOTSTRAP, dtype=np.float64)
    n_constant = 0
    first_drawn = None
    for k in range(N_BOOTSTRAP):
        drawn = rng.integers(0, len(all_months), size=len(all_months))
        if k == 0:
            first_drawn = np.asarray(drawn).copy()
        if len(drawn) > 0 and np.all(np.asarray(drawn) == np.asarray(drawn)[0]):
            n_constant += 1
        sa = a_sum[drawn].sum(); ca = a_cnt[drawn].sum()
        sb = b_sum[drawn].sum(); cb = b_cnt[drawn].sum()
        ma = sa / ca if ca > 0 else float("nan")
        mb = sb / cb if cb > 0 else float("nan")
        deltas[k] = ma - mb
    _LAST_PAIR_DRAWN = first_drawn
    _LAST_PAIR_N_CONSTANT_DRAWS = int(n_constant)
    deltas = deltas[np.isfinite(deltas)]
    if len(deltas) == 0:
        return float(point), float("nan"), float("nan"), a_n, b_n
    lo, hi = np.percentile(deltas, [2.5, 97.5])
    return float(point), float(lo), float(hi), a_n, b_n


# ----- one cell's RNG keyed by a stable label --------------------------------
def _cell_rng(scope: str, a_variant: str, b_variant: str, era: str, col: str) -> np.random.Generator:
    label = f"{scope}|{a_variant}|{b_variant}|{era}|{col}"
    return _spawn_rng(label)


# ----- verdict rule ----------------------------------------------------------
def _compute_verdict(panel):
    """Compute the three verdicts. F10: keeps details through the disagreement
    case and uses an explicit "≥ 2 qualifying phases agree in sign" rule.

    grain_effect_3d REAL iff ≥ 2 phases of 3D.p − 1D.M3 each have BOTH eras with
    the SAME sign AND a CI excluding zero, AND those ≥ 2 qualifying phases all
    share a common sign among themselves. The 2-agree-1-dissent case counts as
    REAL with the 2-phase qualifying_sign set, and the dissenting phase is
    reported in details with ok=False.
    """
    out = {}

    def real_for_n(n_grain, mem_var):
        phases = list(range(n_grain))
        meets = 0
        qualifying_sign = None  # common sign across qualifying phases
        details = []
        per_phase_ok = []
        for p in phases:
            var = f"{n_grain}D.p{p}"
            era_results = {}
            both_sign_within = True
            in_phase_sign = None
            for era in ERAS:
                rng_local = _cell_rng("verdict", var, mem_var, era, H10)
                delta, lo, hi, na, nb = _delta_bootstrap_pair(panel, var, mem_var, era, rng_local, H10)
                excludes = (lo > 0) or (hi < 0) if np.isfinite(lo) and np.isfinite(hi) else False
                era_results[era] = {
                    "delta": float(delta) if np.isfinite(delta) else float("nan"),
                    "ci": [float(lo) if np.isfinite(lo) else float("nan"),
                           float(hi) if np.isfinite(hi) else float("nan")],
                    "excludes_zero": bool(excludes),
                    "a_n_events": int(na), "b_n_events": int(nb),
                }
                if not np.isfinite(delta):
                    both_sign_within = False
                    continue
                if in_phase_sign is None:
                    in_phase_sign = delta > 0
                elif (delta > 0) != in_phase_sign:
                    both_sign_within = False
            # within-phase: both eras must agree on sign AND both must exclude zero
            ok_within = (both_sign_within
                         and all(era_results[e]["excludes_zero"] for e in ERAS)
                         and in_phase_sign is not None)
            per_phase_ok.append(ok_within)
            details.append({"variant": var, "ok": bool(ok_within),
                            "in_phase_sign": (None if in_phase_sign is None else bool(in_phase_sign)),
                            "era_results": era_results})
            if ok_within:
                # the qualifying sign within this phase
                if qualifying_sign is None:
                    qualifying_sign = in_phase_sign
                    meets = 1
                elif in_phase_sign == qualifying_sign:
                    meets += 1
                else:
                    # 2-agree-1-dissent case (F10): dissenting phase stays in
                    # details with ok=False, the qualifying_sign is the SIGN of the
                    # AGREEING phases (not zeroed). 2 qualifies → REAL still possible.
                    pass
        # meets must be ≥ 2 of n_grain and qualifying_sign must be set
        ok_real = (meets >= 2) and (qualifying_sign is not None)
        if qualifying_sign is not None:
            # F10: mark dissenting phases (ok_within=True but sign disagrees with
            # qualifying_sign) as ok=False in details, so the reader sees only the
            # phases that qualified for the verdict.
            for d in details:
                if (d["ok"] is True
                        and d["in_phase_sign"] is not None
                        and d["in_phase_sign"] != qualifying_sign):
                    d["ok"] = False
        return ("REAL" if ok_real
                else _not_supported_or_insufficient(panel, n_grain, mem_var, details)), details

    grain_3d, details_3d = real_for_n(3, "1D.M3")
    grain_2d, details_2d = real_for_n(2, "1D.M2")

    # memory (1D.M3 - 1D): one phase, both eras (D9: same sign in both eras AND both exclude zero)
    mem_details = []
    mem_era_results = {}
    mem_sign = None
    for era in ERAS:
        rng_local = _cell_rng("verdict", "1D.M3", "1D", era, H10)
        delta, lo, hi, na, nb = _delta_bootstrap_pair(panel, "1D.M3", "1D", era, rng_local, H10)
        excl = (lo > 0) or (hi < 0) if (np.isfinite(lo) and np.isfinite(hi)) else False
        mem_era_results[era] = {"delta": float(delta) if np.isfinite(delta) else float("nan"),
                                "ci": [float(lo) if np.isfinite(lo) else float("nan"),
                                       float(hi) if np.isfinite(hi) else float("nan")],
                                "excludes_zero": bool(excl),
                                "a_n_events": int(na), "b_n_events": int(nb)}
        if np.isfinite(delta):
            if mem_sign is None:
                mem_sign = delta > 0
            elif (delta > 0) != mem_sign:
                mem_sign = None  # disagrees
    ok_mem = (mem_sign is not None
              and all(mem_era_results[e]["excludes_zero"] for e in ERAS))
    mem_details.append({"variant": "1D.M3_vs_1D", "ok": bool(ok_mem),
                        "in_phase_sign": (None if mem_sign is None else bool(mem_sign)),
                        "era_results": mem_era_results})
    memory_3 = "REAL" if ok_mem else _not_supported_or_insufficient(panel, None, "1D.M3", mem_details)

    return {
        "grain_effect_3d": grain_3d,
        "grain_effect_2d": grain_2d,
        "memory_effect_3": memory_3,
        "rule": ("grain_effect_3d REAL iff Δ(3D.p − 1D.M3) on H10_net has the same sign and "
                 "CI excludes zero in BOTH eras for ≥ 2 of the 3 phases, AND the qualifying "
                 "phases all share a common sign. grain_effect_2d same rule on "
                 "Δ(2D.p − 1D.M2), requiring BOTH phases. memory_effect_3 same on "
                 "Δ(1D.M3 − 1D) (one phase, both eras, same sign in both eras and both "
                 "CIs exclude zero)."),
        "details": {
            "grain_effect_3d": details_3d,
            "grain_effect_2d": details_2d,
            "memory_effect_3": mem_details,
        },
    }


def _cell_n_events(panel, names_set, era):
    sub = panel[(panel["variant"].isin(names_set)) & (panel["era"] == era)]
    return int(len(sub)), int(sub["entry_month"].nunique()) if len(sub) else 0


def _not_supported_or_insufficient(panel, n_grain, mem_var, details):
    """NOT SUPPORTED iff every phase has at least one zero-including CI AND every cell
    of BOTH arms (variant and mem_var × both eras) has n_events ≥ 300 and n_months ≥ 24.
    INSUFFICIENT otherwise.
    """
    if n_grain is None:
        # memory_effect_3: arm = {1D.M3, 1D} × both eras
        arms = [("1D.M3",), ("1D",)]
    else:
        arms = [(f"{n_grain}D.p{p}",) for p in range(n_grain)] + [(mem_var,)]

    for v_tuple in arms:
        for era in ERAS:
            sub = panel[(panel["variant"] == v_tuple[0]) & (panel["era"] == era)]
            if len(sub) < 300 or sub["entry_month"].nunique() < 24:
                return "INSUFFICIENT"

    if not details:
        return "INSUFFICIENT"
    for d in details:
        er = d.get("era_results", {})
        any_includes = False
        for era in ERAS:
            r = er.get(era)
            if r is None:
                continue
            lo, hi = r["ci"]
            if not (np.isfinite(lo) and np.isfinite(hi)):
                continue
            if lo <= 0.0 <= hi:
                any_includes = True
                break
        if not any_includes:
            return "INSUFFICIENT"
    return "NOT SUPPORTED"


# ----- master compute ---------------------------------------------------------
def compute_pooled_delta(panel, a_variants: list[str], b_variant: str,
                          col: str = H10) -> dict:
    """F1: the pooled-across-phases Δ on `col`, computed with the SHARED month-cluster
    bootstrap (draw months once, compute both means, take the difference).

    Returns {"delta", "ci", "a_n_events", "b_n_events", "a_mean", "b_mean", "a_ci", "b_ci"}.
    """
    label = f"pooled_delta|{','.join(a_variants)}|{b_variant}|{col}"
    rng = _spawn_rng(label)
    a_sub = panel[panel["variant"].isin(a_variants)]
    b_sub = panel[panel["variant"] == b_variant]

    # union of months
    all_months = np.union1d(a_sub["entry_month"].unique(), b_sub["entry_month"].unique())
    all_months = np.sort(all_months)
    a_months_arr = a_sub["entry_month"].to_numpy()
    a_vals = a_sub[col].to_numpy(dtype=np.float64)
    b_months_arr = b_sub["entry_month"].to_numpy()
    b_vals = b_sub[col].to_numpy(dtype=np.float64)

    def pack(months_arr, vals):
        sum_ = np.zeros(len(all_months), dtype=np.float64)
        cnt = np.zeros(len(all_months), dtype=np.int64)
        for i, m_label in enumerate(all_months):
            mask = months_arr == m_label
            if not mask.any():
                continue
            v = vals[mask]
            finite = np.isfinite(v)
            cnt[i] = int(finite.sum())
            sum_[i] = float(v[finite].sum()) if cnt[i] else 0.0
        return sum_, cnt

    a_sum, a_cnt = pack(a_months_arr, a_vals)
    b_sum, b_cnt = pack(b_months_arr, b_vals)
    a_total = a_sum.sum(); a_n = int(a_cnt.sum())
    b_total = b_sum.sum(); b_n = int(b_cnt.sum())
    a_point = (a_total / a_n) if a_n > 0 else float("nan")
    b_point = (b_total / b_n) if b_n > 0 else float("nan")
    point = a_point - b_point if (np.isfinite(a_point) and np.isfinite(b_point)) else float("nan")

    deltas = np.empty(N_BOOTSTRAP, dtype=np.float64)
    means_a = np.empty(N_BOOTSTRAP, dtype=np.float64)
    means_b = np.empty(N_BOOTSTRAP, dtype=np.float64)
    for k in range(N_BOOTSTRAP):
        drawn = rng.integers(0, len(all_months), size=len(all_months))
        sa = a_sum[drawn].sum(); ca = a_cnt[drawn].sum()
        sb = b_sum[drawn].sum(); cb = b_cnt[drawn].sum()
        ma = sa / ca if ca > 0 else float("nan")
        mb = sb / cb if cb > 0 else float("nan")
        means_a[k] = ma
        means_b[k] = mb
        deltas[k] = (ma - mb) if (np.isfinite(ma) and np.isfinite(mb)) else float("nan")
    deltas = deltas[np.isfinite(deltas)]
    means_a = means_a[np.isfinite(means_a)]
    means_b = means_b[np.isfinite(means_b)]
    lo, hi = (np.percentile(deltas, [2.5, 97.5]) if len(deltas) else (float("nan"), float("nan")))
    a_lo, a_hi = (np.percentile(means_a, [2.5, 97.5]) if len(means_a) else (float("nan"), float("nan")))
    b_lo, b_hi = (np.percentile(means_b, [2.5, 97.5]) if len(means_b) else (float("nan"), float("nan")))
    return {
        "delta": float(point),
        "ci": [float(lo), float(hi)],
        "a_n_events": a_n,
        "b_n_events": b_n,
        "a_mean": float(a_point),
        "b_mean": float(b_point),
        "a_ci": [float(a_lo), float(a_hi)],
        "b_ci": [float(b_lo), float(b_hi)],
        "a_variants": list(a_variants),
        "b_variant": b_variant,
    }


def _collect_all_cell_labels() -> list[str]:
    """Enumerate every cell label that compute_all will request from _spawn_rng.

    The set is built once and passed to SeedSequence.spawn() so that distinct
    labels get distinct streams (G7). The list is sorted to make label → index
    deterministic across processes (encounter order was unsafe)."""
    labels = set()
    # variant stats
    for v in VARIANTS:
        labels.add(f"variant:{v}")
    # phase dispersion
    for n in (2, 3):
        labels.add(f"phase_dispersion:{n}D")
    # pooled deltas
    labels.add("pooled_delta|3D.p0,3D.p1,3D.p2|1D.M3|excess_h10_net")
    labels.add("pooled_delta|3D.p0,3D.p1,3D.p2|1D.M3|excess_h21_net")
    labels.add("pooled_delta|2D.p0,2D.p1|1D.M2|excess_h10_net")
    # verdict cells
    for n_grain, mem_var in [(3, "1D.M3"), (2, "1D.M2")]:
        for p in range(n_grain):
            for era in ERAS:
                for col in (H10, H21):
                    labels.add(f"verdict|{n_grain}D.p{p}|{mem_var}|{era}|{col}")
    for era in ERAS:
        labels.add(f"verdict|1D.M3|1D|{era}|{H10}")
        labels.add(f"verdict|1D.M3|1D|{era}|{H21}")
    # contrast cells
    contrast_pairs = []
    for p in range(3):
        contrast_pairs.append((f"3D.p{p}", "1D"))
        contrast_pairs.append((f"3D.p{p}", "1D.M3"))
    for p in range(2):
        contrast_pairs.append((f"2D.p{p}", "1D.M2"))
    contrast_pairs.append(("1D.M3", "1D"))
    contrast_pairs.append(("1D.M2", "1D"))
    contrast_pairs.append(("3D.K1", "3D.p0"))
    for va, vb in contrast_pairs:
        labels.add(f"contrast_overall|{va}|{vb}|ALL|{H10}")
        labels.add(f"contrast_overall_h21|{va}|{vb}|ALL|{H21}")
        for era in ERAS:
            labels.add(f"contrast_era|{va}|{vb}|{era}|{H10}")
            labels.add(f"contrast_era_h21|{va}|{vb}|{era}|{H21}")
    return sorted(labels)


def compute_all(panel, confirms):
    # G7: build sorted-cell streams ONCE before any bootstrap
    cell_labels = _collect_all_cell_labels()
    _build_cell_streams(cell_labels)
    print(f"building indices... ({len(cell_labels)} cell streams)", flush=True)
    indices = _build_indices(panel)

    print("per-variant stats...", flush=True)
    variants_out = {v: _variant_stats(panel, indices, v) for v in VARIANTS}

    print("phase dispersion...", flush=True)
    pd_2d = _phase_dispersion(panel, indices, 2)
    pd_3d = _phase_dispersion(panel, indices, 3)
    phase_dispersion = {
        "2D": {k: pd_2d[k] for k in pd_2d if k != "means_by_phase"},
        "3D": {k: pd_3d[k] for k in pd_3d if k != "means_by_phase"},
        "2D_means_by_phase": pd_2d["means_by_phase"],
        "3D_means_by_phase": pd_3d["means_by_phase"],
    }

    print("contrasts...", flush=True)
    contrasts_def = []
    for p in range(3):
        contrasts_def.append((f"3D.p{p}_minus_1D", f"3D.p{p}", "1D"))
        contrasts_def.append((f"3D.p{p}_minus_1D.M3", f"3D.p{p}", "1D.M3"))
    for p in range(2):
        contrasts_def.append((f"2D.p{p}_minus_1D.M2", f"2D.p{p}", "1D.M2"))
    contrasts_def.append(("1D.M3_minus_1D", "1D.M3", "1D"))
    contrasts_def.append(("1D.M2_minus_1D", "1D.M2", "1D"))
    contrasts_def.append(("3D.K1_minus_3D.p0", "3D.K1", "3D.p0"))

    contrasts_out = {}
    for name, va, vb in contrasts_def:
        # overall (across eras) — F9: n_months / n_names for BOTH arms
        rng_o = _cell_rng("contrast_overall", va, vb, "ALL", H10)
        d_h10, l_h10, h_h10, a_n_overall, b_n_overall = _delta_bootstrap_pair(
            panel, va, vb, None, rng_o, H10)
        rng_o21 = _cell_rng("contrast_overall_h21", va, vb, "ALL", H21)
        d_h21, l_h21, h_h21, _, _ = _delta_bootstrap_pair(
            panel, va, vb, None, rng_o21, H21)
        a_sub = panel[panel["variant"] == va]
        b_sub = panel[panel["variant"] == vb]
        overall = {
            "delta_h10": float(d_h10),
            "ci_h10": [float(l_h10), float(h_h10)],
            "delta_h21": float(d_h21),
            "ci_h21": [float(l_h21), float(h_h21)],
            "n_a_events_overall": int(a_n_overall),
            "n_b_events_overall": int(b_n_overall),
            "n_a_months_overall": int(a_sub["entry_month"].nunique()) if len(a_sub) else 0,
            "n_b_months_overall": int(b_sub["entry_month"].nunique()) if len(b_sub) else 0,
            "n_a_names_overall": int(a_sub["name"].nunique()) if len(a_sub) else 0,
            "n_b_names_overall": int(b_sub["name"].nunique()) if len(b_sub) else 0,
        }
        by_era = {}
        for era in ERAS:
            rng_e10 = _cell_rng("contrast_era", va, vb, era, H10)
            rng_e21 = _cell_rng("contrast_era_h21", va, vb, era, H21)
            dh10, lh10, hh10, an, bn = _delta_bootstrap_pair(panel, va, vb, era, rng_e10, H10)
            dh21, lh21, hh21, _, _ = _delta_bootstrap_pair(panel, va, vb, era, rng_e21, H21)
            a_esub = panel[(panel["variant"] == va) & (panel["era"] == era)]
            b_esub = panel[(panel["variant"] == vb) & (panel["era"] == era)]
            by_era[era] = {
                "delta_h10": float(dh10),
                "ci_h10": [float(lh10), float(hh10)],
                "delta_h21": float(dh21),
                "ci_h21": [float(lh21), float(hh21)],
                "n_a_events": int(an),
                "n_b_events": int(bn),
                "n_a_months": int(a_esub["entry_month"].nunique()) if len(a_esub) else 0,
                "n_b_months": int(b_esub["entry_month"].nunique()) if len(b_esub) else 0,
                "n_a_names": int(a_esub["name"].nunique()) if len(a_esub) else 0,
                "n_b_names": int(b_esub["name"].nunique()) if len(b_esub) else 0,
            }
        contrasts_out[name] = {"overall": overall, "by_era": by_era}

    print("confirmation summary...", flush=True)
    confirm_out = {}
    for v in ["2D.p0", "2D.p1", "3D.p0", "3D.p1", "3D.p2"]:
        sub = confirms[confirms["variant"] == v]
        if len(sub) == 0:
            confirm_out[v] = {"n": 0, "no_confirmation_share": float("nan"),
                              "median_delay": float("nan"), "mean_cost_pct": float("nan"),
                              "mean_mfe_consumed": float("nan")}
            continue
        nc_share = float(sub["no_confirmation"].mean())
        med_delay = float(sub["delay_sessions"].dropna().median()) if sub["delay_sessions"].notna().any() else float("nan")
        mean_cost = float(sub["confirmation_cost_pct"].dropna().mean()) if sub["confirmation_cost_pct"].notna().any() else float("nan")
        mean_consumed = float(sub["mfe21_consumed_frac"].dropna().mean()) if sub["mfe21_consumed_frac"].notna().any() else float("nan")
        confirm_out[v] = {
            "n": int(len(sub)),
            "no_confirmation_share": nc_share,
            "median_delay": med_delay,
            "mean_cost_pct": mean_cost,
            "mean_mfe_consumed": mean_consumed,
        }

    print("verdict...", flush=True)
    verdict = _compute_verdict(panel)

    print("pooled deltas (F1)...", flush=True)
    pooled_deltas = {
        "3D_pool_minus_1D.M3": compute_pooled_delta(
            panel, ["3D.p0", "3D.p1", "3D.p2"], "1D.M3", H10),
        "3D_pool_minus_1D.M3_h21": compute_pooled_delta(
            panel, ["3D.p0", "3D.p1", "3D.p2"], "1D.M3", H21),
        "2D_pool_minus_1D.M2": compute_pooled_delta(
            panel, ["2D.p0", "2D.p1"], "1D.M2", H10),
    }

    return {
        "variants": variants_out,
        "phase_dispersion": phase_dispersion,
        "contrasts": contrasts_out,
        "confirmation": confirm_out,
        "verdict": verdict,
        "pooled_deltas": pooled_deltas,
    }


if __name__ == "__main__":
    import time
    print("loading panel...", flush=True)
    panel = pd.read_parquet(RESULTS_DIR / "events_panel.parquet")
    confirms = pd.read_parquet(RESULTS_DIR / "confirmation_pairs.parquet")
    print(f"panel: {len(panel)}, confirms: {len(confirms)}", flush=True)
    t0 = time.time()
    out = compute_all(panel, confirms)
    print(f"computed in {time.time()-t0:.1f}s", flush=True)
    (RESULTS_DIR / "result_partial.json").write_text(json.dumps(out, indent=2, default=str))
    print("wrote result_partial.json", flush=True)