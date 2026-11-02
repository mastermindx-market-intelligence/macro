# Signals evidence breakdown

The Macro dashboard card and Factors → Full breakdown share this overlay. The reader can see the dated market verdict, identify the strongest opposing contributors, then inspect a factor or reconstruct the score in place.

[Desktop overview](5b44d3086798f43a.png) · [Mobile overview](ba0763cb072c9cf5.png) · [Mobile score trace](score-trace-mobile-zh.png) · [Factor inspector](raw-score-inspector.png) · [Capture matrix](manifest.json)

## Design source and Paper status

The design draws on the existing [Market Dashboard Popups file](https://app.paper.design/file/01M38EVF74SJWG1GANN5VP380Z/p-1-0), its evidence artboard `8PS-0`, mobile overview `8R6-0` and file-level tokens. Those are reference artboards for the popup family. The Signals design sources in this change are [desktop overview markup](paper-overview.html) and [mobile score-trace markup](paper-mobile-trace.html). They are static, inline-styled HTML prepared for Paper’s `write_html` action and can also be opened in a browser.

The selected Mastermind Paper connector allowed exact-file reads, an artboard screenshot and JSX inspection. Its write guard reported `accepted_for_write: false`. The server reported catalog `16e6b93f…` and the installed guard expected `1b9afff4…`. A Paper administrator must qualify and deploy the inspected catalog on this connector before these new Signals artboards can be saved there. [Existing compatibility record](https://github.com/mastermindx-market-intelligence/Mastermind/pull/1904)

## Product contract

- The headline identifies the largest signed factor impacts or the binding cap. Tied contributions at the displayed precision retain each factor name. In light mode the score instrument is a white inset with a hairline and shadow. Dark mode uses a raised surface. Both retain localized directional colors and printed signs.
- **Impact** compares weighted points against 50 on a common, symmetric scale. **Factor score** keeps the same row order and switches to each factor’s 0–100 reading. Expanding a factor reveals source interpretation, measurements, configured weight and the effective share when unavailable factors change the denominator.
- **Trace the score** exposes the neutral starting point, total drag, total lift, reconstructed blend, and the producer’s rounding and cap where present. In the October 30 snapshot the arithmetic is 50 − 9.72 + 6.48 = 46.76, rounded to 47. The input is [the pinned market-state snapshot](https://github.com/mastermindx-market-intelligence/macro/blob/9af0a33eb38b08d902c3e593cb0e276d3f0d6a18/data/market_state/latest.json). Missing weights withhold the contribution trace. A disagreement with the published blend is visible.
- **What would change it?**, the multi-timeframe RSI tape and source vintages open on demand. The registration boundary and the two existing popup entry points retain ownership of access, focus and return behavior.

## Evidence and reproduction

The full-page test exercises a local anonymous and registered visitor, both entry paths, keyboard dismissal, focus restoration, trace arithmetic, radio selection with keyboard and pointer, factor disclosure, index tape, vintages, responsive fit, and EN/ZH in light and dark modes. The input snapshot is fixed. No new runtime requests or external data services are needed for the popup.

```sh
python3 tests/macro_evidence_dialog_browser.py --source-ref 9af0a33eb38b08d902c3e593cb0e276d3f0d6a18 --output /tmp/mmx-macro-signals-r2
python3 -m scripts.capture_page_evidence --site-dir /tmp/mmx-macro-signals-r2 --routes evidence.html \
  --viewports desktop,mobile --locales en,zh --themes dark,light \
  --force-state 'factor_hover:hover(.ev-factor summary)' --force-state 'factor_focus:focus(.ev-factor summary)' \
  --delay-ms 0 --settle-ms 200 --output-dir mockups/evidence/macro-signals-20261102 \
  --manifest mockups/evidence/macro-signals-20261102/manifest.json --smells mockups/evidence/macro-signals-20261102/smells.json
```

The capture visits an open specimen extracted from the full Macro template render. The full-page interaction test separately opens the real card and popover against a local registration fixture. Production publication still requires the PR release process, a covering Macro render and served-page verification.
