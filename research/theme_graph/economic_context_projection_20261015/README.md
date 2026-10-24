# GMI native economic context: implemented read projection

## User and machine capability

`engine/theme_graph/economic_context.py` gives GMI an on-demand, read-only view
of a native admitted planned product-integration fact. It consumes the existing
Company Intelligence disclosure reader and authority rather than accepting an
untrusted fact dictionary, minting a supplier edge or publishing another graph.
The same structured result is usable by an authenticated human-facing consumer
and a machine consumer. No production route is installed by this increment.

The source is intentionally useful before quantitative propagation: explain
who disclosed the product integration, preserve component/platform scope and
source timing, expose the exact current native fact/edition/generation handles,
and give an explicit refusal when a trustworthy view cannot be formed.

## One ownership and access path

The caller first performs its EXISTING authentication and feature entitlement
check. It supplies the adopted `DisclosureAuthority`, the native read-only
store, and an existing `issuer_disclosures.Request` with the intended
purpose/audience. The projection cannot create or select a new authority.

1. Native metadata preflight qualifies the exact request, source owner, rights,
   identity, temporal and correction decisions. Before any private artifact
   read, the projection requires all fields needed for a complete relationship
   view to be permitted by that native grant.
2. `read_disclosure(..., expected_admission=admission)` pins the decision,
   authenticates the retained bytes against native references, checks revision
   slots and correction chains, and rechecks the same owner after the reads.
3. The projection accepts only the existing private reader schema and the exact
   fact/edition/generation bindings. It copies a fixed field set into a fresh
   result. There is no cache, source lookup, callback, retry or write operation.
An existing composing caller may pass its already-qualified native Admission
via `expected_admission`. That skips only the extra composing lookup: the
native reader still resolves its actual owner before and after reads and
rejects a mismatched, revoked or changed decision. A supplied pin is not an
authentication or freshness token.

4. Native refusals retain their stable reason codes. Unavailable output has
   `context: null`: no partial parties, old positive, reference, generation,
   requested identifier, source prose, private path or exception message leaks.

The injected source owner is a trusted host boundary, not a caller-supplied
permission token. Synthetic authorities in unit tests are NOT live admission.
A hash or well-formed reference is not itself proof that a source exists.

## View contract

The response schema is `theme_graph.native_economic_context/v1`:

- `status`: `available` or `unavailable`; `reason`: null or bounded reason code.
- `context.usage`: native-qualified purpose and audience, retained as scope
  metadata, not a permission token or a replacement entitlement check.
- `context.relationship`: native kind/lifecycle, subject and object issuer IDs,
  product/platform scope, amount and economic_share. Amount/share remain null.
- `context.provenance`: original fact ID/revision, native reference, edition,
  and native generation. No new identity or graph-row namespace is minted.
- `context.timing`: distinct source date, nullable publication instant,
  publication precision, edition-known and fact-known instants, native identity
  mode, requested query mode and nullable cutoff. No newly generated timestamp.
- `context.mapping`: native-fact context only; both a legacy theme-graph edge
  and a propagation hypothesis are explicitly null. The missing adopted mapping
  is stated, not filled with a renamed integration identifier.
- `context.limitations`: current planning, current commerce, fulfilled shipment, economic
  sensitivity and inferred historical identity are not established.
- `authority`: `context_only` in every outcome.

A source-disclosed plan is not proof of current planning or fulfilled commerce.
The first species is strictly `product_integration` / `planned`; customer,
supplier, ownership, competitor, thematic and correlation constructs are not
inferred. C01's 2024 publication date cannot replace its 2026 fact-known clock,
and a current-identity admission cannot become a historical replay permission.

## Failure behavior

Missing field permission refuses BEFORE artifact I/O. Owner denial, revocation,
request mismatch, invalid historical eligibility, absent/corrupt native objects,
changed generation, missing revision slots and invalid correction chains retain
the native refusal. Unsupported native reader shape or unmapped species never
becomes a guessed partial positive. The view neither writes nor retries.

## Validation scope

The tests execute the REAL native reader over an in-memory synthetic native
store, exercising its immutable reference and revision-chain behavior. One case
reuses the already committed C01 fact metadata, verifies its exact native refs,
and projects it through an explicitly synthetic authority/store. That is a
source-grain witness, not a production-source acquisition or entitlement proof.
Counterexamples cover field grants before reads, post-read owner changes,
request/audience substitution, historical cutoffs, corrupted or absent bytes,
revision bindings, writer-free consumption, response drift and copy isolation.

The integration suite also exercises the ACTUAL `CurrentDisclosureOwner` and
`ReadOnlyLocalObjects` against the existing native synthetic publication harness,
including revocation and historical-route refusal. Temporary local generations
are isolated test fixtures; the accepted production generation is not touched.

The sole test execution home is the existing code-gated
`company-relationship-candidates` CI job. This adds one suite and the necessary
scope paths, not another runner/controller or relaxed test budget.

## Integration and custody

This independent source increment implements the WP01/WP05 read-projection seam
from the accepted economic-network architecture. It does not change the existing
Company Intelligence private response, API router, dataset registry, current
pointer, producer, source identities, K3-D generator registry or legacy GMI edge
schema. It does not depend on ownership-inspector release or amend its blocked
release operation. K3-D #6514 remains on its own source/release carrier.

The original F04/E20 owner retains private runtime/API/Terminal deployment.
The accepted C01 STAGE/adoption/PROMOTE generation040b is DO_NOT_REDO. A host
consumer may adopt this view only through its existing release and access path.
Actual authenticated positive/refusal UI and machine parity remain unproven
until that owner installs and verifies the consumer. No API retry, publication,
third-party source acquisition, security grant or new runtime worker occurs here.

The local managed operation is
`gmi-economic-context-projection-20261015-sol-001`, based on Macro
`05ea40d5557939bf557d7ce3b74f7f5c2a74aa50`. The current Chairman continuation
supplies source-work authority; native release/access boundaries remain intact.
