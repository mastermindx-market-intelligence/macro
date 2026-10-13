/* global module */
/* Admin workspace: navigation and browser-local presentation preferences only.
   No API writes, customer records, credentials, workflow state or new route inventory. */
(function (root) {
  "use strict";
  const STORAGE_KEY = "mastermind.admin.workspace.v1";
  const MAX_PINS = 8, MAX_RECENT = 6;
  const DETAILS = {
    overview: ["See operational attention and choose your next task.", "home dashboard status"],
    health: ["Check data freshness, pipeline reports and source failures.", "pipeline stale missing data feeds"],
    system: ["Inspect service availability and server resources.", "server cpu memory disk uptime infrastructure"],
    deploy: ["Review build history before starting a build or release.", "release deployment rebuild github actions"],
    analytics: ["Understand visits, traffic sources and customer activity.", "visitors pageviews traffic acquisition retention"],
    users: ["Find customer accounts and inspect account access.", "password reset account customer subscription access"],
    support_tickets: ["Read customer questions and manage support conversations.", "customer help support reply tickets"],
    email_center: ["Review mail and customer communication tools.", "email inbox messages customer mail"],
    revenue: ["Inspect revenue and subscription reporting.", "billing payments money sales subscriptions"],
    marketing_floor: ["See the publishing operation and its connected desks.", "publishing overview marketing operation"],
    marketing_outbox: ["Review queued content before it is published.", "scheduled posts queued drafts approval publishing queue"],
    marketing_content: ["Find and review content plans and their evidence.", "content studio drafts editorial charts plan"],
    marketing_publish: ["Inspect publishing delivery and its controls.", "publisher delivery posting channels"],
    neural_web: ["Explore the intelligence network and its connected lobes.", "observatory neural network intelligence engines"],
    intelligence_os: ["Inspect intelligence engines and their recorded output.", "engine registry evidence intelligence output"],
    orchestrator: ["Inspect Master Brain orchestration and research output.", "master brain orchestration reasoning"],
    prophet: ["Review Prophet research, candidates and diagnostics.", "stock candidates signals prophet trading research"],
    macro_thesis: ["Review recorded macro theses and supporting context.", "macro thesis economy research"],
    mastermind_ai: ["Inspect Mastermind AI status and configuration.", "assistant ai models configuration"],
    mastermind_logs: ["Review AI responses and evaluation records.", "response logs traces evaluation audit"],
    alerts: ["Inspect alert records and their underlying context.", "alerts signals notifications"],
    long_hold: ["Inspect long-hold research and its recorded evidence.", "long hold research"],
    context_lobe: ["Review the context used by intelligence systems.", "context lobe evidence"],
    causal_lab: ["Explore causal research and diagnostic records.", "causal laboratory research"],
    chronicle: ["Browse the market-context timeline.", "chronicle history timeline market events"],
    research_tools: ["Open internal research and calibration tools.", "calibration diagnostics research tools"],
    experiments: ["Review experiments, evidence and upcoming review dates.", "experiments tests research review"],
    marketing_sentinel: ["Review publishing monitoring and its findings.", "sentinel monitoring publishing"],
    marketing_lanes: ["Inspect X publishing lanes.", "twitter x publishing lanes"],
    marketing_radar: ["Explore topics and opportunities under observation.", "radar topics opportunities marketing"],
    marketing_reply_queue: ["Review suggested replies before taking action.", "reply deck review replies queue"],
    marketing_seo: ["Inspect search visibility and SEO work.", "search engine optimization seo organic"],
    marketing_models: ["Inspect model choices used by publishing desks.", "model desk providers marketing"],
    marketing_health: ["Review the health of the publishing desks.", "desk health marketing failures"],
    marketing_learning: ["Inspect publishing feedback and learning records.", "learning feedback publishing results"],
    marketing_lab: ["Explore publishing research and experiments.", "lab marketing research"],
    marketing_lobes: ["Inspect the engines supporting publishing.", "marketing engines lobes"],
    marketing_overview: ["Review marketing strategy and operating context.", "cmo office marketing strategy"],
    marketing_departments: ["Explore marketing departments and their work.", "department organization marketing"],
    marketing_campaigns: ["Inspect campaign plans and their status.", "campaigns marketing plans"],
    marketing_channels: ["Review channels and their publishing desks.", "channels desks distribution"],
    personas: ["Review publishing personas and their assigned beats.", "persona roster identity beats"],
    marketing_allies: ["Inspect the marketing allies directory.", "allies partners collaboration"],
    marketing_ads: ["Review advertising tools and recorded campaigns.", "advertising paid ads campaigns"],
    marketing_experiments: ["Review marketing-specific experiments.", "marketing experiments tests"],
    control_room: ["Open the existing operational control interface.", "control room operations"],
    metabolism: ["Inspect autonomous maintenance and recorded changes.", "autonomy maintenance organism history"],
    codex: ["Review Codex research status and available evidence.", "codex research provider capacity"],
    cost: ["Inspect estimated AI usage costs, separate from billed spend.", "ai cost spend budget usage estimates"],
    content: ["Check generated pages, sizes and site inventory.", "site inventory pages links content"],
    site_gate: ["Inspect site-access rules and country restrictions.", "access country block allow site gate restrictions"],
    features: ["Review feature flags before changing site behavior.", "feature flags toggles configuration"],
    brief: ["Review AI Brief settings and regeneration intervals.", "ai brief settings regenerate"],
    vector: ["Inspect the existing BTC override controls.", "btc bitcoin vector override"],
  };
  function normalize(value) {
    return String(value || "").normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim().replace(/\s+/g, " ");
  }
  function createCatalog(groups) {
    const seen = new Set(), catalog = [];
    for (const group of Array.isArray(groups) ? groups : []) {
      for (const item of Array.isArray(group.items) ? group.items : []) {
        const [id, label] = item;
        if (typeof id !== "string" || !/^[a-z][a-z0-9_]*$/.test(id) || seen.has(id)) continue;
        seen.add(id);
        const detail = Object.prototype.hasOwnProperty.call(DETAILS, id) ? DETAILS[id] : ["Open this tool in " + group.label + ".", ""];
        catalog.push({id, label: String(label), group: String(group.label), primary: !!group.primary,
          description: detail[0], keywords: normalize([label, id.replaceAll("_", " "), group.label, ...detail].join(" "))});
      }
    }
    return catalog;
  }
  function search(catalog, query) {
    const q = normalize(query), terms = q.split(" ").filter(Boolean);
    if (!q) return catalog.slice();
    return catalog.filter(item => terms.every(term => item.keywords.includes(term)))
      .map((item, index) => ({item, index, rank: normalize(item.label) === q ? 0 : normalize(item.label).startsWith(q) ? 1 : normalize(item.label).includes(q) ? 2 : 3}))
      .sort((a, b) => a.rank - b.rank || a.index - b.index).map(row => row.item);
  }
  function sanitizePreferences(value, catalog) {
    const empty = {version: 1, pins: [], recent: []};
    if (!value || value.version !== 1) return empty;
    const allowed = new Set(catalog.map(item => item.id));
    const clean = (items, limit, excludeHome) => Array.isArray(items)
      ? [...new Set(items.filter(id => typeof id === "string" && allowed.has(id) && (!excludeHome || id !== "overview")))].slice(0, limit) : [];
    return {version: 1, pins: clean(value.pins, MAX_PINS, false), recent: clean(value.recent, MAX_RECENT, true)};
  }
  function togglePin(value, id, catalog) {
    const state = sanitizePreferences(value, catalog);
    if (!catalog.some(item => item.id === id)) return state;
    state.pins = state.pins.includes(id) ? state.pins.filter(item => item !== id)
      : state.pins.length < MAX_PINS ? [...state.pins, id] : state.pins;
    return state;
  }
  function visit(value, id, catalog) {
    const state = sanitizePreferences(value, catalog);
    if (id !== "overview" && catalog.some(item => item.id === id)) state.recent = [id, ...state.recent.filter(item => item !== id)].slice(0, MAX_RECENT);
    return state;
  }
  function readState(state, now = Date.now()) {
    const time = state.lastSuccess;
    const valid = Number.isFinite(time) && time > 0 && time <= now + 5000;
    if (state.pending) return {kind: "loading", label: "Reading status…"};
    if (state.error) return {kind: "failed", label: valid ? "Refresh failed · previous snapshot shown" : "Status could not be read"};
    if (!valid) return {kind: "unknown", label: "Status has not been read"};
    const minutes = Math.max(0, Math.floor((now - time) / 60000));
    return {kind: minutes >= 5 ? "old" : "current", label: minutes === 0 ? "Status read just now" : `Status read ${minutes} min ago`};
  }
  const model = {createCatalog, search, sanitizePreferences, togglePin, visit, readState};
  if (typeof module !== "undefined" && module.exports) module.exports = model;
  if (!root.document) return;

  const doc = root.document;
  const escape = value => String(value).replace(/[&<>"']/g, character => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[character]));
  let catalog = [], prefs = {version: 1, pins: [], recent: []}, current = "overview", options = null;
  let dialog, priorFocus, results = [], selected = 0, activeFilter = "all", initialized = false, storageAvailable = true;
  let observation = {lastSuccess: 0, pending: false, error: false};
  function announce(message) { const node = doc.getElementById("workspaceAnnouncement"); if (node) node.textContent = message; }
  function save() {
    try { root.localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs)); }
    catch (_) { storageAvailable = false; announce("Browser storage is unavailable. Preferences last for this visit only."); }
  }
  function routeButton(item, className) {
    return `<button type="button" class="${className}" data-workspace-page="${escape(item.id)}">${options.icons[item.id] || ""}<span>${escape(item.label)}</span></button>`;
  }
  function wireNavigation(host) {
    host.querySelectorAll("[data-workspace-page]").forEach(button => {
      button.addEventListener("click", () => navigate(button.dataset.workspacePage));
    });
  }
  function navigate(id) {
    if (!catalog.some(item => item.id === id)) return;
    if (dialog.open) dialog.close();
    options.navigate(id);
  }
  function paintPins() {
    const nav = doc.getElementById("sidenav");
    let host = doc.getElementById("workspacePins");
    if (!host && nav) { host = doc.createElement("section"); host.id = "workspacePins"; host.className = "workspace-pins"; nav.querySelector(".nav-search").after(host); }
    if (!host) return;
    host.hidden = prefs.pins.length === 0;
    host.innerHTML = `<div class="eyebrow">Pinned by you</div>${prefs.pins.map(id => routeButton(catalog.find(item => item.id === id), "workspace-pin")).join("")}`;
    host.querySelectorAll("button").forEach(button => { if (button.dataset.workspacePage === current) button.setAttribute("aria-current", "page"); });
    wireNavigation(host);
  }
  function paintPage() {
    const item = catalog.find(row => row.id === current);
    if (!item) return;
    const context = doc.getElementById("workspaceContext"), description = doc.getElementById("workspaceDescription"), pin = doc.getElementById("workspacePin");
    context.textContent = item.group;
    doc.getElementById("workspaceToolbar").dataset.page = current;
    description.textContent = item.description;
    const pinned = prefs.pins.includes(current);
    pin.setAttribute("aria-pressed", String(pinned));
    pin.setAttribute("aria-label", `${pinned ? "Unpin" : "Pin"} ${item.label}`);
    pin.textContent = pinned ? "★ Pinned" : "☆ Pin page";
    pin.title = pinned ? "Remove from your pinned pages" : `${prefs.pins.length}/${MAX_PINS} pinned · stored only in this browser`;
    doc.title = `${item.label} · Mastermind Admin`;
  }
  function pinCurrent() {
    if (!prefs.pins.includes(current) && prefs.pins.length >= MAX_PINS) { announce("Eight pages are already pinned. Unpin a page first."); return; }
    prefs = togglePin(prefs, current, catalog); save(); paintPins(); paintPage();
    announce(prefs.pins.includes(current) ? "Page pinned in this browser." : "Page unpinned.");
  }
  function setPage(id) {
    if (!catalog.some(item => item.id === id)) return;
    current = id; prefs = visit(prefs, id, catalog); save(); paintPins(); paintPage();
  }
  function resultOrder(items) {
    if (doc.getElementById("workspaceSearch").value.trim() || activeFilter !== "all") return items;
    const order = [...prefs.pins, ...prefs.recent];
    const rank = id => { const i = order.indexOf(id); return i < 0 ? order.length : i; };
    return items.slice().sort((a, b) => rank(a.id) - rank(b.id) || Number(b.primary) - Number(a.primary));
  }
  function highlight() {
    const list = doc.getElementById("workspaceResults"), input = doc.getElementById("workspaceSearch");
    list.querySelectorAll("[role=option]").forEach((row, index) => {
      row.setAttribute("aria-selected", String(index === selected));
      if (index === selected) { input.setAttribute("aria-activedescendant", row.id); row.scrollIntoView({block: "nearest"}); }
    });
    if (!results.length) input.removeAttribute("aria-activedescendant");
  }
  function paintResults() {
    const query = doc.getElementById("workspaceSearch").value;
    let items = search(catalog, query);
    if (activeFilter === "pinned") items = items.filter(item => prefs.pins.includes(item.id));
    else if (activeFilter === "recent") items = items.filter(item => prefs.recent.includes(item.id));
    else if (activeFilter !== "all") items = items.filter(item => item.group === activeFilter);
    results = resultOrder(items); selected = 0;
    const list = doc.getElementById("workspaceResults");
    list.innerHTML = results.map((item, index) => `<div id="workspace-result-${index}" role="option" aria-selected="${index === 0}" class="workspace-result" data-result-index="${index}">${options.icons[item.id] || ""}<span class="workspace-result-copy"><strong>${escape(item.label)}${prefs.pins.includes(item.id) ? '<span class="workspace-pinned-mark" aria-label="Pinned">★</span>' : ""}</strong><span>${escape(item.description)}</span></span><span class="workspace-result-group">${escape(item.group)}</span><span class="workspace-result-arrow" aria-hidden="true">↵</span></div>`).join("");
    list.querySelectorAll("[data-result-index]").forEach(row => {
      row.addEventListener("click", () => navigate(results[Number(row.dataset.resultIndex)].id));
      row.addEventListener("pointermove", () => { const next = Number(row.dataset.resultIndex); if (selected !== next) { selected = next; highlight(); } });
    });
    const empty = doc.getElementById("workspaceEmpty"); empty.hidden = results.length > 0;
    doc.getElementById("workspaceEmptyTitle").textContent = activeFilter === "pinned" && !query ? "No pinned pages yet" : activeFilter === "recent" && !query ? "No recent pages yet" : "No matching tools";
    doc.getElementById("workspaceEmptyHint").textContent = activeFilter === "pinned" && !query ? "Open a page and choose Pin page to keep it close." : "Try another task or choose All tools to reset the filters.";
    doc.getElementById("workspaceResultCount").textContent = `${results.length} of ${catalog.length} tools`;
    doc.querySelectorAll("[data-workspace-filter]").forEach(button => button.setAttribute("aria-pressed", String(button.dataset.workspaceFilter === activeFilter)));
    highlight();
  }
  function open(filter = "all") {
    if (!initialized || doc.getElementById("app").style.display === "none") return;
    options.closeNavigation(); priorFocus = doc.activeElement;
    activeFilter = filter; doc.getElementById("workspaceSearch").value = "";
    doc.getElementById("workspaceGroup").value = catalog.some(item => item.group === filter) ? filter : "all";
    dialog.showModal(); paintResults(); doc.getElementById("workspaceSearch").focus();
  }
  function paintStatus() {
    const host = doc.getElementById("workspaceStatus"), label = doc.getElementById("workspaceStatusText");
    if (!host || !label) return;
    const state = readState(observation);
    host.dataset.state = state.kind; label.textContent = state.label;
    label.title = observation.lastSuccess ? `Last successful console read: ${new Date(observation.lastSuccess).toLocaleString()}. Underlying data timestamps are shown on each page.` : "The console has not received a status snapshot.";
    const button = doc.getElementById("workspaceRefresh"); button.disabled = observation.pending; button.textContent = state.kind === "failed" ? "Retry status" : "Refresh status";
    const health = doc.getElementById("adminHealthStatus");
    if (health) {
      if (!health.dataset.snapshotLabel) health.dataset.snapshotLabel = health.innerHTML;
      if (state.kind === "failed" || state.kind === "old") health.innerHTML = `<span class="led warn"></span>${state.kind === "failed" ? "Read failed" : "Older snapshot"}`;
      else if (state.kind === "loading") health.innerHTML = `<span class="led warn"></span>Reading status`;
      else health.innerHTML = health.dataset.snapshotLabel;
    }
  }
  function beginStatus() { observation.pending = true; paintStatus(); }
  function statusReceived() { observation = {lastSuccess: Date.now(), pending: false, error: false}; paintStatus(); }
  function statusFailed() { observation.pending = false; observation.error = true; paintStatus(); }
  async function refreshStatus() {
    if (observation.pending) return;
    try { await options.refresh(); announce("Status read completed. Underlying data timestamps remain separate."); }
    catch (_) { announce("Status refresh failed. The previous snapshot is retained."); }
  }
  function init(config) {
    options = config;
    if (initialized) { paintPins(); paintPage(); paintStatus(); return; }
    initialized = true; catalog = createCatalog(config.groups);
    doc.body.classList.add("workspace-ready");
    try { prefs = sanitizePreferences(JSON.parse(root.localStorage.getItem(STORAGE_KEY)), catalog); }
    catch (_) { prefs = sanitizePreferences(null, catalog); storageAvailable = false; }
    dialog = doc.createElement("dialog"); dialog.id = "workspaceDialog"; dialog.className = "workspace-dialog";
    dialog.setAttribute("aria-labelledby", "workspaceDialogTitle");
    dialog.innerHTML = `<div class="workspace-dialog-heading"><div><div class="eyebrow">Your admin workspace</div><h2 id="workspaceDialogTitle">Find the right tool</h2></div><button type="button" class="workspace-close" id="workspaceClose" aria-label="Close tool search">✕</button></div><div class="workspace-search-wrap"><label class="admin-sr-only" for="workspaceSearch">Search admin tools by name or task</label><input id="workspaceSearch" type="search" autocomplete="off" placeholder="Search a task, page or tool…" role="combobox" aria-expanded="true" aria-controls="workspaceResults" aria-autocomplete="list"></div><div class="workspace-filters" aria-label="Filter tools"><button type="button" data-workspace-filter="all" aria-pressed="true">All tools</button><button type="button" data-workspace-filter="pinned" aria-pressed="false">Pinned</button><button type="button" data-workspace-filter="recent" aria-pressed="false">Recent</button><label class="admin-sr-only" for="workspaceGroup">Tool area</label><select id="workspaceGroup"><option value="all">Every area</option>${[...new Set(catalog.map(item => item.group))].map(group => `<option value="${escape(group)}">${escape(group)}</option>`).join("")}</select></div><div id="workspaceResults" role="listbox" aria-label="Admin tools"></div><div id="workspaceEmpty" class="workspace-empty" hidden><strong id="workspaceEmptyTitle"></strong><p id="workspaceEmptyHint"></p><button type="button" class="btn" id="workspaceReset">Show all tools</button></div><footer class="workspace-dialog-footer"><span id="workspaceResultCount" role="status"></span><span><kbd>↑</kbd><kbd>↓</kbd> move <kbd>Enter</kbd> open <kbd>Esc</kbd> close</span></footer><p class="workspace-privacy">Pins and recent pages stay in this browser. Search opens tools; it never runs an admin action.</p>`;
    doc.body.appendChild(dialog);
    doc.getElementById("workspaceClose").onclick = () => dialog.close();
    dialog.addEventListener("close", () => { if (priorFocus && priorFocus.isConnected && !priorFocus.closest("[inert]")) priorFocus.focus(); });
    dialog.addEventListener("click", event => { if (event.target === dialog) { const rect = dialog.getBoundingClientRect(); if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close(); } });
    const input = doc.getElementById("workspaceSearch");
    input.addEventListener("input", paintResults);
    input.addEventListener("keydown", event => {
      if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); dialog.close(); return; }
      if (event.key === "ArrowDown" || event.key === "ArrowUp") { event.preventDefault(); if (results.length) { selected = (selected + (event.key === "ArrowDown" ? 1 : -1) + results.length) % results.length; highlight(); } }
      if (event.key === "Enter" && results[selected]) { event.preventDefault(); navigate(results[selected].id); }
    });
    const reset = () => { activeFilter = "all"; input.value = ""; doc.getElementById("workspaceGroup").value = "all"; paintResults(); input.focus(); };
    doc.getElementById("workspaceReset").onclick = reset;
    doc.getElementById("workspaceGroup").addEventListener("change", event => { activeFilter = event.target.value; paintResults(); input.focus(); });
    dialog.querySelectorAll("[data-workspace-filter]").forEach(button => button.addEventListener("click", () => { activeFilter = button.dataset.workspaceFilter; doc.getElementById("workspaceGroup").value = "all"; paintResults(); input.focus(); }));
    doc.getElementById("workspaceOpen").onclick = () => open();
    doc.getElementById("workspacePin").onclick = pinCurrent;
    doc.getElementById("workspaceRefresh").onclick = refreshStatus;
    doc.addEventListener("keydown", event => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k" && !event.altKey) {
        if (doc.getElementById("app").style.display === "none") return;
        event.preventDefault(); if (dialog.open) dialog.close(); else open();
      }
    });
    root.setInterval(() => { if (!doc.hidden) paintStatus(); }, 30000);
    doc.addEventListener("visibilitychange", () => { if (!doc.hidden) paintStatus(); });
    paintPins(); paintPage(); paintStatus();
    if (!storageAvailable) announce("Browser preferences are unavailable. Navigation remains available.");
  }
  function close() { if (dialog && dialog.open) dialog.close(); }
  root.AdminWorkspace = {...model, init, setPage, open, close, beginStatus, statusReceived, statusFailed};
})(typeof globalThis !== "undefined" ? globalThis : this);
