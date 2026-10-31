"""Tests for scripts/c19_wp31_runner.py — the C19 WP31 injected-I/O runner.

Every reader, fetcher, clock and ledger is injected (lane law R2): no network,
no production reader call, no file under data/.  The exposure ledger lives on
``pytest tmp_path``.  Fixtures are SYNTHETIC except G-1, which reads only the
frozen prereg markdown (a document read, not label data — the same precedent
as tests/test_c19_wp31_gates.py).  Issuer tickers are the non-universe ZZWP /
ZZWQ, monkeypatched into ``sources.UNIVERSE``; every EPS number below is
invented.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from scripts import c19_wp31_gates as gates
from scripts import c19_wp31_runner as runner
from scripts import c19_wp31_sources as sources

UTC = timezone.utc
REPO_ROOT = Path(__file__).resolve().parents[1]
PREREG_PATH = REPO_ROOT / "research" / "C19_WP31_INCREMENTAL_INFORMATION_PREREG.md"

_NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)  # within 120d of the period end
_UNIVERSE = {
    **sources.UNIVERSE,
    "ZZWP": ("ZZCLUSTER", 12),  # FYE December -> 2026-10-29 anchors 2026Q3
    "ZZWQ": ("ZZCLUSTER", 12),
    "ZWSX": ("ZZCLUSTER", 12),
}
_Q_ACCESSION = "0009999991-26-000900"


# ---------------------------------------------------------------------------
# Injected fakes
# ---------------------------------------------------------------------------


class _Resolution:
    def __init__(self, company_id: str) -> None:
        self.company_id = company_id


def _resolver(table: dict[str, str] | None = None) -> Any:
    table = table or {"ZZWP": "cik:0009999991", "ZZWQ": "cik:0009999992"}
    calls: list[tuple[str, date]] = []

    def resolve(ticker: str, *, asof: date) -> Any:
        calls.append((ticker, asof))
        company_id = table.get(ticker)
        return _Resolution(company_id) if company_id else None

    resolve.calls = calls
    return resolve


def _revisions_reader(qm1: list[dict] | None = None,
                      q: list[dict] | None = None,
                      *, fail: Exception | None = None) -> Any:
    """A counting fake: returns empty chains, or the given q-1/q revisions."""
    calls: list[list[str]] = []

    def reader(event_ids: list[str], *, max_hops: int = 500) -> dict:
        calls.append(list(event_ids))
        if fail is not None:
            raise fail
        out: dict[str, list[dict]] = {event_id: [] for event_id in event_ids}
        for event_id in event_ids:
            if qm1 is not None and _is_qm1(event_id):
                out[event_id] = list(qm1)
            if q is not None and _is_q(event_id):
                out[event_id] = list(q)
        return out

    reader.calls = calls
    return reader


def _is_qm1(event_id: str) -> bool:
    return event_id.endswith("2026q2_results")


def _is_q(event_id: str) -> bool:
    return event_id.endswith("2026q3_results")


def _rev(gen: str, *, lifecycle: str = "complete",
         generated_at: str = "2026-10-27T12:00:00Z",
         source_available_at: str | None = None) -> dict:
    return {
        "generation_id": gen,
        "source_sha256": "b" * 64,
        "source_available_at": source_available_at,
        "observed_at": None,
        "lifecycle_state": lifecycle,
        "workspace_receipt": {"sha256": f"rcpt-{gen}", "bytes": 128},
        "workspace": {"generated_at": generated_at},
    }


def _index_headers(calls: list[tuple[Any, Any]] | None = None) -> Any:
    def fetch(cik: Any, accession: Any) -> str:
        if calls is not None:
            calls.append((cik, accession))
        # escaped SGML, exactly as the live EDGAR page serves it
        return ("&lt;DOCUMENT&gt;\n&lt;TYPE&gt;8-K&lt;/TYPE&gt;\n"
                "&lt;FILENAME&gt;8k.htm&lt;/FILENAME&gt;\n"
                "&lt;DOCUMENT&gt;\n&lt;TYPE&gt;EX-99.1&lt;/TYPE&gt;\n"
                "&lt;FILENAME&gt;ex991.htm&lt;/FILENAME&gt;\n")

    return fetch


def _facts(with_comparative: bool = True) -> dict:
    rows = [{"start": "2026-07-01", "end": "2026-09-30", "val": 2.50,
             "accn": _Q_ACCESSION, "form": "10-Q", "filed": "2026-10-30"}]
    if with_comparative:
        rows.append({"start": "2025-07-01", "end": "2025-09-30", "val": 2.00,
                     "accn": _Q_ACCESSION, "form": "10-Q", "filed": "2025-10-30"})
    return {"facts": {"us-gaap": {"EarningsPerShareDiluted":
                                  {"units": {"USD/shares": rows}}}}}


def _ledger_lines() -> list[str]:
    other = json.dumps({"family": "commodity_tsmom", "config_hash": "cafe",
                        "config": {"window": 63}})
    row = json.dumps({"kind": "declared_budget", "family": gates.FAMILY,
                      "n": gates.BUDGET, "reason": gates.registration_reason(),
                      "config_hash": "deadbeef"})
    return [other, row]


def _row(acc: str, ticker: str = "ZZWP", *, cik: int = 9999991) -> dict:
    # raw submissions-JSON clock: 2026-10-30T00:05 "Z" is 2026-10-29T20:05Z true
    return {"ticker": ticker, "cik": cik, "accession": acc, "form": "8-K",
            "filing_date": "2026-10-29",
            "acceptance_datetime": "2026-10-30T00:05:00.000Z",
            "report_date": "2026-10-29", "items": "2.02,9.01"}


def _run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    rows: list[dict] | None = None,
    now: datetime = _NOW,
    facts: Any = "factory",
    revisions: Any = "factory",
    k_inputs: Any = None,
    companyfacts: Any = None,
    submissions_pages: Any = None,
    doc_bytes: bytes | None = None,
) -> dict:
    monkeypatch.setattr(sources, "UNIVERSE", _UNIVERSE)
    exposure = tmp_path / "exposure" / "ledger.jsonl"
    if facts == "factory":
        facts = lambda issuer: _facts()  # noqa: E731
    if revisions == "factory":
        revisions = _revisions_reader(qm1=[_rev("gen-ok")])
    if k_inputs is None:
        k_inputs = lambda issuer, cutoff, period_end: None  # noqa: E731
    if companyfacts is None:
        companyfacts = facts
    if submissions_pages is None:
        submissions_pages = lambda issuer: ()  # noqa: E731
    return runner.run_evaluation(
        doc_bytes=PREREG_PATH.read_bytes() if doc_bytes is None else doc_bytes,
        is_ancestor_of_head=lambda sha: True,
        ledger_lines=_ledger_lines(),
        filing_rows=rows if rows is not None else [_row(_Q_ACCESSION)],
        fetch_index_headers=_index_headers(),
        k_inputs=k_inputs,
        companyfacts=companyfacts,
        submissions_pages=submissions_pages,
        exposure_path=exposure,
        now=now,
        resolve_ticker=_resolver(),
        revisions_reader=revisions,
    )


# ---------------------------------------------------------------------------
# gates
# ---------------------------------------------------------------------------


def test_runner_gates_refusal_propagates_and_no_reader_is_called(
        monkeypatch, tmp_path) -> None:
    revisions = _revisions_reader(qm1=[_rev("gen-ok")])
    monkeypatch.setattr(sources, "UNIVERSE", _UNIVERSE)
    with pytest.raises(gates.WP31Refusal) as excinfo:
        runner.run_evaluation(
            doc_bytes=b"not the prereg",  # G-1 refuses: wrong document bytes
            is_ancestor_of_head=lambda sha: True,
            ledger_lines=_ledger_lines(),
            filing_rows=[_row(_Q_ACCESSION)],
            fetch_index_headers=_index_headers(),
            k_inputs=lambda issuer, cutoff, period_end: None,
            companyfacts=lambda issuer: _facts(),
            submissions_pages=lambda issuer: (),
            exposure_path=tmp_path / "exposure.jsonl",
            now=_NOW,
            resolve_ticker=_resolver(),
            revisions_reader=revisions,
        )
    assert excinfo.value.gate == "G-1"
    assert revisions.calls == []  # no read happens without all three gates


# ---------------------------------------------------------------------------
# end-to-end reads over synthetic ZZWP/ZZWQ episodes
# ---------------------------------------------------------------------------


def test_runner_end_to_end_report_keys_present(monkeypatch, tmp_path) -> None:
    result = _run(monkeypatch, tmp_path, rows=[_row(_Q_ACCESSION),
                                               _row("0009999991-26-000901",
                                                    ticker="ZZWQ", cik=9999992)])
    assert set(result) == {"gates", "report", "label_pending", "exhibit_failures",
                           "episode_count", "episodes"}
    assert [r["gate"] for r in result["gates"]] == ["G-1", "G-2", "G-3"]
    assert result["episode_count"] == 2
    assert result["label_pending"] == 0
    assert result["exhibit_failures"] == []
    report = result["report"]
    for key in ("eligible", "exposed", "not_evaluable", "arms",
                "n_common_support", "n_clusters", "delta", "delta_exact",
                "interval", "discordant", "verdict", "verdict_reason", "look",
                "study_stopped", "secondaries", "splits", "costs", "family",
                "budget"):
        assert key in report, key
    assert report["eligible"] == 2
    # two episodes: the adjudication minimum is nowhere near met, so the read
    # is descriptive monitoring, never an adjudicating look (prereg §5)
    assert report["verdict"] == "MONITORING"
    assert report["look"] == "monitoring"
    for ep in result["episodes"]:
        assert ep["status"] == "ELIGIBLE"
        assert ep["label"] == 1  # synthetic 2.50 vs 2.00
        assert ep["s"]["q_minus_1_resolved"] is True
        assert ep["k"]["abstain_reason"] == "k_inputs_unavailable"


def test_runner_records_label_read_when_any_q_filing_matches(
        monkeypatch, tmp_path) -> None:
    """Wave-3 spec §3: the evaluator label read is recorded whenever the facts
    JSON holds at least one original-filing EPS context for the episode period
    (one OR several matches).  Zero matches -> no record (no label value
    exists to read).  The label itself still requires a single match, so the
    two-match episode stays label=None / not evaluable.
    """
    exposure = tmp_path / "exposure.jsonl"
    monkeypatch.setattr(sources, "UNIVERSE", _UNIVERSE)
    # Two ORIGINAL accessions (10-Q + 10-Q — never amendments) whose max end
    # == 2026-09-30 (the episode period end).  An ambiguous set is refused by
    # the label reader — the label stays None — but the exposure ledger is
    # still written: the facts JSON is in memory either way (prereg §6), so
    # recording is the more conservative choice and needs no amendment.
    two_match_facts = {"facts": {"us-gaap": {"EarningsPerShareDiluted": {
        "units": {"USD/shares": [
            {"start": "2026-07-01", "end": "2026-09-30", "val": 2.50,
             "accn": _Q_ACCESSION, "form": "10-Q", "filed": "2026-10-30"},
            {"start": "2026-07-01", "end": "2026-09-30", "val": 2.55,
             "accn": "0009999991-26-000800", "form": "10-Q",
             "filed": "2026-11-05"},
            {"start": "2025-07-01", "end": "2025-09-30", "val": 2.00,
             "accn": _Q_ACCESSION, "form": "10-Q", "filed": "2025-10-30"},
        ]}}}},
    }
    facts_by_issuer = {
        "ZZWP": _facts(),        # one match: the 2026Q3 filing
        "ZZWQ": {"facts": {"us-gaap": {"EarningsPerShareDiluted": {
            "units": {"USD/shares": [
                # zero matches: a quarter that does NOT match the episode
                # period end (2026-06-30 vs 2026-09-30).
                {"start": "2026-04-01", "end": "2026-06-30", "val": 1.10,
                 "accn": "0009999992-26-000700", "form": "10-Q",
                 "filed": "2026-07-30"}]}}}},
        },
        "ZWSX": two_match_facts,  # two matches for 2026Q3 -> recorded, label None
    }
    result = runner.run_evaluation(
        doc_bytes=PREREG_PATH.read_bytes(),
        is_ancestor_of_head=lambda sha: True,
        ledger_lines=_ledger_lines(),
        filing_rows=[_row(_Q_ACCESSION),
                     _row("0009999992-26-000701", ticker="ZZWQ", cik=9999992),
                     _row("0009999991-26-000801", ticker="ZWSX", cik=9999991)],
        fetch_index_headers=_index_headers(),
        k_inputs=lambda issuer, cutoff, period_end: None,
        companyfacts=lambda issuer: facts_by_issuer.get(issuer),
        submissions_pages=lambda issuer: (),
        exposure_path=exposure,
        now=_NOW,
        resolve_ticker=lambda ticker, *, asof: (
            _Resolution("cik:0009999991") if ticker in {"ZZWP", "ZWSX"}
            else _Resolution("cik:0009999992")
        ),
        revisions_reader=_revisions_reader(qm1=[_rev("gen-ok")]),
    )
    rows = [json.loads(line) for line in exposure.read_text().splitlines()]
    recorded = sorted(row["issuer"] for row in rows)
    # ZZWQ: zero matches -> no record; ZZWP + ZWSX: at least one -> recorded.
    assert recorded == ["ZWSX", "ZZWP"]
    assert {row["reader"] for row in rows} == {gates.EVALUATOR_READER}
    # zero matches: label stays None and a0 still computed through the same function
    zzwq = next(ep for ep in result["episodes"] if ep["issuer"] == "ZZWQ")
    assert zzwq["label"] is None
    assert set(zzwq["a0"]) == {"sign", "period", "accession", "accepted_at"}
    # two matches: label stays None (ambiguous set refused by the label reader)
    zwsx = next(ep for ep in result["episodes"] if ep["issuer"] == "ZWSX")
    assert zwsx["label"] is None
    assert set(zwsx["a0"]) == {"sign", "period", "accession", "accepted_at"}


def test_runner_pre_existing_read_exposes_episode(monkeypatch, tmp_path) -> None:
    exposure = tmp_path / "exposure.jsonl"
    gates.record_label_read(exposure, "ZZWP", "2026Q3", "rogue-human-reader",
                            "2026-10-19T09:00:00Z")
    monkeypatch.setattr(sources, "UNIVERSE", _UNIVERSE)
    result = runner.run_evaluation(
        doc_bytes=PREREG_PATH.read_bytes(),
        is_ancestor_of_head=lambda sha: True,
        ledger_lines=_ledger_lines(),
        filing_rows=[_row(_Q_ACCESSION)],
        fetch_index_headers=_index_headers(),
        k_inputs=lambda issuer, cutoff, period_end: None,
        companyfacts=lambda issuer: _facts(),
        submissions_pages=lambda issuer: (),
        exposure_path=exposure,
        now=_NOW,
        resolve_ticker=_resolver(),
        revisions_reader=_revisions_reader(qm1=[_rev("gen-ok")]),
    )
    (ep,) = result["episodes"]
    assert ep["status"] == "EXPOSED"  # the first read was not the evaluator's
    assert result["report"]["exposed"] == 1


def test_runner_label_none_within_120_days_is_pending(monkeypatch, tmp_path) -> None:
    result = _run(monkeypatch, tmp_path,
                  facts=lambda issuer: _facts(with_comparative=False))
    (ep,) = result["episodes"]
    assert ep["status"] == "ELIGIBLE"
    assert ep["label"] is None
    assert ep["not_evaluable_reason"] is None  # never relabeled early
    assert result["label_pending"] == 1
    assert result["report"]["n_common_support"] == 0  # label is not +/-1


def test_runner_label_none_after_120_days_is_unavailable(
        monkeypatch, tmp_path) -> None:
    late = datetime(2027, 2, 10, 12, 0, tzinfo=UTC)  # > 2026-09-30 + 120d
    result = _run(monkeypatch, tmp_path, now=late,
                  facts=lambda issuer: _facts(with_comparative=False))
    (ep,) = result["episodes"]
    assert ep["status"] == "NOT_EVALUABLE"
    assert ep["not_evaluable_reason"] == "label_unavailable"
    assert result["label_pending"] == 0


def test_runner_s_leak_maps_pre_cutoff_leak(monkeypatch, tmp_path) -> None:
    # a release-bearing q revision whose A2-corrected source clock lands at the
    # cutoff: 2026-10-29T00:00 "Z" -> 2026-10-28T20:00Z == C(e)
    leaky_q = [_rev("gen-q", source_available_at="2026-10-29T00:00:00Z")]
    result = _run(monkeypatch, tmp_path,
                  revisions=_revisions_reader(qm1=[_rev("gen-ok")], q=leaky_q))
    (ep,) = result["episodes"]
    assert ep["s"]["q_release_before_cutoff"] is True
    assert ep["status"] == "NOT_EVALUABLE"
    assert ep["not_evaluable_reason"] == "pre_cutoff_leak"
    assert result["report"]["not_evaluable"] == {"pre_cutoff_leak": 1}


def test_runner_chain_failure_is_pit_unrecoverable(monkeypatch, tmp_path) -> None:
    revisions = _revisions_reader(fail=RuntimeError("chain integrity"))
    result = _run(monkeypatch, tmp_path, revisions=revisions)
    (ep,) = result["episodes"]
    assert ep["s"]["reason"] == "chain_unreadable"
    assert ep["status"] == "NOT_EVALUABLE"
    assert ep["not_evaluable_reason"] == "pit_unrecoverable"
    assert len(revisions.calls) == 1  # the one refused call; never retried


def test_runner_single_revisions_reader_call(monkeypatch, tmp_path) -> None:
    revisions = _revisions_reader(qm1=[_rev("gen-ok")])
    _run(monkeypatch, tmp_path,
         rows=[_row(_Q_ACCESSION),
               _row("0009999991-26-000901", ticker="ZZWQ", cik=9999992)],
         revisions=revisions)
    assert len(revisions.calls) == 1  # one batched walk for ALL episodes
    assert len(revisions.calls[0]) == 4


# ---------------------------------------------------------------------------
# module hygiene
# ---------------------------------------------------------------------------


def test_runner_module_imports_clean_without_network() -> None:
    code = (
        "import sys\n"
        "import scripts.c19_wp31_runner\n"
        "banned = sorted(\n"
        "    name for name in sys.modules\n"
        "    if name == 'requests' or name.startswith(('urllib', 'socket',\n"
        "                                               'http.client'))\n"
        ")\n"
        "assert not banned, banned\n"
        "assert not hasattr(scripts.c19_wp31_runner, '__main__')\n"
        "print('ok')\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120,
    )
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip().endswith("ok")
