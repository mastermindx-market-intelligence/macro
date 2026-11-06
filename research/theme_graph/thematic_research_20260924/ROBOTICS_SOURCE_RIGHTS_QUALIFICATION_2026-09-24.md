# Robotics source-rights qualification matrix (for adjudication)

**Provenance.** Operation `gmi-robotics-fable-ceo-e2e-20260923-chairman-001`, carrier Macro #7908, seat Claude Fable (direct bounded completion under Sol #7780 issuecomment-5814541566 §1; the fabric lane `rob-r7` was withdrawn before any executor STARTed; independent READ_ONLY review taken before posting). Rulings consumed: Sol #7780 issuecomment-5813801605 (option A) and issuecomment-5814333887 (rights admission is a qualification unit, not an analogy); shared owner #7870 issuecomment-5813896754 (Robotics registration + cohort + request 7), 5813976021 (request 7 is a rights-registry admission question for Sol; `system_replay` refusal shape), 5813976564 (post-ruling rights-admission question). Corpus commit: carrier #7908 `5d95a26e9220` (R2b re-mint; the 21 fixtures under `tests/fixtures/robotics_theme_research/`, 66 assertions in `bundle.assertions`); code citations are against the review merge tree `181818522db2` (= that carrier commit + shared foundation #7870 `3e3a7956d014`; the fixture diff between the two is empty) except where a later carrier commit is named. Inspection window: first fetch `2026-09-24T13:21:55Z`, last fetch `2026-09-24T13:48:04Z` (all UTC; every URL fetched is listed in Appendix A with HTTP status, bytes and final URL; no page body was retained).

**Source counts and public accessibility are not an approval basis.**

This document PROPOSES. It concludes nothing. Every representation below is a proposal for the GMI source-rights owner and Sol to adjudicate; until adjudicated, every family named here is **pending = refused**, and refusal includes dependent prose and evidence (Sol 5814333887 §4). No registry row, prefix entry, fixture, test or composer line is changed by this document.

## 0. What the v1 consumer actually does with a source (scope of the ask)

- **Consumer.** The only intended consumer is the entitled private read of the shared theme-research transport: `POST /api/themes/v1/research/query` and `/evidence` (`app/theme_research.py`, #7870 T09), composing `robotics_theme_research.v1` from retained assertions. At this pin the transport is wired to the semiconductor composer only (`app/theme_research.py:44,48,337`); the Robotics composer is registered for dispatch under the shared owner's queued H1 registry lane and is not yet served. Never public site display; never a public JSON; never the tracked evidence parquet (the R3 freeze pins those canaries).
- **What crosses the wire.** Composed facts (typed quantities with unit/basis/precision, relation kinds, dated lifecycle, limitations) and, on the evidence route, the assertion itself plus its `source` block: `publisher`, `source_uri`, `locator`, `published_at`, `published_at_grain`, `observed_at`, `retained_at`. The corpus carries **no verbatim excerpt field**: every one of the 66 assertions' `source` block has exactly the keys `locator, native_digest, observed_at, published_at, published_at_grain, publisher, retained_at, retention_ref, source_uri`, and observation keys are typed values. So v1 exercises only: family recognition, private retention (the `retention_ref` Research Vault object), original factual synthesis with attribution, and a link (`source_uri`). `short_quotation_with_attribution` is **not proposed for any family in v1**; `full_body_display` and `dataset_redistribution` are **not proposed for any family** and appear only in this "not proposed" note.
- **Retention.** Each assertion cites a `retention_ref` (`research-vault://fixture/...` in fixtures). Retention of the acquired document is one of the decisions Sol separated (acquisition/retention ≠ quotation ≠ synthesis ≠ display ≠ redistribution) and is therefore a column, not an assumption. **Acquisition method matters to two rows:** the JPX and HKEX pages inspected below carry clauses on automated collection / text-and-data-mining; how the retained documents were acquired (a human download vs an automated fetch) is part of what the rights owner must qualify and is recorded as a gap, not assumed.

## 1. Matrix (one row per publisher host × source class)

Columns, in order: **Publisher** (legal entity as named on the inspected page where one was read; otherwise the fixture's `source.publisher` string, marked) · **Host** · **Source class** · **Refs in corpus** (assertions whose `source.source_uri` is on the host, with one example locator) · **Proposed representation(s)** (from {family_recognition_only, retained_private_only, short_quotation_with_attribution, original_factual_synthesis_with_attribution, link_only, full_body_display, dataset_redistribution}) · **Actual consumer** · **Authoritative terms/licence/basis actually inspected** (URL · title/version · UTC time read) · **Restrictions found** (verbatim clause ≤ 60 words marked READ, or `silent`, or `terms_unreachable`; INFERRED marks a scope conclusion this document draws) · **Existing source-owner decision** (registry row / prefix entry today) · **Minimum positive witness** (fixture stem + assertion index that would prove the family end to end once admitted) · **Refusal behaviour while pending** (§3) · **Representation gap** (what the registry's `rights_class`/`auth_class` grammar cannot express at this grain).

| Publisher | Host | Source class | Refs in corpus (count + example locator) | Proposed representation(s) (v1) | Actual consumer | Authoritative terms/licence/basis actually inspected | Access/retention/display/export restrictions found | Existing source-owner decision | Minimum positive witness | Refusal behaviour while pending | Representation gap |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Harmonic Drive Systems (fixture `publisher` string; the filing itself was not fetched in this lane) | www2.jpx.co.jp | publisher_authored_filing | 39 · `https://www2.jpx.co.jp/disc/63240/140120260804507706.pdf`; locator of `hds_operating_snapshot.json[0]`: "PDF pp.14-16, product/region operating table, row 'Japan / Speed reducers', column 'Production'" | family_recognition_only; retained_private_only; original_factual_synthesis_with_attribution; link_only | entitled private route (§0) | Issuer's own document; no issuer licence page inspected (the issuer's corporate site is not a corpus host). The document is reached only through the JPX wrapper (next row). | `silent` on the issuer side (no issuer terms read); the wrapper's clauses (next row) apply to the retrieval path. | none — no family row; `family_for_source_ref` → `None` | `hds_operating_snapshot.json[0]` (Japan speed-reducer production, RBV-23/24) | RightsRefusal at the emission boundary once the prefix is recognised (§3); today unrecognised → pass-through (§3.4) | G1: the issuer (this row) and the wrapper (next row) share one URL prefix, and `SOURCE_PREFIX_FAMILY` maps a prefix to exactly one family — the registry has no publisher axis to hold two decisions for one prefix. |
| Japan Exchange Group, Inc. (JPX) — listed-company disclosure hosting (TDnet-fed) | www2.jpx.co.jp | exchange_wrapper_or_database | same 39 refs (wrapper of the row above) | family_recognition_only; link_only | entitled private route | `https://www.jpx.co.jp/english/term-of-use/index.html` · "Disclaimer/ Terms of Use \| Japan Exchange Group" · page shows "Update : Jul. 29, 2026" and states the Japanese version prevails · 2026-09-24T13:24:30Z; Japanese original `https://www.jpx.co.jp/term-of-use/index.html` · "サイトのご利用上の注意と免責事項" · "2026/07/29 更新" · 13:24:29Z. Host root `https://www2.jpx.co.jp/` answered 403; no robots.txt (404). | READ (en): "The collection of data or secondary use of information from this website for commercial purposes is strictly prohibited, unless JPX has granted prior permission or authorized such use under a paid contract." READ (en, sentence fragment as retrieved, continues): "When generative AI or similar technologies are used to learn, analyze, or create content based on information from this website, any actions that infringe copyrights or any other rights or interests, are inappropriate or contrary to the purpose or operational policy of this website, or could harm or disadvantage JPX are strictly […]". INFERRED, not read: whether "this website" (jpx.co.jp) governs the www2.jpx.co.jp/disc/ hosting path. | none | `hds_operating_snapshot.json[0]` (through this wrapper; the issuer row above) | as above; the commercial-secondary-use and generative-AI clauses are the adjudication questions for these two rows (§4 Q1) | G1 as above; plus G4: `auth_class` has no value for "keyless public but acquisition-method-restricted" — the closest, `keyless_public`, cannot record that automated collection is restricted by the wrapper's terms. |
| Sanhua (fixture `publisher` string; issuer-authored HKEX announcement, not fetched in this lane) | www1.hkexnews.hk | publisher_authored_filing | 2 · `https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0826/2026082601555.pdf` (`sanhua_actuator_scaleup.json[0]`) | family_recognition_only; retained_private_only; original_factual_synthesis_with_attribution; link_only | entitled private route | Issuer's own document; no issuer licence page inspected. Reached only through the HKEXnews wrapper (next row). | `silent` on the issuer side; the wrapper's clauses (next row) apply to the retrieval path. | none | `sanhua_actuator_scaleup.json[0]` (actuator scale-up disclosure, RBV-06/07/08) | as the first row | G1 (one prefix, two publishers). |
| Hong Kong Exchanges and Clearing Limited (HKEX) — HKEXnews disclosure database | www1.hkexnews.hk | exchange_wrapper_or_database | same 2 refs (wrapper of the row above) | family_recognition_only; link_only | entitled private route | HKEXnews index (`https://www1.hkexnews.hk/` → final URL `https://www.hkexnews.hk/index.htm`, "HKEXnews", 13:21:58Z; `https://www.hkexnews.hk/` 13:22:07Z) exposes no terms/disclaimer anchor; `https://www.hkexnews.hk/disclaimer.htm` → 404; no robots.txt (404). HKEX group Terms of Use `https://www.hkex.com.hk/Global/Exchange/Terms-of-Use?sc_lang=en` · "Last updated: 19 August 2025" · 13:24:35Z, re-read 13:48:04Z. | READ (hkex.com.hk ToU): "You are permitted to download, print, store temporarily, retrieve and display Information from the Website on a computer screen, print individual pages on paper (but not photocopy them) and store such pages in electronic form on disk (but not on any server or other storage device connected to a network) for your personal use." READ: "You are not permitted to conduct, facilitate, enable, authorise or permit any text or data mining or web scraping in relation to this Website or any services provided via, or in relation to, this Website for any purpose, including the development, training, fine-tuning or validation of artificial intelligence (“AI”) systems or models." INFERRED, not read: that these group terms govern hkexnews.hk. | none | `sanhua_actuator_scaleup.json[0]` (through this wrapper; the issuer row above) | as the first row; the personal-use-only grant and the text-and-data-mining prohibition are the adjudication questions for these two rows (§4 Q1) | G1; G4 (acquisition-method restriction not expressible in `auth_class`). |
| Orbbec Inc. (author of the case-study page) | www.orbbec.com | vendor_case_study | 8 · `https://www.orbbec.com/case-studies/logistics-costs-reduced-by-64-4-twinny-launches-latest-logistics-robot-product-equipped-with-orbbec-cameras/` (`witness_perception_orbbec_twinny.json[0]`) | family_recognition_only; retained_private_only; original_factual_synthesis_with_attribution; link_only | entitled private route | `https://www.orbbec.com/terms-and-conditions/` · "Terms and Conditions \| Orbbec" · no version/date shown · 13:24:37Z; robots.txt 200 (3 lines, nothing relevant to /case-studies/). | READ: "Without the prior written permission of Orbbec or relevant rights holders, you shall not copy, reproduce, disseminate, publish, post, adapt or display the content of this website in any way." No quotation, citation or personal-use carve-out was found on the page (READ absence, whole page inspected). | none | `witness_perception_orbbec_twinny.json[0]` (Gemini 335 ×2 documented inclusion in Twinny NarGo, RBV-02/12/15) | as the first row; only facts-with-attribution and a link are proposed, nothing quoted or displayed (§4 Q2) | G1 with the next row (Twinny statements on this host share the prefix). |
| Twinny (fixture `publisher` string; Twinny-authored statements republished inside Orbbec's case study — a second publisher on the same host and class; Twinny's own site not inspected) | www.orbbec.com | vendor_case_study | 1 · same page as the row above (`unresolved_identity_source_only.json[0]`, `source.publisher` = "Twinny") | family_recognition_only; retained_private_only; original_factual_synthesis_with_attribution; link_only | entitled private route | Twinny's own site was not inspected (not a corpus host; Orbbec's page is the retrieval path); Orbbec's terms (row above) govern the page. | `silent` on the publisher side; the host's clause (row above) applies to the page. | none | `unresolved_identity_source_only.json[0]` (Twinny NarGo capability with unresolved identity, RBV-11) | as the first row; additionally a publisher-level decision is required before any Twinny-attributed fact is served | G1: a second publisher on one prefix cannot be a second family; the registry needs a publisher axis (e.g. keyed on `source.publisher`) or the assertion-level `publisher` must be admitted as a rights key. |
| Parker Hannifin Corporation (K-Series frameless motor catalogue microsite) | discover.parker.com | vendor_catalogue | 3 · `https://discover.parker.com/K-Series` (`witness_motion_parker_kseries.json[0]`) | family_recognition_only; retained_private_only; original_factual_synthesis_with_attribution; link_only | entitled private route | `https://discover.parker.com/` · 200 but an 865-byte script shell with no terms anchor · 13:22:19Z; robots.txt 200 (`Allow: /`). `https://www.parker.com/` → 403 "Access Denied" (curl 13:22:24Z; the seat's fetch tool also 403); its terms page was therefore not reached. | `terms_unreachable` (publisher blocks automated reads; no terms text was read). | none | `witness_motion_parker_kseries.json[0]` (K-Series catalogue capability, RBV-01/15) | as the first row; no quotation of any kind is proposed until a human-readable terms page is inspected | none beyond G4 (unknown acquisition restrictions cannot be recorded). |
| ROBOTIS Co., Ltd. (Dynamixel product pages) | www.robotis.com | vendor_catalogue | 2 · `https://www.robotis.com/en/product/dynamixel-2x.php` (`integrated_assembly_double_count.json[0]`) | family_recognition_only; retained_private_only; original_factual_synthesis_with_attribution; link_only | entitled private route | `https://www.robotis.com/` → final URL `https://www.robotis.com/en/` · "ROBOTIS \| Actuator for Physical AI" · 13:22:30Z — footer links only a Privacy Policy (`/en/policyprivacy.php`); `/en/policyterms.php` → 404; robots.txt 200 (disallows `/pdf/` and admin paths; product pages not disallowed). | `silent` (no terms-of-use page located; the privacy policy is not a content licence). | none | `integrated_assembly_double_count.json[0]` (Dynamixel 2X integrated assembly, RBV-21) | as the first row | none beyond G4. |
| Hexagon Robotics (Hexagon AB group company; press announcement) | robotics.hexagon.com | issuer_press_release_or_announcement | 2 · `https://robotics.hexagon.com/hexagon-robotics-and-schaeffler-deploy-a-fleet-of-aeon-humanoids/` (`schaeffler_hexagon_reciprocal.json[0]`) | family_recognition_only; retained_private_only; original_factual_synthesis_with_attribution; link_only | entitled private route | `https://robotics.hexagon.com/imprint/` · "Imprint - Hexagon Robotics" · 13:24:41Z (no use/copy clause on it); footer "Terms of use" → `https://hexagon.com/legal/terms-of-use` → 403 challenge page (curl on the host root 13:22:55Z; the seat's fetch tool also 403). robots.txt 200 (`Crawl-delay: 10`; `/wp-admin/` only). | `terms_unreachable` for the governing terms; the imprint page is `silent` on reproduction. | none | `schaeffler_hexagon_reciprocal.json[0]` (Schaeffler↔Hexagon two directed edges, RBV-04/05) | as the first row | none beyond G4. |
| Zebra Technologies Corporation (press release) | www.zebra.com | issuer_press_release_or_announcement | 2 · `https://www.zebra.com/us/en/about-zebra/newsroom/press-releases/2026/skild-ai-acquires-zebra-technologies--robotics-automation-busine.html` (`zebra_skild_ownership.json[0]`) | family_recognition_only; retained_private_only; original_factual_synthesis_with_attribution; link_only | entitled private route | `https://www.zebra.com/us/en/about-zebra/company-information/legal/terms-of-use.html` · "Terms of Use \| Zebra" · no effective date found in the page text · 13:24:41Z; robots.txt 200 (218 lines; press-release path not disallowed). | READ: "Unauthorized reproduction, distribution, modification, duplication, creation of derivative works, or use of this website constitutes copyright infringement." READ: "Any use of the website not in compliance with these Terms of Use is strictly prohibited and will be deemed a breach of your agreement with Zebra to access and use the website." No press-release carve-out was found in the extracted clauses (INFERRED absence: the extraction, not the whole page, was inspected). | none | `zebra_skild_ownership.json[0]` (Zebra = the announced party of the Robotics Automation transfer to Skild AI, RBV-10; the composer serves `announced_party` and no direction — the ownership-side parse is retired in v1, carrier #7908 fix11) | as the first row | none beyond G4. |
| 1X Technologies AS (product page "NEO hands") | www.1x.tech | vendor_catalogue | 1 · `https://www.1x.tech/discover/neos-hands` (`per_hand_multiplicity_missing.json[0]`) | family_recognition_only; retained_private_only; original_factual_synthesis_with_attribution; link_only | entitled private route | `https://www.1x.tech/` · "1X \| Home Robots" · 13:23:12Z — footer "Terms of Use" anchor points at `https://www.1x.tech/terms-and-conditions`, which returned **404** at 13:24:43Z; no robots.txt (404). | `terms_unreachable` (linked terms page absent at inspection). | none | `per_hand_multiplicity_missing.json[0]` (NEO tendon-driven hands, per-hand multiplicity missing, RBV-22) | as the first row | none beyond G4. |
| PTC Inc. (press release) | www.ptc.com | issuer_press_release_or_announcement | 1 · `https://www.ptc.com/en/news/2026/ptc-completes-divestiture-of-kepware-and-thingworx-businesses` (`ptc_tpg_ownership.json[0]`) | family_recognition_only; retained_private_only; original_factual_synthesis_with_attribution; link_only | entitled private route | `https://www.ptc.com/` → 403 "Access Denied" (curl 13:23:21Z; the seat's fetch tool also 403); robots.txt 403. No terms text reached. | `terms_unreachable`. | none | `ptc_tpg_ownership.json[0]` (PTC completed divestiture of Kepware/ThingWorx to TPG, RBV-10/18) | as the first row | none beyond G4. |
| Teradyne, Inc. (FY2025 Form 10-K as rendered on the investor-relations host; the filing's authoritative copy is SEC EDGAR accession 0001193125-26-059002) | investors.teradyne.com | investor_relations_page (wrapper of an SEC filing) | 1 · `https://investors.teradyne.com/sec-filings/all-sec-filings/content/0001193125-26-059002/ter-20251231.htm` (`rights_partial.json[0]`) | family_recognition_only; link_only | entitled private route | `https://investors.teradyne.com/disclaimer` · "Disclaimer :: Teradyne, Inc. (TER)" · 13:24:43Z (re-read 13:26:53Z); `https://investors.teradyne.com/` 13:23:27Z; robots.txt 200 (`Disallow: /form-submit`). The registered `sec_edgar` family's stated basis is the SEC Website Dissemination policy (`config/theme_sources.yml`, review row), which on its face concerns sec.gov. | READ: the disclaimer is an investment/forward-looking-statement disclaimer ("The information contained herein has been provided as an information service only.") and is `silent` on reproduction; the page footer attributes market data to QuoteMedia under QuoteMedia's terms (third party, not used). INFERRED, not established: whether the `sec_edgar` decision reaches a copy rendered on an IR host. | `sec_edgar` exists for EDGAR-hosted filing content (auth_class keyless_public; redistribution never claimed) — but **no `https://` prefix of any kind is in `SOURCE_PREFIX_FAMILY`**, so even an EDGAR URL maps to `None` today (observed; the shared owner's item) | `rights_partial.json[0]` (Teradyne FY2025 Robotics segment revenue as recorded in the fixture, RBV-27) | as the first row; no new admission is requested for this witness if the locator is re-pointed to EDGAR and the EDGAR prefix is registered (§4 G2) | G2: the one admitted external family is unrecognisable from a `source_uri`; and the registry cannot say "same document, different host" — a wrapper-of relation is missing. |
| Stabilus SE (press release) | group.stabilus.com | issuer_press_release_or_announcement | 1 · `https://group.stabilus.com/news-and-events/press-releases/mail/news-synapticon-and-stabilus-form-partnership-to-develop-a-joint-product-line-of-integrated-actuators-for-humanoid-robots` (`stabilus_synapticon_joint_product.json[0]`) | family_recognition_only; retained_private_only; original_factual_synthesis_with_attribution; link_only | entitled private route | `https://group.stabilus.com/legal-notice` · "Legal Notice \| Stabilus Group" · no date shown · 13:24:44Z; robots.txt 200 (TYPO3 admin paths only). | READ: "The texts, pictures, graphs and trademarks featured on Stabilus' websites are subject to copyright, trademark and other laws on the protection of intellectual property. They may not be copied, changed or used on other Internet sites without our prior permission." | none | `stabilus_synapticon_joint_product.json[0]` (Stabilus/Synapticon joint product arrangement, RBV-04) | as the first row | none beyond G4. |
| (fixture-only) example.invalid | example.invalid | n/a — synthetic | 3 · `https://example.invalid/robotics/wire-1` (`rights_partial.json[1]`, `source_authority_injection.json[0]`, `syndicated_copy.json[1]`) | none — **not a family**; fixture-only, never production-authorised (Sol 5814333887 §4) | test suites only | n/a | n/a | none, by design | n/a | must never be registered; the guard treats it as unmapped and the fixtures exist to prove refusal/injection handling | n/a |

Not proposed for any row: `full_body_display`, `dataset_redistribution`, and (in v1) `short_quotation_with_attribution`. The corpus has no excerpt field to carry a quotation, and no publisher's inspected terms carve out quotation; if a later version adds an evidence excerpt, that is a new representation request per family, not an extension of this one. Sanhua's, Harmonic Drive Systems' and Twinny's own sites were not inspected: their documents reached the corpus only through the wrapper/host rows above, and inspecting the issuer sites would not change the wrapper questions in §4 Q1.

## 2. Narrowly scoped registry/prefix change — ADJUDICATED, recognition only

> **SOL RULING #7780 issuecomment-5825621672 item 6 (2026-09-25).** "Add the narrowly
> path-scoped publisher prefixes/family rows it already prepared with `rights_class:
> unresolved` so the shared resolver can identify them and the emission gate can refuse them
> explicitly. This is recognition only, not display approval. Do not create a public-source
> exception, second rights axis, new `auth_class` or vertical-local registry. Later promotion of
> an individual family requires its own reviewed terms. `example.invalid` remains fixture-only."
>
> The eleven rows below already carry `rights_class: unresolved`, so they are approved as
> written. They are applied by the **shared rights owner** in `engine/theme_graph/rights.py`
> and `config/theme_sources.yml`, not from the Robotics lane — two seats editing one shared
> tuple is a collision this lane exists to prevent. Delta handed over at #7780
> issuecomment-5825666880. Each row's `outcome` becomes `RECOGNITION ONLY per #7780
> 5825621672 item 6 — not display approval`.
>
> **Recognition does not change what serves.** The corpus holds 66 assertions, each with
> exactly one source ref (14 distinct URIs, 12 hosts). Before: all 66 unmapped, withheld from
> ignorance. After: the 63 refs naming the eleven real publishers resolve to a named family whose
> `rights_class` is `unresolved` and are withheld explicitly with inspected terms attached; the
> remaining 3 are the fixture-only `example.invalid` host and stay unmapped by design. Zero
> assertions serve from these publishers either way. That is the ruled-correct state, not a defect.

Grain: one family per **publisher host × source class**, never a whole first-party domain and never "all vendor sites". Every row is `rights_class: unresolved` — the only honest value pending adjudication — and `auth_class: keyless_public` — INFERRED from the fixtures' keyless URLs, not established: this lane fetched no corpus document, the corpus carries no acquisition receipt, and every `retention_ref` is today a `research-vault://fixture/…` placeholder (real retention receipts are an R5 item); the acquisition-method restrictions found on the JPX/HKEX wrappers are NOT expressible in `auth_class` — G4. Prefixes are exact strings scoped to the corpus locator paths; two hosts (Parker's microsite, Hexagon Robotics) have exactly one corpus page each, so their prefixes are that page, not the host root — a future page on either host needs its own registration (closed exact-string registration, per Sol option A). A second publisher on the same prefix (Twinny on Orbbec's host) cannot be a second family (G1) and is recorded in the host family's notes.

```yaml
# ADJUDICATED #7780 5825621672 item 6 — recognition only, not display approval.
# Applied by the shared rights owner (delta handed over at #7780 5825666880).
# One row per publisher host × source class.
families:
  jpx_tdnet_issuer_disclosure:
    rights_class: unresolved
    auth_class: keyless_public
    source_route: "issuer-authored timely-disclosure PDFs hosted by JPX at www2.jpx.co.jp/disc/<code>/ (TDnet-fed); publisher = the issuer, wrapper = JPX (two decisions on one prefix — G1)"
    review: { date: "2026-09-24", by: "gmi-robotics-r7", outcome: "RECOGNITION ONLY per #7780 5825621672 item 6 — not display approval; JPX terms (2026-07-29) prohibit commercial secondary use without permission and restrict generative-AI use — see qualification §4 Q1" }
  hkexnews_issuer_disclosure:
    rights_class: unresolved
    auth_class: keyless_public
    source_route: "issuer-authored announcements hosted by HKEXnews at www1.hkexnews.hk/listedco/listconews/; publisher = the issuer, wrapper = HKEX (G1)"
    review: { date: "2026-09-24", by: "gmi-robotics-r7", outcome: "RECOGNITION ONLY per #7780 5825621672 item 6 — not display approval; HKEX group ToU (2025-08-19) grants personal use only and prohibits text-and-data mining / scraping for any purpose — see §4 Q1" }
  orbbec_vendor_case_study:
    rights_class: unresolved
    auth_class: keyless_public
    source_route: "Orbbec case studies at www.orbbec.com/case-studies/ (host publisher Orbbec; Twinny-authored statements republished on the same page are a second publisher that this grammar cannot key — G1)"
    review: { date: "2026-09-24", by: "gmi-robotics-r7", outcome: "RECOGNITION ONLY per #7780 5825621672 item 6 — not display approval; T&C forbid copy/reproduce/display without written permission — see §4 Q2" }
  parker_vendor_catalogue:
    rights_class: unresolved
    auth_class: keyless_public
    source_route: "Parker Hannifin catalogue page discover.parker.com/K-Series (exact page)"
    review: { date: "2026-09-24", by: "gmi-robotics-r7", outcome: "RECOGNITION ONLY per #7780 5825621672 item 6 — not display approval; terms_unreachable (403 to automated reads)" }
  robotis_vendor_catalogue:
    rights_class: unresolved
    auth_class: keyless_public
    source_route: "ROBOTIS product pages www.robotis.com/en/product/"
    review: { date: "2026-09-24", by: "gmi-robotics-r7", outcome: "RECOGNITION ONLY per #7780 5825621672 item 6 — not display approval; no terms-of-use page located (silent)" }
  onex_vendor_product_page:
    rights_class: unresolved
    auth_class: keyless_public
    source_route: "1X product/discover pages www.1x.tech/discover/"
    review: { date: "2026-09-24", by: "gmi-robotics-r7", outcome: "RECOGNITION ONLY per #7780 5825621672 item 6 — not display approval; linked terms page 404 at inspection" }
  hexagon_robotics_press:
    rights_class: unresolved
    auth_class: keyless_public
    source_route: "Hexagon Robotics announcement page robotics.hexagon.com/hexagon-robotics-and-schaeffler-deploy-a-fleet-of-aeon-humanoids/ (exact page)"
    review: { date: "2026-09-24", by: "gmi-robotics-r7", outcome: "RECOGNITION ONLY per #7780 5825621672 item 6 — not display approval; governing hexagon.com terms unreachable (403)" }
  zebra_press:
    rights_class: unresolved
    auth_class: keyless_public
    source_route: "Zebra press releases www.zebra.com/us/en/about-zebra/newsroom/press-releases/"
    review: { date: "2026-09-24", by: "gmi-robotics-r7", outcome: "RECOGNITION ONLY per #7780 5825621672 item 6 — not display approval; ToU: unauthorized reproduction/distribution is infringement; no press carve-out found" }
  ptc_press:
    rights_class: unresolved
    auth_class: keyless_public
    source_route: "PTC news releases www.ptc.com/en/news/"
    review: { date: "2026-09-24", by: "gmi-robotics-r7", outcome: "RECOGNITION ONLY per #7780 5825621672 item 6 — not display approval; terms_unreachable (403)" }
  teradyne_ir_sec_wrapper:
    rights_class: unresolved
    auth_class: keyless_public
    source_route: "investors.teradyne.com/sec-filings/ (IR rendering of SEC filings; authoritative copy is EDGAR). Preferred alternative: re-point the fixture locator to EDGAR, register the EDGAR prefix for sec_edgar, and register NO new family — G2"
    review: { date: "2026-09-24", by: "gmi-robotics-r7", outcome: "RECOGNITION ONLY per #7780 5825621672 item 6 — not display approval; prefer the re-point (§4 G2) over a new family" }
  stabilus_press:
    rights_class: unresolved
    auth_class: keyless_public
    source_route: "Stabilus press releases group.stabilus.com/news-and-events/press-releases/"
    review: { date: "2026-09-24", by: "gmi-robotics-r7", outcome: "RECOGNITION ONLY per #7780 5825621672 item 6 — not display approval; legal notice: may not be copied/used on other sites without permission" }
```

```python
# ADJUDICATED additions to engine/theme_graph/rights.py::SOURCE_PREFIX_FAMILY, for the
# shared rights owner to apply (#7780 5825621672 item 6; delta at #7780 5825666880).
# Exact-string prefixes scoped to the corpus locator paths (two are single pages); no host root.
(
    ("https://www2.jpx.co.jp/disc/", "jpx_tdnet_issuer_disclosure"),
    ("https://www1.hkexnews.hk/listedco/", "hkexnews_issuer_disclosure"),
    ("https://www.orbbec.com/case-studies/", "orbbec_vendor_case_study"),
    ("https://discover.parker.com/K-Series", "parker_vendor_catalogue"),
    ("https://www.robotis.com/en/product/", "robotis_vendor_catalogue"),
    ("https://www.1x.tech/discover/", "onex_vendor_product_page"),
    ("https://robotics.hexagon.com/hexagon-robotics-and-schaeffler-deploy-a-fleet-of-aeon-humanoids/", "hexagon_robotics_press"),
    ("https://www.zebra.com/us/en/about-zebra/newsroom/press-releases/", "zebra_press"),
    ("https://www.ptc.com/en/news/", "ptc_press"),
    ("https://investors.teradyne.com/sec-filings/", "teradyne_ir_sec_wrapper"),
    ("https://group.stabilus.com/news-and-events/press-releases/", "stabilus_press"),
)
# example.invalid: fixture-only — deliberately NOT in this tuple (unmapped by design).
```

Why eleven families (fifteen matrix rows) and not one: the inspected terms differ per publisher (JPX: commercial secondary use prohibited without permission, generative-AI use restricted; HKEX: personal use only, text-and-data mining prohibited; Orbbec: no reproduction or display; Zebra: unauthorized reproduction is infringement; Stabilus: no copying without permission; four publishers unreachable or silent). A single "robotics_vendor" family would force one `rights_class` over incompatible terms, which Sol §4 forbids ("must not … treat every first-party domain as one permitted family"). The exchange rows carry the issuer/wrapper distinction in `source_route` and in §1 because a URL prefix can map to only one family (G1).

### 2.1 Verified seam state (measured 2026-09-25) — why §2 is load-bearing, not a nicety

The shared transport's emission filter (`app/theme_research.py::_filter_bundle_for_rights`,
#7870 `f2c2893cf07`) now withholds any assertion whose source it cannot attribute. It keys on

```python
source_ref = source.get("source_uri") or source.get("locator") or ""
family = family_for_source_ref(source_ref)
```

and withholds on `family is None`. Measured over the 21 Robotics bundle fixtures: **66 assertions, each carrying
exactly one source ref (14 distinct URIs over 12 hosts), and all 66 resolving to `None`** — 63 of
them naming the eleven real publishers, the remaining 3 the fixture-only `example.invalid` host
that is unmapped by design — because `SOURCE_PREFIX_FAMILY` holds only repo-relative
prefixes (`data/baskets/`, `finviz_themes/`, `config/theme_crosswalk.yml`) and no `https://`
prefix of any kind. Positive control in the same run: `family_for_source_ref("data/baskets/foo")
-> mastermind_curated`, `family_for_source_ref("zzz/nope") -> None`.

Consequence, stated plainly: **until the §2 prefixes land with owner-approved families, the
Robotics vertical serves zero assertions the moment R4 binds it.** Not a subset — all of it,
including the 39 HDS assertions that are the corpus's largest positive witness.

This changes nothing about the ask and adds no new question. Fail-closed is the correct default
and this document does not request an exception; a vertical that serves nothing is a better
failure than one publishing material no rights row covers. It dates and quantifies the ask, and
it moves G1-G4 from theoretical representation gaps to the thing that decides whether the
vertical serves at all. The remedy needs nothing in the Robotics lane: no fixture change, no
`source_ref` addition, no Robotics-specific rights store, no second registry axis and no new
`auth_class` value — only the eleven §2 prefixes, each naming a family the rights owner has
approved rather than one approved by analogy (#7780 issuecomment-5814333887).

**Resolved 2026-09-25 by #7780 issuecomment-5825621672 item 6.** The eleven prefixes are
approved for RECOGNITION at `rights_class: unresolved`. The measured consequence above is
therefore not a pending risk but the ruled-correct steady state: the vertical serves nothing
from these publishers, and now refuses explicitly rather than from ignorance — item 4 of the
same ruling ("the emission path may not publish from ignorance"). Promotion of any single
family to a serving rights class requires its own reviewed terms, later.

## 3. Refusal behaviour while pending (per family) and the tests that already pin it

Required behaviour for every family in §2 while `rights_class: unresolved`, and what the code at the pin actually does:

1. **Emission boundary.** `engine.theme_graph.rights.assert_current_emission_allowed([family], snapshot=…)` (`rights.py:211-241`) raises `RightsRefusal` for any class outside `EMISSION_OK` (`rights.py:47`: only `derived_display_ok`, `direct_display_ok`), so `unresolved` refuses. On the shared transport, `app/theme_research.py::_filter_bundle_for_rights` (`:190-238`) maps `source.source_uri` (falling back to `source.locator`, then `""`) through `family_for_source_ref`, asks the owner's verdict on a **fresh snapshot** once per family, drops every assertion of a refused family before composition, and the route reports only `rights_refused_families_hidden` — never the family name. At this pin the transport composes through the semiconductor composer only (`app/theme_research.py:44,48,337`); the Robotics composer is not wired yet.
2. **Dependent prose/evidence — required vs today.** Required (Sol 5814333887 §4): refusal includes dependent prose and evidence. Today: (a) dropped assertions never reach a composer, so no view row, no fact/target summary item and no evidence object derived from them can be emitted; (b) BUT `_filter_bundle_for_rights` copies `interpretation_blocks` through unfiltered (`app/theme_research.py:234`), and the Robotics composer (the seat's own file, carrier `55e6fe150bec`, `engine/market_ontology/robotics_theme_research.py::_summary`, `:923-993`) treats a block whose `input_revisions` are not all in the selection as **stale — `why_it_matters` and `offset` items labelled `[stale interpretation]`, `interpretation_stale` limitation, summary status `degraded` — not withheld; and the block's `falsifier` / `missing_measurement` watcher text reaches `summary.next_evidence` with no mark at all** (the stale-labelling loop covers only the first two channels). That labelling is the accepted RBV law for time-scoped staleness (inputs present in the bundle but outside the selection); for an input that is ABSENT from the bundle (which is what a rights drop upstream looks like to the composer) it is a divergence from "refusal includes dependent prose". **Seat fix committed on #7908 as `e57230d3da58` (Robotics side, this seat's file; independent review pending at the time of writing):** withhold any interpretation block whose `input_revisions` include a revision absent from the bundle's assertions — all three channels — counted once as `interpretation_inputs_absent:<n>`, never labelled through. **Transport side (shared owner):** `_filter_bundle_for_rights` should drop or mark interpretation blocks that cite a dropped assertion; registered on #7870 with this reference. Robotics-side, a bundle whose caller populated `omissions` is marked `rights_partial` and never names the withheld family (RBV-27; composer `:401-405` at `55e6fe150bec`).
3. **Independent authorised content untouched.** Assertions of other families are kept (per-family verdict memo); no global shutdown, no public/fixture fallback.
4. **Gap at this pin (observed, shared owner's file).** `_filter_bundle_for_rights` lets an **unmapped** `source_uri` (`family_for_source_ref` → `None`) PASS THROUGH ("the registry has no opinion, so we have none either", `app/theme_research.py:195-196, 210-213`). Every Robotics host is unmapped today, so before the §2 prefixes exist the transport would not refuse a Robotics bundle at all; Sol's option-A ruling (#7780 5813801605) states emission fails closed on unmapped rights families. The Robotics seat does not edit that file; it registers the divergence with the shared owner on #7870 alongside this reference. No live Robotics bundle loader exists yet (R5 held), so there is no live exposure now. Registering the §2 prefixes with `unresolved` is what turns pass-through into refusal under the existing gate — that is the operational reason the prefix table is part of this proposal.

Tests in the repo that already pin the fail-closed law (names, no changes; the two marked "permissive side" pin that a permitted class is served, i.e. no global shutdown):

- `tests/test_theme_sources_registry.py`: `test_every_family_row_carries_a_review_record`, `test_rights_module_reads_this_registry`, `test_sec_edgar_family_is_display_ok_but_never_redistributable`.
- `tests/test_theme_research_rights_refresh.py`: `test_rights_revocation_changes_snapshot_without_process_restart`, `test_missing_registry_refuses`, `test_unparseable_yaml_refuses_as_corrupt`, `test_unknown_family_refuses_and_names_it`, `test_refusal_names_the_family_and_its_rights_class`, `test_unknown_rights_class_in_a_snapshot_refuses_closed`.
- `tests/test_theme_research_api.py`: `test_revoked_rights_warm_drops_assertions_after_registry_flip`, `test_tightening_the_rights_owner_drops_assertions_through_the_route`, `test_owner_permitting_keeps_assertions_with_no_rights_limitation` (permissive side), `test_transport_carries_no_local_rights_restatement`, `test_missing_rights_registry_fails_closed_with_private_headers`, `test_missing_rights_registry_fails_closed_on_the_evidence_route_too`.
- `tests/test_theme_graph_local_plane.py`: `test_L_the_rights_gate_refuses_a_family_that_may_not_be_emitted`, `test_L_the_rights_gate_passes_the_display_classes` (permissive side), `test_L_an_unregistered_family_fails_closed`, `test_L_both_live_vendor_families_are_registered_and_refuse_today`, `test_L_the_guard_fails_closed_on_an_unregistered_source_family` (node/store families at the local plane — a different boundary from the transport's source_uri pass-through in item 4).
- `tests/test_market_ontology_exposure_map.py`: `test_rights_suppression_emits_typed_null_and_leaks_nothing`.
- Robotics: `tests/test_market_ontology_robotics_theme_research.py` RBV-27 (`rights_partial` present, withheld families never named) and the `rights_partial.json` fixture.

## 4. Adjudication questions and representation gaps — DISPOSED 2026-09-25

> **Disposition under #7780 issuecomment-5825621672.** Q1, Q2 and Q3 are **deferred by
> design**, not blockers: item 6 requires each family's own reviewed terms before any
> promotion, and until then explicit refusal is correct behaviour. **G1 and G4 are closed as
> will-not-build** — item 6 refuses a second rights axis and a new `auth_class` value, so the
> issuer-vs-wrapper distinction, the second publisher on one host (Twinny on Orbbec's page) and
> the "reachable but text-and-data-mining-restricted" acquisition fact stay recorded in
> `source_route` and in the §1 matrix rows, and are not expressible in the registry grammar by
> ruling. **G2 is closed by item 5**, which admits family `sec_edgar` at exact prefix
> `https://www.sec.gov/Archives/` (`keyless_public`, `direct_display_ok`, SEC Website
> Dissemination policy basis — explicitly NOT "federal-government works"). **Q4 is confirmed**
> by item 4: unmapped assertions fail closed on emission and dependent interpretation blocks are
> withheld with their sources; the queued Robotics composer fix and the R5 acceptance test stand
> unchanged.
>
> One sequencing call this lane owns: item 5 makes §2's preferred Teradyne alternative real (drop
> `teradyne_ir_sec_wrapper`, re-point the locator at the authoritative EDGAR copy). It is
> **deliberately not taken yet** — the copy actually retained is the IR page, every
> `retention_ref` is still a `research-vault://fixture/…` placeholder, and claiming `sec_edgar`
> for an EDGAR document nobody fetched would assert a source we do not hold. The IR row stays
> `unresolved`; the re-point is an R5 item behind a real acquisition receipt.

The original questions and gaps are preserved verbatim below as the record of what was inspected.


- **Q1 (exchange wrappers).** JPX and HKEX rows: the issuer authored the document, but our copy was retrieved through an exchange wrapper whose terms (READ) prohibit commercial secondary use and restrict generative-AI use (JPX), or grant personal use only and prohibit text-and-data mining and scraping for any purpose including AI training (HKEX). Does the wrapper's site licence govern our retention, automated extraction and factual synthesis of the issuer's disclosure for an entitled commercial consumer, or does the issuer's public-disclosure status govern? Until answered: refused, including the 39 HDS assertions that are the largest positive witness in the corpus. The acquisition method of the retained copies is part of this question (G4).
- **Q2 (explicit no-display vendors).** Orbbec, Zebra and Stabilus state that reproduction/display without permission is prohibited. Proposed representation is deliberately limited to facts-with-attribution and a link (no quotation, no display of page content). Is original factual synthesis with attribution, served privately to entitled users, within those terms? If not, the corresponding RBV cases (02/12/15, 10, 04) cannot be served from these sources.
- **Q3 (unreachable/silent publishers).** Parker, PTC, Hexagon (governing terms) are unreachable to automated reads; 1X's terms link is 404; ROBOTIS has no terms page. A human read of those pages (browser, no automation) is a credential-free ceremony this seat can perform only through a human-driven browser session; until then those rows stay `terms_unreachable` and refused.
- **Q4 (interpretation dependence) — a divergence today, not an open question.** §3.2: rights-dropped inputs leave their interpretation blocks labelled stale rather than withheld. Seat fix queued (Robotics composer); transport half registered with the shared owner. Acceptance test for R5: a bundle with one rights-dropped assertion serves no interpretation text that cites it.
- **G1 (representation gap: grain).** Current source law keys `rights_class` per family and recognises a family per URL prefix; a prefix can name only one family, so the issuer-vs-wrapper distinction that Sol asked us to preserve, and a second publisher on one host (Twinny on Orbbec's page), cannot be expressed as two families for one prefix. §2 records them in `source_route` and the matrix keeps the rows. If adjudication wants distinct rights for the issuer content and the wrapper, or per-publisher rights on one host, the registry needs a second axis (e.g. `wrapper_of:` / `publisher:` keyed on the assertion's `source.publisher`), which is the shared owner's change to design, not this seat's.
- **G2 (representation gap: EDGAR by prefix and wrapper-of).** `SOURCE_PREFIX_FAMILY` carries no `https://` prefix at #7870 3e3a7956d014, so `sec_edgar` — the one admitted external family — is not recognised from a `source_uri` either, and nothing can say "same document, different host". Robotics' Teradyne witness should point at the EDGAR archive URL (fixture change in a later lane); the missing `https://www.sec.gov/Archives/edgar/` prefix is the shared owner's item. **Measured 2026-09-25 (§2.1): the gap is not confined to `sec_edgar` — no Robotics host resolves to any family, so the emission path withholds the entire corpus, not just the EDGAR-sourced part.**
- **G3 (per-publisher terms ≠ per-class family).** Eleven families is the smallest set that does not force one rights class over incompatible terms. If Sol prefers class-level families, the registry needs per-prefix review rows; that is the same second-axis gap as G1.
- **G4 (acquisition-method restrictions).** `auth_class` values (house, keyless_public, receipted_scrape, entitled, licensed) cannot record "publicly reachable without credentials but automated collection / text-and-data mining restricted by the host's terms", which is what the JPX and HKEX pages say. `keyless_public` would silently overstate the permission; `receipted_scrape` describes a method, not a right. The registry needs either a new `auth_class` value or an acquisition-restriction field.

## 5. Honesty statement (M7)

- READ = a sentence extracted verbatim from a page fetched in the window and listed in Appendix A (one JPX clause is a sentence fragment as retrieved and is marked so). INFERRED = a scope conclusion this document draws (marked as such in the matrix). Nothing here paraphrases a licence as permission. No page body was retained; only URL, status, bytes, final URL, UTC time, page title and at most two clauses per page were kept. Where a page's earlier extraction missed a clause the independent review found on point (the JPX generative-AI clause; the HKEX text-and-data-mining clause), the matrix now carries that clause and drops a less specific one, staying within two clauses per page.
- Fetch method: `curl -sL --max-time 30` with the user agent `Mastermind-GMI-rights-review/1.0 (read-only terms inspection; no crawl)` — a DEVIATION from the packet's mandated string `Mastermind-GMI-rights-qualification/1.0 (read-only terms inspection)`, recorded here; same purpose declaration, different product token. Three pages (Parker home, PTC home, hexagon.com terms of use) were additionally attempted through the seat's built-in fetch tool and returned HTTP 403 with no body retrieved (status only; bytes and exact time not exposed by that tool). No filing, catalogue, case study, press release or data file was fetched; no login, registration, interactive acceptance or API was used; at most four pages per host (the HKEX group terms page was read twice; the second read is the last row of Appendix A). `https://www.teradyne.com/` and its robots.txt were fetched while locating the IR host's governing terms; they are cited by no row and www.teradyne.com is not a corpus host. Byte counts are as returned to this seat's fetch; dynamic pages (the HKEX terms page returned 260,504 bytes at 13:24:35Z and 377,500 bytes at 13:48:04Z) vary between fetches.
- Not inspected: any issuer corporate-site licence for Harmonic Drive Systems, Sanhua or Twinny (their documents were reached only through the wrapper/host rows); QuoteMedia's terms (third-party market data on the Teradyne IR host, not used by the corpus).

## Appendix A — every URL fetched (URL · HTTP status · bytes · final URL · UTC time · title)

| URL | HTTP | bytes | final URL | UTC | title |
|---|---|---|---|---|---|
| https://www2.jpx.co.jp/ | 403 | 271 | https://www2.jpx.co.jp/ | 2026-09-24T13:21:55Z | 403 Forbidden  |
| https://www2.jpx.co.jp/robots.txt | 404 | 268 | https://www2.jpx.co.jp/robots.txt | 2026-09-24T13:21:56Z | 404 Not Found  |
| https://www.jpx.co.jp/ | 200 | 56558 | https://www.jpx.co.jp/ | 2026-09-24T13:21:57Z | 日本取引所グループ  |
| https://www.jpx.co.jp/robots.txt | 200 | 69 | https://www.jpx.co.jp/robots.txt | 2026-09-24T13:21:58Z |  |
| https://www1.hkexnews.hk/ | 200 | 9175 | https://www.hkexnews.hk/index.htm | 2026-09-24T13:21:58Z | HKEXnews  |
| https://www1.hkexnews.hk/robots.txt | 404 | 2057 | https://www1.hkexnews.hk/robots.txt | 2026-09-24T13:22:04Z | Hong Kong Exchanges and Clearing Limited  |
| https://www.hkexnews.hk/ | 200 | 9175 | https://www.hkexnews.hk/index.htm | 2026-09-24T13:22:07Z | HKEXnews  |
| https://www.hkexnews.hk/robots.txt | 404 | 2057 | https://www.hkexnews.hk/robots.txt | 2026-09-24T13:22:14Z | Hong Kong Exchanges and Clearing Limited  |
| https://www.orbbec.com/ | 200 | 397425 | https://www.orbbec.com/ | 2026-09-24T13:22:15Z | Home - ORBBEC - Leading Provider of Robotics and AI Vision  |
| https://www.orbbec.com/robots.txt | 200 | 172 | https://www.orbbec.com/robots.txt | 2026-09-24T13:22:18Z |  |
| https://discover.parker.com/ | 200 | 865 | https://discover.parker.com/ | 2026-09-24T13:22:19Z |  |
| https://discover.parker.com/robots.txt | 200 | 43 | https://discover.parker.com/robots.txt | 2026-09-24T13:22:21Z |  |
| https://www.parker.com/ | 403 | 368 | https://www.parker.com/ | 2026-09-24T13:22:24Z | <TITLE>Access Denied  |
| https://www.parker.com/robots.txt | 403 | 382 | https://www.parker.com/robots.txt | 2026-09-24T13:22:27Z | <TITLE>Access Denied  |
| https://www.robotis.com/ | 200 | 51999 | https://www.robotis.com/en/ | 2026-09-24T13:22:30Z | ROBOTIS / Actuator for Physical AI  |
| https://www.robotis.com/robots.txt | 200 | 384 | https://www.robotis.com/robots.txt | 2026-09-24T13:22:34Z |  |
| https://robotics.hexagon.com/ | 200 | 92715 | https://robotics.hexagon.com/ | 2026-09-24T13:22:39Z | Home - Hexagon Robotics  |
| https://robotics.hexagon.com/robots.txt | 200 | 139 | https://robotics.hexagon.com/robots.txt | 2026-09-24T13:22:49Z |  |
| https://hexagon.com/ | 403 | 5508 | https://hexagon.com/ | 2026-09-24T13:22:55Z | Just a moment...  |
| https://hexagon.com/robots.txt | 403 | 5560 | https://hexagon.com/robots.txt | 2026-09-24T13:23:00Z | Just a moment...  |
| https://www.zebra.com/ | 200 | 409317 | https://www.zebra.com/us/en.html | 2026-09-24T13:23:04Z | Zebra: The World’s Foundation for Intelligent Operations / Zebra  |
| https://www.zebra.com/robots.txt | 200 | 9436 | https://www.zebra.com/robots.txt | 2026-09-24T13:23:07Z |  |
| https://www.1x.tech/ | 200 | 30978 | https://www.1x.tech/ | 2026-09-24T13:23:12Z | 1X / Home Robots  |
| https://www.1x.tech/robots.txt | 404 | 11571 | https://www.1x.tech/robots.txt | 2026-09-24T13:23:17Z |  |
| https://www.ptc.com/ | 403 | 363 | https://www.ptc.com/ | 2026-09-24T13:23:21Z | <TITLE>Access Denied  |
| https://www.ptc.com/robots.txt | 403 | 377 | https://www.ptc.com/robots.txt | 2026-09-24T13:23:25Z | <TITLE>Access Denied  |
| https://investors.teradyne.com/ | 200 | 44273 | https://investors.teradyne.com/ | 2026-09-24T13:23:27Z | Teradyne, Inc. (TER)  |
| https://investors.teradyne.com/robots.txt | 200 | 90 | https://investors.teradyne.com/robots.txt | 2026-09-24T13:23:29Z |  |
| https://www.teradyne.com/ | 200 | 282242 | https://www.teradyne.com/ | 2026-09-24T13:23:31Z | The leader in semiconductor test &amp; robotics  |
| https://www.teradyne.com/robots.txt | 200 | 128 | https://www.teradyne.com/robots.txt | 2026-09-24T13:23:35Z |  |
| https://group.stabilus.com/ | 200 | 60814 | https://group.stabilus.com/ | 2026-09-24T13:23:39Z | Stabilus Group - YOUR MOTION. OUR SOLUTION.  |
| https://group.stabilus.com/robots.txt | 200 | 640 | https://group.stabilus.com/robots.txt | 2026-09-24T13:23:43Z |  |
| https://www.jpx.co.jp/term-of-use/index.html | 200 | 52471 | https://www.jpx.co.jp/term-of-use/index.html | 2026-09-24T13:24:29Z | サイトのご利用上の注意と免責事項 / 日本取引所グループ  |
| https://www.jpx.co.jp/english/term-of-use/index.html | 200 | 48122 | https://www.jpx.co.jp/english/term-of-use/index.html | 2026-09-24T13:24:30Z | Disclaimer/ Terms of Use / Japan Exchange Group  |
| https://www.hkexnews.hk/disclaimer.htm | 404 | 2255 | https://www.hkexnews.hk/disclaimer.htm | 2026-09-24T13:24:31Z | Hong Kong Exchanges and Clearing Limited  |
| https://www.hkex.com.hk/Global/Exchange/Terms-of-Use?sc_lang=en | 200 | 260504 | https://www.hkex.com.hk/Global/Exchange/Terms-of-Use?sc_lang=en | 2026-09-24T13:24:35Z |  |
| https://www.orbbec.com/terms-and-conditions/ | 200 | 218283 | https://www.orbbec.com/terms-and-conditions/ | 2026-09-24T13:24:37Z | Terms and Conditions / Orbbec  |
| https://robotics.hexagon.com/imprint/ | 200 | 70274 | https://robotics.hexagon.com/imprint/ | 2026-09-24T13:24:41Z | Imprint - Hexagon Robotics  |
| https://www.zebra.com/us/en/about-zebra/company-information/legal/terms-of-use.html | 200 | 309641 | https://www.zebra.com/us/en/about-zebra/company-information/legal/terms-of-use.html | 2026-09-24T13:24:41Z | Terms of Use / Zebra  |
| https://www.1x.tech/terms-and-conditions | 404 | 906 | https://www.1x.tech/terms-and-conditions | 2026-09-24T13:24:43Z | 404 - Page not found  |
| https://investors.teradyne.com/disclaimer | 200 | 20600 | https://investors.teradyne.com/disclaimer | 2026-09-24T13:24:43Z | Disclaimer :: Teradyne, Inc. (TER)  |
| https://group.stabilus.com/legal-notice | 200 | 45817 | https://group.stabilus.com/legal-notice | 2026-09-24T13:24:44Z | Legal Notice / Stabilus Group  |
| https://www.robotis.com/en/policyterms.php | 404 | 216 | https://www.robotis.com/en/policyterms.php | 2026-09-24T13:24:46Z | 404 Not Found  |
| https://investors.teradyne.com/disclaimer | 200 | 20600 | https://investors.teradyne.com/disclaimer | 2026-09-24T13:26:53Z | Disclaimer :: Teradyne, Inc. (TER) [re-read] |
| https://www.hkex.com.hk/Global/Exchange/Terms-of-Use?sc_lang=en | 200 | 377500 | https://www.hkex.com.hk/Global/Exchange/Terms-of-Use?sc_lang=en | 2026-09-24T13:48:04Z | HKEX Terms of Use [re-read for the TDM clause] |
| https://www.parker.com/ (built-in fetch tool) | 403 | n/a (body not retrieved) | n/a | within the window; exact time not exposed by the tool | — |
| https://www.ptc.com/ (built-in fetch tool) | 403 | n/a (body not retrieved) | n/a | within the window; exact time not exposed by the tool | — |
| https://hexagon.com/legal/terms-of-use (built-in fetch tool) | 403 | n/a (body not retrieved) | n/a | within the window; exact time not exposed by the tool | — |
