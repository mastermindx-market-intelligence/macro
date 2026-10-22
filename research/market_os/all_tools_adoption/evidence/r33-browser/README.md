# Shared Shell R33 — admitted-pilot real-browser proof

**BUILT_NOT_PROVEN · PR7949 remains DRAFT / HOLD-FOR-SOL · no deployment or personal-state effect**

Implementation commit: `7731fad48406fd3875cbf012b0665f0b9adf4580`.

The committed manual Playwright harness under `research/market_os/all_tools_adoption/browser/` ran against the exact committed `site/` tree in Google Chrome 154.0.8037.58. All eight real-browser cases passed.

## Browser matrix

- `macro.html`, `sector_central.html`, and `reports.html`: desktop 1440×1000, dark theme, English; open, search, honest no-match recovery, reset, Escape and focus return.
- The same three pilots: mobile 390×844, light theme, Chinese; heading focus, translated labels, close affordance and viewport-bounded sheet.
- Existing live modal refusal and source-withdrawal fail-closed behavior.
- Shared `theme.js`, `account.js`, and `nav_market.js` responses observed with HTTP 200.
- Desktop footer isolation is measured: footer width equals shell width, `max-width:none`, `margin-top:0px`.

## Browser-discovered repair

The first visual pass exposed a real page-specific defect on Sector Central: its generic `footer { max-width:95ch; margin-top:30px }` rule leaked into `.mmx-tools-footer`, shrinking and offsetting the dialog footer. A red-first source regression was added, then the existing shared navigation stylesheet was minimally hardened with `width:100%`, `max-width:none`, and `margin:0`. The paired template/site assets remain byte-identical.

The changed stylesheet now hashes to `791020aa`. Only the three admitted pilot pages were re-stamped to `navigation-refresh.css?v=791020aa` for both preload and stylesheet links; this does not widen the pilot or create another asset owner.

## Fresh verification

- All tools integration: **10 passed**, including the production-controller suite (**97 Node tests**).
- Template↔site sync: **105 pairs checked / PASS**.
- Complete targeted product-chrome contract: **236 passed, 1 current-main-identical baseline failure, 4 warnings** across 237 collected tests.
- Real Chrome/Playwright matrix: **8 passed, 0 failed**.

## Visual evidence

- `macro-desktop-dark-en.png` — 207854 bytes — SHA256 `2cdbf1b4099a1d932947b137ef0a4c79f3b4d9ec96cef816e1dc3687decebb79`
- `macro-mobile-light-zh.png` — 65693 bytes — SHA256 `b0e912d05094247e3438185193bc285ee9bc7a246105967d53481078ff35bcb2`
- `reports-desktop-dark-en.png` — 182522 bytes — SHA256 `16ab5aa642497cda876979af8cadf4ee7493bc194ae54c42fa08ea363ddc0dde`
- `reports-mobile-light-zh.png` — 66329 bytes — SHA256 `e74e915b53ad755ea5e287fcd97c3565c119c704c3394a58a44437ca7ec3661b`
- `sector_central-desktop-dark-en.png` — 199345 bytes — SHA256 `96948309e9d0f0ab750656bf7c594dd836ce90ecaa3a8030c443092892219e24`
- `sector_central-mobile-light-zh.png` — 67565 bytes — SHA256 `1c2e87b24626d12812e1efe2ce8f95b4acbf97a1f818a36463352ee1822d1792`

Screenshots were reviewed after the footer repair. The three desktop dialogs have a full-width footer and clean lane alignment; the three mobile Chinese sheets remain readable, viewport-bounded, and retain their reachable footer.

## Boundary

This is real local-browser evidence against the exact committed static tree. It is not a deployment, CDN-cache, authenticated-state, Safari/Firefox, physical-device, screen-reader, or 200% text acceptance receipt. Exact-head review/CI and normal release admission remain separate. No merge, ready-for-review transition, automatic merge, deployment, watcher, worker, account write or user-data effect occurred.
