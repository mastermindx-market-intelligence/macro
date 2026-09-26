/* Shared Theme Opportunity visibility.
 * Direct fail-closed reader of theme_intelligence.consumer.v1.
 * Presentation only: it never originates ThemeState, rank, gate, size, escalation,
 * trade authority, member eligibility, or a synthesized overall theme state.
 */
(function (root, factory) {
  "use strict";
  var api = factory(root || {});
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.ThemeOpportunityContext = api;
}(typeof window !== "undefined" ? window : (typeof globalThis !== "undefined" ? globalThis : this), function (root) {
  "use strict";

  var PAYLOAD_SCHEMA = "theme_lanes.v1";
  var CONTRACT_SCHEMA = "theme_intelligence.consumer.v1";
  var DATA_URL = "basketdata/theme_lanes.json";
  var ID_RE = /^[a-z0-9][a-z0-9_-]{0,127}$/;
  var DIMENSION_ORDER = ["leadership", "thesis", "crowding", "entry", "health"];
  var DIMENSION_LABELS = {
    leadership: ["Leadership", "领导力"],
    thesis: ["Thesis", "论点"],
    crowding: ["Crowding", "拥挤度"],
    entry: ["Entry", "入场"],
    health: ["Evidence", "证据"]
  };
  var STATE_LABELS = {
    UNAVAILABLE: ["Unavailable", "暂不可用"],
    UNKNOWN: ["Unknown", "未知"],
    UNCONFIRMED: ["Unconfirmed", "未确认"],
    NOT_DETECTED: ["Not detected", "未检测到"],
    OBSERVED: ["Observed", "已观察"],
    DETECTED: ["Detected", "已检测到"],
    MEASURED: ["Measured", "已测量"],
    PARTIAL: ["Partial", "部分"],
    LEADING: ["Leading", "领先"],
    LAGGING: ["Lagging", "落后"],
    NEUTRAL: ["Neutral", "中性"],
    ACTIVE: ["Active", "有效"],
    INVALIDATED: ["Invalidated", "已失效"],
    QUALIFIED: ["Qualified", "已合格"],
    CURRENT: ["Current", "当前"],
    STALE: ["Stale inputs", "输入过期"]
  };
  var AUTHORITY_FALSE = ["may_rank", "may_gate", "may_size", "may_escalate", "may_trade"];
  var payloadPromise = null;
  var observer = null;

  function isObject(value) {
    return !!value && typeof value === "object" && !Array.isArray(value);
  }

  function safeId(value) {
    var text = typeof value === "string" ? value : "";
    return ID_RE.test(text) ? text : "";
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch];
    });
  }

  function bilingual(en, zh) {
    return '<span class="l-en">' + escapeHtml(en) + '</span><span class="l-zh">' +
      escapeHtml(zh || en) + '</span>';
  }

  function stateOf(raw) {
    if (!isObject(raw) || typeof raw.state !== "string" || !raw.state.trim()) return "UNAVAILABLE";
    return raw.state.trim().toUpperCase();
  }

  function defaultLabel(state) {
    if (STATE_LABELS[state]) return STATE_LABELS[state];
    var en = state.replace(/_/g, " ").toLowerCase().replace(/(^|\s)\S/g, function (c) {
      return c.toUpperCase();
    });
    return [en, state];
  }

  function safeAuthority(row) {
    var authority = isObject(row) && isObject(row.authority) ? row.authority : null;
    if (!authority || authority.is_context_only !== true || authority.display_only !== true) return false;
    return AUTHORITY_FALSE.every(function (key) { return authority[key] === false; });
  }

  function validatePayload(payload) {
    if (!isObject(payload)) return { ok: false, reason: "PAYLOAD_UNAVAILABLE" };
    if (payload.schema !== PAYLOAD_SCHEMA) return { ok: false, reason: "PAYLOAD_SCHEMA_UNSUPPORTED" };
    if (payload.consumer_contract_schema !== CONTRACT_SCHEMA) {
      return { ok: false, reason: "CONTRACT_SCHEMA_UNAVAILABLE" };
    }
    if (!isObject(payload.theme_context) || !isObject(payload.theme_baskets)) {
      return { ok: false, reason: "CONTRACT_BODY_UNAVAILABLE" };
    }
    return { ok: true, reason: null };
  }

  function basketIdForTheme(payload, themeId) {
    var valid = validatePayload(payload);
    var theme = safeId(themeId);
    if (!valid.ok || !theme) return null;
    return safeId(payload.theme_baskets[theme]) || null;
  }

  function themeIdForBasket(payload, basketId) {
    var valid = validatePayload(payload);
    var basket = safeId(basketId);
    if (!valid.ok || !basket) return null;
    var found = null;
    Object.keys(payload.theme_baskets).some(function (themeId) {
      if (safeId(themeId) && payload.theme_baskets[themeId] === basket) {
        found = themeId;
        return true;
      }
      return false;
    });
    return found;
  }

  function unavailableDimension(name, reason) {
    return {
      name: name,
      state: "UNAVAILABLE",
      labelEn: STATE_LABELS.UNAVAILABLE[0],
      labelZh: STATE_LABELS.UNAVAILABLE[1],
      reasonCodes: reason ? [reason] : [],
      sourceRecords: [],
      clocks: null
    };
  }

  function readDimension(name, raw) {
    if (!isObject(raw)) return unavailableDimension(name, "OWNER_FIELD_NOT_JOINED");
    var state = stateOf(raw);
    var fallback = defaultLabel(state);
    return {
      name: name,
      state: state,
      labelEn: (typeof raw.label === "string" && raw.label.trim()) ? raw.label : fallback[0],
      labelZh: (typeof raw.label_zh === "string" && raw.label_zh.trim()) ? raw.label_zh : fallback[1],
      reasonCodes: Array.isArray(raw.reason_codes) ? raw.reason_codes.filter(function (x) {
        return typeof x === "string" && x;
      }) : (typeof raw.reason_code === "string" && raw.reason_code ? [raw.reason_code] : []),
      sourceRecords: Array.isArray(raw.source_records) ? raw.source_records : [],
      clocks: isObject(raw.clocks) ? raw.clocks : null
    };
  }

  function unavailableContext(identity, reason) {
    identity = isObject(identity) ? identity : {};
    var dimensions = {};
    DIMENSION_ORDER.forEach(function (name) { dimensions[name] = unavailableDimension(name, reason); });
    return {
      contractValid: false,
      contractReason: reason || "CONTRACT_UNAVAILABLE",
      themeId: safeId(identity.themeId) || null,
      basketId: safeId(identity.basketId) || null,
      name: typeof identity.name === "string" ? identity.name : null,
      nameZh: typeof identity.nameZh === "string" ? identity.nameZh : null,
      dimensions: dimensions,
      asOf: null
    };
  }

  function readContext(payload, identity) {
    identity = isObject(identity) ? identity : {};
    var valid = validatePayload(payload);
    var requestedTheme = safeId(identity.themeId);
    var requestedBasket = safeId(identity.basketId);
    if (!valid.ok) return unavailableContext(identity, valid.reason);
    var themeId = requestedTheme || themeIdForBasket(payload, requestedBasket);
    if (!themeId) return unavailableContext(identity, "IDENTITY_UNRESOLVED");
    var basketId = basketIdForTheme(payload, themeId);
    if (requestedBasket && requestedBasket !== basketId) {
      return unavailableContext({ themeId: themeId, basketId: requestedBasket }, "IDENTITY_CONFLICT");
    }
    var row = payload.theme_context[themeId];
    if (!isObject(row) || row.schema !== CONTRACT_SCHEMA) {
      return unavailableContext({ themeId: themeId, basketId: basketId }, "THEME_CONTEXT_UNAVAILABLE");
    }
    if (!isObject(row.identity) || row.identity.theme_id !== themeId || !safeAuthority(row)) {
      return unavailableContext({ themeId: themeId, basketId: basketId }, "CONTRACT_AUTHORITY_OR_IDENTITY_INVALID");
    }
    var dimensions = {};
    DIMENSION_ORDER.forEach(function (name) {
      dimensions[name] = readDimension(name, isObject(row.dimensions) ? row.dimensions[name] : null);
    });
    var observation = isObject(row.clocks) && typeof row.clocks.observation === "string" ?
      row.clocks.observation : null;
    return {
      contractValid: true,
      contractReason: null,
      themeId: themeId,
      basketId: basketId,
      name: (typeof identity.name === "string" && identity.name.trim()) ? identity.name.trim() : themeId.replace(/_/g, " "),
      nameZh: (typeof identity.nameZh === "string" && identity.nameZh.trim()) ? identity.nameZh.trim() :
        ((typeof identity.name === "string" && identity.name.trim()) ? identity.name.trim() : themeId.replace(/_/g, " ")),
      dimensions: dimensions,
      asOf: observation || (typeof payload.asof === "string" ? payload.asof : null)
    };
  }

  function routesForContext(context) {
    var theme = safeId(context && context.themeId);
    var basket = safeId(context && context.basketId);
    if (!theme) return {};
    var routes = {
      tracker: "state_of_themes.html#theme-" + theme,
      foresight: "foresight.html#theme-" + theme,
      radar: "radar.html#theme-" + theme
    };
    if (basket) routes.sector = "sector_central.html#theme-" + basket;
    return routes;
  }

  function renderDimension(name, dim) {
    var labels = DIMENSION_LABELS[name];
    var tips = dim.reasonCodes.join(" · ") || dim.labelEn;
    return '<div class="toc-dim toc-dim-' + escapeHtml(dim.state.toLowerCase().replace(/_/g, "-")) +
      '" data-dimension="' + escapeHtml(name) + '" data-state="' + escapeHtml(dim.state.toLowerCase()) +
      '" data-tip-en="' + escapeHtml(tips) + '" data-tip-zh="' + escapeHtml(tips) + '">' +
      '<span class="toc-k">' + bilingual(labels[0], labels[1]) + '</span>' +
      '<strong>' + bilingual(dim.labelEn, dim.labelZh) + '</strong></div>';
  }

  function renderRoutes(context, activeRoute) {
    var routes = routesForContext(context);
    var labels = {
      tracker: ["Tracker", "追踪"],
      foresight: ["Foresight", "前瞻"],
      radar: ["Radar", "雷达"],
      sector: ["Setup", "结构"]
    };
    var out = [];
    ["tracker", "foresight", "radar", "sector"].forEach(function (key) {
      if (!routes[key]) {
        if (key === "sector") out.push('<span class="toc-route" data-route-unavailable="setup">' +
          bilingual("Setup unavailable", "结构暂不可用") + '</span>');
        return;
      }
      if (key === activeRoute) {
        out.push('<span class="toc-route active" aria-current="page">' +
          bilingual(labels[key][0], labels[key][1]) + '</span>');
      } else {
        out.push('<a class="toc-route" href="' + escapeHtml(routes[key]) + '">' +
          bilingual(labels[key][0], labels[key][1]) + '</a>');
      }
    });
    return '<nav class="toc-routes" aria-label="Theme opportunity lenses">' + out.join("") + '</nav>';
  }

  function renderHtml(context, activeRoute) {
    context = isObject(context) ? context : unavailableContext({}, "MODEL_UNAVAILABLE");
    var themeLabel = context.name || (context.themeId ? context.themeId.replace(/_/g, " ") : "Theme context");
    var themeLabelZh = context.nameZh || themeLabel;
    return '<div class="toc-context" data-mx-opportunity="' + escapeHtml(context.themeId || "unavailable") +
      '" data-contract-valid="' + (context.contractValid ? "true" : "false") + '">' +
      '<div class="toc-head"><strong class="toc-theme-name">' + bilingual(themeLabel, themeLabelZh) +
      '</strong><span class="toc-asof">' +
      (context.asOf ? bilingual("As of " + context.asOf, "截至 " + context.asOf) :
        bilingual("Date unavailable", "日期不可用")) + '</span></div>' +
      '<div class="toc-grid">' + DIMENSION_ORDER.map(function (name) {
        return renderDimension(name, context.dimensions[name]);
      }).join("") + '</div>' +
      renderRoutes(context, safeId(activeRoute)) +
      '<p class="toc-boundary">' +
      bilingual("Theme-level context only. Member entries still require an individually qualified setup.",
        "仅为主题级背景。个股入场仍需独立合格的个股结构。") +
      '</p></div>';
  }

  function loadPayload() {
    if (payloadPromise) return payloadPromise;
    if (typeof root.fetch !== "function") {
      payloadPromise = Promise.resolve(null);
      return payloadPromise;
    }
    payloadPromise = root.fetch(DATA_URL, { cache: "no-store" })
      .then(function (response) { return response && response.ok ? response.json() : null; })
      .catch(function () { return null; });
    return payloadPromise;
  }

  function identityForMount(element) {
    var themeId = safeId(element.getAttribute("data-theme-id"));
    var basketId = safeId(element.getAttribute("data-basket-id"));
    var queryParam = safeId(element.getAttribute("data-theme-query-param"));
    if (!themeId && queryParam && root.location && typeof root.URLSearchParams === "function") {
      try { themeId = safeId(new root.URLSearchParams(root.location.search || "").get(queryParam)); }
      catch (ignore) {}
    }
    return {
      themeId: themeId || null,
      basketId: basketId || null,
      name: element.getAttribute("data-theme-name") || null,
      nameZh: element.getAttribute("data-theme-name-zh") || null
    };
  }

  function mountOne(element, payload) {
    if (!element || element.getAttribute("data-theme-opportunity-mounted") === "true") return;
    var context = readContext(payload, identityForMount(element));
    element.innerHTML = renderHtml(context, element.getAttribute("data-active-route") || "");
    element.removeAttribute("hidden");
    element.setAttribute("data-theme-opportunity-mounted", "true");
  }

  function mountAll(scope, payload) {
    if (typeof document === "undefined") return Promise.resolve(payload || null);
    var rootNode = scope && typeof scope.querySelectorAll === "function" ? scope : document;
    return (payload !== undefined ? Promise.resolve(payload) : loadPayload()).then(function (resolved) {
      Array.prototype.forEach.call(
        rootNode.querySelectorAll("[data-theme-opportunity-mount]"),
        function (element) { mountOne(element, resolved); }
      );
      return resolved;
    });
  }

  function boot() {
    mountAll(document);
    if (typeof root.MutationObserver === "function" && !observer) {
      observer = new root.MutationObserver(function (mutations) {
        if (mutations.some(function (mutation) { return mutation.addedNodes && mutation.addedNodes.length; })) {
          mountAll(document);
        }
      });
      observer.observe(document.documentElement, { childList: true, subtree: true });
    }
  }

  if (typeof document !== "undefined") {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
    else boot();
  }

  return {
    PAYLOAD_SCHEMA: PAYLOAD_SCHEMA,
    CONTRACT_SCHEMA: CONTRACT_SCHEMA,
    validatePayload: validatePayload,
    readContext: readContext,
    renderHtml: renderHtml,
    routesForContext: routesForContext,
    themeIdForBasket: themeIdForBasket,
    basketIdForTheme: basketIdForTheme,
    mountAll: mountAll,
    ready: loadPayload
  };
}));
