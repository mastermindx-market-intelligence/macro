"""Bounded read-only audit reproductions against fetched macro pin.

Product repository files are unmodified. Temporary fixture writes are isolated.
Parquet writer proofs inject the decode exception because pyarrow is unavailable;
they prove control flow reaches the replacement writer, not a production incident.
"""
from __future__ import annotations
import json
import os
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

import argparse
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source-root", required=True, type=Path)
args = parser.parse_args()
ROOT = args.source_root.resolve()
sys.path.insert(0, str(ROOT))
import pandas as pd
from engine.theme_graph import local_sources, rights, store
from engine.theme_graph import ontology, probation
from engine import basket_membership_pit as pit
from engine.neuralweb import thematic_state as ts
from types import SimpleNamespace

PIN = "bebcb24db8707f93c3acca470590fead13e78dbd"
results = []

def record(id, kind, details):
    results.append({"id": id, "evidence_type": kind, "details": details})

with tempfile.TemporaryDirectory(prefix="gmi-audit-") as d:
    tmp = Path(d)
    prior = tmp / "nodes.parquet"
    prior.write_bytes(b"fixture existing prior store; decode failure is injected")
    writes = []
    with patch.object(pd, "read_parquet", side_effect=ValueError("injected decode failure")), \
         patch.object(store, "_atomic_write_parquet", side_effect=lambda df, p: writes.append((df.copy(), p))):
        added = store.append_rows(prior, [{"node_id": "theme:new"}], store.NODE_COLUMNS, store.NODE_KEY)
        try:
            store._read(prior, store.NODE_COLUMNS, strict=True)
            strict_refused = False
        except ValueError:
            strict_refused = True
    assert added == 1 and len(writes) == 1 and writes[0][0]["node_id"].tolist() == ["theme:new"]
    assert strict_refused
    record("G1", "injected read-failure control-flow reproduction", {
        "prior_file_existed": True, "replacement_writer_calls": len(writes),
        "replacement_node_ids": writes[0][0]["node_id"].tolist(),
        "append_returned_rows_added": added, "strict_reader_refused_same_exception": strict_refused,
        "scope": "Does not decode corrupt parquet or mutate a production store; proves destructive replacement path is reached."})

    pitpath = tmp / "membership_history.parquet"
    pitpath.write_bytes(b"fixture existing prior store; decode failure is injected")
    pit_writes = []
    one = {"baskets": {"a": {"members": [{"ticker": "A.SZ", "added": None, "removed": None}]}}}
    with patch.object(pit, "history_path", return_value=pitpath), \
         patch.object(pd, "read_parquet", side_effect=ValueError("injected decode failure")), \
         patch.object(pd.DataFrame, "to_parquet", autospec=True, side_effect=lambda df, *a, **k: pit_writes.append(df.copy())):
        added = pit._append_rows(pit.SUITE_THS, pit._rows_from_doc(one, "2026-10-01", pit.SUITE_THS))
    assert added == 1 and len(pit_writes) == 1
    record("G1b", "injected read-failure control-flow reproduction", {
        "incumbent_PIT_owner_replacement_writer_calls": len(pit_writes),
        "replacement_row_count": len(pit_writes[0]), "append_returned_rows_added": added})

    # Two complete membership documents retain an empty basket A in the second.
    # `_rows_from_doc` has no representation for that observed-empty collection.
    first = {"baskets": {"a": {"members": [{"ticker": "A.SZ"}]}, "b": {"members": [{"ticker": "B.SZ"}]}}}
    second = {"baskets": {"a": {"members": []}, "b": {"members": [{"ticker": "B.SZ"}]}}}
    history = pd.DataFrame(pit._rows_from_doc(first, "2026-10-01", pit.SUITE_THS) + pit._rows_from_doc(second, "2026-10-02", pit.SUITE_THS))
    with patch.object(pit, "read_history", return_value=history), patch.object(pit, "_read_json", return_value=second):
        owner = pit.members_asof("a", "2026-10-02")
    intervals = [asdict(x) for x in local_sources.ths_membership_intervals(history) if x.basket_id == "a"]
    assert owner["members"] == [] and owner["pit"] is True
    assert len(intervals) == 1 and intervals[0]["valid_to"] is None
    record("G2", "pure owner-to-graph composition reproduction", {
        "complete_second_document_has_observed_empty_basket": True,
        "owner_asof_result": owner, "graph_intervals": intervals,
        "result": "Owner reports no members; graph retains A.SZ with an open-ended interval."})

    # Explicit source removal is kept in owner rows but ignored by graph intervals.
    removal_doc = {"baskets": {"a": {"members": [
        {"ticker": "A.SZ", "added": "2026-10-01", "removed": "2026-10-02"},
        {"ticker": "B.SZ", "added": "2026-10-01", "removed": None}]}}}
    removed_history = pd.DataFrame(pit._rows_from_doc(removal_doc, "2026-10-03", pit.SUITE_THS))
    with patch.object(pit, "read_history", return_value=removed_history):
        owner = pit.members_asof("a", "2026-10-03")
    intervals = [asdict(x) for x in local_sources.ths_membership_intervals(removed_history)]
    assert owner["members"] == ["B.SZ"]
    assert any(x["ticker"] == "A.SZ" and x["valid_to"] is None for x in intervals)
    record("G3", "pure owner-to-graph composition reproduction", {
        "owner_asof_members": owner["members"], "graph_intervals": intervals,
        "result": "Graph mints an active membership for a source row already removed before the snapshot."})

    reg = tmp / "rights.yml"
    rights._load.cache_clear()
    reg.write_text("families:\n  fixture:\n    rights_class: direct_display_ok\n    auth_class: house\n")
    before = rights.emission_allowed("fixture", path=reg)
    reg.write_text("families:\n  fixture:\n    rights_class: internal_only\n    auth_class: house\n")
    after = rights.emission_allowed("fixture", path=reg)
    rights._load.cache_clear()
    after_refresh = rights.emission_allowed("fixture", path=reg)
    assert before and after and not after_refresh
    record("G4", "pure rights-registry revision reproduction", {
        "before_downgrade": before, "same_process_after_downgrade": after,
        "after_manual_cache_clear": after_refresh,
        "unknown_family_licensing_tuple": rights.licensing_for_family("not_registered", path=reg),
        "scope": "Long-lived-process revocation behavior; no observed production revocation incident."})

    # Exact pinned source-artifact shape, with current membership file.
    n = json.loads((ROOT / ts._NARRATIVE_PATH).read_text())
    b = json.loads((ROOT / "data/baskets/membership.json").read_text())
    ticker_map, stale = ts._read_narrative_tickers(ROOT)
    assert n["narratives"] and all(isinstance(x["legs"], dict) for x in n["narratives"])
    assert ticker_map == {}
    assert all("tickers" not in x and "members" in x for x in b["baskets"].values())
    s = json.loads((ROOT / ts._DATA_OUT).read_text())
    assert len(s["themes"]) == 18 and all(x["narrative"] is None for x in s["themes"])
    record("G5", "exact pinned artifact plus actual reader reproduction", {
        "narrative_rows": len(n["narratives"]),
        "narrative_legs_shape": "dict",
        "actual_reader_ticker_map": ticker_map,
        "upstream_recommended_rows": sum(len(x.get("recommended") or []) for x in n["narratives"]),
        "membership_baskets": len(b["baskets"]),
        "baskets_with_tickers_field": sum("tickers" in x for x in b["baskets"].values()),
        "current_theme_state_null_narratives": sum(x["narrative"] is None for x in s["themes"]),
        "reader_stale_reasons": stale,
        "result": "Two incompatible schema assumptions independently prevent the incumbent narrative overlap path."})

    hroot = tmp / "history"
    art = {"as_of": "2026-10-03", "themes": [{"theme_id": "fixture", "foresight": {"stage": "first"}}]}
    with patch.dict(os.environ, {"COLLECT_LANE": "nightly"}):
        first_count = ts.append_phase_history(hroot, art)
        art["themes"][0]["foresight"]["stage"] = "corrected"
        correction_count = ts.append_phase_history(hroot, art)
    tape = [json.loads(x) for x in (hroot / ts._HISTORY_OUT).read_text().splitlines()]
    assert first_count == 1 and correction_count == 0 and tape[0]["foresight_stage"] == "first"
    record("G6", "pure append-history semantics reproduction", {
        "first_rows_written": first_count, "same_day_correction_rows_written": correction_count,
        "retained_stage": tape[0]["foresight_stage"], "fields": sorted(tape[0]),
        "scope": "Documented daily first-write semantics, not a new defect allegation; insufficient as a complete future evidence snapshot/correction record."})

    future_is_stale = ts._is_stale("2099-01-01")
    assert future_is_stale is False
    record("G7", "pure clock-boundary reproduction", {
        "future_source_date": "2099-01-01", "classified_stale": future_is_stale,
        "scope": "Temporal qualification limitation: future-dated source is not refused by this freshness check."})

    # Positive D2D evidence: valid time and known-at time are distinct, and a
    # source-local concept may remain unmapped even after a proposal is ratified.
    local = "ltheme:ths:fixture"
    company = "co:cn:A.SZ"
    node_rows = [
        {"node_id": local, "kind": "local_theme", "computed_at": "2026-10-01T00:00:00Z"},
        {"node_id": company, "kind": "company", "computed_at": "2026-10-01T00:00:00Z"},
    ]
    first_edge = {"edge_id": "fixture-edge", "type": "MEMBER_OF", "src": company, "dst": local,
                  "valid_from": "2026-10-01", "valid_to": None, "belief_time": "2026-10-01",
                  "computed_at": "2026-10-01T00:00:00Z", "evidence_refs": []}
    later_edge = {**first_edge, "valid_to": "2026-10-02", "belief_time": "2026-10-03",
                  "computed_at": "2026-10-03T00:00:00Z"}
    proposal = probation.make_proposal(kind="mapping", subject={"local_theme": local, "canonical_theme": "theme:fixture"},
                                      proposed_by="coverage_gap", created="2026-10-01T00:00:00Z")
    proposal.update(status="ratified", ratified_by="fixture-curator", adjudicated_at="2026-10-03T00:00:00Z")
    view = SimpleNamespace(read_nodes=lambda: node_rows, read_node_lifecycle=lambda: [],
                           read_edges=lambda: [first_edge, later_edge], read_proposals=lambda: [proposal])
    old = ontology.compose_neighborhood(view, node_id=local, asof="2026-10-02", knowledge_cutoff="2026-10-02")
    now = ontology.compose_neighborhood(view, node_id=local, asof="2026-10-02", knowledge_cutoff="2026-10-03")
    fuzzy = ontology.compose_neighborhood(view, node_id="fixture", asof="2026-10-02")
    assert len(old["relations"]) == 1 and old["counts"]["future_beliefs_excluded"] == 1
    assert now["relations"] == []
    assert old["proposals"][0]["status"] == "proposed"
    assert now["curation"]["state"] == "RATIFIED_NOT_MATERIALIZED"
    assert old["canonical_mapping"]["state"] == now["canonical_mapping"]["state"] == "UNMAPPED"
    assert fuzzy["availability"]["state"] == "SUBJECT_NOT_FOUND"
    record("G8", "positive D2D pure reader reproduction", {
        "old_cutoff_relation_count": len(old["relations"]), "later_cutoff_relation_count": len(now["relations"]),
        "old_cutoff_proposal_status": old["proposals"][0]["status"],
        "later_cutoff_curation_state": now["curation"]["state"],
        "unmapped_source_local_concept_retained": True, "fuzzy_label_lookup_refused": True,
        "scope": "Proves reader behavior only, not production invocation or completion of all frozen D2D objectives."})

    queue = tmp / "bad-proposals.jsonl"
    queue.write_text('{"proposal_id":"first","proposal_id":"second"}\n')
    try:
        probation.read_proposals(queue, strict=True)
        strict_duplicate_refused = False
    except ValueError:
        strict_duplicate_refused = True
    assert strict_duplicate_refused
    record("G9", "positive strict JSON reader reproduction", {"duplicate_JSON_key_refused": True})

out = {"source_pin": PIN, "mode": "standard Pro audit; no Deep Research", "results": results}
print(json.dumps(out, indent=2))
