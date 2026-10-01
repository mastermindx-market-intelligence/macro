from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

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
