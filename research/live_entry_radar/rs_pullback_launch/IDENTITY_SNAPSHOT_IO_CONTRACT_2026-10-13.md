# Entry Radar identity snapshot I/O — R12

Status: candidate consumer adapter, not a publisher, source admission or trading rule.

## Outcome and existing owners

`engine.entry_radar.replay.identity_observation_snapshot.read_identity_snapshot(directory)` reads one complete existing Data OS reference generation and returns an immutable `IdentitySnapshotRead` containing the existing `ReferenceSnapshot` and `ReferenceReadReceipt`. `alias_table()` constructs the existing `VendorAliasTable` over that exact validated snapshot. A successful read does not enroll a consumer automatically: the caller must explicitly supply the returned receipt to native lookup at its actual decision cutoff.

The identity module remains the only identity validator/selector. `scripts/build_security_master.py` remains the publication owner. This change writes no reference artifact, alias, generation, historical receipt or operational state. It starts no collector and changes no market data, user ranking, alert, sizing, rights or execution policy. The already-adopted #8637 reader and the raw-minute reader are reused, not replaced.

## Exact file and clock contract

The trusted local caller supplies an absolute directory, not a URL. One directory descriptor anchors all file opens. Root and final-component file symlinks are refused. Ancestor-directory trust remains with the configured root owner; this is not an arbitrary-user filesystem sandbox. The fixed names are `_receipt.json` and the identity owner's existing five artifacts: security master, vendor aliases, issuer master, issuer migrations, security migrations. No missing-member fallback or best-effort subset exists.

Read order is receipt A, the five artifacts in native contract order, receipt B. Each file must be a regular file and is bounded before and during reading. The receipt limit is 9 MiB; each artifact is at most 64 MiB. Metadata before/after an individual read must be unchanged. Receipt A/B equality and exact artifact/semantic hashes are verified by native `validate_reference_snapshot`.

Only aliases and security master require semantic Parquet decoding here. Their input is the captured bytes, never another pathname read. Parquet metadata/row/column/decompressed-size guards precede batch decoding; nested and binary field types are unsupported rather than silently projected. These guards are defense in depth for the trusted local publisher format, not proof of bounded memory against every malicious Arrow/Parquet implementation behavior.

Date-valued storage is represented by ISO dates. Timestamp storage for `valid_from`/`valid_to` must be timezone-free or UTC and exactly midnight; nonmidnight values refuse instead of truncating. Nanosecond timestamp storage remains nanosecond precise. A timestamp-typed `known_at` without a timezone refuses; an ordinary string is retained as written and checked by the native identity grammar. Nulls remain null. The producer's declared semantic seal must match this decoded representation; no adapter-created seal replaces a mismatching publisher seal.

The API has no supplied clock, cutoff or mtime override. It samples the actual system clock before file access and again after successful parsing/validation. This conservative completion time is the first availability asserted by this adapter. A reversed/invalid clock or completion before the sealed owner's observation refuses. The returned receipt uses the existing `mastermind.identity_read_receipt.v1` fields and hashes. It is a consistency record, not a signature or an independent source-authorization grant.

## Missing or legacy publication

A directory with five readable Parquets but no `publication` and `identity_observations` context is rejected by the native validator. The adapter must not synthesize those objects, drop the ETF refusals, use timeless store/Yahoo aliases, or reinterpret an old generation date as its own read time. Older and newer snapshots can be passed to the native history selector with their separate genuine read receipts; newer receipt-only refusals remain visible and must not erase older views.

## Implementation and verification plan

1. Add native Parquet/file boundary tests using the existing identity test fixtures. Demonstrate missing reader behavior before implementation.
2. Implement only the I/O/normalization boundary and existing receipt construction. Keep identity/publisher source unchanged.
3. Verify real-byte/semantic seals, complete/torn/missing/oversize/nonregular inputs, explicit timestamps, exact one-nanosecond visibility, and later refusal/older view behavior.
4. Run the unchanged native identity tests, new adapter cases, byte-preservation checks and a real read-only current-source refusal. Synthetic positive tests do not qualify the real data.
5. Register the exact tests/dependency paths in ordinary CI, publish a draft candidate, and retain exact source/test results on the existing RS Pullback workstream.

## Documentation consulted

Apache Arrow `ParquetFile` documents BufferReader input, bounded metadata options and batch reads. `TimestampScalar` documents the pandas-dependent nanosecond conversion of `as_py`; timestamp conversion here must not rely on a microsecond-only datetime fallback. These implementation references do not validate market-history completeness, corporate actions or identity truth.
