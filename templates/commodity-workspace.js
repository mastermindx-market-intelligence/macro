/* Commodity workspace: URL-backed context, exact comparisons, portable research drafts. */
(function () {
  "use strict";
  const TABS = ["overview", "explore", "relationships", "compare", "research"];
  const WINDOWS = ["1m", "5", "20", "60", "252"];
  const CONDITION = "mmx.commodities.research_condition.v1";
  const isNumber = value => typeof value === "number" && Number.isFinite(value);
  function returnScale(values) {
    return values.reduce((scale, value) => isNumber(value) ? Math.max(scale, Math.abs(value)) : scale, 0);
  }
  function returnGeometry(value, scale) {
    const available = isNumber(value);
    return {available, direction: available ? (value > 0 ? "positive" : value < 0 ? "negative" : "flat") : "unavailable",
      width: available && isNumber(scale) && scale > 0 ? Math.min(50, Math.abs(value) / scale * 50) : 0};
  }
  const clone = value => JSON.parse(JSON.stringify(value));
  function stable(value, depth = 0) {
    if (depth > 64) throw new RangeError("Research draft nesting exceeds its limit");
    if (Array.isArray(value)) return value.map(item => stable(item, depth + 1));
    if (value && typeof value === "object") return Object.fromEntries(Object.keys(value).sort().map(k => [k,stable(value[k], depth + 1)]));
    return value;
  }
  function validDate(value) {
    if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
    const parsed = new Date(value + "T00:00:00Z");
    return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
  }
  function normalizeState(candidate, data) {
    const ids = new Set(data.assets.map(a => a.id));
    const fallback = ids.has("oil") ? "oil" : (data.assets[0] || {}).id || "";
    const asset = ids.has(candidate.asset) ? candidate.asset : fallback;
    const hypotheses = new Set((data.hypotheses[asset] || []).map(h => h.id).concat("unresolved"));
    const compare = Array.from(new Set((Array.isArray(candidate.compare) ? candidate.compare : ["oil", "gold", "copper", "silver"]).filter(id => ids.has(id)))).slice(0, 4);
    return {
      tab: TABS.includes(candidate.tab) ? candidate.tab : "overview",
      asset: asset,
      window: WINDOWS.includes(String(candidate.window)) ? String(candidate.window) : "1m",
      compare: compare,
      hypothesis: hypotheses.has(candidate.hypothesis) ? candidate.hypothesis : "unresolved"
    };
  }
  function readState(hash, data) {
    if (typeof hash !== "string" || hash.length > 2000 || !hash.startsWith("#cw/")) return normalizeState({}, data);
    const parts = hash.slice(4).split("?");
    const route = parts[0].split("/");
    const params = new URLSearchParams(parts[1] || "");
    return normalizeState({tab: route[0], asset: route[1], window: params.get("window"),
      compare: params.has("compare") ? params.get("compare").split(",").filter(Boolean) : undefined,
      hypothesis: params.get("hypothesis")}, data);
  }
  function stateHash(state) {
    const p = new URLSearchParams();
    p.set("window", state.window); p.set("compare", state.compare.join(",")); p.set("hypothesis", state.hypothesis);
    return "#cw/" + state.tab + "/" + state.asset + "?" + p.toString();
  }
  function companyReturnHref(href, state, pageHref) {
    try {
      const target = new URL(href), page = new URL(pageHref);
      if (target.origin !== "https://app.mastermind-x.com" || target.pathname !== "/analysis"
          || target.username || target.password || target.hash
          || target.searchParams.get("page") !== "intelligence") return href;
      const origins = ["https://www.mastermind-x.com", "https://mastermind-x.com", "https://beta.mastermind-x.com"];
      if (!origins.includes(page.origin) || page.pathname !== "/commodities.html"
          || page.username || page.password) return href;
      // Carry only the owned investigation state; no page query or supplied return target.
      // render() precedes pushState(), so derive the new hash from state itself.
      page.search = "";
      page.hash = stateHash(state);
      target.searchParams.set("from", "macro");
      target.searchParams.set("ret", page.href);
      return target.href;
    } catch (_) { return href; }
  }
  function conditionSemantics(data, asset, window, hypothesis) {
    const selected = data.assets.find(a => a.id === asset) || null;
    const explanation = (data.hypotheses[asset] || []).find(h => h.id === hypothesis) || null;
    const ids = {oil:["oil_inflation_duration_derate","oil_slide_disinflation_duration_rerate"],gold:["real_rate_peak_gold_rerate"]};
    return {as_of:data.as_of, basis:"publisher_price_series", contract:null, expiry_timezone:"UTC",
      effect:"export_only", monitoring_active:false, source_dependencies:clone(data.sources), requires_monitor_owner_qualification:true,
      metric_contract:{source_id:"commodities",owner_path:"data/commodity/complex_latest.json",member_key:{name:asset},
        field:"velocity.r" + window,unit:"%",window_sessions:window,series_identity:null,contract_roll_method:null,
        method_reference:"engine/commodity_index.py",evaluation_qualified:false},
      as_saved_evidence:{schema:"mmx.commodities.as_saved_evidence.v1",workspace_fingerprint:data.fingerprint,
        projection_revision:data.projection_revision,asset:clone(selected),hypothesis:clone(explanation),
        physical:asset === "oil" ? clone(data.physical || null) : null,
        gold_physical:asset === "gold" ? clone(data.gold_physical || null) : null,
        chains:clone(data.chains.filter(c => (ids[asset] || []).includes(c.id))),rates:clone(data.rates),fx:clone(data.fx),ratios:clone(data.ratios || []),
        source_receipts:clone(data.sources),live:false}};
  }
  function checkDraft(draft, data, imported) {
    const d = draft && typeof draft === "object" && !Array.isArray(draft) ? draft : {};
    const errors = [];
    if (d.schema !== CONDITION) errors.push("schema");
    const assetKnown = data.assets.some(a => a.id === d.asset);
    if (!assetKnown) errors.push("asset");
    if (d.metric !== "return_pct" || d.unit !== "%") errors.push("metric_unit");
    if (!Number.isInteger(d.window_sessions) || ![5, 20, 60, 252].includes(d.window_sessions)) errors.push("window_sessions");
    if (!["gt", "gte", "lt", "lte"].includes(d.operator)) errors.push("operator");
    if (!isNumber(d.threshold)) errors.push("threshold");
    if (!validDate(d.expires_on) || !validDate(data.as_of) || d.expires_on < data.as_of) errors.push("expires_on");
    if (d.snapshot_fingerprint !== data.fingerprint) errors.push("snapshot_fingerprint");
    const choices = assetKnown && Array.isArray(data.hypotheses[d.asset]) ? data.hypotheses[d.asset] : [];
    if (!new Set(choices.map(h => h.id).concat("unresolved")).has(d.hypothesis)) errors.push("hypothesis");
    if (errors.length) return {value: null, errors: errors};
    const semantics = conditionSemantics(data,d.asset,d.window_sessions,d.hypothesis);
    try {
      Object.entries(semantics).forEach(([key,expected]) => {
        if ((imported && !Object.prototype.hasOwnProperty.call(d,key)) || (Object.prototype.hasOwnProperty.call(d,key) && JSON.stringify(stable(d[key])) !== JSON.stringify(stable(expected)))) errors.push(key);
      });
    } catch (_) { errors.push("semantic_structure"); }
    if (errors.length) return {value:null,errors:errors};
    return {errors: [], value: {
      schema: CONDITION, asset: d.asset, metric: d.metric, unit: "%", window_sessions: d.window_sessions,
      operator: d.operator, threshold: d.threshold, expires_on: d.expires_on, hypothesis: d.hypothesis,
      snapshot_fingerprint: data.fingerprint, ...semantics
    }};
  }
  const api = {normalizeState, readState, stateHash, companyReturnHref, checkDraft, validDate, conditionSemantics, returnScale, returnGeometry};
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof document === "undefined") return;
  const root = document.getElementById("commodity-workspace");
  const json = document.getElementById("cw-data");
  if (!root || !json) return;
  let data;
  try { data = JSON.parse(json.textContent); } catch (_) { return; }
  if (data.schema !== "mmx.commodities.workspace.v1" || !Array.isArray(data.assets) || !Array.isArray(data.chains)
    || !data.hypotheses || !data.sources || !data.rates || !data.fx) return;
  const all = selector => Array.from(root.querySelectorAll(selector));
  const lang = () => document.documentElement.dataset.lang === "zh" ? "zh" : "en";
  const text = (en, zh) => lang() === "zh" ? zh : en;
  const form = root.querySelector("#cw-research-form");
  const status = root.querySelector("#cw-export-status");
  const compareStatus = root.querySelector("#cw-compare-status");
  // Reuse the shared owner's lazy loader and public API; no page-owned loader.
  const brainEntry = root.querySelector("#cw-brain-entry");
  const brainStatus = root.querySelector("#cw-brain-status");
  let brainFocusBound = false;
  function syncBrainEntry() {
    if (!brainEntry || !brainStatus) return;
    const boot = document.getElementById("mmb-boot");
    const mounted = Boolean(window.MMBrain && typeof window.MMBrain.open === "function");
    const available = mounted || Boolean(boot);
    brainEntry.hidden = !available;
    document.body.classList.toggle("cw-brain-inline", available);
    const wasBusy = brainEntry.getAttribute("aria-busy") === "true";
    const busy = !mounted && boot && boot.getAttribute("aria-busy") === "true";
    brainEntry.setAttribute("aria-busy", String(Boolean(busy)));
    if (busy) brainStatus.textContent = text("Opening Mastermind…", "正在打开操盘大脑…");
    else if (mounted) brainStatus.textContent = "";
    else if (wasBusy) brainStatus.textContent = text("Could not open Mastermind. Try again.", "未能打开操盘大脑，请重试。");
    if (boot) brainObserver.observe(boot, {attributes:true, attributeFilter:["aria-busy"]});
  }
  const brainObserver = new MutationObserver(syncBrainEntry);
  if (brainEntry) {
    brainEntry.addEventListener("click", () => {
      const cfg = window.MM_BRAIN_CFG;
      if (cfg && !brainFocusBound) {
        const previous = cfg.onClose;
        cfg.onClose = () => {
          if (typeof previous === "function" && previous() === true) return true;
          brainEntry.focus({preventScroll:true});
          return document.activeElement === brainEntry;
        };
        brainFocusBound = true;
      }
      if (window.MMBrain && typeof window.MMBrain.open === "function") window.MMBrain.open();
      else {
        const boot = document.getElementById("mmb-boot");
        if (boot) boot.click();
      }
      syncBrainEntry();
    });
    brainObserver.observe(document.body, {childList:true});
    syncBrainEntry();
  }
  const drafts = new Map();
  let state = readState(window.location.hash, data);
  let renderedAsset = "";
  let returnContext = null;
  function captureForm() {
    if (!form || !renderedAsset) return;
    drafts.set(renderedAsset, {operator: form.elements.operator.value, threshold: form.elements.threshold.value,
      expires_on: form.elements.expires_on.value, window_sessions: form.elements.window_sessions.value, hypothesis:state.hypothesis});
  }
  function renderNoteWindow() {
    const window = form ? form.elements.window_sessions.value : "";
    all("[data-cw-note-window]").forEach(el => {
      el.textContent = window ? window + text(" trading sessions", "个交易日") : text("Choose a lookback window", "请选择回看窗口");
    });
  }
  function displayReturn(cell, value) {
    cell.textContent = isNumber(value) ? (value > 0 ? "+" : "") + value.toFixed(1) + "%" : text("Unavailable", "暂不可用");
    cell.classList.add("cw-number");
    cell.classList.toggle("cw-up", isNumber(value) && value > 0);
    cell.classList.toggle("cw-down", isNumber(value) && value < 0);
  }
  function revealActiveTab() {
    const strip = root.querySelector("[data-cw-tablist]");
    const selected = strip && strip.querySelector('[aria-selected="true"]');
    if (!selected) return;
    const box = selected.getBoundingClientRect(), viewport = strip.getBoundingClientRect();
    if (box.left < viewport.left || box.right > viewport.right) {
      strip.scrollLeft += box.left - viewport.left - (viewport.width - box.width) / 2;
    }
  }
  window.addEventListener("resize", revealActiveTab);
  if (document.fonts) document.fonts.ready.then(revealActiveTab);
  function render() {
    all("[data-cw-overview-only]").forEach(el => { el.hidden=state.tab !== "overview"; });
    all("[data-cw-panel]").forEach(el => { el.hidden = el.dataset.cwPanel !== state.tab; });
    all("[data-cw-tab]").forEach(el => {
      const active = el.dataset.cwTab === state.tab;
      el.setAttribute("aria-selected", String(active)); el.tabIndex = active ? 0 : -1;
    });
    revealActiveTab();
    all("[data-cw-asset]").forEach(el => { el.hidden = el.dataset.cwAsset !== state.asset; });
    all("[data-cw-select]").forEach(el => el.setAttribute("aria-pressed", String(el.dataset.cwSelect === state.asset)));
    if (state.tab === "explore") {
      const strip = root.querySelector(".cw-instrument-strip");
      const selected = strip && strip.querySelector('[data-cw-select="' + state.asset + '"]');
      if (selected) {
        const box = selected.getBoundingClientRect(), viewport = strip.getBoundingClientRect();
        if (box.left < viewport.left || box.right > viewport.right) {
          strip.scrollLeft += box.left - viewport.left - (viewport.width - box.width) / 2;
        }
      }
    }
    all("[data-cw-chain-asset]").forEach(el => { el.hidden = el.dataset.cwChainAsset !== state.asset; });
    const emptyChain = root.querySelector("[data-cw-no-chain]");
    if (emptyChain) emptyChain.hidden = data.chains.some(c => state.asset === "oil" ? c.id.includes("oil") : state.asset === "gold" && c.id.includes("gold"));
    all("[data-cw-hypothesis]").forEach(group => group.querySelectorAll("input").forEach(input => {
      input.checked = input.value === (group.dataset.cwHypothesis === state.asset ? state.hypothesis : "unresolved");
    }));
    all("[data-cw-explanation]").forEach(el => {
      const own = el.dataset.cwExplanation.split(":");
      el.hidden = own[1] !== (own[0] === state.asset ? state.hypothesis : "unresolved");
    });
    all("[data-cw-relationship-asset]").forEach(el => { el.value = state.asset; });
    const chosen = (data.hypotheses[state.asset] || []).find(h => h.id === state.hypothesis);
    const selectedAsset = data.assets.find(a => a.id === state.asset);
    const investigationTitle = root.querySelector("#cw-investigation-title");
    if (investigationTitle) {
      investigationTitle.textContent = (selectedAsset ? selectedAsset.label[lang()] + " · " : "") + (chosen ? chosen.label[lang()] : text("Cause unresolved", "原因未明"));
      root.querySelector("#cw-investigation-state").textContent = chosen && chosen.id !== "unresolved"
        ? text("Selected for investigation. The evidence below has not established this explanation.", "这是所选的研究解释；下方证据尚未确立这一解释。")
        : text("Compare alternative explanations before drawing a conclusion.", "得出结论前，请比较不同解释。");
      root.querySelector("#cw-investigation-mechanism").textContent = chosen ? chosen.mechanism[lang()]
        : text("A commodity-specific explanation is not available. Review the price evidence and physical-market coverage.", "本品种暂无专属解释，请先复核价格证据及实物市场覆盖。");
      root.querySelector("#cw-investigation-support").textContent = chosen ? chosen.confirm[lang()] : "";
      root.querySelector("#cw-investigation-invalidate").textContent = chosen ? chosen.invalidate[lang()] : "";
      root.querySelector("#cw-investigation-tests").hidden = !chosen;
    }
    all("[data-cw-compare]").forEach(el => { el.checked = state.compare.includes(el.value); });
    all("[data-cw-compare-row]").forEach(el => { el.hidden = !state.compare.includes(el.dataset.cwCompareRow); });
    all("[data-cw-window]").forEach(el => { el.value = state.window; });
    all("[data-cw-return-cell]").forEach(cell => {
      const asset = data.assets.find(a => a.id === cell.dataset.cwReturnCell);
      displayReturn(cell, state.window === "1m" ? asset.change_1m_pct : asset.returns[state.window]);
    });
    const compareValues = data.assets.filter(a => state.compare.includes(a.id)).map(a => state.window === "1m" ? a.change_1m_pct : a.returns[state.window]);
    const compareScale = returnScale(compareValues);
    const windowLabel = state.window === "1m" ? text("One month · publisher comparison", "一个月 · 发布方口径") : state.window + text(" trading sessions", "个交易日");
    all("[data-cw-compare-plot]").forEach(row => {
      const asset = data.assets.find(a => a.id === row.dataset.cwComparePlot);
      row.hidden = !state.compare.includes(asset.id);
      const value = state.window === "1m" ? asset.change_1m_pct : asset.returns[state.window];
      const geometry = returnGeometry(value, compareScale);
      const mark = row.querySelector("[data-cw-plot-mark]");
      mark.hidden = !geometry.available;
      mark.className = "cw-bar-mark cw-bar-" + geometry.direction;
      mark.style.width = geometry.width + "%";
      displayReturn(row.querySelector("[data-cw-plot-value]"), value);
    });
    all("[data-cw-plot-min]").forEach(el => { el.textContent = compareScale ? "−" + compareScale.toFixed(1) + "%" : ""; });
    all("[data-cw-plot-max]").forEach(el => { el.textContent = compareScale ? "+" + compareScale.toFixed(1) + "%" : ""; });
    all("[data-cw-plot-window]").forEach(el => { el.textContent = windowLabel; });
    all("[data-cw-note-asset]").forEach(el => { el.textContent = selectedAsset ? selectedAsset.label[lang()] : ""; });
    all("[data-cw-compare-empty]").forEach(el => { el.hidden = state.compare.length > 0; });
    all(".cw-plot-axis").forEach(el => { el.hidden = state.compare.length === 0 || !compareValues.some(isNumber); });
    compareStatus.textContent = state.compare.length ? text("One basis. No return ranking.", "同一口径，不进行回报排名。") : text("Select a commodity to compare.", "请选择需要比较的品种。");
    if (form) {
      form.elements.asset.value = state.asset;
      if (renderedAsset !== state.asset) {
        const saved = drafts.get(state.asset);
        form.elements.operator.value = saved ? saved.operator : "gt";
        form.elements.threshold.value = saved ? saved.threshold : "";
        form.elements.expires_on.value = saved ? saved.expires_on : "";
        form.elements.window_sessions.value = saved ? saved.window_sessions : (state.window === "1m" ? "" : state.window);
        renderedAsset = state.asset;
        status.textContent = "";
      }
      const today = new Date().toISOString().slice(0, 10);
      form.elements.expires_on.min = validDate(data.as_of) && data.as_of > today ? data.as_of : today;
      const hypothesisLabel = root.querySelector("#cw-research-hypothesis");
      if (hypothesisLabel) hypothesisLabel.textContent = chosen ? chosen.label[lang()] : text("Cause unresolved", "原因未明");
      renderNoteWindow();
    }
    all("option[data-cw-en]").forEach(el => { el.textContent = el.dataset[lang() === "zh" ? "cwZh" : "cwEn"]; });
    all("a[data-cw-company-href]").forEach(link => {
      link.href = companyReturnHref(link.dataset.cwCompanyHref, state, window.location.href);
    });
  }
  function update(patch, push) {
    captureForm();
    if (patch.asset && patch.asset !== state.asset && !Object.prototype.hasOwnProperty.call(patch,"hypothesis")) {
      patch = Object.assign({},patch,{hypothesis:(drafts.get(patch.asset) || {}).hypothesis || "unresolved"});
    }
    state = normalizeState(Object.assign({}, state, patch), data);
    render();
    if (push !== false) {
      const hash = stateHash(state);
      if (window.location.hash !== hash) window.history.pushState(null, "", hash);
    }
  }
  function openAdvanced(destination, push) {
    const legacy = document.getElementById("commodity-advanced");
    if (!legacy) return;
    const kind = ["detail","physical","catalysts"].includes(destination) ? destination : "detail";
    if (push !== false) {
      returnContext = {state:clone(state),scrollY:window.scrollY};
      window.history.pushState({cwReturn:returnContext},"","#cw-evidence/" + kind + "/" + state.asset);
    }
    legacy.open = true;
    const button = Array.from(document.querySelectorAll("#detail-tabs [data-det]")).find(el => el.dataset.det === state.asset);
    if (button) button.click();
    const panel = Array.from(document.querySelectorAll("[data-detpanel]")).find(el => el.dataset.detpanel === state.asset);
    let target = button ? document.getElementById("detail-tabs") : legacy;
    if (kind === "physical") target = (state.asset === "gold" && panel && panel.querySelector(".cgp")) || document.getElementById("coverage") || target;
    if (kind === "catalysts") target = document.getElementById("commodity-catalysts") || document.getElementById("timeline") || target;
    let parent = target.parentElement;
    while (parent && parent !== legacy) { if (parent.tagName === "DETAILS") parent.open=true; parent=parent.parentElement; }
    target.setAttribute("tabindex","-1");
    window.requestAnimationFrame(() => { target.scrollIntoView({block:"start",behavior:"auto"}); target.focus({preventScroll:true}); });
  }
  function returnToWorkspace() {
    const saved = returnContext || (window.history.state || {}).cwReturn;
    if (saved) { captureForm(); state=normalizeState(saved.state,data); render(); }
    const legacy = document.getElementById("commodity-advanced");
    if (legacy) legacy.open=false;
    window.history.replaceState(null,"",stateHash(state));
    root.querySelector("#cw-tab-" + state.tab).focus({preventScroll:true});
    window.scrollTo({top:saved ? saved.scrollY : root.offsetTop,behavior:"auto"});
  }
  all("[data-cw-tab]").forEach(button => button.addEventListener("click", () => update({tab: button.dataset.cwTab})));
  all("[data-cw-go]").forEach(button => button.addEventListener("click", () => update({tab: button.dataset.cwGo})));
  all("[data-cw-open]").forEach(button => button.addEventListener("click", () => {
    update({asset: button.dataset.cwOpen, tab: "explore"});
    root.querySelector("#cw-tab-explore").focus({preventScroll:true});
    root.querySelector(".cw-tabs").scrollIntoView({block:"start", behavior:"auto"});
  }));
  all("[data-cw-select]").forEach(button => button.addEventListener("click", () => update({asset: button.dataset.cwSelect})));
  all("[data-cw-relationship-asset]").forEach(select => select.addEventListener("change", () => update({asset:select.value})));
  all("[data-cw-advanced]").forEach(link => link.addEventListener("click", event => { event.preventDefault(); openAdvanced("detail"); }));
  function openPhysical() {
    update({tab:"explore", asset:"oil"});
    const panel = document.getElementById("cw-physical-oil");
    if (panel) {
      panel.setAttribute("tabindex","-1");
      window.requestAnimationFrame(() => { panel.scrollIntoView({block:"start",behavior:"auto"}); panel.focus({preventScroll:true}); });
    }
  }
  all("[data-cw-go-physical]").forEach(button => button.addEventListener("click",openPhysical));
  all("[data-cw-evidence]").forEach(button => button.addEventListener("click", () => {
    if (button.dataset.cwEvidence === "physical" && state.asset === "oil") openPhysical();
    else openAdvanced(button.dataset.cwEvidence);
  }));
  const returnButton=document.getElementById("cw-return");
  if (returnButton) returnButton.addEventListener("click",returnToWorkspace);
  all("[data-cw-hypothesis] input").forEach(input => input.addEventListener("change", () => update({hypothesis:input.value})));
  root.querySelector("[data-cw-tablist]").addEventListener("keydown", event => {
    if (!["ArrowLeft","ArrowRight","Home","End"].includes(event.key)) return;
    const current = TABS.indexOf(state.tab);
    const next = event.key === "Home" ? 0 : event.key === "End" ? TABS.length-1 : (current + (event.key === "ArrowRight" ? 1 : -1) + TABS.length) % TABS.length;
    event.preventDefault(); update({tab:TABS[next]}); root.querySelector('[data-cw-tab="' + TABS[next] + '"]').focus();
  });
  all("[data-cw-compare]").forEach(input => input.addEventListener("change", () => {
    if (input.checked && state.compare.length === 4) {
      input.checked = false; compareStatus.textContent = text("Choose up to four. Remove one to add another.", "最多比较四个品种，请先取消一个。"); return;
    }
    update({compare:input.checked ? state.compare.concat(input.value) : state.compare.filter(id => id !== input.value)});
  }));
  all("[data-cw-window]").forEach(select => select.addEventListener("change", () => update({window:select.value})));
  if (form) {
    form.elements.asset.addEventListener("change", () => update({asset:form.elements.asset.value}));
    form.elements.window_sessions.addEventListener("change", renderNoteWindow);
    root.querySelector("#cw-import-trigger").addEventListener("click", () => root.querySelector("#cw-import-file").click());
    form.addEventListener("submit", event => {
      event.preventDefault();
      if (!form.reportValidity()) return;
      const raw = {
        schema:CONDITION, asset:state.asset, metric:"return_pct", unit:"%",
        window_sessions:Number(form.elements.window_sessions.value), operator:form.elements.operator.value,
        threshold:form.elements.threshold.value.trim() === "" ? null : Number(form.elements.threshold.value),
        expires_on:form.elements.expires_on.value, hypothesis:state.hypothesis, snapshot_fingerprint:data.fingerprint
      };
      const checked = checkDraft(raw, data);
      if (checked.errors.length) { status.textContent = text("Check the metric, threshold, expiry and snapshot before exporting.", "导出前请核对指标、阈值、有效期及快照。"); return; }
      const blob = new Blob([JSON.stringify(checked.value,null,2) + "\n"], {type:"application/json"});
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href=url; link.download="commodity-research-" + state.asset + "-" + data.as_of + ".json";
      document.body.appendChild(link); link.click(); link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url),1000);
      captureForm();
      status.textContent=text("Research condition exported. No monitoring or alert has been activated.", "研究条件已导出，未启用监测或提醒。");
    });
    let importGeneration = 0;
    root.querySelector("#cw-import-file").addEventListener("change", async event => {
      const generation = ++importGeneration;
      const file = event.target.files[0];
      if (!file) return;
      if (file.size > 131072) { status.textContent=text("The draft is too large. Use an exported research-condition file.", "草稿文件过大，请选择导出的研究条件文件。"); event.target.value=""; return; }
      let checked;
      try {
        const contents = await file.text();
        if (generation !== importGeneration) return;
        checked = checkDraft(JSON.parse(contents),data,true);
      } catch (_) {
        if (generation !== importGeneration) return;
        status.textContent=text("This research draft could not be read or checked. The current context is unchanged.", "无法读取或校验此研究草稿，当前背景未改变。");
        event.target.value=""; return;
      }
      if (checked.errors.length) {
        status.textContent=checked.errors.includes("snapshot_fingerprint") ? text("This draft belongs to a different research snapshot. It has not been rebound to current evidence.", "此草稿属于不同的研究快照，未将其重新绑定至当前证据。") : text("The draft failed validation; the current research context is unchanged.", "草稿未通过校验，当前研究背景未改变。");
        event.target.value=""; return;
      }
      const v=checked.value;
      update({asset:v.asset, tab:"research", hypothesis:v.hypothesis, window:String(v.window_sessions)});
      form.elements.operator.value=v.operator; form.elements.threshold.value=String(v.threshold);
      form.elements.expires_on.value=v.expires_on; form.elements.window_sessions.value=String(v.window_sessions);
      renderNoteWindow();
      captureForm();
      status.textContent=v.expires_on < new Date().toISOString().slice(0,10) ? text("Draft reopened with its original evidence. Its expiry date has passed; no monitoring is active.", "已按原证据重新打开草稿，其有效期已过，未启用监测。") : text("Draft reopened with the exact metric, window, threshold and evidence. No monitoring is active.", "已恢复精确指标、窗口、阈值与证据，未启用监测。");
      event.target.value="";
    });
  }
  function restore() {
    if (window.location.hash.startsWith("#cw/")) {
      captureForm(); state=readState(window.location.hash,data); render();
      const legacy=document.getElementById("commodity-advanced"); if (legacy) legacy.open=false;
    }
    else if (window.location.hash.startsWith("#cw-evidence/")) {
      const parts=window.location.hash.slice(13).split("/");
      captureForm(); state=normalizeState(Object.assign({},state,{asset:parts[1]}),data); render();
      returnContext=(window.history.state || {}).cwReturn || returnContext;
      openAdvanced(parts[0],false);
    }
    else if (window.location.hash === "#commodity-advanced") openAdvanced("detail",false);
    else if (!window.location.hash) {
      captureForm(); state=normalizeState({},data); render();
      const legacy=document.getElementById("commodity-advanced"); if (legacy) legacy.open=false;
    }
  }
  window.addEventListener("popstate",restore);
  window.addEventListener("hashchange",restore);
  document.addEventListener("langchange",render);
  new MutationObserver(records => { if (records.some(r => r.attributeName === "data-lang")) render(); }).observe(document.documentElement,{attributes:true,attributeFilter:["data-lang"]});
  render(); restore();
})();

