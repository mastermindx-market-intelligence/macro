"""M0 coherent-target retrospective requalification runner (E0 §2.H1).

Re-scores the 13 inherited MRI release-forecast evaluations frozen in the E0
research protocol against ONE coherent first-print target per release, with
the protocol's exact statistic (Diebold-Mariano on the loss differential
against the window-strongest naive baseline, Newey-West lrvar, Holm family of
exactly 13), moving-block bootstrap CIs, ratio rules, verdict order,
S1/S2 verdict-free sensitivities and the H4 descriptive contrasts plus
interval calibration.  Every number in the receipt keeps its target id, model
id, vintage basis, window and episode count.

The runner never re-fits, re-tunes or re-specifies a model: every prediction
series comes from a frozen owner walk-forward call.  It writes exactly one
JSON and one Markdown receipt under ``out_dir`` and nothing else.

Evidence class: synthetic under test (fixtures + monkeypatched owners); the
one real run is the seat's, in a full checkout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

# --------------------------------------------------------------------------- #
# frozen identity (E0 §2.H1 / §3 freeze fields)
# --------------------------------------------------------------------------- #
PROTOCOL_PATH = "research/rates_inflation_command/seat_20261014/E0_RESEARCH_PROTOCOL.md"
PROTOCOL_SHA256 = "87b51dcad66c6f84989675e9cce91eb5b46b3888d60b2e599a8736d87e2309df"

TRIAL_FAMILY = "ric_mri_coherent_requal_v1"
TRIAL_N = 13
# SF1: owner_actual/target median scale ratio outside this band blocks.
UNITS_RATIO_BAND = (0.5, 2.0)
ALPHA = 0.05
BOOT_BLOCK = 6
BOOT_DRAWS = 10000
BOOT_SEED = 20261014
MIN_N_TESTED = 30
WINDOWS = (("current", "2024-01"), ("tested", "2021-01"), ("full", "2010-01"))
SCHEMA = "ric_m0_requal.v1"

BASELINE_ORDER = ("naive", "trailing_3m", "ar_model")
CPI_FAMILIES = ("cpi_headline", "cpi_core")

# release family -> family champion eval (source of every baseline row)
FAMILY_CHAMPION = {
    "cpi_headline": "cpi_headline.v2",
    "cpi_core": "cpi_core.v2",
    "nfp": "nfp.v1",
    "pce_headline": "pce_headline.champion",
    "pce_core": "pce_core.champion",
    "ppi_final_demand": "ppi_final_demand.champion",
}

# series behind the parquet-reconstructed coherent first-print target
TARGET_SERIES = {
    "nfp": "PAYEMS",
    "pce_headline": "PCEPI",
    "pce_core": "PCEPILFE",
    "ppi_final_demand": "PPIFIS",
}


class _Eval:
    __slots__ = ("eval_id", "family", "model_id")

    def __init__(self, eval_id: str, family: str, model_id: str) -> None:
        self.eval_id = eval_id
        self.family = family
        self.model_id = model_id

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"Eval({self.eval_id})"


EVALUATIONS: tuple[_Eval, ...] = tuple(
    [
        _Eval("cpi_headline.v2", "cpi_headline", "v2"),
        _Eval("cpi_headline.v3_factor", "cpi_headline", "v3_factor"),
        _Eval("cpi_headline.cpi_bridge", "cpi_headline", "cpi_bridge"),
        _Eval("cpi_headline.mf_energy_t1", "cpi_headline", "mf_energy_t1"),
        _Eval("cpi_headline.coherent_ridge_v1", "cpi_headline", "coherent_ridge_v1"),
        _Eval("cpi_core.v2", "cpi_core", "v2"),
        _Eval("cpi_core.v3_factor", "cpi_core", "v3_factor"),
        _Eval("cpi_core.coherent_ridge_v1", "cpi_core", "coherent_ridge_v1"),
        _Eval("nfp.v1", "nfp", "v1"),
        _Eval("nfp.v3_factor", "nfp", "v3_factor"),
        _Eval("pce_headline.champion", "pce_headline", "champion"),
        _Eval("pce_core.champion", "pce_core", "champion"),
        _Eval("ppi_final_demand.champion", "ppi_final_demand", "champion"),
    ]
)
EVAL_BY_ID = {e.eval_id: e for e in EVALUATIONS}

# --------------------------------------------------------------------------- #
# PIT legs (E0 §2.H1 Origin: per-spec legs transcribed from the frozen PREREGs)
# --------------------------------------------------------------------------- #
def _legs(*rows: tuple[str, str, str]) -> tuple[dict, ...]:
    return tuple({"leg": l, "pit_class": c, "citation": cit} for l, c, cit in rows)


PIT_LEGS: dict[str, tuple[dict, ...]] = {
    # champion v2 (PREREG_V2.md): ZORI +45d assumed lag; CUSR0000SAH1 shelter
    # leg declared revision_optimistic; remaining legs ALFRED initial prints
    # or the unrevised GASREGW weekly (PREREG_V1.md:50-51).
    "cpi_headline.v2": _legs(
        ("cpi_own_lags", "pit_vintage", "research/release_forecast/PREREG_V1.md:22"),
        ("sticky_mom_lag1", "pit_vintage", "research/release_forecast/PREREG_V2.md:147"),
        ("median_mom_lag1", "pit_vintage", "research/release_forecast/PREREG_V2.md:148"),
        ("flex_mom_lag1", "pit_vintage", "research/release_forecast/PREREG_V2.md:149"),
        ("ppi_mom_lag1", "pit_vintage", "research/release_forecast/PREREG_V2.md:150"),
        ("gasoline_mom", "pit_vintage", "research/release_forecast/PREREG_V1.md:50"),
        ("shelter_cpi_cusr0000sah1", "revision_optimistic", "research/release_forecast/PREREG_V2.md:57"),
        ("zori_shelter", "approximate_pit_lag", "research/release_forecast/PREREG_V2.md:41"),
        ("zori_values", "revision_optimistic", "research/release_forecast/PREREG_V2.md:44"),
    ),
    "cpi_core.v2": _legs(
        ("cpi_own_lags", "pit_vintage", "research/release_forecast/PREREG_V1.md:22"),
        ("sticky_mom_lag1", "pit_vintage", "research/release_forecast/PREREG_V2.md:165"),
        ("median_mom_lag1", "pit_vintage", "research/release_forecast/PREREG_V2.md:166"),
        ("flex_mom_lag1", "pit_vintage", "research/release_forecast/PREREG_V2.md:167"),
        ("ppi_mom_lag1", "pit_vintage", "research/release_forecast/PREREG_V2.md:150"),
        ("shelter_cpi_cusr0000sah1", "revision_optimistic", "research/release_forecast/PREREG_V2.md:57"),
        ("zori_shelter", "approximate_pit_lag", "research/release_forecast/PREREG_V2.md:92"),
        ("zori_values", "revision_optimistic", "research/release_forecast/PREREG_V2.md:44"),
    ),
    "cpi_headline.v3_factor": _legs(
        ("cpi_own_lags", "pit_vintage", "research/release_forecast/PREREG_V3_FACTOR.md:45"),
        ("sticky_mom_lag1", "pit_vintage", "research/release_forecast/PREREG_V3_FACTOR.md:47"),
        ("ppi_fis_mom_lag1", "revision_optimistic", "research/release_forecast/PREREG_V3_FACTOR.md:64"),
        ("ppi_fes_mom_lag1", "revision_optimistic", "research/release_forecast/PREREG_V3_FACTOR.md:63"),
        ("dollar_mom_dtwexbgs", "revision_optimistic", "research/release_forecast/PREREG_V3_FACTOR.md:61"),
        ("shelter_nowcast", "revision_optimistic", "research/release_forecast/PREREG_V2.md:57"),
        ("zori_shelter", "approximate_pit_lag", "research/release_forecast/PREREG_V2.md:41"),
        ("zori_values", "revision_optimistic", "research/release_forecast/PREREG_V2.md:44"),
        ("gasoline_mom", "pit_vintage", "research/release_forecast/PREREG_V3_FACTOR.md:50"),
    ),
    "cpi_core.v3_factor": _legs(
        ("cpi_own_lags", "pit_vintage", "research/release_forecast/PREREG_V3_FACTOR.md:54"),
        ("sticky_mom_lag1", "pit_vintage", "research/release_forecast/PREREG_V3_FACTOR.md:56"),
        ("ppi_fis_mom_lag1", "revision_optimistic", "research/release_forecast/PREREG_V3_FACTOR.md:64"),
        ("ppi_fes_mom_lag1", "revision_optimistic", "research/release_forecast/PREREG_V3_FACTOR.md:63"),
        ("dollar_mom_dtwexbgs", "revision_optimistic", "research/release_forecast/PREREG_V3_FACTOR.md:61"),
        ("shelter_nowcast", "revision_optimistic", "research/release_forecast/PREREG_V2.md:57"),
    ),
    "cpi_headline.cpi_bridge": _legs(
        ("bridge_weights_frozen", "revision_optimistic", "research/release_forecast/PREREG_CPI_BRIDGE_V1.md:70"),
        ("gasoline_gasregw", "pit_vintage", "research/release_forecast/PREREG_CPI_BRIDGE_V1.md:89"),
        ("electricity_apu000072610", "revision_optimistic", "research/release_forecast/PREREG_CPI_BRIDGE_V1.md:294"),
        ("food_cusr0000saf11", "revision_optimistic", "research/release_forecast/PREREG_CPI_BRIDGE_V1.md:143"),
        ("wpu01", "revision_optimistic", "research/release_forecast/PREREG_CPI_BRIDGE_V1.md:143"),
        ("shelter_cusr0000sah1", "revision_optimistic", "research/release_forecast/PREREG_CPI_BRIDGE_V1.md:121"),
        ("zori_shelter", "approximate_pit_lag", "research/release_forecast/PREREG_CPI_BRIDGE_V1.md:119"),
        ("zori_values", "revision_optimistic", "research/release_forecast/PREREG_CPI_BRIDGE_V1.md:296"),
        ("core_services_cusr0000sasle", "revision_optimistic", "research/release_forecast/PREREG_CPI_BRIDGE_V1.md:190"),
        ("ppifis_vintages", "pit_vintage", "research/release_forecast/PREREG_CPI_BRIDGE_V1.md:161"),
    ),
    "cpi_headline.mf_energy_t1": _legs(
        ("gasoline_gasregw", "pit_vintage", "research/release_forecast/PREREG_MF_ENERGY_V1.md:44"),
        ("wti_dcoilwtico", "pit_vintage", "research/release_forecast/PREREG_MF_ENERGY_V1.md:58"),
        ("cpiaucsl_vintages", "pit_vintage", "research/release_forecast/PREREG_MF_ENERGY_V1.md:69"),
        ("cpi_ri_weights", "revision_optimistic", "research/release_forecast/PREREG_MF_ENERGY_V1.md:78"),
    ),
    "cpi_headline.coherent_ridge_v1": _legs(
        ("cpi_target_vintages", "pit_vintage", "research/release_forecast/PREREG_COHERENT_RIDGE_V1.md:75"),
        ("vintage_feature_rows", "pit_vintage", "research/release_forecast/PREREG_COHERENT_RIDGE_V1.md:77"),
        ("gasoline_gasregw", "pit_vintage", "research/release_forecast/PREREG_COHERENT_RIDGE_V1.md:85"),
    ),
    "cpi_core.coherent_ridge_v1": _legs(
        ("cpi_target_vintages", "pit_vintage", "research/release_forecast/PREREG_COHERENT_RIDGE_V1.md:75"),
        ("vintage_feature_rows", "pit_vintage", "research/release_forecast/PREREG_COHERENT_RIDGE_V1.md:77"),
    ),
    "nfp.v1": _legs(
        ("payems_own_lags", "pit_vintage", "research/release_forecast/PREREG_V1.md:22"),
        ("claims_survey_week", "pit_vintage", "research/release_forecast/PREREG_V1.md:136"),
        ("withheld_taxes", "pit_vintage", "research/release_forecast/PREREG_V1.md:55"),
        ("awhman", "revision_optimistic", "research/release_forecast/PREREG_V1.md:42"),
    ),
    "nfp.v3_factor": _legs(
        ("payems_own_lags", "pit_vintage", "research/release_forecast/PREREG_V3_FACTOR.md:62"),
        ("claims_survey_week", "pit_vintage", "research/release_forecast/PREREG_V1.md:136"),
        ("withheld_taxes", "pit_vintage", "research/release_forecast/PREREG_V1.md:55"),
        ("awhman", "revision_optimistic", "research/release_forecast/PREREG_V3_FACTOR.md:65"),
        ("adp_change", "revision_optimistic", "research/release_forecast/PREREG_V3_FACTOR.md:66"),
        ("dollar_mom_dtwexbgs", "revision_optimistic", "research/release_forecast/PREREG_V3_FACTOR.md:61"),
    ),
    "pce_headline.champion": _legs(
        ("pce_own_lags", "pit_vintage", "research/release_forecast/PREREG_NEW_TARGETS_V1.md:50"),
        ("sticky_mom_lag1", "pit_vintage", "research/release_forecast/PREREG_NEW_TARGETS_V1.md:225"),
        ("median_mom_lag1", "pit_vintage", "research/release_forecast/PREREG_NEW_TARGETS_V1.md:225"),
        ("flex_mom_lag1", "pit_vintage", "research/release_forecast/PREREG_NEW_TARGETS_V1.md:225"),
        ("ppifis_mom_lag1", "pit_vintage", "research/release_forecast/PREREG_NEW_TARGETS_V1.md:71"),
        ("gasoline_mom", "pit_vintage", "research/release_forecast/PREREG_NEW_TARGETS_V1.md:119"),
    ),
    "pce_core.champion": _legs(
        ("pce_own_lags", "pit_vintage", "research/release_forecast/PREREG_NEW_TARGETS_V1.md:59"),
        ("sticky_mom_lag1", "pit_vintage", "research/release_forecast/PREREG_NEW_TARGETS_V1.md:225"),
        ("ppifes_mom_lag1", "pit_vintage", "research/release_forecast/PREREG_NEW_TARGETS_V1.md:110"),
    ),
    "ppi_final_demand.champion": _legs(
        ("ppi_own_lags", "pit_vintage", "research/release_forecast/PREREG_NEW_TARGETS_V1.md:68"),
        ("ppifes_mom_lag1", "pit_vintage", "research/release_forecast/PREREG_NEW_TARGETS_V1.md:110"),
        ("gasoline_mom", "pit_vintage", "research/release_forecast/PREREG_NEW_TARGETS_V1.md:119"),
    ),
}

# --------------------------------------------------------------------------- #
# small normalisation helpers
# --------------------------------------------------------------------------- #
def period_text(value: Any) -> str | None:
    """Normalise a period (str/Timestamp/date) to ``YYYY-MM``."""

    if value is None:
        return None
    text = str(value)
    if len(text) >= 7:
        text = text[:7]
    if len(text) == 7 and text[4] == "-":
        return text
    return text


def day_text(value: Any) -> str | None:
    """Normalise a release date (str/Timestamp/date) to ``YYYY-MM-DD``."""

    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value)
    return text[:10] if len(text) >= 10 else text


def _median(values: Sequence[float]) -> float | None:
    return statistics.median(values) if values else None


def _mean(values: Sequence[float]) -> float | None:
    return (sum(values) / len(values)) if values else None


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _round(value: float | None, digits: int = 8) -> float | None:
    return None if value is None else round(float(value), digits)


# --------------------------------------------------------------------------- #
# statistic (E0 §2.H1 Statistic) — owner helpers only
# --------------------------------------------------------------------------- #
def dm_pvalues(d: Sequence[float]) -> dict | None:
    """One-sided DM statistic for the alternative mean(d) < 0.

    ``DM = sqrt(n) * mean(d) / sqrt(newey_west_lrvar(d, lag=newey_west_lag(n)))``
    with ``p_normal = Phi(DM)`` and ``p_t = T_{n-1}.cdf(DM)``.  Returns None
    when n < 2 or the long-run variance is not computable.
    """

    import numpy as np
    from engine.challenger_spa_comparison import newey_west_lag, newey_west_lrvar

    values = [float(v) for v in d]
    n = len(values)
    if n < 2:
        return None
    arr = np.asarray(values, dtype=float)
    try:
        lag = newey_west_lag(n)
        lrvar = newey_west_lrvar(arr, lag)
    except Exception:
        return None
    if not math.isfinite(lrvar) or lrvar <= 0:
        return None
    dm = math.sqrt(n) * float(arr.mean()) / math.sqrt(lrvar)
    from scipy.stats import norm, t as t_dist

    return {
        "dm": dm,
        "p_normal": float(norm.cdf(dm)),
        "p_t": float(t_dist.cdf(dm, df=n - 1)),
    }


def holm_adjusted(pvals: Mapping[str, float | None]) -> dict:
    """Owner Holm step-down; None entries pass through as None."""

    from engine.desk_placebo import holm_adjust

    return holm_adjust(dict(pvals))


def holm_clear_and_borderline(adj_normal: float | None, adj_t: float | None) -> tuple[bool, bool]:
    """(holm_clear, borderline): clear iff both adjusted p < ALPHA."""

    if adj_normal is None or adj_t is None:
        return False, False
    normal_clears = adj_normal < ALPHA
    t_clears = adj_t < ALPHA
    return (normal_clears and t_clears), (normal_clears != t_clears)


def bootstrap_ci(series) -> tuple[float, float] | None:
    """Owner moving-block bootstrap CI at the frozen M0 parameters."""

    import pandas as pd
    from engine.grading_stats import block_bootstrap_scalar_ci

    pd_series = series if isinstance(series, pd.Series) else pd.Series(list(series))
    ci = block_bootstrap_scalar_ci(
        pd_series, block=BOOT_BLOCK, draws=BOOT_DRAWS, seed=BOOT_SEED
    )
    return ci


def choose_strongest_baseline(maes: Mapping[str, float | None]) -> tuple[str | None, list[str]]:
    """Lowest-MAE baseline; ties break naive, trailing_3m, ar_model.

    Returns (strongest, not_available) where not_available lists baselines
    the owner does not emit (absent from ``maes``).
    """

    unavailable = [name for name in BASELINE_ORDER if name not in maes]
    candidates = [
        (name, maes[name]) for name in BASELINE_ORDER if maes.get(name) is not None
    ]
    if not candidates:
        return None, unavailable
    best = min(candidates, key=lambda item: item[1])[0]
    return best, unavailable


# --------------------------------------------------------------------------- #
# verdict (E0 §2.H1 Verdicts — checked in this order; first match wins)
# --------------------------------------------------------------------------- #
def decide_verdict(
    *,
    n_tested: int,
    mean_d_naive_full: float | None,
    mean_d_naive_tested: float | None,
    holm_clear: bool,
    r_tested: float | None,
    r_full: float | None,
    r_current: float | None,
    has_revision_optimistic_leg: bool,
    current_window_empty: bool = False,
) -> tuple[str, list[str]]:
    if n_tested < MIN_N_TESTED:
        return "INSUFFICIENT", []
    if (
        mean_d_naive_full is not None
        and mean_d_naive_tested is not None
        and mean_d_naive_full >= 0
        and mean_d_naive_tested >= 0
    ):
        return "FALSIFIED_UNDER_COHERENT_TARGET", []
    reasons: list[str] = []
    if has_revision_optimistic_leg:
        reasons.append("non_pit_inputs")
    if not holm_clear:
        reasons.append("holm_not_cleared")
    if r_tested is None or r_tested > 0.95:
        reasons.append("r_tested_above_0_95")
    if r_full is None or r_full >= 1.00:
        reasons.append("r_full_not_below_1")
    if current_window_empty:
        reasons.append("current_window_empty")
    elif r_current is None or r_current > 1.00:
        reasons.append("r_current_above_1")
    if not reasons:
        return "QUALIFIED_RETROSPECTIVE", []
    return "NOT_DEMONSTRATED", reasons


# --------------------------------------------------------------------------- #
# coherent target loaders
# --------------------------------------------------------------------------- #
CPI_TRUTH_REL = Path("data/release_forecast/cpi_truth/alfred_same_release_vintage_proxy_v1.json")
PARITY_REL = Path("data/release_forecast/cpi_truth/parity_report.json")
DEFECT_FILES = (
    Path("data/release_forecast/defect_notices.json"),
    Path("data/release_forecast/official_actual_defects.json"),
)


def load_cpi_truth_index(path: Path) -> dict[tuple[str, str], dict]:
    """Minimal reader for the coherent CPI truth history JSON.

    Row shape (owner ``_validate_history_targets``): release, period,
    release_date, published_proxy_1dp, target_epoch, same_release_vintage.
    """

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = payload.get("targets") if isinstance(payload, dict) else payload
    index: dict[tuple[str, str], dict] = {}
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        release = row.get("release")
        period = period_text(row.get("period"))
        value = row.get("published_proxy_1dp")
        if release not in CPI_FAMILIES or period is None or value is None:
            continue
        index[(release, period)] = {
            "value": float(value),
            "release_date": day_text(row.get("release_date")),
        }
    return index


def default_target_loader(root: Path, inputs: list) -> Callable[[str, str], dict | None]:
    """Coherent first-print target per family (E0 §2.H1 Target).

    CPI headline/core read the coherent truth proxy JSON; NFP / PCE / PPI are
    reconstructed from full ALFRED vintage parquets through the owner
    (``release_date=None`` -> same-release first vintage).
    """

    cpi_cache: dict | None = None
    vintage_cache: dict[str, Any] = {}

    def _cpi_index() -> dict:
        nonlocal cpi_cache
        if cpi_cache is None:
            path = Path(root) / CPI_TRUTH_REL
            if path.exists():
                cpi_cache = load_cpi_truth_index(path)
                inputs.append({"path": CPI_TRUTH_REL.as_posix(), "sha256": _hash_file(path)})
            else:
                cpi_cache = {}
        return cpi_cache

    def _vintages(series_id: str):
        if series_id not in vintage_cache:
            from engine import release_target_truth as rtt

            path = rtt.default_vintage_path(root, series_id)
            if not path.exists():
                vintage_cache[series_id] = None
            else:
                inputs.append({"path": path.relative_to(root).as_posix(), "sha256": _hash_file(path)})
                vintage_cache[series_id] = rtt.load_full_vintage_parquets(path)
        return vintage_cache[series_id]

    def loader(release: str, period: str) -> dict | None:
        if release in CPI_FAMILIES:
            row = _cpi_index().get((release, period_text(period)))
            if row is None:
                return None
            return {
                "status": "ok",
                "value": row["value"],
                "release_date": row["release_date"],
                "source": "alfred_same_release_vintage_proxy_v1",
            }
        series_id = TARGET_SERIES.get(release)
        if series_id is None:
            return None
        vintages = _vintages(series_id)
        if vintages is None:
            return None
        from engine import release_target_truth as rtt

        receipt = rtt.reconstruct_release_target(
            vintages, series_id=series_id, period=period, release_date=None
        )
        if not isinstance(receipt, dict) or receipt.get("status") != "ok":
            return receipt if isinstance(receipt, dict) else None
        if release == "nfp":
            value = receipt.get("payroll_change_thousands")
        else:
            value = receipt.get("published_proxy_1dp")
        if value is None:
            return {"status": "unavailable", "reason": "no_target_value"}
        return {
            "status": "ok",
            "value": float(value),
            "release_date": receipt.get("release_date"),
            "release_selection": receipt.get("release_selection"),
            "source": f"alfred_vintage_parquet:{series_id}",
        }

    return loader


# --------------------------------------------------------------------------- #
# adapters (one owner call each; rows normalised, never re-fit)
# --------------------------------------------------------------------------- #
def _normalise_rows(
    raw_rows: Iterable[Mapping],
    *,
    eval_id: str,
    family: str,
    predicted_key: str = "predicted",
    actual_key: str = "actual",
) -> list[dict]:
    rows = []
    for raw in raw_rows:
        period = period_text(raw.get("period"))
        if period is None:
            continue
        predicted = raw.get(predicted_key)
        rows.append(
            {
                "eval_id": eval_id,
                "family": family,
                "period": period,
                "release_date": day_text(raw.get("release_date")),
                "predicted": None if predicted is None else float(predicted),
                "owner_actual": None if raw.get(actual_key) is None else float(raw.get(actual_key)),
            }
        )
    return rows


def _normalise_baselines(raw_rows: Iterable[Mapping]) -> list[dict]:
    out = []
    for raw in raw_rows:
        period = period_text(raw.get("period"))
        if period is None:
            continue
        out.append(
            {
                "period": period,
                "release_date": day_text(raw.get("release_date")),
                "naive": raw.get("baseline_naive"),
                "trailing_3m": raw.get("baseline_trailing3m"),
                "ar_model": raw.get("baseline_ar3"),
            }
        )
    return out


def default_adapters(root: Path, decision_asof: str) -> dict[str, Callable]:
    """Frozen owner adapter set, one owner call per evaluation."""

    root = Path(root)
    adapters: dict[str, Callable] = {}

    def _full_release(release: str, eval_id: str, family: str):
        def adapter(champion_rows=None):
            from engine.release_forecast import run_walk_forward_full

            payload = run_walk_forward_full(release, root)
            rows = _normalise_rows(payload.get("results", []), eval_id=eval_id, family=family)
            baselines = _normalise_baselines(payload.get("results", []))
            return rows, baselines

        return adapter

    def _v3_cpi(release: str, eval_id: str, family: str):
        def adapter(champion_rows=None):
            from engine.release_forecast_v3 import run_walk_forward_v3_cpi

            payload = run_walk_forward_v3_cpi(release, root)
            return (
                _normalise_rows(payload.get("results", []), eval_id=eval_id, family=family),
                _normalise_baselines(payload.get("results", [])),
            )

        return adapter

    def _v3_nfp(eval_id: str, family: str):
        def adapter(champion_rows=None):
            from engine.release_forecast_v3 import run_walk_forward_v3_nfp

            payload = run_walk_forward_v3_nfp(root)
            return (
                _normalise_rows(payload.get("results", []), eval_id=eval_id, family=family),
                _normalise_baselines(payload.get("results", [])),
            )

        return adapter

    def _bridge(release: str, eval_id: str, family: str):
        def adapter(champion_rows=None):
            from engine.release_cpi_bridge import run_bridge_walk_forward

            payload = run_bridge_walk_forward(release, root)
            rows_all = _normalise_rows(payload.get("results", []), eval_id=eval_id, family=family)
            champion_by_period = {
                row["period"]: row.get("release_date") for row in (champion_rows or [])
            }
            rows, excluded = [], []
            for row in rows_all:
                champion_date = champion_by_period.get(row["period"])
                if champion_date is None:
                    excluded.append({"period": row["period"], "reason": "no_release_date"})
                    continue
                row = dict(row, release_date=champion_date)
                rows.append(row)
            return rows, [], excluded

        return adapter

    def _mf_energy(eval_id: str, family: str):
        def adapter(champion_rows=None):
            from engine.release_mf_energy import run_walk_forward_mf

            # T-1 configuration only (PREREG_MF_ENERGY_V1.md:320-331); any
            # other cutoff would be an uncounted trial.
            payload = run_walk_forward_mf(root, cutoff="T-1")
            return (
                _normalise_rows(payload.get("results", []), eval_id=eval_id, family=family),
                _normalise_baselines(payload.get("results", [])),
            )

        return adapter

    def _coherent_ridge(release: str, eval_id: str, family: str):
        def adapter(champion_rows=None):
            from engine import release_cpi_coherent_shadow as shadow

            asof_date = datetime.strptime(decision_asof, "%Y-%m-%d").date()
            model, model_receipt = shadow._load_model_receipt(root.resolve(), asof_date)
            target_index, history, _truth = shadow._load_truth_receipt(root.resolve(), asof_date)
            eligible = [
                shadow._month(period_text)
                for (row_release, period_text), row in target_index.items()
                if row_release == release and row["_release_date"] <= asof_date
            ]
            if not eligible:
                raise ValueError(f"no eligible coherent labels for {release} at {decision_asof}")
            live_period = shadow._shift_month(max(eligible), 1)
            live_cutoff = asof_date
            vintages, gasoline, _receipts = shadow._load_feature_sources(
                root.resolve(), require_gasoline=(release == "cpi_headline")
            )
            records, _excluded = shadow._complete_historical_records(
                release=release,
                live_period=live_period,
                live_cutoff=live_cutoff,
                target_index=target_index,
                history_hash=str(history["history_hash"]),
                vintages=vintages,
                gasoline=gasoline,
            )
            oos = shadow._walk_forward_residuals(records, shadow.FEATURE_ORDER[release])
            rows = _normalise_rows(
                oos, eval_id=eval_id, family=family,
                predicted_key="point_raw", actual_key="actual_raw_target",
            )
            identity = hashlib.sha256(
                json.dumps(model_receipt, sort_keys=True, default=str).encode("utf-8")
            ).hexdigest()
            for row in rows:
                row["coherent_model_receipt_sha256"] = identity
            # E0:87-91 — every owner-excluded row is listed by (period, reason).
            return rows, [], list(_excluded)

        return adapter

    def _track_n(builder_name: str, eval_id: str, family: str):
        def adapter(champion_rows=None):
            import engine.release_targets_v11 as targets

            payload = getattr(targets, builder_name)(root)
            return (
                _normalise_rows(payload.get("results", []), eval_id=eval_id, family=family),
                _normalise_baselines(payload.get("results", [])),
            )

        return adapter

    adapters["cpi_headline.v2"] = _full_release("cpi_headline", "cpi_headline.v2", "cpi_headline")
    adapters["cpi_core.v2"] = _full_release("cpi_core", "cpi_core.v2", "cpi_core")
    adapters["nfp.v1"] = _full_release("nfp", "nfp.v1", "nfp")
    adapters["cpi_headline.v3_factor"] = _v3_cpi("cpi_headline", "cpi_headline.v3_factor", "cpi_headline")
    adapters["cpi_core.v3_factor"] = _v3_cpi("cpi_core", "cpi_core.v3_factor", "cpi_core")
    adapters["nfp.v3_factor"] = _v3_nfp("nfp.v3_factor", "nfp")
    adapters["cpi_headline.cpi_bridge"] = _bridge("cpi_headline", "cpi_headline.cpi_bridge", "cpi_headline")
    adapters["cpi_headline.mf_energy_t1"] = _mf_energy("cpi_headline.mf_energy_t1", "cpi_headline")
    adapters["cpi_headline.coherent_ridge_v1"] = _coherent_ridge("cpi_headline", "cpi_headline.coherent_ridge_v1", "cpi_headline")
    adapters["cpi_core.coherent_ridge_v1"] = _coherent_ridge("cpi_core", "cpi_core.coherent_ridge_v1", "cpi_core")
    adapters["pce_headline.champion"] = _track_n("build_wf_pce_headline", "pce_headline.champion", "pce_headline")
    adapters["pce_core.champion"] = _track_n("build_wf_pce_core", "pce_core.champion", "pce_core")
    adapters["ppi_final_demand.champion"] = _track_n("build_wf_ppi_finaldemand", "ppi_final_demand.champion", "ppi_final_demand")
    return adapters


# --------------------------------------------------------------------------- #
# episode construction and window statistics
# --------------------------------------------------------------------------- #
def _build_episodes(
    eval_rec: _Eval,
    model_rows: Sequence[Mapping],
    baseline_rows: Sequence[Mapping],
    target_loader: Callable[[str, str], dict | None],
) -> dict:
    baseline_by_period = {row["period"]: row for row in baseline_rows}
    episodes: list[dict] = []
    excluded: list[dict] = []
    missing_source: list[dict] = []
    mismatches: list[dict] = []
    naive_seen = False

    for row in model_rows:
        period = period_text(row.get("period"))
        predicted = row.get("predicted")
        if period is None:
            continue
        if predicted is None:
            excluded.append({"period": period, "reason": "model_prediction_absent"})
            continue
        receipt = target_loader(eval_rec.family, period)
        if not isinstance(receipt, dict) or receipt.get("status") != "ok":
            missing_source.append(
                {
                    "release": eval_rec.family,
                    "period": period,
                    "reason": "missing_source",
                }
            )
            continue
        value = receipt.get("value")
        target_day = day_text(receipt.get("release_date"))
        if value is None:
            missing_source.append(
                {"release": eval_rec.family, "period": period, "reason": "missing_source"}
            )
            continue
        baseline = baseline_by_period.get(period)
        naive = baseline.get("naive") if baseline else None
        if naive is None:
            excluded.append({"period": period, "reason": "naive_absent"})
            continue
        naive_seen = True
        owner_day = day_text(row.get("release_date"))
        if owner_day is not None and target_day is not None and owner_day != target_day:
            mismatches.append({"period": period, "owner": owner_day, "target": target_day})
        episodes.append(
            {
                "period": period,
                "release_date": target_day,
                "predicted": float(predicted),
                "owner_actual": row.get("owner_actual"),
                "target": float(value),
                "naive": float(naive),
                "trailing_3m": baseline.get("trailing_3m") if baseline else None,
                "ar_model": baseline.get("ar_model") if baseline else None,
            }
        )

    episodes.sort(key=lambda e: (e["release_date"] or "", e["period"]))
    return {
        "episodes": episodes,
        "excluded": excluded,
        "missing_source": missing_source,
        "mismatches": mismatches,
        "naive_seen": naive_seen,
        "n_model_rows": len(model_rows),
    }


def _window_episodes(episodes: Sequence[Mapping], window: str) -> list[Mapping]:
    start = dict(WINDOWS)[window]
    return [e for e in episodes if e["period"] >= start]


def _baseline_maes(episodes: Sequence[Mapping]) -> dict[str, float]:
    maes: dict[str, float] = {}
    for key in BASELINE_ORDER:
        errors = [
            abs(float(e["target"]) - float(e[key]))
            for e in episodes
            if e.get(key) is not None
        ]
        if errors:
            maes[key] = sum(errors) / len(errors)
    return maes


def _comparison_stats(
    episodes: Sequence[Mapping], base_key: str
) -> dict:
    pairs = [
        (float(e["target"]), float(e["predicted"]), float(e[base_key]))
        for e in episodes
        if e.get(base_key) is not None
    ]
    if not pairs:
        return {"mean_d": None, "ci95": None, "R": None, "n": 0}
    d = [
        abs(target - predicted) - abs(target - base)
        for target, predicted, base in pairs
    ]
    mae_model = sum(abs(target - predicted) for target, predicted, _ in pairs) / len(pairs)
    mae_base = sum(abs(target - base) for target, _, base in pairs) / len(pairs)
    ci = bootstrap_ci(d) if len(d) >= MIN_N_TESTED else None
    ratio = (mae_model / mae_base) if mae_base > 0 else None
    return {
        "mean_d": _round(_mean(d)),
        "ci95": None if ci is None else [_round(ci[0]), _round(ci[1])],
        "R": _round(ratio),
        "n": len(d),
    }


def _window_stats(episodes: Sequence[Mapping], window: str) -> dict:
    window_eps = _window_episodes(episodes, window)
    maes = _baseline_maes(window_eps)
    strongest, unavailable = choose_strongest_baseline(maes)
    stats = {
        "n_scored": len(window_eps),
        "n_rows": len(window_eps),
        "honest_n": len({e["release_date"] for e in window_eps}),
        "mae_model": _round(
            _mean([abs(float(e["target"]) - float(e["predicted"])) for e in window_eps])
        ),
        "baselines": {
            "naive_mae": _round(maes.get("naive")),
            "trailing_3m_mae": _round(maes.get("trailing_3m")),
            "ar_model_mae": _round(maes.get("ar_model")),
            "strongest": strongest,
            "not_available": unavailable,
        },
        "vs_naive": _comparison_stats(window_eps, "naive"),
    }
    # when the strongest baseline IS naive the two comparisons coincide
    if strongest in (None, "naive"):
        stats["vs_strongest"] = dict(stats["vs_naive"])
    else:
        stats["vs_strongest"] = _comparison_stats(window_eps, strongest)
    return stats


def _sensitivity_flag(primary: Mapping | None, sensitivity: Mapping | None) -> bool:
    if not primary or not sensitivity:
        return False
    if primary.get("mean_d") is None or sensitivity.get("mean_d") is None:
        return False
    sign_flip = (primary["mean_d"] < 0) != (sensitivity["mean_d"] < 0)
    if primary.get("R") is not None and sensitivity.get("R") is not None:
        ratio_shift = abs(sensitivity["R"] - primary["R"]) >= 0.05
    else:
        ratio_shift = False
    return bool(sign_flip or ratio_shift)


# --------------------------------------------------------------------------- #
# S1 / S2 (verdict-free re-scorings of the same 13 prediction series)
# --------------------------------------------------------------------------- #
def _parity_non_match_periods(root: Path, inputs: list) -> tuple[set[str], str | None]:
    path = Path(root) / PARITY_REL
    if not path.exists():
        return set(), None
    sha = _hash_file(path)
    inputs.append({"path": PARITY_REL.as_posix(), "sha256": sha})
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return set(), sha
    non_match: set[str] = set()
    for case in payload.get("cases", []) if isinstance(payload, dict) else []:
        if not isinstance(case, dict):
            continue
        comparisons = case.get("comparisons") or []
        is_match = case.get("status") == "passed" and any(
            isinstance(comp, dict) and comp.get("status") == "match"
            for comp in comparisons
        )
        if not is_match:
            period = period_text(case.get("period"))
            if period is not None:
                non_match.add(period)
    return non_match, sha


def _errata_for_family(root: Path, family: str, inputs: list) -> tuple[dict[str, float], list[dict]]:
    corrected: dict[str, float] = {}
    files: list[dict] = []
    for rel in DEFECT_FILES:
        path = Path(root) / rel
        if not path.exists():
            continue
        files.append({"path": rel.as_posix(), "sha256": _hash_file(path)})
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        entries: list = []
        if isinstance(payload, dict):
            entries = payload.get("notices") or payload.get("defects") or []
        elif isinstance(payload, list):
            entries = payload
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if entry.get("release") != family:
                continue
            period = period_text(entry.get("period") or entry.get("target_period"))
            value = None
            for key, candidate in entry.items():
                if "correct" in key.lower() and isinstance(candidate, (int, float)) and not isinstance(candidate, bool):
                    value = float(candidate)
                    break
            if period is not None and value is not None:
                corrected[period] = value
    return corrected, files


def _rescore_windows(episodes: Sequence[Mapping], *, drop_periods: set[str] = frozenset(),
                     target_overrides: Mapping[str, float] | None = None) -> dict:
    overrides = dict(target_overrides or {})
    adjusted = []
    for e in episodes:
        if e["period"] in drop_periods:
            continue
        row = dict(e)
        if e["period"] in overrides:
            row["target"] = overrides[e["period"]]
        adjusted.append(row)
    return {window: _window_stats(adjusted, window) for window, _ in WINDOWS}


# --------------------------------------------------------------------------- #
# H4 (descriptive only; trial-free; never in Holm)
# --------------------------------------------------------------------------- #
H4_CONTRASTS = (
    ("cpi_headline.cpi_bridge", "cpi_headline.v2"),
    ("cpi_headline.v3_factor", "cpi_headline.v2"),
    ("cpi_core.v3_factor", "cpi_core.v2"),
    ("nfp.v3_factor", "nfp.v1"),
)


def _interval_rows(episodes: Sequence[Mapping]) -> dict:
    """[p10, p90] bands from strictly-prior own residuals (owner quantiles)."""

    import numpy as np
    from engine import release_forecast as rf
    from engine.grading_stats import wilson_ci

    ordered = sorted(episodes, key=lambda e: (e["release_date"] or "", e["period"]))
    n_scored_intervals = 0
    covered = 0
    widths: list[float] = []
    naive_widths: list[float] = []
    naive_band_seen = False

    for position, episode in enumerate(ordered):
        prior = ordered[:position]
        prior = [p for p in prior if (p["release_date"] or "") < (episode["release_date"] or "")]
        residuals = [
            float(p["owner_actual"]) - float(p["predicted"])
            for p in prior
            if p.get("owner_actual") is not None
        ]
        if len(residuals) < 24:
            continue
        band = rf._compute_quantiles(np.asarray(residuals, dtype=float), float(episode["predicted"]))
        if band.get("p10") is None or band.get("p90") is None:
            continue
        n_scored_intervals += 1
        widths.append(float(band["p90"]) - float(band["p10"]))
        if float(band["p10"]) <= float(episode["target"]) <= float(band["p90"]):
            covered += 1
        naive_residuals = [
            float(p["owner_actual"]) - float(p["naive"])
            for p in prior
            if p.get("owner_actual") is not None and p.get("naive") is not None
        ]
        if episode.get("naive") is not None and len(naive_residuals) >= 24:
            naive_band = rf._compute_quantiles(
                np.asarray(naive_residuals, dtype=float), float(episode["naive"])
            )
            if naive_band.get("p10") is not None and naive_band.get("p90") is not None:
                naive_band_seen = True
                naive_widths.append(float(naive_band["p90"]) - float(naive_band["p10"]))

    wilson = wilson_ci(covered, n_scored_intervals)
    sharpness = _median(widths)
    naive_sharpness = _median(naive_widths) if naive_widths else None
    sharpness_status = "ok" if naive_sharpness is not None else "NOT_COMPARABLE"
    calibrated = False
    if wilson is not None and sharpness is not None and naive_sharpness is not None:
        calibrated = bool(wilson[0] <= 0.80 <= wilson[1] and sharpness <= naive_sharpness)
    return {
        "n_interval_scored": n_scored_intervals,
        "covered_k": covered,
        "wilson_lo": None if wilson is None else _round(wilson[0], 6),
        "wilson_hi": None if wilson is None else _round(wilson[1], 6),
        "sharpness_median": _round(sharpness),
        "naive_sharpness_median": _round(naive_sharpness),
        "sharpness_status": sharpness_status,
        "calibrated": calibrated,
    }


def _contrast_stats(
    complex_episodes: Sequence[Mapping], simple_episodes: Sequence[Mapping]
) -> dict:
    simple_by_period = {e["period"]: e for e in simple_episodes}
    shared = [
        (c, simple_by_period[c["period"]])
        for c in complex_episodes
        if c["period"] in simple_by_period
    ]
    windows: dict[str, dict] = {}
    for window, _ in WINDOWS:
        start = dict(WINDOWS)[window]
        pairs = [(c, s) for c, s in shared if c["period"] >= start]
        d = [
            abs(float(c["target"]) - float(c["predicted"]))
            - abs(float(s["target"]) - float(s["predicted"]))
            for c, s in pairs
        ]
        ci = bootstrap_ci(d) if len(d) >= MIN_N_TESTED else None
        mae_c = _mean([abs(float(c["target"]) - float(c["predicted"])) for c, _ in pairs])
        mae_s = _mean([abs(float(s["target"]) - float(s["predicted"])) for _, s in pairs])
        ratio = (mae_c / mae_s) if (mae_c is not None and mae_s and mae_s > 0) else None
        windows[window] = {
            "n": len(d),
            "mean_d": _round(_mean(d)),
            "ci95": None if ci is None else [_round(ci[0]), _round(ci[1])],
            "R": _round(ratio),
        }
    return windows


# --------------------------------------------------------------------------- #
# runner
# --------------------------------------------------------------------------- #
def run(
    root: Path,
    out_dir: Path,
    decision_asof: str,
    *,
    declare_budget: bool = False,
    adapters: Mapping[str, Callable] | None = None,
    target_loader: Callable[[str, str], dict | None] | None = None,
) -> dict:
    root = Path(root)
    out_dir = Path(out_dir)
    inputs: list[dict] = []
    gaps: list[str] = []

    protocol_file = root / PROTOCOL_PATH
    protocol_sha = _hash_file(protocol_file) if protocol_file.exists() else None
    if protocol_sha != PROTOCOL_SHA256:
        receipt = {
            "schema": SCHEMA,
            "status": "blocked",
            "reason": "protocol_sha_mismatch",
            "protocol": {"path": PROTOCOL_PATH, "sha256": protocol_sha},
            "decision_asof": decision_asof,
            "trial": {
                "family": TRIAL_FAMILY,
                "n": TRIAL_N,
                "declared": False,
                "sensitivity_rescorings": [],
            },
            "inputs": [
                {"path": PROTOCOL_PATH, "sha256": protocol_sha}
            ],
            "holm": {"family_size": TRIAL_N, "alpha": ALPHA, "raw": {}, "adjusted": {}, "adjusted_t": {}},
            "evaluations": [],
            "h4": {"contrasts": [], "intervals": [], "family_coverage": {}},
            "gaps": [f"protocol sha256 mismatch: expected {PROTOCOL_SHA256}, found {protocol_sha}"],
        }
        _write_receipt(out_dir, decision_asof, receipt)
        return receipt
    inputs.append({"path": PROTOCOL_PATH, "sha256": protocol_sha})

    if declare_budget:
        from engine import trial_ledger as tl

        tl.TrialLedger().log_declared_budget(
            TRIAL_N,
            family=TRIAL_FAMILY,
            reason=f"{PROTOCOL_PATH}:{PROTOCOL_SHA256}",
        )

    if adapters is None:
        adapters = default_adapters(root, decision_asof)
    if target_loader is None:
        target_loader = default_target_loader(root, inputs)

    def _call_adapter(eval_id: str, champion_rows=None):
        adapter = (adapters or {}).get(eval_id)
        if adapter is None:
            raise KeyError(f"no adapter for {eval_id}")
        result = adapter(champion_rows)
        if isinstance(result, dict):
            return (
                result.get("rows", []),
                result.get("baselines", []),
                result.get("excluded", []),
            )
        rows, baselines = result[0], result[1]
        excluded = result[2] if len(result) > 2 else []
        return rows, baselines, excluded

    # pass 1: family champions (they own every baseline row in the family)
    champion_rows_cache: dict[str, list] = {}
    family_baselines: dict[str, list] = {}
    for family, champion_id in FAMILY_CHAMPION.items():
        try:
            rows, baselines, _ = _call_adapter(champion_id)
            champion_rows_cache[champion_id] = rows
            family_baselines[family] = baselines
        except Exception as exc:  # noqa: BLE001 - recorded per evaluation
            champion_rows_cache[champion_id] = []
            family_baselines[family] = []

    # pass 2: every evaluation in protocol order
    eval_receipts: list[dict] = []
    episode_cache: dict[str, list[dict]] = {}
    for eval_rec in EVALUATIONS:
        try:
            rows, baselines, extra_excluded = _call_adapter(
                eval_rec.eval_id, champion_rows_cache.get(FAMILY_CHAMPION[eval_rec.family])
            )
        except Exception as exc:  # noqa: BLE001 - blocked evaluation, others run
            episode_cache[eval_rec.eval_id] = []
            eval_receipts.append(
                _blocked_evaluation(
                    eval_rec,
                    reasons=[f"adapter_error:{type(exc).__name__}"],
                    message=str(exc),
                )
            )
            continue

        built = _build_episodes(eval_rec, rows, family_baselines.get(eval_rec.family, []), target_loader)
        episodes = built["episodes"]
        episode_cache[eval_rec.eval_id] = episodes
        excluded = list(extra_excluded) + built["excluded"]

        status = "ok"
        reasons: list[str] = []
        naive_absent_exclusions = [
            e for e in built["excluded"] if e["reason"] == "naive_absent"
        ]
        if not episodes and naive_absent_exclusions:
            status = "blocked"
            reasons.append("naive_prior_absent")

        units_check = "ok"
        units_ratio: float | None = None
        pairs = [
            (float(e["owner_actual"]), float(e["target"]))
            for e in episodes
            if e.get("owner_actual") is not None
        ]
        if status == "ok":
            if not pairs:
                units_check = "not_checkable"
                gaps.append(
                    f"{eval_rec.eval_id}: units guard not_checkable (no owner_actual values)"
                )
            else:
                # Scale-ratio guard: owner_actual is a mixed-vintage change, so a
                # difference test false-blocks on revision noise (PCE). Only a
                # scale mismatch (x100, x1000, level vs change) blocks.
                med_actual = _median([abs(a) for a, _ in pairs])
                med_target = _median([abs(b) for _, b in pairs])
                if not med_target:
                    units_check = "not_checkable"
                    gaps.append(
                        f"{eval_rec.eval_id}: units guard not_checkable (zero median target)"
                    )
                else:
                    units_ratio = med_actual / med_target
                    if not (UNITS_RATIO_BAND[0] <= units_ratio <= UNITS_RATIO_BAND[1]):
                        status = "blocked"
                        reasons.append("units_mismatch")
                        units_check = "mismatch"

        windows = {window: _window_stats(episodes, window) for window, _ in WINDOWS}
        # n_rows is the COVERAGE row count per window: every model row whose
        # period falls in the window, scored or not (MISSING_SOURCE counts).
        row_periods = [period_text(r.get("period")) for r in rows if r.get("period") is not None]
        for window, start in WINDOWS:
            windows[window]["n_rows"] = sum(1 for p in row_periods if p >= start)
        eval_receipts.append(
            {
                "eval_id": eval_rec.eval_id,
                "family": eval_rec.family,
                "model_id": eval_rec.model_id,
                "target": {
                    "id": f"{eval_rec.family}.same_release_first_print",
                    "source": _target_source(eval_rec.family),
                    "basis": "same_release_first_print",
                },
                "status": status,
                "verdict": None,
                "reasons": reasons,
                "labels": [],
                "units_check": units_check,
                "units_ratio": _round(units_ratio),
                "pit_legs": [dict(leg) for leg in PIT_LEGS.get(eval_rec.eval_id, ())],
                "n_rows": {w: windows[w]["n_rows"] for w in windows},
                "honest_n": {w: windows[w]["honest_n"] for w in windows},
                "excluded": excluded,
                "missing_source": built["missing_source"],
                "release_date_mismatches": built["mismatches"],
                "baselines": {w: windows[w]["baselines"] for w in windows},
                "primary": {},
                "windows": {
                    w: {
                        "n_scored": windows[w]["n_scored"],
                        "vs_naive": windows[w]["vs_naive"],
                        "vs_strongest": windows[w]["vs_strongest"],
                    }
                    for w in windows
                },
                "sensitivities": {"S1": {}, "S2": {}},
                "sensitivity_flags": [],
                "_episodes": episodes,
            }
        )

    # Holm over EXACTLY the 13 primary p-values (blocked/uncomputable -> 1.0)
    p_normal_map: dict[str, float] = {}
    p_t_map: dict[str, float | None] = {}
    dm_map: dict[str, dict | None] = {}
    for receipt in eval_receipts:
        eval_id = receipt["eval_id"]
        dm: dict | None = None
        if receipt["status"] == "ok":
            dm = dm_pvalues(
                _d_series(episode_cache[eval_id], "tested", receipt["baselines"]["tested"]["strongest"])
            )
        dm_map[eval_id] = dm
        p_normal_map[eval_id] = 1.0 if dm is None else dm["p_normal"]
        p_t_map[eval_id] = None if dm is None else dm["p_t"]

    adjusted = holm_adjusted(p_normal_map)
    adjusted_t: dict[str, float | None] = {}
    for eval_id in p_normal_map:
        replaced = dict(p_normal_map)
        replaced[eval_id] = 1.0 if p_t_map[eval_id] is None else p_t_map[eval_id]
        adjusted_t[eval_id] = holm_adjusted(replaced).get(eval_id)

    deviations: list[dict] = []
    for receipt in eval_receipts:
        eval_id = receipt["eval_id"]
        episodes = episode_cache[eval_id]
        tested = receipt["windows"]["tested"]
        dm = dm_map[eval_id]
        adj_n = adjusted.get(eval_id)
        adj_t = adjusted_t.get(eval_id)
        holm_clear, borderline = holm_clear_and_borderline(adj_n, adj_t)
        receipt["primary"] = {
            "dm": None if dm is None else dm["dm"],
            "p_normal": None if dm is None else dm["p_normal"],
            "p_t": None if dm is None else dm["p_t"],
            "holm_adj": _round(adj_n),
            "holm_adj_t": _round(adj_t),
            "holm_clear": holm_clear,
            "borderline": borderline,
            "mean_d": tested["vs_strongest"]["mean_d"],
            "ci95": tested["vs_strongest"]["ci95"],
            "R": tested["vs_strongest"]["R"],
        }
        if receipt["status"] != "ok":
            # E0 vocabulary is exhaustive; §7: a deviation demotes to
            # NOT_DEMONSTRATED with the deviation recorded.
            receipt["verdict"] = "NOT_DEMONSTRATED"
            receipt["reasons"] = list(receipt["reasons"]) + ["deviation_blocked_evaluation"]
            deviations.append({"eval_id": eval_id, "reasons": list(receipt["reasons"])})
            continue
        has_ro = any(leg["pit_class"] == "revision_optimistic" for leg in receipt["pit_legs"])
        if any(leg["pit_class"] == "approximate_pit_lag" for leg in receipt["pit_legs"]):
            receipt["labels"].append("approximate_pit_lag")
        verdict, verdict_reasons = decide_verdict(
            n_tested=tested["n_scored"],
            mean_d_naive_full=receipt["windows"]["full"]["vs_naive"]["mean_d"],
            mean_d_naive_tested=tested["vs_naive"]["mean_d"],
            holm_clear=holm_clear,
            r_tested=tested["vs_strongest"]["R"],
            r_full=receipt["windows"]["full"]["vs_strongest"]["R"],
            r_current=receipt["windows"]["current"]["vs_strongest"]["R"],
            has_revision_optimistic_leg=has_ro,
            current_window_empty=receipt["windows"]["current"]["n_scored"] == 0,
        )
        receipt["verdict"] = verdict
        receipt["reasons"] = list(receipt["reasons"]) + verdict_reasons

    # S1 / S2 sensitivities (verdict-free; never in Holm)
    non_match_periods, parity_sha = _parity_non_match_periods(root, inputs)
    errata_by_family = {
        family: _errata_for_family(root, family, inputs) for family in FAMILY_CHAMPION
    }
    for receipt in eval_receipts:
        eval_id = receipt["eval_id"]
        episodes = episode_cache[eval_id]
        primary_tested = receipt["windows"]["tested"]["vs_strongest"]
        if receipt["family"] in CPI_FAMILIES:
            if parity_sha is None:
                s1 = {
                    "status": "not_available",
                    "reason": "parity_report.json absent",
                    "n_dropped": 0,
                    "dropped_periods": [],
                    "parity_sha256": None,
                    "windows": {w: dict(receipt["windows"][w]) for w in receipt["windows"]},
                }
                gaps.append(f"{eval_id}: S1 not_available (no parity report under root)")
            elif not non_match_periods:
                # nothing to drop: the re-scoring equals the primary windows
                windows = {w: dict(receipt["windows"][w]) for w in receipt["windows"]}
                s1 = {
                    "status": "applied",
                    "n_dropped": 0,
                    "dropped_periods": [],
                    "parity_sha256": parity_sha,
                    "windows": windows,
                }
            else:
                windows = _rescore_windows(episodes, drop_periods=non_match_periods)
                s1 = {
                    "status": "applied",
                    "n_dropped": len([e for e in episodes if e["period"] in non_match_periods]),
                    "dropped_periods": sorted(non_match_periods & {e["period"] for e in episodes}),
                    "parity_sha256": parity_sha,
                    "windows": windows,
                }
                if _sensitivity_flag(primary_tested, windows["tested"]["vs_strongest"]):
                    receipt["sensitivity_flags"].append("verdict sensitive to S1")
        else:
            s1 = {"status": "not_applicable"}
        receipt["sensitivities"]["S1"] = s1

        corrected, files = errata_by_family[receipt["family"]]
        affected = sorted(set(corrected) & {e["period"] for e in episodes})
        if affected:
            windows = _rescore_windows(episodes, target_overrides=corrected)
            s2 = {
                "status": "applied",
                "n_affected": len(affected),
                "affected_periods": affected,
                "files": files,
                "windows": windows,
            }
            if _sensitivity_flag(primary_tested, windows["tested"]["vs_strongest"]):
                receipt["sensitivity_flags"].append("verdict sensitive to S2")
        else:
            s2 = {
                "status": "NO_APPLICABLE_ERRATA",
                "n_affected": 0,
                "affected_periods": [],
                "files": files,
            }
        receipt["sensitivities"]["S2"] = s2

    # H4: descriptive contrasts + interval calibration
    h4_contrasts: list[dict] = []
    for complex_id, simple_id in H4_CONTRASTS:
        if complex_id not in episode_cache or simple_id not in episode_cache:
            continue
        windows = _contrast_stats(episode_cache[complex_id], episode_cache[simple_id])
        labels = []
        tested_r = windows["tested"]["R"]
        if tested_r is not None and tested_r >= 1.00:
            labels.append("COMPLEXITY_NOT_EARNED")
        h4_contrasts.append(
            {
                "contrast": f"{complex_id}_vs_{simple_id}",
                "complex_eval": complex_id,
                "simple_eval": simple_id,
                "labels": labels,
                "windows": windows,
            }
        )
    mf_id = "cpi_headline.mf_energy_t1"
    if mf_id in episode_cache:
        mf_naive_episodes = [
            dict(e, predicted=e["naive"]) for e in episode_cache[mf_id] if e.get("naive") is not None
        ]
        windows = _contrast_stats(episode_cache[mf_id], mf_naive_episodes)
        labels = []
        tested_r = windows["tested"]["R"]
        if tested_r is not None and tested_r >= 1.00:
            labels.append("COMPLEXITY_NOT_EARNED")
        h4_contrasts.append(
            {
                "contrast": f"{mf_id}_vs_naive_prior",
                "complex_eval": mf_id,
                "simple_eval": "naive_prior",
                "labels": labels,
                "windows": windows,
            }
        )

    h4_intervals: list[dict] = []
    for receipt in eval_receipts:
        rows = _interval_rows(episode_cache[receipt["eval_id"]])
        rows.update({"eval_id": receipt["eval_id"], "family": receipt["family"]})
        h4_intervals.append(rows)

    family_coverage = {}
    for family, champion_id in FAMILY_CHAMPION.items():
        row = next(
            (r for r in h4_intervals if r["eval_id"] == champion_id), None
        )
        if row is None:
            continue
        family_coverage[family] = {
            "champion_eval": champion_id,
            "covered_k": row["covered_k"],
            "n": row["n_interval_scored"],
            "wilson_lo": row["wilson_lo"],
            "wilson_hi": row["wilson_hi"],
        }

    for receipt in eval_receipts:
        receipt.pop("_episodes", None)

    receipt = {
        "schema": SCHEMA,
        "status": "ok",
        "protocol": {"path": PROTOCOL_PATH, "sha256": protocol_sha},
        "trial": {
            "family": TRIAL_FAMILY,
            "n": TRIAL_N,
            "declared": bool(declare_budget),
            "sensitivity_rescorings": [
                {"eval": e.eval_id, "kind": kind, "trial": False}
                for e in EVALUATIONS
                for kind in ("S1", "S2")
            ],
        },
        "decision_asof": decision_asof,
        "inputs": inputs,
        "holm": {
            "family_size": TRIAL_N,
            "alpha": ALPHA,
            "raw": {k: _round(v) for k, v in p_normal_map.items()},
            "adjusted": {k: _round(v) for k, v in adjusted.items()},
            "adjusted_t": {k: _round(v) for k, v in adjusted_t.items()},
        },
        "evaluations": eval_receipts,
        "h4": {"contrasts": h4_contrasts, "intervals": h4_intervals, "family_coverage": family_coverage},
        "deviations": deviations,
        "gaps": gaps,
    }
    _write_receipt(out_dir, decision_asof, receipt)
    return receipt


def _target_source(family: str) -> str:
    if family in CPI_FAMILIES:
        return "data/release_forecast/cpi_truth/alfred_same_release_vintage_proxy_v1.json#published_proxy_1dp"
    series = TARGET_SERIES[family]
    return f"engine.release_target_truth.reconstruct_release_target({series}, release_date=None)"


def _blocked_evaluation(eval_rec: _Eval, *, reasons: list[str], message: str | None = None) -> dict:
    empty_windows = {
        window: {
            "n_scored": 0,
            "n_rows": 0,
            "honest_n": 0,
            "vs_naive": {"mean_d": None, "ci95": None, "R": None, "n": 0},
            "vs_strongest": {"mean_d": None, "ci95": None, "R": None, "n": 0},
        }
        for window, _ in WINDOWS
    }
    receipt = {
        "eval_id": eval_rec.eval_id,
        "family": eval_rec.family,
        "model_id": eval_rec.model_id,
        "target": {
            "id": f"{eval_rec.family}.same_release_first_print",
            "source": _target_source(eval_rec.family),
            "basis": "same_release_first_print",
        },
        "status": "blocked",
        "verdict": None,
        "reasons": list(reasons),
        "labels": [],
        "units_check": "not_checkable",
        "units_ratio": None,
        "pit_legs": [dict(leg) for leg in PIT_LEGS.get(eval_rec.eval_id, ())],
        "n_rows": {w: 0 for w, _ in WINDOWS},
        "honest_n": {w: 0 for w, _ in WINDOWS},
        "excluded": [],
        "missing_source": [],
        "release_date_mismatches": [],
        "baselines": {
            w: {
                "naive_mae": None,
                "trailing_3m_mae": None,
                "ar_model_mae": None,
                "strongest": None,
                "not_available": list(BASELINE_ORDER),
            }
            for w, _ in WINDOWS
        },
        "primary": {
            "dm": None, "p_normal": None, "p_t": None,
            "holm_adj": None, "holm_adj_t": None,
            "holm_clear": False, "borderline": False,
            "mean_d": None, "ci95": None, "R": None,
        },
        "windows": empty_windows,
        "sensitivities": {"S1": {"status": "not_applicable"}, "S2": {"status": "not_applicable"}},
        "sensitivity_flags": [],
        "message": message,
    }
    return receipt


def _d_series(episodes: Sequence[Mapping], window: str, base_key: str | None) -> list[float]:
    if base_key is None:
        return []
    start = dict(WINDOWS)[window]
    return [
        abs(float(e["target"]) - float(e["predicted"])) - abs(float(e["target"]) - float(e[base_key]))
        for e in episodes
        if e["period"] >= start and e.get(base_key) is not None
    ]


def _write_receipt(out_dir: Path, decision_asof: str, receipt: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"m0_requal_{decision_asof}.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=False, default=str), encoding="utf-8"
    )
    (out_dir / f"m0_requal_{decision_asof}.md").write_text(
        _markdown(receipt), encoding="utf-8"
    )


# --------------------------------------------------------------------------- #
# markdown receipt
# --------------------------------------------------------------------------- #
def _fmt(value: Any, reason: str = "insufficient episodes") -> str:
    if value is None:
        return f"not computed ({reason})"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _md_table_row(ev: Mapping) -> str:
    tested = ev["windows"].get("tested", {})
    primary = ev.get("primary") or {}
    n_rows = (ev.get("n_rows") or {}).get("tested")
    honest = (ev.get("honest_n") or {}).get("tested")
    ratio = (tested.get("vs_strongest") or {}).get("R")
    holm = primary.get("holm_adj")
    return " | ".join(
        [
            str(ev["eval_id"]),
            str(ev["target"]["id"]),
            _fmt(n_rows) + (f" (honest-N {honest})" if honest is not None else ""),
            _fmt(ratio),
            _fmt(holm),
            _fmt(ev.get("verdict"), reason="blocked evaluation"),
            ",".join(ev.get("reasons") or []) or "-",
        ]
    )


def _markdown(receipt: Mapping) -> str:
    lines: list[str] = []
    lines.append(f"# M0 coherent-target requalification — asof {receipt['decision_asof']}")
    lines.append("")
    lines.append(
        f"Protocol `{receipt['protocol']['path']}` sha256 `{receipt['protocol']['sha256']}`; "
        f"trial family `{receipt['trial']['family']}` n={receipt['trial']['n']} "
        f"declared={receipt['trial']['declared']}."
    )
    lines.append("")
    lines.append(
        "| eval | target | n tested | R tested (vs strongest) | Holm adj p | verdict | reasons |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for ev in receipt["evaluations"]:
        lines.append("| " + _md_table_row(ev) + " |")
    lines.append("")
    lines.append("## Sensitivities (verdict-free re-scorings)")
    for ev in receipt["evaluations"]:
        s1 = ev["sensitivities"].get("S1", {})
        s2 = ev["sensitivities"].get("S2", {})
        flags = ", ".join(ev.get("sensitivity_flags") or []) or "none"
        lines.append(
            f"- {ev['eval_id']}: S1 {_fmt(s1.get('status'))}"
            f" (dropped {_fmt(s1.get('n_dropped'))});"
            f" S2 {_fmt(s2.get('status'))} (affected {_fmt(s2.get('n_affected'))});"
            f" flags: {flags}"
        )
    lines.append("")
    lines.append("## H4 contrasts (descriptive)")
    for contrast in receipt["h4"]["contrasts"]:
        tested = contrast["windows"].get("tested", {})
        lines.append(
            f"- {contrast['contrast']}: tested R {_fmt(tested.get('R'))},"
            f" mean d {_fmt(tested.get('mean_d'))};"
            f" labels {','.join(contrast['labels']) or '-'}"
        )
    lines.append("")
    lines.append("## H4 interval calibration (per evaluation; per family coverage)")
    for row in receipt["h4"]["intervals"]:
        lines.append(
            f"- {row['eval_id']}: covered {row['covered_k']}/{row['n_interval_scored']}"
            f" (Wilson {_fmt(row['wilson_lo'])}–{_fmt(row['wilson_hi'])});"
            f" sharpness {_fmt(row['sharpness_median'])}"
            f" vs naive {_fmt(row['naive_sharpness_median'], reason='naive band unavailable')}"
            f" [{row['sharpness_status']}]; calibrated {_fmt(row['calibrated'])}"
        )
    for family, cov in receipt["h4"]["family_coverage"].items():
        lines.append(
            f"- family {family} (champion {cov['champion_eval']}): covered"
            f" {cov['covered_k']}/{cov['n']}"
            f" (Wilson {_fmt(cov['wilson_lo'])}–{_fmt(cov['wilson_hi'])})"
        )
    lines.append("")
    lines.append("## Exclusions and missing sources")
    for ev in receipt["evaluations"]:
        entries = [
            f"{m['release']}/{m['period']} ({m['reason']})" for m in ev["missing_source"]
        ] + [f"{e['period']} ({e['reason']})" for e in ev["excluded"]]
        if entries:
            lines.append(f"- {ev['eval_id']}: " + "; ".join(entries))
    lines.append("")
    if receipt.get("deviations"):
        lines.append("## DEVIATIONS")
        for dev in receipt["deviations"]:
            lines.append(f"- {dev['eval_id']}: " + ", ".join(dev["reasons"]))
        lines.append("")
    if receipt.get("gaps"):
        lines.append("## Gaps")
        for gap in receipt["gaps"]:
            lines.append(f"- {gap}")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--asof", required=True, help="decision asof date YYYY-MM-DD")
    parser.add_argument("--declare-budget", action="store_true")
    args = parser.parse_args(argv)
    receipt = run(
        args.root,
        args.out_dir,
        args.asof,
        declare_budget=args.declare_budget,
    )
    verdicts = {}
    for ev in receipt.get("evaluations", []):
        verdicts[ev["eval_id"]] = ev.get("verdict")
    print(json.dumps({"status": receipt["status"], "verdicts": verdicts}, default=str))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
