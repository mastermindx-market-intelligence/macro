# Identity observation reader contract — 2026-10-07

Status: pure reader candidate; versioned publication and consumer activation are disabled. This contract extends lib/dataos/identity.py only. No source acquisition, writer, data generation, registry change, issuer-history implementation or authority is included. Base is macro@3781c8c7c4f80007d8d74231e83ec4fbca82e29c. The accepted owner design is SHA-256 c5de4a17494fb60859e6b2ba0591826eeb86b30e02a2776d664d2082b28bab0d.

## Ownership and API

VendorAliasTable remains the only alias selector. AliasRow and the old no-history constructor/from_records/resolve/vendor_symbol_for retain legacy and polygon-v1 evidence-only behavior. IssuerMaster and every other identity family remain unchanged.

The new history mode is explicit:
- VendorAliasTable.from_records(records, *, observation_history=None, original_reference=None, snapshot_contexts=()).
- resolve_binding(vendor, vendor_symbol, on, *, decision_at, snapshot_receipts=()) returns AliasResolution.
- symbol_binding_for(vendor, security_id, on, *, decision_at, snapshot_receipts=()) is the inverse over the identical selected view.
- In history mode, resolve/vendor_symbol_for additionally accept snapshot_receipts and delegate to that view, returning a string only for BOUND, otherwise None. Integrity/schema violations raise IdentityError; a genuine stored family REFUSED is not a parser error.
- VendorAliasTable.legacy_only_records(records) returns copied records excluding polygon/listing. It rejects revision metadata on any legacy namespace; it never strips revision metadata to make a clocked row legacy.
- In history mode rows raises IdentityError: a physical history is not an eligible view and cannot be reconstructed through legacy five-field iteration. Original no-history rows behavior is unchanged.
- validate_reference_snapshot(receipt_before, artifact_bytes, receipt_after, *, alias_records, master_records) returns immutable ReferenceSnapshot context. It performs no I/O or Parquet decoding and creates no read clock.
- ReferenceReadReceipt.from_record(mapping) accepts an externally recorded read; no constructor samples time.

History is optional solely for backward compatibility. Any record carrying non-null attempt_id/alias_family_id/alias_revision_id requires history. listing is never legal as an ungated AliasRow. Both clocked query namespaces require an explicit aware decision even for an empty table or unknown symbol. Structured clocked lookup without a history context is UNAVAILABLE, never candidate custody from a v1 evidence-only row.

AliasResolution is frozen and contains status (BOUND/REFUSED/UNAVAILABLE), vendor, nullable vendor_symbol/security_id, nullable attempt_id/alias_revision_id/known_at_utc_ns/receipt_sha256, and nullable reason. Only BOUND exposes an identity answer. No result grants trading or panel authority.

## Primitive and bound grammar

All new serialized values are JSON primitives. Objects have exact string keys; required schema objects reject missing/extra fields. Identity strings use exact str, never bool/int conversion. Token IDs are 1–80 ASCII alphanumeric/dot/underscore/colon/hyphen characters starting alphanumeric; revision IDs are the exact concatenation attempt_id + "/" + family_id. Family IDs are bounded strings. Digests are exactly 64 lowercase hex characters; code_version/source_commit exactly 40 lowercase hex. Positive integers reject bool. New nanosecond fields are canonical positive decimal strings with no sign/whitespace/leading zero, at most 19 digits and <= 2^63-1. Original v1 integer clocks remain original integers.

All payloads are bounded before canonical encoding: depth <= 16, <= 100,000 nodes, each string <= 262,144 UTF-8 bytes. JSON numbers must be finite and integers within signed 64-bit range. Duplicate JSON keys, non-JSON Python objects, invalid UTF-8 and nonfinite JSON constants refuse. A history is <= 8 MiB canonical UTF-8; each attempt <= 1 MiB; <= 64 new attempts; <= 4 families per envelope and exactly four for a visible NATIVE_REFERENCE payload or exactly two for SAME_VENUE_RENAME. A complete receipt is <= 9 MiB. Each supplied artifact is <= 64 MiB and each semantic record list <= 100,000 rows; this reader does not allocate/read files itself. Reaching any bound refuses; no truncation or history compaction.

Canonical JSON is json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False). SHA-256 hashes these UTF-8 bytes. A semantic record-set seal hashes the list sorted by each record's canonical JSON bytes; duplicate rows refuse. Hashes are consistency seals, not signatures. Explicit null is mandatory where specified.

Dates are exact YYYY-MM-DD strings parsed as dates, not datetimes. New stored known_at is canonical UTC ISO with nine fractional digits and Z, equal to the attempt owner-read ns. decision_at accepts an aware datetime or the existing explicit ISO T/date/time, optional 1–9 fractional digits, Z or colon offset grammar. The new selector compares exact integer ns (datetime inputs carry microsecond precision); it does not truncate evidence, invent tie-break clocks or round decisions upward. on must be an actual date, not datetime, and may not be later than the cutoff's UTC date.

## Original anchor and history

History exact fields: schema="mastermind.identity_observations.v1", anchor, attempts.

Anchor exact fields:
schema="mastermind.identity_anchor.v1";
anchor_id="anchor:" + original_reference_sha256;
original_reference_sha256;
original_alias_rows_sha256 (all unchanged non-revision alias records, including legacy and v1 polygon);
owner_read_completed_at_utc_ns;
anchor_sha256 (hash of anchor excluding only anchor_sha256).

The caller supplies the exact original_reference object. Verify its canonical hash, positive integer source_read_completed_at_utc_ns versus the anchor decimal clock, schema mastermind.prospective_reference.v1, and exactly MU/SPY/QQQ/SMH probes. Validate BOUND/REFUSED and exact BOUND v1 polygon row membership, evidence/binding/known_at/security values. Every original polygon row must be accounted for, no other native root is invented. Preserve the complete object and unchanged original row set; synthetic anchors are accepted only against their supplied exact object/rows. Do not hardcode a fabricated copy of the real object.

The real anchor remains canonical SHA 0e07e498d7a6983c8752a53d719281b07c30d334895c0b418edbbcc160145856, owner clock 1791354276802797000 ns, MU BOUND and SPY/QQQ/SMH REFUSED. This pure phase neither reads nor changes that installed artifact. Initial native family IDs are polygon:MU, polygon:SPY, polygon:QQQ, polygon:SMH; their predecessor revision IDs are anchor_id + "/" + family_id. The initial anchor is not a new observation.

Attempt envelope exact fields:
schema="mastermind.identity_attempt_envelope.v1"; attempt_id; sequence (positive int 1..64); predecessor_attempt_id; predecessor_sha256; kind (nonempty string); scope (1..4 unique family IDs); input_file_sha256; input_sha256; dependencies_sha256; acquisition_sha256; owner_read_completed_at_utc_ns; payload; attempt_sha256.

First predecessor is anchor_id/anchor_sha256; later predecessor is the preceding attempt ID/seal. Sequence is contiguous, IDs unique, owner clocks strictly increase from anchor; duplicate/fork/mutated/reordered/truncated prefixes refuse. attempt_sha256 hashes the full envelope excluding only itself. payload is bounded JSON and may have an unsupported future schema: its digest participates in outer integrity, but its semantic interpretation is deferred. kind/scope are sealed routing metadata, not an authority grant. Sequence is not a visibility clock.

Identical serialized history replay is deterministic. A repeated accepted attempt ID within one array is invalid (it is not a second observation); a writer retry must retain the original array. No writer or retry operation exists here.

## Visible attempt payload

Only after enrollment and cutoff selection, payload must have exact fields:
schema="mastermind.identity_attempt_payload.v1"; dependencies; acquisition; families.

dependencies exact fields: source_commit; prior_receipt_sha256; artifact_sha256 (exact five canonical names below); evidence_sha256 (object, <=16 nonempty string keys, each value digest or null). Its canonical digest must equal envelope dependencies_sha256. This validates represented seals; reading source evidence or proving predecessor publication is the future writer/adapter's responsibility. Missing per-family dependency may support REFUSED; it cannot support BOUND.

acquisition maps every scope family to exactly:
started_at_utc_ns; completed_at_utc_ns; outcome ("SUCCESS" or "FAILED"); representation ("raw_bytes"/"decoded_document"/"decoded_json"/null); response_sha256 (digest/null); source_published_at (aware ISO/null); published_date (date/null).
Require 0 < started <= completed <= owner_read. SUCCESS requires representation and response hash; FAILED may lack body/representation/publication. Source publication is retained independently and is never substituted for observation. Digest acquisition against acquisition_sha256. Shared acquisition entries cannot be absent: absence is rejected input, not an invented REFUSED observation.

NATIVE_REFERENCE scope is exactly the four initial native family IDs. SAME_VENUE_RENAME scope is exactly two distinct listing family IDs ("listing:" + bounded event token). A visible unsupported kind/schema refuses with IdentityError; a properly sealed future unsupported payload does not poison earlier views.

families is one entry per scope, each with exact fields:
family_id; alias_revision_id; predecessor_revision_id (null only for first listing revision);
vendor ("polygon"/"listing"); symbols (one exact probe ticker for polygon, two distinct ordered old/new symbols for listing);
security_id (nullable only for REFUSED);
country ("US"); mic; security_class;
status ("BOUND"/"REFUSED"); reason (nonempty string only REFUSED, null BOUND);
evidence_sha256; row_sha256 (unique list, empty for REFUSED);
family_sha256.

family_sha256 hashes the family excluding itself. Row and family seals use stable attempt_id/alias_revision_id, never attempt_sha256; there is no circular seal.

Native expected scope is MU/XNAS/CS, SPY/ARCX/ETF, QQQ/XNAS/ETF, SMH/XNAS/ETF. Listing requires XNAS and COMMON_CLASS_B or ORDINARY_CLASS_A. A family keeps vendor/symbol scope/country/MIC/class across revisions; an established non-null canonical security cannot change. A previously null REFUSED native family may acquire its first verified security in a later BOUND revision. Class is a sealed source assertion: the current security master has no class column, and this reader does not infer it from CIK. A source/class/MIC conflict is represented as REFUSED with declared expected family scope and zero rows; an incoherent BOUND representation is malformed.

REFUSED retains failed-source/fence/conflict evidence, shadows earlier BOUND, and has zero row members. BOUND requires SUCCESS acquisition and non-null required evidence dependencies. It verifies its canonical master row in the selected snapshot: exact security_id exists uniquely, security_state is null/empty, country and mic agree, parsed listing_key country/MIC/code agrees with row country/MIC/inception_code. Do not compare the security ID's inception spelling to today's venue as an identity allocator. It must not use a current master row under an older snapshot receipt.

## Versioned alias records

Exact fields are the existing vendor/vendor_symbol/security_id/valid_from/valid_to/ingested_at/known_at/evidence_sha256/binding_sha256 plus attempt_id/alias_family_id/alias_revision_id. ingested_at is a nonempty string retained as metadata, not a visibility clock. Existing rows keep their original fields/values and null or absent new fields.

Versioned binding_sha256 hashes schema="mastermind.identity_alias_revision.v1" plus the entire row excluding binding_sha256. row_sha256 in a family is the canonical digest of the full sealed row. All strings use exact typing, bounds are date/null and have positive width, known_at equals the exact owner-read clock, evidence_sha256 matches its family, IDs/vendor/security/symbol agree with family. No orphan/unlisted/duplicated row, wrong membership or cross-attempt row is accepted. Metadata membership and row-seal integrity are checked immediately, before semantic payload interpretation; integrity of a future physical row still matters.

A BOUND polygon family has exactly one row, symbol equal to the probe and valid_from non-null. A BOUND listing family has exactly two rows: old then new naming intervals with null first lower bound/null last upper bound and exact shared finite boundary; no gap, overlap or zero width. An open naming bound is not existence proof. Both directions check event-date coverage against the selected revision only. Whole-history overlaps are legal across revisions, not within a selected view.

## Snapshot context and actual enrollment

The five artifact names are security_master.parquet, vendor_aliases.parquet, issuer_master.parquet, issuer_migrations.parquet, security_migrations.parquet. A supplied receipt JSON may retain other existing owner fields but must include prospective_reference, identity_observations and publication.

publication exact fields:
schema="mastermind.identity_publication.v1"; generation_id; predecessor_receipt_sha256 (digest/null); code_version; artifacts; history_sha256.
artifacts maps the exact five names to {sha256, bytes, semantic_sha256}. bytes is a positive exact int. semantic_sha256 is mandatory for security_master/vendor_aliases and null for the other three; it seals the complete supplied JSON-normalized record sets. history_sha256 seals the complete history object. generation_id is the canonical digest of publication excluding only generation_id.

The pure snapshot validator requires identical receipt_before/receipt_after bytes; exact five immutable bytes payloads; byte counts/hashes; complete receipt/history/anchor seals; and alias/master semantic hashes. It stores immutable canonical JSON records plus exact receipt bytes and artifact hash vector. The API does NOT decode Parquet or independently prove that arbitrary supplied records came from those bytes. Future adapters MUST decode the very bytes accepted by receiptA/artifacts/receiptB and bind those parser results here; semantic manifest seals catch changed/dropped/projected records. This is a declared parser-custody boundary, not self-attestation of a live read. No code samples a clock or claims to authenticate the caller.

ReferenceReadReceipt exact serialized fields:
schema="mastermind.identity_read_receipt.v1"; receipt_sha256 (hash of complete receipt bytes); generation_id; artifact_sha256 (all five); history_prefix_sha256 (hash of that snapshot's complete history prefix); read_started_at_utc_ns; read_completed_at_utc_ns.
Require started <= completed and completed >= the snapshot's last owner clock. All fields must match a supplied validated ReferenceSnapshot, including the semantic records bound by its manifest. A receipt is a consistency record supplied by the existing adapter, not a signature.

from_records in history mode requires at least one validated context whose complete history equals the supplied history and whose alias record-set seal equals the supplied physical records. Each additional context must have the same exact anchor/original object and a genuine attempt prefix; changed/truncated/forked historical context is not accepted. Each context preserves the same original nonrevision rows and contains exactly its prefix's revisioned physical rows. Future history cannot authorize earlier replacement master bytes.

For a query, validate all supplied read-receipt integrity and context bindings, then consider only receipts whose complete clock and covered owner's prefix are <= decision_at. Select the greatest enrolled prefix. If multiple distinct generations with that prefix have different alias/master semantic seals, refuse ambiguity; do not choose a convenient latest master. Equivalent semantic generations choose the earliest completed eligible read, with deterministic digest tie-break only for equal content/provenance, never as invented observation time.

Semantic validation runs through the selected prefix, in sequence. Latest visible family revision shadows earlier versions, including zero-row REFUSED. Unaffected families retain their previous selected revision. Unsupported hidden future payloads are not validated. Immediate outer integrity/seal failures still refuse. A new late read containing old history cannot manufacture an earlier read receipt. An older enrolled prefix can resolve only with its own snapshot/master.

Check both directions for interval ambiguity in the selected view, across families as well as within a family. A typed REFUSED result is returned for a matching refused family, without falling back to its earlier rows. No eligible receipt or no matching eligible event interval yields UNAVAILABLE with a typed reason. on after cutoff is UNAVAILABLE. Unknown or empty clocked queries still validate the explicit decision grammar first.

## Classification and disabled effects

REJECTED_INPUT/shared-custody or predecessor failure is not an accepted attempt. NOT_COMMITTED publication failure is not an accepted history row. Only committed BOUND/REFUSED family dispositions are represented here. The pure reader rejects any attempt trying to encode REJECTED_INPUT/NOT_COMMITTED as an accepted family; it does not publish, persist, retry or reconcile a writer operation. After-commit lost-reply behavior remains a future owner operation preserving this immutable history.

Tests are synthetic and use the existing tests/test_dataos_identity.py. They must prove v1/legacy parity, source/owner/read clock separation and ns boundaries, empty/unknown query refusal, strict identities, BOUND→REFUSED→BOUND and A→B→A, receipt-only failure, original anchor preservation, old-prefix versus current master, future unsupported schema isolation, immediate future integrity refusal, both-direction uniqueness, row membership/orphans/forks/truncation, exact record-seal binding, and capacity limits. No real source acquisition, reference artifact, consumer adapter, publication or installed proof is exercised. Phase1 remains NOT_ADMITTED, H1/H2/H3 NOT_TESTED and all authority false.
