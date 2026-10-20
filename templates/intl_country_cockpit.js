/* Country reading stays functional as native HTML; enhancement synchronizes navigation. */
(function () {
  "use strict";
  function mount() {
    var root = document.querySelector("[data-im-country-analysis]");
    if (!root || root.dataset.imcEnhanced) return;
    root.dataset.imcEnhanced = "true";
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
