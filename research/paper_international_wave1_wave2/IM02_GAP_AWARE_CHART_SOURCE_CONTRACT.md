# International R10 IM02 — Gap-aware chart source contract

**Status:** DATA PROJECTOR IMPLEMENTED / NOT WIRED / NOT SHIPPED. This is an in-scope separable implementation slice under the existing `WS:PAPER-INTERNATIONAL-WAVES` and Paper R10 artboard `6G-0`. The original mockup's returns, dates, SPX reference and leader movement are illustrative, not source data.

## User capability intended

In **Compare & Rotation**, a researcher selects 2–4 markets and sees the same-start price-return paths rebased to **100** in the selected currency (USD-unhedged or local), with honest observed gaps rather than drawn-through interpolations. Cohorts are based on exact agreed start/end and calendar policy, so unrelated periods never share a performance axis. Local/FX/USD endpoint decomposition remains with the existing Compare owner.

## The one current owner chain

- The existing `engine.intl_performance_charts.build_chart_records` supplies **raw interior numerical levels** and per-point missing reasons. It explicitly does **not** qualify those points for publication.
- The accepted `engine.intl_inputs.qualify_return_records` and `engine.intl_workspace_overview` grant only selected endpoint quality. The matching Overview is a required input to the chart projector; an unqualified or redacted market never yields a line.
- The existing EOD source publisher from Macro PR #8715 binds exact index and FX stored files, one content digest, and per-series evidence, including the conservative two-day snapshot. The projector consumes those witness receipts; it **does not** issue decisions, call sources or adjust clock/rights policy.
- New pure `lib/intl_chart_publication.build_source_bound_charts` validates the source digest, saved-series witness identity, configured index/FX pairing, selected horizon/basis, chronological geometry, exact return-window equality, and endpoint parity (at most 1e-7 percentage points). It rebases observed positive finite levels to 100 and preserves any missing observation as a `null` with a fixed reason. No filling and no opaque source fields are copied.
- A USD line needs index **and FX** saved-source witnesses; a local line needs its index witness. One broken source withholds only its dependent line. A cohort is exposed for overlay only when at least two witnessed qualified markets share the same window.
- S&P 500 stays `benchmark_source_not_qualified` until its source, rights and matched calendar/window are independently admitted. No previous-rank/rotation trajectory is fabricated from current-only rankings.

The projector is **not itself a chart publication policy**: a trusted existing publisher must pass the approved Overview and source-evidence package. Its output says `source_bound_observed` or `source_bound_partial`, not a blanket qualified interior series.

## Verified source-level scope (October 11, 2026)

- 16 hermetic cases passed using existing owner-generated synthetic qualifications; nonmutation, denied metadata, missing FX, duplicated source witnesses, fake calendar, wrong source, malformed/out-of-order observations and endpoint mismatch fail-closed.
- An independent **read-only** cross-worktree check against 14 real committed index/FX series and the accepted EOD candidate (before merge) yielded **54 admitted market/horizon/currency lines over 10 panels**. Every actual raw series contains internal observed gaps, and no gap is interpolated. One-month USD cohorts: Japan/South Korea/UK (09-11→10-07) and Taiwan/euro area (09-09→10-07).
- The existing chart adapter's numerical end-to-end identity separately matched all 54 qualified endpoint returns with **zero** percentage-point difference on that source snapshot.
- The source helper has **not** been mounted into `intl.html`, rendered, independently reviewed for release, merged, or served in a signed-in browser. Those are explicit future acceptance requirements.

## Remaining integration in the incumbent product

The publisher owner must attach a compact, qualified chart payload to the existing Compare catalogue **without** a duplicate source store, public sidechannel or score plane. Preserve the current overview, accessible source/detail table, selectable same-window cohorts, and no-JavaScript fallback. Implement an SVG/Canvas plotting controller with discrete segments at every `null` and responsive dark/light, EN/ZH, 1440/390/320 behavior, plus exact-source tests and authenticated served acceptance. The renderer and page-owned `intl_workspace/compare.html.j2` remain unchanged in this phase.

Macro PR #8754 currently owns the overlapping **Paper presentation and asset gate** changes; its source/live writer and review hold must not be displaced. PR #8715 owns the EOD admission path, still under its own release gate. Only combine these once the original overlapping carriers are reconciled.
