"""Public dashboard preview-tier contracts."""
from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_public_dashboard_shells_and_controller_are_allowlisted():
    policy = yaml.safe_load((ROOT / "config" / "site_access.yml").read_text())
    public = set(policy["public"]["exact"])
    assert {"/macro.html", "/start.html", "/us_stocks.html", "/tier_preview.css", "/tier_preview.js"} <= public
    assert "/macro.html" not in set(policy["free_registered"]["exact"])


def test_public_hub_globe_topology_is_allowlisted():
    """The public shell must not fetch its map geometry through the regwall."""
    policy = yaml.safe_load((ROOT / "config" / "site_access.yml").read_text())
    public = set(policy["public"]["exact"])
    html = (ROOT / "site" / "start.html").read_text()

    assert 'data-topo="world-110m.json"' in html
    assert "/world-110m.json" in public


def test_stock_preview_controller_enforces_one_three_full():
    js = (ROOT / "templates" / "tier_preview.js").read_text()
    assert 'state = { tier: "anon", cap: 1 }' in js
    assert 'tier === "free" ? 3 : 1' in js
    assert "isPaid(tier) ? Infinity" in js
    assert "Create free account" in js
    assert "Preview 1 signal before signup" not in js
    assert js.count('action: "Create free account"') == 1
    assert js.count('secondary: "Already a member? Sign in"') == 1
    assert (ROOT / "site" / "tier_preview.js").read_text() == js
    assert (ROOT / "site" / "tier_preview.css").read_text() == (
        ROOT / "templates" / "tier_preview.css"
    ).read_text()


def test_stock_preview_uses_one_surface_cta_per_primary_decision_system():
    js = (ROOT / "templates" / "tier_preview.js").read_text()
    assert '{ key: "action", selector: "#action-board" }' in js
    assert '{ key: "prophet", selector: "#us-standouts" }' in js
    assert 'panel.appendChild(makeGate(surface.key))' in js
    assert 'group.root.insertAdjacentElement("afterend", makeGate())' not in js
    assert "Open more of today’s action board" in js
    assert "Expand the Prophet shortlist" in js


def test_dashboard_wires_preview_and_macro_detail_gate():
    template = (ROOT / "templates" / "dashboard.html.j2").read_text()
    theme = (ROOT / "templates" / "theme.js").read_text()
    assert '<script src="tier_preview.js"></script>' in template
    assert '<link rel="stylesheet" href="tier_preview.css">' in template
    assert '<script src="onboard.js"></script>' not in template
    assert '<link rel="stylesheet" href="onboard.css">' not in template
    assert "onboard.js is lazy-loaded" in theme
    assert "s.src = pfx + 'onboard.js'" in theme
    assert "window.MMXAccessPreview.isAnon()" in template
    assert "window.MMXAccessPreview.openSignin()" in template
    for selector in (
        "#action-board .actbody",
        "#us-standouts .nbgrid",
        "body.page-stocks .panel table tbody",
    ):
        assert selector in (ROOT / "templates" / "tier_preview.js").read_text()


# --------------------------------------------------------------------------- #
# Two surfaces inside #us-standouts that rendered REAL board data outside the gate
# --------------------------------------------------------------------------- #
# Both leaks had the same shape: the gate was wired to the CARD markup, and a second
# surface rendering the same board in different markup was never added to it.  Each
# test therefore pins BOTH sides — the controller's selector AND the template that
# emits it — because a rename on either side alone would re-open the leak with every
# assertion still green.

def test_prophet_ran_rows_go_through_the_same_cap_as_the_cards():
    """The `ran` list carries ticker + name + move, one row per name: the same board
    the blurred cards carry, in quieter markup, and it sat ungated directly beneath
    them — an anonymous visitor could read the roster in plain text."""
    js = (ROOT / "templates" / "tier_preview.js").read_text()
    dash = (ROOT / "templates" / "dashboard.html.j2").read_text()
    # The ROW markup moved to templates/_us_ran_rows.html.j2 when the panel gained a
    # server-side split (the client cap below is now the second of two gates, not
    # the only one), so the emitter assertion follows it there. The CONTAINER is
    # still emitted by dashboard.html.j2 and is what tier_preview.js selects on.
    rows = (ROOT / "templates" / "_us_ran_rows.html.j2").read_text()

    # emitter side
    assert '<div class="pbr-l">' in dash
    assert '{% include "_us_ran_rows.html.j2" %}' in dash
    assert '<a class="pbr-r' in rows
    # gate side — inside groups(), so it inherits applyGroup()'s cap/blur/hide path
    # rather than getting a second, drifting rule of its own.
    gfn = js[js.index("function groups()"):js.index("function surfaceFor(")]
    assert 'add("#us-standouts .pbr-l");' in gfn
    # and inside directRows(), or the container yields zero items and gates nothing.
    assert ".dash-tw-row,.pbr-r" in js


def test_retired_prophet_theme_strip_has_no_preview_adapter_left_behind():
    """Prophet no longer repeats the full Theme Heat panel in a mini-strip, so the
    preview script must not keep a dead, separately drifting membership adapter."""
    js = (ROOT / "templates" / "tier_preview.js").read_text()
    dash = (ROOT / "templates" / "dashboard.html.j2").read_text()
    for retired in ("pbt-tk", "pbt-more", "applyThemeTickers", "themeNameCount"):
        assert retired not in dash
        assert retired not in js
    assert "applyTapeMembers();" in js  # the real Theme Heat preview contract remains


def test_preview_entitlement_resolution_follows_current_native_session():
    """Execute the shipped JS, including signout/account switches at async boundaries."""
    import shutil
    import subprocess

    node = shutil.which("node")
    assert node, "preview entitlement behavior requires Node (provided by the CI pack)"
    script = r'''
// Exercise the shipped controller with synthetic sessions and deferred HTTP responses.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const sourcePath = process.argv[2];
if (!sourcePath) throw new Error('candidate source path required');
const source = fs.readFileSync(sourcePath, 'utf8');
const tick = () => new Promise(resolve => setImmediate(resolve));
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
function session(id) {
  return id ? { user: { id }, access_token: 'synthetic-' + id } : null;
}
function harness({ id = 'A', synchronousInitial = false, hints = false, deferSession = false } = {}) {
  let user = id ? { id } : null;
  let activeSession = session(id);
  let lookupFailure = false;
  let listener;
  const attrs = {}, events = [], requests = [], lookups = [];
  const document = {
    cookie: id ? 'sb-test-auth-token=synthetic' : '',
    readyState: 'complete', body: {},
    documentElement: { setAttribute(k, v) { attrs[k] = String(v); }, removeAttribute(k) { delete attrs[k]; } },
    querySelectorAll() { return []; }, querySelector() { return null; }
  };
  const window = {
    MDXAuth: {
      user: () => user,
      hasSession: () => !!activeSession,
      client: () => Promise.resolve({ auth: { getSession() {
        if (lookupFailure) return Promise.reject(new Error('session unavailable'));
        if (!deferSession) return Promise.resolve({ data: { session: activeSession } });
        const lookup = deferred(); lookups.push(lookup); return lookup.promise;
      } } }),
      onChange(fn) { listener = fn; if (synchronousInitial) fn(user, 'INITIAL_SESSION'); }
    },
    dispatchEvent(e) { events.push(e.detail); }
  };
  const context = { window, document, Promise, Date, JSON, Array, String, Infinity,
    setTimeout, clearTimeout, parseInt, location: {},
    sessionStorage: { getItem: () => hints ? JSON.stringify({ me: { tier: 'pro' }, t: Date.now() }) : null },
    localStorage: { getItem: () => hints ? JSON.stringify({ tier: 'pro' }) : null },
    CustomEvent: function(type, options) { this.type = type; this.detail = options.detail; },
    fetch(url, options) {
      assert.equal(url, '/api/me'); assert.equal(options.cache, 'no-store');
      const reply = deferred(); requests.push({ ...reply, options }); return reply.promise;
    }
  };
  vm.runInNewContext(source, context, { filename: sourcePath });
  return { attrs, events, requests, lookups, window,
    refresh: () => window.MMXAccessPreview.refresh(),
    change(next, event) {
      user = next ? { id: next } : null; activeSession = session(next);
      document.cookie = next ? 'sb-test-auth-token=synthetic' : '';
      listener(user, event || (next ? 'SIGNED_IN' : 'SIGNED_OUT'));
    },
    silentIdentity(next) { user = next ? { id: next } : null; activeSession = session(next); },
    failLookup() { lookupFailure = true; },
    tier() { return window.MMXAccessPreview.tier(); },
    cap() { return window.MMXAccessPreview.cap(); }
  };
}
async function reply(request, tier) {
  assert.ok(request, 'expected native /api/me request');
  request.resolve({ ok: true, status: 200, json: () => Promise.resolve({ tier }) });
  await tick();
}
function expectTier(h, tier, cap) {
  assert.equal(h.tier(), tier); assert.equal(h.attrs['data-access-tier'], tier);
  assert.equal(h.cap(), cap);
  assert.ok(h.events.length);
  assert.equal(h.events.at(-1).tier, tier); assert.equal(h.events.at(-1).cap, cap);
}
function expectBounded(h) {
  assert.ok(Number.isFinite(h.cap()), 'unknown/session-loss must not inherit paid preview');
  assert.notEqual(h.tier(), 'pro');
}
const cases = [];
function test(name, body) { cases.push({ name, body }); }

test('same verified user retains paid on transient HTTP failure', async () => {
  const h = harness(); await tick(); await reply(h.requests[0], 'pro');
  h.refresh(); expectTier(h, 'pro', Infinity); await tick(); h.requests[1].resolve({ ok: false, status: 503 }); await tick();
  expectTier(h, 'pro', Infinity);
});
test('same-tier refresh does not emit an access-change event that dismisses open native detail', async () => {
  const h = harness(); await tick(); await reply(h.requests[0], 'pro');
  const n = h.events.length; h.refresh(); await tick(); await reply(h.requests[1], 'pro');
  expectTier(h, 'pro', Infinity); assert.equal(h.events.length, n);
});
test('same verified user retains paid on transient network failure', async () => {
  const h = harness(); await tick(); await reply(h.requests[0], 'pro');
  h.refresh(); await tick(); h.requests[1].reject(new Error('offline')); await tick();
  expectTier(h, 'pro', Infinity);
});
test('explicit server Free replaces paid', async () => {
  const h = harness(); await tick(); await reply(h.requests[0], 'pro');
  h.refresh(); await tick(); await reply(h.requests[1], 'free'); expectTier(h, 'free', 3);
});
for (const status of [401, 403]) {
  test('server denial cannot retain prior paid preview: ' + status, async () => {
    const h = harness(); await tick(); await reply(h.requests[0], 'pro');
    h.refresh(); await tick(); h.requests[1].resolve({ ok: false, status }); await tick();
    expectBounded(h);
  });
}
test('signout invalidates pending paid HTTP response without later paid event', async () => {
  const h = harness(); await tick(); h.change(null); const n = h.events.length;
  await reply(h.requests[0], 'pro'); expectTier(h, 'anon', 1);
  assert.ok(h.events.slice(n).every(x => x.tier !== 'pro'));
});
test('signout invalidates pending JSON body', async () => {
  const h = harness(); await tick(); const body = deferred();
  h.requests[0].resolve({ ok: true, status: 200, json: () => body.promise }); await tick();
  h.change(null); body.resolve({ tier: 'pro' }); await tick(); expectTier(h, 'anon', 1);
});
test('signout invalidates pending session lookup before any entitlement fetch', async () => {
  const h = harness({ deferSession: true }); await tick(); h.change(null);
  h.lookups[0].resolve({ data: { session: session('A') } }); await tick();
  expectTier(h, 'anon', 1); assert.equal(h.requests.length, 0);
});
test('A to B clears prior paid before a failed B response', async () => {
  const h = harness(); await tick(); await reply(h.requests[0], 'pro'); h.change('B');
  expectBounded(h); await tick(); h.requests[1].reject(new Error('offline')); await tick(); expectBounded(h);
});
test('delayed A cannot overwrite B Free', async () => {
  const h = harness(); await tick(); h.change('B'); await tick();
  await reply(h.requests[1], 'free'); await reply(h.requests[0], 'pro'); expectTier(h, 'free', 3);
});
test('older Free cannot overwrite newer Pro', async () => {
  const h = harness(); await tick(); h.refresh(); await tick();
  await reply(h.requests[1], 'pro'); await reply(h.requests[0], 'free'); expectTier(h, 'pro', Infinity);
});
test('older failure cannot overwrite newer Pro', async () => {
  const h = harness(); await tick(); h.refresh(); await tick(); await reply(h.requests[1], 'pro');
  h.requests[0].reject(new Error('late failure')); await tick(); expectTier(h, 'pro', Infinity);
});
test('older paid response cannot overwrite newer Free', async () => {
  const h = harness(); await tick(); h.refresh(); await tick();
  await reply(h.requests[1], 'free'); await reply(h.requests[0], 'pro'); expectTier(h, 'free', 3);
});
test('anonymous cached paid hints do not grant preview', async () => {
  const h = harness({ id: null, hints: true }); await tick(); expectTier(h, 'anon', 1);
  assert.equal(h.requests.length, 0);
});
test('signed-in unbound paid hints do not grant preview', async () => {
  const h = harness({ hints: true }); await tick(); expectBounded(h);
  h.requests[0].reject(new Error('offline')); await tick(); expectBounded(h);
  assert.notEqual(h.tier(), 'free', 'failed read cannot invent confirmed Free');
});
for (const tier of [undefined, null, 'nonsense', {}, []]) {
  test('malformed tier stays unconfirmed: ' + JSON.stringify(tier), async () => {
    const h = harness(); await tick(); await reply(h.requests[0], tier); expectBounded(h);
    assert.notEqual(h.tier(), 'free', 'malformed body cannot invent confirmed Free');
  });
}
for (const [wire, canonical] of [['insider', 'essential'], ['essential', 'essential'], ['pro', 'pro'], ['unlimited', 'unlimited']]) {
  test('server tier alias preserved: ' + wire, async () => {
    const h = harness(); await tick(); await reply(h.requests[0], wire); expectTier(h, canonical, Infinity);
  });
}
test('synchronous INITIAL_SESSION subscription settles through current request', async () => {
  const h = harness({ synchronousInitial: true }); await tick();
  assert.ok(h.requests.length); await reply(h.requests.at(-1), 'pro'); expectTier(h, 'pro', Infinity);
});
test('native user changed before callback delivery cannot receive old paid response', async () => {
  const h = harness(); await tick(); h.silentIdentity('B');
  await reply(h.requests[0], 'pro'); expectBounded(h);
});
test('lost native session clears remembered paid result on refresh', async () => {
  const h = harness(); await tick(); await reply(h.requests[0], 'pro');
  h.silentIdentity(null); h.refresh(); await tick(); expectTier(h, 'anon', 1);
});
test('failed session verification does not reuse remembered paid result', async () => {
  const h = harness(); await tick(); await reply(h.requests[0], 'pro');
  h.failLookup(); h.refresh(); await tick(); expectBounded(h);
});

(async () => {
  const results = [];
  for (const { name, body } of cases) {
    try { await body(); results.push({ name, pass: true }); }
    catch (e) { results.push({ name, pass: false, error: e.message }); }
  }
  const report = { source_path: sourcePath, source_sha256: crypto.createHash('sha256').update(source).digest('hex'),
    scope: 'synthetic current-session/request-order behavior; no network or production entitlement proof',
    passed: results.filter(x => x.pass).length, failed: results.filter(x => !x.pass).length, results };
  console.log(JSON.stringify(report, null, 2));
  if (report.failed) process.exitCode = 1;
})().catch(e => { console.error(e); process.exitCode = 1; });

'''
    result = subprocess.run(
        [node, "-", str(ROOT / "templates" / "tier_preview.js")],
        input=script, text=True, capture_output=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_unconfirmed_preview_offers_access_retry_in_both_languages():
    """Exercise the rendered native gate and its retry action with deferred HTTP."""
    import shutil
    import subprocess

    node = shutil.which("node")
    assert node, "preview access behavior requires Node (provided by the CI pack)"
    script = r'''
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const source = fs.readFileSync(process.argv[2], 'utf8');
const tick = () => new Promise(resolve => setImmediate(resolve));
const requests = [], gates = [];
function element() {
  const attrs = {}, listeners = {};
  return { attrs, listeners, innerHTML: '', classList: { add() {}, remove() {} },
    setAttribute(k,v) { attrs[k] = v; }, getAttribute(k) { return attrs[k] ?? null; },
    removeAttribute(k) { delete attrs[k]; }, hasAttribute(k) { return k in attrs; },
    matches(selector) { return selector !== 'tr'; },
    addEventListener(type, fn) { listeners[type] = fn; },
    remove() { const n = gates.indexOf(this); if (n >= 0) gates.splice(n,1); }
  };
}
const root = { children: Array.from({length:6}, element), closest: s => s === '#us-standouts' ? root : null };
const document = { cookie: 'sb-test-auth-token=synthetic', readyState: 'complete', body: {}, documentElement: element(),
  querySelectorAll: s => s === '#us-standouts .nbgrid' ? [root] : s === '[data-mx-tier-gate]' ? [...gates] : [],
  querySelector: s => s === '#us-standouts' ? { appendChild(gate) { gates.push(gate); } } : null,
  createElement() { const gate = element(); gate.button = element(); gate.querySelector = s => s === '.mx-tier-primary' ? gate.button : null; return gate; }
};
const window = { MDXAuth: { user: () => ({id:'A'}), client: () => Promise.resolve({auth: { getSession: () => Promise.resolve({data: {session: {user:{id:'A'},access_token:'synthetic'}}}) }}), onChange() {} }, dispatchEvent() {} };
vm.runInNewContext(source, { window, document, Promise, Date, JSON, Array, String, Infinity, parseInt, setTimeout, clearTimeout,
  fetch: () => new Promise(resolve => requests.push(resolve)), CustomEvent: function() {}, location: {},
  sessionStorage: {getItem: () => null}, localStorage: {getItem: () => null} });
(async () => {
  await tick(); requests[0]({ok:false,status:503}); await tick();
  assert.equal(gates.length,1); assert.equal(window.MMXAccessPreview.tier(),'unknown');
  assert.match(gates[0].innerHTML, /Check access/); assert.match(gates[0].innerHTML, /检查访问权限/);
  assert.doesNotMatch(gates[0].innerHTML, /signup|Expand the Prophet shortlist|Unlock full Prophet/);
  gates[0].button.listeners.click(); await tick(); assert.equal(requests.length,2);
  console.log('PASS: unconfirmed native gate offers bilingual access retry without signup/upgrade or a paid grant');
})().catch(e => { console.error(e); process.exitCode=1; });

'''
    result = subprocess.run(
        [node, "-", str(ROOT / "templates" / "tier_preview.js")],
        input=script, text=True, capture_output=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_pricing_copy_matches_preview_limits_and_drops_china_pitch():
    plans = (ROOT / "templates" / "plans.html.j2").read_text()
    index = (ROOT / "templates" / "index.html").read_text()
    onboard = (ROOT / "templates" / "onboard.js").read_text()
    theme = (ROOT / "templates" / "theme.js").read_text()
    combined = "\n".join((plans, index, onboard, theme))
    assert "3 signals per daily list" in combined
    assert "preview 1 before signup" in combined
    assert "6 buy signals a day" not in combined
    assert "6 signals a day" not in combined
    assert "China special situations" not in plans
    assert "The China event desk" not in plans
