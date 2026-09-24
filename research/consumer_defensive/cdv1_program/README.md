# Consumer Defensive CDV-1 — implementation program ledger

Operation `gmi-consumer-defensive-research-20260923-sol-001`. Research/plan carrier: PR #7792 (`sol/consumer-defensive-research-20260923`, DRAFT/HOLD, documentation-only). Frozen plan: `docs/superpowers/plans/2026-09-23-consumer-defensive-cdv1-implementation.md` at `88970a1a197884cc242f6d117cbf209603eccaf9`, with the design spec and six clarifications at the same pin.

Seat: Fable Meta-CEO (Claude session `251f88c8`, account claude8), picked up 2026-09-24 ~04:55Z under the Chairman's live delegation (PICKUP_ACK = #7792 comment 5807883214). Routing: every build/review lane on the external fabric (`remote_lane_v8` labels `cdv1_*` on m1 / mb / mini2; GLM-5.3 build + review); Opus native children only as read-only auditors; Fable adjudicates, posts and merges.

## Delivery shape

One integrated vertical shipped as one PR per plan task, each branched from fresh `origin/main` and squash-merged on concluded green before its dependents branch:

| Task | Lane label | Branch | State |
|---|---|---|---|
| 1 native PG profile + strict scoped facts | `cdv1_t1_pg_facts` | `claude/cdv1-t1-pg-profile-facts` | admitted m1 2026-09-24 05:08Z |
| 2 source selection + native preparation | `cdv1_t2_source_currentness` | `claude/cdv1-t2-source-currentness` | packet ready (after T1) |
| 3 deterministic interpretation | `cdv1_t3_interpretation` | `claude/cdv1-t3-economic-interpretation` | packet ready (after T1) |
| 4 private publication v2 + readers | `cdv1_t4_private_v2` | `claude/cdv1-t4-private-publication-v2` | packet ready (after T1–T3) |
| 5 normal refresh integration (flag off) | `cdv1_t5_refresh_integration` | `claude/cdv1-t5-refresh-integration` | packet ready (after T4) |
| 6 API current selector + pinned evidence | `cdv1_t6_api_evidence` | `claude/cdv1-t6-api-evidence` | packet ready (after T4) |
| 7 shared dossier display | `cdv1_t7_dossier_ui` | — | after T3 + T6 |
| 8 qualification + release | seat | — | readers first, producer enable last |

New test suites are wired into the gate:code job `earnings-economic-dossier` (`.github/ci/legacy-jobs.yml`, minted by Task 1 per the `prophet-us-b4-prereg-registration` recipe); the legacy earnings suites otherwise live only in `if: false` gate:data jobs.

## Records

- `reviews/OPUS_PLAN_SEAM_AUDIT_2026-09-24.md` — read-only Opus audit of the plan against the code seams; its findings F1–F19 are binding rulings folded into the lane packets (wrong discovery seam, permissive latin-1 decode, per-event `fiscal_scope`, no native fact validator, public rights profile, Task 5 insertion point in `publish_public_wire`, stage tree rejects unknown files, `StrictConditionalWriteStore`, evidence route above the catch-all, real-publisher API fixture).

Gates: G1 exercised by the seat as delegated owner; G2 (real source admission), G3 (v2 closure acceptance), G4 (shared shell mount; STSI #7777 does not touch `templates/sector.html.j2`) remain evidence gates on the release step.
