"""Browser-client contract for refreshing server-rendered AI briefs in place."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSET = ROOT / "site" / "assets" / "js" / "aibrief-freshness.js"


def _node(body: str) -> dict:
    script = f"const api = require({json.dumps(str(ASSET))});\n{body}"
    result = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, (
        f"node failed ({result.returncode})\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    return json.loads(result.stdout)


_FAKE_DOM = r"""
class BriefNode {
  constructor(lens, date) {
    this.dataset = { lens };
    this.date = date;
    this.replacedWith = null;
  }
  querySelector(selector) {
    return selector === '.aib2-hdr-date' ? { textContent: this.date } : null;
  }
  cloneNode() { return new BriefNode(this.dataset.lens, this.date); }
  replaceWith(node) { this.replacedWith = node; }
}
function makeDocument(nodes) {
  return {
    nodes,
    baseURI: 'https://www.mastermind-x.com/macro.html',
    hidden: false,
    listeners: {},
    querySelector(selector) {
      return selector === '.aib2[data-lens]' ? (this.nodes[0] || null) : null;
    },
    querySelectorAll(selector) {
      return selector === '.aib2[data-lens]' ? this.nodes : [];
    },
    importNode(node) { return node.cloneNode(true); },
    addEventListener(name, fn) { this.listeners[name] = fn; }
  };
}
"""


def test_client_replaces_only_strictly_newer_matching_lenses() -> None:
    out = _node(
        _FAKE_DOM
        + r"""
const local = [
  new BriefNode('macro', '2026-09-09'),
  new BriefNode('china', '2026-09-10'),
  new BriefNode('btc', '2026-09-11')
];
const remote = [
  new BriefNode('macro', '2026-09-10'),
  new BriefNode('china', '2026-09-10'),
  new BriefNode('btc', '2026-09-09')
];
const changed = api.applyNewerBriefs(makeDocument(local), makeDocument(remote));
process.stdout.write(JSON.stringify({
  changed,
  macro: local[0].replacedWith && local[0].replacedWith.date,
  china: local[1].replacedWith,
  btc: local[2].replacedWith
}));
"""
    )
    assert out == {
        "changed": 1,
        "macro": "2026-09-10",
        "china": None,
        "btc": None,
    }


def test_equal_date_never_replaces_surface_specific_markup() -> None:
    out = _node(
        _FAKE_DOM
        + r"""
const localNode = new BriefNode('macro', '2026-09-10');
const remoteNode = new BriefNode('macro', '2026-09-10');
remoteNode.footer = 'different canonical-page footer';
const changed = api.applyNewerBriefs(makeDocument([localNode]), makeDocument([remoteNode]));
process.stdout.write(JSON.stringify({ changed, replaced: localNode.replacedWith }));
"""
    )
    assert out == {"changed": 0, "replaced": None}


def test_controller_fetches_current_surface_without_cache_and_coalesces_inflight() -> None:
    out = _node(
        _FAKE_DOM
        + r"""
const localNode = new BriefNode('macro', '2026-09-09');
const remoteNode = new BriefNode('macro', '2026-09-10');
const localDoc = makeDocument([localNode]);
const remoteDoc = makeDocument([remoteNode]);
const calls = [];
let release;
const bodyReady = new Promise(resolve => { release = resolve; });
const fakeFetch = (url, options) => {
  calls.push({ url, options });
  return bodyReady.then(() => ({ ok: true, text: () => Promise.resolve('<html></html>') }));
};
class Parser { parseFromString() { return remoteDoc; } }
const win = {
  location: { href: 'https://www.mastermind-x.com/macro.html?theme=dark#dlg-aibrief' },
  listeners: {},
  addEventListener(name, fn) { this.listeners[name] = fn; },
  CustomEvent: class { constructor(name, init) { this.type = name; this.detail = init.detail; } },
  dispatchEvent() {}
};
const controller = api.createController({
  document: localDoc,
  window: win,
  fetch: fakeFetch,
  DOMParser: Parser,
  now: () => 1789156800000
});
const first = controller.checkNow(true);
const second = controller.checkNow(true);
release();
Promise.all([first, second]).then(values => {
  process.stdout.write(JSON.stringify({
    samePromise: first === second,
    values,
    calls: calls.length,
    url: calls[0].url,
    cache: calls[0].options.cache,
    credentials: calls[0].options.credentials,
    replaced: localNode.replacedWith && localNode.replacedWith.date
  }));
});
"""
    )
    assert out["samePromise"] is True
    assert out["values"] == [1, 1]
    assert out["calls"] == 1
    assert out["url"].startswith("https://www.mastermind-x.com/macro.html?")
    assert "brief_refresh=1789156800000" in out["url"]
    assert "theme=dark" not in out["url"]
    assert "#" not in out["url"]
    assert out["cache"] == "no-store"
    assert out["credentials"] == "same-origin"
    assert out["replaced"] == "2026-09-10"


def test_binding_checks_on_return_and_on_ai_brief_intent() -> None:
    out = _node(
        _FAKE_DOM
        + r"""
const doc = makeDocument([new BriefNode('macro', '2026-09-09')]);
const win = {
  location: { href: 'https://www.mastermind-x.com/macro.html' },
  listeners: {},
  addEventListener(name, fn) { this.listeners[name] = fn; },
  dispatchEvent() {}
};
const controller = api.createController({
  document: doc,
  window: win,
  fetch: () => Promise.resolve({ ok: false, text: () => Promise.resolve('') }),
  DOMParser: class {},
  now: () => 1
});
controller.bind();
process.stdout.write(JSON.stringify({
  documentEvents: Object.keys(doc.listeners).sort(),
  windowEvents: Object.keys(win.listeners).sort()
}));
"""
    )
    assert out["documentEvents"] == ["click", "focusin", "visibilitychange"]
    assert out["windowEvents"] == ["pageshow"]


def test_failed_refresh_keeps_last_valid_brief() -> None:
    out = _node(
        _FAKE_DOM
        + r"""
const localNode = new BriefNode('macro', '2026-09-09');
const doc = makeDocument([localNode]);
const controller = api.createController({
  document: doc,
  window: { location: { href: 'https://www.mastermind-x.com/macro.html' }, addEventListener() {}, dispatchEvent() {} },
  fetch: () => Promise.reject(new Error('offline')),
  DOMParser: class {},
  now: () => 2
});
controller.checkNow(true).then(changed => {
  process.stdout.write(JSON.stringify({ changed, replaced: localNode.replacedWith }));
});
"""
    )
    assert out == {"changed": 0, "replaced": None}
