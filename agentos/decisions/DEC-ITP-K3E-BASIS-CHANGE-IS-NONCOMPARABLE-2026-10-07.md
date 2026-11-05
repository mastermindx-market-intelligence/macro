---
key: ITP-K3E-BASIS-CHANGE-IS-NONCOMPARABLE-2026-10-07
question: >
  The E1 K3E semantic-seam suite (tests/test_k3e_semantic_seam_qualification.py, three strict xfails marked
  GAP-E-BASIS) requires that a GAAP/non-GAAP, diluted/basic or cross-currency change is NOT recorded as a revision.
  The enrolled SRC-A1 acceptance test
  tests/test_equity_revisions_src_a1_acceptance.py::test_populated_economic_fact_change_supersedes_without_mutating_prior
  pins the opposite for its unit, currency and basis cases: correction_state == "supersedes" with the prior id.
  One lineage state cannot satisfy both. Which contract wins? The same packet also asks how to treat the two
  GAP-E-ALIAS xfails.
answer: >
  BASIS: the E1 contract wins (option a). In collectors/equity_revisions.py _apply_lineage, directly after the
  existing fiscal-rollover gate (mutation gate 3), add a fourth gate. When unit, currency or basis is non-null on
  both the newest prior row and the current row, and the two differ, the current row stays a new "original" with no
  supersedes_observation_id. A null on either side falls through to the existing value comparison exactly as today,
  so enrichment from null to a value still supersedes. The prior row is never mutated. The three SRC-A1 parametrize
  cases (unit, currency, basis) are amended to assert "noncomparable: original, no supersedes link, prior unmutated".
  Their immutability assertion is kept unchanged, because that is the invariant SRC-A1 exists to prove. The three
  GAP-E-BASIS strict xfails are removed.
  ALIAS: GAP-E-ALIAS e_a #2 has a defective fixture. Its capture time (06-02) is later than its as_of (06-01), so a
  pass would need a backward leak. The fixture is amended to a lawful as_of (at or after capture, preserving the
  test's "resolves on or after" intent), and its strict xfail is removed. GAP-E-ALIAS e_a #1 stays strict-xfail. It
  needs an owner-issued, clocked Data OS identity crosswalk, and none exists. Owner ruling 6029837568 on #8309 keeps
  ticker/security identity Data OS owner-issued and as-of-cutoff. The xfail reason text is updated to name that
  dependency exactly.
rationale: >
  Lineage is a claim about the world. "supersedes" says the new row replaces the prior as the value of the same
  economic fact. A GAAP EPS and an adjusted EPS, a diluted and a basic EPS, or a USD and a EUR figure are different
  facts, not two versions of one fact. Chaining them into one revision lineage lets any consumer that reads
  correction_state (K3E first) compute a revision delta between non-comparable numbers. That would be a fabricated
  signal. Option (a) refuses the false relation at its source, so it fails closed for every consumer, present and
  future. It also mirrors the precedent already on main: the fiscal-rollover gate refuses a supersession when
  period_end differs. Option (b) would keep the false link in the lineage and depend on every consumer
  remembering to check comparability, which fails open. SRC-A1 is this workstream's own contract (#8312), so the
  amendment is a workstream-owner act. It is taken under Chairman delegation
  (DEC:ITP-SEAT-RELEASES-ADMINISTRATIVE-BLOCKS-UNDER-CHAIRMAN-2026-10-06) and is never a Sol ruling.
  financial_influence, k3e_admissible and promotion_eligible stay false.
alternatives:
  - option: "(b) SRC-A1 wins: keep supersedes, refuse at the K3E revision-delta seam instead"
    why_not: >
      It leaves a false "same fact" relation in the durable lineage, and fails open for any consumer that does not
      re-check comparability.
  - option: "Treat any unit/currency/basis difference as noncomparable, including null to value"
    why_not: >
      Enrichment of a previously typed-missing field is the same fact gaining metadata. Refusing it would split
      lineages on vendor backfills. The precedent gate treats a null on either side as fall-through, and this gate
      matches it.
  - option: "ALIAS e_a #1: add an engine-side injected crosswalk parameter so the test passes on a fixture crosswalk"
    why_not: >
      No owner issues such a crosswalk. The test would pass on a contract nobody produces and prove nothing about
      production. Identity issuance belongs to the Data OS identity owner.
evidence:
  - "Orchestrator A, A4.1 census 2026-10-07 (seat scratch orch/A/LEDGER.md): on a scratch copy of main, 130 tests pass and 9 xfail; under --runxfail all 9 fail. A scratch prototype of gate 4 turns the 3 BASIS tests green and turns exactly the 3 SRC-A1 unit/currency/basis cases red."
  - "collectors/equity_revisions.py _apply_lineage on origin/main 42685180: mutation gate 3 (fiscal rollover) is the precedent, and lineage is applied only to newly collected rows."
  - "#8583 (MI seat, head 44d0150d) converts GAP-E-FAMILY-SEAM, CLOCK and both RIGHTS xfails and leaves ALIAS x2 and BASIS x3 strict, per owner ruling 6029837568 on #8309."
affects:
  - "WS:ALPHA-INTELLIGENCE-INTEGRATION"
  - "collectors/equity_revisions.py"
  - "tests/test_equity_revisions_src_a1_acceptance.py"
  - "tests/test_k3e_semantic_seam_qualification.py"
  - "tests/test_k3e_provider_family_qualification.py"
confidence: high
reversibility: easy
decided_by: "seat: fable program-ceo session 2fc05761 (WS:ALPHA-INTELLIGENCE-INTEGRATION owner), under Chairman directive 2026-10-06; census by orchestrator A"
decided_at: 2026-10-07
review_by: 2027-01-07
---

# K3E Package E residual seams: a basis change is not a revision

The seat rules that the E1 contract wins over the SRC-A1 acceptance cases for unit, currency and basis changes. A
change in any of those three, populated on both sides, makes the two values non-comparable. The collector records
the new row as a fresh original, not as a supersession, and the prior row is never mutated. This mirrors the
fiscal-rollover gate that already sits in `_apply_lineage`.

GAP-E-ALIAS e_a #2 is a fixture defect: its as_of precedes its own capture. It is corrected to a lawful as_of and
converted. GAP-E-ALIAS e_a #1 stays strict-xfail until the Data OS identity owner issues a clocked crosswalk. This
seat does not mint one, under the no-new-store law and owner ruling 6029837568.

Lineage applies only to newly collected rows, so historical supersedes links in the committed corpus are not
rewritten. The implementing lane reports how many existing links join rows whose non-null unit, currency or basis
differ. If that count is non-zero, a K3E-side refusal for those historical links is a separate follow-up.

## Correction note (2026-10-07, same seat)

The statements above that GAP-E-ALIAS e_a #1 "stays strict-xfail until the Data OS identity owner issues a clocked
crosswalk", and the rejected alternative's reason "No owner issues such a crosswalk", rest on a false premise. The
Data OS identity owner already publishes a clocked crosswalk: `data/reference/vendor_aliases.parquet`, with an
non-null `ingested_at` knowledge clock (re-stamps only move it later) and a nullable `valid_from`, read via `lib/dataos/identity.VendorAliasTable`.
Orchestrator A's A5 census found it on 2026-10-07. DEC:ITP-K3E-ALIAS-CLOCK-BOUNDED-IDENTITY-2026-10-07 records how
the surface reads it and converts e_a #1.

The BASIS ruling and the e_a #2 fixture correction in this record are unaffected and stand. This note corrects one
premise only and is not a supersession. The answer and alternatives fields above are left as written, so the
record of what was decided at the time stays intact.
