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

    /* ---- Tools and retained research reveal ----
     *
     * The retained research lives inside the Tools disclosure, so a link to any of it
     * is unreachable until every containing disclosure is open. Two properties of a
     * projected page make this more than toggling details.open:
     *  - a projected anchor displays the PARENT href, so its attribute cannot be
     *    compared against this child location to decide whether the destination is
     *    still same-document. Only the bridge knows whether the anchor was authored as
     *    "#id" or as an explicit "/intl.html#id"; it answers that question through
     *    MMXSharedShell.sameDocumentFragment(anchorElement) and this controller never
     *    rebuilds the question out of the displayed URL.
     *  - opening a disclosure reflows everything below it, and the country toolbar is
     *    sticky, so the destination only becomes reachable after that reflow and clear
     *    of the toolbar. Neither is something native fragment scrolling can do.
     *
     * Presentation only: it opens disclosures and scrolls. It never pushes or replaces
     * history, never synthesises a hashchange, a message or an acknowledgment, and
     * never moves focus.
     */
    var revealGeneration = 0;

    function locationFragment() {
      var hash = "";
      try { hash = window.location.hash; } catch (e) { return null; }
      return (typeof hash === "string" && hash.length > 1) ? hash.slice(1) : null;
    }

    function elementForFragment(fragment) {
      if (typeof fragment !== "string" || fragment === "") return null;
      var id = "";
      try { id = decodeURIComponent(fragment); } catch (_) { return null; }
      if (!id) return null;
      try { return document.getElementById(id); } catch (_) { return null; }
    }

    // Research is reachable only through Tools. An id anywhere else on the page keeps
    // its ordinary behaviour, and a malformed or unknown id is not a destination.
    function researchTarget(fragment) {
      if (!tools) return null;
      var target = elementForFragment(fragment);
      if (!target) return null;
      return (target === tools || tools.contains(target)) ? target : null;
    }

    function openAncestors(target) {
      // Every containing disclosure, including the ones ABOVE Tools: a closed
      // ancestor leaves the destination unrendered, so opening only up to Tools'
      // own parent is what leaves a nested target invisible.
      for (var node = target; node && node !== document.body; node = node.parentElement)
        if (node.tagName === "DETAILS") node.open = true;
    }

    // Tools is far taller than the scrollport, so its box is not where a reader
    // arrives; the summary is the first visible line of that destination.
    function arrivalFor(target) {
      if (String(target.tagName || "").toUpperCase() === "DETAILS") {
        var summary = null;
        try { summary = target.querySelector("summary"); } catch (_) { summary = null; }
        if (summary) return summary;
      }
      return target;
    }

    function stickyHeight() {
      if (!toolbar) return 0;
      var box = null;
      try { box = toolbar.getBoundingClientRect(); } catch (e) { return 0; }
      if (!box || !(box.height > 0) || box.top > 1) return 0;
      var limit = window.innerHeight || 0;
      var gap = Math.ceil(box.height) + 8;
      return limit ? Math.min(gap, Math.floor(limit / 2)) : gap;
    }

    function bringIntoView(el) {
      var box = null;
      try { box = el.getBoundingClientRect(); } catch (e) { return; }
      if (!box) return;
      var viewport = window.innerHeight || document.documentElement.clientHeight || 0;
      var offset = stickyHeight();
      // Already inside the scrollport and clear of the toolbar: leave the reader's
      // position, and any parent-restored position, exactly as it is.
      if (viewport > 0 && box.bottom > 0 && box.top >= offset - 1 && box.top < viewport) return;
      var top = (window.pageYOffset || 0) + box.top - offset;
      var limit = Math.max(0, (document.documentElement.scrollHeight || 0) - viewport);
      if (limit > 0 && top > limit) top = limit;
      if (top < 0) top = 0;
      try { window.scrollTo(window.pageXOffset || 0, top); } catch (e) {}
    }

    function revealResearch(fragment) {
      var target = researchTarget(fragment);
      if (!target) return null;
      // Synchronous: the disclosures must already be open when the fragment arrives.
      openAncestors(target);
      revealGeneration += 1;
      var mine = revealGeneration;
      var arrival = arrivalFor(target);
      // Deferred: the arrival alignment runs against the reflowed layout, and a newer
      // destination cancels whatever this one still had pending.
      var run = function () { if (mine === revealGeneration) bringIntoView(arrival); };
      if (typeof window.requestAnimationFrame === "function") window.requestAnimationFrame(run);
      else window.setTimeout(run, 0);
      return target;
    }

    // A standalone page answers this itself, and answers it strictly: same origin,
    // same path, same query bytes, no credentials. A live bridge owns the answer for
    // its own projected anchors; when that bridge exposes no helper, classification
    // fails CLOSED instead of guessing and the accepted-location fallback below stays
    // the only thing that reacts.
    function standaloneFragment(anchor) {
      var attr = null;
      try { attr = anchor.getAttribute("href"); } catch (_) { return null; }
      if (typeof attr !== "string" || attr === "") return null;
      var url = null;
      try { url = new URL(attr, window.location.href); } catch (_) { return null; }
      if (url.username || url.password) return null;
      if (url.origin !== window.location.origin) return null;
      if (url.pathname !== window.location.pathname) return null;
      if (url.search !== window.location.search) return null;
      return url.hash.length > 1 ? url.hash.slice(1) : null;
    }

    function fragmentForAnchor(anchor) {
      var bridge = window.MMXSharedShell;
      if (bridge && bridge.active === true) {
        if (typeof bridge.sameDocumentFragment !== "function") return null;
        try { return bridge.sameDocumentFragment(anchor); } catch (_) { return null; }
      }
      return standaloneFragment(anchor);
    }

    /* Capture phase on the document. The bridge intercepts in the bubble phase on the
     * same node and performs the fragment navigation there, so capturing here is what
     * makes the disclosures open BEFORE the fragment arrives and before its own first
     * scroll attempt, while still reading the pre-navigation classification. */
    document.addEventListener("click", function (event) {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      if (typeof event.button === "number" && event.button !== 0) return;
      var node = event.target;
      if (!node || typeof node.closest !== "function") return;
      var anchor = node.closest("a[href]");
      // Anchors the bridge leaves native (new tab, download, a link acting as a button)
      // keep the current page and its state; they are not an arrival into research.
      if (!anchor || anchor.hasAttribute("download")) return;
      if (String(anchor.getAttribute("target") || "").toLowerCase() === "_blank") return;
      if (String(anchor.getAttribute("role") || "").toLowerCase() === "button") return;
      var fragment = fragmentForAnchor(anchor);
      if (!fragment) return;
      revealResearch(fragment);
    }, true);

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
      revealResearch(locationFragment());
      // Native fragment scrolling may precede the country disclosure reflow.
      // Align after that layout, only while this remains the active destination.
      if (country && hash) window.requestAnimationFrame(function () {
        if (window.location.hash === hash && country.open)
          country.scrollIntoView({block: "start"});
      });
    }
    window.addEventListener("hashchange", followHash);
    // The bridge announces an accepted location with a bare event. The destination is
    // read back from this window, never from event.detail, so a stale or forged detail
    // cannot select a target.
    window.addEventListener("mmx:shell-location", followHash);
    if (tools && new URLSearchParams(window.location.search).has("view")) tools.open = true;
    followHash();
    syncRail();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount, {once: true});
  else mount();
}());
