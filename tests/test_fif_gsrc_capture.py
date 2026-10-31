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

import urllib.error

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


def test_admission_candidates_are_rule_only_by_signature() -> None:
    # R5 candidates are a function of the D0 rows alone: no extras parameter
    # exists through which an operator-supplied accession could reach them.
    import inspect

    assert list(inspect.signature(gsrc.r5_admission_candidates).parameters) == ["rows"]


@pytest.mark.parametrize("ticker", sorted(_R5_SETS))
def test_extras_never_change_the_admission_candidates(ticker: str) -> None:
    row = _d0_issuer_rows()[ticker]
    rule = {item.accession for item in gsrc.r5_admission_candidates(row["accessions"])}
    assert rule == {acc for acc, sel in _R5_SETS[ticker] if sel == "admission_candidate"}
    accessions = [str(item["accession"]) for item in row["accessions"]]
    for extras in [[acc] for acc in accessions] + [accessions]:
        selected = gsrc.select_issuer_accessions(row, extras)
        assert {
            item.accession for item in selected if item.selection == "admission_candidate"
        } == rule, extras
        for extra in extras:
            if extra not in rule:
                assert [
                    item.selection for item in selected if item.accession == extra
                ] == ["capture_only"], extra


_CLOCK = "2026-10-12T00:00:00Z"


def test_main_refuses_unknown_issuer(capsys: pytest.CaptureFixture[str]) -> None:
    rc = gsrc.main(["--issuer", "NOSUCH", "--captured-at", _CLOCK])
    assert rc != 0
    assert "gsrc_refusal: unknown_issuer" in capsys.readouterr().out


def test_main_refuses_non_d0_extra_accession(capsys: pytest.CaptureFixture[str]) -> None:
    rc = gsrc.main(
        [
            "--issuer",
            "SNOW",
            "--captured-at",
            _CLOCK,
            "--extra-accession",
            "1234567890-00-000001",
        ]
    )
    assert rc != 0
    assert "extra_accession_not_in_d0" in capsys.readouterr().out


def test_main_refuses_min_interval_below_floor(capsys: pytest.CaptureFixture[str]) -> None:
    rc = gsrc.main(["--issuer", "SNOW", "--min-interval", "0.5"])
    assert rc != 0
    assert "min_interval_below_floor" in capsys.readouterr().out


def test_min_interval_floor_is_one_second() -> None:
    assert gsrc.MIN_INTERVAL_FLOOR_SECONDS == 1.0


# M1: the capture clock is injected, never read from the wall clock.


def test_main_refuses_missing_captured_at(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def _no_contract(_path: object) -> None:
        raise AssertionError("a run without --captured-at must refuse before any other work")

    monkeypatch.setattr(gsrc, "load_contract", _no_contract)
    rc = gsrc.main(["--issuer", "SNOW"])
    assert rc == 2
    assert "gsrc_refusal: captured_at_required" in capsys.readouterr().out


def test_capture_clock_has_no_wall_clock_fallback() -> None:
    with pytest.raises(SystemExit, match="captured_at_required"):
        gsrc._capture_clock(None)
    assert gsrc._capture_clock(_CLOCK).isoformat() == "2026-10-12T00:00:00+00:00"


# M3: the SEC user agent is the FIF-family canonical helper, never a literal.


def test_script_carries_no_hard_coded_user_agent() -> None:
    source = (_REPO / "scripts" / "capture_fif_issuer_packages.py").read_text(encoding="utf-8")
    assert not hasattr(gsrc, "USER_AGENT")
    assert "mastermind.local" not in source
    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", source), "e-mail literal in script"
    assert "from collectors.edgar_forensics import _user_agent" in source


def test_resolved_user_agent_is_the_fif_canonical_helper() -> None:
    edgar_forensics = pytest.importorskip("collectors.edgar_forensics")
    assert gsrc._resolve_sec_user_agent() == edgar_forensics._user_agent(_REPO)


def test_main_refuses_unresolvable_user_agent(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def _missing() -> str:
        raise ValueError("config.yml edgar.user_agent is required")

    monkeypatch.setattr(gsrc, "_resolve_sec_user_agent", _missing)
    rc = gsrc.main(["--issuer", "SNOW", "--captured-at", _CLOCK])
    assert rc == 2
    assert "gsrc_refusal: sec_user_agent_unavailable: ValueError" in capsys.readouterr().out


def test_main_refuses_malformed_config_yaml_as_typed_code(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    yaml = pytest.importorskip("yaml")
    malformed = "edgar: {user_agent: [unclosed"
    with pytest.raises(yaml.YAMLError) as real:
        yaml.safe_load(malformed)

    def _malformed() -> str:
        # The real PyYAML parse failure a malformed config.yml raises.
        return str(yaml.safe_load(malformed))

    monkeypatch.setattr(gsrc, "_resolve_sec_user_agent", _malformed)
    rc = gsrc.main(["--issuer", "SNOW", "--captured-at", _CLOCK])
    assert rc == 2
    out = capsys.readouterr().out
    assert f"gsrc_refusal: sec_user_agent_unavailable: {type(real.value).__name__}: " in out
    assert "Traceback" not in out


# M2: a status-less URLError is retried within the bound and logged.


class _NoPacer:
    def acquire(self) -> None:
        return None


class _FakeResponse:
    status = 200
    headers = {"Last-Modified": "Mon, 12 Oct 2026 00:00:00 GMT"}

    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


def _scripted_fetcher(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outcomes: list[object]
) -> tuple["gsrc.PacedFetcher", "gsrc.IssuerRequestLog"]:
    script = list(outcomes)

    def _urlopen(request: object, timeout: object) -> _FakeResponse:
        outcome = script.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return _FakeResponse(outcome)

    monkeypatch.setattr(gsrc.urllib.request, "urlopen", _urlopen)
    monkeypatch.setattr(gsrc, "RETRY_BACKOFF_SECONDS", (0.0, 0.0))
    log = gsrc.IssuerRequestLog(tmp_path / "request_log.jsonl")
    log.open()
    return gsrc.PacedFetcher(_NoPacer(), "test-agent", log), log


def _log_lines(tmp_path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in (tmp_path / "request_log.jsonl").read_text(encoding="utf-8").splitlines()
    ]


def test_url_error_is_retried_and_logged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fetch, log = _scripted_fetcher(
        tmp_path,
        monkeypatch,
        [
            urllib.error.URLError(ConnectionResetError("reset")),
            urllib.error.URLError("name resolution failed"),
            b"ok",
        ],
    )
    body, last_modified = fetch.get("https://www.sec.gov/Archives/edgar/data/42/x.htm")
    log.close()
    assert body == b"ok"
    assert last_modified == "Mon, 12 Oct 2026 00:00:00 GMT"
    lines = _log_lines(tmp_path)
    assert [line["status"] for line in lines] == ["url_error", "url_error", 200]
    assert [line["attempt"] for line in lines] == [1, 2, 3]


def test_url_error_exhaustion_is_a_typed_fetch_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fetch, log = _scripted_fetcher(
        tmp_path,
        monkeypatch,
        [urllib.error.URLError(ConnectionRefusedError("refused")) for _ in range(gsrc.MAX_ATTEMPTS)],
    )
    with pytest.raises(gsrc.FetchFailure) as caught:
        fetch.get("https://www.sec.gov/Archives/edgar/data/42/x.htm")
    log.close()
    assert caught.value.status == "url_error"
    assert "url_error:ConnectionRefusedError" in str(caught.value)
    assert len(_log_lines(tmp_path)) == gsrc.MAX_ATTEMPTS


def test_http_error_is_not_absorbed_by_the_url_error_clause(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = "https://www.sec.gov/Archives/edgar/data/42/x.htm"
    fetch, log = _scripted_fetcher(
        tmp_path,
        monkeypatch,
        [urllib.error.HTTPError(url, 404, "Not Found", hdrs=None, fp=None)],
    )
    with pytest.raises(gsrc.FetchFailure) as caught:
        fetch.get(url)
    log.close()
    assert caught.value.status == 404
    assert [line["status"] for line in _log_lines(tmp_path)] == [404]


# M2 + M4: only the submissions walk maps to fetch_failed:submissions, and an
# interrupted issuer loop never leaves a partial capture_index that reads as
# complete.


def _run_main_in_tmp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ticker: str
) -> tuple[list[object], Path]:
    monkeypatch.setattr(gsrc, "_ROOT", tmp_path)
    monkeypatch.setattr(gsrc, "_resolve_sec_user_agent", lambda: "test-agent")
    cik10 = gsrc.canonical_cik(_d0_issuer_rows()[ticker]["cik"])
    index_path = (
        tmp_path / "tests" / "fixtures" / "fundamental_forensics" / "g_src" / cik10
        / "capture_index.json"
    )
    argv: list[object] = [
        "--issuer",
        ticker,
        "--captured-at",
        _CLOCK,
        "--contract",
        str(_D0_PATH),
        "--stage-root",
        str(tmp_path / "stage"),
    ]
    return argv, index_path


def test_capture_package_key_error_is_not_relabelled_as_submissions_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    argv, index_path = _run_main_in_tmp(tmp_path, monkeypatch, "SNOW")
    plan = gsrc.select_issuer_accessions(_d0_issuer_rows()["SNOW"])
    assert len(plan) >= 2
    monkeypatch.setattr(
        gsrc,
        "build_submissions_index",
        lambda fetch, cik10, wanted: {accession: {} for accession in wanted},
    )
    calls: list[str] = []

    def _capture(**kwargs: object) -> tuple[dict, dict]:
        selected = kwargs["selected"]
        calls.append(selected.accession)
        if len(calls) > 1:
            raise KeyError("primaryDocument")
        row = {
            "accession": selected.accession,
            "form": selected.form,
            "period_of_report": selected.period_of_report,
            "selection": selected.selection,
            "manifest_sha256": None,
            "admission": "ADMITTED",
            "statement_roles_state": "extracted",
        }
        return row, {"admission": "ADMITTED"}

    monkeypatch.setattr(gsrc, "capture_package", _capture)
    with pytest.raises(KeyError):
        gsrc.main([str(arg) for arg in argv])
    rows = json.loads(index_path.read_text(encoding="utf-8"))
    assert [row["accession"] for row in rows] == [item.accession for item in plan]
    assert rows[0]["admission"] == "ADMITTED"
    assert {row["admission"] for row in rows[1:]} == {
        f"{gsrc.CAPTURE_INCOMPLETE_PREFIX}:KeyError"
    }
    assert all(row["admission"] != "fetch_failed:submissions" for row in rows)
    assert all(row["manifest_sha256"] is None for row in rows[1:])


def test_submissions_failure_still_maps_to_fetch_failed_submissions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    argv, index_path = _run_main_in_tmp(tmp_path, monkeypatch, "SNOW")
    plan = gsrc.select_issuer_accessions(_d0_issuer_rows()["SNOW"])

    def _broken_submissions(fetch: object, cik10: str, wanted: object) -> dict:
        raise gsrc.FetchFailure("request failed after 3 attempt(s)", status="url_error")

    def _never(**kwargs: object) -> None:
        raise AssertionError("no package capture after an unusable submissions walk")

    monkeypatch.setattr(gsrc, "build_submissions_index", _broken_submissions)
    monkeypatch.setattr(gsrc, "capture_package", _never)
    assert gsrc.main([str(arg) for arg in argv]) == 0
    rows = json.loads(index_path.read_text(encoding="utf-8"))
    assert [row["accession"] for row in rows] == [item.accession for item in plan]
    assert {row["admission"] for row in rows} == {"fetch_failed:submissions"}
    summary = json.loads(capsys.readouterr().out)
    assert summary["totals"]["refusals"] == {"fetch_failed": len(plan)}


def _admitted_row(selected: object) -> dict:
    return {
        "accession": selected.accession,
        "form": selected.form,
        "period_of_report": selected.period_of_report,
        "selection": selected.selection,
        "manifest_sha256": None,
        "admission": "ADMITTED",
        "statement_roles_state": "extracted",
    }


def _capture_recording_out_dirs(out_dirs: list[Path]) -> object:
    def _capture(**kwargs: object) -> tuple[dict, dict]:
        out_dirs.append(Path(kwargs["out_issuer_dir"]))
        selected = kwargs["selected"]
        return _admitted_row(selected), {"admission": "ADMITTED"}

    return _capture


def test_out_root_default_writes_under_g_src(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    argv, index_path = _run_main_in_tmp(tmp_path, monkeypatch, "SNOW")
    out_dirs: list[Path] = []
    monkeypatch.setattr(
        gsrc,
        "build_submissions_index",
        lambda fetch, cik10, wanted: {accession: {} for accession in wanted},
    )
    monkeypatch.setattr(gsrc, "capture_package", _capture_recording_out_dirs(out_dirs))
    assert gsrc.main([str(arg) for arg in argv]) == 0
    default_cik_dir = (
        tmp_path / "tests" / "fixtures" / "fundamental_forensics" / "g_src" / "0001640147"
    )
    assert index_path.is_file()
    assert index_path.parent == default_cik_dir
    assert set(out_dirs) == {default_cik_dir}
    assert (default_cik_dir / "request_log.jsonl").is_file()


def test_out_root_flag_redirects_writes_and_default_root_stays_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    argv, _default_index_path = _run_main_in_tmp(tmp_path, monkeypatch, "SNOW")
    custom = tmp_path / "heldout" / "packages"
    argv = [*argv, "--out-root", str(custom)]
    out_dirs: list[Path] = []
    monkeypatch.setattr(
        gsrc,
        "build_submissions_index",
        lambda fetch, cik10, wanted: {accession: {} for accession in wanted},
    )
    monkeypatch.setattr(gsrc, "capture_package", _capture_recording_out_dirs(out_dirs))
    assert gsrc.main([str(arg) for arg in argv]) == 0
    custom_cik_dir = custom / "0001640147"
    assert set(out_dirs) == {custom_cik_dir}
    assert (custom_cik_dir / "capture_index.json").is_file()
    assert (custom_cik_dir / "request_log.jsonl").is_file()
    assert not (
        tmp_path / "tests" / "fixtures" / "fundamental_forensics" / "g_src"
    ).exists()


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
# Capture-only rows are retained and flagged, never admitted.
# ---------------------------------------------------------------------------


def test_committed_capture_only_rows_are_never_admitted() -> None:
    seen_capture_only = 0
    for cik10 in _g_src_issuers():
        rows = json.loads((_G_SRC / cik10 / "capture_index.json").read_text(encoding="utf-8"))
        for row in rows:
            if row["selection"] == "capture_only":
                seen_capture_only += 1
                assert row["admission"] == gsrc.CAPTURE_ONLY_ADMISSION, row["accession"]
                assert row["manifest_sha256"], row["accession"]
            else:
                assert row["selection"] == "admission_candidate", row["accession"]
                assert row["admission"] != gsrc.CAPTURE_ONLY_ADMISSION, row["accession"]
    assert seen_capture_only > 0


_AAPL_10Q = Path(__file__).resolve().parent / "fixtures" / "fundamental_forensics" / "aapl_10q_2026q3"


class _FixtureFetch:
    """Serves the committed AAPL 10-Q package bytes by archive URL (no network)."""

    def __init__(self, cik10: str, accession: str) -> None:
        self.urls: dict[str, bytes] = {
            gsrc.archive_index_url(cik10, accession): (_AAPL_10Q / "index.json").read_bytes()
        }
        for member in (_AAPL_10Q / "members").iterdir():
            self.urls[gsrc.archive_document_url(cik10, accession, member.name)] = (
                member.read_bytes()
            )

    def get(self, url: str) -> tuple[bytes, str | None]:
        return self.urls[url], None


def _capture_aapl_10q(tmp_path: Path, selection: str) -> tuple[dict, dict]:
    witness = json.loads((_AAPL_10Q / "sec_submissions_witness.json").read_text(encoding="utf-8"))
    issuer_row = _d0_issuer_rows()["AAPL"]
    cik10 = gsrc.canonical_cik(issuer_row["cik"])
    accession = witness["accessionNumber"]
    selected = gsrc.SelectedAccession(
        accession=accession,
        form=witness["form"],
        filing_date=witness["filingDate"],
        period_of_report=witness["reportDate"],
        selection=selection,
    )
    fields = {
        key: witness[key]
        for key in (
            "accessionNumber",
            "form",
            "filingDate",
            "reportDate",
            "acceptanceDateTime",
            "primaryDocument",
        )
    }
    return gsrc.capture_package(
        fetch=_FixtureFetch(cik10, accession),
        issuer_row=issuer_row,
        selected=selected,
        submissions_entry={
            "fields": fields,
            "source_url": witness["source_url"],
            "source_path": witness["source_path"],
        },
        stage_root=tmp_path / "stage",
        out_issuer_dir=tmp_path / "out",
        fixture_recorded_at="2026-10-12T00:00:00Z",
        declared_reason="not required for XBRL statement reconstruction",
    )


def test_capture_only_package_never_reaches_d1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    def _refuse_admission(**kwargs: object) -> None:
        calls.append(str(kwargs.get("capture_recorded_at")))
        raise AssertionError("D1 admission must not be attempted for a capture-only row")

    monkeypatch.setattr(gsrc, "admit_retained_filing_package", _refuse_admission)
    row, detail = _capture_aapl_10q(tmp_path, "capture_only")
    assert calls == []
    assert row["selection"] == "capture_only"
    assert row["admission"] == gsrc.CAPTURE_ONLY_ADMISSION
    assert detail["admission"] == gsrc.CAPTURE_ONLY_ADMISSION
    assert row["statement_roles_state"] == "extracted"
    manifest_path = tmp_path / "out" / row["accession"] / "package_manifest.json"
    assert hashlib.sha256(manifest_path.read_bytes()).hexdigest() == row["manifest_sha256"]


def test_admission_candidate_package_is_self_checked_by_d1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    def _record_admission(**kwargs: object) -> None:
        calls.append(str(kwargs.get("capture_recorded_at")))

    monkeypatch.setattr(gsrc, "admit_retained_filing_package", _record_admission)
    row, _detail = _capture_aapl_10q(tmp_path, "admission_candidate")
    assert calls == ["2026-10-12T00:00:00Z"]
    assert row["admission"] == "ADMITTED"


# ---------------------------------------------------------------------------
# data_gate (c2): byte-level digest re-check + re-admission over staged bytes.
# ---------------------------------------------------------------------------
# Re-derives every committed row's (manifest sha256, verdict) from the staged
# archive bytes through the real path -- statement-role classification, then
# D1 ``admit_retained_filing_package`` for extracted admission candidates --
# and asserts equality with the hermetic ``_VERDICT_PIN`` (c1) below. This is
# the check that catches verdict drift from ANY admission import. It needs the
# staged bytes, so it skips unless ``FIF_GSRC_STAGE_ROOT`` is set.


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
    readmitted: dict[str, tuple[str, str]] = {}
    for cik10 in issuers:
        capture_index = json.loads(
            (_G_SRC / cik10 / "capture_index.json").read_text(encoding="utf-8")
        )
        for row in capture_index:
            if not row.get("manifest_sha256"):
                continue
            accession = str(row["accession"])
            package_dir = stage / cik10 / accession
            manifest_bytes = (_G_SRC / cik10 / accession / "package_manifest.json").read_bytes()
            manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
            assert manifest_sha == row["manifest_sha256"], accession
            manifest = json.loads(manifest_bytes.decode("utf-8"))
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
            by_role = {
                member["role"]: member["name"]
                for member in manifest["members"]
                if member["state"] == "stored"
            }
            _roles, roles_state = gsrc.classify_statement_roles(
                members[by_role["presentation"]], members[by_role["schema"]]
            )
            assert roles_state == row["statement_roles_state"], accession
            if row["selection"] == "capture_only":
                # Retained bytes are digest-checked above; capture-only rows
                # are never admitted, so D1 is not consulted for them.
                verdict = gsrc.CAPTURE_ONLY_ADMISSION
            elif roles_state != "extracted":
                # Capture-side role refusal: D1 was never the arbiter.
                verdict = roles_state
            else:
                try:
                    admit_retained_filing_package(
                        index_bytes=index_bytes,
                        manifest=manifest,
                        members=members,
                        witness_bytes=witness_bytes,
                        capture_recorded_at=manifest["fixture_recorded_at"],
                    )
                except AdmittedFilingPackageError as exc:
                    verdict = str(exc.code)
                else:
                    verdict = "ADMITTED"
            readmitted[accession] = (manifest_sha, verdict)
    assert checked > 0
    assert readmitted == _VERDICT_PIN, _VERDICT_REPIN


# ---------------------------------------------------------------------------
# (c1) Hermetic verdict pin over the committed G-SRC table.
# ---------------------------------------------------------------------------
# Every committed capture_index row as a literal (manifest sha256, verdict),
# plus each issuer's admitted/refused tally under the capture report's own
# rule (``gsrc.admission_counts``). Hermetic and code-independent on purpose:
# a parser or admission edit never trips it. The staged-byte re-admission
# that proves these verdicts is the data_gate test (c2) above.
_VERDICT_PIN: dict[str, tuple[str, str]] = {
    "0000018230-26-000008": (
        "4739cea87815aee6ea849d5686b6d29f80288c3622c0ad44815b4acff8835278",
        "ADMITTED",
    ),
    "0000018230-25-000008": (
        "3b2eae783fc9bd4048bf8364b07cb5755d76fb26e116518b22053e55cb96ced1",
        "ADMITTED",
    ),
    "0000018230-26-000046": (
        "0007a8da08646f22132d8f653325c3686248d97b927cd795e94da966a6100832",
        "ADMITTED",
    ),
    "0000018230-26-000021": (
        "60e12190a7f6825e5898c03c99b2b8e32441bda1542951cadabbd0098e8b6d04",
        "ADMITTED",
    ),
    "0000018230-25-000040": (
        "08846e666e59d28250e15cfe6ef42cf6b9f435d4af658c2654762d5dc4a01cd4",
        "not_admitted:capture_only",
    ),
    "0000070858-26-000157": (
        "88deec70816cfcebfed5b13ba6aae010199a5c9b1a26aea5fc47853b98b6503b",
        "ADMITTED",
    ),
    "0000070858-25-000139": (
        "81e4206c6d0e179aa4ef95902b71fea0d98fb2159454b4f16a0eddac97555237",
        "ADMITTED",
    ),
    "0000070858-26-000394": (
        "7b69baf66ab6aac4f56063667deb959b38c2cf3a1a8d546a11f2c02a75a27afa",
        "ADMITTED",
    ),
    "0000070858-26-000249": (
        "de2caccf73f9952769b980ea120b58c1fb74acdbbea1579039086002e5aac73d",
        "ADMITTED",
    ),
    "0000070858-25-000268": (
        "ce90fbf6044e4a78d87699d1337166f203976b8c67d77a61ff821e39a692e138",
        "not_admitted:capture_only",
    ),
    "0001640147-26-000008": (
        "c8868c1ad12efefde1a32d4ac2ded69a106d5b7e0ad6146a53b7d36bea6752cd",
        "ADMITTED",
    ),
    "0001640147-25-000052": (
        "9cdb431b9ba8709d6e1ce5b5d1b2ff1f17d22c97c93f8eb8668894a20f2be1f0",
        "ADMITTED",
    ),
    "0001640147-26-000037": (
        "ca4ce72461ce39ad1596b55e29e44b63bef41df7397786eb86cb406f3b196cee",
        "ADMITTED",
    ),
    "0001640147-26-000030": (
        "0f7a1d1a5681d910312d26f1e4fbe5f26759e4564bd90721c77fbe2514dc8e55",
        "ADMITTED",
    ),
    "0001640147-24-000101": (
        "6cd08a7a48f61a11e79dc28a5e08c84febf41722697838a1c77ec2f65ce9e069",
        "not_admitted:capture_only",
    ),
    "0001640147-25-000187": (
        "423bbf79430bb162c9ca7678cc31cf06689bcd8ff947ba953f79645c33d17812",
        "not_admitted:capture_only",
    ),
    "0001652044-26-000018": (
        "020717667a072222c70292155eb1050377ebc7c2b75c06225494b71b77f9112e",
        "ADMITTED",
    ),
    "0001652044-25-000014": (
        "be8ea37891071eec6cf5afc68f74beacf6d7df897e0250d029a156dd22b27d46",
        "ADMITTED",
    ),
    "0001652044-26-000071": (
        "3f652297a35d6bafbf479044a0815df8752155d00fcf86c18488eb726722e892",
        "ADMITTED",
    ),
    "0001652044-26-000048": (
        "837db3ff4356a88ee6acdff8d673177af9a5be4571b53279c215ed0780397c09",
        "ADMITTED",
    ),
    "0001652044-25-000062": (
        "859847e57dfef0b7e7dc6ae3c8b376fbe9628f20963b356258108008b523ddbb",
        "not_admitted:capture_only",
    ),
}
_VERDICT_COUNTS: dict[str, dict[str, object]] = {
    "0000018230": {
        "packages": 5,
        "admitted": 4,
        "refusals": {"not_admitted": 1},
    },
    "0000070858": {
        "packages": 5,
        "admitted": 4,
        "refusals": {"not_admitted": 1},
    },
    "0001640147": {
        "packages": 6,
        "admitted": 4,
        "refusals": {"not_admitted": 2},
    },
    "0001652044": {
        "packages": 5,
        "admitted": 4,
        "refusals": {"not_admitted": 1},
    },
}
_VERDICT_REPIN = (
    "re-run `FIF_GSRC_STAGE_ROOT=<stage> python3 -m pytest -m data_gate "
    "tests/test_fif_gsrc_capture.py` where the staged bytes live, then update "
    "the moved capture_index rows, _VERDICT_PIN and _VERDICT_COUNTS in one change"
)


def _committed_g_src_rows() -> dict[str, list[dict]]:
    return {
        cik10: json.loads(
            (_G_SRC / cik10 / "capture_index.json").read_text(encoding="utf-8")
        )
        for cik10 in _g_src_issuers()
    }


def test_committed_g_src_verdicts_match_the_pin() -> None:
    got = {
        str(row["accession"]): (row["manifest_sha256"], row["admission"])
        for rows in _committed_g_src_rows().values()
        for row in rows
    }
    assert got == _VERDICT_PIN, _VERDICT_REPIN


# The classifier's closed role-refusal grammar (``classify_statement_roles``):
# one part per failing kind, in kind order, each kind at most once, joined by
# "; ". A part is ``statement_roles_missing:<kind>`` or
# ``statement_roles_ambiguous:<kind>:<title> | <title>[ | <title>...]`` with
# stripped, non-empty, single-line titles (at least two: one candidate is a
# pick, not an ambiguity).
_ROLE_KINDS = ("income_statement", "balance_sheet", "cash_flow")
_ROLE_KIND = "(income_statement|balance_sheet|cash_flow)"
_ROLE_TITLE = r"\S(?:[^\n]*?\S)?"
_ROLE_REFUSAL_PART = re.compile(
    "statement_roles_missing:" + _ROLE_KIND
    + "|statement_roles_ambiguous:" + _ROLE_KIND
    + ":" + _ROLE_TITLE + r"(?: \| " + _ROLE_TITLE + ")+"
)


def _is_typed_role_refusal(state: object) -> bool:
    if not isinstance(state, str) or not state:
        return False
    kinds: list[str] = []
    for part in re.split(r"; (?=statement_roles_(?:missing|ambiguous):)", state):
        match = _ROLE_REFUSAL_PART.fullmatch(part)
        if match is None:
            return False
        kinds.append(match.group(1) or match.group(2))
    order = [_ROLE_KINDS.index(kind) for kind in kinds]
    return order == sorted(set(order))


def test_pinned_verdicts_are_drawn_from_the_closed_typed_set() -> None:
    from engine.fundamental_forensics.admitted_filing_package import (
        AdmittedFilingPackageError,
    )

    for rows in _committed_g_src_rows().values():
        for row in rows:
            accession, verdict = row["accession"], row["admission"]
            if row["selection"] == "capture_only":
                assert verdict == gsrc.CAPTURE_ONLY_ADMISSION, accession
            elif row["statement_roles_state"] != "extracted":
                # Capture-side role refusal carries the classifier's own state,
                # which must itself parse under the closed role grammar above.
                assert _is_typed_role_refusal(row["statement_roles_state"]), accession
                assert verdict == row["statement_roles_state"], accession
            elif verdict != "ADMITTED":
                # D1's typed refusal constructor rejects any code outside its
                # closed set, so a hand-edited or stale code fails here.
                assert AdmittedFilingPackageError("pin", code=verdict).code == verdict


def test_role_refusal_grammar_admits_classifier_output_and_nothing_else() -> None:
    produced = [
        gsrc.classify_statement_roles(_syn_pre(roles), _SYN_SCHEMA)
        for roles in (
            ["r:ops", "r:ops_plain", "r:bs", "r:cf"],
            ["r:ops", "r:bs"],
            ["r:ops", "r:ops_plain", "r:bs"],
            [],
        )
    ]
    for roles, state in produced:
        assert roles is None, state
        assert _is_typed_role_refusal(state), state
    assert produced[2][1] == (
        "statement_roles_ambiguous:income_statement:"
        "Consolidated Statements of Operations | Statements of Income; "
        "statement_roles_missing:cash_flow"
    )
    for bad in (
        None,
        "",
        "extracted",
        "primary_unparseable",
        "not_admitted:capture_only",
        "statement_roles_missing:equity",
        "statement_roles_missing:cash_flow ",
        "statement_roles_missing:cash_flow; statement_roles_missing:cash_flow",
        "statement_roles_missing:cash_flow; statement_roles_missing:income_statement",
        "statement_roles_missing:balance_sheet;statement_roles_missing:cash_flow",
        "statement_roles_ambiguous:income_statement:",
        "statement_roles_ambiguous:income_statement:Statements of Income",
        "statement_roles_ambiguous:income_statement: | Statements of Income",
        "statement_roles_ambiguous:income_statement:Statements of Income | ",
        "statement_roles_ambiguous:equity:Statements of Income | Operations",
    ):
        assert not _is_typed_role_refusal(bad), bad


def test_pinned_counts_agree_with_the_capture_report_rule() -> None:
    got = {
        cik10: gsrc.admission_counts(rows)
        for cik10, rows in _committed_g_src_rows().items()
    }
    assert got == _VERDICT_COUNTS, _VERDICT_REPIN
    admitted = sum(1 for _sha, verdict in _VERDICT_PIN.values() if verdict == "ADMITTED")
    assert admitted == sum(int(c["admitted"]) for c in _VERDICT_COUNTS.values())
