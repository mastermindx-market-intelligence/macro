# Next native source adapter seam

Read-only engineering review, 2026-10-09. Source pin: Macro `c503c2caabc45b10524c006fbddc571a8608019a`. Protected procedure custody remains with the principal at Mastermind `732cf7be88e7159b4995a8885fbd381cd1484e3e`. This lane changed no native source, Git state, jobs, source registrations, store, credentials, publisher or UI. Preserve active #7870/#8245/#7891, held #6514, micro-membership and Terminal #796.

## Executable recommendation

Build an additive Company Intelligence **pinned SEC retained-document adapter** over Fundamental Forensics. Its input is an exact existing `ffsecsrc_…` snapshot ID, canonical filing-manifest key and exact document ID, supplied by the existing owner. Its output is a native source-binding witness plus the existing manual relationship-candidate inspection. The source binding proves replay of retained bytes through the native archive contract; semantic interpretation, canonical counterparty identity, historical eligibility and downstream rights remain separate. Keep `NOT_ADMITTED`, all authority flags false and Graph 1 exposure fields null.

The first candidate increment is committed on the execution branch at `d68678701b0e58924ae9dd5cf1b7f45b1c598538`; it is not present at the examined main pin. The next PR depends on that reviewed implementation, rather than claiming an existing main API. Do not rewrite its unauthenticated caller-metadata result to “authentic” or “admitted.” Attach a separately named `native_source_binding` result with exact native witnesses, and pass verified original bytes to the established pure inspector.

Suggested next files: `engine/company_intelligence/relationship_source_adapter.py` and `tests/test_company_relationship_source_adapter.py`. An optional module CLI can live in the new adapter file. No shared collector, profile, rights registry, publisher or fact-store edits are necessary. No automatic HTTP acquisition, latest-pointer selection, broad listing, earnings event creation or issuer-ID allocation belongs in this PR.

## Exact APIs and the one-document read

Use these public native imports:

```python
from engine.fundamental_forensics.filing_attestation import (
    PinnedSourceAuthority, gzip_stored_byte_ceiling,
)
from engine.fundamental_forensics.sec_document_spine import (
    manifest_from_json_bytes, HARD_MAX_FILING_MANIFEST_BYTES,
)
from collectors.sec_document_spine import manifest_storage_key
```

Callable signatures at the examined revision:

```python
PinnedSourceAuthority(*, store: Any, snapshot_id: str)
authority.read_file(*, kind: str, relative_path: str,
                    maximum_bytes: int) -> SourceFileRead
authority.read_archive_document(
    *, storage_key: str, expected_receipt: Mapping[str, Any],
    maximum_bytes: int, maximum_stored_bytes: int | None = None,
) -> ArchiveDocumentRead
manifest_from_json_bytes(content: bytes) -> dict[str, Any]
manifest_storage_key(manifest: Mapping[str, Any]) -> str
gzip_stored_byte_ceiling(expected_raw_bytes: int) -> int
```

`SourceFileRead` contains original content and a `SourceWitness` with snapshot ID/time, source kind, relative path, outer object key, SHA-256, byte length and content type. `ArchiveDocumentRead` contains decompressed original bytes, the outer gzip-object read, the independently retained receipt-sidecar read and `receipt_sidecar_verified=True`.

Selection and validation must occur in this order:

1. Obtain an already configured native strict-read store and an explicit owner-supplied snapshot ID. Construct the exact native `PinnedSourceAuthority`. No duck-typed substitute authority or caller-created snapshot mapping should be accepted for a positive witness.
2. Read the explicit manifest key through `authority.read_file(kind="archive", relative_path=manifest_key, maximum_bytes=HARD_MAX_FILING_MANIFEST_BYTES)`. Parse with `manifest_from_json_bytes`. Require `manifest_storage_key(manifest) == manifest_key`. If selector CIK/accession/manifest ID are separately supplied, compare each to the parsed native fields. The canonical key is `manifests/{cik}/{accession}/{manifest_id}.json`; preserve leading-zero CIK and native accession syntax through the native contract.
3. Select exactly one manifest document by exact native `document_id`, rejecting duplicate/ambiguous selectors. Do not pick the first matching name or silently substitute a primary document. Require `availability == "stored"`, a native retrieval mapping, non-null bounded length/digest/storage key, and receipt/document binding already validated by the native manifest parser. A declared or missing member is a typed availability result, not a positive body witness.
4. Enforce the native materializer’s causal checks: manifest `recorded_at` and selected receipt `retrieved_at` must not be later than the pinned `snapshot_at`. Use aware timestamp parsing without converting date-only `filed_on` or `report_date` into timestamps. These checks establish capture causality, not Data OS `known_at`.
5. Set a finite application raw-document budget before reading. Reject exact integer violations, bools and over-budget receipt lengths. Call `read_archive_document(storage_key=document["storage_key"], expected_receipt=document["retrieval"], maximum_bytes=application_cap, maximum_stored_bytes=gzip_stored_byte_ceiling(receipt["byte_length"]))`, subject to the owner helper’s native hard ceiling. Do not use an unbounded gzip read or substitute a CompanyFacts gzip route lacking a verified filing-document sidecar.
6. The native reader validates the actual retained sidecar against the complete expected receipt, then reads the exact gzip object through the same snapshot and verifies bounded decompression, raw digest and length. Preserve manifest witness, sidecar witness, outer-object witness and native retrieval receipt separately. Digest the actual returned raw bytes, preserve strict UTF-8 round-trip requirements for the existing text inspector, and keep original source coordinates distinct from any normalized display text.

The underlying public source contract is:

```python
load_pinned_source_snapshot_strict(
    *, store: StrictBoundedReadStore, snapshot_id: str,
    max_manifest_bytes: int = HARD_MAX_SNAPSHOT_MANIFEST_BYTES,
) -> VerifiedSourceSnapshot
read_pinned_source_snapshot_file_strict(
    *, store: StrictBoundedReadStore, snapshot: VerifiedSourceSnapshot,
    kind: str, relative_path: str,
    max_bytes: int = HARD_MAX_FILE_BYTES,
) -> StrictSourceRead
```

These functions live in `engine.fundamental_forensics.source_sync`. Each positive file read reloads the authoritative immutable manifest; a forged session mapping cannot redirect the object. They use explicit pins, never mutable latest. Missing-object results are distinct from authentication, network and bounded-read failures. Do not catch every exception and report “not found.” An outer object hash proves native retained-source consistency; it does not independently prove SEC server authenticity or a semantic supply relationship.

## Strict-read store selection

The injectable runtime interface is `engine.research_vault.r2_store.StrictBoundedReadStore`, whose bounded method is `get_bytes_strict_bounded(key: str, maximum_bytes: int) -> bytes | None`. Prefer an existing owner-supplied configured reader. Do not construct `LocalStore` for this read-only slice: its constructor creates a directory. Do not use `source_sync.build_private_source_store`: it requests conditional-write capability. Do not fall back to generic research credentials, a different bucket or a filesystem root on absent dedicated configuration.

The exact dedicated native factory is:

```python
from engine.fundamental_forensics.attested_history_store import (
    build_attested_history_store, DedicatedAttestedHistoryStore,
)
build_attested_history_store(
    *, env: Mapping[str, str] | None = None,
) -> DedicatedAttestedHistoryStore | None
```

It returns `None` if any of four dedicated names is absent: `FF_ATTESTED_R2_READONLY_ENDPOINT`, `FF_ATTESTED_R2_READONLY_ACCESS_KEY_ID`, `FF_ATTESTED_R2_READONLY_SECRET_ACCESS_KEY`, `FF_ATTESTED_R2_READONLY_BUCKET`. Present but unusable configuration raises `AttestedHistoryStoreError`. Report only configuration availability; never emit values. The wrapper exposes bounded reads and deliberately rejects discovery, unbounded reads and mutations. It omits the conditional-write protocol members so write admissions refuse it structurally.

Important operational boundary: the factory/wrapper uses expiring read-only child credentials; `_active_backing()` can renew them through the native credential minter. The principal clarified that normal read-only authentication/refresh by an already configured native owner factory is incidental to this authorized read task, distinct from changing durable credentials. An implementation can therefore use this exact configured factory or consume an existing owner-managed reader. Do not promise zero credential activity when using it. No new account, parent grant, bucket or durable secret is authorized. This lane did not invoke the factory because neither a configured dedicated reader nor an exact retained-source pointer was available in the checked runtime.

## Rights, clocks and identity remain with their owners

`config/theme_sources.yml` governs GMI emissions and explicitly does not retro-gate pre-existing owner products. It contains no SEC/Micron family at this pin. `engine.theme_graph.rights.licensing_for_family(unknown)` returns `(True, False, False)` by native design: internal, no direct display, no redistribution. This is not a general retention, training, embeddings or evaluation grant. The Finance SEC evidence decision is Finance-specific. #7870 SEC-family admission is a downstream GMI/public-use seam, not a blanket block on already authorized private Company Intelligence source inspection or native Fundamental Forensics capture. The adapter should report source-policy scope and unavailable affected uses without altering those owners or emitting excerpt/body fields by default. Registry policy is cached per path; a warm process is not proof that a later policy-file change has been loaded.

No registered SEC relationship dataset/profile was found in the native 22-row Data OS catalog. Source snapshot, retrieval and filed-date clocks cannot substitute for a registered `dataset_id`, `TemporalProfile` and native clock crosswalk. Keep historical eligibility unavailable; never derive a local maximum/coalesce availability clock. When adopted inputs later exist, filter each owner input using its registered profile before derivation. DERIVED remains non-PIT-readable; a historical recomputation and an accepted served-artifact replay are different receipts.

Native manifest CIK, accession and document IDs are safe source-local bindings. They are not a resolved legal customer entity or a historical `ISS:` identity. Do not call local ID allocators or attach current ticker mappings as historical crosswalks. `Company Intelligence.SourceDocument` requires an earnings `event_id`; this is not a generic SEC transport contract. Do not manufacture an earnings event to make a 10-K fit it. The reviewed native flat span-replay receipt can remain the text-inspection bridge.

Native amendment lineage (`observed_accession`, inferred same-form/report-period, unresolved) must remain as supplied. An inferred amendment parent is not an observed correction; a later missing relationship mention is not termination. The source adapter must preserve conflicting/versioned provenance without overwriting a relationship observation.

## Actual evidence and next acceptance

This lane inspected native source and existing test definitions at the exact GitHub pin; it ran no native suites. The principal reports the first candidate increment independently passed and was committed. The adapter is not implemented or validated by this lane. **No real retained document, snapshot ID or configured reader has been positively read.** This is an explicit retained-source availability gap, not proof that all native captures are absent. No broad store enumeration occurred.

The bounded read-only Studio Direct follow-up confirmed the named execution workspace exists. The existing owner runner `scripts/run_fundamental_forensics_wave2.py` lines 190–197 declares `data/fundamental_forensics/raw`, `archive`, and sibling `observations` beneath its selected root; all three were absent beneath this execution workspace. The other owner runner declares default operator configuration `config/fundamental_forensics/attested_history_operator.v1.json`; that exact file was absent here. Presence-only checks found none of the four dedicated `FF_ATTESTED_R2_READONLY_*` variables in this Studio Direct process environment. No secret values were read or printed. No exact source snapshot, manifest key or alternate owner cache root was supplied or observed. These are workspace/process-scoped observations; they do not establish that a deployed native service, another authorized root or the private source bucket lacks captures.

The principal subsequently supplied the established canonical primary root `/Users/chriswong/Documents/Cluade/macro-main` and authorized the same bounded owner-path check, because the operation workspace is intentionally sparse. A read-only Studio Direct `Path.exists/is_dir/is_file/is_symlink` check found **all four exact paths absent under that primary root as well**: `data/fundamental_forensics/raw`, `data/fundamental_forensics/archive`, `data/fundamental_forensics/observations`, and `config/fundamental_forensics/attested_history_operator.v1.json`. No source/Git mutation, directory walk, credential scan or bucket enumeration occurred. Because none of those declared paths existed, there was no current pointer/manifest index to follow and no document chain was read. This adds primary-root-scoped owner-cache absence; it still does not prove absence from a separately configured deployed runtime or private bucket. The bounded availability lane stops here with retained-runtime proof explicitly unverified.

Concrete missing input for real acceptance: an existing owner-managed configured strict reader (or its dedicated configuration in the authorized runtime), plus an exact `ffsecsrc_` snapshot ID and canonical retained manifest/document pointer. Alternatively supply an existing owner local archive root and exact manifest key for the separate local-cache witness. Do not fabricate a receipt, infer an opaque snapshot ID, switch credentials or list a bucket to overcome this gap. The adapter can be built and meaningfully tested using explicitly synthetic native fixture stores while the real retained-source acceptance is recorded as unverified.

Tests for the next PR should prove exact pinned selection; canonical manifest binding; complete receipt-sidecar equality; raw/outer digest and length tampering; substituted document IDs/URLs; malformed bool/negative limits; date-only/naive and post-snapshot clocks; UTF-8 failure; missing versus outage/authentication distinctions; bounded gzip-bomb refusal; forged snapshot mapping; amended/inferred lineage preservation; zero writes/discovery/HTTP acquisition; excerpt suppression; and unchanged `NOT_ADMITTED`, null exposure and unavailable identity/PIT. Reuse native fixtures and spies instead of reconstructing a second receipt contract.

Acceptance has two separate levels. Offline adversarial fixture tests plus relevant owner regression tests establish wrapper behavior. A single real already-retained native capture must then replay the manifest, sidecar, gzip object, raw body and selected exact text span, recording pin/keys/digests/lengths and original clocks without leaking the body. Fixtures are not production evidence. If no such pointer or authorized configured reader is available, the CLI must return a truthful typed availability result and the PR must disclose that live acceptance remains unproven.

An existing local cache offers a separate lawful read-only witness route if the owner supplies its exact archive root and manifest key: `collectors.sec_document_spine.read_filing_manifest(cache_root: Path, storage_key: str) -> dict` then `read_archive_document(cache_root: Path, receipt: ArchiveReceipt | Mapping) -> bytes`. The latter independently reads the retained sidecar, requires exact receipt equality, and bounds decompression/hash replay. This proves local owner-cache binding, **not** an `ffsecsrc_` snapshot witness; do not invent a snapshot to label it pinned. Do not call `find_reusable_primary_retrieval` as a provenance validator: it intentionally collapses local anomalies to None for acquisition fallback.

If actual capture is absent, the existing owner acquisition seam is `SecFilingArchiveCollector.fetch_document` followed by native manifest retention and `source_sync.sync_source_roots`. That is a separate authorized capture action, not this adapter. Preserve the original retained retrieval clock on warm reuse. The collector’s per-client pacing does not establish a combined SEC fair-access rate budget. Original Micron IR documents require their own native source-owner admission; the SEC adapter cannot admit an arbitrary issuer URL under SEC identity.

## Inspected primary code provenance

Every link below is pinned to `c503c2caabc45b10524c006fbddc571a8608019a`. Sections/functions were inspected; tests were not run. Source blobs are recorded for decisive interfaces.

| Path at exact revision | Blob SHA | Decisive inspected section |
|---|---|---|
| [source_sync.py](https://github.com/mastermindx-market-intelligence/macro/blob/c503c2caabc45b10524c006fbddc571a8608019a/engine/fundamental_forensics/source_sync.py) | `1fc246978a13f9bbac203e9de565d5875ac003b1` | Strict pinned load/read; no latest fallback; owner-only sync |
| [filing_attestation.py](https://github.com/mastermindx-market-intelligence/macro/blob/c503c2caabc45b10524c006fbddc571a8608019a/engine/fundamental_forensics/filing_attestation.py) | `76a17ed1f4eb49a4cbcf7812eb84c063f0e55e65` | PinnedSourceAuthority, read_archive_document, raw and sidecar witnesses |
| [sec_document_spine.py](https://github.com/mastermindx-market-intelligence/macro/blob/c503c2caabc45b10524c006fbddc571a8608019a/engine/fundamental_forensics/sec_document_spine.py) | `54987bc3557d4bd5e7c7e0ec893b39b42ad988a6` | Canonical manifest parser, document/receipt validation, lineage |
| [collector sec_document_spine.py](https://github.com/mastermindx-market-intelligence/macro/blob/c503c2caabc45b10524c006fbddc571a8608019a/collectors/sec_document_spine.py) | `7e787d0fb6406becab938e05835cfdc22c1ab5a1` | Exact manifest/cache reads, sidecar equality, idempotent retention, collector |
| [filing_package.py](https://github.com/mastermindx-market-intelligence/macro/blob/c503c2caabc45b10524c006fbddc571a8608019a/engine/fundamental_forensics/filing_package.py) | `a2e5701c3ce9b35cbe142e65c1782cb1c78ceed4` | Native materializer manifest selection and causal clocks; full fanout avoided |
| [r2_store.py](https://github.com/mastermindx-market-intelligence/macro/blob/c503c2caabc45b10524c006fbddc571a8608019a/engine/research_vault/r2_store.py) | `8aec6ca9ce727146e970f055692edd993c5f3245` | StrictBoundedReadStore, strict not-found/error distinction, LocalStore constructor |
| [attested_history_store.py](https://github.com/mastermindx-market-intelligence/macro/blob/c503c2caabc45b10524c006fbddc571a8608019a/engine/fundamental_forensics/attested_history_store.py) | `1f987fd94806da5955d824fdaecae9e983761408` | Dedicated factory, credential lifecycle, bounded-only and denied surfaces |
| [rights.py](https://github.com/mastermindx-market-intelligence/macro/blob/c503c2caabc45b10524c006fbddc571a8608019a/engine/theme_graph/rights.py) | `edeee1714a63436935d6b7494acc94a28d23adc5` | Unknown-family tuple/refusal, cached registry |
| [theme_sources.yml](https://github.com/mastermindx-market-intelligence/macro/blob/c503c2caabc45b10524c006fbddc571a8608019a/config/theme_sources.yml) | `20e20cb9f40ba838821aabba371f4498724943f2` | GMI-only scope, declared families |
| [run_fundamental_forensics_wave2.py](https://github.com/mastermindx-market-intelligence/macro/blob/c503c2caabc45b10524c006fbddc571a8608019a/scripts/run_fundamental_forensics_wave2.py) | `905b5a4797c031863d9db7e487a9822bc2516d63` | Owner-declared default raw/archive/observations roots, lines 190–197 |
| [run_fundamental_forensics_attested_history.py](https://github.com/mastermindx-market-intelligence/macro/blob/c503c2caabc45b10524c006fbddc571a8608019a/scripts/run_fundamental_forensics_attested_history.py) | `6244346c165ab19a66e70572f7d640b16c18747c` | Owner-declared default operator configuration, lines 96–99 |

Relevant inspected existing tests: `tests/test_fundamental_forensics_source_sync.py`, `tests/test_fundamental_forensics_attestation.py`, `tests/test_fundamental_forensics_filing_package_materializer.py`, `tests/test_sec_document_spine.py`, `tests/test_fundamental_forensics_acquisition.py`. Earlier native identity/profile findings remain in `lanes/NATIVE_DATAOS_CONTRACT_REVIEW_20261009.md`; current registry and Company Intelligence transport reads confirmed the examined unchanged blobs. This recommendation does not promote rights research inventory into a native source admission receipt.
