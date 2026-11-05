"""B10 — Sector Central publishes a typed record of what it consumed.

The free artifacts (site/sector_central_data.js + site/sectordata/sector_central.json)
must carry data["publication"] (schema sector_central.publication.v1): one status
per secondary source with the failure MODE preserved — absent vs malformed vs
read_error vs ok, never collapsed into "empty" — plus the premium-payload twin
facts, the history mode and the correction contract.

Pins:
  * `_read_secondary` distinguishes absent / bad-JSON / JSON-non-object /
    unreadable / good, and stamps sha256 + as_of on the good path;
  * a stubbed main() run publishes the record with per-source statuses that
    match the fixtures (malformed si_handoff ≠ absent baskets);
  * no withheld (_sc_locked) row id ever lands in the free files;
  * the free JSON and the free JS carry the same as_of.
"""
from __future__ import annotations

import json

import pytest


# ── config pointing at tmp_path ───────────────────────────────────────────────

def _point_config(monkeypatch, tmp_path, *, gated=True, preview_rows=1) -> None:
    import lib.config as config_mod
    monkeypatch.setattr(config_mod, "ROOT", tmp_path)
    monkeypatch.setattr(
        config_mod, "load",
        lambda: {"storage": {"site_dir": "site"},
                 "sector_central_gate": {"gated": gated, "preview_rows": preview_rows}})


# ── _read_secondary unit matrix ───────────────────────────────────────────────

def test_read_secondary_absent(tmp_path, monkeypatch):
    _point_config(monkeypatch, tmp_path)
    from scripts.build_sector_central import _read_secondary

    doc, info = _read_secondary(tmp_path / "site" / "basketdata" / "si_handoff.json")
    assert doc is None
    assert info["status"] == "absent"
    assert info["path"] == "basketdata/si_handoff.json"
    assert info["sha256"] is None and info["as_of"] is None and info["error"] is None


def test_read_secondary_malformed_bad_json(tmp_path, monkeypatch):
    _point_config(monkeypatch, tmp_path)
    from scripts.build_sector_central import _read_secondary

    p = tmp_path / "site" / "basketdata" / "si_handoff.json"
    p.parent.mkdir(parents=True)
    p.write_bytes(b"{not json")
    doc, info = _read_secondary(p)
    assert doc is None
    assert info["status"] == "malformed"
    assert info["error"] == "JSONDecodeError"
    assert info["sha256"], "malformed bytes are still hashed — the generation is identified"


def test_read_secondary_malformed_json_list(tmp_path, monkeypatch):
    """A valid JSON document whose top level is not an object is malformed, not ok."""
    _point_config(monkeypatch, tmp_path)
    from scripts.build_sector_central import _read_secondary

    p = tmp_path / "site" / "basketdata" / "action_board.json"
    p.parent.mkdir(parents=True)
    p.write_bytes(b"[1, 2, 3]")
    doc, info = _read_secondary(p)
    assert doc is None
    assert info["status"] == "malformed"
    assert info["error"] == "list"


def test_read_secondary_read_error(tmp_path, monkeypatch):
    """An OS-level read failure (here: a directory) is read_error, not absent."""
    _point_config(monkeypatch, tmp_path)
    from scripts.build_sector_central import _read_secondary

    p = tmp_path / "site" / "basketdata" / "baskets.json"
    p.parent.mkdir(parents=True)
    p.mkdir()  # read_bytes() on a directory → IsADirectoryError
    doc, info = _read_secondary(p)
    assert doc is None
    assert info["status"] == "read_error"
    assert info["error"] == "IsADirectoryError"
    assert info["sha256"] is None


def test_read_secondary_ok(tmp_path, monkeypatch):
    _point_config(monkeypatch, tmp_path)
    from scripts.build_sector_central import _read_secondary

    p = tmp_path / "site" / "basketdata" / "action_board.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"as_of": "2026-10-18", "action_board": {}}), encoding="utf-8")
    doc, info = _read_secondary(p)
    assert doc == {"as_of": "2026-10-18", "action_board": {}}
    assert info["status"] == "ok"
    assert info["path"] == "basketdata/action_board.json"
    assert len(info["sha256"]) == 64 and info["as_of"] == "2026-10-18"
    assert info["error"] is None


def test_read_secondary_ok_generated_utc_fallback(tmp_path, monkeypatch):
    _point_config(monkeypatch, tmp_path)
    from scripts.build_sector_central import _read_secondary

    p = tmp_path / "site" / "basketdata" / "si_handoff.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"generated_utc": "2026-10-18T01:02:03Z"}), encoding="utf-8")
    doc, info = _read_secondary(p)
    assert info["status"] == "ok"
    assert info["as_of"] == "2026-10-18T01:02:03Z"


# ── main() end-to-end with stubbed engine / grader / template env ────────────

class _StubTemplate:
    def render(self, **kwargs):
        return "<html>stub</html>"


class _StubEnvironment:
    def __init__(self, *args, **kwargs):
        self.globals = {}

    def get_template(self, name):
        return _StubTemplate()


_LOCKED_IDS = ("LOCKED-ROW-B", "LOCKED-ROW-C")


def _run_main(monkeypatch, tmp_path, *, si_handoff_bytes: bytes | None) -> int:
    """Drive scripts.build_sector_central.main() against a tmp site with the
    engine, the grader, the flows board, the accumulation panel and the Jinja
    environment stubbed. Returns main()'s exit code."""
    import scripts.build_sector_central as bsc

    _point_config(monkeypatch, tmp_path)
    site = tmp_path / "site"
    (site / "basketdata").mkdir(parents=True, exist_ok=True)

    # action_board.json: 3 buy_now rows, preview_rows=1 → rows 2-3 are withheld
    board = {"as_of": "2026-10-18", "action_board": {"buy_now": [
        {"slug": "FREE-ROW-A", "name": "Free Row A"},
        {"slug": "LOCKED-ROW-B", "name": "Locked Row B"},
        {"slug": "LOCKED-ROW-C", "name": "Locked Row C"},
    ]}}
    (site / "basketdata" / "action_board.json").write_text(
        json.dumps(board), encoding="utf-8")
    if si_handoff_bytes is not None:
        (site / "basketdata" / "si_handoff.json").write_bytes(si_handoff_bytes)
    # baskets.json deliberately NOT written → status "absent"

    import engine.sector_central as sc
    monkeypatch.setattr(sc, "compute", lambda: {
        "as_of": "2026-10-18", "asof": "2026-10-18",
        "sectors": [{"id": "xlk", "name": "Technology", "conviction": "hold"}],
        "baskets": [],
    })
    import engine.sector_central_grader as cg
    monkeypatch.setattr(cg, "append_central_log", lambda data: 0)
    monkeypatch.setattr(cg, "grade", lambda: {"available": True})

    monkeypatch.setattr(bsc, "Environment", _StubEnvironment)
    monkeypatch.setattr(bsc, "_flows_section_html", lambda: "<div>flows</div>")
    monkeypatch.setattr(bsc, "_accumulation_rows", lambda: ([], None))
    return bsc.main()


def test_main_publishes_typed_secondary_statuses(tmp_path, monkeypatch):
    rc = _run_main(monkeypatch, tmp_path, si_handoff_bytes=b"{not json")
    assert rc == 0

    site = tmp_path / "site"
    free = json.loads((site / "sectordata" / "sector_central.json").read_text(encoding="utf-8"))
    pub = free["publication"]
    assert pub["schema"] == "sector_central.publication.v1"
    assert pub["as_of"] == "2026-10-18" == free["as_of"]
    assert pub["built_utc"].endswith("Z")

    sources = pub["secondary_sources"]
    # the record distinguishes malformed from absent — the pre-B10 builder logged
    # both as the same warning and rendered the same fallback
    assert sources["si_handoff"]["status"] == "malformed"
    assert sources["si_handoff"]["error"] == "JSONDecodeError"
    assert sources["si_handoff"]["path"] == "basketdata/si_handoff.json"
    assert sources["baskets"]["status"] == "absent"
    assert sources["action_board"]["status"] == "ok"
    assert sources["action_board"]["sha256"] and sources["action_board"]["as_of"] == "2026-10-18"
    assert sources["flows_html"]["status"] == "ok"
    assert sources["grader"]["status"] == "ok"

    assert pub["premium_payload"] == {
        "path": "premiumdata/sector_central.json",
        "written": True,
        "withheld_rows": 2,
    }
    assert pub["history_mode"] == "observed_at_build"
    assert pub["correction_contract"]["status"] == "none_native"
    assert "correction" in pub["correction_contract"]["basis"].lower()

    # the premium twin exists and is the tier payload
    prem = json.loads((site / "premiumdata" / "sector_central.json").read_text(encoding="utf-8"))
    assert prem["schema"] == "tier_payload.v1"
    assert prem["panels"]["actnow"]["locked"] == 2


def test_main_free_js_and_json_carry_same_as_of_and_no_locked_rows(tmp_path, monkeypatch):
    rc = _run_main(monkeypatch, tmp_path, si_handoff_bytes=None)  # absent si_handoff
    assert rc == 0

    site = tmp_path / "site"
    js_text = (site / "sector_central_data.js").read_text(encoding="utf-8")
    assert js_text.startswith("window.SECTOR_CENTRAL=")
    js_data = json.loads(js_text[len("window.SECTOR_CENTRAL="):].rstrip(";\n"))
    json_text = (site / "sectordata" / "sector_central.json").read_text(encoding="utf-8")
    free = json.loads(json_text)

    assert js_data["as_of"] == free["as_of"] == free["publication"]["as_of"]
    assert js_data["publication"]["schema"] == free["publication"]["schema"]

    # no withheld row id in either free artifact — the split is the gate
    for locked_id in _LOCKED_IDS:
        assert locked_id not in js_text, f"{locked_id} leaked into the free JS"
        assert locked_id not in json_text, f"{locked_id} leaked into the free JSON"

    # absent si_handoff is recorded as absent (not malformed)
    assert free["publication"]["secondary_sources"]["si_handoff"]["status"] == "absent"
