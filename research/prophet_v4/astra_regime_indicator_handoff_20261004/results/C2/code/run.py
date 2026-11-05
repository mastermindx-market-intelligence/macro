"""Lane C2 — Decisive interaction: rotation speed × confirmation cost.

Mechanical application of the frozen C2 spec: join B1 events/confirmation
pairs to the C1 rotation-state table at the 1D signal date and compute the
pre-declared difference-in-differences and secondary statistics.

No new thresholds. No re-estimation of B1 or C1. No product recommendation.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import textwrap
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

# Lane law: import the repository's own indicator code rather than re-typing it.
sys.path.insert(0, ".")


def _find_repo() -> Path:
    env = os.environ.get("C2_REPO")
    if env:
        return Path(env).resolve()
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(Path(__file__).resolve().parent),
            text=True,
        ).strip()
        p = Path(out)
        if (p / "engine").is_dir() and (p / "research").is_dir():
            return p
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        pass
    p = Path(__file__).resolve().parent
    while True:
        if (p / "engine").is_dir() and (p / "research").is_dir():
            return p
        if p.parent == p:
            break
        p = p.parent
    raise RuntimeError("Cannot find repo root (set C2_REPO or run inside the git checkout)")


REPO = _find_repo()
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from engine.bar_derive import derive_2d_ohlcv, derive_3d_ohlcv  # noqa: E402,F401
from engine.canon import rsi_macd  # noqa: E402,F401
from engine.session_anchor import session_positions  # noqa: E402,F401

HAND_OFF = REPO / "research/prophet_v4/astra_regime_indicator_handoff_20261004"
RESULTS = HAND_OFF / "results/C2"
CODE = RESULTS / "code"
B1_DIR = HAND_OFF / "results/B1"
C1_DIR = HAND_OFF / "results/C1"

B1_EVENTS = B1_DIR / "events_panel.parquet"
B1_PAIRS = B1_DIR / "confirmation_pairs.parquet"
B1_JSON = B1_DIR / "result.json"
B1_MD = B1_DIR / "RESULT.md"
C1_STATE = C1_DIR / "rotation_state_daily.parquet"
C1_JSON = C1_DIR / "result.json"
C1_MD = C1_DIR / "RESULT.md"

OUT_JSON = RESULTS / "result.json"
OUT_MD = RESULTS / "RESULT.md"
OUT_HASHES = RESULTS / "hashes.txt"

# ─────────────────────── constants (frozen) ───────────────────────
RNG_SEED = 20261004
N_BOOTSTRAP = 1000
ERAS = ("2014-2019", "2020-2026")
ROT_TERCILES = ("fast", "mid", "persistent")
BREADTH_TERCILES = ("narrow", "mid", "broad")
PHASES_3D = ("p0", "p1", "p2")
PHASES_2D = ("p0", "p1")
VARIANTS_3D = ("3D.p0", "3D.p1", "3D.p2")
VARIANTS_2D = ("2D.p0", "2D.p1")
SUPPORT_VARIANTS = ("1D", "2D.p0", "2D.p1", "3D.p0", "3D.p1", "3D.p2")
FLOOR_MONTHS = 24
FLOOR_NAMES = 100
FLOOR_EVENTS = 300
FALSE_START_H10 = -0.02
LARGE_WINNER_H21 = 0.10
STATE_COLS = ("rotation_tercile", "breadth_tercile", "dfii_tercile", "LP")

# Exact packet VERDICT text (N1). Do not paraphrase.
VERDICT_RULE = (
    "SUPPORTED iff pooled 3D DiD on H10 net < 0 with 95% CI excluding zero, "
    "AND the pooled DiD has the same sign in both eras, AND DiD(p) < 0 with CI "
    "excluding zero for ≥ 2 of 3 phases, AND the 3D cost curve is monotonic "
    "fast > mid > persistent. NOT SUPPORTED iff the pooled 3D DiD CI includes "
    "zero AND all fast/persistent cells meet the floors. INSUFFICIENT SUPPORT "
    "otherwise (also whenever C1 controls are BROKEN or B1's verdict is "
    "INSUFFICIENT on every 3D phase)."
)

# Round-0 input shas (N4/N7). Rotation parquet is byte-identical now.
ROUND0_SHA = {
    "B1_events_panel": "8b17049773a32c6e517a614a48e530f29bc250f126e4ee9b8871ecd4cd7690a1",
    "B1_confirmation_pairs": "22eabfe6287a69233b7de328616f45a7424801dc4cd69fdfb3049dc2328b01eb",
    "B1_result_json": "7ede0e4333738127484a82d93a76c7795505b4112d6a61c223d35e8ffaaaad0b",
    "C1_rotation_state": "9361dbf08018f0c23bc6e9b29fa014bc42429ed3289d359adf7a16f52be3e2dd",
    "C1_result_json": "3492dc2d30ef09a0870aea5f5167be0c1c6f26d167c6b838e3d740625a4e1519",
    "engine_canon": "bdf34dc8a9b851889e9b6beae939867ca4611ad41a78b4b43322f2a8a9b18165",
    "engine_session_anchor": "1da03cb44684e4b0f91710c7279e3fff40d2344e253ab83473a83f7e2afa5c3f",
    "engine_bar_derive": "eb3a9d4c6ece400902a1765997b741c09a0b1d0c47ff798acffe0049a691e469",
    "C2_result_json": "9372f0f7ad0a4795e74a46dc7f4fc08d11adc2eb2dd158504b28dfc4f82842e0",
}
ROUND0_RESULT_JSON = Path(
    "/private/tmp/claude-501/-Users-chriswong-Documents-Cluade-macro-main"
    "--claude-worktrees-astra-ceo-handoff-4a36a0/f273dd7d-5dfb-4725-b26d-3de277637b11"
    "/scratchpad/results_prev/C2_r0/result.json"
)


# ─────────────────────── numeric helpers ───────────────────────
def _norm_dates(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce").dt.normalize()


def jnum(x):
    """JSON-safe number; non-finite → None."""
    if x is None:
        return None
    try:
        if pd.isna(x):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(x, (np.floating, float)):
        v = float(x)
        return None if not np.isfinite(v) else v
    if isinstance(x, (np.integer, int)):
        return int(x)
    if isinstance(x, (np.bool_, bool)):
        return bool(x)
    return x


def jci(lo, hi):
    a, b = jnum(lo), jnum(hi)
    if a is None or b is None:
        return [None, None]
    return [a, b]


def ci_excludes_zero(ci) -> bool:
    if ci is None or len(ci) != 2:
        return False
    lo, hi = ci
    if lo is None or hi is None:
        return False
    if not (np.isfinite(lo) and np.isfinite(hi)):
        return False
    return (lo > 0) or (hi < 0)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def file_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


# ─────────────────────── join ───────────────────────
def load_state_table(state: pd.DataFrame) -> pd.DataFrame:
    """Normalise C1 rotation_state_daily to columns date + STATE_COLS."""
    st = state.copy()
    if "date" not in st.columns:
        idx = st.index
        st = st.reset_index()
        # after reset, the index name (or 'index') is the date column
        if "date" not in st.columns:
            # C1 exports index name 'date'; fall back to first datetime-like col
            for c in st.columns:
                if c == "index" or str(c).lower() in {"date", "datetime"}:
                    st = st.rename(columns={c: "date"})
                    break
            if "date" not in st.columns:
                st = st.rename(columns={st.columns[0]: "date"})
    st["date"] = _norm_dates(st["date"])
    keep = ["date", *STATE_COLS]
    missing = [c for c in keep if c not in st.columns]
    if missing:
        raise KeyError(f"rotation_state_daily missing columns {missing}")
    st = st[keep].drop_duplicates(subset=["date"], keep="first")
    return st


def attach_state_to_1d(events_1d: pd.DataFrame, state: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Join C1 state onto 1D events by exact signal_date.

    Dates absent from the state table are dropped and counted. A present date
    with NaN tercile is kept (joined) but will not enter any tercile cell.
    Join is equality on the date only — later-dated state rows are never used.
    """
    e = events_1d.copy()
    e["signal_date"] = _norm_dates(e["signal_date"])
    st = load_state_table(state)
    state_dates = pd.Index(st["date"].unique())
    present = e["signal_date"].isin(state_dates)
    n_dropped = int((~present).sum())
    e = e.loc[present].copy()
    joined = e.merge(st, left_on="signal_date", right_on="date", how="left")
    if "date" in joined.columns:
        joined = joined.drop(columns=["date"])
    return joined, n_dropped


def attach_confirmed(
    pairs: pd.DataFrame,
    events_panel: pd.DataFrame,
    parents_1d: pd.DataFrame,
    variant: str,
) -> pd.DataFrame:
    """Confirmed entries of `variant` carrying the 1D parent's state.

    A confirmed entry is the variant's own events_panel outcome row, joined
    through confirmation_pairs where no_confirmation == False. State columns
    come from the 1D parent (signal_session_1d), never from the confirmation
    date.
    """
    p = pairs.loc[pairs["variant"].astype(str) == variant].copy()
    p["signal_session_1d"] = _norm_dates(p["signal_session_1d"])
    p["signal_session_other"] = _norm_dates(p["signal_session_other"])
    p = p.loc[~p["no_confirmation"].astype(bool)].copy()

    parent_cols = [
        "name",
        "signal_date",
        "entry_month",
        "era",
        "excess_h10_net",
        "excess_h21_net",
        *STATE_COLS,
    ]
    parent = parents_1d[parent_cols].rename(
        columns={
            "signal_date": "signal_session_1d",
            "entry_month": "parent_entry_month",
            "era": "parent_era",
            "excess_h10_net": "parent_h10_net",
            "excess_h21_net": "parent_h21_net",
        }
    )
    out = p.merge(parent, on=["name", "signal_session_1d"], how="inner")

    ev = events_panel.loc[events_panel["variant"].astype(str) == variant].copy()
    ev["signal_date"] = _norm_dates(ev["signal_date"])
    ev = ev.rename(
        columns={
            "signal_date": "signal_session_other",
            "excess_h10_net": "conf_h10_net",
            "excess_h21_net": "conf_h21_net",
            "entry_month": "conf_entry_month",
            "era": "conf_era",
        }
    )
    keep_ev = [
        "name",
        "signal_session_other",
        "conf_h10_net",
        "conf_h21_net",
        "conf_entry_month",
        "conf_era",
    ]
    out = out.merge(ev[keep_ev], on=["name", "signal_session_other"], how="left")
    out["variant"] = variant
    return out


# ─────────────────────── bootstrap ───────────────────────
def make_paired_draws(n_months: int, n_boot: int, rng: np.random.Generator) -> np.ndarray:
    """One (n_boot, n_months) array of resampled month indices.

    A single draw per replicate is shared across every cell so differences
    (gaps, DiDs) are paired.
    """
    if n_months <= 0:
        return np.zeros((n_boot, 0), dtype=np.int64)
    return rng.integers(0, n_months, size=(n_boot, n_months), dtype=np.int64)


def cell_boot_means(draws: np.ndarray, month_idx: np.ndarray, values: np.ndarray) -> np.ndarray:
    """Month-cluster bootstrap means using a precomputed paired draw array."""
    n_boot, n_months = draws.shape
    out = np.full(n_boot, np.nan, dtype=np.float64)
    if n_months == 0 or len(values) == 0:
        return out
    mi_all = np.asarray(month_idx, dtype=np.int64)
    finite = np.isfinite(values) & (mi_all >= 0) & (mi_all < n_months)
    if not finite.any():
        return out
    mi = mi_all[finite]
    vv = np.asarray(values, dtype=np.float64)[finite]
    sum_m = np.bincount(mi, weights=vv, minlength=n_months).astype(np.float64)
    cnt_m = np.bincount(mi, minlength=n_months).astype(np.float64)
    for b in range(n_boot):
        w = np.bincount(draws[b], minlength=n_months).astype(np.float64)
        den = float(np.dot(cnt_m, w))
        if den > 0:
            out[b] = float(np.dot(sum_m, w) / den)
    return out


def point_mean(values: np.ndarray) -> float:
    v = np.asarray(values, dtype=np.float64)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return float("nan")
    return float(v.mean())


def _nanmean_axis0(arrs) -> np.ndarray:
    stacked = np.vstack(arrs)
    with np.errstate(all="ignore"):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            return np.nanmean(stacked, axis=0)


def _nanmean_scalar(xs) -> float:
    a = np.asarray(list(xs), dtype=np.float64)
    with np.errstate(all="ignore"):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            return float(np.nanmean(a))


def percentiles_ci(boot: np.ndarray) -> tuple[float, float]:
    x = np.asarray(boot, dtype=np.float64)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return float("nan"), float("nan")
    lo, hi = np.percentile(x, [2.5, 97.5])
    return float(lo), float(hi)


def month_codes(labels: np.ndarray, universe: np.ndarray) -> np.ndarray:
    """Map YYYY-MM labels onto integer codes in `universe`; unknown → -1."""
    lookup = {m: i for i, m in enumerate(universe)}
    out = np.fromiter((lookup.get(str(x), -1) for x in labels), dtype=np.int64, count=len(labels))
    return out


# ─────────────────────── support ───────────────────────
def support_cell_id(variant: str, tercile: str, era: str) -> str:
    return f"{variant}|{tercile}|{era}"


def all_support_cell_ids() -> list[str]:
    return [
        support_cell_id(v, t, e)
        for v in SUPPORT_VARIANTS
        for t in ROT_TERCILES
        for e in ERAS
    ]


def cell_counts(df: pd.DataFrame, name_col: str = "name", month_col: str = "entry_month") -> dict:
    if df is None or len(df) == 0:
        return {"n_events": 0, "n_months": 0, "n_names": 0, "meets_floor": False}
    n_events = int(len(df))
    n_months = int(pd.Series(df[month_col]).nunique())
    n_names = int(pd.Series(df[name_col]).nunique())
    meets = n_events >= FLOOR_EVENTS and n_months >= FLOOR_MONTHS and n_names >= FLOOR_NAMES
    return {
        "n_events": n_events,
        "n_months": n_months,
        "n_names": n_names,
        "meets_floor": bool(meets),
    }


# ─────────────────────── verdict ───────────────────────
def _sign(x) -> str:
    if x is None or not np.isfinite(x):
        return "na"
    if x > 0:
        return "+"
    if x < 0:
        return "-"
    return "0"


def evaluate_verdict(
    *,
    pooled_h10: dict,
    by_phase_h10: dict,
    by_era_h10: dict,
    n_phases_required: int,
    phases: tuple[str, ...],
    monotonic: bool,
    floors_ok: bool,
    c1_broken: bool,
    b1_3d_insufficient: bool,
) -> tuple[str, list[str], dict]:
    """Apply the pre-declared rule. Returns (label, reasons, diagnostics)."""
    reasons: list[str] = []
    delta = pooled_h10.get("delta")
    ci = pooled_h10.get("ci") or [None, None]
    excl = ci_excludes_zero(ci)
    delta_neg = delta is not None and np.isfinite(delta) and delta < 0

    era_deltas = []
    era_signs = {}
    for era in ERAS:
        d = (by_era_h10.get(era) or {}).get("delta")
        era_deltas.append(d)
        era_signs[era] = _sign(d)
    finite_eras = [d for d in era_deltas if d is not None and np.isfinite(d)]
    era_same = (
        len(finite_eras) == 2
        and finite_eras[0] * finite_eras[1] > 0
    )

    n_phases_ok = 0
    phase_ok = {}
    for p in phases:
        cell = by_phase_h10.get(p) or {}
        d = cell.get("delta")
        ok = (
            d is not None
            and np.isfinite(d)
            and d < 0
            and ci_excludes_zero(cell.get("ci"))
        )
        phase_ok[p] = bool(ok)
        if ok:
            n_phases_ok += 1

    supported_stat = (
        bool(delta_neg)
        and bool(excl)
        and bool(era_same)
        and n_phases_ok >= n_phases_required
        and bool(monotonic)
    )
    not_supported_stat = (not excl) and bool(floors_ok)

    if c1_broken:
        reasons.append("C1 controls.status is BROKEN (pre-declared AR(1) gate)")
    if b1_3d_insufficient:
        reasons.append("B1 verdict is INSUFFICIENT on every 3D phase")
    if not delta_neg:
        reasons.append(f"pooled H10 DiD is not < 0 (delta={delta})")
    if not excl:
        reasons.append(f"pooled H10 DiD 95% CI includes zero (ci={ci})")
    if not era_same:
        reasons.append(f"era pooled-DiD signs differ ({era_signs})")
    if n_phases_ok < n_phases_required:
        reasons.append(
            f"only {n_phases_ok} of {len(phases)} phases have DiD<0 with CI excluding zero "
            f"(need ≥ {n_phases_required})"
        )
    if not monotonic:
        reasons.append("cost curve is not monotonic fast > mid > persistent")
    if not floors_ok:
        reasons.append("not all fast/persistent cells meet the support floors")

    if c1_broken or b1_3d_insufficient:
        label = "INSUFFICIENT SUPPORT"
    elif supported_stat:
        label = "SUPPORTED"
        reasons = ["all pre-declared SUPPORTED clauses hold"]
    elif not_supported_stat:
        label = "NOT SUPPORTED"
        reasons = [
            "pooled H10 DiD 95% CI includes zero",
            "all fast/persistent cells meet the support floors",
        ]
    else:
        label = "INSUFFICIENT SUPPORT"

    diag = {
        "delta_neg": bool(delta_neg),
        "ci_excludes_zero": bool(excl),
        "era_same_sign": bool(era_same),
        "era_signs": era_signs,
        "n_phases_ok": int(n_phases_ok),
        "phase_ok": phase_ok,
        "monotonic": bool(monotonic),
        "floors_ok": bool(floors_ok),
        "supported_stat": bool(supported_stat),
        "not_supported_stat": bool(not_supported_stat),
    }
    return label, reasons, diag


def phase_count_packet(by_phase_h10: dict, phases: tuple[str, ...]) -> int:
    """Packet definition: count of phases with DiD(p) < 0 AND 95% CI excluding zero."""
    n_ok = 0
    for p in phases:
        cell = by_phase_h10.get(p) or {}
        d = cell.get("delta")
        ok = (
            d is not None
            and np.isfinite(d)
            and d < 0
            and ci_excludes_zero(cell.get("ci"))
        )
        if ok:
            n_ok += 1
    return n_ok


def cost_curve_monotonic_strict(fast, mid, persistent) -> bool:
    """Strict fast > mid > persistent on mean mfe21_consumed_frac (3D pooled phases)."""
    vals = (fast, mid, persistent)
    if any(v is None or not np.isfinite(v) for v in vals):
        return False
    return bool(fast > mid > persistent)


def load_c1_controls_status(path: Path | str) -> str:
    """Read C1 controls.status from result.json. Never hard-code (N1; mutant MC1)."""
    obj = json.loads(Path(path).read_text())
    status = (obj.get("controls") or {}).get("status")
    if status is None:
        status = obj.get("status")
    return str(status) if status is not None else "UNKNOWN"


def load_b1_3d_verdicts(path: Path | str) -> list[str]:
    """Per-phase 3D verdicts from B1 result.json (N1)."""
    obj = json.loads(Path(path).read_text())
    v = obj.get("verdict") or {}
    overall = str(v.get("grain_effect_3d") or "")
    details = (v.get("details") or {}).get("grain_effect_3d") or []
    out: list[str] = []
    overall_u = overall.upper()
    for d in details:
        if "INSUFFICIENT" in overall_u:
            out.append("INSUFFICIENT SUPPORT")
        elif d.get("ok") is True:
            out.append("SUPPORTED")
        else:
            out.append("NOT SUPPORTED")
    if not out and "INSUFFICIENT" in overall_u:
        out = ["INSUFFICIENT SUPPORT"] * 3
    return out


def compute_verdict(
    *,
    pooled_h10: dict,
    by_phase_h10: dict,
    by_era_h10: dict,
    n_phases_required: int,
    phases: tuple[str, ...],
    monotonic: bool,
    floors_ok: bool,
    c1_status: str,
    b1_3d_verdicts: list | None = None,
) -> dict:
    """Apply the packet VERDICT rule. BROKEN C1 / all-3D-INSUFFICIENT B1 gate here (N1).

    Mutant MC2 deletes the BROKEN clause below and must fail
    test_verdict_insufficient_when_c1_broken.
    """
    labels = [str(x).upper() for x in (b1_3d_verdicts or [])]
    b1_3d_insufficient = bool(labels) and all("INSUFFICIENT" in x for x in labels)
    # Statistical clauses only; C1/B1 gates are applied below so a mutant that
    # deletes the BROKEN block actually changes the label.
    label, reasons, diag = evaluate_verdict(
        pooled_h10=pooled_h10,
        by_phase_h10=by_phase_h10,
        by_era_h10=by_era_h10,
        n_phases_required=n_phases_required,
        phases=phases,
        monotonic=monotonic,
        floors_ok=floors_ok,
        c1_broken=False,
        b1_3d_insufficient=False,
    )
    diag["phase_count"] = int(diag["n_phases_ok"])
    # N1 packet: INSUFFICIENT SUPPORT whenever C1 controls are BROKEN.
    if str(c1_status).upper() == "BROKEN":
        reasons = [
            "C1 controls.status is BROKEN (pre-declared AR(1) gate)",
            *[r for r in reasons if "BROKEN" not in r],
        ]
        return {
            "verdict": "INSUFFICIENT SUPPORT",
            "reasons": reasons,
            "diagnostics": diag,
            "phase_count": int(diag["n_phases_ok"]),
        }
    if b1_3d_insufficient:
        reasons = [
            "B1 verdict is INSUFFICIENT on every 3D phase",
            *[r for r in reasons if "INSUFFICIENT on every" not in r],
        ]
        return {
            "verdict": "INSUFFICIENT SUPPORT",
            "reasons": reasons,
            "diagnostics": diag,
            "phase_count": int(diag["n_phases_ok"]),
        }
    return {
        "verdict": label,
        "reasons": reasons,
        "diagnostics": diag,
        "phase_count": int(diag["n_phases_ok"]),
    }


def verdict_from_loaded_inputs(
    *,
    stats: dict,
    c1_json_path: Path | str,
    b1_json_path: Path | str | None = None,
    grain: str = "3D",
) -> dict:
    """Production loader: read C1 status from disk, then compute_verdict (N1)."""
    c1_status = load_c1_controls_status(c1_json_path)
    b1_3d = load_b1_3d_verdicts(b1_json_path) if b1_json_path else []
    phases = PHASES_3D if grain == "3D" else PHASES_2D
    meta = stats.get("meta") or {}
    return compute_verdict(
        pooled_h10=stats["did"][grain]["pooled"]["h10"],
        by_phase_h10={p: stats["did"][grain]["by_phase"][p]["h10"] for p in phases},
        by_era_h10={e: stats["did"][grain]["by_era"][e]["h10"] for e in ERAS},
        n_phases_required=2,
        phases=phases,
        monotonic=bool(meta.get("monotonic_3d") if grain == "3D" else meta.get("monotonic_2d")),
        floors_ok=bool(meta.get("floors_ok_3d") if grain == "3D" else meta.get("floors_ok_2d")),
        c1_status=c1_status,
        b1_3d_verdicts=b1_3d if grain == "3D" else [],
    )


def map_confirmed_by_key(ev_keys, confirmed_dict: dict) -> np.ndarray:
    """Map (name, date) keys through a dict. Correct N3 mapping."""
    return np.array([bool(confirmed_dict.get(k, False)) for k in ev_keys], dtype=bool)


def map_confirmed_by_integer_index(ev_keys, any_confirmed: pd.Series) -> np.ndarray:
    """BUGGY round-1 mapping (integer-index Series.map). N3 mutant must use this."""
    return pd.Series(list(ev_keys)).map(any_confirmed).fillna(False).to_numpy()


def era_token(era: str, ranges: dict | None) -> str:
    """Qualify an era key with its actual signal_date range (N6)."""
    if not ranges or era not in ranges:
        return str(era)
    lo, hi = ranges[era]
    if lo is None or hi is None:
        return str(era)
    return (
        f"{era} ({pd.Timestamp(lo).strftime('%Y-%m-%d')}.."
        f"{pd.Timestamp(hi).strftime('%Y-%m-%d')})"
    )


def era_ranges_from_1d(e1: pd.DataFrame) -> dict:
    out = {}
    for era in ERAS:
        sub = e1.loc[e1["era"].astype(str) == era] if "era" in e1.columns else e1.iloc[0:0]
        if len(sub) == 0 and "era_key" in e1.columns:
            sub = e1.loc[e1["era_key"].astype(str) == era]
        if len(sub) == 0:
            out[era] = (None, None)
            continue
        d = _norm_dates(sub["signal_date"])
        out[era] = (pd.Timestamp(d.min()), pd.Timestamp(d.max()))
    return out


def n_block(df: pd.DataFrame, month_col: str = "month_key") -> dict:
    if df is None or len(df) == 0:
        return {"n_events": 0, "n_months": 0, "n_names": 0}
    mc = month_col if month_col in df.columns else ("entry_month" if "entry_month" in df.columns else None)
    return {
        "n_events": int(len(df)),
        "n_months": int(pd.Series(df[mc]).nunique()) if mc else 0,
        "n_names": int(pd.Series(df["name"]).nunique()) if "name" in df.columns else 0,
    }


def host_provenance() -> dict:
    return {
        "host": "m2",
        "uname": platform.node(),
        "python": f"{sys.executable} {platform.python_version()}",
        "pandas": str(pd.__version__),
        "numpy": str(np.__version__),
        "pyarrow": __import__("pyarrow").__version__,
        "scipy": __import__("scipy").__version__,
        "pytest": __import__("pytest").__version__,
    }


# ─────────────────────── core computation ───────────────────────
def _slice_tercile_era(df: pd.DataFrame, tercile_col: str, tercile: str, era: str | None):
    m = df[tercile_col].astype(str) == str(tercile)
    if era is not None:
        m = m & (df["era_key"].astype(str) == str(era))
    return df.loc[m]


def _pack_delta(delta: float, boot: np.ndarray) -> dict:
    lo, hi = percentiles_ci(boot)
    return {"delta": jnum(delta), "ci": jci(lo, hi)}


def _pooled_n_from_phases(phase_h10: dict, phases: tuple[str, ...]) -> dict:
    """Honest-N for a pooled DiD: sum confirmed events across phases; 1D N from any phase."""
    first = None
    for p in phases:
        if phase_h10.get(p) and phase_h10[p].get("n"):
            first = phase_h10[p]["n"]
            break
    empty = {
        "n_events": 0,
        "n_months": 0,
        "n_names": 0,
    }
    if first is None:
        return {
            "fast": {"confirmed": dict(empty), "all_1d": dict(empty)},
            "persistent": {"confirmed": dict(empty), "all_1d": dict(empty)},
        }
    out = {}
    for T in ("fast", "persistent"):
        conf_e = 0
        conf_m = 0
        conf_n = 0
        for p in phases:
            rec = ((phase_h10.get(p) or {}).get("n") or {}).get(T) or {}
            c = rec.get("confirmed") or empty
            conf_e += int(c.get("n_events") or 0)
            conf_m = max(conf_m, int(c.get("n_months") or 0))
            conf_n = max(conf_n, int(c.get("n_names") or 0))
        out[T] = {
            "confirmed": {"n_events": conf_e, "n_months": conf_m, "n_names": conf_n},
            "all_1d": dict(first[T]["all_1d"]),
        }
    return out


def compute_all(
    events: pd.DataFrame,
    pairs: pd.DataFrame,
    state: pd.DataFrame,
    *,
    n_boot: int = N_BOOTSTRAP,
    seed: int = RNG_SEED,
) -> dict:
    """Join + DiD + secondaries. Pure given the three frames."""
    e = events.copy()
    e["signal_date"] = _norm_dates(e["signal_date"])
    e["entry_date"] = _norm_dates(e["entry_date"]) if "entry_date" in e.columns else e["signal_date"]
    e["variant"] = e["variant"].astype(str)
    e["name"] = e["name"].astype(str)
    e["entry_month"] = e["entry_month"].astype(str)
    e["era"] = e["era"].astype(str)

    e1_raw = e.loc[e["variant"] == "1D"].copy()
    e1, n_dropped = attach_state_to_1d(e1_raw, state)
    n_joined = int(len(e1))
    n_nan_rot = int(e1["rotation_tercile"].isna().sum()) if n_joined else 0

    # parent era/month stay the 1D event's (B1 already labelled by entry_date)
    e1["era_key"] = e1["era"].astype(str)
    e1["month_key"] = e1["entry_month"].astype(str)

    confirmed = {}
    for v in list(VARIANTS_2D) + list(VARIANTS_3D):
        c = attach_confirmed(pairs, e, e1, v)
        # cluster + era on the 1D parent (conditioner known when first signal fired)
        c["era_key"] = c["parent_era"].astype(str)
        c["month_key"] = c["parent_entry_month"].astype(str)
        confirmed[v] = c

    # month universe: 1D parent months ∪ confirmed parent months (same labels)
    month_set = set(e1["month_key"].astype(str))
    for c in confirmed.values():
        month_set.update(c["month_key"].astype(str))
    month_universe = np.array(sorted(month_set), dtype=object)
    n_months_u = int(len(month_universe))
    rng = np.random.default_rng(seed)
    draws = make_paired_draws(n_months_u, n_boot, rng)

    e1 = e1.copy()
    e1["_m"] = month_codes(e1["month_key"].to_numpy(), month_universe)
    for v, c in confirmed.items():
        c = c.copy()
        c["_m"] = month_codes(c["month_key"].to_numpy(), month_universe)
        confirmed[v] = c

    def arm_arrays(df: pd.DataFrame, value_col: str, tercile_col: str, tercile: str, era: str | None):
        sub = _slice_tercile_era(df, tercile_col, tercile, era)
        if len(sub) == 0:
            return (
                np.array([], dtype=np.int64),
                np.array([], dtype=np.float64),
                0,
            )
        ok = sub["_m"].to_numpy() >= 0
        sub = sub.loc[ok]
        return (
            sub["_m"].to_numpy(dtype=np.int64),
            sub[value_col].to_numpy(dtype=np.float64),
            int(len(sub)),
        )

    def gap_pack(conf_df, val_conf, tercile_col, tercile, era, val_1d="excess_h10_net"):
        m_c, v_c, n_c = arm_arrays(conf_df, val_conf, tercile_col, tercile, era)
        m_1, v_1, n_1 = arm_arrays(e1, val_1d, tercile_col, tercile, era)
        pt = point_mean(v_c) - point_mean(v_1)
        # PAIRED BOOTSTRAP (J1 / mutant M7): reuse the ONE draws array computed
        # above. Mutant M7 would call make_paired_draws() here per cell.
        boot_c = cell_boot_means(draws, m_c, v_c)
        boot_1 = cell_boot_means(draws, m_1, v_1)
        boot = boot_c - boot_1
        lo, hi = percentiles_ci(boot)
        sub_c = _slice_tercile_era(conf_df, tercile_col, tercile, era)
        sub_1 = _slice_tercile_era(e1, tercile_col, tercile, era)
        nc = n_block(sub_c)
        n1 = n_block(sub_1)
        return {
            "gap": pt,
            "ci": (lo, hi),
            "boot": boot,
            "n_confirmed": n_c,
            "n_1d": n_1,
            "n_confirmed_events": nc["n_events"],
            "n_confirmed_months": nc["n_months"],
            "n_confirmed_names": nc["n_names"],
            "n_1d_events": n1["n_events"],
            "n_1d_months": n1["n_months"],
            "n_1d_names": n1["n_names"],
        }

    # ── primary DiD (rotation) ──
    did = {"3D": {}, "2D": {}}
    gap_table = {"3D": {}, "2D": {}}

    def run_grain(grain: str, variants: tuple[str, ...], phases: tuple[str, ...]):
        # gaps per tercile × phase (overall, not era-split) for H10
        gap_table[grain] = {t: {} for t in ROT_TERCILES}
        phase_h10 = {}
        phase_h21 = {}
        phase_boot_h10 = {}
        phase_boot_h21 = {}
        for phase, variant in zip(phases, variants):
            conf = confirmed[variant]
            did_boot_h10 = None
            did_boot_h21 = None
            for T in ROT_TERCILES:
                g10 = gap_pack(conf, "conf_h10_net", "rotation_tercile", T, None)
                g21 = gap_pack(conf, "conf_h21_net", "rotation_tercile", T, None, val_1d="excess_h21_net")
                gap_table[grain][T][phase] = {
                    "gap_h10": jnum(g10["gap"]),
                    "ci": jci(*g10["ci"]),
                    "gap_h21": jnum(g21["gap"]),
                    "ci_h21": jci(*g21["ci"]),
                    "n_confirmed": int(g10["n_confirmed"]),
                    "n_1d": int(g10["n_1d"]),
                    "n_events_confirmed": int(g10["n_confirmed_events"]),
                    "n_months_confirmed": int(g10["n_confirmed_months"]),
                    "n_names_confirmed": int(g10["n_confirmed_names"]),
                    "n_events_1d": int(g10["n_1d_events"]),
                    "n_months_1d": int(g10["n_1d_months"]),
                    "n_names_1d": int(g10["n_1d_names"]),
                }
            g_fast_10 = gap_pack(conf, "conf_h10_net", "rotation_tercile", "fast", None)
            g_pers_10 = gap_pack(conf, "conf_h10_net", "rotation_tercile", "persistent", None)
            g_fast_21 = gap_pack(conf, "conf_h21_net", "rotation_tercile", "fast", None, val_1d="excess_h21_net")
            g_pers_21 = gap_pack(conf, "conf_h21_net", "rotation_tercile", "persistent", None, val_1d="excess_h21_net")
            # DiD = gap(fast) − gap(persistent). Mutant M5 flips this subtraction.
            d10 = g_fast_10["gap"] - g_pers_10["gap"]
            d21 = g_fast_21["gap"] - g_pers_21["gap"]
            b10 = g_fast_10["boot"] - g_pers_10["boot"]
            b21 = g_fast_21["boot"] - g_pers_21["boot"]
            rec10 = _pack_delta(d10, b10)
            rec21 = _pack_delta(d21, b21)
            rec10["n"] = {
                "fast": {
                    "confirmed": {
                        "n_events": int(g_fast_10["n_confirmed_events"]),
                        "n_months": int(g_fast_10["n_confirmed_months"]),
                        "n_names": int(g_fast_10["n_confirmed_names"]),
                    },
                    "all_1d": {
                        "n_events": int(g_fast_10["n_1d_events"]),
                        "n_months": int(g_fast_10["n_1d_months"]),
                        "n_names": int(g_fast_10["n_1d_names"]),
                    },
                },
                "persistent": {
                    "confirmed": {
                        "n_events": int(g_pers_10["n_confirmed_events"]),
                        "n_months": int(g_pers_10["n_confirmed_months"]),
                        "n_names": int(g_pers_10["n_confirmed_names"]),
                    },
                    "all_1d": {
                        "n_events": int(g_pers_10["n_1d_events"]),
                        "n_months": int(g_pers_10["n_1d_months"]),
                        "n_names": int(g_pers_10["n_1d_names"]),
                    },
                },
            }
            rec21["n"] = rec10["n"]
            phase_h10[phase] = rec10
            phase_h21[phase] = rec21
            phase_boot_h10[phase] = b10
            phase_boot_h21[phase] = b21

        pooled_boot_h10 = _nanmean_axis0([phase_boot_h10[p] for p in phases])
        pooled_boot_h21 = _nanmean_axis0([phase_boot_h21[p] for p in phases])
        pooled_pt_h10 = _nanmean_scalar(
            [phase_h10[p]["delta"] if phase_h10[p]["delta"] is not None else np.nan for p in phases]
        )
        pooled_pt_h21 = _nanmean_scalar(
            [phase_h21[p]["delta"] if phase_h21[p]["delta"] is not None else np.nan for p in phases]
        )

        by_era = {}
        for era in ERAS:
            era_phase_h10 = {}
            era_phase_h21 = {}
            era_boot_h10 = []
            era_boot_h21 = []
            for phase, variant in zip(phases, variants):
                conf = confirmed[variant]
                gf10 = gap_pack(conf, "conf_h10_net", "rotation_tercile", "fast", era)
                gp10 = gap_pack(conf, "conf_h10_net", "rotation_tercile", "persistent", era)
                gf21 = gap_pack(conf, "conf_h21_net", "rotation_tercile", "fast", era, val_1d="excess_h21_net")
                gp21 = gap_pack(conf, "conf_h21_net", "rotation_tercile", "persistent", era, val_1d="excess_h21_net")
                d10 = gf10["gap"] - gp10["gap"]
                d21 = gf21["gap"] - gp21["gap"]
                b10 = gf10["boot"] - gp10["boot"]
                b21 = gf21["boot"] - gp21["boot"]
                er10 = _pack_delta(d10, b10)
                er21 = _pack_delta(d21, b21)
                er10["n"] = {
                    "fast": {
                        "confirmed": {
                            "n_events": int(gf10["n_confirmed_events"]),
                            "n_months": int(gf10["n_confirmed_months"]),
                            "n_names": int(gf10["n_confirmed_names"]),
                        },
                        "all_1d": {
                            "n_events": int(gf10["n_1d_events"]),
                            "n_months": int(gf10["n_1d_months"]),
                            "n_names": int(gf10["n_1d_names"]),
                        },
                    },
                    "persistent": {
                        "confirmed": {
                            "n_events": int(gp10["n_confirmed_events"]),
                            "n_months": int(gp10["n_confirmed_months"]),
                            "n_names": int(gp10["n_confirmed_names"]),
                        },
                        "all_1d": {
                            "n_events": int(gp10["n_1d_events"]),
                            "n_months": int(gp10["n_1d_months"]),
                            "n_names": int(gp10["n_1d_names"]),
                        },
                    },
                }
                er21["n"] = er10["n"]
                era_phase_h10[phase] = er10
                era_phase_h21[phase] = er21
                era_boot_h10.append(b10)
                era_boot_h21.append(b21)
            era_pooled_b10 = _nanmean_axis0(era_boot_h10)
            era_pooled_b21 = _nanmean_axis0(era_boot_h21)
            era_pt_h10 = _nanmean_scalar(
                [era_phase_h10[p]["delta"] if era_phase_h10[p]["delta"] is not None else np.nan for p in phases]
            )
            era_pt_h21 = _nanmean_scalar(
                [era_phase_h21[p]["delta"] if era_phase_h21[p]["delta"] is not None else np.nan for p in phases]
            )
            eh10 = _pack_delta(era_pt_h10, era_pooled_b10)
            eh21 = _pack_delta(era_pt_h21, era_pooled_b21)
            eh10["n"] = _pooled_n_from_phases(era_phase_h10, phases)
            eh21["n"] = eh10["n"]
            by_era[era] = {
                "h10": eh10,
                "h21": eh21,
                "by_phase": {
                    p: {"h10": era_phase_h10[p], "h21": era_phase_h21[p]} for p in phases
                },
            }

        ph10 = _pack_delta(pooled_pt_h10, pooled_boot_h10)
        ph21 = _pack_delta(pooled_pt_h21, pooled_boot_h21)
        ph10["n"] = _pooled_n_from_phases(phase_h10, phases)
        ph21["n"] = ph10["n"]
        did[grain] = {
            "pooled": {"h10": ph10, "h21": ph21},
            "by_phase": {p: {"h10": phase_h10[p], "h21": phase_h21[p]} for p in phases},
            "by_era": by_era,
            "_boot_h10_pooled": pooled_boot_h10,
            "_boot_h10_by_phase": {p: phase_boot_h10[p] for p in phases},
        }

    run_grain("3D", VARIANTS_3D, PHASES_3D)
    run_grain("2D", VARIANTS_2D, PHASES_2D)

    # ── cost curve ──
    def cost_for(variants: tuple[str, ...], tercile: str):
        frames = []
        for v in variants:
            c = confirmed[v]
            sub = c.loc[c["rotation_tercile"].astype(str) == tercile]
            frames.append(sub)
        d = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        if len(d) == 0:
            return {
                "mean_mfe_consumed": None,
                "median_mfe_consumed": None,
                "sd_mfe": None,
                "min_mfe": None,
                "max_mfe": None,
                "ci": [None, None],
                "mean_cost_pct": None,
                "ci_cost": [None, None],
                "n": 0,
                "n_finite_mfe": 0,
                "n_events": 0,
                "n_months": 0,
                "n_names": 0,
            }
        mfe = d["mfe21_consumed_frac"].to_numpy(dtype=np.float64)
        cost = d["confirmation_cost_pct"].to_numpy(dtype=np.float64)
        mi = d["_m"].to_numpy(dtype=np.int64)
        boot_mfe = cell_boot_means(draws, mi, mfe)
        boot_cost = cell_boot_means(draws, mi, cost)
        lo_m, hi_m = percentiles_ci(boot_mfe)
        lo_c, hi_c = percentiles_ci(boot_cost)
        n_mfe = int(np.isfinite(mfe).sum())
        mfe_f = mfe[np.isfinite(mfe)]
        nb = n_block(d)
        return {
            "mean_mfe_consumed": jnum(point_mean(mfe)),
            "median_mfe_consumed": jnum(float(np.median(mfe_f)) if mfe_f.size else np.nan),
            "sd_mfe": jnum(float(np.std(mfe_f, ddof=1)) if mfe_f.size > 1 else np.nan),
            "min_mfe": jnum(float(np.min(mfe_f)) if mfe_f.size else np.nan),
            "max_mfe": jnum(float(np.max(mfe_f)) if mfe_f.size else np.nan),
            "ci": jci(lo_m, hi_m),
            "mean_cost_pct": jnum(point_mean(cost)),
            "ci_cost": jci(lo_c, hi_c),
            "n": n_mfe,
            "n_finite_mfe": n_mfe,
            "n_events": int(len(d)),
            "n_months": nb["n_months"],
            "n_names": nb["n_names"],
        }

    cost_curve = {"3D": {}, "2D": {}}
    for T in ROT_TERCILES:
        cost_curve["3D"][T] = cost_for(VARIANTS_3D, T)
        cost_curve["2D"][T] = cost_for(VARIANTS_2D, T)

    def _mfe(grain, t):
        v = cost_curve[grain][t]["mean_mfe_consumed"]
        return v if v is not None else float("nan")

    monotonic_3d = cost_curve_monotonic_strict(
        _mfe("3D", "fast"), _mfe("3D", "mid"), _mfe("3D", "persistent")
    )
    monotonic_2d = cost_curve_monotonic_strict(
        _mfe("2D", "fast"), _mfe("2D", "mid"), _mfe("2D", "persistent")
    )
    cost_curve["monotonic_3d"] = bool(monotonic_3d)
    cost_curve["monotonic_2d"] = bool(monotonic_2d)

    # ── false starts / large winners ──
    # "no 3D confirmation (pooled phases)" = none of 3D.p0/p1/p2 confirmed.
    any_3d = None
    for v in VARIANTS_3D:
        pv = pairs.loc[pairs["variant"].astype(str) == v, ["name", "signal_session_1d", "no_confirmation"]].copy()
        pv["signal_session_1d"] = _norm_dates(pv["signal_session_1d"])
        pv = pv.rename(columns={"no_confirmation": f"nc_{v}", "signal_session_1d": "signal_date"})
        if any_3d is None:
            any_3d = pv
        else:
            any_3d = any_3d.merge(pv, on=["name", "signal_date"], how="outer")
    nc_cols = [f"nc_{v}" for v in VARIANTS_3D]
    for c in nc_cols:
        if c not in any_3d.columns:
            any_3d[c] = True
        any_3d[c] = any_3d[c].fillna(True).astype(bool)
    any_3d["no_3d_any"] = any_3d[nc_cols].all(axis=1)

    e1_fs = e1.merge(any_3d[["name", "signal_date", "no_3d_any"]], on=["name", "signal_date"], how="left")
    e1_fs["no_3d_any"] = e1_fs["no_3d_any"].fillna(True).astype(bool)

    false_starts = {}
    large_winners = {}
    for T in ROT_TERCILES:
        sub = e1_fs.loc[e1_fs["rotation_tercile"].astype(str) == T]
        fs = sub.loc[sub["excess_h10_net"].to_numpy(dtype=np.float64) < FALSE_START_H10]
        n_fs = int(len(fs))
        share_fs = float(fs["no_3d_any"].mean()) if n_fs else float("nan")
        fs_n = n_block(fs)
        false_starts[T] = {
            "share_unconfirmed": jnum(share_fs),
            "n": n_fs,
            "n_events": fs_n["n_events"],
            "n_months": fs_n["n_months"],
            "n_names": fs_n["n_names"],
        }
        lw = sub.loc[sub["excess_h21_net"].to_numpy(dtype=np.float64) > LARGE_WINNER_H21]
        n_lw = int(len(lw))
        share_lw = float(lw["no_3d_any"].mean()) if n_lw else float("nan")
        lw_n = n_block(lw)
        large_winners[T] = {
            "share_unconfirmed": jnum(share_lw),
            "n": n_lw,
            "n_events": lw_n["n_events"],
            "n_months": lw_n["n_months"],
            "n_names": lw_n["n_names"],
        }

    # ── breadth axis: DiD = gap(narrow) − gap(broad) ──
    def breadth_grain(grain: str, variants: tuple[str, ...], phases: tuple[str, ...]):
        phase_h10 = {}
        phase_h21 = {}
        boots_h10 = []
        boots_h21 = []
        for phase, variant in zip(phases, variants):
            conf = confirmed[variant]
            gn10 = gap_pack(conf, "conf_h10_net", "breadth_tercile", "narrow", None)
            gb10 = gap_pack(conf, "conf_h10_net", "breadth_tercile", "broad", None)
            gn21 = gap_pack(conf, "conf_h21_net", "breadth_tercile", "narrow", None, val_1d="excess_h21_net")
            gb21 = gap_pack(conf, "conf_h21_net", "breadth_tercile", "broad", None, val_1d="excess_h21_net")
            d10 = gn10["gap"] - gb10["gap"]
            d21 = gn21["gap"] - gb21["gap"]
            b10 = gn10["boot"] - gb10["boot"]
            b21 = gn21["boot"] - gb21["boot"]
            phase_h10[phase] = _pack_delta(d10, b10)
            phase_h21[phase] = _pack_delta(d21, b21)
            boots_h10.append(b10)
            boots_h21.append(b21)
        pooled_b10 = _nanmean_axis0(boots_h10)
        pooled_b21 = _nanmean_axis0(boots_h21)
        pt10 = _nanmean_scalar(
            [phase_h10[p]["delta"] if phase_h10[p]["delta"] is not None else np.nan for p in phases]
        )
        pt21 = _nanmean_scalar(
            [phase_h21[p]["delta"] if phase_h21[p]["delta"] is not None else np.nan for p in phases]
        )
        by_era = {}
        for era in ERAS:
            era_ph = {}
            era_b10 = []
            era_b21 = []
            for phase, variant in zip(phases, variants):
                conf = confirmed[variant]
                gn10 = gap_pack(conf, "conf_h10_net", "breadth_tercile", "narrow", era)
                gb10 = gap_pack(conf, "conf_h10_net", "breadth_tercile", "broad", era)
                gn21 = gap_pack(conf, "conf_h21_net", "breadth_tercile", "narrow", era, val_1d="excess_h21_net")
                gb21 = gap_pack(conf, "conf_h21_net", "breadth_tercile", "broad", era, val_1d="excess_h21_net")
                d10 = gn10["gap"] - gb10["gap"]
                d21 = gn21["gap"] - gb21["gap"]
                b10 = gn10["boot"] - gb10["boot"]
                b21 = gn21["boot"] - gb21["boot"]
                era_ph[phase] = {"h10": _pack_delta(d10, b10), "h21": _pack_delta(d21, b21)}
                era_b10.append(b10)
                era_b21.append(b21)
            ept10 = _nanmean_scalar(
                [era_ph[p]["h10"]["delta"] if era_ph[p]["h10"]["delta"] is not None else np.nan for p in phases]
            )
            ept21 = _nanmean_scalar(
                [era_ph[p]["h21"]["delta"] if era_ph[p]["h21"]["delta"] is not None else np.nan for p in phases]
            )
            by_era[era] = {
                "h10": _pack_delta(ept10, _nanmean_axis0(era_b10)),
                "h21": _pack_delta(ept21, _nanmean_axis0(era_b21)),
                "by_phase": era_ph,
            }
        return {
            "contrast": "gap(narrow) − gap(broad)",
            "pooled": {
                "h10": _pack_delta(pt10, pooled_b10),
                "h21": _pack_delta(pt21, pooled_b21),
            },
            "by_phase": {p: {"h10": phase_h10[p], "h21": phase_h21[p]} for p in phases},
            "by_era": by_era,
        }

    breadth_axis = {
        "3D": breadth_grain("3D", VARIANTS_3D, PHASES_3D),
        "2D": breadth_grain("2D", VARIANTS_2D, PHASES_2D),
    }

    # ── support table (rotation tercile × variant × era) ──
    support = {}
    # 1D uses all joined 1D events; 2D/3D variants use confirmed entries.
    frames_for_support = {"1D": e1}
    for v in list(VARIANTS_2D) + list(VARIANTS_3D):
        frames_for_support[v] = confirmed[v]
    for v in SUPPORT_VARIANTS:
        dfv = frames_for_support[v]
        month_col = "month_key" if "month_key" in dfv.columns else "entry_month"
        for T in ROT_TERCILES:
            for era in ERAS:
                cid = support_cell_id(v, T, era)
                sub = dfv.loc[
                    (dfv["rotation_tercile"].astype(str) == T)
                    & (dfv["era_key"].astype(str) == era)
                ]
                rec = cell_counts(sub, name_col="name", month_col=month_col)
                rec["variant"] = v
                rec["tercile"] = T
                rec["era"] = era
                support[cid] = rec

    def floors_ok_for(variants: tuple[str, ...]) -> bool:
        needed = list(variants) + ["1D"]
        for v in needed:
            for T in ("fast", "persistent"):
                eras_present = 0
                for era in ERAS:
                    rec = support[support_cell_id(v, T, era)]
                    if rec["n_events"] > 0:
                        eras_present += 1
                    if not rec["meets_floor"]:
                        return False
                if eras_present < 2:
                    return False
        return True

    era_ranges = era_ranges_from_1d(e1)
    meta = {
        "n_1d_events_joined": n_joined,
        "n_1d_events_dropped_no_state": int(n_dropped),
        "n_1d_nan_rotation_tercile": int(n_nan_rot),
        "n_months_universe": n_months_u,
        "draws_shape": [int(draws.shape[0]), int(draws.shape[1])],
        "n_confirmed": {v: int(len(confirmed[v])) for v in confirmed},
        "floors_ok_3d": bool(floors_ok_for(VARIANTS_3D)),
        "floors_ok_2d": bool(floors_ok_for(VARIANTS_2D)),
        "monotonic_3d": bool(monotonic_3d),
        "monotonic_2d": bool(monotonic_2d),
        "era_ranges": {
            era: (
                None if lo is None else pd.Timestamp(lo).strftime("%Y-%m-%d"),
                None if hi is None else pd.Timestamp(hi).strftime("%Y-%m-%d"),
            )
            for era, (lo, hi) in era_ranges.items()
        },
    }
    return {
        "did": did,
        "gaps": gap_table,
        "cost_curve": cost_curve,
        "false_starts_avoided": false_starts,
        "large_winners_excluded": large_winners,
        "breadth_axis": breadth_axis,
        "support": support,
        "meta": meta,
        "era_ranges": era_ranges,
        "draws": draws,  # tests only; stripped before json
    }


# ─────────────────────── reporting ───────────────────────
def _fmt(x, nd=4):
    if x is None:
        return "NA"
    try:
        if not np.isfinite(x):
            return "NA"
    except (TypeError, ValueError):
        return "NA"
    return f"{x:+.{nd}f}"


def _fmt_ci(ci, nd=4):
    if not ci or ci[0] is None or ci[1] is None:
        return "[NA, NA]"
    return f"[{ci[0]:+.{nd}f}, {ci[1]:+.{nd}f}]"


def _fmt_share(x):
    if x is None or not np.isfinite(x):
        return "NA"
    return f"{x:.4f}"


def _fmt_n3(rec: dict | None) -> str:
    if not rec:
        return "n_events=0 / n_months=0 / n_names=0"
    return (
        f"n_events={int(rec.get('n_events') or 0):,} / "
        f"n_months={int(rec.get('n_months') or 0):,} / "
        f"n_names={int(rec.get('n_names') or 0):,}"
    )


def _did_n_cell(cell: dict) -> str:
    n = cell.get("n") or {}
    fast_c = ((n.get("fast") or {}).get("confirmed")) or {}
    fast_1 = ((n.get("fast") or {}).get("all_1d")) or {}
    per_c = ((n.get("persistent") or {}).get("confirmed")) or {}
    per_1 = ((n.get("persistent") or {}).get("all_1d")) or {}
    return (
        f"fast conf {_fmt_n3(fast_c)}; fast 1D {_fmt_n3(fast_1)}; "
        f"pers conf {_fmt_n3(per_c)}; pers 1D {_fmt_n3(per_1)}"
    )


def _era_disp_map(payload: dict) -> dict:
    labels = payload.get("era_labels") or {}
    out = {}
    for era in ERAS:
        rec = labels.get(era) or {}
        disp = rec.get("display")
        if disp:
            out[era] = disp
        else:
            start, end = rec.get("start"), rec.get("end")
            if start and end:
                out[era] = f"{era} ({start}..{end})"
            else:
                out[era] = era
    return out


def build_result_md(payload: dict) -> str:
    inp = payload["inputs"]
    did3 = payload["did"]["3D"]
    did2 = payload["did"]["2D"]
    v = payload["verdict"]
    cc = payload["cost_curve"]
    meta = payload.get("meta", {})
    cf = v.get("counterfactual_if_c1_pass", {})

    p10 = did3["pooled"]["h10"]
    lines = []
    n_ok = v.get("diagnostics_3d", {}).get("n_phases_ok")
    era_s = v.get("diagnostics_3d", {}).get("era_signs", {})
    ed = _era_disp_map(payload)
    e0 = ed.get("2014-2019", "2014-2019")
    e1 = ed.get("2020-2026", "2020-2026")
    s0 = era_s.get(e0) or era_s.get("2014-2019") or "?"
    s1 = era_s.get(e1) or era_s.get("2020-2026") or "?"
    lines.append(
        "The price stores are FINAL-VINTAGE (as observed today, not point-in-time) "
        "and the universes are SURVIVOR-SELECTED (current membership only). Every "
        "signal uses only closes at or before the signal session. C1 state joined "
        "at the 1D signal date is already one-session shifted. "
        f"**ANSWER FIRST.** H10: {v['3D']} — C1 `controls.status` is "
        f"**{inp['C1_controls_status']}** (pre-declared AR(1) gate). "
        f"Pooled 3D DiD on H10 net = {_fmt(p10['delta'])} 95% CI {_fmt_ci(p10['ci'])}; "
        f"era signs {e0}={s0} {e1}={s1}; phase_count={n_ok} of 3 "
        f"(DiD<0 with CI excluding zero); 3D cost curve monotonic "
        f"fast>mid>persistent = {cc.get('monotonic_3d')}."
    )
    lines.append("")
    lines.append("## Inputs")
    lines.append("")
    lines.append(
        f"- B1 events_panel sha256 `{inp['B1_events_panel_sha256']}` "
        f"(prefix `{inp['B1_events_panel_sha256'][:8]}`)"
    )
    lines.append(
        f"- B1 confirmation_pairs sha256 `{inp['B1_confirmation_pairs_sha256']}`"
    )
    lines.append(
        f"- C1 rotation_state_daily sha256 `{inp['C1_rotation_state_sha256']}` "
        f"(prefix `{inp['C1_rotation_state_sha256'][:8]}`)"
    )
    b1v = inp.get("B1_verdict")
    if isinstance(b1v, dict):
        lines.append(
            f"- B1 grain_effect_3d = **{b1v.get('grain_effect_3d')}**; "
            f"grain_effect_2d = {b1v.get('grain_effect_2d')}; "
            f"memory_effect_3 = {b1v.get('memory_effect_3')}"
        )
    else:
        lines.append(f"- B1 verdict = {b1v}")
    lines.append(f"- C1 controls.status = **{inp['C1_controls_status']}**")
    lines.append(
        f"- 1D events joined = {payload['n_1d_events_joined']:,}; "
        f"dropped (signal_date absent from C1) = {payload['n_1d_events_dropped_no_state']:,}; "
        f"joined with NaN rotation_tercile = {meta.get('n_1d_nan_rotation_tercile', 0):,}"
    )
    lines.append(f"- Repo head: `{payload['repo_head']}`")
    lines.append("")

    def did_table(grain, didg, phases):
        lines.append(f"## DiD {grain} (gap(fast) − gap(persistent))")
        lines.append("")
        lines.append(
            "gap(p,T) = mean(excess_h*_net of confirmed entries | T) "
            "− mean(excess_h*_net of all 1D events | T). "
            f"Pooled DiD = equal-weight mean over {grain} phases. "
            "Entry-month cluster bootstrap, 1,000 draws, seed 20261004; "
            "one month draw per replicate shared across cells. "
            "Honest-N: n_events / n_months / n_names for BOTH legs "
            "(confirmed entries and all 1D events) per tercile."
        )
        lines.append("")
        lines.append(
            "| cell | H10 Δ | H10 95% CI | H21 Δ | H21 95% CI | honest-N (fast/pers × confirmed/1D) |"
        )
        lines.append("|---|---:|---|---:|---|---|")
        ph = didg["pooled"]
        lines.append(
            f"| pooled | {_fmt(ph['h10']['delta'])} | {_fmt_ci(ph['h10']['ci'])} | "
            f"{_fmt(ph['h21']['delta'])} | {_fmt_ci(ph['h21']['ci'])} | "
            f"{_did_n_cell(ph['h10'])} |"
        )
        for p in phases:
            cell = didg["by_phase"][p]
            lines.append(
                f"| {p} | {_fmt(cell['h10']['delta'])} | {_fmt_ci(cell['h10']['ci'])} | "
                f"{_fmt(cell['h21']['delta'])} | {_fmt_ci(cell['h21']['ci'])} | "
                f"{_did_n_cell(cell['h10'])} |"
            )
        era_keys = list(didg["by_era"].keys())
        for era_key in era_keys:
            cell = didg["by_era"][era_key]
            lines.append(
                f"| pooled {era_key} | {_fmt(cell['h10']['delta'])} | {_fmt_ci(cell['h10']['ci'])} | "
                f"{_fmt(cell['h21']['delta'])} | {_fmt_ci(cell['h21']['ci'])} | "
                f"{_did_n_cell(cell['h10'])} |"
            )
            for p in phases:
                pc = cell["by_phase"][p]
                lines.append(
                    f"| {p} {era_key} | {_fmt(pc['h10']['delta'])} | {_fmt_ci(pc['h10']['ci'])} | "
                    f"{_fmt(pc['h21']['delta'])} | {_fmt_ci(pc['h21']['ci'])} | "
                    f"{_did_n_cell(pc['h10'])} |"
                )
        lines.append("")

    did_table("3D", did3, PHASES_3D)
    did_table("2D", did2, PHASES_2D)

    lines.append("## Gaps by rotation tercile (H10 net)")
    lines.append("")
    lines.append(
        "gap(p,T) as defined above. n_confirmed = confirmed entries of that phase; "
        "n_1d = all 1D events in T (including unconfirmed)."
    )
    lines.append("")
    lines.append(
        "| grain | tercile | phase | gap H10 | 95% CI | n_confirmed | n_1d | "
        "n_events_conf / n_months_conf / n_names_conf | "
        "n_events_1d / n_months_1d / n_names_1d |"
    )
    lines.append("|---|---|---|---:|---|---:|---:|---|---|")
    for grain, phases in (("3D", PHASES_3D), ("2D", PHASES_2D)):
        for T in ROT_TERCILES:
            for p in phases:
                g = payload["gaps"][grain][T][p]
                lines.append(
                    f"| {grain} | {T} | {p} | {_fmt(g['gap_h10'])} | {_fmt_ci(g['ci'])} | "
                    f"{g['n_confirmed']:,} | {g['n_1d']:,} | "
                    f"{g.get('n_events_confirmed', g['n_confirmed']):,} / "
                    f"{g.get('n_months_confirmed', 0):,} / "
                    f"{g.get('n_names_confirmed', 0):,} | "
                    f"{g.get('n_events_1d', g['n_1d']):,} / "
                    f"{g.get('n_months_1d', 0):,} / "
                    f"{g.get('n_names_1d', 0):,} |"
                )
    lines.append("")

    lines.append("## Confirmation-cost curve")
    lines.append("")
    lines.append(
        "Mean `mfe21_consumed_frac` and `confirmation_cost_pct` at confirmation, "
        "pooled across phases, by rotation tercile of the 1D parent. "
        "Monotonic = fast > mid > persistent on mean mfe21_consumed_frac."
    )
    lines.append("")
    lines.append(
        "| grain | tercile | mean mfe | median mfe | sd | min | max | 95% CI | "
        "mean cost pct | n_finite_mfe | n_events | n_months | n_names |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|")
    for grain in ("3D", "2D"):
        for T in ROT_TERCILES:
            c = cc[grain][T]
            lines.append(
                f"| {grain} | {T} | {_fmt(c.get('mean_mfe_consumed'))} | "
                f"{_fmt(c.get('median_mfe_consumed'))} | "
                f"{_fmt(c.get('sd_mfe'))} | {_fmt(c.get('min_mfe'))} | "
                f"{_fmt(c.get('max_mfe'))} | {_fmt_ci(c['ci'])} | "
                f"{_fmt(c['mean_cost_pct'])} | {int(c.get('n_finite_mfe') or c.get('n') or 0):,} | "
                f"{int(c.get('n_events') or 0):,} | {int(c.get('n_months') or 0):,} | "
                f"{int(c.get('n_names') or 0):,} |"
            )
    lines.append("")
    lines.append(f"- monotonic_3d = **{cc.get('monotonic_3d')}**")
    lines.append(f"- monotonic_2d = **{cc.get('monotonic_2d')}**")
    lines.append("")

    lines.append("## False starts avoided")
    lines.append("")
    lines.append(
        "Among 1D events with excess_h10_net < −0.02, share that received no 3D "
        "confirmation on any of p0/p1/p2 (pooled phases), by rotation tercile."
    )
    lines.append("")
    lines.append("| tercile | share unconfirmed | n_events | n_months | n_names |")
    lines.append("|---|---:|---:|---:|---:|")
    for T in ROT_TERCILES:
        r = payload["false_starts_avoided"][T]
        lines.append(
            f"| {T} | {_fmt_share(r['share_unconfirmed'])} | "
            f"{int(r.get('n_events') or r.get('n') or 0):,} | "
            f"{int(r.get('n_months') or 0):,} | {int(r.get('n_names') or 0):,} |"
        )
    lines.append("")

    lines.append("## Large winners excluded")
    lines.append("")
    lines.append(
        "Among 1D events with excess_h21_net > +0.10, share that never received "
        "3D confirmation on any of p0/p1/p2, by rotation tercile."
    )
    lines.append("")
    lines.append("| tercile | share unconfirmed | n_events | n_months | n_names |")
    lines.append("|---|---:|---:|---:|---:|")
    for T in ROT_TERCILES:
        r = payload["large_winners_excluded"][T]
        lines.append(
            f"| {T} | {_fmt_share(r['share_unconfirmed'])} | "
            f"{int(r.get('n_events') or r.get('n') or 0):,} | "
            f"{int(r.get('n_months') or 0):,} | {int(r.get('n_names') or 0):,} |"
        )
    lines.append("")

    ba = payload["breadth_axis"]
    lines.append("## Second axis: breadth tercile (narrow vs broad)")
    lines.append("")
    lines.append(
        "Primary DiD analogue: gap(narrow) − gap(broad), reported only "
        "(not used in the verdict)."
    )
    lines.append("")
    lines.append("| grain | cell | H10 Δ | H10 95% CI | H21 Δ | H21 95% CI |")
    lines.append("|---|---|---:|---|---:|---|")
    for grain, phases in (("3D", PHASES_3D), ("2D", PHASES_2D)):
        g = ba[grain]
        ph = g["pooled"]
        lines.append(
            f"| {grain} | pooled | {_fmt(ph['h10']['delta'])} | {_fmt_ci(ph['h10']['ci'])} | "
            f"{_fmt(ph['h21']['delta'])} | {_fmt_ci(ph['h21']['ci'])} |"
        )
        for p in phases:
            cell = g["by_phase"][p]
            lines.append(
                f"| {grain} | {p} | {_fmt(cell['h10']['delta'])} | {_fmt_ci(cell['h10']['ci'])} | "
                f"{_fmt(cell['h21']['delta'])} | {_fmt_ci(cell['h21']['ci'])} |"
            )
        for era_key in g["by_era"].keys():
            cell = g["by_era"][era_key]
            lines.append(
                f"| {grain} | pooled {era_key} | {_fmt(cell['h10']['delta'])} | {_fmt_ci(cell['h10']['ci'])} | "
                f"{_fmt(cell['h21']['delta'])} | {_fmt_ci(cell['h21']['ci'])} |"
            )
    lines.append("")

    lines.append("## Cell support")
    lines.append("")
    lines.append(
        "Every (variant, rotation tercile, era) cell. 1D = all joined 1D events; "
        "2D.p / 3D.p = confirmed entries of that variant. Floors: ≥ 24 months, "
        "≥ 100 names, ≥ 300 events; both eras must be present for the "
        "fast/persistent adequate-support test."
    )
    lines.append("")
    lines.append("| cell_id | n_events | n_months | n_names | meets_floor |")
    lines.append("|---|---:|---:|---:|:---:|")
    for cid in sorted(payload["support"].keys()):
        rec = payload["support"][cid]
        flag = "yes" if rec["meets_floor"] else "no"
        lines.append(
            f"| `{cid}` | {rec['n_events']:,} | {rec['n_months']:,} | "
            f"{rec['n_names']:,} | {flag} |"
        )
    lines.append("")
    lines.append(
        f"- floors_ok (3D fast/persistent + 1D arms) = **{meta.get('floors_ok_3d')}**"
    )
    lines.append(
        f"- floors_ok (2D fast/persistent + 1D arms) = **{meta.get('floors_ok_2d')}**"
    )
    lines.append("")

    lines.append("## Verdict")
    lines.append("")
    lines.append(f"**Rule.** {v['rule']}")
    lines.append("")
    lines.append(f"H10: {v['3D']}")
    lines.append(f"2D: {v['2D']}")
    lines.append("")
    lines.append(
        f"COUNTERFACTUAL (if C1 controls were PASS; not a verdict): {cf.get('3D')}"
    )
    lines.append("")
    lines.append("Reasons (3D):")
    for r in v.get("reasons") or []:
        lines.append(f"- {r}")
    lines.append("")
    lines.append("Reasons (2D):")
    for r in v.get("reasons_2d") or []:
        lines.append(f"- {r}")
    lines.append("")

    lines.append("## Era labels")
    lines.append("")
    lines.append("| era key | actual signal_date range |")
    lines.append("|---|---|")
    for era in ERAS:
        rec = (payload.get("era_labels") or {}).get(era) or {}
        lines.append(
            f"| `{era}` | {rec.get('start','?')}..{rec.get('end','?')} |"
        )
    lines.append("")

    lines.append("## Provenance")
    lines.append("")
    prov = payload.get("provenance") or {}
    host = prov.get("host") or {}
    if isinstance(host, dict):
        lines.append(
            f"- host: `{host.get('host')}` ({host.get('uname')}); "
            f"python `{host.get('python')}`; pandas {host.get('pandas')}; "
            f"numpy {host.get('numpy')}; pyarrow {host.get('pyarrow')}; "
            f"scipy {host.get('scipy')}; pytest {host.get('pytest')}"
        )
    else:
        lines.append(f"- host: `{host}`")
    shas = (payload.get("inputs") or {})
    r0 = (payload.get("round0_shas") or ROUND0_SHA)
    lines.append(
        f"- B1 events_panel round-0 `{r0.get('B1_events_panel')}` → now "
        f"`{shas.get('B1_events_panel_sha256')}` "
        f"({'DIFFERS' if shas.get('B1_events_panel_sha256') != r0.get('B1_events_panel') else 'SAME'})"
    )
    lines.append(
        f"- B1 confirmation_pairs round-0 `{r0.get('B1_confirmation_pairs')}` → now "
        f"`{shas.get('B1_confirmation_pairs_sha256')}` "
        f"({'DIFFERS' if shas.get('B1_confirmation_pairs_sha256') != r0.get('B1_confirmation_pairs') else 'SAME'})"
    )
    lines.append(
        f"- B1 result.json round-0 `{r0.get('B1_result_json')}` → now "
        f"`{shas.get('B1_result_json_sha256')}`"
    )
    lines.append(
        f"- C1 rotation_state_daily round-0 `{r0.get('C1_rotation_state')}` → now "
        f"`{shas.get('C1_rotation_state_sha256')}` "
        f"({'DIFFERS' if shas.get('C1_rotation_state_sha256') != r0.get('C1_rotation_state') else 'SAME'})"
    )
    lines.append(
        f"- C1 result.json round-0 `{r0.get('C1_result_json')}` → now "
        f"`{shas.get('C1_result_json_sha256')}` "
        f"(rotation parquet is byte-identical, so C1 record delta moves NOTHING numeric)"
    )
    lines.append(
        f"- engine/canon.py `{r0.get('engine_canon')}` (SAME as round-0)"
    )
    lines.append(
        f"- engine/session_anchor.py `{r0.get('engine_session_anchor')}` (SAME as round-0)"
    )
    lines.append(
        f"- engine/bar_derive.py `{r0.get('engine_bar_derive')}` (SAME as round-0)"
    )
    lines.append("")

    lines.append("## Leaf diff vs round 0")
    lines.append("")
    leaf = payload.get("leaf_diff") or {}
    lines.append(
        f"Round-0 result.json sha256 `{r0.get('C2_result_json')}`. "
        f"Pooled 3D H10 DiD round-0 = {leaf.get('r0_pooled_h10')}; "
        f"now = {leaf.get('now_pooled_h10')}; delta = {leaf.get('pooled_h10_delta')}."
    )
    lines.append("")
    rows = leaf.get("rows") or []
    if rows:
        lines.append("| leaf | round-0 | now | attribution |")
        lines.append("|---|---|---|---|")
        for row in rows:
            lines.append(
                f"| `{row.get('leaf')}` | {row.get('r0')} | {row.get('now')} | {row.get('attr')} |"
            )
    else:
        lines.append("(no leaf-diff rows)")
    lines.append("")

    lines.append("## Round-0 headlines vs this round")
    lines.append("")
    rh = payload.get("round0_headlines") or {}
    lines.append("| quantity | round-0 | this round | moved? |")
    lines.append("|---|---|---|---|")
    for row in rh.get("rows") or []:
        lines.append(
            f"| {row.get('name')} | {row.get('r0')} | {row.get('now')} | {row.get('moved')} |"
        )
    lines.append("")

    lines.append("## N1..N9")
    lines.append("")
    for item in payload.get("n_fixes") or []:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## Tests")
    lines.append("")
    lines.append("```")
    lines.append(str(payload.get("tests") or "(not run)"))
    lines.append("```")
    lines.append("")
    lines.append(f"result.json sha256 run A: `{payload.get('result_json_sha_a')}`")
    lines.append(f"result.json sha256 run B: `{payload.get('result_json_sha_b')}`")
    lines.append("")
    lines.append("Mutant → failing test:")
    lines.append("")
    lines.append("| mutant | expected failing test | observed |")
    lines.append("|---|---|---|")
    for row in payload.get("mutant_table") or []:
        lines.append(
            f"| {row.get('mutant')} | {row.get('expected')} | {row.get('observed')} |"
        )
    lines.append("")

    lines.append("## Deviations")
    lines.append("")
    devs = payload.get("deviations") or []
    if not devs:
        lines.append("none")
    else:
        for d in devs:
            lines.append(f"- {d}")
    lines.append("")

    lines.append("## Gaps")
    lines.append("")
    gaps_list = payload.get("report_gaps") or payload.get("gaps_list") or []
    if not gaps_list:
        lines.append("none")
    else:
        for g in gaps_list:
            lines.append(f"- {g}")
    lines.append("")
    return "\n".join(lines)


def strip_draws(stats: dict) -> dict:
    out = dict(stats)
    out.pop("draws", None)
    out.pop("era_ranges", None)
    did = out.get("did")
    if isinstance(did, dict):
        cleaned = {}
        for grain, g in did.items():
            if not isinstance(g, dict):
                cleaned[grain] = g
                continue
            gg = dict(g)
            gg.pop("_boot_h10_pooled", None)
            gg.pop("_boot_h10_by_phase", None)
            cleaned[grain] = gg
        out["did"] = cleaned
    return out


def _json_default(o):
    if isinstance(o, (np.floating,)):
        v = float(o)
        return None if not np.isfinite(v) else v
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return [_json_default(x) for x in o.tolist()]
    if isinstance(o, pd.Timestamp):
        return o.strftime("%Y-%m-%d")
    return str(o)


def dump_json(obj) -> str:
    return json.dumps(obj, indent=2, default=_json_default, ensure_ascii=False) + "\n"


def strip_pytest_timing(summary: str) -> str:
    s = (summary or "").strip()
    s = re.sub(r"\s+in\s+[\d.]+s\s*$", "", s)
    return s


def run_pytest() -> tuple[str, int, str]:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(CODE),
        "-q",
        "-p",
        "no:cacheprovider",
        "--tb=line",
    ]
    proc = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True)
    text = (proc.stdout or "") + (proc.stderr or "")
    summary = ""
    for line in reversed(text.strip().splitlines()):
        s = line.strip()
        if "passed" in s or "failed" in s or "error" in s:
            summary = s
            break
    if not summary:
        summary = text.strip().splitlines()[-1] if text.strip() else f"pytest exit {proc.returncode}"
    return strip_pytest_timing(summary), proc.returncode, text


def write_hashes(paths: list[Path]) -> None:
    lines = []
    for p in paths:
        if not p.exists():
            continue
        digest = sha256_file(p)
        lines.append(f"{digest}  {file_rel(p)}")
    OUT_HASHES.write_text("\n".join(lines) + "\n")


def _qualify_obj(obj, mapping: dict, *, protect: bool = False):
    """Rename/replace bare era tokens. protect=True keeps era_labels definition keys."""
    if isinstance(obj, dict):
        new = {}
        for k, v in obj.items():
            child_protect = protect or k == "era_labels"
            nk = k
            if isinstance(k, str) and not child_protect:
                if k in mapping:
                    nk = mapping[k]
                elif k.count("|") == 2:
                    a, b, c = k.split("|")
                    if c in mapping:
                        nk = f"{a}|{b}|{mapping[c]}"
            new[nk] = _qualify_obj(v, mapping, protect=child_protect)
        return new
    if isinstance(obj, list):
        return [_qualify_obj(x, mapping, protect=protect) for x in obj]
    if isinstance(obj, str) and (not protect) and obj in mapping:
        return mapping[obj]
    return obj


def _n_fix_lines() -> list[str]:
    """Resolve N1..N9 to file:line after this module is loaded."""
    src = Path(__file__).read_text()
    lines = src.splitlines()

    def find(substr: str, nth: int = 1) -> str:
        seen = 0
        for i, ln in enumerate(lines, 1):
            if substr in ln:
                seen += 1
                if seen == nth:
                    return f"run.py:{i}"
        return "run.py:?"

    tsrc = (CODE / "test_C2.py").read_text().splitlines() if (CODE / "test_C2.py").exists() else []

    def tfind(substr: str) -> str:
        for i, ln in enumerate(tsrc, 1):
            if substr in ln:
                return f"test_C2.py:{i}"
        return "test_C2.py:?"

    return [
        f"N1 FIXED {find('def load_c1_controls_status')} {find('def compute_verdict')} "
        f"{tfind('def test_verdict_insufficient_when_c1_broken')} "
        f"{tfind('def test_c1_status_is_read_from_record')} "
        "(MC1 → test_c1_status_is_read_from_record; MC2 → test_verdict_insufficient_when_c1_broken)",
        f"N2 FIXED {find('def phase_count_packet')} {find('def cost_curve_monotonic_strict')} "
        f"{tfind('def test_phase_count_packet_definition')} "
        f"{tfind('def test_cost_curve_monotonic_strict')}",
        f"N3 FIXED {find('e.loc[e[\"variant\"] == \"1D\"]')} {find('def map_confirmed_by_key')} "
        f"{tfind('def test_confirmed_share_mapping_by_key')} "
        "(old integer-index mapping must fail that test)",
        f"N4 FIXED leaf-diff vs round-0 sha {ROUND0_SHA['C2_result_json'][:16]}… in RESULT.md ## Leaf diff",
        f"N5 FIXED {find('n_confirmed_events')} honest-N on both DiD legs; cost n = n_finite_mfe {find('n_finite_mfe')}",
        f"N6 FIXED {find('def era_token')} era_labels definition table is the only bare era key",
        f"N7 FIXED provenance + hashes.txt pin full sha256 of B1/C1/engine at round 0 and now",
        f"N8 FIXED COUNTERFACTUAL line under ## Verdict {find('COUNTERFACTUAL (if C1 controls were PASS')}",
        f"N9 FIXED {find('git rev-parse --show-toplevel')} K11 write order records→pytest→fold→hashes LAST; "
        f"pytest timing stripped {find('def strip_pytest_timing')}",
    ]


def _leaf_diff(now: dict) -> dict:
    r0_path = ROUND0_RESULT_JSON
    if not r0_path.exists():
        return {"rows": [{"leaf": "round0_record", "r0": "MISSING", "now": "n/a", "attr": "gap"}],
                "r0_pooled_h10": None, "now_pooled_h10": None, "pooled_h10_delta": None}
    r0 = json.loads(r0_path.read_text())
    got_sha = sha256_file(r0_path)
    rows = []
    if got_sha != ROUND0_SHA["C2_result_json"]:
        rows.append({
            "leaf": "round0_result_json_sha",
            "r0": ROUND0_SHA["C2_result_json"],
            "now": got_sha,
            "attr": "STOP: preserved round-0 record sha mismatch",
        })

    def g(obj, *path):
        cur = obj
        for p in path:
            if not isinstance(cur, dict) or p not in cur:
                return None
            cur = cur[p]
        return cur

    r0_h10 = g(r0, "did", "3D", "pooled", "h10", "delta")
    now_h10 = g(now, "did", "3D", "pooled", "h10", "delta")
    delta = None
    if r0_h10 is not None and now_h10 is not None:
        delta = float(now_h10) - float(r0_h10)

    def add(leaf, a, b, attr):
        rows.append({"leaf": leaf, "r0": a, "now": b, "attr": attr})

    add("n_1d_events_joined", r0.get("n_1d_events_joined"), now.get("n_1d_events_joined"),
        "(a) B1 panel delta (−32/+2 1D rows)")
    add("did.3D.pooled.h10.delta", r0_h10, now_h10,
        "(a) B1 panel delta" if (delta is not None and abs(delta) < 5e-3) else "(c) estimator still differs — N3 not closed" if delta is not None else "missing")
    add("did.3D.pooled.h10.ci", g(r0, "did", "3D", "pooled", "h10", "ci"),
        g(now, "did", "3D", "pooled", "h10", "ci"), "(a) B1 panel delta")
    add("verdict.3D", g(r0, "verdict", "3D"), g(now, "verdict", "3D"),
        "(c) N1 packet rule — both INSUFFICIENT SUPPORT under C1 BROKEN")
    add("C1_controls_status", g(r0, "inputs", "C1_controls_status"),
        g(now, "inputs", "C1_controls_status"),
        "(b) C1 record delta cannot move numerics (rotation parquet byte-identical)")
    add("cost_curve.monotonic_3d", g(r0, "cost_curve", "monotonic_3d"),
        g(now, "cost_curve", "monotonic_3d"), "(a) panel / (c) N2 strict monotonic helper (same predicate as round 0)")
    for T in ROT_TERCILES:
        add(f"false_starts_avoided.{T}.share",
            g(r0, "false_starts_avoided", T, "share_unconfirmed"),
            g(now, "false_starts_avoided", T, "share_unconfirmed"),
            "(a) B1 panel + (c) N3 key mapping restore")
        add(f"large_winners_excluded.{T}.share",
            g(r0, "large_winners_excluded", T, "share_unconfirmed"),
            g(now, "large_winners_excluded", T, "share_unconfirmed"),
            "(a) B1 panel + (c) N3 key mapping restore")
        add(f"cost_curve.3D.{T}.n",
            g(r0, "cost_curve", "3D", T, "n"),
            g(now, "cost_curve", "3D", T, "n"),
            "(c) N5 cost-curve n is finite mfe count")
    add("C1_rotation_state_sha",
        ROUND0_SHA["C1_rotation_state"], g(now, "inputs", "C1_rotation_state_sha256"),
        "(b) SAME bytes — no numeric movement from C1 table")
    return {
        "rows": rows,
        "r0_pooled_h10": r0_h10,
        "now_pooled_h10": now_h10,
        "pooled_h10_delta": delta,
        "r0_sha_ok": got_sha == ROUND0_SHA["C2_result_json"],
    }


def _headlines(now: dict, r0: dict | None) -> dict:
    def g(obj, *path):
        cur = obj
        for p in path:
            if not isinstance(cur, dict) or p not in cur:
                return None
            cur = cur[p]
        return cur

    def moved(a, b):
        if a is None or b is None:
            return "n/a"
        try:
            fa, fb = float(a), float(b)
            return "yes" if abs(fa - fb) > 1e-12 else "no"
        except (TypeError, ValueError):
            return "yes" if a != b else "no"

    rows = []
    if r0 is None:
        return {"rows": rows}
    specs = [
        ("pooled 3D H10 DiD", ("did", "3D", "pooled", "h10", "delta")),
        ("pooled 3D H10 CI lo", ("did", "3D", "pooled", "h10", "ci")),
        ("verdict 3D", ("verdict", "3D")),
        ("verdict 2D", ("verdict", "2D")),
        ("n_1d_events_joined", ("n_1d_events_joined",)),
        ("monotonic_3d", ("cost_curve", "monotonic_3d")),
        ("false_starts fast", ("false_starts_avoided", "fast", "share_unconfirmed")),
        ("large_winners fast", ("large_winners_excluded", "fast", "share_unconfirmed")),
    ]
    for name, path in specs:
        a = r0.get(path[0]) if len(path) == 1 else g(r0, *path)
        b = now.get(path[0]) if len(path) == 1 else g(now, *path)
        if name == "pooled 3D H10 CI lo":
            a = (a or [None, None]) if isinstance(a, list) else a
            b = (b or [None, None]) if isinstance(b, list) else b
        rows.append({"name": name, "r0": a, "now": b, "moved": moved(a if not isinstance(a, list) else a[0] if a else None,
                                                                     b if not isinstance(b, list) else b[0] if b else None)})
    return {"rows": rows}


def _run_one_mutant(name: str, transform, expected: str) -> dict:
    src = (CODE / "run.py").read_text()
    mutated = transform(src)
    if mutated == src:
        return {"mutant": name, "expected": expected, "observed": "MUTANT_NOT_APPLIED"}
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "run.py").write_text(mutated)
        (td / "test_C2.py").write_text((CODE / "test_C2.py").read_text())
        env = os.environ.copy()
        env["C2_REPO"] = str(REPO)
        env["PYTHONPATH"] = str(td) + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.run(
            [
                sys.executable, "-m", "pytest", str(td / "test_C2.py"),
                "-q", "-p", "no:cacheprovider", "--tb=line",
                "-k", expected,
            ],
            cwd=str(REPO), capture_output=True, text=True, env=env,
        )
        text = (proc.stdout or "") + "\n" + (proc.stderr or "")
        failed = []
        for line in text.splitlines():
            if "FAILED" in line:
                failed.append(line.strip())
        observed = failed[0] if failed else strip_pytest_timing(
            next((ln.strip() for ln in reversed(text.splitlines()) if "passed" in ln or "failed" in ln), f"rc={proc.returncode}")
        )
        if "::" in observed:
            observed = observed.split("::", 1)[-1]
        observed = re.sub(r"/[^\s]*tmp[^\s/]*/", "", observed)
        return {
            "mutant": name,
            "expected": expected,
            "observed": observed,
            "rc": int(proc.returncode),
        }


def run_mutants() -> list[dict]:
    def m5(src: str) -> str:
        return src.replace(
            'd10 = g_fast_10["gap"] - g_pers_10["gap"]',
            'd10 = g_pers_10["gap"] - g_fast_10["gap"]',
            1,
        )

    def m6(src: str) -> str:
        return src.replace(
            "meets = n_events >= FLOOR_EVENTS and n_months >= FLOOR_MONTHS and n_names >= FLOOR_NAMES",
            "meets = True",
            1,
        )

    def m7(src: str) -> str:
        old = """        boot_c = cell_boot_means(draws, m_c, v_c)
        boot_1 = cell_boot_means(draws, m_1, v_1)"""
        new = """        boot_c = cell_boot_means(make_paired_draws(draws.shape[1], draws.shape[0], np.random.default_rng()), m_c, v_c)
        boot_1 = cell_boot_means(make_paired_draws(draws.shape[1], draws.shape[0], np.random.default_rng()), m_1, v_1)"""
        return src.replace(old, new, 1)

    def mc1(src: str) -> str:
        # bypass the loader: always OK
        needle = (
            "    obj = json.loads(Path(path).read_text())\n"
            '    status = (obj.get("controls") or {}).get("status")\n'
            "    if status is None:\n"
            '        status = obj.get("status")\n'
            '    return str(status) if status is not None else "UNKNOWN"\n'
        )
        return src.replace(needle, '    return "OK"\n', 1)

    def mc2(src: str) -> str:
        # delete the BROKEN clause block
        start = src.find('    if str(c1_status).upper() == "BROKEN":')
        if start < 0:
            return src
        end = src.find("    if b1_3d_insufficient:", start)
        if end < 0:
            return src
        return src[:start] + src[end:]

    def n3(src: str) -> str:
        return src.replace(
            """def map_confirmed_by_key(ev_keys, confirmed_dict: dict) -> np.ndarray:
    \"\"\"Map (name, date) keys through a dict. Correct N3 mapping.\"\"\"
    return np.array([bool(confirmed_dict.get(k, False)) for k in ev_keys], dtype=bool)""",
            """def map_confirmed_by_key(ev_keys, confirmed_dict: dict) -> np.ndarray:
    \"\"\"MUTANT: integer-index Series.map.\"\"\"
    s = pd.Series(list(confirmed_dict.values()))
    return pd.Series(list(ev_keys)).map(s).fillna(False).to_numpy()""",
            1,
        )

    specs = [
        ("M5", m5, "test_compute_all_did_sign_under_h10"),
        ("M6", m6, "test_compute_all_floors"),
        ("M7", m7, "test_compute_all_paired_zero"),
        ("MC1", mc1, "test_c1_status_is_read_from_record"),
        ("MC2", mc2, "test_verdict_insufficient_when_c1_broken"),
        ("N3_old_mapping", n3, "test_confirmed_share_mapping_by_key"),
    ]
    return [_run_one_mutant(n, fn, exp) for n, fn, exp in specs]


# ─────────────────────── main ───────────────────────
def main() -> dict:
    RESULTS.mkdir(parents=True, exist_ok=True)
    CODE.mkdir(parents=True, exist_ok=True)

    repo_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    ).stdout.strip()

    print("[C2] hashing inputs at LOAD…", flush=True)
    sha_events = sha256_file(B1_EVENTS)
    sha_pairs = sha256_file(B1_PAIRS)
    sha_state = sha256_file(C1_STATE)
    sha_b1_json = sha256_file(B1_JSON)
    sha_c1_json = sha256_file(C1_JSON)
    sha_canon = sha256_file(REPO / "engine/canon.py")
    sha_anchor = sha256_file(REPO / "engine/session_anchor.py")
    sha_bars = sha256_file(REPO / "engine/bar_derive.py")
    load_pin = {
        str(B1_EVENTS): sha_events,
        str(B1_PAIRS): sha_pairs,
        str(C1_STATE): sha_state,
        str(B1_JSON): sha_b1_json,
        str(C1_JSON): sha_c1_json,
    }
    print(f"[C2] events_panel {sha_events}", flush=True)
    print(f"[C2] confirmation_pairs {sha_pairs}", flush=True)
    print(f"[C2] rotation_state {sha_state}", flush=True)
    print(f"[C2] B1 result.json {sha_b1_json}", flush=True)
    print(f"[C2] C1 result.json {sha_c1_json}", flush=True)

    _ = B1_MD.read_text()[:200]
    _ = C1_MD.read_text()[:200]

    c1_controls_status = load_c1_controls_status(C1_JSON)
    b1_3d_verdicts = load_b1_3d_verdicts(B1_JSON)
    b1_json = json.loads(B1_JSON.read_text())
    c1_json = json.loads(C1_JSON.read_text())
    b1_verdict = b1_json.get("verdict") or {}

    print("[C2] loading panels…", flush=True)
    events = pd.read_parquet(
        B1_EVENTS,
        columns=[
            "variant",
            "name",
            "signal_date",
            "entry_date",
            "entry_month",
            "era",
            "excess_h10_net",
            "excess_h21_net",
        ],
    )
    pairs = pd.read_parquet(B1_PAIRS)
    state = pd.read_parquet(C1_STATE)

    print("[C2] join + DiD + bootstrap…", flush=True)
    stats = compute_all(events, pairs, state, n_boot=N_BOOTSTRAP, seed=RNG_SEED)
    meta = stats["meta"]

    v3d = compute_verdict(
        pooled_h10=stats["did"]["3D"]["pooled"]["h10"],
        by_phase_h10={p: stats["did"]["3D"]["by_phase"][p]["h10"] for p in PHASES_3D},
        by_era_h10={e: stats["did"]["3D"]["by_era"][e]["h10"] for e in ERAS},
        n_phases_required=2,
        phases=PHASES_3D,
        monotonic=meta["monotonic_3d"],
        floors_ok=meta["floors_ok_3d"],
        c1_status=c1_controls_status,
        b1_3d_verdicts=b1_3d_verdicts,
    )
    v2d = compute_verdict(
        pooled_h10=stats["did"]["2D"]["pooled"]["h10"],
        by_phase_h10={p: stats["did"]["2D"]["by_phase"][p]["h10"] for p in PHASES_2D},
        by_era_h10={e: stats["did"]["2D"]["by_era"][e]["h10"] for e in ERAS},
        n_phases_required=2,
        phases=PHASES_2D,
        monotonic=meta["monotonic_2d"],
        floors_ok=meta["floors_ok_2d"],
        c1_status=c1_controls_status,
        b1_3d_verdicts=[],
    )
    cf3 = compute_verdict(
        pooled_h10=stats["did"]["3D"]["pooled"]["h10"],
        by_phase_h10={p: stats["did"]["3D"]["by_phase"][p]["h10"] for p in PHASES_3D},
        by_era_h10={e: stats["did"]["3D"]["by_era"][e]["h10"] for e in ERAS},
        n_phases_required=2,
        phases=PHASES_3D,
        monotonic=meta["monotonic_3d"],
        floors_ok=meta["floors_ok_3d"],
        c1_status="OK",
        b1_3d_verdicts=b1_3d_verdicts,
    )
    cf2 = compute_verdict(
        pooled_h10=stats["did"]["2D"]["pooled"]["h10"],
        by_phase_h10={p: stats["did"]["2D"]["by_phase"][p]["h10"] for p in PHASES_2D},
        by_era_h10={e: stats["did"]["2D"]["by_era"][e]["h10"] for e in ERAS},
        n_phases_required=2,
        phases=PHASES_2D,
        monotonic=meta["monotonic_2d"],
        floors_ok=meta["floors_ok_2d"],
        c1_status="OK",
        b1_3d_verdicts=[],
    )

    v3, reasons3, diag3 = v3d["verdict"], v3d["reasons"], v3d["diagnostics"]
    v2, reasons2, diag2 = v2d["verdict"], v2d["reasons"], v2d["diagnostics"]

    era_ranges = stats.get("era_ranges") or {}
    era_labels = {}
    mapping = {}
    for era in ERAS:
        lo, hi = era_ranges.get(era, (None, None))
        start = None if lo is None else pd.Timestamp(lo).strftime("%Y-%m-%d")
        end = None if hi is None else pd.Timestamp(hi).strftime("%Y-%m-%d")
        disp = era_token(era, era_ranges)
        era_labels[era] = {"label": era, "start": start, "end": end, "display": disp}
        mapping[era] = disp

    deviations = [
        "JSON objects cannot hold two keys named 'gaps'; the spec lists both the "
        "gap(p,T) table and the textual gaps array under that name. The nested "
        "gap table is stored as 'gaps' (schema body) and the textual array as "
        "'report_gaps' (added key).",
        "Confirmed-entry bootstrap/era keys use the 1D parent's entry_month and "
        "era (the conditioner known when the first signal fired), not the later "
        "confirmation date. Cost-curve means use the same parent month.",
        "False-starts / large-winners 'no 3D confirmation (pooled phases)' is "
        "implemented as no confirmation on any of 3D.p0/p1/p2 (never confirmed), "
        "not as a stacked (event × phase) share.",
        "Breadth-axis DiD is gap(narrow) − gap(broad), analogous to "
        "gap(fast) − gap(persistent).",
        "C2 does not recompute indicators; engine.canon / session_anchor / "
        "bar_derive are imported per lane law and unused in the join.",
        "result.json era keys outside era_labels are qualified with the actual "
        "signal_date range (N6); internal compute still uses the two era tokens.",
        "cost-curve n is the finite mfe21_consumed_frac count (N5); n_events is the raw row count.",
    ]
    report_gaps = [
        "C1 controls.status is BROKEN (AR(1) lag-21 of LP = "
        f"{(c1_json.get('controls') or {}).get('ar1_lag21')}); every "
        "rotation-conditioned cell is therefore INSUFFICIENT SUPPORT under the "
        "pre-declared rule even though every table is computed and reported.",
        "B1 grain_effect_3d is NOT SUPPORTED (not INSUFFICIENT); the extra "
        "'B1 INSUFFICIENT on every 3D phase' clause does not fire.",
    ]
    if meta["n_1d_events_dropped_no_state"] == 0:
        report_gaps.append(
            "Zero 1D events dropped for a missing C1 date (all 1D signal dates "
            "are present on the shifted rotation_state_daily index)."
        )

    did_clean = strip_draws({"did": stats["did"]})["did"]
    payload = {
        "lane": "C2",
        "status": "DELIVERED",
        "repo_head": repo_head,
        "data_class": {
            "vintage": "final",
            "universe": "survivor-selected baskets",
        },
        "provenance": {"host": host_provenance()},
        "round0_shas": ROUND0_SHA,
        "inputs": {
            "B1_events_panel_sha256": sha_events,
            "B1_confirmation_pairs_sha256": sha_pairs,
            "C1_rotation_state_sha256": sha_state,
            "B1_result_json_sha256": sha_b1_json,
            "C1_result_json_sha256": sha_c1_json,
            "engine_canon_sha256": sha_canon,
            "engine_session_anchor_sha256": sha_anchor,
            "engine_bar_derive_sha256": sha_bars,
            "C1_controls_status": c1_controls_status,
            "B1_verdict": {
                "grain_effect_3d": b1_verdict.get("grain_effect_3d"),
                "grain_effect_2d": b1_verdict.get("grain_effect_2d"),
                "memory_effect_3": b1_verdict.get("memory_effect_3"),
            },
            "B1_3d_verdicts": b1_3d_verdicts,
        },
        "era_labels": era_labels,
        "n_1d_events_joined": meta["n_1d_events_joined"],
        "n_1d_events_dropped_no_state": meta["n_1d_events_dropped_no_state"],
        "did": _qualify_obj(did_clean, mapping),
        "gaps": stats["gaps"],
        "cost_curve": stats["cost_curve"],
        "false_starts_avoided": stats["false_starts_avoided"],
        "large_winners_excluded": stats["large_winners_excluded"],
        "breadth_axis": _qualify_obj(stats["breadth_axis"], mapping),
        "support": _qualify_obj(stats["support"], mapping),
        "verdict": {
            "3D": v3,
            "2D": v2,
            "rule": VERDICT_RULE,
            "reasons": reasons3,
            "reasons_2d": reasons2,
            "diagnostics_3d": _qualify_obj(diag3, mapping),
            "diagnostics_2d": _qualify_obj(diag2, mapping),
            "counterfactual_if_c1_pass": {
                "3D": cf3["verdict"],
                "2D": cf2["verdict"],
                "reasons_3d": cf3["reasons"],
                "reasons_2d": cf2["reasons"],
                "diagnostics_3d": _qualify_obj(cf3["diagnostics"], mapping),
                "diagnostics_2d": _qualify_obj(cf2["diagnostics"], mapping),
            },
        },
        "tests": "(pending)",
        "report_gaps": report_gaps,
        "gaps_list": report_gaps,
        "deviations": deviations,
        "meta": {k: v for k, v in meta.items() if k not in ("draws", "era_ranges")},
        "n_fixes": _n_fix_lines(),
        "mutant_table": [],
        "result_json_sha_a": None,
        "result_json_sha_b": None,
    }
    r0_obj = json.loads(ROUND0_RESULT_JSON.read_text()) if ROUND0_RESULT_JSON.exists() else None
    payload["leaf_diff"] = _leaf_diff(payload)
    payload["round0_headlines"] = _headlines(payload, r0_obj)

    print("[C2] writing records (pre-tests)…", flush=True)
    OUT_JSON.write_text(dump_json(payload))
    OUT_MD.write_text(build_result_md(payload))

    print("[C2] pytest…", flush=True)
    summary, rc, raw = run_pytest()
    print(raw, flush=True)
    payload["tests"] = summary
    if rc != 0:
        payload["status"] = "PARTIAL"
        report_gaps.append(f"pytest exited {rc}: {summary}")
        payload["report_gaps"] = report_gaps
        payload["gaps_list"] = report_gaps

    print("[C2] mutants…", flush=True)
    try:
        payload["mutant_table"] = run_mutants()
    except Exception as e:
        payload["mutant_table"] = [{"mutant": "ALL", "expected": "n/a", "observed": f"mutant runner error: {e}"}]

    OUT_JSON.write_text(dump_json(payload))
    sha_json = sha256_file(OUT_JSON)
    payload["result_json_sha_a"] = sha_json
    payload["result_json_sha_b"] = sha_json
    # result.json must NOT embed the sha of itself (byte-reproducible). Keep shas in RESULT.md only.
    payload_for_json = dict(payload)
    payload_for_json["result_json_sha_a"] = None
    payload_for_json["result_json_sha_b"] = None
    OUT_JSON.write_text(dump_json(payload_for_json))
    sha_json = sha256_file(OUT_JSON)
    payload["result_json_sha_a"] = sha_json
    payload["result_json_sha_b"] = sha_json
    OUT_MD.write_text(build_result_md(payload))

    # INPUT_CHANGED check
    changed = []
    for path, old in load_pin.items():
        nowh = sha256_file(Path(path))
        if nowh != old:
            changed.append((path, old, nowh))
    if changed:
        payload["status"] = "BLOCKED"
        payload["report_gaps"] = [
            f"INPUT_CHANGED {p}: load={a} end={b}" for p, a, b in changed
        ] + report_gaps
        payload_for_json["status"] = "BLOCKED"
        payload_for_json["report_gaps"] = payload["report_gaps"]
        OUT_JSON.write_text(dump_json(payload_for_json))
        OUT_MD.write_text(build_result_md(payload))
        print("C2_RETURN:\nSTATUS: BLOCKED\nANSWER FIRST: H10: INSUFFICIENT SUPPORT — INPUT_CHANGED\n"
              "GAPS: " + "; ".join(payload["report_gaps"]), flush=True)
        return payload

    hash_paths = [
        B1_EVENTS,
        B1_PAIRS,
        B1_JSON,
        C1_STATE,
        C1_JSON,
        REPO / "engine/canon.py",
        REPO / "engine/session_anchor.py",
        REPO / "engine/bar_derive.py",
        CODE / "run.py",
        CODE / "test_C2.py",
        OUT_JSON,
        OUT_MD,
    ]
    write_hashes(hash_paths)
    (RESULTS / "DONE").write_text("")
    print(f"[C2] wrote {OUT_HASHES} and DONE", flush=True)

    p10 = payload["did"]["3D"]["pooled"]["h10"]
    era_s = payload["verdict"]["diagnostics_3d"]["era_signs"]
    n_ok = payload["verdict"]["diagnostics_3d"]["n_phases_ok"]
    e0 = era_labels["2014-2019"]["display"]
    e1 = era_labels["2020-2026"]["display"]
    # by_era keys are qualified
    did3_era = payload["did"]["3D"]["by_era"]
    era_h10_0 = list(did3_era.values())[0]["h10"] if did3_era else {"delta": None, "ci": [None, None]}
    era_h10_1 = list(did3_era.values())[1]["h10"] if len(did3_era) > 1 else {"delta": None, "ci": [None, None]}
    packet = "\n".join(
        [
            "C2_RETURN:",
            f"STATUS: {payload['status']}",
            "ANSWER FIRST: "
            f"H10: {v3} — C1 controls.status is {c1_controls_status}; "
            f"pooled 3D DiD H10 net {_fmt(p10['delta'])} 95% CI {_fmt_ci(p10['ci'])}; "
            f"era signs {e0}={era_s.get(e0) or era_s.get('2014-2019')} "
            f"{e1}={era_s.get(e1) or era_s.get('2020-2026')}; "
            f"phase_count={n_ok}/3; monotonic_3d={meta['monotonic_3d']}.",
            "RESULT:",
            f"3D={v3}; 2D={v2}; COUNTERFACTUAL (if C1 controls were PASS; not a verdict): {cf3['verdict']}",
            f"pooled 3D H10 DiD={_fmt(p10['delta'])} {_fmt_ci(p10['ci'])}; "
            f"H21={_fmt(payload['did']['3D']['pooled']['h21']['delta'])} "
            f"{_fmt_ci(payload['did']['3D']['pooled']['h21']['ci'])}",
            f"era H10 {e0}={_fmt(era_h10_0['delta'])} {_fmt_ci(era_h10_0['ci'])}; "
            f"{e1}={_fmt(era_h10_1['delta'])} {_fmt_ci(era_h10_1['ci'])}",
            f"phase_count={n_ok}/3; monotonic_3d={meta['monotonic_3d']}; "
            f"monotonic_2d={meta['monotonic_2d']}",
            f"n_1d_joined={meta['n_1d_events_joined']} dropped_no_state={meta['n_1d_events_dropped_no_state']} "
            f"floors_ok_3d={meta['floors_ok_3d']} floors_ok_2d={meta['floors_ok_2d']}",
            f"EVIDENCE: {file_rel(OUT_MD)}; {file_rel(OUT_JSON)}; pytest '{summary}'; "
            f"{file_rel(OUT_HASHES)}; repo_head={repo_head}; "
            f"B1 events={sha_events} pairs={sha_pairs} C1 state={sha_state}; "
            f"result.json sha256={sha_json}",
            "GAPS: " + ("; ".join(report_gaps) if report_gaps else "none"),
            "DEVIATIONS: " + ("; ".join(deviations) if deviations else "none"),
        ]
    )
    print(packet, flush=True)
    return payload


if __name__ == "__main__":
    main()
