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
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "research/single_name_intelligence/residual"))
sys.path.insert(0, str(REPO / "research/single_name_intelligence/event_response"))

import lib.nyse_calendar as nyse_calendar  # noqa: E402
import run_s2 as run_s2_mod  # noqa: E402
import s2_outcomes as s2_outcomes  # noqa: E402
from run_s2 import episode_identity, pooled_prior  # noqa: E402
from s2_outcomes import BABA_PATH, OutcomeEngine  # noqa: E402
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
    GRADE_HORIZONS,
    INFO_LEAK_STEP_TOLERANCE,
    MIN_TRAIN_CLUSTERS_POOLED_PRIOR,
    PROTOCOLS,
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

_SYNTH_ISSUER = "synthetic-issuer-mut4f"


class _SynthLoader:
    """Caller-supplied synthetic price frames; parquet paths are opaque keys."""

    def __init__(self, baba, spy):
        self.baba = baba
        self.spy = spy

    def read_parquet(self, path, columns=None):
        df = self.baba if path == BABA_PATH else self.spy
        return df if columns is None else df[[c for c in columns if c in df.columns]]


def _price_frame(sess, closes, raw=None):
    return pd.DataFrame({
        "Date": pd.to_datetime(sess),
        "close": list(closes),
        "close_price": list(closes) if raw is None else list(raw),
    })


def _price_engine(sess, baba_closes, spy_closes, baba_raw=None, spy_raw=None):
    return OutcomeEngine(_SynthLoader(
        _price_frame(sess, baba_closes, baba_raw),
        _price_frame(sess, spy_closes, spy_raw),
    ))


def _sessions_ending_at(last: date, n: int) -> list:
    """The n NYSE sessions ending at `last`, oldest first (last is a session)."""
    out, cur = [last], last
    while len(out) < n:
        cur -= timedelta(days=1)
        if nyse_calendar.is_session(cur):
            out.append(cur)
    return list(reversed(out))


def _prior_episode(s_us: str, n: int) -> SimpleNamespace:
    opener = SimpleNamespace(
        issuer_key=_SYNTH_ISSUER,
        family="results",
        t_avail_utc=f"{s_us}T20:00:00Z",
        evidence_pointer=f"synthetic#ep={n}",
        s_us=s_us,
        s_hk=s_us,
        member_ids=[f"synthetic-{n}"],
    )
    return SimpleNamespace(opener=opener, confounded=False, absorbed_count=0)


def _prior_state() -> dict:
    return {
        "membership": {
            pid: {"counted": {h: [] for h in GRADE_HORIZONS}} for pid in PROTOCOLS
        },
        "collapse": {"counts": {"literal_row_count_pre_step0": 0,
                                "excluded_and_listed": []}},
        "prereg_digest_sha256": "aa" * 32,
    }


def _graded(excess: float) -> dict:
    return {"state": "OK", "excess": excess, "window": None}


def test_mut4f_s2_seal_module_1():
    """s2_seal.py:216, INFO_LEAK_STEP_TOLERANCE `1e-6` -> `1e-6*1.001`.

    Behavioural (X7-05): the consumer is OutcomeEngine.info_leak_scan, whose
    use-site global is s2_outcomes.INFO_LEAK_STEP_TOLERANCE. A vintage step
    at the nominal tolerance stays clean; a step strictly between the
    tolerance and the mutant tolerance*1.001 raises the leak bit. Inputs are
    pinned to the nominal tolerance so a use-site mutation flips the
    observable; the trailing equality line catches a declaration-only
    mutation of the seal copy (behaviour is driven by the use-site copy).
    """
    tol = 1e-6  # nominal INFO_LEAK_STEP_TOLERANCE (seal and s2_outcomes agree)
    # float-exact boundary facts for q = close/close_price with raw = 1.0
    assert (1.0 + tol) / 1.0 - 1.0 <= tol
    assert tol < (1.0 + tol * 1.0005) / 1.0 - 1.0 <= tol * 1.001
    sess = [date(2024, 6, 3), date(2024, 6, 4), date(2024, 6, 5),
            date(2024, 6, 6), date(2024, 6, 7)]
    assert all(nyse_calendar.is_session(d) for d in sess)

    def _scan(vintage_step: float) -> dict:
        eng = _price_engine(
            sess, [1.0, 1.0, vintage_step, vintage_step, vintage_step],
            [200.0] * len(sess), baba_raw=[1.0] * len(sess),
            spy_raw=[200.0] * len(sess))
        return eng.info_leak_scan(sess[0])

    at_tolerance = _scan(1.0 + tol)
    inside_mutant = _scan(1.0 + tol * 1.0005)
    assert at_tolerance["series"]["BABA"]["steps_above_tolerance"] == 0
    assert at_tolerance["leak"] is False
    assert inside_mutant["series"]["BABA"]["steps_above_tolerance"] == 1
    assert inside_mutant["leak"] is True
    assert s2_outcomes.INFO_LEAK_STEP_TOLERANCE == INFO_LEAK_STEP_TOLERANCE


def test_mut4f_s2_seal_module_2():
    """s2_seal.py:197, TRAILING63_SESSIONS `63` -> `64`.

    Behavioural (X7-05): the consumer is OutcomeEngine.trailing63_direction,
    whose use-site global is s2_outcomes.TRAILING63_SESSIONS. With
    TRAILING63_SESSIONS-1 sessions of history before D(s) the D63 bar is
    absent and the direction abstains (0); with TRAILING63_SESSIONS sessions
    of history the D63 bar is present and the designed +1 sign is returned.
    History lengths are pinned to the nominal 63 so a use-site mutation
    flips the observable; the trailing equality line catches a
    declaration-only mutation of the seal copy.
    """
    t63 = 63  # nominal TRAILING63_SESSIONS (seal and s2_outcomes agree)
    s_us = date(2024, 6, 3)
    d = s_us - timedelta(days=1)
    while not nyse_calendar.is_session(d):
        d -= timedelta(days=1)

    short = _sessions_ending_at(d, t63)      # d + t63-1 earlier sessions
    eng_short = _price_engine(short, [100.0] * len(short), [100.0] * len(short))
    assert eng_short.trailing63_direction(s_us) == 0  # D63 bar absent

    full = _sessions_ending_at(d, t63 + 1)   # d + t63 earlier sessions
    baba = [100.0] * len(full)
    baba[full.index(d)] = 110.0              # +10% subject excess over D63..D
    eng_full = _price_engine(full, baba, [100.0] * len(full))
    assert eng_full.trailing63_direction(s_us) == 1  # D63 bar present
    assert s2_outcomes.TRAILING63_SESSIONS == TRAILING63_SESSIONS


def test_mut4f_s2_seal_module_3():
    """s2_seal.py:194, MIN_TRAIN_CLUSTERS_POOLED_PRIOR `2` -> `3`.

    Behavioural (X7-05): the consumer is run_s2.pooled_prior, which imports
    the constant from s2_seal (use-site global
    run_s2.MIN_TRAIN_CLUSTERS_POOLED_PRIOR). With one fewer than
    MIN_TRAIN_CLUSTERS_POOLED_PRIOR distinct TRAIN clusters (cluster_key =
    s_us) the prior abstains NOT ESTIMABLE; with exactly that many clusters
    it estimates the sign. Cluster counts are pinned to the nominal 2 so a
    use-site mutation flips the observable; the trailing equality line
    catches a declaration-only mutation of the seal copy.
    """
    one = _prior_episode("2019-03-01", 1)
    two = _prior_episode("2019-06-03", 2)
    k1, k2 = episode_identity(one), episode_identity(two)
    assert one.opener.s_us != two.opener.s_us  # distinct cluster_keys

    state_one = _prior_state()
    state_one["membership"]["P04"]["counted"][5] = [one]
    direction, token = pooled_prior(
        state_one, {"outcomes": {(k1, 5): _graded(0.10)}, "trailing": {}}, 5)
    assert direction is None
    assert "NOT ESTIMABLE" in token

    state_two = _prior_state()
    state_two["membership"]["P04"]["counted"][5] = [one, two]
    direction_two, token_two = pooled_prior(
        state_two,
        {"outcomes": {(k1, 5): _graded(0.10), (k2, 5): _graded(0.30)},
         "trailing": {}},
        5)
    assert direction_two == 1
    assert "+0.200000" in token_two
    assert (run_s2_mod.MIN_TRAIN_CLUSTERS_POOLED_PRIOR
            == MIN_TRAIN_CLUSTERS_POOLED_PRIOR)


def test_mut4f_s2_seal_refuse_nonfalse_authority_1():
    """s2_seal.py:100, delete `if not isinstance(mapping, dict): raise` guard."""
    with pytest.raises(ValueError, match="not a mapping"):
        refuse_nonfalse_authority({"authority_flags": ["rank_authority"]})


def test_mut4f_s2_seal_refuse_nonfalse_authority_2():
    """s2_seal.py:96, delete `if top is None and under_labels is None: raise` guard."""
    with pytest.raises(ValueError, match="no authority_flags"):
        refuse_nonfalse_authority({})
