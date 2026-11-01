/* Admin preferences reuse the site's keys and change-event contract.
   Load before styles to apply validated preferences before first paint. */
(function () {
  "use strict";
  const root = document.documentElement;
  const validTheme = value => value === "dark" || value === "light";
  const validLanguage = value => value === "en" || value === "zh";
  function read(key) {
    try { return localStorage.getItem(key); } catch (_) { return null; }
  }
  function persist(key, value) {
    try { localStorage.setItem(key, value); } catch (_) { /* Preferences still work in memory. */ }
  }
  function deviceTheme() {
    try { return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"; }
    catch (_) { return "dark"; }
  }
  let theme = read("theme");
  let language = read("lang");
  theme = validTheme(theme) ? theme : deviceTheme();
  language = validLanguage(language) ? language : "en";
  function applyRoot() {
    root.setAttribute("data-theme", theme);
    root.setAttribute("data-lang", language);
    root.lang = language === "zh" ? "zh-CN" : "en";
    root.style.colorScheme = theme;
  }
  function translateShell() {
    document.querySelectorAll("[data-admin-en][data-admin-zh]").forEach(node => {
      node.textContent = node.getAttribute("data-admin-" + language);
    });
    document.querySelectorAll("[data-admin-placeholder-en][data-admin-placeholder-zh]").forEach(node => {
      node.placeholder = node.getAttribute("data-admin-placeholder-" + language);
    });
    document.querySelectorAll("[data-admin-aria-en][data-admin-aria-zh]").forEach(node => {
      node.setAttribute("aria-label", node.getAttribute("data-admin-aria-" + language));
    });
  }
  function syncControls() {
    const themeControl = document.getElementById("adminTheme");
    const languageControl = document.getElementById("adminLanguage");
    if (themeControl) themeControl.value = theme;
    if (languageControl) languageControl.value = language;
    translateShell();
  }
  function setTheme(value) {
    if (!validTheme(value)) { syncControls(); return; }
    theme = value;
    persist("theme", theme);
    try { localStorage.removeItem("themeAuto"); } catch (_) { /* Explicit choice stays active in this page. */ }
    applyRoot();
    syncControls();
    document.dispatchEvent(new CustomEvent("themechange", { detail: theme }));
  }
  function setLanguage(value) {
    if (!validLanguage(value)) { syncControls(); return; }
    language = value;
    persist("lang", language);
    applyRoot();
    syncControls();
    document.dispatchEvent(new CustomEvent("langchange", { detail: language }));
  }
  applyRoot();
  function wire() {
    syncControls();
    const themeControl = document.getElementById("adminTheme");
    const languageControl = document.getElementById("adminLanguage");
    if (themeControl) themeControl.addEventListener("change", event => setTheme(event.target.value));
    if (languageControl) languageControl.addEventListener("change", event => setLanguage(event.target.value));
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", wire, { once: true });
  else wire();
}());
