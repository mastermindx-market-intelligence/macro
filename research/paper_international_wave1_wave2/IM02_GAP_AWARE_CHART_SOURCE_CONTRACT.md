# International R10 IM02 — Gap-aware chart source contract

**Status:** DATA + SVG GEOMETRY + ACCESSIBLE JINJA CHART COMPONENT IMPLEMENTED / NOT WIRED / NOT SHIPPED. This is an in-scope separable implementation slice under the existing `WS:PAPER-INTERNATIONAL-WAVES` and Paper R10 artboard `6G-0`. The original mockup's returns, dates, SPX reference and leader movement are illustrative, not source data.

## User capability intended

In **Compare & Rotation**, a researcher selects 2–4 markets and sees the same-start price-return paths rebased to **100** in the selected currency (USD-unhedged or local), with honest observed gaps rather than drawn-through interpolations. Cohorts are based on exact agreed start/end and calendar policy, so unrelated periods never share a performance axis. Local/FX/USD endpoint decomposition remains with the existing Compare owner.

## The one current owner chain

- The existing `engine.intl_performance_charts.build_chart_records` supplies **raw interior numerical levels** and per-point missing reasons. It explicitly does **not** qualify those points for publication.
- The accepted `engine.intl_inputs.qualify_return_records` and `engine.intl_workspace_overview` grant only selected endpoint quality. The matching Overview is a required input to the chart projector; an unqualified or redacted market never yields a line.
- The existing EOD source publisher from Macro PR #8715 binds exact index and FX stored files, one content digest, and per-series evidence, including the conservative two-day snapshot. The projector consumes those witness receipts; it **does not** issue decisions, call sources or adjust clock/rights policy.
- New pure `lib/intl_chart_publication.build_source_bound_charts` validates the source digest, saved-series witness identity, configured index/FX pairing, selected horizon/basis, chronological geometry, exact return-window equality, and endpoint parity (at most 1e-7 percentage points). It rebases observed positive finite levels to 100 and preserves any missing observation as a `null` with a fixed reason. No filling and no opaque source fields are copied.
- Pure `lib.intl_chart_geometry.build_chart_geometry` produces responsive, fixed-scale SVG path commands from *only* admitted compatible cohorts. Its y-axis includes the rebased 100 baseline, all group lines share one x/y scale, and every null observation explicitly splits a path; it never fabricates a benchmark or joins across missing dates. A separate optional bilingual Jinja SVG component exists, but no incumbent shell/builder/controller/CSS/JS file is modified by this phase.
- New opt-in `templates/intl_workspace/chart_cohorts.html.j2` renders trusted compatible cohorts as theme-variable colored SVG paths and isolated-point markers, with unique titles/descriptions, an exact 100 baseline, short actual date labels, a source-gap notice, color-swatches and an accessible bilingual data table. The native `details` element supports keyboard interaction and no-JavaScript reading. It is **not imported** by the current Compare shell, and cannot bypass the producer or displace PR #8754.
- A USD line needs index **and FX** saved-source witnesses; a local line needs its index witness. One broken source withholds only its dependent line. A cohort is exposed for overlay only when at least two witnessed qualified markets share the same window.
- S&P 500 stays `benchmark_source_not_qualified` until its source, rights and matched calendar/window are independently admitted. No previous-rank/rotation trajectory is fabricated from current-only rankings.

The projector is **not itself a chart publication policy**: a trusted existing publisher must pass the approved Overview and source-evidence package. Its output says `source_bound_observed` or `source_bound_partial`, not a blanket qualified interior series.

## Verified source-level scope (October 11, 2026)

- 16 source-admission cases plus 9 gap-geometry cases plus 5 accessible Jinja template cases passed using existing owner-generated synthetic qualifications; nonmutation, denied metadata, missing FX, duplicated source witnesses, fake calendar, wrong source, malformed/out-of-order observations and endpoint mismatch fail-closed.
- An independent **read-only** cross-worktree check against 14 real committed index/FX series and the accepted EOD candidate (before merge) yielded **54 admitted market/horizon/currency lines over 10 panels**. Every actual raw series contains internal observed gaps, and no gap is interpolated. One-month USD cohorts: Japan/South Korea/UK (09-11→10-07) and Taiwan/euro area (09-09→10-07).
- The existing chart adapter's numerical end-to-end identity separately matched all 54 qualified endpoint returns with **zero** percentage-point difference on that source snapshot.
- The chart helpers and optional Jinja macro have **not** been mounted into `intl.html`, independently reviewed for final release, merged, or served in a signed-in browser. Their **standalone component preview** has been rendered in real Chrome for 12 desktop/mobile (1440/390/320) × dark/light × English/Chinese combinations with no horizontal overflow, missing routed assets or JavaScript exceptions. Native keyboard disclosure passes. These preview inputs are synthetic source qualification fixtures, **not authenticated production**, and capture evidence is saved in `/Volumes/Mastermind/evidence/paper-waves-20261006-01a1101f/IM02_CHART_COMPONENT_BROWSER_R2_20261012/BROWSER_PROOF.json`.

## Remaining integration in the incumbent product

The publisher owner must attach a compact, qualified chart payload to the existing Compare catalogue **without** a duplicate source store, public sidechannel or score plane. Preserve the current overview, accessible source/detail table, selectable same-window cohorts, and no-JavaScript fallback. Mount the prepared gap-aware SVG macro through the existing Compare producer/controller, enable exact 2–4 selected-market pin behavior and route preservation, then verify the complete page in dark/light, EN/ZH and 1440/390/320 states with authenticated served acceptance. The renderer and page-owned `intl_workspace/compare.html.j2` remain unchanged in this phase.

Macro PR #8754 currently owns the overlapping **Paper presentation and asset gate** changes; its source/live writer and review hold must not be displaced. PR #8715 owns the EOD admission path, still under its own release gate. Only combine these once the original overlapping carriers are reconciled.


## CI closure readback

The full repository-wide `test_curated_exclusive_scopes_cover_their_own_import_closure`
was bounded at 300 seconds on the heavily loaded local M2 and returned a timeout
without a result. A changed tactic ran the **same accepted**
`suite_dependency_closure` resolver selectively for both new suite files:
240 and 242 transitive file edges respectively, with **zero** paths missing
from the existing International foundation job's declared `paths:`. Its 23
reported inherited dynamic-analysis ambiguities are not misreported as fully
proven dependencies; the normal hosted CI retains the final scope authority.
The source, geometry and opt-in Jinja component tests are registered in the incumbent Foundation job; `jinja2` is added as an explicit test dependency. A selective exact-source closure check of the Jinja test resolved 242 files, **zero uncovered paths**, with the same inherited ambiguity disclosures. No new CI owner created.
