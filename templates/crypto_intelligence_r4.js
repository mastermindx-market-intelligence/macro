/* Progressive enhancement only: the first reading and price chart render on the server. */
(function () {
  "use strict";
  var root = document.getElementById("crypto-intelligence"), dataNode = document.getElementById("cri-data");
  if (!root || !dataNode) return;
  var data;
  try { data = JSON.parse(dataNode.textContent); } catch (error) { return; }
  var dialog = document.getElementById("cri-dialog"), body = document.getElementById("cri-dialog-body");
  var title = document.getElementById("cri-dialog-title"), kicker = document.getElementById("cri-dialog-kicker");
  var views = ["overview", "bitcoin", "markets", "scenarios"], lastTrigger = null, toastTimer = null;
  var storageKey = "mmx.crypto.r4.scenarios.v1", currentShock = "tightening";
  function zh() { return document.documentElement.dataset.lang === "zh"; }
  function t(en, cn) { return zh() ? cn : en; }
  function field(value, name) { return value[name + (zh() ? "_zh" : "_en")] || ""; }
  function money(value) { return typeof value === "number" && isFinite(value) ? "$" + value.toLocaleString("en-US", { maximumFractionDigits: value < 1000 ? 2 : 0 }) : t("Unavailable", "暂无"); }
  function pct(value) { return typeof value === "number" && isFinite(value) ? (value > 0 ? "+" : "") + value.toFixed(1) + "%" : t("Unavailable", "暂无"); }
  function node(tag, text, className) {
    var element = document.createElement(tag);
    if (text !== undefined && text !== null) element.textContent = String(text);
    if (className) element.className = className;
    return element;
  }
  function paragraph(text) { var element = node("p", text); body.appendChild(element); return element; }
  function heading(text) { body.appendChild(node("h3", text)); }
  function button(text, action) { var element = node("button", text, "cri-btn"); element.type = "button"; element.addEventListener("click", action); body.appendChild(element); return element; }
  function definition(rows) {
    var list = node("dl");
    rows.forEach(function (row) { var item = node("div"); item.append(node("dt", row[0]), node("dd", row[1] == null ? t("Unavailable", "暂无") : row[1])); list.appendChild(item); });
    body.appendChild(list);
  }
  function link(text, url) { var a = node("a", text); a.href = url; var p = node("p"); p.appendChild(a); body.appendChild(p); }
  function state() {
    var parts = location.hash.slice(1).split("?"), view = views.indexOf(parts[0]) >= 0 ? parts[0] : root.dataset.defaultView;
    return { view: view, params: new URLSearchParams(parts.slice(1).join("?")) };
  }
  function address(view, params) { return "#" + view + (params.toString() ? "?" + params.toString() : ""); }
  function update(view, changes, replace) {
    var current = state(), params = current.params;
    Object.keys(changes || {}).forEach(function (key) { if (changes[key] == null || changes[key] === "") params.delete(key); else params.set(key, changes[key]); });
    var metadata = replace && params.has("panel") && history.state && history.state.drawer ? history.state : { r4: true };
    history[replace ? "replaceState" : "pushState"](metadata, "", address(view || current.view, params));
    apply();
  }
  function horizon() { return state().params.get("h") === "30" ? "30" : "7"; }
  function activeScenario(id) { return (data.scenarios[horizon()] || []).find(function (s) { return s.id === id; }); }
  function open(key, trigger, scenarioHorizon) {
    if (trigger) lastTrigger = trigger;
    var s = state(), previous = location.hash, alreadyOpen = s.params.has("panel");
    s.params.set("panel", key);
    if (scenarioHorizon) s.params.set("h", scenarioHorizon);
    var managed = history.state && history.state.r4 && history.state.drawer && Number.isInteger(history.state.depth);
    var depth = managed ? history.state.depth + 1 : 1;
    var detachedOrigin = managed ? history.state.detachedOrigin === true : alreadyOpen;
    history.pushState({ r4: true, drawer: true, previous: previous, depth: depth, detachedOrigin: detachedOrigin }, "", address(s.view, s.params));
    apply();
  }
  function close() {
    if (history.state && history.state.r4 && history.state.drawer && !history.state.detachedOrigin && Number.isInteger(history.state.depth) && history.state.depth > 0) history.go(-history.state.depth);
    else update(null, { panel: null }, true);
  }
  function toast(message) {
    var el = document.getElementById("cri-toast");
    clearTimeout(toastTimer); el.textContent = message; el.hidden = false;
    toastTimer = setTimeout(function () { el.hidden = true; }, 5000);
  }
  function stored() {
    try {
      var entries = JSON.parse(localStorage.getItem(storageKey) || "[]");
      return Array.isArray(entries) ? entries.filter(function (s) { return s && typeof s.revision === "string" && s.authority === "conditional_research_only"; }).slice(0, 50) : [];
    } catch (error) { return []; }
  }
  function expired(s) { return !s.expires || s.expires < new Date().toISOString().slice(0, 10); }
  function snapshotEvidence() {
    return {
      bitcoin_as_of: data.as_of || null,
      market_as_of: data.market_as_of || null,
      asset_as_of: data.asset_as_of || null,
      history_state: data.history && data.history.state || "unavailable",
      families: (data.families || []).map(function (f) {
        return { id: f.id, label_en: f.label_en, label_zh: f.label_zh,
          state_en: f.state_en, state_zh: f.state_zh, quality: f.quality || "unknown",
          snapshot_as_of: f.snapshot_as_of || null, source: f.source || null };
      })
    };
  }
  function save(s) {
    if (!s) return;
    var items = stored(), index = items.findIndex(function (item) { return item.revision === s.revision; });
    if (index < 0 && (expired(s) || s.state === "insufficient" || s.progress_state === "unavailable")) { toast(t("This scenario cannot be saved with the available evidence.", "现有证据不足，无法保存此情景。")); return; }
    if (index >= 0) items.splice(index, 1);
    else items.push(Object.assign({}, s, { saved_at: new Date().toISOString(), issue_evidence: snapshotEvidence() }));
    try {
      localStorage.setItem(storageKey, JSON.stringify(items.slice(-50)));
      toast(index >= 0 ? t("Removed from this device.", "已从本设备移除。") : t("Saved on this device.", "已保存至本设备。"));
      if (index >= 0 && (state().params.get("panel") || "").indexOf("saved-item:") === 0) update(null, { panel: "saved" }, true);
      else renderDrawer(state().params.get("panel"));
      var restoredAction = body.querySelector("[data-snapshot-action]");
      (restoredAction || document.getElementById("cri-dialog-close")).focus();
    } catch (error) { toast(t("This browser could not save the scenario. The current view still works.", "浏览器无法保存情景，当前页面仍可使用。")); }
  }
  function status(s) {
    if (expired(s)) return t("Expired · historical context only", "已到期 · 仅供历史参考");
    if (s.state === "insufficient") return t("Insufficient price history", "价格历史不足");
    if (s.progress_en) return field(s, "progress");
    if (s.levels && ((s.id === "continuation" && s.levels.position === "above") || (s.id === "failure" && s.levels.position === "below"))) return t("Price condition met · demand unconfirmed", "价格条件已满足 · 需求尚未确认");
    return t("Conditional · confirmation pending", "条件路径 · 等待确认");
  }
  function evidence(family) {
    heading(field(family, "label"));
    paragraph(field(family, "note"));
    definition([
      [t("Observed reading", "观测读数"), field(family, "state")],
      [t("Underlying observation date", "底层观测日期"), family.as_of || t("Not supplied", "未提供")],
      [t("Published snapshot", "发布快照"), family.snapshot_as_of],
      [t("Coverage", "覆盖状态"), family.quality === "observed" ? t("Dated observation", "带日期观测") : family.quality === "snapshot_only" ? t("Snapshot context; underlying date not supplied", "快照背景；未提供底层日期") : family.quality === "stale" ? t("Update overdue", "更新滞后") : t("Evidence incomplete", "证据不完整")]
    ]);
    if (family.members.length) {
      heading(t("Component readings", "组成读数"));
      definition(family.members.map(function (member) { return [field(member, "label"), field(member, "state")]; }));
    }
    var details = node("details", null, "mx-disc");
    details.appendChild(node("summary", t("Source and interpretation", "来源与解读")));
    details.appendChild(node("p", family.source));
    details.appendChild(node("p", t("Related readings are not independent votes, and this is not a forecast probability.", "相关读数不是独立投票，也不代表预测概率。")));
    body.appendChild(details);
  }
  function scenario(s, frozen) {
    if (!s) { title.textContent = t("Scenario unavailable", "情景暂不可用"); paragraph(t("This scenario is unavailable. The source may have changed or the saved item was removed.", "该情景不可用，原始来源可能已经变化或快照已经移除。")); return; }
    title.textContent = field(s, "title");
    paragraph(status(s)).className = "cri-warning";
    paragraph((s.asset || t("Asset unavailable", "资产暂无")) + " · " + s.horizon_days + t(" days", "天") + " · " + (s.as_of || t("Date not supplied", "未提供日期"))).className = "cri-note";
    if (s.next_check_en && !expired(s)) { heading(t("Next check", "下一步检查")); paragraph(field(s, "next_check")); }
    heading(expired(s) ? t("Sequence at the original cutoff", "原始时点的后续路径") : t("What could follow", "可能的后续变化")); paragraph(field(s, "sequence"));
    heading(expired(s) ? t("Original invalidation condition", "原始失效条件") : t("What changes the view", "什么会改变判断")); paragraph(field(s, "invalidation"));
    var details = node("details", null, "mx-disc");
    details.appendChild(node("summary", t("Conditions and evidence", "条件与证据")));
    details.appendChild(node("p", field(s, "condition")));
    details.appendChild(node("p", field(s, "counter")));
    details.appendChild(node("p", t("Expires: ", "到期日：") + s.expires));
    details.appendChild(node("p", t("Levels use prior daily closes. They are research conditions, not official model invalidations.", "价位来自前期日收盘，属于研究条件，并非官方模型失效位。")));
    body.appendChild(details);
    button(t("Historical review", "历史检验"), function () { open((frozen ? "memory-saved:" + s.revision : "memory:" + s.id), null, String(s.horizon_days)); });
    if (frozen) {
      heading(t("Original evidence snapshot", "原始证据快照"));
      var savedEvidence = s.issue_evidence;
      if (savedEvidence && Array.isArray(savedEvidence.families) && savedEvidence.families.length) {
        paragraph(t("Bitcoin: ", "比特币：") + (savedEvidence.bitcoin_as_of || t("date unavailable", "日期暂无")) +
          t(" · Broader market: ", " · 全市场：") + (savedEvidence.market_as_of || t("date unavailable", "日期暂无"))).className = "cri-note";
        var digest = node("details", null, "mx-disc"), digestSummary = node("summary",
          t("Review saved source quality and dates", "查看保存时的来源质量与日期"));
        digest.appendChild(digestSummary);
        var digestList = node("dl");
        savedEvidence.families.filter(function (f) { return f && typeof f === "object"; }).forEach(function (f) {
          var item = node("div"), name = node("dt", field(f, "label") || f.id || t("Unknown reading", "未知读数"));
          var detail = node("dd", (field(f, "state") || t("Unavailable", "暂无")) + " · " +
            (f.quality || "unknown") + " · " + (f.snapshot_as_of || t("date unavailable", "日期暂无")));
          item.append(name, detail); digestList.appendChild(item);
        });
        digest.appendChild(digestList); body.appendChild(digest);
        paragraph(t("These are the readings saved at issue time, not current evidence or validated forecast performance.", "这些读数属于原始时点，并非最新证据或已验证的预测表现。")).className = "cri-note";
      } else paragraph(t("Evidence digest was not preserved in this older snapshot. Its original conditions and cutoff remain visible, but source quality cannot be reconstructed.", "旧快照未保存原始证据摘要。原始条件与时间仍可查看，但无法恢复当时的来源质量。")).className = "cri-warning";
    }
    if (!frozen) {
      var saved = stored().some(function (item) { return item.revision === s.revision; });
      var saveButton = button(saved ? t("Remove snapshot", "移除快照") : t("Save snapshot", "保存快照"), function () { save(s); });
      saveButton.dataset.snapshotAction = "toggle";
      saveButton.disabled = !saved && (expired(s) || s.state === "insufficient" || s.progress_state === "unavailable");
      button(t("Inspect demand evidence", "查看需求证据"), function () { open("evidence:liquidity_flows"); });
    } else {
      paragraph(t("This saved version preserves its original conditions and cutoff.", "该保存版本保留原始条件与证据日期。"));
      button(t("Remove from this device", "从本设备移除"), function () { save(s); }).dataset.snapshotAction = "remove";
    }
  }
  function renderDrawer(key) {
    if (!key) return;
    body.replaceChildren(); dialog.classList.toggle("cri-dialog-wide", key === "comparison"); kicker.textContent = t("CRYPTO INTELLIGENCE", "加密资产情报");
    var parts = key.split(":"), category = parts[0], id = parts.slice(1).join(":");
    if (category === "evidence") {
      var rows = id === "all" ? data.families : data.families.filter(function (f) { return f.id === id; });
      title.textContent = t("Evidence behind the view", "判断背后的证据");
      if (!rows.length) paragraph(t("This evidence is unavailable.", "该证据暂不可用。"));
      if (id === "all") {
        paragraph(t("Choose one evidence family. Source dates and missing observations stay with that reading.", "选择一类证据，查看其来源日期与缺失观测。"));
        rows.forEach(function (family) {
          var entry = button(field(family, "label") + " · " + field(family, "state"), function () { open("evidence:" + family.id); });
          entry.classList.add("cri-evidence-index");
        });
      } else rows.forEach(evidence);
    } else if (category === "scenario") {
      scenario(activeScenario(id), false);
    } else if (category === "saved-item") {
      scenario(stored().find(function (s) { return s.revision === id; }), true);
    } else if (category === "asset") {
      var asset = data.assets.find(function (a) { return a.symbol === id; });
      title.textContent = asset ? asset.name + " · " + asset.symbol : t("Asset unavailable", "资产暂不可用");
      if (asset) {
        definition([[t("Price", "价格"), money(asset.price)], [t("Observation date", "观测日期"), asset.as_of], [t("30-day change", "30天涨跌"), pct(asset.change_30d_pct)], [t("90-day relative return vs Bitcoin", "90天相对比特币表现"), pct(asset.relative_90d_pct)], [t("Structure", "结构"), field(asset, "trend")], [t("Risk", "风险"), field(asset, "risk")]]);
        heading(t("What matters next", "接下来关注什么"));
        paragraph(t("Look for persistent relative strength with improving risk conditions. The present state alone is not an entry signal.", "关注相对强势能否持续，以及风险是否改善。当前状态本身不是入场信号。"));
        heading(t("Coverage", "覆盖情况")); paragraph(field(asset, "coverage"));
        paragraph(t("Asset-specific conditional price levels are not yet available from this contract.", "该数据约定暂未提供此资产的条件价位。"));
      }
    } else if (category === "comparison") {
      title.textContent = t("Compare supported assets", "比较已覆盖资产");
      paragraph(t("Compare the same published horizon; missing values stay unavailable.", "比较相同发布周期；缺失读数保留为暂无。"));
      var wrap = node("div", null, "cri-comparison-scroll"), table = node("table", null, "cri-comparison-table");
      var caption = node("caption", t("Bitcoin is the relative-return benchmark (0% by definition, not its price change). Asset observations retain their own dates.", "比特币为相对表现基准（定义为0%，并非其价格涨跌），各资产保留自己的观测日期。"));
      table.appendChild(caption);
      var headerRow = node("tr");
      [t("Measure", "指标")].concat(data.assets.map(function (a) { return a.symbol; })).forEach(function (label) { var cell = node("th", label); cell.scope = "col"; headerRow.appendChild(cell); });
      var head = node("thead"); head.appendChild(headerRow); table.appendChild(head);
      var tbody = node("tbody");
      [[t("Observation date", "观测日期"), function (a) { return a.as_of; }],
       [t("90D vs Bitcoin", "90天相对比特币"), function (a) { return pct(a.relative_90d_pct); }],
       [t("30D price change", "30天价格涨跌"), function (a) { return pct(a.change_30d_pct); }],
       [t("Structure", "结构"), function (a) { return field(a, "trend"); }],
       [t("Risk", "风险"), function (a) { return field(a, "risk"); }]].forEach(function (row) {
        var tr = node("tr"), label = node("th", row[0]); label.scope = "row"; tr.appendChild(label);
        data.assets.forEach(function (a) { tr.appendChild(node("td", row[1](a) || t("Unavailable", "暂无"))); }); tbody.appendChild(tr);
      });
      table.appendChild(tbody); wrap.appendChild(table); body.appendChild(wrap);
      if (!data.assets.length) paragraph(t("No supported assets are available for comparison.", "暂无可供比较的已覆盖资产。"));
    } else if (category === "coverage") {
      title.textContent = t("Data and coverage", "数据与覆盖");
      definition([[t("Bitcoin daily close", "比特币日收盘"), data.as_of], [t("Broad-market snapshot", "全市场快照"), data.market_as_of], [t("Asset snapshot", "资产快照"), data.asset_as_of]]);
      heading(t("Broader market context", "全市场背景"));
      paragraph(field(data, "market_headline")); paragraph(field(data, "market_summary"));
      if (data.limitations.source_dates_differ) paragraph(t("These observations have different cutoffs. An older market assessment does not confirm the latest Bitcoin price move.", "这些观测的截止日期不同，较早的全市场判断不能确认比特币最新价格变化。")).className = "cri-warning";
      button(t("Inspect breadth coverage", "查看广度覆盖"), function () { open("evidence:participation"); });
      button(t("Inspect price basis", "查看价格口径"), function () { open("history"); });
    } else if (category === "history") {
      title.textContent = t("Price data and levels", "价格数据与价位");
      var displayedDates = data.history.dates.slice(state().params.get("window") === "30" ? -30 : -90);
      definition([[t("Observation date", "观测日期"), data.as_of], [t("Price basis", "价格口径"), t("Published Bitcoin daily closes in USD", "已发布的比特币美元日收盘价")], [t("Displayed history", "展示历史"), displayedDates.length ? displayedDates[0] + " → " + displayedDates[displayedDates.length - 1] : t("Unavailable", "暂无")], [t("Latest segment", "最新连续片段"), data.history.state]]);
      if (data.limitations.price_basis_divergence) paragraph(t("The cockpit price differs from the chart series. This chart and its levels use the published daily close series.", "快照价格与图表序列不同。本图及价位采用已发布的日收盘序列。")).className = "cri-warning";
      paragraph(t("The chart uses the latest uninterrupted daily segment. Missing dates or prices break the line; they are not filled with zero.", "图表只展示最新连续日频片段。缺失日期或价格会中断曲线，不会补零。"));
      paragraph(t("The 7-day research scenarios use the prior 20 daily closes; the 30-day scenarios use the prior 60. Today's close is excluded from both thresholds.", "7天情景使用前20天日收盘；30天情景使用前60天。两者阈值均不包含当日收盘。"));
      if (data.history.gaps) paragraph(t("Older gaps exist. The plot starts after the most recent gap.", "较早历史存在缺口，图表从最近一次缺口后开始。")).className = "cri-warning";
    } else if (category === "model") {
      title.textContent = t("Bitcoin model", "比特币模型");
      if (data.model.available) {
        paragraph(data.model.exposure_pct + "%").className = "cri-large-number";
        paragraph(t("Canonical model exposure", "官方模型仓位"));
        definition([[t("Effective date", "生效日期"), data.model.as_of], [t("Authority", "权威来源"), data.model.source || data.model.schema]]);
      } else paragraph(t("The model decision is unavailable. No replacement allocation is inferred.", "模型决策暂不可用，不推算替代仓位。")).className = "cri-warning";
      paragraph(t("The scenario workspace does not change the model. Crypto budget splitting retains its existing separate governed projection.", "情景研究不会改变模型。加密预算拆分继续遵循既有约定。"));
      link(t("Open the existing model record", "查看现有模型记录"), "https://www.mastermind-x.com/vector.html");
    } else if (category === "saved") {
      title.textContent = t("Saved snapshots", "已存快照");
      paragraph(t("Saved in this browser. Each snapshot preserves its original evidence cutoff.", "保存在此浏览器中，每份快照保留原始证据截止日期。"));
      var items = stored();
      if (!items.length) paragraph(t("Nothing saved yet. Open a scenario and save its dated conditions.", "尚未保存。打开一个情景，保存其带日期的条件。"));
      items.forEach(function (s) { button(field(s, "title") + " · " + s.horizon_days + t(" days", "天") + " · " + s.as_of, function () { open("saved-item:" + s.revision); }); });
    } else if (category === "memory" || category === "memory-saved") {
      title.textContent = t("Historical review", "历史检验");
      var historicalContext = category === "memory-saved" ? stored().find(function (s) { return s.revision === id; }) : (id ? activeScenario(id) : null);
      paragraph(historicalContext ? field(historicalContext, "title") + " · BTC · " + historicalContext.horizon_days + t(" days · evidence at ", "天 · 证据日期 ") + historicalContext.as_of : "BTC · " + horizon() + t(" days · evidence at ", "天 · 证据日期 ") + (data.as_of || t("Unavailable", "暂无")));
      paragraph(t("No qualified comparison yet", "暂无合格的历史比较")).className = "cri-warning";
      paragraph(t("A historical match must preserve the scenario's issue-time evidence, horizon and eligible universe. Similar-looking charts alone do not establish predictive value.", "历史匹配必须保留情景发布时的证据、周期与合格样本。图形相似本身不能证明预测价值。"));
      heading(t("Required before results", "结果发布前需要"));
      definition([[t("Point-in-time history", "时点历史"), t("Source availability and revisions retained", "保留来源可用时间与修订")], [t("Independent episodes", "独立事件"), t("Overlapping warnings are not separate cases", "重叠预警不算独立案例")], [t("Counterexamples", "反例"), t("Failures shown alongside matches", "失败案例与匹配案例并列")], [t("Forecast evaluation", "预测检验"), t("Simple baselines, held-out periods and calibration", "简单基线、留出区间与校准")]]);
    } else if (category === "research") {
      title.textContent = t("Research behind the scenarios", "情景背后的研究");
      heading(t("Macro transmission", "宏观传导"));
      paragraph(t("The IMF study supports investigating the monetary-policy and risk-taking channel. It does not establish a fixed current sensitivity or this scenario's probability.", "IMF研究支持检验货币政策与风险偏好传导，但不代表固定的当前敏感度或本情景概率。"));
      link("IMF · The Crypto Cycle and US Monetary Policy", "https://www.imf.org/en/publications/wp/issues/2023/08/04/the-crypto-cycle-and-us-monetary-policy-534834");
      heading(t("Carry and leverage", "基差与杠杆"));
      paragraph(t("The BIS study motivates testing venue-specific carry and funding stress. Its historical findings are not a promoted live crash signal.", "BIS研究支持检验各交易场所的基差与融资压力；历史发现不是已获认可的实时崩盘信号。"));
      link("BIS · Crypto carry", "https://www.bis.org/publications/working-paper-1087-crypto-carry");
    } else {
      title.textContent = t("View unavailable", "内容暂不可用");
      paragraph(t("Return to the current view and choose an available tool.", "请返回当前页面，选择可用工具。"));
    }
  }
  function filterMarkets() {
    var s = state(), query = (s.params.get("q") || "").toLowerCase(), filter = s.params.get("filter") || "all", sort = s.params.get("sort") || "relative";
    document.getElementById("cri-search").value = s.params.get("q") || "";
    document.getElementById("cri-search").placeholder = t("Search assets", "搜索资产");
    Array.from(document.getElementById("cri-filter").options).forEach(function(o){o.textContent = {all:t("All assets","全部资产"),leaders:t("Leading Bitcoin","领先比特币"),stressed:t("Stressed","承压")}[o.value];});
    Array.from(document.getElementById("cri-sort").options).forEach(function(o){o.textContent = {relative:t("Relative strength","相对强弱"),return:t("30-day return","30天涨跌"),symbol:t("Asset","资产")}[o.value];});
    document.getElementById("cri-filter").value = ["all", "leaders", "stressed"].indexOf(filter) >= 0 ? filter : "all";
    document.getElementById("cri-sort").value = ["relative", "return", "symbol"].indexOf(sort) >= 0 ? sort : "relative";
    var items = data.assets.slice().sort(function (a, b) {
      if (sort === "symbol") return a.symbol.localeCompare(b.symbol);
      var key = sort === "return" ? "change_30d_pct" : "relative_90d_pct";
      return (b[key] === null ? -Infinity : b[key]) - (a[key] === null ? -Infinity : a[key]);
    }), shown = 0, tbody = document.querySelector("#cri-market-table tbody");
    items.forEach(function (asset) {
      var row = Array.from(tbody.children).find(function (r) { return r.dataset.assetRow === asset.symbol; });
      if (!row) return;
      var matches = (asset.name + " " + asset.symbol).toLowerCase().indexOf(query) >= 0 &&
        (filter !== "leaders" || asset.relative_en === "Leading Bitcoin") && (filter !== "stressed" || asset.risk_en === "Stressed");
      row.hidden = !matches; tbody.appendChild(row); if (matches) shown++;
    });
    document.getElementById("cri-market-empty").hidden = shown !== 0;
    document.getElementById("cri-market-count").textContent = t(shown + " of " + data.assets.length + " supported assets", "显示" + shown + "个，共覆盖" + data.assets.length + "个资产");
  }
  var shocks = {
    tightening: {
      family: "macro_backdrop",
      title: ["Pressure on demand", "需求可能承压"],
      steps: [["Higher rates or a stronger dollar tighten financial conditions.", "利率上升或美元走强，金融条件收紧。"], ["Risk appetite can weaken, reducing marginal crypto demand.", "风险偏好可能转弱，压低边际加密需求。"], ["A price break matters more if spot demand also weakens.", "若现货需求同步转弱，价格失守更值得关注。"]],
      limit: ["Macro hypothesis · weeks to months. Confirm the actual release surprise and market response.", "宏观假设 · 数周至数月。需确认实际数据意外与市场反应。"]
    },
    easing: {
      family: "macro_backdrop",
      title: ["Room for demand", "需求可能获得空间"],
      steps: [["Easier financial conditions can support risk appetite.", "金融条件放松，可能支持风险偏好。"], ["Fresh capital must reach crypto rather than remain idle.", "新增资金需要进入加密市场，而非闲置。"], ["A recovery is stronger when participation expands with price.", "价格回升伴随参与扩大，修复才更有支撑。"]],
      limit: ["Macro hypothesis · weeks to months. Easier conditions do not guarantee crypto inflows.", "宏观假设 · 数周至数月。金融条件放松不保证资金流入加密市场。"]
    },
    leverage: {
      family: "leverage_derivatives",
      title: ["A more fragile rise", "上涨可能更脆弱"],
      steps: [["Leveraged positioning grows faster than observed spot demand.", "杠杆头寸增长快于已观测的现货需求。"], ["The market becomes more sensitive to funding and margin shocks.", "市场对融资与保证金冲击更敏感。"], ["A downside break can force selling if positioning is crowded.", "若头寸拥挤，向下突破可能触发被动卖出。"]],
      limit: ["Conditional mechanism. Funding and venue coverage must be current before confirmation.", "条件机制。确认前需要最新资金费率与交易场所覆盖。"]
    }
  };
  function renderShock() {
    var shock = shocks[currentShock], index = zh() ? 1 : 0;
    var list = root.querySelector("#cri-shock-chain"), label = root.querySelector("#cri-shock-title");
    var evidenceButton = root.querySelector("#cri-shock-evidence"), limit = root.querySelector("#cri-shock-limit");
    if (!shock || !shock.title || !shock.steps || !shock.steps[1] || !shock.limit || !list || !label || !evidenceButton || !limit) return;
    label.textContent = shock.title[index]; list.replaceChildren();
    var families = data.families || [];
    var context = families.find(function (f) { return f.id === shock.family; });
    var demand = families.find(function (f) { return f.id === "liquidity_flows"; });
    var cases = (data.scenarios || {})[horizon()] || [];
    var next = cases.find(function (s) { return s.progress_state === "price_met"; }) || cases.find(function (s) { return s.id === "range"; });
    list.appendChild(node("li", t("Observed context: ", "已观测背景：") + (context ? field(context, "state") + t(" · snapshot ", " · 快照 ") + (context.snapshot_as_of || t("date not supplied", "未提供日期")) : t("Unavailable", "暂无"))));
    list.appendChild(node("li", t("Possible transmission: ", "可能的传导：") + shock.steps[1][index]));
    list.appendChild(node("li", t("Demand evidence: ", "需求证据：") + (demand ? field(demand, "state") : t("Unavailable", "暂无")) + t(". Fresh observations are required for confirmation.", "。确认前需要最新观测。")));
    list.appendChild(node("li", t("Next check: ", "下一步检查：") + (next && !expired(next) ? field(next, "title") + " · " + field(next, "next_check") : t("Wait for current, sufficient price evidence.", "等待充足的最新价格证据。"))));
    evidenceButton.dataset.open = "evidence:" + shock.family;
    limit.textContent = shock.limit[index];
    root.querySelectorAll("[data-shock]").forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.shock === currentShock)); });
  }
  function apply() {
    var s = state(), h = horizon(), windowSize = s.params.get("window") === "30" ? "30" : "90";
    root.querySelectorAll("[data-view]").forEach(function (p) { p.hidden = p.dataset.view !== s.view; });
    root.querySelectorAll("[data-route]").forEach(function (a) { if (a.closest(".cri-tabs") && a.dataset.route === s.view) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); });
    root.querySelectorAll("[data-chart-window]").forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.chartWindow === windowSize)); });
    root.querySelectorAll("[data-chart-panel]").forEach(function (p) { p.hidden = p.dataset.chartPanel !== windowSize; });
    root.querySelectorAll("[data-horizon]").forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.horizon === h)); });
    root.querySelectorAll("[data-case-horizon]").forEach(function (p) { p.hidden = p.dataset.caseHorizon !== h; });
    filterMarkets(); renderShock();
    if (s.params.get("panel")) { var focusWasInside = dialog.contains(document.activeElement); renderDrawer(s.params.get("panel")); if (!dialog.open) dialog.showModal(); else if (focusWasInside && !dialog.contains(document.activeElement)) document.getElementById("cri-dialog-close").focus(); }
    else if (dialog.open) { dialog.close(); if (lastTrigger && document.contains(lastTrigger)) lastTrigger.focus(); }
  }
  root.addEventListener("click", function (event) {
    var route = event.target.closest("[data-route]"), openButton = event.target.closest("[data-open]");
    if (route && !event.metaKey && !event.ctrlKey && !event.shiftKey && event.button === 0) { event.preventDefault(); update(route.dataset.route, { panel: null }); }
    else if (openButton) { event.preventDefault(); var caseGroup = openButton.closest("[data-case-horizon]"); var scenarioHorizon = openButton.dataset.open.indexOf("scenario:") === 0 ? (caseGroup ? caseGroup.dataset.caseHorizon : horizon()) : null; open(openButton.dataset.open, openButton, scenarioHorizon); }
    var windowButton = event.target.closest("[data-chart-window]");
    if (windowButton) update(null, { window: windowButton.dataset.chartWindow }, true);
    var horizonButton = event.target.closest("[data-horizon]");
    if (horizonButton) update(null, { h: horizonButton.dataset.horizon }, true);
    var shockButton = event.target.closest("[data-shock]");
    if (shockButton) { currentShock = shockButton.dataset.shock; renderShock(); }
  });
  document.getElementById("cri-dialog-close").addEventListener("click", close);
  dialog.addEventListener("cancel", function (event) { event.preventDefault(); close(); });
  dialog.addEventListener("click", function (event) { var r = dialog.getBoundingClientRect(); if (event.target === dialog && (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom)) close(); });
  document.getElementById("cri-search").addEventListener("input", function (event) { update(null, { q: event.target.value.slice(0, 80) }, true); });
  document.getElementById("cri-filter").addEventListener("change", function (event) { update(null, { filter: event.target.value }, true); });
  document.getElementById("cri-sort").addEventListener("change", function (event) { update(null, { sort: event.target.value }, true); });
  document.getElementById("cri-reset").addEventListener("click", function () { update(null, { q: null, filter: null, sort: null }, true); });
  window.addEventListener("popstate", apply); window.addEventListener("hashchange", apply);
  new MutationObserver(function () { apply(); }).observe(document.documentElement, { attributes: true, attributeFilter: ["data-lang"] });
  apply();
})();
