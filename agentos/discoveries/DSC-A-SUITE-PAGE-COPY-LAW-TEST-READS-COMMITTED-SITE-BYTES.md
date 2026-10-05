---
key: A-SUITE-PAGE-COPY-LAW-TEST-READS-COMMITTED-SITE-BYTES
claim: "The market-os-macro-suite-pages job runs its ZH copy-law pytest over the COMMITTED site/*.html pages and never rebuilds them, so a library-only heal cannot green the job until a render re-bakes the page."
falsifier: "`grep -n 'build_macro_suite_pages' .github/ci/legacy-jobs.yml` showing a build step in the market-os-macro-suite-pages run line (then a lib fix would self-green)."
so_what: "A suite-page heal is lib fix + test, merged on concluded checks with the red attributed by logical job + test + tuple, then a render re-bake (scope=macro after the live render concludes, or nightly scope=all) \u2014 never a committed rebuilt page (DEC:SUITE-PAGE-HEALS-SHIP-LIB-PLUS-RENDER)."
kind: constraint
verified_at: 2026-10-02
verified_by: "PR #8288 (merge 4aa073e063f5) stayed red on the Recession tuple until render 37055118662 SUCCESS 20:24:46Z; main proof 37060732646 then green"
scope:
  - "macro"
  - "WS:MARKET-OS"
  - "site/macro_*.html"
  - ".github/ci/legacy-jobs.yml"
confidence: verified
---

Measured 2026-10-02 on `('macro_national_debt_liabilities.html','Recession')`: the heal lib landed 18:54Z, the pack stayed red through main proof 37043074910, and greened only after the macro-scope render re-baked the page.
