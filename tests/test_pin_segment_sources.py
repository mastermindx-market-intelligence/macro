"""Wholly synthetic tests for the GMI segment-source tooling (ruling 105 step 1).

No network, no secrets, no real-company filing text. The pin end-to-end cases drive
``run_pin`` through a fake SEC session in the style of the repo's collector tests;
the packet cases replay the resulting LocalStore snapshot and prove the produced
owner decision + policy are accepted by ``issuer_disclosure_owner.qualify_records``
with injected identity receipts, exactly as ``_segment_case`` wires them. Nothing
here imports production admission or writes ``data/theme_graph``.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from collectors.edgar_forensics import endpoint_url
from collectors.sec_request_pacer import SecRequestPacer
from engine.company_intelligence import issuer_disclosure_owner as o
from engine.company_intelligence import issuer_disclosures as n
from engine.fundamental_forensics.sec_document_spine import (
    archive_index_document,
    build_filing_manifests,
)
from scripts import pin_segment_sources as m

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "gmi-segment-sources.yml"
TARGETS_PATH = ROOT / "config" / "theme_graph" / "segment_source_targets.v1.json"
SCRIPT_PATH = ROOT / "scripts" / "pin_segment_sources.py"

R2_SECRETS = {
    "R2_RESEARCH_ENDPOINT", "R2_RESEARCH_ACCESS_KEY_ID",
    "R2_RESEARCH_SECRET_ACCESS_KEY", "R2_RESEARCH_BUCKET",
}

# --- synthetic pin fixture constants ----------------------------------------
CIK = "0000000001"
TICKER = "ALPHA"
ACCESSION = "0000000001-24-000001"
RECORDED = "2024-03-01T12:00:00Z"
SUBMISSIONS = {
    "cik": "1", "name": "SYNTHETIC Aurora",
    "filings": {"recent": {
        "accessionNumber": [ACCESSION], "form": ["10-K"],
        "filingDate": ["2024-02-26"], "reportDate": ["2023-12-31"],
        "acceptanceDateTime": ["2024-02-26T16:00:00Z"],
        "primaryDocument": ["annual.htm"],
    }},
}
SPAN_START = "SYNTHETIC annual report."
SPAN_END = "profit_denominator: 100"
SEG_BODY = (
    "SYNTHETIC annual report. Aurora operates the Data Center Storage segment. "
    "Aurora buys Widget wafers from Boreal. "
    "revenue: 30 revenue_denominator: 100 profit: 10 profit_denominator: 100"
).encode("utf-8")
FIGURES = {
    "revenue": {"text": "30", "sign": "+", "scale": "units", "anchor": "revenue: "},
    "revenue_denominator": {"text": "100", "sign": "+", "scale": "units",
                            "anchor": "revenue_denominator: "},
    "profit": {"text": "10", "sign": "+", "scale": "units", "anchor": "profit: "},
    "profit_denominator": {"text": "100", "sign": "+", "scale": "units",
                           "anchor": "profit_denominator: "},
}
SEG_ISSUER = "ISS:US-XNAS-ALPHA"
IDENTITY_RECEIPT = {
    "schema": o.context.RECEIPT_SCHEMA, "identity_mode": "current",
    "issuer_id": SEG_ISSUER, "evidenced_cik": CIK, "source_commit": "a" * 40,
    "sources": {name: {"sha256": "b" * 64, "byte_length": 100} for name in o.IDENTITY_SOURCES},
    "evidence_source": "sec_company_tickers", "evidence_snapshot": "2024-02-01",
}
IDENTITIES = {"subject": IDENTITY_RECEIPT}
THEME = yaml.safe_dump({"families": {"sec_public_filing_facts": {
    "rights_class": "derived_display_ok", "auth_class": "keyless_public"}}}).encode()


def _identity_reader(ticker):
    assert ticker == TICKER
    return IDENTITY_RECEIPT


# --- fake SEC session (mirrors the repo collector-test style) ---------------

class _FakeResponse:
    def __init__(self, url, body, status_code, headers):
        self.url = url
        self.status_code = status_code
        self.headers = headers
        self._body = body
        self.closed = False

    def iter_content(self, chunk_size=8192, **kwargs):
        for offset in range(0, len(self._body), chunk_size):
            yield self._body[offset:offset + chunk_size]

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def close(self):
        self.closed = True

    @property
    def content(self):
        raise AssertionError("bounded collector must not read response.content")


class _FakeSession:
    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(url)
        if url not in self.routes:
            raise AssertionError(f"unexpected URL requested: {url}")
        body, status, headers = self.routes[url]
        return _FakeResponse(url, body, status, headers)


def _pin(tmp_path, body, *, primary_headers=None):
    """Drive run_pin end to end through a fake session into a LocalStore."""
    manifest = build_filing_manifests(SUBMISSIONS, cik=CIK, ticker=TICKER,
                                      recorded_at=RECORDED)[0]
    index_url = archive_index_document(manifest)["archive_url"]
    primary_url = manifest["documents"][0]["archive_url"]
    submissions_url = endpoint_url(CIK, "submissions")
    index_bytes = json.dumps({"directory": {"item": [
        {"name": "annual.htm"}, {"name": "other.htm"}]}}).encode("utf-8")
    routes = {
        submissions_url: (json.dumps(SUBMISSIONS).encode("utf-8"), 200, {"ETag": '"synthetic"'}),
        index_url: (index_bytes, 200, {"ETag": '"synthetic"'}),
        primary_url: (body, 200, primary_headers or {"ETag": '"synthetic"'}),
    }
    session = _FakeSession(routes)
    targets_path = tmp_path / "targets.json"
    targets_path.write_text(json.dumps({
        "schema": m.TARGETS_SCHEMA,
        "targets": [{"ticker": TICKER, "cik": CIK, "forms": ["10-K", "10-K/A"]}],
    }), encoding="utf-8")
    out = tmp_path / "out"
    store = tmp_path / "store"
    report = m.run_pin(
        targets_path, tmp_path / "raw", tmp_path / "archive", out,
        local_store=store, session=session,
        pacer=SecRequestPacer(min_interval_seconds=0), now=RECORDED,
    )
    return SimpleNamespace(report=report, store=store, out=out, session=session,
                           primary_url=primary_url, row=report["targets"][0])


def _packet_request(pin, **overrides):
    row = {
        "ticker": TICKER, "accession": ACCESSION,
        "manifest_key": pin.row["manifest_key"], "document_id": pin.row["document_id"],
        "subject_label": "Aurora", "disclosed_line": "Data Center Storage",
        "share_scope": "segment", "fiscal_year": 2023,
        "span_start_anchor": SPAN_START, "span_end_anchor": SPAN_END,
        "figures": FIGURES, "profit_measure": "operating_income",
        "reviewer": "synthetic fixture", "reviewed_at": "2024-03-03T11:00:00Z",
        "adopted_at": "2024-03-05T10:00:00Z", "policy_recorded_at": "2024-03-04T10:00:00Z",
    }
    row.update(overrides)
    return {"schema": m.REQUEST_SCHEMA, "rows": [row]}


def _run_packet(tmp_path, pin, request):
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(request), encoding="utf-8")
    out = tmp_path / "packet_out"
    report = m.run_packet(
        request_path, pin.report["snapshot_id"], out,
        local_store=pin.store, identity_reader=_identity_reader,
        theme_sources_raw=THEME, now="2024-03-03T10:00:00Z",
    )
    return SimpleNamespace(report=report, out=out)


# ---------------------------------------------------------------------------
# Workflow shape
# ---------------------------------------------------------------------------

def _workflow():
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


def test_workflow_dispatch_only_least_privilege_and_concurrency():
    wf = _workflow()
    triggers = wf.get("on", wf.get(True))
    assert set(triggers) == {"workflow_dispatch"}
    for bad in ("push", "pull_request", "pull_request_target", "schedule",
                "workflow_run", "repository_dispatch"):
        assert bad not in triggers
    assert wf["permissions"] == {"contents": "read"}
    assert wf["concurrency"] == {"group": "gmi-segment-sources", "cancel-in-progress": False}
    inputs = triggers["workflow_dispatch"]["inputs"]
    assert inputs["step"]["type"] == "choice"
    assert set(inputs["step"]["options"]) == {"pin", "packet", "propose"}
    assert {"snapshot_id", "request_path", "manifest_path"} <= set(inputs)


def test_workflow_every_job_main_guard_timeout_and_pinned_checkout():
    wf = _workflow()
    assert wf["jobs"], "workflow has no jobs"
    for job in wf["jobs"].values():
        assert "github.ref == 'refs/heads/main'" in job["if"]
        assert job["timeout-minutes"] <= 60
        checkout = job["steps"][0]
        assert checkout["uses"] == "actions/checkout@v4"
        assert checkout["with"]["ref"] == "main"
        assert checkout["with"]["persist-credentials"] is False


def test_workflow_no_input_interpolation_inside_run():
    for job in _workflow()["jobs"].values():
        for step in job["steps"]:
            run = step.get("run", "")
            assert "${{ inputs." not in run
            assert "${{ github.event." not in run
            assert "set -x" not in run
            assert "git push" not in run and "gh pr" not in run


def test_workflow_secrets_only_four_names_and_only_in_env():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert set(re.findall(r"secrets\.([A-Za-z0-9_]+)", text)) <= R2_SECRETS
    for job in _workflow()["jobs"].values():
        for step in job["steps"]:
            assert "secrets." not in step.get("run", "")
            for value in (step.get("with") or {}).values():
                assert "secrets." not in str(value)
            for value in (step.get("env") or {}).values():
                for name in re.findall(r"secrets\.([A-Za-z0-9_]+)", str(value)):
                    assert name in R2_SECRETS


def test_workflow_uploads_out_as_pinned_artifact_14_days():
    for job in _workflow()["jobs"].values():
        uploads = [s for s in job["steps"]
                   if str(s.get("uses", "")).startswith("actions/upload-artifact@")]
        assert uploads, "job does not upload its --out artifact"
        for upload in uploads:
            assert re.fullmatch(r"actions/upload-artifact@[0-9a-f]{40}", upload["uses"])
            assert upload["with"]["retention-days"] == 14


# ---------------------------------------------------------------------------
# Target list
# ---------------------------------------------------------------------------

EXPECTED_CIKS = {
    "MU": "0000723125", "SNDK": "0002023554", "WDC": "0000106040",
    "STX": "0001137789", "NTAP": "0001002047", "NTNX": "0001618732",
    "RMBS": "0000917273", "SIMO": "0001329394", "MRAM": "0001438423",
    "PENG": "0001616533", "AMKR": "0001047127",
}


def test_target_list_schema_shape_and_initial_content():
    payload = json.loads(TARGETS_PATH.read_text(encoding="utf-8"))
    assert payload["schema"] == m.TARGETS_SCHEMA
    targets = payload["targets"]
    assert len(targets) == len(EXPECTED_CIKS)
    assert len({t["ticker"] for t in targets}) == len(targets)
    for target in targets:
        assert set(target) == {"ticker", "cik", "forms"}
        assert re.fullmatch(r"[0-9]{10}", target["cik"])
        assert set(target["forms"]) <= set(n.SEGMENT_FORM_TYPES)
    by_ticker = {t["ticker"]: t for t in targets}
    assert set(by_ticker) == set(EXPECTED_CIKS)
    for ticker, cik in EXPECTED_CIKS.items():
        assert by_ticker[ticker]["cik"] == cik
        expected_forms = ["20-F", "20-F/A"] if ticker == "SIMO" else ["10-K", "10-K/A"]
        assert by_ticker[ticker]["forms"] == expected_forms
    # The script's own loader accepts the committed list.
    assert len(m._load_targets(TARGETS_PATH)) == len(EXPECTED_CIKS)


# ---------------------------------------------------------------------------
# pin end to end
# ---------------------------------------------------------------------------

def test_pin_writes_report_snapshot_and_never_creates_latest_pointer(tmp_path):
    pin = _pin(tmp_path, SEG_BODY)
    report = pin.report
    assert re.fullmatch(r"ffsecsrc_[0-9a-f]{64}", report["snapshot_id"])
    # The snapshot clock is the injected now (owner may normalize microseconds).
    assert report["snapshot_at"].startswith("2024-03-01T12:00:00")
    assert (pin.out / "pin_report.json").read_bytes() == n._canonical(report)
    row = pin.row
    assert row["ticker"] == TICKER and row["cik"] == CIK
    assert row["form"] == "10-K" and row["accession"] == ACCESSION
    assert row["filed_on"] == "2024-02-26"
    assert row["manifest_key"] and row["document_id"]
    assert re.fullmatch(r"[0-9a-f]{64}", row["raw_sha256"])
    assert row["byte_length"] == len(SEG_BODY)
    assert "refusal" not in row
    # The shared filing-forensics latest pointer is NEVER published by this lane.
    latest = pin.store / "fundamental_forensics" / "sec-source" / "v1" / "latest.json"
    assert not latest.exists() and not latest.is_symlink()


def test_pin_over_cap_document_is_typed_refusal_skipped_without_retry(tmp_path):
    headers = {"ETag": '"synthetic"', "Content-Length": str(n.MAX_SEC_SOURCE_BYTES + 1)}
    pin = _pin(tmp_path, SEG_BODY, primary_headers=headers)
    row = pin.row
    assert row["refusal"] == "DOCUMENT_OVER_CAP"
    assert row["accession"] == ACCESSION
    assert "manifest_key" not in row
    # The refused primary is fetched once and never retried at a larger cap.
    assert pin.session.calls.count(pin.primary_url) == 1
    # The run still completes and writes its report.
    assert (pin.out / "pin_report.json").exists()


# ---------------------------------------------------------------------------
# packet on the pinned snapshot
# ---------------------------------------------------------------------------

def test_packet_owner_decision_and_policy_are_accepted_by_qualify_records(tmp_path):
    pin = _pin(tmp_path, SEG_BODY)
    packet = _run_packet(tmp_path, pin, _packet_request(pin))
    assert packet.report["rows"][0]["status"] == "ADOPTED"
    stem = f"{TICKER}_{ACCESSION}"
    spec_raw = (packet.out / f"{stem}_SEGMENT_OWNER_DECISION.json").read_bytes()
    policy_raw = (packet.out / f"{stem}_SOURCE_POLICY.json").read_bytes()
    registry = (ROOT / o.REGISTRY_PATH).read_bytes()
    snapshot = o.qualify_records("a" * 40, spec_raw, policy_raw, registry,
                                 IDENTITIES, theme_sources_raw=THEME)
    # The canonical bytes written are exactly what the owner qualifier accepts.
    assert n._canonical(snapshot.spec) == spec_raw
    fact = snapshot.spec["fact"]
    assert fact["kind"] == "segment_activity" and fact["form_type"] == "10-K"
    assert fact["revenue"] == 30.0 and fact["revenue_denominator"] == 100.0
    assert fact["profit"] == 10.0 and fact["profit_denominator"] == 100.0
    policy = json.loads(policy_raw)
    assert policy["rights_family"] == "sec_public_filing_facts"
    assert policy["permitted_use"]["kind"] == "segment_activity"
    assert policy["permitted_use"]["source_quotation"] is False
    assert policy["permitted_use"]["source_body_export"] is False
    assert policy["permitted_use"]["reviewer_text"] is False


def test_packet_missing_anchor_is_typed_row_refusal(tmp_path):
    pin = _pin(tmp_path, SEG_BODY)
    request = _packet_request(pin, span_start_anchor="THIS ANCHOR IS NOT IN THE BODY")
    packet = _run_packet(tmp_path, pin, request)
    row = packet.report["rows"][0]
    assert row["status"] == "REFUSED" and row["refusal"] == "ANCHOR_MISSING"
    stem = f"{TICKER}_{ACCESSION}"
    assert not (packet.out / f"{stem}_SEGMENT_OWNER_DECISION.json").exists()
    assert not (packet.out / f"{stem}_SOURCE_POLICY.json").exists()


def test_packet_non_unique_anchor_is_typed_row_refusal(tmp_path):
    pin = _pin(tmp_path, SEG_BODY)
    # "Aurora" occurs twice in the synthetic body, so it is not a unique anchor.
    request = _packet_request(pin, span_start_anchor="Aurora")
    packet = _run_packet(tmp_path, pin, request)
    row = packet.report["rows"][0]
    assert row["status"] == "REFUSED" and row["refusal"] == "ANCHOR_NOT_UNIQUE"


def test_packet_outputs_carry_no_filing_text_beyond_schema_fields(tmp_path):
    pin = _pin(tmp_path, SEG_BODY)
    packet = _run_packet(tmp_path, pin, _packet_request(pin))
    assert packet.report["rows"][0]["status"] == "ADOPTED"
    # Labels and figure texts are schema-carried; the surrounding prose is not.
    non_schema_prose = (b"Widget wafers", b"buys", b"Boreal", SEG_BODY)
    for path in packet.out.rglob("*"):
        if not path.is_file():
            continue
        content = path.read_bytes()
        for prose in non_schema_prose:
            assert prose not in content, f"filing prose leaked into {path.name}"


# ---------------------------------------------------------------------------
# Filing choice and propose flags
# ---------------------------------------------------------------------------

def _manifest(form, filed_on, accession):
    return {"filing": {"form": form, "accession": accession}, "clocks": {"filed_on": filed_on}}


def test_choose_filing_prefers_original_over_later_amendment():
    original = _manifest("10-K", "2026-08-01", "0000000001-26-000001")
    amendment = _manifest("10-K/A", "2026-10-01", "0000000001-26-000002")
    assert m.choose_filing([original, amendment]) is original


def test_choose_filing_takes_latest_original_and_falls_back_to_amendment():
    old = _manifest("20-F", "2025-04-01", "0000000002-25-000001")
    new = _manifest("20-F", "2026-04-01", "0000000002-26-000001")
    assert m.choose_filing([old, new]) is new
    only_amendment = _manifest("10-K/A", "2026-10-01", "0000000003-26-000001")
    assert m.choose_filing([only_amendment]) is only_amendment


def test_profit_driver_flag_accepts_only_json_booleans():
    assert m.profit_driver_flag(True) == "--profit-driver"
    assert m.profit_driver_flag(False) == "--no-profit-driver"
    for bad in ("false", "true", 0, 1, None):
        with pytest.raises(ValueError, match="PROFIT_DRIVER_NOT_BOOLEAN"):
            m.profit_driver_flag(bad)


# ---------------------------------------------------------------------------
# Script hygiene
# ---------------------------------------------------------------------------

def test_script_never_imports_tests_or_references_forensics_targets_or_workflows():
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "import tests" not in source and "from tests" not in source
    assert "config/fundamental_forensics" not in source
    assert "filing-forensics-sec.yml" not in source
    assert "filing-forensics-broad-sec.yml" not in source
