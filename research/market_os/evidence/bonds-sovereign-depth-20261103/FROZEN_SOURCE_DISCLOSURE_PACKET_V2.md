# P12.T2.S1 — frozen sovereign observation/source disclosure packet

Source: ed9fb81da853429ce87495d6c012467ebf057548. Existing accepted gauge candidate168c19b6453929b033beb5d6ed83b8d9fd166c41 is byte-identical in templates/bonds.html.j2 at this source; preserve its gauge regions, styles and semantics. Retain all scored fields/yields/thresholds/models. Paper p-O-1 /283Q-0 retained by10603; W9 crosswalk consumer oracle requires tenor/currency/period/source/as-of/depth/return, not a new native page.

JOB: Reader enters Bonds, opens Global rates & sovereign detail, distinguishes daily Japan10y observation Sep30 from the page analysis Oct30, reads the exact existing source and observation dates with currency/curve basis, then returns through incumbent hash/overview navigation. Controlled offline native owner+authored fragment proof only; no full Shell/auth/served acceptance is implied.

CAUSAL GAP: Native _country_row derives age after _align forward-fills. Retained Japan raw jgb_10y ends2026-09-30, analysis2026-10-30, yield3.057 (presenter3.06), daily threshold12days; current stale=false. Actual source clocks and exact provider links are absent from the detail UI; ccy/slope_basis already exist but are dropped.

FROZEN CHANGE: (1) retain raw source series; select effective last non-null source observation at/before the aligned value endpoint (never future data); use that date for the incumbent stale threshold. Expose immutable per-leg observation/source metadata alongside the row, without altering measured/derived numeric fields. (2) existing sovereign tables disclose currency and human curve basis; stale text/tooltips describe source age, not falsely label daily Japan as OECD monthly. (3) Inside existing #global-detail scorecard, one canonical mx-disc native details/summary lists provider, tenor, exact existing source URL and raw observation date for the row’s yield and used comparison/real legs. Existing source unavailable stays explicit. All-source unavailable gets a bilingual unavailable sentence. No new stylesheet, JS, endpoint, data acquisition, store, taxonomy or source authority.

SOURCES: reuse native ROSTER and its _load_series_standalone US alias→FRED mapping. FRED uses incumbent canonical https://fred.stlouisfed.org/series/<qualified-id> pattern; ECB URL and key, MoF URL and tenor column come only from config.yml sovereign already used by collectors/sovereign.py. No guessed provider path. Data-source links are rendered only, never requested in the fixture.

DARK TREATMENT: retain existing dark table/card material, muted explanatory ink and canonical mx-disc summary/links. LIGHT TREATMENT: retain existing cool-canvas/white research surface and existing semantic foreground/link ink. Both use authored styles unchanged; no new color, stripe, surface family, hierarchy or geometry. Differences are incumbent material treatments, not new palette substitution.

COMPONENTS: incumbent sc-tbl with internal scroll; existing note/faint labels; canonical mx-disc details/summary. Evidence is Tier3, never a new Tier1 tile. Keyboard/touch uses native summary. No invented custom popover or modal.

VALIDATION: missing raw input→no false zero/fresh row; genuine zero yield retained; daily old source vs same-day source, monthly below/above existing75-day threshold, future source excluded, independent secondary clocks/used slope basis. Actual retained7-country snapshot after must preserve all numeric/scoring fields; only new metadata and true source-age stale state may differ. Actual authored global-detail fragment+C styles,8 changed dark/light×EN/ZH×1440/390 cells; keyboard/touch details open, exact source hrefs, incumbent hash entry/back. All requests blocked beyond controlled local fixture, no held browser/profile/ports/provider. Reuse accepted gauge16cells untouched; source tests affected only, no broad rerun/newPR/workflow.

RETURN: source-only isolated patch+focused tests+offline changed-region proof, exact original worker outcomes, one root limited nonauthor source/provenance/visual judgment. Hosted/SharedShell bridge and served publication remain explicit downstream obligations under existing release custody.

## Prospective v2 integration amendment — after exact C1 terminal return

Original packet SHA256 fc1d1d5d0f55a153a7b2cc681464ba35b24d8459546d2f68919c0179ac5f41ae. Both original C0/C1 settled with no useful output on the admitted route (EAI_AGAIN/provider_error), no project source effects or active writer; no quality acceptance and no retry/replacement. Root explicitly authorized native isolated completion after exact23041 consumption. Parent now owns local implementation.

The observed blue section-heading marker is local templates/bonds.html.j2:119–120 `.sec-head::before` width3px/background:var(--accent-grad). Remove that decorative pseudo-element rule only; retain the neutral ::after divider and every gauge/style/model geometry region. No shared stylesheet or token family is changed. This is the sole CSS exception to v1, frozen before source mutation.

Focused regressions go in existing CI-covered tests/test_bonds_glance_copy.py (legacy CCW-W4 job explicitly runs it), rather than the uncovered tests/test_bond_hub.py proposed to the failed worker. No CI definition/manifest edit. Source paths: engine/intl_bonds.py, templates/bonds.html.j2, tests/test_bonds_glance_copy.py.
