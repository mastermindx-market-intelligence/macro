# Issuer guidance: revision before results, delivery against the right version

**Built research/factual algorithms; NOT a promoted stock-selection model.**

This second phase followed the completed D5-detail consumer rather than treating
its test pass as a stop. It adds three pieces to the existing `engine/sue.py`:
`IssuerGuidance`, `guidance_change` and `guidance_delivery`. The existing factual
dossier accepts the delivery observation separately from analyst consensus.
No collector, forecast store, model registry, live rank or new policy was added.

## Two distinct information events

**At a guidance update**, `guidance_change` compares an explicitly source-qualified
adjacent pair for the same issuer, metric, accounting/share basis and fiscal period.
It requires both sources to be available at that decision; an actual earnings
result is not an input. Lower-bound, upper-bound, midpoint and width changes are
separate. A higher midpoint with a lower downside bound is a mixed range change,
not an automatically stronger forecast. Withdrawal/reintroduction is not a
continuous numerical revision. Missing adjacency stays unavailable.

**At the eventual results**, `guidance_delivery` selects the latest usable,
comparable pre-release issuer range, not the oldest convenient range. It refuses
ambiguous equal-publication values, discloses excluded basis/clock records, honors
withdrawal/expiry without older-record fallback and requires a source-owner
complete-history assertion. No complete-history claim is inferred from the number
of records supplied. The range is management's stated forecast, never a
confidence interval or an analyst consensus. All ranking/entry flags are false.

When the forecast episode is continuous, the arithmetic is preserved exactly:

`actual - initial midpoint = earlier midpoint revision + actual - latest midpoint`

The first part was earlier information. The second is the residual against the
latest qualified issuer outlook. Neither is a return forecast or a trading rule.
These are candidate factual inputs for the existing Earnings sleeve, not a claim
that the inputs improve stock returns before a registered incremental comparison.

## Primary-source historical counterexample

Micron FY2025 Q4, revenue in USD millions:

| Observation | Public date | Midpoint / actual | Range |
|---|---|---:|---|
| Initial outlook | June25,2025 |10700|10400–11000|
| Revised outlook | August11,2025 |11200|11100–11300|
| Reported actual | September23,2025 |11315|not a forecast|

SEC sources:
- https://www.sec.gov/Archives/edgar/data/723125/000072312525000019/a2025q3ex991-pressrelease.htm
- https://www.sec.gov/Archives/edgar/data/723125/000110465925075940/tm2522933d1_ex99-1.htm
- https://www.sec.gov/Archives/edgar/data/723125/000072312525000024/a2025q4ex991-pressrelease.htm

Against the initial midpoint the difference is615million;500million was already
in the August update. The remaining difference is115million against the revised
midpoint and15million above its upper bound. Thus81.3%of the initial-midpoint gap
was already disclosed in the guidance upgrade. It would be misleading to call
all615million a new September beat. Conversely, the August change itself is
observable before the final results and can be separately evaluated as a candidate
information event without hindsight access to September's actual.

This historical construction uses public dates and verified amounts only.
System-ingestion times are UNKNOWN, so it is not a point-in-time historical trade,
original Prophet recommendation or executable return. Code tests use synthetic
instant clocks with these numeric values to test chronology. The JSON companion
retains raw retrieved-page hashes, URLs, exact values and these limitations; the
source bodies are retained in this session's existing evidence directory, not a
new production store. No full market-wide event census or financial outcome is
claimed.

## Qualification and scientific next step

Across the existing earnings/fusion and D5/API suites, the final source now passes
**231 tests /12 warnings /0 skips**. The priorD5-stage196count is a subset, not an
additional count. Final log SHA256 `9ee831836454bec19c58d2b2b56a79c30f5a2e530496a5fe7e6cd1d8d1ac43b1`.

Guidance tests cover latest-version selection, pre-result usability, wrong basis,
withdrawal/expiry, absent history, duplicate/ambiguous revisions, range boundaries,
input-order invariance, dossier identity, output copies, range widening and the
ability to compute an upgrade without final results. Earlier source-hash and
endpoint-disconnection faults also remain tested.

Selecting the obsolete forecast deliberately fails the source-vintage test,
logSHA256 `9eabfe2c8be8ee29d81b845be5359f2a8350d34a4762022ba9f02a1f08b0433c`.
Treating incomplete history as complete deliberately fails its test,
logSHA256 `e00a260335471a0c49dfe87da6a28314c98a342505cfaf5731e869e3b32a0e0e`.
Original bytes restored. These are software discrimination tests, not alpha proof.

The natural next experiment is NOT a fresh score assembled from all these numbers.
Under existing B15/Evaluation ownership, first qualify issuer-guidance event
coverage and correction/availability history. Separate an update-time cohort from
a results-time cohort. Compare incremental value beyond the current company-price
and independent sector baseline on the same eligible population, hold market/entry
policy fixed and charge for elapsed price response, costs and unfilled entries.
Factual management delivery and stock-price predictability are separate estimands.
Do not access H1/Cycle outcomes, import unlicensed consensus, reset trial history,
or select thresholds after seeing the protected result.

Source stays on PR#8189 with the D5 consumer. Existing engine owner and pure-math
contract remain; production guidance ingestion, model promotion and automatic
recommendations are not activated by this commit. The original legacyC1 default
and all old grades remain unchanged.
