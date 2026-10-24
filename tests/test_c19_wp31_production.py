"""Tests for scripts/c19_wp31_production.py and scripts/c19_wp31_evaluate.py.

Every fetcher, loader, git runner and clock is injected (R2).  No network,
no real repo reads beyond ``tmp_path``, no real ledger writes.  Issuer
tickers are the non-universe ZZWP / ZZWQ where a non-universe issuer is
needed; universe tickers may appear with synthetic, invented numbers.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from scripts import c19_wp31_gates as gates
from scripts import c19_wp31_runner as runner_mod
from scripts import c19_wp31_sources as sources

UTC = timezone.utc
REPO_ROOT = Path(__file__).resolve().parents[1]
PREREG_PATH = REPO_ROOT / "research" / "C19_WP31_INCREMENTAL_INFORMATION_PREREG.md"

_NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Subprocess helper (case 2): import the module in a clean interpreter and
# verify it imports NO heavy incumbent.
# ---------------------------------------------------------------------------

def _run_banned_imports(*names: str) -> list[str]:
    code = (
        "import sys\n"
        "import scripts.c19_wp31_production as p\n"
        "banned = sorted(s for s in sys.modules if s in " + repr(list(names)) + ")\n"
        "print('banned=' + ','.join(banned))\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120,
    )
    assert out.returncode == 0, out.stderr
    last = out.stdout.strip().splitlines()[-1]
    return [x for x in last[len("banned="):].split(",") if x]


# ---------------------------------------------------------------------------
# case 1 — UNIVERSE_CIK
# ---------------------------------------------------------------------------


def test_universe_cik_keys_match_universe_and_values_are_10_digits() -> None:
    from scripts import c19_wp31_production as prod
    assert set(prod.UNIVERSE_CIK) == set(sources.UNIVERSE)
    for ticker, cik in prod.UNIVERSE_CIK.items():
        assert len(cik) == 10 and cik.isdigit(), (ticker, cik)


# ---------------------------------------------------------------------------
# case 2 — import closure
# ---------------------------------------------------------------------------


def test_importing_production_does_not_import_collectors_or_k3e() -> None:
    banned = _run_banned_imports(
        "collectors.edgar_earnings_8k",
        "collectors.edgar_8k",
        "collectors.fundamental_forensics_companyfacts",
        "scripts.query_k3e_expectation_surface",
    )
    assert banned == []


# ---------------------------------------------------------------------------
# In-memory fixtures: only the runner-side calls the module returns are tested
# ---------------------------------------------------------------------------


def _page0(ticker: str = "ZZWP", cik: int = 9999991,
           shard_names: list[str] | None = None) -> dict[str, Any]:
    recent = {
        "form": ["8-K", "10-Q"],
        "accessionNumber": ["9999991-26-000100", "9999991-26-000110"],
        "filingDate": ["2026-10-29", "2026-11-05"],
        "acceptanceDateTime": ["2026-10-30T00:05:00.000Z",
                                "2026-11-05T12:00:00.000Z"],
        "reportDate": ["2026-10-29", "2026-09-30"],
        "items": ["2.02,9.01", ""],
    }
    files = [{"name": n} for n in (shard_names or [])]
    return {"cik": str(cik), "ticker": ticker,
            "filings": {"recent": recent, "files": files}}


def _shard(name: str) -> dict[str, Any]:
    return {
        "form": ["8-K"], "accessionNumber": [f"{name.split('-')[0]}-26-999999"],
        "filingDate": ["2025-08-01"], "acceptanceDateTime": ["2025-08-01T12:00:00.000Z"],
        "reportDate": ["2025-07-30"], "items": ["2.02"],
        "_name": name,
    }


def _make_inputs(
    tmp_path: Path,
    *,
    now: datetime = _NOW,
    sec_get_json: Any = None,
    extract_8k_rows: Any = None,
    fetch_doc_text: Any = None,
    companyfacts_client: Any = None,
    k3e_load_source: Any = None,
    k3e_load_aliases: Any = None,
    git_runner: Any = None,
    sleeper: Any = None,
    pace_seconds: float = 0.0,
) -> Any:
    from scripts import c19_wp31_production as prod
    return prod.ProductionInputs(
        repo=tmp_path,
        now=now,
        sec_get_json=sec_get_json,
        extract_8k_rows=extract_8k_rows,
        fetch_doc_text=fetch_doc_text,
        companyfacts_client=companyfacts_client,
        k3e_load_source=k3e_load_source,
        k3e_load_aliases=k3e_load_aliases,
        git_runner=git_runner,
        pace_seconds=pace_seconds,
        sleeper=sleeper or (lambda _: None),
    )


def _write_minimal_repo(tmp_path: Path) -> Path:
    """Write the bare minimum so ``config.yml`` reads succeed in tests.

    ProductionInputs only reads ``config.yml`` when ``_companyfacts_client``
    is invoked without an injected client — and most tests inject one.
    The doc-bytes path (``PREREG_DOC``) is read for the gate; tests that
    exercise it stub ``run_kwargs`` directly.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    return repo


# ---------------------------------------------------------------------------
# case 3 — submissions: page0 + 2 shards; one shard raising -> pages = [page0, ok]
# ---------------------------------------------------------------------------


def test_submissions_skips_failed_shard_and_caches(tmp_path: Path) -> None:
    repo = _write_minimal_repo(tmp_path)
    page0 = _page0(shard_names=["a.json", "b.json", "c.json"])
    shard_a = _shard("a.json")
    shard_c = _shard("c.json")

    def sec(url: str) -> Any:
        if url.endswith("/submissions/CIK0000320193.json") or url.endswith("/submissions/CIK9999991.json"):
            return dict(page0)
        if url.endswith("/a.json") or "submissions/a.json" in url:
            return dict(shard_a)
        if url.endswith("/b.json") or "submissions/b.json" in url:
            raise RuntimeError("simulated shard failure")
        if url.endswith("/c.json") or "submissions/c.json" in url:
            return dict(shard_c)
        return None

    inputs = _make_inputs(tmp_path=repo, sec_get_json=sec,
                          extract_8k_rows=lambda t, c, rec: [
                                  {"ticker": t, "cik": c,
                                   "accession": "9-1", "form": f,
                                   "filing_date": "2026-10-29",
                                   "acceptance_datetime": "2026-10-30T00:05Z",
                                   "report_date": r, "items": i}
                                  for f, r, i in [("8-K", "2026-10-29", "2.02")]],
                          pace_seconds=0.0)
    pages = inputs.submissions_pages("AAPL")
    # page0 + 2 successful shards (b failed -> not in pages)
    assert len(pages) == 3
    assert pages[0]["filings"]["recent"]["form"][0] == "8-K"
    assert inputs.counts["submissions_shards_missing"] == 1
    # 1 page0 + 2 successful shard requests (a + c); the failed b is not
    # counted as a request, only as a missing shard.
    assert inputs.counts["submissions_requests"] == 3
    # Cache: repeated calls don't re-fetch.
    before = inputs.counts["submissions_requests"]
    pages2 = inputs.submissions_pages("AAPL")
    assert len(pages2) == len(pages)
    assert inputs.counts["submissions_requests"] == before


# ---------------------------------------------------------------------------
# case 4 — page0 raising
# ---------------------------------------------------------------------------


def test_submissions_handles_page0_failure(tmp_path: Path) -> None:
    repo = _write_minimal_repo(tmp_path)

    def sec(url: str) -> Any:
        raise RuntimeError("page0 fetch failed")

    inputs = _make_inputs(tmp_path=repo, sec_get_json=sec,
                          extract_8k_rows=lambda t, c, rec: [])
    pages = inputs.submissions_pages("AAPL")
    assert pages == ()
    assert inputs.counts["submissions_unavailable"] == 1
    # filing_rows for AAPL -> no rows
    rows = inputs.filing_rows()
    assert rows == []


# ---------------------------------------------------------------------------
# case 5 — fetch_index_headers: dashed and nodash produce the same call
# ---------------------------------------------------------------------------


def test_fetch_index_headers_normalizes_and_handles_none(tmp_path: Path) -> None:
    repo = _write_minimal_repo(tmp_path)
    calls: list[tuple[int, str, str, bool]] = []

    def fetch(cik: int, nodash: str, filename: str, *,
              pace_s: float = 0.0, strip: bool = True,
              max_bytes: int | None = None, stats: Any = None) -> str | None:
        calls.append((int(cik), nodash, filename, strip))
        return "<DOCUMENT>\n<TYPE>EX-99.1</TYPE>\n<FILENAME>ex991.htm</FILENAME>\n"

    inputs = _make_inputs(tmp_path=repo, fetch_doc_text=fetch, pace_seconds=0.0)

    # Dashed accession.
    a = inputs.fetch_index_headers(9999991, "0009999991-26-000100")
    # Nodash accession (different surface; should map to the same URL).
    b = inputs.fetch_index_headers(9999991, "000999999126000100")
    assert a is not None and b is not None
    # Same call shape: same nodash, same dashed-10-2-6 filename, strip=False
    assert len(calls) == 2
    assert calls[0][1] == calls[1][1]
    assert calls[0][2] == calls[1][2] == "0009999991-26-000100-index-headers.html"
    assert calls[0][3] is False and calls[1][3] is False

    # Exception -> None
    def boom(*args: Any, **kw: Any) -> None:
        raise RuntimeError("net")
    inputs2 = _make_inputs(tmp_path=repo, fetch_doc_text=boom, pace_seconds=0.0)
    assert inputs2.fetch_index_headers(9999991, "0009999991-26-000100") is None


# ---------------------------------------------------------------------------
# case 6 — companyfacts
# ---------------------------------------------------------------------------


def test_companyfacts_parses_bytes_and_handles_errors(tmp_path: Path) -> None:
    repo = _write_minimal_repo(tmp_path)

    class _ErrCls:
        pass

    class _GoodClient:
        def fetch(self, cik: Any, *, max_response_bytes: int) -> tuple[bytes, dict]:
            return (json.dumps({"facts": {"us-gaap": {"x": 1}}}).encode(), {})

    class _ErrClient(_ErrCls):
        def fetch(self, cik: Any, *, max_response_bytes: int) -> tuple[bytes, dict]:
            from collectors.fundamental_forensics_companyfacts import (
                CompanyFactsAcquisitionError,
            )
            raise CompanyFactsAcquisitionError("bad")

    class _BadJsonClient(_ErrCls):
        def fetch(self, cik: Any, *, max_response_bytes: int) -> tuple[bytes, dict]:
            return (b"{not json", {})

    inputs = _make_inputs(tmp_path=repo, companyfacts_client=_GoodClient(), pace_seconds=0.0)
    assert inputs.companyfacts("AAPL") == {"facts": {"us-gaap": {"x": 1}}}

    inputs2 = _make_inputs(tmp_path=repo, companyfacts_client=_ErrClient(), pace_seconds=0.0)
    assert inputs2.companyfacts("AAPL") is None
    assert inputs2.counts["companyfacts_unavailable"] == 1

    inputs3 = _make_inputs(tmp_path=repo, companyfacts_client=_BadJsonClient(), pace_seconds=0.0)
    assert inputs3.companyfacts("AAPL") is None
    assert inputs3.counts["companyfacts_unavailable"] == 1


# ---------------------------------------------------------------------------
# case 7 — k_inputs
# ---------------------------------------------------------------------------


def test_k_inputs_loaded_once_and_handles_loader_failure(tmp_path: Path) -> None:
    repo = _write_minimal_repo(tmp_path)
    src_calls: list[tuple[Any, str]] = []
    alias_calls: list[tuple[Any, str]] = []

    def good_source(repository: Any, revision: str) -> tuple[list, list, dict]:
        src_calls.append((repository, revision))
        return ([{"a": 1}], [{"b": 2}], {"source_revision": revision})

    def good_aliases(repository: Any, revision: str) -> tuple[list, dict]:
        alias_calls.append((repository, revision))
        return ([{"alias": 1}], {})  # no absent_at_revision

    def failing_source(repository: Any, revision: str) -> tuple:
        raise RuntimeError("loader failure")

    def git_run(args: list[str]) -> Any:
        class _R:
            stdout = b"a" * 40
            stderr = b""
            returncode = 0
        return _R()

    inputs = _make_inputs(tmp_path=repo, k3e_load_source=good_source,
                          k3e_load_aliases=good_aliases, git_runner=git_run,
                          pace_seconds=0.0)
    out_a = inputs.k_inputs("AAPL", _NOW, "2026-09-30")
    out_b = inputs.k_inputs("AAPL", _NOW, "2026-09-30")
    out_c = inputs.k_inputs("DHI", _NOW, "2026-09-30")
    # Loader called once across many calls.
    assert len(src_calls) == 1 and len(alias_calls) == 1
    # The two calls return identical content (one loader invocation cached).
    assert out_a == out_b
    # aliases are passed (no absent_at_revision)
    assert out_a["identity_aliases"] == [{"alias": 1}]
    assert out_a["ticker"] == "AAPL"
    assert out_c["ticker"] == "DHI"

    # Loader raising -> None for every call.
    inputs2 = _make_inputs(tmp_path=repo, k3e_load_source=failing_source,
                           k3e_load_aliases=good_aliases, git_runner=git_run,
                           pace_seconds=0.0)
    assert inputs2.k_inputs("AAPL", _NOW, "2026-09-30") is None
    assert inputs2.k_inputs("DHI", _NOW, "2026-09-30") is None
    assert inputs2.counts["k_inputs_unavailable"] >= 1


def test_k_inputs_omits_aliases_when_absent_at_revision(tmp_path: Path) -> None:
    repo = _write_minimal_repo(tmp_path)

    def good_source(repository: Any, revision: str) -> tuple[list, list, dict]:
        return ([], [], {"source_revision": revision})

    def good_aliases(repository: Any, revision: str) -> tuple[list, dict]:
        return ([], {"absent_at_revision": True})

    def git_run(args: list[str]) -> Any:
        class _R:
            stdout = b"b" * 40
            stderr = b""
            returncode = 0
        return _R()

    inputs = _make_inputs(tmp_path=repo, k3e_load_source=good_source,
                          k3e_load_aliases=good_aliases, git_runner=git_run,
                          pace_seconds=0.0)
    out = inputs.k_inputs("AAPL", _NOW, "2026-09-30")
    assert out is not None and "identity_aliases" not in out


# ---------------------------------------------------------------------------
# case 8 — is_ancestor_of_head
# ---------------------------------------------------------------------------


def test_is_ancestor_of_head_rc_0_1_128(tmp_path: Path) -> None:
    """rc 0 -> True, rc 1 -> False, rc 128 (or anything else) -> raise."""
    repo = _write_minimal_repo(tmp_path)

    def make_git_runner(rc_value: int) -> Any:
        def _runner(args: list[str]) -> Any:
            class _R:
                stdout = b""
                stderr = b""
                returncode = rc_value
            return _R()
        return _runner

    # rc 0 -> True
    inputs_ok = _make_inputs(tmp_path=repo,
                             git_runner=make_git_runner(0), pace_seconds=0.0)
    assert inputs_ok.is_ancestor_of_head("a" * 40) is True

    # rc 1 -> False
    inputs_no = _make_inputs(tmp_path=repo,
                             git_runner=make_git_runner(1), pace_seconds=0.0)
    assert inputs_no.is_ancestor_of_head("a" * 40) is False

    # rc 128 -> raises (gates.check_merged_ancestry then refuses fail-closed)
    inputs_bad = _make_inputs(tmp_path=repo,
                              git_runner=make_git_runner(128), pace_seconds=0.0)
    with pytest.raises(RuntimeError):
        inputs_bad.is_ancestor_of_head("a" * 40)


# ---------------------------------------------------------------------------
# case 9 — head_revision non-hex -> ValueError
# ---------------------------------------------------------------------------


def test_head_revision_non_hex_raises_value_error(tmp_path: Path) -> None:
    repo = _write_minimal_repo(tmp_path)

    def git_run(args: list[str]) -> Any:
        class _R:
            stdout = b"NOTHEX!"
            stderr = b""
            returncode = 0
        return _R()

    inputs = _make_inputs(tmp_path=repo, git_runner=git_run, pace_seconds=0.0)
    with pytest.raises(ValueError):
        inputs.head_revision()


# ---------------------------------------------------------------------------
# case 10 — CLI end-to-end: episodes with sentinel string not in out/stdout
# ---------------------------------------------------------------------------


def _build_inputs_with_repo(tmp_path: Path) -> tuple[Any, Path, Path]:
    """Build a ProductionInputs whose doc_bytes/ledger/filesystem are stubbed.

    We do NOT read the real ``config.yml`` — every load is stubbed via the
    constructor so the test is hermetic.  The fake repo carries a COPY of
    the real prereg so the gate's doc-hash check passes (its read_bytes
    is overridden to return the live one in the per-run kwargs anyway).
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    research = repo / "research"
    research.mkdir()
    (research / "C19_WP31_INCREMENTAL_INFORMATION_PREREG.md").write_bytes(
        PREREG_PATH.read_bytes()
    )
    # Stub all incumbents.
    sec_calls: list[str] = []

    def sec(url: str) -> Any:
        sec_calls.append(url)
        return None  # no submissions — episodes empty

    extract = lambda t, c, rec: []  # noqa: E731

    fetch = lambda *a, **kw: None  # noqa: E731

    class _GoodClient:
        def fetch(self, cik: Any, *, max_response_bytes: int) -> tuple[bytes, dict]:
            return (b"{}", {})

    def source(repository: Any, revision: str) -> tuple[list, list, dict]:
        return ([], [], {"source_revision": revision})

    def aliases(repository: Any, revision: str) -> tuple[list, dict]:
        return ([], {"absent_at_revision": True})

    def git_run(args: list[str]) -> Any:
        class _R:
            stdout = b"a" * 40
            stderr = b""
            returncode = 0
        return _R()

    inputs = _make_inputs(
        tmp_path=repo, sec_get_json=sec, extract_8k_rows=extract,
        fetch_doc_text=fetch, companyfacts_client=_GoodClient(),
        k3e_load_source=source, k3e_load_aliases=aliases,
        git_runner=git_run, pace_seconds=0.0,
    )
    # Override doc_bytes (returns the real prereg so gates pass) and
    # ledger_lines (returns a synthetic declared_budget row).
    inputs.doc_bytes = lambda: PREREG_PATH.read_bytes()  # type: ignore[assignment]
    inputs.ledger_lines = lambda: [json.dumps({  # type: ignore[assignment]
        "kind": "declared_budget", "family": gates.FAMILY, "n": gates.BUDGET,
        "reason": gates.registration_reason(), "config_hash": "deadbeef",
    })]
    return inputs, repo, tmp_path


def test_cli_end_to_end_never_writes_or_prints_sentinel(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    inputs, repo, out_root = _build_inputs_with_repo(tmp_path)
    exposure = out_root / "exposure.jsonl"
    out = out_root / "report.json"

    sentinel = "ZZ_SENTINEL_LABEL"
    fake_result = {
        "gates": [{"gate": "G-1", "detail": "ok"}],
        "report": {
            "eligible": 0, "exposed": 0, "not_evaluable": {},
            "arms": {}, "n_common_support": 0, "n_clusters": 0,
            "delta": 0, "delta_exact": "0/0",
            "interval": [0.0, 0.0],
            "discordant": {"a2_right_minus_k_wrong": 0, "k_right_minus_a2_wrong": 0},
            "verdict": "MONITORING", "verdict_reason": "",
            "look": "monitoring", "study_stopped": False,
            "secondaries": {}, "splits": {}, "costs": {},
            "family": gates.FAMILY, "budget": gates.BUDGET,
        },
        "label_pending": 0,
        "exhibit_failures": [],
        "episode_count": 1,
        "episodes": [
            {"issuer": "ZZWP", "q": "2026Q3", "label": sentinel,
             "status": "ELIGIBLE", "period_end": "2026-09-30"}
        ],
    }

    monkeypatch.setattr(runner_mod, "run_evaluation", lambda **kw: fake_result)
    monkeypatch.setattr("scripts.c19_wp31_runner.run_evaluation", lambda **kw: fake_result)

    from scripts import c19_wp31_evaluate as cli
    rc = cli.main([
        "--repo", str(repo),
        "--exposure-path", str(exposure),
        "--out", str(out),
        "--now", "2026-10-30T12:00:00Z",
    ])
    assert rc == 0

    # Atomic write: out file exists, no leftover .tmp in the same dir.
    assert out.exists()
    leftover = list(out.parent.glob(".c19-wp31-*.json.tmp"))
    assert leftover == [], leftover
    payload = json.loads(out.read_text())
    assert "episodes" not in payload
    assert sentinel not in out.read_text()


def test_cli_capture_stdout_never_contains_sentinel(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    inputs, repo, out_root = _build_inputs_with_repo(tmp_path)
    exposure = out_root / "exposure.jsonl"
    out = out_root / "report.json"
    sentinel = "ZZ_SENTINEL_LABEL"
    fake_result = {
        "gates": [{"gate": "G-1", "detail": "ok"}],
        "report": {"eligible": 0, "exposed": 0, "not_evaluable": {},
                   "arms": {}, "n_common_support": 0, "n_clusters": 0,
                   "delta": 0, "delta_exact": "0/0",
                   "interval": [0.0, 0.0],
                   "discordant": {"a2_right_minus_k_wrong": 0,
                                 "k_right_minus_a2_wrong": 0},
                   "verdict": "MONITORING", "verdict_reason": "",
                   "look": "monitoring", "study_stopped": False,
                   "secondaries": {}, "splits": {}, "costs": {},
                   "family": gates.FAMILY, "budget": gates.BUDGET},
        "label_pending": 0,
        "exhibit_failures": [],
        "episode_count": 0,
        "episodes": [],
    }
    monkeypatch.setattr(runner_mod, "run_evaluation", lambda **kw: fake_result)
    monkeypatch.setattr("scripts.c19_wp31_runner.run_evaluation", lambda **kw: fake_result)

    from scripts import c19_wp31_evaluate as cli
    cli.main([
        "--repo", str(repo),
        "--exposure-path", str(exposure),
        "--out", str(out),
        "--now", "2026-10-30T12:00:00Z",
    ])
    captured = capsys.readouterr()
    assert sentinel not in captured.out
    assert sentinel not in captured.err


# ---------------------------------------------------------------------------
# case 11 — CLI lock: hold flock -> exit 3
# ---------------------------------------------------------------------------


def test_cli_lock_busy_exits_with_code_3(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    exposure = tmp_path / "exposure.jsonl"
    out = tmp_path / "report.json"

    # Hold the lock in this process so the CLI's LOCK_EX|LOCK_NB fails.
    import fcntl as _fcntl
    lock_path = Path(str(exposure) + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    held = lock_path.open("w", encoding="utf-8")
    try:
        _fcntl.flock(held.fileno(), _fcntl.LOCK_EX | _fcntl.LOCK_NB)

        from scripts import c19_wp31_evaluate as cli
        rc = cli.main([
            "--repo", str(repo),
            "--exposure-path", str(exposure),
            "--out", str(out),
            "--now", "2026-10-30T12:00:00Z",
        ])
        assert rc == 3
        captured = capsys.readouterr()
        assert "busy" in captured.err.lower()
    finally:
        _fcntl.flock(held.fileno(), _fcntl.LOCK_UN)
        held.close()

    # out file not written when busy.
    assert not out.exists()


# ---------------------------------------------------------------------------
# case 12 — CLI refusal: WP31Refusal -> exit 2, out not written
# ---------------------------------------------------------------------------


def test_cli_refusal_exits_with_code_2_and_does_not_write(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    research = repo / "research"
    research.mkdir()
    (research / "C19_WP31_INCREMENTAL_INFORMATION_PREREG.md").write_bytes(
        PREREG_PATH.read_bytes()
    )
    exposure = tmp_path / "exposure.jsonl"
    out = tmp_path / "report.json"

    def boom(**kw: Any) -> Any:
        raise gates.WP31Refusal("G-1", "wrong sha")

    monkeypatch.setattr(runner_mod, "run_evaluation", boom)
    monkeypatch.setattr("scripts.c19_wp31_runner.run_evaluation", boom)

    from scripts import c19_wp31_evaluate as cli
    rc = cli.main([
        "--repo", str(repo),
        "--exposure-path", str(exposure),
        "--out", str(out),
        "--now", "2026-10-30T12:00:00Z",
    ])
    assert rc == 2
    captured = capsys.readouterr()
    assert "refused" in captured.err.lower()
    assert not out.exists()


# ---------------------------------------------------------------------------
# extra: ProductionInputs constructor — naive now -> ValueError
# ---------------------------------------------------------------------------


def test_naive_now_raises_value_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        _make_inputs(tmp_path=tmp_path, now=datetime(2026, 10, 30, 12, 0))