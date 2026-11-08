# Explicit basket and theme-context inputs

Status: source implementation qualified locally; runtime acquisition, publication, deployment and beta acceptance remain open.

Mission: [pinned migration issue #10779](https://github.com/mastermindx-market-intelligence/macro/issues/10779). Original source carrier: [PR #10780](https://github.com/mastermindx-market-intelligence/macro/pull/10780). Protected law pin: `49c2e1d93e5e080b1671c98087a845e5beb09dd5`.

## Canonical computation boundaries

`engine.baskets.BasketInputs` supplies membership, the broad close panel, SPY, supplemental closes, company names/sectors and reference-proxy frames. `compute_baskets_from_inputs(inputs)` performs the existing basket calculation without reading files, configuration, stores or clocks, and without writes or diagnostic output. Missing proxy entries mean unavailable; there is no implicit store fallback. The broad panel and SPY still determine the source calendar. Newer supplemental data cannot advance that calendar. Existing whole-column thematic price resolution, coverage checks, formulae, ordering and rounding remain canonical.

The legacy `compute_baskets()` wrapper retains its missing-membership, missing-close, missing-SPY and shared-calendar short circuits. It captures each declared reference proxy once after those checks. The core repeats the pure alignment on the original inputs so the full observation receipt is preserved. This capture may read an unused declared proxy earlier than the former per-basket loop; it does not invoke a provider. Only the legacy wrapper emits the existing coverage warnings.

`engine.theme_context.ThemeContextInputs` supplies allocation, theme intelligence, region, history and rotation events. `compute_theme_context_from_inputs(inputs)` computes context without reading or advancing history, seeding archives, checking runtime lanes, consulting the clock, or writing artifacts. The allocation's source date remains authoritative. Missing rotation events and an empty supplied events object preserve their distinct legacy meanings.

The legacy theme-context wrapper still owns lane-gated archive seeding and same-day history replacement or append. Seeded history is adopted only after its existing write succeeds. The extracted core supplies the history row; it does not publish that row. Supplied nested inputs are copied where the calculations could otherwise retain aliases; returned data does not mutate the caller's inputs.

## Qualification

The parent recovered this bounded implementation after the original paid worker refused before source work because of its thermal admission guard. No worker was retried or moved to another carrier.

- Original basket/context suites: 73 passed.
- New plus original targeted suites: 96 passed, with six existing pytest temporary-directory cleanup warnings.
- Reproducible full-output comparison: 16 cases, 12 distinct output digests; original source, legacy adapter and explicit-input core agree for every case.
- Baseline: `38f2441def30f02cf2accf9ddfbaee334d86e1b5`.
- Harness: `research/market_os/verify_sector_basket_context_parity.py` loads the actual baseline functions from git and compares complete payloads before accepting the golden fixture.
- Golden outputs: `tests/fixtures/sector_basket_context_parity.json`.
- Focused tests: `tests/test_sector_basket_context_inputs.py`, including read/write/config/store traps, non-mutation, source-calendar preservation, early short circuits and successful/failed history seeding.

The fixture corpus covers normal and missing population coverage, membership changes, newer extras, missing proxies/SPY/membership, same-day/empty histories, unavailable/empty/malformed rotation events, rotating leaders and missing ranks. It is numerical and structural parity evidence, not proof that a provider supplied a current or licensed source cohort.

## Remaining acceptance work

Register these tests through the existing curated CI owner; qualify complete historical panels and upstream allocation inputs; bind all inputs to one verified runtime generation; integrate the existing publisher and API; deploy only through the protected release owner; prove the authenticated beta journey and failure behavior. These pure seams alone do not establish fresh inputs, source-owner transfer, atomic publication or completion of the full Sector product.
