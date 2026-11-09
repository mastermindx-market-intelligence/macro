# Confluence metadata and navigable combination headings

## What changes for readers

Search and shared-link descriptions now describe the actual research task without promising signals that are firing right now:

> Compare historical evidence for technical signal combinations across large US stocks, including recent and older periods.

The existing `seo_desc` supplies the same description to the ordinary, Open Graph and Twitter fields. Titles, canonical URL and all other metadata remain unchanged.

An empty or unavailable source also stops advertising the retained positive-result image. When the existing qualified `combos` collection is nonempty, the page retains its Confluence PNG and large-image card type. Otherwise the page leaves `seo_image` and `seo_card` undefined, allowing the existing shared helper to emit its generic icon and summary card.

The three combination names are now H3 headings beneath the evidence-list H2. Readers using heading navigation can reach each combination directly. Existing text, order and visual styling are unchanged; `margin:0` prevents browser heading margins from changing card layout. No extra tab stop, action, ID or disclosure label is introduced.

## Existing ownership and historical adoption

The image predicate is adopted from [historical commit 143dded8a0a0f4f0a7e24396e8d169292135d9e0](https://github.com/mastermindx-market-intelligence/Macro/commit/143dded8a0a0f4f0a7e24396e8d169292135d9e0). It is retained work applied to the current source, not a newly invented metadata system. That historical commit also proposed image-file cleanup; this increment does not adopt that separate effect.

`scripts/build_confluence_screener.py` remains the source qualifier and producer. Its unavailable and qualified-zero contexts both have no displayed combinations. `templates/_seo_head.html.j2` remains the metadata owner, with existing defaults:

| Page state | Open Graph and Twitter image | Twitter card |
|---|---|---|
| Qualified source with displayed combinations | `https://www.mastermind-x.com/og/confluence_screener.png` | `summary_large_image` |
| Qualified source with no eligible combination | `https://www.mastermind-x.com/apple-touch-icon.png` | `summary` |
| Source unavailable | `https://www.mastermind-x.com/apple-touch-icon.png` | `summary` |

Keep the variables **undefined** in the latter two states. Assigning an empty string would bypass the helper's existing undefined-value default and could produce the wrong URL.

This is an HTML metadata correction. It does not generate, delete, replace or qualify an image asset. A positive source whose image renderer fails can still advertise a retained PNG; that existing publication risk is separate. External search/social caches are not refreshed or inspected by these local checks.

The historical source is linked from [PR8332](https://github.com/mastermindx-market-intelligence/Macro/pull/8332) as PR8428. A fresh PR8428 read returned 404, so its current status is unresolved. PR8332 reports visual request 5985261197 as unfulfilled and offline fixture/asset preparation as blocked before dispatch, with no PID, page or screenshot. Its original reason/category was not verified. That block is preserved: this work neither recreates those visual fixtures nor replays that request.

## Exact source change

Parent: `26e0b8ba9ad322dc7c47a1dc1e0bead789589173`.

Four exact template substitutions:

1. Replace the existing description with snapshot-faithful research copy.
2. Wrap the two page-specific image/card assignments in the historical `if combos` predicate.
3. Add `margin:0` to the existing `.lc-title` rule.
4. Change the existing bilingual combination-title wrapper from DIV to H3.

The saved positive page changes three emitted descriptions, three title tags and one local CSS rule. Its image metadata stays exact. Reversing those substitutions restores its parent bytes. This is a bounded saved-component projection; its emitted metadata and combination headings are checked against the actual current-input Jinja render.

Complete body content reverses exactly by restoring only the three title tags. Scripts, methods, action labels/hrefs, source clocks, footer, counts, ranking and protected data remain exact. All CSS reverses exactly with the one margin addition. Builder, shared SEO helper and protected JSON are byte-identical to the parent; protected JSON still matches the actual producer. Source receipt remains `4f8c3dcd8508a55978f4b27d7c4d34828bc1044881ed404120cb353b1d4dc7c1`, built 2026-11-08T11:31:29Z.

## Current rendered-metadata proof

Three existing test functions gain tag-level assertions. A small HTMLParser helper records image/card values as lists, so duplicate metadata cannot silently satisfy a broad substring assertion. No new test case or image writer is introduced.

- The positive render retains both specific image tags and the large-image card type.
- The existing qualified-zero/unavailable test checks their generic image and summary card.
- All nine existing actual-render overwrite cases check the tags written by the real Jinja and page writer: missing, malformed JSON, non-object, read error, missing collection, missing clock, invalid clock, mixed malformed row and qualified zero.

These actual writer cases have no combinations, so their existing image-generation branch is not entered. No PNG is seeded, generated or removed for this proof.

**92 existing page cases pass**, PID 96506, 20.36 seconds pytest /24.55seconds process. The baseline, with only the new assertions and the parent template, passed the positive case and failed ten expectations (PID 86357, 2.29 seconds pytest /4.75 seconds process, 81 deselected). These failures expose the same incorrect image-selection behavior across existing source states; they are not ten independent product defects.

Pure before/after Jinja projections also compare the current positive source, the existing qualified synthetic zero source and unavailable input. All three descriptions match the replacement. Image/card fields follow the table above; other metadata tags stay exact. The zero fixture remains source time 2026-07-19T04:00:00Z; it is not current-source data.

- [Full source, process, adoption and reproduction receipts](METADATA_HEADING_VALIDATION.json)
- [Original current-source baseline output](METADATA_HEADING_BASELINE.txt)

## Combination-heading proof

A bounded native DOM/geometry inspection compares the actual parent/current saved positive pages in EN dark and ZH light at 320px and 1440px: **four contexts, eight page observations, 24 card observations**, zero page errors, Chrome 157.0.8103.39, 26.73 seconds process.

Each page gains three combination H3 headings in unchanged source order. Each active-language title resolves to exactly one heading through the browser role locator. H1/H2 hierarchy stays unchanged. Title/card boxes, computed type properties, action geometry, labels and hrefs compare exactly before/after; title margins are zero. Document width is unchanged and all card titles remain contained.

This inspection took **zero screenshots** and exercised no image-generation or account action. It is DOM/geometry evidence for the newly changed title semantics, not spoken assistive-technology proof, a new functional regression suite or fulfillment of the historical share-card visual request.

[Original inspection report](METADATA_HEADING_INSPECTION.json) is retained unchanged. One diagnostic selector used `.methods` rather than `.lc-method`, so all 24 recorded method fields are null. Its combined `methods_actions_exact` label therefore establishes action equality only. Method conservation is independently established by the exact source/body inverses; no runtime method proof is claimed from those null fields.

## Reproduce and build

```bash
python3 -B -m pytest -q tests/test_confluence_screener_page.py --disable-warnings
```

The validation file retains the exact current-source projection, baseline, final test and bounded DOM-inspection commands. The latter is a one-time inspection, not a new permanent harness.

Use the existing page template and shared metadata include. Keep combination titles as the existing bilingual content inside H3, with the existing 16px/700/1.35 type and zero margins. Keep the native method disclosure and company actions intact. Paper anatomy remains unchanged visually; the Build contract names this semantic hierarchy and the metadata ownership.

PR10893 remains Draft/unarmed. Incumbent PR10705 admission/calendar, historical visual effects, positive-image publication, source/model, programme and release boundaries remain. No hosted preview, deployed cache, live entitlement or production acceptance is claimed.
