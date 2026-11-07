"""tests/test_risk_state_live_session_floor.py — the live patchers must never drag a
rendered board BACKWARDS onto an older session.

The 2026-08-02 operator report: macro.html showed a 44 / Mixed gauge beside a path
chart whose Jul 31 endpoint sat at 66 in the Risk-on band, and china.html showed a 37
gauge beside a Jul 31 endpoint of 38. Both pages are rendered from the nightly read;
`site/live/risk_state.json` and `site/live/china_risk_state.json` are published by a
SEPARATE intraday VPS lane that does not run on a closed session, so a Friday file is
what a weekend visitor fetches. 44 was Jul 30's graded score; 37 was China's Jul 30
close. `patchPath` already refused to move the chart backwards ("never rewrite
history") — the headline had no such floor, so the feed won the gauge and the render
kept the chart, and the two halves of one card disagreed by a whole band.

A source assertion cannot catch that class: the old code was valid JS reading real
fields, and every value it wrote was a genuine number from a genuine snapshot — just
from the wrong session. So the shipped JS is EXECUTED under node against a minimal DOM
stub, with feeds built to sit behind / level with / ahead of the baked page, and the
resulting DOM is read back. Both the templates/ source and the site/ copy are exercised
(they are a byte-paired plain-copy asset; test_risk_state_live_copy_sync pins the pair,
this pins the behaviour of each).

Node ships on CI + dev Macs; the suite skips loudly when it is absent (mirrors
tests/test_intraday_flow_ncp_js.py).

GD-3R1 ADDENDUM: this file also carries the pure-Python unit coverage for
scripts/build_risk_state.py's quote-clock plumbing (`_spliced_frames` /
`_source_event_time`) and, for the same reason, the engine.live_quotes
`quote_ts_synthetic` flag (amendment F3) — see the `TestSourceEventTime`,
`TestSplicedFramesQuoteClocks`, and `TestSyntheticQuoteClockFlag` classes near
the bottom of this file. Nothing in that coverage needs node; those classes run
under plain pytest. They live here (rather than in a new file, or in
tests/test_live_quotes.py) because this is the CI-wired suite that already
mirrors risk_state.json's shape via its `_us_feed`/`_cn_feed` fixtures — see
each class's own docstring for the full placement rationale.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import textwrap
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from engine import live_overlay
from scripts import build_risk_state as brs

ROOT = Path(__file__).resolve().parents[1]

HAS_NODE = shutil.which("node") is not None
needs_node = pytest.mark.skipif(not HAS_NODE, reason="node not on PATH")

US_JS = [ROOT / "templates" / "risk_state_live.js", ROOT / "site" / "risk_state_live.js"]
CN_JS = [ROOT / "templates" / "china_risk_state_live.js",
         ROOT / "site" / "china_risk_state_live.js"]
US_PAGES = pytest.mark.parametrize("js", US_JS, ids=["template", "site"])
CN_PAGES = pytest.mark.parametrize("js", CN_JS, ids=["template", "site"])

# GD-3 (adjudication #10): the Risk Envelope live overlay is a SECOND US-macro-page
# consumer of the same feed-behind-the-render floor law, but its DOM shape (the
# #risk-envelope-band chip/pending/receipt hooks) is unrelated to the
# ms-word/ms-score headline patcher's, so it gets its own JS list + harness rather
# than being appended into US_JS/US_PAGES (which would silently break every
# existing test there — `entry = "patchMacro"` does not exist in this module).
RE_JS = [ROOT / "templates" / "risk_envelope_live.js", ROOT / "site" / "risk_envelope_live.js"]
RE_PAGES = pytest.mark.parametrize("js", RE_JS, ids=["template", "site"])

BAKED_SESSION = "2026-07-31"
BAKED_SCORE = 66          # the chart endpoint AND the gauge, post-reconciliation
BAKED_WORD = "Risk-on"

# ── DOM stub ────────────────────────────────────────────────────────────────
# Just enough of the document API for the patchers: getElementById,
# querySelector/querySelectorAll over a flat element registry keyed by the exact
# selector strings the patchers use, classList, style, textContent, and the
# element factory setBL() needs. Elements record every write so the assertions
# can read back what the patcher actually did.
DOM_STUB = r"""
function El(id, cls, text) {
  this.id = id || ""; this._text = "";
  Object.defineProperty(this, "textContent", {
    get: function () { return this._text; },
    set: function (value) { this._text = String(value); this.children = []; }
  });
  this.textContent = text === undefined ? "" : text;
  this._cls = {}; (cls || "").split(/\s+/).forEach(function (c) { if (c) this._cls[c] = 1; }, this);
  this.style = {}; this.children = []; this._attrs = {};
  var self = this;
  this.classList = {
    add: function () { [].forEach.call(arguments, function (c) { self._cls[c] = 1; }); },
    remove: function () { [].forEach.call(arguments, function (c) { delete self._cls[c]; }); },
    contains: function (c) { return !!self._cls[c]; },
    toggle: function (c, on) { if (on) self._cls[c] = 1; else delete self._cls[c]; }
  };
}
El.prototype.getAttribute = function (k) { return k in this._attrs ? this._attrs[k] : null; };
El.prototype.setAttribute = function (k, v) { this._attrs[k] = String(v); };
El.prototype.appendChild = function (c) { this.children.push(c); return c; };
El.prototype.querySelector = function () { return null; };
El.prototype.querySelectorAll = function () { return []; };
El.prototype.closest = function () { return null; };
El.prototype.hasClass = function (c) { return !!this._cls[c]; };

var REG = {};      // selector / id -> El
function reg(key, el) { REG[key] = el; return el; }

var EVENT_HANDLERS = {};
var document = {
  readyState: "complete",
  documentElement: { getAttribute: function () { return "en"; }, lang: "en" },
  body: { classList: { contains: function () { return false; } } },
  getElementById: function (id) { return REG["#" + id] || null; },
  querySelector: function (s) { return REG[s] || null; },
  querySelectorAll: function (s) { return REG[s] ? [REG[s]] : []; },
  createElement: function () { return new El(); },
  addEventListener: function (name, handler) { EVENT_HANDLERS[name] = handler; },
  dispatchEvent: function () {}
};
function CustomEvent() {}
var window = {};
var setInterval = function () {};
var fetch = function () { return { then: function () { return this; }, catch: function () {} }; };
"""


def _harness(js_src: str, feed: dict, page: str, *, now=None, after="", poll=False) -> dict:
    """Run one patcher against one feed and report what the DOM ended up holding."""
    if page == "us":
        setup = f"""
        var wordEl  = reg("#ms-word", new El("ms-word", "", {BAKED_WORD!r}));
        var scoreEl = reg("#ms-score", new El("ms-score", "", "{BAKED_SCORE}"));
        var bigEl   = reg(".mx5-big-score", new El("", "mx5-big-score", "{BAKED_SCORE}"));
        var vwEl    = reg(".mx5-verdict-word", new El("", "mx5-verdict-word", {BAKED_WORD!r}));
        var thesis  = reg(".mx5-thesis", new El("", "mx5-thesis", "Risk-on — the tape"));
        var subline = reg(".mx5-sub-line", new El("", "mx5-sub-line", "GREEN — Risk-on backdrop"));
        var action  = reg("[data-wtd-primary] .mx5-action-label", new El("", "mx5-action-label", "Stay selective."));
        var actionSub = reg("[data-wtd-primary] .mx5-action-sub", new El());
        var flipEl = reg(".mx5-flip", new El());
        var pill    = reg("#ms-live-pill", new El("ms-live-pill", "on"));
        reg("#ms-date", new El("ms-date", "", "{BAKED_SESSION}"));
        reg("#regime-asof", new El("regime-asof", "", "{BAKED_SESSION}"));
        reg("#ms-tick", new El("ms-tick"));
        var gauge = reg(".mx5-gauge-svg", new El("", "mx5-gauge-svg"));
        gauge.setAttribute("data-gauge-arc-len", "175.93");
        """
        readback = """
        out.word  = (wordEl.children[0] || {}).textContent || wordEl.textContent;
        out.score = String(scoreEl.textContent);
        out.big   = String(bigEl.textContent);
        out.thesis = (thesis.children[0] || {}).textContent || thesis.textContent;
        out.subline = (subline.children[0] || {}).textContent || subline.textContent;
        out.action = (action.children[0] || {}).textContent || action.textContent;
        out.action_sub = (actionSub.children[0] || {}).textContent || actionSub.textContent;
        out.thesis_zh = (thesis.children[1] || {}).textContent;
        out.flip_hidden = flipEl.style.display === "none";
        out.pill_on = pill.hasClass("on");
        """
    else:
        setup = f"""
        var wordEl  = reg("#ms-word", new El("ms-word", "", {BAKED_WORD!r}));
        var scoreEl = reg("#ms-score", new El("ms-score", "", "{BAKED_SCORE}"));
        var numEl   = reg("#mx5-score-numeral", new El("mx5-score-numeral", "", "{BAKED_SCORE}"));
        var dateEl  = reg("#ms-date", new El("ms-date", "", "{BAKED_SESSION}"));
        var pill    = reg("#ms-live-pill", new El("ms-live-pill", "on"));
        reg("#ms-tick", new El("ms-tick"));
        reg(".v-thesis", new El("", "v-thesis", "Risk-on — the tape"));
        """
        readback = """
        out.word  = (wordEl.children[0] || {}).textContent || wordEl.textContent;
        out.score = String(scoreEl.textContent);
        out.numeral = String(numEl.textContent);
        out.date  = (dateEl.children[0] || {}).textContent || dateEl.textContent;
        out.pill_on = pill.hasClass("on");
        """

    pts = [{"d": "2026-07-30", "md": "Jul 30", "mz": "7月30", "s": 44,
            "v": "Mixed", "vz": "中性", "x": 945.09, "y": 113.04},
           {"d": BAKED_SESSION, "md": "Jul 31", "mz": "7月31", "s": BAKED_SCORE,
            "v": BAKED_WORD, "vz": "偏多", "x": 988.0, "y": 72.56}]
    chart = f"""
        var svg = reg(".mx5-sc-right .mx5-path-svg[data-points]", new El("", "mx5-path-svg"));
        svg.setAttribute("data-points", {json.dumps(json.dumps(pts))});
        svg.setAttribute("data-px0", "44"); svg.setAttribute("data-pxw", "944");
        svg.setAttribute("data-py0", "10"); svg.setAttribute("data-pyb", "194");
        svg.setAttribute("data-vbw", "1000"); svg.setAttribute("data-vbh", "224");
    """

    # the patchers are IIFEs that self-invoke on DOMContentLoaded/readyState and
    # keep their internals private; re-expose the one entry point we drive by
    # replacing the fetch-driven tick with a direct call.
    entry = "patchMacro" if page == "us" else "patchChina"
    # Deterministic browser time: these fixtures intentionally describe older
    # sessions. Expiry tests pass an independent later observation time.
    if now is None:
        now = (feed.get("built") or "2026-07-31 22:31:49 UTC").replace(" UTC", "+00:00")
        now = (datetime.fromisoformat(now) + timedelta(seconds=60)).isoformat()
    result_js = "\n".join([
        readback,
        "out.chart_last = JSON.parse(svg.getAttribute('data-points')).slice(-1)[0];",
        "console.log(JSON.stringify(out));",
    ])
    invocation = (f"patchMacro(FEED); {after}" if poll else f"{entry}(FEED); {after}")
    if poll:
        invocation = ("(async function () { try { " + invocation +
                      " } catch (e) { out.error = String(e); } " + result_js + " })();")
    else:
        invocation = f"try {{ {invocation} }} catch (e) {{ out.error = String(e); }}"
    script = "\n".join([
        DOM_STUB,
        setup,
        chart,
        "var out = {};",
        f"var FEED = {json.dumps(feed)};",
        f"var browserNow = Date.parse({json.dumps(now)}); Date.now = function () {{ return browserNow; }};",
        # strip the module's own auto-run tail, then invoke the patcher directly
        "(function(){",
        js_src.replace("})();", invocation + "\n})();"),
        "})();",
        "" if poll else result_js,
    ])
    res = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, f"node failed: {res.stderr[-2000:]}"
    return json.loads(res.stdout.strip().splitlines()[-1])


# ── GD-3: the Risk Envelope overlay's own DOM stub + harness (adjudication #10) ──
# risk_envelope_live.js exposes `applyFeed(d)` (extracted from tick()'s fetch chain
# specifically so it is drivable this way, same idiom as patchMacro/patchChina
# above) — reads the band's data-bundle-id/data-settled-session, and paints/hides
# the #gde-live-chip / #gde-pending-chip / #gde-live-receipt hooks.

RE_BAKED_BUNDLE = "fd9ccdbe47f7f008"
RE_BAKED_SESSION = "2026-08-19"


def _re_harness(js_src: str, feed: dict | None, *, now=None, after="") -> dict:
    """Run risk_envelope_live.js's `applyFeed` against one feed and report what
    the DOM ended up holding. `feed=None` simulates a fetch that resolved falsy
    (network error / non-OK response already reduced to null upstream of
    applyFeed in the real fetch chain)."""
    setup = f"""
    var band = reg("#risk-envelope-band", new El("risk-envelope-band"));
    band.setAttribute("data-bundle-id", {RE_BAKED_BUNDLE!r});
    band.setAttribute("data-settled-session", {RE_BAKED_SESSION!r});

    var chip = reg("#gde-live-chip", new El("gde-live-chip"));
    chip.hidden = true;
    var chipEn = new El("", "l-en", "");
    var chipZh = new El("", "l-zh", "");
    var chipTime = new El("", "gde-live-time", "");
    chip.querySelector = function (sel) {{
      if (sel === ".l-en") return chipEn;
      if (sel === ".l-zh") return chipZh;
      if (sel === ".gde-live-time") return chipTime;
      return null;
    }};

    var pending = reg("#gde-pending-chip", new El("gde-pending-chip"));
    pending.hidden = true;
    var pendingEn = new El("", "l-en", "");
    var pendingZh = new El("", "l-zh", "");
    pending.querySelector = function (sel) {{
      if (sel === ".l-en") return pendingEn;
      if (sel === ".l-zh") return pendingZh;
      return null;
    }};

    var receipt = reg("#gde-live-receipt", new El("gde-live-receipt"));
    receipt.hidden = true;
    """
    readback = """
    out.chip_hidden = !!chip.hidden;
    out.chip_en = chipEn.textContent;
    out.chip_zh = chipZh.textContent;
    out.chip_time = chipTime.textContent;
    out.pending_hidden = !!pending.hidden;
    out.pending_en = pendingEn.textContent;
    out.receipt_hidden = !!receipt.hidden;
    out.receipt_text = receipt.textContent;
    """
    script = "\n".join([
        DOM_STUB,
        setup,
        "var out = {};",
        f"var FEED = {json.dumps(feed)};",
        (f"var browserNow = Date.parse({json.dumps(now)}); Date.now = function () {{ return browserNow; }};"
         if now is not None else ""),
        "(function(){",
        js_src.replace(
            "})();",
            "try { applyFeed(FEED); " + after + " } catch (e) { out.error = String(e); }\n})();",
        ),
        "})();",
        readback,
        "console.log(JSON.stringify(out));",
    ])
    res = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, f"node failed: {res.stderr[-2000:]}"
    return json.loads(res.stdout.strip().splitlines()[-1])


def _re_feed(*, source_session="2026-08-20", bundle_id=RE_BAKED_BUNDLE, precedence="live",
             live_active=True, built=None, stale_after_min=5,
             stage="FRAGILE", stable_stage="FRAGILE", pending=None, data_state="FRESH") -> dict:
    # `active()`'s freshness gate compares against REAL wall-clock Date.now() (it
    # must, in production), so a fixture built from a fixed historical string would
    # go stale the moment real time moves past it. Default to "90s ago" computed at
    # call time instead, well inside the 5min horizon regardless of when the suite
    # actually runs.
    if built is None:
        built = (datetime.now(timezone.utc) - timedelta(seconds=90)).strftime("%Y-%m-%d %H:%M:%S UTC")
    return {
        "schema": "mastermind.risk_envelope/v1",
        "revision": "live_provisional",
        "precedence": precedence,
        "source_session": source_session,
        "bundle_id": "9c4a7e21ab30f581",
        "built": built,
        "live_active": live_active,
        "stale_after_min": stale_after_min,
        "stale_after": (datetime.fromisoformat(built.replace(" UTC", "+00:00")) +
                        timedelta(minutes=stale_after_min)).isoformat() if live_active else None,
        "data_state": data_state,
        "hazard_summary": {"stage": stage},
        "overlays": {"settled_bundle_id": bundle_id, "settled_source_session": RE_BAKED_SESSION},
        "live_transition": {"candidate_stage": stage, "stable_stage": stable_stage, "pending": pending},
    }


@needs_node
@RE_PAGES
def test_re_feed_a_session_behind_the_render_never_paints(js):
    """The SAME feed-behind-the-render floor law as risk_state_live.js, applied to
    the Risk Envelope overlay: a live read whose own source_session is OLDER than
    the page's baked settled session (data-settled-session) must never paint."""
    feed = _re_feed(source_session="2026-08-18")   # older than RE_BAKED_SESSION
    out = _re_harness(js.read_text(encoding="utf-8"), feed)
    assert not out.get("error"), out.get("error")
    assert out["chip_hidden"] is True
    assert out["pending_hidden"] is True
    assert out["receipt_hidden"] is True


@needs_node
@RE_PAGES
def test_re_feed_on_or_ahead_of_the_render_still_paints(js):
    """Sanity control for the floor test above: a live session AHEAD of the baked
    settled session (the normal case) must still paint."""
    feed = _re_feed(source_session="2026-08-20")   # ahead of RE_BAKED_SESSION
    out = _re_harness(js.read_text(encoding="utf-8"), feed)
    assert not out.get("error"), out.get("error")
    assert out["chip_hidden"] is False
    assert out["chip_en"] == "Live · provisional"


@needs_node
@RE_PAGES
def test_re_unpaint_hides_all_three_hooks_completely(js):
    """A feed that fails `active()` (mismatched settled_bundle_id here) must hide
    ALL three hooks — chip, pending, and receipt — never leave one painted while
    the others clear."""
    feed = _re_feed()
    feed["overlays"]["settled_bundle_id"] = "SOME-OTHER-BUNDLE"
    out = _re_harness(js.read_text(encoding="utf-8"), feed)
    assert not out.get("error"), out.get("error")
    assert out["chip_hidden"] is True
    assert out["pending_hidden"] is True
    assert out["receipt_hidden"] is True
    assert out["receipt_text"] == ""


@needs_node
@RE_PAGES
def test_re_stage_null_routes_to_degraded_even_when_data_state_is_fresh(js):
    """Adjudication #8 regression: route on hazard_summary.stage alone. A feed
    with a null stage but data_state FRESH (the exact shape a laundered empty
    live block used to produce) must still paint the DEGRADED copy, never the
    healthy "Live · provisional" chip."""
    feed = _re_feed(stage=None, stable_stage="FRAGILE", data_state="FRESH")
    out = _re_harness(js.read_text(encoding="utf-8"), feed)
    assert not out.get("error"), out.get("error")
    assert out["chip_hidden"] is False
    assert out["chip_en"] == "Live · not enough to say"
    assert out["chip_zh"] == "实时 · 暂无法判断"
    assert out["pending_hidden"] is True


@needs_node
@RE_PAGES
def test_re_paint_degraded_paint_restores_chip_copy_and_receipt(js):
    """Adjudication #4 regression: paint() must NOT assume the DOM still holds its
    baked "Live · provisional" copy — a prior paintDegraded() call must not leave
    the chip stuck on degraded text, or the receipt stuck on a stale HEALTHY line,
    once a subsequent feed is healthy again. Runs three feeds through the SAME
    long-lived DOM stub in one node process, exactly like a real poll sequence."""
    healthy = _re_feed(stage="TRANSMITTING",
                       pending={"stage": "TRANSMITTING", "ticks": 2, "needs": 3})
    degraded = _re_feed(stage=None, data_state="DEGRADED")
    healthy_again = _re_feed(stage="FRAGILE", pending=None)

    setup = f"""
    var band = reg("#risk-envelope-band", new El("risk-envelope-band"));
    band.setAttribute("data-bundle-id", {RE_BAKED_BUNDLE!r});
    band.setAttribute("data-settled-session", {RE_BAKED_SESSION!r});

    var chip = reg("#gde-live-chip", new El("gde-live-chip"));
    chip.hidden = true;
    var chipEn = new El("", "l-en", "");
    var chipZh = new El("", "l-zh", "");
    var chipTime = new El("", "gde-live-time", "");
    chip.querySelector = function (sel) {{
      if (sel === ".l-en") return chipEn;
      if (sel === ".l-zh") return chipZh;
      if (sel === ".gde-live-time") return chipTime;
      return null;
    }};

    var pending = reg("#gde-pending-chip", new El("gde-pending-chip"));
    pending.hidden = true;
    var pendingEn = new El("", "l-en", "");
    var pendingZh = new El("", "l-zh", "");
    pending.querySelector = function (sel) {{
      if (sel === ".l-en") return pendingEn;
      if (sel === ".l-zh") return pendingZh;
      return null;
    }};

    var receipt = reg("#gde-live-receipt", new El("gde-live-receipt"));
    receipt.hidden = true;
    """
    readback = """
    out.chip_en = chipEn.textContent;
    out.receipt_text = receipt.textContent;
    """
    script = "\n".join([
        DOM_STUB,
        setup,
        "var out1 = {}, out2 = {}, out3 = {};",
        f"var FEED1 = {json.dumps(healthy)};",
        f"var FEED2 = {json.dumps(degraded)};",
        f"var FEED3 = {json.dumps(healthy_again)};",
        "(function(){",
        js.read_text(encoding="utf-8").replace(
            "})();",
            "try {\n"
            "  applyFeed(FEED1);\n"
            "  out1.chip_en = chipEn.textContent; out1.receipt_text = receipt.textContent;\n"
            "  applyFeed(FEED2);\n"
            "  out2.chip_en = chipEn.textContent; out2.receipt_text = receipt.textContent;\n"
            "  applyFeed(FEED3);\n"
            "  out3.chip_en = chipEn.textContent; out3.receipt_text = receipt.textContent;\n"
            "} catch (e) { out1.error = String(e); }\n"
            "})();",
        ),
        "})();",
        "console.log(JSON.stringify({one: out1, two: out2, three: out3}));",
    ])
    res = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, f"node failed: {res.stderr[-2000:]}"
    out = json.loads(res.stdout.strip().splitlines()[-1])
    assert not out["one"].get("error"), out["one"].get("error")

    assert out["one"]["chip_en"] == "Live · provisional"
    assert "TRANSMITTING" in out["one"]["receipt_text"]

    assert out["two"]["chip_en"] == "Live · not enough to say", (
        "paintDegraded must overwrite the chip copy"
    )
    assert "TRANSMITTING" not in out["two"]["receipt_text"], (
        "the degraded receipt must not keep showing the last HEALTHY pending line"
    )

    assert out["three"]["chip_en"] == "Live · provisional", (
        "a healthy feed after a degraded one must restore the chip's normal copy, "
        "not leave it stuck on 'not enough to say'"
    )
    assert "TRANSMITTING" not in out["three"]["receipt_text"]


# display labels exactly as engine/market_state.py _LABEL emits them
LABEL = {"RISK_ON": ("Risk-on", "风险偏好"), "MIXED": ("Mixed", "混合"),
         "RISK_OFF": ("Risk-off", "避险")}
COLOR = {"RISK_ON": "green", "MIXED": "yellow", "RISK_OFF": "red"}


def _us_feed(nightly_asof: str, score: int, verdict: str, *, live=False, built=None) -> dict:
    en, zh = LABEL[verdict]
    built = built or f"{nightly_asof} 22:31:49 UTC"
    event = datetime.fromisoformat(built.replace(" UTC", "+00:00")) - timedelta(minutes=15)
    return {
        "schema": "risk_state.v1",
        "built": built,
        "live_active": live, "realtime": False, "stale": not live,
        "nightly_asof": nightly_asof,
        "session": {"open": live, "expected_session": nightly_asof},
        "quote_stale_after_min": 20,
        "stale_after": (event + timedelta(minutes=20)).isoformat() if live else None,
        "live": {"source_event_time": event.isoformat()},
        "display": {"verdict": verdict, "label_en": en, "label_zh": zh,
                    "color": COLOR[verdict], "score": score},
        "nightly": {"verdict": verdict, "score": score, "label_en": en, "label_zh": zh},
    }


def _cn_feed(nightly_asof: str, score: int, verdict: str, *, live=False, built=None) -> dict:
    f = _us_feed(nightly_asof, score, verdict, live=live, built=built)
    f["schema"] = "china_risk_state.v1"
    f["live"] = {"verdict": verdict, "headline_en": "Risk-off — stress is elevated",
                 "headline_zh": "避险"}
    f["nightly"]["headline_en"] = "Risk-off — stress is elevated"
    f["nightly"]["headline_zh"] = "避险"
    return f


# ── the regression itself ───────────────────────────────────────────────────

@needs_node
@US_PAGES
def test_us_feed_a_session_behind_leaves_the_board_alone(js):
    """The reported bug: a Jul 30 feed must not repaint a Jul 31 board."""
    out = _harness(js.read_text(encoding="utf-8"),
                   _us_feed("2026-07-30", 44, "MIXED"), "us")
    assert not out.get("error"), out["error"]
    assert out["score"] == str(BAKED_SCORE), (
        f"gauge regressed to the older session: {out['score']} (chart still "
        f"{out['chart_last']['s']}) — the split the floor exists to prevent")
    assert out["big"] == str(BAKED_SCORE)
    assert out["word"] == BAKED_WORD
    assert out["thesis"].startswith("Current market assessment unavailable")
    assert out["pill_on"] is False, "a behind-the-render feed must not claim live"
    assert out["chart_last"]["s"] == BAKED_SCORE


@needs_node
@CN_PAGES
def test_cn_feed_a_session_behind_leaves_the_board_alone(js):
    out = _harness(js.read_text(encoding="utf-8"),
                   _cn_feed("2026-07-30", 37, "RISK_OFF", live=True,
                            built="2026-07-30 08:22:23 UTC"), "cn")
    assert not out.get("error"), out["error"]
    assert out["score"] == str(BAKED_SCORE), (
        f"gauge regressed to the older session: {out['score']} (chart still "
        f"{out['chart_last']['s']})")
    assert out["numeral"] == str(BAKED_SCORE)
    assert out["word"] == BAKED_WORD
    assert out["date"] == BAKED_SESSION, (
        f"freshness chip claims {out['date']!r} for a feed a session behind the render")
    assert out["pill_on"] is False


# ── and the floor must not break the thing it guards ────────────────────────

@needs_node
@US_PAGES
def test_us_feed_on_the_rendered_session_still_patches(js):
    """Same-session feed is the normal intraday case — it must still win."""
    out = _harness(js.read_text(encoding="utf-8"),
                   _us_feed(BAKED_SESSION, 44, "MIXED"), "us")
    assert not out.get("error"), out["error"]
    assert out["score"] == "44"
    assert out["word"] == "Mixed"
    assert out["chart_last"]["s"] == 44, "same-session patch must carry the chart with it"
    assert out["chart_last"]["v"] == "Mixed"


@needs_node
@US_PAGES
def test_us_legacy_feed_keeps_safe_verdict_fallback_copy(js):
    # Older payloads without display presentation fields retain safe copy.
    feed = _us_feed(BAKED_SESSION, 61, "RISK_ON")

    out = _harness(js.read_text(encoding="utf-8"), feed, "us")

    assert not out.get("error"), out["error"]
    assert out["thesis"].startswith(
        "Risk-on — the overall backdrop is supportive."
    )
    assert out["subline"] == "GREEN — Risk-on backdrop"
    assert out["action"] == "Stay selective. Add where setups confirm."
    assert "breadth and cross-asset signals line up" not in out["thesis"]


@needs_node
@US_PAGES
def test_us_feed_prefers_canonical_participation_aware_headline(js):
    feed = _us_feed(BAKED_SESSION, 61, "RISK_ON")
    feed["display"]["headline_en"] = (
        "Selective risk-on — the broader backdrop is supportive, but participation is weak."
    )
    feed["display"]["headline_zh"] = "选择性风险偏好 — 大环境仍支持风险资产，但市场参与度偏弱。"
    feed["display"]["participation_scope"] = {
        "state": "selective",
        "participation": "weak",
        "breadth_score": 0,
        "subline_en": "GREEN — Selective risk-on",
        "subline_zh": "偏多 — 选择性风险偏好",
        "action_en": "Stay selective. Follow confirmed leadership and fresh turns.",
        "action_zh": "保持精选。跟随已确认的强势板块与新出现的转强信号。",
    }

    out = _harness(js.read_text(encoding="utf-8"), feed, "us")

    assert not out.get("error"), out["error"]
    assert out["thesis"].startswith("Selective risk-on")
    assert out["subline"] == "GREEN — Selective risk-on"
    assert out["action"] == "Stay selective. Follow confirmed leadership and fresh turns."
    assert "breadth and cross-asset signals line up" not in out["thesis"]


@needs_node
@US_PAGES
def test_us_feed_participation_unverified_headline_fails_closed(js):
    feed = _us_feed(BAKED_SESSION, 61, "RISK_ON")
    feed["display"]["headline_en"] = (
        "Risk-on — the broader backdrop is supportive, but participation is unverified."
    )
    feed["display"]["headline_zh"] = "风险偏好 — 大环境支持风险资产，但市场参与度尚无法验证。"
    feed["display"]["participation_scope"] = {
        "state": "unverified", "participation": "unverified", "breadth_score": None
    }

    out = _harness(js.read_text(encoding="utf-8"), feed, "us")

    assert not out.get("error"), out["error"]
    assert "participation is unverified" in out["thesis"]


@needs_node
@US_PAGES
def test_us_feed_ahead_of_the_render_appends_a_provisional_point(js):
    """A genuinely newer session still appends, and the chart follows the gauge."""
    out = _harness(js.read_text(encoding="utf-8"),
                   _us_feed("2026-08-03", 52, "MIXED", live=True,
                            built="2026-08-03 14:05:00 UTC"), "us")
    assert not out.get("error"), out["error"]
    assert out["score"] == "52"
    assert out["chart_last"]["d"] == "2026-08-03"
    assert out["chart_last"]["s"] == 52


@needs_node
@US_PAGES
def test_us_null_measured_and_display_scores_preserve_the_baked_path(js):
    """JS must not coerce an explicit null score to zero and invent a Risk-off point."""
    feed = _us_feed(BAKED_SESSION, 44, "MIXED", live=True,
                    built=f"{BAKED_SESSION} 14:05:00 UTC")
    feed["display"]["score"] = None
    feed["display"]["raw_score"] = None
    out = _harness(js.read_text(encoding="utf-8"), feed, "us")
    assert not out.get("error"), out["error"]
    assert out["score"] == str(BAKED_SCORE)
    assert out["chart_last"]["s"] == BAKED_SCORE
    assert out["chart_last"]["v"] == BAKED_WORD


@needs_node
@CN_PAGES
def test_cn_feed_on_the_rendered_session_still_patches(js):
    out = _harness(js.read_text(encoding="utf-8"),
                   _cn_feed(BAKED_SESSION, 37, "RISK_OFF", live=True,
                            built=f"{BAKED_SESSION} 08:22:23 UTC"), "cn")
    assert not out.get("error"), out["error"]
    assert out["score"] == "37"
    assert out["word"] == "Risk-off"


@needs_node
@US_PAGES
def test_us_unreadable_feed_session_fails_closed(js):
    """No parseable session on the feed → keep the served render, not a guess."""
    feed = _us_feed("2026-07-30", 44, "MIXED")
    feed["nightly_asof"] = None
    feed["built"] = ""
    out = _harness(js.read_text(encoding="utf-8"), feed, "us")
    assert not out.get("error"), out["error"]
    assert out["score"] == str(BAKED_SCORE)
    assert out["word"] == BAKED_WORD


# ══ GD-3R1 — scripts/build_risk_state.py's own quote-clock plumbing ══════════════

@needs_node
@US_PAGES
def test_us_postclose_does_not_present_previous_session_as_current(js):
    feed = _us_feed("2026-11-04", 57, "MIXED", built="2026-11-05 22:25:53 UTC")
    feed["session"] = {"open": False, "state": "postclose", "expected_session": "2026-11-05"}
    out = _harness(js.read_text(), feed, "us", now="2026-11-05T22:26:00Z")
    assert not out.get("error"), out.get("error")
    assert out["score"] == "57"
    assert out["chart_last"]["d"] == "2026-11-04"
    assert out["chart_last"]["s"] == 57
    assert out["thesis"].startswith("Current market assessment unavailable")
    assert "2026-11-04" in out["subline"]
    assert "unavailable" in out["action"]
    assert "2026-11-04" in out["action_sub"]
    assert "暂不可用" in out["thesis_zh"]
    assert out["flip_hidden"] and not out["pill_on"]


@needs_node
@US_PAGES
@pytest.mark.parametrize("source_clock", [
    None, "2026-11-05T14:50:00", "2026-11-05T14:00:00Z", "2026-11-06T15:05:00Z",
])
def test_us_fresh_build_cannot_launder_bad_or_expired_market_clock(js, source_clock):
    feed = _us_feed("2026-11-05", 70, "RISK_ON", live=True,
                    built="2026-11-05 15:05:00 UTC")
    feed["live"]["source_event_time"] = source_clock
    out = _harness(js.read_text(), feed, "us", now="2026-11-05T15:06:00Z")
    assert not out.get("error"), out.get("error")
    assert out["score"] == str(BAKED_SCORE)
    assert out["chart_last"]["d"] == BAKED_SESSION
    assert "unavailable" in out["action"]


@needs_node
@US_PAGES
def test_us_healthy_delayed_observation_remains_eligible(js):
    feed = _us_feed("2026-11-05", 38, "RISK_OFF", live=True,
                    built="2026-11-05 15:05:00 UTC")
    out = _harness(js.read_text(), feed, "us", now="2026-11-05T15:06:00Z")
    assert not out.get("error"), out.get("error")
    assert out["score"] == "38"
    assert out["chart_last"]["d"] == "2026-11-05"
    assert out["thesis"].startswith("Risk-off")
    assert not out["pill_on"]  # delayed is not realtime


@needs_node
@US_PAGES
def test_us_long_open_failure_expires_and_fresh_recovery_restores_copy(js):
    feed = _us_feed("2026-11-05", 38, "RISK_OFF", live=True,
                    built="2026-11-05 15:05:00 UTC")
    after = """
    browserNow += 6 * 60000;
    EVENT_HANDLERS.visibilitychange();
    out.expired_action = action.children[0].textContent;
    out.expired_thesis = thesis.children[0].textContent;
    out.expired_base_action = action.getAttribute("data-wtd-base-en");
    out.expired_base_verdict = action.getAttribute("data-wtd-base-verdict");
    FEED.built = new Date(browserNow - 1000).toISOString();
    FEED.live.source_event_time = new Date(browserNow - 15 * 60000).toISOString();
    FEED.stale_after = new Date(Date.parse(FEED.built) + 5 * 60000).toISOString();
    patchMacro(FEED);
    out.recovered_base_action = action.getAttribute("data-wtd-base-en");
    out.recovered_base_verdict = action.getAttribute("data-wtd-base-verdict");
    """
    out = _harness(js.read_text(), feed, "us", now="2026-11-05T15:06:00Z", after=after)
    assert not out.get("error"), out.get("error")
    assert "unavailable" in out["expired_action"]
    assert "historical snapshot" in out["expired_thesis"]
    assert out["expired_base_action"] == out["expired_action"]
    assert out["expired_base_verdict"] == "UNAVAILABLE"
    assert out["recovered_base_action"] == "Reduce risk. Protect capital."
    assert out["recovered_base_verdict"] == "RISK_OFF"
    assert out["thesis"].startswith("Risk-off")
    assert out["action"] == "Reduce risk. Protect capital."
    assert out["score"] == "38"


@needs_node
@US_PAGES
def test_us_postclose_fallback_cannot_rewind_a_live_session_already_shown(js):
    feed = _us_feed("2026-11-04", 38, "RISK_OFF", live=True,
                    built="2026-11-05 20:55:00 UTC")
    after = """
    browserNow = Date.parse('2026-11-05T22:26:00Z');
    var fallback = JSON.parse(JSON.stringify(FEED));
    fallback.built = '2026-11-05 22:25:53 UTC';
    fallback.live_active = false;
    fallback.stale = true;
    fallback.session = {open:false, state:'postclose', expected_session:'2026-11-05'};
    fallback.display = {verdict:'MIXED', label_en:'Mixed', score:57, raw_score:57};
    patchMacro(fallback);
    """
    out = _harness(js.read_text(), feed, "us", now="2026-11-05T20:56:00Z", after=after)
    assert not out.get("error"), out.get("error")
    assert out["score"] == "38"
    assert out["chart_last"]["d"] == "2026-11-05"
    assert out["chart_last"]["s"] == 38
    assert "2026-11-05" in out["subline"]
    assert "unavailable" in out["action"]


@needs_node
@US_PAGES
def test_us_expired_build_never_appends_an_old_live_tick(js):
    feed = _us_feed("2026-11-05", 70, "RISK_ON", live=True,
                    built="2026-11-05 15:05:00 UTC")
    out = _harness(js.read_text(), feed, "us", now="2026-11-05T15:11:00Z")
    assert not out.get("error"), out.get("error")
    assert out["chart_last"]["d"] == BAKED_SESSION
    assert "unavailable" in out["action"]


@needs_node
@US_PAGES
@pytest.mark.parametrize("failure", ["http", "json", "network"])
def test_us_poll_failures_expire_then_recover_without_rewriting_history(js, failure):
    feed = _us_feed("2026-11-05", 38, "RISK_OFF", live=True,
                    built="2026-11-05 15:05:00 UTC")
    response = {
        "http": "Promise.resolve({ok:false})",
        "json": "Promise.resolve({ok:true,json:function(){return Promise.reject(new Error('bad JSON'));}})",
        "network": "Promise.reject(new Error('offline'))",
    }[failure]
    after = f"""
    requestPending = false;
    fetch = function () {{ return {response}; }};
    tick();
    await new Promise(function (resolve) {{ setImmediate(resolve); }});
    out.brief_failure = action.children[0].textContent;
    browserNow += 6 * 60000;
    tick();
    await new Promise(function (resolve) {{ setImmediate(resolve); }});
    out.failed_action = action.children[0].textContent;
    out.failed_last = JSON.parse(svg.getAttribute('data-points')).slice(-1)[0];
    var recovered = JSON.parse(JSON.stringify(FEED));
    recovered.built = new Date(browserNow - 1000).toISOString();
    recovered.live.source_event_time = new Date(browserNow - 15 * 60000).toISOString();
    recovered.stale_after = new Date(Date.parse(recovered.built) + 5 * 60000).toISOString();
    fetch = function () {{ return Promise.resolve({{ok:true,json:function(){{return Promise.resolve(recovered);}}}}); }};
    tick();
    await new Promise(function (resolve) {{ setImmediate(resolve); }});
    """
    out = _harness(js.read_text(), feed, "us", now="2026-11-05T15:06:00Z", after=after, poll=True)
    assert not out.get("error"), out.get("error")
    assert out["brief_failure"] == "Reduce risk. Protect capital."
    assert "unavailable" in out["failed_action"]
    assert out["failed_last"]["s"] == out["chart_last"]["s"] == 38
    assert out["failed_last"]["d"] == out["chart_last"]["d"] == "2026-11-05"
    assert out["action"] == "Reduce risk. Protect capital."


def test_live_vix_shock_refreshes_existing_percentile_definition(monkeypatch):
    from engine.indicators import pct_rank_window
    from engine.market_state import _comp_vol
    monkeypatch.setattr(brs.config, "load", lambda: {
        "engine": {"conditions": {"complacency": {"vix_pctile_lookback_d": 504}}}
    })
    prices = pd.Series([16.0 + i / 1000 for i in range(504)] + [28.0])
    value = brs._live_vix_percentile({"_VIX": pd.DataFrame({"close": prices})})
    assert value == pct_rank_window(prices, 504).iloc[-1] == 1.0
    stale = {"conditions": {"risk_appetite": {"vix_term": 1.1},
                            "complacency": {"vix_pctile": 0.41865079365079366}}}
    fresh = {"conditions": {"risk_appetite": {"vix_term": 1.1},
                            "complacency": {"vix_pctile": value}}}
    assert _comp_vol(stale)["score"] == 34
    assert _comp_vol(fresh)["score"] == 12


def test_live_vix_percentile_does_not_invent_missing_observation():
    assert brs._live_vix_percentile({}) is None
    assert brs._live_vix_percentile({"_VIX": pd.DataFrame({"close": []})}) is None


def _built_required_clock_feed(monkeypatch, tmp_path, *, unavailable=None,
                               quote_times=None, now=None, budget=20, use_vix9d=True):
    from engine import shock_deescalation
    now = now or datetime(2026, 11, 5, 15, 5, tzinfo=timezone.utc)
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return now
    monkeypatch.setattr(brs, "datetime", FrozenDatetime)
    monkeypatch.setattr(brs.config, "ROOT", tmp_path)
    cfg = {"live": {"stale_after_min": 20, "delayed_min": 15},
           "storage": {"site_dir": "site"},
           "engine": {"conditions": {"complacency": {"vix_pctile_lookback_d": 504}}}}
    if budget is None:
        cfg["live"].pop("stale_after_min")
    else:
        cfg["live"]["stale_after_min"] = budget
    monkeypatch.setattr(brs.config, "load", lambda: cfg)
    monkeypatch.setattr(brs.config, "data_dir", lambda: tmp_path / "data")
    regime = tmp_path / "data" / "regime"
    regime.mkdir(parents=True, exist_ok=True)
    latest = {"date": "2026-11-04", "conditions": {
        "complacency": {"vix_pctile": 0.41865079365079366},
        "risk_appetite": {"vix_term": 0.8835}}}
    (regime / "latest.json").write_text(json.dumps(latest))
    nightly = {"asof": "2026-11-04", "verdict": "MIXED", "score": 57, "raw_score": 57}
    monkeypatch.setattr(brs.market_state, "load_persisted", lambda: nightly)
    monkeypatch.setattr(brs.live_overlay, "market_session", lambda *a: {
        "open": True, "state": "regular", "expected_session": "2026-11-05"})
    monkeypatch.setattr(brs.live_quotes, "fetch_quotes", lambda *a, **kw: {})
    idx = pd.date_range(end="2026-11-05", periods=505)
    spliced = {name: pd.DataFrame({"close": [100.0] * 505}, index=idx)
               for name in ("SPY", "QQQ", "IWM", "HYG", "_VIX", "_VIX3M", "_VIX9D")}
    spliced["_VIX"]["close"] = [16.0 + i / 1000 for i in range(504)] + [28.0]
    if not use_vix9d:
        spliced.pop("_VIX9D", None)
    if unavailable == "equities":
        for name in ("SPY", "QQQ", "IWM"):
            del spliced[name]
    if unavailable == "volatility":
        for name in ("_VIX", "_VIX3M", "_VIX9D"):
            del spliced[name]
    clocks = {name: "2026-11-05T14:50:00+00:00" for name in spliced}
    if quote_times:
        clocks.update(quote_times)
    if unavailable == "missing_clock":
        clocks["QQQ"] = None
    if unavailable == "future_clock":
        clocks["QQQ"] = "2026-11-06T15:05:00+00:00"
    if unavailable == "naive_clock":
        clocks["QQQ"] = "2026-11-05T14:50:00"
    live_close = {name: frame["close"].iloc[-1] for name, frame in spliced.items()}
    if "_VIX9D" in live_close:
        live_close.update({"_VIX9D": 33.0, "_VIX3M": 30.0})
    monkeypatch.setattr(brs, "_spliced_frames", lambda *a: (spliced, live_close, {}, clocks))
    monkeypatch.setattr(brs, "_live_frame", lambda *a: None)
    monkeypatch.setattr(brs, "_hy_oas_asof", lambda: "2026-11-04")
    monkeypatch.setattr(brs.risk_radar, "compute", lambda: {})
    captured = {}
    def snapshot(projected, *args):
        captured.update(projected)
        if unavailable == "computation":
            return None
        vol = brs.market_state._comp_vol(projected)
        return {"verdict": "RISK_OFF", "score": 38, "raw_score": 38,
                "components": [{"key": "trend", "score": 10}, vol]}
    monkeypatch.setattr(brs.market_state, "market_state_snapshot", snapshot)
    monkeypatch.setattr(brs.market_drivers, "snapshot", lambda: {})
    monkeypatch.setattr(brs.market_drivers, "append_log", lambda *a, **kw: None)
    monkeypatch.setattr(shock_deescalation, "build_intraday", lambda: {})
    original_reader = brs.store_mod.read
    assert brs.build(offline=True)["status"] == "ok"
    out = json.loads((tmp_path / "site" / "live" / "risk_state.json").read_text())
    assert brs.store_mod.read is original_reader
    assert json.loads((regime / "latest.json").read_text()) == latest
    return out, captured


@pytest.mark.parametrize("unavailable", [None, "equities", "volatility", "naive_clock"])
def test_build_refreshes_vix_but_partial_inputs_cannot_claim_live(monkeypatch, tmp_path, unavailable):
    from scripts.build_live_risk_envelope import market_freshness

    now = datetime(2026, 11, 5, 15, 5, tzinfo=timezone.utc)
    out, captured = _built_required_clock_feed(monkeypatch, tmp_path, unavailable=unavailable)
    assert out["quote_stale_after_min"] == 20
    legs = {leg["key"]: leg for leg in out["legs"]}
    assert out["legs_asof"]["tape_trend"] == legs["trend"]["asof"]
    assert out["legs_asof"]["volatility"] == legs["vol"]["asof"]
    if unavailable != "volatility":
        assert captured["conditions"]["complacency"]["vix_pctile"] == 1.0
        assert legs["vol"]["score"] == 12
    if unavailable:
        assert out["n_live_symbols"] > 0
        assert out["live_active"] is False and out["stale"] is True
        assert out["critical_missing"]
        assert out["display"]["score"] == 57  # dated historical fallback only
        assert market_freshness(out, 5, now)["usable"] is False
        if unavailable == "naive_clock":
            assert legs["trend"]["basis"] == "partial"
            assert "QQQ" in out["critical_missing"]
    else:
        assert out["live_active"] is True and out["critical_missing"] == []
        assert out["display"]["score"] == 38
        assert out["display"]["verdict"] == "MIXED"  # preserve two-tick debounce
        assert out["display"]["pending"]["ticks"] == 1
        assert market_freshness(out, 5, now)["usable"] is True


@pytest.mark.parametrize("quote_times,budget,use_vix9d,now,expected", [
    ({"QQQ": "2026-11-05T14:45:30+00:00"}, 20, True, None,
     "2026-11-05T15:05:30+00:00"),
    ({"HYG": "2026-11-05T14:45:10+00:00"}, 20, True, None,
     "2026-11-05T15:10:00+00:00"),
    ({"_VIX9D": "2026-11-05T14:46:05+00:00"}, 20, True, None,
     "2026-11-05T15:06:05+00:00"),
    ({}, 20, False, None, "2026-11-05T15:10:00+00:00"),
    ({}, 18, True, None, "2026-11-05T15:08:00+00:00"),
    ({}, None, True, None, "2026-11-05T15:10:00+00:00"),
    ({name: "2026-11-05T15:04:00+00:00"
      for name in ("SPY", "QQQ", "IWM", "_VIX", "_VIX3M", "_VIX9D")},
     20, True, datetime(2026, 11, 5, 15, 5, 0, 750000, tzinfo=timezone.utc),
     "2026-11-05T15:10:00+00:00"),
], ids=["mixed-required-age", "optional-no-veto", "selected-vix9d", "vix-fallback",
        "configured-budget", "default-budget", "serialized-artifact-cap"])
def test_required_quote_deadline_matches_actual_admitted_inputs(
        monkeypatch, tmp_path, quote_times, budget, use_vix9d, now, expected):
    out, _ = _built_required_clock_feed(
        monkeypatch, tmp_path, quote_times=quote_times, budget=budget,
        use_vix9d=use_vix9d, now=now)
    assert out["live_active"] is True
    assert out["stale_after"] == expected
    assert out["quote_stale_after_min"] == (20 if budget is None else budget)
    assert out["live"]["source_event_time"] == (
        "2026-11-05T15:04:00+00:00" if now else "2026-11-05T14:50:00+00:00")
    if not use_vix9d:
        assert "_VIX9D" not in out["live"]["source_quote_clocks"]


@pytest.mark.parametrize("unavailable", [
    "equities", "volatility", "naive_clock", "missing_clock", "future_clock", "computation",
])
def test_required_quote_deadline_unavailable_inputs_have_no_live_deadline(
        monkeypatch, tmp_path, unavailable):
    out, _ = _built_required_clock_feed(monkeypatch, tmp_path, unavailable=unavailable)
    assert out["live_active"] is False
    assert out.get("stale_after") is None
    assert out["display"]["score"] == 57


@needs_node
@US_PAGES
@pytest.mark.parametrize("failure", ["resume", "http", "json", "network"])
def test_required_quote_expiry_reaches_actual_emitted_feed_consumers(
        monkeypatch, tmp_path, js, failure):
    feed, _ = _built_required_clock_feed(
        monkeypatch, tmp_path, quote_times={"QQQ": "2026-11-05T14:45:30+00:00"})
    responses = {
        "http": "Promise.resolve({ok:false})",
        "json": "Promise.resolve({ok:true,json:function(){return Promise.reject(new Error('bad JSON'));}})",
        "network": "Promise.reject(new Error('offline'))",
    }
    after = """
    out.initial_action = action.children[0].textContent;
    out.initial_score = String(scoreEl.textContent);
    browserNow = Date.parse('2026-11-05T15:06:00Z');
    """
    if failure == "resume":
        after += "EVENT_HANDLERS.visibilitychange();"
    else:
        after += f"""
        requestPending = false;
        fetch = function () {{ return {responses[failure]}; }};
        tick();
        await new Promise(function (resolve) {{ setImmediate(resolve); }});
        """
    after += """
    out.expired_base_verdict = action.getAttribute('data-wtd-base-verdict');
    """
    out = _harness(js.read_text(), feed, "us", now="2026-11-05T15:05:10Z",
                   after=after, poll=failure != "resume")
    assert not out.get("error"), out.get("error")
    assert "unavailable" not in out["initial_action"]
    assert out["initial_score"] == "38"
    assert "unavailable" in out["action"]
    assert out["expired_base_verdict"] == "UNAVAILABLE"
    assert out["score"] == "38"
    assert out["chart_last"]["d"] == "2026-11-05"


@needs_node
@US_PAGES
@pytest.mark.parametrize("deadline,eligible", [
    (None, False),
    ("invalid", False),
    ("2026-11-05T15:10:00", False),
    ("2026-11-05T15:05:59Z", False),
    ("2026-11-05T15:06:00Z", False),
    ("2026-11-05T15:06:00.001Z", True),
])
def test_required_quote_deadline_missing_malformed_and_exact_boundary(js, deadline, eligible):
    feed = _us_feed("2026-11-05", 38, "RISK_OFF", live=True,
                    built="2026-11-05 15:05:00 UTC")
    if deadline is None:
        feed.pop("stale_after", None)
    else:
        feed["stale_after"] = deadline
    out = _harness(js.read_text(), feed, "us", now="2026-11-05T15:06:00Z")
    assert not out.get("error"), out.get("error")
    assert ("unavailable" not in out["action"]) is eligible
    assert out["score"] == ("38" if eligible else str(BAKED_SCORE))


@needs_node
@US_PAGES
def test_required_quote_deadline_cannot_be_laundered_but_actual_new_feed_recovers(
        monkeypatch, tmp_path, js):
    feed, _ = _built_required_clock_feed(
        monkeypatch, tmp_path / "initial",
        quote_times={"QQQ": "2026-11-05T14:45:30+00:00"})
    renewed, _ = _built_required_clock_feed(
        monkeypatch, tmp_path / "renewed",
        now=datetime(2026, 11, 5, 15, 6, tzinfo=timezone.utc),
        quote_times={name: "2026-11-05T15:00:00+00:00"
                     for name in ("SPY", "QQQ", "IWM", "_VIX", "_VIX3M", "_VIX9D")})
    after = """
    browserNow = Date.parse('2026-11-05T15:06:00Z');
    FEED.built = new Date(browserNow).toISOString();
    FEED.live.source_event_time = new Date(browserNow).toISOString();
    patchMacro(FEED);
    out.laundered_action = action.children[0].textContent;
    out.laundered_base = action.getAttribute('data-wtd-base-verdict');
    """ + f"patchMacro({json.dumps(renewed)});" + """
    out.recovered_base = action.getAttribute('data-wtd-base-verdict');
    """
    out = _harness(js.read_text(), feed, "us", now="2026-11-05T15:05:10Z", after=after)
    assert not out.get("error"), out.get("error")
    assert "unavailable" in out["laundered_action"]
    assert out["laundered_base"] == "UNAVAILABLE"
    assert "unavailable" not in out["action"]
    assert out["recovered_base"] == "MIXED"
    assert out["chart_last"]["d"] == "2026-11-05"

#
# No suite unit-tests scripts/build_risk_state.py's pure Python helpers directly
# (tests/test_risk_state.py covers the unrelated engine/risk_state.py; this file
# is the sibling JS-behavior suite for the SAME risk_state.json artifact that
# module's `build()` publishes — its `_us_feed`/`_cn_feed` fixtures already mirror
# that artifact's shape). GD-3R1 adds the real source-market quote clock to that
# artifact's `live` block (`live.source_event_time` / `live.source_quote_clocks`,
# scripts/build_risk_state.py's `_spliced_frames` / `_source_event_time`); these
# classes are the discriminating regression FROZEN SPEC item 5 requires: a
# spliced quote's own `quote_ts` lands in `live.source_quote_clocks` and the max
# of those lands in `live.source_event_time`; an unclocked quote is excluded from
# the max; all-None -> None. Amendments: F3 (synthetic clocks excluded), F5 (naive
# dropped, never assumed UTC), F6 (a quote clock >120s ahead of `now` excluded
# from the max, single-glitch-proof).

def _nightly_close(price: float, n: int = 3) -> pd.Series:
    idx = pd.date_range("2026-08-18", periods=n, freq="D")
    return pd.Series([price] * n, index=idx)


def _live_quote(price: float, quote_ts: str | None, prev_close: float = 100.0,
                delay_min: float = 0.0, synthetic: bool = False) -> dict:
    # Real engine.live_quotes.fetch_quotes() quotes always carry `quote_ts`,
    # `quote_ts_synthetic` (GD-3R1 F3), AND a precomputed `delay_min`
    # (engine/live_quotes.py's `_delay_min`). `delay_min` is supplied explicitly
    # so `live_overlay.staleness()` can judge freshness even in the (synthetic,
    # defensive) case a test wants a spliceable quote whose `quote_ts` is itself
    # None.
    return {"price": price, "prev_close": prev_close, "quote_ts": quote_ts,
            "delay_min": delay_min, "quote_ts_synthetic": synthetic}


class TestSourceEventTime:

    def test_max_of_parseable_clocks_wins(self):
        now = datetime(2026, 8, 21, 9, 6, tzinfo=timezone.utc)
        clocks = {
            "SPY": "2026-08-21T09:00:00+00:00",
            "QQQ": "2026-08-21T09:05:00+00:00",   # newest -> must win
            "IWM": "2026-08-21T08:50:00+00:00",
        }
        assert brs._source_event_time(clocks, now) == "2026-08-21T09:05:00+00:00"

    def test_unclocked_quote_is_excluded_from_the_max(self):
        now = datetime(2026, 8, 21, 9, 6, tzinfo=timezone.utc)
        clocks = {
            "SPY": "2026-08-21T09:00:00+00:00",
            "QQQ": None,   # spliced but carried no quote_ts — must not participate
        }
        assert brs._source_event_time(clocks, now) == "2026-08-21T09:00:00+00:00"

    def test_all_none_or_empty_is_none(self):
        now = datetime(2026, 8, 21, 9, 6, tzinfo=timezone.utc)
        assert brs._source_event_time({"SPY": None, "QQQ": None}, now) is None
        assert brs._source_event_time({}, now) is None

    def test_unparseable_clock_is_excluded_not_fatal(self):
        now = datetime(2026, 8, 21, 9, 6, tzinfo=timezone.utc)
        clocks = {"SPY": "not-a-timestamp", "QQQ": "2026-08-21T09:00:00+00:00"}
        assert brs._source_event_time(clocks, now) == "2026-08-21T09:00:00+00:00"

    def test_naive_clock_is_dropped_not_assumed_utc(self):
        """F5: a naive (tz-less) quote_ts is never coerced to UTC — dropped."""
        now = datetime(2026, 8, 21, 9, 6, tzinfo=timezone.utc)
        clocks = {"SPY": "2026-08-21T09:00:00", "QQQ": "2026-08-21T09:05:00+00:00"}
        assert brs._source_event_time(clocks, now) == "2026-08-21T09:05:00+00:00"

    def test_all_naive_is_none(self):
        now = datetime(2026, 8, 21, 9, 6, tzinfo=timezone.utc)
        assert brs._source_event_time({"SPY": "2026-08-21T09:00:00"}, now) is None

    def test_single_future_glitch_leg_does_not_poison_the_max(self):
        """F6: one glitched/clock-skewed leg (>120s ahead of `now`) must not win
        the max, but a legitimate leg elsewhere still wins normally."""
        now = datetime(2026, 8, 21, 9, 6, tzinfo=timezone.utc)
        clocks = {
            "SPY": "2026-08-21T09:05:00+00:00",       # legit, near now
            "_MOVE": "2027-01-01T00:00:00+00:00",      # glitched far future
        }
        assert brs._source_event_time(clocks, now) == "2026-08-21T09:05:00+00:00"

    def test_wholesale_future_clocks_yield_none(self):
        now = datetime(2026, 8, 21, 9, 6, tzinfo=timezone.utc)
        clocks = {"SPY": "2027-01-01T00:00:00+00:00", "QQQ": "2027-01-01T00:05:00+00:00"}
        assert brs._source_event_time(clocks, now) is None

    def test_clock_within_future_tolerance_still_counts(self):
        now = datetime(2026, 8, 21, 9, 6, 0, tzinfo=timezone.utc)
        clocks = {"SPY": "2026-08-21T09:07:00+00:00"}   # 60s ahead, within 120s tolerance
        assert brs._source_event_time(clocks, now) == "2026-08-21T09:07:00+00:00"

    def test_clock_beyond_future_tolerance_is_excluded(self):
        now = datetime(2026, 8, 21, 9, 6, 0, tzinfo=timezone.utc)
        clocks = {"SPY": "2026-08-21T09:09:00+00:00"}   # 180s ahead, beyond 120s tolerance
        assert brs._source_event_time(clocks, now) is None


class TestSplicedFramesQuoteClocks:

    def test_spliced_quotes_own_clock_is_captured_per_store(self, monkeypatch):
        closes = {"SPY": _nightly_close(500.0), "QQQ": _nightly_close(400.0)}
        monkeypatch.setattr(live_overlay, "read_close", lambda name: closes.get(name))
        now = datetime(2026, 8, 21, 9, 6, tzinfo=timezone.utc)
        quotes = {
            "SPY": _live_quote(505.0, "2026-08-21T09:05:30+00:00", prev_close=500.0),
            "QQQ": _live_quote(404.0, "2026-08-21T09:04:10+00:00", prev_close=400.0),
        }
        spliced, live_close, nightly_close, quote_clocks = brs._spliced_frames(
            quotes, max_chg=10.0, stale_after=20.0, now=now, session_open=True)
        assert set(spliced) == {"SPY", "QQQ"}
        # each store's OWN quote_ts lands in quote_clocks — never a builder wall clock
        assert quote_clocks["SPY"] == "2026-08-21T09:05:30+00:00"
        assert quote_clocks["QQQ"] == "2026-08-21T09:04:10+00:00"
        assert quote_clocks["SPY"] != now.isoformat()
        # and the max of those lands in source_event_time
        assert brs._source_event_time(quote_clocks, now) == "2026-08-21T09:05:30+00:00"

    def test_a_quote_that_fails_usable_is_never_spliced_and_never_clocked(self, monkeypatch):
        """A rejected (limit-move-guard) quote must not appear in quote_clocks at
        all — bounded to exactly the members actually spliced."""
        closes = {"SPY": _nightly_close(500.0)}
        monkeypatch.setattr(live_overlay, "read_close", lambda name: closes.get(name))
        now = datetime(2026, 8, 21, 9, 6, tzinfo=timezone.utc)
        quotes = {"SPY": _live_quote(5000.0, "2026-08-21T09:05:30+00:00", prev_close=500.0)}
        spliced, live_close, nightly_close, quote_clocks = brs._spliced_frames(
            quotes, max_chg=10.0, stale_after=20.0, now=now, session_open=True)
        assert "SPY" not in spliced
        assert "SPY" not in quote_clocks

    def test_a_quote_with_no_quote_ts_still_splices_but_carries_a_none_clock(self, monkeypatch):
        closes = {"SPY": _nightly_close(500.0)}
        monkeypatch.setattr(live_overlay, "read_close", lambda name: closes.get(name))
        now = datetime(2026, 8, 21, 9, 6, tzinfo=timezone.utc)
        quotes = {"SPY": _live_quote(505.0, None, prev_close=500.0)}
        spliced, live_close, nightly_close, quote_clocks = brs._spliced_frames(
            quotes, max_chg=10.0, stale_after=20.0, now=now, session_open=True)
        assert "SPY" in spliced
        assert quote_clocks["SPY"] is None
        assert brs._source_event_time(quote_clocks, now) is None

    def test_nothing_spliced_yields_empty_quote_clocks(self, monkeypatch):
        monkeypatch.setattr(live_overlay, "read_close", lambda name: None)
        now = datetime(2026, 8, 21, 9, 6, tzinfo=timezone.utc)
        spliced, live_close, nightly_close, quote_clocks = brs._spliced_frames(
            {}, max_chg=10.0, stale_after=20.0, now=now, session_open=True)
        assert spliced == {}
        assert quote_clocks == {}
        assert brs._source_event_time(quote_clocks, now) is None

    def test_a_synthetic_flagged_quote_is_excluded_from_the_clock_receipt(self, monkeypatch):
        """F3: a quote whose quote_ts did NOT come from a real market timestamp
        (quote_ts_synthetic=True) must never put its clock in the receipt. Since
        #8606 (rule 6: a synthetic quote clock is no actionable live cash update)
        live_overlay.staleness() calls it stale, so it is not spliced at all: the
        symbol reads its nightly close and has no clock."""
        closes = {"SPY": _nightly_close(500.0)}
        monkeypatch.setattr(live_overlay, "read_close", lambda name: closes.get(name))
        now = datetime(2026, 8, 21, 9, 6, tzinfo=timezone.utc)
        quotes = {"SPY": _live_quote(505.0, "2026-08-21T09:05:30+00:00",
                                     prev_close=500.0, synthetic=True)}
        assert live_overlay.staleness(quotes["SPY"], 20.0, now=now, session_open=True)["reason"] \
            == "synthetic quote timestamp"
        spliced, live_close, nightly_close, quote_clocks = brs._spliced_frames(
            quotes, max_chg=10.0, stale_after=20.0, now=now, session_open=True)
        assert "SPY" not in spliced and "SPY" not in live_close
        assert nightly_close["SPY"] == 500.0
        assert "SPY" not in quote_clocks      # its clock never enters the receipt
        assert brs._source_event_time(quote_clocks, now) is None

    def test_all_synthetic_quotes_yield_none_source_event_time(self, monkeypatch):
        closes = {"SPY": _nightly_close(500.0), "QQQ": _nightly_close(400.0)}
        monkeypatch.setattr(live_overlay, "read_close", lambda name: closes.get(name))
        now = datetime(2026, 8, 21, 9, 6, tzinfo=timezone.utc)
        quotes = {
            "SPY": _live_quote(505.0, "2026-08-21T09:05:30+00:00", prev_close=500.0, synthetic=True),
            "QQQ": _live_quote(404.0, "2026-08-21T09:04:10+00:00", prev_close=400.0, synthetic=True),
        }
        spliced, live_close, nightly_close, quote_clocks = brs._spliced_frames(
            quotes, max_chg=10.0, stale_after=20.0, now=now, session_open=True)
        assert spliced == {} and live_close == {}
        assert nightly_close == {"SPY": 500.0, "QQQ": 400.0}
        assert quote_clocks == {}
        assert brs._source_event_time(quote_clocks, now) is None


# ══ GD-3R1 amendment F3 — engine.live_quotes' quote_ts_synthetic flag ════════════
#
# Engine-level coverage for the two fallback-to-wall-clock paths (polygon
# trade/minute lacking `t`, or day/prev basis; yahoo lacking regularMarketTime)
# lives HERE rather than in tests/test_live_quotes.py: that file exists
# (grepped) but carries NO run: step anywhere under .github/ci/ or
# .github/workflows/ — it is not CI-wired — so a regression added there would be
# invisible to CI. This file IS CI-wired (.github/ci/legacy-jobs.yml), per the
# GD-3R1 commission's explicit fallback instruction for exactly this case.

class TestSyntheticQuoteClockFlag:

    def test_polygon_trade_with_real_t_is_not_synthetic(self):
        from engine import live_quotes as lq
        now = datetime(2026, 6, 21, 15, 0, tzinfo=timezone.utc)
        trade_ns = int(datetime(2026, 6, 21, 14, 50, tzinfo=timezone.utc).timestamp() * 1e9)
        payload = {"tickers": [{"ticker": "AAPL", "lastTrade": {"p": 201.25, "t": trade_ns},
                                "day": {"c": 200.0}, "prevDay": {"c": 198.0}}]}
        q = lq.parse_polygon_snapshot(payload, now=now)["AAPL"]
        assert q["quote_ts_synthetic"] is False

    def test_polygon_trade_without_t_is_synthetic(self):
        from engine import live_quotes as lq
        payload = {"tickers": [{"ticker": "AAPL", "lastTrade": {"p": 201.25},  # no "t"
                                "day": {"c": 200.0}, "prevDay": {"c": 198.0}}]}
        q = lq.parse_polygon_snapshot(payload)["AAPL"]
        assert q["quote_ts_synthetic"] is True

    def test_polygon_day_basis_is_synthetic(self):
        from engine import live_quotes as lq
        payload = {"tickers": [{"ticker": "AAPL", "day": {"c": 200.0}, "prevDay": {"c": 198.0}}]}
        q = lq.parse_polygon_snapshot(payload)["AAPL"]
        assert q["quote_ts_synthetic"] is True

    def test_yahoo_with_regular_market_time_is_not_synthetic(self):
        from engine import live_quotes as lq
        ts_s = int(datetime(2026, 6, 21, 14, 30, tzinfo=timezone.utc).timestamp())
        payload = {"spark": {"result": [{"symbol": "0700.HK", "response": [{"meta": {
            "regularMarketPrice": 412.6, "regularMarketTime": ts_s}}]}]}}
        q = lq.parse_yahoo_spark(payload)["0700.HK"]
        assert q["quote_ts_synthetic"] is False

    def test_yahoo_without_regular_market_time_is_synthetic(self):
        from engine import live_quotes as lq
        payload = {"spark": {"result": [{"symbol": "0700.HK", "response": [{"meta": {
            "regularMarketPrice": 412.6}}]}]}}   # no regularMarketTime
        q = lq.parse_yahoo_spark(payload)["0700.HK"]
        assert q["quote_ts_synthetic"] is True


@needs_node
@RE_PAGES
@pytest.mark.parametrize("deadline,eligible", [
    (None, False),
    ("invalid", False),
    ("2026-11-05T15:05:30", False),
    ("2026-11-05T15:05:29Z", False),
    ("2026-11-05T15:05:30Z", False),
    ("2026-11-05T15:05:31Z", True),
])
def test_required_quote_envelope_client_requires_deadline(js, deadline, eligible):
    feed = _re_feed(source_session="2026-11-05", built="2026-11-05 15:05:00 UTC")
    if deadline is None:
        feed.pop("stale_after")
    else:
        feed["stale_after"] = deadline
    out = _re_harness(js.read_text(encoding="utf-8"), feed, now="2026-11-05T15:05:30Z")
    assert not out.get("error"), out.get("error")
    assert out["chip_hidden"] is (not eligible)
    if not eligible:
        assert out["pending_hidden"] and out["receipt_hidden"]


@needs_node
@RE_PAGES
def test_required_quote_actual_producer_envelope_and_cached_client_expire(monkeypatch, tmp_path, js):
    from scripts import build_live_risk_envelope as blre

    built = datetime(2026, 11, 5, 15, 5, tzinfo=timezone.utc)
    feed, _ = _built_required_clock_feed(
        monkeypatch, tmp_path, now=built,
        quote_times={"QQQ": "2026-11-05T14:45:30+00:00"})
    deadline = datetime(2026, 11, 5, 15, 5, 30, tzinfo=timezone.utc)
    assert datetime.fromisoformat(feed["stale_after"]) == deadline
    settled = tmp_path / "data" / "risk_envelope" / "latest.json"
    settled.parent.mkdir(parents=True, exist_ok=True)
    settled.write_text(json.dumps({
        "source_session": "2026-11-04", "bundle_id": RE_BAKED_BUNDLE,
        "hazard_summary": {"stage": "FRAGILE"}}))
    monkeypatch.setattr(blre, "_risk_envelope_cfg",
                        lambda: {"stale_after_min": 5, "debounce_ticks": 3})
    monkeypatch.setattr(blre, "_emit_materiality_firing",
                        lambda **kw: pytest.fail("expiry fixture must not emit a firing"))

    envelope = blre.build(root=tmp_path, now=built + timedelta(seconds=5))
    assert envelope["live_active"] is True
    assert envelope["stale_after"] is not None
    assert datetime.fromisoformat(envelope["stale_after"]) == deadline
    assert envelope["clocks"]["event_time"] == "2026-11-05T14:50:00.000Z"

    # The initial request remains pending in this DOM fixture. The existing
    # tick's precheck must still withdraw the cached envelope at the deadline.
    after = (
        "out.was_visible = !chip.hidden; "
        "browserNow = Date.parse('2026-11-05T15:05:30Z'); tick();"
    )
    out = _re_harness(js.read_text(encoding="utf-8"), envelope,
                      now="2026-11-05T15:05:05Z", after=after)
    assert not out.get("error"), out.get("error")
    assert out["was_visible"] is True
    assert out["chip_hidden"] and out["pending_hidden"] and out["receipt_hidden"]

    # A new envelope build cannot renew the original source inputs.
    expired = blre.build(root=tmp_path, now=deadline)
    assert expired["live_active"] is False
    assert expired["measured_state"]["usable"] is False
