# Tech Volatility Shock — Macro Market Internals

**Parent:** WS:MARKET-OS (product context only; this branch does not mutate the incumbent workstream/waves). **Status:** source candidate, not released. **Current user assignment:** integrate the attached SPY/QQQ shock panel into the US Macro Dashboard.

## Outcome and provenance

Users can tell whether tech is experiencing an unusually severe selloff relative to the broader market, how extreme the day is against a causal historical reference, and whether damage came before or after the opening auction. This is an EOD **descriptive** instrument, not a new trade signal, risk classifier, or forecast. It must extend the existing market-state/risk surfaces rather than stack a second regime hero or originate a new shock taxonomy (see `research/UNIFIED_DASHBOARD_DISPOSITION.md` and `research/TECH_INTERNALS_CODEX_ADJUDICATION_BY_FABLE.md`).

**Input:** `data/massive_stock_day/{SPY,QQQ}.parquet` through `lib.store`; qualified unadjusted raw OHLC and whole-market-day volume (not regular-session-only volume). Do NOT combine Yahoo total-return-adjusted close with raw opening prices. Missing R2 restore/volume/history or mismatched dates must display disclosed unavailability; never synthesize values. Display as-of session date and source basis. No new collector, narrative classifier, or dependency on an LLM.

**Math (same paired market date):** net return = C[t]/C[t-1] - 1; overnight = O[t]/C[t-1] - 1; intraday = C[t]/O[t] - 1; `(1+overnight)*(1+intraday)-1 = net`. Relative daily performance is `(QQQ return-SPY return)*100` percentage points (not the QQQ/SPY price ratio return). Each 60-session z-score uses the **prior** 60 return observations (exclude t) with sample standard deviation; no insufficient-sample claims. Relative z-score applies the same causal window to the paired daily difference series. Volume multiple = current full-day aggregate volume divided by the prior 20-session mean, clearly labeled. Yearly worst-day rank counts observed YTD eligible sessions; disclose eligible N. Recency/extreme labels must be derived from observations, not screenshot figures. Missing, nonpositive or nonfinite bars invalidate the affected metric, not a fabricated zero.

**Session caveat:** Massive's daily OHLC rungs are XNYS regular-session prices and the corresponding daily activity counters include broader sessions (DSC-SPY-DAILY-AGG-IS-RTH-PRICE-FULLDAY-ACTIVITY). 'Overnight' means previous regular close to next regular open; it does not separately isolate after-hours versus premarket. Display additive split via rounded legs only with a compounding note. No unverified "1-in-192" probability claim.

## Task tree and acceptance

| ID | Node | Depends | Status | Done when / proof |
|---|---|---|---|---|
| TVS.P1 | Measurement and contracts | — | implementation_complete; current-head CI pending | Exact source/basis/date/causal formulas and null coverage tested with synthetic bars |
| TVS.P1.T1 | Pure snapshot calculator | — | implemented; unit tested on earlier head | Supports aligned SPY/QQQ; basis/no-open guards; 60-session z and paired relative z; YTD ranking and volume baseline; opposite-sign sessions |
| TVS.P1.T2 | Deterministic unit tests | P1.T1 | implemented; current-head retest pending | Formula equality, leaks, mismatch, missing, stale, partial and yearly rank pass |
| TVS.P2 | EOD Macro user experience | P1 | implemented; real browser proof pending | Compact summary after existing regime section with opt-in detailed comparison, responsive 2-up/stacked cards, status/source labels; no duplicate regime verdict |
| TVS.P2.T1 | Renderer partial and safe mount | P1.T1 | implemented; CI/prod proof pending | Build-site route only (not stocks mode); Jinja escaping; no runtime external requests; dev re-render parity |
| TVS.P3 | Release/quality | P1,P2 | blocked | Exact-head CI + non-author review; production date, source restore, numeric fixture and responsive browser interaction verified; protected merge/deploy through normal owner only |

**Negative acceptance:** no public screenshot numbers hard-coded as current market quotes; no silently adjusted/unadjusted mix; no claim of intraday live data; no standalone "tech shock" trading decision engine; no user-position sizing or signals; no overwriting concurrent Macro source work. Current modified surface restricted to the additive engine, focused tests, a self-contained presentation partial, source-bound build hooks and this plan.

**Next action:** implement P1.T1 and T2 on isolated `sol/tech-volatility-shock-20261030` branch, then wire the compact component to `scripts/build_site.py` and `scripts/render_macro_fast.py`. Publish one reviewable PR. Do not mark production live from CI alone.

## Integration discovery — 2026-10-30

The nightly `.github/workflows/daily.yml` engine job explicitly restores
`massive_stock_day` R2 before its `scripts.build_site` render. The
`.github/workflows/render.yml` and `engine-render.yml` express render spines
**do not** restore that ~617 MB store. Binding raw `store.read` in the page
renderer alone would therefore produce a good nightly panel but erase its
metrics on later lightweight re-renders.

**Repair implemented:** the existing nightly `build_site` produces a **derived
EOD presentation view**, `site/marketdata/tech_volatility_shock.json`, only
when both source-backed raw bars pass the calculator's pair/date/price checks.
This is under the already-authoritative site/ git publication flow; no additional
collector or market-state decision plane. The view is small, schema/scopes
validated and atomically written, and carries the observed trading date and
generation timestamp. Express renders with no raw R2 read the last committed
view, recalculate its age against the independent exchange calendar, visibly
disclose stale/partial status and never overwrite the qualified observation with
a fabricated zero/unknown. A newer direct raw observation supersedes an older
projection; stale raw inputs never move the readout's as-of date backwards.

Focused synthetic test suites now cover nightly-to-express handoff, one-completed-
session staleness, monotonic as-of selection, corrupted projections and failed
view publication. The dedicated, path-scoped
`.github/workflows/tech-volatility-shock.yml` runs these named suites: the
repository's broad CI pack does NOT automatically run newly added `tests/*`
suites (see `.github/workflows/ci.yml` unrun-suite census), and claiming tests
without a real executable runner would be false.

**Status remains BUILT_NOT_PROVEN** until exact-head CI, a non-author review,
natural nightly data generation, express-route retention and responsive/browser
real-page qualification. PR #10229 is an open Draft at the writing of this
checkpoint; no self-merge or production acceptance is asserted.

## 2026-10-31 CI and UI hardening checkpoint

- Previous candidate `9013e169901a1b2d0e778519933d759b2ed87e8e` passed its dedicated
  source-bound fixture job (`41170158112`, **16 passed**), but broad `ci`
  (`41170158155`) failed. The exact defects were **eight** curated
  `scope: exclusive` import-closure omissions (contract-delta and
  `ci-control-plane-contracts`), and **40** new literal color/radius/font
  decisions on the added presentation template (design-governance).
- Follow-up `464af868` registered the 14 missing scope-path entries in
  `.github/ci/legacy-jobs.yml` and replaced the hand-written CSS literals
  with the existing house tokens. `4bf48bca` removed the final inline hex
  accent. This is a repair of real failures, **not** a gate waiver.
- UI audit found the screenshot-inspired panel had English-only copy on the
  existing Chinese-language Macro route and a static "Expand" accessibility
  label that became wrong when expanded. `ee77fd8e` supplies `l-en/l-zh`
  paired copy on summary, metrics, status, source caveats and methodology;
  localized toggle pseudo-content; and removes the overriding summary aria
  label, allowing native `<details>` expanded-state semantics. Duplicate
  bar text is marked decorative because readable overnight/intraday numbers
  are already adjacent. A dedicated bilingual/accessibility regression test
  is included. Both code and test changes remain **unreleased**.
- The earlier Fabric review `tvs_10229_review_01` was explicitly
  `REQUEST_REFUSED_BEFORE_LAUNCH / EXECUTION_NOT_ELIGIBLE` (no worker START
  or result; no retry). A **distinct human review-coordination request**
  was delivered to Grok Secretary in Slack
  `#dotsandgroksecretary`, root `1793426477.516929`. Delivery is not
  review acceptance, and any earlier head in that message is invalidated by
  the subsequent source changes. The final exact head must be reported in
  that same thread before any independent review.
- Production site `site/macro.html` at main `1c858789` carried
  `2026-10-30` regime as-of, without this new panel; the public crawler
  returned an older `2026-10-20` snapshot, so crawler age alone is not
  a valid production-freshness diagnosis. No live R2 sample, rendered panel,
  390px/dark/light browser proof or merge/deploy acceptance is claimed.

**Release frontier:** check all exact-final-head `ci`, `fences` and
`tech-volatility-shock` results. Obtain a genuinely independent non-author
review bound to that head and current base, resolve any findings, use the
normal protected merge path (no self-approval), then prove the actual nightly
R2→projected snapshot→Macro page and later express render, responsive bilingual
browser layout, and the absence of a Stocks-mode duplicate. Do not mark
`PROVEN_LIVE` before those receipts.

## 2026-10-31 independent review — repair candidate (not accepted)

Independent non-author `MastermindX1` submitted formal **REQUEST_CHANGES** on
immutable head `95ce26e18c9ac4fc101216dd0417f779ab65d547`:
https://github.com/mastermindx-market-intelligence/macro/pull/10229#pullrequestreview-5721625307 .
The reviewer confirmed the previous 17 focused tests and fences were green,
but identified five **release-blocking source defects**. The current repair
candidate addresses each without waiving a CI gate:

1. `build_site.py` had two Macro outputs: initial source-mounted render and a
   conditional fresh-board re-render that overwrote the panel. Both now call
   one `write_macro_page` owner; the test rewrites actual final HTML using
   a newer board value, requires exactly one panel, and checks both source calls.
2. `_volume_multiple` previously used 20 last *present* bar rows even if a
   trading session was missing. It now rejects a calendar gap between any of
   those rows and the as-of date, preserving a null instead of inventing a
   20-session denominator; regression tests remove a prior-window session
   while preserving older available bars, and keep normal holiday/weekend
   gaps valid.
3. White/house text on red/green loss-bar fills failed 4.5:1 in EN/ZH dark/light.
   The visible colored bars are now **decorative only** (no foreground glyphs).
   Adjacent per-segment percentages and labels remain readable outside
   colored fills. Browser contrast acceptance must measure those adjacent
   labels, not the bar fill as a text surface.
4. Stable `reason_code` for all emitted data status causes and a keyed,
   deterministic ZH translation preserve the same cause-specific detail as EN:
   e.g. an as-of session mismatch is distinct from a missing prior close.
   Unknown older source reasons remain specific rather than generic.
5. Dev-fast Jinja environment now enables production-parity
   `autoescape=True`, with explicit injection test covering untrusted
   `reason` and native source markup.

This new source revision needs **new exact-head** feature suite, CI/fences
proof, and fresh *independent non-author* review. Old head review remains a
record of real defects, not approval of this repair. The reviewer and Grok
Secretary closed the original review request with STOP; any next review must
have a fresh scoped request/identity, not silently reuse the old worker.
Real production R2→snapshot→page, express render preservation, bilingual
browser paths and protected merge/deployment remain separate gates.

## 2026-10-31 third review & CI source repair (post-feda59ce)

Fresh non-author MastermindX1 review on `feda59ce` returned
**REQUEST_CHANGES**, identifying an *inserted* Sunday/NYSE-holiday raw daily bar
as a distinct case from a **missing** NYSE session. Even with the old 20-row
adjacent-session-hole check, a non-session row could replace one prior actual
session, corrupt the 20d volume denominator (0.35× versus the qualified 2.07×
fixture) and leak into prior-return z/rank. **Repair:** refuse the entire
SPY/QQQ readout with typed `NON_SESSION_HISTORY` if either raw daily history
contains any row not identified as an NYSE session. This is deliberately
fail-visible, not filtering or silently substituting historical prices. Tests
inject both Sunday (2026-10-25) and observed Labor Day (2026-09-07), plus a
QQQ-only non-session row. Existing valid-weekend/holiday *gaps* and missing
trading-session guards remain intact.

CI `41178112097` at `feda59ce` failed: `contract-delta` and
`ci-pack-1` each found that `lib/nyse_calendar.py` was a source dependency
of the targeted feature suite but absent from that suite's PR trigger
paths. The workflow adds the actual dependency path without suppressing the
closure check. `ci-pack-6` failed because the new inline CSS had no
committed governed visual evidence. The fix uses the **existing**
`mastermind.page_evidence_receipt.v1` → `mastermind.p0_evidence.v2`
format and unmodified `capture_page_evidence.py`, not a new evidence plane:
`mockups/evidence/tech-volatility-shock-20261031/`.
The exact M2 Chromium capture has 8 required rest cells at
1440×900/390×844 × EN/ZH × dark/light plus 8 authentic
`focus(.tvs summary)` interaction captures, with actual PNG bytes,
manifest hashes, observed theme/locale and capture tool digest. The source
fixture deliberately opens the normally collapsed panel to reveal all cards
and uses **synthetic** SPY/QQQ numbers: this is visual evidence only, not
production price, deployment or end-to-end market-data proof.

New exact-head `ci`, `fences` and `tech-volatility-shock` must finish
green, then request a **new** independent non-author review of that exact
head. Former reviewer comments on prior commits remain historical
`REQUEST_CHANGES`, not acceptance. Protected merge and actual production
browser/raw-R2 acceptance remain outstanding.
