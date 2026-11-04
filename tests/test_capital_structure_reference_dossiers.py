"""A0-0 gates: the six reference dossiers and their operand-traceability check.

The dossiers are parsed through the checker script's own parser (imported by
path), the identity/rule expectations are checked against the reference pack
through the engine's own ``load_reference_pack``/``identity_for``/rule
examples, the typed negative states are the frozen tuples from
``issuer_state_contracts``, and the fixture-bundle traceability run reuses the
U1a state-bundle suite's fixtures BY IMPORT.

Engine modules are imported through the real package via the checker's
``_engine_module`` (no stub fallback).
"""
from __future__ import annotations

from decimal import Decimal  # exact arithmetic only; never a binary approximation
import importlib.util
import json
from pathlib import Path
import re
import shutil

import pytest

import tests.test_capital_structure_state_bundle as state_suite

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "check_capital_structure_reference_dossiers.py"
REFERENCE_DIR = ROOT / "research" / "capital_structure" / "e2e_20261013" / "reference"
TICKERS = ("AIR", "CLNN", "QNCX", "WHK", "LPTH", "EDBL")
SCHEMA_LINE = "capital_structure.reference_dossier.v1"

_SPEC = importlib.util.spec_from_file_location(
    "check_capital_structure_reference_dossiers", SCRIPT_PATH,
)
checker = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(checker)

# Engine modules through the checker's own loader (the real package only).
_rq = checker._engine_module("reference_qualification")
_contracts = checker._engine_module("issuer_state_contracts")
PACK = _rq.load_reference_pack(ROOT / _rq.REFERENCE_PACK_RELPATH)

_TYPED_STATES = frozenset(
    (*_contracts.SUPPORT_STATES, *_contracts.QUANTITY_STATUSES,
     *_contracts.ROUTE_STATUSES, *_contracts.CONSTRAINT_STATUSES),
)

_VOCAB = re.compile(r"score|rank|probab|recommend|should (buy|sell)", re.IGNORECASE)


def _dossier_text(ticker: str) -> str:
    return (REFERENCE_DIR / f"{ticker}.md").read_text(encoding="utf-8")


def _dossiers() -> dict:
    return checker.load_dossiers(ROOT)


def test_a0_dossiers_have_the_fixed_shape():
    for ticker in TICKERS:
        text = _dossier_text(ticker)
        assert len(checker.YAML_FENCE.findall(text)) == 1, (
            f"{ticker}: exactly one fenced yaml block is required"
        )
        spec = checker.parse_dossier(text, ticker)
        assert spec["schema"] == SCHEMA_LINE
        for section in checker.SECTIONS:
            assert section in text, f"{ticker}: missing section {section!r}"
        assert len(spec["negatives"]) >= 2, f"{ticker}: at least two negatives"
        for row in spec["expectations"]:
            assert row.get("path_id"), f"{ticker}: expectation without path_id"
            for operand in row.get("operands") or ():
                assert operand.get("name"), f"{ticker}: operand without a name"


def test_a0_identities_match_the_reference_pack():
    dossiers = _dossiers()
    for ticker in TICKERS:
        identity = _rq.identity_for(PACK, ticker)
        spec = dossiers[ticker]
        assert spec["issuer_id"] == identity.issuer_id, ticker
        assert str(spec["cik"]) == identity.cik, ticker
        assert spec["registry_name"] == identity.registry_name, ticker
        assert spec["binding_status"] == identity.qualification, ticker
        # A dossier is keyed by its archetype.  A renamed registrant (G0-S
        # requalification, QNCX -> primary IRLA) keeps the archetype's ticker as
        # one the registry still lists for the same CIK.
        assert spec["ticker"] == identity.archetype == ticker, ticker
        assert ticker in tuple(identity.details.get("all_tickers") or (identity.ticker,)), ticker


def test_a0_expected_values_are_decimal_strings_with_unit_and_pack_rule():
    rule_ids, _pinned = checker._load_rule_pack_ids(ROOT)
    example_ids = {example.example_id for example in _rq.rule_examples(PACK)}
    # Rule-id sources, named: the active rule-applicability pack
    # (config/capital_structure_rule_applicability_pack.v1.json rules[].rule_id)
    # and the reference pack's rule_examples[].example_id. The RuleExample
    # dataclass carries example_id, not rule_id, so both id spaces are accepted.
    dossiers = _dossiers()
    with_value = 0
    for ticker, spec in dossiers.items():
        for row in spec["expectations"]:
            if row.get("expected") is None:
                assert row.get("gap"), f"{ticker}: a null expected needs a gap reason"
                continue
            with_value += 1
            Decimal(str(row["expected"]))  # raises unless it is a Decimal string
            assert str(row["unit"] or "").strip(), f"{ticker}/{row['path_id']}: unit"
            assert row.get("rule_id") in rule_ids or row.get("rule_example_id") in example_ids, (
                f"{ticker}/{row['path_id']}: rule id not in either active pack"
            )
    assert with_value >= 1, "at least one admitted expected value must exist"


def test_a0_negatives_name_typed_states_or_detail_text():
    dossiers = _dossiers()
    for ticker, spec in dossiers.items():
        for negative in spec["negatives"]:
            expect = str(negative.get("expect"))
            if expect.startswith("detail:"):
                continue
            assert expect in _TYPED_STATES, (
                f"{ticker}/{negative.get('name')}: {expect!r} is neither a typed "
                f"state member nor detail text"
            )
            if not expect.startswith("detail:"):
                assert negative.get("state"), (
                    f"{ticker}/{negative.get('name')}: name the frozen tuple"
                )


def test_a0_whk_is_withheld_by_construction():
    spec = _dossiers()["WHK"]
    assert spec["verdict_hint"] == "withheld"
    assert "whk_replacement_issuer" in spec["gap_ids"]
    for row in spec["expectations"]:
        assert row.get("expected") is None, (
            "WHK is withheld by construction: no number may be asserted"
        )


def test_a0_checker_reports_traceability_against_fixture_bundle(tmp_path):
    events, edges = state_suite._two_issuer_rows()
    rule_pack = state_suite.load_rule_applicability_pack()
    _generation, _projection, bundle = state_suite._built(
        events, edges,
        (state_suite.ISSUER_ONE, state_suite.ISSUER_TWO),
        rule_pack=rule_pack,
    )
    served_keys = sorted(state_suite._evidence_keys_of(bundle))
    assert served_keys, "the fixture bundle must publish at least one evidence key"
    missing_ref = "manifest:cs:" + "0" * 64 + "/root:" + "f" * 64
    assert missing_ref not in bundle["evidence_index"]
    dossier_markdown = (
        "# XYZ fixture dossier\n\n"
        "## Identity\n\nfixture\n\n"
        "## Source packet\n\nfixture\n\n"
        "## Mandatory numerical path\n\nfixture\n\n"
        "## Negatives\n\nfixture\n\n"
        "## J5 cutoff\n\nfixture\n\n"
        "## Findings\n\nnone\n\n"
        "```yaml\n"
        f"schema: {SCHEMA_LINE}\n"
        "ticker: XYZ\n"
        "issuer_id: sec:cik:0000000002\n"
        'cik: "0000000002"\n'
        "registry_name: XYZ fixture\n"
        "binding_status: qualified\n"
        "verdict_hint: accept\n"
        "gap_ids: []\n"
        'j5_cutoff: "2026-08-04"\n'
        "expectations:\n"
        "  - path_id: xyz:fixture_traceable_operand\n"
        "    family: registration\n"
        "    rule_id: form_s3.I.B.1\n"
        "    unit: count\n"
        '    expected: "1"\n'
        "    arithmetic: one filed registration\n"
        "    operands:\n"
        "      - name: filed_registration\n"
        f"        ref: {served_keys[0]}\n"
        "  - path_id: xyz:fixture_deliberately_missing_operand\n"
        "    family: registration\n"
        "    rule_id: form_s3.I.B.1\n"
        "    unit: count\n"
        '    expected: "1"\n'
        "    arithmetic: one operand the ledger never carried\n"
        "    operands:\n"
        "      - name: absent_operand\n"
        f"        ref: {missing_ref}\n"
        "negatives:\n"
        "  - name: fixture_route_without_witness\n"
        "    expect: unknown\n"
        "    state: ROUTE_STATUSES\n"
        "    reason: the fixture carries no rule-pack witness\n"
        "  - name: fixture_withheld_quantity\n"
        "    expect: detail:no number is asserted for the withheld family\n"
        "```\n"
    )
    spec = checker.parse_dossier(dossier_markdown, "XYZ")
    results = checker.evaluate_expectations({"XYZ": spec}, PACK, bundle)
    by_path = {row["path_id"]: row for row in results}
    assert by_path["xyz:fixture_traceable_operand"]["kind"] == "traceable"
    untraceable = by_path["xyz:fixture_deliberately_missing_operand"]
    assert untraceable["kind"] == "untraceable"
    assert missing_ref in untraceable["detail"]


def test_a0_checker_exits_3_when_bundle_absent(tmp_path, capsys):
    staging = tmp_path / "tree"
    shutil.copytree(ROOT / "config", staging / "config")
    shutil.copytree(REFERENCE_DIR, staging / REFERENCE_DIR.relative_to(ROOT))
    assert checker.main(["--root", str(staging), "--json"]) == 3
    payload = json.loads(capsys.readouterr().out)
    assert payload["message"] == "a0: real bundles absent on this tree"
    assert checker.main(["--root", str(staging)]) == 3
    assert capsys.readouterr().out.strip() == "a0: real bundles absent on this tree"


def test_a0_no_recommendation_vocabulary_in_dossiers():
    for ticker in TICKERS:
        text = _dossier_text(ticker)
        hit = _VOCAB.search(text)
        assert hit is None, f"{ticker}: recommendation vocabulary {hit.group(0)!r}"
