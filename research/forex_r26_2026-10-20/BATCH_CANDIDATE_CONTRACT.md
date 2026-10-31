## Numeric offset range repair — 25 October 2026

Independent repair [review006](https://github.com/mastermindx-market-intelligence/macro/pull/10052#pullrequestreview-5641438013)
authenticated parent `cbe30ec7ca5cef3c8fbda08f0c38b232a86325b9`.
The unchanged original independent harness passed all 37 cases, while 40 of
44 added probes passed. Its four failures exposed one remaining issue: pandas
normalizes malformed offset minutes such as `+00:60` and `+0199`, allowing
invalid caller clocks to satisfy both public candidate assessors.

The explicit offset grammar now requires hours 00–23 and minutes 00–59 before
pandas parsing, for either sign and both HH:MM and HHMM forms. Nanosecond
normalization and chronology checks are unchanged. The added public regressions
exercise invalid minutes and hours in both caller fields across single and
batch assessors, plus valid positive and negative 23:59 boundary controls.

Before this source repair, the 28 new cases produced **16 failures and 12 passes**
on the parent parser. After repair, the complete source test file passed
**303 tests with zero skips**, including the real PyArrow paths. The original
independent 37/37 and 40/44 results remain attributed to cbe; independent repair
recheck and exact-head contract/publication/CI are recorded on PR10052.

Candidate policy remains unadopted, eligibility empty and admission false.
The separate historical readback-digest target/serialization limitation is not
silently repaired or converted into accepted provider provenance.

---

## Clock precision repair at cbe — retained qualification

Independent source review 004 reproduced a precision-loss defect on parent
`e2169fe462017d849b525c16dd44d2f45a69393a`: compact ISO clock strings with comma
fractions could collapse to whole seconds in pandas 2.2.3. A readback at
`2026-02-16T160200,9Z` and assessment at `2026-02-16T160200,5Z` then appeared
equal, hiding the actual 400 ms inversion in both exported candidate assessors.
The original review's 35 passing and two failing independent cases remain
retained; the failure is not relabeled as a passing original test.

The shared clock parser now admits an explicit lossless subset: extended or
basic calendar dates and second-resolution clocks, separated by T/t or a space;
an optional dot fraction of one through nine digits; and Z/z or a whole-minute
numeric UTC offset in HH:MM or HHMM form. It normalizes that syntax to extended
ISO before pandas parsing and UTC conversion. Comma fractions, precision beyond
nanoseconds, naive clocks and unsupported forms are refused rather than
truncated. Valid compact/lowercase/offset forms preserve their represented
nanoseconds, so chronology checks retain their original meaning.

At cbe, the affected source test file passed **275 tests**, including 24 new public-API
cases across the single and batch assessors: lossy input refusals, one-nanosecond
assessment inversions and accepted lossless ordered controls. The independent
repair recheck and exact commit/CI binding are recorded on
[PR10052](https://github.com/mastermindx-market-intelligence/macro/pull/10052).
The actual census emits canonical ISO clocks; the original reproduction does
not demonstrate that historical census outputs were affected.

This repair does not adopt the candidate policy, admit an observation, acquire
provider data, renew the expired October 22 evidence, or activate monitoring.
`CANDIDATE_NOT_ADOPTED`, empty eligibility and false admission flags remain.

---

## Follow-on enqueue design — 24 October 2026

The selected full delivery-vintage encoding, source eligibility-generation fence, invalidate-first publication, atomic enqueue and account lifecycle proposal is now specified in [OWNER_INTEGRATION.md](OWNER_INTEGRATION.md#selected-source-fence-and-lifecycle-protocol--24-october-2026). The observation identity and revision decisions below are unchanged. That follow-on owner design remains uninstalled and subject to incumbent acceptance and qualified review; it does not adopt this candidate policy or renew the expired October22 evidence.

# Owner-selected observation identity for qualified review — 23 October 2026

The assigned recovery/source owner has completed the remaining name, byte encoding and local-revision design decisions below. They are submitted for the existing qualified source review. **The /2 candidate policy remains unadopted:** no feed is registered, observation admitted, account activated, or evaluator/queue added. The original Forex policy-review operation remains unqualified; this owner decision and native advisory analysis do not replace its verdict.

## Exact source-contract name

Select the existing proposed literal `tiingo.fx.USDJPY.reported-close.utc4h.local/v1` for the reviewed future `feed` binding. Its scope remains USDJPY, JPY per USD, Tiingo-reported native historical close with the incumbent minute-consistency evidence and local UTC4H qualification. It does not mean midpoint, executable transaction price, vendor finality or independently attested producer execution. The name is a design selection, not an installed registry entry. No aliases, trimming or case folding are admitted. A later change to this literal or encoding requires an explicit versioned contract decision; it must not silently preserve or migrate old identities.

## Deterministic logical observation ID

After the existing source qualification succeeds under an actually adopted contract, the future owner projection uses exactly six strings in this order:

```text
[contract,"USDJPY","4H","fx-utc-4h/v1",startUTC,endUTC]
```

Here `contract` is the exact literal above. Validate the full represented timestamp precision before formatting: both endpoints must be timezone-aware, normalize to UTC, and must have zero minute, second and fractional components, including microseconds and nanoseconds. Each UTC hour must be one of 00/04/08/12/16/20. The end must be exactly 14,400 seconds after the start, preserving the existing half-open slot and complete aligned 240-minute witness. Never truncate a fractional timestamp, bridge a gap or change the calendar to make an endpoint qualify.

Serialize the six-string array as compact JSON using ASCII bytes, literal unescaped `/`, ordinary double-quote string delimiters and commas, with no spaces, BOM, leading/trailing whitespace or newline. Endpoints use exactly `YYYY-MM-DDTHH:mm:ssZ`, with four-digit year and zero-padded fields. The logical `observation_id` is the literal lowercase prefix `sha256:` followed by the 64 lowercase hexadecimal digits of SHA-256 over those exact bytes. The closed ASCII inputs make the serialization explicit; no locale or general-purpose Unicode canonicalization is involved.

Do not include close price, selected receipt ID, receipt order, scan time, readback time, availability, fixed expiry, rule/account identity or incidental equal witness selection in this slot identity. The contract version fixes the price-basis semantics. Original receipts, prices, clocks and their proof identities remain separate evidence. An identity hash does not authenticate that evidence or independently establish source eligibility.

### Documentation conformance vectors

These are offline encoding examples for already-documented slot boundaries, not new acquired or admitted observations. Both preimages have **125 ASCII bytes**, no final newline.

```json
["tiingo.fx.USDJPY.reported-close.utc4h.local/v1","USDJPY","4H","fx-utc-4h/v1","2026-10-22T08:00:00Z","2026-10-22T12:00:00Z"]
```

Result: `sha256:11bd014973059403cf8a8d8b6fa8b617ce1b9270979431398d5f1190de313e57`.

```json
["tiingo.fx.USDJPY.reported-close.utc4h.local/v1","USDJPY","4H","fx-utc-4h/v1","2026-10-22T12:00:00Z","2026-10-22T16:00:00Z"]
```

Result: `sha256:52df079d29892cec2ca624d44bf32ae4bfd5dd994ba8fc6adf26b5451887433e`.

## Local revision, equal witnesses and conflicts

Use JSON numeric `1`, consumed as a positive non-boolean Python built-in `int`, for the proposed local observation revision. String `"1"`, floating `1.0` and boolean `true` do not satisfy the current evaluator. This local revision is separate from the saved rule revision and Terminal condition version and is not a Tiingo vendor revision.

An equal reread retains the same logical ID and local revision 1. After **all** relevant closed vintages have qualified, the future projection supplies one logical observation per slot; equal proof receipts remain separately retained. The current evaluator refuses duplicate observation IDs and duplicate bar ends across the supplied window, so passing multiple equal receipts as separate bars is not an integration strategy.

A relevant conflicting closed vintage withholds the incumbent sequence. Do not discard the conflict during equal-witness grouping, choose the newest receipt to hide it, hash the changed price into a replacement identity, or mint local revision 2. No accepted replacement/correction policy is introduced. This remains a bounded local inventory assertion, not proof that no unobserved vendor correction exists.

## Incumbent integration and review limits

The unchanged `engine/forex_alerts.py::evaluate_price_condition` accepts caller-supplied identity and qualified convention fields; it does not recompute this proposed ID, verify the hashed start endpoint or adopt a feed. The source owner must qualify both endpoints and evidence before any future projection. Valid encoding cannot turn a research result into `status="final"`. Keep `CANDIDATE_NOT_ADOPTED`, empty eligibility and all admission flags unchanged.

Macro `evaluation_id` remains an evidence digest and may change with readback/availability metadata even when logical observation ID/revision remain stable. This observation specification does not define the complete Terminal delivery vintage. Its existing `(alert_id, condition_version, vintage)` boundary still needs the reviewed feed contract and ordered observation IDs/revisions, exact owned active rule/source eligibility, both expiries and atomic enqueue/idempotency qualification.

The original Forex review is `forex-r26-candidate-policy-review-20261022-sol-001`, under root `forex-r26-native-completion-20261020-sol-001`, controller 50810. Its retained first-attempt 429/rc1 result has no qualified verdict, accepted=false and retry_allowed=false; 690-byte response SHA-256 `aaa15c5bbc2e99cb34a07f8a8e6ef8cab50ff9a56a29e4ce0505d38225a26e31`. Preserve that operation without polling, replay, replacement or provider/carrier substitution. Terminal #1106's original repair-review and deployment refusal remain separate.

The two vector digests were calculated offline on source parent `227735dcf6a5c2358f898063914a87bef0c9c287`. Evaluator blob `aea6b913a9642a34b6cfb26657c0c970ee639ede` and candidate-reader blob `be4e99308aebbdac83677d9d12be8dd20e865901` remain unchanged. No provider/archive read, new runtime helper, observation store or prospective cohort was created. The actual October 22 observation expired at 20:00 UTC; specifying its slot encoding does not renew it.

---

## Retained earlier design and implementation checkpoints

# Existing-owner prospective USDJPY contract decisions — 22 October 2026

The accountable recovery owner records the following **design decisions for qualified source review and later existing-owner integration**. They do not adopt the current `/2` policy, admit observations, register a production feed or activate saved conditions. The successful 19:15 readback below is the actual bounded witness. No provider-support or licensing email is required.

| Boundary | Owner design decision | Evidence limit / release condition |
| --- | --- | --- |
| Pair and observable | USDJPY only, JPY per USD; Tiingo-reported native historical close, with minute completeness/consistency evidence. Draft contract name: `tiingo.fx.USDJPY.reported-close.utc4h.local/v1`, subject to incumbent naming review. | Never call it midpoint, executable price or a transaction close. Other pairs remain outside this proposed scope; preserve CNH and BRL evidence. |
| Numeric semantics | Use the existing reader's normalized representation and exact normalized comparisons. Add no rounding or tolerance. | No raw arbitrary-precision equivalence claim. |
| Interval and calendar | Reuse `4H` and `fx-utc-4h/v1`: half-open UTC slots, a complete aligned 240-minute witness, qualified lineage, post-end observations, native/minute agreement and relevant-vintage checks. Withhold gaps or conflicts; never skip/bridge a slot. | Local qualification after an interval is not vendor immutability. Two observed windows do not prove all holidays, sessions or ten-close live history. |
| Availability and freshness | Use actual current readback availability. Keep stable older support with its original expired individual state; require newest freshness before its fixed end plus four hours. | Never backdate availability or extend expiry on reread. The recorded 16:00 end expires at 20:00 UTC. |
| Inventory and corrections | Scope the contract to the existing bounded, observed local receipt inventory and actual two scans, exact binding verification and all relevant observed closed vintages. Preserve originals. A conflicting closed vintage withholds the sequence; no accepted replacement policy is proposed. | Non-atomic scans and incomplete global/vendor correction knowledge remain explicit. If an atomic/global guarantee is required, this contract is insufficient. |
| Logical identity and revision | Proposed logical identity binds the named contract, literal pair, interval/calendar and UTC start/end. Exclude scan/readback time, receipt order and incidental selected equal witness. Proposed local revision 1 means immutable local-observation semantics, not a vendor revision number. Keep proof receipt identities separately. | An equal reread cannot become a new bar. A conflict cannot silently become revision 2. Final identity naming/encoding requires existing source-owner review before operative use. |
| Account binding | Future binding must use the normal owned-account, expected-revision mutation and preserve the user's threshold, operator, count and condition expiry. Existing saved rows stay inactive with null feed. | No automatic upgrade or in-memory feed injection. Preserve completed inactive CRUD proof. |

## Concrete incumbent integration sequence

1. Keep `assess_forex_source_batch_candidate` and `read_forex_source_batch_candidate` research-only with unchanged empty eligibility and false admission flags. Their existing candidate projection already supplies pair, interval endpoints, current availability, fixed expiry, slot sequence and close; no additional handoff wrapper or parallel evaluator is needed merely to relabel it.
2. Obtain qualified source review through the existing owner and original operation constraints. The failed 429 return does not become qualified through this document or a native agent's advice. No replay, new review operation or provider substitution is authorized by these design decisions.
3. At actual adoption, bind the existing projection to the incumbent evaluator's `pair/feed/interval/calendar/quote_basis/bar_end/available_at/expires_at/bar_sequence/close/observation_id/revision` fields under the reviewed source contract. Preserve `engine/forex_alerts.py::evaluate_price_condition` and its checks.
4. Preserve stable delivery deduplication at the **existing Terminal** Alerts/outbox boundary. At Terminal `4f0e533a8ca6438470c51ef256f83b52a6302b05`, `mint_fire_event_id` uses `(alert_id, condition_version, vintage)`, not Macro `evaluation_id`. The future reviewed Forex vintage binding must preserve owned condition identity, exact rule revision, feed contract and ordered observation IDs/revisions across equal rereads. Macro's digest includes availability clocks and remains evidence; this is a forward integration requirement, not a demonstrated current Terminal dedupe defect.
5. Existing Terminal validation and `save_forex_watch`, Macro's `templates/forex_watch_client.js`, and **Terminal repository** `ingest/alerts_engine.py` must be integrated together. The inspected Terminal runner has no wired Forex dispatch branch; current storage/API/client validation deliberately requires null feed/inactive state. Preserve that accepted behavior. Future Forex enqueue must atomically qualify owned account, exact active rule revision, rule/source expiry, feed and source eligibility with the existing idempotency boundary; a later disarm PATCH is insufficient forward proof, not evidence of a current wired Forex activation bug.
6. Qualify the changed source, account/API, expiry/correction/deduplication behavior and genuine delivery path through existing owners before activation. Terminal #1106's original-only review HOLD and the prior deployment safety refusal remain separate gates. Migration 0038 is never reapplied.

The exact repository/operation map, field bindings and ten future qualification cases are in [the existing owner-integration handoff](OWNER_INTEGRATION.md#existing-owner-integration-handoff--source-audit-23-october-2026).

The remaining blockers are therefore concrete technical review and incumbent integration/proof boundaries, not an unanswered licensing request. This record provides reviewable decisions without inventing accepted authority or a new lifecycle, account, watch, evaluator, queue, retry or publication plane.

## Recorded actual observation and preserved implementation contract

# Actual version 2 USDJPY observation — 22 October 2026, 19:15 UTC

The existing observed-census reader completed a real marked-receipt readback on source `0a71e8cac5620593975b741abdf8d798900452fd`. Exactly two requests were called once after a bounded absence/effect preflight, using the existing collector, account and archive. The two original receipts were materialized once each. No historical receipt was upgraded.

The 08:00–12:00 supporting interval and 12:00–16:00 latest interval both passed batch support at the actual 19:15:19 UTC readback. Both observed scans contained the same 24 metadata entries; four exact USDJPY views were read, including the preserved old unmarked pair. All relevant selected receipt clock declarations qualified under version 2. See [the metadata-only actual execution receipt](evidence/usdjpy_v2_actual_readback_20261022.json).

The older interval's individual verification/assessment-expiry failures remain present. The latest interval's fixed expiry is **20:00 UTC**, and subsequent readbacks cannot extend it. Equal normalized prices and equal local scans establish only the recorded bounded comparisons. They do not prove all vendor corrections, an atomic/global inventory, producer execution attestation or earlier historical availability.

`batch_checks_satisfied=true` is now an actual observed research result. `CANDIDATE_NOT_ADOPTED`, empty eligible observations and every admission flag remain unchanged. Technical adoption requires the existing owners' explicit identity, observable, calendar, clock/concurrency, correction and account-binding decisions plus qualified review. Licensing/product use is COMPLETE by Chairman attestation; provider approval email is not a remaining step.

## Preserved implementation contract and earlier observations

# Current original-receipt clock contract and policy version 2 — 22 October 2026

The original receipt may declare `observation_clock_contract=local_utc_after_bounded_read_before_http_exit/v1`. The repaired `collect_one` supplies it with the local clock sampled after a successful bounded body read and before response-context teardown. Generic direct `store_response` calls remain unmarked unless they explicitly supply the recognized declaration and a received-at clock. An absent or bounded unknown declaration stays readable; strict policy does not qualify it.

The optional field participates in the original receipt's existing content identity. The exact reader derives `TiingoView.source_observation_clock_contract` only from the validated original receipt context, never the normalized manifest. Materialized schemas and historical archive bytes are unchanged. Reuse returns the original first receipt's marker or absence; a newly requested declaration cannot upgrade it. Unmarked metadata retains its historical shape and batch fingerprint.

| Boundary | Current default | Explicit historical selection |
| --- | --- | --- |
| Single candidate | CURRENT_CANDIDATE_POLICY_VERSION, tiingo-forex-local-close-candidate/2 | CANDIDATE_POLICY_VERSION, /1 |
| Batch candidate | CURRENT_BATCH_CANDIDATE_POLICY_VERSION, tiingo-forex-local-close-batch-candidate/2 | BATCH_CANDIDATE_POLICY_VERSION, /1 |
| Observed census | Current batch /2 when omitted | Explicit batch /1 |

A shared parser rejects unknown or cross-family versions. Actual selected versions are recorded. Version2 assessments use their version 2 schemas; the existing census envelope records its selected policy. Version1 preserves the earlier timestamp-only research behavior. The unchanged diagnostic/reconciliation prefix ends at line 455 and is bound by the qualification receipt; the version dispatch lies after that boundary.

For each target slot, version 2 requires recognized declarations from the selected minute/native receipts and every relevant supplied competitor. Relevance follows the vendor interval position without trusting an unknown observation clock. Unplaceable evidence remains relevant; provably unrelated windows remain visible without vetoing a different slot. The single assessor's existing minute-inventory limitation remains explicit; the batch owner provides competing minute vintages. No unknown competitor is silently removed to make the result pass.

Numeric post-close timing is independent: a recognized declaration does not turn a pre-close response into a closed one. The declaration is integrity-bound producer metadata, **not authenticated producer execution, vendor publication, wire arrival, finality, exhaustive corrections or historical availability**. Version2 reports producer_declaration_only=true and producer_execution_independently_attested=false.

Actual qualification: 9 new failures / 8 controls before source changes; 524 affected tests passed after the change, including real temporary archive→materializer→bounded reader→single/batch/census. See [the exact qualification](evidence/clock_contract_qualification_20261022.json). Tests made no provider call or real archive mutation. All admission flags remain false, eligible observations remain empty, and the policy remains CANDIDATE_NOT_ADOPTED. Licensing/intended use stays Chairman-COMPLETE.

## Historical response-sampling, count, census and version 1 contracts

# Current response-observation contract — 22 October 2026

The existing `collect_one` acquisition route uses the private `_fetch_json_observation` helper. A successful bounded read and size check precede a local UTC sample; that sample precedes response-context teardown and storage. A newly created receipt therefore does not use storage delay as its observation clock. Oversized bodies are rejected before sampling. Transport/HTTP/teardown failures retain safe error translation and cannot reach storage.

This is a local read-completion sample, not wire-exact arrival, vendor publication, bounded scheduling delay, finality or correction immutability. The public `fetch_json_bytes` signature and ordinary `(raw, content_type)` result remain unchanged. BOATS history routes keep their existing independent storage-clock semantics.

`Archive.store_response` is unchanged. Identical same-request/same-day content reuses its original receipt identity, clock and bytes. No historical receipt is rewritten or upgraded. The current receipt schema alone cannot distinguish the producer timing basis; strict prospective candidate qualification needs actual acquisition provenance. The accepted post-boundary operation chronology remains valid on its own retained capture record.

Actual regression qualification: **3 failed / 4 passed** on original collector blob `631dbfa4d6545ff55aabf56fe17366924fa2d2a8`, then **507 passed** across seven affected suites on repaired collector blob `d3f5f822a794763fac5842a90763193d8e2176b7`. The source-to-candidate test uses the actual temporary archive, materializer, exact bounded reader and unchanged assessor. With a pre-close minute read and post-close storage, grid/OHLC checks pass while the post-close response check fails and candidate eligibility remains empty.

See [response-clock qualification](evidence/response_clock_qualification_20261022.json). The 355-pass count-bound repair, original green 3db8846 CI and real retained census remain evidence on their original identities. Source admission, active monitoring and account/evaluator authority are unchanged.

## Retained batch and count contracts

# Forex R26 — bounded batch candidate contract

## Strict Parquet count qualification — 22 October 2026

This descendant of `2743fb06245d18edcbeb3f00be08b24164a348e3` closes a malformed-input row-limit gap in the opt-in bounded reader. With `read_context` present, `max_rows` must be an actual integer before archive access. File and row-group counts must be nonnegative integers; cumulative group rows must stay within the allowance and equal the file count before decode. The decoded table count must then equal that validated total and remain within the allowance before `to_pylist()`. Census independently checks returned rows against `min(per-type limit, remaining total)` before recording them.

The legacy `read_context=None` decode branch remains unchanged. Production imports, the existing materializer source and the pure Forex assessor prefix are unchanged. No reader/census change grants source, monitoring or account admission. Encoded-byte and row-count guards do not establish a decoder-memory, CPU or process-RSS bound.

The 27 new regression cases use the existing temporary retained fixtures and controlled parser counts. On unchanged production source, 24 refusal cases failed and three controls passed. After repair, the four incumbent source suites passed all 355 tests in 10.08s at 13:24:54 UTC. Refusals are checked before decode, before Python conversion and before census accounting/assessment. This is source qualification, not accepted independent review or an actual malformed-footer exploit claim. See [strict count qualification](evidence/strict_parquet_count_qualification_20261022.json).

The earlier 328-pass census run, separate closure pass and 12:23:40 real retained-archive readback remain accepted for their recorded source. No archive readback was repeated to refresh its clock. Its required 08:00/12:00 support remains absent; eligibility and monitoring remain false.

## Retained observed-census contract and qualification

## Observed exact-reader census — implemented and qualified on 22 October 2026

Entry: read_forex_source_batch_candidate(expected_pair, consecutive, policy_version, root, check_mount). Evidence schema: mastermind.tiingo.forex_batch_observed_census.v1. It calls the unchanged pure assessor only after successful bounded acquisition. Existing reader/materializer behavior with read_context=None is preserved.

The existing materializer owner now exposes BoundedTiingoRead. It opens the original absolute lexical root and components with directory descriptors and no symlink following, then applies the incumbent mount policy. All later directory/leaf access is descriptor-relative, regular-file and same-device checked. Strict JSON refuses duplicate keys/nonfinite values/non-object metadata. Exact Parquet verification and parsing use the same byte snapshot; no subsequent pathname reopen supplies the parser. Gzip uses bounded decoded read1 calls. Before/after file identity and final named-binding observations detect the covered replacement cases; they create no lock or transaction.

| Acquisition boundary | Contract |
| --- | --- |
| Capture-date scope | Real start clock fixes the current UTC4H end. Scan earliest required end's date through the current UTC date; at most3 capture dates for consecutive1–10. Request market dates do not prune late-captured corrections. |
| Entries | Count every directory entry before filtering/deduplication; maximum256 per scan. Unexpected temporary names, special files and invalid receipt metadata refuse instead of disappearing from the census. Validate every observed entry before excluding another literal pair/frequency. |
| Metadata bytes | At most16MiB aggregate and1,000,000 bytes per metadata file. |
| Other evidence bytes | Separate64MiB budgets for decoded raw, compressed raw and encoded normalized input. At most one refusal sentinel is charged beyond a limit. These are not process-memory, CPU or decoded-Parquet-allocation bounds. |
| Selected views | All observed literal-pair1min/4hour receipts; maximum9 per frequency before deduplication. Exact receipt path and identity, never a glob fallback. At most20,000 minute rows,128 native rows,100,000 selected row references total. |
| Unavailable materialization | A raw-only/missing normalized view stays explicitly unavailable. No materializer is run and empty_payload_proven stays false. |
| Concurrent publication | A second observed scan includes full paths and metadata identity fingerprints; actual final binding, verification and assessment clocks follow. Changed observations or a4H boundary crossing withhold. No automatic rescan or older-sequence fallback. |

Every scan's entry dispositions and original response clocks are retained. Equal scans cannot exclude a transient change between scans, later publication, out-of-scope evidence or an omitted vendor correction. Final binding checks do not reread every byte. atomic_census_proven, global_inventory_completeness_proven, owner_quiescence_independently_verified and historical_availability_proven remain false.

### Executed qualification and actual outcome

The four source suites passed328 tests in9.11s (9.778s command wall time), completed12:21:12UTC. The separate existing-owner closure check passed1 test in146.34s, completed12:28:07UTC. Source stayed unchanged through both runs and the actual acquisition. The pure batch-assessor parent prefix is byte-identical. These tests qualify the implementation boundary; they are not accepted independent source review.

The single actual retained-archive acquisition began12:23:40.208249UTC and completed12:23:40.457022UTC. Both scans observed22 entries for capture date2026-10-22. One1min receipt supplied1438rows and one4hour receipt supplied6rows. Actual verification was12:23:40.287017UTC; assessment12:23:40.287033UTC. Required ends08:00 and12:00 were unsupported. State observed_census_complete_policy_unadopted describes acquisition completion; batch checks remained false, eligible observations empty and monitoring false. This does not establish that Tiingo lacks current data elsewhere.

Actual evidence-byte counters: metadata45,490; decoded raw167,152; compressed16,872; normalized37,365. No provider call, capture, materializer invocation or archive mutation occurred. Compact receipts preserve all22 metadata dispositions per scan and exact identities without licensed price rows.

See evidence/observed_census_qualification_20261022.json and evidence/observed_census_readback_20261022.json. The original failed Fabric review remains unqualified; it was not replayed. Licensing/intended product use is COMPLETE by Chairman attestation. Source adoption, genuine current-slot support and revision-safe downstream admission remain separate existing-owner gates.

## Retained pure-assessment contract and earlier qualification

Policy: tiingo-forex-local-close-batch-candidate/1
Result schema: mastermind.tiingo.forex_source_batch_candidate.v1
Inventory declaration: mastermind.tiingo.forex_batch_inventory_evidence.v1

The existing lib/dataos/tiingo_forex.py now contains assess_forex_source_batch_candidate. This is a pure research assessment over exact reader views. The unchanged individual helper remains the authority for each supplied minute/native reconciliation. No candidate result admits source observations, an account binding, historical availability or monitoring.

## Input and resource boundary

Call with ordered view/receipt pairs in minute_vintages and four_hour_vintages, an existing literal expected_pair, integer consecutive1–10, exact policy_version and explicit verified_at_utc <= assessed_at_utc. Optional inventory_evidence validates only a caller's declaration.

| Bound | Behavior |
| --- | --- |
| Minute/native references | At most9 each, counted before deduplication. |
| Rows | At most100,000 supplied row references overall; existing20,000-per-view diagnostic limit and128-per-native-view limit remain. |
| Identity representation | All declared TiingoView fields, original row order and type-sensitive values; depth16,10million nodes and64MiB serialized identity budget. |
| Inventory | At most256 unique exact receipt IDs per declared list; exactly two ordered scan declarations. |
| Selected comparisons | At most one deterministic minute/native pair per required slot, ten cached pairs maximum; no retained Cartesian product. |

Unsupported types, invalid clock ranges, over-budget input, conflicting identity representations, diagnostic lineage failures or mismatched request frequency raise the existing TiingoViewRefusal. Nothing is truncated to manufacture a result.

## Identity, lineage and correction semantics

The receipt map is built before slot filtering. A repeated exact receipt/content is deduplicated and disclosed. The same receipt with a different field, request context, value type, row order or non-OHLC content is refused. Distinct receipts are never merged merely because their values agree.

Every view passes the incumbent diagnostic, including row-level source identity, raw digest, original observation clock and admission flags. These lineage checks apply outside the selected slots too. The pure assessor cannot authenticate a raw digest against disk; the exact reader remains responsible for that.

For each required half-open UTC slot, one exact closed minute view must supply all240 aligned unique minutes. Partial views are compared but never stitched together. Every supplied closed minute vintage is compared at all present overlapping minutes across normalized O/H/L/C. Aggregate agreement cannot conceal offsetting minute corrections. An unplaceable timestamp cannot be excluded and withholds the comparison; a provably out-of-slot value problem does not poison that unrelated slot. Duplicate normalized instants, subminute labels and malformed in-slot values withhold. Open receipts are disclosed separately and never classified as closed corrections.

All supplied native vintages participate in the unchanged native consistency check. The deterministic chosen reference is a computational choice after competing evidence checks, never a correction-selection policy.

## Exact sequence and clocks

The latest required end is the UTC four-hour boundary derived from the actual assessed_at_utc. The preceding consecutive−1 ends are adjacent. A verification/assessment boundary crossing requires the newly ended slot; the assessor never falls back to the previous sequence.

Older slots use the seven stable individual checks plus minute-vintage consistency. Their original individual expiry failure remains in candidate_assessment. Only the latest slot additionally requires verification and assessment before its fixed expiry. candidate_available_at_utc is the caller's actual current readback completion; this describes current-decision support and does not manufacture earlier knowability.

Re-reading never extends the newest observation's fixed expiry. Equal normalized OHLC is not a proof of raw arbitrary precision, vendor immutability, global correction completeness or source adoption.

## Inventory declaration boundary

selected_receipt_ids must exactly match the supplied unique views by1min/4hour frequency. Each selected receipt must appear in both declared scans. Scan clocks must be ordered, complete before verification and no earlier than selected response observation clocks. The optional owner_quiescence_reference is a bounded reference string and never a boolean grant.

Missing declaration reports selection consistency and two-scan equality as unknown. Equal declared sets report their equality only. atomic_census_proven, global_inventory_completeness_proven and owner_quiescence_independently_verified remain false. Changed scan sets withhold batch checks. The pure function cannot detect a receipt omitted from both the declaration and input views.

The observed exact-reader census above implements these acquisition boundaries; it still makes no wider completeness claim.

## Authority

Every return preserves CANDIDATE_NOT_ADOPTED / RESEARCH_ONLY_VENDOR_SOURCE, eligible_observations=[], monitoring_admitted=false, dataos_identity_admitted=false, pit_backtest_eligible=false and redistribution_admitted=false. No I/O, capture, storage, account mutation, event, schedule, delivery or publication occurs in the function.

Tiingo licensing/intended R26 product use is COMPLETE by Chairman attestation. Technical source adoption, actual readback clock, inventory concurrency, normalized precision, calendar scope, observation revision and saved-rule feed binding remain existing-owner contracts.

## Qualification and actual retained result

Source SHA256ab5153b812d57a1d672bd4062595b14e68e002e68ad6b13f5e7b45f4bef8b656; testsSHA2560c4e6ce7ba22b94cfe15b1aa8232d1249aa93e4cfbea70e14a1ff6f07fe6153a. The parent source prefix SHA256f3e3849f91bc677a3de641f1affee292549f39902a97668a0ddddaf978647afa is unchanged.

The initial run passed168 cases and failed one fixture before reaching the pure API because the real reader correctly refused its malformed timestamp. After correcting only that fixture, its targeted case passed. Reuse the168 unaffected passes; qualified union169 is not described as a single all-green run. The retained source and corrected test hashes bind the results.

The actual retained-only readback at2026-10-22T10:32:17.692333+00:00, assessed13microseconds later, required04:00/08:00 ends. The older slot supported history with its individual freshness still false. The newest lacked a complete closed minute witness. Batchfalse, zero eligible observations, no admission, inventoryunknown and atomicfalse are the observed result. No provider request, capture, materializer call or archive mutation occurred.

See evidence/batch_candidate_qualification_20261022.json and evidence/batch_retained_readback_20261022.json for compact non-price receipts. Full licensed rows and private assessment remain in the existing local proof directory. Source review is still unqualified after the original terminal429 return; CI/source tests do not clear it.
