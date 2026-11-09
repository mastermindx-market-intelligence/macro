"""User-visible contract for the Portfolio snapshot page on the Macro site."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "mastermind.html.j2"
JS = ROOT / "templates" / "mastermind.js"
SITE_ACCESS = ROOT / "config" / "site_access.yml"
CADDY = ROOT / "app" / "deploy" / "Caddyfile"
LIFECYCLE_SOURCE = {
    "repository": "mastermindx-market-intelligence/Mastermind",
    "path": "portfolio/registry.py",
    "commit": "42ba5c76eb7ce1fdf44f3b44f332928668939df4",
    "blob": "f5eb632d8f2d8dfcdbe11abb19076f9d746b38fe",
    "recorded_at": "2026-08-11T22:13:49Z",
    "effective_at": None,
}


def _node(expression: str):
    if shutil.which("node") is None:
        pytest.fail("node is required to execute the Mastermind page contract")
    script = (
        f"const mm = require({json.dumps(str(JS))});\n"
        f"const value = ({expression});\n"
        "process.stdout.write(JSON.stringify(value));\n"
    )
    proc = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_static_chrome_does_not_claim_a_current_daily_cadence() -> None:
    text = TEMPLATE.read_text(encoding="utf-8").lower()
    assert "daily snapshot" not in text
    assert "pushed twice" not in text
    assert "refreshed twice" not in text


def test_live_dashboard_fallback_uses_the_public_https_product() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    assert 'id="mm-live" href="https://bot.mastermind-x.com"' in text
    assert "http://localhost:8000" not in text


def test_snapshot_cannot_override_the_live_link_with_loopback() -> None:
    assert _node('mm.safeLiveUrl("http://localhost:8000")') == "https://bot.mastermind-x.com"
    assert _node('mm.safeLiveUrl("https://bot.mastermind-x.com")') == "https://bot.mastermind-x.com"
    assert _node('mm.safeLiveUrl("https://evil.example")') == "https://bot.mastermind-x.com"


def test_structured_market_status_formats_as_human_text() -> None:
    assert _node('mm.formatMarketStatus({open:false, venue:"HKEX"}, "en")') == "HKEX · Closed"
    assert _node('mm.formatMarketStatus({open:true, venue:"NASDAQ"}, "en")') == "NASDAQ · Open"
    assert _node('mm.formatMarketStatus("After hours", "en")') == "After hours"


def test_snapshot_freshness_distinguishes_current_and_stale_bytes() -> None:
    fresh = _node(
        'mm.snapshotFreshness("2026-09-19T12:00:00Z", Date.parse("2026-09-21T12:00:00Z"))'
    )
    stale = _node(
        'mm.snapshotFreshness("2026-09-18T11:59:59Z", Date.parse("2026-09-21T12:00:00Z"))'
    )
    unknown = _node('mm.snapshotFreshness("not-a-date", Date.parse("2026-09-21T12:00:00Z"))')
    assert fresh["state"] == "fresh"
    assert stale["state"] == "stale"
    assert stale["ageHours"] > 72
    assert unknown["state"] == "unknown"


def test_access_failures_keep_the_shell_truthful() -> None:
    signin = _node('mm.accessState(401, {signin_url:"/?signin=1"}, "en")')
    upgrade = _node('mm.accessState(403, {upgrade_url:"/plans.html?plan=pro"}, "en")')
    unavailable = _node('mm.accessState(500, {}, "en")')
    assert signin == {"kind": "signin", "href": "/?signin=1"}
    assert upgrade == {"kind": "upgrade", "href": "/plans.html?plan=pro"}
    assert unavailable == {"kind": "unavailable", "href": ""}


def test_archived_books_are_explicitly_classified() -> None:
    archived = _node(
        'mm.bookLifecycle({archived:true,status:"archived",superseded_by:"autonomous"}, "en")'
    )
    active = _node('mm.bookLifecycle({active:true,status:"active"}, "en")')
    assert archived["archived"] is True
    assert archived["label"] == "Archived"
    assert archived["supersededBy"] == "autonomous"
    assert active["archived"] is False
    assert active["label"] == "Active"


def test_missing_lifecycle_is_unknown_instead_of_active() -> None:
    unknown = _node('mm.bookLifecycle({id:"flagship"}, "en")')
    assert unknown["active"] is False
    assert unknown["archived"] is False
    assert unknown["label"] == "Status unavailable"


@pytest.mark.parametrize("value", ["javascript:alert(1)", "//evil.example", "/\\evil.example", "/other-page"])
def test_access_actions_refuse_unsafe_or_unintended_routes(value: str) -> None:
    signin = _node(f'mm.accessState(401, {{signin_url:{json.dumps(value)}}}, "en")')
    upgrade = _node(f'mm.accessState(403, {{upgrade_url:{json.dumps(value)}}}, "en")')
    assert signin["href"] == "/?signin=1"
    assert upgrade["href"] == "/plans.html?upgrade=1&plan=pro"


def test_presentation_script_is_public_but_snapshot_payload_remains_gated() -> None:
    config = yaml.safe_load(SITE_ACCESS.read_text(encoding="utf-8"))
    public_exact = set(config["public"]["exact"])
    assert "/mastermind.js" in public_exact
    assert "/mastermind/mastermind_snapshot.json" not in public_exact

    caddy = CADDY.read_text(encoding="utf-8")
    assert caddy.count("/mastermind.js") >= 4
    assert "/mastermind/mastermind_snapshot.json" not in caddy


def test_committed_snapshot_carries_current_lifecycle_and_safe_default() -> None:
    payload = json.loads(
        (ROOT / "site" / "mastermind" / "mastermind_snapshot.json").read_text(encoding="utf-8")
    )
    books = {book["id"]: book for book in payload["books"]}

    assert payload["live_url"] == "https://bot.mastermind-x.com"
    assert payload["default_book"] == "autonomous"
    for book_id in {"flagship", "heavyweight", "etf"}:
        assert books[book_id]["active"] is False
        assert books[book_id]["status"] == "archived"
        assert books[book_id]["archived"] is True
        assert books[book_id]["superseded_by"] == "autonomous"
    for book_id in {"autonomous", "china", "hk", "self_directed"}:
        assert books[book_id]["active"] is True
        assert books[book_id]["status"] == "active"
        assert books[book_id]["archived"] is False


def test_frozen_july_snapshot_identifies_its_later_registry_source() -> None:
    payload = json.loads((ROOT / "site/mastermind/mastermind_snapshot.json").read_text())
    # A future complete producer snapshot may replace this historical artifact.
    # While the July data is retained, its later lifecycle overlay must be explicit.
    if payload["generated_at"] == "2026-07-29T22:25:01Z":
        assert payload["lifecycle_source"] == LIFECYCLE_SOURCE


def test_published_page_keeps_data_and_registry_clocks_separate() -> None:
    assert (ROOT / "site/mastermind.js").read_bytes() == JS.read_bytes()
    script = r'''
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {createHash} = require("node:crypto");
const {JSDOM} = require("jsdom");
const root = process.argv[1];
const source = JSON.parse(process.argv[2]);
const html = fs.readFileSync(path.join(root, "site/mastermind.html"), "utf8");
const js = fs.readFileSync(path.join(root, "site/mastermind.js"), "utf8");
const published = JSON.parse(fs.readFileSync(path.join(root, "site/mastermind/mastermind_snapshot.json"), "utf8"));
async function openPage(payload, status = 200) {
  const dom = new JSDOM(html, {url: "https://www.mastermind-x.com/mastermind.html", runScripts: "outside-only"});
  // Load only the committed, content-addressed page CSS. No remote resources
  // or unrelated shared scripts execute in this controlled consumer.
  const links = [...dom.window.document.querySelectorAll('link[rel="stylesheet"][href^="assets/css/"]')];
  assert.equal(links.length, 1);
  for (const link of links) {
    const match = link.getAttribute("href").match(/^assets\/css\/([0-9a-f]{8})\.css\?v=\1$/);
    assert.ok(match);
    const css = fs.readFileSync(path.join(root, "site/assets/css", match[1] + ".css"), "utf8");
    assert.equal(createHash("sha256").update(css).digest("hex").slice(0, 8), match[1]);
    const style = dom.window.document.createElement("style");
    style.textContent = css;
    link.replaceWith(style);
  }
  dom.window.Date.now = () => Date.parse("2026-08-12T00:00:00Z");
  let requests = 0;
  dom.window.fetch = async (url, options) => {
    assert.match(url, /^mastermind\/mastermind_snapshot\.json\?_=/);
    assert.equal(options.credentials, "same-origin");
    assert.equal(options.cache, "no-store");
    requests++;
    return {ok: status === 200, status, json: async () => payload};
  };
  dom.window.eval(js);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(requests, 1);
  return dom;
}
(async () => {
  const payload = structuredClone(published);
  payload.generated_at = "2026-07-29T22:25:01Z";
  payload.lifecycle_source = source;
  let dom = await openPage(payload);
  const doc = dom.window.document;
  const state = doc.querySelector("#mm-state");
  assert.ok(state.querySelector(".mm-notice-stale"));
  assert.equal(state.querySelector(".mm-data-time").getAttribute("datetime"), payload.generated_at);
  assert.equal(state.querySelector(".mm-lifecycle-time").getAttribute("datetime"), source.recorded_at);
  assert.match(state.textContent, /Data snapshot/);
  assert.match(state.textContent, /Book status source recorded/);
  assert.match(state.textContent, /does not update the holdings snapshot/);
  const sourceLink = state.querySelector("a");
  assert.equal(sourceLink.href, `https://github.com/${source.repository}/blob/${source.commit}/${source.path}`);
  assert.equal(doc.querySelector('[role="tab"][aria-selected="true"]').getAttribute("data-book"), "autonomous");
  doc.querySelector('[role="tab"][data-book="flagship"]').click();
  assert.match(doc.querySelector(".mm-archive-note").textContent, /Archived book/);
  for (const selector of [".mm-notice", ".mm-archive-note"]) {
    const rule = [...doc.styleSheets].flatMap(sheet => [...sheet.cssRules]).find(rule => rule.selectorText === selector);
    assert.ok(rule, selector);
    assert.match(rule.style.getPropertyValue("border"), /1px solid var\(--line\)/);
    for (const edge of ["left", "right", "top", "bottom"]) {
      assert.equal(rule.style.getPropertyValue(`border-${edge}`), "", selector);
    }
  }
  doc.documentElement.setAttribute("data-lang", "zh");
  doc.dispatchEvent(new dom.window.Event("langchange"));
  assert.match(state.textContent, /数据快照时间/);
  assert.match(state.textContent, /账本状态来源记录时间/);
  assert.equal(state.querySelector(".mm-data-time").getAttribute("datetime"), payload.generated_at);
  assert.equal(state.querySelector(".mm-lifecycle-time").getAttribute("datetime"), source.recorded_at);
  assert.ok(state.querySelector(".mm-notice-stale"));
  assert.equal(doc.querySelector('[role="tab"][aria-selected="true"]').getAttribute("data-book"), "flagship");
  assert.match(doc.querySelector(".mm-archive-note").textContent, /已归档账本/);
  dom.window.close();

  // Legacy data still renders, but missing lifecycle fields cannot create activity.
  const legacy = structuredClone(payload);
  delete legacy.lifecycle_source;
  legacy.default_book = "flagship";
  const flagship = legacy.books.find(book => book.id === "flagship");
  for (const key of ["active", "status", "archived", "superseded_by", "archived_reason"]) delete flagship[key];
  dom = await openPage(legacy);
  assert.equal(dom.window.document.querySelector(".mm-lifecycle-time"), null);
  assert.equal(dom.window.document.querySelector('[role="tab"][aria-selected="true"]').getAttribute("data-book"), "autonomous");
  assert.match(dom.window.document.querySelector('[role="tab"][data-book="flagship"]').textContent, /Status unavailable/);
  dom.window.close();

  for (const [status, cls, href] of [[401, "signin", "/?signin=1"], [403, "upgrade", "/plans.html?upgrade=1&plan=pro"]]) {
    dom = await openPage({signin_url: "javascript:alert(1)", upgrade_url: "//evil.example"}, status);
    assert.equal(dom.window.document.querySelector(`.mm-access-${cls} a`).getAttribute("href"), href);
    assert.equal(dom.window.document.querySelector(".mm-lifecycle-time"), null);
    assert.equal(dom.window.document.querySelector("#mm-tabs").children.length, 0);
    assert.equal(dom.window.document.querySelector("#mm-state").children.length, 0);
    dom.window.close();
  }
  dom = await openPage({}, 500);
  assert.ok(dom.window.document.querySelector(".mm-access-unavailable"));
  assert.equal(dom.window.document.querySelector("#mm-tabs").children.length, 0);
  assert.equal(dom.window.document.querySelector("#mm-state").children.length, 0);
  dom.window.close();
})().catch(error => {console.error(error); process.exitCode = 1;});
'''
    proc = subprocess.run(
        ["node", "-e", script, str(ROOT), json.dumps(LIFECYCLE_SOURCE)],
        cwd=ROOT, text=True, capture_output=True, check=False, timeout=30,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
