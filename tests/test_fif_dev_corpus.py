"""Hermetic tests for the FIF development-corpus instrument.

No network: the paced client's ``get`` seam is monkeypatched with canned
public-EDGAR payloads (ticker map + submissions JSON), and the held-out
exclusion set is a synthetic five-issuer-shaped contract written to a
temporary path. The contract the instrument writes must satisfy the EXISTING
capture tool's own gates (``load_contract`` + ``contract_declared_reason`` +
``build_package_manifest``), because the dev capture runs through that tool
unmodified.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

from scripts import fif_dev_corpus as dev_corpus
from scripts.capture_fif_issuer_packages import (
    build_package_manifest,
    build_witness_bytes,
    contract_declared_reason,
    load_contract,
)

ROOT = Path(__file__).resolve().parents[1]
DEV_CIK = 1111111
DEV_CIK10 = "0001111111"
HELD_OUT_CIK10 = "0000000009"
CAPTURED_AT = "2026-11-01T12:00:00Z"

HELD_OUT_SHAPE = {
    "schema": "fundamental_forensics.coverage_contract/v1",
    "contract_id": "five_issuer_v1",
    "issuers": [
        {
            "ticker": "HO1",
            "cik": "0000000009",
            "legal_name": "HELD OUT ONE",
            "accessions": [],
        },
        {
            "ticker": "HO2",
            "cik": "0000000008",
            "legal_name": "HELD OUT TWO",
            "accessions": [],
        },
    ],
    "source_rights": {
        "access_policy": "sec_fair_access_declared_user_agent",
        "credentials_required": [],
        "licences_accepted": [],
        "provider": "sec_edgar_public_filings",
        "purchases": [],
    },
    "retained_package_law": {
        "declared_reason": "not required for XBRL statement reconstruction",
        "member_states": ["stored"],
    },
    "field_denominator": {
        "metric_catalog": "config/fundamental_forensics/metrics/v1/metric_catalog.yaml",
        "metric_ids": ["revenue"],
    },
}

TICKER_MAP = {
    "0": {"cik_str": DEV_CIK, "ticker": "DEV1", "title": "Dev One Bancorp"},
    "1": {"cik_str": 9, "ticker": "HO1", "title": "Held Out One Inc."},
    "2": {"cik_str": 9, "ticker": "DEV9", "title": "Dev Nine In Disguise"},
}

SUBMISSIONS = {
    "cik": str(DEV_CIK),
    "name": "DEV ONE BANCORP",
    "sic": "6021",
    "sicDescription": "National Commercial Banks",
    "fiscalYearEnd": "1231",
    "tickers": ["DEV1"],
    "filings": {
        "recent": {
            "accessionNumber": [
                "0001111111-26-000001",
                "0001111111-26-000002",
                "0001111111-26-000003",
            ],
            "form": ["10-K", "10-Q", "8-K"],
            "filingDate": ["2026-02-15", "2026-05-01", "2026-05-02"],
            "reportDate": ["2025-12-31", "2026-03-31", "2026-05-02"],
        }
    },
}


def _write_held_out(tmp_path: Path) -> Path:
    path = tmp_path / "held_out.json"
    path.write_text(json.dumps(HELD_OUT_SHAPE), encoding="utf-8")
    return path


class _CannedClient:
    """Stand-in for DevCorpusClient.get: canned payloads by URL."""

    def __init__(self, ticker_map=None, submissions=None) -> None:
        self._ticker_map = json.dumps(ticker_map or TICKER_MAP).encode("utf-8")
        self._submissions = json.dumps(submissions or SUBMISSIONS).encode("utf-8")

    def __call__(self, url: str) -> bytes:
        if url == dev_corpus.TICKER_MAP_URL:
            return self._ticker_map
        if url == f"{dev_corpus.SUBMISSIONS_ORIGIN}/CIK{DEV_CIK10}.json":
            return self._submissions
        raise AssertionError(f"unexpected fetch: {url}")


def _patch_client(monkeypatch: pytest.MonkeyPatch, client=None) -> None:
    canned = client or _CannedClient()
    monkeypatch.setattr(dev_corpus.DevCorpusClient, "get", canned)
    monkeypatch.setattr(dev_corpus, "_resolve_sec_user_agent", lambda: "dev-corpus-test")


def _contract_argv(tmp_path: Path, held_out: Path, *tickers: str, min_interval=None):
    argv = [
        "contract",
        "--tickers",
        *tickers,
        "--captured-at",
        CAPTURED_AT,
        "--out",
        str(tmp_path / "dev_contract.json"),
        "--submissions-dir",
        str(tmp_path / "submissions"),
        "--held-out-contract",
        str(held_out),
    ]
    if min_interval is not None:
        argv += ["--min-interval", str(min_interval)]
    return argv


def test_rate_limit_floor_is_enforced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    _patch_client(monkeypatch)
    held_out = _write_held_out(tmp_path)
    code = dev_corpus.main(_contract_argv(tmp_path, held_out, "DEV1", min_interval=0.5))
    assert code == 2
    assert "dev_corpus_refusal: min_interval_below_floor" in capsys.readouterr().out


def test_held_out_ticker_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    _patch_client(monkeypatch)
    held_out = _write_held_out(tmp_path)
    code = dev_corpus.main(_contract_argv(tmp_path, held_out, "HO1"))
    assert code == 2
    assert "dev_corpus_refusal: held_out_ticker:HO1" in capsys.readouterr().out


def test_held_out_cik_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    # DEV9 is not a held-out ticker string but resolves through the ticker
    # map to CIK 0000000009, which the held-out contract carries.
    _patch_client(monkeypatch)
    held_out = _write_held_out(tmp_path)
    code = dev_corpus.main(_contract_argv(tmp_path, held_out, "DEV9"))
    assert code == 2
    assert f"dev_corpus_refusal: held_out_cik:{HELD_OUT_CIK10}" in (
        capsys.readouterr().out
    )


def test_unknown_ticker_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    _patch_client(monkeypatch)
    held_out = _write_held_out(tmp_path)
    code = dev_corpus.main(_contract_argv(tmp_path, held_out, "NOPE"))
    assert code == 2
    assert "dev_corpus_refusal: ticker_unknown:NOPE" in capsys.readouterr().out


def test_contract_shape_satisfies_the_capture_tool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    _patch_client(monkeypatch)
    held_out = _write_held_out(tmp_path)
    code = dev_corpus.main(_contract_argv(tmp_path, held_out, "DEV1"))
    assert code == 0
    contract_path = tmp_path / "dev_contract.json"
    capsys.readouterr()

    # The EXISTING tool's gates.
    contract = load_contract(contract_path)
    assert contract_declared_reason(contract) == (
        "not required for XBRL statement reconstruction"
    )
    assert contract["contract_id"] == dev_corpus.CONTRACT_ID
    assert contract["attested"] is False
    assert contract["capture_basis"] == "dev_corpus"
    # Verbatim blocks, byte-equal to the shape reference.
    for block in dev_corpus.VERBATIM_CONTRACT_BLOCKS:
        assert contract[block] == HELD_OUT_SHAPE[block]
    # One issuer row, periodic forms only (the 8-K row never enters).
    assert len(contract["issuers"]) == 1
    row = contract["issuers"][0]
    assert row["ticker"] == "DEV1"
    assert row["cik"] == DEV_CIK10
    assert row["sic"] == "6021"
    assert row["issuer_class"] == "bank"
    assert row["identity_binding_state"] == "sec_submissions_ticker_map"
    assert row["security_master_binding"] == {
        "issuer_id": "DEV:DEV1",
        "security_id": "DEV:DEV1:EQ",
        "listing_key": "DEV:DEV1",
        "issuer_cik": DEV_CIK10,
        "security_state": "dev_corpus_unbound",
        "effective_at": CAPTURED_AT,
    }
    assert [item["form"] for item in row["accessions"]] == ["10-K", "10-Q"]
    assert all(item["retention_state"] == "candidate" for item in row["accessions"])
    assert all(item["census_ref"] == "sec_submissions" for item in row["accessions"])
    staged = json.loads(
        (tmp_path / "submissions" / f"CIK{DEV_CIK10}.json").read_text("utf-8")
    )
    assert row["sic_source"]["sha256"] == hashlib.sha256(
        json.dumps(SUBMISSIONS).encode("utf-8")
    ).hexdigest()
    assert row["sic_source"]["sic_description"] == "National Commercial Banks"

    # The capture tool's manifest builder accepts the synthetic row.
    accession = "0001111111-26-000001"
    primary = "dev1-20251231.htm"
    index_bytes = json.dumps(
        {"directory": {"item": [{"name": primary, "size": 12, "type": "text/html"}]}}
    ).encode("utf-8")
    witness = {
        "source_url": f"https://data.sec.gov/submissions/CIK{DEV_CIK10}.json",
        "source_path": "filings.recent[0]",
        "accessionNumber": accession,
        "form": "10-K",
        "filingDate": "2026-02-15",
        "reportDate": "2025-12-31",
        "acceptanceDateTime": "2026-02-15T16:00:00Z",
        "primaryDocument": primary,
    }
    witness_bytes = build_witness_bytes(witness)
    content = b"<html>primary</html>"
    retained = {
        primary: {
            "name": primary,
            "state": "stored",
            "role": "primary",
            "content_sha256": hashlib.sha256(content).hexdigest(),
            "byte_length": len(content),
            "path": f"members/{primary}",
            "archive_url": (
                f"https://www.sec.gov/Archives/edgar/data/{DEV_CIK}/"
                f"{accession.replace('-', '')}/{primary}"
            ),
            "http_last_modified": None,
        }
    }
    package_manifest = build_package_manifest(
        issuer_row=row,
        cik10=DEV_CIK10,
        accession=accession,
        submissions_fields={
            "form": "10-K",
            "primaryDocument": primary,
            "reportDate": "2025-12-31",
            "filingDate": "2026-02-15",
            "acceptanceDateTime": "2026-02-15T16:00:00Z",
        },
        index_bytes=index_bytes,
        index_last_modified=None,
        inventory_items=[{"name": primary, "size": 12, "type": "text/html"}],
        retained=retained,
        declared_reason=contract_declared_reason(contract),
        statement_roles=None,
        fixture_recorded_at=CAPTURED_AT,
        witness_bytes=witness_bytes,
        witness_source_url=witness["source_url"],
    )
    assert package_manifest["schema"] == (
        "fundamental_forensics.golden_filing_package/v1"
    )
    assert package_manifest["entity_id"] == "DEV:DEV1"
    assert package_manifest["security_id"] == "DEV:DEV1:EQ"
    assert package_manifest["listing_key"] == "DEV:DEV1"
    assert package_manifest["legal_name"] == "DEV ONE BANCORP"


def test_manifest_is_digest_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    capture_out = tmp_path / "out"
    stage_root = tmp_path / "stage"
    accession = "0001111111-26-000001"
    member_name = "dev1-20251231.htm"
    member_sha = hashlib.sha256(b"primary bytes").hexdigest()
    package_manifest = {
        "filing_date": "2026-02-15",
        "fixture_recorded_at": CAPTURED_AT,
        "members": [
            {"name": member_name, "state": "stored", "content_sha256": member_sha},
            {"name": "unrequested.htm", "state": "not_requested"},
        ],
    }
    issuer_dir = capture_out / DEV_CIK10
    (issuer_dir / accession).mkdir(parents=True)
    (issuer_dir / accession / "package_manifest.json").write_text(
        json.dumps(package_manifest), encoding="utf-8"
    )
    (issuer_dir / "capture_index.json").write_text(
        json.dumps(
            [
                {
                    "accession": accession,
                    "form": "10-K",
                    "period_of_report": "2025-12-31",
                    "admission": "ADMITTED",
                },
                {
                    "accession": "0001111111-26-000002",
                    "form": "10-Q",
                    "period_of_report": "2026-03-31",
                    "admission": "statement_roles_missing:cash_flow",
                },
            ]
        ),
        encoding="utf-8",
    )
    stage_submissions = stage_root / "submissions"
    stage_submissions.mkdir(parents=True)
    (stage_submissions / f"CIK{DEV_CIK10}.json").write_text(
        json.dumps({"tickers": ["DEV1"], "sic": "6021"}), encoding="utf-8"
    )
    stage_accession = stage_root / DEV_CIK10 / accession
    stage_accession.mkdir(parents=True)
    (stage_accession / "index.json").write_bytes(b"{}")
    (stage_accession / "sec_submissions_witness.json").write_bytes(b"{}")

    held_out = _write_held_out(tmp_path)
    code = dev_corpus.main(
        [
            "manifest",
            "--stage-root",
            str(stage_root),
            "--capture-out",
            str(capture_out),
            "--out",
            str(tmp_path / "banks_v1.manifest.json"),
            "--held-out-contract",
            str(held_out),
        ]
    )
    assert code == 0
    capsys.readouterr()
    manifest = json.loads((tmp_path / "banks_v1.manifest.json").read_text("utf-8"))
    assert manifest["schema"] == dev_corpus.MANIFEST_SCHEMA
    assert manifest["corpus_id"] == "banks_v1"
    assert manifest["held_out_disjoint"] is True
    assert manifest["captured_at"] == CAPTURED_AT
    assert len(manifest["issuers"]) == 1
    issuer = manifest["issuers"][0]
    assert issuer["ticker"] == "DEV1"
    assert issuer["cik10"] == DEV_CIK10
    assert issuer["sic"] == "6021"
    assert [row["admission"] for row in issuer["accessions"]] == [
        "admitted",
        "statement_roles_missing:cash_flow",
    ]
    digest_re = re.compile(r"^[0-9a-f]{64}$")
    for row in issuer["accessions"]:
        for name, value in row["members"].items():
            assert digest_re.fullmatch(str(value)), (name, value)
        if "package_manifest_sha256" in row:
            assert digest_re.fullmatch(row["package_manifest_sha256"])
    admitted = issuer["accessions"][0]
    assert admitted["members"][member_name] == member_sha
    assert digest_re.fullmatch(admitted["members"]["index.json"])
    assert digest_re.fullmatch(admitted["members"]["sec_submissions_witness.json"])
    # No document bytes, text excerpts or XBRL values ride along.
    text = json.dumps(manifest)
    assert "primary bytes" not in text
    assert "unrequested.htm" not in text


def test_probe_on_empty_stage_reports_zero_accessions(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    stage_root = tmp_path / "stage"
    stage_root.mkdir()
    manifest = {
        "schema": dev_corpus.MANIFEST_SCHEMA,
        "corpus_id": "banks_v1",
        "capture_out_root": str(tmp_path / "out"),
        "issuers": [
            {"ticker": "DEV1", "cik10": DEV_CIK10, "sic": "6021", "accessions": []}
        ],
    }
    manifest_path = tmp_path / "empty.manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    code = dev_corpus.main(
        [
            "probe",
            "--stage-root",
            str(stage_root),
            "--manifest",
            str(manifest_path),
            "--pack",
            "PK11",
        ]
    )
    assert code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["accessions_probed"] == 0
    assert report["per_field"] == {}
    assert report["per_accession"] == []
