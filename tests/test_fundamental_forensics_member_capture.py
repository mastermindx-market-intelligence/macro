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
    return [
        {
            "cik": identity["cik"],
            "ticker": identity["ticker"],
            "legal_name": "Synthetic Lane Issuer",
            "security_master_binding": binding if with_binding else None,
            "accessions": [{"accession": a} for a in identity["accessions"]],
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
