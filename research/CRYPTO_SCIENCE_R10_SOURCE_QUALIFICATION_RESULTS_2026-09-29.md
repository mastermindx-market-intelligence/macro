# Crypto science R10 — source meaning and timing before another forecast

Date: 2026-09-29. Existing WS:CRYPTO-INTELLIGENCE / operation crypto-vector-r2-20260926-sol-001 / Macro draft PR8050. Baseline d636e9c405c0283209eb75b09d477d32003ff827. Protocol 38b8f6d2f2580730993e81de95ef1b7fa34e2a14 preceded the numerical audit. Tested initial implementation 342cb1454d0aee29028f53df9019fbc7a568c5b3 preceded the first run; technical amendment 90adead20f7797b10446c54d0ca0bf0779bacd19 is disclosed below. Research/tests/continuity only; no production source, collector, configuration, gate, live allocation, alert, trade, account or subscription changed.

## 1. Main finding

Existing derivatives observations are not yet a defensible historical information increment for the R9 advance-warning model. This is not because the data are imaginary or every observation is corrupt. The actual sources contain useful measurements, but the current capture loses distinctions needed to interpret them: aggregate derivatives versus spot, provider units versus dollars, observation timestamps versus availability, predicted versus settled funding, and sparse observation counts versus elapsed time.

R10 resolves those distinctions with source inspection, primary provider documentation, an actual stored-history census, offline reproductions and tested research-only qualification functions. It does not fit another model on unqualified inputs and label its backtest improvement as alpha. The next dependency is an existing-collector evidence-preservation repair, not a speculative history splice or another price threshold.

Two practical results matter immediately. A historical 24-row flow window can span33hours, and the secondary OKX funding collector stores predicted funding values while discarding actual-settlement values and intraday timestamps. The former is a narrowly located historical gap, not proof that the latest flow display is wrong. The latter must not be misattributed to the currently selected BGeometrics funding input that powers the incumbent signal stack.

## 2. What the existing flow actually measures

The collector requests `ccy=BTC`, `instType=CONTRACTS`, `period=1H` from OKX's aggregate taker-volume endpoint. The documented response order is timestamp, sell volume, buy volume. The local parser follows that order correctly. This is exchange-reported aggressor-side activity in the requested derivatives scope, not candle-signed volume, Coinbase spot flow, all-exchange Bitcoin flow, or observed net position creation.

The inspected endpoint documentation gives the request scope, supported aggregation periods and field order. It does not define an absolute volume unit, exact timestamp start/end convention, per-instrument membership, finality flag or publication lag. Those semantics cannot be imported from a different endpoint merely because field names look similar. Exact document identities and qualified versus unknown fields are recorded in `provider_contract_observations.json` [1].

This limits claims selectively. If both sides use the same unit within an observation, `buy/(buy+sell)` is mathematically invariant to a common scale; unknown dollar denomination does not make every ratio meaningless. However, summing values and displaying millions/billions does not establish USD capital entering or leaving a market. Cross-time changes in instrument mix or contract measurement can also affect a ratio's interpretation. Negative net aggressor flow does not by itself establish distribution by a particular investor class, liquidation pressure or passive absorption.

The current CVD source retains a display-only warning, which should remain. Its stronger historical wording about a genuinely leading divergence must not be elevated into a fresh scientific acceptance claim. R10 did not reproduce an order-flow forecasting edge.

## 3. The actual hourly history is mostly continuous, but count-based windows are not time windows

The inspected flow snapshot contains **2,957 rows**, from 2026-05-26 00:00 through 2026-09-26 13:00. Both aggressor columns are finite and positive in every stored row. There are no duplicate or off-hour labels. Across its 2,966-hour calendar span, nine hours are absent in one gap. The longest continuous valid run is2,956hours.

| Diagnostic | 24-row calculation | 72-row calculation |
| --- | ---: | ---: |
| Count-based full-length windows |2,934|2,886|
| Windows crossing the observed missing-hour gap |1|1|
| Longest elapsed support represented by one such window |33hours|81hours|
| Complete strict elapsed-time windows |2,933|2,885|
| Latest window complete in this stored snapshot |Yes|Yes|

The incumbent CVD helper only restarts after a gap larger than720hours. It uses `tail(24)` and `tail(72)` for the shorter readings. That guard protects against a very long outage but does not make the intervening observation count an elapsed-hour measurement.

An independent synthetic example makes the defect explicit:24rows across25hours, with one interior hour missing, are accepted by the old display calculation without a gap flag. The new research helper marks the exact24-hour request incomplete. Missing observations are not zero selling, neutral flow or safe conditions.

The affected real-data count is small here: one full-length row window for each lookback around the early gap. The final24/72hour windows are complete. This audit does not claim widespread current corruption or change any displayed value. It establishes a failure mode that would recur under future shorter outages and must be handled before the feature receives predictive authority.

The display's freshness test also compares the last OKX label with the last Coinbase label. In the inspected historical snapshot they match, so the code reports not stale. That is relative synchrony, not proof of freshness against today's wall clock. Likewise, `accruing=false` means the row-count warm-up threshold was met; it does not prove source semantics, historical first availability or independent forecasting validation.

## 4. Mechanical overlap is not historical availability proof

R10 joins only timestamps and eligibility fields from the saved R9 data; it does not inspect their outcomes or price forecasts. The original15,686six-hour watch clocks and8,879qualified primary-lag forecasts are preserved.

For both possible bucket-label conventions, start and end, and additional assumed delays of zero or one hour:

| Required flow window | Mechanically complete R9 clocks | Also R9 forecast-qualified |
| --- | ---: | ---: |
|24elapsed hours|489|364|
|72elapsed hours|481|364|

Equal counts across conventions do not settle which convention is correct. The six-hour sampling grid and long continuous segment can conceal one-hour label differences. The two conventions and both delays are explicit timing sensitivities, not a choice optimized against market outcomes.

None of these364overlapping observations carries all the recorded contract, finality, revision and first-availability evidence required for a point-in-time forecasting claim. Thus the strictly qualified count is zero under the declared test. This does not claim no human could ever have obtained the source at the time; it says the inspected files do not prove when the values used in this replay became available.

There is a second, independent limit: even treating every mechanically overlapping row as qualified would leave fewer than R9's frozen1,000training observations, before chronological splits and the positive/negative event minimums. We did not inspect target counts, lower those floors or splice short derivatives history into the longer spot-price sample. The364clocks overlap in time and are not364independent crises.

This does not block all smaller descriptive studies or future data accumulation. It blocks representing a nominal unchanged-R9 incremental model fit as adequately supported today. Any differently scoped exploratory question requires its own transparent specification, not an after-the-fact relaxation to manufacture a result.

## 5. Funding: expected cost, settled cost and date labels must remain separate

OKX's funding-history documentation distinguishes `fundingRate` from `realizedRate` and identifies `fundingTime` as the settlement timestamp. It also provides mechanism/formula fields. Its discussion of possible interval changes is a reason to retain the actual interval rather than universally assuming one schedule [2].

The existing local secondary OKX collector selects `fundingRate`, drops the other fields, groups by the normalized settlement date, and stores one daily mean as `funding_rate_okx`. The actual stored file has199daily observations from2026-03-12 through2026-09-26, including41negative values. Its one-column daily representation cannot reconstruct individual settlements or prove a day is complete.

The offline reproduction used the ORIGINAL collector with fake HTTP responses, never a live provider request:

| Synthetic three-settlement example | Result |
| --- | ---: |
| Mean predicted funding values |0.00020|
| Mean actual settled funding values |0.00021|
| Latest settlement timestamp represented |16:00UTC|
| Stored daily index |00:00UTC|

A daily aggregate labeled midnight is not automatically wrong as a daily chart convention. It is wrong to treat that label alone as evidence that the full value was known at midnight. A run before the last settlement can also produce a partial-day mean that changes on a subsequent refresh. R10 demonstrates the information discarded by the collector; it does not estimate historical trading impact or replace the existing field silently.

The active incumbent input in this branch selects a named BGeometrics funding field, not this OKX daily field. Therefore the OKX finding is not evidence that every current risk calculation uses the wrong funding series. A future settled-cost computation, expected-carry feature and cross-provider check need separate names and provenance.

### BGeometrics has a different unresolved contract

The actual funding store contains1,168dates, but its usable fields differ:

- Legacy `funding_rate`:1,089finite values,2023-07-09 through2026-07-01.
- Current `funding_rate_fundingRate`:80finite values,2026-07-01 through2026-09-18.
- `funding_rate_markPrice`:80values on the newer dates.

Only one date overlaps between the two rate fields, and it agrees numerically. That is not sufficient proof of equal venue composition, denomination, settlement interval or revision semantics. The already-corrected exact-field selection remains unchanged; no legacy/current splice or substitution of mark price occurred.

The provider's current OpenAPI describes a generic list response and a more explicit latest response that includes a timestamp and delay-related fields. A generic update-time statement and subscription badge do not provide a historical, metric-specific first-publication record or prove the current stored data were delayed. No entitlement was activated or inferred [3].

An offline fake response confirms the local generic parser discards `unixTs`, truncates the supplied date-time to a date, retains the delay flag numerically when supplied, and converts nonnumeric explanatory text to missing. The actual audited historical file does not contain those delay/message fields; a synthetic flag is not evidence that a particular historical observation was delayed.

## 6. What is now executable, and what is not

The new **research-only** helper and tests provide a checkable contract:

- Exact elapsed-hour membership; neither missing bars nor invalid negative/nonfinite volumes become measured zero.
- Known zero activity versus undefined directional ratio; a balanced positive-volume window remains a meaningful neutral ratio.
- Separately represented bucket completion, assumed reporting delay and first-received/available time. A purported final receipt before completion, or an observation received after the decision, is rejected.
- Source scope, unit, timestamp role, finality and vintage requirements kept explicit. Supplying synthetic verification flags exercises conditional logic; it does not self-authorize a source or replace independent review.
- Predicted and settled funding values retained separately, including valid negative and zero values. Missing settled funding never falls back to predicted funding. Unknown interval cannot be converted into a precise annualized cost.

This is not a new runtime registry, live permission gate, collector, event store or forecast owner. The production engines and collectors have not imported it. Its utility is that a proposed producer repair now has exact failure tests instead of relying on prose promising better data.

A received timestamp is not the same as a provider's first-ever publication. It is a conservative bound on what this system demonstrably possessed. For revised/backfilled data, a current fetch time must not be retroactively assigned to the original observation as evidence of earlier knowledge. Current mutable parquet histories cannot recover omitted facts by themselves. Other existing immutable archives or raw snapshots may contain them; R10 did not exhaustively search every possible archive and does not declare historical reconstruction impossible.

## 7. The next implementation boundary

The next bounded source task is evidence preservation through the EXISTING collector/storage owners, after their current writer custody and interfaces are checked:

1. Preserve exact instrument or aggregate request scope, endpoint/parameters, provider timestamps, observation interval where established, response receipt, source status and revision identity. Unknown contract fields remain unknown; do not guess units from magnitudes.
2. For funding, retain predicted and settled fields plus settlement time, mechanism/formula and separately evidenced interval. Derive a named, completeness-qualified daily view without overwriting the meaning of the incumbent field or silently substituting another venue.
3. For flow, replace row-count assumptions in candidate consumers with complete elapsed-time windows, and qualify cross-source alignment before any divergence claim. Show safe descriptive ratios only with their limited scope; withhold dollar-capital or proven-absorption claims when unsupported.
4. Use existing source/version ownership for first-seen revisions, not another parallel database or forecast ledger. Preserve old inputs and nulls, test backward compatibility, and gather prospective evidence through the existing admitted process rather than claiming this Web session is a collector daemon.

The precise external semantic questions are which instruments enter the aggregate, their volume measure, whether the timestamp marks the opening or closing boundary, what finality/revisions mean, and when a completed observation is published. Those questions need source-specific documentation or attributable provider confirmation. R10 made no support-ticket, account or paid-data request.

Once enough comparable, time-qualified observations exist, freeze a coverage-matched incremental study. Keep the descriptive source-validity question distinct from forecasting efficacy. There is no justification for running a more impressive flow backtest now on an invented publication timeline.

## 8. Verification, amendments and disposition

Thirteen tests were added to the existing scientific test owner. The initial12failed for the absent module and then passed. A later synthetic edge test reproduced a defect in the NEW helper: an otherwise fully qualified receipt one second before completion was incorrectly accepted. The original script, tests, result and CSVs were preserved under `r10/initial/`; a documented post-audit correction now rejects that impossible receipt. One amended diagnostic run reproduced identical real-data findings and byte-identical gap/window/clock CSVs. This was a correctness repair, not result-driven feature or financial-outcome tuning.

The independent verifier first exposed its own timestamp-unit mistake: it assumed the raw integer DatetimeIndex representation was nanoseconds. That failure log is retained. The verifier was corrected to use elapsed seconds from timestamp subtraction, without changing any generating result or running another empirical study.

Final results:

- **306tests passed,49warnings** in the combined Crypto/Vector/science suite.
- Python compilation, existing source-scope claim checker and difference checks passed.
- Independent index-membership and scalar arithmetic verified **five source frames,5,914elapsed-window rows and125,488clock-convention masks**, plus field overlaps, funding projection examples and original display arithmetic.
- All **57input identities,18gate files,137prior evidence artifacts** and inherited source/config/research hashes remained unchanged. The earlier scientific test file is an exact byte prefix of the extended file.

This numerical verification is by the SAME session, not an independent researcher. Existing warnings, initial RED results, the synthetic correction and the verifier failure are preserved. The observed documentation bodies are represented by exact hashes and bounded semantic notes, not republished full copyrighted pages. No raw provider price/volume parquet, secret or font is published.

**Disposition:** R10 source-qualification audit complete, no model/policy promotion. We now know where genuine additional information loses instrument, timing or cost meaning in the present capture, and have tests for a safe next repair. The large Crypto/Vector product and high-quality risk-transition science remain incomplete. Independent review, source-specific semantics, adequate prospective history and production acceptance remain separate obligations.

### Primary documentation

[1] OKX exact taker-volume endpoint section, https://www.okx.com/docs-v5/en/#trading-statistics-rest-api-get-taker-volume . Inspected2026-09-29. Full response-body hash and extracted field observations are in provider_contract_observations.json. No market-data request was made.

[2] OKX funding-history section, https://www.okx.com/docs-v5/en/#public-data-rest-api-get-funding-rate-history ; also readable through https://app.okx.com/docs-v5/en/ . Only this specific history endpoint's field meanings are applied; other funding channels may have distinct semantics.

[3] BGeometrics current documentation UI https://api.bitcoin-data.com/scalar.html and OpenAPI https://api.bitcoin-data.com/v3/api-docs . Body identities and observed generic-versus-latest schemas are recorded locally. Current documentation and rights hints do not certify historical release timing or activate access.
