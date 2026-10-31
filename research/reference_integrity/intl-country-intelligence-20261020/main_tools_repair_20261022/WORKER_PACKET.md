MISSION: Return a minimal, reviewable scratch-only patch that fixes the International country cockpit's real projected Data & tools link under the existing Shared Shell bridge, with discriminating browser regressions. Do not edit any original repository/worktree. The parent will integrate and run actual Terminal-parent acceptance.

ASSIGNMENT/CUSTODY: Macro PR9596, existing operation intl-country-cockpit-20261018, exact source ae6de4e56e2f826beab78f4de29fcaa89f27dbeb. The current user explicitly answered "yes, resume and get as much done as u can" to superseding the interrupted scratch-only Tools repair and making this parent the sole source integrator. Prior run intl-20261021-shell-country-repair-r1 under original root 01a1101f-2a37-7320-9a9b-5df3ce1b890d retains UNKNOWN historical effect; do NOT query/retry/consume it. This is one explicitly authorized successor scratch assignment. Preserve original root accounting. Immediate calling principal is native /root, represented as schema-safe parent_id root; this is continuity metadata, not authentication.

ROUTE: fix_build / C1_ROUTINE_BOUNDED; low ambiguity; routine reversible execution risk; material product impact; worker leaf. WHY NOT FABLE: frozen architecture and reproduced defect. Direct CEO->worker: LOWER_TOTAL_OVERHEAD for one small patch; parent owns integration, independent review and actual-parent acceptance. Do not spawn descendants/native helpers/nested provider CLIs. Use only installed admitted worker tools and the existing budget.

REQUIRED ROLE loaded from protected Mastermind c9cbee5569ba50e30e28715d930809061a169517, skills/mastermind-fabric-orchestration/references/worker.md:
Complete exactly the assigned implementation/test outcome inside existing source/effect and budget envelope. Do not spawn descendants. Run discriminating validations and permitted repairs within existing attempt budget. Return exact artifact revisions, actual results, limitations/blockers. Do not self-approve independent review, publish/deploy or bypass refusal. EFFECT_UNKNOWN stays on original operation/carrier. State that you consumed this bounded worker role in the return.

KNOWN REAL FAILURE: unchanged Macro child through real Terminal AppShell->SharedShellRuntime->LegacyPageHost at parent e45bde2cac07ac3b29285ff70c40d68900fad62c. Parent 127.0.0.1:3100 child3102. Bridge projects authored href="#intl-analysis-tools" to http://127.0.0.1:3100/intl.html#intl-analysis-tools. First click gets matching real NAVIGATE / LOCATION_ACCEPTED req-2 and parent URL changes, but outer disclosure stays closed. Same-hash repeated click also stays closed with no new ACK/history entry. Country rail and parent Back/Forward controls pass. Full evidence: https://raw.githubusercontent.com/mastermindx-market-intelligence/macro/ae6de4e56e2f826beab78f4de29fcaa89f27dbeb/research/reference_integrity/intl-country-intelligence-20261020/main_parent_reproduction_20261022/README.md .
Source diagnosis: country click matcher only matches literal fragment href; country controller only subscribes hashchange; accepted bridge location emits mmx:shell-location; workspace entry listener handles nested legacy root but excludes outer tools.

INPUT ACCESS: Source is public and immutable. Worker host is selected by admission; never assume M2 filesystem paths are accessible. Exact source can be fetched from these raw URLs into your own scratch only:
https://raw.githubusercontent.com/mastermindx-market-intelligence/macro/ae6de4e56e2f826beab78f4de29fcaa89f27dbeb/templates/intl_country_cockpit.js
https://raw.githubusercontent.com/mastermindx-market-intelligence/macro/ae6de4e56e2f826beab78f4de29fcaa89f27dbeb/templates/shared_shell_bridge.js
https://raw.githubusercontent.com/mastermindx-market-intelligence/macro/ae6de4e56e2f826beab78f4de29fcaa89f27dbeb/templates/intl_workspace_entry.js
https://raw.githubusercontent.com/mastermindx-market-intelligence/macro/ae6de4e56e2f826beab78f4de29fcaa89f27dbeb/tests/intl_workspace_legacy_navigation.test.cjs
https://raw.githubusercontent.com/mastermindx-market-intelligence/macro/ae6de4e56e2f826beab78f4de29fcaa89f27dbeb/tests/js/shared_shell_bridge.test.cjs
https://raw.githubusercontent.com/mastermindx-market-intelligence/macro/ae6de4e56e2f826beab78f4de29fcaa89f27dbeb/tests/intl_workspace_page.test.cjs
Controller complete baseline is embedded below. Inspect the bridge's actual supported canonical-URL/helper contract; do not invent a parent-origin trust shortcut.

ALLOWED PATCH PATHS:
- templates/intl_country_cockpit.js
- site/intl_country_cockpit.js (plain paired copy, same bytes)
- tests/intl_country_cockpit_navigation.test.cjs (new focused regression using established Node test + Playwright style; no fake all-pass source-string assertions).
If a different existing test file is materially necessary, propose it in return, do not broaden production edits.

ACCEPTANCE:
1 First and repeated actual projected Tools activation opens the outer disclosure, including manually re-collapsing at same hash. Recognize only the current document's valid local or admitted projected destination; foreign origin/path/query lookalikes do not open it.
2 Consume accepted shell-location consistently using current actual location, without trusting arbitrary event-detail URL or fabricating history.
3 Preserve standalone links, normal/modified clicks, country selection/focus, one parent history transition, generation retention and nested legacy behavior. No parent/bridge/allowlist/protocol/authentication changes.
4 Regression must actually execute controller behavior in browser; include before failure with unmodified baseline and after success if tools allow. Test failures/limitations honest. A test harness may model bridge interactions for unit scope, but label it clearly; only parent's actual supported-runtime proof qualifies product.
5 No data/country analysis/CSS/design/proposal/CI packing/manifest changes. Never rewrite frozen evidence.
6 Return complete unified diff (or exact full changed files with clearly delimited names), SHA256s, exact commands/results, original baseline binding, deviations and open questions. Keep response under 48KiB. Do not send only a path on an inaccessible worker host.

STOP: one complete bounded patch/evidence return or concrete blocker; no commits, push, PR changes, merge, deployment, external messaging, server persistence, production access or source acquisition. No independent acceptance claim.

BASELINE templates/intl_country_cockpit.js:
/* Country reading stays functional as native HTML; enhancement synchronizes navigation. */
(function () {
  "use strict";
  function mount() {
    var root = document.querySelector("[data-im-country-analysis]");
    if (!root || root.dataset.imcEnhanced) return;
    root.dataset.imcEnhanced = "true";
    // Keep the existing shared assistant in reserved navigation space.
    // Its DOM, lazy handover, language handling and focus owner stay untouched.
    var toolbar = root.querySelector(".imc-toolbar");
    var toolbarAnchor = root.querySelector(".imc-toolbar-anchor");
    var assistantSlot = root.querySelector(".imc-assistant-slot");
    if (toolbar && toolbarAnchor && assistantSlot) {
      var dockFrame = 0;
      function updateAssistantDock() {
        dockFrame = 0;
        var anchorBox = toolbarAnchor.getBoundingClientRect();
        var chrome = document.documentElement;
        chrome.style.setProperty("--imc-toolbar-left", anchorBox.left + "px");
        chrome.style.setProperty("--imc-toolbar-width", anchorBox.width + "px");
        toolbar.classList.toggle("is-stuck", anchorBox.top <= 0);
        chrome.style.setProperty("--imc-toolbar-height", toolbar.getBoundingClientRect().height + "px");
        var slotBox = assistantSlot.getBoundingClientRect();
        chrome.style.setProperty("--imc-assistant-left", slotBox.left + "px");
        chrome.style.setProperty("--imc-assistant-top", slotBox.top + "px");
        document.body.dataset.imcAssistantDock = "true";
        document.querySelectorAll("#mmb-boot, #mmb-launch").forEach(function (launcher) {
          launcher.title = launcher.getAttribute("aria-label") || "";
        });
      }
      function scheduleAssistantDock() {
        if (!dockFrame) dockFrame = window.requestAnimationFrame(updateAssistantDock);
      }
      window.addEventListener("scroll", scheduleAssistantDock, {passive: true});
      window.addEventListener("resize", scheduleAssistantDock);
      document.addEventListener("langchange", scheduleAssistantDock);
      if (typeof ResizeObserver === "function") {
        var toolbarResize = new ResizeObserver(scheduleAssistantDock);
        toolbarResize.observe(toolbarAnchor);
        toolbarResize.observe(toolbar);
      }
      // The bootstrap and full widget are mounted directly under body.
      // Observing that handover does not watch chat content or move widget nodes.
      var assistantMount = new MutationObserver(scheduleAssistantDock);
      assistantMount.observe(document.body, {childList: true});
      updateAssistantDock();
    }
    var tools = document.getElementById("intl-analysis-tools");
    var initialCountry = root.querySelector(".imc-country[open]");
    var initialCountryHash = initialCountry ? "#" + initialCountry.id : "";
    function syncRail() {
      var active = root.querySelector(".imc-country[open]");
      root.querySelectorAll(".imc-country-rail a").forEach(function (link) {
        if (active && link.hash === "#" + active.id) link.setAttribute("aria-current", "location");
        else link.removeAttribute("aria-current");
      });
    }
    function countryFor(hash) {
      if (!/^#imc-country-(JP|KR|TW|IN|AU|GB|EZ)$/.test(hash)) return null;
      var target = document.getElementById(hash.slice(1));
      return target && root.contains(target) && target.matches("details.imc-country") ? target : null;
    }
    function reveal(hash) {
      var target = countryFor(hash);
      if (!target) return null;
      root.querySelectorAll(".imc-country[open]").forEach(function (item) {
        if (item !== target) item.open = false;
      });
      target.open = true;
      syncRail();
      return target;
    }
    function select(hash, scroll) {
      var target = reveal(hash);
      if (!target) return;
      if (window.location.hash !== hash) window.history.pushState(window.history.state, "", hash);
      if (scroll) target.scrollIntoView({block: "start"});
      target.querySelector("summary").focus({preventScroll: true});
    }
    function exposeLegacyAnchor() {
      if (!tools) return;
      var hash = window.location.hash, target = null;
      try { target = document.getElementById(decodeURIComponent(hash.slice(1))); } catch (_) {}
      if (target && (target === tools || tools.contains(target))) {
        for (var node = target; node && node !== tools.parentElement; node = node.parentElement)
          if (node.tagName === "DETAILS") node.open = true;
      }
    }
    root.addEventListener("click", function (event) {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return;
      var link = event.target.closest("a[data-imc-country]");
      if (link && root.contains(link)) {
        event.preventDefault();
        select(link.hash, true);
        return;
      }
      var summary = event.target.closest(".imc-country > summary");
      if (summary && root.contains(summary) && !summary.parentElement.open) {
        event.preventDefault();
        select("#" + summary.parentElement.id, false);
        return;
      }
      if (event.target.closest('a[href="#intl-analysis-tools"]') && tools) tools.open = true;
    });
    root.addEventListener("toggle", syncRail, true);
    function followHash() {
      var hash = window.location.hash;
      var country = reveal(hash || initialCountryHash);
      exposeLegacyAnchor();
      // Native fragment scrolling may precede the country disclosure reflow.
      // Align after that layout, only while this remains the active destination.
      if (country && hash) window.requestAnimationFrame(function () {
        if (window.location.hash === hash && country.open)
          country.scrollIntoView({block: "start"});
      });
    }
    window.addEventListener("hashchange", followHash);
    if (tools && new URLSearchParams(window.location.search).has("view")) tools.open = true;
    followHash();
    syncRail();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount, {once: true});
  else mount();
}());

END BASELINE