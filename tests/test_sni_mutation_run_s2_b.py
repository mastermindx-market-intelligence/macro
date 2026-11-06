"""MUT5E killing tests for run_s2.py (owned range generate_outputs..EOF).

SNI-local DRAFT contract tests. They consume owner-supplied opaque identity
strings (Stock Identity / Data OS) and never mint issuer or security ids.
HISTORICAL-DESCRIPTIVE only: rank_authority, gate_authority, size_authority,
signal_authority, escalation_authority and trade_authority stay false.
Fixtures are synthetic. Residuals and event-study numbers are descriptive,
never causal, never a news-impact claim. An unestimable family ABSTAINS.

Each test_mut5e_run_s2_<function>_<n> docstring names the surviving mutant
from the 2026-10-13 sweep (seed 20261013).
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research/single_name_intelligence/event_response"))

import run_s2  # noqa: E402
from run_s2 import (  # noqa: E402
    AUTHORITY_FLAGS_FALSE,
    SPLITS,
    _fmt,
    build_version_record,
    generate_outputs,
    main,
    render_observations,
    render_report,
    run_check,
)
from s2_seal import GRADE_HORIZONS, PROTOCOLS  # noqa: E402


def _assert_flags_false(flags: dict) -> None:
    for k in ("rank_authority", "gate_authority", "size_authority",
              "signal_authority", "escalation_authority", "trade_authority"):
        assert flags[k] is False


def _synth_state() -> dict:
    mem = {}
    for pid in PROTOCOLS:
        mem[pid] = {
            "counted": {h: [] for h in GRADE_HORIZONS},
            "sha_table": {
                str(h): {sp: "0" * 64 for sp in SPLITS} for h in GRADE_HORIZONS
            },
            "count_table": {
                str(h): {sp: 0 for sp in SPLITS} for h in GRADE_HORIZONS
            },
            "lines_by_h": {h: [] for h in GRADE_HORIZONS},
        }
    return {
        "membership": mem,
        "collapse": {"counts": {"excluded_and_listed": []}},
        "programmes": {},
        "event_exclusions": {},
        "class_summary": {"count_per_category": {}},
        "vocab": {},
        "prereg_membership_table": [],
    }


def _cell_block() -> dict:
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


def _empty_results() -> dict:
    return {
        pid: {
            "title": pid,
            "splits": {
                **{sp: {f"h{h}": _cell_block() for h in GRADE_HORIZONS}
                   for sp in SPLITS},
                "TEST": "none (prospective only; REG §2 registration gate not met)",
            },
        }
        for pid in PROTOCOLS
    }


def _install_generate_outputs_stubs(monkeypatch) -> None:
    class _FakeEngine:
        def __init__(self, _loader) -> None:
            self.last_bar_date = dt.date(2024, 1, 2)

    monkeypatch.setattr(run_s2, "verify_pinned_blobs", lambda *a, **k: None)
    monkeypatch.setattr(run_s2, "compute_state", lambda _loader: _synth_state())
    monkeypatch.setattr(run_s2, "prereg_digest_of", lambda _s: "d" * 64)
    monkeypatch.setattr(run_s2, "verify_seal", lambda *a, **k: None)
    monkeypatch.setattr(run_s2, "OutcomeEngine", _FakeEngine)
    monkeypatch.setattr(
        run_s2, "base_commit_detected_at",
        lambda *_a, **_k: "2024-01-02T00:00:00+00:00")
    monkeypatch.setattr(
        run_s2, "maybe_log_retirement",
        lambda _led, pid, *_a, **_k: {"protocol_id": pid, "state": "ok"})
    monkeypatch.setattr(
        run_s2, "compute_outcomes",
        lambda *_a, **_k: {"outcomes": {}, "trailing": {}})
    monkeypatch.setattr(
        run_s2, "evaluate_family",
        lambda *_a, **_k: {"summary": {"PRIMARY": {}}})
    monkeypatch.setattr(
        run_s2, "abstention_state", lambda _p: "ABSTAIN_NO_EPISODES")
    monkeypatch.setattr(run_s2, "build_block", lambda *_a, **_k: _cell_block())
    monkeypatch.setattr(run_s2, "render_observations", lambda *_a, **_k: [])
    monkeypatch.setattr(
        run_s2, "build_version_record",
        lambda *_a, **_k: {
            "descriptive_only": True,
            "defects": {},
            "authority_flags": dict(AUTHORITY_FLAGS_FALSE),
        })
    monkeypatch.setattr(run_s2, "render_report", lambda *_a, **_k: "synthetic\n")


def _prep_v1_tree(tmp_path: Path, digest: str, sha: str) -> tuple[dict, dict]:
    seal_dir = tmp_path / "research/single_name_intelligence/runs/s2_event_response"
    seal_dir.mkdir(parents=True)
    rows = []
    membership: dict = {}
    for pid in PROTOCOLS:
        sha_table: dict = {}
        for h in GRADE_HORIZONS:
            sha_table[str(h)] = {}
            for split in SPLITS:
                sha_table[str(h)][split] = sha
                rows.append({
                    "protocol_id": pid,
                    "horizon": h,
                    "split": split,
                    "membership_sha256": sha,
                    "count": 0,
                })
        membership[pid] = {"sha_table": sha_table}
    (seal_dir / "SEAL_AND_BUDGET.json").write_text(
        json.dumps({"prereg_digest_sha256": digest, "membership_table": rows}),
        encoding="utf-8")
    state = {"prereg_digest_sha256": digest, "membership": membership}
    results: dict = {}
    for pid in PROTOCOLS:
        splits: dict = {}
        for split in SPLITS:
            splits[split] = {
                f"h{h}": {"family_row": {"abstention_state": "ABSTAIN_NO_EPISODES"}}
                for h in GRADE_HORIZONS
            }
        results[pid] = {"splits": splits}
    return state, results


_CHECK_RELS = (
    "REPORT.md", "LANE_MANIFEST.json", "VERSION_RECORD.json",
    "results/P04.json", "results/P05.json", "results/P06.json",
    "observations/episodes.jsonl",
)


def _write_check_tree(root: Path, report: str = "ok-report\n") -> None:
    for rel in _CHECK_RELS:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if rel.endswith(".json"):
            p.write_text(json.dumps({"synthetic": rel}) + "\n", encoding="utf-8")
        elif rel.endswith(".jsonl"):
            p.write_text('{"synthetic": true}\n', encoding="utf-8")
        else:
            p.write_text(report, encoding="utf-8")
    (root / "trial_ledger.jsonl").write_text(
        json.dumps({"ts": "2024-01-02T00:00:00+00:00", "n": 1}) + "\n",
        encoding="utf-8")


def _fake_generate_copy(seal_dir: Path, report: str | None = None):
    def _gen(_repo, _ref, out_dir, ledger_path, _seal):
        for rel in _CHECK_RELS:
            src = seal_dir / rel
            dst = out_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            data = src.read_bytes()
            if report is not None and rel == "REPORT.md":
                data = report.encode("utf-8")
            dst.write_bytes(data)
        ledger_path.write_bytes((seal_dir / "trial_ledger.jsonl").read_bytes())
    return _gen


# ---------------------------------------------------------------------------
# generate_outputs
# ---------------------------------------------------------------------------


def test_mut5e_run_s2_generate_outputs_1(tmp_path: Path, monkeypatch) -> None:
    """run_s2.py:589, indent=2 -> 3 (results json.dumps)."""
    _install_generate_outputs_stubs(monkeypatch)
    out = tmp_path / "o"
    generate_outputs(tmp_path, "synthetic-ref", out,
                     tmp_path / "ledger.jsonl", tmp_path / "seal")
    text = (out / "results" / "P04.json").read_text(encoding="utf-8")
    first = text.splitlines()[1]
    assert first.startswith("  \""), first
    assert not first.startswith("   \""), first
    flags = json.loads(text)["authority_flags"]
    _assert_flags_false(flags)


def test_mut5e_run_s2_generate_outputs_2(tmp_path: Path, monkeypatch) -> None:
    """run_s2.py:626, ensure_ascii=False -> True (LANE_MANIFEST json.dumps)."""
    _install_generate_outputs_stubs(monkeypatch)
    seen: list[bool | None] = []
    orig = run_s2.json.dumps

    def spy(obj, *a, **k):
        if isinstance(obj, dict) and "lane" in obj and "census_only" in obj:
            seen.append(k.get("ensure_ascii"))
        return orig(obj, *a, **k)

    monkeypatch.setattr(run_s2.json, "dumps", spy)
    out = tmp_path / "o"
    generate_outputs(tmp_path, "synthetic-ref", out,
                     tmp_path / "ledger.jsonl", tmp_path / "seal")
    assert seen == [False]
    flags = json.loads((out / "LANE_MANIFEST.json").read_text(encoding="utf-8"))[
        "authority_flags"]
    _assert_flags_false(flags)


# ---------------------------------------------------------------------------
# build_version_record
# ---------------------------------------------------------------------------


def test_mut5e_run_s2_build_version_record_1(tmp_path: Path) -> None:
    """run_s2.py:720, digest == v1_digest -> != (prereg_digest_unchanged)."""
    digest = "a" * 64
    sha = "b" * 64
    state, results = _prep_v1_tree(tmp_path, digest, sha)
    rec = build_version_record(tmp_path, state, results)
    assert rec["prereg_digest_unchanged"] is True
    _assert_flags_false(rec["authority_flags"])


def test_mut5e_run_s2_build_version_record_2(tmp_path: Path) -> None:
    """run_s2.py:693, want != got -> == (membership mismatch append)."""
    digest = "a" * 64
    sha = "b" * 64
    state, results = _prep_v1_tree(tmp_path, digest, sha)
    rec = build_version_record(tmp_path, state, results)
    assert rec["membership_sha256_mismatches"] == []
    assert rec["membership_sha256_per_cell"] == "identical to v1"


def test_mut5e_run_s2_build_version_record_3(tmp_path: Path) -> None:
    """run_s2.py:734, descriptive_only True -> False."""
    digest = "a" * 64
    sha = "b" * 64
    state, results = _prep_v1_tree(tmp_path, digest, sha)
    rec = build_version_record(tmp_path, state, results)
    assert rec["descriptive_only"] is True


# ---------------------------------------------------------------------------
# _fmt
# ---------------------------------------------------------------------------


def test_mut5e_run_s2__fmt_1() -> None:
    """run_s2.py:747, return f\"{x:+.6f}\" -> return None."""
    assert _fmt(1.5) == "+1.500000"
    assert _fmt(-0.25) == "-0.250000"


def test_mut5e_run_s2__fmt_2() -> None:
    """run_s2.py:748, return str(x) -> return None."""
    assert _fmt(7) == "7"
    assert _fmt("synthetic") == "synthetic"


# ---------------------------------------------------------------------------
# render_report
# ---------------------------------------------------------------------------


def test_mut5e_run_s2_render_report_1() -> None:
    """run_s2.py:922, hit == 1 -> != (baseline episode hit label)."""
    results = _empty_results()
    ep = {
        "episode_key": "SYNTHETIC_KEYXX",
        "s_us": "2020-01-02",
        "excess": 0.1,
        "direction": 1,
        "hit": 1,
        "tie": False,
        "outcome_state": "OK",
    }
    blk = results["P04"]["splits"]["TRAIN"]["h5"]
    blk["baselines"] = {
        "always_long": {
            "label": "baseline (i) always-long (+1)",
            "episodes": [ep],
        }
    }
    retirement = {pid: {"state": "ok"} for pid in PROTOCOLS}
    md = render_report(results, retirement, version_record={})
    assert " → hit" in md


def test_mut5e_run_s2_render_report_2() -> None:
    """run_s2.py:924, episode_key[:12] -> [:13]."""
    results = _empty_results()
    key = "SYNTHETIC_KEYXX"
    ep = {
        "episode_key": key,
        "s_us": "2020-01-02",
        "excess": 0.1,
        "direction": 1,
        "hit": 1,
        "tie": False,
        "outcome_state": "OK",
    }
    blk = results["P04"]["splits"]["TRAIN"]["h5"]
    blk["baselines"] = {
        "always_long": {
            "label": "baseline (i) always-long (+1)",
            "episodes": [ep],
        }
    }
    retirement = {pid: {"state": "ok"} for pid in PROTOCOLS}
    md = render_report(results, retirement, version_record={})
    assert f"episode {key[:12]} s_us" in md
    assert f"episode {key[:13]} s_us" not in md


# ---------------------------------------------------------------------------
# render_observations
# ---------------------------------------------------------------------------


def test_mut5e_run_s2_render_observations_1() -> None:
    """run_s2.py:993, retired_cells or set() -> and (None default)."""
    line = json.dumps({
        "episode_key": "synthetic-ep",
        "issuer_key": "synthetic-issuer",
        "split": "TRAIN",
        "flags": {"census_only": False, "purged": False},
        "cluster_key": "synthetic-cluster",
    }) + "\n"
    state = {
        "membership": {
            pid: {"lines_by_h": {h: [] for h in GRADE_HORIZONS}}
            for pid in PROTOCOLS
        }
    }
    state["membership"]["P04"]["lines_by_h"][5] = [line]
    rows = render_observations(state, {"outcomes": {}}, None)
    assert len(rows) == 1
    assert rows[0]["outcome"]["state"] == "ABSTAIN_MISSING_ENDPOINT"
    assert rows[0]["issuer_key"] == "synthetic-issuer"


# ---------------------------------------------------------------------------
# run_check
# ---------------------------------------------------------------------------


def test_mut5e_run_s2_run_check_1(tmp_path: Path, monkeypatch) -> None:
    """run_s2.py:1081, '+' -> '-' (check-failed print concat)."""
    seal = tmp_path / "seal"
    _write_check_tree(seal, report="seal-report\n")
    monkeypatch.setattr(
        run_s2, "generate_outputs",
        _fake_generate_copy(seal, report="mutated-report\n"))
    rc = run_check(tmp_path, "synthetic-ref", seal)
    assert rc == 1


def test_mut5e_run_s2_run_check_2(tmp_path: Path, monkeypatch) -> None:
    """run_s2.py:1072, tmp / 'trial_ledger.jsonl' -> * (Path join)."""
    seal = tmp_path / "seal"
    _write_check_tree(seal)
    monkeypatch.setattr(run_s2, "generate_outputs", _fake_generate_copy(seal))
    rc = run_check(tmp_path, "synthetic-ref", seal)
    assert rc == 0


def test_mut5e_run_s2_run_check_3(tmp_path: Path, monkeypatch) -> None:
    """run_s2.py:1078, json.dumps(la) != json.dumps(lb) -> ==."""
    seal = tmp_path / "seal"
    _write_check_tree(seal)
    monkeypatch.setattr(run_s2, "generate_outputs", _fake_generate_copy(seal))
    rc = run_check(tmp_path, "synthetic-ref", seal)
    assert rc == 0


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def test_mut5e_run_s2_main_1(tmp_path: Path, monkeypatch) -> None:
    """run_s2.py:1102, text=True -> False (git rev-parse stdout)."""
    monkeypatch.setattr(run_s2, "generate_outputs", lambda *a, **k: None)
    monkeypatch.setattr(sys, "argv", [
        "run_s2.py",
        "--out-dir", str(tmp_path / "o"),
        "--trial-ledger-path", str(tmp_path / "ledger.jsonl"),
    ])
    rc = main()
    assert rc == 0


def test_mut5e_run_s2_main_2(tmp_path: Path, monkeypatch) -> None:
    """run_s2.py:1117, exist_ok=True -> False (out_dir.mkdir)."""
    monkeypatch.setattr(run_s2, "generate_outputs", lambda *a, **k: None)
    out = tmp_path / "o"
    out.mkdir()
    monkeypatch.setattr(sys, "argv", [
        "run_s2.py",
        "--out-dir", str(out),
        "--trial-ledger-path", str(tmp_path / "ledger.jsonl"),
        "--repo-root", str(tmp_path),
    ])
    rc = main()
    assert rc == 0
