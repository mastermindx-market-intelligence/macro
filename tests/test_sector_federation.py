"""Controlled Task2 source proof; no natural publication/rights/market claim."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess

import pytest

from engine.neuralweb.sector_federation import FederationError, FederationInputs, UnsupportedSector, compose_sector_dossier
from engine.sector_intelligence.contracts import canonical_json_bytes, canonical_json_sha256, validate_contract

FIXTURE = Path(__file__).parent / "fixtures/sector_federation/technology_split_view.v2.json"
ORDER = ("sector_slow_clock", "sector_fast_tape", "sector_participation", "sector_concentration", "subsector_entry", "closed_session_leadership", "theme_health", "group_entry_context")


def raw():
    return json.loads(FIXTURE.read_text())


def refresh(value):
    """Rebind known synthetic source bytes after controlled mutations."""
    source_keys = {"site-baskets": "baskets", "site-action-board": "action_board", "site-sector-central": "sector_central", "site-subsector-confluence": "subsector_confluence", "site-subsector-rotation": "subsector_rotation", "site-theme-state": "theme_state", "theme-crosswalk": "theme_crosswalk", "sp500-heatmap": "heatmap", "site-theme-lanes": "optional_entry_context"}
    basket_hash = canonical_json_sha256(value["baskets"])
    value["action_board"]["baskets_sha256"] = basket_hash
    for row in value["input_receipts"]:
        payload = value[source_keys[row["source_id"]]]
        if payload is not None:
            row["sha256"] = canonical_json_sha256(payload)
    return value


def compose(value=None, **overrides):
    kwargs = dict(inputs=FederationInputs.from_mapping(raw() if value is None else value), sector_id="xlk", common_as_of="2026-09-18", generated_at="2026-09-18T20:00:00Z", code_version="controlled-task2")
    kwargs.update(overrides)
    return compose_sector_dossier(**kwargs)


def dim(doc, name):
    return next(row for row in doc["dimensions"] if row["dimension_id"] == name)


def test_native_owner_shape_positive_validates_all_four_contracts():
    value = raw()
    doc = compose(value)
    validate_contract(doc)
    for nested in doc["governance"].values():
        validate_contract(nested)
    assert doc["identity"]["subject"] == {"kind": "sector", "node_id": "sector:xlk", "native_id": "xlk", "source_family": None}
    assert doc["identity"]["tradable_binding"]["value"] == "XLK"
    assert doc["identity"]["benchmark_binding"]["value"] is None
    assert tuple(row["dimension_id"] for row in doc["dimensions"]) == ORDER
    assert dim(doc, "sector_slow_clock")["value"]["conviction_score"] == 40
    assert dim(doc, "sector_fast_tape")["value"]["rotation_state"] == "MONEY ROTATING IN"
    assert doc["participation"]["n_advancing"] == 20
    assert doc["participation"]["n_declining"] == 29
    assert doc["participation"]["value_pct"] == 41.0
    assert doc["concentration"]["value"] == pytest.approx(0.9)
    assert doc["concentration"]["n_members"] == 9
    assert doc["children"][0]["child_id"] == "subsector:semiconductors"
    assert doc["children"][0]["entry_tier"] == "T1"
    assert doc["connected_themes"][0]["theme_id"] == "ai_semiconductors"
    assert doc["children"][0]["relationship_basis"] == "structural_child"
    assert doc["connected_themes"][0]["relationship_basis"] == "theme_crosswalk.subsector_keys"
    assert doc["material_changes"] == []
    assert doc["headline"]["state"] == "selective_leadership"
    assert {"TIMEFRAME_SPLIT", "SCOPE_SPLIT"}.issubset({r["class"] for r in doc["conflicts"]})


def test_deterministic_canonical_hash_and_input_immutability():
    value = raw()
    before = copy.deepcopy(value)
    first = compose(value)
    assert value == before
    assert canonical_json_bytes(first) == canonical_json_bytes(compose(value))
    reordered = copy.deepcopy(value)
    reordered["input_receipts"].reverse()
    reordered["heatmap"]["tiles"].reverse()
    assert canonical_json_bytes(first) == canonical_json_bytes(compose(reordered))
    assert canonical_json_sha256({k:v for k,v in first.items() if k != "dossier_hash"}) == first["dossier_hash"]


def test_all_receipts_subjects_and_nested_output_bind_exactly():
    doc = compose()
    packet, run, manifest = (doc["governance"][k] for k in ("packet", "lobe_run", "authority_manifest"))
    assert all(p["subject"] == doc["identity"]["subject"] for p in (packet, run, manifest))
    assert [w["input_receipt"] for w in run["source_watermarks"]] == doc["input_receipts"]
    assert run["input_hashes"] == sorted({r["sha256"] for r in doc["input_receipts"] if r["sha256"] is not None})
    assert run["output_artifacts"] == [{"artifact_ref": packet["packet_id"], "content_sha256": packet["packet_hash"], "row_count": 1}]
    assert run["started_at"] == run["finished_at"] == doc["generated_at"]
    assert packet["lobe_run_ref"] == run["run_id"]
    assert manifest["artifact_ref"] == packet["packet_id"]
    assert all(not v for k,v in doc["authority_caps"].items() if k != "is_context_only")
    assert packet["authority_caps"]["allowed_actions"] == ["observe", "explain"]
    assert "originate_signal" in packet["authority_caps"]["forbidden_actions"]


def test_optional_absence_static_null_and_pit_are_honest():
    doc = compose()
    assert dim(doc, "closed_session_leadership")["value"] is None
    assert dim(doc, "group_entry_context")["value"] is None
    assert doc["quality"]["optional_dimensions_available"] == 0
    assert doc["quality"]["point_in_time_safe"] is False
    static = next(r for r in doc["input_receipts"] if r["source_id"] == "theme-crosswalk")
    assert static["as_of"] is static["observed_at"] is None
    assert doc["freshness"]["oldest_required_source_at"] == "2026-09-18T19:55:00Z"


def test_valid_empty_children_and_themes_are_not_missing_sources():
    value = raw()
    value["subsector_confluence"]["subsectors"] = []
    value["theme_state"]["themes"] = []
    doc = compose(refresh(value))
    assert doc["children"] == doc["connected_themes"] == []
    assert dim(doc, "subsector_entry")["state"] == "valid_empty"
    assert dim(doc, "theme_health")["state"] == "valid_empty"
    assert doc["quality"]["required_completeness"] == 1.0


def test_heatmap_absence_is_null_not_zero_and_other_sector_is_excluded():
    value = raw()
    value["heatmap"]["tiles"] = [{"t": "ENERGY_CONTROL", "sector": "Energy", "size": 1000000}]
    doc = compose(refresh(value))
    assert doc["concentration"]["value"] is None
    assert doc["concentration"]["state"] == "unavailable"


def test_native_counts_unavailable_remain_null():
    value = raw()
    value["sector_central"]["sectors"][0]["heat"] = {"adv": None, "dec": None, "breadth_pct": None}
    doc = compose(refresh(value))
    assert doc["participation"]["n_advancing"] is None
    assert doc["participation"]["n_total"] is None
    assert doc["participation"]["value_pct"] is None


@pytest.mark.parametrize("mutation", ["duplicate", "unknown", "path", "missing", "hash", "clock", "null_reason"])
def test_intrinsic_receipt_failures_refuse(mutation):
    value = raw()
    row = value["input_receipts"][0]
    if mutation == "duplicate": value["input_receipts"].append(copy.deepcopy(row))
    if mutation == "unknown": row["source_id"] = "foreign"
    if mutation == "path": row["path"] = "site/foreign.json"  # ci-trigger-closure: data — supplied reference identity or output data; never opened here
    if mutation == "missing": value["input_receipts"] = [r for r in value["input_receipts"] if r["source_id"] != "site-theme-state"]
    if mutation == "hash": row["sha256"] = "bad"
    if mutation == "clock": row["observed_at"] = "2026-09-18T19:55:00"
    if mutation == "null_reason": next(r for r in value["input_receipts"] if r["source_id"] == "theme-crosswalk")["null_reasons"] = {}
    with pytest.raises(FederationError):
        compose(value)


@pytest.mark.parametrize("state,expected", [("fresh", "degraded"), ("stale", "stale"), ("unknown", "unknown")])
def test_older_auxiliary_keeps_native_freshness(state, expected):
    value = raw()
    value["subsector_confluence"]["as_of"] = "2026-09-17"
    value["subsector_confluence"]["subsectors"][0]["as_of"] = "2026-09-17"
    row = next(r for r in value["input_receipts"] if r["source_id"] == "site-subsector-confluence")
    row.update(as_of="2026-09-17", observed_at="2026-09-17T19:55:00Z", freshness_state=state)
    doc = compose(refresh(value))
    assert doc["freshness"]["state"] == expected
    assert row["freshness_state"] == state
    assert any(r["class"] == "FRESHNESS_SPLIT" for r in doc["conflicts"])


@pytest.mark.parametrize("kind", ["date", "clock", "coordinated_date"])
def test_future_facts_refuse_after_controlled_source_rebinding(kind):
    value = raw()
    if kind == "date":
        value["theme_state"]["as_of"] = "2030-01-02"
        next(r for r in value["input_receipts"] if r["source_id"] == "site-theme-state")["as_of"] = "2030-01-02"
    if kind == "clock":
        next(r for r in value["input_receipts"] if r["source_id"] == "site-theme-state")["observed_at"] = "2030-01-02T20:00:00Z"
    overrides = {}
    if kind == "coordinated_date":
        for key in ("baskets", "action_board", "sector_central", "subsector_confluence", "theme_state"): value[key]["as_of"] = "2030-01-02"
        for key in ("subsector_rotation", "heatmap"): value[key]["asof"] = "2030-01-02"
        for row in value["input_receipts"]:
            if row["freshness_role"] == "market_observation": row["as_of"] = "2030-01-02"
        value["subsector_confluence"]["subsectors"][0]["as_of"] = "2030-01-02"
        overrides["common_as_of"] = "2030-01-02"
    with pytest.raises(FederationError):
        compose(refresh(value), **overrides)


@pytest.mark.parametrize("mutation", ["unstamped", "basket_binding", "selection_clock", "wrong_xlk", "label_alias"])
def test_owner_shape_or_selection_substitution_refuses(mutation):
    value = raw()
    if mutation == "unstamped": value["action_board"] = {"action_board": value["action_board"]["action_board"]}
    if mutation == "basket_binding": value["action_board"]["baskets_sha256"] = "f" * 64
    if mutation == "selection_clock": value["action_board"]["generated_utc"] = "2026-09-18T20:00:00"
    if mutation == "wrong_xlk": value["sector_central"]["sectors"][0]["ticker"] = "XLF"
    if mutation == "label_alias": value["sector_central"]["sectors"][0]["id"] = "Technology"
    with pytest.raises(FederationError):
        compose(value)


@pytest.mark.parametrize("sector", ["xlf", "XLK", "technology", "theme:ai_semiconductors"])
def test_sector_admission_is_exact(sector):
    with pytest.raises(UnsupportedSector):
        compose(sector_id=sector)


@pytest.mark.parametrize("which", ["heat", "heatmap"])
def test_nonfinite_native_measurement_refuses(which):
    value = raw()
    if which == "heat": value["sector_central"]["sectors"][0]["heat"]["breadth_pct"] = float("nan")
    else: value["heatmap"]["tiles"][0]["size"] = float("inf")
    with pytest.raises(FederationError):
        compose(value)


def test_exact_crosswalk_relation_only_no_label_guess():
    value = raw()
    value["theme_crosswalk"]["themes"][0]["subsector_keys"] = ["Almost Semiconductors"]
    assert compose(refresh(value))["connected_themes"] == []


@pytest.mark.parametrize("change", ["fresh", "scope", "horizon", "stale", "unadmitted"])
def test_same_horizon_requires_qualified_ref_scope_horizon_and_date(change):
    value = raw()
    read = {"scope": "sector", "horizon": "multi_year_cycle", "state": "constructive", "as_of": "2026-09-18", "source_ref": "site/sectordata/sector_central.json#/qualified_same_horizon"}  # ci-trigger-closure: data — supplied reference identity or output data; never opened here
    if change == "scope": read["scope"] = "subsector"
    if change == "horizon": read["horizon"] = "short_term"
    if change == "stale": read["as_of"] = "2026-09-17"
    if change == "unadmitted": read["source_ref"] = "fixture#/same_horizon_owner_read"
    value["same_horizon_owner_read"] = read
    if change == "unadmitted":
        with pytest.raises(FederationError): compose(value)
    else:
        classes = {r["class"] for r in compose(value)["conflicts"]}
        assert ("GENUINE_CONTRADICTION" in classes) is (change == "fresh")


def test_unknown_headline_combination_is_neutral_copy():
    value = raw()
    value["sector_central"]["sectors"][0]["conviction"]["label_en"] = "Unknown"
    doc = compose(refresh(value))
    assert doc["headline"]["state"] == "mixed_or_incomplete"


def test_no_domain_file_acquisition_or_output_in_composer(monkeypatch):
    value = raw()
    text, binary = Path.read_text, Path.read_bytes
    root = Path(__file__).resolve().parents[1]
    # The incumbent registry discovers committed schema source across contracts/.
    committed = set(subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", "HEAD", "--", "contracts"], text=True).splitlines())
    assert subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "contracts"]).returncode == 0
    seen = []
    def guard(method):
        def read(path, *args, **kwargs):
            seen.append(str(path))
            relative = path.resolve().relative_to(root).as_posix()
            assert relative in committed and path.name.endswith(".schema.json"), (
                f"domain/input acquisition forbidden: {path}")
            return method(path, *args, **kwargs)
        return read
    monkeypatch.setattr(Path, "read_text", guard(text))
    monkeypatch.setattr(Path, "read_bytes", guard(binary))
    def no_write(*args, **kwargs): raise AssertionError("output effects forbidden")
    monkeypatch.setattr(Path, "write_text", no_write)
    monkeypatch.setattr(Path, "write_bytes", no_write)
    doc = compose(value)
    assert doc["identity"]["subject"]["node_id"] == "sector:xlk"
    assert seen  # Only parent's allowed incumbent schema-source dependency.


def test_v1_golden_stays_accepted():
    old = json.loads(subprocess.check_output(["git","show","HEAD:data/sector_intelligence/fixtures/sector_dossier_read_model.v1.valid.json"],text=True))
    validate_contract(old)

@pytest.mark.parametrize("field", ["optional_leadership", "same_horizon_owner_read"])
def test_future_qualified_owner_read_refuses(field):
    value = raw()
    value[field] = {"scope": "subsector" if field == "optional_leadership" else "sector",
                    "horizon": "closed_session" if field == "optional_leadership" else "multi_year_cycle",
                    "state": "constructive", "as_of": "2030-01-02",
                    "source_ref": "site/marketdata/subsector_rotation.json#/qualified_read"}  # ci-trigger-closure: data — supplied reference identity or output data; never opened here
    with pytest.raises(FederationError):
        compose(value)


@pytest.mark.parametrize("mutation", ["child_kind", "child_date", "theme_native_id", "crosswalk_native_id", "theme_entry_missing"])
def test_native_child_and_theme_grain_cannot_be_substituted(mutation):
    value = raw()
    if mutation == "child_kind": value["subsector_confluence"]["subsectors"][0]["kind"] = "theme"
    if mutation == "child_date": value["subsector_confluence"]["subsectors"][0]["as_of"] = "2030-01-02"
    if mutation == "theme_native_id": value["theme_state"]["themes"][0]["id"] = value["theme_state"]["themes"][0].pop("theme_id")
    if mutation == "crosswalk_native_id": value["theme_crosswalk"]["themes"][0]["theme_id"] = value["theme_crosswalk"]["themes"][0].pop("id")
    if mutation == "theme_entry_missing": del value["theme_state"]["themes"][0]["foresight"]["entry_ready"]
    with pytest.raises(FederationError):
        compose(refresh(value))


def test_partial_heatmap_sizes_cannot_become_a_complete_population_measure():
    value = raw()
    value["heatmap"]["tiles"][0]["size"] = None
    doc = compose(refresh(value))
    assert doc["concentration"]["value"] is None
    assert dim(doc, "sector_concentration")["coverage_state"] == "unavailable"
    assert dim(doc, "sector_concentration")["value"]["n_missing_sizes"] == 1


def test_optional_leadership_preserves_exact_subsector_scope_and_source_date():
    value = raw()
    value["optional_leadership"] = {"scope": "sector", "horizon": "closed_session",
                                   "state": "constructive", "as_of": "2026-09-18",
                                   "source_ref": "site/marketdata/subsector_rotation.json#/qualified_read"}  # ci-trigger-closure: data — supplied reference identity or output data; never opened here
    with pytest.raises(FederationError): compose(value)


def test_headline_copy_requires_the_frozen_constructive_fast_state():
    value = raw()
    value["sector_central"]["sectors"][0]["rotation"]["state"] = "MONEY ROTATING OUT"
    assert compose(refresh(value))["headline"]["state"] == "mixed_or_incomplete"

def test_available_optional_owner_context_is_preserved_without_new_action():
    value = raw()
    value["optional_entry_context"] = {"as_of": "2026-09-18", "theme_context": {
        "ai_semiconductors": {"dimensions": {"entry": {"state": "READY"}}}}}
    receipt = next(r for r in value["input_receipts"] if r["source_id"] == "site-theme-lanes")
    receipt.update(state="available", as_of="2026-09-18", observed_at="2026-09-18T19:55:00Z",
                   freshness_state="fresh", null_reasons={})
    value["optional_leadership"] = {"scope": "subsector", "horizon": "closed_session",
                                  "state": "leading", "as_of": "2026-09-18",
                                  "source_ref": "site/marketdata/subsector_rotation.json#/qualified_read"}  # ci-trigger-closure: data — injected reference, never opened
    doc = compose(refresh(value))
    assert doc["quality"]["optional_dimensions_available"] == 2
    assert dim(doc, "closed_session_leadership")["value"]["owner_state"] == "leading"
    assert dim(doc, "group_entry_context")["value"]["owner_states"] == "READY"
    assert doc["authority_caps"]["may_trade"] is False


def test_unavailable_optional_known_hash_is_retained_without_domain_facts():
    value = raw()
    receipt = next(r for r in value["input_receipts"] if r["source_id"] == "site-theme-lanes")
    receipt.update(sha256="c"*64, as_of="2026-09-17",
                   null_reasons={"observed_at": "OWNER_CLOCK_UNAVAILABLE"})
    doc = compose(value)
    assert "c"*64 in doc["governance"]["lobe_run"]["input_hashes"]
    assert dim(doc, "group_entry_context")["value"] is None


@pytest.mark.parametrize("field,value", [("adv", -1), ("dec", True), ("breadth_pct", 101), ("breadth_pct", "41%")])
def test_measurement_count_and_percent_units_are_not_coerced(field, value):
    inputs = raw()
    inputs["sector_central"]["sectors"][0]["heat"][field] = value
    with pytest.raises(FederationError): compose(refresh(inputs))


@pytest.mark.parametrize("source", ["subsector_confluence", "theme_state", "theme_crosswalk"])
def test_duplicate_owner_child_theme_identity_refuses(source):
    value = raw()
    key = "subsectors" if source == "subsector_confluence" else "themes"
    value[source][key].append(copy.deepcopy(value[source][key][0]))
    with pytest.raises(FederationError): compose(refresh(value))


@pytest.mark.parametrize("generated", ["2026-09-19T10:00:00+14:00", "2026-09-18T08:00:00-12:00"])
def test_aware_clock_aliases_keep_utc_selection_date(generated):
    doc = compose(generated_at=generated)
    assert doc["common_as_of"] == "2026-09-18"
    validate_contract(doc)


def test_connected_configuration_without_owner_health_is_unavailable():
    value = raw()
    value["theme_state"]["themes"] = []
    doc = compose(refresh(value))
    assert doc["connected_themes"] == []
    assert dim(doc, "theme_health")["state"] == "unavailable"
    assert dim(doc, "theme_health")["value"] is None


def test_zero_sizes_are_counted_but_do_not_create_a_denominator():
    value = raw()
    for row in value["heatmap"]["tiles"]:
        if row["sector"] == "Technology": row["size"] = 0
    doc = compose(refresh(value))
    assert doc["concentration"]["value"] is None
    assert doc["concentration"]["n_members"] == 9

def test_concentration_is_stable_for_finite_float_population_permutations():
    value = raw()
    for row, size in zip(value["heatmap"]["tiles"][:9], [1e16, 1., 1., 1., 1., 1., 1., 1., 1.]):
        row["size"] = size
    value = refresh(value)
    first = compose(value)
    value["heatmap"]["tiles"].reverse()
    assert canonical_json_bytes(first) == canonical_json_bytes(compose(value))

@pytest.mark.parametrize("field", ["heat", "conviction", "cycle", "rotation", "child_entry", "child_regime"])
def test_malformed_nested_native_objects_refuse_as_federation_error(field):
    value = raw()
    if field.startswith("child_"):
        value["subsector_confluence"]["subsectors"][0][field.removeprefix("child_")] = ["malformed"]
    else:
        value["sector_central"]["sectors"][0][field] = ["malformed"]
    with pytest.raises(FederationError):
        compose(refresh(value))


@pytest.mark.parametrize("mutation", [
    "duplicate_member", "nonobject", "missing_identity", "empty_identity",
    "numeric_identity", "missing_sector", "empty_sector", "numeric_sector",
    "energy_negative_size",
])
def test_heatmap_native_population_rejects_duplicate_or_malformed_rows(mutation):
    value = raw()
    tiles = value["heatmap"]["tiles"]
    if mutation == "duplicate_member": tiles.append(copy.deepcopy(tiles[8]))
    if mutation == "nonobject": tiles.append(["malformed"])
    if mutation == "missing_identity": tiles[8].pop("t")
    if mutation == "empty_identity": tiles[8]["t"] = ""
    if mutation == "numeric_identity": tiles[8]["t"] = 8
    if mutation == "missing_sector": tiles[8].pop("sector")
    if mutation == "empty_sector": tiles[8]["sector"] = ""
    if mutation == "numeric_sector": tiles[8]["sector"] = 8
    if mutation == "energy_negative_size": next(t for t in tiles if t["sector"] == "Energy")["size"] = -1
    with pytest.raises(FederationError):
        compose(refresh(value))


def test_valid_other_sector_keeps_native_identity_and_is_excluded_exactly():
    value = raw()
    value["heatmap"]["tiles"].append({"t": "OTHER_OWNER_MEMBER", "sector": "Owner Other Sector", "size": 1000000})
    doc = compose(refresh(value))
    assert doc["concentration"]["n_members"] == 9
    assert doc["concentration"]["value"] == pytest.approx(0.9)
