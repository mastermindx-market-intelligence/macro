"""Lane E — regime join, spread / interaction statistic, bootstrap, verdict.

Pre-declared design:
    join : merge_asof backward, allow_exact_matches=False (≤ 7d fallback window)
    partitions: P1 growth (EXPANSION if growth_score > 0 else CONTRACTION)
                P2 stress (STRESSED if n_flags ≥ 1 else CALM)
                P3 quad (Q1/Q2/Q3/Q4) — DESCRIPTIVE ONLY
    statistic per family f, partition P:
        spread(f, S) = mean(y | T3, S) − mean(y | T1, S)
        I(f, P) = spread(f, A) − spread(f, B)      (A = EXPANSION or STRESSED)
    inference: entry-month cluster bootstrap, 1,000 draws,
               SeedSequence(20261004).spawn-derived stable RNG (no builtin
               hashing), months drawn WITH replacement and weighted by
               multiplicity (np.bincount). Pairing holds within a test.
    Holm step-down on the 12 primary tests (6 families × 2 partitions) at α=0.05
    verdict rule in VERDICT_RULE (also written to result.json before compute)

Outcome: excess_h10_net (primary), excess_h21_net (secondary), confirmed 3D.p0
events (secondary set, no_confirmation == False).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


FLOOR_MONTHS = 24
FLOOR_NAMES = 100
FLOOR_EVENTS = 300
ERAS = ("2014-2019", "2020-2026")
TERCILES_I = ("T1", "T3")


VERDICT_RULE = (
    "Pre-declared rule (Lane E):\n"
    "  For each (family f, partition P) in 6×2 = 12 primary tests:\n"
    "    I(f, P) = [mean(y | T3, A) − mean(y | T1, A)] − [mean(y | T3, B) − mean(y | T1, B)]\n"
    "    where (A, B) = (EXPANSION, CONTRACTION) for P1 growth or (STRESSED, CALM) for P2 stress.\n"
    "    y = excess_h10_net on the PRIMARY event set (variant == '1D').\n"
    "  WINNER(S): every (f, P) with Holm-adjusted p < 0.05 on H10 net,\n"
    "    the same sign of I in both eras (2014-2019 and 2020-2026),\n"
    "    AND all cells above floor (≥ 24 months, ≥ 100 names, ≥ 300 events, both eras present)\n"
    "    — floors are evaluated on the eight (tercile ∈ {T1,T3}) × (state) × (era) cells,\n"
    "    ranked by |I|/SE.\n"
    "  SCOPED NULL: no (f, P) meets the winner rule AND at least 8 of 12 tests had all cells above floor.\n"
    "  INSUFFICIENT SUPPORT: fewer than 8 of 12 tests had all cells above floor, OR the B1 repaired panel is absent.\n"
    "Holm step-down over the 12 primary tests at α = 0.05; report raw and adjusted p."
)


# ───────────────────────────────────────────────────────────────── #
# Regime join (also used by the secondary 3D.p0-confirmed set)
# ───────────────────────────────────────────────────────────────── #
def join_regime(
    events: pd.DataFrame,
    regime: pd.DataFrame,
    *,
    fallback_max_days: int = 7,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """merge_asof backward, allow_exact_matches=False on (signal_date, regime.index).

    Returns (joined, drops):
      joined has cols 'growth_state', 'stress_state', 'quad', 'recession',
      'transition_ratcheted'
      drops has cols ['reason', 'n']
    """
    ev = events.copy()
    ev["signal_date"] = pd.to_datetime(ev["signal_date"]).dt.normalize()

    rg = regime[["growth_score", "n_flags", "quad", "recession", "transition_ratcheted"]].copy()
    rg.index = pd.to_datetime(rg.index).normalize()
    rg = rg[~rg.index.duplicated(keep="last")].sort_index()
    rg_reset = rg.reset_index()
    rg_reset.columns = ["_rg_date"] + list(rg.columns)
    rg_reset["_rg_date"] = rg_reset["_rg_date"].astype("datetime64[ns]")

    ev_sorted = ev.sort_values("signal_date").reset_index()
    ev_sorted = ev_sorted.rename(columns={ev_sorted.columns[0]: "_ev_idx"})
    j = pd.merge_asof(
        ev_sorted, rg_reset,
        left_on="signal_date", right_on="_rg_date",
        direction="backward", allow_exact_matches=False,
    )
    j["_age_days"] = (j["signal_date"] - j["_rg_date"]).dt.days

    too_old = j["_age_days"] > fallback_max_days
    miss = j["growth_score"].isna() | j["_rg_date"].isna()

    # K12: regime series ends 2026-07-02; events after that fall into too_old.
    regime_end = rg.index.max()
    past_end = j["signal_date"] > (regime_end + pd.Timedelta(days=fallback_max_days))

    drops = pd.DataFrame([
        {"reason": "no_prior_regime_row", "n": int(miss.sum())},
        {"reason": "match_older_than_7d", "n": int(too_old.sum())},
        {"reason": "regime_series_ended_late_2026", "n": int((too_old & past_end).sum())},
    ])

    keep = (~miss) & (~too_old)
    out = j.loc[keep].copy()

    out["growth_state"] = np.where(out["growth_score"] > 0, "EXPANSION", "CONTRACTION")
    out["stress_state"] = np.where(out["n_flags"] >= 1, "STRESSED", "CALM")

    out = out.set_index("_ev_idx")
    out.index.name = None
    return out, drops


# ───────────────────────────────────────────────────────────────── #
# Spread and interaction
# ───────────────────────────────────────────────────────────────── #
def cell_mean(
    df: pd.DataFrame,
    *,
    tercile_col: str = "tercile",
    state_col: str = "state",
    outcome_col: str = "y",
) -> pd.DataFrame:
    """Return per (tercile × state) cell: mean_y, n_events, n_months, n_names."""
    sub = df.dropna(subset=[tercile_col, state_col, outcome_col])
    g = sub.groupby([tercile_col, state_col], observed=True)
    out = g.agg(
        mean_y=(outcome_col, "mean"),
        n_events=(outcome_col, "size"),
        n_months=("entry_month", "nunique"),
        n_names=("name", "nunique"),
    ).reset_index()
    return out


def interaction_from_means(means: dict, state_a: str, state_b: str) -> float:
    """I = (mean T3A − mean T1A) − (mean T3B − mean T1B)."""
    keys = [(state_a, "T3"), (state_a, "T1"), (state_b, "T3"), (state_b, "T1")]
    if any(k not in means or not np.isfinite(means[k]) for k in keys):
        return float("nan")
    return float((means[(state_a, "T3")] - means[(state_a, "T1")]) -
                 (means[(state_b, "T3")] - means[(state_b, "T1")]))


def observed_I(df: pd.DataFrame, state_a: str, state_b: str,
               *, state_col: str = "state", outcome_col: str = "y") -> float:
    cell = cell_mean(df, state_col=state_col, outcome_col=outcome_col)
    by_key = {(row["state"], row["tercile"]): row["mean_y"]
              for _, row in cell.iterrows()}
    return interaction_from_means(by_key, state_a, state_b)


def era_I(df: pd.DataFrame, state_a: str, state_b: str,
          *, state_col: str = "state", outcome_col: str = "y") -> dict[str, float]:
    out: dict[str, float] = {}
    for era in ERAS:
        sub = df[df["era"] == era]
        out[era] = observed_I(sub, state_a, state_b,
                              state_col=state_col, outcome_col=outcome_col)
    return out


# ───────────────────────────────────────────────────────────────── #
# Floor gate — eight (T1/T3 × state × era) cells (K1)
# ───────────────────────────────────────────────────────────────── #
def _cell_ok(n_events: int, n_months: int, n_names: int) -> bool:
    return (n_events >= FLOOR_EVENTS and
            n_months >= FLOOR_MONTHS and
            n_names >= FLOOR_NAMES)


def floor_gate_eight_cells(
    df: pd.DataFrame,
    state_a: str,
    state_b: str,
    *,
    tercile_col: str = "tercile",
    state_col: str = "state",
    outcome_col: str = "y",
    era_col: str = "era",
) -> tuple[bool, list[dict], list[str]]:
    """Evaluate floors on the eight (T1/T3) × (state A/B) × (two eras) cells.

    Returns (floor_pass, cell_details, failing_cell_names).
    A missing cell is a failing cell. T2 is ignored.
    """
    sub = df.dropna(subset=[tercile_col, state_col, outcome_col, era_col]).copy()
    cells: list[dict] = []
    failing: list[str] = []
    for terc in TERCILES_I:
        for st in (state_a, state_b):
            for era in ERAS:
                sl = sub[(sub[tercile_col] == terc) &
                         (sub[state_col] == st) &
                         (sub[era_col] == era)]
                n_events = int(len(sl))
                n_months = int(sl["entry_month"].nunique()) if n_events else 0
                n_names = int(sl["name"].nunique()) if n_events else 0
                if n_events:
                    mean_y = float(sl[outcome_col].mean())
                else:
                    mean_y = float("nan")
                ok = _cell_ok(n_events, n_months, n_names)
                name = f"{era}/{terc}/{st}"
                rec = {
                    "cell_name": name,
                    "tercile": terc,
                    "state": st,
                    "era": era,
                    "n_events": n_events,
                    "n_months": n_months,
                    "n_names": n_names,
                    "mean_y": None if not np.isfinite(mean_y) else mean_y,
                    "above_floor": bool(ok),
                }
                cells.append(rec)
                if not ok:
                    failing.append(name)
    eras_present = all(era in set(sub[era_col].unique()) for era in ERAS)
    floor_pass = (len(failing) == 0) and (len(cells) == 8) and eras_present
    return bool(floor_pass), cells, failing


def floor_gate_pooled_six_MUTANT(
    df: pd.DataFrame,
    state_a: str,
    state_b: str,
    *,
    tercile_col: str = "tercile",
    state_col: str = "state",
    outcome_col: str = "y",
) -> tuple[bool, int]:
    """K1 mutant: pooled-era cells including T2, requiring cells_total == 6.

    This is the round-0 bug. Tests use it to prove the 8-cell gate is required.
    Production code must NOT call this.
    """
    cell_full = cell_mean(df, tercile_col=tercile_col, state_col=state_col,
                          outcome_col=outcome_col)
    cells_total = 0
    cells_above = 0
    for _, row in cell_full.iterrows():
        cells_total += 1
        if _cell_ok(int(row["n_events"]), int(row["n_months"]), int(row["n_names"])):
            cells_above += 1
    era_present = all(era in set(df["era"].unique()) for era in ERAS) if "era" in df.columns else True
    floor_pass = (cells_above == cells_total) and cells_total == 6 and era_present
    return bool(floor_pass), cells_total


# ───────────────────────────────────────────────────────────────── #
# Bootstrap: entry-month cluster WITH replacement, multiplicity weights (K2)
# ───────────────────────────────────────────────────────────────── #
def _month_cell_aggregates(
    df: pd.DataFrame,
    cells: list[tuple[str, str]],
    *,
    state_col: str,
    tercile_col: str,
    outcome_col: str,
    month_col: str = "entry_month",
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list]:
    """Return (months, sum_y [n_m × n_cells], cnt [n_m × n_cells], month_list)."""
    months = list(pd.Index(df[month_col].dropna().unique()))
    n_m = len(months)
    month_to_i = {m: i for i, m in enumerate(months)}
    e_mi = df[month_col].map(month_to_i).to_numpy()
    terc = df[tercile_col].to_numpy()
    st = df[state_col].to_numpy()
    y = df[outcome_col].to_numpy(dtype=float)
    n_c = len(cells)
    sum_y = np.zeros((n_m, n_c), dtype=float)
    cnt = np.zeros((n_m, n_c), dtype=float)
    valid = np.isfinite(e_mi.astype(float)) if n_m else np.zeros(len(df), dtype=bool)
    if n_m == 0:
        return np.array([]), sum_y, cnt, months
    e_mi_int = e_mi.astype(int)
    for j, (sv, tv) in enumerate(cells):
        mask = (st == sv) & (terc == tv) & np.isfinite(y)
        if not mask.any():
            continue
        np.add.at(sum_y[:, j], e_mi_int[mask], y[mask])
        np.add.at(cnt[:, j], e_mi_int[mask], 1.0)
    return e_mi_int, sum_y, cnt, months


def _I_from_month_weights(w: np.ndarray, sum_y: np.ndarray, cnt: np.ndarray) -> float:
    """I from 4-cell layout [A-T3, A-T1, B-T3, B-T1]."""
    n = w @ cnt
    if np.any(n <= 0):
        return float("nan")
    sy = w @ sum_y
    means = sy / n
    return float((means[0] - means[1]) - (means[2] - means[3]))


def cluster_bootstrap_I(
    df: pd.DataFrame,
    *,
    state_a: str,
    state_b: str,
    n_draws: int,
    rng: np.random.Generator,
    state_col: str = "state",
    tercile_col: str = "tercile",
    outcome_col: str = "y",
    mode: str = "weight",
) -> tuple[float, np.ndarray]:
    """Entry-month cluster bootstrap of I.

    mode:
      'weight' — WITH replacement, event/month weighted by draw multiplicity
                 (np.bincount). Production path (K2).
      'isin'   — unique-month keep mask (round-0 mutant; understates SE).
      'row'    — unclustered row-level resample (negative control).
      'keep_all' — every draw uses all months once (mutation B; SE ≈ 0).
    """
    cells = [(state_a, "T3"), (state_a, "T1"), (state_b, "T3"), (state_b, "T1")]
    e_mi, sum_y, cnt, months = _month_cell_aggregates(
        df, cells, state_col=state_col, tercile_col=tercile_col,
        outcome_col=outcome_col,
    )
    n_m = len(months)
    if n_m == 0:
        return float("nan"), np.full(n_draws, np.nan)

    w_ones = np.ones(n_m, dtype=float)
    obs = _I_from_month_weights(w_ones, sum_y, cnt)
    out = np.full(n_draws, np.nan)

    if mode == "weight":
        for k in range(n_draws):
            drawn = rng.integers(0, n_m, size=n_m)
            w = np.bincount(drawn, minlength=n_m).astype(float)
            out[k] = _I_from_month_weights(w, sum_y, cnt)
        return obs, out

    if mode == "isin":
        # Round-0 mutant: collapse duplicate month draws via unique membership.
        terc = df[tercile_col].to_numpy()
        st = df[state_col].to_numpy()
        y = df[outcome_col].to_numpy(dtype=float)
        for k in range(n_draws):
            drawn = rng.integers(0, n_m, size=n_m)
            uniq = np.unique(drawn)
            keep = np.isin(e_mi, uniq)
            means = {}
            for sv, tv in cells:
                m = keep & (st == sv) & (terc == tv) & np.isfinite(y)
                if m.any():
                    means[(sv, tv)] = float(y[m].mean())
            out[k] = interaction_from_means(means, state_a, state_b)
        return obs, out

    if mode == "row":
        terc = df[tercile_col].to_numpy()
        st = df[state_col].to_numpy()
        y = df[outcome_col].to_numpy(dtype=float)
        n = len(df)
        idx_all = np.arange(n)
        for k in range(n_draws):
            take = rng.integers(0, n, size=n)
            terc_k = terc[take]
            st_k = st[take]
            y_k = y[take]
            means = {}
            for sv, tv in cells:
                m = (st_k == sv) & (terc_k == tv) & np.isfinite(y_k)
                if m.any():
                    means[(sv, tv)] = float(y_k[m].mean())
            out[k] = interaction_from_means(means, state_a, state_b)
        return obs, out

    if mode == "keep_all":
        for k in range(n_draws):
            out[k] = obs
        return obs, out

    raise ValueError(f"unknown bootstrap mode {mode!r}")


def _bootstrap_interaction_for_family_partition(
    df: pd.DataFrame,
    *,
    state_col: str,
    outcome_col: str,
    state_a: str,
    state_b: str,
    n_draws: int,
    rng: np.random.Generator,
    mode: str = "weight",
) -> tuple[float, np.ndarray]:
    """Back-compat wrapper used by run.py and tests."""
    work = df
    if state_col != "state" and "state" not in df.columns:
        work = df.rename(columns={state_col: "state"})
        state_col = "state"
    elif state_col != "state":
        work = df.copy()
        work["state"] = df[state_col]
        state_col = "state"
    return cluster_bootstrap_I(
        work, state_a=state_a, state_b=state_b, n_draws=n_draws, rng=rng,
        state_col=state_col, outcome_col=outcome_col, mode=mode,
    )


def two_sided_p(obs: float, samples: np.ndarray) -> float:
    valid = samples[np.isfinite(samples)]
    if len(valid) < 50 or not np.isfinite(obs):
        return float("nan")
    if obs > 0:
        p = float((valid <= 0).mean() * 2.0)
    elif obs < 0:
        p = float((valid >= 0).mean() * 2.0)
    else:
        p = 1.0
    return float(min(p, 1.0))


def ci_se(samples: np.ndarray) -> tuple[float, float, float]:
    valid = samples[np.isfinite(samples)]
    if len(valid) < 50:
        return float("nan"), float("nan"), float("nan")
    return (float(np.percentile(valid, 2.5)),
            float(np.percentile(valid, 97.5)),
            float(valid.std(ddof=1)))


def cluster_bootstrap_mean(
    df: pd.DataFrame,
    *,
    n_draws: int,
    rng: np.random.Generator,
    outcome_col: str = "y",
    month_col: str = "entry_month",
) -> tuple[float, np.ndarray]:
    """Month-cluster mean of outcome_col (for regime main-effect context)."""
    months = list(pd.Index(df[month_col].dropna().unique()))
    n_m = len(months)
    if n_m == 0 or len(df) == 0:
        return float("nan"), np.full(n_draws, np.nan)
    month_to_i = {m: i for i, m in enumerate(months)}
    e_mi = df[month_col].map(month_to_i).to_numpy().astype(int)
    y = df[outcome_col].to_numpy(dtype=float)
    sum_y = np.zeros(n_m)
    cnt = np.zeros(n_m)
    mask = np.isfinite(y)
    np.add.at(sum_y, e_mi[mask], y[mask])
    np.add.at(cnt, e_mi[mask], 1.0)
    obs = float(sum_y.sum() / cnt.sum()) if cnt.sum() else float("nan")
    out = np.full(n_draws, np.nan)
    for k in range(n_draws):
        drawn = rng.integers(0, n_m, size=n_m)
        w = np.bincount(drawn, minlength=n_m).astype(float)
        n = float(w @ cnt)
        if n <= 0:
            continue
        out[k] = float(w @ sum_y) / n
    return obs, out


def analytic_cluster_se_equal_months(month_I: np.ndarray) -> float:
    """Analytic SE of the mean of equally-weighted month-level I values."""
    m = np.asarray(month_I, dtype=float)
    m = m[np.isfinite(m)]
    n = len(m)
    if n < 2:
        return float("nan")
    return float(m.std(ddof=1) / np.sqrt(n))


# ───────────────────────────────────────────────────────────────── #
# Holm step-down
# ───────────────────────────────────────────────────────────────── #
def holm(pvals: np.ndarray) -> np.ndarray:
    p = np.asarray(pvals, dtype=float)
    n = len(p)
    order = np.argsort(p)
    p_sorted = p[order]
    adj_sorted = np.empty(n, dtype=float)
    running_max = 0.0
    for i in range(n):
        scaled = (n - i) * p_sorted[i]
        running_max = max(running_max, scaled)
        adj_sorted[i] = min(running_max, 1.0)
    adj = np.empty(n, dtype=float)
    adj[order] = adj_sorted
    return adj


def apply_verdict(tests: list[dict]) -> tuple[str, list[str], list[dict], int]:
    """Mechanical winner / scoped-null / insufficient rule."""
    winners = []
    for t in tests:
        ph = t.get("p_holm")
        se = t.get("se")
        obs = t.get("observed")
        if (ph is not None and np.isfinite(ph) and ph < 0.05 and
                t.get("same_sign_eras") and t.get("floor_pass") and
                obs is not None and se is not None and
                np.isfinite(obs) and np.isfinite(se) and se > 0):
            winners.append({**t, "t_stat": abs(obs) / se})
    winners.sort(key=lambda w: -w["t_stat"])
    n_above = sum(1 for t in tests if t.get("floor_pass"))
    if len(winners) > 0:
        return "WINNERS", [f"{len(winners)} (f,P) meet all winner clauses"], winners, n_above
    if n_above >= 8:
        return ("SCOPED_NULL",
                ["no (f,P) meets the winner rule",
                 f"{n_above}/12 tests had all cells above floor"],
                winners, n_above)
    return ("INSUFFICIENT_SUPPORT",
            [f"only {n_above}/12 tests had all cells above floor (need ≥8)"],
            winners, n_above)
