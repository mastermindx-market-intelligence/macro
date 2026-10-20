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
    window.addEventListener("hashchange", function () {
      reveal(window.location.hash || initialCountryHash);
      exposeLegacyAnchor();
    });
    if (tools && new URLSearchParams(window.location.search).has("view")) tools.open = true;
    reveal(window.location.hash);
    exposeLegacyAnchor();
    syncRail();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount, {once: true});
  else mount();
}());
