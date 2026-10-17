/* Human presentation for the incumbent authenticated BEA GVC API.
 * No source fetch, alternate data store, client-side publication decision or
 * retrospective "as known then" mode. The API remains the only authority.
 */
"use strict";
(() => {
  // Mirror the existing Mastermind site theme preference without loading
  // another theme or account settings service. OS theme remains the fallback.
  try {
    const savedTheme = window.localStorage.getItem("theme");
    if (savedTheme === "light" || savedTheme === "dark") {
      document.documentElement.setAttribute("data-theme", savedTheme);
    }
  } catch (_unavailableStorage) { /* account/theme storage is optional */ }

  const byId = id => document.getElementById(id);
  const codeInput = byId("bea-code");
  const deck = byId("bea-data-deck");
  const heading = byId("bea-state-title");
  const detail = byId("bea-state-detail");
  const period = byId("bea-years");
  const regionsPanel = byId("bea-region-bars");
  const trendPanel = byId("bea-trend");
  const codePattern = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,31}$/;
  const years = [2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024];
  const regionFields = [
    ["canada", "Canada"], ["china", "China"], ["europe", "Europe"],
    ["japan", "Japan"], ["mexico", "Mexico"],
    ["rest_of_asia_and_pacific", "Rest of Asia / Pacific"],
    ["rest_of_world", "Rest of world"]
  ];
  const number = new Intl.NumberFormat(undefined, {maximumFractionDigits: 0, signDisplay: "auto"});
  const regionName = code => code.replace(/_/g, " ");
  const reasonMessages = {
    SOURCE_UNREGISTERED: "This BEA edition has not been registered as a produced native source.",
    SOURCE_NOT_PRODUCED: "The original BEA inputs and normalized industry views are not yet produced.",
    OWNER_VIEW_BYTES_MISSING_OR_OVERSIZED: "A complete owner-verified industry view is not available.",
    SOURCE_RIGHTS_NOT_GRANTED: "The required data rights have not been qualified.",
    SOURCE_CONTRACT_NOT_BOUND: "The complete native source contract has not been accepted."
  };

  function status(title, message) {
    heading.textContent = title;
    detail.textContent = message;
    deck.hidden = true;
  }

  function codeFromPath() {
    try {
      const parts = decodeURIComponent(window.location.pathname).split("/");
      if (parts.length < 7 || parts[parts.length - 1] !== "view") return null;
      const code = parts[parts.length - 2];
      return codePattern.test(code) ? code : null;
    } catch (_error) {
      return null;
    }
  }

  function safeAnnualRow(row, year) {
    if (!row || row.accounting_year !== year) return false;
    if (!Number.isSafeInteger(row.world_import_million_USD)) return false;
    if (!Number.isSafeInteger(row.canada_import_million_USD)) return false;
    if (!Number.isSafeInteger(row.region_rounding_difference_million_USD)) return false;
    for (const [field] of regionFields) {
      if (!Number.isSafeInteger(row[field + "_import_million_USD"])) return false;
    }
    return row.year_over_year_change_million_USD === null ||
      (row.year_over_year_change_million_USD &&
       Number.isSafeInteger(row.year_over_year_change_million_USD.world_import_million_USD));
  }

  // This is deliberately NOT an authorization. It only prevents rendering
  // a malformed response. The server must independently authenticate the
  // produced source generation and paid session before minting a public status.
  function isPublishedCurrent(packet, code) {
    return packet && packet.status === "PUBLISHED_CURRENT_DESCRIPTIVE" &&
      packet.may_publish === true && packet.may_rank === false &&
      packet.may_trade === false && packet.dataos_native_admitted === true &&
      packet.historical_pit_eligible === false &&
      packet.publisher_edition_date === "2026-05-21" &&
      packet.annual_comparison_basis ===
        "RETROSPECTIVE_2026_VINTAGE_NOT_ORIGINAL_HISTORICAL_KNOWLEDGE" &&
      packet.measurement_class === "IMPUTED_INDUSTRY_IMPORT_ALLOCATION_NOT_COMPANY_SUPPLY_CHAINS" &&
      packet.industry_code_exact === code &&
      typeof packet.source_generation_id === "string" &&
      /^[0-9a-f]{64}$/.test(packet.source_generation_id) &&
      Array.isArray(packet.annual_descriptive) &&
      packet.annual_descriptive.length === years.length &&
      packet.industry_names_by_accounting_year &&
      typeof packet.industry_names_by_accounting_year === "object" &&
      years.every(year => {
        const label = packet.industry_names_by_accounting_year[String(year)];
        return typeof label === "string" && label.trim().length > 0 && label.length <= 256;
      }) &&
      packet.annual_descriptive.every((row, i) => safeAnnualRow(row, years[i]));
  }

  function node(tag, name, value) {
    const element = document.createElement(tag);
    if (name) element.className = name;
    if (value !== undefined) element.textContent = String(value);
    return element;
  }

  function paintYear(packet, year) {
    const row = packet.annual_descriptive[year - years[0]];
    byId("bea-world").textContent = number.format(row.world_import_million_USD);
    byId("bea-canada").textContent = number.format(row.canada_import_million_USD);
    byId("bea-year-name").textContent =
      packet.industry_names_by_accounting_year[String(year)];
    const yoy = row.year_over_year_change_million_USD;
    byId("bea-yoy").textContent = yoy ? number.format(yoy.world_import_million_USD) : "—";
    for (const button of period.querySelectorAll("button")) {
      button.setAttribute("aria-pressed", String(Number(button.dataset.year) === year));
    }
    regionsPanel.replaceChildren();
    const max = Math.max(1, ...regionFields.map(([field]) =>
      Math.abs(row[field + "_import_million_USD"])));
    for (const [field, label] of regionFields) {
      const value = row[field + "_import_million_USD"];
      const barRow = node("div", "bar-row");
      barRow.append(node("span", "bar-title", label));
      const track = node("span", "track");
      const fill = node("span", "bar-fill");
      fill.style.width = Math.round(100 * Math.abs(value) / max) + "%";
      if (value < 0) fill.style.background = "var(--warn)";
      track.append(fill);
      barRow.append(track, node("span", "bar-value", number.format(value)));
      regionsPanel.append(barRow);
    }
  }

  function renderPublished(packet) {
    const values = packet.annual_descriptive.map(row => row.world_import_million_USD);
    if (values.some(v => v < 0)) {
      // A bars-from-zero chart of signed-negative values would be misleading.
      trendPanel.replaceChildren(node("span", "state-desc",
        "Signed world-import values include negatives. Inspect the yearly figures instead."));
    } else {
      const max = Math.max(1, ...values);
      trendPanel.replaceChildren();
      values.forEach((value, index) => {
        const item = node("div", "trend-col");
        const bar = node("span", "trend-fill");
        bar.style.height = Math.round(120 * value / max) + "px";
        bar.setAttribute("title", years[index] + ": " + number.format(value) + " USD millions");
        item.append(bar, node("span", "trend-label", String(years[index])));
        trendPanel.append(item);
      });
    }
    period.replaceChildren();
    for (const year of years) {
      const button = node("button", "", year);
      button.type = "button";
      button.dataset.year = String(year);
      button.addEventListener("click", () => paintYear(packet, year));
      period.append(button);
    }
    deck.hidden = false;
    byId("bea-generation").textContent =
      "Native generation " + packet.source_generation_id.slice(0, 12);
    byId("bea-generation").hidden = false;
    status("Verified current edition",
      "Current BEA industry accounting · May 2026 release. Earlier accounting years are retrospective.");
    deck.hidden = false;
    paintYear(packet, years[years.length - 1]);
  }

  byId("bea-industry-form").addEventListener("submit", event => {
    event.preventDefault();
    const code = codeInput.value.trim();
    if (!codePattern.test(code)) {
      status("Invalid industry code", "Use one exact BEA publisher code, without a historical query.");
      codeInput.focus();
      return;
    }
    window.location.assign("/api/gmi/bea/industry/" + encodeURIComponent(code) + "/view");
  });

  const code = codeFromPath();
  if (!code) {
    status("Invalid industry code", "The requested industry code does not match the exact BEA publisher format.");
    return;
  }
  codeInput.value = code;
  status("Checking source availability", "Confirming this industry's current BEA source status.");

  fetch("/api/gmi/bea/industry/" + encodeURIComponent(code), {
    method: "GET",
    credentials: "same-origin",
    cache: "no-store",
    headers: {Accept: "application/json"}
  }).then(async response => {
    if (response.status === 401) {
      status("Sign-in required", "Sign in using your existing Mastermind account to inspect this industry.");
      return;
    }
    if (response.status === 403) {
      status("Premium access required", "This data workspace requires an active Mastermind site-full entitlement.");
      return;
    }
    if (response.status !== 200 && response.status !== 503) {
      status("Data not available", "The current data service cannot qualify this request.");
      return;
    }
    const packet = await response.json();
    if (response.status === 200 && isPublishedCurrent(packet, code)) {
      renderPublished(packet);
      return;
    }
    if (packet && packet.status === "UNAVAILABLE") {
      status("Not yet available", reasonMessages[packet.reason] ||
        "Current BEA industry accounting has not passed the native source release checks.");
      return;
    }
    status("Data not available", "This data is not qualified for presentation.");
  }).catch(() => status("Source temporarily unavailable",
    "The current data service could not be reached. No estimate has been substituted."));
})();
