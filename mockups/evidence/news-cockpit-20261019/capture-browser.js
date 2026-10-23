// News visual evidence capture adapter v1.
// Invoked through the Browser plugin in the existing Chrome extension session.
// It observes the requested state and records browser screenshot bytes; it never mutates the DOM.
// UI interactions and fixture transitions are recorded separately in the manifest.
async function captureNewsEvidence(spec) {
  const observed = await newsStyleTab.playwright.evaluate((s) => {
    const root = document.documentElement;
    const target = s.selector ? document.querySelector(s.selector) : null;
    const style = target ? getComputedStyle(target) : null;
    const desk = document.querySelector(".news-desk");
    return {
      url: location.href,
      captured_at: new Date().toISOString(),
      applied_theme: root.getAttribute("data-theme"),
      applied_locale: root.getAttribute("data-lang") || root.lang.split("-")[0],
      viewport_width: innerWidth,
      viewport_height: innerHeight,
      document_width: root.scrollWidth,
      desk_width: desk ? desk.getBoundingClientRect().width : null,
      target_present: !!target,
      hover_applied: target ? target.matches(":hover") : false,
      focus_applied: target ? document.activeElement === target : false,
      focus_visible: target ? target.matches(":focus-visible") : false,
      target_background: style ? style.backgroundColor : null,
      target_outline: style ? style.outline : null,
      visible_dialog: document.querySelector("dialog[open]")?.id || null,
      aggregate_connection: document.querySelector("#ndConnection")?.textContent,
      company_connection: document.querySelector("#ndCompanyStatus")?.textContent,
      company_update_visible: !!document.querySelector("#ndCompanyUpdates:not([hidden])")
    };
  }, spec);
  if (observed.applied_theme !== spec.theme || observed.applied_locale !== spec.locale ||
      observed.viewport_width !== spec.viewport_width || observed.viewport_height !== spec.viewport_height) {
    throw new Error("Observed theme, locale or viewport differs from the requested capture");
  }
  if (spec.kind === "hover" && !observed.hover_applied) throw new Error("Hover state absent");
  if (spec.kind === "focus" && (!observed.focus_applied || !observed.focus_visible)) {
    throw new Error("Visible keyboard focus absent");
  }
  if (observed.document_width > observed.viewport_width) throw new Error("Horizontal page overflow");
  await nodeRepl.write({news_evidence: {requested: spec, observed}});
  await nodeRepl.write(await newsStyleTab.screenshot({}));
}
