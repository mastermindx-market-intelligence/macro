"""Controlled real-owner/source-shape tests; no publication or natural rights claim."""
from __future__ import annotations

import copy
import datetime as dt
import json
import types
from pathlib import Path

import pandas as pd
import pytest
import yaml

from engine import basket_membership_pit as pit
from engine.neuralweb import thematic_state as legacy, theme_state_adapter as adapter
from engine.theme_graph import identity, rights, store
from lib import config

LOCAL = "ltheme:finviz:power_grid"
CN = "ltheme:ths:900001"
EFFECTIVE = "2026-10-03"
KNOWN = "2026-10-04T12:00:00Z"
EMITTED = "2026-10-04T12:00:00Z"


def write(root, path, value):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False))


@pytest.fixture
def production_world(tmp_path, monkeypatch):
    # Explicit controlled observation clock; fixed fixture cutoffs do not depend
    # on wall-clock progress. Production capture still uses its real clock.
    class ControlledCaptureClock(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            instant = dt.datetime.fromisoformat("2026-10-04T11:00:00+00:00")
            return instant.astimezone(tz) if tz is not None else instant.replace(tzinfo=None)
    namespace = {name: getattr(dt, name) for name in dir(dt) if not name.startswith("__")}
    namespace["datetime"] = ControlledCaptureClock
    monkeypatch.setattr(adapter, "dt", types.SimpleNamespace(**namespace))
    # Synthetic owner estate: no live registry or crosswalk acquisition.
    root = tmp_path / "synthetic-owner"
    root.mkdir()
    crosswalk = {"themes": [
        {"id": "grid", "name_en": "Grid", "name_zh": "电网",
         "foresight_id": "grid_owner", "basket_ids": ["power_grid"], "subsector_keys": ["grid_rrg"]},
        {"id": "travel", "name_en": "Travel", "name_zh": "旅行",
         "foresight_id": "travel_owner", "basket_ids": ["travel"], "subsector_keys": []},
    ]}
    (root / "config").mkdir()
    (root / "config/theme_crosswalk.yml").write_text(yaml.safe_dump(crosswalk, allow_unicode=True))
    (root / "config/theme_sources.yml").write_text(yaml.safe_dump({"families": {
        "finviz_themes": {"rights_class": "derived_display_ok", "auth_class": "house"},
        "ths_concepts": {"rights_class": "derived_display_ok", "auth_class": "house"},
        "controlled_specialist": {"rights_class": "derived_display_ok", "auth_class": "house"},
    }}))
    write(root, legacy._FORESIGHT_PATH, {"asof": EFFECTIVE, "themes": [
        {"theme": "grid_owner", "stage": "watch", "score": 0, "entry_ready": False,
         "bottleneck_band": None, "units": {"score": "native_points"}, "period": "native_session",
         "scenario": {"assumptions": ["owner assumption"], "target_at": "2027-01-01"}}]})
    write(root, legacy._BASKETS_PATH, {"theme_intel": {"as_of": EFFECTIVE, "themes": [
        {"id": "power_grid", "score": 0, "reco": False, "components": {"crowding": None},
         "native_receipt_extra": {"measurement": "preserved"}}]}})
    write(root, legacy._RADAR_ENRICHED_PATH, {"as_of": EFFECTIVE, "flags": [
        {"basket": "power_grid", "state": "watch", "salience": 0, "divergence": None}]})
    write(root, legacy._RADAR_PATH, {"as_of": EFFECTIVE, "hypotheses": [
        {"subject": "power_grid", "lean": "flat", "horizon_d": 0, "check_by": "2027-01-01",
         "thesis": "full native thesis " * 20, "scenario": {"case": "native"}}]})
    write(root, legacy._SUBSECTOR_PATH, {"asof": EFFECTIVE, "themes": [
        {"theme": "grid_rrg", "quadrant": "Leading", "rs": 0, "z_accel": 0,
         "emerging_score": None, "window": {"start": "2026-09-01", "end": EFFECTIVE}}]})
    write(root, legacy._NARRATIVE_PATH, {"schema": "narrative_emergence.v1", "region": "us",
        "as_of": EFFECTIVE, "narratives": [{"signature": "controlled", "n": 1,
        "legs": {"tighten": 0, "momentum": 0}, "recommended": [{"ticker": "HUBB"}]}]})
    p = root / legacy._DIVERGENCE_LOG_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(json.dumps(row) for row in [
        {"theme": "grid", "asof": "2026-10-02", "divergence": 0, "correction_of": None},
        {"theme": "grid", "asof": EFFECTIVE, "divergence": None, "money_pct": 0},
    ]) + "\n")
    nodes = []
    for node_id, kind, meta in [
        ("theme:grid", "theme", {}), ("theme:travel", "theme", {}),
        (LOCAL, "local_theme", {"basket_id": "power_grid", "suite": "baskets"}),
        (CN, "local_theme", {"basket_id": "thsc900001", "suite": "baskets_china_ths"}),
    ]:
        nodes.append({"node_id": node_id, "kind": kind, "name_en": node_id, "name_zh": "测试",
            "status": "ACTIVE", "birth_date": "2026-10-01", "computed_at": "2026-10-01T00:00:00Z",
            "engine_version": store.ENGINE_VERSION, "source_meta": json.dumps(meta)})
    graph = root / "data/theme_graph"
    graph.mkdir(parents=True)
    pd.DataFrame(nodes, columns=list(store.NODE_COLUMNS)).to_parquet(graph / "nodes.parquet", index=False)
    pd.DataFrame(columns=list(store.NODE_LIFECYCLE_COLUMNS)).to_parquet(graph / "node_lifecycle.parquet", index=False)
    pd.DataFrame(columns=list(store.EDGE_COLUMNS)).to_parquet(graph / "edges.parquet", index=False)
    (graph / "probation").mkdir()
    (graph / "probation/proposals.jsonl").write_text("")
    for suite, bid in [("baskets", "power_grid"), ("baskets_china_ths", "thsc900001")]:
        write(root, "data/" + suite + "/membership.json", {"version": EFFECTIVE, "baskets": {
            bid: {"members": [{"ticker": "HUBB", "added": "2026-10-01", "removed": None}]}}})
        pd.DataFrame([{"suite": suite, "basket_id": bid, "ticker": "HUBB", "snapshot_date": EFFECTIVE,
            "added": "2026-10-01", "removed": None, "source_shape": "membership", "members_sha": "fixture"}],
            columns=list(pit.COLUMNS)).to_parquet(root / "data" / suite / "membership_history.parquet", index=False)
    monkeypatch.setattr(config, "data_dir", lambda: root / "data")
    return root


def compose(root, *, known_at=KNOWN, owner_readers=None):
    bundle = adapter.capture_owner_bundle(root, effective_at=EFFECTIVE, known_at=known_at,
                                          owner_readers=owner_readers)
    # Before S1 the real incumbent shadow can run but cannot express these facts.
    fn = getattr(adapter, "compose_production_from_owner_bundle", adapter.compose_from_owner_bundle)
    return bundle, fn(bundle, generated_at=EMITTED)


def subject(result, node="theme:grid"):
    return next(row for row in result["state"]["subjects"] if row["node_id"] == node)


def test_production_retains_native_zero_null_units_period_and_scenario(production_world):
    _, result = compose(production_world)
    assert result["state"]["schema"] == "neuralweb.theme_state.v2"
    record = subject(result)["legs"]["foresight_cascade"]["records"][0]
    assert record["value"]["score"] == 0 and type(record["value"]["score"]) is int
    assert record["value"]["entry_ready"] is False
    assert record["value"]["bottleneck_band"] is None
    assert record["units"]["value"] == {"score": "native_points"}
    assert record["period"]["value"] == "native_session"
    assert record["scenario"]["value"]["target_at"] == "2027-01-01"
    assert record["native_clocks"]["known_at"] == {"value": None, "grain": "UNAVAILABLE",
                                                  "null_reason": "NATIVE_CLOCK_NOT_DECLARED"}
    assert subject(result)["eligibility"] == "NOT_QUALIFIED"


def test_exact_local_scope_never_inherits_canonical_foresight_or_us_as_cn(production_world):
    _, result = compose(production_world)
    local, cn = subject(result, LOCAL), subject(result, CN)
    assert local["canonical_mapping"]["state"] == "UNMAPPED"
    assert local["legs"]["foresight_cascade"]["records"] == []
    assert local["legs"]["baskets"]["records"][0]["value"]["score"] == 0
    assert cn["legs"]["baskets"]["records"] == []
    assert cn["legs"]["narrative_emergence"]["records"] == []
    assert cn["legs"]["narrative_emergence_cn"]["presence"] == "UNAVAILABLE"


def test_full_radar_thesis_forecast_targets_and_native_subsector_are_not_reinterpreted(production_world):
    _, result = compose(production_world)
    legs = subject(result)["legs"]
    hyp = legs["radar"]["records"][0]
    assert hyp["value"]["thesis"] == "full native thesis " * 20
    assert hyp["value"]["horizon_d"] == 0
    assert hyp["value"]["check_by"] == "2027-01-01"
    assert legs["radar"]["freshness"] != "FUTURE"
    assert legs["radar_enriched"]["records"][0]["value"]["salience"] == 0
    rec = legs["subsector_rotation"]["records"][0]
    assert rec["value"]["z_accel"] == 0
    assert rec["compatibility_aliases"]["accel_z"] == 0
    assert rec["window"]["value"] == {"start": "2026-09-01", "end": EFFECTIVE}


def test_divergence_preserves_native_history_without_fabricated_known_clocks(production_world):
    _, result = compose(production_world)
    records = subject(result)["legs"]["divergence_log"]["records"]
    assert [r["value"]["asof"] for r in records] == ["2026-10-02", EFFECTIVE]
    assert records[0]["value"]["divergence"] == 0
    assert records[1]["value"]["divergence"] is None
    assert all(r["native_clocks"]["known_at"]["value"] is None for r in records)


def test_empty_unreceipted_population_and_duplicate_rows_are_not_complete(production_world):
    path = production_world / legacy._FORESIGHT_PATH
    payload = json.loads(path.read_text())
    payload["themes"].append(copy.deepcopy(payload["themes"][0]))
    path.write_text(json.dumps(payload))
    _, result = compose(production_world)
    leg = subject(result)["legs"]["foresight_cascade"]
    assert len(leg["records"]) == 2
    assert leg["conflicts"][0]["reason"] == "DUPLICATE_NATIVE_IDENTITY"
    missing = subject(result, "theme:travel")["legs"]["foresight_cascade"]
    assert missing["presence"] == "UNAVAILABLE"
    assert missing["coverage"]["declared"] is None
    assert missing["coverage"]["completeness"] == "UNPROVEN"


def test_complete_legacy_projection_and_meaningful_same_bundle_shadow(production_world):
    _, result = compose(production_world)
    assert [t["theme_id"] for t in result["legacy_candidate"]["themes"]] == ["grid", "travel"]
    assert all(t["narrative"] is None for t in result["legacy_candidate"]["themes"])
    assert result["legacy_candidate"]["themes"][0]["foresight"]["entry_ready"] is False
    assert result["shadow"]["production_state_sha256"] == result["state"]["state_sha256"]
    assert result["shadow"]["successor_surface"]["theme:grid"]["legs"]["foresight_cascade"]["records"]
    assert result["shadow"]["parity_accepted"] is False
    assert result["publication_allowed"] is False


@pytest.mark.parametrize("stamp,want", [("2026-10-03T13:00:00Z", "FUTURE"),
    ("2026-10-03T12:00:00Z", "FRESH"), ("2026-10-03", "UNKNOWN")])
def test_native_precise_future_equal_and_date_only_are_distinct(production_world, stamp, want):
    payload = json.loads((production_world / legacy._FORESIGHT_PATH).read_text())
    payload["asof"] = stamp
    write(production_world, legacy._FORESIGHT_PATH, payload)
    _, result = compose(production_world, known_at="2026-10-03T12:00:00Z")
    leg = subject(result)["legs"]["foresight_cascade"]
    assert leg["freshness"] == want
    assert leg["records"][0]["value"]["score"] == 0
    assert leg["records"][0]["usable_at_query"] is (want != "FUTURE")


class SourceReceiptFixture:
    """Injected controlled source-clock receipts; never a production authenticator."""
    def __init__(self, root, names=("foresight_cascade",), *, valid_empty=False, change=None):
        self.root, self.names, self.valid_empty, self.change = root, names, valid_empty, change

    def read_state_qualification(self, *, node_id, query, graph_capture_id, native_reads, source_sha256):
        from engine.theme_graph import theme_state
        sources = {}
        for name in self.names:
            doc = json.loads((self.root / adapter.SOURCE_PATHS[name]).read_text())
            effective = doc.get("as_of") or doc.get("asof") or doc.get("theme_intel", {}).get("as_of")
            sources[name] = {"owner": "controlled-source:" + name + ":" + node_id,
                "schema": "controlled.prequalified_source/v1", "generation_id": "controlled-source-generation",
                "graph_generation_id": graph_capture_id, "subject_id": node_id, "query": copy.deepcopy(query),
                "effective_at": effective, "known_at": "2026-10-03T09:00:00Z",
                "available_at": "2026-10-03T08:00:00Z", "recorded_at": "2026-10-03T09:00:00Z",
                "availability": "VALID_EMPTY" if self.valid_empty else "AVAILABLE",
                "payload": doc, "sha256": theme_state.canonical_sha256(doc)}
        result = {"owner_receipts": {}, "source_receipts": sources}
        if self.change:
            self.change(result)
        return result


def rehash(state):
    from engine.theme_graph import theme_state_production as production
    state["state_sha256"] = production.state_digest(state)
    state["generation_id"] = production.GENERATION_PREFIX + state["state_sha256"][:20]
    return state


def test_qualified_specialist_receipts_contribute_real_facts_without_vocabulary_rights_upgrade(production_world):
    names = ("foresight_cascade", "baskets", "radar", "radar_enriched", "subsector_rotation")
    _, result = compose(production_world, owner_readers=SourceReceiptFixture(production_world, names))
    for name in names:
        leg = subject(result)["legs"][name]
        assert leg["records"]
        assert leg["qualification"]["source_receipt"]["owner"].startswith("controlled-source:")
        assert leg["qualification"]["status"] == "SOURCE_QUALIFIED_RIGHTS_UNAVAILABLE"
        assert leg["qualification"]["rights"]["status"] == "UNAVAILABLE"
    local = subject(result, LOCAL)
    assert local["legs"]["foresight_cascade"]["records"] == []
    assert local["legs"]["baskets"]["records"][0]["value"]["score"] == 0
    assert local["legs"]["baskets"]["qualification"]["rights"]["family"] is None
    assert local["legs"]["baskets"]["qualification"]["rights"]["native_read"]["known_family"] is False
    assert result["state"]["materialization_allowed"] is False


def test_only_explicit_qualified_empty_is_admitted(production_world):
    write(production_world, legacy._FORESIGHT_PATH, {"asof": EFFECTIVE, "themes": []})
    _, unqualified = compose(production_world)
    _, qualified = compose(production_world, owner_readers=SourceReceiptFixture(production_world, valid_empty=True))
    a = subject(unqualified)["legs"]["foresight_cascade"]
    b = subject(qualified)["legs"]["foresight_cascade"]
    assert a["presence"] == "UNAVAILABLE" and a["coverage"]["declared"] is None
    assert b["presence"] == "VALID_EMPTY" and b["coverage"]["declared"] == 0
    assert b["coverage"]["observed"] == 0 and b["records"] == []


def test_source_receipt_cannot_change_scope_native_number_or_source_clock(production_world):
    def change(result):
        receipt = result["source_receipts"]["foresight_cascade"]
        receipt["effective_at"] = "2026-10-02"
    with pytest.raises(ValueError, match="native source clock"):
        compose(production_world, owner_readers=SourceReceiptFixture(production_world, change=change))


def test_rehashed_omission_and_number_to_bool_cannot_escape_meaningful_shadow(production_world):
    from engine.theme_graph import theme_state_production as production
    bundle, result = compose(production_world)
    state = copy.deepcopy(result["state"])
    row = subject({"state": state})["legs"]["foresight_cascade"]["records"][0]
    row["value"]["score"] = False
    row["record_id"] = production.canonical_sha256({"source": subject({"state": state})["legs"]["foresight_cascade"]["source_ref"]["sha256"],
                                                 "position": row["source_position"], "value": row["value"]})
    rehash(state)
    production.validate_state(state)  # Integrity is not authority or same-input assembly.
    with pytest.raises(ValueError, match="deterministic captured owner assembly"):
        adapter.compare_production_shadow(state, bundle)


@pytest.mark.parametrize("change", [
    lambda state: state["authority_caps"].update(ranking=0),
    lambda state: subject({"state": state})["legs"]["foresight_cascade"]["coverage"].update(observed=True),
    lambda state: state["bundle_ref"].update(sha256="1" * 64),
    lambda state: state.update(known_at="2026-10-04T13:00:00Z"),
    lambda state: subject({"state": state})["canonical_mapping"].update(state="MAPPED", theme_node_ids=[]),
])
def test_closed_strict_flags_counts_mapping_and_bundle_scope(production_world, change):
    from engine.theme_graph import theme_state_production as production
    _, result = compose(production_world)
    state = copy.deepcopy(result["state"])
    change(state)
    rehash(state)
    with pytest.raises(ValueError):
        production.validate_state(state)


def test_available_without_records_is_not_empty_and_bad_native_clock_use_is_refused(production_world):
    from engine.theme_graph import theme_state_production as production
    _, result = compose(production_world)
    state = copy.deepcopy(result["state"])
    leg = subject({"state": state})["legs"]["foresight_cascade"]
    leg["records"] = []
    leg["coverage"]["observed"] = 0
    rehash(state)
    with pytest.raises(ValueError, match="available.*records"):
        production.validate_state(state)


def test_full_predecessor_optional_fields_and_configured_order_survive(production_world):
    _, result = compose(production_world)
    previous = copy.deepcopy(result["legacy_candidate"])
    previous["owner_receipt_extra"] = {"zero": 0, "false": False, "unknown": None}
    previous["themes"][0]["basket_intel"][0]["receipt_extra"] = {"revision": "old"}
    write(production_world, "data/neuralweb/theme_state.json", previous)
    cfg = yaml.safe_load((production_world / "config/theme_crosswalk.yml").read_text())
    cfg["themes"].reverse()
    (production_world / "config/theme_crosswalk.yml").write_text(yaml.safe_dump(cfg))
    _, next_result = compose(production_world)
    projection = next_result["legacy_candidate"]
    assert [row["theme_id"] for row in projection["themes"]] == ["travel", "grid"]
    assert projection["owner_receipt_extra"] == {"zero": 0, "false": False, "unknown": None}
    assert projection["themes"][1]["basket_intel"][0]["receipt_extra"] == {"revision": "old"}
    assert next_result["shadow"]["predecessor_optional_inventory"]
    assert next_result["shadow"]["parity_accepted"] is False


def test_missing_and_malformed_specialist_are_distinct_from_valid_empty(production_world):
    (production_world / legacy._FORESIGHT_PATH).unlink()
    _, absent = compose(production_world)
    leg = subject(absent)["legs"]["foresight_cascade"]
    assert leg["presence"] == "UNAVAILABLE" and leg["null_reason"] == "SOURCE_MISSING"
    (production_world / legacy._FORESIGHT_PATH).write_text('{"bad":')
    _, invalid = compose(production_world)
    leg = subject(invalid)["legs"]["foresight_cascade"]
    assert leg["presence"] == "INVALID" and leg["null_reason"] == "SPECIALIST_SOURCE_SHAPE_INVALID"


def test_cn_native_narrative_is_separate_and_zero_legs_are_measured(production_world):
    write(production_world, adapter.SOURCE_PATHS["narrative_emergence_cn"], {
        "region": "cn", "as_of": EFFECTIVE, "narratives": [{
            "signature": "cn-controlled", "legs": {"momentum": 0, "tighten": 0}, "recommended": []}]})
    _, result = compose(production_world)
    cn = subject(result, CN)["legs"]
    assert cn["narrative_emergence"]["records"] == []
    assert cn["narrative_emergence_cn"]["records"][0]["value"]["legs"]["momentum"] == 0
    assert cn["narrative_emergence_cn"]["presence"] == "AVAILABLE"
    assert cn["narrative_emergence_cn"]["coverage"]["declared"] is None
    assert cn["narrative_emergence_cn"]["overlap_observation"] is None


def test_emission_read_cutoff_public_refusal_and_correction_prior_clock(production_world):
    from engine.theme_graph import theme_state_production as production
    bundle, result = compose(production_world)
    state = result["state"]
    good = production.read_subject(state, node_id=LOCAL, effective_at=EFFECTIVE, known_at=KNOWN)
    assert good["status"] == "DESCRIPTIVE"
    assert good["state_generated_at"] == EMITTED
    late = production.read_subject(state, node_id=LOCAL, effective_at=EFFECTIVE,
                                   known_at="2026-10-04T11:59:59Z")
    assert late["status"] == "UNAVAILABLE" and late["reason_codes"] == ["STATE_NOT_YET_EMITTED"]
    public = production.read_subject(state, node_id=LOCAL, effective_at=EFFECTIVE, known_at=KNOWN,
                                     purpose="derived_display")
    assert public["status"] == "UNAVAILABLE" and public["subject"] is None
    corrected = adapter.compose_production_from_owner_bundle(bundle, generated_at="2026-10-05T12:00:00Z",
        previous=state, correction_reason="controlled native correction")["state"]
    assert corrected["correction"]["previous"]["state_sha256"] == state["state_sha256"]
    assert corrected["correction"]["previous"]["generated_at"] == EMITTED
    invalid = copy.deepcopy(corrected)
    invalid["correction"]["previous"]["generation_id"] = production.GENERATION_PREFIX + "0" * 20
    rehash(invalid)
    with pytest.raises(ValueError, match="prior correction"):
        production.validate_state(invalid)
    with pytest.raises(ValueError):
        adapter.compose_production_from_owner_bundle(bundle, generated_at=EMITTED,
            previous=corrected, correction_reason="cannot precede the prior emission")


def test_read_receipt_validator_refuses_rehashed_clock_scope_and_type_overrides(production_world):
    from engine.theme_graph import theme_state_production as production
    _, result = compose(production_world)
    good = production.read_subject(result["state"], node_id=LOCAL, effective_at=EFFECTIVE, known_at=KNOWN)
    production.validate_read_receipt(good)
    for mutate in (
        lambda read: read.update(state_generated_at="2026-10-04T12:00:01Z"),
        lambda read: read.update(subject_id="theme:grid"),
        lambda read: read["authority_caps"].update(may_publish=0),
        lambda read: read.update(state_generation_id=production.GENERATION_PREFIX + "0" * 20),
    ):
        bad = copy.deepcopy(good)
        mutate(bad)
        with pytest.raises(ValueError):
            production.validate_read_receipt(bad)


def test_native_invalid_and_impossible_clocks_preserve_facts_but_refuse_use(production_world):
    from engine.theme_graph import theme_state_production as production
    doc = json.loads((production_world / legacy._FORESIGHT_PATH).read_text())
    row = doc["themes"][0]
    row.update(available_at="2026-10-03T10:00:00Z", known_at="2026-10-03T09:00:00Z",
               recorded_at="2026-10-03T09:00:00Z")
    write(production_world, legacy._FORESIGHT_PATH, doc)
    _, result = compose(production_world)
    leg = subject(result)["legs"]["foresight_cascade"]
    assert leg["records"][0]["value"]["score"] == 0
    assert leg["records"][0]["usable_at_query"] is False
    bad = copy.deepcopy(result["state"])
    subject({"state": bad})["legs"]["foresight_cascade"]["records"][0]["usable_at_query"] = True
    rehash(bad)
    with pytest.raises(ValueError, match="chronology"):
        production.validate_state(bad)


@pytest.mark.parametrize("clock", [0, False, "2026-10-03 12:00:00Z"])
def test_invalid_native_clock_value_is_retained_and_not_treated_as_missing(production_world, clock):
    payload = json.loads((production_world / legacy._FORESIGHT_PATH).read_text())
    payload["asof"] = clock
    write(production_world, legacy._FORESIGHT_PATH, payload)
    _, result = compose(production_world)
    record = subject(result)["legs"]["foresight_cascade"]["records"][0]
    assert record["native_clocks"]["effective_at"]["value"] == clock
    assert record["native_clocks"]["effective_at"]["grain"] == "INVALID"
    assert record["usable_at_query"] is False


def test_explicit_native_clock_null_retains_its_distinct_reason(production_world):
    payload = json.loads((production_world / legacy._FORESIGHT_PATH).read_text())
    payload["known_at"] = None
    write(production_world, legacy._FORESIGHT_PATH, payload)
    _, result = compose(production_world)
    slot = subject(result)["legs"]["foresight_cascade"]["records"][0]["native_clocks"]["known_at"]
    assert slot == {"value": None, "grain": "UNAVAILABLE", "null_reason": "EXPLICIT_NATIVE_CLOCK_NULL"}


def test_fractional_type_counts_cannot_equal_integer_coverage(production_world):
    from engine.theme_graph import theme_state_production as production
    _, result = compose(production_world)
    state = copy.deepcopy(result["state"])
    subject({"state": state})["legs"]["foresight_cascade"]["coverage"]["observed"] = 1.0
    rehash(state)
    with pytest.raises(ValueError, match="integer"):
        production.validate_state(state)



def test_non_calendar_date_clock_is_preserved_invalid():
    from engine.theme_graph import theme_state_production as production
    assert production.clock_slot("2026-W40-6") == {
        "value": "2026-W40-6", "grain": "INVALID", "null_reason": "NATIVE_CLOCK_INVALID"}


def test_record_position_requires_exact_integer(production_world):
    from engine.theme_graph import theme_state_production as production
    _, result = compose(production_world)
    state = copy.deepcopy(result["state"])
    leg = subject({"state": state})["legs"]["foresight_cascade"]
    record = leg["records"][0]
    record["source_position"] = float(record["source_position"])
    record["record_id"] = production.canonical_sha256({
        "source": leg["source_ref"]["sha256"], "position": record["source_position"],
        "value": record["value"]})
    rehash(state)
    with pytest.raises(ValueError, match="position.*integer"):
        production.validate_state(state)


# Independent S1 B1-B4 regressions. Controlled owner inputs only.
@pytest.mark.parametrize("mutation", ["crosswalk_scope", "local_basket", "graph_capture"])
def test_captured_bundle_derived_scope_cannot_disagree_with_owner_inputs(production_world, mutation):
    payload = json.loads((production_world / legacy._FORESIGHT_PATH).read_text())
    payload["themes"].append({"theme": "travel_owner", "stage": "take", "score": 99})
    write(production_world, legacy._FORESIGHT_PATH, payload)
    bundle, _ = compose(production_world)
    snapshot = bundle.snapshot()
    if mutation == "crosswalk_scope":
        snapshot["crosswalk"]["themes"][0]["foresight_id"] = "travel_owner"
    elif mutation == "local_basket":
        snapshot["subjects"][LOCAL]["basket"]["basket_id"] = "travel"
    else:
        snapshot["graph_capture_id"] = "adapter-snapshot:" + "0" * 64
    text = adapter._json(snapshot)
    bad = adapter.OwnerBundle(text, adapter._sha(text.encode()))
    with pytest.raises(ValueError, match="captured|derived"):
        adapter.compose_production_from_owner_bundle(bad, generated_at=EMITTED)


@pytest.mark.parametrize("mutation", ["future", "malformed", "chronology", "effective", "unavailable", "subject", "query", "graph"])
def test_persisted_source_receipt_cannot_assert_invalid_qualified_empty(production_world, mutation):
    from engine.theme_graph import theme_state_production as production
    write(production_world, legacy._FORESIGHT_PATH, {"asof": EFFECTIVE, "themes": []})
    _, result = compose(production_world, owner_readers=SourceReceiptFixture(production_world, valid_empty=True))
    state = copy.deepcopy(result["state"])
    receipt = subject({"state": state})["legs"]["foresight_cascade"]["qualification"]["source_receipt"]
    if mutation == "future":
        receipt.update(known_at="2026-10-05T09:00:00Z", available_at="2026-10-05T08:00:00Z", recorded_at="2026-10-05T09:00:00Z")
    elif mutation == "malformed":
        receipt["known_at"] = "not-a-clock"
    elif mutation == "chronology":
        receipt["available_at"] = "2026-10-03T10:00:00Z"
    elif mutation == "effective":
        receipt["effective_at"] = "2026-10-04"
    elif mutation == "unavailable":
        receipt["availability"] = "UNAVAILABLE"
    elif mutation == "subject":
        receipt["subject_id"] = LOCAL
    elif mutation == "query":
        receipt["query"] = {"effective_at": EFFECTIVE, "known_at": "2026-10-05T12:00:00Z"}
    else:
        receipt["graph_generation_id"] = "foreign-graph"
    rehash(state)
    for call in (
        lambda: production.validate_state(state),
        lambda: production.read_subject(state, node_id="theme:grid", effective_at=EFFECTIVE, known_at=KNOWN),
    ):
        with pytest.raises(ValueError):
            call()


@pytest.mark.parametrize("claim", ["status", "historical_knowability"])
def test_persisted_source_qualification_requires_nonnull_receipt(production_world, claim):
    from engine.theme_graph import theme_state_production as production
    _, result = compose(production_world)
    state = copy.deepcopy(result["state"])
    q = subject({"state": state})["legs"]["foresight_cascade"]["qualification"]
    q[claim] = "SOURCE_QUALIFIED_RIGHTS_UNAVAILABLE" if claim == "status" else "OWNER_RECEIPT_BOUND"
    rehash(state)
    with pytest.raises(ValueError, match="receipt"):
        production.validate_state(state)


def test_native_effective_axis_is_separate_from_later_knowledge_axis(production_world):
    from engine.theme_graph import theme_state_production as production
    doc = json.loads((production_world / legacy._FORESIGHT_PATH).read_text())
    doc.update(asof="2026-10-04T10:00:00Z", known_at="2026-10-04T10:00:00Z",
               available_at="2026-10-04T09:00:00Z", recorded_at="2026-10-04T10:00:00Z",
               generated_at="2026-10-04T08:00:00Z")
    write(production_world, legacy._FORESIGHT_PATH, doc)
    _, result = compose(production_world)
    leg = subject(result)["legs"]["foresight_cascade"]
    record = leg["records"][0]
    assert record["value"]["score"] == 0
    assert record["usable_at_query"] is False
    assert "NATIVE_SOURCE_EFFECTIVE_AFTER_CUTOFF" in record["reason_codes"]
    assert leg["freshness"] == "FUTURE"
    state = copy.deepcopy(result["state"])
    subject({"state": state})["legs"]["foresight_cascade"]["records"][0]["usable_at_query"] = True
    rehash(state)
    with pytest.raises(ValueError, match="effective"):
        production.validate_state(state)


def test_unqualified_native_emission_order_is_not_invented_artifact_law(production_world):
    doc = json.loads((production_world / legacy._FORESIGHT_PATH).read_text())
    doc.update(asof="2026-10-03T07:00:00Z", known_at="2026-10-03T09:00:00Z",
               available_at="2026-10-03T08:00:00Z", recorded_at="2026-10-03T09:00:00Z",
               generated_at="2026-10-03T11:00:00Z")
    write(production_world, legacy._FORESIGHT_PATH, doc)
    _, result = compose(production_world)
    record = subject(result)["legs"]["foresight_cascade"]["records"][0]
    assert record["usable_at_query"] is True
    assert record["native_clocks"]["emitted_at"]["value"] == doc["generated_at"]


@pytest.mark.parametrize("same_value", [True, False])
def test_same_clock_divergence_is_named_without_erasing_history(production_world, same_value):
    from engine.theme_graph import theme_state_production as production
    rows = [{"theme": "grid", "asof": EFFECTIVE, "divergence": 0},
            {"theme": "grid", "asof": EFFECTIVE, "divergence": 0 if same_value else 9}]
    (production_world / legacy._DIVERGENCE_LOG_PATH).write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    _, result = compose(production_world)
    leg = subject(result)["legs"]["divergence_log"]
    assert [r["value"] for r in leg["records"]] == rows
    assert leg["conflicts"][0]["reason"] == ("DUPLICATE_SAME_CLOCK_DIVERGENCE" if same_value else "CONFLICTING_SAME_CLOCK_DIVERGENCE")
    assert leg["conflicts"][0]["record_ids"] == [r["record_id"] for r in leg["records"]]
    state = copy.deepcopy(result["state"])
    subject({"state": state})["legs"]["divergence_log"]["conflicts"] = []
    rehash(state)
    with pytest.raises(ValueError, match="divergence"):
        production.validate_state(state)


def test_distinct_clock_and_explicit_native_revision_divergence_remain_history(production_world):
    rows = [{"theme": "grid", "asof": "2026-10-02", "divergence": 0},
            {"theme": "grid", "asof": EFFECTIVE, "divergence": 9, "revision_id": "native-a"},
            {"theme": "grid", "asof": EFFECTIVE, "divergence": 0, "revision_id": "native-b"},
            {"theme": "grid", "divergence": None}]
    (production_world / legacy._DIVERGENCE_LOG_PATH).write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    _, result = compose(production_world)
    leg = subject(result)["legs"]["divergence_log"]
    assert [r["value"] for r in leg["records"]] == rows
    assert leg["conflicts"] == []



@pytest.mark.parametrize("known", ["2026-10-04", "2026-10-03"])
def test_receipt_date_precision_requires_proven_knowledge_day(production_world, known):
    change = lambda result: [receipt.update(known_at=known, available_at=known, recorded_at=known)
                             for receipt in result["source_receipts"].values()]
    owner = SourceReceiptFixture(production_world, change=change)
    if known == "2026-10-04":
        with pytest.raises(ValueError, match="precision"):
            compose(production_world, owner_readers=owner)
    else:
        _, result = compose(production_world, owner_readers=owner)
        assert subject(result)["legs"]["foresight_cascade"]["qualification"]["historical_knowability"] == "OWNER_RECEIPT_BOUND"


def test_standalone_read_receipt_checks_source_receipt_clocks(production_world):
    from engine.theme_graph import theme_state_production as production
    _, result = compose(production_world, owner_readers=SourceReceiptFixture(production_world))
    read = production.read_subject(result["state"], node_id="theme:grid", effective_at=EFFECTIVE, known_at=KNOWN)
    read["subject"]["legs"]["foresight_cascade"]["qualification"]["source_receipt"]["known_at"] = "not-a-clock"
    with pytest.raises(ValueError):
        production.validate_read_receipt(read)


@pytest.mark.parametrize("effective,want", [("2026-10-03T09:59:59Z", False),
    ("2026-10-03T10:00:00Z", True), ("2026-10-03", True)])
def test_native_effective_cutoff_precise_equal_and_session_precision(production_world, effective, want):
    doc = json.loads((production_world / legacy._FORESIGHT_PATH).read_text())
    doc["asof"] = "2026-10-03T10:00:00Z"
    write(production_world, legacy._FORESIGHT_PATH, doc)
    bundle = adapter.capture_owner_bundle(production_world, effective_at=effective, known_at=KNOWN)
    result = adapter.compose_production_from_owner_bundle(bundle, generated_at=EMITTED)
    record = subject(result)["legs"]["foresight_cascade"]["records"][0]
    assert record["usable_at_query"] is want
    assert ("NATIVE_SOURCE_EFFECTIVE_AFTER_CUTOFF" in record["reason_codes"]) is (not want)
