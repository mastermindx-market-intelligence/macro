# Factor Atlas S2 — actual Tiingo L1 minutes into existing source-preflight refusals

**Native slice:** `prototype/tiingo_preflight_bridge.py`, `prototype/test_tiingo_preflight_bridge.py`. **Status:** SOURCE_METADATA_NOT_ADMITTED. This is *not* a new Tiingo API client, archive, Data OS identity/rights selector, OOS study, BVC calculation, publisher or background job.

## Original source and exact bounded use

The incumbent Tiingo Data OS producer/reader was merged in Macro #8698. Its original collector archived authentic `equity-intraday-bars` one-minute OHLCV vendor rows for the four symbols **AAPL, MSFT, NVDA, SPY** for **2026-10-09** (4,063 source rows total; 1,560 nominal regular-session timestamp slots 09:30–16:00 ET). Original source receipt hashes/first-received times are on [Macro #8698's original source carrier](https://github.com/mastermindx-market-intelligence/macro/pull/8698#issuecomment-6115007538); the original source owner also acquired four `security-search` responses and documented US/CA ticker ambiguity under [its existing search carrier](https://github.com/mastermindx-market-intelligence/macro/pull/8698#issuecomment-6115302530). Vendor prices and raw source identities are retained by the incumbent Data OS archive, **not duplicated into this PR**.

The new bridge consumes only **already constructed** original `lib.dataos.tiingo_reader.TiingoView` objects. The caller supplies an `IntakeScope` carrying registered 4-symbol expected labels, explicit owner calendar segments and **an explicit UTC evaluation cutoff**; the bridge does not generate a market calendar. It invokes the existing accepted `tiingo_source_fitness.assess_tiingo_view` for each original source-value context and the same module's cohort SHA alias check, then maps the source metadata into the **existing** `source_preflight.MinuteClaim` and `preflight`. No second expected-grid reducer or BVC source permit is created.

Each selected in-window source row binds the original source-content SHA and exact source-observed UTC time (at nanosecond precision where supplied) to the actual vendor timestamp. The source **reader-completion receipt, selected revision receipt, historical sealed prefix, canonical PIT listing/ETF identity, rights, dataset-use grant, source unit/volume convention, raw/unadjusted price basis and corporate-action vintage** remain **NULL** rather than forged. The existing preflight therefore returns the original exact refusal reasons such as `SOURCE_AFTER_CUTOFF`, `READER_RECEIPT_MISSING`, `REVISION_SELECTION_UNPROVEN`, `SOURCE_BINDING_MISSING`, `LISTING_IDENTITY_UNPROVEN`, `MONETARY_BASIS_UNPROVEN`, `DATASET_RIGHTS_UNPROVEN` and `MINUTE_VALUE_UNAVAILABLE`.

A vendor-reported zero volume is counted **separately** as a vendor observation, but is intentionally mapped as `value_state=UNKNOWN` until interval share-volume and execution eligibility are source-owner qualified. A reported NULL vendor volume maps to `MISSING_VOLUME`; neither becomes a verified zero activity or a signed-money observation. Bars outside the caller's calendar stay out of its expected/represented denominator, with a separate outside-row count. Candidate source hashes across different vendor symbols must be context-unique, and competing same-symbol source partitions require the incumbent revision selector. As source hashes/row contents change, the bridge's research fingerprint reflects the original source-fitness digest, while the metadata-only source-preflight digest retains its own original semantics.

**Strict negative authority:** `actual_market_flow_computed=false`, `source_rights_admitted=false`, `canonical_identity_admitted=false`, `calendar_attested=false`, `reader_receipts_attested=false`, `market_pilot_admitted=false`, `customer_publishable=false`, every source and trading authority FALSE. There is no argument or mode that turns self-described source completeness into an admitted source.

## Direct read-only real-data census (no exported licensed prices)

In this session the original Data OS `read_research_view(source='equity-intraday-bars', purpose='RETROSPECTIVE_EXPLORATORY', acknowledge_hindsight=True)` read **the existing four retained Tiingo L1 research partitions**, without vendor/network requests or archive modifications. We passed their returned objects **in memory** into the new native bridge, with a **nominal** caller-supplied 2026-10-09 RTH segment and a historical October 9 20:00 UTC cutoff. The accepted S2 source-preflight reported:

| Field | Observed |
| --- | ---: |
| Expected four-name RTH security-minute slots | 1,560 |
| Represented source timestamps | 1,560 |
| Missing in the nominal RTH grid | 0 |
| Source-minute cells without qualified measurement | 1,560 |
| Source rows outside nominal RTH (still retained by Tiingo) | 2,503 |
| Original source known AFTER requested decision cutoff | 1,560 |
| Canonical PIT identity/basis/rights/reader selection admitted | **0** |
| BVC pressure or trade executed | **0** |

These numbers are **coverage and source-refusal diagnostics only**, not historical point-in-time trading signals or measured institutional buying. The **source was acquired October 11**, so this cohort cannot be backdated to an October 9 `as_observed` study. The caller's `OWNER_CALENDAR_CANDIDATE_UNQUALIFIED` label is not an original exchange-calendar attestation. The retained Tiingo L1 projector still carries `volume_unit_vendor=unqualified` and `canonical_price_basis_admitted=false`. Legal dataset-use rights, original reader first-seen time, selected correction, matched prints and quote/NBBO comparison remain distinct original owner and S6 scientific gates.

The earlier explicit platform refusal to package a **different BOATS** actual-source observation into an artifact remains DO_NOT_REDO; this research slice did **not** retry that operation or create its denied output. There are no licensed price rows in the synthetic test fixtures or accepted evidence manifest.

## Acceptance and remaining frontier

**Test-first:** the initial missing implementation test failed; a later adversarial same-raw-SHA/two-ticker test failed and was repaired **using the already accepted `aggregate_cohort_fitness`** instead of introducing a new alias plane. **21 new tests pass** covering real-shape input, source receipt known-after decision, missing/zero vendor volume, partial grid, competing contexts, out-of-scope rows, source mutation, vendor spoof, future capture/submicrosecond timestamp, full 1,560 nominal RTH rows and unwavering no-admission. The complete registered Factor Atlas suite covers **17 suites, 557/557 native Python 3.12 tests locally**, and uses the original GitHub Actions read-only workflow.

**Direct next source-grade work:** original Data OS identity/ETF owner binds genuine Tiingo alias + SPY security listing with historical known-at/effective dates and original immutable receipts, and independently accepts consolidated interval share-volume/adjustment semantics, corrections/finality and dataset-use rights. Only after that original owner admission should the existing `intake_bridge` and `window_pressure` be used for actual source-qualified BVC pressure, with separate quote/print scientific review and authorized private Terminal read. The independently platform-blocked S2-P4 read-model patch and S2-P6 forecast-decision repair remain held and are not represented as resolved here.


## Current source-assessment propagation — 2026-10-12 UTC

The existing bridge now preserves every refusal from the original `assess_tiingo_view`, rather than discarding source-specific findings after mapping to generic preflight failures. This includes the consolidated reference-price construction warning and off-calendar source-phase findings. Its research fingerprint now binds original source-assessment status/refusals in addition to the same original source bytes and metadata. The underlying preflight grid and owner admission fields are unchanged.

See [the current source-fit ruling](TIINGO_SOURCE_FIT_CONTRACT.md#source-selection-ruling--2026-10-12-utc): Tiingo documents consolidated OHLC built from reference prices that may include quote midpoints, so selected identity/rights alone cannot convert it into the original S2 traded-price basis. Current documentation does not establish each historical row's lineage. The optional reference-price experiment remains distinct and unadmitted.

Thirteen new synthetic cases: fail-first 9 expected failures/87 passes, targeted 96/96, existing 17-suite command 570/570. Exact code/test/log hashes and synthetic scenarios are retained in `evidence/native_tiingo_reference_basis_tests.json` and `evidence/tiingo_reference_basis_synthetic.json`. No real capture was repeated or market metric computed.
