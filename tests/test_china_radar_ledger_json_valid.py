"""China Divergence Radar ledger — the published emit must be strict JSON.

RED-first (DESIGN W27B §SPEC 5): `track_record()` copies the parquet cell straight into the
row dict (engine/china_radar_ledger.py:236), so a legacy row's NaN `family` reaches
site/chinaradar/ledger.json as `"family":NaN` — 46 occurrences in the committed bytes, which
`JSON.parse` rejects. Fixtures are synthetic parquets under tmp_path (the pattern of
tests/test_china_radar.py:82-95): no data/ read, no network, no builder call.
"""
from __future__ import annotations

import json

import pandas as pd

from engine import china_radar_ledger as rl

_COLS = list(rl._COLUMNS)
_LEGACY = "credit_impulse->512800.SS"
_VENUE = "venue_offshore_gap->china"


def _ledger_frame():
    """One legacy row whose `family` is NaN (as the committed parquet carries it) + one venue."""
    return pd.DataFrame([
        {"event_id": f"{_LEGACY}|2026-07", "fired_date": "2026-07-17", "pair": _LEGACY,
         "signal_key": "credit_impulse", "family": float("nan"), "sector_etf": "512800.SS",
         "sector_en": "Banks", "sector_zh": "银行", "sign": "negative", "rs_at_fire": 0.63,
         "signal_value": -6.4},
        {"event_id": f"{_VENUE}|2026-07", "fired_date": "2026-07-07", "pair": _VENUE,
         "signal_key": "venue_offshore_gap", "family": "venue", "sector_etf": None,
         "sector_en": "CSI 300 (onshore)", "sector_zh": "沪深300（境内）", "sign": "positive",
         "rs_at_fire": 5.5, "signal_value": 5.5},
    ], columns=_COLS)


def _track(tmp_path, monkeypatch):
    """track_record() over the synthetic parquet; resolution legs read no price data."""
    monkeypatch.setattr(rl, "_path", lambda: tmp_path / "ledger.parquet")
    monkeypatch.setenv("CN_LANE", "asia")
    monkeypatch.setattr(rl.store, "read", lambda group, name: None)
    _ledger_frame().to_parquet(tmp_path / "ledger.parquet", index=False)
    return rl.track_record()


def test_track_record_rows_have_no_nan_family(tmp_path, monkeypatch):
    track = _track(tmp_path, monkeypatch)
    rows = {r["pair"]: r for r in track["rows"]}
    assert rows[_LEGACY]["family"] is None            # was NaN — not strictly serializable
    assert rows[_VENUE]["family"] == "venue"          # the real tag is untouched


def test_ledger_emit_is_strict_json(tmp_path, monkeypatch):
    track = _track(tmp_path, monkeypatch)
    # the builder's exact call (scripts/build_china_radar.py:59-60)
    emit = json.dumps(track, ensure_ascii=False, separators=(",", ":"), default=str)
    assert "NaN" not in emit
    assert "Infinity" not in emit

    def _reject(name):
        raise ValueError(f"emit is not strict JSON: {name}")

    parsed = json.loads(emit, parse_constant=_reject)   # must not raise
    families = {r["pair"]: r["family"] for r in parsed["rows"]}
    assert families[_LEGACY] is None and families[_VENUE] == "venue"


def test_venue_dispatch_still_routes_on_family(tmp_path, monkeypatch):
    """The venue row still resolves through _fwd_venue, the legacy row through _fwd_rel."""
    seen = []

    def _venue(pair, sign, fired, horizon=rl.HORIZON_DAYS):
        seen.append(("venue", pair))
        return -1.75

    def _rel(etf, fired, horizon=rl.HORIZON_DAYS):
        seen.append(("rel", etf))
        return 16.94

    monkeypatch.setattr(rl, "_fwd_venue", _venue)
    monkeypatch.setattr(rl, "_fwd_rel", _rel)
    monkeypatch.setattr(rl, "_path", lambda: tmp_path / "ledger.parquet")
    monkeypatch.setenv("CN_LANE", "asia")
    _ledger_frame().to_parquet(tmp_path / "ledger.parquet", index=False)
    track = rl.track_record()
    assert ("venue", _VENUE) in seen
    assert ("rel", "512800.SS") in seen
    assert ("rel", None) not in seen                  # the venue row never took the ETF leg
    rows = {r["pair"]: r for r in track["rows"]}
    assert rows[_VENUE]["family"] == "venue" and rows[_VENUE]["status"] == "miss"
    assert rows[_LEGACY]["family"] is None            # not the string "nan"
    assert rows[_LEGACY]["status"] == "miss" and rows[_LEGACY]["fwd_rel"] == 16.94
    assert track["n_resolved"] == 2 and track["hit_rate"] == 0.0
