# Independent integration review

**Disposition: the three-join architecture is useful, but the prototype is blocked for end-to-end implementation as written.** The independent review reproduced seven contract gaps, including a real temporary-Parquet rewrite that silently loses retained event history. The original 63-check laboratory result remains a valid record of the cases it exercised; it does not establish the stronger completeness, immutable-first-observation, and price-provenance claims against these counterexamples.

Reviewed input: `INTEGRATION_MANIFEST.json` SHA256 `d755a012d80469c241a554252e61bee88e604eb445ce7ca03ec1e2eecfdbc8b6`, study source `3d90aad6d83152dfeeaf8345bc995826ac9d3139`. The completed integration and vintage laboratories, and the earlier reviews, were not changed.

## What remains accepted

The source architecture correctly separates three authorities: the prior-session armed generation supplies event thresholds and frozen fields; the same-session settlement pack supplies its technical gate verdict; the same-session canonical board supplies the membership comparison. The independent baseline reproduces all four retained ledger rows exactly using the unchanged proposal and the native pinned functions. Replaying the complete fixture is idempotent, and the prior armed generation still resolves after the current-pack key rolls to settlement.

Those positive results narrow the repair: retain the existing owner, writer, daily key and three joins, then strengthen their validation boundaries. These findings do not justify a second ledger or another runtime owner.

## Confirmed findings

| ID | Priority | Counterexample and actual result | Required correction |
|---|---|---|---|
| F4 | High: retained history | A **readable five-row Parquet** contains a duplicate daily key whose later row retains one additional event ID. The unchanged `reconcile_file` and native atomic writer accept it and write **four rows**, dropping that ID. Reversing the duplicate order instead produces `spool_regression`. | Validate existing-key uniqueness and row integrity before native merge or any write. Refuse conflicting duplicates while preserving original bytes. |
| F3 | High: false provenance | Quotes with missing adjustment metadata, explicit `split_and_dividend_adjusted`, or explicit `unadjusted_vendor_print` all produce the **same three raw-labeled event IDs**, and all three rows pass into the ledger. | Require a validated adapter/provider basis declaration, preserve it, and include its evidence in event identity. Missing or incompatible basis remains unavailable or refused. |
| F1 | High: evidence completeness | Removing the first transition object removes evidence for three consumed keys, yet reconciliation succeeds. Removing **all transition objects**, leaving two close snapshots, returns all four old rows with `distinct_events=0` and no regression refusal. | Check all previously consumed event IDs and keys for the requested session against the complete resolved spool before iterating newly reconstructed rows. |
| F2 | High: membership authority | Two close snapshots share the same session, generation and `built_at`, but disagree on one member. Changing only an irrelevant envelope nonce changes digest sort order and selects either **two confirmed / zero dropped** or **two confirmed / one dropped**. | Detect conflicting close evidence at equal authority. Record the selected close object identity, or leave the membership comparison unresolved pending an explicit supersession rule. |
| F7 | High: immutable observation | An existing row keeps its original `first_event_id` but has `first_px=47.1029`; the resolved event contains `price=46.1029`. Replay succeeds and returns **47.1029**. | Validate the denormalized immutable first-observation fields against the resolved event and pack, or bind a canonical first-observation record digest. Refuse conflicts. |
| F5 | Medium: validator parity | Correctly rehashed archived packs with frozen scores **−1** and **100.01** both pass standalone `validate_pack`. The board loader enforces 0–100. | Enforce the same score domain at the standalone archived-pack boundary. A matching content hash does not establish semantic validity. |
| F6 | Medium: failure channel | `finite(10**400, positive=True)` raises `OverflowError`. The same single bad quote escapes `evaluate_checked`'s `Refused` handler and aborts the entire pass. | Make numeric validation total over JSON values and reject out-of-domain magnitude through the intended typed/per-name refusal path. |

### F4 — readable storage can still lose evidence

This is a file-backed counterexample, not an inferred behavior or a mocked writer. The input is valid Parquet with five readable rows. One existing `(2026-10-12, 002460.SZ, forming)` key appears twice. The second copy contains an additional synthetic previously retained event ID and an updated occurrence count/time. The additional identity is deliberately absent from the current spool; the claimed regression contract should stop the write.

The proposal finds the **first** existing row matching the incoming daily key and validates only that row. Native `merge_rows` subsequently combines all existing rows by the daily key, then lets non-`FIRST_WINS` incoming fields overwrite the merged fields. The incoming `event_ids` therefore replaces the union that included the additional old identity. One native `_write_parquet` call commits four rows. Moving the conflicting duplicate to the front changes the outcome to refusal, demonstrating that input row order controls whether the evidence loss is detected.

Actual file hashes are retained:

- Before, five rows: `e27b40119ca438c71d81fe89e5cd2cf5f87451cb454b7febc9dbe6435d33ebbd`.
- After, four rows: `1acd93e4934ecf0ad50849e279c38a4c3b6ece0a795f33941b6a006cedea1351`.

The correction must run before merging **all existing rows**, not merely before writing a newly produced row. Exact duplicate normalization, if desired, needs its own explicit equivalence rule; conflicting rows cannot be silently collapsed. An unreadability guard alone cannot establish history preservation.

### F3 — numeric alignment does not supply adjustment provenance

`evaluate_checked` assigns `price_adjustment="unadjusted_vendor_print"` after native evaluation without reading or validating the source quote's adjustment declaration. The consumer then requires that exact string. This enforces a vocabulary that the producer itself supplies unconditionally, so the downstream check cannot detect the upstream provenance loss.

The native evaluator runs in the counterexample. Quote clocks, numeric prices and previous closes stay fixed; only the declared adjustment differs. Each variant emits the same three event IDs and reaches the same three raw-labeled ledger rows with no quote rejection. `price_basis="regular"` is kept constant because that field describes the regular/day quote vocabulary; it does not independently certify corporate-action adjustment.

An implementation may obtain a valid declaration from a checked adapter or quote batch rather than duplicating it in every row. Whichever boundary owns it must be explicit, validated, retained and distinguishable in event identity. A previous-close numerical match cannot certify that the quote is an original unadjusted vendor print. The experiment establishes a false-provenance path in the proposal; it does not establish that a natural vendor quote took that path.

### F1 — a missing entire key never reaches the regression check

The existing `spool_regression` predicate is useful when a daily key is reconstructed and its old event-ID set is not a subset of the new one. Its placement inside the new-row loop leaves an entire missing key unchecked. The independent positive control confirms that the predicate rejects an extra old identity when the key remains present. The whole-object omission variants then prove the blind spot.

The omitted objects are deleted from the synthetic store; remaining objects retain their original content, keys and valid hashes. No malformed payload or failed pagination is needed. The ledger rows themselves remain present in this case, so this finding is **undetected loss of supporting spool evidence**, not a claim that the omission variant deletes ledger rows.

Validate the union of consumed identities for the targeted session against all resolved spool identities before constructing incoming rows. Any allowed archival expiry, correction or historical replay exemption needs a separate recorded disposition. Empty event evidence with close snapshots present cannot silently count as a complete replay of a session known to have consumed events.

### F2 — digest order is not a close-observation precedence rule

`list_complete` sorts object keys; the consumer appends close snapshots in that order; `max(closes, key=lambda item: item[0])` resolves equal timestamps by taking the first. Content-addressed keys protect object identity but provide no semantic authority between two conflicting observations.

Both variants use the same two close bodies, the same source pack and the same `2026-10-12T07:06:00Z` timestamp. One close includes `603799.SS`; the other does not. Only an inert top-level nonce on the second envelope changes. That changes which key sorts first and consequently whether the native membership receipt reports the name dropped. Both calls return successfully.

The compact same-session canonical document in this case is explicitly synthetic. Its exact hash is bound into a new synthetic settlement pack, so the test satisfies the intended canonical/settlement generation join. The observed difference comes from the close tie, not a deliberately mismatched canonical hash.

Equivalent duplicate close evidence may be coalesced. Conflicting evidence at the same authority must be refused or labeled unresolved unless a real producer sequence or supersession relation resolves it. Adding an arbitrary digest tie-break would make the choice deterministic while leaving its authority unsupported.

### F7 — identity equality does not validate copied fields

The proposal checks selected first-observation identity fields, including `first_event_id`, but omits `first_px`. The native merger's `FIRST_WINS` policy then preserves the old non-null price even though the resolved first event disagrees. This creates a ledger row whose quoted first-event identity and copied observation contradict each other.

The test changes one existing field by +1.0 while leaving the event ID intact. It does not ask the merger to overwrite the historical value. The correct response is a conflict requiring explicit adjudication, preserving both evidence versions. Silently retaining the contradiction and silently healing it are both inadequate for the proposed immutable-observation contract.

Review the complete immutable field set as one record: source and pack identity, event identity, event/quote time, price and adjustment declaration, entry class, basis anchor, and frozen values. Define canonical null/type normalization before comparison so Parquet representation changes do not become false revisions.

## Minimal next implementation requirements

The blockers can be addressed within the proposed existing-owner design:

1. Before any merge, validate the existing ledger's key/schema integrity and uniqueness. Compare every known event identity for the session with the resolved evidence set, including keys absent from new rows.
2. Resolve close evidence through a stated observation identity and precedence contract. Preserve source object IDs in the membership receipt and expose equal-authority conflicts.
3. Move adjustment provenance to an explicit checked producer boundary. Preserve its source declaration through event identity and ledger projection; retain unavailable states.
4. Validate immutable first-observation contents against their event/pack evidence. Keep contradictory historical rows and current evidence available for an explicit correction process; no silent overwrite or silent acceptance.
5. Apply total numeric-domain validation at every standalone trust boundary, including the frozen score range and extremely large JSON integers.

These are concrete acceptance conditions. Re-run the existing 63 checks and these counterexamples after the repair. The old positive fixture must still reproduce, while F1/F2/F3/F4/F7 must take an explicit refusal or unavailable path and the numeric cases must fail through their intended channels before any write.

## Execution, reproducibility and limits

`review_integration.py` executes the unchanged proposal and nine native modules loaded from `native_source_bundle.json`. That bundle was obtained through bounded, read-only `git show` calls at the study pin; each byte hash matches the completed laboratory's source manifest. Native reconciliation, CN clock/calendar, state evaluation, interval checking and event logic are executed rather than replaced with mocks. The object transport is the deliberately synthetic in-memory store.

The chat runtime has pandas 2.2.3 but no installed Parquet engine. The actual file-backed proof therefore ran through `parquet_counterexample.py` in the existing host runtime, Python 3.14.7 / pandas 3.0.5, using the original isolated source export after checking its hashes. Its only writes were under a new `/tmp/mmx-cn-integration-review-20261010-r0xd07ip` directory. The source checkout and original laboratory paths were read-only. `parquet_review_receipt.json` and both binary files are retained; the main review verifies their exact hashes and labels that proof as a separate host execution. It does not pretend to have run the native Parquet writer in the chat runtime.

The main terminal run completes **56 checks and seven confirmed findings**. Run:

```bash
python review_integration.py
```

With an installed Parquet engine, it re-executes the native file path directly. Without one, it verifies the separately executed receipt, exact helper code, subject/native/fixture hashes and binary artifacts. The companion helper's command-line arguments reproduce its bounded host proof against an isolated pinned export and the retained original fixture. The package manifest binds all delivered files.

All bad inputs and the October 12 session are explicitly synthetic research cases. There is no claim of natural production corruption, an actual executed trade, an observed future-session quote, or realized economic loss. These counterexamples establish reachable behavior under the claimed validation contract. A natural scheduled roundtrip, real object-store completeness and retention, source publication receipts, lawful fills, aligned price bases, and future performance evidence remain separate production/research obligations.
