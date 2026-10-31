"""b1: governed not-presented (NP) pack + census-parity evaluator.

Synthetic linkbases only: no issuer bytes, no ticker/CIK literal. Every NP
verdict must be earned by an exact standard-only decomposition with no family
concept in calc, statement presentation or slot-context facts.
"""
from __future__ import annotations

import copy
from dataclasses import fields
from datetime import datetime, timezone
from decimal import Decimal
import hashlib

import pytest
import yaml

from engine.fundamental_forensics.metric_registry import (
    _content_digest,
    load_core_metric_registry,
)
from engine.fundamental_forensics.not_presented import (
    DEFAULT_NOT_PRESENTED_PACK_PATH,
    FOOTING_EXACT,
    FOOTING_OFF,
    NA_BASIS_NOT_PRESENTED_ITEM,
    NOT_PRESENTED_SCHEMA,
    NP_KIND_ITEM,
    REASON_ORDER,
    NotPresentedError,
    evaluate_not_presented,
    evaluate_not_presented_package,
    load_not_presented_pack,
    not_presented_pack_from_dict,
    parse_calculation_networks,
    parse_presentation_networks,
    verify_not_presented_evidence,
)

AFTER = datetime(2026, 10, 22, tzinfo=timezone.utc)
BEFORE = datetime(2026, 10, 20, 23, 59, 59, tzinfo=timezone.utc)
STATEMENT_ROLE = "http://ext.example/role/ConsolidatedBalanceSheets"
OPS_ROLE = "http://ext.example/role/ConsolidatedStatementsOfOperations"
DETAILS_ROLE = "http://ext.example/role/IntangibleAssetsDetails"
EVIDENCE_KEYS = {
    "na_basis",
    "np_kind",
    "np_rule_id",
    "np_rule_version",
    "np_rules_sha256",
    "np_parent_concepts",
    "np_roles_checked",
    "np_children_n",
    "np_children_with_fact_n",
    "np_footing",
    "np_cal_sha256",
    "np_pre_sha256",
    "np_accession",
}


def _href(qname: str) -> str:
    prefix, local = qname.split(":", 1)
    if prefix == "us-gaap":
        return f"http://xbrl.fasb.org/us-gaap/2024/elts/us-gaap-2024.xsd#us-gaap_{local}"
    return f"{prefix}-20241231.xsd#{prefix}_{local}"


def calc_xml(links: list[tuple[str, list[tuple[str, str, str]]]]) -> bytes:
    parts = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase" '
        'xmlns:xlink="http://www.w3.org/1999/xlink">',
    ]
    for role, arcs in links:
        parts.append(f'<link:calculationLink xlink:type="extended" xlink:role="{role}">')
        labels: dict[str, str] = {}
        for parent, child, _weight in arcs:
            for concept in (parent, child):
                if concept not in labels:
                    labels[concept] = f"loc_{len(labels)}"
                    parts.append(
                        f'<link:loc xlink:type="locator" xlink:href="{_href(concept)}" '
                        f'xlink:label="{labels[concept]}"/>'
                    )
        for order, (parent, child, weight) in enumerate(arcs, 1):
            parts.append(
                '<link:calculationArc xlink:type="arc" '
                'xlink:arcrole="http://www.xbrl.org/2003/arcrole/summation-item" '
                f'xlink:from="{labels[parent]}" xlink:to="{labels[child]}" '
                f'order="{order}" weight="{weight}"/>'
            )
        parts.append("</link:calculationLink>")
    parts.append("</link:linkbase>")
    return "\n".join(parts).encode("utf-8")


def pre_xml(links: list[tuple[str, list[str]]]) -> bytes:
    parts = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase" '
        'xmlns:xlink="http://www.w3.org/1999/xlink">',
    ]
    for role, concepts in links:
        parts.append(f'<link:presentationLink xlink:type="extended" xlink:role="{role}">')
        for index, concept in enumerate(concepts):
            parts.append(
                f'<link:loc xlink:type="locator" xlink:href="{_href(concept)}" xlink:label="p_{index}"/>'
            )
        for index in range(1, len(concepts)):
            parts.append(
                '<link:presentationArc xlink:type="arc" '
                'xlink:arcrole="http://www.xbrl.org/2003/arcrole/parent-child" '
                f'xlink:from="p_0" xlink:to="p_{index}" order="{index}"/>'
            )
        parts.append("</link:presentationLink>")
    parts.append("</link:linkbase>")
    return "\n".join(parts).encode("utf-8")


@pytest.fixture(scope="module")
def pack():
    return load_not_presented_pack()


@pytest.fixture(scope="module")
def raw_pack():
    return yaml.safe_load(DEFAULT_NOT_PRESENTED_PACK_PATH.read_text(encoding="utf-8"))


# A balance sheet whose Assets decomposes exactly into standard non-intangible lines.
BS_ARCS = [
    ("us-gaap:Assets", "us-gaap:AssetsCurrent", "1"),
    ("us-gaap:Assets", "us-gaap:PropertyPlantAndEquipmentNet", "1"),
    ("us-gaap:Assets", "us-gaap:OtherAssetsNoncurrent", "1"),
]
BS_FACTS = {
    "us-gaap:Assets": Decimal("1000000"),
    "us-gaap:AssetsCurrent": Decimal("600000"),
    "us-gaap:PropertyPlantAndEquipmentNet": Decimal("300000"),
    "us-gaap:OtherAssetsNoncurrent": Decimal("100000"),
    "us-gaap:Liabilities": Decimal("400000"),
}
BS_PRE = [
    (
        STATEMENT_ROLE,
        [
            "us-gaap:StatementOfFinancialPositionAbstract",
            "us-gaap:Assets",
            "us-gaap:AssetsCurrent",
            "us-gaap:PropertyPlantAndEquipmentNet",
            "us-gaap:OtherAssetsNoncurrent",
            "us-gaap:Liabilities",
        ],
    ),
    # A details role naming an intangible concept is excluded from the statement guard.
    (DETAILS_ROLE, ["us-gaap:Assets", "us-gaap:FiniteLivedIntangibleAssetsNet"]),
]


def _evaluate(pack, metric_id, *, arcs, facts, pre=BS_PRE, recorded_at=AFTER, accession="0000000000-24-000001"):
    return evaluate_not_presented_package(
        pack,
        metric_id,
        calculation=calc_xml([(STATEMENT_ROLE, arcs)]),
        presentation=pre_xml(pre),
        facts_in_context=facts,
        recorded_at=recorded_at,
        accession=accession,
    )


# ------------------------------------------------------------------ pack --


def test_pack_loads_governed_item_rules_bound_to_catalog(pack, raw_pack):
    registry = load_core_metric_registry()
    catalog_ids = {contract.metric_id for contract in registry.contracts}
    bound = load_not_presented_pack(known_metric_ids=catalog_ids)
    assert bound.content_sha256 == pack.content_sha256 == _content_digest(raw_pack)
    assert raw_pack["schema"] == NOT_PRESENTED_SCHEMA
    assert len(pack.rules) == 19
    assert set(pack.rules) <= catalog_ids
    assert pack.na_basis == NA_BASIS_NOT_PRESENTED_ITEM
    assert {rule.np_kind for rule in pack.rules.values()} == {NP_KIND_ITEM}
    for metric_id, rule in pack.rules.items():
        assert rule.rule.rule_id == f"not_presented.{metric_id}/v1"
        assert rule.rule.available_at == pack.available_at
        assert all(member.startswith("us-gaap:") for tier in rule.parent_tiers for member in tier)


def test_intangible_rule_is_narrowed_to_finite_lived(pack):
    family = pack.rules["intangible_assets_net"].family_re
    for name in (
        "IndefiniteLivedIntangibleAssetsExcludingGoodwill",
        "IndefiniteLivedTradeNames",
        "IndefiniteLivedTrademarks",
        "OtherIndefiniteLivedIntangibleAssets",
        "IndefiniteLivedFranchiseRights",
    ):
        assert family.search(name) is None, name
    for name in ("FiniteLivedIntangibleAssetsNet", "IntangibleAssetsNetExcludingGoodwill", "FiniteLivedPatentsGross"):
        assert family.search(name) is not None, name


def test_digest_tamper_is_refused(raw_pack):
    tampered = copy.deepcopy(raw_pack)
    tampered["rules"][0]["family_pattern"] = "(Nothing)"
    with pytest.raises(ValueError, match="content_sha256"):
        not_presented_pack_from_dict(tampered)


def _redigest(raw):
    raw = dict(raw)
    raw["content_sha256"] = _content_digest(raw)
    return raw


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda raw: raw.__setitem__("extra", 1), "unsupported field"),
        (lambda raw: raw["rules"][0].__setitem__("np_kind", "subtotal_not_in_composition"), "np_kind"),
        (lambda raw: raw["rules"][0].__setitem__("family_pattern", "(unclosed"), "regular expression"),
        (lambda raw: raw["rules"][0]["rule"].__setitem__("rule_id", "not_presented.other/v1"), "rule_id"),
        (lambda raw: raw["rules"][0].__setitem__("parent_tiers", [["Assets"]]), "prefixed concept"),
        (lambda raw: raw.__setitem__("na_basis", "class_policy"), "na_basis"),
        (lambda raw: raw["rules"].append(copy.deepcopy(raw["rules"][0])), "repeats metric"),
        (lambda raw: raw["rules"][0].__setitem__("value", 0), "unsupported field"),
    ],
)
def test_pack_validation_fails_closed(raw_pack, mutate, message):
    raw = copy.deepcopy(raw_pack)
    mutate(raw)
    with pytest.raises(ValueError, match=message):
        not_presented_pack_from_dict(_redigest(raw))


def test_unknown_metric_is_refused_against_the_catalog(raw_pack):
    with pytest.raises(NotPresentedError, match="not a catalog metric"):
        not_presented_pack_from_dict(raw_pack, known_metric_ids={"revenue"})


# ------------------------------------------------------------------ pass --


def test_item_not_presented_passes_with_exact_footing(pack):
    verdict = _evaluate(pack, "intangible_assets_net", arcs=BS_ARCS, facts=BS_FACTS)
    assert verdict.is_not_presented, verdict.fails
    assert verdict.fails == ()
    assert verdict.np_kind == NP_KIND_ITEM
    assert verdict.na_basis == NA_BASIS_NOT_PRESENTED_ITEM
    assert verdict.footing == FOOTING_EXACT
    assert verdict.parent_concepts == ("us-gaap:Assets",)
    assert (verdict.roles_checked, verdict.children_n, verdict.children_with_fact_n) == (1, 3, 3)
    evidence = verdict.evidence()
    assert set(evidence) == EVIDENCE_KEYS
    assert evidence["np_rule_id"] == "not_presented.intangible_assets_net/v1"
    assert evidence["np_rules_sha256"] == pack.content_sha256
    assert evidence["np_cal_sha256"] == hashlib.sha256(calc_xml([(STATEMENT_ROLE, BS_ARCS)])).hexdigest()
    assert evidence["np_pre_sha256"] == hashlib.sha256(pre_xml(BS_PRE)).hexdigest()
    assert evidence["np_accession"] == "0000000000-24-000001"


def test_indefinite_lived_child_no_longer_blocks_the_intangible_verdict(pack):
    arcs = [
        ("us-gaap:Assets", "us-gaap:AssetsCurrent", "1"),
        ("us-gaap:Assets", "us-gaap:PropertyPlantAndEquipmentNet", "1"),
        ("us-gaap:Assets", "us-gaap:IndefiniteLivedIntangibleAssetsExcludingGoodwill", "1"),
    ]
    facts = {
        "us-gaap:Assets": Decimal("1000000"),
        "us-gaap:AssetsCurrent": Decimal("600000"),
        "us-gaap:PropertyPlantAndEquipmentNet": Decimal("300000"),
        "us-gaap:IndefiniteLivedIntangibleAssetsExcludingGoodwill": Decimal("100000"),
    }
    pre = [(STATEMENT_ROLE, ["us-gaap:Assets", "us-gaap:IndefiniteLivedIntangibleAssetsExcludingGoodwill"])]
    verdict = _evaluate(pack, "intangible_assets_net", arcs=arcs, facts=facts, pre=pre)
    assert verdict.is_not_presented, verdict.fails


def test_container_recursion_and_negative_weights_pass(pack):
    # cost_of_revenue: tier-2 totals, a container child recursed into.
    arcs = [
        ("us-gaap:CostsAndExpenses", "us-gaap:SellingGeneralAndAdministrativeExpense", "1"),
        ("us-gaap:CostsAndExpenses", "us-gaap:OperatingCostsAndExpenses", "1"),
        ("us-gaap:OperatingCostsAndExpenses", "us-gaap:ResearchAndDevelopmentExpense", "1"),
        ("us-gaap:OperatingCostsAndExpenses", "us-gaap:OtherCostAndExpenseOperating", "1"),
    ]
    facts = {
        "us-gaap:CostsAndExpenses": Decimal("900"),
        "us-gaap:SellingGeneralAndAdministrativeExpense": Decimal("500"),
        "us-gaap:OperatingCostsAndExpenses": Decimal("400"),
        "us-gaap:ResearchAndDevelopmentExpense": Decimal("250.4"),
        "us-gaap:OtherCostAndExpenseOperating": Decimal("149.6"),
    }
    pre = [(OPS_ROLE, ["us-gaap:IncomeStatementAbstract", "us-gaap:CostOfRevenueAbstract", "us-gaap:CostsAndExpenses"])]
    verdict = _evaluate(pack, "cost_of_revenue", arcs=arcs, facts=facts, pre=pre)
    assert verdict.is_not_presented, verdict.fails
    assert verdict.parent_concepts == ("us-gaap:CostsAndExpenses", "us-gaap:OperatingCostsAndExpenses")
    assert verdict.roles_checked == 3  # parent link, recursed container link, second parent link

    # income_tax_expense_benefit: a filer with no tax line; weight -1 child.
    arcs = [
        ("us-gaap:NetIncomeLoss", "us-gaap:OperatingIncomeLoss", "1"),
        ("us-gaap:NetIncomeLoss", "us-gaap:InterestExpense", "-1"),
    ]
    facts = {
        "us-gaap:NetIncomeLoss": Decimal("70"),
        "us-gaap:OperatingIncomeLoss": Decimal("100"),
        "us-gaap:InterestExpense": Decimal("30"),
    }
    verdict = _evaluate(pack, "income_tax_expense_benefit", arcs=arcs, facts=facts, pre=[(OPS_ROLE, ["us-gaap:NetIncomeLoss"])])
    assert verdict.is_not_presented, verdict.fails


# ------------------------------------------------------------------ fail --


def _fails(verdict):
    assert not verdict.is_not_presented
    assert verdict.np_kind is None and verdict.na_basis is None
    with pytest.raises(NotPresentedError):
        verdict.evidence()
    return verdict.fails


def test_fail_extension_child_lists_the_residual(pack):
    arcs = BS_ARCS[:2] + [("us-gaap:Assets", "ext:OtherLongLivedAssets", "1")]
    facts = dict(BS_FACTS, **{"ext:OtherLongLivedAssets": Decimal("100000")})
    del facts["us-gaap:OtherAssetsNoncurrent"]
    verdict = _evaluate(pack, "intangible_assets_net", arcs=arcs, facts=facts)
    assert _fails(verdict) == ("np_extension_child",)
    assert verdict.extension_children == ("ext:OtherLongLivedAssets",)
    assert verdict.footing == FOOTING_EXACT


def test_fail_family_in_calc(pack):
    arcs = BS_ARCS[:2] + [("us-gaap:Assets", "us-gaap:FiniteLivedIntangibleAssetsNet", "1")]
    facts = dict(BS_FACTS)
    facts.pop("us-gaap:OtherAssetsNoncurrent")
    verdict = _evaluate(pack, "intangible_assets_net", arcs=arcs, facts=facts)
    assert "np_family_in_calc" in _fails(verdict)


def test_fail_non_decomposing_container(pack):
    arcs = [
        ("us-gaap:CostsAndExpenses", "us-gaap:SellingGeneralAndAdministrativeExpense", "1"),
        ("us-gaap:CostsAndExpenses", "us-gaap:OperatingCostsAndExpenses", "1"),
    ]
    facts = {
        "us-gaap:CostsAndExpenses": Decimal("900"),
        "us-gaap:SellingGeneralAndAdministrativeExpense": Decimal("500"),
        "us-gaap:OperatingCostsAndExpenses": Decimal("400"),
    }
    verdict = _evaluate(pack, "cost_of_revenue", arcs=arcs, facts=facts, pre=[(OPS_ROLE, ["us-gaap:CostsAndExpenses"])])
    assert _fails(verdict) == ("np_container_leaf",)


def test_fail_children_without_facts(pack):
    facts = {"us-gaap:Assets": Decimal("1000000")}
    verdict = _evaluate(pack, "intangible_assets_net", arcs=BS_ARCS, facts=facts)
    assert _fails(verdict) == ("np_children_no_facts",)
    assert verdict.footing is None


def test_fail_off_by_one_footing(pack):
    facts = dict(BS_FACTS, **{"us-gaap:OtherAssetsNoncurrent": Decimal("100001")})
    verdict = _evaluate(pack, "intangible_assets_net", arcs=BS_ARCS, facts=facts)
    assert _fails(verdict) == ("np_unbalanced",)
    assert verdict.footing == FOOTING_OFF
    assert verdict.off_units == 1


def test_fail_unbalanced_reports_off_units_at_the_common_grain(pack):
    facts = dict(BS_FACTS, **{"us-gaap:OtherAssetsNoncurrent": Decimal("70000")})
    verdict = _evaluate(pack, "intangible_assets_net", arcs=BS_ARCS, facts=facts)
    assert _fails(verdict) == ("np_unbalanced",)
    assert verdict.off_units == 3  # 30,000 short at a 10,000 grain


def test_fail_family_in_statement_presentation(pack):
    pre = [(STATEMENT_ROLE, ["us-gaap:Assets", "us-gaap:IntangibleAssetsNetExcludingGoodwill"])]
    verdict = _evaluate(pack, "intangible_assets_net", arcs=BS_ARCS, facts=BS_FACTS, pre=pre)
    assert _fails(verdict) == ("np_family_in_statement_pre",)


def test_fail_family_fact_in_slot_context(pack):
    facts = dict(BS_FACTS, **{"ext:CustomerRelationshipsNet": Decimal("5")})
    verdict = _evaluate(pack, "intangible_assets_net", arcs=BS_ARCS, facts=facts)
    assert _fails(verdict) == ("np_family_fact",)


def test_fail_no_parent_without_a_parent_fact(pack):
    facts = dict(BS_FACTS)
    facts.pop("us-gaap:Assets")
    verdict = _evaluate(pack, "intangible_assets_net", arcs=BS_ARCS, facts=facts)
    assert _fails(verdict) == ("np_no_parent",)


def test_reasons_are_reported_in_census_order(pack):
    arcs = [
        ("us-gaap:Assets", "ext:OtherLongLivedAssets", "1"),
        ("us-gaap:Assets", "us-gaap:FiniteLivedIntangibleAssetsNet", "1"),
    ]
    facts = {"us-gaap:Assets": Decimal("10"), "us-gaap:FiniteLivedIntangibleAssetsNet": Decimal("3")}
    verdict = _evaluate(pack, "intangible_assets_net", arcs=arcs, facts=facts)
    assert _fails(verdict) == ("np_extension_child", "np_family_in_calc", "np_unbalanced", "np_family_fact")
    assert list(verdict.fails) == [reason for reason in REASON_ORDER if reason in verdict.fails]


# ------------------------------------------------- visibility and inputs --


def test_rule_is_invisible_before_its_available_at(pack):
    verdict = _evaluate(pack, "intangible_assets_net", arcs=BS_ARCS, facts=BS_FACTS, recorded_at=BEFORE)
    assert _fails(verdict) == ("np_no_rule",)


def test_metric_without_a_rule_stays_absent(pack):
    verdict = _evaluate(pack, "revenue", arcs=BS_ARCS, facts=BS_FACTS)
    assert _fails(verdict) == ("np_no_rule",)


def test_missing_or_hostile_linkbases_stay_absent(pack):
    common = dict(facts_in_context=BS_FACTS, recorded_at=AFTER, accession="0000000000-24-000001")
    calc = calc_xml([(STATEMENT_ROLE, BS_ARCS)])
    pre = pre_xml(BS_PRE)
    missing_calc = evaluate_not_presented_package(pack, "goodwill", calculation=None, presentation=pre, **common)
    assert _fails(missing_calc) == ("np_no_calc_linkbase",)
    missing_pre = evaluate_not_presented_package(pack, "goodwill", calculation=calc, presentation=b"", **common)
    assert _fails(missing_pre) == ("np_no_presentation_linkbase",)
    dtd = b'<!DOCTYPE x [<!ENTITY e "e">]><x/>'
    hostile = evaluate_not_presented_package(pack, "goodwill", calculation=dtd, presentation=pre, **common)
    assert _fails(hostile) == ("np_parse_error",)
    bad_weight = calc.replace(b'weight="1"', b'weight="one"', 1)
    unparsable = evaluate_not_presented_package(pack, "goodwill", calculation=bad_weight, presentation=pre, **common)
    assert _fails(unparsable) == ("np_parse_error",)


def test_non_decimal_fact_values_are_refused(pack):
    rule = pack.rules["goodwill"]
    with pytest.raises(NotPresentedError, match="finite Decimal"):
        evaluate_not_presented(
            pack,
            rule,
            calculation=parse_calculation_networks(calc_xml([(STATEMENT_ROLE, BS_ARCS)])),
            presentation=parse_presentation_networks(pre_xml(BS_PRE)),
            facts_in_context={"us-gaap:Assets": 1000000.0},
        )


def test_verdict_has_no_value_field(pack):
    names = {field.name for field in fields(type(_evaluate(pack, "goodwill", arcs=BS_ARCS, facts=BS_FACTS)))}
    assert not {"value", "val", "amount"} & names


# ------------------------------------------------------- recomputation --


def test_evidence_recomputes_from_package_bytes_and_refuses_tamper(pack):
    calc = calc_xml([(STATEMENT_ROLE, BS_ARCS)])
    pre = pre_xml(BS_PRE)
    verdict = _evaluate(pack, "goodwill", arcs=BS_ARCS, facts=BS_FACTS)
    evidence = verdict.evidence()
    kwargs = dict(calculation=calc, presentation=pre, facts_in_context=BS_FACTS, recorded_at=AFTER)
    verify_not_presented_evidence(pack, "goodwill", evidence, **kwargs)

    tampered = dict(evidence, np_cal_sha256="0" * 64)
    with pytest.raises(NotPresentedError, match="does not match"):
        verify_not_presented_evidence(pack, "goodwill", tampered, **kwargs)

    changed_bytes = dict(kwargs, calculation=calc + b"\n")
    with pytest.raises(NotPresentedError, match="does not match"):
        verify_not_presented_evidence(pack, "goodwill", evidence, **changed_bytes)

    added_family = dict(kwargs, facts_in_context=dict(BS_FACTS, **{"us-gaap:Goodwill": Decimal("1")}))
    with pytest.raises(NotPresentedError, match="does not recompute"):
        verify_not_presented_evidence(pack, "goodwill", evidence, **added_family)

    with pytest.raises(NotPresentedError, match="does not recompute"):
        verify_not_presented_evidence(pack, "goodwill", evidence, **dict(kwargs, recorded_at=BEFORE))
