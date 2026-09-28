# Commodities WTI/EIA Slice A — implementation evidence

Status: **BUILT_NOT_PROVEN**. This is an additive implementation of the frozen WTI physical-evidence slice, not the complete R2 redesign, a deployment, or release acceptance.

## Real path

`collectors/eia.py` cached series → existing `engine/commodity_supply_context.py` → `_oil_supply_read()` → `_wti_physical_evidence_vm()` → oil-only sector-detail projection → `_commodity_oil_physical.html.j2` → generated `site/commodities.html`.

The generated page showed the actual local EIA observation dated **2026-09-18**, separate from daily commodity analysis **2026-09-25**. It displayed **426.4 million barrels**, **−2.5 million barrels over four weeks**, and **+0.46σ crude seasonal anomaly**, with the composite physical balance labeled Tight. The latter combines available inventory categories and is not the crude-only anomaly. At the 2026-09-28 UTC build evaluation this was correctly labeled **STALE_LAST_KNOWN**, not fresh evidence. Publication and receipt instants were explicitly unavailable.

No forecast, price target, trading instruction, portfolio sizing, alert activation, or new evidence store was added. Research-case attachment remains the next slice.

## Tests and falsifiers

New date/value/markup review regressions were run before fixes: **17 failed, 9 passed**. A second future/wrong-source withholding regression run failed **2 tests** before the correction, then passed. Tests cover invalid and future clocks, chronological ordering, wrong source, unknown method, finite values, genuine zero, source-read errors, missing observations, stale analysis, unequal inventory periods, Chinese balance wording, and native disclosure markup.

The focused integration command includes:

```
python3 -m pytest tests/test_commodities_r2_wti_physical.py \
  tests/test_commodity_supply_context.py tests/test_phase_buildout.py \
  tests/test_commodities_w6_truth.py tests/test_commodity_coverage_matrix.py \
  tests/test_bilingual_span_leak.py tests/test_i18n_attribute_guard.py \
  tests/test_f01_fx_commodity_source_rights.py -q --tb=short
```

Latest result: **843 passed, 3 warnings**. The warnings were existing covariance degrees-of-freedom/divide warnings in `test_short_interest_factor_if_cache`, not WTI test failures.

A whole-repository `python3 -m pytest -q --maxfail=1 --tb=short` attempt **did not pass**: collection stopped in `collectors/marketdesk_extractor/extractor/tests/test_allocator.py` with `ModuleNotFoundError: No module named 'marketdesk_extractor'`. This environment/package issue is not waived or represented as a green repository suite.

## Browser evidence

`capture.json` is emitted by the existing `scripts/capture_page_evidence.py` owner using its injected PageDriver seam. `scripts/capture_commodities_wti_slice_a.py` navigates the **real locally served generated page** in anonymous ephemeral Chrome, clicks the existing Oil tab, and checks the new panel. It is not a `set_content` mock or an authenticated production session.

**16/16 cells captured**: desktop 1440/mobile 390 × English/Chinese × dark/light, each at rest and with actual keyboard-visible source-summary focus. Rest cells also opened/closed the source disclosure using Enter and verified the EIA source link. Focus cells traversed Shift+Tab/Tab and asserted `:focus-visible`. No observed page exceptions or local HTTP error responses. Screenshots are content-hashed by the canonical manifest.

External networking was deliberately blocked in this local browser test and recorded by the driver. It does **not** establish live quotes, sign-in, account sync, EIA fetching, or external integration availability. This is generated-page and interaction evidence. The actual captured source state is stale; other degraded states have unit/template coverage, not a complete live-browser matrix.

The first mobile capture failed at 473px document width on a 390px viewport. A diagnostic removed the new WTI panel and retained 473px overflow, locating the cause in the incumbent early-warning row's nowrap/fixed-width layout. A page-local responsive grid fix preserves its values while removing that overflow. Final captures assert document width equals viewport width; no global overflow-hiding rule was added.

## Visual treatment

Dark: existing command-surface layers, neutral hairlines and information/limitation ink. Light: white panel with the existing shadow token, cooler metric wells, no dark blur. Market direction colors are not used to imply that qualified physical evidence predicts a price rise. Long producer caveats and method detail are disclosed, not repeated in the primary reading. The section retains one concise non-directional warning.

Desktop dark/light and mobile English/Chinese-light section captures were visually reviewed. Shared assistant launcher overlap remains inherited global UI, not changed by this slice. Full screen-reader, production negative-state, performance and live release review remain owed.

## Guard results

- Python compilation: passed.
- Actual candidate-diff design-system added-lines check: passed after mapping new styling to shared tokens.
- Canonical visual-evidence guard: passed with real image hashes/state matrix.
- Runtime style-injection guard: passed.
- Template/site plain-copy parity: 105 pairs passed.
- Agent OS validation: 0 errors; existing overdue-review warnings remain.
- Diff whitespace check: passed; unchanged generated-page whitespace was preserved rather than reformatting unrelated sections.

An incidental regenerated `signals_index.parquet` was dataframe-equal to HEAD and was restored; no model-data diff is included.

## Boundaries and continuation

Protected procedure: Mastermind `aebb2ed19e68bda072e38221638925d674b656dc`. Implementation base: Macro `46963311ba19fe8167553774be506bae43d3460b`. Source carrier: `claude/commodities-wti-eia-slice-a-20260927`. Cumulative program record: Macro #8049.

Preserve #7596 Gold-publication and #7601 shared-navigation ownership. Before release: exact-head CI, independent code/visual review, generated-page/source reconciliation on current main, and live verification. Only after this slice's acceptance should Research-case evidence attachment be integrated. No production release or mission completion is claimed.
