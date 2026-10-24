"""L1a gates: registration paths keep every predicate distinct and every clock apart.

A10 -- an effectiveness notice, an automatic shelf form token, a withdrawal and a
shelf window are separate facts; none of them, alone or combined, is a capacity,
amount, ranking or executable-offering claim, and no forbidden property name
appears in any key or any string value of a path record.
A11 -- valid time (SEC acceptance) and house knowledge (``mastermind_available_at``)
stay separate on every interval, and an earlier ``as_of`` recompiles to exactly the
then-known facts, never to a retroactive later fact.
A20 -- a rule the L0 pack does not carry is missing text answered ``unknown`` with
a named reason; it is never 0, never infinity and never guessed.
A23 -- primary versus resale is accepted-content evidence; a form type never
implies it, so ``offering_role`` stays ``unknown`` on every path.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import re
from typing import Any, Mapping

import pytest

from engine.capital_structure.issuer_state_contracts import (
    FORBIDDEN_PROPERTY_PATTERN,
    STATE_CONTRACT_VERSION,
    CalculationReceipt,
    CapitalInputs,
    FamilyProvenance,
    FamilyState,
    GenerationBinding,
    sha256_of,
)
from engine.capital_structure.registration_integration import (
    AUTHORITY,
    AUTOMATIC_SHELF_FORMS,
    PREDICATE_STATUSES,
    REGISTRATION_INTEGRATION_VERSION,
    REGISTRATION_PATH_SCHEMA,
    RULE_415_A_5,
    RULE_462_E,
    SHELF_WINDOW_CONDITIONS,
    UNAVAILABLE,
    WKSI_CONDITION,
    RegistrationIntegrationRefusal,
    integrate_registration_paths,
    registration_path_at,
)
from engine.capital_structure.registration_lifecycle import UNAVAILABLE as LIFECYCLE_UNAVAILABLE
from engine.capital_structure.rule_applicability import (
    ApplicableRule,
    RuleApplicabilityError,
    RuleWindow,
    load_rule_applicability_pack,
    rule_status_as_of,
)
from tests.test_capital_structure_registration_lifecycle import (
    _compile,
    _edge,
    _event,
    _scenario,
)

EVENT_SCHEMA = "capital_structure.event.v1"
EDGE_SCHEMA = "capital_structure.event_edge.v1"
BUNDLE_SCHEMA = "capital_structure.registration_lifecycle_bundle.v1"
AS_OF = "2026-10-14T00:00:00Z"
GENERATED_AT = "2026-10-14T06:00:00Z"
PREDICATE_NAMES = (
    "filed",
    "effect_observed",
    "automatic_shelf_form",
    "automatic_effectiveness",
    "offering_role",
    "withdrawn",
    "replaced",
    "shelf_window",
)


# ---------------------------------------------------------------------------
# Builders: the lifecycle suite's own event/edge factories, never re-implemented
# ---------------------------------------------------------------------------


def _binding(family: str, schema: str | None, support: str, *, seed: str, as_of: str = AS_OF) -> GenerationBinding:
    return GenerationBinding(
        family,
        schema,
        support,
        generation_id=f"generation:cs:{seed * 24}"[:200],
        artifact_sha256=sha256_of({"family": family, "seed": seed, "as_of": as_of}),
        as_of=as_of,
    )


def _events_inputs(
    events: list[dict],
    edges: list[dict],
    *,
    as_of: str = AS_OF,
    support: str = "supported",
    lifecycles: tuple[dict, ...] = (),
    lifecycle_binding: GenerationBinding | None = None,
    event_seed: str = "a",
) -> CapitalInputs:
    bindings = [_binding("events", EVENT_SCHEMA, support, seed=event_seed, as_of=as_of)]
    bindings.append(_binding("event_edges", EDGE_SCHEMA, support, seed="b", as_of=as_of))
    if lifecycle_binding is not None:
        bindings.append(lifecycle_binding)
    return CapitalInputs(
        bindings=tuple(bindings),
        events=tuple(events),
        edges=tuple(edges),
        lifecycles=lifecycles,
    )


def _lifecycle_inputs(bundle: dict, *, as_of: str = AS_OF, support: str = "supported") -> CapitalInputs:
    return CapitalInputs(
        bindings=(_binding("registration_lifecycle", BUNDLE_SCHEMA, support, seed="c", as_of=as_of),),
        lifecycles=(bundle,),
    )


def _integrate(events, edges, *, as_of=AS_OF, generated_at=GENERATED_AT, rule_pack=None, **kwargs):
    return integrate_registration_paths(
        _events_inputs(list(events), list(edges), as_of=as_of, **kwargs),
        as_of=as_of,
        generated_at=generated_at,
        rule_pack=rule_pack,
    )


def _s1_filed_amended_effective_withdrawn() -> tuple[list[dict], list[dict]]:
    """S-1 -> S-1/A -> EFFECT -> RW, each with its own house-knowledge clock."""
    original = _event(1, "S-1", accepted_at="2026-08-01T10:00:00Z", seen_at="2026-08-01T18:00:00Z")
    amendment = _event(2, "S-1/A", accepted_at="2026-08-02T10:00:00Z", seen_at="2026-08-03T12:00:00Z")
    effect = _event(3, "EFFECT", accepted_at="2026-08-04T10:00:00Z", seen_at="2026-08-04T18:00:00Z")
    withdrawal = _event(4, "RW", accepted_at="2026-08-05T10:00:00Z", seen_at="2026-08-05T18:00:00Z")
    edges = [
        _edge(amendment, original, "amendment_of"),
        _edge(effect, amendment, "effectuates"),
        _edge(withdrawal, amendment, "withdraws"),
    ]
    return [original, amendment, effect, withdrawal], edges


def _s3_amended_effective_post_effective() -> tuple[list[dict], list[dict]]:
    """S-3 -> S-3/A -> EFFECT -> POS AM: a post-effective amendment stays effective."""
    original = _event(11, "S-3", accepted_at="2026-08-01T10:00:00Z", seen_at="2026-08-01T18:00:00Z")
    amendment = _event(12, "S-3/A", accepted_at="2026-08-02T10:00:00Z", seen_at="2026-08-03T12:00:00Z")
    effect = _event(13, "EFFECT", accepted_at="2026-08-04T10:00:00Z", seen_at="2026-08-04T18:00:00Z")
    post = _event(14, "POS AM", accepted_at="2026-08-06T10:00:00Z", seen_at="2026-08-07T09:00:00Z")
    edges = [
        _edge(amendment, original, "amendment_of"),
        _edge(effect, amendment, "effectuates"),
        _edge(post, original, "amendment_of"),
    ]
    return [original, amendment, effect, post], edges


def _automatic_shelf_only() -> tuple[list[dict], list[dict]]:
    """A bare S-3ASR: an automatic shelf form token and no EFFECT notice."""
    return [_event(21, "S-3ASR", accepted_at="2026-08-01T10:00:00Z", seen_at="2026-08-01T18:00:00Z")], []


def _corrected_automatic_shelf_with_repeated_effect() -> tuple[list[dict], list[dict]]:
    """LPTH-like: a corrected S-3ASR root, two POS AMs and two EFFECT notices.

    The ``supersedes`` edge is event-version supersession of the root, never a
    Rule 415(a)(6) replacement of a prior registration statement.
    """
    original = _event(31, "S-3", accepted_at="2026-08-01T10:00:00Z", seen_at="2026-08-01T18:00:00Z")
    correction = _event(
        31, "S-3ASR", accepted_at="2026-08-01T10:00:00Z", seen_at="2026-08-06T10:00:00Z",
        correction_version=2, correction_of=original["event_id"], source_suffix="corrected",
    )
    first_post = _event(32, "POS AM", accepted_at="2026-08-03T10:00:00Z", seen_at="2026-08-03T18:00:00Z")
    first_effect = _event(33, "EFFECT", accepted_at="2026-08-04T10:00:00Z", seen_at="2026-08-04T18:00:00Z")
    second_post = _event(34, "POS AM", accepted_at="2026-08-07T10:00:00Z", seen_at="2026-08-07T18:00:00Z")
    second_effect = _event(35, "EFFECT", accepted_at="2026-08-08T10:00:00Z", seen_at="2026-08-08T18:00:00Z")
    edges = [
        _edge(correction, original, "supersedes", observed_at="2026-08-06T10:00:00Z"),
        _edge(first_post, original, "amendment_of"),
        _edge(first_effect, first_post, "effectuates"),
        _edge(second_post, original, "amendment_of"),
        _edge(second_effect, second_post, "effectuates"),
    ]
    return [original, correction, first_post, first_effect, second_post, second_effect], edges


def _s3_effective_on(accepted_at: str, *, seen_at: str) -> tuple[list[dict], list[dict]]:
    """An S-3 whose EFFECT notice was accepted at an exact instant."""
    original = _event(41, "S-3", accepted_at="2024-01-15T10:00:00Z", seen_at="2024-01-15T18:00:00Z")
    effect = _event(42, "EFFECT", accepted_at=accepted_at, seen_at=seen_at)
    return [original, effect], [_edge(effect, original, "effectuates")]


def _stub_pack(
    *,
    version: str = "capital-structure-rule-applicability/stub-test",
    with_rules: tuple[str, ...] = (RULE_415_A_5, RULE_462_E),
) -> Any:
    """A minimal pack whose 415(a)(5) and 462(e) text is verified over the fixtures.

    Built from the real ``ApplicableRule``/``RuleWindow`` records so that
    ``rule_status_as_of`` semantics are honoured unchanged rather than replaced.
    ``with_rules=()`` models a pack that carries neither text (the frozen L0
    pack 1.0.0 shape) without depending on which pack edition the repo ships.
    """

    def rule(rule_id: str, citation: str) -> ApplicableRule:
        return ApplicableRule(
            rule_id=rule_id,
            binding_class="binding_rule",
            enforceable=True,
            citation=citation,
            form=None,
            instruction=None,
            span_ids=("stub:span",),
            reference_span_labels=(),
            windows=(RuleWindow(
                kind="version_index", start="1990-01-01", end="2030-12-31",
                sha256="0" * 64, span_id="stub:span", reference_span_label=None,
            ),),
            before_first_window="withheld",
            not_in_force_before=None,
            required_issuer_facts=(),
            interpretation_date=None,
            note=None,
        )

    @dataclass(frozen=True)
    class StubPack:
        version: str
        rules: Mapping[str, ApplicableRule] = field(default_factory=dict)
        gaps: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)

        def rule(self, rule_id: str) -> ApplicableRule:
            if rule_id not in self.rules:
                raise RuleApplicabilityError(f"unknown rule {rule_id!r}")
            return self.rules[rule_id]

    citations = {RULE_415_A_5: "17 CFR 230.415(a)(5)", RULE_462_E: "17 CFR 230.462(e)"}
    return StubPack(
        version=version,
        rules={rule_id: rule(rule_id, citations[rule_id]) for rule_id in with_rules},
    )


@pytest.fixture(scope="module")
def repo_pack():
    """The rule pack the repository ships (1.1.0 once L1b has landed)."""
    return load_rule_applicability_pack()


_AMOUNT_KEY = re.compile(r"amount|dollar|proceeds|remaining|balance|quantity|price|size", re.IGNORECASE)
_SHA256_RUN = re.compile(r"[0-9a-f]{64}")


def _scalars(value: Any):
    if isinstance(value, Mapping):
        for item in value.values():
            yield from _scalars(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _scalars(item)
    else:
        yield value


def _walk(value: Any, path: str = "<path>"):
    """Yield ``(path, kind, token)`` for every key and every string value."""
    if isinstance(value, Mapping):
        for key, item in value.items():
            yield f"{path}.{key}", "key", str(key)
            yield from _walk(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            yield from _walk(item, f"{path}[{index}]")
    elif isinstance(value, str):
        yield path, "value", value


# ---------------------------------------------------------------------------
# A.5 case 1 -- A10: distinct predicates on an S-1 path, no capacity in any token
# ---------------------------------------------------------------------------


def test_a10_s1_path_predicates_distinct():
    events, edges = _s1_filed_amended_effective_withdrawn()
    path = _integrate(events, edges).paths[0]
    predicates = path["predicates"]

    assert tuple(predicates) == PREDICATE_NAMES
    assert path["observed_registration_state"] == "withdrawn"
    filed, effect, withdrawn = predicates["filed"], predicates["effect_observed"], predicates["withdrawn"]
    assert (filed["status"], effect["status"], withdrawn["status"]) == ("observed", "observed", "observed")
    assert filed["evidence_accessions"] == ["0000000001-26-000001"]
    assert effect["evidence_accessions"] == ["0000000001-26-000003"]
    assert withdrawn["evidence_accessions"] == ["0000000001-26-000004"]
    evidence = [set(filed["evidence_event_ids"]), set(effect["evidence_event_ids"]), set(withdrawn["evidence_event_ids"])]
    assert len(evidence) == 3 and not (evidence[0] & evidence[1]) and not (evidence[1] & evidence[2])
    assert effect["reason"] == "effect_notice_observed"
    assert predicates["automatic_shelf_form"]["status"] == "not_observed"
    assert predicates["automatic_shelf_form"]["reason"] == "form_fact_only_not_wksi_status"
    assert predicates["automatic_effectiveness"]["status"] == "not_applicable"
    assert predicates["automatic_effectiveness"]["reason"] == "no_automatic_shelf_form_observed"
    assert predicates["offering_role"] == {
        "status": "unknown",
        "evidence_event_ids": [],
        "evidence_accessions": [],
        "reason": "no_accepted_content_evidence_lifecycle_carries_no_primary_or_resale_classification",
        "rule_ids": [],
        "value": "unknown",
    }
    # No key and no string value of the record may name a capacity, score, rank,
    # sizing, entry or prophet fact (A10/A48).
    for location, kind, token in _walk(path):
        assert not FORBIDDEN_PROPERTY_PATTERN.match(token), f"{kind} {location}: {token!r}"
    assert path["authority"] == dict(AUTHORITY)
    assert path["authority"]["is_context_only"] is True
    assert set(path["unavailable"]) >= {
        "active_or_executable_offering_capacity",
        "registered_amount_remaining",
        "remaining_offering_dollars",
        "wksi_eligibility",
        "replacement_carry_forward_classification",
        "exchange_public_offering_treatment",
    }
    # No amount, price, proceeds or remaining-dollars key at any depth, and no
    # floating-point value anywhere: a registration path carries dates and ids.
    assert not [
        location for location, kind, token in _walk(path)
        if kind == "key" and _AMOUNT_KEY.search(token)
    ]
    assert not [value for value in _scalars(path) if isinstance(value, float)]
    assert path["schema"] == REGISTRATION_PATH_SCHEMA


def test_a10_every_predicate_status_is_closed_and_reasons_are_snake_case():
    events, edges = _corrected_automatic_shelf_with_repeated_effect()
    integration = _integrate(events, edges, rule_pack=_stub_pack())
    for path in integration.paths:
        for name, predicate in path["predicates"].items():
            assert predicate["status"] in PREDICATE_STATUSES, name
            assert predicate["reason"] == predicate["reason"].lower()
            assert set(predicate["reason"]) <= set("abcdefghijklmnopqrstuvwxyz0123456789_")
            assert isinstance(predicate["rule_ids"], list)


# ---------------------------------------------------------------------------
# A.5 case 2 -- A10: an automatic shelf form is a form fact, not effectiveness
# ---------------------------------------------------------------------------


def test_a10_automatic_shelf_form_is_a_form_fact_not_effectiveness():
    events, edges = _automatic_shelf_only()
    path = _integrate(events, edges, rule_pack=None).paths[0]
    predicates = path["predicates"]

    assert predicates["automatic_shelf_form"]["status"] == "observed"
    assert predicates["automatic_shelf_form"]["reason"] == "form_fact_only_not_wksi_status"
    assert predicates["automatic_shelf_form"]["evidence_accessions"] == ["0000000001-26-000021"]
    assert path["origin"]["form"] in AUTOMATIC_SHELF_FORMS
    assert predicates["automatic_effectiveness"]["status"] == "unknown"
    assert predicates["automatic_effectiveness"]["reason"] == "rule_462_e_text_not_in_rule_pack"
    assert predicates["effect_observed"]["status"] == "not_observed"
    assert predicates["effect_observed"]["reason"] == (
        "no_effect_notice_visible_absence_is_not_non_effectiveness"
    )
    assert predicates["effect_observed"]["evidence_event_ids"] == []
    assert path["observed_registration_state"] == "filed"
    assert "wksi_eligibility" in path["unavailable"]
    assert "automatic_effectiveness_without_wksi_determination" in path["unavailable"]


# ---------------------------------------------------------------------------
# A.5 case 3 -- A11: valid time and house knowledge stay apart on every interval
# ---------------------------------------------------------------------------


def test_a11_intervals_separate_valid_time_from_house_knowledge():
    events, edges = _s3_amended_effective_post_effective()
    path = _integrate(events, edges).paths[0]

    assert path["intervals"] == [
        {
            "state": "filed", "transition": "filed",
            "event_id": events[0]["event_id"], "accession": "0000000001-26-000011", "form": "S-3",
            "valid_from": "2026-08-01T10:00:00Z", "valid_to": "2026-08-02T10:00:00Z",
            "known_from": "2026-08-01T18:00:00Z", "valid_to_known_from": "2026-08-03T12:00:00Z",
        },
        {
            "state": "amended", "transition": "amended",
            "event_id": events[1]["event_id"], "accession": "0000000001-26-000012", "form": "S-3/A",
            "valid_from": "2026-08-02T10:00:00Z", "valid_to": "2026-08-04T10:00:00Z",
            "known_from": "2026-08-03T12:00:00Z", "valid_to_known_from": "2026-08-04T18:00:00Z",
        },
        {
            "state": "effective", "transition": "effective",
            "event_id": events[2]["event_id"], "accession": "0000000001-26-000013", "form": "EFFECT",
            "valid_from": "2026-08-04T10:00:00Z", "valid_to": "2026-08-06T10:00:00Z",
            "known_from": "2026-08-04T18:00:00Z", "valid_to_known_from": "2026-08-07T09:00:00Z",
        },
        {
            "state": "effective", "transition": "amended",
            "event_id": events[3]["event_id"], "accession": "0000000001-26-000014", "form": "POS AM",
            "valid_from": "2026-08-06T10:00:00Z", "valid_to": None,
            "known_from": "2026-08-07T09:00:00Z", "valid_to_known_from": None,
        },
    ]
    assert path["observed_registration_state"] == "effective"
    for interval in path["intervals"]:
        assert interval["known_from"] >= interval["valid_from"]


# ---------------------------------------------------------------------------
# A.5 case 4 -- A11: then-known differs from later-known exactly at the EFFECT
# ---------------------------------------------------------------------------


def test_a11_then_known_differs_from_later_known_exactly_at_the_effect():
    events, edges = _s1_filed_amended_effective_withdrawn()
    effect = events[2]
    then_as_of = "2026-08-04T00:00:00Z"

    then = _integrate(events, edges, as_of=then_as_of, generated_at="2026-08-04T06:00:00Z")
    later = _integrate(events, edges)
    then_path, later_path = then.paths[0], later.paths[0]

    assert then_path["observed_registration_state"] == "amended"
    assert then_path["predicates"]["effect_observed"]["status"] == "not_observed"
    assert then_path["predicates"]["effect_observed"]["reason"] == (
        "no_effect_notice_visible_absence_is_not_non_effectiveness"
    )
    assert then_path["predicates"]["filed"]["status"] == "observed"
    assert later_path["observed_registration_state"] == "withdrawn"
    assert later_path["predicates"]["effect_observed"]["status"] == "observed"

    # The two calls differ by exactly the facts that became known: the EFFECT and
    # the RW, and nothing else.
    then_ids = [interval["event_id"] for interval in then_path["intervals"]]
    later_ids = [interval["event_id"] for interval in later_path["intervals"]]
    assert then_ids == [events[0]["event_id"], events[1]["event_id"]]
    assert later_ids == [event["event_id"] for event in events]
    assert set(later_ids) - set(then_ids) == {effect["event_id"], events[3]["event_id"]}
    assert then_path["path_id"] != later_path["path_id"]
    assert {key: then_path[key] for key in ("issuer", "registration")} == {
        key: later_path[key] for key in ("issuer", "registration")
    }

    # Valid-time lookup on the later-known path: before the origin, inside the
    # amendment, and after the effectiveness notice.
    assert registration_path_at(later_path, "2026-07-31T00:00:00Z") is None
    assert registration_path_at(later_path, "2026-08-01T12:00:00Z")["state"] == "filed"
    assert registration_path_at(later_path, "2026-08-03T00:00:00Z")["state"] == "amended"
    assert registration_path_at(later_path, "2026-08-04T12:00:00Z")["state"] == "effective"
    # The then-known path simply has no effective interval to find.
    assert registration_path_at(then_path, "2026-08-04T12:00:00Z")["state"] == "amended"
    assert registration_path_at(then_path, "2026-08-05T00:00:00Z") is not None


# ---------------------------------------------------------------------------
# A.5 case 5 -- repeated EFFECT and a corrected root keep order and versions
# ---------------------------------------------------------------------------


def test_a11_repeated_effect_and_amendment_chain_preserve_order_and_correction_version():
    events, edges = _corrected_automatic_shelf_with_repeated_effect()
    correction = events[1]
    bundle = _compile(events, edges, as_of=AS_OF, generated_at=GENERATED_AT)
    timeline = bundle["records"][0]["timeline"]
    path = _integrate(events, edges).paths[0]

    assert path["origin"]["event_id"] == correction["event_id"]
    assert [item["event_id"] for item in timeline if item["transition"] == "amended"] == [
        item["event_id"] for item in path["amendment_chain"]
    ]
    assert [item["form"] for item in path["amendment_chain"]] == ["POS AM", "POS AM"]
    assert [item["correction_version"] for item in path["amendment_chain"]] == [
        item["correction_version"] for item in timeline if item["transition"] == "amended"
    ]
    assert timeline[0]["correction_version"] == 2
    assert [item["sec_accepted_at"] for item in path["amendment_chain"]] == [
        "2026-08-03T10:00:00Z", "2026-08-07T10:00:00Z",
    ]
    assert [item["relationship"]["relationship"] for item in path["amendment_chain"]] == [
        "amendment_of", "amendment_of",
    ]
    # Two EFFECT notices: both are evidence, the second one keeps the state effective.
    effects = [item for item in path["intervals"] if item["transition"] == "effective"]
    assert [item["form"] for item in effects] == ["EFFECT", "EFFECT"]
    assert path["predicates"]["effect_observed"]["evidence_accessions"] == [
        "0000000001-26-000033", "0000000001-26-000035",
    ]
    assert path["observed_registration_state"] == "effective"
    assert path["intervals"][-1]["state"] == "effective"


# ---------------------------------------------------------------------------
# A.5 case 6 -- defers pass through and partial coverage is a named limit
# ---------------------------------------------------------------------------


def test_deferred_pass_through_and_partial_coverage_limit():
    events, edges = _scenario("post_withdrawal_effect")
    bundle = _compile(events, edges, as_of=AS_OF, generated_at=GENERATED_AT)
    assert bundle["deferred"] and bundle["coverage"]["state"] == "partial"

    integration = _integrate(events, edges)
    assert integration.deferred == tuple(deepcopy(dict(row)) for row in bundle["deferred"])
    assert [row["reason"] for row in integration.deferred] == ["post_withdrawal_transition"]
    assert "lifecycle_coverage_partial" in integration.support_limits
    path = integration.paths[0]
    assert path["coverage"] == bundle["records"][0]["coverage"]
    assert path["coverage"]["state"] == "partial"
    assert path["coverage"]["deferred_ids"] == [row["defer_id"] for row in bundle["deferred"]]
    # A deferred post-withdrawal EFFECT is not an observed effectiveness.
    assert path["observed_registration_state"] == "withdrawn"
    assert path["predicates"]["effect_observed"]["status"] == "not_observed"
    assert integration.as_record()["deferred_ids"] == [row["defer_id"] for row in bundle["deferred"]]


# ---------------------------------------------------------------------------
# A.5 case 7 -- source selection fails closed
# ---------------------------------------------------------------------------


def test_source_selection_events_and_precompiled_bundle_agree():
    events, edges = _s3_amended_effective_post_effective()
    bundle = _compile(events, edges, as_of=AS_OF, generated_at=GENERATED_AT)

    from_events = _integrate(events, edges)
    from_bundle = integrate_registration_paths(
        _lifecycle_inputs(bundle), as_of=AS_OF, generated_at=GENERATED_AT,
    )
    both = _integrate(
        events, edges,
        lifecycles=(bundle,),
        lifecycle_binding=_binding("registration_lifecycle", BUNDLE_SCHEMA, "supported", seed="c"),
    )

    assert from_events.paths == from_bundle.paths
    assert from_events.paths == both.paths
    assert from_events.deferred == from_bundle.deferred
    assert from_bundle.source_family == "registration_lifecycle"
    assert from_bundle.source_schema == BUNDLE_SCHEMA
    assert from_bundle.source_generation_id == bundle["generation_id"]
    assert from_events.source_family == "events"
    assert from_events.source_schema == EVENT_SCHEMA
    assert both.source_family == "events"


def test_source_selection_mismatched_precompiled_bundle_refuses_naming_both_digests():
    events, edges = _s3_amended_effective_post_effective()
    other = _compile(events[:3], edges[:2], as_of=AS_OF, generated_at=GENERATED_AT)
    assert other["records"] != _compile(events, edges, as_of=AS_OF, generated_at=GENERATED_AT)["records"]

    with pytest.raises(RegistrationIntegrationRefusal) as excinfo:
        _integrate(
            events, edges,
            lifecycles=(other,),
            lifecycle_binding=_binding("registration_lifecycle", BUNDLE_SCHEMA, "supported", seed="c"),
        )
    message = str(excinfo.value)
    assert "recompiled registration lifecycle records differ" in message
    digests = _SHA256_RUN.findall(message)
    assert len(digests) == 2 and digests[0] != digests[1]
    assert sha256_of(other["records"]) in digests
    assert sha256_of(_compile(events, edges, as_of=AS_OF, generated_at=GENERATED_AT)["records"]) in digests


def test_source_selection_precompiled_bundle_at_another_as_of_refuses():
    events, edges = _s3_amended_effective_post_effective()
    stale = _compile(events, edges, as_of="2026-08-09T12:00:00Z", generated_at="2026-08-10T12:00:00Z")

    with pytest.raises(RegistrationIntegrationRefusal) as excinfo:
        integrate_registration_paths(
            _lifecycle_inputs(stale, as_of="2026-08-09T12:00:00Z"),
            as_of=AS_OF, generated_at=GENERATED_AT,
        )
    assert "cannot be re-cut to another house-knowledge cutoff" in str(excinfo.value)


def test_source_selection_without_any_registration_binding_refuses():
    with pytest.raises(RegistrationIntegrationRefusal) as excinfo:
        integrate_registration_paths(CapitalInputs(bindings=()), as_of=AS_OF, generated_at=GENERATED_AT)
    assert "inputs carry no registration source" in str(excinfo.value)

    with pytest.raises(RegistrationIntegrationRefusal):
        integrate_registration_paths({"events": []}, as_of=AS_OF, generated_at=GENERATED_AT)

    events, edges = _s1_filed_amended_effective_withdrawn()
    inputs = CapitalInputs(
        bindings=(_binding("events", EVENT_SCHEMA, "supported", seed="a"),),
        events=tuple(events),
    )
    with pytest.raises(RegistrationIntegrationRefusal) as excinfo:
        integrate_registration_paths(inputs, as_of=AS_OF, generated_at=GENERATED_AT)
    assert "event_edges" in str(excinfo.value)


def test_source_selection_unavailable_binding_is_an_unavailable_family():
    inputs = CapitalInputs(
        bindings=(
            GenerationBinding("events", None, "unavailable", as_of=AS_OF),
            GenerationBinding("event_edges", None, "unavailable", as_of=AS_OF),
        ),
    )
    integration = integrate_registration_paths(inputs, as_of=AS_OF, generated_at=GENERATED_AT)

    assert integration.support == "unavailable"
    assert integration.paths == () and integration.deferred == ()
    assert integration.source_family == "events"
    assert integration.source_schema is None
    state = integration.family_state()
    assert state.provenance.support == "unavailable"
    assert state.provenance.input_schema is None
    assert state.records == ()
    assert state.unavailable == UNAVAILABLE
    assert set(integration.support_limits) >= {"offering_role_unknown", "replacement_not_extracted"}

    lifecycle_only = CapitalInputs(
        bindings=(GenerationBinding("registration_lifecycle", None, "not_built", as_of=AS_OF),),
    )
    other = integrate_registration_paths(lifecycle_only, as_of=AS_OF, generated_at=GENERATED_AT)
    assert other.support == "unavailable"
    assert other.source_family == "registration_lifecycle"
    assert other.paths == ()

    # Spec A.2(5): events bound supported beside an edges ledger BOUND as
    # unavailable is a bound-but-unavailable source, never a refusal and never a
    # compile over half the ledger pair.
    events, _edges = _s1_filed_amended_effective_withdrawn()
    half = CapitalInputs(
        bindings=(
            _binding("events", EVENT_SCHEMA, "supported", seed="a"),
            GenerationBinding("event_edges", None, "unavailable", as_of=AS_OF),
        ),
        events=tuple(events),
    )
    half_integration = integrate_registration_paths(half, as_of=AS_OF, generated_at=GENERATED_AT)
    assert half_integration.support == "unavailable"
    assert half_integration.source_family == "events"
    assert half_integration.paths == ()
    assert half_integration.family_state().unavailable == UNAVAILABLE


# ---------------------------------------------------------------------------
# A.5 case 8 -- the family state validates and the receipt binds its inputs
# ---------------------------------------------------------------------------


def test_family_state_validates_and_receipt_binds_inputs():
    events, edges = _s3_amended_effective_post_effective()
    integration = _integrate(events, edges, rule_pack=_stub_pack())
    state = integration.family_state()

    assert isinstance(state, FamilyState) and isinstance(state.provenance, FamilyProvenance)
    assert state.family == "registration" == state.provenance.family
    assert state.provenance.input_family == "events"
    assert state.provenance.input_schema == EVENT_SCHEMA
    assert state.provenance.support == "partial"
    assert state.provenance.compiler_version == REGISTRATION_INTEGRATION_VERSION
    assert state.provenance.as_of == AS_OF
    assert state.unavailable == UNAVAILABLE
    assert len(state.records) == len(integration.paths)

    record = state.as_record()
    provenance = record["provenance"]
    rebuilt = FamilyState(
        family=record["family"],
        provenance=FamilyProvenance(
            family=provenance["family"],
            input_family=provenance["input_family"],
            input_schema=provenance["input_schema"],
            support=provenance["support"],
            compiler_version=provenance["compiler_version"],
            generation_id=provenance["generation_id"],
            artifact_sha256=provenance["artifact_sha256"],
            support_limits=tuple(provenance["support_limits"]),
            as_of=provenance["as_of"],
            available_at=provenance["available_at"],
        ),
        records=tuple(record["records"]),
        unavailable=tuple(record["unavailable"]),
    )
    assert rebuilt.as_record() == record

    receipt = integration.receipt
    assert isinstance(receipt, CalculationReceipt)
    assert receipt.computed_at == GENERATED_AT
    assert receipt.implementation_digest == sha256_of({
        "contract": STATE_CONTRACT_VERSION,
        "implementation": REGISTRATION_INTEGRATION_VERSION,
    })
    events_binding = _binding("events", EVENT_SCHEMA, "supported", seed="a")
    assert receipt.input_digest == sha256_of({
        "events_binding": events_binding.as_record(),
        "event_edges_binding": _binding("event_edges", EDGE_SCHEMA, "supported", seed="b").as_record(),
        "as_of": AS_OF,
        "rule_pack_version": _stub_pack().version,
    })
    # A different accepted generation, or a different rule pack, is a different receipt.
    other_seed = _integrate(events, edges, event_seed="9", rule_pack=_stub_pack())
    assert other_seed.receipt.input_digest != receipt.input_digest
    assert _integrate(events, edges, rule_pack=None).receipt.rule_digest != receipt.rule_digest
    assert _integrate(events, edges, rule_pack=None).receipt.rule_digest == sha256_of("no_rule_pack")
    assert integration.as_record()["receipt"] == receipt.as_record()


# ---------------------------------------------------------------------------
# A.5 case 9 -- the shelf window is a rule bound, never an amount
# ---------------------------------------------------------------------------


def test_shelf_window_not_applicable_for_s1_and_unknown_without_415_a_5_text():
    textless = _stub_pack(with_rules=())
    s1_events, s1_edges = _s1_filed_amended_effective_withdrawn()
    s1_path = _integrate(s1_events, s1_edges, rule_pack=textless).paths[0]
    assert s1_path["predicates"]["shelf_window"] == {
        "status": "not_applicable",
        "evidence_event_ids": [],
        "evidence_accessions": [],
        "reason": "registration_family_not_a_shelf_family",
        "rule_ids": [],
    }

    s3_events, s3_edges = _s3_amended_effective_post_effective()
    window = _integrate(s3_events, s3_edges, rule_pack=textless).paths[0]["predicates"]["shelf_window"]
    assert window["status"] == "unknown"
    assert window["reason"] == "rule_415_a_5_text_not_in_rule_pack"
    assert "window_start" not in window and "window_end" not in window and "position" not in window


def test_a_pack_without_415_or_462_e_text_keeps_both_unknown():
    textless = _stub_pack(with_rules=())
    events, edges = _automatic_shelf_only()
    path = _integrate(events, edges, rule_pack=textless).paths[0]
    predicates = path["predicates"]

    assert predicates["automatic_shelf_form"]["status"] == "observed"
    assert predicates["automatic_effectiveness"] == {
        "status": "unknown",
        "evidence_event_ids": [events[0]["event_id"]],
        "evidence_accessions": ["0000000001-26-000021"],
        "reason": "rule_462_e_text_not_in_rule_pack",
        "rule_ids": [],
    }
    assert predicates["shelf_window"]["status"] == "unknown"
    assert predicates["shelf_window"]["reason"] == "rule_415_a_5_text_not_in_rule_pack"
    with pytest.raises(RuleApplicabilityError):
        textless.rule(RULE_415_A_5)
    with pytest.raises(RuleApplicabilityError):
        textless.rule(RULE_462_E)
    assert f"rule_text_not_in_pack:{RULE_415_A_5}" in _integrate(
        events, edges, rule_pack=textless
    ).support_limits


# ---------------------------------------------------------------------------
# A.5 case 10 -- the lifecycle record is embedded unchanged
# ---------------------------------------------------------------------------


def test_lifecycle_records_embed_unchanged():
    events, edges = _corrected_automatic_shelf_with_repeated_effect()
    bundle = _compile(events, edges, as_of=AS_OF, generated_at=GENERATED_AT)
    record = bundle["records"][0]
    path = _integrate(events, edges).paths[0]

    for name in ("issuer", "registration", "coverage"):
        assert path[name] == record[name], name
        assert path[name] is not record[name], f"{name} must be a deep copy"
    assert path["lifecycle_id"] == record["lifecycle_id"]
    assert path["lifecycle_generation_id"] == bundle["generation_id"]
    assert path["observed_registration_state"] == record["observed_registration_state"]
    assert path["as_of"] == record["as_of"] == AS_OF
    assert [item["event_id"] for item in path["intervals"]] == [
        item["event_id"] for item in record["timeline"]
    ]
    path["issuer"]["ticker"] = "MUTATED"
    path["registration"]["file_number"] = "MUTATED"
    assert record["issuer"]["ticker"] == "ABC"
    assert record["registration"]["file_number"] == "333-123"
    assert set(LIFECYCLE_UNAVAILABLE) <= set(UNAVAILABLE)


# ---------------------------------------------------------------------------
# The firewall: no forbidden property name in any key or any string value
# ---------------------------------------------------------------------------


def test_no_forbidden_property_name_in_any_key_or_string_value():
    fixtures = (
        _s1_filed_amended_effective_withdrawn(),
        _s3_amended_effective_post_effective(),
        _automatic_shelf_only(),
        _corrected_automatic_shelf_with_repeated_effect(),
        _scenario("post_withdrawal_effect"),
        _scenario("full_lifecycle"),
        _s3_effective_on("2024-03-01T10:00:00Z", seen_at="2024-03-01T18:00:00Z"),
    )
    seen = 0
    for events, edges in fixtures:
        for pack in (None, _stub_pack()):
            integration = _integrate(events, edges, rule_pack=pack)
            assert integration.paths, events[0]["filing"]["form"]
            seen += len(integration.paths)
            for record in (*integration.paths, *integration.deferred, integration.as_record()):
                for location, kind, token in _walk(record):
                    assert not FORBIDDEN_PROPERTY_PATTERN.match(token), f"{kind} {location}: {token!r}"
    assert seen >= 14


def test_offering_role_and_replaced_are_unknown_on_every_path():
    fixtures = (
        _s1_filed_amended_effective_withdrawn(),
        _s3_amended_effective_post_effective(),
        _automatic_shelf_only(),
        _corrected_automatic_shelf_with_repeated_effect(),
        _scenario("post_withdrawal_effect"),
        _scenario("full_lifecycle"),
        _s3_effective_on("2024-02-29T10:00:00Z", seen_at="2024-02-29T18:00:00Z"),
    )
    checked = 0
    for events, edges in fixtures:
        for pack in (None, _stub_pack()):
            for path in _integrate(events, edges, rule_pack=pack).paths:
                checked += 1
                role = path["predicates"]["offering_role"]
                assert (role["status"], role["value"]) == ("unknown", "unknown")
                assert role["reason"] == (
                    "no_accepted_content_evidence_lifecycle_carries_no_primary_or_resale_classification"
                )
                assert role["evidence_event_ids"] == [] and role["rule_ids"] == []
                replaced = path["predicates"]["replaced"]
                assert replaced["status"] == "unknown"
                assert replaced["reason"] == "rule_415_a_6_carry_forward_rows_not_extracted"
                assert replaced["evidence_event_ids"] == [] and replaced["rule_ids"] == []
                assert "primary_or_resale_classification" in path["unavailable"]
                assert "replacement_carry_forward_classification" in path["unavailable"]
    assert checked >= 14


def test_supersedes_edge_is_version_supersession_and_never_a_replacement():
    events, edges = _corrected_automatic_shelf_with_repeated_effect()
    supersedes = [edge for edge in edges if edge["relationship"] == "supersedes"]
    assert len(supersedes) == 1
    bundle = _compile(events, edges, as_of=AS_OF, generated_at=GENERATED_AT)
    assert supersedes[0]["edge_id"] in bundle["records"][0]["derivation_receipt"]["edge_ids"]

    path = _integrate(events, edges).paths[0]
    assert path["predicates"]["replaced"]["status"] == "unknown"
    assert path["predicates"]["replaced"]["evidence_event_ids"] == []
    assert path["origin"]["event_id"] == events[1]["event_id"]
    assert bundle["records"][0]["timeline"][0]["correction_version"] == 2
    assert path["predicates"]["filed"]["status"] == "observed"
    assert len(path["intervals"]) == len(bundle["records"][0]["timeline"])


# ---------------------------------------------------------------------------
# A qualified pack: the three-year window is a date bound with named conditions
# ---------------------------------------------------------------------------


def test_shelf_window_is_conditional_with_exact_dates_and_position():
    events, edges = _s3_effective_on("2024-03-01T10:00:00Z", seen_at="2024-03-01T18:00:00Z")
    pack = _stub_pack()

    inside = _integrate(events, edges, as_of="2026-10-14T00:00:00Z", generated_at="2026-10-14T06:00:00Z",
                        rule_pack=pack).paths[0]["predicates"]["shelf_window"]
    assert inside["status"] == "conditional"
    assert inside["window_start"] == "2024-03-01"
    assert inside["window_end"] == "2027-03-01"
    assert inside["position"] == "inside_window"
    assert inside["rule_ids"] == [RULE_415_A_5]
    assert inside["conditions"] == list(SHELF_WINDOW_CONDITIONS)
    assert inside["evidence_accessions"] == ["0000000001-26-000042"]
    assert WKSI_CONDITION not in inside["conditions"]

    after = _integrate(events, edges, as_of="2027-06-01T00:00:00Z", generated_at="2027-06-01T06:00:00Z",
                       rule_pack=pack).paths[0]["predicates"]["shelf_window"]
    assert after["status"] == "conditional"
    assert after["window_start"] == "2024-03-01"
    assert after["window_end"] == "2027-03-01"
    assert after["position"] == "after_window_end"
    for window in (inside, after):
        assert "amount" not in window and set(window) <= {
            "status", "evidence_event_ids", "evidence_accessions", "reason", "rule_ids",
            "window_start", "window_end", "position", "conditions",
        }



# ---------------------------------------------------------------------------
# SPEC_L1 B.5 cross-test -- the real rule pack 1.1.0 (L1b) qualifies the window
# ---------------------------------------------------------------------------


def test_b5_real_rule_pack_makes_the_s3_window_and_the_s3asr_effectiveness_conditional(repo_pack):
    """The repository pack, not a stub: L1b's 415(a)(5) and 462(e) text drive L1a.

    The rule state is read on the window-start (or filing) day, never on the
    ``as_of`` day: the eCFR served no edition after 2026-10-09, so 2026-10-14
    reads ``beyond_window`` while 2024-03-01 reads ``verified``.
    """
    assert repo_pack.version == "capital-structure-rule-applicability/1.2.0"
    assert rule_status_as_of(repo_pack, RULE_415_A_5, "2024-03-01").state == "verified"
    assert rule_status_as_of(repo_pack, RULE_415_A_5, "2026-10-14").state == "beyond_window"
    assert rule_status_as_of(repo_pack, RULE_462_E, "2026-08-01").state == "verified"

    events, edges = _s3_effective_on("2024-03-01T10:00:00Z", seen_at="2024-03-01T18:00:00Z")
    inside = _integrate(events, edges, as_of="2026-10-14T00:00:00Z", generated_at="2026-10-14T06:00:00Z",
                        rule_pack=repo_pack)
    window = inside.paths[0]["predicates"]["shelf_window"]
    assert window["status"] == "conditional"
    assert window["reason"] == "rule_415_a_5_window_conditional_on_unverified_requirements"
    assert window["rule_ids"] == [RULE_415_A_5]
    assert (window["window_start"], window["window_end"], window["position"]) == (
        "2024-03-01", "2027-03-01", "inside_window",
    )
    assert window["conditions"] == list(SHELF_WINDOW_CONDITIONS)
    assert f"rule_text_not_in_pack:{RULE_415_A_5}" not in inside.support_limits
    assert f"rule_text_not_in_pack:{RULE_462_E}" not in inside.support_limits
    assert inside.support == "partial"

    after = _integrate(events, edges, as_of="2027-06-01T00:00:00Z", generated_at="2027-06-01T06:00:00Z",
                       rule_pack=repo_pack).paths[0]["predicates"]["shelf_window"]
    assert after["status"] == "conditional"
    assert (after["window_start"], after["window_end"], after["position"]) == (
        "2024-03-01", "2027-03-01", "after_window_end",
    )

    asr_events, asr_edges = _automatic_shelf_only()
    asr = _integrate(asr_events, asr_edges, rule_pack=repo_pack).paths[0]["predicates"]
    assert asr["automatic_shelf_form"]["status"] == "observed"
    assert asr["automatic_effectiveness"]["status"] == "conditional"
    assert asr["automatic_effectiveness"]["reason"] == (
        "rule_462_e_effective_on_filing_if_wksi_at_determination_date_wksi_not_evaluated"
    )
    assert asr["automatic_effectiveness"]["rule_ids"] == [RULE_462_E]
    assert asr["shelf_window"]["status"] == "conditional"
    assert asr["shelf_window"]["conditions"] == [*SHELF_WINDOW_CONDITIONS, WKSI_CONDITION]
    assert asr["offering_role"]["status"] == "unknown"


def test_b5_real_rule_pack_leaves_a_window_starting_after_the_last_served_edition_unknown(repo_pack):
    """An EFFECT after the last served eCFR day (2026-10-09) cannot be qualified.

    The status is ``unknown``.  The reason is the frozen SPEC_L1 literal, which
    names missing text even though 1.1.0 carries the text and only the day is
    beyond its window; that naming is reported as a reviewed spec gap, not
    silently changed here.
    """
    events, edges = _s3_effective_on("2026-10-12T10:00:00Z", seen_at="2026-10-12T18:00:00Z")
    window = _integrate(events, edges, rule_pack=repo_pack).paths[0]["predicates"]["shelf_window"]
    assert rule_status_as_of(repo_pack, RULE_415_A_5, "2026-10-12").state == "beyond_window"
    assert window["status"] == "unknown"
    assert window["reason"] == "rule_415_a_5_text_not_in_rule_pack"
    assert "window_start" not in window and "window_end" not in window

def test_shelf_window_feb_29_start_clamps_to_feb_28():
    events, edges = _s3_effective_on("2024-02-29T10:00:00Z", seen_at="2024-02-29T18:00:00Z")
    window = _integrate(events, edges, rule_pack=_stub_pack()).paths[0]["predicates"]["shelf_window"]
    assert window["status"] == "conditional"
    assert window["window_start"] == "2024-02-29"
    assert window["window_end"] == "2027-02-28"
    assert window["position"] == "inside_window"


def test_automatic_shelf_window_starts_at_the_origin_filing_date():
    events, edges = _automatic_shelf_only()
    path = _integrate(events, edges, rule_pack=_stub_pack()).paths[0]
    effectiveness = path["predicates"]["automatic_effectiveness"]
    window = path["predicates"]["shelf_window"]

    assert effectiveness["status"] == "conditional"
    assert effectiveness["rule_ids"] == [RULE_462_E]
    assert effectiveness["reason"] == (
        "rule_462_e_effective_on_filing_if_wksi_at_determination_date_wksi_not_evaluated"
    )
    assert window["status"] == "conditional"
    assert window["window_start"] == "2026-08-01"
    assert window["window_end"] == "2029-08-01"
    assert window["position"] == "inside_window"
    assert window["conditions"] == [*SHELF_WINDOW_CONDITIONS, WKSI_CONDITION]
    assert window["evidence_event_ids"] == [events[0]["event_id"]]
    assert "wksi_eligibility" in path["unavailable"]
    assert "automatic_effectiveness_without_wksi_determination" in path["unavailable"]


def test_shelf_window_without_effectiveness_and_with_rule_text_is_unknown():
    original = _event(51, "S-3", accepted_at="2026-08-01T10:00:00Z", seen_at="2026-08-01T18:00:00Z")
    amendment = _event(52, "S-3/A", accepted_at="2026-08-02T10:00:00Z", seen_at="2026-08-02T18:00:00Z")
    events, edges = [original, amendment], [_edge(amendment, original, "amendment_of")]
    window = _integrate(events, edges, rule_pack=_stub_pack()).paths[0]["predicates"]["shelf_window"]
    assert window == {
        "status": "unknown",
        "evidence_event_ids": [],
        "evidence_accessions": [],
        "reason": "initial_effectiveness_not_observed",
        "rule_ids": [],
    }


def test_support_is_never_supported_and_names_its_limits(repo_pack):
    fixtures = (
        _s1_filed_amended_effective_withdrawn(),
        _automatic_shelf_only(),
        _scenario("post_withdrawal_effect"),
    )
    for events, edges in fixtures:
        for pack in (None, repo_pack, _stub_pack(), _stub_pack(with_rules=())):
            integration = _integrate(events, edges, rule_pack=pack)
            assert integration.support == "partial"
            assert integration.support != "supported"
            assert set(integration.support_limits) >= {"offering_role_unknown", "replacement_not_extracted"}
            assert integration.family_state().provenance.support == "partial"
            assert len(integration.support_limits) > 0
