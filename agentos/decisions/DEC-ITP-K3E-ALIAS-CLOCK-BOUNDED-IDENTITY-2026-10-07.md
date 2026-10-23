---
key: ITP-K3E-ALIAS-CLOCK-BOUNDED-IDENTITY-2026-10-07
question: >
  GAP-E-ALIAS e_a #1 (tests/test_k3e_provider_family_qualification.py::test_e_a_alias_p_unresolved_before_alias_known_date)
  requires that the K3E expectation surface does not resolve a ticker to a security before that identity was knowable.
  DEC:ITP-K3E-BASIS-CHANGE-IS-NONCOMPARABLE-2026-10-07 kept it strict-xfail on the premise that no owner-issued, clocked
  Data OS identity crosswalk exists. Orchestrator A's census (A5, 2026-10-07) found that one does exist. Which crosswalk
  does the surface read, in which vendor space, how are undated rows clocked, and is the resulting unresolved share
  acceptable?
answer: >
  The surface reads the Data OS owner's existing crosswalk data/reference/vendor_aliases.parquet
  (lib/dataos/identity.VendorAliasTable; registry reference.vendor_aliases; producer scripts/build_security_master.py;
  master in config/identity_seams.yml). Nothing new is minted. (a) Vendor space: "yahoo", because every K3E attempt's
  provider is yfinance. The provider-to-space map is explicit ({"yfinance": "yahoo"}), and an unmapped provider is
  identity-unresolved. (b) Clock: a row is usable for a capture only if its ingested_at is at or before both the
  capture's own clock and the query cutoff. Its validity window, when dated, must also cover the capture date. An
  undated row (valid_from null) is therefore usable from its ingested_at forward, never before. ingested_at is the
  table's non-null knowledge clock. It is not strictly append-only: a rebuild can re-stamp a row later (orchestrator
  B's B4 census found 3 yahoo rows, FBRX, LEG and TWO, re-stamped on 2026-09-03/04). A re-stamp only moves the clock
  later, so the rule stays conservative: it never makes a row usable before it was knowable, and it is not a
  fabricated valid_from. (c) A row is identity-resolved only if the security_id resolved at its capture equals the query ticker's
  security_id resolved at the cutoff. Every other relevant row stays counted in the denominators but becomes
  snapshot-ineligible, with the new disclosed reason SECURITY_IDENTITY_UNRESOLVED_AT_CUTOFF. (d) The roughly 48.6
  percent of current attempts that resolve to no clocked identity (4,567 of 9,390, all captured before the table's
  first ingestion on 2026-08-13 or on uncovered symbols) are accepted as disclosed UNRESOLVED on the on-demand CLI.
  The CLI reads the crosswalk blob at the same frozen source revision as its observations, and it pins the
  crosswalk's git blob id and sha256 in provenance. GAP-E-ALIAS e_a #1 converts from strict xfail to a passing test.
rationale: >
  Owner ruling 6029837568 on #8309 keeps ticker/security identity Data OS owner-issued and as-of-cutoff. The surface
  previously matched on ticker_compat equality alone, so a symbol later reassigned or aliased could attach another
  security's history to the queried ticker. That is a backward identity leak. Reading the owner's own crosswalk under
  its own knowledge clock closes the leak without minting a store or a vocabulary. Fail-closed is the only lawful
  direction. A capture whose identity was not yet knowable is withheld and counted, never repaired by a later
  backfill. The EVAL-1 preregistration states the same law for issuer_ref ("never repaired by a later identity
  backfill"). The surface is display tier, and its only caller is scripts/query_k3e_expectation_surface.py, so no
  site page and no ranking moves. financial_influence, k3e_admissible and promotion_eligible stay false. This is a
  workstream-owner act under Chairman delegation (DEC:ITP-SEAT-RELEASES-ADMINISTRATIVE-BLOCKS-UNDER-CHAIRMAN-2026-10-06),
  never a Sol ruling.
alternatives:
  - option: "Vendor space 'membership' (resolves 4,886 rather than 4,823 attempts)"
    why_not: >
      K3E captures come from yfinance, so its symbols live in the yahoo space. Both spaces agree on security_id for
      all 1,217 shared symbols, so the 63-attempt gain would come from borrowing another vendor's symbol namespace, not
      from better identity.
  - option: "Dated rows only (strict valid_from)"
    why_not: >
      Only 3 yahoo rows carry valid_from, so 9,381 of 9,390 attempts would be unresolved and the surface would be off
      in practice. A null valid_from is unknown validity, not invalidity, and the knowledge clock already prevents any
      backward use.
  - option: "Narrow variant: withhold only symbols the crosswalk knows, on dates it does not cover"
    why_not: >
      An unknown symbol would still resolve by bare ticker equality, which is the backward leak ruling 6029837568
      forbids.
  - option: "Keep e_a #1 strict-xfail and wait for a dated crosswalk"
    why_not: >
      Its premise ("none exists") is false. Widening coverage or dating rows is the identity owner's forward work, and
      waiting changes no fact the surface can lawfully use today.
  - option: "Mint a K3E-local alias table"
    why_not: >
      That is a new store and a parallel identity vocabulary, which the no-new-store law and ruling 6029837568 both
      forbid.
evidence:
  - "Orchestrator A, A5 PHASE_RETURN 2026-10-07 (seat scratch orch/A): crosswalk located at data/reference/vendor_aliases.parquet; schema valid_from date nullable inclusive, ingested_at datetime64 non-null (not strictly append-only: B4 found 3 yahoo rows re-stamped later, which only tightens the clock); config/dataset_registry.yml reference.vendor_aliases; config/identity_seams.yml lists it as master."
  - "Seat re-run of A5 orch/A/a5/strict.py, 2026-10-07 ~08:20Z: 9,390 attempts over 1,510 tickers. yahoo: 1,219 rows (3 dated); knowledge-clocked including undated resolves 4,823 and leaves 4,567 unresolved; dated-only resolves 9 and leaves 9,381. membership: 1,218 rows (2 dated); 4,886 resolved / 4,504 unresolved; dated-only 9 / 9,381."
  - "Seat check: every attempt has provider == yfinance (9,390 of 9,390); yahoo and membership agree on security_id for all 1,217 shared symbols; yahoo ingested_at spans 2026-08-13T13:08:12 to 2026-09-21T03:19:29 (6 distinct values)."
  - "git grep on origin/main 6077ca56: inspect_expectation_surface is called only by scripts/query_k3e_expectation_surface.py; the EVAL-1 preregistration (eval1_preregistration.v1.json effective_n_rule) already makes a row without a cutoff-known issuer_ref ineligible and forbids identity backfill repair."
affects:
  - "WS:ALPHA-INTELLIGENCE-INTEGRATION"
  - "engine/k3e_expectation_surface.py"
  - "scripts/query_k3e_expectation_surface.py"
  - "tests/test_k3e_provider_family_qualification.py"
  - "tests/test_k3e_expectation_surface.py"
confidence: high
reversibility: easy
decided_by: "seat: fable program-ceo session 2fc05761 (WS:ALPHA-INTELLIGENCE-INTEGRATION owner), under Chairman directive 2026-10-06; census by orchestrator A (A5)"
decided_at: 2026-10-07
review_by: 2027-01-07
---

# K3E ticker identity is read from the Data OS crosswalk, clock-bounded, fail-closed

The K3E expectation surface stops trusting bare ticker equality. A captured row counts as the queried security only
when the Data OS owner's existing crosswalk (`data/reference/vendor_aliases.parquet`, yahoo space) knew that identity
at the row's capture and at the query cutoff. An undated crosswalk row is usable from its `ingested_at` forward, never
before. Rows that fail stay counted in every denominator, become snapshot-ineligible, and are disclosed as
`SECURITY_IDENTITY_UNRESOLVED_AT_CUTOFF`.

About 48.6 percent of today's attempts resolve to no clocked identity, because most were captured before the
crosswalk's first ingestion on 2026-08-13. That share is printed, not hidden. Widening coverage or dating rows is the
identity owner's forward work; this record authorizes no backfill.

This record corrects the premise of DEC:ITP-K3E-BASIS-CHANGE-IS-NONCOMPARABLE-2026-10-07 that no clocked crosswalk
exists. Its BASIS ruling and its e_a #2 fixture correction stand unchanged.

Receipts produced by the surface before this change, such as the R4 dry-run positive-control digest
280b96ba8a5885482647107c10a3cb803047679c575969ccd1c55475b6dea7ef, reproduce at their own code revision, not at the
new head.
