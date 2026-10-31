---
key: FIF-PACK-GENERALIZATION-DEV-CORPUS
question: >
  The first Q1 generation shows two distinct causes behind every pack's
  unavailable_research_only label — cells too small for the frozen 0.80 Wilson
  floor even at perfect precision, and genuine pack defects off the AAPL gold
  (wrong values, invented extraction, non-generalizing selectors). How are pack
  repairs developed without contaminating the held-out set, and what reopens a
  failed family?
answer: >
  Two separate instruments, never mixed. (1) Pack repairs are developed against a
  DEVELOPMENT CORPUS of public EDGAR filings from issuers disjoint from the five
  held-out issuers (AAPL, SNOW, CAT, BAC, GOOGL) and from the AAPL gold; digest-only
  manifests enter git, bytes stay on a lane host stage; repair lanes write their
  own development assertions and never read held-out labels, the Q1 reports'
  false-positive rows, or the held-out stage. The seat plans repairs from the
  family-level failed_families rows only (section_family, numerator/denominator,
  reason_codes) and never from label values. (2) A failed family reopens only
  through a second Q0 split decision: a new labeling wave on additional fiscal
  years of the same five issuers (different from gold and from wave one), sized so
  each positive family reaches at least 16 trials — the smallest N at which a
  perfect cell clears the frozen 0.80 lower bound — labelled by independent
  labeler lanes, sealed, then measured by a new Q1 generation. The precision floor
  does not move.
rationale: >
  Reading held-out labels to fix a pack would turn the held-out split into a
  training set, and the protocol forbids relabelling, dropping cells or lowering N
  after a result (§10). At n=10 a perfect cell's Wilson lower bound is 0.722, at
  n=12 0.758, at n=14 0.785 and only at n=16 0.806, so most generation-one
  families could not have passed regardless of pack quality; that is a power
  problem the protocol already names (underpowered) and only more labels cure.
  The genuine defects (PK07 invented extraction on a negative, PK02 wrong EPS and
  SBC values, PK08 and PK01 abstaining on every non-AAPL filing) are visible at
  family level and are fixed by developing against other issuers' filings, which
  is exactly what the 250/1,000 coverage program will need anyway.
alternatives:
  - option: Let repair lanes read the held-out labels and false-positive rows
    why_not: Contaminates the held-out split; every later measurement would be a training-set measurement and A37 could never be satisfied on these labels.
  - option: Lower the precision floor or exempt perfect small cells
    why_not: The floor was predeclared before any result (DEC:FIF-Q1-PRECISION-FLOOR-PREDECLARED-0-80) and the protocol forbids moving it after a result.
  - option: Add more held-out issuers instead of more fiscal years of the same five
    why_not: New issuers change applicability (sector classes) and need contract, capture and witness work before a single label; more fiscal years of the five reuse the frozen contract and reach the N threshold faster. New issuers remain the coverage program's instrument.
evidence:
  - "reports/q1_held_out_20261031: perfect-precision families flagged precision_below_floor by N alone — PK01 liquidity 10/10, maturity_schedule 5/5, PK06 lease_liability 12/12, PK07 goodwill_intangibles 8/8, PK09 icfr_opinion 6/6"
  - "Wilson 95% lower bound at k=n: n=10 0.722, n=12 0.758, n=14 0.785, n=16 0.806, n=20 0.839; one miss needs n>=25 (0.805)"
  - "Genuine defects at family level: PK02 eps 12/20, sbc 3/6, share_counts 7/10; PK03 segments 1/6; PK05 income_tax 17/20, utp 15/23; PK07 impairment_testing fp_on_negative + invented_extraction, business_combination 0/5 recall; PK08 legal_proceedings 0/4, loss_contingency 0/8 recall; PK01 debt_outstanding 2/8, covenant_text 0/3 recall"
  - "FIF_Q0_QUALITY_PROTOCOL.md §1 split law, §6 minimum N, §10 failed-family disposition"
affects:
  - WS:FINANCIAL-INTELLIGENCE-FABRIC
  - engine/fundamental_forensics/specialist_packs/
  - tests/fixtures/fundamental_forensics_held_out/
confidence: high
reversibility: easy
decided_by: "FIF Meta-CEO seat 96dc937a (Fable)"
decided_at: 2026-10-31
---

Pack repairs develop against a disjoint development corpus; failed families reopen only via a second Q0 split with ≥16 positive trials per family; the floor never moves.
