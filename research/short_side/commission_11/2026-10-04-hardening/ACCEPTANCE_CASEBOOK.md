# C11 acceptance casebook — design fixtures, not completed implementation tests

These scenarios specify required behavior for later implementation. **They were not run against production collectors or consumers in this research commission.** Synthetic timestamps and quantities below are deliberately small and are not market observations. Document validation checks the casebook's structure; it does not prove an implementation conforms.

## Temporal and replay scenarios

| ID | Given | Required result | Defect prevented |
|---|---|---|---|
| T01 | SI settlement September 30, 2026; official publication October 9; decision October 4 | Exclude that settlement in source-knowable and actual-system modes | Settlement/reporting-deadline look-ahead |
| T02 | Synthetic source generation published at 18:00Z, first received 18:07Z, persisted 18:08Z, admitted 18:10Z | SOURCE_KNOWABLE may use at 18:05Z only with qualified original generation/entitlement; SYSTEM_REPLAY excludes until 18:10Z | Public availability confused with actual knowledge |
| T03 | Source reports a date but no time | Apply a sourced or explicitly conservative boundary; never invent midnight release | False precision |
| T04 | Generation 0 admitted at t1; corrected generation 1 admitted at t3 | Replay t2 returns generation 0; replay t4 returns generation 1 for the same economic record | Retroactive restatement |
| T05 | Older settlement corrected after a newer settlement was published | Correct the old lineage without making it the latest economic state | Arrival ordering confused with economic ordering |
| T06 | Identical bytes fetched twice | Two receipt events can refer to one content object; no invented second economic event | Duplicate observations |
| T07 | Source tombstone or authoritative retraction | Preserve prior generation and append a retraction; later view abstains or applies sourced replacement | Destructive erasure |
| T08 | Two pages belong to incompatible snapshot generations | Quarantine or explicitly incomplete; no admitted whole-market cross-section | Hybrid snapshots |
| T09 | Historical current-value download contains a revision flag but no original publication payload | AS_RESTATED qualification; exclude from strict original-vintage replay | Lag-adjusted hindsight |
| T10 | A source-only historical reconstruction predates Mastermind's first receipt by years | May enter a qualified counterfactual research mode; never actual-system history | Fabricated operating history |
| T11 | Vendor entitlement starts after the proposed historical decision | No claim that Mastermind could lawfully have used that vendor at the decision; state counterfactual license assumptions separately | Retrospective entitlement |
| T12 | Entire SI panel stops at July 31 but is queried in October | Expected-release and decision-clock freshness fail independently of within-panel staleness | Frozen panel marked fresh |

## Identity, units and source-scope scenarios

| ID | Given | Required result | Defect prevented |
|---|---|---|---|
| D01 | Same ticker belongs to two different historical listings | Resolve by effective-dated listing identity; never join across issuers | Reused ticker contamination |
| D02 | Split changes share units between position date and ADV window | Align numerator/denominator units or abstain; preserve raw values and adjustment receipt | Manufactured DTC/float change |
| D03 | FINRA ADV settlement precedes decision, but release follows decision | Reject the ADV input or use a separately qualified historical liquidity source | Ownership-crowding publication leakage |
| D04 | ADV column absent, ADV zero, or a DTC sentinel | No valid DTC percentile; distinct missing/zero/sentinel flags | Fail-open denominator guard |
| D05 | IBKR availability token `>10000000` | Lower bound strictly greater than ten million; not exact ten million, infinity or an unlimited guarantee | False precision and false safety |
| D06 | Numeric availability zero versus parse failure versus symbol absent | Three distinct states; none silently fills the others | Missingness as calm |
| D07 | Raw IBKR record contains ISIN/FIGI/CON | Preserve identifiers in source envelope, even when canonical mapping is unresolved | Discarded identity evidence |
| D08 | Out-of-universe security falls below the retained fee threshold | Mark selection/inclusion change; never interpret disappearance as zero fee or vanished short demand | Feature-dependent censoring |
| D09 | FINRA file contains ShortVolume 60, ShortExemptVolume 5, TotalVolume 100 | Short ratio 0.60; non-exempt short volume 55 when subtraction is valid; not 0.65 | Exempt double counting |
| D10 | Exempt value malformed or greater than total short volume | Invalid observation/quarantine, not zero | Coercion hides data faults |
| D11 | CNMS consolidated file and individual constituent facility files loaded | Choose a non-overlapping scope; do not add both | Facility double counting |
| D12 | One broker reports lower availability | Broker-scoped observation; market-wide supply/utilization remains unavailable | Scope inflation |
| D13 | Two providers use different lender populations or rate weights | Preserve definitions; do not average as an independent market consensus without a specified estimator | False corroboration |
| D14 | Current SIC/GICS label attached to a historical leaver | Non-era-correct flag excludes it from a claimed historical sector control | Survivorship/sector look-ahead |
| D15 | 13F form versions use thousands versus dollars | Normalize by actual filing schema version; retain original unit | Thousandfold value error |
| D16 | Same beneficial position appears through manager/submanager or ETF look-through | Existing holdings owner resolves overlap; disclose unresolved coverage | Ownership double counting |

## Consumer, model and research scenarios

| ID | Given | Required result | Defect prevented |
|---|---|---|---|
| A01 | High SI but lending supply absent | Show high reported position and missing supply; no aggregate LOW or imminent-squeeze verdict | Missing dimension hidden by label |
| A02 | Option OI exists, dealer side unknown | Modeled sign scenarios or explicit assumption; no observed-dealer claim | Unobservable inventory presented as fact |
| A03 | New source producer writes an existing artifact consumed by a factor | Consumer/import/key regression test required even if C11's own authority fields are false | Indirect authority widening |
| A04 | Existing PSS construction has a similar crowding name | Preserve its frozen identity and outcomes; C11 is not an unannounced replacement or pooled sample | Scientific identity collision |
| A05 | Vendor outperforming baseline uses fewer, more liquid names | Re-evaluate on identical admitted support and report deployment missingness | Coverage selection mistaken for information |
| A06 | Researcher tries secondary horizon after primary fails | Retain primary failure; secondary remains exploratory; no promotion | Outcome-driven model selection |
| A07 | Return rows overlap by 21 sessions | Use appropriate dependence/purge treatment; raw row count is not independent N | Inflated significance |
| A08 | Data rights permit internal research but not Terminal display | Internal processing may proceed within terms; external display remains blocked | Access mistaken for redistribution rights |
| A09 | A large upside event occurs without direct covering evidence | Price-tail label only; causal squeeze attribution remains unverified | Circular labels |
| A10 | Avoid strategy reduces drawdown but misses larger gains or changes cash exposure | Compare explicit replacement/cash/exposure/cost counterfactual | Free-lunch de-risking claim |
| A11 | Historical sample too small to distinguish minimum useful effect | UNDERPOWERED; do not classify proof of no value or promote anyway | False certainty |
| A12 | New generation fails normalization or source-completeness checks | Preserve raw receipt in permitted storage, keep prior admitted view stale/qualified, do not overwrite healthy state | Failure destroys evidence |

## Synthetic arithmetic oracles

These are specification examples, not claims about an implemented engine:

- DTC: short shares 2,000,000 and ADV 500,000 imply 4 sessions. If shares remain unchanged and ADV falls to 250,000, DTC becomes 8 solely because liquidity declined.
- Utilization: Q=800 and L=1,000 imply 0.80 only when L is total lendable inventory including the on-loan portion under the provider's definition. If L instead denotes remaining unused availability, the same formula is not admitted.
- Liquidation scenario: tracked shares 2,000,000, ADV 500,000 and participation 10% imply 40 sessions under a constant-liquidity assumption. This is not a guaranteed executable liquidation duration.
- Fee units: 1 percent/year equals 100 basis points/year and normalized decimal 0.01/year. This conversion does not establish the correct day-count basis, financing charge or realized transaction cost.
- Statistical budget: four public families × two primary endpoints = eight confirmatory tests; one separately admitted commercial family adds two. Secondary horizons do not expand promotion opportunities within this generation.

## Evidence required from a later implementer

For each case, record the implementation commit, exact test/fixture identifier, expected output, actual result and source-owner review. Include a mutation or deliberately broken input where practical to prove the test detects the intended failure. An all-green synthetic suite is insufficient without an actual owner-path integration test and a current consumer diff.

The initial implementation commission covers capture/replay qualification, not the entire empirical or product program. Cases outside that first wave remain mandatory gates for the phase that introduces the corresponding behavior. No test result here authorizes a live portfolio or ranking change.
