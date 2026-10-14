"""PLNT display packet, the first consumer-visible Cyclical signal.

The packet is the projection lead and ``advertising_net_change`` from the
committed synthetic fixture. ``filing_claim`` stays false. A fact marked
``native_admitted`` true raises a Cyclical-owned refusal and returns no
packet. The shared-contract probe is recorded as ``unavailable`` or
``present`` and is not asked to certify the packet as a filing.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from engine.sector_intelligence.consumer_cyclical_display import (
    ConsumerCyclicalDisplayRefusal,
    display_packet,
)
from engine.sector_intelligence.consumer_cyclical_projection import (
    _DEFINITION_CONTRADICTED,
    project_economic_change,
)
from engine.sector_intelligence.consumer_cyclical_shared_contract import (
    ConsumerCyclicalResearchRefusal,
    shared_contract,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = (
    REPO_ROOT
    / "data"
    / "sector_intelligence"
    / "fixtures"
    / "consumer_cyclical_intelligence_read_model.v1.valid.json"
)
PROJECTION_PATH = (
    REPO_ROOT
    / "engine"
    / "sector_intelligence"
    / "consumer_cyclical_projection.py"
)
DISPLAY_PATH = (
    REPO_ROOT
    / "engine"
    / "sector_intelligence"
    / "consumer_cyclical_display.py"
)


def _committed_synthetic_case() -> dict:
    """The committed fixture's case fields, not a hand-built PLNT accession."""
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {
        "subject": fixture["subject"],
        "comparison_basis": fixture["comparison_basis"],
        "facts": fixture["facts"],
        "generated_at": fixture["generated_at"],
        "source_records": fixture["source_records"],
    }


def _import_targets(tree: ast.AST) -> list[str]:
    targets: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                targets.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module:
                targets.append(module)
            for alias in node.names:
                targets.append(f"{module}.{alias.name}" if module else alias.name)
    return targets


def test_synthetic_packet_shows_the_r6_lead_and_refuses_a_filing_claim() -> None:
    case = _committed_synthetic_case()
    projected = project_economic_change(case)
    packet = display_packet(case)
    emitted = {row["key"]: row["value_text"] for row in projected["results"]}
    assert packet["filing_claim"] is False
    assert packet["provenance"] == "synthetic_fixture"
    assert packet["shared_contract_status"] == "unavailable"
    assert packet["advertising_net_change"] == emitted["advertising_net_change"]
    assert packet["advertising_net_change"] == "-4"
    assert packet["lead"] == projected["explanation"]["lead"]
    assert packet["facts"] == projected["facts"]
    assert packet["facts"]
    assert all(fact["native_admitted"] is False for fact in packet["facts"])
    assert packet["availability"] == projected["availability"] == "ready"
    assert packet["advertising_net_change_status"] == "ready"
    assert packet["advertising_net_change_withheld_reason"] is None
    assert set(packet) == {
        "availability",
        "lead",
        "advertising_net_change",
        "advertising_net_change_status",
        "advertising_net_change_withheld_reason",
        "filing_claim",
        "provenance",
        "shared_contract_status",
        "facts",
    }


def _patch_projection(monkeypatch: pytest.MonkeyPatch, document: dict) -> None:
    monkeypatch.setattr(
        "engine.sector_intelligence.consumer_cyclical_display.project_economic_change",
        lambda case: document,
    )


def test_unavailable_document_and_withheld_row_stay_visible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _committed_synthetic_case()
    document = project_economic_change(case)
    rows = [dict(row) for row in document["results"]]
    target = [row for row in rows if row["key"] == "advertising_net_change"]
    assert len(target) == 1
    target[0]["value_text"] = None
    target[0]["withheld_reason"] = _DEFINITION_CONTRADICTED
    _patch_projection(
        monkeypatch, {**document, "results": rows, "availability": "unavailable"}
    )
    packet = display_packet(case)
    assert packet["availability"] == "unavailable"
    assert packet["advertising_net_change"] is None
    assert packet["advertising_net_change_status"] == "withheld"
    assert packet["advertising_net_change_withheld_reason"] == (
        _DEFINITION_CONTRADICTED
    )


def test_absent_row_and_unknown_verdict_read_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _committed_synthetic_case()
    document = project_economic_change(case)
    rows = [
        dict(row)
        for row in document["results"]
        if row["key"] != "advertising_net_change"
    ]
    _patch_projection(monkeypatch, {**document, "results": rows, "availability": "READY"})
    packet = display_packet(case)
    assert packet["availability"] == "unavailable"
    assert packet["advertising_net_change"] is None
    assert packet["advertising_net_change_status"] == "absent"
    assert packet["advertising_net_change_withheld_reason"] is None


def test_native_admitted_true_raises_and_emits_nothing() -> None:
    case = _committed_synthetic_case()
    assert case["facts"]
    assert all(fact["native_admitted"] is False for fact in case["facts"])
    facts = [dict(fact) for fact in case["facts"]]
    facts[0]["native_admitted"] = True
    case["facts"] = facts
    with pytest.raises(ConsumerCyclicalDisplayRefusal) as raised:
        display_packet(case)
    assert raised.value.code == "native_admitted"


def test_absent_contract_records_unavailable_and_keeps_the_lead(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _committed_synthetic_case()
    projected = project_economic_change(case)
    with pytest.raises(ConsumerCyclicalResearchRefusal) as live:
        shared_contract()
    assert live.value.code == "shared_contract_unavailable"
    packet = display_packet(case)
    assert packet["shared_contract_status"] == "unavailable"
    assert packet["lead"] == projected["explanation"]["lead"]
    assert packet["filing_claim"] is False

    calls: list[object] = []

    def validate_assertion(*args: object, **kwargs: object) -> dict:
        calls.append((args, kwargs))
        return {}

    monkeypatch.setattr(
        "engine.sector_intelligence.consumer_cyclical_display.shared_contract",
        lambda: validate_assertion,
    )
    present = display_packet(case)
    assert present["shared_contract_status"] == "present"
    assert present["filing_claim"] is False
    assert present["provenance"] == "synthetic_fixture"
    assert present["lead"] == projected["explanation"]["lead"]
    assert calls == []


def test_projection_does_not_import_the_display() -> None:
    projection_tree = ast.parse(PROJECTION_PATH.read_text(encoding="utf-8"))
    projection_imports = _import_targets(projection_tree)
    assert not any(
        "consumer_cyclical_display" in name for name in projection_imports
    ), projection_imports

    display_tree = ast.parse(DISPLAY_PATH.read_text(encoding="utf-8"))
    display_imports = _import_targets(display_tree)
    assert any(
        name == "engine.sector_intelligence.consumer_cyclical_projection"
        or name.endswith(".project_economic_change")
        for name in display_imports
    ), display_imports
    assert any(
        name == "engine.sector_intelligence.consumer_cyclical_shared_contract"
        or name.endswith(".shared_contract")
        for name in display_imports
    ), display_imports
    banned = (
        "engine.theme_graph.store",
        "semiconductor_theme_research",
        "VerticalRegistration",
    )
    leaked = [name for name in display_imports if any(item in name for item in banned)]
    assert leaked == []
    for node in ast.walk(display_tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        called = func.id if isinstance(func, ast.Name) else (
            func.attr if isinstance(func, ast.Attribute) else ""
        )
        assert called != "VerticalRegistration"
