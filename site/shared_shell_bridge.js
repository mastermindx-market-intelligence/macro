/*
 * mmx.shared-shell.v1 first-party browser CHILD bridge.
 * Plain browser IIFE: no dependencies, imports, eval, innerHTML, auth SDK,
 * tokens, arbitrary message commands, fetch/XHR/timers, cookie/storage reads.
 * Host contract decided 2026-10-18; parent owns actual document replacement.
 */
(function () {
  "use strict";

  var PROTOCOL = "mmx.shared-shell.v1";
  var BRIDGE_VERSION = "20261018.1";
  var DOCUMENT_META_NAME = "mmx-shell-document";
  var RESPONSE_META_NAME = "mmx-shell-response";
  var APPROVED_PARENT_ORIGINS = ["https://beta.mastermind-x.com", "https://app.mastermind-x.com"];
  var LOCAL_PARENTS = ["http://localhost:3100", "http://127.0.0.1:3100"];
  var MAX_QUEUE = 8;
  var MAX_URL = 8192;
  var MAX_ID = 128;
  var MAX_TITLE = 240;
  var MAX_COORD = 10000000;
  // Bounded total of exact admitted paths (legacy + native). The real canonical
  // projection carries 13015 legacy + 14 native rows, so a 5000 cap rejected the
  // whole site. The bound is fixed and never grown at runtime.
  var MAX_CATALOG_PATHS = 50000;
  var SCROLL_INTERVAL_MS = 100;
  var CORRECTION_BUDGET_MS = 1200;
  var ID_RE = /^[A-Za-z0-9_:.-]+$/;
  var DEAD_SCHEME_RE = /^(javascript|data|blob|mailto|tel):/;
  var TRANSPORT_KEYS = ["mmx_shell", "mmx_generation"];
  var SECRET_KEYS = ["access_token", "refresh_token", "token_hash", "id_token", "code_verifier", "authorization"];
  var SENSITIVE_SEGS = ["auth", "login", "reset-password"];
  var THEMES = ["dark", "light"];
  var LOCALES = ["en", "zh"];
  var AUTH_INTENTS = ["signin", "signup", "settings", "billing"];
  var ERROR_CODES = ["initialization_failed", "unsupported_context", "navigation_unavailable", "authentication_navigation"];

  if (typeof window === "undefined" || typeof document === "undefined") return;
  var w = window;
  if (w.__MMX_SHARED_BRIDGE_INSTALLED__) return;
  var BAD = { bad: true };

  function isObj(v) { return v !== null && typeof v === "object" && !Array.isArray(v); }
  function own(v, k) { return Object.prototype.hasOwnProperty.call(v, k); }
  function strBounded(v, max) { return typeof v === "string" && v.length <= max; }
  function boundedStr(v, max) { return typeof v === "string" && v.length > 0 && v.length <= max; }
  function safeNonNegInt(v) { return Number.isSafeInteger(v) && v >= 0; }
  function coordOK(v) { return typeof v === "number" && Number.isFinite(v) && v >= 0 && v <= MAX_COORD; }
  function clampCoord(v) {
    if (typeof v !== "number" || !Number.isFinite(v)) return 0;
    if (v < 0) return 0;
    if (v > MAX_COORD) return MAX_COORD;
    return Math.round(v);
  }
  function validId(v) { return typeof v === "string" && v.length <= MAX_ID && ID_RE.test(v); }
  function exactKeys(obj, expected) {
    var keys = Object.keys(obj);
    if (keys.length !== expected.length) return false;
    for (var i = 0; i < keys.length; i++) { if (expected.indexOf(keys[i]) === -1) return false; }
    for (var j = 0; j < expected.length; j++) { if (!own(obj, expected[j])) return false; }
    return true;
  }
  function paramPairs(search, hash) {
    var out = [];
    function add(str) {
      if (!str) return;
      str = String(str);
      if (str.charAt(0) === "?") str = str.slice(1);
      var parts = str.split("&");
      for (var i = 0; i < parts.length; i++) {
        var p = parts[i];
        if (!p) continue;
        var eq = p.indexOf("=");
        var k = eq === -1 ? p : p.slice(0, eq);
        var v = eq === -1 ? "" : p.slice(eq + 1);
        out.push([decode(k), decode(v)]);
      }
    }
    function decode(s) { try { return decodeURIComponent(String(s).replace(/\+/g, " ")); } catch (e) { return String(s); } }
    add(search);
    var h = String(hash || "").replace(/^#/, "");
    if (h) {
      var hi = h.indexOf("?");
      if (hi !== -1) add(h.slice(hi + 1));
      else if (h.indexOf("=") !== -1) add(h);
    }
    return out;
  }
  function hasSensitiveSegment(pathname) {
    var segs = String(pathname || "").split("/");
    for (var i = 0; i < segs.length; i++) { if (SENSITIVE_SEGS.indexOf(segs[i]) !== -1) return true; }
    return false;
  }
  function isSensitiveURL(u) {
    try {
      var pairs = paramPairs(u.search, u.hash);
      var hasCode = false, hasOnboard = false;
      for (var i = 0; i < pairs.length; i++) {
        var k = pairs[i][0].toLowerCase(), v = pairs[i][1].toLowerCase();
        if (SECRET_KEYS.indexOf(k) !== -1) return true;
        if (k === "type" && (v === "recovery" || v === "signup")) return true;
        if (k === "code") hasCode = true;
        if (k === "onboard") hasOnboard = true;
      }
      if (hasCode && (hasSensitiveSegment(u.pathname) || hasOnboard)) return true;
      return false;
    } catch (e) { return true; }
  }

  /* ---- candidate boot guards ---- */
  if (w.parent === w) return;
  var search = "";
  try { search = String(w.location.search || ""); } catch (e) { return; }
  var sp;
  try { sp = new URLSearchParams(search); } catch (e) { return; }
  if (sp.get("mmx_shell") !== "1") return;
  var frameGeneration = sp.get("mmx_generation");
  if (!frameGeneration || frameGeneration.length === 0 || frameGeneration.length > MAX_ID) return;

  var childOrigin;
  try { childOrigin = new URL(w.location.href).origin; } catch (e) { return; }
  var allowedParents = APPROVED_PARENT_ORIGINS.slice();
  var host = "";
  try { host = w.location.hostname || ""; } catch (e) {}
  if ((host === "localhost" || host === "127.0.0.1") && childOrigin !== "https://www.mastermind-x.com") {
    allowedParents = allowedParents.concat(LOCAL_PARENTS);
  }
  var refOrigin = "";
  try { refOrigin = new URL(document.referrer).origin; } catch (e) {}
  if (allowedParents.indexOf(refOrigin) === -1) return;
  var parentOrigin = refOrigin;

  if (typeof w.MMXSharedShell !== "undefined" && (!w.MMXSharedShell || w.MMXSharedShell.__mmxBridge !== PROTOCOL)) return;

  var installed = true;
  w.__MMX_SHARED_BRIDGE_INSTALLED__ = true;

  var state = { active: false, chrome: false, anchors: false, runtime: false };
  var admitted = null;
  var appliedRevision = -1;
  var desiredTheme = null, desiredLocale = null;
  var themePendingSetter = false, localePendingSetter = false;
  var suppress = false;
  var preInitQueue = [];
  var navSeq = 0;
  var lastNavRequestId = null;
  var scrollTimer = null;
  var correctionTimers = [];
  var correctionCancelers = [];
  var docVersion = null;
  var responseKind = null;
  var restorePending = null;
  var anchorObserver = null;
  var origReplaceBound = null;
  var origPushBound = null;
  var nativePushRef = null, nativeReplaceRef = null;
  var projected = (typeof WeakMap === "function") ? new WeakMap() : null;
  var messageHandlerRef = null, pagehideHandlerRef = null;
  var userThemeHandlerRef = null, userLangHandlerRef = null;
  var uncontrolledNavHandlerRef = null, scrollHandlerRef = null, clickHandlerRef = null;
  var domReadyHandlerRef = null, domReadyWaiters = null, domReadyListener = null;
  var pendingInitialReady = false;
  var domReadyObserved = false;
  try { domReadyObserved = document.readyState === "complete"; } catch (e) {}
  var initialBootWindow = false;
  var initializedPath = null;
  var lastLocationNotified = null;
  var ENV_KEYS = ["protocol", "frameGeneration", "type"];
  var INIT_KEYS = ENV_KEYS.concat(["theme", "locale", "contextRevision", "canonicalPath", "catalog", "restore"]);
  var CONTEXT_KEYS = ENV_KEYS.concat(["theme", "locale", "contextRevision"]);

  function send(type, fields) {
    var msg = { protocol: PROTOCOL, frameGeneration: frameGeneration, type: type };
    if (fields) { var ks = Object.keys(fields); for (var i = 0; i < ks.length; i++) msg[ks[i]] = fields[ks[i]]; }
    try { w.parent.postMessage(msg, parentOrigin); } catch (e) {}
  }
  function emitError(code) {
    if (ERROR_CODES.indexOf(code) !== -1) send("ERROR", { code: code });
  }
  function currentUrl() { try { return new URL(w.location.href); } catch (e) { return null; } }
  function currentCanonical() {
    var u = currentUrl();
    if (!u || !credentialsFree(u) || isSensitiveURL(u)) return null;
    var c = canonicalHref(u);
    return c.length <= MAX_URL ? c : null;
  }

  /* ---- transport query handling (byte preserving) ----
   * URLSearchParams mutation reserializes the whole query (space -> "+", "," ->
   * "%2C", "%2c" -> "%2C", duplicate keys re-written). The canonical projection
   * has to keep every non-reserved byte exactly as the server and the parent
   * computed it, so the reserved pairs are filtered out of the RAW query and the
   * result is assigned to URL.search directly (never re-serialized). The
   * incoming location is already URL-normalized, so no further reserialization.
   */
  function filterTransport(search) {
    if (!search) return "";
    var raw = String(search);
    if (raw.charAt(0) === "?") raw = raw.slice(1);
    var parts = raw.split("&");
    var kept = [];
    for (var i = 0; i < parts.length; i++) {
      var part = parts[i];
      var eq = part.indexOf("=");
      var key = eq === -1 ? part : part.slice(0, eq);
      var reserved = false;
      try { reserved = TRANSPORT_KEYS.indexOf(decodeURIComponent(key.replace(/\+/g, " "))) !== -1; } catch (e) { reserved = false; }
      if (!reserved) kept.push(part);
    }
    return kept.length ? "?" + kept.join("&") : "";
  }
  function stripTransport(u) {
    try { u.search = filterTransport(u.search); } catch (e) {}
    return u;
  }
  function restoreTransport(u) {
    try {
      var kept = filterTransport(u.search);
      var raw = kept.slice(1);
      var reserved = "mmx_shell=1&mmx_generation=" + encodeURIComponent(frameGeneration);
      u.search = raw ? raw + "&" + reserved : "?" + reserved;
    } catch (e) {}
    return u;
  }
  function canonicalHref(u) { try { var c = new URL(u.href); stripTransport(c); return c.toString(); } catch (e) { return ""; } }
  function withTransport(u) { try { return restoreTransport(new URL(u.href)).toString(); } catch (e) { return null; } }
  function coerceHref(v) {
    if (typeof v === "string") return v;
    if (v && typeof v === "object" && typeof v.href === "string") return v.href;
    return null;
  }
  function resolveHref(h, base) {
    try { return new URL(String(h), base || w.location.href); } catch (e) { return null; }
  }
  function credentialsFree(u) { try { return !u.username && !u.password; } catch (e) { return false; } }
  function isAdmitted(p) { return !!admitted && own(admitted, p) && admitted[p] === true; }
  // An already-projected first-party href (equal to the parent origin) stands for
  // this child document, so it maps back to the child path for classification.
  // Only the exact admitted parent origin qualifies; other origins stay external.
  function firstPartyToChild(u) {
    if (!u || u.origin !== parentOrigin || u.origin === childOrigin) return null;
    if (!credentialsFree(u)) return null;
    try {
      var mapped = new URL(String(u.pathname) + String(u.search) + String(u.hash), childOrigin);
      return mapped.origin === childOrigin && credentialsFree(mapped) ? mapped : null;
    } catch (e) { return null; }
  }

  /* ---- queue ---- */
  function enqueue(item) {
    if (preInitQueue.length >= MAX_QUEUE) return false;
    preInitQueue.push(item);
    return true;
  }
  function dropQueue() { preInitQueue.length = 0; }
  function drainQueue() {
    var q = preInitQueue;
    preInitQueue = [];
    for (var i = 0; i < q.length; i++) {
      var item = q[i];
      if (item.kind === "nav") performNavigate(item.href, item.mode);
      else if (item.kind === "history") handleQueuedHistory(item);
      else if (item.kind === "auth") send("AUTH_REQUEST", { intent: item.intent });
      else if (item.kind === "error") emitError(item.code);
    }
  }

  function flushView() {
    if (scrollTimer !== null) {
      try { clearTimeout(scrollTimer); } catch (e) {}
      scrollTimer = null;
    }
    sendViewState();
  }
  function sendViewState() {
    if (!state.active) return;
    var view = { x: clampCoord(w.scrollX), y: clampCoord(w.scrollY) };
    var id = currentFocusId();
    if (id !== null) view.focusId = id;
    send("VIEW_STATE", { view: view });
  }
  function currentFocusId() {
    try {
      var ae = document.activeElement;
      if (!ae || typeof ae !== "object") return null;
      if (ae === document.body || ae === document.documentElement) return null;
      var s = ae.id;
      return validId(s) ? s : null;
    } catch (e) { return null; }
  }
  function emitNavigate(canonical, mode, sameDocument, viewCaptured) {
    // The parent must see the view the user is leaving *before* anything about the
    // child location, scroll or focus changes. viewCaptured=true means the caller
    // already flushed it and only then mutated the child document.
    if (viewCaptured !== true) flushView();
    navSeq += 1;
    lastNavRequestId = "req-" + navSeq;
    send("NAVIGATE", { href: canonical, mode: mode, sameDocument: sameDocument === true, requestId: lastNavRequestId });
  }

  function stripHash(s) { var i = s.indexOf("#"); return i === -1 ? s : s.slice(0, i); }
  function fragmentOf(canonical) {
    var base = stripHash(canonical);
    var f = canonical.length > base.length ? canonical.slice(base.length + 1) : "";
    return f === "" ? null : f;
  }
  function isFragmentAgainst(canonical, curCanonical) {
    if (typeof canonical !== "string" || typeof curCanonical !== "string") return false;
    var fid = fragmentOf(canonical);
    return fid !== null && stripHash(canonical) === stripHash(curCanonical);
  }
  function scrollFragmentTarget(fid) {
    if (!fid) return;
    try {
      var el = document.getElementById(decodeURIComponent(fid));
      if (el && typeof el.scrollIntoView === "function") el.scrollIntoView({ block: "start" });
    } catch (e) {}
  }
  function hstate() { try { return w.history ? w.history.state : null; } catch (e) { return null; } }
  /* Same-document fragment change. The child only ever replaces its own entry, so a
   * fragment never becomes a child history entry the parent cannot see; the parent
   * receives its intended mode so Back can return from the fragment. Clicking the
   * already-current fragment scrolls but never fabricates a new parent entry. */
  function applyFragmentNavigation(u, canonical, curCanonical, mode) {
    var fid = fragmentOf(canonical);
    if (canonical === curCanonical) { scrollFragmentTarget(fid); return false; }
    flushView();
    origReplaceSafe(hstate(), "", withTransport(u));
    scrollFragmentTarget(fid);
    emitNavigate(canonical, mode, true, true);
    return true;
  }

  function performNavigate(u, mode) {
    if (isSensitiveURL(u)) { emitError("authentication_navigation"); return false; }
    var canonical = canonicalHref(u);
    if (!canonical || canonical.length > MAX_URL) { emitError("navigation_unavailable"); return false; }
    if (!isAdmitted(u.pathname)) { emitError("navigation_unavailable"); return false; }
    var cur = currentCanonical();
    if (cur !== null && isFragmentAgainst(canonical, cur)) { applyFragmentNavigation(u, canonical, cur, mode); return true; }
    emitNavigate(canonical, mode, cur !== null && cur === canonical);
    return true;
  }

  function handleQueuedHistory(item) {
    var u = item.href;
    if (isSensitiveURL(u)) { emitError("authentication_navigation"); return; }
    var canonical = canonicalHref(u);
    if (!canonical || canonical.length > MAX_URL || !isAdmitted(u.pathname)) { emitError("navigation_unavailable"); return; }
    emitNavigate(canonical, item.mode, item.sameDocument === true);
  }

  /* ---- history capture (candidate boot, before page scripts) ---- */
  function handleHistoryCall(mode, state_, title, url) {
    if (url === undefined || url === null) {
      origReplaceSafe(state_, title, undefined);
      return;
    }
    var hs = coerceHref(url);
    if (hs === null) return;
    var u = resolveHref(hs);
    if (!u || u.origin !== childOrigin || !credentialsFree(u)) return;
    if (isSensitiveURL(u)) {
      if (state.active) emitError("authentication_navigation");
      else enqueue({ kind: "error", code: "authentication_navigation" });
      return;
    }
    var current = currentUrl();
    var sameDocument = !!current && u.pathname === current.pathname;
    if (!state.active) {
      // Only mutate a same-document location after its parent notification is queued.
      if (enqueue({ kind: "history", mode: mode, href: u, sameDocument: sameDocument }) && sameDocument)
        origReplaceSafe(state_, title, withTransport(u));
      return;
    }
    var canonical = canonicalHref(u);
    if (!canonical || canonical.length > MAX_URL || !isAdmitted(u.pathname)) {
      emitError("navigation_unavailable");
      return;
    }
    // A different pathname belongs to another document; the parent replaces it.
    if (!sameDocument) { emitNavigate(canonical, mode, false); return; }
    flushView();
    origReplaceSafe(state_, title, withTransport(u));
    emitNavigate(canonical, mode, true, true);
  }
  function origReplaceSafe(state_, title, url) {
    try { if (origReplaceBound) origReplaceBound(state_, title === undefined ? "" : title, url); } catch (e) {}
  }
  function wrapHistory() {
    var h = w.history;
    if (!h || typeof h.pushState !== "function" || typeof h.replaceState !== "function") return;
    nativePushRef = h.pushState;
    nativeReplaceRef = h.replaceState;
    try { origPushBound = nativePushRef.bind(h); } catch (e) { origPushBound = null; }
    try { origReplaceBound = nativeReplaceRef.bind(h); } catch (e) { origReplaceBound = null; }
    try {
      h.pushState = function (state_, title, url) { return handleHistoryCall("push", state_, title, url); };
      h.replaceState = function (state_, title, url) { return handleHistoryCall("replace", state_, title, url); };
    } catch (e) {}
  }
  function unwrapHistory() {
    try {
      if (w.history) {
        if (nativePushRef) w.history.pushState = nativePushRef;
        if (nativeReplaceRef) w.history.replaceState = nativeReplaceRef;
      }
    } catch (e) {}
  }

  /* ---- anchors ----
   * Projection and interception are separate decisions:
   *  - skipIntercept: a normal new-tab (_blank), download or role=button click keeps
   *    native semantics; the bridge never fabricates a parent entry for it.
   *  - skipProjection: an anchor keeps its authored href only when a native default
   *    activation could load the child frame with a parent-origin href (download, or
   *    a role=button link that is not already first-party). Every other target is
   *    projected: no target and _blank as before, and now explicit _self, _parent or
   *    a named frame too, because the bridge owns that default activation and always
   *    prevents it. A copied, middle/ctrl-clicked or open-in-new-tab destination then
   *    stays on the beta shell instead of leaking the legacy origin, while external
   *    and download anchors keep native handling and the recorded projection makes
   *    re-observation a no-op (no MutationObserver feedback).
   */
  function anchorTarget(a) { try { return String(a.getAttribute("target") || "").toLowerCase(); } catch (e) { return ""; } }
  function authoredParentHref(a) {
    var hs = null;
    try { hs = a.getAttribute("href"); } catch (e) { return false; }
    if (typeof hs !== "string" || hs === "") return false;
    var u = resolveHref(hs);
    return !!u && u.origin === parentOrigin && u.origin !== childOrigin;
  }
  function skipIntercept(a) {
    if (!a || typeof a !== "object" || typeof a.getAttribute !== "function") return true;
    if (String(a.tagName || "").toUpperCase() !== "A") return true;
    if (a.hasAttribute && a.hasAttribute("download")) return true;
    if (anchorTarget(a) === "_blank") return true;
    if (String(a.getAttribute("role") || "").toLowerCase() === "button") {
      // Unless the authored href is already a projected first-party page: that must
      // never load inside the child frame.
      return !authoredParentHref(a);
    }
    return false;
  }
  function skipProjection(a) {
    if (!a || typeof a !== "object" || typeof a.getAttribute !== "function") return true;
    if (String(a.tagName || "").toUpperCase() !== "A") return true;
    if (a.hasAttribute && a.hasAttribute("download")) return true;
    if (anchorTarget(a) === "_blank") return false;  // new tab wants the beta href
    if (String(a.getAttribute("role") || "").toLowerCase() === "button") {
      // An authored first-party href is already the projected destination and is
      // intercepted; a child-href button keeps native semantics and stays unprojected.
      return !authoredParentHref(a);
    }
    // No target, _self, _parent or a named frame: the click handler owns the default
    // activation and prevents it, so the projected first-party href is safe. The
    // authored target itself is never rewritten.
    return false;
  }
  function addNoopener(a) {
    var tokens;
    try { tokens = String(a.getAttribute("rel") || "").split(/\s+/); } catch (e) { return; }
    var kept = [];
    for (var i = 0; i < tokens.length; i++) { if (tokens[i] !== "") kept.push(tokens[i]); }
    for (var j = 0; j < kept.length; j++) { if (kept[j].toLowerCase() === "noopener") return; }
    kept.push("noopener");
    try { a.setAttribute("rel", kept.join(" ")); } catch (e) {}
  }
  function projectAnchor(a) {
    if (!projected || skipProjection(a) || !state.active) return;
    var current;
    try { current = a.getAttribute("href"); } catch (e) { return; }
    if (typeof current !== "string" || current === "") return;
    var rec = projected.get(a);
    if (rec && current === rec.projected) return;
    var low = current.trim().toLowerCase();
    if (DEAD_SCHEME_RE.test(low)) return;
    var u = resolveHref(current);
    if (!u || !credentialsFree(u)) return;
    if (u.origin !== childOrigin) {
      var mapped = firstPartyToChild(u);
      if (mapped) {
        u = mapped;  // explicit first-party target: admitted as an internal link
      } else if (u.protocol === "http:" || u.protocol === "https:") {
        try { if (anchorTarget(a) === "") a.setAttribute("target", "_blank"); } catch (e) {}
        addNoopener(a);
        return;
      } else return;
    }
    if (isSensitiveURL(u) || !isAdmitted(u.pathname)) return;
    var canonical = canonicalHref(u);
    if (!canonical || canonical.length > MAX_URL || canonical.indexOf(childOrigin) !== 0) return;
    var projectedHref = parentOrigin + canonical.slice(childOrigin.length);
    try {
      a.setAttribute("href", projectedHref);
      projected.set(a, { original: current, projected: projectedHref });
    } catch (e) {}
  }
  function preventDefault(e) { try { if (typeof e.preventDefault === "function") e.preventDefault(); } catch (err) {} }
  function onClick(e) {
    try {
      if (!state.active || !e || e.defaultPrevented) return;
      if (typeof e.button === "number" && e.button !== 0) return;
      if (e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
      var node = e.target;
      if (!node || typeof node !== "object") return;
      if (node.nodeType !== undefined && node.nodeType !== 1) node = node.parentElement;
      if (!node || typeof node.closest !== "function") return;
      var a = node.closest("a[href]");
      if (!a || skipIntercept(a)) return;
      var attr = null;
      try { attr = a.getAttribute("href"); } catch (err) { return; }
      var rec = projected ? projected.get(a) : null;
      // Use the recorded authored value only while the attribute is still exactly what
      // the bridge projected. An unregistered rewrite is reclassified from the current
      // value, so a stale destination is never navigated to.
      var raw = (rec && attr === rec.projected) ? rec.original : attr;
      var hs = coerceHref(raw);
      if (hs === null) return;
      var low = hs.trim().toLowerCase();
      if (DEAD_SCHEME_RE.test(low)) return;
      var u = resolveHref(hs);
      if (!u) return;
      if (u.origin !== childOrigin) {
        var mapped = firstPartyToChild(u);
        if (mapped) {
          u = mapped;  // first-party target classified against the child catalog
        } else {
          if (u.protocol === "http:" || u.protocol === "https:") {
            try {
              if (anchorTarget(a) === "") a.setAttribute("target", "_blank");
            } catch (err) {}
            addNoopener(a);
          }
          return;
        }
      }
      if (!credentialsFree(u)) { preventDefault(e); emitError("navigation_unavailable"); return; }
      if (isSensitiveURL(u)) { preventDefault(e); emitError("authentication_navigation"); return; }
      var canonical = canonicalHref(u);
      var curC = currentCanonical();
      if (!canonical || canonical.length > MAX_URL || !isAdmitted(u.pathname) || curC === null) {
        preventDefault(e);
        emitError("navigation_unavailable");
        return;
      }
      preventDefault(e);
      if (isFragmentAgainst(canonical, curC)) { applyFragmentNavigation(u, canonical, curC, "push"); return; }
      emitNavigate(canonical, "push", canonical === curC);
    } catch (err) {}
  }
  function installAnchors() {
    if (state.anchors) return;
    state.anchors = true;
    clickHandlerRef = onClick;
    try { document.addEventListener("click", clickHandlerRef, false); } catch (e) {}
    if (typeof MutationObserver !== "function" || !document.documentElement) return;
    try {
      anchorObserver = new MutationObserver(function (muts) {
        if (!state.active) return;
        for (var i = 0; i < muts.length; i++) {
          var m = muts[i];
          if (!m) continue;
          if (m.type === "attributes") {
            if (m.target && String(m.target.tagName || "").toUpperCase() === "A") projectAnchor(m.target);
          } else if (m.addedNodes && typeof m.addedNodes.length === "number") {
            for (var j = 0; j < m.addedNodes.length; j++) {
              var n = m.addedNodes[j];
              if (!n || n.nodeType !== 1 || typeof n.querySelectorAll !== "function") continue;
              if (String(n.tagName || "").toUpperCase() === "A") projectAnchor(n);
              var subs = n.querySelectorAll("a[href]");
              if (subs && typeof subs.length === "number") {
                var cap = subs.length < 500 ? subs.length : 500;
                for (var k = 0; k < cap; k++) projectAnchor(subs[k]);
              }
            }
          }
        }
      });
      anchorObserver.observe(document.documentElement, { childList: true, subtree: true, attributes: true, attributeFilter: ["href"] });
    } catch (e) {}
    try {
      var all = document.querySelectorAll("a[href]");
      for (var q = 0; q < all.length; q++) projectAnchor(all[q]);
    } catch (e) {}
  }

  /* ---- context application ----
   * The incumbent page owns the theme/locale setters (they repaint charts and
   * strings), so they must run even when the attribute already happens to equal
   * the request. A setter that throws is a real failure and is surfaced instead of
   * being swallowed on the way to an "usable readiness" acknowledgment.
   *
   * Locale convention: the incumbent setLang("zh") writes data-lang="zh" AND
   * html lang="zh-CN" (WCAG 3.1.1), so the wire locale is read back with a valid
   * data-lang preferred and a region-qualified html.lang as the fallback. The
   * closed wire vocabulary stays exactly en / zh on INIT, CONTEXT and
   * CONTEXT_REQUEST; no new locale is ever invented on the wire.
   */
  function langAttrFor(locale) { return locale === "zh" ? "zh-CN" : "en"; }
  function normalizeLocale(raw) {
    if (typeof raw !== "string") return null;
    var v = raw.trim().toLowerCase();
    if (v === "en" || v.indexOf("en-") === 0) return "en";
    if (v === "zh" || v.indexOf("zh-") === 0) return "zh";
    return null;
  }
  function readIncumbentLocale() {
    var de = null;
    try { de = document.documentElement; } catch (e) { return null; }
    if (!de || typeof de.getAttribute !== "function") return null;
    var raw = null;
    try { raw = de.getAttribute("data-lang"); } catch (e) { return null; }
    var norm = normalizeLocale(raw);
    if (norm !== null) return norm;              // incumbent semantic key wins
    try { raw = de.getAttribute("lang"); } catch (e) { return null; }
    return normalizeLocale(raw);                 // html lang fallback: zh-CN / en-US
  }
  function applyContext(theme, locale, revision) {
    var failure = false;
    suppress = true;
    try {
      var de = document.documentElement;
      if (theme) {
        desiredTheme = theme;
        try {
          if (de && typeof de.getAttribute === "function" && de.getAttribute("data-theme") !== theme &&
              typeof de.setAttribute === "function") de.setAttribute("data-theme", theme);
        } catch (e) {}
        if (typeof w.setTheme === "function") {
          themePendingSetter = false;
          try { w.setTheme(theme); } catch (e) { failure = true; }
        } else themePendingSetter = true;
      }
      if (locale) {
        desiredLocale = locale;
        // Write the incumbent attribute pair itself: a page with no setter yet is
        // still presented correctly and a setter that only repaints can never leave
        // the semantic data-lang key behind.
        try {
          if (de && typeof de.getAttribute === "function" && typeof de.setAttribute === "function") {
            if (de.getAttribute("data-lang") !== locale) de.setAttribute("data-lang", locale);
            if (de.getAttribute("lang") !== langAttrFor(locale)) de.setAttribute("lang", langAttrFor(locale));
          }
        } catch (e) {}
        if (typeof w.setLang === "function") {
          localePendingSetter = false;
          try { w.setLang(locale); } catch (e) { failure = true; }
        } else localePendingSetter = true;
      }
    } finally { suppress = false; }
    if (failure) return false;
    appliedRevision = revision;
    return true;
  }
  // Initial readiness. Between the head INIT and DOMContentLoaded the legacy boot may
  // rewrite theme/locale: those are not interactive user choices, and a setter that
  // was missing at INIT may exist now. The parent context owns presentation, so the
  // latest desired values (a newer CONTEXT received during loading is already the
  // desired state) are reapplied unconditionally through the real setters and
  // attributes with suppression, then proved, before any READY is claimed.
  function reapplyDesiredContext() {
    return applyContext(desiredTheme, desiredLocale, appliedRevision);
  }
  function proofAppliedContext() {
    var de = null;
    try { de = document.documentElement; } catch (e) { return false; }
    if (!de || typeof de.getAttribute !== "function") return false;
    if (desiredTheme) {
      var shown = null;
      try { shown = de.getAttribute("data-theme"); } catch (e) { return false; }
      if (shown !== desiredTheme) return false;
    }
    if (desiredLocale) {
      try {
        if (de.getAttribute("data-lang") !== desiredLocale ||
            normalizeLocale(de.getAttribute("lang")) !== desiredLocale) return false;
      } catch (e) { return false; }
    }
    return true;
  }
  function finalizeInitialReadiness() {
    if ((initialBootWindow || !proofAppliedContext()) && !reapplyDesiredContext()) return false;
    return proofAppliedContext();
  }
  function onUserThemeChange() {
    // While initial readiness is pending the document is still booting: a theme
    // mutation is legacy initialization, not a user choice, and the parent context
    // is authoritative at DOM ready.
    if (!state.active || suppress || pendingInitialReady) return;
    var v = null;
    try { v = document.documentElement.getAttribute("data-theme"); } catch (e) {}
    if (THEMES.indexOf(v) !== -1) send("CONTEXT_REQUEST", { theme: v });
  }
  function onUserLangChange() {
    if (!state.active || suppress || pendingInitialReady) return;
    var v = readIncumbentLocale();  // data-lang first, html lang (zh-CN) as fallback
    if (v !== null) send("CONTEXT_REQUEST", { locale: v });
  }

  /* ---- chrome suppression ---- */
  function proofChromeSuppression() {
    // The static sheet precedes this blocking script. Computed style also proves a
    // sheet that loaded before our listeners, and rejects a missing/gated/CSP-blocked
    // response. The marker is inert until the trusted INIT sets the root attribute.
    try {
      var de = document.documentElement;
      return !!de && de.getAttribute("data-mmx-shared-shell") === "1" &&
        typeof w.getComputedStyle === "function" &&
        w.getComputedStyle(de).getPropertyValue("--mmx-shared-shell-css-ready").trim() === "1";
    } catch (e) { return false; }
  }
  function applyChromeSuppression() {
    if (state.chrome) return proofChromeSuppression();
    var de = document.documentElement;
    if (!de || typeof de.setAttribute !== "function") return false;
    try { de.setAttribute("data-mmx-shared-shell", "1"); } catch (e) { return false; }
    if (!proofChromeSuppression()) {
      try { de.removeAttribute("data-mmx-shared-shell"); } catch (e) {}
      return false;
    }
    state.chrome = true;
    return true;
  }

  /* ---- ready + restoration ---- */
  function readDocumentVersion() {
    try {
      var meta = document.querySelector('meta[name="' + DOCUMENT_META_NAME + '"]');
      if (!meta || typeof meta.getAttribute !== "function") return null;
      var c = meta.getAttribute("content");
      if (typeof c !== "string" || c.length === 0 || c.length > MAX_ID) return null;
      return c;
    } catch (e) { return null; }
  }
  function readResponseKind() {
    try {
      var meta = document.querySelector('meta[name="' + RESPONSE_META_NAME + '"]');
      var kind = meta && meta.getAttribute("content");
      return kind === "content" || kind === "coming_soon" ? kind : null;
    } catch (e) { return null; }
  }
  // withRestore=false acknowledges an applied context: never re-runs the initial
  // scroll/focus restoration and therefore never steals focus from the user.
  function sendReady(withRestore) {
    if (!proofChromeSuppression()) { emitError("initialization_failed"); return; }
    if (!proofAppliedContext()) {
      emitError(withRestore === true ? "initialization_failed" : "unsupported_context");
      return;
    }
    var href = currentCanonical();
    if (!href || !boundedStr(docVersion, MAX_ID)) { emitError("initialization_failed"); return; }
    send("READY", {
      title: String(document.title || "").slice(0, MAX_TITLE),
      href: href,
      contextRevision: appliedRevision,
      bridgeVersion: BRIDGE_VERSION,
      documentVersion: docVersion,
      responseKind: responseKind
    });
    if (withRestore === true) {
      applyRestore(restorePending);
      restorePending = null;
    }
  }
  function whenDocumentReady(fn) {
    // interactive means parsing ended; deferred and module boot scripts may still run.
    // The blocking head bridge observes the event itself, including before a late INIT.
    if (!domReadyObserved) {
      try { domReadyObserved = document.readyState === "complete"; } catch (e) {}
    }
    if (domReadyObserved) { try { fn(); } catch (e) { emitError("initialization_failed"); } return; }
    // One DOMContentLoaded listener regardless of how many acknowledgments queue.
    if (!domReadyWaiters) domReadyWaiters = [];
    domReadyWaiters.push(fn);
    if (domReadyListener) return;
    var listener = function () {
      domReadyObserved = true;
      var list = domReadyWaiters || [];
      domReadyWaiters = null;
      domReadyListener = null;
      domReadyHandlerRef = null;
      try { document.removeEventListener("DOMContentLoaded", listener, false); } catch (e) {}
      for (var i = 0; i < list.length; i++) { try { list[i](); } catch (e) { emitError("initialization_failed"); } }
    };
    domReadyListener = listener;
    domReadyHandlerRef = listener;
    try { document.addEventListener("DOMContentLoaded", domReadyHandlerRef, false); } catch (e) {}
  }
  // The parent may publish a newer context while the initial READY is still in
  // flight. It must get a READY carrying the revision it actually applied.
  function acknowledgeContext() {
    if (pendingInitialReady) return;  // queued initial READY already carries the newer revision
    whenDocumentReady(function () { sendReady(false); });
  }
  function applyRestore(restore) {
    try {
      if (restore) {
        if (typeof w.scrollTo === "function") { try { w.scrollTo(restore.x, restore.y); } catch (e) {} }
        if (restore.focusId) {
          var el = document.getElementById(restore.focusId);
          if (el && typeof el.focus === "function") { try { el.focus({ preventScroll: true }); } catch (e) {} }
        }
        scheduleCorrection(restore.x, restore.y);
      } else {
        focusPrimary();
      }
    } catch (e) {}
  }
  function focusPrimary() {
    try {
      var ae = document.activeElement;
      if (ae && ae !== document.body && ae !== document.documentElement) return;
      var el = document.querySelector('main,[role="main"],h1');
      if (!el || typeof el.focus !== "function") return;
      var had = el.getAttribute("tabindex");
      el.setAttribute("tabindex", "-1");
      el.focus({ preventScroll: true });
      if (had === null) el.removeAttribute("tabindex");
      else el.setAttribute("tabindex", had);
    } catch (e) {}
  }
  function scheduleCorrection(x, y) {
    function cancel() {
      for (var i = 0; i < correctionTimers.length; i++) { try { clearTimeout(correctionTimers[i]); } catch (e) {} }
      correctionTimers.length = 0;
      for (var j = 0; j < correctionCancelers.length; j++) {
        var c = correctionCancelers[j];
        try { document.removeEventListener(c[0], c[1], true); } catch (e) {}
      }
      correctionCancelers.length = 0;
    }
    function apply() { try { if (typeof w.scrollTo === "function") w.scrollTo(x, y); } catch (e) {} }
    var names = ["wheel", "pointerdown", "keydown"];
    for (var i = 0; i < names.length; i++) {
      try {
        (function (name) {
          var fn = function () { cancel(); };
          correctionCancelers.push([name, fn]);
          document.addEventListener(name, fn, true);
        })(names[i]);
      } catch (e) {}
    }
    var now = Date.now();
    var t1 = now + 250, t2 = now + 900;
    if (t1 - now < CORRECTION_BUDGET_MS) { try { correctionTimers.push(setTimeout(function () { correctionTimers = []; apply(); correctionTimers.push(setTimeout(function () { correctionTimers = []; apply(); cancel(); }, 650)); }, 250)); } catch (e) {} }
    else if (t2 - now < CORRECTION_BUDGET_MS) { try { correctionTimers.push(setTimeout(function () { correctionTimers = []; apply(); cancel(); }, 900)); } catch (e) {} }
  }

  /* ---- inbound message handling ---- */
  function validateCatalog(c) {
    if (!isObj(c) || !exactKeys(c, ["legacyPaths", "nativePaths"])) return null;
    if (!Array.isArray(c.legacyPaths) || !Array.isArray(c.nativePaths)) return null;
    if (c.legacyPaths.length + c.nativePaths.length > MAX_CATALOG_PATHS) return null;
    var out = Object.create(null);
    var count = 0;
    var lists = [c.legacyPaths, c.nativePaths];
    for (var li = 0; li < lists.length; li++) {
      var list = lists[li];
      for (var i = 0; i < list.length; i++) {
        var p = list[i];
        if (typeof p !== "string" || p.length === 0 || p.length > MAX_URL) return null;
        if (p.charAt(0) !== "/" || p.indexOf("//") === 0) return null;
        if (p.indexOf("?") !== -1 || p.indexOf("#") !== -1 || p.indexOf("\\") !== -1 || p.indexOf("://") !== -1) return null;
        if (/[\x00-\x1f\x7f\s]/.test(p)) return null;
        // One shared map: a repeat within a list and a legacy/native collision are
        // both refused, and admission is always by exact path, never by prefix.
        if (own(out, p)) return null;
        out[p] = true;
        count += 1;
        if (count > MAX_CATALOG_PATHS) return null;
      }
    }
    return out;
  }
  function validateRestoreInbound(v) {
    if (v === null) return null;
    if (!isObj(v)) return BAD;
    var keys = Object.keys(v);
    for (var i = 0; i < keys.length; i++) { if (["x", "y", "focusId"].indexOf(keys[i]) === -1) return BAD; }
    if (!coordOK(v.x) || !coordOK(v.y)) return BAD;
    var out = { x: v.x, y: v.y };
    if (own(v, "focusId")) {
      if (!validId(v.focusId)) return BAD;
      out.focusId = v.focusId;
    }
    return out;
  }

  function handleInit(data) {
    if (!exactKeys(data, INIT_KEYS)) return;
    if (THEMES.indexOf(data.theme) === -1) return;
    if (LOCALES.indexOf(data.locale) === -1) return;
    if (!safeNonNegInt(data.contextRevision)) return;
    if (!strBounded(data.canonicalPath, MAX_URL)) return;
    var catalog = validateCatalog(data.catalog);
    if (!catalog) return;
    var restore = validateRestoreInbound(data.restore);
    if (restore === BAD) return;

    if (state.active) {
      // Repeated trusted INIT for the live generation: idempotent. No new observers,
      // no queue replay, no second restoration, and only the same requested canonical
      // path is acknowledged.
      if (initializedPath === null || data.canonicalPath !== initializedPath) return;
      if (!applyContext(data.theme, data.locale, data.contextRevision)) { emitError("unsupported_context"); return; }
      acknowledgeContext();
      return;
    }

    docVersion = readDocumentVersion();
    responseKind = readResponseKind();
    if (docVersion === null || responseKind === null) { dropQueue(); emitError("initialization_failed"); return; }
    // A head INIT lands while legacy boot scripts still run, so this document has a
    // boot window whose late presentation writes must be overridden at DOM ready.
    var bootWindow = !domReadyObserved;
    if (!applyContext(data.theme, data.locale, data.contextRevision)) {
      dropQueue();
      emitError("initialization_failed");
      return;
    }
    if (!applyChromeSuppression()) { dropQueue(); emitError("initialization_failed"); return; }
    admitted = catalog;
    initializedPath = data.canonicalPath;
    lastLocationNotified = currentCanonical();
    restorePending = restore;
    initialBootWindow = bootWindow;
    pendingInitialReady = true;
    state.active = true;
    installAnchors();
    installRuntime();
    drainQueue();
    whenDocumentReady(function () {
      // One restoration attempt, proved before readiness is claimed. A setter that
      // throws or leaves the presentation wrong is an explicit initialization failure
      // and never a false READY.
      var ok = finalizeInitialReadiness();
      pendingInitialReady = false;
      initialBootWindow = false;
      if (!ok) {
        dropQueue();
        emitError("initialization_failed");
        return;
      }
      sendReady(true);
    });
  }
  function handleContext(data) {
    if (!state.active) return;  // INIT owns the first context
    var keys = Object.keys(data);
    for (var i = 0; i < keys.length; i++) { if (CONTEXT_KEYS.indexOf(keys[i]) === -1) return; }
    if (!safeNonNegInt(data.contextRevision)) return;
    if (data.contextRevision <= appliedRevision) return;  // stale: never falsely acknowledged
    var hasTheme = own(data, "theme"), hasLocale = own(data, "locale");
    if (!hasTheme && !hasLocale) return;
    if (hasTheme && THEMES.indexOf(data.theme) === -1) { emitError("unsupported_context"); return; }
    if (hasLocale && LOCALES.indexOf(data.locale) === -1) { emitError("unsupported_context"); return; }
    if (!applyContext(hasTheme ? data.theme : null, hasLocale ? data.locale : null, data.contextRevision)) {
      emitError("unsupported_context");
      return;
    }
    acknowledgeContext();
  }
  function handleLocationAccepted(data) {
    if (!exactKeys(data, ENV_KEYS.concat(["requestId", "canonicalPath"]))) return;
    if (!boundedStr(data.requestId, MAX_ID) || !strBounded(data.canonicalPath, MAX_URL)) return;
    if (lastNavRequestId === null || data.requestId !== lastNavRequestId) return;
    var accepted = resolveHref(data.canonicalPath, childOrigin + "/");
    if (!accepted || accepted.origin !== childOrigin || !credentialsFree(accepted) || isSensitiveURL(accepted)) return;
    var canonical = canonicalHref(accepted);
    if (canonical !== currentCanonical()) return;
    lastNavRequestId = null;
    // The parent owns URL acceptance. Notify the actual legacy window only after
    // that acknowledgment, without inventing a native hashchange. A subscriber
    // may replaceState the current hash; that same-value ACK must not recurse.
    if (canonical === lastLocationNotified) return;
    lastLocationNotified = canonical;
    try {
      var evt = null;
      if (typeof CustomEvent === "function") evt = new CustomEvent("mmx:shell-location");
      else if (typeof document.createEvent === "function") {
        evt = document.createEvent("Event");
        evt.initEvent("mmx:shell-location", false, false);
      }
      if (evt && typeof w.dispatchEvent === "function") w.dispatchEvent(evt);
    } catch (e) {}
  }
  function handleVisibility(data) {
    if (!exactKeys(data, ENV_KEYS.concat(["visible"]))) return;
    if (typeof data.visible !== "boolean") return;
    try {
      var evt;
      if (typeof CustomEvent === "function") evt = new CustomEvent("mmx:shell-visibility", { detail: { visible: data.visible } });
      else if (typeof document.createEvent === "function") {
        evt = document.createEvent("CustomEvent");
        evt.initCustomEvent("mmx:shell-visibility", false, false, { visible: data.visible });
      }
      if (evt) document.dispatchEvent(evt);
    } catch (e) {}
  }
  function onMessage(event) {
    try {
      if (!event || event.origin !== parentOrigin) return;
      if (event.source !== w.parent) return;
      var data = event.data;
      if (!isObj(data)) return;
      if (data.protocol !== PROTOCOL || data.frameGeneration !== frameGeneration) return;
      var type = data.type;
      if (typeof type !== "string") return;
      if (type === "INIT") { handleInit(data); return; }
      if (!state.active) return;  // pre-INIT: only INIT is actionable
      if (type === "CONTEXT") handleContext(data);
      else if (type === "LOCATION_ACCEPTED") handleLocationAccepted(data);
      else if (type === "VISIBILITY") handleVisibility(data);
    } catch (e) {}
  }

  function onScroll() {
    if (!state.active || scrollTimer !== null) return;
    try { scrollTimer = setTimeout(function () { scrollTimer = null; sendViewState(); }, SCROLL_INTERVAL_MS); } catch (e) {}
  }
  function onUncontrolledNav() {
    if (state.active) emitError("navigation_unavailable");
  }
  function installRuntime() {
    if (state.runtime) return;
    state.runtime = true;
    scrollHandlerRef = onScroll;
    uncontrolledNavHandlerRef = onUncontrolledNav;
    userThemeHandlerRef = onUserThemeChange;
    userLangHandlerRef = onUserLangChange;
    try { w.addEventListener("scroll", scrollHandlerRef, false); } catch (e) {}
    try { w.addEventListener("hashchange", uncontrolledNavHandlerRef, false); } catch (e) {}
    try { w.addEventListener("popstate", uncontrolledNavHandlerRef, false); } catch (e) {}
    try { document.addEventListener("themechange", userThemeHandlerRef, false); } catch (e) {}
    try { document.addEventListener("langchange", userLangHandlerRef, false); } catch (e) {}
  }

  function cleanup() {
    try { if (messageHandlerRef) w.removeEventListener("message", messageHandlerRef, false); } catch (e) {}
    try { if (scrollHandlerRef) w.removeEventListener("scroll", scrollHandlerRef, false); } catch (e) {}
    try { if (uncontrolledNavHandlerRef) { w.removeEventListener("hashchange", uncontrolledNavHandlerRef, false); w.removeEventListener("popstate", uncontrolledNavHandlerRef, false); } } catch (e) {}
    try {
      if (userThemeHandlerRef) document.removeEventListener("themechange", userThemeHandlerRef, false);
      if (userLangHandlerRef) document.removeEventListener("langchange", userLangHandlerRef, false);
      if (clickHandlerRef) document.removeEventListener("click", clickHandlerRef, false);
      if (domReadyHandlerRef) document.removeEventListener("DOMContentLoaded", domReadyHandlerRef, false);
    } catch (e) {}
    try { if (scrollTimer !== null) { clearTimeout(scrollTimer); scrollTimer = null; } } catch (e) {}
    try { for (var i = 0; i < correctionTimers.length; i++) clearTimeout(correctionTimers[i]); correctionTimers.length = 0; } catch (e) {}
    try {
      for (var j = 0; j < correctionCancelers.length; j++) document.removeEventListener(correctionCancelers[j][0], correctionCancelers[j][1], true);
      correctionCancelers.length = 0;
    } catch (e) {}
    try { if (anchorObserver) { anchorObserver.disconnect(); anchorObserver = null; } } catch (e) {}
    domReadyWaiters = null;
    domReadyListener = null;
    domReadyHandlerRef = null;
    unwrapHistory();
    try { delete w.MMXSharedShell; } catch (e) { try { w.MMXSharedShell = null; } catch (e2) {} }
    state.active = false;
  }

  /* ---- public API (candidate only) ---- */
  var api = {
    __mmxBridge: PROTOCOL,
    navigate: function (href, mode) {
      if (mode === undefined) mode = "push";
      if (mode !== "push" && mode !== "replace") return false;
      var hs = coerceHref(href);
      if (hs === null) return false;
      var canonicalBase = currentCanonical();
      if (canonicalBase === null) return false;
      var u = resolveHref(hs, canonicalBase);
      if (!u) return false;
      if (u.origin !== childOrigin) {
        var mapped = firstPartyToChild(u);
        if (!mapped) return false;  // arbitrary external origins are never internal
        u = mapped;
      }
      if (!credentialsFree(u)) return false;
      if (!state.active) return enqueue({ kind: "nav", href: u, mode: mode });
      return performNavigate(u, mode);
    },
    openAuth: function (intent) {
      if (AUTH_INTENTS.indexOf(intent) === -1) return false;
      if (!state.active) return enqueue({ kind: "auth", intent: intent });
      send("AUTH_REQUEST", { intent: intent });
      return true;
    }
  };
  try {
    Object.defineProperty(api, "active", { enumerable: true, get: function () { return state.active === true; } });
    // Incumbent preference owners can distinguish applying parent presentation
    // from a deliberate user edit, without reading or transferring account state.
    Object.defineProperty(api, "applyingContext", { enumerable: true, get: function () { return suppress === true; } });
  } catch (e) {
    try { api.active = false; } catch (e2) {}
  }
  try { w.MMXSharedShell = Object.freeze(api); } catch (e) {}

  messageHandlerRef = onMessage;
  pagehideHandlerRef = function (event) {
    // A persisted document resumes with its existing JavaScript and bridge owners.
    if (!event || event.persisted !== true) cleanup();
  };
  try { w.addEventListener("message", messageHandlerRef, false); } catch (e) {}
  try { w.addEventListener("pagehide", pagehideHandlerRef, false); } catch (e) {}
  wrapHistory();
  // Arm the existing single readiness listener while the data-sync head script runs.
  whenDocumentReady(function () {});
})();
