"""Actual A1 composition: unqualified class payloads cannot become task evidence.

Synthetic native ledgers only; no protected outcomes, producer execution or scorer.
The class-specific payloads deliberately have no accepted owner metric adapter.
Each case proves display/source preservation, not empirical validity.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from admin import intelligence_os as IOS

CLASS_PAYLOADS = {
    "predictive": ({"target": "UP/DOWN/FLAT at21 NYSE sessions", "probabilities": [.7,.2,.1]},
                   {"target": "UP/DOWN/FLAT at21 NYSE sessions", "probabilities": [65,20,15]}),
    "ranking": ({"eligible_at_cutoff": ["A","B","C"], "ranked": ["A","C","B"], "top_k": 1},
                {"eligible_at_cutoff": ["A","B","C"], "evaluated_universe": ["A"], "claimed_coverage": 1}),
    "classification_state": ({"label": "STABLE", "label_known_at": "2026-01-01T00:00:00Z", "decision_at": "2026-01-02T00:00:00Z"},
                             {"label": "STABLE", "label_known_at": "2026-01-03T00:00:00Z", "decision_at": "2026-01-02T00:00:00Z"}),
    "detection_event": ({"events": ["e1"], "alarms": ["a1"], "matches": [["a1","e1"]]},
                        {"events": ["e1"], "alarms": ["a1","a2","a3"], "matches": [["a1","e1"],["a2","e1"],["a3","e1"]]}),
    "descriptive": ({"entity": "fixture", "value": .1, "unit": "ratio", "window": "quarter"},
                    {"entity": "fixture", "value": .1, "unit": "percent", "window": "quarter"}),
    "salience": ({"rubric_owner": "independent-fixture", "target": "relevance", "direction": 0},
                 {"rubric_owner": "same-generating-model", "target": "price-hit-rate", "direction": 0}),
    "generative": ({"source_entity": "fixture", "source_unit": "USD", "source_window": "quarter", "answer_unit": "USD", "answer_window": "quarter"},
                   {"source_entity": "fixture", "source_unit": "USD", "source_window": "quarter", "answer_unit": "percent", "answer_window": "year", "self_grade": 100}),
}


def _snapshot(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


def _estate(root, output_class, variant):
    fresh=(datetime.now(timezone.utc)-timedelta(hours=6)).isoformat()
    ledger="data/fixture_ledger/theses.jsonl"
    eid="engine/eval_fixture.py::eval-composition-fixture"
    art={"path":ledger,"format":"jsonl","producer":"engine/eval_fixture.py",
         "owner_program":"eval-composition-fixture","cadence":"daily-engine",
         "storage":"git","asof_field":"asof","freshness_sla_hours":24,
         "schema":"none","tier":"shadow","horizon_role":"context",
         "weights":"none","consumers":[]}
    doc={"meta":{"schema_version":1,"description":"synthetic class composition",
                 "tier_vocabulary":{},"article2_surfaces":[]},"artifacts":{"fixture":art}}
    files={"config/synapse.yml":yaml.safe_dump(doc),
           "config/intelligence_registry_overlay.yml":yaml.safe_dump({"schema_version":1,"engines":{eid:{"output_class":{"value":output_class,"rationale":"synthetic declared class"}}}}),
           "config/qual_ladder.yml":"families: {}\n",
           "engine/eval_fixture.py":"# Synthetic artifact owner; never executed.\n",
           ledger:json.dumps({"asof":fresh,"class_payload":CLASS_PAYLOADS[output_class][variant]})+"\n",
           "data/species/registry.json":json.dumps({"species":[{"species_id":"fixture-v1","validation_status":"validated","version":"1.0","market_scope":["US"],"evidence_stack":["retained fixture source reference"],"ledger_binding":{"ledger":ledger,"since":"2026-01-01","flip_criteria":"existing owner fixture criterion"}}]}),
           "data/qledger/claims.jsonl":""}
    for rel,value in files.items():
        target=root/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(value)
    return eid


@pytest.mark.parametrize("output_class", list(CLASS_PAYLOADS))
@pytest.mark.parametrize("variant", [0,1], ids=["valid-metadata-unqualified-metric", "adversarial-payload"])
def test_seven_class_real_panel_detail_composition(tmp_path, output_class, variant, record_property):
    root=tmp_path/"estate"
    eid=_estate(root,output_class,variant)
    before=_snapshot(root)
    IOS._CACHE.clear()
    panel=IOS.panel(root=root,force=True)
    detail=IOS.engine_detail(eid,root=root)
    assert panel["ok"] and detail["ok"]
    row=panel["engines"][0]
    assert row["output_class"]==output_class
    assert detail["engine"]["validation_state"]=="validated"
    assert row["evidence_status"]=="Accruing"
    assert "owner_validation_scope_unqualified" in row["evidence_reason_codes"]
    assert row["evidence_owner_scope"]["qualified_task_scope"] is None
    bound=row["evidence_owner_scope"]["bound_species"]
    assert bound[0]["species_id"]=="fixture-v1"
    assert bound[0]["owner_scope"]["version"]=="1.0"
    assert "species:fixture-v1" in row["evidence_refs"]
    assert row["evidence_provider"]["kind"]=="t1_owner_native"
    assert all(o["state"]=="healthy" and o["assessment_status"]=="complete" for o in detail["outputs"])
    for key in ("evidence_status","evidence_reason_codes","evidence_owner_scope","evidence_provider","evidence_ruler"):
        assert row[key]==detail["engine"][key]
    assert sum(b["n_engines"] for b in panel["ceo_view"])==1
    assert len(panel["ceo_view"])==5
    assert _snapshot(root)==before  # Actual reader never registers/promotes/writes a claim/clock.
    assert "class_payload" not in json.dumps({"panel":panel,"detail":detail})
    record_property("output_class",output_class)
    record_property("variant",variant)
    record_property("composition_acceptance","PASS: actual registry/health/provider/panel/detail")
    record_property("task_metric_acceptance","UNAVAILABLE: no qualified class owner adapter in current projection")
    IOS._CACHE.clear()


def test_ready_matched_owner_does_not_grant_panel_validation_or_write_authority(tmp_path, record_property):
    """Real readiness positive control reaches the consumer, without task qualification.

    Reuses incumbent QLedger fixture constructors; registrar clocks exist solely
    under tmp_path before the no-write snapshot. No outcome or production access.
    """
    from engine import qledger as q, qledger_evidence_clock
    import importlib.util
    spec=importlib.util.spec_from_file_location("eval_os_incumbent_control_fixtures",
        Path(__file__).with_name("test_qledger_control_policy.py"))
    fixtures=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixtures)
    _cohort,_write_store,_start_clock=fixtures._cohort,fixtures._write_store,fixtures._start_clock

    root=tmp_path/"estate"
    eid=_estate(root,"predictive",0)
    doc=yaml.safe_load((root/"config/synapse.yml").read_text())
    old_ledger=root/doc["artifacts"]["fixture"]["path"]
    new_ledger="data/stock_desk/theses.jsonl"
    target=root/new_ledger
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(old_ledger.read_bytes())
    old_ledger.unlink()
    doc["artifacts"]["fixture"]["path"]=new_ledger
    (root/"config/synapse.yml").write_text(yaml.safe_dump(doc))
    species=json.loads((root/"data/species/registry.json").read_text())
    species["species"][0]["ledger_binding"]["ledger"]=new_ledger
    (root/"data/species/registry.json").write_text(json.dumps(species))
    claims,grades=_cohort("stock_desk",30,controlled=30)
    _write_store(root,claims,grades)
    _start_clock(root,"stock_desk")
    qledger_evidence_clock.record_start("stock_desk",horizon_d=21,horizon_unit="trading_days",
        root=root,now="2025-01-01T00:00:00+00:00")
    assert q.promotion_check_dispatch("stock_desk",21,root=root).eligible
    before=_snapshot(root)
    IOS._CACHE.clear()
    panel=IOS.panel(root=root,force=True)
    detail=IOS.engine_detail(eid,root=root)
    assert panel["ok"] and detail["ok"]
    row=panel["engines"][0]
    assert row["evidence_provider"]["family"]=="stock_desk"
    assert row["evidence_provider"]["read_status"]=="ok"
    assert row["evidence_ruler"]["selected_qledger_rung"]=="21"
    assert row["evidence_maturity"]["rungs"]["21"]["ready"] is True
    assert row["evidence_status"]=="Accruing"
    assert "owner_validation_scope_unqualified" in row["evidence_reason_codes"]
    assert row["evidence_status"]==detail["engine"]["evidence_status"]
    assert _snapshot(root)==before
    record_property("advisory_readiness","PASS: actual matched-control ready owner")
    record_property("authority_effect","PASS: no owner validation/promotion/clock/financial writes")
    IOS._CACHE.clear()
