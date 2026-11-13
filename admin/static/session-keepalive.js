"use strict";
/* Keep an active admin login fresh without storing credentials in JavaScript.
   /api/session validates the HttpOnly signed cookie and renews it on the server.
   Transient network/proxy errors must never log the operator out. */
(() => {
  const INTERVAL_MS = 30 * 60 * 1000;
  let inFlight = false;
  let lastProbe = Date.now();

  async function keepAlive() {
    if (inFlight || document.visibilityState === "hidden" ||
        document.querySelector("#login")?.classList.contains("show")) return;
    inFlight = true;
    lastProbe = Date.now();
    try {
      const response = await fetch("/api/session", {
        method: "GET", credentials: "same-origin", cache: "no-store"
      });
      if (!response.ok) return; // outages, edge errors, throttles: not logout evidence
      const result = await response.json();
      if (result && result.auth_enabled && result.authenticated === false) {
        clearApiCache();
        showLogin();
      }
    } catch (_) {
      // Offline / network interruption: preserve the current UI and retry later.
    } finally {
      inFlight = false;
    }
  }

  function onReturn() {
    if (Date.now() - lastProbe >= INTERVAL_MS) void keepAlive();
  }

  setInterval(keepAlive, INTERVAL_MS);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") onReturn();
  });
  window.addEventListener("focus", onReturn);
})();
