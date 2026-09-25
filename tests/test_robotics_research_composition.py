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

try:  # the assertion-side theme id is minted by the identity owner
    from engine.theme_graph.identity import theme_node_id as _theme_node_id
    REF_PREFIX = f"gmi-curation://{_theme_node_id('robotics_automation')}/"
except ImportError:  # pragma: no cover - base without the identity owner
    REF_PREFIX = "gmi-curation://theme:robotics_automation/"

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
    _, _, bundle = compose("witness_perception_orbbec_twinny")
    expected = [{"owner_store": r["owner_store"],
                 "native_identity": r["native_identity"],
                 "reference_id": r["reference_id"], "kind": "native"}
                for r in bundle.native_refs]
    assert natives == expected
    assert all(e["reference_id"].startswith(REF_PREFIX) for e in natives)


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
    # the stored replay query carries both cutoffs and composes as-is (R2b N12)
    robotics.compose_robotics_research(query, bundle)
    for missing in ("source_cutoff", "recorded_cutoff"):
        with pytest.raises(robotics.ResearchRefusal) as exc:
            robotics.compose_robotics_research(
                dataclasses.replace(query, **{missing: None}), bundle)
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
    ref = f"{REF_PREFIX}{assertion['curation_revision']}"
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
    succ_ref = f"{REF_PREFIX}{successor['curation_revision']}"
    pred_ref = f"{REF_PREFIX}{predecessor['curation_revision']}"
    succ = robotics.select_authorized_evidence(query, bundle, succ_ref)
    assert succ["lineage"] == [pred_ref]
    pred = robotics.select_authorized_evidence(query, bundle, pred_ref)
    assert pred["lineage"] == []


def test_select_authorized_evidence_unknown_and_out_of_scope_share_one_code():
    query, bundle = load_bundle_case("witness_perception_orbbec_twinny")
    unknown = REF_PREFIX + "gmirca_" + "f" * 32
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
                f"{REF_PREFIX}{out['curation_revision']}")
        assert exc.value.code == "not_available"


def test_select_authorized_evidence_generation_gate():
    query, bundle = load_bundle_case("witness_perception_orbbec_twinny")
    case = load_case("witness_perception_orbbec_twinny")
    ref = f"{REF_PREFIX}" \
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
        f"{REF_PREFIX}{held['curation_revision']}")
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


# ---------------------------------------------------------------------------
# R2b — canonical theme ids, closed reasons, declared cohort, ownership side
# (shared-owner ruling #7870 5812295091; Sol #7780 5813801605; R2 review nits)
# ---------------------------------------------------------------------------

_ROOT = Path(robotics.__file__).resolve().parents[2] if robotics is not None else Path(__file__).resolve().parents[1]
_READY = sorted(p.stem for p in FIXTURE_ROOT.glob("*.json")
                if json.loads(p.read_text())["status"] == "ready")


def _restamped(assertion, **changes):
    """Deep-copy an assertion, apply nested changes, re-mint its stamp."""
    from engine.theme_graph.curation_assertion import curation_revision
    out = copy.deepcopy(assertion)
    for path, value in changes.items():
        node = out
        keys = path.split(".")
        for key in keys[:-1]:
            node = node[key]
        node[keys[-1]] = value
    out["curation_revision"] = curation_revision(out)
    return out


def _walk_strings(value, under_limitations=False):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _walk_strings(item, under_limitations=(key == "limitations"))
    elif isinstance(value, list):
        for item in value:
            yield from _walk_strings(item, under_limitations=under_limitations)
    elif isinstance(value, str):
        yield value, under_limitations


def test_slug_keyed_assertion_is_out_of_scope_and_counted():
    query, bundle = load_bundle_case("zebra_skild_ownership")
    keep, drop = bundle.assertions
    slug = _restamped(drop, **{"scope.canonical_theme_id": query.anchor_theme_id})
    mixed = dataclasses.replace(bundle, assertions=(keep, slug))
    response = robotics.compose_robotics_research(
        dataclasses.replace(query, view="commercial"), mixed)
    refs = {e["assertion_ref"] for e in response["evidence_refs"]
            if e["kind"] == "assertion"}
    assert REF_PREFIX + keep["curation_revision"] in refs
    assert all(slug["curation_revision"] not in ref for ref in refs)
    for view in robotics.VIEWS:
        for row in response["industrial_views"][view]["rows"]:
            assert row["curation_revision"] != slug["curation_revision"]
    assert "scope_slug_keyed:1" in response["limitations"]
    with pytest.raises(robotics.ResearchRefusal) as exc:
        robotics.select_authorized_evidence(
            dataclasses.replace(query, view="commercial"), mixed,
            f"gmi-curation://{query.anchor_theme_id}/{slug['curation_revision']}")
    assert exc.value.code == "not_available"
    _RESPONSE_SCHEMA.validate(response)


def test_identity_owner_fallback_is_declared_and_otherwise_identical(monkeypatch):
    import sys
    response, query, bundle = compose("witness_perception_orbbec_twinny")
    monkeypatch.setitem(sys.modules, "engine.theme_graph.identity", None)
    fallback = robotics.compose_robotics_research(query, bundle)
    assert "identity_owner_fallback" in fallback["limitations"]
    assert "identity_owner_fallback" not in response["limitations"]
    trimmed = dict(fallback)
    trimmed["limitations"] = [x for x in fallback["limitations"]
                              if x != "identity_owner_fallback"]
    assert trimmed == response


def test_canonical_form_is_refused_at_the_api_boundary():
    query, bundle = load_bundle_case("witness_perception_orbbec_twinny")
    with pytest.raises(robotics.ResearchRefusal) as exc:
        robotics.compose_robotics_research(
            dataclasses.replace(query, anchor_theme_id=REF_PREFIX.split("//")[1].rstrip("/")),
            bundle)
    assert exc.value.code == "not_available"


def test_every_reason_is_closed_grammar_and_no_per_view_evidence_reason():
    pattern = re.compile(r"^[a-z0-9_]+$")
    banned = re.compile(r"^no_(composition|commercial|capacity|economics)_evidence$")
    for name in _READY:
        query, bundle = load_bundle_case(name)
        for view in robotics.VIEWS:
            response = robotics.compose_robotics_research(
                dataclasses.replace(query, view=view), bundle)
            for reason in _reasons(response):
                assert reason is None or pattern.match(reason), reason
                assert reason is None or not banned.match(reason), reason


def _reasons(value):
    """Section-level ``reason`` values only (a dict carrying ``status`` or a
    ``total`` cell) — never the free prose of an assertion's ``correction``."""
    if isinstance(value, dict):
        if "reason" in value and ("status" in value or set(value) == {"value", "reason"}):
            yield value["reason"]
        for key, item in value.items():
            if key != "reason":
                yield from _reasons(item)
    elif isinstance(value, list):
        for item in value:
            yield from _reasons(item)


def test_schema_reason_pattern_matches_the_shared_envelope():
    ours = json.loads((_ROOT / "contracts/market_ontology/robotics_theme_research.v1.schema.json").read_text())
    shared = json.loads((_ROOT / "contracts/market_ontology/semiconductor_theme_research.v1.schema.json").read_text())
    assert ours["$defs"]["reason"] == shared["$defs"]["reason"]


def test_module_source_reads_no_wall_clock():
    source = Path(robotics.__file__).read_text(encoding="utf-8")
    for token in ("datetime.now", "utcnow", "time.time", "date.today",
                  "perf_counter", "monotonic"):
        assert token not in source, token


def test_falsifiers_are_labelled_interpretation_not_target():
    for name in _READY:
        query, bundle = load_bundle_case(name)
        response = robotics.compose_robotics_research(query, bundle)
        watchers = {b.get("falsifier") for b in bundle.interpretation_blocks} | {
            b.get("missing_measurement") for b in bundle.interpretation_blocks}
        by_revision = {a["curation_revision"]: a for a in bundle.assertions}
        for item in response["summary"]["next_evidence"]:
            if item["text"] in watchers:
                assert item["label"] == "interpretation", (name, item)
            if item["label"] == "target":
                assert len(item["input_refs"]) == 1
                source = by_revision[item["input_refs"][0]]
                assert source["statement_mode"] in ("FORWARD_TARGET", "ANNOUNCED_ARRANGEMENT") \
                    or source["predicate"] == "DEPLOYMENT_TARGET", (name, item)


def test_declared_cohort_limitation_on_every_response_and_evidence():
    for name in _READY:
        query, bundle = load_bundle_case(name)
        for view in robotics.VIEWS:
            response = robotics.compose_robotics_research(
                dataclasses.replace(query, view=view), bundle)
            assert "slice_scope_unowned" in response["limitations"], (name, view)
            # the string is a limitation token only, never a visible label
            for text, under_limitations in _walk_strings(response):
                if "slice_scope_unowned" in text:
                    assert under_limitations and text == "slice_scope_unowned", (name, view, text)
            # evidence follows the same cohort as composition: the evidence
            # refs ARE the authorized selection, and every returned row
            # comes from that same selection
            row_refs = {row["assertion_ref"]
                        for row in response["industrial_views"][view]["rows"]}
            evidence = {e["assertion_ref"] for e in response["evidence_refs"]
                        if e["kind"] == "assertion"}
            assert {ref.rsplit("/", 1)[1] for ref in evidence} == set(
                response["authorized_coverage"]["input_refs"]), (name, view)
            assert row_refs <= evidence, (name, view)
            for ref in evidence:
                assert "slice_scope_unowned" in robotics.select_authorized_evidence(
                    dataclasses.replace(query, view=view), bundle, ref)["limitations"]


def _served_role(case, **changes):
    """Role served for the ANNOUNCED_ARRANGEMENT ownership assertion of ``case``
    after applying ``changes`` (nested dotted paths) and re-minting its stamp."""
    query, bundle = load_bundle_case(case)
    announced = next(a for a in bundle.assertions
                     if a["statement_mode"] == "ANNOUNCED_ARRANGEMENT")
    other = tuple(a for a in bundle.assertions if a is not announced)
    mutated = _restamped(announced, **changes) if changes else announced
    response = robotics.compose_robotics_research(
        dataclasses.replace(query, view="commercial"),
        dataclasses.replace(bundle, assertions=other + (mutated,)))
    row = next(r for r in response["companies"]["rows"]
               if r["source_business_label"] == mutated["subject"]["source_business_label"])
    ref = REF_PREFIX + mutated["curation_revision"]
    return next(r["role"] for r in row["roles"] if r["assertion_ref"] == ref)


def _zebra_role(**changes):
    return _served_role("zebra_skild_ownership", **changes)


def _ptc_role(sentence):
    return _served_role("ptc_tpg_ownership", **{"limitations.establishes": [sentence]})


def _role_for(label, sentence):
    return _zebra_role(**{"subject.source_business_label": label,
                          "limitations.establishes": [sentence]})


def test_ownership_side_is_structurally_unavailable_in_v1():
    """The ruling: every ANNOUNCED_ARRANGEMENT serves ``announced_party``.

    Eleven independent READ_ONLY reviews rejected eleven readings of this field.
    The last one falsified the premise of the one before it: agency attaches a
    second party with no preposition, no conjunction and no punctuation at all
    (a transitive participle, "Skild AI Representing Fanuc"; the English
    genitive, "Fanuc's Nominee Skild AI"), so the closed GRAMMATICAL class that
    was meant to replace the open SEMANTIC one is not closed either. There is no
    parse left to invert: neither the curated label nor the prose is read.
    """
    # both real corpus assertions - the entire ownership surface - go neutral
    assert _zebra_role() == "announced_party"
    assert _ptc_role("an announced change of the ThingWorx and Kepware businesses to TPG") \
        == "announced_party"
    # the cleanest possible curated direction still serves no side
    assert _zebra_role(**{
        "object.source_product_label": "Robotics Automation business (sale to Skild AI)",
        "limitations.establishes":
            ["an announced sale of the Robotics Automation business to Skild AI"],
    }) == "announced_party"
    # and neither does the opposite preposition, which used to mean "acquirer"
    assert _zebra_role(**{
        "object.source_product_label": "perception assets (acquisition from Skild AI)",
        "limitations.establishes":
            ["an announced acquisition of the perception assets from Skild AI"],
    }) == "announced_party"
    # a subject label cannot reach it either
    assert _role_for("Universal Robots Holdings",
                     "an announced sale of the Universal Robots to Skild AI") \
        == "announced_party"


def test_reported_fact_ownership_still_carries_its_effective_date():
    """The half of ``_ownership_role`` the ruling does NOT retire.

    Retiring the announced side removed 206 lines; this pins that the
    REPORTED_FACT branch is untouched, since nothing else in either suite did.
    """
    assert _zebra_role(**{"statement_mode": "REPORTED_FACT",
                          "temporal.business_valid_from": "2026-03-01"}) \
        == "owner_from:2026-03-01"
    # a reported fact with no effective date is named as such, not guessed
    assert _zebra_role(**{"statement_mode": "REPORTED_FACT",
                          "temporal.business_valid_from": None}) \
        == "owner_reported_effective_date_unknown"


def test_no_curated_label_or_prose_can_produce_an_ownership_side():
    """The eleven rounds' inversion corpus, preserved and re-pinned to neutral.

    Every entry below served a WRONG side in some earlier round - each was found
    by an independent reviewer, and each is the reason a parse was retired. They
    are kept because they are the evidence: if a future change restores a parse,
    these are the shapes it has to survive. Grouped by the round that found them.
    """
    B = "Robotics Automation business"
    INVERSIONS = (
        # rounds 2-6: prose agency, which retired the subject-naming templates
        ("r2-6", "(sale to Skild AI)", "an announced sale of the %s for a client to Skild AI" % B),
        ("r2-6", "(sale to Skild AI)", "an announced sale of the %s by Fanuc to Skild AI" % B),
        # round 8: a greedy preposition scan with no head-noun check
        ("r8", "(licensed to Skild AI)", "an announced transfer of the %s to Skild AI" % B),
        ("r8", "(change of name to Skild Robotics)",
         "an announced change of the %s to Skild Robotics" % B),
        ("r8", "(divestiture to Skild AI, carved out from Fanuc)",
         "an announced acquisition of the %s from Fanuc" % B),
        # round 9: agency inside the curated counterparty
        ("r9", "(acquisition from Fanuc by Skild AI)",
         "an announced acquisition of the %s from Fanuc by Skild AI" % B),
        ("r9", "(sale to Skild AI on behalf of Fanuc)",
         "an announced sale of the %s to Skild AI on behalf of Fanuc" % B),
        ("r9", "(sale to Skild AI, mandated by Fanuc)",
         "an announced sale of the %s to Skild AI, mandated by Fanuc" % B),
        ("r9", "(sale to a vehicle managed by Fanuc)",
         "an announced sale of the %s to a vehicle managed by Fanuc" % B),
        ("r9", "(sale to Skild AI) (transfer from Fanuc)",
         "an announced acquisition of the %s (sale to Skild AI) from Fanuc" % B),
        # round 10: a shape rule degenerating on TITLE-case input, and a comma
        ("r10", "(Sale To Skild AI As Agent Of Fanuc)",
         "an announced sale of the %s to Skild AI As Agent Of Fanuc" % B),
        ("r10", "(Acquisition From Fanuc, Buyer Skild AI)",
         "an announced acquisition of the %s from Fanuc, Buyer Skild AI" % B),
        ("r10", "(sale to Skild AI, Seller Fanuc)",
         "an announced sale of the %s to Skild AI, Seller Fanuc" % B),
        # round 10 blocker 1: capitalisation mistaken for agency
        ("r10", "(sale to Skild AI)",
         "an announced sale of the Robotics business for A Client to Skild AI"),
        # round 11 B1: prepositions missing from a hand-written "closed" class
        ("r11-B1", "(sale to Skild AI Qua Fanuc)",
         "an announced sale of the %s to Skild AI Qua Fanuc" % B),
        ("r11-B1", "(sale to Skild AI Sans Fanuc)",
         "an announced sale of the %s to Skild AI Sans Fanuc" % B),
        ("r11-B1", "(sale to Skild AI Notwithstanding Fanuc)",
         "an announced sale of the %s to Skild AI Notwithstanding Fanuc" % B),
        # round 11 B2: agency with NO connective - the falsifying finding
        ("r11-B2", "(sale to Skild AI Representing Fanuc)",
         "an announced sale of the %s to Skild AI Representing Fanuc" % B),
        ("r11-B2", "(sale to Skild AI Acting Fanuc)",
         "an announced sale of the %s to Skild AI Acting Fanuc" % B),
        ("r11-B2", "(sale to Fanuc's Nominee Skild AI)",
         "an announced sale of the %s to Fanuc's Nominee Skild AI" % B),
        ("r11-B2", "(sale to Skild AI Fanuc's Nominee)",
         "an announced sale of the %s to Skild AI Fanuc's Nominee" % B),
        # round 11 B3: apposition without the comma
        ("r11-B3", "(Acquisition From Fanuc Buyer Skild AI)",
         "an announced acquisition of the %s from Fanuc Buyer Skild AI" % B),
        ("r11-B3", "(sale to Skild AI Seller Fanuc)",
         "an announced sale of the %s to Skild AI Seller Fanuc" % B),
        ("r11-B3", "(sale to Skild AI Trustee Fanuc)",
         "an announced sale of the %s to Skild AI Trustee Fanuc" % B),
        # round 11 B4: separators inside the name-token class fusing refused words
        ("r11-B4", "(Sale To Skild AI-As-Agent-Of Fanuc)",
         "an announced sale of the %s to Skild AI-As-Agent-Of Fanuc" % B),
        ("r11-B4", "(sale to Skild AI/by Fanuc)",
         "an announced sale of the %s to Skild AI/by Fanuc" % B),
        ("r11-B4", "(Acquisition From Fanuc-Buyer Skild AI)",
         "an announced acquisition of the %s from Fanuc-Buyer Skild AI" % B),
        # round 11 B5: a word silently dropped from the refused vocabulary
        ("r11-B5", "(sale to Skild AI Behalf Fanuc)",
         "an announced sale of the %s to Skild AI Behalf Fanuc" % B),
    )
    for round_found, parenthetical, sentence in INVERSIONS:
        label = B + " " + parenthetical
        assert _zebra_role(**{"object.source_product_label": label,
                              "limitations.establishes": [sentence]}) == "announced_party", (
            "%s: %s" % (round_found, label))

    # and exhaustively: no combination of head noun, preposition and counterparty
    # produces anything but the neutral. A parse would show up here as a second
    # distinct role.
    import itertools
    heads = ("sale", "divestiture", "transfer", "acquisition", "purchase",
             "ownership change", "change of control", "licensed", "change of name")
    preps = ("to", "from", "by", "for", "with", "qua", "'s")
    parties = ("Skild AI", "TPG", "Fanuc Buyer Skild AI", "Skild AI Representing Fanuc",
               "Fanuc's Nominee Skild AI", "Skild AI-As-Agent-Of Fanuc", "Skild AI, Inc.")
    roles = set()
    for head, prep, party in itertools.product(heads, preps, parties):
        label = "%s (%s %s %s)" % (B, head, prep, party)
        for sentence in ("an announced %s of the %s %s %s" % (head, B, prep, party),
                         "an announced %s %s %s of the %s" % (head, prep, party, B)):
            roles.add(_zebra_role(**{"object.source_product_label": label,
                                     "limitations.establishes": [sentence]}))
    assert roles == {"announced_party"}, sorted(roles)


def test_view_reasons_are_the_shared_closed_set_and_never_contradict_the_selection():
    allowed = {"no_selected_assertions", "no_rows_for_view", "no_manufacturing_evidence"}
    seen = set()
    for name in _READY:
        query, bundle = load_bundle_case(name)
        for view in robotics.VIEWS:
            response = robotics.compose_robotics_research(
                dataclasses.replace(query, view=view), bundle)
            selected = response["authorized_coverage"]["selected"]
            section = response["industrial_views"][view]
            if section["rows"]:
                assert "reason" not in section
                continue
            reason = section["reason"]
            seen.add(reason)
            assert reason in allowed, (name, view, reason)
            # ``no_selected_assertions`` is only true when nothing was
            # selected; a selection with no row for the view says so
            assert (reason == "no_selected_assertions") == (selected == 0), (name, view)
            if view == "manufacturing" and selected:
                assert reason == "no_manufacturing_evidence"
    assert {"no_rows_for_view", "no_manufacturing_evidence"} <= seen


def test_slug_keyed_count_follows_the_slice_gate():
    query, bundle = load_bundle_case("zebra_skild_ownership")
    keep, drop = bundle.assertions
    other_slice = next(s for s in robotics.SLICES if s != query.slice_key)
    slug_elsewhere = _restamped(drop, **{"scope.canonical_theme_id": query.anchor_theme_id,
                                         "scope.technology_facet": other_slice})
    response = robotics.compose_robotics_research(
        dataclasses.replace(query, view="commercial"),
        dataclasses.replace(bundle, assertions=(keep, slug_elsewhere)))
    assert not any(l.startswith("scope_slug_keyed") for l in response["limitations"])
    assert "slice_scope_unowned" in response["limitations"]
