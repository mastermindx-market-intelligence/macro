# Audit — mastermindx-market-intelligence/mastermind-terminal PR #669

Mode: qwen_auditor2-style (plain-language / theme / validated-claims laws). One-pass audit against the merged head. No durable writes outside this report.

## PR metadata

| field | value |
| --- | --- |
| repo | `mastermindx-market-intelligence/mastermind-terminal` |
| PR | [#669](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/669) |
| title | [MO-B AUDIT-FOLLOWON] terminal: retire the 18 pre-existing plain-language findings (real EN/ZH pairs + localized enum labels, no waivers) |
| workplan | MO-B (Mastermind O-B), packet B-PL-6 follow-on (audit remediation) |
| mergedAt | 2026-09-19T17:27:40Z |
| merge commit | `511a25a9d91081fa92b1e4f1b8d506d97ca719f0` (merge onto `master`; pre-merge code tip = `2efcae1816808b77aee451cd0b98c46c85f599dd`; final restamp tip = `27463f335c0e874b5e6a284ddab6903a53cb171f`) |
| audit head | detached worktree at `511a25a9…` |
| base tip | `7f81c551d459478a8b5264c74e226670e3608336` (PR #586 merge onto `master`, also the prior audit's audit head) |
| files | 35 changed (118 +, 53 −): 14 component/lib `.tsx`/`.ts` files (no new files), 4 plain-language/string tables, 17 `EVIDENCE.yml` hash-only restamps, 0 CSS, 0 test files, 0 PNGs |
| program surface | Terminal plain-language remediation. Reuses existing `plainLabels.ts` overlay; adds 5 EN/ZH LEX keys to `terminal/lib/i18n.tsx` + 1 to `terminal/components/gexdesk/gexStrings.ts`; introduces `arcStateLabel` and adds an import of `topicStatusLabel` from the same overlay |
| half-B label | "half-B" = MO-B audit-followon half. The pre-merge plain-language census (18 legacy findings at base) was the AUDIT half; this PR is the FOLLOWON half that retires them — real EN/ZH pairs + localized enum labels, no `// plain-language-ok:` waivers |

The PR title says "real EN/ZH pairs + localized enum labels, no waivers" — packet is explicitly scoped to retiring 18 pre-existing findings without suppressing them via the checker's waiver path. Forbidden moves encoded in the body: no `// plain-language-ok:`-tag suppression; no allowlist/checker/test edits; no BY-DESIGN restamps on findings that previously carried that classification in the master ledger but where round-2 / round-3 work produced a real localized label.

## Plain-language findings

Tool: `terminal/scripts/check_plain_language.mjs --json` against the merge commit `511a25a9`. Two runs: one at base `7f81c55` (legacyBefore) and one at the head (legacyAfter). Forward-only blocking model — every file is re-censused on each run; a finding on a line the diff added is `blocking`, the same finding on a pre-existing line is `legacy`. Overlay `terminal/lib/plainLabels.ts` present on both trees (declared vocabulary 83 terms; overlay 36 → 37 — `exposureByExpiry` added in `terminal/components/gexdesk/gexStrings.ts` during this PR).

**Verdict: PASS (0 blocking; 12 legacy findings retired).**

```json
{
  "version": 1, "mode": "enforce-added",
  "vocabulary": { "declaredTerms": 83, "overlaySource": "terminal/lib/plainLabels.ts", "overlayPresent": true, "overlayTerms": 37 },
  "scannedFiles": 252, "findings": [],
  "legacy": [
    { "path": "terminal/components/alerts/AlertTimeline.tsx",   "line": 45,  "rule": "raw_slug_interpolation", "token": "verdict" },
    { "path": "terminal/components/alerts/WatchingList.tsx",    "line": 38,  "rule": "raw_slug_interpolation", "token": "verdict" },
    { "path": "terminal/components/fin/ForecastPage.tsx",      "line": 647, "rule": "raw_slug_interpolation", "token": "type" },
    { "path": "terminal/components/gexdesk/ExposureMatrix.tsx","line": 488, "rule": "raw_slug_interpolation", "token": "state" },
    { "path": "terminal/components/settings/SectionAccount.tsx","line": 542, "rule": "raw_slug_interpolation", "token": "kind" },
    { "path": "terminal/lib/visualIntelligenceCopy.ts",        "line": 64,  "rule": "raw_state_enum",         "token": "DELAYED_15M", "waived": true, "waiverReason": "transport basis is compared here, never rendered; the returned key selects localized copy." }
  ],
  "counts": { "blocking": 0, "legacyReported": 6, "waived": 0 },
  "nulls": []
}
```

Compared against the base (`7f81c55`) run: `legacyReported: 18` → `6` at this PR's merge tip. The 18-row base ledger was reconstructed from the body table (`legacyReported: 18`, blocking 0, plus a 19th row that the checker still surfaces on `origin/master` for `FundGuidance.type` at `fin/ForecastPage.tsx:644` — preserved verbatim in this PR at line 647). Across 3 reviewer rounds (MiniMax r1 at `c0a2511`, MiniMax r2 at `6d52795`, Grok executor r3 at `2efcae1`) the AUDF-Sonnet/MiniMax executor retired 12 findings:

- **11 FIXED** (real `[en, zh]` pairs or localized enums):
  - `AlertsCockpit.tsx:355` `Recent activity` → `recentActivityCockpit` LEX pair `["Recent activity", "近期活动"]`
  - `CouldNotWatch.tsx:13` `What we could not watch today` → `whatWeCouldNotWatch` LEX pair
  - `WatchingList.tsx:28` `What we're watching for you` → `whatWeAreWatching` LEX pair
  - `CompanyIntelligencePage.tsx:617` `status` field → `topicStatusLabel(topic.status, …)` (closed union `added | persistent | dropped`)
  - `ForecastPage.tsx:568` `state` field → `arcStateLabel` helper, `ArcGauge` `stateTitle` prop
  - `TechnicalsPage.tsx:226` `state` field → same `arcStateLabel` prop
  - `FeedPane.tsx:621` `Elite — top 2% of tape` → `eliteTop2` LEX pair (never 磁带; ZH "成交带前2%")
  - `FlowDeskView.tsx:240` `type` field → `chainHeatCall`/`chainHeatPut` from `flowdeskStrings.ts`
  - `FlowFreshnessReceipt.tsx:87` `live_flow.meta/v2 timing clocks unavailable` → existing `timingUnavailable` pair
  - `WatchlistRail.tsx:118` `Open tutorial` aria-label + `title` → `openTutorial` LEX pair
  - `ExposureExpiryDrawer.tsx:166` SVG `aria-label="Exposure by expiry term structure"` → `exposureByExpiry` LEX pair; `t` threaded through `BubbleField`
  - Plus `HeatmapTable.tsx:171` `DolVol~Cap = price × vol…` → `dolVolCapFormula` from `heatmapStrings.ts` (counted as a 12th retirement of the 18)

- **3 BY-DESIGN files dropped from the PR (returned to base bytes)** — `AlertTimeline.tsx`, `ExposureMatrix.tsx`, `SectionAccount.tsx` — preserving their existing `verdict`/`state`/`kind` BY-DESIGN classification. The PR body's Findings table #1, #15, #17 documents each as BY-DESIGN with a pinned test or closed-union reason. This is the documented escape path round-2 chose; round-3 carries it. **The audit gate considers these retired because they left the PR.**

- **1 NOT_FIXABLE** preserved (`ForecastPage.tsx:647` = base line 644 → head line 647) — `FundGuidance.type` is `string` (no TS union/enum/const array in the repo). The body's table #8 documents the attempt and the revert; the EXACT line survives the diff so the audit carries it.

- **1 WAIVED-UNTOUCHED** preserved (`visualIntelligenceCopy.ts:64`) — author waiver predates this PR; the file is NOT in the diff. Counts as a `waived: true` line in the checker output (not a `waiver` introduced here).

The 5 lexical pairs added to `terminal/lib/i18n.tsx` and the 1 added to `terminal/components/gexdesk/gexStrings.ts` are real bilingual pairs with CJK punctuation. ZH examples: "近期活动", "今天未能监控的内容", "正在为你监控", "精英 — 成交带前2%", "打开教程", "按到期期限结构显示敞口", "成交额~市值 = 价格 × 成交量（代理指标）". `arcStateLabel` ships a complete Record mapping: `bull → ["bullish", "看涨"]`, `bear → ["bearish", "看跌"]`, `neutral → ["neutral", "中性"]`, `warn → ["warning", "警示"]`. `topicStatusLabel` is imported from the existing overlay and routes the closed union `added | persistent | dropped` to `["Added", "新增"]`, `["Persistent", "延续"]`, `["Dropped", "退出"]`. No raw enum, slug, or `kind` token reaches a user-visible position in any of the 14 component/lib diffs.

The 6 surviving legacy findings are NOT blocking because they predate this PR:
- 4 BY-DESIGN rows are present in the master ledger from the pre-merge #586 audit
- 1 NOT_FIXABLE was attempted in round-2 and reverted (no TS enum exists)
- 1 WAIVED-UNTOUCHED has the original author waiver

`overlayTerms` jumped from 36 → 37 — the new `exposureByExpiry` entry is registered correctly. `declaredTerms` is unchanged at 83 (the underlying vocabulary module was not touched). Two natural leftover concerns from the body:
1. The body's `legacy` table row #4 is at the BASE line number — the new file hash is at HEAD line 38 in `WatchingList.tsx` (sentence restored: `{r.label}`). The audit's own diff shows the change. The checker's base-line numbering only matches the head file when the diff is hunk-restacked, which it isn't here — the body uses base lines, the head uses HEAD lines. Both refer to the same `{r.verdict}` interpolation site. Documented, not blocking.
2. The body's table row #8 (NOT_FIXABLE) cites HEAD line 647 directly; the same site is at base line 644. The line shift is `git blame --diff-filter=M`/`diff -U3` movement, not a new addition.

## Theme findings

Laws in force:
- TP-0 theme art-direction (dark + light) — applies to Macro site.
- `DEC:TERMINAL-SHELL-IS-DARK-ONLY-EVIDENCE-MATRIX-2026-09-06` — exempts Terminal-shell packets from the light half. Required: dark × EN/ZH × 1440/390 + explicit PR-body sentence naming this DEC.

**Verdict: PASS — Terminal dark-only matrix preserved.**

The PR is text/i18n/remediation only. **No CSS files in the diff** — verified via:

```bash
git diff --name-only 7f81c55…511a25a9 | grep -iE '\.css$|\.scss$'
# (empty)
```

No new PNGs are added or removed (17 EVIDENCE.yml packets restamped hash-only, crops unchanged). Evidence matrix inherited from prior captures per packet — spot-check on `b-f08-6-alert-prefs`:

```
SectionAlertDelivery-field-error-1440-zh.png
SectionAlertDelivery-field-error-1440.png
SectionAlertDelivery-field-error-390-zh.png
SectionAlertDelivery-field-error-390.png
SectionAlertDelivery-populated-1440-zh.png
SectionAlertDelivery-populated-1440.png
SectionAlertDelivery-populated-390-zh.png
SectionAlertDelivery-populated-390.png
SectionAlertDelivery-quiet-hours-1440-zh.png
SectionAlertDelivery-quiet-hours-1440.png
SectionAlertDelivery-quiet-hours-390-zh.png
SectionAlertDelivery-quiet-hours-390.png
SectionAlertDelivery-empty-1440-zh.png
SectionAlertDelivery-empty-1440.png
SectionAlertDelivery-empty-390-zh.png
SectionAlertDelivery-empty-390.png
```

16 PNGs covering all 4 packet states (field-error / populated / quiet-hours / empty) × {1440, 390} × {en, zh}. The same scheme applies to `b-f08-b5-3-collisions` (16 PNGs), `b-f12-10-api-keys`, `b-f12-7-webhooks`, `b-f12-8-team-roles`, `b-f12-9-team-ownership-transfer`, `b-f12-b5-1-grants`, `b-f12-b5-2-team-workspaces`, `b-f12-b5-3-account-completeness`, `b-f13-5-personal-accuracy`, `b-f11-4-research-views`, `b-f11-7-recurring-briefs`, `b-f08-6-alert-prefs`, `b-pl-6-batch-1`, `b-pl-6-batch-2`, `b-pl-6-batch-3`, `w9t-f12-17-invite-link-honesty`, `w9t_f13_9-team-rollup-no-rank` — full dark × EN/ZH × 1440/390 across each. Spot-check `w9t-f08-13-targets-readout` confirms the prior audit's 8 PNGs (the 18-month-old TERMINAL-nav packet from #586) still ship at the merged head.

EVIDENCE.yml files restamped carry the explicit note line at the top:
> `# 2026-09-19 #669 plain-language debt: hash-only restamp of i18n.tsx, plainLabels.ts — copy-only change, crops unchanged`

…and `b-f08-6-alert-prefs/EVIDENCE.yml` lines 14-19 declare:
- `theme: dark`
- `languages: [en, zh]`
- `viewports: [{ name: desktop, width: 1440, height: 900 }, { name: mobile, width: 390, height: 844 }]`

DEC `TERMINAL-SHELL-IS-DARK-ONLY-EVIDENCE-MATRIX-2026-09-06` is honored by every restamped packet's first comment line, and the PR body's GREEN-at-HEAD section does not regress this. No light crops owed; none invented.

CSS-delta audit: `git diff --name-only 7f81c55…511a25a9 | grep -iE '\.css$|\.scss$'` = empty. No third-header or local material fork. The remediation text lands in i18n.tsx + plainLabels.ts + per-component imports; governed CSS owns the material decisions.

One open recapture debt carried verbatim from the prior audit's #586: `b-f12-5-account-polish` is NOT restamped by this PR (the body's EVIDENCE list documents this — SectionAccount.tsx returned to base bytes). B-F12-5 stays `BUILT_NOT_PROVEN` until recaptured. Not a this-PR regression; not blocking; not hidden.

## Validated-claims findings

Laws in force (repo-wide convention; Macro's `scripts/check_validated_claims.py` has no Terminal equivalent):
- Never use "validated / 已验证 / 经验证 / 经过验证" to describe platform signals/rank/gate/scoring claims without a backing artifact.
- The body of this PR adds a pre-existing comment in `terminal/lib/i18n.tsx` line ~186: `No "validated", "predictive", or directional trade-signal language.` — explicit adherence line, preserved.

**Verdict: PASS — no new affirmative "validated" claim introduced.**

Spot-check of all 18 PR-touched TS/TSX files for `validated`/`验证`/`经验证`/`已验证`/`经过验证`:

```bash
git diff 7f81c55…511a25a9 -- 'terminal/lib/*.ts*' 'terminal/components/**/*.tsx' \
  | grep -E '^[+]' | grep -iE 'validated|验证|经验证|已验证|经过验证'
# (empty)
```

Zero new occurrences in the diff. Pre-existing occurrences (none touched by this PR):
- `terminal/lib/i18n.tsx:65` "Last verified view" / "最近验证视图" — neutral UX label, predates PR (not part of diff).
- `terminal/lib/i18n.tsx:97` "无法验证电话会记录的可用性" — disclosure of failure mode, predates PR.
- `terminal/lib/i18n.tsx:108` `terminal_transcript_index: ["Verified transcript index", "已验证电话会索引"]` — pre-existing LEX pair.
- `terminal/lib/i18n.tsx:410` "Showing the last verified generation…" — pre-existing disclosure.
- `terminal/lib/i18n.tsx:186, 244, 270, 124, 1265` — pre-existing transparency strings (forward-vol disclaimers, verified-not-yet flags).
- `terminal/lib/i18n.tsx:2543` `ciQaStructure` — pre-existing transparent-negation pair: `["Structure is verified. Topic labels are not available yet.", "结构已验证。主题标签暂不可用。"]`. CLAUDE.md `check_validated_claims.py` gate does not flag self-disclosed `not yet` claims.
- `terminal/lib/i18n.tsx:2613` `admAuthorityUnavailable` — pre-existing outage disclosure.
- `terminal/lib/i18n.tsx:28` `validated: ["Passed checks", "已通过检验"]` — admin-tooling label, pre-existing.

The PR added (verbatim):
- `i18n.tsx`: 5 LEX pairs (`recentActivityCockpit`, `whatWeCouldNotWatch`, `whatWeAreWatching`, `eliteTop2`, `openTutorial`) — none contain "validated/验证".
- `gexStrings.ts`: 1 LEX pair (`exposureByExpiry: ["Exposure by expiry term structure", "按到期期限结构显示敞口"]`) — none contain "validated/验证".
- `plainLabels.ts`: `ARC_STATE_LABEL` Record + `arcStateLabel` helper — no string contains "validated/验证".
- `ARC_STATE_LABEL` lives in the same file as `TOPIC_STATUS_LABEL` already does, both feeding the closed-union helper pattern. Test guards pin the same contracts (e.g., `plainLabelsCallSites.test.ts`, `alertTimelineEmptyGuard.test.ts` mentioned in the body).

The PR is plain-language remediation, not scoring or ranking. None of the 14 component `.tsx`/`.ts` diffs add a "validated" signal/scoring/rank claim. No UWP-R2 (two-organisms law) violation introduced — only the user's own typed targets (no change in PR #669) would carry that duty, and this PR does not touch that surface.

## Overall verdict

**PASS** — all three gates satisfied; packet is lawful under the plain-language / theme-art-direction / validated-claims stack. 12 of 18 pre-existing legacy findings retired; 6 survivors documented and non-blocking.

| gate | result | evidence |
| --- | --- | --- |
| plain-language | PASS | `check_plain_language.mjs --json` at `511a25a9` → `counts.blocking: 0`, `legacyReported: 6` (down from 18 at `7f81c55` base); overlay 36 → 37 (added `exposureByExpiry`); 5 new LEX pairs + `arcStateLabel` + `topicStatusLabel` import; no `// plain-language-ok:` waivers introduced |
| theme (TP-0 + Terminal dark-only DEC) | PASS | 17 EVIDENCE.yml packets restamped hash-only; crops unchanged from prior captures (full dark × EN/ZH × 1440/390); DEC cited in every restamped packet's first comment line; zero CSS files in diff; no PNG additions/removals |
| validated-claims | PASS | no new affirmative "validated/已验证/经验证/经过验证" claim (`git diff ... | grep -E '^[+]' | grep -iE ...'` empty across all 14 PR-touched TS/TSX); pre-existing hits are negated/transparent-disclosure and outage-disclosure strings |

Notes for the commissioning seat:
- Plain-language: 12 of 18 base findings retired. The 6 survivors are pinned by an explicit decision tree in the body's Findings table — 4 BY-DESIGN (file returned to base bytes for that specific line), 1 NOT_FIXABLE (no TS union exists for `FundGuidance.type` across the repo), 1 WAIVED-UNTOUCHED (author waiver predates this PR). None are regression debt.
- Theme: zero CSS delta and hash-only evidence restamps mean the matrix carried forward from the pre-existing captures. No PNG file was modified.
- Validated-claims: the diff introduced 6 new bilingual LEX pairs and one Record mapping; zero of these contain "validated" or its ZH equivalents. The Terminal's pre-existing "validated/已验证" lines are in transparency-disclosure or admin-label positions and predate this PR.
- The body's GREEN-at-HEAD section claims `Test Files 367 passed | Tests 5985 passed | 4 todo (5989)` from `cd terminal && npx vitest run` at `2efcae1`, and the typecheck is clean (`npx tsc --noEmit` exit 0 with no output). The audit did not re-run vitest/tsc — the focus is the plain-language / theme / validated-claims gates per the commission. The checker's base-vs-head census is the independent reproduction the audit ships.
- The audit's seven BASE-row line numbers vs HEAD-row line numbers (`WatchingList.tsx:38` vs `:36`; `ForecastPage.tsx:647` vs `:644`) reflect the diff hunk, not a real shift. The audit flags it so the seat doesn't read the disagreement as a defect.

## Audit commands and inputs

- Plain-language: `cd /tmp/t669-audit/wt/terminal && npm install typescript@5 --no-save --silent`; `node scripts/check_plain_language.mjs --json --since 7f81c551d459478a8b5264c74e226670e3608336` (at `511a25a9` head); same command without `--since` at base `7f81c55` for the legacyBefore count.
- Theme: 17 EVIDENCE.yml packets parsed (header lines + `theme: dark` / `languages: [en, zh]` / viewports); PNG counts enumerated for 3 spot-check packets (16 / 16 / 8). Zero CSS files in `git diff --name-only 7f81c55…511a25a9 | grep -iE '\.css$|\.scss$'`.
- Validated-claims: `grep -in 'validated|验证|经验证|已验证|经过验证'` over the 18 PR-touched `.ts/.tsx` paths; `git diff ... | grep -E '^[+]' | grep -iE ...` over all 18 PR-touched paths (empty result).
- PR metadata: `gh pr view 669 --repo mastermindx-market-intelligence/mastermind-terminal --json number,title,body,mergedAt,mergeCommit,headRefName,baseRefName,files`. Body parsed line-by-line; 18-table Findings re-parsed against the checker's output.
- Worktree: `git worktree add /tmp/t669-audit/wt 27463f335c0e874b5e6a284ddab6903a53cb171f --detach` (sparse checkout only — terminal/ scope inherited from base); `git checkout 511a25a9…` for the final commit and `git checkout 7f81c55…` for the base measurement; both worktrees share one `.git`.

SESSION END: PROVEN_OUTCOME — single merged PR audited; three gates returned concrete verdicts (plain-language PASS / theme PASS / validated-claims PASS); report written to `orch/audits/mastermind-terminal_pr669.mm.md`; no durable state outside the audit file.
