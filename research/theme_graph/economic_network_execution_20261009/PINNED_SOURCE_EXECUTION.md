# Pinned SEC source adapter — execution and verification

This continuation implements `engine/company_intelligence/pinned_relationship_candidates.py` on the same source carrier as the reviewed manual candidate inspector: [PR #8667](https://github.com/mastermindx-market-intelligence/macro/pull/8667). It uses Fundamental Forensics' existing retained-source reader to establish a stronger, explicitly bounded source binding before manual candidate inspection.

The adapter is implemented. Native focused validation passes **150 tests**: 43 new adapter cases and the existing 107 candidate cases. Independent review additionally runs three targeted native source-sync adversarial checks. Exact final review and GitHub delivery states are recorded separately from this implementation description.

## Result and trust boundary

A successful current call returns two separate objects:

- `candidate_inspection`: the existing manual assertion review, including native flat span replay and explicit identity/time/rights/admission gaps.
- `native_source_binding`: the selected snapshot, canonical manifest, exact document, retrieval receipt, retained receipt-sidecar witness, compressed-object witness, raw digest/length and source-local filing metadata.

The binding is labeled `verified_relative_to_supplied_native_reader`. It does not authenticate the supplied reader's production deployment, independently prove SEC authorship, or adjudicate the economic assertion. A self-consistent synthetic native store remains synthetic evidence. Requiring the native authority class is an input boundary; class identity does not establish institutional custody.

All results retain `NOT_ADMITTED`, null Graph1 projection and false rank/gate/size/trade/prediction authority. Canonical legal-party identity and purpose-specific rights remain unresolved. Native filing amendment lineage is preserved as source metadata; it does not overwrite candidate correction state or imply termination of an economic relationship.

## Exact API

```python
from engine.company_intelligence.pinned_relationship_candidates import (
    inspect_pinned_candidate,
)
from engine.fundamental_forensics.filing_attestation import PinnedSourceAuthority

# Obtain these objects/selectors from the existing source owner.
authority = PinnedSourceAuthority(
    store=owner_configured_strict_reader,
    snapshot_id=owner_snapshot_id,
)
result = inspect_pinned_candidate(
    manual_candidate,
    authority=authority,
    snapshot_id=owner_snapshot_id,
    manifest_key=owner_manifest_key,
    document_id=owner_document_id,
)
```

Full signature:

```python
inspect_pinned_candidate(
    candidate, *,
    authority,
    snapshot_id,
    manifest_key,
    document_id,
    as_of=None,
    registry=None,
    maximum_bytes=MAX_SOURCE_BYTES,
    include_support_text=False,
)
```

There is no new CLI configuration, store factory, acquisition route, latest-pointer discovery or credential manager. The caller supplies the existing authority and exact selectors. That owner-managed reader may perform its normal read-only authentication lifecycle; the adapter does not configure it or grant privileges.

The candidate's `document` must exactly equal:

```python
{
    "document_id": selected_native_document_id,
    "version": "sha256:" + native_raw_body_digest,
    "source_ref": selected_native_archive_url,
    "published_date": None,
}
```

A caller-provided replacement locator, version, document ID or publication date refuses. Native `filed_on` and `report_date` stay in their original DATE fields. They are not inserted as publication timestamps. Other candidate fields continue to use the existing closed manual-inspection contract.

The raw source cap remains 4 MiB and is checked against the native receipt before decompression. A filing over that cap is a refusal, not a truncated or rewritten original. This bounds the first implementation; coverage across large filings is not established.

## Native read sequence

1. Check bounded selectors and exact native `PinnedSourceAuthority` type. Compare the explicit pin to the authority's pin, then reconstruct the native authority over the same existing store. Caller-edited cached snapshot mappings, clocks and instance read-method overrides are not accepted as source authority.
2. Read one explicit archive manifest through native `read_file`; parse it with `manifest_from_json_bytes`; require that the owner's `manifest_storage_key` reproduces the selected key.
3. Select exactly one document by its native document ID. Duplicate/ambiguous selectors refuse. Require a stored document with its complete native retrieval receipt.
4. Check that the manifest recording clock and selected retrieval clock are no later than the pinned snapshot. These are source capture-causality checks using existing UTC validation, not a new Data OS knowability clock.
5. Call native `read_archive_document` with the exact storage key, complete expected receipt, finite raw budget and native compressed-byte ceiling. The owner reader independently reloads the retained sidecar, verifies complete receipt equality, reads the pinned gzip object and validates bounded decompression plus raw digest and length.
6. Strictly decode the actual returned original bytes as UTF-8 without modifying markup or newlines. Bind the candidate metadata and call the existing candidate inspector.
7. Return source witnesses only when the inner result is `INSPECTABLE`. Every refusal or exclusion suppresses `native_source_binding`.

No filing fan-out, source synchronization, persistence, earnings-event creation, identity allocation, graph materialization or publication occurs in this API.

## Temporal and rights behavior

An aware historical request can perform bounded source reads before the inner native-registry decision. Independent inspection observed seven bounded reads for the missing-registry case, followed by `AS_OF_REGISTRY_REQUIRED`; native binding and inner candidate/provenance/support views were all null. That read I/O is not a historical-system answer. Invalid DATE/naive cutoffs refuse without inventing an instant.

A supplied native row still tests only the existing candidate inspector's bounded mechanics. No registered SEC relationship profile or authenticated historical identity/source crosswalk has been established. This wrapper never relabels a retained snapshot or filing date as an adopted `known_at` clock.

The current GMI rights registry governs GMI emissions and does not retroactively gate existing source-owner products. Its unknown-family behavior is not a general retention, training, embedding or evaluation grant. This adapter adds no rights map or source-family admission. Downstream GMI/public emission remains an owner-specific unresolved use. Authorized private inspection and downstream publication are assessed separately.

By default, the dedicated replayed supporting text is omitted, but manual annotations can contain source prose. The output is not certified quote-free or public-safe and provides no public-export authorization.

## Verification and failure evidence

The focused native command is:

```bash
python3 -m pytest -q \
  tests/test_company_pinned_relationship_candidates.py \
  tests/test_company_relationship_candidates.py
```

Observed builder result: **150 passed**, exit 0, 8 unrelated pre-existing pytest temporary-directory cleanup warnings. The adapter suite uses wholly synthetic temporary native captures built through the native owner functions. It exercises the actual pinned reader, not a duck-typed replacement authority.

Meaningful cases include exact/alternate document selection, canonical manifest binding, duplicate document IDs, retained sidecar equality, compressed-object and raw-body corruption, gzip budget violations, invalid encoding, stale/forged cached authority fields, metadata substitution, source capture causality, identity/rights/authority preservation and absence of current source views on refusal or exclusion.

Missing-source, contract-integrity, archive-replay, access, bounded-read, unavailable-reader and unknown reader failures remain typed. Native exceptions are not reflected into output with host paths or credential details. Unknown transport/SDK failures never become a claim that the source does not exist.

An early test run intentionally revealed a distinction: appending tamper bytes hit the native LocalStore length cap before checksum comparison. The final suite uses same-length mutations for checksum assertions and separate manifest/sidecar/gzip overflow tests for `SOURCE_BOUNDED_READ_FAILED`. No integrity check was weakened.

The existing CI job runs both focused suites and declares their actual third-party test imports: pytest, PyYAML and requests. Initial inference identified 28 import/read paths but also broad runtime-input fallbacks. Hosted contract-delta correctly found that those fallbacks selected this job for three unrelated homepage/strategy probes and exceeded the existing packing ceilings. The repaired job uses an exclusive scope containing 68 actual inputs: all 28 inferred dependencies, the exact Micron case JSON, package initializers and their executed imports/configuration reads, shared pytest fixtures and their module imports, and the sparse-check collection hook. Independent inspection rejected an intermediate 36-input scope because it missed 32 of those inputs. Native selector probes preserve all 68 positive inputs and own-job semantic manifest invalidation, while excluding the three unrelated paths. The final independent repair review records its exact manifest hash separately from the earlier structural review. No global ceiling or unrelated job is changed; full exact-head hosted contract-delta remains the release gate.

## Actual retained-source proof remains open

The real Micron source-to-CLI replay remains a valid, separately recorded current file-input witness. It is not an `ffsecsrc_` retained-source witness.

The bounded availability check examined the owner-declared FF raw/archive/observations paths and exact operator config beneath both the canonical operation workspace and the known primary repository root. All four paths were absent in both locations. The four dedicated read-only reader configuration names were absent in the checked Studio Direct process environment; no values were read or published. No exact snapshot/manifest/document pointer was available.

These checks do not establish that a separately configured deployed runtime or private source bucket lacks captures. The real retained-store journey was **not run**. Source availability and production-reader ownership remain unverified. See [NATIVE_SOURCE_ADAPTER_SEAM.md](NATIVE_SOURCE_ADAPTER_SEAM.md) for exact scoped observations and primary code references.

The next real acceptance input is concrete: an existing owner-configured `StrictBoundedReadStore`, its exact `ffsecsrc_` snapshot ID, canonical filing-manifest key and selected document ID. In that owning runtime, replay one retained manifest → sidecar → gzip → original body → native flat span → candidate inspection, and retain the resulting non-body witness. Also execute a real unavailable/purpose-denied refusal where the owner contract supports it. Do not transmit credentials into a research artifact.

Only after that proof and native relationship/identity/temporal/source-purpose adoption should the incumbent GMI/K3-D/F04 owners connect admitted data to composition and product. This completed adapter does not release their held carriers or satisfy the subsequent predictive promotion gates.
