"""Durability ratchets for the Chairman C2 ruling and provider-free C3 successor."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1] / "agentos"
WORKSTREAM = ROOT / "workstreams/WS-AGENT-EVAL-FABRIC.md"
HANDOFF = ROOT / "handoffs/AGENT-EVAL-FABRIC-2026-09-19.md"
DECISION = ROOT / "decisions/DEC-AGENT-EVAL-C2-CHAIRMAN-RULING.md"

HEAD = "33d77c3fa94b9b8127d5a08974da9033091c6137"
MERGE = "db4ef921c1e9a1abd790197d2719ba5316fbf99e"
PROTECTED = "3e66e43258f34db240d5bff76f54148c7af84ee4"


def _record(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8").split("---", 2)[1])


def test_c2_ruling_is_durable_without_claiming_historical_execution() -> None:
    current = _record(WORKSTREAM)
    waves = {row["id"]: row for row in current["waves"]}
    assert waves["C2"]["status"] == "done"
    assert "immutable" in waves["C2"]["next_action"]
    assert "unexecuted" in waves["C2"]["next_action"]
    assert "retired as an executable experiment" in waves["C2"]["next_action"]
    assert "DEC:AGENT-EVAL-C2-CHAIRMAN-RULING" in current["decisions"]
    decision = _record(DECISION)
    assert decision["decided_by"] == "chairman"
    assert "No provider experiment may run" in decision["answer"]
    evidence = " ".join(decision["evidence"])
    assert MERGE in evidence
    assert PROTECTED in evidence


def test_c3_uses_protected_contracts_but_requires_a_real_episode() -> None:
    current = _record(WORKSTREAM)
    waves = {row["id"]: row for row in current["waves"]}
    c3 = waves["C3"]
    assert c3["status"] == "in_progress"
    assert c3["pr"] == 871
    assert HEAD in c3["next_action"]
    assert MERGE in c3["next_action"]
    assert PROTECTED in c3["next_action"]
    assert "BUILT_NOT_PROVEN" in c3["next_action"]
    assert "real provider-free H1/H2 episode" in c3["next_action"]
    assert "accepted paired evidence" in c3["next_action"]
    assert "merge queue" not in c3["next_action"]
    assert "Mastermind #871 exact head" in " ".join(current["do_not_redo"])
    objective = current["objective"]
    assert "No ranking, routing, trading, promotion, or execution authority" in objective


def test_forward_dependencies_use_c3_not_retired_c2() -> None:
    waves = {row["id"]: row for row in _record(WORKSTREAM)["waves"]}
    for wave_id in ("F1", "G1"):
        assert "C3" in waves[wave_id]["depends_on"]
        assert "C2" not in waves[wave_id]["depends_on"]


def test_latest_handoff_names_protected_contract_boundary_and_d1_no_effect() -> None:
    handoff = _record(HANDOFF)
    actions = " ".join(handoff["next_actions"])
    assert MERGE in actions
    assert PROTECTED in actions
    assert "real provider-free H1/H2 episode" in actions
    assert "d79d2ec3537d8eb060055731a7c3cebee0c543eb" in actions
    assert "READ/A0" in actions
    assert any(
        row["claim"] == "Mastermind #871 is merged and protected."
        for row in handoff["verified"]
    )
    assert any(
        row["claim"] == "C3 has produced a real provider-free H1/H2 episode."
        for row in handoff["unverified"]
    )
    do_not_redo = " ".join(handoff["do_not_redo"])
    for settled in ("Mastermind #162", "Mastermind #692", "Mastermind #841", "Macro #7344"):
        assert settled in do_not_redo
    assert "EFFECT_UNKNOWN" in do_not_redo
    assert "Do not bypass the merge queue" not in do_not_redo
