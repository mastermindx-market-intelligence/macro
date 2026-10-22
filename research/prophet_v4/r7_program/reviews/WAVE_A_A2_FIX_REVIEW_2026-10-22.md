# Wave A A2 fix re-review (#9956) + A1 receipt remint (#9954)
A2 head: ce64b9795c40 (refs/pro/wa-a2-rehome; parents 3f406fc8 wa-a2-fix, 1f536032 main). Prior head attacked: b48469a5.
A1 head: 7fa87f9bf424 (refs/pro/wa-a1-rehome; parents d4219e7f, 1f536032).
Reviewer: native Opus, ROUTE: review, MODE: READ_ONLY. Export: scratchpad/a2rev/tree (git archive of ce64b979). Probes: scratchpad/a2rev/probe/probe_fix.py (outside the tree).

STATUS: FAIL (A2) / PASS (A1 remint)
- A2 = FAIL. The save semantics now PASS: findings 1, 2 and 4 are FIXED and proven by probes and tests. Two gates are still open. (a) The finding-3 repair introduced a new CSS defect: it references an undefined token with no fallback. (b) The committed dual-theme receipts never show the surfaces this PR changed. Both repairs are small.
- A1 remint = PASS. The re-pin is faithful and touches nothing else.

## Blocking / gate-holding findings (A2)
N1. MINOR, REGRESSION from the F3 repair. templates/watchlist.html.j2:116 reads `border-radius:var(--r-card);`, with no fallback. `--r-card` is not defined at :root on any stylesheet the watchlist page loads. `grep -E -- '--r-card\s*:'` over site/{shared_shell,theme,tier_preview,portfolio_import,product-nav-icons,navigation-refresh}.css, assets/css/29cecf26.css and site/watchlist.html matches only a COMMENT at theme.css:2109, which says "--r-ctl/--r-card are DS-PR-0 scales not yet landed at :root". Every other consumer writes `var(--r-card,12px)` (commodity-workspace.css:27, sector_central.html.j2:452, _prophet_card.html.j2:579). An undefined var() is invalid at computed-value time, so the radius falls back to its initial value of 0. `.ws-save-live/.ws-save-alert` would therefore render square, where b48469a5 rendered them at 10px. The ratchet passes only because it checks literals. Repair: `var(--r-card,12px)`.
N2. GATE (dual-theme evidence does not cover the change). mockups/evidence/prophet-r7-wave-a/watchlist has 16 cells: 8 rest + 8 row_hover, desktop 1440 and mobile 390, en/zh, light/dark. All are anonymous, and check_ui_visual_evidence rc=0. I inspected 1171ff1d9bc96ff3.png (light/en/desktop) and 595baaa7f5b3bd79.png (dark/zh/desktop). Both show the default **Portfolio** tab with an empty holdings table. Neither shows the Watchlists table, where the new "When you saved" / "Tonight" columns and footnote live, or the save live regions. The hover cells target `.hold tbody tr`, the empty positions row (NOTES.md says so). So the receipts pass the checker, but they cannot support a dark-vs-light or EN/ZH adjudication of A2's new UI. Under the review standard that is not PASS. Repair: capture the Watchlists-mode cells in the same 8-cell matrix. The anonymous starter list exists ("Watchlists 1" chip).

## Findings 1-7 of the FAIL review
1. FIXED (was MAJOR, blocking).
   - watchstore.js:929-943: `_isRefusalErr` now returns false for Error instances, for status 0/408/>=500, and for messages matching `/failed to fetch|networkerror|network request failed|load failed|timed? ?out/i`. It returns refusal only for 4xx or a non-empty string `code`.
   - New `_checkedInsert` (watchstore.js:955-983) copies `res.status` onto the thrown error. The gate stays `!stage.ok && _isRefusalErr(stage.err) && !wroteAnything` (:1116). Everything else goes to the read-back (:1120).
   - Probe output (python3 probe_fix.py <tree>, rc=0):
     - `P1-orig(no status, lands) state=saved reads=2`
     - `P1-v2shape(status0, lands) state=saved reads=2`
     - `P1-safari(status0, nothing) uncertain`
     - `P1-undici(status0) uncertain`
     - `P1-503(lands) saved`
     - `P1-504 PGRST000(nothing) uncertain`
     - `P1-v0shape(status400 'FetchError: Failed to fetch', lands) saved`
     - `REF-403 42501(nothing) rejected reads=1`
   - Residual NITs:
     - `{message:'TypeError: fetch failed', code:'UND_ERR_SOCKET'}` with no status gives `rejected`. The message is Node/undici wording and does not occur in a browser, where postgrest-js sets status 0.
     - A 4xx is trusted with no read-back. A probe with status 499 and the row landed gave `rejected reads=1 rowsOnServer=1`. That needs a proxy that returns 499 to the client, which is theoretical. The prior review's "read back before every rejected after an attempted insert" would close the class.
2. FIXED. In site/research_screener.html, the A2-attributable diff against main 1f536032 is exactly `watchstore.js?v=3812c6a9` -> `?v=dd730491`. `shasum -a 256 site/watchstore.js` = dd730491…, the same sha8 rule A1's theme stamp uses. `pytest tests/test_research_screener.py -k "fresh_bake or stamped"`: 2 passed. NOTE: A1 and A2 each edit a different stamp in this one file. Whichever lands second must re-bake on top of the first.
3. PARTIAL. The literal is gone (`--mode enforce-added` on diff main..ce64b979: "blocking=0", rc=0), but the repair regressed rendering. See N1.
4. FIXED. `_checkedInsert` never calls `_syncMarkInsertFailed`. The outbox marker is set only at :839 in `_symbolInsert`, which saveChecked no longer uses (:1099). Probe P2 (the insert REJECTS late with TypeError after a 40ms deadline and the row lands, then `online` and `WS.pull()`): `state=uncertain attempts=1 markerMentionsPendingVRT=false vrtRows=1`. The old result was attempts 2, vrtRows 2.
5. PARTIAL.
   - FIXED: `already` tickers get no snapshot. `mine = confirmed.filter(attempted)` (:1129).
   - FIXED: `decisionsKept: kept > 0` (:1135). `_saveSnapshots` now returns the count it stored, and 0 on a setItem failure.
   - NOT FIXED: the snapshot day is still the browser-local date, `now.getFullYear()…getDate()` at watchstore.js:1014, not ET.
6. NOT FIXED (disclosure only). There is still no caller of `saveChecked`: grep finds only the definition/export at :2425 and comments. "Saving doesn't create a plan or a position." appears 0 times in watchlist.js and watchlist.html.j2. Check again / Choose another list are not rendered. The cached-then-deleted list case is still unchanged. The feature stays dormant. It is acceptable only if the PR body says so.
7. NOT FIXED (nit).
   - watchlist.js:913 still has `hour12: false`.
   - `_checkedInsert` still calls `setPill('synced')` on a late success (:979).
   - `listCount: (rows || []).length` still counts raw rows (:1134).

## Other checks
- Tests on the export: `pytest tests/test_prophet_r7_wave_a_watchlist.py -q -rs`: 22 passed, 1 skipped. The skip is the documented no-staleness-flag GAP at :904. The suite now includes the P1/P1b/P2 and snapshot regressions (:588-719).
- Template/site parity: site/watchstore.js equals templates/watchstore.js, and site/watchlist.js equals templates/watchlist.js (`cmp`, rc 0).
- `symbolInspect` (+73 lines) arrives from main 1f536032 through the merge. It is not A2 work: wa-a2-fix has 0 occurrences and main has 2.
- CI: in legacy-jobs.yml, the `washout-turn-organ` paths (lines 27972-27999) declare templates/watchlist.js, watchstore.js, watchlist.html.j2 and the test. The step is at :28124. That is the test's whole load closure.
- No colored edge: the only A2 template CSS change is the radius line. The earlier added CSS uses even 1px neutral borders.

## A1 remint (7fa87f9bf424) - PASS
- Against main 1f536032 the remint touches only mockups/evidence/prophet-p0b-zero-fouc/{manifest.json, mobile-layout.json, mobile-layout-canada.json}.
- In each layout JSON the only change is `"site/theme.css": 2e861147… -> a922b22c08ca57ef81a6352e56a1cef18e1173cbb7029c685035f5d7e3a8a11a`.
  - 2e861147… = sha256 of main's site/theme.css.
  - a922b22c… = sha256 of the A1 head's site/theme.css (and templates/theme.css).
- manifest.json re-pins the receipts to their blob sha256:
  - hk mobile-layout.json -> b8349824849fa8aeda2ed35e483df1a0e6e55a08ad86784b8da6ff540f512e51
  - ca mobile-layout-canada.json -> bbc6f54d26f36acdbb8daa84ba67095e54c292b5b81b03d6a52851e098e9b7ce
  - Both match `git show refs/pro/wa-a1-rehome:<file> | shasum -a 256`.
- Screener: the A1 diff is `theme.css?v=2e861147` -> `?v=a922b22c`, which equals the sha8 of the A1 theme.css.
- Plan-cards content: `git diff --numstat d4219e7f 7fa87f9b` over templates/_us_prophet_plan_cards.html.j2, templates/theme.css, site/theme.css, tests/test_prophet_r7_wave_a_plan_cards.py and mockups/evidence/prophet-r7-wave-a/plan-cards returns 0 lines. The content is unchanged from the reviewed A1 head.
- Not re-run: the layout measurements themselves were not re-measured. This is a hash re-pin, not a re-capture.

## GAPS
- No browser. The radius regression (N1) comes from reading the cascade, not from a render. Only 2 of the 16 watchlist cells were inspected visually.
- The A1 p0b layout receipts were re-pinned, not re-measured. I did not check whether A1's 10-line theme.css change moves any p0b mobile layout metric.
- The full washout-turn-organ CI job and test_ci_pack were not run. postgrest-js shapes are modelled from library knowledge, with no network.

## DEVIATIONS
- None to the artifact or the seat worktree. Git read commands only. Probes and diffs live in scratchpad/a2rev/.
