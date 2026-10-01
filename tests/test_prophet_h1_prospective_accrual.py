from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import pytest

from scripts import check_prophet_h1_prospective_accrual as chk

SESSION = "2026-09-29"
BOARD = "board-v1"


def _row(ticker: str = "AAA", **updates):
    row = {
        "stamp_date": SESSION, "ticker": ticker, "board_definition": BOARD, "lane": "scan",
        "security_id": f"SEC:{ticker}", "issuer_id": f"ISS:{ticker}", "identity_epoch": "epoch_0",
        "identity_epoch_state": "provisional", "identity_capture_state": "AVAILABLE",
        "identity_capture_basis": "prospective", "identity_alias_source_sha256": "sha256:a",
        "identity_master_source_sha256": "sha256:b", "cycle_state": "ready", "cycle_label": "Ready",
        "cycle_label_vocab_sha256": "sha256:c", "theme_membership_ids": "basket-x",
        "theme_membership_source_sha256": "sha256:d", "theme_membership_source_version": "v1",
        "theme_membership_source_curated": SESSION, "theme_membership_basis": "PIT",
        "theme_capture_group_id": "basket-x", "theme_capture_group_state": "SOLE_ACTIVE_MEMBERSHIP",
        "theme_capture_group_rule": "SOLE_ACTIVE_PIT_MEMBERSHIP_ONLY_V1",
        "theme_capture_group_weighting": "equal", "theme_capture_member_tickers": "BBB|CCC",
        "theme_capture_member_set_sha256": "sha256:e", "context_dims": "regime|theme",
    }
    row.update(updates)
    return row


def _write(root: Path, rows: list[dict], month: str = "2026-09") -> Path:
    path = root / "data" / "us_prophet_rank" / "candidates" / f"{month}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)
    return path


def test_absent_store_is_not_started(tmp_path):
    r = chk.inspect(expected_session=SESSION, board_definition=BOARD, root=tmp_path)
    assert r["status"] == chk.STATUS_CAPTURE_NOT_STARTED
    assert r["outcome_redacted"] is True
    assert r["h1_admitted"] is False


def test_month_without_expected_session_is_dark(tmp_path):
    path = _write(tmp_path, [_row(stamp_date="2026-09-26")])
    r = chk.inspect(expected_session=SESSION, board_definition=BOARD, root=tmp_path)
    assert r["status"] == chk.STATUS_CANDIDATE_CAPTURE_DARK
    assert r["source_receipt"]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_legacy_month_without_prospective_schema_does_not_start_s0(tmp_path):
    path = tmp_path / "data" / "us_prophet_rank" / "candidates" / "2026-09.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{
        "stamp_date": SESSION, "ticker": "AAA", "board_definition": BOARD,
        "lane": "scan", "context_dims": "regime|theme",
        "theme_membership_ids": "basket-x",
    }]).to_parquet(path, index=False)
    r = chk.inspect(expected_session=SESSION, board_definition=BOARD, root=tmp_path)
    assert r["status"] == chk.STATUS_CANDIDATE_CAPTURE_DARK
    assert r["reason"] == "PROSPECTIVE_SCHEMA_NOT_PRESENT"
    assert "security_id" in r["missing_required_columns"]
    assert "theme_capture_group_state" in r["missing_required_columns"]
    assert r["source_receipt"]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert r["h1_admitted"] is False


def test_nonempty_native_capture_produces_s0_receipt_and_coverage(tmp_path):
    path = _write(tmp_path, [_row("AAA"), _row("BBB")])
    r = chk.inspect(expected_session=SESSION, board_definition=BOARD, root=tmp_path)
    assert r["status"] == chk.STATUS_S0_CAPTURE_PRESENT
    assert r["rows"] == 2
    assert r["unique_tickers"] == 2
    assert r["duplicate_key_rows"] == 0
    assert r["cycle_pair_mismatch_rows"] == 0
    assert r["coverage"] == {
        "identity_resolved": 1.0,
        "membership_source_receipt": 1.0,
        "sole_supported_peer_group": 1.0,
        "context_dims_present": 1.0,
    }
    assert r["source_receipt"]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert r["h1_admitted"] is False


def test_identical_duplicate_is_reported_but_not_conflicting(tmp_path):
    row = _row()
    _write(tmp_path, [row, dict(row)])
    r = chk.inspect(expected_session=SESSION, board_definition=BOARD, root=tmp_path)
    assert r["status"] == chk.STATUS_S0_CAPTURE_PRESENT
    assert r["duplicate_key_rows"] == 2


def test_conflicting_native_key_fails_closed(tmp_path):
    _write(tmp_path, [_row(), _row(issuer_id="ISS:OTHER")])
    r = chk.inspect(expected_session=SESSION, board_definition=BOARD, root=tmp_path)
    assert r["status"] == chk.STATUS_SOURCE_CONFLICT
    assert r["reason"] == "CONFLICTING_NATIVE_KEYS"
    assert r["conflicting_keys"] == [
        {"stamp_date": SESSION, "ticker": "AAA", "board_definition": BOARD}
    ]


def test_cycle_pair_mismatch_and_group_missingness_are_disclosed(tmp_path):
    _write(tmp_path, [_row(cycle_label=None, theme_capture_group_state="AMBIGUOUS_OVERLAP",
                           theme_capture_group_id=None, theme_capture_group_weighting=None,
                           theme_capture_member_set_sha256=None)])
    r = chk.inspect(expected_session=SESSION, board_definition=BOARD, root=tmp_path)
    assert r["status"] == chk.STATUS_S0_CAPTURE_PRESENT
    assert r["cycle_pair_mismatch_rows"] == 1
    assert r["coverage"]["sole_supported_peer_group"] == 0.0
    assert r["source_states"]["group_state"] == {"AMBIGUOUS_OVERLAP": 1}


def test_forbidden_outcome_fields_are_not_requested():
    assert set(chk.READ_COLUMNS).isdisjoint(chk.FORBIDDEN)


def _legacy_row(ticker="OLD", **updates):
    row = {"stamp_date": SESSION, "ticker": ticker, "board_definition": BOARD,
           "lane": "scan", "context_dims": "regime"}
    row.update(updates)
    return row


def test_newer_month_row_cannot_backdate_s0_for_legacy_session(tmp_path):
    _write(tmp_path, [_legacy_row(), _row("NEW", stamp_date="2026-09-30")])
    r = chk.inspect(expected_session=SESSION, board_definition=BOARD, root=tmp_path)
    assert r["status"] == chk.STATUS_CANDIDATE_CAPTURE_DARK
    assert r["reason"] == "PROSPECTIVE_ROW_WITNESS_NOT_PRESENT"
    assert r["rows_missing_prospective_witness"] == 1
    assert r["h1_admitted"] is False


def test_one_current_row_cannot_hide_legacy_rows_in_same_session(tmp_path):
    _write(tmp_path, [_legacy_row(), _row("NEW")])
    r = chk.inspect(expected_session=SESSION, board_definition=BOARD, root=tmp_path)
    assert r["status"] == chk.STATUS_CANDIDATE_CAPTURE_DARK
    assert r["rows"] == 2
    assert r["rows_missing_prospective_witness"] == 1


def test_explicit_unavailable_capture_is_not_mistaken_for_legacy(tmp_path):
    _write(tmp_path, [_row(security_id=None, issuer_id=None, identity_epoch=None,
        identity_capture_state="SOURCE_UNAVAILABLE", identity_capture_basis=None,
        cycle_state=None, cycle_label=None, cycle_label_vocab_sha256=None,
        theme_membership_source_sha256=None, theme_capture_group_id=None,
        theme_capture_group_state="SOURCE_UNAVAILABLE", theme_capture_group_weighting=None,
        theme_capture_member_set_sha256=None)])
    r = chk.inspect(expected_session=SESSION, board_definition=BOARD, root=tmp_path)
    assert r["status"] == chk.STATUS_S0_CAPTURE_PRESENT
    assert r["coverage"]["identity_resolved"] == 0.0
    assert r["h1_admitted"] is False


def test_optional_column_missing_never_decodes_unrequested_fields(tmp_path, monkeypatch):
    row = _row()
    del row["identity_alias_source_sha256"]
    row["fwd_ret"] = 999999.0  # Synthetic forbidden-field sentinel, not an outcome.
    _write(tmp_path, [row])
    original = chk.pq.ParquetFile
    calls = []
    class ProjectedOnly:
        def __init__(self, *args, **kwargs):
            self.inner = original(*args, **kwargs)
            self.schema_arrow = self.inner.schema_arrow
        def read(self, *args, **kwargs):
            columns = kwargs.get("columns")
            calls.append(columns)
            assert columns is not None, "unrestricted native read is forbidden"
            assert set(columns).issubset(chk.READ_COLUMNS)
            assert set(columns).isdisjoint(chk.FORBIDDEN)
            assert kwargs.get("use_pandas_metadata") is False
            return self.inner.read(*args, **kwargs)
    monkeypatch.setattr(chk.pq, "ParquetFile", ProjectedOnly)
    r = chk.inspect(expected_session=SESSION, board_definition=BOARD, root=tmp_path)
    assert r["status"] == chk.STATUS_S0_CAPTURE_PRESENT
    assert len(calls) == 1


def test_schema_rows_and_receipt_use_one_original_snapshot(tmp_path, monkeypatch):
    part = _write(tmp_path, [_row("ORIGINAL")])
    original_bytes = part.read_bytes()
    original_read = Path.read_bytes
    original_loader = chk.ucv.load_candidates
    reads = []
    snapshot_payloads = []
    def count_original(path):
        if path == part:
            reads.append(path)
        return original_read(path)
    def load_while_source_changes(root=None, **kwargs):
        # Simulate a concurrent atomic producer replacement after snapshot acquisition.
        _write(tmp_path, [_row("LATER"), _row("ANOTHER")])
        supplied = kwargs.get("snapshot_parts")
        assert supplied == {"2026-09": original_bytes}, "native reader lacks bound byte snapshot"
        snapshot_payloads.append(supplied)
        return original_loader(root, **kwargs)
    monkeypatch.setattr(Path, "read_bytes", count_original)
    monkeypatch.setattr(chk.ucv, "load_candidates", load_while_source_changes)
    r = chk.inspect(expected_session=SESSION, board_definition=BOARD, root=tmp_path)
    assert r["status"] == chk.STATUS_S0_CAPTURE_PRESENT
    assert r["rows"] == 1
    assert r["source_receipt"]["sha256"] == hashlib.sha256(original_bytes).hexdigest()
    assert len(reads) == 1
    assert len(snapshot_payloads) == 1


def test_malformed_part_returns_typed_conflict(tmp_path):
    part = tmp_path / "data/us_prophet_rank/candidates/2026-09.parquet"
    part.parent.mkdir(parents=True)
    part.write_bytes(b"synthetic invalid parquet")
    r = chk.inspect(expected_session=SESSION, board_definition=BOARD, root=tmp_path)
    assert r["status"] == chk.STATUS_SOURCE_CONFLICT
    assert r["reason"] == "CANDIDATE_PART_UNREADABLE"
    assert r["h1_admitted"] is False
    assert r["source_receipt"]["sha256"] == hashlib.sha256(part.read_bytes()).hexdigest()


def test_native_key_missing_from_physical_part_cannot_start_s0(tmp_path):
    row = _row()
    del row["ticker"]
    _write(tmp_path, [row])
    r = chk.inspect(expected_session=SESSION, board_definition=BOARD, root=tmp_path)
    assert r["status"] != chk.STATUS_S0_CAPTURE_PRESENT
    assert "ticker" in r["missing_required_columns"]


def test_empty_native_ticker_cannot_start_s0(tmp_path):
    _write(tmp_path, [_row(ticker=" ")])
    r = chk.inspect(expected_session=SESSION, board_definition=BOARD, root=tmp_path)
    assert r["status"] == chk.STATUS_SOURCE_CONFLICT
    assert r["reason"] == "INVALID_NATIVE_KEYS"


def test_read_failure_cannot_be_reported_as_quiet_capture(tmp_path, monkeypatch):
    part = _write(tmp_path, [_row()])
    original = Path.read_bytes
    def fail_read(path):
        if path == part:
            raise PermissionError("synthetic private path detail")
        return original(path)
    monkeypatch.setattr(Path, "read_bytes", fail_read)
    r = chk.inspect(expected_session=SESSION, board_definition=BOARD, root=tmp_path)
    assert r["status"] == chk.STATUS_SOURCE_CONFLICT
    assert r["reason"] == "CANDIDATE_PART_UNREADABLE"
    assert "private path" not in str(r)


@pytest.mark.parametrize("columns", [None, [], "ticker", ["ticker", "ticker"]])
def test_strict_native_snapshot_requires_bounded_unique_projection(tmp_path, columns):
    raw = _write(tmp_path, [_row()]).read_bytes()
    with pytest.raises(ValueError):
        chk.ucv.load_candidates(months=["2026-09"], columns=columns,
                                snapshot_parts={"2026-09": raw})


@pytest.mark.parametrize("months", [None, [], ["2026-08"], ["2026-09", "2026-09"], "2026-09"])
def test_strict_native_snapshot_requires_exact_month_binding(tmp_path, months):
    raw = _write(tmp_path, [_row()]).read_bytes()
    with pytest.raises(ValueError):
        chk.ucv.load_candidates(months=months, columns=["ticker"],
                                snapshot_parts={"2026-09": raw})


def test_snapshot_reader_does_not_consult_storage(tmp_path, monkeypatch):
    raw = _write(tmp_path, [_row()]).read_bytes()
    def forbidden_storage(*args, **kwargs):
        raise AssertionError("snapshot path must not consult storage")
    monkeypatch.setattr(chk.ucv, "_store_dir", forbidden_storage)
    frame = chk.ucv.load_candidates(months=["2026-09"], columns=["ticker"],
                                    snapshot_parts={"2026-09": raw})
    assert frame["ticker"].tolist() == ["AAA"]


def test_pandas_index_metadata_cannot_add_outcome_columns(tmp_path, monkeypatch):
    part = _write(tmp_path, [_row()])
    frame = pd.DataFrame([_row()])
    frame["fwd_ret"] = 999999.0
    frame.set_index("fwd_ret").to_parquet(part)
    raw = part.read_bytes()
    original = chk.pq.ParquetFile
    reads = []
    class GuardedProjection:
        def __init__(self, *args, **kwargs):
            self.inner = original(*args, **kwargs)
            self.schema_arrow = self.inner.schema_arrow
        def read(self, *args, **kwargs):
            assert kwargs.get("use_pandas_metadata") is False
            assert set(kwargs["columns"]).isdisjoint(chk.FORBIDDEN)
            reads.append(kwargs["columns"])
            return self.inner.read(*args, **kwargs)
    monkeypatch.setattr(chk.pq, "ParquetFile", GuardedProjection)
    result = chk.ucv.load_candidates(months=["2026-09"], columns=["ticker"],
                                     snapshot_parts={"2026-09": raw})
    assert reads == [["ticker"]]
    assert list(result.columns) == ["ticker"]
    assert list(result.index) == [0]


def test_snapshot_decode_failure_never_uses_legacy_fallback(tmp_path, monkeypatch):
    part = _write(tmp_path, [_row()])
    original = chk.pq.ParquetFile
    reads = []
    class BrokenProjectedDecode:
        def __init__(self, *args, **kwargs):
            self.inner = original(*args, **kwargs)
            self.schema_arrow = self.inner.schema_arrow
        def read(self, *args, **kwargs):
            reads.append(kwargs.get("columns"))
            raise ValueError("synthetic decoder failure")
    def forbidden_fallback(*args, **kwargs):
        raise AssertionError("legacy fallback must not be reachable")
    monkeypatch.setattr(chk.pq, "ParquetFile", BrokenProjectedDecode)
    monkeypatch.setattr(pd, "read_parquet", forbidden_fallback)
    r = chk.inspect(expected_session=SESSION, board_definition=BOARD, root=tmp_path)
    assert r["status"] == chk.STATUS_SOURCE_CONFLICT
    assert r["reason"] == "CANDIDATE_PART_UNREADABLE"
    assert len(reads) == 1 and reads[0] is not None


def test_nested_requested_field_is_rejected_before_decoding(tmp_path, monkeypatch):
    _write(tmp_path, [_row(security_id={"fwd_ret": 999999.0})])
    original = chk.pq.ParquetFile
    reads = []
    class TraceDecode:
        def __init__(self, *args, **kwargs):
            self.inner = original(*args, **kwargs)
            self.schema_arrow = self.inner.schema_arrow
        def read(self, *args, **kwargs):
            reads.append(kwargs.get("columns"))
            return self.inner.read(*args, **kwargs)
    monkeypatch.setattr(chk.pq, "ParquetFile", TraceDecode)
    r = chk.inspect(expected_session=SESSION, board_definition=BOARD, root=tmp_path)
    assert r["status"] == chk.STATUS_SOURCE_CONFLICT
    assert reads == [], "nested metadata rejection must precede value decoding"


def test_snapshot_month_union_is_chronological_and_null_preserving(tmp_path):
    first = _write(tmp_path, [_row("EARLIER", stamp_date="2026-08-31")], month="2026-08").read_bytes()
    later = _row("LATER")
    del later["identity_alias_source_sha256"]
    second = _write(tmp_path, [later]).read_bytes()
    frame = chk.ucv.load_candidates(months=["2026-09", "2026-08"],
        columns=["ticker", "identity_alias_source_sha256"],
        snapshot_parts={"2026-09": second, "2026-08": first})
    assert frame["ticker"].tolist() == ["EARLIER", "LATER"]
    assert frame["identity_alias_source_sha256"].iloc[0] == "sha256:a"
    assert pd.isna(frame["identity_alias_source_sha256"].iloc[1])


@pytest.mark.parametrize("session", ["20260929", "2026-02-30", "../2026-09", "2026-13-01"])
def test_invalid_session_is_rejected_before_storage_lookup(tmp_path, monkeypatch, session):
    def forbidden_lookup(*args, **kwargs):
        raise AssertionError("invalid session reached storage")
    monkeypatch.setattr(chk, "_part_path", forbidden_lookup)
    with pytest.raises(ValueError):
        chk.inspect(expected_session=session, board_definition=BOARD, root=tmp_path)
