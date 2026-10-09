"""Rotation/risk integration: source fidelity, overlap, clocks and no new authority."""
from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone
from itertools import permutations

import pytest

from engine.risk_envelope import SourceRead, EnvelopeContractError, compose_envelope
from scripts import build_risk_envelope as settled
from scripts import build_live_risk_envelope as live

SESSION = "2026-10-06"
NOW = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)


def lineage(roots, *, groups=(), parents=(), status="COMPLETE"):
    return {"definition_id": "fixture-v1", "status": status, "roots": list(roots),
            "dependency_groups": list(groups), "derived_from": list(parents)}


def rotation(*, day=SESSION, state="DEFENSIVE_RELATIVE_STRENGTH", roots=("price:xlp:oct6",), groups=("equity_price",)):
    return {"schema": "rotation_events.v1", "asof": day, "active": [],
            "early_context": {"schema": "rotation_early_context/v1", "definition_id": "fixture-v1",
                              "as_of": day, "state": state, "display_only": True,
                              "pairs": [], "coverage": {"registered_pairs": 0},
                              "lineage": lineage(roots, groups=groups)}}


def source(sid, *, role="context", roots=(), groups=(), parents=(), status="COMPLETE"):
    return SourceRead(source_id=sid, role=role, as_of=SESSION,
                      state="MIXED" if role == "measured_state" else "BROKEN",
                      score=51 if role == "measured_state" else None,
                      hazard_stage="FRAGILE" if role == "hazard_evidence" else None,
                      required=role != "context",
                      detail={"lineage": lineage(roots, groups=groups, parents=parents, status=status)})


def reads():
    return [source("market-state-latest", role="measured_state", roots=("price:spy:oct6",), groups=("equity_price",)),
            source("leadership-crack-latest", role="hazard_evidence", roots=("price:semis:oct6",), groups=("equity_price",)),
            settled._rotation_read(rotation(), SESSION, now=NOW)]


def compose(sources):
    return compose_envelope(sources=sources, market="US", source_session=SESSION,
                            observed_at="2026-10-07T12:00:00Z", produced_at="2026-10-07T12:00:00Z")


def test_context_is_additive_and_does_not_change_stage_or_policy():
    sources = reads()
    previous = compose(sources[:2])
    current = compose(sources)
    for key in ("measured_state", "hazard_summary", "policies", "episodes", "policy_summary", "authority"):
        assert current[key] == previous[key]
    assert current["hazard_summary"]["stage"] == "FRAGILE"
    assert current["confluence"]["nonredundant_component_count"] == 1
    assert current["confluence"]["statistical_independence_established"] is False
    assert current["confluence"]["changes_hazard_stage"] is False
    assert current["rotation_context"]["confirmed_events"]["active_count"] == 0


def test_duplicate_alias_and_source_permutation_never_add_corroboration():
    sources = reads()
    baseline = compose(sources)
    for reordered in permutations(sources):
        assert compose(list(reordered)) == baseline
    alias = source("same-price-other-dashboard", roots=("price:xlp:oct6",), groups=("equity_price",))
    copied = compose(sources + [alias])
    assert copied["confluence"]["nonredundant_component_count"] == 1
    assert copied["hazard_summary"] == baseline["hazard_summary"]
    assert copied["policy_summary"] == baseline["policy_summary"]


def test_shared_components_collapse_transitively():
    sources = [settled._rotation_read(rotation(roots=("a",), groups=()), SESSION, now=NOW),
               source("middle", roots=("a", "b")), source("last", roots=("b",))]
    audit = compose(sources)["confluence"]
    assert audit["nonredundant_component_count"] == 1
    assert audit["nonredundant_components"] == [["last", "middle", "site-marketdata-rotation-events"]]


def test_disjoint_recorded_roots_do_not_claim_statistical_independence():
    sources = [settled._rotation_read(rotation(groups=()), SESSION, now=NOW),
               source("credit", roots=("credit:hy:oct6",))]
    audit = compose(sources)["confluence"]
    assert audit["source_relationships"][0]["relationship"] == "DISTINCT_RECORDED_ROOTS"
    assert audit["nonredundant_component_count"] == 2
    assert audit["statistical_independence_established"] is False


@pytest.mark.parametrize("extra", [
    source("unknown", roots=(), status="UNKNOWN"),
    source("partial", roots=("a",), status="PARTIAL"),
    source("empty-complete", roots=()),
])
def test_incomplete_lineage_total_is_null(extra):
    audit = compose(reads() + [extra])["confluence"]
    assert audit["nonredundant_component_count"] is None
    assert extra.source_id in audit["unknown_lineage_sources"]


@pytest.mark.parametrize("extra", [
    [source("self", roots=("a",), parents=("self",))],
    [source("a", roots=("a",), parents=("b",)), source("b", roots=("b",), parents=("a",))],
    [source("downstream", roots=("a",), parents=("risk-envelope-settled",))],
])
def test_cycles_and_envelope_feedback_are_rejected(extra):
    with pytest.raises(EnvelopeContractError):
        compose(reads() + extra)


def test_declared_ancestry_is_shared_even_when_roots_differ():
    audit = compose(reads() + [source("credit-summary", roots=("other",), parents=("market-state-latest",))])["confluence"]
    relationship = next(r for r in audit["source_relationships"] if set(r["sources"]) == {"market-state-latest", "credit-summary"})
    assert relationship["relationship"] == "SHARED"


def test_rotation_cannot_be_repurposed_as_hazard():
    sources = reads()
    sources[-1] = replace(sources[-1], role="hazard_evidence", hazard_stage="FRAGILE")
    with pytest.raises(EnvelopeContractError):
        compose(sources)


@pytest.mark.parametrize("mutate,reason", [
    (lambda d: d["early_context"].update(as_of="2026-10-05"), "off_session"),
    (lambda d: d["early_context"].update(as_of="2026-10-07"), "future_source_session"),
    (lambda d: d["early_context"].update(as_of=None), "missing_or_malformed_session"),
    (lambda d: d["early_context"].update(as_of="2026-10-99"), "missing_or_malformed_session"),
    (lambda d: d["early_context"].update(available_at="2026-10-07T13:00:00Z"), "source_not_available"),
    (lambda d: d["early_context"].update(produced_at="tomorrow"), "malformed_source_clock"),
    (lambda d: d["early_context"].update(freshness={"stale": True}), "source_stale"),
    (lambda d: d["early_context"].update(state=None), "early_context_unavailable"),
])
def test_bad_rotation_clock_or_state_is_unavailable_not_no_shift(mutate, reason):
    doc = rotation()
    mutate(doc)
    read = settled._rotation_read(doc, SESSION, now=NOW)
    assert read.usable is False
    assert read.detail["excluded_reason"] == reason
    output = compose(reads()[:2] + [read])
    assert output["rotation_context"]["state"] is None
    assert output["confluence"]["rotation_state"] is None
    assert output["hazard_summary"]["stage"] == "FRAGILE"


def test_missing_rotation_is_context_absence_and_does_not_null_hazard():
    output = compose(reads()[:2] + [settled._rotation_read(None, SESSION, now=NOW)])
    assert output["rotation_context"]["coverage"] == "MISSING"
    assert output["rotation_context"]["state"] is None
    assert output["hazard_summary"]["stage"] == "FRAGILE"


def test_product_pairs_are_bounded_and_lineage_is_not_repeated():
    doc = rotation()
    doc["early_context"]["pairs"] = [
        {"pair_id": f"p{i}", "horizons": {"2s": {"ratio_return_pct": i}}, "lineage": lineage((str(i),))}
        for i in range(13)
    ]
    output = compose(reads()[:2] + [settled._rotation_read(doc, SESSION, now=NOW)])
    native = output["rotation_context"]["early_context"]
    assert len(native["pairs"]) == 12
    assert native["source_pair_count"] == 13 and native["pairs_omitted"] == 1
    assert native["omitted_pair_ids"] == ["p12"]
    assert "lineage" not in native and all("lineage" not in p for p in native["pairs"])


def test_healthy_broadening_under_risk_on_has_no_risk_off_effect():
    sources = reads()
    sources[0] = replace(sources[0], state="RISK_ON", score=76)
    sources[1] = replace(sources[1], state="INTACT", hazard_stage="NONE")
    sources[-1] = settled._rotation_read(rotation(state="BROADENING"), SESSION, now=NOW)
    output = compose(sources)
    assert output["measured_state"]["verdict"] == "RISK_ON"
    assert output["hazard_summary"]["stage"] == "NONE"
    assert output["confluence"]["state"] == "BROADENING__RISK_ON"
    assert output["policy_summary"]["posture"] == "NORMAL"


def test_native_caps_and_freshness_survive_unchanged():
    native = {"asof": SESSION, "verdict": "MIXED", "score": 59, "raw_score": 75,
              "score_source": "verdict_cap", "capped": True, "score_caps": [{"kind": "verdict_cap", "limit": 59}],
              "overrides": [{"kind": "regime", "note_en": "Recorded native cause"}],
              "components": [{"key": "breadth", "score": 30, "weight": 0.16}],
              "input_vintages": {"breadth": SESSION}, "freshness": {"stale": False}}
    adapted = settled._market_state_read(native, SESSION, context_enabled=True, now=NOW)
    for key, value in native.items():
        if key != "asof":
            assert adapted.detail[key] == value
    assert adapted.detail["lineage"]["status"] == "PARTIAL"
    assert adapted.detail["lineage"]["dependency_groups"] == ["equity_price"]


def write_log(tmp_path, rows):
    path = tmp_path / "data" / "market_state" / "forward_log.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return path


def recorded_rows():
    return [
        {"asof": "2026-09-29", "logged_at": "2026-09-30T01:00:00Z", "verdict": "RISK_ON", "score": 61, "raw_score": 61,
         "components": {"risk": {"score": 77, "weight": 0.18}}},
        {"asof": "2026-09-30", "logged_at": "2026-10-01T01:00:00Z", "verdict": "MIXED", "score": 54, "raw_score": 54,
         "components": {"risk": {"score": 37, "weight": 0.18}}},
        {"asof": "2026-10-05", "logged_at": "2026-10-06T01:00:00Z", "verdict": "MIXED", "score": 48, "raw_score": 48},
        {"asof": SESSION, "logged_at": "2026-10-07T01:00:00Z", "verdict": "MIXED", "score": 51, "raw_score": 51},
    ]


def test_recorded_transition_is_prior_backdrop_not_an_invented_event_week_flip(tmp_path):
    rows = recorded_rows()
    result = settled._recorded_market_transition(write_log(tmp_path, rows), SESSION, now=NOW, current=rows[-1])
    assert result["latest_comparison"]["verdict_changed"] is False
    change = result["latest_recorded_change"]
    assert change["before"]["asof"] == "2026-09-29"
    assert change["after"]["asof"] == "2026-09-30"
    assert change["after"]["logged_at"] == "2026-10-01T01:00:00Z"
    assert change["component_movements"][0]["score_delta"] == -40
    assert change["cause"] == "not_inferred_from_snapshot_differences"
    assert result["current_matches_latest_record"] is True


def test_current_mixed_without_recorded_prior_does_not_invent_transition(tmp_path):
    row = recorded_rows()[-1]
    result = settled._recorded_market_transition(write_log(tmp_path, [row]), SESSION, now=NOW, current=row)
    assert result["latest_recorded_change"] is None
    assert result["latest_comparison"] is None
    assert result["previous_recorded"] is None


@pytest.mark.parametrize("fault", ["duplicate", "unordered", "missing_clock", "future_receipt"])
def test_bad_first_writer_evidence_cannot_create_a_transition(tmp_path, fault):
    rows = recorded_rows()[:2]
    if fault == "duplicate":
        rows.append(dict(rows[-1]))
    elif fault == "unordered":
        rows.reverse()
    elif fault == "missing_clock":
        rows[0].pop("logged_at")
    else:
        rows[0]["logged_at"] = "2026-10-09T01:00:00Z"
    result = settled._recorded_market_transition(write_log(tmp_path, rows), SESSION, now=NOW)
    assert result["latest_recorded_change"] is None


def test_future_rows_and_rebuilt_current_snapshot_do_not_replace_first_writer(tmp_path):
    rows = recorded_rows()
    rows.append({"asof": "2026-10-08", "logged_at": "2026-10-09T01:00:00Z", "verdict": "RISK_OFF", "score": 20})
    current = dict(rows[-2], score=52)
    result = settled._recorded_market_transition(write_log(tmp_path, rows), SESSION, now=NOW, current=current)
    assert result["latest_recorded"]["score"] == 51
    assert result["current_snapshot"]["score"] == 52
    assert result["current_matches_latest_record"] is False
    assert result["excluded_record_count"] == 1


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def test_settled_builder_reads_actual_rotation_owner_and_recorded_log(tmp_path):
    market = dict(recorded_rows()[-1], freshness={"stale": False}, radar={"state": "calm"})
    dump(tmp_path / "data/market_state/latest.json", market)
    dump(tmp_path / "data/leadership_crack/latest.json", {"asof": SESSION, "state": "BROKEN"})
    dump(tmp_path / "site/marketdata/rotation_events.json", rotation())
    path = write_log(tmp_path, recorded_rows())
    before = path.read_bytes()
    result = settled.build(tmp_path, now=NOW)
    assert result["rotation_context"]["state"] == "DEFENSIVE_RELATIVE_STRENGTH"
    assert result["market_transition"]["latest_recorded_change"]["after"]["asof"] == "2026-09-30"
    assert path.read_bytes() == before
    assert not (tmp_path / "data/risk_envelope/latest.json").exists()


def test_live_reuses_context_adapter_and_preserves_native_caps_and_clocks(tmp_path, monkeypatch):
    now = datetime(2026, 10, 7, 14, 1, tzinfo=timezone.utc)
    produced = datetime(2026, 10, 7, 14, 1, 1, tzinfo=timezone.utc)
    native = {"verdict": "MIXED", "score": 59, "raw_score": 76, "score_source": "verdict_cap", "capped": True,
              "score_caps": [{"kind": "verdict_cap", "limit": 59}], "overrides": [{"kind": "alert"}],
              "radar": {"state": "calm"}, "source_event_time": "2026-10-07T13:59:50Z"}
    dump(tmp_path / "site/live/risk_state.json", {"built": "2026-10-07 14:00:00 UTC", "live_active": True, "live": native})
    dump(tmp_path / "data/leadership_crack/latest.json", {"asof": SESSION, "state": "BROKEN"})
    dump(tmp_path / "data/risk_envelope/latest.json", {"source_session": SESSION, "bundle_id": "settled", "hazard_summary": {"stage": "FRAGILE"}})
    dump(tmp_path / "site/marketdata/rotation_events.json", rotation(day="2026-10-07"))
    write_log(tmp_path, recorded_rows())
    monkeypatch.setattr(live, "_risk_envelope_cfg", lambda: {"debounce_ticks": 3, "stale_after_min": 5})
    result = live.build(tmp_path, now=now, produced_now=produced)
    measured = next(s for s in result["provenance"]["sources"] if s["source_id"] == "market-state-latest")
    assert measured["detail"]["score_source"] == "verdict_cap"
    assert measured["detail"]["capped"] is True
    assert measured["detail"]["score_caps"] == native["score_caps"]
    assert result["rotation_context"]["state"] == "DEFENSIVE_RELATIVE_STRENGTH"
    assert result["observed_at"] != result["produced_at"]
    assert result["clocks"]["event_time"] == "2026-10-07T13:59:50.000Z"
    assert result["hazard_summary"]["stage"] == "FRAGILE"
    # A prior-session rotation does not acquire today's source clock just because
    # the live builder ran again.
    dump(tmp_path / "site/marketdata/rotation_events.json", rotation())
    prior = live.build(tmp_path, now=now, produced_now=produced)
    assert prior["rotation_context"]["state"] is None
    assert prior["rotation_context"]["as_of"] == SESSION
    assert prior["hazard_summary"] == result["hazard_summary"]
    assert prior["policy_summary"] == result["policy_summary"]


def test_fresh_early_context_does_not_inherit_last_confirmed_event_date():
    doc = rotation()
    doc.pop("asof")
    doc["as_of"] = "2026-09-25"
    output = compose(reads()[:2] + [settled._rotation_read(doc, SESSION, now=NOW)])
    assert output["rotation_context"]["state"] == "DEFENSIVE_RELATIVE_STRENGTH"
    assert output["rotation_context"]["as_of"] == SESSION
    assert output["rotation_context"]["confirmed_events"]["as_of"] == "2026-09-25"
    assert output["rotation_context"]["confirmed_events"]["usable"] is False


def test_nested_actual_availability_cannot_arrive_after_cutoff():
    doc = rotation()
    doc["early_context"]["availability"] = {"available_at": "2026-10-07T13:00:00Z"}
    read = settled._rotation_read(doc, SESSION, now=NOW)
    assert read.usable is False and read.detail["excluded_reason"] == "source_not_available"


def test_native_rotation_production_clock_and_older_confirmation_date_are_preserved():
    doc = rotation()
    doc.pop("asof")
    doc.update(as_of="2026-09-25", generated_utc="2026-10-07 11:00 UTC")
    read = settled._rotation_read(doc, SESSION, now=NOW)
    assert read.usable is True
    assert read.as_of == SESSION
    assert read.detail["confirmed_events"]["as_of"] == "2026-09-25"
    assert read.detail["confirmed_events"]["usable"] is False


def test_us_source_session_remains_future_after_utc_midnight():
    now = datetime(2026, 10, 9, 1, tzinfo=timezone.utc)  # still October 8 in New York
    read = settled._rotation_read(rotation(day="2026-10-09"), "2026-10-09", now=now)
    assert read.usable is False
    assert read.detail["excluded_reason"] == "future_source_session"
    assert settled._clock_reason({}, "2026-10-08", "2026-10-08", now) is None


@pytest.mark.parametrize("parent,reason", [
    ({"produced_at": "2026-10-07T13:00:00Z"}, "future_production_clock"),
    ({"generated_utc": "2026-10-07T13:00:00Z"}, "future_production_clock"),
    ({"generated_utc": "2026-10-07 13:00 UTC"}, "future_production_clock"),
    ({"available_at": "2026-10-07T13:00:00Z"}, "source_not_available"),
    ({"availability": {"available_at": "2026-10-07T13:00:00Z"}}, "source_not_available"),
    ({"produced_at": "unknown"}, "malformed_source_clock"),
    ({"produced_at": "2026-10-07T11:00:00Z", "generated_utc": "2026-10-07T13:00:00Z"}, "future_production_clock"),
    ({"available_at": "2026-10-07T11:00:00Z", "availability": {"available_at": "2026-10-07T13:00:00Z"}}, "source_not_available"),
    ({"availability": "unknown"}, "malformed_availability"),
    ({"freshness": {"stale": True}}, "source_stale"),
])
def test_fresh_child_cannot_bypass_parent_artifact_clocks(parent, reason):
    doc = rotation()
    doc.pop("asof")
    doc.update(as_of="2026-09-25", **parent)
    read = settled._rotation_read(doc, SESSION, now=NOW)
    assert read.usable is False
    assert read.detail["excluded_reason"] == reason
    assert compose(reads()[:2] + [read])["rotation_context"]["state"] is None


@pytest.mark.parametrize("mutate,reason", [
    ({"asof": "2026-10-07"}, "future_source_session"),
    ({"asof": "2026-10-05"}, "off_session"),
    ({"asof": None}, "missing_or_malformed_session"),
    ({"asof": "2026-10-99"}, "missing_or_malformed_session"),
    ({"available_at": "2026-10-07T13:00:00Z"}, "source_not_available"),
    ({"availability": {"available_at": "2026-10-07T13:00:00Z"}}, "source_not_available"),
    ({"produced_at": "2026-10-07T13:00:00Z"}, "future_production_clock"),
    ({"produced_at": "bad"}, "malformed_source_clock"),
    ({"freshness": {"stale": True}}, "source_stale"),
])
def test_unqualified_current_snapshot_cannot_bypass_recorded_history(tmp_path, mutate, reason):
    current = dict(recorded_rows()[-1], **mutate)
    result = settled._recorded_market_transition(
        write_log(tmp_path, recorded_rows()), SESSION, now=NOW, current=current)
    assert result["current_snapshot"] is None
    assert result["current_snapshot_excluded_reason"] == reason
    assert result["current_matches_latest_record"] is None
    assert result["latest_recorded"]["asof"] == SESSION
    assert result["latest_recorded_change"]["after"]["asof"] == "2026-09-30"


def test_future_economic_record_is_excluded_on_us_clock(tmp_path):
    rows = recorded_rows()[:2] + [
        {"asof": "2026-10-09", "logged_at": "2026-10-09T00:30:00Z", "verdict": "RISK_OFF"}]
    result = settled._recorded_market_transition(
        write_log(tmp_path, rows), "2026-10-09",
        now=datetime(2026, 10, 9, 1, tzinfo=timezone.utc))
    assert result["latest_recorded"]["asof"] == "2026-09-30"
    assert result["excluded_record_count"] == 1


def test_new_context_schema_closes_authority_and_unknown_meanings():
    from pathlib import Path
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((Path(__file__).resolve().parents[1] / "contracts/risk_envelope.schema.json").read_text())
    result = compose(reads())
    jsonschema.validate(result, schema)
    for invented in ({"confidence": 0.9}, {"probability": 0.8}, {"changes_policy": True}):
        malformed = json.loads(json.dumps(result))
        malformed["confluence"].update(invented)
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(malformed, schema)


def test_original_clock_metadata_survives_compact_projection_without_inference():
    from copy import deepcopy
    doc = rotation()
    doc.update(generated_utc="2026-10-07 11:00 UTC",
               stale_after="2026-10-07T14:00:00Z",
               freshness={"stale": False, "unrelated": {"body": "excluded"}},
               availability={"status": "UNKNOWN", "available_at": None, "body": "excluded"})
    doc["early_context"].update(generated_utc="2026-10-07 11:00 UTC",
                                stale_after="2026-10-07T13:00:00Z",
                                freshness={"stale": False, "body": "excluded"},
                                availability={"status": "UNKNOWN", "available_at": None})
    before = deepcopy(doc)
    output = compose(reads()[:2] + [settled._rotation_read(doc, SESSION, now=NOW)])
    parent = output["rotation_context"]["source_clock_receipt"]
    child = output["rotation_context"]["early_context"]
    assert parent == {"generated_utc": doc["generated_utc"], "stale_after": doc["stale_after"],
                      "freshness": {"stale": False},
                      "availability": {"status": "UNKNOWN", "available_at": None}}
    assert child["generated_utc"] == doc["early_context"]["generated_utc"]
    assert child["stale_after"] == doc["early_context"]["stale_after"]
    assert child["freshness"] == {"stale": False}
    assert child["availability"] == {"status": "UNKNOWN", "available_at": None}
    assert "available_at" not in child and "produced_at" not in child
    assert doc == before


def test_missing_source_expiry_and_first_availability_are_not_filled_by_parent():
    doc = rotation()
    doc["generated_utc"] = "2026-10-07 11:00 UTC"
    doc["early_context"]["availability"] = {"status": "UNKNOWN", "available_at": None}
    output = compose(reads()[:2] + [settled._rotation_read(doc, SESSION, now=NOW)])
    child = output["rotation_context"]["early_context"]
    assert output["rotation_context"]["source_clock_receipt"] == {"generated_utc": doc["generated_utc"]}
    for key in ("produced_at", "available_at", "stale_after", "freshness"):
        assert key not in child
    assert child["availability"] == {"status": "UNKNOWN", "available_at": None}


def test_clock_receipts_change_evidence_identity_but_never_stage_policy_or_confluence():
    doc = rotation()
    without = compose(reads()[:2] + [settled._rotation_read(doc, SESSION, now=NOW)])
    doc["generated_utc"] = "2026-10-07 11:00 UTC"
    sources = reads()[:2] + [settled._rotation_read(doc, SESSION, now=NOW)]
    with_receipt = compose(sources)
    for key in ("measured_state", "hazard_summary", "policy_summary", "confluence", "authority"):
        assert without[key] == with_receipt[key]
    assert without["bundle_id"] != with_receipt["bundle_id"]
    republished = compose_envelope(sources=sources, market="US", source_session=SESSION,
                                  observed_at="2026-10-07T12:01:00Z", produced_at="2026-10-07T12:02:00Z")
    assert republished["bundle_id"] == with_receipt["bundle_id"]
    assert republished["rotation_context"] == with_receipt["rotation_context"]


def test_optional_clock_receipt_schema_is_closed_and_backward_compatible():
    from copy import deepcopy
    from pathlib import Path
    import jsonschema
    schema = json.loads((Path(__file__).parents[1] / "contracts/risk_envelope.schema.json").read_text())
    old = compose(reads())
    jsonschema.validate(old, schema)
    doc = rotation()
    doc.update(generated_utc="2026-10-07 11:00 UTC", stale_after="2026-10-07T13:00:00Z")
    doc["early_context"].update(generated_utc="2026-10-07 11:00 UTC",
                                freshness={"stale": False}, stale_after="2026-10-07T13:00:00Z")
    new = compose(reads()[:2] + [settled._rotation_read(doc, SESSION, now=NOW)])
    jsonschema.validate(new, schema)
    invalid = deepcopy(new)
    invalid["rotation_context"]["source_clock_receipt"]["unknown_payload"] = {"body": "excluded"}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(invalid, schema)


# BR-IR-01: an optional excluded source cannot invalidate the native envelope.
@pytest.fixture(scope="module")
def optional_clock_schema():
    from pathlib import Path
    from jsonschema import Draft202012Validator
    return Draft202012Validator(json.loads(
        (Path(__file__).parents[1] / "contracts/risk_envelope.schema.json").read_text()))


def _assert_optional_clock_composition(doc, validator):
    from copy import deepcopy
    before = deepcopy(doc)
    native_sources = reads()[:2]
    native = compose(native_sources)
    optional = settled._rotation_read(doc, SESSION, now=NOW)
    output = compose(native_sources + [optional])
    assert not list(validator.iter_errors(native)), "native-only control must be valid"
    errors = [(list(error.absolute_path), error.message) for error in validator.iter_errors(output)]
    assert not errors, errors
    for key in ("measured_state", "hazard_summary", "policy_summary", "policies", "episodes", "authority"):
        assert output[key] == native[key], key
    assert json.loads(json.dumps(output)) == output
    assert doc == before
    return optional, output


@pytest.mark.parametrize("where", ["parent", "child"])
@pytest.mark.parametrize("path,value,reason", [
    (("generated_utc",), [], "malformed_source_clock"),
    (("produced_at",), {}, "malformed_source_clock"),
    (("available_at",), 1, "malformed_source_clock"),
    (("stale_after",), [], "malformed_source_expiry"),
    (("stale_after",), "not-an-expiry", "malformed_source_expiry"),
    (("stale_after",), "2026-10-07T13:00:00", "malformed_source_expiry"),
    (("availability",), [], "malformed_availability"),
    (("availability", "status"), [], "malformed_availability"),
    (("availability", "status"), True, "malformed_availability"),
    (("availability", "available_at"), [], "malformed_source_clock"),
    (("availability", "available_at"), False, "malformed_source_clock"),
    (("availability", "available_at"), "not-an-availability", "malformed_source_clock"),
    (("freshness",), [], "malformed_freshness"),
    (("freshness", "stale"), "false", "malformed_freshness"),
    (("freshness", "stale"), None, "malformed_freshness"),
    (("freshness", "stale"), 0, "malformed_freshness"),
])
def test_malformed_optional_clock_is_excluded_without_schema_poisoning(
        where, path, value, reason, optional_clock_schema, request):
    from copy import deepcopy
    from pathlib import Path
    guard_source = Path(__file__).with_name("conftest.py").resolve()
    assert any(isinstance(getattr(plugin, "__file__", None), str)
               and Path(plugin.__file__).resolve() == guard_source
               for plugin in request.config.pluginmanager.get_plugins())
    assert hasattr(request.config, "_mm_data_guard_baseline")
    assert hasattr(request.config, "_mm_module_baseline")
    doc = rotation()
    target = doc if where == "parent" else doc["early_context"]
    node = target
    for name in path[:-1]:
        node = node.setdefault(name, {})
    node[path[-1]] = deepcopy(value)
    optional, output = _assert_optional_clock_composition(doc, optional_clock_schema)
    assert optional.usable is False and optional.detail["excluded_reason"] == reason
    assert output["rotation_context"]["usable"] is False
    assert output["rotation_context"]["early_context"] is None
    assert output["rotation_context"]["excluded_reason"] == reason
    assert any(row["source_id"] == optional.source_id and row["reason"] == reason
               for row in output["confluence"]["excluded_sources"])


@pytest.mark.parametrize("where", ["parent", "child"])
@pytest.mark.parametrize("expiry,usable", [
    ("2026-10-07T11:59:59Z", False),
    ("2026-10-07T12:00:00Z", False),
    ("2026-10-07T12:00:00.001Z", True),
])
def test_declared_optional_expiry_is_validated_at_its_original_boundary(
        where, expiry, usable, optional_clock_schema):
    doc = rotation()
    target = doc if where == "parent" else doc["early_context"]
    target["stale_after"] = expiry
    optional, output = _assert_optional_clock_composition(doc, optional_clock_schema)
    assert optional.usable is usable and output["rotation_context"]["usable"] is usable
    if not usable:
        assert optional.detail["excluded_reason"] == "source_expired"
    if where == "parent":
        assert output["rotation_context"]["source_clock_receipt"]["stale_after"] == expiry
    elif usable:
        assert output["rotation_context"]["early_context"]["stale_after"] == expiry


@pytest.mark.parametrize("where", ["parent", "child"])
@pytest.mark.parametrize("metadata", [
    {},
    {"generated_utc": None, "produced_at": None, "available_at": None, "stale_after": None,
     "availability": None, "freshness": None},
    {"availability": {"status": None, "available_at": None}, "freshness": {"stale": False}},
    {"generated_utc": "2026-10-07 11:00 UTC", "produced_at": "2026-10-07T11:00:00.125Z",
     "available_at": "2026-10-07T10:59:59.750Z", "stale_after": "2026-10-07T13:00:00+00:00",
     "availability": {"status": "UNKNOWN", "available_at": None}, "freshness": {"stale": False}},
])
def test_valid_original_optional_clock_values_null_unknown_and_absence_are_preserved(
        where, metadata, optional_clock_schema):
    from copy import deepcopy
    doc = rotation()
    target = doc if where == "parent" else doc["early_context"]
    target.update(deepcopy(metadata))
    optional, output = _assert_optional_clock_composition(doc, optional_clock_schema)
    assert optional.usable is True and output["rotation_context"]["usable"] is True
    projected = (output["rotation_context"].get("source_clock_receipt", {})
                 if where == "parent" else output["rotation_context"]["early_context"])
    for key in ("generated_utc", "produced_at", "available_at", "stale_after", "availability", "freshness"):
        if key in metadata:
            assert projected[key] == metadata[key]
        else:
            assert key not in projected
    if where == "parent" and not metadata:
        assert "source_clock_receipt" not in output["rotation_context"]


def test_mixed_valid_and_malformed_parent_receipt_retains_valid_raw_fields_and_exclusion(optional_clock_schema):
    doc = rotation()
    doc.update(generated_utc="2026-10-07 11:00 UTC", stale_after="2026-10-07T13:00:00.125Z",
               availability={"status": [], "available_at": "2026-10-07T10:00:00Z"},
               freshness={"stale": False})
    optional, output = _assert_optional_clock_composition(doc, optional_clock_schema)
    assert optional.usable is False and optional.detail["excluded_reason"] == "malformed_availability"
    receipt = output["rotation_context"]["source_clock_receipt"]
    assert receipt == {"generated_utc": doc["generated_utc"], "stale_after": doc["stale_after"],
                       "availability": {"available_at": "2026-10-07T10:00:00Z"},
                       "freshness": {"stale": False}}


def test_expiry_qualification_does_not_invent_an_observation_clock():
    doc = rotation()
    doc["stale_after"] = "2026-10-07T11:00:00Z"
    # Explicit now controls expiration; no implicit current-time sampling is added.
    assert settled._clock_reason(doc, SESSION, SESSION, None) is None
    assert settled._clock_reason(doc, SESSION, SESSION, NOW) == "source_expired"
    doc["stale_after"] = []
    assert settled._clock_reason(doc, SESSION, SESSION, None) == "malformed_source_expiry"
