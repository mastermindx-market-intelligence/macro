"""Opus R1 probes for PR #7932 — every test here FAILS at a27a7262. Freeze RED (R-MIN-04)."""
import dataclasses
import importlib.util
import sys

import pytest

from engine.market_ontology.mining_dependency_binding import (
    MiningResearchRefusal,
    publication_harness,
    validate_delivery_inputs,
)
from tests.mining_casebook import synthetic_case


def _inputs(case, query=None, expected=None):
    return {
        "query": query if query is not None else case.query,
        "bundle": case.bundle,
        "expected": expected if expected is not None else case.expected,
        "account_generation": case.account_generation,
    }


# F1 — the mirrored kernel refuses limit > 100 (SEM@pr/7870:90 _MAX_LIMIT); this harness admits up to 500.
@pytest.mark.parametrize("limit", [101, 250, 500])
def test_probe_limit_above_the_shared_kernel_ceiling_is_refused(limit):
    case = synthetic_case("copper_complete")
    query = dataclasses.replace(case.query, limit=limit)
    with pytest.raises(MiningResearchRefusal) as raised:
        validate_delivery_inputs(_inputs(case, query=query))
    assert raised.value.code == "limit_out_of_range"


def test_probe_limit_one_hundred_is_admitted():
    case = synthetic_case("copper_complete")
    result = validate_delivery_inputs(_inputs(case, query=dataclasses.replace(case.query, limit=100)))
    assert result["live_admission"] == "refused"


# F1 — SEM:177-178 fires expected_generation_required only when offset > 0.
def test_probe_offset_zero_without_expected_generation_is_admitted():
    case = synthetic_case("copper_complete")
    query = dataclasses.replace(case.query, offset=0, expected_generation=None)
    result = validate_delivery_inputs(_inputs(case, query=query))
    assert result["live_admission"] == "refused"


# F1 — SEM:179-181 fires replay_cutoffs_required only for time_mode == "system_replay".
def test_probe_latest_time_mode_needs_no_replay_cutoffs():
    case = synthetic_case("copper_complete")
    query = dataclasses.replace(case.query, time_mode="latest", source_cutoff=None, recorded_cutoff=None)
    result = validate_delivery_inputs(_inputs(case, query=query))
    assert result["live_admission"] == "refused"


# F2 — the degrade must be typed even when the module resolves and then fails to import.
def test_probe_shared_contract_degrade_is_exception_safe(monkeypatch):
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: object())
    # seat amendment (R-MIN-26): the probe must stay meaningful once #7870 lands, so the import
    # itself is forced to fail — None in sys.modules makes ``import`` raise ImportError.
    monkeypatch.setitem(sys.modules, "engine.theme_graph.curation_assertion", None)
    with pytest.raises(MiningResearchRefusal) as raised:
        publication_harness().shared_contract()
    assert raised.value.code == "shared_contract_unavailable"


# F3 — the refusal must report the harness's own read counter, not a constant.
def test_probe_route_unbound_reports_the_harness_read_counter():
    harness = publication_harness()
    harness.read_count = 3
    assert harness.client().read_count == 3


# F5 — a case that claims a signed block while omitting its economics must be refused.
def test_probe_expected_contradicting_omissions_is_refused():
    case = synthetic_case(
        "source_only",
        expected={
            "signed_native_blocks": [
                {"measure": "fictional operating income", "value": 111, "basis": "fictional reported dollars"}
            ],
            "reported_only_economics": [],
        },
    )
    with pytest.raises(ValueError):
        validate_delivery_inputs(_inputs(case))


# F6 — the one case whose expected output is a retained signed block must not be "not research usable".
def test_probe_a_retained_signed_block_is_research_usable():
    case = synthetic_case("signed_loss")
    assert case.expected["signed_native_blocks"][0]["value"] == -375
    result = validate_delivery_inputs(_inputs(case))
    assert result["research_usable"] is True
