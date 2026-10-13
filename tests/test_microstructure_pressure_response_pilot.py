"""Offline pilot CLI projection; protect original raw print/quote receipts."""

import json

import pytest

from scripts.microstructure_pressure_response_pilot import (
    INPUT_SCHEMA, MAX_INPUT_BYTES, bounded_json, main, summarize,
)
from test_equity_pressure_response import payload


def valid_frame():
    return {"contract": INPUT_SCHEMA, "measurement": payload()}


def test_pilot_derives_only_summary_no_print_identity_or_trade_price():
    frame = valid_frame()
    result = summarize(frame)
    assert result["pressure_balance"].startswith("0.00398")
    assert "print_diagnostics_private_only" not in result
    assert "\"trade_id\"" not in json.dumps(result)
    assert "quote_source_receipt" not in json.dumps(result)


def test_wrong_input_contract_and_unknown_properties_refused():
    frame = valid_frame()
    frame["contract"] = "unknown/v1"
    with pytest.raises(ValueError, match="unrecognized R0"):
        summarize(frame)
    frame = valid_frame()
    frame["unexpected"] = 1
    with pytest.raises(ValueError, match="only a measurement"):
        summarize(frame)
    frame = valid_frame()
    frame["measurement"]["new_source_event"] = []
    with pytest.raises(ValueError, match="frozen input contract"):
        summarize(frame)


def test_qualification_failure_does_not_emit_a_fake_zero_measurement():
    frame = valid_frame()
    frame["measurement"]["watermark_ns"] = 50
    out = summarize(frame)
    assert out["state"] == "NOT_MATURE"
    assert "pressure_balance" not in out


def test_bounded_json_rejects_malformed_or_oversize(tmp_path):
    malformed = tmp_path / "bad.json"
    malformed.write_text("not JSON")
    with pytest.raises(ValueError, match="UTF-8 JSON"):
        bounded_json(malformed)
    giant = tmp_path / "giant.json"
    giant.write_bytes(b" " * (MAX_INPUT_BYTES + 1))
    with pytest.raises(ValueError, match="file budget"):
        bounded_json(giant)
    wrong_ext = tmp_path / "wrong.txt"
    wrong_ext.write_text("{}")
    with pytest.raises(ValueError, match="private JSON"):
        bounded_json(wrong_ext)


def test_cli_success_and_safe_summary_stdout(tmp_path, capsys):
    path = tmp_path / "qualified.json"
    path.write_text(json.dumps(valid_frame()))
    rc = main(["--input", str(path)])
    captured = capsys.readouterr()
    assert rc == 0 and not captured.err
    result = json.loads(captured.out)
    assert result["schema"] == "equity.pressure_response_observation/v0"
    assert "print_diagnostics_private_only" not in captured.out
    assert "source_receipt" not in captured.out


def test_cli_failure_return_is_not_success(tmp_path, capsys):
    path = tmp_path / "missing.json"
    assert main(["--input", str(path)]) == 2
    captured = capsys.readouterr()
    assert not captured.out and "refused" in captured.err
