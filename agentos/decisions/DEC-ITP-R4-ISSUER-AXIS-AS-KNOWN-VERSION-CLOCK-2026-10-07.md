---
key: ITP-R4-ISSUER-AXIS-AS-KNOWN-VERSION-CLOCK-2026-10-07
question: >
  The EVAL-1 preregistration (K3E-EVAL-1-V1) makes episode identity issuer + metric + horizon/fiscal period +
  episode-start session. It counts a row only when its issuer_ref was known at the cutoff, and it forbids repair by a
  later identity backfill. K3E observations carry issuer_ref null on 517,384 of 517,384 rows. The security-to-issuer
  mapping lives in the Data OS owner's data/reference/security_master.parquet, which has no knowledge-clock column for
  the issuer axis. Which clock tells R4 and EVAL-1 that a security-to-issuer mapping was known at a cutoff?
answer: >
  The clock is the owner's own publication history. For a cutoff C, the "version known at C" is the newest
  data/reference/security_master.parquet blob on origin/main whose committer time is at or before C minus 24 hours.
  The 24-hour guard covers the gap between a local commit and its push. A security resolves to an issuer at C only if,
  in that one version, all of the following hold: the security is present and not superseded; issuer_state is
  RESOLVED; issuer_id is non-null; country is US. Every field is read from that same version. A later version never
  repairs an earlier cutoff. The clock is labelled REPO_HISTORY_AVAILABILITY in every receipt that uses it. A row whose
  security does not resolve this way stays counted in the denominators and is excluded from issuer episodes with a
  disclosed reason (MAPPING_NOT_PUBLISHED_BY_CUTOFF, SECURITY_NOT_IN_MASTER, SECURITY_SUPERSEDED, ISSUER_STATE_<state>
  or NON_US_SEPARATE_SUBGROUP). The security side of the join stays under
  DEC:ITP-K3E-ALIAS-CLOCK-BOUNDED-IDENTITY-2026-10-07. Nothing is written back to the owner's table.
rationale: >
  The preregistration's point-in-time law says that corrections use the version known at the cutoff. origin/main is
  the owner's publication channel: scripts/build_security_master.py writes the table and the nightly commits it. A
  committed version is therefore the most direct owner-native evidence of what was knowable and when. The history is
  conservative in both directions that matter. The clone's shallow horizon (first visible version 2026-08-23T22:55Z)
  can only make a mapping look newer than it was. A re-stamp or rebuild can only make it later. Neither can make a
  mapping usable before it was published. Orchestrator B's B4 census found 29 versions from 2026-08-23T22:55Z to
  2026-10-05T04:26Z. 1,207 of 1,212 issuer mappings are present in the first visible version; the rest appear on
  08-25 (1), 09-03 (3) and 09-21 (1). No security's issuer_id ever changed. Under this clock, 780 clock-resolved yahoo
  tickers map to 778 resolved US issuers, and the result changes no decision that the alternatives below would change.
  The ruling mints no store, no column and no vocabulary. financial_influence, k3e_admissible and promotion_eligible
  stay false. This is a workstream-owner act under Chairman delegation
  (DEC:ITP-SEAT-RELEASES-ADMINISTRATIVE-BLOCKS-UNDER-CHAIRMAN-2026-10-06), never a Sol ruling.
alternatives:
  - option: "Column clock only (no clock column means no issuer is known)"
    why_not: >
      The owner never published an issuer-axis clock column. Treating that as "never known" would turn a schema
      absence into a false claim about knowledge, and it would leave 0 issuer episodes forever, although the mapping
      was demonstrably published before every cutoff in the corpus.
  - option: "issuer_evidence_snapshot as the clock"
    why_not: >
      It dates the evidence the owner used, not the moment the owner published the mapping. A mapping built later from
      older evidence would become usable before it existed. That is a backward leak.
  - option: "Current version with an earliest-appearance clock (B4's V2 shape)"
    why_not: >
      It reads the state fields (issuer_state, country, security_state) from the newest version and only the time from
      history. That is equivalent today, because no issuer_id changed, but it violates "corrections use the version
      known at the cutoff" the first time a field changes. Reading every field from the one known version costs nothing
      extra.
  - option: "Ask the Data OS owner to add an issuer knowledge-clock column first"
    why_not: >
      That is the owner's forward work and is not blocked by this ruling. Waiting would change no fact about the
      already-published history, and that history already answers the question conservatively.
  - option: "Mint a K3E-local issuer crosswalk"
    why_not: "A new store and a parallel identity vocabulary, which the no-new-store law and owner ruling 6029837568 forbid."
evidence:
  - "git ls-tree origin/main -- data/reference/ (2026-10-07): security_master.parquet blob 362a32522f92, vendor_aliases.parquet blob 1197a56fd610."
  - "Orchestrator B, B4 PHASE_RETURN 2026-10-07 08:44Z (seat scratch orch/B/b4/q/q23a.py sha256 38be1871..., q23_out.json sha256 8a2ad5bb...), pinned to origin/main e208a2546b8b: issuer_ref null on 517,384/517,384 rows; no issuer-axis clock column; 29 security_master versions 2026-08-23T22:55Z to 2026-10-05T04:26Z; 1,207/1,212 mappings in the first visible version; issuer_id never changed; 268,016 rows / 780 tickers / 778 RESOLVED US issuers after the clocked yahoo alias join."
  - "EVALUATION_PREREG.md and eval1_preregistration.v1.json on origin/main: point-in-time inputs require owner-native availability and system clock <= cutoff, corrections use the version known at the cutoff, and a row without a cutoff-known issuer_ref is ineligible and never repaired by a later identity backfill."
affects:
  - "WS:ALPHA-INTELLIGENCE-INTEGRATION"
  - "engine/k3e_eval1_forward.py"
  - "research/alpha_intelligence/expectation_market_dynamics/R4_DRYRUN_RECEIPT_V2_2026-10-07.*"
confidence: high
reversibility: easy
decided_by: "seat: Information->Price program Meta-CEO session 2fc05761 (WS:ALPHA-INTELLIGENCE-INTEGRATION owner), under Chairman directive 2026-10-06; census by orchestrator B (B4)"
decided_at: 2026-10-07
review_by: 2027-01-07
---

# The issuer axis is clocked by the owner's published version history

K3E observations carry no issuer. R4 and EVAL-1 get one only through the Data OS owner's
`data/reference/security_master.parquet`, read as it stood on origin/main at least 24 hours before the cutoff. Every
field comes from that one version. A later version never repairs an earlier cutoff, and nothing is written back.

The table has no issuer knowledge-clock column, so the clock is its publication history, labelled
`REPO_HISTORY_AVAILABILITY`. The shallow clone and later re-stamps can only make a mapping look newer, never older, so
the rule fails toward exclusion.

Rows that do not resolve stay in every denominator and are disclosed by reason. Adding a real clock column is the
identity owner's forward work and is not required by this record.
