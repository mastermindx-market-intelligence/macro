---
key: NEWS-IMPACT-BENCHMARK-BODY-SOURCE
question: >
  The commission D benchmark (600 cases, 200 per template) grades critical-numeric
  correctness and span-cited transfer edges, so every graded case needs an article body
  with byte offsets. The qbus news tape that defines the population carries headlines and
  publisher names only, no bodies, and the repository has no general multi-source rights
  registry. Where do benchmark bodies come from, under what rights state, how is a tape row
  with no body counted, and what does the sampler's rights_allow gate key on?
answer: >
  BODY SOURCE. The body of a benchmark case is the issuer's own SEC EDGAR 8-K: the primary
  document plus any EX-99.x exhibit, for filings carrying Item 1.01, 2.02, 7.01 or 8.01.
  Bodies are fetched only through the existing SEC owners: submissions through
  collectors/edgar_forensics.SecForensicsCollector.retrieve_current(cik, "submissions"),
  documents through collectors/sec_document_spine.SecFilingArchiveCollector.fetch_document
  with an exact https://www.sec.gov/Archives/ URL, and pacing through the shared
  collectors/sec_request_pacer.SecRequestPacer. No new HTTP client, cache, pacer or archive
  is written.
  SPANS. Each body is minted as engine/company_intelligence/documents.SourceDocument with
  source_class primary_filing and rights_state internal_only, and every label span is cut
  with documents.text_span and re-checked with documents.verify_span against the body
  sha256 before it is graded.
  RIGHTS. The benchmark corpus is internal_only. It is never displayed, excerpted or linked
  on any product surface. Display of SEC filing text stays held exactly as
  DEC:FINANCE-SEC-EVIDENCE-RIGHTS-HELD-UNTIL-FAMILY-ADMITTED rules, until the theme-source
  registry owner admits a sec_edgar family. This program writes no row into
  config/theme_sources.yml and keeps no second rights table. Reading 8-K text with a model
  for internal measurement follows the existing engine/earnings_qual._fetch_8k_press_release
  precedent and changes no source license.
  MATCHING. A tape row matches a body when the row's issuer resolves to a CIK and that CIK
  filed a qualifying 8-K within one trading session of the row's seendate. A row with no
  match is recorded as deferred with reason body_unavailable. Deferred rows are counted per
  template and per cell and printed in the manifest. They are never dropped silently and
  never padded.
  SCORING. Material-event routing recall is measured on the full drawn population,
  headline only. Critical-numeric correctness and unsupported-transfer grading are measured
  only on cases that have a verified body. If body coverage leaves a template short of 200,
  the graded population is the body-available subset, the restriction is printed with its
  counts, and the short cell stays short. Template T3 (strategic partnership) is expected
  to come up short because many partnerships are not 8-K events, and is reported short.
  GRADED DRAW (amended 2026-10-14). Grading only the body-available rows of the routing
  draw would leave 73 of 484 cases. So the graded population is a SEPARATE draw, made with
  the same seed (20261014), sampler (ni-sampler-1), caps and inputs, over a frame of the
  candidates that have a body. The frame is outcome-blind. It is the edgar_body status map
  for the full pool of 2,837 candidates (status_map sha256 66ce529d…) and reads only
  whether an issuer-filed body exists. 235 candidates are in the frame. The rest are
  excluded: 1,271 with no_cik and 1,331 with no_qualifying_8k. The graded draw (manifest
  bd2f1b0b…) holds 157 cases: T1 68, T2 66, T3 23. Every cell's shortfall against
  90/50/30/30 is printed in its report. The 484-case full-pool draw (manifest 94e80a34…)
  stays the routing-recall population. The frame restricts graded metrics to issuers that
  file 8-Ks, and graded results are reported with that scope. Frozen records live under
  research/prophet_v4/news_to_business_impact_20261006/benchmark/.
  LABELER FAMILIES. A6 label returns name the model family by token only: fam_a is
  MiniMax-M3, fam_b is qwen3.7-plus, fam_c is cursor-grok-4.6-high. The first pass is
  fam_a plus fam_b. fam_c labels only the cases that the first pass routes to a third family.
  RIGHTS GATE. The sampler's rights_allow decision keys on the source class of the body
  receipt (EDGAR primary_filing, internal_only), never on the headline publisher.
  Headline publishers are internal recall metadata only. A Benzinga row counts as Benzinga
  only under its existing qbus receipt.
rationale: >
  The benchmark measures whether a packet's numbers and edges are supported by text. A
  headline cannot support a number it does not contain, and the tape carries no bodies, so
  the body has to come from somewhere with a provable byte identity. The issuer's own 8-K
  is the only source that is (a) already fetched by audited owners in this repository,
  (b) public primary disclosure with no vendor license to clear, (c) addressable by CIK,
  which the tape already resolves, and (d) hashable, so a span can be replayed later. The
  three templates map onto the 8-K items that carry them: 2.02 and 7.01 for
  demand/guidance, 1.01 and 8.01 for capital allocation and partnerships. Keeping the
  corpus internal_only and leaving display to the Finance DEC avoids both forbidden moves:
  editing the rights registry from a consumer, and keeping a private rights table beside
  it. Scoring recall on headlines and numeric correctness only on bodies keeps each metric
  honest about its own evidence. A short T3 is a real finding about where partnerships are
  disclosed, and padding it would hide that.
alternatives:
  - option: Fetch the vendor article bodies behind each tape headline (GlobeNewswire, Zacks, Reuters and the rest).
    why_not: >
      Each publisher is a separate license, and no rights registry admits any of them. A
      consumer program may not decide those rights, and masterplan section 13 forbids
      source-license changes.
  - option: Grade numeric correctness against the headline text alone.
    why_not: >
      Most headlines carry no number, so the metric would grade almost nothing, and it would
      reward packets that copy the headline instead of reading the disclosure.
  - option: Keep a benchmark-local rights table admitting sec_edgar for this corpus.
    why_not: >
      DEC:FINANCE-SEC-EVIDENCE-RIGHTS-HELD-UNTIL-FAMILY-ADMITTED forbids a second rights
      table; internal_only needs no admission because nothing is displayed.
  - option: Pad short templates with synthetic or LLM-written bodies.
    why_not: >
      DNR:KILL-LLM-ORIGINATION. A synthetic body grades the generator, not the packet, and
      short cells are printed, never padded.
  - option: Write a new EDGAR client for 8-Ks.
    why_not: >
      SecForensicsCollector, SecFilingArchiveCollector and SecRequestPacer already own SEC
      retrieval, pacing (concurrency group filing-forensics-sec) and receipts. A second
      client would break the shared pacing budget.
evidence:
  - "collectors/edgar_forensics.py:227 SecForensicsCollector; :368 retrieve_current(cik, endpoint) returns body bytes and headers without persistence."
  - "collectors/sec_document_spine.py:806 SecFilingArchiveCollector; :856 fetch_document refuses any URL not under https://www.sec.gov/Archives/."
  - "collectors/sec_request_pacer.py:14 SecRequestPacer is the shared SEC pacer."
  - "engine/company_intelligence/documents.py:153 SourceDocument; :375 text_span; :470 verify_span(span, *, segment_text, body_sha256)."
  - "engine/earnings_qual.py:1517 _fetch_8k_press_release already sends Item 2.02 8-K text to a model for internal scoring."
  - "engine/news_impact/sampler.py:97 RightsRefused; draw_sample(..., rights_allow) refuses any case whose rights key is not allowed."
  - "config/theme_sources.yml on origin/main has rows for mastermind_curated, finviz_themes and ths_concepts only; git grep sec_edgar finds no rights row."
  - "Tape census (seat, 2026-10-14): 55,110 rows, no body field; headline-family calibration in PHASE0_FREEZE section 8."
  - "Body fetch (seat, 2026-10-14, ni-edgar-body-1): 2,837 candidates, 474 submissions, 243 indexes, 489 documents, 79,149,824 bytes; 235 available, no_cik 1,271, no_qualifying_8k 1,331, zero fetch failures (benchmark/body_frame/body_report.json)."
  - "Routing draw: 484 cases, 73 with a body, 411 body_unavailable (benchmark/routing/draw_report_body.json)."
  - "Graded draw: python -m engine.news_impact.tape_draw ... --seed 20261014 --body-frame status_map.json reproduces benchmark/graded/manifest.json and cases.jsonl byte for byte (seat re-run, 2026-10-14); 157 cases, short 443 of 600."
affects:
  - "WS:PROPHET-NEWS-IMPACT"
  - "engine/news_impact/tape_draw.py"
  - "engine/news_impact/edgar_body.py"
  - "research/prophet_v4/news_to_business_impact_20261006/benchmark/**"
confidence: high
reversibility: easy
decided_by: fable-meta-ceo-seat-0e739467 (recovered fork 959095da) under the Chairman delegation of 2026-10-10
decided_at: 2026-10-14
---

# Benchmark body source: issuer 8-Ks, internal only

Wave w2 grades packets against text. The tape has no text, so the issuer's own 8-K is the
body, fetched only through the existing SEC owners, held internal_only, and never
displayed until the registry owner admits a sec_edgar family. Rows with no matching 8-K
are counted as `body_unavailable`. Routing recall still uses every drawn row. Numeric and
transfer grading run on a separate draw over the body-available frame, with the same seed
and sampler. That draw has 157 cases against a target of 600. Short templates are printed
short.
