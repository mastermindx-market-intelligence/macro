/* AI Brief freshness controller — keep long-lived dashboard tabs honest.
 *
 * The canonical brief bodies remain server-rendered by the existing shared Jinja
 * renderer. This client never interprets model JSON and never reimplements that
 * renderer. It fetches the canonical aibrief.html, compares each lens's rendered
 * state, and swaps in a newer date or a corrected body on the same date. A failed
 * request leaves the last valid body untouched.
 */
(function (root, factory) {
  "use strict";

  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;

  if (!root) return;
  root.MMXAIBriefFreshness = api;

  if (root.document && typeof root.fetch === "function" && typeof root.DOMParser === "function") {
    var controller = api.createController({
      document: root.document,
      window: root,
      fetch: root.fetch.bind(root),
      DOMParser: root.DOMParser,
      now: Date.now
    });
    controller.bind();
    root.MMXAIBriefFreshness = {
      applyNewerBriefs: api.applyNewerBriefs,
      createController: api.createController,
      checkNow: controller.checkNow,
      bind: controller.bind
    };
  }
})(
  typeof window !== "undefined"
    ? window
    : (typeof globalThis !== "undefined" ? globalThis : this),
  function () {
    "use strict";

    var BRIEF_SELECTOR = ".aib2[data-lens]";
    var DATE_SELECTOR = ".aib2-hdr-date";
    var MIN_CHECK_INTERVAL_MS = 60 * 1000;

    function toArray(value) {
      return Array.prototype.slice.call(value || []);
    }

    function lensOf(node) {
      if (!node) return "";
      if (node.dataset && typeof node.dataset.lens === "string") return node.dataset.lens;
      if (typeof node.getAttribute === "function") return node.getAttribute("data-lens") || "";
      return "";
    }

    function dateOf(node) {
      if (!node || typeof node.querySelector !== "function") return "";
      var dateNode = node.querySelector(DATE_SELECTOR);
      var value = dateNode && dateNode.textContent ? String(dateNode.textContent).trim() : "";
      if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return "";

      var parsed = new Date(value + "T00:00:00Z");
      if (!Number.isFinite(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== value) return "";
      return value;
    }

    function markupOf(node) {
      return node && typeof node.outerHTML === "string" ? node.outerHTML : "";
    }

    function cloneInto(documentRef, node) {
      if (documentRef && typeof documentRef.importNode === "function") {
        return documentRef.importNode(node, true);
      }
      return node && typeof node.cloneNode === "function" ? node.cloneNode(true) : null;
    }

    function replaceNode(current, replacement) {
      if (!current || !replacement) return false;
      if (typeof current.replaceWith === "function") {
        current.replaceWith(replacement);
        return true;
      }
      if (current.parentNode && typeof current.parentNode.replaceChild === "function") {
        current.parentNode.replaceChild(replacement, current);
        return true;
      }
      return false;
    }

    function applyNewerBriefs(localDocument, remoteDocument) {
      if (!localDocument || !remoteDocument) return 0;
      if (typeof localDocument.querySelectorAll !== "function"
          || typeof remoteDocument.querySelectorAll !== "function") return 0;

      var remoteByLens = Object.create(null);
      toArray(remoteDocument.querySelectorAll(BRIEF_SELECTOR)).forEach(function (node) {
        var lens = lensOf(node);
        var date = dateOf(node);
        if (!lens || !date) return;
        var existing = remoteByLens[lens];
        if (!existing || date > existing.date) remoteByLens[lens] = { node: node, date: date };
      });

      var changed = 0;
      toArray(localDocument.querySelectorAll(BRIEF_SELECTOR)).forEach(function (current) {
        var lens = lensOf(current);
        var candidate = remoteByLens[lens];
        if (!candidate) return;

        var currentDate = dateOf(current);
        if (currentDate && candidate.date < currentDate) return;
        if (currentDate && candidate.date === currentDate) {
          var currentMarkup = markupOf(current);
          var candidateMarkup = markupOf(candidate.node);
          if (!currentMarkup || !candidateMarkup || currentMarkup === candidateMarkup) return;
        }

        var replacement = cloneInto(localDocument, candidate.node);
        if (replaceNode(current, replacement)) changed += 1;
      });
      return changed;
    }

    function createController(environment) {
      environment = environment || {};
      var documentRef = environment.document;
      var windowRef = environment.window || {};
      var fetchRef = environment.fetch;
      var Parser = environment.DOMParser;
      var now = typeof environment.now === "function" ? environment.now : Date.now;
      var minimumInterval = Number.isFinite(environment.minimumIntervalMs)
        ? Math.max(0, environment.minimumIntervalMs)
        : MIN_CHECK_INTERVAL_MS;

      var inFlight = null;
      var lastStartedAt = 0;
      var bound = false;

      function canonicalUrl(stamp) {
        var href = (windowRef.location && windowRef.location.href)
          || (documentRef && documentRef.baseURI)
          || "http://localhost/";
        var url = new URL("/aibrief.html", href);
        url.searchParams.set("brief_refresh", String(stamp));
        return url.href;
      }

      function announce(changed) {
        if (!changed || typeof windowRef.dispatchEvent !== "function"
            || typeof windowRef.CustomEvent !== "function") return;
        try {
          windowRef.dispatchEvent(new windowRef.CustomEvent(
            "mm:aibrief-refreshed",
            { detail: { changed: changed } }
          ));
        } catch (_error) {
          // Refresh is complete even if an old browser cannot construct CustomEvent.
        }
      }

      function checkNow(force) {
        if (!documentRef || typeof documentRef.querySelector !== "function"
            || !documentRef.querySelector(BRIEF_SELECTOR)) return Promise.resolve(0);
        if (inFlight) return inFlight;

        var startedAt = now();
        if (!force && lastStartedAt && startedAt - lastStartedAt < minimumInterval) {
          return Promise.resolve(0);
        }
        lastStartedAt = startedAt;

        var request = Promise.resolve()
          .then(function () {
            if (typeof fetchRef !== "function") throw new Error("fetch unavailable");
            return fetchRef(canonicalUrl(startedAt), {
              cache: "no-store",
              credentials: "same-origin",
              headers: { Accept: "text/html" }
            });
          })
          .then(function (response) {
            if (!response || response.ok !== true || typeof response.text !== "function") {
              throw new Error("brief refresh unavailable");
            }
            return response.text();
          })
          .then(function (html) {
            if (typeof Parser !== "function") throw new Error("DOMParser unavailable");
            var remoteDocument = new Parser().parseFromString(html, "text/html");
            var changed = applyNewerBriefs(documentRef, remoteDocument);
            announce(changed);
            return changed;
          })
          .catch(function () {
            // Network, auth, parse, or schema failure: keep the last valid brief.
            return 0;
          });

        inFlight = request.then(
          function (value) { inFlight = null; return value; },
          function () { inFlight = null; return 0; }
        );
        return inFlight;
      }

      function isBriefIntent(target) {
        if (!target || typeof target.closest !== "function") return false;
        return Boolean(target.closest(
          BRIEF_SELECTOR + ', [id*="aibrief"], [onclick*="aibrief"]'
        ));
      }

      function bind() {
        if (bound || !documentRef || typeof documentRef.addEventListener !== "function") return;
        bound = true;

        documentRef.addEventListener("visibilitychange", function () {
          if (!documentRef.hidden) checkNow(true);
        });
        documentRef.addEventListener("click", function (event) {
          if (isBriefIntent(event && event.target)) checkNow(false);
        }, true);
        documentRef.addEventListener("focusin", function (event) {
          if (isBriefIntent(event && event.target)) checkNow(false);
        }, true);

        if (windowRef && typeof windowRef.addEventListener === "function") {
          windowRef.addEventListener("pageshow", function (event) {
            if (event && event.persisted) checkNow(true);
          });
        }
      }

      return { checkNow: checkNow, bind: bind };
    }

    return {
      applyNewerBriefs: applyNewerBriefs,
      createController: createController
    };
  }
);
