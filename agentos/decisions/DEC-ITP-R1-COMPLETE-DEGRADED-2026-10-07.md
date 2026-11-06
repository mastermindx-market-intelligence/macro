---
key: ITP-R1-COMPLETE-DEGRADED-2026-10-07
question: >
  The R1 completion spec (research/alpha_intelligence/expectation_market_dynamics/R1_COMPLETION_SPEC_2026-10-06.md)
  found all five R1 gaps OPEN and every path behind them UNOWNED, and left "decide that R1 is complete" with the
  source owners (seat decision D18). With no owner existing, does R1 stay open until someone else claims the paths,
  or does the program's own workstream owner designate itself and close R1 in the spec's degraded form?
answer: >
  R1 is COMPLETE IN DEGRADED FORM at the cutoff 2026-10-03T06:31:51Z. WS:ALPHA-INTELLIGENCE-INTEGRATION
  (owner fable, status active) is designated owner of the paths the spec's G1-G5 (b) lines mark UNOWNED, by
  adding them to its front-matter owns_paths: data/reference/, data/symbol_directory/, data/openfigi/,
  data/revisions/expectation_observations.parquet, data/revisions/expectation_attempts.parquet and
  collectors/equity_revisions.py. No live incumbent workstream owns any of them or their writers, so no other
  workstream is named. As owner it issues
  research/alpha_intelligence/expectation_market_dynamics/R1_OWNER_RECEIPTS_2026-10-07.json
  (schema r1-owner-receipts.v1). G1, G2 and G3 take the form DEGRADED_LABELED_ABSENCE, G4 takes
  OWNER_REFUSAL_NO_CLASS, and G5 takes CAPTURE_CLOCK_ONLY. Each gap quotes the spec's own (e) line verbatim
  as its exclusion rule. Issuer-level studies exclude the 724 unresolved names. Prospective studies exclude
  the 777 undated aliases. A study that needs currency, fiscal-year-end or basis excludes the missing field.
  Any rights-dependent use is excluded. Event-time studies are excluded. For G4, the refusal is recorded on
  the same source line as the literal (line 363). The value stays "UNKNOWN" and behaviour does not change.
  The readiness probe reports each gap as CLOSED, DEGRADED_ACCEPTED or OPEN. Its top-level r1_status is
  COMPLETE_DEGRADED only when every gap is CLOSED or DEGRADED_ACCEPTED. A gap is DEGRADED_ACCEPTED only when
  the owner receipt is present, its form and cutoff are right, the owning workstream's owns_paths cover the
  gap's (b) paths, and the stable counts equal the probe's own measurement.
rationale: >
  On 2026-10-06 the Chairman directed this program's seat to resolve owner and parent blocks itself rather than
  bounce them: "If there are blocks where u require some parent or owner or something, you should assess to see
  if u can do it yourself". DEC:ITP-SEAT-RELEASES-ADMINISTRATIVE-BLOCKS-UNDER-CHAIRMAN-2026-10-06 records the
  same delegation for holds. R1 is such a block. Nobody has to buy, rights-classify or backfill anything; it
  only needs an owner to issue receipts. The spec has an owner rule: only a workstream whose front-matter
  owns_paths covers a path is its owner. Under that rule no owner existed. The seat already holds
  WS:ALPHA-INTELLIGENCE-INTEGRATION, the workstream whose program consumes these artifacts. Designating it
  owner meets the rule as written and does not invent a new owner class. The degraded forms are the spec's
  own (e) lines, so the receipts add no data. They only make each absence an owner-acknowledged, labeled
  absence. That is the honest state of a yfinance-only, prospective collection: no issuer ids beyond 779, no
  dated aliases beyond 2, no currency/fiscal-year-end/basis, no rights decision and no source clocks. The
  closure is prospective only. Every exclusion stays in force. financial_influence, k3e_admissible and
  promotion_eligible stay false. This decision does not satisfy the spec's own HOLD-FOR-SOL addressed to
  owners. The ratification is a workstream-owner act under Chairman delegation, and is recorded as such,
  never as a Sol ruling.
alternatives:
  - option: Wait for Sol, or for another workstream, to claim the R1 paths and issue receipts
    why_not: >
      Under the spec's own owner rule nobody owns them, and no workstream is working toward claiming them. The
      Chairman explicitly classified owner/parent blocks of this program as resolvable by the seat. Waiting
      would leave R1 OPEN indefinitely with no change in the underlying data.
  - option: Backfill issuer ids, valid_from dates, fiscal fields or source clocks from tickers, CIKs, OpenFIGI or later filings
    why_not: >
      Forbidden by the spec's (e) lines and by program law (no fabricated history). An owner receipt is
      prospective only.
  - option: Buy a vendor point-in-time identity/clock feed
    why_not: >
      Procurement is a genuine money gate that stays with the Chairman. A feed fetched after the cutoff counts 0
      at this cutoff anyway.
  - option: Assign a rights class to the yfinance estimate rows
    why_not: >
      The rights vocabulary belongs to the shared-base owner (ASTRA/Chairman ruling 2026-09-24 on #7870: sector
      programs mint no rights vocabularies). The lawful owner act is a refusal that keeps UNKNOWN as a labeled
      absence.
  - option: Build an SEC/EDGAR identity collector now to close G1/G2 outright
    why_not: >
      Out of scope and prospective-only. A receipt fetched after the cutoff counts 0 at this cutoff. It stays
      a recorded future option that would upgrade a gap to CLOSED at a later cutoff.
evidence:
  - "python3 research/alpha_intelligence/expectation_market_dynamics/r1_readiness_probe.py --rev bb7847a33c5fcaa3d2963e3c6be18d3628493966 (v1, 2026-10-07): universe 1503 sha MATCH; issuer_id_resolved 779; undated aliases 777, dated 2; spine columns none, observation currency/fiscal_year/basis non-null 0/0/0; rights literal UNKNOWN at collectors/equity_revisions.py:363; source clocks non-null 0/0. All stable counts equal R1_READINESS_2026-10-06.json."
  - "Cohort counts at the cutoff re-measured equal to the spec: unchanged 276,724; same-anchor changed value 47,731; missing-after-good 303; rollover 2,561; correction-state unchanged/original/missing/supersedes 276,724/75,630/71,039/49,807."
  - "Owner census: git log -5 origin/main on each R1 path shows writers scripts/build_security_master.py (data/reference/*) and collectors/equity_revisions.py (data/revisions/*). Neither writer, nor any R1 path, is covered by any agentos/workstreams/*.md front-matter owns_paths at bb7847a3."
  - "R1_COMPLETION_SPEC_2026-10-06.md lines 27, 41, 55, 69, 83 (the (b) UNOWNED lines) and 33, 47, 61, 75, 89 (the (e) degraded paths, quoted verbatim in the receipts file)."
  - "The probe re-run on the PR head is committed as research/alpha_intelligence/expectation_market_dynamics/R1_READINESS_2026-10-07.json and reports r1_status COMPLETE_DEGRADED."
affects:
  - "WS:ALPHA-INTELLIGENCE-INTEGRATION"
  - "research/alpha_intelligence/expectation_market_dynamics/**"
  - "collectors/equity_revisions.py"
  - "data/reference/**"
  - "data/revisions/**"
confidence: high
reversibility: easy
decided_by: "seat: fable program-ceo session 2fc05761 (WS:ALPHA-INTELLIGENCE-INTEGRATION owner), under Chairman directive 2026-10-06; drafted by orchestrator A"
decided_at: 2026-10-07
review_by: 2026-11-07
---

# R1 complete in degraded form (2026-10-07)

The owner receipts are in `research/alpha_intelligence/expectation_market_dynamics/R1_OWNER_RECEIPTS_2026-10-07.json`.
The probe readback is `R1_READINESS_2026-10-07.json` in the same directory. The 10-06 receipt is kept unchanged as the
pre-designation baseline.

**Upgrade path.** A later prospective owner receipt upgrades its gap from DEGRADED_ACCEPTED to CLOSED at a later cutoff.
That can be real issuer ids, dated aliases, currency/fiscal-year-end/basis, a rights class issued by the shared-base
owner, or real source clocks. It never re-labels rows at or before 2026-10-03T06:31:51Z.

**Future option, not built.** A prospective SEC/EDGAR (or vendor) identity and clock receipt. At this cutoff it counts 0.

**What this does not change.** Every exclusion in the receipts stays in force. No K3E admission, financial influence,
promotion, rank or capital authority follows from R1's degraded completion.
