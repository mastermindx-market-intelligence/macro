---
key: CS-V2-TRANSACTION-RECONCILIATION-X0
question: >
  Masterplan task X0 (research/capital_structure/e2e_20261013/MASTERPLAN.md
  §13; acceptance rows A15, A20, A23, A24 and A27; line 98) must reconcile
  what actually happened: priced takedowns, at-the-market sales, warrant
  exercises, conversions, redemptions, repurchases and cancellations, and the
  share and cash changes they caused. Issuers report the same sales twice:
  as individual transactions (424B pricing supplements, 8-Ks) and as
  cumulative figures (an ATM programme's sales-to-date in a 10-Q). Instrument
  balances are reported as point-in-time tables. How are these combined so
  that shelf and programme usage, instrument outstanding and realized cash
  are each counted exactly once, and what is the honest answer when the
  history is incomplete?
answer: >
  X0 adds three evidence-record families and one deterministic reconciler.
  (1) C0 2.2.0 (stacked on I1a's 2.1.0) registers
  capital_structure.transaction_observation.v1 (one reported fact with its
  reporting basis: individual, cumulative over a stated window, or a
  point-in-time balance; canonical_extraction or adjudicated_gold only),
  capital_structure.transaction_binding.v1 (an observation bound to a
  registration path by an exact, unique file number, or to an instrument by
  adjudicated gold only, with a transaction_id that collapses the same event
  seen in several documents) and
  capital_structure.transaction_filing_coverage.v1 (an attestation, produced
  only by the X0b extractor from the E0 filing index, that every filing of
  one form class in a date range was retrieved and read). Existing 2.0.0 and
  2.1.0 digests are byte-identical. (2)
  engine/capital_structure/transactions.py reconcile_transactions computes
  usage per shelf path and per ATM programme by window coverage: contained
  cumulative windows are dominated, individual events inside a window are
  covered and never add, events outside every window add, and partially
  overlapping windows or a contained window larger than its container are
  unknown or contradicted, never apportioned. Usage is known only when
  completeness reaches the as_of date, either through a contiguous chain of
  cumulative windows from inception or, for a shelf, through a 424B filing
  coverage attestation. Otherwise it is unknown with an evidenced floor,
  which C2 uses as the bound for remaining capacity. Instrument outstanding
  is the latest reported balance plus or minus the flows after it, never the
  flows already reflected in it; apply_outstanding feeds that balance to
  I1's supply evaluation so issued shares are not counted again as overhang.
  Share reconciliation reports observed, evidenced and unexplained deltas
  separately and never plugs the difference. Realized cash (proceeds,
  repayment, no_cash) comes only from reported amounts and is a separate
  record from the scenario CashEffect. (3) A deterministic extractor (X0b)
  reads 424B final pricing supplements, 10-Q and 10-K ATM paragraphs and
  outstanding-balance tables from retained filing bytes; everything else,
  including 8-Ks, is deferred and enters only as adjudicated gold. It never
  reads a Rule 457 fee-table maximum as a sale. (4) Audit repair: usage,
  instrument versions and share reconciliation share one §4 interval window
  cover, so an event inside a counted window is listed but never added twice
  anywhere. A contradicted flow or contradicted usage yields no evidenced
  floor and no number, and the instrument balance it touches becomes
  contradicted rather than partly decremented. A cumulative window that
  straddles a balance or observation date, or partially overlaps another
  window, is unknown and never apportioned; a window wholly inside the
  interval after a balance is counted when it closes. Two balances for one
  instrument on one day that disagree are contradicted, never chosen between.
  Only plain decimal text is an exact amount, and apply_outstanding refuses a
  ledger dated after the instrument set it updates. The cash paid on a
  redemption or repurchase is the reported amount only; its principal is
  never taken as the cash paid, because a redemption can carry a premium or
  a discount. A share figure that states no availability time is never
  visible at the cutoff; it is a named unknown, not a reconciliation input.
rationale: >
  The two failure modes the masterplan names for this task are additive.
  Deducting a cumulative usage figure and the individual sales it already
  includes double-counts usage and understates remaining capacity (L98,
  A15). Treating a missing history as zero overstates it (A20). Counting a
  warrant that was exercised both as issued shares and as remaining overhang
  is review focus (2). Window coverage removes the double count without
  choosing between documents, and it makes the remaining uncertainty
  explicit: between periodic reports the honest ATM answer is "at least the
  floor, later sales not yet reported", which a capacity bound can use. A
  completeness claim needs evidence that no filing was missed, and
  individual events cannot provide that by themselves, so only a
  filing-index attestation or a contiguous chain of cumulative windows can
  make usage known. Keeping realized cash apart from scenario cash keeps
  facts and scenarios separate (A28-A30, review focus (5)). Signed deltas are
  carried as strings in dictionaries because a C0 Quantity is nonnegative by
  contract.
alternatives:
  - option: Deduct both the cumulative figure and every individual transaction
    why_not: Double-counts the same sales (L98, A15).
  - option: Prefer the cumulative figure and drop individual events entirely
    why_not: Loses sales after the last periodic report, so usage is
      understated and remaining capacity overstated between 10-Qs.
  - option: Treat a missing or partial history as zero usage
    why_not: Unknown is never 0 (A20); capacity would be overstated.
  - option: Apportion partially overlapping cumulative windows pro rata
    why_not: Invents a split the documents do not state.
  - option: Mutate I0 instrument status or outstanding in place
    why_not: I0 is accepted identity work; a new InstrumentSet with
      transaction provenance keeps the prior state and its digest intact
      (A27).
  - option: Plug an unexplained share delta into a residual issuance line
    why_not: Hides missing evidence; the delta is reported, not explained
      away.
  - option: Reuse the scenario CashEffect for realized cash
    why_not: Mixes facts with scenarios (review focus 5); realized cash must
      never be inferred from a scenario price.
  - option: Extract every document class, including 8-K narratives
    why_not: 8-K language is too varied for a deterministic extractor; those
      enter as adjudicated gold, and the transaction_id collapses them with
      the 424B record.
evidence:
  - research/capital_structure/e2e_20261013/MASTERPLAN.md line 98, line 258 review focus, §13 row X0 and §15 rows A15, A20, A23, A24, A27 (PR #9115 @93c82c90)
  - engine/capital_structure/issuer_state_contracts.py (Quantity, CalculationReceipt, FamilyState, InstrumentSet, ShareObservationRef, stable_id)
  - engine/capital_structure/registration_lifecycle.py and SPEC_L1 §A.3 (registration_path origin and intervals)
  - SPEC_C1 §6 (shelf_usage and continuing_offering deductions through UnknownResolution)
  - DEC:CS-V2-SUPPLY-ECONOMIC-TERMS-I1 (evaluate_supply consumes instruments_outstanding)
affects:
  - WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2
  - engine/capital_structure/issuer_state_contracts.py
  - contracts/capital_structure_state.v2.schema.json
  - engine/capital_structure/transactions.py
  - engine/capital_structure/transaction_extraction.py
  - masterplan tasks C2, S0 and U2 (consume usage, outstanding and realized cash; never re-derive them)
confidence: high
reversibility: costly
decided_by: fable-meta-ceo-a9559a4c
decided_at: 2026-10-14
---

# Each actual sale counts once; missing history is a floor, not zero (X0)

Cumulative and individual reports of the same sales are combined by window
coverage, so each sale reduces capacity once. Usage is known only when the
record is provably complete to the date asked about; otherwise it is an
evidenced floor with a named unknown. Instrument balances start from the
latest reported table, and realized cash comes only from reported amounts.
