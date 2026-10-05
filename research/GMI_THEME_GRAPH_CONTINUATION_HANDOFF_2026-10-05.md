# GMI Theme Graph — continuation handoff 2026-10-05 (Fable Meta-CEO seat `6f14c2da`)

**Workstream:** `WS:GMI-THEME-GRAPH`. **Master Plan carrier:** PR #8324 (Sol handoff comment `5991777960`, 2026-10-05T09:30:21Z, `CHECKPOINTED_CONTINUATION`, `MISSION_COMPLETE: false`).
**Seat mandate (Chairman, 2026-10-05):** act as Meta-CEO for the program; finish end to end via the subagent fabric (GLM-flash → GLM → Grok/Cursor → Opus last resort); no Claude-native subagents; save blockers for the Chairman last.
**Pin at write:** `origin/main` = `20eb503a09aef8bc2ccc8945f1ea140bdc9aeace`.

This file is the resumption record. A successor seat loses at most one cycle by reading it: §1 is the ladder per carrier, §2 the decisions already taken (DO_NOT_REDO), §3 the open gates by owner, §4 the next bounded actions.

---

## 1. Carrier ladder (rung reached, evidence, and what the seat may do)

Ladder: `ACK → QUEUED → START → RUNNING → DELIVERED → CI → MERGED → PRODUCTION_PROOF → ACCEPTANCE`. None implies the next.

| Wave | Carrier | Head at write | Rung | Hold | Seat may |
|---|---|---|---|---|---|
| A — state owner adapter / CTE-v3 lineage | #8455 (DRAFT) | `029fe5b17f0f` (merge of lineage `d3195488ef6` + integrity remedy `61ed68e2078`) | CI (ci.yml `37300796142` in flight at write; fences ✓; ci-authority ✓) | **Sol HOLD** | one result comment; never ready/arm/merge |
| B — CTE-v3 delta review | local grok lane | PASS-WITH-NITS, folded into Wave A's lineage merge | ACCEPTANCE (seat) | — | nothing further |
| C — current-use rights capture `engine/theme_graph/rights_use.py` | #8485 (READY) | `74467f24300a` | CI (ci.yml `37299976182` in flight) → armed `merge-on-green` 11:12Z | none (seat-owned, ordinary) | sweeper merges on concluded green, or `gh pr merge 8485 --squash --match-head-commit 74467f24300a310106242cba2e4f0becbe19c8e8`; then blob-verify |
| D1 — W3C seams on CTE successor | #8417 (DRAFT) | `d02ebf451f1d` | CI **red**: ci.yml `37299950277` completed/failure — the only failing unit is `tests/test_first_party_import_names.py::test_every_first_party_import_resolves` on `engine/theme_graph/selection_cohort_publication.py:48` importing `engine.theme_graph.rights_use`, which exists only on #8485 (`DSC:GMI-D1-SEAMS-IMPORT-WAVE-C-RIGHTS-USE`) | **Sol HOLD** | after #8485 merges: freshness re-read of the #8417 carrier, then push a plain merge-of-main so a fresh merge-ref run proves the heal; never ready/arm/merge |
| D2 — selection-clock qualified reads | #8486 (DRAFT, base = #8417's branch) | `2e2bcd75ca62` | DELIVERED + seat ACCEPT (192 passed / 56 skipped locally; owner reads via store/identity_resolution/rights/theme_state/ontology) | **PARKED by inheritance** (stacked on #8417) | nothing until #8417 releases; ci-authority FAIL is structural `unsupported_base_ref` (`DSC:A-STACKED-PR-ON-A-NON-MAIN-BASE-GETS-NO-PULL-REQUEST-CI`) |
| D2C — PIT vintage completion | #8432 (DRAFT) | `54d17ebcb1c1` | CI green on head (`37206291268`) | **Sol HOLD** | Wave E qualification done: merge-tree vs main CLEAN, zero path movement; never ready/arm/merge |
| D2D — ontology + probation breadth / structural owner binding | #8435 (DRAFT) | `7429a3e5f6da` | CI green on head (`37242875242`) | **Sol HOLD** | same as D2C; **#8432 + #8435 CONFLICT in `.github/ci/legacy-jobs.yml`** (`DSC:GMI-D2C-AND-D2D-CARRIERS-CONFLICT-IN-LEGACY-JOBS-YML`) — second to land must rebase its CI block |
| D2E — rights / coverage / D2 acceptance | #8488 (READY, armed 11:35Z) | `a1bd8c5cc117` | DELIVERED + seat ACCEPT (pre-acceptance census: main+#8432 slice 524 passed; contracts guard selftest OK; 5 DECISIONS REQUIRED) | depends_on D2C+D2D acceptance | merge the census; D2E acceptance itself waits on Sol releasing #8432/#8435 |
| E — re-pin / qualification | seat | — | ACCEPTANCE (merge-tree clean ×2 for #8432/#8435; no cosmetic ancestry joins made) | — | re-run only on a material main movement under `engine/theme_graph/**` |
| F — Terminal / R2 / human-consumer proof | not started | — | — | m1 (only Terminal-capable host) refused auth; Terminal repo `mastermindx-market-intelligence/mastermind-terminal`, last pinned cutover-normalizer epoch `2ca21c44718a9f44c5ab74baaa42afbd14623399` | macro-side CTE/R2 contract census is possible; the cross-repo proof is a Sol/Chairman gate |
| G — independent completion-ruler audit | #8487 (READY, armed 11:35Z) | `5957918bbf34` | DELIVERED + seat ACCEPT (13 sections; 0/9 ruler items PROVEN, 2 HELD_BY_AUTHORITY, rest PARTIAL/UNPROVEN) | — | merge the audit |
| records | this PR | — | — | — | ordinary merge |

Seat annotations on the accepted lane reports (not repairs — both lanes were read-only and reported honestly):
- G §5 reads the newest `daily.yml` success as 2026-09-29, but the natural store on main carries `data/theme_graph/_meta.json` `computed_at` **2026-10-05T07:55:06Z**, `lane: nightly`, 3,882 nodes (D2E census C0(c)). The nightly is live; the audit's workflow-name read is the stale instrument, not the store.
- G §4 NEXT advises not arming #8485 until Sol clears Wave C. The seat had already accepted and armed #8485 at 11:12Z as seat-owned ordinary work (standalone module + tests; its only shared path with the held carriers is `legacy-jobs.yml`). That decision stands; the audit lane did not hold the handoff context. A late Sol ruling to the contrary outranks it (O.12).

## 2. DECIDED (DO_NOT_REDO absent a material invalidator)

1. Wave A accepted and pushed onto #8455 as an ORDINARY merge (never a force-push); #8455 flipped CONFLICTING → MERGEABLE. Do not re-run the packing lane, do not push the stale local lineage over `029fe5b17f0f`.
2. Wave B review accepted (PASS-WITH-NITS); nit 1 folded into the lineage merge. Do not re-review the CTE-v3 delta.
3. Wave C (#8485) accepted by artifact and armed. Do not re-open its design; the sweeper or the seat merges it on concluded green.
4. Wave D1 accepted as a lane result on held #8417; its ci-pack-10 red is the rights_use composition dependency, not a defect of D1. Do not "fix" the import by vendoring `rights_use` into #8417.
5. Wave D2 accepted as a lane result on #8486; PARKED by inheritance. Do not retarget #8486 to main before #8417 lands (it would carry #8417's 13 paths and collide).
6. Wave E qualification: #8432 and #8435 each merge clean against main with zero path movement since their pins; no cosmetic ancestry joins were made and none are to be made.
7. Wave G audit and D2E pre-census accepted as read-only reports; their DECISIONS REQUIRED lists are carried to the Chairman gate list (§3) and are not to be re-derived.
8. Routing: GLM lives only on mini2, which is disk-blocked (`STORAGE_GUARD_LOW_SPACE`, never override `min_free_gb`); lanes ran on ubuntu1/ubuntu2 under cursor composer-2.5 with `review_engine: seat` — recorded deviation, Chairman ladder rung 3. No Claude-native subagents were spawned.

## 3. Open gates by owner (saved for last, per the Chairman's instruction)

**Sol (holding authority on #8324):**
- Release order for the held stack: #8485 (seat, armed) → #8417 (D1) → #8486 (D2); and D2C #8432 / D2D #8435 (the second needs a `legacy-jobs.yml` rebase). Each release is one `HOLD-RELEASED` line on the carrier.
- Wave A #8455 release once its ci.yml run concludes (the q06 curated-scope red seen earlier is inherited from main; #8484 landed the curated-scope cover on main and a fresh merge-ref run is the test).
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

1. On the CI watcher's report: #8485 merge → `git fetch origin main` ALONE → blob-compare its 3 paths + `git grep capture_capability origin/main -- engine/theme_graph/rights_use.py` → record MERGED.
2. Freshness re-read of #8417's carrier, then push a plain merge-of-main to its branch so the merge-ref run re-tests `test_every_first_party_import_resolves`; one seat comment with the result. Never ready/arm/merge.
3. One seat comment on #8455 with its concluded ci.yml result and the q06 classification.
4. Seat checkpoint on #8324 (own fence `>5991959730`): rungs per §1, gates per §3.
5. Wave F macro-side census (read-only lane): enumerate the versioned state→CTE→R2/API contract surface on main and in #8455/#8417, and the Terminal consumer paths pinned at `2ca21c44718a`; no Terminal writes.
6. Hand the §3 list to the Chairman as the final report item.

## 5. Danger areas

- Every held PR (#8455, #8417, #8432, #8435, #7870, #7886, #8486 by inheritance) binds all merge paths; a label, a `gh pr ready`, or a merge on any of them is a violation regardless of check state.
- A push to a held PR needs a freshness re-read of its carrier first; rollup watchers miss it.
- A stacked PR shows a structural `ci-authority` red and no `pull_request` CI; do not "heal" it, and do not retarget it early.
- `#8432` + `#8435` conflict in `legacy-jobs.yml`; whichever lands second must rebase its CI block, and a pack is ONE check — never split a heal across two PRs.
- Never run the full pipeline (`scripts.build_theme_graph`) in a session worktree (`DSC:THEME-GRAPH-FULL-REBAKE-DIVERGES-LOCALLY`); never `git add -A` a `data/`/`site/` diff in a sparse tree.
