"""W11 r3 — dealer-line absolute day-word + evidence-matrix receipts.

Packet: packet_intraday_flow.md REQUIRED EVIDENCE MATRIX plus the seat-added
dealer-line minor (same truth family as r2 B1). r1/r2 repairs stay frozen.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from tests.test_intraday_flow_w11_r1 import _region, _run_node, _src
from tests.test_intraday_flow_w11_r2 import RELATIVE_DAY, needs_node

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "intraday_flow.html.j2"
EVIDENCE = ROOT / "mockups" / "evidence" / "intraday-flow-w11"

# r2 stamp sweep plus the ZH day-word pair the dealer line actually used.
DEALER_BANNED = RELATIVE_DAY + ("今日", "昨日")


def _dealer_region(src: str) -> str:
    return _region(src, "function dealerCompact", "function detailContent")


def test_dealer_line_drops_relative_day_words_both_lanes():
    src = _src()
    region = _dealer_region(src)
    assert "% expected move" in region
    assert "预期波动约" in region
    assert "move today" not in region
    assert "今日约" not in region
    for word in DEALER_BANNED:
        assert word not in region, f"banned {word!r} still in dealerCompact"
    # ~ and fmtNum stay; daily-ness already lives on the existing Tier-2 row.
    assert "'~'+fmtNum(d.expected_move_daily_pct,1)+'% expected move'" in region
    assert "'~预期波动约'+fmtNum(d.expected_move_daily_pct,1)+'%'" in region
    assert "Expected move (day)" in src
    assert "预期波动（日）" in src


@needs_node
def test_dealer_compact_render_has_no_relative_day_words():
    src = _src()
    js = "\n".join((
        "function lz(en, zh){ return '<span class=\"l-en\">'+en+'</span><span class=\"l-zh\">'+(zh||en)+'</span>'; }",
        "function fmtNum(v, dec){ return (v==null||isNaN(v)) ? '—' : Number(v).toFixed(dec!=null?dec:2); }",
        _dealer_region(src),
    ))
    script = js + """
    var html = dealerCompact({
      regime: 'long',
      call_wall: 120,
      put_wall: 90,
      expected_move_daily_pct: 2.4,
      vol_hole_state: 'NONE'
    }, {price: 110});
    function pick(tag){
      var o=[], re=new RegExp('class="l-'+tag+'">([^<]*)','g'), m;
      while ((m=re.exec(html))) o.push(m[1]);
      return o.join(' | ');
    }
    process.stdout.write(JSON.stringify({html: html, en: pick('en'), zh: pick('zh')}));
    """
    out = _run_node(script)
    assert "~2.4% expected move" in out["en"]
    assert "~预期波动约2.4%" in out["zh"]
    blob = out["html"] + out["en"] + out["zh"]
    for word in DEALER_BANNED:
        assert word not in blob, f"banned {word!r} leaked into dealerCompact render"


def test_r2_stamp_banned_word_sweep_extends_to_dealer_line():
    """Same instrument as r2's stamp sweep, pointed at dealerCompact."""
    src = _src()
    stamp = _region(src, 'id="ift-stamp"', "</header>")
    dealer = _dealer_region(src)
    for word in DEALER_BANNED:
        assert word not in stamp
        assert word not in dealer


def test_evidence_home_names_both_art_directions_and_fixture_n():
    readme = (EVIDENCE / "README.md").read_text(encoding="utf-8")
    assert "DARK TREATMENT" in readme
    assert "LIGHT TREATMENT" in readme
    assert "Which mechanisms intentionally differ" in readme or "intentionally differ" in readme
    assert re.search(r"fixture N\s*=\s*\d+", readme, re.I)
    assert "overlay-clean" in readme
    receipt = EVIDENCE / "EVIDENCE.yml"
    assert receipt.is_file()
    yml = receipt.read_text(encoding="utf-8")
    assert "mastermind.page_evidence_receipt.v1" in yml
    assert "templates/intraday_flow.html.j2" in yml
    manifest = json.loads((EVIDENCE / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "mastermind.p0_evidence.v2"
    rest = [
        s
        for page in manifest["pages"]
        for s in page.get("states") or []
        if s.get("captured") and not s.get("force_state")
    ]
    # 16 rest cells: (hero|board) × dark/light × EN/ZH × desktop/mobile.
    themes = {(s.get("theme"), s.get("locale"), s.get("viewport")) for s in rest}
    assert len(themes) == 8, themes
    assert len(rest) == 16, len(rest)


def test_evidence_cells_carry_overlay_clean_column():
    cells = json.loads((EVIDENCE / "cells.json").read_text(encoding="utf-8"))
    rows = cells["cells"] if isinstance(cells, dict) else cells
    assert rows, "no evidence cells"
    dirty = [c["id"] for c in rows if not c.get("overlay_clean")]
    assert not dirty, f"overlay-dirty cells: {dirty}"
    p0 = [c for c in rows if c.get("state") == "d-quotes-outage"]
    assert p0, "missing P0 quotes-outage cells"
    for cell in p0:
        hits = cell.get("live_hits") or []
        stamp_hits = [h for h in hits if h.get("in_stamp")]
        assert not stamp_hits, stamp_hits
        pricing = [
            h for h in hits
            if re.search(r"\blive\b|实时", h.get("text") or "")
            and "setups live" not in (h.get("text") or "")
            and "非实时" not in (h.get("text") or "")
            and "not a live signal" not in (h.get("text") or "")
        ]
        assert not pricing, pricing
