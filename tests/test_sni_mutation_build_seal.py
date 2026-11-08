"""Killing tests for MUT4C survivors in residual/build_seal.py and
event_response/build_seal.py.

SNI-local DRAFT contract tests. They consume owner-supplied opaque identity
strings (Stock Identity / Data OS) already present on the seal builders and
never mint issuer or security ids. HISTORICAL-DESCRIPTIVE only:
rank_authority, gate_authority, size_authority, signal_authority,
escalation_authority and trade_authority stay false. Fixtures are synthetic.
These tests do not feed a rank, gate, size, signal, escalation, or trade path.

Each test_mut4c_<module>_<function>_<n> docstring names one non-equivalent
surviving mutant from the 2026-10-13 sweep (seed 20261013).
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import types
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RESIDUAL_DIR = ROOT / "research/single_name_intelligence/residual"
EVENT_DIR = ROOT / "research/single_name_intelligence/event_response"
RESIDUAL_PATH = RESIDUAL_DIR / "build_seal.py"
EVENT_PATH = EVENT_DIR / "build_seal.py"

for _p in (str(ROOT), str(RESIDUAL_DIR), str(EVENT_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _load(name: str, path: Path):
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_residual():
    return _load("sni_mut4c_residual_build_seal", RESIDUAL_PATH)


def _load_event():
    return _load("sni_mut4c_event_response_build_seal", EVENT_PATH)


def _false_authority(mod) -> dict:
    flags = dict(mod.AUTHORITY_FLAGS)
    for key, value in flags.items():
        assert value is False, key
    return flags


class _FakeS1Store:
    def __init__(self, mod, missing_id: bool = False, empty_issuer: bool = False):
        self.pins = {mod.SECURITY_MASTER: "b" * 40}
        self._mod = mod
        self._missing_id = missing_id
        self._empty_issuer = empty_issuer

    def verify_all(self) -> None:
        return None

    def read_columns(self, path, columns):
        ids = list(self._mod.SECURITY_IDS)
        if self._missing_id:
            ids = ids[:2]
        n = len(ids)
        issuers = ["ISS:SYNTH-0", "ISS:SYNTH-1", "ISS:SYNTH-2"][:n]
        if self._empty_issuer and issuers:
            issuers[0] = ""
        return {
            "security_id": ids,
            "issuer_id": issuers,
            "issuer_state": ["RESOLVED"] * n,
            "ingested_at": ["1970-01-01T00:00:00Z"] * n,
        }

    def index_dates(self, path):
        return [date(2020, 1, 2), date(2020, 1, 3)]

    def list_dir(self, prefix):
        return []

    def schema(self, path):
        return ["Date", "close"]

    def rev_parse_ref_path(self, path):
        return "a" * 40


def _stub_s1_build(mod, monkeypatch, *, store=None) -> None:
    store_cls = store or (lambda *a, **k: _FakeS1Store(mod))
    monkeypatch.setattr(mod, "GitBlobStore", store_cls)
    monkeypatch.setattr(
        mod, "build_rows",
        lambda *a, **k: [{"split": "TRAIN"}],
    )
    monkeypatch.setattr(mod, "manifest_bytes", lambda rows: b"{}\n")
    monkeypatch.setattr(
        mod, "split_digests",
        lambda rows: {"TRAIN": {"count": 1, "membership_sha256": "ab"}},
    )
    monkeypatch.setattr(
        mod, "build_universe",
        lambda spy, blob_sha, sessions: {
            "files_examined": 0,
            "admitted_count": 0,
            "admitted": [],
            "rejected_by_reason": {"z_reason": 1, "a_reason": 2},
        },
    )
    monkeypatch.setattr(mod.nyse_calendar, "sessions_between", lambda *a, **k: [])
    monkeypatch.setattr(
        mod, "build_spec",
        lambda: {"authority_flags": _false_authority(mod)},
    )
    monkeypatch.setattr(mod, "prereg_digest", lambda spec: "d" * 64)


def _s1_build_all(mod, monkeypatch, tmp_path, *, nested=False, pre_manifests=False):
    _stub_s1_build(mod, monkeypatch)
    out = tmp_path / "a" / "b" / "s1" if nested else tmp_path / "s1"
    if pre_manifests:
        (out / "manifests").mkdir(parents=True, exist_ok=True)
    return mod.build_all(tmp_path, "SYNTHETIC", out), out


def _residual_md_args(mod):
    seal = {
        "lane": "s1_residual",
        "version": "v1",
        "base": "SYNTHETIC",
        "branch": "SYNTHETIC",
        "input_ref": "SYNTHETIC",
        "prereg_digest_sha256": "aa",
        "trial_ledger_path": "synthetic/trial_ledger.jsonl",
        "labels": ["HISTORICAL-DESCRIPTIVE"],
        "families": {
            "P01": {
                "family": "sni.s1_residual.P01",
                "declared_budget": 6,
                "itemized_count": 6,
                "reg_s8_canonical": "sni.s0.P01",
            },
        },
        "membership_table": [{
            "protocol_id": "P01", "subject": "adr_baba", "h": 5,
            "split": "TRAIN", "count": 1, "membership_sha256": "ab",
        }],
        "seal_builder_audit": {"spy_calls": ["index_dates"], "index_only": True},
        "authority_flags": _false_authority(mod),
        "outcome_free": True,
    }
    manifests = {"P01_adr_baba_5.jsonl": {"digests": {"TRAIN": {"count": 1}}}}
    universe = {
        "files_examined": 0,
        "admitted_count": 0,
        "rejected_by_reason": {"z_reason": 1, "a_reason": 2},
    }
    return seal, manifests, universe


def _run_residual_help() -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    return subprocess.run(
        [sys.executable, str(RESIDUAL_PATH), "--help"],
        cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=30,
    )


def _first_indent(text: str) -> int:
    for line in text.splitlines()[1:]:
        if line.strip():
            return len(line) - len(line.lstrip(" "))
    return -1


def _stub_s2_main(mod, monkeypatch, tmp_path, *, cov_rows=None, census_rows=None,
                  spec=None, nested=False, pre_manifests=False):
    out = tmp_path / "nested" / "s2" if nested else tmp_path / "s2"
    if pre_manifests:
        (out / "manifests").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(mod, "GitBlobLoader", lambda *a, **k: object())
    monkeypatch.setattr(mod, "verify_pinned_blobs", lambda *a, **k: None)
    collapse = {"counts": {
        "literal_row_count_pre_step0": 1,
        "kept_after_step0": 1,
        "events_after_step2": 1,
        "events_after_step2_and_step3": 1,
        "excluded_and_listed": [],
    }}
    membership = {
        pid: {"lines_by_h": {h: [] for h in mod.GRADE_HORIZONS}, "table_rows": []}
        for pid in mod.PROTOCOLS
    }
    state = {
        "collapse": collapse,
        "membership": membership,
        "event_rows": [],
        "earning_rows": [],
        "selected": [],
        "programmes": [],
        "census_rows": census_rows or [],
        "coverage_reports": {"stub": True},
    }
    monkeypatch.setattr(mod, "compute_state", lambda loader: state)
    monkeypatch.setattr(
        mod, "enrich_membership_rows_with_graded",
        lambda rows, lines: list(rows),
    )
    monkeypatch.setattr(
        mod, "coverage_census_rows",
        lambda reports: list(cov_rows or []),
    )
    spec_obj = spec if spec is not None else {
        "note": "— synthetic",
        "authority_flags": _false_authority(mod),
    }
    run_s2 = types.ModuleType("run_s2")
    run_s2.full_spec_digest = lambda st: (spec_obj, "d" * 64)
    monkeypatch.setitem(sys.modules, "run_s2", run_s2)
    monkeypatch.setattr(sys, "argv", [
        "build_seal.py",
        "--out-dir", str(out),
        "--repo-root", str(tmp_path),
        "--input-ref", "SYNTHETIC",
    ])
    return out, collapse


def _s2_render_args(mod):
    seal = {
        "lane": "s2_event_response",
        "version": "v1.1",
        "base_commit": "SYNTHETIC",
        "branch": "SYNTHETIC",
        "input_ref": "SYNTHETIC",
        "outcome_free": True,
        "families": [{
            "protocol_id": "P04",
            "family": "results",
            "ledger_family": "sni.s2_event_response.P04",
            "reg_canonical_family": "sni.s0.P04",
            "declared_budget": 6,
            "itemized_grid_size": 12,
        }],
        "not_supported_in_s2": [{"protocol_id": "P07", "line": "x"}],
        "graded_cohort": {
            "issuer_group": "alibaba",
            "graded_leg": "adr_baba",
            "census_only": ["tencent only"],
        },
        "membership_table": [{
            "protocol_id": "P04",
            "horizon": 5,
            "split": "TRAIN",
            "count": 1,
            "membership_sha256": "deadbeef",
            "graded_membership_sha256": "cafebabe",
            "graded_membership_count": 1,
            "census_only_count": 0,
        }],
        "prereg_digest_sha256": "aa",
        "authority_flags": _false_authority(mod),
    }
    collapse = {"counts": {
        "literal_row_count_pre_step0": 0,
        "kept_after_step0": 0,
        "events_after_step2": 0,
        "events_after_step2_and_step3": 0,
        "excluded_and_listed": [],
    }}
    return seal, collapse


# ---------------------------------------------------------------------------
# residual/build_seal.py
# ---------------------------------------------------------------------------


def test_mut4c_residual_build_seal_module_1():
    """residual/build_seal.py:44, + -> - (PROTOCOL_SUBJECTS P03 concat)."""
    mod = _load_residual()
    assert mod.PROTOCOL_SUBJECTS["P03"] == mod.SUBJECTS["P01"] + mod.SUBJECTS["P02"]


def test_mut4c_residual_build_seal_module_2():
    """residual/build_seal.py:25, 3 -> 4 (sys.path parents index)."""
    src = RESIDUAL_PATH.read_text(encoding="utf-8")
    assert "parents[3]" in src


def test_mut4c_residual_build_seal_module_3():
    """residual/build_seal.py:272, == -> != (`if __name__ == "__main__"`)."""
    proc = _run_residual_help()
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "--input-ref" in proc.stdout


def test_mut4c_residual_build_seal_module_4():
    """residual/build_seal.py:272, delete `if __name__ == "__main__": raise SystemExit`."""
    proc = _run_residual_help()
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "--input-ref" in proc.stdout


def test_mut4c_residual_build_seal__runs_rel_1(tmp_path):
    """residual/build_seal.py:184, return relative path -> None."""
    mod = _load_residual()
    out = tmp_path / "research" / "runs"
    out.mkdir(parents=True)
    got = mod._runs_rel(tmp_path, out)
    assert isinstance(got, str)
    assert got.replace("\\", "/").endswith("research/runs")


def test_mut4c_residual_build_seal__runs_rel_2(tmp_path):
    """residual/build_seal.py:186, return RUNS_REL -> None (outside repo_root)."""
    mod = _load_residual()
    repo = tmp_path / "repo"
    other = tmp_path / "other"
    repo.mkdir()
    other.mkdir()
    got = mod._runs_rel(repo, other)
    assert got == mod.RUNS_REL


def test_mut4c_residual_build_seal_identity_facts_1():
    """residual/build_seal.py:67, delete missing-security_id RuntimeError."""
    mod = _load_residual()
    store = _FakeS1Store(mod, missing_id=True)
    with pytest.raises(RuntimeError, match="security_master has no row"):
        mod.identity_facts(store)


def test_mut4c_residual_build_seal_identity_facts_2():
    """residual/build_seal.py:61, `and` -> `or` (empty issuer -> UNRESOLVED)."""
    mod = _load_residual()
    store = _FakeS1Store(mod, empty_issuer=True)
    facts = mod.identity_facts(store)
    sid = mod.SECURITY_IDS[0]
    assert facts[sid]["canonical_issuer_id"] == "UNRESOLVED"


def test_mut4c_residual_build_seal_identity_facts_3():
    """residual/build_seal.py:69, `return out` -> `return None`."""
    mod = _load_residual()
    facts = mod.identity_facts(_FakeS1Store(mod))
    assert isinstance(facts, dict)
    assert set(facts) == set(mod.SECURITY_IDS)


def test_mut4c_residual_build_seal_write_json_1(tmp_path):
    """residual/build_seal.py:190, canonical_json(obj) + newline -> minus."""
    mod = _load_residual()
    path = tmp_path / "x.json"
    mod.write_json(path, {"k": 1})
    text = path.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert json.loads(text) == {"k": 1}


def test_mut4c_residual_build_seal_render_seal_md_1():
    """residual/build_seal.py:237, json.dumps sort_keys True -> False."""
    mod = _load_residual()
    md = mod.render_seal_md(*_residual_md_args(mod))
    dumped = json.dumps({"z_reason": 1, "a_reason": 2}, sort_keys=True)
    assert dumped in md


def test_mut4c_residual_build_seal_render_seal_md_2():
    """residual/build_seal.py:255, return markdown -> None."""
    mod = _load_residual()
    md = mod.render_seal_md(*_residual_md_args(mod))
    assert isinstance(md, str)
    assert md.startswith("# SEAL_AND_BUDGET")


def test_mut4c_residual_build_seal_render_seal_md_3():
    """residual/build_seal.py:255, join(L) + newline -> minus."""
    mod = _load_residual()
    md = mod.render_seal_md(*_residual_md_args(mod))
    assert md.endswith("\n")


def test_mut4c_residual_build_seal_main_1(monkeypatch):
    """residual/build_seal.py:260, argparse --input-ref required True -> False."""
    mod = _load_residual()
    monkeypatch.setattr(mod, "build_all", lambda *a, **k: {
        "seal": {"membership_table": []},
        "digest": "a" * 64,
        "manifests": {},
        "universe": {"admitted_count": 0},
    })
    monkeypatch.setattr(sys, "argv", ["build_seal.py"])
    with pytest.raises(SystemExit):
        mod.main()


def test_mut4c_residual_build_seal_main_2(monkeypatch, tmp_path):
    """residual/build_seal.py:269, `return 0` -> `return None`."""
    mod = _load_residual()
    monkeypatch.setattr(mod, "build_all", lambda *a, **k: {
        "seal": {"membership_table": []},
        "digest": "a" * 64,
        "manifests": {},
        "universe": {"admitted_count": 0},
    })
    monkeypatch.setattr(sys, "argv", [
        "build_seal.py", "--input-ref", "SYNTHETIC", "--out-dir", str(tmp_path),
    ])
    assert mod.main() == 0


def test_mut4c_residual_build_seal_main_3(monkeypatch, tmp_path):
    """residual/build_seal.py:269, `return 0` -> `return 1`."""
    mod = _load_residual()
    monkeypatch.setattr(mod, "build_all", lambda *a, **k: {
        "seal": {"membership_table": []},
        "digest": "a" * 64,
        "manifests": {},
        "universe": {"admitted_count": 0},
    })
    monkeypatch.setattr(sys, "argv", [
        "build_seal.py", "--input-ref", "SYNTHETIC", "--out-dir", str(tmp_path),
    ])
    assert mod.main() == 0


def test_mut4c_residual_build_seal_main_4(monkeypatch, tmp_path, capsys):
    """residual/build_seal.py:266, digest[:12] -> digest[:13]."""
    mod = _load_residual()
    monkeypatch.setattr(mod, "build_all", lambda *a, **k: {
        "seal": {"membership_table": []},
        "digest": "0123456789abcdef",
        "manifests": {},
        "universe": {"admitted_count": 0},
    })
    monkeypatch.setattr(sys, "argv", [
        "build_seal.py", "--input-ref", "SYNTHETIC", "--out-dir", str(tmp_path),
    ])
    assert mod.main() == 0
    text = capsys.readouterr().out
    assert "0123456789ab…" in text
    assert "0123456789abc" not in text


def test_mut4c_residual_build_seal_build_all_1(monkeypatch, tmp_path):
    """residual/build_seal.py:122, mkdir exist_ok True -> False."""
    mod = _load_residual()
    _stub_s1_build(mod, monkeypatch)
    out = tmp_path / "s1"
    out.mkdir()
    res = mod.build_all(tmp_path, "SYNTHETIC", out)
    assert (out / "SEAL_AND_BUDGET.json").is_file()
    assert res["seal"]["outcome_free"] is True
    assert res["seal"]["authority_flags"]["rank"] is False


def test_mut4c_residual_build_seal_build_all_2(monkeypatch, tmp_path):
    """residual/build_seal.py:170, out_dir / "manifests" -> * (inner Path div)."""
    mod = _load_residual()
    res, out = _s1_build_all(mod, monkeypatch, tmp_path)
    assert any((out / "manifests").glob("*.jsonl"))
    assert res["seal"]["authority_flags"]["trade"] is False


def test_mut4c_residual_build_seal_build_all_3(monkeypatch, tmp_path):
    """residual/build_seal.py:167, out_dir / INPUT_MANIFEST.json -> *."""
    mod = _load_residual()
    _s1_build_all(mod, monkeypatch, tmp_path)
    assert (tmp_path / "s1" / "INPUT_MANIFEST.json").is_file()


def test_mut4c_residual_build_seal_build_all_4(monkeypatch, tmp_path):
    """residual/build_seal.py:123, manifests mkdir exist_ok True -> False."""
    mod = _load_residual()
    res, out = _s1_build_all(mod, monkeypatch, tmp_path, pre_manifests=True)
    assert (out / "SEAL_AND_BUDGET.json").is_file()
    assert res["digest"] == "d" * 64


def test_mut4c_residual_build_seal_build_all_5(monkeypatch, tmp_path):
    """residual/build_seal.py:123, out_dir / "manifests" -> *."""
    mod = _load_residual()
    _s1_build_all(mod, monkeypatch, tmp_path)
    assert (tmp_path / "s1" / "manifests").is_dir()


def test_mut4c_residual_build_seal_build_all_6(monkeypatch, tmp_path):
    """residual/build_seal.py:151, P02 itemized_count 12 -> 13."""
    mod = _load_residual()
    res, _out = _s1_build_all(mod, monkeypatch, tmp_path)
    assert res["seal"]["families"]["P02"]["itemized_count"] == 12


def test_mut4c_residual_build_seal_build_all_7(monkeypatch, tmp_path):
    """residual/build_seal.py:153, P03 itemized_count 21 -> 22."""
    mod = _load_residual()
    res, _out = _s1_build_all(mod, monkeypatch, tmp_path)
    assert res["seal"]["families"]["P03"]["itemized_count"] == 21


def test_mut4c_residual_build_seal_build_all_8(monkeypatch, tmp_path):
    """residual/build_seal.py:168, out_dir / CHALLENGER_UNIVERSE.json -> *."""
    mod = _load_residual()
    _s1_build_all(mod, monkeypatch, tmp_path)
    assert (tmp_path / "s1" / "CHALLENGER_UNIVERSE.json").is_file()


def test_mut4c_residual_build_seal_build_all_9(monkeypatch, tmp_path):
    """residual/build_seal.py:166, out_dir / PREREG_SPEC.json -> *."""
    mod = _load_residual()
    _s1_build_all(mod, monkeypatch, tmp_path)
    assert (tmp_path / "s1" / "PREREG_SPEC.json").is_file()


def test_mut4c_residual_build_seal_build_all_10(monkeypatch, tmp_path):
    """residual/build_seal.py:170, manifests / name -> * (outer Path div)."""
    mod = _load_residual()
    res, out = _s1_build_all(mod, monkeypatch, tmp_path)
    written = list((out / "manifests").glob("*.jsonl"))
    assert written
    assert res["manifests"]


def test_mut4c_residual_build_seal_build_all_11(monkeypatch, tmp_path):
    """residual/build_seal.py:149, P01 itemized_count 6 -> 7."""
    mod = _load_residual()
    res, _out = _s1_build_all(mod, monkeypatch, tmp_path)
    assert res["seal"]["families"]["P01"]["itemized_count"] == 6


def test_mut4c_residual_build_seal_build_all_12(monkeypatch, tmp_path):
    """residual/build_seal.py:150, P02 declared_budget 4 -> 5."""
    mod = _load_residual()
    res, _out = _s1_build_all(mod, monkeypatch, tmp_path)
    assert res["seal"]["families"]["P02"]["declared_budget"] == 4
    assert res["seal"]["authority_flags"]["signal"] is False


# ---------------------------------------------------------------------------
# event_response/build_seal.py
# ---------------------------------------------------------------------------


def test_mut4c_event_response_build_seal_render_seal_md_1():
    """event_response/build_seal.py:203, membership_sha256 `or` -> `and`."""
    mod = _load_event()
    md = mod.render_seal_md(*_s2_render_args(mod))
    assert "deadbeef" in md


def test_mut4c_event_response_build_seal_render_seal_md_2():
    """event_response/build_seal.py:251, return markdown -> None."""
    mod = _load_event()
    md = mod.render_seal_md(*_s2_render_args(mod))
    assert isinstance(md, str)
    assert md.startswith("# S2 SEAL_AND_BUDGET")


def test_mut4c_event_response_build_seal_render_seal_md_3():
    """event_response/build_seal.py:251, join(lines) + newline -> minus."""
    mod = _load_event()
    md = mod.render_seal_md(*_s2_render_args(mod))
    assert md.endswith("\n")


def test_mut4c_event_response_build_seal_render_seal_md_4():
    """event_response/build_seal.py:204, graded_membership_sha256 `or` -> `and`."""
    mod = _load_event()
    md = mod.render_seal_md(*_s2_render_args(mod))
    assert "cafebabe" in md


def test_mut4c_event_response_build_seal_render_seal_md_5():
    """event_response/build_seal.py:167, json.dumps AUTHORITY_FLAGS sort_keys True -> False."""
    mod = _load_event()
    md = mod.render_seal_md(*_s2_render_args(mod))
    dumped = json.dumps(mod.AUTHORITY_FLAGS, sort_keys=True)
    assert dumped in md
    assert md.find("escalation_authority") < md.find("rank_authority")


def test_mut4c_event_response_build_seal_main_1(monkeypatch, tmp_path):
    """event_response/build_seal.py:65, manifests / filename -> * (outer Path div)."""
    mod = _load_event()
    out, _c = _stub_s2_main(mod, monkeypatch, tmp_path)
    assert mod.main() == 0
    assert (out / "manifests" / "P04_h5.jsonl").is_file()


def test_mut4c_event_response_build_seal_main_2(monkeypatch, tmp_path):
    """event_response/build_seal.py:125, SEAL json ensure_ascii False -> True."""
    mod = _load_event()
    out, _c = _stub_s2_main(mod, monkeypatch, tmp_path)
    assert mod.main() == 0
    text = (out / "SEAL_AND_BUDGET.json").read_text(encoding="utf-8")
    assert "—" in text
    assert "\\u2014" not in text
    seal = json.loads(text)
    assert seal["authority_flags"]["trade_authority"] is False


def test_mut4c_event_response_build_seal_main_3(monkeypatch, tmp_path):
    """event_response/build_seal.py:136, EVENT_CENSUS indent 2 -> 3."""
    mod = _load_event()
    out, _c = _stub_s2_main(mod, monkeypatch, tmp_path)
    assert mod.main() == 0
    text = (out / "EVENT_CENSUS.json").read_text(encoding="utf-8")
    assert _first_indent(text) == 2


def test_mut4c_event_response_build_seal_main_4(monkeypatch, tmp_path):
    """event_response/build_seal.py:132, out / EVENT_CENSUS.json -> *."""
    mod = _load_event()
    out, _c = _stub_s2_main(mod, monkeypatch, tmp_path)
    assert mod.main() == 0
    assert (out / "EVENT_CENSUS.json").is_file()


def test_mut4c_event_response_build_seal_main_5(monkeypatch, tmp_path):
    """event_response/build_seal.py:139, E_COVERAGE json + newline -> minus."""
    mod = _load_event()
    out, _c = _stub_s2_main(mod, monkeypatch, tmp_path)
    assert mod.main() == 0
    text = (out / "E_COVERAGE_CENSUS.json").read_text(encoding="utf-8")
    assert text.endswith("\n")


def test_mut4c_event_response_build_seal_main_6(monkeypatch, tmp_path):
    """event_response/build_seal.py:131, INPUT_MANIFEST indent 2 -> 3."""
    mod = _load_event()
    out, _c = _stub_s2_main(mod, monkeypatch, tmp_path)
    assert mod.main() == 0
    text = (out / "INPUT_MANIFEST.json").read_text(encoding="utf-8")
    assert _first_indent(text) == 2


def test_mut4c_event_response_build_seal_main_7(monkeypatch, tmp_path):
    """event_response/build_seal.py:133, EVENT_CENSUS json + newline -> minus."""
    mod = _load_event()
    out, _c = _stub_s2_main(mod, monkeypatch, tmp_path)
    assert mod.main() == 0
    text = (out / "EVENT_CENSUS.json").read_text(encoding="utf-8")
    assert text.endswith("\n")


def test_mut4c_event_response_build_seal_main_8(monkeypatch, tmp_path):
    """event_response/build_seal.py:125, SEAL json indent 2 -> 3."""
    mod = _load_event()
    out, _c = _stub_s2_main(mod, monkeypatch, tmp_path)
    assert mod.main() == 0
    text = (out / "SEAL_AND_BUDGET.json").read_text(encoding="utf-8")
    assert _first_indent(text) == 2


def test_mut4c_event_response_build_seal_main_9(monkeypatch, tmp_path):
    """event_response/build_seal.py:84, outcome_free True -> False."""
    mod = _load_event()
    out, _c = _stub_s2_main(mod, monkeypatch, tmp_path)
    assert mod.main() == 0
    seal = json.loads((out / "SEAL_AND_BUDGET.json").read_text(encoding="utf-8"))
    assert seal["outcome_free"] is True


def test_mut4c_event_response_build_seal_main_10(monkeypatch, tmp_path):
    """event_response/build_seal.py:143, issuer_key == iss -> !=."""
    mod = _load_event()
    cov = [
        {"issuer_key": "alibaba", "state": "OK"},
        {"issuer_key": "tencent", "state": "GAP"},
    ]
    out, _c = _stub_s2_main(mod, monkeypatch, tmp_path, cov_rows=cov)
    assert mod.main() == 0
    payload = json.loads((out / "E_COVERAGE_CENSUS.json").read_text(encoding="utf-8"))
    assert payload["counts"]["alibaba"] == {"OK": 1}
    assert payload["counts"]["tencent"] == {"GAP": 1}


def test_mut4c_event_response_build_seal_main_11(monkeypatch, tmp_path):
    """event_response/build_seal.py:128, out / INPUT_MANIFEST.json -> *."""
    mod = _load_event()
    out, _c = _stub_s2_main(mod, monkeypatch, tmp_path)
    assert mod.main() == 0
    assert (out / "INPUT_MANIFEST.json").is_file()


def test_mut4c_event_response_build_seal_main_12(monkeypatch, tmp_path):
    """event_response/build_seal.py:127, PREREG json + newline -> minus."""
    mod = _load_event()
    out, _c = _stub_s2_main(mod, monkeypatch, tmp_path)
    assert mod.main() == 0
    text = (out / "PREREG_SPEC.json").read_text(encoding="utf-8")
    assert text.endswith("\n")


def test_mut4c_event_response_build_seal_main_13(monkeypatch, tmp_path):
    """event_response/build_seal.py:129, INPUT_MANIFEST json + newline -> minus."""
    mod = _load_event()
    out, _c = _stub_s2_main(mod, monkeypatch, tmp_path)
    assert mod.main() == 0
    text = (out / "INPUT_MANIFEST.json").read_text(encoding="utf-8")
    assert text.endswith("\n")


def test_mut4c_event_response_build_seal_main_14(monkeypatch, tmp_path):
    """event_response/build_seal.py:97, itemized_grid_size 12 -> 13."""
    mod = _load_event()
    out, _c = _stub_s2_main(mod, monkeypatch, tmp_path)
    assert mod.main() == 0
    seal = json.loads((out / "SEAL_AND_BUDGET.json").read_text(encoding="utf-8"))
    assert {row["itemized_grid_size"] for row in seal["families"]} == {12}


def test_mut4c_event_response_build_seal_main_15(monkeypatch, tmp_path):
    """event_response/build_seal.py:127, PREREG ensure_ascii False -> True."""
    mod = _load_event()
    out, _c = _stub_s2_main(mod, monkeypatch, tmp_path)
    assert mod.main() == 0
    text = (out / "PREREG_SPEC.json").read_text(encoding="utf-8")
    assert "—" in text
    assert "\\u2014" not in text


def test_mut4c_event_response_build_seal_main_16(monkeypatch, tmp_path):
    """event_response/build_seal.py:53, mkdir parents True -> False."""
    mod = _load_event()
    out, _c = _stub_s2_main(mod, monkeypatch, tmp_path, nested=True)
    assert mod.main() == 0
    assert (out / "SEAL_AND_BUDGET.json").is_file()


def test_mut4c_event_response_build_seal_main_17(monkeypatch, tmp_path):
    """event_response/build_seal.py:154, `return 0` -> `return None`."""
    mod = _load_event()
    _stub_s2_main(mod, monkeypatch, tmp_path)
    assert mod.main() == 0


def test_mut4c_event_response_build_seal_main_18(monkeypatch, tmp_path):
    """event_response/build_seal.py:53, out / "manifests" -> *."""
    mod = _load_event()
    out, _c = _stub_s2_main(mod, monkeypatch, tmp_path)
    assert mod.main() == 0
    assert (out / "manifests").is_dir()


def test_mut4c_event_response_build_seal_main_19(monkeypatch, tmp_path):
    """event_response/build_seal.py:53, mkdir exist_ok True -> False."""
    mod = _load_event()
    out, _c = _stub_s2_main(mod, monkeypatch, tmp_path, pre_manifests=True)
    assert mod.main() == 0
    assert (out / "SEAL_AND_BUDGET.md").is_file()
