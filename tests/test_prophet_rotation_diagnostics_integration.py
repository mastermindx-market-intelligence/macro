"""Existing admin panel consumes the diagnostic adapter without a data writer."""
from __future__ import annotations
import hashlib
import json
from admin import prophet


def _audit():
    return {
        "schema": "prophet_miss_audit/v1", "price_through": "2026-09-14",
        "summary": {"universe_n": 1496, "top63_n": 150, "top21_n": 50},
        "themes": {"standouts_asof": "2026-09-11", "rotation_asof": "2026-09-11"},
        "conversion": {"sighted_n": 124, "converted_n": 21, "rate": 0.1694},
        "basket_misses": {"available": True, "as_of": "2026-09-14",
            "standouts_asof": "2026-09-11", "baskets": [{
                "basket_id": "energy_complex", "name": "US Energy Complex",
                "as_of": "2026-09-14", "members_on_board": ["DINO", "VLO"],
                "present_counts": {"buy": 0, "watch": 0, "leaders": 2, "ran": 0}}]},
    }


def test_real_panel_reads_exact_audit_and_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(prophet, "_fable_spend", lambda *a: {})
    path = tmp_path / "data/prophet_miss_audit/latest.json"
    path.parent.mkdir(parents=True)
    raw = json.dumps(_audit()).encode()
    path.write_bytes(raw)
    before = {str(p.relative_to(tmp_path)): p.read_bytes()
              for p in tmp_path.rglob("*") if p.is_file()}
    payload = prophet.panel(tmp_path)
    diag = payload["rotation_diagnostics"]
    assert payload["ok"] is True and diag["available"] is True
    assert diag["source"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert diag["dates_aligned"] is False
    assert diag["baskets"][0]["visibility"] == "leader_only"
    assert diag["baskets"][0]["entry_actionability"] == "not_measured"
    assert diag["conversion"]["on_time_rate"] is None
    assert diag["conversion"]["legacy_rate"] == 0.1694
    json.dumps(payload, allow_nan=False)
    after = {str(p.relative_to(tmp_path)): p.read_bytes()
             for p in tmp_path.rglob("*") if p.is_file()}
    assert after == before


def test_panel_retains_all_existing_fields_when_source_is_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(prophet, "_fable_spend", lambda *a: {})
    payload = prophet.panel(tmp_path)
    diag = payload.pop("rotation_diagnostics")
    assert diag["available"] is False and diag["status"] == "unavailable"
    assert diag["conversion"]["on_time_rate"] is None
    assert set(payload) == {"ok", "prophet_status", "suggestions", "fitness",
        "audit_state", "postmortems", "postmortems_note", "pick_autopsies",
        "pick_autopsies_note", "track_record", "learning_loop", "learning_loop_note",
        "fable_spend", "settings"}
    assert payload["ok"] is True
    assert list(tmp_path.iterdir()) == []
