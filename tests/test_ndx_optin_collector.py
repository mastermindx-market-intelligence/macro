"""NDX-family acquisition uses the existing opt-in ThetaData collector only."""
from __future__ import annotations

from engine import options_universe
from scripts import backfill_thetadata_eod as backfill


def test_scheduled_full_history_roots_are_not_modified():
    # This assertion is deliberately strict: ordinary launchd/backfill defaults
    # stay as they were before the NDX/NDXP draft feature.
    assert backfill.INDEX_ROOTS == ["SPX", "SPXW"]
    assert "NDX" not in backfill.INDEX_ROOTS
    assert "NDXP" not in backfill.INDEX_ROOTS


def test_existing_explicit_roots_include_both_ndx_settlement_families(monkeypatch):
    monkeypatch.setattr(options_universe, "gex_symbols", lambda: ["SPY"])
    roots = backfill._resolve_universe(extra_roots=["NDX", "NDXP"])
    assert roots.count("NDX") == 1
    assert roots.count("NDXP") == 1
    assert roots.index("NDX") < roots.index("NDXP")
    assert backfill.INDEX_ROOTS == ["SPX", "SPXW"]
