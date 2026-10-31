# Prophet opportunity card presentation

This is the first presentation integration of the Paper opportunity workspace,
file `01M3NT5Y3G5HTJHVR0K5W2MDJM`, successor page `p-A-0`.
It changes the existing US Today and candidate card layout. The shared card
renderer, source selection, assessment values, live quote hooks and setup-detail
owner retain their original behavior. The richer Paper assessment summary,
comparison and saved-setup interactions are separate unfinished integrations.

## Art direction

Light uses white card material, hairline edges and the canonical card shadow.
Dark uses panel depth, with the raised canonical panel for featured cards and a
semantic rail. Both preserve the same information and interaction hierarchy:
assessment/caution and quote, series, ticker and full issuer name, existing
priority/context/maturity, setup details, then dated zone information. Missing
reads retain the shared renderer's neutral and dashed treatment. No new
assessment, source date or action authority is inferred by the stylesheet.

## What was captured

`manifest.json` and `smells.json` were produced by the repository's
`scripts/capture_page_evidence.py`, not manually authored. The screenshots cover
desktop 1440 and mobile 390, EN and ZH, light and dark, and real browser hover,
caution focus and setup-summary focus. The PNGs are retained with their original
digests so the evidence gate can verify them in a clean checkout.

The route is an **illustrative integration fixture**, rendered by the actual
`_prophet_card.html.j2` macro with the new scoped stylesheet and canonical
`theme.css`. It includes a normal card, a long issuer/price, missing quote/chart
and unavailable read, and a caution card. The numbers and series are synthetic
test inputs, not market data, a native receipt, a live recommendation or proof of
authenticated production behavior. The fixture title explicitly labels this.
The manifest's nearest-Git field does not establish renderer provenance.

Captured source SHA-256 values:

- `_prophet_card.html.j2`: `e8d875372e984f8f6b2da7ce5a19e7378b38697ba039c23e051c4d8447fa6e27`
- `theme.css`: `311f121e4d748b917aaa3ce8ca6dae411782a02571fc39f551e3516a4e0a2ab2`
- `_prophet_workspace.css.j2`: `3a510a50016dbcacaad6e92587ea1cba2c47b27c10d86a99ad9f5711b1121ba1`

The capture used `/prophet-cards.html` with `--viewports desktop,mobile`,
`--locales en,zh`, `--themes light,dark`, and:

```
--force-state 'card-hover:hover(.pvcard)'
--force-state 'caution-focus:focus(.pv-cau-btn)'
--force-state 'setup-focus:focus(.pv-setup-inline > summary)'
```

Separate offline browser checks exercised all 12 width/theme/language cases
(1440, 390 and 320 pixels): control hit areas and reachability, no card/page
overflow, caution bounds, exact setup-body node and focus return after Escape,
and preservation of the live-change sibling when the quote text changes. A full
dashboard SSR fixture was also opened through the real Today source button at
1440 and 390 pixels. These are integration proofs, not deployment acceptance.

The baseline browser check exposed an obstructed 35-by-19-pixel caution control.
The repaired control is at least 44 by 44 pixels. A separate 320-pixel overflow
found during implementation was corrected before this capture.
