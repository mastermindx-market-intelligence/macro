"""Audit bytes, honesty and side-effect fences using real temporary parquet files."""
from datetime import datetime, timezone
import hashlib
import json

import pandas as pd
import pytest

from scripts import audit_market_fragility as audit_module

NOW = datetime(2026, 11, 13, 14, tzinfo=timezone.utc)


def write_source(path, *, asof="2026-11-12"):
    pd.DataFrame({"gamma_regime": ["short"], "tier": ["full"], "spot": [7500.0]},
                 index=pd.to_datetime([asof])).to_parquet(path)


def test_hash_matches_exact_read_bytes_and_source_is_unchanged(tmp_path):
    path = tmp_path / "gex_SPX.parquet"
    write_source(path)
    original = path.read_bytes()
    report = audit_module.audit(path, now=NOW, window_sessions=1)
    assert report["source_snapshot"]["sha256"] == hashlib.sha256(original).hexdigest()
    assert report["source_snapshot"]["rows"] == 1
    assert report["observation"]["state"] == "amplifying"
    assert path.read_bytes() == original
    assert set(tmp_path.iterdir()) == {path}
    assert report["research_readiness"]["promotion_authorized"] is False
    assert report["research_readiness"]["availability_clock_rows"] == 0
    json.dumps(report, allow_nan=False)


def test_missing_source_reports_failure_not_empty_success(tmp_path):
    report = audit_module.audit(tmp_path / "absent.parquet", now=NOW)
    assert report["source_snapshot"]["read_error"] == "FileNotFoundError"
    assert report["observation"]["state"] == "unknown"
    assert report["research_readiness"]["availability_clock_fraction"] is None


def test_oversize_source_is_not_windowed_or_truncated_into_a_good_result(tmp_path, monkeypatch):
    path = tmp_path / "gex_SPX.parquet"
    write_source(path)
    monkeypatch.setattr(audit_module, "_MAX_INPUT_BYTES", 10)
    report = audit_module.audit(path, now=NOW)
    assert report["source_snapshot"]["read_error"] == "source_bound_exceeded"
    assert report["observation"]["state"] == "unknown"


def test_historical_asof_is_never_pit_qualification(tmp_path):
    path = tmp_path / "gex_SPX.parquet"
    write_source(path, asof="2026-07-10")
    report = audit_module.audit(path, now=datetime(2026, 7, 13, 14, tzinfo=timezone.utc))
    assert report["audit_kind"] == "snapshot_diagnostic_not_pit_backtest"
    assert report["research_readiness"]["historical_vintages_verified"] is False
    assert report["research_readiness"]["predictive_validation"] == "NOT_ESTABLISHED"


def test_cli_returns_nonzero_for_stale_source_without_writing_a_gate(tmp_path, capsys):
    path = tmp_path / "gex_SPX.parquet"
    write_source(path, asof="2026-11-06")
    rc = audit_module.main(["--input", str(path), "--as-of", "2026-11-13T14:00:00Z", "--require-current"])
    assert rc == 2
    result = json.loads(capsys.readouterr().out)
    assert result["observation"]["state"] == "unknown"
    assert set(tmp_path.iterdir()) == {path}


def test_audit_output_is_explicit_and_exclusive(tmp_path, capsys):
    path = tmp_path / "gex_SPX.parquet"
    target = tmp_path / "evidence" / "audit.json"
    write_source(path)
    args = ["--input", str(path), "--as-of", "2026-11-13T14:00:00Z", "--output", str(target)]
    assert audit_module.main(args) == 0
    capsys.readouterr()
    before = target.read_bytes()
    with pytest.raises(FileExistsError):
        audit_module.main(args)
    assert target.read_bytes() == before


@pytest.mark.parametrize("asof", ["2026-11-13", "2026-11-13T14:00:00", "not-a-date"])
def test_cli_demands_explicit_clock_timezone(asof):
    with pytest.raises(SystemExit) as exc:
        audit_module.main(["--as-of", asof])
    assert exc.value.code == 2


def test_existing_validator_is_called_only_as_read_only_diagnostic(tmp_path, monkeypatch):
    from scripts import validate_gex
    path = tmp_path / "gex_SPX.parquet"
    write_source(path)
    calls = []
    def evaluate(name, data, store_label):
        calls.append((name, len(data), store_label))
        return ["test diagnostic, not promotion"]
    monkeypatch.setattr(validate_gex, "evaluate", evaluate)
    def forbidden():
        raise AssertionError("existing gate writer must not run")
    monkeypatch.setattr(validate_gex, "main", forbidden)
    report = audit_module.audit(path, now=NOW, run_existing_diagnostic=True)
    assert calls == [("SPX", 1, "cboe")]
    assert report["research_readiness"]["diagnostic_is_promotion"] is False
    assert set(tmp_path.iterdir()) == {path}
