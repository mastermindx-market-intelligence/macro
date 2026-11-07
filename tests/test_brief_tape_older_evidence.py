"""A2_D21: the Brief tape says when it is showing older evidence than the page.

The page hero carries the build's ``data-si-as-of`` (``source_as_of``). When the
tape's own quote date is more than five days older than that, both tape
renderers (``renderTapeStrip`` and ``renderSlimStrip``) append one existing
``mr-chip-stale`` chip using the frozen deck pair ``states.stale_title`` with
``states.stale_body`` as its tip. A missing or unparsable date shows nothing
(fail closed); exactly five days shows nothing.

The tape's own intraday stale guard (``_dtpState``) is armor and must stay
byte-identical to BASE 098637a4; ``tests/test_ftr_w3_ui.py`` extracts it.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "sector_central.html.j2"
DECK = ROOT / "design_refs" / "sector-paper-20261021" / "copy_deck.json"

CHIP = (
    ' <span class="mr-chip mr-chip-stale" '
    'data-tip-en="Observation is no longer current." '
    'data-tip-zh="观测已过期。">'
    '<span class="l-en">Older evidence shown</span>'
    '<span class="l-zh">显示较早证据</span></span>'
)
THRESHOLD = "<=5*864e5"
CALL_TAIL = "+_tapeOlderNote(pulse); }"

# BASE 098637a4 text of the tape's intraday stale guard (armor).
_BASE_ARMOR = (
    "    var builtMs=Date.parse(pulse.as_of_utc||'');",
    "    var stale=isFinite(builtMs)&&(Date.now()-builtMs)>12*3600e3;",
)
_BASE_DTP_STATE = (
    '  function _dtpState(pulse){\n'
    "    var mode    = pulse.mode||'live';\n"
    "    var session = pulse.session||'closed';\n"
    '    var ts      = pulse.as_of_quotes||pulse.as_of_utc;\n'
    "    var asofStr = '';\n"
    '    /* >12h staleness guard (weekend/holiday frozen file) — a stale file describes\n'
    '       a finished session; never label it live or post-market */\n'
    "    var builtMs=Date.parse(pulse.as_of_utc||'');\n"
    '    var stale=isFinite(builtMs)&&(Date.now()-builtMs)>12*3600e3;\n'
    '    if(ts){\n'
    '      try{\n'
    '        if(ts.length<=10){ asofStr=ts; }\n'
    "        else if(stale||(mode==='last_rth'&&pulse.settled_close)){\n"
    "          asofStr=new Date(ts).toLocaleString([],{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',timeZoneName:'short'});\n"
    '        } else {\n'
    "          asofStr=new Date(ts).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',timeZoneName:'short'});\n"
    '        }\n'
    '      }catch(e){asofStr=ts;}\n'
    '    }\n'
    '    if(stale){\n'
    "      if(mode==='live'||mode==='delayed'){ pulse.mode='last_rth'; }\n"
    "      return {cls:'closed', en:'LAST SESSION · SETTLED', zh:'上一交易时段 · 已收盘', asofStr:asofStr, live:false};\n"
    '    }\n'
    "    if(mode==='live'){\n"
    "      if(session==='pre')\n"
    "        return {cls:'pre', en:'PREMARKET · 15-MIN DELAYED', zh:'盘前 · 15分钟延迟', asofStr:asofStr, live:true};\n"
    "      return {cls:'live', en:'LIVE · 15-MIN DELAYED', zh:'实盘 · 15分钟延迟', asofStr:asofStr, live:true};\n"
    '    }\n'
    "    if(mode==='last_rth'){\n"
    '      if(pulse.settled_close)\n'
    "        return {cls:'post', en:'POST-MARKET · SETTLED CLOSE', zh:'盘后 · 当日收盘', asofStr:asofStr, live:false};\n"
    "      return {cls:'post', en:'LAST SESSION', zh:'上一交易时段', asofStr:asofStr, live:false};\n"
    '    }\n'
    "    if(mode==='eod')\n"
    "      return {cls:'closed', en:'LAST SESSION', zh:'上一交易时段', asofStr:asofStr, live:false};\n"
    "    if(mode==='delayed'){\n"
    '      var h=pulse.delay_min_median!=null?Math.round(pulse.delay_min_median/60):0;\n'
    "      return {cls:'warn', en:'DELAYED · ~'+h+'h', zh:'延迟 · 约'+h+'小时', asofStr:asofStr, live:false};\n"
    '    }\n'
    "    return {cls:'closed', en:'LAST SESSION', zh:'上一交易时段', asofStr:asofStr, live:false};\n"
    '  }'
)


def _src() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def _one_line(pattern: str) -> str:
    found = re.findall(pattern, _src(), re.M)
    assert len(found) == 1, (pattern, len(found))
    return found[0]


def _helper_source() -> str:
    return _one_line(r"^  (function _tapeOlderNote\(pulse\)\{.*\})$")


def _l_source() -> str:
    return _one_line(r"^  (function L\(en,zh\)\{.*\})$")


def _dtp_state_block() -> str:
    lines = _src().split("\n")
    start = lines.index("  function _dtpState(pulse){")
    end = lines.index("  }", start)
    return "\n".join(lines[start:end + 1])


def _require_node() -> None:
    if shutil.which("node"):
        return
    pytest.skip("node is not on PATH locally")


def _note(page, pulse, helper: str | None = None) -> str:
    """Evaluate the template's _tapeOlderNote with a stubbed hero element."""
    _require_node()
    script = "var PAGE=" + json.dumps(page) + ";\n"
    script += "var document={querySelector:function(sel){"
    script += "if(sel!=='.rvx-hero[data-si-as-of]')throw new Error('selector '+sel);"
    script += "if(PAGE===null)return null;"
    script += "return {getAttribute:function(k){return k==='data-si-as-of'?PAGE:null;}};}};\n"
    script += _l_source() + "\n" + (helper or _helper_source()) + "\n"
    script += "process.stdout.write(JSON.stringify(_tapeOlderNote("
    script += json.dumps(pulse) + ")));\n"
    env = dict(os.environ)
    env["TZ"] = "UTC"
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True,
                         env=env, check=True, timeout=30)
    return json.loads(out.stdout)


PAGE = "2026-11-02T21:40:00Z"


@pytest.mark.parametrize(
    "pulse",
    [
        {"as_of_quotes": "2026-10-30T20:00:00Z"},
        {"as_of_quotes": "2026-10-29T20:00:00Z"},
        {"as_of_quotes": "2026-10-28T20:00:00Z"},
        {"as_of_utc": "2026-11-02T20:00:00Z"},
    ],
    ids=["3-days", "4-days", "exactly-5-days", "same-day"],
)
def test_recent_tape_shows_no_chip(pulse):
    assert _note(PAGE, pulse) == ""


@pytest.mark.parametrize(
    "pulse",
    [
        {"as_of_quotes": "2026-10-27T20:00:00Z"},
        {"as_of_quotes": "2026-10-01T20:00:00Z"},
        {"as_of_utc": "2026-10-20T20:00:00Z"},
    ],
    ids=["6-days", "a-month", "utc-fallback"],
)
def test_older_tape_shows_the_deck_chip(pulse):
    assert _note(PAGE, pulse) == CHIP


@pytest.mark.parametrize(
    ("page", "pulse"),
    [
        (None, {"as_of_quotes": "2026-10-01T20:00:00Z"}),
        ("", {"as_of_quotes": "2026-10-01T20:00:00Z"}),
        ("not-a-date", {"as_of_quotes": "2026-10-01T20:00:00Z"}),
        (PAGE, {"as_of_quotes": "n/a"}),
        (PAGE, {}),
        (PAGE, None),
    ],
    ids=["no-hero", "empty-attr", "bad-page", "bad-tape", "no-tape-date", "no-pulse"],
)
def test_missing_or_unparsable_dates_fail_closed(page, pulse):
    assert _note(page, pulse) == ""


def test_quote_date_wins_over_build_time():
    assert _note(PAGE, {"as_of_quotes": "2026-10-30T20:00:00Z",
                        "as_of_utc": "2026-10-20T20:00:00Z"}) == ""
    assert _note(PAGE, {"as_of_quotes": "2026-10-20T20:00:00Z",
                        "as_of_utc": "2026-11-01T20:00:00Z"}) == CHIP


def test_threshold_mutation_is_caught():
    """A six-day threshold must lose the six-day chip (mutation control)."""
    helper = _helper_source()
    assert helper.count(THRESHOLD) == 1
    mutant = helper.replace(THRESHOLD, "<=6*864e5")
    six_days = {"as_of_quotes": "2026-10-27T20:00:00Z"}
    assert _note(PAGE, six_days) == CHIP
    assert _note(PAGE, six_days, helper=mutant) == ""


def test_both_tape_renderers_append_the_note():
    calls = [l for l in _src().split("\n") if "asofEl.innerHTML=" in l and "_tapeOlderNote" in l]
    assert len(calls) == 2
    assert all(l.endswith(CALL_TAIL) for l in calls)
    assert _src().count("_tapeOlderNote(") == 3


def test_chip_uses_existing_style_and_hero_attribute():
    src = _src()
    assert ".mr-chip-stale{" in src
    assert re.search(r'<section class="rvx-hero[^"]*"[^>]*\n?\s*data-si-as-of="', src)


def test_chip_strings_are_the_frozen_deck_pair():
    states = json.loads(DECK.read_text(encoding="utf-8"))["states"]
    title, body = states["stale_title"], states["stale_body"]
    helper = _helper_source()
    assert "L(" + repr(title["en"]) + "," + repr(title["zh"]) + ")" in helper
    assert 'data-tip-en="' + body["en"] + '"' in helper
    assert 'data-tip-zh="' + body["zh"] + '"' in helper


def test_tape_stale_guard_is_byte_identical_to_base():
    block = _dtp_state_block()
    assert block == "".join(_BASE_DTP_STATE)
    for line in _BASE_ARMOR:
        assert _src().count(line) == 1
        assert line in block
    assert "_tapeOlderNote" not in block
