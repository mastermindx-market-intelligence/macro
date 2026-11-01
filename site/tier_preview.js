/* Anonymous/Free preview controller for public dashboard shells.
   The server still owns every protected detail page and data payload. This
   layer only determines how many already-public summary rows each visitor sees:
   anonymous = 1, registered Free = 3, Essential/Pro = the full book. */
(function () {
  "use strict";

  var state = { tier: "anon", cap: 1 };
  var GATE_ATTR = "data-mx-tier-gate";
  var observer = null;
  var applying = false;
  var requestGeneration = 0;
  var verifiedUserId = null;
  var confirmedTier = null;
  var tierPublished = false;

  // `essential` is the WIRE value; `insider` is what the estate shipped before the
  // rename (lib/tiers.py is the server's copy of the same table). Named here, not just
  // resolved in setTier(), because a far-future-cached copy of this file must keep a
  // paying visitor OUT of the 3-row free cap when /api/me answers with either value —
  // rows written before the flip still say `insider` and are never back-filled.
  var TIER_ALIAS = { insider: "essential" };
  function normTier(tier) {
    var t = String(tier == null ? "" : tier).trim().toLowerCase();
    return TIER_ALIAS[t] || t;
  }
  function isPaid(tier) {
    var t = normTier(tier);
    return t === "essential" || t === "pro" || t === "unlimited";
  }
  function capFor(tier) { return isPaid(tier) ? Infinity : (tier === "free" ? 3 : 1); }
  function hasSessionCookie() {
    try {
      return String(document.cookie || "").split(";").some(function (part) {
        return /^sb-.*-auth-token(\.\d+)?$/.test(part.split("=")[0].trim());
      });
    } catch (e) { return false; }
  }
  function openOnboard(mode) {
    if (window.MMOnboard && typeof window.MMOnboard.open === "function") {
      window.MMOnboard.open(mode || "signup", {});
      return;
    }
    if (window.MDXAuth && typeof window.MDXAuth.open === "function") {
      window.MDXAuth.open(mode === "signup" ? "signup" : "signin");
      return;
    }
    if (window.MMXSharedShell) { window.MMXSharedShell.openAuth(mode === "signup" ? "signup" : "signin"); return; }
    location.href = "/?signup=1";
  }
  function openUpgrade() {
    if (window.MMOnboard && typeof window.MMOnboard.open === "function") {
      window.MMOnboard.open("upgrade", { plan: "essential", period: "annual" });
      return;
    }
    if (window.MMXSharedShell) { window.MMXSharedShell.openAuth("billing"); return; }
    location.href = "/plans.html";
  }

  function directRows(root) {
    var rows = Array.prototype.slice.call(root.children || []);
    return rows.filter(function (row) {
      if (row.matches && row.matches("tr")) return !!row.querySelector("td");
      // .cand-row: P-MP1-SHELL repair round, finding B2 — the us_stocks.html
      // Candidates shelf (#us-candidates .cand-rows, dashboard.html.j2) ships
      // ticker/name/price rows with no gating of its own; without this, an
      // anonymous visitor reads every baked candidate row in plain text.
      return !!(row.matches && row.matches(".actitem,[data-theme-id],.pvcard,.nbcard,.nb-card,.ts-row,.sbx-tile,.dash-tw-row,.pbr-r,.cand-row"));
    });
  }
  function groups() {
    var out = [];
    function add(selector) {
      document.querySelectorAll(selector).forEach(function (root) {
        var items = directRows(root);
        if (items.length) out.push({ root: root, items: items });
      });
    }
    add("#action-board .actbody");
    add("#us-standouts .nbgrid");
    add("#us-standouts .topsetups tbody");
    // P-MP1-SHELL repair round, finding B2: the Candidates shelf
    // (#us-candidates .cand-rows) is a SECOND population inside the same
    // #us-standouts panel as the Setups grid above — surfaceFor() already
    // resolves anything under #us-standouts to the "prophet" surface, so
    // this joins the SAME shared gate banner rather than opening a third
    // lock (MP-1 §7's "max two locks" law is unaffected). Before this line,
    // every candidate row baked into the page (up to 6) was fully visible to
    // an anonymous visitor — reproduced as "anonymous tier gains 2 tickers +
    // 3 names + 3 prices vs pre-migration".
    add("#us-candidates .cand-rows");
    // The `ran` list is quieter markup than the cards, but it is the SAME board:
    // ticker, name and move, one row per name. It sat inside #us-standouts ungated,
    // so an anonymous visitor read the full roster in plain text directly under a
    // blurred grid. Same group idiom, same cap, same gate.
    add("#us-standouts .pbr-l");
    add("#us-stocktable-wrap tbody");
    add("#dash-tw-rows");
    add("#dash-mtf-body tbody");
    add("body.page-stocks .panel table tbody");

    var seen = [];
    return out.filter(function (group) {
      if (seen.indexOf(group.root) !== -1) return false;
      seen.push(group.root);
      return true;
    });
  }
  function surfaceFor(root) {
    if (root.closest && root.closest("#action-board")) return "action";
    if (root.closest && root.closest("#us-standouts")) return "prophet";
    return "";
  }
  function gateCopy(surface) {
    if (state.tier === "unknown") {
      return {
        eyebrow: "Account access",
        eyebrowZh: "账户权限",
        mark: "↗",
        title: "Access not yet confirmed",
        zh: "访问权限尚未确认",
        body: "Check your access again to load the right preview for your account.",
        bodyZh: "请重新检查访问权限，以加载适合您账户的预览。",
        action: "Check access",
        actionZh: "检查访问权限",
        mode: "refresh"
      };
    }
    if (state.tier === "free") {
      if (surface === "prophet") {
        return {
          eyebrow: "Prophet",
          eyebrowZh: "Prophet",
          mark: "P",
          title: "See the complete Prophet ranking",
          zh: "查看完整 Prophet 排名",
          body: "Every model-ranked setup, in one signal book.",
          bodyZh: "所有模型排名机会，集中于一份信号名单。",
          action: "Unlock full Prophet",
          actionZh: "解锁完整 Prophet",
          mode: "upgrade"
        };
      }
      return {
        eyebrow: "Essential access",
        eyebrowZh: "Essential 权限",
        mark: "↗",
        title: "Unlock the complete action board",
        zh: "解锁完整行动面板",
        body: "See every current setup, without limits.",
        bodyZh: "无限制查看所有当前机会。",
        action: "View Essential plans",
        actionZh: "查看 Essential 方案",
        mode: "upgrade"
      };
    }
    if (surface === "prophet") {
      return {
        eyebrow: "Prophet",
        eyebrowZh: "Prophet",
        mark: "P",
        title: "Expand the Prophet shortlist",
        zh: "展开 Prophet 精选名单",
        body: "More model-ranked setups, with the same signal detail and discipline.",
        bodyZh: "查看更多模型排名机会，同时保留完整信号细节与纪律。",
        action: "See more Prophet picks",
        actionZh: "查看更多 Prophet 精选",
        mode: "signup"
      };
    }
    return {
      eyebrow: "Daily action board",
      eyebrowZh: "每日行动面板",
      mark: "↗",
      title: "Open more of today’s action board",
      zh: "展开今日行动面板",
      body: "More actionable signals, presented in one clean daily workflow.",
      bodyZh: "更多可执行信号，集中于清晰的每日流程。",
      action: "Create free account",
      actionZh: "创建免费账户",
      secondary: "Already a member? Sign in",
      secondaryZh: "已有账户？登录",
      mode: "signup"
    };
  }
  function makeGate(surface) {
    var copy = gateCopy(surface);
    var gate = document.createElement("div");
    gate.className = "mx-tier-gate mx-tier-gate--" + surface;
    gate.setAttribute(GATE_ATTR, surface);
    gate.innerHTML =
      '<span class="mx-tier-copy">' +
      '<span class="mx-tier-eyebrow"><span class="mx-tier-mark" aria-hidden="true">' + copy.mark + '</span>' +
      '<span class="l-en">' + copy.eyebrow + '</span><span class="l-zh">' + copy.eyebrowZh + '</span></span>' +
      '<b><span class="l-en">' + copy.title + '</span><span class="l-zh">' + copy.zh + '</span></b>' +
      '<small><span class="l-en">' + copy.body + '</span><span class="l-zh">' + copy.bodyZh + '</span></small></span>' +
      '<span class="mx-tier-actions"><button class="mx-tier-primary" type="button"><span class="l-en">' + copy.action + '</span><span class="l-zh">' + copy.actionZh + '</span></button>' +
      (copy.secondary ? '<button class="mx-tier-signin" type="button"><span class="l-en">' + copy.secondary + '</span><span class="l-zh">' + copy.secondaryZh + '</span></button>' : '') +
      '</span>';
    gate.querySelector(".mx-tier-primary").addEventListener("click", function () {
      if (copy.mode === "refresh") resolveTier();
      else if (copy.mode === "upgrade") openUpgrade(); else openOnboard("signup");
    });
    var signin = gate.querySelector(".mx-tier-signin");
    if (signin) signin.addEventListener("click", function () { openOnboard("signin"); });
    return gate;
  }
  function clearGroup(group) {
    group.items.forEach(function (item) {
      item.classList.remove("mx-tier-blurred", "mx-tier-hidden");
      item.removeAttribute("aria-hidden");
      if (item.hasAttribute("data-mx-old-tabindex")) {
        var old = item.getAttribute("data-mx-old-tabindex");
        if (old === "") item.removeAttribute("tabindex"); else item.setAttribute("tabindex", old);
        item.removeAttribute("data-mx-old-tabindex");
      }
    });
  }
  function applyGroup(group) {
    clearGroup(group);
    if (!isFinite(state.cap) || group.items.length <= state.cap) return false;
    group.items.forEach(function (item, index) {
      if (index < state.cap) return;
      item.setAttribute("aria-hidden", "true");
      if (index < state.cap + 2) {
        item.classList.add("mx-tier-blurred");
        if (item.hasAttribute("tabindex")) item.setAttribute("data-mx-old-tabindex", item.getAttribute("tabindex") || "");
        item.setAttribute("tabindex", "-1");
      } else {
        item.classList.add("mx-tier-hidden");
      }
    });
    return true;
  }
  // ── theme tape member lists ───────────────────────────────────────────────
  // Same law as the themes-in-favour strip above, one panel higher up the page.
  // The tape's COUNTS are aggregate and stay free — they are the panel's whole
  // argument ("6 of Software's 60 names are on this board"), and a count names
  // nobody. The member LISTS inside an expanded row are the product: ticker plus
  // the board state it sits in, which is exactly what the gated cards below sell.
  // They are in the DOM whether or not the <details> is open, so the collapse has
  // to rewrite them rather than rely on the disclosure being shut.
  // Reversible through the same data-mx-old-html stash, because a visitor who
  // upgrades in-page must get the names back without a reload.
  function applyTapeMembers() {
    var gated = isFinite(state.cap);
    document.querySelectorAll("#theme-tape .tt-names").forEach(function (list) {
      var stashed = list.getAttribute("data-mx-old-html");
      if (!gated) {
        if (stashed !== null) {
          list.innerHTML = stashed;
          list.removeAttribute("data-mx-old-html");
        }
        return;
      }
      if (stashed !== null) return;
      /* SERVER-COLLAPSED (docs/TIER_PREVIEW_PATTERN.md, us_stocks adjacent-panel
         gate): on a gated build the member names are not in this document at all
         — the shell already ships the count and the names ride the paid payload.
         Such a list has no .tt-n children, so counting them here would rewrite a
         truthful "7 names" to "0 names"; and stashing that text would let this
         function later RESTORE it over the names the payload just hydrated in.
         Leave it entirely alone: nothing stashed, nothing to undo. */
      if (!list.querySelector(".tt-n")) return;
      var n = 0;
      list.querySelectorAll(".tt-n").forEach(function (el) {
        if (el.classList.contains("tt-more")) {
          var extra = parseInt(String(el.textContent || "").replace(/[^0-9]/g, ""), 10);
          if (extra > 0) n += extra;
        } else { n += 1; }
      });
      list.setAttribute("data-mx-old-html", list.innerHTML);
      list.innerHTML =
        '<span class="l-en">' + n + (n === 1 ? " name" : " names") + '</span>' +
        '<span class="l-zh">' + n + " 只股票</span>";
    });
  }
  function placeSurfaceGates(surfaces) {
    [
      { key: "action", selector: "#action-board" },
      { key: "prophet", selector: "#us-standouts" }
    ].forEach(function (surface) {
      var panel = document.querySelector(surface.selector);
      if (panel && surfaces[surface.key]) panel.appendChild(makeGate(surface.key));
    });
  }
  function apply() {
    if (applying) return;
    applying = true;
    if (observer) observer.disconnect();
    try {
      document.querySelectorAll("[" + GATE_ATTR + "]").forEach(function (gate) { gate.remove(); });
      var surfaces = { action: false, prophet: false };
      groups().forEach(function (group) {
        if (!applyGroup(group)) return;
        var surface = surfaceFor(group.root);
        if (surface) surfaces[surface] = true;
      });
      placeSurfaceGates(surfaces);
      // Unconditional: tape member names sit outside the capped card grids.
      applyTapeMembers();
    } finally {
      applying = false;
      if (observer && document.body) observer.observe(document.body, { childList: true, subtree: true });
    }
  }
  function setTier(tier, resolution) {
    tier = normTier(tier);
    tier = isPaid(tier) || tier === "unknown" ? tier : (tier === "free" ? "free" : "anon");
    // Resolution health is separate from the last confirmed summary entitlement.
    // In particular, a failed read is neither a fresh Free verdict nor a grant.
    document.documentElement.setAttribute("data-access-resolution", resolution);
    var changed = !tierPublished || state.tier !== tier;
    state.tier = tier;
    state.cap = capFor(tier);
    document.documentElement.setAttribute("data-access-tier", tier);
    if (!changed) return;
    tierPublished = true;
    apply();
    // Native detail dialogs dismiss on this event. A same-tier refresh must not
    // close an open detail or temporarily repaint a paid member as Free.
    try { window.dispatchEvent(new CustomEvent("mmx-access-tier", { detail: { tier: tier, cap: state.cap } })); } catch (e) {}
  }
  function nativeUserId() {
    try {
      var user = window.MDXAuth && window.MDXAuth.user && window.MDXAuth.user();
      return user && typeof user.id === "string" && user.id ? user.id : null;
    } catch (e) { return null; }
  }
  function clearIdentity() {
    verifiedUserId = null;
    confirmedTier = null;
  }
  function currentRequest(generation, userId) {
    if (generation !== requestGeneration) return false;
    if (nativeUserId() === userId) return true;
    // Recheck the native identity even if its notification has not arrived yet.
    requestGeneration += 1;
    clearIdentity();
    setTier(nativeUserId() ? "unknown" : "anon", "unconfirmed");
    return false;
  }
  function resolveTier() {
    var generation = ++requestGeneration;
    var observedUserId = nativeUserId();
    if (!observedUserId && !hasSessionCookie()) {
      clearIdentity();
      setTier("anon", "signed-out");
      return;
    }
    if (!observedUserId || observedUserId !== verifiedUserId) {
      clearIdentity();
      setTier("unknown", "pending");
    } else {
      setTier(confirmedTier || "unknown", "pending");
    }
    // No session/local-storage entitlement hints: neither cache binds a result
    // to the current native user or this request generation.
    Promise.resolve().then(function () {
      if (generation !== requestGeneration) return null;
      if (!window.MDXAuth || typeof window.MDXAuth.client !== "function") throw new Error("auth unavailable");
      return window.MDXAuth.client();
    }).then(function (sb) {
      if (generation !== requestGeneration) return null;
      if (!sb || !sb.auth || typeof sb.auth.getSession !== "function") throw new Error("session unavailable");
      return sb.auth.getSession();
    }).then(function (result) {
      if (generation !== requestGeneration) return;
      if (!result || result.error || !result.data) throw new Error("session unavailable");
      var session = result.data.session;
      if (!session) {
        clearIdentity();
        setTier("anon", "signed-out");
        return;
      }
      var userId = session.user && session.user.id;
      if (typeof userId !== "string" || !userId || !session.access_token || nativeUserId() !== userId) {
        throw new Error("unverified session identity");
      }
      if (verifiedUserId !== userId) confirmedTier = null;
      verifiedUserId = userId;
      return Promise.resolve().then(function () {
        if (!currentRequest(generation, userId)) return null;
        return fetch("/api/me", {
          cache: "no-store",
          headers: { Authorization: "Bearer " + session.access_token }
        });
      }).then(function (response) {
        if (!currentRequest(generation, userId)) return;
        if (!response) throw new Error("entitlement unavailable");
        if (response.status === 401 || response.status === 403) {
          confirmedTier = null;
          setTier("unknown", "denied");
          return;
        }
        if (!response.ok) throw new Error("entitlement unavailable");
        return response.json().then(function (me) {
          if (!currentRequest(generation, userId)) return;
          var tier = me && typeof me.tier === "string" ? normTier(me.tier) : "";
          if (!me || (me.id != null && me.id !== userId) || (tier !== "free" && !isPaid(tier))) {
            throw new Error("unconfirmed entitlement");
          }
          confirmedTier = tier;
          setTier(tier, "confirmed");
        });
      }).catch(function () {
        if (!currentRequest(generation, userId)) return;
        setTier(confirmedTier || "unknown", "degraded");
      });
    }).catch(function () {
      if (generation !== requestGeneration) return;
      // Session verification failed: retaining a paid result here could attach
      // it to an unknown account. Only /api/me failures for a verified user may
      // retain that user's last confirmed summary cap.
      clearIdentity();
      setTier(nativeUserId() ? "unknown" : "anon", "unconfirmed");
    });
  }

  window.MMXAccessPreview = {
    tier: function () { return state.tier; },
    cap: function () { return state.cap; },
    isAnon: function () { return state.tier === "anon" || !nativeUserId(); },
    openSignin: function () { openOnboard("signin"); },
    openSignup: function () { openOnboard("signup"); },
    refresh: resolveTier
  };

  function boot() {
    resolveTier();
    if (window.MDXAuth && typeof window.MDXAuth.onChange === "function") {
      window.MDXAuth.onChange(function (user, event) {
        if (!user || event === "SIGNED_OUT") {
          requestGeneration += 1;
          clearIdentity();
          setTier("anon", "signed-out");
        }
        else resolveTier();
      });
    }
    if (window.MutationObserver) {
      observer = new MutationObserver(function () {
        if (applying) return;
        clearTimeout(observer._timer);
        observer._timer = setTimeout(apply, 40);
      });
      observer.observe(document.body, { childList: true, subtree: true });
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
