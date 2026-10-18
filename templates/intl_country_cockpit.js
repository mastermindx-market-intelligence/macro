/* Country disclosure enhancement; the existing workspace owns tool state. */
(function () {
  "use strict";
  function mount() {
    var root = document.querySelector("[data-im-country-analysis]");
    if (!root || root.dataset.imcEnhanced) return;
    root.dataset.imcEnhanced = "true";
    var tools = document.getElementById("intl-analysis-tools");
    function syncRail() {
      var active = root.querySelector(".imc-country[open]");
      root.querySelectorAll(".imc-country-rail a").forEach(function (link) {
        if (active && link.hash === "#" + active.id) link.setAttribute("aria-current", "location");
        else link.removeAttribute("aria-current");
      });
    }
    function reveal(hash, focus) {
      if (!/^#imc-country-(JP|KR|TW|IN|AU|GB|EZ)$/.test(hash)) return;
      var target = document.getElementById(hash.slice(1));
      if (!target || !root.contains(target) || target.tagName !== "DETAILS") return;
      root.querySelectorAll(".imc-country[open]").forEach(function (item) {
        if (item !== target) item.open = false;
      });
      target.open = true;
      syncRail();
      if (focus) target.querySelector("summary").focus({preventScroll:true});
    }
    function exposeLegacyAnchor() {
      if (!tools) return;
      var hash = window.location.hash;
      var target = null;
      try { target = document.getElementById(decodeURIComponent(hash.slice(1))); } catch (_) {}
      if (target && (target === tools || tools.contains(target))) {
        for (var node = target; node && node !== tools.parentElement; node = node.parentElement) {
          if (node.tagName === "DETAILS") node.open = true;
        }
      }
    }
    root.addEventListener("click", function (event) {
      var link = event.target.closest("a[data-imc-country]");
      if (link && root.contains(link) && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey && event.button === 0) {
        event.preventDefault();
        reveal(link.hash, false);
        if (window.location.hash !== link.hash) window.history.pushState(window.history.state, "", link.hash);
        var country = document.getElementById(link.hash.slice(1));
        country.scrollIntoView({block:"start"});
        country.querySelector("summary").focus({preventScroll:true});
      }
      if (event.target.closest('a[href="#intl-analysis-tools"]') && tools) tools.open = true;
    });
    root.addEventListener("toggle", syncRail, true);
    window.addEventListener("hashchange", function () {
      reveal(window.location.hash, false);
      exposeLegacyAnchor();
    });
    // Reveal the existing query-driven tools without parsing or owning their state.
    if (tools && new URLSearchParams(window.location.search).has("view")) tools.open = true;
    reveal(window.location.hash, false);
    exposeLegacyAnchor();
    syncRail();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount, {once:true});
  else mount();
}());
