"""Synthetic fixtures for the W3 post-floor statistical guardrail reader.

Temporary trees only. Does not read production paired/candidate/grade outcomes.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engine import us_prophet_w3 as w3
from engine.validation import newey_west_tstat, rank_ic
from scripts.report_us_prophet_w3_guardrail import (
    ACCRUAL_FORBIDDEN_TOKENS,
    MIN_NAMES,
    PRIMARY_LABEL_NONCONFIRMATORY,
    GuardrailReadError,
    hac_t_interval,
    main as guardrail_main,
    read_w3_guardrail,
    top_n_inclusive_ties,
)


def _receipt() -> dict:
    return {
        "schema": w3.STRUCTURAL_SCHEMA,
        "canonical_observation": True,
        "admitted_frozen": ["alpha"],
        "full_model_rank_matches_published": True,
        "families_present": ["F2_MOMENTUM_EXTENSION"],
        "families_absent": [{"family": "F4_POSITIONING", "reason": "no surviving member"}],
        "lofo": [{
            "family": "F2_MOMENTUM_EXTENSION",
            "rows_carrying": 12,
            "distinct_values": 8,
            "modal_value": 0.5,
            "modal_share": 0.25,
            "dispersion": 0.11,
            "mean_abs_rank_displacement": 1.5,
            "max_abs_rank_displacement": 4,
            "rows_moved": 6,
            "top30_churn": 2,
        }],
        "census": [{
            "member": "alpha",
            "family": "F2_MOMENTUM_EXTENSION",
            "status": "voting",
            "coverage": 1.0,
            "distinct_values": 8,
            "variation_share": 1.0,
            "thresholds": {
                "presence_floor": 0.80,
                "min_distinct_values": 2,
                "min_variation_share": 0.50,
            },
            "reason": "admitted and not collapsed",
            "source": "board.alpha",
            "staleness_basis": None,
        }],
    }


def _cand(stamp: str, ticker: str, score_rank: int, shadow_rank: int,
          score: float = 40.0, shadow_score: float = 30.0) -> dict:
    return {
        "stamp_date": stamp,
        "ticker": ticker,
        "board_definition": w3.CANONICAL_BOARD,
        "selection_era": "anticipation-v1",
        "anchor_era": "abs-session-2026-08-06",
        "stage": "live",
        "lane": "buy",
        "prophet_score": score,
        "score_rank": score_rank,
        "prophet_shadow_definition": w3.SHADOW_DEFINITION,
        "prophet_shadow_score": shadow_score,
        "prophet_shadow_score_rank": shadow_rank,
    }


def _grade(stamp: str, ticker: str, excess: float) -> dict:
    return {
        "stamp_date": stamp,
        "ticker": ticker,
        "board_definition": w3.CANONICAL_BOARD,
        "horizon": 10,
        "excess_spy": excess,
        "fill_date": "2026-09-02",
        "mark_date": "2026-09-16",
        "graded_asof": "2026-09-16",
        "bench": "SPY",
    }


def _aligned_names(stamp: str, n: int = 4, *, c1_good: bool = True,
                   shadow_good: bool = False, tie_cutoff: bool = False):
    """Monotone excess vs rank. c1_good=True → rank 1 has the highest excess."""
    if tie_cutoff:
        n = max(n, 32)
    excess = [0.01 * (n - i) for i in range(n)]
    cands = []
    grades = []
    for i in range(n):
        ticker = f"T{i:02d}"
        c1_rank = (i + 1) if c1_good else (n - i)
        shadow_rank = (i + 1) if shadow_good else (n - i)
        if tie_cutoff and c1_good and i in (29, 30):
            c1_rank = 30
        if tie_cutoff and not shadow_good and i in (1, 2):
            # two names share shadow cutoff when shadow is inverted
            shadow_rank = 30 if i == 1 else 31
            if i == 2:
                shadow_rank = 30
        cands.append(_cand(stamp, ticker, c1_rank, shadow_rank,
                           score=50.0 - c1_rank, shadow_score=50.0 - shadow_rank))
        grades.append(_grade(stamp, ticker, excess[i]))
    return cands, grades


def _stamps(n: int = 20) -> list[str]:
    return [f"2026-09-{i:02d}" for i in range(1, n + 1)]


def _append_session(root: Path, rec: dict) -> None:
    path = w3.sessions_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(rec, sort_keys=True, default=str) + "\n")


def _write_stamp(root: Path, stamp: str, cands: list[dict], grades: list[dict],
                 *, liveness: str | None = None,
                 session_overrides: dict | None = None) -> dict:
    rows, _ = w3.build_paired_rows(pd.DataFrame(cands), pd.DataFrame(grades))
    receipt = _receipt()
    family = w3.family_rows_from_receipt(stamp, receipt)
    coverage = w3.coverage_rows_from_receipt(stamp, receipt)
    w3._commit_stamp_grains(stamp, {
        "paired": pd.DataFrame(rows),
        "family": pd.DataFrame(family),
        "coverage": pd.DataFrame(coverage),
    }, root)
    fps = w3.observation_fingerprints(root, stamp)
    rec = {
        "schema": w3.SCHEMA_SESSION,
        "stamp_date": stamp,
        "liveness": liveness or w3.LIVENESS_PAIRED_ACCRUED,
        "n_v3_buy_rows": len(rows),
        "n_paired": len(rows),
        "n_pending_outcome": 0 if liveness != w3.LIVENESS_UNMATURED else len(rows),
        "structural_schema": w3.STRUCTURAL_SCHEMA,
        "source": "frozen_w3_parts",
        "reason": "synthetic fixture",
        **fps,
    }
    if session_overrides:
        rec.update(session_overrides)
    _append_session(root, rec)
    return rec


def _write_floor(root: Path, n: int = 20, **kwargs) -> list[str]:
    stamps = _stamps(n)
    for stamp in stamps:
        cands, grades = _aligned_names(stamp, **kwargs)
        _write_stamp(root, stamp, cands, grades)
    return stamps


def _boom(*_a, **_k):
    raise AssertionError("forbidden loader/writer called")


def _forbid_global_loaders(monkeypatch) -> None:
    monkeypatch.setattr(w3, "load_paired", _boom)
    monkeypatch.setattr(w3, "load_family", _boom)
    monkeypatch.setattr(w3, "load_coverage", _boom)
    monkeypatch.setattr(w3.upg, "load_grades", _boom)
    monkeypatch.setattr(w3.ucv, "load_candidates", _boom)


def _forbid_pre_floor(monkeypatch) -> None:
    _forbid_global_loaders(monkeypatch)
    monkeypatch.setattr(w3, "load_paired_stamp", _boom)
    monkeypatch.setattr(w3, "observation_fingerprints", _boom)
    monkeypatch.setattr(w3, "stamp_observation_complete", _boom)
    monkeypatch.setattr(w3, "qualify_paired_candidates", _boom)
    monkeypatch.setattr(w3, "build_paired_rows", _boom)
    monkeypatch.setattr("scripts.report_us_prophet_w3_guardrail.rank_ic", _boom)
    monkeypatch.setattr("scripts.report_us_prophet_w3_guardrail.newey_west_tstat", _boom)


def _forbid_writers(monkeypatch) -> None:
    monkeypatch.setattr(w3, "write_status", _boom)
    monkeypatch.setattr(w3, "append_sessions", _boom)
    monkeypatch.setattr(w3, "append_paired", _boom)
    monkeypatch.setattr(w3, "append_family", _boom)
    monkeypatch.setattr(w3, "append_coverage", _boom)
    monkeypatch.setattr(w3, "accrue", _boom)


def _assert_no_stats(payload: dict) -> None:
    inspected = {key: value for key, value in payload.items() if key != "refusal"}
    dumped = json.dumps(inspected)
    for token in ACCRUAL_FORBIDDEN_TOKENS:
        assert token.lower() not in dumped.lower(), token
    assert payload["authority"] is False
    assert payload["c2_trigger"] is False
    assert payload["automatic_reversion"] is False
    assert payload["promotion"] is False
    assert payload["agentos_write"] is False
    assert payload.get("investigation_open") is False
    assert "primary" not in payload
    assert "secondary" not in payload
    assert "per_stamp" not in payload


# --------------------------------------------------------------------------- #
# floor / loaders
# --------------------------------------------------------------------------- #

class TestPreFloorAccrualOnly:

    def test_below_floor_is_accrual_only_and_loaders_untouched(
            self, tmp_path, monkeypatch):
        _write_floor(tmp_path, n=19)
        _forbid_pre_floor(monkeypatch)
        _forbid_writers(monkeypatch)
        payload = read_w3_guardrail(tmp_path)
        assert payload["status"] == "FLOOR_UNMET"
        assert payload["accrual"]["n_selected_sessions"] == 19
        assert "PENDING" in payload["first_lawful_comparison_read"]
        _assert_no_stats(payload)

    def test_unmatured_and_terminal_do_not_count(self, tmp_path, monkeypatch):
        stamps = _stamps(19)
        for stamp in stamps:
            cands, grades = _aligned_names(stamp)
            _write_stamp(tmp_path, stamp, cands, grades)
        cands, grades = _aligned_names("2026-08-01")
        _write_stamp(tmp_path, "2026-08-01", cands, grades,
                     liveness=w3.LIVENESS_UNMATURED,
                     session_overrides={"n_pending_outcome": 4})
        cands, grades = _aligned_names("2026-08-02")
        _write_stamp(tmp_path, "2026-08-02", cands, grades,
                     liveness=w3.LIVENESS_DEGRADED,
                     session_overrides={"n_paired": 0, "n_v3_buy_rows": 0,
                                        "n_pending_outcome": 0})
        _forbid_pre_floor(monkeypatch)
        payload = read_w3_guardrail(tmp_path)
        assert payload["status"] == "FLOOR_UNMET"
        assert payload["accrual"]["n_selected_sessions"] == 19
        _assert_no_stats(payload)

    def test_keep_first_does_not_count_retries_as_two_sessions(
            self, tmp_path, monkeypatch):
        stamps = _write_floor(tmp_path, n=19)
        rec = json.loads(w3.sessions_path(tmp_path).read_text(encoding="utf-8").splitlines()[0])
        rec["n_paired"] = 99
        _append_session(tmp_path, rec)
        by = w3.sessions_by_stamp(tmp_path)
        assert by[stamps[0]]["n_paired"] != 99
        _forbid_pre_floor(monkeypatch)
        payload = read_w3_guardrail(tmp_path)
        assert payload["accrual"]["n_selected_sessions"] == 19
        assert payload["status"] == "FLOOR_UNMET"


# --------------------------------------------------------------------------- #
# tamper / incomplete → whole refuse
# --------------------------------------------------------------------------- #

class TestWholeRefuse:

    def test_duplicate_claimed_stamp_keep_first_still_reads_floor(
            self, tmp_path, monkeypatch):
        stamps = _write_floor(tmp_path, n=20, c1_good=False, shadow_good=True)
        rec = json.loads(w3.sessions_path(tmp_path).read_text(encoding="utf-8").splitlines()[-1])
        rec["n_paired"] = 1
        _append_session(tmp_path, rec)
        _forbid_global_loaders(monkeypatch)
        _forbid_writers(monkeypatch)
        payload = read_w3_guardrail(tmp_path)
        assert payload["status"] == "READ"
        assert payload["accrual"]["n_selected_sessions"] == 20
        assert stamps[-1] in payload["accrual"]["selected_stamps"]

    def test_session_schema_tamper_among_claimed_refuses(self, tmp_path, monkeypatch):
        _write_floor(tmp_path, n=20)
        cands, grades = _aligned_names("2026-08-15")
        _write_stamp(tmp_path, "2026-08-15", cands, grades,
                     session_overrides={"schema": "not-a-session"})
        _forbid_global_loaders(monkeypatch)
        payload = read_w3_guardrail(tmp_path)
        assert payload["status"] == "REFUSED"
        _assert_no_stats(payload)

    def test_session_fingerprint_mismatch_refuses(self, tmp_path, monkeypatch):
        stamps = _write_floor(tmp_path, n=20)
        lines = w3.sessions_path(tmp_path).read_text(encoding="utf-8").splitlines()
        rec = json.loads(lines[-1])
        rec["observation_fingerprint"] = "0" * 64
        lines[-1] = json.dumps(rec, sort_keys=True)
        w3.sessions_path(tmp_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
        _forbid_global_loaders(monkeypatch)
        payload = read_w3_guardrail(tmp_path)
        assert payload["status"] == "REFUSED"
        assert stamps[-1] in payload.get("refusal", "") or "fingerprint" in payload["refusal"]
        _assert_no_stats(payload)

    def test_incomplete_stamp_does_not_drop_survivors(self, tmp_path, monkeypatch):
        stamps = _write_floor(tmp_path, n=20)
        w3._part_path("coverage", stamps[-1], tmp_path).unlink()
        _forbid_global_loaders(monkeypatch)
        payload = read_w3_guardrail(tmp_path)
        assert payload["status"] == "REFUSED"
        assert "complete observation" in payload["refusal"]
        _assert_no_stats(payload)

    def test_key_tamper_refuses(self, tmp_path, monkeypatch):
        stamps = _write_floor(tmp_path, n=20)
        path = w3._part_path("paired", stamps[0], tmp_path)
        frame = pd.read_parquet(path)
        frame.loc[frame.index[1], "ticker"] = frame.iloc[0]["ticker"]
        frame.to_parquet(path, index=False)
        _forbid_global_loaders(monkeypatch)
        payload = read_w3_guardrail(tmp_path)
        assert payload["status"] == "REFUSED"
        _assert_no_stats(payload)

    def test_source_tamper_refuses(self, tmp_path, monkeypatch):
        stamps = _write_floor(tmp_path, n=20)
        path = w3._part_path("paired", stamps[0], tmp_path)
        frame = pd.read_parquet(path)
        frame["source"] = "pages"
        frame.to_parquet(path, index=False)
        _forbid_global_loaders(monkeypatch)
        payload = read_w3_guardrail(tmp_path)
        assert payload["status"] == "REFUSED"
        _assert_no_stats(payload)

    def test_board_tamper_refuses(self, tmp_path, monkeypatch):
        stamps = _write_floor(tmp_path, n=20)
        path = w3._part_path("paired", stamps[0], tmp_path)
        frame = pd.read_parquet(path)
        frame["board_definition"] = w3.FALLBACK_DEFINITION
        frame.to_parquet(path, index=False)
        _forbid_global_loaders(monkeypatch)
        payload = read_w3_guardrail(tmp_path)
        assert payload["status"] == "REFUSED"
        _assert_no_stats(payload)

    def test_horizon_tamper_refuses(self, tmp_path, monkeypatch):
        stamps = _write_floor(tmp_path, n=20)
        path = w3._part_path("paired", stamps[0], tmp_path)
        frame = pd.read_parquet(path)
        frame["horizon"] = 21
        frame.to_parquet(path, index=False)
        _forbid_global_loaders(monkeypatch)
        payload = read_w3_guardrail(tmp_path)
        assert payload["status"] == "REFUSED"
        _assert_no_stats(payload)

    def test_outcome_tamper_refuses(self, tmp_path, monkeypatch):
        stamps = _write_floor(tmp_path, n=20)
        path = w3._part_path("paired", stamps[0], tmp_path)
        frame = pd.read_parquet(path)
        frame.loc[frame.index[0], "excess_spy"] = np.nan
        frame.to_parquet(path, index=False)
        _forbid_global_loaders(monkeypatch)
        payload = read_w3_guardrail(tmp_path)
        assert payload["status"] == "REFUSED"
        _assert_no_stats(payload)

    def test_undefined_ic_whole_refuses(self, tmp_path, monkeypatch):
        stamps = _stamps(20)
        for i, stamp in enumerate(stamps):
            if i == 0:
                cands = [_cand(stamp, "AAA", 1, 2), _cand(stamp, "BBB", 2, 1)]
                grades = [_grade(stamp, "AAA", 0.05), _grade(stamp, "BBB", 0.05)]
            else:
                cands, grades = _aligned_names(stamp)
            _write_stamp(tmp_path, stamp, cands, grades)
        _forbid_global_loaders(monkeypatch)
        payload = read_w3_guardrail(tmp_path)
        assert payload["status"] == "REFUSED"
        assert "undefined rank-IC" in payload["refusal"]
        _assert_no_stats(payload)

    def test_hac_undefined_from_interval_returns_refused_not_uncaught(
            self, tmp_path, monkeypatch):
        """Lexical accrual scan must not re-raise on free-text refusal diagnostics."""
        _write_floor(tmp_path, n=20, c1_good=True, shadow_good=False)
        _forbid_global_loaders(monkeypatch)
        _forbid_writers(monkeypatch)

        def _raise_hac(*_a, **_k):
            raise GuardrailReadError("HAC estimator undefined on the ΔIC series")

        monkeypatch.setattr(
            "scripts.report_us_prophet_w3_guardrail.hac_t_interval", _raise_hac)
        payload = read_w3_guardrail(tmp_path)
        assert payload["status"] == "REFUSED"
        assert payload["refusal"] == "HAC estimator undefined on the ΔIC series"
        assert "primary" not in payload
        assert "secondary" not in payload
        assert "per_stamp" not in payload
        assert payload.get("investigation_open") is False
        assert payload.get("investigation_label") is None
        _assert_no_stats(payload)


# --------------------------------------------------------------------------- #
# math: rank sign, min_names, top30, HAC, t-CI, secondary
# --------------------------------------------------------------------------- #

class TestRankAndMinNames:

    def test_rank_sign_positive_when_better_rank_has_higher_excess(self):
        ranks = pd.Series([1, 2, 3, 4])
        excess = pd.Series([0.04, 0.03, 0.02, 0.01])
        ic = rank_ic(-ranks, excess, min_names=MIN_NAMES)
        assert ic == pytest.approx(1.0)
        ic_bad = rank_ic(-ranks, -excess, min_names=MIN_NAMES)
        assert ic_bad == pytest.approx(-1.0)

    def test_two_name_reader_min_and_default_min10(self):
        assert np.isnan(rank_ic(pd.Series([1, 2]), pd.Series([2, 1])))
        assert rank_ic(pd.Series([1, 2]), pd.Series([1, 2]), min_names=2) == pytest.approx(1.0)
        ten = pd.Series(range(10))
        assert np.isfinite(rank_ic(ten, ten))

    def test_reader_two_name_stamps_meet_floor(self, tmp_path, monkeypatch):
        for stamp in _stamps(20):
            cands = [_cand(stamp, "AAA", 1, 2), _cand(stamp, "BBB", 2, 1)]
            grades = [_grade(stamp, "AAA", 0.05), _grade(stamp, "BBB", -0.01)]
            _write_stamp(tmp_path, stamp, cands, grades)
        _forbid_global_loaders(monkeypatch)
        payload = read_w3_guardrail(tmp_path)
        assert payload["status"] == "READ"
        assert payload["primary"]["min_names"] == 2
        assert payload["per_stamp"][0]["ic_c1"] == pytest.approx(1.0)
        assert payload["per_stamp"][0]["ic_shadow"] == pytest.approx(-1.0)


class TestTop30Ties:

    def test_cutoff_ties_are_included_and_n_reported(self):
        ranks = list(range(1, 30)) + [30, 30, 32]
        excess = list(range(32, 0, -1))
        frame = pd.DataFrame({
            "score_rank": ranks,
            "excess_spy": excess,
            "prophet_shadow_score_rank": ranks,
        })
        selected, n = top_n_inclusive_ties(frame, "score_rank", 30)
        assert n == 31
        assert len(selected) == 31
        assert set(selected["score_rank"]) <= set(range(1, 31))

    def test_reader_reports_actual_n_with_ties(self, tmp_path, monkeypatch):
        for stamp in _stamps(20):
            cands, grades = _aligned_names(stamp, tie_cutoff=True, c1_good=True,
                                           shadow_good=False)
            _write_stamp(tmp_path, stamp, cands, grades)
        _forbid_global_loaders(monkeypatch)
        payload = read_w3_guardrail(tmp_path)
        assert payload["status"] == "READ"
        n_c1 = payload["secondary"]["by_stamp"][0]["c1_n"]
        assert n_c1 == 31


class TestHacAndStudentT:

    def test_independent_lag9_matches_unrounded_estimator(self):
        x = np.array([
            0.02, 0.018, 0.015, 0.019, 0.011, 0.014, 0.016, 0.012, 0.017, 0.013,
            0.015, 0.018, 0.014, 0.016, 0.012, 0.019, 0.011, 0.015, 0.017, 0.013,
        ], dtype=float)
        n = len(x)
        mean = float(x.mean())
        d = x - mean
        var = float(np.dot(d, d) / n)
        lags = 9
        for j in range(1, lags + 1):
            gj = float(np.dot(d[j:], d[:-j]) / n)
            var += 2.0 * (1.0 - j / (lags + 1)) * gj
        se = math.sqrt(max(var, 1e-18) / n)
        t = mean / se
        got = newey_west_tstat(x, lags=9, unrounded=True)
        assert got["lags"] == 9
        assert got["mean"] == pytest.approx(mean, rel=0, abs=0)
        assert got["se"] == pytest.approx(se, rel=0, abs=0)
        assert got["t"] == pytest.approx(t, rel=0, abs=0)
        interval = hac_t_interval(x, lags=9)
        assert interval["hac_lags"] == 9
        assert interval["mean"] == pytest.approx(mean)
        assert interval["se"] == pytest.approx(se)

    def test_student_t_ci_just_below_equal_above_zero(self):
        lo = hac_t_interval([-0.05] * 20)
        hi = hac_t_interval([0.05] * 20)
        assert lo["ci95_hi"] < 0
        assert lo["tripwire_upper95ci_lt_0"] is True
        assert hi["ci95_hi"] > 0
        assert hi["tripwire_upper95ci_lt_0"] is False
        # Shift a zero series so the upper bound lands on 0; tripwire is strict.
        zero = hac_t_interval([0.0] * 20)
        equal = [0.0 - zero["ci95_hi"]] * 20
        eq = hac_t_interval(equal)
        if eq["ci95_hi"] < 0:
            equal = [v + abs(eq["ci95_hi"]) for v in equal]
            eq = hac_t_interval(equal)
        assert eq["ci95_hi"] == pytest.approx(0.0, abs=1e-15)
        assert eq["ci95_hi"] >= 0 or eq["ci95_hi"] == pytest.approx(0.0, abs=1e-18)
        assert eq["tripwire_upper95ci_lt_0"] is False

    def test_normal_p_never_controls_primary(self):
        from scipy.stats import t as student_t, norm
        rng = np.random.default_rng(7)
        noise = rng.normal(0, 1, size=20)
        noise = noise - noise.mean()
        se = newey_west_tstat(noise, lags=9, unrounded=True)["se"]
        target_t = -2.00
        series = noise + (target_t * se)
        out = hac_t_interval(series, lags=9)
        crit = float(student_t.ppf(0.975, 19))
        p_norm = 2.0 * (1.0 - float(norm.cdf(abs(out["t"]))))
        assert abs(out["t"]) < crit
        assert p_norm < 0.05
        assert out["tripwire_upper95ci_lt_0"] is False
        assert out["p_normal_diagnostic"] == pytest.approx(p_norm, rel=1e-9)


class TestPrimarySecondary:

    def test_primary_fire_secondary_not_confirmatory(self, tmp_path, monkeypatch):
        _write_floor(tmp_path, n=20, c1_good=False, shadow_good=True)
        _forbid_global_loaders(monkeypatch)
        payload = read_w3_guardrail(tmp_path)
        assert payload["status"] == "READ"
        assert payload["primary"]["tripwire_upper95ci_lt_0"] is True
        assert payload["investigation_open"] is True
        assert payload["investigation_label"] == PRIMARY_LABEL_NONCONFIRMATORY
        assert payload["secondary"]["or_trigger"] is False
        assert payload["secondary"]["cancels_primary"] is False
        assert payload["authority"] is False
        assert payload["c2_trigger"] is False

    def test_secondary_adverse_cannot_open_investigation(self, tmp_path, monkeypatch):
        _write_floor(tmp_path, n=20, c1_good=True, shadow_good=False)
        _forbid_global_loaders(monkeypatch)
        payload = read_w3_guardrail(tmp_path)
        assert payload["status"] == "READ"
        assert payload["primary"]["tripwire_upper95ci_lt_0"] is False
        assert payload["investigation_open"] is False
        assert payload["investigation_label"] is None
        assert payload["p_normal_controls_primary"] is False


class TestCaptureOwnerExactness:
    """The persisted paired output is the registered capture owner.

    No reconstruction / requalification / row-constructor rebuild, exact
    canonical source, exact persisted benchmark, and a grain fingerprint that
    must match BOTH the observation record and the session record.
    """

    def test_lawful_read_never_requalifies_or_rebuilds(self, tmp_path, monkeypatch):
        _write_floor(tmp_path, n=20, c1_good=True, shadow_good=False)
        monkeypatch.setattr(w3, "qualify_paired_candidates", _boom)
        monkeypatch.setattr(w3, "build_paired_rows", _boom)
        _forbid_global_loaders(monkeypatch)
        _forbid_writers(monkeypatch)
        payload = read_w3_guardrail(tmp_path)
        assert payload["status"] == "READ"
        assert payload["accrual"]["n_selected_sessions"] == 20

    @pytest.mark.parametrize("mode", ["missing", "empty", "null"])
    def test_source_must_be_exactly_canonical(self, tmp_path, monkeypatch, mode):
        stamps = _write_floor(tmp_path, n=20)
        path = w3._part_path("paired", stamps[0], tmp_path)
        frame = pd.read_parquet(path)
        if mode == "missing":
            frame = frame.drop(columns=["source"])
        elif mode == "empty":
            frame["source"] = ""
        else:
            frame["source"] = None
        frame.to_parquet(path, index=False)
        _forbid_global_loaders(monkeypatch)
        payload = read_w3_guardrail(tmp_path)
        assert payload["status"] == "REFUSED"
        assert "paired source" in payload["refusal"]
        _assert_no_stats(payload)

    def test_legacy_bench_fallback_cannot_pass_internally_valid_fingerprints(
            self, tmp_path, monkeypatch):
        stamps = _write_floor(tmp_path, n=20, c1_good=True, shadow_good=False)
        path = w3._part_path("paired", stamps[0], tmp_path)
        tampered = pd.read_parquet(path).copy()
        tampered["benchmark"] = None
        tampered["bench"] = "SPY"
        rows = tampered.to_dict(orient="records")
        for row in rows:
            row["identity_fingerprint"] = w3.fingerprint(row, w3.PAIRED_IDENTITY)
        tampered = pd.DataFrame(rows).reset_index(drop=True)

        real_load = w3.load_paired_stamp

        def _swap(root, stamp):
            frame = real_load(root, stamp)
            if str(stamp)[:10] == stamps[0]:
                return tampered.copy()
            return frame

        monkeypatch.setattr(w3, "load_paired_stamp", _swap)
        _forbid_global_loaders(monkeypatch)
        payload = read_w3_guardrail(tmp_path)
        assert payload["status"] == "REFUSED"
        assert "benchmark" in payload["refusal"]
        _assert_no_stats(payload)

    def test_grain_fingerprint_must_match_observation_and_session(
            self, tmp_path, monkeypatch):
        stamps = _write_floor(tmp_path, n=20, c1_good=True, shadow_good=False)
        path = w3._part_path("paired", stamps[0], tmp_path)
        altered = pd.read_parquet(path).copy()
        altered.loc[altered.index[0], "score_rank"] = (
            int(altered.iloc[0]["score_rank"]) + 1000)
        rows = altered.to_dict(orient="records")
        rows[0]["identity_fingerprint"] = w3.fingerprint(rows[0], w3.PAIRED_IDENTITY)
        altered = pd.DataFrame(rows).reset_index(drop=True)

        real_load = w3.load_paired_stamp

        def _swap(root, stamp):
            frame = real_load(root, stamp)
            if str(stamp)[:10] == stamps[0]:
                return altered.copy()
            return frame

        monkeypatch.setattr(w3, "load_paired_stamp", _swap)
        _forbid_global_loaders(monkeypatch)
        payload = read_w3_guardrail(tmp_path)
        assert payload["status"] == "REFUSED"
        assert "paired grain fingerprint" in payload["refusal"]
        _assert_no_stats(payload)

    def test_lawful_floor_read_binds_grain_fingerprint_both_records(
            self, tmp_path, monkeypatch):
        stamps = _write_floor(tmp_path, n=20, c1_good=True, shadow_good=False)
        _forbid_global_loaders(monkeypatch)
        _forbid_writers(monkeypatch)
        payload = read_w3_guardrail(tmp_path)
        assert payload["status"] == "READ"
        assert payload["accrual"]["n_selected_sessions"] == 20
        assert set(payload["accrual"]["selected_stamps"]) == set(stamps)


class TestLoaderIsolationAndCli:

    def test_successful_read_uses_per_stamp_loader_not_global(
            self, tmp_path, monkeypatch):
        stamps = _write_floor(tmp_path, n=20, c1_good=True, shadow_good=False)
        _forbid_global_loaders(monkeypatch)
        _forbid_writers(monkeypatch)
        sess = w3.sessions_path(tmp_path).read_bytes()
        paired = w3._part_path("paired", stamps[0], tmp_path).read_bytes()
        payload = read_w3_guardrail(tmp_path)
        assert payload["status"] == "READ"
        assert w3.sessions_path(tmp_path).read_bytes() == sess
        assert w3._part_path("paired", stamps[0], tmp_path).read_bytes() == paired

    def test_cli_stdout_json_requires_root_and_writes_nothing(
            self, tmp_path, capsys):
        _write_floor(tmp_path, n=5)
        with pytest.raises(SystemExit):
            guardrail_main([])
        sess = w3.sessions_path(tmp_path).read_bytes()
        rc = guardrail_main(["--root", str(tmp_path)])
        assert rc == 0
        out = capsys.readouterr().out
        payload = json.loads(out)
        assert payload["status"] == "FLOOR_UNMET"
        assert payload["authority"] is False
        assert w3.sessions_path(tmp_path).read_bytes() == sess
        assert out.lstrip().startswith("{")
        assert "leader" not in out.lower()
