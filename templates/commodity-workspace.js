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
      hypothesis: hypotheses.has(candidate.hypothesis) ? candidate.hypothesis : "unresolved",
      view: candidate.view === "universe" ? "universe" : "detail",
      query: typeof candidate.query === "string" ? candidate.query.replace(/[\u0000-\u001f\u007f]/g, "").slice(0, 80) : "",
      family: (Array.isArray(data.families) ? data.families.some(f => f.id === candidate.family) : data.assets.some(a => a.family === candidate.family)) ? candidate.family : "all",
      sort: ["source","name","return_asc","return_desc"].includes(candidate.sort) ? candidate.sort : "source",
      trend: ["up","down","flat","unknown"].includes(candidate.trend) ? candidate.trend : "all",
      momentum: ["bull","bear","neutral","unknown"].includes(candidate.momentum) ? candidate.momentum : "all",
      layout: candidate.layout === "map" ? "map" : "table"
    };
  }
  function readState(hash, data) {
    if (typeof hash !== "string" || hash.length > 2000 || !hash.startsWith("#cw/")) return normalizeState({}, data);
    const parts = hash.slice(4).split("?");
    const route = parts[0].split("/");
    const params = new URLSearchParams(parts[1] || "");
    return normalizeState({tab: route[0], asset: route[1], window: params.get("window"),
      compare: params.has("compare") ? params.get("compare").split(",").filter(Boolean) : undefined,
      hypothesis: params.get("hypothesis"), view: params.get("view"), query: params.get("q"),
      family: params.get("family"), sort: params.get("sort"), trend: params.get("trend"),
      momentum: params.get("momentum"), layout: params.get("layout")}, data);
  }
  function stateHash(state) {
    const p = new URLSearchParams();
    p.set("window", state.window); p.set("compare", state.compare.join(",")); p.set("hypothesis", state.hypothesis);
    if (state.view === "universe") p.set("view", "universe");
    if (state.query) p.set("q", state.query);
    for (const key of ["family","trend","momentum"]) if (state[key] && state[key] !== "all") p.set(key, state[key]);
    if (state.sort && state.sort !== "source") p.set("sort", state.sort);
    if (state.layout === "map") p.set("layout", "map");
    return "#cw/" + state.tab + "/" + state.asset + "?" + p.toString();
  }
  function filterAssets(assets, state) {
    const query = (state.query || "").trim().toLocaleLowerCase();
    const rows = assets.filter(asset =>
      (!query || [asset.id,asset.label.en,asset.label.zh].some(value => value.toLocaleLowerCase().includes(query))) &&
      (state.family === "all" || asset.family === state.family) &&
      (state.trend === "all" || (asset.trend || "unknown") === state.trend) &&
      (state.momentum === "all" || (asset.momentum || "unknown") === state.momentum));
    if (state.sort === "name") rows.sort((a,b) => a.label.en.localeCompare(b.label.en, "en"));
    if (["return_asc","return_desc"].includes(state.sort)) rows.sort((a,b) => {
      const av=a.change_1m_pct, bv=b.change_1m_pct;
      if (!isNumber(av)) return isNumber(bv) ? 1 : 0;
      if (!isNumber(bv)) return -1;
      return (state.sort === "return_asc" ? 1 : -1) * (av-bv);
    });
    return rows;
  }
  function coverageReading(data, family, language) {
    const zh=language==="zh", pick=(en,cn)=>zh?cn:en;
    const record=family==="all"?null:(data.families || []).find(row=>row.id===family);
    const raw=family==="all"?(data.universe || {}).coverage:record && record.coverage;
    const c=raw && typeof raw==="object" && !Array.isArray(raw)?raw:{};
    const observations=data.assets.filter(a=>family==="all" || a.family===family);
    const states=["complete","partial","missing","inconsistent","unknown","invalid"];
    let state=states.includes(c.state)?c.state:"unknown";
    const expected=Number.isInteger(c.expected_n)&&c.expected_n>0?c.expected_n:null;
    const counts=expected!==null && [c.present_n,c.matched_n,c.price_1m_known_n].every(n=>Number.isInteger(n)&&n>=0&&n<=expected)
      && c.matched_n<=c.present_n && c.price_1m_known_n<=c.matched_n;
    const configured=["complete","partial","missing","inconsistent"].includes(state);
    if(configured && !counts && !(state==="inconsistent" && c.expected_n===0))state="invalid";
    const known=configured && counts && state!=="invalid";
    const complete=known && state==="complete" && c.price_1m_state==="complete" && c.present_n===expected && c.matched_n===expected && c.price_1m_known_n===expected;
    const missing=known && state==="missing" && c.present_n===0;
    const scope=record && record.label?record.label[zh?"zh":"en"]:pick("Snapshot","快照");
    let detail="";
    if(state==="unknown")detail=pick("This publication does not provide a usable configured roster. Observed members do not establish complete coverage.","本发布未提供可用的品种配置范围，已有品种不能证明覆盖完整。");
    else if(state==="invalid")detail=pick("The configured roster is invalid. Read available observations individually; completeness cannot be confirmed.","品种配置范围无效，请逐项阅读已有观察；无法确认覆盖完整。");
    else if(state==="inconsistent")detail=pick("Member identities disagree with the configured roster. Coverage and family breadth remain unconfirmed.","品种标识与配置范围不一致，覆盖及类别涨跌分布仍未确认。");
    else if(missing)detail=pick("Missing observations are neither zero performance nor a neutral state.","缺失观察不代表零涨跌，也不代表中性状态。");
    else if(state==="partial")detail=pick("Some configured members are missing. Available readings cannot establish a complete family conclusion.","部分已配置品种缺失，已有读数不能支持完整的类别判断。");
    else if(!complete)detail=pick("Some one-month values are unavailable. Missing prices are not counted as flat.","部分一个月读数不可用，缺失价格不计为持平。");
    return {state,complete,missing,expected:known?expected:null,observed:observations.length,
      title:scope+pick(" coverage","覆盖"),detail,
      members:known?pick(c.present_n+" of "+expected+" configured members present",expected+"个已配置品种中已有"+c.present_n+"个"):
        pick(observations.length+" observed members · expected membership unconfirmed","已记录"+observations.length+"个品种 · 预期品种范围尚未确认"),
      prices:known?pick(c.price_1m_known_n+" of "+expected+" identity-matched one-month values",expected+"个预期一个月读数中有"+c.price_1m_known_n+"个通过身份核验"):
        pick("One-month price coverage cannot be verified against configuration","无法按配置核实一个月价格覆盖")};
  }
  function comparisonReading(assets, selected, window, language) {
    const zh=language === "zh", chosen=assets.filter(a=>selected.includes(a.id));
    const rows=chosen.map(a=>({asset:a,value:window==="1m"?a.change_1m_pct:a.returns[window]})).filter(r=>isNumber(r.value));
    if (rows.length<2) return zh ? "至少需要两个同一窗口的有效观察，才能比较差异。" : "Two available observations in the same window are needed to compare the difference.";
    const sorted=rows.slice().sort((a,b)=>b.value-a.value), high=sorted[0], low=sorted[sorted.length-1];
    const gap=high.value-low.value;
    const reading=gap===0 ? (zh ? "所选品种在此窗口的记录变化相同。" : "The selected commodities have the same recorded change over this window.") :
      zh ? high.asset.label.zh+"与"+low.asset.label.zh+"相差"+gap.toFixed(1)+"个百分点。" :
        high.asset.label.en+" and "+low.asset.label.en+" are "+gap.toFixed(1)+" percentage points apart.";
    return reading+(rows.length<chosen.length ? (zh ? " 缺失观察未参与比较。" : " Missing observations are excluded.") : "");
  }
  function metricReceipt(data, assetId, metric) {
    const asset=data.assets.find(a=>a.id===assetId);
    if (!asset || !["1m","5","20","60","252","trend","momentum"].includes(metric)) return null;
    const field=metric==="1m"?"chg_1m_pct":metric==="trend"?"ts_trend":metric==="momentum"?"momentum_state":"velocity.r"+metric;
    const value=metric==="1m"?asset.change_1m_pct:metric==="trend"?asset.trend:metric==="momentum"?asset.momentum:asset.returns[metric];
    return {asset,metric,field,value,source:data.sources.commodities || {},analysis_as_of:asset.as_of,observation_at:null,
      method_path:"engine/commodity_index.py",point_in_time_verified:false};
  }
  function physicalReceipt(data, key) {
    const physical=data.physical;
    if(!physical || !physical.evidence || !Object.prototype.hasOwnProperty.call(physical.evidence,key))return null;
    const observation=physical.evidence[key];
    const slots={level:["_stocks_mb","Stock level","库存水平"],anomaly:["_z","Seasonal deviation","季节偏离"],change_4w:["_chg_4w_mb","Four-week stock change","四周库存变化"],days_cover:[null,"Stock / daily flow","库存 / 日均流量"]};
    for(const stock of physical.stocks || [])for(const [slot,spec] of Object.entries(slots)){
      const field=slot==="days_cover"?({crude:"days_supply",gasoline:"gasoline_days",distillate:"distillate_days"})[stock.id]:stock.id+spec[0];
      if(field===key)return {key,kind:slot,observation,label:stock.label,metric_label:{en:spec[1],zh:spec[2]},physical};
    }
    const flow=(physical.flows || []).find(row=>row.id===key);
    const kinds={refinery_inputs_avg:"flow",gasoline_supplied_avg:"flow",distillate_supplied_avg:"flow",production_mbd:"flow",production_chg_4w:"production_change",refinery_util:"utilisation",spr_chg_4w_mb:"change_4w",cushing_stocks_mb:"level"};
    return flow && Object.prototype.hasOwnProperty.call(kinds,key) ? {key,kind:kinds[key],observation,label:flow.label,metric_label:{en:"US petroleum balance",zh:"美国石油供需"},physical}:null;
  }
  function metricInterpretation(receipt, language) {
    const zh=language==="zh", pick=(en,cn)=>zh?cn:en;
    const trend={up:pick("up","向上"),down:pick("down","向下"),flat:pick("flat","持平")};
    const momentum={bull:pick("positive","偏强"),bear:pick("negative","偏弱"),neutral:pick("neutral","中性")};
    const unknown=pick("unavailable","暂不可用");
    const recordedTrend=trend[receipt.asset.trend]||unknown, recordedMomentum=momentum[receipt.asset.momentum]||unknown;
    const numeric=isNumber(receipt.value), state=receipt.metric==="trend"?trend[receipt.value]:momentum[receipt.value];
    const available=["trend","momentum"].includes(receipt.metric)?Boolean(state):numeric;
    let supports=pick("This field is unavailable in the published snapshot. It supports no directional conclusion.","本发布快照中此字段不可用，不能据此作出方向判断。");
    let doesNot=pick("An executable return, a spot quote, a physical shortage, future performance or an entry signal.","可执行回报、现货报价、实物短缺、未来表现或入场信号。");
    if(receipt.metric==="trend") {
      if(available)supports=pick("The source records a long-term trend that is "+state+". Momentum is "+recordedMomentum+" and remains a separate reading.","来源记录的长期趋势"+state+"；动能"+recordedMomentum+"，两者仍是独立判断。");
      doesNot=pick("Near-term momentum, the cause of a price move, future performance or entry readiness. A trend state does not replace the dated price change.","短期动能、价格变化原因、未来表现或入场准备度。趋势状态不能替代有日期的价格变化。");
    } else if(receipt.metric==="momentum") {
      if(available)supports=pick("The source records "+state+" momentum. Long-term trend is "+recordedTrend+" and remains a separate reading.","来源记录的动能"+state+"；长期趋势"+recordedTrend+"，两者仍是独立判断。");
      doesNot=pick("A long-term trend, a physical supply or demand cause, future performance or an entry signal.","长期趋势、实物供需原因、未来表现或入场信号。");
    } else if(numeric) {
      const direction=receipt.value>0?pick("positive","为正"):receipt.value<0?pick("negative","为负"):pick("zero","为零");
      supports=receipt.metric==="1m"?
        pick("The published one-month price change is "+direction+". Long-term trend is "+recordedTrend+"; momentum is "+recordedMomentum+". These readings retain their own scope.","发布的一个月价格变化"+direction+"；长期趋势"+recordedTrend+"，动能"+recordedMomentum+"。各项判断保留各自范围。"):
        pick("The published endpoint price change over "+receipt.metric+" trading sessions is "+direction+". It describes that selected window only.","发布的"+receipt.metric+"个交易日端点价格变化"+direction+"，仅描述所选窗口。");
    }
    return {supports,doesNot};
  }
  function physicalInterpretation(receipt, language) {
    const zh=language==="zh", pick=(en,cn)=>zh?cn:en;
    const readings={
      level:["The recorded inventory level for the dated observation. Read the level alongside stock changes and physical flows.","有日期观察中的库存水平，应结合库存变化与实物流量阅读。","A physical shortage, the reason prices moved, or how much inventory is available for immediate delivery.","实物短缺、价格变化原因，或可立即交割的库存数量。"],
      anomaly:["Where this stock observation sits relative to the recorded seasonal reference. Its sign distinguishes above from below that reference.","本次库存观察相对记录的季节参照的位置；正负号区分高于或低于参照。","EIA’s published five-year range, a probability, a shortage or a trading signal.","EIA发布的五年区间、概率、短缺或交易信号。"],
      change_4w:["The net inventory change over the recorded four-week window. A draw or build is separate from the inventory level.","记录的四周窗口内库存净变化；去库或累库与库存水平是不同读数。","Whether supply or demand caused the change, a price forecast or confirmation of a transmission chain.","变化由供给还是需求造成、价格预测，或传导链已获确认。"],
      days_cover:["The ratio of the recorded stock level to the daily flow over its stated window. Its meaning depends on that denominator.","记录的库存水平与指定窗口日均流量之比，其含义取决于该分母。","An inventory exhaustion date, guaranteed deliverable supply, or proof of a shortage.","库存耗尽日期、保证可交付的供给，或短缺证明。"],
      utilisation:["The recorded refinery utilisation percentage for its dated observation. This is a capacity-use ratio, not a volume of oil.","有日期观察中的炼厂利用率，这是产能使用比例，而非石油数量。","Refining margins, product demand, a physical shortage or the cause of a price move.","炼油利润率、成品油需求、实物短缺或价格变化原因。"],
      production_change:["The change in the recorded daily production rate over four weeks. This is a rate change, not cumulative output over the window.","记录的日均产量在四周内的变化，这是产出速率变化，而非窗口内累计产量。","A cumulative inventory change, the cause of a supply change or future production.","累计库存变化、供给变化原因或未来产量。"],
      flow:["The recorded physical flow for its dated window. Read it alongside inventories and the other petroleum balance measures.","有日期窗口内记录的实物流量，应结合库存及其他石油供需指标阅读。","The cause of a commodity price move, a complete supply-demand balance or an activated entry signal.","商品价格变化原因、完整供需平衡，或已激活的入场信号。"]
    };
    const copy=readings[receipt.kind];
    const supports=isNumber(receipt.observation.value)&&copy?pick(copy[0],copy[1]):pick("This physical observation is unavailable. No level, direction or balance conclusion is supported.","此实物观察不可用，不能据此判断水平、方向或供需平衡。");
    return {supports,doesNot:copy?pick(copy[2],copy[3]):pick("A physical shortage, future price performance or an entry signal.","实物短缺、未来价格表现或入场信号。")};
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
  const api = {normalizeState, readState, stateHash, companyReturnHref, checkDraft, validDate, conditionSemantics, returnScale, returnGeometry, filterAssets, coverageReading, comparisonReading, metricReceipt, physicalReceipt, metricInterpretation, physicalInterpretation};
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
  let browseReturn = null;
  let inspection = null;
  let inspectorTrigger = null;
  const inspector = root.querySelector("[data-cw-inspector]");
  function renderBrowse() {
    const universe=root.querySelector("[data-cw-universe]"), detail=root.querySelector("[data-cw-explore-detail]");
    if (!universe || !detail) return;
    universe.hidden=state.view !== "universe"; detail.hidden=state.view === "universe";
    const rows=filterAssets(data.assets,state), shown=new Set(rows.map(a=>a.id));
    const body=root.querySelector("[data-cw-universe-body]");
    const rowNodes=new Map(all("[data-cw-universe-row]").map(el=>[el.dataset.cwUniverseRow,el]));
    const focused=document.activeElement;
    rows.forEach((a,index)=>{const row=rowNodes.get(a.id);if(body.children[index]!==row)body.insertBefore(row,body.children[index]||null);});
    rowNodes.forEach((el,id)=>{el.hidden=!shown.has(id);});
    if(focused && body.contains(focused) && !focused.closest("[hidden]") && document.activeElement!==focused)focused.focus({preventScroll:true});
    all("[data-cw-pick]").forEach(el=>{el.checked=state.compare.includes(el.value);});
    all("[data-cw-family]").forEach(el=>el.setAttribute("aria-pressed",String(el.dataset.cwFamily===state.family)));
    all("[data-cw-layout]").forEach(el=>el.setAttribute("aria-pressed",String(el.dataset.cwLayout===state.layout)));
    for(const [selector,key] of [["[data-cw-search]","query"],["[data-cw-sort]","sort"],["[data-cw-trend]","trend"],["[data-cw-momentum]","momentum"]]){
      const el=root.querySelector(selector); if(el.value!==state[key])el.value=state[key];
    }
    root.querySelector("[data-cw-results-count]").textContent=text("Showing ","显示 ")+rows.length+text(" of "," / ")+data.assets.length+text(" available observations · analysis dated ","个已有观察 · 研究日期 ")+(data.as_of||text("unavailable","不可用"));
    const coverage=coverageReading(data,state.family,lang()), coveragePanel=root.querySelector("[data-cw-browse-coverage]");
    if(coveragePanel){
      coveragePanel.dataset.coverageState=coverage.state;
      coveragePanel.querySelector("[data-cw-coverage-title]").textContent=coverage.title;
      coveragePanel.querySelector("[data-cw-coverage-members]").textContent=coverage.members;
      coveragePanel.querySelector("[data-cw-coverage-prices]").textContent=coverage.prices;
      const context=coveragePanel.querySelector("[data-cw-coverage-context]");context.textContent=coverage.detail;context.hidden=!coverage.detail;
    }
    const empty=root.querySelector("[data-cw-universe-empty]");empty.hidden=rows.length>0;
    empty.querySelector("h3").textContent=coverage.missing?text("Configured members are missing from this snapshot","本快照缺少已配置品种"):
      coverage.observed===0?text("Observations are unavailable for this selection","此选择的观察不可用"):text("No commodities match","没有符合条件的品种");
    empty.querySelector("p").textContent=coverage.missing?
      text(coverage.expected+" configured members have no published observations. Missing data does not imply zero performance or a neutral state.",coverage.expected+"个已配置品种没有发布观察。缺失数据不代表零涨跌或中性状态。"):
      coverage.observed===0?coverage.detail:text("Your search and filters are combined. Clear them to see available observations.","搜索与筛选共同生效，清除条件即可查看已有观察。");
    empty.querySelector("button").textContent=text("Show available commodities","显示已有商品");
    root.querySelector("[data-cw-table-view]").hidden=state.layout!=="table" || !rows.length;
    root.querySelector("[data-cw-map-view]").hidden=state.layout!=="map" || !rows.length;
    all("[data-cw-map-trend]").forEach(cell=>{
      const members=rows.filter(a=>a.trend===cell.dataset.cwMapTrend && a.momentum===cell.dataset.cwMapMomentum);
      cell.querySelector("[data-cw-map-count]").textContent=String(members.length);
      cell.querySelector(".cw-map-members").textContent=members.map(a=>a.label[lang()]).join(" · ");
      cell.disabled=members.length===0;
    });
    const unknown=rows.filter(a=>!a.trend || !a.momentum);
    root.querySelector("[data-cw-map-unknown]").textContent=!rows.length?text("No observations are displayed.","当前未显示观察。"):unknown.length ?
      unknown.map(a=>a.label[lang()]).join(" · ") : text("Every displayed commodity has both recorded states.","显示的品种均有这两项记录。");
    all("[data-cw-selection-count]").forEach(el=>{el.textContent=state.compare.length+" / 4";});
    const labels=state.compare.map(id=>data.assets.find(a=>a.id===id).label[lang()]);
    all("[data-cw-selection-names]").forEach(el=>{el.textContent=labels.length?labels.join(" · "):text("Nothing selected yet","尚未选择品种");});
  }
  function receiptList(selector, facts) {
    const list=root.querySelector(selector); list.replaceChildren();
    for (const [label,value] of facts) {
      const row=document.createElement("div"), term=document.createElement("dt"), description=document.createElement("dd");
      term.textContent=label; description.textContent=value===null || value===undefined || value==="" ? text("Not recorded","未记录") : String(value);
      row.append(term,description);list.appendChild(row);
    }
  }
  function renderInterpretation(copy) {
    root.querySelector("[data-cw-inspector-supports]").textContent=copy.supports;
    root.querySelector("[data-cw-inspector-does-not]").textContent=copy.doesNot;
  }
  function renderInspection() {
    if (!inspection || !inspector) return;
    if(inspection.kind==="physical"){renderPhysicalInspection();return;}
    const receipt=metricReceipt(data,inspection.asset,inspection.metric); if(!receipt)return;
    renderInterpretation(metricInterpretation(receipt,lang()));
    const metricLabel=receipt.metric==="1m"?text("One-month price change","一个月价格变化"):
      receipt.metric==="trend"?text("Long-term trend","长期趋势"):receipt.metric==="momentum"?text("Momentum","动能"):
      receipt.metric+text("-session price change","个交易日价格变化");
    root.querySelector("#cw-inspector-title").textContent=receipt.asset.label[lang()];
    root.querySelector("[data-cw-inspector-label]").textContent=metricLabel;
    const valueNode=root.querySelector("[data-cw-inspector-value]");
    valueNode.classList.remove("cw-up","cw-down");
    if (["trend","momentum"].includes(receipt.metric)) {
      const names={up:["Up","向上"],down:["Down","向下"],flat:["Flat","持平"],bull:["Positive","偏强"],bear:["Negative","偏弱"],neutral:["Neutral","中性"]};
      valueNode.textContent=receipt.value && names[receipt.value] ? names[receipt.value][lang()==="zh"?1:0]:text("Unavailable","暂不可用");
    } else displayReturn(valueNode,receipt.value);
    root.querySelector("[data-cw-inspector-limit]").textContent=receipt.metric==="1m" ?
      text("The publisher’s one-month change is distinct from 20 trading sessions.","发布方的一个月变化不同于20个交易日。") :
      ["trend","momentum"].includes(receipt.metric) ? text("This is the publisher’s recorded state. It is not inferred from the one-month price change.","这是发布方记录的状态，未由一个月价格变化推断。") :
      text("An endpoint change over this many trading sessions; not a total return or a price history.","这是指定交易日窗口的端点变化，并非总回报或价格历史。");
    receiptList("[data-cw-inspector-facts]",[
      [text("Analysis snapshot","研究快照"),receipt.analysis_as_of],
      [text("Price observation time","价格观察时间"),receipt.observation_at],
      [text("Publication time","发布时间"),receipt.source.available_at],
      [text("Series basis","序列口径"),text("Published price series; contract identity is not recorded","发布价格序列；未记录合约标识")],
      [text("Historical availability","历史可得性"),text("Not verified","未经核实")]
    ]);
    const identity=receipt.source.immutable_source;
    receiptList("[data-cw-inspector-identity]",[
      [text("Source artifact","来源文件"),receipt.source.path],
      [text("Member / field","品种 / 字段"),receipt.asset.id+" / "+receipt.field],
      [text("Calculation owner","计算来源"),receipt.method_path],
      [text("Source payload fingerprint","来源数据指纹"),receipt.source.fingerprint],
      [text("Immutable file identity","不可变文件标识"),identity ? JSON.stringify(identity) : null]
    ]);
  }
  function renderPhysicalInspection() {
    const receipt=physicalReceipt(data,inspection.key);if(!receipt)return;
    renderInterpretation(physicalInterpretation(receipt,lang()));
    const observation=receipt.observation, physical=receipt.physical;
    const units={million_barrels:["million bbl","百万桶"],million_barrels_per_day:["million bbl/day","百万桶/日"],seasonal_z:["z","z"],days:["days","天"],percent:["%","%"]};
    const unit=units[observation.unit];
    root.querySelector("#cw-inspector-title").textContent=receipt.label[lang()];
    root.querySelector("[data-cw-inspector-label]").textContent=receipt.metric_label[lang()];
    const valueNode=root.querySelector("[data-cw-inspector-value]");valueNode.classList.remove("cw-up","cw-down");
    valueNode.textContent=isNumber(observation.value)?String(observation.value)+" "+(unit?unit[lang()==="zh"?1:0]:observation.unit||text("Unit not recorded","未记录单位")):text("Unavailable","暂不可用");
    root.querySelector("[data-cw-inspector-limit]").textContent=text("A dated physical observation does not establish its historical publication vintage or the cause of a price move.","实物观察日期不能证明其历史发布版本，也不能单独确定价格变化的原因。");
    const facts=[
      [text("Observation week ending","观察周截至"),observation.observation_at],
      [text("Analysis snapshot","研究快照"),data.as_of],
      [text("Window starts","窗口开始"),observation.window_start],
      [text("Window ends","窗口结束"),observation.window_end],
      [text("Publication time","发布时间"),observation.release_at],
      [text("Historical availability","历史可得性"),observation.point_in_time_verified===true?text("Verified by source receipt","来源记录已核实"):text("Not verified","未经核实")]
    ];
    if(observation.reference){
      const reference=observation.reference;
      facts.push([text("Seasonal reference","季节参照"),(reference.start||"—")+" → "+(reference.end||"—")],
        [text("Reference observations","参照观察数"),reference.observations],
        [text("Latest observation included","包含最新观察"),reference.latest_included===true?text("Yes · this is not EIA’s published five-year range","是 · 此值并非EIA发布的五年区间"):reference.latest_included===false?text("No","否"):null]);
    }
    receiptList("[data-cw-inspector-facts]",facts);
    const identity=[
      [text("Evidence field","证据字段"),"physical.evidence."+receipt.key],
      [text("Calculation owner","计算来源"),"engine/commodity_supply_context.py"],
      [text("Method revision","方法版本"),physical.owner_method_revision]
    ];
    for(const id of observation.source_ids || []){
      const source=physical.source_dependencies && physical.source_dependencies[id];
      identity.push([text("Source artifact","来源文件")+" · "+id,source && source.path],
        [text("Source payload fingerprint","来源数据指纹")+" · "+id,source && source.fingerprint],
        [text("Immutable file identity","不可变文件标识")+" · "+id,source && source.immutable_source?JSON.stringify(source.immutable_source):null]);
    }
    receiptList("[data-cw-inspector-identity]",identity);
  }
  function closeInspector() { if(!inspector)return; if(typeof inspector.close==="function")inspector.close();else{inspector.removeAttribute("open");finishInspector();} }
  function finishInspector() {
    inspection=null;document.body.classList.remove("cw-dialog-open");
    const visible=inspectorTrigger && inspectorTrigger.isConnected && !inspectorTrigger.closest("[hidden]") && !inspectorTrigger.closest("details:not([open])");
    const target=visible?inspectorTrigger:root.querySelector("#cw-tab-"+state.tab);
    inspectorTrigger=null;if(target)target.focus({preventScroll:true});
  }
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
    renderBrowse();
    renderInspection();
    all("[data-cw-brief-compare-status]").forEach(el => { el.textContent=""; });
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
    all("[data-cw-current-inspect]").forEach(el=>{
      const asset=data.assets.find(a=>a.id===el.dataset.cwCurrentInspect);
      el.dataset.cwInspect=asset.id+":"+state.window;
      el.querySelector("[data-cw-current-label]").textContent=text("Inspect ","核查 ")+asset.label[lang()]+" · "+windowLabel+": ";
    });
    all("[data-cw-note-asset]").forEach(el => { el.textContent = selectedAsset ? selectedAsset.label[lang()] : ""; });
    all("[data-cw-compare-empty]").forEach(el => { el.hidden = state.compare.length > 0; });
    all(".cw-plot-axis").forEach(el => { el.hidden = state.compare.length === 0 || !compareValues.some(isNumber); });
    compareStatus.textContent = state.compare.length ? text("Same selected window · series bases not verified.", "同一所选窗口 · 序列口径未核实。") : text("Select a commodity to compare.", "请选择需要比较的品种。");
    all("[data-cw-comparison-reading]").forEach(el=>{el.textContent=comparisonReading(data.assets,state.compare,state.window,lang());});
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
      if (window.location.hash !== hash) window.history[push==="replace"?"replaceState":"pushState"](null, "", hash);
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
  all("[data-cw-tab]").forEach(button => button.addEventListener("click", () => update({tab: button.dataset.cwTab, ...(button.dataset.cwTab==="explore"?{view:"universe"}:{})})));
  all("[data-cw-go]").forEach(button => button.addEventListener("click", () => update({tab: button.dataset.cwGo, ...(button.dataset.cwGo==="explore"?{view:"detail"}:{})})));
  all("[data-cw-open]").forEach(button => button.addEventListener("click", () => {
    if(state.tab==="explore" && state.view==="universe")browseReturn={asset:button.dataset.cwOpen,scrollY:window.scrollY};
    update({asset: button.dataset.cwOpen, tab: "explore",view:"detail"});
    root.querySelector("#cw-tab-explore").focus({preventScroll:true});
    root.querySelector(".cw-tabs").scrollIntoView({block:"start", behavior:"auto"});
  }));
  all("[data-cw-select]").forEach(button => button.addEventListener("click", () => update({asset: button.dataset.cwSelect,view:"detail"})));
  all("[data-cw-universe-open]").forEach(button=>button.addEventListener("click",()=>update({tab:"explore",view:"universe"})));
  all("[data-cw-family-open]").forEach(button=>button.addEventListener("click",()=>{
    update({tab:"explore",view:"universe",family:button.dataset.cwFamilyOpen,query:"",trend:"all",momentum:"all",layout:"table"});
    const selected=all("[data-cw-family]").find(el=>el.dataset.cwFamily===state.family);if(selected)selected.focus();
  }));
  all("[data-cw-family]").forEach(button=>button.addEventListener("click",()=>update({family:button.dataset.cwFamily})));
  all("[data-cw-layout]").forEach(button=>button.addEventListener("click",()=>update({layout:button.dataset.cwLayout})));
  all("[data-cw-reset-filters]").forEach(button=>button.addEventListener("click",()=>{
    update({query:"",family:"all",trend:"all",momentum:"all"});root.querySelector("[data-cw-search]").focus({preventScroll:true});
  }));
  all("[data-cw-map-trend]").forEach(button=>button.addEventListener("click",()=>{
    update({trend:button.dataset.cwMapTrend,momentum:button.dataset.cwMapMomentum,layout:"table"});
    const result=root.querySelector('[data-cw-universe-row]:not([hidden]) [data-cw-open]');
    if(result){result.focus({preventScroll:true});result.scrollIntoView({block:"nearest",behavior:"auto"});}
  }));
  all("[data-cw-search]").forEach(input=>input.addEventListener("input",()=>update({query:input.value},"replace")));
  for(const key of ["sort","trend","momentum"])all("[data-cw-"+key+"]").forEach(select=>select.addEventListener("change",()=>update({[key]:select.value})));
  all("[data-cw-results-back]").forEach(button=>button.addEventListener("click",()=>{
    update({tab:"explore",view:"universe"});
    const target=browseReturn && root.querySelector('[data-cw-universe-row="'+browseReturn.asset+'"]:not([hidden]) [data-cw-open]');
    window.requestAnimationFrame(()=>{(target||root.querySelector("[data-cw-search]")).focus({preventScroll:true});window.scrollTo({top:browseReturn?browseReturn.scrollY:root.offsetTop,behavior:"auto"});});
  }));
  all("[data-cw-compare-preset]").forEach(button=>button.addEventListener("click",()=>update({tab:"compare",compare:button.dataset.cwComparePreset.split(",")})));
  all("[data-cw-finish-selection]").forEach(button=>button.addEventListener("click",()=>{
    const editor=root.querySelector("[data-cw-compare-editor]");editor.open=false;editor.querySelector("summary").focus();
  }));
  all("[data-cw-inspect]").forEach(button=>button.addEventListener("click",()=>{
    const [asset,metric]=button.dataset.cwInspect.split(":");if(!metricReceipt(data,asset,metric)||!inspector)return;
    inspection={asset,metric};inspectorTrigger=button;renderInspection();
    document.body.classList.add("cw-dialog-open");
    if(typeof inspector.showModal==="function")inspector.showModal();else inspector.setAttribute("open","");
    root.querySelector("[data-cw-inspector-close]").focus();
  }));
  all("[data-cw-physical-inspect]").forEach(button=>button.addEventListener("click",()=>{
    const key=button.dataset.cwPhysicalInspect;if(!physicalReceipt(data,key)||!inspector)return;
    inspection={kind:"physical",key};inspectorTrigger=button;renderInspection();
    document.body.classList.add("cw-dialog-open");
    if(typeof inspector.showModal==="function")inspector.showModal();else inspector.setAttribute("open","");
    root.querySelector("[data-cw-inspector-close]").focus();
  }));
  all("[data-cw-inspector-close]").forEach(button=>button.addEventListener("click",closeInspector));
  if(inspector) {
    inspector.addEventListener("close",finishInspector);
    inspector.addEventListener("cancel",()=>{document.body.classList.remove("cw-dialog-open");});
    inspector.addEventListener("keydown",event=>{
      if(event.key!=="Tab" || !inspector.open)return;
      const controls=Array.from(inspector.querySelectorAll('button:not([disabled]),a[href],input:not([disabled]),select:not([disabled]),textarea:not([disabled]),summary,[tabindex]:not([tabindex="-1"])'))
        .filter(el=>el.getClientRects().length>0 && !el.closest("[hidden]"));
      if(!controls.length)return;
      const first=controls[0],last=controls[controls.length-1];
      if(event.shiftKey && (document.activeElement===first || !inspector.contains(document.activeElement))){event.preventDefault();last.focus();}
      else if(!event.shiftKey && (document.activeElement===last || !inspector.contains(document.activeElement))){event.preventDefault();first.focus();}
    });
  }
  all("[data-cw-relationship-asset]").forEach(select => select.addEventListener("change", () => update({asset:select.value})));
  all("[data-cw-advanced]").forEach(link => link.addEventListener("click", event => { event.preventDefault(); openAdvanced("detail"); }));
  function openPhysical() {
    if(!data.assets.some(asset=>asset.id==="oil")){
      update({tab:"explore",view:"universe",family:"energy",query:"",trend:"all",momentum:"all",layout:"table"});
      const search=root.querySelector("[data-cw-search]");
      if(search){search.focus({preventScroll:true});search.scrollIntoView({block:"nearest",behavior:"auto"});}
      return;
    }
    update({tab:"explore", asset:"oil",view:"detail"});
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
    event.preventDefault(); update({tab:TABS[next],...(TABS[next]==="explore"?{view:"universe"}:{})}); root.querySelector('[data-cw-tab="' + TABS[next] + '"]').focus();
  });
  all("[data-cw-compare], [data-cw-pick]").forEach(input => input.addEventListener("change", () => {
    if (input.checked && state.compare.length === 4) {
      input.checked = false;
      const message=text("Choose up to four. Remove one to add another.", "最多比较四个品种，请先取消一个。");
      compareStatus.textContent=message;
      const visibleStatus=root.querySelector("[data-cw-results-count]");if(visibleStatus && state.tab==="explore")visibleStatus.textContent=message;
      const briefHead=input.closest(".cw-brief-head");
      const briefStatus=briefHead && briefHead.querySelector("[data-cw-brief-compare-status]");
      if(briefStatus)briefStatus.textContent=message;
      return;
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
    if(inspector && inspector.hasAttribute("open")){inspectorTrigger=null;closeInspector();}
  }
  window.addEventListener("popstate",restore);
  window.addEventListener("hashchange",restore);
  document.addEventListener("langchange",render);
  new MutationObserver(records => { if (records.some(r => r.attributeName === "data-lang")) render(); }).observe(document.documentElement,{attributes:true,attributeFilter:["data-lang"]});
  render(); restore();
})();
