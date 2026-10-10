/* Catalyst Loop Session 03 — anonymous-first, no client-side rights or consent authority.
   No user PII, signed receipt, OTP or opaque verification reference enters the URL,
   localStorage, analytics payload or rendered result cards. */
(function () {
  "use strict";

  const SCAN_PATH = "/api/catalyst/scan";
  const REQUEST_PATH = "/api/catalyst/optin/request";
  const VERIFY_PATH = "/api/catalyst/optin/verify";
  const SCOPE = "catalyst_event_updates/v1";
  const TICKER = /^[A-Z][A-Z0-9.-]{0,9}$/;
  const STATUSES = new Set(["SUPPORTED", "RIGHTS_BLOCKED", "NOT_COVERED", "TEMPORARILY_UNAVAILABLE"]);
  const TOKEN_LIMIT = 10;
  const SOURCE_LIMIT = 12;

  const el = (id) => document.getElementById(id);
  const form = el("cs-scan-form");
  if (!form) return;
  // Follow the existing site's persisted appearance preference only. No
  // identity, scan receipt, consent or subscriber state is ever persisted.
  try {
    const preferred = window.localStorage.getItem("theme");
    if (preferred === "dark" || preferred === "light")
      document.documentElement.setAttribute("data-theme", preferred);
  } catch { /* Browser storage may be disabled. The dark default stays usable. */ }

  const input = el("cs-tickers");
  const error = el("cs-scan-error");
  const busy = el("cs-progress");
  const scanSubmit = el("cs-scan-submit");
  const results = el("cs-results");
  const cards = el("cs-result-cards");
  const copy = el("cs-copy-link");
  const optin = el("cs-optin");
  const optinForm = el("cs-optin-form");
  const verifyForm = el("cs-verify-form");
  const email = el("cs-email");
  const consent = el("cs-consent");
  const otp = el("cs-otp");
  const optinStatus = el("cs-optin-status");

  let lastTickers = [];
  // Ephemeral only. Do not put a signed receipt, email or OTP in a DOM attribute.
  let scanReceipt = null;
  let pendingRef = null;
  let pendingEmail = null;
  let formShownAt = 0;
  let activeRequest = null;
  let scanRunning = false;

  const text = (tag, value, cls) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    node.textContent = String(value == null ? "" : value);
    return node;
  };
  const appendLabel = (parent, title) => parent.appendChild(text("h4", title));
  const show = (node, visible) => { node.hidden = !visible; };
  const showError = (message) => {
    error.textContent = message;
    show(error, Boolean(message));
  };
  const feedback = (message, kind) => {
    optinStatus.textContent = message;
    optinStatus.dataset.kind = kind || "info";
    show(optinStatus, Boolean(message));
  };

  const parseTickers = (raw) => {
    if (typeof raw !== "string" || raw.length > 120) throw new Error("Enter 1–10 stock symbols.");
    const names = raw.toUpperCase().trim().split(/[\s,;]+/).filter(Boolean);
    if (!names.length || names.length > TOKEN_LIMIT) throw new Error("Enter between 1 and 10 symbols.");
    if (names.some((name) => !TICKER.test(name))) {
      throw new Error("Use letters, numbers, dots or hyphens in each ticker (maximum 10 characters).");
    }
    if (new Set(names).size !== names.length) throw new Error("Remove duplicate symbols before scanning.");
    return names;
  };

  const utc = (value) => {
    if (typeof value !== "string" || !value || value.length > 48) return "Unverified";
    const date = new Date(value);
    if (!Number.isFinite(date.getTime()) || !/[zZ]|[+-]\d\d:\d\d$/.test(value)) return "Unverified";
    return date.toISOString().replace(".000Z", " UTC");
  };

  const safeExternal = (raw) => {
    if (typeof raw !== "string" || raw.length > 2048) return null;
    const privateKeys = new Set(["email","e_mail","phone","ip","token","access_token",
      "auth","authorization","api_key","apikey","secret","session","user_id",
      "session_id","signature","password","credential","client_secret","jwt","bearer"]);
    const emailPattern = /[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/i;
    try {
      const url = new URL(raw);
      if (url.protocol !== "https:" || url.username || url.password || url.port && url.port !== "443") return null;
      const host = url.hostname.toLowerCase();
      if (!host || host === "localhost" || host === "127.0.0.1" ||
          host.endsWith(".internal") || host.endsWith(".local") || /^[\[?[a-f\d:.]+\]?$/.test(host)) return null;
      let decoded = raw;
      for (let i = 0; i < 4; i++) {
        const parsed = new URL(decoded);
        const pairs = [...new URLSearchParams(parsed.search),
                       ...new URLSearchParams(parsed.hash.startsWith("#") ? parsed.hash.slice(1) : parsed.hash)];
        if (pairs.some(([key]) => privateKeys.has(key.toLowerCase())) ||
            emailPattern.test(decoded) || /[\x00-\x1f\x7f]/.test(decoded)) return null;
        const expanded = decodeURIComponent(decoded);
        if (expanded === decoded) return url.href;
        decoded = expanded;
      }
      // A fifth decoding layer is an unreviewed source URL, not a safe link.
      return null;
    } catch { return null; }
  };

  const listSection = (parent, heading, lines, field) => {
    if (!Array.isArray(lines) || !lines.length) return;
    const safeLines = lines.slice(0, 10).filter((x) => x && typeof x === "object" &&
      typeof x[field] === "string" && x[field].trim());
    if (!safeLines.length) return;
    appendLabel(parent, heading);
    const ul = document.createElement("ul");
    for (const item of safeLines) ul.appendChild(text("li", item[field]));
    parent.appendChild(ul);
  };

  const publicState = (state) => ({
    SUPPORTED: "SOURCE-SUPPORTED",
    RIGHTS_BLOCKED: "RIGHTS-BLOCKED",
    NOT_COVERED: "NOT COVERED",
    TEMPORARILY_UNAVAILABLE: "TEMPORARILY UNAVAILABLE"
  })[state] || "COVERAGE UNKNOWN";

  const renderCard = (item) => {
    const wrap = document.createElement("article");
    wrap.className = "cs-result-card";
    const header = document.createElement("div");
    header.className = "cs-card-header";
    const heading = document.createElement("div");
    heading.appendChild(text("div", item.ticker, "cs-card-ticker"));
    if (item.status === "SUPPORTED" && typeof item.headline === "string") {
      heading.appendChild(text("h3", item.headline));
    }
    header.appendChild(heading);
    const pill = text("span", publicState(item.status), "cs-pill");
    pill.dataset.state = item.status;
    header.appendChild(pill);
    wrap.appendChild(header);
    const meta = document.createElement("div");
    meta.className = "cs-card-meta";
    if (item.status === "SUPPORTED") {
      meta.appendChild(text("span", "RELATION: " + (item.relationship === "DIRECT" ? "DIRECT" : "EVIDENCED INDIRECT")));
      meta.appendChild(text("span", "AS OF: " + utc(item.as_of_utc)));
      meta.appendChild(text("span", "REVISION: " + (item.correction_state === "CORRECTED" ? "CORRECTED" : "CURRENT")));
    } else {
      meta.appendChild(text("span", "NOT AN INVESTMENT CONCLUSION"));
    }
    wrap.appendChild(meta);
    const body = document.createElement("div");
    body.className = "cs-card-body";

    if (item.status !== "SUPPORTED") {
      const reason = ({
        RIGHTS_BLOCKED: "Public display permission is unavailable for this event. Evidence is withheld rather than inferred.",
        NOT_COVERED: "No eligible source-backed relationship was established for this symbol in this scan.",
        TEMPORARILY_UNAVAILABLE: "Qualified event data is temporarily unavailable. Try again later."
      })[item.status];
      body.appendChild(text("p", reason || "Coverage is unavailable.", "cs-unavailable"));
    } else {
      listSection(body, "WHAT CHANGED", item.what_changed, "text");
      if (Array.isArray(item.scenarios) && item.scenarios.length) {
        appendLabel(body, "SCENARIOS TO WATCH · NOT PREDICTIONS");
        const cases = document.createElement("div");
        cases.className = "cs-cases";
        for (const s of item.scenarios.slice(0, 3)) {
          if (!s || typeof s.trigger !== "string" || !["BULL", "BASE", "BEAR"].includes(s.case)) continue;
          const box = document.createElement("div");
          box.className = "cs-case";
          box.dataset.case = s.case;
          box.appendChild(text("strong", s.case));
          box.appendChild(text("p", s.trigger));
          cases.appendChild(box);
        }
        body.appendChild(cases);
      }
      listSection(body, "WHAT WOULD CHALLENGE THIS", item.invalidators, "text");
      appendLabel(body, "PRIMARY SOURCES · UTC");
      const sources = document.createElement("div");
      sources.className = "cs-source-list";
      if (Array.isArray(item.sources)) {
        for (const src of item.sources.slice(0, SOURCE_LIMIT)) {
          if (!src || typeof src !== "object" || src.display_rights !== "ALLOWED") continue;
          const safe = safeExternal(src.url);
          if (!safe) continue;
          const row = document.createElement("div");
          row.className = "cs-source";
          const a = text("a", src.title || "Source document ↗");
          a.href = safe;
          a.target = "_blank";
          a.rel = "noopener noreferrer";
          a.referrerPolicy = "no-referrer";
          row.appendChild(a);
          const dt = text("time", utc(src.published_at_utc));
          if (typeof src.published_at_utc === "string") dt.dateTime = src.published_at_utc;
          row.appendChild(dt);
          sources.appendChild(row);
        }
      }
      body.appendChild(sources);
      const dossier = typeof item.dossier_path === "string" ? item.dossier_path : "";
      if (dossier === "/stocks/" + item.ticker + ".html") {
        const a = text("a", "Open " + item.ticker + " dossier ↗", "cs-dossier-link");
        a.href = dossier;
        body.appendChild(a);
      }
    }
    wrap.appendChild(body);
    return wrap;
  };

  const checkScan = (data, tickers) => {
    if (!data || typeof data !== "object" || data.schema !== "catalyst.scan/v1" ||
        data.schema_version !== 1 || !Array.isArray(data.results) ||
        !Array.isArray(data.requested_tickers) || data.results.length !== tickers.length ||
        tickers.some((name, i) => data.requested_tickers[i] !== name)) {
      throw new Error("The source returned an incompatible scan. No coverage was displayed.");
    }
    if (data.results.some((item, i) => !item || item.ticker !== tickers[i] ||
        !STATUSES.has(item.status))) {
      throw new Error("The source returned incomplete ticker identities. No coverage was displayed.");
    }
    return data;
  };

  const resetSubscriberState = () => {
    scanReceipt = null; pendingRef = null; pendingEmail = null;
    formShownAt = 0;
    email.value = ""; otp.value = ""; consent.checked = false;
    show(verifyForm, false); show(optinForm, true); show(optin, false);
    feedback("", "");
  };

  const displayResults = (data, tickers) => {
    resetSubscriberState();
    lastTickers = tickers.slice();
    cards.replaceChildren();
    const eligible = data.results.filter((item) => item.status === "SUPPORTED");
    for (const item of data.results) cards.appendChild(renderCard(item));
    el("cs-summary-status").textContent = eligible.length + " OF " + tickers.length + " SUPPORTED";
    el("cs-summary-clock").textContent = utc(data.as_of_utc);
    el("cs-summary-event").textContent = data.event_id && Number.isInteger(data.generation) ?
      String(data.event_id).slice(0, 27) + " / " + String(data.generation) : "Not established";
    el("cs-results-note").textContent = data.coverage_note && typeof data.coverage_note === "string" ?
      "Only independently qualified public sources are eligible. " + data.coverage_note.slice(0, 280) :
      "Only independently qualified public sources are eligible. Missing coverage does not imply a neutral market view.";
    show(results, true);
    // Proof is a private client capability. It stays only in a closure and is
    // passed solely to the same-origin, positive-consent owner after disclosure.
    if (eligible.length && typeof data.scan_receipt === "string" &&
        data.scan_receipt.length <= 1024 && data.scan_receipt.length > 20) {
      scanReceipt = data.scan_receipt;
      formShownAt = Date.now();
      show(optin, true);
    } else if (eligible.length) {
      el("cs-results-note").textContent += " Email monitoring is not available for this scan.";
    }
    results.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const api = async (path, payload) => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 14000);
    try {
      const res = await fetch(path, {
        method: "POST", headers: { "Content-Type": "application/json", "Accept": "application/json" },
        cache: "no-store", credentials: "same-origin", redirect: "error",
        referrerPolicy: "no-referrer", signal: controller.signal,
        body: JSON.stringify(payload)
      });
      const json = await res.json().catch(() => null);
      if (!res.ok) {
        const e = new Error(res.status === 429 ? "Rate limit reached. Try again later." :
          res.status === 503 ? "The service is temporarily unavailable; nothing was submitted." :
          res.status === 404 ? "This feature is not enabled yet." :
          res.status === 400 || res.status === 403 || res.status === 409 || res.status === 415 ?
            "The request could not be verified. Review the scan and try again." :
            "Request failed; nothing has been confirmed.");
        e.status = res.status;
        throw e;
      }
      if (!json || typeof json !== "object") throw new Error("An invalid response was received.");
      return json;
    } catch (err) {
      if (err && err.name === "AbortError") throw new Error("The request timed out; nothing is confirmed.");
      throw err;
    } finally {
      clearTimeout(timer);
    }
  };

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (scanRunning) return;
    let tickers;
    try { tickers = parseTickers(input.value); }
    catch (e) { showError(e.message); input.focus(); return; }
    showError("");
    scanRunning = true; scanSubmit.disabled = true;
    show(busy, true); show(results, false); resetSubscriberState();
    cards.replaceChildren();
    try {
      const data = checkScan(await api(SCAN_PATH, { tickers }), tickers);
      displayResults(data, tickers);
    } catch (e) {
      const message = e && typeof e.message === "string" ? e.message : "Evidence is unavailable.";
      showError(message);
    } finally {
      show(busy, false); scanRunning = false; scanSubmit.disabled = false;
    }
  });

  const touch = () => {
    const first = {};
    const params = new URLSearchParams(window.location.search);
    for (const key of ["utm_source", "utm_medium", "utm_campaign", "utm_content", "partner_id"]) {
      const value = params.get(key);
      if (value && /^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$/.test(value)) first[key] = value;
    }
    return first;
  };

  optinForm.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (!scanReceipt) { feedback("Monitoring cannot be requested without a qualified first scan.", "error"); return; }
    if (!email.checkValidity()) { feedback("Enter a valid email address.", "error"); email.focus(); return; }
    if (!consent.checked) { feedback("Explicit event-update consent is required.", "error"); consent.focus(); return; }
    const elapsed = Date.now() - formShownAt;
    if (elapsed < 3000) { feedback("Please review the consent terms before requesting verification.", "error"); return; }
    const button = el("cs-optin-submit");
    button.disabled = true; feedback("Requesting identity verification; no subscription is confirmed yet.", "info");
    try {
      const address = email.value.trim();
      const result = await api(REQUEST_PATH, {
        email: address, scan_receipt: scanReceipt, consent_checked: true,
        scope: SCOPE, form_elapsed_ms: elapsed, honeypot: "", first_touch: touch()
      });
      if (result.status !== "VERIFICATION_REQUIRED" ||
          typeof result.public_ref !== "string" || !/^[A-Za-z0-9_-]{8,128}$/.test(result.public_ref)) {
        throw new Error("The verification owner did not confirm a pending request.");
      }
      pendingRef = result.public_ref; pendingEmail = address;
      show(optinForm, false); show(verifyForm, true);
      feedback("A verification request was accepted. Enter the code if one arrives; delivery is not guaranteed.", "info");
      otp.focus();
    } catch (e) {
      feedback(e.message || "Verification is unavailable; no subscription is confirmed.", "error");
    } finally { button.disabled = false; }
  });

  verifyForm.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (!pendingRef || !pendingEmail) { feedback("No verification request is active.", "error"); return; }
    const code = otp.value.trim();
    if (!/^\d{6,8}$/.test(code)) { feedback("Enter the 6–8 digit code.", "error"); otp.focus(); return; }
    const button = el("cs-verify-submit");
    button.disabled = true;
    feedback("Checking the code and source/consent status...", "info");
    try {
      const response = await api(VERIFY_PATH, { email: pendingEmail, otp: code,
        public_ref: pendingRef, honeypot: "" });
      if (response.status !== "verified" && response.status !== "already_verified") {
        throw new Error("Verification was not confirmed.");
      }
      show(verifyForm, false);
      // Do not retain contact details or verification references after confirmation.
      pendingEmail = null; pendingRef = null; scanReceipt = null; otp.value = ""; email.value = "";
      feedback("Event-scoped verification confirmed. Any later update remains subject to approved evidence, suppression and unsubscribe controls.", "success");
    } catch (e) {
      feedback(e.message || "Verification could not be confirmed.", "error");
    } finally { button.disabled = false; }
  });

  copy.addEventListener("click", async () => {
    if (!lastTickers.length) return;
    // Whitelist ticker names only; discard original query/referrer, email, signed
    // proof, verification handle, OTP and untrusted attribution parameters.
    const url = new URL(window.location.pathname, window.location.origin);
    url.searchParams.set("tickers", lastTickers.join(","));
    try {
      if (!navigator.clipboard || !navigator.clipboard.writeText) throw new Error("clipboard unavailable");
      await navigator.clipboard.writeText(url.toString());
      copy.textContent = "Ticker link copied ✓";
    } catch { copy.textContent = "Clipboard unavailable"; }
  });

  // The form was disabled in source markup. Only enable after all handlers are bound.
  el("cs-scan-controls").disabled = false;
  show(el("cs-js-needed"), false);

  try {
    const initial = new URLSearchParams(window.location.search).get("tickers");
    if (initial) input.value = parseTickers(initial).join(", ");
  } catch { /* Ignore unsafe/unqualified URL input. Never submit automatically. */ }
})();
