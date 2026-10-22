# Wave A landing return (A1 #9954, A2 #9956, A3 #9955), 2026-10-21

STATUS: DONE. The fix refs exist, each a single commit whose parent is its PR head. Two
rehome refs (merge of current origin/main) are the landing candidates for A1 and A2.
Nothing was pushed, posted, merged or labeled. All refs live in the seat worktree object
store under refs/pro/.

Acceptance was run on byte-verified exports of the merge with origin/main
1f536032d446e2b51bda47f0575e371f0c4a0aae (re-run after main moved past the earlier pin
c6bbf9bf; 0 mismatches between each export and its tree).

## Return table

| PR | head | fix ref -> commit (tree) | parent | stat (head..fix) | ratchet: check_design_system enforce-added | visual evidence: check_ui_visual_evidence + cells | tests (on new-main merge export) | probe | merge-tree vs origin/main 1f536032 |
|---|---|---|---|---|---|---|---|---|---|
| A1 #9954 | 25f6ca41 | refs/pro/wa-a1-fix -> d4219e7f196cbf47e553657db1d81d7cb9bae26a (30ab14ef) | 25f6ca414a495c4d1592368f23decf66dbb5e3ec only | 25 files, +1292/-3 | rc=0 (fix vs PR merge-base); rc=0 (rehome merge vs main) | ui rc=0 both variants; macro 8 rest, plan-cards 8 rest; all cells match their manifest; 0 orphan PNGs | plan_cards + research_screener 78 passed; p0b first_frame + closure tests 136 passed; check_p0b_receipt_closure rc=0 (all on the rehome tree) | 1 passed; breaches [] | fix: CLEAN, tree 3b004601819f32dff6f4af0fd91a3b26ba674681, but the p0b gate is RED there (see GAPS). Rehome refs/pro/wa-a1-rehome 7fa87f9bf42492573ac3a743ff8bd9b0f7878cb6: CLEAN, tree d534b79302df33c242278461eb358826bd6e522c |
| A2 #9956 | b48469a5 | refs/pro/wa-a2-fix -> 3f406fc8a40bc4f31e687f4096984b8ef07fc21d (5eb10576) | b48469a57949dfffc1d152a50077d4dff1a88471 only | 24 files, +904/-73 | rc=0 / rc=0; negative control rc=1 | ui rc=0 both variants; watchlist 8 rest + 8 forced row_hover; all match; 0 orphans | test_prophet_r7_wave_a_watchlist + test_research_screener + test_site_assets: 86 passed, 1 skipped (fresh_bake included); node --check ok | 1 passed; breaches [] | fix: DIRTY, site/research_screener.html stamp line only, tree d36af066. Rehome refs/pro/wa-a2-rehome ce64b9795c4095a77c889fe378dd8002fb3620ad: CLEAN, tree a89af0d2cef9884b5915f7cf9ba72525313def43 |
| A3 #9955 | 21a95484 | refs/pro/wa-a3-fix -> ff052167aa16b2463bc9f1468412806c9c1842e0 (b39a3419) | 21a95484becdc5c5671e9a3f5586cc5890840e06 only | 20 files, +742 | rc=0 / rc=0; negative control rc=1 | ui rc=0 both variants; receipts 8 rest + 8 rc-focus; all match; 0 orphans | test_prophet_r7_wave_a_guards 24 passed; screener fresh_bake 1 passed | 1 passed; breaches [] | fix: CLEAN, tree 91392cedf9dd5162f06df7609306d54b2a92a81c |

Probe values were measured on all three new-main merge exports with packing_probe_measurements:

| probe | jobs | max jobs | weight | max weight |
|---|---|---|---|---|
| templates/index.html | 135 | 136 | 5841 | 5841 |
| scripts/build_free_content.py | 135 | 135 | 5814 | 5814 |
| engine/prophet/plan_book.py | 128 | 130 | 5590 | 5600 |

No tests/test_ci_pack.py change was needed: the ceilings compose with main. Main's
docstring notes are untouched.

Earlier pin (main c6bbf9bf), superseded but kept for the record:
- A1 merged clean (a177b5b0), with the same p0b RED. The rehome was 9aec1c0c.
- A2 was DIRTY in the screener only. The rehome was f7edc2e1.
- A3 merged clean (a7011f21).
- Every check was green on those exports too.

## Ref parents (git rev-list --parents -1)

- wa-a1-fix d4219e7f, parent 25f6ca41
- wa-a2-fix 3f406fc8, parent b48469a5
- wa-a3-fix ff052167, parent 21a95484
- wa-a1-rehome 7fa87f9b, parents d4219e7f and 1f536032. Delta over the textual merge: 3 files in mockups/evidence/prophet-p0b-zero-fouc, +4/-4.
- wa-a2-rehome ce64b979, parents 3f406fc8 and 1f536032. Delta over main in site/research_screener.html: `watchstore.js?v=3812c6a9 -> dd730491` only.

Each rehome ref is a fast-forward of its fix ref, which is a fast-forward of its PR head.

## Seat next commands (not executed here; push is out of scope)

- A1: push `refs/pro/wa-a1-rehome` to #9954's branch.
- A2: push `refs/pro/wa-a2-rehome` to #9956's branch.
- A3: push `refs/pro/wa-a3-fix` to #9955's branch.

If main moves again, rerun `git merge-tree --write-tree origin/main <ref>` before pushing.
For A1 and A2, a moved main may also need a re-bake:
- A2: rerun `$S/rehome_screener.py`.
- A1: rerun the p0b verify scripts, then `$S/p0b_rebind.py`.

## GAPS

1. **A1 single-parent ref is RED on CI.** On the plain merge of refs/pro/wa-a1-fix, the
   p0b receipt-closure gate and the 2 self_binding tests fail. The receipts pin
   site/theme.css, and A1 changes it. The fix cannot carry the remint as a single parent:
   - main edited the same receipt lines;
   - the merge-file simulation conflicts (798d419e).

   So only refs/pro/wa-a1-rehome is CI-green for p0b.
2. **A2 single-parent ref cannot merge clean.**
   - The commission requires the screener stamp rebake on each fix.
   - Base, main, fix and merged bytes need four different watchstore stamps: 03277dd8,
     3812c6a9, eaad5a7c, dd730491.
   - Any single-parent value either conflicts or fails fresh_bake on the merge.

   Amendment 2 assumed A2 "still merges clean"; that held for the PR head, not for the
   fix. Land via refs/pro/wa-a2-rehome.
3. **Probe weight headroom is 0** on index (5841/5841) and free-content (5814/5814). These
   are main's own values, and the PRs pass. The next probe-selected registration on main
   will need a ceiling bump.
4. **Known 404s in the macro receipt.** It records 11 console errors and 10 failed
   responses: live/risk_envelope.json, live/release_publications.json and api/brain/me,
   which are absent in a static capture.
5. **Pre-existing stripe in the plan-cards specimen, not modified.** The specimen carries
   production CSS `.pvs-availability{...border-inline-start:2px solid var(--muted)...}`
   from templates/_prophet_card.html.j2:577 (since #7237). It is unused and not rendered
   in the specimen. It conflicts with the Chairman's no-accent-stripe rule; recommend a
   separate cleanup PR.
6. **Capture tool version.** The receipts were captured with capture tool v1.3.0; main
   now has v1.4.0. The checker accepts both.
7. **Environment-only items:**
   - rjsmin==1.2.5 (the pinned requirements.txt dependency) was installed into scratch
     pylib. Without it, 6 test_site_assets cases fail with ModuleNotFoundError.
   - A node playwright shim lives at $S/nodeshim.
   - One Playwright capture was retried after a transient launch failure.
   - test-6 of the A2 packet was reseeded.

   The rendered watchlist.html is a build product and was not committed.

## DEVIATIONS

1. **Commit trailer.** I used `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`,
   not the commissioned Fable 5.1 line, because the author model is Opus 5.5 and the
   session attribution rule requires it.
2. **A1 legacy-jobs placement.** The A1 step sits before the B05 step. Merged order: A1,
   B05, B4 nightly, B4 producer basis.
   - The literal amended order (B4 nightly, A1, B4 producer basis) cannot be carried by a
     commit parented on 25f6ca41 without a textual conflict (proofs dc3f4b60/04b6815e).
   - Main's B4 nightly step and its comment are byte-identical to main.
   - The merge diff against main on legacy-jobs.yml is +3 lines (the A1 step only).
3. **A1 manifest rebind beyond Amendment 1.**
   - The remint used only the repo's tools.
   - Making test_visual_manifest_preserves_history_and_appends_bounded_repair pass also
     needed manifest.json browser_receipts.{hk,ca}.sha256 rebound to the reminted bytes,
     by script ($S/p0b_rebind.py).
   - This is the same pattern as main's earlier remints #9650 and #9178.
   - The rebind is in the rehome only; the fix ref is untouched.
4. **Rehome refs are merge commits (2 parents)**, created because both fix refs need one
   to land green. The seat owns adoption.
5. **Commit method.** Trees were built with a private GIT_INDEX_FILE ($S/mkfix.py) and
   commit-tree. The seat worktree index and branch were never touched.

## Stats per ref

### git diff --stat 25f6ca41 refs/pro/wa-a1-fix
```
 .github/ci/legacy-jobs.yml                                          |   4 +-
 mockups/evidence/prophet-r7-wave-a/macro/00b0f1016d24ba50.png       | Bin 0 -> 531407 bytes
 mockups/evidence/prophet-r7-wave-a/macro/26b9578526d401a1.png       | Bin 0 -> 766237 bytes
 mockups/evidence/prophet-r7-wave-a/macro/39a79232afba21a8.png       | Bin 0 -> 739494 bytes
 mockups/evidence/prophet-r7-wave-a/macro/46f61a38de1ccdc1.png       | Bin 0 -> 511108 bytes
 mockups/evidence/prophet-r7-wave-a/macro/EVIDENCE.yml               |   5 ++
 mockups/evidence/prophet-r7-wave-a/macro/NOTES.md                   |  29 ++++++++
 mockups/evidence/prophet-r7-wave-a/macro/a2600506123adaef.png       | Bin 0 -> 536987 bytes
 mockups/evidence/prophet-r7-wave-a/macro/b2a92d7ce1d35a8e.png       | Bin 0 -> 408067 bytes
 mockups/evidence/prophet-r7-wave-a/macro/d8d0b43ab4b6a0f1.png       | Bin 0 -> 536277 bytes
 mockups/evidence/prophet-r7-wave-a/macro/ef16cf2da9691f0e.png       | Bin 0 -> 400569 bytes
 mockups/evidence/prophet-r7-wave-a/macro/manifest.json              | 391 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 mockups/evidence/prophet-r7-wave-a/plan-cards/08ebf2dc738d8563.png  | Bin 0 -> 260448 bytes
 mockups/evidence/prophet-r7-wave-a/plan-cards/1d3fb4ffc3d4d6e7.png  | Bin 0 -> 316937 bytes
 mockups/evidence/prophet-r7-wave-a/plan-cards/37cedc55f03b5ed3.png  | Bin 0 -> 260055 bytes
 mockups/evidence/prophet-r7-wave-a/plan-cards/4f5640c0b0e031bf.png  | Bin 0 -> 327044 bytes
 mockups/evidence/prophet-r7-wave-a/plan-cards/6070e6bafc5a7eb4.png  | Bin 0 -> 325059 bytes
 mockups/evidence/prophet-r7-wave-a/plan-cards/6a2fcb7bb6bd8e0f.png  | Bin 0 -> 335305 bytes
 mockups/evidence/prophet-r7-wave-a/plan-cards/747cdc65abcb09f1.png  | Bin 0 -> 257939 bytes
 mockups/evidence/prophet-r7-wave-a/plan-cards/829149f30ae707fb.png  | Bin 0 -> 262832 bytes
 mockups/evidence/prophet-r7-wave-a/plan-cards/EVIDENCE.yml          |   4 +
 mockups/evidence/prophet-r7-wave-a/plan-cards/NOTES.md              |  52 +++++++++++++
 mockups/evidence/prophet-r7-wave-a/plan-cards/manifest.json         | 308 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 mockups/evidence/prophet-r7-wave-a/plan-cards/source/component.html | 500 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 site/research_screener.html                                         |   2 +-
 25 files changed, 1292 insertions(+), 3 deletions(-)
```

### git diff --stat b48469a5 refs/pro/wa-a2-fix
```
 mockups/evidence/prophet-r7-wave-a/watchlist/1171ff1d9bc96ff3.png            | Bin 0 -> 233311 bytes
 mockups/evidence/prophet-r7-wave-a/watchlist/1e1f57bb00196f59.png            | Bin 0 -> 156792 bytes
 mockups/evidence/prophet-r7-wave-a/watchlist/2e9f5e22b092270b.png            | Bin 0 -> 239514 bytes
 mockups/evidence/prophet-r7-wave-a/watchlist/3586b8ddff3f01c0--row_hover.png | Bin 0 -> 247893 bytes
 mockups/evidence/prophet-r7-wave-a/watchlist/587f92a26826c2f1--row_hover.png | Bin 0 -> 240369 bytes
 mockups/evidence/prophet-r7-wave-a/watchlist/595baaa7f5b3bd79.png            | Bin 0 -> 251221 bytes
 mockups/evidence/prophet-r7-wave-a/watchlist/605af479795c866d--row_hover.png | Bin 0 -> 168329 bytes
 mockups/evidence/prophet-r7-wave-a/watchlist/68fb330907edf606--row_hover.png | Bin 0 -> 251839 bytes
 mockups/evidence/prophet-r7-wave-a/watchlist/6d0e1a063144895d.png            | Bin 0 -> 157845 bytes
 mockups/evidence/prophet-r7-wave-a/watchlist/6d1c24ae6c5bcb88.png            | Bin 0 -> 247170 bytes
 mockups/evidence/prophet-r7-wave-a/watchlist/72c6375513cde5d6--row_hover.png | Bin 0 -> 234337 bytes
 mockups/evidence/prophet-r7-wave-a/watchlist/867e41ce2f4a9f03--row_hover.png | Bin 0 -> 157276 bytes
 mockups/evidence/prophet-r7-wave-a/watchlist/9a97e667c87254f2--row_hover.png | Bin 0 -> 158495 bytes
 mockups/evidence/prophet-r7-wave-a/watchlist/EVIDENCE.yml                    |   8 ++
 mockups/evidence/prophet-r7-wave-a/watchlist/NOTES.md                        |  42 +++++++++++
 mockups/evidence/prophet-r7-wave-a/watchlist/f0ec93572dbce3fa--row_hover.png | Bin 0 -> 168404 bytes
 mockups/evidence/prophet-r7-wave-a/watchlist/f77f630f02b05796.png            | Bin 0 -> 167911 bytes
 mockups/evidence/prophet-r7-wave-a/watchlist/fe15535e9faed34c.png            | Bin 0 -> 167666 bytes
 mockups/evidence/prophet-r7-wave-a/watchlist/manifest.json                   | 458 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 site/research_screener.html                                                  |   2 +-
 site/watchstore.js                                                           | 127 ++++++++++++++++++++++++--------
 templates/watchlist.html.j2                                                  |   2 +-
 templates/watchstore.js                                                      | 127 ++++++++++++++++++++++++--------
 tests/test_prophet_r7_wave_a_watchlist.py                                    | 211 +++++++++++++++++++++++++++++++++++++++++++++++++++--
 24 files changed, 904 insertions(+), 73 deletions(-)
```

### git diff --stat 21a95484 refs/pro/wa-a3-fix
```
 mockups/evidence/prophet-r7-wave-a/receipts/0888fa0765148c99.png           | Bin 0 -> 275633 bytes
 mockups/evidence/prophet-r7-wave-a/receipts/139034bc0b89abf9.png           | Bin 0 -> 338684 bytes
 mockups/evidence/prophet-r7-wave-a/receipts/25c535d3ca7c52a6--rc-focus.png | Bin 0 -> 339068 bytes
 mockups/evidence/prophet-r7-wave-a/receipts/370c83bdad49e839.png           | Bin 0 -> 300850 bytes
 mockups/evidence/prophet-r7-wave-a/receipts/45ca7cf6b8a74666--rc-focus.png | Bin 0 -> 372560 bytes
 mockups/evidence/prophet-r7-wave-a/receipts/4885ca1439d84baa.png           | Bin 0 -> 376086 bytes
 mockups/evidence/prophet-r7-wave-a/receipts/525c61e6a8b3e2b1--rc-focus.png | Bin 0 -> 275854 bytes
 mockups/evidence/prophet-r7-wave-a/receipts/5edbf09a5904ffce--rc-focus.png | Bin 0 -> 342438 bytes
 mockups/evidence/prophet-r7-wave-a/receipts/6b5483e8bc7b2165--rc-focus.png | Bin 0 -> 275095 bytes
 mockups/evidence/prophet-r7-wave-a/receipts/7620cf97f5a98f03.png           | Bin 0 -> 300543 bytes
 mockups/evidence/prophet-r7-wave-a/receipts/78a41d8b58e2a93e--rc-focus.png | Bin 0 -> 376518 bytes
 mockups/evidence/prophet-r7-wave-a/receipts/878026be78c9ef0b--rc-focus.png | Bin 0 -> 301125 bytes
 mockups/evidence/prophet-r7-wave-a/receipts/EVIDENCE.yml                   |   4 ++
 mockups/evidence/prophet-r7-wave-a/receipts/NOTES.md                       |  50 +++++++++++++
 mockups/evidence/prophet-r7-wave-a/receipts/a11254cadefe43f7--rc-focus.png | Bin 0 -> 300806 bytes
 mockups/evidence/prophet-r7-wave-a/receipts/b627be6969947c88.png           | Bin 0 -> 274839 bytes
 mockups/evidence/prophet-r7-wave-a/receipts/dc54c4ecc4d45aea.png           | Bin 0 -> 372166 bytes
 mockups/evidence/prophet-r7-wave-a/receipts/f367309393dfd11b.png           | Bin 0 -> 342044 bytes
 mockups/evidence/prophet-r7-wave-a/receipts/manifest.json                  | 460 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 mockups/evidence/prophet-r7-wave-a/receipts/source/component.html          | 228 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 20 files changed, 742 insertions(+)
```

### git diff --stat 1f536032d446e2b51bda47f0575e371f0c4a0aae refs/pro/wa-a1-rehome (PR contribution over current main)
```
 .github/ci/legacy-jobs.yml                                          |   3 +
 mockups/evidence/prophet-p0b-zero-fouc/manifest.json                |   4 +-
 mockups/evidence/prophet-p0b-zero-fouc/mobile-layout-canada.json    |   2 +-
 mockups/evidence/prophet-p0b-zero-fouc/mobile-layout.json           |   2 +-
 mockups/evidence/prophet-r7-wave-a/macro/00b0f1016d24ba50.png       | Bin 0 -> 531407 bytes
 mockups/evidence/prophet-r7-wave-a/macro/26b9578526d401a1.png       | Bin 0 -> 766237 bytes
 mockups/evidence/prophet-r7-wave-a/macro/39a79232afba21a8.png       | Bin 0 -> 739494 bytes
 mockups/evidence/prophet-r7-wave-a/macro/46f61a38de1ccdc1.png       | Bin 0 -> 511108 bytes
 mockups/evidence/prophet-r7-wave-a/macro/EVIDENCE.yml               |   5 ++
 mockups/evidence/prophet-r7-wave-a/macro/NOTES.md                   |  29 ++++++++
 mockups/evidence/prophet-r7-wave-a/macro/a2600506123adaef.png       | Bin 0 -> 536987 bytes
 mockups/evidence/prophet-r7-wave-a/macro/b2a92d7ce1d35a8e.png       | Bin 0 -> 408067 bytes
 mockups/evidence/prophet-r7-wave-a/macro/d8d0b43ab4b6a0f1.png       | Bin 0 -> 536277 bytes
 mockups/evidence/prophet-r7-wave-a/macro/ef16cf2da9691f0e.png       | Bin 0 -> 400569 bytes
 mockups/evidence/prophet-r7-wave-a/macro/manifest.json              | 391 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 mockups/evidence/prophet-r7-wave-a/plan-cards/08ebf2dc738d8563.png  | Bin 0 -> 260448 bytes
 mockups/evidence/prophet-r7-wave-a/plan-cards/1d3fb4ffc3d4d6e7.png  | Bin 0 -> 316937 bytes
 mockups/evidence/prophet-r7-wave-a/plan-cards/37cedc55f03b5ed3.png  | Bin 0 -> 260055 bytes
 mockups/evidence/prophet-r7-wave-a/plan-cards/4f5640c0b0e031bf.png  | Bin 0 -> 327044 bytes
 mockups/evidence/prophet-r7-wave-a/plan-cards/6070e6bafc5a7eb4.png  | Bin 0 -> 325059 bytes
 mockups/evidence/prophet-r7-wave-a/plan-cards/6a2fcb7bb6bd8e0f.png  | Bin 0 -> 335305 bytes
 mockups/evidence/prophet-r7-wave-a/plan-cards/747cdc65abcb09f1.png  | Bin 0 -> 257939 bytes
 mockups/evidence/prophet-r7-wave-a/plan-cards/829149f30ae707fb.png  | Bin 0 -> 262832 bytes
 mockups/evidence/prophet-r7-wave-a/plan-cards/EVIDENCE.yml          |   4 +
 mockups/evidence/prophet-r7-wave-a/plan-cards/NOTES.md              |  52 +++++++++++++
 mockups/evidence/prophet-r7-wave-a/plan-cards/manifest.json         | 308 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 mockups/evidence/prophet-r7-wave-a/plan-cards/source/component.html | 500 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 site/research_screener.html                                         |   2 +-
 site/theme.css                                                      |  10 +++
 templates/_us_prophet_plan_cards.html.j2                            |  20 +++++
 templates/theme.css                                                 |  10 +++
 tests/test_prophet_r7_wave_a_plan_cards.py                          | 389 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 32 files changed, 1726 insertions(+), 5 deletions(-)
```

### git diff --stat 1f536032d446e2b51bda47f0575e371f0c4a0aae refs/pro/wa-a2-rehome (PR contribution over current main)
```
 .github/ci/legacy-jobs.yml                                                   |   6 +
 mockups/evidence/prophet-r7-wave-a/watchlist/1171ff1d9bc96ff3.png            | Bin 0 -> 233311 bytes
 mockups/evidence/prophet-r7-wave-a/watchlist/1e1f57bb00196f59.png            | Bin 0 -> 156792 bytes
 mockups/evidence/prophet-r7-wave-a/watchlist/2e9f5e22b092270b.png            | Bin 0 -> 239514 bytes
 mockups/evidence/prophet-r7-wave-a/watchlist/3586b8ddff3f01c0--row_hover.png | Bin 0 -> 247893 bytes
 mockups/evidence/prophet-r7-wave-a/watchlist/587f92a26826c2f1--row_hover.png | Bin 0 -> 240369 bytes
 mockups/evidence/prophet-r7-wave-a/watchlist/595baaa7f5b3bd79.png            | Bin 0 -> 251221 bytes
 mockups/evidence/prophet-r7-wave-a/watchlist/605af479795c866d--row_hover.png | Bin 0 -> 168329 bytes
 mockups/evidence/prophet-r7-wave-a/watchlist/68fb330907edf606--row_hover.png | Bin 0 -> 251839 bytes
 mockups/evidence/prophet-r7-wave-a/watchlist/6d0e1a063144895d.png            | Bin 0 -> 157845 bytes
 mockups/evidence/prophet-r7-wave-a/watchlist/6d1c24ae6c5bcb88.png            | Bin 0 -> 247170 bytes
 mockups/evidence/prophet-r7-wave-a/watchlist/72c6375513cde5d6--row_hover.png | Bin 0 -> 234337 bytes
 mockups/evidence/prophet-r7-wave-a/watchlist/867e41ce2f4a9f03--row_hover.png | Bin 0 -> 157276 bytes
 mockups/evidence/prophet-r7-wave-a/watchlist/9a97e667c87254f2--row_hover.png | Bin 0 -> 158495 bytes
 mockups/evidence/prophet-r7-wave-a/watchlist/EVIDENCE.yml                    |   8 +
 mockups/evidence/prophet-r7-wave-a/watchlist/NOTES.md                        |  42 +++++
 mockups/evidence/prophet-r7-wave-a/watchlist/f0ec93572dbce3fa--row_hover.png | Bin 0 -> 168404 bytes
 mockups/evidence/prophet-r7-wave-a/watchlist/f77f630f02b05796.png            | Bin 0 -> 167911 bytes
 mockups/evidence/prophet-r7-wave-a/watchlist/fe15535e9faed34c.png            | Bin 0 -> 167666 bytes
 mockups/evidence/prophet-r7-wave-a/watchlist/manifest.json                   | 458 ++++++++++++++++++++++++++++++++++++++++++++++++++++++
 site/research_screener.html                                                  |   2 +-
 site/watchlist.js                                                            | 154 ++++++++++++++++++-
 site/watchstore.js                                                           | 291 ++++++++++++++++++++++++++++++++++-
 templates/watchlist.html.j2                                                  |  37 ++++-
 templates/watchlist.js                                                       | 154 ++++++++++++++++++-
 templates/watchstore.js                                                      | 291 ++++++++++++++++++++++++++++++++++-
 tests/test_prophet_r7_wave_a_watchlist.py                                    | 971 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 27 files changed, 2402 insertions(+), 12 deletions(-)
```

## Evidence files
- acceptance logs: $S/acc/n2_{a1,a2,a3}.log and $S/acc/n2_{a1,a2,a3}/ (design/ui diffs and outputs, test outputs, probe rows)
- commit messages: $S/msg_a{1,2,3}.txt, $S/msg_a{1,2}_rehome.txt; ref list: $S/final_fix_refs.txt
- p0b remint logs: $S/p0b_verify_hk_stocks.log, $S/p0b_verify_canada_stocks.log
- $S = /private/tmp/claude-501/-Volumes-Mastermind-2-agent-workspaces-claude-14851c4656838a3b-prophet-end-to-end-dbeaec-7e88fffefdd61737/69eb9a1c-622e-4c17-a57d-b9e3868109b1/scratchpad
