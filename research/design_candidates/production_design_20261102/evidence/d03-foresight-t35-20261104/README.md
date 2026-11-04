# D03 T35 — Foresight entry-window source state

Status: source repair and fixture browser proof, Draft / HOLD. Not merged, deployed, or production-accepted.
Parent: [D03 checkpoint](https://github.com/mastermindx-market-intelligence/macro/pull/10617#issuecomment-6623889088).
Specification: `D03_US_PROPHET_PHASE_2A.md` at `e521f04dcc5afb4fb06152584d35c8a01dbe21ff`, T35 / F04.
Base: `005232fa54edbc6d271a796db6b15d5cd7443641`, refreshed unchanged before publication.
Protected procedure: Mastermind `75a6540519cf519edfef7633e74f57b68aef9329`.

## Observable result

Missing or malformed dislocation projections now say **Unavailable**, not **Closed**.
A valid Boolean `active=false` remains Closed unless `verdict=buyable_washout`; that established exception remains Open.
A verdict must be absent, null or text. Only a nonblank text headline is displayed, and remains escaped.
Unknown source reason and observation time stay explicitly unavailable. Page-generation time is not reused as a source clock.

This is a presenter repair, not a signal-engine change. The upstream projector still Boolean-normalizes some raw values;
the template cannot recover producer distinctions already lost upstream. The full F04 typed availability/reason/clock obligation remains **BLOCKED_DATA**.
Scores, stages, rankings, controls, cohort membership, entry eligibility and position sizing are unchanged.

## Native Paper evidence

- File: PROPHET `01M3NT5Y3G5HTJHVR0K5W2MDJM`; page `p-D-0`; board `10Z3-0`.
- [Open the D03 page](https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-D-0).
- Actual final capture: [entry-state-contract.paper.jpg](entry-state-contract.paper.jpg).
- JSX extracted after visual QA: [entry-state-contract.paper.jsx](entry-state-contract.paper.jsx).
- Final semantic update `d03-t35-contract-input-shapes-20261104-c2` and final finish
  `d03-t35-final-contract-finish-20261104-c2` both returned APPLIED_RESPONSE_OBSERVED.
- Snapshot guard `989079ab7271f971a2886d4d7cbe3968ce15a3050d6385cba3fa00dd8510100b` is not an immutable document revision.
- Image SHA256: `2052e54113055113256e0edd5beb81c30f76337b52aaf38ec5ac4c123e5cd0f5`.
- JSX SHA256: `609bfeb8d728e5d69493a4c877896c0be1dfd0cf2662f3ca7959b09317956da9`.

The component specification uses 288px cards to exercise narrow content.
The real existing page has its own 18px body gutters. No F01/F02 final-release claim or global shell/token change is made.
Original R8 held effect on ZE5-0 and the #9495 source workspace remain untouched.

## Browser proof

[verify_browser.py](verify_browser.py) renders the actual Jinja template, shared theme CSS/JS, icons and existing test row
in Chromium 151.0.7922.34. It intercepts every request and never contacts production.
The fixture's 2026-10-20 date, score 45, rare-earth row and “synthetic fixture” text are examples, not current market data.
The only unrelated request stubbed was `/case/live_config.js`. No JavaScript page errors occurred.

[Machine receipt](browser-proof.json): **36 cases** = 3 states × 3 widths (320/390/1440) × 2 themes × 2 languages.
Every case retains the existing theme card and checks state, language, text sizes, neutral uniform border, hidden decorative SVG,
local overflow, contrast and reduced-motion behavior. No full-page horizontal overflow was measured.
The minimum measured contrast of the three gate text roles is **5.219:1**.
Settings → theme/language changes → keyboard activation → Escape passed at 390 and 1440.

Representative retained captures:

| State/context | Capture |
|---|---|
| Unavailable, 320 light EN | [image](unavailable-320-light-en.png) |
| Unavailable, 320 dark ZH | [image](unavailable-320-dark-zh.png) |
| Closed, 390 dark EN | [image](closed-390-dark-en.png) |
| Open, 320 light ZH | [image](open-320-light-zh.png) |
| Open, 1440 dark EN | [image](open-1440-dark-en.png) |
| Actual full template, 390 light EN | [image](page-390-light-en.png) |
| Actual full template, 1440 dark ZH | [image](page-1440-dark-zh.png) |

All 36 measurements are retained; the renderer can regenerate the full screenshot matrix.
The final source template SHA256 is `8546c95ef36bc63b470541b71f1f60d73c8c1698978eb7d86ccb8adb8c133515`.
The proof runner verifies the source and records theme-asset hashes.

To reproduce using the existing installed Playwright Chromium, Jinja2 and pytest:

```bash
proof_dir=$(mktemp -d /tmp/d03-t35-browser.XXXXXX)
python3 research/design_candidates/production_design_20261102/evidence/d03-foresight-t35-20261104/verify_browser.py --repo "$PWD" --out "$proof_dir"
```

Harness corrections are disclosed: the first interaction attempt selected the obsolete hidden `.theme-switch`;
inspection showed that the real shared Settings three-way control replaces it. The final runner uses that real control.
Element captures use a normal centred scroll position so the existing fixed chat launcher does not obscure the gate;
no CSS masking, hidden launcher, or production layout alteration is used. The full-page captures retain the shared launcher.

## Source/CI proof

- Initial 22-case suite against old source: **20 failed / 2 passed**.
- Added malformed verdict/headline probes before the final guards: **12 failed / 28 passed**.
- Final combined six page-reader suites plus cascade/health/score/sizing: **213 passed**.
  The new T35 suite contributes 40 cases.
- Three CI guards passed: declared scope coverage, referenced test paths, curated exclusive closure.
- Existing 12-pack code-gate manifest validated all **312 logical jobs**; no new job or pack-limit change.
- Actual selection: test, template and builder each match existing code-gated
  `healthcare-fda-supply` as a declared exclusive owner.
- `git diff --check` and author diff/visual self-QA passed.

No generated repository `site/` or market data was changed. After lawful release, the normal builder and served Foresight page
still need exact-source and real-route acceptance. A fixture render or green CI does not establish production deployment.
