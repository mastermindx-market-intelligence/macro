/* R26 display controller. Reads the embedded owner projection; never writes account,
   event, watch, feed or delivery state. Prepared rules live in this tab only. */
(function () {
  "use strict";
  const root = document.querySelector("[data-fxr]");
  const data = document.getElementById("forex-r26-consumer");
  if (!root || !data) return;
  let view;
  try { view = JSON.parse(data.textContent); } catch (_) { return; }
  const rows = new Map(view.destinations.today.pair_tabs.filter(r => r.pair_scope === "fx_pair").map(r => [r.pair, r]));
  const destinations = ["today", "explore", "my_watches"];
  const tabs = ["outlook", "drivers", "history", "impact"];
  const selected = new Set();
  const prepared = [];
  let pendingRule = null, editIndex = -1;
  let state = { destination: "today", pair: null, tab: "outlook", from: "today" };
  const q = selector => root.querySelector(selector);
  const all = selector => Array.from(root.querySelectorAll(selector));
  const zh = () => document.documentElement.getAttribute("data-lang") === "zh";
  const words = (en, cn) => zh() ? cn : en;
  const el = (tag, text, className) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  };
  function currentLean(row) {
    const model = row.model_direction;
    if (!model || !model.available) return words("Current lean unavailable", "当前倾向不可用");
    return model.pair_direction === "higher" ? words("Leaning higher", "倾向走高") :
      model.pair_direction === "lower" ? words("Leaning lower", "倾向走低") : words("No clear lean", "无明显倾向");
  }
  function safePrice(row) {
    return row.status !== "withheld" && Number.isFinite(row.price) ? row.price.toFixed(4) : "—";
  }
  function safeChange(row) { return row.status !== "withheld" && row.chg_display ? row.chg_display : "—"; }
  function period(row) { return row.chg_horizon === "1m" ? words("1 month", "1个月") : words("Reported change", "报告变化"); }

  function readRoute() {
    if (!location.hash.startsWith("#forex/")) {
      state = { destination: "today", pair: null, tab: "outlook", from: "today" };
      return;
    }
    const fragment = location.hash.slice(7);
    const split = fragment.indexOf("?");
    const path = split < 0 ? fragment : fragment.slice(0, split);
    const params = new URLSearchParams(split < 0 ? "" : fragment.slice(split + 1));
    const parts = path.split("/");
    const destination = destinations.includes(parts[0]) ? parts[0] : "explore";
    state = { destination, pair: null, tab: "outlook", from: destination };
    if (parts[0] === "pair" && rows.has(parts[1])) {
      state = { destination: "pair", pair: parts[1], tab: tabs.includes(parts[2]) ? parts[2] : "outlook",
        from: destinations.includes(params.get("from")) ? params.get("from") : "explore" };
    }
    q("#fxr-search").value = params.get("q") || "";
    q("#fxr-filter").value = ["all", "up", "down", "unknown"].includes(params.get("move")) ? params.get("move") : "all";
  }
  function writeRoute(replace) {
    const params = new URLSearchParams();
    const query = q("#fxr-search").value.trim();
    const move = q("#fxr-filter").value;
    if (query) params.set("q", query);
    if (move !== "all") params.set("move", move);
    if (state.destination === "pair") params.set("from", state.from);
    const path = state.destination === "pair" ? "pair/" + state.pair + "/" + state.tab : state.destination;
    const url = new URL(location.href);
    url.hash = "forex/" + path + (params.size ? "?" + params.toString() : "");
    history[replace ? "replaceState" : "pushState"](null, "", url);
  }
  function renderRoute(focus) {
    all("[data-fxr-view]").forEach(panel => { panel.hidden = panel.dataset.fxrView !== state.destination; });
    all("[data-fxr-destination]").forEach(button => {
      const active = button.dataset.fxrDestination === (state.destination === "pair" ? state.from : state.destination);
      button.setAttribute("aria-selected", String(active));
      button.tabIndex = active ? 0 : -1;
    });
    all("[data-fxr-pair]").forEach(article => {
      const active = state.destination === "pair" && article.dataset.fxrPair === state.pair;
      article.hidden = !active;
      if (!active) return;
      article.querySelectorAll("[data-fxr-pair-tab]").forEach(button => {
        const chosen = button.dataset.fxrPairTab === state.tab;
        button.setAttribute("aria-selected", String(chosen));
        button.tabIndex = chosen ? 0 : -1;
      });
      article.querySelectorAll("[data-fxr-panel]").forEach(panel => { panel.hidden = panel.dataset.fxrPanel !== state.tab; });
      if (focus) article.querySelector("h2").focus();
      if (window.ilxReveal) window.ilxReveal(article);
    });
    filterPairs(false);
  }
  function navigate(destination, pair, tab, focus) {
    const from = state.destination === "pair" ? state.from : state.destination;
    state = { destination, pair: pair || null, tab: tab || "outlook", from: destinations.includes(from) ? from : "explore" };
    writeRoute(false);
    renderRoute(focus);
  }
  function filterPairs(updateUrl) {
    const search = q("#fxr-search").value.trim().toLocaleLowerCase().replace(/\//g, "");
    const move = q("#fxr-filter").value;
    let count = 0;
    all("[data-fxr-search-row]").forEach(row => {
      const match = row.dataset.fxrSearchText.toLocaleLowerCase().includes(search) &&
        (move === "all" || row.dataset.fxrMove === move);
      row.hidden = !match;
      if (match) count++;
    });
    q("#fxr-no-results").hidden = count !== 0;
    q("#fxr-results").textContent = words(count + " pairs shown", "显示 " + count + " 个货币对");
    if (updateUrl) writeRoute(true);
  }
  function openDialog(dialog, opener) {
    dialog._returnFocus = opener || document.activeElement;
    dialog.showModal();
  }
  all("dialog").forEach(dialog => dialog.addEventListener("close", () => {
    if (dialog._returnFocus && dialog._returnFocus.isConnected && dialog._returnFocus.getClientRects().length)
      dialog._returnFocus.focus();
  }));

  function summary(rule) {
    const operators = { gt: ["> (above)", ">（高于）"], gte: ["≥ (at or above)", "≥（不低于）"],
      lt: ["< (below)", "<（低于）"], lte: ["≤ (at or below)", "≤（不高于）"] };
    const op = operators[rule.operator][zh() ? 1 : 0];
    return words(rule.pair.slice(0,3) + "/" + rule.pair.slice(3) + ": " + rule.consecutive +
      " consecutive finalized 4H closes " + op + " " + rule.threshold + " " +
      rule.pair.slice(3) + " per " + rule.pair.slice(0,3) + ". Expires " + rule.expires_at + ".",
      rule.pair.slice(0,3) + "/" + rule.pair.slice(3) + "：连续 " + rule.consecutive +
      " 次最终4小时收盘价 " + op + " " + rule.threshold + " " + rule.pair.slice(3) +
      " / " + rule.pair.slice(0,3) + "。到期：" + rule.expires_at + "。");
  }
  function renderReview() {
    if (!pendingRule) return;
    q("#fxr-rule-summary").textContent = summary(pendingRule);
    q("#fxr-rule-json").textContent = JSON.stringify(pendingRule, null, 2);
  }
  function showReview() {
    q("#fxr-rule-form").hidden = true;
    q("#fxr-rule-review").hidden = false;
    renderReview();
    q("#fxr-edit-rule").focus();
  }
  function startRule(pair, opener, existingIndex) {
    if (!rows.has(pair)) return;
    const form = q("#fxr-rule-form");
    form.reset();
    q("#fxr-rule-error").textContent = "";
    q("#fxr-rule-pair").value = pair;
    q("#fxr-rule-pair-label").textContent = pair.slice(0,3) + "/" + pair.slice(3) + " · " +
      pair.slice(3) + words(" per ", " / ") + pair.slice(0,3);
    form.elements.expires_at.value = new Date(Date.now() + 7 * 86400000).toISOString().slice(0,16);
    editIndex = Number.isInteger(existingIndex) ? existingIndex : -1;
    pendingRule = editIndex >= 0 ? { ...prepared[editIndex] } : null;
    form.hidden = false;
    q("#fxr-rule-review").hidden = true;
    if (pendingRule) {
      for (const field of ["operator", "threshold", "consecutive"]) form.elements[field].value = pendingRule[field];
      form.elements.expires_at.value = pendingRule.expires_at.slice(0,16);
    }
    openDialog(q("#fxr-watch-dialog"), opener);
    if (pendingRule) showReview(); else form.elements.threshold.focus();
  }
  function renderPrepared() {
    const list = q("#fxr-prepared-list");
    list.replaceChildren();
    q("#fxr-prepared-section").hidden = prepared.length === 0;
    prepared.forEach((rule, index) => {
      const card = el("article", undefined, "fxr-prepared-item");
      card.append(el("h3", rule.pair.slice(0,3) + "/" + rule.pair.slice(3)),
        el("p", summary(rule)), el("p", words("Prepared in this tab · Not saved · Not active", "仅在此标签页准备 · 未保存 · 未启用"), "fxr-muted"));
      const actions = el("div", undefined, "fxr-actions");
      const review = el("button", words("Review condition", "核对条件"), "gbtn");
      review.type = "button";
      review.addEventListener("click", () => startRule(rule.pair, review, index));
      const remove = el("button", words("Remove draft", "移除草稿"), "gbtn gbtn-quiet");
      remove.type = "button";
      remove.addEventListener("click", () => { prepared.splice(index, 1); renderPrepared(); q("#fxr-nav-my_watches").focus(); });
      actions.append(review, remove); card.append(actions); list.append(card);
    });
  }
  function renderComparison() {
    const body = q("#fxr-compare-body");
    body.replaceChildren();
    selected.forEach(pair => {
      const row = rows.get(pair), section = el("section");
      section.append(el("h3", row.base_ccy + "/" + row.quote_ccy),
        el("p", safePrice(row), "fxr-number"),
        el("p", safeChange(row) + " · " + period(row)),
        el("p", words("Observation date: ", "观测日期：") + (row.asof || "—"), "fxr-muted"),
        el("p", currentLean(row)),
        el("p", words("Quote unit: ", "报价单位：") + row.quote_ccy + words(" per ", " / ") + row.base_ccy, "fxr-caption"));
      body.append(section);
    });
  }
  function localize() {
    all("[data-en][data-zh]").forEach(node => { node.textContent = node.dataset[zh() ? "zh" : "en"]; });
    all("[data-placeholder-en]").forEach(node => { node.placeholder = node.dataset[zh() ? "placeholderZh" : "placeholderEn"]; });
    all("[data-aria-en]").forEach(node => { node.setAttribute("aria-label", node.dataset[zh() ? "ariaZh" : "ariaEn"]); });
    filterPairs(false); renderPrepared(); renderReview(); renderComparison();
  }

  root.addEventListener("click", event => {
    const button = event.target.closest("button");
    if (!button || !root.contains(button)) return;
    if (button.hasAttribute("data-fxr-destination")) navigate(button.dataset.fxrDestination);
    else if (button.hasAttribute("data-fxr-go")) navigate(button.dataset.fxrGo);
    else if (button.hasAttribute("data-fxr-open-pair")) navigate("pair", button.dataset.fxrOpenPair, "outlook", true);
    else if (button.hasAttribute("data-fxr-pair-tab")) navigate("pair", state.pair, button.dataset.fxrPairTab);
    else if (button.hasAttribute("data-fxr-jump-tab")) navigate("pair", state.pair, button.dataset.fxrJumpTab);
    else if (button.hasAttribute("data-fxr-source")) openDialog(q("#fxr-source-dialog"), button);
    else if (button.hasAttribute("data-fxr-prepare")) startRule(button.dataset.fxrPrepare, button);
    else if (button.hasAttribute("data-fxr-close")) button.closest("dialog").close();
    else if (button.hasAttribute("data-fxr-study")) {
      const study = document.getElementById("forex-full-study");
      if (!study) return;
      study.open = true;
      const target = document.getElementById("fx-study-" + button.dataset.fxrStudy) || study.querySelector("summary");
      target.scrollIntoView({block:"start", behavior:"auto"});
      target.focus({preventScroll:true});
      window.dispatchEvent(new Event("resize"));
    }
  });
  root.addEventListener("keydown", event => {
    const button = event.target.closest('[role="tab"]');
    if (!button) return;
    const siblings = Array.from(button.parentElement.querySelectorAll('[role="tab"]'));
    let index = siblings.indexOf(button);
    if (event.key === "ArrowRight") index = (index + 1) % siblings.length;
    else if (event.key === "ArrowLeft") index = (index + siblings.length - 1) % siblings.length;
    else if (event.key === "Home") index = 0;
    else if (event.key === "End") index = siblings.length - 1;
    else return;
    event.preventDefault(); siblings[index].click(); siblings[index].focus();
  });
  q("#fxr-back").addEventListener("click", () => {
    const pair = state.pair, from = state.from;
    navigate(from);
    const button = q('[data-fxr-view="' + from + '"] [data-fxr-open-pair="' + pair + '"]');
    if (button) button.focus(); else q("#fxr-nav-" + from).focus();
  });
  q("#fxr-search").addEventListener("input", () => filterPairs(true));
  q("#fxr-filter").addEventListener("change", () => filterPairs(true));
  q("#fxr-reset-filters").addEventListener("click", () => {
    q("#fxr-search").value = ""; q("#fxr-filter").value = "all"; filterPairs(true); q("#fxr-search").focus();
  });
  all("[data-fxr-compare-pair]").forEach(input => input.addEventListener("change", () => {
    const pair = input.dataset.fxrComparePair;
    if (input.checked && selected.size < 2) selected.add(pair);
    else if (input.checked) { input.checked = false; q("#fxr-results").textContent = words("Select up to two pairs.", "最多选择两个货币对。"); }
    else selected.delete(pair);
    q("#fxr-compare-count").textContent = String(selected.size);
    q("#fxr-compare").disabled = selected.size !== 2;
  }));
  q("#fxr-compare").addEventListener("click", event => {
    if (selected.size !== 2) return;
    renderComparison(); openDialog(q("#fxr-compare-dialog"), event.currentTarget);
  });
  q("#fxr-rule-form").addEventListener("submit", event => {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.reportValidity()) return;
    const pair = form.elements.pair.value, threshold = Number(form.elements.threshold.value),
      consecutive = Number(form.elements.consecutive.value), expires = new Date(form.elements.expires_at.value + "Z"),
      operator = form.elements.operator.value;
    if (!rows.has(pair) || !Number.isFinite(threshold) || threshold <= 0 ||
        !Number.isInteger(consecutive) || consecutive < 1 || consecutive > 10 ||
        !["gt","gte","lt","lte"].includes(operator) || !Number.isFinite(expires.valueOf()) || expires <= new Date()) {
      q("#fxr-rule-error").textContent = words("Enter a positive price, 1–10 closes and a future expiry in UTC.", "请输入正价格、1–10次收盘，以及未来的UTC到期时间。");
      return;
    }
    pendingRule = { condition_id: null, revision: null, kind: "price_close", pair, feed: null,
      interval: "4H", calendar: "fx-utc-4h/v1", operator, threshold, consecutive,
      expires_at: expires.toISOString(), quote_basis: "literal", state: "prepared",
      saved: false, active: false, snapshot_id: view.current_read.snapshot_id };
    showReview();
  });
  q("#fxr-edit-rule").addEventListener("click", () => {
    q("#fxr-rule-review").hidden = true; q("#fxr-rule-form").hidden = false;
    q("#fxr-rule-form").elements.threshold.focus();
  });
  q("#fxr-keep-rule").addEventListener("click", () => {
    if (!pendingRule) return;
    if (editIndex >= 0) prepared[editIndex] = { ...pendingRule }; else prepared.push({ ...pendingRule });
    pendingRule = null; editIndex = -1;
    q("#fxr-watch-dialog").close(); renderPrepared(); navigate("my_watches");
    q("#fxr-nav-my_watches").focus();
  });
  window.addEventListener("hashchange", () => { readRoute(); renderRoute(false); });
  new MutationObserver(localize).observe(document.documentElement, { attributes:true, attributeFilter:["data-lang"] });
  readRoute(); renderRoute(false); localize();
})();
