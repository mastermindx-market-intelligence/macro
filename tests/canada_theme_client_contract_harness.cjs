"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const sourcePath = process.argv[2];
const scenario = process.argv[3];

if (scenario === "builder-seam") {
  const repoRoot = path.resolve(path.dirname(sourcePath), "..");
  const builder = fs.readFileSync(path.join(repoRoot, "scripts", "build_canada.py"), "utf8");
  process.stdout.write(JSON.stringify({
    scenario,
    builder_safe_import: builder.includes(
      "from scripts.canada_theme_action_map import _safe_canada_theme_action_map"
    ),
    builder_safe_call: builder.includes(
      'vm["theme_actions"] = _safe_canada_theme_action_map(setups, site)'
    ),
    errors: [],
  }) + "\n");
  process.exit(0);
}
const payload = {
  baskets: [{id: "oil", members: [{symbol: "AAA.TO"}]}],
  theme_intel: {
    themes: [{
      id: "oil",
      name: "Oil",
      rank: 1,
      reco: "accumulate",
      leadership: {top: [{ticker: "AAA.TO"}]},
    }],
  },
};

if (scenario === "duplicate-basket") {
  payload.baskets.push({id: "oil", members: [{symbol: "ZZZ.TO"}]});
} else if (scenario === "duplicate-theme") {
  payload.theme_intel.themes.push({
    id: "oil", name: "Oil duplicate", rank: 9, leadership: {top: []},
  });
} else if (scenario === "numeric-symbol") {
  payload.baskets[0].members = [{symbol: 123}];
} else if (scenario === "malformed-members") {
  payload.baskets[0].members = [null, {}, " "];
} else if (scenario === "malformed-leadership") {
  payload.theme_intel.themes[0].leadership = {top: {ticker: "AAA.TO"}};
} else if (scenario === "valid-empty") {
  payload.baskets[0].members = [];
  payload.theme_intel.themes[0].leadership = {top: []};
} else if (scenario === "numeric-id") {
  payload.baskets[0].id = 123;
  payload.theme_intel.themes[0].id = 123;
} else if (scenario === "blank-id") {
  payload.baskets[0].id = " ";
  payload.theme_intel.themes[0].id = " ";
} else if (scenario === "server-wins") {
  payload.baskets[0].members = [{symbol: "ZZZ.TO"}];
  payload.theme_intel.themes[0].leadership = {top: [{ticker: "ZZZ.TO"}]};
}

function classList() {
  return {toggle() {}, add() {}, remove() {}, contains() { return false; }};
}
function card(ticker) {
  const attrs = {"data-ticker": ticker};
  return {
    hidden: false,
    style: {animationDelay: ""},
    classList: classList(),
    getAttribute(key) { return attrs[key] ?? null; },
    setAttribute(key, value) { attrs[key] = String(value); },
    querySelector() { return null; },
    querySelectorAll() { return []; },
  };
}

const cards = [card("AAA.TO"), card("ZZZ.TO")];
const cardsHost = {
  querySelector() { return null; },
  querySelectorAll(selector) { return selector === ".pvcard" ? cards : []; },
};
const host = {
  innerHTML: "",
  setAttribute() {},
  getAttribute() { return null; },
  querySelector() { return null; },
  querySelectorAll() { return []; },
  classList: classList(),
};
const staticName = {textContent: "Server Oil", querySelector() { return null; }};
const staticTheme = {
  classList: classList(),
  getAttribute(key) {
    return {
      "data-ca-lead-kind": "theme",
      "data-ca-lead-id": "oil",
      "data-ca-members": "AAA.TO",
    }[key] ?? null;
  },
  hasAttribute(key) { return key === "data-ca-members"; },
  querySelector(selector) { return selector === ".ca-theme-name b" ? staticName : null; },
  querySelectorAll() { return []; },
  closest(selector) {
    return selector === "[data-ca-lead-kind][data-ca-lead-id]" ? this : null;
  },
};
const handlers = Object.create(null);
const main = {
  attrs: Object.create(null),
  getAttribute(key) { return this.attrs[key] ?? null; },
  setAttribute(key, value) { this.attrs[key] = String(value); },
  addEventListener(type, callback) { handlers[type] = callback; },
  querySelector() { return null; },
  querySelectorAll(selector) {
    if (scenario === "server-wins" && selector === "[data-ca-lead-kind][data-ca-lead-id]") {
      return [staticTheme];
    }
    return [];
  },
  classList: classList(),
};

global.window = global;
global.location = {pathname: "/canada_stocks.html", hash: ""};
global.history = {pushState() {}, replaceState() {}};
global.document = {
  readyState: "complete",
  body: {classList: {contains() { return true; }}},
  documentElement: {style: {}},
  activeElement: null,
  querySelector(selector) {
    if (selector === "#ca-v36") return main;
    if (selector === "#ca-v36-lead-cols") return host;
    if (selector === "#standouts .cards") return cardsHost;
    return null;
  },
  querySelectorAll(selector) {
    if (scenario === "server-wins" && selector === '[data-ca-lead-kind="theme"][data-ca-lead-id]') {
      return [staticTheme];
    }
    return [];
  },
  addEventListener() {},
};
global.MutationObserver = function MutationObserver() {
  this.observe = function observe() {};
};
global.window.MutationObserver = global.MutationObserver;
global.window.addEventListener = function addEventListener() {};
global.window.matchMedia = function matchMedia() {
  return {matches: false, addEventListener() {}, addListener() {}};
};
global.fetch = async function fetchOwner(url) {
  return {
    ok: true,
    json: async () => String(url).includes("baskets.json")
      ? payload
      : {themes: payload.theme_intel.themes},
  };
};
const errors = [];
process.on("unhandledRejection", (error) => {
  errors.push(String(error && (error.stack || error.message) || error));
});

vm.runInThisContext(fs.readFileSync(sourcePath, "utf8"), {filename: sourcePath});

setTimeout(() => {
  if (scenario === "server-wins") {
    handlers.click({target: staticTheme, preventDefault() {}});
  }
  const leader = host.innerHTML.match(/ca-v36-leaders\">([^<]*)</);
  const count = host.innerHTML.match(/ca-v36-count\">([^<]*)</);
  const rows = host.innerHTML.match(/class=\"ca-v36-lead-row\"/g) || [];
  process.stdout.write(JSON.stringify({
    scenario,
    actionable: /data-ca-lead-kind=\"theme\"/.test(host.innerHTML),
    row_count: rows.length,
    leaders: leader ? leader[1] : null,
    count: count ? count[1] : null,
    visible: cards.filter((item) => !item.hidden).map((item) => item.getAttribute("data-ticker")),
    errors,
  }) + "\n");
}, 50);
