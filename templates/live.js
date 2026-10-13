/* live.js — progressive enhancement that patches live prices + the nightly
 * divergence/invalidation signal into the static, nightly-built pages. PURE
 * DISPLAY: it refreshes the price text, a freshness dot, and a small divergence
 * chip; it never touches the scores/verdicts (those are the nightly slow brain).
 * If nothing is configured/served it cleanly no-ops and the page stays exactly as
 * the build rendered it.
 *
 * HONESTY: this is now a MIXED-LATENCY feed. Polygon Standard / Yahoo legs keep
 * their configured vendor delay floor (currently ~15 min), while mainland A-share
 * snapshots from Tushare rt_k or Tencent carry a zero vendor floor and their real
 * exchange timestamp. Freshness is therefore resolved PER QUOTE, not by painting
 * the entire poller delayed merely because one provider is delayed.
 *
 * Three browser price sources, in priority order (all optional):
 *   - the Worker /quotes endpoint (window.LIVE_QUOTES_URL) -> freshest, per-page.
 *   - a static same-contract snapshot JSON (window.LIVE_SNAPSHOT_URL, written by
 *     scripts/build_live_quotes) -> provider-specific latency: Tushare/Tencent CN
 *     live, Polygon/Yahoo according to the configured delayed floor.
 *   - the static live/overlay.json (written by build_live_overlay) -> the
 *     divergence flag + market sessions (+ a conservative delayed price fallback).
 *
 * Cards carry <span class="nb-px" data-sym="600519.SS" data-mkt="cn">. data-sym is
 * the canonical market symbol the build already knows — the browser does NO symbol
 * re-derivation. data-mkt decides currency formatting / decimal precision. An
 * adjacent <span class="nb-chg" data-sym="..."> (optional) is painted with the %
 * change computed from prevClose.
 */
(function () {
  if (window.__mmLiveInit) return; window.__mmLiveInit = true; // idempotency guard — second include is a no-op
  if (!window.LIVE_ENABLED) return;                          // static-site no-op
  var URL = window.LIVE_QUOTES_URL || "";
  var SNAP = window.LIVE_SNAPSHOT_URL || "";                 // keyless no-Worker fallback
  // Live breadth (Phase 2, LIVE_TAPE_SCOREBOARD_MASTERPLAN §4): the intraday
  // adv/dec payload the breadth poller publishes beside quotes.json. Fetched on
  // the same 60s tick ONLY when the page carries the sbx scoreboard; absent or
  // stale payload -> the baked "last close" numbers stay untouched.
  var BREADTH = window.LIVE_BREADTH_URL ||
    (SNAP ? SNAP.replace(/quotes\.json(\?.*)?$/, "breadth.json") : "live/breadth.json");
  var POLL = (window.LIVE_POLL_SEC || 60) * 1000;
  var STALE_MIN = window.LIVE_STALE_MIN || 20;
  // Default vendor delay FLOOR (min) for quote sources that do not declare a
  // lower-latency lane. Today Polygon Standard / Yahoo inherit 15; the mainland
  // Tushare rt_k + Tencent sources are explicitly zero-floor in sourceDelayFloor().
  // This is a fallback policy, no longer a claim that every symbol is delayed.
  var DELAYED_MIN = window.LIVE_DELAYED_MIN || 0;
  var FEED_LABEL = window.LIVE_FEED_LABEL || "";   // honest caption for legacy [data-live-label] nodes
  var OVERLAY = "live/overlay.json";
  var inflight = false, lastTs = 0, pendingRefresh = false;
  var _paused = false, _timer = null;
  // ── Live Tape (/ws/tape) state ──
  // TAPE_SYMS: the six instruments the server relay fans out; the ws only opens
  // if the page actually carries one of these tiles. _wsSock: the socket (or
  // null). _wsLast[sym] = wall-clock (ms) we last applied a ws tick for `sym` —
  // used to make a ws quote win over the poller while the socket is live-feeding.
  var TAPE_SYMS = { "ES=F": 1, "NQ=F": 1, "YM=F": 1, "RTY=F": 1, "^TNX": 1, "DX-Y.NYB": 1 };
  var _wsSock = null, _wsLast = {}, _wsRetry = 0, _wsTimer = null, _wsClosed = false;
  var WS_FRESH_MS = 30000;   // a ws tick shields a symbol from the poller this long
  // Ops kill switch (config.yml live.ws_tape_enabled -> LIVE_WS_TAPE). Defaults
  // ON when the flag is absent (older live_config.js) so the tape works the moment
  // the relay is deployed, without a page rebuild.
  var WS_TAPE = (window.LIVE_WS_TAPE !== false);

  function nodes() { return [].slice.call(document.querySelectorAll(".nb-px[data-sym]")); }
  function chgNodes() { return [].slice.call(document.querySelectorAll(".nb-chg[data-sym]")); }
  function symNodes() { return [].slice.call(document.querySelectorAll(".nb-px[data-sym],.nb-chg[data-sym]")); }
  function rawSym(el) { return (el.getAttribute("data-sym") || "").trim().toUpperCase(); }
  // Markets whose BOARD BAKES a "$" on the nightly price, so a live patch must put
  // it back or the number visibly loses its currency glyph mid-session. Measured on
  // the served pages 2026-08-19: us_stocks.html data-mkt="us" bakes "$212.55" and
  // canada_stocks.html data-mkt="ca" bakes "$15.20", while hk_stocks.html ("hk",
  // HKD) bakes "6.22" and china_stocks.html ("cn", CNY) bakes "37.70" bare. `ca` was
  // missing here, so every .TO card dropped its "$" the moment live.js patched it —
  // invisible until the Canada board joined the live universe and started patching
  // at all. Do NOT add "hk"/"cn": those are HKD/CNY and a "$" would be plain wrong.
  var DOLLAR_MKT = { us: 1, ca: 1 };
  function fmtPrice(price, mkt) {
    if (mkt === "crypto") {
      try { return "$" + Number(price).toLocaleString(undefined, { maximumFractionDigits: 0 }); }
      catch (e) { return "$" + Math.round(Number(price)); }
    }
    var dec = (mkt === "fx") ? 4 : 2;
    var s;
    try { s = Number(price).toLocaleString(undefined, { minimumFractionDigits: dec, maximumFractionDigits: dec }); }
    catch (e) { s = Number(price).toFixed(dec); }
    return (DOLLAR_MKT[mkt] ? "$" : "") + s;
  }
  // Crypto trades 24/7 and is refreshed on its own hourly cadence, so it goes stale
  // only when a scheduled refresh is actually MISSED (~65 min), not at the 20-min
  // equity threshold.
  function isStale(mkt, ageMin, fallback) {
    if (ageMin == null) return !!fallback;
    var lim = (mkt === "crypto") ? (window.LIVE_CRYPTO_STALE_MIN || 65) : STALE_MIN;
    return ageMin > lim;
  }
  // Vendor-delay authority belongs to the individual quote source. The static
  // snapshot already carries `source` and `delayMin`; Tushare/Tencent exchange
  // clocks are genuinely live and must not inherit the Polygon/Yahoo 15m floor.
  function sourceDelayFloor(q) {
    var src = String((q && q.source) || "").toLowerCase();
    if (src === "tushare-rt-k" || src === "tencent") return 0;
    return DELAYED_MIN;
  }
  // ^TNX transform (Live Tape): Yahoo quotes the 10-year yield as yield×10
  // (42.5 => 4.25%). Price tiles with data-fmt="tnx" show price/10 + "%"; the
  // delta is shown in basis points (bps = price-delta × 10) rather than percent,
  // which is how rate moves are read. bpsDelta needs the absolute price delta;
  // prevClose (raw yield×10) is threaded through the reading for that.
  function isTnx(el) { return (el.getAttribute("data-fmt") || "") === "tnx"; }
  // SCALE-AWARE (go-live 2026-07-24): the feeds disagree on ^TNX units — the
  // relay's REST-fallback frames deliver percent directly (live-verified 4.679
  // while the 10Y was 4.68%), whereas the ×10 index convention (46.79) exists
  // on other paths. A 10Y above 15% or below 1.5-on-the-×10-scale hasn't traded
  // since 1981, so the threshold cleanly separates the two encodings.
  function tnxPct(v) { v = Number(v); return v > 15 ? v / 10 : v; }
  function fmtTnxPrice(price) { return tnxPct(price).toFixed(2) + "%"; }
  function tnxBps(price, prevClose) {
    if (prevClose == null) return null;
    return (tnxPct(price) - tnxPct(prevClose)) * 100;
  }
  function paintChg(el, chg, stale, reading) {
    if (isTnx(el) && reading && reading.price != null) {
      var _pc = reading.prevClose;
      if (_pc == null && chg != null && isFinite(chg) && Number(chg) > -100) {
        _pc = Number(reading.price) / (1 + Number(chg) / 100);
      }
      var bps = tnxBps(reading.price, _pc);
      if (bps != null) {
        var upB = bps >= 0;
        el.textContent = (upB ? "+" : "") + Number(bps).toFixed(0) + " bps";
        el.classList.remove("up", "down", "dn", "stale");
        el.classList.add(upB ? "up" : "down");
        if (stale) el.classList.add("stale");
        return;
      }
    }
    if (Math.abs(Number(chg)) < 0.005) chg = 0;
    var up = chg >= 0;
    el.textContent = (up ? "+" : "") + Number(chg).toFixed(2) + "%";
    el.classList.remove("up", "down", "dn", "stale");
    el.classList.add(up ? "up" : "down");
    if (stale) el.classList.add("stale");
  }
  // Cash-market scope is explicit. Futures, FX, crypto and unknown foreign
  // suffixes/indices have their own clocks and must never inherit a US closure.
  function regionOf(s) {
    if (/-USD$/.test(s)) return "crypto";
    if (/=F$/.test(s)) return "futures";
    if (/=X$/.test(s)) return "fx";
    if (/\.HK$/.test(s)) return "hk";
    if (/\.(SS|SZ|BJ)$/.test(s)) return "cn";
    if (/\.(TO|V)$/.test(s)) return "ca";
    var indices = { "^HSI": "hk", "^HSCE": "hk", "^HSTECH": "hk", "^HSCC": "hk", "^HSIL": "hk",
      "^GSPC": "us", "^DJI": "us", "^IXIC": "us", "^NDX": "us",
      "^RUT": "us", "^VIX": "us", "^GSPTSE": "ca", "^SPCDNX": "ca" };
    if (indices[s]) return indices[s];
    if (s.indexOf(".") !== -1) return /^(BRK|BF)\.[AB]$/.test(s) ? "us" : null;
    return /^[A-Z][A-Z0-9]{0,9}(?:-[A-Z])?$/.test(s) ? "us" : null;
  }

  // These receipts arrive on the existing overlay tick. No browser holiday
  // table, second feed or timer: expiry is checked whenever this client paints.
  var _marketSessions = {}, _marketTickers = {};
  var CASH_REGIONS = { us: 1, cn: 1, hk: 1, ca: 1 };
  var MARKET_NAMES = { us: ["US", "美股"], cn: ["China", "A股"],
    hk: ["Hong Kong", "港股"], ca: ["Canada", "加拿大"],
    connect: ["Stock Connect", "互联互通"] };
  var SESSION_WORDS = {
    holiday: ["Market closed", "休市"], weekend: ["Weekend closed", "周末休市"],
    preopen: ["Before open", "尚未开市"], open: ["Market open", "交易中"],
    lunch: ["Lunch break", "午间休市"], postclose: ["Market closed", "已收盘"],
    unverified: ["Status unverified", "状态未确认"]
  };
  function awareTime(value) {
    if (typeof value !== "string" || !/(Z|[+-]\d{2}:\d{2})$/i.test(value)) return NaN;
    return Date.parse(value);
  }
  function quoteTime(value) {
    if (typeof value !== "number") return typeof value === "string" ? value : null;
    var d = new Date(value);
    return isFinite(d.getTime()) ? d.toISOString() : null;
  }
  function invalidQuoteClock(ts, synthetic, now) {
    return synthetic === true || typeof ts !== "number" || !isFinite(ts) ||
      ts <= 0 || ts > now + 60000;
  }
  function receiptState(sess) {
    if (!sess || sess.calendar_verified !== true || !SESSION_WORDS[sess.state]) return "unverified";
    var checked = awareTime(sess.checked_at), until = awareTime(sess.valid_until), now = Date.now();
    if (!isFinite(checked) || !isFinite(until) || checked > now + 60000 ||
        until <= now || until <= checked) return "unverified";
    return sess.state;
  }
  function mergeSessions(incoming, snapshot) {
    if (!incoming || typeof incoming !== "object") return;
    Object.keys(MARKET_NAMES).forEach(function (region) {
      var next = incoming[region], old = _marketSessions[region];
      if (!next || typeof next !== "object") return;
      var nt = awareTime(next.checked_at), ot = old && awareTime(old.checked_at);
      if (nt > Date.now() + 60000) nt = NaN;
      if (ot > Date.now() + 60000) ot = NaN;
      // Each producer has its own cadence. A late overlay must not replace
      // a newer minute-snapshot receipt; quote ordering is a separate clock.
      if (!old || (isFinite(nt) && (!isFinite(ot) || nt > ot || (snapshot && nt === ot)))) {
        _marketSessions[region] = next;
      }
    });
  }
  function pageRegion() {
    var pathname = (window.location && window.location.pathname) || "";
    var name = pathname.split("/").pop().replace(/\.html$/, "");
    if (/^china(?:_stocks)?$/.test(name)) return "cn";
    if (/^hk(?:_stocks)?$/.test(name)) return "hk";
    if (/^canada(?:_stocks)?$/.test(name)) return "ca";
    if (name === "us_stocks" || name === "macro") return "us";
    var body = document.body, cls = body && body.classList;
    if (cls && (cls.contains("page-china") || cls.contains("page-china-stocks"))) return "cn";
    if (cls && cls.contains("page-hk")) return "hk";
    if (cls && cls.contains("page-canada")) return "ca";
    if (cls && (cls.contains("page-stocks") || cls.contains("page-macro"))) return "us";
    return null;
  }
  function escapeText(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function marketBi(en, zh) {
    return '<span class="l-en">' + escapeText(en) + '</span><span class="l-zh">' + escapeText(zh) + '</span>';
  }
  function localOpen(sess) {
    if (!sess || !isFinite(awareTime(sess.next_open)) || !sess.timezone) return null;
    try {
      var parts = new Intl.DateTimeFormat("en-CA", { timeZone: sess.timezone,
        year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit",
        minute: "2-digit", hourCycle: "h23", timeZoneName: "short" })
        .formatToParts(new Date(sess.next_open));
      var p = {};
      parts.forEach(function (part) { p[part.type] = part.value; });
      return p.year + "-" + p.month + "-" + p.day + " " + p.hour + ":" + p.minute + " " + p.timeZoneName;
    } catch (e) { return null; }
  }
  function sessionDetails(sess, state, zh) {
    var words = [];
    if (state !== "unverified" && sess) {
      var holiday = zh ? sess.holiday_name_zh : sess.holiday_name;
      if (holiday) words.push(holiday);
      if (sess.early_close) words.push(zh ? "半日市" : "Half day");
    }
    if (sess && sess.calendar_verified === true && /^\d{4}-\d{2}-\d{2}$/.test(sess.expected_session || "")) {
      words.push((state === "unverified"
        ? (zh ? "上次确认收盘：" : "Last confirmed close: ")
        : (zh ? "最近收盘：" : "Last completed: ")) + sess.expected_session);
    }
    var next = state !== "unverified" && localOpen(sess);
    words.push(next ? (zh ? "下次开市：" : "Next open: ") + next
      : (zh ? "开市时间待确认" : "Next open unverified"));
    return words.join(" · ");
  }
  function priceIssue(region) {
    var issue = null, rank = { unverified: 1, late: 2, missing: 3, invalid: 4, rejected: 5 };
    symNodes().forEach(function (el) {
      var sym = rawSym(el), ov = _marketTickers[sym] || {}, reading = el._mmLastReading;
      if (regionOf(sym) !== region) return;
      var guard = reading && cashGuard(sym, reading, _marketSessions, ov, el);
      var rejected = guard ? guard.quoteState === "invalid"
        : ov.quote_state === "invalid" || (ov.divergence && ov.divergence.flag === "bad_print");
      var q = rejected ? "rejected" : el.getAttribute("data-data-state") || ov.data_state;
      if (rank[q] && (!issue || rank[q] > rank[issue])) issue = q;
    });
    return issue;
  }
  function renderSessionStrip() {
    var region = pageRegion();
    if (!region || !document.querySelector) return;
    var strip = document.getElementById("market-session-status");
    if (!strip) {
      var nav = document.querySelector(".site-nav");
      var host = nav && nav.parentNode;
      if (!host || !host.insertBefore) return;
      strip = document.createElement("div");
      strip.id = "market-session-status";
      strip.className = "dtp-row";
      strip.setAttribute("role", "status");
      strip.setAttribute("aria-live", "polite");
      host.insertBefore(strip, nav.nextSibling);
    }
    var sess = _marketSessions[region], state = receiptState(sess);
    var names = MARKET_NAMES[region], words = SESSION_WORDS[state];
    var tone = state === "open" ? "live" : state === "unverified" ? "behind"
      : state === "preopen" || state === "lunch" ? "pre" : "stale";
    var html = '<span class="dtp-chip dtp-chip--' + tone + '">' +
      marketBi(names[0] + " · " + words[0], names[1] + " · " + words[1]) + '</span>';
    var issue = priceIssue(region);
    if (issue) {
      var issueWords = { late: ["Some prices late", "部分价格滞后"], missing: ["Some prices missing", "部分价格缺失"],
        invalid: ["Some prices invalid", "部分价格无效"], unverified: ["Prices unverified", "价格未确认"],
        rejected: ["Quote rejected", "报价已拒绝"] };
      html += '<span class="dtp-chip dtp-chip--behind">' + marketBi(issueWords[issue][0], issueWords[issue][1]) + '</span>';
    }
    html += '<span class="dtp-asof">' + marketBi(sessionDetails(sess, state, false),
      sessionDetails(sess, state, true)) + '</span>';
    var connect = _marketSessions.connect, cs = receiptState(connect);
    if ((region === "cn" || region === "hk") && connect &&
        (cs !== state || (cs === "holiday" && connect.holiday_name !== (sess && sess.holiday_name)))) {
      html += '<span class="dtp-chip dtp-chip--' + (cs === "unverified" ? "behind" : cs === "open" ? "live" : "stale") + '">' +
        marketBi("Stock Connect · " + SESSION_WORDS[cs][0], "互联互通 · " + SESSION_WORDS[cs][1]) + '</span>';
      html += '<span class="dtp-asof">' + marketBi(sessionDetails(connect, cs, false),
        sessionDetails(connect, cs, true)) + '</span>';
    }
    if (strip.innerHTML !== html) strip.innerHTML = html;
    strip.setAttribute("data-session-state", state);
    var sources = (sess && Array.isArray(sess.source_urls)) ? sess.source_urls.join(" · ") : "";
    strip.setAttribute("data-tip-en", state === "unverified"
      ? "Calendar status is unverified. Displayed data keeps its original date."
      : "Exchange session calendar. The data on this page retains its own source date.");
    strip.setAttribute("data-tip-zh", state === "unverified"
      ? "交易日历状态未确认。已显示数据保留原始日期。"
      : "交易所交易时段日历。本页数据保留各自的来源日期。");
    if (sources) {
      strip.setAttribute("data-tip-rc-en", sources);
      strip.setAttribute("data-tip-rc-zh", sources);
    } else {
      strip.removeAttribute("data-tip-rc-en"); strip.removeAttribute("data-tip-rc-zh");
    }
  }
  var CARRIED_META = ["data-through", "data-quote-ts", "data-source"];
  function saveCarried(el) {
    var meta = {};
    CARRIED_META.forEach(function (key) { meta[key] = el.getAttribute(key); });
    el._mmCarried = { html: el.innerHTML, className: el.className, meta: meta };
  }
  function rememberCarried(el) {
    if (!el._mmCarried) saveCarried(el);
  }
  function restoreCarried(el) {
    rememberCarried(el);
    el.innerHTML = el._mmCarried.html;
    el.className = el._mmCarried.className;
    CARRIED_META.forEach(function (key) {
      var value = el._mmCarried.meta[key];
      if (value != null) el.setAttribute(key, value); else el.removeAttribute(key);
    });
  }
  function observationDay(r, sess) {
    if (r.invalidClock || !sess || !sess.timezone || !isFinite(awareTime(r.quoteTs))) return null;
    try {
      var p = {};
      new Intl.DateTimeFormat("en-CA", { timeZone: sess.timezone, year: "numeric",
        month: "2-digit", day: "2-digit" }).formatToParts(new Date(r.quoteTs))
        .forEach(function (part) { p[part.type] = part.value; });
      return p.year + "-" + p.month + "-" + p.day;
    } catch (e) { return null; }
  }
  function frozenPriceQuality(r, sess, el) {
    var rowDate = el && (el._mmCarried ? el._mmCarried.meta["data-through"] : el.getAttribute("data-through"));
    var observed = rowDate || observationDay(r, sess), expected = sess && sess.expected_session;
    if (!observed) return r.price == null ? "missing" : "unverified";
    if (!/^\d{4}-\d{2}-\d{2}$/.test(observed) || !/^\d{4}-\d{2}-\d{2}$/.test(expected || "")) return "unverified";
    // Minute age is not a missed-session count. A genuine prior close stays
    // current throughout a closure; no page-wide date is assigned to a row.
    return observed === expected ? "current" : observed < expected ? "late" : "unverified";
  }
  function cashGuard(sym, r, sessions, ov, el) {
    var region = regionOf(sym);
    if (!CASH_REGIONS[region]) return null;
    var sess = (sessions || _marketSessions)[region];
    var state = receiptState(sess);
    var frozen = state === "holiday" || state === "weekend" || (sess && sess.data_frozen === true);
    var quality = ov && ov.data_state;
    if (!/^(current|late|missing|invalid|unverified)$/.test(quality || "")) {
      if (r.price != null && (typeof r.price !== "number" || !isFinite(r.price) || r.price <= 0)) quality = "invalid";
      else if (frozen && state !== "unverified") quality = frozenPriceQuality(r, sess, el);
      else quality = r.price == null ? "missing" : state === "unverified" ? "unverified"
        : r.stale || (ov && (ov.stale || ov.baseline_stale)) ? "late" : "current";
    }
    if (quality === "current" && state !== "unverified") {
      var through = (ov && ov.data_through) || (el && (el._mmCarried
        ? el._mmCarried.meta["data-through"] : el.getAttribute("data-through")));
      // Age an explicitly retained date against the latest completed-session
      // expectation; a fresh quote cannot heal history that missed a session.
      if (/^\d{4}-\d{2}-\d{2}$/.test(through || "") && /^\d{4}-\d{2}-\d{2}$/.test(sess.expected_session || "")) {
        if (through < sess.expected_session) quality = "late";
        else if (through > sess.session_date) quality = "unverified";
      }
    }
    // Rejection describes an observation, not the stored baseline. A newer
    // real quote can supersede an old rejected print without changing data_state.
    var oldQuoteTime = awareTime(ov && ov.quote_ts), newQuoteTime = awareTime(r.quoteTs);
    var oldClockInvalid = (ov && ov.quote_clock_invalid === true) ||
      !isFinite(oldQuoteTime) || oldQuoteTime > Date.now() + 60000 ||
      /^(synthetic|missing|invalid|future) quote timestamp$/.test((ov && ov.stale_reason) || "");
    var newerQuote = !r.invalidClock && isFinite(newQuoteTime) &&
      (oldClockInvalid || newQuoteTime > oldQuoteTime);
    var quoteState = newerQuote ? (r.stale ? "stale" : "current") : ov && ov.quote_state;
    if (r.invalidClock || (!newerQuote && ov && ov.divergence && ov.divergence.flag === "bad_print") ||
        (r.price != null && (typeof r.price !== "number" || !isFinite(r.price) || r.price <= 0))) quoteState = "invalid";
    if (state === "unverified" && quality === "current") quality = "unverified";
    // Frozen ticker metadata can outlive its old overlay receipt. The newest
    // session receipt owns closure; the record still owns baseline health.
    var held = state === "unverified" || frozen || quality !== "current" || quoteState === "invalid";
    return { held: held, frozen: frozen, state: state, quality: quality, quoteState: quoteState, sess: sess, ov: ov };
  }
  function paintHeldPrice(el, r, guard) {
    restoreCarried(el);
    var ov = guard.ov || {};
    // The overlay may supply a newer carried close than this page's baked text.
    // Only its explicit frozen record may replace that baseline, never a fresh
    // retrieval of a quote during the closure.
    var accepted = guard.state !== "unverified" && guard.frozen && ov.data_frozen === true &&
        (guard.quality === "current" || guard.quality === "late") &&
        typeof ov.price === "number" && isFinite(ov.price) && ov.price > 0;
    if (accepted) {
      el.classList.remove("skel", "mx-skel", "dtp-token", "behind");
      el.removeAttribute("aria-busy");
      el.textContent = el.hasAttribute("data-bare")
        ? fmtPrice(ov.price, el.getAttribute("data-mkt")).replace(/^\$/, "")
        : fmtPrice(ov.price, el.getAttribute("data-mkt"));
    }
    var dataState = guard.quality;
    var state = guard.quoteState === "invalid" ? "behind"
      : dataState === "late" ? "stale" : dataState !== "current" ? "behind" : "closed";
    el.setAttribute("data-live", state);
    el.setAttribute("data-session-state", guard.state);
    el.setAttribute("data-data-state", dataState);
    if (guard.quoteState) el.setAttribute("data-quote-state", guard.quoteState); else el.removeAttribute("data-quote-state");
    if (accepted && ov.data_through) el.setAttribute("data-through", ov.data_through);
    if (ov.quote_ts || r.quoteTs) el.setAttribute("data-quote-ts", ov.quote_ts || r.quoteTs);
    if (ov.source || r.src) el.setAttribute("data-source", ov.source || r.src);
    if (accepted) saveCarried(el);
    if (r.invalidClock) {
      if (r.quoteTs) el.setAttribute("data-quote-ts", r.quoteTs); else el.removeAttribute("data-quote-ts");
      if (r.src) el.setAttribute("data-source", r.src); else el.removeAttribute("data-source");
    }
    var through = el.getAttribute("data-through"), qt = el.getAttribute("data-quote-ts");
    var src = el.getAttribute("data-source");
    var en = SESSION_WORDS[guard.state][0], zh = SESSION_WORDS[guard.state][1];
    if (dataState !== "current") {
      var qualityWords = { late: ["data late", "数据滞后"], missing: ["data missing", "数据缺失"],
        invalid: ["data invalid", "数据无效"], unverified: ["data unverified", "数据未确认"] };
      en += " · " + qualityWords[dataState][0]; zh += " · " + qualityWords[dataState][1];
    }
    if (through) { en += " · Prices through " + through; zh += " · 价格截至 " + through; }
    if (guard.quoteState === "invalid") { en += " · Quote rejected"; zh += " · 报价已拒绝"; }
    var quoteLabel = guard.quoteState === "invalid" ? ["Rejected quote", "已拒绝报价"] : ["Quote", "报价"];
    if (src) { en += " · " + quoteLabel[0] + " source: " + src; zh += " · " + quoteLabel[1] + "来源：" + src; }
    if (qt) { en += " · " + quoteLabel[0] + " time: " + qt; zh += " · " + quoteLabel[1] + "时间：" + qt; }
    el.setAttribute("data-tip-en", en); el.setAttribute("data-tip-zh", zh);
    el.removeAttribute("title");
  }

  function injectStyle() {
    if (document.getElementById("live-px-style")) return;
    var s = document.createElement("style");
    s.id = "live-px-style";
    s.textContent =
      ".nb-px[data-live]::after{content:'';display:inline-block;width:6px;height:6px;" +
      "border-radius:50%;margin-left:5px;vertical-align:middle;background:#16a34a;" +
      "box-shadow:0 0 0 0 rgba(22,163,74,.5);animation:livePulse 2s infinite}" +
      ".nb-px[data-live='stale']::after{background:#9ca3af;animation:none;box-shadow:none}" +
      ".nb-px[data-live='closed']::after{background:#6b7280;animation:none;box-shadow:none}" +
      ".nb-px[data-live='delayed']::after{background:#d97706;animation:none;box-shadow:none}" +
      ".nb-px[data-live='behind']::after{background:var(--muted);animation:none;box-shadow:none}" +
      ".nb-dvg{font-size:10px;font-weight:700;margin-left:5px;padding:0 4px;border-radius:4px;" +
      "vertical-align:middle;white-space:nowrap}" +
      ".nb-dvg.alert{background:color-mix(in srgb,var(--act,#dc2626) 15%,transparent);" +
      "color:var(--ink-act,var(--act,#991b1b))}" +
      ".nb-dvg.watch{background:color-mix(in srgb,var(--warn,#d97706) 16%,transparent);" +
      "color:var(--ink-warn,var(--warn,#92400e))}" +
      ".nb-chg{font-weight:600}" +
      ".nb-chg.up{color:var(--ink-up,#15803d)}" +
      ".nb-chg.down{color:var(--ink-down,#b91c1c)}" +
      ".nb-chg.stale{color:var(--muted,#5d6b7e);font-weight:500}" +
      'html[data-lang="zh"] .nb-chg.up{color:var(--ink-up,#b91c1c)}' +
      'html[data-lang="zh"] .nb-chg.down{color:var(--ink-down,#15803d)}' +
      "@media (forced-colors:active){.nb-px[data-live]::after{forced-color-adjust:none;border:1px solid currentColor}}" +
      "@keyframes livePulse{0%{box-shadow:0 0 0 0 rgba(22,163,74,.5)}" +
      "70%{box-shadow:0 0 0 5px rgba(22,163,74,0)}100%{box-shadow:0 0 0 0 rgba(22,163,74,0)}}" +
      "@media (prefers-reduced-motion:reduce){.nb-px[data-live]::after{animation:none}}" +
      "html.fx-min .nb-px[data-live]::after{animation:none}";
    document.head.appendChild(s);
  }

  function setChip(el, dvg) {
    var sev = dvg && dvg.severity;
    var chip = el.parentNode && el.parentNode.querySelector(".nb-dvg");
    if (sev !== "alert" && sev !== "watch") { if (chip) chip.remove(); return; }
    if (!chip) { chip = document.createElement("span"); chip.className = "nb-dvg"; el.parentNode.appendChild(chip); }
    chip.className = "nb-dvg " + sev;
    chip.textContent = dvg.flag === "band_breach_up" ? "▲ breach"
      : dvg.flag === "band_breach_down" ? "▼ breach" : "⚠";
    chip.title = dvg.detail || "";
  }

  // ── Shared per-node patch (used by BOTH the poller and the /ws/tape socket) ──
  // reading = { price, src, stale, ageMin, delayFloor, chg, prevClose, basis }.
  var TAPE_NULL_EN = "Quotes unavailable — the rest of this page is unaffected.";
  var TAPE_NULL_ZH = "行情暂不可用——本页其余内容不受影响。";
  function paintTapeNull(el) {
    // Null design is Markets-only. patchSymbol walks every .nb-px[data-sym]
    // site-wide (nav ticker included); TAPE_SYMS is that same symbol set.
    // Pre-diff behaviour outside #sx-markets-v2 was a silent return — keep it.
    var mount = (el.closest && el.closest("#sx-markets-v2")) || null;
    if (!mount) return;
    el.classList.add("dtp-token", "behind");
    el.classList.remove("skel");
    el.removeAttribute("aria-busy");
    el.setAttribute("data-live", "behind");
    el.title = "";
    el.removeAttribute("title");
    // Per-tile behind glyph so .dtp-token.behind has something to tint and the
    // price node keeps true geometry after .skel is dropped.
    el.textContent = "—";
    var line = mount.querySelector && mount.querySelector(".mx-mkt-null");
    if (!line && document.createElement) {
      var html = '<span class="l-en">' + TAPE_NULL_EN + '</span>' +
                 '<span class="l-zh">' + TAPE_NULL_ZH + '</span>';
      line = document.createElement("div");
      line.className = "mx-empty mx-mkt-null";
      line.setAttribute("role", "status");
      // Packet plain line IS the why (.mx-empty-why is required alongside .mx-empty).
      line.innerHTML = '<p class="mx-empty-line mx-empty-why">' + html + '</p>';
      mount.appendChild(line);
    }
  }
  function clearTapeNullLine(el) {
    var mount = el.closest && el.closest("#sx-markets-v2");
    if (!mount || !mount.querySelector) return;
    var still = mount.querySelector(".mx5-mkt-price[data-live='behind']");
    var line = mount.querySelector(".mx-mkt-null");
    if (!still && line && line.parentNode) line.parentNode.removeChild(line);
  }
  function patchPriceNode(el, r, sessions) {
    if (r.price == null) {
      if (TAPE_SYMS[rawSym(el)]) paintTapeNull(el);
      return;
    }
    el.classList.remove("dtp-token", "behind", "skel");
    el.removeAttribute("aria-busy");
    var sym = rawSym(el);
    var mkt = el.getAttribute("data-mkt") || "us";
    el.textContent = isTnx(el)
      ? fmtTnxPrice(r.price)
      : (el.hasAttribute("data-bare")
          ? fmtPrice(r.price, mkt).replace(/^\$/, "")
          : fmtPrice(r.price, mkt));
    el.classList.remove("mx-skel");
    el.removeAttribute("aria-busy");
    var sess = sessions && sessions[regionOf(sym)];
    var closed = sess && sess.open === false;
    var stale = isStale(mkt, r.ageMin, r.stale);
    // A websocket trade frame is zero-floor by construction. Poll readings carry
    // the provider floor resolved in pick(); overlay/poll fallbacks inherit the
    // global delayed floor. Thus a live Tushare/Tencent A-share is allowed to pulse
    // green while a Yahoo quote elsewhere on the same page remains amber/delayed.
    var delayFloor = (r.delayFloor != null && isFinite(r.delayFloor))
      ? Math.max(0, Number(r.delayFloor))
      : (r.basis === "quote" ? 0 : DELAYED_MIN);
    var state = stale ? (closed ? "closed" : "stale")
                      : (delayFloor > 0 ? "delayed" : "1");
    el.setAttribute("data-live", state);
    var word = state === "closed" ? "market closed"
             : state === "stale" ? "stale"
             : state === "delayed" ? ("≥" + delayFloor + "-min delayed") : "live";
    el.title = word + " · " + (r.src || "?") +
      (r.ageMin != null ? " · " + Number(r.ageMin).toFixed(0) + "m ago" : "");
    clearTapeNullLine(el);
  }
  function patchChgNode(el, r) {
    var mkt = el.getAttribute("data-mkt") || "us";
    if (r.chg == null && !(isTnx(el) && r.price != null)) return;
    el.classList.remove("skel");
    el.removeAttribute("aria-busy");
    paintChg(el, r.chg, isStale(mkt, r.ageMin, r.stale), r);
    el.classList.remove("mx-skel");
    el.removeAttribute("aria-busy");
  }
  function patchSymbol(sym, r, sessions, ovT) {
    var touched = false;
    sessions = sessions || _marketSessions;
    ovT = ovT || _marketTickers;
    var ov = ovT[sym], guard = cashGuard(sym, r, sessions, ov);
    nodes().forEach(function (el) {
      if (rawSym(el) !== sym) return;
      rememberCarried(el);
      el._mmLastReading = r;
      var pxGuard = cashGuard(sym, r, sessions, ov, el);
      if (pxGuard && pxGuard.held) {
        paintHeldPrice(el, r, pxGuard);
        setChip(el, null);
      } else {
        patchPriceNode(el, r, sessions);
        if (guard) {
          el.setAttribute("data-session-state", guard.state);
          el.setAttribute("data-data-state", guard.quality);
          if (guard.quoteState) el.setAttribute("data-quote-state", guard.quoteState); else el.removeAttribute("data-quote-state");
          el.removeAttribute("data-tip-en"); el.removeAttribute("data-tip-zh");
        }
        if (r.quoteTs) el.setAttribute("data-quote-ts", r.quoteTs);
        if (r.src) el.setAttribute("data-source", r.src); else if (guard) el.removeAttribute("data-source");
        if (r.dataThrough) el.setAttribute("data-through", r.dataThrough); else if (guard) el.removeAttribute("data-through");
        setChip(el, ov && !ov.stale && !ov.baseline_stale ? ov.divergence : null);
      }
      touched = true;
    });
    chgNodes().forEach(function (el) {
      if (rawSym(el) !== sym) return;
      rememberCarried(el);
      el._mmLastReading = r;
      var rowPx = el.parentNode && el.parentNode.querySelector(".nb-px[data-sym]");
      var chgGuard = cashGuard(sym, r, sessions, ov, rowPx && rawSym(rowPx) === sym ? rowPx : null);
      if (chgGuard && chgGuard.held) {
        restoreCarried(el);
        if (chgGuard.quality !== "current") el.classList.add("stale");
      } else patchChgNode(el, r);
      touched = true;
    });
    return touched;
  }

  function apply(quotes, overlay, snapshotSessions, preserveReadings) {
    mergeSessions(overlay && overlay.sessions, false);
    mergeSessions(snapshotSessions, true);
    if (overlay && overlay.tickers) _marketTickers = overlay.tickers;
    var sessions = _marketSessions, ovT = _marketTickers;
    var serverNow = Date.now();
    renderSessionStrip();

    function pick(sym) {
      var q = quotes[sym], ov = ovT[sym];
      var r = { price: null, src: null, stale: true, ageMin: null, delayFloor: null,
                chg: null, prevClose: null, basis: null };
      if (q && q.price != null) {
        r.price = q.price; r.src = q.source; r.basis = "poll";
        r.invalidClock = invalidQuoteClock(q.ts, q.tsSynthetic, serverNow);
        r.quoteTs = q.tsSynthetic === true ? null : quoteTime(q.quote_ts || q.ts);
        r.dataThrough = q.data_through || null;
        var prev = (q.prevClose != null) ? q.prevClose : null;
        r.prevClose = prev;
        r.chg = (q.changePct != null) ? q.changePct : (prev ? (q.price / prev - 1) * 100 : null);
        r.delayFloor = sourceDelayFloor(q);
        // A retrieval clock cannot certify an equity observation. Missing
        // clocks stay invalid; the other instrument families keep their scope.
        var clockAge = typeof q.ts === "number" && isFinite(q.ts) && q.ts > 0
          ? Math.max(0, (serverNow - q.ts) / 60000)
          : CASH_REGIONS[regionOf(sym)] ? Infinity : 0;
        var measuredAge = (typeof q.delayMin === "number" && isFinite(q.delayMin))
          ? Math.max(0, Number(q.delayMin)) : clockAge;
        r.ageMin = Math.max(r.delayFloor, measuredAge, clockAge);
        r.stale = r.ageMin > STALE_MIN;
      } else if (ov && ov.price != null) {
        r.price = ov.price; r.src = ov.source; r.stale = !!ov.stale; r.basis = "poll";
        r.quoteTs = ov.quote_ts; r.dataThrough = ov.data_through;
        r.prevClose = (ov.prev_close != null) ? ov.prev_close : null;
        r.delayFloor = DELAYED_MIN;
        r.ageMin = (ov.age_min != null) ? Math.max(r.delayFloor, ov.age_min) : ov.age_min;
        r.chg = (ov.chg_pct != null) ? ov.chg_pct : null;
      }
      return r;
    }

    var seen = {};
    symNodes().forEach(function (el) {
      var sym = rawSym(el);
      if (!sym || seen[sym]) return;
      seen[sym] = 1;
      var r = preserveReadings && el._mmLastReading ? el._mmLastReading : pick(sym);
      var guard = cashGuard(sym, r, sessions, ovT[sym], el);
      if (guard && guard.held) {
        patchSymbol(sym, r, sessions, ovT);
      } else if ((TAPE_SYMS[sym] || r.price != null) && !_wsFresher(sym, serverNow)) {
        patchSymbol(sym, r, sessions, ovT);
      }
    });
    renderSessionStrip();
  }

  function getJSON(url, opts) {
    var ctrl = ("AbortController" in window) ? new AbortController() : null;
    var t = ctrl && setTimeout(function () { ctrl.abort(); }, 10000);
    return fetch(url, Object.assign({ signal: ctrl && ctrl.signal }, opts || {}))
      .then(function (r) { if (t) clearTimeout(t); return r.ok ? r.json() : null; })
      .catch(function () { if (t) clearTimeout(t); return null; });
  }

  function tick() {
    if (_paused || document.hidden) return;
    renderSessionStrip();
    // A failed/slow network request must not extend a calendar receipt's life.
    var expired = {};
    nodes().forEach(function (el) {
      var sym = rawSym(el), sess = _marketSessions[regionOf(sym)];
      if (!sess || expired[sym] || receiptState(sess) !== "unverified") return;
      expired[sym] = true;
      patchSymbol(sym, el._mmLastReading || { price: null, stale: true }, _marketSessions, _marketTickers);
    });
    if (inflight) return;
    var ns = symNodes();
    if (!ns.length && !pageRegion()) return;
    var syms = {};
    ns.forEach(function (el) { var s = rawSym(el); if (s) syms[s] = 1; });
    var list = Object.keys(syms);
    if (!list.length && !pageRegion()) return;
    inflight = true;
    // The public snapshot carries minute-fresh session receipts even when
    // the worker is healthy or this regional page has no quote nodes.
    // Share one promise with quote fallback: never fetch the snapshot twice.
    var sP = SNAP ? getJSON(SNAP) : Promise.resolve(null), qP;
    if (!list.length) qP = Promise.resolve(null);
    else if (URL) {
      qP = getJSON(URL.replace(/\/$/, "") + "/quotes?symbols=" + encodeURIComponent(list.join(",")))
        .then(function (r) {
          if ((!r || !r.quotes || !Object.keys(r.quotes).length) && SNAP) return sP;
          return r;
        });
    } else qP = sP;
    function done() {
      inflight = false;
      if (pendingRefresh) { pendingRefresh = false; tick(); }
    }
    var bP = document.getElementById("sbx-stamp") ? getJSON(BREADTH) : Promise.resolve(null);
    Promise.all([qP, getJSON(OVERLAY), bP, sP]).then(function (res) {
      var quotes = (res[0] && res[0].quotes) || {};
      var ts = (res[0] && res[0].ts) || 0;
      var snapshotSessions = res[3] && res[3].sessions;
      if (ts && ts < lastTs) {
        // Calendar authority has its own receipt clock. A late quote response
        // must not discard a newly observed holiday, reopening or expiry.
        if (res[1] || snapshotSessions) apply({}, res[1], snapshotSessions, true);
      } else {
        if (ts) lastTs = ts;
        if (Object.keys(quotes).length || res[1] || snapshotSessions) apply(quotes, res[1], snapshotSessions, false);
      }
      if (res[2]) applyBreadth(res[2]);
      done();
    }, done);
  }

  // ── Live breadth patch (sbx scoreboard, us_stocks) ─────────────────────────
  // Stance bands MIRROR scripts/build_site.py::_breadth_read exactly — if those
  // thresholds or words change, change these with them (render test pins baked).
  //
  // The fail-CLOSED eligibility gate + stamp below (FROZEN CONTRACT §3/§9) is
  // lifted verbatim by tests/test_live_breadth_js_contract.py and executed
  // under node against a DOM stub — do not rename these markers, and keep them
  // as SELF-CONTAINED block comments (not nested in a `//` line) so the sliced
  // text is still valid, parseable JS.
  /* SBX-BREADTH-CONTRACT-BEGIN */
  var SBX_MAX_SOURCE_AGE_MIN = 25;
  var SBX_STANCE = {
    broad: { l: ["broad", "广泛"], v: ["The advance is well-supported across the full 1,500", "上涨在整个 1500 只股票中获得良好支撑"], tone: "pos" },
    thin:  { l: ["thin", "稀薄"], v: ["Few names hold their trend — rallies here are fragile", "守住趋势的个股很少 — 此时的反弹较脆弱"], tone: "neg" },
    mixed: { l: ["mixed", "参差"], v: ["No clear breadth edge either way", "广度上没有明显的方向性优势"], tone: "muted" }
  };
  var SBX_WORDS = {
    w50hi: ["healthy participation", "参与度健康"], w50lo: ["below half — thin tape", "不足半数 — 盘面稀薄"], w50mid: ["middling", "中等水平"],
    w200ok: ["long-term trend intact", "长期趋势完好"], w200bad: ["long-term trend damaged", "长期趋势受损"],
    nnhup: ["more breakouts than breakdowns", "创新高多于创新低"], nnhdn: ["more stocks breaking down than out", "创新低多于创新高"]
  };
  function sbxBi(pair) {
    return '<span class="l-en">' + pair[0] + '</span><span class="l-zh">' + pair[1] + '</span>';
  }
  function sbxSet(id, html) { var el = document.getElementById(id); if (el) el.innerHTML = html; }
  function applyBreadth(b) {
    if (!b || b.usable !== true) return;
    var c = b && b.comp;
    if (!c || typeof c.adv !== "number" || typeof c.dec !== "number") return;
    if (b.session === "closed") return;
    var srcAge = (typeof b.source_age_min === "number" && isFinite(b.source_age_min))
      ? b.source_age_min : null;
    if (srcAge === null) return;
    if (srcAge > SBX_MAX_SOURCE_AGE_MIN) return;
    var buildStamp = b.built_at || b.asof;
    var buildAge = buildStamp
      ? (Date.now() - new Date(buildStamp).getTime()) / 60000 : NaN;
    if (!isFinite(buildAge) || buildAge > SBX_MAX_SOURCE_AGE_MIN) return;
    var n = c.n || (c.adv + c.dec + (c.unch || 0)) || 1;
    var unch = (typeof c.unch === "number") ? c.unch : Math.max(0, n - c.adv - c.dec);
    var den = (c.adv + c.dec + unch) || 1;
    sbxSet("sbx-adv", c.adv.toLocaleString("en-US"));
    sbxSet("sbx-dec", c.dec.toLocaleString("en-US"));
    var ba = document.getElementById("sbx-bar-a"), bu = document.getElementById("sbx-bar-u"), bd = document.getElementById("sbx-bar-d");
    if (ba) ba.style.width = (100 * c.adv / den).toFixed(1) + "%";
    if (bu) bu.style.width = (100 * unch / den).toFixed(1) + "%";
    if (bd) bd.style.width = (100 * c.dec / den).toFixed(1) + "%";
    if (typeof c.pa50 === "number") {
      sbxSet("sbx-v50", Math.round(c.pa50) + "%");
      var wl50 = document.getElementById("sbx-wl50");
      if (wl50) { wl50.classList.toggle("low", c.pa50 < 50); wl50.firstElementChild.style.width = Math.round(c.pa50) + "%"; }
      sbxSet("sbx-w50", sbxBi(c.pa50 >= 60 ? SBX_WORDS.w50hi : (c.pa50 <= 40 ? SBX_WORDS.w50lo : SBX_WORDS.w50mid)));
    }
    if (typeof c.pa200 === "number") {
      sbxSet("sbx-v200", Math.round(c.pa200) + "%");
      var wl2 = document.getElementById("sbx-wl200");
      if (wl2) { wl2.classList.toggle("low", c.pa200 < 50); wl2.firstElementChild.style.width = Math.round(c.pa200) + "%"; }
      sbxSet("sbx-w200", sbxBi(c.pa200 >= 50 ? SBX_WORDS.w200ok : SBX_WORDS.w200bad));
    }
    if (typeof c.net_nh === "number") {
      var nnh = document.getElementById("sbx-nnh");
      if (nnh) {
        nnh.textContent = (c.net_nh >= 0 ? "+" : "−") + Math.abs(c.net_nh);
        nnh.classList.toggle("pos", c.net_nh >= 0); nnh.classList.toggle("neg", c.net_nh < 0);
      }
      sbxSet("sbx-nnhw", sbxBi(c.net_nh >= 0 ? SBX_WORDS.nnhup : SBX_WORDS.nnhdn));
    }
    var st = (typeof c.pa50 === "number" && c.pa50 >= 60 && c.net_nh >= 0) ? SBX_STANCE.broad
           : ((typeof c.pa50 === "number" && c.pa50 <= 40) || c.net_nh < 0) ? SBX_STANCE.thin
           : SBX_STANCE.mixed;
    var sl = document.getElementById("sbx-stance-l");
    if (sl) { sl.innerHTML = sbxBi(st.l); sl.className = st.tone; }
    sbxSet("sbx-stance-v", sbxBi(st.v));
    var stamp = document.getElementById("sbx-stamp");
    if (stamp) {
      stamp.classList.add("live");
      var et = new Date(b.source_asof).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", timeZone: "America/New_York" });
      var dm = (typeof b.delay_min === "number" && isFinite(b.delay_min))
        ? Math.max(b.delay_min, Math.round(srcAge)) : Math.round(srcAge);
      stamp.innerHTML = '<span class="sbx-dot"></span>' +
        sbxBi(["≈" + dm + "-min delayed · " + et + " ET", "约" + dm + "分钟延迟 · 美东 " + et]);
    }
  }
  /* SBX-BREADTH-CONTRACT-END */

  function paintLabel() {
    var zh = document.documentElement.getAttribute("data-lang") === "zh";
    var lab = (zh && window.LIVE_FEED_LABEL_ZH) || FEED_LABEL;
    if (!lab) return;
    [].slice.call(document.querySelectorAll("[data-live-label]"))
      .forEach(function (el) { el.textContent = lab; el.title = lab; });
  }

  // ── Live Tape websocket (same-origin /ws/tape) ────────────────────────────
  function _wsFresher(sym, now) {
    var t = _wsLast[sym];
    return t != null && (now - t) < WS_FRESH_MS;
  }
  function _pageHasTapeSym() {
    var found = false;
    symNodes().forEach(function (el) { if (TAPE_SYMS[rawSym(el)]) found = true; });
    return found;
  }
  function _applyWsQuote(q) {
    if (!q || !q.sym) return;
    if (!TAPE_SYMS[q.sym]) return;
    if (q.price == null) {
      patchSymbol(q.sym, { price: null, src: null, stale: true, ageMin: null,
                           delayFloor: null, chg: null, prevClose: null, basis: q.basis || "quote" },
                  null, null);
      return;
    }
    var basis = q.basis || "quote";
    var prevTs = _wsLast[q.sym + "|ts"] || 0;
    var prevBasis = _wsLast[q.sym + "|basis"];
    if (q.ts && basis === prevBasis && q.ts < prevTs) return;
    var now = Date.now();
    _wsLast[q.sym] = now;
    if (q.ts) _wsLast[q.sym + "|ts"] = q.ts;
    _wsLast[q.sym + "|basis"] = basis;
    var ageMin = q.ts ? Math.max(0, (now - q.ts) / 60000) : 0;
    var r = {
      price: q.price, src: "ws:" + (q.basis || "quote"),
      invalidClock: invalidQuoteClock(q.ts, q.tsSynthetic, now),
      quoteTs: q.tsSynthetic === true ? null : quoteTime(q.ts),
      stale: ageMin > STALE_MIN, ageMin: ageMin, delayFloor: null,
      chg: (q.chgPct != null) ? q.chgPct : null,
      prevClose: (q.prevClose != null) ? q.prevClose : null,
      basis: q.basis || "quote"
    };
    patchSymbol(q.sym, r, null, null);
  }
  function _tapeWsUrl() {
    try {
      var proto = (location.protocol === "https:") ? "wss:" : "ws:";
      return proto + "//" + location.host + "/ws/tape";
    } catch (e) { return null; }
  }
  function startTape() {
    if (!WS_TAPE) return;
    if (_wsClosed || _wsSock) return;
    if (!("WebSocket" in window)) return;
    if (!_pageHasTapeSym()) return;
    var url = _tapeWsUrl();
    if (!url) return;
    var sock;
    try { sock = new WebSocket(url); }
    catch (e) { return; }
    _wsSock = sock;
    sock.onmessage = function (ev) {
      var msg;
      try { msg = JSON.parse(ev.data); } catch (e) { return; }
      if (!msg || msg.type === "heartbeat") return;
      if (document.hidden) return;
      _applyWsQuote(msg);
    };
    sock.onopen = function () { _wsRetry = 0; };
    sock.onclose = function () { _wsSock = null; _scheduleWsReconnect(); };
    sock.onerror = function () { try { sock.close(); } catch (e) {} };
  }
  function _scheduleWsReconnect() {
    if (_wsClosed || _paused) return;
    if (_wsTimer) clearTimeout(_wsTimer);
    var delay = Math.min(30000, 1000 * Math.pow(2, _wsRetry++));
    _wsTimer = setTimeout(function () { if (!document.hidden) startTape(); }, delay);
  }
  function stopTape() {
    _wsClosed = true;
    if (_wsTimer) { clearTimeout(_wsTimer); _wsTimer = null; }
    if (_wsSock) { try { _wsSock.close(); } catch (e) {} _wsSock = null; }
  }

  function _startTimer() {
    if (_timer) clearInterval(_timer);
    _timer = setInterval(tick, POLL);
  }

  function start() {
    injectStyle();
    paintLabel();
    document.addEventListener("langchange", paintLabel);
    window.LiveQuotes = {
      refresh: function () {
        if (_paused) return;
        if (inflight) pendingRefresh = true; else tick();
      },
      pause: function () {
        _paused = true;
        if (_timer) { clearInterval(_timer); _timer = null; }
        stopTape();
      },
      resume: function () {
        _paused = false;
        _wsClosed = false;
        _startTimer();
        tick();
        startTape();
      }
    };
    try { localStorage.removeItem("liveOff"); } catch (e) {}
    if (!_paused) {
      tick();
      _startTimer();
      startTape();
    }
    document.addEventListener("visibilitychange", function () {
      if (!document.hidden && !_paused) { tick(); if (!_wsSock) { _wsClosed = false; startTape(); } }
    });
  }
  if (document.readyState !== "loading") start();
  else document.addEventListener("DOMContentLoaded", start);
})();
