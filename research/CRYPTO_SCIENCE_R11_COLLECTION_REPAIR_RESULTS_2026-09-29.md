# Crypto science R11 — preserve source evidence without rewriting the model

Date: 2026-09-29. Existing WS:CRYPTO-INTELLIGENCE / operation `crypto-vector-r2-20260926-sol-001` / Macro draft PR #8050. Published R10 baseline: `4577adc349ef68f86f6c6200369e49b86e7c453f`. This is a producer/consumer repair with synthetic integration proof, not another fitted trading strategy or a live collection receipt.

## 1. Outcome

The existing OKX and BGeometrics collector paths now have an additive candidate that preserves public response evidence before numerical normalization discards timing and field distinctions. It reuses the repository's keep-first evidence writer. Existing funding/flow numeric series and request patterns remain unchanged in the controlled compatibility tests.

The existing display-only CVD consumer now requires actual contiguous hourly observations, differentiates old observations from a proven collector outage, and no longer labels unknown provider units as dollar millions/billions. The repair does not make derivatives activity into spot inflow, passive absorption or a qualified predictor. `causally_qualified` remains false.

The final candidate source passed the broad 368-test Crypto/Vector/storage pack and the ordinary collector-to-storage synthetic integration. No production collector ran against a provider; no real data file, forecast gate, live allocation, alert, review, account or subscription changed. This is **BUILT_NOT_PROVEN on the live production path**. Independent review, deployment admission and prospective evidence are still required.

## 2. Recovery preserved the interrupted implementation

The preceding visible interruption had not erased the work. Recovery found two local commits beyond the published R10 head: the implementation plan `ff591f1809...` and source candidate `e489b12bc0bbf7c3be37a04c23bb358d42bf0ecd`, plus one unfinished test and two diagnostic logs. These were inspected and continued, not reset, discarded or recreated. There was no active scientific process or unresolved modifying effect. The old loopback design servers were left untouched.

Current protected Mastermind law is pinned to `0b3bdf78be9b86bc3672f224ddacf80854a4c3fb`, INDEX blob `94d1af402598894372858793a5b1931019c5fa77`, compatible Skillpack 1.0.1/bootstrap 1. The same M2 Studio Direct sparse branch/carrier remains in use. A bounded source comparison from the prior custody pin to observed main `1df73c1ac9289a21e192aeb50088a4f9119aee82` found no intervening changes in the relevant collector/store/CVD files or builder warning path. The earlier current-PR custody census had identified another owner on `tests/test_btc_impulse_falsifier.py`; R11 leaves that scientific test file untouched and extends the existing collector/CVD test owners instead.

The PR's draft and integration status do not establish acceptance. No merge, rebase, force push or writer displacement was used to remove a release gate.

## 3. What the collector retains

A narrow adapter, `collectors/_crypto_observations.py`, receives already-returned public responses from the existing collectors. It makes no provider requests of its own. Capture is active only inside the existing public `fetch()` call; private parser probes remain free of implicit persistence, and a finally clause clears capture scope even on a failed run.

The capture records the registered endpoint and allowlisted request scope, provider fields and values, local UTC receive time, exact response-body digest when available, canonical retained-payload digest and an occurrence identity. It does not retain authentication headers, credentials or arbitrary request parameters. Unexpected nested values inside purported scalar public fields are rejected. Response row count and retained JSON size are bounded.

For OKX funding, predicted `fundingRate` and actual `realizedRate` are retained separately, with instrument, settlement timestamp, method and formula. These meanings are specific to the official funding-history endpoint, whose documentation distinguishes the two fields [1]. The legacy daily `funding_rate_okx` field is not silently converted into settled cost. The active BGeometrics funding input is not replaced by a different venue or a spliced older series.

For flow, capture retains the exact request scope, including BTC/CONTRACTS and the daily/hourly aggregation parameter, and the reported sell-then-buy values. It does not supply missing absolute units, contract membership, timestamp boundary semantics or finality. For BGeometrics funding, the original date-time, Unix timestamp and supplied delay/message fields survive in the evidence record even where the legacy numeric projection truncates or cannot represent them.

A local response receipt proves only that this collector possessed that response at the recorded clock. It is not the provider's first-ever publication, a trustworthy historical revision timestamp, or proof that a received aggregate was final. Old mutable history is not backdated into new receipts.

## 4. Revisions are preserved, not overwritten

The adapter uses the existing `collectors/_first_seen_store.py` keep-first/atomic persistence owner. That shared helper and `lib/store.py` are unchanged. A small per-file nonblocking critical section protects the append/readback sequence; it is not another runtime lease, queue, retry engine or database.

The identity describes a response occurrence rather than only its value. Consequently, all three parts of a sequence A → B → A remain recoverable, while an exact replay of the same occurrence is idempotent.

The synthetic public-fetch test exercised this sequence:

| Response received | Predicted rate | Actual rate in response | Distinct funding captures |
| --- | ---: | ---: | ---: |
| 08:00 | 0.00020 | 0.00021 | 1 |
| 09:00, revised | 0.00020 | 0.00031 | 2 |
| 10:00, reverted | 0.00020 | 0.00021 | 3 |
| Identical repeat of the 10:00 capture | 0.00020 | 0.00021 | 3 |

As-of views at 08:30, 09:30 and 10:30 reproduce the corresponding actual rates. A view before the first receipt returns no known event. These are synthetic fixtures, not funding observations from a real market date.

The view preserves valid negative/zero rates and missing actual rates. A later response omitting the actual rate does not silently restore an earlier value. Conflicting values with the same receipt timestamp remain unresolved rather than being selected by incidental row order; a later unambiguous receipt can supersede that conflict. An actual settlement supposedly received before its settlement time cannot be shown as already settled. Boolean/fractional/negative settlement timestamps are not coerced into valid events.

Neither an unknown settlement interval nor a guessed eight-hour default can produce an annualized settled-cost figure. Interval, publication and finality remain unknown where the source contract does not establish them.

## 5. Evidence failures are visible without inventing market failure

Corrupt existing evidence, wrong-provider contents, capture identity mismatch, concurrent lock contention, failed atomic persistence, a malformed response or missing observed HTTP status cannot produce a successful receipt. Existing evidence bytes are protected and persistence is checked by readback. A missing HTTP status is not filled with an assumed 200.

The numerical collector output is independent of successful evidence recording. The controlled ordinary `run_adapter()` test proves that when evidence persistence fails, the existing numeric series are still stored and the collector's existing result-status path reports degraded/stale. The adapter does not claim a new time-qualified observation, erase prior evidence or trigger a new provider retry.

This distinction matters: usable current price/flow context is not necessarily usable historical first-seen evidence. Losing the latter should be observable, but must not fabricate a bearish market signal or force cash allocation.

## 6. Exact elapsed windows and truthful flow context

The repaired CVD reads only observations at or before its explicit UTC evaluation cutoff. Undated observations are rejected before filtering; duplicate/off-hour labels and invalid quantities are not cleaned into apparently valid observations. Boolean true is not treated as one unit of volume. It finds the latest continuous valid segment and computes 24/72-hour observation-label windows only when every required hour exists. Any missing or invalid hour breaks continuity, not only a gap larger than the provider's retrieval window.

A zero-activity window has known zero volume but no defined buy-share ratio. Balanced positive activity is distinct from missing data. Cumulative native volume starts with the current continuous segment; no silent forward-fill crosses a price gap to construct a divergence.

Unknown provider units are not converted into dollars. Existing output keys for scaled millions/billions remain present with null values for compatibility, while descriptive native values and coverage are separately named. The source remains OKX aggregate derivatives, not all-market capital flow. Strong historical language about a proven leading divergence or investor accumulation/distribution is removed from the current consumer. This is a descriptive measurement, never a new scored signal or sizing authority.

Freshness is checked against the evaluation clock as well as the stored price reference. In the unchanged September 26 snapshot, flow and price labels agree. At the explicit September 29 12:00 UTC audit clock, however, both are 71 hours old: relative lag is zero, but the flow context is stale and its directional state is unavailable. This demonstrates clock behavior on a stored snapshot, not a live diagnosis of a running collector.

The existing builder warnings were updated with the consumer: a short gap is no longer called an unbackfillable 30-day outage, and old observations are not stated to prove that collection stopped. This change is limited to diagnostic wording and availability handling, not allocation logic.

## 7. Compatibility, hostile cases and verification

The ordinary collector entry point was exercised with fake HTTP and temporary storage, not merely a mocked return from the new persistence helper. OKX's three targeted request signatures per run are unchanged; BGeometrics' targeted fetch still makes one request. Funding and flow numeric frames remain equal before and after capture activation in those controlled cases. No raw provider account or market-data call was made. Public documentation was read separately, without activating an entitlement.

The synthetic pipeline verifies nine distinct receipt identities across three response types and three receive times, four funding as-of views, repeat/revision/reversion handling, and explicit evidence-failure degradation. Separate direct timestamp membership and scalar arithmetic verify 54 elapsed-window scenarios across complete, gapped, invalid, zero and balanced histories. Two checks against the unchanged stored snapshot confirm its current native window arithmetic and the distinction between wall-clock and relative freshness. These are test scenarios, not independent market events or predictive-success counts.

The recovered candidate's broad test failure was traced to a historical diagnostic that imported the *current* CVD. After the CVD repair, that no longer reproduced the original defect. The historical helper now loads the original exact source from R9 commit `d636e9c405c0283209eb75b09d477d32003ff827` and verifies its SHA-256 before running the synthetic fixture. Original helper bytes are retained, and the actual scientific test file held by another source owner is not changed. No R10 empirical results or forecast tests were rerun to manufacture agreement.

A separate CI packaging defect had caused the archived `test_btc_impulse_falsifier.py` copy to be discovered as an unenrolled live suite. It is now retained byte-for-byte as `.py.txt`, with preserved before/after manifest evidence. The real suite remains enrolled and unchanged. The original checker passes; no allowlist, waiver or assertion was weakened.

Adversarial review produced real failing tests before fixes for nested public-field objects, provider-directory mismatch, undated observations, boolean quantities, malformed settlement times and invented default HTTP success. Tests also cover corrupt/unreadable stores, failed atomic writes, lock contention, identical retries, conflicting simultaneous responses, later null revisions, out-of-order capture input, impossible settlement/receipt ordering and timezone normalization. Normal source responses were not altered to satisfy these cases.

Verification results on final source candidate `b53636f05b6374dafabcbc9c5d8085773d88fdf0`:

- Collector/CVD tests: **50 passed**, 43 warnings.
- Broad existing Crypto/Vector/storage/science invocation: **368 passed**, 49 warnings.
- Python compilation, existing source-claim checker and difference checks: pass.
- Original suite-enrollment checker: exit 0; no newly dark suite. Existing repository-wide unrun/baseline warnings remain reported and are not declared solved.
- Full synthetic pipeline: exit 0; ordinary entry/storage behavior, independent timestamp arithmetic and response identities checked.
- All 57 recorded input identities, 18 gate files and 137 prior research artifacts remain unchanged. The shared storage owners remain unchanged. Actual OKX/BGeometrics response-observation files were absent before and after proof; only temporary fixture stores were created.

The successful pipeline before the final timestamp/status hardening is preserved. The changed-source verification repeats the same fixed synthetic scenarios; their semantic results are identical. This is compatibility verification after an actual code change, not a repeat or tuning of a financial experiment. The original failing logs are retained. Pytest-generated trailing whitespace was normalized only after a commit check stopped before execution; its original/normalized hashes and the reason are recorded. No failure result was edited away.

Numerical cross-checks are independently expressed in this same session, not independent code/science review by another person or model. The result remains a source candidate, not a release approval.

## 8. What remains open

The additive producer can preserve facts that future ordinary collection receives; it cannot reconstruct omitted historical first-received data. Nor does receiving a response establish provider first publication, finality or stable aggregate membership. No previously rejected funding-history splice, assumed settlement schedule, higher prediction confidence or new alert eligibility is enabled.

A completeness-qualified daily settled-cost view is still separate work: preserving individual responses/events is not proof that all expected settlements for a day are present. The actual interval and completeness must be established before that view can replace any existing interpretation. Likewise, the CVD output uses exact elapsed *label* coverage and explicitly unqualified semantics; its `ok`/warm-up fields must not be read as permission to feed a causal forecasting model.

Operational review must inspect the actual retention cadence, maximum history size, repeated overlap volume and atomic-file cost. Each response is bounded and failures are observable, but this batch does not certify unlimited store growth, multi-host locking or production throughput. The lock is local file exclusion under the current writer, not a distributed coordination service.

The next bounded release unit is independent review of these exact source/consumer boundaries, exact-head CI and a lawfully admitted prospective collection check through the existing process. That check must prove that real incoming responses are durably retained, remain backwards compatible, expose failures, and can be reconstructed as of their actual receipt times. It must not backdate freshly collected historical responses or claim a ChatGPT turn is a collector daemon.

Only after source-specific units, aggregate scope, timestamp roles and sufficient comparable observation history are established should the additional data enter a frozen incremental-information study. R1–R10's unfavorable results and training floors remain intact. No live model, design board, user review, alert, trade, merge or deployment was changed in this R11 source-repair batch.

[1] Official OKX funding-history documentation, rechecked 2026-09-29: https://app.okx.com/docs-v5/en/#public-data-rest-api-get-funding-rate-history . This endpoint identifies `fundingRate` as predicted, `realizedRate` as actual, and `fundingTime` as settlement time; it also distinguishes formula/mechanism and discusses varying intervals. Those semantics are not borrowed from a different WebSocket or ticker endpoint. Documentation establishes field meaning, not Mastermind's historical receipt time or source efficacy.
