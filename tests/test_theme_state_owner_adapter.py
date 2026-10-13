"""Controlled owner-code tests; no natural qualification or publisher execution."""
from __future__ import annotations

import copy
import dataclasses
import datetime as dt
import json
import hashlib
from pathlib import Path

import pandas as pd
import pytest
import yaml

from engine.neuralweb import thematic_state as legacy
from engine.neuralweb import theme_state_adapter as adapter
from engine.theme_graph import identity, identity_resolution, ontology, rights, store, theme_state
from engine import basket_membership_pit as pit
from lib import config

CONTROLLED_CONFIG_ROOT = Path(__file__).parent / "fixtures/theme_state_owner"
CONTROLLED_CONFIG_HASHES = {
    "theme_crosswalk.yml": "76256cd177ea8664b24fdeb915ca7c9e4f24a07bc23d22f40ba0f2a42ba8b48a",
    "theme_sources.yml": "8bb48fb9117043f6ee45ab156a773aedda6bfaed688fc38a9c1ada7d881cd97e",
}


def controlled_config_bytes(name):
    """Frozen test inputs; missing/corrupt files never fall back to live sources."""
    raw = (CONTROLLED_CONFIG_ROOT / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == CONTROLLED_CONFIG_HASHES[name]
    return raw
EFFECTIVE = "2026-10-03"
KNOWN = "2026-10-03T12:00:00Z"
EMITTED = "2026-10-04T12:00:00Z"
LOCAL = "ltheme:finviz:power_grid"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def narrative():
    # Bounded source reproduction of accepted main's real numeric dict legs and
    # recommended-five entries, not a full cluster or a natural publication.
    return {"schema": "narrative_emergence.v1", "region": "us", "as_of": "2026-10-02", "narratives": [
        {"signature": "b1d5c09e6b31", "n": 5,
         "legs": {"tighten": .563, "cohesion": .302, "momentum": .03, "novelty": 1., "size": .6},
         "recommended": [{"ticker": t} for t in ["HUBB", "BDC", "APG", "FLS", "IDCC"]]},
        {"signature": "6eed05ff174f", "n": 7,
         "legs": {"tighten": 1., "cohesion": .28, "momentum": 0., "novelty": 1., "size": 1.},
         "recommended": [{"ticker": t} for t in ["PLNT", "ZTS", "IBP", "SHAK", "PAHC"]]},
        {"signature": "b872817b28b8", "n": 5,
         "legs": {"tighten": .837, "cohesion": .285, "momentum": .957, "novelty": 1., "size": .6},
         "recommended": [{"ticker": t} for t in ["CART", "QNST", "ABNB", "DOCS", "DV"]]},
    ]}


@pytest.fixture
def world(tmp_path, monkeypatch):
    # Root-admitted controlled observation clock. Only this fixture-local
    # adapter namespace changes; actual owner APIs and global datetime do not.
    import types
    class ControlledCaptureClock(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            instant = dt.datetime.fromisoformat("2026-10-04T11:00:00+00:00")
            return instant.astimezone(tz) if tz is not None else instant.replace(tzinfo=None)
    namespace = {name: getattr(dt, name) for name in dir(dt) if not name.startswith("__")}
    namespace["datetime"] = ControlledCaptureClock
    monkeypatch.setattr(adapter, "dt", types.SimpleNamespace(**namespace))
    root = tmp_path / "controlled-repo"
    root.mkdir()
    crosswalk = yaml.safe_load(controlled_config_bytes("theme_crosswalk.yml"))
    (root / "config").mkdir()
    (root / "config/theme_crosswalk.yml").write_text(yaml.safe_dump(crosswalk, allow_unicode=True, sort_keys=False))
    (root / "config/theme_sources.yml").write_bytes(controlled_config_bytes("theme_sources.yml"))
    write(root / legacy._NARRATIVE_PATH, narrative())
    write(root / legacy._FORESIGHT_PATH, {"asof": EFFECTIVE, "themes": [
        {"theme": c.get("foresight_id", c["id"]), "stage": "watch", "tier": "A", "score": 0,
         "entry_ready": False, "bottleneck_band": None} for c in crosswalk["themes"]]})
    write(root / legacy._BASKETS_PATH, {"as_of": EFFECTIVE, "theme_intel": {"themes": [
        {"id": "power_grid", "score": 0, "label": "watch", "label_en": "Watch", "label_zh": "观察", "crowding": None, "reco": False}]}})
    write(root / legacy._RADAR_PATH, {"as_of": EFFECTIVE, "hypotheses": []})
    write(root / legacy._RADAR_ENRICHED_PATH, {"as_of": EFFECTIVE, "flags": []})
    write(root / legacy._SUBSECTOR_PATH, {"asof": EFFECTIVE, "themes": [
        {"theme": "power_grid", "quadrant": "Leading", "rs": 0., "z_accel": 0., "emerging_score": None}]})
    div = root / legacy._DIVERGENCE_LOG_PATH
    div.parent.mkdir(parents=True, exist_ok=True)
    div.write_text(json.dumps({"theme_id": crosswalk["themes"][0]["id"], "asof": EFFECTIVE, "quadrant": "neutral", "divergence": 0., "narrative_pct": None, "money_pct": 0.}) + "\n")
    for suite, bid, tickers in [("baskets", "power_grid", ["HUBB"]), ("baskets", "housing", ["IBP"]),
                                ("baskets", "travel", ["ABNB"]), ("baskets_china_ths", "thsc900001", ["600001.SS"])]:
        path = root / "data" / suite / "membership.json"
        doc = json.loads(path.read_text()) if path.exists() else {"version": EFFECTIVE, "baskets": {}}
        doc["baskets"][bid] = {"members": [{"ticker": t, "added": "2026-10-01", "removed": None} for t in tickers]}
        write(path, doc)
        hp = path.with_name("membership_history.parquet")
        old = pd.read_parquet(hp).to_dict("records") if hp.exists() else []
        rows = [{"suite": suite, "basket_id": bid, "ticker": t, "snapshot_date": EFFECTIVE,
                 "added": "2026-10-01", "removed": None, "source_shape": "membership", "members_sha": "fixture"} for t in tickers]
        pd.DataFrame(old + rows, columns=list(pit.COLUMNS)).to_parquet(hp, index=False)
    nodes = []
    for c in crosswalk["themes"]:
        nodes.append({"node_id": identity.theme_node_id(c["id"]), "kind": "theme", "name_en": c.get("name_en"), "name_zh": c.get("name_zh")})
    for node, suite, bid in [(LOCAL, "baskets", "power_grid"), ("ltheme:finviz:housing", "baskets", "housing"),
                             ("ltheme:finviz:travel", "baskets", "travel"), ("ltheme:ths:900001", "baskets_china_ths", "thsc900001")]:
        nodes.append({"node_id": node, "kind": "local_theme", "name_en": node, "name_zh": "本地",
                      "source_meta": json.dumps({"suite": suite, "basket_id": bid})})
    for suite, ticker in [("baskets", "HUBB"), ("baskets", "IBP"), ("baskets", "ABNB"), ("baskets_china_ths", "600001.SS")]:
        nodes.append({"node_id": identity.company_node_id(suite, ticker, breaks={}), "kind": "company", "name_en": ticker})
    for row in nodes:
        row.update(status="ACTIVE", birth_date="2026-10-01", computed_at="2026-10-01T00:00:00Z", engine_version=store.ENGINE_VERSION)
    graph = root / "data/theme_graph"
    graph.mkdir(parents=True)
    pd.DataFrame(nodes, columns=list(store.NODE_COLUMNS)).to_parquet(graph / "nodes.parquet", index=False)
    pd.DataFrame(columns=list(store.NODE_LIFECYCLE_COLUMNS)).to_parquet(graph / "node_lifecycle.parquet", index=False)
    edge = {"edge_id": "fixture-expression", "type": "EXPRESSES", "src": LOCAL,
            "dst": identity.theme_node_id(crosswalk["themes"][0]["id"]), "valid_from": "2026-10-01", "valid_to": None,
            "belief_time": "2026-10-01", "evidence_time": "2026-10-01", "computed_at": "2026-10-01T00:00:00Z",
            "source_class": "house_curation", "evidence_refs": "[]"}
    pd.DataFrame([edge], columns=list(store.EDGE_COLUMNS)).to_parquet(graph / "edges.parquet", index=False)
    (graph / "probation").mkdir()
    store_probation = graph / "probation" / "proposals.jsonl"
    store_probation.write_text("")
    ref = root / "data/reference"
    ref.mkdir()
    pd.DataFrame([{"inception_code": t, "security_id": "fixture-security:" + t, "issuer_id": "fixture-issuer:" + t,
                   "issuer_state": "RESOLVED", "security_state": None, "listing_key": ("CN-" if t.endswith(".SS") else "US-") + t}
                  for t in ["HUBB", "IBP", "ABNB", "600001.SS"]]).to_parquet(ref / "security_master.parquet", index=False)
    pd.DataFrame(columns=["vendor", "vendor_symbol", "security_id", "valid_from", "valid_to"]).to_parquet(ref / "vendor_aliases.parquet", index=False)
    write(ref / "_receipt.json", {"generated_at": "2026-10-02T09:00:00Z", "code_version": "controlled-fixture", "identity_exceptions": []})
    # Owner APIs still run; only their filesystem configuration is controlled.
    monkeypatch.setattr(config, "data_dir", lambda: root / "data")
    return root, crosswalk


def capture(world, **options):
    return adapter.capture_owner_bundle(world[0], effective_at=EFFECTIVE, known_at=KNOWN, **options)


def test_real_owner_apis_are_called_and_date_only_knowledge_is_not_promoted(world, monkeypatch):
    calls = []
    for module, name in [(ontology, "compose_neighborhood"), (pit, "members_asof"), (identity_resolution, "resolve_graph_node_identity")]:
        original = getattr(module, name)
        def spy(*a, _fn=original, _name=name, **k):
            calls.append(_name)
            return _fn(*a, **k)
        monkeypatch.setattr(module, name, spy)
    bundle = capture(world)
    raw = bundle.snapshot()
    assert {"compose_neighborhood", "members_asof", "resolve_graph_node_identity"} <= set(calls)
    assert raw["subjects"][LOCAL]["native_reads"]["membership"]["value"]["members"] == ["HUBB"]
    result = adapter.compose_from_owner_bundle(bundle, generated_at=EMITTED)
    local = next(s for s in result["state"]["subjects"] if s["node_id"] == LOCAL)
    assert local["eligibility"]["status"] == "NOT_QUALIFIED"
    assert local["owner_receipts"]["membership"] is None
    assert result["native_observations"][LOCAL]["narrative_measurements"]["fact"]["narratives"][0]["legs"]["momentum"] == .03
    overlap = result["native_observations"][LOCAL]["forming_narrative_recommended_ticker_overlap"]
    assert overlap["availability"] == "UNAVAILABLE" and overlap["fact"] is None


def test_full_v1_candidate_reuses_incumbent_and_preserves_every_field(world, monkeypatch):
    bundle = capture(world)
    instant = dt.datetime.fromisoformat(EMITTED.replace("Z", "+00:00"))
    class Clock(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return instant if tz else instant.replace(tzinfo=None)
    monkeypatch.setattr(legacy, "datetime", Clock)
    baseline = legacy.compose(world[0])
    result = adapter.compose_from_owner_bundle(bundle, generated_at=EMITTED)
    expected = copy.deepcopy(baseline)
    for block in expected["themes"]:
        block["narrative"] = None
    assert result["legacy_baseline"] == baseline
    assert result["legacy_candidate"] == expected
    assert [t["theme_id"] for t in expected["themes"]] == [c["id"] for c in world[1]["themes"]]
    assert expected["authority"] == legacy.AUTHORITY_BLOCK
    assert expected["sources"] == baseline["sources"]
    assert result["shadow"]["same_input_bundle_sha256"] == bundle.bundle_sha256


def test_bundle_is_immutable_and_composition_reads_no_changed_source(world):
    bundle = capture(world)
    first = adapter.compose_from_owner_bundle(bundle, generated_at=EMITTED)
    snapshot = bundle.snapshot()
    snapshot["query"]["known_at"] = "2099-01-01"
    write(world[0] / legacy._NARRATIVE_PATH, {"narratives": []})
    second = adapter.compose_from_owner_bundle(bundle, generated_at=EMITTED)
    assert first == second
    with pytest.raises(dataclasses.FrozenInstanceError):
        bundle.bundle_sha256 = "0" * 64
    forged = dataclasses.replace(bundle, payload_json=bundle.payload_json.replace("HUBB", "EVIL"))
    with pytest.raises(ValueError, match="digest"):
        adapter.compose_from_owner_bundle(forged, generated_at=EMITTED)


@pytest.mark.parametrize("mode", ["missing", "malformed", "empty"])
def test_narrative_absence_is_not_an_admitted_empty(world, mode):
    path = world[0] / legacy._NARRATIVE_PATH
    if mode == "missing":
        path.unlink()
    elif mode == "malformed":
        path.write_text("not-json")
    else:
        write(path, {"as_of": EFFECTIVE, "narratives": []})
    result = adapter.compose_from_owner_bundle(capture(world), generated_at=EMITTED)
    observation = result["native_observations"][LOCAL]["forming_narrative_recommended_ticker_overlap"]
    assert observation["availability"] == "UNAVAILABLE"
    assert observation["null_reason"]
    assert observation["fact"] is None


def test_unmapped_cn_local_and_canonical_subjects_remain_distinct(world):
    result = adapter.compose_from_owner_bundle(capture(world), generated_at=EMITTED)
    by_id = {s["node_id"]: s for s in result["state"]["subjects"]}
    assert by_id["ltheme:ths:900001"]["mapping"]["state"] == "UNMAPPED"
    assert by_id["ltheme:ths:900001"]["native_id"] == "900001"
    assert by_id[LOCAL]["mapping"]["state"] == "MAPPED"
    assert all(by_id[identity.theme_node_id(c["id"])]["kind"] == "canonical_theme" for c in world[1]["themes"])
    assert result["native_observations"]["ltheme:ths:900001"]["membership_owner_read"]["fact"]["members"] == ["600001.SS"]


@pytest.mark.parametrize("clock,expected", [("2026-09-01", "STALE"), ("2026-10-10", "FUTURE"), (None, "UNKNOWN")])
def test_native_clock_states_do_not_refresh_with_generation(world, clock, expected):
    doc = narrative()
    doc["as_of"] = clock
    write(world[0] / legacy._NARRATIVE_PATH, doc)
    result = adapter.compose_from_owner_bundle(capture(world), generated_at=EMITTED)
    observation = result["native_observations"][LOCAL]["narrative_measurements"]
    assert observation["freshness"] == expected
    assert observation["native_clocks"]["effective_at"] == clock
    assert observation["native_clocks"]["known_at"] is None
    assert observation["observed_at"] != clock


def test_unreadable_owner_history_does_not_masquerade_as_empty(world):
    (world[0] / "data/baskets/membership_history.parquet").write_bytes(b"broken")
    result = adapter.compose_from_owner_bundle(capture(world), generated_at=EMITTED)
    native = result["native_observations"][LOCAL]["membership_owner_read"]
    assert native["availability"] == "UNAVAILABLE"
    assert native["null_reason"] == "OWNER_HISTORY_UNREADABLE"


def test_source_mutation_during_owner_reads_refuses_mixed_bundle(world, monkeypatch):
    original = ontology.compose_neighborhood
    def mutate(*a, **k):
        value = original(*a, **k)
        write(world[0] / legacy._NARRATIVE_PATH, {"as_of": EFFECTIVE, "narratives": []})
        return value
    monkeypatch.setattr(ontology, "compose_neighborhood", mutate)
    with pytest.raises(ValueError, match="changed during capture"):
        capture(world)


def test_actual_emission_and_correction_knowledge_are_not_backdated(world):
    bundle = capture(world)
    first = adapter.compose_from_owner_bundle(bundle, generated_at=EMITTED)
    read = theme_state.read_theme_state(first["state"], LOCAL, effective_at=EFFECTIVE, known_at=KNOWN)
    assert read["status"] == "UNAVAILABLE"
    assert "STATE_NOT_YET_EMITTED" in read["reason_codes"]
    later = adapter.capture_owner_bundle(world[0], effective_at=EFFECTIVE, known_at="2026-10-05T12:00:00Z")
    corrected = adapter.compose_from_owner_bundle(later, generated_at="2026-10-05T12:00:00Z", previous=first["state"])
    assert corrected["state"]["correction"]["state_sha256"] == first["state"]["state_sha256"]
    assert first["state"]["known_at"] == KNOWN



class QualifiedFixtureReader:
    """Prequalified controlled receipts; no production authenticator is supplied."""
    def __init__(self, root, *, omit_identity=False, empty_narrative=False, change=None):
        self.root, self.omit_identity, self.empty_narrative, self.change = root, omit_identity, empty_narrative, change

    def read_state_qualification(self, *, node_id, query, graph_capture_id, native_reads, source_sha256):
        if not node_id.startswith("ltheme:"):
            return None
        native = native_reads["membership"]
        if native["availability"] != "AVAILABLE":
            return None
        members = native["value"]["members"]
        def receipt(role, payload, availability="AVAILABLE"):
            return {"owner": "fixture-qualified." + role + ":" + node_id, "schema": "fixture.accepted_owner_read/v1",
                    "generation_id": "fixture-qualified-generation", "graph_generation_id": graph_capture_id,
                    "subject_id": node_id, "query": copy.deepcopy(query), "effective_at": "2026-10-02",
                    "available_at": "2026-10-02T08:00:00Z", "known_at": "2026-10-02T09:00:00Z",
                    "recorded_at": "2026-10-02T09:00:00Z", "availability": availability,
                    "payload": payload, "sha256": theme_state.canonical_sha256(payload)}
        actual = {}
        for ticker in members:
            matches = [(nid, r["value"]) for nid, r in native_reads["identity"].items()
                       if identity_resolution._best_effort_symbol(nid) == ticker and r["availability"] == "AVAILABLE"]
            nid, resolved = matches[0]
            actual[ticker] = {"node_id": nid, "security_id": resolved.get("security_id"), "issuer_id": resolved.get("issuer_id")}
        member_rows = [{"ticker": ticker, "security_id": r["security_id"], "issuer_id": r["issuer_id"]} for ticker, r in actual.items()]
        payload = {"status": "AVAILABLE" if members else "VALID_EMPTY", "basket_id": native["value"]["basket_id"],
                   "members": member_rows, "declared_count": len(members), "eligible_count": len(members), "observed_count": len(members),
                   "basis": "controlled_prequalified_owner_population", "era": "OBSERVED",
                   "native_owner_read_sha256": theme_state.canonical_sha256(native)}
        roles = {"membership": receipt("membership", payload, payload["status"])}
        if not self.omit_identity:
            payload = {"status": "RESOLVED", "member_identities": actual,
                       "native_owner_read_sha256": theme_state.canonical_sha256(native_reads["identity"])}
            roles["identity"] = receipt("identity", payload)
        doc = json.loads((self.root / legacy._NARRATIVE_PATH).read_text())
        sources = {"narrative_emergence": receipt("narrative", doc, "VALID_EMPTY" if self.empty_narrative else "AVAILABLE")}
        result = {"owner_receipts": roles, "source_receipts": sources}
        if self.change:
            self.change(result)
        return result


@pytest.mark.parametrize("node,ticker", [(LOCAL, "HUBB"), ("ltheme:finviz:housing", "IBP"), ("ltheme:finviz:travel", "ABNB")])
def test_actual_owner_population_and_real_dict_recommended_subset_join(world, node, ticker):
    reader = QualifiedFixtureReader(world[0])
    result = adapter.compose_from_owner_bundle(capture(world, owner_readers=reader), generated_at=EMITTED)
    observation = result["native_observations"][node]["forming_narrative_recommended_ticker_overlap"]
    assert observation["availability"] == "POSITIVE"
    assert observation["fact"]["matched_tickers"] == [ticker]
    assert observation["fact"]["coverage_basis"] == "top_5_entry_quality_subset"
    assert all(t["narrative"] is None for t in result["legacy_candidate"]["themes"])


def test_missing_identity_qualification_cannot_bind_recommended_overlap(world):
    result = adapter.compose_from_owner_bundle(capture(world, owner_readers=QualifiedFixtureReader(world[0], omit_identity=True)), generated_at=EMITTED)
    observation = result["native_observations"][LOCAL]["forming_narrative_recommended_ticker_overlap"]
    assert observation["availability"] == "UNAVAILABLE" and observation["fact"] is None


def test_unresolved_actual_identity_cannot_be_promoted_by_success_receipt(world):
    (world[0] / "data/reference/security_master.parquet").unlink()
    with pytest.raises(ValueError, match="identity"):
        adapter.compose_from_owner_bundle(capture(world, owner_readers=QualifiedFixtureReader(world[0])), generated_at=EMITTED)


def test_qualified_zero_overlap_is_measured_and_unknown_population_is_not(world):
    doc = narrative()
    for row in doc["narratives"]:
        row["recommended"] = [{"ticker": "OTHER"}]
    write(world[0] / legacy._NARRATIVE_PATH, doc)
    result = adapter.compose_from_owner_bundle(capture(world, owner_readers=QualifiedFixtureReader(world[0])), generated_at=EMITTED)
    zero = result["native_observations"][LOCAL]["forming_narrative_recommended_ticker_overlap"]
    assert zero["availability"] == "VALID_EMPTY"
    assert zero["fact"]["has_overlap"] is False and zero["coverage"]["declared"] == 1
    unknown = adapter.compose_from_owner_bundle(capture(world), generated_at=EMITTED)["native_observations"][LOCAL]["forming_narrative_recommended_ticker_overlap"]
    assert unknown["coverage"]["declared"] is None and unknown["fact"] is None


def test_explicit_qualified_narrative_empty_has_distinct_admission(world):
    write(world[0] / legacy._NARRATIVE_PATH, {"region": "us", "as_of": "2026-10-02", "narratives": []})
    result = adapter.compose_from_owner_bundle(capture(world, owner_readers=QualifiedFixtureReader(world[0], empty_narrative=True)), generated_at=EMITTED)
    assert result["native_observations"][LOCAL]["forming_narrative_recommended_ticker_overlap"]["availability"] == "VALID_EMPTY"


def test_qualified_source_cannot_restamp_old_native_effective_clock(world):
    def change(result):
        result["source_receipts"]["narrative_emergence"]["effective_at"] = "2026-10-03"
    with pytest.raises(ValueError, match="native source clock"):
        adapter.compose_from_owner_bundle(capture(world, owner_readers=QualifiedFixtureReader(world[0], change=change)), generated_at=EMITTED)


def test_predecessor_optional_fields_envelopes_and_sources_survive(world, monkeypatch):
    # Pin the incumbent's staleness clock; its 5-day window otherwise ages the fixture legs on the wall clock.
    instant = dt.datetime.fromisoformat(EMITTED.replace("Z", "+00:00"))
    class Clock(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return instant if tz else instant.replace(tzinfo=None)
    monkeypatch.setattr(legacy, "datetime", Clock)
    baseline = legacy.compose(world[0])
    baseline["schema_version"] = "1.0"
    baseline["produced_by"] = "incumbent"
    baseline["prior_optional"] = {"value": 0, "native_known_at": None}
    baseline["themes"][0]["leadership"] = {"observation": {"coverage": {"expected": 4, "observed": 2}, "score": None}, "clock": "2026-09-01"}
    write(world[0] / "data/neuralweb/theme_state.json", baseline)
    result = adapter.compose_from_owner_bundle(capture(world), generated_at=EMITTED)
    candidate = result["legacy_candidate"]
    assert candidate["prior_optional"] == baseline["prior_optional"]
    assert candidate["produced_by"] == "incumbent" and candidate["schema_version"] == "1.0"
    assert candidate["themes"][0]["leadership"] == baseline["themes"][0]["leadership"]
    assert not any(d["reason"] == "UNEXPECTED_DIFFERENCE" for d in result["shadow"]["differences"])


def test_plain_success_dictionary_is_not_an_owner_reader(world):
    with pytest.raises(TypeError, match="capability"):
        capture(world, owner_readers={"allowed": True})


def test_same_graph_but_different_bundle_cannot_supply_a_compatibility_projection(world):
    first_bundle = capture(world)
    first = adapter.compose_from_owner_bundle(first_bundle, generated_at=EMITTED)
    write(world[0] / legacy._NARRATIVE_PATH, {"region": "us", "as_of": EFFECTIVE, "narratives": []})
    second_bundle = capture(world)
    assert first_bundle.snapshot()["graph_capture_id"] == second_bundle.snapshot()["graph_capture_id"]
    with pytest.raises(ValueError, match="mixed"):
        adapter.legacy_projection_for_owner(first["state"], second_bundle)


def test_shadow_rejects_arbitrary_comparison_payload_from_other_inputs(world):
    bundle = capture(world)
    result = adapter.compose_from_owner_bundle(bundle, generated_at=EMITTED)
    changed = copy.deepcopy(result["legacy_baseline"])
    changed["themes"][0]["name_en"] = "DIFFERENT INPUT"
    with pytest.raises(ValueError, match="same captured"):
        adapter.compare_shadow(changed, result["state"], result["legacy_candidate"], bundle)


def test_qualified_membership_cannot_attach_another_security_to_ticker(world):
    def change(result):
        r = result["owner_receipts"]["membership"]
        if r["payload"]["members"]:
            r["payload"]["members"][0]["security_id"] = "other-security"
            r["sha256"] = theme_state.canonical_sha256(r["payload"])
    with pytest.raises(ValueError, match="member identity"):
        adapter.compose_from_owner_bundle(capture(world, owner_readers=QualifiedFixtureReader(world[0], change=change)), generated_at=EMITTED)


def test_cn_cannot_assert_zero_from_global_us_narrative(world):
    result = adapter.compose_from_owner_bundle(capture(world, owner_readers=QualifiedFixtureReader(world[0])), generated_at=EMITTED)
    observation = result["native_observations"]["ltheme:ths:900001"]["forming_narrative_recommended_ticker_overlap"]
    assert observation["availability"] == "UNAVAILABLE" and observation["fact"] is None


def test_cn_unmapped_local_uses_its_actual_narrative_owner_scope(world):
    doc = {"region": "cn", "as_of": "2026-10-02", "narratives": [
        {"signature": "controlled-cn", "n": 7, "legs": {"tighten": .6, "cohesion": .3, "momentum": .1, "novelty": 1., "size": .6},
         "recommended": [{"ticker": t} for t in ["600001.SS", "600002.SS", "600003.SS", "600004.SS", "600005.SS"]]}]}
    write(world[0] / "site/chinabasketdata/narrative_emergence.json", doc)
    class CNReader(QualifiedFixtureReader):
        def read_state_qualification(self, **kwargs):
            result = super().read_state_qualification(**kwargs)
            if kwargs["node_id"] == "ltheme:ths:900001":
                receipt = result["source_receipts"].pop("narrative_emergence")
                receipt["payload"] = doc
                receipt["sha256"] = theme_state.canonical_sha256(doc)
                result["source_receipts"]["narrative_emergence_cn"] = receipt
            return result
    result = adapter.compose_from_owner_bundle(capture(world, owner_readers=CNReader(world[0])), generated_at=EMITTED)
    observation = result["native_observations"]["ltheme:ths:900001"]["forming_narrative_recommended_ticker_overlap"]
    assert observation["availability"] == "POSITIVE"
    assert observation["fact"]["matched_tickers"] == ["600001.SS"]
    subject = next(s for s in result["state"]["subjects"] if s["node_id"] == "ltheme:ths:900001")
    assert subject["mapping"]["state"] == "UNMAPPED"
    assert subject["eligibility"]["status"] == "NOT_QUALIFIED"


class InternalRightsFixtureReader(QualifiedFixtureReader):
    def read_state_qualification(self, **kwargs):
        result = super().read_state_qualification(**kwargs)
        native = kwargs["native_reads"]["rights"]
        if (result is None or native["availability"] != "AVAILABLE" or not native["known_family"]
                or native["licensing"][0] is not True):
            return result
        mr = next(iter(result["owner_receipts"].values()))
        receipt = copy.deepcopy(mr)
        receipt["owner"] = "fixture-qualified.rights:" + kwargs["node_id"]
        payload = {"allowed": True, "purpose": "research_internal", "revision": "controlled-existing-registry",
                   "registry_sha256": kwargs["source_sha256"]["rights_registry"],
                   "native_owner_read_sha256": theme_state.canonical_sha256(native)}
        receipt["payload"], receipt["sha256"] = payload, theme_state.canonical_sha256(payload)
        result["owner_receipts"]["rights"] = receipt
        return result


def test_actual_rights_tuple_is_bound_without_publication_upgrade(world):
    bundle = capture(world, owner_readers=InternalRightsFixtureReader(world[0]))
    native = bundle.snapshot()["subjects"][LOCAL]["native_reads"]["rights"]
    assert len(native["licensing"]) == 3 and all(type(v) is bool for v in native["licensing"])
    result = adapter.compose_from_owner_bundle(bundle, generated_at=EMITTED)
    subject = next(s for s in result["state"]["subjects"] if s["node_id"] == LOCAL)
    assert subject["owner_receipts"]["rights"]["payload"]["purpose"] == "research_internal"
    assert result["publication_allowed"] is False
    assert subject["eligibility"]["status"] == "NOT_QUALIFIED"


def test_emission_before_actual_capture_is_refused(world):
    with pytest.raises(ValueError, match="emission precedes"):
        adapter.compose_from_owner_bundle(capture(world), generated_at=KNOWN)

# Independent-review owning regressions: actual unchanged owner APIs, fixtures only.
def test_rehashed_successor_interpretation_cannot_escape_bundle_shadow(world):
    bundle = capture(world, owner_readers=QualifiedFixtureReader(world[0]))
    result = adapter.compose_from_owner_bundle(bundle, generated_at=EMITTED)
    changed = copy.deepcopy(result["state"])
    local = next(s for s in changed["subjects"] if s["node_id"] == LOCAL)
    assert local["observations"]
    local["observations"] = {}
    digest = theme_state._state_digest(changed)
    changed.update(generation_id=digest[:32], state_sha256=digest)
    theme_state.validate_state(changed)  # valid artifact is not the bundle's interpretation
    with pytest.raises(ValueError, match="deterministic owner bundle assembly"):
        adapter.legacy_projection_for_owner(changed, bundle)


def test_qualified_foresight_has_explicit_source_specific_disposition(world):
    class Reader(QualifiedFixtureReader):
        def read_state_qualification(self, **kwargs):
            result = super().read_state_qualification(**kwargs)
            if result is None:
                return None
            receipt = copy.deepcopy(result["source_receipts"]["narrative_emergence"])
            doc = json.loads((self.root / legacy._FORESIGHT_PATH).read_text())
            receipt.update(owner="fixture-qualified.foresight:" + kwargs["node_id"],
                           effective_at=doc["asof"], available_at="2026-10-03T08:00:00Z",
                           known_at="2026-10-03T09:00:00Z", recorded_at="2026-10-03T09:00:00Z",
                           payload=doc, sha256=theme_state.canonical_sha256(doc))
            result["source_receipts"]["foresight_cascade"] = receipt
            return result
    bundle = capture(world, owner_readers=Reader(world[0]))
    result = adapter.compose_from_owner_bundle(bundle, generated_at=EMITTED)
    disposition = result["source_dispositions"][LOCAL]["foresight_cascade"]
    assert disposition["status"] == "QUALIFIED_SOURCE_NOT_ADAPTED"
    assert disposition["reason_code"] == "SUBJECT_SCOPED_FORESIGHT_ADAPTER_NOT_IMPLEMENTED"
    assert disposition["receipt_sha256"] == theme_state.canonical_sha256(
        json.loads((world[0] / legacy._FORESIGHT_PATH).read_text()))
    assert disposition["legacy_fields"] == ["foresight"]
    assert result["shadow"]["successor_surface"][LOCAL]["source_dispositions"]["foresight_cascade"] == disposition
    assert result["shadow"]["parity_accepted"] is False


@pytest.mark.parametrize("native_clock,availability,freshness", [
    ("2026-10-03T13:00:00Z", "UNAVAILABLE", "FUTURE"),
    ("2026-10-03T12:00:00Z", "AVAILABLE", "FRESH"),
    ("2026-10-03", "AVAILABLE", "UNKNOWN"),
])
def test_precise_same_day_and_date_only_clock_boundaries(world, native_clock, availability, freshness):
    doc = narrative()
    doc["as_of"] = native_clock
    write(world[0] / legacy._NARRATIVE_PATH, doc)
    result = adapter.compose_from_owner_bundle(capture(world), generated_at=EMITTED)
    fact = result["native_observations"][LOCAL]["narrative_measurements"]
    assert (fact["availability"], fact["freshness"]) == (availability, freshness)
    assert fact["fact"] == doc
    if freshness == "FUTURE":
        assert fact["null_reason"] == "SOURCE_AFTER_CUTOFF"


def test_list_optional_receipts_match_stable_identity_and_retired_records_are_disposed(world, monkeypatch):
    # Pin the incumbent's staleness clock; its 5-day window otherwise ages the fixture legs on the wall clock.
    instant = dt.datetime.fromisoformat(EMITTED.replace("Z", "+00:00"))
    class Clock(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return instant if tz else instant.replace(tzinfo=None)
    monkeypatch.setattr(legacy, "datetime", Clock)
    previous = legacy.compose(world[0])
    old = next(t for t in previous["themes"] if t["basket_intel"])
    record = old["basket_intel"][0]
    record["native_receipt_extra"] = {"known_at": None, "source_revision": "preserve-this"}
    retired = copy.deepcopy(record)
    retired.update(basket_id="retired-not-in-current-population", score=99,
                   native_receipt_extra={"source_revision": "must-not-merge-by-index"})
    old["basket_intel"].insert(0, retired)
    write(world[0] / "data/neuralweb/theme_state.json", previous)
    result = adapter.compose_from_owner_bundle(capture(world), generated_at=EMITTED)
    current = next(t for t in result["legacy_candidate"]["themes"] if t["theme_id"] == old["theme_id"])
    assert len(current["basket_intel"]) == 1
    assert current["basket_intel"][0]["native_receipt_extra"] == record["native_receipt_extra"]
    assert current["basket_intel"][0]["score"] == 0
    inventory = result["shadow"]["predecessor_optional_inventory"]
    assert any(i["status"] == "PRESERVED" and i["path"].endswith("/native_receipt_extra") for i in inventory)
    assert any(i["status"] == "UNMATCHED_PREDECESSOR_LIST_RECORD"
               and i["prior_record"]["basket_id"] == retired["basket_id"] for i in inventory)


def test_rights_owner_api_interprets_exact_captured_registry_path(world, monkeypatch):
    paths = []
    for name in ("known_families", "licensing_for_family"):
        original = getattr(rights, name)
        def spy(*args, _fn=original, **kwargs):
            paths.append(kwargs.get("path"))
            return _fn(*args, **kwargs)
        monkeypatch.setattr(rights, name, spy)
    bundle = capture(world, owner_readers=InternalRightsFixtureReader(world[0]))
    expected = world[0] / "config/theme_sources.yml"
    assert paths and all(Path(p) == expected for p in paths)
    native = bundle.snapshot()["subjects"][LOCAL]["native_reads"]["rights"]
    assert native["current_bytes_bound"] is True
    assert native["registry_sha256"] == bundle.snapshot()["sources"]["rights_registry"]["sha256"]


def test_removed_family_in_current_captured_registry_cannot_qualify(world):
    path = world[0] / "config/theme_sources.yml"
    doc = yaml.safe_load(path.read_text())
    doc["families"].pop(rights.family_for_node_id(LOCAL))
    path.write_text(yaml.safe_dump(doc))
    bundle = capture(world, owner_readers=InternalRightsFixtureReader(world[0]))
    native = bundle.snapshot()["subjects"][LOCAL]["native_reads"]["rights"]
    assert native["known_family"] is False
    result = adapter.compose_from_owner_bundle(bundle, generated_at=EMITTED)
    local = next(s for s in result["state"]["subjects"] if s["node_id"] == LOCAL)
    assert local["owner_receipts"]["rights"] is None


def test_same_path_cached_pre_revocation_registry_is_typed_unavailable(world):
    path = world[0] / "config/theme_sources.yml"
    family = rights.family_for_node_id(LOCAL)
    assert family in rights.known_families(path=path)  # actual owner's cache, no patch/clear
    doc = yaml.safe_load(path.read_text())
    doc["families"].pop(family)
    path.write_text(yaml.safe_dump(doc))
    bundle = capture(world, owner_readers=InternalRightsFixtureReader(world[0]))
    native = bundle.snapshot()["subjects"][LOCAL]["native_reads"]["rights"]
    assert native["availability"] == "UNAVAILABLE"
    assert native["null_reason"] == "RIGHTS_CACHE_VERSION_UNAVAILABLE"
    result = adapter.compose_from_owner_bundle(bundle, generated_at=EMITTED)
    local = next(s for s in result["state"]["subjects"] if s["node_id"] == LOCAL)
    assert local["owner_receipts"]["rights"] is None


def test_state_bundle_binding_preserves_boolean_value_type(world):
    bundle = capture(world, owner_readers=QualifiedFixtureReader(world[0]))
    result = adapter.compose_from_owner_bundle(bundle, generated_at=EMITTED)
    changed = copy.deepcopy(result["state"])
    local = next(s for s in changed["subjects"] if s["node_id"] == LOCAL)
    value = local["observations"]["forming_narrative_recommended_ticker_overlap"]["value"]
    assert value["has_overlap"] is True
    value["has_overlap"] = 1
    digest = theme_state._state_digest(changed)
    changed.update(generation_id=digest[:32], state_sha256=digest)
    theme_state.validate_state(changed)
    with pytest.raises(ValueError, match="deterministic owner bundle assembly"):
        adapter.legacy_projection_for_owner(changed, bundle)


def test_same_input_shadow_rejects_numeric_zero_relabelled_boolean(world):
    bundle = capture(world)
    result = adapter.compose_from_owner_bundle(bundle, generated_at=EMITTED)
    changed = copy.deepcopy(result["legacy_baseline"])
    record = next(t["foresight"] for t in changed["themes"] if t["foresight"] is not None)
    assert record["score"] == 0 and type(record["score"]) is int
    record["score"] = False
    with pytest.raises(ValueError, match="same captured"):
        adapter.compare_shadow(changed, result["state"], result["legacy_candidate"], bundle)


def test_qualified_payload_cannot_change_native_number_to_equal_boolean(world):
    def change(result):
        receipt = result["source_receipts"]["narrative_emergence"]
        assert receipt["payload"]["narratives"][0]["legs"]["novelty"] == 1.0
        receipt["payload"]["narratives"][0]["legs"]["novelty"] = True
        receipt["sha256"] = theme_state.canonical_sha256(receipt["payload"])
    bundle = capture(world, owner_readers=QualifiedFixtureReader(world[0], change=change))
    with pytest.raises(ValueError, match="differs from captured bytes"):
        adapter.compose_from_owner_bundle(bundle, generated_at=EMITTED)


def test_malformed_actual_rights_registry_is_typed_unavailable(world):
    path = world[0] / "config/theme_sources.yml"
    path.write_text("families: [not-a-registry]\n")
    bundle = capture(world)
    native = bundle.snapshot()["subjects"][LOCAL]["native_reads"]["rights"]
    assert native["availability"] == "UNAVAILABLE"
    assert native["null_reason"] == "RIGHTS_REGISTRY_UNAVAILABLE"
    assert native["current_bytes_bound"] is False


@pytest.mark.parametrize("old_epoch,new_epoch,expected", [
    (True, 1, "UNAVAILABLE"), (False, 0, "UNAVAILABLE"), (True, True, "AVAILABLE"),
])
def test_exact_typed_current_rights_cache_version(world, old_epoch, new_epoch, expected):
    path = world[0] / "config/theme_sources.yml"
    family = rights.family_for_node_id(LOCAL)
    doc = yaml.safe_load(path.read_text())
    doc["families"][family]["controlled_cache_epoch"] = old_epoch
    path.write_text(yaml.safe_dump(doc))
    rights.load_registry(path=path)  # real owner cache, never patched or cleared
    doc["families"][family]["controlled_cache_epoch"] = new_epoch
    path.write_text(yaml.safe_dump(doc))
    bundle = capture(world, owner_readers=InternalRightsFixtureReader(world[0]))
    native = bundle.snapshot()["subjects"][LOCAL]["native_reads"]["rights"]
    assert native["availability"] == expected
    result = adapter.compose_from_owner_bundle(bundle, generated_at=EMITTED)
    local = next(s for s in result["state"]["subjects"] if s["node_id"] == LOCAL)
    if expected == "UNAVAILABLE":
        assert native["null_reason"] == "RIGHTS_CACHE_VERSION_UNAVAILABLE"
        assert native["current_bytes_bound"] is False
        assert local["owner_receipts"]["rights"] is None
    else:
        assert native["current_bytes_bound"] is True
        assert local["owner_receipts"]["rights"] is not None


def test_native_and_qualified_radar_roles_match_actual_incumbent_readers(world):
    flags = {"as_of": EFFECTIVE, "flags": [{"basket": "power_grid", "state": "watch",
              "lifecycle": "early", "divergence": 0, "salience": None}]}
    hypotheses = {"as_of": EFFECTIVE, "hypotheses": [{"subject": "power_grid", "lean": "neutral",
                   "horizon_d": 30, "check_by": "2026-11-03", "thesis": "native hypothesis"}]}
    write(world[0] / legacy._RADAR_ENRICHED_PATH, flags)
    write(world[0] / legacy._RADAR_PATH, hypotheses)
    assert legacy._read_radar_flags(world[0])[0]["power_grid"] == flags["flags"][0]
    assert legacy._read_radar_hypotheses(world[0])[0]["power_grid"] == hypotheses["hypotheses"][0]
    class Reader(QualifiedFixtureReader):
        def read_state_qualification(self, **kwargs):
            result = super().read_state_qualification(**kwargs)
            if result is None:
                return None
            for name, doc in (("radar", hypotheses), ("radar_enriched", flags)):
                receipt = copy.deepcopy(result["source_receipts"]["narrative_emergence"])
                receipt.update(owner="fixture-qualified." + name + ":" + kwargs["node_id"],
                               effective_at=EFFECTIVE, available_at="2026-10-03T08:00:00Z",
                               known_at="2026-10-03T09:00:00Z", recorded_at="2026-10-03T09:00:00Z",
                               payload=doc, sha256=theme_state.canonical_sha256(doc))
                result["source_receipts"][name] = receipt
            return result
    result = adapter.compose_from_owner_bundle(capture(world, owner_readers=Reader(world[0])), generated_at=EMITTED)
    native = result["native_observations"][LOCAL]
    assert native["radar_flag_measurements"]["fact"] == flags
    assert native["radar_hypothesis_measurements"]["fact"] == hypotheses
    assert native["radar_flag_measurements"]["source_sha256"] != native["radar_hypothesis_measurements"]["source_sha256"]
    dispositions = result["source_dispositions"][LOCAL]
    assert dispositions["radar"]["reason_code"] == "SUBJECT_SCOPED_RADAR_HYPOTHESES_ADAPTER_NOT_IMPLEMENTED"
    assert dispositions["radar_enriched"]["reason_code"] == "SUBJECT_SCOPED_RADAR_FLAGS_ADAPTER_NOT_IMPLEMENTED"
    assert all(dispositions[n]["status"] == "QUALIFIED_SOURCE_NOT_ADAPTED" for n in ("radar", "radar_enriched"))


@pytest.mark.parametrize("stamp", ["2026-09-28T23:00:00Z", "2026-09-28T23:00:00-04:00", "2026-09-28"])
def test_calendar_day_staleness_matches_incumbent_after_precise_future_guard(world, monkeypatch, stamp):
    cutoff = dt.datetime.fromisoformat(KNOWN.replace("Z", "+00:00"))
    class Clock(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return cutoff if tz else cutoff.replace(tzinfo=None)
    monkeypatch.setattr(legacy, "datetime", Clock)
    assert legacy._is_stale(stamp) is True
    doc = narrative()
    doc["as_of"] = stamp
    write(world[0] / legacy._NARRATIVE_PATH, doc)
    result = adapter.compose_from_owner_bundle(capture(world), generated_at=EMITTED)
    native = result["native_observations"][LOCAL]["narrative_measurements"]
    assert native["freshness"] == "STALE"
    assert native["native_clocks"]["effective_at"] == stamp
    assert native["freshness_policy"] == "incumbent-source-5-calendar-days"


@pytest.mark.parametrize("class_value", [None, "UNREVIEWED_UNKNOWN_CLASS", True])
def test_unreadable_current_rights_class_cannot_qualify_even_internal(world, class_value):
    path = world[0] / "config/theme_sources.yml"
    family = rights.family_for_node_id(LOCAL)
    doc = yaml.safe_load(path.read_text())
    if class_value is None:
        doc["families"][family].pop("rights_class")
    else:
        doc["families"][family]["rights_class"] = class_value
    path.write_text(yaml.safe_dump(doc))
    with pytest.raises(rights.RightsRefusal):
        rights.rights_class(family, path=path)  # actual classification refuses
    assert rights.licensing_for_family(family, path=path) == (True, False, False)
    bundle = capture(world, owner_readers=InternalRightsFixtureReader(world[0]))
    native = bundle.snapshot()["subjects"][LOCAL]["native_reads"]["rights"]
    assert native["availability"] == "UNAVAILABLE"
    assert native["null_reason"] == "RIGHTS_CLASS_UNAVAILABLE"
    assert native["licensing"] == [True, False, False]  # fallback retained, never a grant
    result = adapter.compose_from_owner_bundle(bundle, generated_at=EMITTED)
    local = next(s for s in result["state"]["subjects"] if s["node_id"] == LOCAL)
    assert local["owner_receipts"]["rights"] is None


# S1 exercises the new production interface through a fully synthetic owner
# estate. Original world/assertions remain unchanged; retained-byte redirection
# for those controls is explicitly an evidence-only harness.
from tests.test_theme_state_production import production_world


def test_production_bundle_is_immutable_after_specialist_sources_change(production_world):
    bundle = adapter.capture_owner_bundle(production_world, effective_at=EFFECTIVE,
                                          known_at="2026-10-04T12:00:00Z")
    before = adapter.compose_production_from_owner_bundle(bundle, generated_at=EMITTED)
    payload = json.loads((production_world / legacy._FORESIGHT_PATH).read_text())
    payload["themes"][0]["score"] = 99
    write(production_world / legacy._FORESIGHT_PATH, payload)
    after = adapter.compose_production_from_owner_bundle(bundle, generated_at=EMITTED)
    assert before == after
    changed = adapter.capture_owner_bundle(production_world, effective_at=EFFECTIVE,
                                           known_at="2026-10-04T12:00:00Z")
    fresh = adapter.compose_production_from_owner_bundle(changed, generated_at=EMITTED)
    assert fresh["state"]["state_sha256"] != before["state"]["state_sha256"]


def test_production_composition_reads_no_source_file_or_ambient_clock_after_capture(production_world, monkeypatch):
    from engine.theme_graph import theme_state_production
    bundle = adapter.capture_owner_bundle(production_world, effective_at=EFFECTIVE,
                                          known_at="2026-10-04T12:00:00Z")
    # Static contract validators initialize before the no-input-read assertion.
    theme_state._validator()
    def forbidden(*args, **kwargs):
        raise AssertionError("recapture or file read after immutable bundle")
    monkeypatch.setattr(adapter, "_source", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    result = adapter.compose_production_from_owner_bundle(bundle, generated_at=EMITTED)
    assert result["state"]["schema"] == "neuralweb.theme_state.v2"
    assert result["state"]["compatibility"]["projection"] == result["legacy_candidate"]


def test_production_input_mutation_cannot_supply_a_rehashed_wrong_bundle(production_world):
    bundle = adapter.capture_owner_bundle(production_world, effective_at=EFFECTIVE,
                                          known_at="2026-10-04T12:00:00Z")
    snapshot = bundle.snapshot()
    snapshot["subjects"][LOCAL]["native_id"] = "another_local"
    text = adapter._json(snapshot)
    changed = adapter.OwnerBundle(text, adapter._sha(text.encode()))
    with pytest.raises(ValueError):
        adapter.compose_production_from_owner_bundle(changed, generated_at=EMITTED)


def test_production_keeps_real_recommended_subset_positive_for_all_three_local_baskets(world):
    result = adapter.compose_production_from_owner_bundle(
        capture(world, owner_readers=QualifiedFixtureReader(world[0])), generated_at=EMITTED)
    subjects = {row["node_id"]: row for row in result["state"]["subjects"]}
    for node, ticker in [(LOCAL, "HUBB"), ("ltheme:finviz:housing", "IBP"), ("ltheme:finviz:travel", "ABNB")]:
        leg = subjects[node]["legs"]["narrative_emergence"]
        overlap = leg["overlap_observation"]
        assert overlap["value"]["matched_tickers"] == [ticker]
        assert leg["qualification"]["identity_membership"] == "OWNER_RECEIPT_BOUND"
        assert leg["qualification"]["rights"]["status"] == "UNAVAILABLE"
        assert subjects[node]["eligibility"] == "NOT_QUALIFIED"
    assert result["publication_allowed"] is False



def test_raw_crosswalk_scope_binding_applies_to_both_owner_assemblies(production_world):
    from engine.neuralweb import theme_state_adapter as actual
    bundle = actual.capture_owner_bundle(production_world, effective_at="2026-10-03",
                                        known_at="2026-10-04T12:00:00Z")
    snapshot = bundle.snapshot()
    snapshot["crosswalk"]["themes"][0]["foresight_id"] = "travel_owner"
    text = actual._json(snapshot)
    contradictory = actual.OwnerBundle(text, actual._sha(text.encode()))
    for compose in (actual.compose_from_owner_bundle, actual.compose_production_from_owner_bundle):
        with pytest.raises(ValueError, match="derived crosswalk"):
            compose(contradictory, generated_at="2026-10-04T12:00:00Z")



def test_controlled_capture_clock_changes_only_fixture_local_namespace(world):
    assert adapter.dt is not dt
    assert adapter.dt.datetime is not dt.datetime
    assert adapter.dt.date is dt.date
    assert adapter.dt.timezone is dt.timezone
    assert adapter.dt.datetime.now(dt.timezone.utc).isoformat() == "2026-10-04T11:00:00+00:00"
    assert dt.datetime.__module__ == "datetime"


def test_capture_clock_namespace_is_restored_after_fixture_teardown():
    assert adapter.dt is dt
    assert dt.datetime.__module__ == "datetime"



def test_owner_fixture_uses_exact_committed_controlled_inputs(world):
    assert (world[0] / "config/theme_sources.yml").read_bytes() == controlled_config_bytes("theme_sources.yml")
    assert yaml.safe_load((world[0] / "config/theme_crosswalk.yml").read_text()) == yaml.safe_load(controlled_config_bytes("theme_crosswalk.yml"))


@pytest.mark.parametrize("name", sorted(CONTROLLED_CONFIG_HASHES))
def test_controlled_configuration_has_no_live_fallback_or_unchecked_bytes(tmp_path, monkeypatch, name):
    # Change only this test module's fixture location, not a production owner or cache.
    monkeypatch.setitem(globals(), "CONTROLLED_CONFIG_ROOT", tmp_path)
    with pytest.raises(FileNotFoundError):
        controlled_config_bytes(name)
    (tmp_path / name).write_bytes(b"unqualified replacement")
    with pytest.raises(AssertionError):
        controlled_config_bytes(name)


def _live_capture_clock(monkeypatch, *instants):
    import types
    values = [dt.datetime.fromisoformat(x.replace('Z', '+00:00')) for x in instants]
    count = [0]
    class CaptureClock(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            value = values[min(count[0], len(values) - 1)]
            count[0] += 1
            return value.astimezone(tz) if tz else value.replace(tzinfo=None)
    namespace = {name: getattr(dt, name) for name in dir(dt) if not name.startswith('__')}
    namespace['datetime'] = CaptureClock
    monkeypatch.setattr(adapter, 'dt', types.SimpleNamespace(**namespace))


def test_live_query_is_bound_before_qualification_and_receives_only_frozen_reads(world, monkeypatch):
    _live_capture_clock(monkeypatch, '2026-10-04T12:00:00Z', '2026-10-04T12:00:03Z')
    seen = []
    class Reader:
        def read_state_qualification(self, **kwargs):
            seen.append(copy.deepcopy(kwargs))
            kwargs['native_reads'].clear()
            kwargs['query']['known_at'] = '2099-01-01T00:00:00Z'
            return None
    bundle = adapter.capture_owner_bundle(world[0], effective_at=EFFECTIVE,
                                          known_at=None, owner_readers=Reader())
    snapshot = bundle.snapshot()
    assert seen
    assert snapshot['query']['known_at'] == snapshot['observed_at']
    assert dt.datetime.fromisoformat(snapshot['observed_at'].replace('Z', '+00:00')).second == 3
    assert all(item['query'] == snapshot['query'] for item in seen)
    assert all(item['graph_capture_id'] == snapshot['graph_capture_id'] for item in seen)
    assert all(subject['native_reads'] for subject in snapshot['subjects'].values())


def test_explicit_historical_query_remains_earlier_than_actual_observation(world, monkeypatch):
    _live_capture_clock(monkeypatch, '2026-10-04T12:00:03Z')
    bundle = adapter.capture_owner_bundle(world[0], effective_at=EFFECTIVE, known_at=KNOWN)
    snapshot = bundle.snapshot()
    assert snapshot['query']['known_at'] == KNOWN
    state = adapter.compose_from_owner_bundle(bundle, generated_at='2026-10-04T12:00:04Z')['state']
    observed = theme_state.read_theme_state(state, LOCAL, effective_at=EFFECTIVE,
                                            known_at='2026-10-04T12:00:05Z')
    assert 'SOURCE_AFTER_CUTOFF' in observed['reason_codes']


def test_live_midnight_capture_does_not_return_mixed_date_bundle(world, monkeypatch):
    _live_capture_clock(monkeypatch, '2026-10-04T23:59:59Z', '2026-10-05T00:00:01Z')
    with pytest.raises(ValueError, match='day|midnight|date'):
        adapter.capture_owner_bundle(world[0], effective_at=EFFECTIVE, known_at=None)


def test_qualification_mutation_is_refused_after_native_capture(world, monkeypatch):
    _live_capture_clock(monkeypatch, '2026-10-04T12:00:00Z', '2026-10-04T12:00:03Z')
    class MutatingReader:
        def read_state_qualification(self, **kwargs):
            (world[0] / legacy._NARRATIVE_PATH).write_text('{"as_of":"2026-10-03","narratives":[]}')
            return None
    with pytest.raises(ValueError, match='changed'):
        adapter.capture_owner_bundle(world[0], effective_at=EFFECTIVE,
                                     known_at=None, owner_readers=MutatingReader())


def test_live_clock_regression_is_refused(world, monkeypatch):
    _live_capture_clock(monkeypatch, "2026-10-04T12:00:03Z", "2026-10-04T12:00:00Z")
    with pytest.raises(ValueError, match="backwards"):
        adapter.capture_owner_bundle(world[0], effective_at=EFFECTIVE, known_at=None)


@pytest.mark.parametrize("changed_input", ["rights", "producer"])
def test_qualification_cannot_change_capture_dependencies(world, monkeypatch, changed_input):
    _live_capture_clock(monkeypatch, "2026-10-04T12:00:00Z", "2026-10-04T12:00:03Z")
    original_refs = adapter._production_code_refs()

    class MutatingReader:
        def read_state_qualification(self, **kwargs):
            if changed_input == "rights":
                path = world[0] / "config/theme_sources.yml"
                path.write_bytes(path.read_bytes() + b"\n# capture race\n")
            else:
                monkeypatch.setattr(adapter, "_production_code_refs", lambda: {**original_refs, "changed": {}})
            return None

    with pytest.raises(ValueError, match="changed"):
        adapter.capture_owner_bundle(world[0], effective_at=EFFECTIVE,
                                     known_at=None, owner_readers=MutatingReader())
