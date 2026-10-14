"""MUT4F killing tests for s1_report.py and s2_seal.py (2026-10-13).

SNI-local DRAFT contract tests. They consume caller-supplied synthetic
blocks and opaque subject tokens; they do not mint issuer or security
identifiers and they do not feed a rank, gate, size, signal, escalation,
or trade path. Authority flags stay false. Fixtures are synthetic.

Each test_mut4f_* docstring names one non-equivalent mutant that survived
the pre-existing importer suite (file:line, original -> mutated).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "research/single_name_intelligence/residual"))
sys.path.insert(0, str(REPO / "research/single_name_intelligence/event_response"))

from s1_prereg import POWER_FLOOR_N  # noqa: E402
from s1_report import (  # noqa: E402
    _below_floor_receipt,
    _sanitize_finding_words,
    appendix_cells,
    below_floor_count,
    block_lead,
    empty_exclusions,
    family_effective_n,
    family_wise_clearing,
    lead_change_counts,
    m2_over_m1_sentence,
    render_report_md,
    s0_criterion_holds,
    version_record_obj,
)
from s2_seal import (  # noqa: E402
    INFO_LEAK_STEP_TOLERANCE,
    MIN_TRAIN_CLUSTERS_POOLED_PRIOR,
    TRAILING63_SESSIONS,
    refuse_nonfalse_authority,
)


def _blk(*, honest_n: int = 200, analysis_set: str = "split=TRAIN",
         test: dict | None = None, ci: dict | None = None,
         trial_accounting: dict | None = None, **extra) -> dict:
    block = {
        "honest_n": honest_n,
        "analysis_set": analysis_set,
        "cluster_n": 1,
        "literal_rows": 1,
        "exclusions": empty_exclusions(),
        "test": test if test is not None else {},
        "ci": ci if ci is not None else {},
        "trial_accounting": trial_accounting if trial_accounting is not None else {},
        "receipt": {},
        "null": "synthetic null",
    }
    block.update(extra)
    return block


def _family(pid: str, blocks: dict, order: list[str] | None = None) -> dict:
    return {pid: {"family": pid, "blocks": blocks,
                  "block_order": order if order is not None else list(blocks)}}


def _lane() -> dict:
    return {
        "labels": ["HISTORICAL-DESCRIPTIVE (synthetic)"],
        "title": "S1 residual MUT4F fixture",
        "base": "e4c2f672bed06eef3fac0b7bb88d46275a228f28",
        "branch": "mut4f-fixture",
        "prereg_digest_sha256": "aa" * 32,
    }


# ---------------------------------------------------------------------------
# s1_report survivors
# ---------------------------------------------------------------------------


def test_mut4f_s1_report__below_floor_receipt_1():
    """s1_report.py:368, BoolOp `or` -> `and` in `_below_floor_receipt` statistic fallback."""
    rec = _below_floor_receipt(_blk(
        honest_n=10,
        test={"p_value": 0.4, "statistic": {"delta_R2": 0.01}},
        ci={"ci95": [0.0, 0.02], "mean": 0.0125, "delta_R2": 0.01},
    ))
    assert rec["statistic"] == {"delta_R2": 0.01}
    assert rec["mean"] == 0.0125
    assert rec["ci95"] == [0.0, 0.02]


def test_mut4f_s1_report__below_floor_receipt_2():
    """s1_report.py:367, BoolOp `or` -> `and` in `_below_floor_receipt` ci fallback."""
    rec = _below_floor_receipt(_blk(
        honest_n=10,
        test={"p_value": 0.01, "statistic": {"delta_R2": 0.2}},
        ci={"ci95": [0.1, 0.3], "mean": 0.05},
    ))
    assert rec["p_value"] == 0.01
    assert rec["statistic"] == {"delta_R2": 0.2}
    assert rec["mean"] == 0.05
    assert rec["ci95"] == [0.1, 0.3]


def test_mut4f_s1_report__sanitize_finding_words_1():
    """s1_report.py:357, `return {k: ...}` -> `return None` (dict branch)."""
    got = _sanitize_finding_words({"null": "criterion met"})
    assert got == {"null": ""}


def test_mut4f_s1_report__sanitize_finding_words_2():
    """s1_report.py:359, `return [_sanitize_finding_words(v) for v in obj]` -> `return None`."""
    got = _sanitize_finding_words(["beats", "rejects"])
    assert got == ["", ""]


def test_mut4f_s1_report_appendix_cells_1():
    """s1_report.py:169, comparison `pv < 0.05` -> `pv <= 0.05`."""
    key = "P01|adr_baba|h=5|TRAIN|X"
    protocols = _family("P01", {
        key: _blk(honest_n=200, test={"p_value": 0.05},
                  trial_accounting={"effective_n": 5}),
    })
    assert appendix_cells(protocols) == []


def test_mut4f_s1_report_appendix_cells_2():
    """s1_report.py:169, constant `0.05` -> `0.05*1.001` in appendix threshold."""
    key = "P01|adr_baba|h=5|TRAIN|X"
    protocols = _family("P01", {
        key: _blk(honest_n=200, test={"p_value": 0.05002},
                  trial_accounting={"effective_n": 5}),
    })
    assert appendix_cells(protocols) == []


def test_mut4f_s1_report_below_floor_count_1():
    """s1_report.py:254, constant `n = 0` -> `n = 1` in below_floor_count."""
    assert below_floor_count({}) == 0


def test_mut4f_s1_report_below_floor_count_2():
    """s1_report.py:258, constant `n += 1` -> `n += 2` in below_floor_count."""
    protocols = _family("P01", {
        "P01|adr_baba|h=5|TRAIN|X": _blk(honest_n=1),
    })
    assert below_floor_count(protocols) == 1


def test_mut4f_s1_report_block_lead_1():
    """s1_report.py:116, TUNE-RETIRED `return (f"criterion not assessable...")` -> `return None`."""
    lead = block_lead(
        "P03|adr_baba|h=5|TUNE|M2_vs_M1",
        _blk(honest_n=POWER_FLOOR_N,
             analysis_set="PRIMARY; TUNE RETIRED (A23 INFO-LEAK)",
             test={"verdict": "S0 criterion met; descriptive comparison kept"}),
    )
    assert lead.startswith("criterion not assessable — TUNE RETIRED")
    assert "descriptive comparison" in lead


def test_mut4f_s1_report_empty_exclusions_1():
    """s1_report.py:69, `return {excluded_listed: 0, ...}` -> `return None`."""
    ex = empty_exclusions()
    assert ex == {
        "excluded_listed": 0,
        "confounded": 0,
        "absorbed": 0,
        "purged": 0,
        "quarantine": 0,
        "detail": {},
    }


def test_mut4f_s1_report_family_effective_n_1():
    """s1_report.py:127, fallback `return 0` -> `return None` when no effective_n."""
    protocols = _family("P01", {
        "P01|adr_baba|h=5|TRAIN|X": _blk(trial_accounting={"literal_n": 9}),
    })
    assert family_effective_n(protocols, "P01") == 0


def test_mut4f_s1_report_family_wise_clearing_1():
    """s1_report.py:159, comparison `pv < a` -> `pv <= a` in family_wise_clearing."""
    key = "P01|adr_baba|h=5|TRAIN|X"
    protocols = _family("P01", {
        key: _blk(honest_n=POWER_FLOOR_N, test={"p_value": 0.05},
                  trial_accounting={"effective_n": 1}),
    })
    assert family_wise_clearing(protocols, "P01") == []


def test_mut4f_s1_report_lead_change_counts_1():
    """s1_report.py:277, BoolOp `and` -> `or` in TRAIN BLOCKED-AS-EVIDENCE counter."""
    protocols = _family("P01", {
        "P01|adr_baba|h=5|TRAIN|X": _blk(
            honest_n=200, analysis_set="PRIMARY = SENS-A = SENS-B; split=TRAIN"),
    })
    got = lead_change_counts(protocols)
    assert got["train_blocks_blocked_as_evidence"] == 0


def test_mut4f_s1_report_m2_over_m1_sentence_1():
    """s1_report.py:244, BoolOp `or` -> `and` in HK M2_vs_M1 verdict fallback."""
    baba = _blk(
        honest_n=200,
        test={"statistic": {"delta_R2": 0.2}, "verdict": "S0 criterion met"},
        ci={"ci95": [0.05, 0.4], "delta_R2": 0.2},
    )
    hk = _blk(
        honest_n=200,
        test={"statistic": {"delta_R2": -0.1},
              "verdict": "KILL/HOLD — criterion not met"},
        ci={"ci95": [-0.2, 0.0], "delta_R2": -0.1},
    )
    protocols = _family("P03", {
        "P03|adr_baba|h=5|TRAIN|M2_vs_M1": baba,
        "P03|hkd_9988|h=5|TRAIN|M2_vs_M1": hk,
    })
    sent = m2_over_m1_sentence(protocols)
    assert sent is not None
    assert "KILL/HOLD" in sent


def test_mut4f_s1_report_render_report_md_1():
    """s1_report.py:476, BoolOp `or` -> `and` in render_report_md default seal_path."""
    md = render_report_md(_lane(), {}, {})
    assert "SEAL_AND_BUDGET.json" in md
    assert "seal: None" not in md


def test_mut4f_s1_report_s0_criterion_holds_1():
    """s1_report.py:94, BoolOp `or` -> `and` in s0_criterion_holds test fallback."""
    block = {
        "test": {"statistic": {"delta_R2": 0.2}},
        "ci": {"ci95": [0.1, 0.3]},
    }
    assert s0_criterion_holds(block) is True


def test_mut4f_s1_report_version_record_obj_1():
    """s1_report.py:323, constant `escalation: False` -> `True` in version_record_obj."""
    rec = version_record_obj(_lane(), {}, True)
    assert rec["authority_flags"]["signal"] is False
    assert rec["authority_flags"] == {
        "rank": False, "gate": False, "size": False,
        "signal": False, "escalation": False, "trade": False,
    }


# ---------------------------------------------------------------------------
# s2_seal survivors
# ---------------------------------------------------------------------------


def test_mut4f_s2_seal_module_1():
    """s2_seal.py:216, INFO_LEAK_STEP_TOLERANCE `1e-6` -> `1e-6*1.001`."""
    assert INFO_LEAK_STEP_TOLERANCE == 1e-6


def test_mut4f_s2_seal_module_2():
    """s2_seal.py:197, TRAILING63_SESSIONS `63` -> `64`."""
    assert TRAILING63_SESSIONS == 63


def test_mut4f_s2_seal_module_3():
    """s2_seal.py:194, MIN_TRAIN_CLUSTERS_POOLED_PRIOR `2` -> `3`."""
    assert MIN_TRAIN_CLUSTERS_POOLED_PRIOR == 2


def test_mut4f_s2_seal_refuse_nonfalse_authority_1():
    """s2_seal.py:100, delete `if not isinstance(mapping, dict): raise` guard."""
    with pytest.raises(ValueError, match="not a mapping"):
        refuse_nonfalse_authority({"authority_flags": ["rank_authority"]})


def test_mut4f_s2_seal_refuse_nonfalse_authority_2():
    """s2_seal.py:96, delete `if top is None and under_labels is None: raise` guard."""
    with pytest.raises(ValueError, match="no authority_flags"):
        refuse_nonfalse_authority({})
