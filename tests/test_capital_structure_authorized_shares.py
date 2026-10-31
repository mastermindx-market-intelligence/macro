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
import inspect
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from engine.capital_structure import authorized_shares
from engine.capital_structure import share_count_materializer as materializer
from engine.capital_structure import share_count_truth as sct
from engine.capital_structure.authorized_shares import (
    AUTHORIZED_KIND,
    COMPILER_VERSION as AUTHORIZED_COMPILER_VERSION,
    HEADROOM_STATUSES,
    IMPLEMENTATION as AUTHORIZED_IMPLEMENTATION,
    ISSUED_KIND,
    RESERVED_KIND,
    AuthorizedHeadroom,
    AuthorizedSharesInputError,
    headroom_from_records,
    select_authorized_headroom,
)
from engine.capital_structure.issuer_state_contracts import (
    CorporateActionInputs,
    GenerationBinding,
)
from engine.capital_structure.share_basis import (
    AUTHORIZED_CAPITAL_KINDS,
    MAX_BASIS_AGE_DAYS,
    select_share_basis,
)
from engine.capital_structure.share_count_truth import compile_share_count_observations
from tests.test_capital_structure_share_basis import (
    AS_OF,
    CA_SCHEMA,
    GEN,
    ISSUER,
    SECURITY,
    _event,
    _events,
    _four,
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


# ---------------------------------------------------------------------------
# §6 / §0.4-§0.6 — the authorized-unreserved headroom selector
# ---------------------------------------------------------------------------

INSTANT = "2026-02-27"
NUMERIC_FIELDS = ("authorized", "issued", "reserved", "headroom", "ceiling")


def _cap(instant: str, *, authorized=None, issued=None, reserved=None, label="cap", **overrides) -> list[dict]:
    """Clean authorized-capital records at one instant, one per named side."""

    records = []
    for kind, value in ((AUTHORIZED_KIND, authorized), (ISSUED_KIND, issued), (RESERVED_KIND, reserved)):
        if value is None:
            continue
        records.append(_authorized_obs(f"{label}-{kind}-{instant}", instant, value, kind=kind, **overrides))
    return records


def _headroom(records, actions=None, *, issuer_id=ISSUER, as_of=AS_OF) -> AuthorizedHeadroom:
    return headroom_from_records(records, actions, issuer_id=issuer_id, as_of=as_of)


def _corporate_actions() -> CorporateActionInputs:
    return CorporateActionInputs(
        GenerationBinding("corporate_actions", CA_SCHEMA, "partial", generation_id=GEN), tuple(_four()),
    )


def _wrong_family_actions() -> CorporateActionInputs:
    schema = "capital_structure.document_term_observation.v1"
    return CorporateActionInputs(
        GenerationBinding("document_terms", schema, "partial", generation_id=GEN),
        ({"schema": schema, "issuer_id": ISSUER},),
    )


def _assert_exact_decimal_text(result: AuthorizedHeadroom) -> None:
    """Every numeric field is exact decimal text or ``None`` — never a float."""

    for label in NUMERIC_FIELDS:
        raw = getattr(result, label)
        assert not isinstance(raw, float)
        if raw is None:
            continue
        assert isinstance(raw, str)
        parsed = Decimal(raw)
        assert parsed.is_finite()
        assert str(parsed) == raw


def test_headroom_known_exact() -> None:
    records = _cap(INSTANT, authorized="500000000", issued="120000000", reserved="8000000")
    result = _headroom(records)
    assert result.status == "known"
    assert result.instant == INSTANT
    assert Decimal(result.authorized) == Decimal(500000000)
    assert Decimal(result.issued) == Decimal(120000000)
    assert Decimal(result.reserved) == Decimal(8000000)
    assert Decimal(result.headroom) == Decimal(500000000) - Decimal(120000000) - Decimal(8000000)
    assert Decimal(result.headroom) == Decimal(372000000)
    assert result.ceiling is None
    assert result.issuer_id == ISSUER and result.security_class_id == SECURITY
    assert result.as_of == "2026-04-15T00:00:00Z"
    assert sorted(result.observation_ids) == sorted(
        record["observation_id"] for record in records
    )
    assert result.notes == ()
    assert result.conditions == (
        f"corporate_actions_unobserved_since:{INSTANT}",
        f"issuance_since_instant_not_reconciled:{INSTANT}",
    )
    _assert_exact_decimal_text(result)


def test_headroom_shortfall_when_reserved_exceeds_unissued() -> None:
    result = _headroom(_cap(INSTANT, authorized="100000000", issued="99000000", reserved="5000000"))
    assert result.status == "shortfall"
    assert Decimal(result.headroom) == Decimal(100000000) - Decimal(99000000) - Decimal(5000000)
    assert Decimal(result.headroom) == Decimal(-4000000)
    assert Decimal(result.headroom) < Decimal(0)
    assert result.ceiling is None
    assert result.conditions == (
        f"corporate_actions_unobserved_since:{INSTANT}",
        f"issuance_since_instant_not_reconciled:{INSTANT}",
        f"reservation_exceeds_unissued_authorized:{INSTANT}",
    )
    assert result.notes == ()
    _assert_exact_decimal_text(result)


def test_headroom_ceiling_only_when_reserved_missing_at_instant() -> None:
    records = _cap(INSTANT, authorized="500000000", issued="120000000")
    result = _headroom(records)
    assert result.status == "ceiling_only"
    assert Decimal(result.ceiling) == Decimal(500000000) - Decimal(120000000)
    assert Decimal(result.ceiling) == Decimal(380000000)
    assert result.reserved is None and result.headroom is None
    assert result.conditions == (
        f"corporate_actions_unobserved_since:{INSTANT}",
        f"issuance_since_instant_not_reconciled:{INSTANT}",
        f"reserved_unobserved_at_instant:{INSTANT}",
    )
    assert result.notes == ()
    assert sorted(result.observation_ids) == sorted(record["observation_id"] for record in records)
    _assert_exact_decimal_text(result)


def test_headroom_never_borrows_reserved_from_other_instant() -> None:
    records = _cap(INSTANT, authorized="500000000", issued="120000000")
    borrowed = _cap(
        "2025-11-01", reserved="8000000", label="old",
        filed="2025-11-10", available_at="2025-11-10T21:00:00Z",
    )
    result = _headroom([*records, *borrowed])
    assert result.instant == INSTANT
    assert result.status == "ceiling_only"
    assert result.reserved is None
    assert Decimal(result.ceiling) == Decimal(380000000)
    assert f"reserved_unobserved_at_instant:{INSTANT}" in result.conditions
    assert sorted(result.observation_ids) == sorted(record["observation_id"] for record in records)
    # The earlier reserve is neither reported nor used: it is not even a used record.
    assert result.reserved is None
    assert all(item["observation_id"] not in result.observation_ids for item in borrowed)
    assert Decimal(result.ceiling) == Decimal(result.authorized) - Decimal(result.issued)


def test_headroom_unknown_when_authorized_missing() -> None:
    result = _headroom(_cap(INSTANT, issued="120000000", reserved="8000000"))
    assert result.status == "unknown"
    assert result.notes == ("authorized_unobserved",)
    assert result.instant is None
    assert all(getattr(result, label) is None for label in NUMERIC_FIELDS)
    assert result.observation_ids == ()


def test_headroom_unknown_when_issued_missing() -> None:
    result = _headroom(_cap(INSTANT, authorized="500000000", reserved="8000000"))
    assert result.status == "unknown"
    assert result.notes == ("issued_unobserved",)
    assert result.instant is None
    assert all(getattr(result, label) is None for label in NUMERIC_FIELDS)


def test_headroom_unknown_when_never_observed_at_one_instant() -> None:
    authorized = _cap(INSTANT, authorized="500000000")
    issued = _cap(
        "2026-03-31", issued="125000000", label="later",
        filed="2026-04-10", available_at="2026-04-10T21:00:00Z",
    )
    result = _headroom([*authorized, *issued])
    assert result.status == "unknown"
    # Values from different instants are never combined into one answer.
    assert result.notes == ("authorized_unobserved", "issued_unobserved")
    assert result.instant is None
    assert all(getattr(result, label) is None for label in NUMERIC_FIELDS)


def test_headroom_unknown_when_stale() -> None:
    stale = "2025-06-30"
    result = _headroom(
        _cap(stale, authorized="500000000", issued="120000000", reserved="8000000",
             filed="2025-07-10", available_at="2025-07-10T21:00:00Z"),
    )
    assert result.status == "unknown"
    assert result.notes == (f"stale_instant:{stale}",)
    assert result.instant == stale
    assert result.headroom is None and result.ceiling is None
    # The observed state quantities are still reported, exactly and unscaled.
    assert Decimal(result.authorized) == Decimal(500000000)
    assert Decimal(result.issued) == Decimal(120000000)
    assert Decimal(result.reserved) == Decimal(8000000)
    _assert_exact_decimal_text(result)


def test_headroom_is_not_stale_at_exactly_the_age_bound() -> None:
    from datetime import date, timedelta

    edge = (date.fromisoformat("2026-04-15") - timedelta(days=MAX_BASIS_AGE_DAYS)).isoformat()
    filed = edge
    result = _headroom(
        _cap(edge, authorized="500000000", issued="120000000", reserved="8000000",
             filed=filed, available_at=f"{filed}T21:00:00Z"),
    )
    assert result.status == "known"
    assert Decimal(result.headroom) == Decimal(372000000)
    assert not any(note.startswith("stale_instant:") for note in result.notes)


def test_headroom_unknown_when_split_after_instant() -> None:
    records = _cap(INSTANT, authorized="500000000", issued="120000000", reserved="8000000")
    result = _headroom(records, _four())
    assert result.status == "unknown"
    assert result.headroom is None and result.ceiling is None
    assert result.notes == ("split_since_instant_unscaled:ca:0000000001:rs-2026-03",)
    # A19: the split ratio is never applied to authorized, issued or reserved.
    assert Decimal(result.authorized) == Decimal(500000000)
    assert Decimal(result.issued) == Decimal(120000000)
    assert Decimal(result.reserved) == Decimal(8000000)
    _assert_exact_decimal_text(result)


def test_headroom_unknown_when_split_is_only_partly_evidenced() -> None:
    records = _cap(INSTANT, authorized="500000000", issued="120000000", reserved="8000000")
    partial = _four()[:2]
    result = _headroom(records, partial)
    assert result.status == "unknown"
    assert result.headroom is None
    assert any(note.startswith("split_since_instant_unscaled:unconfirmed:") for note in result.notes)


def test_headroom_condition_when_actions_unobserved() -> None:
    records = _cap(INSTANT, authorized="500000000", issued="120000000", reserved="8000000")
    unobserved = _headroom(records, None)
    assert unobserved.status == "known"
    assert f"corporate_actions_unobserved_since:{INSTANT}" in unobserved.conditions
    assert not any(note.startswith("split_since_instant_unscaled:") for note in unobserved.notes)

    # An empty-but-observed action family is a different fact from an unobserved one.
    observed_empty = _headroom(records, ())
    assert observed_empty.status == "known"
    assert f"corporate_actions_unobserved_since:{INSTANT}" not in observed_empty.conditions
    assert observed_empty.notes == ()


def test_headroom_contradicted_on_conflicting_duplicates() -> None:
    first = _authorized_obs("auth-x", INSTANT, "500000000", kind=AUTHORIZED_KIND)
    second = _authorized_obs("auth-y", INSTANT, "600000000", kind=AUTHORIZED_KIND)
    others = _cap(INSTANT, issued="120000000", reserved="8000000")
    result = _headroom([first, second, *others])
    assert result.status == "contradicted"
    assert result.authorized is None
    assert result.headroom is None and result.ceiling is None
    ids = "+".join(sorted([first["observation_id"], second["observation_id"]]))
    assert result.notes == (f"conflict:{AUTHORIZED_KIND}:{ids}",)
    assert Decimal(result.issued) == Decimal(120000000)
    assert Decimal(result.reserved) == Decimal(8000000)
    _assert_exact_decimal_text(result)


def test_headroom_equal_duplicate_values_are_not_a_conflict() -> None:
    first = _authorized_obs("auth-x", INSTANT, "500000000", kind=AUTHORIZED_KIND)
    second = _authorized_obs("auth-y", INSTANT, "500000000", kind=AUTHORIZED_KIND)
    result = _headroom([first, second, *_cap(INSTANT, issued="120000000", reserved="8000000")])
    assert result.status == "known"
    assert result.notes == ()
    assert Decimal(result.authorized) == Decimal(500000000)
    assert Decimal(result.headroom) == Decimal(372000000)


def test_headroom_contradicted_when_issued_exceeds_authorized() -> None:
    for extra in ({}, {"reserved": "8000000"}):
        result = _headroom(_cap(INSTANT, authorized="100000000", issued="150000000", **extra))
        assert result.status == "contradicted"
        assert result.notes == (f"issued_exceeds_authorized:{INSTANT}",)
        assert result.headroom is None and result.ceiling is None
        assert Decimal(result.authorized) == Decimal(100000000)
        assert Decimal(result.issued) == Decimal(150000000)
        _assert_exact_decimal_text(result)


def test_headroom_unclean_record_is_noted_and_unused() -> None:
    clean = _cap(INSTANT, authorized="500000000", issued="120000000", reserved="8000000")
    dollars = _authorized_obs("auth-usd", INSTANT, "500000000", kind=AUTHORIZED_KIND)
    dollars["normalized"]["unit"] = "USD"
    ambiguous = _authorized_obs(
        "issued-ambiguous", INSTANT, None, kind=ISSUED_KIND,
        disposition="ambiguous", reason="multiple_distinct_values_for_fact_slot",
    )
    result = _headroom([*clean, dollars, ambiguous])
    assert result.status == "known"
    assert Decimal(result.headroom) == Decimal(372000000)
    assert f"unclean:{AUTHORIZED_KIND}:unit_mismatch:USD" in result.notes
    assert (
        f"unclean:{ISSUED_KIND}:ambiguous:multiple_distinct_values_for_fact_slot" in result.notes
    )
    assert dollars["observation_id"] not in result.observation_ids
    assert ambiguous["observation_id"] not in result.observation_ids
    assert sorted(result.observation_ids) == sorted(record["observation_id"] for record in clean)


def test_headroom_issuance_since_instant_condition() -> None:
    same_day = "2026-03-10"
    at_as_of = _headroom(
        _cap(same_day, authorized="500000000", issued="120000000", reserved="8000000"),
        as_of="2026-03-10T23:00:00Z",
    )
    assert at_as_of.instant == same_day
    assert at_as_of.status == "known"
    assert "issuance_since_instant_not_reconciled" not in json.dumps(at_as_of.as_record())
    assert f"issuance_since_instant_not_reconciled:{same_day}" not in at_as_of.conditions

    before = _headroom(_cap(INSTANT, authorized="500000000", issued="120000000", reserved="8000000"))
    assert before.instant == INSTANT
    assert f"issuance_since_instant_not_reconciled:{INSTANT}" in before.conditions


def test_headroom_uses_decimal_only_and_never_scales_by_split() -> None:
    # §0.6: the selector source never converts an exact count to a binary float.
    float_call = "float" + "("
    source = inspect.getsource(authorized_shares)
    assert float_call not in source
    assert "import math" not in source

    records = _cap(INSTANT, authorized="500000000", issued="120000000", reserved="8000000")
    plain = _headroom(records)
    split = _headroom(records, _four())

    assert plain.status == "known" and Decimal(plain.headroom) == Decimal(372000000)
    assert split.status == "unknown" and split.headroom is None and split.ceiling is None
    # The 1-for-10 reverse split changed the status, never the numbers.
    for label in ("authorized", "issued", "reserved"):
        assert getattr(split, label) == getattr(plain, label)
        assert Decimal(getattr(split, label)) == Decimal(getattr(plain, label))
    assert Decimal(split.authorized) == Decimal(500000000)
    assert Decimal(split.issued) == Decimal(120000000)
    assert Decimal(split.reserved) == Decimal(8000000)

    for result in (plain, split):
        _assert_exact_decimal_text(result)
        for value in result.as_record().values():
            assert not isinstance(value, float)


def test_headroom_ignores_other_metric_kinds_without_a_note() -> None:
    records = _cap(INSTANT, authorized="500000000", issued="120000000", reserved="8000000")
    noise = (
        _obs("outstanding", INSTANT, "118000000"),
        _obs("float", INSTANT, "2500000000", kind="public_float", name="EntityPublicFloat", unit="USD"),
        _obs("weighted", INSTANT, "119000000", kind="weighted_average_shares_outstanding"),
    )
    plain = _headroom(records)
    with_noise = _headroom([*records, *noise])
    assert with_noise.as_record() == plain.as_record()
    assert with_noise.status == "known"
    assert with_noise.notes == ()
    # Outstanding shares are never substituted for issued shares.
    assert Decimal(with_noise.issued) == Decimal(120000000)


def test_headroom_records_not_yet_available_are_invisible() -> None:
    records = _cap(INSTANT, authorized="500000000", issued="120000000")
    future = _cap(
        "2026-03-31", reserved="9000000", label="future",
        filed="2026-04-20", available_at="2026-04-20T21:00:00Z",
    )
    result = _headroom([*records, *future])
    assert result.status == "ceiling_only"
    assert result.notes == (f"not_yet_available:{RESERVED_KIND}",)
    assert f"reserved_unobserved_at_instant:{INSTANT}" in result.conditions


def test_headroom_instant_after_as_of_is_excluded() -> None:
    records = _cap(INSTANT, authorized="500000000", issued="120000000")
    after = _cap(
        "2026-06-30", authorized="900000000", issued="130000000", label="after",
        filed="2026-03-01", available_at="2026-03-01T21:00:00Z",
    )
    result = _headroom([*records, *after])
    assert result.instant == INSTANT
    assert result.status == "ceiling_only"
    assert Decimal(result.ceiling) == Decimal(380000000)
    assert f"instant_after_as_of:{AUTHORIZED_KIND}" in result.notes
    assert f"instant_after_as_of:{ISSUED_KIND}" in result.notes


def test_headroom_superseded_correction_replaces_its_predecessor() -> None:
    original = _authorized_obs("reserved-v1", INSTANT, "8000000", kind=RESERVED_KIND)
    corrected = _authorized_obs(
        "reserved-v2", INSTANT, "9000000", kind=RESERVED_KIND,
        supersedes=(original["observation_id"],), correction_of=original["observation_id"],
    )
    records = [*_cap(INSTANT, authorized="500000000", issued="120000000"), original, corrected]
    result = _headroom(records)
    assert result.status == "known"
    assert Decimal(result.reserved) == Decimal(9000000)
    assert Decimal(result.headroom) == Decimal(500000000) - Decimal(120000000) - Decimal(9000000)
    assert Decimal(result.headroom) == Decimal(371000000)
    assert original["observation_id"] not in result.observation_ids
    assert corrected["observation_id"] in result.observation_ids


def test_headroom_rejects_bad_as_of_and_a_foreign_issuer() -> None:
    records = _cap(INSTANT, authorized="500000000", issued="120000000", reserved="8000000")
    for bad_as_of in ("2026-04-15", "2026-04-15T00:00:00", "", None, "not-a-timestamp"):
        with pytest.raises(AuthorizedSharesInputError):
            _headroom(records, as_of=bad_as_of)

    foreign = _authorized_obs("foreign", INSTANT, "1", kind=AUTHORIZED_KIND, issuer="issuer:0000000002")
    with pytest.raises(AuthorizedSharesInputError):
        _headroom([*records, foreign])


def test_select_authorized_headroom_wrapper_matches_core() -> None:
    records = _cap(INSTANT, authorized="500000000", issued="120000000", reserved="8000000")
    observations = _shares(*records)

    assert select_authorized_headroom(observations, _no_actions(), AS_OF).as_record() == (
        headroom_from_records(records, None, issuer_id=ISSUER, as_of=AS_OF).as_record()
    )
    wrapper = select_authorized_headroom(observations, _no_actions(), AS_OF)
    assert wrapper.status == "known" and Decimal(wrapper.headroom) == Decimal(372000000)
    assert wrapper.issuer_id == ISSUER and wrapper.security_class_id == SECURITY

    actions = _corporate_actions()
    split_wrapper = select_authorized_headroom(observations, actions, AS_OF)
    split_core = headroom_from_records(records, tuple(_four()), issuer_id=ISSUER, as_of=AS_OF)
    assert split_wrapper.as_record() == split_core.as_record()
    assert split_wrapper.status == "unknown"

    # An empty action family maps to actions=None in the core.
    empty = select_authorized_headroom(observations, _no_actions(), AS_OF)
    assert f"corporate_actions_unobserved_since:{INSTANT}" in empty.conditions


def test_select_authorized_headroom_rejects_wrong_types() -> None:
    records = _cap(INSTANT, authorized="500000000", issued="120000000", reserved="8000000")
    observations = _shares(*records)

    with pytest.raises(AuthorizedSharesInputError):
        select_authorized_headroom(records, _no_actions(), AS_OF)
    with pytest.raises(AuthorizedSharesInputError):
        select_authorized_headroom(tuple(records), _no_actions(), AS_OF)
    with pytest.raises(AuthorizedSharesInputError):
        select_authorized_headroom(observations, tuple(_four()), AS_OF)
    with pytest.raises(AuthorizedSharesInputError):
        select_authorized_headroom(observations, records, AS_OF)
    for bad_as_of in ("2026-04-15", "2026-04-15T00:00:00", ""):
        with pytest.raises(AuthorizedSharesInputError):
            select_authorized_headroom(observations, _no_actions(), bad_as_of)
    with pytest.raises(AuthorizedSharesInputError):
        select_authorized_headroom(observations, _wrong_family_actions(), AS_OF)
    with pytest.raises(AuthorizedSharesInputError):
        select_authorized_headroom(_shares(), _no_actions(), AS_OF)
    with pytest.raises(AuthorizedSharesInputError):
        select_authorized_headroom(
            _shares(
                *records,
                _authorized_obs("foreign", INSTANT, "1", kind=AUTHORIZED_KIND, issuer="issuer:0000000002"),
            ),
            _no_actions(),
            AS_OF,
        )


# ---------------------------------------------------------------------------
# Review regressions (independent Opus audit of PR #9400)
# ---------------------------------------------------------------------------


def test_review_events_family_does_not_raise_and_keeps_the_unobserved_condition() -> None:
    records = _cap(INSTANT, authorized="500000000", issued="120000000", reserved="8000000")
    observations = _shares(*records)
    # One event filed before the instant (ignored) and one vote after it (a note only).
    events = _events(
        _event("old-charter", "charter_amendment_candidate", "2026-01-15"),
        _event("vote", "shareholder_vote_candidate", "2026-03-20"),
    )
    result = select_authorized_headroom(observations, events, AS_OF)
    assert result.status == "known"
    assert Decimal(result.headroom) == Decimal(372000000)
    # Event candidates never confirm that no split took effect.
    assert f"corporate_actions_unobserved_since:{INSTANT}" in result.conditions
    assert "rejected:event:vote:vote_or_authorization_is_not_an_effective_split" in result.notes
    assert result.as_record() == headroom_from_records(
        records, None, issuer_id=ISSUER, as_of=AS_OF, events=tuple(events.actions),
    ).as_record()


def test_review_unconfirmed_charter_amendment_after_the_instant_refuses() -> None:
    records = _cap(INSTANT, authorized="500000000", issued="120000000", reserved="8000000")
    events = _events(_event("charter", "charter_amendment_candidate", "2026-03-20"))
    result = select_authorized_headroom(_shares(*records), events, AS_OF)
    assert result.status == "unknown"
    assert result.headroom is None and result.ceiling is None
    assert (
        "split_since_instant_unscaled:unconfirmed:charter_amendment_candidate:event:charter:2026-03-20"
        in result.notes
    )
    # The facts themselves are still reported, unscaled (A19).
    assert Decimal(result.authorized) == Decimal(500000000)


def test_review_events_filed_after_as_of_are_invisible() -> None:
    records = _cap(INSTANT, authorized="500000000", issued="120000000", reserved="8000000")
    events = _events(_event("late-charter", "charter_amendment_candidate", "2026-04-20"))
    result = select_authorized_headroom(_shares(*records), events, AS_OF)
    assert result.status == "known"
    assert Decimal(result.headroom) == Decimal(372000000)


def test_review_a_record_claiming_authority_is_refused() -> None:
    records = _cap(INSTANT, authorized="500000000", issued="120000000", reserved="8000000")
    for flag in ("capacity_authority", "share_count_ledger_authority", "sizing_authority"):
        granted = deepcopy(records)
        granted[0]["authority"][flag] = True
        with pytest.raises(AuthorizedSharesInputError, match=flag):
            _headroom(granted)
    not_context = deepcopy(records)
    not_context[2]["authority"]["is_context_only"] = False
    with pytest.raises(AuthorizedSharesInputError, match="context-only"):
        _headroom(not_context)
    missing = deepcopy(records)
    missing[1].pop("authority")
    with pytest.raises(AuthorizedSharesInputError):
        _headroom(missing)


def test_review_an_authorized_capital_record_must_name_its_issuer() -> None:
    records = _cap(INSTANT, authorized="500000000", issued="120000000", reserved="8000000")
    anonymous = deepcopy(records)
    anonymous[0].pop("issuer_id")
    anonymous[0].pop("issuer", None)
    with pytest.raises(AuthorizedSharesInputError, match="must name its issuer"):
        _headroom(anonymous)


def test_review_a_visible_correction_supersedes_even_when_its_instant_is_excluded() -> None:
    original = _authorized_obs("reserved-v1", INSTANT, "8000000", kind=RESERVED_KIND)
    # The correction is available before as_of but reports an instant after it.
    corrected = _authorized_obs(
        "reserved-v2", "2026-05-31", "9000000", kind=RESERVED_KIND,
        supersedes=(original["observation_id"],), correction_of=original["observation_id"],
    )
    records = [*_cap(INSTANT, authorized="500000000", issued="120000000"), original, corrected]
    result = _headroom(records)
    assert f"instant_after_as_of:{RESERVED_KIND}" in result.notes
    assert original["observation_id"] not in result.observation_ids
    # The withdrawn reservation is never used, so only a ceiling is stated.
    assert result.status == "ceiling_only"
    assert Decimal(result.ceiling) == Decimal(380000000)
    assert result.reserved is None


def test_review_a_record_filed_after_as_of_is_not_yet_available() -> None:
    records = _cap(INSTANT, authorized="500000000", issued="120000000")
    late = _authorized_obs(
        "reserved-late", INSTANT, "8000000", kind=RESERVED_KIND,
        filed="2026-04-20", available_at="2026-03-10T21:00:00Z",
    )
    result = _headroom([*records, late])
    assert f"not_yet_available:{RESERVED_KIND}" in result.notes
    assert late["observation_id"] not in result.observation_ids
    assert result.status == "ceiling_only"
    assert Decimal(result.ceiling) == Decimal(380000000)


def test_review_output_text_is_canonical_and_equal_values_do_not_conflict() -> None:
    records = _cap(INSTANT, authorized="1E+9", issued="120000000.0")
    reserved = [
        _authorized_obs("reserved-a", INSTANT, "8000000", kind=RESERVED_KIND),
        _authorized_obs("reserved-b", INSTANT, "8000000.00", kind=RESERVED_KIND),
    ]
    result = _headroom([*records, *reserved])
    assert result.status == "known"
    assert result.authorized == "1000000000"
    assert result.issued == "120000000"
    assert result.reserved == "8000000"
    assert result.headroom == "872000000"
    assert not any(note.startswith("conflict:") for note in result.notes)

    exact_zero = _headroom(_cap(INSTANT, authorized="120000000.00", issued="120000000", reserved="0.0"))
    assert exact_zero.status == "known"
    assert exact_zero.headroom == "0"
    assert exact_zero.reserved == "0"


def test_review_arithmetic_is_exact_at_every_magnitude() -> None:
    authorized = "123456789012345678901234567890123"
    issued = "0.000000000000000000000000001"
    result = _headroom(_cap(INSTANT, authorized=authorized, issued=issued, reserved="0"))
    assert result.status == "known"
    # 60 significant digits; the default 28-digit context would round this.
    assert result.headroom == "123456789012345678901234567890122.999999999999999999999999999"
    assert result.authorized == authorized


def test_headroom_result_is_deterministic_and_json_safe() -> None:
    records = _cap(INSTANT, authorized="500000000", issued="120000000", reserved="8000000")
    first = _headroom(records)
    second = _headroom(list(reversed(records)))
    assert first.as_record() == second.as_record()

    record = first.as_record()
    encoded = json.dumps(record, sort_keys=True)
    assert json.loads(encoded) == record
    for value in record.values():
        assert value is None or isinstance(value, (str, list))
    assert record["status"] in HEADROOM_STATUSES
    assert AUTHORIZED_IMPLEMENTATION.endswith("select_authorized_headroom/1")
    assert AUTHORIZED_COMPILER_VERSION == "capital_structure.authorized_shares/1"


def test_headroom_post_init_refuses_an_incoherent_result() -> None:
    base = dict(
        issuer_id=ISSUER, security_class_id=SECURITY, as_of=AS_OF, instant=INSTANT,
        observation_ids=(), conditions=(), notes=(),
    )

    def _build(**overrides) -> AuthorizedHeadroom:
        payload = {
            "status": "known", "authorized": "500000000", "issued": "120000000",
            "reserved": "8000000", "headroom": "372000000", "ceiling": None,
        }
        payload.update(overrides)
        return AuthorizedHeadroom(**base, **payload)

    assert _build().status == "known"
    for bad in (
        {"status": "invented"},
        {"status": "known", "headroom": None},
        {"status": "known", "reserved": None},
        {"status": "known", "headroom": "-1"},
        {"status": "known", "ceiling": "380000000"},
        {"status": "shortfall", "headroom": "1"},
        {"status": "shortfall", "headroom": "-1", "ceiling": "2"},
        {"status": "ceiling_only", "ceiling": None},
        {"status": "ceiling_only", "reserved": "8000000"},
        {"status": "ceiling_only", "headroom": "372000000"},
        {"status": "unknown", "headroom": "372000000"},
        {"status": "contradicted", "ceiling": "380000000"},
        {"authorized": "not-a-number"},
        {"authorized": 500000000},
    ):
        with pytest.raises(AuthorizedSharesInputError):
            _build(**bad)
