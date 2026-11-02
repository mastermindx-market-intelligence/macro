---
key: SUITE-PAGE-HEALS-SHIP-LIB-PLUS-RENDER
question: "When the market-os-macro-suite-pages copy-law test is red on a committed site/*.html page (ZH span untranslated), does the heal PR commit a rebuilt page, or ship the library fix alone?"
answer: "Ship lib + test only (#8288: OWNER_VALUE phase pairs in the ZH copy law + pinned test), then let the render pipeline re-bake the page (dispatch render.yml scope=macro once the live render has CONCLUDED, or wait for the nightly scope=all). Never commit a lane- or seat-rebuilt suite page."
rationale: "The suite-pages job runs pytest over COMMITTED site/*.html bytes and never rebuilds, so a lib-only heal cannot green it until a render rewrites the page. But scripts/build_macro_suite_pages.py emits no ?v=/defer stamps \u2014 those come from scripts.optimize_assets at the end of render.yml (:1281) \u2014 so a page rebuilt outside the render lane is unstamped (seat rebuild vs main: 374 diff lines, 0 ?v=) and committing it would ship a regression to every cached referencing page. The render lane is the only lawful re-baker."
alternatives:
  - option: "Commit the rebuilt macro_national_debt_liabilities.html in the heal PR"
    why_not: "the rebuilt page is unstamped (0 ?v=) and 374 lines off main's; it would be overwritten by the next render anyway and ship a cache-busting regression meanwhile"
  - option: "Cancel the in-flight render and dispatch a fresh one at the heal head"
    why_not: "forbidden (gh_quota_guard shape 6; a cancel is invisible to every staleness instrument) \u2014 the live render concludes first, then one macro-scope dispatch"
  - option: "Whitelist the Recession tuple in the copy-law test"
    why_not: "hides a real ZH defect (\u8870\u9000 missing) instead of fixing the OWNER_VALUE source"
evidence:
  - "PR #8288 (F01_NATIONAL_DEBT_PHASE_ZH_HEAL_R1, m1 lane rs_20261002T180123Z_92698) MERGED 4aa073e063f5 2026-10-02T18:54:07Z; its PR-side red sat in ci-pack-4 while main's proof had the same logical job in ci-pack-10"
  - "render 37055118662 (scope=macro at 6246d8860ffe) SUCCESS 20:24:46Z re-baked site/macro_national_debt_liabilities.html with \u8870\u9000; main proof 37060732646 SUCCESS 21:35:58Z (head 20258f7de107) greened ci-pack-10"
  - "seat measurement: `python3 scripts/build_macro_suite_pages.py` output vs origin/main site page = 374 diff lines, 0 `?v=`; render.yml:1281 scripts.optimize_assets is the stamper"
  - "program file rulings D41, D43"
affects:
  - "WS:MARKET-OS"
  - "scripts/build_macro_suite_pages.py"
  - "scripts/build_bonds.py"
  - "site/macro_*.html"
  - ".github/workflows/render.yml"
confidence: high
reversibility: easy
decided_by: "CEO A seat 587e986f-b055-4df2-a9ed-ca3a709fcc5b (Claude Fable 5.1), single F00 writer under the Astra handoff on macro#6819"
decided_at: 2026-10-02
---

## Shape of a suite-page heal

1. Reproduce the copy-law failure on the committed page (tuple quoted).
2. Fix the SOURCE (lib pairs, template) + pin a unit test on the pairs.
3. Merge on concluded checks, attributing the suite-pages red by logical job + test + tuple
   (its pack index differs between the PR and main — `DSC:A-PRS-PACK-INDEX-DIFFERS-FROM-MAINS`).
4. Re-bake through render.yml only (macro scope after the live render concludes, or nightly).
5. A postdating main proof greens the pack; sweeper/hand-merge siblings then clear.
