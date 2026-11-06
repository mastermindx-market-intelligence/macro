# C01 private observation append/read — prepared implementation v1

## Delivery and verification status

The two source artifacts implement an immutable private observation on the existing Research Vault conditional store. They add content-addressed persistence, complete-package verification, safe repeat behavior and fresh-request inspection. **They are prepared source, not evidence that a native observation has been written or read.** This lane did not import the application, run its tests, construct a store, acquire a source, invoke a provider, or change native application/Git state.

| Artifact | Intended native path | Bytes | SHA-256 |
|---|---|---:|---|
| `relationship_observations.py` | `engine/company_intelligence/relationship_observations.py` | 42,432 | `4239285b177d2947173404f96f1672394b6f246e70ea4a82885e25ca8990196b` |
| `test_company_relationship_observations.py` | `tests/test_company_relationship_observations.py` | 43,659 | `80acae7aadcecec3214fe86d77c99da841d2544629d35380ec11b5d9cc94d67e` |

Both files and the embedded fresh-process test script passed Python `compile` without execution. There are 23 prepared test functions, several parameterized. **Native test results and retained-source append/read results are NOT_RUN by this lane.** The module was frozen before the test file was completed so independent source review could proceed in parallel. Neither file may change under those review hashes; an actual finding requires a new version and delta review.

The principal authorized the bounded scope and reported decision commit `a48d5c0c078bc531cfc0f6b37643f44f77c2e937`, containing `agentos/decisions/DEC-GMI-ECONOMIC-RELATIONSHIP-OBSERVATION-MATERIALIZATION.md`. Native application, source reconciliation, CI enrollment, store selection, real evidence execution and Git release remain principal-owned. Existing pilot, retained judgments, protected products and earlier reader files were preserved.

## Deliberately narrow contract

`c01_private_observation/v1` binds the six-case pilot's **C01 artifact shapes**. It is not a generic validator for arbitrary economic observations or arbitrary reviewer formats. The candidate must remain a source-local `product_integration` with lifecycle `planned`, no dataset row and no identity annotation. The first retained judgment's target must be the source-local object label followed by `H200 Tensor Core GPUs`. The principal retained judgment must name that same target or its exact H200 suffix. Both target forms must reconcile to the supplied replayed span; matching broad company labels alone are insufficient.

The checked summary preserves the component, the H200 target and planned status. The exact source, span and retained judgments preserve the distinction between planned downstream inclusion and the separate statement that memory production had begun. They do not establish completed customer delivery, ongoing supply today, all products of a company, quantities, economic weights, purchase amounts, exclusivity or authenticated legal identities. The publication remains a date without an invented publication instant. The code validates specified content bindings; it does not automatically understand prose, authenticate the reviewers, or independently verify commerce.

## Public API

```python
append_relationship_observation(
    store, *, review_set_id, case_id,
    candidate_bytes, source_bytes, source_record_bytes,
    pilot_adjudications_bytes, semantic_review_bytes,
    retained_first_review_bytes, retained_independent_review_bytes,
    prior_observation=None, registry=None,
) -> dict

read_relationship_observation(
    store, reference, *, as_of=None, registry=None,
    include_support_text=False,
    purpose="private_current_inspection",
) -> dict
```

The principal injects an existing store. The producer has no store factory, environment-selected bucket, credentials, registry loader, source-file reader, capture, network client, subprocess, CLI, route or publisher. It imports the existing `inspect_candidate` at runtime; the store protocol import is type-checking only. There is no caller argument for a precomputed inspection. Append calculates the complete original inspector result itself and retains it without reclassifying its `NOT_PERFORMED` semantic adjudication as an automated positive.

The raw artifact arguments must be exact UTF-8 bytes. The complete original six-case pilot JSONL and independent six-case review JSON are retained, although only C01 contributes this observation's interpreted bindings. The other five records are not additional economic observations or automatic validations by this producer.

An optional `prior_observation` is null or `{reference, relation}` with relation `corrects`, `contradicts` or `adds_review`. Its reference is shape-checked and retained as `UNRESOLVED_NO_SELECTION`. It is never fetched, coalesced, selected as a winner, or used to erase an original.

## Seven exact artifact roles

| Role | Binding and interpretation |
|---|---|
| `candidate` | Original bytes, source receipt, canonical API-payload digest, source-local assertion and original revision. |
| `source` | Original UTF-8 bytes, whole-source digest, replayed receipt and retained-review context intervals. |
| `source_record` | Source URL/date/encoding, whole-source and span identities, original case/candidate/document labels and explicit missing native/rights evidence. |
| `pilot_adjudications` | Exact six-record JSONL, C01 subject/scope/source binding and the cited independent web-review digest. |
| `semantic_review` | Exact independent six-case JSON, preserved as a web-rendered review with separate retained-input provenance. |
| `retained_first_review` | Exact first-reader judgment, source/candidate/metadata byte bindings, span, complete declared context coordinates/digest, narrow subject/scope and withheld authority. |
| `retained_independent_review` | Exact principal judgment, source/candidate/span bindings, declared context interval, subject/scope and withheld authority. |

Every original component is stored as `{sha256, byte_length, encoding, text}`. Re-encoding its UTF-8 text must reproduce its exact raw bytes. Whitespace is not normalized. The canonical candidate-payload digest is separate from the original candidate-file digest. Content identities are derived from supplied evidence/options/results, not a clock or latest pointer.

The first review's context digest is checked. The principal artifact supplies a different character interval; its byte coordinates and digest are explicitly derived from the supplied source by this reader. They are not retroactively described as fields that the principal's original receipt supplied. Reviewer labels, apparent independence, cited external receipts and matching hashes remain caller-supplied evidence. Output marks authorship, review independence, source custody and semantic truth `NOT_AUTHENTICATED`.

## Closed storage and result envelopes

The exact reference has only `schema`, `sha256` and `byte_length`. Its schema is `company_intelligence.relationship_observation_reference/v1`; its digest identifies the complete canonical manifest bytes. Its byte length is required **before the first read**, rather than discovered through an unbounded read.

The canonical manifest has only `schema`, `producer_contract`, `package_sha256`, `package_byte_length` and ordered `chunks`. Each chunk descriptor has only `sha256` and `byte_length`. Package identity is therefore reproducible from its bounded exact closure. Chunk identities alone are byte identities, not independent corroboration.

The closed package contains `schema`, `producer_contract`, `review_set_id`, `case_id`, `components`, `canonical_candidate_payload_sha256`, `inspection_request`, `inspection`, `review_binding`, `prior_observation`, `purpose_scope`, `admission`, `authority`, `graph1_projection` and `content_boundary`. The sealed request records a null cutoff, false support-text option and whether a registry was supplied. A supplied registry is not a registry attestation or an admitted dataset.

The closed returned result contains `schema`, `operation`, `status`, `reference`, `expected_reference`, `inspection`, `review_provenance`, `refusal`, `integrity_status`, `replay_status`, `effect_state`, `prior_observation`, `purpose_scope`, `admission`, `authority`, `graph1_projection` and `content_boundary`. Schema is `company_intelligence.relationship_observation_result/v1`. Refusals have stable codes, without backend paths, source-body interpolation or raw exception text.

| Limit | Enforcement |
|---|---|
| Complete canonical package | 1,048,576 bytes, including source/JSON escaping, seven originals and derived fields. |
| Raw supplied bytes combined | At most 1,048,576 bytes before parsing or inspection. |
| Candidate | At most 262,144 raw bytes. |
| Source record and each review artifact | At most 65,536 raw bytes. |
| Source | At most 1,048,576 raw bytes, further constrained by total serialized package size. |
| Chunk | At most 16,384 bytes; at most 64 ordered chunks. |
| Manifest | At most 16,384 bytes. |
| Complete inspector result | At most 524,288 canonical bytes. |
| Returned complete result | At most 1,048,576 canonical bytes for visible success. |
| Input JSON | Maximum depth 16, 8,192 counted nodes and 65,536 characters per scalar. The enclosing parsed package permits eight extra levels, 256 extra nodes and a bounded source scalar. |

Duplicate JSON keys, nonfinite constants/numbers, invalid Unicode, excessive nesting, malformed required fields and oversized artifacts produce typed refusals. The canonical serializer counts escaped UTF-8 bytes before materializing the final serialization and exits when the cap is exceeded. All payload, chunk, manifest and visible-success sizes are preflighted before the first write. This is a closed JSON/byte contract, not a sandbox for arbitrary executable Python subclasses.

## Append and read semantics

Storage keys are derived only from validated digests beneath `company_intelligence/relationship_observations/v1/chunks/sha256/` and `company_intelligence/relationship_observations/v1/commits/sha256/`. All reads, including the first manifest read, invoke the incumbent exact keyword mode:

```python
get_bytes_strict_bounded(
    key, expected_byte_length=known_length, max_byte_length=16384,
)
```

There is no positional, legacy, versioned, listing or latest fallback. Conditional writes use only `expected_version=None`. Before creating anything, append checks for a complete existing manifest and probes every existing chunk; a corrupt existing object is terminal. It creates absent chunks, verifies every raw chunk, reconstructs and verifies the complete package, and publishes the manifest last. It then verifies the committed closure again.

| Outcome | Exact meaning |
|---|---|
| `COMMITTED` | The expected manifest and complete closure were observed and verified after the creation phase. A concurrent identical producer may have supplied some objects; this is not a claim of exclusive authorship. |
| `REPEATED` | The expected manifest already existed, its complete closure matched the freshly prepared package, and no writes were issued. |
| `REFUSED` | No usable observation result is returned. Before a manifest attempt, the effect field says only that this call did not attempt that manifest; partial chunks can remain. After an attempted manifest, the expected reference remains visible and the result does not claim global absence. No refusal authorizes repair or overwrite. |
| `EFFECT_UNKNOWN` | A final write/readback or final closure read left commitment unresolved. Only the expected reference is exposed; no positive inspection or review is promoted. A later exact read can reconcile actual state. |
| `VERIFIED` on read | Exact closure and content bindings verify and the fresh inspector is inspectable. Only an unchanged request may also claim exact equality with the sealed result. |
| `ABSTAINED` on read | The actual fresh inspector returned a non-inspectable outcome. The complete fresh result is returned; sealed positive/review/prior-link semantics are withheld. |

A conditional-write exception may occur after a modification. The producer performs bounded exact readback; correct bytes resolve a lost acknowledgment, a known absence is a refusal, and unresolved final effect is `EFFECT_UNKNOWN`. It never blindly retries an ambiguous write. Missing components invalidate a committed closure; the reader and repeated producer do not restore them. Partial chunks are neither a committed observation nor automatically deleted.

Read computes the actual inspector outcome from the original candidate and source for the supplied request. In this unadmitted C01 slice, historical reads encounter the incumbent registry/dataset requirements; the new module does not invent a replacement refusal or create a `PRODUCED` row. A changed support option returns the actual fresh support result and marks it as a changed request, without claiming sealed-result equality. An unchanged-request mismatch refuses while retaining the real fresh result and withholding saved review semantics.

All statuses retain `NOT_ADMITTED`, null Graph1 and false rank/gate/size/trade/prediction. Production, public export and training remain false, source-purpose permission remains unestablished, and the payload is private evidence rather than certified quote-free or public-safe content.

## Prepared falsifiers and test coverage

The focused tests use synthetic Aurora/Boreal/Widget evidence and the actual LocalStore API. They do not read retained Micron/NVIDIA artifacts, fabricate a native dataset, or establish economic accuracy.

- Preserve all seven exact originals and the complete internally delegated inspector output across multi-chunk append, repeated append and read; verify raw/canonical candidate identities remain distinct.
- Require all exact-length reads and create-only predecessor values. Detect legacy fallback, unnecessary rewriting and mutation of caller input.
- Exercise concurrent identical native LocalStore creation, lost final acknowledgment, authoritative absent final readback and unreadable final effects. Later reads resolve actual committed bytes when available.
- Refuse missing/corrupt chunks, corrupt manifests, wrong digest/length, malformed descriptors, noncanonical or duplicate-key structures, and native symlink/FIFO/directory entries; no repair.
- Refuse metadata, subject, context, authority, exact artifact digest and both-broadened H200 target mismatches before store access.
- Refuse oversized/deep/nonfinite/invalid-UTF8 inputs and count JSON escaping before complete package materialization.
- Preserve actual inspector refusal and unchanged-request mismatch; reject a caller-supplied positive result; withhold sealed review semantics on actual historical refusals.
- Exercise support-text reads, unsupported purposes, unresolved prior links, exact whitespace-sensitive input identity and unauthenticated reviewer labels.
- In two separate Python processes, use only the supplied existing store root/reference; deny acquisition/client imports and network/process effects before application import. Record the incumbent constructor's narrowly allowed existing-root mkdir, then permit no filesystem mutation. Compare complete current/historical outputs byte for byte and verify store hashes/mtimes are unchanged.

The final fresh-process guard itself is 3,242 characters with SHA-256 `b89dcdaff980f88fddeaf86ee6d57839ad03fe857bddd70ac4bc37f725732d15`; it was syntax-checked as a separate script, not executed. The existing-root constructor allowance is explicit evidence of that attempted call and is not misreported as zero setup activity.

## Incumbent dependencies and proof still owed

The native store source was actually read through the authorized same-host read-only carrier: PID **30946**, exit **0**. The read covered protocol declarations and the relevant exact-read/conditional-write/LocalStore regions; it did not instantiate or invoke a store. `engine/research_vault/r2_store.py` was 47,498 bytes with SHA-256 `7ba42eb8f74c034413997707a35156e67342fb9a30ca2b80dde0f11d1dc7e2bd`. The immutable source pin is [macro 4d736c55, Research Vault store](https://github.com/mastermindx-market-intelligence/macro/blob/4d736c55adb630a4a8eb11b261e31acd0f6dc48b/engine/research_vault/r2_store.py). The independent frozen storage adjudication is `lanes/NATIVE_OBSERVATION_STORAGE_ADJUDICATION.md`, 45,586 bytes, SHA-256 `e4966d1e38fe0c5cc495982b74600ab77860fdf0d807db1129d70638bba67543`.

The exact incumbent inspector was read from `lanes/review_set_v4/relationship_candidates.py`, 45,473 bytes, SHA-256 `a558922c0586a5532f3912524b48f3cf592c3c6c9c21f689e3d416976e9cae55`. Its complete result and temporal refusal codes remain its own contract.

The syntax-only commands used `PYTHONDONTWRITEBYTECODE=1 python -B`, read the two prepared files, invoked `compile(raw, path, 'exec')`, and compiled the extracted child-script literal. No code object was executed. The principal's first native focused run should execute `tests/test_company_relationship_observations.py` with `python -B -m pytest -p no:cacheprovider`, alongside the owning job's existing compatible suites and required composition gates.

Before native acceptance, proof must show: byte-identical application of these reviewed files; focused native tests actually pass; all seven retained C01 artifacts pass the real bindings and final serialized package cap; append/read/repeat occur in an explicitly selected private incumbent store; the actual complete current inspector matches and the actual historical result abstains; fresh-process read guards observe no unexpected imports/effects; and immutable original evidence bytes remain unchanged. An R2 SDK capability method or a LocalStore proof is not remote bucket/rights proof. Root owns these concrete checks and publication.

The source-local observation is an executable private persistence step. Native dataset admission, authenticated custody, legal party resolution, purpose-specific licensing, historical system knowledge and any product/predictive promotion remain separate missing evidence. None is implied by this code, by retained byte hashes or by the research PR's merge.

**Lane state: prepared source/test frozen; native execution pending principal; STOP after return.**
