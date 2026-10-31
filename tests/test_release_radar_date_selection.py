"""Regression tests for the date-scoped Release Radar calendar selector.

The selector lives inline in ``dashboard.html.j2`` rather than in a standalone
asset.  The executable test below therefore evaluates the production function
definitions themselves with a deliberately small DOM/timer harness.  This
keeps the test focused on the interaction contract without adding a browser
dependency to the suite.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "dashboard.html.j2"
SITE = ROOT / "site" / "macro.html"


def _selector_source(path: Path = TEMPLATE) -> str:
    source = path.read_text()
    start = source.index("    function _inlineItemsSignature(")
    end = source.index("    /* Wire every dlg-events calendar card", start)
    return source[start:end]


def test_release_radar_selection_is_date_scoped_idempotent_and_race_safe():
    """Exercise the real selector against grouped cards and controlled timers."""
    driver = f"""
"use strict";

class ClassList {{
  constructor(initial) {{ this.values = new Set(initial || []); }}
  add(name) {{ this.values.add(name); }}
  remove(name) {{ this.values.delete(name); }}
  contains(name) {{ return this.values.has(name); }}
  toggle(name, force) {{
    if (force === undefined) force = !this.values.has(name);
    if (force) this.values.add(name);
    else this.values.delete(name);
    return force;
  }}
}}

class Card {{
  constructor(date, classes) {{
    this.attrs = {{ "data-cal-date": date }};
    this.classList = new ClassList(classes);
  }}
  getAttribute(name) {{ return this.attrs[name] ?? null; }}
  setAttribute(name, value) {{ this.attrs[name] = String(value); }}
  removeAttribute(name) {{ delete this.attrs[name]; }}
}}

let bodyWrites = 0;
let bodyHTML = "";
const body = {{
  classList: new ClassList(),
  querySelectorAll: function () {{ return []; }}
}};
Object.defineProperty(body, "innerHTML", {{
  get: function () {{ return bodyHTML; }},
  set: function (value) {{ bodyWrites += 1; bodyHTML = String(value); }}
}});
const dateHeader = {{ innerHTML: "" }};
const dateSub = {{ innerHTML: "" }};

const gdp = new Card("2026-07-30", ["rr-select"]);
const pce = new Card("2026-07-30", ["rr-select"]);
const claims = new Card("2026-07-30", ["rr-select"]);
const nfp = new Card("2026-08-07", ["rr-select"]);
const cpi = new Card("2026-08-12", ["rr-select"]);
/* A same-date Fed card is present in the calendar, but is not a radar selector. */
const fomc = new Card("2026-07-30", ["rr-fed"]);
const allCards = [gdp, pce, claims, nfp, cpi, fomc];

global.document = {{
  getElementById: function (id) {{
    if (id === "rr-inline-body") return body;
    if (id === "rr-inline-date") return dateHeader;
    if (id === "rr-inline-sub") return dateSub;
    return null;
  }},
  querySelectorAll: function (selector) {{
    if (selector !== "#dlg-events .mx5-dlg-cal-card.rr-select") {{
      throw new Error("unexpected selector: " + selector);
    }}
    return allCards.filter(function (card) {{
      return card.classList.contains("rr-select");
    }});
  }}
}};
global.window = {{
  matchMedia: function () {{ return {{ matches: false }}; }}
}};

let timerId = 0;
const timers = [];
global.setTimeout = function (fn, delay) {{
  const timer = {{ id: ++timerId, fn: fn, delay: delay, cancelled: false }};
  timers.push(timer);
  return timer;
}};
global.clearTimeout = function (timer) {{ timer.cancelled = true; }};
global.requestAnimationFrame = function (fn) {{ fn(); }};

const _rrItems = [
  {{ release_date: "2026-07-30", release: "GDP" }},
  {{ release_date: "2026-07-30", release: "PCE" }},
  {{ release_date: "2026-07-30", release: "Initial Claims" }},
  {{ release_date: "2026-08-07", release: "NFP" }},
  {{ release_date: "2026-08-12", release: "CPI" }}
];
function _itemsForDate(dateStr) {{
  return _rrItems.filter(function (item) {{ return item.release_date === dateStr; }});
}}
function renderCard(item) {{ return "<article class=rr-card>" + item.release + "</article>"; }}
function _rrUpdateSnapshotNotice() {{}}
function _inlineEmptyHTML() {{ return "<div class=empty></div>"; }}
function _setInlineHeader(dateStr) {{ dateHeader.value = dateStr; }}
function _rrInlineBody() {{ return body; }}
function _rrInlineDateEl() {{ return dateHeader; }}
function openModal() {{}}

let _rrInlineDate = null;
let _rrInlineSignature = null;
let _rrInlineSwapToken = 0;
let _rrInlineSwapTimer = null;

{_selector_source()}

function assert(condition, message) {{
  if (!condition) throw new Error(message);
}}
function isActive(card) {{ return card.classList.contains("rr-active"); }}

/* One date selection highlights every release on that date. */
selectInlineDate("2026-07-30", gdp, true);
assert(isActive(gdp) && isActive(pce) && isActive(claims),
  "all same-date Release Radar cards were not activated");
for (const card of [gdp, pce, claims]) {{
  assert(card.attrs["aria-pressed"] === "true", "active card lacks aria-pressed=true");
  assert(card.attrs["aria-current"] === "date", "active card lacks aria-current=date");
}}
assert(!isActive(nfp) && nfp.attrs["aria-pressed"] === "false",
  "a different-date card was activated");
assert(!isActive(fomc) && fomc.attrs["aria-pressed"] === undefined,
  "FOMC/Fed Path card leaked into the date selection group");
assert(bodyWrites === 1, "initial selection did not paint exactly once");
assert(bodyHTML.includes("GDP") && bodyHTML.includes("PCE") && bodyHTML.includes("Initial Claims"),
  "same-date panel did not contain every release");

/* Clicking another event on the already-selected date must be a true no-op. */
const firstHTML = bodyHTML;
const timerCountBeforeRepeat = timers.length;
selectInlineDate("2026-07-30", pce, false);
assert(bodyWrites === 1, "repeat same-date click repainted the panel");
assert(bodyHTML === firstHTML, "repeat same-date click changed panel markup");
assert(timers.length === timerCountBeforeRepeat,
  "repeat same-date click scheduled a fake cross-fade");

/* A new date clears the complete old group and activates the new one. */
selectInlineDate("2026-08-07", nfp, true);
for (const card of [gdp, pce, claims]) {{
  assert(!isActive(card), "old date remained active after selecting a new date");
  assert(card.attrs["aria-pressed"] === "false", "old date retained aria-pressed=true");
  assert(card.attrs["aria-current"] === undefined, "old date retained aria-current");
}}
assert(isActive(nfp) && nfp.attrs["aria-pressed"] === "true",
  "new date was not activated");
assert(bodyWrites === 2 && bodyHTML.includes("NFP"),
  "new date did not repaint with its own release");

/* Rapid cross-fades: even if a cancelled callback runs, its token cannot paint. */
selectInlineDate("2026-07-30", claims, false);
const staleTimer = timers[timers.length - 1];
assert(staleTimer.delay === 130, "first cross-fade timer was not scheduled");
selectInlineDate("2026-08-12", cpi, false);
const currentTimer = timers[timers.length - 1];
assert(staleTimer !== currentTimer && staleTimer.cancelled,
  "superseded cross-fade timer was not cancelled");
const writesBeforeStaleCallback = bodyWrites;
staleTimer.fn();
assert(bodyWrites === writesBeforeStaleCallback,
  "stale timer callback painted over the current selection");
assert(isActive(cpi) && !isActive(gdp) && !isActive(pce) && !isActive(claims),
  "latest date selection was not retained while its panel paint was pending");
currentTimer.fn();
assert(bodyWrites === writesBeforeStaleCallback + 1 && bodyHTML.includes("CPI"),
  "current timer did not paint the latest date");
"""
    result = subprocess.run(
        ["node", "-e", driver],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr


def test_fomc_wiring_stays_outside_grouped_release_radar_selection():
    """Pin the FOMC early return and the selector's rr-select-only boundary."""
    source = TEMPLATE.read_text()

    sync_start = source.index("    function _syncInlineDateSelection(")
    sync_end = source.index("    function selectInlineDate(", sync_start)
    sync_source = source[sync_start:sync_end]
    assert "#dlg-events .mx5-dlg-cal-card.rr-select" in sync_source
    assert ".rr-fed" not in sync_source

    fomc_start = source.index("        if (calType === 'FOMC'){")
    selectable_start = source.index("        /* selectable card */", fomc_start)
    fomc_branch = source[fomc_start:selectable_start]
    assert "card.classList.add('rr-fed')" in fomc_branch
    assert "return;" in fomc_branch
    assert "card.classList.add('rr-select')" not in fomc_branch


def test_idempotence_and_timer_token_guards_are_ordered_before_mutation():
    """Static ordering guard makes accidental refactors fail with a useful cause."""
    source = TEMPLATE.read_text()
    start = source.index("    function selectInlineDate(")
    end = source.index("    function _prefReducedRR(", start)
    selector = source[start:end]

    unchanged_guard = selector.index("if (!immediate && unchanged) return;")
    body_markup = selector.index("body.innerHTML = bodyHTML;")
    timer_creation = selector.index("_rrInlineSwapTimer = setTimeout(")
    assert unchanged_guard < body_markup
    assert unchanged_guard < timer_creation

    token_increment = selector.index("var token = ++_rrInlineSwapToken;")
    token_check = selector.index("if (token !== _rrInlineSwapToken) return;")
    assert token_increment < token_check < body_markup


def test_rendered_macro_contains_the_same_date_selector_logic():
    assert _selector_source(SITE) == _selector_source(TEMPLATE)


SOURCE = TEMPLATE.read_text()


def _extract(start: str, end: str) -> str:
    left = SOURCE.index(start)
    return SOURCE[left:SOURCE.index(end, left)]


def _node(script: str) -> None:
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, capture_output=True, text=True, timeout=20
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_release_radar_countdowns_use_live_new_york_calendar_day():
    """An Oct 16 snapshot's baked 'in 13d' must read six days on Oct 23."""
    source = _extract("    function _rrEasternDay(){", "    function _rrMetaChip")
    driver = r"""
const assert = require('assert');
const NativeDate = Date;
let now = NativeDate.parse('2026-10-23T07:15:00Z');
class Clock extends NativeDate {
  constructor(...args) { super(...(args.length ? args : [now])); }
  static now() { return now; }
}
global.Date = Clock;
""" + source + r"""
assert.strictEqual(_rrDaysUntil('2026-10-29'), 6);
assert.strictEqual(_rrCountdownLabels(_rrDaysUntil('2026-10-29')).en, '6 days away');
assert.strictEqual(_rrDaysUntil('2026-10-22'), -1);
assert.strictEqual(_rrCountdownLabels(-1).en, '1 days since release');
now = NativeDate.parse('2026-10-24T03:59:00Z'); // Still Oct 23 Eastern
assert.strictEqual(_rrDaysUntil('2026-10-29'), 6);
now = NativeDate.parse('2026-10-24T04:00:00Z'); // Eastern midnight
assert.strictEqual(_rrDaysUntil('2026-10-29'), 5);
now = NativeDate.parse('2026-11-01T05:30:00Z'); // DST fallback
assert.strictEqual(_rrDaysUntil('2026-11-02'), 1);
now = NativeDate.parse('2026-11-01T06:30:00Z');
assert.strictEqual(_rrDaysUntil('2026-11-02'), 1);
assert.strictEqual(_rrDaysUntil('2026-02-30'), null);
assert.strictEqual(_rrDaysUntil(null), null);
"""
    _node(driver)
    assert "var daysTo = _rrDaysUntil(item.release_date)" in SOURCE
    assert "var currentDays = _rrDaysUntil(item.release_date)" in SOURCE
    assert "_rrCountdownLabels(item.days_to)" not in SOURCE
    assert "var daysTo = item.days_to" not in SOURCE


def test_stale_forecast_snapshot_disclosed_without_claiming_live_models():
    source = _extract("    function _rrSnapshotNotice(){", "    function _rrUpdateSnapshotNotice(){")
    driver = (
        "const assert = require('assert');\n"
        "var _rrForecastAsOf = '2026-10-16T18:18:59Z';\n"
        "var _rrForecastFailed = false;\n"
        + source
        + """
const oldNow = Date.now;
Date.now = () => Date.parse('2026-10-23T07:15:00Z');
assert(_rrSnapshotNotice().en.includes('last-known'));
assert(_rrSnapshotNotice().en.includes('Oct 16'));
_rrForecastAsOf = '2026-10-23T07:14:00Z';
assert.strictEqual(_rrSnapshotNotice(), null);
_rrForecastFailed = true;
assert(_rrSnapshotNotice().en.includes('refresh unavailable'));
_rrForecastAsOf = '';
assert(_rrSnapshotNotice().en.includes('no live model estimate'));
Date.now = oldNow;
"""
    )
    _node(driver)


def test_forecast_refresh_coalesces_requests_retains_last_good_and_revalidates():
    source = _extract("    var _rrForecastSignature = null;", "    /* Deep-link hook:")
    driver = r"""
const assert = require('assert');
let requests = [];
let listeners = {};
let tick;
let renders = [];
let clocks = 0, notices = 0;
let _rrForecastAsOf = null, _rrForecastFailed = false;
global.document = {
  hidden:false,
  addEventListener:(name,cb)=>{listeners[name]=cb;}
};
global.window = { addEventListener:(name,cb)=>{listeners[name]=cb;} };
global.fetch = (url,opts) => new Promise((resolve,reject) => {
  assert.strictEqual(url,'macrodata/release_forecast.json');
  assert.strictEqual(opts.cache,'no-store');
  requests.push({resolve,reject});
});
global.setInterval = (cb,ms) => { assert.strictEqual(ms,60000); tick=cb; };
function renderRadar(value){ renders.push(value); }
function _rrUpdateCountdowns(){ clocks += 1; }
function _rrUpdateSnapshotNotice(){ notices += 1; }
""" + source + r"""
async function drain(){ await new Promise(setImmediate); }
(async function(){
  assert.strictEqual(requests.length,1);
  tick(); listeners.focus(); listeners.visibilitychange();
  assert.strictEqual(requests.length,1,'pending request must coalesce');
  let payload = {asof:'2026-10-23T07:00:00Z',upcoming:[{release:'PCE'}]};
  requests[0].resolve({ok:true,json:async()=>payload});
  await drain();
  assert.strictEqual(renders.length,1);
  assert.strictEqual(_rrForecastFailed,false);
  tick();
  assert.strictEqual(requests.length,2);
  requests[1].resolve({ok:true,json:async()=>payload});
  await drain();
  assert.strictEqual(renders.length,1,'identical snapshot must retain DOM');
  tick();
  requests[2].reject(new Error('offline'));
  await drain();
  assert.strictEqual(_rrForecastFailed,true);
  assert.strictEqual(renders.length,1,'failure must preserve last-good snapshot');
  document.hidden=true;
  tick(); assert.strictEqual(requests.length,3,'hidden page must not fetch');
  document.hidden=false;
  listeners.visibilitychange();
  assert.strictEqual(requests.length,4,'visibility should revalidate');
  payload = {asof:'2026-10-23T07:30:00Z',upcoming:[{release:'GDP'}]};
  requests[3].resolve({ok:true,json:async()=>payload});
  await drain();
  assert.strictEqual(renders.length,2);
  assert.strictEqual(_rrForecastFailed,false);
  assert(clocks>=3 && notices>=4);
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    _node(driver)
