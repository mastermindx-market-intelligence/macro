# Risk Radar workspace: implementation and visual evidence

This replaces the dense first view of Macro's existing `#dlg-risk` with a compact
risk overview and one integrated evidence inspector. The existing dashboard
registration and modal controller remain in charge.

## Design decisions

- State, reason and current stance lead the overview.
- SPY ≥5% pullback odds have explicit 5/10/21 trading-day controls, a same-horizon
  baseline, a fixed 0–100% desktop rail, and adjacent history qualifications.
- The signal index is secondary and explicitly distinct from probability.
- Four comparable “What matters now” cards open detailed evidence with Back,
  previous/next, focus restoration and same-context scroll return.
- Source dates, partial coverage and live internals stay visible. Secondary
  explanations, provenance and context modifiers are available on demand.
- Calendar's legacy illustrative bar widths are removed; seasonal observations
  and source context are retained.
- English/Chinese, light/dark, 320/390/768/1440px layouts, reduced motion, touch
  targets and keyboard navigation are covered.

## Source and integration boundaries

The working design was read from
[Mastermind · Market Dashboard Popups · Redesign](https://app.paper.design/file/01M38EVF74SJWG1GANN5VP380Z).
The current Paper connector rejected write eligibility for its tool catalog,
so no editable canvas update is claimed.

This is a presentation projection of existing backend readings. It creates no
new risk score, capital policy, drawdown forecast, fetch loop, interval or alert
engine. Native live-hook nodes are moved rather than cloned. Unknown future
source-owned panels remain visible; registered evidence stays secondary.

The captured market data comes from immutable repository source
`d7c2316d1626b980cd17224bb090a4b6f17d6141`, not Paper's illustrative forecast values.
Exact input and presentation SHA-256 values are in [source-inputs.json](source-inputs.json).
These are dated test observations, not a claim of current live market readings.

## Evidence and reproduction

[manifest.json](manifest.json) is the canonical `mastermind.p0_evidence.v2`
capture receipt: 8 rest cells (desktop/mobile × English/Chinese × dark/light)
plus actual driver hover and horizon focus in all 8 combinations, 24 captures
total. [EVIDENCE.yml](EVIDENCE.yml) maps the product files to that manifest.

The anonymous component is rendered locally from the actual template and Macro
CSS and staged in its open presentation state. It neither invokes nor overrides
the registered page opener, uses no account or saved session, and is never
written to `site/`. The separate isolated full-page test exercises the real
opener and close/return behavior using a local registration stub and blocks all
external requests. No authenticated production screenshot is claimed.

```sh
python tests/risk_radar_workspace_browser.py \
  --source-ref d7c2316d1626b980cd17224bb090a4b6f17d6141 \
  --output /tmp/risk-radar-ui

python -m pytest tests/test_risk_radar_workspace.py \
  tests/test_risk_envelope_radar_integration.py \
  tests/test_dashboard_template_render.py -q
```

Observed results: **133 pytest cases passed** and **49 browser checks passed**,
with zero JavaScript exceptions. The projection regression suite is registered
in the existing `dashboard-render-contract` CI code gate. Full browser assertions
are in [ui-checks.json](ui-checks.json). Capture command provenance is in the manifest.

Supplemental settled full-page inspector views:
[mobile dark English](detail-390-dark-en.png) ·
[mobile light Chinese](detail-390-light-zh.png).

Normal PR/CI, a covering render and served-byte verification are separate
release steps; local evidence alone does not establish production delivery.

## CI release repair

CI run `39016123857` passed the Risk Radar contract and rendering gates but failed
only `recurring-briefs`: two assertions assumed a real `zh` block meant every
weekly row had a translation. The tested baseline and then-current main both
contained four explicit null watch translations; the existing producer correctly
retained its pending marker. The tests now assert exact complete translations,
exact real-source pairs and stable pairing across absent/null/blank translations.
No weekly runtime or generated data was changed.

The **78-case recurring-briefs suite passed** on both the carrier artifact and
the immutable main artifact. The old two failures were reproduced against both
CI baseline and main; mutations that discard valid translations or shift later
pairs were caught. [ci-repair.json](ci-repair.json) records the exact source
references, artifact/test hashes and outcomes. The 78 cases are distinct from
the 133 Risk Radar/template cases; repeated runs are not additional unique tests.
