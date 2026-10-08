---
key: THEME-GRAPH-RENAME-REMINT-MERGES-INTO-INCUMBENT-NODE
question: >-
  The 2026-09-04 nightly minted company node co:us:VMRK, with an open MEMBER_OF edge to
  us_sector_realestate back-dated to 2023-05-09, after data/baskets/membership.json was
  re-keyed in place EQR->VMRK (#6643). co:us:EQR's identical membership edge stayed open,
  so one issuer is counted twice in one basket. The D2A identity-resolution tests pin
  2806 physical company nodes and VMRK's absence from the sidecar, so data-health's D2A
  step is red. Which node is canonical, how is the duplicate corrected in an append-only
  store, and how are the frozen D2A pins reconciled?
answer: >-
  co:us:EQR stays canonical. A company node id never re-points, and a rename is not a
  ticker reuse; the D2B1-R1 security-master ruling already continues SEC:US-XNYS-EQR and
  marks SEC:US-XNYS-VMRK a superseded duplicate mint. co:us:VMRK is corrected through the
  incumbent D2B3 writer (scripts/correct_gmi_identity_lineage.py) with a new curated
  DUPLICATE_MINT shape. It appends one lifecycle row (status=merged,
  merged_into=co:us:EQR, reason=duplicate_mint, retire_date=run date, never back-dated),
  driven by an explicit curated row in config/theme_graph_duplicate_mints.yml. It also
  appends one newer-belief annulment row for each open MEMBER_OF edge of the duplicate.
  The materializer's existing retired-like post-pass keeps the duplicate suppressed on
  every later nightly. The store is append-only and D2B3 never writes nodes.parquet, so
  the physical company count becomes 2807 permanently. The D2A pins are re-pinned with
  the delta enumerated: 2806 + {co:us:VMRK}, where every enumerated node is
  lifecycle-merged into a canonical node. R1 §6.1 assertion 3 becomes the post-merge
  invariant: VMRK is merged into co:us:EQR, never resolves to SEC:US-XNYS-VMRK and has no
  open MEMBER_OF, and co:us:EQR holds exactly one open membership of
  us_sector_realestate. The correction's curated source refs are registered
  mastermind_curated in the rights registry. A rename-continuation mechanism (symbol to
  incumbent node) is deliberately NOT built here.
rationale: >-
  The identity law in config/theme_graph_identity_breaks.yml fixes the direction. A
  company node id never re-points, and only a REUSED ticker retires a node for a new
  epoch. EQR->VMRK is a rename of one issuer (same CIK), so the incumbent node continues
  and the later mint is the duplicate, exactly as D2B1-R1 already ruled for the security
  master. The store is append-only and bitemporal by design, so the only lawful
  correction is additive: a lifecycle overlay row plus newer-belief edge annulments.
  status=merged already exists in the lifecycle schema and in RETIRED_LIKE_STATUSES. The
  same mechanism has kept the IBIT and GOLD corrections stable across about 45 nightlies
  through the materializer's retired-like post-pass. An additive correction cannot
  reduce the physical node count, so the frozen D2A pins must move. Test 1's own
  docstring prescribes re-pinning over silent trust, and enumerating the delta keeps the
  pin a drift detector for every other node. A curated row is required instead of a data
  rule because ratification is a curated act, and a data rule would also hit the
  accepted FI/FISV pair.
alternatives:
  - option: Re-pin only, accepting two nodes for one company as the D2A FI/FISV precedent did
    why_not: >-
      FI/FISV was accepted because its two nodes held disjoint containers. Here both
      nodes hold an open MEMBER_OF edge to the same basket from the same date, so the
      basket double-counts one issuer. That is a data defect, not an identity nuance.
  - option: Make co:us:VMRK canonical and merge co:us:EQR into it, following the re-keyed basket
    why_not: >-
      It contradicts the D2B1-R1 frozen contract (SEC:US-XNYS-EQR continues and
      SEC:US-XNYS-VMRK is a superseded duplicate mint) and the law that a node id never
      re-points. It would also orphan EQR's other edges and force a re-pin of R1
      assertions 1, 2 and 4.
  - option: Retire the duplicate and keep the 2806 pins unchanged
    why_not: >-
      This is impossible in an append-only store. The physical co:us:VMRK row is never
      removed and D2B3 never writes nodes.parquet, so the count stays 2807 and the
      latest sidecar keeps a VMRK row.
  - option: Drive the merge from a data rule (two company nodes resolving to one security id)
    why_not: >-
      It would also merge the accepted D2A FI/FISV pair, and ratification is a curated
      act under the identity law.
  - option: Add the VMRK row to config/theme_graph_identity_breaks.yml
    why_not: >-
      That file also feeds identity_epoch, so a VMRK row there would mint co:us:VMRK#2
      instead of merging anything.
  - option: Build a rename-continuation alias (VMRK -> co:us:EQR) inside company_node_id now
    why_not: >-
      It changes company_node_id semantics fleet-wide under a same-day pre-nightly
      deadline. It is deferred as a named follow-up. Until it lands, a future `removed`
      date on the VMRK basket row would be suppressed together with the duplicate and
      leave the EQR edge stale-open.
evidence:
  - "git show origin/main:data/baskets/membership.json: us_sector_realestate row {ticker: VMRK, added: 2023-05-09, removed: null, rationale 'formerly EQR ... NYSE EQR->VMRK eff. 2026-08-18, SEC 8-K accession 0001140361-26-033377'}; EQR absent; re-key landed in #6643 (7f4b314fbf70)"
  - "engine/theme_graph/identity.py:129 company_node_id: co:<market>:<SYMBOL> plus an epoch from identity breaks only; no rename/alias path"
  - "engine/theme_graph/materialize.py:1246 _suppress_conflicts_and_retired drops retired-like re-mints and their src edges from the computed view (typed retired_remint refusal)"
  - "engine/theme_graph/store.py:255 RETIRED_LIKE_STATUSES = {retired, merged}; contracts/theme_graph/node_lifecycle.v1.schema.json status enum includes merged; merged_into is string|null"
  - "tests/test_theme_graph_identity_resolution.py:99 pins 2806 physical company nodes ('needs re-pinning, not silent trust'); :787 R1 §6.1 assertion 3 asserts co:us:VMRK not in the latest sidecar"
  - "data/theme_graph/edges.parquet on main: co:us:VMRK MEMBER_OF us_sector_realestate valid_from 2023-05-09 open (belief 2026-09-04, observed); co:us:EQR same basket valid_from 2023-05-09 open (belief 2026-08-11, reconstruction)"
  - "identity_resolution sidecar latest (2026-10-06T08:07:42Z): co:us:VMRK and co:us:EQR both RESOLVED -> SEC:US-XNYS-EQR"
  - "data-health run 37407802317 red on the D2A step"
affects:
  - WS:GMI-THEME-GRAPH
  - WS:PROPHET-US-V4-RECOVERY
  - scripts/correct_gmi_identity_lineage.py
  - config/theme_graph_duplicate_mints.yml
  - contracts/theme_graph/node_lifecycle.v1.schema.json
  - scripts/check_theme_graph_contracts.py
  - engine/theme_graph/rights.py
  - tests/test_theme_graph_identity_resolution.py
  - data/theme_graph/node_lifecycle.parquet
  - data/theme_graph/edges.parquet
  - data/theme_graph/evidence.parquet
confidence: high
reversibility: costly
decided_by: GMI Theme Graph Meta-CEO seat 6f14c2da (Chairman-delegated program authority, 2026-10-06)
decided_at: 2026-10-06
---

# A renamed ticker's re-mint merges into the incumbent node

This is an append-only DUPLICATE_MINT merge plus an enumerated re-pin of the D2A pins.
The follow-up that remains open is a rename-continuation mechanism, so that a future
departure of the renamed symbol closes the incumbent node's membership. It is named in
the WS-GMI-THEME-GRAPH handoff danger_areas.
