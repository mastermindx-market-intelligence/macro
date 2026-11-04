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
    incompatible_generation: ["Snapshots do not match", "快照版本不一致"],
    incompatibleBody: ["This reading is withheld rather than mixing source dates or publication versions.", "暂不显示此读数，以免混用不同的日期或发布版本。"],
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
    chartInvalid: ["History withheld: observations are invalid or out of order. Core facts remain available.", "历史暂不显示：观测值无效或顺序有误。核心事实仍可查看。"],
    chartUnverified: ["History withheld until its source part is verified. Core facts remain available.", "历史需待来源分块核验后显示。核心事实仍可查看。"],
    chartFailed: ["History could not be drawn; the facts above are unchanged", "历史图暂无法绘制，上方事实读数不受影响"],
    open: ["Open full Cycles evidence", "查看完整周期证据"],
    members: ["View constituent evidence", "查看成分股证据"],
    source: ["Sources & calculation", "数据来源与计算方法"],
    hostRequired: ["Available when connected to the owning route", "接入原有页面后可用"],
    exact: ["Exact values", "精确数值"], coordinate: ["Source year coordinate", "源数据年份坐标"],
    cycleValue: ["Legacy position · 0–100", "旧版位置 · 0–100"],
    exactNote: ["Original plotted observations. Decimal-year coordinates are not publication dates.", "原始绘图观测值。小数年份坐标并非发布日期。"],
    previous: ["Previous values", "上一页数值"], next: ["Next values", "下一页数值"],
    showing: ["Showing", "显示"], of: ["of", "共"], points: ["observations", "个观测值"],
    sourceDetails: ["Evidence details", "证据详情"], publication: ["Publication identity", "发布版本身份"],
    unverified: ["Unverified snapshot", "未核验快照"], classifier: ["Phase classifier", "阶段分类器"],
    historyBasis: ["Price-history basis", "价格历史口径"], membership: ["Membership basis", "成员口径"],
    historyMode: ["History interpretation", "历史解释"], seriesStatus: ["Plotted-history verification", "所绘历史核验"],
    currentReconstruction: ["Reconstructed history; not an observed point-in-time record", "重建历史，并非当时观测记录"],
    singleInstrument: ["Single instrument; not a claim about historical constituents", "单一证券，不代表已核验历史成分"],
    currentMembers: ["Current membership; historical constituents not established", "当前成员口径，历史成分尚未确认"],
    fallback: ["Declared total-return fallback", "已声明的总回报回退"],
    verified: ["Verified by the original source owner", "已由原有来源核验"],
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
  function publicationGate(o, locale) {
    if (o.requirePublication !== true) return null;
    var e = o.evidence;
    if (!obj(e) || e.schema !== 'sector_cycles.evidence.v1') return outcome('unavailable', 'receipt_unavailable', locale);
    if (e.status === 'pending') return outcome('loading', 'verification_pending', locale);
    if (e.status === 'superseded' || e.status === 'incompatible_publication') return outcome('incompatible_generation', e.status, locale);
    if (e.status !== 'verified') return outcome('unavailable', 'publication_' + text(e.status, 40), locale);
    if (!obj(e.parts) || e.parts.core !== 'verified') return outcome('unavailable', 'core_receipt_unverified', locale);
    var validId = function (id) { return typeof id === 'string' && /^cycp1-[0-9a-f]{64}$/.test(id); };
    if (!validId(e.publicationId) || !validId(o.expectedPublicationId)) return outcome('unavailable', 'publication_unbound', locale);
    if (e.publicationId !== o.expectedPublicationId || e.region !== 'us') return outcome('incompatible_generation', 'publication_mismatch', locale);
    if (!date(e.asOf)) return outcome('unavailable', 'receipt_date_invalid', locale);
    if (o.expectedSpine != null) {
      var want = o.expectedSpine, got = e.spine;
      if (o.family !== 'sectors' || !obj(want) || !obj(got) ||
          want.schema !== 'sector_cycles.sector_spine.v1' || want.scope !== 'us_sectors_11' ||
          !/^[0-9a-f]{64}$/.test(want.sha256 || '') ||
          want.schema !== got.schema || want.scope !== got.scope || want.sha256 !== got.sha256) {
        return outcome('incompatible_generation', 'spine_mismatch', locale);
      }
    }
    return null;
  }
  function historyOf(record, options) {
    var sourcePart = options.family === 'sectors' ? 'core' : 'series';
    if (options.requirePublication === true && sourcePart === 'series' && (!obj(options.evidence.parts) || options.evidence.parts.series !== 'verified')) {
      return {state: 'unverified', sourcePart: sourcePart, rows: []};
    }
    var points = record.osc;
    if (!Array.isArray(points) || points.length < 2) return {state: 'unavailable', rows: []};
    var previous = -Infinity, rows = [];
    for (var i = 0; i < points.length; i++) {
      var p = points[i], x = obj(p) ? finite(p.x) : null, value = obj(p) ? finite(p.v) : null;
      if (x == null || value == null || value < 0 || value > 100 || x <= previous) return {state: 'invalid', rows: []};
      rows.push({x: x, value: value}); previous = x;
    }
    return {state: 'ready', sourcePart: sourcePart, rows: rows};
  }
  function buildView(payload, options) {
    var o = obj(options) ? options : {}, locale = o.locale === "zh" ? "zh" : "en";
    // The payload is not even evaluated until the host's access boundary settles.
    if (o.accessState == null || o.accessState === "pending") return outcome("loading", "access_pending", locale);
    if (o.accessState !== "allowed") return outcome("denied", o.accessState === "unauthenticated" ? "unauthenticated" : "forbidden", locale);
    if (o.locale !== "en" && o.locale !== "zh") return outcome("unavailable", "unsupported_locale", locale);
    if (o.dataState === "loading") return outcome("loading", "source_loading", locale);
    if (o.dataState !== "ready" && o.dataState !== "stale") return outcome("unavailable", "source_unavailable", locale);
    var gate = publicationGate(o, locale); if (gate) return gate;
    if (!own(KINDS, o.family) || typeof o.id !== "string" || !o.id || !obj(payload) || !obj(payload.meta)) return outcome("unavailable", "invalid_selection", locale);
    var meta = payload.meta, asOf = date(meta.asOf);
    if (meta.region != null && meta.region !== "us") return outcome("unavailable", "unsupported_region", locale);
    if (!asOf || (o.expectedAsOf != null && !date(o.expectedAsOf))) return outcome("unavailable", "invalid_asof", locale);
    if (o.expectedAsOf != null && o.expectedAsOf !== asOf) return outcome("incompatible_generation", "snapshot_mismatch", locale);
    if (o.requirePublication === true && (o.evidence.asOf !== asOf || o.evidence.region !== (meta.region || "us"))) return outcome("incompatible_generation", "receipt_payload_mismatch", locale);
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
    var history = historyOf(record, o);
    return {
      state: o.dataState, locale: locale, asOf: asOf,
      subject: {id: record.id, kind: record.kind, family: o.family,
        ticker: text(record.ticker, 40), name: text(locale === "zh" ? (record.name_zh || record.name) : record.name) || text(record.ticker) || record.id},
      phase: {key: phase, label: phase ? PHASES[phase][locale === "zh" ? 1 : 0] : label("unknown", locale), source: phaseSource, semanticFamily: phase ? "ontology" : "unavailable"},
      position: {value: position, semanticFamily: "ontology"}, age: phase ? phaseAge(n) : {value: null, status: "unavailable"},
      trend: {above200: typeof n.above200d === "boolean" ? n.above200d : null},
      relative: {value: relative, horizonSessions: 63, benchmark: benchmark || null, basis: basis === "tr" || basis === "price" ? basis : null},
      chart: {semanticFamily: "legacy", structureBasis: text(prov.structure_basis || record.basis, 24) || "unknown", hasHistory: history.state === "ready"},
      history: history,
      publication: o.requirePublication === true ? {id: o.evidence.publicationId, status: "verified", asOf: o.evidence.asOf, parts: Object.assign({}, o.evidence.parts || {})} : {id: null, status: "unverified"},
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
    var doc = root.ownerDocument, disposed = false, chartCleanup = null, chartHandle = null, previousKey = null, previousPayload = null;
    function node(tag, cls, value) {
      var e = doc.createElement(tag); if (cls) e.className = cls;
      if (value != null) e.textContent = String(value); return e;
    }
    function cleanChart() {
      chartHandle = null;
      if (chartCleanup) { var cleanup = chartCleanup; chartCleanup = null; try { cleanup(); } catch (_) { /* Host cleanup cannot retain old DOM. */ } }
    }
    function render(p, opts) {
      if (disposed) return null;
      var o = obj(opts) ? opts : {}, v = buildView(p, o), lang = v.locale;
      var key = v.subject ? [v.subject.family, v.subject.id, v.asOf, v.publication.id || 'unverified'].join('/') : null;
      var hadFocus = !!doc.activeElement && root.contains(doc.activeElement);
      var held = {}, same = key && key === previousKey && (v.publication.id || p === previousPayload);
      if (same) {
        var oldValues = root.querySelector('.sdc-values'), oldSources = root.querySelector('.sdc-sources');
        held.values = !!oldValues && oldValues.open; held.sources = !!oldSources && oldSources.open;
        held.offset = oldValues ? Number(oldValues.dataset.offset) || 0 : 0;
        held.focus = root.contains(doc.activeElement) ? doc.activeElement.getAttribute('data-sdc-focus') : null;
        try { if (chartHandle && typeof chartHandle.getView === 'function') held.zoom = chartHandle.getView(); } catch (_) {}
      }
      cleanChart(); root.replaceChildren(); previousKey = key; previousPayload = key ? p : null;
      function L(key) { return label(key, lang); }
      var card = node("section", "sdc"); card.lang = lang === "zh" ? "zh-Hans" : "en";
      card.dataset.state = v.state; card.setAttribute("aria-label", L("title"));
      card.setAttribute("aria-busy", v.state === "loading" ? "true" : "false");
      root.appendChild(card);
      if (v.state !== "ready" && v.state !== "stale") {
        var stateTitle = v.state === "denied" && v.reason === "unauthenticated" ? "unauthenticated" : v.state;
        var message = node("div", "sdc-state"); message.setAttribute("role", "status");
        var stateHeading = node("h2", "sdc-title", L(stateTitle)); stateHeading.tabIndex = -1;
        message.appendChild(stateHeading);
        message.appendChild(node("p", "sdc-muted", L(v.state === "incompatible_generation" ? "incompatibleBody" : "unavailableBody")));
        card.appendChild(message);
        if (hadFocus) stateHeading.focus({preventScroll: true});
        return v;
      }
      var heading = node("header", "sdc-heading"), identity = node("div", "sdc-identity");
      var subjectHeading = node("h2", "sdc-title", v.subject.name); subjectHeading.tabIndex = -1; subjectHeading.dataset.sdcFocus = "heading";
      identity.appendChild(subjectHeading);
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
      var history = node("section", "sdc-history"); history.dataset.state = v.history.state; history.appendChild(node("h3", "sdc-subtitle", L("chart")));
      history.appendChild(node("p", "sdc-muted", L("chartNote")));
      var chart = node("div", "sdc-chart"); history.appendChild(chart); card.appendChild(history);
      if (v.chart.hasHistory && typeof o.renderChart === "function") {
        try {
          var handle = o.renderChart(chart, {record: recordFor(p, o), meta: p.meta, semanticFamily: "legacy", asOf: v.asOf, locale: lang});
          chartHandle = handle;
          if (held.zoom && Array.isArray(held.zoom) && held.zoom.length === 2 && held.zoom.every(function (n) { return finite(n) != null; }) && held.zoom[0] < held.zoom[1] && handle && typeof handle.setView === 'function') handle.setView(held.zoom, false);
          if (typeof handle === "function") chartCleanup = handle;
          else if (handle && typeof handle.destroy === "function") chartCleanup = function () { handle.destroy(); };
          var hostCleanup = chartCleanup, stopLabelLayout = fitAxisLabels(chart);
          chartCleanup = function () { stopLabelLayout(); if (hostCleanup) hostCleanup(); };
        } catch (_) { chart.replaceChildren(node("p", "sdc-muted", L("chartFailed"))); }
      } else chart.appendChild(node("p", "sdc-muted", L(v.history.state === "invalid" ? "chartInvalid" : v.history.state === "unverified" ? "chartUnverified" : "chartMissing")));
      if (v.history.state === 'ready') {
        var values = node('details', 'sdc-values'), valueSummary = node('summary', '', L('exact'));
        valueSummary.dataset.sdcFocus = 'values'; values.appendChild(valueSummary); values.open = !!held.values;
        values.appendChild(node('p', 'sdc-muted', L('exactNote')));
        var table = node('table', 'sdc-table'), caption = node('caption', 'sdc-muted', L('asOf') + ' ' + v.asOf);
        table.appendChild(caption);
        var head = node('thead'), headRow = node('tr');
        ['coordinate', 'cycleValue'].forEach(function (key) { var th = node('th', '', L(key)); th.scope = 'col'; headRow.appendChild(th); });
        head.appendChild(headRow); table.appendChild(head);
        var body = node('tbody'); table.appendChild(body); values.appendChild(table);
        var pager = node('div', 'sdc-pager'), previous = node('button', 'sdc-page', L('previous'));
        var next = node('button', 'sdc-page', L('next')), count = node('p', 'sdc-muted'), offset = Math.min(held.offset || 0, Math.floor((v.history.rows.length - 1) / 50) * 50);
        previous.dataset.sdcFocus = 'previous'; next.dataset.sdcFocus = 'next';
        previous.type = next.type = 'button'; count.setAttribute('aria-live', 'polite');
        function pageValues() {
          body.replaceChildren(); values.dataset.offset = String(offset);
          v.history.rows.slice(offset, offset + 50).forEach(function (point) {
            var row = node('tr'); row.appendChild(node('td', '', point.x)); row.appendChild(node('td', '', point.value)); body.appendChild(row);
          });
          previous.disabled = offset === 0; next.disabled = offset + 50 >= v.history.rows.length;
          count.textContent = L('showing') + ' ' + (offset + 1) + '–' + Math.min(offset + 50, v.history.rows.length) + ' / ' + v.history.rows.length;
        }
        previous.addEventListener('click', function () { offset = Math.max(0, offset - 50); pageValues(); });
        next.addEventListener('click', function () { if (offset + 50 < v.history.rows.length) offset += 50; pageValues(); });
        if (v.history.rows.length > 50) { pager.appendChild(previous); pager.appendChild(next); values.appendChild(pager); }
        values.appendChild(count); pageValues(); history.appendChild(values);
      }
      var sources = node('details', 'sdc-sources'), sourceSummary = node('summary', '', L('sourceDetails'));
      sources.appendChild(sourceSummary); sources.open = !!held.sources; sourceSummary.dataset.sdcFocus = 'sources';
      var sourceList = node('dl', 'sdc-source-list');
      function sourceFact(key, value) { sourceList.appendChild(node('dt', '', L(key))); sourceList.appendChild(node('dd', '', value)); }
      sourceFact('asOf', v.asOf);
      sourceFact('publication', v.publication.id || L('unverified'));
      sourceFact('classifier', v.phase.source);
      sourceFact('historyBasis', v.chart.structureBasis === 'price' ? L('priceBasis') : v.chart.structureBasis === 'tr' ? L('totalReturn') : v.chart.structureBasis === 'tr_fallback' ? L('fallback') : L('unknown'));
      sourceFact('membership', v.provenance.membership === 'single_instrument' ? L('singleInstrument') : v.provenance.membership === 'current_membership' ? L('currentMembers') : L('unknown'));
      sourceFact('historyMode', v.provenance.historyMode === 'reconstructed_price_history' ? L('currentReconstruction') : L('unknown'));
      sourceFact('seriesStatus', v.publication.status === 'verified' && (v.history.sourcePart === 'core' || (v.publication.parts && v.publication.parts.series === 'verified')) ? L('verified') : L('unverified'));
      sources.appendChild(sourceList);
      var actions = node("div", "sdc-actions");
      function action(key, callback) {
        var b = node("button", "sdc-action", L(key)); b.type = "button";
        var actionKey = key === "open" ? "cycles" : key === "source" ? "sources" : "members"; b.dataset.sdcFocus = "action-" + actionKey;
        if (typeof callback !== "function") { b.disabled = true; b.title = L("hostRequired"); }
        else b.addEventListener("click", function () {
          if (!disposed && root.contains(b)) callback({id: v.subject.id, family: v.subject.family, asOf: v.asOf, locale: lang, actionKey: actionKey, invoker: b});
        });
        actions.appendChild(b);
      }
      action("members", o.onMembers); action("open", o.onOpenCycles);
      action("source", typeof o.onSources === 'function' ? o.onSources : function () { sources.open = true; sourceSummary.focus(); });
      card.appendChild(actions); card.appendChild(sources); card.appendChild(node("p", "sdc-muted sdc-footer", L("footer")));
      if (hadFocus) {
        var focusTarget = held.focus && Array.from(root.querySelectorAll('[data-sdc-focus]')).find(function (n) { return n.dataset.sdcFocus === held.focus; });
        if (!focusTarget || focusTarget.disabled) focusTarget = subjectHeading;
        focusTarget.focus({preventScroll: true});
      }
      return v;
    }
    render(payload, options);
    return {
      update: function (nextPayload, nextOptions) { return render(nextPayload, nextOptions); },
      destroy: function () { if (!disposed) { disposed = true; cleanChart(); root.replaceChildren(); } }
    };
  }
  // Explicit host integration. The original Cycles verifier is the sole source
  // of publication acceptance; this adapter neither fetches nor re-hashes data.
  function mountFromNative(root, owner, options) {
    if (!root || !root.ownerDocument) throw new TypeError('A DOM element is required');
    var current = Object.assign({}, options || {}), component = null, disposed = false;
    var doc = root.ownerDocument;
    var events = ['sc:publication-ready', 'sc:cycles-ready', 'sc:series-ready', 'sc:series-error', 'sc:extras-ready'];
    function receipt() {
      try { return owner && typeof owner.SectorCyclesEvidence === 'function' ? owner.SectorCyclesEvidence() : null; }
      catch (_) { return null; }
    }
    function currentReceipt(expected) {
      var now = receipt();
      var gate = publicationGate(Object.assign({}, current, {requirePublication: true, evidence: now}), current.locale === 'zh' ? 'zh' : 'en');
      return !gate && now.publicationId === expected.publicationId && now.asOf === expected.asOf && now.region === expected.region;
    }
    function refresh() {
      if (disposed) return;
      var next = Object.assign({}, current, {requirePublication: true, evidence: null}), payload = null;
      if (next.accessState === 'allowed' && (next.dataState === 'ready' || next.dataState === 'stale')) {
        next.evidence = receipt();
        if (!publicationGate(next, next.locale === 'zh' ? 'zh' : 'en')) {
          try {
            payload = owner.SECTOR_CYCLES;
            if (!currentReceipt(next.evidence)) {
              payload = null; next.evidence = Object.assign({}, next.evidence, {status: 'superseded'});
            }
          } catch (_) { payload = null; next.dataState = 'unavailable'; }
        }
      }
      var bound = next.evidence;
      ['onMembers', 'onOpenCycles', 'onSources'].forEach(function (name) {
        if (typeof current[name] !== 'function') return;
        var callback = current[name];
        next[name] = function (selection) {
          if (disposed || current.accessState !== 'allowed' || !bound || !currentReceipt(bound)) { refresh(); return; }
          callback(Object.assign({}, selection, {publicationId: bound.publicationId}));
        };
      });
      if (component) component.update(payload, next);
      else component = mount(root, payload, next);
    }
    events.forEach(function (name) { doc.addEventListener(name, refresh); });
    refresh();
    return {
      update: function (nextOptions) { if (!disposed) { current = Object.assign({}, nextOptions || {}); refresh(); } },
      destroy: function () {
        if (disposed) return; disposed = true;
        events.forEach(function (name) { doc.removeEventListener(name, refresh); });
        if (component) component.destroy();
      }
    };
  }
  return Object.freeze({buildView: buildView, mount: mount, mountFromNative: mountFromNative});
});
