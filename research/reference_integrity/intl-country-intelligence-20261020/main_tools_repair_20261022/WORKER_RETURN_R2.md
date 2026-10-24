All100 tests pass. Here is the complete return.

---

# Return: intl-country-cockpit Tools disclosure — bounded worker patch

**Operation:** intl-country-cockpit-20261018 · source `ae6de4e56e2f826beab78f4de29fcaa89f27dbeb`
**Parent:** native `/root` (schema-safe `parent_id: root`), sole source integrator
**Role consumed:** bounded Mastermind Fabric **worker** (`skills/mastermind-fabric-orchestration/references/worker.md`, protected Mastermind `c9cbee5569ba50e30e28715d930809061a169517`). No descendants, no independent-review self-approval, no publish/deploy, no commits/push/PR/deploy/external messaging, no production access. Prior run `intl-20261021-shell-country-repair-r1` (root `01a1101f-…`, UNKNOWN effect) was **not** queried, retried or consumed. Original root accounting preserved.

## 1. Outcome

Fix is 3 hunks in one production file + one new focused regression file. It reproduces the reported failure **exactly** in a real browser against the real bridge, and the same suite fails on the unmodified baseline and passes after the fix.

## 2. Baseline binding

| Artifact | SHA256 |
|---|---|
| `templates/intl_country_cockpit.js` @ baseline (ae6de4e5) | `d9827c38995d766f0cf7a4c1112353d1dabb42835ba5fd88ade1ef95dd83d45a` |
| `templates/intl_country_cockpit.js` **patched** | `bd369bd48318d6fdb5c8247cc7e87f2e091b1c6bf0d118dc926441046aaeef8e` |
| `tests/intl_country_cockpit_navigation.test.cjs` **new** | `665b13ad7fec7c279fd08a14069c9054430d92bf8156a74d2b6dc4919f8e291a` |
| `site/intl_country_cockpit.js` (optional, see §7) | `bd369bd48318d6fdb5c8247cc7e87f2e091b1c6bf0d118dc926441046aaeef8e` |

Scratch tree: `/home/ubuntu2/mmx-scratch/intl-country-r2`. `patch.diff` (507 lines, 23936 bytes) applies cleanly (`git apply --check -p1` OK) to a pristine baseline tree and reproduces both files byte-for-byte.

## 3. Root cause (confirmed, not assumed)

I inspected the bridge's real contract in `templates/shared_shell_bridge.js`:

- `projectAnchor` (L468) rewrites every authored first-party href to `parentOrigin + canonical.slice(childOrigin.length)` — **path and non-transport query preserved byte-for-byte, only the origin swapped**; `installAnchors` (L587) does an immediate full pass, so the attribute is projected at INIT.
- `onClick` (L499) `preventDefault`s and `applyFragmentNavigation` (L323) mutates the child location with native `replaceState` — **so no native `hashchange` ever fires**.
- `handleLocationAccepted` (L965) dispatches `mmx:shell-location` **with no `detail`**, and only after the parent ACKs a requestId whose canonical equals the child's *already-updated* `currentCanonical()`.
- Same-hash repeat: `applyFragmentNavigation` → `canonical === curCanonical` → `scrollFragmentTarget` only — **no NAVIGATE, no ACK, no history**.

Two controller defects, exactly as diagnosed: the click matcher `a[href="#intl-analysis-tools"]` compares a literal fragment that projection has already replaced, and `followHash` was only bound to `hashchange`, which parent-owned acceptance never fires.

## 4. Reproduction of the KNOWN REAL FAILURE (unmodified baseline)

Scratch diagnostic `diagnostic.mjs` (not part of the patch), real bridge + real cross-origin iframe on the production origins, modeled parent:

```
controller sha256 : d9827c38995d766f0cf7a4c1112353d1dabb42835ba5fd88ade1ef95dd83d45a
projected href    : https://beta.mastermind-x.com/intl.html#intl-analysis-tools
before click open : false
NAVIGATE          : [{"href":"https://www.mastermind-x.com/intl.html#intl-analysis-tools","requestId":"req-1"}]
LOCATION_ACCEPTED : [{"requestId":"req-1","canonicalPath":"/intl.html#intl-analysis-tools"}]
parent URL        : /intl.html#intl-analysis-tools
child location    : /intl.html?mmx_shell=1&mmx_generation=g1#intl-analysis-tools
native hashchange : 0
tools.open AFTER  : false          <-- outer disclosure stays closed
--- repeated click at the same hash ---
NAVIGATE count    : 1              <-- no new ACK / history entry
tools.open AFTER  : false
```

This matches the reported evidence line-for-line (real run used `http://127.0.0.1:3100`/`3102`; same shape, `req-2` vs `req-1` is only sequence position).

Same diagnostic after the patch — **identical protocol traffic**, only the outcome differs:

```
controller sha256 : bd369bd48318d6fdb5c8247cc7e87f2e091b1c6bf0d118dc926441046aaeef8e
NAVIGATE / LOCATION_ACCEPTED : unchanged (1 each)
parent URL        : /intl.html#intl-analysis-tools
tools.open AFTER  : true          <-- fixed
--- repeated click at the same hash ---
NAVIGATE count    : 1   ACCEPTED count : 1   parent URL unchanged
tools.open AFTER  : true          <-- fixed, no fabricated history
```

## 5. THE PATCH — `templates/intl_country_cockpit.js`

```diff
diff --git a/templates/intl_country_cockpit.js b/templates/intl_country_cockpit.js
index a62bf0f..e5cc811 100644
--- a/templates/intl_country_cockpit.js
+++ b/templates/intl_country_cockpit.js
@@ -86,6 +86,85 @@
           if (node.tagName === "DETAILS") node.open = true;
       }
     }
+    /* ---- destination identity ----
+     * The Shared Shell bridge projects every authored first-party href to the
+     * admitted parent origin before the user can click it, so an authored
+     * "#intl-analysis-tools" is observed as an absolute parent-origin URL. The
+     * projection is the bridge's own contract (projectAnchor): it canonicalizes
+     * the destination, drops the shell transport query keys and swaps only the
+     * origin, keeping path and remaining query byte for byte. Recognition
+     * therefore compares the resolved destination against this document's own
+     * canonical path and query instead of a literal fragment string, so a
+     * projected link and a standalone link behave identically while a foreign
+     * path or query lookalike still fails to match.
+     */
+    var SHELL_TRANSPORT_KEYS = ["mmx_shell", "mmx_generation"];
+    function nonTransportSearch(search) {
+      var raw = String(search || "");
+      if (raw.charAt(0) === "?") raw = raw.slice(1);
+      if (!raw) return "";
+      var kept = [];
+      raw.split("&").forEach(function (part) {
+        if (!part) return;
+        var eq = part.indexOf("=");
+        var key = eq === -1 ? part : part.slice(0, eq);
+        var name = key;
+        try { name = decodeURIComponent(key.replace(/\+/g, " ")); } catch (_) {}
+        if (SHELL_TRANSPORT_KEYS.indexOf(name) === -1) kept.push(part);
+      });
+      return kept.length ? "?" + kept.join("&") : "";
+    }
+    function selfCanonical() {
+      try {
+        var self = new URL(window.location.href);
+        return {origin: self.origin, key: self.pathname + nonTransportSearch(self.search)};
+      } catch (_) {
+        return null;
+      }
+    }
+    // The bridge publishes its own supported liveness marker on the public API
+    // object it installs. That object only exists once the bridge has passed its
+    // own boot guards, and "active" only turns true for a trusted, verified INIT.
+    function shellProjectionLive() {
+      try {
+        var api = window.MMXSharedShell;
+        return !!(api && api.__mmxBridge === "mmx.shared-shell.v1" && api.active === true);
+      } catch (_) {
+        return false;
+      }
+    }
+    // The bridge installs itself only after proving document.referrer's origin is
+    // one of its exact admitted parents, and that origin is the one it projects
+    // to. Reading it here reuses the bridge's own admission record; an unrelated
+    // origin, path or query never qualifies.
+    function admittedShellOrigin() {
+      if (!shellProjectionLive()) return null;
+      try { return new URL(document.referrer).origin; } catch (_) { return null; }
+    }
+    function selfDestination(url) {
+      var self = selfCanonical();
+      if (!self || !url) return false;
+      if (url.pathname + nonTransportSearch(url.search) !== self.key) return false;
+      if (url.origin === self.origin) return true;
+      var admitted = admittedShellOrigin();
+      return !!admitted && url.origin === admitted;
+    }
+    // Same containment contract as exposeLegacyAnchor: the disclosure itself, or
+    // anything inside it.
+    function toolsDestination(url) {
+      if (!tools || !url || !url.hash) return false;
+      var id = null;
+      try { id = decodeURIComponent(url.hash.slice(1)); } catch (_) { return false; }
+      if (!id) return false;
+      var target = document.getElementById(id);
+      return !!target && (target === tools || tools.contains(target));
+    }
+    function anchorDestination(anchor) {
+      var href = null;
+      try { href = anchor.getAttribute("href"); } catch (_) { return null; }
+      if (typeof href !== "string" || href === "") return null;
+      try { return new URL(href, window.location.href); } catch (_) { return null; }
+    }
     root.addEventListener("click", function (event) {
       if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return;
       var link = event.target.closest("a[data-imc-country]");
@@ -100,7 +179,16 @@
         select("#" + summary.parentElement.id, false);
         return;
       }
-      if (event.target.closest('a[href="#intl-analysis-tools"]') && tools) tools.open = true;
+      // The tools link keeps its native activation so the bridge still owns the
+      // navigation and the single parent history transition. Opening the outer
+      // disclosure is this controller's own responsibility, including when the
+      // destination is already the current hash and the parent therefore accepts
+      // no new navigation at all.
+      var toolsLink = event.target.closest("a[href]");
+      if (toolsLink && root.contains(toolsLink) && tools) {
+        var destination = anchorDestination(toolsLink);
+        if (destination && selfDestination(destination) && toolsDestination(destination)) tools.open = true;
+      }
     });
     root.addEventListener("toggle", syncRail, true);
     function followHash() {
@@ -115,6 +203,10 @@
       });
     }
     window.addEventListener("hashchange", followHash);
+    // Parent-owned acceptance notifies mmx:shell-location instead of inventing a
+    // native hashchange. The actual location is already current here, so read it
+    // directly and never trust a URL carried by the event.
+    window.addEventListener("mmx:shell-location", followHash);
     if (tools && new URLSearchParams(window.location.search).has("view")) tools.open = true;
     followHash();
     syncRail();
```

Design notes for review:
- **No parent-origin trust shortcut was invented.** The origin check is the bridge's own two admission facts: `window.MMXSharedShell.__mmxBridge === "mmx.shared-shell.v1" && api.active === true` (the bridge's documented "public API (candidate only)" surface, L1064–1099) plus `document.referrer`'s origin, which the bridge itself proves is an exact admitted parent before it installs (L128). No origin is hardcoded, no allowlist widened, no event/global payload trusted.
- `followHash` reads `window.location` only — it never reads `event.detail` (the bridge sends none anyway). No `pushState`/`replaceState` is added anywhere.
- The tools link is **not** `preventDefault`ed, so the bridge keeps owning navigation and the single parent transition.

## 6. NEW TEST — `tests/intl_country_cockpit_navigation.test.cjs`

Runs the **real** `templates/shared_shell_bridge.js` in a **real cross-origin iframe** on the production origins (`https://beta.mastermind-x.com` parent / `https://www.mastermind-x.com` child, all requests fulfilled from the file, no network, no fixed ports), driving genuine `mmx.shared-shell.v1` INIT → NAVIGATE → LOCATION_ACCEPTED. Style mirrors `tests/intl_workspace_legacy_navigation.test.cjs` (node:test + Playwright + route fixture + `addScriptTag`-equivalent served `/templates/*.js`).

**The parent shell in the test is a MODELED parent and is labeled as such in the file header.** It is a stand-in for the Terminal parent, not a substitute for the parent's actual supported-runtime acceptance.

```javascript
'use strict';
/*
 * Browser regression for the International country cockpit "Data & tools" disclosure.
 *
 * Shell mode runs the REAL child bridge (templates/shared_shell_bridge.js) in a real
 * cross-origin iframe on the production parent/child origins, so the authored
 * "#intl-analysis-tools" href is genuinely projected to the parent origin exactly as
 * the reproduced defect does, and activation really travels
 * AppShell -> SharedShellRuntime -> LegacyPageHost -> NAVIGATE -> LOCATION_ACCEPTED.
 *
 * The parent shell below is a MODELED parent: it speaks the real mmx.shared-shell.v1
 * messages and owns its own URL, but it is a test stand-in, not the Terminal parent.
 * These tests therefore prove controller behavior against genuine bridge behavior in
 * a real browser; the parent's actual supported-runtime acceptance run remains the
 * only qualifying product proof.
 */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');
const { chromium } = require('playwright');

const root = path.resolve(__dirname, '..');
const templates = path.join(root, 'templates');

// Production origins: the bridge admits https://beta.mastermind-x.com as the parent
// of a https://www.mastermind-x.com child, exactly like the real shell. Every
// request is fulfilled from this file, so no network and no fixed port is involved.
const PARENT_ORIGIN = 'https://beta.mastermind-x.com';
const CHILD_ORIGIN = 'https://www.mastermind-x.com';
const GENERATION = 'g1';
const TRANSPORT = `mmx_shell=1&mmx_generation=${GENERATION}`;

let browser;

test.before(async () => {
  browser = await chromium.launch({ headless: true,
    ...(process.env.PLAYWRIGHT_CHROMIUM_CHANNEL ? { channel: process.env.PLAYWRIGHT_CHROMIUM_CHANNEL } : {}) });
});

test.after(async () => {
  if (browser) await browser.close();
});

const CHILD_BODY = `
  <div data-im-country-analysis id="cockpit">
    <div class="imc-toolbar"><div class="imc-toolbar-anchor" id="toolbar-anchor"></div></div>
    <div class="imc-assistant-slot" id="assistant-slot"></div>
    <nav class="imc-country-rail">
      <a id="rail-jp" href="#imc-country-JP" data-imc-country>Japan</a>
      <a id="rail-kr" href="#imc-country-KR" data-imc-country>Korea</a>
    </nav>
    <details class="imc-country" id="imc-country-JP" open>
      <summary>Japan</summary><p id="jp-body">Japan</p>
    </details>
    <details class="imc-country" id="imc-country-KR">
      <summary>Korea</summary><p id="kr-body">Korea</p>
    </details>
    <p><a id="tools-link" href="#intl-analysis-tools">Data &amp; tools</a></p>
  </div>
  <details id="intl-analysis-tools">
    <summary>Data &amp; tools</summary><p id="intl-tools-body">Tools</p>
  </details>`;

function childHtml({ bridge }) {
  return `<!doctype html><html lang="en"><head><meta charset="utf-8">
  <title>International country cockpit</title>
  <meta name="mmx-shell-document" content="20261018.1">
  <meta name="mmx-shell-response" content="content">
  <style>:root{--mmx-shared-shell-css-ready:1}</style>
  ${bridge ? '<script src="/shared_shell_bridge.js"></script>' : ''}
  </head><body>${CHILD_BODY}
  <script src="/intl_country_cockpit.js"></script>
  </body></html>`;
}

// Modeled parent shell. It performs only what the real AppShell does for this
// protocol: hand the child a verified INIT, own its own URL, and acknowledge a
// NAVIGATE with the exact requestId and child-relative canonical path.
function parentHtml() {
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Shell</title></head>
  <body>
  <h1>Shell</h1>
  <iframe id="legacy-frame" title="Legacy" style="width:100%;height:600px"></iframe>
  <script>
  (function () {
    var frame = document.getElementById('legacy-frame');
    var state = window.__mmxShell = { navigates: [], accepted: [], pushes: 0, autoAccept: true, ready: null, errors: [] };
    function accept(nav) {
      var canonical = new URL(nav.href);
      var canonicalPath = canonical.pathname + canonical.search + canonical.hash;
      if (nav.mode === 'replace') window.history.replaceState(null, '', canonicalPath);
      else window.history.pushState(null, '', canonicalPath);
      if (nav.mode !== 'replace') state.pushes += 1;
      state.accepted.push({ requestId: nav.requestId, canonicalPath: canonicalPath });
      frame.contentWindow.postMessage({
        protocol: 'mmx.shared-shell.v1', frameGeneration: nav.frameGeneration, type: 'LOCATION_ACCEPTED',
        requestId: nav.requestId, canonicalPath: canonicalPath
      }, ${JSON.stringify(CHILD_ORIGIN)});
    }
    window.addEventListener('message', function (event) {
      if (event.origin !== ${JSON.stringify(CHILD_ORIGIN)}) return;
      if (event.source !== frame.contentWindow) return;
      var data = event.data;
      if (!data || data.protocol !== 'mmx.shared-shell.v1') return;
      if (data.type === 'NAVIGATE') { state.navigates.push(data.href); if (state.autoAccept) accept(data); return; }
      if (data.type === 'READY') { state.ready = data.href; return; }
      if (data.type === 'ERROR') state.errors.push(data.code);
    });
    frame.addEventListener('load', function () {
      frame.contentWindow.postMessage({
        protocol: 'mmx.shared-shell.v1', frameGeneration: ${JSON.stringify(GENERATION)}, type: 'INIT',
        theme: 'dark', locale: 'en', contextRevision: 1, canonicalPath: '/intl.html',
        catalog: { legacyPaths: ['/intl.html', '/dashboard'], nativePaths: [] }, restore: null
      }, ${JSON.stringify(CHILD_ORIGIN)});
    });
    frame.src = ${JSON.stringify(`${CHILD_ORIGIN}/intl.html?${TRANSPORT}`)};
  }());
  </script></body></html>`;
}

async function openShell({ initialHash = '', autoAccept = true } = {}) {
  const context = await browser.newContext();
  const page = await context.newPage();
  page.setDefaultTimeout(5000);
  await context.route('**/*', route => {
    const url = new URL(route.request().url());
    if (url.origin === PARENT_ORIGIN && url.pathname === '/shell') {
      return route.fulfill({ contentType: 'text/html; charset=utf-8', body: parentHtml() });
    }
    if (url.origin === CHILD_ORIGIN && url.pathname === '/intl.html') {
      return route.fulfill({ contentType: 'text/html; charset=utf-8', body: childHtml({ bridge: true }) });
    }
    const file = path.join(templates, url.pathname.slice(1));
    if (url.origin === CHILD_ORIGIN && file.startsWith(templates + path.sep) && fs.existsSync(file) && fs.statSync(file).isFile()) {
      return route.fulfill({ path: file, contentType: 'text/javascript' });
    }
    return route.abort();
  });
  await page.goto(`${PARENT_ORIGIN}/shell${initialHash}`);
  await page.waitForFunction(() => window.__mmxShell && window.__mmxShell.ready !== null);
  if (!autoAccept) await setAutoAccept(page, false);
  const frame = page.frames().find(f => f.url().startsWith(CHILD_ORIGIN));
  assert.ok(frame, 'the legacy child frame is live');
  assert.equal(await frame.evaluate(() => window.MMXSharedShell && window.MMXSharedShell.active), true);
  return { context, page, frame };
}

async function openStandalone({ initialHash = '' } = {}) {
  const context = await browser.newContext();
  const page = await context.newPage();
  page.setDefaultTimeout(5000);
  await context.route('**/*', route => {
    const url = new URL(route.request().url());
    if (url.origin === CHILD_ORIGIN && url.pathname === '/intl.html') {
      return route.fulfill({ contentType: 'text/html; charset=utf-8', body: childHtml({ bridge: false }) });
    }
    const file = path.join(templates, url.pathname.slice(1));
    if (url.origin === CHILD_ORIGIN && file.startsWith(templates + path.sep) && fs.existsSync(file) && fs.statSync(file).isFile()) {
      return route.fulfill({ path: file, contentType: 'text/javascript' });
    }
    return route.abort();
  });
  await page.goto(`${CHILD_ORIGIN}/intl.html${initialHash}`);
  await page.waitForFunction(() => document.getElementById('cockpit').dataset.imcEnhanced === 'true');
  return { context, page, frame: page.mainFrame() };
}

const setAutoAccept = (page, value) => page.evaluate(v => { window.__mmxShell.autoAccept = v; }, value);
const shellState = page => page.evaluate(() => ({
  navigates: window.__mmxShell.navigates.slice(),
  pushes: window.__mmxShell.pushes,
  url: location.pathname + location.search + location.hash,
}));
const href = (frame, id) => frame.locator(`#${id}`).getAttribute('href');
const isOpen = (frame, id) => frame.evaluate(el => document.getElementById(el).open, id);
const childLocation = frame => frame.evaluate(() => location.pathname + location.search + location.hash);

// A lookalike href is authored into the live anchor and its own default activation is
// suppressed so a foreign destination cannot actually be followed during the test.
async function setLookalike(frame, value) {
  await frame.evaluate(v => {
    const link = document.getElementById('tools-link');
    link.setAttribute('href', v);
    link.addEventListener('click', event => event.preventDefault());
  }, value);
}

test('shell: the reproduced precondition projects the authored fragment to the parent origin', async () => {
  const { context, page, frame } = await openShell();
  try {
    assert.equal(await href(frame, 'tools-link'), `${PARENT_ORIGIN}/intl.html#intl-analysis-tools`);
    assert.equal(await href(frame, 'rail-jp'), `${PARENT_ORIGIN}/intl.html#imc-country-JP`);
    assert.equal(await isOpen(frame, 'intl-analysis-tools'), false);
    assert.deepEqual((await shellState(page)).navigates, []);
  } finally {
    await context.close();
  }
});

test('shell: first projected Tools activation opens the outer disclosure with one parent transition', async () => {
  const { context, page, frame } = await openShell();
  try {
    await frame.locator('#tools-link').click();
    await frame.waitForFunction(() => document.getElementById('intl-analysis-tools').open);
    assert.equal(await isOpen(frame, 'intl-analysis-tools'), true);

    const state = await shellState(page);
    assert.deepEqual(state.navigates, [`${CHILD_ORIGIN}/intl.html#intl-analysis-tools`]);
    assert.equal(state.pushes, 1);
    assert.equal(state.url, '/intl.html#intl-analysis-tools');
    assert.equal(await childLocation(frame), `/intl.html?${TRANSPORT}#intl-analysis-tools`);
    assert.equal(await isOpen(frame, 'imc-country-JP'), true, 'the country selection is untouched');
  } finally {
    await context.close();
  }
});

test('shell: repeated same-hash Tools activation reopens a manually collapsed disclosure', async () => {
  const { context, page, frame } = await openShell();
  try {
    await frame.locator('#tools-link').click();
    await frame.waitForFunction(() => document.getElementById('intl-analysis-tools').open);
    await frame.evaluate(() => { document.getElementById('intl-analysis-tools').open = false; });
    assert.equal(await isOpen(frame, 'intl-analysis-tools'), false);

    await frame.locator('#tools-link').click();
    await frame.waitForFunction(() => document.getElementById('intl-analysis-tools').open);

    const state = await shellState(page);
    assert.equal(state.navigates.length, 1, 'the already-current fragment is never re-navigated');
    assert.equal(state.pushes, 1, 'no parent history entry is fabricated for the repeat');
  } finally {
    await context.close();
  }
});

test('shell: accepted bridge navigation reopens the disclosure after a manual collapse', async () => {
  const { context, page, frame } = await openShell();
  try {
    await frame.locator('#rail-jp').click();
    await frame.waitForFunction(() => document.getElementById('imc-country-KR').open === false &&
      location.hash === '#imc-country-JP');
    assert.equal(await isOpen(frame, 'intl-analysis-tools'), false);

    // The supported bridge API, not a click: only an accepted shell location can open
    // the outer disclosure here.
    await frame.evaluate(() => window.MMXSharedShell.navigate('/intl.html#intl-analysis-tools'));
    await frame.waitForFunction(() => document.getElementById('intl-analysis-tools').open);

    const state = await shellState(page);
    assert.equal(state.navigates.length, 2);
    assert.equal(state.pushes, 2);
    assert.equal(await childLocation(frame), `/intl.html?${TRANSPORT}#intl-analysis-tools`);
  } finally {
    await context.close();
  }
});

test('shell: an accepted location that claims a different destination is ignored', async () => {
  const { context, page, frame } = await openShell();
  try {
    await frame.locator('#rail-jp').click();
    await frame.waitForFunction(() => location.hash === '#imc-country-JP');

    await frame.evaluate(() => {
      window.dispatchEvent(new CustomEvent('mmx:shell-location', {
        detail: { href: 'https://beta.mastermind-x.com/intl.html#intl-analysis-tools' }
      }));
    });
    assert.equal(await isOpen(frame, 'intl-analysis-tools'), false,
      'the handler must read the actual location, not the event detail URL');
    assert.equal(await isOpen(frame, 'imc-country-JP'), true);
    assert.equal((await shellState(page)).navigates.length, 1, 'no navigation is invented from an event');
  } finally {
    await context.close();
  }
});

test('shell: the disclosure opens even when the parent has not accepted yet', async () => {
  const { context, page, frame } = await openShell({ autoAccept: false });
  try {
    await frame.locator('#tools-link').click();
    await frame.waitForFunction(() => document.getElementById('intl-analysis-tools').open);
    const state = await shellState(page);
    assert.equal(state.navigates.length, 1);
    assert.equal(state.pushes, 0, 'the parent never accepted, so it owns no history');
    assert.equal(await childLocation(frame), `/intl.html?${TRANSPORT}#intl-analysis-tools`);
  } finally {
    await context.close();
  }
});

const lookalikes = [
  ['foreign origin', `${PARENT_ORIGIN.replace('beta.', 'lookalike.')}/intl.html#intl-analysis-tools`],
  ['foreign path', '/other.html#intl-analysis-tools'],
  ['foreign query', '/intl.html?x=1#intl-analysis-tools'],
  ['foreign fragment', '/intl.html#intl-analysis-tool'],
  ['no fragment', '/intl.html'],
];

for (const [label, value] of lookalikes) {
  test(`shell: a ${label} lookalike does not open the disclosure`, async () => {
    const { context, frame } = await openShell();
    try {
      await setLookalike(frame, value);
      await frame.locator('#tools-link').click();
      assert.equal(await isOpen(frame, 'intl-analysis-tools'), false);
    } finally {
      await context.close();
    }
  });
}

test('shell: a modified click keeps native semantics and does not open the disclosure', async () => {
  const { context, frame } = await openShell();
  try {
    await frame.locator('#tools-link').click({ modifiers: ['Control'] });
    assert.equal(await isOpen(frame, 'intl-analysis-tools'), false);
    assert.equal(await isOpen(frame, 'imc-country-JP'), true);
  } finally {
    await context.close();
  }
});

test('shell: country rail selection keeps exactly one parent transition', async () => {
  const { context, page, frame } = await openShell();
  try {
    await frame.locator('#rail-kr').click();
    await frame.waitForFunction(() => document.getElementById('imc-country-KR').open);
    assert.equal(await isOpen(frame, 'imc-country-JP'), false);
    assert.equal(await frame.getAttribute('#rail-kr', 'aria-current'), 'location');
    assert.equal(await frame.getAttribute('#rail-jp', 'aria-current'), null);

    const state = await shellState(page);
    assert.deepEqual(state.navigates, [`${CHILD_ORIGIN}/intl.html#imc-country-KR`]);
    assert.equal(state.pushes, 1);
    assert.equal(state.url, '/intl.html#imc-country-KR');
    assert.equal(await isOpen(frame, 'intl-analysis-tools'), false);
  } finally {
    await context.close();
  }
});

test('standalone: the authored fragment link opens and reopens the disclosure', async () => {
  const { context, page } = await openStandalone();
  try {
    assert.equal(await page.locator('#tools-link').getAttribute('href'), '#intl-analysis-tools');
    await page.locator('#tools-link').click();
    await page.waitForFunction(() => document.getElementById('intl-analysis-tools').open);
    assert.equal(new URL(page.url()).hash, '#intl-analysis-tools');

    await page.evaluate(() => { document.getElementById('intl-analysis-tools').open = false; });
    await page.locator('#tools-link').click();
    await page.waitForFunction(() => document.getElementById('intl-analysis-tools').open);
    assert.equal(await page.evaluate(() => window.MMXSharedShell), undefined, 'no bridge surface in standalone');
  } finally {
    await context.close();
  }
});

test('standalone: a foreign lookalike does not open the disclosure', async () => {
  const { context, page } = await openStandalone();
  try {
    await setLookalike(page.mainFrame(), 'https://lookalike.example/intl.html#intl-analysis-tools');
    await page.locator('#tools-link').click();
    assert.equal(await isOpen(page.mainFrame(), 'intl-analysis-tools'), false);
  } finally {
    await context.close();
  }
});

test('standalone: a view query still opens the disclosure on startup', async () => {
  const { context, page } = await openStandalone({ initialHash: '?view=macro' });
  try {
    assert.equal(await isOpen(page.mainFrame(), 'intl-analysis-tools'), true);
  } finally {
    await context.close();
  }
});
```

## 7. Optional artifact — `site/intl_country_cockpit.js` (PARENT DECISION NEEDED)

`https://…/ae6de4e5…/site/intl_country_cockpit.js` returns **404**: the published site copy of this controller **does not exist at ae6de4e5** (`site/shared_shell.js`/`shared_shell_bridge.js`/`shared_shell.css` do exist and are byte-identical to their templates). So the assignment's "plain paired copy, same bytes" is not a parity edit — it would be a **new published asset**.

I did **not** include it in the patch, to keep the patch minimal and to avoid publishing a file the parent may not want. The exact bytes are ready if you want it: `optional/site/intl_country_cockpit.js`, SHA256 `bd369bd4…` (byte-identical to the patched `templates/` file). **Open question:** does the parent want the site paired copy created, or is it build-generated / intentionally absent for this controller?

## 8. Commands and actual results

Environment: node `v22.23.3`, playwright `1.64.1` (installed into scratch only), chromium `156.0.8078.4` (pre-existing cache).

| Command | Result |
|---|---|
| `node --test tests/intl_country_cockpit_navigation.test.cjs` — **patched** | **16/16 pass** |
| `node --test tests/intl_country_cockpit_navigation.test.cjs` — **unmodified baseline** (`d9827c38…`, sha-verified before the run) | **12 pass / 4 FAIL** |
| `node --test tests/js/shared_shell_bridge.test.cjs` | **70/70 pass** |
| `node --test tests/intl_workspace_legacy_navigation.test.cjs tests/intl_country_cockpit_navigation.test.cjs` | **30/30 pass** |
| **combined final**: all three suites | **100/100 pass** |
| `node --check` on both changed files | valid JS |
| `git apply --check -p1 patch.diff` on pristine baseline | clean; applied result byte-identical (`bd369bd4…`, `665b13ad…`) |

Baseline failure set (the discriminating core — all four are the reproduced defect):

```
not ok 2 - shell: first projected Tools activation opens the outer disclosure with one parent transition
not ok 3 - shell: repeated same-hash Tools activation reopens a manually collapsed disclosure
not ok 4 - shell: accepted bridge navigation reopens the disclosure after a manual collapse
not ok 6 - shell: the disclosure opens even when the parent has not accepted yet
error: 'frame.waitForFunction: Timeout 5000ms exceeded.'   (x4 — the disclosure never opens)
```

The 12 that **pass on the baseline too** are the preservation guards (lookalikes ×5, modified click, country rail one-transition, precondition, standalone ×3, hostile-detail) — they prove the patch does not merely make the disclosure open indiscriminately.

## 9. Acceptance mapping

1. ✅ First click, repeated same-hash click, and re-collapsing at the same hash all open the disclosure (tests 2, 3, 14). Only the document's own canonical path+non-transport query qualifies; foreign origin / path / query / fragment / no-fragment lookalikes do not (5 shell + 1 standalone test).
2. ✅ `mmx:shell-location` is consumed via `followHash`, which reads `window.location` only. No `pushState`/`replaceState` is introduced; test 3 asserts the repeat adds **0** new parent entries and test "hostile detail" asserts a lying `event.detail` URL is ignored.
3. ✅ Standalone links, normal/modified clicks, country selection/focus + `aria-current`, one parent transition, transport-generation retention (`childLocation` asserted as `/intl.html?mmx_shell=1&mmx_generation=g1#…`), and nested legacy behavior are unchanged. **No parent, bridge, allowlist, protocol or authentication change** — the bridge is untouched (its 70-test suite is green).
4. ✅ The regression executes real controller + real bridge behavior in real Chromium. Before-failure with the unmodified baseline and after-success are both captured above. **The harness models the parent shell and is labeled as such**; this is not a product acceptance claim.
5. ✅ No data/country analysis, CSS, design, proposal, CI packing or manifest change. No frozen evidence touched. `shared_shell.css`, `site/shared_shell*` were fetched **read-only as run fixtures only** and are not part of the patch.
6. ✅ This return contains the complete unified diff, the full new file, SHA256s, exact commands/results, baseline binding, deviations and open questions — all inline, no inaccessible-host paths.

## 10. Deviations, limitations, open questions

- **Deviation:** `site/intl_country_cockpit.js` omitted from the patch (§7) — it does not exist upstream at ae6de4e5; bytes supplied separately for the parent's call.
- **Deviation:** added `optional/site/` and two extra read-only fixture fetches (`templates/shared_shell.css`, `site/shared_shell.{css,js}`) purely so the existing 70-test bridge suite could run; not part of the patch.
- **Limitation:** `tests/intl_workspace_page.test.cjs` was **not run** — it generates its fixture via `tests/test_intl_workspace_integration.py` (plus `python3`), which is outside my assigned input list and was not fetched. It loads `intl_workspace_entry.js`, not the patched controller, so no direct regression is expected — but the parent's full run should cover it.
- **Limitation:** product qualification remains the parent's actual supported-runtime acceptance (Terminal `127.0.0.1:3100` / child `3102`). My ports/origins differ by construction.
- **Open question:** the modeled parent in the test uses `theme:'dark', locale:'en', contextRevision:1` and a two-path catalog. If the real Terminal parent's INIT shape differs materially, only the test fixture needs updating — the controller fix does not depend on it.
- **Open question (worth a look):** the bridge's `applyFragmentNavigation` uses `replaceState` for the child's fragment, so a fragment never becomes a child history entry — the observed "one parent history transition" behavior is the bridge's, and my patch preserves it rather than changing it.
