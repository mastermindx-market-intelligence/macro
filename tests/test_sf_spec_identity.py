"""Construction identity and lossless legacy screening: no provider calls."""
import copy
import hashlib
import json
import subprocess
from pathlib import Path

import pytest
from engine.signal_foundry.spec import construction_hash
from engine.signal_foundry.screen import screen_candidate


def candidate():
    return {"id": "SF-9901", "name": "Identity fixture alpha", "market": "US fixture",
            "thesis": "Synthetic identity test", "mechanism": "Earlier public observation",
            "data": [{"path": "data/a.csv", "column": "value", "pit": "known at release"}],
            "feature": {"pipeline": [["zscore", {"window": 252}]]},
            "target": {"path": "data/target.csv", "kind": "absolute_return", "horizon_d": 21},
            "universe": "single_series", "baseline": "buy_and_hold",
            "gates": {"min_t_hac": 2.0, "fdr_q": 0.1, "dsr": 0.9},
            "registered_at": "2026-09-16", "history_years": 8, "pit": "clean",
            "orthogonality_note": "Distinct construction", "evidence_note": "Synthetic fixture"}


def legacy_hash(s):
    t = s.get("target", {})
    payload = {"market": s.get("market", ""), "pipeline": s.get("feature", {}).get("pipeline", []),
               "target_path": t.get("path", ""), "target_kind": t.get("kind", ""),
               "target_horizon_d": t.get("horizon_d"), "universe": s.get("universe", "")}
    return hashlib.sha1(json.dumps(payload, sort_keys=True, default=str,
                                    separators=(",", ":")).encode()).hexdigest()[:20]


@pytest.mark.parametrize("dimension", ["input_path", "input_column", "availability", "input_order",
                                       "target_column", "baseline", "target_threshold"])
def test_identity_changes_when_computation_input_changes(dimension):
    a = candidate(); b = copy.deepcopy(a)
    if dimension == "input_path": b["data"][0]["path"] = "data/b.csv"
    elif dimension == "input_column": b["data"][0]["column"] = "other"
    elif dimension == "availability": b["data"][0]["pit"] = "released one month later"
    elif dimension == "input_order":
        a["data"].append({"path": "data/b.csv", "column": "value", "pit": "known"})
        b["data"] = list(reversed(a["data"]))
    elif dimension == "target_column": b["target"]["column"] = "adjusted_close"
    elif dimension == "target_threshold": b["target"]["threshold"] = -0.05
    else: b["baseline"] = "sma_200"
    assert construction_hash(a) != construction_hash(b)


def test_default_target_column_and_optional_defaults_have_one_identity():
    a = candidate(); b = copy.deepcopy(a)
    a.pop("baseline"); a.pop("universe")
    b["target"]["column"] = "Close"
    assert construction_hash(a) == construction_hash(b)


def test_identity_ignores_prose_and_gate_retuning_is_not_novelty():
    a = candidate(); b = copy.deepcopy(a)
    b.update(name="Renamed", id="SF-9910", thesis="New words", status="tested",
             construction_hash="spoofed", construction_hash_version=123,
             gates={"min_t_hac": 0.1, "fdr_q": 0.9, "dsr": 0.1})
    assert construction_hash(a) == construction_hash(b)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), object()])
def test_noncanonical_values_are_not_stringified_into_identity(bad):
    s = candidate(); s["feature"]["pipeline"][0][1]["window"] = bad
    with pytest.raises((ValueError, TypeError)):
        construction_hash(s)


@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "data/signal_foundry").mkdir(parents=True)
    (tmp_path / "config").mkdir()
    (tmp_path / "config/signal_foundry_blocklist.yml").write_text("entries: []\n")
    for name in ("a.csv", "b.csv", "target.csv"):
        (tmp_path / "data" / name).write_text("date,value\n2000-01-01,1\n2008-01-01,2\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "data", "config"], check=True)
    return tmp_path


def save_prior(repo, row):
    p = repo / "data/signal_foundry/candidates.jsonl"
    p.write_text(json.dumps(row) + "\n")
    return p


def test_full_legacy_record_still_rejects_identical_construction(repo):
    s = candidate(); old = dict(s, construction_hash=legacy_hash(s), status="tested")
    p = save_prior(repo, old); before = p.read_bytes()
    out = screen_candidate(dict(s, name="Renamed idea"), repo_root=repo)
    assert not out["admit"] and "novelty" in out["gates_failed"]
    assert out.get("construction_hash_version") == 2
    assert p.read_bytes() == before


def test_full_legacy_collision_does_not_reject_different_inputs(repo):
    a = candidate(); b = copy.deepcopy(a); b["data"][0]["path"] = "data/b.csv"
    assert legacy_hash(a) == legacy_hash(b)
    save_prior(repo, dict(a, construction_hash=legacy_hash(a), status="tested"))
    out = screen_candidate(b, repo_root=repo)
    assert out["admit"], out


def test_legacy_proposed_record_without_hash_still_prevents_duplicate(repo):
    save_prior(repo, dict(candidate(), status="proposed"))
    out = screen_candidate(dict(candidate(), name="Renamed legacy"), repo_root=repo)
    assert not out["admit"] and "novelty" in out["gates_failed"]


def test_opaque_legacy_collision_is_uncertain_not_automatically_new(repo):
    s = candidate()
    save_prior(repo, {"id":"SF-0001", "construction_hash":legacy_hash(s), "status":"tested"})
    out = screen_candidate(s, repo_root=repo)
    assert not out["admit"] and "novelty" in out["gates_failed"]
    assert any("incomplete" in x.lower() for x in out["reasons"])


@pytest.mark.parametrize("contents", ['{broken json\n', '[]\n'])
def test_corrupt_prior_registry_cannot_silently_admit(repo, contents):
    (repo / "data/signal_foundry/candidates.jsonl").write_text(contents)
    out = screen_candidate(candidate(), repo_root=repo)
    assert not out["admit"] and "novelty" in out["gates_failed"]


def test_hash_failure_is_a_rejection_not_a_missing_dedup_check(repo):
    s = candidate(); s["target"]["metadata"] = object()
    out = screen_candidate(s, repo_root=repo)
    assert not out["admit"] and "novelty" in out["gates_failed"]


def test_brainstorm_filer_overwrites_spoof_and_rejects_same_batch_rename(repo):
    from scripts.run_signal_foundry_brainstorm import _file_specs
    s = dict(candidate(), construction_hash="invented", construction_hash_version=999)
    duplicate = dict(s, id="SF-9902", name="Same definition renamed")
    p = repo / "data/signal_foundry/candidates.jsonl"
    accepted, rejected = _file_specs([s, duplicate], p, repo, "2026-W38", False)
    assert (accepted, rejected) == (1, 1)
    rows = [json.loads(x) for x in p.read_text().splitlines()]
    assert all(x["construction_hash_version"] == 2 for x in rows)
    assert all(x["construction_hash"] == construction_hash(s) for x in rows)
    assert rows[1]["data"] == s["data"]


def test_codex_filing_helper_uses_backend_identity_without_provider(repo):
    from scripts.codex_signal_lane import _file_specs
    s = dict(candidate(), construction_hash="invented", construction_hash_version=999)
    p = repo / "data/signal_foundry/candidates.jsonl"
    accepted, rejected, ids = _file_specs([s], p, repo, "2026-W38", False)
    assert (accepted, rejected) == (1, 0)
    saved = json.loads(p.read_text().splitlines()[0])
    assert saved["construction_hash_version"] == 2
    assert saved["construction_hash"] == construction_hash(s)


@pytest.mark.parametrize("filer", ["brainstorm", "codex"])
def test_malformed_rejection_cannot_poison_future_novelty(repo, filer):
    if filer == "brainstorm":
        from scripts.run_signal_foundry_brainstorm import _file_specs
    else:
        from scripts.codex_signal_lane import _file_specs
    bad = candidate()
    bad["feature"]["pipeline"][0][1]["window"] = float("nan")
    p = repo / "data/signal_foundry/candidates.jsonl"
    out = _file_specs([bad], p, repo, "2026-W38", False)
    assert out[:2] == (0, 1)
    saved = json.loads(p.read_text())
    assert saved["status"] == "screen_rejected"
    assert "NaN" not in p.read_text()
    assert "construction_hash" not in saved
    assert saved.get("identity_error")
    good = dict(candidate(), id="SF-9902", name="Subsequent valid definition")
    screened = screen_candidate(good, repo_root=repo)
    assert screened["admit"], screened


def test_stored_v2_identity_disagreement_is_not_silently_repaired(repo):
    save_prior(repo, dict(candidate(), construction_hash="0" * 20,
                         construction_hash_version=2, status="tested"))
    out = screen_candidate(candidate(), repo_root=repo)
    assert not out["admit"] and "novelty" in out["gates_failed"]
    assert any("disagrees" in x for x in out["reasons"])


def test_nested_nonstring_keys_cannot_alias_string_keys():
    s = candidate(); s["target"]["metadata"] = {1: "x"}
    with pytest.raises(TypeError):
        construction_hash(s)


def test_identity_suite_is_in_existing_causal_factory_ci():
    import yaml
    root = Path(__file__).resolve().parents[1]
    jobs = yaml.safe_load((root / ".github/ci/legacy-jobs.yml").read_text())["jobs"]
    commands = "\n".join(str(x.get("run", "")) for x in jobs["causal-factory"]["steps"])
    assert "tests/test_sf_spec_identity.py" in commands


def test_codex_rejected_definition_retains_backend_identity(repo):
    from scripts.codex_signal_lane import _file_specs
    s = candidate(); s["orthogonality_note"] = ""
    p = repo / "data/signal_foundry/candidates.jsonl"
    out = _file_specs([s], p, repo, "2026-W38", False)
    assert out[:2] == (0, 1)
    saved = json.loads(p.read_text())
    assert saved["construction_hash_version"] == 2
    assert saved["construction_hash"] == construction_hash(s)
    assert saved["data"] == s["data"]
