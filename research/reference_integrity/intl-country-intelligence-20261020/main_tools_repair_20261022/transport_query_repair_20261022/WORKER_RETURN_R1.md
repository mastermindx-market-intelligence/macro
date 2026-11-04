Work complete. This bounded worker role is consumed; I am not self-accepting the repair.

## Outcome

One complete, reviewable patch for the workspace/Shared Shell query-ownership defect. All 7 changed files are inside the allowed set; nothing else was touched.

**Deliverable (complete unified diff, 1275 lines, 80,079 bytes):**
`/home/ubuntu3/scratch-intl-20261022/workspace-transport-query.patch`
SHA256 `420997f5ec5174601ebe4572bbaa357288df5655637915e1742a13ae104dfe28`

The response cap (60,000 UTF-8 bytes) is smaller than the complete diff, so I inline the **entire production change** below (10,080 bytes) and deliver the test hunks as the file rather than truncating anything. Verified `git apply --check` → exit 0 against a clean BASE tree; applying it reproduces the patched tree byte-for-byte on all 7 files.

## Production change (complete; `site/` copies are byte-identical)

```diff
diff --git a/templates/shared_shell_bridge.js b/templates/shared_shell_bridge.js
index 235e77e..ad4f146 100644
--- a/templates/shared_shell_bridge.js
+++ b/templates/shared_shell_bridge.js
@@ -133,6 +133,9 @@

   var installed = true;
   w.__MMX_SHARED_BRIDGE_INSTALLED__ = true;
+  // Instance liveness for the public API. cleanup() retires this candidate; a
+  // persisted pagehide never calls cleanup, so a BFCache document stays live.
+  var apiLive = true;

   var state = { active: false, chrome: false, anchors: false, runtime: false };
   var admitted = null;
@@ -1077,6 +1080,7 @@
       correctionCancelers.length = 0;
     } catch (e) {}
     try { if (anchorObserver) { anchorObserver.disconnect(); anchorObserver = null; } } catch (e) {}
+    apiLive = false;
     domReadyWaiters = null;
     domReadyListener = null;
     domReadyHandlerRef = null;
@@ -1139,6 +1143,42 @@
         if (!isFragmentAgainst(cls.canonical, cls.current)) return null;
         return fragmentOf(cls.canonical);
       } catch (e) { return null; }
+    },
+    /* Read-only projection of the query of the page this document is already
+     * showing, with the two transport pairs removed by the SAME byte-preserving
+     * filter the canonical projection uses. Those two pairs belong to the shell
+     * frame rather than to the page's own query vocabulary, so a child that reads
+     * location.search itself sees them as foreign keys; the page that needs the
+     * business query asks here instead of re-implementing - or loosely
+     * approximating - that filter.
+     *
+     * Every other byte survives exactly: encoding, order, duplicates and empty
+     * segments are returned unchanged, so the caller's own strict validation still
+     * decides what is acceptable and no wildcard, normalization, serialization,
+     * truncation or parser relaxation is introduced here.
+     *
+     * A projection of the CURRENT page is not evidence of parent admission, of an
+     * accepted destination or of LOCATION_ACCEPTED, and it carries no navigation
+     * authority: a caller that needs any of those must go through navigate() and the
+     * parent's acknowledgment. It returns a value; it never navigates. No message,
+     * error or request id, nothing queued for a later INIT, and no history, DOM,
+     * attribute, scroll, focus or observer effect.
+     *
+     * It is available before INIT - the API is installed by the blocking head script
+     * ahead of every page script - because a fresh document has to know its own query
+     * before any parent context arrives. It is NOT available after cleanup(): the
+     * retired flag plus the exact-instance identity check make a cached reference to a
+     * cleaned-up bridge refuse, exactly like any other dead capability. A persisted
+     * pagehide performs no cleanup, so a BFCache document keeps its live reader.
+     */
+    readPageSearch: function () {
+      try {
+        if (!apiLive) return null;
+        if (w.MMXSharedShell !== api) return null;
+        var raw = null;
+        try { raw = String(w.location.search || ""); } catch (e) { return null; }
+        return filterTransport(raw);
+      } catch (e) { return null; }
     }
   };
   try {
diff --git a/templates/intl_workspace.js b/templates/intl_workspace.js
index 0ac7bb2..6830a36 100644
--- a/templates/intl_workspace.js
+++ b/templates/intl_workspace.js
@@ -1648,6 +1648,50 @@
     return urlPath(location.pathname) + '?' + query + anchorHash(location, controller.config.anchor_ids);
   }

+  /* ---- external query ownership ----
+   * Inside a shared-shell frame the child URL carries two transport pairs the page's
+   * own strict query vocabulary does not contain. Handing location.search straight to
+   * the parser therefore refuses a perfectly good transport-only URL as an invalid
+   * business query: it reports "Invalid URL state restored" and silently discards the
+   * requested nondefault state. The shell bridge already owns the byte-preserving
+   * removal of exactly those two pairs, so the page asks it for a projection of its
+   * own current query rather than reproducing - or loosening - that filter here.
+   *
+   * The provider is BOUND once, at mount, and is never re-acquired. A later
+   * replacement, a swapped API object or a cleanup is the loss of a capability, not
+   * an invitation to fall back to raw standalone parsing, which would silently accept
+   * a query this frame is no longer entitled to project. Identity is re-checked on
+   * every read, so a cached method whose instance was retired refuses.
+   *
+   * "Unavailable" is never an empty query. An empty query is a genuine answer and is
+   * returned as "". A bridge that is installed but older, refusing, throwing or
+   * returning a non-string is unavailable, not empty; only a page with no bridge at
+   * all keeps the ordinary standalone raw validation.
+   */
+  function bindQuerySource(win) {
+    var shell = win.MMXSharedShell;
+    // Only a self-identifying bridge instance is a capability. Anything else - absent,
+    // null, or a foreign object that merely happens to sit on the same global - leaves
+    // the page exactly where it was before this repair: ordinary standalone raw
+    // validation, which is also what a cleaned-up bridge correctly reduces to.
+    if (typeof shell === 'undefined' || shell === null || shell.__mmxBridge !== 'mmx.shared-shell.v1') {
+      return { standalone: true, shell: null, reader: null };
+    }
+    return { standalone: false, shell: shell, reader: typeof shell.readPageSearch === 'function' ? shell.readPageSearch : null };
+  }
+
+  function externalQuery(controller) {
+    var source = controller.querySource;
+    if (!source) return { available: false, query: null };
+    if (source.standalone) return { available: true, query: controller.environment.window.location.search };
+    if (!source.reader) return { available: false, query: null };
+    if (controller.environment.window.MMXSharedShell !== source.shell) return { available: false, query: null };
+    if (source.shell.readPageSearch !== source.reader) return { available: false, query: null };
+    var value;
+    try { value = source.reader.call(source.shell); } catch (_) { return { available: false, query: null }; }
+    return typeof value === 'string' ? { available: true, query: value } : { available: false, query: null };
+  }
+
   function stageAndCommit(controller, state, issues, actionType) {
     var previous = controller.state;
     var snapshot = snapshotRoot(controller.root);
@@ -1698,9 +1742,22 @@

   function popstate(controller) {
     if (!controller.live) return;
+    // The external read is obtained and its capability verified BEFORE any state,
+    // history, inspector, scenario or focus mutation. A refused capability reports
+    // the refusal and stops: validated state, serializedQuery, inspector attachment
+    // and mode, the scenario draft and pending proposal, the return stack, the
+    // baseline and the current focus are all left exactly as they were. The browser
+    // has already moved its own location and that location stays as received - this
+    // path never sanitizes the URL, commits a history entry or focuses a heading.
+    var external = externalQuery(controller);
+    if (!external.available) {
+      controller.issues = [{ code: 'UI_UPDATE_FAILED', field: 'url' }];
+      repaintIssues(controller);
+      return;
+    }
     var hadInspector = !!controller.inspector;
     if (hadInspector) visuallyCloseInspector(controller, { release: true });
-    var parsed = controller.reducer.parseQuery(controller.environment.window.location.search);
+    var parsed = controller.reducer.parseQuery(external.query);
     var committed = commitResearch(controller, parsed, 'popstate');
     if (controller.pendingScenario) {
       try { controller.environment.window.history.replaceState(null,'',nextUrl(controller,controller.serializedQuery)); }
@@ -1850,7 +1907,7 @@
     };
     var controller = {
       root: root, config: config, bindingVersion: bindingVersion, configWithSource: configWithSource, reducer: reducer, environment: { window: window },
-      state: null, issues: [], serializedQuery: '', live: false, original: [], inspector: null, scenarioDraft:null, pendingScenario:null
+      state: null, issues: [], serializedQuery: '', live: false, original: [], inspector: null, scenarioDraft:null, pendingScenario:null, querySource:null
     };
     controller.library = prepareLibrary(root,config);
     controller.inspectorHost = prepareInspector(controller);
@@ -1861,7 +1918,20 @@
       required(root, '[data-im-heading]').setAttribute('tabindex', '-1');
       required(root, '[data-im-issues]').setAttribute('role', 'status');
       required(root, '[data-im-unavailable]');
-      var parsed = reducer.parseQuery(window.location.search);
+      // The shell query provider is bound here, once, and the initial read runs
+      // inside the existing mount rollback boundary: an unavailable capability
+      // throws into the catch below, which tears the half-installed controller down,
+      // restores the pristine snapshot and lets the entry script present its readable
+      // fallback. A returned business query is NOT re-interpreted here - the strict
+      // parser still owns genuine invalid queries, length bounds and vocabulary.
+      controller.querySource = bindQuerySource(window);
+      var external = externalQuery(controller);
+      if (!external.available) {
+        var refusal = new TypeError('International workspace query source is unavailable');
+        refusal.code = 'UNAVAILABLE_QUERY_SOURCE';
+        throw refusal;
+      }
+      var parsed = reducer.parseQuery(external.query);
       if (IntlWorkspaceScenario && owned(root,'[data-im-history-panel]').length) controller.scenarioDraft=IntlWorkspaceScenario.createDraft(scenarioContext(parsed.state));
       stageAndCommit(controller, parsed.state, parsed.issues, 'mount', false);
       controller.live = true;
```

## Compatibility and lifetime decisions

- **Additive only.** One new API member, `readPageSearch()`. `PROTOCOL`, `BRIDGE_VERSION` (20261018.1), `DOCUMENT_VERSION`, the catalog/admission logic, allowlists and every other existing API member are untouched. No wildcard, serialization, normalization, truncation or parser relaxation; `filterTransport()` is reused directly.
- **Pre-INIT availability, not active-gated.** The API is installed by the blocking head script ahead of every page script, so a fresh document learns its own query before any parent context arrives. Existing candidate boot guards are unchanged and still mandatory.
- **Lifetime.** Two independent guards: the bridge's `apiLive` flag (cleared only in `cleanup()`) plus an exact-instance identity check, so a cached reference to a cleaned-up bridge refuses. A persisted `pagehide` performs no cleanup, so a BFCache document keeps its live reader. `sameDocumentFragment`/`navigate`/`openAuth` behavior is unchanged.
- **Consumer binding is one-shot.** The provider is bound at mount and never re-acquired. A later replacement, swap or cleanup is a capability loss — never a silent fallback to raw standalone parsing. A *string* result of `""` is a genuine answer; only unavailable returns the refusal.
- **Identity marker.** Only a self-identifying bridge (`__mmxBridge === 'mmx.shared-shell.v1'`) counts as a capability. Anything else — absent, null, or a foreign object on the same global — keeps the exact pre-existing standalone raw validation. That is also the correct reading of a cleaned-up bridge, which deletes the global.
- **Failure paths.** Mount failure throws a coded `TypeError` inside the existing mount rollback boundary (teardown + `restoreRoot` + rethrow), which the entry script's existing catch turns into `controls.disabled = true` and `legacy.open = true`. At popstate the read is obtained and validated **before** `visuallyCloseInspector` or any other mutation; failure sets `[{code:'UI_UPDATE_FAILED',field:'url'}]`, calls `repaintIssues()` and returns. `UI_UPDATE_FAILED` has no `ISSUE_TEXT` entry, so the rendered text is the existing "Workspace state unavailable" / "工作区状态不可用". No fragment-ACK listener was added.
- **Focus diagnosis noted, not "fixed".** I confirmed `paintLibrary` returns early when `library.panel.hidden`, so the static Library search input stays disabled while another view is shown. I implemented no focus retry, no protocol change and no URL sanitation, and I do **not** claim the parent-exposure theory is uniquely proved — that measurement stays with Root.

## Artifacts and SHA256

All 10 declared BASE baselines verified OK before and after (`sha256sum -c`, 10/10). Paired template/site equality confirmed with `cmp` for both asset pairs, before and after.

| File | BASE SHA256 | Patched SHA256 |
|---|---|---|
| `templates/shared_shell_bridge.js` | `31b150d8335f7abafa6210bcaf26d98a9e7e2251e34a09ce69f4524c59720e30` | `24d7bb10d1c59a2d051b3279c436c3581ced7dfe53da3872d1452a1cde2019bf` |
| `site/shared_shell_bridge.js` | `31b150d8335f7abafa6210bcaf26d98a9e7e2251e34a09ce69f4524c59720e30` | `24d7bb10d1c59a2d051b3279c436c3581ced7dfe53da3872d1452a1cde2019bf` |
| `templates/intl_workspace.js` | `d910e296a5d6ea9b58f79ec59ab112b79a58cad21dff96f0a4831204ab06b296` | `f09421d4dad8dcdb86e5591d63e53836347e54afdcc2a330defa79eb672f96c5` |
| `site/intl_workspace.js` | `d910e296a5d6ea9b58f79ec59ab112b79a58cad21dff96f0a4831204ab06b296` | `f09421d4dad8dcdb86e5591d63e53836347e54afdcc2a330defa79eb672f96c5` |
| `tests/js/shared_shell_bridge.test.cjs` | `c6641ae09c5fdf4e131be0c4b2104410d916c70ccc6c75618d53b287c8de7aa3` | `cc6551d371b6960148adcc50bd0d06264b78fefe512d76ccc87d99680c15c73f` |
| `tests/intl_workspace_controller.test.cjs` | `436c4e27d2d41507ee1c8ce30523b6964cbffa7d3b172916ec7714151558e4af` | `148fe2799c01a958ec38356a2b14d3b116c91b86b79c09494eaab19d0bf0fc86` |
| `tests/intl_workspace_state.test.cjs` | `25bcbae7b91eb4b7612b071a49f1acdb828308895fb8f4e5072a343dbf85993d` | `7a357cc834eefe423cdf37195bde80ab891c4069b0b43e3f64bcb1a7950e7113` |

Verified UNCHANGED (BASE == patched): `templates/intl_workspace_state.js`, `templates/intl_workspace_entry.js`, `templates/intl_workspace_scenario.js`, `templates/intl_country_cockpit.js`, `templates/shared_shell.css`, `templates/intl_library_search.js`, `site/shared_shell.css`, `site/intl_workspace_state.js`, `site/intl_workspace_entry.js`, `tests/intl_country_cockpit_navigation.test.cjs`, `tests/test_shared_shell_injection.py`.

## Validation — exact commands, exits, counts

Run in the tree where the delivered patch was applied to a clean BASE:

```
$ node --test tests/js/shared_shell_bridge.test.cjs    → tests 79  pass 79  fail 0   exit=0
$ node --test tests/intl_workspace_state.test.cjs      → tests 22  pass 22  fail 0   exit=0
$ node --test tests/intl_workspace_controller.test.cjs → tests 52  pass 52  fail 0   exit=0
$ PYTHONPATH=. python3 -m pytest tests/test_shared_shell_injection.py -q → 34 passed exit=0
$ node --test tests/intl_country_cockpit_navigation.test.cjs → tests 18 pass 17 fail 1 exit=1
```

No existing assertion was weakened, skipped or removed, and no timeout was broadened. BASE baselines were 74 / 20 / 43 / 18 / 34 — so the deltas are +5 bridge, +2 state, +9 controller, all passing.

## Genuine baseline negative results (new tests against pristine BASE sources)

Verified by SHA256 that the control tree really carries BASE `templates/shared_shell_bridge.js` and `templates/intl_workspace.js`, with only the new test files copied in.

**The two required discriminating cases fail on BASE for the observed defect, not an absent-API TypeError:**

```
✖ shell frame: transport-only pre-INIT mount keeps the default state, the URL and the history
  AssertionError: a transport-only URL is not an invalid business query
  + actual 'Invalid URL state restored'   - expected ''

✖ shell frame: a valid nondefault business query beside the transport restores the real state
  AssertionError: the requested state is not reported as invalid
  + actual 'Invalid URL state restored'   - expected ''
```

I reordered the transport-only test's assertions specifically so its BASE failure is the warning text, not `readPageSearch is not a function`.

Full BASE control: bridge `79 tests / 74 pass / 5 fail` (all 5 new `readPageSearch` cases fail — expected, the API is new); state `22 / 22 / 0` (tests 21 and 22 pin unchanged parser semantics, so they correctly pass on BASE); controller `52 / 45 / 7 fail` — the 7 failures are the transport-only, nondefault, negatives, popstate, refusal, unusable-provider and cleaned-bridge cases. Two new tests pass on BASE by design and are reported as such: `a standalone page with no bridge keeps the exact existing raw query validation` and `shell frame: a foreign object on the bridge global is not a bridge and keeps standalone parsing` — both are preservation tests.

New test inventory (16 cases): bridge 5 (`readPageSearch removes exactly the two transport keys and preserves every other byte`; `…is available before INIT, is not admission, and follows the current page`; `…is pure: repeated pre- and post-INIT reads have no effect and queue nothing`; `…refuses a retired, replaced or unreadable instance, including a cached reference`; `a persisted pagehide keeps readPageSearch live, and the reader is absent without the bridge`); state 2 (tests 21–22,19 refusal cases each carrying its genuine issue code and field); controller 9 (`shell frame: …` ×7 plus the standalone and foreign-object cases).

The controller cases are **real Playwright with the real production bridge in a real cross-origin child iframe** (`localhost:3105` inside `localhost:3100`, `document.referrer` = `http://localhost:3100/`), booted through the **real** `intl_workspace_entry.js` with production injection order (CSS → blocking bridge → page scripts). They are **not** the Terminal-parent proof. The shared-bridge unit harness remains the pre-existing `vm`-modeled one; `tests/intl_workspace_state.test.cjs` needs no browser.

## One preserved-suite failure needing an out-of-scope change

`tests/intl_country_cockpit_navigation.test.cjs` → `E protocol, version and admission are unchanged by the repair` fails deterministically (17/18, 3/3 repeat runs, also fails on BASE). Cause: line 678 pins the exact published key set, whose comment reads "The helper is the only addition to the published surface":

```
- ['__mmxBridge','active','applyingContext','navigate','openAuth','sameDocumentFragment']
+ ['__mmxBridge','active','applyingContext','navigate','openAuth','readPageSearch','sameDocumentFragment']
```

This file is a **read-only dependency**, outside my allowed set, so I could not update it. I deliberately did not dodge it by making `readPageSearch` non-enumerable — that would contradict this bridge's own convention (`active`/`applyingContext` are defined `enumerable: true` precisely so they appear) and would be tailoring code to satisfy a guard. Protocol string, `bridgeVersion`, `documentVersion`, `responseKind`, admission and `Object.isFrozen` all still assert correctly in that same test. **Required follow-up by Root:** insert `'readPageSearch'` into that expected array at `tests/intl_country_cockpit_navigation.test.cjs:678`.

## Environment and limits

- Node v24.21.0, Python 3.12.3, Chromium (Chrome for Testing 156.0.8078.4) headless via `chromium.launch({headless:true})` — the exact launch shape already in the file; no `executablePath`, no `PLAYWRIGHT_CHROMIUM_CHANNEL` override.
- Playwright 1.64.1 installed into scratch only, chosen because it maps to the `chromium_headless_shell-1248` already in `~/.cache/ms-playwright`.
- No repository clone. Only exact-pin raw files were fetched (`raw.githubusercontent.com/.../macro/14ed4f12f31b71c63bbabd969aebbf9c4305ccaa/`), plus read-only Python test dependencies needed to make `tests/test_shared_shell_injection.py` runnable at all (`lib/`, `scripts/`, `app/`, `tests/fixtures/intl_workspace/history_cases.json`). All 34 injection tests pass; without those dependencies8 of them error on collection, which is an environment limitation, not a result.
- Not run here: any `lib.pages` / asset-optimizer / build pipeline, ordinary build, or actual Terminal-parent proof. Root owns those.
- Every edit lives in `/home/ubuntu3/scratch-intl-20261022/{base,patched,basecontrol,applycheck,applycheck2}`. No file in the original workspace or any other worktree was read-modified; no staging, commit to a real repo, push, PR, comment, message, deployment, production change, data acquisition or authentication change. The only commits are to my own throwaway scratch git repo.
