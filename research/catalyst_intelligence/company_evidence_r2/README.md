# Catalyst Intelligence — Company source context R2

Status: implemented with bounded C3 source acceptance; DRAFT / HOLD. Source admission, production publication and activation remain unestablished.

Operation: catalyst-company-evidence-r2-20261019  
Source base: ec5c2e2544576f20348c6eadf834fe3cefae8039, the retained open draft BioCatalyst #6712.  
Carrier: a separate managed, stacked source operation; the incumbent #6712 repair remains preserved.

## User outcome

An issuer-disclosure case can carry an inspectable source document through the existing Company Intelligence event, BioCatalyst composer and authenticated API contracts. A user can open the document associated with the selected event revision. The interface must identify this as **source context**, with a task to review whether the passage supports the milestone.

This closes a concrete implementation gap. The previous Company event schema explicitly required empty public_evidence; the adapter preserved that empty field and the Bio composer emitted an empty evidence list. Merely changing presentation or copying the old list could not produce a citation.

A reproducible byte receipt establishes the quoted source address and identity association. It does not establish clinical validity, economic relevance, a favorable price response, or an attractive entry. Those remain separate research and admission decisions in the Catalyst stock-context program.

## Existing owners and the implemented path

| Responsibility | Existing owner reused | R2 behavior |
|---|---|---|
| Filing normalization, source URL and document identity | engine/fundamental_forensics/disclosure_diff.py | Consumes its typed DisclosureDocument; replays the same normalization to verify the document ID still binds the URL, metadata and exact body. |
| Company document and revision association | engine/company_intelligence/documents.py | Consumes the selected DocumentRevisionChain and its latest SourceDocument; retains existing event, document, filing and rights fields. |
| Exact text address | Company SourceSpan, text_span and verify_span | Replays the full UTF-8 source as segment zero, its body and segment hashes, byte range, citation hash and canonical span identity. |
| Catalyst event identity and wire validation | engine/company_intelligence/contracts.py and events.py | Preserves the v1.0 factory and empty evidence contract; adds explicit v1.1 consumption and attachment. |
| Source-context projection | engine/company_intelligence/catalyst_evidence.py | New pure module within the existing Company owner. It does not create a store, collector, event bus, issuer identity or publication pointer. |
| Bio projection | engine/biocatalyst/company_event_adapter.py and what_matters_next.py | The existing adapter retains validated evidence; one separately identifiable composer hunk carries it into the row. |
| Serving and access | Existing app/biocatalyst.py handlers | Actual list and detail integration tests exercise the current private/no-store API and its selected generation. |

No fiscal event workspace is used as a non-fiscal catalyst producer. The generic filing normalizer already serves the existing release-binding owner; this projection reuses its document identity and source bytes without invoking financial extraction or inventing a fiscal period.

## Versioned contracts

The existing company_catalyst_event.v1 schema at version 1.0.0 remains unchanged on disk and continues to reject nonempty public evidence. Existing callers of project_catalyst_event retain that behavior.

A new company_catalyst_event.v1_1.schema.json mirrors the Python validator's explicit schema_version 1.1.0 branch. It admits only the closed company_catalyst_public_evidence.v1 object. The public evidence contract itself is version 1.0.0. Event revision, document revision and projection schema version are distinct fields.

The producer accepts typed owner records and a selected event, rather than echoing a caller-supplied revision string. Its checks require:

- The Company document chain belongs to the selected event.
- The selected document is included in that event's document_refs.
- The filing, Company document and SourceSpan identify the same document.
- The span version equals the selected Company document revision.
- The Company filing CIK and accession match the normalized filing and the event issuer.
- The source URL retains its existing document identity binding.
- The full body reproduces the document and segment hashes.
- The selected text range reproduces the existing receipt and canonical span identity.

The wire carries source context, not a supports/confirms/contradicts claim. Assets and relationships still retain their withheld semantics; probability, materiality, historical response and incorporation remain NOT_ESTIMABLE. No material-change clock is manufactured.

## Public projection and rights

The first slice exposes a bounded SEC source URL and structured provenance. It requires the existing document's public_primary state and rp_public_primary_v1 profile, with the same profile on the span. These are **consumed owner records**, not grants minted by this function.

The URL is taken from the normalized DisclosureDocument. It must be an HTTPS SEC Archives document locator whose CIK and accession match the selected filing. A new URL cannot retain an older document ID, because URL and body metadata participate in the existing normalizer's identity.

Only this declared SEC document slice is implemented. Other source domains need their own compatible owner projection, rather than a permissive arbitrary-URL adapter.

The excerpt field is always null. This new port does not treat public availability or a profile label as permission to redistribute source text. The raw body, receipt object, private source locator, filesystem paths and arbitrary extension maps do not enter the public evidence record. A 16 MiB body cap bounds this implementation; it is a resource limit, not a coverage or scientific qualification claim.

The function is internal to the source owner and must not become a public evidence-upload API. A valid serialized object does not independently establish intake custody, source rights, publication acceptance or operational availability. Those remain with the existing owners.

## Time and corrections

The filing calendar date remains a date. It is not promoted to a guessed publication instant. Source availability and fetch/observation clocks come from the selected Company document record and are kept distinct from the event's observation and the evidence projection cutoff.

The evidence wire and explicit Company v1.1 event use UTC timestamps with at most six fractional digits. Subsecond source and parent-event knowledge is retained; longer fractions are refused instead of being silently rounded backward by a parser. The new port checks its generation cutoff with the same rule. The original v1.0 clock normalization remains unchanged.

When this port consumes a v1.0 event, it first validates the original empty-evidence contract, then validates a detached internal selection under v1.1 using the original supplied clock literals. This cannot smuggle nonempty evidence through v1.0 or recover precision that an upstream owner has already discarded. A same-second observation witness preserves the source's 100001-microsecond and event's 200001-microsecond timestamps through attachment and the real API.

For the admitted source-context record:

source availability <= source observation <= selected event observation <= projection cutoff

A consumer additionally requires the evidence projection cutoff not to exceed its selected generation cutoff. Fresh attachment requires the exact same projection cutoff, so an older citation cannot be silently relabelled as a fresh composition. Later valid reads may consume the retained record without advancing its source clocks.

These are current owner-record bindings. They do not qualify a historical issuer join, backtest, market-onset comparison or earliest-public-information reconstruction.

The source projector rejects a superseded document, a duplicate delivery, a non-current event revision, and cancelled or withdrawn event occurrences. For a corrected document, the existing revision chain and selected event must supply the successor. Tests show that the event identity can remain stable while the document hash, document revision, span and event revision change; an old citation cannot be attached to the new event revision.

A source-provenance test does not replace the outstanding production requirement: after a correction is admitted, the existing publication transaction must fence dependency generations so an older recomposition cannot restore obsolete current content. This slice adds no second correction ledger or publication selector.

## Verification

The focused evidence suite exercises actual owner functions, the Bio adapter/composer, and the real API handlers with explicitly synthetic inputs and the existing test authentication override. It checks:

- Exact source/body/URL/document/span association.
- v1.0 compatibility and the two new machine-readable schemas.
- Unknown, licensed, internal-only and mismatched rights profiles.
- Missing or altered bytes, partial segment zero and forged span identity.
- Incorrect event, issuer, accession, document or revision associations.
- Source clocks after the selected event and incompatible projection cuts.
- Duplicate citations, unapproved excerpts, extra private fields and authority promotion.
- A successor document with a stable event identity and a different citation.
- Same-generation API list/detail evidence and bounded refusal of a mismatched record.

The API fixture uses an in-memory test projection and a synthetic current identity cut. It is not a native source-admission receipt, live account/entitlement proof or deployed publication transaction. No network collection is performed.

Tests are registered in the existing biocatalyst-contracts CI job, alongside the original Company event tests. No new job, packing ceiling, gate exemption or authority waiver is introduced. Exact execution receipts and source hashes are recorded in verification.json.

## Custody and integration

The legacy repair checkout remains at the retained #6712 head with four dirty test files:

- tests/test_biocatalyst_what_matters_next.py
- tests/test_biocatalyst_wmn_api.py
- tests/test_biocatalyst_wmn_publication.py
- tests/test_company_intelligence_catalyst_event.py

This operation does not write to that checkout or adopt those changes. It adds a new test file in a separate registered workspace. Its one-line WMN integration hunk changes only the evidence value, without implementing or claiming the incumbent timing, identity-cut, future-cut, estimate-coverage, stored-error or template synchronization repairs.

The source carrier remains a draft with a release hold. Integration requires the retained Bio repair to be reconciled, the dependent interface adapter to be accepted, and the existing source/publication/access owners to supply a qualified native case. The R1 stock-context consumer remains separately scoped and retains its existing NewsImpact and B4 authorities.

## Next capability

The next useful release case is a real admitted issuer disclosure whose changed claim can be reproduced from its prior and current source revisions, with a correct issuer/security binding and an inspectable document. A later correction must withdraw or revise the current interpretation through the same publication and interface path.

This citation port is one dependency of that case. Claim support, economic exposure, peer-context qualification and executable entry research remain explicit additional dependencies.
