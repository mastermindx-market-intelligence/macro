# GMI Theme Graph — continuation handoff 2026-10-05 (Fable Meta-CEO seat `6f14c2da`)

**Workstream:** `WS:GMI-THEME-GRAPH`. **Master Plan carrier:** PR #8324 (Sol handoff comment `5991777960`, 2026-10-05T09:30:21Z, `CHECKPOINTED_CONTINUATION`, `MISSION_COMPLETE: false`).
**Seat mandate (Chairman, 2026-10-05):** act as Meta-CEO for the program; finish end to end via the subagent fabric (GLM-flash → GLM → Grok/Cursor → Opus last resort); no Claude-native subagents; save blockers for the Chairman last.
**Pin at write:** `origin/main` = `192a46de8be8` (amended 2026-10-05 ~14Z by the same seat; first pin `20eb503a09aef8bc2ccc8945f1ea140bdc9aeace`).

This file is the resumption record. A successor seat loses at most one cycle by reading it: §1 is the ladder per carrier, §2 the decisions already taken (DO_NOT_REDO), §3 the open gates by owner, §4 the next bounded actions.

---

## 1. Carrier ladder (rung reached, evidence, and what the seat may do)

Ladder: `ACK → QUEUED → START → RUNNING → DELIVERED → CI → MERGED → PRODUCTION_PROOF → ACCEPTANCE`. None implies the next.

| Wave | Carrier | Head at write | Rung | Hold | Seat may |
|---|---|---|---|---|---|
| A — state owner adapter / CTE-v3 lineage | #8455 (DRAFT) | `4b38f2501a3b` (round-2 repair: `regime-outlook-mapping` + `nw-lobe-unfreeze` path widenings in `legacy-jobs.yml`; contract-delta local 0/0) | CI **green**: ci.yml `37307906336` completed/success 12:45Z; reds from the first head classified in issuecomment-5994191898 (ci-pack-0 q06 INHERITED, healed by #8484; contract-delta OWN, closed) | **Sol HOLD** — PARKED | nothing: no arm/ready/merge; Sol release ruling is the next act |
| B — CTE-v3 delta review | local grok lane | PASS-WITH-NITS, folded into Wave A's lineage merge | ACCEPTANCE (seat) | — | nothing further |
| C — current-use rights capture `engine/theme_graph/rights_use.py` | #8485 | `f0991eade1e6` | **MERGED** 2026-10-05T12:44:43Z by the sweeper, squash `fd2552813811`; blob-verified on `origin/main` after a bare `git fetch origin main` (rights_use.py SAME, test SAME, legacy-jobs.yml carries the wiring) | — | nothing (DO_NOT_REDO) |
| D1 — W3C seams on CTE successor | #8417 (DRAFT) | `bddb73d9cb9e` (path widening in `legacy-jobs.yml` for conviction-profile / nw-lobe-unfreeze / unrun-picks-boards, over the merge-of-main `65ee41785e1c`) | CI: ci.yml 37320358321 in flight at record time (expected: ci-pack-0 + contract-delta green; ci-pack-2 inherits main's readiness red until this PR lands, then a plain merge-of-main re-proof); seat classification comment 5995904316; both prior reds classified in issuecomment-5994839328 (ci-pack-0 q06 INHERITED → #8484; ci-pack-10 import DEPENDENCY → #8485 merged); local `test_first_party_import_names` 15 passed | **Sol HOLD** — PARKED | nothing: no arm/ready/merge; Sol release order #8417 → #8486 |
| D2 — selection-clock qualified reads | #8486 (DRAFT, base = #8417's branch) | `2e2bcd75ca62` | DELIVERED + seat ACCEPT (192 passed / 56 skipped locally; owner reads via store/identity_resolution/rights/theme_state/ontology) | **PARKED by inheritance** (stacked on #8417) | nothing until #8417 releases; ci-authority FAIL is structural `unsupported_base_ref` (`DSC:A-STACKED-PR-ON-A-NON-MAIN-BASE-GETS-NO-PULL-REQUEST-CI`) |
| D2C — PIT vintage completion | #8432 (DRAFT) | `54d17ebcb1c1` | CI green on head (`37206291268`) | **Sol HOLD** | Wave E qualification done: merge-tree vs main CLEAN, zero path movement; never ready/arm/merge |
| D2D — ontology + probation breadth / structural owner binding | #8435 (DRAFT) | `7429a3e5f6da` | CI green on head (`37242875242`) | **Sol HOLD** | same as D2C; **#8432 + #8435 CONFLICT in `.github/ci/legacy-jobs.yml`** (`DSC:GMI-D2C-AND-D2D-CARRIERS-CONFLICT-IN-LEGACY-JOBS-YML`) — second to land must rebase its CI block |
| D2E — rights / coverage / D2 acceptance | #8488 | `0060ac74f310` (sweeper refresh of `a1bd8c5cc117`) | **MERGED** squash `192a46de8be8` (pre-acceptance census only; the 5 DECISIONS REQUIRED and the D2B3 clause stay open in §3) | depends_on D2C+D2D acceptance | nothing until D2C/D2D land |
| E — re-pin / qualification | seat | — | ACCEPTANCE (merge-tree clean ×2 for #8432/#8435; no cosmetic ancestry joins made) | — | re-run only on a material main movement under `engine/theme_graph/**` |
| F — Terminal / R2 / human-consumer proof | #8490 | `2e0c8d2e3908` (sweeper refresh of `da8721465e67`) | accepted by artifact; **MERGED** 2026-10-05 14:46:17Z, squash `d8f08cffd319` (refresh after the main heal landed: visible disarm, plain merge of healed main `601f87f39924` → final head `6a21e2b302a1`, re-arm last; ci.yml 37323909239 green; merged by hand with `--match-head-commit`; both paths blob-verified on origin/main): read-only consumer census `research/theme_graph/WAVE_F_TERMINAL_R2_CONSUMER_CENSUS_2026-10-05.md` + `.json`, delivered by a ubuntu1 cursor composer-2.5 lane (m1 refused auth — deviation, Chairman ladder rung 3) and judged by artifact against main `81eb0c9b3993` and Terminal `2ca21c44718a`: 6 MATCH / 1 UNKNOWN (no Terminal consumer for v2/cohort), 4 gaps recorded in the JSON | — | cross-repo Terminal proof for v2/cohort remains a Sol/Chairman gate |
| G — independent completion-ruler audit | #8487 | `5957918bbf34` | **MERGED** squash `625d0c71714d` (blob-verified) | — | nothing |
| records | #8489 → this follow-up | `23df8374a768` (sweeper refresh) | #8489 **MERGED** squash `c0f4a83ce974`; this PR amends it | — | ordinary merge |

Seat annotations on the accepted lane reports (not repairs — both lanes were read-only and reported honestly):
- G §5 reads the newest `daily.yml` success as 2026-09-29, but the natural store on main carries `data/theme_graph/_meta.json` `computed_at` **2026-10-05T07:55:06Z**, `lane: nightly`, 3,882 nodes (D2E census C0(c)). The nightly is live; the audit's workflow-name read is the stale instrument, not the store.
- G §4 NEXT advises not arming #8485 until Sol clears Wave C. The seat had already accepted and armed #8485 at 11:12Z as seat-owned ordinary work (standalone module + tests; its only shared path with the held carriers is `legacy-jobs.yml`). That decision stands; the audit lane did not hold the handoff context. A late Sol ruling to the contrary outranks it (O.12).

## 2. DECIDED (DO_NOT_REDO absent a material invalidator)

1. Wave A accepted and pushed onto #8455 as an ORDINARY merge (never a force-push); #8455 flipped CONFLICTING → MERGEABLE. Do not re-run the packing lane, do not push the stale local lineage over `029fe5b17f0f`.
2. Wave B review accepted (PASS-WITH-NITS); nit 1 folded into the lineage merge. Do not re-review the CTE-v3 delta.
3. Wave C (#8485) accepted by artifact and armed. Do not re-open its design; the sweeper or the seat merges it on concluded green.
4. Wave D1 accepted as a lane result on held #8417; its ci-pack-10 red is the rights_use composition dependency, not a defect of D1. Do not "fix" the import by vendoring `rights_use` into #8417.
5. Wave D2 accepted as a lane result on #8486; PARKED by inheritance. Do not retarget #8486 to main before #8417 lands (it would carry #8417's 13 paths and collide).
6. Wave A round-2 repair (`4b38f2501a3b`): the two `legacy-jobs.yml` widenings are the contract-delta remedy and were proven by run `37307906336`. Do not re-classify the earlier reds or re-run the pack validation (weights unchanged).
7. Wave C landed (#8485 → `fd2552813811`); D1 was re-proved by a plain merge-of-main (`65ee41785e1c`) and its own next-layer reds (three curated jobs reaching `rights_use.py`/`rights.py`) closed by path widening (`bddb73d9cb9e`). Do not vendor, rebase, or force-push on #8417; do not retarget #8486.
8. Wave F accepted by artifact (#8490): the census is a read-only consumer map, not a Terminal change. The m1 refusal → ubuntu1 cursor deviation is recorded; do not re-run the census unless the Terminal pin `2ca21c44718a` or the macro C0 writer moves.
9. Watchers written from a non-checkout cwd must use `gh api` (REST `pulls/N` reports `closed` + `merged_at`), never `gh pr view` — the first #8490 watcher read `err` for 17 ticks and was replaced.
6. Wave E qualification: #8432 and #8435 each merge clean against main with zero path movement since their pins; no cosmetic ancestry joins were made and none are to be made.
7. Wave G audit and D2E pre-census accepted as read-only reports; their DECISIONS REQUIRED lists are carried to the Chairman gate list (§3) and are not to be re-derived.
8. Routing: GLM lives only on mini2, which is disk-blocked (`STORAGE_GUARD_LOW_SPACE`, never override `min_free_gb`); lanes ran on ubuntu1/ubuntu2 under cursor composer-2.5 with `review_engine: seat` — recorded deviation, Chairman ladder rung 3. No Claude-native subagents were spawned.

## 3. Open gates by owner (saved for last, per the Chairman's instruction)

**Sol (holding authority on #8324):**
- Release order for the held stack, #8485 now MERGED: #8417 (D1, head `bddb73d9cb9e`) → #8486 (D2, retarget to main only after #8417 lands); and D2C #8432 / D2D #8435 (the second needs a `legacy-jobs.yml` rebase). Each release is one `HOLD-RELEASED` line on the carrier.
- Wave A #8455 release: ci.yml `37307906336` on `4b38f2501a3b` is green; the hold is the only thing between the PR and a merge.
- D2E acceptance after D2C+D2D land: D2B3 natural-proof clause reconciliation against the latest nightly `_meta.json` / `identity_resolution.parquet` (contract `research/prophet_v4/d2/D2B3_FROZEN_CONTRACT_2026-08-21.md`).
- Cross-repo Terminal proof (Wave F) and the per-application economics/leadership DEC rows (ruler §8).

**Chairman (rights / infrastructure):**
1. `finviz_themes` and `ths_concepts` rights class: `unresolved` → `derived_display_ok` or `internal_only` for new GMI emissions (registry `config/theme_sources.yml`).
2. `site/factordata/us_standouts.json`: mint a registry row + rights class if any GMI coverage reporter treats Prophet board rows as a source family, or exclude it from GMI emission scope (today: provenance string only, `SOURCE_FAMILY_UNRESOLVED`).
3. Probation `relation_events.v2.jsonl` `source_ref` prefix: map `data/theme_graph/probation/...` in `SOURCE_PREFIX_FAMILY` or forbid it as an evidence ref.
4. Ontology-action authority resolver wiring (D2C body: "remains UNWIRED"; `OWNER_ACTION_AUTHORITY_UNAVAILABLE` has no matches on main+#8432).
5. m1 Terminal-host auth (refused) or an alternative Terminal-capable host for Wave F.
6. mini2 disk (GLM host) — operator act; until then GLM-first routing is unavailable and cursor on ubuntu is the lawful rung.

## 4. NEXT (bounded, in order)
10. main's ci-pack-2 red (`tests/test_agentos_status.py::test_readiness_states_explain_graph_and_authored_progress`) was CAUSED by #8489 flipping D2C/D2D to `in_progress` — an in_progress wave outranks a blocked parent in `_reason_for_wave`. Healed in this PR by synthesizing the D2C wave status to `todo` inside the test's fixture copy. Never revert D2C to `todo` in the live record to green the test; run `tests/test_agentos_status.py` locally before pushing any agentos record edit.

Done since the first write (DO_NOT_REDO): #8485 blob-verified MERGED; #8417 merge-of-main pushed and commented; #8455 repaired, green, commented; Wave F census MERGED and blob-verified (#8490 → `d8f08cffd319`); #8487/#8488/#8489 merged.

1. Sol release rulings (one `HOLD-RELEASED` line each): #8417 → #8486 (retarget to main after #8417 lands, then a fresh merge-ref run) → #8455; #8432 / #8435 order plus the `legacy-jobs.yml` rebase of whichever lands second.
2. On each release: the releasing seat merges on concluded green with `--match-head-commit <exact head>`, then `git fetch origin main` ALONE and blob-compares the PR's paths.
3. D2E acceptance (after D2C+D2D land): D2B3 natural-proof reconciliation against the then-current nightly `_meta.json` / `identity_resolution.parquet`; the 5 DECISIONS REQUIRED in §3 stay open until the Chairman rules.
4. Wave F cross-repo: a Terminal consumer for v2/cohort does not exist (census verdict UNKNOWN); that is a product decision for Sol/Chairman, not a lane to spawn.
5. Hand the §3 list to the Chairman as the final report item.

## 5. Danger areas

- Every held PR (#8455, #8417, #8432, #8435, #7870, #7886, #8486 by inheritance) binds all merge paths; a label, a `gh pr ready`, or a merge on any of them is a violation regardless of check state.
- A push to a held PR needs a freshness re-read of its carrier first; rollup watchers miss it.
- A stacked PR shows a structural `ci-authority` red and no `pull_request` CI; do not "heal" it, and do not retarget it early.
- `#8432` + `#8435` conflict in `legacy-jobs.yml`; whichever lands second must rebase its CI block, and a pack is ONE check — never split a heal across two PRs.
- Never run the full pipeline (`scripts.build_theme_graph`) in a session worktree (`DSC:THEME-GRAPH-FULL-REBAKE-DIVERGES-LOCALLY`); never `git add -A` a `data/`/`site/` diff in a sparse tree.
