"""Companion publication tests: real VM and main, hermetic inputs, no live services."""
from copy import deepcopy
from pathlib import Path
import json

import pytest

from scripts import build_macro_context as m


def inputs():
    snapshot = {
        "schema": "macro_snapshot.v1", "asof": "2026-10-17", "oldest_component_asof": "2026-10-14",
        "macro_context_id": "same-snapshot-id", "display_only": True,
        "labels": {"bonds": {"bond_health_label": "healthy", "bond_cycle_phase": "recession",
                            "bond_duration_bucket": "lean_long", "bond_curve_lean": "neutral"},
                   "transmission": {"yield_curve_regime": "positive", "recession_risk": "low"}},
        "sources": {"data/bonds/bond_health.json": "2026-10-16", "data/transmission/latest.json": "2026-10-16"},
        "gaps": [],
    }
    world = {
        "rates_credit": {"as_of": "2026-10-16", "health_label": "stressed", "cycle_phase": "late",
                         "bond_compass": {"duration": {"bucket": "neutral"}, "curve_trade": {"lean": "flat", "slope_10y3m": 0.91}},
                         "fed_path": {"policy_rate": 0, "implied_bp_12m": 74},
                         "drivers_for": {"equities": {"hy_oas": 3.16, "credit_canary": True, "stock_bond_corr": 0},
                                         "forex": {"real_10y": 2.88, "term_premium": 1.0729}}},
        "cross_asset_flows": {"asof": "2026-10-17", "regime": "mixed", "funding_state": "calm", "stale": False,
                              "confirm": {"verdict": "mixed"}},
        "produced_at": "2026-10-18T07:03:19Z", "inputs_hash": "upstream-declared-id",
    }
    regime = {"asof": "2026-10-16", "conditions": {"stale_inputs": [], "vintages": {
        "hy_oas": {"asof": "2026-10-13", "age_days": 3, "stale": False, "cadence_days": 5},
        "ebp": {"asof": "2026-09-01", "age_days": 45, "stale": False, "cadence_days": 70},
    }}}
    return snapshot, world, regime, []


def publication(values=None, today="2026-10-18", built="2026-10-18T11:00:00Z"):
    snapshot, world, regime, changes = values or inputs()
    vm = {"asof": (snapshot or {}).get("asof", today), "macro_context_id": (snapshot or {}).get("macro_context_id", ""),
          "n_transitions_14d": len(changes), "headline_en": "Context", "headline_zh": "背景",
          "decision_workspaces": m._build_decision_workspaces(snapshot, world, regime, changes, today)}
    return m._build_decision_publication(vm, snapshot, world, regime, changes, today, built)


@pytest.mark.parametrize("missing", [False, True])
def test_main_publishes_same_vm_and_preserves_five_key_hub(tmp_path, monkeypatch, missing):
    data = tmp_path / "data"
    if not missing:
        for path, obj in zip(("macro_snapshots/latest.json", "neuralweb/world_state.json", "regime/latest.json"), inputs()[:3]):
            target = data / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(obj))
    seen = {}
    class Template:
        def render(self, **kwargs):
            seen["vm"] = kwargs["vm"]
            return "<html>hermetic render boundary</html>"
    class Environment:
        def __init__(self, **kwargs):
            self.globals = {}
        def get_template(self, name):
            assert name == "macro_context.html.j2"
            return Template()
    monkeypatch.setattr(m.config, "ROOT", tmp_path)
    monkeypatch.setattr(m.config, "data_dir", lambda: data)
    monkeypatch.setattr(m.config, "load", lambda: {"storage": {"site_dir": "site"}})
    monkeypatch.setattr(m, "Environment", Environment)
    monkeypatch.setattr(m, "write_page", lambda path, html: seen.update(page=str(path)))
    original = m._build_decision_workspaces
    calls = []
    def select(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)
    monkeypatch.setattr(m, "_build_decision_workspaces", select)
    assert m.main() == 0
    hub = json.loads((data / "macro_context/latest.json").read_text())
    result = json.loads((data / "macro_context/decision_workspaces.json").read_text())
    assert len(calls) == 1
    assert set(hub) == {"asof", "macro_context_id", "n_transitions_14d", "headline_en", "headline_zh"}
    assert hub == result["hub"]
    assert result["decision_workspaces"] == seen["vm"]["decision_workspaces"]
    assert result["display_only"] is True
    if missing:
        assert result["decision_workspaces"]["bonds"]["status"] == "unavailable"
        assert result["publication"]["component_clocks"]["snapshot"]["asof"] is None
        assert result["publication"]["input_fingerprints"]["snapshot"]["loaded_state"] == "absent_or_unreadable"


def test_build_time_is_separate_from_content_and_interpretation_date():
    first = publication()
    later = publication(built="2026-10-18T23:00:00Z")
    next_day = publication(today="2026-10-19", built="2026-10-19T00:00:00Z")
    assert first["publication"]["content_sha256"] == later["publication"]["content_sha256"]
    assert first["publication"]["content_sha256"] != next_day["publication"]["content_sha256"]
    check = deepcopy(first)
    digest = check["publication"].pop("content_sha256")
    check["publication"].pop("built_at")
    assert m._publication_sha256(check) == digest


@pytest.mark.parametrize("dependency", ["world_state", "regime", "transitions"])
def test_same_snapshot_id_does_not_hide_dependency_change(dependency):
    before = publication()
    changed = inputs()
    if dependency == "world_state":
        changed[1]["rates_credit"]["drivers_for"]["equities"]["hy_oas"] = 3.40
    elif dependency == "regime":
        changed[2]["conditions"]["stale_inputs"] = ["hy_oas"]
    else:
        changed[3].append({"asof": "2026-10-16", "domain": "bonds", "field": "bond_health_label", "from": "stressed", "to": "healthy"})
    after = publication(changed)
    assert before["hub"]["macro_context_id"] == after["hub"]["macro_context_id"]
    assert before["publication"]["input_fingerprints"][dependency]["sha256"] != after["publication"]["input_fingerprints"][dependency]["sha256"]
    assert before["publication"]["content_sha256"] != after["publication"]["content_sha256"]


@pytest.mark.parametrize("primary,fallback,selection,selected_path", [
    ("healthy", "stressed", "primary", "labels.bonds.bond_health_label"),
    ("", "stressed", "fallback", "rates_credit.health_label"),
    (None, None, "missing", None),
])
def test_lineage_follows_actual_or_fallback(primary, fallback, selection, selected_path):
    values = inputs()
    values[0]["labels"]["bonds"]["bond_health_label"] = primary
    values[1]["rates_credit"]["health_label"] = fallback
    out = publication(values)
    lineage = out["publication"]["field_lineage"]["bonds"]["current_read.health"]
    assert out["decision_workspaces"]["bonds"]["current_read"]["health"] == (primary or fallback)
    assert lineage["selection"] == selection
    assert lineage["source_path"] == selected_path
    assert lineage["observation_asof"] is None and lineage["available_at"] is None
    if selection != "primary":
        assert lineage["reported_upstream"] is None


def test_numeric_risk_does_not_fill_absent_transmission_label():
    values = inputs()
    values[0]["labels"]["transmission"]["recession_risk"] = None
    values[1]["rates_credit"]["recession_risk"] = 3.7
    out = publication(values)
    assert out["decision_workspaces"]["bonds"]["current_read"]["recession_risk"] is None
    assert out["publication"]["field_lineage"]["bonds"]["current_read.recession_risk"]["selection"] == "missing"


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_is_unavailable_with_distinct_identity_and_zero_preserved(bad):
    values = inputs()
    values[1]["rates_credit"]["drivers_for"]["equities"]["hy_oas"] = bad
    out = publication(values)
    json.dumps(out, allow_nan=False)
    assert out["decision_workspaces"]["bonds"]["transmission"]["equities"]["hy_oas"] is None
    assert out["publication"]["invalid_values"]
    assert out["decision_workspaces"]["bonds"]["mechanism_evidence"]["fed_path"]["policy_rate"] == 0
    assert out["decision_workspaces"]["bonds"]["transmission"]["equities"]["credit_canary"] is True
    values[1]["rates_credit"]["drivers_for"]["equities"]["hy_oas"] = None
    explicit_null = publication(values)
    assert explicit_null["publication"]["content_sha256"] != out["publication"]["content_sha256"]


def test_clocks_do_not_promote_related_vintages_or_complete_fields():
    out = publication()
    pub = out["publication"]
    assert out["decision_workspaces"]["bonds"]["status"] == "ready"
    assert pub["component_clocks"]["rates_credit"]["asof"] == "2026-10-16"
    assert pub["related_vintages"]["hy_oas"]["clock"]["asof"] == "2026-10-13"
    assert pub["related_vintages"]["ebp"]["reported"]["stale"] is False
    assert pub["reported_cross_asset_stale"] is False
    assert all(row["observation_asof"] is None and row["available_at"] is None
               and row["underlying_source_family"] is None for row in pub["field_lineage"]["bonds"].values())
    assert out["probability_policy"] == "withheld"


@pytest.mark.parametrize("raw,status", [("2026-10-20", "future"), ("2026-02-30", "malformed"), ("20261016", "malformed"), (None, "missing")])
def test_component_date_anomalies_remain_visible(raw, status):
    values = inputs()
    values[1]["rates_credit"]["as_of"] = raw
    clock = publication(values)["publication"]["component_clocks"]["rates_credit"]
    assert clock["date_status"] == status
    assert clock["reported_value"] == raw


def test_fingerprints_do_not_reread_mutated_files_or_mutate_vm():
    values = inputs()
    before = deepcopy(values)
    publication(values)
    assert values == before
    absent = publication((None, None, None, []))
    empty = publication(({}, {}, {}, []))
    assert absent["publication"]["input_fingerprints"]["snapshot"]["sha256"] != empty["publication"]["input_fingerprints"]["snapshot"]["sha256"]
