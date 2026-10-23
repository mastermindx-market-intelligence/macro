---
workstream: "WS:FINANCIAL-INTELLIGENCE-FABRIC"
session: claude/fif-3a4-cross-filing-lineage-impl
model: opus
ended_because: complete
prs: [7518]
mission: >
  Implement FIF-3A4 — cutoff-visible cross-filing fact lineage — through the
  existing Financial Intelligence Fabric query path, prove it on the frozen
  AAPL A1/A2 golden pair, run it through the existing service/API path, and
  land one user-facing journey with browser proof. No second fact ledger,
  lineage DB, revision store, metric registry or query kernel.
state_before: >
  FIF-3A4R was ACCEPTED_ARCHITECTURE / ON_MAIN / NOT_BUILT per
  DEC:FIF-3A4R-CROSS-FILING-LINEAGE-ACCEPTED-ON-MAIN. Comparative
  total_assets instant 2025-09-27 was NOT_EVALUABLE with reason
  "unlinked source vintages require an explicit typed revision lineage"
  because A1 and A2 are two unlinked FILED roots.
changed:
  - path: engine/fundamental_forensics/lineage_evidence.py
    what: >
      New module. The accepted §5 v1 positive rule (twelve guards), the
      immutable fif3a4r.lineage_evidence_receipt/v1 receipt, and
      derive_confirmation_receipts, which mints positive receipts from source
      filings only. The A4R research census JSON is never imported or read.
  - path: engine/fundamental_forensics/query.py
    what: >
      The single authorized product change. _select_source_group now resolves
      each root through an effective-root map built from cutoff-visible,
      still-provable confirmation receipts. Adds _admit_lineage_evidence,
      _receipt_still_proves_confirmation, _visible_accession_group,
      _accession_group, _effective_roots and the read-only
      applied_lineage_evidence disclosure. Absent evidence allocates nothing
      and changes no byte.
  - path: engine/fundamental_forensics/query_service.py
    what: >
      FinancialQueryDataset gains lineage_evidence, default empty, passed
      through to the kernel. The envelope gains an evidence-gated "lineage"
      section so a user-facing answer can name the filing that supports it.
      It is outside "receipt", so query_hash is untouched.
  - path: engine/fundamental_forensics/ixbrl_raw_ledger.py
    what: >
      original_concept_namespace_uris reads the original Clark namespace URI
      back from the committed package for guard 11, which the canonical ledger
      does not retain. GoldenAaplFinancialQueryProvider takes an optional
      lineage_evidence_available_at; absent is exactly FIF-3A3.
      FIF3A4_LINEAGE_AVAILABLE_AT is the committed system clock.
  - path: app/forensics.py
    what: >
      The existing /financial/query provider attaches lineage evidence at the
      committed clock. No new route, no new API, delivery unchanged.
  - path: site/financial_lineage.html
    what: >
      One user-facing journey over the existing endpoint - point-in-time
      question, three policies side by side, repeated-vs-revised verdict, and
      an evidence drilldown onto the immutable receipt.
  - path: tests/test_fundamental_forensics_cross_filing_lineage.py
    what: >
      The accepted §9 discriminating battery plus forged-taxonomy and
      chained-third-filing attacks. 27 tests.
  - path: tests/test_fundamental_forensics_ixbrl_raw_ledger.py
    what: >
      Releases query.py from the A4R research wave's byte-freeze, which was
      that wave's self-restraint and is the exact file §10 authorizes A4 to
      change. raw_ledger.py and metric_registry.py stay byte-frozen, and the
      accepted A3 hashes remain asserted directly in the same file.
verified:
  - claim: The accepted A3 ledger identity is unchanged, with and without evidence.
    command: parse_and_convert_golden_packages(GOLDEN_AAPL_QUERY_ACCESSIONS).ledger_sha256
    result: ba149bd55d929d843f353e91bbf68147791fb8b4a20c258426ea2eb7527019d8 in both cases.
  - claim: Absent evidence is byte-identical FIF-3A3/FIP1.
    command: execute_financial_query on the golden 4-metric/4-period request at the A3 cutoffs
    result: >
      response SHA 58972cb88f82483e86acc9d9fc3b1cbce046f466ff8665ae214909d90ab078b0 and query hash
      f8f6dc3134592c817001738cbdefb09ee1b71798ef24a8e64dc75685a6f9c7a1, with and without an
      attached bundle. No "lineage" key is emitted.
  - claim: The runtime rule reproduces the accepted A4R AAPL calibration from source.
    command: derive_confirmation_receipts over the A1/A2 ledger
    result: >
      130 positive receipts over 133 overlapping logical keys; 93 dimensioned and 37
      empty-dimension retained; OtherAssetsNoncurrent (changed_value), LongTermDebt
      (precision_consistent_unconfirmed) and CommitmentsAndContingencies
      (nil_confirmation_unspecified) each refused exactly once.
  - claim: The three point-in-time states behave exactly as the accepted clock law requires.
    command: POST /api/forensics/v1/financial/query for total_assets instant 2025-09-27
    result: >
      At recorded_at 2026-08-23 all three policies stay NOT_EVALUABLE with the accepted unlinked
      vintage reason. At recorded_at 2026-09-20 LATEST_KNOWN_AS_OF is VALUE 359241000000 from A2
      occurrence rawfact_9669446bc8076fa26bca33a3d9a067093bddadbb28e4617318bb3de33a4eca29,
      AS_REPORTED is VALUE from A1 occurrence
      rawfact_bc9355a292f06baaaf988b683106b2b02e3dd9c4a9555f1eb160a94643e4feaf, and
      LATEST_RESTATED remains missing with "no eligible explicitly typed reported revision vintage".
  - claim: A confirmation can never reach reported revisions.
    command: inspect REPORTED_REVISION_EVENT_TYPES against the ledger with 130 receipts attached
    result: >
      xbrl_confirmation is absent from the set; 0 of 1722 events are revision-eligible because
      every occurrence is FILED with revision_of None, so packet revisions[] stays empty.
  - claim: No regression across the forensics surface.
    command: pytest over the 19 fundamental-forensics and forensics-api test files
    result: 611 passed, 0 failed.
  - claim: The user journey works in a browser against the real route.
    command: browser against the page served on one origin with app/forensics.py
    result: >
      At 2026-09-20 the page reads "Repeated - not revised" with both accessions, both accepted
      clocks, equal values, equal decimals, equal taxonomy URIs and both occurrence ids, plus the
      receipt drilldown. Rewound to 2026-08-23 all three policies read "Not evaluable" with the
      accepted refusal and no evidence table, no drilldown, no leaked value.
review_findings_resolved:
  - severity: HIGH
    finding: >
      Guard 11 attested only that the two Clark taxonomy URIs matched, so two matching but
      invented URIs would satisfy it.
    resolution: >
      _approved_taxonomy_uri now requires the attested URI to be present in the repository's own
      TAXONOMY_NAMESPACE_POLICY and to resolve to the prefix the retained concept_qname already
      carries. Enforced at mint and again on every query.
  - severity: MEDIUM
    finding: >
      _admit_lineage_evidence checked shape and binding but did not re-prove the edge, so a bundle
      built without derive_confirmation_receipts could chain A->B and B->C across three filings.
    resolution: >
      Admission now re-runs evaluate_confirmation against the live ledger for every edge and
      refuses any logical key whose bundle spans more than two filings. _effective_roots also drops
      any component larger than two, so the cell keeps the honest unlinked-vintage refusal.
  - severity: LOW
    finding: _effective_root_cache could grow without bound if an engine were pooled.
    resolution: Bounded by MAX_EFFECTIVE_ROOT_CACHE_ENTRIES; the cache is a speed aid, never a correctness input.
unverified:
  - claim: Production attested issuer service.
    state: NOT_BUILT
    what_would_verify: >
      The separately gated production issuer admission program. Delivery on this path is still
      exactly committed_golden_fixture with attested=false and production_issuer_service=false,
      and the served corpus is still the two committed golden accessions. A golden fixture is not
      a production issuer service and this commission does not make it one.
  - claim: Any issuer other than AAPL.
    state: NOT_STARTED
    what_would_verify: A separate commission. SNOW/CAT/BAC/GOOGL were explicitly out of scope here.
unresolved:
  - FIF-3 remains IN_PROGRESS. The broader five-issuer slice is not complete and FIF-3 is not complete from an AAPL fixture alone.
  - >
    Guard 11 still reads the original taxonomy URI from the source package at mint time, because the
    canonical ledger does not retain it. The attestation is now policy-bound rather than
    self-asserted, and a changed source document changes body_sha256 and therefore occurrence_id,
    which invalidates the receipt at admission. A signed external taxonomy manifest would be
    strictly stronger and remains available as a later wave.
  - >
    site/financial_lineage.html is one journey over the existing endpoint. It is not wired into
    the generated fundamental_forensics.html page, which is a separate non-FIF data lane, and it
    has no design packet or ZH parity yet.
next_actions:
  - Sol/Chairman adjudication of this implementation against DEC:FIF-3A4R before any further issuer.
  - If accepted, mint a DEC recording FIF-3A4 as BUILT and the v1 runtime rule as accepted source law.
  - Keep FIF-3 IN_PROGRESS and production attested issuer service NOT_BUILT until their own gates clear.
do_not_redo:
  - Do not reopen accepted FIF-3A1/A2/A3 identities or hashes; they are asserted green in this branch.
  - Do not remint A2 FILED, append a third confirmation occurrence, or manufacture revision_of.
  - Do not load the A4R research census JSON into runtime; the runtime rule derives 130 from source.
  - Do not widen v1 from exact equality to duplicate consistency or precision intervals.
  - Do not discard dimensioned lawful lineage; 93 dimensioned receipts are retained deliberately.
  - Do not re-freeze query.py byte-wise; A4 is the authorized change and the A3 hashes are the real guard.
  - Do not call this production attested issuer service, or FIF-3 complete.
danger_areas:
  - >
    The clock floor is what preserves history. system_available_at below
    max(rule availability, both recorded clocks) is refused at mint; weakening that would
    retroactively repair historical A3 NOT_EVALUABLE states.
  - >
    Widening the two-filing ceiling would admit a third filing with no unique parent. It is
    enforced at mint, at admission, and again in effective-root resolution.
  - Emitting lineage inside "receipt" rather than beside it would move query_hash.
---

Capability delta: before this session FIF-3A4 was accepted architecture with no
runtime. After it, two separate real accepted filing packages produce lawful
immutable cutoff-visible lineage evidence, the existing query kernel consumes it,
point-in-time LATEST_KNOWN_AS_OF changes exactly where the accepted relation
permits, AS_REPORTED does not move, refusals remain refusals, and a user-facing
answer names the filing that supports it. Production attested issuer service
remains NOT_BUILT and FIF-3 remains IN_PROGRESS.
