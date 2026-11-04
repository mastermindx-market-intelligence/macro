/* Sector Dossier Cycle — opt-in presentation over the existing cycle producer.
 * No fetch, authorization decision, signal calculation, history/storage or auto-mount.
 * Host access/data states are consumed, never inferred from a nonempty payload.
 * New copy is the R4.1 candidate; production route adoption is a separate gate.
 */
(function (root, factory) {
  "use strict";
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.SectorDossierCycle = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  var KINDS = { sectors: "sector", baskets: "basket", nasdaq: "nasdaq", russell: "russell" };
  var PHASES = {
    Trough: ["Bottoming", "筑底"], Recovery: ["Recovering", "复苏"],
    Expansion: ["Trending", "扩张"], Peak: ["Topping", "做顶"],
    Downturn: ["Rolling over", "回落中"]
  };
  var COPY = {
    title: ["Cycle evidence", "周期证据"], loading: ["Loading cycle evidence…", "正在加载周期证据…"],
    denied: ["Cycle evidence is not available with this access", "当前访问权限无法查看周期证据"],
    unauthenticated: ["Sign in to view cycle evidence", "请登录以查看周期证据"],
    unavailable: ["Cycle evidence unavailable", "周期证据暂不可用"],
    unavailableBody: ["No reading is inferred. Other parts of this investigation remain available.", "不推断任何读数，仍可查看本次研究的其他内容。"],
    incompatible_generation: ["Snapshots do not match", "快照日期不一致"],
    incompatibleBody: ["This reading is withheld rather than joined to a different snapshot.", "暂不显示此读数，以免与其他日期的快照混用。"],
    stale: ["Historical snapshot", "历史快照"], asOf: ["As of", "截至"],
    phase: ["Cycle phase · ontology", "周期阶段 · 本体框架"],
    position: ["Position · ontology", "位置 · 本体框架"],
    positionNote: ["0–100 scale. Not a probability.", "0–100刻度，并非概率。"],
    unknown: ["Unavailable", "暂不可用"], sessions: ["trading sessions", "个交易日"],
    ageUnknown: ["Phase age unavailable", "阶段时长暂不可用"],
    atLeast: ["At least", "至少"], trend: ["Price vs 200-session average", "价格与200日均线"],
    above: ["Above", "高于"], below: ["Below", "低于"],
    relative: ["Relative wealth", "相对财富"], totalReturn: ["Total-return basis", "总回报口径"],
    priceBasis: ["Price basis", "价格口径"], gap: ["Not a percentage-point return gap", "并非回报率的百分点差"],
    parity_failed: ["Model reading is not current: live parity not met", "模型读数不代表当前状态：实时一致性核验未通过"],
    parity_not_established: ["Current model qualification unavailable", "当前模型资格尚未确认"],
    parity_holds: ["Source parity holds; model qualifications remain separate", "源数据一致性核验通过，模型资格仍需单独判断"],
    modelBody: ["No probability is promoted here. Historical MODEL and PRIOR evidence remains in the full Cycles view.", "此处不提升任何概率主张。完整周期视图保留历史模型与先验证据。"],
    chart: ["Legacy cycle history", "旧版周期历史"],
    chartNote: ["Different measure from the ontology summary. Do not read the two on one scale.", "其测量方法与本体摘要不同，不可视为同一刻度。"],
    chartMissing: ["History not attached", "尚未附上历史序列"],
    chartFailed: ["History could not be drawn; the facts above are unchanged", "历史图暂无法绘制，上方事实读数不受影响"],
    open: ["Open full Cycles evidence", "查看完整周期证据"],
    members: ["View constituent evidence", "查看成分股证据"],
    source: ["Sources & calculation", "数据来源与计算方法"],
    hostRequired: ["Available when connected to the owning route", "接入原有页面后可用"],
    footer: ["Descriptive evidence. No stock recommendation, sizing or execution authority.", "描述性证据，不构成个股建议、仓位建议或执行授权。"]
  };
  function own(o, k) { return Object.prototype.hasOwnProperty.call(o, k); }
  function obj(x) { return !!x && typeof x === "object" && !Array.isArray(x); }
  function finite(x) { return typeof x === "number" && Number.isFinite(x) ? x : null; }
  function text(x, limit) { return typeof x === "string" ? x.trim().slice(0, limit || 180) : ""; }
  function date(x) {
    if (typeof x !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(x)) return null;
    var d = new Date(x + "T00:00:00Z");
    return Number.isFinite(d.getTime()) && d.toISOString().slice(0, 10) === x ? x : null;
  }
  function label(k, locale) { return COPY[k][locale === "zh" ? 1 : 0]; }
  function outcome(state, reason, locale) { return {state: state, reason: reason, locale: locale}; }
  function recordFor(payload, options) {
    var list = payload[options.family];
    if (!Array.isArray(list)) return null;
    var matches = list.filter(function (r) { return obj(r) && r.id === options.id; });
    return matches.length === 1 && matches[0].kind === KINDS[options.family] ? matches[0] : null;
  }
  function qualification(record, meta) {
    var e = obj(record.estimate_kinds) ? record.estimate_kinds : {};
    var local = obj(e.live_feature_parity) ? e.live_feature_parity.verdict : null;
    var global = obj(meta.live_hazard_parity) ? meta.live_hazard_parity.verdict : null;
    if (e.model_cell_current_claim === "parity_failed" || local === "PARITY_FAILS" || global === "PARITY_FAILS") return "parity_failed";
    if (e.model_cell_current_claim === "parity_holds" && local === "PARITY_HOLDS" && global === "PARITY_HOLDS") return "parity_holds";
    return "parity_not_established";
  }
  function phaseAge(n) {
    var a = obj(n.phase_v2_age) ? n.phase_v2_age : {};
    var count = finite(a.sessions), status = a.status;
    var valid = (status === "measured" || status === "lower_bound") &&
      Number.isInteger(count) && count >= 1 && (n.freq == null || n.freq === "D") &&
      n.phase_v2_age_status === status && n.phase_v2_age_sessions === count;
    return {value: valid ? count : null, status: valid ? status : "unavailable"};
  }
  function buildView(payload, options) {
    var o = obj(options) ? options : {}, locale = o.locale === "zh" ? "zh" : "en";
    // The payload is not even evaluated until the host's access boundary settles.
    if (o.accessState == null || o.accessState === "pending") return outcome("loading", "access_pending", locale);
    if (o.accessState !== "allowed") return outcome("denied", o.accessState === "unauthenticated" ? "unauthenticated" : "forbidden", locale);
    if (o.locale !== "en" && o.locale !== "zh") return outcome("unavailable", "unsupported_locale", locale);
    if (o.dataState === "loading") return outcome("loading", "source_loading", locale);
    if (o.dataState !== "ready" && o.dataState !== "stale") return outcome("unavailable", "source_unavailable", locale);
    if (!own(KINDS, o.family) || typeof o.id !== "string" || !o.id || !obj(payload) || !obj(payload.meta)) return outcome("unavailable", "invalid_selection", locale);
    var meta = payload.meta, asOf = date(meta.asOf);
    if (meta.region != null && meta.region !== "us") return outcome("unavailable", "unsupported_region", locale);
    if (!asOf || (o.expectedAsOf != null && !date(o.expectedAsOf))) return outcome("unavailable", "invalid_asof", locale);
    if (o.expectedAsOf != null && o.expectedAsOf !== asOf) return outcome("incompatible_generation", "snapshot_mismatch", locale);
    var record = recordFor(payload, o);
    if (!record || !obj(record.now)) return outcome("unavailable", "subject_unavailable", locale);
    var n = record.now, prov = obj(record.series_provenance) ? record.series_provenance : {};
    var phaseSource = text(n.phase_v2_source, 40) || "unknown";
    var phase = phaseSource === "ontology" && own(PHASES, n.phase_v2) ? n.phase_v2 : null;
    var position = finite(n.pos_v2);
    if (position == null || position < 0 || position > 100 || n.phase_v2_position_input !== "pos_v2") position = null;
    var benchmark = text(prov.benchmark, 32), basis = prov.rs_basis;
    var relative = finite(n.rs_63d);
    if (n.thin_history === true || !benchmark || benchmark === "unknown" || (basis !== "tr" && basis !== "price")) relative = null;
    return {
      state: o.dataState, locale: locale, asOf: asOf,
      subject: {id: record.id, kind: record.kind, family: o.family,
        ticker: text(record.ticker, 40), name: text(locale === "zh" ? (record.name_zh || record.name) : record.name) || text(record.ticker) || record.id},
      phase: {key: phase, label: phase ? PHASES[phase][locale === "zh" ? 1 : 0] : label("unknown", locale), source: phaseSource, semanticFamily: phase ? "ontology" : "unavailable"},
      position: {value: position, semanticFamily: "ontology"}, age: phase ? phaseAge(n) : {value: null, status: "unavailable"},
      trend: {above200: typeof n.above200d === "boolean" ? n.above200d : null},
      relative: {value: relative, horizonSessions: 63, benchmark: benchmark || null, basis: basis === "tr" || basis === "price" ? basis : null},
      chart: {semanticFamily: "legacy", structureBasis: text(prov.structure_basis || record.basis, 24) || "unknown", hasHistory: Array.isArray(record.osc) && record.osc.length > 1},
      provenance: {membership: text(prov.membership, 40) || "unknown", pointInTime: typeof prov.point_in_time === "boolean" ? prov.point_in_time : null,
        historyMode: text(prov.history_mode, 80) || "unknown"},
      qualification: qualification(record, meta)
    };
  }
  // Keep the native chart's data, zoom and crosshair intact; suppress only date
  // labels that physically collide inside this component's available width.
  function fitAxisLabels(root) {
    var view = root.ownerDocument.defaultView, pending = 0, stopped = false;
    function fit() {
      pending = 0; if (stopped || !root.isConnected) return;
      root.querySelectorAll('.mmc-axis').forEach(function (axis) {
        var kept = [], labels = Array.from(axis.querySelectorAll('text'));
        labels.forEach(function (label, index) {
          if (label.dataset.sdcHidden) {
            label.style.removeProperty('visibility'); label.removeAttribute('aria-hidden'); delete label.dataset.sdcHidden;
          }
          var box = label.getBoundingClientRect(); if (!box.width) return;
          if (index === labels.length - 1) {
            while (kept.length && box.left - kept[kept.length - 1].right < 4) {
              var prior = kept.pop().node; prior.style.visibility = 'hidden'; prior.setAttribute('aria-hidden', 'true'); prior.dataset.sdcHidden = 'true';
            }
          }
          if (kept.length && box.left - kept[kept.length - 1].right < 4) {
            label.style.visibility = 'hidden'; label.setAttribute('aria-hidden', 'true'); label.dataset.sdcHidden = 'true';
          } else kept.push({node: label, right: box.right});
        });
      });
    }
    function schedule() { if (!stopped && !pending) pending = view.requestAnimationFrame(fit); }
    var mutations = new view.MutationObserver(schedule);
    mutations.observe(root, {childList: true, subtree: true, characterData: true});
    var sizes = typeof view.ResizeObserver === 'function' ? new view.ResizeObserver(schedule) : null;
    if (sizes) sizes.observe(root);
    schedule();
    return function () { stopped = true; mutations.disconnect(); if (sizes) sizes.disconnect(); if (pending) view.cancelAnimationFrame(pending); };
  }
  function mount(root, payload, options) {
    if (!root || !root.ownerDocument || typeof root.replaceChildren !== "function") throw new TypeError("A DOM element is required");
    var doc = root.ownerDocument, disposed = false, chartCleanup = null;
    function node(tag, cls, value) {
      var e = doc.createElement(tag); if (cls) e.className = cls;
      if (value != null) e.textContent = String(value); return e;
    }
    function cleanChart() {
      if (chartCleanup) { var cleanup = chartCleanup; chartCleanup = null; try { cleanup(); } catch (_) { /* Host cleanup cannot retain old DOM. */ } }
    }
    function render(p, opts) {
      if (disposed) return null;
      cleanChart(); root.replaceChildren();
      var o = obj(opts) ? opts : {}, v = buildView(p, o), lang = v.locale;
      function L(key) { return label(key, lang); }
      var card = node("section", "sdc"); card.lang = lang === "zh" ? "zh-Hans" : "en";
      card.dataset.state = v.state; card.setAttribute("aria-label", L("title"));
      card.setAttribute("aria-busy", v.state === "loading" ? "true" : "false");
      root.appendChild(card);
      if (v.state !== "ready" && v.state !== "stale") {
        var stateTitle = v.state === "denied" && v.reason === "unauthenticated" ? "unauthenticated" : v.state;
        var message = node("div", "sdc-state"); message.setAttribute("role", "status");
        message.appendChild(node("h2", "sdc-title", L(stateTitle)));
        message.appendChild(node("p", "sdc-muted", L(v.state === "incompatible_generation" ? "incompatibleBody" : "unavailableBody")));
        card.appendChild(message); return v;
      }
      var heading = node("header", "sdc-heading"), identity = node("div", "sdc-identity");
      identity.appendChild(node("h2", "sdc-title", v.subject.name));
      identity.appendChild(node("span", "sdc-ticker", v.subject.ticker));
      heading.appendChild(identity);
      heading.appendChild(node("p", "sdc-muted sdc-asof", (v.state === "stale" ? L("stale") + " · " : "") + L("asOf") + " " + v.asOf));
      card.appendChild(heading);
      var facts = node("div", "sdc-facts");
      function fact(title, value, detail, valueClass) {
        var box = node("section", "sdc-fact"); box.appendChild(node("h3", "sdc-label", title));
        box.appendChild(node("p", "sdc-value" + (valueClass ? " " + valueClass : ""), value));
        if (detail) box.appendChild(node("p", "sdc-muted", detail)); facts.appendChild(box);
      }
      var age = v.age.value == null ? L("ageUnknown") :
        (v.age.status === "lower_bound" ? L("atLeast") + " " : "") + v.age.value + (lang === "zh" ? "" : " ") + L("sessions");
      fact(L("phase"), v.phase.label, age);
      fact(L("position"), v.position.value == null ? "—" : v.position.value.toFixed(1) + " / 100", v.position.value == null ? L("unknown") : L("positionNote"), "sdc-numeric");
      fact(L("trend"), v.trend.above200 == null ? "—" : L(v.trend.above200 ? "above" : "below"), v.trend.above200 == null ? L("unknown") : "");
      var rv = v.relative.value, value = rv == null ? "—" : (rv > 0 ? "+" : "") + rv.toFixed(1) + "%";
      fact(L("relative") + (v.relative.benchmark ? " · " + v.relative.benchmark : ""), value,
        rv == null ? L("unknown") : "63 " + L("sessions") + " · " + L(v.relative.basis === "tr" ? "totalReturn" : "priceBasis") + ". " + L("gap"),
        "sdc-numeric" + (rv > 0 ? " sdc-positive" : rv < 0 ? " sdc-negative" : ""));
      card.appendChild(facts);
      var qualifier = node("aside", "sdc-qualification");
      qualifier.appendChild(node("strong", "", L(v.qualification)));
      qualifier.appendChild(node("p", "sdc-muted", L("modelBody"))); card.appendChild(qualifier);
      var history = node("section", "sdc-history"); history.appendChild(node("h3", "sdc-subtitle", L("chart")));
      history.appendChild(node("p", "sdc-muted", L("chartNote")));
      var chart = node("div", "sdc-chart"); history.appendChild(chart); card.appendChild(history);
      if (v.chart.hasHistory && typeof o.renderChart === "function") {
        try {
          var handle = o.renderChart(chart, {record: recordFor(p, o), meta: p.meta, semanticFamily: "legacy", asOf: v.asOf, locale: lang});
          if (typeof handle === "function") chartCleanup = handle;
          else if (handle && typeof handle.destroy === "function") chartCleanup = function () { handle.destroy(); };
          var hostCleanup = chartCleanup, stopLabelLayout = fitAxisLabels(chart);
          chartCleanup = function () { stopLabelLayout(); if (hostCleanup) hostCleanup(); };
        } catch (_) { chart.replaceChildren(node("p", "sdc-muted", L("chartFailed"))); }
      } else chart.appendChild(node("p", "sdc-muted", L("chartMissing")));
      var actions = node("div", "sdc-actions");
      function action(key, callback) {
        var b = node("button", "sdc-action", L(key)); b.type = "button";
        if (typeof callback !== "function") { b.disabled = true; b.title = L("hostRequired"); }
        else b.addEventListener("click", function () {
          if (!disposed && root.contains(b)) callback({id: v.subject.id, family: v.subject.family, asOf: v.asOf, locale: lang});
        });
        actions.appendChild(b);
      }
      action("members", o.onMembers); action("open", o.onOpenCycles); action("source", o.onSources);
      card.appendChild(actions); card.appendChild(node("p", "sdc-muted sdc-footer", L("footer")));
      return v;
    }
    render(payload, options);
    return {
      update: function (nextPayload, nextOptions) { return render(nextPayload, nextOptions); },
      destroy: function () { if (!disposed) { disposed = true; cleanChart(); root.replaceChildren(); } }
    };
  }
  return Object.freeze({buildView: buildView, mount: mount});
});
