# Consumer Defensive CDV-1 — implementation program ledger

Operation `gmi-consumer-defensive-research-20260923-sol-001`. Research/plan carrier: PR #7792 (`sol/consumer-defensive-research-20260923`, DRAFT/HOLD, documentation-only). Frozen plan: `docs/superpowers/plans/2026-09-23-consumer-defensive-cdv1-implementation.md` at `88970a1a197884cc242f6d117cbf209603eccaf9`, with the design spec and six clarifications at the same pin.

Seat: Fable Meta-CEO (Claude session `251f88c8`, account claude8), picked up 2026-09-24 ~04:55Z under the Chairman's live delegation (PICKUP_ACK = #7792 comment 5807883214). Routing: every build/review lane on the external fabric (`remote_lane_v8` labels `cdv1_*` on m1 / mb / mini2; GLM-5.3 build + review); Opus native children only as read-only auditors; Fable adjudicates, posts and merges.

## Delivery shape

One integrated vertical shipped as one PR per plan task, each branched from fresh `origin/main` and squash-merged on concluded green before its dependents branch:

| Task | Lane label | Branch | State |
|---|---|---|---|
| 1 native PG profile + strict scoped facts | `cdv1_t1_pg_facts` (rounds r1 m1, r2–r3 mini2, r4 mini2, r5 mini2/MiniMax; envelope rounds 2026-09-25 → 09-29) | `claude/cdv1-t1-pg-profile-facts` | **MERGED** #7905 on 2026-09-30 01:42:52Z: squash `cdce3023` of the exact head `1c3e2215`, released by Sol 5902318060 after the R11 ACCEPT |
| 2 source selection + native preparation | `cdv1_t2_source_currentness_r3` (mb), then r4 (mb); rounds 5–6 seat commits | `claude/cdv1-t2-source-currentness` | **MERGED** #8234 on 2026-09-30 16:22:30Z: squash `b1b2ea3b` of the exact head `5f33a5a2`, after the round-6 review's ACCEPT |
| 3 deterministic interpretation | `cdv1_t3_interpretation_r4`, then r5 (mini2); round 6 seat commits | `claude/cdv1-t3-economic-interpretation` | **MERGED** #8232 on 2026-09-30 12:20:22Z: squash `ddf03116` of the exact head `47441f3b`, after the fourth review's ACCEPT |
| 4 private publication v2 + readers | `cdv1_t4_private_publication_r2a`, then `_r2b` (mini2) | `claude/cdv1-t4-private-publication-v2` | PR #8245 (DRAFT). Round A (`packets/CDV1_T4_R2A_PACKET_2026-09-30.md`) seat-verified at `12da187d`; round B (`packets/CDV1_T4_R2B_PACKET_2026-09-30.md`) dispatched 2026-09-30 19:29Z on the same PR |
| 5 normal refresh integration (flag off) | `cdv1_t5_refresh_integration` | `claude/cdv1-t5-refresh-integration` | packet written 2026-09-30 (rulings R5.1–R5.12); dispatched once T4 merges |
| 6 API current selector + pinned evidence | `cdv1_t6_api_evidence` | `claude/cdv1-t6-api-evidence` | packet ready (after T4) + T7 contract binding + Q6 fold |
| 7 shared dossier display | `cdv1_t7_design_spec` (r1–r3 mb/mini2) | `claude/cdv1-t7-design-spec` | RE-SCOPED to CONTENT + CONTRACT: spec MERGED #7904; UI build waits for the foundation host slot (#7870) |
| 8 qualification + release | `cdv1_t8_census` + seat | `claude/cdv1-t8-release-census` | release-readiness census MERGED #7910; readers first, producer enable last |

New test suites are wired into the gate:code job `earnings-economic-dossier` (`.github/ci/legacy-jobs.yml`, minted by Task 1 per the `prophet-us-b4-prereg-registration` recipe); the legacy earnings suites otherwise live only in `if: false` gate:data jobs. The exception is Task 2's suite. Its import closure reaches `requests` through `scripts/refresh_event_workspaces.py`, so it runs in its own exclusive job `earnings-economic-source-selection` rather than widening the dossier job (T2 R5, `reviews/SEAT_RULING_T2_T3_R3_2026-09-30.md`).

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

## Wave 2 (2026-09-25 → 09-30) — seat ledger

- **Seat model:** from 2026-09-29 the seat runs Opus 5.5 under the fable-mode doctrine. Routing is unchanged: labor runs on the external fabric, and Opus native children run only as read-only auditors.
- **T1 first-release envelope.** On 09-25, T1 gained the family F1-Q envelope (`engine/company_intelligence/pg_envelope.py`, rulings R116–R121 in `reviews/SEAT_RULING_T1_ENVELOPE_2026-09-25.md`). Rounds 1–10 followed, 09-25 → 09-29 (rulings R122–R197). Each round has three parts:
  - an independent read-only Opus audit, `reviews/OPUS_T1_ENVELOPE_AUDIT_R<n>_*.md`;
  - a seat ruling, `reviews/SEAT_RULING_T1_ENVELOPE_R<n>_*.md`;
  - a frozen single-author probe suite, `tests/test_pg_envelope_f1_probes_r<n>.py`.
- **Bounded design correction.** One integrity class — a value the validator's entry admits raises instead of being refused — survived two rulings meant to close it (R189, R193). Under the operating brief of 09-29, round 10 stopped adding literal cases:
  - R195 admits a number only in the form Python builds, and it decides every type by identity.
  - R196 makes the public entry's contract total. A built-in type or range error anywhere in the body leaves the entry as the typed refusal.
- **Round 11.** Two independent Opus groups audited exact head `1c3e2215` and both returned ACCEPT (`reviews/OPUS_T1_ENVELOPE_AUDIT_R11_A_2026-09-30.md`, `..._R11_B_...`). The dossier command gave 2313 passed / 176 skipped / 0 failed, both on the candidate and on its current-base composition.
- **Real release.** `release/T1_REAL_RELEASE_DEMONSTRATION_2026-09-29.md` covers P&G's FY25Q4–FY26Q4 exhibits and a Colgate near-neighbour. They run from the exact bytes EDGAR serves, through `bind_release_document` → `build_event_workspace` → `validate_selected_facts`. Source, value, period and refusal are as expected, with 0 failures on CPython 3.12.13 and 3.14.7.
- **Release and merge.** Sol ruling 5902318060 (01:33:57Z) accepted R11 and released the HOLD for exact head `1c3e2215` only. The seat then ran one final reconciliation in the same invocation as the merge, checking:
  - the head, the base and mergeability;
  - that the carrier had not moved;
  - `git merge-tree`;
  - that no path overlapped main's movement since Sol's composition proof.

  It then squash-merged with `--match-head-commit`, giving `cdce3023` at 01:42:52Z; the receipt is #7905 comment 5902450708. The T1 child is ACCEPTED / STOP. What merged is the T1 source seam only: not the dossier, not publication, and not a served experience.
- **Carried notes:**
  - n-B1: `fiscal_period` is typed text, not a date.
  - n-B2: the validator never reads the release entry's metadata.

  Both became obligations in the r3 packets. T2 produces that metadata from the actual acquisition. T3 takes the fiscal pair from `fiscal_scope` plus the facts' `period` fields, and never uses entry metadata.
- **Runtime note (Sol 5902318060).** In teardown, the frozen R9 100,000-level nested-deque probe can SIGSEGV under CPython 3.12 with an 8 MiB stack, after the validator has already refused correctly. It is not a product crash, and the frozen witness is not mutated to hide it. Lanes run dossier commands under `ulimit -s hard`.
- **T2 ∥ T3 (r3).** Dispatched 2026-09-30 on disjoint file grants: `reviews/SEAT_RULING_T2_T3_R3_2026-09-30.md` (T2 R5, T3 R2, and the fourteen-key correction). The only shared file is `.github/ci/legacy-jobs.yml`, edited at non-adjacent anchors.
- **r3 erratum.** The r3 packets were rewritten rather than derived from r2, and the rewrite dropped binding sections. `reviews/SEAT_RULING_T2_T3_R3_ERRATUM_2026-09-30.md` restores them:
  - T2 R6: the `PROFILE_SOURCE_FAMILY` constant (FOUNDATION MAP Q6);
  - T3 R3: the §6.2 payload paths (R13 on #7904);
  - a common anti-collapse and exact-venv ruling.

  They bind at acceptance: seat verification, each PR's review bar and the next fix round. Every later re-based packet is diffed paragraph by paragraph against its predecessor before dispatch.
- **T3 review → r4.** PR #8232 at `f2714400` passed every mechanical check in the seat harness. The independent Opus review still returned REJECT, with ten blocking semantic findings (`reviews/OPUS_T3_PR_REVIEW_R1_2026-09-30.md`). `reviews/SEAT_RULING_T3_R4_2026-09-30.md` upholds all ten and dispatches one fix round on the same PR. Rulings R4–R13 replace the hand-listed special cases with general rules. This records PR also amends spec §5.7: owner rows for `demand` and `earnings`, and one rendered sentence per owner.
- **Next:**
  1. For each T2/T3 PR, the seat verifies:
     - RED, then GREEN;
     - T2's pure-addition proof;
     - the T1 freeze;
     - the curated-closure test;
     - the dossier command under `ulimit -s hard`.

     Each PR then gets an independent read-only Opus review, then concluded CI, then a merge with `--match-head-commit`.
  2. Before the second of the two merges, check `git merge-tree` on the two heads.
  3. Then T4, then T5 ∥ T6. The T7 UI and the T8 release still wait for the foundation host edge (#7870).

## Wave 3 (2026-09-30) — seat ledger

- **T3 rounds 5–6 → MERGED.** The round-5 lane returned at `f4a167ff`, and the seat added one commit under R5a (`reviews/SEAT_RULING_T3_R5A_2026-09-30.md`). The third Opus review rejected head `38e4e71b` on seven blocking findings, F1–F7 (`reviews/OPUS_T3_PR_REVIEW_R3_2026-09-30.md`). Round 6 answered them with rulings R6.1–R6.10, one boundary for every value, in two seat commits, `be277281` and `47441f3b` (`reviews/SEAT_RULING_T3_R6_2026-09-30.md`). The fourth review accepted `47441f3b` with no blocking finding and eight notes (`reviews/OPUS_T3_PR_REVIEW_R4_2026-09-30.md`). The seat squash-merged it with `--match-head-commit` at 12:20:22Z as `ddf03116`.
- **T3 follow-up owed (R6a):** five test pins, a local decimal context for `compare_eps`, and a platform-independent clock form. It changes `CODE_REVISION`, so it lands before Task 4 stores an interpretation in production.
- **T2 rounds 5–6 → MERGED.**
  - The erratum R4.2a (`reviews/SEAT_ERRATUM_T2_R4_2A_2026-09-30.md`) aligned Task 2's unverified currentness with Task 3. Round 5 amends it.
  - Round 5 (`reviews/SEAT_RULING_T2_R5_2026-09-30.md`, rulings R5.1–R5.8 and R5.10–R5.14) was a seat commit on the round-4 lane's return.
  - The second review rejected its head `113323df` on B1: after a transient 503, an older filing could supersede a newer one (`reviews/OPUS_T2_PR_REVIEW_R2_2026-09-30.md`).
  - Round 6 closed it with ruling R6.1: inside one fiscal period the source clock never steps back (`reviews/SEAT_RULING_T2_R6_2026-09-30.md`).
  - The third review accepted head `5f33a5a2` with no blocking finding (`reviews/OPUS_T2_PR_REVIEW_R3_2026-09-30.md`). The seat squash-merged it with `--match-head-commit` at 16:22:30Z as `b1b2ea3b`.
- **Carried to Task 4** from that review:
  - N1: the stored chain of an event must be a prefix of the candidate's chain, entry for entry.
  - N2: a stored workspace's `source_available_at` is never later than its `observed_at`.
- **One standing red on both merges.** `ci-authority/codex/merge-queue-pilot` ("CI authority context rejected") was red on #8232 and #8234 at merge, because each PR edits CI-authority paths. Each PR body named it; it was neither rerun nor worked around. Every other check concluded green.
- **T4 runs in two rounds on one PR.**
  - Round A (`packets/CDV1_T4_R2A_PACKET_2026-09-30.md`, rulings R-A1–R-A12) stages a v2 private generation beside the unchanged v1, and adds one closure validator over the native objects of Tasks 1–3.
  - Round B adds the v2 publish transaction, the readers, the rights seam, the CI job and the deploy restart wiring.
  - Until round B lands, the PR's CI-manifest and restart checks are expected to be red. The PR is not merged between rounds.
  - The seat checked the packet against `main`'s code with its own probes before dispatch. Round A was dispatched at 17:32Z on mini2, with a CPython 3.12 venv to match CI.
- **T3 R6a → MERGED.**
  - PR #8246 implemented rulings R6a.1–R6a.7 (`packets/CDV1_T3_R6A_PACKET_2026-09-30.md`).
  - The independent Opus review accepted head `20b2facd` with no blocking finding (`reviews/OPUS_T3_R6A_PR_REVIEW_2026-09-30.md`). Its EPS oracle and clock sweeps found 0 mismatches.
  - The seat squash-merged it at the exact head at 19:47:29Z as `26b0908e2bb7`, and verified it in `main`'s bytes (`reviews/SEAT_RULING_T3_R6A_2026-09-30.md`). That record also covers the lane-report corrections (m3 is killed; the floors are 77 and 39) and the erratum to R6.6.
  - `CODE_REVISION` moved with it, so Task 4 reads stored interpretations in the stale-carry mode (R-B9) and Task 5 re-derives them (R5.5).
  - The standing `ci-authority/codex/merge-queue-pilot` red was named, and was neither rerun nor worked around.
- **T4 round A verified; round B running.**
  - The seat verified round A at `12da187d`.
  - The round-B packet (`packets/CDV1_T4_R2B_PACKET_2026-09-30.md`, rulings R-B1–R-B14) was dispatched at 19:29Z on mini2, on the same PR. It covers the v2 publish transaction, the readers, the rights seam, the CI job and the deploy restart wiring.
  - Before dispatch, the packet gained the stale-carry reader mode (R-B9) and the round-A validators.
- **T5 packet written.** Rulings R5.1–R5.12 cover:
  - the refresh inside the private publisher, behind a default-off `--economic-refresh` flag;
  - carry-forward as the rollback;
  - a decision table for every collection outcome;
  - no clock renewal on an unchanged rerun;
  - an issuer-keyed public admission guard at both publication boundaries;
  - a real-builder fixture driver.

  It is dispatched once T4 merges. The workflow is not edited; Task 8 turns the flag on after the readers and the safe UI are deployed.
- **Next:**
  1. Seat verification of round B.
  2. An independent read-only Opus review of the integrated T4 head, then concluded CI and a merge with `--match-head-commit`, and the Task 4 ruling record.
  3. Then T5 ∥ T6. The T7 UI and the T8 release still wait for the foundation host edge (#7870).
