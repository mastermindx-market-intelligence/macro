"""`?v=` stamps and route-scoped freshness assets must stay current.

`app/deploy/Caddyfile` serves versioned asset requests `Cache-Control: immutable,
max-age=1y`. That is only safe if the stamp moves when the file does — and it did
not: `optimize_assets_text` skipped any ref that already carried a query, so a
stamp committed into a page froze at whatever the asset contained that day. On
2026-07-26 `theme.js` was stamped stale on 1,509 pages across four generations of
hash, and #3560's onboard.css/js changes landed under frozen stamps on the
landing.

The same owner now attaches the content-hashed AI Brief freshness client to every
rendered page carrying the shared `.aib2` body. These tests pin both contracts:
our own stamps are re-hashed, unrelated author queries are untouched, and a
long-lived server-rendered brief can adopt only a strictly newer body from its
same surface without inventing a second renderer.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.pages import optimize_assets_text  # noqa: E402
from scripts.optimize_assets import _attach_aibrief_freshness, optimize  # noqa: E402

HASHES = {
    "theme.js": "aaaaaaaa",
    "onboard.css": "bbbbbbbb",
    "../theme.js": "aaaaaaaa",
    "assets/css/deadbeef.css": "cccccccc",
}


def _hash_for(url: str):
    return HASHES.get(url)


def _rw(html: str) -> str:
    return optimize_assets_text(html, _hash_for)


def test_stale_stamp_is_refreshed():
    out = _rw('<script src="theme.js?v=015c6c36" defer></script>')
    assert 'src="theme.js?v=aaaaaaaa"' in out
    assert "015c6c36" not in out


def test_stale_stamp_refreshed_at_any_depth():
    out = _rw('<script src="../theme.js?v=16dc65dc" defer></script>')
    assert 'src="../theme.js?v=aaaaaaaa"' in out


def test_stale_css_stamp_is_refreshed():
    out = _rw('<link rel="stylesheet" href="onboard.css?v=233832f9">')
    assert 'href="onboard.css?v=bbbbbbbb"' in out


def test_current_stamp_is_a_no_op():
    src = '<script src="theme.js?v=aaaaaaaa" defer></script>'
    assert _rw(src) == src


def test_rerun_is_idempotent():
    once = _rw('<script src="theme.js"></script>')
    assert _rw(once) == once


def test_unstamped_ref_still_gets_a_stamp_and_defer():
    out = _rw('<script src="theme.js"></script>')
    assert 'src="theme.js?v=aaaaaaaa"' in out
    assert "defer" in out


def test_hand_written_query_is_left_alone():
    """Only our exact `?v=<8 hex>` shape is ours to rewrite."""
    for src in (
        '<script src="theme.js?v=3" defer></script>',
        '<script src="theme.js?v=ZZZZZZZZ" defer></script>',
        '<script src="theme.js?foo=bar" defer></script>',
        '<script src="theme.js?v=aaaaaaaa&x=1" defer></script>',
    ):
        assert _rw(src) == src, f"rewrote a ref that was not ours: {src}"


def test_fragment_is_left_alone():
    src = '<link href="theme.js#frag">'
    assert _rw(src) == src


def test_cross_origin_is_left_alone():
    src = '<script src="https://js.stripe.com/v3"></script>'
    assert _rw(src) == src


def test_unhashable_asset_keeps_its_existing_stamp():
    out = _rw('<script src="unknown.js?v=deadbeef"></script>')
    assert "unknown.js?v=deadbeef" in out


def test_data_base_shim_is_never_touched():
    src = '<script data-dbase src="data_base.js?v=012345ab"></script>'
    assert _rw(src) == src


def test_preload_hint_is_never_restamped():
    """A preload hint mirrors a URL owned elsewhere and must not mint a second key."""
    for src in (
        '<link rel="preload" as="style" href="onboard.css?v=233832f9">',
        '<link rel="modulepreload" href="theme.js?v=015c6c36">',
        '<link rel="prefetch" href="theme.js?v=015c6c36">',
    ):
        assert _rw(src) == src, f"re-stamped a mirrored hint: {src}"


def test_stylesheet_link_is_still_restamped():
    out = _rw('<link rel="stylesheet" href="onboard.css?v=233832f9">')
    assert 'href="onboard.css?v=bbbbbbbb"' in out


# ---------------------------------------------------------------------------
# AI Brief freshness injection — same post-render asset owner
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
_AIBRIEF_ASSET = "assets/js/aibrief-freshness.js"


def _write_aibrief_asset(site: Path) -> None:
    asset = site / _AIBRIEF_ASSET
    asset.parent.mkdir(parents=True, exist_ok=True)
    asset.write_text("window.__aibriefFreshness = true;\n")


def test_optimizer_attaches_versioned_live_refresh_to_aibrief_page(tmp_path: Path) -> None:
    site = tmp_path / "site"
    site.mkdir()
    _write_aibrief_asset(site)
    (site / "macro.html").write_text(
        '<html><head></head><body><div class="aib2" data-lens="macro">'
        '<span class="aib2-hdr-date">2026-09-09</span></div></body></html>'
    )

    assert optimize(site) == 1

    out = (site / "macro.html").read_text()
    refs = re.findall(
        r'<script src="assets/js/aibrief-freshness\.js\?v=[0-9a-f]{8}" defer></script>',
        out,
    )
    assert len(refs) == 1
    assert out.index(refs[0]) < out.lower().index("</body>")
    assert optimize(site) == 0
    assert (site / "macro.html").read_text().count("aibrief-freshness.js") == 1


def test_optimizer_uses_depth_correct_aibrief_asset_path(tmp_path: Path) -> None:
    site = tmp_path / "site"
    nested = site / "desk" / "daily"
    nested.mkdir(parents=True)
    _write_aibrief_asset(site)
    page = nested / "index.html"
    page.write_text(
        "<html><body><section class='panel aib2' data-lens='macro'></section></body></html>"
    )

    assert optimize(site) == 1
    assert re.search(
        r'<script src="\.\./\.\./assets/js/aibrief-freshness\.js\?v=[0-9a-f]{8}" defer></script>',
        page.read_text(),
    )


def test_optimizer_does_not_duplicate_existing_aibrief_client(tmp_path: Path) -> None:
    site = tmp_path / "site"
    site.mkdir()
    _write_aibrief_asset(site)
    (site / "macro.html").write_text(
        '<html><body><div class="aib2" data-lens="macro"></div>'
        '<script src="assets/js/aibrief-freshness.js"></script></body></html>'
    )

    assert optimize(site) == 1
    out = (site / "macro.html").read_text()
    assert out.count("aibrief-freshness.js") == 1
    assert re.search(r'aibrief-freshness\.js\?v=[0-9a-f]{8}', out)


def test_optimizer_does_not_attach_aibrief_client_to_unrelated_page(tmp_path: Path) -> None:
    site = tmp_path / "site"
    site.mkdir()
    _write_aibrief_asset(site)
    original = "<html><head></head><body><p>ordinary page</p></body></html>"
    (site / "about.html").write_text(original)

    optimize(site)
    assert "aibrief-freshness.js" not in (site / "about.html").read_text()


def test_optimizer_fails_open_when_aibrief_asset_is_missing(tmp_path: Path) -> None:
    site = tmp_path / "site"
    site.mkdir()
    page = site / "macro.html"
    page.write_text('<html><body><div class="aib2" data-lens="macro"></div></body></html>')

    optimize(site)
    assert "aibrief-freshness.js" not in page.read_text()


def test_every_shipped_shared_brief_surface_is_eligible_for_refresh() -> None:
    site = ROOT / "site"
    assert (site / _AIBRIEF_ASSET).is_file()

    for name in ("macro.html", "china.html", "hk.html", "aibrief.html"):
        page = site / name
        text = page.read_text(encoding="utf-8")
        assert re.search(r'class=["\'][^"\']*\baib2\b', text), name
        out = _attach_aibrief_freshness(text, page.parent, site)
        assert out.count("aibrief-freshness.js") == 1, name
        assert out.index("aibrief-freshness.js") < out.lower().rindex("</body>"), name


def test_aibrief_injection_uses_final_body_close_not_literal_inside_script(tmp_path: Path) -> None:
    site = tmp_path / "site"
    _write_aibrief_asset(site)
    source = (
        '<html><body><script>const marker = "</body>";</script>'
        '<div class="aib2" data-lens="macro"></div></body></html>'
    )

    out = _attach_aibrief_freshness(source, site, site)
    assert out.index("aibrief-freshness.js") > out.index("</script>")
    assert out.index("aibrief-freshness.js") < out.rindex("</body>")
    assert 'const marker = "</body>";' in out


# ---------------------------------------------------------------------------
# Browser-client contract (executed with Node from this already-wired suite)
# ---------------------------------------------------------------------------

_AIBRIEF_CLIENT = ROOT / "site" / "assets" / "js" / "aibrief-freshness.js"


def _node_aibrief(body: str) -> dict:
    script = f"const api = require({json.dumps(str(_AIBRIEF_CLIENT))});\n{body}"
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


def test_aibrief_client_replaces_only_strictly_newer_matching_lenses() -> None:
    out = _node_aibrief(
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
    assert out == {"changed": 1, "macro": "2026-09-10", "china": None, "btc": None}


def test_aibrief_client_equal_date_preserves_surface_specific_markup() -> None:
    out = _node_aibrief(
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


def test_aibrief_controller_fetches_same_surface_no_store_and_coalesces() -> None:
    out = _node_aibrief(
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


def test_aibrief_binding_checks_return_and_brief_intent() -> None:
    out = _node_aibrief(
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


def test_aibrief_failed_refresh_keeps_last_valid_brief() -> None:
    out = _node_aibrief(
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
