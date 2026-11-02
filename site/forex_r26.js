/* R26 workspace controller. Market views read the embedded owner projection.
   Account condition writes use the existing alerts owner through ForexWatchClient.
   Tab drafts stay local; this controller never activates watches or sends alerts. */
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
  const watchClient = window.ForexWatchClient || null, pendingOperations = new Map();
  let accountView = { status: "checking", rows: [] }, accountRead = 0, priorAccount = null;
  let editingSaved = null, editorVersion = 0;
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
    q("#fxr-rule-status").textContent = editingSaved ? words("Review changes · Not saved yet", "核对更改 · 尚未保存") : words("Prepared · not active", "已准备 · 未启用");
    q("#fxr-rule-persistence").textContent = editingSaved ? words("Saved revision ", "已保存版本 ") + editingSaved.condition.revision : words("Not created", "未创建");
    q("#fxr-rule-note").textContent = editingSaved ? words("Your saved condition stays inactive. Changes take effect only when the account service confirms the new revision.", "已保存条件保持未启用。账户服务确认新版本后，更改才会生效。") : words("No notification will be sent. Keep this draft in the tab, then choose Save to account in My watches if you want to retain it.", "不会发送通知。可先将草稿保留在当前标签页，再到“我的关注”选择保存到账户。 ");
    q("#fxr-keep-rule").textContent = editingSaved ? words("Save changes", "保存更改") : words("Keep prepared in this tab", "在此标签页保留已准备条件");
    q("#fxr-keep-rule").disabled = !!editingSaved && (pendingOperations.has(editingSaved.id) || !q("#fxr-reload-saved").hidden);
  }
  function showReview() {
    q("#fxr-rule-form").hidden = true;
    q("#fxr-rule-review").hidden = false;
    renderReview();
    q("#fxr-edit-rule").focus();
  }
  function startRule(pair, opener, existingIndex, savedRow) {
    if ((!rows.has(pair) && !savedRow) || (savedRow && pendingOperations.has(savedRow.id))) return;
    editorVersion++; editingSaved = savedRow || null;
    q("#fxr-rule-save-message").textContent = "";
    q("#fxr-reload-saved").hidden = true;
    const form = q("#fxr-rule-form");
    form.reset();
    q("#fxr-rule-error").textContent = "";
    q("#fxr-rule-pair").value = pair;
    q("#fxr-rule-pair-label").textContent = pair.slice(0,3) + "/" + pair.slice(3) + " · " +
      pair.slice(3) + words(" per ", " / ") + pair.slice(0,3);
    form.elements.expires_at.value = new Date(Date.now() + 7 * 86400000).toISOString().slice(0,16);
    editIndex = Number.isInteger(existingIndex) ? existingIndex : -1;
    pendingRule = editingSaved ? { ...editingSaved.condition } : editIndex >= 0 ? { ...prepared[editIndex] } : null;
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
      const held = Array.from(pendingOperations.values()).some(operation => operation.draft === rule);
      review.disabled = remove.disabled = held;
      const auth = watchClient && watchClient.authState();
      const save = el("button", auth && auth.status === "signed_out" ? words("Sign in to save", "登录以保存") : words("Save to account", "保存到账户"), "gbtn gbtn-cta");
      save.type = "button";
      save.disabled = held || !auth || !["ready", "signed_out"].includes(auth.status);
      save.addEventListener("click", () => { const request = makeRequest(rule); if (request) beginOperation("save", request, rule); });
      actions.append(review, save, remove); card.append(actions); list.append(card);
    });
  }
  function accountMessage(status) {
    return ({
      signed_out: ["Sign in to save a condition to your account.", "登录后可将条件保存到账户。"],
      checking: ["Checking your account…", "正在检查账户…"],
      unavailable: ["Account watches are unavailable. Retry to read their current state.", "账户关注暂不可用。请重试以读取当前状态。"],
      invalid: ["Check the condition and choose a future expiry in UTC.", "请检查条件，并选择未来的UTC到期时间。"],
      limit: ["Your account has reached its alert limit. Remove an existing condition before saving another.", "账户已达到提醒数量上限。请先移除已有条件。"],
      conflict: ["This condition changed in another session. Reload the saved version before editing it.", "此条件已在另一会话中更改。请先重新载入已保存版本。"],
      not_found: ["This condition is no longer available in your account.", "此条件已不在您的账户中。"],
      unconfirmed: ["The result is not confirmed. Check its status before attempting another write.", "结果尚未确认。再次写入前，请先检查状态。"],
      session_changed: ["Your account session changed. Read your watches again.", "账户会话已更改。请重新读取关注。"]
    }[status] || ["The account service could not confirm this action.", "账户服务未能确认此操作。"]);
  }
  function messageFor(status) { const text = accountMessage(status); return words(text[0], text[1]); }
  function announceAccount(text) { q("#fxr-account-message").textContent = text; q("#fxr-account-message").hidden = !text; }
  function renderAccount() {
    const auth = watchClient ? watchClient.authState() : { status: "unavailable" };
    // An inventory read cannot resolve a mutation that may still complete.
    const status = accountView.status === "ready" && pendingOperations.size ?
      "unconfirmed" : accountView.status;
    const ready = accountView.status === "ready";
    const confirmedInventory = status === "ready";
    q("#fxr-account-title").dataset.accountStatus = status;
    q("#fxr-account-title").textContent = confirmedInventory ?
      (accountView.rows.length ? words("Saved conditions", "已保存条件") : words("No saved Forex conditions", "没有已保存的外汇条件")) :
      status === "updating" ? words("Updating saved conditions…", "正在更新已保存条件…") :
      status === "unconfirmed" ? words("Change awaiting confirmation", "更改等待确认") :
      status === "loading" ? words("Loading your watches…", "正在载入关注…") :
      status === "signed_out" ? words("Save conditions to your account", "将条件保存到账户") :
      status === "checking" ? words("Checking your account…", "正在检查账户…") :
      words("Account watch status unavailable", "账户关注状态不可用");
    q("#fxr-account-description").textContent = confirmedInventory ?
      words("Saved conditions remain inactive. Finalized 4H monitoring and notifications are not available yet.", "已保存条件仍未启用。目前尚不支持最终4小时监测与通知。") :
      ["loading", "updating"].includes(status) ? words("Waiting for the account service to return your records.", "正在等待账户服务返回记录。") : messageFor(status);
    q("#fxr-account-signin").hidden = auth.status !== "signed_out";
    q("#fxr-account-refresh").hidden = auth.status !== "ready";
    q("#fxr-account-refresh").disabled = status === "loading";
    const list = q("#fxr-saved-list"); list.replaceChildren();
    q("#fxr-saved-section").hidden = !ready || !accountView.rows.length;
    if (ready) accountView.rows.forEach(row => {
      const card = el("article", undefined, "fxr-prepared-item");
      card.dataset.fxrSavedId = row.id;
      const expired = new Date(row.condition.expires_at) <= new Date();
      card.append(el("h3", row.symbol.slice(0,3) + "/" + row.symbol.slice(3)),
        el("p", summary(row.condition)),
        el("p", words("Saved inactive · Revision ", "已保存，未启用 · 版本 ") + row.condition.revision +
          (expired ? words(" · Expired", " · 已到期") : ""), "fxr-muted"));
      const actions = el("div", undefined, "fxr-actions");
      const edit = el("button", words("Edit saved condition", "编辑已保存条件"), "gbtn");
      edit.type = "button"; edit.disabled = pendingOperations.has(row.id);
      edit.addEventListener("click", () => startRule(row.symbol, edit, undefined, row));
      const remove = el("button", words("Delete condition", "删除条件"), "gbtn gbtn-quiet");
      remove.type = "button"; remove.disabled = pendingOperations.has(row.id);
      remove.addEventListener("click", () => {
        const request = makeRequest(row.condition, row.id, row.condition.revision);
        if (request) beginOperation("remove", request);
      });
      actions.append(edit, remove); card.append(actions); list.append(card);
    });
    renderPending();
  }
  async function loadAccount() {
    if (!watchClient) { accountView = { status: "unavailable", rows: [] }; renderAccount(); return; }
    const auth = watchClient.authState(), serial = ++accountRead;
    if (auth.status !== "ready") { accountView = { status: auth.status, rows: [] }; renderAccount(); return; }
    accountView = { status: "loading", rows: [] }; renderAccount();
    const result = await watchClient.list();
    if (serial !== accountRead || auth.epoch !== watchClient.authState().epoch) return;
    accountView = result.status === "ready" ? result : { status: result.status, rows: [] };
    renderAccount();
  }
  function makeRequest(rule, id, revision) {
    const auth = watchClient && watchClient.authState();
    if (!auth || auth.status !== "ready") {
      if (auth && auth.status === "signed_out" && window.MDXAuth) window.MDXAuth.open("signin");
      else announceAccount(messageFor(auth ? auth.status : "unavailable"));
      return null;
    }
    const identity = id || watchClient.newId();
    if (!identity) { announceAccount(words("A secure condition identity could not be created.", "无法创建安全的条件标识。")); return null; }
    return { id: identity, expectedRevision: revision || 0, rule: { ...rule },
      userId: auth.userId, accountEpoch: auth.epoch };
  }
  function renderPending() {
    const list = q("#fxr-pending-list"); list.replaceChildren();
    q("#fxr-pending-section").hidden = pendingOperations.size === 0;
    pendingOperations.forEach(operation => {
      const card = el("article", undefined, "fxr-prepared-item");
      card.dataset.fxrPendingId = operation.request.id;
      const uncertain = operation.status === "unconfirmed";
      card.append(el("h3", operation.request.rule.pair),
        el("p", summary(operation.request.rule)),
        el("p", uncertain ? messageFor("unconfirmed") :
          operation.kind === "save" ? words("Saving… Not yet confirmed.", "正在保存…尚未确认。") :
          words("Deleting… Not yet confirmed.", "正在删除…尚未确认。"), "fxr-muted"));
      if (uncertain) {
        const check = el("button", words("Check status", "检查状态"), "gbtn");
        check.type = "button";
        check.addEventListener("click", async () => {
          check.disabled = true;
          const result = await (operation.kind === "save" ? watchClient.reconcileSave(operation.request) : watchClient.reconcileRemove(operation.request));
          finishOperation(operation, result);
        });
        card.append(check);
      }
      list.append(card);
    });
  }
  async function beginOperation(kind, request, draft) {
    if (pendingOperations.has(request.id)) return;
    const operation = { kind, request, draft, editor: editorVersion, status: kind === "save" ? "saving" : "deleting" };
    pendingOperations.set(request.id, operation);
    accountRead++; accountView = { status: "updating", rows: [] };
    announceAccount(""); renderAccount(); renderPrepared(); renderReview();
    const result = await watchClient[kind](request);
    finishOperation(operation, result);
  }
  function finishOperation(operation, result) {
    const auth = watchClient.authState();
    if (auth.epoch !== operation.request.accountEpoch || auth.userId !== operation.request.userId ||
        pendingOperations.get(operation.request.id) !== operation) return;
    const inEditor = operation.editor === editorVersion && editingSaved && editingSaved.id === operation.request.id;
    if (result.status === "unconfirmed" || result.status === "unavailable") {
      // A failed reconciliation read supplies no new write verdict.
      if (result.status === "unconfirmed" || operation.status === "unconfirmed") {
        operation.status = "unconfirmed"; accountView = { status: "unconfirmed", rows: [] }; renderAccount(); renderPrepared(); renderReview();
        announceAccount(messageFor("unconfirmed"));
        if (inEditor) q("#fxr-rule-save-message").textContent = words("Save not confirmed. Check status in My watches.", "保存尚未确认。请在“我的关注”中检查状态。");
        return;
      }
    }
    pendingOperations.delete(operation.request.id);
    if (result.status === "saved" || result.status === "deleted") {
      if (operation.draft) {
        const index = prepared.indexOf(operation.draft); if (index >= 0) prepared.splice(index, 1);
      }
      announceAccount(result.status === "saved" ? words("Saved inactive. No alerts will be sent.", "已保存，未启用。不会发送提醒。") : words("Condition deleted.", "条件已删除。"));
      if (inEditor && q("#fxr-watch-dialog").open) {
        q("#fxr-watch-dialog").close(); editingSaved = null; pendingRule = null;
        navigate("my_watches"); q("#fxr-nav-my_watches").focus();
      }
      loadAccount();
    } else {
      announceAccount(messageFor(result.status));
      if (inEditor) {
        q("#fxr-rule-save-message").textContent = messageFor(result.status);
        q("#fxr-reload-saved").hidden = result.status !== "conflict";
      }
      loadAccount();
    }
    renderAccount(); renderPrepared(); renderReview();
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
    filterPairs(false); renderPrepared(); renderReview(); renderComparison(); renderAccount();
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
    if ((!rows.has(pair) && (!editingSaved || editingSaved.symbol !== pair)) || !Number.isFinite(threshold) || threshold <= 0 ||
        !Number.isInteger(consecutive) || consecutive < 1 || consecutive > 10 ||
        !["gt","gte","lt","lte"].includes(operator) || !Number.isFinite(expires.valueOf()) || expires <= new Date()) {
      q("#fxr-rule-error").textContent = words("Enter a positive price, 1–10 closes and a future expiry in UTC.", "请输入正价格、1–10次收盘，以及未来的UTC到期时间。");
      return;
    }
    pendingRule = { condition_id: editingSaved ? editingSaved.id : null, revision: editingSaved ? editingSaved.condition.revision : null, kind: "price_close", pair, feed: null,
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
    if (editingSaved) {
      const request = makeRequest(pendingRule, editingSaved.id, editingSaved.condition.revision);
      if (request) beginOperation("save", request);
      return;
    }
    if (editIndex >= 0) prepared[editIndex] = { ...pendingRule }; else prepared.push({ ...pendingRule });
    pendingRule = null; editIndex = -1;
    q("#fxr-watch-dialog").close(); renderPrepared(); navigate("my_watches");
    q("#fxr-nav-my_watches").focus();
  });
  q("#fxr-account-signin").addEventListener("click", () => { if (window.MDXAuth) window.MDXAuth.open("signin"); });
  q("#fxr-account-refresh").addEventListener("click", loadAccount);
  q("#fxr-reload-saved").addEventListener("click", async () => {
    if (!editingSaved || !watchClient) return;
    const target = editingSaved.id, version = editorVersion;
    q("#fxr-reload-saved").disabled = true;
    const result = await watchClient.get(target);
    if (version !== editorVersion) return;
    q("#fxr-reload-saved").disabled = false;
    if (result.status === "ready" && result.row) {
      editingSaved = result.row; pendingRule = { ...result.row.condition };
      q("#fxr-rule-pair").value = pendingRule.pair;
      q("#fxr-rule-pair-label").textContent = pendingRule.pair.slice(0,3) + "/" + pendingRule.pair.slice(3) + " · " + pendingRule.pair.slice(3) + words(" per ", " / ") + pendingRule.pair.slice(0,3);
      for (const field of ["operator", "threshold", "consecutive"]) q("#fxr-rule-form").elements[field].value = pendingRule[field];
      q("#fxr-rule-form").elements.expires_at.value = pendingRule.expires_at.slice(0,16);
      q("#fxr-reload-saved").hidden = true; q("#fxr-rule-save-message").textContent = words("Loaded the saved version. Review it before making changes.", "已载入保存版本。更改前请先核对。");
      renderReview();
    } else q("#fxr-rule-save-message").textContent = messageFor(result.status === "ready" ? "not_found" : result.status);
  });
  if (watchClient) watchClient.subscribeAuth(auth => {
    accountRead++;
    if (priorAccount && priorAccount.epoch !== auth.epoch) {
      pendingOperations.clear();
      if (priorAccount.userId) {
        prepared.length = 0; pendingRule = null; editingSaved = null; editorVersion++;
        q("#fxr-rule-form").reset(); q("#fxr-rule-pair").value = "";
        ["#fxr-rule-summary", "#fxr-rule-json", "#fxr-rule-save-message", "#fxr-rule-pair-label"].forEach(selector => { q(selector).textContent = ""; });
        if (q("#fxr-watch-dialog").open) q("#fxr-watch-dialog").close();
      }
      announceAccount("");
    }
    priorAccount = auth; accountView = { status: auth.status, rows: [] };
    renderPrepared(); renderReview(); loadAccount();
  });
  window.addEventListener("hashchange", () => { readRoute(); renderRoute(false); });
  new MutationObserver(localize).observe(document.documentElement, { attributes:true, attributeFilter:["data-lang"] });
  readRoute(); renderRoute(false); localize();
})();
