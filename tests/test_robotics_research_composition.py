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


def test_ownership_side_comes_from_the_curated_object_label_only():
    # The direction is read from the parenthetical of the assertion's own
    # curated ``object.source_product_label`` — a curation decision, never an
    # inference over prose. ``limitations.establishes`` is a GUARD on that
    # direction, never its source.
    assert _zebra_role() == "announced_seller"
    # a denial never affirms and never flips
    base = load_bundle_case("zebra_skild_ownership")[1]
    announced = next(a for a in base.assertions
                     if a["statement_mode"] == "ANNOUNCED_ARRANGEMENT")
    denial = list(announced["limitations"]["does_not_establish"]) + [
        "that Zebra acquired the Skild AI equity stake"]
    assert _zebra_role(**{"limitations.does_not_establish": denial}) == "announced_seller"
    # the counterparty's verb in the coverage prose never flips the side
    assert _zebra_role(**{"limitations.coverage":
                          "issuer press release announcing a sale to Skild AI, "
                          "whose acquisition closes later"}) == "announced_seller"
    # a label carrying NO curated direction serves no side, however clean the prose
    assert _zebra_role(**{"object.source_product_label": "Robotics Automation business"}) \
        == "announced_party"
    # the label's own preposition decides which side: "to" = seller, "from" = acquirer
    assert _zebra_role(**{"object.source_product_label":
                          "Twinny perception unit (acquisition from Orbbec)",
                          "limitations.establishes":
                          ["an announced acquisition of the Twinny perception unit from Orbbec"]}) \
        == "announced_acquirer"
    # prose that contradicts the label borrows nothing from it
    assert _zebra_role(**{"limitations.establishes":
                          ["an announced acquisition of the Twinny perception unit from Orbbec"]}) \
        == "announced_party"
    # both directions stated at once = ambiguous, never guessed
    assert _zebra_role(**{"limitations.establishes":
                          ["an announced sale of the Robotics Automation business to Skild AI",
                           "an announced acquisition of the Robotics Automation business "
                           "from Skild AI"]}) == "announced_party"
    # non-ownership prose under a directional label serves nothing
    assert _zebra_role(**{"limitations.establishes":
                          ["a catalog capability listing for strain-wave gearing"]}) \
        == "announced_party"


def test_ownership_direction_comes_only_from_a_closed_curated_parenthetical():
    # Review 8 blocker 1: the direction slot is a CLOSED grammar, not a search
    # for any "to"/"from" in the label. Each label below once supplied a
    # direction through a greedy scan with no head-noun check, and served a side
    # against what the label actually says; all of them must now refuse. The
    # prose is the one that would match if a direction were extracted, so these
    # pin the served role, not just the parse.
    for label, sentence in (
        # a second relation in the same parenthetical records no single direction
        ("Robotics Automation business (divestiture to Skild AI, carved out from Fanuc)",
         "an announced acquisition of the Robotics Automation business from Fanuc"),
        ("Robotics Automation business (acquisition from Fanuc, later resold to Skild AI)",
         "an announced sale of the Robotics Automation business to Skild AI"),
        # the head noun is not an ownership transfer at all
        ("Robotics Automation business (change of name to Skild Robotics)",
         "an announced change of the Robotics Automation business to Skild Robotics"),
        ("Robotics Automation business (licensed to Skild AI)",
         "an announced transfer of the Robotics Automation business to Skild AI"),
        ("Robotics Automation business (formerly known as Robotics to Go)",
         "an announced sale of the Robotics Automation business to Go"),
        # the parenthetical is not the label's trailing slot
        ("Robotics Automation business (sale to Skild AI) pending approval",
         "an announced sale of the Robotics Automation business to Skild AI"),
        # a curated product NAME embedding an agent phrase is a curation defect,
        # refused rather than served (review 8 nit 2)
        ("Robotics Automation business by Fanuc (sale to Skild AI)",
         "an announced sale of the Robotics Automation business by Fanuc to Skild AI"),
        ("Robotics Automation business for a client (sale to Skild AI)",
         "an announced sale of the Robotics Automation business for a client to Skild AI"),
        # a label that is only the parenthetical names no product
        ("(sale to Skild AI)", "an announced sale of the  to Skild AI"),
        # review 9 blocker 2: two relations split across TWO parentheticals.
        # Whatever the slot refuses inside one parenthetical it must refuse
        # across two - the trailing slot must never serve the label's SECOND
        # relation against its first, in either order.
        ("Robotics Automation business (sale to Skild AI) (transfer from Fanuc)",
         "an announced acquisition of the Robotics Automation business "
         "(sale to Skild AI) from Fanuc"),
        ("Robotics Automation business (sale to Skild AI) (acquisition from Fanuc)",
         "an announced acquisition of the Robotics Automation business "
         "(sale to Skild AI) from Fanuc"),
        ("Robotics Automation business (transfer from Fanuc) (sale to Skild AI)",
         "an announced sale of the Robotics Automation business "
         "(transfer from Fanuc) to Skild AI"),
        # review 9 nit 3: the status word needs a space after it, so a fused
        # "announcedsale" is not an ownership head
        ("Robotics Automation business (announcedsale to Skild AI)",
         "an announced sale of the Robotics Automation business to Skild AI"),
    ):
        assert _zebra_role(**{"object.source_product_label": label,
                              "limitations.establishes": [sentence]}) == "announced_party", label
    # the shapes the curated corpus does use, including a status word, a
    # product that itself contains parentheses, and a capitalised slot
    for label, sentence, role in (
        ("Robotics Automation business (sale to Skild AI)",
         "an announced sale of the Robotics Automation business to Skild AI", "announced_seller"),
        ("Robotics Automation business (completed sale to Skild AI)",
         "an announced sale of the Robotics Automation business to Skild AI", "announced_seller"),
        ("Robotics Automation business (Sale To Skild AI)",
         "an announced sale of the Robotics Automation business to Skild AI", "announced_seller"),
        ("Robotics (EMEA) business (sale to Skild AI)",
         "an announced sale of the Robotics (EMEA) business to Skild AI", "announced_seller"),
        ("perception assets (acquisition from Skild AI)",
         "an announced acquisition of the perception assets from Skild AI", "announced_acquirer"),
        # review 9 nit 1: in a curated product name "for" marks a market
        # segment, and refusing every "for" was the largest measured source of
        # silent over-refusal. A capitalised segment is admitted; "for a client"
        # above stays refused, because that one really is an agency phrase. An
        # ownership head noun inside the product name is likewise not a relation.
        ("Kepware for Industry 4.0 (sale to Skild AI)",
         "an announced sale of the Kepware for Industry 4.0 to Skild AI", "announced_seller"),
        ("Machine Vision for Logistics unit (sale to Skild AI)",
         "an announced sale of the Machine Vision for Logistics unit to Skild AI",
         "announced_seller"),
        ("Point of sale systems (sale to Skild AI)",
         "an announced sale of the Point of sale systems to Skild AI", "announced_seller"),
        ("By-products recycling line (sale to Skild AI)",
         "an announced sale of the By-products recycling line to Skild AI", "announced_seller"),
    ):
        assert _zebra_role(**{"object.source_product_label": label,
                              "limitations.establishes": [sentence]}) == role, label


def test_ownership_side_is_withheld_when_the_curated_counterparty_is_not_a_bare_name():
    # Review 9 blocker 1: fix8 closed the direction slot's FRAME (trailing
    # parenthetical, one head noun, the preposition) but left its counterparty
    # as free text behind a two-word blocklist - and it inverted exactly the way
    # the retired prose blocklists had, with agency phrases. Each label below
    # served a side while naming a DIFFERENT party as the real principal. The
    # counterparty is now an allowlist: a NAME and nothing else.
    for label, sentence in (
        ("Robotics Automation business (acquisition from Fanuc by Skild AI)",
         "an announced acquisition of the Robotics Automation business from Fanuc by Skild AI"),
        ("Robotics Automation business (sale to Skild AI on behalf of Fanuc)",
         "an announced sale of the Robotics Automation business to Skild AI on behalf of Fanuc"),
        ("Robotics Automation business (sale to Skild AI, mandated by Fanuc)",
         "an announced sale of the Robotics Automation business to Skild AI, mandated by Fanuc"),
        ("Robotics Automation business (sale to Skild AI by Fanuc)",
         "an announced sale of the Robotics Automation business to Skild AI by Fanuc"),
        ("Robotics Automation business (purchase from Fanuc by Skild AI)",
         "an announced purchase of the Robotics Automation business from Fanuc by Skild AI"),
        # a counterparty that is a description rather than a name, and one that
        # names two parties, each record no single counterparty
        ("Robotics Automation business (sale to a vehicle managed by Fanuc)",
         "an announced sale of the Robotics Automation business to a vehicle managed by Fanuc"),
        ("Robotics Automation business (sale to Skild AI and Fanuc)",
         "an announced sale of the Robotics Automation business to Skild AI and Fanuc"),
    ):
        assert _zebra_role(**{"object.source_product_label": label,
                              "limitations.establishes": [sentence]}) == "announced_party", label
    # a real name still anchors, including one with a name-internal connector
    for party in ("Skild AI", "TPG", "Bank of America", "3M Robotics", "Kollmorgen Holdings"):
        assert _zebra_role(**{
            "object.source_product_label":
                "Robotics Automation business (sale to %s)" % party,
            "limitations.establishes":
                ["an announced sale of the Robotics Automation business to %s" % party],
        }) == "announced_seller", party


def test_ownership_side_is_withheld_when_the_curated_counterparty_names_the_subject():
    # Review 9 blocker 3: the subject-named-nowhere guard blanked EVERY
    # occurrence of the curated product name in the sentence, so when the
    # product name was a prefix of the counterparty the strip erased the
    # subject's own mention and the guard went blind - serving a side that
    # named the subject as the opposite party to the label. The guard now
    # blanks only the span the grammar itself matched, and a label naming the
    # subject as its own counterparty records no direction at all.
    for subject, label, sentence in (
        ("Universal Robots Holdings", "Universal Robots (sale to Universal Robots Holdings)",
         "an announced sale of the Universal Robots to Universal Robots Holdings"),
        ("Fanuc Robotics Group", "Fanuc Robotics (acquisition from Fanuc Robotics Group)",
         "an announced acquisition of the Fanuc Robotics from Fanuc Robotics Group"),
    ):
        assert _zebra_role(**{"subject.source_business_label": subject,
                              "object.source_product_label": label,
                              "limitations.establishes": [sentence]}) == "announced_party", label
    # the control the carve-out exists for: the same overlapping product name
    # with a counterparty that does NOT name the subject still anchors
    assert _zebra_role(**{
        "subject.source_business_label": "Universal Robots Holdings",
        "object.source_product_label": "Universal Robots (sale to Skild AI)",
        "limitations.establishes":
            ["an announced sale of the Universal Robots to Skild AI"]}) == "announced_seller"


def test_ownership_side_requires_the_closed_curated_sentence_grammar():
    # The guard sentence must name the curated PRODUCT after one of a few fixed
    # ownership heads, then the curated PREPOSITION and the curated
    # COUNTERPARTY, then nothing but a date. Product and counterparty enter the
    # grammar as escaped curated literals, so no free slot is left for a parser
    # to be wrong about, and the tail is an ALLOWLIST rather than a blocklist.
    anchored = (
        # the two shapes the curated corpus actually uses
        "an announced ownership change transferring the Robotics Automation business to Skild AI",
        "an announced sale of the Robotics Automation business to Skild AI",
        "an announced divestiture of the Robotics Automation business to Skild AI",
        "an announced transfer of the Robotics Automation business to Skild AI",
        "an announced change of control of the Robotics Automation business to Skild AI",
        # the reordered form
        "an announced sale to Skild AI of the Robotics Automation business",
        "an announced transfer to Skild AI of the Robotics Automation business",
        # a date tail, and only a date tail
        "an announced sale of the Robotics Automation business to Skild AI on 15 April 2026",
        "an announced sale of the Robotics Automation business to Skild AI, effective April 2026",
        "an announced sale of the Robotics Automation business to Skild AI dated 2026-04-15",
        "an announced sale of the Robotics Automation business to Skild AI in 2026",
        # quotes, typographic marks, a capitalised article and case are normalised
        "“an announced sale of the Robotics Automation business to Skild AI”",
        "An announced sale of the Robotics Automation business to Skild AI",
        "AN ANNOUNCED SALE OF THE ROBOTICS AUTOMATION BUSINESS TO SKILD AI",
        "an announced sale of the Robotics Automation business to Skild AI.",
    )
    for sentence in anchored:
        assert _zebra_role(**{"limitations.establishes": [sentence]}) == "announced_seller", sentence
    # the conjoined-product fixture shape, on its own curated label
    assert _ptc_role("the announced change of the ThingWorx and Kepware businesses to TPG") \
        == "announced_seller"
    assert _ptc_role("The announced change of the ThingWorx and Kepware businesses to TPG") \
        == "announced_seller"
    # the acquirer direction, both orders
    for sentence in ("an announced acquisition of the Twinny perception unit from Orbbec",
                     "an announced purchase of the Twinny perception unit from Orbbec",
                     "an announced acquisition from Orbbec of the Twinny perception unit"):
        assert _zebra_role(**{"object.source_product_label":
                              "Twinny perception unit (acquisition from Orbbec)",
                              "limitations.establishes": [sentence]}) \
            == "announced_acquirer", sentence
    # everything outside the grammar is neutral: another product, another party,
    # the wrong preposition, an extra clause, a consideration, a missing head,
    # an injected phrase inside the product or before it
    for sentence in (
        "an announced sale of the perception unit to Skild AI",
        "an announced sale of the Robotics Automation business to Fanuc",
        "an announced sale of the Robotics Automation business from Skild AI",
        "an announced sale of the Robotics Automation business to Skild AI for cash",
        "an announced sale of the Robotics Automation business to Skild AI for USD 1.2 billion",
        "an announced sale of the Robotics Automation business to Skild AI for an undisclosed sum",
        "an announced sale of the Robotics Automation business to Skild AI as part of a "
        "restructuring",
        "an announced sale of the Robotics Automation business held for a client to Skild AI",
        "an announced sale of the Robotics Automation business by Fanuc to Skild AI",
        "an announced sale (on behalf of Fanuc) of the Robotics Automation business to Skild AI",
        "a sale of the Robotics Automation business to Skild AI",
        "the Robotics Automation business goes to Skild AI",
        "an announced sale of the Robotics Automation business to Skild AI and Fanuc",
    ):
        assert _zebra_role(**{"limitations.establishes": [sentence]}) == "announced_party", sentence


def test_ownership_side_is_withheld_for_every_reviewed_inversion_family():
    # Every sentence here once made (or would make) an open resolver name the
    # WRONG party as agent; under the closed grammar all of them are neutral.
    neutral = (
        # R2b review 1-2: counterparty as agent, subject in a patient slot,
        # comma-set / parenthesised ``by``, agentless passives, no party at all
        "an announced ownership change in which Skild AI acquires the Robotics Automation "
        "business from Zebra",
        "the announced acquisition of Zebra's Robotics Automation business by Skild AI",
        "the announced acquisition of Zebra's Robotics Automation business",
        "an announced acquisition, by Skild AI, of the Robotics Automation business",
        "an announced acquisition (by Skild AI) of the Robotics Automation business",
        "an announced purchase of Zebra's Robotics Automation business",
        "an announced sale of the Skild AI perception unit to Zebra",
        "an announced sale to Zebra Technologies of the Skild AI perception unit",
        "an announced transfer of the Robotics Automation business from Skild AI to Zebra",
        "an announced ownership change in which Skild AI, a foundation-model developer, "
        "acquires the business",
        "Zebra announced that Skild AI acquires the Robotics Automation business",
        "Skild AI purchases the Robotics Automation business from Zebra",
        "Skild AI buys the Robotics Automation business",
        "Zebra's Robotics Automation business was acquired",
        "Zebra's Robotics Automation business was acquired by Skild AI",
        "the unit was sold",
        "the business is acquired",
        "skild ai acquires the robotics automation business",
        # review 3: the subject inside an aside; a coordinated clause
        "Skild AI, a partner of Zebra Technologies, acquires the Robotics Automation business",
        "Fortive, which owns Zebra Technologies, acquires the Skild AI perception unit",
        "Skild AI announced the transaction and acquired the Robotics Automation business",
        "Skild AI raised capital, and the sale of the Robotics Automation business closed",
        "Zebra Technologies was acquired.",
        "Zebra Technologies is being acquired.",
        # review 4 B1: a trailing attribution / financing / advisory ``by`` clause
        "an announced ownership change in which Skild AI acquires the Robotics Automation "
        "business, as announced by Zebra Technologies",
        "Skild AI acquires the Robotics Automation business, financed by Zebra Technologies",
        "Skild AI acquires the business, a transaction underwritten by Zebra Technologies",
        "the perception unit was acquired, as announced by Zebra Technologies",
        # review 4 B2: an implicit-subject noun with no counterparty slot, or with
        # the real agent named after it
        "the announced acquisition of the Robotics Automation business",
        "an announced acquisition in which Skild AI acquires the Robotics Automation business "
        "from Zebra",
        "an announced acquisition that Skild AI completes in April",
        "an announced acquisition; Skild AI takes the Robotics Automation business",
        "an announced acquisition whose acquirer is Skild AI and whose target is the Robotics "
        "Automation business",
        "an announced acquisition and sale of the Zebra Technologies Robotics Automation "
        "business",
        "the acquisition, which Skild AI announced, of the Robotics Automation business",
        "an announced sale of the unit to the market",
        # review 4 B3: the agent named in a leading appositive or attribution
        "The buyer, Skild AI, acquires the Robotics Automation business",
        "According to Skild AI, the acquisition of the Robotics Automation business closed",
        "Pursuant to the Skild AI agreement, the acquisition of the Robotics Automation "
        "business closed",
        "Skild AI, which, as Zebra Technologies disclosed, acquires the unit, confirmed the "
        "timing",
        # review 4 B4: the subject as the target of a modal / infinitive passive
        "Zebra Technologies has agreed to be acquired",
        "Zebra Technologies will be acquired",
        "Zebra Technologies expects to be acquired",
        "an announced arrangement under which Zebra Technologies will be acquired",
        "Zebra Technologies will be sold",
        # review 4 B5: a longer name that merely starts with the subject's word
        "Zebra Technologies's buyer acquires the remaining stake",
        "Zebra Technologies Robotics Unit acquires the perception business",
        "Zebra Technologies' partner Skild AI acquires the business",
        # review 5 B1: the same family in the passive voice (the mention needs a
        # right boundary: end, comma or a lowercase function word)
        "the remaining stake was acquired by Zebra Technologies's buyer",
        "the perception business was acquired by Zebra Technologies Robotics Unit",
        "the business was acquired by Zebra Technologies' partner Skild AI",
        "the perception unit was acquired by Zebra Technologies\u2019 adviser",
        "the unit was acquired by Zebra Technologies competitor Fanuc",
        "the perception unit was purchased by Zebra Robotics GmbH",
        "the unit was acquired by ZebraCorp",
        # review 5 B2/B3: an implicit noun whose slot holds a date, a place or
        # a second party, or that names no curated counterparty at all
        "the announced acquisition of the Robotics Automation business from Q2 2026",
        "an announced sale of the Robotics Automation business to April 2026 closing",
        "an announced sale of the unit to Delaware",
        "an announced sale of the unit to European regulators",
        "an announced acquisition of the Robotics Automation business from Skild AI to Fanuc",
        "an announced transfer of the unit to Skild AI from Fanuc",
        "an announced sale of the unit to Skild AI benefit",
        # review 5 B4: the subject acting for another principal
        "Zebra Technologies transferred the unit on behalf of Skild AI",
        "Zebra Technologies sells the unit as agent for Skild AI",
        "Zebra Technologies acquires the unit for Skild AI",
        # review 5 nit 3: "change of" something that is not a business
        "an announced change of the distribution agreement to Skild AI",
        "an announced change of the reporting segment to Robotics Automation",
        # review 6 B1: agency (or any dirt) inside the parenthetical after the subject
        "an announced sale by Zebra Technologies (on behalf of its joint venture partner)",
        "Zebra Technologies (on behalf of Skild AI) sells the unit",
        "Zebra Technologies (as agent for Skild AI) acquires the unit",
        "the unit was acquired by Zebra Technologies (on behalf of Skild AI)",
        "the unit was sold by Zebra Technologies (in the name of Skild AI)",
        "Zebra Technologies (which sold the unit to Fanuc) acquires the perception business",
        "Zebra Technologies (the buyer is Skild AI) sells the unit",
        "Zebra Technologies (not the acquirer) sells the unit",
        # review 6 B2: agency with a fiduciary noun, "for <non-consideration>",
        # "as <role> of", "on account of", "under a mandate from", joint agents
        "Zebra Technologies acquires the unit for its client Skild AI",
        "Zebra Technologies acquires the unit for the account of Skild AI",
        "the unit was acquired by Zebra Technologies, agent of Skild AI",
        "Zebra Technologies sells the unit as broker of Skild AI",
        "Zebra Technologies acquires the unit as nominee of Skild AI",
        "the unit was acquired by Zebra Technologies, as trustee of the Skild AI trust",
        "Zebra Technologies sells the unit under a mandate from Skild AI",
        "Zebra Technologies sells the unit at the direction of Skild AI",
        "the unit was acquired by Zebra Technologies or Skild AI",
        "the unit was acquired by Zebra Technologies and Skild AI",
        "an announced change of control by Zebra Technologies",
        # ambiguity inside one sentence: two markers, a second clause with its own
        # ownership verb, negation / substitution
        "an announced sale to X and the acquisition of Y",
        "Zebra Technologies sells the unit to Skild AI and acquires a perception unit",
        "Zebra Technologies sells the unit to Skild AI and Fanuc acquires the remainder",
        "Zebra Technologies sells the unit and is acquired by Skild AI",
        "Zebra Technologies acquires the unit that Skild AI sells",
        "Zebra Technologies rather than Skild AI acquires the business",
        "Skild AI acquires the business on behalf of Zebra Technologies",
        "Zebra Technologies acquires Zebra Technologies",
    )
    for sentence in neutral:
        assert _zebra_role(**{"limitations.establishes": [sentence]}) == "announced_party", sentence
    # review 4 B5 with other labels
    assert _role_for("Smith & Nephew Robotics",
                     "Smith Micro Software acquires the perception unit") == "announced_party"
    assert _role_for("Fortive",
                     "Fortive Industrial Technologies acquires the Skild AI perception unit") \
        == "announced_party"
    assert _ptc_role("the announced acquisition of the ThingWorx and Kepware businesses") \
        == "announced_party"
    assert _role_for("TPG", "the announced change of the ThingWorx and Kepware businesses to TPG") \
        == "announced_party"
    assert _role_for("Fortive",
                     "the Skild AI perception unit was acquired by Fortive Industrial Technologies") \
        == "announced_party"
    assert _role_for("PTC", "the ThingWorx business was acquired by PTCTech") == "announced_party"
    assert _role_for("PTC Inc.", "the ThingWorx business was acquired by PTC Inc.'s adviser") \
        == "announced_party"
    # R2b review 7: the 39 inversions that retired the subject-naming
    # templates. Each once served a side naming the WRONG party as agent
    # through an agency phrase outside the then-current blocklist.
    retired = (
        # B1  "for a|an <agent>" — the consideration exemption with a determiner
        "Zebra Technologies acquires the perception unit for a Skild AI subsidiary",
        "Zebra Technologies acquires the perception unit for an affiliate of Skild AI",
        "Zebra Technologies acquires the perception unit for a client",
        "Zebra Technologies acquires the perception unit for a customer",
        "Zebra Technologies acquires the perception unit for an investor group",
        "an announced sale by Zebra Technologies of the unit for a client",
        "the unit was acquired by Zebra Technologies for a Skild AI vehicle",
        "Zebra Technologies' sale of the unit for a Skild AI vehicle",
        "an announced sale of the Robotics Automation business to Skild AI for a client",
        "Zebra Technologies sells the unit (for a client)",
        "Zebra Technologies sells the unit for the aggregate benefit of Skild AI",
        "Zebra Technologies sells the unit for cash-rich Skild AI",
        # B2  appointment-of-agent parentheticals
        "Zebra Technologies (mandated by Skild AI) sells the unit",
        "Zebra Technologies (appointed by Skild AI) sells the unit",
        "Zebra Technologies (retained by Skild AI) sells the unit",
        "Zebra Technologies (engaged by Skild AI) sells the unit",
        "the unit was acquired by Zebra Technologies (mandated by Skild AI)",
        "an announced sale by Zebra Technologies (mandated by Skild AI)",
        "Zebra Technologies (by Skild AI) sells the unit",
        # B3  the same agency wording, capitalised
        "the unit was acquired by Zebra Technologies, On Behalf Of Skild AI",
        "the unit was sold by Zebra Technologies, as Nominee of Skild AI",
        "Zebra Technologies (as Agent of Skild AI) sells the unit",
        "Zebra Technologies (as Trustee) sells the unit",
        "the unit was sold by Zebra Technologies (Not the seller of record)",
        "Fortive (as Nominee) sells the automation unit",
        # B4  a multi-word agency role
        "Zebra Technologies sells the unit in its capacity as sole manager of the Skild AI fund",
        "Zebra Technologies acquires the unit as general partner of the Skild AI fund",
        # B5  agency instruments the lexicon did not name
        "Zebra Technologies sells the unit under a power of attorney from Skild AI",
        "Zebra Technologies acquires the unit under an agency agreement with Skild AI",
        # B6  a co-ordinate clause naming a different principal by role noun
        "the unit was acquired by Zebra Technologies, Skild AI remains the buyer",
        "the unit was sold by Zebra Technologies, the vendor of record remains Skild AI",
        "the unit was acquired by Zebra Technologies, with Skild AI as the ultimate acquirer",
        "with Skild AI as the ultimate acquirer, the unit was acquired by Zebra Technologies",
        "Zebra Technologies (the seller of record remains Skild AI) sells the unit",
        # a bare parenthetical naming another party (review 7 nit 1)
        "Zebra Technologies (Skild AI) sells the unit",
        # the same families reaching the implicit path and the label cohort
        "an announced sale of the Robotics Automation business to Skild AI on behalf of a client",
        "an announced sale of the Robotics Automation business to Skild AI, Fanuc is the seller",
        "ABB Ltd sells the robotics division for a client",
        "Smith & Nephew Robotics acquires the surgical unit for a Skild AI affiliate",
    )
    for sentence in retired:
        assert _zebra_role(**{"limitations.establishes": [sentence]}) == "announced_party", sentence


def test_ownership_side_is_withheld_when_the_subject_is_named_as_the_actor():
    # The subject-naming templates are RETIRED (R2b review 7). Six rounds of
    # blocklist repairs were each inverted by an agency phrase the previous
    # round had not seen — "for a client", "(mandated by Y)", "as sole manager
    # of the Y fund", "under a power of attorney from Y", "Y remains the buyer"
    # — because agency in free prose is an open set. A served side naming the
    # WRONG party as agent is a blocker; an unnecessary neutral is not. Prose
    # that makes the subject the actor is therefore neutral whatever its shape,
    # and however the subject is written.
    for label, sentence in (
        ("Zebra Technologies",
         "Zebra Technologies divests the Robotics Automation business to Skild AI"),
        ("Zebra Technologies",
         "an announced sale by Zebra of its Robotics Automation business to Skild AI"),
        ("Zebra Technologies", "the business was sold by Zebra to Skild AI"),
        ("Zebra Technologies",
         "Zebra Technologies' sale of the Robotics Automation business to Skild AI"),
        ("Zebra Technologies",
         "Zebra Technologies’ sale of the Robotics Automation business to Skild AI"),
        ("Zebra Technologies", "Zebra (Nasdaq: ZBRA) sells the Robotics Automation business"),
        ("Zebra Technologies",
         "Zebra Technologies (advised by Goldman Sachs) sells the unit to Skild AI"),
        ("Zebra Technologies, Inc.",
         "Zebra Technologies, Inc. sells the Robotics Automation business"),
        ("ABB Ltd", "ABB acquires the robotics unit"),
        ("Smith & Nephew Robotics", "Smith & Nephew Robotics sells the unit to Skild AI"),
        ("PTC Inc.", "the ThingWorx business was acquired by PTC Inc."),
    ):
        assert _role_for(label, sentence) == "announced_party", (label, sentence)
    # the subject named INSIDE an otherwise-grammatical guard sentence also
    # withholds the side
    assert _zebra_role(**{"limitations.establishes":
                          ["an announced sale by Zebra Technologies of the Robotics Automation "
                           "business to Skild AI"]}) == "announced_party"
    # a curated product that innocently shares a word with its owner's label is
    # NOT a subject mention, so the guard sentence still anchors
    assert _role_for("Robotics Automation Holdings",
                     "an announced sale of the Robotics Automation business to Skild AI") \
        == "announced_seller"


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
