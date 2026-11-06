"""MUT5D killing tests for run_s2.py (functions before generate_outputs).

SNI-local DRAFT contract tests. They consume caller-supplied synthetic
episodes and opaque issuer tokens; they do not mint issuer or security
identifiers and they do not feed a rank, gate, size, signal, escalation,
or trade path. Authority flags stay false. Fixtures are synthetic.
Residuals and event-study numbers are descriptive, never causal, never a
news-impact claim (A24). An unestimable family ABSTAINS (A25).

Each test_mut5d_run_s2_* docstring names one non-equivalent mutant that
survived the pre-existing importer suite (file:line, original -> mutated).
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research/single_name_intelligence/event_response"))

import run_s2 as run_s2_mod  # noqa: E402
from run_s2 import (  # noqa: E402
    RETIRED_TOKEN,
    base_commit_detected_at,
    build_block,
    episode_identity,
    episode_purged,
    evaluate_family,
    pooled_prior,
    refuse_data_path,
)
from s2_seal import (  # noqa: E402
    BASELINE_ALWAYS_LONG,
    GRADE_HORIZONS,
    PROTOCOLS,
)
from s2_splits import episode_key  # noqa: E402

ISSUER = "synthetic-issuer-mut5d"


def _ep(s_us: str, n: int = 1) -> SimpleNamespace:
    opener = SimpleNamespace(
        issuer_key=ISSUER,
        family="results",
        t_avail_utc=f"{s_us}T20:00:00Z",
        evidence_pointer=f"synthetic#ep={n}",
        s_us=s_us,
        s_hk=s_us,
        member_ids=[f"synthetic-{n}"],
    )
    return SimpleNamespace(opener=opener, confounded=False, absorbed_count=0)


def _empty_state() -> dict:
    return {
        "membership": {
            pid: {"counted": {h: [] for h in GRADE_HORIZONS}} for pid in PROTOCOLS
        },
        "collapse": {
            "counts": {
                "literal_row_count_pre_step0": 0,
                "excluded_and_listed": [],
            }
        },
        "prereg_digest_sha256": "aa" * 32,
    }


def _ok(excess: float) -> dict:
    return {"state": "OK", "excess": excess, "window": None}


def _ledger() -> dict:
    return {"literal_n": 0, "effective_n": 0, "declared_budget": 6}


def _tested_block():
    """153 TRAIN PRIMARY episodes: 100 positive excess, 53 negative."""
    eps = []
    occ = {"outcomes": {}, "trailing": {}}
    for i in range(153):
        s_us = "2019-03-01" if i < 80 else "2019-06-03"
        ep = _ep(s_us, i + 1)
        eps.append(ep)
        key = episode_identity(ep)
        excess = 0.05 if i < 100 else -0.05
        occ["outcomes"][(key, 5)] = _ok(excess)
    state = _empty_state()
    state["membership"]["P04"]["counted"][5] = eps
    return build_block("P04", state, occ, 5, "TRAIN", _ledger(), [], {})


# ---------------------------------------------------------------------------
# base_commit_detected_at
# ---------------------------------------------------------------------------


def test_mut5d_run_s2_base_commit_detected_at_1(monkeypatch, tmp_path: Path) -> None:
    """run_s2.py:89, return parsed.isoformat() -> return None (base_commit_detected_at)."""

    class _Proc:
        stdout = "2026-10-11T21:59:47-04:00\n"
        stderr = ""
        returncode = 0

    monkeypatch.setattr(run_s2_mod.subprocess, "run", lambda *_a, **_k: _Proc())
    got = base_commit_detected_at("synthetic-ref", tmp_path)
    assert got == "2026-10-12T01:59:47+00:00"


# ---------------------------------------------------------------------------
# episode_identity / episode_purged
# ---------------------------------------------------------------------------


def test_mut5d_run_s2_episode_identity_1() -> None:
    """run_s2.py:111, return mk(...) -> return None (episode_identity)."""
    ep = _ep("2019-06-03", 1)
    want = episode_key(
        ISSUER, "results", "2019-06-03T20:00:00Z", "synthetic#ep=1"
    )
    assert episode_identity(ep) == want


def test_mut5d_run_s2_episode_purged_1() -> None:
    """run_s2.py:118, return purge_flag(split, coverage) -> return None (episode_purged)."""
    assert episode_purged(_ep("2019-06-03", 1), 5) is False


# ---------------------------------------------------------------------------
# evaluate_family
# ---------------------------------------------------------------------------


def test_mut5d_run_s2_evaluate_family_1() -> None:
    """run_s2.py:170, baseline == BASELINE_ALWAYS_LONG -> != (evaluate_family)."""
    ep = _ep("2019-06-03", 1)
    state = _empty_state()
    state["membership"]["P04"]["counted"][5] = [ep]
    key = episode_identity(ep)
    occ = {"outcomes": {(key, 5): _ok(0.05)}, "trailing": {key: 1}}
    ev = evaluate_family(
        "P04", state, occ, 5, "TRAIN", BASELINE_ALWAYS_LONG, None
    )
    assert ev["rows"][0]["direction"] == 1
    assert ev["rows"][0]["hit"] == 1


def test_mut5d_run_s2_evaluate_family_2() -> None:
    """run_s2.py:157, retired: bool = False -> True (evaluate_family default)."""
    ep = _ep("2019-06-03", 1)
    state = _empty_state()
    state["membership"]["P04"]["counted"][5] = [ep]
    key = episode_identity(ep)
    occ = {"outcomes": {(key, 5): _ok(0.05)}, "trailing": {}}
    ev = evaluate_family(
        "P04", state, occ, 5, "TRAIN", BASELINE_ALWAYS_LONG, None
    )
    assert ev["rows"][0]["outcome_state"] != RETIRED_TOKEN
    assert ev["rows"][0]["excess"] == 0.05


# ---------------------------------------------------------------------------
# refuse_data_path
# ---------------------------------------------------------------------------


def test_mut5d_run_s2_refuse_data_path_1(tmp_path: Path) -> None:
    """run_s2.py:102, SystemExit(2) -> SystemExit(3) (refuse_data_path)."""
    data = tmp_path / "data"
    data.mkdir()
    nested = data / "trial_ledger.jsonl"
    with pytest.raises(SystemExit) as ei:
        refuse_data_path(tmp_path, nested)
    assert ei.value.code == 2


def test_mut5d_run_s2_refuse_data_path_2(tmp_path: Path) -> None:
    """run_s2.py:98, resolved == repo_data or repo_data in parents -> and."""
    data = tmp_path / "data"
    data.mkdir()
    nested = data / "trial_ledger.jsonl"
    with pytest.raises(SystemExit) as ei:
        refuse_data_path(tmp_path, nested)
    assert ei.value.code == 2


def test_mut5d_run_s2_refuse_data_path_3(tmp_path: Path) -> None:
    """run_s2.py:98, resolved == repo_data -> != (refuse_data_path)."""
    (tmp_path / "data").mkdir()
    ledger = tmp_path / "trial_ledger.jsonl"
    refuse_data_path(tmp_path, ledger)


# ---------------------------------------------------------------------------
# build_block
# ---------------------------------------------------------------------------


def test_mut5d_run_s2_build_block_1() -> None:
    """run_s2.py:325, r['hit'] or 0 -> or 1 (build_block TESTED hits)."""
    block = _tested_block()
    assert block["family_row"]["abstention_state"] == "TESTED"
    assert block["test"]["hits"] == 100
    assert block["test"]["n"] == 153


def test_mut5d_run_s2_build_block_2() -> None:
    """run_s2.py:314, split_label(...) == split -> != (build_block split_eps)."""
    ep = _ep("2019-06-03", 1)
    state = _empty_state()
    state["membership"]["P04"]["counted"][5] = [ep]
    key = episode_identity(ep)
    occ = {"outcomes": {(key, 5): _ok(0.05)}, "trailing": {}}
    block = build_block("P04", state, occ, 5, "TRAIN", _ledger(), [], {})
    assert block["family_row"]["event_count"] == 1


def test_mut5d_run_s2_build_block_3() -> None:
    """run_s2.py:325, r['hit'] or 0 -> and 0 (build_block TESTED hits)."""
    block = _tested_block()
    assert block["family_row"]["abstention_state"] == "TESTED"
    assert block["test"]["hits"] == 100
    assert block["test"]["n"] == 153


# ---------------------------------------------------------------------------
# pooled_prior
# ---------------------------------------------------------------------------


def test_mut5d_run_s2_pooled_prior_1() -> None:
    """run_s2.py:277, mean_ex = sum(excesses) / len(excesses) -> *."""
    e1, e2 = _ep("2019-03-01", 1), _ep("2019-06-03", 2)
    state = _empty_state()
    state["membership"]["P04"]["counted"][5] = [e1, e2]
    k1, k2 = episode_identity(e1), episode_identity(e2)
    occ = {
        "outcomes": {(k1, 5): _ok(0.10), (k2, 5): _ok(0.30)},
        "trailing": {},
    }
    direction, token = pooled_prior(state, occ, 5)
    assert direction == 1
    assert "+0.200000" in token


def test_mut5d_run_s2_pooled_prior_2() -> None:
    """run_s2.py:274, len(set(clusters)) < MIN_TRAIN_CLUSTERS_POOLED_PRIOR -> <=."""
    e1, e2 = _ep("2019-03-01", 1), _ep("2019-06-03", 2)
    state = _empty_state()
    state["membership"]["P04"]["counted"][5] = [e1, e2]
    k1, k2 = episode_identity(e1), episode_identity(e2)
    occ = {
        "outcomes": {(k1, 5): _ok(0.10), (k2, 5): _ok(0.30)},
        "trailing": {},
    }
    direction, token = pooled_prior(state, occ, 5)
    assert direction is not None
    assert token.startswith("direction")
