/* mastermind.js — renders the governed Portfolio/Mastermind point-in-time snapshot.
   The JSON remains tier-gated; this presentation script is public so an anonymous
   shell can explain whether sign-in, upgrade, freshness, or availability is blocking
   the data. Paper-only / display-only — never a signal. */
(function () {
  "use strict";

  var CANONICAL_LIVE_URL = "https://bot.mastermind-x.com";
  var STALE_AFTER_HOURS = 72; // covers the normal weekend gap without hiding a stopped publisher
  var SNAP = null, ACTIVE = null, LOAD_STATE = { kind: "loading", href: "" };

  var LBL = {
    en: {
      nav: "Book value", ret: "Total return", vs: "vs", day: "Day", mdd: "Max drawdown",
      invested: "Invested", cash: "Cash", regime: "Regime", asof: "as of", perf: "Performance",
      alloc: "Allocation", positions: "Positions", decisions: "Recent decisions",
      track: "Track record", trades: "decisions logged", hit: "hit rate", brier: "Brier",
      skill: "skill", status: "status", pending: "pending", hold: "hold",
      colT: "Ticker", colW: "Weight", colS: "Sleeve", colRS: "RS %ile", colSt: "Status",
      equity: "Equity curve", book: "book", bench: "benchmark", building: "building — too few decided to grade",
      empty: "No book has been published yet.",
      off: "The Portfolio snapshot is unavailable. The live Portfolio product may still be current.",
      leadership: "Leadership", conviction: "Conviction", none: "—",
      open: "Open", closed: "Closed", active: "Active", archived: "Archived",
      archivedBook: "Archived book", supersededBy: "Superseded by", archivedReason: "Reason",
      fresh: "Snapshot current", stale: "Stale snapshot", unknownFreshness: "Snapshot time unavailable",
      generated: "Generated", staleDetail: "These are last-known bytes; verify the live Portfolio dashboard before relying on them.",
      signinTitle: "Sign in to view the Portfolio snapshot",
      signinBody: "The page shell is public, but the portfolio payload is protected.",
      signinAction: "Sign in",
      upgradeTitle: "Portfolio snapshot requires Pro",
      upgradeBody: "Upgrade access to load positions, decisions, and paper-book performance.",
      upgradeAction: "View plans",
      unavailableTitle: "Portfolio snapshot unavailable",
      unavailableBody: "The protected snapshot could not be loaded. The live Portfolio dashboard remains the source of truth.",
      liveAction: "Open live Portfolio"
    },
    zh: {
      nav: "账本市值", ret: "总回报", vs: "对比", day: "当日", mdd: "最大回撤",
      invested: "已投资", cash: "现金", regime: "市场格局", asof: "截至", perf: "业绩",
      alloc: "仓位分配", positions: "持仓", decisions: "近期决策",
      track: "战绩", trades: "条决策记录", hit: "胜率", brier: "Brier", skill: "技巧",
      status: "状态", pending: "待成交", hold: "持有",
      colT: "代码", colW: "权重", colS: "策略槽", colRS: "RS 百分位", colSt: "状态",
      equity: "净值曲线", book: "账本", bench: "基准", building: "构建中 — 已决策样本过少",
      empty: "尚未发布账本。",
      off: "Portfolio 快照暂不可用；实时 Portfolio 产品仍可能保持最新。",
      leadership: "领涨", conviction: "信念", none: "—",
      open: "开市", closed: "休市", active: "运行中", archived: "已归档",
      archivedBook: "已归档账本", supersededBy: "后继账本", archivedReason: "原因",
      fresh: "快照为当前版本", stale: "快照已过期", unknownFreshness: "快照时间不可用",
      generated: "生成时间", staleDetail: "这是最后已知数据；使用前请在实时 Portfolio 面板核实。",
      signinTitle: "登录以查看 Portfolio 快照",
      signinBody: "页面外壳公开，但组合数据受保护。",
      signinAction: "登录",
      upgradeTitle: "Portfolio 快照需要 Pro",
      upgradeBody: "升级后可查看持仓、决策与模拟账本业绩。",
      upgradeAction: "查看方案",
      unavailableTitle: "Portfolio 快照不可用",
      unavailableBody: "受保护的快照无法加载；实时 Portfolio 面板仍是事实来源。",
      liveAction: "打开实时 Portfolio"
    }
  };

  function language(lang) { return lang === "zh" ? "zh" : "en"; }

  function safeLiveUrl(value) {
    try {
      var parsed = new URL(String(value || ""));
      if (parsed.protocol === "https:" && parsed.hostname === "bot.mastermind-x.com") {
        return CANONICAL_LIVE_URL;
      }
    } catch (e) { /* fall through to the governed product origin */ }
    return CANONICAL_LIVE_URL;
  }

  function formatMarketStatus(status, lang) {
    var L = LBL[language(lang)];
    if (status == null || status === "") return "";
    if (typeof status === "string" || typeof status === "number") return String(status);
    if (typeof status !== "object") return "";

    var venue = status.venue || status.exchange || status.market || "";
    var state = "";
    if (typeof status.open === "boolean") state = status.open ? L.open : L.closed;
    else if (typeof status.is_open === "boolean") state = status.is_open ? L.open : L.closed;
    else if (typeof status.label === "string") state = status.label;
    else if (typeof status.status === "string") state = status.status;

    return [venue, state].filter(Boolean).join(" · ");
  }

  function snapshotFreshness(generatedAt, nowMs) {
    var stamp = Date.parse(String(generatedAt || ""));
    var now = typeof nowMs === "number" ? nowMs : Date.now();
    if (!isFinite(stamp) || !isFinite(now)) return { state: "unknown", ageHours: null };
    var ageHours = (now - stamp) / 3600000;
    if (ageHours < -1) return { state: "unknown", ageHours: ageHours };
    return {
      state: ageHours > STALE_AFTER_HOURS ? "stale" : "fresh",
      ageHours: ageHours
    };
  }

  function accessState(status, body, lang) {
    body = body && typeof body === "object" ? body : {};
    if (Number(status) === 401) return { kind: "signin", href: body.signin_url || "/?signin=1" };
    if (Number(status) === 403) return { kind: "upgrade", href: body.upgrade_url || "/plans.html?upgrade=1&plan=pro" };
    return { kind: "unavailable", href: "" };
  }

  function bookLifecycle(book, lang) {
    book = book && typeof book === "object" ? book : {};
    var L = LBL[language(lang)];
    var archived = book.archived === true || book.active === false || book.status === "archived";
    return {
      archived: archived,
      label: archived ? L.archived : L.active,
      supersededBy: archived ? (book.superseded_by || "") : "",
      reason: archived ? (book.archived_reason || "") : ""
    };
  }

  var TEST_API = {
    safeLiveUrl: safeLiveUrl,
    formatMarketStatus: formatMarketStatus,
    snapshotFreshness: snapshotFreshness,
    accessState: accessState,
    bookLifecycle: bookLifecycle
  };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = TEST_API;
    return;
  }

  function esc(s) {
    var d = document.createElement("div");
    d.textContent = (s == null ? "" : String(s));
    return d.innerHTML;
  }
  function curLang() { return document.documentElement.getAttribute("data-lang") === "zh" ? "zh" : "en"; }
  function tt() { return LBL[curLang()]; }

  function pct(x, dp) {
    if (x == null || isNaN(x)) return "—";
    return Number(x).toFixed(dp == null ? 2 : dp) + "%";
  }
  function signed(x) {
    if (x == null || isNaN(x)) return { txt: "—", cls: "" };
    var v = Number(x);
    return { txt: (v > 0 ? "+" : "") + v.toFixed(2) + "%", cls: v > 0 ? "up" : (v < 0 ? "down" : "") };
  }
  function money(x) {
    if (x == null || isNaN(x)) return "—";
    return "$" + Math.round(Number(x)).toLocaleString("en-US");
  }
  function span(cls, txt) { return '<span class="' + cls + '">' + esc(txt) + "</span>"; }

  function formatStamp(raw) {
    var d = new Date(raw || "");
    if (isNaN(d.getTime())) return "";
    try {
      return d.toLocaleString(curLang() === "zh" ? "zh-CN" : "en-US", {
        year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
        timeZoneName: "short"
      });
    } catch (e) {
      return d.toISOString();
    }
  }

  function statePanel(kind) {
    var L = tt(), title, body, action = "", href = LOAD_STATE.href || "";
    if (kind === "signin") {
      title = L.signinTitle; body = L.signinBody;
      action = '<a class="live-btn" href="' + esc(href) + '">' + esc(L.signinAction) + "</a>";
    } else if (kind === "upgrade") {
      title = L.upgradeTitle; body = L.upgradeBody;
      action = '<a class="live-btn" href="' + esc(href) + '">' + esc(L.upgradeAction) + "</a>";
    } else if (kind === "loading") {
      title = curLang() === "zh" ? "正在加载 Portfolio 快照…" : "Loading the Portfolio snapshot…";
      body = "";
    } else {
      title = L.unavailableTitle; body = L.unavailableBody;
      action = '<a class="live-btn" href="' + CANONICAL_LIVE_URL + '" target="_blank" rel="noopener">↗ ' +
        esc(L.liveAction) + "</a>";
    }
    return '<div class="panel mm-empty mm-access mm-access-' + esc(kind) + '"><h2>' + esc(title) + "</h2>" +
      (body ? '<p class="muted sm">' + esc(body) + "</p>" : "") + action + "</div>";
  }

  function renderSnapshotState() {
    var state = document.getElementById("mm-state");
    if (!state) return;
    if (!SNAP) { state.innerHTML = ""; return; }
    var L = tt(), freshness = snapshotFreshness(SNAP.generated_at, Date.now());
    var stamp = formatStamp(SNAP.generated_at);
    if (freshness.state === "fresh") {
      state.innerHTML = '<div class="mm-notice mm-notice-fresh"><strong>' + esc(L.fresh) + "</strong>" +
        (stamp ? " · " + esc(L.generated + ": " + stamp) : "") + "</div>";
    } else if (freshness.state === "stale") {
      state.innerHTML = '<div class="mm-notice mm-notice-stale"><strong>' + esc(L.stale) + "</strong>" +
        (stamp ? " · " + esc(L.generated + ": " + stamp) : "") +
        '<div class="sm">' + esc(L.staleDetail) + "</div></div>";
    } else {
      state.innerHTML = '<div class="mm-notice mm-notice-stale"><strong>' + esc(L.unknownFreshness) + "</strong>" +
        '<div class="sm">' + esc(L.staleDetail) + "</div></div>";
    }
  }

  // ---- sparkline (nav vs benchmark) -------------------------------------
  function sparkline(series, benchSym) {
    if (!series || series.length < 2) return "";
    var W = 640, H = 90, P = 4;
    var navs = [], bens = [];
    for (var i = 0; i < series.length; i++) {
      var n = Number(series[i].nav); if (!isNaN(n)) navs.push(n);
      var b = Number(series[i].spy_nav); if (!isNaN(b)) bens.push(b);
    }
    var all = navs.concat(bens), lo = Math.min.apply(null, all), hi = Math.max.apply(null, all);
    if (!(hi > lo)) hi = lo + 1;
    function pathFor(arr) {
      var pts = [];
      for (var k = 0; k < arr.length; k++) {
        var x = P + (W - 2 * P) * (k / (arr.length - 1));
        var y = P + (H - 2 * P) * (1 - (arr[k] - lo) / (hi - lo));
        pts.push(x.toFixed(1) + "," + y.toFixed(1));
      }
      return pts.join(" ");
    }
    var s = '<svg class="spark" viewBox="0 0 ' + W + " " + H + '" width="100%" height="' + H +
      '" preserveAspectRatio="none" role="img">';
    if (bens.length > 1)
      s += '<polyline points="' + pathFor(bens) + '" fill="none" stroke="var(--muted)" stroke-width="1.4" stroke-dasharray="4 3" opacity="0.8"/>';
    if (navs.length > 1)
      s += '<polyline points="' + pathFor(navs) + '" fill="none" stroke="var(--link)" stroke-width="2"/>';
    s += "</svg>";
    var L = tt();
    s += '<div class="spark-leg"><span style="color:var(--ink-link, var(--link))">▬ ' + esc(L.book) +
      '</span> &nbsp; <span style="color:var(--muted)">┄ ' + esc(benchSym || L.bench) + "</span></div>";
    return '<div class="sparkwrap">' + s + "</div>";
  }

  function archiveNote(b) {
    var L = tt(), life = bookLifecycle(b, curLang());
    if (!life.archived) return "";
    var detail = [];
    if (life.supersededBy) detail.push(L.supersededBy + ": " + life.supersededBy);
    if (life.reason) detail.push(L.archivedReason + ": " + life.reason);
    return '<div class="mm-archive-note"><strong>' + esc(L.archivedBook) + "</strong>" +
      (detail.length ? " · " + esc(detail.join(" · ")) : "") + "</div>";
  }

  function perfPanel(b) {
    var L = tt(), p = b.performance || {};
    var ret = signed(p.total_return_pct), vs = signed(p.vs_spy_pct), day = signed(p.day_change_pct);
    var stat = function (k, vhtml) { return '<div class="mm-stat"><div class="k">' + esc(k) + '</div><div class="v">' + vhtml + "</div></div>"; };
    var grid = '<div class="mm-stats">' +
      stat(L.nav, esc(money(p.current_nav))) +
      stat(L.ret, span(ret.cls, ret.txt)) +
      stat(L.vs + " " + (b.benchmark || "SPY"), span(vs.cls, vs.txt)) +
      stat(L.day, span(day.cls, day.txt)) +
      stat(L.mdd, esc(p.max_drawdown_pct != null ? "-" + Math.abs(p.max_drawdown_pct).toFixed(2) + "%" : "—")) +
      "</div>";
    var marketText = formatMarketStatus(b.market_status, curLang());
    var sub = '<div class="muted sm" style="margin:8px 0 10px">' +
      (b.as_of ? esc(L.asof + " " + b.as_of) : "") +
      (marketText ? " · " + esc(marketText) : "") +
      (b.regime && b.regime.quad_name ? " · " + esc(L.regime + ": " + b.regime.quad_name +
        (b.regime.liquidity_overlay ? " / " + b.regime.liquidity_overlay : "")) : "") + "</div>";
    return '<div class="panel"><h2>' + esc(L.perf) + ' — ' + esc(b.name || b.id) + "</h2>" +
      archiveNote(b) + grid + sub + sparkline(p.series, b.benchmark) + "</div>";
  }

  var SLEEVE_COLORS = { leadership: "var(--link)", conviction: "var(--up)", cash: "var(--muted)" };
  function allocPanel(b) {
    var L = tt(), sl = b.sleeves || {};
    var keys = Object.keys(sl);
    if (!keys.length) return "";
    var bar = '<div class="mm-bar">', leg = '<div class="mm-legend">';
    keys.forEach(function (k) {
      var w = Number(sl[k]) || 0, col = SLEEVE_COLORS[k] || "var(--card)";
      var label = L[k] || (k.charAt(0).toUpperCase() + k.slice(1));
      bar += '<span style="width:' + (w * 100).toFixed(2) + "%;background:" + col + '"></span>';
      leg += '<span><i style="background:' + col + '"></i>' + esc(label) + " " + pct(w * 100, 1) + "</span>";
    });
    bar += "</div>"; leg += "</div>";
    return '<div class="panel"><h2>' + esc(L.alloc) + "</h2>" + bar + leg + "</div>";
  }

  function positionsPanel(b) {
    var L = tt(), pos = b.positions || [];
    if (!pos.length) return "";
    var rows = pos.map(function (p) {
      var st = p.pending ? '<span class="pill pend">' + esc(L.pending) + "</span>"
        : (p.verdict ? '<span class="pill ' + (p.verdict === "hold" ? "hold" : "") + '">' + esc(p.verdict) + "</span>" : "");
      return "<tr><td>" + esc(p.ticker || "") + '</td><td class="num">' + pct((Number(p.weight) || 0) * 100, 1) +
        "</td><td>" + esc(p.sleeve || "—") + '</td><td class="num">' +
        (p.rs_pctile != null ? esc(Number(p.rs_pctile).toFixed(0)) : "—") + "</td><td>" + st + "</td></tr>";
    }).join("");
    return '<div class="panel"><h2>' + esc(L.positions) + " (" + pos.length + ')</h2>' +
      '<table class="mm"><thead><tr><th>' + esc(L.colT) + '</th><th class="num">' + esc(L.colW) +
      '</th><th>' + esc(L.colS) + '</th><th class="num">' + esc(L.colRS) + '</th><th>' + esc(L.colSt) +
      "</th></tr></thead><tbody>" + rows + "</tbody></table></div>";
  }

  function decisionsPanel(b) {
    var L = tt(), dec = (b.decisions || []).slice(0, 12);
    if (!dec.length) return "";
    var items = dec.map(function (d) {
      var conv = [d.lean, d.conviction].filter(Boolean).join(" · ");
      var prob = d.prob_correct != null ? " · p=" + Number(d.prob_correct).toFixed(2) : "";
      var hz = d.horizon_d != null ? " · " + d.horizon_d + "d" : "";
      return '<div class="mm-dec"><div class="h">' + esc(d.subject || d.id || "") +
        ' <span class="muted sm">' + esc(conv + prob + hz) + "</span></div>" +
        (d.thesis ? '<div class="muted sm">' + esc(d.thesis) + "</div>" : "") + "</div>";
    }).join("");
    return '<div class="panel"><h2>' + esc(L.decisions) + "</h2>" + items + "</div>";
  }

  function trackPanel(b) {
    var L = tt(), tr = b.track_record || {};
    var parts = [esc((tr.n != null ? tr.n : 0) + " " + L.trades)];
    if (tr.hit_rate != null) parts.push(esc(L.hit + " " + (Number(tr.hit_rate) * 100).toFixed(0) + "%"));
    if (tr.brier != null) parts.push(esc(L.brier + " " + Number(tr.brier).toFixed(3)));
    if (tr.skill != null) parts.push(esc(L.skill + " " + Number(tr.skill).toFixed(3)));
    var statusTxt = (tr.status === "building" || tr.n === 0) ? L.building : (tr.status || "");
    return '<div class="panel"><h2>' + esc(L.track) + '</h2><div class="sm">' + parts.join(" · ") +
      (statusTxt ? ' · <span class="muted">' + esc(statusTxt) + "</span>" : "") + "</div></div>";
  }

  function renderTabs() {
    var wrap = document.getElementById("mm-tabs");
    if (!wrap || !SNAP || !SNAP.books) return;
    wrap.innerHTML = SNAP.books.map(function (b) {
      var life = bookLifecycle(b, curLang());
      return '<button class="mm-tab-btn' + (b.id === ACTIVE ? " active" : "") + '" data-book="' + esc(b.id) +
        '" role="tab" aria-selected="' + (b.id === ACTIVE ? "true" : "false") + '">' + esc(b.name || b.id) +
        (b.tagline ? '<span class="tl">' + esc(b.tagline) + "</span>" : "") +
        '<span class="life' + (life.archived ? " archived" : "") + '">' + esc(life.label) + "</span></button>";
    }).join("");
    var btns = wrap.querySelectorAll(".mm-tab-btn");
    for (var i = 0; i < btns.length; i++) {
      btns[i].addEventListener("click", function () { ACTIVE = this.getAttribute("data-book"); render(); });
    }
  }

  function selectDefaultBook() {
    var books = SNAP && SNAP.books ? SNAP.books : [];
    var byId = {};
    books.forEach(function (b) { byId[b.id] = b; });
    if (ACTIVE && byId[ACTIVE]) return ACTIVE;
    if (SNAP.default_book && byId[SNAP.default_book] && !bookLifecycle(byId[SNAP.default_book], curLang()).archived) {
      return SNAP.default_book;
    }
    for (var i = 0; i < books.length; i++) {
      if (!bookLifecycle(books[i], curLang()).archived) return books[i].id;
    }
    return books.length ? books[0].id : null;
  }

  function render() {
    var root = document.getElementById("mm-root");
    var tabs = document.getElementById("mm-tabs");
    if (!root) return;

    if (!SNAP) {
      if (tabs) tabs.innerHTML = "";
      renderSnapshotState();
      root.innerHTML = statePanel(LOAD_STATE.kind || "unavailable");
      return;
    }
    renderSnapshotState();
    if (!SNAP.books || !SNAP.books.length) {
      if (tabs) tabs.innerHTML = "";
      root.innerHTML = '<div class="panel mm-empty">' + esc(tt().empty) + "</div>";
      return;
    }
    ACTIVE = selectDefaultBook();
    renderTabs();
    var book = SNAP.books.filter(function (b) { return b.id === ACTIVE; })[0];
    root.innerHTML = perfPanel(book) + allocPanel(book) + positionsPanel(book) +
      decisionsPanel(book) + trackPanel(book);

    var live = document.getElementById("mm-live");
    if (live) live.setAttribute("href", safeLiveUrl(SNAP.live_url));
  }

  function loadSnapshot() {
    LOAD_STATE = { kind: "loading", href: "" };
    render();
    fetch("mastermind/mastermind_snapshot.json?_=" + Date.now(), {
      credentials: "same-origin",
      cache: "no-store"
    }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (body) {
        if (!response.ok) {
          SNAP = null;
          LOAD_STATE = accessState(response.status, body, curLang());
          render();
          return;
        }
        if (!body || typeof body !== "object" || !Array.isArray(body.books)) {
          SNAP = null;
          LOAD_STATE = { kind: "unavailable", href: "" };
          render();
          return;
        }
        SNAP = body;
        LOAD_STATE = { kind: "data", href: "" };
        render();
      });
    }).catch(function () {
      SNAP = null;
      LOAD_STATE = { kind: "unavailable", href: "" };
      render();
    });
  }

  document.addEventListener("langchange", render);
  loadSnapshot();
})();
