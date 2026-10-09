"""Read-only corpus accounting against exact planned requests; synthetic data only."""
from datetime import date
import hashlib
import json
from pathlib import Path

import pytest
import collectors.tiingo_archive as a
from scripts.tiingo_corpus_audit import audit_corpus, summarize_records
from scripts.tiingo_ingest import Task, plan

CUTOFF = "2026-10-09T23:00:00Z"


@pytest.fixture
def lake(tmp_path, monkeypatch):
    monkeypatch.setattr(a, "EXTERNAL_MOUNT", tmp_path)
    return a.Archive(tmp_path / "lake", check_mount=False, free_floor=0)


def task(source="eod-bars", symbol="AMD"):
    return Task(source, symbol, {"startDate": "2020-01-01", "endDate": "2020-01-03"})


def saved(lake, t, data, at="2026-10-09T12:00:00Z"):
    raw = data if isinstance(data, bytes) else json.dumps(data).encode()
    return lake.store_response(t.source, t.symbol, a.request_path(t.source, t.symbol, t.params), raw,
                               received_at=at)


def audit(lake, tasks=None, **kw):
    opts = dict(root=lake.root, observed_before=CUTOFF, check_mount=False)
    opts.update(kw)
    return audit_corpus(tasks if tasks is not None else [task()], **opts)


def test_missing_archive_is_not_created(tmp_path, monkeypatch):
    monkeypatch.setattr(a, "EXTERNAL_MOUNT", tmp_path)
    root = tmp_path / "missing"
    out = audit_corpus([task()], root=root, observed_before=CUTOFF, check_mount=False)
    assert out["request_status_counts"] == {"NOT_FOUND": 1}
    assert not root.exists()
    assert out["complete_history_proven"] is False


def test_empty_response_is_distinct_from_not_fetched(lake):
    saved(lake, task(), [])
    out = audit(lake)
    assert out["request_status_counts"] == {"EMPTY_CAPTURED": 1}
    assert out["backtest_admission"] == "NOT_GRANTED"


def test_exact_request_matches_but_does_not_imply_gap_free_data(lake):
    saved(lake, task(), [{"date": "2020-01-01", "close": 1}, {"date": "2020-01-03", "close": 2}])
    out = audit(lake)
    assert out["request_status_counts"] == {"RAW_RECORDS_CAPTURED": 1}
    info = out["requests"][0]["latest_capture"]
    assert info["records"] == info["dates"] == 2
    assert out["complete_history_proven"] is False
    assert out["canonical_identity_admitted"] is False
    assert out["source_authenticity_proven"] is False


def test_byte_integrity_is_checked_not_just_file_existence(lake):
    rec = saved(lake, task(), [{"date": "2020-01-01", "close": 1}])
    (lake.root / rec["path"]).write_bytes(b"invalid")
    assert audit(lake)["request_status_counts"] == {"INVALID_CAPTURE": 1}


def test_wrong_symbol_receipt_cannot_satisfy_requested_history(lake):
    saved(lake, task(), [{"date": "2020-01-01", "close": 1}])
    file = next((lake.root / "receipts").rglob("*.json"))
    rec = json.loads(file.read_text()); rec["symbol"] = "NVDA"; file.write_text(json.dumps(rec))
    assert audit(lake)["request_status_counts"] == {"INVALID_CAPTURE": 1}


def test_different_date_window_is_not_complete_matching_request(lake):
    other = Task("eod-bars", "AMD", {"startDate": "2021-01-01", "endDate": "2021-01-03"})
    saved(lake, other, [{"date": "2021-01-01", "close": 1}])
    out = audit(lake)
    assert out["request_status_counts"] == {"NOT_FOUND": 1}
    assert out["scan"]["unrelated_receipts"] == 1


def test_capture_after_cutoff_is_excluded(lake):
    saved(lake, task(), [{"date": "2020-01-01", "close": 1}])
    out = audit(lake, observed_before="2026-10-09T11:00:00Z")
    assert out["request_status_counts"] == {"NOT_FOUND": 1}
    assert out["scan"]["after_observation_cutoff"] == 1


def test_latest_capture_tie_is_ambiguous_not_arbitrary_winner(lake):
    saved(lake, task(), [{"date": "2020-01-01", "close": 1}])
    saved(lake, task(), [{"date": "2020-01-01", "close": 2}])
    assert audit(lake)["request_status_counts"] == {"AMBIGUOUS_LATEST_CAPTURE": 1}


def test_revision_history_is_counted_separately(lake):
    saved(lake, task(), [{"date": "2020-01-01", "close": 1}], at="2026-10-09T10:00:00Z")
    saved(lake, task(), [{"date": "2020-01-01", "close": 2}], at="2026-10-09T11:00:00Z")
    out = audit(lake)
    assert out["requests"][0]["stored_response_count"] == 2
    assert out["requests"][0]["latest_capture"]["records"] == 1


def test_crypto_counts_bars_not_top_level_pairs():
    t = Task("crypto-bars", None, {"tickers": "btcusd,ethusd"})
    raw = json.dumps([{"ticker": "btcusd", "priceData": [{"date": "2020-01-01"}, {"date": "2020-01-02"}]}]).encode()
    out = summarize_records(raw, t)
    assert out["records"] == 2 and out["missing_crypto_pairs"] == 1


def test_crypto_pair_mismatch_is_invalid():
    t = Task("crypto-bars", None, {"tickers": "btcusd"})
    with pytest.raises(ValueError):
        summarize_records(b'[{"ticker":"ethusd","priceData":[]}]', t)


def test_outside_requested_dates_are_reported(lake):
    saved(lake, task(), [{"date": "2025-01-01", "close": 1}])
    assert audit(lake)["request_status_counts"] == {"PARTIAL_OR_OUT_OF_RANGE": 1}


def test_api_error_shape_cannot_count_as_a_history_row(lake):
    saved(lake, task(), {"detail": "not available"})
    assert audit(lake)["request_status_counts"] == {"INVALID_CAPTURE": 1}


def test_json_nonfinite_and_duplicate_fields_are_rejected(lake):
    for body in (b'[{"date":"2020-01-01","close":NaN}]', b'[{"date":"2020-01-01","date":"2020-01-02"}]'):
        with pytest.raises(ValueError):
            summarize_records(body, task())


def test_read_budget_exhaustion_is_not_full_scan(lake):
    saved(lake, task(), [{"date": "2020-01-01", "close": 1}])
    out = audit(lake, read_budget=1)
    assert out["all_receipts_inspected"] is False
    assert out["scan"]["read_budget_skips"] == 1


def test_scan_budget_and_output_budget_are_explicit(lake):
    tasks = [task(symbol="AMD"), task(symbol="NVDA")]
    for t in tasks:
        saved(lake, t, [{"date": "2020-01-01", "close": 1}])
    out = audit(lake, tasks, max_receipts=1, detail_limit=0)
    assert out["all_receipts_inspected"] is False
    assert out["requests"] == []
    assert out["expected_requests"] == 2


def test_audit_does_not_mutate_any_evidence_or_call_provider(lake, monkeypatch):
    saved(lake, task(), [{"date": "2020-01-01", "close": 1}])
    def forbid(*args, **kwargs):
        pytest.fail("read-only audit invoked provider or key")
    monkeypatch.setattr(a, "read_key", forbid)
    monkeypatch.setattr(a, "collect_one", forbid)
    before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in lake.root.rglob("*") if p.is_file()}
    audit(lake)
    after = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in lake.root.rglob("*") if p.is_file()}
    assert before == after


def test_naive_observation_cutoff_is_not_implicitly_utc(lake):
    with pytest.raises(ValueError):
        audit(lake, observed_before="2026-10-09T20:00:00")


def test_duplicate_expected_requests_are_not_double_counted(lake):
    with pytest.raises(ValueError):
        audit(lake, [task(), task()])
