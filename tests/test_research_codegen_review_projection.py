import json
import sys

import pytest

from engine.research_codegen.bridge import BridgeRefused
from engine.research_factory.review_queue import build_queue
from scripts import build_research_factory_review_queue as builder
from tests.test_research_codegen_bridge import make_case, persist


def test_joined_queue_and_real_builder_never_offer_decision(tmp_path, monkeypatch):
    run, commission = make_case(tmp_path, monkeypatch)
    binding, _ = persist(run, commission)
    rf = tmp_path / "factory"
    rf.mkdir()
    kwargs = dict(trusted_codegen_artifacts=(binding,), synthetic_commission=commission)
    packets = build_queue(rf, **kwargs)
    assert len(packets) == 1 and packets[0]["allowed_decisions"] == []
    assert packets[0]["current_status"] == "unregistered_synthetic_diagnostic"
    markdown = builder.render_markdown(packets, "2010-07-01")
    assert "Candidates awaiting decision: 0" in markdown
    assert "Synthetic research diagnostics" in markdown
    assert "NO_QUALIFIED_PROCEDURE" in markdown
    assert "--decision" not in markdown and "To record a decision" not in markdown
    monkeypatch.setattr(sys, "argv", ["build", "--rf-dir", str(rf), "--write"])
    assert builder.main(**kwargs) == 0
    payload = json.loads((rf / "review/queue.json").read_text())
    assert payload["n_candidates"] == 0 and payload["n_research_diagnostics"] == 1
    assert not (rf / "candidates.jsonl").exists()


def test_missing_commission_refuses_before_legacy_queue_read(tmp_path, monkeypatch):
    run, commission = make_case(tmp_path, monkeypatch)
    binding, _ = persist(run, commission)
    from engine.research_factory import review_queue
    monkeypatch.setattr(review_queue, "_load_jsonl", lambda *a: pytest.fail("read before binding admission"))
    with pytest.raises(BridgeRefused, match="PRODUCTION_DISABLED"):
        build_queue(tmp_path, trusted_codegen_artifacts=(binding,))


def test_default_legacy_queue_does_not_import_bridge(tmp_path, monkeypatch):
    import builtins
    original_import = builtins.__import__
    def blocked(name, *args, **kwargs):
        if name == 'engine.research_codegen.bridge':
            pytest.fail('default legacy queue imported bridge')
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', blocked)
    assert build_queue(tmp_path) == []
