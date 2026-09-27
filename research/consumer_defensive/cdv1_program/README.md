# Consumer Defensive CDV-1 — implementation program ledger

Operation `gmi-consumer-defensive-research-20260923-sol-001`. Research/plan carrier: PR #7792 (`sol/consumer-defensive-research-20260923`, DRAFT/HOLD, documentation-only). Frozen plan: `docs/superpowers/plans/2026-09-23-consumer-defensive-cdv1-implementation.md` at `88970a1a197884cc242f6d117cbf209603eccaf9`, with the design spec and six clarifications at the same pin.

Seat: Fable Meta-CEO (Claude session `251f88c8`, account claude8), picked up 2026-09-24 ~04:55Z under the Chairman's live delegation (PICKUP_ACK = #7792 comment 5807883214). Routing: every build/review lane on the external fabric (`remote_lane_v8` labels `cdv1_*` on m1 / mb / mini2; GLM-5.3 build + review); Opus native children only as read-only auditors; Fable adjudicates, posts and merges.

## Delivery shape

One integrated vertical shipped as one PR per plan task, each branched from fresh `origin/main` and squash-merged on concluded green before its dependents branch:

| Task | Lane label | Branch | State |
|---|---|---|---|
| 1 native PG profile + strict scoped facts | `cdv1_t1_pg_facts` (rounds r1 m1, r2–r3 mini2, r4 mini2, r5 mini2/MiniMax) | `claude/cdv1-t1-pg-profile-facts` | PR #7905 DRAFT — repair round 5; probe suite frozen at 7804e24a, seat head b8bb513e93 |
| 2 source selection + native preparation | `cdv1_t2_source_currentness` | `claude/cdv1-t2-source-currentness` | packet ready (after T1) + CI dependency law + foundation-map Q6 fold |
| 3 deterministic interpretation | `cdv1_t3_interpretation` | `claude/cdv1-t3-economic-interpretation` | packet ready (after T1) + T7 contract binding |
| 4 private publication v2 + readers | `cdv1_t4_private_v2` | `claude/cdv1-t4-private-publication-v2` | packet ready (after T1–T3) + T7 contract binding + Q6 fold |
| 5 normal refresh integration (flag off) | `cdv1_t5_refresh_integration` | `claude/cdv1-t5-refresh-integration` | packet ready (after T4) |
| 6 API current selector + pinned evidence | `cdv1_t6_api_evidence` | `claude/cdv1-t6-api-evidence` | packet ready (after T4) + T7 contract binding + Q6 fold |
| 7 shared dossier display | `cdv1_t7_design_spec` (r1–r3 mb/mini2) | `claude/cdv1-t7-design-spec` | RE-SCOPED to CONTENT + CONTRACT: spec MERGED #7904; UI build waits for the foundation host slot (#7870) |
| 8 qualification + release | `cdv1_t8_census` + seat | `claude/cdv1-t8-release-census` | release-readiness census MERGED #7910; readers first, producer enable last |

New test suites are wired into the gate:code job `earnings-economic-dossier` (`.github/ci/legacy-jobs.yml`, minted by Task 1 per the `prophet-us-b4-prereg-registration` recipe); the legacy earnings suites otherwise live only in `if: false` gate:data jobs.

## Records

- `reviews/OPUS_PLAN_SEAM_AUDIT_2026-09-24.md` — read-only Opus audit of the plan against the code seams; its findings F1–F19 are binding rulings folded into the lane packets (wrong discovery seam, permissive latin-1 decode, per-event `fiscal_scope`, no native fact validator, public rights profile, Task 5 insertion point in `publish_public_wire`, stage tree rejects unknown files, `StrictConditionalWriteStore`, evidence route above the catch-all, real-publisher API fixture).

Gates: G1 exercised by the seat as delegated owner; G2 (real source admission), G3 (v2 closure acceptance), G4 (shared shell mount; STSI #7777 does not touch `templates/sector.html.j2`) remain evidence gates on the release step.

## Wave 1 (2026-09-24) — seat ledger

- **Base ruling (Astra CEO via Chairman, ~07:50Z):** the Semiconductors session owns the shared base (macro #7870 theme-graph / evidence-foundation / rights; `contracts/sector_intelligence/*` on main). CDV-1 rebuilds no shell, evidence or rights vocabulary; T1–T6 extend the incumbent Earnings owner; T7 is a CONTENT + CONTRACT spec that integrates into the foundation host slot later. Record: `DEC:CDV1-FOUNDATION-INTEGRATION`.
- **Merged:** #7880 (ledger + seam audit), #7906 (Agent OS records), #7904 (T7 spec, `design/T7_DOSSIER_DESIGN_SPEC_2026-09-24.md`, adjudicated ACCEPT at 8c117f8b after two Opus rounds — rulings R1–R16 in `reviews/`), #7910 (`release/RELEASE_READINESS_CENSUS_2026-09-24.md`, Q1–Q7), #7917 (`integration/FOUNDATION_INTEGRATION_MAP_2026-09-24.md`, Q1–Q6: `rp_public_primary_v1` static profile conflicts with source-family rights → ONE mapping `rp_public_primary_v1 → sec_edgar` declared in T2, validated fail-closed in T4, gated at read in T6 through one injectable registry-reader seam; `sec_edgar`, `load_registry_snapshot`, `assert_current_emission_allowed`, `admission.py` are NOT on main until #7870 lands, so production PG publication stays refused by design until then).
- **T1 (#7905):** two Opus read-only red-team rounds → seat rulings R1–R16 (`reviews/SEAT_RULING_T1_PR_R1_2026-09-24.md`, `..._R2_...`): scope-derived vocabulary, replay compares value+period+basis, drivers by column header, unit-aware parsing, quarter from scope, fact_id = f(event_id, metric, period, basis), one rights registry, `unit_mismatch` reason, synthetic fixture values only, probe file frozen. The reviewer's 20 probes were committed RED by the seat at 7804e24a and wired into the gate job; a repair lane may not touch that file (single-author gate).
- **Lane incidents:** glm-5.3 fix lanes collapsed into gibberish three times on this task (r1 on m1 after 105 min with two shim `upstream=500`; r4 on mini2 after 35 min with a clean upstream) — each time the seat salvaged the dirty worktree over ssh and pushed it (WIP d5d2dd7e80, fix b8bb513e93). Round 5 runs on MiniMax-M3 with commit-per-group law. ci-pack-8 red on the first T1 head was a missing `pyyaml` in the job's `pip install` (fixed 5dadd935). mini2 refused one admission on load (Spotlight indexing `~/lanes`; operator item: exclude `/Users/mini2/lanes` from Spotlight).
- **CI wiring:** gate:code job `earnings-economic-dossier` (`.github/ci/legacy-jobs.yml`) runs `tests/test_pg_economic_observations.py` + `tests/test_pg_economic_observations_probes.py` in a clean venv with `pip install pytest pyyaml`; every test added to `run:` must also appear in `paths:`.
- **Next:** T1 round 5 → final Opus round bounded to R7–R16 → CI on the exact head → ready → merge → T2 ∥ T3 → T4 → T5 ∥ T6; T7 UI build and T8 release gates wait for #7870.
