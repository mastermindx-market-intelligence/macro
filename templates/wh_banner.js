/* Market alert ticker — a Wall-Street-style scrolling tape pinned to the top of
   every page. Fully client-side and self-contained. It hosts TWO channels:

     • WHITE HOUSE ALERT (blue/red)  — fetched from wh_banner.json
         (built by scripts/build_whitehouse.py from the WH RSS + LLM brain).
     • RISK RADAR ALERT (deep red)     — fetched from rr_banner.json
         (built by scripts/build_rr_banner.py; fires only at the radar's EXTREME,
          gate-confirmed "risk-off" band — the get-out-now tier, not every reading).

   A published severe Risk Radar alert takes precedence over the news tape. It
   stays visible after acknowledgement and does not scroll or alternate away.
   The issue date remains explicit: this legacy feed is not a freshness proof.
   News-only dismissal is unchanged. The new multi-market warning projection is
   not activated by this bounded client repair; its publisher/consumer rollout
   and long-open-page refresh remain separate release work.

   Degrade-silent: no file, no alerts, or any error → nothing renders. The page is
   never blocked (loaded `defer`), and all model-derived text is written via
   textContent (never innerHTML) so a headline can never inject markup.

   The injector sets data-root on this script tag to the site-root-relative prefix
   ("" at root, "../" one level deep) so fetch + links resolve from any page depth. */
(function () {
  "use strict";

  var ALT_MS = 9000; // dwell time per channel when both are live

  function boot() {
    var self =
      document.currentScript ||
      document.querySelector("script[data-whb]") ||
      (function () {
        var s = document.getElementsByTagName("script");
        for (var i = s.length - 1; i >= 0; i--) {
          if ((s[i].src || "").indexOf("wh_banner.js") !== -1) return s[i];
        }
        return null;
      })();
    var root = (self && self.getAttribute("data-root")) || "";
    if (root && root.slice(-1) !== "/") root += "/";

    Promise.all([
      getJSON(root + "wh_banner.json"),
      getJSON(root + "rr_banner.json"),
    ]).then(function (res) {
      render(res[0], res[1], root);
    });
  }

  function getJSON(url) {
    return fetch(url, { cache: "no-cache" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; });
  }

  function render(whData, rrData, root) {
    var reduce =
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // Build the candidate channels, each already filtered by its own dismissal.
    var channels = [];
    var wh = whChannel(whData, root, reduce);
    if (wh) channels.push(wh);
    var rr = rrChannel(rrData, root, reduce);
    if (rr) channels.unshift(rr);
    // A critical warning must not rotate out or be hidden behind the first news
    // channel in reduced-motion mode. News remains available on its own page.
    if (rr && rr.critical) channels = [rr];
    if (!channels.length) return;

    injectStyle();

    var bar = el("div", "whb");
    bar.setAttribute("role", "region");
    bar.setAttribute("aria-label", "Market alert");

    var stage = el("div", "whb-stage" + (channels.length > 1 ? " multi" : ""));
    var faces = channels.map(function (c) {
      var face = el("div", "whb-face whb-face-" + c.kind);
      face.appendChild(c.label);
      face.appendChild(c.view);
      stage.appendChild(face);
      return face;
    });
    bar.appendChild(stage);

    // Severe warnings can be acknowledged, not erased by a routine dismissal.
    // News-only dismissal retains its existing monotonic behaviour.
    var requiresAcknowledgement = channels.some(function (c) { return !!c.critical; });
    var close = txt("button", "whb-x", requiresAcknowledgement ? "✓" : "×");
    if (requiresAcknowledgement) close.setAttribute("aria-pressed", "false");
    function syncCloseLabel() {
      close.setAttribute(
        "aria-label",
        document.documentElement.getAttribute("data-lang") === "zh"
          ? (requiresAcknowledgement ? "确认风险警告（保持显示）" : "关闭市场提醒")
          : (requiresAcknowledgement ? "Acknowledge risk warning (keep visible)" : "Dismiss market alert")
      );
    }
    syncCloseLabel();
    document.addEventListener("langchange", syncCloseLabel);
    close.addEventListener("click", function (ev) {
      ev.stopPropagation();
      if (requiresAcknowledgement) {
        close.setAttribute("aria-pressed", "true");
        bar.classList.add("whb-acknowledged");
        return;
      }
      channels.forEach(function (c) { c.dismiss(); });
      bar.parentNode && bar.parentNode.removeChild(bar);
      document.documentElement.classList.remove("whb-on");
      document.removeEventListener("langchange", syncCloseLabel);
      if (close._whbResize) window.removeEventListener("resize", close._whbResize);
      if (bar._whbTimer) clearInterval(bar._whbTimer);
    });
    bar.appendChild(close);

    document.body.insertBefore(bar, document.body.firstChild);
    document.documentElement.classList.add("whb-on");

    // apply the first (or only) channel's accent, then start alternation if needed
    applyAccent(bar, channels[0]);
    faces[0].classList.add("is-active");
    if (channels.length > 1 && !reduce && !channels[0].critical) startAlternation(bar, faces, channels);

    fullBleed(bar, close);
    scaleDurations(bar, reduce);
  }

  // ---------------------------------------------------------------------------
  // WHITE HOUSE channel — unchanged behaviour: a tape of the live WH alerts.
  // ---------------------------------------------------------------------------
  function whChannel(data, root, reduce) {
    if (!data || !Array.isArray(data.alerts) || !data.alerts.length) return null;
    var now = Date.now();
    var alerts = data.alerts.filter(function (a) {
      if (!a || !a.title) return false;
      var exp = a.expires_at ? Date.parse(a.expires_at) : NaN;
      return isNaN(exp) || now < exp; // defensive: server already prunes expired
    });
    if (!alerts.length) return null;

    // Monotonic dismissal: stay hidden only while EVERY currently-live alert was
    // already dismissed. A NEW alert re-opens; an old one expiring must not.
    var dismissed = readDismissed("whb_dismissed");
    if (alerts.every(function (a) { return dismissed[a.id]; })) return null;

    var label = el("a", "whb-label whb-label-wh");
    label.href = root + "whitehouse.html";
    label.appendChild(el("span", "whb-dot"));
    var lt = el("span", "whb-label-tx");
    lt.appendChild(txt("span", "whb-en", "WHITE HOUSE ALERT"));
    lt.appendChild(txt("span", "whb-zh", "白宫警报"));
    label.appendChild(lt);

    var view = el("div", "whb-view");
    var track = el("div", "whb-track" + (reduce ? " whb-static" : ""));
    track.appendChild(buildWhRun(alerts, root));
    if (!reduce) track.appendChild(buildWhRun(alerts, root)); // 2nd copy → seamless
    view.appendChild(track);

    return {
      kind: "wh",
      label: label,
      view: view,
      top: "linear-gradient(90deg,#3d6fd6,#d9a441 50%,#d2455c)",
      dismiss: function () {
        try {
          alerts.forEach(function (a) { dismissed[a.id] = 1; });
          localStorage.setItem(
            "whb_dismissed", Object.keys(dismissed).sort().join("|"));
        } catch (e) {}
      },
    };
  }

  // one pass of the WH tape: every alert as a clickable segment
  function buildWhRun(alerts, root) {
    var run = el("div", "whb-run");
    alerts.forEach(function (a, i) {
      var seg = el("a", "whb-seg");
      seg.href = root + "whitehouse.html#" + encodeURIComponent(a.id || "");
      seg.appendChild(el("span", "whb-pipe whb-tone-" + (a.tone || "neutral")));
      var ttl = el("span", "whb-ttl");
      ttl.appendChild(txt("span", "whb-en", a.title));
      ttl.appendChild(txt("span", "whb-zh", a.title_zh || a.title));
      seg.appendChild(ttl);
      (a.tickers || []).slice(0, 6).forEach(function (t) {
        if (!t || !t.symbol) return;
        var chip = el("span", "whb-chip");
        chip.appendChild(
          txt("span", "whb-sym", t.symbol + (t.direction === "hurt" ? " ▾" : " ▴"))
        );
        if (t.chg_pct !== null && t.chg_pct !== undefined && !isNaN(t.chg_pct)) {
          var up = Number(t.chg_pct) >= 0;
          chip.appendChild(
            txt("span", "whb-chg " + (up ? "up" : "dn"),
              (up ? "+" : "") + Number(t.chg_pct).toFixed(2) + "%")
          );
        }
        seg.appendChild(chip);
      });
      run.appendChild(seg);
      if (i < alerts.length - 1) run.appendChild(txt("span", "whb-div", "◆"));
    });
    return run;
  }

  // ---------------------------------------------------------------------------
  // RISK RADAR channel — a steady, dated notice for the legacy extreme feed.
  // No forecast, score threshold or producer authority changes here.
  // ---------------------------------------------------------------------------
  function rrChannel(data, root, reduce) {
    var a = data && data.alert;
    if (!a || !a.headline_en) return null;

    // Older dismissal records must not erase a still-published severe warning.
    // The legacy producer is US-only; never accept an arbitrary payload URL.
    var href = root + "macro.html";
    var label = el("a", "whb-label whb-label-rr");
    label.href = href;
    label.appendChild(el("span", "whb-dot"));
    var lt = el("span", "whb-label-tx");
    lt.appendChild(txt("span", "whb-en", "RISK RADAR ALERT"));
    lt.appendChild(txt("span", "whb-zh", "风险雷达警报"));
    label.appendChild(lt);

    var view = el("div", "whb-view whb-risk-view");
    var summary = el("a", "whb-risk-summary");
    summary.href = href;
    summary.appendChild(biTxt("whb-ttl", "⚠ " + a.headline_en,
      "⚠ " + (a.headline_zh || a.headline_en)));
    var sourceDate = a.asof != null ? a.asof : data.asof;
    var issued = null;
    if (typeof sourceDate === "string" && /^\d{4}-\d{2}-\d{2}$/.test(sourceDate)) {
      var parsed = new Date(sourceDate + "T00:00:00Z");
      if (!isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === sourceDate) issued = sourceDate;
    }
    summary.appendChild(biTxt("whb-issued",
      "Last issued " + (issued || "date unavailable") + " · Verify latest Risk Radar",
      "上次发布：" + (issued || "日期未知") + " · 请核对最新风险雷达"));
    view.appendChild(summary);

    return {
      kind: "rr", label: label, view: view,
      top: "linear-gradient(90deg,#d2455c,#a91e35)",
      critical: true,
      dismiss: function () {}, // acknowledgement is handled by the shared bar
    };
  }

  // ---------------------------------------------------------------------------
  // shared plumbing
  // ---------------------------------------------------------------------------
  function readDismissed(key) {
    var out = {};
    try {
      (localStorage.getItem(key) || "").split("|").forEach(function (id) {
        if (id) out[id] = 1;
      });
    } catch (e) {}
    return out;
  }

  function applyAccent(bar, ch) {
    bar.style.setProperty("--whb-top", ch.top);
    bar.classList.toggle("whb-warm", !!ch.warm);
    bar.classList.toggle("whb-critical", !!ch.critical);
  }

  function startAlternation(bar, faces, channels) {
    var idx = 0, paused = false;
    var timer = setInterval(function () {
      if (paused) return;
      faces[idx].classList.remove("is-active");
      idx = (idx + 1) % faces.length;
      faces[idx].classList.add("is-active");
      applyAccent(bar, channels[idx]);
    }, ALT_MS);
    bar._whbTimer = timer;
    bar.addEventListener("mouseenter", function () { paused = true; });
    bar.addEventListener("mouseleave", function () { paused = false; });
  }

  // Full-bleed: cancel whatever padding/margin the host <body> sets so the bar hugs
  // the very top and both edges — pages differ (0/18/24/28px tops, viewport gutters),
  // so read the resolved values and negate them; recompute on resize.
  function fullBleed(bar, close) {
    var onResize = function () {
      try {
        var cs = window.getComputedStyle(document.body);
        var v = function (p) { return parseFloat(cs[p]) || 0; };
        bar.style.marginTop = -(v("paddingTop") + v("marginTop")) + "px";
        bar.style.marginLeft = -(v("paddingLeft") + v("marginLeft")) + "px";
        bar.style.marginRight = -(v("paddingRight") + v("marginRight")) + "px";
        // Restore the width removed by the host gutters; max-width:100vw still
        // prevents the long news tape from expanding the document sideways.
        bar.style.width = "calc(100% + " + (v("paddingLeft") + v("marginLeft") +
          v("paddingRight") + v("marginRight")) + "px)";
      } catch (e) {}
    };
    onResize();
    window.addEventListener("resize", onResize);
    close._whbResize = onResize; // so dismissal can detach the listener
  }

  // Scale each tape's scroll DURATION to its content width so the reading pace
  // (~px/sec) stays constant whether one alert or six are live.
  function scaleDurations(bar, reduce) {
    if (reduce) return;
    var tracks = bar.querySelectorAll(".whb-track");
    for (var i = 0; i < tracks.length; i++) {
      var firstRun = tracks[i].querySelector(".whb-run");
      var w = firstRun ? firstRun.getBoundingClientRect().width : 0;
      if (w > 0) tracks[i].style.animationDuration = Math.max(30, Math.round(w / 80)) + "s";
    }
  }

  // --- tiny DOM helpers (textContent only — never innerHTML) ---
  function el(tag, cls) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    return n;
  }
  function txt(tag, cls, text) {
    var n = el(tag, cls);
    n.textContent = text == null ? "" : String(text);
    return n;
  }
  // bilingual inline span: <span class=cls><span.whb-en>en</span><span.whb-zh>zh</span></span>
  function biTxt(cls, en, zh) {
    var n = el("span", cls);
    n.appendChild(txt("span", "whb-en", en));
    n.appendChild(txt("span", "whb-zh", zh == null ? en : zh));
    return n;
  }

  function injectStyle() {
    if (document.getElementById("whb-style")) return;
    var css = [
      ".whb-on .whb{--whb-h:42px}",
      // width:100% + max-width:100vw is load-bearing, not belt-and-braces. .whb is a
      // flex container holding a marquee track that is deliberately ~10,800px wide.
      // Its own overflow:hidden only clips what is INSIDE it — it does not stop the
      // container itself from being sized by that child when the parent does not
      // constrain it. On coming-soon.html it did exactly that and blew the document
      // to 6,159px against a 1,440px viewport (measured 2026-08-12): a page that
      // scrolls sideways on every viewport, which design system §15 forbids outright.
      ".whb{position:relative;z-index:60;display:flex;align-items:stretch;height:42px;",
      "width:100%;max-width:100vw;box-sizing:border-box;",
      "background:linear-gradient(90deg,rgba(20,30,55,.96),rgba(34,20,30,.96));",
      "color:#f4f6fb;border-bottom:1px solid rgba(255,255,255,.10);",
      "box-shadow:0 2px 14px rgba(0,0,0,.28);font:13px/1.4 -apple-system,'Segoe UI',Roboto,Helvetica,sans-serif;",
      "-webkit-backdrop-filter:saturate(1.3) blur(2px);backdrop-filter:saturate(1.3) blur(2px);overflow:hidden}",
      // warmer backdrop while the orange Risk-Radar channel is showing
      ".whb.whb-warm{background:linear-gradient(90deg,rgba(44,32,20,.96),rgba(48,24,22,.96))}",
      // Warning severity is not a price direction: deep red in both languages.
      ".whb.whb-critical{height:auto;min-height:64px;background:linear-gradient(90deg,rgba(74,13,25,.98),rgba(47,12,20,.98))}",
      ".whb-critical .whb-label-rr{background:linear-gradient(90deg,#9b1830,#741527)}",
      ".whb-critical .whb-dot::after{animation:none}",
      ".whb-critical .whb-risk-view{-webkit-mask-image:none;mask-image:none;contain:none}",
      ".whb-risk-summary{display:flex;flex-direction:column;gap:3px;min-width:0;padding:10px 16px;",
      "white-space:normal;overflow-wrap:anywhere;text-decoration:none;color:inherit}",
      ".whb-risk-summary:hover .whb-ttl{text-decoration:underline}",
      ".whb-issued{font-size:11px;color:#f0c7cf}",
      ".whb-acknowledged .whb-x{opacity:1;background:rgba(255,255,255,.09)}",
      ".whb a:focus-visible{outline:2px solid currentColor;outline-offset:-3px}",
      "@media(prefers-reduced-motion:reduce){.whb *,.whb *::after{animation:none!important;transition:none!important}}",
      ".whb::before{content:'';position:absolute;left:0;right:0;top:0;height:2px;",
      "background:var(--whb-top,linear-gradient(90deg,#3d6fd6,#d9a441 50%,#d2455c))}",
      // stage holds one face per channel; when .multi they overlap and crossfade
      ".whb-stage{flex:1 1 auto;position:relative;display:flex;align-items:stretch;min-width:0;overflow:hidden}",
      ".whb-face{display:flex;align-items:stretch;flex:1 1 auto;min-width:0}",
      ".whb-stage.multi .whb-face{position:absolute;inset:0;opacity:0;transition:opacity .55s ease;pointer-events:none}",
      ".whb-stage.multi .whb-face.is-active{opacity:1;pointer-events:auto}",
      // breaking label (channel colour set by whb-label-wh / whb-label-rr)
      ".whb-label{flex:0 0 auto;display:flex;align-items:center;gap:8px;padding:0 16px;",
      "color:#fff;font-weight:800;letter-spacing:.07em;font-size:11px;text-transform:uppercase;",
      "text-decoration:none;box-shadow:6px 0 14px rgba(0,0,0,.30);position:relative;z-index:2;white-space:nowrap}",
      ".whb-label-wh{background:linear-gradient(90deg,#b8253c,#8f1d30)}",
      ".whb-label-rr{background:linear-gradient(90deg,#e0791c,#b8560f)}",
      ".whb-label-tx{white-space:nowrap}",
      "@media(max-width:560px){.whb-label-tx{display:none}.whb-label{padding:0 12px}}",
      ".whb-dot{position:relative;width:8px;height:8px;border-radius:50%;background:#ffe1d1}",
      ".whb-dot::after{content:'';position:absolute;inset:0;border:1px solid rgba(255,170,170,.82);",
      "border-radius:50%;pointer-events:none;will-change:transform,opacity;animation:whb-pulse 1.6s infinite}",
      "@keyframes whb-pulse{0%{transform:scale(1);opacity:.72}",
      "70%,100%{transform:scale(3);opacity:0}}",
      // scrolling viewport
      ".whb-view{flex:1 1 auto;overflow:hidden;position:relative;display:flex;align-items:center;",
      "-webkit-mask-image:linear-gradient(90deg,transparent,#000 28px,#000 calc(100% - 40px),transparent);",
      "mask-image:linear-gradient(90deg,transparent,#000 28px,#000 calc(100% - 40px),transparent);contain:paint}",
      ".whb-track{display:flex;align-items:center;white-space:nowrap;will-change:transform;",
      "transform:translate3d(0,0,0);backface-visibility:hidden;",
      "animation:whb-scroll 46s linear infinite}",
      ".whb-static{animation:none;overflow-x:auto;scrollbar-width:none}",
      ".whb-static::-webkit-scrollbar{display:none}",
      ".whb:hover .whb-track{animation-play-state:paused}",
      "@keyframes whb-scroll{from{transform:translate3d(0,0,0)}to{transform:translate3d(-50%,0,0)}}",
      ".whb-run{display:flex;align-items:center}",
      ".whb-seg{display:inline-flex;align-items:center;gap:10px;padding:0 20px;text-decoration:none;color:#eef1f8}",
      ".whb-seg:hover .whb-ttl{text-decoration:underline}",
      ".whb-pipe{width:3px;height:18px;border-radius:2px;background:#9aa4bf;flex:0 0 auto}",
      ".whb-tone-tailwind{background:#39c07d}.whb-tone-headwind{background:#ef5b6b}",
      ".whb-tone-mixed{background:#e3b341}.whb-tone-neutral{background:#9aa4bf}",
      /* zh 红涨绿跌: tailwind (bullish/positive flow) pipe swaps green→red; headwind (bearish) swaps red→green */
      'html[data-lang="zh"] .whb-tone-tailwind{background:#e05555}html[data-lang="zh"] .whb-tone-headwind{background:#39c07d}',
      ".whb-tone-danger{background:linear-gradient(180deg,#ffb13a,#ec5a1e)}",
      ".whb-ttl{font-weight:650;color:#fff;letter-spacing:.01em}",
      // self-contained EN/中文 toggle (does not depend on the host page's theme.css)
      ".whb-zh{display:none}",
      'html[data-lang="zh"] .whb-en{display:none}',
      'html[data-lang="zh"] .whb-zh{display:inline}',
      ".whb-chip{display:inline-flex;align-items:center;gap:6px;padding:3px 9px;border-radius:7px;",
      "background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.10)}",
      ".whb-sym{font-weight:700;font-variant-numeric:tabular-nums;font-size:12px;color:#dfe5f2;letter-spacing:.02em}",
      ".whb-chg{font-variant-numeric:tabular-nums;font-size:11.5px;font-weight:700}",
      ".whb-chg.up{color:#54d495}.whb-chg.dn{color:#ff7a86}",
      /* zh 红涨绿跌: price change up (bullish) swaps green→red; dn swaps red→green */
      'html[data-lang="zh"] .whb-chg.up{color:#ff7a86}html[data-lang="zh"] .whb-chg.dn{color:#54d495}',
      ".whb-div{color:rgba(255,255,255,.28);padding:0 6px;font-size:9px}",
      // --- Risk-Radar channel accents ---
      ".whb-rr-k{display:inline-flex;align-items:center;padding:2px 8px;border-radius:6px;",
      "font-size:9.5px;font-weight:800;letter-spacing:.09em;text-transform:uppercase;",
      "color:#ffcf9a;background:rgba(236,122,30,.16);border:1px solid rgba(236,122,30,.42)}",
      ".whb-rr-p{font-variant-numeric:tabular-nums;font-size:11px;font-weight:800;color:#ffb066}",
      ".whb-amp{background:rgba(236,122,30,.10);border-color:rgba(236,122,30,.28)}",
      ".whb-conj{background:rgba(210,69,92,.14);border-color:rgba(210,69,92,.40)}",
      ".whb-conj .whb-sym{color:#ffb3bd}",
      ".whb-fall .whb-sym{color:#ffd9a3}",
      ".whb-rr-big{display:inline-flex;align-items:baseline;gap:6px}",
      ".whb-rr-pct{font-variant-numeric:tabular-nums;font-weight:800;font-size:17px;color:#ffb066;letter-spacing:.01em}",
      ".whb-rr-hz{font-size:10.5px;color:rgba(255,214,170,.85);font-weight:600}",
      ".whb-ramp .whb-sym{color:#e9c9a2;font-size:11px}",
      ".whb-x{flex:0 0 40px;width:40px;height:40px;display:grid;place-items:center;",
      "background:transparent;border:0;color:inherit;opacity:.6;",
      "font-size:21px;line-height:1;padding:0;cursor:pointer;align-self:center;",
      "border-radius:var(--r-sm,10px);touch-action:manipulation}",
      ".whb-x:hover{opacity:1}",
      ".whb-x:focus-visible{outline:2px solid currentColor;outline-offset:-4px;opacity:1}",
      ".whb-x:active{opacity:.78}",
      "@media print{.whb{display:none}}",
    ].join("");
    var st = document.createElement("style");
    st.id = "whb-style";
    st.textContent = css;
    document.head.appendChild(st);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
