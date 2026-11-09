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
  var renderedHistory = null, readingSuspended = false, pendingCaseReturn = null;
  function zh() { return document.documentElement.dataset.lang === "zh"; }
  function t(en, cn) { return zh() ? cn : en; }
  function field(value, name) { return value[name + (zh() ? "_zh" : "_en")] || ""; }
  function money(value) { return typeof value === "number" && isFinite(value) ? "$" + value.toLocaleString("en-US", { maximumFractionDigits: value < 1000 ? 2 : 0 }) : t("Unavailable", "暂无"); }
  function assetMoney(value) {
    if (typeof value !== "number" || !isFinite(value) || value <= 0) return t("Unavailable", "暂无");
    if (value < 0.00000001) return "<$0.00000001";
    if (value < 0.01) return "$" + value.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 8, useGrouping: false });
    return money(value);
  }
  function assetTitle(asset) {
    var name = typeof asset.name === "string" ? asset.name : "";
    return name.trim() && name.trim().toLowerCase() !== asset.symbol.trim().toLowerCase() ?
      name + " · " + asset.symbol : asset.symbol;
  }
  function pct(value) { return typeof value === "number" && isFinite(value) ? (value > 0 ? "+" : "") + value.toFixed(1) + "%" : t("Unavailable", "暂无"); }
  function node(tag, text, className) {
    var element = document.createElement(tag);
    if (text !== undefined && text !== null) element.textContent = String(text);
    if (className) element.className = className;
    return element;
  }
  function paragraph(text) { var element = node("p", text); body.appendChild(element); return element; }
  function heading(text) { body.appendChild(node("h3", text)); }
  function button(text, action, parent) { var element = node("button", text, "cri-btn"); element.type = "button"; element.addEventListener("click", action); (parent || body).appendChild(element); return element; }
  function definition(rows, parent) {
    var list = node("dl");
    rows.forEach(function (row) { var item = node("div"); item.append(node("dt", row[0]), node("dd", row[1] == null ? t("Unavailable", "暂无") : row[1])); list.appendChild(item); });
    (parent || body).appendChild(list);
    return list;
  }
  function link(text, url) { var a = node("a", text); a.href = url; var p = node("p"); p.appendChild(a); body.appendChild(p); }
  function state() {
    var parts = location.hash.slice(1).split("?"), view = views.indexOf(parts[0]) >= 0 ? parts[0] : root.dataset.defaultView;
    return { view: view, params: new URLSearchParams(parts.slice(1).join("?")) };
  }
  function address(view, params) { return "#" + view + (params.toString() ? "?" + params.toString() : ""); }
  function historySignature() {
    try { return JSON.stringify(history.state); } catch (error) { return null; }
  }
  function drawerFocus(key) {
    if (key === "close") return document.getElementById("cri-dialog-close");
    if (key === "heading") return title;
    var matches = Array.from(dialog.querySelectorAll("[data-drawer-focus]")).filter(function (element) {
      return element.dataset.drawerFocus === key;
    });
    return matches.length === 1 ? matches[0] : null;
  }
  function readingScope() {
    var panel = body.dataset.panel;
    if (panel && panel.indexOf("scenario:") === 0) {
      if (state().params.get("panel") !== panel) return null;
      var current = activeScenario(panel.slice(9));
      if (!current || !savedText(current.revision) || !savedDay(current.as_of) ||
          current.horizon_days !== Number(horizon())) return null;
      return { panel: panel, revision: current.revision, horizon: current.horizon_days, cutoff: current.as_of };
    }
    if (!body.dataset.savedRevision && body.dataset.savedList !== "true") return null;
    return { panel: body.dataset.panel, revision: body.dataset.savedRevision || null,
      horizon: body.dataset.savedHorizon ? Number(body.dataset.savedHorizon) : null,
      cutoff: body.dataset.savedCutoff || null };
  }
  function captureDrawerReading(focusOverride) {
    // Fresh DOM and history ownership are separate from reading eligibility.
    var signature = historySignature();
    if (!dialog.open || root.dataset.renderedAddress !== location.href ||
        renderedHistory === null || signature !== renderedHistory ||
        state().params.get("panel") !== body.dataset.panel) return { owned: false };
    var capture = { owned: true, address: location.href, language: zh(), subtree: body.firstChild,
      signature: signature, length: history.length, reading: null };
    var scope = readingScope();
    if (!scope) return capture;
    var active = document.activeElement, keyed = active && active.closest("[data-drawer-focus]");
    var focus = active === title ? "heading" : active && active.id === "cri-dialog-close" ? "close" :
      keyed && dialog.contains(keyed) ? keyed.dataset.drawerFocus : null;
    if (typeof focusOverride === "string" && drawerFocus(focusOverride)) focus = focusOverride;
    capture.reading = Object.assign({}, scope, {
      disclosures: Array.from(body.querySelectorAll("details[data-drawer-disclosure]")).filter(function (element) {
        return element.open;
      }).map(function (element) { return element.dataset.drawerDisclosure; }),
      focus: focus, scroll: Math.max(0, dialog.scrollTop)
    });
    return capture;
  }
  function ownsDrawerCapture(capture, signature) {
    return capture.owned && dialog.open && location.href === capture.address && zh() === capture.language &&
      body.firstChild === capture.subtree && history.length === capture.length &&
      historySignature() === (signature === undefined ? capture.signature : signature);
  }
  function persistDrawerReading(capture) {
    if (!capture.reading || !ownsDrawerCapture(capture)) return false;
    var metadata = history.state && typeof history.state === "object" && !Array.isArray(history.state) ?
      Object.assign({}, history.state) : {};
    metadata.reading = capture.reading;
    var intended = JSON.stringify(metadata);
    if (intended === capture.signature) return true;
    try { history.replaceState(metadata, "", capture.address); }
    catch (error) { /* Optional reading state must not break the visible reader. */ }
    // A callback may replace this entry without changing its URL or focus.
    if (ownsDrawerCapture(capture, intended)) { renderedHistory = intended; return true; }
    return ownsDrawerCapture(capture); // An unchanged, failed optional write remains usable.
  }
  function rememberDrawer(focusOverride) {
    if (!readingSuspended) persistDrawerReading(captureDrawerReading(focusOverride));
  }
  function matchingDrawerReading(reading) {
    var scope = readingScope();
    if (!scope || !reading || typeof reading !== "object" || reading.panel !== scope.panel ||
        reading.revision !== scope.revision || reading.horizon !== scope.horizon ||
        reading.cutoff !== scope.cutoff || !Array.isArray(reading.disclosures) ||
        typeof reading.scroll !== "number" || !isFinite(reading.scroll) || reading.scroll < 0) return null;
    return reading;
  }
  function drawerReading() { return matchingDrawerReading(history.state && history.state.reading); }
  function restoreDrawerReading(reading) {
    body.querySelectorAll("details[data-drawer-disclosure]").forEach(function (element) {
      element.open = reading.disclosures.indexOf(element.dataset.drawerDisclosure) >= 0;
    });
    dialog.scrollTop = reading.scroll;
  }
  function usableDrawerFocus(element) {
    return element && element.isConnected && !element.matches(":disabled") && element.getClientRects().length &&
      !element.closest("[hidden],[inert]") && getComputedStyle(element).visibility !== "hidden" ? element : null;
  }
  function savedIdentity(s) {
    dialog.classList.add("cri-dialog-saved");
    body.dataset.savedRevision = s.revision;
    body.dataset.savedHorizon = String(s.horizon_days);
    body.dataset.savedCutoff = s.as_of;
  }
  function hasDrawerParent(panel, expectedHorizon) {
    var metadata = history.state, current = state();
    if (!metadata || metadata.r4 !== true || metadata.drawer !== true ||
        !Number.isInteger(metadata.depth) || metadata.depth < 1 ||
        typeof metadata.previous !== "string" || metadata.previous.charAt(0) !== "#") return false;
    var parts = metadata.previous.slice(1).split("?"), params = new URLSearchParams(parts.slice(1).join("?"));
    return views.indexOf(parts[0]) >= 0 && parts[0] === current.view && params.get("panel") === panel &&
      (expectedHorizon === undefined || (params.get("h") === "30" ? "30" : "7") === String(expectedHorizon));
  }
  function drawerParent(label, action, context) {
    var parent = node("button", label, "cri-dialog-parent");
    parent.type = "button"; parent.dataset.drawerFocus = "parent";
    parent.addEventListener("click", action);
    kicker.replaceChildren(parent, node("span", context === undefined ? t("Saved snapshot", "已存快照") : context, "cri-saved-kicker"));
  }
  function returnToSavedCase(revision) {
    if (pendingCaseReturn && pendingCaseReturn.childAddress === location.href) return;
    var addressBefore = location.href, languageBefore = zh(), subtree = body.firstChild, focusBefore = document.activeElement;
    var collection = stored();
    if (location.href !== addressBefore || zh() !== languageBefore || body.firstChild !== subtree || document.activeElement !== focusBefore) return;
    var saved = collection.ready ? savedVersion(collection, revision) : null;
    if (!collection.ready || !saved) { apply({ collection: collection }); return; }
    if (hasDrawerParent("saved-item:" + revision)) {
      rememberDrawer();
      pendingCaseReturn = { panel: "saved-item:" + revision, revision: revision,
        horizon: saved.horizon_days, cutoff: saved.as_of, childAddress: location.href,
        parentAddress: location.href.split("#")[0] + history.state.previous };
      history.back();
    }
    else update(null, { panel: "saved-item:" + revision, h: String(saved.horizon_days) }, true);
  }
  function returnToCurrentCase(id, caseHorizon) {
    if (state().params.get("panel") !== "memory:" + id || horizon() !== caseHorizon ||
        pendingCaseReturn && pendingCaseReturn.childAddress === location.href) return;
    var current = activeScenario(id), panel = "scenario:" + id;
    if (!current) { apply(); return; }
    if (hasDrawerParent(panel, caseHorizon)) {
      rememberDrawer();
      pendingCaseReturn = { panel: panel, revision: current.revision, horizon: current.horizon_days,
        cutoff: current.as_of, childAddress: location.href,
        parentAddress: location.href.split("#")[0] + history.state.previous };
      history.back();
    } else update(null, { panel: panel, h: caseHorizon }, true);
  }
  function returnToSavedList() {
    if (hasDrawerParent("saved")) { rememberDrawer(); history.back(); }
    else update(null, { panel: "saved" }, true);
  }
  function visibleInView(element, view) {
    if (!element || !element.isConnected || !root.contains(element) ||
        !element.getClientRects().length || element.closest("[hidden],[inert]") ||
        getComputedStyle(element).visibility === "hidden") return false;
    var section = element.closest("[data-view]");
    return !section || section.dataset.view === view;
  }
  function viewHeading(view) {
    return root.querySelector('[data-view="' + view + '"] h2') || root.querySelector("h1");
  }
  function update(view, changes, replace) {
    pendingCaseReturn = null; rememberDrawer();
    var current = state(), params = current.params, oldPanel = params.get("panel");
    Object.keys(changes || {}).forEach(function (key) { if (changes[key] == null || changes[key] === "") params.delete(key); else params.set(key, changes[key]); });
    var metadata = replace && params.has("panel") && history.state && history.state.drawer ? Object.assign({}, history.state) : { r4: true };
    if (params.get("panel") !== oldPanel) delete metadata.reading;
    history[replace ? "replaceState" : "pushState"](metadata, "", address(view || current.view, params));
    apply();
  }
  function horizon() { return state().params.get("h") === "30" ? "30" : "7"; }
  function activeScenario(id) { return (data.scenarios[horizon()] || []).find(function (s) { return s.id === id; }); }
  function open(key, trigger, scenarioHorizon, returnFocus) {
    pendingCaseReturn = null; rememberDrawer(returnFocus);
    var s = state(), addressBefore = location.href, languageBefore = zh(), subtree = body.firstChild, focusBefore = document.activeElement;
    var savedKey = /^(saved-item|memory-saved):/.test(key), retained;
    if (savedKey) {
      var revision = key.slice(key.indexOf(":") + 1), collection = stored();
      if (location.href !== addressBefore || zh() !== languageBefore || body.firstChild !== subtree || document.activeElement !== focusBefore) return;
      retained = collection.ready ? savedVersion(collection, revision) : null;
      scenarioHorizon = retained ? String(retained.horizon_days) : null;
      // Repair a legacy parent in place without changing its outer ancestry.
      if (retained && key.indexOf("memory-saved:") === 0 &&
          s.params.get("panel") === "saved-item:" + revision && s.params.get("h") !== scenarioHorizon) {
        s.params.set("h", scenarioHorizon);
        history.replaceState(history.state, "", address(s.view, s.params));
        rememberDrawer(returnFocus);
      }
    }
    if (trigger && !dialog.contains(trigger)) lastTrigger = trigger;
    var previous = location.hash, alreadyOpen = s.params.has("panel");
    s.params.set("panel", key);
    if (scenarioHorizon) s.params.set("h", scenarioHorizon);
    var managed = history.state && history.state.r4 && history.state.drawer && Number.isInteger(history.state.depth);
    var depth = managed ? history.state.depth + 1 : 1;
    var detachedOrigin = managed ? history.state.detachedOrigin === true : alreadyOpen;
    history.pushState({ r4: true, drawer: true, previous: previous, depth: depth, detachedOrigin: detachedOrigin }, "", address(s.view, s.params));
    apply();
  }
  function close() {
    pendingCaseReturn = null; rememberDrawer();
    if (history.state && history.state.r4 && history.state.drawer && !history.state.detachedOrigin && Number.isInteger(history.state.depth) && history.state.depth > 0) history.go(-history.state.depth);
    else update(null, { panel: null }, true);
  }
  function toast(message) {
    var el = document.getElementById("cri-toast");
    clearTimeout(toastTimer); el.textContent = message; el.hidden = false;
    toastTimer = setTimeout(function () { el.hidden = true; }, 5000);
  }
  function storedSnapshot(s) {
    return !!s && typeof s === "object" && !Array.isArray(s) &&
      typeof s.revision === "string" && s.revision.length > 0 &&
      s.authority === "conditional_research_only";
  }
  function savedDay(value) {
    if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
    var day = new Date(value + "T00:00:00Z");
    return isFinite(day.getTime()) && day.toISOString().slice(0, 10) === value;
  }
  function usableSnapshot(s) {
    return storedSnapshot(s) && (s.horizon_days === 7 || s.horizon_days === 30) &&
      savedDay(s.as_of) && savedDay(s.expires) && s.expires >= s.as_of &&
      ["id", "asset", "title_en", "title_zh", "condition_en", "condition_zh",
        "sequence_en", "sequence_zh", "invalidation_en", "invalidation_zh",
        "counter_en", "counter_zh"].every(function (key) {
        return typeof s[key] === "string" && s[key].trim().length > 0;
      });
  }
  function stored() {
    try {
      var serialized = localStorage.getItem(storageKey);
      var entries = serialized === null ? [] : JSON.parse(serialized, function (key, value) {
        if (typeof value === "number" && !isFinite(value)) throw new Error("Unsupported saved number");
        return value;
      });
      if (!Array.isArray(entries)) return { ready: false };
      return { ready: true, serialized: serialized, entries: entries,
        items: entries.filter(usableSnapshot).slice(0, 50) };
    } catch (error) { return { ready: false }; }
  }
  function savedMatches(collection, revision) {
    return collection.entries.filter(function (entry) {
      return entry && typeof entry === "object" && entry.revision === revision;
    });
  }
  function savedVersion(collection, revision) {
    var matches = savedMatches(collection, revision);
    return matches.length === 1 && usableSnapshot(matches[0]) ? matches[0] : null;
  }
  function savedUnavailable() {
    title.textContent = t("Saved snapshots unavailable", "已存快照暂不可用");
    paragraph(t("Saved snapshots couldn’t be read.", "无法读取已存快照。")).className = "cri-warning";
    var actions = node("div", null, "cri-drawer-actions"); body.appendChild(actions);
    button(t("Try reading again", "重试读取"), function () { apply(); }, actions).classList.add("cri-btn-primary");
    button(t("Open current outlook", "查看当前展望"), function () { update("overview", { panel: null }, true); }, actions);
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
  function save(s, intent, trigger) {
    if (!s || typeof s.revision !== "string" || !s.revision ||
        (intent !== "save" && intent !== "remove")) return;
    var actionUrl = location.href, actionLang = zh(), actionHistory = historySignature(), actionHistoryLength = history.length, panel = state().params.get("panel");
    var ownedFocus = document.activeElement === trigger;
    function ownsAction() {
      return location.href === actionUrl && zh() === actionLang && history.length === actionHistoryLength &&
        trigger && trigger.isConnected && body.contains(trigger);
    }
    function report(message) {
      if (!ownsAction()) return;
      toast(message);
      if (!ownedFocus || document.activeElement !== trigger || !ownsAction() || historySignature() !== actionHistory) return;
      var feedback = document.getElementById("cri-toast").getBoundingClientRect();
      var frame = dialog.getBoundingClientRect(), header = dialog.querySelector(".cri-dialog-header").getBoundingClientRect();
      var top = Math.max(frame.top + dialog.clientTop, header.bottom);
      var bottom = frame.top + dialog.clientTop + dialog.clientHeight;
      // Failure has no changed action to signal its outcome; keep the message visible.
      if (feedback.bottom > bottom) dialog.scrollTop += feedback.bottom - bottom;
      else if (feedback.top < top) dialog.scrollTop += feedback.top - top;
    }
    var collection = stored();
    if (!collection.ready) {
      report(t("Saved snapshots couldn’t be read. No changes were made.", "无法读取已存快照，未作任何更改。"));
      return;
    }
    var matches = savedMatches(collection, s.revision), next, outcome;
    if (intent === "save" && matches.length) {
      if (matches.length !== 1 || !usableSnapshot(matches[0])) {
        report(t("This saved version couldn’t be read reliably. No changes were made.", "无法可靠读取此已存版本，未作任何更改。"));
        return;
      }
      outcome = "present";
    } else if (intent === "remove" && !matches.length) {
      outcome = "absent";
    } else if (intent === "remove") {
      next = collection.entries.filter(function (entry) {
        return !(entry && typeof entry === "object" && entry.revision === s.revision);
      });
      outcome = "removed";
    } else {
      if (!usableSnapshot(s) || expired(s) || s.state === "insufficient" || s.progress_state === "unavailable") {
        report(t("This scenario cannot be saved with the available evidence.", "现有证据不足，无法保存此情景。"));
        return;
      }
      // Only a genuinely new save applies the existing 50-snapshot capacity.
      // Opaque entries survive; retained array order defines oldest, not dates.
      var excess = Math.max(0, collection.entries.filter(storedSnapshot).length - 49);
      next = collection.entries.filter(function (entry) {
        if (storedSnapshot(entry) && excess > 0) { excess -= 1; return false; }
        return true;
      });
      next.push(Object.assign({}, s, { saved_at: new Date().toISOString(), issue_evidence: snapshotEvidence() }));
      outcome = "saved";
    }
    if (next) {
      var serialized;
      try { serialized = JSON.stringify(next); }
      catch (error) {
        report(t("The saved collection couldn’t be prepared. No changes were made.", "无法准备已存快照数据，未作任何更改。"));
        return;
      }
      try {
        localStorage.setItem(storageKey, serialized);
        collection = stored();
        if (!collection.ready || collection.serialized !== serialized) throw new Error("Unconfirmed saved collection");
      } catch (error) {
        report(t("The change couldn’t be confirmed. Check Saved snapshots before trying again.", "无法确认更改结果。请先查看已存快照，再决定是否重试。"));
        return;
      }
    }
    if (!ownsAction()) return;
    toast(outcome === "saved" ? t("Saved on this device.", "已保存至本设备。") :
      outcome === "removed" ? t("Removed from this device.", "已从本设备移除。") :
      outcome === "present" ? t("Already saved on this device.", "本设备已保存此快照。") :
      t("This snapshot is no longer saved on this device.", "本设备已无此快照。"));
    // A programmatic activation must not replace an unrelated focused control.
    if (!ownedFocus || document.activeElement !== trigger) return;
    if (intent === "remove" && panel === "saved-item:" + s.revision) {
      update(null, { panel: "saved" }, true);
      return; // apply() owns displaced focus; no late focus after its callbacks.
    }
    var captured = captureDrawerReading();
    if (!captured.owned || !ownsAction() || document.activeElement !== trigger) return;
    var priorSuspension = readingSuspended, restoredAction, projected = false;
    readingSuspended = true;
    try {
      renderDrawer(panel, collection);
      if (location.href !== actionUrl || zh() !== actionLang ||
          history.length !== actionHistoryLength || historySignature() !== captured.signature) return;
      var focusAfterRender = document.activeElement;
      if (focusAfterRender !== document.body && focusAfterRender !== trigger && focusAfterRender !== dialog) return;
      var reading = matchingDrawerReading(captured.reading);
      if (reading) { restoreDrawerReading(reading); projected = true; }
      restoredAction = usableDrawerFocus(body.querySelector("[data-snapshot-action]")) || title;
      if (restoredAction === title) title.tabIndex = -1;
      // Persist the completed projection before focus, including inside a render callback.
      var completed = captureDrawerReading(restoredAction === title ? "heading" : restoredAction.dataset.drawerFocus);
      if (!completed.owned || (reading ? !persistDrawerReading(completed) : !ownsDrawerCapture(completed)) ||
          location.href !== actionUrl || zh() !== actionLang || body.firstChild !== completed.subtree ||
          history.length !== actionHistoryLength || document.activeElement !== focusAfterRender) return;
    } finally { readingSuspended = priorSuspension; }
    restoredAction.focus({ preventScroll: projected });
    // No later projection or persistence: a focus callback owns its new choice.
  }
  function scenarioCardState(s, today, language) {
    var windowState = "unknown", progress = null, nextCheck = null, insufficient = false;
    if (s && typeof s === "object" && !Array.isArray(s)) {
      if (savedDay(s.as_of) && savedDay(s.expires) && s.expires >= s.as_of && savedDay(today)) {
        windowState = s.as_of > today ? "future" : s.expires < today ? "expired" : "open";
      }
      progress = savedText(s["progress_" + language]);
      nextCheck = savedText(s["next_check_" + language]);
      insufficient = s.state === "insufficient" || s.progress_state === "unavailable";
    }
    return { window: windowState, progress: progress, nextCheck: nextCheck, insufficient: insufficient };
  }
  function renderScenarioCards(today, language) {
    var labels = language === "zh" ? {
      expired: "已到期 · 仅供历史参考", unknown: "到期状态暂无", future: "观测日期超前",
      cutoff: "原始时点 · ", recorded: "记录状态 · ", missing: "记录状态暂无",
      insufficient: "价格证据暂无", next: "下一步检查", recordedNext: "当时的下一步检查", absent: "未提供"
    } : {
      expired: "Expired · historical context only", unknown: "Expiry status unavailable", future: "Future-dated observation",
      cutoff: "At cutoff · ", recorded: "Recorded status · ", missing: "Recorded status unavailable",
      insufficient: "Price evidence unavailable", next: "Next check", recordedNext: "Recorded next check", absent: "Not supplied"
    };
    root.querySelectorAll("[data-scenario-card]").forEach(function (card) {
      var group = card.closest("[data-case-horizon]");
      var scenarios = group && data.scenarios && data.scenarios[group.dataset.caseHorizon];
      var scenario = Array.isArray(scenarios) ? scenarios.find(function (s) { return s && s.id === card.dataset.scenarioCard; }) : null;
      var reading = scenarioCardState(scenario, today, language);
      var recorded = reading.window !== "open" || reading.insufficient || !reading.progress;
      var windowLabel = card.querySelector("[data-card-window]"), progressLabel = card.querySelector("[data-card-progress-label]");
      card.dataset.cardRecorded = String(recorded);
      windowLabel.hidden = reading.window === "open";
      windowLabel.textContent = labels[reading.window] || "";
      progressLabel.hidden = !recorded || reading.insufficient || !reading.progress;
      progressLabel.textContent = progressLabel.hidden ? "" : reading.window === "expired" ? labels.cutoff : labels.recorded;
      card.querySelector("[data-card-progress-value]").textContent = reading.insufficient ? labels.insufficient : reading.progress || labels.missing;
      card.querySelector("[data-card-next-label]").textContent = recorded ? labels.recordedNext : labels.next;
      card.querySelector("[data-card-next]").textContent = reading.nextCheck || labels.absent;
    });
  }
  function progressStatus(s) {
    if (s.state === "insufficient") return t("Insufficient price history", "价格历史不足");
    if (s.progress_en) return field(s, "progress");
    if (s.levels && ((s.id === "continuation" && s.levels.position === "above") || (s.id === "failure" && s.levels.position === "below"))) return t("Price condition met · demand unconfirmed", "价格条件已满足 · 需求尚未确认");
    return t("Conditional · confirmation pending", "条件路径 · 等待确认");
  }
  function status(s) {
    return expired(s) ? t("Expired · historical context only", "已到期 · 仅供历史参考") : progressStatus(s);
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
  function savedText(value) { return typeof value === "string" && value.trim() ? value : null; }
  function savedProgress(s) { return savedText(field(s, "progress")); }
  function savedScenario(s) {
    savedIdentity(s); body.classList.add("cri-saved-case");
    drawerParent(hasDrawerParent("saved") ? t("← Saved snapshots", "← 已存快照") : t("Open saved snapshots", "查看已存快照"), returnToSavedList);
    paragraph(s.asset + " · " + s.horizon_days + t(" days · cutoff ", "天 · 截止 ") + s.as_of).className = "cri-saved-meta";
    var progress = savedProgress(s);
    paragraph(expired(s) ? status(s) : progress ? t("At cutoff · ", "快照时 · ") + progress :
      t("Original progress unavailable", "原始进展暂无")).className = "cri-warning cri-saved-status";
    heading(t("Original condition", "原始条件"));
    paragraph(field(s, "condition")).className = "cri-case-condition";

    var details = node("details", null, "mx-disc cri-saved-details");
    var summary = node("summary", t("Original case details", "原始情景详情"));
    details.dataset.drawerDisclosure = "case-details"; summary.dataset.drawerFocus = "case-details";
    details.appendChild(summary);
    var rows = [];
    if (expired(s)) rows.push([t("Progress at cutoff", "快照时进展"), progress || t("Not preserved", "未保存")]);
    rows.push([t("Sequence at cutoff", "当时的后续路径"), field(s, "sequence")],
      [t("Original invalidation condition", "原始失效条件"), field(s, "invalidation")],
      [t("Counterpoint at cutoff", "当时的反向因素"), field(s, "counter")]);
    if (field(s, "next_check")) rows.push([t("Next check recorded then", "当时记录的下一步检查"), field(s, "next_check")]);
    rows.push([t("Expiry", "到期日"), s.expires]);
    var levels = s.levels;
    if (levels && levels.available === true && levels.basis === "prior_daily_closes" &&
        Number.isInteger(levels.lookback_days) && levels.lookback_days > 0 &&
        savedDay(levels.start) && savedDay(levels.end) && levels.start <= levels.end && levels.end < s.as_of) {
      rows.push([t("Prior-close basis", "前期收盘价依据"),
        levels.lookback_days + t(" prior daily closes · ", "个此前日收盘价 · ") + levels.start + " – " + levels.end]);
      if (typeof levels.low === "number" && isFinite(levels.low) && typeof levels.high === "number" &&
          isFinite(levels.high) && levels.low > 0 && levels.high >= levels.low)
        rows.push([t("Prior-close range", "前期收盘区间"), money(levels.low) + " – " + money(levels.high)]);
    } else rows.push([t("Prior-close basis", "前期收盘价依据"), t("The original range window is unavailable.", "原始区间窗口暂无。")]);
    definition(rows, details);
    details.appendChild(node("p", t("Levels use prior daily closes. They are research conditions, not official model invalidations.", "价位来自前期日收盘，属于研究条件，并非官方模型失效位。"), "cri-saved-note"));
    body.appendChild(details);

    var savedEvidence = s.issue_evidence;
    var retainedFamilies = savedEvidence && Array.isArray(savedEvidence.families) ? savedEvidence.families : [];
    var families = retainedFamilies.filter(function (f) {
      return f && typeof f === "object" && !Array.isArray(f) &&
        (savedText(field(f, "label")) || savedText(f.id)) && savedText(field(f, "state"));
    });
    if (families.length) {
      var digest = node("details", null, "mx-disc cri-saved-details cri-saved-evidence");
      var digestSummary = node("summary", t("Original evidence", "原始证据"));
      digest.dataset.drawerDisclosure = "saved-evidence"; digestSummary.dataset.drawerFocus = "saved-evidence";
      digestSummary.appendChild(node("span", families.length + (families.length === 1 ? t(" captured reading", "项留存读数") : t(" captured readings", "项留存读数")), "cri-disclosure-meta"));
      digest.appendChild(digestSummary);
      digest.appendChild(node("p", t("Bitcoin snapshot: ", "比特币快照：") + (savedDay(savedEvidence.bitcoin_as_of) ? savedEvidence.bitcoin_as_of : t("date unavailable", "日期暂无")) +
        t(" · Broader-market snapshot: ", " · 全市场快照：") + (savedDay(savedEvidence.market_as_of) ? savedEvidence.market_as_of : t("date unavailable", "日期暂无")), "cri-saved-note"));
      if (families.length !== retainedFamilies.length)
        digest.appendChild(node("p", t("Some saved evidence entries could not be read.", "部分已存证据条目无法读取。"), "cri-saved-note"));
      var digestList = node("dl");
      families.forEach(function (f) {
        var item = node("div"), name = node("dt", savedText(field(f, "label")) || savedText(f.id));
        var reading = node("dd", savedText(field(f, "state")));
        var quality = f.quality === "observed" ? t("Observed at capture", "保存时有观测") :
          f.quality === "snapshot_only" ? t("Snapshot only", "仅快照") :
          f.quality === "stale" ? t("Stale at capture", "保存时已过时") :
          f.quality === "insufficient" || f.quality === "missing" ? t("Incomplete at capture", "保存时不完整") :
          t("Quality unavailable", "质量未知");
        reading.appendChild(node("span", quality + " · " + (savedDay(f.snapshot_as_of) ?
          t("Snapshot ", "快照 ") + f.snapshot_as_of : t("Snapshot date unavailable", "快照日期暂无")), "cri-captured-meta"));
        item.append(name, reading); digestList.appendChild(item);
      });
      digest.appendChild(digestList);
      digest.appendChild(node("p", t("These are the readings saved at issue time, not current evidence or validated forecast performance.", "这些读数属于原始时点，并非最新证据或已验证的预测表现。"), "cri-saved-note"));
      body.appendChild(digest);
    } else {
      heading(t("Original evidence", "原始证据"));
      paragraph(Object.prototype.hasOwnProperty.call(s, "issue_evidence") ?
        t("The saved evidence digest is incomplete or unreadable. Original conditions and cutoff remain available.", "已存证据摘要不完整或无法读取。原始条件与截止日期仍可查看。") :
        t("Evidence digest was not preserved in this older snapshot. Its original conditions and cutoff remain visible, but source quality cannot be reconstructed.", "旧快照未保存原始证据摘要。原始条件与时间仍可查看，但无法恢复当时的来源质量。")).className = "cri-warning";
    }
    var actions = node("div", null, "cri-saved-actions"); body.appendChild(actions);
    var review = button(t("Historical review", "历史检验"), function () { open("memory-saved:" + s.revision, null, String(s.horizon_days), "review"); }, actions);
    review.classList.add("cri-btn-primary"); review.dataset.drawerFocus = "review";
    var remove = button(t("Remove from this device", "从本设备移除"), function (event) { save(s, "remove", event.currentTarget); }, actions);
    remove.classList.add("cri-btn-remove"); remove.dataset.snapshotAction = "remove"; remove.dataset.drawerFocus = "remove";
  }
  function reviewRequirements() {
    return [[t("Point-in-time history", "时点历史"), t("Source availability and revisions retained", "保留来源可用时间与修订")],
      [t("Independent episodes", "独立事件"), t("Overlapping warnings are not separate cases", "重叠预警不算独立案例")],
      [t("Counterexamples", "反例"), t("Failures shown alongside matches", "失败案例与匹配案例并列")],
      [t("Forecast evaluation", "预测检验"), t("Simple baselines, held-out periods and calibration", "简单基线、留出区间与校准")]];
  }
  function savedReview(s) {
    body.classList.add("cri-saved-review");
    paragraph(field(s, "title") + " · " + s.asset + " · " + s.horizon_days + t(" days", "天")).className = "cri-review-identity";
    paragraph(t("Evidence cutoff · ", "证据截止日期 · ") + s.as_of).className = "cri-saved-meta";
    var result = node("section", null, "cri-review-state");
    result.append(node("h3", t("No qualified comparison yet", "暂无合格的历史比较")),
      node("p", t("No performance result is available for this saved case.", "此已存情景尚无可用的表现检验结果。")));
    body.appendChild(result);
    var details = node("details", null, "mx-disc cri-saved-details");
    var summary = node("summary", t("What would qualify a comparison", "什么样的比较才合格"));
    details.dataset.drawerDisclosure = "review-requirements"; summary.dataset.drawerFocus = "review-requirements";
    details.appendChild(summary);
    details.appendChild(node("p", t("A historical match must preserve the scenario's issue-time evidence, horizon and eligible universe. Similar-looking charts alone do not establish predictive value.", "历史匹配必须保留情景发布时的证据、周期与合格样本。图形相似本身不能证明预测价值。"), "cri-saved-note"));
    definition(reviewRequirements(), details); body.appendChild(details);
  }
  function scenario(s, frozen, collection) {
    if (!s) {
      title.textContent = t("Scenario unavailable", "情景暂不可用");
      paragraph(frozen ? t("This scenario is unavailable. The source may have changed or the saved item was removed.", "该情景不可用，原始来源可能已经变化或快照已经移除。") :
        t("This scenario is not in the current snapshot for this horizon.", "当前快照在此周期内没有这个情景。"));
      if (frozen) {
        var actions = node("div", null, "cri-drawer-actions"); body.appendChild(actions);
        var recover = button(t("Open saved snapshots", "查看已存快照"), function () { update(null, { panel: "saved" }, true); }, actions);
        recover.classList.add("cri-btn-primary"); recover.dataset.drawerFocus = "saved-recovery";
        button(t("Open current outlook", "查看当前展望"), function () { update("overview", { panel: null }, true); }, actions);
      } else {
        var currentActions = node("div", null, "cri-drawer-actions"); body.appendChild(currentActions);
        button(t("Browse scenarios", "浏览情景"), function () { update("scenarios", { panel: null }, true); }, currentActions).classList.add("cri-btn-primary");
      }
      return;
    }
    title.textContent = field(s, "title");
    if (frozen) { savedScenario(s); return; }
    paragraph(status(s)).className = "cri-warning";
    paragraph((s.asset || t("Asset unavailable", "资产暂无")) + " · " + s.horizon_days + t(" days", "天") + " · " + (s.as_of || t("Date not supplied", "未提供日期"))).className = "cri-note";
    if (s.next_check_en && !expired(s)) { heading(t("Next check", "下一步检查")); paragraph(field(s, "next_check")); }
    heading(expired(s) ? t("Sequence at the original cutoff", "原始时点的后续路径") : t("What could follow", "可能的后续变化")); paragraph(field(s, "sequence"));
    heading(expired(s) ? t("Original invalidation condition", "原始失效条件") : t("What changes the view", "什么会改变判断")); paragraph(field(s, "invalidation"));
    var details = node("details", null, "mx-disc");
    var caseSummary = node("summary", t("Conditions and evidence", "条件与证据"));
    details.dataset.drawerDisclosure = "scenario-conditions"; caseSummary.dataset.drawerFocus = "scenario-conditions";
    details.appendChild(caseSummary);
    details.appendChild(node("p", field(s, "condition")));
    details.appendChild(node("p", field(s, "counter")));
    details.appendChild(node("p", t("Expires: ", "到期日：") + s.expires));
    details.appendChild(node("p", t("Levels use prior daily closes. They are research conditions, not official model invalidations.", "价位来自前期日收盘，属于研究条件，并非官方模型失效位。")));
    body.appendChild(details);
    collection = collection === undefined ? stored() : collection;
    if (!collection.ready) paragraph(t("Saved snapshots couldn’t be read.", "无法读取已存快照。")).className = "cri-warning";
    var actions = node("div", null, "cri-drawer-actions cri-current-actions"); body.appendChild(actions);
    button(t("Historical review", "历史检验"), function () {
      open("memory:" + s.id, null, String(s.horizon_days), "review");
    }, actions).dataset.drawerFocus = "review";
    if (!collection.ready) {
      button(t("Try reading again", "重试读取"), function () { apply(); }, actions).dataset.drawerFocus = "storage-retry";
    } else {
      var saved = savedMatches(collection, s.revision).length > 0, intent = saved ? "remove" : "save";
      var saveButton = button(saved ? t("Remove snapshot", "移除快照") : t("Save snapshot", "保存快照"), function (event) { save(s, intent, event.currentTarget); }, actions);
      if (intent === "save") saveButton.classList.add("cri-btn-primary");
      saveButton.dataset.snapshotAction = intent; saveButton.dataset.drawerFocus = "snapshot-" + intent;
      saveButton.disabled = !saved && (expired(s) || s.state === "insufficient" || s.progress_state === "unavailable");
    }
    var demandActions = node("div", null, "cri-drawer-actions cri-current-demand"); body.appendChild(demandActions);
    button(t("Inspect demand evidence", "查看需求证据"), function () {
      open("evidence:liquidity_flows", null, null, "demand-evidence");
    }, demandActions).dataset.drawerFocus = "demand-evidence";
  }
  function comparisonBasis(asset) {
    // One bilingual copy owner: the server-rendered Markets disclosure.
    var details = document.getElementById("cri-market-basis").cloneNode(true);
    details.removeAttribute("id"); details.hidden = false; details.open = false;
    var coverage = details.querySelector("[data-open]");
    coverage.addEventListener("click", function () { open(coverage.dataset.open, coverage); });
    if (asset) {
      details.appendChild(node("h3", t("Asset coverage", "资产覆盖")));
      details.appendChild(node("p", field(asset, "coverage")));
      details.appendChild(node("p", t("Asset-specific conditional price levels are not supplied.", "未提供此资产的条件价位。")));
    }
    body.appendChild(details);
    return details;
  }
  function assetEmptyCopy() {
    return data.contracts && data.contracts.asset_states === "accepted" ?
      [t("No assets in this snapshot", "本快照暂无资产"), t("There are no asset readings to display.", "暂无可显示的资产读数。")] :
      [t("Asset data unavailable", "资产数据暂无"), t("This snapshot could not provide asset readings.", "本快照无法提供资产读数。")];
  }
  function renderDrawer(key, collection) {
    if (!key) return;
    body.replaceChildren(); body.classList.remove("cri-saved-case", "cri-saved-review");
    dialog.classList.remove("cri-dialog-saved"); dialog.classList.toggle("cri-dialog-wide", key === "comparison"); kicker.textContent = t("CRYPTO INTELLIGENCE", "加密资产情报");
    body.dataset.panel = key;
    delete body.dataset.savedRevision; delete body.dataset.savedHorizon; delete body.dataset.savedCutoff; delete body.dataset.savedList;
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
      scenario(activeScenario(id), false, collection);
    } else if (category === "saved-item") {
      collection = collection === undefined ? stored() : collection;
      if (!collection.ready) { savedUnavailable(); return; }
      scenario(savedVersion(collection, id), true);
    } else if (category === "asset") {
      var asset = data.assets.find(function (a) { return a.symbol === id; });
      title.textContent = asset ? assetTitle(asset) : t("Asset unavailable", "资产暂不可用");
      if (asset) {
        comparisonBasis(asset);
        var assetReadings = definition([[t("Price", "价格"), assetMoney(asset.price)], [t("Asset observation date", "资产观测日期"), asset.as_of],
          [t("Price change", "价格涨跌"), pct(asset.change_30d_pct)],
          [t("Asset/BTC ratio change", "资产/BTC比值变化"), pct(asset.relative_90d_pct)],
          [t("Relative state", "相对状态"), field(asset, "relative") || t("Unavailable", "暂无")],
          [t("Structure", "结构"), field(asset, "trend")], [t("Risk", "风险"), field(asset, "risk")]]);
        assetReadings.children[0].classList.add("cri-asset-quote");
        assetReadings.children[1].classList.add("cri-asset-observed");
      } else {
        paragraph(data.contracts && data.contracts.asset_states === "accepted" ?
          t("This asset is not present in the snapshot.", "本快照中没有此资产。") : assetEmptyCopy()[1]);
        button(t("Data and coverage", "数据与覆盖"), function () { open("coverage"); });
      }
    } else if (category === "comparison") {
      title.textContent = t("Compare assets", "比较资产");
      if (!data.assets.length) {
        var empty = assetEmptyCopy();
        heading(empty[0]); paragraph(empty[1]);
        button(t("Data and coverage", "数据与覆盖"), function () { open("coverage"); });
        return;
      }
      paragraph(t("All " + data.assets.length + " assets in this snapshot", "本快照中的全部" + data.assets.length + "项资产")).className = "cri-comparison-scope";
      comparisonBasis();
      var wrap = node("div", null, "cri-comparison-scroll"), table = node("table", null, "cri-comparison-table");
      wrap.tabIndex = 0; wrap.setAttribute("role", "region"); wrap.setAttribute("aria-label", t("Asset comparison, scroll for more columns", "资产比较，可滚动查看其余列"));
      var caption = node("caption", t("All reported assets. Observation dates belong to each asset, not a verified shared comparison endpoint.", "全部已提供的资产。观测日期属于各资产，并非已确认的共同比较截止日期。"), "cri-sr");
      table.appendChild(caption);
      var headerRow = node("tr");
      [t("Measure", "指标")].concat(data.assets.map(function (a) { return a.symbol; })).forEach(function (label) { var cell = node("th", label); cell.scope = "col"; headerRow.appendChild(cell); });
      var head = node("thead"); head.appendChild(headerRow); table.appendChild(head);
      var tbody = node("tbody");
      [[t("Asset observation date", "资产观测日期"), function (a) { return a.as_of; }],
       [t("Asset/BTC ratio change", "资产/BTC比值变化"), function (a) { return pct(a.relative_90d_pct); }, "relative"],
       [t("Price change", "价格涨跌"), function (a) { return pct(a.change_30d_pct); }],
       [t("Structure", "结构"), function (a) { return field(a, "trend"); }],
       [t("Risk", "风险"), function (a) { return field(a, "risk"); }]].forEach(function (row) {
        var tr = node("tr"), label = node("th", row[0]); label.scope = "row"; tr.appendChild(label);
        data.assets.forEach(function (a) {
          var cell = node("td", row[1](a) || t("Unavailable", "暂无"));
          if (row[2] === "relative" && a.relative_90d_pct === null && field(a, "relative") && field(a, "relative") !== t("Unavailable", "暂无")) {
            cell.appendChild(node("span", field(a, "relative"), "cri-measure-state"));
          }
          tr.appendChild(cell);
        }); tbody.appendChild(tr);
      });
      table.appendChild(tbody); wrap.appendChild(table); body.appendChild(wrap);
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
      collection = collection === undefined ? stored() : collection;
      if (!collection.ready) { savedUnavailable(); return; }
      title.textContent = t("Saved snapshots", "已存快照"); body.dataset.savedList = "true";
      paragraph(t("Saved in this browser. Each snapshot preserves its original evidence cutoff.", "保存在此浏览器中，每份快照保留原始证据截止日期。"));
      var items = collection.items;
      if (!items.length) paragraph(collection.entries.length ?
        t("No supported snapshots can be opened here.", "此处无法打开这些已存快照。") :
        t("Nothing saved yet. Open a scenario and save its dated conditions.", "尚未保存。打开一个情景，保存其带日期的条件。"));
      items.forEach(function (s) {
        var entry = button(field(s, "title") + " · " + s.horizon_days + t(" days", "天") + " · " + s.as_of, function () {
          open("saved-item:" + s.revision, null, String(s.horizon_days), "saved:" + s.revision);
        });
        entry.dataset.drawerFocus = "saved:" + s.revision;
      });
    } else if (category === "memory" || category === "memory-saved") {
      title.textContent = t("Historical review", "历史检验");
      var historicalContext;
      if (category === "memory-saved") {
        collection = collection === undefined ? stored() : collection;
        if (!collection.ready) { savedUnavailable(); return; }
        historicalContext = savedVersion(collection, id);
        if (!historicalContext) { scenario(null, true); return; }
        savedIdentity(historicalContext);
        drawerParent(hasDrawerParent("saved-item:" + id) ? t("← Saved case", "← 已存情景") : t("Open saved case", "打开已存情景"), function () { returnToSavedCase(id); });
        savedReview(historicalContext); return;
      } else {
        historicalContext = id ? activeScenario(id) : null;
        if (key !== "memory" && !historicalContext) { scenario(null, false); return; }
        if (historicalContext) {
          var caseHorizon = horizon();
          drawerParent(hasDrawerParent("scenario:" + id, caseHorizon) ? t("← Scenario details", "← 情景详情") :
            t("Open scenario details", "打开情景详情"), function () { returnToCurrentCase(id, caseHorizon); }, t("Scenario", "情景"));
        }
      }
      paragraph(historicalContext ? field(historicalContext, "title") + " · BTC · " + historicalContext.horizon_days + t(" days · evidence at ", "天 · 证据日期 ") + historicalContext.as_of : "BTC · " + horizon() + t(" days · evidence at ", "天 · 证据日期 ") + (data.as_of || t("Unavailable", "暂无")));
      paragraph(t("No qualified comparison yet", "暂无合格的历史比较")).className = "cri-warning";
      paragraph(t("A historical match must preserve the scenario's issue-time evidence, horizon and eligible universe. Similar-looking charts alone do not establish predictive value.", "历史匹配必须保留情景发布时的证据、周期与合格样本。图形相似本身不能证明预测价值。"));
      heading(t("Required before results", "结果发布前需要"));
      definition(reviewRequirements());
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
    var s = state(), query = (s.params.get("q") || "").toLowerCase();
    var filter = s.params.get("filter"), sort = s.params.get("sort");
    filter = ["all", "leaders", "stressed"].indexOf(filter) >= 0 ? filter : "all";
    sort = ["default", "relative", "return", "symbol"].indexOf(sort) >= 0 ? sort : "default";
    var search = document.getElementById("cri-search"), filterSelect = document.getElementById("cri-filter"), sortSelect = document.getElementById("cri-sort");
    search.value = s.params.get("q") || ""; search.placeholder = t("Search assets", "搜索资产");
    filterSelect.setAttribute("aria-label", t("Asset filter", "资产筛选"));
    sortSelect.setAttribute("aria-label", t("Asset sort", "资产排序"));
    Array.from(filterSelect.options).forEach(function (o) { o.textContent = {all:t("All assets","全部资产"),leaders:t("Leading Bitcoin","领先比特币"),stressed:t("Stressed","承压")}[o.value]; });
    Array.from(sortSelect.options).forEach(function (o) { o.textContent = {default:t("Default order","默认顺序"),relative:t("Ratio change","比值变化"),return:t("Price change","价格涨跌"),symbol:t("Symbol","代码")}[o.value]; });
    filterSelect.value = filter; sortSelect.value = sort;
    var items = data.assets.slice();
    if (sort !== "default") items.sort(function (a, b) {
      if (sort === "symbol") return a.symbol.localeCompare(b.symbol);
      var key = sort === "return" ? "change_30d_pct" : "relative_90d_pct";
      return (b[key] === null ? -Infinity : b[key]) - (a[key] === null ? -Infinity : a[key]);
    });
    var shown = 0, tbody = document.querySelector("#cri-market-table tbody");
    items.forEach(function (asset, index) {
      var row = Array.from(tbody.children).find(function (r) { return r.dataset.assetRow === asset.symbol; });
      if (!row) return;
      var matches = (asset.name + " " + asset.symbol).toLowerCase().indexOf(query) >= 0 &&
        (filter !== "leaders" || asset.relative_en === "Leading Bitcoin") && (filter !== "stressed" || asset.risk_en === "Stressed");
      row.hidden = !matches;
      // Keep surviving controls attached when locale or unrelated state refreshes.
      if (tbody.children[index] !== row) tbody.insertBefore(row, tbody.children[index] || null);
      if (matches) shown++;
    });
    var hasAssets = data.assets.length > 0, empty = document.getElementById("cri-market-empty");
    document.getElementById("cri-market-controls").hidden = !hasAssets;
    document.getElementById("cri-market-table").hidden = !hasAssets || shown === 0;
    document.getElementById("cri-market-basis").hidden = !hasAssets;
    document.getElementById("cri-market-compare").hidden = !hasAssets;
    document.getElementById("cri-reset").hidden = !hasAssets;
    document.getElementById("cri-empty-coverage").hidden = hasAssets;
    empty.hidden = shown !== 0;
    var copy = hasAssets ? [t("No matching assets", "没有符合条件的资产"), t("Try a different search or reset the filters.", "请调整搜索或重置筛选。")] : assetEmptyCopy();
    document.getElementById("cri-market-empty-title").textContent = copy[0];
    document.getElementById("cri-market-empty-note").textContent = copy[1];
    var count = document.getElementById("cri-market-count");
    count.hidden = !hasAssets;
    count.textContent = t(shown + " of " + data.assets.length + " assets", "显示" + shown + "项，共" + data.assets.length + "项资产");
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
  function apply(event) {
    // popstate always consumes its incoming entry, even when its URL is unchanged.
    if (event && event.type === "hashchange" &&
        (event.newURL !== location.href || root.dataset.renderedAddress === location.href &&
         root.dataset.renderedLanguage === String(zh()))) return;
    var priorSuspension = readingSuspended; readingSuspended = true;
    try {
      var s = state(), panel = s.params.get("panel"), requestAddress = location.href, requestLanguage = zh(), requestSubtree = body.firstChild, requestFocus = document.activeElement;
      var startingCurrentReview = panel && panel.indexOf("memory:") === 0 && activeScenario(panel.slice(7)) &&
        (!dialog.open || root.dataset.renderedAddress !== requestAddress ||
         event && event.type === "popstate" || renderedHistory !== historySignature());
      var returning = pendingCaseReturn && pendingCaseReturn.parentAddress === requestAddress &&
        panel === pendingCaseReturn.panel ? pendingCaseReturn : null;
      if (pendingCaseReturn && requestAddress !== pendingCaseReturn.childAddress) pendingCaseReturn = null;
      var collection = event && event.collection, retained;
      if (panel && (panel === "saved" || /^(scenario|saved-item|memory-saved):/.test(panel))) {
        collection = collection === undefined ? stored() : collection;
        if (location.href !== requestAddress || zh() !== requestLanguage ||
            body.firstChild !== requestSubtree || document.activeElement !== requestFocus) return;
      }
      if (panel && /^(saved-item|memory-saved):/.test(panel)) {
        retained = collection.ready ? savedVersion(collection, panel.slice(panel.indexOf(":") + 1)) : null;
        if (retained && s.params.get("h") !== String(retained.horizon_days)) {
          s.params.set("h", String(retained.horizon_days));
          history.replaceState(history.state, "", address(s.view, s.params));
        }
      }
      var h = s.params.get("h") === "30" ? "30" : "7", windowSize = s.params.get("window") === "30" ? "30" : "90";
      root.querySelectorAll("[data-view]").forEach(function (p) { p.hidden = p.dataset.view !== s.view; });
      var routeParams = new URLSearchParams(s.params); routeParams.delete("panel");
      root.querySelectorAll("[data-route]").forEach(function (a) {
        if (a.tagName === "A" && views.indexOf(a.dataset.route) >= 0) a.setAttribute("href", address(a.dataset.route, routeParams));
        if (a.closest(".cri-tabs") && a.dataset.route === s.view) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
      });
      root.querySelectorAll("[data-chart-window]").forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.chartWindow === windowSize)); });
      root.querySelectorAll("[data-chart-panel]").forEach(function (p) { p.hidden = p.dataset.chartPanel !== windowSize; });
      root.querySelectorAll("[data-horizon]").forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.horizon === h)); });
      root.querySelectorAll("[data-case-horizon]").forEach(function (p) { p.hidden = p.dataset.caseHorizon !== h; });
      renderScenarioCards(new Date().toISOString().slice(0, 10), requestLanguage ? "zh" : "en");
      filterMarkets(); renderShock();
      var focusWasInside = dialog.contains(document.activeElement);
      var priorBasis = body.querySelector("[data-comparison-basis]"), basisReading = null;
      if (priorBasis && body.dataset.panel === panel && root.dataset.renderedAddress === location.href &&
          root.dataset.renderedLanguage !== String(zh())) {
        var basisFocus = document.activeElement.closest("[data-basis-focus]");
        basisReading = { open: priorBasis.open, scroll: dialog.scrollTop,
          focus: basisFocus && priorBasis.contains(basisFocus) ? basisFocus.dataset.basisFocus : null };
      }
      if (panel) renderDrawer(panel, collection);
      if (startingCurrentReview) dialog.scrollTop = 0;
      var renderedBasis = body.querySelector("[data-comparison-basis]");
      if (basisReading && renderedBasis) renderedBasis.open = basisReading.open;
      root.dataset.renderedAddress = location.href; root.dataset.renderedLanguage = String(zh());
      renderedHistory = historySignature();
      var renderedAddress = location.href, renderedLanguage = zh(), subtree = body.firstChild;
      function ownsRender() {
        return location.href === renderedAddress && zh() === renderedLanguage && body.firstChild === subtree;
      }
      if (panel) {
        if (!dialog.open) {
          var openingFocusEvents = 0;
          function noteOpeningFocus() { openingFocusEvents += 1; }
          dialog.addEventListener("focusin", noteOpeningFocus, true);
          try { dialog.showModal(); } finally { dialog.removeEventListener("focusin", noteOpeningFocus, true); }
          if (!ownsRender() || !dialog.open || openingFocusEvents > 1) return;
        }
        if (basisReading && renderedBasis && ownsRender()) dialog.scrollTop = basisReading.scroll;
        var reading = drawerReading(), scope = readingScope();
        var returningToCase = returning && scope && returning.panel === scope.panel &&
          returning.revision === scope.revision && returning.horizon === scope.horizon && returning.cutoff === scope.cutoff;
        if (reading || returningToCase) {
          if (reading) restoreDrawerReading(reading);
          var restored = returningToCase ? drawerFocus("review") :
            reading && typeof reading.focus === "string" ? drawerFocus(reading.focus) : null;
          restored = usableDrawerFocus(restored) || title;
          if (restored === title) title.tabIndex = -1;
          restored.focus({ preventScroll: !!reading });
          return; // A focus callback owns any newer destination or reading position.
        }
        if (basisReading && basisReading.focus && renderedBasis && ownsRender()) {
          var basisTarget = renderedBasis.querySelector('[data-basis-focus="' + basisReading.focus + '"]');
          if (basisTarget) {
            basisTarget.focus({ preventScroll: true });
            return; // A focus callback owns any newer destination.
          }
        }
        if (focusWasInside && !dialog.contains(document.activeElement)) {
          var fallback = /^(saved-item|memory-saved):/.test(panel) ? title : document.getElementById("cri-dialog-close");
          if (fallback === title) title.tabIndex = -1;
          fallback.focus({ preventScroll: true });
        }
      } else if (dialog.open) {
        dialog.close();
        if (!ownsRender() || dialog.open) return;
        var active = document.activeElement;
        if (active !== document.body && !dialog.contains(active) && visibleInView(active, s.view)) return;
        var destination = visibleInView(lastTrigger, s.view) ? lastTrigger : viewHeading(s.view);
        if (destination) {
          if (destination.matches("h1,h2")) destination.tabIndex = -1;
          destination.focus();
        }
      }
    } finally { readingSuspended = priorSuspension; }
  }
  root.addEventListener("click", function (event) {
    var route = event.target.closest("[data-route]"), openButton = event.target.closest("[data-open]");
    if (route) {
      if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
      event.preventDefault();
      var routeView = route.dataset.route, activeSection = document.activeElement.closest("[data-view]");
      if (activeSection && activeSection.dataset.view !== routeView) {
        var routeAddress = location.href, routeLanguage = zh(), routeHistory = historySignature(), routeLength = history.length;
        var destination = Array.from(root.querySelectorAll(".cri-tabs [data-route]")).find(function (a) { return a.dataset.route === routeView; });
        if (!destination || !visibleInView(destination, state().view)) return;
        destination.focus();
        if (location.href !== routeAddress || zh() !== routeLanguage || historySignature() !== routeHistory || history.length !== routeLength ||
            document.activeElement !== destination || !visibleInView(destination, state().view)) return;
      }
      update(routeView, { panel: null });
    } else if (openButton) { event.preventDefault(); var caseGroup = openButton.closest("[data-case-horizon]"); var scenarioHorizon = openButton.dataset.open.indexOf("scenario:") === 0 ? (caseGroup ? caseGroup.dataset.caseHorizon : horizon()) : null; open(openButton.dataset.open, openButton, scenarioHorizon); }
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
  document.getElementById("cri-reset").addEventListener("click", function () {
    var addressBefore = location.href, languageBefore = zh(), search = document.getElementById("cri-search");
    search.focus();
    if (location.href !== addressBefore || zh() !== languageBefore || document.activeElement !== search) return;
    update(null, { q: null, filter: null, sort: null }, true);
  });
  window.addEventListener("popstate", apply); window.addEventListener("hashchange", apply);
  body.addEventListener("toggle", function (event) {
    if (body.contains(event.target) && event.target.hasAttribute("data-drawer-disclosure")) rememberDrawer();
  }, true);
  dialog.addEventListener("focusin", function () { rememberDrawer(); });
  dialog.addEventListener("scrollend", function () { rememberDrawer(); });
  new MutationObserver(function () { rememberDrawer(); apply(); }).observe(document.documentElement, { attributes: true, attributeFilter: ["data-lang"] });
  apply();
})();
