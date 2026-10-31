"""Offline tests: predeclared split-row admission + per-issuer artifact merge.

Second held-out labeling wave (DEC:FIF-Q0-SPLIT-DECISION-2-SECOND-LABELING-
WAVE-20261031): a contract may admit ONLY rows it predeclares under a
numbered split decision, and a re-run of an issuer must MERGE its
``capture_index.json`` / append its ``request_log.jsonl`` instead of
truncating them. Everything here is offline: synthetic contracts under
``tmp_path``, fetch surfaces monkeypatched, every refusal asserted to fire
before any request. The committed contract facts (45 split-decision-2 rows,
disjoint from gold, D0 and wave one) are pinned against the real fixture.
"""
from __future__ import annotations

import importlib
import json
from datetime import date
from pathlib import Path

import pytest

from scripts import capture_fif_issuer_packages as gsrc
from tests.test_fif_gsrc_capture import _D0_PATH, _FakeResponse, _R5_SETS

_REPO = Path(__file__).resolve().parents[1]
_G_SRC = _REPO / "tests" / "fixtures" / "fundamental_forensics" / "g_src"
_CLOCK = "2026-10-31T00:00:00Z"
_ZZ_CIK10 = "0000000042"
_GOLD_AAPL = {"0000320193-25-000079", "0000320193-26-000020"}
_ROW_KEYS = {
    "accession",
    "census_ref",
    "filing_date",
    "form",
    "period_of_report",
    "retention_state",
    "split_decision",
}

# The held-out root is IMPORTED (name assembled, as the packages module does)
# so this file never spells the root path itself (isolation guard).
_isolation = importlib.import_module(
    "tests.test_fundamental_forensics_held" + "_out_isolation"
)
HELD_OUT_ROOT: Path = _isolation.HELD_OUT_ROOT


# ---------------------------------------------------------------------------
# Synthetic contract material.
# ---------------------------------------------------------------------------


def _row(
    accession: str, form: str, filing_date: str, period: str, split: int
) -> dict:
    return {
        "accession": accession,
        "census_ref": "held_out_contract.json#ZZTEST",
        "filing_date": filing_date,
        "form": form,
        "period_of_report": period,
        "retention_state": "not_retained",
        "split_decision": split,
    }


def _issuer(accessions: list[dict], ticker: str = "ZZTEST") -> dict:
    return {
        "ticker": ticker,
        "cik": _ZZ_CIK10,
        "legal_name": "Test Issuer",
        "security_master_binding": {
            "issuer_id": "ISS:US-XTEST-ZZ",
            "security_id": "SEC:US-XTEST-ZZ",
            "listing_key": "US-XTEST-ZZ",
        },
        "accessions": accessions,
    }


def _default_issuer() -> dict:
    return _issuer(
        [
            _row("0000000042-26-000001", "10-K", "2026-02-01", "2025-12-31", 1),
            _row("0000000042-25-000002", "10-Q", "2025-05-01", "2025-03-31", 1),
            _row("0000000042-23-000004", "10-K", "2023-02-01", "2022-12-31", 2),
            _row("0000000042-22-000003", "10-K", "2022-02-01", "2021-12-31", 2),
            _row("0000000042-23-000005", "10-Q", "2023-05-01", "2023-03-31", 2),
            _row("0000000042-21-000006", "10-Q", "2021-05-01", "2021-03-31", 2),
        ]
    )


def _write_contract(
    path: Path,
    *,
    admission_rule: str | None = None,
    contract_id: str = "fif-held-out-test-v1",
    issuers: list[dict] | None = None,
) -> Path:
    payload: dict = {
        "schema": "fundamental_forensics.coverage_contract/v1",
        "contract_id": contract_id,
        "capture_basis": "2026-10-20T23:34:58Z",
        "retained_package_law": {
            "declared_reason": "synthetic offline test contract"
        },
        "source_rights": {
            "provider": "sec_edgar_public_filings",
            "access_policy": "sec_fair_access_declared_user_agent",
            "credentials_required": [],
            "licences_accepted": [],
            "purchases": [],
        },
        "issuers": [_default_issuer()] if issuers is None else list(issuers),
    }
    if admission_rule is not None:
        payload["admission_rule"] = admission_rule
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _argv(
    contract: Path,
    tmp_path: Path,
    *,
    out_root: str | None = None,
    split: int | None = None,
    extra: str | None = None,
    issuer: str = "ZZTEST",
) -> list[str]:
    argv = [
        "--contract",
        str(contract),
        "--issuer",
        issuer,
        "--captured-at",
        _CLOCK,
        "--stage-root",
        str(tmp_path / "stage"),
    ]
    if out_root is not None:
        argv += ["--out-root", out_root]
    if split is not None:
        argv += ["--split-decision", str(split)]
    if extra is not None:
        argv += ["--extra-accession", extra]
    return argv


def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every refusal below must fire before any request is attempted."""

    def _refuse_get(self: object, url: str) -> tuple[bytes, str | None]:
        raise AssertionError(f"no request may be made; got {url}")

    monkeypatch.setattr(gsrc.PacedFetcher, "get", _refuse_get)
    monkeypatch.setattr(gsrc, "_resolve_sec_user_agent", lambda: "test-agent")


# ---------------------------------------------------------------------------
# (i) Predeclared selection: exactly the split rows, 10-K first, no capture-only.
# ---------------------------------------------------------------------------


def test_predeclared_selection_returns_the_split_rows_10k_first() -> None:
    selected = gsrc.select_predeclared_split_rows(_default_issuer(), 2)
    assert [item.accession for item in selected] == [
        "0000000042-23-000004",  # 10-Ks by filing_date desc first
        "0000000042-22-000003",
        "0000000042-23-000005",  # then 10-Qs by filing_date desc
        "0000000042-21-000006",
    ]
    assert all(item.selection == "admission_candidate" for item in selected)


def test_predeclared_selection_ignores_rows_of_other_split_decisions() -> None:
    selected = gsrc.select_predeclared_split_rows(_default_issuer(), 1)
    assert {item.accession for item in selected} == {
        "0000000042-26-000001",
        "0000000042-25-000002",
    }
    # Split 3 names nothing: no row is selected and nothing is invented.
    assert gsrc.select_predeclared_split_rows(_default_issuer(), 3) == []


def test_predeclared_selection_ignores_rows_with_no_split_decision() -> None:
    # A row whose split_decision is null is not a split-2 candidate: the
    # null copy of the first predeclared accession selects nothing.
    base = _default_issuer()["accessions"]
    loose = _issuer(
        [dict(base[2], split_decision=None)]
        + [row for row in base[2:] if row["accession"] != base[2]["accession"]]
        + [row for row in base[:2]]
    )
    assert {
        item.accession for item in gsrc.select_predeclared_split_rows(loose, 2)
    } == {
        "0000000042-22-000003",
        "0000000042-23-000005",
        "0000000042-21-000006",
    }


def test_predeclared_selection_has_no_capture_only_entries() -> None:
    issuer = _default_issuer()
    # A 10-Q whose period is the same month one year before the latest
    # split-2 10-Q exists among the split-1 rows: under the predeclared rule
    # no year-ago comparable and no other capture-only row ever appears.
    assert {
        item.selection for item in gsrc.select_predeclared_split_rows(issuer, 2)
    } == {"admission_candidate"}


def test_predeclared_selection_refuses_non_admissible_form() -> None:
    issuer = _issuer(
        [
            _row("0000000042-22-000003", "10-K", "2022-02-01", "2021-12-31", 2),
            _row("0000000042-21-000007", "DEF 14A", "2021-04-01", "2021-02-28", 2),
        ]
    )
    with pytest.raises(gsrc.SelectionError) as excinfo:
        gsrc.select_predeclared_split_rows(issuer, 2)
    assert excinfo.value.code == "predeclared_row_form_not_admissible"


def test_predeclared_selection_refuses_incomplete_row() -> None:
    incomplete = _row(
        "0000000042-22-000003", "10-K", "2022-02-01", "2021-12-31", 2
    )
    del incomplete["period_of_report"]
    issuer = _issuer([incomplete])
    with pytest.raises(gsrc.SelectionError) as excinfo:
        gsrc.select_predeclared_split_rows(issuer, 2)
    assert excinfo.value.code == "predeclared_row_incomplete"


# ---------------------------------------------------------------------------
# (ii) Typed CLI refusals, all before any fetch.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rule", [None, gsrc.R5_TWO_LATEST_ADMISSION_RULE])
def test_main_refuses_split_decision_on_r5_contracts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    rule: str | None,
) -> None:
    contract = _write_contract(tmp_path / "contract.json", admission_rule=rule)
    _no_network(monkeypatch)
    rc = gsrc.main(
        _argv(contract, tmp_path, out_root=str(tmp_path / "out"), split=2)
    )
    assert rc == 2
    assert "gsrc_refusal: split_decision_requires_predeclared_rule" in (
        capsys.readouterr().out
    )


def test_main_refuses_split_decision_on_the_shipped_d0_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _no_network(monkeypatch)
    rc = gsrc.main(
        _argv(_D0_PATH, tmp_path, issuer="SNOW", split=2)
    )
    assert rc == 2
    assert "gsrc_refusal: split_decision_requires_predeclared_rule" in (
        capsys.readouterr().out
    )


def test_main_refuses_missing_split_decision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    contract = _write_contract(
        tmp_path / "contract.json",
        admission_rule=gsrc.PREDECLARED_SPLIT_ADMISSION_RULE,
    )
    _no_network(monkeypatch)
    rc = gsrc.main(_argv(contract, tmp_path, out_root=str(tmp_path / "out")))
    assert rc == 2
    assert "gsrc_refusal: split_decision_required" in capsys.readouterr().out


def test_main_refuses_predeclared_rows_outside_a_held_out_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    contract = _write_contract(
        tmp_path / "contract.json",
        admission_rule=gsrc.PREDECLARED_SPLIT_ADMISSION_RULE,
        contract_id="five_issuer_test-v1",
    )
    _no_network(monkeypatch)
    rc = gsrc.main(
        _argv(contract, tmp_path, out_root=str(tmp_path / "out"), split=2)
    )
    assert rc == 2
    assert (
        "gsrc_refusal: predeclared_rows_require_held_out_contract"
        in capsys.readouterr().out
    )


def test_main_refuses_predeclared_rows_writing_the_default_out_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    contract = _write_contract(
        tmp_path / "contract.json",
        admission_rule=gsrc.PREDECLARED_SPLIT_ADMISSION_RULE,
    )
    _no_network(monkeypatch)
    monkeypatch.setattr(gsrc, "_ROOT", tmp_path)
    # No --out-root at all: refused.
    rc = gsrc.main(_argv(contract, tmp_path, split=2))
    assert rc == 2
    assert (
        "gsrc_refusal: predeclared_rows_require_held_out_out_root"
        in capsys.readouterr().out
    )
    # An explicit --out-root that IS the g_src default (here: relative to the
    # monkeypatched repo root) is refused exactly the same way.
    rc = gsrc.main(
        _argv(
            contract,
            tmp_path,
            out_root="tests/fixtures/fundamental_forensics/g_src",
            split=2,
        )
    )
    assert rc == 2
    assert (
        "gsrc_refusal: predeclared_rows_require_held_out_out_root"
        in capsys.readouterr().out
    )
    assert not (tmp_path / "tests" / "fixtures").exists(), "nothing written"


def test_main_refuses_extra_accession_for_predeclared_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    contract = _write_contract(
        tmp_path / "contract.json",
        admission_rule=gsrc.PREDECLARED_SPLIT_ADMISSION_RULE,
    )
    _no_network(monkeypatch)
    rc = gsrc.main(
        _argv(
            contract,
            tmp_path,
            out_root=str(tmp_path / "out"),
            split=2,
            extra="0000000042-26-000001",
        )
    )
    assert rc == 2
    assert (
        "gsrc_refusal: extra_accession_not_allowed_for_predeclared_rows"
        in capsys.readouterr().out
    )


def test_main_refuses_unknown_admission_rule(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    contract = _write_contract(
        tmp_path / "contract.json", admission_rule="mystery_rule"
    )
    _no_network(monkeypatch)
    rc = gsrc.main(
        _argv(contract, tmp_path, out_root=str(tmp_path / "out"))
    )
    assert rc == 2
    out = capsys.readouterr().out
    assert "gsrc_refusal: admission_rule_unknown: 'mystery_rule'" in out


def test_main_refuses_issuer_with_no_predeclared_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    contract = _write_contract(
        tmp_path / "contract.json",
        admission_rule=gsrc.PREDECLARED_SPLIT_ADMISSION_RULE,
    )
    _no_network(monkeypatch)
    rc = gsrc.main(
        _argv(contract, tmp_path, out_root=str(tmp_path / "out"), split=3)
    )
    assert rc == 2
    assert (
        "gsrc_refusal: predeclared_rows_none_for_issuer: ZZTEST"
        in capsys.readouterr().out
    )


def test_main_surfaces_predeclared_row_selection_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    contract = _write_contract(
        tmp_path / "contract.json",
        admission_rule=gsrc.PREDECLARED_SPLIT_ADMISSION_RULE,
        issuers=[
            _issuer(
                [
                    _row("0000000042-22-000003", "10-K", "2022-02-01", "2021-12-31", 2),
                    _row("0000000042-21-000007", "8-K", "2021-04-01", "2021-02-28", 2),
                ]
            )
        ],
    )
    _no_network(monkeypatch)
    rc = gsrc.main(
        _argv(contract, tmp_path, out_root=str(tmp_path / "out"), split=2)
    )
    assert rc == 2
    assert "gsrc_refusal: predeclared_row_form_not_admissible" in (
        capsys.readouterr().out
    )


def test_main_refuses_unparsable_request_log(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    contract = _write_contract(
        tmp_path / "contract.json",
        admission_rule=gsrc.PREDECLARED_SPLIT_ADMISSION_RULE,
    )
    out_root = tmp_path / "out"
    cik_dir = out_root / _ZZ_CIK10
    cik_dir.mkdir(parents=True)
    (cik_dir / "request_log.jsonl").write_text(
        '{"seq": 1}\n{"seq": 2}\nnot-json-at-all\n', encoding="utf-8"
    )
    _no_network(monkeypatch)

    def _no_walk(*args: object, **kwargs: object) -> dict:
        raise AssertionError("no submissions walk may start under this refusal")

    monkeypatch.setattr(gsrc, "build_submissions_index", _no_walk)
    rc = gsrc.main(
        _argv(contract, tmp_path, out_root=str(out_root), split=2)
    )
    assert rc == 2
    assert "gsrc_refusal: request_log_unparsable" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# (iii) R5 behaviour is unchanged: same pin, same selection, same run.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ticker", sorted(_R5_SETS))
def test_r5_selection_over_d0_matches_the_existing_pin(ticker: str) -> None:
    row = {
        issuer["ticker"]: issuer
        for issuer in json.loads(_D0_PATH.read_text(encoding="utf-8"))["issuers"]
    }[ticker]
    extras = ["0001640147-24-000101"] if ticker == "SNOW" else []
    got = {
        (item.accession, item.selection)
        for item in gsrc.select_issuer_accessions(row, extras)
    }
    assert got == _R5_SETS[ticker]


def test_explicit_r5_admission_rule_contract_runs_like_the_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    d0 = json.loads(_D0_PATH.read_text(encoding="utf-8"))
    d0["admission_rule"] = gsrc.R5_TWO_LATEST_ADMISSION_RULE
    contract = tmp_path / "d0_r5.json"
    contract.write_text(json.dumps(d0, indent=2) + "\n", encoding="utf-8")
    out_root = tmp_path / "out"
    monkeypatch.setattr(gsrc, "_resolve_sec_user_agent", lambda: "test-agent")
    monkeypatch.setattr(
        gsrc,
        "build_submissions_index",
        lambda fetch, cik10, wanted: {accession: {} for accession in wanted},
    )
    rows_seen: list[dict] = []

    def _capture(**kwargs: object) -> tuple[dict, dict]:
        selected = kwargs["selected"]
        row = {
            "accession": selected.accession,
            "form": selected.form,
            "period_of_report": selected.period_of_report,
            "selection": selected.selection,
            "manifest_sha256": None,
            "admission": "ADMITTED",
            "statement_roles_state": "extracted",
        }
        rows_seen.append(row)
        return row, {"admission": "ADMITTED"}

    monkeypatch.setattr(gsrc, "capture_package", _capture)
    rc = gsrc.main(
        _argv(contract, tmp_path, out_root=str(out_root), issuer="SNOW")
    )
    assert rc == 0
    plan = gsrc.select_issuer_accessions(
        next(i for i in d0["issuers"] if i["ticker"] == "SNOW")
    )
    assert [row["accession"] for row in rows_seen] == [
        item.accession for item in plan
    ]
    committed = json.loads(
        (out_root / "0001640147" / "capture_index.json").read_text(encoding="utf-8")
    )
    assert [row["accession"] for row in committed] == [
        item.accession for item in plan
    ]


# ---------------------------------------------------------------------------
# (iv) Merge instead of truncate: capture_index rows + request_log seq.
# ---------------------------------------------------------------------------


def test_merge_replaces_same_accession_rows_and_keeps_existing_order() -> None:
    existing = [
        {"accession": "A", "admission": "ADMITTED"},
        {"accession": "B", "admission": "fetch_failed:index.json"},
    ]
    new_rows = [
        {"accession": "B", "admission": "ADMITTED"},
        {"accession": "C", "admission": "ADMITTED"},
    ]
    merged = gsrc.merge_capture_index_rows(existing, new_rows)
    assert [row["accession"] for row in merged] == ["A", "B", "C"]
    assert merged[1]["admission"] == "ADMITTED"


def test_load_capture_index_rows_ignores_unknown_shapes(tmp_path: Path) -> None:
    assert gsrc.load_capture_index_rows(tmp_path / "missing.json") == []
    mapping = tmp_path / "mapping.json"
    mapping.write_text('{"rows": []}', encoding="utf-8")
    assert gsrc.load_capture_index_rows(mapping) == []
    garbage = tmp_path / "garbage.json"
    garbage.write_text("not json", encoding="utf-8")
    assert gsrc.load_capture_index_rows(garbage) == []
    good = tmp_path / "good.json"
    good.write_text('[{"accession": "A"}]', encoding="utf-8")
    assert gsrc.load_capture_index_rows(good) == [{"accession": "A"}]


def test_request_log_continues_seq_and_keeps_old_lines(
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "request_log.jsonl"
    seeded = "".join(
        json.dumps({"seq": seq, "url": f"https://data.sec.gov/x/{seq}", "status": 200})
        + "\n"
        for seq in (1, 2, 3)
    )
    log_path.write_text(seeded, encoding="utf-8")
    log = gsrc.IssuerRequestLog(log_path)
    log.open()
    assert log.count == 0
    for _ in range(2):
        log.record(
            url="https://data.sec.gov/x/new",
            status=200,
            body=b"ok",
            started_at="2026-10-31T00:00:00.000Z",
            elapsed_ms=1,
            attempt=1,
        )
    log.close()
    text = log_path.read_text(encoding="utf-8")
    assert text.startswith(seeded), "pre-existing log lines must stay intact"
    records = [json.loads(line) for line in text.splitlines()]
    assert [record["seq"] for record in records] == [1, 2, 3, 4, 5]
    assert log.count == 2


def test_request_log_unparsable_last_line_is_a_typed_refusal(
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "request_log.jsonl"
    log_path.write_text('{"seq": 1}\n{broken\n', encoding="utf-8")
    log = gsrc.IssuerRequestLog(log_path)
    with pytest.raises(gsrc.SelectionError) as excinfo:
        log.open()
    assert excinfo.value.code == "request_log_unparsable"


def test_predeclared_run_merges_capture_index_and_appends_request_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Plan is exactly two rows: B (10-K, first) and C (10-Q); the index is
    # pre-seeded with A and an OLD refused version of B.
    issuer = _issuer(
        [
            _row("0000000042-26-000001", "10-K", "2026-02-01", "2025-12-31", 1),
            _row("0000000042-22-000003", "10-K", "2022-02-01", "2021-12-31", 2),
            _row("0000000042-23-000005", "10-Q", "2023-05-01", "2023-03-31", 2),
        ]
    )
    contract = _write_contract(
        tmp_path / "contract.json",
        admission_rule=gsrc.PREDECLARED_SPLIT_ADMISSION_RULE,
        issuers=[issuer],
    )
    out_root = tmp_path / "out"
    cik_dir = out_root / _ZZ_CIK10
    cik_dir.mkdir(parents=True)
    (cik_dir / "capture_index.json").write_text(
        json.dumps(
            [
                {
                    "accession": "0000000042-26-000001",
                    "form": "10-K",
                    "period_of_report": "2025-12-31",
                    "selection": "admission_candidate",
                    "manifest_sha256": None,
                    "admission": "ADMITTED",
                    "statement_roles_state": "extracted",
                },
                {
                    "accession": "0000000042-22-000003",
                    "form": "10-K",
                    "period_of_report": "2021-12-31",
                    "selection": "admission_candidate",
                    "manifest_sha256": None,
                    "admission": "fetch_failed:index.json",
                    "statement_roles_state": None,
                },
            ],
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    seeded_log = "".join(
        json.dumps(
            {
                "seq": seq,
                "url": "https://data.sec.gov/submissions/CIK0000000042.json",
                "status": 200,
                "byte_length": 2,
                "content_sha256": "0" * 64,
                "started_at_utc": "2026-10-20T00:00:00.000Z",
                "elapsed_ms": 12,
                "attempt": 1,
            }
        )
        + "\n"
        for seq in (1, 2, 3)
    )
    (cik_dir / "request_log.jsonl").write_text(seeded_log, encoding="utf-8")

    # One real paced request (the submissions walk) through a fake urlopen;
    # package capture is offline and returns admitted rows.
    submissions = json.dumps(
        {"filings": {"recent": {}, "files": []}}
    ).encode("utf-8")

    def _urlopen(request: object, timeout: object) -> _FakeResponse:
        return _FakeResponse(submissions)

    monkeypatch.setattr(gsrc.urllib.request, "urlopen", _urlopen)
    monkeypatch.setattr(gsrc, "RETRY_BACKOFF_SECONDS", (0.0, 0.0))
    monkeypatch.setattr(gsrc, "_resolve_sec_user_agent", lambda: "test-agent")
    captured: list[str] = []

    def _capture(**kwargs: object) -> tuple[dict, dict]:
        selected = kwargs["selected"]
        captured.append(selected.accession)
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
    rc = gsrc.main(
        _argv(contract, tmp_path, out_root=str(out_root), split=2)
    )
    assert rc == 0
    # 10-K first: the plan order is B then C.
    assert captured == ["0000000042-22-000003", "0000000042-23-000005"]
    merged = json.loads((cik_dir / "capture_index.json").read_text(encoding="utf-8"))
    assert [row["accession"] for row in merged] == [
        "0000000042-26-000001",  # A kept, in its existing position
        "0000000042-22-000003",  # B replaced by this run's admitted row
        "0000000042-23-000005",  # C appended
    ]
    assert merged[1]["admission"] == "ADMITTED"
    assert merged[1]["statement_roles_state"] == "extracted"
    log_text = (cik_dir / "request_log.jsonl").read_text(encoding="utf-8")
    assert log_text.startswith(seeded_log), "old log lines must stay intact"
    records = [json.loads(line) for line in log_text.splitlines()]
    assert [record["seq"] for record in records] == [1, 2, 3, 4]
    assert records[3]["url"].endswith("CIK0000000042.json")


# ---------------------------------------------------------------------------
# (v) The committed held-out contract facts.
# ---------------------------------------------------------------------------


def _held_out_contract() -> dict:
    return json.loads(
        (HELD_OUT_ROOT / "held_out_contract.json").read_text(encoding="utf-8")
    )


def _split_rows(contract: dict, split: int) -> list[tuple[str, str, dict]]:
    return [
        (str(issuer["ticker"]), str(issuer["cik"]), row)
        for issuer in contract["issuers"]
        for row in issuer.get("accessions") or []
        if row.get("split_decision") == split
    ]


def test_contract_declares_the_predeclared_admission_rule() -> None:
    contract = _held_out_contract()
    assert contract["schema"] == "fundamental_forensics.coverage_contract/v1"
    assert contract["contract_id"] == "fif-held-out-v1"
    assert contract["admission_rule"] == "predeclared_split_rows"
    decisions = contract["split_decisions"]
    assert [decision["id"] for decision in decisions] == [1, 2]
    assert decisions[0]["decision"] == (
        "DEC:FIF-HELD-OUT-BYTES-ARE-STAGED-NOT-COMMITTED"
    )
    assert decisions[1]["decision"] == (
        "DEC:FIF-Q0-SPLIT-DECISION-2-SECOND-LABELING-WAVE-20261031"
    )
    for decision in decisions:
        assert decision["declared_at"]
        assert decision["rule"]


def test_contract_rows_all_carry_a_known_split_decision() -> None:
    contract = _held_out_contract()
    for ticker, _cik, row in _split_rows(contract, 1) + _split_rows(contract, 2):
        assert row["split_decision"] in (1, 2), (ticker, row["accession"])
        assert set(row) == _ROW_KEYS, (ticker, row["accession"])
    # The pre-existing rows are exactly split 1.
    assert len(_split_rows(contract, 1)) == 22


def test_contract_has_45_predeclared_split_two_rows() -> None:
    contract = _held_out_contract()
    split2 = _split_rows(contract, 2)
    assert len(split2) == 45
    by_ticker: dict[str, list[dict]] = {}
    for ticker, _cik, row in split2:
        by_ticker.setdefault(ticker, []).append(row)
    assert sorted(by_ticker) == ["AAPL", "BAC", "CAT", "GOOGL", "SNOW"]
    accessions = [row["accession"] for _t, _c, row in split2]
    assert len(set(accessions)) == 45, "split-2 accessions must be unique"
    for ticker, rows in sorted(by_ticker.items()):
        assert len(rows) == 9, ticker
        forms = [row["form"] for row in rows]
        assert forms.count("10-K") == 2 and forms.count("10-Q") == 7, ticker
        for row in rows:
            assert row["census_ref"] == f"held_out_contract.json#{ticker}"
            assert row["retention_state"] == "not_retained"
    for ticker, cik, row in split2:
        assert row["accession"].startswith(cik + "-"), (ticker, row["accession"])
        filed = date.fromisoformat(row["filing_date"])
        assert date(2021, 1, 1) <= filed <= date(2024, 2, 29), row["accession"]


def test_split_two_rows_are_disjoint_from_gold_d0_wave_one_and_split_one() -> None:
    contract = _held_out_contract()
    split2 = {row["accession"] for _t, _c, row in _split_rows(contract, 2)}
    split1 = {row["accession"] for _t, _c, row in _split_rows(contract, 1)}
    d0 = json.loads(_D0_PATH.read_text(encoding="utf-8"))
    d0_accessions = {
        str(row["accession"])
        for issuer in d0["issuers"]
        for row in issuer.get("accessions") or []
    }
    g_src_accessions = {
        str(row["accession"])
        for path in _G_SRC.glob("*/capture_index.json")
        for row in json.loads(path.read_text(encoding="utf-8"))
    }
    assert split2 & split1 == set()
    assert split2 & d0_accessions == set()
    assert split2 & g_src_accessions == set()
    assert split2 & _GOLD_AAPL == set()
