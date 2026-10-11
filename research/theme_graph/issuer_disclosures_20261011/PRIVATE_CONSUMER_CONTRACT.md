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

## Issuer selection for F04 composition

GET `/api/company-intelligence/private/issuers/{issuer_id}/product-integrations`
uses the same authentication, actual feature, fixed purpose and fixed audience.
The input is a canonical Data OS issuer ID; a ticker, caller-supplied CIK, event
ID or client-derived hash is not a verified issuer binding. The incumbent identity
owner must resolve the product's company context before this call. C01's current
Micron/NVIDIA bindings and their exact committed reference sources are recorded
in `C01_CURRENT_IDENTITY_QUALIFICATION.json`, without historical admission.

The response schema is `company_intelligence.private_issuer_selections/v1`:
generation, identity_mode=current, issuer_role=subject_disclosing_company,
issuer_binding (issuer_id, evidenced_cik, immutable identity_snapshot_reference),
and at most 16 sorted unique selections. Each selection contains fact_id, exact
fact_reference, exact edition_reference, kind=product_integration and
lifecycle=planned. Counterparty listings are not implied.

The trusted `SelectionOwner.resolve_issuer` capability supplies an independently
qualified current metadata generation, not arbitrary serialized HTTP data. Every
selected entry passes the native admission boundary before even constructing a
private Store. The reader then verifies the actual committed native artifact,
its issuer role, exact references and generation, rechecks selection, and
rechecks all admissions before serialization. The returned fields contain no
source/reviewer text, decision basis or grant booleans. A reference is discovery
metadata, not a permission token. A qualified empty generation returns an empty
list; missing runtime or unqualified owner metadata is unavailable.

F04 must retain the selection generation and references, call the fixed fact
reader, and compare the returned fact/edition references and generation before
display. A mismatch invalidates the composition; the caller cannot force an old
generation to remain authorized. The source owner must eventually publish its
selection projection through the incumbent Store/CAS pointer after the actual
native facts and owner decisions qualify. This producer/pointer and actual
source-owner resolver are not installed by this transport implementation. C01
therefore contributes no selected row yet.

The expanded transport suite passes 47 cases in 3.88 seconds, including exact
selection-to-fact composition on actual LocalStore, subject/counterparty
separation, duplicate/overflow/reference rejection before private I/O, empty
versus unavailable, selection and admission races, and rejected identity/old
generation overrides. All positive owners/authentication remain synthetic.


The independent composition review reproduced a cross-owner identity gap: two
otherwise valid current selections with the same issuer/generation could disagree
on the CIK or identity snapshot. Both regression cases first returned HTTP 200
instead of refusing. `Admission.subject_binding` now carries an explicit
`SubjectIdentityBinding`: issuer ID, evidenced CIK, actual snapshot schema/hash/
length, and the subject-specific decision revision. Selection requires this
binding and compares it before Store construction; the native reader compares
the fact's subject identity decision, and publication checks it before any I/O.
The aggregate `identity_revision` remains separate. The response names the actual
supplied snapshot schema; no new Data OS contract is implied. After repair, all
125 affected native, private transport and public API tests passed in 4.59 seconds.
Positive fixtures still prove source behavior only, not production qualification.

The correction review found no remaining architectural defect in that repair.
Production must verify the immutable subject decision record itself binds the
issuer/CIK/snapshot tuple; equality of unverified hashes is insufficient. The
installed production slice must provide this binding on publication and reads,
even though the base native API keeps it optional for existing callers.

The HTTP slice enforces that subject binding before Store construction. Both
HTTP and issuer composition pin the native reader to their original complete
Admission with `expected_admission`; a fresh owner preflight must match before
the first artifact read. A final equality check alone was insufficient: a
transient A-to-B-to-B-to-A downgrade could omit the native optional binding and
restore it before serialization. Both routes reproduced that failure, and now
refuse it before artifact retrieval. The affected native/private suite passed
108 cases in3.93s after repair; unchanged public API proof is reused. Independent
review accepted the pinning correction. The base native API remains compatible
with older callers, without weakening the production HTTP slice.

## Owner integration decision

Use one Company Intelligence adapter for `DisclosureAuthority` and
`SelectionOwner`, backed by the same qualified current generation. Reuse
`lib/dataos/registry.py` (validate before lookup), its incumbent temporal
vocabulary, `IssuerMaster` for evidenced current identity, and the bounded
versioned/CAS Store implementation. There is no adopted native disclosure
dataset row yet. Neither Research Vault's default Store factory nor its rights
catalog authorizes this domain's private bucket, audience or source.

The owner generation must reference and verify original dataset/adoption,
purpose, identity, temporal and correction records, exact published native
objects and issuer membership. An authorized producer advances the current
pointer only after native publication; the HTTP adapter receives read authority
only. Revocation, expiry, identity change and corrections must invalidate the
current metadata and final rechecks. No indefinitely cached startup allow,
caller-supplied grant or second rights registry is acceptable. This integration
requires real owner records and an approved private transport; no always-refusing
adapter constitutes production completion.


## Current company context query

GET `/api/company-intelligence/private/company-context?symbol=MU` is the additive
authenticated metadata edge. The same canonical authentication and fresh actual
feature check precede even reference metadata access. Only one `symbol` query
parameter is admitted. It must already be uppercase, 1–24 characters, and match
`[A-Z0-9][A-Z0-9.\-]{0,23}`. No caller vendor, market, CIK, ID, date or path is
accepted. The server fixes the namespace to the incumbent Data OS `store` current
alias space. A symbol is a query, never identity evidence. Punctuation is exact:
no dot/hyphen conversion, vendor fallback or invented venue. Unsupported aliases
and non-US-equity identities refuse. For the qualified committed bundle, `BRK-B`
resolves while `BRK.B` does not; `^NDX` is invalid for this company query.

The closed success schema is `company_intelligence.private_company_context/v1`:

```text
schema
identity_mode = current
query = {namespace: store, symbol: <validated input>}
security_id = <owner-resolved canonical SEC identity>
issuer_binding = {issuer_id, evidenced_cik, identity_snapshot_reference}
identity_receipt = {schema, identity_mode, issuer_id, evidenced_cik, source_commit,
                    sources, evidence_source, evidence_snapshot}
```

`identity_snapshot_reference` is `{schema, sha256, byte_length}` over the exact
UTF-8 receipt JSON (sorted keys recursively, compact separators, no ASCII escape).
Its schema is `company_intelligence.current_issuer_identity/v1`. `sources` contains
exactly `security_master`, `vendor_aliases`, and `issuer_master`, each with SHA256
and byte length of the immutable Parquet bytes. `source_commit` identifies the
owner-qualified compatible committed tree; `evidence_source=sec_company_tickers`,
and `evidence_snapshot` is the actual date-only source observation. The receipt
is at most16KiB and references the larger artifacts rather than relabeling them.
It deliberately excludes the query, security and evaluation time: share classes
of one issuer in the same bundle receive the same issuer receipt.

The independent installed `app.state.company_context_owner` supplies a currently
qualified `IdentityBundle` via `current_identity_bundle(purpose, audience)`. It
must establish exact compatible source-tree bytes before supplying the bundle
and re-resolve its current generation on every call; a constructor or hash alone
is no qualification. The pure composition hashes and parses the same bytes, uses
only `VendorAliasTable` and `IssuerMaster`, validates active/resolved securities,
canonical issuer kind, positive CIK, listing/alias roundtrips and compatible
issuer evidence. Both source observations must be valid dates no later than the
current UTC date. It rechecks the bundle and UTC date before returning, refusing
a midnight transition. No HTTP-supplied clock or historical identity is supported.

F04 must first obtain this context, then call the existing issuer-selection
endpoint and compare the entire issuer/CIK/identity-reference binding. A mismatch
invalidates the composed result; never force an older binding. The selection and
fact admission owner must use this exact receipt, or separately qualify a new
generation binding all three surfaces. The aggregate admission identity decision
remains distinct from this subject receipt. The new endpoint grants no disclosure
purpose and does not access the private artifact Store.

Errors retain the existing `company_intelligence.private_error/v1` envelope,
`automatic_retry_permitted=false`, and private/no-store headers. Authentication
and entitlement are401/403; malformed query is400 `REQUEST_INVALID`; missing
installed capability is503 `SOURCE_RUNTIME_UNAVAILABLE`; unresolved, conflicting,
future, changed or unsupported identity is503 `PRIVATE_SOURCE_UNAVAILABLE`.

Verification: independent review supplied five concrete canonical-ID/CIK/date/
midnight counterexamples; all five failed before correction. The affected native,
private and public API suites then passed160 tests. Canonical exclusive CI closure
is empty. Exact committed references and producer row counts were independently
checked for current MU/NVDA/GOOG/GOOGL/BRK-B resolution, exact BRK.B/^NDX refusal,
and shared GOOG/GOOGL issuer receipt equality. This is source/reference metadata
qualification only; no current owner is installed and no C01 rights or private
publication have been admitted.


Installed identity owner source continuation (2026-10-11): the HTTP context route
now has its own capability slot. `CommittedCompanyContextOwner(REPO)` is wired
alongside the existing router without constructing a disclosure authority,
selection owner or private Store. Its configured repository is the incumbent
application deployment root, not an HTTP input. Constructor installation performs
no I/O; authentication and the actual feature check still precede all Git reads.

On each resolution the owner verifies installed HEAD against the existing
`origin/main`, including detached protected installs. It selects the latest commit
touching the three references or their producer receipt, reads immutable objects,
and verifies all four blob IDs against installed HEAD. Thus unrelated source
installs do not change the identity receipt, while receipt-only corrections do.
The installed registry is independently checked for current adoption on every
resolution. Its exact contracts, producer receipt authority/consumer and counts,
whole-bundle canonical identifiers, alias references and active issuer census
must qualify. Superseded security rows remain stored but do not contribute to
issuer membership. Missing CIK on unresolved members is allowed; resolved or
evidenced active links require positive ten-digit matching CIKs.

Git repository/object/config environment redirection is removed. Explicit
`--no-replace-objects`, lazy-fetch suppression where supported, a present empty
`GIT_ALLOW_PROTOCOL` whitelist, bounded objects and command deadlines prohibit
transport retrieval. The actual API host uses Git2.43, which lacks the
`--no-lazy-fetch` command option. Its empty whitelist overrides per-protocol allow
configuration, including when lazy-fetch suppression is unavailable.
Missing objects, unsupported guards, unprotected ancestry, incompatible evidence
or a changing installed HEAD refuse. Cached immutable bundles remain contingent
on the current selector, all four object identities and the current registry.
The existing context reader also rechecks the owner and UTC date before return.

This adds the runtime implementation, not a VPS installation attestation. Real
postmerge installed-source selection and an authenticated context response still
must be verified. The context receipt must be bound by any future disclosure
owner; no disclosure purpose, C01 artifact, qualified empty selection or private
publication is created here. The response schema and fields are unchanged.


Git2.43 compatibility was checked against the real API host: the unsupported
option returned129; the deny-all environment returned128 with an explicit file
transport refusal despite `protocol.file.allow=always`. Local missing-promisor
regressions deliberately disable lazy-fetch suppression and allow file/custom
protocols: no remote helper starts, no object is retrieved, and all isolated
repository file hashes remain unchanged. The affected runtime suite passes32
cases after correction; the earlier190-case transport/native/public suite is
reused for unchanged boundaries. Independent reasoning review accepts this
compatibility repair. Reference: Git2.43's documented overriding protocol whitelist
at https://git-scm.com/docs/git/2.43.0#Documentation/git.txt-codeGITALLOWPROTOCOLcode.
The host was only inspected; source installation and authenticated API serving
still require postmerge proof. No Git upgrade, service restart or account change
was performed for these compatibility checks.
