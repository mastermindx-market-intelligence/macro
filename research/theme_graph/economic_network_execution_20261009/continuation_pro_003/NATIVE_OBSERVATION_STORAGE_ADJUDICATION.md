# C01 native observation storage adjudication

Date: 2026-10-09. Reviewer: `/root/pure_reader_builder`. Principal: `/root`.

## Decision: BUILD, with the storage and provenance adjustments below

Build a bounded **private Company Intelligence observation append/read operation** on the existing Research Vault store. Preserve the exact candidate, complete retained source, source/span metadata, complete freshly computed inspection, frozen pilot adjudication, frozen independent semantic judgment, and a separately frozen review of the retained bytes. Store content-addressed components and publish a small immutable commit manifest last. A subsequent reader must reconstruct the evidence and call the existing relationship inspector again.

This is useful additional capability: a caller can obtain a stable reference to the complete inspection evidence and its distinct semantic-review provenance, reproduce the inspection in another process, detect corruption, and append a correction or review addition without overwriting the original. Merely writing the inspector's current JSON under another name would not meet this decision.

The principal explicitly confirmed that the user's end-to-end authorization covers this bounded private materialization. It does not establish publisher production, export or training rights, authenticated producers/reviewers, canonical company identity, product acceptance, or predictive eligibility. The proposed output remains `NOT_ADMITTED`, with null Graph 1 projection and all decision-authority flags false. No `PRODUCED` registry row is required or justified by this increment.

**Dispatch fence:** new `engine/company_intelligence/relationship_observations.py`, new `tests/test_company_relationship_observations.py`, and the minimum enrollment change in the existing `.github/ci/legacy-jobs.yml` job. Root subsequently dispatched the scratch-only builder and acquired a separate canonical pro-003 workspace at main `4d736c55`; that acquisition and its source/decision-path absence check are principal-reported, not executed by this reviewer. Do not modify the shared store, existing candidate semantics, held F04/Forensics/product paths, registry, runtime configuration, or publisher. Begin from the principal's accepted reader composition after its release and a fresh collision check. This review does not release the parent's currently frozen PR.

## 1. What this review actually inspected

Fixed native application head: `930125848136f08efd1bb61cc5899d9a5a0eeb51`. Fixed fetched main: `4d736c55adb630a4a8eb11b261e31acd0f6dc48b`. Workspace: `/Volumes/Mastermind/agent-workspaces/macro/web/gmi-economic-network-native-reader-20261009-pro-002`, on actual m2studio, Remote Desktop Commander device `3f5ce987-e3eb-40a3-af9f-4b0ae54919cc`.

Inspection used fixed-ref Git blob/tree/grep reads with `--no-lazy-fetch --no-optional-locks`, `GIT_NO_LAZY_FETCH=1`, `GIT_OPTIONAL_LOCKS=0`, and native Python with bytecode disabled. No fetch, ref mutation, application import, test execution, store construction, credential inspection, source acquisition, or application/runtime write occurred. The only new artifact is this report. This reviewer previously authored the separate pure-reader repair; this assignment does not independently certify that repair.

The seven pilot/review artifacts in the following table were read. Hashes were recomputed from their final bytes. The pilot's execution claims remain attributed to the principal; this lane did not run them.

| Artifact under `lanes/` | Bytes | SHA-256 |
|---|---:|---|
| `native_adoption_pilot_v1/protocol.json` | 8,673 | `cfff2160744ca51c6aabd1e6dd023ec07d6ddf99a345b93641056696b779763a` |
| `native_adoption_pilot_v1/native_adoption_return.md` | 15,228 | `fe175837da1b64eea082bc8873071c93fb5c582263d11928b48a59733e079c1f` |
| `native_adoption_pilot_v1/case_adjudications.jsonl` | 23,612 | `039cfbfa04738612457e5ed04be4b20864c088103bb5a8309ff7839938830b25` |
| `native_adoption_pilot_v1/source_attempts.jsonl` | 12,185 | `52a82c80857ba403b8db5bd1d971638e5fe4daec2e3416789386906ade9679a9` |
| `native_adoption_pilot_v1/replay_receipt.json` | 5,130 | `75dfbc580ce302c9802bf6d6da12d48401434f405505219cfdfb38719e2e502f` |
| `NATIVE_ADOPTION_PILOT_INDEPENDENT_SEMANTIC_REVIEW.md` | 32,181 | `c24cd161708a5ad696eedcf5159b976716581e2fe29cd8dcd1231d2c590c22b3` |
| `NATIVE_ADOPTION_PILOT_INDEPENDENT_SEMANTIC_JUDGMENTS.json` | 10,309 | `4357ab18cd8dddafd944b30641bf4c9168f755e1da60059a6ee5d8ded9192652` |

Current source evidence, including the exact native equality check between head `9301258` and main `4d736c5` where indicated:

| Source | SHA-256 | Scope of read / equality |
|---|---|---|
| `engine/research_vault/r2_store.py` | `7ba42eb8f74c034413997707a35156e67342fb9a30ca2b80dde0f11d1dc7e2bd` | Protocols, client separation, strict reads, both bounded modes, versioned reads, conditional writes, LocalStore constructor/path handling, factory; equal at both refs |
| `engine/company_intelligence/relationship_candidates.py` | `a558922c0586a5532f3912524b48f3cf592c3c6c9c21f689e3d416976e9cae55` | Frozen consumer reviewed earlier; current API, temporal, result and aggregate regions re-read; native head hash confirmed |
| `engine/company_intelligence/economic_observations.py` | `3373f342e282ae182ff65900eb051e8664c909f20e9b67ad97febd960cd9db34` | Closed PG imports/definition/selection interface; equal at both refs |
| `engine/company_intelligence/event_workspace.py` | `ff90af02298ed82797b0071f947be34a035064e1347f91f1cfef9f33822bfd47` | Earnings/fiscal schema, generation-chain comments and API inventory at main |
| `engine/company_intelligence/identity.py` | `1466868ae3b9f6461e67c7150be29634b463358dad994093b793685b007416f4` | Current registry API inventory; equal at both refs |
| `lib/dataos/registry.py` | `b57ec16a61086b8d35beb2f81af30efc4af55f1ac07ec95cfcfd87beefeef0a5` | Status, contract and validation law; equal at both refs |
| `lib/dataos/temporal.py` | `4415404186f0b0d2870f42d9e4a0b95be87937863adf30cf015ed34e8bf92b67` | Clock/profile rules and ordered-coalesce references; equal at both refs |
| `config/dataset_registry.yml` | `bb9b6975eeabebf630f73e632d307d280ea1d9e34f30953ac3989c65fc90f0a7` | All 22 dataset declarations parsed; equal at both refs |
| `engine/research_intelligence/store.py` | `e06c21ac60f8ebbb07153bcc8fad3a9616d303b34ef931f6d8ab8b3cba844e33` | Artifact/domain header and immutable-create/ambiguous-write reconciliation at main |
| `engine/institutional_census/storage.py` | `9d78d6d5af9424c3b30d0760cfb0b052d632d7b7e7864ae264768df11429bb44` | Dedicated owner/factory and immutable-create/readback conventions at main |
| `engine/earnings_narrative/private_publication.py` | `f543b7215784a1feaf4abb17218c84a45b126281f142cb3c6808afd7f0682734` | Existing publication namespace, bounded read, immutable-artifact and pointer routines at main |
| `engine/fundamental_forensics/attested_history_store.py` | `7a28128493357f16187bfd3748d34ce783fdbb9b5f28f96c48a37c37e738a6ec` | Dedicated read-only bucket/credential contract and API inventory at main |
| `.github/ci/legacy-jobs.yml` at head | `8754604c46e236023fab35aa6914196bc2462d9308772d406efed96c58dce7b2` | Actual existing candidate job and other store-path owners parsed |
| `tests/test_ci_pack.py` | `e2e7e0307a2e02fdd6703a40ff87f2efbd1d1fd82bf65d7ed365d579cccb8d52` | Existing five validation functions and candidate curation literal confirmed; equal at both refs |

These are bounded source inspections, not complete fresh audits of every incumbent module. Immutable source links are listed in §9.

## 2. Preserve the pilot's actual economic conclusion

C01 is one document-scoped assertion revision: Micron's 2024-02-26 announcement states planned integration of its **24GB 8H HBM3E** into the named NVIDIA H200 configuration, with calendar-Q2-2024 shipping planned. The separate statement that Micron began memory volume production does not prove downstream customer delivery. The observation cannot become ongoing 2026 supply, exclusivity, quantities, revenue, economic share, or a generic company-pair fact. Its date-only publication remains a date; no midnight publication instant is invented.

The selected labels remain source-local. `manual:micron-hbm3e-h200:2024-02-26:1` is a manual candidate identifier, and `manual:micron-ir:hbm3e-h200:2024-02-26` is a manual document identifier. Neither resolves a legal counterparty, issuer, listing, or security. Current Company Intelligence `IssuerRegistry.resolve_ticker(..., asof=...)` is not evidence that these labels have been resolved or that a historical knowledge-time identity view exists. The existing inspector deliberately leaves canonical subject/object IDs null and identity annotations untrusted. [S2, S7]

The other five cases must not be forced into C01's store as equivalent relationship positives:

| Case | Preserved disposition |
|---|---|
| C02 CATL/Tesla | Historical order-dependent framework, one source-defined buyer group; original-PDF route and multiparty adoption held. Research lifecycle wording is not a valid native enum. |
| C03 Apple | FY2023 supplier-roster observation; 98% is aggregate coverage, not an edge weight. Original-PDF route held; research lifecycle wording is not a native enum. |
| C04 Cameco/Brookfield | Historical 49/51 equity interests and qualified governance; ownership is outside the current relationship-kind contract. |
| C05 AMD | Heterogeneous fiscal segment accounting; no invented bilateral counterparty or relationship. |
| C06 Microsoft | Distinct cash flow, noncash lease and outstanding commitment measures; no invented supplier allocation or summed AI-demand pool. |

Those holds/refusals are semantic eligibility judgments in the pilot, not five executed native refusal witnesses. Six supported narrow source readings are not statistical precision, recall, corpus coverage, independent verification of commerce, or a production acceptance cohort. The separate NVIDIA transport control contributes zero additional economic cases.

### The retained-byte review gap is real and fixable

The frozen independent judgment explicitly labels C01's representation `WEB_RENDERED_HTML_WITH_SEPARATE_RETAINED_INPUT_PROVENANCE`. The web attempts record null raw-byte hashes and no new native capture. Preserve those facts unchanged. Hashing the independent review document establishes which review bytes were retained; it does not retroactively prove the reviewer inspected the exact retained HTML, authenticate the reviewer, or establish review independence by itself.

The retained Micron binding reported in the pilot is:

- Source SHA-256 `a7efabf9cec581ba684688368118e3e13df6a3043aff56667927e24df97e8b2e`; 504,119 original UTF-8 bytes.
- Character interval `[370876, 371258)`; byte interval `[370936, 371320)`; span SHA-256 `f79bce81f656e826b3aa74380eb9a2b63bf74fc0e60376dc2b40c64600eb890a`.
- Retrieval instant `2026-10-09T01:38:55.651385+00:00`; publication date `2024-02-26`; publication instant null.
- `MICRON_SOURCE_CASE.json` SHA-256 `dd72d31afce12ca727a171e6f635d7085c8c2d6bff6bea2750f9c29a04fe101b`.

This lane read the binding metadata, not the private source bytes. Root has commissioned a separate bounded read of the retained original span and context. Its **new addendum** should bind the actual candidate-file digest, canonical candidate digest, complete source digest/length, replayed span and reviewed context intervals, the original pilot-review digest, C01, and the actual reviewed representation. It should preserve planned/configuration-specific/null-magnitude qualifications and explicitly distinguish reviewing a span/context from semantically reviewing every byte of the HTML document. Reviewer labels and freeze timestamps remain procedural attribution; no cryptographic reviewer authentication is claimed.

Code construction can proceed while that addendum is being prepared. Do not claim a retained-byte semantic positive until the actual addendum is frozen and bound. The old web review remains useful provenance independently of that additional qualification.

## 3. Reuse the real store, with its exact limits

The incumbent `StrictConditionalWriteStore` already supplies:

```python
get_bytes_strict_bounded_versioned(key, maximum_bytes) -> VersionedBytes
validate_strict_conditional_write_capability() -> None
put_bytes_strict_conditional(
    key, data, *, expected_version, content_type="application/octet-stream"
) -> bool
```

`expected_version=None` means create only while the key is absent. R2 uses `IfNoneMatch="*"`; LocalStore checks the predecessor under a cross-process lock, writes a temporary regular file, fsyncs, and replaces it. False is the documented authoritative conditional-conflict result; operational/protocol failures raise. The local SDK capability check is not proof that a real remote bucket accepts conditional writes. [S1]

**Precise cap issue:** `HARD_MAX_STRICT_CONDITIONAL_OBJECT_BYTES` is 16 KiB, and LocalStore enforces it while reading an existing predecessor in `_version_at`. It does **not** cap the first new payload in `put_bytes_strict_conditional`. Consequently a first large create may succeed, while a later conditional attempt against that large predecessor raises before conflict classification. Do not describe this as a universal R2 or new-write maximum. Do not publish a whole large C01 object and assume portable repeat behavior.

Accepted Research Intelligence and Institutional Census code already reconcile ambiguous creates by exact bounded readback and refuse different bytes at an immutable key. They demonstrate the necessary distinction between absence, collision and unknown effects. They also contain domain-specific W1/RIO or 13F schemas, owned-key validation and dedicated configuration; do not import their producer, forge their receipts, or transfer their namespace to C01. The reuse boundary is the existing Research Vault adapter and its public protocols, not a renamed vertical producer. [S3, S4]

### Read the stronger existing bounded mode

Both native Research Vault adapters also implement the existing `BoundedStrictReadStore` keyword contract:

```python
get_bytes_strict_bounded(
    key, *, expected_byte_length, max_byte_length
) -> bytes | None
```

Use this exact-length mode for the manifest and all chunks. LocalStore checks the root/path components, rejects symlinks and nonregular objects, checks identity/size while opening, and bounds the read. Its generic positional-cap path calls `_open_strict_read` and lacks the same nonregular-file checks. For example, opening a FIFO through that path can block before a useful bounded read occurs. R2's exact-length mode binds HEAD and GET with the service ETag and checks lengths. Choose the existing stronger mode; do not repair or broaden the shared adapter in this slice. [S1]

The reference returned by append must therefore include **both manifest digest and manifest byte count**. A later reader can use exact-length mode for its first read rather than guessing a manifest length or falling back to the weaker mode. Unsupported signatures/capabilities are typed refusals, not a reason to call legacy `get_bytes`, `exists`, `put_bytes`, or list-prefix enumeration.

The existing factory supports explicit LocalStore and dedicated private Research Vault R2 settings. It refuses implicit generic delivery-credential fallback and configured private/public bucket aliasing. A source read of that factory does not prove any current private bucket or credentials are configured. The first real materialization can use a principal-selected **private local directory outside the repository**, with an explicitly constructed incumbent LocalStore. Reader construction must be outside the strict read guard after verifying the directory already exists; its constructor performs `mkdir`. Do not silently call the environment-selected factory inside the observation reader. [S1]

## 4. Exact minimal implementation contract

Final principal narrowing: seal one complete bounded evidence package of at most **1 MiB**, use at most 16 KiB chunks/manifest, and compute `inspect_candidate` internally. This supersedes the broader multi-component capacity considered during inspection. Use two public functions in the new Company Intelligence module. Private helpers may validate, canonicalize, segment and verify the bounded record; do not export a general storage framework.

```python
append_relationship_observation(
    store, *,
    case_id,
    candidate_bytes, source_bytes, source_record_bytes,
    pilot_adjudications_bytes, semantic_review_bytes,
    semantic_addendum_bytes,
    prior_observation=None,
    registry=None,
) -> dict  # stable manifest reference, after verified commitment

read_relationship_observation(
    store, reference, *,
    as_of=None, registry=None, include_support_text=False,
) -> dict  # verified storage binding plus actual inspector output
```

These are proposed interfaces for immediate implementation, not existing APIs or a claim that code has been built. `semantic_addendum_bytes` may be absent only if the record explicitly preserves an unbound-review disposition; absence must never yield a retained-byte-reviewed positive. Root may simplify v1 by requiring the addendum before any real append. Do not accept a precomputed `inspection`, a caller-supplied success flag, a module path, a provider, a source fetch callback, or a producer-authentication Boolean.

### Input and component rules

Inputs are exact bounded bytes, with strict UTF-8 round trips where appropriate. Parse JSON with duplicate-key and nonfinite-number rejection. Bound bytes before decoding/materialization and validate closed shape/cardinality before collection conversions. All supplied candidate rules remain owned by the existing candidate inspector. No arbitrary caller-object sandbox is implied; this is a closed JSON-shaped/private bytes interface.

Preserve these role-distinct components:

| Component | Byte representation and v1 ceiling |
|---|---|
| `candidate` | Actual original candidate-file bytes; 256 KiB. Also compute the existing canonical API payload binding. |
| `source` | Complete original UTF-8 source bytes; 4 MiB. No HTML-to-text substitution or PDF extraction. |
| `source_record` | Exact source/capture metadata, including C01's declared purpose limits; 64 KiB. Metadata is still untrusted attribution. |
| `pilot_adjudications` | Exact frozen six-case JSONL artifact; 64 KiB, selecting C01 by its explicit case ID without discarding the parent artifact. |
| `semantic_review` | Exact frozen independent judgments JSON; 64 KiB. Preserve web-representation scope. |
| `semantic_addendum` | Separately frozen retained-byte review JSON; 64 KiB if present. Validate its byte/span bindings against actual inputs. |
| `inspection` | Complete canonical output computed by the real `inspect_candidate` for this case, `as_of=None` and `include_support_text=False`; it must fit the overall package bound. |

Seven roles maximum. The **complete serialized package**, including all encoding overhead, is at most 1,048,576 bytes; the separate manifest is at most 16,384 bytes. The per-role limits are upper bounds, not simultaneous allowances: any source or role that cannot fit the stricter package bound is refused by this v1 materializer even if the existing inspector would accept it. These explicit local limits avoid a growing generic artifact bag. The retained C01 source leaves roughly half of the package budget for candidate, metadata, reviews and inspection; actual complete package fit must be measured by the builder before any write. An unknown role, duplicate role, oversized aggregate, malformed metadata or impossible binding refuses before storage effects. If retaining an additional full review manuscript later becomes necessary, explicitly revise this contract and its bound rather than silently adding arbitrary attachments.

The span need not be copied into a competing receipt format: retain its original candidate receipt, the full source, the source record, and the complete inspector support result. On every read, recompute its exact original byte interval/digest and invoke the incumbent receipt replay through the inspector. This preserves the actual source and span while leaving canonical receipt law with its current owner.

### Manifest and identity

Use one closed `company_intelligence.relationship_observation/v1` manifest with these fields:

| Field | Required meaning |
|---|---|
| `schema`, `producer_contract` | Fixed local protocol/version, not authenticated producer identity. |
| `case_id`, `subject_binding` | Stable case identifier and explicit untrusted binding to candidate/document/source identifiers, C01 for the first real record; no inferred issuer ID or authenticated subject. |
| `package`, `components` | Package descriptor: complete-byte SHA-256, exact byte count and derived chunk count. Fixed role bindings describe original bytes/digest/encoding within the package. No caller storage keys. |
| `inspection_request` | Frozen current-only request parameters and whether a registry was supplied. No registry authentication claim. |
| `semantic_review_binding` | Original web-review digest; optional addendum digest; explicit representation and checked bindings; authentication/independence status not established by the function. |
| `prior_observation` | Null or one bounded reference plus `corrects`, `contradicts`, or `adds_review`. A declaration, not automatic selection/erasure. |
| `purpose_scope` | Commissioned private observation materialization; publisher production/export/training permission not established. |
| `admission`, `authority`, `graph1_projection` | Fixed `NOT_ADMITTED`, all false, null. |

Do not duplicate the economic assertion into a second editable object: it remains in the exact candidate and actual inspection. Unknown publication instants, actual shipments, present commercial status, quantities, revenue and canonical identities stay unknown in those objects.

The manifest's canonical bytes determine its SHA-256. The observation identifier and storage key are derived from that digest; avoid a self-referential digest field inside the hashed bytes. The returned closed reference needs a schema, the digest (or derived observation ID), and exact manifest byte count. Repeated append of unchanged inputs returns the **same reference**. Creation status, attempts, local paths, wall-clock invocation times, file mtimes and operational diagnostics must not enter content identity. Genuine source/review clocks already present in frozen evidence retain their meanings.

This identifier binds an archived evidence/inspection revision. It is not a canonical relationship ID or economic truth identity. Different original candidate-file formatting can legitimately create a different archive reference while retaining the same canonical candidate payload digest; the two identities must be labeled separately. A digest or code-version label alone is not an authenticated execution receipt. Root's exact-head execution proof remains separate.

### Chunk and commit layout

Choose the new narrow namespace `company_intelligence/relationship_observations/v1/` within the explicitly supplied private store. Proposed keys:

```text
company_intelligence/relationship_observations/v1/components/sha256/<digest>/chunks/<six-digit-index>.bin
company_intelligence/relationship_observations/v1/commits/sha256/<manifest-digest>.json
```

The complete canonical evidence package is split into deterministic raw chunks of **16,384 bytes maximum**, with at most 64 package chunks. The logical role components can be retained as exact UTF-8 strings in that package (including original candidate-file formatting and JSONL newlines), then round-tripped and independently digest-checked after parsing. JSON escaping must preserve the original reconstructed bytes; a pretty-printed replacement of the original evidence file is not equivalent. No base64 is needed for these UTF-8 inputs. The last chunk has the exact derived residual length. The package itself is nonempty. Empty source is refused by the existing candidate contract. The reader derives chunk keys and expected lengths from the validated package descriptor and fixed segmentation, then verifies the complete package digest and every reconstructed role binding. No compression, base64 expansion, filename-derived key, user-provided path, multipart R2 feature, mutable current pointer or new bucket is needed.

C01's 504,119-byte raw source by itself would occupy **31 chunks**, with 30 full chunks and a 12,599-byte final chunk. The complete serialized package has additional metadata and escaping overhead; its actual chunk count has not been measured by this lane and must not be reported as 31. No store was populated. The manifest remains small because it names a bounded package descriptor and seven role bindings rather than an unbounded list of attachments.

## 5. Append/read state and failure law

The following sequence is binding:

1. Validate the complete input bundle and all caps; compute the real current `inspect_candidate` result; check source/span and review bindings; canonicalize components and manifest. Reject any attempted authority promotion. No store effects before this stage completes.
2. Require the existing conditional-write and exact-length bounded-read capabilities. Missing/unavailable configuration or unsupported capability remains a typed failure. No fallback to legacy store methods.
3. Probe the exact commit reference using its expected byte count. If present, verify the complete manifest and every required component, then replay the inspector. Only exact agreement can return the same stable reference. A present but corrupt commit is never repaired.
4. For an absent commit, create each absent chunk with `expected_version=None`. After a successful acknowledgment, conflict, or ambiguous modifying error, reconcile through exact-length readback. A byte-identical object is acceptable reuse; different bytes are a collision; unreadable/unknown results do not authorize overwrite or repeated speculative writes.
5. Read and verify every complete component, including the generated full inspection and actual semantic-review bytes. Only after that full verification create the manifest using `expected_version=None` and read it back exactly. Return the reference only when commitment is proven.
6. On a modifying timeout followed by an unreadable commit state, return/raise a bounded **effect-unknown** failure carrying only the expected reference and safe error category. Do not claim no write occurred. A later read-only reconciliation can establish whether the exact manifest and complete closure exist. Exact readback after lost acknowledgment may establish commitment; it still does not authenticate a remote producer.

Chunks left by a failed precommit attempt are **uncommitted components**. Do not count them as observations, enumerate them into successful results, delete them, or publish a replacement manifest over damaged state. Retry may reuse byte-identical chunks and finish an absent manifest. A manifest referencing a missing/different/oversized component is a corrupt committed closure and must fail closed. Logical immutability is enforced by these functions; this is not a claim of bucket-level WORM enforcement against other credential holders.

Corrections and review additions append new manifest identities and retain the old one. A supplied predecessor reference is preserved as a link, never evidence of automatic legal supersession or permission to select a winner. Missing/ambiguous targets remain unresolved. Candidate correction semantics continue to come from the incumbent inspector. Do not create a cross-issuer latest index or a global candidate-ID registry in this first slice.

### The real consumer path

Both functions reconstruct the actual candidate/source and call the existing public inspector:

```python
engine.company_intelligence.relationship_candidates.inspect_candidate(
    candidate, source=source, as_of=as_of, registry=registry,
    include_support_text=include_support_text,
)
```

This is also the existing per-case consumer called by `inspect_review_set` and its `--review-set` CLI. The new storage reader can be checked against that already-owned path without adding a second semantic inspector, mutating the review-set API, or installing a product route. The archive adds original-file bindings and review provenance around the complete incumbent result.

Append always seals a current inspection. Read returns the **fresh complete inspector result**, its storage/content bindings, and a separate semantic-review provenance section. It does not replace `support.semantic_adjudication = NOT_PERFORMED` inside the incumbent inspector: that field truthfully describes what that inspector did. A separate attached review is separately described.

For the original request, compare the complete fresh canonical result with the sealed inspection. A mismatch is a visible replay mismatch, not a silently substituted old positive. A changed request (`as_of`, support-text option, or registry-supplied state) is separately labeled and cannot claim exact equality with the original sealed result. Software/contract drift must remain distinguishable from verified byte integrity; preserve the old sealed bytes rather than rewriting them to match current code.

Every semantic attachment is gated by the **actual current returned case status**. If a historical query refuses or excludes the case, return that full existing refusal/exclusion and withhold the saved positive's candidate labels, support, source-provenance text and semantic-review assertions from the new response/aggregate. A private store's possession of later evidence is not permission to expose it through a historical answer. If the record is subsequently used in the existing review-set path, its processing denominators remain input counts. The new single-observation API should not invent a separate economic denominator; duplicate bytes never become independent corroboration. [S2]

For C01, a non-null `as_of` with the real registry still refuses because its native dataset binding is null (`AS_OF_DATASET_REQUIRED` after a valid Registry is supplied). Without a registry it refuses earlier as `AS_OF_REGISTRY_REQUIRED`. This is the required natural abstention: the actual retained C01 input cannot provide a native historical dataset/history view. Do not fabricate a `PRODUCED` relationship row to make it pass. Source publication date, current file creation, review freeze time and store upload time cannot substitute for the missing history. [S2, S6]

## 6. Ownership and occupied paths

The following are direct current source or PR observations, not hypothetical owner dependencies:

| Incumbent / carrier | Observed evidence and consequence |
|---|---|
| Research Vault adapter | Existing public store protocols and private factory are sufficient. Read-only dependency only; no shared-file edit proposed. |
| Company Intelligence PG observations | Current `economic_observations.py` imports PG definitions and rejects undefined metrics. C01 is not a PG metric selection; no widening or counterfeit PG receipt. [S8] |
| Company Intelligence event workspace | Current contract is a compact earnings/fiscal payload with immutable-generation chain. Do not invent an earnings event/fiscal period to persist C01. [S9] |
| Private earnings publication / PR #8245 | Current draft head `b019f975c6959803e872fd5000601d6c4591bf62`; all seven changed filenames read. It owns `engine/earnings_narrative/private_publication.py`, its private-store test and shared CI/deployment files. Preserve it. Main's existing publication routines also use legacy writes/pointer behavior; they are not a shortcut to this new strict create-only contract. |
| Semiconductor B / PR #7870 | Current draft head `f12db8bff1d1a46a2c9fbf100bed8f6f3abc9ec9`; complete changed-file inventory read. It owns Company Intelligence event-workspace and related source/theme/rights paths and the shared CI manifest. Its shared-kernel extraction/release gates are not satisfied by this observation slice. |
| F04 native evidence preview / PR #8703 | Current draft head `572e05ddedfae9210c74818d2b6a45ae1c5b6fb8`; exact three-file inventory: `engine/company_theme_exposure/factor_evidence.py`, `tests/test_factor_atlas_native_evidence.py`, and shared CI manifest. PR states no live trusted source-use adapter or customer path; no borrowing its proposed preview as C01 source-purpose admission. |
| Fundamental Forensics | Its current findings derive from detector/comparison models. `attested_history_store.py` is a dedicated read-only bucket contract, not the Research Vault bucket, and intentionally has no conditional writer surface. C01 must not be inserted into that store, detector outputs, or served findings. [S10] |
| GMI D2E / PR #8540 | Draft head `03462ef689a5bbb4c4254c48db34713efd731876`; exact two research paths read in inventory. Current record holds selected-generation proof, with replacement Phase 2 not assessed and independent P3 pending. A private C01 commit cannot satisfy those owner gates. |
| K3-D / PR #6514 | Draft head `74b6426c8be71adec27df00f2f98172f8528c2b2`; complete file inventory read. The held compiler is explicitly a hypothesis composer, not a store. Its explicit Sol acceptance gate remains. No compiler/store/Graph 1 adoption here. |

The proposed two source/test paths are absent at native head `9301258` by exact `ls-tree` reads. Neither appears in the complete candidate inventories above. This is **bounded collision evidence**, not a claim that every current open PR was inventoried. Root must perform the normal fresh prebuild collision/ownership check, especially for the shared CI manifest. The checked `docs/ACTIVE_BUILD_MAP.md` at main has SHA-256 `9cd6e0850c04d4bcbab0c7ffca2d304b2ccb4c2f42524d2c1d60cb171764228f` and still lists now-accepted #8661 as draft; it is not a sufficient current liveness or clearance source.

Current dataset registry parsing found 22 rows and no Company Intelligence relationship-observation dataset. `DatasetStatus.PRODUCED` expressly means an existing store written by a producer today; the validator checks declaration structure, not actual producer authentication, source-purpose permission or product acceptance. A physical private-local append can be truthfully reported as that operation's materialization without changing this registry. [S6]

## 7. Required useful proof and CI enrollment

At the inspected parent head `9301258`, the existing `company-relationship-candidates` job is already `gate: code`, `scope: exclusive`, Python 3.12, with 69 declared paths including `engine/research_vault/r2_store.py`, all existing manual/pinned/review-set modules and their suites. Root must preserve that released parent composition when integrating the separately acquired pro-003 base. Its legacy `if: ${{ false }}` representation is not evidence that curated execution is disabled. It is already in the existing curated inventory. Add the new module, new test path and that test to the existing test command. No new job, workflow, or `tests/test_ci_pack.py` registration change is indicated. [S11]

Required discriminating tests in the new test file:

1. Full synthetic source/candidate/review bundle crosses several chunks, is appended using actual LocalStore, and is read in a fresh Python process through the actual consumer. Complete positive result equality must hold. The child does not import the parent test/fixture module, collector, requests or urllib3; network/process denial precedes application imports, bytecode is disabled, and full filesystem mutation denial follows the same already-reviewed existing-directory construction point. Do not weaken the accepted reader guard.
2. Exact repeat returns the same reference and does not rewrite committed content. Exercise concurrent same-content creation and a lost-acknowledgment result through bounded reconciliation, with native LocalStore behavior where applicable. Adapter doubles alone are not the native proof.
3. A failure before manifest publication leaves no committed observation; retry reuses valid chunks. Corrupt existing chunk/manifest, missing component and wrong complete digest refuse without repair. An unknown commit effect remains unknown until readback establishes it.
4. Enforce per-component, aggregate, manifest and exact-length caps; reject nonregular/symlink store entries, malformed descriptors and duplicate JSON keys. Do not fall back to the positional reader or legacy store methods.
5. A forged saved positive cannot bypass a fresh `inspect_candidate` call. Missing or mismatched addendum bindings cannot become byte-reviewed semantic support; caller identity/reviewer labels cannot set authentication or authority true.
6. Historical refusal uses the actual consumer and withholds all sealed positive semantics in the read response. Changed request and unchanged-request replay mismatch are distinct. Corrections/additional reviews retain the old committed record and unresolved links.

Do not duplicate the complete existing kind/tamper/temporal suite in the new file. Run it alongside the new storage tests. Suggested native commands, to be executed by the builder/principal rather than this reviewer:

```sh
PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/Caskroom/miniconda/base/bin/python3 -B -m pytest -p no:cacheprovider \
  tests/test_company_relationship_observations.py \
  tests/test_company_relationship_candidates.py \
  tests/test_company_pinned_relationship_candidates.py \
  tests/test_company_relationship_review_set.py -q

PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/Caskroom/miniconda/base/bin/python3 -B -m pytest -p no:cacheprovider \
  tests/test_ci_pack.py::test_every_declared_scope_in_the_real_manifest_is_covered \
  tests/test_ci_pack.py::test_the_curated_exclusive_set_is_actually_declared \
  tests/test_ci_pack.py::test_curated_exclusive_scopes_cover_their_own_import_closure \
  tests/test_ci_pack.py::test_plan_is_deterministic \
  tests/test_ci_pack.py::test_exclusive_curation_narrows_ordinary_code_prs -q
```

Use an operation-owned native temporary/cache directory and the appropriate required runtime; preserve a CI-matched Python 3.12 run if local default differs. The five CI functions exist at the inspected current pin. Their baseline plan does not prove selection by the actual future PR diff; exact-head hosted planning must still bind the eventual head/base/paths and select this existing job. No local `run_ci_pack --execute` is needed or authorized by this review.

Root's real proof should then use the existing original retained Micron bytes and the new exact-byte semantic addendum: append once, append again, verify identical references and complete stored closure, start a fresh reader, compare the full current result, and request the natural historical abstention using the real registry. Keep raw source and private payloads outside Git and public artifacts. Save compact digest/length/command/result receipts, including actual source/head composition and guard outcomes. This lane has not executed that proof, populated a store, or measured remote R2 conformance.

## 8. Decisions available now versus facts still missing

| Principal can decide under the current commission | Must still be established by observation/evidence |
|---|---|
| Own this bounded document-scoped record under Company Intelligence. | Actual appended manifest/component bytes and fresh-process read result. |
| Choose the narrow namespace, fixed segmentation, role caps and two-function API above. | Actual private-local root chosen for this operation and its completed write/read receipt. No current remote configuration is inferred. |
| Keep all outputs current-inspection-only, source-local and unadmitted. | New independently frozen review of the exact retained candidate/span/context. Existing web review is not relabeled. |
| Attach the frozen pilot/independent reviews and new addendum as separate byte-bound provenance. | Authenticity/independence of named reviewers or producer. Labels, hashes and test callbacks do not establish these. |
| Append new correction/review identities while preserving originals. | Later fulfillment/current commercial state, resolved canonical identities, economic magnitude or legal supersession. |
| Enroll the module/test in the incumbent CI job and require native positive/refusal proof. | Fresh collision check, final independent source review, actual new-head CI and principal release. |
| Perform the authorized private observation materialization. | Publisher production/export/training rights, served-product acceptance, F04/D2E/K3-D owner gates or predictive eligibility. |

**Do not defer the code build for the missing production facts.** Build and prove the explicitly authorized private-local capability while keeping those facts unestablished. Conversely, do not label code, a source hash, a metadata row or a private append as having supplied them. Completion of this bounded slice means a repeat-safe immutable observation with independently reviewable evidence, actual positive replay and actual abstention; it does not mean a production economic network has been admitted.

## 9. Direct source references and execution boundary

- **S1:** [Research Vault native store at main 4d736c5](https://github.com/mastermindx-market-intelligence/macro/blob/4d736c55adb630a4a8eb11b261e31acd0f6dc48b/engine/research_vault/r2_store.py). Relevant source regions: protocols 47–182; private client 184–217; bounded R2 read 319–466; R2 conditional write 535–586; LocalStore exact-length read 719–840; local predecessor/write 843–1017; factory 1070–1119.
- **S2:** [Actual frozen relationship consumer at head 9301258](https://github.com/mastermindx-market-intelligence/macro/blob/930125848136f08efd1bb61cc5899d9a5a0eeb51/engine/company_intelligence/relationship_candidates.py). Base result 181–218; temporal law 221–311; single inspector 314–389; review completion 737–782; API 785–826.
- **S3:** [Research Intelligence immutable artifact conventions](https://github.com/mastermindx-market-intelligence/macro/blob/4d736c55adb630a4a8eb11b261e31acd0f6dc48b/engine/research_intelligence/store.py), header and 741–813.
- **S4:** [Institutional Census dedicated store and immutable-create conventions](https://github.com/mastermindx-market-intelligence/macro/blob/4d736c55adb630a4a8eb11b261e31acd0f6dc48b/engine/institutional_census/storage.py), 1–150 and 157–244.
- **S5:** [Incumbent earnings publication](https://github.com/mastermindx-market-intelligence/macro/blob/4d736c55adb630a4a8eb11b261e31acd0f6dc48b/engine/earnings_narrative/private_publication.py) and [held PR #8245](https://github.com/mastermindx-market-intelligence/macro/pull/8245).
- **S6:** [DataOS registry law](https://github.com/mastermindx-market-intelligence/macro/blob/4d736c55adb630a4a8eb11b261e31acd0f6dc48b/lib/dataos/registry.py), [actual registry](https://github.com/mastermindx-market-intelligence/macro/blob/4d736c55adb630a4a8eb11b261e31acd0f6dc48b/config/dataset_registry.yml), and [temporal law](https://github.com/mastermindx-market-intelligence/macro/blob/4d736c55adb630a4a8eb11b261e31acd0f6dc48b/lib/dataos/temporal.py).
- **S7:** [Company Intelligence identity API](https://github.com/mastermindx-market-intelligence/macro/blob/4d736c55adb630a4a8eb11b261e31acd0f6dc48b/engine/company_intelligence/identity.py).
- **S8:** [Closed PG observation contract](https://github.com/mastermindx-market-intelligence/macro/blob/4d736c55adb630a4a8eb11b261e31acd0f6dc48b/engine/company_intelligence/economic_observations.py).
- **S9:** [Earnings event workspace](https://github.com/mastermindx-market-intelligence/macro/blob/4d736c55adb630a4a8eb11b261e31acd0f6dc48b/engine/company_intelligence/event_workspace.py) and [held PR #7870](https://github.com/mastermindx-market-intelligence/macro/pull/7870).
- **S10:** [Dedicated Forensics reader](https://github.com/mastermindx-market-intelligence/macro/blob/4d736c55adb630a4a8eb11b261e31acd0f6dc48b/engine/fundamental_forensics/attested_history_store.py) and [held F04 PR #8703](https://github.com/mastermindx-market-intelligence/macro/pull/8703).
- **S11:** [Actual candidate CI enrollment](https://github.com/mastermindx-market-intelligence/macro/blob/930125848136f08efd1bb61cc5899d9a5a0eeb51/.github/ci/legacy-jobs.yml) and [current CI validation functions](https://github.com/mastermindx-market-intelligence/macro/blob/4d736c55adb630a4a8eb11b261e31acd0f6dc48b/tests/test_ci_pack.py).
- Owner gate metadata: [D2E #8540](https://github.com/mastermindx-market-intelligence/macro/pull/8540), [K3-D #6514](https://github.com/mastermindx-market-intelligence/macro/pull/6514). PR states are observations at review time, not promises of future liveness. Exact heads are recorded above.

Read-only native process IDs reconciled to exit 0: `43818`, `51118`, `57732`, `59873`, `63424`, `70466`, `82945`. The final principal narrowing to 1 MiB and `inspect_candidate` was incorporated before this report freeze. Every source process used the permitted RDC carrier and fixed refs; no Studio Direct use. No proof command, native observation writer, private store, retained-source capture or product path was executed by this lane.

**STOP.** The source fence remains untouched. This report is the bounded build recommendation and evidence receipt for principal adjudication/publication.
