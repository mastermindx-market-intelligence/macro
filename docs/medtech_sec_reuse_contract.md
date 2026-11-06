# SEC evidence reuse for the MedTech continuation

Status: **source-owner discovery and proposed consumer boundary only**. The current R14 runtime does not resolve FDA applicants to listed issuers or qualify their economic rights. No SEC retrieval, new collector, source-store creation, issuer assignment or production activation occurred in this review.

## Existing owners and reusable contracts

The census was pinned to Macro `5f2233c41d7f9560eb26afa5597859c11b6c0ac7`. The following are observed repository contracts, not a claim that a new MedTech consumer has been admitted.

| Existing owner | Reuse boundary |
| --- | --- |
| [SEC document spine](https://github.com/mastermindx-market-intelligence/macro/blob/5f2233c41d7f9560eb26afa5597859c11b6c0ac7/engine/fundamental_forensics/sec_document_spine.py) | `canonical_cik`, `sec_document_id`, validated manifests, canonical receipt/storage identities and bounded retained-byte reads. It is an evidence contract and carries no device-rights interpretation. |
| [Archive acquisition and retention](https://github.com/mastermindx-market-intelligence/macro/blob/5f2233c41d7f9560eb26afa5597859c11b6c0ac7/collectors/sec_document_spine.py) | The existing collector owns HTTP acquisition and persistence. `find_reusable_primary_retrieval` lives here and returns a verified prior receipt verbatim, preserving its original observation clock. |
| [Shared SEC request pacer](https://github.com/mastermindx-market-intelligence/macro/blob/5f2233c41d7f9560eb26afa5597859c11b6c0ac7/collectors/sec_request_pacer.py) | One injected `SecRequestPacer` coordinates requests inside a process. The default interval is 0.12 seconds and the constructor floor is 0.1 seconds. This is not a cross-process or cross-host budget. |
| [Broad SEC source store](https://github.com/mastermindx-market-intelligence/macro/blob/5f2233c41d7f9560eb26afa5597859c11b6c0ac7/engine/fundamental_forensics/broad_sec_store.py) | `live_fetchers` supplies the same pacer to its existing submissions and Company Facts collectors. A MedTech consumer must use the admitted existing owner and its retained source selectors; a new source store is not implied. |
| [Pinned relationship candidate inspection](https://github.com/mastermindx-market-intelligence/macro/blob/5f2233c41d7f9560eb26afa5597859c11b6c0ac7/engine/company_intelligence/pinned_relationship_candidates.py) | `inspect_pinned_candidate` inspects one exact retained document through an exact `PinnedSourceAuthority`. It is the existing bounded inspection entrance for candidate prose. It remains private and `NOT_ADMITTED`; it does not resolve canonical identity or rights. |
| [Filing attestation](https://github.com/mastermindx-market-intelligence/macro/blob/5f2233c41d7f9560eb26afa5597859c11b6c0ac7/engine/fundamental_forensics/filing_attestation.py) | `ffatt_` binds one `ffpkg_` / `ffxbrl_` pair to pinned source evidence and parser replay, with an optional exact projection of a dimension-known-empty numeric iXBRL fact into a captured Company Facts response. A restored artifact requires `verify_filing_attestation_source()` before relying on its positive source-presence or projection claims; loading or validating it alone proves canonical self-consistency. Its object-presence claim covers the index and selected member, not every inventory document. It does not certify arbitrary licensing passages or economic rights. |

The pacer's own contract leaves cross-process serialization with the existing `filing-forensics-sec` workflow group and aggregate per-IP limits with the scheduler. This review did not inspect or exercise a new consumer's admission to either. Reusing a class does not establish aggregate rate compliance.

## Document identity and clocks

Native document identity combines canonical ten-digit CIK, exact accession, role and document name. A ticker or applicant-name match cannot substitute for that identity.

Keep the source clocks separate:

- `accepted_at`: the spine's SEC acceptance/source-event timestamp.
- `filed_on`: the date-only SEC filing label.
- `recorded_at`: when the source plane retained the manifest.
- `retrieved_at`: the actual HTTP observation recorded by the retained document receipt.
- The pinned snapshot's time and any requested historical case cutoff: separate constraints evaluated by the existing owners.

A retained read must not restamp `retrieved_at` as a new download. The existing reuse helper preserves the original receipt, including its ID, ETag and observation clock. It verifies sidecar/body identity and refuses an ambiguous content identity. A previous missing-document response is not reused as permanent absence.

`manifest_content_key` excludes run/observation clocks while retaining content digest, byte length and storage identity. Therefore an unchanged recapture must not manufacture a new MedTech filing development. Amendment relationships inferred from form and report period remain inferences; cite the exact accession/document used rather than silently transferring a passage to an inferred predecessor.

These clocks do not independently establish registered `known_at`, historical served state, canonical as-of issuer identity or when a claimed economic relationship became publicly knowable.

## The existing candidate inspection entrance

A prospective MedTech inspection should supply the incumbent reader plus explicit `snapshot_id`, `manifest_key` and `document_id`, without discovery or filing fan-out. The existing `inspect_pinned_candidate` implementation:

1. Reconstructs the exact native authority over its supplied store and validates the manifest selector.
2. Requires one stored native document, a verified receipt sidecar, bounded bytes and an exact raw digest/length.
3. Requires candidate metadata to match native document ID, archive URL and `sha256:<raw digest>` version, with `published_date=null`.
4. Passes the exact UTF-8 body to the incumbent relationship candidate inspector.
5. Exposes a native source witness only for an inspectable result, while preserving `NOT_ADMITTED`, no Graph1 projection and false rank/gate/size/trade/prediction authority.

This proves custody replay relative to the supplied reader. It does not independently authenticate the reader's production ownership or SEC authorship, validate a manual annotation's interpretation, certify public-safe text, establish economic truth or authorize publication. The source explicitly records those gaps. Do not turn its successful inspection into an issuer-assignment or rights seal.

The `PinnedSourceAuthority` reader is shared infrastructure. Its use by this candidate adapter does not broaden `ffatt_` into a prose-attestation API. The candidate adapter deliberately emits no `ffatt_` or identity/rights seal.

## Proposed bounded next increment

The current [relationship-candidate v1 schema](https://github.com/mastermindx-market-intelligence/macro/blob/5f2233c41d7f9560eb26afa5597859c11b6c0ac7/engine/company_intelligence/relationship_candidates.py) has a closed set of supported kinds. It includes product integration and framework agreements but no typed device-license or territorial-economic-rights claim. Do not encode a device license as a framework agreement to imply unsupported rights coverage. Reuse its custody and `SpanReceipt` replay machinery; any new licensing semantics require an explicit schema extension and qualification by the existing company-intelligence owner.

First qualify a read-only MedTech consumer of one already-retained, owner-supplied SEC document and one manually reviewed candidate of a supported kind. An unsupported licensing case requires an accepted owner schema extension first. Retain native selectors, exact source digest and separate clocks. Keep applicant similarity as a candidate-generation signal only.

An accepted rights claim still needs evidence binding the exact device, applicant, submission, indication, territory, issuer/security and retained relationship, including license-term identity where relevant. Commercialization and materiality require separate evidence. The [existing MedTech backend contract](https://github.com/mastermindx-market-intelligence/macro/blob/5f2233c41d7f9560eb26afa5597859c11b6c0ac7/docs/medtech_backend.md) already assigns this work to the company-intelligence owners; Company Facts alone does not prove device-level rights or revenue.

Before implementation admission, resolve:

- The existing production source reader and exact snapshot selectors available to this consumer.
- The incumbent relationship candidate schema, issuer registry and native temporal/rights admission path for the proposed case.
- Purpose-specific retention/display rights and whether any quoted filing text may leave the private inspection boundary.
- Whether additional acquisition is necessary; if so, explicit admission through the incumbent collector, shared request budget and scheduler.
- Missing, ambiguous, mismatched, amended and temporally ineligible evidence behavior, with discriminating fixtures.

No parallel issuer registry, SEC collector, attestation format or source store is proposed. The earlier research proposals retain their own review conditions as recorded in [the CMS continuity note](medtech_cms_source_contract.md#continuity-with-the-existing-research-proposals).

## Review provenance and limit

A bounded paid-worker census inspected eight existing source files at the pinned commit. The owner independently verified all eight blob identities and the relevant pacing, manifest, retained-read, attestation and MedTech ownership code, then inspected the incumbent pinned relationship adapter. The worker's suggestion to use filing attestation as arbitrary passage-level authority was not adopted. This document records the corrected source boundary; worker completion alone is not production or consumer acceptance.

This is documentation only. It does not claim a tested or deployed MedTech-to-SEC integration, a resolved issuer relationship, a source-coverage denominator, economic materiality, a forecast or a recommendation.
