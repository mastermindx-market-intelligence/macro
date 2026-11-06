STATUS: PARTIAL

RESULT:
- **Verdict.** The commission verdict for the P20 set is ACCEPT-WITH-NOTES, with one major finding that must be fixed before merge. Every P20 repair clears the CI failure it names, and I found no weakened guard. I checked all four commits and every pytest selection and script the commission named passed when I ran it. Nothing touches GMI: 0 GMI paths differ from main 838a69c08deb. The trackBox edit and the engine docstring keep their files the same length (4183 → 4183 and 1144 → 1144).
- **Strongest surviving objection (MAJOR, must change before merge).** The `templates/subsectors.js` fix for SC-066 / R3A-66 is correct, but it adds 3 lines at about line 220 (582 → 585 lines). That moves the code under four state-matrix citations in the frozen design reference `design_refs/sector-paper-20261021/state_matrix.csv` (rows 19, 26, 33, 34) and `state_matrix.md` (lines 62, 69, 74, 75). The cited lines `subsectors.js:309/496/506/508` now land 3 lines early:
  - HEAD:309 is the avoid-column header; the "Nothing extended" empty state is now at :312.
  - HEAD:506 is `var app = …`; the "No data yet" line is now at :509.
  - The same +3 shift applies to :496 (now :499) and :508 (now :511).

  This is the same problem the commission's rule (d) exists to stop. The trackBox edit was kept line-neutral for exactly this reason; this edit was not. CI did not catch it because `tests/test_sector_paper_state_matrix.py:101` only checks that a cited line is inside the file, and that suite was wired in this same commit. Fix it either way:
  - make the subsectors.js edit line-neutral, or
  - re-point the four citations in both the csv and the md to :312/:499/:509/:511, as recorded post-approval maintenance.
- **What P21 may land as.** P21 may land only as a PARTIAL release: the Sector Central shell, the engines, the design reference and the CI wiring. It must not land as the Sector Cycles replacement, which is still NOT DELIVERED.
- **Other notes (none blocks merge).**
  - The merged P0B receipts combine two separate re-mints. Nobody re-minted them on the merged tree itself. Every hashed input matches that tree, but the layout numbers were never re-measured there.
  - The research-vault textarea now renders differently, and there is no dual-theme evidence for that change.
  - "Measured" and "Measuring" now differ by one suffix but mean opposite things.
  - In `tests/test_ci_pack.py` the docstring says "free-content 137 jobs", but the probe tuple says 138.
  - The 2280 "validated" leftover is recorded in `proposal.yml`, not in the P19 acceptance note.

Per-file table (commit | file | verdict | strongest counter-argument | does it survive? | evidence):

**Commit 1e4d9980e615**

| File | Verdict | Strongest counter-argument | Does it survive? | Evidence |
|---|---|---|---|---|
| templates/subsectors.js | ACCEPT-WITH-NOTE (MAJOR: citation drift) | The edit adds 3 lines and moves four frozen state-matrix citations | **Survives.** The shift is confirmed at HEAD:309/312, 496/499, 506/509, 508/511. The behaviour fix itself is correct: baskets carry `n_listed` (`engine/subsector_confluence.py:489`), sectors carry `n_subsectors` (:414, :605) | `wc -l` 582 → 585; `state_matrix.csv:19,26,33,34`; `test_sector_paper_state_matrix.py:101` checks range only |
| templates/sector_central.html.j2 | ACCEPT-WITH-NOTE | Swapping only the face label could hide a real "validated" state, and "Measured" vs "Measuring" is easy to misread | Does not survive as a defect. The engine key and colours (`--up` vs `--info`) are unchanged and the length is unchanged. The near-homograph is a minor copy-clarity note | 4183 → 4183; `:3413-3414`; `engine/index_leadership_track.py:256-257` |
| .github/ci/legacy-jobs.yml | ACCEPT | Wiring guards that only check line ranges gives false assurance | Partly survives, but only as a note on how weak the guard is. The wiring itself is right: an unscoped reference-integrity job, and the four suites pass | yaml loads, 377 jobs; 4 suites + confluence: 50 passed, 3 skipped |
| tests/test_ci_pack.py | ACCEPT-WITH-NOTE (nit) | The ceilings were raised to fit, not measured | I could not test this (full suite not rerun, per the commission). Each ceiling rose by exactly +9, which matches the claimed 9 → 18 weight. The docstring says 137 jobs for free-content, but the tuple says 138 | `tests/test_ci_pack.py:5431-5435`; `-k` subset 2 passed |
| tests/test_sector_central_paper.py | ACCEPT | It is a string pin, not a render | Does not survive. It pins the served template body between function bounds; the served-page readback is P22 | 237 passed (group run) |
| tests/test_subsector_confluence.py | ACCEPT | It pins the expression, not the behaviour | Does not survive. Dropping the fallback fails the test | 50 passed, 3 skipped (group) |
| research/* records, proposal.yml, agentos | ACCEPT-WITH-NOTE | The records point at the wrong home for the 2280 note, and the R3A-47 pointer is incomplete | **Survives as notes.** The 2280 leftover is recorded at `proposal.yml:2436-2437`, not in `P19_ACCEPTANCE_2026-11-02.md` (that note covers only trackBox, at :58-59). The R3A-47 pointer covers 3 of the 5 artifacts | grep results quoted under EVIDENCE |

**Commit 442713973f2a**

| File | Verdict | Strongest counter-argument | Does it survive? | Evidence |
|---|---|---|---|---|
| tests/test_sector_central.py | ACCEPT | The helper copies `compute()` instead of calling it, so it can drift, and fixing the date could hide a wall-clock bug | Does not survive. It mirrors `compute()` exactly: the loader, then `session_alignment(session or asof, consumer, today)`, then blank on a non-aligned file, then `_fast_lens_status(armed, raw)`. Telling stale from absent works because `_fast_lens_status` re-reads the file itself. The `ts` field is never the gate. The slice test pins the `compute()` call text | `engine/sector_central.py:1071-1094`, `:743-761`; 56 passed |
| engine/sector_central.py | ACCEPT | Hidden code change | Does not survive. Only 4 docstring lines changed; length unchanged | 1144 → 1144 |
| mockups/.../mobile-layout.json and mobile-layout-canada.json | ACCEPT-WITH-NOTE | A one-line hash edit can't be told apart from a hand edit | I could not test this without a browser re-mint. The receipts are consistent: 55/55 path-keyed hashes match the tree in each. The only difference from main is the `site/stocktable.js` line | recomputed hashes; `git diff 838a69c08deb HEAD` |
| mockups/.../manifest.json | ACCEPT (superseded by the merge) | — | — | — |
| templates/dashboard.html.j2 | ACCEPT | Production code was changed to satisfy a test harness | Does not survive. Real browsers always have `window.dispatchEvent`, so no event is lost. The pinned substring still appears twice | `grep -c` = 2; 237 passed |

**Commit 8d1fe9324402**

| File | Verdict | Strongest counter-argument | Does it survive? | Evidence |
|---|---|---|---|---|
| site/research_screener.html | ACCEPT | Hand-stamping a site file | Does not survive. The stamp equals sha256[:8] of `site/watchstore.js`, which is byte-identical to `templates/watchstore.js`. It appears once, and the bake test passes | f43cba98; H4.7: 1 passed |
| templates/research_vault.html.j2 | ACCEPT-WITH-NOTE | It changes rendered styling beyond what the failure required | **Partly survives.** The radius goes 11px → 8px (`--r-ctl` isn't defined at `:root`, so the 8px fallback applies; `theme.css:2131-2135`). The hover goes from accent-tinted to neutral `--mx5-hover-border`. But this block is new on the branch (0 `si-research-entry` hits on main), and both themes define the token (:43 dark, :60 light). There is no dual-theme evidence | reproduced pre-fix: 2 blocking; post-fix: 0 |

**Merge b6b4743f534d (conflict paths only)**

| File | Verdict | Strongest counter-argument | Does it survive? | Evidence |
|---|---|---|---|---|
| mockups/.../manifest.json | ACCEPT-WITH-NOTE | "Exactly what a re-mint on the merged tree produces" is an inference, not a run | **Survives as a GAP.** The receipts combine main's nav re-mint with the branch's stocktable re-mint. The hk/ca digests match the files, all inputs match, and the rendered-fixture is unchanged at main's 949339f3 with 38/38 inputs matching | recomputed digests; closure gate rc=0 |
| .github/ci/legacy-jobs.yml | ACCEPT | Auto-merge could drop the branch's step | Does not survive. 0 lines were removed against parent 1, and the branch's steps are present against parent 2 | 377 jobs |
| site/research_screener.html | ACCEPT | The stamp could be duplicated or lost | Does not survive. It appears once (`?v=f43cba98`) | `uniq -c` = 1 |

EVIDENCE:
- **Commands I ran and what they printed:**
  - `pytest tests/test_sector_central.py tests/test_sector_generation_guard.py` → `56 passed in 3.67s`
  - `pytest tests/test_prophet_plan_relation.py tests/test_prophet_candidate_plan_return.py tests/test_sector_central_paper.py` → `237 passed in 68.87s`
  - `check_p0b_receipt_closure.py --selftest` → `selftest OK`
  - `--diff-file` over the 375 paths in `/private/tmp/claude-501/p20_review_changed.txt` → `rc=0`
  - `pytest tests/test_stock_dashboard_first_frame.py` → `120 passed in 54.91s`. The seat's message claimed 143; my count is 120.
  - Design ratchet on `git diff --unified=0 838a69c08deb HEAD -- templates` → `blocking=0` (estate pre-existing 25321).
  - Pre-fix ratchet reproduction (`--root /private/tmp/claude-501/dsroot_prefix`) → `blocking=2`: `research_vault.html.j2:282 radius-literal`, `:286 color-literal`.
  - H4.7 → `1 passed`
  - `test_ci_pack.py -k "wired or unwired or gated"` → `2 passed, 236 deselected`
  - The four sector-paper suites plus `test_subsector_confluence.py` → `50 passed, 3 skipped`
  - `yaml.safe_load(legacy-jobs.yml)` → 377 jobs
- **Recomputed digests:**
  - `mobile-layout.json` b7abf55c150b3ffafd70f04c9e1ec7b0eea7bb466cf56782c0775c4d812bc326 = manifest hk
  - `mobile-layout-canada.json` 75cbf4a097887f50d83785e7328506cfd55b0d1d8de12d4a8259201643b02c55 = manifest ca
  - `site/stocktable.js` eedfe64934bec3f37aa878ac4b45695f30293cd2ba28a9307c2ebe1fba19b964 = receipt line
  - `rendered-fixture.json` 949339f37416890fba72a9831dcdecac0235533fdc4baf7737b080ddd90ef1d3 = fixture_receipt
  - `site/watchstore.js` sha256[:8] = f43cba98
- **Diff vs main for both mobile receipts:** exactly one line each, `site/stocktable.js` 94935dc1… → eedfe649….
- **Ratchet blocking count:** 0 (pre-fix reproduced at 2).
- **Line counts:**
  - `sector_central.html.j2`: 4183 → 4183
  - `engine/sector_central.py`: 1144 → 1144
  - `research_vault.html.j2`: 1158 → 1158
  - `subsectors.js`: 582 → 585 (the major finding)
- **Pointer lines** (all four rows have verifier verdict UNSUPPORTED; seat pointers are in the `proposal.yml` ledger block P20-R3A-47-52-75-86):
  - **R3A-47: CONFIRMED with a correction.** The seat's pointers resolve: `templates/subsector_rotation.js:3` and `:260`, `templates/rotation_events.js:8`, `:203` and `:986`. But the contract names five artifacts. The missing two are at `templates/desk_watch.js:20-21` (`oracle_turn_desk.json`, `oracle_tape_onset.json`); the seat pointer omits them.
  - **R3A-52: CONFIRMED.** `templates/heatmap.js:242` has `setInterval`, and `:264` skips when `generated_utc` is unchanged, which is the poll-and-swap.
  - **R3A-86: CONFIRMED-PARTIAL.** `sector_central.html.j2:1503-1507`, `:1535-1536`, `:2096`, `:2438` and `:3872` hold the view hrefs. Overview lives at `:1496` (`href="#overview"`), which the pointer omits. Whether the runtime-generated destinations keep their native order and semantics was not proven.
  - **R3A-75: FOUND (was not found by the verifier or the seat).** `engine/subsector_confluence.py:270-271`: `members_detail.sort(key=(-stock_weight, -vs_basket))`. `templates/subsector_detail.html.j2:191,194` render the members in producer order. The row can move to CONFIRMED once the seat records this pointer.

GAPS:
- I did not re-run the P0B browser recipe, so I could not distinguish a real re-mint from a hand edit for the receipts in 442713973f2a or for the merge.
- I did not rerun the full `tests/test_ci_pack.py`, per the commission. The ceiling values are the seat's measurements, not mine.
- I did not run `tests/test_check_p0b_receipt_closure.py`, the research_vault suites or the GMI suites; they were out of my named scope.
- There is no dual-theme or EN/ZH visual evidence for the textarea restyle or the trackBox label change. Browser and production proof is P22's.
- I did not check whether the 3 sector-paper skips come from the sparse tree; I didn't read the skip reasons. I hit no FileNotFoundError in my selections.

DEVIATIONS: I wrote scratch files only under /private/tmp/claude-501/: `p20_review_changed.txt`, `rv_prefix.diff`, and `dsroot_prefix/templates/research_vault.html.j2` (the pre-fix copy, for the ratchet reproduction). Nothing was written inside the repository, I ran no git command that changes state, and no `gh`.