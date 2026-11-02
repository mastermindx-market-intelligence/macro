# Intraday Flow — independent review and repair record

## Review identity

- Paid Fabric run: `intraday-final-review-20261102-c2`.
- Root/parent: `intraday-flow-design-upgrade-20261101-c2`.
- Reviewed head: `cdc17bf634219135c000b0d97c84d1dd102014c6`.
- Response SHA-256: `7d61c0905c0248112489bdd2c1ccc6ccbcaa8900613faea6891e12b5f8bba196`.
- Actual provider/model reported: GLM 5.3 through the admitted Fabric lane.
- Returned disposition: **CODE=CHANGES_REQUIRED; VISUAL=PARTIAL**.
- Parent disposition: report consumed for bounded repairs. It is not a code approval,
  qualified visual acceptance, Paper acceptance or release authorization.

## Repair adjudication

| Finding | Decision and bounded repair |
|---|---|
| F1 — locale-specific direction colors | Accepted. Buy now and In favour both use the canonical rising-price ink token; no global token change. Browser checks compare both actual dot colors with the resolved shared token in all eight cells. |
| F2 — unavailable inputs labeled Not met | Accepted; also independently identified by the principal design adviser. A display-only availability mask distinguishes absent VWAP/price, rvol, durability and trend inputs. Existing leg values, K and classification functions remain unchanged. Real controls are tested with missing, zero, positive and supported-rvol-fallback fixtures in both languages. |
| F3 — stock overview inaccessible on phones | Accepted. Opened evidence now includes a native stock-overview link on layouts without the inspector, with a 44px target and stable focus identity. Its path and focus retention are exercised. |
| F4 — repeated count announcements | Accepted. Identical count markup is no longer rewritten. A mutation observer verifies that an unchanged count region stays silent across actual asynchronous refresh. |
| F5 — English-only feed-status name | Accepted. The feed help accessible name follows the current language on initial render and language changes; an isolated rendering context retains a safe English default. |
| F6 — native sort focus styling | Accepted. Select is included in the page focus-visible rule; actual keyboard focus is checked on phones. |
| F7 — untagged names bypass theme filters | Accepted as a display-filter edge case. Theme matching uses exact tokens; names without a theme remain in All and are excluded from specific themes. Both behaviors are exercised with explicit test fixtures. |

The degraded-count gap is also addressed with a neutral count of existing rows that
have no current read. It is separate from the six deterministic classifications;
its count plus the stage counts reconciles to the same full population. No name is
reassigned to Stand aside and no trading category is added.

Opened evidence now carries actual quote/source times (synthetic quote clocks are
excluded), the producer's stale marker, an explicitly named nightly package date,
and the absence of a dealer-chain source clock. A nightly build is never relabeled
as a classification or dealer-chain observation timestamp. Dealer wall-strength
values are readable and localized instead of exposing internal underscore strings.

The original 15 protected model/coverage/session/leg functions remain byte-identical
to the initial base. The separate #6867 timing/precursor work is untouched. The
reported shared-navigation startup movement remains an inherited limitation, not a
field-performance pass. The report's phrase "accepted limitation" is read only as
reviewer acknowledgement; it does not grant final production performance acceptance.

## Remaining independent gates

A separate bounded follow-up must verify these repairs on the next pushed exact
head. The author does not self-certify their independent approval.

Qualified visual judgment remains open. The reviewer explicitly reported a typed
vision-helper refusal and was not a human/Opus route. A current discovery of the
existing Claude session target family returned `backend_unavailable: installed
Session Bridge owner is unavailable`. No substitute route was started, no guard
was bypassed, and native advisory reasoning is not represented as formal acceptance.

Paper still requires the existing runtime owner's catalog qualification; no canvas
write has occurred. No source merge, deployment or commissioning acceptance is claimed.

## Original report — preserved verbatim

---

All checks complete. The executed headless probe confirms the zh lane-color split against the shipped stylesheets. Composing the final report.

---

# Independent exact-head review — Intraday Flow redesign (macro PR #10498)

**STATUS:** COMPLETE — defects found; merge not recommended until F1 is fixed.
**Reviewed head:** `cdc17bf634219135c000b0d97c84d1dd102014c6` (PR head verified equal; baseline `f754bdee…` is ancestor, 5 commits, 52 files). UI source `9e1af79…` confirmed to carry identical template/CSS (later commits add proof/docs only).
**Actual provider/model:** GLM 5.3 (Fabric lane `87be0891…`), via Claude Code harness. Not Opus, not human.
**CODE=CHANGES_REQUIRED** (one blocker F1; remainder minor).
**VISUAL=PARTIAL** — AGENTS requires human/Opus visual judgment; my route is not qualified, and the guarded vision helper returned a typed refusal (`GLM_VISION_DELEGATION_REFUSED reason=controller_minimax_lease_required`), preserved verbatim, not retried. What follows includes structured pixel evidence only; source inspection is not visual acceptance.

## Findings (severity order)

**F1 — REGRESSION, blocker-ish (one CSS line): ZH lane colors split the two "long" stances.** `templates/intraday-flow.css:36-38` — `.lane-act{--lane:var(--ink-ok,var(--ok))}` vs `.lane-fav{--lane:var(--ink-up,var(--up))}`. theme.css swaps `--up/--down` per language globally (`html[data-lang="zh"]{--up:#e06464…}`, lines 303/316) but remaps `--ink-ok→--ink-up` only inside `.rrx/.igx/.igs` (lines 578-580); this page contains none (0 hits in template+CSS). Executed Chromium probe against both shipped stylesheets: zh dark act=`#3da564` **green**, fav=`#e06464` **red** (zh light `#296b48`/`#b23c3d`); EN dark act `#3da564` vs fav `#45b873` (two different greens). Under the site's own 红涨绿跌 convention, the *Buy now* lane paints the zh "down" color while *In favour* paints red — recreating exactly the defect the baseline ruling fixed by pinning both lanes to `--up` (documented comment deleted with the old inline stylesheet; no re-ruling exists in MASTER_PLAN/DESIGN_SPEC/VERIFICATION). Impact: zh readers misread the strongest buy signal as bearish; EN gets inconsistent greens for equivalent stances. Remedy: `.page-intraday-flow .lane-act{--lane:var(--ink-up,var(--up))}` (presentation-only, restores baseline pin).

**F2 — Inherited conflation, newly verbalized: absent inputs read "Not met".** `intraday_flow.html.j2:998-1003` renders Met/Not met/Unavailable from `computeLegs`, but L2/L3/L4/L6 initialize to `false` (lines 368-388), never `null`. Off-hours or missing pulse/quote, the evidence panel shows "Reclaimed above VWAP ✗ Not met", "Volume elevated ✗ Not met" although the input is unavailable (L1/L5/L7 correctly tri-state). Baseline showed a bare ✗; head spells "Not met", overstating. Remedy is display-layer only (null-vs-false is stance-equivalent everywhere `L2/L3/L4/L6` is consumed except `===true` checks), keeping `computeLegs` byte-preserved.

**F3 — Capability regression (low): phone loses the per-name stock link.** The stock-overview link now exists only in the inspector (`j2:1082`), `display:none` ≤1199px (`css:171`). Baseline ticker cells linked every row to `stock.html#TK`. Users ≤1199px (all phones) have no path to a stock page. Remedy: also render the link in the mobile evidence row.

**F4 — A11y noise (low):** `#count-label` (`role=status aria-live=polite aria-atomic`, `j2:170,1223-39`) rewrites `innerHTML` on every coalesced render (~60 s poll) even when unchanged → repeated full SR announcements. Skip identical writes (pattern the retired `_spotHtml` guard used).

**F5 — Low:** feed-status `?` trigger `aria-label="Feed status"` is EN-only in zh (`j2:768`); not covered by `localizeControls`.

**F6 — Low:** workspace focus-visible rule `:where(button,a,input,summary,[tabindex])` (`css:158`) omits `select`, so `#ift-mobile-sort` depends on UA/theme defaults.

**F7 — Edge:** leaders with no baskets get `data-baskets="all"` and bypass every theme filter (`j2:907,1188`). Moot today (116/116 have baskets) but a silent escape hatch.

**Inherited, disclosed, not regressed:** degraded rows appear in board totals but in no stance-card count (`laneCounts` six keys; audit D-gap left open); off-hours a stale pulse can still produce a present-tense "Buy now" reason — now tagged *Recorded* with source clocks shown; weekday check intentionally omitted from the ET session window; quotes-fetch catch re-throw path can leave status stale.

**Genuine improvements verified (not defects):** ungrouped sort comparator was actually **inverted in baseline** and is fixed here (pinned by new executed test); full button/aria-pressed/aria-expanded/aria-sort/aria-controls coverage replaced click-only divs/spans; focus restoration across async rebuilds, menu Escape+focus-return, empty-state reset; separate honest source clocks ("time unavailable" never becomes *now*); ncp (call-only) vs net_all (calls+puts) distinction preserved; CSS token discipline verified (zero color-mix/rgba/hex; no edge rails — baseline's 3px stance-card rail removed); paired CSS byte-identical; render coalescing; no shared-asset, nav, producer or classifier changes (diff -u shows no hunk touching any of the 15 preserved regions — independently stronger than trusting model_preservation.json).

**Adversarial results:** six stances + degraded, nine themes, search/reset, sorting/grouping, counted 8-of-116 expansion and seven evidence legs all present and pinned by tests; `browser_verification.json` 403/403 passed (0 failures) with real focus-trace, menu-clip and assistant-clearance assertions; layout-stability phone candidate ≈.25–.28 vs baseline .23 (desktop .69 vs .73), dominated by shared nav — accepted limitation, correctly not claimed as a performance pass.

## Evidence (actually performed)

- `gh api` pulls/compare (head SHA verified); raw file fetches at pinned SHAs into `/home/ubuntu2/intraday_review_cdc17bf/` (scratch, no repo writes).
- Read fully: `templates/intraday_flow.html.j2` (head, 1441 ln), full base→head `diff -u` (1465 ln), `intraday-flow.css` (371 ln), six test diffs; `cmp` site/templates CSS (identical); BASELINE_AUDIT, VERIFICATION, DESIGN_SPEC, model_preservation (15 regions cross-checked via diff), README/EVIDENCE.yml/smells, manifest (24 states), browser_verification (aggregated), layout_stability (summarized); grep-level: MASTER_PLAN, theme.js (lens delegation, `langchange`), theme.css token/zh blocks.
- Parsed embedded `BASE_DATA` from built page: 116 leaders, thresholds 1.30/0.60/10; no unrendered Jinja; built/template parity spot-checked.
- Executed: Playwright computed-style probe (zh/en × dark/light lane colors); PIL structural checks on 14 PNGs.
- **Images actually opened (downloaded, sha256-verified against manifest; structural analysis only, no semantic visual judgment):** final-r2 resting ×8 (all cells), `4fd961c…hover`, `8d48a34…focus`, `54bff734…focus`, expanded ×4. Results: dimensions match claims (1440×1135, 390×2332–2351, crops 1018×619/352×1036-72); light/dark luminance 242 vs 26; no saturated rail pixels at sampled container edges; README↔manifest mapping exact 8/8; correctly-paired force-state diffs localized (1.7–1.9% desktop; phone focus 11%, consistent with re-render timing, unadjudicated).

## Gaps / deviations

Local macOS carrier absent (Linux host) — all reads via GitHub API at pinned SHAs. No pytest/verify_browser execution (read-only, no clone) — pass counts are builder evidence; I independently read the assertions. MASTER_PLAN read via targeted grep only. No semantic visual judgment (route unqualified; helper refused — typed refusal preserved). Paper catalog not re-queried; no writes attempted or implied. No CI, deployment, or production acceptance claimed or conferred.
