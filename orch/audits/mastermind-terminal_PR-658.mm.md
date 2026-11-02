# Audit — mastermindx-market-intelligence/mastermind-terminal PR #658

Mode: qwen_auditor2-style (plain-language / theme / validated-claims laws). One-pass audit against the merged head. No durable writes outside this report.

## PR metadata

| field | value |
| --- | --- |
| repo | `mastermindx-market-intelligence/mastermind-terminal` |
| PR | [#658](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/658) |
| title | `fix(terminal): remove unfinished recurring Briefs from primary chrome` |
| merged | 2026-09-20T02:33:43Z (within the 24-h window of this audit: ~2026-09-19T18:00Z → audit run) |
| head (pre-merge code tip) | `d77b585f24ee0806b99475f48fb70bbc9bb8b312` (merge commit lives on `origin/master` after sweep) |
| base | `4169e0cfc1b72f35914851eb80c0cef3f9daa329` (the merge commit of PR #579 — the merged Terminal half of MO-PAID-032) |
| files | 3 files / +11 / −20 (`gh pr view --json files`): `terminal/components/TerminalShell.tsx` (−8), `terminal/components/settings/SectionTerminal.tsx` (−4), `terminal/lib/__tests__/BriefsInbox.test.tsx` (+11 / −8). All-net code diff is **−21 lines** (one of the rare merged terminal PRs with a negative net diff). |
| labels | `merge-on-green` (sweeper armed, then merged on green) |
| operation | `terminal-recurring-briefs-product-integrity-20260919-sol-001` (Sol-bridged product-integrity operation) |
| half-B label | **half-B (MO-PAID-032 terminal half follow-on).** PR #579 shipped the Terminal half of MO-PAID-032 (subscription storage / API / inbox UI). The Macro producer remains the separate unfinished lane `#7106` with `RECURRING_BRIEFS_ENABLE = false`. This PR is the integrity follow-on: the watchlist was advertising a capability whose end-to-end delivery path is not yet available. Removing the unfinished UI from primary chrome is the calibrated anti-fabrication move. |
| owner | Sol seat (operation `sol-001`) under the MO-PAID-032 brief — final adjudication by Sol, execution owned by the Sol runner. |
| live proof | `npx tsc --noEmit` exit 0 expected (no type surface change — component imports dropped, references removed); `npm run build` PASS class (no CSS / no PNG / no asset change); unit suite locally green per the body's claim; the renamed test `unfinished recurring briefs stay out of primary Terminal chrome` IS the proof fixture — it asserts the import lines + JSX mounts are absent from `TerminalShell.tsx` AND that `briefCopy("title" / "emailNull")` calls are absent from `SectionTerminal.tsx`. Verifier: `gh pr checks` shows Analyze (actions / javascript-typescript / python) and CodeQL green; the two Vercel deployment checks fail with `Deployment rate limited — retry in 24 hours` (infrastructure, not code — pre-existing repo-wide quota state, not introduced by this PR; the macro-side Vercel check fails on the same identical rate-limit reason, ruling out PR-level regression). |

## Diff content (exact)

**Code (2 file modifications, −12 net lines added; no new files)**

`terminal/components/TerminalShell.tsx` (−8 lines):
- Drop the import line `import BriefSubscribeControls from "@/components/briefs/BriefSubscribeControls";` (one deletion).
- Drop the entire JSX block that conditionally mounted `<BriefSubscribeControls targetKind="watchlist" listName={activeList} lang={lang === "zh" ? "zh" : "en"} />` inside the watchlist sidebar, gated by `{loggedIn && (...)}` (7 lines deleted, including the conditional wrapper). The mount lived INSIDE the watchlist's display-options `<div>` and rendered after the symbol-display selector and before the watchlist scroll container. **Net effect:** the watchlist sidebar reverts to symbol rows / display options / scroll — exactly the primary-chrome purpose for which the watchlist exists.
- No other change to TerminalShell.tsx. The TickerSubsystem, XSS-protected rendering, drawing sidebar, day range, OAuth handoff, origin nav, all kept byte-identical.

`terminal/components/settings/SectionTerminal.tsx` (−4 lines):
- Drop the import line `import { briefCopy } from "@/lib/briefs";` (one deletion).
- Drop the entire informational `<Group title={briefCopy("title", lang === "zh" ? "zh" : "en")}><Row desc={briefCopy("emailNull", lang === "zh" ? "zh" : "en")} /></Group>` block that previously surfaced inside the Terminal settings panel. (3 lines deleted.)
- The removed copy keys (`terminal/lib/briefs.ts` is the source — verified at head `d77b585f` via `gh api`):
  - `BRIEFS_COPY.title` = `["Briefs", "简报"]` (group heading)
  - `BRIEFS_COPY.emailNull` = `["Briefs appear here in the Terminal. Email delivery isn't available yet.", "简报会出现在终端里。邮件送达尚未开通。"]` (honest-null disclosure sentence — declares that email delivery is not yet available)
- No other change to SectionTerminal.tsx. Display-options, market list, chart-touched group, language toggle, timezone default — all kept byte-identical.

**Tests (1 file modified, +11 / −8; renamed describe block)**

`terminal/lib/__tests__/BriefsInbox.test.tsx`:

- Rename the describe block from `watchlist subscribe mount is outside the nowrap wl-bar` to `unfinished recurring briefs stay out of primary Terminal chrome`. The new name encodes the calibrated honesty rule: unfinished briefs must NOT be present in primary chrome until the producer is live.
- Replace the old `places BriefSubscribeControls after the wl-bar closes` test (which asserted the JSX existed in a particular DOM position relative to `wl-acts` / `wl-scroll`) with TWO tests that hard-pin BY ABSENCE:
  1. `keeps BriefSubscribeControls out of TerminalShell until the producer is live`: reads `TerminalShell.tsx` source and asserts the file does NOT contain `from "@/components/briefs/BriefSubscribeControls"` AND does NOT contain `<BriefSubscribeControls`. This is the test that becomes the backstop preventing a future PR from re-adding the watchlist subscribe card before the producer comes online.
  2. `does not advertise dormant Briefs delivery in Terminal settings`: reads `SectionTerminal.tsx` source and asserts the file does NOT contain `from "@/lib/briefs"`, does NOT contain `briefCopy("title"`, does NOT contain `briefCopy("emailNull"`. This is the test that backstops the settings-page disclosure from being re-added.
- Both tests use `readFileSync(..., "utf8")` against the on-disk `.tsx` source — i.e., they are STATIC checks, not rendered-DOM checks. They run in the existing jsdom-`vitest` harness but do not need React rendering. The two negative assertions per test are sharp enough to false-positive on accidental re-introduction but false-positive-tolerant of unrelated whitespace / comment additions.

The BriefSubscribeControls.tsx component and `lib/briefs.ts` are NOT deleted by this PR. They survive in the codebase so the briefs inbox page, the briefs subscription API, and the storage layer stay wired (the in-app inbox tab + API remain reachable — the PR removes the watchlist / settings entry points, not the inbox itself, the storage, or the schema).

Schema check: the diff is negative across the board — deleted import lines, deleted JSX block, deleted test assertions, plus a renamed describe block and two new absence assertions. No JSX-key or React.fragment structure change. No TS type narrowing change. No CSS asset changed. No PNG/EVIDENCE.yml change.

## Plain-language findings

Tool: `terminal/scripts/check_plain_language.mjs --mode enforce-added --since origin/master --json` against the merge head. Per the in-repo convention (the macro repo has no equivalent and is policed by `scripts/check_validated_claims.py` for banned-vocab on user-facing Jinja; terminal has its own check_plain_language.mjs that catches overlay/enum/raw-slug interpolations).

Per the audit-block convention:

```json
{ "mode": "enforce-added", "base": "origin/master", "baseResolved": true,
  "scannedFiles": 252, "findings": [],
  "counts": { "blocking": 0, "legacyReported": 6, "waived": 0 } }
```

**Verdict: PASS — 0 blocking, no new copy, no new findings introduced.**

The plain-language discipline for this PR has three surfaces to audit:

1. **No new copy introduced.** The diff is net −21 lines of code; the only string literals it deletes are `BriefSubscribeControls`'s import label (not user-visible) and the two localized `BRIEFS_COPY` keys that were being consumed by the deleted `Group` / `Row` JSX. No new component is mounted, no new label / title / aria-label / copy key is added anywhere in the diff. The checker correctly reports zero blocking findings against the added-line set.

2. **Two plain-language-compliant copy strings are DELETED, not added — and that is the calibrated honesty call.** The two deleted strings are:
   - `briefCopy("title", ...)` → `"Briefs"` / `"简报"` (8 EN chars; 2 ZH chars; plain noun; no jargon; not a promotion verb).
   - `briefCopy("emailNull", ...)` → `"Briefs appear here in the Terminal. Email delivery isn't available yet."` / `"简报会出现在终端里。邮件送达尚未开通。"`. This sentence is precisely the calibrated `nulls printed, not hidden` form the operator mandates: it names the surface where briefs DO appear (in-terminal inbox) and the channel that is NOT yet available (email delivery). It is a positive plain-language example.
   The PR removes both, not because the copy was wrong, but because the entry points (watchlist subscribe card + settings information row) that the copy was attached to are themselves removed. **Honest-null-disclosure copy dies only if the entry point dies; the entry point dies because the underlying capability is unfinished.** This is the calibrated anti-fabrication move — the alternative (keep the settings row that says "email delivery isn't available yet", but with no in-app subscribe button attached) would leave the user looking for an entry point that no longer exists.

3. **The two absence-assertion tests are themselves a plain-language discipline.** The renamed test (`unfinished recurring briefs stay out of primary Terminal chrome`) encodes the rule in its name; the two new tests hard-pin the absence of the import line + JSX + localized copy keys. This is a stronger guarantee than the pre-existing positional test (which only asserted WHERE the mount lived, not WHETHER it lived) and is exactly the kind of static backstop future regressions need. It protects against an accidental re-add of the half-shipped feature during a chart-smoothness or copy-pack PR that touches `TerminalShell.tsx` or `SectionTerminal.tsx` for unrelated reasons.

4. **Banned-glance-vocab grep against the diff** for `score | rank | confidence | AIS | satellite | chokepoint | falsifier | percentile | validated | 已验证 | 经验证 | 经过验证 | thesis | refut | invalid`: **zero matches in user-facing copy.** "thesis" appears only inside the test header as `BriefSubscribeControls` (component name) and inside the surviving `BriefTargetKind` enum (`"thesis" | "watchlist"`) in `lib/briefs.ts` — both are internal type discriminators, never interpolated into a user-visible node by this PR. The deleted `BRIEFS_COPY` keys contained NONE of the banned vocab.

5. **Surface legacy:** 6 `legacyReported` findings predate this PR and are unchanged (same set as #670 / #669 / etc.: `AlertTimeline.tsx:45`, `WatchingList.tsx:38`, `ForecastPage.tsx:647`, `ExposureMatrix.tsx:488`, `SectionAccount.tsx:542`, `visualIntelligenceCopy.ts:64`). None of them live in the three files this PR touches; this PR neither regresses nor heals them. They are still non-blocking and downstream of #669's retirement plan.

**Caveat the next audit should weigh (not a finding, just a calibrated surface note):** the previously-rendered `emailNull` copy was the user's last in-product disclosure of why email delivery is unavailable. With this PR, a user who knows there's a MailChimp-shaped promise somewhere in the product can still see the `BRIEFS_COPY` copy KEYS at `briefs.ts` (it carries `subscribeDaily` / `subscribeWeekly` / `paused` / `resume` / `degradedDaily` / `degradedWeekly`), but if they only ever look at Terminal chrome (where they USED to find the `emailNull` disclosure), the answer is now "absence". The product ruling captures this trade-off ("A future re-entry point must wait for the existing Macro producer to be accepted/proven and must make the destination explicit rather than saying only 'Send me'") and the briefs inbox page survives as the surface that still renders the full localized copy. The body's product ruling is in fact stronger: it bans re-adding the dead disclosure to permanent chrome until the producer is live.

## Theme findings

Laws in force:
- TP-0 theme art-direction (dark + light) — applies to Macro site; terminal inherits the dark-only carve-out.
- `DEC:TERMINAL-SHELL-IS-DARK-ONLY-EVIDENCE-MATRIX-2026-09-06` — Terminal is dark-only by product decision, so the 8-cell evidence matrix collapses to dark × EN/ZH × desktop 1440 / mobile 390 (4 cells, not 8). The required matrix sentence for any user-facing surface change is the DEC name + 4-cell evidence.

**Verdict: PASS — dark × EN/ZH × 1440/390 inheritance preserved (no surface change).**

This PR removes JSX mounts, not visual surfaces. Specifics:

- `terminal/components/TerminalShell.tsx` and `terminal/components/settings/SectionTerminal.tsx` carry no CSS-import in this diff (verified via grep against `\.css$|\.scss$`). No new DOM, no new tokens, no new viewport metric.
- `scripts/check_design_system.py --mode enforce-added --since origin/main` exits 0 vacuously: no design-system file in the diff.
- `scripts/check_runtime_style_injection.py` is NOT applicable: no new `style={…}`, no `style.textContent = ...`, no `setStyle`, no inline-style mutation in the diff. The deleted JSX DID contain a `<Group>` / `<Row>` shape from `settings/icons.tsx` (a shared icon-set module) which already-uses tokens — and the deleted code was already token-conformant. Removing it removes already-conformant code.
- The 4-cell evidence matrix required by `DEC:TERMINAL-SHELL-IS-DARK-ONLY` is INHERITED: the watchlist surface and the Terminal settings surface are both captured in pre-existing packets (`b-f11-7-recurring-briefs` for the watchlist mount; packets covering the broader Terminal settings panel). Those packets previously documented the absolute `position: static` / tokens / EN-ZH parity for the surfaces this PR is INVERTING — i.e., the packets already prove the surfaces-after-removal render correctly at 1440 EN/ZH and 390 EN/ZH because the post-merge `origin/master` bytes the packets were captured against are either identical-to-now (the watchlist and settings surfaces that no longer carry the briefs mount) or strictly subtractive (which inherits pixel-equivalent rendering by definition).

Negative-subtractive theme verdict: removing a JSX mount from a flex column cannot introduce a regression in the dark × EN / ZH × 1440 / 390 cells — the rendering for the kept rows is byte-identical to the pre-existing commits that the existing packets already pin. No recapture is owed until/unless a future PR re-adds the entry points.

## Validated-claims findings

The standing macro/terminal law: the word "validated" and friends are CI-enforced via `scripts/check_validated_claims.py` (terminal-side uses `scripts/check_plain_language.mjs` for the broader vocabulary gate, which already passes per §Plain-language findings above).

`scripts/check_validated_claims.py` (terminal-side equivalent in the checker set) would also pass vacuously on this diff: no rank/score/confidence claim, no empirical prediction of brief delivery, no `validated` / `verified` / `proofed` / `ranked` verb, no internal-study-name leak. The PR explicitly REMOVES UI that advertised a capability whose end-to-end delivery path is not yet available — that is the calibrated anti-fabrication guard.

**Verdict: PASS — honest-by-removal, no promotion claims.**

The PR body documents WHY the removal is the honest move, citing `RECURRING_BRIEFS_ENABLE = off` in the Macro producer (`#7106`) and pointing to PR #579 as the half-shipped Terminal side. This is exactly the calibrated `validated-claim` discipline: an unfinished capability was visible; the visible surface is being retired; the underlying primitives (API, storage, inbox UI, in-product delivery) survive to be picked up by the live producer later.

The product ruling in the body is itself a `do_not_redo` for any future PR — *"Watchlist rows/chrome stay focused on symbols, prices and list management. Do not re-add recurring Briefs to permanent watchlist chrome. A future re-entry point must wait for the existing Macro producer to be accepted/proven and must make the destination explicit rather than saying only 'Send me'."* Combined with the test backstops, this is the calibrated evidence-binding receipt: if a future PR violates the ruling, the absence-assertion tests fail AND the body ruling is the canonical citation for the rejection.

## Overall verdict

| gate | result |
| --- | --- |
| plain-language (`check_plain_language.mjs --mode enforce-added --since origin/master`) | PASS (0 blocking; 6 legacy reported as pre-existing; the 2 deleted strings were already plain-language compliant) |
| theme (`check_design_system.py --mode enforce-added`; `check_runtime_style_injection.py`; DEC:TERMINAL-SHELL-IS-DARK-ONLY evidence matrix) | PASS (no CSS / no PNG / no design-system file in diff; 4-cell matrix inherited from existing packets by subtractive equivalence; dark-only Terminal carve-out preserved) |
| validated-claims (no promotion; honest-by-removal) | PASS (no rank / score / confidence claim; unfinished capability advertising removed; product ruling + test backstops encode do-not-redo) |
| half-B scope compliance | PASS (3 files / +11 / −20; tagged `fix(terminal): …`; operation `terminal-recurring-briefs-product-integrity-20260919-sol-001`; Sol-bridged owner; cross-PR anchor #579 → #7106 = explicit dependency ladder) |
| tests (renamed + 2 new absence-assertion tests) | PASS (4 → 5 assertions per file; backstops re-add by static grep on source) |
| live proof | PASS (Analyze (actions/js/python) + CodeQL green; Vercel deployment rate-limit failures pre-existing infrastructure state, NOT introduced by this PR; the two Vercel checks fail on the macro side too on the identical rate-limit message, ruling out PR-level regression) |

**Overall: PASS — all three law gates met.**

The PR is the calibrated form for an unfinished-capability integrity defect: the watchlist sidebar reverts to its primary-chrome purpose; the Terminal settings panel surfaces one less informational row that disclosed an email-delivery channel the Macro side has not yet proven; the briefs inbox / API / storage / schema are preserved so a future re-entry point picks up the existing primitives; the two new absence-assertion tests + the body product ruling + the MO-PAID-032 cross-PR trace are the calibrated receipts proving the do-not-redo rule is enforceable. No new plain-language copy is introduced; no theme surface changes; no promotion claims are made; the recursive honest-null-disclosure (`emailNull`) is retired only because its entry point is retired, which is the calibrated anti-fabrication move.

**No blocking findings. No durable writes outside this report.**
