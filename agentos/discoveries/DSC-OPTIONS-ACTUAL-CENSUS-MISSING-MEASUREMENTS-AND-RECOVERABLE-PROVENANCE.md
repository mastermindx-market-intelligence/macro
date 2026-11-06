---
key: OPTIONS-ACTUAL-CENSUS-MISSING-MEASUREMENTS-AND-RECOVERABLE-PROVENANCE
claim: >
  At Macro d675bbece0848e8587e4070b576e7585e02b5a19, the hash-verified Flow ML
  ledger contains 74589 events and zero populated measured-microstructure rows,
  including 4375 events dated after the OA-1T implementation merge. An exact
  source-event join recovers existing episode availability/selection provenance
  for 8711 ML rows without reconstructing NBBO. The campaign checkpoint is an
  intact older episode prefix with a 769-row September4 suffix unconsumed, and
  all 54 missing-price grade rows are SLV. These are committed-data findings,
  not a diagnosis of the first runtime failure or a claim of live acceptance.
falsifier: >
  Read the exact ledger/grade/episode Git blobs and SHA-256 hashes recorded in
  research/options_estate/OPTIONS_ACTUAL_CENSUS_AND_RECOVERY_2026-09-10.md and
  recompute schema nonnull counts, exact ID joins, grade reasons and the first
  8872 newline-preserved episode bytes. A conflicting result on those identical
  bytes refutes the respective finding. Newer source/runtime evidence requires
  a dated continuation, not silently changing this snapshot's meaning.
so_what: >
  Stop treating the complete census as a pending research task, the row count
  as measured-model readiness, or a merge as evidence delivery. Under the
  existing source owner, trace one natural qualifying event across installed
  producer, stage, publication, harvester and consumer, and repair only the first
  demonstrated loss. Reuse exact episode provenance through reviewed projections,
  reconcile missing IDs/prefix lag and label coverage, and preserve the legacy
  clock cohort rather than rewriting history or building another collector.
kind: architecture
verified_at: 2026-09-10
verified_by: >
  Sol's read-only actual-data census on the authorized Mini using already-present
  Git objects matched to the current GitHub path/blob metadata. Ledger blob
  e8dc48d53519cf1cae40c3a48f9f06c71e943055; grades blob
  b8798f058459e0b8f892168cc521fc55ab9b872e; episodes blob
  79277635aeb5578a346727e9e2cb34be6d19bcfe. Exact aggregate receipt at
  2026-09-10T21:08:26.668709Z. Auditor SHA-256
  cb9eff21caec93094868e25d347aa45b2657d9ad53662f39cef8d9f8a03b6151;
  current-object audit exit0; 73 pre-existing research tests rerun and passed.
scope:
  - macro
  - terminal
  - options-intelligence
  - options-alpha
  - "data/flow_signals/*"
  - "data/options_signal_episode/*"
  - "data/options_signal_campaign/*"
  - "research/options_estate/*"
confidence: verified
---

Parent: WS:OPTIONS-ALPHA-INTELLIGENCE-RECOVERY. Existing draft carrier: Macro #7027.

## Evidence delta

The earlier durability turn could inspect source and synthetic fixtures but had
not loaded the complete Parquet data. That limitation is now resolved for the
specified committed snapshot. The fullest evidence and limits are in
`research/options_estate/OPTIONS_ACTUAL_CENSUS_AND_RECOVERY_2026-09-10.md`.

The older local worktree's 72880 rows were also read; all remained equal in the
latest 74589-row snapshot after ID/column alignment. The current object was read
from Git's existing object store without fetching or changing the checkout.

The episode artifact contains 9641 unique records. The 8711 joins agree on
normalized event time, root/session, contract and premium/quantity. All joined
availability/selection fields are present; OI vintage is present on7868. There
are930 episode IDs outside ML, grouped as384 August10,7 August20,539 September1.
Missing joins are reconciliation candidates, not permission to alter a frozen
population. The matching campaign source prefix is a valid older receipt, not a
corruption claim.

A separate50969-row legacy clock cohort throughJuly29 agrees with the documented
naive-ET-as-Z defect fixed by Macro #4017, merge
`f8f5a90af90e6d7830cf53e1c222298fd9db966e`. Intraday reuse needs source-bound
interpretation; timezone-aware types alone are insufficient. Daily grades use
session_date, so they are not automatically invalidated by that clock finding.

Grades have67473 ok,7062 not-yet-matured and54 SLV no-price rows. Among completed
underlying grades,440 lack primary SPY-excess values. All option-premium-touch
values remain null. These facts do not constitute exact-option P&L or alpha.

## Exact continuation

The primary next capability is one naturally occurring measured event traced
end-to-end under the current sole-writer source owner. Identify the installed
runtime and the first boundary where fields disappear before commissioning any
repair. Do not rerun the initial census merely as activity. Do not repeat the
already-merged OA-1T source implementation, lower selection floors, overwrite
immutable rows, or relax the all-null feature guard.

Independent research can reconcile the exact provenance join, missing IDs,
valid-prefix suffix, clock cohort and SLV/target gaps. AD-1T2, OA-3, OA-4/5,
current DNR rules and existing Issue Desk/source/campaign owners retain all their
requirements. No new collector, ledger, scheduler, signal super-score or control
plane is authorized by this record.

## Closeout boundaries

No runtime service, source data, checkpoint, model or trading gate was changed.
The Mini analysis processes exited0. A separate unresponsive MacStudio REPL
produced no accepted result and its exit request timed out; shutdown remains
unconfirmed. The raw research copy is restricted outside the repository and is
not included in this public research carrier.

Keep draft pending normal record validation/review. Repository-wide Agent OS
validation, hosted CI success, production proof and final program acceptance
are not claimed. A newer live measured receipt can change the current action,
but cannot rewrite what these pinned committed bytes contained.
