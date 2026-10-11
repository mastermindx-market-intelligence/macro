# Native issuer disclosures: private consumer contract v1

The source owner is Company Intelligence. The implementation is
`engine/company_intelligence/issuer_disclosures.py`. It represents a standalone
issuer disclosure and its separately reviewed `product_integration` fact without
inventing an earnings period, SEC accession or corporate-action identity.
`SourceDocument.v1`, the accepted relationship-observation implementation, and
the economic kernel remain unchanged.

This is an implemented source contract and mounted HTTP source boundary, not an
installed production resolver, entitlement or source-purpose grant. C01 remains NOT_ADMITTED.
The source changes permit the incumbent F04 owner to implement its private
boundary against a concrete versioned interface while real source qualification
continues. A synthetic authority in tests is never a production authority.

## F04 order and interface

1. Authenticate through the incumbent session authority.
2. Check the actual `company_intelligence_private_read` feature as issued by the
   existing entitlement authority. A Pro label alone is insufficient.
3. Construct `Request(fact_id, purpose, audience, mode, as_of)` from trusted
   server-side purpose/audience policy and validated query input. Current requests
   have no supplied cutoff; historical requests require an explicit offset-aware
   instant with at most microsecond precision.
4. Use the source-owner `DisclosureAuthority.resolve(request)` for metadata-only
   adoption, purpose, identity, time, correction and current-generation selection.
   `preflight(authority, request)` requires no store and performs no private I/O.
   A denial or resolver error must stop before private storage is touched.
5. Call `read_disclosure(store, authority, request)` with the incumbent private
   Store. It repeats admission, verifies exact content references and native
   revision bindings, walks both bounded predecessor chains and rechecks the
   admission generation before returning constrained fields.
6. Serialize the closed result without adding source/reviewer text or public R2
   fallback. The browser and machine consumer must observe the same immutable
   references and generation. Actual authenticated serving remains a separate
   production acceptance obligation.

The returned schema is `company_intelligence.private_product_integration/v1`:

```text
schema, fact, reference, edition, generation, authority="context_only"
```

`fact` contains only the source-owner field grant, selected from `fact_id`,
`revision`, `kind`, `lifecycle`, `subject_id`, `object_id`, `product`, `platform`,
`amount`, `economic_share`. `fact_id`, `kind`, `lifecycle` are mandatory;
`kind=product_integration`, `lifecycle=planned`, and both magnitude fields are
null. The result contains no evidence quotation, reviewer narrative or arbitrary
metadata. Each reference is the exact schema, SHA256 and byte length.

`DisclosureError.code` is safe bounded machine output. All such errors prohibit
automatic retry. `effect_unknown=true` on a write means reconciliation of the
same operation is required; it does not mean the write failed or permit a
replacement publication. Consumers must fail closed on any unknown code.
Authentication and entitlement failures remain F04-owned and precede this API.

## Real owner obligations

The trusted resolver must supply an actual `Admission`, binding the exact request
and immutable fact/edition references to a dataset/profile, current generation,
and immutable adoption, purpose, identity, temporal and correction decisions.
These decision digests identify independent owner records; they are not tokens
or a mechanism for a caller to grant itself permission. Production wiring must
never deserialize an Admission supplied by a web caller.

The owner must qualify the source and fact species, adopt its dataset/profile,
resolve legal parties for the appropriate time, resolve source and judgment
corrections, decide permitted audiences/purposes/fields, and select the current
artifact. None of these is installed by a fixture or the mere existence of a
private content blob. Date-only publication remains date-only and cannot support
instant-granular historical replay. Historical reads require both instant
publication and historical identity; current reads do not assert those rights.

Publication uses a separate `authorize_publication(request, candidate)` decision
whose operation is `publish`; read authority cannot authorize writing.
`publish_disclosure` receives a trusted `DisclosureSourceReader` with exact
disclosure/edition/body digest and length, and a one-MiB maximum that the source
transport must enforce before buffering. It verifies an exact UTF-8 source span
through the existing Company Intelligence receipt owner. Production source
transport is still to be installed and qualified; this capability does not fetch
URLs or choose credentials.

## Native revision and storage semantics

Source editions use `company_intelligence.issuer_disclosure_edition/v1`; reviewed
facts use `company_intelligence.product_integration_fact/v1`. Their separate
chains preserve the difference between a corrected disclosure and a changed
judgment. Stable disclosure identity uses the legal issuer and original native
source key; stable fact identity uses disclosure identity and claim key.

The incumbent Store owns create-only writes under
`company_intelligence/issuer_disclosures/v1/`. Content objects are immutable;
atomic per-identity revision bindings admit one content reference per revision.
Two concurrent sibling publications cannot both win the same native revision.
A losing publication may leave an immutable content blob; readers still refuse
it because its native revision binding does not match. A lost acknowledgement is
reconciled by exact readback, never by blind write retry. Chains are bounded to
64 revisions, objects to 16 KiB, and source retrieval to one MiB.

Initial publication observes four conditional objects (edition, edition binding,
fact, fact binding). A judgment-only correction adds only the fact and its
binding. Repeating an unchanged publication and all private reads perform zero
writes. Production R2 conditional capability and real-source adoption still need
their own proof; the completed tests qualify actual LocalStore and this contract.

## Verification and remaining delivery

The new suite passed 49 cases. Two discriminating regressions first failed on
sibling revision reuse and missing predecessor reads; both now pass. Tests also
exercise actual LocalStore concurrent siblings, lost acknowledgements, immutable
repeat/read, rejection of a losing orphan blob even when selected by a resolver,
auth-metadata refusal before private I/O, generation revocation, separate read
and publish authority, time precision, correction identity and source bounds.
An independent native reasoning coordinator critiqued the architecture and
reviewed the repairs; it did not execute these tests or attest production.

The existing `company-relationship-candidates` CI job enrolls the new suite and
its five additional closure paths. Canonical job-scope inference found all 76
paths covered, without changing the curated job inventory or other definitions.
Natural hosted CI and ordinary release must pass on the published head.

Completion requires an actual source-owned adoption/purpose/identity/time/
correction resolver and current private artifact, F04's real entitlement and
private route, an authenticated source-backed positive and refusal, and matching
human/machine production evidence. No public teaser publication, commercial
magnitude, graph promotion, cohort certification or trade authority is implied.

## Fixed private HTTP boundary

`app/company_disclosures.py` mounts GET
`/api/company-intelligence/private/product-integrations/{fact_id}` in the existing
Macro application. Bearer and shared-cookie callers use `app.main.require_user`.
The handler reads the actual entitlement row freshly, requires the exact
`company_intelligence_private_read` feature with active/trialing and nonfree
semantics, and does not reuse another feature's paywall cache or a Pro label.
All successful and failed handler outcomes are private/no-store; failures carry
a bounded code without upstream details.

Only `mode` and `as_of` are query controls. Unknown or duplicate parameters are
rejected after authentication and entitlement. The server fixes purpose to
`private_company_intelligence_context` and audience to
`company_intelligence_entitled`; a future positive owner receipt must cover
that entire audience. A grant limited to one operator, customer or tenant cannot
be used through this audience without a separately qualified narrower binding.

The installed capability slot is `app.state.company_disclosure_reader`, an exact
`PrivateDisclosureReader` instance containing the trusted owner resolver and a
lazy incumbent Store factory. Preflight precedes even Store construction. The
native reader verifies admission before retrieval and again before serialization.
The browser cannot set this slot, deserialize an Admission, choose a root or
publish an artifact. Missing runtime is `SOURCE_RUNTIME_UNAVAILABLE`; denied
admission never constructs the private Store. No production capability has been
installed by these source changes.

The 28 new transport tests passed, then the unchanged public API plus private
transport suite passed 49 tests in 4.90 seconds. These include actual app mounting,
actual LocalStore reads with immutable references, fresh entitlement revocation,
cookie forwarding, query injection/duplicates, generation changes, absent runtime,
and no-store sanitized errors. Authentication and owner grants in those tests are
synthetic. The tests are enrolled once in the existing `prelaunch-hardening` API
job; no new CI job or threshold is introduced. Independent architectural critique
found no make-or-break authorization defect; its final-recheck comment correction
was applied. Real resolver installation, source-owner purpose and dataset adoption,
current private artifact, deployment, and authenticated positive/refusal proof are
still required.
