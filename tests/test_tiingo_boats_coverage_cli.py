"""Offline CLI coverage binding: file errors must precede any provider effect."""
from datetime import datetime, timezone
import pytest
from scripts import build_ext_quotes as publisher


@pytest.fixture
def cli(monkeypatch, tmp_path):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 19, 1, tzinfo=timezone.utc)
    calls = []
    monkeypatch.setattr(publisher, "datetime", Clock)
    monkeypatch.setattr(publisher, "publish_boats_stream", lambda **kw: calls.append(kw) or {"publication_ok": True})
    path = tmp_path / "coverage.txt"
    def run(content):
        path.write_text(content)
        monkeypatch.setattr("sys.argv", ["build_ext_quotes", "--boats", "--symbols-file", str(path)])
        publisher.main()
    return run, calls


def test_explicit_file_reaches_existing_publisher_in_order(cli):
    run, calls = cli
    run("AMD\nAAPL\nBRK.B\n")
    assert calls[0]["symbols"] == ["AMD", "AAPL", "BRK.B"]
    assert calls[0]["max_seconds"] == 600
    assert calls[0]["publish"] is False


@pytest.mark.parametrize("content", ["", "# empty\n", "../AMD\n", "amd\n"])
def test_invalid_file_has_no_provider_effect(cli, content):
    run, calls = cli
    with pytest.raises(ValueError):
        run(content)
    assert not calls


def test_symbol_file_cannot_enter_legacy_mode(monkeypatch, tmp_path):
    path = tmp_path / "coverage.txt"
    path.write_text("AMD\n")
    monkeypatch.setattr("sys.argv", ["build_ext_quotes", "--symbols-file", str(path)])
    with pytest.raises(SystemExit) as e:
        publisher.main()
    assert e.value.code == 2
