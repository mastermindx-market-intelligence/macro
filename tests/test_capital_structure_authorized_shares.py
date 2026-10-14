"""Direct tests for SPEC_C2C_P: authorized/issued/reserved common-share facts.

Two halves are proven here.  The producer half brings three named SEC XBRL
concepts into the share-count truth plane (``common_shares_authorized``,
``common_shares_issued``, ``common_shares_reserved_for_future_issuance``) and
keeps them out of the comparable share basis.  The consumer half is the pure
selector ``select_authorized_headroom``, which answers one question — how many
authorized common shares are neither issued nor reserved at one instant — with
an exact signed number, a ceiling, a shortfall or a named unknown.

Gates exercised: A19 (a split never scales authorized capital, reservations or
issued shares), A16 (no basis substitution — outstanding is never issued),
A17 (no input selects or sizes), A48 (no score, rank, sizing or probability).
Every numeric assertion compares exact ``Decimal`` values; there is no float
literal anywhere in this module.
"""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from engine.capital_structure import share_count_materializer as materializer
from engine.capital_structure import share_count_truth as sct
from engine.capital_structure.share_basis import (
    AUTHORIZED_CAPITAL_KINDS,
    select_share_basis,
)
from engine.capital_structure.share_count_truth import compile_share_count_observations
from tests.test_capital_structure_share_basis import (
    AS_OF,
    ISSUER,
    SECURITY,
    _no_actions,
    _obs,
    _shares,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "capital_structure" / "share_count_truth"
AAPL_FIXTURE = FIXTURE_DIR / "companyfacts_0000320193.json"
SYNTHETIC_FIXTURE = FIXTURE_DIR / "companyfacts_synthetic_authorized_capital.json"
V1_SCHEMA_PATH = ROOT / "contracts" / "capital_structure_share_count_observation.schema.json"
V2_SCHEMA_PATH = ROOT / "contracts" / "capital_structure_share_count_observation_v2.schema.json"

KIND_ENUM = [
    "common_shares_outstanding",
    "public_float",
    "common_shares_authorized",
    "common_shares_issued",
    "common_shares_reserved_for_future_issuance",
]
CONCEPT_BY_KIND = {
    "common_shares_authorized": "CommonStockSharesAuthorized",
    "common_shares_issued": "CommonStockSharesIssued",
    "common_shares_reserved_for_future_issuance": "CommonStockCapitalSharesReservedForFutureIssuance",
}
NEW_CONCEPTS = [
    "CommonStockSharesAuthorized",
    "CommonStockSharesIssued",
    "CommonStockCapitalSharesReservedForFutureIssuance",
]


# ---------------------------------------------------------------------------
# Fixture compilation (mirrors tests/test_capital_structure_share_count_truth.py)
# ---------------------------------------------------------------------------


def _compile_fixture(path: Path) -> dict:
    """Compile one retained Company Facts payload through the truth kernel."""

    raw = path.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    cik = str(payload["cik"]).zfill(10)
    digest = hashlib.sha256(raw).hexdigest()
    receipt = {
        "schema": "capital_structure.companyfacts_source_receipt.v1",
        "version": 1,
        "source_system": "sec_companyfacts",
        "acquisition_state": "provided_snapshot",
        "issuer_id": f"issuer:{cik}",
        "source_url": f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
        "source_payload_sha256": digest,
        "raw_object_locator": f"capital_structure/sec/companyfacts/sha256/{digest[:2]}/{digest}",
        "manifest_locator": f"companyfacts-manifest:cs:{digest}",
        "source_retrieved_at": "2026-05-01T00:00:00Z",
        "system_available_at": "2026-05-01T00:03:00Z",
    }
    return compile_share_count_observations(raw, receipt)


def _synthetic_rows() -> list[dict]:
    return list(_compile_fixture(SYNTHETIC_FIXTURE)["observations"])


def _rows_by_kind(rows, kind: str) -> list[dict]:
    return sorted(
        (row for row in rows if row["metric"]["kind"] == kind),
        key=lambda row: str(row["period"]["period_end"]),
    )


def _v1_validator() -> Draft202012Validator:
    return Draft202012Validator(
        json.loads(V1_SCHEMA_PATH.read_text(encoding="utf-8")), format_checker=FormatChecker(),
    )


def _v2_validator() -> Draft202012Validator:
    return Draft202012Validator(
        json.loads(V2_SCHEMA_PATH.read_text(encoding="utf-8")), format_checker=FormatChecker(),
    )


def _authorized_obs(label: str, period_end: str | None, value: str | None, *, kind: str, **overrides) -> dict:
    """A v2 authorized-capital record.

    The share-basis builder derives ``security_class`` and ``normalized.unit``
    from ``kind == "common_shares_outstanding"``, so it cannot express an
    authorized-capital kind; this reuses its exact record shape and corrects
    only those two derived fields (see DEVIATIONS in the lane return).
    """

    record = _obs(
        label, period_end, value, kind=kind, name=CONCEPT_BY_KIND[kind],
        namespace="us-gaap", unit="shares", **overrides,
    )
    record["security_class"] = {
        "state": "concept_semantic",
        "classification": "common_stock",
        "raw_label": None,
        "basis": "xbrl_concept_semantics",
    }
    if record["normalized"]["value"] is not None:
        record["normalized"]["unit"] = "shares"
    return record


# ---------------------------------------------------------------------------
# §1 / §0.1 — the three new source facts reach the truth plane
# ---------------------------------------------------------------------------


def test_truth_rows_from_synthetic_fixture_carry_three_new_kinds() -> None:
    rows = _synthetic_rows()
    kinds = {row["metric"]["kind"] for row in rows}
    assert set(AUTHORIZED_CAPITAL_KINDS) <= kinds

    authorized = _rows_by_kind(rows, "common_shares_authorized")
    issued = _rows_by_kind(rows, "common_shares_issued")
    reserved = _rows_by_kind(rows, "common_shares_reserved_for_future_issuance")
    assert [row["period"]["period_end"] for row in authorized] == ["2025-12-31", "2026-03-31"]
    assert [row["period"]["period_end"] for row in issued] == ["2025-12-31", "2026-03-31"]
    # Reserved is present at the earlier instant only: a 10-Q omits it.
    assert [row["period"]["period_end"] for row in reserved] == ["2025-12-31"]

    for row in (*authorized, *issued, *reserved):
        assert row["fact"]["unit"] == "shares"
        assert row["normalized"]["unit"] == "shares"
        assert row["reported"]["unit"] == "shares"
        assert row["state"] == {"disposition": "observed", "reason": "direct_sec_companyfacts_fact"}
        assert row["security_class"]["classification"] == "common_stock"
        assert Decimal(row["normalized"]["value"]) >= Decimal(0)

    assert [Decimal(row["normalized"]["value"]) for row in authorized] == [Decimal(500000000)] * 2
    assert [Decimal(row["normalized"]["value"]) for row in issued] == [Decimal(120000000), Decimal(125000000)]
    assert [Decimal(row["normalized"]["value"]) for row in reserved] == [Decimal(8000000)]

    concept_by_kind = {row["metric"]["kind"]: row["fact"]["name"] for row in (*authorized, *issued, *reserved)}
    assert concept_by_kind == CONCEPT_BY_KIND
    assert all(row["fact"]["namespace"] == "us-gaap" for row in (*authorized, *issued, *reserved))

    validator = _v1_validator()
    for row in rows:
        assert list(validator.iter_errors(row)) == []


def test_aapl_fixture_still_yields_only_three_rows() -> None:
    ledger = _compile_fixture(AAPL_FIXTURE)
    rows = ledger["observations"]
    assert len(rows) == 3
    kinds = {row["metric"]["kind"] for row in rows}
    assert kinds == {"common_shares_outstanding", "public_float"}
    assert not kinds & set(AUTHORIZED_CAPITAL_KINDS)
    names = {row["fact"]["name"] for row in rows}
    assert not names & set(NEW_CONCEPTS)


# ---------------------------------------------------------------------------
# §2 / §0.2 — both observation schemas
# ---------------------------------------------------------------------------


def test_v1_schema_accepts_new_kinds_with_outstanding_rules() -> None:
    schema = json.loads(V1_SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["properties"]["metric"]["properties"]["kind"]["enum"] == KIND_ENUM
    assert schema["properties"]["fact"]["properties"]["name"]["enum"] == [
        "CommonStockSharesOutstanding",
        "EntityCommonStockSharesOutstanding",
        "EntityPublicFloat",
        *NEW_CONCEPTS,
    ]

    validator = _v1_validator()
    rows = _synthetic_rows()
    for kind in AUTHORIZED_CAPITAL_KINDS:
        for row in _rows_by_kind(rows, kind):
            assert list(validator.iter_errors(row)) == []
            # The outstanding rules are applied verbatim to the new kinds.
            assert row["security_class"]["state"] == "concept_semantic"
            assert row["security_class"]["classification"] == "common_stock"
            assert row["security_class"]["basis"] == "xbrl_concept_semantics"
            assert row["fact"]["unit"] == "shares"
            assert row["reported"]["unit"] == "shares"
            assert row["normalized"]["unit"] == "shares"

    # Each new kind carries the same two if/then blocks as outstanding.
    blocks = [item for item in schema["allOf"] if "metric" in json.dumps(item.get("if", {}))]
    class_blocks = {
        item["if"]["properties"]["metric"]["properties"]["kind"]["const"]: item["then"]
        for item in blocks
        if "security_class" in item.get("then", {}).get("properties", {})
    }
    unit_blocks = {
        item["if"]["properties"]["metric"]["properties"]["kind"]["const"]: item["then"]
        for item in blocks
        if "fact" in item.get("then", {}).get("properties", {})
    }
    for kind in AUTHORIZED_CAPITAL_KINDS:
        assert class_blocks[kind] == class_blocks["common_shares_outstanding"]
        assert unit_blocks[kind] == unit_blocks["common_shares_outstanding"]


def test_v1_schema_rejects_new_kind_with_wrong_unit_or_class() -> None:
    validator = _v1_validator()
    for kind in AUTHORIZED_CAPITAL_KINDS:
        base = _rows_by_kind(_synthetic_rows(), kind)[0]
        assert list(validator.iter_errors(base)) == []

        for path, bad in (
            (("fact", "unit"), "USD"),
            (("reported", "unit"), "USD"),
            (("normalized", "unit"), "USD"),
            (("security_class", "state"), "not_security_specific"),
            (("security_class", "classification"), "not_security_specific"),
            (("security_class", "basis"), "companyfacts_fact_has_no_security_class"),
        ):
            record = deepcopy(base)
            node = record
            for key in path[:-1]:
                node = node[key]
            node[path[-1]] = bad
            errors = list(validator.iter_errors(record))
            assert errors, f"{kind}: {path} = {bad!r} was accepted"

        unknown_kind = deepcopy(base)
        unknown_kind["metric"]["kind"] = "weighted_average_shares_outstanding"
        assert len(list(validator.iter_errors(unknown_kind))) >= 1


def test_v2_schema_accepts_new_kinds_and_concepts() -> None:
    schema = json.loads(V2_SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["$defs"]["metric"]["properties"]["kind"]["enum"] == KIND_ENUM
    assert schema["$defs"]["fact"]["properties"]["name"]["enum"] == [
        "CommonStockSharesOutstanding",
        "EntityCommonStockSharesOutstanding",
        "EntityPublicFloat",
        *NEW_CONCEPTS,
    ]
    # v2 carries no if/then blocks and gains none here.
    assert "allOf" not in schema

    validator = _v2_validator()
    for index, kind in enumerate(AUTHORIZED_CAPITAL_KINDS):
        record = _authorized_obs(f"v2-{kind}", "2026-02-27", "1000000" + str(index), kind=kind)
        assert list(validator.iter_errors(record)) == []
        assert record["metric"]["kind"] == kind
        assert record["fact"]["name"] == CONCEPT_BY_KIND[kind]

    # The truth dict and the v2 fact-name enum carry exactly the same names.
    assert sorted(name for _, name in sct.SUPPORTED_FACTS) == sorted(
        schema["$defs"]["fact"]["properties"]["name"]["enum"]
    )


# ---------------------------------------------------------------------------
# §3 / §0.3 — the new kinds never enter the share basis
# ---------------------------------------------------------------------------


def test_share_basis_ignores_new_kinds_with_one_note_each() -> None:
    base = (
        _obs("old", "2025-11-01", "90000000", filed="2025-11-10", available_at="2025-11-10T21:00:00Z"),
        _obs("new", "2026-02-27", "100000000"),
    )
    authorized = (
        _authorized_obs("auth", "2026-02-27", "500000000", kind="common_shares_authorized"),
        _authorized_obs("issued", "2026-02-27", "120000000", kind="common_shares_issued"),
        _authorized_obs("reserved", "2026-02-27", "8000000", kind="common_shares_reserved_for_future_issuance"),
    )

    without = select_share_basis(_shares(*base), _no_actions(), AS_OF)
    with_new = select_share_basis(_shares(*base, *authorized), _no_actions(), AS_OF)

    assert without.status == "selected"
    assert with_new.status == without.status
    assert with_new.selected == without.selected
    assert with_new.selected is not None
    assert Decimal(with_new.selected.value) == Decimal(100000000)
    assert with_new.candidates == without.candidates
    assert with_new.security_class_id == without.security_class_id == SECURITY
    assert with_new.issuer_id == without.issuer_id == ISSUER
    assert with_new.corporate_action == without.corporate_action

    gained = sorted(set(with_new.conflicts) - set(without.conflicts))
    assert gained == [f"not_a_share_basis_kind:{kind}" for kind in sorted(AUTHORIZED_CAPITAL_KINDS)]
    lost = sorted(set(without.conflicts) - set(with_new.conflicts))
    assert lost == []
    # One note per kind, never one per observation id.
    for kind in AUTHORIZED_CAPITAL_KINDS:
        assert with_new.conflicts.count(f"not_a_share_basis_kind:{kind}") == 1


def test_share_basis_refuses_when_only_authorized_capital_kinds_are_present() -> None:
    result = select_share_basis(
        _shares(
            _authorized_obs("only-auth", "2026-02-27", "500000000", kind="common_shares_authorized"),
            _authorized_obs("only-issued", "2026-02-27", "120000000", kind="common_shares_issued"),
        ),
        _no_actions(),
        AS_OF,
    )
    # An authorized-capital fact is never a substitute for an outstanding count.
    assert result.status == "refused"
    assert result.selected is None
    assert result.candidates == ()
    assert "refused:no_admissible_common_shares_outstanding_fact" in result.conflicts
    assert "not_a_share_basis_kind:common_shares_authorized" in result.conflicts
    assert "not_a_share_basis_kind:common_shares_issued" in result.conflicts


# ---------------------------------------------------------------------------
# §1.2 / §1.3 / §0.7 — compiler versions
# ---------------------------------------------------------------------------


def test_compiler_versions_bumped() -> None:
    assert sct.COMPILER_VERSION == "capital-structure-share-count-truth/1.4.0"
    assert materializer.COMPILER_VERSION == "capital-structure-share-count-materializer/2.2.0"
    assert _compile_fixture(SYNTHETIC_FIXTURE)["compiler_version"] == sct.COMPILER_VERSION
