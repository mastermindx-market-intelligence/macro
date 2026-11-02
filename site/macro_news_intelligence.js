/* Progressive enhancement only. Existing mx5 owns modal lifecycle and access. */
(function () {
  "use strict";
  function init() {
    var root = document.querySelector("#dlg-news [data-news-intelligence]");
    if (!root || root.getAttribute("data-news-enhanced") === "true") return;
    var rows = Array.from(root.querySelectorAll("[data-news-item]"));
    var sections = Array.from(root.querySelectorAll("[data-news-section]"));
    var buttons = Array.from(root.querySelectorAll("[data-news-filter]"));
    var search = root.querySelector("[data-news-search]");
    var count = root.querySelector("[data-news-count]");
    var reset = root.querySelector("[data-news-reset]");
    var noMatches = root.querySelector("[data-news-no-matches]");
    var announcement = root.querySelector("[data-news-announcement]");
    var filter = "all", announceTimer;
    function zh() { return document.documentElement.getAttribute("data-lang") === "zh"; }
    function normalize(text) { return String(text || "").normalize("NFKC").toLocaleLowerCase().replace(/\s+/g, " ").trim(); }
    // Cache only source row text. Release status refreshes never replace or reorder rows.
    var index = rows.map(function (row) { return normalize(row.textContent); });
    function apply(announce) {
      var terms = normalize(search.value).split(" ").filter(Boolean), visible = 0;
      rows.forEach(function (row, i) {
        var matches = (filter === "all" || row.getAttribute("data-news-item") === filter) &&
          terms.every(function (term) { return index[i].indexOf(term) !== -1; });
        row.hidden = !matches;
        if (matches) visible += 1;
      });
      sections.forEach(function (section) {
        section.hidden = !Array.from(section.querySelectorAll("[data-news-item]")).some(function (row) { return !row.hidden; });
      });
      buttons.forEach(function (button) {
        var selected = button.getAttribute("data-news-filter") === filter;
        button.classList.toggle("is-selected", selected);
        button.setAttribute("aria-pressed", String(selected));
      });
      count.textContent = zh() ? "显示 " + visible + " / " + rows.length + " 条动态" :
        visible + " of " + rows.length + " developments";
      reset.hidden = filter === "all" && terms.length === 0;
      noMatches.hidden = visible > 0 || rows.length === 0;
      window.clearTimeout(announceTimer);
      if (announce) announceTimer = window.setTimeout(function () {
        announcement.textContent = zh() ? "找到 " + visible + " 条匹配动态" : visible + " matching developments";
      }, 180);
    }
    function clockLabel(node) {
      var raw = node.getAttribute("data-news-clock") || "";
      // Date-only is an observation date, never pretend it is midnight or a live clock.
      var dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(raw);
      var iso = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})$/.test(raw);
      var value = dateOnly ? new Date(raw + "T12:00:00Z") : new Date(raw);
      var day = new Date(raw.slice(0, 10) + "T12:00:00Z");
      var valid = (dateOnly || iso) && Number.isFinite(value.getTime()) && Number.isFinite(day.getTime()) && day.toISOString().slice(0, 10) === raw.slice(0, 10);
      if (!valid) {
        node.textContent = zh() ? "时间不可用" : "Time unavailable";
        node.removeAttribute("datetime");
        return;
      }
      var future = dateOnly ? raw > new Date().toISOString().slice(0, 10) : value.getTime() > Date.now() + 60000;
      if (future) {
        node.textContent = zh() ? "时间待核查" : "Time needs checking";
        node.removeAttribute("datetime");
        return;
      }
      var label = new Intl.DateTimeFormat(zh() ? "zh-CN" : "en-US", {
        year: "numeric", month: "short", day: "numeric", timeZone: "UTC",
        ...(dateOnly ? {} : {hour: "2-digit", minute: "2-digit", hourCycle: "h23"})
      }).format(value);
      var reported = node.getAttribute("data-news-clock-kind") === "reported";
      node.textContent = (zh() ? (reported ? "报道于 " : "观测于 ") : (reported ? "Reported " : "Observed ")) + label + (dateOnly ? "" : " UTC");
    }
    function localize() {
      var close = root.closest('#dlg-news').querySelector('.mx5-dlg-close');
      if (close) close.setAttribute('aria-label', zh() ? '关闭' : 'Close');
      root.querySelectorAll("[data-news-aria-en]").forEach(function (node) {
        node.setAttribute("aria-label", node.getAttribute(zh() ? "data-news-aria-zh" : "data-news-aria-en"));
      });
      search.placeholder = search.getAttribute(zh() ? "data-news-placeholder-zh" : "data-news-placeholder-en");
      root.querySelectorAll("[data-news-clock]").forEach(clockLabel);
      apply(false);
    }
    buttons.forEach(function (button) {
      button.addEventListener("click", function () { filter = button.getAttribute("data-news-filter"); apply(true); });
    });
    search.addEventListener("input", function () { apply(true); });
    reset.addEventListener("click", function () { filter = "all"; search.value = ""; apply(true); search.focus(); });
    root.addEventListener("click", function (event) {
      var link = event.target.closest("[data-news-panel]");
      if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button) return;
      if (typeof window.mx5OpenDlg === "function") {
        event.preventDefault();
        window.mx5OpenDlg(link.getAttribute("data-news-panel"));
      }
    });
    new MutationObserver(localize).observe(document.documentElement, {attributes: true, attributeFilter: ["data-lang"]});
    localize();
    root.querySelector("[data-news-toolbar]").hidden = false;
    root.setAttribute("data-news-enhanced", "true");
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, {once: true});
  else init();
})();
