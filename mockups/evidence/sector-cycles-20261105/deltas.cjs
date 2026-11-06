"use strict";
// Seat delta cells on top of the 28-cell packet matrix (L6 ordering ruling, L6.4).
// Each cell names the closure row it proves; variants are served by serve_l6.py from
// <out>/_variants/<variant>/ through the X-L6-Variant header.
const D21 = [
  // Brief tape with quotes older than 5 days (renderTapeStrip desktop, renderSlimStrip 375) and a <=5d control.
  // The tape lives in the Brief view; under #cycles that view is hidden, so the cell opens Brief first.
  {view: "v1", theme: "dark", lang: "en", width: 1440, tag: "d21-gt5d", variant: "pulse_gt5d", steps: [{click: ".si-view-btn[data-view=\"overview\"]"}, {scroll: "#ftr-tape-strip"}], expectVisibleAny: ["tape_asof", "strip_asof"]},
  {view: "v1", theme: "dark", lang: "en", width: 375, tag: "d21-gt5d", variant: "pulse_gt5d", steps: [{click: ".si-view-btn[data-view=\"overview\"]"}, {scroll: "#ftr-tape-strip"}], expectVisibleAny: ["tape_asof", "strip_asof"]},
  {view: "v1", theme: "light", lang: "zh", width: 375, tag: "d21-gt5d", variant: "pulse_gt5d", steps: [{click: ".si-view-btn[data-view=\"overview\"]"}, {scroll: "#ftr-tape-strip"}], expectVisibleAny: ["tape_asof", "strip_asof"]},
  {view: "v1", theme: "dark", lang: "en", width: 1440, tag: "d21-le5d", variant: "pulse_le5d", steps: [{click: ".si-view-btn[data-view=\"overview\"]"}, {scroll: "#ftr-tape-strip"}], expectVisibleAny: ["tape_asof", "strip_asof"]},
];
const D30 = [
  // Unstamped payload: every face falls back to scStanceUnavailable.
  {view: "v2", theme: "dark", lang: "en", width: 1440, tag: "d30-unstamped", variant: "unstamped"},
  {view: "v2", theme: "light", lang: "zh", width: 390, tag: "d30-unstamped", variant: "unstamped"},
  // Focused sector detail (stance chip, ok/warn/muted tones) through the #<id> focus hash.
  {view: "v2", theme: "dark", lang: "en", width: 1440, tag: "d30-detail", steps: [{hash: "xlk", wait: 600}, {scroll: "#sc-detail"}]},
  {view: "v2", theme: "light", lang: "en", width: 1440, tag: "d30-detail", steps: [{hash: "xlk", wait: 600}, {scroll: "#sc-detail"}]},
  {view: "v2", theme: "dark", lang: "zh", width: 1440, tag: "d30-detail", steps: [{hash: "xlk", wait: 600}, {scroll: "#sc-detail"}]},
  {view: "v2", theme: "light", lang: "zh", width: 390, tag: "d30-detail", steps: [{hash: "xlk", wait: 600}]},
  {view: "v2", theme: "dark", lang: "en", width: 1440, tag: "d30-detail-unstamped", variant: "unstamped", steps: [{hash: "xlk", wait: 600}, {scroll: "#sc-detail"}]},
  // INTL legacy path: shared cycle.css on the country cycles page.
  {view: "v5", theme: "dark", lang: "en", width: 1440, tag: "d30-intl"},
  {view: "v5", theme: "light", lang: "en", width: 390, tag: "d30-intl"},
];
const DL310 = [
  {view: "v2", theme: "dark", lang: "en", width: 1440, tag: "d-l3-10-chip-all", steps: [{click: "#sc-chips .sc-chip-all"}]},
  // The basket rail only mounts under the Thematic Baskets tab and its chips sit in a closed drawer.
  {view: "v2", theme: "dark", lang: "en", width: 1440, tag: "d-l3-10-basket", steps: [{click: "#sc-tabs .sc-tab[data-fam=\"baskets\"]"}, {click: "#sc-bask-toggle", wait: 500}, {click: ".sc-bchip[data-id]"}, {scroll: "#sc-baskets"}], expectVisibleAny: ["basket_on"]},
  {view: "v2", theme: "light", lang: "en", width: 1440, tag: "d-l3-10-group", steps: [{click: "#sc-groups .cyc-gchip[data-k]"}]},
  // Members live in the Companies tab; #cycle opens the Cycle tab.
  {view: "v3", theme: "dark", lang: "en", width: 1440, tag: "d-l3-10-members", steps: [{click: "#scd-t-companies"}, {scroll: ".scd-members"}], expectVisibleAny: ["members"]},
];
const L4 = [
  // No-JS server HTML must carry <span id="sc-asof">YYYY-MM-DD</span> (US + China builders).
  {view: "v2", theme: "dark", lang: "en", width: 1440, tag: "l4-nojs", js: false},
  {view: "v4", theme: "dark", lang: "zh", width: 1440, tag: "l4-nojs", js: false},
];
const L5 = [
  // Dossier at 375 in both themes (retired-stripe containers, urgency pills, neutral .synthesis).
  {view: "v3", theme: "dark", lang: "en", width: 375, tag: "l5"},
  {view: "v3", theme: "light", lang: "en", width: 375, tag: "l5"},
  // Companies "Not covered": no members and no holdings resolve for the ETF.
  {view: "v3", theme: "dark", lang: "en", width: 1440, tag: "l5-unresolved", variant: "xlk_unresolved", steps: [{click: "#scd-t-companies"}, {scroll: "#scd-p-companies"}], expectVisibleAny: ["companies_unavailable"]},
  {view: "v3", theme: "light", lang: "zh", width: 375, tag: "l5-unresolved", variant: "xlk_unresolved", steps: [{click: "#scd-t-companies"}, {scroll: "#scd-p-companies"}], expectVisibleAny: ["companies_unavailable"]},
];
module.exports = [...D21, ...D30, ...DL310, ...L4, ...L5];
