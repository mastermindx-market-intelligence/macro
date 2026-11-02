"""FIF C0-b: issuer-generic member capture (D1 write side) — offline, fake fetches.

Every identity is DERIVED at runtime from the committed golden fixture bytes
(the fixture is a byte source for a synthetic lane, never a producer input
path), so this file carries no ticker or CIK literal either.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest

from collectors.sec_document_spine import (
    persist_archive_document,
    retain_filing_manifest,
    with_document_retrievals,
)
from engine.fundamental_forensics import fif_member_capture as CAP
from engine.fundamental_forensics.fif_member_capture import (
    FifMemberCaptureError,
    capture_fif_filing_packages,
    find_retained_primary_manifest,
    mint_statement_roles,
    package_dir_for,
    read_retained_fif_packages,
    refuse_repository_fixture_inputs,
)
from engine.fundamental_forensics.sec_document_spine import build_filing_manifests
from engine.fundamental_forensics.statement_graph import GOLDEN_AAPL_FIXTURES
from collectors.sec_request_pacer import SecRequestPacer

ROOT = Path(__file__).resolve().parents[1]

# Real-shaped clocks: filings accepted 2024-2025, captured after the lineage
# chain-rule clock. The SECOND accession is re-dated into 2024 so the pair
# spans 2024-2025 exactly as the frozen spec's REAL-SHAPED CLOCKS case demands.
FIRST_ACCEPTED_AT = "2025-10-31T10:01:26.000Z"
SECOND_ACCEPTED_AT = "2024-07-31T10:01:26.000Z"
CAPTURE_CLOCK = "2026-10-13T02:31:00Z"
LATER_CAPTURE_CLOCK = "2026-10-14T02:31:00Z"
USER_AGENT = "MastermindX FIF C0-b test bench test@example.invalid"



def _normalized_utc(value: str) -> str:
    from datetime import datetime, timezone

    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    return datetime.fromisoformat(text).astimezone(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _fixture_identity() -> dict:
    """Issuer identity derived from the committed fixture at runtime."""
    accessions = sorted(GOLDEN_AAPL_FIXTURES)
    manifests = {}
    for accession in accessions:
        fixture = ROOT / GOLDEN_AAPL_FIXTURES[accession]
        manifests[accession] = json.loads(
            (fixture / "package_manifest.json").read_text(encoding="utf-8")
        )
    first = manifests[accessions[0]]
    listing_key = str(first["listing_key"])
    return {
        "cik": str(first["cik"]),
        "ticker": listing_key.rsplit("-", 1)[-1],
        "entity_id": str(first["entity_id"]),
        "security_id": str(first["security_id"]),
        "listing_key": listing_key,
        "accessions": accessions,
        "manifests": manifests,
    }


def _acceptance_for(accessions: list[str], accession: str) -> str:
    return FIRST_ACCEPTED_AT if accession == accessions[0] else SECOND_ACCEPTED_AT


def _filing_date_for(accessions: list[str], accession: str) -> str:
    identity = _fixture_identity()
    manifest = identity["manifests"][accession]
    if accession == accessions[0]:
        return str(manifest["filing_date"])
    return str(manifest["filing_date"]).replace("2026-", "2024-")


def _report_date_for(accessions: list[str], accession: str) -> str:
    identity = _fixture_identity()
    manifest = identity["manifests"][accession]
    if accession == accessions[0]:
        return str(manifest["period_of_report"])
    return str(manifest["period_of_report"]).replace("2026-", "2024-")


def _synthetic_submissions(identity: dict) -> dict:
    accessions = identity["accessions"]
    recent = {
        "accessionNumber": list(accessions),
        "form": [str(identity["manifests"][a]["form"]) for a in accessions],
        "filingDate": [_filing_date_for(accessions, a) for a in accessions],
        "reportDate": [_report_date_for(accessions, a) for a in accessions],
        "acceptanceDateTime": [_acceptance_for(accessions, a) for a in accessions],
        "primaryDocument": [
            str(identity["manifests"][a]["primary_document"]) for a in accessions
        ],
        "isXBRL": [True, True],
        "isInlineXBRL": [True, True],
    }
    return {
        "cik": int(identity["cik"]),
        "name": "Synthetic Lane Issuer",
        "filings": {"recent": recent},
    }


def _write_submissions(raw_root: Path, identity: dict) -> None:
    """Retain the Submissions payload + verified pointer (the raw-root shape)."""
    cik = identity["cik"]
    payload = json.dumps(_synthetic_submissions(identity)).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    object_path = f"{cik}/submissions/{digest[:32]}.json.gz"
    target = raw_root / object_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(gzip.compress(payload))
    receipt = {
        "schema": "fundamental_forensics_retrieval.v1",
        "cik": cik,
        "endpoint": "submissions",
        "url": f"https://data.sec.gov/submissions/CIK{cik}.json",
        "retrieved_at": CAPTURE_CLOCK,
        "sha256": digest,
        "bytes": len(payload),
        "object_path": object_path,
        "http_etag": None,
        "http_last_modified": None,
    }
    pointer = raw_root / cik / "submissions" / "latest.json"
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text(json.dumps(receipt), encoding="utf-8")


def _retain_primaries(archive_root: Path, identity: dict, *, extra: str | None = None) -> None:
    """Retain wave-2 filing manifests with STORED primaries (the archive shape).

    ``extra`` retains one ADDITIONAL accession (cloned from the first row) so a
    test can hold a retained primary that the raw-root Submissions pointer does
    not list.
    """
    submissions = _synthetic_submissions(identity)
    if extra is not None:
        recent = submissions["filings"]["recent"]
        recent["accessionNumber"] = [extra, *recent["accessionNumber"]]
        for field in ("form", "filingDate", "reportDate", "acceptanceDateTime", "primaryDocument"):
            recent[field] = [recent[field][0], *recent[field]]
        recent["isXBRL"] = [True, *recent["isXBRL"]]
        recent["isInlineXBRL"] = [True, *recent["isInlineXBRL"]]
    manifests = build_filing_manifests(
        submissions,
        cik=identity["cik"],
        ticker=identity["ticker"],
        recorded_at=CAPTURE_CLOCK,
    )
    by_accession = {m["filing"]["accession"]: m for m in manifests}
    retain_accessions = list(identity["accessions"])
    if extra is not None:
        retain_accessions.append(extra)
    for accession in retain_accessions:
        manifest = by_accession[accession]
        primary = next(
            item for item in manifest["documents"] if item["role"] == "primary"
        )
        source_accession = (
            accession if accession in GOLDEN_AAPL_FIXTURES else identity["accessions"][0]
        )
        fixture = ROOT / GOLDEN_AAPL_FIXTURES[source_accession]
        primary_bytes = (fixture / "members" / primary["document_name"]).read_bytes()
        receipt = persist_archive_document(
            archive_root, primary, primary_bytes, retrieved_at=CAPTURE_CLOCK
        )
        materialized = with_document_retrievals(
            manifest, {str(primary["document_id"]): receipt.to_dict()}
        )
        retain_filing_manifest(archive_root, materialized)


def _fixture_member_bytes() -> dict[str, dict[str, bytes]]:
    """Every member byte the fake fetcher serves, keyed by accession then name."""
    served: dict[str, dict[str, bytes]] = {}
    for accession, relative in sorted(GOLDEN_AAPL_FIXTURES.items()):
        fixture = ROOT / relative
        members = {"index.json": (fixture / "index.json").read_bytes()}
        for path in sorted((fixture / "members").iterdir()):
            members[path.name] = path.read_bytes()
        served[accession.replace("-", "")] = members
    return served


class _FakeCollector:
    """Offline stand-in for ``SecFilingArchiveCollector``.

    Persists the served bytes through the incumbent ``persist_archive_document``
    so the capture reads genuinely retained, digest-verified bytes back from
    the archive cache; it paces every fetch on the SHARED pacer exactly as the
    real collector does.
    """

    def __init__(self, cache_root: Path, served: dict[str, dict[str, bytes]], pacer) -> None:
        self.cache_root = Path(cache_root)
        self._served = served
        self._pacer = pacer
        self.fetched: list[str] = []
        self.pacer_acquires = 0

    def fetch_document(self, document, *, retrieved_at=None, expected_sha256=None, max_document_bytes=None):
        self._pacer.acquire()
        self.pacer_acquires += 1
        url = document["archive_url"]
        accession = url.rsplit("/", 2)[-2].replace("-", "")
        name = url.rsplit("/", 1)[-1]
        self.fetched.append(name)
        payload = self._served[accession][name]
        return persist_archive_document(
            self.cache_root, document, payload, retrieved_at=retrieved_at
        )


def _no_sleep_pacer() -> SecRequestPacer:
    return SecRequestPacer(
        min_interval_seconds=0.12,
        sleeper=lambda _seconds: None,
        monotonic=lambda: 0.0,
    )


def _contract_issuers(identity: dict, *, with_binding: bool = True) -> list[dict]:
    binding = {
        "issuer_id": identity["entity_id"],
        "issuer_cik": identity["cik"],
        "security_id": identity["security_id"],
        "listing_key": identity["listing_key"],
        "mic": "XNAS",
        "effective_at": "2023-05-09T00:00:00",
    }
    accessions = identity["accessions"]
    return [
        {
            "cik": identity["cik"],
            "ticker": identity["ticker"],
            "legal_name": "Synthetic Lane Issuer",
            "security_master_binding": binding if with_binding else None,
            "accessions": [
                {
                    "accession": a,
                    "form": str(identity["manifests"][a]["form"]),
                    "filing_date": _filing_date_for(accessions, a),
                }
                for a in accessions
            ],
        }
    ]


def _materialized_lane(
    tmp_path: Path, *, with_binding: bool = True, extra_retained: str | None = None
):
    identity = _fixture_identity()
    raw_root = tmp_path / "raw"
    archive_root = tmp_path / "archive"
    raw_root.mkdir(parents=True)
    archive_root.mkdir(parents=True)
    _write_submissions(raw_root, identity)
    _retain_primaries(archive_root, identity, extra=extra_retained)
    served = _fixture_member_bytes()
    pacer = _no_sleep_pacer()
    collector = _FakeCollector(archive_root, served, pacer)
    issuers = _contract_issuers(identity, with_binding=with_binding)
    return {
        "identity": identity,
        "raw_root": raw_root,
        "archive_root": archive_root,
        "collector": collector,
        "pacer": pacer,
        "issuers": issuers,
        "served": served,
    }


def test_all_members_fetched_under_one_shared_pacer(tmp_path) -> None:
    lane = _materialized_lane(tmp_path)
    report = capture_fif_filing_packages(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=lane["issuers"],
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=CAPTURE_CLOCK,
    )
    # Two accessions x (archive index + five role members) — the primary is
    # already retained and is never re-fetched.
    assert len(lane["collector"].fetched) == 12
    assert lane["collector"].pacer_acquires == len(lane["collector"].fetched)
    assert lane["collector"]._pacer is lane["pacer"]
    rows = report["issuers"][0]["accessions"]
    assert [row["outcome"] for row in rows] == ["captured", "captured"]
    for row in rows:
        assert row["capture_recorded_at"] == CAPTURE_CLOCK
        assert row["reused"] is False


def test_private_pacer_is_a_typed_refusal(tmp_path) -> None:
    lane = _materialized_lane(tmp_path)
    impostor = _no_sleep_pacer()
    assert impostor is not lane["pacer"]
    with pytest.raises(FifMemberCaptureError) as caught:
        capture_fif_filing_packages(
            raw_root=lane["raw_root"],
            archive_root=lane["archive_root"],
            issuers=lane["issuers"],
            collector=lane["collector"],
            pacer=impostor,
            recorded_at=CAPTURE_CLOCK,
        )
    assert caught.value.code == "private_pacer"


def test_witness_fields_bound_to_the_retained_submissions_row(tmp_path) -> None:
    lane = _materialized_lane(tmp_path)
    capture_fif_filing_packages(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=lane["issuers"],
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=CAPTURE_CLOCK,
    )
    submissions = _synthetic_submissions(lane["identity"])
    recent = submissions["filings"]["recent"]
    for index, accession in enumerate(lane["identity"]["accessions"]):
        package_dir = package_dir_for(lane["archive_root"], lane["identity"]["cik"], accession)
        witness = json.loads(
            (package_dir / "sec_submissions_witness.json").read_text(encoding="utf-8")
        )
        assert witness["accessionNumber"] == accession
        assert witness["form"] == recent["form"][index]
        assert witness["filingDate"] == recent["filingDate"][index]
        assert witness["reportDate"] == recent["reportDate"][index]
        # The minter normalizes every clock to whole-second UTC text.
        assert witness["acceptanceDateTime"] == _normalized_utc(
            recent["acceptanceDateTime"][index]
        )
        assert witness["primaryDocument"] == recent["primaryDocument"][index]
        assert witness["source_url"] == f"https://data.sec.gov/submissions/CIK{lane['identity']['cik']}.json"
        manifest = json.loads(
            (package_dir / "package_manifest.json").read_text(encoding="utf-8")
        )
        assert manifest["source_accepted_at"] == witness["acceptanceDateTime"]
        assert manifest["capture_recorded_at"] == CAPTURE_CLOCK
        assert manifest["schema"] == CAP.FIF_MEMBER_CAPTURE_PACKAGE_SCHEMA
        assert manifest["retained_count"] == 6
        stored_roles = {
            item["role"]
            for item in manifest["members"]
            if item.get("state") == "stored"
        }
        assert stored_roles == {
            "primary",
            "schema",
            "calculation",
            "definition",
            "label",
            "presentation",
        }


def test_statement_roles_minted_from_the_filing_schema(tmp_path) -> None:
    lane = _materialized_lane(tmp_path)
    capture_fif_filing_packages(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=lane["issuers"],
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=CAPTURE_CLOCK,
    )
    from xml.etree import ElementTree as ET

    for accession in lane["identity"]["accessions"]:
        fixture = ROOT / GOLDEN_AAPL_FIXTURES[accession]
        schema_name = next(
            path.name
            for path in (fixture / "members").iterdir()
            if path.name.endswith(".xsd")
        )
        root = ET.parse(fixture / "members" / schema_name).getroot()
        expected: dict[str, str] = {}
        for element in root.iter():
            if not element.tag.endswith("roleType"):
                continue
            definition = next(
                (child.text for child in element if child.tag.endswith("definition")),
                None,
            )
            if not definition or " - Statement - " not in definition:
                continue
            title = definition.split(" - Statement - ", 1)[1]
            for kind, needle in (
                ("income_statement", "OPERATIONS"),
                ("balance_sheet", "BALANCE SHEET"),
                ("cash_flow", "CASH FLOW"),
            ):
                if needle in title.upper() and kind not in expected:
                    if "Parenthetical" in title:
                        continue
                    expected[kind] = element.get("roleURI")
        package_dir = package_dir_for(lane["archive_root"], lane["identity"]["cik"], accession)
        manifest = json.loads(
            (package_dir / "package_manifest.json").read_text(encoding="utf-8")
        )
        minted = manifest["statement_roles"]
        assert set(minted) == {"income_statement", "balance_sheet", "cash_flow"}
        for kind, role_uri in expected.items():
            assert minted[kind]["role_uri"] == role_uri
        # mint_statement_roles is pure and re-derivable from the schema bytes.
        schema_bytes = (fixture / "members" / schema_name).read_bytes()
        assert mint_statement_roles(schema_bytes) == minted


def _schema_with_roles(*roles: tuple[str, str]) -> bytes:
    """A minimal filing schema declaring ``(role_uri, definition)`` roleTypes."""
    body = "".join(
        f'<link:roleType roleURI="{uri}" id="r{index}">'
        f"<link:definition>{definition}</link:definition>"
        '<link:usedOn>link:presentationLink</link:usedOn>'
        "</link:roleType>"
        for index, (uri, definition) in enumerate(roles)
    )
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" '
        'xmlns:link="http://www.xbrl.org/2003/linkbase">'
        f"<xs:annotation><xs:appinfo>{body}</xs:appinfo></xs:annotation>"
        "</xs:schema>"
    ).encode("utf-8")


def test_statement_roles_titled_results_of_operations_and_financial_position() -> None:
    # Shaped on an issuer whose statements are "Consolidated Results of
    # Operations" / "Consolidated Financial Position"; its "Income taxes"
    # disclosure must not stand in for the income statement.
    schema = _schema_with_roles(
        ("http://x.test/role/Cover", "0000001 - Document - Cover Page"),
        (
            "http://x.test/role/Results",
            "0000002 - Statement - Consolidated Results of Operations for the Years Ended December 31",
        ),
        (
            "http://x.test/role/Comprehensive",
            "0000003 - Statement - Consolidated Comprehensive Income (Loss) for the Years Ended December 31",
        ),
        (
            "http://x.test/role/Position",
            "0000004 - Statement - Consolidated Financial Position at December 31",
        ),
        (
            "http://x.test/role/PositionParen",
            "0000005 - Statement - Consolidated Financial Position at December 31 (Parenthetical)",
        ),
        (
            "http://x.test/role/CashFlow",
            "0000006 - Statement - Consolidated Statement of Cash Flow for the Years Ended December 31",
        ),
        ("http://x.test/role/IncomeTaxes", "0000040 - Disclosure - Income taxes"),
    )
    minted = mint_statement_roles(schema)
    assert minted == {
        "income_statement": {
            "role_uri": "http://x.test/role/Results",
            "title": "Consolidated Results of Operations for the Years Ended December 31",
            "title_search": "Consolidated Results of Operations for the Years Ended December 31",
        },
        "balance_sheet": {
            "role_uri": "http://x.test/role/Position",
            "title": "Consolidated Financial Position at December 31",
            "title_search": "Consolidated Financial Position at December 31",
        },
        "cash_flow": {
            "role_uri": "http://x.test/role/CashFlow",
            "title": "Consolidated Statement of Cash Flow for the Years Ended December 31",
            "title_search": "Consolidated Statement of Cash Flow for the Years Ended December 31",
        },
    }


def test_statement_role_outranks_an_earlier_needle_on_a_disclosure() -> None:
    # "Consolidated Statement of Income" is reached only by the late "INCOME"
    # needle, while a parent-company disclosure matches the earlier "INCOME
    # STATEMENT" needle; the issuer's own statement role still wins.
    schema = _schema_with_roles(
        (
            "http://x.test/role/Income",
            "1000002 - Statement - Consolidated Statement of Income",
        ),
        (
            "http://x.test/role/Comprehensive",
            "1000003 - Statement - Consolidated Statement of Comprehensive Income",
        ),
        (
            "http://x.test/role/Balance",
            "1000004 - Statement - Consolidated Balance Sheet",
        ),
        (
            "http://x.test/role/CashFlows",
            "1000007 - Statement - Consolidated Statement of Cash Flows",
        ),
        (
            "http://x.test/role/ParentIncome",
            "9952201 - Disclosure - Parent Company Information - Income Statement (Details)",
        ),
    )
    minted = mint_statement_roles(schema)
    assert minted["income_statement"]["role_uri"] == "http://x.test/role/Income"
    assert minted["income_statement"]["title_search"] == "Consolidated Statement of Income"
    assert minted["balance_sheet"]["role_uri"] == "http://x.test/role/Balance"
    assert minted["cash_flow"]["role_uri"] == "http://x.test/role/CashFlows"


def test_statement_of_financial_condition_is_a_balance_sheet() -> None:
    schema = _schema_with_roles(
        (
            "http://x.test/role/Earnings",
            "2000002 - Statement - Consolidated Statements of Earnings",
        ),
        (
            "http://x.test/role/Condition",
            "2000004 - Statement - Consolidated Statements of Financial Condition",
        ),
        (
            "http://x.test/role/CashFlows",
            "2000006 - Statement - Consolidated Statements of Cash Flows",
        ),
        ("http://x.test/role/IncomeTaxes", "2000090 - Disclosure - Income Taxes"),
    )
    roles = CAP._statement_role_candidates(schema)
    assert CAP._pick_statement_role(roles, "balance_sheet")["role_uri"] == (
        "http://x.test/role/Condition"
    )
    # "Earnings" names no income needle and the "Income Taxes" disclosure is
    # never a candidate once the schema categorizes Statements, so the mint is
    # a typed refusal for the income statement rather than a guessed role.
    assert CAP._pick_statement_role(roles, "income_statement") is None
    with pytest.raises(CAP.FifMemberCaptureError) as excinfo:
        mint_statement_roles(schema)
    assert excinfo.value.code == "statement_roles_mint_failed"


def test_statement_role_search_falls_back_to_every_category() -> None:
    # A schema whose definitions carry no "Statement" category still mints:
    # the fallback searches every role, as before.
    schema = _schema_with_roles(
        ("http://x.test/role/Ops", "CONSOLIDATED STATEMENTS OF OPERATIONS"),
        ("http://x.test/role/Balance", "CONSOLIDATED BALANCE SHEETS"),
        ("http://x.test/role/CashFlows", "CONSOLIDATED STATEMENTS OF CASH FLOWS"),
    )
    minted = mint_statement_roles(schema)
    assert {kind: spec["role_uri"] for kind, spec in minted.items()} == {
        "income_statement": "http://x.test/role/Ops",
        "balance_sheet": "http://x.test/role/Balance",
        "cash_flow": "http://x.test/role/CashFlows",
    }
    assert [is_statement for _, _, is_statement in CAP._statement_role_candidates(schema)] == [
        False,
        False,
        False,
    ]


def test_disclosure_naming_financial_position_never_binds_the_balance_sheet() -> None:
    # A "Statement of Condition" names no balance-sheet needle; a derivatives
    # disclosure "in Statement of Financial Position" and an MD&A "Financial
    # Condition" disclosure must not stand in for it.
    schema = _schema_with_roles(
        (
            "http://x.test/role/Income",
            "0000002 - Statement - Consolidated Statement of Income",
        ),
        (
            "http://x.test/role/Condition",
            "0000004 - Statement - Consolidated Statement of Condition",
        ),
        (
            "http://x.test/role/CashFlows",
            "0000006 - Statement - Consolidated Statement of Cash Flows",
        ),
        (
            "http://x.test/role/Deriv",
            "0000150 - Disclosure - Derivative Financial Instruments - Fair Value of "
            "Derivatives in Statement of Financial Position (Details)",
        ),
        (
            "http://x.test/role/Reg",
            "0000160 - Disclosure - Regulatory Matters - Capital and Financial Condition (Details)",
        ),
    )
    roles = CAP._statement_role_candidates(schema)
    assert CAP._pick_statement_role(roles, "balance_sheet") is None
    with pytest.raises(CAP.FifMemberCaptureError) as excinfo:
        mint_statement_roles(schema)
    assert excinfo.value.code == "statement_roles_mint_failed"


def test_category_less_fallback_searches_only_the_original_needles() -> None:
    # Without any Statement category the search covers every role, but only
    # with the original needles: a derivatives table titled "... Statement of
    # Financial Position" is never guessed to be the balance sheet.
    schema = _schema_with_roles(
        ("http://x.test/role/Ops", "CONSOLIDATED STATEMENTS OF OPERATIONS"),
        (
            "http://x.test/role/Deriv",
            "FAIR VALUE OF DERIVATIVES IN STATEMENT OF FINANCIAL POSITION (DETAILS)",
        ),
        ("http://x.test/role/CashFlows", "CONSOLIDATED STATEMENTS OF CASH FLOWS"),
    )
    roles = CAP._statement_role_candidates(schema)
    assert CAP._pick_statement_role(roles, "income_statement")["role_uri"] == (
        "http://x.test/role/Ops"
    )
    assert CAP._pick_statement_role(roles, "balance_sheet") is None


def test_statement_category_survives_wrapped_definition_whitespace() -> None:
    schema = _schema_with_roles(
        (
            "http://x.test/role/IS",
            "0000002 - Statement -\n  CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS (Unaudited)",
        ),
        (
            "http://x.test/role/Seg",
            "0000005 -  Statement - STATEMENTS OF OPERATIONS - SEGMENT",
        ),
    )
    roles = CAP._statement_role_candidates(schema)
    assert roles == [
        (
            "http://x.test/role/IS",
            "CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS (Unaudited)",
            True,
        ),
        ("http://x.test/role/Seg", "STATEMENTS OF OPERATIONS - SEGMENT", True),
    ]
    picked = CAP._pick_statement_role(roles, "income_statement")
    assert picked["role_uri"] == "http://x.test/role/IS"
    assert picked["title_search"] == "CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS"


def test_original_needles_outrank_the_statement_only_needles() -> None:
    # Needle-major order: an earlier Statement role reached only by a
    # statement-only needle loses to a later one reached by an original needle.
    schema = _schema_with_roles(
        (
            "http://x.test/role/SegmentResults",
            "0000002 - Statement - Segment Results of Operations",
        ),
        (
            "http://x.test/role/SubsidiaryCondition",
            "0000003 - Statement - Financial Condition of the Insurance Subsidiary",
        ),
        (
            "http://x.test/role/Income",
            "0000004 - Statement - Consolidated Statement of Income",
        ),
        (
            "http://x.test/role/Balance",
            "0000005 - Statement - Consolidated Balance Sheets",
        ),
    )
    roles = CAP._statement_role_candidates(schema)
    assert CAP._pick_statement_role(roles, "income_statement")["role_uri"] == (
        "http://x.test/role/Income"
    )
    assert CAP._pick_statement_role(roles, "balance_sheet")["role_uri"] == (
        "http://x.test/role/Balance"
    )


def test_already_retained_accession_is_skipped_and_clock_reused(tmp_path) -> None:
    lane = _materialized_lane(tmp_path)
    capture_fif_filing_packages(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=lane["issuers"],
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=CAPTURE_CLOCK,
    )
    fetched_before = list(lane["collector"].fetched)
    report = capture_fif_filing_packages(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=lane["issuers"],
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=LATER_CAPTURE_CLOCK,
    )
    assert lane["collector"].fetched == fetched_before  # nothing re-fetched
    rows = report["issuers"][0]["accessions"]
    assert [row["outcome"] for row in rows] == ["retained_reused", "retained_reused"]
    for row in rows:
        assert row["reused"] is True
        assert row["capture_recorded_at"] == CAPTURE_CLOCK  # never re-stamped
    for accession in lane["identity"]["accessions"]:
        package_dir = package_dir_for(lane["archive_root"], lane["identity"]["cik"], accession)
        manifest = json.loads(
            (package_dir / "package_manifest.json").read_text(encoding="utf-8")
        )
        assert manifest["capture_recorded_at"] == CAPTURE_CLOCK


def test_read_retained_packages_digest_verifies(tmp_path) -> None:
    lane = _materialized_lane(tmp_path)
    capture_fif_filing_packages(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=lane["issuers"],
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=CAPTURE_CLOCK,
    )
    packages = read_retained_fif_packages(
        lane["archive_root"],
        cik=lane["identity"]["cik"],
        accessions=lane["identity"]["accessions"],
    )
    assert [package.accession for package in packages] == sorted(lane["identity"]["accessions"])
    victim = packages[0].package_dir / "members"
    member_file = next(path for path in sorted(victim.iterdir()))
    member_file.write_bytes(member_file.read_bytes()[:-1])
    with pytest.raises(FifMemberCaptureError) as caught:
        read_retained_fif_packages(
        lane["archive_root"],
        cik=lane["identity"]["cik"],
        accessions=lane["identity"]["accessions"],
    )
    assert caught.value.code == "package_bytes_mismatch"


def test_malformed_member_is_a_typed_refusal(tmp_path) -> None:
    lane = _materialized_lane(tmp_path)
    identity = lane["identity"]
    first_accession = identity["accessions"][0]
    empty_name = next(
        path.name
        for path in sorted((ROOT / GOLDEN_AAPL_FIXTURES[first_accession] / "members").iterdir())
        if path.name.endswith(".xsd")
    )
    lane["collector"]._served[first_accession.replace("-", "")][empty_name] = b""
    report = _capture_report(lane)
    assert report["issuers"][0]["accessions"][0]["outcome"] == (
        "member_capture_failed:malformed_member"
    )


def _capture_report(lane) -> dict:
    return capture_fif_filing_packages(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=lane["issuers"],
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=CAPTURE_CLOCK,
    )


def test_d3_non_json_archive_index_is_typed_malformed_member(tmp_path) -> None:
    """D3: an HTML throttle page served as index.json (status-200 garbage) must
    be a typed row refusal, never an untyped JSONDecodeError that aborts the
    whole capture run."""
    lane = _materialized_lane(tmp_path)
    identity = lane["identity"]
    accession_key = identity["accessions"][0].replace("-", "")
    lane["collector"]._served[accession_key]["index.json"] = b"<html>throttle</html>"
    report = _capture_report(lane)
    assert report["issuers"][0]["accessions"][0]["outcome"] == (
        "member_capture_failed:malformed_member"
    )
    assert report["issuers"][0]["accessions"][1]["outcome"] == "captured"


def test_d3_wrong_shape_archive_index_is_typed_malformed_member(tmp_path) -> None:
    """D3: JSON that parses but is not {directory: {item: [dicts]}} is the same
    typed refusal — a truncated-but-parseable index must not crash untyped."""
    lane = _materialized_lane(tmp_path)
    identity = lane["identity"]
    accession_key = identity["accessions"][0].replace("-", "")
    for bogus in (
        b'{"directory": {}}',                  # item missing
        b'{"directory": {"item": "not-a-list"}}',  # item not a list
        b'{"directory": {"item": ["plain-string"]}}',  # rows not dicts
        b'{"no_directory": true}',             # directory missing
        b'[1, 2, 3]',                          # not an object at all
    ):
        lane["collector"]._served[accession_key]["index.json"] = bogus
        report = _capture_report(lane)
        assert report["issuers"][0]["accessions"][0]["outcome"] == (
            "member_capture_failed:malformed_member"
        ), bogus


def test_member_byte_ceiling_enforced(tmp_path, monkeypatch) -> None:
    lane = _materialized_lane(tmp_path)
    monkeypatch.setattr(CAP, "MAX_MEMBER_BYTES", 64)
    report = _capture_report(lane)
    outcomes = [row["outcome"] for row in report["issuers"][0]["accessions"]]
    assert all(item == "member_capture_failed:member_oversize" for item in outcomes)


def test_member_count_ceiling_enforced(tmp_path, monkeypatch) -> None:
    lane = _materialized_lane(tmp_path)
    monkeypatch.setattr(CAP, "MAX_INDEX_MEMBERS", 1)
    report = _capture_report(lane)
    outcomes = [row["outcome"] for row in report["issuers"][0]["accessions"]]
    assert all(item == "member_capture_failed:member_count_exceeded" for item in outcomes)


def test_run_byte_budget_enforced(tmp_path) -> None:
    lane = _materialized_lane(tmp_path)
    first_accession = lane["identity"]["accessions"][0].replace("-", "")
    index_bytes = lane["served"][first_accession]["index.json"]
    report = capture_fif_filing_packages(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=lane["issuers"],
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=CAPTURE_CLOCK,
        run_budget_bytes=len(index_bytes) + 1,
    )
    outcomes = [row["outcome"] for row in report["issuers"][0]["accessions"]]
    assert all(item == "member_capture_failed:run_budget_exceeded" for item in outcomes)


def test_d12_index_member_count_refused_before_member_fetch(tmp_path, monkeypatch) -> None:
    """D12: the member-count ceiling fires on the INDEX listing, before any
    member fetch — the index itself is the only fetch the accession makes."""
    lane = _materialized_lane(tmp_path)
    monkeypatch.setattr(CAP, "MAX_INDEX_MEMBERS", 1)
    report = _capture_report(lane)
    outcomes = [row["outcome"] for row in report["issuers"][0]["accessions"]]
    assert all(item == "member_capture_failed:member_count_exceeded" for item in outcomes)
    assert lane["collector"].fetched == ["index.json", "index.json"]


def test_d12_index_listed_member_size_refused_before_fetch(tmp_path, monkeypatch) -> None:
    """D12: a role member whose INDEX-LISTED size exceeds MAX_MEMBER_BYTES is
    refused before that member (or any sibling member) is fetched. The
    ceiling sits strictly above every index payload (the index rides the same
    _fetch_member_bytes ceiling) and strictly below every role member."""
    lane = _materialized_lane(tmp_path)
    index_limit = max(
        len(members["index.json"]) for members in lane["served"].values()
    )
    member_sizes = [
        len(payload)
        for members in lane["served"].values()
        for name, payload in members.items()
        if name != "index.json"
    ]
    limit = index_limit + 1
    assert min(member_sizes) > limit  # the ceiling bites members only
    monkeypatch.setattr(CAP, "MAX_MEMBER_BYTES", limit)
    report = _capture_report(lane)
    outcomes = [row["outcome"] for row in report["issuers"][0]["accessions"]]
    assert all(item == "member_capture_failed:member_oversize" for item in outcomes)
    assert lane["collector"].fetched == ["index.json", "index.json"]


def test_d12_planned_budget_refused_before_member_fetch(tmp_path) -> None:
    """D12: when the index states sizes, the planned five-member sum is
    checked against the remaining run budget before ANY member fetch — a
    spent budget never still downloads members one at a time."""
    lane = _materialized_lane(tmp_path)
    identity = lane["identity"]
    first_accession = identity["accessions"][0].replace("-", "")
    served = lane["served"][first_accession]
    index_len = len(served["index.json"])
    stem = next(
        name for name in sorted(served) if name.endswith(".xsd")
    ).rsplit(".", 1)[0]
    first_member_len = len(served[f"{stem}.xsd"])
    # Enough budget for the index and ONE member (the pre-rev1 code fetched
    # that member before refusing the second), never for the planned five.
    budget = index_len + first_member_len + 1
    report = capture_fif_filing_packages(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=lane["issuers"],
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=CAPTURE_CLOCK,
        run_budget_bytes=budget,
    )
    outcomes = [row["outcome"] for row in report["issuers"][0]["accessions"]]
    assert all(item == "member_capture_failed:run_budget_exceeded" for item in outcomes)
    # ZERO member fetches anywhere in the run — only the two indexes.
    assert lane["collector"].fetched == ["index.json", "index.json"]


def test_submissions_identity_mismatch_is_typed(tmp_path) -> None:
    lane = _materialized_lane(tmp_path)
    identity = lane["identity"]
    first = identity["accessions"][0]
    other = identity["accessions"][1]
    # Cross-claim: the Submissions row for the FIRST accession names the
    # SECOND accession's primary document.
    submissions = _synthetic_submissions(identity)
    recent = submissions["filings"]["recent"]
    recent["primaryDocument"][0] = str(
        identity["manifests"][other]["primary_document"]
    )
    payload = json.dumps(submissions).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    object_path = f"{identity['cik']}/submissions/{digest[:32]}.json.gz"
    target = lane["raw_root"] / object_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(gzip.compress(payload))
    pointer = lane["raw_root"] / identity["cik"] / "submissions" / "latest.json"
    pointer.write_text(
        json.dumps(
            {
                "schema": "fundamental_forensics_retrieval.v1",
                "cik": identity["cik"],
                "endpoint": "submissions",
                "url": f"https://data.sec.gov/submissions/CIK{identity['cik']}.json",
                "retrieved_at": CAPTURE_CLOCK,
                "sha256": digest,
                "bytes": len(payload),
                "object_path": object_path,
                "http_etag": None,
                "http_last_modified": None,
            }
        ),
        encoding="utf-8",
    )
    report = _capture_report(lane)
    # The FIRST (tampered) accession refuses; the untouched one still captures.
    outcomes = [row["outcome"] for row in report["issuers"][0]["accessions"]]
    assert outcomes[0] == "member_capture_failed:identity_mismatch"
    assert outcomes[1] == "captured"


def test_accession_absent_from_submissions_is_typed(tmp_path) -> None:
    identity = _fixture_identity()
    original = str(identity["accessions"][0])
    invented = original[:-1] + ("8" if original[-1] != "8" else "7")
    assert invented != original
    lane = _materialized_lane(tmp_path, extra_retained=invented)
    issuers = _contract_issuers(identity)
    # The invented row carries identity[0]'s form + filing_date (R8 shape);
    # it is absent from BOTH the recent window and every page.
    issuers[0]["accessions"] = [
        {
            "accession": invented,
            "form": str(identity["manifests"][original]["form"]),
            "filing_date": _filing_date_for(identity["accessions"], original),
        }
    ]
    report = capture_fif_filing_packages(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=issuers,
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=CAPTURE_CLOCK,
    )
    row = report["issuers"][0]["accessions"][0]
    assert row["outcome"] == f"member_capture_failed:accession_not_in_submissions"


def test_unretained_primary_is_reported_not_fetched(tmp_path) -> None:
    lane = _materialized_lane(tmp_path)
    identity = lane["identity"]
    original = str(identity["accessions"][0])
    invented = original[:-1] + ("8" if original[-1] != "8" else "7")
    assert invented != original
    issuers = _contract_issuers(identity)
    issuers[0]["accessions"] = [{"accession": invented}]
    report = capture_fif_filing_packages(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=issuers,
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=CAPTURE_CLOCK,
    )
    row = report["issuers"][0]["accessions"][0]
    assert row["outcome"] == "no_retained_primary"
    assert lane["collector"].fetched == []


def test_find_retained_primary_manifest_requires_a_stored_primary(tmp_path) -> None:
    lane = _materialized_lane(tmp_path)
    identity = lane["identity"]
    found = find_retained_primary_manifest(
        lane["archive_root"], cik=identity["cik"], accession=identity["accessions"][0]
    )
    assert found is not None
    assert any(
        item.get("role") == "primary" and item.get("availability") == "stored"
        for item in found["documents"]
    )


def test_repository_fixture_inputs_are_refused() -> None:
    fixture_root = ROOT / "tests" / "fixtures" / "fundamental_forensics"
    with pytest.raises(FifMemberCaptureError) as caught:
        refuse_repository_fixture_inputs(fixture_root)
    assert caught.value.code == "golden_input_refused"
    with pytest.raises(FifMemberCaptureError) as caught:
        refuse_repository_fixture_inputs(ROOT, fixture_root)
    assert caught.value.code == "golden_input_refused"
    refuse_repository_fixture_inputs(ROOT / "engine")  # lawful root passes


def test_d4_stray_non_contract_package_dir_is_ignored(tmp_path) -> None:
    """D4: the reader iterates the CONTRACT accessions only, never a directory
    listing — a stray (dropped-from-contract or foreign) accession directory
    under the CIK is never read back, even when it holds a valid package."""
    lane = _materialized_lane(tmp_path)
    identity = lane["identity"]
    capture_fif_filing_packages(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=lane["issuers"],
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=CAPTURE_CLOCK,
    )
    # Clone one finished package under a stray accession name (valid manifest,
    # valid digests — only the directory name is foreign).
    stray_accession = identity["accessions"][0][:-1] + "9"
    if stray_accession in identity["accessions"]:
        stray_accession = identity["accessions"][0][:-1] + "8"
    assert stray_accession not in identity["accessions"]
    source = package_dir_for(lane["archive_root"], identity["cik"], identity["accessions"][0])
    stray = package_dir_for(lane["archive_root"], identity["cik"], stray_accession)
    shutil.copytree(source, stray)
    packages = read_retained_fif_packages(
        lane["archive_root"],
        cik=identity["cik"],
        accessions=identity["accessions"],
    )
    assert [package.accession for package in packages] == sorted(identity["accessions"])


def test_d4_missing_manifest_is_package_manifest_malformed(tmp_path) -> None:
    """D4: a non-empty package directory without package_manifest.json is a
    typed refusal — never the old silent skip (a half-restored package must
    never quietly shrink or poison the admitted set)."""
    lane = _materialized_lane(tmp_path)
    identity = lane["identity"]
    capture_fif_filing_packages(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=lane["issuers"],
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=CAPTURE_CLOCK,
    )
    victim = package_dir_for(
        lane["archive_root"], identity["cik"], identity["accessions"][0]
    )
    (victim / "package_manifest.json").unlink()
    with pytest.raises(FifMemberCaptureError) as caught:
        read_retained_fif_packages(
            lane["archive_root"],
            cik=identity["cik"],
            accessions=identity["accessions"],
        )
    assert caught.value.code == "package_manifest_malformed"


def test_d4_malformed_manifest_is_package_manifest_malformed(tmp_path) -> None:
    """D4 (pin): non-JSON manifest bytes keep the typed refusal on the
    contract-scoped read path. (This case was already typed inside
    _verify_retained_package before rev1 — pinned here so the reader's new
    iteration shape cannot lose it.)"""
    lane = _materialized_lane(tmp_path)
    identity = lane["identity"]
    capture_fif_filing_packages(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=lane["issuers"],
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=CAPTURE_CLOCK,
    )
    victim = package_dir_for(
        lane["archive_root"], identity["cik"], identity["accessions"][0]
    )
    (victim / "package_manifest.json").write_text("{ truncated", encoding="utf-8")
    with pytest.raises(FifMemberCaptureError) as caught:
        read_retained_fif_packages(
            lane["archive_root"],
            cik=identity["cik"],
            accessions=identity["accessions"],
        )
    assert caught.value.code == "package_manifest_malformed"


def _rewrite_manifest_field(lane: dict, accession: str, field: str, value: str) -> None:
    manifest_path = (
        package_dir_for(lane["archive_root"], lane["identity"]["cik"], accession)
        / "package_manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest[field] = value
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


def test_d4_manifest_cik_mismatch_is_package_manifest_malformed(tmp_path) -> None:
    """D4: the verified manifest's cik must equal the path's CIK — a package
    cross-claimed under another issuer's directory is a typed refusal."""
    lane = _materialized_lane(tmp_path)
    identity = lane["identity"]
    capture_fif_filing_packages(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=lane["issuers"],
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=CAPTURE_CLOCK,
    )
    other_cik = identity["cik"][:-1] + str((int(identity["cik"][-1]) + 1) % 10)
    _rewrite_manifest_field(lane, identity["accessions"][0], "cik", other_cik)
    with pytest.raises(FifMemberCaptureError) as caught:
        read_retained_fif_packages(
            lane["archive_root"],
            cik=identity["cik"],
            accessions=identity["accessions"],
        )
    assert caught.value.code == "package_manifest_malformed"


def test_d4_manifest_accession_mismatch_is_package_manifest_malformed(tmp_path) -> None:
    """D4: the verified manifest's accession must equal the path's accession."""
    lane = _materialized_lane(tmp_path)
    identity = lane["identity"]
    capture_fif_filing_packages(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=lane["issuers"],
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=CAPTURE_CLOCK,
    )
    invented = identity["accessions"][0][:-1] + "7"
    _rewrite_manifest_field(lane, identity["accessions"][0], "accession", invented)
    with pytest.raises(FifMemberCaptureError) as caught:
        read_retained_fif_packages(
            lane["archive_root"],
            cik=identity["cik"],
            accessions=identity["accessions"],
        )
    assert caught.value.code == "package_manifest_malformed"


def test_golden_schema_manifest_is_refused(tmp_path) -> None:
    lane = _materialized_lane(tmp_path)
    identity = lane["identity"]
    accession = identity["accessions"][0]
    package_dir = package_dir_for(lane["archive_root"], identity["cik"], accession)
    package_dir.mkdir(parents=True)
    manifest = json.loads(
        (ROOT / GOLDEN_AAPL_FIXTURES[accession] / "package_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    (package_dir / "package_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    with pytest.raises(FifMemberCaptureError) as caught:
        read_retained_fif_packages(
        lane["archive_root"], cik=identity["cik"], accessions=identity["accessions"]
    )
    assert caught.value.code == "golden_input_refused"


def test_d9_unknown_package_schema_is_refused(tmp_path) -> None:
    """D9: the schema check is an ALLOW-list on FIF_MEMBER_CAPTURE_PACKAGE_SCHEMA.
    A manifest claiming an unknown schema string (or no schema at all) used to
    pass the one-entry deny-list and be read back as a package."""
    lane = _materialized_lane(tmp_path)
    identity = lane["identity"]
    capture_fif_filing_packages(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=lane["issuers"],
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=CAPTURE_CLOCK,
    )
    manifest_path = (
        package_dir_for(lane["archive_root"], identity["cik"], identity["accessions"][0])
        / "package_manifest.json"
    )
    original = json.loads(manifest_path.read_text(encoding="utf-8"))

    def _rewrite(schema_value):
        manifest = dict(original)
        if schema_value is _MISSING:
            manifest.pop("schema", None)
        else:
            manifest["schema"] = schema_value
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    for bogus in ("fundamental_forensics.golden_filing_package/v2", "", _MISSING):
        _rewrite(bogus)
        with pytest.raises(FifMemberCaptureError) as caught:
            read_retained_fif_packages(
                lane["archive_root"],
                cik=identity["cik"],
                accessions=identity["accessions"],
            )
        assert caught.value.code == "golden_input_refused", bogus


class _Missing:
    """Sentinel: drop the schema key entirely."""


_MISSING = _Missing()


def test_no_ticker_or_cik_literal_in_member_capture_module() -> None:
    source = (
        ROOT / "engine" / "fundamental_forensics" / "fif_member_capture.py"
    ).read_text(encoding="utf-8")
    contract = json.loads(
        (
            ROOT
            / "config"
            / "fundamental_forensics"
            / "coverage"
            / "five_issuer_v1.json"
        ).read_text(encoding="utf-8")
    )
    for issuer in contract["issuers"]:
        assert issuer["ticker"] not in source
        assert issuer["cik"] not in source


# ---------------------------------------------------------------------------
# ERRATA E1: verify-before-reuse fails closed, never re-mints a clock
# ---------------------------------------------------------------------------


def test_retained_package_integrity_codes_are_the_errata_set() -> None:
    assert CAP.RETAINED_PACKAGE_INTEGRITY_CODES == frozenset(
        {
            "package_bytes_mismatch",
            "package_manifest_malformed",
            "inventory_mismatch",
            "golden_input_refused",
            # C0-c E5-e: a retained submissions page that fails its receipt
            # verification is run-level integrity (added by ERRATA-5).
            "submissions_page_receipt_mismatch",
        }
    )
    assert CAP.RETAINED_PACKAGE_INTEGRITY_CODES <= CAP._REFUSAL_CODES


def test_tampered_retained_member_never_recaptures_or_restamps(tmp_path) -> None:
    lane = _materialized_lane(tmp_path)
    identity = lane["identity"]
    capture_fif_filing_packages(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=lane["issuers"],
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=CAPTURE_CLOCK,
    )
    victim_dir = package_dir_for(
        lane["archive_root"], identity["cik"], identity["accessions"][0]
    )
    manifest_before = (victim_dir / "package_manifest.json").read_bytes()
    member = sorted((victim_dir / "members").iterdir())[0]
    member.write_bytes(member.read_bytes()[:-1])
    fetched_before = list(lane["collector"].fetched)
    report = capture_fif_filing_packages(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=lane["issuers"],
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=LATER_CAPTURE_CLOCK,
    )
    rows = report["issuers"][0]["accessions"]
    assert rows[0]["outcome"] == "member_capture_failed:package_bytes_mismatch"
    assert rows[1]["outcome"] == "retained_reused"
    assert rows[1]["capture_recorded_at"] == CAPTURE_CLOCK
    # No row anywhere carries tonight's clock: the tampered package was NOT
    # re-captured, so no new capture clock exists in the report.
    assert all(row["capture_recorded_at"] != LATER_CAPTURE_CLOCK for row in rows)
    assert lane["collector"].fetched == fetched_before
    # The on-disk manifest (and its capture_recorded_at) is untouched.
    assert (victim_dir / "package_manifest.json").read_bytes() == manifest_before


def test_partial_package_dir_is_a_typed_refusal_not_a_recapture(tmp_path) -> None:
    lane = _materialized_lane(tmp_path)
    identity = lane["identity"]
    capture_fif_filing_packages(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=lane["issuers"],
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=CAPTURE_CLOCK,
    )
    victim_dir = package_dir_for(
        lane["archive_root"], identity["cik"], identity["accessions"][0]
    )
    members_before = {
        path.name: path.read_bytes() for path in sorted((victim_dir / "members").iterdir())
    }
    (victim_dir / "package_manifest.json").unlink()
    fetched_before = list(lane["collector"].fetched)
    report = capture_fif_filing_packages(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=lane["issuers"],
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=LATER_CAPTURE_CLOCK,
    )
    rows = report["issuers"][0]["accessions"]
    assert rows[0]["outcome"] == "member_capture_failed:package_manifest_malformed"
    assert rows[1]["outcome"] == "retained_reused"
    # ZERO fetches for the manifest-less accession (and none for the reused one).
    assert lane["collector"].fetched == fetched_before
    # Member files are untouched and the package was not re-minted.
    members_after = {
        path.name: path.read_bytes() for path in sorted((victim_dir / "members").iterdir())
    }
    assert members_after == members_before
    assert not (victim_dir / "package_manifest.json").exists()


def test_absent_and_empty_package_dirs_still_capture(tmp_path) -> None:
    lane = _materialized_lane(tmp_path)
    identity = lane["identity"]
    # An EMPTY package dir (restore created the directory but nothing else)
    # still captures normally, as does the absent one.
    empty_dir = package_dir_for(
        lane["archive_root"], identity["cik"], identity["accessions"][1]
    )
    empty_dir.mkdir(parents=True)
    report = capture_fif_filing_packages(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=lane["issuers"],
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=CAPTURE_CLOCK,
    )
    assert [row["outcome"] for row in report["issuers"][0]["accessions"]] == [
        "captured",
        "captured",
    ]
    assert (empty_dir / "package_manifest.json").is_file()


def test_leftover_staging_dir_is_ignored_by_readers_and_capture(tmp_path) -> None:
    lane = _materialized_lane(tmp_path)
    identity = lane["identity"]
    capture_fif_filing_packages(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=lane["issuers"],
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=CAPTURE_CLOCK,
    )
    staging_root = lane["archive_root"] / CAP.PACKAGE_PREFIX / CAP.STAGING_DIR_NAME
    staging_root.mkdir(parents=True, exist_ok=True)
    leftover = staging_root / f"{identity['cik']}-{identity['accessions'][0]}-deadbeef"
    (leftover / CAP.MEMBERS_DIR).mkdir(parents=True)
    (leftover / CAP.MEMBERS_DIR / "schema.xsd").write_bytes(b"partial garbage")
    (leftover / CAP.MANIFEST_NAME).write_text("{ truncated", encoding="utf-8")
    # A dot-prefixed sibling inside the CIK dir is never read as a package.
    hidden = (
        lane["archive_root"] / CAP.PACKAGE_PREFIX / identity["cik"] / CAP.STAGING_DIR_NAME
    )
    hidden.mkdir(parents=True)
    (hidden / "junk").write_bytes(b"junk")
    packages = read_retained_fif_packages(
        lane["archive_root"], cik=identity["cik"], accessions=identity["accessions"]
    )
    assert [package.accession for package in packages] == sorted(identity["accessions"])
    fetched_before = list(lane["collector"].fetched)
    report = capture_fif_filing_packages(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=lane["issuers"],
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=LATER_CAPTURE_CLOCK,
    )
    assert [row["outcome"] for row in report["issuers"][0]["accessions"]] == [
        "retained_reused",
        "retained_reused",
    ]
    assert lane["collector"].fetched == fetched_before
    assert leftover.is_dir()  # ignored, never consumed or cleaned by readers


def test_successful_capture_leaves_no_staging_dir_behind(tmp_path) -> None:
    lane = _materialized_lane(tmp_path)
    identity = lane["identity"]
    capture_fif_filing_packages(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=lane["issuers"],
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=CAPTURE_CLOCK,
    )
    staging_root = lane["archive_root"] / CAP.PACKAGE_PREFIX / CAP.STAGING_DIR_NAME
    if staging_root.exists():
        assert not any(staging_root.iterdir())
    for accession in identity["accessions"]:
        package_dir = package_dir_for(lane["archive_root"], identity["cik"], accession)
        assert (package_dir / "package_manifest.json").is_file()
        assert (package_dir / "index.json").is_file()
        assert (package_dir / "sec_submissions_witness.json").is_file()
        assert (package_dir / "members").is_dir()


def test_capture_report_counts_files_and_bytes_written(tmp_path) -> None:
    lane = _materialized_lane(tmp_path)
    identity = lane["identity"]
    report = capture_fif_filing_packages(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=lane["issuers"],
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=CAPTURE_CLOCK,
    )
    expected_files = 0
    expected_bytes = 0
    for accession in identity["accessions"]:
        package_dir = package_dir_for(lane["archive_root"], identity["cik"], accession)
        files = [path for path in package_dir.rglob("*") if path.is_file()]
        expected_files += len(files)
        expected_bytes += sum(path.stat().st_size for path in files)
    assert report["package_files_written"] == expected_files
    assert report["package_bytes_written"] == expected_bytes
    # A fully reused night adds nothing to the snapshot.
    second = capture_fif_filing_packages(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=lane["issuers"],
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=LATER_CAPTURE_CLOCK,
    )
    assert second["package_files_written"] == 0
    assert second["package_bytes_written"] == 0


def test_cross_device_staging_is_a_typed_refusal_never_a_copy(tmp_path, monkeypatch) -> None:
    lane = _materialized_lane(tmp_path)
    identity = lane["identity"]
    real_stat = os.stat

    class _ForeignDevice:
        def __init__(self, inner: os.stat_result) -> None:
            self._inner = inner
            self.st_dev = inner.st_dev + 1  # a different filesystem

        def __getattr__(self, name: str):
            return getattr(self._inner, name)

    def fake_stat(path, *args, **kwargs):
        result = real_stat(path, *args, **kwargs)
        if str(path).endswith(CAP.STAGING_DIR_NAME):
            return _ForeignDevice(result)
        return result

    monkeypatch.setattr(os, "stat", fake_stat)
    report = capture_fif_filing_packages(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=lane["issuers"],
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=CAPTURE_CLOCK,
    )
    monkeypatch.undo()
    outcomes = [row["outcome"] for row in report["issuers"][0]["accessions"]]
    assert all(item == "member_capture_failed:staging_device_mismatch" for item in outcomes)
    # Never fell back to a copy: no package directory appeared at all.
    for accession in identity["accessions"]:
        assert not package_dir_for(
            lane["archive_root"], identity["cik"], accession
        ).exists()


# ---------------------------------------------------------------------------
# D13: the isolated, non-gating contract acquire lane (T4 harness)
# ---------------------------------------------------------------------------


def test_d13_t4_partial_acquire_retains_selected_manifests_and_syncs(
    tmp_path, monkeypatch
) -> None:
    """D13 T4: a PARTIAL bounded acquire — one issuer whose recent Submissions
    window holds a single 10-K (the motivating contract shape) — retains every
    selected manifest AND lands it in the latest synced snapshot, when run
    through ``run_operator_flow`` WITHOUT ``--require-complete-acquisition``
    (the isolated contract lane's invocation shape: acquire + reuse-local +
    sync + incremental-sync, no gate).

    Reuses the repo's existing acquisition fakes — ``_SubmissionsCollector``
    and ``_ArchiveCollector`` (tests/test_fundamental_forensics_acquisition.py)
    over the ``_submissions`` rows fixture — with the one-10-K row variant;
    the sync/restore legs ride the REAL source_sync over a LocalStore.
    """
    import json as _json

    from collectors import fundamental_forensics_acquisition as acquisition
    from collectors.edgar_forensics import endpoint_url, persist_response
    from engine.fundamental_forensics.source_sync import restore_source_roots
    from engine.research_vault.r2_store import LocalStore
    from scripts import run_fundamental_forensics_wave2 as operator
    from tests.test_fundamental_forensics_acquisition import (
        _ArchiveCollector,
        _SubmissionsCollector,
        _submissions,
    )

    def _one_ten_k_rows(cik: int) -> dict:
        """The fixture rows with every 10-K except FY2025 dropped, so the
        bounded selection finds exactly ONE 10-K comparable (1 of 2) — the
        same shape as a recent window that no longer reaches the prior 10-K."""
        rows = _submissions(cik)
        recent = rows["filings"]["recent"]
        keep = [
            index
            for index, (form, report_date) in enumerate(
                zip(recent["form"], recent["reportDate"])
            )
            if not (form == "10-K" and report_date != "2025-12-31")
        ]
        rows["filings"]["recent"] = {
            key: [value[index] for index in keep] for key, value in recent.items()
        }
        return rows

    class _OneTenKSubmissionsCollector(_SubmissionsCollector):
        def fetch(self, cik, endpoint, *, retrieved_at, max_response_bytes=None):
            cik10 = f"{int(cik):010d}"
            self.calls.append((cik10, endpoint, max_response_bytes))
            content = _json.dumps(_one_ten_k_rows(int(cik))).encode("utf-8")
            return persist_response(
                self.raw_root,
                cik=cik,
                endpoint=endpoint,
                url=endpoint_url(cik, endpoint),
                content=content,
                retrieved_at=retrieved_at,
            )

    def _acquire(**kwargs):
        return acquisition.acquire_bounded_filings(
            submissions_collector_factory=_OneTenKSubmissionsCollector,
            archive_collector_factory=_ArchiveCollector,
            **kwargs,
        )

    monkeypatch.setattr(operator, "acquire_bounded_filings", _acquire)
    monkeypatch.setattr(
        operator, "_user_agent", lambda root: "MastermindX D13 test bench test@example.invalid"
    )

    raw_root = tmp_path / "raw"
    archive_root = tmp_path / "archive"
    outcome = operator.run_operator_flow(
        root=tmp_path,
        targets=("FXT=1",),
        as_of="2026-08-01T23:59:59Z",
        recorded_at="2026-08-02T00:05:00Z",
        computed_at="2026-08-02T00:10:00Z",
        acquire=True,
        sync=True,
        incremental_sync=True,
        reuse_local_archive=True,
        require_complete_acquisition=False,
        raw_root=raw_root,
        archive_root=archive_root,
        observation_root=tmp_path / "observations-contract",
        local_store=tmp_path / "private-store",
    )

    acquired = outcome["results"]["acquire"]
    assert acquired["status"] == "partial"  # the 10-K shortfall, no exception
    forms = [
        (form["form"], len(form["selected_accessions"]), form["status"])
        for receipt in acquired["ticker_receipts"]
        for form in receipt["forms"]
    ]
    assert ("10-K", 1, "partial") in forms
    assert ("10-Q", 2, "complete") in forms

    cik = "0000000001"
    selected = [
        accession
        for receipt in acquired["ticker_receipts"]
        for form in receipt["forms"]
        for accession in form["selected_accessions"]
    ]
    assert len(selected) == 3  # 1 10-K + 2 10-Q
    # Every selected manifest exists under archive_root/manifests/<cik>/...
    for accession in selected:
        directory = archive_root / "manifests" / cik / accession
        assert directory.is_dir(), directory
        assert list(directory.glob("*.json")), directory

    # AND appears in the latest synced snapshot manifest: restoring the LATEST
    # snapshot into FRESH roots materializes every selected manifest again —
    # the public restore path follows the latest pointer, so a file landing
    # here proves the latest manifest names it.
    fresh_raw = tmp_path / "fresh-raw"
    fresh_archive = tmp_path / "fresh-archive"
    restored = restore_source_roots(
        raw_root=fresh_raw,
        archive_root=fresh_archive,
        store=LocalStore(tmp_path / "private-store"),
    )
    for accession in selected:
        assert list(
            (fresh_archive / "manifests" / cik / accession).glob("*.json")
        ), accession
    assert restored.to_dict()["restored_files"] >= 2 * len(selected) + 1


# ---------------------------------------------------------------------------
# C0-c ERRATA-5: the submissions-page witness (p1..p7)
# ---------------------------------------------------------------------------

from collectors.edgar_forensics import (  # noqa: E402
    historical_submissions_url,
    persist_response,
)


def _page_row_for(identity: dict, accession: str, filing_date: str) -> dict:
    manifest = identity["manifests"][identity["accessions"][0]]
    return {
        "accessionNumber": accession,
        "form": str(manifest["form"]),
        "filingDate": filing_date,
        "reportDate": str(manifest["period_of_report"]),
        "acceptanceDateTime": FIRST_ACCEPTED_AT,
        "primaryDocument": str(manifest["primary_document"]),
        "isXBRL": True,
        "isInlineXBRL": True,
    }


class _FakeSubmissionsCollector:
    """Offline stand-in for the historical-shard fetch (publish_latest=False)."""

    def __init__(self, raw_root: Path, pages: dict[str, dict], pacer) -> None:
        self.raw_root = Path(raw_root)
        self._pages = pages
        self._pacer = pacer
        self.page_fetches: list[str] = []

    def fetch_historical_submissions_file(
        self, cik, source_name, *, retrieved_at=None, max_response_bytes=None
    ):
        self._pacer.acquire()
        self.page_fetches.append(str(source_name))
        content = json.dumps(self._pages[str(source_name)]).encode("utf-8")
        return persist_response(
            self.raw_root,
            cik=cik,
            endpoint="submissions",
            url=historical_submissions_url(cik, source_name),
            content=content,
            retrieved_at=retrieved_at,
            publish_latest=False,
        )


class _FlakyArchiveCollector(_FakeCollector):
    """Fails one (accession, name) document exactly once (the failed night).

    Scoped to the accession directory so a shared member NAME under a sibling
    accession (same primary stem) is never the one that fails.
    """

    def __init__(self, cache_root, served, pacer, *, fail_documents=()):
        super().__init__(cache_root, served, pacer)
        self._fail_once = {(acc, name): 1 for acc, name in fail_documents}

    def fetch_document(
        self, document, *, retrieved_at=None, expected_sha256=None, max_document_bytes=None
    ):
        url = document["archive_url"]
        accession = url.rsplit("/", 2)[-2].replace("-", "")
        name = url.rsplit("/", 1)[-1]
        key = (accession, name)
        if self._fail_once.get(key):
            self._fail_once[key] -= 1
            self.fetched.append(name)
            raise RuntimeError(f"forced one-shot failure: {name}")
        return super().fetch_document(
            document,
            retrieved_at=retrieved_at,
            expected_sha256=expected_sha256,
            max_document_bytes=max_document_bytes,
        )


def _write_submissions_with_files(
    raw_root: Path, identity: dict, files: list[dict]
) -> None:
    """latest.json whose filings.files[] names the page inventory (E5-d)."""
    payload = json.dumps(
        {
            "cik": int(identity["cik"]),
            "name": "Synthetic Lane Issuer",
            "filings": {
                "recent": _synthetic_submissions(identity)["filings"]["recent"],
                "files": files,
            },
        }
    ).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    object_path = f"{identity['cik']}/submissions/{digest[:32]}.json.gz"
    target = raw_root / object_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(gzip.compress(payload))
    pointer = raw_root / identity["cik"] / "submissions" / "latest.json"
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text(
        json.dumps(
            {
                "schema": "fundamental_forensics_retrieval.v1",
                "cik": identity["cik"],
                "endpoint": "submissions",
                "url": f"https://data.sec.gov/submissions/CIK{identity['cik']}.json",
                "retrieved_at": CAPTURE_CLOCK,
                "sha256": digest,
                "bytes": len(payload),
                "object_path": object_path,
                "http_etag": None,
                "http_last_modified": None,
            }
        ),
        encoding="utf-8",
    )


def _page_witness_lane(
    tmp_path: Path,
    *,
    files: list[dict] | None = None,
    fail_member_once: str | None = None,
):
    """A capture lane with ONE page-row accession: outside recent, primary
    retained (the wave-2 shape), covered by a synthetic submissions page."""
    identity = _fixture_identity()
    outside = identity["accessions"][0][:-1] + "7"
    filing_date = str(identity["manifests"][identity["accessions"][0]]["filing_date"])
    page_name = f"CIK{identity['cik']}-submissions-001.json"
    raw_root = tmp_path / "raw"
    archive_root = tmp_path / "archive"
    raw_root.mkdir(parents=True)
    archive_root.mkdir(parents=True)
    if files is None:
        files = [{"name": page_name, "filingFrom": filing_date, "filingTo": filing_date}]
    _write_submissions_with_files(raw_root, identity, files)
    _retain_primaries(archive_root, identity, extra=outside)
    served = _fixture_member_bytes()
    served[outside.replace("-", "")] = dict(
        served[identity["accessions"][0].replace("-", "")]
    )
    pacer = _no_sleep_pacer()
    if fail_member_once is not None:
        collector = _FlakyArchiveCollector(
            archive_root,
            served,
            pacer,
            fail_documents=[(outside.replace("-", ""), fail_member_once)],
        )
    else:
        collector = _FakeCollector(archive_root, served, pacer)
    page_row = _page_row_for(identity, outside, filing_date)
    pages = {page_name: {key: [value] for key, value in page_row.items()}}
    submissions_collector = _FakeSubmissionsCollector(raw_root, pages, pacer)
    binding = {
        "issuer_id": identity["entity_id"],
        "issuer_cik": identity["cik"],
        "security_id": identity["security_id"],
        "listing_key": identity["listing_key"],
        "mic": "XNAS",
        "effective_at": "2023-05-09T00:00:00",
    }
    issuers = [
        {
            "cik": identity["cik"],
            "ticker": identity["ticker"],
            "legal_name": "Synthetic Lane Issuer",
            "security_master_binding": binding,
            "accessions": [
                {
                    "accession": a,
                    "form": str(identity["manifests"][a]["form"]),
                    "filing_date": _filing_date_for(identity["accessions"], a),
                }
                for a in identity["accessions"]
            ]
            + [
                {
                    "accession": outside,
                    "form": page_row["form"],
                    "filing_date": filing_date,
                }
            ],
        }
    ]
    return {
        "identity": identity,
        "raw_root": raw_root,
        "archive_root": archive_root,
        "collector": collector,
        "submissions_collector": submissions_collector,
        "pacer": pacer,
        "issuers": issuers,
        "outside": outside,
        "page_name": page_name,
        "page_row": page_row,
        "filing_date": filing_date,
    }


def _capture_with_pages(lane: dict, **overrides):
    kwargs = dict(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=lane["issuers"],
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=CAPTURE_CLOCK,
    )
    kwargs.update(overrides)
    return capture_fif_filing_packages(**kwargs)


def _outcome_by_accession(report: dict) -> dict:
    return {
        row["accession"]: row["outcome"]
        for issuer in report["issuers"]
        for row in issuer["accessions"]
    }


def test_c0c_p1_recent_row_binding_is_byte_unchanged(tmp_path) -> None:
    """(p1) In recent -> binding byte-unchanged: the witness bytes equal the
    canonical recomputation exactly (golden bytes)."""
    lane = _materialized_lane(tmp_path)
    capture_fif_filing_packages(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=lane["issuers"],
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=CAPTURE_CLOCK,
    )
    submissions = _synthetic_submissions(lane["identity"])
    recent = submissions["filings"]["recent"]
    for index, accession in enumerate(lane["identity"]["accessions"]):
        witness_path = package_dir_for(
            lane["archive_root"], lane["identity"]["cik"], accession
        ) / "sec_submissions_witness.json"
        expected = {
            "source_url": f"https://data.sec.gov/submissions/CIK{lane['identity']['cik']}.json",
            "source_path": f"filings.recent[accessionNumber={accession}]",
            "accessionNumber": accession,
            "form": recent["form"][index],
            "filingDate": recent["filingDate"][index],
            "reportDate": recent["reportDate"][index],
            "acceptanceDateTime": _normalized_utc(recent["acceptanceDateTime"][index]),
            "primaryDocument": recent["primaryDocument"][index],
        }
        golden = (json.dumps(expected, indent=2, sort_keys=True) + "\n").encode("utf-8")
        assert witness_path.read_bytes() == golden, accession


def test_c0c_p2_page_row_witness_binds_from_the_page(tmp_path) -> None:
    """(p2) Outside recent, inside ONE page -> page-bound and captured: the
    witness source_path names the page, source_url is the page URL, and the
    package lands with capture outcome captured."""
    lane = _page_witness_lane(tmp_path)
    report = _capture_with_pages(lane, submissions_collector=lane["submissions_collector"])
    rows = _outcome_by_accession(report)
    assert rows[lane["outside"]] == "captured", rows
    assert lane["submissions_collector"].page_fetches == [lane["page_name"]]
    witness = json.loads(
        (
            package_dir_for(lane["archive_root"], lane["identity"]["cik"], lane["outside"])
            / "sec_submissions_witness.json"
        ).read_text("utf-8")
    )
    assert witness["source_path"] == (
        f"filings.files[{lane['page_name']}][accessionNumber={lane['outside']}]"
    )
    assert witness["source_url"] == (
        f"https://data.sec.gov/submissions/{lane['page_name']}"
    )
    row = lane["page_row"]
    assert witness["form"] == row["form"]
    assert witness["filingDate"] == row["filingDate"]
    assert witness["primaryDocument"] == row["primaryDocument"]
    # latest.json never moved: the shard fetch is publish_latest=False.
    pointer = json.loads(
        (
            lane["raw_root"] / lane["identity"]["cik"] / "submissions" / "latest.json"
        ).read_text()
    )
    assert pointer["url"].endswith(f"CIK{lane['identity']['cik']}.json")


def test_c0c_p3_no_covering_page_is_typed(tmp_path) -> None:
    """(p3) In no page -> ``submissions_page_not_found``."""
    identity = _fixture_identity()
    lane = _page_witness_lane(
        tmp_path,
        files=[
            {
                "name": f"CIK{identity['cik']}-submissions-009.json",
                "filingFrom": "2001-01-01",
                "filingTo": "2001-12-31",
            }
        ],
    )
    report = _capture_with_pages(lane, submissions_collector=lane["submissions_collector"])
    rows = _outcome_by_accession(report)
    assert rows[lane["outside"]] == "member_capture_failed:submissions_page_not_found"
    assert lane["submissions_collector"].page_fetches == []


def test_c0c_p4_two_covering_pages_are_typed(tmp_path) -> None:
    """(p4) Two covering pages -> ``submissions_page_ambiguous``."""
    identity = _fixture_identity()
    lane = _page_witness_lane(
        tmp_path,
        files=[
            {
                "name": f"CIK{identity['cik']}-submissions-001.json",
                "filingFrom": "2001-01-01",
                "filingTo": "2030-12-31",
            },
            {
                "name": f"CIK{identity['cik']}-submissions-002.json",
                "filingFrom": "2000-01-01",
                "filingTo": "2029-12-31",
            },
        ],
    )
    report = _capture_with_pages(lane, submissions_collector=lane["submissions_collector"])
    rows = _outcome_by_accession(report)
    assert rows[lane["outside"]] == "member_capture_failed:submissions_page_ambiguous"


def test_c0c_p5_retained_page_reuse_makes_zero_requests(tmp_path) -> None:
    """(p5) Retained page reuse -> zero requests: after a first capture whose
    member fetch failed (package not written, page retained), the second
    capture re-mints the page witness with ZERO page fetches."""
    identity = _fixture_identity()
    stem = str(
        identity["manifests"][identity["accessions"][0]]["primary_document"]
    ).rsplit(".", 1)[0]
    lane = _page_witness_lane(tmp_path, fail_member_once=f"{stem}_cal.xml")
    first = _capture_with_pages(lane, submissions_collector=lane["submissions_collector"])
    rows = _outcome_by_accession(first)
    assert rows[lane["outside"]] == "member_capture_failed:member_fetch_failed"
    assert lane["submissions_collector"].page_fetches == [lane["page_name"]]
    second = _capture_with_pages(lane, submissions_collector=lane["submissions_collector"])
    rows = _outcome_by_accession(second)
    assert rows[lane["outside"]] == "captured", rows
    # ZERO additional page requests: the retained page was reused (E5-b).
    assert lane["submissions_collector"].page_fetches == [lane["page_name"]]


def test_c0c_p6_receipt_mismatch_is_typed_and_never_refetched(tmp_path) -> None:
    """(p6) A retained page whose object fails verification ->
    ``submissions_page_receipt_mismatch`` (run-level integrity), with NO
    refetch of the page."""
    identity = _fixture_identity()
    stem = str(
        identity["manifests"][identity["accessions"][0]]["primary_document"]
    ).rsplit(".", 1)[0]
    lane = _page_witness_lane(tmp_path, fail_member_once=f"{stem}_cal.xml")
    first = _capture_with_pages(lane, submissions_collector=lane["submissions_collector"])
    rows = _outcome_by_accession(first)
    assert rows[lane["outside"]] == "member_capture_failed:member_fetch_failed"
    assert lane["submissions_collector"].page_fetches == [lane["page_name"]]
    # Corrupt the retained page OBJECT (identified through ITS receipt, never
    # the latest pointer's object) in the incumbent namespace.
    cik = lane["identity"]["cik"]
    page_object = None
    for receipt_path in sorted((lane["raw_root"] / cik / "submissions").glob("*.receipt.json")):
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("url") == f"https://data.sec.gov/submissions/{lane['page_name']}":
            page_object = lane["raw_root"] / str(receipt["object_path"])
            break
    assert page_object is not None
    page_object.write_bytes(gzip.compress(b"corrupted page bytes"))
    second = _capture_with_pages(lane, submissions_collector=lane["submissions_collector"])
    rows = _outcome_by_accession(second)
    assert rows[lane["outside"]] == (
        "member_capture_failed:submissions_page_receipt_mismatch"
    )
    # Never a silent refetch-over: the fake saw exactly the one lawful fetch.
    assert lane["submissions_collector"].page_fetches == [lane["page_name"]]
    assert rows[lane["identity"]["accessions"][0]] == "retained_reused"


def test_c0c_p7_d1_admits_a_page_bound_witness(tmp_path) -> None:
    """(p7) D1 admits the page-bound witness WITHOUT any D1 edit."""
    from engine.fundamental_forensics.admitted_filing_package import (
        admit_retained_filing_package,
    )

    lane = _page_witness_lane(tmp_path)
    _capture_with_pages(lane, submissions_collector=lane["submissions_collector"])
    retained = read_retained_fif_packages(
        lane["archive_root"],
        cik=lane["identity"]["cik"],
        accessions=[lane["outside"]],
    )
    assert len(retained) == 1
    package = retained[0]
    admitted = admit_retained_filing_package(
        index_bytes=package.index_bytes,
        manifest=dict(package.manifest),
        members=dict(package.members),
        witness_bytes=package.witness_bytes,
        capture_recorded_at=package.capture_recorded_at,
    )
    witness = json.loads(package.witness_bytes.decode("utf-8"))
    assert witness["source_path"].startswith("filings.files[")
    assert admitted.manifest["accession"] == lane["outside"]


def _retain_stale_submissions_page(
    lane: dict, page_row: dict, *, retrieved_at: str
) -> dict:
    """Seed a VERIFIED retained page for the lane's page name (incumbent
    ``persist_response``, ``publish_latest=False``) whose bytes carry exactly
    the given row. Returns the object/receipt paths plus their BEFORE bytes so
    a test can prove the stale artifacts are never rewritten."""
    cik = lane["identity"]["cik"]
    content = json.dumps({key: [value] for key, value in page_row.items()}).encode(
        "utf-8"
    )
    receipt = persist_response(
        lane["raw_root"],
        cik=cik,
        endpoint="submissions",
        url=historical_submissions_url(cik, lane["page_name"]),
        content=content,
        retrieved_at=retrieved_at,
        publish_latest=False,
    )
    object_path = lane["raw_root"] / str(receipt.object_path)
    receipt_path = object_path.with_suffix(".receipt.json")
    return {
        "object_path": object_path,
        "receipt_path": receipt_path,
        "object_before": object_path.read_bytes(),
        "receipt_before": receipt_path.read_bytes(),
        "content": content,
    }


def _mint_page_witness(lane: dict, collector, accession: str):
    """Drive ``mint_acceptance_witness`` over one page-row accession."""
    identity = lane["identity"]
    return CAP.mint_acceptance_witness(
        raw_root=lane["raw_root"],
        cik=identity["cik"],
        accession=accession,
        primary_document=str(
            identity["manifests"][identity["accessions"][0]]["primary_document"]
        ),
        filing_date=lane["filing_date"],
        submissions_collector=collector,
        retrieved_at=CAPTURE_CLOCK,
        budget_remaining=CAP.DEFAULT_RUN_BUDGET_BYTES,
    )


def test_c0c_p9_stale_retained_page_is_refetched_and_new_bytes_used(
    tmp_path,
) -> None:
    """(p9) A VERIFIED retained page for the selected page name whose bytes
    LACK the accession and whose derived range disagrees with the current
    files[] entry is STALE (SEC re-paged): the page is re-fetched through the
    incumbent path exactly once, the witness binds from the NEW row, and the
    stale receipt + object bytes are never rewritten."""
    from datetime import date, timedelta

    lane = _page_witness_lane(tmp_path)
    identity = lane["identity"]
    filing_date = lane["filing_date"]
    stale_date = (date.fromisoformat(filing_date) - timedelta(days=1)).isoformat()
    stale_row = _page_row_for(identity, identity["accessions"][0][:-1] + "3", stale_date)
    stale = _retain_stale_submissions_page(
        lane, stale_row, retrieved_at="2026-10-12T02:31:00Z"
    )
    # The fake collector serves the CURRENT page bytes: the contract row.
    new_row = _page_row_for(identity, lane["outside"], filing_date)
    new_page = {key: [value] for key, value in new_row.items()}
    new_bytes = json.dumps(new_page).encode("utf-8")
    collector = _FakeSubmissionsCollector(lane["raw_root"], {lane["page_name"]: new_page}, lane["pacer"])
    witness_bytes, bound, page_info = _mint_page_witness(lane, collector, lane["outside"])
    # Exactly ONE fetch, for that page name; the FRESH bytes were used.
    assert collector.page_fetches == [lane["page_name"]]
    assert page_info["reused"] is False
    assert page_info["charged_bytes"] == len(new_bytes)
    # The witness binds from the NEW row (fields equal the new row).
    witness = json.loads(witness_bytes.decode("utf-8"))
    assert witness["form"] == new_row["form"]
    assert witness["filingDate"] == new_row["filingDate"]
    assert witness["reportDate"] == new_row["reportDate"]
    assert witness["primaryDocument"] == new_row["primaryDocument"]
    assert bound["filingDate"] == new_row["filingDate"]
    # The stale receipt and its object are byte-identical before/after: new
    # bytes mean a NEW content-addressed object + receipt, never a rewrite.
    assert stale["object_path"].read_bytes() == stale["object_before"]
    assert stale["receipt_path"].read_bytes() == stale["receipt_before"]


def test_c0c_p10_matching_retained_page_reused_with_zero_requests(
    tmp_path,
) -> None:
    """(p10) (a) A retained page CONTAINING the accession is reused with zero
    fetch calls, reused=True, charged 0; (b) a retained page LACKING the
    accession but whose derived range EQUALS the current files[] entry is
    reused (zero fetch calls) and the refusal is the genuine typed
    ``accession_not_in_submissions``."""
    # (a) containment-qualifying retained page -> reuse, zero requests.
    lane = _page_witness_lane(tmp_path)
    matching_row = _page_row_for(lane["identity"], lane["outside"], lane["filing_date"])
    _retain_stale_submissions_page(
        lane, matching_row, retrieved_at="2026-10-12T02:31:00Z"
    )
    decoy = _page_row_for(
        lane["identity"],
        lane["identity"]["accessions"][0][:-1] + "6",
        lane["filing_date"],
    )
    collector_a = _FakeSubmissionsCollector(
        lane["raw_root"],
        {lane["page_name"]: {key: [value] for key, value in decoy.items()}},
        lane["pacer"],
    )
    witness_bytes, _bound, page_info = _mint_page_witness(
        lane, collector_a, lane["outside"]
    )
    assert collector_a.page_fetches == []
    assert page_info["reused"] is True
    assert page_info["charged_bytes"] == 0
    witness = json.loads(witness_bytes.decode("utf-8"))
    assert witness["form"] == matching_row["form"]
    assert witness["filingDate"] == matching_row["filingDate"]
    assert witness["primaryDocument"] == matching_row["primaryDocument"]

    # (b) range-equal retained page that lacks the accession -> reuse, then
    # the genuine typed refusal — never a refetch.
    lane_b = _page_witness_lane(tmp_path / "b")
    sibling_row = _page_row_for(
        lane_b["identity"],
        lane_b["identity"]["accessions"][0][:-1] + "4",
        lane_b["filing_date"],
    )
    _retain_stale_submissions_page(
        lane_b, sibling_row, retrieved_at="2026-10-12T02:31:00Z"
    )
    collector_b = _FakeSubmissionsCollector(
        lane_b["raw_root"],
        {
            lane_b["page_name"]: {
                key: [value]
                for key, value in _page_row_for(
                    lane_b["identity"], lane_b["outside"], lane_b["filing_date"]
                ).items()
            }
        },
        lane_b["pacer"],
    )
    with pytest.raises(FifMemberCaptureError) as caught:
        _mint_page_witness(lane_b, collector_b, lane_b["outside"])
    assert caught.value.code == "accession_not_in_submissions"
    assert collector_b.page_fetches == []


def test_c0c_p6b_receipt_mismatch_refuses_even_beside_a_stale_sibling(
    tmp_path,
) -> None:
    """(p6b) Two receipts share the page URL: one verifies but is stale, one
    FAILS verification. The mismatch refuses with ZERO fetches — never a
    refetch over the corrupt receipt, and never a silent fallback to the
    (range-qualifying) stale sibling."""
    lane = _page_witness_lane(tmp_path)
    identity = lane["identity"]
    stale_row = _page_row_for(
        identity, identity["accessions"][0][:-1] + "3", lane["filing_date"]
    )
    _retain_stale_submissions_page(lane, stale_row, retrieved_at="2026-10-12T02:31:00Z")
    corrupt = _retain_stale_submissions_page(
        lane,
        _page_row_for(identity, identity["accessions"][0][:-1] + "5", lane["filing_date"]),
        retrieved_at="2026-10-13T01:00:00Z",
    )
    corrupt["object_path"].write_bytes(gzip.compress(b"corrupted page bytes"))
    collector = _FakeSubmissionsCollector(
        lane["raw_root"],
        {
            lane["page_name"]: {
                key: [value]
                for key, value in _page_row_for(
                    identity, lane["outside"], lane["filing_date"]
                ).items()
            }
        },
        lane["pacer"],
    )
    with pytest.raises(FifMemberCaptureError) as caught:
        _mint_page_witness(lane, collector, lane["outside"])
    assert caught.value.code == "submissions_page_receipt_mismatch"
    assert collector.page_fetches == []


# ---------------------------------------------------------------------------
# C0-c ERRATA-4: form-keyed 8-K member set (t1..t7)
# ---------------------------------------------------------------------------


def _eight_k_index_bytes(base_index: bytes, drop_suffixes: tuple[str, ...]) -> bytes:
    """A synthetic 8-K archive index: the fixture index minus dropped members."""
    payload = json.loads(base_index.decode("utf-8"))
    items = [
        item
        for item in payload["directory"]["item"]
        if not any(str(item.get("name") or "").endswith(suffix) for suffix in drop_suffixes)
    ]
    payload["directory"]["item"] = items
    return (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")


def _eight_k_lane(tmp_path: Path, *, drop_suffixes=("_cal.xml", "_def.xml")):
    """A capture lane with ONE 8-K contract accession whose index omits the
    optional members (the dei-only earnings-8-K shape)."""
    identity = _fixture_identity()
    eight_k = identity["accessions"][0][:-1] + "5"
    ten_q_manifest = identity["manifests"][identity["accessions"][0]]
    raw_root = tmp_path / "raw"
    archive_root = tmp_path / "archive"
    raw_root.mkdir(parents=True)
    archive_root.mkdir(parents=True)
    submissions = _synthetic_submissions(identity)
    recent = submissions["filings"]["recent"]
    recent["accessionNumber"] = [eight_k, *recent["accessionNumber"]]
    for field in ("form", "filingDate", "reportDate", "acceptanceDateTime", "primaryDocument"):
        recent[field] = ["8-K" if field == "form" else recent[field][0], *recent[field]]
    recent["isXBRL"] = [True, *recent["isXBRL"]]
    recent["isInlineXBRL"] = [True, *recent["isInlineXBRL"]]
    _write_submissions(raw_root, identity)
    # Rewrite the pointer over the 8-K-carrying payload.
    payload = json.dumps(submissions).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    object_path = f"{identity['cik']}/submissions/{digest[:32]}.json.gz"
    target = raw_root / object_path
    target.write_bytes(gzip.compress(payload))
    pointer = raw_root / identity["cik"] / "submissions" / "latest.json"
    pointer.write_text(
        json.dumps(
            {
                "schema": "fundamental_forensics_retrieval.v1",
                "cik": identity["cik"],
                "endpoint": "submissions",
                "url": f"https://data.sec.gov/submissions/CIK{identity['cik']}.json",
                "retrieved_at": CAPTURE_CLOCK,
                "sha256": digest,
                "bytes": len(payload),
                "object_path": object_path,
                "http_etag": None,
                "http_last_modified": None,
            }
        ),
        encoding="utf-8",
    )
    _retain_primaries(archive_root, identity, extra=eight_k)
    served = _fixture_member_bytes()
    base = dict(served[identity["accessions"][0].replace("-", "")])
    base["index.json"] = _eight_k_index_bytes(base["index.json"], drop_suffixes)
    served[eight_k.replace("-", "")] = base
    pacer = _no_sleep_pacer()
    collector = _FakeCollector(archive_root, served, pacer)
    issuers = [
        {
            "cik": identity["cik"],
            "ticker": identity["ticker"],
            "legal_name": "Synthetic Lane Issuer",
            "security_master_binding": {
                "issuer_id": identity["entity_id"],
                "issuer_cik": identity["cik"],
                "security_id": identity["security_id"],
                "listing_key": identity["listing_key"],
                "mic": "XNAS",
                "effective_at": "2023-05-09T00:00:00",
            },
            "accessions": [
                {
                    "accession": eight_k,
                    "form": "8-K",
                    "filing_date": _filing_date_for(identity["accessions"], identity["accessions"][0]),
                }
            ],
        }
    ]
    return {
        "identity": identity,
        "raw_root": raw_root,
        "archive_root": archive_root,
        "collector": collector,
        "pacer": pacer,
        "issuers": issuers,
        "eight_k": eight_k,
        "served": served,
        "primary_name": str(ten_q_manifest["primary_document"]),
    }


def _capture_eight_k(lane: dict, **overrides):
    kwargs = dict(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=lane["issuers"],
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=CAPTURE_CLOCK,
    )
    kwargs.update(overrides)
    return capture_fif_filing_packages(**kwargs)


def test_c0c_t1_eight_k_with_absent_optionals_captures(tmp_path) -> None:
    """(t1) 8-K, _cal and _def absent from the listing -> captured, with
    ``absent_members`` holding exactly those two entries and ZERO requests
    issued for them (fake-collector call log)."""
    lane = _eight_k_lane(tmp_path, drop_suffixes=("_cal.xml", "_def.xml"))
    report = _capture_eight_k(lane)
    row = report["issuers"][0]["accessions"][0]
    assert row["outcome"] == "captured", row
    fetched = lane["collector"].fetched
    stem = lane["primary_name"].rsplit(".", 1)[0]
    assert f"{stem}_cal.xml" not in fetched
    assert f"{stem}_def.xml" not in fetched
    manifest = json.loads(
        (
            package_dir_for(lane["archive_root"], lane["identity"]["cik"], lane["eight_k"])
            / "package_manifest.json"
        ).read_text("utf-8")
    )
    assert manifest["absent_members"] == [
        {"role": "calculation", "name": f"{stem}_cal.xml", "reason": "absent_in_archive_index"},
        {"role": "definition", "name": f"{stem}_def.xml", "reason": "absent_in_archive_index"},
    ]
    # R6: the 8-K manifest carries NO statement_roles key at all.
    assert "statement_roles" not in manifest


def test_c0c_t2_listed_optional_member_fetch_failure_is_typed(tmp_path) -> None:
    """(t2) 8-K, _cal LISTED but its fetch fails -> ``member_fetch_failed``
    and no package dir is written (a failed fetch is NEVER downgraded to
    absence)."""

    class _FailCal(_FakeCollector):
        def fetch_document(self, document, *, retrieved_at=None, expected_sha256=None, max_document_bytes=None):
            name = document["archive_url"].rsplit("/", 1)[-1]
            if name.endswith("_cal.xml"):
                self.fetched.append(name)
                raise RuntimeError("forced _cal failure")
            return super().fetch_document(
                document,
                retrieved_at=retrieved_at,
                expected_sha256=expected_sha256,
                max_document_bytes=max_document_bytes,
            )

    lane = _eight_k_lane(tmp_path, drop_suffixes=("_def.xml",))
    lane["collector"] = _FailCal(lane["archive_root"], lane["served"], lane["pacer"])
    report = _capture_eight_k(lane)
    row = report["issuers"][0]["accessions"][0]
    assert row["outcome"] == "member_capture_failed:member_fetch_failed", row
    assert not package_dir_for(
        lane["archive_root"], lane["identity"]["cik"], lane["eight_k"]
    ).exists()


def test_c0c_t3_required_member_not_listed_is_typed(tmp_path) -> None:
    """(t3) 8-K, _lab not listed -> ``member_missing_from_index`` and no
    member fetch is issued."""
    lane = _eight_k_lane(tmp_path, drop_suffixes=("_lab.xml",))
    report = _capture_eight_k(lane)
    row = report["issuers"][0]["accessions"][0]
    assert row["outcome"] == "member_capture_failed:member_missing_from_index", row
    # Only the index itself was fetched — no member request at all.
    assert lane["collector"].fetched == ["index.json"]


def test_c0c_t4_ten_k_missing_member_still_typed(tmp_path) -> None:
    """(t4) 10-K, _cal not listed -> ``member_missing_from_index`` (unchanged
    behaviour: all five members stay required for 10-K/10-Q)."""
    lane = _materialized_lane(tmp_path)
    served = lane["served"]
    identity = lane["identity"]
    stem = str(identity["manifests"][identity["accessions"][0]]["primary_document"]).rsplit(".", 1)[0]
    for accession in identity["accessions"]:
        base = dict(served[accession.replace("-", "")])
        base["index.json"] = _eight_k_index_bytes(base["index.json"], ("_cal.xml",))
        served[accession.replace("-", "")] = base
    report = capture_fif_filing_packages(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=lane["issuers"],
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=CAPTURE_CLOCK,
    )
    rows = _outcome_by_accession(report)
    assert rows[identity["accessions"][0]] == "member_capture_failed:member_missing_from_index"
    assert f"{stem}_cal.xml" not in lane["collector"].fetched


def test_c0c_t5_nightly_rerun_after_captured_eight_k_reuses(tmp_path) -> None:
    """(t5) A nightly rerun after a captured 8-K -> ``retained_reused``, zero
    fetches, byte-identical package files."""
    lane = _eight_k_lane(tmp_path)
    first = _capture_eight_k(lane)
    assert first["issuers"][0]["accessions"][0]["outcome"] == "captured"
    package_dir = package_dir_for(
        lane["archive_root"], lane["identity"]["cik"], lane["eight_k"]
    )
    before = {
        path.name: path.read_bytes() for path in sorted(package_dir.rglob("*")) if path.is_file()
    }
    fetches_before = list(lane["collector"].fetched)
    second = _capture_eight_k(lane)
    row = second["issuers"][0]["accessions"][0]
    assert row["outcome"] == "retained_reused", row
    assert row["reused"] is True
    assert lane["collector"].fetched == fetches_before
    after = {
        path.name: path.read_bytes() for path in sorted(package_dir.rglob("*")) if path.is_file()
    }
    assert after == before


def test_c0c_t7_contract_form_disagreeing_with_row_is_typed(tmp_path) -> None:
    """(t7) A contract form disagreeing with the witness-bound row ->
    ``submissions_row_mismatch`` (R8, before the index fetch)."""
    lane = _materialized_lane(tmp_path)
    lane["issuers"][0]["accessions"][0]["form"] = "8-K"  # the row says 10-K
    report = capture_fif_filing_packages(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=lane["issuers"],
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=CAPTURE_CLOCK,
    )
    rows = _outcome_by_accession(report)
    assert rows[lane["identity"]["accessions"][0]] == (
        "member_capture_failed:submissions_row_mismatch"
    )
    # Refused BEFORE the index fetch: exactly ONE index fetch happened in the
    # whole run (the second, agreeing accession's) — none for the refused row.
    assert lane["collector"].fetched.count("index.json") == 1


def test_c0c_form_not_in_member_policy_is_typed_before_fetches(tmp_path) -> None:
    """(R1's typed refusal — the a8/t-series sibling on the capture side) an
    unknown contract form refuses before ANY fetch."""
    lane = _materialized_lane(tmp_path)
    lane["issuers"][0]["accessions"][0]["form"] = "8-K/A"
    report = capture_fif_filing_packages(
        raw_root=lane["raw_root"],
        archive_root=lane["archive_root"],
        issuers=lane["issuers"],
        collector=lane["collector"],
        pacer=lane["pacer"],
        recorded_at=CAPTURE_CLOCK,
    )
    rows = _outcome_by_accession(report)
    assert rows[lane["identity"]["accessions"][0]] == (
        "member_capture_failed:form_not_in_member_policy"
    )
    # Refused before ANY fetch for it: exactly one index fetch in the whole
    # run (the second, lawful accession's).
    assert lane["collector"].fetched.count("index.json") == 1
