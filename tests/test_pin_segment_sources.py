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


def _pin(tmp_path, body, *, primary_headers=None, tickers=(TICKER,)):
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
        "targets": [{"ticker": t, "cik": CIK, "forms": ["10-K", "10-K/A"]} for t in tickers],
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
        assert job["if"] == "github.ref == 'refs/heads/main'"
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


def _input_check_script():
    """The workflow's own input-check prelude (regex vars + valid_input), verbatim."""
    run = next(s["run"] for job in _workflow()["jobs"].values() for s in job["steps"]
               if "valid_input()" in s.get("run", ""))
    lines = run.splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip().startswith("SNAPSHOT_RE="))
    end = next(i for i, line in enumerate(lines) if i > start and line.strip() == "}")
    return "\n".join(lines[start:end + 1])


def test_workflow_input_checks_are_whole_string_and_refuse_line_breaks():
    import subprocess
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "grep -Eq" not in text
    prelude = _input_check_script()
    snap = "ffsecsrc_" + "a" * 64
    path = "research/theme_graph/sec_segment_20261114/request.json"
    cases = [
        (snap, "SNAPSHOT_RE", True),
        (path, "PATH_RE", True),
        (snap + "\n" + snap, "SNAPSHOT_RE", False),
        ("x\n" + snap, "SNAPSHOT_RE", False),
        (path + "\nresearch/theme_graph/sec_segment_20261114/b.json", "PATH_RE", False),
        (path + "\r", "PATH_RE", False),
        ("../" + path, "PATH_RE", False),
        (snap + "0", "SNAPSHOT_RE", False),
    ]
    for value, var, ok in cases:
        script = prelude + f'\nvalid_input "$VALUE" "${var}"'
        proc = subprocess.run(["bash", "-c", script], env={"VALUE": value, "PATH": "/usr/bin:/bin"})
        assert (proc.returncode == 0) is ok, (value, var)


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
    # Ruling 118: semicap, AI-semis and the remaining memory companies.
    "ACLS": "0001113232", "ACMR": "0001680062", "ALAB": "0001736297",
    "AMAT": "0000006951", "AMD": "0000002488", "ARM": "0001973239",
    "ASX": "0001122411", "AVGO": "0001730168", "CAMT": "0001109138",
    "CDNS": "0000813672", "COHR": "0000820318", "COHU": "0000021535",
    "CRDO": "0001807794", "DELL": "0001571996", "ENTG": "0001101302",
    "FN": "0001408710", "FORM": "0001039399", "GFS": "0001709048",
    "ICHR": "0001652535", "INTC": "0000050863", "KLAC": "0000319201",
    "KLIC": "0000056978", "LITE": "0001633978", "LRCX": "0000707549",
    "MKSI": "0001049502", "MPWR": "0001280452", "MTSI": "0001493594",
    "NVDA": "0001045810", "NVMI": "0001109345", "ONTO": "0000704532",
    "PDFS": "0001120914", "PLAB": "0000810136", "QCOM": "0000804328",
    "SMCI": "0001375365", "SNPS": "0000883241", "TER": "0000097210",
    "TSM": "0001046179", "UCTT": "0001275014", "VECO": "0000103145",
    "VICR": "0000751978",
}
# Foreign private issuers file 20-F; everyone else 10-K. Amendments of the same family only.
EXPECTED_20F = {"ARM", "ASX", "CAMT", "GFS", "NVMI", "TSM"}


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
        expected_forms = (["20-F", "20-F/A"] if ticker == "SIMO" or ticker in EXPECTED_20F
                          else ["10-K", "10-K/A"])
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
    assert (pin.out / "pin_report.json").read_bytes() == m.report_bytes(report)
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


def test_pin_report_for_the_full_target_list_is_written_past_the_owner_object_cap(tmp_path):
    # Run 43564756554 (51 targets) crashed writing its report: the owner's 16 KB
    # object cap applies to disclosure objects, not to this lane's run report.
    tickers = tuple(f"T{i:02d}" for i in range(60))
    pin = _pin(tmp_path, SEG_BODY, tickers=tickers)
    raw = (pin.out / "pin_report.json").read_bytes()
    assert len(raw) > n.MAX_OBJECT_BYTES
    assert raw == m.report_bytes(pin.report)
    assert [r["ticker"] for r in json.loads(raw)["targets"]] == list(tickers)
    assert all("refusal" not in r for r in pin.report["targets"])


def test_report_bytes_is_canonical_and_bounded():
    assert m.report_bytes({"b": 1, "a": "é"}) == '{"a":"é","b":1}'.encode("utf-8")
    with pytest.raises(m.ReportRefused, match="REPORT_JSON_INVALID"):
        m.report_bytes({"a": float("nan")})
    with pytest.raises(m.ReportRefused, match="REPORT_TOO_LARGE"):
        m.report_bytes({"a": "x" * m.MAX_REPORT_BYTES})


def test_pin_report_over_the_ceiling_is_refused_before_the_sync_writes_anything(
        tmp_path, monkeypatch):
    # A report that cannot be written must leave no object or snapshot in the store.
    monkeypatch.setattr(m, "MAX_REPORT_BYTES", 2048)
    with pytest.raises(m.ReportRefused, match="REPORT_TOO_LARGE"):
        _pin(tmp_path, SEG_BODY, tickers=tuple(f"T{i:02d}" for i in range(20)))
    store = tmp_path / "store"
    assert not store.exists() or not any(p.is_file() for p in store.rglob("*"))
    assert not (tmp_path / "out" / "pin_report.json").exists()


def test_pin_report_at_the_preflight_edge_still_fits_with_its_snapshot_fields(tmp_path):
    pin = _pin(tmp_path, SEG_BODY)
    head = len(m.report_bytes(pin.report)) - len(
        m.report_bytes({"schema": pin.report["schema"], "targets": pin.report["targets"]}))
    assert 0 < head <= m.REPORT_SNAPSHOT_ALLOWANCE


def test_pin_leaves_an_existing_latest_pointer_byte_identical(tmp_path):
    latest = tmp_path / "store" / "fundamental_forensics" / "sec-source" / "v1" / "latest.json"
    latest.parent.mkdir(parents=True)
    seeded = b'{"snapshot_id": "ffsecsrc_' + b"0" * 64 + b'", "owner": "filing-forensics"}'
    latest.write_bytes(seeded)
    pin = _pin(tmp_path, SEG_BODY)
    assert "refusal" not in pin.row
    assert latest.read_bytes() == seeded


def test_pin_over_cap_streamed_body_without_content_length_is_refused(tmp_path):
    body = b"x" * (n.MAX_SEC_SOURCE_BYTES + 1)
    pin = _pin(tmp_path, body, primary_headers={"ETag": '"synthetic"'})
    row = pin.row
    assert row["refusal"] == "DOCUMENT_OVER_CAP"
    assert "manifest_key" not in row
    assert pin.session.calls.count(pin.primary_url) == 1
    assert (pin.out / "pin_report.json").exists()


def test_pin_row_carries_an_empty_later_amendments_list_when_none_exist(tmp_path):
    assert _pin(tmp_path, SEG_BODY).row["later_amendments"] == []


def test_pin_streamed_over_cap_row_records_bytes_at_cut_and_amendments(tmp_path):
    body = b"x" * (n.MAX_SEC_SOURCE_BYTES + 1)
    row = _pin(tmp_path, body, primary_headers={"ETag": '"synthetic"'}).row
    assert row["refusal"] == "DOCUMENT_OVER_CAP"
    # The stream was cut one byte past the limit; that is all the run knows.
    assert row["size_bytes"] == n.MAX_SEC_SOURCE_BYTES + 1
    assert row["size_basis"] == m.SIZE_BASIS_CUT
    # Refused rows carry the later-amendment list too.
    assert row["later_amendments"] == []
    # The refusal message (which names the URL) is never written into the row.
    assert all("http" not in str(value) for value in row.values())


def test_pin_declared_over_cap_row_records_the_declared_size_without_download(tmp_path):
    declared = n.MAX_SEC_SOURCE_BYTES + 5000
    headers = {"ETag": '"synthetic"', "Content-Length": str(declared)}
    pin = _pin(tmp_path, SEG_BODY, primary_headers=headers)
    assert pin.row["refusal"] == "DOCUMENT_OVER_CAP"
    assert pin.row["size_bytes"] == declared
    assert pin.row["size_basis"] == m.SIZE_BASIS_DECLARED
    # One request for the refused primary; nothing is fetched to measure it.
    assert pin.session.calls.count(pin.primary_url) == 1


def test_over_cap_size_reads_only_the_collector_refusal_shape():
    limit = n.MAX_SEC_SOURCE_BYTES
    msg = "SEC archive response exceeds bounded ingest limit ({} > {}) for https://example.test/a.htm"
    assert m.over_cap_size(ValueError(msg.format(limit + 1, limit))) == (limit + 1, m.SIZE_BASIS_CUT)
    assert m.over_cap_size(ValueError(msg.format(limit + 9, limit))) == (limit + 9, m.SIZE_BASIS_DECLARED)
    assert m.over_cap_size(ValueError("SEC archive response has invalid Content-Length")) == (None, None)


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
    stem = m.packet_output_stem(_packet_request(pin)["rows"][0])
    spec_raw =(packet.out / f"{stem}_SEGMENT_OWNER_DECISION.json").read_bytes()
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
    stem = m.packet_output_stem(request["rows"][0])
    assert not (packet.out / f"{stem}_SEGMENT_OWNER_DECISION.json").exists()
    assert not (packet.out / f"{stem}_SOURCE_POLICY.json").exists()


def test_packet_two_lines_of_one_filing_produce_four_distinct_files(tmp_path):
    pin = _pin(tmp_path, SEG_BODY)
    first = _packet_request(pin)["rows"][0]
    # A second line of the SAME filing, present in the same span text.
    second = {**first, "disclosed_line": "Data Center Storage segment"}
    request = {"schema": m.REQUEST_SCHEMA, "rows": [first, second]}
    packet = _run_packet(tmp_path, pin, request)
    assert [r["status"] for r in packet.report["rows"]] == ["ADOPTED", "ADOPTED"]
    assert packet.report["outcome"] == "complete"
    stems = [m.packet_output_stem(first), m.packet_output_stem(second)]
    assert stems[0] != stems[1]
    assert [r["stem"] for r in packet.report["rows"]] == stems
    written = sorted(p.name for p in packet.out.iterdir() if p.name != "packet_report.json")
    assert written == sorted(f"{s}_{kind}.json" for s in stems
                             for kind in ("SEGMENT_OWNER_DECISION", "SOURCE_POLICY"))
    lines = {json.loads((packet.out / f"{s}_SEGMENT_OWNER_DECISION.json").read_bytes())["fact"]["disclosed_line"]
             for s in stems}
    assert lines == {first["disclosed_line"], second["disclosed_line"]}


def test_packet_request_with_colliding_output_names_is_refused_before_any_write(tmp_path):
    pin = _pin(tmp_path, SEG_BODY)
    row = _packet_request(pin)["rows"][0]
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps({"schema": m.REQUEST_SCHEMA, "rows": [row, dict(row)]}),
                            encoding="utf-8")
    out = tmp_path / "packet_out"
    with pytest.raises(m.PacketRequestRefused) as caught:
        m.run_packet(request_path, pin.report["snapshot_id"], out, local_store=pin.store,
                     identity_reader=_identity_reader, theme_sources_raw=THEME,
                     now="2024-03-03T10:00:00Z")
    assert caught.value.code == "PACKET_OUTPUT_NAME_COLLISION_ROWS_0_1"
    # Nothing at all was written: not even the output directory or a report.
    assert not out.exists()


def test_packet_cli_names_a_collision_and_exits_two(tmp_path, capsys):
    pin = _pin(tmp_path, SEG_BODY)
    row = _packet_request(pin)["rows"][0]
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps({"schema": m.REQUEST_SCHEMA, "rows": [row, dict(row)]}),
                            encoding="utf-8")
    out = tmp_path / "cli_out"
    code = m.main(["packet", "--request", str(request_path), "--snapshot-id", pin.report["snapshot_id"],
                   "--out", str(out), "--local-store", str(pin.store)])
    assert code == 2
    assert "REFUSED: PACKET_OUTPUT_NAME_COLLISION_ROWS_0_1" in capsys.readouterr().err
    assert not out.exists()


def test_packet_report_says_partial_when_some_rows_are_refused(tmp_path):
    pin = _pin(tmp_path, SEG_BODY)
    good = _packet_request(pin)["rows"][0]
    bad = {**good, "disclosed_line": "Data Center Storage segment",
           "span_start_anchor": "THIS ANCHOR IS NOT IN THE BODY"}
    packet = _run_packet(tmp_path, pin, {"schema": m.REQUEST_SCHEMA, "rows": [good, bad]})
    assert [r["status"] for r in packet.report["rows"]] == ["ADOPTED", "REFUSED"]
    assert packet.report["outcome"] == "partial"


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


def test_later_amendments_lists_only_later_slash_a_filings():
    original = _manifest("10-K", "2026-08-01", "0000000001-26-000001")
    earlier_a = _manifest("10-K/A", "2026-03-01", "0000000001-26-000000")
    later_a = _manifest("10-K/A", "2026-10-01", "0000000001-26-000002")
    later_a2 = _manifest("10-K/A", "2026-11-01", "0000000001-26-000003")
    eligible = [original, earlier_a, later_a, later_a2]
    chosen = m.choose_filing(eligible)
    assert chosen is original
    assert m.later_amendments(eligible, chosen) == [
        "0000000001-26-000002", "0000000001-26-000003"]
    assert m.later_amendments([original], original) == []


def _propose_row(**overrides):
    row = {
        "ticker": "ALPHA", "issuer": "ISS:US-XNAS-ALPHA", "theme": "theme:hbm_packaging",
        "role": "component_supplier", "knowledge_cutoff": "2026-11-14",
        "created": "2026-11-14T00:00:00Z",
        "spec_path": "research/theme_graph/sec_segment_20261114/A_SPEC.json",
        "policy_path": "research/theme_graph/sec_segment_20261114/A_POLICY.json",
        "exposure_role": "primary", "profit_driver": True,
    }
    row.update(overrides)
    return row


def _write_manifest(tmp_path, rows):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"rows": rows}), encoding="utf-8")
    return path


# Exactly the line scripts/propose_activity_membership.py prints on success
# (probation.activity_proposal_id = "actprop:" + 24 hex; status PROPOSED).
REAL_PROPOSAL_ID = "actprop:287edbf7e04b8aba873b7493"
REAL_WRITER_STDOUT = (
    f'{{"proposal_id": "{REAL_PROPOSAL_ID}", "status": "PROPOSED", '
    f'"appended": 1, "unchanged": 0, '
    f'"ledger": "/home/runner/work/macro/out/activity_proposals.jsonl"}}\n')


class _Proc:
    returncode = 0
    stdout = REAL_WRITER_STDOUT
    stderr = ""


def test_writer_still_prints_the_shape_the_report_parser_reads():
    # Guards the parser against drift in the writer's id format and print line.
    source = (m.ROOT / "scripts" / "propose_activity_membership.py").read_text(encoding="utf-8")
    assert '{{"proposal_id": "{row["proposal_id"]}", "status": "{row["status"]}", ' in source
    probation_src = (m.ROOT / "engine" / "theme_graph" / "probation.py").read_text(encoding="utf-8")
    assert 'return "actprop:" + hashlib.sha256(' in probation_src
    assert '.hexdigest()[:24]' in probation_src
    assert '"status": "PROPOSED",' in probation_src


def test_run_propose_builds_the_unchanged_cli_argument_list(tmp_path):
    calls = []

    def runner(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return _Proc()

    rows = [_propose_row(), _propose_row(ticker="BETA", profit_driver=False)]
    out = tmp_path / "out"
    report = m.run_propose(_write_manifest(tmp_path, rows), out, python="PY", runner=runner)
    ledger = str(out / "activity_proposals.jsonl")
    assert calls[0][0] == [
        "PY", str(m.ROOT / "scripts" / "propose_activity_membership.py"), "propose",
        "--issuer", "ISS:US-XNAS-ALPHA", "--theme", "theme:hbm_packaging",
        "--role", "component_supplier", "--knowledge-cutoff", "2026-11-14",
        "--created", "2026-11-14T00:00:00Z", "--segment-packet",
        "research/theme_graph/sec_segment_20261114/A_SPEC.json",
        "research/theme_graph/sec_segment_20261114/A_POLICY.json", "config/theme_sources.yml",
        "--ledger", ledger, "--exposure-role", "primary", "--profit-driver",
    ]
    assert calls[1][0][-1] == "--no-profit-driver"
    assert calls[0][1]["cwd"] == m.ROOT and "shell" not in calls[0][1]
    assert [r["exit_code"] for r in report["rows"]] == [0, 0]
    assert report["outcome"] == "complete"
    assert report["rows"][0]["proposal"] == {"proposal_id": REAL_PROPOSAL_ID, "status": "PROPOSED",
                                             "appended": 1, "unchanged": 0}
    assert "/home/runner" not in (out / "propose_report.json").read_text(encoding="utf-8")
    assert (out / "propose_report.json").exists()


class _RefusedProc:
    returncode = 2
    stdout = ""
    stderr = "REFUSED: SEGMENT_SHARE_INVALID\n"


def test_run_propose_report_says_partial_when_the_writer_refuses_partway(tmp_path):
    procs = iter([_Proc(), _RefusedProc()])
    rows = [_propose_row(), _propose_row(ticker="BETA")]
    report = m.run_propose(_write_manifest(tmp_path, rows), tmp_path / "out", python="PY",
                           runner=lambda cmd, **kwargs: next(procs))
    assert [r["exit_code"] for r in report["rows"]] == [0, 2]
    assert report["outcome"] == "partial"
    assert report["rows"][1]["refusal_codes"] == ["SEGMENT_SHARE_INVALID"]
    assert report["rows"][1]["proposal"] is None


class _ChattyProc:
    returncode = 2
    stdout = 'warning: something from a document\n' + REAL_WRITER_STDOUT
    stderr = ("REFUSED: FACT_KIND_INVALID: unexpected kind 'Revenue from DRAM products'\n"
              "REFUSED: oddly shaped line\nnoise\n")


def test_run_propose_report_carries_only_fixed_shape_fields(tmp_path):
    out = tmp_path / "out"
    report = m.run_propose(_write_manifest(tmp_path, [_propose_row()]), out, python="PY",
                           runner=lambda cmd, **kwargs: _ChattyProc())
    row = report["rows"][0]
    assert set(row) == {"ticker", "exit_code", "proposal", "refusal_codes"}
    assert row["proposal"] == {"proposal_id": REAL_PROPOSAL_ID, "status": "PROPOSED",
                               "appended": 1, "unchanged": 0}
    assert row["refusal_codes"] == ["FACT_KIND_INVALID", "UNPARSED_REFUSAL"]
    raw = (out / "propose_report.json").read_text(encoding="utf-8")
    for leaked in ("DRAM", "warning", "/home/runner", "ledger", "oddly"):
        assert leaked not in raw


@pytest.mark.parametrize("line", [
    '{"proposal_id": "actprop_abc123", "status": "PROPOSED"}',
    '{"proposal_id": "actprop:287edbf7e04b8aba873b7493", "status": "ACCEPTED"}',
    '{"proposal_id": "actprop:287EDBF7E04B8ABA873B7493", "status": "PROPOSED"}',
    'actprop:287edbf7e04b8aba873b7493 PROPOSED',
])
def test_proposal_parser_refuses_anything_but_the_writer_contract(line):
    assert m._proposal_result(line + "\n") is None


def test_run_propose_refuses_a_manifest_ticker_that_is_not_a_ticker(tmp_path):
    calls = []
    with pytest.raises(m.ManifestRowRefused, match="INVALID_TICKER"):
        m.run_propose(_write_manifest(tmp_path, [_propose_row(ticker="Revenue from DRAM")]),
                      tmp_path / "out", python="PY", runner=lambda c, **k: calls.append(c))
    assert calls == [] and not (tmp_path / "out").exists()


def test_packet_request_with_an_over_long_disclosed_line_is_refused_before_any_write(tmp_path):
    rows = [{"ticker": "AAA", "accession": "0000000000-26-000001",
             "disclosed_line": "x" * (m.MAX_DISCLOSED_LINE_CHARS + 1)}]
    with pytest.raises(m.PacketRequestRefused, match="PACKET_REQUEST_ROW_0_INVALID"):
        m._validate_packet_rows(rows)
    ok = [{"ticker": "AAA", "accession": "0000000000-26-000001",
           "disclosed_line": "x" * m.MAX_DISCLOSED_LINE_CHARS}]
    assert len(m._validate_packet_rows(ok)) == 1


@pytest.mark.parametrize("bad, code", [
    ({"profit_driver": "false"}, "PROFIT_DRIVER_NOT_BOOLEAN"),
    ({"theme": ""}, "INVALID_THEME"),
    ({"spec_path": None}, "INVALID_SPEC_PATH"),
])
def test_run_propose_refuses_a_bad_row_before_any_subprocess(tmp_path, bad, code):
    calls = []
    rows = [_propose_row(), _propose_row(ticker="BETA", **bad), _propose_row(ticker="GAMMA")]
    out = tmp_path / "out"
    with pytest.raises(m.ManifestRowRefused) as info:
        m.run_propose(_write_manifest(tmp_path, rows), out, runner=lambda *a, **k: calls.append(a))
    assert info.value.index == 1 and info.value.code == code
    assert calls == []
    assert not (out / "activity_proposals.jsonl").exists()
    assert not (out / "propose_report.json").exists()


def test_run_propose_refuses_a_row_missing_a_key(tmp_path):
    row = _propose_row()
    del row["exposure_role"]
    with pytest.raises(m.ManifestRowRefused) as info:
        m.run_propose(_write_manifest(tmp_path, [_propose_row(), row]), tmp_path / "out",
                      runner=lambda *a, **k: pytest.fail("subprocess started"))
    assert (info.value.index, info.value.code) == (1, "MISSING_EXPOSURE_ROLE")


def test_main_names_the_refused_row_without_writing(tmp_path, capsys):
    rows = [_propose_row(), _propose_row(profit_driver="yes")]
    out = tmp_path / "out"
    code = m.main(["propose", "--manifest", str(_write_manifest(tmp_path, rows)), "--out", str(out)])
    assert code == 2
    assert "PROPOSE_MANIFEST_ROW_1_PROFIT_DRIVER_NOT_BOOLEAN" in capsys.readouterr().err
    assert not out.exists() or not any(out.iterdir())


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
