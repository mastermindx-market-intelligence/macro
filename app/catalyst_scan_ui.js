/* Mastermind Catalyst — anonymous first value, optional verified update.
 * Session 00 UI adapter. Public claims and links originate ONLY from the
 * server's rights-gated /api/catalyst/scan projection. No analytics/senders.
 */
(() => {
  "use strict";
  const get = (id) => document.getElementById(id);
  const scanForm = get("catalyst-scan-form");
  const results = get("catalyst-results");
  const signup = get("catalyst-optin");
  const verify = get("catalyst-verify");
  const signupForm = get("catalyst-optin-form");
  const verifyForm = get("catalyst-verify-form");
  const status = get("catalyst-status");
  if (!scanForm || !results || !signup || !verify || !signupForm || !verifyForm || !status) return;

  const VALID_TICKER = /^[A-Z][A-Z0-9.-]{0,9}$/;
  const VALID_TOUCH = /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}$/;
  const SCOPE = "catalyst_event_updates/v1";
  const touch = {};
  // Attribution is untrusted campaign metadata, never confirmed partner credit.
  // Read it once, before scan/share navigation. Never read or forward raw PII.
  const urlParams = new URLSearchParams(window.location.search);
  for (const key of ["utm_source", "utm_medium", "utm_campaign", "utm_content"]) {
    const value = urlParams.get(key);
    if (value && VALID_TOUCH.test(value)) touch[key] = value;
  }

  let scanReceipt = get("catalyst-scan-proof")?.value || "";
  let publicRef = "";
  let requestEmail = "";
  let requestSerial = 0;
  let shownAt = window.performance?.now?.() ?? Date.now();

  const setStatus = (message) => { status.textContent = message; };
  const make = (tag, text, className) => {
    const node = document.createElement(tag);
    if (text !== undefined && text !== null) node.textContent = String(text);
    if (className) node.className = className;
    return node;
  };
  const resetOptin = () => {
    scanReceipt = "";
    publicRef = "";
    requestEmail = "";
    signup.hidden = true;
    verify.hidden = true;
    signupForm.reset();
    verifyForm.reset();
  };
  const invite = () => {
    signup.hidden = !scanReceipt;
    verify.hidden = true;
    shownAt = window.performance?.now?.() ?? Date.now();
  };
  const normalized = (raw) => {
    const parts = raw.split(",").map((x) => x.trim().toUpperCase());
    if (!parts.length || parts.length > 10 || parts.some((x) => !VALID_TICKER.test(x))) {
      return null;
    }
    return [...new Set(parts)];
  };
  const list = (parent, heading, entries, field) => {
    if (!Array.isArray(entries) || !entries.length) return;
    parent.append(make("h4", heading));
    const ul = make("ul");
    for (const claim of entries) ul.append(make("li", claim[field]));
    parent.append(ul);
  };
  const render = (data) => {
    results.replaceChildren();
    results.append(make("p", "Evidence checked " + data.as_of_utc + " · " + data.coverage_note));
    for (const entry of data.results || []) {
      const section = make("section");
      section.setAttribute("aria-label", String(entry.ticker));
      section.append(make("h2", entry.ticker + " · " + entry.status));
      if (entry.status !== "SUPPORTED") {
        section.append(make("p", entry.coverage_note || "Not covered by this event."));
        results.append(section);
        continue;
      }
      section.append(make("h3", entry.headline));
      section.append(make("p", "Evidence as of " + entry.as_of_utc +
        " · " + entry.relationship + " · " + entry.correction_state));
      list(section, "What changed", entry.what_changed, "text");
      list(section, "Conditional scenarios — not predictions", entry.scenarios, "trigger");
      list(section, "What would invalidate this reading", entry.invalidators, "text");
      if (Array.isArray(entry.sources) && entry.sources.length) {
        section.append(make("h4", "Independent public sources"));
        const refs = make("ul");
        for (const source of entry.sources) {
          // The server already validated source rights and HTTPS; the UI
          // independently refuses links not matching that public URL class.
          try {
            const parsed = new URL(source.url);
            if (parsed.protocol !== "https:") continue;
            const li = make("li");
            const a = make("a", source.title);
            a.href = parsed.href;
            a.rel = "noopener noreferrer";
            a.target = "_blank";
            li.append(a, make("span", " · published " + source.published_at_utc));
            refs.append(li);
          } catch (_) { /* An invalid source link cannot become a clickable URL. */ }
        }
        section.append(refs);
      }
      if (entry.dossier_path === "/stocks/" + entry.ticker + ".html") {
        const a = make("a", "Public company dossier");
        a.href = entry.dossier_path;
        section.append(a);
      }
      results.append(section);
    }
  };
  const messageForError = (code, task) => {
    if (code === 429) return "Too many attempts. Please try again later.";
    if (code === 503) return task === "scan"
      ? "Qualified public evidence is temporarily unavailable. No result was invented."
      : "Verified updates are not currently available. Your scan remains free.";
    if (code === 413) return "The request is too large.";
    return task === "scan" ? "Check the 1–10 ticker symbols and try again."
      : "Verification could not be completed. Check the fields or try again later.";
  };
  const post = async (path, body) => {
    const response = await fetch(path, {
      method: "POST", credentials: "same-origin", cache: "no-store", redirect: "error",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify(body)
    });
    if (!response.ok) {
      const err = new Error("Request refused");
      err.status = response.status;
      throw err;
    }
    return response.json();
  };

  scanForm.addEventListener("input", () => {
    ++requestSerial;
    resetOptin(); // Changing source interest invalidates the old signed scan.
  });
  scanForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const tickers = normalized(get("catalyst-tickers").value);
    if (!tickers) { setStatus("Enter between one and ten valid ticker symbols."); return; }
    const serial = ++requestSerial;
    resetOptin();
    setStatus("Checking qualified public evidence…");
    const button = get("catalyst-scan-button");
    button.disabled = true;
    try {
      const data = await post("/api/catalyst/scan", {tickers});
      if (serial !== requestSerial) return;
      if (data.schema !== "catalyst.scan/v1" || !Array.isArray(data.results)) {
        throw new Error("Invalid source");
      }
      render(data); // Show the entire supported scan before revealing email.
      scanReceipt = typeof data.scan_receipt === "string" ? data.scan_receipt : "";
      invite();
      const share = new URL(window.location.pathname, window.location.origin);
      share.searchParams.set("tickers", tickers.join(","));
      if (typeof data.event_id === "string") share.searchParams.set("event_id", data.event_id);
      window.history.replaceState(null, "", share.pathname + share.search);
      setStatus(scanReceipt ? "Scan ready. Updates are optional." :
        "Scan ready. Verified updates are not enabled for this evidence.");
    } catch (error) {
      if (serial === requestSerial) {
        resetOptin();
        results.replaceChildren(make("p", "No qualified scan result is available."));
        setStatus(messageForError(error.status, "scan"));
      }
    } finally {
      button.disabled = false;
    }
  });

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!scanReceipt) { setStatus("Get a supported scan first."); return; }
    const email = get("catalyst-email").value.trim();
    if (!get("catalyst-consent").checked || !email) {
      setStatus("Email and explicit update consent are required."); return;
    }
    const button = get("catalyst-optin-button");
    button.disabled = true;
    setStatus("Preparing optional email verification…");
    try {
      const elapsed = (window.performance?.now?.() ?? Date.now()) - shownAt;
      if (elapsed < 3100) await new Promise((resolve) => setTimeout(resolve, 3100 - elapsed));
      const pending = await post("/api/catalyst/optin/request", {
        email, scan_receipt: scanReceipt, scope: SCOPE, consent_checked: true,
        first_touch: touch,
        honeypot: get("catalyst-honeypot").value,
        form_elapsed_ms: Math.max(3100, Math.round((window.performance?.now?.() ?? Date.now()) - shownAt))
      });
      if (pending.status !== "VERIFICATION_REQUIRED" ||
          typeof pending.public_ref !== "string") {
        throw new Error("Verification was not accepted");
      }
      requestEmail = email;
      publicRef = pending.public_ref; // In-memory only; never URL/localStorage.
      signup.hidden = true;
      verify.hidden = false;
      setStatus("Verification requested. Enter the one-time code if it arrives.");
      get("catalyst-code").focus();
    } catch (error) {
      setStatus(messageForError(error.status, "optin"));
    } finally {
      button.disabled = false;
    }
  });

  verifyForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!publicRef || !requestEmail) { setStatus("Request verification again."); return; }
    const otp = get("catalyst-code").value.trim();
    if (!/^[0-9]{6,8}$/.test(otp)) { setStatus("Enter a six- to eight-digit code."); return; }
    const button = get("catalyst-verify-button");
    button.disabled = true;
    setStatus("Checking the one-time code…");
    try {
      const response = await post("/api/catalyst/optin/verify", {
        email: requestEmail, public_ref: publicRef, otp, honeypot: ""
      });
      if (response.status !== "verified" && response.status !== "already_verified") {
        throw new Error("Verification was not confirmed");
      }
      verify.hidden = true;
      requestEmail = "";
      publicRef = "";
      get("catalyst-email").value = "";
      get("catalyst-code").value = "";
      setStatus("Event updates verified. Future messages include an unsubscribe link.");
    } catch (error) {
      setStatus(messageForError(error.status, "verify"));
    } finally {
      button.disabled = false;
    }
  });

  // A first result may have been server-rendered for a shareable URL. Only
  // an actually signed, rights-qualified result reveals optional verification.
  if (scanReceipt) invite();
})();
