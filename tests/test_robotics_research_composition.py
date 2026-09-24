"""tests/test_robotics_research_composition.py — envelope-composition tests
for the Robotics research composer (R2).

Operation gmi-robotics-fable-ceo-e2e-20260923-chairman-001 (carrier #7908).
These pin the SHARED envelope: every composed response validates against
``contracts/market_ontology/robotics_theme_research.v1.schema.json``, the
generation fingerprint is deterministic over content and pagination-invariant,
the refusal ladder matches the shared owner's, evidence selection is
authorized-only, and the module stays pure (no pandas/requests/app/brain).

The schema is the same envelope family as
``semiconductor_theme_research.v1`` — one generic route and client serve both
verticals — so every assertion here is also a parity pin.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import re
from pathlib import Path

import jsonschema
import pytest

try:  # the composer needs the shared assertion contract (#7870, RR9: main alone must
    # still collect); when that module is absent every test here is a strict xfail.
    import engine.market_ontology.robotics_theme_research as robotics
    HAS_SHARED = True
except ImportError:  # pragma: no cover - carrier base without the shared foundation
    robotics = None  # type: ignore[assignment]
    HAS_SHARED = False

pytestmark = pytest.mark.xfail(
    condition=not HAS_SHARED,
    strict=True,
    reason="engine.theme_graph.curation_assertion (#7870 shared foundation) is not on "
           "this base; flips loudly the day it lands",
)
from tests.robotics_research_helpers import FIXTURE_ROOT, load_case, load_bundle_case

try:
    import engine.market_ontology.semiconductor_theme_research as semiconductor
    HAS_SHARED_TYPES = True
except ImportError:  # pragma: no cover - explained by the xfail-strict marker
    HAS_SHARED_TYPES = False

try:
    from engine.theme_graph.curation_assertion import encode_assertion
    HAS_CODEC = True
except Exception:  # pragma: no cover
    HAS_CODEC = False

SHARED_TYPES_REASON = (
    "shared composition types not on this base; pinned to #7870 c6c67c87"
)
CODEC_REASON = "assertion codec not on this base"

SCHEMA_PATH = (Path(__file__).resolve().parent.parent / 'contracts'
               / 'market_ontology' / 'robotics_theme_research.v1.schema.json')
_RESPONSE_SCHEMA = jsonschema.Draft202012Validator(
    json.loads(SCHEMA_PATH.read_text(encoding='utf-8')))

TOP_LEVEL_KEYS = {
    "schema", "definition_version", "generation", "request",
    "native_subjects", "summary", "companies", "industrial_views",
    "economics", "expectations", "evidence_refs", "authorized_coverage",
    "limitations", "authority",
}


def compose(name: str, **query_overrides):
    query, bundle = load_bundle_case(name)
    if query_overrides:
        query = dataclasses.replace(query, **query_overrides)
    return robotics.compose_robotics_research(query, bundle), query, bundle


def ready_names() -> list[str]:
    return [p.stem for p in sorted(FIXTURE_ROOT.glob("*.json"))
            if load_case(p.stem).get("status") == "ready"]


# The stored later_retained_backdate query is a system_replay query with no
# source_cutoff; composing it as stored must refuse (replay_cutoffs_required),
# so the schema sweep normalizes it with the cutoff its own case supplies.
def replayable(name: str):
    query, bundle = load_bundle_case(name)
    if query.time_mode == "system_replay" and query.source_cutoff is None:
        query = dataclasses.replace(query, source_cutoff="2026-09-24T00:00:00Z")
    return query, bundle


# ---------------------------------------------------------------------------
# Envelope: schema validation across the corpus x every view
# ---------------------------------------------------------------------------

def test_every_response_validates_against_the_contract():
    ready = ready_names()
    assert len(ready) == 20
    for name in ready:
        query, bundle = replayable(name)
        for view in robotics.VIEWS:
            response = robotics.compose_robotics_research(
                dataclasses.replace(query, view=view), bundle)
            _RESPONSE_SCHEMA.validate(response)


def test_top_level_envelope_keys_and_consts():
    response, query, _ = compose("witness_perception_orbbec_twinny")
    assert set(response.keys()) == TOP_LEVEL_KEYS
    assert response["schema"] == robotics.SCHEMA_ID
    assert response["definition_version"] == robotics.DEFINITION_VERSION
    assert response["request"] == {
        "anchor_theme_id": query.anchor_theme_id,
        "slice_key": query.slice_key,
        "view": query.view,
        "time_mode": query.time_mode,
        "source_cutoff": query.source_cutoff,
        "recorded_cutoff": query.recorded_cutoff,
        "offset": query.offset,
        "limit": query.limit,
        "expected_generation": query.expected_generation,
    }
    assert set(response["industrial_views"].keys()) == set(robotics.VIEWS)
    assert response["limitations"] == sorted(response["limitations"])


def test_native_refs_pass_through_as_opaque_evidence():
    response, _, _ = compose("witness_perception_orbbec_twinny")
    natives = [e for e in response["evidence_refs"] if e["kind"] == "native"]
    assert natives == [{
        "owner_store": "theme_graph.curation_assertion",
        "native_identity": {"curation_revision":
                            "gmirca_e02206282f8189d337e1aad57e3f925e"},
        "reference_id":
            "gmi-curation://robotics_automation/gmirca_e02206282f8189d337e1aad57e3f925e",
        "kind": "native",
    }]


# ---------------------------------------------------------------------------
# Economics / expectations / manufacturing section law
# ---------------------------------------------------------------------------

def test_economics_section_is_always_the_missing_witness_slot():
    for name in ("witness_perception_orbbec_twinny", "sanhua_actuator_scaleup"):
        response, _, _ = compose(name)
        section = response["economics"]
        assert section["status"] == "unavailable"
        assert section["reason"] == "no_management_sequence_in_robotics_v1"
        assert section["management"] is None
        assert section["witness_gate"] == "missing"
        assert section["input_refs"] == []


def test_economics_view_rows_do_not_heal_the_economics_section():
    response, _, _ = compose("sanhua_actuator_scaleup", view="economics")
    assert len(response["industrial_views"]["economics"]["rows"]) == 1
    assert response["economics"]["status"] == "unavailable"


def test_expectations_are_structurally_unavailable():
    response, _, _ = compose("witness_perception_orbbec_twinny")
    expectations = response["expectations"]
    assert expectations["management"]["status"] == "unavailable"
    assert expectations["management"]["reason"] == \
        "no_management_sequence_in_robotics_v1"
    assert expectations["management"]["roles"] is None
    assert expectations["external_consensus"]["reason"] == "no_external_consensus"
    assert expectations["house_forecast"]["reason"] == "not_authorized"
    assert expectations["market_incorporation"]["reason"] == "not_authorized"


def test_manufacturing_view_is_unavailable_across_the_corpus():
    for name in ready_names():
        if name == "later_retained_backdate":
            # its normalized replay selects nothing at all; the empty-selection
            # reason is pinned by the temporal suite instead
            continue
        query, bundle = replayable(name)
        response = robotics.compose_robotics_research(
            dataclasses.replace(query, view="manufacturing"), bundle)
        view = response["industrial_views"]["manufacturing"]
        assert view["rows"] == []
        assert view["status"] == "unavailable"
        assert view["reason"] == "no_manufacturing_evidence"
        assert view["total"] == {"value": None, "reason": None}


# ---------------------------------------------------------------------------
# Empty selection
# ---------------------------------------------------------------------------

def test_empty_bundle_composes_unavailable_not_refused():
    query, bundle = load_bundle_case("witness_perception_orbbec_twinny")
    empty = dataclasses.replace(
        bundle, assertions=(), revision_tuple=(), identity_results=(),
        interpretation_blocks=(), native_refs=(), omissions=())
    response = robotics.compose_robotics_research(query, empty)
    assert response["authorized_coverage"]["selected"] == 0
    assert response["authorized_coverage"]["status"] == "unavailable"
    for view in robotics.VIEWS:
        section = response["industrial_views"][view]
        assert section["rows"] == []
        assert section["status"] == "unavailable"
        assert section["reason"] == "no_selected_assertions"
    assert response["companies"]["status"] == "unavailable"
    assert response["companies"]["reason"] == "no_companies"
    assert response["summary"]["status"] == "unavailable"
    assert response["summary"]["reason"] == "no_selected_assertions"
    assert response["native_subjects"] == []
    _RESPONSE_SCHEMA.validate(response)


# ---------------------------------------------------------------------------
# Generation fingerprint
# ---------------------------------------------------------------------------

def test_generation_is_deterministic_and_shaped():
    first, _, bundle = compose("witness_perception_orbbec_twinny")
    second = robotics.compose_robotics_research(
        robotics.ResearchQuery(**first["request"]), bundle)
    assert first["generation"] == second["generation"]
    assert re.fullmatch(r"gen_[0-9a-f]{32}", first["generation"])


def test_generation_is_pagination_invariant():
    response, query, bundle = compose("hds_operating_snapshot", view="capacity")
    generation = response["generation"]
    paged = robotics.compose_robotics_research(
        dataclasses.replace(query, view="capacity", offset=0, limit=10,
                            expected_generation=generation), bundle)
    assert paged["generation"] == generation


def test_generation_follows_the_time_scoping_fields():
    response, query, bundle = compose("witness_perception_orbbec_twinny")
    variants = {
        dataclasses.replace(query, slice_key="precision_motion"),
        dataclasses.replace(query, view="commercial"),
        dataclasses.replace(query, time_mode="source_history",
                            source_cutoff="2026-09-23T00:00:00Z"),
    }
    for variant in variants:
        other = robotics.compose_robotics_research(variant, bundle)
        assert other["generation"] != response["generation"]


def test_expected_generation_roundtrip_and_mismatch():
    response, query, bundle = compose("witness_perception_orbbec_twinny")
    ok = robotics.compose_robotics_research(
        dataclasses.replace(query, expected_generation=response["generation"]),
        bundle)
    assert ok["request"]["expected_generation"] == response["generation"]
    with pytest.raises(robotics.ResearchRefusal) as exc:
        robotics.compose_robotics_research(
            dataclasses.replace(query, expected_generation="gen_" + "0" * 32),
            bundle)
    assert exc.value.code == "generation_changed"
    # None is "no expectation" — a first fetch composes without a pin
    fresh = robotics.compose_robotics_research(
        dataclasses.replace(query, expected_generation=None), bundle)
    assert fresh["request"]["expected_generation"] is None
    assert fresh["generation"] == response["generation"]


def test_replay_without_cutoffs_refuses():
    query, bundle = load_bundle_case("later_retained_backdate")
    assert query.time_mode == "system_replay"
    with pytest.raises(robotics.ResearchRefusal) as exc:
        robotics.compose_robotics_research(query, bundle)
    assert exc.value.code == "replay_cutoffs_required"


# ---------------------------------------------------------------------------
# Pagination slices rows, never the population
# ---------------------------------------------------------------------------

def test_pagination_slices_companies_and_view_rows():
    response, query, bundle = compose("hds_operating_snapshot", view="capacity")
    generation = response["generation"]
    full_rows = response["industrial_views"]["capacity"]["rows"]
    assert len(full_rows) == 36
    page = robotics.compose_robotics_research(
        dataclasses.replace(query, view="capacity", offset=30, limit=10,
                            expected_generation=generation), bundle)
    assert len(page["industrial_views"]["capacity"]["rows"]) == 6
    tail = [r["curation_revision"] for r in full_rows[30:]]
    assert [r["curation_revision"] for r
            in page["industrial_views"]["capacity"]["rows"]] == tail
    assert page["authorized_coverage"]["selected"] == 36
    assert len(page["evidence_refs"]) == 36
    beyond = robotics.compose_robotics_research(
        dataclasses.replace(query, view="capacity", offset=50, limit=10,
                            expected_generation=generation), bundle)
    assert beyond["industrial_views"]["capacity"]["rows"] == []


# ---------------------------------------------------------------------------
# Out-of-scope invariance (fingerprint and body)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(condition=not HAS_CODEC, strict=True, reason=CODEC_REASON)
def test_out_of_scope_assertion_never_perturbs_the_response():
    query, bundle = load_bundle_case("witness_perception_orbbec_twinny")
    base = robotics.compose_robotics_research(query, bundle)
    case = load_case("witness_perception_orbbec_twinny")
    other_theme = restamp(case["bundle"]["assertions"][0],
                          scope={**case["bundle"]["assertions"][0]["scope"],
                                 "canonical_theme_id": "semiconductors",
                                 "technology_facet": "advanced_packaging"})
    grown = dataclasses.replace(bundle, assertions=bundle.assertions + (other_theme,))
    assert len(grown.assertions) == 2
    response = robotics.compose_robotics_research(query, grown)
    assert response["generation"] == base["generation"]
    assert response == base, "an out-of-scope assertion is invisible everywhere"


def restamp(payload: dict, **changes) -> dict:
    mutant = copy.deepcopy(dict(payload))
    mutant.update(changes)
    mutant["curation_revision"] = None
    return json.loads(encode_assertion(mutant))


# ---------------------------------------------------------------------------
# Authorized evidence selection
# ---------------------------------------------------------------------------

def test_select_authorized_evidence_happy_path():
    query, bundle = load_bundle_case("witness_perception_orbbec_twinny")
    case = load_case("witness_perception_orbbec_twinny")
    assertion = case["bundle"]["assertions"][0]
    ref = f"gmi-curation://robotics_automation/{assertion['curation_revision']}"
    evidence = robotics.select_authorized_evidence(query, bundle, ref)
    assert evidence["schema"] == robotics.EVIDENCE_SCHEMA_ID
    assert evidence["assertion_ref"] == ref
    assert evidence["assertion"] == copy.deepcopy(assertion)
    assert evidence["assertion"] is not assertion, "the payload is deep-copied"
    assert evidence["source"] == {
        "publisher": "Orbbec",
        "source_uri": assertion["source"]["source_uri"],
        "locator": "case-study body, camera configuration paragraph",
        "published_at": None,
        "published_at_grain": "unknown",
        "observed_at": "2026-09-23T06:00:00Z",
        "retained_at": "2026-09-23T06:05:00Z",
    }
    assert "available_at" not in evidence["source"]
    assert evidence["authority"] == robotics.AUTHORITY


def test_select_authorized_evidence_correction_lineage():
    query, bundle = load_bundle_case("corrected_same_url")
    case = load_case("corrected_same_url")
    successor = next(a for a in case["bundle"]["assertions"]
                     if a["correction"]["predecessor_revision"])
    predecessor = next(a for a in case["bundle"]["assertions"]
                       if not a["correction"]["predecessor_revision"])
    succ_ref = f"gmi-curation://robotics_automation/{successor['curation_revision']}"
    pred_ref = f"gmi-curation://robotics_automation/{predecessor['curation_revision']}"
    succ = robotics.select_authorized_evidence(query, bundle, succ_ref)
    assert succ["lineage"] == [pred_ref]
    pred = robotics.select_authorized_evidence(query, bundle, pred_ref)
    assert pred["lineage"] == []


def test_select_authorized_evidence_unknown_and_out_of_scope_share_one_code():
    query, bundle = load_bundle_case("witness_perception_orbbec_twinny")
    unknown = "gmi-curation://robotics_automation/gmirca_" + "f" * 32
    with pytest.raises(robotics.ResearchRefusal) as exc:
        robotics.select_authorized_evidence(query, bundle, unknown)
    assert exc.value.code == "not_available"
    if HAS_CODEC:
        case = load_case("witness_perception_orbbec_twinny")
        out = restamp(case["bundle"]["assertions"][0],
                      scope={**case["bundle"]["assertions"][0]["scope"],
                             "canonical_theme_id": "factory_automation"})
        grown = dataclasses.replace(bundle,
                                    assertions=bundle.assertions + (out,))
        with pytest.raises(robotics.ResearchRefusal) as exc:
            robotics.select_authorized_evidence(
                query, grown,
                f"gmi-curation://robotics_automation/{out['curation_revision']}")
        assert exc.value.code == "not_available"


def test_select_authorized_evidence_generation_gate():
    query, bundle = load_bundle_case("witness_perception_orbbec_twinny")
    case = load_case("witness_perception_orbbec_twinny")
    ref = f"gmi-curation://robotics_automation/" \
        f"{case['bundle']['assertions'][0]['curation_revision']}"
    with pytest.raises(robotics.ResearchRefusal) as exc:
        robotics.select_authorized_evidence(
            dataclasses.replace(query, expected_generation="gen_" + "a" * 32),
            bundle, ref)
    assert exc.value.code == "generation_changed"
    evidence = robotics.select_authorized_evidence(
        dataclasses.replace(query, expected_generation=None), bundle, ref)
    assert evidence["schema"] == robotics.EVIDENCE_SCHEMA_ID


def test_held_assertion_is_still_selectable_evidence():
    query, bundle = load_bundle_case("review_expired_or_withdrawn")
    case = load_case("review_expired_or_withdrawn")
    held = next(a for a in case["bundle"]["assertions"]
                if a["review"]["disposition"] == "held")
    evidence = robotics.select_authorized_evidence(
        query, bundle,
        f"gmi-curation://robotics_automation/{held['curation_revision']}")
    assert evidence["assertion"]["review"]["disposition"] == "held"
    assert "held_present" in evidence["limitations"]


# ---------------------------------------------------------------------------
# Module purity
# ---------------------------------------------------------------------------

def test_module_imports_nothing_impure():
    source = Path(robotics.__file__).read_text(encoding="utf-8")
    imports = re.findall(
        r"^\s*(?:import|from)\s+([A-Za-z_][\w.]*)", source, re.MULTILINE)
    for target in imports:
        root = target.split(".")[0]
        assert root not in {"pandas", "requests", "app", "brain"}, target
    assert "engine.neuralweb" not in source


def test_module_source_has_no_io_or_subprocess_surface():
    source = Path(robotics.__file__).read_text(encoding="utf-8")
    for token in ("urlopen", "socket", "subprocess", "os.system", "shutil"):
        assert token not in source, token
