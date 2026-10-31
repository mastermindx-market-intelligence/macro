"""Pin the FIF D0 five-issuer source and coverage contract.

Contract only: no fetch, no retention, no attestation. Stdlib + pytest + pyyaml.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import date
from pathlib import Path

import pytest
import yaml

from engine.fundamental_forensics.detectors import issuer_class_for_sic
from engine.fundamental_forensics.issuer_sic import resolve_issuer_sic
from engine.fundamental_forensics.ixbrl_raw_ledger import GOLDEN_AAPL_QUERY_ACCESSIONS

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "config" / "fundamental_forensics" / "coverage" / "five_issuer_v1.json"
CATALOG_PATH = ROOT / "config" / "fundamental_forensics" / "metrics" / "v1" / "metric_catalog.yaml"
DOC_PATH = (
    ROOT
    / "research"
    / "financial_intelligence_fabric"
    / "FIF_D0_SOURCE_COVERAGE_CONTRACT.md"
)
MANIFEST_BY_ACCESSION = {
    "0000320193-25-000079": ROOT
    / "tests"
    / "fixtures"
    / "fundamental_forensics"
    / "aapl_10k_2025"
    / "package_manifest.json",
    "0000320193-26-000020": ROOT
    / "tests"
    / "fixtures"
    / "fundamental_forensics"
    / "aapl_10q_2026q3"
    / "package_manifest.json",
}

ACCESSION_RE = re.compile(r"^\d{10}-\d{2}-\d{6}$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ALLOWED_FORMS = frozenset({"10-K", "10-K/A", "10-Q", "10-Q/A", "8-K"})
SECRET_RE = re.compile(r"(secret|token|password|api[_-]?key|access[_-]?key)", re.I)
EVIDENCE_RE = re.compile(r"^(.+):(\d+(?:-\d+)?)$")
TICKER_ORDER = ("AAPL", "SNOW", "CAT", "BAC", "GOOGL")
EXPECTED_CIKS = {
    "AAPL": "0000320193",
    "SNOW": "0001640147",
    "CAT": "0000018230",
    "BAC": "0000070858",
    "GOOGL": "0001652044",
}
SUBMISSIONS_DIR = (
    ROOT / "tests" / "fixtures" / "fundamental_forensics" / "five_issuer_submissions"
)
CAPTURE_MANIFEST_PATH = SUBMISSIONS_DIR / "capture_manifest.json"
SECURITY_MASTER_PARQUET = ROOT / "data" / "reference" / "security_master.parquet"
DECLARED_USER_AGENT = "Mastermind FIF research lane fif-lane@mastermind.local"


@pytest.fixture(scope="module")
def contract_bytes() -> bytes:
    return CONTRACT_PATH.read_bytes()


@pytest.fixture(scope="module")
def contract(contract_bytes: bytes) -> dict:
    return json.loads(contract_bytes)


@pytest.fixture(scope="module")
def catalog_metric_ids() -> list[str]:
    catalog = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))
    return sorted(str(row["metric_id"]) for row in catalog["metrics"])


def _walk(obj, path=""):
    if isinstance(obj, dict):
        for key, value in obj.items():
            child = f"{path}.{key}" if path else key
            yield child, key
            yield from _walk(value, child)
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from _walk(value, f"{path}[{index}]")
    else:
        yield path, obj


def _all_accessions(contract: dict) -> list[dict]:
    rows = []
    for issuer in contract["issuers"]:
        for row in issuer["accessions"]:
            rows.append(row)
    return rows


def test_json_is_byte_canonical(contract_bytes: bytes, contract: dict) -> None:
    canonical = json.dumps(contract, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    assert contract_bytes == canonical
    assert contract_bytes.endswith(b"\n")


def test_schema_and_contract_id(contract: dict) -> None:
    assert contract["schema"] == "fundamental_forensics.coverage_contract/v1"
    assert contract["contract_id"] == "five_issuer_v1"
    assert contract["capture_basis"] == "reconstruction"
    assert contract["attested"] is False
    assert contract["historical_attestation"] == "unavailable_until_d2_admission"


def test_five_tickers_in_order_with_exact_ciks(contract: dict) -> None:
    tickers = [issuer["ticker"] for issuer in contract["issuers"]]
    assert tickers == list(TICKER_ORDER)
    assert len(contract["issuers"]) == 5
    for issuer in contract["issuers"]:
        assert issuer["cik"] == EXPECTED_CIKS[issuer["ticker"]]
        assert re.fullmatch(r"^\d{10}$", issuer["cik"])
        assert issuer["identity_binding_state"] == (
            "golden_committed" if issuer["ticker"] == "AAPL" else "generic_path_only"
        )
        # G0-a: D0 issuer_class is a checked projection of the kernel SIC map.
        # The recorded class must equal issuer_class_for_sic(sic) for every
        # issuer — SNOW (7372) and GOOGL (7370) are software, BAC (6021) is
        # bank, AAPL (3571) and CAT (3531) are industrial — and the classes
        # stay distinct: software is never collapsed into industrial.
        assert issuer["issuer_class"] == issuer_class_for_sic(issuer["sic"]), (
            issuer["ticker"],
            issuer["sic"],
            issuer["issuer_class"],
        )
    classes = {issuer["ticker"]: issuer["issuer_class"] for issuer in contract["issuers"]}
    assert classes == {
        "AAPL": "industrial",
        "SNOW": "software",
        "CAT": "industrial",
        "BAC": "bank",
        "GOOGL": "software",
    }


def test_accessions_match_pattern_and_are_unique(contract: dict) -> None:
    seen: list[str] = []
    for row in _all_accessions(contract):
        assert ACCESSION_RE.fullmatch(row["accession"]), row["accession"]
        seen.append(row["accession"])
        assert row["form"] in ALLOWED_FORMS
        assert ISO_DATE_RE.fullmatch(row["period_of_report"])
        assert ISO_DATE_RE.fullmatch(row["filing_date"])
        period = date.fromisoformat(row["period_of_report"])
        filed = date.fromisoformat(row["filing_date"])
        assert filed >= period, row["accession"]
    assert len(seen) == len(set(seen))


def test_retention_matches_golden_aapl_query_accessions(contract: dict) -> None:
    retained = [
        row["accession"]
        for row in _all_accessions(contract)
        if row["retention_state"] == "retained_golden_fixture"
    ]
    assert tuple(retained) == GOLDEN_AAPL_QUERY_ACCESSIONS
    assert retained == ["0000320193-25-000079", "0000320193-26-000020"]
    aapl = next(issuer for issuer in contract["issuers"] if issuer["ticker"] == "AAPL")
    aapl_retained = {
        row["accession"]
        for row in aapl["accessions"]
        if row["retention_state"] == "retained_golden_fixture"
    }
    assert aapl_retained == set(GOLDEN_AAPL_QUERY_ACCESSIONS)
    for issuer in contract["issuers"]:
        if issuer["ticker"] == "AAPL":
            continue
        assert all(
            row["retention_state"] == "not_retained" for row in issuer["accessions"]
        )


def test_retained_rows_match_golden_package_manifests(contract: dict) -> None:
    aapl = next(issuer for issuer in contract["issuers"] if issuer["ticker"] == "AAPL")
    by_acc = {row["accession"]: row for row in aapl["accessions"]}
    for accession, manifest_path in MANIFEST_BY_ACCESSION.items():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        row = by_acc[accession]
        assert row["form"] == manifest["form"]
        assert row["period_of_report"] == manifest["period_of_report"]
        assert row["filing_date"] == manifest["filing_date"]
        assert row["retention_state"] == "retained_golden_fixture"


def test_attested_false_everywhere(contract: dict) -> None:
    assert contract["attested"] is False
    assert contract["capture_basis"] == "reconstruction"
    for path, value in _walk(contract):
        if isinstance(value, str) and value == "attested":
            continue
        if path.endswith(".attested") or (isinstance(value, str) and path.endswith("attested")):
            assert value is False, path
        if isinstance(value, dict) and "attested" in value:
            assert not value["attested"], path


def test_rights_lists_empty(contract: dict) -> None:
    rights = contract["source_rights"]
    assert rights["purchases"] == []
    assert rights["licences_accepted"] == []
    assert rights["credentials_required"] == []
    assert rights["provider"] == "sec_edgar_public_filings"
    assert rights["access_policy"] == "sec_fair_access_declared_user_agent"


def test_no_secret_tokens_outside_credential_name_list(contract: dict) -> None:
    for path, value in _walk(contract):
        if not isinstance(value, str):
            continue
        if SECRET_RE.search(value):
            assert (
                path == "known_credential_names_not_used"
                or path.startswith("known_credential_names_not_used[")
            ), path


def test_field_denominator_matches_catalog(
    contract: dict, catalog_metric_ids: list[str]
) -> None:
    denom = contract["field_denominator"]
    assert (
        denom["metric_catalog"]
        == "config/fundamental_forensics/metrics/v1/metric_catalog.yaml"
    )
    assert denom["metric_ids"] == catalog_metric_ids
    assert len(denom["metric_ids"]) == 50
    catalog_set = set(catalog_metric_ids)
    for ticker, metrics in denom["not_applicable"].items():
        assert ticker in TICKER_ORDER
        for metric_id, reason in metrics.items():
            assert metric_id in catalog_set, metric_id
            assert isinstance(reason, str) and reason


def test_known_contradiction_evidence_paths_exist(contract: dict) -> None:
    rows = contract["known_contradictions"]
    assert rows
    ids = {row["id"] for row in rows}
    assert "d0-2docs-vs-3fy" in ids
    assert "d0-8k-item-202-retained-nowhere" in ids
    for row in rows:
        match = EVIDENCE_RE.fullmatch(row["evidence"])
        assert match, row["evidence"]
        path = ROOT / match.group(1)
        assert path.is_file(), row["evidence"]


def test_human_contract_exists_and_mentions_every_cik() -> None:
    assert DOC_PATH.is_file()
    text = DOC_PATH.read_text(encoding="utf-8")
    for cik in EXPECTED_CIKS.values():
        assert cik in text, cik
    assert "five_issuer_v1" in text
    assert "reconstruction" in text
    assert "GOLDEN_AAPL_QUERY_ACCESSIONS" in text


@pytest.fixture(scope="module")
def capture_manifest() -> dict:
    return json.loads(CAPTURE_MANIFEST_PATH.read_text(encoding="utf-8"))


def test_capture_manifest_is_canonical_and_covers_every_cik(
    capture_manifest: dict,
) -> None:
    assert CAPTURE_MANIFEST_PATH.read_bytes() == (
        json.dumps(capture_manifest, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    )
    assert sorted(capture_manifest) == sorted(EXPECTED_CIKS.values())
    for cik, entry in capture_manifest.items():
        assert entry["cik"] == cik
        assert entry["ticker"] in TICKER_ORDER
        assert entry["source_url"] == f"https://data.sec.gov/submissions/CIK{cik}.json"
        assert entry["bytes"] > 0
        assert entry["retrieved_at"].endswith("Z")
        assert entry["user_agent_declared"] == DECLARED_USER_AGENT
        assert entry["budget_owner"] == "collectors.edgar_forensics:SecForensicsCollector"


def test_retained_capture_bytes_match_manifest_and_contract_sic_source(
    contract: dict, capture_manifest: dict
) -> None:
    for issuer in contract["issuers"]:
        cik = issuer["cik"]
        entry = capture_manifest[cik]
        sic_source = issuer["sic_source"]
        capture_path = ROOT / sic_source["capture_path"]
        assert capture_path.is_file(), sic_source["capture_path"]
        body = capture_path.read_bytes()
        digest = hashlib.sha256(body).hexdigest()
        assert digest == entry["sha256"], cik
        assert entry["bytes"] == len(body), cik
        assert digest == sic_source["sha256"], cik
        assert entry["ticker"] == issuer["ticker"]
        assert entry["source_url"] == sic_source["source_url"]
        assert entry["retrieved_at"] == sic_source["retrieved_at"]


def test_contract_sic_pins_match_retained_capture_bytes(
    contract: dict, capture_manifest: dict
) -> None:
    for issuer in contract["issuers"]:
        cik = issuer["cik"]
        body = (ROOT / issuer["sic_source"]["capture_path"]).read_bytes()
        doc = json.loads(body)
        assert str(doc["cik"]).zfill(10) == cik
        assert issuer["sic"] == str(doc["sic"]), cik
        assert issuer["sic"].isdigit(), cik
        assert issuer["sic_source"]["sic_description"] == doc["sicDescription"], cik
        assert str(doc["cik"]).zfill(10) == capture_manifest[cik]["cik"]


def test_security_master_binding_matches_reference_parquet(contract: dict) -> None:
    if not SECURITY_MASTER_PARQUET.is_file():
        pytest.skip(
            "data/reference/security_master.parquet is absent from this sparse "
            "checkout (opt in: python3 scripts/worktree_sparse.py full)"
        )
    try:
        import pandas as pd
    except ImportError:  # pragma: no cover - dependency guard for minimal steps
        pytest.skip("pandas is not installed in this environment")
    blob = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD:data/reference/security_master.parquet"],
        capture_output=True,
        text=True,
    )
    if blob.returncode != 0:
        pytest.skip(f"git rev-parse unavailable: {blob.stderr.strip()}")
    expected_blob = blob.stdout.strip()
    frame = pd.read_parquet(SECURITY_MASTER_PARQUET)
    cik10 = frame["issuer_cik"].astype(str).str.zfill(10)
    for issuer in contract["issuers"]:
        binding = issuer["security_master_binding"]
        assert binding is not None, issuer["ticker"]
        assert binding["security_master_blob"] == expected_blob, issuer["ticker"]
        active = frame[(cik10 == issuer["cik"]) & (frame["superseded_by"].isna())]
        match = active[
            active["listing_key"].str.rsplit("-", n=1).str[-1] == issuer["ticker"]
        ]
        assert len(match) == 1, issuer["ticker"]
        row = match.iloc[0]
        state = row["security_state"]
        assert binding == {
            "issuer_id": row["issuer_id"],
            "security_id": row["security_id"],
            "listing_key": row["listing_key"],
            "mic": row["mic"],
            "issuer_cik": str(row["issuer_cik"]).zfill(10),
            "security_state": None if pd.isna(state) else str(state),
            "effective_at": row["effective_at"].isoformat(),
            "security_master_blob": expected_blob,
        }, issuer["ticker"]


# ---------------------------------------------------------------------------
# Issuer SIC resolver (R1-SIC): the shipped contract is the only source
# ---------------------------------------------------------------------------


def test_issuer_sic_resolver_resolves_members_by_exact_zero_padded_cik(
    contract: dict,
) -> None:
    for issuer in contract["issuers"]:
        # the exact zero-padded spelling and the integer form are one CIK
        assert resolve_issuer_sic(issuer["cik"]) == issuer["sic"], issuer["ticker"]
        assert resolve_issuer_sic(int(issuer["cik"])) == issuer["sic"], issuer["ticker"]


def test_issuer_sic_resolver_returns_none_for_absent_or_sicless_cik(
    tmp_path: Path,
) -> None:
    # a CIK with no member record anywhere resolves to None (fail-closed)
    assert resolve_issuer_sic("0000000000") is None
    coverage = tmp_path / "config" / "fundamental_forensics" / "coverage"
    coverage.mkdir(parents=True)
    (coverage / "synthetic_v1.json").write_text(
        json.dumps({"issuers": [{"cik": "0000000017"}]}), encoding="utf-8"
    )
    # a member record with no sic is the same fail-closed None, never a guess
    assert resolve_issuer_sic("0000000017", repo_root=tmp_path) is None
    assert resolve_issuer_sic("0000000099", repo_root=tmp_path) is None


def test_issuer_sic_resolver_raises_when_contracts_disagree_on_one_cik(
    tmp_path: Path,
) -> None:
    def _root(name: str) -> Path:
        coverage = tmp_path / name / "config" / "fundamental_forensics" / "coverage"
        coverage.mkdir(parents=True)
        return tmp_path / name

    # two shipped spellings of one CIK carrying different SICs
    first = _root("disagree-value")
    (first / "config" / "fundamental_forensics" / "coverage" / "a_v1.json").write_text(
        json.dumps({"issuers": [{"cik": "0000000017", "sic": "3571"}]}),
        encoding="utf-8",
    )
    (first / "config" / "fundamental_forensics" / "coverage" / "b_v1.json").write_text(
        json.dumps({"issuers": [{"cik": "17", "sic": "6021"}]}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="disagree on the SIC"):
        resolve_issuer_sic("0000000017", repo_root=first)

    # present-versus-absent is the same disagreement, never silently resolved
    second = _root("disagree-presence")
    (second / "config" / "fundamental_forensics" / "coverage" / "a_v1.json").write_text(
        json.dumps({"issuers": [{"cik": "0000000017", "sic": "3571"}]}),
        encoding="utf-8",
    )
    (second / "config" / "fundamental_forensics" / "coverage" / "b_v1.json").write_text(
        json.dumps({"issuers": [{"cik": "0000000017"}]}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="disagree on the SIC"):
        resolve_issuer_sic("0000000017", repo_root=second)
