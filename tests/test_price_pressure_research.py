"""Captured DRL context is present-day research, never event-time availability."""
from datetime import datetime, timezone
from hashlib import sha256
import json

import pytest

from engine.price_pressure import research


@pytest.fixture
def snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(research, "_utc_now", lambda: datetime(2026, 10, 19, 12, tzinfo=timezone.utc))
    row = {"ticker": "ACWI", "date": "2026-10-15", "side": "down", "era": "forward",
           "ret": 0.003, "peer_ret": 0.013, "resid": -0.010, "resid_z": -3.12,
           "peer_basis": "market", "edgar_covered": False, "family": "filing-coverage-unknown",
           "harvested_asof": "2026-10-16", "engine_version": "native-historical-version",
           "fwd21": 0.9, "retrace_frac": 1.2, "terminal_state": "RECOVERED"}
    body = {"schema": "price_pressure.v1", "display_only": True,
            "authority": dict(research._AUTHORITY), "generated_utc": "2026-10-16T18:17:51Z",
            "open_events": [row], "recently_resolved": []}
    path = tmp_path / research.SOURCE
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(body))
    return tmp_path, path, body


def read(root):
    return research.capture_event(root, event_date="2026-10-15", ticker="ACWI", side="down")


def test_exact_capture_keeps_native_values_and_clock_meanings(snapshot):
    root, path, body = snapshot
    before = path.read_bytes()
    result = read(root)
    assert result["source"]["snapshot_sha256"] == sha256(before).hexdigest()
    assert result["source"]["bytes"] == len(before)
    assert result["source"]["generated_utc"] == body["generated_utc"]
    assert result["capture"] == {
        "captured_at": "2026-10-19T12:00:00Z", "clock_class": "system_recorded",
        "historical_availability": "unknown", "scope": "retrospective_captured_read"}
    assert result["native_identity"] == {"date": "2026-10-15", "ticker": "ACWI", "side": "down"}
    assert result["native"]["harvested_asof"] == "2026-10-16"
    assert result["native"]["engine_version"] == "native-historical-version"
    assert result["native"]["ret"] > 0 and result["native"]["resid"] < 0
    assert result["native"]["peer_basis"] == "market"
    assert result["native"]["family"] == "filing-coverage-unknown"
    assert not any(result["authority"].values())
    assert path.read_bytes() == before


def test_capture_never_synthesizes_missing_native_provenance(snapshot):
    root, path, body = snapshot
    row = body["open_events"][0]
    del row["harvested_asof"], row["engine_version"]
    path.write_text(json.dumps(body))
    result = read(root)
    assert result["native"]["harvested_asof"] is None
    assert result["native"]["engine_version"] is None
    assert result["capture"]["historical_availability"] == "unknown"


def test_outcome_fields_do_not_enter_research_evidence(snapshot):
    root, path, body = snapshot
    first = read(root)
    row = body["open_events"][0]
    row.update(fwd21=-1, retrace_frac=0, terminal_state="DELISTED", state="FAILED")
    path.write_text(json.dumps(body))
    second = read(root)
    assert first["native"] == second["native"]
    assert first["source"]["snapshot_sha256"] != second["source"]["snapshot_sha256"]
    assert not {"fwd21", "retrace_frac", "terminal_state", "state"} & second["native"].keys()


@pytest.mark.parametrize("field,value,reason", [
    ("ret", True, "native_value_unavailable"),
    ("resid", None, "native_value_unavailable"),
    ("resid_z", "-3.12", "native_value_unavailable"),
    ("peer_basis", "unknown", "native_basis_invalid"),
    ("family", "no-filing", "filing_coverage_incoherent"),
    ("edgar_covered", 0, "filing_coverage_incoherent"),
    ("harvested_asof", "2026-10-14", "harvest_session_incoherent"),
    ("engine_version", "", "native_version_invalid"),
    ("era", "live", "native_era_invalid"),
    ("era", {}, "native_era_invalid"),
    ("family", [], "filing_coverage_incoherent"),
    ("peer_basis", {}, "native_basis_invalid"),
    ("ret", 10 ** 400, "native_value_unavailable"),
])
def test_invalid_native_input_is_refused(snapshot, field, value, reason):
    root, path, body = snapshot
    body["open_events"][0][field] = value
    path.write_text(json.dumps(body))
    with pytest.raises(research.CaptureUnavailable, match="^" + reason + "$"):
        read(root)


def test_same_event_in_ledger_mirror_lists_is_not_double_evidence(snapshot):
    root, path, body = snapshot
    body["recently_resolved"] = body["open_events"]
    path.write_text(json.dumps(body))
    with pytest.raises(research.CaptureUnavailable, match="^event_key_conflicted$"):
        read(root)


def test_missing_event_has_no_fallback(snapshot):
    root, _, _ = snapshot
    with pytest.raises(research.CaptureUnavailable, match="^event_not_found$"):
        research.capture_event(root, event_date="2026-10-15", ticker="AAPL", side="down")


def test_unhashable_request_side_is_a_typed_refusal(snapshot):
    root, _, _ = snapshot
    with pytest.raises(research.CaptureUnavailable, match="^invalid_event_key$"):
        research.capture_event(root, event_date="2026-10-15", ticker="ACWI", side=[])


@pytest.mark.parametrize("mutation,reason", [
    (lambda b: b.update(schema="other"), "snapshot_schema_invalid"),
    (lambda b: b["authority"].update(can_rank=True), "snapshot_authority_invalid"),
    (lambda b: b.update(display_only=1), "snapshot_authority_invalid"),
    (lambda b: b.update(generated_utc="2026-10-20T00:00:00Z"), "build_after_capture"),
    (lambda b: b.update(generated_utc="2026-10-16T18:17:51"), "invalid_build_clock"),
    (lambda b: b.update(open_events=b["open_events"] * 65), "event_population_invalid"),
])
def test_source_contract_refusals(snapshot, mutation, reason):
    root, path, body = snapshot
    mutation(body)
    path.write_text(json.dumps(body))
    with pytest.raises(research.CaptureUnavailable, match="^" + reason + "$"):
        read(root)


def test_duplicate_json_keys_are_not_silently_selected(snapshot):
    root, path, _ = snapshot
    path.write_text('{"schema":"price_pressure.v1","schema":"other"}')
    with pytest.raises(research.CaptureUnavailable, match="^duplicate_json_key$"):
        read(root)


def test_nonfinite_json_is_refused(snapshot):
    root, path, body = snapshot
    body["open_events"][0]["ret"] = float("inf")
    path.write_text(json.dumps(body))
    with pytest.raises(research.CaptureUnavailable, match="^nonfinite_json$"):
        read(root)


def test_oversized_snapshot_is_refused_before_reading(snapshot):
    root, path, _ = snapshot
    path.write_bytes(b" " * (research.MAX_BYTES + 1))
    with pytest.raises(research.CaptureUnavailable, match="^snapshot_bound_invalid$"):
        read(root)


def test_read_detects_in_place_change(snapshot, monkeypatch):
    root, path, _ = snapshot
    original = research.os.read
    changed = False

    def mutate(fd, size):
        nonlocal changed
        raw = original(fd, size)
        if not changed:
            changed = True
            path.write_bytes(path.read_bytes() + b" ")
        return raw

    monkeypatch.setattr(research.os, "read", mutate)
    with pytest.raises(research.CaptureUnavailable, match="^snapshot_changed_during_read$"):
        read(root)


def test_captured_evidence_uses_one_reference_and_native_event_subject_without_reread(snapshot, monkeypatch):
    from lib import evidence_foundation as ef, opportunity_evidence as oe
    root, _, _ = snapshot
    capture = read(root)
    monkeypatch.setattr(research, "_read", lambda *_: pytest.fail("composition reread the owner"))
    inputs = research.compose_captured_evidence(capture)
    assert set(inputs) == {"recipe", "blocks", "references", "vector"}
    assert len(inputs["references"]) == len(inputs["blocks"]) == 1
    ref_id, ref = next(iter(inputs["references"].items()))
    assert ef.validate_reference(ref) == ref
    assert ref["native_identity"] == capture["native_identity"]
    assert ref["native_schema"] == research.SCHEMA
    assert ref["native_digest"]["sha256"] == capture["source"]["snapshot_sha256"]
    assert ref["rights"] == {"state": "unknown", "policy_id": None}
    assert ref["freshness"]["state"] == "unknown"
    assert ref["subject"] == {"key_type": "drl_event_key", "key": '["2026-10-15","ACWI","down"]'}
    assert {c["class"] for c in ref["clocks"]} == {"world_valid", "belief_or_build", "system_recorded"}
    assert not any("harvest" in c["field"] for c in ref["clocks"])
    assert all(c["class"] not in {"observed", "knowable"} for c in ref["clocks"])
    block = inputs["blocks"][0]
    assert block["reference_ids"] == [ref_id] and block["coverage"]["included"] == 1
    assert block["coverage"]["state"] == "unknown"
    receipt = ef.compile_recipe(inputs["recipe"], blocks=inputs["blocks"], references=inputs["references"])
    assert receipt["denominator"]["total"] == 1
    assert inputs["recipe"]["identity_joins"] == []
    vector = inputs["vector"]
    assert oe.validate_vector(vector) == []
    assert vector["asof"]["value"] == capture["capture"]["captured_at"]
    assert vector["asof"]["t0_mode"] == "retrospective_research"
    assert vector["denominator"]["included"] == 2
    for slot in vector["slots"]:
        assert slot["captured_read"]["harvested_asof"] == capture["native"]["harvested_asof"]
        assert slot["captured_read"]["engine_version"] == capture["native"]["engine_version"]
    assert len({s["owner_ref"]["evidence_ref_id"] for s in vector["slots"]}) == 1
    assert vector["projection"]["inferred"]["slot_refs"] == ["drl_resid_shock", "drl_filing_coverage"]
    assert not vector["projection"]["observed"]["slot_refs"]
    assert not any(vector["authority"].values())
    assert research.compose_captured_evidence(capture) == inputs


@pytest.mark.parametrize("path,value", [
    (("schema",), "price_pressure.v1"),
    (("source", "artifact"), "data/private/body.json"),
    (("source", "snapshot_sha256"), "unknown"),
    (("source", "bytes"), True),
    (("capture", "historical_availability"), "known"),
    (("capture", "captured_at"), "2026-10-19"),
    (("capture", "clock_class"), "observed"),
    (("native", "peer_basis"), "guessed"),
    (("native", "resid_z"), True),
    (("native", "harvested_asof"), "2026-10-20"),
    (("native", "state"), "FAILED"),
    (("authority", "can_rank"), True),
    (("source", "generated_utc"), "2999-01-01T00:00:00Z"),
])
def test_capture_composition_rejects_unvalidated_contract(snapshot, path, value):
    capture = read(snapshot[0])
    target = capture
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(research.CaptureUnavailable, match="^capture_contract_invalid$"):
        research.compose_captured_evidence(capture)


def _rehash(vector):
    from lib.opportunity_evidence import compute_content_sha256
    vector["content_sha256"] = compute_content_sha256(vector)
    return vector


@pytest.mark.parametrize("mutation", [
    "event_date", "ticker", "side", "digest", "capture", "origin_tuple", "origin_digest", "origin_clock",
    "live", "non_drl_origin", "non_drl_slot", "canonical_subject", "known_at", "ref_id", "historical_availability",
])
def test_captured_vector_rejects_mismatched_native_bindings(snapshot, mutation):
    from lib import opportunity_evidence as oe
    vector = research.compose_captured_evidence(read(snapshot[0]))["vector"]
    slot = vector["slots"][1]
    # The two receipts are independently mutable on the wire.
    import copy
    vector = copy.deepcopy(vector)
    slot = vector["slots"][1]
    slot["captured_read"] = dict(slot["captured_read"])
    receipt = slot["captured_read"]
    if mutation in {"event_date", "ticker", "side", "digest", "capture"}:
        key, value = {"event_date": ("event_date", "2026-10-14"), "ticker": ("ticker", "OTHER"),
                      "side": ("side", "up"), "digest": ("snapshot_sha256", "0" * 64),
                      "capture": ("captured_at", "2026-10-19T11:59:59Z")}[mutation]
        receipt[key] = value
    elif mutation == "origin_tuple": vector["asof"]["t0_evidence_ref"]["native_identity"]["side"] = "up"
    elif mutation == "origin_digest": vector["asof"]["t0_evidence_ref"]["native_digest"]["sha256"] = "0" * 64
    elif mutation == "origin_clock": vector["asof"]["t0_evidence_ref"]["recorded_clock"]["value"] = "2026-10-19T11:59:59Z"
    elif mutation == "live": vector["asof"]["t0_mode"] = "live"
    elif mutation == "non_drl_origin": vector["asof"]["t0_source"] = "owner_pit_reference"
    elif mutation == "non_drl_slot": slot["construct"] = "attention_views"
    elif mutation == "canonical_subject": vector["subject"].update(subject_type="dataos_security_id", value="SEC:US-ARCX-ACWI")
    elif mutation == "known_at": slot["known_at"]["value"] = "2026-10-19T11:59:59Z"
    elif mutation == "ref_id": slot["owner_ref"] = {**slot["owner_ref"], "evidence_ref_id": "efr_" + "0" * 64}
    elif mutation == "historical_availability": receipt["historical_availability"] = "known"
    findings = oe.validate_vector(_rehash(vector))
    assert findings, mutation
    assert any(f.code in {"K3E_R022", "K3E_R021"} or f.code.startswith("K3E_SCHEMA") for f in findings), findings


@pytest.mark.parametrize("cutoff,grain", [("2026-10-19T11:59:59Z", "datetime"), ("2026-10-19", "date")])
def test_capture_cutoff_excludes_lookahead_and_ambiguous_same_day(snapshot, cutoff, grain):
    from lib import opportunity_evidence as oe
    vector = research.compose_captured_evidence(read(snapshot[0]))["vector"]
    asof = {**vector["asof"], "value": cutoff, "grain": grain}
    rebuilt = oe.compose_vector(vector["subject"], asof, vector["slots"], generated_at=vector["generated_at"])
    assert all(s["included_in_composition"] is False for s in rebuilt["slots"])
    assert all(s["exclusion_reason"] == "lookahead_known_at_after_asof" for s in rebuilt["slots"])
    assert "K3E_R022" in {f.code for f in oe.validate_vector(rebuilt)}
    for slot in rebuilt["slots"]:
        slot["included_in_composition"] = True
    assert "K3E_R007" in {f.code for f in oe.validate_vector(_rehash(rebuilt))}


def test_uncaptured_drl_session_cannot_supply_availability(snapshot):
    from lib import opportunity_evidence as oe
    vector = research.compose_captured_evidence(read(snapshot[0]))["vector"]
    slots = [{k: v for k, v in slot.items() if k != "captured_read"} for slot in vector["slots"]]
    # Use an independently supported non-DRL origin to isolate availability.
    asof = {**vector["asof"], "t0_source": "radar_observed_at", "t0_mode": "live",
            "t0_evidence_ref": {"owner_store": "data/entry_radar/", "native_identity": {"episode_id": "synthetic"},
                                "native_digest": {"state": "unknown", "sha256": None},
                                "recorded_clock": {"value": vector["asof"]["value"], "grain": "datetime", "clock_class": "belief_or_build", "native_field": "candidate_at", "state": "known"}}}
    for slot in slots:
        slot.pop("owner_ref")
        slot["known_at"] = {"value": "2026-10-16", "grain": "date", "native_field": "harvested_asof"}
    rebuilt = oe.compose_vector(vector["subject"], asof, slots)
    assert oe.validate_vector(rebuilt) == []
    for slot in rebuilt["slots"]:
        assert slot["state"] == "unknown" and slot["known_at"]["state"] == "unknown"
        assert slot["known_at"]["native_field"] is None and slot["value_or_null"] is None
        assert not slot["included_in_composition"]
    # Independently rehashed wire forgery must still be refused.
    rebuilt["slots"][0]["state"] = "observed"
    rebuilt["slots"][0]["included_in_composition"] = True
    assert "K3E_R022" in {f.code for f in oe.validate_vector(_rehash(rebuilt))}


def test_native_event_key_parity_and_capture_version_remain_separate(snapshot):
    from lib import evidence_foundation as ef
    first = research.compose_captured_evidence(read(snapshot[0]))
    root, path, body = snapshot
    body["open_events"][0]["terminal_state"] = "FAILED"
    path.write_text(json.dumps(body))
    second = research.compose_captured_evidence(read(root))
    r1, r2 = (next(iter(x["references"].values())) for x in (first, second))
    assert r1["native_identity"] == r2["native_identity"] and r1["subject"] == r2["subject"]
    assert r1["reference_id"] != r2["reference_id"]
    assert first["vector"]["slots"][0]["value_or_null"] == second["vector"]["slots"][0]["value_or_null"]
    r2["subject"]["key"] = '["2026-10-15","ACWI","up"]'
    r2["reference_id"] = ef.compute_reference_id(r2)
    with pytest.raises(ef.EvidenceFoundationError, match="subject_native_identity_mismatch"):
        ef.validate_reference(r2)


@pytest.mark.parametrize("mutation", ["live", "replay", "digest", "rights", "freshness", "unknown_capture", "future_build", "event_clock", "missing_slot", "duplicate_slot"])
def test_capture_owner_contract_does_not_grant_source_purpose_or_fabricate_clocks(snapshot, mutation):
    from lib import evidence_foundation as ef, opportunity_evidence as oe
    inputs = research.compose_captured_evidence(read(snapshot[0]))
    if mutation in {"missing_slot", "duplicate_slot"}:
        vector = inputs["vector"]
        if mutation == "missing_slot": vector["slots"].pop()
        else: vector["slots"].append(vector["slots"][0])
        assert "K3E_R022" in {f.code for f in oe.validate_vector(_rehash(vector))}
        return
    ref = next(iter(inputs["references"].values()))
    if mutation == "live": ref["replay"].update(mode="live", vintage_state="unavailable")
    elif mutation == "replay": ref["replay"]["mode"] = "historical_replay"
    elif mutation == "digest": ref["replay"]["input_digest"] = "0" * 64
    elif mutation == "rights": ref["rights"] = {"state": "permitted", "policy_id": "invented"}
    elif mutation == "freshness": ref["freshness"] = {"state": "native_clock_bound", "clock_field": "capture.captured_at", "policy_id": "invented"}
    elif mutation == "unknown_capture": ref["clocks"][2].update(value_state="unknown", value=None)
    elif mutation == "future_build": ref["clocks"][1]["value"] = "2026-10-19T12:00:01Z"
    elif mutation == "event_clock": ref["clocks"][0]["value"] = "2026-10-14"
    ref["reference_id"] = ef.compute_reference_id(ref)
    with pytest.raises(ef.EvidenceFoundationError, match="drl_capture"):
        ef.validate_reference(ref)


@pytest.mark.parametrize("mode", ["live", "retrospective_research"])
def test_native_harvest_session_is_a_retired_decision_origin(snapshot, mode):
    from lib import opportunity_evidence as oe
    vector = research.compose_captured_evidence(read(snapshot[0]))["vector"]
    vector["asof"]["t0_source"] = "drl_event_date"
    vector["asof"]["t0_mode"] = mode
    assert "K3E_R021" in {f.code for f in oe.validate_vector(_rehash(vector))}


def test_native_harvest_metadata_cannot_become_future_availability(snapshot):
    from lib import opportunity_evidence as oe
    vector = research.compose_captured_evidence(read(snapshot[0]))["vector"]
    for slot in vector["slots"]:
        slot["captured_read"]["harvested_asof"] = "2026-10-20"
    assert "K3E_R022" in {f.code for f in oe.validate_vector(_rehash(vector))}


def test_captured_case_binds_event_but_never_unrelated_context(snapshot):
    from lib.opportunity_case import compose_case, validate_case
    root, _, _ = snapshot
    case = compose_case(**research.compose_captured_evidence(read(root)))
    assert validate_case(case) == case
    assert case["evidence_binding"]["state"] == "exact_owner_native_event"
    assert case["research_state"] == "partial"
    assert case["permitted_consumers"] == ["research_session"]
    assert case["denominators"]["evidence"]["included"] == 1
    assert len(case["inputs"]["vector"]["slots"]) == 2
    for leg in ("transmission", "company_context", "valuation_context", "path_timing", "portfolio_intersection"):
        assert case[leg]["state"] == "unavailable" and case[leg]["block_ids"] == []
    assert not any(case["authority"].values())


@pytest.mark.parametrize("leg", ["company_context", "transmission"])
def test_captured_case_refuses_rehashed_recipe_context_promotion(snapshot, leg):
    from lib import evidence_foundation as ef
    from lib.opportunity_case import compose_case, OpportunityCaseError
    root, _, _ = snapshot
    inputs = research.compose_captured_evidence(read(root))
    inputs["recipe"]["block_specs"][0]["output_fields"] = [leg]
    inputs["recipe"]["output_mappings"][0]["output_field"] = leg
    inputs["recipe"]["recipe_id"] = ef.compute_recipe_id(inputs["recipe"])
    with pytest.raises(OpportunityCaseError, match="case_native_event_binding_invalid"):
        compose_case(**inputs)


def test_captured_case_event_key_survives_new_capture_and_snapshot(snapshot, monkeypatch):
    from lib.opportunity_case import compose_case
    root, path, body = snapshot
    first = compose_case(**research.compose_captured_evidence(read(root)))
    body["open_events"][0]["engine_version"] = "next-native-version"
    path.write_text(json.dumps(body))
    monkeypatch.setattr(research, "_utc_now", lambda: datetime(2026, 10, 19, 13, tzinfo=timezone.utc))
    second = compose_case(**research.compose_captured_evidence(read(root)))
    assert first["case_id"] == second["case_id"]
    assert first["content_sha256"] != second["content_sha256"]
    body["open_events"][0]["ticker"] = "OTHER"
    path.write_text(json.dumps(body))
    other = research.capture_event(root, event_date="2026-10-15", ticker="OTHER", side="down")
    third = compose_case(**research.compose_captured_evidence(other))
    assert third["case_id"] != first["case_id"]
