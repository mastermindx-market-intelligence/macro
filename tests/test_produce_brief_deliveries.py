"""Tests for scripts/produce_brief_deliveries.py (W6-B MO-PAID-032 child).

Covers the CLI flag: unset BRIEF_DELIVERIES_ENABLE → DORMANT on stdout,
dry_run=True into the engine, 0 POSTs, exit 0.
--dry-run with flag set still writes nothing.
Never print env values.
"""
from __future__ import annotations

import pytest

from engine import brief_delivery_producer as prod
from scripts import produce_brief_deliveries as entry


# ---------------------------------------------------------------------------
# Fake tables helper (mirrors test_alert_delivery_drain.py pattern)
# ---------------------------------------------------------------------------

class FakeProducerResult:
    def __init__(
        self,
        outcome="ok",
        read_state=prod.READ_OK,
        error_class=None,
        planned_n=0,
        duplicate_n=0,
        written_n=0,
        run_id="test-run-id",
    ):
        self.outcome = outcome
        self.read_state = read_state
        self.error_class = error_class
        self.planned_n = planned_n
        self.duplicate_n = duplicate_n
        self.written_n = written_n
        self.run_id = run_id


# ---------------------------------------------------------------------------
# Test 1 — DORMANT: unset BRIEF_DELIVERIES_ENABLE → DORMANT line, dry_run forced
# ---------------------------------------------------------------------------

def test_dormant_default_forces_dry_run(monkeypatch, capsys):
    """DORMANT default: unset BRIEF_DELIVERIES_ENABLE forces dry_run=True, prints DORMANT."""
    captured = {}

    def fake_run(**kwargs):
        captured.update(kwargs)
        return FakeProducerResult(
            outcome="ok",
            read_state=prod.READ_OK,
            planned_n=0,
            duplicate_n=0,
            written_n=0,
        )

    monkeypatch.setattr(prod, "run", fake_run)
    monkeypatch.delenv("BRIEF_DELIVERIES_ENABLE", raising=False)

    rc = entry.main(["--now", "2026-09-16T18:30:00+00:00"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "DORMANT" in out
    assert captured.get("dry_run") is True


# ---------------------------------------------------------------------------
# Test 2 — --dry-run with flag unset: still DORMANT, 0 POSTs
# ---------------------------------------------------------------------------

def test_dry_run_flag_still_dormant_without_enable(monkeypatch, capsys):
    """--dry-run passed but flag unset: still DORMANT, forces dry_run=True."""
    captured = {}

    def fake_run(**kwargs):
        captured.update(kwargs)
        return FakeProducerResult()

    monkeypatch.setattr(prod, "run", fake_run)
    monkeypatch.delenv("BRIEF_DELIVERIES_ENABLE", raising=False)

    rc = entry.main(["--dry-run", "--now", "2026-09-16T18:30:00+00:00"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "DORMANT" in out
    assert captured.get("dry_run") is True


# ---------------------------------------------------------------------------
# Test 3 — With flag set (no --dry-run): writes real rows, not DORMANT
# ---------------------------------------------------------------------------

def test_enabled_without_dry_run_writes_real_rows(monkeypatch, capsys):
    """BRIEF_DELIVERIES_ENABLE=1 without --dry-run: dry_run=False, no DORMANT line."""
    captured = {}

    def fake_run(**kwargs):
        captured.update(kwargs)
        return FakeProducerResult(
            outcome="ok",
            read_state=prod.READ_OK,
            planned_n=1,
            duplicate_n=0,
            written_n=1,
        )

    monkeypatch.setattr(prod, "run", fake_run)
    monkeypatch.setenv("BRIEF_DELIVERIES_ENABLE", "1")

    rc = entry.main([])
    out = capsys.readouterr().out

    assert rc == 0
    assert "DORMANT" not in out
    assert captured.get("dry_run") is False


# ---------------------------------------------------------------------------
# Test 4 — --dry-run with flag set: still writes nothing (dry_run=True)
# ---------------------------------------------------------------------------

def test_dry_run_flag_with_enable_set_still_dry_run(monkeypatch, capsys):
    """--dry-run with BRIEF_DELIVERIES_ENABLE=1: dry_run=True, writes nothing."""
    captured = {}

    def fake_run(**kwargs):
        captured.update(kwargs)
        return FakeProducerResult(planned_n=1, written_n=0)

    monkeypatch.setattr(prod, "run", fake_run)
    monkeypatch.setenv("BRIEF_DELIVERIES_ENABLE", "1")

    rc = entry.main(["--dry-run"])
    out = capsys.readouterr().out

    assert rc == 0
    assert captured.get("dry_run") is True
    assert "planned=1" in out  # dry_run → label is "planned"


# ---------------------------------------------------------------------------
# Test 5 — READ_UNAVAILABLE emits ::warning line starting at column 0
# ---------------------------------------------------------------------------

def test_read_unavailable_emits_warning_at_column_0(monkeypatch, capsys):
    """READ_UNAVAILABLE: ::warning line starts at column 0, exit 0."""
    def fake_run(**kwargs):
        return FakeProducerResult(
            outcome="read_unavailable",
            read_state=prod.READ_UNAVAILABLE,
            error_class="no_credentials",
            written_n=0,
        )

    monkeypatch.setattr(prod, "run", fake_run)
    monkeypatch.setenv("BRIEF_DELIVERIES_ENABLE", "1")

    rc = entry.main([])
    out = capsys.readouterr().out

    assert rc == 0
    warning_lines = [ln for ln in out.splitlines() if "::warning" in ln]
    assert warning_lines, "expected a ::warning line"
    assert warning_lines[0].startswith("::warning")


# ---------------------------------------------------------------------------
# Test 6 — No env values printed
# ---------------------------------------------------------------------------

def test_dormant_cli_real_run_emits_no_warning(monkeypatch, capsys):
    """B1(ii) / m1: ENABLE unset exercises the real run() path (no stub).

    Exit 0, DORMANT on stdout, no ::warning on stdout or stderr. Fails at
    654771a0 because the warning fired whenever read_state was unavailable,
    including dormant mode.
    """
    monkeypatch.delenv("BRIEF_DELIVERIES_ENABLE", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

    rc = entry.main(["--now", "2026-09-16T22:30:00+00:00"])
    captured = capsys.readouterr()

    assert rc == 0
    assert "DORMANT" in captured.out
    assert "::warning" not in captured.out
    assert "::warning" not in captured.err


def test_no_env_values_in_output(monkeypatch, capsys):
    """Stdout must not contain env var names or values."""
    def fake_run(**kwargs):
        return FakeProducerResult()

    monkeypatch.setattr(prod, "run", fake_run)
    monkeypatch.setenv("BRIEF_DELIVERIES_ENABLE", "1")
    monkeypatch.setenv("SUPABASE_URL", "https://real.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "real-secret-key")

    rc = entry.main([])
    out = capsys.readouterr().out

    assert rc == 0
    assert "real.supabase.co" not in out
    assert "real-secret-key" not in out
    assert "https://" not in out
    assert "secret" not in out.lower()
