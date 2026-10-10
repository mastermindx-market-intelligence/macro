"""China predictive-validation harness — forward-return scorecard for the China signal legs.

LEAF · CONTEXT-ONLY · keyless · never raises into a build. The keystone Stage-3 honesty
layer: for every China signal that is RECONSTRUCTABLE from stored history it measures
whether the signal actually predicted forward returns, using the SAME institutional
primitives the US/vector calibrators use (engine.validation — imported and called VERBATIM,
never re-derived: rank_ic, ic_summary, newey_west_tstat, incremental_ic, benjamini_hochberg).

Signal families, each reconstructed from what is actually on disk today:

  * fundflow         — per-name 主力 (超大+大单) net inflow rate (GATED Tushare moneyflow_dc), a
                      CROSS-SECTIONAL signal validated like valuation off the accrued history in
                      data/tushare/flow_hist.parquet (collectors/tushare_history backfills it from
                      the paid history). sign_expected +1 (inflow → continuation). `accruing` when
                      the token / history is absent.
  * chips            — per-name 获利比例 win-rate (GATED Tushare cyq_perf), same cross-sectional path
                      off data/tushare/chips_hist.parquet. sign_expected −1 (euphoric → contrarian).
  * guidance         — 业绩预告 earnings-guidance surprise (GATED Tushare forecast), cross-sections
                      keyed by ann_date off data/tushare/forecast_hist.parquet. sign_expected +1
                      (positive guidance → post-announcement drift).


  * valuation       — per-name P/E·P/B own-history percentile (cheap = low pctile). A
                      CROSS-SECTIONAL signal → daily cross-sectional rank-IC vs each name's
                      forward CSI-300-relative return, summarized over a date grid, plus an
                      incremental-IC neutralization against {momentum_252, reversal_21, size}
                      (the honest "is value just reversal?" number — A-share value Sharpe is
                      known negative, so the leg is EXPECTED to wash out / validate wrong-sign).
  * margin          — whole-market financing balance as a share of float (fin_pct_float). A
                      MARKET-WIDE timing series, NOT a cross-section → validated as a market
                      timer: signed forward CSI-300 return regressed on the leg, pooled
                      Newey-West HAC t (high leverage = contrarian risk → sign_expected -1).
  * news_sentiment  — blended CCTV+wire media-sentiment z-score. Also MARKET-WIDE → same
                      market-timer path (rich sentiment = contrarian fade → sign_expected -1).

Forward returns come from the wide panel data/china_search/closes.parquet (cols = tickers),
benched to CSI 300 (510300.SS, resolved via store.read because it is NOT a panel column).
Leakage-guarded throughout: every forward return is measured PAST→FUTURE only, and a date
is only scored once the panel actually covers its forward end (mirrors china_radar_ledger._fwd_rel).

Anything without enough reconstructable history degrades to status "accruing" (n_obs 0) — the
conviction/hub LEDGERS (snapshot-forward) are the rigorous path that accrues from go-live.

SAMPLING CADENCE — why N is not a row count (2026-07-25)
-------------------------------------------------------
The fundflow/chips stores were designed as a WEEKLY grid (collectors/tushare_history._GRID_WEEKS
= 52) and this harness was written against that assumption. They are no longer weekly: `_grid_dates`
is tail-anchored (``idx[-260:][::5]``), so its stride phase-shifts by one trading day per build and
the append-only store accreted every phase. Measured 2026-07-25, flow_hist/chips_hist hold 273
distinct dates from 2025-05-26 to 2026-07-20 — a median gap of 1 trading day, ~20 dates/month where
a weekly grid would give ~4. forecast_hist (guidance) is event-keyed and likewise sub-weekly.

Consequences, and what this module does about each:

  * IC POINT ESTIMATES are unaffected. A cross-sectional rank-IC is invariant to any common
    per-date additive offset, so the finer grid changes only how often the same forward window
    is re-measured, not what it measures. Nothing here corrects them.
  * SIGNIFICANCE was inflated. Cross-sections one trading day apart share (h-1)/h of their
    forward window, so the per-date IC series is an MA(~h) process. The harness passed
    ``periods_per_year=12`` to ic_summary, which truncates Newey-West at 6 lags — right for a
    weekly grid at h<=21, but ~3x too few at daily h=21 and ~10x too few at h=63. Measured
    inflation on the live store: 1.1x at h=21, and 1.73x at h=63 (fundflow t 3.075 -> 1.772,
    crossing the |t|>=2 gate). Lags are now sized to the MEASURED cadence (`_hac_lags_for`).
  * N was inflated ~5x. `n_obs` counted scored rows: 272 where the design intended ~52, against
    a `_MIN_PROVEN_N` of 40 — a gate that could no longer bind on any grid this dense. The same
    14 months hold 56 distinct weeks and, at the headline 21d horizon, only 13 non-overlapping
    forward windows (4 at h=63). Promotion now gates on those honest counts; every horizon block
    prints `n_weeks`, `n_indep`, `sampling_step_td`, `hac_lags` and `overlap_ratio` alongside `n`.

The collector is deliberately left alone: the accreted daily panel is MORE data for the point
estimates and costs nothing to keep — it was only the inference that was wrong. See the
horizon-config comment in engine/flow_velocity.py (PR #3561) for the collector-side write-up.

validate_all() writes data/china_validation/scorecard.json (schema china_validation.v1) and
returns the same dict. Every public fn returns plain data / None and NEVER raises.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
from datetime import date, datetime, timezone
from pathlib import Path

from lib import config, store

log = logging.getLogger(__name__)

SCHEMA = "china_validation.v1"
BENCH = "510300.SS"                       # CSI 300 ETF — same bench as china_radar / its ledger
FDR_ALPHA = 0.10
# N gates are counted in DISTINCT WEEKS, not in scored rows. A row count is not a sample
# size when the grid is sampled finer than the forward window: flow_hist/chips_hist accreted
# to a ~daily cadence (see the module docstring), so the same ~14 months of history reports
# 272 cross-sections where the weekly design intended ~52. Weeks are cadence-INVARIANT — a
# genuine weekly grid still scores 1 per cross-section, so these thresholds keep their
# original meaning ("~40 weekly cross-sections") while a daily grid stops inflating them.
_MIN_PROVEN_N = 40                        # cross-sectional families (mirror hub_track_record._MIN_PROVEN_N)
_MIN_PROVEN_N_TS = 25                     # pooled time-series families (looser, fewer obs)
# Independent-evidence floor: non-overlapping forward windows at the headline horizon.
# 8 mirrors newey_west_tstat's own n<8 refusal — a HAC t computed over fewer genuinely
# disjoint windows than the primitive would accept observations is not evidence, however
# many overlapping rows fed it. At h=63 over 14 months this is 4, which is why the 63d
# cells must never carry a verdict (chips still reads |t| 2.61 there).
_MIN_INDEP_WINDOWS = 8
_TD_PER_YEAR = 252

# (family -> expected SIGN of mean predictive IC / regression slope). A leg that validates
# to the WRONG sign is actively misleading; signal_lab will zero its weight. A-share value /
# leverage / sentiment all carry a contrarian prior (cheap or de-levered or fearful outperforms).
_SIGN_EXPECTED = {"valuation": +1, "margin": -1, "news_sentiment": -1,
                  "fundflow": +1, "chips": -1, "guidance": +1}
# fundflow: 主力 net inflow → continuation (+1, the accumulation prior).
# chips:    high 获利比例 win-rate → euphoric/profit-taking → contrarian fade (−1).
# guidance: positive 业绩预告 (预增/扭亏…) → positive forward return (+1, post-earnings drift).
# All are PRIORS only — the harness measures the realized sign and signal_lab zeros a
# proven wrong-sign leg regardless.


# --------------------------------------------------------------------------- #
# CIE-18 preregistration admission — PURE guard, no outcome read / no new store
# --------------------------------------------------------------------------- #

CIE18_PREREG_SCHEMA = "china_cie18_prereg.v1"
_CIE18_TRACKS = frozenset({"D", "O", "M"})
_CIE18_PLACEHOLDERS = frozenset({
    "", "tbd", "todo", "pending", "unknown", "unset", "later", "n/a", "na",
})
_CIE18_FORBIDDEN_RESULT_KEYS = frozenset({
    "results", "holdout_results", "point_estimates", "p_values",
    "observed_effect", "observed_alpha", "promotion_decision",
    "final_disposition", "winning_variant",
    # Derived admission/read fields may never be supplied by the prereg itself.
    "admitted_for_outcome_read", "outcome_read_eligible",
    "structurally_admissible_for_runner_binding", "outcome_read_blockers",
})

_CIE18_COMMON_FIELDS = (
    "schema",
    "experiment_id",
    "version",
    "track",
    "mechanism",
    "role",
    "sign_prior",
    "horizon",
    "horizon_unit",
    "falsifier",
    "source_owner_refs",
    "source_use_permissions",
    "population_manifest",
    "availability_contract",
    "outcome_contract",
    "development_interval",
    "holdout_interval",
    "prospective_contract",
    "primary_metric",
    "minimum_useful_effect",
    "downside_bound",
    "multiplicity",
    "clustering",
    "power",
    "stopping_rule",
    "trial_family",
    "declared_trial_budget",
    "attempted_variants",
    "negative_controls",
    "cost_capacity_contract",
    "source_reliability_contract",
    "code_sha",
    "input_hashes",
    "outcome_access_state",
)

_CIE18_TRACK_FIELDS = {
    # Discovery before candidate admission.
    "D": (
        "lawful_asof_universe",
        "equal_budget_control",
        "lead_time_clock",
        "future_admission_is_endpoint_only",
        "resource_budget",
    ),
    # Ordering among exactly identical lawful candidates.
    "O": (
        "candidate_snapshot_manifest",
        "actual_serving_policy",
        "fallback_state",
        "deterministic_tiebreak",
        "original_fill_owner",
        "population_identity_rule",
    ),
    # Post-admission evidence/falsifier monitoring.
    "M": (
        "thesis_falsifier_version",
        "alert_policy",
        "observability_rule",
        "action_rule",
        "adjudication_policy",
        "alert_budget",
    ),
}


def _cie18_present(value) -> bool:
    """True only for a substantive frozen prereg value, never a placeholder."""
    if value is None:
        return False
    if isinstance(value, bool):
        return True
    if isinstance(value, str):
        return value.strip().lower() not in _CIE18_PLACEHOLDERS
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _cie18_finite_number(value, *, positive: bool = False, nonnegative: bool = False) -> bool:
    if isinstance(value, bool):
        return False
    try:
        x = float(value)
    except (TypeError, ValueError):
        return False
    if not math.isfinite(x):
        return False
    if positive and x <= 0:
        return False
    if nonnegative and x < 0:
        return False
    return True


def _cie18_sha(value) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip().lower()
    return len(text) in (40, 64) and all(ch in "0123456789abcdef" for ch in text)


def _cie18_interval(value) -> tuple[date, date] | None:
    """Parse a closed prereg interval {start,end}; no inferred/open holdout dates."""
    if not isinstance(value, dict):
        return None
    try:
        start = date.fromisoformat(str(value.get("start") or "")[:10])
        end = date.fromisoformat(str(value.get("end") or "")[:10])
    except (TypeError, ValueError):
        return None
    return (start, end) if start <= end else None


def _cie18_metric_contract(value) -> bool:
    if not isinstance(value, dict):
        return False
    return (
        _cie18_present(value.get("name"))
        and _cie18_present(value.get("definition"))
        and value.get("direction") in {"higher_is_better", "lower_is_better"}
    )


def _cie18_multiplicity_contract(value) -> bool:
    if not isinstance(value, dict):
        return False
    alpha = value.get("confirmation_alpha")
    method = str(value.get("confirmation_method") or "").strip().lower()
    family = value.get("confirmation_family")
    if method not in {"holm_fwer", "bonferroni_fwer", "closed_testing_fwer"}:
        return False
    if not _cie18_finite_number(alpha, positive=True) or float(alpha) > 0.05:
        return False
    if not _cie18_present(family):
        return False
    # Exploratory FDR may coexist, but it may not masquerade as confirmation.
    if value.get("exploratory_method") is not None:
        em = str(value.get("exploratory_method") or "").strip().lower()
        if em not in {"bh_fdr", "by_fdr", "none"}:
            return False
    return True


def _cie18_stopping_contract(value) -> bool:
    if not isinstance(value, dict):
        return False
    mode = str(value.get("mode") or "").strip().lower()
    if mode == "fixed_no_interim_inference":
        return _cie18_present(value.get("final_read_rule"))
    if mode == "sequential_alpha_spending":
        return (
            _cie18_present(value.get("spending_rule"))
            and _cie18_present(value.get("look_schedule"))
            and _cie18_finite_number(value.get("total_alpha"), positive=True)
            and float(value["total_alpha"]) <= 0.05
        )
    return False


def _cie18_prospective_contract(value) -> bool:
    """A prospective leg may have an unknown calendar end, but its stop rule is frozen."""
    if not isinstance(value, dict):
        return False
    try:
        start = date.fromisoformat(str(value.get("start") or "")[:10])
    except (TypeError, ValueError):
        return False
    return bool(start) and _cie18_present(value.get("end_rule"))


def cie18_prereg_digest(record: dict) -> str:
    """Semantic digest of one prereg record; derived fields never participate."""
    if not isinstance(record, dict):
        raise ValueError("CIE-18 prereg must be a dict")
    payload = {
        k: v for k, v in record.items()
        if k not in {
            "prereg_digest",
            "validation_errors",
            "admitted_for_outcome_read",
            "outcome_read_eligible",
            "outcome_read_blockers",
            "structurally_admissible_for_runner_binding",
        }
    }
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def validate_cie18_prereg(record: dict) -> dict:
    """Fail-closed admission proof for CIE-18 D/O/M empirical work.

    This function is PURE. It reads no data, outcomes, files, clock, network or
    model and writes no ledger. A passing return means only that the experiment's
    pre-outcome contract is structurally frozen enough for a canonical runner to
    bind later; it is not scientific acceptance, power proof, or permission to
    view a final holdout.

    Numeric useful-effect/downside values are deliberately caller-owned: this
    guard requires them to exist before the final outcome read but does not invent
    them from this module.
    """
    errors: list[str] = []
    if not isinstance(record, dict):
        return {
            "schema": CIE18_PREREG_SCHEMA,
            "structurally_admissible_for_runner_binding": False,
            "outcome_read_eligible": False,
            "outcome_read_blockers": ["prereg_structural_validation_failed"],
            "validation_errors": ["record_not_mapping"],
            "disposition_if_incomplete": "ACCRUAL_GATED",
            "prereg_digest": None,
        }

    for field in _CIE18_COMMON_FIELDS:
        if not _cie18_present(record.get(field)):
            errors.append(f"missing_or_placeholder:{field}")

    if record.get("schema") != CIE18_PREREG_SCHEMA:
        errors.append("schema_mismatch")

    track = str(record.get("track") or "").strip().upper()
    if track not in _CIE18_TRACKS:
        errors.append("track_invalid")
    else:
        for field in _CIE18_TRACK_FIELDS[track]:
            if not _cie18_present(record.get(field)):
                errors.append(f"missing_or_placeholder:{field}")

    # The prereg itself may never carry a viewed result.
    forbidden = sorted(k for k in _CIE18_FORBIDDEN_RESULT_KEYS if k in record)
    errors.extend(f"outcome_field_forbidden:{k}" for k in forbidden)
    if str(record.get("outcome_access_state") or "") != "SEALED_UNSEEN":
        errors.append("outcome_access_state_must_be_SEALED_UNSEEN")

    if not _cie18_metric_contract(record.get("primary_metric")):
        errors.append("primary_metric_contract_invalid")
    if not _cie18_finite_number(record.get("minimum_useful_effect"), positive=True):
        errors.append("minimum_useful_effect_must_be_positive_finite")
    if not _cie18_finite_number(record.get("downside_bound"), nonnegative=True):
        errors.append("downside_bound_must_be_nonnegative_finite")

    if not _cie18_multiplicity_contract(record.get("multiplicity")):
        errors.append("multiplicity_contract_invalid")
    if not _cie18_stopping_contract(record.get("stopping_rule")):
        errors.append("stopping_rule_invalid")

    horizon = record.get("horizon")
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 1:
        errors.append("horizon_must_be_positive_int")

    budget = record.get("declared_trial_budget")
    if isinstance(budget, bool) or not isinstance(budget, int) or budget < 1:
        errors.append("declared_trial_budget_must_be_positive_int")
    variants = record.get("attempted_variants")
    if isinstance(budget, int) and not isinstance(budget, bool) \
            and isinstance(variants, list) and budget < len(variants):
        errors.append("declared_trial_budget_below_registered_variants")

    if _cie18_interval(record.get("development_interval")) is None:
        errors.append("development_interval_invalid")
    if _cie18_interval(record.get("holdout_interval")) is None:
        errors.append("holdout_interval_invalid")
    else:
        dev = _cie18_interval(record.get("development_interval"))
        hold = _cie18_interval(record.get("holdout_interval"))
        if dev is not None and hold is not None and dev[1] >= hold[0]:
            errors.append("development_holdout_overlap")
    prospective = record.get("prospective_contract")
    if not _cie18_prospective_contract(prospective):
        errors.append("prospective_contract_invalid")
    else:
        hold = _cie18_interval(record.get("holdout_interval"))
        try:
            prospective_start = date.fromisoformat(str(prospective.get("start") or "")[:10])
        except (TypeError, ValueError):
            prospective_start = None
        if hold is not None and prospective_start is not None and hold[1] >= prospective_start:
            errors.append("holdout_prospective_overlap")

    power = record.get("power")
    if not isinstance(power, dict) \
            or str(power.get("basis") or "") != "development_only" \
            or not _cie18_finite_number(power.get("minimum_independent_n"), positive=True):
        errors.append("power_contract_must_be_development_only")

    clustering = record.get("clustering")
    if not isinstance(clustering, dict) \
            or not _cie18_present(clustering.get("unit")) \
            or clustering.get("effective_n_reported") is not True:
        errors.append("clustering_contract_invalid")

    if not _cie18_sha(record.get("code_sha")):
        errors.append("code_sha_invalid")
    hashes = record.get("input_hashes")
    if not isinstance(hashes, dict) or not hashes:
        errors.append("input_hashes_invalid")
    else:
        for key, value in hashes.items():
            if not _cie18_present(key) or not _cie18_sha(value):
                errors.append(f"input_hash_invalid:{key}")

    # Track-specific truth fences.
    if track == "D":
        if record.get("future_admission_is_endpoint_only") is not True:
            errors.append("track_D_future_admission_must_be_endpoint_only")
        if str(record.get("lead_time_clock") or "") != "EVIDENCE_AVAILABLE_AT":
            errors.append("track_D_lead_time_clock_must_be_evidence_available")
    elif track == "O":
        if str(record.get("population_identity_rule") or "") != "EXACT_SAME_CANDIDATES_AND_TIME":
            errors.append("track_O_population_identity_rule_invalid")
        if not isinstance(record.get("fallback_state"), dict):
            errors.append("track_O_fallback_state_must_be_explicit")
    elif track == "M":
        if not isinstance(record.get("action_rule"), dict):
            errors.append("track_M_action_rule_must_be_explicit")
        elif record["action_rule"].get("automatic_trade") is not False:
            errors.append("track_M_automatic_trade_must_be_false_without_separate_authority")

    # Exact variant/negative-control lists are required, even when the chosen set
    # has one member. A string is not a trial family.
    for field in ("attempted_variants", "negative_controls"):
        value = record.get(field)
        if not isinstance(value, list) or not value:
            errors.append(f"{field}_must_be_nonempty_list")

    errors = sorted(set(errors))
    structurally_ready = not errors
    digest = cie18_prereg_digest(record) if structurally_ready else None

    # This pure structural guard NEVER grants outcome access. Upstream acceptance
    # receipts are canonical-owner facts and cannot be supplied as arbitrary
    # prereg prose. A later owner-bound gate may consume this structural receipt,
    # but the holdout remains sealed here.
    outcome_read_blockers: list[str] = []
    if not structurally_ready:
        outcome_read_blockers.append("prereg_structural_validation_failed")
    else:
        if track == "O":
            outcome_read_blockers.append(
                "cie02_serving_fill_acceptance_required"
            )
        outcome_read_blockers.extend([
            "cie03_outcome_baseline_acceptance_required",
            "accepted_family_consumer_receipt_required",
            "canonical_outcome_access_gate_not_bound",
        ])

    return {
        "schema": CIE18_PREREG_SCHEMA,
        "track": track or None,
        "experiment_id": record.get("experiment_id"),
        "version": record.get("version"),
        "structurally_admissible_for_runner_binding": structurally_ready,
        "outcome_read_eligible": False,
        "outcome_read_blockers": outcome_read_blockers,
        "validation_errors": errors,
        "disposition_if_incomplete": (
            None if structurally_ready else "ACCRUAL_GATED"
        ),
        "scientific_state": (
            "STRUCTURALLY_PREREGISTERED_OUTCOME_SEALED"
            if structurally_ready else "ACCRUAL_GATED"
        ),
        "prereg_digest": digest,
        "trial_family": record.get("trial_family"),
        "declared_trial_budget": record.get("declared_trial_budget"),
    }


def register_cie18_trial_budget(record: dict, ledger) -> dict:
    """Bind a *valid* prereg to the existing TrialLedger before experiment work.

    The ledger is injected deliberately: this helper never creates a second
    multiple-testing store or silently writes the production ledger. Callers must
    pass the canonical TrialLedger owner they are already using.
    """
    receipt = validate_cie18_prereg(record)
    if not receipt["structurally_admissible_for_runner_binding"]:
        raise ValueError("CIE-18 prereg is not structurally admissible: " + "; ".join(
            receipt["validation_errors"]
        ))
    if ledger is None or not all(
        hasattr(ledger, name) for name in ("log_declared_budget", "declared_budget")
    ):
        raise ValueError("canonical TrialLedger instance is required")
    family = str(record["trial_family"])
    budget = int(record["declared_trial_budget"])
    ledger.log_declared_budget(
        budget,
        family=family,
        reason=f"CIE-18 {record['track']} prereg {record['experiment_id']} "
               f"v{record['version']} digest={receipt['prereg_digest']}",
    )
    observed = int(ledger.declared_budget(family))
    if observed < budget:
        raise RuntimeError("trial ledger failed to preserve declared CIE-18 budget")
    return {
        **receipt,
        "trial_budget_registered": True,
        "trial_budget_observed": observed,
    }


# --------------------------------------------------------------------------- #
# leak-guarded forward returns from the wide panel  (mirror china_radar_ledger._fwd_rel)
# --------------------------------------------------------------------------- #
def _bench_close():
    """CSI-300 close Series (the bench is NOT a panel column). None on miss."""
    try:
        b = store.read("china", BENCH)
        if b is None or b.empty or "close" not in b.columns:
            return None
        import pandas as pd  # noqa: F401
        return b["close"].dropna()
    except Exception:  # noqa: BLE001
        return None


def _panel():
    """Wide close panel (Date index, cols = tickers). None on miss."""
    try:
        df = store.read("china_search", "closes")
        if df is None or df.empty:
            return None
        return df
    except Exception:  # noqa: BLE001
        return None


def _fwd_rel_panel(panel, bench, horizon: int):
    """Per-name forward CSI-300-RELATIVE return over `horizon` trading days, as a DataFrame
    aligned to the panel (row d, col t = name return d->d+h MINUS bench return d->d+h).
    Vectorized: one pct_change(horizon) on the whole panel, shifted to land the forward
    window on its START date. Leakage-safe — the value at date d uses only dates >= d, and
    callers must additionally drop dates whose forward end the panel does not yet cover.
    """
    try:
        import numpy as np  # noqa: F401
        import pandas as pd
        px = panel.apply(pd.to_numeric, errors="coerce")
        # forward h-day return realized over (d, d+h], stamped on START date d
        fwd = px.pct_change(horizon).shift(-horizon)
        # bench forward return aligned to the SAME row index
        bc = pd.to_numeric(bench, errors="coerce").reindex(px.index).ffill()
        bfwd = bc.pct_change(horizon).shift(-horizon)
        rel = fwd.sub(bfwd, axis=0) * 100.0
        return rel
    except Exception as e:  # noqa: BLE001
        log.debug("china_validation._fwd_rel_panel failed (%s)", e)
        return None


def _last_covered(panel, horizon: int):
    """Last panel date whose forward end (+horizon rows) is still inside the panel — the
    leak guard: any signal date AFTER this has no realized forward return yet."""
    try:
        if panel is None or len(panel.index) <= horizon:
            return None
        return panel.index[-(horizon + 1)]
    except Exception:  # noqa: BLE001
        return None


# --------------------------------------------------------------------------- #
# reconstructable cross-sectional signal: own-history valuation percentile
# --------------------------------------------------------------------------- #
def _valuation_cross_sections():
    """{asof_date(Timestamp): Series(ticker -> cheapness)} from the valuation percentile
    cache. cheapness = -(mean of pe.pctile, pb.pctile)/100 so that a HIGHER signal = CHEAPER
    (sign_expected +1 means cheap predicts positive forward returns). Empty dict on miss.

    Only the snapshots actually stored are returned (today this is a few asof days — that
    yields < MIN_DATES cross-sections, so the family honestly reports `accruing`)."""
    out: dict = {}
    try:
        import pandas as pd
        p = config.data_dir() / "china_valuation" / "percentiles.parquet"
        if not p.exists():
            return out
        df = pd.read_parquet(p)
        if df.empty or "asof" not in df.columns:
            return out
        for asof, grp in df.groupby(df["asof"].astype(str)):
            ser = {}
            for _, r in grp.iterrows():
                try:
                    pay = json.loads(r["payload"])
                except Exception:  # noqa: BLE001
                    continue
                pe = (pay.get("pe") or {}).get("pctile")
                pb = (pay.get("pb") or {}).get("pctile")
                vals = [v for v in (pe, pb) if isinstance(v, (int, float))]
                if not vals:
                    continue
                ser[str(r["ticker"])] = -(sum(vals) / len(vals)) / 100.0
            if len(ser) >= 10:
                out[pd.Timestamp(asof)] = pd.Series(ser, dtype=float)
    except Exception as e:  # noqa: BLE001
        log.debug("china_validation._valuation_cross_sections failed (%s)", e)
    return out


def _factor_loadings(panel, asof, horizon_lookback: int = 252):
    """{ticker -> {momentum_252, reversal_21, size}} cross-section AS OF `asof` for the
    incremental-IC neutralization. Uses only PAST prices (<= asof) — leakage-safe. None/empty
    if the panel doesn't reach back far enough."""
    try:
        import pandas as pd
        px = panel[panel.index <= asof].apply(pd.to_numeric, errors="coerce")
        if len(px) < 30:
            return None
        last = px.iloc[-1]
        # momentum_252: 12m return skipping the most recent ~21d (12-1, the robust leg)
        mom_win = min(horizon_lookback, len(px) - 1)
        skip = min(21, mom_win - 1)
        past = px.iloc[-(mom_win + 1)] if mom_win + 1 <= len(px) else px.iloc[0]
        recent = px.iloc[-(skip + 1)] if skip + 1 <= len(px) else last
        mom = (recent / past) - 1.0
        # reversal_21: short-term reversal (NEGATIVE of last-21d return)
        rev_base = px.iloc[-(skip + 1)] if skip + 1 <= len(px) else px.iloc[0]
        rev = -((last / rev_base) - 1.0)
        # size proxy: log price level (no shares-out on disk) — coarse but orthogonalizes scale
        import numpy as np
        size = pd.Series(np.log(last.where(last > 0)), index=last.index)
        load = pd.concat([mom.rename("momentum_252"), rev.rename("reversal_21"),
                          size.rename("size")], axis=1)
        return load.dropna(how="all")
    except Exception as e:  # noqa: BLE001
        log.debug("china_validation._factor_loadings failed (%s)", e)
        return None


# --------------------------------------------------------------------------- #
# reconstructable market-wide timing series (margin leverage, media sentiment)
# --------------------------------------------------------------------------- #
def _margin_series():
    """Whole-market financing-balance-as-%-of-float, z-scored on its own trailing history.
    Market-wide → validated as a TIMER, not a cross-section. None on miss."""
    try:
        import pandas as pd
        m = store.read("china_margin", "balance")
        if m is None or m.empty or "fin_pct_float" not in m.columns:
            return None
        s = pd.to_numeric(m["fin_pct_float"], errors="coerce").dropna()
        if len(s) < 60:
            return None
        z = (s - s.rolling(252, min_periods=60).mean()) / s.rolling(252, min_periods=60).std()
        return z.dropna()
    except Exception as e:  # noqa: BLE001
        log.debug("china_validation._margin_series failed (%s)", e)
        return None


def _news_sentiment_series():
    """Blended media-sentiment z (reuses china_news_intel's own blended-tone series).

    Market-wide timer series. Z-scored against the best available baseline:

    W4 long-history hybrid (D5 / spec §2.2):
      When cctv_tone_history.parquet exists (written by scripts/rebuild_cctv_tone_history.py
      after the CCTV backfill), we use the FULL 10-year CCTV history as the reference
      distribution for the z-score.  This is the mechanism that makes the news_sentiment
      family satisfy the ≥60-day and ≥25-obs requirements for the §3 gate:

        - Without the history: the live series has only ~19 points → n_obs stays 0.
        - With the history: we have ≥3,700 usable broadcaster-days → the blended series
          z-scores against a genuine long-run distribution → meaningful n_obs for the
          _validate_timer call.

    Fallback: when the history file is absent or has < 60 ok rows, we z-score against
    a 252-day rolling window (minimum 60 obs), which keeps the family in `accruing`
    (n_obs < 8) until enough live data accrues — the pre-W4 behaviour.

    PIT-correctness note: the history baseline is computed from PAST data only; the live
    series is z-scored using (raw − baseline_μ) / baseline_σ where μ/σ come from the full
    10-year smoothed series — there is no forward leakage because the history ends before
    the live series begins (the backfill covers 2016-02 → ~today, the live series covers
    the most recent ~19 broadcast days, and the z-score denominator is fixed at build time
    rather than being a look-ahead window).

    None on miss.
    """
    try:
        import pandas as pd
        from pathlib import Path
        from engine import china_news_intel as cni
        from engine.china_news import _load_tone_history_baseline

        # Live blended series (CCTV + wire)
        s_live = cni._blended_tone_series()

        # Try long-history baseline first (W4 path)
        history_baseline = _load_tone_history_baseline()

        if history_baseline is not None and len(history_baseline) >= 60:
            # W4 path: z-score the live series against the 10-year CCTV distribution.
            # We need the blended series for the _validate_timer call; if live is too
            # short we use the history directly as the "signal series" for the timer.
            baseline_mu = float(history_baseline.mean())
            baseline_sd = float(history_baseline.std(ddof=1)) if len(history_baseline) > 1 else 1.0
            if baseline_sd < 1e-9:
                baseline_sd = 1.0

            # Build the full signal series by concatenating the history + live:
            # use the raw history tone (not the z'd version) and z-score the whole concat.
            hist_tone = pd.to_numeric(history_baseline, errors="coerce").dropna()

            if s_live is not None and not s_live.empty:
                live_s = pd.to_numeric(s_live, errors="coerce").dropna()
                # Concatenate, drop overlap (live wins for duplicate dates)
                combined = pd.concat([hist_tone, live_s])
                combined = combined[~combined.index.duplicated(keep="last")].sort_index()
            else:
                combined = hist_tone

            if len(combined) < 8:
                return None

            # Z-score against the fixed long-history distribution
            z = (combined - baseline_mu) / baseline_sd
            return z.dropna()

        # Fallback: rolling-window z on the live blended series
        if s_live is None or len(s_live) < 60:
            return None
        s = pd.to_numeric(s_live, errors="coerce").dropna()
        z = (s - s.rolling(252, min_periods=60).mean()) / s.rolling(252, min_periods=60).std()
        return z.dropna()
    except Exception as e:  # noqa: BLE001
        log.debug("china_validation._news_sentiment_series failed (%s)", e)
        return None


def _bench_fwd_series(bench, horizon: int):
    """Bench forward h-day return stamped on the START date (leak-safe, value at d uses d->d+h)."""
    try:
        import pandas as pd
        bc = pd.to_numeric(bench, errors="coerce").dropna()
        return bc.pct_change(horizon).shift(-horizon).dropna()
    except Exception:  # noqa: BLE001
        return None


def _accruing(family: str, reason: str = "no reconstructable history") -> dict:
    return {"family": family, "status": "accruing", "tier": "display", "proven": False,
            "n_obs": 0, "by_horizon": {}, "sign_expected": _SIGN_EXPECTED.get(family),
            "reason": reason, "is_context_only": True}


def _tier_for(t_hac, q_fdr, n_obs, proven) -> str:
    """Computed tier the signal_lab consumes: scored / confirmer / pending / display."""
    if proven:
        return "scored"
    try:
        if t_hac is not None and abs(t_hac) >= 1.5 and (q_fdr is None or q_fdr <= 0.20):
            return "confirmer"
    except (TypeError, ValueError):
        pass
    return "pending" if n_obs else "display"


# --------------------------------------------------------------------------- #
# sampling-cadence forensics — how much INDEPENDENT evidence is really here
#
# Every count below answers a question a raw row count cannot. A scored grid whose step is
# finer than the forward horizon repeats the same forward window over and over: the IC point
# estimate is unaffected (a common per-date offset cancels out of a cross-sectional rank
# correlation), but the row count, the HAC lag and therefore the t-stat all become fiction.
# --------------------------------------------------------------------------- #
def _cal_positions(dates, calendar):
    """Positions of `dates` on the trading calendar (sorted, de-duped, misses dropped).
    Trading-day positions — NOT calendar days — so weekends/holidays never masquerade as
    sampling gaps. Empty list when the calendar can't resolve them."""
    try:
        import pandas as pd
        idx = pd.Index(calendar)
        pos = idx.get_indexer(pd.DatetimeIndex(sorted(set(dates))))
        return sorted(int(p) for p in pos if p >= 0)
    except Exception as e:  # noqa: BLE001
        log.debug("china_validation._cal_positions failed (%s)", e)
        return []


def _sampling_step(pos) -> float:
    """Median gap between consecutive scored dates, in TRADING DAYS. 1.0 = a daily grid,
    ~5.0 = the weekly grid this harness was originally written for."""
    try:
        if len(pos) < 2:
            return 1.0        # cadence unknowable → assume the densest grid (most HAC lags)
        import numpy as np
        return max(1.0, float(np.median(np.diff(pos))))
    except Exception:  # noqa: BLE001
        return 1.0            # fail CONSERVATIVE: a short step buys more lags, never fewer


def _hac_lags_for(horizon: int, step: float) -> int:
    """Newey-West truncation lag in SAMPLING STEPS for a `horizon`-day forward window.

    Consecutive scored dates share (horizon − step) days of their forward window, so the IC
    series is an MA process of order ~horizon/step and the Bartlett kernel must span it.
    Under the weekly design (step 5, h 21) this returns 5 — near the hard-coded 6 the harness
    used to pass, which is why the constant looked right. Under a daily grid the same h=21
    needs 21, and 6 understates the long-run variance by ~3x (t inflated ~1.8x at h=63)."""
    import math
    return max(1, int(math.ceil(float(horizon) / max(float(step), 1.0))))


def _disjoint_windows(pos, horizon: int) -> int:
    """Count of NON-OVERLAPPING forward windows among the scored dates — the honest
    independent-observation count. Greedy left-to-right: take a date, skip everything whose
    forward window still overlaps it, repeat. This is what `n` would have been had the grid
    been sampled at the horizon instead of below it."""
    try:
        h = max(1, int(horizon))
        n, end = 0, None
        for p in sorted(pos):
            if end is None or p >= end:
                n += 1
                end = p + h
        return n
    except Exception:  # noqa: BLE001
        return 0


def _distinct_weeks(dates) -> int:
    """Distinct ISO weeks covered by the scored dates — the cadence-INVARIANT restatement of
    the design's '52 weekly cross-sections' unit. A weekly grid scores 1 per cross-section
    (unchanged bar); a daily grid over the same span scores the same ~52 rather than ~260."""
    try:
        import pandas as pd
        d = pd.DatetimeIndex(sorted(set(dates)))
        if len(d) == 0:
            return 0
        iso = d.isocalendar()
        return int(len({(int(y), int(w)) for y, w in zip(iso.year, iso.week)}))
    except Exception as e:  # noqa: BLE001
        log.debug("china_validation._distinct_weeks failed (%s)", e)
        return 0


# --------------------------------------------------------------------------- #
# per-family validators  (call engine.validation primitives VERBATIM)
# --------------------------------------------------------------------------- #
def _hist_cross_sections(name: str, col: str, date_col: str = "date") -> dict:
    """{asof(Timestamp): Series(ticker->signal)} from a data/tushare/<name>.parquet ({ticker,date_col,col})
    accruing-history cache. Empty dict on miss / token-absent (no history)."""
    out: dict = {}
    try:
        import pandas as pd
        p = config.data_dir() / "tushare" / f"{name}.parquet"
        if not p.exists():
            return out
        df = pd.read_parquet(p)
        if df.empty or date_col not in df.columns or col not in df.columns or "ticker" not in df.columns:
            return out
        for dt, grp in df.groupby(df[date_col].astype(str)):
            ser = {str(t): float(v) for t, v in zip(grp["ticker"], grp[col])
                   if isinstance(v, (int, float)) and v == v}
            if len(ser) >= 10:
                out[pd.Timestamp(dt)] = pd.Series(ser, dtype=float)
    except Exception as e:  # noqa: BLE001
        log.debug("china_validation._hist_cross_sections(%s) failed (%s)", name, e)
    return out


def _validate_xs(V, family, xs, panel, bench, horizons, neutralize: bool = True) -> dict:
    """Generic CROSS-SECTIONAL forward-return rank-IC over a {asof: Series(ticker->signal)} grid,
    vs each name's forward CSI-300-relative return, with an optional incremental-IC neutralization
    against {momentum_252, reversal_21, size}. Leak-guarded (a date is scored only once its forward
    end is realized in the panel). Shared by valuation / fundflow / chips / guidance.

    OVERLAP-AWARE. The grid's cadence is MEASURED per horizon rather than assumed, because the
    stores it reads no longer sample weekly (module docstring). Two corrections follow from it:
    the HAC truncation lag is sized to the real overlap (`_hac_lags_for`), and the promotion gate
    counts distinct weeks + non-overlapping forward windows instead of scored rows. The IC point
    estimates are untouched — only the claim of confidence in them changes."""
    try:
        if not xs:
            return _accruing(family, f"{family} history empty")
        if panel is None or bench is None:
            return _accruing(family, "price panel / bench missing")
        by_h: dict = {}
        max_n = 0
        for h in horizons:
            rel = _fwd_rel_panel(panel, bench, h)
            covered = _last_covered(panel, h)
            if rel is None or covered is None:
                continue
            sig_by_date, fwd_by_date, load_by_date = {}, {}, {}
            ics, scored = [], []
            for asof, sig in xs.items():
                if asof > covered:
                    continue                             # leak guard: forward end not realized
                # align the cross-section to the nearest panel row on/after asof
                idx = rel.index[rel.index >= asof]
                if len(idx) == 0:
                    continue
                row = rel.loc[idx[0]].dropna()
                if len(row) < 10:
                    continue
                ics.append(V.rank_ic(sig, row))
                scored.append(idx[0])                    # the PANEL row actually scored
                sig_by_date[asof] = sig
                fwd_by_date[asof] = row
                if neutralize:
                    load = _factor_loadings(panel, idx[0])
                    if load is not None and len(load):
                        load_by_date[asof] = load
            # measured cadence → honest lag + honest N (never assumed weekly)
            pos = _cal_positions(scored, panel.index)
            step = _sampling_step(pos)
            lags = _hac_lags_for(h, step)
            n_indep = _disjoint_windows(pos, h)
            n_weeks = _distinct_weeks(scored)
            summ = V.ic_summary(ics, periods_per_year=12, hac_lags=lags)
            n = summ.get("n", 0)
            max_n = max(max_n, n)
            block = {"mean_ic": summ.get("mean_ic"), "ic_ir": summ.get("ic_ir"),
                     "t_hac": summ.get("t_hac"), "p_hac": summ.get("p_hac"),
                     "hit": summ.get("hit"), "n": n,
                     # honest N — printed for EVERY horizon, gate or no gate
                     "n_weeks": n_weeks, "n_indep": n_indep,
                     "sampling_step_td": round(step, 2), "hac_lags": lags,
                     "overlap_ratio": round(max(1.0, h / max(step, 1.0)), 2)}
            if neutralize and len(load_by_date) >= 6:
                inc = V.incremental_ic(sig_by_date, fwd_by_date, load_by_date,
                                       periods_per_year=12, hac_lags=lags)
                block["incremental"] = {"surviving_frac": inc.get("surviving_frac"),
                                        "ic_delta": inc.get("ic_delta")}
            by_h[str(h)] = block
        if not by_h or max_n < 6:
            return _accruing(family, f"only {max_n} cross-sections (< MIN_DATES 6)")
        return _finalize(family, by_h, max_n, _MIN_PROVEN_N)
    except Exception as e:  # noqa: BLE001
        log.error("china_validation._validate_xs(%s) failed (%s)", family, e)
        return _accruing(family, "exception")


def _validate_timer(V, family, sig, panel, bench, horizons) -> dict:
    """Market-wide TIMER validation: regress signed forward CSI-300 return on the (lagged)
    signal level; pooled Newey-West HAC t on signal·fwd_return product per horizon. Sign of
    the mean product is the predictive sign. Leak-safe (forward stamped on signal date).

    The HAC lag here was already horizon-aware (`lags = h - 1` on a daily series), so the
    t-stats are sound. The N was not: these series are daily, so a 21-day horizon reports
    ~3400 overlapping obs against a 25-obs gate. config/qual_ladder.yml already specifies
    "n_dates >= 25 (not overlapping obs)" for the news_sentiment family — this counts weeks
    and non-overlapping windows so the code honours the contract the ladder already wrote."""
    try:
        if sig is None:
            return _accruing(family, "signal series missing")
        if bench is None:
            return _accruing(family, "bench missing")
        import pandas as pd
        by_h: dict = {}
        max_n = 0
        for h in horizons:
            bfwd = _bench_fwd_series(bench, h)
            if bfwd is None or bfwd.empty:
                continue
            j = pd.concat([sig.rename("s"), bfwd.rename("f")], axis=1).dropna()
            if len(j) < 8:
                continue
            # standardize signal so the product is a comparable predictive contribution
            s = (j["s"] - j["s"].mean()) / (j["s"].std(ddof=1) or 1.0)
            prod = (s * j["f"]).rename("sf")
            nw = V.newey_west_tstat(prod, lags=max(1, h - 1))
            n = nw.get("n", 0)
            max_n = max(max_n, n)
            mean = nw.get("mean")
            # the timer's own index IS its calendar — positions are just 0..len-1
            pos = list(range(len(j.index)))
            by_h[str(h)] = {"mean_ic": mean, "ic_ir": None,
                            "t_hac": nw.get("t"), "p_hac": nw.get("p"),
                            "hit": None, "n": n,
                            "n_weeks": _distinct_weeks(j.index),
                            "n_indep": _disjoint_windows(pos, h),
                            "hac_lags": max(1, h - 1)}
        if not by_h or max_n < 8:
            return _accruing(family, f"only {max_n} obs")
        return _finalize(family, by_h, max_n, _MIN_PROVEN_N_TS)
    except Exception as e:  # noqa: BLE001
        log.error("china_validation._validate_timer(%s) failed (%s)", family, e)
        return _accruing(family, "exception")


def _finalize(family, by_h, n_obs, min_proven) -> dict:
    """Pick the headline horizon (prefer 21d), compute PROVEN gate + computed tier.

    The PROMOTION gate is counted in independent evidence, not in rows. `n_obs` stays the raw
    scored-row count — china_signal_lab's wrong-sign DEMOTION path reads it, and demotion is
    deliberately the easier burden (a misleading leg should stay easy to zero) — but `proven`
    now requires `n_weeks >= min_proven` AND `n_indep >= _MIN_INDEP_WINDOWS` at the headline
    horizon. Both honest counts ride along in the family block so the row/evidence gap is
    legible wherever the scorecard is read."""
    sign_expected = _SIGN_EXPECTED.get(family)
    head = by_h.get("21") or next(iter(by_h.values()))
    t_hac = head.get("t_hac")
    mean_ic = head.get("mean_ic")
    n_weeks = int(head.get("n_weeks") or 0)
    n_indep = int(head.get("n_indep") or 0)
    sign_ok = (mean_ic is not None and sign_expected is not None
               and (mean_ic > 0) == (sign_expected > 0))
    enough = n_weeks >= min_proven and n_indep >= _MIN_INDEP_WINDOWS
    proven = bool(enough and t_hac is not None and abs(t_hac) >= 2.0 and sign_ok)
    tier = _tier_for(t_hac, head.get("p_hac"), n_obs, proven)
    status = "scored" if proven else ("validated" if tier == "confirmer" else "tested")
    out = {"family": family, "status": status, "tier": tier, "proven": proven,
           "n_obs": int(n_obs), "n_weeks": n_weeks, "n_indep": n_indep,
           "by_horizon": by_h, "sign_expected": sign_expected,
           "sign_ok": sign_ok, "t_hac": t_hac, "mean_ic": mean_ic,
           "is_context_only": True}
    if not enough:
        # say WHICH honest count is short — never let a blocked promotion read as a weak signal.
        # Quote the HEADLINE horizon's own row count (n_obs is a max across horizons, so pairing
        # it with headline-horizon weeks/windows would compare two different populations).
        out["n_gate"] = (f"{n_weeks}/{min_proven} distinct weeks, "
                         f"{n_indep}/{_MIN_INDEP_WINDOWS} non-overlapping windows "
                         f"(from {int(head.get('n') or 0)} overlapping rows)")
    return out


# --------------------------------------------------------------------------- #
# public API
# --------------------------------------------------------------------------- #
def validate_all(root=None, horizons=(5, 10, 21, 63)) -> dict:
    """Run every reconstructable China signal family through the forward-return gauntlet.

    Returns (and writes to data/china_validation/scorecard.json) the china_validation.v1
    scorecard: {schema, generated_utc, is_context_only, fdr_alpha, families:{name:{...}}}.
    Each family carries status/tier/proven + a by_horizon block of {mean_ic,t_hac,p_hac,hit,n}.
    Benjamini-Hochberg q across families' headline p_hac sets each family's q_fdr. A trial-ledger
    budget is logged so any downstream DSR is honestly counted. Degrades family-by-family to
    `accruing`; NEVER raises."""
    try:
        import engine.validation as V
    except Exception as e:  # noqa: BLE001
        log.error("china_validation: cannot import engine.validation (%s)", e)
        return {"schema": SCHEMA, "is_context_only": True, "families": {},
                "fdr_alpha": FDR_ALPHA, "error": "validation primitives unavailable"}

    panel = _panel()
    bench = _bench_close()

    families: dict = {}
    try:
        families["valuation"] = _validate_xs(V, "valuation", _valuation_cross_sections(),
                                             panel, bench, horizons)
    except Exception as e:  # noqa: BLE001
        log.error("china_validation valuation family failed (%s)", e)
        families["valuation"] = _accruing("valuation", "exception")
    # Tushare GATED cross-sectional legs (validate from the accruing/backfilled history; degrade to
    # `accruing` when the token / history is absent — e.g. keyless CI before the secret is set).
    try:
        families["fundflow"] = _validate_xs(V, "fundflow", _hist_cross_sections("flow_hist", "flow"),
                                            panel, bench, horizons)
    except Exception as e:  # noqa: BLE001
        log.error("china_validation fundflow family failed (%s)", e)
        families["fundflow"] = _accruing("fundflow", "exception")
    try:
        families["chips"] = _validate_xs(V, "chips", _hist_cross_sections("chips_hist", "winner"),
                                         panel, bench, horizons)
    except Exception as e:  # noqa: BLE001
        log.error("china_validation chips family failed (%s)", e)
        families["chips"] = _accruing("chips", "exception")
    try:                                          # 业绩预告 guidance surprise — cross-sections keyed by ann_date
        families["guidance"] = _validate_xs(V, "guidance",
                                            _hist_cross_sections("forecast_hist", "guidance_score", "ann_date"),
                                            panel, bench, horizons)
    except Exception as e:  # noqa: BLE001
        log.error("china_validation guidance family failed (%s)", e)
        families["guidance"] = _accruing("guidance", "exception")
    try:
        families["margin"] = _validate_timer(V, "margin", _margin_series(), panel, bench, horizons)
    except Exception as e:  # noqa: BLE001
        log.error("china_validation margin family failed (%s)", e)
        families["margin"] = _accruing("margin", "exception")
    try:
        families["news_sentiment"] = _validate_timer(
            V, "news_sentiment", _news_sentiment_series(), panel, bench, horizons)
    except Exception as e:  # noqa: BLE001
        log.error("china_validation news_sentiment family failed (%s)", e)
        families["news_sentiment"] = _accruing("news_sentiment", "exception")

    # FDR across families on the headline (21d, else first) p_hac
    try:
        pvals = {}
        for name, fam in families.items():
            by_h = fam.get("by_horizon") or {}
            head = by_h.get("21") or (next(iter(by_h.values())) if by_h else {})
            p = head.get("p_hac")
            if p is not None:
                pvals[name] = p
        bh = V.benjamini_hochberg(pvals, alpha=FDR_ALPHA) if pvals else {}
        for name, fam in families.items():
            q = (bh.get(name) or {}).get("q") if bh else None
            fam["q_fdr"] = q
            # re-gate PROVEN with the FDR q now available
            if fam.get("proven") and q is not None and q > FDR_ALPHA:
                fam["proven"] = False
                fam["status"] = "tested"
                fam["tier"] = _tier_for(fam.get("t_hac"), head.get("p_hac"),
                                        fam.get("n_obs", 0), False)
    except Exception as e:  # noqa: BLE001
        log.debug("china_validation FDR step failed (%s)", e)

    # honest multiple-testing budget (#families × #horizons cells)
    try:
        from engine.trial_ledger import TrialLedger
        led = TrialLedger()
        led.log_declared_budget(n=max(1, len(families) * len(horizons)),
                                family="china_validation",
                                reason="china signal × horizon predictive grid")
    except Exception as e:  # noqa: BLE001
        log.debug("china_validation trial-ledger budget skipped (%s)", e)

    out = {"schema": SCHEMA, "is_context_only": True,
           "generated_utc": datetime.now(timezone.utc).isoformat(),
           "fdr_alpha": FDR_ALPHA, "horizons": list(horizons), "families": families}
    try:
        p = config.data_dir() / "china_validation" / "scorecard.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(out, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        log.error("china_validation: could not write scorecard (%s)", e)
    return out


def load_scorecard() -> dict | None:
    """Read the last-written scorecard (for signal_lab / pages). None on miss. Never raises."""
    try:
        p = config.data_dir() / "china_validation" / "scorecard.json"
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
