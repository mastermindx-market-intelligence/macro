"""Bounded contextual-only mode (market_memory_only) of the Research Factory runner.

The runner must emit exactly the installed real-owner market-memory evidence
attachment and nothing else: no candidate load, no registered filtering, no
registered routing, no transition, no count, no disk write.  Uses the existing
synthetic admitted fixture (real owner, registered current binding) and traps
the registered path; no fabricated capabilities.
"""
import json

import pytest

from engine.neuralweb import market_memory_retained_use as use

from engine.research_factory import adapter_market_memory as old
from engine.research_factory import adapter_market_memory_evidence as mm_evidence
from engine.research_factory import schema
from scripts import research_factory_run as runner
from tests.test_research_factory_market_memory_evidence import (
    REGISTERED,
    admitted,
    original,
    files,
)


def _trap_registered_path(monkeypatch):
    monkeypatch.setattr(runner, "load_candidates",
                        lambda *a, **k: pytest.fail("contextual-only mode loaded candidates"))
    monkeypatch.setattr(runner, "filter_registered",
                        lambda *a, **k: pytest.fail("contextual-only mode filtered candidates"))
    monkeypatch.setattr(runner, "_route_candidate",
                        lambda *a, **k: pytest.fail("contextual-only mode routed a registered candidate"))
    monkeypatch.setattr(runner, "_perform_transition",
                        lambda *a, **k: pytest.fail("contextual-only mode attempted a transition"))


def test_contextual_only_emits_one_real_citation_without_candidate_work(admitted, monkeypatch):
    root, binding, request, _ = admitted
    before = files(root)
    _trap_registered_path(monkeypatch)
    summary = runner.run(rf_dir=root / "rf", data_dir=root / "data", dry_run=True,
                         count=False, market_memory_inputs=(request,),
                         market_memory_only=True)

    assert summary["mode"] == "market_memory_only"
    assert summary["dry_run"] is True
    assert summary["count"] is False
    assert summary["effective_count"] is False
    assert summary["n_candidates"] == summary["n_registered"] == 0
    assert summary["transitions_attempted"] == summary["transitions_ok"] == 0

    assert len(summary["contextual_evidence"]) == 1
    value = summary["contextual_evidence"][0]
    assert schema.validate_market_memory_evidence_attachment(value) == []
    assert value["attachment_id"].startswith("mmrfevidence_")
    assert value["trial_binding"]["binding_id"] == binding["binding_id"]
    assert value["candidate"] == old.build_market_memory_candidate(
        exact_trial_registration_bytes=request.exact_trial_registration_bytes,
        created_at=REGISTERED)
    assert value["contextual_retrieval_join"]["denominator"]["returned"] == 2
    assert len(value["real_evidence_join"]["source_cards"]) == 3
    assert not any(v for v in value["lifecycle"].values() if type(v) is bool)

    assert len(summary["routes"]) == 1
    route = summary["routes"][0]
    assert route["candidate_id"] == value["candidate"]["candidate_id"]
    assert route["source"] == "market_memory"
    assert route["domain"] == "market_memory"
    assert route["action"] == "no_action"
    assert route["reason"] == "contextual_evidence_only"
    assert route["projected_state"] == "proposed"
    assert route["transition_ok"] is None
    assert route["attachment_id"] == value["attachment_id"]

    assert files(root) == before


def test_invalid_contextual_only_mode_rejected_before_private_reads(admitted, monkeypatch):
    root, _, request, _ = admitted
    _trap_registered_path(monkeypatch)
    monkeypatch.setattr(
        mm_evidence, "build_market_memory_evidence_attachment",
        lambda *a, **k: pytest.fail("invalid contextual-only mode reached private evidence build"))

    with pytest.raises(ValueError, match="market_memory_only"):
        runner.run(rf_dir=root / "rf", data_dir=root / "data", dry_run=False, count=False,
                   market_memory_inputs=(request,), market_memory_only=True)
    with pytest.raises(ValueError, match="market_memory_only"):
        runner.run(rf_dir=root / "rf", data_dir=root / "data", dry_run=True, count=True,
                   market_memory_inputs=(request,), market_memory_only=True)
    with pytest.raises(ValueError, match="market_memory_only"):
        runner.run(rf_dir=root / "rf", data_dir=root / "data", dry_run=True, count=False,
                   market_memory_inputs=(), market_memory_only=True)
    with pytest.raises(ValueError, match="at_most_one_typed"):
        runner.run(rf_dir=root / "rf", data_dir=root / "data", dry_run=True, count=False,
                   market_memory_inputs=(request, request), market_memory_only=True)
    with pytest.raises(ValueError, match="market_memory_only"):
        runner.run(rf_dir=root / "rf", data_dir=root / "data", dry_run=True, count=False,
                   market_memory_inputs=(request,), market_memory_only="yes")
    with pytest.raises(ValueError, match="market_memory_only"):
        runner.run(rf_dir=root / "rf", data_dir=root / "data", dry_run=True, count=False,
                   market_memory_inputs=(request,), market_memory_only=1)


def test_cli_contextual_only_emits_citation_without_candidate_load(admitted, monkeypatch, capsys):
    root, binding, _, _ = admitted
    monkeypatch.setattr(runner, "ROOT", root)
    _trap_registered_path(monkeypatch)
    assert runner.main(["--market-memory-only", "--market-memory-binding", binding["binding_id"],
                        "--data-dir", str(root / "none")]) == 0
    output = capsys.readouterr().out
    assert "mmrfevidence_" in output
    assert '"transitions_attempted": 0' in output
    assert '"transitions_ok": 0' in output
    assert "[DRY-RUN] No writes performed." in output


def test_cli_contextual_only_rejects_invalid_combos_before_binding_load(admitted, monkeypatch, capsys):
    root, binding, _, _ = admitted
    monkeypatch.setattr(runner, "ROOT", root)
    monkeypatch.setattr(mm_evidence, "load_registered_factory_evidence",
                        lambda *a, **k: pytest.fail("rejected CLI mode loaded binding/private data"))
    for argv in (
        ["--market-memory-only"],
        ["--market-memory-only", "--execute",
         "--market-memory-binding", binding["binding_id"]],
        ["--market-memory-only", "--count",
         "--market-memory-binding", binding["binding_id"]],
        ["--market-memory-only", "--execute", "--count",
         "--market-memory-binding", binding["binding_id"]],
    ):
        with pytest.raises(SystemExit) as excinfo:
            runner.main([*argv, "--data-dir", str(root / "none")])
        assert excinfo.value.code == 2
    capsys.readouterr()


def test_default_mode_unchanged_and_still_loads_candidates(admitted, monkeypatch):
    root, _, request, _ = admitted
    real_load = runner.load_candidates
    seen = {}

    def spy(rf_dir):
        seen["loaded"] = True
        return real_load(rf_dir)

    monkeypatch.setattr(runner, "load_candidates", spy)
    summary = runner.run(rf_dir=root / "rf", data_dir=root / "data", dry_run=True, count=False)
    assert seen.get("loaded") is True
    assert "mode" not in summary
    assert "contextual_evidence" not in summary
    assert summary["n_candidates"] == summary["n_registered"] == 0
    assert summary["routes"] == []
    assert summary["transitions_attempted"] == summary["transitions_ok"] == 0
    assert summary["dry_run"] is True
    assert summary["count"] is False
    assert summary["effective_count"] is False

    # Explicit market_memory_only=False keeps the existing evidence+summary path.
    summary2 = runner.run(rf_dir=root / "rf", data_dir=root / "data", dry_run=True,
                          count=False, market_memory_inputs=(request,),
                          market_memory_only=False)
    assert "mode" not in summary2
    assert len(summary2["contextual_evidence"]) == 1
    assert summary2["transitions_attempted"] == summary2["transitions_ok"] == 0
    assert len(summary2["routes"]) == 1
    assert summary2["routes"][0]["reason"] == "contextual_evidence_only"


def test_contextual_only_rechecks_current_policy_before_final_return(admitted, monkeypatch):
    root, _, request, _ = admitted
    _trap_registered_path(monkeypatch)
    real_disclose = mm_evidence.disclose_market_memory_evidence_attachment
    calls = []

    def revoke_after_first(capability):
        value = real_disclose(capability)
        calls.append(value["attachment_id"])
        if len(calls) == 1:
            p = root / use.REGISTRATION
            current = json.loads(p.read_text())
            current["service_consumers"][use.FACTORY_CONSUMER]["enabled"] = False
            p.write_text(json.dumps(current))
        return value

    monkeypatch.setattr(mm_evidence, "disclose_market_memory_evidence_attachment", revoke_after_first)
    with pytest.raises(use.RetainedUseError):
        runner.run(rf_dir=root / "rf", data_dir=root / "data", dry_run=True,
                   count=False, market_memory_inputs=(request,), market_memory_only=True)
    assert len(calls) == 1
