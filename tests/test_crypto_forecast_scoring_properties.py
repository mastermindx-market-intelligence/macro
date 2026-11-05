"""Scoring properties for the T17 forecast-adjudication protocol.

Pins two facts against code that already exists:

* On a toy distribution whose empirical frequency is the true probability,
  the truthful constant report minimizes expected Brier and expected log
  score against three constant misreports. Brier comes from
  ``engine.grading_stats.brier_decomposition`` and
  ``engine.validation.brier_reliability``. Log score comes from
  ``engine.seasonality.calibration.log_score``.
* Those scorers drop non-finite pairs and report the finite count.
  Catalogue coverage keeps every issued slot, including abstentions.
  The catalogue arithmetic lives here because no crypto scorer implements
  it. The assertions are literals, not a second call to the same helper.

No network. No ``data/`` read. No new engine module.
"""
from __future__ import annotations

import math

import numpy as np

from engine.grading_stats import brier_decomposition
from engine.seasonality.calibration import log_score
from engine.validation import brier_reliability

# 60 ones and 40 zeros. The empirical frequency is the true probability 0.6,
# so a sample mean on this array equals the expectation.
_P_STAR = 0.6
_N_POS = 60
_N_NEG = 40
_Y = np.array([1.0] * _N_POS + [0.0] * _N_NEG)
_MISREPORTS = (0.2, 0.4, 0.9)


def _expected_brier(q: float) -> float:
    p = _P_STAR
    return (q - p) ** 2 + p * (1.0 - p)


def _expected_log(q: float) -> float:
    p = _P_STAR
    return -(p * math.log(q) + (1.0 - p) * math.log(1.0 - q))


def _constant(q: float) -> np.ndarray:
    return np.full(_Y.shape, q)


def catalogue_accounting(rows: list[dict]) -> dict:
    """All-catalogue coverage for one issued set.

    ``disposition`` is one of ``scored``, ``abstain``, ``unavailable``.
    The denominator is ``len(rows)``. An abstention is counted.
    """
    counts = {"scored": 0, "abstain": 0, "unavailable": 0}
    for row in rows:
        disposition = row["disposition"]
        if disposition not in counts:
            raise ValueError(f"unknown disposition {disposition!r}")
        counts[disposition] += 1
    n = len(rows)
    if sum(counts.values()) != n:
        raise AssertionError("dispositions do not partition the catalogue")

    def _rate(key: str) -> float | None:
        return None if n == 0 else counts[key] / n

    return {
        "n_catalogue": n,
        "n_scored": counts["scored"],
        "n_abstain": counts["abstain"],
        "n_unavailable": counts["unavailable"],
        "scored_share": _rate("scored"),
        "abstain_rate": _rate("abstain"),
        "unavailable_rate": _rate("unavailable"),
    }


def test_truthful_probability_minimizes_expected_brier_and_log_score() -> None:
    truthful_brier = brier_decomposition(_constant(_P_STAR), _Y)["brier_score"]
    truthful_reliability = brier_reliability(_constant(_P_STAR), _Y)["brier"]
    truthful_log = log_score(_constant(_P_STAR), _Y)

    assert truthful_log["abstained"] is False
    assert truthful_log["n"] == 100
    assert truthful_brier == round(_expected_brier(_P_STAR), 6)
    assert truthful_reliability == round(_expected_brier(_P_STAR), 4)
    assert truthful_log["log_score"] == round(_expected_log(_P_STAR), 6)
    assert len(_MISREPORTS) >= 3

    for q in _MISREPORTS:
        brier = brier_decomposition(_constant(q), _Y)["brier_score"]
        reliability = brier_reliability(_constant(q), _Y)["brier"]
        scored = log_score(_constant(q), _Y)
        assert brier == round(_expected_brier(q), 6)
        assert reliability == round(_expected_brier(q), 4)
        assert scored["abstained"] is False
        assert scored["log_score"] == round(_expected_log(q), 6)
        assert truthful_brier < brier
        assert truthful_reliability < reliability
        assert truthful_log["log_score"] < scored["log_score"]


def test_constant_truthful_forecast_has_zero_resolution_and_brier_equals_uncertainty() -> None:
    decomposed = brier_decomposition(_constant(_P_STAR), _Y, n_bins=10)
    uncertainty = _P_STAR * (1.0 - _P_STAR)
    assert decomposed["n"] == 100
    assert decomposed["base_rate"] == round(_P_STAR, 6)
    assert decomposed["uncertainty"] == round(uncertainty, 6)
    assert decomposed["reliability"] == 0.0
    assert decomposed["resolution"] == 0.0
    assert decomposed["brier_score"] == round(uncertainty, 6)


def test_short_sample_is_a_refusal_not_a_zero_score() -> None:
    p = [0.6] * 29
    y = [1.0] * 17 + [0.0] * 12
    assert brier_reliability(p, y) == {}
    refused = log_score(p, y)
    assert refused["abstained"] is True
    assert refused["value"] is None
    assert refused["reason"].startswith("log_score_unestimable:")
    assert "log_score" not in refused


def test_abstention_stays_in_the_catalogue_denominator() -> None:
    scored = [{"disposition": "scored"} for _ in range(100)]
    abstained = [{"disposition": "abstain"} for _ in range(20)]
    unavailable = [{"disposition": "unavailable"} for _ in range(10)]
    rows = scored + abstained + unavailable

    accounting = catalogue_accounting(rows)
    assert accounting["n_catalogue"] == 130
    assert accounting["n_scored"] == 100
    assert accounting["n_abstain"] == 20
    assert accounting["n_unavailable"] == 10
    assert accounting["scored_share"] == 100 / 130
    assert accounting["abstain_rate"] == 20 / 130
    assert accounting["unavailable_rate"] == 10 / 130

    dropped = [row for row in rows if row["disposition"] != "abstain"]
    assert len(dropped) == 110
    assert accounting["n_catalogue"] != len(dropped)
    assert accounting["scored_share"] != 100 / 110


def test_existing_scorers_drop_nonfinite_pairs_and_do_not_own_the_catalogue() -> None:
    """A zero filled in for a missing probability is a different score.

    The existing functions correctly ignore non-finite pairs. They will
    also score a literal zero if the caller supplies one. Catalogue
    coverage is the caller's job, and the finite-pair ``n`` is not it.
    """
    finite_p = _constant(_P_STAR)
    mixed_p = np.concatenate([finite_p, np.full(20, np.nan), np.full(10, _P_STAR)])
    mixed_y = np.concatenate([_Y, np.ones(20), np.full(10, np.nan)])

    on_finite = brier_reliability(finite_p, _Y)
    on_mixed = brier_reliability(mixed_p, mixed_y)
    assert on_finite["n"] == 100
    assert on_mixed["n"] == 100
    assert on_mixed["brier"] == on_finite["brier"]

    logged = log_score(mixed_p.tolist(), mixed_y.tolist())
    assert logged["abstained"] is False
    assert logged["n"] == 100
    assert logged["log_score"] == log_score(finite_p, _Y)["log_score"]

    zero_filled_p = np.concatenate([finite_p, np.zeros(20), np.full(10, 0.0)])
    zero_filled_y = np.concatenate([_Y, np.ones(20), np.zeros(10)])
    filled = brier_reliability(zero_filled_p, zero_filled_y)
    assert filled["n"] == 130
    assert filled["brier"] != on_mixed["brier"]
    assert filled["n"] != 100
