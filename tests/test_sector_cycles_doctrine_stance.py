"""A2_D30: the Cycles stance chip renders the producer-stamped doctrine stance (SIC-ADJ-01).

``templates/sector_cycles.js`` reads ``now.doctrine_stance_en/zh`` + ``now.doctrine_ink`` (stamped by
engine/cycle_ontology.py ``doctrine_for``); the engine ``stance`` stays provenance and no renderer maps
stance -> doctrine. The raw BUY/SELL ``cc-sig`` chip is retired, and an unstamped payload draws
"Stance unavailable". The renderer helpers are pulled out of the IIFE by source text and run in a bare
node vm sandbox; a mutation control proves the harness fails on the pre-D30 (BASE) label.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from engine.cycle_ontology import STANCES, doctrine_for
from tests.test_sector_paper_copy_deck import _present, norm

ROOT = Path(__file__).resolve().parent.parent
JS = ROOT / "templates" / "sector_cycles.js"
CSS = ROOT / "templates" / "sector_cycles.css"
SRC = JS.read_text(encoding="utf-8")
LINES = SRC.split("\n")

# BASE 098637a4:templates/sector_cycles.js:204, verbatim — the label the mutation control must catch.
BASE_STANCE_LABEL = ('  function stanceLabel(nw) { return curLang() === "zh" ? (nw.stance_zh || nw.stance) : '
                     'nw.stance; }')

_RAW_EN = sorted({k for k in STANCES} | {v["en"] for v in STANCES.values()})
# 观望 / 准备 are substrings of the doctrine faces 暂时观望 / 做好准备, so they are checked by equality only.
_RAW_ZH_EQ_ONLY = {"观望", "准备"}
_RAW_ZH = sorted(v["zh"] for v in STANCES.values() if v["zh"] not in _RAW_ZH_EQ_ONLY)
_INK_CLS = {"ok": "st-ok", "warn": "st-caut", "muted": "st-neu"}


def _one_line(prefix: str) -> str:
    hits = [s for s in LINES if s.startswith(prefix)]
    assert len(hits) == 1, (prefix, len(hits))
    return hits[0]


def _block(head: str) -> str:
    i = LINES.index(head)
    j = LINES.index("  }", i)
    return "\n".join(LINES[i:j + 1])


def _helpers(stance_label: str | None = None) -> str:
    return "\n".join([
        _one_line("  function curLang() "),
        _one_line("  function L(en, zh) "),
        _one_line("  function esc(s) "),
        stance_label or _one_line("  function stanceLabel(nw) "),
        _block("  function stanceHTML(nw) {"),
        _one_line("  function scDoctrineInkCls(ink) "),
        _one_line("  function scStanceUnavailable() "),
    ])


_RUNNER = r"""
const fs = require('fs'), vm = require('vm');
const job = JSON.parse(fs.readFileSync(0, 'utf8'));
const out = job.cases.map(function (c) {
  const sb = { document: { documentElement: { getAttribute: function (a) { return a === 'data-lang' ? c.lang : null; } } } };
  vm.createContext(sb);
  vm.runInContext(job.src + '\nthis.__html = stanceHTML(' + JSON.stringify(c.nw) + ');', sb);
  return sb.__html;
});
process.stdout.write(JSON.stringify(out));
"""


def _render(cases, stance_label=None):
    proc = subprocess.run(["node", "-e", _RUNNER], input=json.dumps({"src": _helpers(stance_label), "cases": cases}),
                          capture_output=True, text=True, cwd=str(ROOT))
    assert proc.returncode == 0, proc.stderr[-2000:]
    return json.loads(proc.stdout)


def _fixture(key: str) -> dict:
    meta = STANCES[key]
    return {"stance": key, "stance_zh": meta["zh"], "tone": meta["tone"], **doctrine_for(key)}


def _text(html: str) -> str:
    return re.sub(r"<[^>]*>", "", html)


def _assert_doctrine_chips(stance_label=None, keys=None):
    keys = list(keys or STANCES)
    cases = [{"lang": lang, "nw": _fixture(k)} for lang in ("en", "zh") for k in keys]
    for case, html in zip(cases, _render(cases, stance_label)):
        nw, lang = case["nw"], case["lang"]
        want = nw["doctrine_stance_zh"] if lang == "zh" else nw["doctrine_stance_en"]
        assert _text(html) == want, (nw["stance"], lang, html)
        assert 'class="cc-stance ' + _INK_CLS[nw["doctrine_ink"]] + '"' in html, (nw["stance"], html)
        if lang == "en":
            for raw in _RAW_EN:
                assert re.search(r"(?<![0-9A-Za-z])" + re.escape(raw) + r"(?![0-9A-Za-z])", html) is None, (raw, html)
        else:
            for raw in _RAW_ZH:
                assert raw not in html, (raw, html)
            assert _text(html) not in _RAW_ZH_EQ_ONLY, html


# ---- (A) node: the chip is the stamped doctrine stance --------------------------------------------------
@pytest.mark.skipif(shutil.which("node") is None, reason="node is required to run the stance renderer")
def test_every_engine_stance_renders_its_stamped_doctrine_face_en_and_zh():
    assert len(STANCES) == 9
    _assert_doctrine_chips()


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required to run the stance renderer")
def test_unstamped_or_missing_now_draws_stance_unavailable():
    unstamped = {"stance": "BUY", "stance_zh": "买入", "tone": "bullish", "doctrine_stance": None,
                 "doctrine_stance_en": None, "doctrine_stance_zh": None, "doctrine_ink": None}
    cases = [{"lang": lang, "nw": nw} for lang in ("en", "zh") for nw in (unstamped, None)]
    out = _render(cases)
    for case, html in zip(cases, out):
        want = "立场不可用" if case["lang"] == "zh" else "Stance unavailable"
        assert html == '<span class="cc-stance-na">' + want + "</span>", (case, html)


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required to run the stance renderer")
def test_unknown_doctrine_ink_falls_back_to_neutral():
    nw = dict(_fixture("BUY"), doctrine_ink="bogus")
    (html,) = _render([{"lang": "en", "nw": nw}])
    assert 'class="cc-stance st-neu"' in html, html


# ---- (B) pure text: no raw chip, no renderer map, BASE ladder untouched ---------------------------------
def test_raw_signal_chip_literal_is_retired():
    assert 'class="cc-sig' not in SRC
    assert "<span class=\\\"cc-sig" not in SRC


def test_no_renderer_stance_to_doctrine_map():
    assert re.search(r"""(BUY|TRIM|SELL|AVOID)["']?\s*:\s*["'](act|protect|aside)""", SRC) is None


def test_tone_ladder_lines_carry_no_stance_run():
    window = norm("\n".join(LINES[196:203]))  # lines 197–203
    assert not _present(window, "stance"), window


def test_doctrine_ink_css_is_token_composed():
    css = CSS.read_text(encoding="utf-8")
    tail = css[css.index("/* A2_D30 doctrine ink"):]
    assert ".cc-stance.st-ok {" in tail and ".cc-stance-na {" in tail
    assert "--up" not in tail and "--down" not in tail
    assert "color-mix(" not in tail


# ---- (C) mutation control: the BASE label must fail the harness -----------------------------------------
@pytest.mark.skipif(shutil.which("node") is None, reason="node is required to run the stance renderer")
def test_mutation_control_base_stance_label_fails_on_buy():
    with pytest.raises(AssertionError) as exc:
        _assert_doctrine_chips(BASE_STANCE_LABEL, keys=["BUY"])
    assert "'BUY'" in str(exc.value) and "Act" in str(exc.value)


# ---- (D) the stamped label is text, never markup (PR #10777 review F7) ---------------------------------
@pytest.mark.skipif(shutil.which("node") is None, reason="node is required to run the stance renderer")
def test_stamped_doctrine_label_is_escaped():
    nw = dict(_fixture("BUY"), doctrine_stance_en="<b>x</b> & y", doctrine_stance_zh="<i>甲</i> & 乙")
    en_html, zh_html = _render([{"lang": "en", "nw": nw}, {"lang": "zh", "nw": nw}])
    assert "&lt;b&gt;x&lt;/b&gt; &amp; y" in en_html and "<b>" not in en_html, en_html
    assert "&lt;i&gt;甲&lt;/i&gt; &amp; 乙" in zh_html and "<i>" not in zh_html, zh_html
