"""test_sni_quarantine_fence.py — mutation tests for the SNI QUARANTINE fence.

SNI-local DRAFT contract tests. They consume owner-supplied opaque identity
strings (Stock Identity / Data OS) and never mint issuer or security ids.
HISTORICAL-DESCRIPTIVE only: rank_authority, gate_authority, size_authority,
signal_authority, escalation_authority and trade_authority stay false.

Registered split (S0 SL §2): TRAIN s < 2024-01-01; TUNE [2024-01-01, 2026-10-01);
QUARANTINE s >= 2026-10-01. An observation dated on/after 2026-10-01 must not
reach a TRAIN/TUNE statistic. Fixtures are synthetic in-memory rows.
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "research/single_name_intelligence/residual"))
sys.path.insert(0, str(REPO / "research/single_name_intelligence/event_response"))

from s1_manifest import TRAIN_END, TUNE_END, label_unit, time_split  # noqa: E402
from s1_prereg import HORIZONS, build_spec  # noqa: E402
from s1_report import render_report_md  # noqa: E402
import run_s1  # noqa: E402

from s2_seal import (  # noqa: E402
    GRADE_HORIZONS,
    PROTOCOLS,
    SPLIT_QUARANTINE_START,
    SPLIT_TUNEE_START,
    SPLITS,
    build_prereg_spec,
)
from s2_splits import purge_flag, split_label  # noqa: E402
from run_s2 import render_report  # noqa: E402

BOUNDARY = date(2026, 10, 1)
PRE = date(2026, 9, 30)
ON = date(2026, 10, 1)
POST = date(2026, 10, 2)
SYNTH_DATES = (PRE, ON, POST)
LIVE_SPLITS = ("TRAIN", "TUNE")


class _CloseStore:
    """Synthetic price store. Identity paths are opaque caller strings."""

    def __init__(self, dates, close=100.0):
        self.dates = list(dates)
        self.close = float(close)

    def frame(self, path, columns):
        n = len(self.dates)
        cols = {c: [self.close + i * 0.01 for i in range(n)] for c in columns}
        return list(self.dates), cols


def _empty_rebuilt(pid, counter, rows):
    out = {}
    for h in HORIZONS:
        out[(pid, counter, h)] = {
            "rows": list(rows),
            "digests": {
                "TRAIN": {"membership_sha256": "0" * 64, "count": 0},
                "TUNE": {"membership_sha256": "0" * 64, "count": 0},
                "QUARANTINE": {"membership_sha256": "0" * 64, "count": 0},
            },
        }
    return out


def _manifest_row(split, session, coverage=None, key="ek"):
    return {
        "split": split,
        "anchor_session_date": session.isoformat(),
        "coverage_date": None if coverage is None else coverage.isoformat(),
        "episode_key": f"{key}-{split}-{session.isoformat()}",
    }


# ---------------------------------------------------------------------------
# (i) constants: 2026-10-01 and TUNE end == QUARANTINE start
# ---------------------------------------------------------------------------

def test_s1_tune_end_is_2026_10_01():
    assert TUNE_END == BOUNDARY
    assert TUNE_END == date(2026, 10, 1)


def test_s2_quarantine_start_is_2026_10_01():
    assert SPLIT_QUARANTINE_START == BOUNDARY
    assert SPLIT_QUARANTINE_START == date(2026, 10, 1)


def test_tune_end_equals_quarantine_start_across_s1_and_s2():
    assert TUNE_END == SPLIT_QUARANTINE_START
    assert TRAIN_END == SPLIT_TUNEE_START == date(2024, 1, 1)


# ---------------------------------------------------------------------------
# (ii) synthetic frame 2026-09-30 / 2026-10-01 / 2026-10-02
# ---------------------------------------------------------------------------

def test_s1_time_split_drops_on_and_after_boundary_from_live_splits():
    labelled = [(d, time_split(d)) for d in SYNTH_DATES]
    assert labelled[0] == (PRE, "TUNE")
    assert labelled[1] == (ON, "QUARANTINE")
    assert labelled[2] == (POST, "QUARANTINE")
    live = [d for d, sp in labelled if sp in LIVE_SPLITS]
    assert live == [PRE]


def test_s2_split_label_drops_on_and_after_boundary_from_live_splits():
    labelled = [(d, split_label(d)) for d in SYNTH_DATES]
    assert labelled[0] == (PRE, "TUNE")
    assert labelled[1] == (ON, "QUARANTINE")
    assert labelled[2] == (POST, "QUARANTINE")
    live = [d for d, sp in labelled if sp in LIVE_SPLITS]
    assert live == [PRE]


def test_s1_label_unit_same_day_coverage_keeps_pre_boundary_in_tune():
    # coverage == anchor: the 2026-09-30 unit stays TUNE; the last two are QUARANTINE.
    labelled = [label_unit(d, d) for d in SYNTH_DATES]
    assert labelled == ["TUNE", "QUARANTINE", "QUARANTINE"]
    live = [d for d, sp in zip(SYNTH_DATES, labelled) if sp in LIVE_SPLITS]
    assert live == [PRE]


def test_s1_label_unit_purges_tune_when_coverage_reaches_boundary():
    assert label_unit(PRE, BOUNDARY) == "PURGED_TUNE"
    assert label_unit(PRE, date(2026, 9, 30)) == "TUNE"
    assert label_unit(ON, POST) == "QUARANTINE"


def test_s2_purge_flag_true_when_tune_coverage_reaches_boundary():
    assert purge_flag("TUNE", BOUNDARY) is True
    assert purge_flag("TUNE", PRE) is False
    assert purge_flag("QUARANTINE", POST) is False
    assert purge_flag("TUNE", None) is True


# ---------------------------------------------------------------------------
# (iii) sealed spec records the boundary; eval filters exclude quarantined rows
# ---------------------------------------------------------------------------

def test_s1_build_spec_records_quarantine_boundary():
    spec = build_spec()
    splits = spec["splits"]
    assert splits["tune"] == "2024-01-01 <= s < 2026-10-01"
    assert splits["quarantine"] == "s >= 2026-10-01 (listed and counted, never evaluated)"
    assert splits["purge"]["tune"] == "coverage_date >= 2026-10-01 -> PURGED_TUNE"
    assert spec["authority_flags"]["rank"] is False
    assert spec["authority_flags"]["gate"] is False
    assert spec["authority_flags"]["size"] is False
    assert spec["authority_flags"]["signal"] is False
    assert spec["authority_flags"]["escalation"] is False
    assert spec["authority_flags"]["trade"] is False


def test_s2_build_prereg_spec_records_quarantine_boundary():
    spec = build_prereg_spec({}, [], [])
    splits = spec["splits"]
    assert splits["TUNE"] == "2024-01-01 <= s < 2026-10-01"
    assert splits["QUARANTINE"] == "s >= 2026-10-01 (listed, counted, never evaluated)"
    assert "2026-10-01" in splits["purge"]
    flags = spec["labels"]["authority_flags"]
    for k in ("rank_authority", "gate_authority", "size_authority",
              "signal_authority", "escalation_authority", "trade_authority"):
        assert flags[k] is False


def test_s1_report_names_tune_window_ending_2026_10_01():
    lane = {
        "labels": ["HISTORICAL-DESCRIPTIVE (non-confirmatory)"],
        "title": "S1 residual fence fixture",
        "base": "synthetic",
        "branch": "synthetic",
        "prereg_digest_sha256": "0" * 64,
    }
    md = render_report_md(lane, {})
    assert "2024-01-01..2026-10-01 TUNE" in md
    assert "2026-12-01" not in md.split("## Coverage and current regime", 1)[1].split("##", 1)[0]


def test_s2_report_names_tune_window_crossing_2026_10_01():
    def _blk():
        return {
            "family_row": {
                "honest_n": 0, "distinct_calendar_clusters": 0,
                "abstention_state": "ABSTAIN_NO_EPISODES",
                "event_count": 0, "honest_n_sens_a": 0, "honest_n_sens_b": 0,
                "pooling_weight": "NOT ESTIMABLE", "uncertainty": "n/a",
            },
            "labels": {"status": "HISTORICAL-DESCRIPTIVE"},
            "plain_word_null": "no test",
            "analysis_set": {
                "SENS_A": {"honest_n": 0, "cluster_n": 0},
                "SENS_B": {"honest_n": 0, "cluster_n": 0},
            },
            "honest_n": {"PRIMARY": 0},
            "cluster_n": {"PRIMARY": 0},
            "literal_row_count": 0,
            "visible_exclusions": {
                "excluded_and_listed_count": 0, "excluded_and_listed": [],
                "confounded": 0, "absorbed": 0, "purged": 0, "quarantine": 0,
            },
            "test": "ABSTAIN_NO_EPISODES",
            "ci": "CI NOT ESTIMABLE (cluster-N < 2)",
            "receipt": {
                "code_commit_sha": "synthetic",
                "prereg_digest_sha256": "0" * 64,
                "seal_row": "synthetic",
                "trial_ledger_path": "synthetic",
                "prior_looks": "none",
            },
            "baselines": {},
            "proper_score": "NOT SUPPORTED",
            "trials": {"literal_n": 0, "effective_n": 0, "declared_budget": 6},
        }

    results = {
        pid: {
            "title": pid,
            "splits": {sp: {f"h{h}": _blk() for h in GRADE_HORIZONS} for sp in SPLITS},
        }
        for pid in PROTOCOLS
    }
    retirement = {pid: {"state": "ok"} for pid in PROTOCOLS}
    md = render_report(results, retirement, version_record={})
    assert "reaches past 2026-10-01" in md


def test_s0_register_time_axis_split_pins_2026_10_01():
    text = (REPO / "research/single_name_intelligence/protocols"
            / "S0_PROTOCOL_REGISTER.md").read_text(encoding="utf-8")
    needle = ("TUNE [2024-01-01, 2026-10-01); TEST = prospective claims "
              "registered after the S0 freeze and after §2; QUARANTINE otherwise "
              "for `s` ≥ 2026-10-01")
    assert needle in text


def test_s1_evaluate_directional_does_not_score_quarantine_rows():
    rows = [
        _manifest_row("TUNE", PRE, PRE, "tune"),
        _manifest_row("QUARANTINE", ON, ON, "q1"),
        _manifest_row("QUARANTINE", POST, POST, "q2"),
    ]
    rebuilt = _empty_rebuilt("P01", "adr_baba", rows)
    store = _CloseStore([PRE + timedelta(days=i) for i in range(-5, 10)])
    ev = run_s1.evaluate_directional("P01", store, rebuilt)
    for h in HORIZONS:
        obs = ev["observations"][f"P01_adr_baba_{h}"]
        q = [o for o in obs if o["manifest_split"] == "QUARANTINE"]
        assert len(q) == 2
        for o in q:
            assert o["excess"] is None
            assert o["trail63_direction"] is None
            assert o["abstention"] == "OK"


def test_s1_directional_blocks_emit_no_quarantine_stat_keys():
    rows = [
        _manifest_row("TUNE", PRE, PRE, "tune"),
        _manifest_row("QUARANTINE", ON, ON, "q1"),
        _manifest_row("QUARANTINE", POST, POST, "q2"),
    ]
    rebuilt = _empty_rebuilt("P01", "adr_baba", rows)
    obs = []
    for r in rows:
        obs.append({
            "episode_key": r["episode_key"],
            "anchor_session_date": r["anchor_session_date"],
            "coverage_date": r["coverage_date"],
            "manifest_split": r["split"],
            "split": r["split"],
            "time_split": time_split(date.fromisoformat(r["anchor_session_date"])),
            "abstention": "OK",
            "excess": 0.01 if r["split"] == "TUNE" else None,
            "tie": False,
            "always_long_direction": 1,
            "trail63_direction": 1 if r["split"] == "TUNE" else None,
        })
    evaluation = {"observations": {f"P01_adr_baba_{h}": list(obs) for h in HORIZONS}}
    blocks, order = run_s1.directional_blocks(
        "P01", evaluation, rebuilt, set(),
        trial_accounting={"literal_n": 0, "effective_n": 0, "declared_budget": 6},
        receipt_base={},
    )
    assert order
    for key in list(blocks) + list(order):
        assert "|QUARANTINE" not in key
        assert "QUARANTINE (" not in key


def test_s1_quarantine_missing_endpoint_is_not_folded_into_live_exclusions():
    rows = [
        _manifest_row("TUNE", PRE, PRE, "tune"),
        _manifest_row("QUARANTINE", ON, ON, "q1"),
    ]
    rebuilt = _empty_rebuilt("P01", "adr_baba", rows)
    obs_h5 = [
        {
            "episode_key": "tune",
            "anchor_session_date": PRE.isoformat(),
            "coverage_date": PRE.isoformat(),
            "manifest_split": "TUNE",
            "split": "TUNE",
            "time_split": "TUNE",
            "abstention": "OK",
            "excess": 0.01,
            "tie": False,
            "always_long_direction": 1,
            "trail63_direction": 1,
        },
        {
            "episode_key": "q-miss",
            "anchor_session_date": ON.isoformat(),
            "coverage_date": ON.isoformat(),
            "manifest_split": "QUARANTINE",
            "split": "QUARANTINE",
            "time_split": "QUARANTINE",
            "abstention": "ABSTAIN_MISSING_ENDPOINT",
            "excess": None,
            "tie": False,
            "always_long_direction": 1,
            "trail63_direction": None,
        },
    ]
    evaluation = {
        "observations": {
            "P01_adr_baba_5": obs_h5,
            "P01_adr_baba_21": [],
            "P01_adr_baba_63": [],
        }
    }
    blocks, _ = run_s1.directional_blocks(
        "P01", evaluation, rebuilt, set(),
        trial_accounting={"literal_n": 0, "effective_n": 0, "declared_budget": 6},
        receipt_base={},
    )
    for key, blk in blocks.items():
        detail = (blk.get("exclusions") or {}).get("detail") or {}
        if "|TUNE" in key or "|TRAIN" in key:
            assert detail.get("abstain_missing_endpoint", 0) == 0


def test_s1_evaluate_p03_skips_quarantine_rows():
    q_row = _manifest_row("QUARANTINE", ON, POST, "q")
    t_row = _manifest_row("TUNE", PRE, PRE, "t")
    rebuilt = {}
    for counter in ("adr_baba", "hkd_9988", "hkd_0700"):
        for h in HORIZONS:
            rebuilt[("P03", counter, h)] = {
                "rows": [q_row, t_row] if counter == "adr_baba" and h == 5 else [],
                "digests": {"TRAIN": {"membership_sha256": "0" * 64, "count": 0},
                            "TUNE": {"membership_sha256": "0" * 64, "count": 0}},
            }
    dates = [PRE]
    close = {PRE: 100.0}
    frames = {
        "BABA": (dates, close, None),
        "9988": (dates, close, None),
        "0700": (dates, close, None),
        "SPY": (dates, close, None),
        "KWEB": (dates, close, None),
        "2800.HK": (dates, close, None),
        "3033.HK": (dates, close, None),
    }
    store = _CloseStore(dates)
    out = run_s1.evaluate_p03(store, rebuilt, frames, challenger_ctx=None)
    for key, rows in out.items():
        assert all(r.get("split") != "QUARANTINE" for r in rows), key


def _p03_obs_and_rebuilt():
    rebuilt = {}
    p03_obs = {}
    for counter in ("adr_baba", "hkd_9988", "hkd_0700"):
        for h in HORIZONS:
            rebuilt[("P03", counter, h)] = {
                "rows": [],
                "digests": {
                    "TRAIN": {"membership_sha256": "0" * 64, "count": 0},
                    "TUNE": {"membership_sha256": "0" * 64, "count": 0},
                    "QUARANTINE": {"membership_sha256": "0" * 64, "count": 0},
                },
            }
            rows = []
            for model in ("M0", "M1", "M2"):
                rows.append({
                    "episode_key": f"tune-{model}",
                    "split": "TUNE",
                    "model": model,
                    "abstention": "OK",
                    "z__oc": 0.1,
                    "r__oc": 0.2,
                    "common__oc": 0.05,
                    "anchor_session_date": PRE.isoformat(),
                    "challenger": {"state": "OK", "common_ipca__oc": 0.04},
                })
                rows.append({
                    "episode_key": f"q-{model}",
                    "split": "QUARANTINE",
                    "model": model,
                    "abstention": "OK",
                    "z__oc": 9.9,
                    "r__oc": 9.9,
                    "common__oc": 9.9,
                    "anchor_session_date": ON.isoformat(),
                    "challenger": {"state": "OK", "common_ipca__oc": 9.9},
                })
            p03_obs[f"P03_{counter}_{h}"] = rows
    return p03_obs, rebuilt


def test_s1_p03_calibration_omits_quarantine():
    p03_obs, rebuilt = _p03_obs_and_rebuilt()
    _, _, diagnostics = run_s1.p03_blocks(
        p03_obs, rebuilt, set(),
        trial_accounting={"literal_n": 0, "effective_n": 0, "declared_budget": 4},
        receipt_base={},
    )
    assert diagnostics
    assert all("QUARANTINE" not in k for k in diagnostics)


def test_s1_p03_comparison_blocks_omit_quarantine():
    p03_obs, rebuilt = _p03_obs_and_rebuilt()
    blocks, order, _ = run_s1.p03_blocks(
        p03_obs, rebuilt, set(),
        trial_accounting={"literal_n": 0, "effective_n": 0, "declared_budget": 4},
        receipt_base={},
    )
    assert order
    for key in list(blocks) + list(order):
        assert "|QUARANTINE" not in key
