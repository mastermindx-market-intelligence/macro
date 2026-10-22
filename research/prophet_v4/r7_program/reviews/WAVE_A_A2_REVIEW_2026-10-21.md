# Wave A A2 adversarial review: watchlist checked save + "When you saved" / "Tonight"
PR: 9956
Head: b48469a57949dfffc1d152a50077d4dff1a88471
Base: 35321d4c07e6e6e321269a01d34339f5d18d4c7e
STATUS: FAIL

Reviewer: native Opus, ROUTE: review, MODE: READ_ONLY. TREE = scratchpad/a2_tree (PR head export). Line numbers below are TREE/templates/*.

## Surface 1: save semantics (saveChecked), BLOCKING
- (a) PASS. `saved` is built only inside the read-back `.then` (watchstore.js ~987-1006): `var confirmed = want.filter(function (t) { return !!onList[t]; }); if (confirmed.length !== want.length) return uncertain(); _saveSnapshots(...); return { state: 'saved', readBackAt: nowISO(), ... }`. Mutation (i) was caught (Surface 6).
- (b) PASS. Check first: `var already = want.filter(function (t) { return !!present[t]; }); var missing = want.filter(function (t) { return !present[t]; });`, and only `missing` reaches `symbolAdd`. The test's second save writes nothing.
- (c) PASS for signed-out and bad-args: `if (!user || !sb) { return Promise.resolve({ state: 'rejected', reason: 'no-session', ...}).then(_finish); }` and `if (!listId || !want.length) {... 'bad-args' ...}` both return before any network call. `no-list` returns `rejected('no-list')` before any symbols read or write.
- (c') BLOCKING (major). A transport loss is reported as `rejected` with "Nothing was added anywhere." and no read-back. `_isRefusalErr` treats any plain object with a non-empty `message` as "the account answered no": `!(err instanceof Error) && ((err.message != null && err.message !== '') || err.code != null)`. The code comment says fetch failures are `Error` instances. That assumption is false for postgrest-js (supabase-js v2). PostgrestBuilder catches a fetch rejection and resolves `{error:{message:'TypeError: Failed to fetch', details, hint:'', code:''}, status:0}`. A gateway 502/503/504 body also arrives as a plain error object. `_symbolInsert` rethrows `res.error` unchanged, and `!wroteAnything` is true for the first ticker, so `rejected(...)` is returned with no read-back. Probe P1 (throwaway copy): the insert commits the row server-side and then returns `{error:{message:'TypeError: Failed to fetch', code:''}}`. Result: `{"state": "rejected", "reason": "TypeError: Failed to fetch", "rowsOnServer": 1}`. The page then states "Not saved / Nothing was added anywhere." while the account holds the row. This breaks "no outcome is claimed without a read-back" and "a save reports what the account actually holds". Repair: classify `status===0`, a FetchError/TypeError message and 5xx as ambiguous, and send them to the read-back. Better still, read back before every `rejected` that follows an attempted insert.
- (d) PASS for the module itself. The deadline path returns `uncertain()` and schedules no timer: `_withDeadline` cancels its timer on settle. The test records `attempts == 1`.
- (d') minor, latent. If the insert promise REJECTS (not resolves-with-error) after the deadline, `_symbolInsert`'s rejection handler runs `_syncMarkInsertFailed(listId, t)`. The existing outbox (`_retryOutboxBeforePull`, watchstore.js 1161-1200, triggered by `window 'online'` at 2497-2505 and at the start of `pull()` at 1039) then re-inserts it on its own, using the cached membership. Probe P2 with a rejecting late-landing insert, then `online`: `{"state": "uncertain", "attempts": 2, "vrtRows": 2}`. That is a duplicate row after the UI promised "nothing is saved twice". With the resolve-with-error variant (the normal postgrest-js shape) P2 gave `attempts 1, vrtRows 1`, because the `then(onOk, onErr)` shape in `_symbolInsert` does not catch the rethrow from `onOk`. So this is reachable only if the SDK is configured to throw or the fetch wrapper rejects. Record it, and guard it: saveChecked should not leave pendingInserts markers, or the outbox should read back before inserting.
- (e) PASS. A late insert resolution cannot change the returned or dispatched outcome, because `_finish` runs once on the raced chain. A snapshot is written only in the read-back branch. A late success does call `setPill('synced')` (watchstore.js `_symbolInsert`), so the chip can say synced beside an `uncertain` live region. That is a nit-level inconsistency.
- (f) NOTE. `saveChain[listId]` serializes saves per list (`var run = prev.then(_doSaveChecked, _doSaveChecked)`). After a deadline, though, the chain moves on while the first insert is still in flight, so a user re-save's pre-read can miss it and insert a duplicate. This is the same exposure as the existing `symbolAdd` (no unique (watchlist_id, symbol) index). It is not worse than the store, but the "nothing is saved twice" copy overclaims in that window.

## Surface 2: snapshot, PASS with notes
- Confirmed-only: `_saveSnapshots(listId, confirmed, o.decisions)` is called only after `confirmed.length === want.length`.
- Frozen: `if (perList[t]) return; // frozen history`. Mutation (ii) was caught.
- Storage guarded: the getItem+JSON.parse pair is in try/catch (`catch (e) { snap = {}; }`), then `if (!snap || typeof snap !== 'object') snap = {};`, and setItem is in try/catch. Reader `saveSnapOf` (watchlist.js) wraps getItem+parse in try/catch and type-checks perList/entry. The test `test_snapshot_storage_failures_never_crash_the_save` passes.
- NOTE (minor): a snapshot is also written for `already` tickers (confirmed includes them). A name saved weeks ago, before this feature, gets TODAY's date and decision as "When you saved". That is false history. Restrict snapshots to tickers this save actually wrote, or label them differently.
- NOTE (minor): `day` is the browser-local date (`now.getFullYear()/getMonth()/getDate()`), not ET. `decisionsKept: !!o.decisions` is true for `{}` or when every entry was skipped, so the "decisions kept" clause can be printed when nothing was kept.

## Surface 3: painter and copy, PASS with notes
- These are byte-for-byte equal to R7-21: Saved EN "Read back from your account at HH:MM ET. X, Y and Z are in the list with tonight’s decisions kept as they stand.", Saved ZH "HH:MM（美东）从您的账户读回。X、Y 和 Z 已在列表中，今晚的决策按原样保留。", Waiting EN/ZH, Uncertain EN/ZH + "Asked at HH:MM ET" / "请求于 HH:MM（美东）", Rejected "Not saved"/"未保存", deleted-list sentence EN/ZH, and "Nothing was added anywhere."/"没有添加到任何列表。". The `already` line reuses R7-20 "N names, TK is already in it" / "N 只，TK 已在其中".
- The decisions clause is gated on `d.decisionsKept`. See Surface 2 for why that flag is loose.
- ET: `Intl.DateTimeFormat('en-US', {timeZone:'America/New_York', hour:'2-digit', minute:'2-digit', hour12:false})`. Nit: `hour12:false` can render midnight as "24:xx" in some engines. Prefer `hourCycle:'h23'`.
- Escaping: every interpolation goes through `te(esc(..), esc(..))` or `soP` (`'<p>' + te(esc(en), esc(zh)) + '</p>'`), and that includes list names and tickers. `savedCell` escapes `s.en`/`s.zh`.
- `#ws_save_alert` is written only in the `rejected` branch. The other branches clear it.
- returnFocus: `if (d.returnFocus && d.returnFocus.focus) { try { d.returnFocus.focus(); } catch (e) {} }` cannot throw.
- minor: the spec's R7-19/R7-21 disclaimer "Saving doesn’t create a plan or a position." / "保存不会创建计划或仓位。" is not painted anywhere, and neither are the R7-21 controls (Check again / Choose another list / Done). No call site of `saveChecked` exists in templates/site (grep finds only the definition and the painter comment), so the save flow is dormant until a sheet slice wires it in. State that in the PR. Otherwise "When you saved" will read "Not supplied" for every row in production.
- minor: the deleted-list scene (`reason 'no-list'`) fires only when the list is ABSENT from listsCache. `ensureList` returns true without asking whenever the id is cached. In the realistic case (cached list deleted on another device) the insert fails on FK/RLS, and the user sees a generic "Not saved" with no list sentence. Also, for an uncached unknown id, `listName` falls back to the raw id: `listNameOf(listId) || String(listId || '')`.

## Surface 4: columns, see appended evidence
## Surface 5: doctrine and wording, see appended evidence
## Surface 6: test realism, PASS
- Mutation (i), "saved" without the read-back: 4 failed, 12 passed, 1 skipped. Failing assertions: `AssertionError: [('select', 0), ('insert', 1)]` (expected `... ('select', 2)]`, "Right contains one more item: ('select', 2)") and `AssertionError: assert 'saved' == 'uncertain'` (×2), plus `KeyError: 'L1'`. Failing tests: test_savechecked_saved_requires_a_read_back_after_the_insert, test_savechecked_deadline_is_uncertain_and_never_retries_itself, test_snapshot_written_only_for_confirmed_and_never_overwritten, test_snapshot_is_not_written_when_the_save_cannot_confirm.
- Mutation (ii), overwrite an existing snapshot: 1 failed, 15 passed, 1 skipped. Failing assertion: `AssertionError: assert 'CHANGED' == 'Not there yet, get ready'` in test_snapshot_written_only_for_confirmed_and_never_overwritten.
- Gap in the suite: nothing models a postgrest-shaped transport error (P1) or a pendingInserts-marker → outbox retry (P2). Both defects pass the suite.
## Surface 7: CI registration, see appended evidence
## Surface 8: custody, see appended evidence

## CI facts supplied by the coordinator (classified)
- Design ratchet flags `templates/watchlist.html.j2:116 border-radius:10px` (radius-literal) as a new forbidden decision. Classification: minor defect, CI-blocking. The new `.ws-save-live/.ws-save-alert` rule mints a literal radius instead of the shared radius token. Repair by using the existing radius custom property. This is not a design-doctrine edge/stripe violation.
- research-screener fresh-bake test fails on the PR tree. `site/research_screener.html` stamps watchstore.js/theme.css by content hash, so changing site/watchstore.js changes the stamp. Classification: major, CI-blocking custody gap. The PR is missing a required paired derived site artifact (the re-baked `site/research_screener.html`). This also means the commission's "exactly seven files" expectation cannot hold. A correct PR needs an eighth, derived file, regenerated by the canonical builder rather than hand-edited.

## Commanded runs (TREE, PYTHONPATH=TREE, python3 -W ignore, perl alarm 600)
- 7-file watchlist set: `250 passed, 4 skipped in 25.14s`, EXIT=0. Skips: test_prophet_r7_wave_a_watchlist.py:707 "GAP: no per-row quote staleness flag exists ..."; test_watchlist_drawer_js.py:1045 "origin/main not fetched in this checkout"; :1119 and :1139 "site/stockdata/ nightly artifacts not present in this checkout". The builder's "five pre-existing failures" did NOT reproduce here (0 failures). No failure to attribute to base vs PR.
- New file alone: `16 passed, 1 skipped in 2.84s`, EXIT=0.
- `tests/test_ci_pack.py -k "exclusive or washout or narrow"`: `7 passed, 197 deselected in 225.25s (0:03:45)`, EXIT=0.
- `node --check templates/watchstore.js && node --check templates/watchlist.js`: exit 0 (node v26.5.0).

## Findings
1. MAJOR (blocking): transport/gateway error misclassified as account refusal → `rejected` + "Nothing was added anywhere." with no read-back. watchstore.js `_isRefusalErr` and the `!stage.ok && _isRefusalErr(stage.err) && !wroteAnything` branch, plus the outer `.then(_finish, ...)` refusal branch. Probe P1.
2. MAJOR (CI-blocking): missing paired derived artifact `site/research_screener.html` (content-hash stamp of watchstore.js). Fresh-bake test red.
3. MINOR (CI-blocking): radius literal `border-radius:10px` at watchlist.html.j2:116. Design ratchet red.
4. MINOR (latent): a rejecting late insert leaves a pendingInserts marker, and the existing outbox re-inserts it on its own (`online`/`pull`), producing a duplicate row after "uncertain". Probe P2 (`attempts 2, vrtRows 2`).
5. MINOR: snapshot written for `already` tickers with today's date and decision (false "When you saved" history). Snapshot date is local, not ET. `decisionsKept` is true for any truthy `decisions`.
6. MINOR: dormant feature. No caller of `saveChecked`. Disclaimer, "Check again" and "Choose another list" are not rendered. The deleted-list sentence is unreachable for a cached-then-deleted list.
7. NIT: `hour12:false` midnight "24:xx". The chip can show synced beside an uncertain outcome after a late landing. `listCount` counts raw (possibly duplicate) rows.

## Appended evidence (surfaces 4, 5, 7, 8)

### Surface 4: columns, PASS with note
- Gate: `WL_HEAD` (watchlist.js:1078) is used only by the Watchlists renderer: `var host = el('tbl_wl')` (1259) → `host.innerHTML = WL_HEAD + '<tbody>' + rows.map(wlRowHTML).join('') + '</tbody>' + WL_FOOT;` (1272). Portfolio renders `tbl_pf` through its own head (1700). The new cells exist only in `wlRowHTML`.
- Column count: WL_HEAD has `th('sym' th('px' th('signal' th('flags' th('evt' th('sector' th('wsv' th('ton' th('chg'` + `<th></th>` = 10. `WL_FOOT colspan="10"` and `drawerHTML(r, 10)` are consistent (base: 8 = 7 th + 1). The new th's are `sortable=false`, and existing sort keys are untouched.
- Tonight: `function tonightCell(r) { if (!r.st) return '<span class="mut ton-na">' + te('Unavailable', '暂不可用') + '</span>'; return stageCell(stageOf(r.st)); }`. Unavailable carries no `stg`/`s-*` class and no `<i>` glyph. An unmapped state falls to `stageOf → 'none'` → the existing `s-none` (dotted ring) vocabulary, not a buy class. No new state words.
- Hold-mode hiding: `.hold .c-day, .hold .c-since, .hold .c-rc, .hold .c-sect, .hold .c-wsv, .hold .c-ton { display:none; }` sits inside the narrow media block. NOTE (minor): the pair is therefore INVISIBLE at mobile width, while R7-19 is drawn only at 1440. Whether that is acceptable is a design question for the seat. I did not verify in a browser how `tfoot` renders inside the narrow grid row layout (UNVERIFIED).

### Surface 5: doctrine and wording, PASS (CSS literal noted)
- `git diff base..head -- templates/ | grep -E "^\+.*(border-left|border-inline-start|inset|border-right|box-shadow)"` returned no lines. The added borders are even 1px neutral: `border:1px solid var(--line-quiet, var(--line))` and `border-top:1px solid var(--line-quiet, var(--line))` on the footnote.
- `grep -iE "^\+.*(risk|position|holding|P&L|仓位|持仓|pnl)"` over the added template lines returned no lines.
- `templates/watchlist_risk.js` diff is 0 lines (unchanged).
- OQ9: no added heading carries a dash separator. My ZH `——` grep errored on ugrep regex syntax ("invalid syntax"). Manual reading of the added copy shows no em-dash heading, so this is N/A.
- OQ8 fix present: `.wri-lrow .st.watch { color:var(--ink-warn, var(--warn)); }`.
- Radius literal at watchlist.html.j2:116: see the CI facts above (minor, CI-blocking).
- Focus outlines: no outline rule is added or removed. Live regions are non-focusable.
- Dual theme: UNVERIFIED. No dark/light browser evidence matrix was supplied for this UI change, and the new surfaces (`.ws-save-live/.ws-save-alert` on `var(--panel)`, `.c-wsv`, `.wl-night-foot`) use only theme tokens. Per the review standard, missing dual-theme evidence cannot be PASS.

### Surface 7: CI registration, PASS with note
- Manifest hunk: job `washout-turn-organ` (legacy-jobs.yml:26210, `gate: code`). Added paths are `"templates/watchlist.js"`, `"templates/watchstore.js"`, `"templates/watchlist.html.j2"` and `"tests/test_prophet_r7_wave_a_watchlist.py"`. The added step is `- name: Prophet R7 Wave A watchlist save outcomes and saved/tonight columns (A2)` / `run: python -m pytest tests/test_prophet_r7_wave_a_watchlist.py -q`.
- The test's declared load closure (watchstore.js, watchlist.js, watchlist.html.j2) is fully declared.
- Node: the job uses `runs-on: ubuntu-latest` + `actions/setup-python@v5` with no setup-node. GitHub's ubuntu-latest image ships node on PATH, so `HAS_NODE` should be true and the test should run, not skip. NOTE: it is unproven until the CI log shows "16 passed".
- `tests/test_ci_pack.py -k "exclusive or washout or narrow"`: 7 passed.

### Surface 8: custody, NOTE (eighth derived file owed)
- `git diff --stat`: exactly the 7 expected files (.github/ci/legacy-jobs.yml +6, site/watchlist.js 154, site/watchstore.js 228, templates/watchlist.html.j2 37, templates/watchlist.js 154, templates/watchstore.js 228, tests/test_prophet_r7_wave_a_watchlist.py +774; 7 files changed, 1570 insertions(+), 11 deletions(-)).
- `cmp templates/watchlist.js site/watchlist.js` → identical. `cmp templates/watchstore.js site/watchstore.js` → identical.
- `python3 -m scripts.check_template_site_sync`: "DIVERGED: site/theme.js != templates/theme.js" with "theme.js bake unavailable (No module named 'rjsmin')"; "1 of 134 pairs diverged". This is an environment NOTE (missing rjsmin). It is not a PR finding.
- Nothing in the nav family, `engine/` or `.github/workflows/` is touched.
- Owed: the re-baked `site/research_screener.html` (hash stamp), per CI fact 2. Without it the PR stays red.

## EVIDENCE
- Report: this file. Mutation logs: scratchpad/a2_mut_i.txt, scratchpad/a2_mut_ii.txt. Probe source: scratchpad/a2_probe/test_probe_a2.py (copied into the throwaway a2_mut/tests only). Run logs: scratchpad/a2_run1.txt, a2_run_new.txt, a2_run_ci.txt.

## GAPS
- No browser render, so dark/light and EN/ZH visual adjudication is UNVERIFIED. Mobile tfoot-in-grid behavior is UNVERIFIED.
- postgrest-js error shape is cited from library knowledge (no vendored copy found offline, no network permitted). P1 models that shape.
- CI facts 2 and 3 are taken from the coordinator, not re-run here.

## DEVIATIONS
- Added two probes (P1/P2) to the throwaway a2_mut copy beyond the two commanded mutations. TREE, the worktree and the reviewed files were untouched. No git writes.
