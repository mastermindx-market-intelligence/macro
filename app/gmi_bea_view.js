/* BEA human view: one canonical API, no alternate publication or source owner.
 * CommonJS exports exist for hermetic tests. Production mounts only the refusal
 * controller. Research charts consume the REAL nonpublic candidate vocabulary;
 * no invented published status is accepted or manufactured here.
 */
(function (factory) {
  "use strict";
  const view = factory();
  if (typeof module === "object" && module.exports) { module.exports = view; return; }
  view.applyTheme(document, window);
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => view.mount(document, window), {once: true});
  else view.mount(document, window);
})(function () {
  "use strict";
  /* BEGIN BEA SOURCE CONTRACT — tests pin this projection to the Python owner. */
  const CONTRACT = {"schema":"market_ontology.bea_gvc_current_descriptive/v1","edition":"2026-05-21","years":[2017,2018,2019,2020,2021,2022,2023,2024],"regions":["canada","china","europe","japan","mexico","rest_of_asia_and_pacific","rest_of_world"],"candidateStatus":"CANDIDATE_NOT_PUBLISHED","unavailableStatus":"UNAVAILABLE","authority":"internal_descriptive_candidate_only","numberKind":"integer_usd_millions","maxInteger":9007199254740991,"commoditiesPerYear":139};
  /* END BEA SOURCE CONTRACT */
  const REASONS = {
    ANNUAL_AMOUNT_EXCEEDS_JSON_SAFE_INTEGER: ["Source values need review", "An annual total exceeds the exact numeric range supported by this view."],
    ANNUAL_CHANGE_EXCEEDS_JSON_SAFE_INTEGER: ["Source values need review", "An annual change cannot be represented exactly. No rounded substitute is shown."],
    COMMODITY_IDENTITY_DRIFT: ["Source identity needs review", "The commodity identities do not align across accounting years."],
    DUPLICATE_SOURCE_REGISTRY_ID: ["Source registration needs review", "More than one registry entry claims this source. The ambiguous record is withheld."],
    INCOMPLETE_COMMODITY_YEARS: ["Source coverage is incomplete", "The complete set of commodity rows and accounting years is not available."],
    ORIGINAL_RESPONSE_LINEAGE_UNBOUND: ["Source evidence is incomplete", "The original BEA response and capture references have not been consistently bound."],
    OWNER_VIEW_BYTES_MISSING_OR_OVERSIZED: ["Industry view not available", "A complete, owner-verified industry view has not been provided."],
    SOURCE_AMOUNTS_INVALID: ["Source values need review", "One or more source amounts do not match the declared whole-million accounting format."],
    SOURCE_AMOUNT_EXCEEDS_JSON_SAFE_INTEGER: ["Source values need review", "A source amount exceeds the exact numeric range supported by this view."],
    SOURCE_ANNUAL_RESPONSE_DRIFT: ["Source evidence needs review", "Rows within an accounting year refer to different original responses."],
    SOURCE_CONTRACT_NOT_BOUND: ["Source contract is incomplete", "The original and normalized source records are not bound to the required Data OS contract."],
    SOURCE_GRAIN_OR_IDENTITY_INVALID: ["Source identity needs review", "The industry, commodity or accounting-year identifiers do not match the requested view."],
    SOURCE_INDUSTRY_NAME_DRIFT_WITHIN_YEAR: ["Industry label needs review", "Conflicting publisher labels were found within one accounting year."],
    SOURCE_INDUSTRY_NAME_INVALID: ["Industry label needs review", "The source label is missing or cannot be presented safely."],
    SOURCE_NOT_PRODUCED: ["Not yet available", "Mastermind has not admitted the original inputs and normalized industry views as a produced source."],
    SOURCE_PRODUCER_OR_LINEAGE_DRIFT: ["Source generation needs review", "The rows do not share one consistent producer and source lineage."],
    SOURCE_PROVENANCE_OR_AUTHORITY_INVALID: ["Source evidence needs review", "Source generation, native observation or usage limits do not agree. Figures remain withheld."],
    SOURCE_QUALITY_FLAG_DRIFT: ["Accounting quality needs review", "Reported quality flags do not match the signed source amounts."],
    SOURCE_RIGHTS_NOT_GRANTED: ["Source permissions not qualified", "The required source-use permissions have not been granted under the BEA decision."],
    SOURCE_SCOPE_UNQUALIFIED: ["Source scope not qualified", "The registered use scope does not match this current-descriptive BEA view."],
    SOURCE_SIGNED_ACCOUNTING_INVALID: ["Accounting does not reconcile", "Regional allocations and world imports do not meet the source's rounding limits."],
    SOURCE_UNREGISTERED: ["Not yet available", "This edition is not registered as a complete native BEA source. No figures are substituted."],
    SOURCE_VIEW_DIGEST_MISMATCH: ["Source integrity needs review", "The industry bytes do not match the expected source digest."],
    VIEW_FRAMING_INVALID: ["Source format needs review", "The industry file does not meet the declared source framing contract."],
    VIEW_ROW_FRAMING_INVALID: ["Source format needs review", "One or more industry rows are missing or exceed the declared format bound."],
    VIEW_ROW_MALFORMED: ["Source format needs review", "The industry data cannot be parsed without changing its meaning."]
  };
  const LABELS = ["Canada", "China", "Europe", "Japan", "Mexico", "Rest of Asia / Pacific", "Rest of world"];
  const UNAVAILABLE_FIELDS = ["annual_descriptive","authority_ceiling","industry_code_exact","may_publish","may_rank","may_trade","native_ingested_at","publication_precision","publisher_edition_date","reason","rows_examined","schema","source_generation_id","status"];
  const CANDIDATE_FIELDS = ["annual_comparison_basis","annual_descriptive","attribution","authority_ceiling","canonical_security_id","historical_availability_null_reason","historical_pit_eligible","industry_code_exact","industry_display_name","industry_display_name_state","industry_names_by_accounting_year","legacy_mapping_state","may_publish","may_rank","may_trade","measurement_class","native_ingested_at","owner_digest_is_not_authenticated_here","owner_expected_view_sha256_claim","producer_code_sha256","publication_precision","publisher_edition_date","reason","rows_examined","schema","source_generation_id","source_lineage_sha256","status"];
  const AMOUNTS = ["total_use_million_USD", "world_import_million_USD", ...CONTRACT.regions.map(r => r + "_import_million_USD"), "region_rounding_difference_million_USD"];
  const QUALITY = ["negative_region_adjustment_commodities", "nonpositive_world_commodities", "rounding_residual_commodities"];
  const codePattern = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,31}(?![\s\S])/;
  const hex = /^[0-9a-f]{64}(?![\s\S])/;
  const format = new Intl.NumberFormat("en-US", {maximumFractionDigits: 0});
  const fmt = n => format.format(n).replace(/^-/, "−");
  const signed = n => (n > 0 ? "+" : "") + fmt(n);
  const plainObject = o => o !== null && typeof o === "object" && !Array.isArray(o);
  const exactKeys = (o, keys) => plainObject(o) && Object.keys(o).sort().join("|") === [...keys].sort().join("|");
  const safeName = s => typeof s === "string" && s.trim().length > 0 && s.length <= 256 && !/[\p{Cc}\p{Cf}\p{Cs}\p{Zl}\p{Zp}]/u.test(s);
  function sourceCode(path) {
    const match = /^\/api\/gmi\/bea\/industry\/([^/]+)\/view$/.exec(path);
    if (!match) return null;
    try { const code = decodeURIComponent(match[1]); return codePattern.test(code) ? code : null; }
    catch (_e) { return null; }
  }
  function unavailable(packet, code) {
    return exactKeys(packet, UNAVAILABLE_FIELDS) && packet.schema === CONTRACT.schema && packet.status === CONTRACT.unavailableStatus && packet.industry_code_exact === code && packet.authority_ceiling === CONTRACT.authority && packet.may_publish === false && packet.may_rank === false && packet.may_trade === false && packet.publication_precision === "DAY" && packet.publisher_edition_date === CONTRACT.edition && packet.rows_examined === 0 && packet.source_generation_id === null && packet.native_ingested_at === null && Array.isArray(packet.annual_descriptive) && packet.annual_descriptive.length === 0 && Object.hasOwn(REASONS, packet.reason);
  }
  function validateCandidate(p) {
    if (!exactKeys(p, CANDIDATE_FIELDS) || p.schema !== CONTRACT.schema || p.status !== CONTRACT.candidateStatus || p.authority_ceiling !== CONTRACT.authority || p.may_publish !== false || p.may_rank !== false || p.may_trade !== false || p.historical_pit_eligible !== false || p.owner_digest_is_not_authenticated_here !== true || p.canonical_security_id !== null || p.reason !== "OWNER_AUTHENTICATION_AND_RUNTIME_RELEASE_UNPROVEN" || p.publisher_edition_date !== CONTRACT.edition || p.publication_precision !== "DAY" || typeof p.industry_code_exact !== "string" || !codePattern.test(p.industry_code_exact) || p.rows_examined !== 1112 || p.annual_comparison_basis !== "RETROSPECTIVE_2026_VINTAGE_NOT_ORIGINAL_HISTORICAL_KNOWLEDGE" || p.measurement_class !== "IMPUTED_INDUSTRY_IMPORT_ALLOCATION_NOT_COMPANY_SUPPLY_CHAINS" || p.historical_availability_null_reason !== "HISTORICAL_AVAILABILITY_UNVERIFIED") return false;
    for (const key of ["source_generation_id", "source_lineage_sha256", "producer_code_sha256", "owner_expected_view_sha256_claim"]) if (typeof p[key] !== "string" || !hex.test(p[key])) return false;
    if (typeof p.native_ingested_at !== "string" || !/(Z|[+-]\d\d:\d\d)(?![\s\S])/.test(p.native_ingested_at) || !Number.isFinite(Date.parse(p.native_ingested_at)) || Date.parse(p.native_ingested_at) < Date.parse(CONTRACT.edition + "T00:00:00Z") || Date.parse(p.native_ingested_at) > Date.now()) return false;
    if (p.attribution !== "Source: U.S. Bureau of Economic Analysis" || p.legacy_mapping_state !== (p.industry_code_exact === "5241X" ? "UNRESOLVED_5241X_VS_5241XX" : "NOT_APPLIED")) return false;
    if (!exactKeys(p.industry_names_by_accounting_year, CONTRACT.years.map(String)) || !Object.values(p.industry_names_by_accounting_year).every(safeName)) return false;
    const stable = new Set(Object.values(p.industry_names_by_accounting_year)).size === 1;
    if (p.industry_display_name !== (stable ? p.industry_names_by_accounting_year["2017"] : null) || p.industry_display_name_state !== (stable ? "EXACT_SOURCE_LABEL_STABLE" : "SOURCE_LABELS_VARY_ACROSS_YEARS")) return false;
    if (!Array.isArray(p.annual_descriptive) || p.annual_descriptive.length !== 8) return false;
    let previous = null;
    for (let i = 0; i < 8; i++) {
      const row = p.annual_descriptive[i];
      if (!exactKeys(row, ["accounting_year", "quality", "year_over_year_change_million_USD", ...AMOUNTS]) || row.accounting_year !== CONTRACT.years[i] || !AMOUNTS.every(k => Number.isSafeInteger(row[k])) || !exactKeys(row.quality, QUALITY) || !QUALITY.every(k => Number.isInteger(row.quality[k]) && row.quality[k] >= 0 && row.quality[k] <= 139)) return false;
      const residual = BigInt(row.world_import_million_USD) - CONTRACT.regions.reduce((sum, r) => sum + BigInt(row[r + "_import_million_USD"]), 0n);
      if (residual !== BigInt(row.region_rounding_difference_million_USD) || Math.abs(row.region_rounding_difference_million_USD) > 3 * row.quality.rounding_residual_commodities) return false;
      const delta = row.year_over_year_change_million_USD;
      if (previous === null ? delta !== null : (!exactKeys(delta, AMOUNTS) || !AMOUNTS.every(k => Number.isSafeInteger(delta[k]) && BigInt(delta[k]) === BigInt(row[k]) - BigInt(previous[k])))) return false;
      previous = row;
    }
    return true;
  }
  function failure(status, body, code) {
    if (status === 401) return {tone: "pending", tag: "Session required", title: "Your session has expired", message: "Return to Mastermind and sign in again. No industry values have been loaded.", reason: "AUTHENTICATION_REQUIRED", access: true};
    if (status === 403) return {tone: "pending", tag: "Access required", title: "Premium access required", message: "An active site-full entitlement is required for this research workspace.", reason: "ENTITLEMENT_REQUIRED", access: true};
    if (status === 422) return {tone: "error", tag: "Check the request", title: "Use an exact industry code", message: "Enter the publisher's case-sensitive code. Historical or other query parameters are not supported.", reason: "INVALID_REQUEST"};
    if (status === 503 && unavailable(body, code)) { const [title, message] = REASONS[body.reason]; return {tone: "pending", tag: "Source unavailable", title, message, reason: body.reason}; }
    if (status === 200 && body && body.status === CONTRACT.candidateStatus) return {tone: "pending", tag: "Not released", title: "Research candidate—not published", message: "A nonpublic candidate cannot be displayed as admitted industry data. Figures remain withheld.", reason: "CANDIDATE_NOT_PUBLISHED"};
    if (status === 503 && plainObject(body) && plainObject(body.detail) && ["BEA_SOURCE_REGISTRY_UNAVAILABLE", "BEA_NATIVE_OWNER_READ_NOT_ADMITTED"].includes(body.detail.error)) return {tone: "error", tag: "Service unavailable", title: "Source service temporarily unavailable", message: "The source owner could not provide a qualified response. Try checking again later.", reason: body.detail.error};
    if (status === 503 && body && body.status === CONTRACT.unavailableStatus) return {tone: "error", tag: "Response withheld", title: "Source response could not be verified", message: "The response does not match the requested industry's source contract. No figures are shown.", reason: "RESPONSE_CONTRACT_MISMATCH"};
    if (status >= 500) return {tone: "error", tag: "Service unavailable", title: "Source service temporarily unavailable", message: "The service returned an error. No older or estimated values have been substituted.", reason: "SERVICE_ERROR"};
    return {tone: "error", tag: "Response withheld", title: "Source response could not be verified", message: "The response does not match this view's declared contract. No figures are shown.", reason: "RESPONSE_CONTRACT_MISMATCH"};
  }
  function applyTheme(doc, host) {
    let theme;
    try { theme = host.localStorage.getItem("theme"); } catch (_e) { /* storage can be disabled */ }
    if (theme !== "light" && theme !== "dark") theme = host.matchMedia && host.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    doc.documentElement.setAttribute("data-theme", theme);
    return theme;
  }
  function element(doc, tag, className, text) {
    const n = doc.createElement(tag); if (className) n.className = className;
    if (text !== undefined) n.textContent = String(text); return n;
  }
  function scale(values, extent) {
    const max = Math.max(1, ...values.map(Math.abs));
    return value => value === 0 ? 0 : Math.abs(value) / max * extent;
  }
  function state(doc, s) {
    const byId = id => doc.getElementById(id);
    byId("bea-data-deck").hidden = true; byId("bea-empty-context").hidden = false;
    byId("bea-state-card").dataset.tone = s.tone;
    byId("bea-state-card").setAttribute("aria-busy", String(s.tone === "loading"));
    byId("bea-state-title").textContent = s.title;
    byId("bea-state-detail").textContent = s.message;
    byId("bea-status-tag").textContent = s.tag;
    byId("bea-reason-code").textContent = s.reason || "CHECK_IN_PROGRESS";
    byId("bea-source-state").textContent = s.tone === "loading" ? "Checking" : s.reason === "SOURCE_NOT_PRODUCED" ? "Not produced" : s.reason === "SOURCE_UNREGISTERED" ? "Not registered" : Object.hasOwn(REASONS, s.reason || "") ? "Unavailable" : "Not confirmed";
    byId("bea-account-action").hidden = !s.access;
    byId("bea-account-action").href = s.reason === "AUTHENTICATION_REQUIRED" ? "/intelligence_hub.html" : "/plans.html";
    byId("bea-account-action").textContent = s.reason === "AUTHENTICATION_REQUIRED" ? "Return to Mastermind" : "Review access";
    byId("bea-generation").textContent = "Not available";
    byId("bea-retry").disabled = s.tone === "loading";
  }
  // Testable visual component of a REAL NONPUBLIC candidate. Never called by
  // mount() or fetch handling; it always carries an unpublished warning.
  function renderResearchPreview(doc, packet) {
    if (!validateCandidate(packet)) throw new Error("INVALID_NONPUBLIC_CANDIDATE");
    const byId = id => doc.getElementById(id);
    state(doc, {tone: "pending", tag: "Unpublished research", title: "Research preview—not released", message: "These figures belong to a nonpublic research candidate. They are not an admitted source or a trading signal.", reason: CONTRACT.candidateStatus});
    byId("bea-empty-context").hidden = true; byId("bea-data-deck").hidden = false;
    byId("bea-active-code").textContent = packet.industry_code_exact;
    byId("bea-code").value = packet.industry_code_exact;
    byId("bea-generation").textContent = packet.source_generation_id + " · candidate only";
    byId("bea-source-state").textContent = "Unpublished candidate";
    byId("bea-name-variation").hidden = packet.industry_display_name_state === "EXACT_SOURCE_LABEL_STABLE";
    const years = byId("bea-years"); const history = byId("bea-trend");
    years.replaceChildren(); history.replaceChildren(); byId("bea-values-body").replaceChildren();
    const height = scale(packet.annual_descriptive.map(r => r.world_import_million_USD), 59);
    let activeYear = 2024;
    let regionalMode = "amounts";
    function paint(year, moveFocus) {
      activeYear = year;
      const row = packet.annual_descriptive[year - 2017];
      byId("bea-year-name").textContent = packet.industry_names_by_accounting_year[String(year)];
      byId("bea-world").textContent = fmt(row.world_import_million_USD);
      byId("bea-total-use").textContent = fmt(row.total_use_million_USD);
      byId("bea-yoy-label").textContent = year === 2017 ? "Change from previous year" : "Change from " + (year - 1);
      byId("bea-yoy").textContent = row.year_over_year_change_million_USD === null ? "Not available" : signed(row.year_over_year_change_million_USD.world_import_million_USD);
      for (const group of [years, history]) for (const button of group.querySelectorAll("button")) { const active = Number(button.dataset.year) === year; button.setAttribute("aria-pressed", String(active)); button.tabIndex = active ? 0 : -1; }
      if (moveFocus) moveFocus.querySelector('button[data-year="' + year + '"]').focus();
      const bars = byId("bea-region-bars"); bars.replaceChildren();
      const changes = regionalMode === "changes";
      byId("bea-region-level").setAttribute("aria-pressed", String(!changes));
      byId("bea-region-change").setAttribute("aria-pressed", String(changes));
      byId("bea-negative-legend").textContent = changes ? "Decrease from prior year" : "Negative adjustment";
      byId("bea-positive-legend").textContent = changes ? "Increase from prior year" : "Positive allocation";
      const shift = byId("bea-region-shift");
      shift.hidden = true;
      shift.textContent = "";
      byId("bea-region-title").textContent = changes ? (year === 2017
        ? "Regional change not available" : "Regional changes from " + (year - 1)) : "Regional import allocation";
      byId("bea-region-note").textContent = changes
        ? "Signed differences from the prior accounting year, calculated retrospectively within the May 2026 edition—not observed real-time flows or investment signals."
        : "Bars share a zero baseline. Negative values are accounting adjustments—not negative trade volumes. Same May 2026 vintage.";
      const source = changes ? row.year_over_year_change_million_USD : row;
      if (source === null) {
        shift.hidden = false;
        shift.textContent = "No previous accounting year is available for 2017; no annual change is calculated.";
      } else {
        const values = CONTRACT.regions.map(r => source[r + "_import_million_USD"]);
        const width = scale(values, 48);
        CONTRACT.regions.forEach((region, index) => {
          const value = values[index], r = element(doc, "div", "bar-row");
          const track = element(doc, "span", "track"), bar = element(doc, "span", "bar-fill");
          track.setAttribute("aria-hidden", "true"); bar.dataset.sign = value < 0 ? "negative" : value > 0 ? "positive" : "zero";
          bar.style.setProperty("--size", width(value) + "%"); track.append(bar);
          r.append(element(doc, "span", "bar-title", LABELS[index]), track, element(doc, "span", "bar-value", signed(value))); bars.append(r);
        });
        if (changes) {
          const largest = Math.max(...values.map(v => Math.abs(v)));
          const ties = values.reduce((names, value, index) => {
            if (Math.abs(value) === largest) names.push(LABELS[index]);
            return names;
          }, []);
          shift.hidden = false;
          shift.textContent = largest === 0 ? "No reported regional change from " + (year - 1) + "."
            : ties.length > 1 ? "Equal largest changes: " + ties.join(", ") + "."
            : "Largest reported change: " + ties[0] + " " + signed(values[LABELS.indexOf(ties[0])]) + " USD millions. This describes accounting, not capital rotation.";
        }
      }
      const quality = byId("bea-quality"); quality.replaceChildren();
      for (const [value, caption] of [[row.quality.nonpositive_world_commodities,"Commodities with zero or negative world imports"],[row.quality.negative_region_adjustment_commodities,"Commodities with negative regional adjustments"],[signed(row.region_rounding_difference_million_USD),"USD millions rounding residual · " + row.quality.rounding_residual_commodities + " flagged commodities"]]) {
        const card = element(doc, "div", "quality-item"); card.append(element(doc, "strong", "", value), element(doc, "span", "", caption)); quality.append(card);
      }
    }
    for (const row of packet.annual_descriptive) {
      const year = row.accounting_year, button = element(doc, "button", "", year);
      button.type = "button"; button.dataset.year = year; button.setAttribute("aria-label", "Accounting year " + year); button.addEventListener("click", () => paint(year)); years.append(button);
      const historical = element(doc, "button", "history-year"); historical.type = "button"; historical.dataset.year = year;
      historical.setAttribute("aria-label", year + ": " + signed(row.world_import_million_USD) + " USD millions. Select this year.");
      const plot = element(doc, "span", "history-plot"), bar = element(doc, "span", "history-bar"); plot.setAttribute("aria-hidden", "true");
      bar.dataset.sign = row.world_import_million_USD < 0 ? "negative" : row.world_import_million_USD > 0 ? "positive" : "zero";
      bar.style.setProperty("--height", height(row.world_import_million_USD) + "px"); plot.append(bar);
      historical.append(element(doc, "span", "history-value", signed(row.world_import_million_USD)), plot, element(doc, "span", "history-label", year));
      historical.addEventListener("click", () => paint(year)); history.append(historical);
      const tr = element(doc, "tr"); tr.append(element(doc, "th", "", year)); tr.firstChild.setAttribute("scope", "row");
      for (const value of [signed(row.world_import_million_USD),row.year_over_year_change_million_USD === null ? "Not available" : signed(row.year_over_year_change_million_USD.world_import_million_USD),signed(row.region_rounding_difference_million_USD)]) tr.append(element(doc, "td", "", value));
      byId("bea-values-body").append(tr);
    }
    for (const group of [years, history]) group.addEventListener("keydown", e => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key) || !e.target.dataset.year) return;
      e.preventDefault(); let i = CONTRACT.years.indexOf(Number(e.target.dataset.year));
      i = e.key === "Home" ? 0 : e.key === "End" ? 7 : (i + (e.key === "ArrowRight" ? 1 : -1) + 8) % 8;
      paint(CONTRACT.years[i], group);
    });
    for (const [buttonId, mode] of [["bea-region-level", "amounts"], ["bea-region-change", "changes"]]) {
      byId(buttonId).addEventListener("click", () => {
        if (regionalMode === mode) return;
        regionalMode = mode;
        paint(activeYear);
      });
    }
    paint(2024);
  }
  async function jsonBody(response) {
    if (!String(response.headers.get("content-type") || "").toLowerCase().includes("application/json")) throw new Error("INVALID_RESPONSE_FORMAT");
    const cap = 262144; const length = Number(response.headers.get("content-length")); if (Number.isFinite(length) && length > cap) throw new Error("RESPONSE_TOO_LARGE");
    if (response.body && response.body.getReader) {
      const reader = response.body.getReader(), decoder = new TextDecoder(); let size = 0, text = "";
      while (true) { const part = await reader.read(); if (part.done) break; size += part.value.byteLength; if (size > cap) { await reader.cancel(); throw new Error("RESPONSE_TOO_LARGE"); } text += decoder.decode(part.value, {stream: true}); }
      return JSON.parse(text + decoder.decode());
    }
    const text = await response.text(); if (text.length > cap) throw new Error("RESPONSE_TOO_LARGE"); return JSON.parse(text);
  }
  function mount(doc, host) {
    if (!doc.getElementById("bea-gvc-root")) return;
    const byId = id => doc.getElementById(id); let controller = null, sequence = 0, activeCode = sourceCode(host.location.pathname);
    let disposed = false;
    const themeButton = byId("bea-theme");
    function themeLabel() { themeButton.setAttribute("aria-label", "Switch to " + (doc.documentElement.dataset.theme === "dark" ? "light" : "dark") + " theme"); }
    themeLabel();
    themeButton.addEventListener("click", () => { const theme = doc.documentElement.dataset.theme === "dark" ? "light" : "dark"; doc.documentElement.dataset.theme = theme; try { host.localStorage.setItem("theme", theme); host.localStorage.removeItem("themeAuto"); } catch (_e) {} doc.dispatchEvent(new host.CustomEvent("themechange", {detail: theme})); themeLabel(); });
    host.addEventListener("storage", e => { if (e.key === "theme") { applyTheme(doc, host); themeLabel(); } });
    async function load(code) {
      const request = ++sequence; if (controller) controller.abort();
      if (!codePattern.test(code || "") || host.location.search) { activeCode = null; state(doc, failure(422, null, code)); byId("bea-retry").disabled = true; return; }
      activeCode = code; byId("bea-code").value = code; byId("bea-checked-at").textContent = "";
      state(doc, {tone:"loading", tag:"Checking source", title:"Checking source availability", message:"Verifying the current source status for industry " + code + ". No figures are displayed during this check."});
      controller = new host.AbortController(); const currentController = controller; let timedOut = false;
      const timer = host.setTimeout(() => { timedOut = true; currentController.abort(); }, 10000);
      try {
        const response = await host.fetch("/api/gmi/bea/industry/" + encodeURIComponent(code), {method:"GET", credentials:"same-origin", cache:"no-store", signal:currentController.signal, headers:{Accept:"application/json"}});
        if (request !== sequence || disposed) return;
        let body = null;
        if (![401,403,422].includes(response.status)) { try { body = await jsonBody(response); } catch (_badBody) { if (currentController.signal.aborted) throw _badBody; if (request !== sequence || disposed) return; state(doc, {tone:"error",tag:"Response withheld",title:"The response could not be read",message:"The service returned an invalid or oversized response. No data has been substituted.",reason:"INVALID_RESPONSE_FORMAT"}); return; } }
        if (request !== sequence || disposed) return;
        state(doc, failure(response.status, body, code));
        byId("bea-checked-at").textContent = "Checked " + new Intl.DateTimeFormat("en-US", {hour:"2-digit", minute:"2-digit"}).format(new Date());
      } catch (_error) {
        if (request !== sequence || disposed || (currentController.signal.aborted && !timedOut)) return;
        state(doc, {tone:"error", tag:"Connection unavailable", title:timedOut ? "The availability check timed out" : "Unable to reach the source service", message:"Your previous values have not been reused. Check your connection, then try again.", reason:timedOut ? "REQUEST_TIMEOUT" : "NETWORK_UNAVAILABLE"});
      } finally { host.clearTimeout(timer); if (request === sequence && !disposed) byId("bea-retry").disabled = false; }
    }
    byId("bea-industry-form").addEventListener("submit", e => { e.preventDefault(); const code = byId("bea-code").value.trim(); if (!codePattern.test(code)) { load(null); byId("bea-code").focus(); return; } host.history.pushState(null,"","/api/gmi/bea/industry/"+encodeURIComponent(code)+"/view"); load(code); });
    byId("bea-retry").addEventListener("click", () => load(activeCode));
    byId("bea-open-evidence").addEventListener("click", () => { const panel = byId("bea-evidence"); panel.open = true; panel.querySelector("summary").focus(); panel.scrollIntoView({behavior:host.matchMedia && host.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",block:"nearest"}); });
    byId("bea-copy-source").addEventListener("click", async () => { const text = "U.S. Bureau of Economic Analysis | May 21, 2026 edition | industry code " + (activeCode || "unselected") + " | 2017–2024 retrospective accounting | reason " + byId("bea-reason-code").textContent + " | no trading or historical PIT authority"; try { await host.navigator.clipboard.writeText(text); byId("bea-copy-status").textContent = "Source reference copied."; } catch (_e) { byId("bea-copy-status").textContent = "Clipboard unavailable. The source details remain visible above."; } });
    host.addEventListener("popstate", () => load(sourceCode(host.location.pathname)));
    host.addEventListener("pagehide", () => { disposed = true; if (controller) controller.abort(); });
    host.addEventListener("pageshow", event => { if (event.persisted) { disposed = false; load(sourceCode(host.location.pathname)); } });
    load(activeCode);
    return {load};
  }
  return Object.freeze({CONTRACT, REASONS, UNAVAILABLE_FIELDS, CANDIDATE_FIELDS, AMOUNTS, sourceCode, unavailable, validateCandidate, failure, scale, applyTheme, mount, renderResearchPreview});
});
