"""The semiconductor research names are the shared shell, byte-neutrally.

Expectations below were captured at authoring from
``git show HEAD:engine/market_ontology/semiconductor_theme_research.py``
(the pre-move composer) on ``tests/fixtures/semiconductor_theme_research``.
The committed test does not call git. Fourteen bundle fixtures, 39
assertions: ``_passes_time_mode`` kept every row and added no limitation.
``_Selection.interpretation_blocks`` returned every block, sorted by
``interpretation_id``, and added no limitation. The named probes are the
drop branches of that same pre-move function on ``recorded_later``.

``review_excluded``, ``correction_lineage`` and ``collapse_syndicated``
were not defined on that composer (hasattr was false). Their outputs were
captured by running the moved algorithm on ``recorded_later``'s assertion
at authoring time and are frozen here. This composer does not call them,
so those three do not participate in semiconductor response bytes.
"""
from __future__ import annotations

import copy
import json
from dataclasses import fields, replace
from pathlib import Path

import engine.market_ontology.semiconductor_theme_research as semi
import engine.market_ontology.theme_research_binding as shell

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "semiconductor_theme_research"


def load_bundle_case(name: str):
    """Build the carriers from one synthetic bundle fixture.

    Local on purpose: the shared helper also imports the witness-nest
    intake, and this suite does not read that nest.
    """
    value = json.loads((FIXTURE_ROOT / f"{name}.json").read_text(encoding="utf-8"))
    if value.get("synthetic") is not True:
        raise ValueError(f"{name} is not a synthetic fixture")
    source = value["bundle"]
    bundle = shell.OwnerBundle(
        revision_tuple=tuple(tuple(item) for item in source["revision_tuple"]),
        rights_revision=source["rights_revision"],
        assertions=tuple(source["assertions"]),
        identity_results=tuple(source["identity_results"]),
        event_workspaces=tuple(source["event_workspaces"]),
        financial_packets=tuple(source["financial_packets"]),
        interpretation_blocks=tuple(source["interpretation_blocks"]),
        native_refs=tuple(source["native_refs"]),
        omissions=tuple(source["omissions"]),
    )
    return shell.ResearchQuery(**value["query"]), bundle

# Bundle fixtures whose pre-move time gate kept every assertion.
FIXTURE_ASSERTION_COUNTS = {
    "abf_substrate": 2,
    "corrected_interpretation": 1,
    "cowos_variants": 3,
    "empty_financial_success": 3,
    "hbm_12h_16h": 2,
    "jv_physical_vs_economics": 6,
    "mixed_wafer_units": 2,
    "page2_new_generation": 2,
    "recorded_later": 1,
    "revoked_rights_warm": 3,
    "st_target_then_operations": 2,
    "umc_output_utilization": 3,
    "witness_hbm_packaging": 5,
    "witness_sic_gan": 4,
}

# Non-empty interpretation blocks, pre-move, sorted by interpretation_id.
FIXTURE_BLOCK_IDS = {
    "abf_substrate": [],
    "corrected_interpretation": ["interp-psi-new", "interp-psi-old"],
    "cowos_variants": [],
    "empty_financial_success": [],
    "hbm_12h_16h": ["interp-kappa-01"],
    "jv_physical_vs_economics": [],
    "mixed_wafer_units": [],
    "page2_new_generation": [],
    "recorded_later": [],
    "revoked_rights_warm": [],
    "st_target_then_operations": [],
    "umc_output_utilization": [],
    "witness_hbm_packaging": ["interp-hbm-current"],
    "witness_sic_gan": ["interp-sic-current"],
}

RESEARCH_QUERY_FIELDS = (
    "anchor_theme_id",
    "slice_key",
    "view",
    "time_mode",
    "source_cutoff",
    "recorded_cutoff",
    "offset",
    "limit",
    "expected_generation",
)
OWNER_BUNDLE_FIELDS = (
    "revision_tuple",
    "rights_revision",
    "assertions",
    "identity_results",
    "event_workspaces",
    "financial_packets",
    "interpretation_blocks",
    "native_refs",
    "omissions",
)


def test_semiconductor_names_are_the_shell_objects():
    assert semi.ResearchQuery is shell.ResearchQuery
    assert semi.OwnerBundle is shell.OwnerBundle
    assert semi.passes_time_mode is shell.passes_time_mode
    assert semi._passes_time_mode is shell.passes_time_mode
    assert semi._canonical_text is shell.canonical_text
    assert semi._is_instant is shell.is_instant
    assert semi._parse_clock is shell.parse_clock
    assert semi._parse_day is shell.parse_day
    assert semi._le is shell.le
    assert semi._within is shell.within
    assert semi._readable is shell.readable
    assert semi._review_excluded is shell.review_excluded
    assert semi._filter_interpretation_blocks is shell.filter_interpretation_blocks
    assert semi._correction_lineage is shell.correction_lineage
    assert semi._collapse_syndicated is shell.collapse_syndicated
    assert semi._in_anchor_scope is shell.in_anchor_scope
    assert semi.review_excluded is shell.review_excluded
    assert semi.filter_interpretation_blocks is shell.filter_interpretation_blocks
    assert semi.correction_lineage is shell.correction_lineage
    assert semi.collapse_syndicated is shell.collapse_syndicated
    assert semi.ResearchRefusal is shell.ResearchRefusal
    assert semi.canonical_text is shell.canonical_text
    assert semi.generation_fingerprint is shell.generation_fingerprint
    assert semi.in_anchor_scope is shell.in_anchor_scope
    assert semi.is_instant is shell.is_instant
    assert semi.le is shell.le
    assert semi.parse_clock is shell.parse_clock
    assert semi.parse_day is shell.parse_day
    assert semi.readable is shell.readable
    assert semi.validate_cutoff_format is shell.validate_cutoff_format
    assert semi.validate_pagination is shell.validate_pagination
    assert semi.validate_replay_cutoffs is shell.validate_replay_cutoffs
    assert semi.within is shell.within


def test_shared_module_constants():
    assert shell.SHARED_CONTRACT_MODULE == "engine.theme_graph.curation_assertion"
    assert shell.SHARED_SHELL_MODULE == "engine.market_ontology.theme_research_binding"


def test_carriers_are_str_typed_and_keep_the_pre_move_field_order():
    assert [item.name for item in fields(shell.ResearchQuery)] == list(RESEARCH_QUERY_FIELDS)
    assert [item.name for item in fields(shell.OwnerBundle)] == list(OWNER_BUNDLE_FIELDS)
    annotations = shell.ResearchQuery.__annotations__
    assert annotations["slice_key"] == "str"
    assert annotations["view"] == "str"
    assert annotations["time_mode"] == "str"
    assert annotations["anchor_theme_id"] == "str"
    assert annotations["source_cutoff"] == "str | None"
    assert annotations["recorded_cutoff"] == "str | None"


def _gate(assertion, query):
    limitations: set[str] = set()
    kept = shell.passes_time_mode(assertion, query, limitations)
    return bool(kept), sorted(limitations)


def test_passes_time_mode_matches_the_pre_move_gate_on_every_bundle_fixture():
    assert sum(FIXTURE_ASSERTION_COUNTS.values()) == 39
    for name, count in FIXTURE_ASSERTION_COUNTS.items():
        query, bundle = load_bundle_case(name)
        assert len(bundle.assertions) == count
        for assertion in bundle.assertions:
            assert _gate(assertion, query) == (True, [])


def test_passes_time_mode_matches_the_pre_move_drop_branches():
    """``recorded_later`` assertion 0, the same cutoffs the temporal suite uses."""
    query, bundle = load_bundle_case("recorded_later")
    assertion = bundle.assertions[0]
    early = replace(query, source_cutoff="2026-02-01T00:00:00Z")
    latest = replace(query, time_mode="latest", source_cutoff=None, recorded_cutoff=None)
    replay_ok = replace(
        query,
        time_mode="system_replay",
        source_cutoff="2026-06-30T00:00:00Z",
        recorded_cutoff="2026-06-30T00:00:00Z",
    )
    replay_early = replace(
        query,
        time_mode="system_replay",
        source_cutoff="2026-06-30T00:00:00Z",
        recorded_cutoff="2026-03-01T00:00:00Z",
    )
    assert _gate(assertion, query) == (True, [])
    assert _gate(assertion, early) == (False, [])
    assert _gate(assertion, latest) == (True, [])
    assert _gate(assertion, replay_ok) == (True, [])
    assert _gate(assertion, replay_early) == (False, [])

    unknown = copy.deepcopy(dict(assertion))
    unknown["source"]["available_at"] = "unknown"
    absent = copy.deepcopy(dict(assertion))
    absent["source"].pop("available_at", None)
    assert _gate(unknown, replay_ok) == (False, ["availability_unknown_excluded"])
    assert _gate(absent, replay_ok) == (False, ["availability_unknown_excluded"])

    same_day = replace(
        query,
        time_mode="system_replay",
        source_cutoff="2026-02-10T12:00:00Z",
        recorded_cutoff="2026-06-30T00:00:00Z",
    )
    assert _gate(assertion, same_day) == (False, ["same_day_grain_ambiguous"])

    bad_retained = copy.deepcopy(dict(assertion))
    bad_retained["source"]["retained_at"] = ""
    assert _gate(bad_retained, replay_ok) == (False, ["undatable_excluded"])


def _blocks(bundle, query):
    limitations: set[str] = set()
    chosen = shell.filter_interpretation_blocks(
        bundle.interpretation_blocks,
        time_mode=query.time_mode,
        recorded_cutoff=query.recorded_cutoff,
        limitations=limitations,
    )
    return [block.get("interpretation_id") for block in chosen], sorted(limitations)


def test_filter_interpretation_blocks_matches_the_pre_move_selector():
    for name, expected_ids in FIXTURE_BLOCK_IDS.items():
        query, bundle = load_bundle_case(name)
        ids, added = _blocks(bundle, query)
        assert ids == expected_ids
        assert added == []
        expected_blocks = sorted(
            (dict(block) for block in bundle.interpretation_blocks),
            key=lambda block: block.get("interpretation_id", ""),
        )
        limitations: set[str] = set()
        assert shell.filter_interpretation_blocks(
            bundle.interpretation_blocks,
            time_mode=query.time_mode,
            recorded_cutoff=query.recorded_cutoff,
            limitations=limitations,
        ) == expected_blocks


def test_filter_interpretation_blocks_matches_the_pre_move_replay_drop():
    query, bundle = load_bundle_case("corrected_interpretation")
    replay = replace(
        query,
        time_mode="system_replay",
        source_cutoff="2026-06-30T00:00:00Z",
        recorded_cutoff="2026-06-30T00:00:00Z",
    )
    assert _blocks(bundle, replay) == (["interp-psi-old"], [])
    blank = []
    for block in bundle.interpretation_blocks:
        copied = dict(block)
        copied["reviewed_at"] = ""
        blank.append(copied)
    limitations: set[str] = set()
    assert shell.filter_interpretation_blocks(
        blank,
        time_mode="system_replay",
        recorded_cutoff="2026-06-30T00:00:00Z",
        limitations=limitations,
    ) == []
    assert sorted(limitations) == ["undatable_excluded"]


def _ref(item):
    scope = item.get("scope") or {}
    return f"gmi-curation://{scope.get('canonical_theme_id')}/{item.get('curation_revision')}"


def test_review_excluded_on_the_recorded_later_assertion():
    _query, bundle = load_bundle_case("recorded_later")
    assertion = bundle.assertions[0]
    now = "2026-06-30T00:00:00Z"
    limitations: set[str] = set()
    assert shell.review_excluded(assertion, now=now, limitations=limitations) is False
    assert limitations == set()

    held = copy.deepcopy(dict(assertion))
    held["review"] = {"disposition": "held", "review_due_at": None}
    limitations = set()
    assert shell.review_excluded(held, now=now, limitations=limitations) is True
    assert sorted(limitations) == ["held_present"]

    rejected = copy.deepcopy(dict(assertion))
    rejected["review"] = {"disposition": "rejected"}
    limitations = set()
    assert shell.review_excluded(rejected, now=now, limitations=limitations) is True
    assert sorted(limitations) == ["rejected_present"]

    expired = copy.deepcopy(dict(assertion))
    expired["review"] = {"disposition": "accepted", "review_due_at": "2026-01-01"}
    limitations = set()
    assert shell.review_excluded(expired, now="2026-06-30", limitations=limitations) is True
    assert sorted(limitations) == ["review_expired_present"]

    future = copy.deepcopy(dict(assertion))
    future["review"] = {"disposition": "accepted", "review_due_at": "2026-12-31"}
    limitations = set()
    assert shell.review_excluded(future, now="2026-06-30", limitations=limitations) is False
    assert limitations == set()

    no_now = copy.deepcopy(dict(assertion))
    no_now["review"] = {"review_due_at": "2026-01-01"}
    limitations = set()
    assert shell.review_excluded(no_now, now=None, limitations=limitations) is False
    assert limitations == set()


def test_correction_lineage_on_the_recorded_later_assertion():
    _query, bundle = load_bundle_case("recorded_later")
    assertion = dict(bundle.assertions[0])
    assert shell.correction_lineage(assertion, [assertion]) == []

    prior = "gmirca_" + "ab" * 16
    child = copy.deepcopy(assertion)
    child["correction"] = {"predecessor_revision": prior}
    assert shell.correction_lineage(child, [child]) == [
        f"gmi-curation://ai_semiconductors/{prior}"
    ]
    parent = copy.deepcopy(assertion)
    parent["curation_revision"] = prior
    assert shell.correction_lineage(child, [child, parent]) == [_ref(parent)]

    left = copy.deepcopy(assertion)
    right = copy.deepcopy(assertion)
    left["curation_revision"] = "gmirca_" + "aa" * 16
    right["curation_revision"] = "gmirca_" + "bb" * 16
    left["correction"] = {"predecessor_revision": right["curation_revision"]}
    right["correction"] = {"predecessor_revision": left["curation_revision"]}
    assert shell.correction_lineage(left, [left, right]) == [_ref(right)]


def test_collapse_syndicated_on_the_recorded_later_assertion():
    _query, bundle = load_bundle_case("recorded_later")
    assertion = dict(bundle.assertions[0])
    limitations: set[str] = set()
    survivors, corroboration = shell.collapse_syndicated([assertion], limitations)
    assert [item["curation_revision"] for item in survivors] == [assertion["curation_revision"]]
    assert corroboration == {}
    assert limitations == set()

    copied = copy.deepcopy(assertion)
    copied["curation_revision"] = "gmirca_" + "cc" * 16
    copied["limitations"] = dict(copied.get("limitations") or {})
    copied["limitations"]["source_dependence"] = (
        "syndicated_copy_of:" + assertion["source"]["publisher"]
    )
    limitations = set()
    survivors, corroboration = shell.collapse_syndicated([assertion, copied], limitations)
    assert [item["curation_revision"] for item in survivors] == [assertion["curation_revision"]]
    assert corroboration == {assertion["curation_revision"]: [_ref(copied)]}
    assert sorted(limitations) == ["syndicated_collapsed"]

    other = copy.deepcopy(assertion)
    other["curation_revision"] = "gmirca_" + "dd" * 16
    limitations = set()
    survivors, corroboration = shell.collapse_syndicated(
        [assertion, other, copied], limitations
    )
    assert [item["curation_revision"] for item in survivors] == [
        assertion["curation_revision"],
        other["curation_revision"],
        copied["curation_revision"],
    ]
    assert corroboration == {}
    assert limitations == set()
