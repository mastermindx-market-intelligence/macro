# B3/B5 source-admission research reference

Status: **C2 bounded implementation/research; proposed synthetic contract, no production integration.** Prepared 2026-10-03 for `options-intelligence-deep-research-20261003-astra-001`, under procedure pin `20adcaf65c2dd1bb734ab06e215feb1a0eb65659`.

The deliverables are `source-admission-reference.py`, `source-admission-fixtures.json`, and this specification. The Python standard-library reference is an offline, deterministic experiment over supplied JSON. It does not query a provider, certify real source data, publish candidates, install a store, create a correction ledger, or change an incumbent lifecycle. `source_certified_accepted` is always false, including successful fixtures. The booleans `synthetic_contract_pass` and `captured_pit_eligible` describe the local fixture contract; neither grants production admission or demonstrates real historical capture.

**WHY NOT FABLE:** this is a finite deterministic contract and adversarial fixture task, already subject to independent review. Launching implementation orchestration would add scope before the source policy, exact adapter qualification and migration gates exist. Production work belongs to the existing owners after those gates are adjudicated. No Fable, M2, Executive, live runtime or GitHub write is part of this reference.

## Evidence and boundaries

The reference applies B3/B5 in `OWNER_REPAIR_BRIEFS.md`, `CONTRACTS.md`, and the trade-clock/condition census in `options-macro-census.md`. The census is pinned to Macro `6f5e78e94e8808582a650cdfa0fc3357040a179c`; the PR #8310 candidate-schema supplement is pinned to `a15ba9ae77826bf6a1d6fcb40022b6816b705e43`. The latter is a candidate head, not a claim that it is merged or active. Source repository: `mastermindx-market-intelligence/macro`.

The census distinguishes three existing quantities: premium-weighted category scores `~buy → .80`, `~sell → .20`, `mixed → .50` in `build_chain_heat`; measured `microstructure.at_ask_share`; and inferred positive-premium signing share. Their names do not make them interchangeable. It also records current measured rejection of future, locked, crossed and missing quotes. Maximum age, condition eligibility, and cancellation/reversal qualification are gaps at that pin. The additional gates below are **proposed synthetic policy**, not claims about existing implementation or provider rules.

The source retains trade/quote timestamps, exact nullable sequence and raw trade/quote condition fields. A root's post-fetch `observed_at` is response observation; it is not necessarily per-print socket receipt or exchange/SIP time. A max-sequence watermark does not establish an amendment ledger. This reference does not reinterpret these fields or retrofit historical captured receipts.

Read sources and SHA-256 values:

| Source | SHA-256 |
|---|---|
| `OWNER_REPAIR_BRIEFS.md` | `5282755ed0b67932e24037e07f9d2c099352884dae4843e31e26813057f4233c` |
| `CONTRACTS.md` | `e2a8ced5a769996a8b46a737db07d33ce6a9571b8838d763447d5c2e19514db5` |
| `options-macro-census.md` | `02c9e1050c4003bd7ed0756eed9f419888fa20c4021611164d3df2ff3b9d0dc9` |
| `/tmp/options-macro-source/contracts/options/options.alpha_candidate_feed.v1.schema.json` | `04f0d87772ab28e6b9fe6ecb15981132f6f6dbecb83deb9826bddfc9f1bc5290` |

## Separate evidence, strict candidate schema

The inspected candidate schema has `additionalProperties:false` at root, candidate and measured-object levels. Its measured keys are only `source_print_count`, `nbbo_valid_print_count`, `nbbo_premium_coverage`, `source_premium_usd`, `nbbo_covered_premium_usd`, `schema`, and `schema_digest_sha256`. There is no general `options_context` slot. This experiment is a **separate research evidence reference**, not a conforming candidate object or an adapter. Do not append its fields to production candidates without an explicit reviewed migration. Its zero-valid or refused examples cannot become qualifying candidates; the inspected candidate contract requires positive valid count and coverage. All 15 inspected authority flags remain false, and the candidate publication boundary is `caller_supplied_synthetic_only_no_live_publication`.

Retain existing candidate, campaign, event and campaign-revision IDs, including `candidate_id`, `campaign_id`, `final_event_id`, `first_qualifying_campaign_revision_id`, and `current_campaign_revision_id`. Local `evidence_ref` and synthetic references introduce no alternate lifecycle. Do not overwrite incumbent `source_formed_at`, `first_observed_at`, `decision_at`, `available_at`, or `published_at`. B3 remains with `WS:INTRADAY-FLOW-P0-RECOVERY`; B5 data provenance involves `WS:ADVANCED-DATA-OPTIONS`, with candidate consumption and historical evaluation through the existing options-alpha and options-context owners.

## Proposed policy and monetary units

The fixture policy is `synthetic_source_admission/v1`, version 1, status `proposed_synthetic_only`. Its condition policy is `synthetic_conditions/v1`, version 1, qualified only as `synthetic_fixture_only`. `SYN_T_REGULAR` and `SYN_Q_TWO_SIDED` are invented fixture tokens, **not feed condition codes**. Missing/unqualified policy fails. `input_origin` other than `synthetic` produces `REAL_SOURCE_UNQUALIFIED`; changing a real-source payload's label cannot constitute source certification.

The default maximum quote age is 1,000 ms, inclusive; a configurable positive integer and the exact policy content digest accompany output. Price tolerance is exactly zero. Quotes must be strictly earlier than trades: an equal timestamp gives insufficient ordering under this contract. Timestamps require explicit offsets or `Z`, ASCII syntax, at most three fractional digits, legal offset minutes, and valid calendar/time values. Declared precision is 1 ms and uncertainty is zero for this synthetic experiment. Unknown/nonzero clock uncertainty refuses captured eligibility; this is not a claim that real clocks achieve zero uncertainty.

For each record, premium is `p × q × m` USD: `p` is dollars per underlying unit, `q` is a positive integer contract count, and `m` is actual underlying units per contract for this supported synthetic single-underlying deliverable. The baseline `p=2, q=2, m=50` is USD 200. Quote multiplier must match the retained, versioned contract reference. Missing/mismatched multipliers, unqualified units/currency, or adjusted/cash deliverables without a qualified transform cannot be silently multiplied by 100. Complex deliverables are deliberately outside this reference's accepted domain.

Bid/ask must be positive, unlocked, uncrossed and accompanied by positive integer sizes and eligible synthetic conditions. Quote `contract_id` must match the trade. The quote travels inside the whole-record input receipt; there is no separate quote-arrival claim. All supplied source fields are retained in an immutable deep-copy view.

Source sequence is a **proposed synthetic contract/session identity**, represented as canonical ASCII `0` or `[1-9][0-9]*`; leading zero forms, non-ASCII digits and unknown scope refuse admission. No real provider scope is inferred. Duplicate record IDs or duplicate contract/scope/sequence/UTC-session-date identity refuse the cohort. Only `synthetic_original_unamended` is admitted: unresolved correction or sequence uncertainty refuses the whole cohort and its complete economic denominator. This is a bounded ambiguity check, not deduplication, amendment resolution, or late replay.

## Unknowns and denominators

`source_print_count` counts supplied records within the declared source population. Only `selected_notable_event_subset` and `synthetic_fixture_population` are supported. Matching unknown or “market-wide” request labels still refuse; a notable-event subset cannot be relabeled market-wide.

`valid_print_count` counts rows meeting the quote policy. `print_coverage = valid/source`; `premium_coverage = covered/source premium`. Source premium is complete only when all monetary references and cohort identities are qualified and no correction is unresolved. Otherwise `source_premium_usd=null` and completeness is false. `known_record_premium_usd` retains the raw known sum for inspection; it must not be presented as deduplicated economic turnover. Incomplete proxy denominators also refuse the proxy claim.

NBBO location shares are premium-weighted **conditional on covered premium**. Zero denominator yields null. A valid midpoint print has observed at-ask share zero and inside share one, while its inferred sign is unknown. A missing quote is unknown measurement, not an observed zero. An outside-quote print has measurable location “outside” but abstains from signing.

| Baseline variants, all premiums USD 200 | Source / valid | At-ask share | Category proxy | Inferred sign |
|---|---:|---:|---:|---:|
| Trade 2, bid 1.8, ask 2; category `~buy` | 1 / 1 | 1 | .8 | +1 |
| Trade 2, bid 1.8, ask 2.2; same category | 1 / 1 | 0 | .8 | null |
| Missing quote; same category | 1 / 0 | null | .8 | null |
| One at-ask row plus one unknown-quote row | 2 / 1 | 1 | .8 | one classified, one unknown |

The final row has premium coverage .5, not complete-market at-ask share 1. Category proxy is separately labeled `source_side_category_proxy`, uses only category-covered premium, and reports category coverage. It cannot satisfy a measured-NBBO claim. Signing uses a transparent synthetic midpoint rule, not a customer/aggressor ground truth, opening/closing classification, dealer inventory, or confidence probability. Unknown sign is null, with counts and premium mass explicit. Signed premium is null if no row can be signed; a measured net zero is possible only from actual classified contributions. No unknown is coerced to neutral zero.

## Input, artifact and consumer point in time

Trade event ≤ whole-record observed ≤ input available is required. Versioned contract reference availability is separate. These classifier dependencies must all be available by `producer_classified_at`. Additional OI/Greek references are declared **feature-only dependencies** and may arrive after classification but must be available by feature `computed_at`. A positive fixture demonstrates that distinction.

All declared inputs must be available by computation; producer classification ≤ computation ≤ artifact publication ≤ consumer receipt ≤ consumer admission ≤ candidate decision. Publication and consumer receipts bind the same nonblank, typed artifact ID and revision. Matching input/receipt revisions are mandatory. The producer classifier's clock is not the candidate decision clock. Input PIT alone never establishes artifact-to-consumer PIT.

Captured-mode flags, whole-record receipts, contract-reference retention, publication/consumer receipts and additional-input receipts are required for the synthetic captured check. Reconstructed provenance and a captured label without retention fail. These receipts are **simulated assertions**, not independently authenticated originals; hashes bind the exact local packet and policy, not external custody, publication or historical availability. `captured_pit_eligible` concerns this receipt/clock evidence only and can be true while measurement admission fails for another reason. Always inspect `synthetic_contract_pass` and reason codes as well.

OI references distinguish effective time from source/receipt/available times; OI is a nonnegative integer, not publication at its effective date. Greek references require underlying timestamp/source, model/version, price basis, rate/dividend/inversion references, contract binding, TTE, ACT/365F, expiry-rule reference and explicit units. Proposed units are decimal annualized sigma, delta as price per underlying price, gamma per underlying price, vega per decimal sigma, vanna as delta per decimal sigma, and charm as delta per calendar year. Every such view retains `numerical_accuracy_qualified=false`: metadata completeness proves neither fresh underlying pricing nor correct inversion, scaling, expiry treatment or Greek values.

Outcome references are separate. A label's value appears only after both its maturity and availability at the evaluation clock, with typed nonblank label ID/revision. Pending/invalid labels return null, never zero. An available observed zero is retained. Outcome values do not enter the feature or its admission calculation; this is no fill, cost or P&L evaluator.

## Revision and population identity witness

The parent supplied a current board with `as_of=2026-10-01`, emit `2026-10-03T08:15:30+00:00`, pair `f9f4108104c84918bacc5ff06805be40`, blob `bae9b8dac3b1cfefe9912e58c3d524f8c2007a1d`, and 69 rows; archived W3 has the same date, 62 rows, and observation fingerprint `cf0059c8da553ea5ad07bdf8cc4ce8252ca504e78dcea17b164b39f37fe3627b`. B4 package reference: `626848e`.

No artifact was independently fetched here. These supplied identities form one concrete negative fixture: equal dates do not authorize joining incompatible revisions/populations. The supported identity-only join requires exact nonblank revision/population/date equality and equal positive row counts. An identical-artifact positive control passes. No crosswalk, row matching or compatibility across revisions is invented.

## Verification and use

From this directory:

```bash
python -B source-admission-reference.py --self-test --mutation-check
python -B source-admission-reference.py --case same_date_incompatible_board_archive
python -B source-admission-reference.py --validate-stdin
```

The stdin envelope is exactly `{"evidence": ..., "policy": ...}`. Duplicate JSON keys, nonfinite constants and malformed envelopes refuse with exit 2. Direct `evaluate(evidence, policy)` is deterministic and performs no I/O. Successful synthetic stdin validation exits 0; refused stdin validation exits 2. `--case` prints a named fixture's result, including negative controls, and exits 0 for inspection. A failing suite exits 1. No-argument invocation runs the suite. There are no output-file, network, runtime-install or production-publication operations.

The 73 literal fixtures include valid zeros versus unknowns; partial quote coverage; future, tied, stale, locked, crossed and ineligible quotes; corrections and duplicate identities; monetary provenance; clock and receipt chains; metadata-only OI/Greek references; outcome availability; and revision/population mismatch. Every fixture also checks deterministic repeated output, unchanged inputs/policy, and source-record retention. Expected assertions are hand-derived, not generated from the evaluator.

Test-first evidence: the initial 50 cases failed before implementation; independent review added 12 failing regressions; the next review added 10 failing regressions and a positive feature-only timing control. Final result is **73/73 passing**. The harness temporarily injects ten forbidden defects: unknown-to-zero, future quotes, ignoring publication, unqualified condition policy, proxy-as-measured, blanket multiplier 100, reconstructed-as-captured, ignoring consumer cutoff, ignoring corrections, and date-only joins. **All ten are killed**, and the baseline passes after restoration. The harness changes only in-memory functions and restores them in `finally`; it does not mutate any installed system. Output is stdout, with no fourth result artifact.

Before production admission, existing owners must settle exact source clocks and uncertainty; real condition enums/eligibility and amendment semantics; sequence identity scope; actual multiplier/deliverable transforms; receipt custody and immutable revision binding; source coverage population; metadata and numerical qualification of Greeks; and the exact active consumer/schema migration. The configurable synthetic age threshold is not an empirically selected execution-quality threshold. These are explicit unresolved source contracts, not evidence of prediction efficacy or implementation readiness.
