# Crypto R4: implementation and build map

This is the dependent candidate for reliable saved cases, asset readings and navigation in [Macro PR #10901](https://github.com/mastermindx-market-intelligence/Macro/pull/10901). Start with the workflow below, then open its contract and exact proof.

**Latest recorded runtime proof: 9 November 2026, assets `2698fd4fd4ed`; [current-case navigation receipt](current-return/PUBLICATION_RECEIPT.json).** The candidate remains Draft, unmerged and unarmed. Its incumbent base is [PR #9580](https://github.com/mastermindx-market-intelligence/Macro/pull/9580) at `5e496c24c962e85a4f7f514dd43dc61443b95cab`. These are recorded checkpoints, not live-head assertions.

## Find the workflow

| User task or failure | Builder contract | Exact verification |
|---|---|---|
| Save or remove a specific snapshot; handle unreadable storage or uncertain completion | [Storage and snapshot safety](SNAPSHOT_SAFETY.md) | [Validation and limits](SNAPSHOT_VALIDATION.json) |
| Reopen the original saved horizon; return to the same version and reading position | [Saved navigation](NAVIGATION.md) | [Navigation validation](NAVIGATION_VALIDATION.json) |
| Read a frozen case, its condition and retained evidence; distinguish unavailable historical results | [Frozen-case hierarchy](FROZEN_LAYOUT.md) | [Layout validation](FROZEN_LAYOUT_VALIDATION.json) |
| Distinguish an open, expired, future-dated or unverifiable case before inspection | [Scenario-card lifecycle](SCENARIO_CARD_LIFECYCLE.md) | [Native proof and exact scope](card-lifecycle/PUBLICATION_RECEIPT.json) |
| Return from current Historical review, keep the case reading and start new review entries clearly | [Current-case review and return](CURRENT_CASE_RETURN.md) | [Native proof and exact scope](current-return/PUBLICATION_RECEIPT.json) |
| Recover from a missing current scenario or named review | [Current-case recovery](SCENARIO_RECOVERY.md) | [Native proof](scenario-recovery/PUBLICATION_RECEIPT.json) |
| Copy/open route links with their context; navigate without hiding the focused control | [Native navigation](NATIVE_NAVIGATION.md) | [Native proof](route-context/PUBLICATION_RECEIPT.json) · [Captures](route-context/CAPTURE_REFERENCES.json) |
| Understand price change versus Asset/BTC ratio change; compare the complete cohort | [Comparison meaning and ownership](COMPARISON_BASIS.md) | [Comparison validation](COMPARISON_VALIDATION.json) |
| Read complete dates and values in a narrow comparison matrix | [Compact matrix](COMPACT_MATRIX.md) | [Matrix validation](COMPACT_MATRIX_VALIDATION.json) |
| Distinguish a numeric relative reading, genuine zero and unavailable evidence | [Relative-state integrity](RELATIVE_INTEGRITY.md) | [Projection and browser proof](RELATIVE_INTEGRITY_VALIDATION.json) |
| Read small quotes accurately; distinguish unavailable prices | [Quote clarity](QUOTE_CLARITY.md) | [Quote validation](QUOTE_CLARITY_VALIDATION.json) |
| Identify an asset once and read its quote beside its observation date | [Asset identity and hierarchy](ASSET_READING.md) | [Native proof](asset-reading/PUBLICATION_RECEIPT.json) |
| Scan Overview labels and aligned headings | [Overview clarity](OVERVIEW_CLARITY.md) | [Overview proof](overview/PUBLICATION_RECEIPT.json) |
| Reach the final methods control above the shared launcher | [Footer clearance](FOOTER_CLEARANCE.md) | [Footer proof](footer/PUBLICATION_RECEIPT.json) |

Each receipt defines its own inputs, cases, corrections, captures and limitations. Counts from different phases overlap; do not add them into a new complete-suite claim. The original storage proof is **76 initial passes plus three affected dependency-recovery passes**, not one 79-pass run. The native-navigation phase has 23 affected passing cases. Scenario-card lifecycle has 45 unique affected passing cases across an initial 40-pass run and five corrected affected passes; its runtime remained unchanged during that correction. Neither is a complete browser-suite rerun.

## Existing implementation owners

| Concern | Continue in this owner | Preserve |
|---|---|---|
| Public projection, numeric qualification and supplied evidence | `lib/crypto_intelligence_view.py` | Source units, null versus zero, historical cutoff and model authority |
| Rendered page and static fallback | `templates/crypto_intelligence_r4.html.j2` | Progressive enhancement, supplied data and locale text |
| Routes, drawers, saved records and focus | `templates/crypto_intelligence_r4.js` | Existing `address()`, `update()`, `apply()`, history and storage owners |
| Layout, hierarchy and responsive behavior | `templates/crypto_intelligence_r4.css` | Existing shell, readable type, full evidence and native overflow |
| Candidate generation and served assets | `scripts/build_crypto_intelligence_r4.py` and `site/crypto-r4.html` / `site/vector-r4.html` | Exact input identity, template/served parity and explicit asset references |
| Affected proof | `tests/test_crypto_intelligence_r4.py` and `tests/test_crypto_intelligence_r4_browser.py` | Real rendered fixtures, current owner behavior and bounded claims |

Extend these owners. Do not add a second router, history store, save registry, retry lifecycle, comparison calculator or model pipeline.

## Open the editable design

- [Start and source map](https://app.paper.design/file/01M6Y3F0NXNDPAKJMJGCAD759Z/p-5-0): current page purposes and retained archive boundary.
- [Interaction references and scorecard](https://app.paper.design/file/01M6Y3F0NXNDPAKJMJGCAD759Z/p-1-0): `QI-0` records implementation scope; `G5-0` links current-case recovery and saved states.
- [Asset readings](https://app.paper.design/file/01M6Y3F0NXNDPAKJMJGCAD759Z/p-3-0): Build `2ZJ-0`; candidate UI beside **proposed paired-receipt** states. Quote companion `3N8-0` has verified contents/dimensions; its freeform canvas coordinates remain unreported.
- [Saved cases](https://app.paper.design/file/01M6Y3F0NXNDPAKJMJGCAD759Z/p-4-0): Build `3IP-0`; implemented candidate states beside **proposed qualified historical results**. States 09–18 include legacy, missing and unreadable recovery.

The full portfolio audit remains in [PR #10617](https://github.com/mastermindx-market-intelligence/Macro/pull/10617). A Paper specimen, a source implementation, local browser proof and production acceptance are different claims.

## Next bounded work

**Recorded on 9 November 2026:** scenario-card lifecycle qualification is implemented and locally verified. Next, add a same-case return from a valid current review through the existing history owner. Preserve whole-drawer Close, saved-case return/reading state, missing-case recovery and newer-choice safeguards.

Model/H5 authority, alert integration, paired receipts, qualified historical results, hosted/independent visual acceptance, public-route cutover and admission/release remain with their existing owners. Historical or synthetic local fixtures do not establish current-market freshness or production acceptance.

## Evidence history

All phase contracts, source transformations, harness diagnostics, receipts and captures remain in place. The [complete previous landing page](README_PHASE_HISTORY_20261109.md) is an exact snapshot from source `e70fc60183c83565497c431c433b0594423cc7cb`; its “current” and “next” wording belongs to that historical snapshot.

<details>
<summary>Earlier section destinations</summary>

<a id="crypto-r4-reliable-cases-asset-readings-and-navigation"></a>

- [Crypto R4: reliable cases, asset readings and navigation](README_PHASE_HISTORY_20261109.md#crypto-r4-reliable-cases-asset-readings-and-navigation)

<a id="current-phase--native-context-and-focus-continuity"></a>

- [Current phase — native context and focus continuity](README_PHASE_HISTORY_20261109.md#current-phase--native-context-and-focus-continuity)

<a id="prior-phase--honest-missing-case-recovery"></a>

- [Prior phase — honest missing-case recovery](README_PHASE_HISTORY_20261109.md#prior-phase--honest-missing-case-recovery)

<a id="prior-phase--clear-asset-identity-and-quote-hierarchy"></a>

- [Prior phase — clear asset identity and quote hierarchy](README_PHASE_HISTORY_20261109.md#prior-phase--clear-asset-identity-and-quote-hierarchy)

<a id="prior-phase--honest-quote-availability-and-useful-small-prices"></a>

- [Prior phase — honest quote availability and useful small prices](README_PHASE_HISTORY_20261109.md#prior-phase--honest-quote-availability-and-useful-small-prices)

<a id="prior-phase--footer-actions-clear-the-shared-launcher"></a>

- [Prior phase — footer actions clear the shared launcher](README_PHASE_HISTORY_20261109.md#prior-phase--footer-actions-clear-the-shared-launcher)

<a id="prior-phase--clear-overview-fields-and-aligned-section-headings"></a>

- [Prior phase — clear Overview fields and aligned section headings](README_PHASE_HISTORY_20261109.md#prior-phase--clear-overview-fields-and-aligned-section-headings)

<a id="prior-phase--qualified-relative-values-and-bilingual-states"></a>

- [Prior phase — qualified relative values and bilingual states](README_PHASE_HISTORY_20261109.md#prior-phase--qualified-relative-values-and-bilingual-states)

<a id="prior-phase--complete-comparison-readings-on-narrow-screens"></a>

- [Prior phase — complete comparison readings on narrow screens](README_PHASE_HISTORY_20261109.md#prior-phase--complete-comparison-readings-on-narrow-screens)

<a id="prior-phase--honest-comparison-basis-and-usable-asset-workflows"></a>

- [Prior phase — honest comparison basis and usable asset workflows](README_PHASE_HISTORY_20261109.md#prior-phase--honest-comparison-basis-and-usable-asset-workflows)

<a id="prior-phase--original-condition-first-saved-cases"></a>

- [Prior phase — original-condition-first saved cases](README_PHASE_HISTORY_20261109.md#prior-phase--original-condition-first-saved-cases)

<a id="prior-phase--saved-case-navigation-verified"></a>

- [Prior phase — saved-case navigation verified](README_PHASE_HISTORY_20261109.md#prior-phase--saved-case-navigation-verified)

<a id="prior-completed-phase--storage-safety"></a>

- [Prior completed phase — storage safety](README_PHASE_HISTORY_20261109.md#prior-completed-phase--storage-safety)

<a id="implemented"></a>

- [Implemented](README_PHASE_HISTORY_20261109.md#implemented)

<a id="verification"></a>

- [Verification](README_PHASE_HISTORY_20261109.md#verification)

<a id="build-contract-and-evidence"></a>

- [Build contract and evidence](README_PHASE_HISTORY_20261109.md#build-contract-and-evidence)

</details>
