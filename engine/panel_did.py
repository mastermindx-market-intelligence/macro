"""Common-adoption balanced panel two-way fixed-effects DiD (research-only).

MO-DELTA-015/016 engineering component.  :func:`estimate_common_adoption_panel`
fits a descriptive two-way fixed-effects (unit and time)
difference-in-differences coefficient on a strictly balanced ``N x T`` panel in
which every treated unit adopts in one common period, treatment never reverses,
and the caller supplies the actual assignment/dependence clusters.

Authority and scope
-------------------
* ``research_only`` / ``descriptive_estimate``: no causal identification is
  claimed; parallel trends, no anticipation and no spillover are stated as
  NOT VERIFIED; no real-data study is performed or claimed by this module.
* Strict input gating: staggered adoption, unbalanced/ragged input, treatment
  reversals, already-treated-at-start designs, mixed-treatment assignment
  clusters, nonfinite or boolean outcomes, and duplicate/invalid identifiers
  are rejected with a typed abstention.  Nothing is silently dropped, padded
  or imputed.
* Inference is CR1 cluster-robust with a Student-t(G-1) reference distribution
  and is withheld (typed, never fabricated) when either arm has fewer than two
  clusters, or when the computed uncertainty sits at numerical roundoff level
  (exact/near-exact fit).

The JSON CLI (``python -m engine.panel_did``) reads one JSON request object
with the named API fields from stdin and writes one JSON response object to
stdout.  It touches no network and no files beyond the standard streams, and
exits non-zero whenever the study is rejected or the request is malformed, so a
rejected study never looks like a success.
"""

from __future__ import annotations

import json
import math
import sys
from datetime import date
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

try:  # scipy is an approved dependency; the guard only keeps failures typed.
    from scipy import stats as _scipy_stats
except Exception:  # pragma: no cover - scipy is expected to be present
    _scipy_stats = None

__all__ = ["estimate_common_adoption_panel", "main"]

STATUS_OK = "ok"
STATUS_REJECTED = "rejected"
STATUS_ERROR = "error"

INFERENCE_CR1 = "cluster_robust_cr1"
INFERENCE_INSUFFICIENT = "insufficient_clusters"
INFERENCE_DEGENERATE = "degenerate_variance"
INFERENCE_NO_SCIPY = "scipy_unavailable"

_SMALL_CLUSTER_THRESHOLD = 30
# A computed standard error within this multiple of the coefficient's own
# floating-point roundoff is treated as zero (exact/near-exact fit) rather
# than reported as spurious certainty.
_ROUNDOFF_SAFETY = 64.0

_REQUIRED_FIELDS = ("outcomes", "treatment", "unit_ids", "periods", "cluster_ids")
_OPTIONAL_FIELDS = ("design_id",)


# ---------------------------------------------------------------------------
# typed abstentions
# ---------------------------------------------------------------------------


def _abstain(
    reason_code: str, message: str, details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "status": STATUS_REJECTED,
        "authority": "research_only",
        "research_only": True,
        "reason_code": reason_code,
        "reason": message,
    }
    if details:
        payload["details"] = details
    return payload


def _short(value: Any, limit: int = 80) -> str:
    text = repr(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


# ---------------------------------------------------------------------------
# input validation helpers
# ---------------------------------------------------------------------------


def _to_matrix(
    raw: Any, field: str, *, allow_bool: bool, nonfinite_code: str
) -> Tuple[Optional[np.ndarray], Optional[Dict[str, Any]]]:
    """Coerce an array-like to a finite float64 2-D matrix, or abstain."""
    if raw is None or isinstance(raw, (str, bytes, bytearray, bool, int, float, complex)):
        return None, _abstain(
            "invalid_input",
            "%s must be a rectangular N x T array-like (list of equal-length numeric rows)" % field,
        )
    try:
        # Preserve heterogeneous input types before NumPy can coerce True to 1.0.
        if not allow_bool and any(isinstance(v, (bool, np.bool_))
                                  for v in np.asarray(raw, dtype=object).flat):
            return None, _abstain(
                "boolean_outcomes", "outcomes must not contain boolean values"
            )
        arr = np.asarray(raw)
    except (TypeError, ValueError) as exc:
        return None, _abstain(
            "invalid_input",
            "%s could not be read as a rectangular numeric matrix" % field,
            {"error": str(exc)},
        )
    if arr.ndim != 2:
        return None, _abstain(
            "invalid_shape",
            "%s must be 2-D (N units x T periods)" % field,
            {"ndim": int(arr.ndim)},
        )
    n_rows, n_cols = arr.shape
    if n_rows == 0 or n_cols == 0:
        return None, _abstain(
            "invalid_shape",
            "%s must have at least one row and one column" % field,
            {"shape": [int(n_rows), int(n_cols)]},
        )
    kind = arr.dtype.kind
    if kind == "b":
        if not allow_bool:
            return None, _abstain(
                "boolean_outcomes",
                "%s must hold numeric values; booleans are accepted for the treatment mask only" % field,
            )
        arr = arr.astype(np.float64)
    elif kind in ("i", "u", "f"):
        arr = arr.astype(np.float64)
    else:
        return None, _abstain(
            "non_numeric_entries",
            "%s must hold only real numbers" % field,
            {"dtype": str(arr.dtype)},
        )
    finite = np.isfinite(arr)
    if not bool(finite.all()):
        return None, _abstain(
            nonfinite_code,
            "%s must hold only finite values (NaN and infinities are rejected)" % field,
            {"nonfinite_count": int(np.count_nonzero(~finite))},
        )
    return arr, None


def _validate_label_list(
    raw: Any,
    field: str,
    *,
    unique: bool,
    length: Optional[int] = None,
) -> Tuple[Optional[List[str]], Optional[Dict[str, Any]]]:
    if not isinstance(raw, (list, tuple)):
        return None, _abstain("invalid_input", "%s must be a list of strings" % field)
    if length is not None and len(raw) != length:
        return None, _abstain(
            "length_mismatch",
            "%s must have exactly %d entries (one per unit)" % (field, length),
            {"observed": int(len(raw))},
        )
    labels: List[str] = []
    for i, item in enumerate(raw):
        if not isinstance(item, str) or not item.strip():
            return None, _abstain(
                "invalid_label",
                "%s[%d] must be a nonempty string" % (field, i),
                {"value": _short(item)},
            )
        labels.append(item)
    if unique and len(set(labels)) != len(labels):
        return None, _abstain(
            "duplicate_unit_ids", "%s must be unique; duplicates would silently merge units" % field
        )
    return labels, None


def _validate_periods(
    raw: Any,
) -> Tuple[Optional[List[str]], Optional[Dict[str, Any]]]:
    if not isinstance(raw, (list, tuple)) or len(raw) == 0:
        return None, _abstain(
            "invalid_periods", "periods must be a nonempty list of ISO YYYY-MM-DD date strings"
        )
    parsed: List[date] = []
    for i, item in enumerate(raw):
        if not isinstance(item, str):
            return None, _abstain(
                "invalid_periods",
                "periods[%d] must be an ISO YYYY-MM-DD date string" % i,
                {"value": _short(item)},
            )
        try:
            day = date.fromisoformat(item)
        except ValueError:
            return None, _abstain(
                "invalid_periods",
                "periods[%d] is not a valid calendar date" % i,
                {"value": item},
            )
        if day.isoformat() != item:
            return None, _abstain(
                "invalid_periods",
                "periods[%d] must use the canonical YYYY-MM-DD form" % i,
                {"value": item},
            )
        if parsed and day <= parsed[-1]:
            return None, _abstain(
                "invalid_periods",
                "periods must be strictly increasing and unique (no repeated or backward periods)",
                {"index": i, "value": item},
            )
        parsed.append(day)
    return list(raw), None


def _validate_treatment(
    d: np.ndarray, cluster_ids: Sequence[str]
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Validate the treatment mask; return design facts or a typed abstention."""
    n, t = d.shape
    is_zero_or_one = (d == 0.0) | (d == 1.0)
    if not bool(is_zero_or_one.all()):
        return None, _abstain(
            "invalid_treatment_values",
            "every treatment entry must be exactly 0 or 1",
            {"invalid_count": int(np.count_nonzero(~is_zero_or_one))},
        )
    treated_any = d.max(axis=1) >= 1.0
    treated_rows = np.flatnonzero(treated_any)
    control_rows = np.flatnonzero(~treated_any)
    if treated_rows.size == 0:
        return None, _abstain(
            "no_treated_units",
            "the design needs at least one treated unit; every unit is never treated",
        )
    if control_rows.size == 0:
        return None, _abstain(
            "no_control_units",
            "the design needs at least one never-treated control unit; every unit adopts",
        )
    first_one = np.argmax(d == 1.0, axis=1)
    for i in treated_rows.tolist():
        k = int(first_one[i])
        expected = np.concatenate(
            [np.zeros(k, dtype=np.float64), np.ones(t - k, dtype=np.float64)]
        )
        if not np.array_equal(d[i], expected):
            return None, _abstain(
                "invalid_treatment_path",
                (
                    "treated units must be 0 in every pre-adoption period and 1 in every "
                    "period from adoption onward; reversals, gaps and exits are not supported"
                ),
                {"unit_index": int(i), "first_treated_period_index": k},
            )
    adoptions = sorted({int(first_one[i]) for i in treated_rows.tolist()})
    if len(adoptions) != 1:
        return None, _abstain(
            "staggered_adoption",
            (
                "all treated units must first adopt in the same period; staggered adoption is "
                "not supported by this estimator (see research notes)"
            ),
            {"adoption_period_indices": adoptions},
        )
    adoption_index = adoptions[0]
    if adoption_index == 0:
        return None, _abstain(
            "no_pre_period",
            (
                "the common adoption period is the first period; at least one pre-adoption "
                "period is required"
            ),
        )

    unit_arm = ["treated" if bool(b) else "control" for b in treated_any]
    cluster_map: Dict[str, List[int]] = {}
    for idx, cid in enumerate(cluster_ids):
        cluster_map.setdefault(cid, []).append(idx)
    for cid in sorted(cluster_map):
        arms = {unit_arm[m] for m in cluster_map[cid]}
        if len(arms) > 1:
            return None, _abstain(
                "mixed_treatment_within_cluster",
                (
                    "assignment cluster %r mixes treated and control units; the caller-supplied "
                    "dependence cluster must be homogeneous in treatment status" % cid
                ),
                {"cluster_id": cid},
            )
    treated_cluster_ids = sorted({cluster_ids[i] for i in treated_rows.tolist()})
    control_cluster_ids = sorted({cluster_ids[i] for i in control_rows.tolist()})
    return (
        {
            "unit_arm": unit_arm,
            "cluster_map": cluster_map,
            "treated_rows": treated_rows,
            "control_rows": control_rows,
            "treated_cluster_ids": treated_cluster_ids,
            "control_cluster_ids": control_cluster_ids,
            "adoption_index": adoption_index,
        },
        None,
    )


def _limitations() -> List[str]:
    return [
        (
            "Research-only descriptive estimate; no causal identification is claimed and none "
            "is established by this routine."
        ),
        (
            "Parallel trends, no anticipation and no spillover are assumed and NOT VERIFIED; "
            "the coefficient is an average treatment effect on the treated only under "
            "assumptions this routine does not test."
        ),
        (
            "The design is limited to balanced panels with one common adoption period, "
            "absorbing treatment (no reversals), pure treated and pure control units, and at "
            "least one pre-period; staggered adoption, unbalanced panels and time-varying "
            "treatment are rejected, not handled."
        ),
        (
            "CR1 cluster-robust inference with few clusters is unreliable; the small-cluster "
            "warning is a flag, not a validated coverage guarantee."
        ),
        (
            "One specification is estimated per call; prior specification search and "
            "pre-specification are NOT VERIFIED or priced. No registration side effects "
            "or model selection are performed by this routine."
        ),
        (
            "This module performs no study of real data; any product empirical result would "
            "require an independently identified native panel and separate review."
        ),
    ]


def _assumptions() -> Dict[str, str]:
    return {
        "parallel_trends": "NOT VERIFIED",
        "no_anticipation": "NOT VERIFIED",
        "no_spillover": "NOT VERIFIED",
        "no_time_varying_confounders": "NOT VERIFIED",
        "cluster_ids_reflect_actual_dependence": "ASSUMED FROM CALLER INPUT (not verified)",
        "strictly_balanced_panel": "VERIFIED STRUCTURALLY (rejected otherwise)",
        "common_first_adoption": "VERIFIED STRUCTURALLY (rejected otherwise)",
    }


# ---------------------------------------------------------------------------
# estimator
# ---------------------------------------------------------------------------


def estimate_common_adoption_panel(
    outcomes: Any,
    treatment: Any,
    *,
    unit_ids: Sequence[str],
    periods: Sequence[str],
    cluster_ids: Sequence[str],
    design_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Estimate a common-adoption two-way fixed-effects DiD coefficient.

    Parameters
    ----------
    outcomes, treatment:
        ``N x T`` array-likes.  ``treatment`` entries must be exactly 0 or 1
        (booleans accepted); ``outcomes`` must be finite reals.
    unit_ids:
        N unique nonempty strings identifying units.
    periods:
        T unique, strictly increasing ISO ``YYYY-MM-DD`` date strings.
    cluster_ids:
        N nonempty strings giving each unit's actual assignment/dependence
        cluster; clusters may group several units and must be homogeneous in
        treatment status.
    design_id:
        Optional opaque label echoed back for provenance.

    Returns
    -------
    dict
        JSON-safe.  ``status == "ok"`` carries a descriptive point estimate
        (plus CR1 cluster-robust inference when supported); any other status is
        a typed abstention and carries ``reason_code``/``reason``.
    """
    if design_id is not None and (not isinstance(design_id, str) or not design_id.strip()):
        return _abstain("invalid_design_id", "design_id must be None or a nonempty string")

    y, err = _to_matrix(outcomes, "outcomes", allow_bool=False, nonfinite_code="nonfinite_outcomes")
    if err is not None:
        return err
    d, err = _to_matrix(treatment, "treatment", allow_bool=True, nonfinite_code="nonfinite_treatment")
    if err is not None:
        return err
    if y.shape != d.shape:
        return _abstain(
            "shape_mismatch",
            "outcomes and treatment must share the same N x T shape",
            {"outcomes_shape": [int(y.shape[0]), int(y.shape[1])],
             "treatment_shape": [int(d.shape[0]), int(d.shape[1])]},
        )
    n, t = y.shape

    unit_list, err = _validate_label_list(unit_ids, "unit_ids", unique=True, length=n)
    if err is not None:
        return err
    period_list, err = _validate_periods(periods)
    if err is not None:
        return err
    if len(period_list) != t:
        return _abstain(
            "length_mismatch",
            "periods must have exactly T=%d entries (one per column)" % t,
            {"observed": int(len(period_list))},
        )
    cluster_list, err = _validate_label_list(cluster_ids, "cluster_ids", unique=False, length=n)
    if err is not None:
        return err

    if n < 2:
        return _abstain("insufficient_units", "need at least one treated and one control unit", {"N": int(n)})
    if t < 2:
        return _abstain(
            "insufficient_timepoints", "need at least two timepoints for a DiD design", {"T": int(t)}
        )

    k_params = n + t  # intercept + (N-1) unit effects + (T-1) time effects + treatment
    n_obs = n * t
    residual_df = n_obs - k_params
    if residual_df <= 0:
        return _abstain(
            "insufficient_observations",
            "two-way fixed effects leave no positive residual degrees of freedom (NT - (N + T) must be > 0)",
            {"NT": int(n_obs), "K": int(k_params), "residual_df": int(residual_df)},
        )

    design, err = _validate_treatment(d, cluster_list)
    if err is not None:
        return err
    assert design is not None  # narrow Optional for type checkers

    adoption_index = design["adoption_index"]
    cluster_map: Dict[str, List[int]] = design["cluster_map"]
    unit_arm: List[str] = design["unit_arm"]

    # --- balanced two-way within transformation -----------------------------
    y_unit_mean = y.mean(axis=1, keepdims=True)
    y_time_mean = y.mean(axis=0, keepdims=True)
    y_grand_mean = float(y.mean())
    y_tilde = y - y_unit_mean - y_time_mean + y_grand_mean

    d_unit_mean = d.mean(axis=1, keepdims=True)
    d_time_mean = d.mean(axis=0, keepdims=True)
    d_grand_mean = float(d.mean())
    d_tilde = d - d_unit_mean - d_time_mean + d_grand_mean

    d_flat = d_tilde.ravel()
    y_flat = y_tilde.ravel()
    denom = float(np.dot(d_flat, d_flat))
    if not math.isfinite(denom) or denom <= 0.0:
        return _abstain(
            "unidentified_treatment",
            "the treatment indicator has no within (unit and time) variation after demeaning; "
            "the DiD coefficient is not identified",
        )
    numer = float(np.dot(d_flat, y_flat))
    beta = numer / denom
    if not math.isfinite(beta):
        return _abstain("unidentified_estimate", "the point estimate is not finite")
    residual = y_tilde - beta * d_tilde

    # --- CR1 cluster-robust variance ---------------------------------------
    score_grid = d_tilde * residual
    scores: Dict[str, float] = {}
    for cid in sorted(cluster_map):
        members = cluster_map[cid]
        scores[cid] = float(score_grid[np.asarray(members, dtype=int), :].sum())
    g = len(scores)
    # g >= 2 is guaranteed: pure treated and pure control clusters both exist.
    meat = float(sum(s * s for s in scores.values()))
    cr1_factor = (g / (g - 1.0)) * ((n_obs - 1.0) / (n_obs - k_params))
    variance = cr1_factor * meat / (denom * denom)

    treated_clusters = design["treated_cluster_ids"]
    control_clusters = design["control_cluster_ids"]

    warnings: List[str] = []
    estimate: Dict[str, Any] = {
        "coefficient": beta,
        "estimand": (
            "common-adoption two-way fixed-effects DiD coefficient on the treatment indicator "
            "(descriptive within estimate; an ATT only under assumptions that are NOT VERIFIED here)"
        ),
        "se": None,
        "ci95": None,
        "p_value": None,
        "p_value_status": "inference_unavailable",
        "t_statistic": None,
        "reference_distribution": None,
        "degrees_of_freedom": None,
        "inference_status": None,
        "inference_detail": None,
    }

    enough_clusters = len(treated_clusters) >= 2 and len(control_clusters) >= 2
    if not enough_clusters:
        estimate["inference_status"] = INFERENCE_INSUFFICIENT
        estimate["inference_detail"] = (
            "point estimate retained; cluster-robust uncertainty is not computed because "
            "reliable inference needs at least 2 treated and 2 control assignment clusters "
            "(observed: %d treated, %d control)" % (len(treated_clusters), len(control_clusters))
        )
        warnings.append(estimate["inference_detail"])
    else:
        se = math.sqrt(variance) if variance > 0.0 and math.isfinite(variance) else None
        # Roundoff floor: beta's own floating-point error is O(eps * sum|d*y| / denom).
        beta_roundoff = float(np.finfo(np.float64).eps) * float(np.abs(d_flat * y_flat).sum()) / denom
        if se is None:
            estimate["inference_status"] = INFERENCE_DEGENERATE
            estimate["inference_detail"] = (
                "point estimate retained; the computed cluster-robust variance is zero or "
                "non-finite (zero residual variation or numerical degeneracy), so no standard "
                "error, confidence interval or p-value is fabricated"
            )
            warnings.append(estimate["inference_detail"])
        elif se <= _ROUNDOFF_SAFETY * beta_roundoff:
            estimate["inference_status"] = INFERENCE_DEGENERATE
            estimate["inference_detail"] = (
                "point estimate retained; the fit is exact up to floating-point roundoff, so the "
                "computed uncertainty is at machine-precision level and no standard error, "
                "confidence interval or p-value is reported (no fabricated certainty)"
            )
            warnings.append(estimate["inference_detail"])
        elif _scipy_stats is None:
            estimate["inference_status"] = INFERENCE_NO_SCIPY
            estimate["inference_detail"] = (
                "point estimate retained; scipy is unavailable so the Student-t reference "
                "distribution cannot be evaluated and no p-value is fabricated"
            )
            warnings.append(estimate["inference_detail"])
        else:
            df = g - 1
            se = float(se)
            t_stat = beta / se
            crit = float(_scipy_stats.t.ppf(0.975, df))
            p_value = float(2.0 * _scipy_stats.t.sf(abs(t_stat), df))
            estimate["inference_status"] = INFERENCE_CR1
            estimate["inference_detail"] = (
                "CR1 cluster-robust standard error with Student-t(%d) reference distribution; "
                "scores aggregated over units and time within caller-supplied assignment clusters"
                % df
            )
            estimate["se"] = se
            estimate["ci95"] = [beta - crit * se, beta + crit * se]
            if p_value == 0.0:
                # A floating-point tail underflow is not an exact probability of zero.
                estimate["p_value_status"] = "numerical_underflow"
                estimate["inference_detail"] += (
                    "; the tail probability underflowed numerically, so p_value is unavailable"
                )
                warnings.append("p_value numerical underflow; do not report exact zero")
            elif math.isfinite(p_value) and 0.0 < p_value <= 1.0:
                estimate["p_value"] = p_value
                estimate["p_value_status"] = "available"
            else:
                estimate["p_value_status"] = "numerically_unavailable"
                warnings.append("p_value numerical evaluation unavailable")
            estimate["t_statistic"] = float(t_stat)
            estimate["reference_distribution"] = "student_t"
            estimate["degrees_of_freedom"] = int(df)
            if g < _SMALL_CLUSTER_THRESHOLD:
                msg = (
                    "small_cluster_warning: G = %d assignment clusters is below %d; cluster-robust "
                    "standard errors with few clusters are noisy and the t(G-1) reference "
                    "distribution may under-cover. This warning is not a validated coverage "
                    "statement." % (g, _SMALL_CLUSTER_THRESHOLD)
                )
                warnings.append(msg)

    cluster_listing = [
        {
            "cluster_id": cid,
            "arm": unit_arm[cluster_map[cid][0]],
            "unit_ids": [unit_list[i] for i in cluster_map[cid]],
        }
        for cid in sorted(cluster_map)
    ]

    result: Dict[str, Any] = {
        "status": STATUS_OK,
        "authority": "research_only",
        "research_only": True,
        "estimate_type": "descriptive_estimate",
        "design_id": design_id,
        "estimate": estimate,
        "design": {
            "N": int(n),
            "T": int(t),
            "NT": int(n_obs),
            "K": int(k_params),
            "K_description": "intercept + (N-1) unit effects + (T-1) time effects + treatment",
            "residual_df": int(residual_df),
            "balanced": True,
            "n_clusters": int(g),
            "treated_units": int(design["treated_rows"].size),
            "control_units": int(design["control_rows"].size),
            "treated_clusters": int(len(treated_clusters)),
            "control_clusters": int(len(control_clusters)),
            "adoption_period_index": int(adoption_index),
            "adoption_date": period_list[adoption_index],
            "pre_periods": int(adoption_index),
            "post_periods": int(t - adoption_index),
            "first_period": period_list[0],
            "last_period": period_list[-1],
            "clusters": cluster_listing,
        },
        "method": {
            "name": "common_adoption_twfe_within",
            "estimator": (
                "balanced two-way (unit and time) fixed-effects within estimator; algebraically "
                "identical to OLS of outcomes on an intercept, unit dummies, time dummies and one "
                "treatment indicator"
            ),
            "within_transformation": (
                "y_tilde = y - unit_mean - time_mean + grand_mean; d_tilde analog; "
                "beta = <d_tilde, y_tilde> / <d_tilde, d_tilde>"
            ),
            "variance": (
                "CR1 cluster-robust sandwich: (G/(G-1)) * ((NT-1)/(NT-K)) * sum_g score_g^2 / "
                "<d_tilde, d_tilde>^2 with score_g = sum of d_tilde * within-residual over units "
                "and time in cluster g"
            ),
            "cluster_variable": (
                "caller-supplied cluster_ids (the actual assignment/dependence unit, not inferred)"
            ),
            "specification_search": "one call only; caller selection history NOT VERIFIED or priced",
        },
        "assumptions": _assumptions(),
        "warnings": warnings,
        "limitations": _limitations(),
    }
    return result


# ---------------------------------------------------------------------------
# JSON CLI
# ---------------------------------------------------------------------------


def _cli_error(
    reason_code: str, message: str, details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "status": STATUS_ERROR,
        "authority": "research_only",
        "research_only": True,
        "reason_code": reason_code,
        "reason": message,
    }
    if details:
        payload["details"] = details
    return payload


def _emit(payload: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, allow_nan=False, sort_keys=True, indent=2) + "\n")


def main() -> int:
    """Read one JSON request from stdin, emit one JSON response, return exit code.

    Exit codes: 0 = estimate produced; 1 = study rejected (typed abstention);
    2 = malformed request or non-serialisable result.
    """
    raw = sys.stdin.read()
    try:
        request = json.loads(raw)
    except ValueError as exc:
        _emit(_cli_error("invalid_json", "stdin is not valid JSON", {"error": str(exc)}))
        return 2
    if not isinstance(request, dict):
        _emit(_cli_error("invalid_request", "request must be a JSON object with named API fields"))
        return 2
    unknown = sorted(set(request) - set(_REQUIRED_FIELDS) - set(_OPTIONAL_FIELDS))
    if unknown:
        _emit(_cli_error("unknown_field", "request contains unknown fields", {"unknown": unknown}))
        return 2
    missing = [field for field in _REQUIRED_FIELDS if field not in request]
    if missing:
        _emit(_cli_error("missing_field", "request is missing required fields", {"missing": missing}))
        return 2
    try:
        result = estimate_common_adoption_panel(
            request["outcomes"],
            request["treatment"],
            unit_ids=request["unit_ids"],
            periods=request["periods"],
            cluster_ids=request["cluster_ids"],
            design_id=request.get("design_id"),
        )
    except Exception as exc:  # defensive: a rejected run must never look like success
        _emit(
            _cli_error(
                "internal_error",
                "estimation raised an unexpected exception",
                {"error": "%s: %s" % (type(exc).__name__, exc)},
            )
        )
        return 2
    try:
        _emit(result)
    except (TypeError, ValueError) as exc:
        _emit(_cli_error("non_json_safe_result", "result could not be serialised", {"error": str(exc)}))
        return 2
    return 0 if result.get("status") == STATUS_OK else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
