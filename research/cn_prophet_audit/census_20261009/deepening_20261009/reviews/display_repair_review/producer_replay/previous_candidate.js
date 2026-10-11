/* cn_prophet_live.js — CN Breathing Platform runtime board (CN-PR-3).
   Polls live/cn_prophet_live.json and paints only the reserved .pv-live chip on
   each .pvcard[data-ticker]. The SSR session floor is carried by the existing
   stocks header; there is no standalone page-level CN live/telemetry module.

   Fail-closed. A 401, a bad schema, a feed older than the page session, or an
   artifact at least 15 minutes old tears the live layer down and leaves the SSR
   board untouched. No client-side scoring or ranking.

   PAIRED plain-copy: templates/cn_prophet_live.js must byte-match
   site/cn_prophet_live.js.

   Vocabulary fence (G0.6): glance copy stays observational. Settled-fact
   tokens are banned by tests/test_cn_live_surface.py (BANNED).
*/
(function () {
  "use strict";
  var URL = "live/cn_prophet_live.json";
  var SCHEMA = "cn_prophet_live.states/v1";
  var POLL = 120000;
  var FLOOR = 30000;
  var MAXAGE = 900000; /* 15 min × 3 missed evaluator passes */
  var DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

  var STATE = {
    dormant:  ["Watching", "观察中"],
    near:     ["Near", "临近"],
    forming:  ["Forming", "正在形成"],
    faded:    ["Fell back", "回落"],
    at_risk:  ["At the edge", "靠近失效"],
    unknown:  ["No read", "暂无判读"],
    dark:     ["Unread", "未能读取"]
  };
  var STATUS = {
    trading:              ["Trading", "交易中"],
    session_break:        ["Lunch break", "盘中暂歇"],
    limit_up_locked:      ["Limit-up lock", "一字涨停"],
    limit_down_locked:    ["Limit-down lock", "一字跌停"],
    unavailable:          ["No quote", "暂无行情"],
    suspended_suspected:  ["Halted", "停牌"]
  };

  var _bakedSession;
  var _painted = false;
  var _timer = 0;
  var _lastFetch = 0;
  var _fetching = false;
  var _request = 0;
  var _expiryTimer = 0;
  var _expiresAt = 0;
  var FUTURE = 60000; /* research choice: allowed device/source clock skew */

  function pageSession() {
    if (_bakedSession !== undefined) return _bakedSession;
    _bakedSession = "";
    var el = document.getElementById("stocks-header");
    var s = el ? (el.getAttribute("data-cn-session") || "") : "";
    if (DATE_RE.test(s)) _bakedSession = s;
    return _bakedSession;
  }

  function feedIsCurrent(d) {
    var floor = pageSession();
    if (!floor) return true;
    var s = String(d.session || "");
    return DATE_RE.test(s) && s >= floor;
  }

  function setBL(el, en, zh) {
    el.textContent = "";
    var a = document.createElement("span"); a.className = "l-en"; a.textContent = en;
    var b = document.createElement("span"); b.className = "l-zh"; b.textContent = zh;
    el.appendChild(a); el.appendChild(b);
  }

  function pair(table, key) {
    var row = table[key];
    return row ? row : [key, key];
  }

  function ageMs(d) {
    var iso = (d.liveness && d.liveness.artifact_written_at) || d.built_at || "";
    var t = Date.parse(iso);
    return isFinite(t) ? (Date.now() - t) : Infinity;
  }

  function refuse(d, status) {
    if (status === 401 || status === 403) return true;
    if (!d || d.schema !== SCHEMA) return true;
    if (d.status === "dark") return true;
    if (!feedIsCurrent(d)) return true;
    var age = ageMs(d);
    if (!isFinite(age) || age < -FUTURE || age >= MAXAGE) return true;
    return false;
  }

  function tearDown() {
    if (_expiryTimer) clearTimeout(_expiryTimer);
    _expiryTimer = 0;
    _expiresAt = 0;
    if (!_painted) return;
    var slots = document.querySelectorAll(".pvcard[data-ticker] .pv-live");
    for (var i = 0; i < slots.length; i++) {
      var el = slots[i];
      el.hidden = true;
      el.className = "pv-live";
      el.innerHTML = "";
      el.removeAttribute("data-tip-en");
      el.removeAttribute("data-tip-zh");
    }
    _painted = false;
  }

  function paintChip(el, name) {
    var st = name.state;
    var ms = name.market_status;
    if (!st || st === "dark" || st === "unknown" || st === "dormant") {
      if (ms && ms !== "trading" && STATUS[ms]) {
        st = null;
      } else {
        if (!el.hidden) {
          el.hidden = true;
          el.className = "pv-live";
          el.innerHTML = "";
        }
        return;
      }
    }
    var word = st ? pair(STATE, st) : pair(STATUS, ms);
    var extra = (st && ms && ms !== "trading" && STATUS[ms]) ? pair(STATUS, ms) : null;
    var cls = "pv-live";
    if (ms === "limit_up_locked") cls += " cnpl-up";
    else if (ms === "limit_down_locked") cls += " cnpl-down";
    else if (ms === "session_break") cls += " cnpl-break";
    el.className = cls;
    var en = word[0] + (extra && extra !== word ? " · " + extra[0] : "");
    var zh = word[1] + (extra && extra !== word ? " · " + extra[1] : "");
    el.innerHTML = "";
    setBL(el, en, zh);
    el.setAttribute("data-tip-en", "Intraday read — windows, not certainties. Tonight's settlement decides.");
    el.setAttribute("data-tip-zh", "盘中暂读 — 窗口，不是定论。今晚结算才算数。");
    el.hidden = false;
    _painted = true;
  }

  function paintCards(names) {
    var slots = document.querySelectorAll(".pvcard[data-ticker] .pv-live");
    for (var i = 0; i < slots.length; i++) {
      var el = slots[i];
      var card = el.closest ? el.closest(".pvcard") : null;
      var tkr = card ? card.getAttribute("data-ticker") : "";
      var row = (names && tkr) ? names[tkr] : null;
      if (row) paintChip(el, row);
      else if (!el.hidden) {
        el.hidden = true;
        el.className = "pv-live";
        el.innerHTML = "";
      }
    }
  }

  function expire() {
    if (_expiresAt && Date.now() >= _expiresAt) tearDown();
  }

  function apply(d) {
    paintCards(d.names || {});
    if (_expiryTimer) clearTimeout(_expiryTimer);
    _expiresAt = Date.now() - ageMs(d) + MAXAGE;
    _expiryTimer = setTimeout(expire, Math.max(0, _expiresAt - Date.now()));
  }

  function tick(force) {
    expire();
    if (document.visibilityState === "hidden" && !force) return;
    var now = Date.now();
    if (!force && _fetching) return;
    if (!force && _lastFetch && (now - _lastFetch) < FLOOR) return;
    _fetching = true;
    _lastFetch = now;
    var request = ++_request;
    var controller = typeof AbortController !== "undefined" ? new AbortController() : null;
    var deadline = setTimeout(function () {
      if (controller) controller.abort(); /* also bound obsolete requests */
      if (request !== _request) return;
      ++_request; /* any late response is obsolete */
      _fetching = false;
      tearDown();
    }, FLOOR); /* bounded request lifetime; poll cadence remains unchanged */
    var options = { cache: "no-store" };
    if (controller) options.signal = controller.signal;
    fetch(URL + "?t=" + now, options)
      .then(function (r) {
        if (request !== _request) return null;
        if (!r.ok) { tearDown(); return null; }
        return r.json().then(function (d) { return { d: d, status: r.status }; });
      })
      .then(function (pack) {
        if (request !== _request) return;
        if (!pack) { tearDown(); return; }
        if (refuse(pack.d, pack.status)) { tearDown(); return; }
        try { apply(pack.d); } catch (e) { tearDown(); }
      })
      .catch(function () { if (request === _request) tearDown(); })
      .then(function () {
        clearTimeout(deadline);
        if (request === _request) _fetching = false;
      });
  }

  function arm() {
    if (!document.getElementById("stocks-header")) return;
    pageSession();
    tick(true);
    if (_timer) clearInterval(_timer);
    _timer = setInterval(function () { tick(false); }, POLL);
    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "visible") tick(true);
    });
  }

  if (document.readyState !== "loading") arm();
  else document.addEventListener("DOMContentLoaded", arm);
})();
