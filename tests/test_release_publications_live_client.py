"""Contracts for the official-event progressive-enhancement client."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "release_publications_live.js"
SITE = ROOT / "site" / "release_publications_live.js"


def test_release_publication_client_copies_are_identical():
    assert TEMPLATE.read_bytes() == SITE.read_bytes(), (
        "templates/release_publications_live.js and site/release_publications_live.js "
        "must be byte-identical"
    )


def test_release_publication_client_uses_et_lifecycle_and_safe_sources():
    driver = f"""
const fs = require("fs");
const vm = require("vm");
global.window = {{ location: {{ href: "https://www.mastermind-x.com/macro.html" }} }};
global.document = {{
  readyState: "loading",
  addEventListener: function () {{}}
}};
vm.runInThisContext(fs.readFileSync({json.dumps(str(TEMPLATE))}, "utf8"));
const api = window.__mmReleasePublicationTest;
if (!api) throw new Error("test API missing");
if (api.easternDateKey(new Date("2026-07-30T00:00:01Z")) !== "2026-07-29") {{
  throw new Error("UTC evening boundary did not remain on the ET event date");
}}
const event = {{ date: "2026-07-29", time_et: "14:00" }};
if (api.eventHasPassed(event, new Date("2026-07-29T17:59:00Z"))) {{
  throw new Error("event advanced before scheduled ET time");
}}
if (!api.eventHasPassed(event, new Date("2026-07-29T18:00:00Z"))) {{
  throw new Error("event did not advance at scheduled ET time");
}}
if (!api.safeOfficialUrl("https://www.federalreserve.gov/example")) {{
  throw new Error("official Fed URL rejected");
}}
if (api.safeOfficialUrl("https://federalreserve.gov.evil.example/payload")) {{
  throw new Error("lookalike source URL accepted");
}}
const coldStartRow = {{
  source_released_at: "2026-07-29T18:00:15Z",
  detected_at: "2026-07-30T01:00:00Z"
}};
if (api.officialReleaseTime(coldStartRow) !== "14:00 ET") {{
  throw new Error("official release time was replaced by cold-start detection time");
}}
const freshNow = new Date("2026-07-29T18:03:00Z");
if (!api.payloadIsFresh({{ built: "2026-07-29T18:01:00Z" }}, freshNow)) {{
  throw new Error("fresh sidecar was rejected");
}}
if (api.payloadIsFresh({{ built: "2026-07-29T17:59:00Z" }}, freshNow)) {{
  throw new Error("stale sidecar retained live status");
}}
const radar = api.radarState(
  [{{ type: "FOMC", actual: {{ headline_en: "Old result" }} }}],
  [{{ type: "GDP" }}]
);
if (radar.kind !== "awaiting" || radar.en.indexOf("GDP") < 0) {{
  throw new Error("active verification did not outrank an older publication");
}}
const sameDayPublications = [
  {{
    event_id: "GDP:2026-07-30:08:30",
    type: "GDP",
    date: "2026-07-30",
    data_ready: true,
    actual: {{ headline_en: "GDP rose 2.1%" }}
  }},
  {{
    event_id: "PCE:2026-07-30:08:30",
    type: "PCE",
    date: "2026-07-30",
    data_ready: true,
    actual: {{ headline_en: "Core PCE rose 0.2%" }}
  }}
];
const sameDayAwaiting = [{{
  event_id: "CLAIMS:2026-07-30:08:30",
  type: "CLAIMS",
  date: "2026-07-30"
}}];
const sameDayGroup = api.activeReleaseGroup(sameDayPublications, sameDayAwaiting);
if (!sameDayGroup || sameDayGroup.total !== 3 ||
    sameDayGroup.verified.length !== 2 || sameDayGroup.awaiting.length !== 1) {{
  throw new Error("same-day release lifecycle was not grouped");
}}
const sameDaySummary = api.releaseGroupSummary(sameDayGroup);
["GDP", "PCE", "CLAIMS", "2 verified results", "1 awaiting official source"].forEach(
  function (part) {{
    if (sameDaySummary.en.indexOf(part) < 0) {{
      throw new Error("same-day summary omitted " + part);
    }}
  }}
);
if (sameDaySummary.zh.indexOf("2 个结果已核验") < 0 ||
    sameDaySummary.zh.indexOf("1 个正在等待官方来源") < 0) {{
  throw new Error("same-day summary is not bilingual");
}}
const groupedRadar = api.radarState(sameDayPublications, sameDayAwaiting);
if (groupedRadar.kind !== "awaiting" || groupedRadar.count !== 3 ||
    groupedRadar.en.indexOf("GDP") < 0 ||
    groupedRadar.en.indexOf("PCE") < 0 ||
    groupedRadar.en.indexOf("CLAIMS") < 0) {{
  throw new Error("radar banner collapsed a same-day group to one release");
}}
const priorDayPlusGroup = api.activeReleaseGroup(
  [{{
    event_id: "FOMC:2026-07-29:14:00",
    type: "FOMC",
    date: "2026-07-29",
    data_ready: true
  }}].concat(sameDayPublications),
  sameDayAwaiting
);
if (priorDayPlusGroup.total !== 3 || priorDayPlusGroup.names.indexOf("FOMC") >= 0) {{
  throw new Error("same-day summary included an older retained release");
}}
const singleRadar = api.radarState(
  [{{ type: "GDP", date: "2026-07-30",
      actual: {{ headline_en: "GDP rose 2.1%" }} }}],
  []
);
if (singleRadar.en !== "GDP rose 2.1%" || singleRadar.count) {{
  throw new Error("single-release banner output changed");
}}
const latestSingleRadar = api.radarState(
  [{{ type: "GDP", date: "2026-07-30",
      actual: {{ headline_en: "GDP rose 2.1%" }} }}],
  [{{ type: "FOMC", date: "2026-07-29" }}]
);
if (latestSingleRadar.kind !== "published" ||
    latestSingleRadar.en !== "GDP rose 2.1%") {{
  throw new Error("older retained verification displaced the latest release date");
}}
const duplicateTypeRows = api.awaitingEvents({{
  events: [
    {{
      event_id: "CLAIMS:2026-07-30:08:30:A",
      type: "CLAIMS",
      date: "2026-07-30",
      time_et: "08:30",
      status: "awaiting_publication"
    }},
    {{
      event_id: "CLAIMS:2026-07-30:08:30:B",
      type: "CLAIMS",
      date: "2026-07-30",
      time_et: "08:30",
      status: "awaiting_publication"
    }}
  ]
}}, new Date("2026-07-30T13:00:00Z"), {{
  "event:CLAIMS:2026-07-30:08:30:A": true,
  "CLAIMS:2026-07-30": true
}});
if (duplicateTypeRows.length !== 1 ||
    duplicateTypeRows[0].event_id !== "CLAIMS:2026-07-30:08:30:B") {{
  throw new Error("event identity collapsed distinct same-type releases");
}}
const overnight = api.awaitingEvents({{
  events: [{{
    type: "FOMC",
    date: "2026-07-29",
    time_et: "14:00",
    status: "published_unparsed"
  }}]
}}, new Date("2026-07-30T05:00:00Z"), {{}});
if (overnight.length !== 1) {{
  throw new Error("prior-day FOMC verification disappeared after ET midnight");
}}
const unparsedPayload = {{
  publications: [{{
    type: "FOMC",
    date: "2026-07-29",
    status: "published_unparsed",
    data_ready: false,
    detected_at: "2026-07-30T00:50:00Z"
  }}],
  events: [{{
    type: "FOMC",
    date: "2026-07-29",
    time_et: "14:00",
    status: "published_unparsed",
    data_ready: false
  }}]
}};
const detectedRows = api.recentPublications(
  unparsedPayload, new Date("2026-07-30T01:00:00Z"));
if (detectedRows.length !== 1 || detectedRows[0].status !== "published_unparsed") {{
  throw new Error("published-but-unparsed event was not routed as detected");
}}
if (api.awaitingEvents(
    unparsedPayload,
    new Date("2026-07-30T01:00:00Z"),
    {{ "FOMC:2026-07-29": true }}
  ).length !== 0) {{
  throw new Error("detected publication was mislabeled as awaiting release");
}}
if (api.radarState(detectedRows, []).kind !== "published") {{
  throw new Error("detected publication did not reach publication UI state");
}}
const detectedAfter25h = api.recentPublications(
  unparsedPayload, new Date("2026-07-31T02:00:00Z"));
if (detectedAfter25h.length !== 1) {{
  throw new Error("unparsed publication disappeared after the 24h result window");
}}
if (api.awaitingEvents(
    unparsedPayload,
    new Date("2026-07-31T02:00:00Z"),
    {{ "FOMC:2026-07-29": true }}
  ).length !== 0) {{
  throw new Error("T+25h detected publication regressed to awaiting release");
}}
const expiringPayload = {{
  publications: [{{
    type: "FOMC",
    date: "2026-07-29",
    status: "published",
    detected_at: "2026-07-29T06:00:00Z"
  }}]
}};
if (api.recentPublications(
    expiringPayload, new Date("2026-07-30T05:00:00Z")).length !== 1) {{
  throw new Error("T+23h verified result expired too early");
}}
if (api.recentPublications(
    expiringPayload, new Date("2026-07-30T07:00:00Z")).length !== 0) {{
  throw new Error("T+25h verified result remained active");
}}
const restored = {{
  publications: [{{ event_id: "cpi:2026-10-14", status: "published", data_ready: true,
    date: "2026-10-14", detected_at: "2026-10-14T12:31:17Z",
    verified_at: "2026-10-31T06:00:00Z", actual: {{ headline_mom: 0.6 }} }}]
}};
const afterRepair = new Date("2026-10-31T06:01:00Z");
if (api.recentPublications(restored, afterRepair, true).length !== 1 ||
    api.recentPublications(restored, afterRepair).length !== 0 ||
    api.recentPublications(restored, new Date("2026-11-01T06:00:01Z"), true).length !== 0) {{
  throw new Error("a newly recovered historical report must be visible in the modal for 24h only");
}}
if (api.trackPrimaryState(true) || !api.trackPrimaryState(false)) {{
  throw new Error("active-to-expired primary transition was not detected");
}}
if (api.rowMatchesText({{ type: "FOMC", label: "FOMC rate decision" }},
    "GDP and PCE release today")) {{
  throw new Error("retained FOMC result matched a different current event");
}}
if (!api.rowMatchesText({{ type: "FOMC", label: "FOMC rate decision" }},
    "FOMC rate decision today")) {{
  throw new Error("matching FOMC surface was not recognized");
}}
api.notePollFailure(freshNow);
if (api.freshness() !== "stale") {{
  throw new Error("poll failure did not downgrade an uninitialized live feed");
}}
"""
    result = subprocess.run(
        ["node", "-e", driver],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr


ACTION_PLAN_DRIVER = r"""
const fs = require("fs");
const vm = require("vm");

// Minimal DOM. Only class-compound selectors resolve; every other selector
// matches nothing, which is exactly how the other patch helpers behave on a page
// that lacks those surfaces (they no-op instead of throwing).
function TextNode(value) {
  this.nodeValue = String(value);
  this.childNodes = [];
  this.parentNode = null;
}
Object.defineProperty(TextNode.prototype, "textContent", {
  get: function () { return this.nodeValue; },
  set: function (value) { this.nodeValue = String(value); }
});

function El(tag) {
  this.tagName = String(tag).toUpperCase();
  this.childNodes = [];
  this.parentNode = null;
  this.attributes = {};
  this.className = "";
  var self = this;
  this.classList = {
    add: function () {
      Array.prototype.slice.call(arguments).forEach(function (name) {
        if (self._classes().indexOf(name) < 0) {
          self.className = self.className ? self.className + " " + name : name;
        }
      });
    },
    remove: function () {
      var drop = Array.prototype.slice.call(arguments);
      self.className = self._classes().filter(function (name) {
        return drop.indexOf(name) < 0;
      }).join(" ");
    },
    contains: function (name) { return self._classes().indexOf(name) >= 0; }
  };
}
El.prototype._classes = function () {
  return String(this.className || "").split(/\s+/).filter(Boolean);
};
El.prototype.appendChild = function (node) {
  node.parentNode = this;
  this.childNodes.push(node);
  return node;
};
El.prototype.getAttribute = function (name) {
  if (name === "class") return this.className;
  return Object.prototype.hasOwnProperty.call(this.attributes, name) ?
    this.attributes[name] : null;
};
El.prototype.setAttribute = function (name, value) {
  if (name === "class") { this.className = String(value); return; }
  this.attributes[name] = String(value);
};
Object.defineProperty(El.prototype, "textContent", {
  get: function () {
    return this.childNodes.map(function (node) { return node.textContent; }).join("");
  },
  set: function (value) {
    this.childNodes = [];
    if (String(value) !== "") this.appendChild(new TextNode(value));
  }
});
El.prototype._descendants = function () {
  var found = [];
  this.childNodes.forEach(function (node) {
    if (node instanceof El) {
      found.push(node);
      found = found.concat(node._descendants());
    }
  });
  return found;
};
function selectorMatches(el, selector) {
  if (!/^(\.[A-Za-z0-9_-]+)+$/.test(selector)) return false;
  return selector.split(".").filter(Boolean).every(function (name) {
    return el.classList.contains(name);
  });
}
El.prototype.querySelectorAll = function (selector) {
  return this._descendants().filter(function (el) {
    return selectorMatches(el, selector);
  });
};
El.prototype.querySelector = function (selector) {
  return this.querySelectorAll(selector)[0] || null;
};

const root = new El("div");
global.window = { location: { href: "https://www.mastermind-x.com/macro.html" } };
global.document = {
  readyState: "loading",
  addEventListener: function () {},
  createElement: function (tag) { return new El(tag); },
  createTextNode: function (value) { return new TextNode(value); },
  getElementById: function () { return null; },
  querySelector: function (selector) { return root.querySelector(selector); },
  querySelectorAll: function (selector) { return root.querySelectorAll(selector); }
};

vm.runInThisContext(fs.readFileSync(__TEMPLATE_PATH__, "utf8"));
const api = window.__mmReleasePublicationTest;
if (!api) throw new Error("test API missing");

function freshActionRow() {
  root.childNodes = [];
  const label = new El("div");
  label.className = "mx5-action-label";
  const english = new El("span");
  english.className = "l-en";
  english.textContent = "GDP release today: expect noise; ignore the first move.";
  const chinese = new El("span");
  chinese.className = "l-zh";
  chinese.textContent = "GDP 发布今日：波动会放大，忽略初动。";
  label.appendChild(english);
  label.appendChild(chinese);
  root.appendChild(label);
  return label;
}
function readPair(label) {
  return {
    en: label.querySelector(".l-en").textContent,
    zh: label.querySelector(".l-zh").textContent
  };
}
function check(actualValue, expected, what) {
  if (actualValue !== expected) {
    throw new Error(what + "\n  expected: " + expected + "\n  actual:   " + actualValue);
  }
}

// A summary carrying a prospective word ("today") is the case that proves the
// generic .l-en sweep still leaves this row alone now that the sentinel span is
// gone: the sweep's isProspective test matches this text.
const verifiedRow = {
  event_id: "GDP:2026-07-30:08:30",
  type: "GDP",
  label: "GDP release",
  label_zh: "GDP 发布",
  date: "2026-07-30",
  data_ready: true,
  actual: { summary_en: "GDP rose 2.1% today.", summary_zh: "GDP 今日上升 2.1%。" }
};

let label = freshActionRow();
api.patchProspectiveCopy(verifiedRow, true);
let pair = readPair(label);
check(pair.en, "Result: GDP rose 2.1% today.", "verified row lost its stance word");
check(pair.zh, "结果：GDP 今日上升 2.1%。", "verified zh row lost its stance word");
if (label.querySelector(".mx5-action-verb")) {
  throw new Error("the CSS-less .mx5-action-verb chip came back");
}
if (/(Result|Status)[^:\s]/.test(pair.en)) {
  throw new Error("stance word is jammed against the sentence: " + pair.en);
}
if (/(结果|状态)[^：]/.test(pair.zh)) {
  throw new Error("zh stance word is jammed against the sentence: " + pair.zh);
}

// Re-poll: the row must survive its own second pass unchanged, and the spans are
// rebuilt each time so the nodes have to be re-read.
api.patchProspectiveCopy(verifiedRow, true);
pair = readPair(label);
check(pair.en, "Result: GDP rose 2.1% today.",
  "a second poll flattened the row to the generic fallback");
check(pair.zh, "结果：GDP 今日上升 2.1%。",
  "a second poll flattened the zh row to the generic fallback");

// Awaiting verification: the same sentence shape, no chip.
label = freshActionRow();
api.patchProspectiveCopy({
  event_id: "GDP:2026-07-30:08:30",
  type: "GDP",
  label: "GDP release",
  label_zh: "GDP 发布",
  date: "2026-07-30",
  data_ready: false,
  actual: {}
}, true);
pair = readPair(label);
check(pair.en,
  "Status: GDP release published — verified values are unavailable.",
  "awaiting row copy changed");
check(pair.zh, "状态：GDP 发布官方已发布 — 核验数据暂不可用。",
  "awaiting zh row copy changed");

// Verified with no extracted summary must not claim a result and deny it in the
// same breath ("Result: … facts are being extracted").
label = freshActionRow();
api.patchProspectiveCopy({
  event_id: "GDP:2026-07-30:08:30",
  type: "GDP",
  label: "GDP release",
  label_zh: "GDP 发布",
  date: "2026-07-30",
  data_ready: true,
  actual: {}
}, true);
pair = readPair(label);
check(pair.en, "Result: GDP release released — see verified outcome.",
  "verified fallback copy changed");
check(pair.zh, "结果：GDP 发布已发布 — 查看核验结果。",
  "verified zh fallback copy changed");
"""


def test_action_plan_row_reads_as_a_sentence_not_a_styleless_chip():
    """The stance word is sentence text; `.mx5-action-verb` had no CSS anywhere.

    Drives the real client against a synthetic release row: the retired span was
    also the sentinel that kept the generic `.l-en` sweep off these rows, so this
    pins both the rendered copy and the sweep's hands-off behaviour.
    """
    driver = ACTION_PLAN_DRIVER.replace("__TEMPLATE_PATH__", json.dumps(str(TEMPLATE)))
    result = subprocess.run(
        ["node", "-e", driver],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_release_publication_client_patches_all_event_surfaces():
    source = TEMPLATE.read_text()
    for contract in (
        "America/New_York",
        "mx-live-event-outcomes",
        ".mx5-dlg-cal-card",
        ".mx5-tl-item",
        ".mx5-events-sub",
        '.wnx-card[href="#dlg-events"]',
        "awaiting official source",
        "Official result · verified",
        '.ms-sig[data-ms-dlg="dlg-events"]',
        ".mx5-action-label",
        ".aib2-watch-row",
        ".aib2-cat-read",
        "Update delayed",
        "published_unparsed",
        "Official publication detected — result verification underway",
        "published — verified values are unavailable",
        'data-live-event-id',
        "FOMC (?:decision|statement)",
        "data-live-action-plan",
        "activeReleaseGroup",
        "patchEventsFaceGroup",
        "patchWhereNextGroup",
        "Same-day releases",
        "official results · live",
    ):
        assert contract in source
    assert "toISOString().slice(0, 10)" not in source


def test_release_publication_client_covers_actual_stale_macro_surfaces():
    """Pin selectors against a stable fixture from the rendered incident page."""
    page = (ROOT / "tests" / "fixtures" / "macro_fomc_stale_surfaces.html").read_text()
    source = TEMPLATE.read_text()
    stale_fixture_markers = {
        'data-ms-dlg="dlg-events"': '.ms-sig[data-ms-dlg="dlg-events"]',
        "FOMC rate decision: expect noise": ".mx5-action-label",
        "FOMC (Jul 29)": ".aib2-watch-row",
        "The immediate hurdle is the FOMC decision": ".aib2-cat-read",
        "Major event on deck": ".mx5-alert-item.warn",
        "FOMC rate decision 07-29": ".v2chip",
    }
    for stale_text, runtime_selector in stale_fixture_markers.items():
        assert stale_text in page, f"expected fixture marker missing: {stale_text}"
        assert runtime_selector in source, (
            f"live client does not supersede {stale_text!r}"
        )
    current_page = (ROOT / "site" / "macro.html").read_text()
    assert 'id="sx-events-v2"' in current_page
    assert 'id="dlg-events"' in current_page
    assert "release_publications_live.js" in current_page


def test_new_live_labels_have_bilingual_pairs():
    source = TEMPLATE.read_text()
    for english, chinese in (
        ("Official source ↗", "官方来源 ↗"),
        ("Official statement ↗", "官方声明 ↗"),
        ("Detected ", "检测于 "),
        ("Last checked ", "上次检查 "),
        ("Awaiting official release", "等待官方发布"),
        ("Update delayed", "更新延迟"),
        ("Last verified result", "上次核验结果"),
        ("No active live result", "当前无实时结果"),
        ("Scheduled time passed · verifying official source", "预定时间已过 · 正在核验官方来源"),
    ):
        assert english in source
        assert chinese in source


def test_release_publication_client_uses_current_immutable_asset_hash():
    from scripts.optimize_assets import make_optimizer

    expected = hashlib.sha256(SITE.read_bytes()).hexdigest()[:8]
    optimizer = make_optimizer(ROOT / "site")
    for page_name in ("macro.html", "us_stocks.html"):
        page = optimizer((ROOT / "site" / page_name).read_text(), ROOT / "site")
        match = re.search(r"release_publications_live\.js\?v=([0-9a-f]{8})", page)
        assert match, f"{page_name} does not version the live event client"
        assert match.group(1) == expected, (
            f"{page_name} points at a stale immutable client hash"
        )

    caddy = (ROOT / "app" / "deploy" / "Caddyfile").read_text()
    versioned = caddy[caddy.index("@public_versioned {") :]
    versioned = versioned[: versioned.index("}")]
    assert "/release_publications_live.js" in versioned


import pytest


@pytest.mark.parametrize(
    "recovery_kind",
    ["group", "single", "cold_start", "cleared_override"],
)
def test_where_next_freshness_survives_hidden_poll_failure(recovery_kind):
    marker = 'vm.runInThisContext(fs.readFileSync(__TEMPLATE_PATH__, "utf8"));'
    assert ACTION_PLAN_DRIVER.count(marker) == 1

    # Reuse only the existing DOM shim and its window/document construction.
    # Stop BEFORE client evaluation, so start() captures our actual handlers.
    driver = ACTION_PLAN_DRIVER.split(marker, 1)[0]
    driver += r"""
const assert = require("assert");
const recoveryKind = __RECOVERY_KIND__;

// Fake only the browser timer surface and Date. Native Promise/setImmediate
// remain available for draining the client's complete asynchronous chain.
const NativeDate = global.Date;
let clockMs = NativeDate.parse("2026-07-30T12:33:00Z");
class ControlledDate extends NativeDate {
  constructor(...args) {
    super(...(args.length ? args : [clockMs]));
  }
  static now() { return clockMs; }
}
global.Date = ControlledDate;

const timers = new Map();
let nextTimerId = 1;

function registerTimer(callback, delay, every) {
  const id = nextTimerId++;
  timers.set(id, {
    id: id,
    callback: callback,
    due: clockMs + Number(delay),
    every: every
  });
  return id;
}
window.setTimeout = function (callback, delay) {
  return registerTimer(callback, delay, 0);
};
window.setInterval = function (callback, delay) {
  assert(Number(delay) > 0, "interval must advance");
  return registerTimer(callback, delay, Number(delay));
};
window.clearTimeout = window.clearInterval = function (id) {
  timers.delete(id);
};

function advanceClock(milliseconds) {
  assert(milliseconds >= 0);
  const target = clockMs + milliseconds;
  while (true) {
    const next = Array.from(timers.values())
      .filter(function (timer) { return timer.due <= target; })
      .sort(function (left, right) {
        return left.due - right.due || left.id - right.id;
      })[0];
    if (!next) break;

    clockMs = next.due;
    if (next.every) next.due += next.every;
    else timers.delete(next.id);
    next.callback();
  }
  clockMs = target;
}
function timeoutCount() {
  return Array.from(timers.values()).filter(function (timer) {
    return timer.every === 0;
  }).length;
}
function intervals() {
  return Array.from(timers.values()).filter(function (timer) {
    return timer.every > 0;
  });
}
async function drainClient() {
  // Native Node turn: drain response.json(), render(), catch() and finally().
  // Do not replace this with an assumed number of Promise.resolve() calls.
  await new Promise(function (resolve) { setImmediate(resolve); });
}

// Retain actual client event listeners rather than suppressing start().
const documentListeners = new Map();
const windowListeners = new Map();

function listen(registry, type, callback) {
  const callbacks = registry.get(type) || [];
  callbacks.push(callback);
  registry.set(type, callbacks);
}
function emit(registry, target, type) {
  (registry.get(type) || []).slice().forEach(function (callback) {
    callback.call(target, {type: type, target: target});
  });
}
document.addEventListener = function (type, callback) {
  listen(documentListeners, type, callback);
};
window.addEventListener = function (type, callback) {
  listen(windowListeners, type, callback);
};
document.readyState = "loading";
document.visibilityState = "visible";

El.prototype.removeAttribute = function (name) {
  if (name === "class") this.className = "";
  else delete this.attributes[name];
};

// Mount only the two consumers involved in this finding. Missing calendar,
// report-panel, Fed, Alerts and radar islands intentionally remain absent.
function bilingual(className, english, chinese) {
  const container = new El("div");
  container.className = className;
  const en = new El("span");
  en.className = "l-en";
  en.textContent = english;
  const zh = new El("span");
  zh.className = "l-zh";
  zh.textContent = chinese;
  container.appendChild(en);
  container.appendChild(zh);
  return container;
}
function pair(container) {
  assert(container, "missing bilingual container");
  const en = container.querySelector(".l-en");
  const zh = container.querySelector(".l-zh");
  assert(en && en.textContent.trim(), "missing English label");
  assert(zh && zh.textContent.trim(), "missing Chinese label");
  return {en: en.textContent, zh: zh.textContent};
}

document.head = new El("head");
document.documentElement = new El("html");
document.documentElement.appendChild(document.head);
document.documentElement.appendChild(root);

const island = new El("div");
island.id = "sx-events-v2";
const face = new El("div");
face.className = "sxg-face mx5-card-face";
face.appendChild(bilingual(
  "mx5-card-title", "Upcoming Events", "近期事件"
));
face.appendChild(bilingual(
  "mx5-card-badge", "This week", "本周"
));
face.appendChild(bilingual(
  "mx5-events-sub", "Current event schedule", "当前事件日历"
));
island.appendChild(face);
root.appendChild(island);

const whereNext = new El("a");
whereNext.className = "wnx-card";
whereNext.setAttribute("href", "#dlg-events");
whereNext.appendChild(bilingual("wnx-kicker", "Events", "事件"));
whereNext.appendChild(bilingual(
  "wnx-state", "Current event schedule", "当前事件日历"
));
whereNext.appendChild(bilingual(
  "wnx-line", "Open the event calendar", "打开事件日历"
));
whereNext.appendChild(bilingual("wnx-go", "Open events", "查看事件"));
root.appendChild(whereNext);

document.getElementById = function (id) {
  return document.documentElement._descendants().find(function (node) {
    return node.id === id || node.getAttribute("id") === id;
  }) || null;
};
function queryAll(selector) {
  if (selector === "#sx-events-v2 .mx5-card-face") return [face];
  if (selector === "#sx-events-v2 .mx5-card-face.mx-live-event-face") {
    return face.classList.contains("mx-live-event-face") ? [face] : [];
  }
  if (selector === '.wnx-card[href="#dlg-events"]') {
    return whereNext.getAttribute("href") === "#dlg-events" ?
      [whereNext] : [];
  }
  return root.querySelectorAll(selector);
}
document.querySelectorAll = queryAll;
document.querySelector = function (selector) {
  return queryAll(selector)[0] || null;
};

// Keep native AbortController semantics, including its synchronous abort event.
// This harness therefore needs Node with built-in AbortController.
assert.strictEqual(typeof AbortController, "function");

const requests = [];
global.fetch = function (url, options) {
  assert.strictEqual(url, "live/release_publications.json");
  assert(options && options.signal, "poll must supply its abort signal");

  let resolveFetch;
  let rejectFetch;
  const promise = new Promise(function (resolve, reject) {
    resolveFetch = resolve;
    rejectFetch = reject;
  });

  const request = {
    signal: options.signal,
    settled: false,
    succeed: function (payload) {
      finish(function () {
        resolveFetch({
          ok: true,
          json: function () { return Promise.resolve(payload); }
        });
      });
    },
    fail: function (error) {
      finish(function () { rejectFetch(error); });
    }
  };
  function finish(settle) {
    assert.strictEqual(request.settled, false, "fetch settled twice");
    request.settled = true;
    options.signal.removeEventListener("abort", onAbort);
    settle();
  }
  function onAbort() {
    if (request.settled) return;
    const error = new Error("synthetic request aborted");
    error.name = "AbortError";
    request.fail(error);
  }

  requests.push(request);
  options.signal.addEventListener("abort", onAbort);
  if (options.signal.aborted) onAbort();
  return promise;
};

// Synthetic display facts, not claimed historical release measurements.
const rows = ["GDP", "PCE"].map(function (type) {
  return {
    event_id: type.toLowerCase() + ":2026-07-30",
    type: type,
    date: "2026-07-30",
    time_et: "08:30",
    label: type + " release",
    label_zh: type + " 发布",
    status: "published",
    data_ready: true,
    source_released_at: "2026-07-30T12:30:00Z",
    detected_at: "2026-07-30T12:31:00Z",
    actual: {
      headline_en: type + " verified result",
      headline_zh: type + " 已核验结果",
      summary_en: type + " official facts retained.",
      summary_zh: type + " 官方事实已保留。"
    }
  };
});
function envelope(publications) {
  // Explicit transport-envelope control. This does not simulate a new
  // producer extraction or advance detected_at / extraction clocks.
  return {
    built: new Date().toISOString(),
    publications: JSON.parse(JSON.stringify(publications)),
    events: []
  };
}

vm.runInThisContext(fs.readFileSync(__TEMPLATE_PATH__, "utf8"));
const api = window.__mmReleasePublicationTest;
assert(api, "test API missing");

function assertMountedOnce() {
  assert.strictEqual(root.querySelectorAll(".wnx-card").length, 1);
  assert.strictEqual(root.querySelectorAll(".mx5-card-face").length, 1);
  assert.strictEqual(
    document.querySelector('.wnx-card[href="#dlg-events"]'), whereNext
  );
  assert.strictEqual(whereNext.getAttribute("href"), "#dlg-events");
}
function assertLive(kind) {
  const grouped = kind === "group";
  assert.strictEqual(api.freshness(), "fresh");
  assert.strictEqual(
    document.documentElement.getAttribute("data-release-live-freshness"),
    "fresh"
  );
  assert.strictEqual(face.getAttribute("data-live-state"), "verified");
  assert.deepStrictEqual(pair(face.querySelector(".mx5-card-badge")), {
    en: grouped ? "2 live" : "Live",
    zh: grouped ? "2 个实时" : "实时"
  });
  assert.deepStrictEqual(pair(whereNext.querySelector(".wnx-state")), {
    en: grouped ? "2 official results · live" : rows[0].actual.headline_en,
    zh: grouped ? "2 个官方结果 · 实时" : rows[0].actual.headline_zh
  });
  assert.deepStrictEqual(pair(whereNext.querySelector(".wnx-go")), {
    en: grouped ? "Open all live details" : "Open live details",
    zh: grouped ? "查看全部实时详情" : "查看实时详情"
  });
  assertMountedOnce();
}

let originalFacts;
function assertStale(label) {
  assert.strictEqual(api.freshness(), "stale", label);
  assert.strictEqual(
    document.documentElement.getAttribute("data-release-live-freshness"),
    "stale",
    label
  );
  assert.strictEqual(face.getAttribute("data-live-state"), "verified");
  assert.deepStrictEqual(pair(face.querySelector(".mx5-card-badge")), {
    en: "Update delayed", zh: "更新延迟"
  });
  assert.deepStrictEqual(
    pair(face.querySelector(".mx5-events-sub")), originalFacts.face
  );
  assert.deepStrictEqual(
    pair(whereNext.querySelector(".wnx-line")), originalFacts.whereNext
  );
  assertMountedOnce();

  const state = pair(whereNext.querySelector(".wnx-state"));
  const action = pair(whereNext.querySelector(".wnx-go"));
  const problems = [];

  // Report state AND CTA failures together; do not hide the second behind
  // the first assertion. Neutral CTA wording is allowed.
  [["state", state], ["action", action]].forEach(function (entry) {
    if (/\blive\b/i.test(entry[1].en) || /实时/.test(entry[1].zh)) {
      problems.push(entry[0] + " still claims live: " +
        JSON.stringify(entry[1]));
    }
  });
  // State must positively disclose last-known/delayed/unavailable status.
  // Exact copy remains the repair owner's choice within this contract.
  if (!/(last[- ](?:known|verified)|delayed|unavailable)/i.test(state.en) ||
      !/(上次|延迟|不可用)/.test(state.zh)) {
    problems.push("state lacks bilingual last-known/delayed qualification");
  }
  assert.strictEqual(problems.length, 0, label + ": " + problems.join("; "));
}

function whereNextCopy() {
  return {
    kicker: pair(whereNext.querySelector(".wnx-kicker")),
    state: pair(whereNext.querySelector(".wnx-state")),
    line: pair(whereNext.querySelector(".wnx-line")),
    action: pair(whereNext.querySelector(".wnx-go")),
    href: whereNext.getAttribute("href")
  };
}

function assertUnownedWhereNext(expected, label) {
  assert.strictEqual(
    whereNext.__mmLiveWhereNextText, undefined, label
  );
  assert.deepStrictEqual(whereNextCopy(), expected, label);
  assertMountedOnce();
}

async function failAfterHiddenTTL(label) {
  const before = requests.length;
  assert.strictEqual(timeoutCount(), 0);

  document.visibilityState = "hidden";
  emit(documentListeners, document, "visibilitychange");
  advanceClock(4 * 60 * 1000);
  await drainClient();
  assert.strictEqual(requests.length, before, label + ": hidden fetch");

  document.visibilityState = "visible";
  emit(documentListeners, document, "visibilitychange");
  assert.strictEqual(requests.length, before + 1, label + ": missing fetch");
  requests[before].fail(new Error(label));
  await drainClient();

  assert.strictEqual(api.freshness(), "stale", label);
  assert.strictEqual(timeoutCount(), 0, label);
}

async function main() {
  assert.strictEqual(requests.length, 0, "client started before DOM ready");
  assert.strictEqual(
    (documentListeners.get("DOMContentLoaded") || []).length, 1
  );

  document.readyState = "interactive";
  emit(documentListeners, document, "DOMContentLoaded");
  assert.strictEqual(requests.length, 1, "start() must initiate one fetch");
  assert.strictEqual(intervals().length, 1);
  assert.strictEqual(intervals()[0].every, 15000);
  assert.strictEqual(
    (documentListeners.get("visibilitychange") || []).length, 1
  );
  assert.strictEqual((windowListeners.get("focus") || []).length, 1);

  if (recoveryKind === "cold_start") {
    const shell = whereNextCopy();
    requests[0].fail(new Error("synthetic initial network failure"));
    await drainClient();

    assert.strictEqual(api.freshness(), "stale");
    assert.strictEqual(timeoutCount(), 0);
    assertUnownedWhereNext(shell, "initial failure must preserve SSR");

    // Prove the single painter establishes its own marker without any
    // earlier group hydration having supplied one.
    emit(windowListeners, window, "focus");
    assert.strictEqual(requests.length, 2);
    requests[1].succeed(envelope([rows[0]]));
    await drainClient();
    assertLive("single");
    originalFacts = {
      face: pair(face.querySelector(".mx5-events-sub")),
      whereNext: pair(whereNext.querySelector(".wnx-line"))
    };

    await failAfterHiddenTTL("single result after cold-start recovery");
    assertStale("single result after cold-start recovery");
    assert.deepStrictEqual(pair(whereNext.querySelector(".wnx-state")), {
      en: rows[0].actual.headline_en + " · update delayed",
      zh: rows[0].actual.headline_zh + " · 更新延迟"
    });
    return;
  }

  requests[0].succeed(envelope(rows));
  await drainClient();
  assertLive("group");
  assert.strictEqual(timeoutCount(), 0);
  originalFacts = {
    face: pair(face.querySelector(".mx5-events-sub")),
    whereNext: pair(whereNext.querySelector(".wnx-line"))
  };
  if (recoveryKind === "cleared_override") {
    emit(windowListeners, window, "focus");
    assert.strictEqual(requests.length, 2);
    requests[1].succeed(envelope([]));
    await drainClient();

    // A fresh payload with no active publications invokes the existing
    // expiry/handoff path. This is not a separate 24-hour boundary test.
    assert.strictEqual(api.freshness(), "fresh");
    assert.deepStrictEqual(pair(whereNext.querySelector(".wnx-state")), {
      en: "No active live result", zh: "当前无实时结果"
    });
    assert.deepStrictEqual(pair(whereNext.querySelector(".wnx-go")), {
      en: "Open events", zh: "查看事件"
    });
    const schedule = whereNextCopy();
    assertUnownedWhereNext(schedule, "fresh handoff clears ownership");

    await failAfterHiddenTTL("failure after fresh schedule handoff");
    assertUnownedWhereNext(
      schedule, "failed transport must not revive the old live override"
    );
    return;
  }


  document.visibilityState = "hidden";
  emit(documentListeners, document, "visibilitychange");

  // Four minutes crosses the freshness TTL. Ten extra seconds aligns the
  // next 15-second interval inside the return request's 10-second timeout.
  advanceClock(4 * 60 * 1000 + 10 * 1000);
  await drainClient();
  assert.strictEqual(requests.length, 1, "hidden ticks started a fetch");
  assert.strictEqual(timeoutCount(), 0);

  document.visibilityState = "visible";
  emit(documentListeners, document, "visibilitychange");
  assert.strictEqual(requests.length, 2, "visibility return did not fetch");
  assert.strictEqual(timeoutCount(), 1);

  emit(windowListeners, window, "focus");
  emit(windowListeners, window, "focus");
  assert.strictEqual(requests.length, 2, "focus did not coalesce");

  advanceClock(5000);  // Actual registered interval fires while pending.
  assert.strictEqual(requests.length, 2, "interval did not coalesce");
  assert.strictEqual(requests[1].settled, false);
  assert.strictEqual(requests[1].signal.aborted, false);

  // Do not assert fresh/stale labels while this request is pending.
  requests[1].fail(new Error("synthetic network failure"));
  await drainClient();
  assert.strictEqual(timeoutCount(), 0, "failure timer was not cleared");
  assertStale("first failed return poll");

  // A second failure must retain qualification. Exercise the real abort
  // callback rather than calling notePollFailure() or render() directly.
  emit(windowListeners, window, "focus");
  assert.strictEqual(requests.length, 3, "failed request remained latched");
  advanceClock(9999);
  assert.strictEqual(requests[2].signal.aborted, false);
  advanceClock(1);
  assert.strictEqual(requests[2].signal.aborted, true);
  await drainClient();
  assert.strictEqual(requests[2].settled, true);
  assert.strictEqual(timeoutCount(), 0);
  assertStale("second, timeout-driven failure");

  const recoveryRows = recoveryKind === "group" ? rows : [rows[0]];
  emit(windowListeners, window, "focus");
  assert.strictEqual(requests.length, 4, "aborted request remained latched");
  requests[3].succeed(envelope(recoveryRows));
  await drainClient();
  assertLive(recoveryKind);
  assert.strictEqual(timeoutCount(), 0);

  const recoveredFacts = recoveryKind === "group" ? originalFacts : {
    face: {
      en: rows[0].actual.headline_en,
      zh: rows[0].actual.headline_zh
    },
    whereNext: {
      en: rows[0].actual.summary_en,
      zh: rows[0].actual.summary_zh
    }
  };
  assert.deepStrictEqual(
    pair(face.querySelector(".mx5-events-sub")), recoveredFacts.face
  );
  assert.deepStrictEqual(
    pair(whereNext.querySelector(".wnx-line")), recoveredFacts.whereNext
  );

  // The existing periodic poll continues after recovery. A second successful
  // transport envelope must preserve current labels and mounted identities.
  advanceClock(5000);
  assert.strictEqual(requests.length, 5, "periodic polling did not resume");
  requests[4].succeed(envelope(recoveryRows));
  await drainClient();
  assertLive(recoveryKind);
  assert.deepStrictEqual(
    pair(whereNext.querySelector(".wnx-line")), recoveredFacts.whereNext
  );
  assert.strictEqual(timeoutCount(), 0);
  assert.strictEqual(intervals().length, 1);
}

main().catch(function (error) {
  console.error(error.stack || error);
  process.exitCode = 1;
}).finally(function () {
  global.Date = NativeDate;
});
"""
    driver = driver.replace("__TEMPLATE_PATH__", json.dumps(str(TEMPLATE)))
    driver = driver.replace("__RECOVERY_KIND__", json.dumps(recovery_kind))
    result = subprocess.run(
        ["node", "-e", driver],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_events_face_stance_follows_live_release_state():
    driver = ACTION_PLAN_DRIVER.split("function freshActionRow()", 1)[0]
    driver += r"""
document.head = new El("head");
document.documentElement = new El("html");
let face = null;
document.querySelector = function (selector) {
  if (selector === "#sx-events-v2 .mx5-card-face") return face;
  if (selector === "#sx-events-v2 .mx5-card-face.mx-live-event-face") {
    return face && face.classList.contains("mx-live-event-face") ? face : null;
  }
  return root.querySelector(selector);
};

if (!El.prototype.removeAttribute) {
  El.prototype.removeAttribute = function (name) {
    if (name === "class") this.className = "";
    else delete this.attributes[name];
  };
}
function pairNode(className, en, zh) {
  const node = new El("div");
  node.className = className;
  const english = new El("span");
  english.className = "l-en";
  english.textContent = en;
  const chinese = new El("span");
  chinese.className = "l-zh";
  chinese.textContent = zh;
  node.appendChild(english);
  node.appendChild(chinese);
  return node;
}
function fixture(count) {
  root.childNodes = [];
  face = new El("div");
  face.className = "sxg-face mx5-card-face";
  face.appendChild(pairNode("mx5-card-title", "Upcoming Events", "近期事件"));
  face.appendChild(pairNode("mx5-card-badge", "This week", "本周"));
  face.appendChild(pairNode("mx5-card-stance",
    "Get ready — " + count + " big prints ahead; avoid adding risk right before them.",
    "做好准备——前方有 " + count + " 项重磅数据，公布前不宜加仓。"));
  face.appendChild(pairNode("mx5-events-sub",
    count + " high-impact prints ahead", count + " 项高影响数据待发"));
  root.appendChild(face);
}
const now = new Date("2026-07-30T12:33:00Z");
function publication(type) {
  return {
    event_id: type.toLowerCase() + ":2026-07-30",
    type: type, date: "2026-07-30", time_et: "08:30",
    label: type + " release", label_zh: type + " 发布",
    status: "published", data_ready: true,
    source_released_at: "2026-07-30T12:30:00Z",
    detected_at: "2026-07-30T12:31:00Z",
    actual: {
      headline_en: type + " official result",
      headline_zh: type + " 官方结果",
      summary_en: type + " official values are verified.",
      summary_zh: type + " 官方数据已核验。"
    }
  };
}
function assertLiveStance(caseName, payload, expectedState, expectedStance) {
  for (let poll = 0; poll < 2; poll += 1) {
    if (api.render(payload, now) !== true)
      throw new Error(caseName + ": fresh payload was rejected");
    if (face.getAttribute("data-live-state") !== expectedState)
      throw new Error(caseName + ": expected live face was not reached");
    const stance = face.querySelector(".mx5-card-stance");
    const en = stance.querySelector(".l-en").textContent;
    const zh = stance.querySelector(".l-zh").textContent;
    if (expectedStance &&
        (en !== expectedStance[0] || zh !== expectedStance[1])) {
      throw new Error(caseName + ": unexpected stance: " +
        JSON.stringify([en, zh]));
    }
    if (!en.trim() || !zh.trim())
      throw new Error(caseName + ": lifecycle stance must remain bilingual");
    if (/big prints ahead|avoid adding risk right before them/.test(en))
      throw new Error(caseName + ": stale English pre-release stance: " + en);
    if (/项重磅数据|公布前不宜加仓/.test(zh))
      throw new Error(caseName + ": stale Chinese pre-release stance: " + zh);
  }
}
const verifiedStance = [
  "Verified official values are available.",
  "官方数据已核验。"
];
const awaitingStance = [
  "Awaiting official-source verification.",
  "等待官方来源核验。"
];
const incompleteStance = [
  "Verification is incomplete — check each release's status.",
  "核验尚未完成——请逐项查看发布状态。"
];

function facePair(selector) {
  const node = face.querySelector(selector);
  return [
    node.querySelector(".l-en").textContent,
    node.querySelector(".l-zh").textContent
  ];
}

fixture(1);
assertLiveStance("single verified publication", {
  built: now.toISOString(), publications: [publication("GDP")], events: []
}, "verified", verifiedStance);
fixture(2);
assertLiveStance("same-day verified publication group", {
  built: now.toISOString(),
  publications: [publication("GDP"), publication("PCE")], events: []
}, "verified", verifiedStance);
fixture(1);
assertLiveStance("scheduled time passed, source still awaited", {
  built: now.toISOString(), publications: [],
  events: [{
    event_id: "gdp:2026-07-30", type: "GDP",
    date: "2026-07-30", time_et: "08:30",
    label: "GDP release", label_zh: "GDP 发布",
    status: "awaiting_publication", data_ready: false
  }]
}, "awaiting", awaitingStance);
function awaitingRow(type) {
  return {
    event_id: type.toLowerCase() + ":2026-07-30",
    type: type,
    date: "2026-07-30",
    time_et: "08:30",
    label: type + " release",
    label_zh: type + " 发布",
    status: "awaiting_publication",
    data_ready: false
  };
}

const unparsed = publication("PCE");
unparsed.status = "published_unparsed";
unparsed.data_ready = false;
unparsed.actual = {};
unparsed.extraction = { status: "source_unavailable" };

// The existing progress helper uses the same detail pair for unavailable
// and delayed extraction. This fixture does not depend on wall-clock age.
fixture(1);
assertLiveStance("detected publication without verified values", {
  built: now.toISOString(),
  publications: [unparsed],
  events: []
}, "detected", [
  "The report is published, but verified values have not reached this dashboard. " +
    "This is a data-delivery issue, not a release still in progress.",
  "报告已经发布，但核验数据尚未送达本看板。这是数据更新问题，并非报告仍在发布中。"
]);

fixture(3);
assertLiveStance("verified, detected and awaiting release group", {
  built: now.toISOString(),
  publications: [publication("GDP"), unparsed],
  events: [awaitingRow("CLAIMS")]
}, "detected", incompleteStance);

fixture(2);
assertLiveStance("all-awaiting release group", {
  built: now.toISOString(),
  publications: [],
  events: [awaitingRow("GDP"), awaitingRow("PCE")]
}, "detected", incompleteStance);

fixture(1);
assertLiveStance("prior mounted live face", {
  built: now.toISOString(),
  publications: [publication("GDP")],
  events: []
}, "verified", verifiedStance);

// A replacement SSR face has never received the live override.
fixture(3);
const faceSelectors = [
  ".mx5-card-title", ".mx5-card-badge",
  ".mx5-card-stance", ".mx5-events-sub"
];
const untouchedShell = faceSelectors.map(facePair);

if (api.render({
  built: now.toISOString(),
  publications: [],
  events: []
}, now) !== true) {
  throw new Error("fresh no-active payload was rejected");
}
if (JSON.stringify(faceSelectors.map(facePair)) !==
    JSON.stringify(untouchedShell)) {
  throw new Error("expiry modified a face with no live override");
}

// Complete the four lifecycle cases after the replacement-SSR guard.
(function proveEventsStanceLifecycle() {
  const assert = require("assert");
  const NativeDate = global.Date;
  let clockMs = NativeDate.parse("2026-07-30T12:33:00Z");

  class LifecycleDate extends NativeDate {
    constructor(...args) {
      super(...(args.length ? args : [clockMs]));
    }
    static now() { return clockMs; }
  }
  global.Date = LifecycleDate;

  try {
    const currentTime = function () { return new Date(clockMs); };
    const unknownStance = [
      "Watch — this read is being updated.",
      "观望——该读数更新中。"
    ];
    const fields = [
      ".mx5-card-title", ".mx5-card-badge",
      ".mx5-card-stance", ".mx5-events-sub"
    ];
    function copy() { return fields.map(facePair); }
    function putPair(selector, pair) {
      const node = face.querySelector(selector);
      node.querySelector(".l-en").textContent = pair[0];
      node.querySelector(".l-zh").textContent = pair[1];
    }
    function expectPair(selector, pair) {
      assert.deepStrictEqual(facePair(selector), pair, selector);
    }
    function expectFreshness(expected) {
      assert.strictEqual(api.freshness(), expected);
      assert.strictEqual(document.documentElement.getAttribute(
        "data-release-live-freshness"), expected);
    }
    function expectLive(expected) {
      assert.strictEqual(face.classList.contains("mx-live-event-face"), expected);
      assert.strictEqual(face.getAttribute("data-live-state"),
        expected ? "verified" : null);
    }
    function render(payload, expected) {
      assert.strictEqual(api.render(payload, currentTime()), expected);
    }
    function rebuilt(payload) {
      return Object.assign({}, payload, {
        built: currentTime().toISOString()
      });
    }

    // Seed this journey with an unknown full calendar, not an empty one.
    // Discard both count-bearing nodes supplied by the fixture factory.
    fixture(1);
    putPair(".mx5-card-stance", unknownStance);
    putPair(".mx5-events-sub", [
      "Events feed is reconnecting — re-checked nightly. " +
        "The rest of this page is unaffected.",
      "事件数据源重连中——每晚重新检查。本页其余内容不受影响。"
    ]);
    const row = publication("GDP");
    assert.strictEqual(row.detected_at, "2026-07-30T12:31:00Z");
    const originalEnvelope = {
      built: currentTime().toISOString(),
      publications: [row],
      events: []
    };
    render(originalEnvelope, true);
    expectFreshness("fresh");
    expectLive(true);
    expectPair(".mx5-card-stance", verifiedStance);

    // 1. Exactly 24h from detection remains active with a fresh envelope.
    clockMs = NativeDate.parse("2026-07-31T12:31:00Z");
    assert.strictEqual(clockMs - NativeDate.parse(row.detected_at),
      24 * 60 * 60 * 1000);
    const boundaryEnvelope = rebuilt(originalEnvelope);
    assert.strictEqual(api.payloadIsFresh(boundaryEnvelope, currentTime()), true);
    assert.deepStrictEqual(api.recentPublications(
      boundaryEnvelope, currentTime()), [row]);
    render(boundaryEnvelope, true);
    expectFreshness("fresh");
    expectLive(true);
    expectPair(".mx5-card-stance", verifiedStance);
    const lastKnownStance = facePair(".mx5-card-stance");
    const lastKnownSubline = facePair(".mx5-events-sub");

    // 2. Just past the boundary, reject the ORIGINAL previous-day envelope.
    // Only 1ms has elapsed since successful revalidation: the first two
    // failures retain freshness; the third reaches the missed-poll limit.
    clockMs += 1;
    assert.strictEqual(api.payloadIsFresh(originalEnvelope, currentTime()), false);
    for (let failure = 1; failure <= 3; failure += 1) {
      render(originalEnvelope, false);
      expectLive(true);
      expectPair(".mx5-card-stance", lastKnownStance);
      expectPair(".mx5-events-sub", lastKnownSubline);
      expectFreshness(failure < 3 ? "fresh" : "stale");
      expectPair(".mx5-card-title", failure < 3 ?
        ["Latest official result", "最新官方结果"] :
        ["Last verified result", "上次核验结果"]);
      expectPair(".mx5-card-badge", failure < 3 ?
        ["Live", "实时"] : ["Update delayed", "更新延迟"]);
    }

    // 3. Identical publication/event data; only built is refreshed.
    // That accepted envelope can now establish expiry. events: [] does not
    // establish that the separate full future calendar is empty.
    const expiredEnvelope = rebuilt(originalEnvelope);
    assert.strictEqual(api.payloadIsFresh(expiredEnvelope, currentTime()), true);
    assert.deepStrictEqual(api.recentPublications(
      expiredEnvelope, currentTime()), []);
    for (let poll = 0; poll < 2; poll += 1) {
      render(expiredEnvelope, true);
      expectFreshness("fresh");
      expectLive(false);
      expectPair(".mx5-card-title", ["Upcoming events", "近期事件"]);
      expectPair(".mx5-card-badge", ["Schedule", "日历"]);
      expectPair(".mx5-events-sub", [
        "No active live result · open the current schedule",
        "当前无实时结果 · 打开最新日历"
      ]);
      expectPair(".mx5-card-stance", unknownStance);
    }

    // 4. Separate synthetic full-calendar input supplies three future rows.
    // Only the first row is exposed to this client in the shorter sidecar.
    const fullCalendar = [
      { event_id: "synthetic:2026-08-03", type: "FUTURE_A",
        date: "2026-08-03", time_et: "08:30",
        impact: "high", status: "scheduled" },
      { event_id: "synthetic:2026-08-04", type: "FUTURE_B",
        date: "2026-08-04", time_et: "08:30",
        impact: "high", status: "scheduled" },
      { event_id: "synthetic:2026-08-05", type: "FUTURE_C",
        date: "2026-08-05", time_et: "08:30",
        impact: "high", status: "scheduled" }
    ];
    const fullCount = fullCalendar.filter(function (event) {
      return event.impact === "high";
    }).length;
    assert.strictEqual(fullCount, 3);
    fullCalendar.forEach(function (event) {
      assert.strictEqual(api.eventHasPassed(event, currentTime()), false);
    });
    fixture(fullCount);
    expectLive(false);
    const fullCalendarShell = copy();
    const futureEnvelope = {
      built: currentTime().toISOString(),
      publications: [],
      events: [Object.assign({}, fullCalendar[0])]
    };
    assert.strictEqual(futureEnvelope.events.length, 1);
    render(futureEnvelope, true);
    expectFreshness("fresh");
    expectLive(false);
    assert.deepStrictEqual(copy(), fullCalendarShell,
      "future-only sidecar replaced the full-calendar SSR count");

    // Age the envelope, not the canonical future dates.
    clockMs += 4 * 60 * 1000;
    fullCalendar.forEach(function (event) {
      assert.strictEqual(api.eventHasPassed(event, currentTime()), false);
    });
    assert.strictEqual(api.payloadIsFresh(futureEnvelope, currentTime()), false);
    render(futureEnvelope, false);
    expectFreshness("stale");
    expectLive(false);
    assert.deepStrictEqual(copy(), fullCalendarShell,
      "stale transport erased the still-future full-calendar SSR count");
  } finally {
    global.Date = NativeDate;
  }
})();

"""
    driver = driver.replace("__TEMPLATE_PATH__", json.dumps(str(TEMPLATE)))
    result = subprocess.run(
        ["node", "-e", driver], cwd=ROOT,
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
