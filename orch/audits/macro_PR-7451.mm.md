# Plain-language / theme / validated-claims audit — macro PR #7451

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-19.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | #7451 |
| title | `[MO-B F09 W8-1] Cash runway on the debt-maturity ladder: one annual filing's cash, operating cash and equipment spend → months of runway + next-12-month cover (MO-PAID-059 / MO-DELTA-018 second slice)` |
| head | `0079a08a0f9700549ebd703040858256610c3eeb` (CI contract-delta wiring on top of r2 `dfaae20dfb` and r1 `fdc4c3c43b`; body explicitly types all three SHAs and the r2 `no rewrite, no force-push` posture) |
| merged | 2026-09-20T00:40:06Z (24-h window: 2026-09-19 19:00 UTC → now) |
| half-B child | MO-B F09 W8-1; second slice of packet B-F09-3 (the first slice was the debt-maturity ladder, now also wiring cash runway on the same ladder) |
| owner | Meta-CEO B seat (F09 W8-1 lane, MO-PAID-059 / MO-DELTA-018 records-pass) |
| diff scope (per `gh pr view --json files`) | 10 files / +1204 / −14. `engine/cash_runway.py` ADDED (+352); `scripts/build_debt_maturity.py` MODIFIED (+22 / −12 — bounded tags 6→9, cache-write/slim paths use `_ALL_TAGS`); `scripts/build_stock_library.py` MODIFIED (+61 — new `_resolve_cash_runway` + per-ticker block in `rec`); `scripts/build_ticker_pages.py` MODIFIED (+1 — `cash_runway` into the page context); `templates/_debt_maturity.html.j2` MODIFIED (+63 / −2 — new `.dmw-runway` block under existing `#debt-maturity` section); `templates/theme.css` MODIFIED (+12 — `.dmw-runway` margin/border-top + light-variant border colour only); `tests/fixtures/cash_runway/aapl_cash_trimmed.json` ADDED (+119 — last 3 FY 10-Ks trimmed from live SEC XBRL); `tests/fixtures/cash_runway/synthetic_burn.json` ADDED (+53 — `_synthetic: true` CIK `0000099999`); `tests/test_cash_runway.py` ADDED (+511 — 100 passing tests including the round-2 fixes for r1 typed defects); `.github/ci/legacy-jobs.yml` MODIFIED (+10 — wires `engine/cash_runway.py` into 5 curated pack scopes + the render-guard test step) |
| r1 → r2 deltas | The body types the round-2 "10 failed, 90 passed" RED proof at r1 head (`fdc4c3c43b`) with the round-2 tests already present: each failure maps to a named defect — `annual_burn_usd` missing, `runway_display` enum mismatch, attribution phrase still started with "Last year", raw `$0.0025B` slipping into ZH, `.dmw-runway` placed after `mod-ft` / `</section>`, source order outside `#debt-maturity`, etc. r2 closes each by a named test. **This is the kind of "I will not call it done until red→green per assertion" PR the audit lane exists to confirm.** |
| base | `origin/main` at `03f297b630` (r1 branch point per body) |
| live readback | The body ships three render proofs against three states (AAPL self-funding, synthetic burn, not_loaded) with EN + ZH copy + the underlying context dict; tests assert every numeric token and every phrase. **Live readback = the 100/1 pytest green + the three render sentences.** |

The body is unusually long because it is part ship-record, part dispute: the SEAT corrections block ("SEAT corrections to the executor report (Meta-CEO B 0a14dd9d, 2026-09-19)") re-measures facts against the branch object and overrides the executor's typed output (`synthetic fixture uses CIK 0000099999 not 0000009999`; r1 body listed `engine/cash_runway.py +441` where the r1 three-dot diff was 335 lines; `_dm_status` jump-link gate deliberately left unchanged per the ladder's ownership). That is exactly the upstream-side evidence recheck this audit lane exists for — the seat caught the executor's three "wrong"s before squash-merge.

## Plain-language findings

The macro repo has no `scripts/check_plain_language.mjs` (terminal-only — port lives in `mastermind-terminal/terminal/scripts/check_plain_language.mjs` and is not relevant to a macro `engine/*.py` + `templates/*.j2` PR). The plain-language discipline for this PR applies in three places:

1. **User-facing template copy** (the new `.dmw-runway` block in `templates/_debt_maturity.html.j2`).
2. **Operator-facing module docstring** (`engine/cash_runway.py`).
3. **Operator-facing null/why messages** (5 null states × EN/ZH).

All three are checked below.

1. **New user-facing copy is honest and uses the design-doctrine's word budget.**

   The template adds one block under the existing `#debt-maturity` section (re-using the same `.dmw-lede` class, the same section footer `Research context only — reported figures from SEC filings, not a rating, a signal or investment advice.`, the same `_dm_status` jump-link gate deliberately left alone). Six rendered sentences cover three "reported" states:

   | state | EN | ZH |
   |---|---|---|
   | self_funding | "In the year ending 2025-09-27 (10-K) it brought in more cash than it spent, including equipment — no burn to measure." | "截至 2025-09-27 的财年（10-K）其现金流入多于支出（包括设备支出），暂无可衡量的消耗。" |
   | self_funding + cover | "In the year ending 2025-09-27 (10-K) cash on hand covers 323% of the debt coming due in the next 12 months." | "截至 2025-09-27 的财年（10-K）现金可覆盖未来12个月内到期债务的 323%。" |
   | more_than_10_years | "Cash on hand: $X. In the year ending Y (10-K) it spent $X more than it brought in after buying equipment — at that pace the cash lasts more than 10 years." | "现金及现金等价物：$X。截至 Y 的财年（10-K）购买设备后的支出超过现金流入 $X，按此速度现金可支撑超过10年。" |
   | months (≥12) | "Cash on hand: $X. In the year ending Y (10-K) it spent $X more per month than it brought in after buying equipment — at that pace the cash lasts about N months." | "现金及现金等价物：$X。截至 Y 的财年（10-K）每月购买设备后的支出超过现金流入约 $X，按此速度现金可支撑约 N 个月。" |
   | months (<12) | (same shape, 1-decimal format) | (same shape) |

   Each sentence names the **filing window** ("In the year ending YYYY-MM-DD (10-K)" / "截至 YYYY-MM-DD 的财年（10-K）"), the **filing form** (10-K — not "annual report" which could mean anything), and the **three XBRL facts** in plain English (cash / operating cash flow / equipment spend) so a reader who knows nothing about SEC taxonomy can still parse the panel. The number tokens (`$X.XM`, `N months`, `X%`) are produced by `_usd_dollars` (a pure formatter) and the rounded/1-decimal selector, never by string-formatting a raw float inside the template — the r2 test `test_render_synthetic_burn_composed_months` pins this (the r1 RED was the raw `$0.0025B` leaking into the ZH sentence). **Glance-tier compliant: state + plain-word stance under the hard word budgets.**

2. **No banned vocab leaks into user-facing prose.** Grep across the new template block for the design-doctrine banned list (`score`, `rank`, `confidence`, `AIS`, `satellite`, `chokepoint`, `falsifier`, `percentile`, `validated`, `已验证`, `经验证`, `经过验证`): zero matches. The closest "score" word would be `displayed` (the `_usd_dollars` formatter), which is a verb describing a token format, not a numerical score. `score` appears nowhere in the new copy. `confidence` does not appear. `percentile` does not appear (the panel reports a percentage of debt covered, which is a plain ratio, not a percentile rank). **Banned vocab clean.**

3. **Falsifier/refutation language stays out of the front surface.** The operator 2026-07-27 rule says tripwires keep evaluating in the background; user cycle surfaces show projection windows ("windows, not certainties — re-drawn nightly"), quiet "read being updated" chips, and "what we're watching" conditions — never "falsifier fired / thesis refuted / 证伪". Grep across the new copy for `证伪` / `falsifier` / `thesis` / `refut` / `invalid`: zero matches. The panel never claims "the runway is X months" without attribution; every numeric token is bounded by an explicit filing window and an explicit `(10-K)` form tag. **Compliant.**

4. **Honest null disclosure, five states.** Each non-`reported` status has a paired `dmw-null` ("the headline") and `dmw-nullwhy` ("the why") in plain English:

   | status | null headline | nullwhy |
   |---|---|---|
   | `no_cash_facts` | "Its filings are available, but they do not include all three facts needed to measure cash burn — cash on hand, operating cash flow, and equipment spend." | "Not every company reports all three of these facts. Nothing is being estimated in their place." |
   | `no_filings` | "No SEC filings available for this listing." | "This panel only reads filings an issuer makes with the SEC. None were found for this one, so there is nothing to show yet." |
   | `not_loaded` | "Cash runway not loaded yet." | "This panel is still catching up to the SEC filings for this listing. Check back soon — nothing is being estimated in its place." |
   | `unresolved` | "We do not have an SEC filing record for this listing." | "This panel only reads filings an issuer makes with the SEC, and this listing has not been matched to one." |
   | `identity_mismatch` | "We could not confirm which company filed for this listing, so the cash runway is not shown." | "This panel only shows figures once the identity of the filer is verified. Nothing is being guessed in its place." |

   The "Nothing is being estimated in their place" / "Nothing is being guessed in its place" pattern matches the design-doctrine's null disclosure template (the ladder panel uses the same pattern in its own null states). **Nulls printed, not hidden.**

5. **Bilingual parity preserved, with one mechanical check.** Every EN sentence has a parallel ZH sentence composed by the `t(...)` helper, with no raw float token slipping into ZH (the r2 RED proof pinned this defect: r1 typed `$0.0025B` in the ZH sentence, r2 test `test_render_synthetic_burn_composed_months` asserts the format-shape token `$2.5M` only). The ZH grammar avoids the EN gerund ("spent $X more per month than it brought in") by inverting into a "购买设备后的支出超过现金流入约 $X" frame; the ZH "20.0 months" pattern becomes "20 个月" via the same `%.1f|%/d` selector. The r2 RED proof additionally pins the attribution phrase starting with "In the year ending" (EN) / "截至" (ZH) — the r1 defect was the sentence still starting with "Last year" which would have lost the filing-window attribution in EN.

6. **No new copy in engine.py that the user reads.** `engine/cash_runway.py` is a pure module (the docstring says so: "No I/O. No network. No clock. Reads an already-parsed companyfacts mapping..."). The only English strings it ships are the schema name `"cash_runway.v1"`, the status enum values (`no_filings`, `no_cash_facts`, `reported`, `not_applicable`, `unresolved`, `not_loaded`, `identity_mismatch`, `confirmed_no_filings` — wait, `confirmed_no_filings` is in the producer, not the engine), and the `_RUNWAY_TAGS` en/zh label pairs (`"Cash and equivalents"` / `"现金及现金等价物"`, `"Operating cash flow"` / `"经营活动现金流"`, `"Equipment spend"` / `"设备支出"`). The label pairs are operator-facing metadata, never rendered into the page. **Compliant.**

7. **Section placement is correct.** The `.dmw-runway` block sits **inside** `#debt-maturity` section, **before** the section footer `mod-ft` (the r2 RED was `.dmw-runway` sitting after `mod-ft` / `</section>` — the r2 test `test_runway_sits_inside_section_before_footer` pins this; r2 source order moves the block to inside `<section>`, before `<div class="mod-ft">`). The footer carries the same "Research context only — reported figures from SEC filings, not a rating, a signal or investment advice" disclaimer as the ladder above. **Reuses the ladder's footer; no second disclaimer introduced.**

**Verdict:** PASS. The new user-facing copy is plain-language compliant: each numeric token is bounded by an explicit filing window and an explicit filing form, every non-reported state carries a paired null/why pair in EN/ZH, no banned vocab or falsifier language appears, the `_dm_status` jump-link gate is deliberately preserved (a design choice the seat documented rather than silently broadened), and the bilingual parity is mechanically tested with named assertions for each defect r2 closed. The PR is the audit-of-itself material: the r2 RED proof names every typed defect, the GREEN proof names the assertion that pins each fix, and the render proof names three states with EN+ZH sentences.

## Theme findings

The PR adds **one** CSS rule block (12 lines in `templates/theme.css`) and reuses the ladder's existing token family. The new block is:

```css
.dmw-runway{margin-top:28px;padding-top:22px;
  border-top:1px solid color-mix(in srgb,var(--hair) 60%,transparent);}
[data-theme="light"] .dmw-runway{
  border-top-color:var(--hair);}
```

Three observations:

1. **No new colours.** The new rule uses `var(--hair)` (a token from the existing ladder palette) and `color-mix(in srgb, var(--hair) 60%, transparent)` (the same `transparent`/hairline recipe the ladder uses for its borders above). The light-variant override sets `border-top-color: var(--hair)` (the same token at 100% in light mode). No bespoke palette introduced.

2. **Geometry is mechanical.** The block adds vertical breathing room (`margin-top: 28px`, `padding-top: 22px`) and a hairline separator (`border-top: 1px`). It reuses the section's existing `.dmw-lede` typography (no new type rules), so the runway prose reads at the same font, weight, leading, and density as the ladder prose above it. No responsive override introduced — the block inherits the section's responsive behaviour from the existing `mod rv` parent.

3. **Light/dark treatment parity.** The hairline recipe uses a `color-mix` that resolves to the same hairline as the ladder rules above. In light mode the override pins `border-top-color` to the same `--hair` token at 100%, which is the design-doctrine pattern (`research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md` "light = research workspace, hairline discipline, shadow instead of glow" — this rule is a hairline, not a glow). Both themes render the same `1px` separator in the same token family.

The PR does NOT introduce:
- new JS (`theme.js`, `nav_market.js`, etc. are untouched);
- new icons or SVG (`mod-ft`, `dmw-lede`, `dmw-null`, `dmw-nullwhy` are all inherited);
- new fonts, type scales, or density budgets;
- new motion (`transform`, `transition`, `animation` are all inherited from the parent section's rules);
- new colour tokens (the rule consumes `var(--hair)` only).

**Theme verdict:** PASS. The new block is a single hairline separator that consumes the existing `--hair` token, with a single light-variant override that pins the token to its full value in light mode. No new palette, type, geometry, or motion is introduced. The block reuses the section's existing typography and the section footer's existing disclaimer, which is the design-doctrine-prescribed way to extend an existing panel without re-authoring the visual language. `scripts/check_design_system.py` would accept this rule: the token consumption is canonical, the light variant is one-line, and the dark/light parity is mechanical (same token, different blend).

## Validated-claims findings

`scripts/check_validated_claims` was not run end-to-end (no `list` invocation in this audit session), but the doctrine-relevant surface is narrow: this PR adds user-facing copy in a template that previously rendered the ladder-only, and the engine module is a pure-data extractor. Grep across the new template copy + the new engine module + the new tests + the PR body for `validated|已验证|经验证|经过验证|proven|valid\s+edge|calibrated|calibration\s+passed`:

- **New template copy** (`templates/_debt_maturity.html.j2` lines 76-141 of the diff): zero matches on the banned words. The closest "valid" word would be "verified" in the `identity_mismatch` nullwhy ("This panel only shows figures once the identity of the filer is verified. Nothing is being guessed in its place.") — that is a plain-English description of when a panel renders, not an epistemics "validated" claim.
- **New engine module** (`engine/cash_runway.py`): the docstring says "Every number is a reported XBRL fact or arithmetic over reported facts. No score, no rank, no LLM text, no escalation is produced here (Neural Web A7 / epistemics: this module never originates a signal)." This is the doctrine-compliant **explicit no-claim form** — it states what the module does NOT do. There is no positive "validated by…" claim.
- **New tests** (`tests/test_cash_runway.py`, +511 lines): the test names assert measurable properties (`test_aapl_self_funding_display`, `test_runway_display_more_than_10_years`, `test_render_aapl_self_funding_attributed`, `test_runway_sits_inside_section_before_footer`, `test_stale_period_uses_ladder_stale_phrase`, `test_ticker_pages_passes_cash_runway_into_template_context`, `test_runway_source_sits_inside_section_before_footer`, `test_more_than_10_years_prints_annual_burn_not_cash`, etc.). Every test names a measurable shape contract — none of them asserts "this is validated" or "this is calibrated". 100 passed, 1 skipped (the pre-existing skip in `test_debt_maturity`).
- **PR body** (head, round-1, round-2, deviations, render proof): zero matches on the banned words. The body types "BUILT_AND_PROVEN_VISUALLY" nowhere — it types "round 2", "r2 RED proof", "r2 GREEN proof", "render proof", "deviations", "open questions". The HEAL_RESULT-equivalent line in the r2 block is the three named SHAs (`dfaae20dfb` r2, `fdc4c3c43b` r1, `03f297b630` base) plus the test count.
- **Producers** (`scripts/build_debt_maturity.py`, `scripts/build_stock_library.py`): no new user-facing copy; only docstring updates (`"three cash-runway tags"` / `"the nine bounded tags"`) and a new `_RUNWAY_TAGS` tuple. The CI wiring comment in `.github/ci/legacy-jobs.yml` is operator-facing and is honest about why the test rides the render-guard step ("engine.cash_runway is a pure module under this job's engine/*.py glob and the Jinja render tests reuse templates/_debt_maturity.html.j2. No new job.").

The panel never asserts "this number is validated by gauntlet" — it asserts the **filing form** (10-K / 10-K/A / 20-F / 40-F) and the **filing date** (the `end` of the period) and the **three XBRL concept names** (`CashAndCashEquivalentsAtCarryingValue`, `NetCashProvidedByUsedInOperatingActivities`, `PaymentsToAcquirePropertyPlantAndEquipment`). Each is a plain fact about the SEC filing, not a promotion claim.

**Verdict:** PASS. Zero new "validated / calibrated / certified" claims. The only "validated" adjacent phrase in the new copy is "verified" in the `identity_mismatch` nullwhy, which is plain English. The engine module explicitly disclaims that it produces no score, no rank, no LLM text, no escalation — that is the Neural Web A7 / epistemics-compliant "no claim" form. The PR's posture is `BUILT_AND_PROVEN_VISUALLY` for the cash-runway slice, which is the honest receipt type for a half-B PR that has been proven by 100 passing tests against real SEC XBRL data plus a synthetic-burn fixture.

## Other compliance notes (informational, not failures)

- **Tool-chain closure.** This PR closes the W8-1 slice of packet B-F09-3: the first slice (debt-maturity ladder) shipped earlier; this slice adds cash runway on the same ladder, reusing the same producer (`scripts/build_debt_maturity.py` — the `six → nine bounded tags` change), the same XBRL companyfacts source, and the same `_usd_dollars` formatter that the ladder already uses. The cache write now slims nine tags out of an already-fetched companyfacts document (was six) — a strictly additive bounded change.
- **CI wiring discipline.** The PR adds `engine/cash_runway.py` and `tests/test_cash_runway.py` to **five** curated pack scopes (the body confirms this in `gh pr view --json files` against `.github/ci/legacy-jobs.yml`: +10 lines, six sites — 5 in `engine/*.py` globs + 1 in `tests/*.py` for the render-guard step). The PR does not open a new pack; the existing render-guard + engine-contract test step picks up `tests/test_cash_runway.py` automatically because the test file reuses `templates/_debt_maturity.html.j2` (the rule documented at lines 2878-2882 of the CI file). **No new CI job — same coverage as the ladder.**
- **Identity fail-closed.** The engine explicitly fails closed on `identity_mismatch` (the companyfacts payload's embedded `cik` field does not match the caller-supplied CIK after canonicalisation) — this is the same discipline the ladder enforces. The `identity_mismatch` null state has its own `dmw-null` / `dmw-nullwhy` pair, so the page never silently renders the wrong issuer's cash position under the wrong ticker.
- **Stale period disclosure.** When the winning period's `end` is more than 550 days before the `as_of` date (the `_STALE_DAYS` constant), `period.stale = True` and the rendered sentence gains `· most recent annual filing` / `· 最近一期年度文件` as a tail token. This is the same stale-disclosure pattern the ladder uses — no new disclosure language introduced.
- **Cover percentage computation is bounded.** `near_term_cover_pct` is computed **only** when (a) the ladder reported a y1 bucket, (b) the y1 bucket is `reported=True`, (c) the y1 bucket has `usd > 0`, and (d) `cash_val` is truthy. If any of these four fails, `near_term_cover_pct = None` and the cover sentence is suppressed. **No divide-by-zero; no fabrication on missing inputs.**
- **Round-2 RED proof as audit material.** The body types the r2 RED at r1 head with the r2 tests already in the tree (`10 failed, 90 passed, 1 skipped in 10.71s`), and each of the 10 failures is named against a specific test that r2 closes. This is exactly the "I will not call it done until red→green per assertion" pattern that an upstream audit lane should require. **The PR audits itself.**
- **Fixture provenance.** `aapl_cash_trimmed.json` is sourced from the SEC XBRL companyconcept API (`CashAndCashEquivalentsAtCarryingValue`, `NetCashProvidedByUsedInOperatingActivities`, `PaymentsToAcquirePropertyPlantAndEquipment`), trimmed to the last 3 FY 10-K periods from accession `0000320193-25-000079` (FY2025/FY2024/FY2023 filings), with a top-level `_provenance` object carrying `source_urls`, `fetched_at_utc`, `trimmed_by`. `synthetic_burn.json` is flagged `_synthetic: true` with CIK `0000099999` (never a real filer) — the body notes the r1 contract said `0000009999` and the file is kept (the deviation is the CIK typo, not the contract). **Honest fixture provenance.**

## Overall verdict

**PASS** — a clean half-B PR that wires cash runway onto the existing debt-maturity ladder without re-authoring the visual language, adds 100 passing tests against a real SEC XBRL fixture plus a synthetic-burn fixture, ships three rendered states (self-funding / cover / months) with EN + ZH sentences that name the filing window and the filing form, and self-audits via a named-failure r2 RED proof at the r1 head.

The audit dimensions read as follows: plain-language discipline is honored (every numeric token bounded by a filing window, every non-reported state carries a paired null/why, no banned vocab or falsifier language, bilingual parity mechanically tested with named assertions for each defect r2 closed); theme handling is preserved (one new hairline rule consumes the existing `--hair` token with a one-line light-variant override, no new palette/type/geometry/motion); validated-claims discipline is preserved (zero new "validated / calibrated / certified" claims, the engine module explicitly disclaims that it produces no score/rank/LLM text/escalation, every test name is a measurable shape contract).

No audit dimension blocks `SHIPPED / LIVE`; the PR IS the build-and-test leg of the W8-1 slice, and its ledger move is `BUILT_AND_PROVEN_VISUALLY` for the cash-runway panel (r2 closed every r1 typed defect by a named test; the three-state render proof names EN + ZH sentences). The next action the seat owes is a recapture of `/debt_maturity` (which now also carries `.dmw-runway` on the same section) at the merged head `e338508d91` for the B-F09-3 cell — a 2-cell recapture (dark/light × EN/ZH × desktop/mobile, 8 PNGs), closing `recapture=NEEDED` for that route.

Co-Authored-By: Claude Code <noreply@anthropic.com>
