# Factor Atlas Session 2 — S2-P1 retained-minute evidence preflight

**Status: research-only metadata census; NOT_ADMITTED; no market-data observation and no admissibility authority.** Source and revision owners remain incumbent. This contract adds no collector, entitlement endpoint, permission layer, currency/basis registry, watermark, market-data store, scheduler or publication path.

## Qualified incumbent path and actual blocking finding

Terminal `ingest/backfill_intraday.py` / `ingest/intraday_capture.py` own each retained per-symbol true-one-minute capture. Macro `engine/entry_radar/replay/terminal_minute_observations.py` owns its actual read-completion and read receipt; `engine/entry_radar/replay/rs_pullback_launch_data.py` owns enrolled revision selection. Canonical listing identity, exchange calendar, corporate actions and volume-treatment laws remain with their existing owners. Terminal [#844](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/844) and Macro [#8623](https://github.com/mastermindx-market-intelligence/macro/pull/8623) remain separate Draft/HOLD deliveries.

The existing retention reader contract `research/live_entry_radar/rs_pullback_launch/SOURCE_RETENTION_READER_CONTRACT_2026-10-07.md` (Macro #8623 head `6cff6ef8aba28dc7ee6f7779a81ef18856d9b3b6`, blob `af637fe1fc24789386aed1c64535f5f9f06e8680`) explicitly states **all currently decoded one-minute rows carry `basis_id=null` and `TERMINAL_BASIS_UNPROVEN`**. Even a v3 `research_unadjusted` request with `request.adjusted=false` and all page declarations `FALSE` is **only evidence of request compliance**. It is not proof of actual split/dividend, volume unit, adjustment vintage, or stable monetary basis. The incumbent corporate-actions owner must bind that evidence to the exact capture/page/response version or supply reconstructable raw-plus-factors evidence before a numeric factor flow can be admitted.

Other hard gates: human/operator-confirmed enterprise entitlement record is already present and does not require general relicensing. Dataset conditions may still matter. Neither first-seen timestamp, signed hash, same bar price, current snapshot nor old 5-minute display history proves a retained, causally available unadjusted 1-minute archive. The incumbent selector's conflicts and the current 900-second finality policy are not overridden.

## Pure metadata gate for the proposed four-name pilot

`prototype/source_preflight.py` exposes `IntakeScope`, `MinuteClaim`, `CellIssue`, `Preflight` and `preflight(scope, claims)`. The hardcoded **proposed trial population** is AAPL, MSFT, NVDA and SPY; these are four security *labels*, not proof of stable listing identities or a pre-existing admitted investor basket. The owning calendar supplies one session and up to three explicit PRE/RTH/AH segments; no calendar is invented, a gap or early close is not padded, no 5m bars are interpolated. For each real minute and security, the scope defines one *expected cell*.

Each claimed cell has:
- Security label, existing canonical listing identity reference, source calendar segment and exact `[start,end)` UTC minute;
- Actual Terminal response-receipt nanoseconds, Macro reader-completion nanoseconds, original capture object and sealed-prefix SHA-256 hashes, and exact reader-receipt digest;
- Owner-selected revision/source identity and its retained selection receipt (a second candidate for the same symbol-minute refuses rather than selecting it);
- Exact original `acquisition_role='research_unadjusted'`, Boolean `request_adjusted=false` and page declaration `response_adjusted='FALSE'`;
- Monetary basis identity, exact action/corporate-action vintage receipt, volume-unit and source-value conventions; the role/declaration alone is not basis evidence;
- Canonical enterprise entitlement reference and **specific dataset-use evaluation** reference; source ref strings are not permission grants;
- `PRESENT`, `EXPLICIT_ZERO_VOLUME`, `MISSING_VOLUME` or `UNKNOWN` value state, never fabricating missing values as zero.

The preflight checks equal-minute clocks, source response only after bar close, actual reader completion after source receipt, both at or before explicit cutoff **after conservatively rounding reader nanoseconds upward to the incumbent microsecond availability precision**, source/revision/read hash shape, unique per-slot selection, and **stable listing identity and monetary basis within each security's window**. It reports `expected_cells`, `represented_cells`, `missing_cells`, `unknown_cells`, `explicit_zero_cells`, per-cell reasons and a deterministic input hash. The `coverage_ratio` represents **claimed metadata slot presence only**; it does *not* certify usable market data or quote signing coverage.

`owner_review_candidate=True` means the submitted metadata is structurally complete **pending the original owners' inspection**. It can never say `ADMITTED`, cannot verify raw source bytes against a presented self-hash, authenticate who actually created a receipt, independently decide a canonical revision, establish business rights or rebuild a missing corporate-action basis. Therefore **even for 100% apparent metadata completeness**, all returned records permanently retain:
- `status='NOT_ADMITTED'`;
- `external_owner_admission_required=True`, `may_execute_market_pilot=False`;
- all five research authority flags FALSE;
- explicitly enumerated `UNCHECKED_CUSTODY`, `INPUT_DIGEST_NOT_AUTHENTICATED`, `EXTERNAL_SOURCE_RIGHTS_UNPROVEN`, `SOURCE_BASIS_OWNER_UNVERIFIED`, `CALENDAR_OWNER_UNVERIFIED`, `LISTING_IDENTITY_OWNER_UNVERIFIED`, `DATASET_CONDITIONS_UNVERIFIED`.

There is no positive-admission argument, flag, backdoor or sample-data loader in this API. A metadata fixture, signed-looking SHA, local file or fabricated author receipt cannot produce source admission. The actual decision stays exclusively with the incumbent owner's qualified input-bundle workflow; this research output is merely a blocker census.

## Pilot intake when owners are ready

1. On the incumbent Terminal/Macro owner, identify explicit existing selected input objects and their **actual** response, prefix, reader and revision receipts for the four labels, with stable listing identity and calendar. Do not mutate retained object bytes merely to make the census pass. Do not resurrect the explicitly denied Massive masterplan, polygon script, flat-file or benchmark operations via another carrier.
2. Bind the pre-existing enterprise entitlement to the exact target dataset and intended research use; separately evaluate any feed-specific contract restrictions. Verify exact monetary basis/volume conventions and corporate-action vintage against the source/canonical action authority, not caller labels or `adjusted=false`.
3. Qualify open, premarket, extended-hour availability, missing slots, incomplete/canceled conditions, late revision/reporting and explicit zero volume. Confirm reader-known time relative to requested evaluation cutoff. Keep a complete **negative**, partial and no-eligible sample.
4. Receive an independent source-owner admission decision through its existing source/input-bundle custody, not via `preflight`. For now S2-P1 remains **NOT_ADMITTED**.
5. Only after actual positive owner admission may S2-P2's offline private replay be engineered/executed using the canonical selector and versioned memberships. S2-P3's experimental bar/quote comparison additionally requires corrected print sale-condition-to-volume/OHLC mapping and enough licensed quote coverage. Do not begin a new provider request or author a market-data pipeline in Factor Atlas.

## Reproducible fixture-only proof

`test_source_preflight.py` covers empty and complete proposed cohorts, 4 × 3 minutes; explicit zero versus absent values; request-versus-response truth, missing source/reader/corporate-action/rights/identity metadata, after-cutoff receipts, contradictory clocks, duplicate selected revisions, invalid SHA shape, calendar/identity mismatch, early-close owner window, order independence, and version drift within a security. Complete claimed metadata still produces **NOT_ADMITTED**. This is a native *software falsifier suite*, not evidence that any of those four securities have usable 1-minute archives or that source/reader receipt bytes have been inspected.


## Bounded local Terminal output census (read-only)

The M2 Studio local `charting-app` checkout was observed at Git head `81221cb15345118d0796fabaa7c47476350dc614`. Its `ingest/backfill_intraday.py` declares the default output root `terminal/public/data` unless `TERMINAL_DATA_DIR` overrides it. In this Studio process, that environment override was not set. The default `terminal/public/data/manifest.json` existed and had SHA-256 `b66f89a606ac5a374d993e2ced21f5332d9312ee069d40ed8ce4f55b73ecb6e3`, 13,038 bytes and declared `as_of: 2026-06-26`. It listed all four proposed security symbols among 34 labels.

**The default `terminal/public/data/intraday` directory was absent** in this checkout, so none of `AAPL/MSFT/NVDA/SPY.{1m,5m,1h}.json` were present at that specific location. The result is recorded without market price/volume values in `evidence/local_terminal_default_path_census.json`, with exact local checkout/source and manifest identity.

**Scope restriction:** This is a single M2 local checkout/default-path observation. It is NOT a scan of production, the full fleet, any `TERMINAL_DATA_DIR` configured in a service process, the M1 host, all mounted offloaded archives, or alternative owner source stores. A manifest ticker is not a minute capture. This negative local result does not disprove permitted data elsewhere, but it does not unlock a licensed Factor Atlas pilot. The original Terminal/Macro capture and basis owners still need exact actual receipts and owner admission. No source refresh, provider request, file modification, denied-path read, fresh-main fetch or cross-carrier source action was performed for this census.
