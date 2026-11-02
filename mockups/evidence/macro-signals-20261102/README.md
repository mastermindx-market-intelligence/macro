# Macro Signals evidence breakdown

The existing dashboard card and Factors popover open the same dialog. Its persona is a US equity-market reader checking what drove a published score and which inputs support it. The registered full-page test and component screenshots use the October 30 market-state snapshot from [macro at 9af0a33e](https://github.com/mastermindx-market-intelligence/macro/blob/9af0a33eb38b08d902c3e593cb0e276d3f0d6a18/data/market_state/latest.json).

[Desktop, light, English](701a6ce04626e99a.png) · [Mobile, dark, Chinese](1dd43a1708789f74.png) · [Capture matrix](manifest.json)

## Reading and layout

The first view pairs the published verdict with the producer’s conditional explanation. A signed contribution is measured in raw blend points relative to 50. Available factor weights are normalized before attribution. The labels for largest lift and drag include ties at the displayed precision. A binding cap has a separate raw-to-published readout. Missing observations, dated inputs, degraded components and intraday versus settled observations are exposed at their respective levels.

Light mode uses an opaque research surface and a recessed verdict panel. Dark mode uses raised surfaces and restrained semantic ink. At 390 px the verdict and the conditional explanation stack, with scoring and signed contributions still visible beside every factor. Disclosure controls and the source-date summary work by touch or keyboard.

## Reproduce

Run from the candidate checkout with the repository’s Chromium dependencies and the site assets materialized.

```sh
python3 tests/macro_evidence_dialog_browser.py --source-ref 9af0a33eb38b08d902c3e593cb0e276d3f0d6a18 --output /tmp/macro-evidence-preview
python3 -m scripts.capture_page_evidence --site-dir /tmp/macro-evidence-preview --routes evidence.html \
  --viewports desktop,mobile --locales en,zh --themes dark,light \
  --force-state 'factor_hover:hover(.ev-factor summary)' --force-state 'factor_focus:focus(.ev-factor summary)' \
  --delay-ms 0 --settle-ms 180 --output-dir mockups/evidence/macro-signals-20261102 \
  --manifest mockups/evidence/macro-signals-20261102/manifest.json --smells mockups/evidence/macro-signals-20261102/smells.json
```

The full-page test exercises the dashboard entry, registration boundary using local fixtures, keyboard opening and dismissal, focus return and eight responsive layout combinations. The canonical capture visits an open component specimen extracted from that render. Each of eight theme, language and viewport combinations has a resting, hovered and focused frame. Production deployment and authenticated production proof require separate verification.
