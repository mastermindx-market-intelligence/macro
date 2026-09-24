from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "ops/inference-host/ubuntu/inference_guard.py"
SPEC = importlib.util.spec_from_file_location("inference_guard", PATH)
GUARD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(GUARD)


def test_admission_refuses_low_host_memory(monkeypatch, tmp_path):
    cg = tmp_path / "ci"
    cg.mkdir()
    (cg / "memory.current").write_text("1")
    (cg / "memory.high").write_text("100")
    (cg / "memory.max").write_text("200")
    monkeypatch.setattr(GUARD, "_mem_available", lambda: 10)
    monkeypatch.setattr(GUARD, "_other_gpu_mib", lambda: (0, None))
    state = GUARD.admission(cgroup=cg, min_mem_available=11)
    assert not state["ok"]
    assert "host_memory_low" in state["reasons"]


def test_admission_refuses_ci_at_memory_high(monkeypatch, tmp_path):
    cg = tmp_path / "ci"
    cg.mkdir()
    (cg / "memory.current").write_text("100")
    (cg / "memory.high").write_text("100")
    (cg / "memory.max").write_text("200")
    monkeypatch.setattr(GUARD, "_mem_available", lambda: 1000)
    monkeypatch.setattr(GUARD, "_other_gpu_mib", lambda: (0, None))
    state = GUARD.admission(cgroup=cg, min_mem_available=11)
    assert not state["ok"]
    assert "ci_memory_high" in state["reasons"]


def test_admission_refuses_other_gpu_compute(monkeypatch, tmp_path):
    cg = tmp_path / "ci"
    cg.mkdir()
    (cg / "memory.current").write_text("1")
    (cg / "memory.high").write_text("100")
    (cg / "memory.max").write_text("200")
    monkeypatch.setattr(GUARD, "_mem_available", lambda: 1000)
    monkeypatch.setattr(GUARD, "_other_gpu_mib", lambda: (513, None))
    state = GUARD.admission(cgroup=cg, min_mem_available=11, max_other_gpu_mib=512)
    assert not state["ok"]
    assert "gpu_busy_other_workload" in state["reasons"]


def test_admission_accepts_bounded_idle_host(monkeypatch, tmp_path):
    cg = tmp_path / "ci"
    cg.mkdir()
    (cg / "memory.current").write_text("10")
    (cg / "memory.high").write_text("100")
    (cg / "memory.max").write_text("200")
    monkeypatch.setattr(GUARD, "_mem_available", lambda: 1000)
    monkeypatch.setattr(GUARD, "_other_gpu_mib", lambda: (0, None))
    state = GUARD.admission(cgroup=cg, min_mem_available=11)
    assert state["ok"]
    assert state["reasons"] == []


def test_unload_only_targets_pinned_model(monkeypatch):
    calls = []
    monkeypatch.setattr(GUARD.subprocess, "run", lambda argv, **kwargs: calls.append(argv))
    GUARD._unload("other-model", "/usr/local/bin/ollama")
    assert calls == []
    GUARD._unload(GUARD.DEFAULT_MODEL, "/usr/local/bin/ollama")
    assert calls == [["/usr/local/bin/ollama", "stop", GUARD.DEFAULT_MODEL]]
