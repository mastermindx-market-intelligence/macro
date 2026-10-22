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
