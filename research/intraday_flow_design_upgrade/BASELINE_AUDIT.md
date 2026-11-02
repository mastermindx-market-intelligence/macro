# Intraday Flow — baseline audit adjudication

## Identity and disposition

- Original paid Fabric run: `intraday-design-contract-audit-20261101-c2`.
- Root/parent operation: `intraday-flow-design-upgrade-20261101-c2`.
- Returned response SHA-256: `4ebc7c01bb72237113af19b251edeee605e9aa3c1b1e438dce158c75ea08f928`.
- Scope: read-only contracts at the original `f754bdee6b803b18191841863c35527c0a74571e` baseline / initial plan commit. This is not a review of the final implementation.
- Fabric acceptance: recorded by the parent after manual result review on 2026-11-02; exact response digest above.
- Disposition: consumed as a bounded baseline inventory, with the corrections below. No final code, visual, Paper, production or trading acceptance is conferred.

## Accepted and applied

The DOM/test inventory, separate model/presentation boundary and page-only rendering path were useful. The implementation preserves 15 classifier/coverage/session/leg regions byte-for-byte and runs the full Intraday regression suite. The refresh-focus problem is repaired and exercised in the actual browser paths. Core classifier, null-safety and call-only premium assertions remain intact; retired layout assertions were deliberately migrated.

The audit identifies existing off-hours pulse timing, uncounted degraded rows, and thin nightly dealer evidence as limitations. These remain review considerations. The redesign makes recorded status, current input availability and source timestamps visible, while the separate #6867 timing/precursor work and producer semantics remain unchanged. A leader's nightly `built` date is not automatically the timestamp of a classification combining other observations; it must not be relabeled that way.

## Corrections and limits

1. The statement that `site/live/flow_pulse.json` is not committed is false for this branch. At proof head `9e2967ad2bc5ca4fcaacd913441d9e327c0d121a`, `git rev-parse HEAD:site/live/flow_pulse.json` returns blob `3f42612f2b724fe33793f8f7fa045d8ad745a181`. The base, quotes and overlay files checked are also tracked. The similarly named `intraday_quotes.json` is a different path and was not used to establish this correction.
2. The report's final drift paragraph references an inconsistent base (`3c3f3190`). Our read-only comparison from the actual initial base to fetched main `75c68c5f4141b4f82674ec503b69f0b8de2a718b` shows no change in the Intraday template/page/tests, builder, shared navigation/theme, `lib/pages.py`, or product-experience configuration. No rebase was performed. Future release still needs a fresh overlap check.
3. The worker's remote-branch equality to the initial plan commit is an earlier observation; the pushed branch advanced during implementation. It is not the current review identity.
4. "All other inline JS is presentation" is too broad. Transport, source clocks, availability and coverage remain protected integration contracts even when outside the listed classifier functions.
5. The old page had externalized inline CSS. This redesign uses an explicit page-scoped stylesheet with byte-identical template/site copies and a rendered link. Actual captures observe no failed responses. Normal paired-file/render sweeps and CI still apply; the old hashed asset is not evidence that the new page is styled incorrectly.
6. The audit did not run pytest or inspect Paper. Its closed-market timing example is a synthetic execution of baseline logic, not observed live production evidence.

## Recorded result

The report below is preserved verbatim to distinguish the worker's findings from the adjudication. The final exact-head reviewer must independently inspect the implemented code and visual proof.

---

Audit complete, read-only, within the ≤9000-byte limit (8985 bytes). Findings below.

# Intraday Flow UI — read-only integration audit

SHAs: macro base `f754bdee6b803b18191841863c35527c0a74571e` (parent of plan commit); plan `7e2d20094fde64ecc8e2e7fae1c7a0fe0a77b265` == remote `refs/heads/claude/intraday-flow-design-upgrade-20261101-c2` · template blob `8832ceba22068eccc65704f7bf6d7bbe027a9e45` · builder blob `bac284439a72d901a5b7933a7ac9a90d5064e146` · procedure pin Mastermind `19cb00cf`. `T:`=templates/intraday_flow.html.j2, `B:`=scripts/build_intraday_flow.py, `E:`=engine/intraday_flow.py.

## 1. JS/DOM contracts
- Hero: `#ift-hero` T:376 · `#sess-pill`/`#sess-state` T:379 · `#ift-hero-copy` (`aria-busy`) T:385 · `#hero-thesis`/`#hero-sub` T:387-388 (tints T:1176) · `#hs-count` T:394 (animated T:1112) · `#ctx-strong`/`#ctx-watch`/`#ift-stamp` T:404-409 · `<body>` `tape-*` T:1180-81 · `#ift-aurora` T:371.
- Counts: `.stance-strip` T:423 + six `.stance-card[data-stance]`+`.sc-count[data-count]` T:424-453 · `STANCE_META` (7 keys incl `degraded`) T:625-633.
- Spotlight: `#spotlight-panel`/`#spot-note`/`#spot-grid` T:458-467 · `.spot-card/.stance-pill/.spot-metrics` T:1282-1308 · `_spotHtml`/`_spotSeen` T:1239.
- Table: `#leaders-table` T:494 · `th[data-col]`=ticker|stance|last|rvol|tape|dealer|expand T:497-503 · `#leaders-body` T:506 · `tr.lead-row` carries `data-ticker,data-stance,data-rvol,data-k,data-last,data-stance-order,data-baskets` T:1362-64 · `tr.detail-row[data-detail]` T:1367 · `tr.group-head` T:1553-54.
- Controls: `.chip[data-basket]`×9 T:476-484 · `#ift-search`+`data-ph-zh`+`langchange` T:488/1676-82 · `#group-toggle`/`groupByStance` T:486/1656-58 · `BOARD_CAP=8` T:621.
- Keyboard: only `.ift-see-all`, `?` lens T:1087, `a.tk-link` T:1317 are focusable; `.expander` T:1360, `.chip`, `.stance-card`, `.toggle-btn`, `th` are click-only.
- Theme/lang: `<html data-theme/data-lang>` pre-paint T:20 · `theme.css` T:21 + `theme.js` T:1700 · `.l-en/.l-zh` CSS-only swap (theme.css:582-583) · `html[data-lang=zh]` remaps `--ok/--act` (theme.css:578-580) → flips `.lane-fav`.

## 2. Model semantics vs presentation
Byte-identical (do not touch): `computeLegs` T:695-732 (mirror `E.confluence_legs` E:421) · `computeStance` T:798-867 (mirror `E.stance` E:668) · `computeRvol` T:671-683 (`E.rvol_tod` E:93) · `computeAll` T:1092-1104 · `laneCounts` T:1105 · `dealerOf` T:735 · `quotePx` T:741 · `STANCE_META` T:625. Engine truth `E.washout_context` E:832, `E.dealer_context` E:555. All other inline JS and CSS T:22-368 is presentation.
Mirror drift (report only — classification, not layout): JS `degraded` lane T:805-807 is a 7th state the engine lacks (feed availability, not a classification); JS L1 falls back to an `entry_signal.status`/`vol_squeeze` proxy T:699-707 where the engine returns `None`.

## 3. Refresh / selection / focus + rail pitfalls
`render()` T:1597 rebuilds every row via `tbody.innerHTML` T:1617 on each fetch completion (quotes 60s, pulse 5m, flow 3m, one per root payload T:1036-63); T:1583-91 records **19 rebuilds in 2.8s** at load; `scheduleRender()` coalesces to 50ms.
- Focus destroyed every render: `tbody.innerHTML` replaces the focused node and `applyView()` re-appends rows via a fragment T:1530/1560, blurring anything inside a moved row — `a.tk-link` T:1317 loses focus ~every 60s. No selection state exists, only `openRows` T:620.
- No per-row staleness: `computeStance` degrades only while `isMarketHours()` T:805; off-hours with a leftover `flow_pulse.json` (`bars_today>0`) makes `livePresent` true T:803 and runs the **live** branch. Executing the extracted JS (closed market, stale pulse) returns `key="act"`, reason "Reclaimed above the average price on durable volume…" — while the hero says "Market's closed" T:1160-73.
- `degraded` counted nowhere: `laneCounts` counts only six keys T:1106-08, so the ladder sums to N−degraded while the board lists N; `hs-count`=`act+get_ready` T:1127 excludes them too.
Rail pitfalls: (1) needs new `selectedTicker`; `openRows` is never cleared on filter/sort change (only `boardExpanded` is: T:1634/1642/1652/1658/1678). (2) A rail sits outside the tbody, so `applyView()`'s hide/show of `detail-row` T:1538/1547/1558 no longer covers it. (3) Rail DOM is rewritten each render — use the `_spotHtml` guard T:1271 or it flickers 19× at load.

## 4. Tests and smallest meaningful regression matrix
Suites at f754bdee: `test_intraday_flow.py` + `test_intraday_flow_stance.py` · `test_intraday_flow_ncp_js.py` (JS mirror; `PAGES` over template+site — `test_template_and_site_copies_agree` requires Jinja-free JS byte-identical in both) · `test_intraday_flow_spotlight_flicker.py` · `test_intraday_flow_w11_r1..r5.py` (copy-honesty + visual). Visual proof: the Playwright rig `mockups/evidence/intraday-flow-w11/capture.py`, gated by `scripts/check_ui_visual_evidence.py`.
- A — must not weaken (classifier/feed parity): the first three suites; any failure = semantics changed.
- B — layout-coupled, update deliberately: r1:272 hero-legend+`id="hs-count"`+`animateCount(num, actionable)`; r1:340/r1:405 board-cap shim on `lead-row`/`detail-row`/`group-head`+`data-*`; r2:76 `COL_ATTR`→`applyView` region; r5:308 skeleton hosts `aria-busy`+one `.sr-only` each.
- C — trust checks to keep green: r2:533 quotes-outage-is-degraded; ncp_js:604-720 boot set; r2:168 feed-word matrix (3 lanes×4 states×2 languages); ncp_js:346/477 source clock and live-label freshness.
- D — gaps to add (none exist): closed-market+stale pulse must not yield `act`; degraded names must appear in a count; per-row "assessed at" qualifier.

## 5. Evidence labels from stale/missing inputs + display-only seams
Yes. In the committed payload `options_entry.evidence_quality` is **`"thin"` for all 116 leaders**; `evidenceWord` T:1498 renders it as the dealer-map "Evidence" row T:1482, beside live tape numbers, with no as-of. Also nightly-only and unqualified beside live tape: the dealer map (`site/gex/<T>.json` → `B._dealer_from_gex` B:649, merged in `B._load_options_entry` B:740-790 — **no date field**); L7 `failed_breakout_trap` (**False for 112/116**) shown as ✓ "Clean leader (no trap)" — a negative assertion rendered positive.
Display-only seams (no #6867 rewrite, no engine change): (1) `leader.built` (`"2026-10-30"`, per leader) is **never read by the template** — the natural per-row recorded-assessment stamp. (2) `entry_signal.status` (7 recorded statuses: `bounce_wait`×56 … `buy_soon`×1) is used **only** as the L1 proxy T:701-704, never displayed — a ready-made "next condition" sentence. (3) `degraded` copy T:805-807 is the template for an off-hours/stale "no current read". (4) `updateFlowStamp` T:1065-89 shows "Board built &lt;as-of&gt; · &lt;headline&gt;" but the per-lane feed rows live in a **hidden `?` popover** T:1085-88 — the caveat must be at the assessment.

## 6. Builder / render command (page only, no poller, no external fetch)
Canonical nightly (no network; local stores only): `python -m scripts.build_intraday_flow --mode nightly --as-of <ISO8601>` (production: `scripts.build_intraday_flow --mode nightly`, `closing-bell.yml:379`). It also rewrites `site/flowtracker/base.json` B:1060-62 and, unless redirected, `data/run_status.json`; redirected roots make it ephemeral and skip run_status (B:1084-88). Reads only local stores — no poller, no HTTP. `--mode fastpath` (B:1273) writes `site/live/flow_pulse.json` and must **not** be used here.
True page-only render (recommended for design iteration): render the template against the **already-committed** `site/flowtracker/base.json` and write via `lib.pages.write_page` — the builder's path at B:1118-24 (`FileSystemLoader(templates)` → `tpl.render(...)` → `write_page(...)`). Output is **not** byte-equal to the committed page, which had gone through the site sweeps — inline `<style>` lifted by `scripts/externalize_css.py` to `site/assets/css/1b3a1152.css`, plus the data-base/asset/shell sweeps. A page-only rebuild must therefore be followed by those sweeps (`daily.yml:4848-4856`) or the served page keeps stale CSS.

## Gaps / explicit unknowns (not guessed)
- No Paper tool invoked, no Paper write attempted; the plan's Paper catalog/readback not re-verified. No pytest executed (read-only scope): test claims come from reading assertions.
- `site/live/intraday_quotes.json`/`site/live/flow_pulse.json` are **not committed**, so the post-close staleness window is unconfirmed empirically; the closed-market `act` result comes from executing the page's own JS with a synthetic stale pulse (a model of that state, not a capture).
- Not audited in depth: `engine/intraday_flow_history.py` (`_explicit_coverage` L159, `_evidence_availability` L206) — the plan's canonical freshness/coverage functions. `main` drifted from the audited base (`3c3f3190`): `site/intraday_flow.html` by 19 lines (shell/nav/`?v=` only), `scripts/build_intraday_flow.py` by 69 lines → a rebase must re-check `B`.
