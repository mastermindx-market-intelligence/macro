# Asset identity and quote reading hierarchy

## Outcome

The asset inspector now gives the quote a clear visual focus and groups its explicitly labeled observation date directly underneath. Fallback identity appears once: **BTC**, rather than BTC · BTC. Distinct names remain **Ethereum · ETH** and **Solana · SOL**.

This presentation phase follows source `0c895f7bf5585f152f7bc0c6fc5eb23b6ec057c6` in dependent Draft PR #10901. Quote arithmetic, projection, producer data and navigation ownership remain unchanged.

## Identity rule

| Supplied name and symbol | Overview / Markets | Inspector title |
|---|---|---|
| Ethereum / ETH | Ethereum with secondary ETH | Ethereum · ETH |
| Solana / SOL | Solana with secondary SOL | Solana · SOL |
| BTC / BTC | BTC | BTC |
| Surrounding whitespace and case variant of BTC / BTC | BTC | BTC |
| Missing, non-string or blank name / XRP | XRP | XRP |
| Distinct meaningful name / symbol | Preserve the supplied name and secondary symbol | Preserve the supplied name · symbol |

Trim and lowercase only for the equality decision. Preserve the original primary name when distinct and the original symbol when falling back. Do not normalize source keys, add a name catalogue, infer localized names or collapse separate assets.

The Jinja `asset_identity` macro serves Overview and Markets. Its stacked form keeps the existing secondary `small` element only for distinct names. The pure JavaScript `assetTitle` helper applies the same decision to the existing drawer title. The Markets coin initial is decorative and now has `aria-hidden="true"`, so an accessible button name does not repeat the ticker's first letter.

Search continues to use the existing name/symbol corpus. Routes, `data-open`, `data-asset-row`, source ordering and symbol-only comparison headings are unchanged. The display repair does not mutate retained view JSON.

## Quote and date hierarchy

The price remains a definition-list value with its existing Price / 价格 term. Its value uses **30px / 38px, weight 600, tabular numerals**. The same neutral text treatment applies to ordinary quotes, Unavailable / 暂无 and the complete <$0.00000001 bound.

The price row has no top padding or lower divider, and has 8px bottom padding. The observation-date row has no top padding and retains its lower divider. This groups the quote and date before the other measures without adding a card, banner or footnote. The full **Asset observation date / 资产观测日期** label remains; the bare date in an isolated design component is not substituted for it.

Comparison basis stays first, with its visible window qualification and disclosure. Price change, Asset/BTC ratio change, relative state, structure and risk remain in their previous order and retain their supplied values.

### Existing implementation owner

`definition()` now returns the same list it already appends. The asset branch marks only the first two known Price/date rows on that returned list. This matters because the preceding comparison-basis disclosure contains its own definition list; a drawer-wide first-list selector would target the wrong content.

The scoped CSS selectors are:

- `.cri-dialog-body .cri-asset-quote`
- `.cri-dialog-body .cri-asset-quote > dd`
- `.cri-dialog-body .cri-asset-observed`

They override the existing generic row padding at the required specificity. Generic definition styles remain exact, and other callers ignore the new return value. If the asset field order changes later, update these marker assignments with that order; do not find rows by translated labels.

There is no new focusable element, route, state owner or animation. Close and existing history behavior stay with the current drawer owner.

## Paper alignment and builder navigation

File `01M6Y3F0NXNDPAKJMJGCAD759Z` retains the same page and board IDs.

The quote companion `3N8-0` carries the implemented price typography and an added concise identity rule. Its component shell remains a design reference; the native inspector retains the explicitly labeled date and existing comparison disclosure.

The active Markets reference `8E-0` had older copy implying calendar-day returns and a shared comparison window. Eight text nodes are aligned with the existing producer/consumer contract:

| Node | Final wording |
|---|---|
| 9R-0 | Ratio change ▾ |
| 9V-0 | Price change |
| 9W-0 | Asset/BTC ratio change |
| AJ-0 | Asset/BTC ratio change |
| AK-0 | 90-step rule |
| AV-0 | Paired window not supplied; compare each reading with its risk state. |
| B1-0 | Solana · SOL |
| B6-0 | Paired window not supplied. / Asset observation · 15 Oct 2026. |

The displayed historical values and risk/structure states remain intact. The bar/reference panel is not a claim that a new native chart was implemented. Ninety shared observation steps is the producer's calculation rule; emitted paired-window endpoints and counts remain proposed.

Builder navigation is also being aligned with the actual source status: comparison, quote and saved-case presentation have locally verified candidate implementations in PR #10901. Paired-window receipts and qualified historical review remain unfinished. Public-route cutover and release acceptance remain separate. The canonical page IDs and source owners are preserved.

The quote companion's canvas position fields remain unreported by the adapter. Its rendered component and page membership are established; exact canvas spacing is not claimed.

## Verification

The exact parent with the new/extended checks returned **six expected browser failures and 15 passing server-price checks**. Four failures showed the previous 14px undifferentiated quote; two showed repeated or invalid fallback identity.

The candidate returned **21 passed in 12.59s**: 15 unchanged server-price cases and six browser cases. Native subprocess: 12.849s. Chrome 157.0.8103.39, six fresh contexts/pages, zero page errors or external/WebSocket traffic.

The four existing quote cases now also check the actual 30px/38px/600 value, intact single-line bound, 8px quote-to-date gap, explicit date label, normal date size and no quote divider. Their 18 asset Inspect→Close journeys retain price strings, supporting fields, opener focus and untouched storage.

Two new EN390/ZH320 identity workflows check:

- Overview fallback labels and exact asset open/return.
- Accessible Markets button names, with no decorative-initial duplication.
- Canonical name preservation and fallback drawer titles.
- Search by ticker and name, opening the same asset and retaining search/focus on Close.
- Full cohort and symbol-only comparison headings.
- A non-asset Coverage definition list remaining at 14px and receiving no asset quote class.
- Retained asset JSON, no page overflow and no storage writes.

Eight native captures were inspected: four quote states, two fallback inspectors and two Overview sections. All narrow layouts retain readable text/actions. The captures use explicit historical/synthetic fixtures.

This is a focused 21-case run, not a complete browser-suite rerun. The earlier quote phase's 102-contract/eight-browser evidence retains its exact source scope.

## Source conservation and evidence

Eight source/served/test paths change; 13 inputs remain byte-exact, including the builder, projection, contract tests, retained view and shared assets. Reversing the three product transformations and browser-test changes recovers the exact parent.

The retained candidate pages keep their ordinary Ethereum/Solana visible content. Their only byte differences are two asset-version references, two decorative coin accessibility attributes and one extra leading newline from the added Jinja macro. Served JS/CSS match their template sources. Runtime assets: `bc279c50ec6b`.

- [Exact native publication receipt](asset-reading/PUBLICATION_RECEIPT.json)
- [Parent baseline](asset-reading/BASELINE.txt) and [candidate JUnit](asset-reading/CANDIDATE_RESULTS.xml)
- [Source/test transformations](asset-reading/TRANSFORMS.json)
- [Publication readback script](asset-reading/PUBLICATION_READBACK.py)
- [Eight inspected native captures](asset-reading/captures)

## Next and boundaries

Continue correcting stale builder/reference claims against current source, while preserving intentionally proposed receipt/model states. Validate any later feature against the existing producer and shared-shell owners.

Draft/unarmed/unmerged. H5/model, alerts, hosted/independent acceptance, public-route cutover, admission/release and all existing denied/unknown-effect boundaries remain. Local historical/synthetic proof is not current freshness or production acceptance.
