from __future__ import annotations

"""Q06 evaluate.py: RESEARCH REFERENCE — NOT WIRED.

Runs the stages frozen in PREREG.md (sha256 pinned in FREEZE.log):

* ``baseline``: reproduces the incumbent FS-4 trainer state from source text,
  config and the retained data directory.
* ``e1``: the one empirical comparison (native-law support accrual, pre-outcome
  geometry only; PREREG §2, §3, §10, §11, §13 K3).
* ``s1``: the fixed synthetic operating-characteristics grid (PREREG §8, §12,
  §13 K1/K2). After the grid, it combines e1.json and s1.json into verdict.json.

Refusals and records:

* It refuses to run when sha256(PREREG.md) differs from the FREEZE.log hash.
* It re-hashes every PREREG §4 input and aborts on any mismatch.
* Grades are read with an explicit, asserted geometry-only column list. No
  outcome column is ever read.
* Every run (including refusals and crashes) is appended to RUNS.log as one
  JSON line: command, stage, exit code, input sha256s and output sha256s.

Interpretations fixed in code before any stage was run:

* K1 rates are conditional on R_alt support holding in that replicate (the
  stricter reading). Unconditional rates are also reported.
* K2 must hold for every (truth, regime) pair within each bucket.
* "Support holds" means the rule's reason does not start with
  ``CALIBRATION_INSUFFICIENT`` or ``NOT_YET_ESTIMABLE``.
"""

import hashlib
import json
import math
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
Q06_ROOT = HERE.parents[2]
if str(Q06_ROOT) not in sys.path:
    sys.path.insert(0, str(Q06_ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import engine.calibration_sparse_weighted as csw  # noqa: E402

DATA_DIR = Path("/Users/chriswong/Documents/Cluade/macro-main/data/flow_signals")
PREREG = HERE / "PREREG.md"
FREEZE = HERE / "FREEZE.log"
RUNS = HERE / "RUNS.log"
AMENDMENT = HERE / "PREREG_AMENDMENT.md"
AMENDMENT_2 = HERE / "PREREG_AMENDMENT_2.md"
# PREREG_AMENDMENT_2.md: the exact code bytes allowed to produce results. evaluate.py refuses
# (exit 2) when CODE_PIN.json is missing or any listed file hashes differently.
CODE_PIN = HERE / "CODE_PIN.json"

PINNED_INPUTS = {
    str(DATA_DIR / "ledger.parquet"): "c14b99cf92c29467d40a823a42e1b8974f018233c76b70d917b403f7a3898b62",
    str(DATA_DIR / "grades.parquet"): "3bb26d6440f262c2f8bac7cfd23313b466ce00091a397a17684cc8cc073e1d32",
    str(DATA_DIR / "gate.json"): "92eec77adb20de9e8599435fda221a361fa24c8d4d7a6ddef99ce453a0f64682",
    str(Q06_ROOT / "config/flow_score.yml"): "f372519b5b41f9c175c1cd044ab0289da464b97963dda8b61e53bea73d53502c",
    str(Q06_ROOT / "lib/flow_score.py"): "e697a9a06f430ee9496e757b67f4cb3d6fc8b5db3376385afd88f261ba096102",
    str(Q06_ROOT / "lib/flow_score_geometry.py"): "1960d0589c76cd2a6a3ecfeb685714357c7ac4997c98ca8d55b202b771469cdf",
    str(Q06_ROOT / "lib/nyse_calendar.py"): "7c9167fd416babb64c3067ae7e6237615011ad79e26d826e57005486496410ce",
    str(Q06_ROOT / "research/OPTIONS_ALPHA_FLOW_SCORE_AMENDMENT.md"): "1c8ac33e0b189d080f41ef74b3e029f91777ad3e9043f5d8eb0ab6e937496d40",
    str(Q06_ROOT / "scripts/ops_train_flow_score.py"): "a174315ab9917f9733a995843452c5cd7590f3b3a9c74e5c8b40f794e9e3469e",
}
CODE_INPUTS = (
    Path(__file__).resolve(),
    Q06_ROOT / "engine/calibration_sparse_weighted.py",
)

LEDGER_COLUMNS = ["event_id", "session_date", "root", "source", "detector_version", "dte_bucket"]
GRADES_GEOMETRY_COLUMNS = [
    "event_id", "graded_ok", "reason_code", "fill_date",
    "outcome_end_session_5", "outcome_end_session_21",
    "outcome_end_session_63", "outcome_end_session_126",
]
FORBIDDEN_PREFIXES = ("fwd_", "spy_excess_", "terminal_state_", "prem_touch_", "entry_price")

BUCKETS = {"0_7": 5, "8_90": 21, "90p": 63}
E1_REPLICATES = 9_999
E1_CHUNK = 1_111
INFEASIBLE_SESSIONS = 2_520

S1_GRID = {5: (252, 504, 1260), 21: (252, 756, 1512, 4536)}
S1_BUCKET_LABEL = {5: "0_7", 21: "8_90"}
S1_REPLICATES = 200
S1_BOOTSTRAP = 299
FR_FK_BAR = 0.10


def sha256_file(path: Path | str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def frozen_hash() -> str:
    text = FREEZE.read_text(encoding="utf-8").strip().splitlines()[0]
    for token in text.split():
        if token.startswith("sha256="):
            return token.split("=", 1)[1]
    raise RuntimeError("freeze_log_unparseable")


def clean(obj: Any) -> Any:
    """JSON-safe conversion: numpy scalars to Python, inf to strings, nan to None."""
    if isinstance(obj, dict):
        return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return [clean(v) for v in obj.tolist()]
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        f = float(obj)
        if math.isnan(f):
            return None
        if math.isinf(f):
            return "inf" if f > 0 else "-inf"
        return f
    return obj


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(clean(payload), indent=1, sort_keys=True) + "\n", encoding="utf-8")


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


def support_holds(rule: dict[str, Any]) -> bool:
    reason = str(rule.get("reason", ""))
    return not reason.startswith(("CALIBRATION_INSUFFICIENT", "NOT_YET_ESTIMABLE"))


# ── stage: baseline ──────────────────────────────────────────────────────────

def stage_baseline() -> tuple[dict[str, Any], list[Path]]:
    import yaml

    src_path = Q06_ROOT / "scripts/ops_train_flow_score.py"
    lines = src_path.read_text(encoding="utf-8").splitlines()
    needles = ("calibration_insufficient", "CALIBRATION_INSUFFICIENT:weighted_bin_method_unavailable")
    hits = {n: [i + 1 for i, line in enumerate(lines) if n in line] for n in needles}
    ece_none = [i + 1 for i, line in enumerate(lines) if '"ece": None' in line or "'ece': None" in line
                or "ece=None" in line]
    cfg = yaml.safe_load((Q06_ROOT / "config/flow_score.yml").read_text(encoding="utf-8"))
    scoring_enabled = cfg.get("scoring", {}).get("enabled")
    gate = json.loads((DATA_DIR / "gate.json").read_text(encoding="utf-8"))
    names = sorted(p.name for p in DATA_DIR.iterdir())
    models_dir = DATA_DIR / "models"
    receipt_like = [n for n in names if any(k in n.lower() for k in ("partition", "receipt", "calibration_eval"))]
    checks = {
        "trainer_insufficient_strings_present": all(hits[n] for n in needles),
        "trainer_ece_none_present": bool(ece_none),
        "scoring_enabled_is_false": scoring_enabled is False,
        "gate_status_building_history": gate.get("status") == "building_history",
        "gate_scored_false": gate.get("scored") is False,
        "models_dir_absent": not models_dir.exists(),
        "no_partition_receipt_in_data_dir": not receipt_like,
    }
    out = {
        "stage": "baseline",
        "reproduced": all(checks.values()),
        "checks": checks,
        "trainer_string_lines": hits,
        "trainer_ece_none_lines": ece_none,
        "config_scoring_enabled": scoring_enabled,
        "gate_status": gate.get("status"),
        "gate_scored": gate.get("scored"),
        "data_dir_entries": names,
        "outcome_calibration": {
            "state": "INSUFFICIENT_DATA",
            "missing": [
                "retained FS-4 fitted model artifact or predictions under data/flow_signals/models "
                "(absent; the directory is gitignored and R2-only, and R2 is forbidden here)",
                "admitted FS-5 population partition receipt naming calibration_eval membership (absent)",
            ],
        },
    }
    path = HERE / "baseline.json"
    write_json(path, out)
    return out, [path]


# ── stage: e1 ────────────────────────────────────────────────────────────────

def _load_cohort() -> tuple[pd.DataFrame, dict[str, Any]]:
    import pyarrow.parquet as pq

    from lib.flow_score import map_model_bucket

    grade_schema = pq.read_schema(DATA_DIR / "grades.parquet")
    for col in GRADES_GEOMETRY_COLUMNS:
        if col not in grade_schema.names:
            raise RuntimeError(f"grades_geometry_column_missing:{col}")
    for col in GRADES_GEOMETRY_COLUMNS:
        if col.startswith(FORBIDDEN_PREFIXES):
            raise RuntimeError("geometry_list_contains_outcome_column")
    ledger = pd.read_parquet(DATA_DIR / "ledger.parquet", columns=LEDGER_COLUMNS)
    grades = pd.read_parquet(DATA_DIR / "grades.parquet", columns=GRADES_GEOMETRY_COLUMNS)
    assert list(grades.columns) == GRADES_GEOMETRY_COLUMNS, "grades_columns_not_geometry_only"
    assert list(ledger.columns) == LEDGER_COLUMNS, "ledger_columns_unexpected"

    funnel: dict[str, Any] = {"ledger_rows": int(len(ledger)), "grade_rows": int(len(grades))}
    funnel["ledger_duplicate_event_id"] = int(ledger["event_id"].duplicated().sum())
    funnel["grades_duplicate_event_id"] = int(grades["event_id"].duplicated().sum())
    ledger = ledger.drop_duplicates("event_id", keep=False)
    grades = grades.drop_duplicates("event_id", keep=False)

    src_ok = ledger["source"].astype(str).str.strip().eq("live_feed")
    det_ok = ledger["detector_version"].astype(str).str.strip().eq("live_feed_v1")
    funnel["excluded_source_not_live_feed"] = int((~src_ok).sum())
    funnel["excluded_detector_not_live_feed_v1"] = int((src_ok & ~det_ok).sum())
    ledger = ledger[src_ok & det_ok].copy()
    ledger["root"] = ledger["root"].astype(str).str.strip().str.upper()
    spy = ledger["root"].eq("SPY")
    empty_root = ledger["root"].eq("") | ledger["root"].eq("NONE") | ledger["root"].eq("NAN")
    funnel["excluded_root_spy"] = int(spy.sum())
    funnel["excluded_root_missing"] = int((~spy & empty_root).sum())
    ledger = ledger[~spy & ~empty_root].copy()
    ledger["model_bucket"] = ledger["dte_bucket"].map(map_model_bucket)
    funnel["excluded_bucket_unmapped"] = int(ledger["model_bucket"].isna().sum())
    ledger = ledger[ledger["model_bucket"].notna()].copy()
    merged = ledger.merge(grades, on="event_id", how="left", indicator=True)
    merged["has_grade"] = merged["_merge"].eq("both")
    return merged.drop(columns="_merge"), funnel


def _session_or_none(value: Any):
    from lib.nyse_calendar import is_session

    if value is None or (isinstance(value, float) and math.isnan(value)) or value is pd.NA:
        return None
    text = str(value).strip()
    if not text or text.lower() in ("nan", "none", "nat"):
        return None
    try:
        ts = pd.Timestamp(text)
    except (TypeError, ValueError):
        return "invalid"
    if pd.isna(ts):
        return None
    d = ts.date()
    return d if is_session(d) else "not_session"


def _bucket_eligibility(rows: pd.DataFrame, horizon: int) -> tuple[pd.DataFrame, dict[str, Any]]:
    att: dict[str, Any] = {"cohort_rows": int(len(rows))}
    r = rows[rows["has_grade"]].copy()
    att["step1_missing_grade_row"] = int(len(rows) - len(r))
    ok = r["graded_ok"].fillna(False).astype(bool)
    not_ok = r[~ok]
    att["step2_not_graded_ok"] = int(len(not_ok))
    att["step2_reason_codes"] = {str(k): int(v) for k, v in
                                 not_ok["reason_code"].fillna("<null>").astype(str).value_counts().items()}
    r = r[ok].copy()
    r["event_s"] = r["session_date"].map(_session_or_none)
    r["fill_s"] = r["fill_date"].map(_session_or_none)
    end_col = f"outcome_end_session_{horizon}"
    r["end_s"] = r[end_col].map(_session_or_none)
    ev_bad = r["event_s"].map(lambda v: v is None or isinstance(v, str))
    att["excluded_event_session_invalid"] = int(ev_bad.sum())
    r = r[~ev_bad]
    fill_missing = r["fill_s"].map(lambda v: v is None)
    fill_bad = r["fill_s"].map(lambda v: isinstance(v, str))
    att["step3_fill_missing"] = int(fill_missing.sum())
    att["step3_fill_not_session_or_invalid"] = int(fill_bad.sum())
    r = r[~fill_missing & ~fill_bad]
    end_missing = r["end_s"].map(lambda v: v is None)
    end_bad = r["end_s"].map(lambda v: isinstance(v, str))
    att["step4_end_missing_pending"] = int(end_missing.sum())
    att["step4_end_not_session_or_invalid"] = int(end_bad.sum())
    r = r[~end_missing & ~end_bad]
    causal = (r["fill_s"] >= r["event_s"]) & (r["end_s"] >= r["fill_s"])
    att["step5_noncausal"] = int((~causal).sum())
    r = r[causal].copy()
    n_ends = r.groupby(["fill_s", "root"])["end_s"].transform("nunique")
    att["step6_unit_boundary_inconsistent"] = int((n_ends > 1).sum())
    r = r[n_ends == 1].copy()
    att["eligible_rows"] = int(len(r))
    return r, att


def _positions(rows: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray, list]:
    from lib.nyse_calendar import sessions_between

    lo = min(rows["event_s"].min(), rows["fill_s"].min(), rows["end_s"].min())
    hi = max(rows["event_s"].max(), rows["fill_s"].max(), rows["end_s"].max())
    sessions = sessions_between(lo, hi)
    pos = {d: i for i, d in enumerate(sessions)}
    fill = rows["fill_s"].map(pos).to_numpy(dtype=np.int64)
    end = rows["end_s"].map(pos).to_numpy(dtype=np.int64)
    event = rows["event_s"].map(pos).to_numpy(dtype=np.int64)
    return event, fill, end, sessions


def _lib_crosscheck(rows: pd.DataFrame, bucket: str, horizon: int, module_weight: np.ndarray) -> dict[str, Any]:
    from lib.flow_score import uniqueness_weights_nyse_intervals

    df = pd.DataFrame({
        "event_id": rows["event_id"].astype(str).values,
        "evaluation_spec_version": "fs5-v1",
        "source": rows["source"].astype(str).values,
        "detector_version": rows["detector_version"].astype(str).values,
        "model_bucket": bucket,
        "root": rows["root"].values,
        "session_date": [d.isoformat() for d in rows["event_s"]],
        "fill_date": [d.isoformat() for d in rows["fill_s"]],
        "outcome_end_session": [d.isoformat() for d in rows["end_s"]],
    })
    lib_w = uniqueness_weights_nyse_intervals(df)
    aligned = lib_w.reindex(df["event_id"]).to_numpy(dtype=float)
    if np.any(~np.isfinite(aligned)):
        return {"max_abs_diff": float("inf"), "n": int(len(df)), "f0_clear": False,
                "note": "lib returned missing ids"}
    diff = float(np.max(np.abs(aligned - module_weight)))
    return {"max_abs_diff": diff, "n": int(len(df)), "f0_clear": diff <= 1e-12,
            "sum_lib": math.fsum(aligned.tolist()), "sum_module": math.fsum(module_weight.tolist())}


def _rate_bootstrap(s: np.ndarray, block: int, label: tuple[str, ...]) -> np.ndarray:
    rng = csw.rng_from_label(*label)
    out = []
    remaining = E1_REPLICATES
    while remaining > 0:
        r = min(E1_CHUNK, remaining)
        counts = csw.circular_block_counts(s.size, block, r, rng)
        out.append(counts @ s / s.size)
        remaining -= r
    return np.concatenate(out)


def _q_from_rates(rates: np.ndarray, horizon: int) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        t_inc = np.maximum(csw.DRAFT_TOTAL_FLOOR / rates, csw.DRAFT_MIN_BLOCKS * horizon)
        t_alt = np.maximum(csw.BUCKET_FLOOR / rates, csw.DRAFT_MIN_BLOCKS * horizon)
        return np.where(rates > 0, t_inc / t_alt, np.nan)


def _years_inc(rates: np.ndarray, horizon: int) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        t_inc = np.where(rates > 0, np.maximum(csw.DRAFT_TOTAL_FLOOR / rates, csw.DRAFT_MIN_BLOCKS * horizon),
                         np.inf)
    return t_inc / csw.SESSIONS_PER_YEAR


def _era(year: int) -> str:
    if year <= 2019:
        return "2017-19" if year >= 2017 else "pre-2017"
    if year <= 2022:
        return "2020-22"
    return "2023+"


def _e1_bucket(rows: pd.DataFrame, bucket: str, horizon: int) -> dict[str, Any]:
    L = horizon + 1
    event, fill, end, sessions = _positions(rows)
    units = csw.native_units(fill, end, rows["root"].values, exact=True)
    cross = _lib_crosscheck(rows, bucket, horizon, units.event_weight)
    f0, f1 = int(fill.min()), int(fill.max())
    t_all = f1 - f0 + 1
    s_full = csw.anchor_accrual_series(units, f0, f1)
    a_t = csw.position_decomposition(units)
    total_u = math.fsum(units.unit_weight.tolist())
    rho = total_u / t_all
    cap = csw.native_rate_cap(L, t_all)
    support = csw.support_summary(units.event_weight, fill, horizon)
    g_full = csw.gate_ratio(rho, horizon)

    blocks_all = csw.block_count(t_all, horizon)
    alt_state = ("SUPPORT_UPPER_BOUND_MET" if total_u >= csw.BUCKET_FLOOR and blocks_all >= csw.DRAFT_MIN_BLOCKS
                 else "NOT_YET_ESTIMABLE")
    inc_state = ("SUPPORT_UPPER_BOUND_MET" if total_u >= csw.DRAFT_TOTAL_FLOOR and blocks_all >= csw.DRAFT_MIN_BLOCKS
                 else "NOT_YET_ESTIMABLE")

    eras: dict[str, dict[str, float]] = {}
    unit_years = np.array([sessions[p].year for p in units.unit_start.tolist()])
    for era in sorted({_era(int(y)) for y in unit_years.tolist()}):
        m = np.array([_era(int(y)) == era for y in unit_years.tolist()])
        eras[era] = {"units": int(m.sum()), "sum_unit_weight": math.fsum(units.unit_weight[m].tolist()),
                     "meets_cell_floor_20": bool(units.unit_weight[m].sum() >= csw.CELL_FLOOR)}

    # Chronological split (PREREG §10): weights recomputed inside each window.
    t_train = (2 * t_all) // 3
    t_test = t_all - t_train
    split_pos = f0 + t_train
    train_mask = fill < split_pos
    test_mask = ~train_mask
    split: dict[str, Any] = {"t_all": t_all, "t_train": t_train, "t_test": t_test,
                             "train_rows": int(train_mask.sum()), "test_rows": int(test_mask.sum()),
                             "train_first_session": sessions[f0].isoformat(),
                             "test_first_session": sessions[split_pos].isoformat() if split_pos < len(sessions) else None,
                             "last_fill_session": sessions[f1].isoformat()}
    if train_mask.sum() == 0 or test_mask.sum() == 0:
        split["computable"] = False
        k3 = {"computable": False, "reason": "empty_train_or_test_window"}
    else:
        u_tr = csw.native_units(fill[train_mask], end[train_mask], rows["root"].values[train_mask], exact=True)
        u_te = csw.native_units(fill[test_mask], end[test_mask], rows["root"].values[test_mask], exact=True)
        s_tr = csw.anchor_accrual_series(u_tr, f0, split_pos - 1)
        s_te = csw.anchor_accrual_series(u_te, split_pos, f1)
        rho_tr = float(s_tr.mean())
        realized = math.fsum(s_te.tolist())
        predicted = rho_tr * t_test
        ratio = realized / predicted if predicted > 0 else float("nan")
        g_tr = csw.gate_ratio(rho_tr, horizon)
        sens = {}
        for mult in (1, 2, 4):
            b = mult * L
            rates = _rate_bootstrap(s_tr, b, ("q06-e1", bucket, "train", str(b)))
            q = _q_from_rates(rates, horizon)
            yi = _years_inc(rates, horizon)
            sens[f"b={b}"] = {
                "block_len": b, "honest_n_blocks": t_train // b, "replicates": int(rates.size),
                "rho_p05": csw.order_statistic_quantile(rates, 0.05),
                "rho_p95": csw.order_statistic_quantile(rates, 0.95),
                "q_p05": csw.order_statistic_quantile(q[np.isfinite(q)], 0.05),
                "q_p95": csw.order_statistic_quantile(q[np.isfinite(q)], 0.95),
                "years_inc_p05": csw.order_statistic_quantile(yi, 0.05),
                "years_inc_p95": csw.order_statistic_quantile(yi, 0.95),
            }
        r_tr = _rate_bootstrap(s_tr, L, ("q06-e1", bucket, "proj", "train"))
        r_te = _rate_bootstrap(s_te, L, ("q06-e1", bucket, "proj", "test"))
        with np.errstate(divide="ignore", invalid="ignore"):
            pr = np.where(r_tr > 0, r_te / r_tr, np.nan)
        pr = pr[np.isfinite(pr)]
        p_lo = csw.order_statistic_quantile(pr, 0.05)
        p_hi = csw.order_statistic_quantile(pr, 0.95)
        split.update({
            "computable": True,
            "rho_train": rho_tr, "rho_test": float(s_te.mean()),
            "sum_u_train": math.fsum(s_tr.tolist()), "sum_u_test_realized": realized,
            "sum_u_test_predicted": predicted, "projection_ratio": ratio,
            "projection_ratio_interval_90": (p_lo, p_hi),
            "projection_valid_replicates": int(pr.size),
            "gate_train": g_tr, "bootstrap": sens,
        })
        q_lo = sens[f"b={L}"]["q_p05"]
        ratio_ok = bool(g_full["ratio"] >= 2 and g_tr["ratio"] >= 2 and q_lo >= 2)
        proj_ok = bool(np.isfinite(p_lo) and np.isfinite(p_hi) and p_lo <= 2.0 and p_hi >= 0.5)
        k3 = {"computable": True, "q_full": g_full["ratio"], "q_train": g_tr["ratio"], "q_train_p05_bL": q_lo,
              "ratio_holds": ratio_ok, "projection_interval_intersects_0p5_2": proj_ok}

    return {
        "bucket": bucket, "horizon": horizon, "interval_len": L,
        "eligible_rows": int(len(rows)), "units": int(units.unit_start.size),
        "first_fill_session": sessions[f0].isoformat(), "last_fill_session": sessions[f1].isoformat(),
        "t_all_sessions": t_all, "years_all": t_all / csw.SESSIONS_PER_YEAR,
        "sum_unit_weight": total_u, "rho_full": rho, "rho_cap": cap, "rho_over_cap": rho / cap,
        "decomposition_abs_error": abs(math.fsum(a_t.tolist()) - total_u),
        "s_t_mean": float(s_full.mean()), "s_t_zero_sessions": int(np.count_nonzero(s_full == 0)),
        "kish_n_event_weights": csw.kish_effective_n(units.event_weight),
        "support_summary": support,
        "gate_full": g_full,
        "g_inc_practically_infeasible_full": bool(g_full["t_inc"] > INFEASIBLE_SESSIONS),
        "g_alt_practically_infeasible_full": bool(g_full["t_alt"] > INFEASIBLE_SESSIONS),
        "estimability": {"G_alt": alt_state, "G_inc": inc_state,
                         "G_inc_bin_floor_check": "UNKNOWN_NO_SCORES (FS-4 predictions absent)",
                         "basis": "total retained support; an upper bound on any calibration_eval share"},
        "eras": eras,
        "lib_crosscheck": cross,
        "split": split,
        "k3": k3,
    }


def stage_e1() -> tuple[dict[str, Any], list[Path]]:
    merged, funnel = _load_cohort()
    buckets: dict[str, Any] = {}
    for bucket, horizon in BUCKETS.items():
        rows = merged[merged["model_bucket"] == bucket]
        if bucket == "90p":
            buckets[bucket] = {"bucket": bucket, "horizon": horizon, "cohort_rows": int(len(rows)),
                               "note": "zero rows expected (PREREG §3)" if len(rows) == 0 else "rows present"}
            if len(rows) == 0:
                continue
        elig, att = _bucket_eligibility(rows, horizon)
        if len(elig) == 0:
            buckets[bucket] = {"bucket": bucket, "horizon": horizon, "attrition": att,
                               "state": "NO_ELIGIBLE_ROWS"}
            continue
        res = _e1_bucket(elig, bucket, horizon)
        res["attrition"] = att
        buckets[bucket] = res
    with_rows = [b for b, v in buckets.items() if v.get("eligible_rows", 0) > 0]
    k3_all = [buckets[b]["k3"] for b in with_rows]
    if not with_rows or not all(k.get("computable") for k in k3_all):
        k3 = {"state": "INSUFFICIENT_DATA", "reason": "E1 not computable for every bucket with rows"}
    elif not all(k["ratio_holds"] for k in k3_all):
        k3 = {"state": "REJECT", "reason": "Q ratio below 2 in a bucket"}
    elif not all(k["projection_interval_intersects_0p5_2"] for k in k3_all):
        k3 = {"state": "INSUFFICIENT_DATA", "reason": "projection unreliable (H-E1-proj failed)"}
    else:
        k3 = {"state": "HOLDS"}
    f0 = all(buckets[b]["lib_crosscheck"]["f0_clear"] for b in with_rows) if with_rows else None
    out = {"stage": "e1", "funnel": funnel, "buckets": buckets, "buckets_with_rows": with_rows,
           "k3": k3, "f0_crosscheck_clear": f0,
           "outcome_columns_read": False, "grades_columns_read": GRADES_GEOMETRY_COLUMNS,
           "ledger_columns_read": LEDGER_COLUMNS}
    path = HERE / "e1.json"
    write_json(path, out)
    return out, [path]


# ── stage: s1 ────────────────────────────────────────────────────────────────

def _s1_cell(horizon: int, n_sessions: int, truth: str, regime: str) -> dict[str, Any]:
    # PREREG §8: seed label "q06-s1\0{bucket}\0{T}\0{truth}\0{regime}" with bucket strings.
    rng = csw.rng_from_label("q06-s1", S1_BUCKET_LABEL[horizon], str(n_sessions), truth, regime)
    tally = {rule: {"PASS": 0, "FAIL": 0, "NO_VERDICT": 0, "supported": 0,
                    "pass_supported": 0, "fail_supported": 0}
             for rule in ("R_inc", "R_alt", "R_pool")}
    proposed = {"PASS": 0, "FAIL": 0, "NO_VERDICT": 0}
    gaps, sum_w, kish, implied, binned, report_ok, empty = [], [], [], [], [], 0, 0
    for _ in range(S1_REPLICATES):
        sim = csw.simulate_panel(rng, n_sessions, horizon, truth, regime)
        if sim["anchor"].size == 0:
            empty += 1
            for rule in tally:
                tally[rule]["NO_VERDICT"] += 1
            proposed["NO_VERDICT"] += 1
            continue
        res = csw.evaluate_rules(sim["p"], sim["y"], sim["w"], sim["anchor"], horizon, S1_BOOTSTRAP, rng)
        for rule in tally:
            d = res[rule]["decision"]
            tally[rule][d] += 1
            if support_holds(res[rule]):
                tally[rule]["supported"] += 1
                tally[rule]["pass_supported"] += int(d == "PASS")
                tally[rule]["fail_supported"] += int(d == "FAIL")
        proposed[res["proposed"]] += 1
        gaps.append(csw.true_calibration_gap(sim["p"], sim["w"], truth))
        sum_w.append(float(np.sum(sim["w"])))
        kish.append(csw.kish_effective_n(sim["w"]))
        er = res["error_report"]
        if er.get("binned_ece") is not None and np.isfinite(er["binned_ece"]):
            report_ok += 1
            binned.append(er["binned_ece"])
        if er.get("implied_ece") is not None and np.isfinite(er["implied_ece"]):
            implied.append(er["implied_ece"])
    n = S1_REPLICATES
    rules_out = {}
    for rule, t in tally.items():
        sup = t["supported"]
        wrong = t["fail_supported"] if truth == "T0" else t["pass_supported"]
        rules_out[rule] = {
            **{k: t[k] for k in ("PASS", "FAIL", "NO_VERDICT")},
            "support_fraction": sup / n,
            "error_kind": "false_kill" if truth == "T0" else "false_reassurance",
            "error_rate_given_support": (wrong / sup) if sup else float("nan"),
            "error_rate_given_support_wilson95": wilson(wrong, sup),
            "error_rate_unconditional": wrong / n,
            "error_rate_unconditional_wilson95": wilson(wrong, n),
            "pass_rate": t["PASS"] / n, "fail_rate": t["FAIL"] / n,
        }
    return {
        "horizon": horizon, "n_sessions": n_sessions, "truth": truth, "regime": regime,
        "replicates": n, "bootstrap_replicates": S1_BOOTSTRAP, "empty_panels": empty,
        "rules": rules_out, "proposed": proposed,
        "error_report_produced": report_ok,
        "mean_true_gap": float(np.mean(gaps)) if gaps else float("nan"),
        "mean_sum_w": float(np.mean(sum_w)) if sum_w else float("nan"),
        "mean_kish_n": float(np.mean(kish)) if kish else float("nan"),
        "mean_binned_ece": float(np.mean(binned)) if binned else float("nan"),
        "mean_implied_ece": float(np.mean(implied)) if implied else float("nan"),
    }


def _first_supported(cells: list[dict[str, Any]], rule: str) -> float:
    for c in sorted(cells, key=lambda c: c["n_sessions"]):
        if c["rules"][rule]["support_fraction"] >= 0.5:
            return float(c["n_sessions"])
    return float("inf")


def stage_s1() -> tuple[dict[str, Any], list[Path]]:
    cells = []
    for horizon, grid in S1_GRID.items():
        for n_sessions in grid:
            for truth in csw.TRUTHS:
                for regime in csw.REGIMES:
                    cells.append(_s1_cell(horizon, n_sessions, truth, regime))
    k1_cells = []
    for c in cells:
        alt = c["rules"]["R_alt"]
        if alt["support_fraction"] >= 0.5:
            rate = alt["error_rate_given_support"]
            k1_cells.append({"horizon": c["horizon"], "n_sessions": c["n_sessions"], "truth": c["truth"],
                             "regime": c["regime"], "kind": alt["error_kind"], "rate": rate,
                             "holds": bool(rate <= FR_FK_BAR)})
    k1 = bool(k1_cells) and all(x["holds"] for x in k1_cells)
    k2_rows = []
    for horizon in S1_GRID:
        for truth in csw.TRUTHS:
            for regime in csw.REGIMES:
                sub = [c for c in cells if c["horizon"] == horizon and c["truth"] == truth and c["regime"] == regime]
                t_inc = _first_supported(sub, "R_inc")
                t_alt = _first_supported(sub, "R_alt")
                # Fixed before running: if R_alt never reaches support either, R_alt shows no
                # feasibility advantage on that pair, so K2 does not hold there.
                holds = (not math.isinf(t_alt)) and (math.isinf(t_inc) or t_inc >= 2 * t_alt)
                k2_rows.append({"horizon": horizon, "truth": truth, "regime": regime,
                                "first_supported_R_inc": t_inc, "first_supported_R_alt": t_alt,
                                "first_supported_R_pool": _first_supported(sub, "R_pool"),
                                "holds": bool(holds)})
    k2 = all(r["holds"] for r in k2_rows)
    out = {"stage": "s1", "cells": cells, "k1": {"holds": k1, "cells": k1_cells, "bar": FR_FK_BAR},
           "k2": {"holds": k2, "rows": k2_rows}}
    paths = []
    path = HERE / "s1.json"
    write_json(path, out)
    paths.append(path)
    e1_path = HERE / "e1.json"
    if e1_path.exists():
        e1 = json.loads(e1_path.read_text(encoding="utf-8"))
        verdict = combine_verdict(e1, out)
        vpath = HERE / "verdict.json"
        write_json(vpath, verdict)
        paths.append(vpath)
    return out, paths


def combine_verdict(e1: dict[str, Any], s1: dict[str, Any]) -> dict[str, Any]:
    f0 = e1.get("f0_crosscheck_clear")
    k3 = e1.get("k3", {}).get("state")
    k1 = s1["k1"]["holds"]
    k2 = s1["k2"]["holds"]
    if f0 is False:
        verdict, why = "REJECT", "F0: module weights differ from lib beyond 1e-12"
    elif not k1:
        verdict, why = "REJECT", "K1 failed"
    elif not k2:
        verdict, why = "REJECT", "K2 failed"
    elif k3 == "REJECT":
        verdict, why = "REJECT", "K3 ratio failed"
    elif k3 == "INSUFFICIENT_DATA" or f0 is None:
        verdict, why = "INSUFFICIENT_DATA", e1.get("k3", {}).get("reason", "E1 not computable")
    else:
        verdict, why = "KEEP", "F0 clear; K1, K2, K3 hold"
    return {"verdict": verdict, "reason": why, "f0_crosscheck_clear": f0, "k1": k1, "k2": k2, "k3": k3,
            "outcome_calibration": "INSUFFICIENT_DATA",
            "note": "F0 also requires the focused pytest to pass; that evidence is recorded separately"}


# ── stage: attrition (PREREG_AMENDMENT.md 1; descriptive, no verdict effect) ─

def _date_range(values: pd.Series) -> dict[str, Any]:
    s = pd.to_datetime(values.astype("string"), errors="coerce").dropna()
    if s.empty:
        return {"min": None, "max": None, "n_non_null": 0}
    return {"min": str(s.min().date()), "max": str(s.max().date()), "n_non_null": int(len(s))}


def _month_counts(values: pd.Series) -> dict[str, int]:
    s = pd.to_datetime(values.astype("string"), errors="coerce").dropna()
    return {str(k): int(v) for k, v in s.dt.strftime("%Y-%m").value_counts().sort_index().items()}


def stage_attrition() -> tuple[dict[str, Any], list[Path]]:
    merged, funnel = _load_cohort()
    out_b: dict[str, Any] = {}
    for bucket, horizon in BUCKETS.items():
        rows = merged[merged["model_bucket"] == bucket]
        graded = rows[rows["has_grade"]]
        ok = graded["graded_ok"].fillna(False).astype(bool)
        end_col = f"outcome_end_session_{horizon}"
        end_present = graded[end_col].map(lambda v: _session_or_none(v) is not None)
        classes = {
            "missing_grade_row": rows[~rows["has_grade"]],
            "graded_ok_end_present": graded[ok & end_present],
            "graded_ok_end_missing": graded[ok & ~end_present],
        }
        for code, sub in graded[~ok].groupby(graded[~ok]["reason_code"].fillna("<null>").astype(str)):
            classes[f"not_graded_ok:{code}"] = sub
        out_b[bucket] = {
            "horizon": horizon, "end_column": end_col, "cohort_rows": int(len(rows)),
            "classes": {name: {"rows": int(len(sub)),
                               "session_date": _date_range(sub["session_date"]),
                               "fill_date": _date_range(sub["fill_date"]) if "fill_date" in sub else None,
                               "session_month_counts": _month_counts(sub["session_date"])}
                        for name, sub in classes.items()},
        }
    out = {"stage": "attrition", "amendment": "PREREG_AMENDMENT.md #1", "verdict_effect": "none",
           "funnel": funnel, "buckets": out_b, "outcome_columns_read": False,
           "grades_columns_read": GRADES_GEOMETRY_COLUMNS, "ledger_columns_read": LEDGER_COLUMNS}
    path = HERE / "attrition.json"
    write_json(path, out)
    return out, [path]


# ── driver ───────────────────────────────────────────────────────────────────

STAGES = {"baseline": stage_baseline, "e1": stage_e1, "s1": stage_s1, "attrition": stage_attrition}


def append_run(record: dict[str, Any]) -> None:
    with open(RUNS, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(clean(record), sort_keys=True) + "\n")


def _code_pin_mismatches() -> list[str]:
    """Return the code paths whose bytes differ from CODE_PIN.json (missing pin = refuse)."""
    if not CODE_PIN.exists():
        return ["CODE_PIN.json:missing"]
    try:
        pins = json.loads(CODE_PIN.read_text(encoding="utf-8"))["sha256"]
    except Exception as exc:  # noqa: BLE001
        return [f"CODE_PIN.json:unreadable:{type(exc).__name__}"]
    bad = []
    for path in CODE_INPUTS:
        rel = str(path.resolve().relative_to(Q06_ROOT))
        if pins.get(rel) != sha256_file(path):
            bad.append(rel)
    return bad


def main(argv: list[str]) -> int:
    stage = argv[1] if len(argv) > 1 else ""
    record: dict[str, Any] = {
        "command": " ".join([sys.executable] + argv),
        "stage": stage,
        "thread_env": {k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                                                      "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")},
        "served_model": "claude-opus-5-5",
    }
    t0 = time.perf_counter()
    prereg_sha = sha256_file(PREREG)
    record["prereg_sha256"] = prereg_sha
    try:
        want = frozen_hash()
    except Exception as exc:  # noqa: BLE001
        record.update({"exit_code": 2, "refused": f"freeze_log_unreadable:{exc}"})
        append_run(record)
        print("REFUSED: FREEZE.log unreadable", file=sys.stderr)
        return 2
    if prereg_sha != want:
        record.update({"exit_code": 2, "refused": "prereg_hash_mismatch", "freeze_sha256": want})
        append_run(record)
        print("REFUSED: sha256(PREREG.md) differs from FREEZE.log", file=sys.stderr)
        return 2
    code_mismatch = _code_pin_mismatches()
    if code_mismatch:
        record.update({"exit_code": 2, "refused": "code_hash_mismatch", "mismatched": code_mismatch})
        append_run(record)
        print("REFUSED: code bytes differ from CODE_PIN.json: " + ", ".join(code_mismatch), file=sys.stderr)
        return 2
    if stage not in STAGES:
        record.update({"exit_code": 2, "refused": "unknown_stage"})
        append_run(record)
        print(f"usage: evaluate.py {{{'|'.join(STAGES)}}}", file=sys.stderr)
        return 2
    inputs = {}
    mismatches = []
    for path, pinned in PINNED_INPUTS.items():
        got = sha256_file(path)
        inputs[path] = got
        if got != pinned:
            mismatches.append(path)
    for path in CODE_INPUTS:
        inputs[str(path)] = sha256_file(path)
    for extra in (AMENDMENT, AMENDMENT_2, CODE_PIN):
        if extra.exists():
            inputs[str(extra)] = sha256_file(extra)
    if stage == "s1" and (HERE / "e1.json").exists():
        inputs[str(HERE / "e1.json")] = sha256_file(HERE / "e1.json")
    record["inputs"] = inputs
    if mismatches:
        record.update({"exit_code": 3, "refused": "input_hash_mismatch", "mismatched": mismatches})
        append_run(record)
        print("ABORT: input hash mismatch: " + ", ".join(mismatches), file=sys.stderr)
        return 3
    try:
        result, outputs = STAGES[stage]()
    except Exception as exc:  # noqa: BLE001
        record.update({"exit_code": 1, "error": f"{type(exc).__name__}: {exc}",
                       "traceback_tail": traceback.format_exc().splitlines()[-6:],
                       "elapsed_s": round(time.perf_counter() - t0, 2)})
        append_run(record)
        traceback.print_exc()
        return 1
    record.update({"exit_code": 0, "outputs": {str(p): sha256_file(p) for p in outputs},
                   "elapsed_s": round(time.perf_counter() - t0, 2)})
    append_run(record)
    print(json.dumps(clean({"stage": stage, "outputs": record["outputs"], "elapsed_s": record["elapsed_s"]})))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
