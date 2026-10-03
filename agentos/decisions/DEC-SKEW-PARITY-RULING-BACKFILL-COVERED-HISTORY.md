---
key: SKEW-PARITY-RULING-BACKFILL-COVERED-HISTORY
question: >
  What should we do about the 60% sign disagreement between the polygon_gex
  ledger and the ThetaData recompute
  (DSC:SKEW-THETADATA-RECOMPUTE-DIVERGES-FROM-POLYGON-LEDGER)?
answer: >
  Backfill the priceable covered history from the ThetaData store, and let a
  thetadata row replace a polygon_gex row for the same date and name. Keep
  each unpriceable row as polygon_gex, disclosed by the per-row source column.
  Leave weekend as-of rows out of emit. Ship one plain-language sentence about
  the source break on the options page in W2-5b. Do not change how a single
  chain is turned into a skew number.
rationale: >
  Of the 12,375 legacy polygon_gex keys, 3,965 can be priced from the store.
  Those two series disagree mostly because the spot does not match: more than
  2% on 1,680 keys, which is 46.4% of the absolute gap. Both implied-vol legs
  move. The tenor never moves. The legacy snapshots were priced at a different
  moment than the end-of-day close, so the ledger is two series. Index ETFs
  agree 87.5% under the current rule, which is evidence the strike rule is not
  what is wrong. Skew stays a display figure. A kill on using it to predict
  returns still stands. Recomputing the covered dates from the store makes
  that covered history one series. The 8,410 keys the store cannot price stay
  polygon_gex, and the source column says so. The 2,875 weekend-dated rows are
  as-of artifacts (2026-06-21 is a Sunday). The end-of-day store has no weekend
  sessions, so emit skips them instead of pretending they are sessions.
alternatives:
  - option: Disclosure only, leaving both series in the ledger as they are
    why_not: >
      A note would tell a reader the numbers come from two constructions. It
      would not make the covered history one series.
  - option: Change the strike, tenor, or spot rule inside the skew formula
    why_not: >
      Nothing in the parity receipt shows the strike rule is at fault. A
      formula change would need the gauntlet, and skew is display-tier, so
      that change is rejected.
evidence:
  - "research/MARKET_ONTOLOGY_F03_SKEW_PARITY_RECEIPT_2026-09-23.md — parity receipt for the covered keys (spot mismatch 46.4%, 1,680 keys over 2%; both IV legs move; tenor never)"
  - "PR #7756 — W2-4 parity audit, read only"
  - "W2-2 lane receipts: research/MARKET_ONTOLOGY_F03_SKEW_ACCRUAL_LANE_2026-09-22.md and DSC:SKEW-THETADATA-RECOMPUTE-DIVERGES-FROM-POLYGON-LEDGER (3,965 priceable keys, 8,410 unpriceable, 2,875 weekend rows)"
  - "python -m pytest tests/test_options_skew_backfill.py tests/test_options_skew.py tests/test_audit_options_skew_overlap.py tests/test_skew_accrual_launchd.py -q -p no:cacheprovider"
affects:
  - engine/options_skew.py
  - scripts/build_options_skew.py
  - tests/test_options_skew_backfill.py
  - data/options_skew/snapshots.parquet
  - "WS:OPTIONS-CONTEXT-AUDIT-PREREG-V2"
confidence: high
reversibility: easy
decided_by: "META-CEO A seat, packet A-F03-W2-4b, 2026-09-23"
decided_at: 2026-09-23
---

# Backfill the covered skew history from the store

The discovery this question cites records that the sign agrees on only 60
percent of the keys both sources can price (2,392 match, 1,563 flip). The
gap is mostly a spot mismatch: the legacy row was not priced at the
end-of-day close. Both volatility legs move with that spot. The tenor does not.

The covered dates are therefore recomputed from the store. Where the store
cannot price a name, the old row stays and the source column still says
polygon_gex. Weekend dates are not sessions in the store, so emit does not
treat them as the latest snapshot. The page that shows skew will say, in
ordinary words, that the source changed. That sentence is W2-5b's job. The
formula that turns one chain into one skew number does not change.

The old polygon numbers are still recoverable. They are in the git history of
the bootstrap ledger, in the commit from before the W2-2 lane, and R2 keeps
the earlier manifests.
