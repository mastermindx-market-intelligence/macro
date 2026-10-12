"""Hermetic tests for the G-SRC issuer-generic capture lane (R8).

No network, no staged bytes: everything here runs over committed fixtures,
the D0 coverage contract, and pure functions of the capture script. The one
byte-level admission re-check is ``data_gate`` and skips unless
``FIF_GSRC_STAGE_ROOT`` points at the lane stage directory.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

import pytest

from scripts import capture_fif_issuer_packages as gsrc

_REPO = Path(__file__).resolve().parents[1]
_D0_PATH = _REPO / "config" / "fundamental_forensics" / "coverage" / "five_issuer_v1.json"
_G_SRC = _REPO / "tests" / "fixtures" / "fundamental_forensics" / "g_src"
_AAPL_FIXTURES = {
    "aapl_10k_2025": _REPO / "tests" / "fixtures" / "fundamental_forensics" / "aapl_10k_2025",
    "aapl_10q_2026q3": _REPO
    / "tests"
    / "fixtures"
    / "fundamental_forensics"
    / "aapl_10q_2026q3",
}
_REQUEST_LOG_KEYS = {
    "seq",
    "url",
    "status",
    "byte_length",
    "content_sha256",
    "started_at_utc",
    "elapsed_ms",
    "attempt",
}
_HEX64 = re.compile(r"^[0-9a-f]{64}$")

# The R5 admission/capture sets as frozen in D0 at the 2026-10-12 seat ruling.
_R5_SETS = {
    "SNOW": {
        ("0001640147-26-000008", "admission_candidate"),
        ("0001640147-25-000052", "admission_candidate"),
        ("0001640147-26-000037", "admission_candidate"),
        ("0001640147-26-000030", "admission_candidate"),
        ("0001640147-25-000187", "capture_only"),
        ("0001640147-24-000101", "capture_only"),
    },
    "CAT": {
        ("0000018230-26-000008", "admission_candidate"),
        ("0000018230-25-000008", "admission_candidate"),
        ("0000018230-26-000046", "admission_candidate"),
        ("0000018230-26-000021", "admission_candidate"),
        ("0000018230-25-000040", "capture_only"),
    },
    "BAC": {
        ("0000070858-26-000157", "admission_candidate"),
        ("0000070858-25-000139", "admission_candidate"),
        ("0000070858-26-000394", "admission_candidate"),
        ("0000070858-26-000249", "admission_candidate"),
        ("0000070858-25-000268", "capture_only"),
    },
    "GOOGL": {
        ("0001652044-26-000018", "admission_candidate"),
        ("0001652044-25-000014", "admission_candidate"),
        ("0001652044-26-000071", "admission_candidate"),
        ("0001652044-26-000048", "admission_candidate"),
        ("0001652044-25-000062", "capture_only"),
    },
}


def _load_d0() -> dict:
    return json.loads(_D0_PATH.read_text(encoding="utf-8"))


def _d0_issuer_rows() -> dict[str, dict]:
    return {str(row["ticker"]): row for row in _load_d0()["issuers"]}


# ---------------------------------------------------------------------------
# (a) AAPL statement_roles reproduction over committed fixture members.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fixture_name", sorted(_AAPL_FIXTURES))
def test_aapl_statement_roles_reproduction(fixture_name: str) -> None:
    fixture = _AAPL_FIXTURES[fixture_name]
    manifest = json.loads((fixture / "package_manifest.json").read_text(encoding="utf-8"))
    members = fixture / "members"
    pre_name = next(p.name for p in members.iterdir() if p.name.endswith("_pre.xml"))
    xsd_name = next(p.name for p in members.iterdir() if p.name.endswith(".xsd"))
    roles, state = gsrc.classify_statement_roles(
        (members / pre_name).read_bytes(), (members / xsd_name).read_bytes()
    )
    assert state == "extracted"
    committed = manifest.get("statement_roles")
    if committed is None:
        # The 10-K golden manifest predates statement_roles; extraction must
        # still succeed deterministically over its members.
        assert set(roles) == {"income_statement", "balance_sheet", "cash_flow"}
        return
    for kind in ("income_statement", "balance_sheet", "cash_flow"):
        assert roles[kind]["role_uri"] == committed[kind]["role_uri"], kind
        assert roles[kind]["title"] == committed[kind]["title"], kind
        assert roles[kind]["title_search"] == committed[kind]["title_search"], kind


# ---------------------------------------------------------------------------
# (b) Selection over D0 + typed refusals.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ticker", sorted(_R5_SETS))
def test_selection_over_d0_matches_r5_sets(ticker: str) -> None:
    row = _d0_issuer_rows()[ticker]
    extras = ["0001640147-24-000101"] if ticker == "SNOW" else []
    selected = gsrc.select_issuer_accessions(row, extras)
    got = {(item.accession, item.selection) for item in selected}
    assert got == _R5_SETS[ticker]
    for item in selected:
        assert item.form in {"10-K", "10-Q"}
        assert re.fullmatch(r"\d{10}-\d{2}-\d{6}", item.accession)


def test_selection_refuses_accession_not_in_d0() -> None:
    row = _d0_issuer_rows()["SNOW"]
    with pytest.raises(gsrc.SelectionError) as excinfo:
        gsrc.select_issuer_accessions(row, ["9999999999-99-999999"])
    assert excinfo.value.code == "extra_accession_not_in_d0"


def test_selection_year_ago_absent_adds_nothing() -> None:
    synthetic = {
        "ticker": "ZZTEST",
        "cik": "0000000042",
        "legal_name": "Test Issuer",
        "security_master_binding": {
            "issuer_id": "ISS:US-XTEST-ZZ",
            "security_id": "SEC:US-XTEST-ZZ",
            "listing_key": "US-XTEST-ZZ",
        },
        "accessions": [
            {
                "accession": "0000000042-26-000001",
                "form": "10-Q",
                "filing_date": "2026-09-01",
                "period_of_report": "2026-08-31",
            },
            {
                "accession": "0000000042-26-000002",
                "form": "10-Q",
                "filing_date": "2026-06-01",
                "period_of_report": "2026-05-31",
            },
            {
                "accession": "0000000042-25-000003",
                "form": "10-K",
                "filing_date": "2025-12-01",
                "period_of_report": "2025-11-30",
            },
        ],
    }
    selected = gsrc.select_issuer_accessions(synthetic)
    # No 2025-08 10-Q row exists, so no year-ago comparable is added.
    assert {(item.accession, item.selection) for item in selected} == {
        ("0000000042-25-000003", "admission_candidate"),
        ("0000000042-26-000001", "admission_candidate"),
        ("0000000042-26-000002", "admission_candidate"),
    }


def test_main_refuses_unknown_issuer(capsys: pytest.CaptureFixture[str]) -> None:
    rc = gsrc.main(["--issuer", "NOSUCH"])
    assert rc != 0
    assert "gsrc_refusal: unknown_issuer" in capsys.readouterr().out


def test_main_refuses_non_d0_extra_accession(capsys: pytest.CaptureFixture[str]) -> None:
    rc = gsrc.main(["--issuer", "SNOW", "--extra-accession", "1234567890-00-000001"])
    assert rc != 0
    assert "extra_accession_not_in_d0" in capsys.readouterr().out


def test_main_refuses_min_interval_below_floor(capsys: pytest.CaptureFixture[str]) -> None:
    rc = gsrc.main(["--issuer", "SNOW", "--min-interval", "0.5"])
    assert rc != 0
    assert "min_interval_below_floor" in capsys.readouterr().out


def test_min_interval_floor_is_one_second() -> None:
    assert gsrc.MIN_INTERVAL_FLOOR_SECONDS == 1.0
    assert gsrc.USER_AGENT == "Mastermind FIF research lane fif-lane@mastermind.local"


# ---------------------------------------------------------------------------
# (c) Committed g_src manifests, capture indexes and request logs.
# ---------------------------------------------------------------------------


def _g_src_issuers() -> list[str]:
    if not _G_SRC.is_dir():
        return []
    return sorted(p.name for p in _G_SRC.iterdir() if p.is_dir())


@pytest.mark.skipif(not _g_src_issuers(), reason="no g_src fixtures committed yet")
def test_committed_g_src_manifests_match_contract_and_index() -> None:
    from engine.fundamental_forensics.admitted_filing_package import REQUIRED_STORED_ROLES

    d0_rows = {
        (str(issuer["cik"]), str(acc["accession"]), str(acc["form"]))
        for issuer in _load_d0()["issuers"]
        for acc in issuer.get("accessions") or []
    }
    declared_reason = _load_d0()["retained_package_law"]["declared_reason"]
    for cik10 in _g_src_issuers():
        issuer_dir = _G_SRC / cik10
        capture_index = json.loads((issuer_dir / "capture_index.json").read_text(encoding="utf-8"))
        rows_by_accession = {str(row["accession"]): row for row in capture_index}
        manifest_files = sorted(issuer_dir.glob("*/package_manifest.json"))
        with_manifest = {
            accession
            for accession, row in rows_by_accession.items()
            if row.get("manifest_sha256")
        }
        assert {p.parent.name for p in manifest_files} == with_manifest
        for path in manifest_files:
            payload = path.read_bytes()
            row = rows_by_accession[path.parent.name]
            assert hashlib.sha256(payload).hexdigest() == row["manifest_sha256"]
            manifest = json.loads(payload.decode("utf-8"))
            assert manifest["schema"] == "fundamental_forensics.golden_filing_package/v1"
            assert (manifest["cik"], manifest["accession"], manifest["form"]) in d0_rows
            assert manifest["cik"] == cik10
            stored = [m for m in manifest["members"] if m["state"] == "stored"]
            assert manifest["retained_count"] == len(stored) == 6
            assert {m["role"] for m in stored} == set(REQUIRED_STORED_ROLES)
            assert manifest["member_count"] == len(manifest["members"])
            for member in stored:
                assert _HEX64.fullmatch(member["content_sha256"])
                assert isinstance(member["byte_length"], int) and member["byte_length"] > 0
            for member in manifest["members"]:
                if member["state"] == "not_requested":
                    assert member["declared_reason"] == declared_reason
            if row["admission"] == "ADMITTED":
                roles = manifest["statement_roles"]
                assert isinstance(roles, dict)
                for kind in ("income_statement", "balance_sheet", "cash_flow"):
                    assert roles[kind]["role_uri"]
                    assert roles[kind]["title"]


@pytest.mark.skipif(not _g_src_issuers(), reason="no g_src fixtures committed yet")
def test_committed_g_src_file_inventory_is_closed() -> None:
    allowed = {"package_manifest.json", "request_log.jsonl", "capture_index.json"}
    files = [p for p in _G_SRC.rglob("*") if p.is_file()]
    assert files, "g_src fixture root exists but holds no files"
    for path in files:
        assert path.name in allowed, f"unexpected file under g_src: {path}"


@pytest.mark.skipif(not _g_src_issuers(), reason="no g_src fixtures committed yet")
def test_committed_request_logs_are_well_formed() -> None:
    for cik10 in _g_src_issuers():
        lines = (
            (_G_SRC / cik10 / "request_log.jsonl").read_text(encoding="utf-8").splitlines()
        )
        assert lines, f"empty request log for {cik10}"
        seqs = []
        for line in lines:
            record = json.loads(line)
            assert set(record) == _REQUEST_LOG_KEYS
            assert isinstance(record["seq"], int)
            assert record["url"].startswith(("https://www.sec.gov/", "https://data.sec.gov/"))
            assert isinstance(record["attempt"], int) and 1 <= record["attempt"] <= 3
            assert isinstance(record["elapsed_ms"], int) and record["elapsed_ms"] >= 0
            assert _HEX64.fullmatch(record["content_sha256"])
            assert isinstance(record["byte_length"], int) and record["byte_length"] >= 0
            seqs.append(record["seq"])
        assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)


# ---------------------------------------------------------------------------
# (d) The script source carries no issuer literal.
# ---------------------------------------------------------------------------


def test_script_source_carries_no_issuer_literal() -> None:
    source = (_REPO / "scripts" / "capture_fif_issuer_packages.py").read_text(encoding="utf-8")
    for ticker in ("SNOW", "CAT", "BAC", "GOOGL"):
        assert not re.search(rf"\b{ticker}\b", source), f"ticker literal in script: {ticker}"
    for cik in ("1640147", "18230", "70858", "1652044"):
        assert cik not in source, f"CIK literal in script: {cik}"
    assert not re.search(r"\d{10}-\d{2}-\d{6}", source), "accession literal in script"


# ---------------------------------------------------------------------------
# (e) Pure functions: witness building, member naming, classification.
# ---------------------------------------------------------------------------


def test_build_witness_bytes_shape() -> None:
    witness = {
        "source_url": "https://data.sec.gov/submissions/CIK0000000042.json",
        "source_path": "filings.recent[accessionNumber=0000000042-26-000001]",
        "accessionNumber": "0000000042-26-000001",
        "form": "10-Q",
        "filingDate": "2026-09-01",
        "reportDate": "2026-08-31",
        "acceptanceDateTime": "2026-09-01T12:00:00Z",
        "primaryDocument": "zztest-20260831.htm",
    }
    payload = gsrc.build_witness_bytes(witness)
    assert payload.endswith(b"\n")
    parsed = json.loads(payload.decode("utf-8"))
    assert parsed == witness
    # indent=2 + sort_keys=True is the committed AAPL witness byte shape.
    assert payload == (json.dumps(parsed, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with pytest.raises(ValueError):
        gsrc.build_witness_bytes({"form": "10-Q"})


def test_member_names_for_primary() -> None:
    names = gsrc.member_names_for_primary("zztest-20260831.htm")
    assert names["primary"] == "zztest-20260831.htm"
    assert names["schema"] == "zztest-20260831.xsd"
    assert names["presentation"] == "zztest-20260831_pre.xml"
    assert names["calculation"] == "zztest-20260831_cal.xml"
    assert names["definition"] == "zztest-20260831_def.xml"
    assert names["label"] == "zztest-20260831_lab.xml"


_SYN_SCHEMA = b"""<schema xmlns="http://www.xbrl.org/2003/instance">
<roleType roleURI="r:ops"><definition>100 - Statement - Consolidated Statements of Operations</definition></roleType>
<roleType roleURI="r:ops_plain"><definition>101 - Statement - Statements of Income</definition></roleType>
<roleType roleURI="r:bs"><definition>102 - Statement - Consolidated Balance Sheets</definition></roleType>
<roleType roleURI="r:bs_par"><definition>103 - Statement - Consolidated Balance Sheets (Parenthetical)</definition></roleType>
<roleType roleURI="r:cf"><definition>104 - Statement - Consolidated Statements of Cash Flows</definition></roleType>
<roleType roleURI="r:ci"><definition>105 - Statement - Statements of Comprehensive Income</definition></roleType>
<roleType roleURI="r:cond"><definition>106 - Statement - Consolidated Statements of Financial Condition</definition></roleType>
<roleType roleURI="r:doc"><definition>107 - Document - Cover</definition></roleType>
<roleType roleURI="r:disc"><definition>108 - Disclosure - Goodwill</definition></roleType>
</schema>"""


def _syn_pre(roles: list[str]) -> bytes:
    links = "".join(
        f'<presentationLink xlink:role="{role}"/>' for role in roles
    )
    return (
        b'<linkbase xmlns="http://www.xbrl.org/2003/linkbase" '
        b'xmlns:xlink="http://www.w3.org/1999/xlink">' + links.encode() + b"</linkbase>"
    )


def test_classification_picks_one_per_kind_and_skips_non_statements() -> None:
    pre = _syn_pre(
        ["r:ops", "r:ops_plain", "r:bs", "r:bs_par", "r:cf", "r:ci", "r:doc", "r:disc"]
    )
    schema = _SYN_SCHEMA.replace(
        b'<roleType roleURI="r:ops_plain"><definition>101 - Statement - Statements of Income'
        b'</definition></roleType>',
        b"",
    ).replace(
        b'<roleType roleURI="r:cond"><definition>106 - Statement - Consolidated Statements '
        b'of Financial Condition</definition></roleType>',
        b"",
    )
    roles, state = gsrc.classify_statement_roles(pre, schema)
    assert state == "extracted"
    assert roles["income_statement"]["role_uri"] == "r:ops"
    assert roles["balance_sheet"]["role_uri"] == "r:bs"
    assert roles["cash_flow"]["role_uri"] == "r:cf"


def test_classification_refuses_ambiguity_with_candidates() -> None:
    pre = _syn_pre(["r:ops", "r:ops_plain", "r:bs", "r:cf"])
    roles, state = gsrc.classify_statement_roles(pre, _SYN_SCHEMA)
    assert roles is None
    assert state == (
        "statement_roles_ambiguous:income_statement:"
        "Consolidated Statements of Operations | Statements of Income"
    )


def test_classification_reports_missing_kind() -> None:
    pre = _syn_pre(["r:ops", "r:bs"])
    roles, state = gsrc.classify_statement_roles(pre, _SYN_SCHEMA)
    assert roles is None
    assert state == "statement_roles_missing:cash_flow"


def test_classification_combined_income_only_when_no_plain_income() -> None:
    pre = _syn_pre(["r:ci", "r:bs", "r:cf"])
    roles, state = gsrc.classify_statement_roles(pre, _SYN_SCHEMA)
    assert state == "extracted"
    assert roles["income_statement"]["role_uri"] == "r:ci"
    # A plain income title always outranks the combined one.
    pre_with_plain = _syn_pre(["r:ops", "r:ci", "r:bs", "r:cf"])
    roles, state = gsrc.classify_statement_roles(pre_with_plain, _SYN_SCHEMA)
    assert state == "extracted"
    assert roles["income_statement"]["role_uri"] == "r:ops"


def test_classification_financial_position_and_condition_variants() -> None:
    pre = _syn_pre(["r:ops", "r:cond", "r:cf"])
    roles, state = gsrc.classify_statement_roles(pre, _SYN_SCHEMA)
    assert state == "extracted"
    assert roles["balance_sheet"]["role_uri"] == "r:cond"


def test_title_search_drops_one_trailing_parenthesised_suffix() -> None:
    assert (
        gsrc._title_search("Statements of Operations (Unaudited)")
        == "Statements of Operations"
    )
    assert gsrc._title_search("Statements of Operations") == "Statements of Operations"
    assert gsrc._title_search("(Everything)") == "(Everything)"


# ---------------------------------------------------------------------------
# data_gate: byte-level digest re-check + D1 re-admission over staged bytes.
# ---------------------------------------------------------------------------


@pytest.mark.data_gate
def test_staged_bytes_match_manifests_and_readmit() -> None:
    stage_root = os.environ.get("FIF_GSRC_STAGE_ROOT")
    if not stage_root:
        pytest.skip("FIF_GSRC_STAGE_ROOT is not set; staged bytes are not present")
    stage = Path(stage_root).expanduser()
    issuers = _g_src_issuers()
    assert issuers, "no committed g_src fixtures to check against"
    from engine.fundamental_forensics.admitted_filing_package import (
        AdmittedFilingPackageError,
        admit_retained_filing_package,
    )

    checked = 0
    for cik10 in issuers:
        capture_index = json.loads(
            (_G_SRC / cik10 / "capture_index.json").read_text(encoding="utf-8")
        )
        for row in capture_index:
            if not row.get("manifest_sha256"):
                continue
            accession = str(row["accession"])
            package_dir = stage / cik10 / accession
            manifest = json.loads(
                (_G_SRC / cik10 / accession / "package_manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            index_bytes = (package_dir / "index.json").read_bytes()
            assert hashlib.sha256(index_bytes).hexdigest() == manifest["index_sha256"]
            assert len(index_bytes) == manifest["index_byte_length"]
            witness_bytes = (package_dir / "sec_submissions_witness.json").read_bytes()
            witness_meta = manifest["acceptance_witness"]
            assert (
                hashlib.sha256(witness_bytes).hexdigest()
                == witness_meta["content_sha256"]
            )
            assert len(witness_bytes) == witness_meta["byte_length"]
            members = {}
            for member in manifest["members"]:
                if member["state"] != "stored":
                    continue
                payload = (package_dir / "members" / member["name"]).read_bytes()
                assert hashlib.sha256(payload).hexdigest() == member["content_sha256"]
                assert len(payload) == member["byte_length"]
                members[member["name"]] = payload
            checked += 1
            if row["statement_roles_state"] != "extracted":
                # Capture-side role refusal: D1 was never the arbiter.
                continue
            try:
                admit_retained_filing_package(
                    index_bytes=index_bytes,
                    manifest=manifest,
                    members=members,
                    witness_bytes=witness_bytes,
                    capture_recorded_at=manifest["fixture_recorded_at"],
                )
            except AdmittedFilingPackageError as exc:
                assert str(exc.code) == row["admission"], (accession, exc.code, row["admission"])
            else:
                assert row["admission"] == "ADMITTED", accession
    assert checked > 0
