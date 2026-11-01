---
key: MX-CATALYST-SEC-ISSUER-EARNINGS-RELEASE-PUBLIC-FACTS
question: >
  Under what exact rights scope may the public Marketing X Catalyst scan (/api/catalyst,
  /scan, link-only partner pack) display facts from an SEC EDGAR filing to an anonymous
  reader, and how are the five steward questions D1–D5 (PR #7870 comment 6549466894)
  answered?
answer: >
  A new, narrow registry family ``sec_issuer_earnings_release_facts`` (derived_display_ok,
  keyless_public) covers only the issuer's own EX-99.1 earnings-release exhibit of a retained
  8-K/8-K/A Item 2.02 filing under https://www.sec.gov/Archives/edgar/data/<cik>/, present in
  the pinned catalyst source snapshot. D1: grants are exact-document only — the family admits
  the class and ``marketing.catalyst_source_adapter`` mints one runtime PublicSourceGrant per
  URL + sha256; no family-level or filing-level allow-all. D2: the EX-99.1 is displayed as
  verified facts only (figures and clock), attributed ("SEC Form 8-K Item 2.02" + link) with a
  link-out; no quotation, excerpt or body export. D3: third-party documents under the same
  /Archives/ prefix, every other exhibit and SEC index pages are excluded as display sources.
  D4: expires_at = min(first retained + 7 d, mint + 24 h); bytes are retained internally in
  the R2 snapshot for verification only and never re-served. D5: owner_ref =
  ``marketing.catalyst_source_adapter@SEC-ISSUER-EARNINGS-RELEASE-PUBLIC-FACTS-20261101``;
  receipt_id = the document's ORIGINAL first-retrieval receipt id from the pinned snapshot
  (≤128 chars). Email, paid-product display, rehosting and reviewer text stay out of scope,
  and the public flags stay off until their operator turns them on.
rationale: >
  The SEC webmaster FAQ and Website Dissemination policy (both re-read 2026-11-01) state that
  EDGAR public filing content may be reused with SEC citation. The issuer's earnings release
  is issuer expression, not a §105 government work, so the scope is facts with attribution,
  never the release's words. A separate family keeps this public_anonymous display basis from
  widening ``sec_public_filing_facts`` (another program's entitled-audience basis), and the
  per-document runtime grant with a short expiry keeps every displayed fact traceable to one
  exact retained document. The steward on #7870 has been absent since the request was
  delivered; under the Chairman 10-24 leadership-continuity ruling the current seat records
  the decision rather than waiting.
alternatives:
  - option: Reuse the existing ``sec_public_filing_facts`` family
    why_not: >
      Its basis (SEC-PUBLIC-FILING-FACT-USE-20261019) is scoped to another program's entitled
      audience; admitting anonymous public display under it would silently widen that basis.
  - option: Adopt the #7870 ``sec_edgar`` direct_display_ok candidate row
    why_not: >
      Family-level and broader (receipted-excerpt display across filings); D1 asks for exact
      document grants and D2 for facts only.
  - option: Wait for the GMI/source steward to answer D1–D5
    why_not: >
      The steward is absent; the Chairman 10-24 ruling makes the current receiver responsible
      for recording the decision. Independent review before merge still applies.
evidence:
  - "research/marketing_dockets/catalyst_fable_20261031/SEC_ISSUER_EARNINGS_RELEASE_PUBLIC_FACTS.json (basis SEC-ISSUER-EARNINGS-RELEASE-PUBLIC-FACTS-20261101)"
  - "https://www.sec.gov/about/webmaster-frequently-asked-questions (opened and read 2026-11-01)"
  - "https://www.sec.gov/privacy-information#dissemination (opened and read 2026-11-01)"
  - "research/marketing_dockets/catalyst_fable_20261031/RIGHTS_CLASSIFICATION_REQUEST.md (D1–D5 as delivered to PR #7870 comment 6549466894)"
  - "engine/theme_graph/rights.py (EMISSION_OK = derived_display_ok/direct_display_ok; unknown family raises RightsRefusal)"
affects:
  - WS:MARKETING-X-CATALYST-LOOP
  - config/theme_sources.yml
  - engine/marketing/catalyst_admission.py
  - engine/marketing/catalyst_source_adapter.py
confidence: medium
reversibility: easy
decided_by: "fable-meta-ceo (MX Catalyst CEO seat ce215fa3, leadership continuity under Chairman 10-24 ruling; steward #7870 absent)"
decided_at: 2026-11-01
---

The registry row admits the family and the adapter mints the exact-document grants; neither
is a Chairman grant, a legal opinion or a vendor license, and neither extends
DEC:COMMERCIAL-DATA-RIGHTS-CHAIRMAN-ATTESTATION-20261023. Reversal is a one-row removal from
`config/theme_sources.yml`; the gate then refuses the family and the scan fails closed.
