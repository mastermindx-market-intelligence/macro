"""SIC-D-B02 — settled-session generation guard tests.

Covers engine/sector_generation_guard.py, the compute()-level gate in
engine/sector_central.py, and the rotation_context stamp in
scripts/build_sector_cycles.py.  No network, no site files, no data/ ledger
reads — all loaders are monkeypatched.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import sector_generation_guard as sgg  # noqa: E402
from engine import sector_central as scg  # noqa: E402
from scripts import build_sector_cycles  # scripts  # noqa: E402


# ------------------------------------------------------------- pure guard ----

def test_friday_artifact_read_on_monday_is_aligned():
    """The old 48 h wall-clock rule rejected a settled Friday artifact read on
    Monday (ts age > 48 h).  Same settled session on both sides → aligned."""
    # 2026-10-16 is a Friday; the consumer spine is still Friday-settled on
    # Monday 2026-10-19 before the Monday session settles.
    out = sgg.session_alignment("2026-10-16", "2026-10-16", today=dt.date(2026, 10, 19))
    assert out["status"] == "aligned"
    assert out["reason"] == "aligned"
    assert out["artifact_session"] == "2026-10-16"
    assert out["consumer_session"] == "2026-10-16"
    assert out["clock"] == "settled_daily_session"


def test_holiday_gap_is_aligned():
    """Artifact and consumer both on the last session before a US holiday
    (Wed 2026-11-25 before Thanksgiving Thu 2026-11-26), read three days
    later — no wall-clock age rule fires."""
    out = sgg.session_alignment("2026-11-25", "2026-11-25", today=dt.date(2026, 11, 28))
    assert (out["status"], out["reason"]) == ("aligned", "aligned")


def test_future_session_rejected():
    out = sgg.session_alignment("2026-10-22", "2026-10-19", today=dt.date(2026, 10, 20))
    assert (out["status"], out["reason"]) == ("incompatible_generation", "future_session")


def test_missing_session_values():
    for art in (None, "", "   "):
        out = sgg.session_alignment(art, "2026-10-19")
        assert (out["status"], out["reason"]) == ("missing_input", "missing_session"), art
        assert out["artifact_session"] is None
    out = sgg.session_alignment("2026-10-16", None)
    assert (out["status"], out["reason"]) == ("missing_input", "missing_session")
    assert out["consumer_session"] is None and out["artifact_session"] == "2026-10-16"


def test_unparseable_session_string():
    out = sgg.session_alignment("not-a-date", "2026-10-19")
    assert (out["status"], out["reason"]) == ("invalid_payload", "invalid_session")
    out2 = sgg.session_alignment("2026-10-16", 20261019)
    assert (out2["status"], out2["reason"]) == ("invalid_payload", "invalid_session")


def test_iso_datetime_reduced_to_date_part():
    assert sgg.parse_session("2026-10-16T14:30:00Z") == dt.date(2026, 10, 16)
    assert sgg.parse_session("2026-10-16T22:00:00+00:00") == dt.date(2026, 10, 16)
    assert sgg.parse_session(dt.datetime(2026, 10, 19, 9, 30)) == dt.date(2026, 10, 19)
    # the date part is taken, never the wall clock → same-day datetime aligns
    out = sgg.session_alignment("2026-10-16T22:00:00+00:00", "2026-10-16")
    assert (out["status"], out["reason"]) == ("aligned", "aligned")


def test_oct19_oct16_counterexample_is_as_of_mismatch():
    """The measured masterplan §6.2 case: cycles payload as of 2026-10-19,
    rotation artifact as of 2026-10-16."""
    out = sgg.session_alignment("2026-10-16", "2026-10-19")
    assert (out["status"], out["reason"]) == ("incompatible_generation", "as_of_mismatch")
    assert out["artifact_session"] == "2026-10-16"
    assert out["consumer_session"] == "2026-10-19"


def test_artifact_newer_than_consumer():
    out = sgg.session_alignment("2026-10-20", "2026-10-19")
    assert (out["status"], out["reason"]) == ("incompatible_generation", "artifact_newer_than_consumer")


# ------------------------------------------------- compute()-level (Central) ----

def _minimal_cyc():
    return {"meta": {"asOf": "2026-10-19"},
            "sectors": [
                {"id": "us_sector_tech", "kind": "sector", "ticker": "XLK",
                 "name": "Technology", "now": {}},
                {"id": "us_sector_energy", "kind": "sector", "ticker": "XLE",
                 "name": "Energy", "now": {}},
            ],
            "baskets": []}


def _central_seams(monkeypatch, artifact):
    monkeypatch.setattr(scg, "_load_rotation_artifact", lambda: artifact)
    monkeypatch.setattr(scg, "market_context", lambda: {"risk_on": 0.0, "gate_factor": 0.7, "heat": {}})
    monkeypatch.setattr(scg, "_trend_gates", lambda closes, rotation: {})
    monkeypatch.setattr(scg, "_measured_read", lambda cyc: {"status": "unavailable"})
    import engine.sector_cycles as _sc
    monkeypatch.setattr(_sc, "compute", lambda: _minimal_cyc())
    seen = []
    real_attach = scg._attach_rotation
    def _rec(records, rotation_raw, kind):
        seen.append(rotation_raw)
        return real_attach(records, rotation_raw, kind=kind)
    monkeypatch.setattr(scg, "_attach_rotation", _rec)
    return seen


def test_central_compute_oct16_artifact_keeps_conviction_order(monkeypatch, tmp_path):
    """compute()-level Oct19/Oct16: sectors keep conviction order, carry no
    rotation block, meta carries the typed mismatch."""
    monkeypatch.setattr(scg.config, "data_dir", lambda: tmp_path)
    artifact = {"asof": "2026-10-16", "ts": "2026-10-16T22:00:00+00:00",
                "session": "2026-10-16", "clock": "settled_daily_session",
                "instruments": [{"id": "us_sector_tech", "kind": "sector",
                                 "rotation_rank": 1, "rotation_score": 0.9}]}
    seen = _central_seams(monkeypatch, artifact)
    out = scg.compute()
    assert out is not None
    align = out["meta"]["rotation_alignment"]
    assert (align["status"], align["reason"]) == ("incompatible_generation", "as_of_mismatch")
    assert align["artifact_session"] == "2026-10-16" and align["consumer_session"] == "2026-10-19"
    assert align["artifact_generated_at"] == "2026-10-16T22:00:00+00:00"
    assert out["meta"]["rotation_alignment_version"] == 1
    assert out["market"]["rotation_board_order"] == "conviction"
    assert out["meta"]["board_order"] == "conviction"
    # no rotation block on any record; conviction order kept
    for s in out["sectors"]:
        assert not s.get("rotation")
    scores = [s["conviction"]["score"] for s in out["sectors"]]
    assert scores == sorted(scores, reverse=True)
    # the raw artifact never reached _attach_rotation — only the emptied dict did
    assert seen and all(raw == {} for raw in seen), seen


def test_central_compute_aligned_artifact_attaches(monkeypatch, tmp_path):
    monkeypatch.setattr(scg.config, "data_dir", lambda: tmp_path)
    artifact = {"asof": "2026-10-19", "session": "2026-10-19",
                "clock": "settled_daily_session",
                "ts": "2026-10-19T22:00:00+00:00",
                "instruments": [{"id": "us_sector_tech", "kind": "sector",
                                 "rotation_rank": 1, "rotation_score": 0.9}]}
    seen = _central_seams(monkeypatch, artifact)
    out = scg.compute()
    assert out is not None
    assert out["meta"]["rotation_alignment"]["status"] == "aligned"
    assert out["market"]["rotation_board_order"] == "fast-lens"
    assert any(raw == artifact for raw in seen), seen


# ------------------------------------------- Cycles rotation_context stamp ----

def _cycles_payload():
    return {"schema": "sector_cycles.v9", "meta": {"asOf": "2026-10-19"},
            "sectors": [{"id": "us_sector_tech"}], "baskets": []}


def _events(as_of="2026-10-19", ok=True, schema="rotation_events.v1", active=None):
    return {"schema": schema, "ok": ok, "as_of": as_of,
            "active": active if active is not None else [{"sector": "tech"}]}


def _frag(as_of="2026-10-19"):
    return {"schema": "sector_fragmentation.v1", "ok": True, "as_of": as_of,
            "sectors": [{"key": "tech", "spread": 0.4}]}


def _write_site(tmp_path, events=None, frag=None):
    md = tmp_path / "marketdata"
    md.mkdir(parents=True, exist_ok=True)
    if events is not None:
        (md / "rotation_events.json").write_text(json.dumps(events), encoding="utf-8")
    if frag is not None:
        (md / "sector_fragmentation.json").write_text(json.dumps(frag), encoding="utf-8")
    return tmp_path


def test_cycles_rotation_context_aligned(tmp_path):
    root = _write_site(tmp_path, events=_events(), frag=_frag())
    payload = _cycles_payload()
    build_sector_cycles._stamp_rotation_context(payload, site_root=root)
    ctx = payload["rotation_context"]
    assert ctx["schema"] == "sector_cycles.rotation_context.v1"
    assert ctx["events"]["status"] == "aligned" and ctx["events"]["active"] == [{"sector": "tech"}]
    assert ctx["events"]["clock"] == "settled_daily_session"
    assert ctx["fragmentation"]["status"] == "aligned"
    assert ctx["fragmentation"]["sectors"] == [{"key": "tech", "spread": 0.4}]
    assert payload["rotation_alignment_version"] == 1


def test_cycles_rotation_context_mismatched(tmp_path):
    root = _write_site(tmp_path, events=_events(as_of="2026-10-16"), frag=_frag(as_of="2026-10-16"))
    payload = _cycles_payload()
    build_sector_cycles._stamp_rotation_context(payload, site_root=root)
    ctx = payload["rotation_context"]
    for sub in ("events", "fragmentation"):
        assert ctx[sub]["status"] == "incompatible_generation"
        assert ctx[sub]["reason"] == "as_of_mismatch"
    assert ctx["events"]["active"] is None and ctx["fragmentation"]["sectors"] is None


def test_cycles_rotation_context_missing_files(tmp_path):
    payload = _cycles_payload()
    build_sector_cycles._stamp_rotation_context(payload, site_root=tmp_path)
    ctx = payload["rotation_context"]
    for sub in ("events", "fragmentation"):
        assert ctx[sub]["status"] == "missing_input" and ctx[sub]["reason"] == "missing_input"
        assert ctx[sub].get("active", ctx[sub].get("sectors")) is None


def test_cycles_rotation_context_wrong_schema_events(tmp_path):
    root = _write_site(tmp_path, events=_events(schema="rotation_events.v0"), frag=_frag())
    payload = _cycles_payload()
    build_sector_cycles._stamp_rotation_context(payload, site_root=root)
    ctx = payload["rotation_context"]
    assert (ctx["events"]["status"], ctx["events"]["reason"]) == ("invalid_payload", "invalid_payload")
    assert ctx["events"]["active"] is None
    assert ctx["fragmentation"]["status"] == "aligned"  # unaffected sibling


def test_cycles_rotation_context_events_not_ok(tmp_path):
    root = _write_site(tmp_path, events=_events(ok=False), frag=_frag())
    payload = _cycles_payload()
    build_sector_cycles._stamp_rotation_context(payload, site_root=root)
    ctx = payload["rotation_context"]
    assert (ctx["events"]["status"], ctx["events"]["reason"]) == ("invalid_payload", "invalid_payload")
    assert ctx["events"]["active"] is None


def test_cycles_fragmentation_aligned_vs_mismatched(tmp_path):
    payload = _cycles_payload()
    build_sector_cycles._stamp_rotation_context(
        payload, site_root=_write_site(tmp_path, frag=_frag(as_of="2026-10-19")))
    assert payload["rotation_context"]["fragmentation"]["sectors"] == [{"key": "tech", "spread": 0.4}]
    payload2 = _cycles_payload()
    build_sector_cycles._stamp_rotation_context(
        payload2, site_root=_write_site(tmp_path, frag=_frag(as_of="2026-10-18")))
    assert payload2["rotation_context"]["fragmentation"]["status"] == "incompatible_generation"
    assert payload2["rotation_context"]["fragmentation"]["sectors"] is None


def test_rotation_context_exception_path_projects_error(tmp_path, monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("boom")
    monkeypatch.setattr(sgg, "session_alignment", _boom)
    payload = _cycles_payload()
    build_sector_cycles._stamp_rotation_context(
        payload, site_root=_write_site(tmp_path, events=_events(), frag=_frag()))
    assert payload["rotation_context"] == {"schema": "sector_cycles.rotation_context.v1",
                                           "status": "unavailable", "reason": "projection_error"}
    assert payload["rotation_alignment_version"] == 1


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
