# Owner visual spot review — current composed International build

Root inspected two actual PNGs through Studio Direct after the successful runtime run. Build source: b380435c7d0f6d9bfc117dc7f6424b3309478fb7. HTML SHA256: bf8066967a885bd226ccc1abe622e626349e431d11c38cda6e19331751d9edae.

- `standalone_toolbar_images/anchor-imc-country-JP-desktop-en-light.png`: the Japan section begins below the toolbar. The country thesis, growth path, published-history/projection distinction, source dates and conditions panel are visible and legible. No overlapping header or horizontal clipping is visible.
- `standalone_toolbar_images/anchor-imc-country-JP-narrow-zh-dark.png`: the 320px Chinese dark view places the Japan header below the wrapped toolbar, retains the assistant button in its slot, and wraps the narrative into the available width. Forecast values, historical/projection chart and source labels remain visible without horizontal clipping.

The screenshot identities are bound in `toolbar_main6a420261022_landings.json`; the ordinary build and browser receipts bind source and HTML hashes. Automated results are separately recorded as 22 passing landing checks and 28 passing country/history checks, with no failures.

This is an inspection of these two images only. It is not a full visual-matrix, measured contrast, authenticated-session, actual-parent focus, current-source-acquisition or deployed-product acceptance claim.
