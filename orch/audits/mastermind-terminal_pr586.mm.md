# Audit — mastermindx-market-intelligence/mastermind-terminal PR #586

Mode: qwen_auditor2-style (plain-language / theme / validated-claims laws). One-pass audit against the merged head. No durable writes outside this report.

## PR metadata

| field | value |
| --- | --- |
| repo | `mastermindx-market-intelligence/mastermind-terminal` |
| PR | [#586](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/586) |
| title | [MO-B F08-13] Your own weight targets and drift, readout only, over the applied 0023 columns (MO-DELTA-003) |
| workplan | MO-B (Mastermind O-B), packet B-F08-13 / MO-DELTA-003 |
| mergedAt | 2026-09-19T13:11:28Z |
| merge commit | `7f81c551d459478a8b5264c74e226670e3608336` (merge onto `master`; pre-merge tip = `dafc016e`) |
| audit head | detached worktree at `7f81c551…` (sparse-checkout `terminal/{app,components,lib,scripts}`) |
| files | 34 changed (911 +, 46 −): 5 component files (1 new + 4 modified), 1 i18n file, 2 e2e specs (1 new + 1 modified), 1 capture script (new), 18 EVIDENCE.yml restamps, 8 PNG crops |
| program surface | Terminal Settings panel — new "Portfolio targets" section. Reuses existing `PortfolioTargetsReadout` already mounted on the holdings page (`#552`, B-F08-B5-1); no new column, no new BFF route (0023 columns already `applied_in_production`) |
| half-B label | "half-B" = MO-B user-facing-readout half. Backend shipped earlier (migration 0023 + `/api/portfolio/targets`); this PR is the Settings entry-point half, not a new contract |

The PR title says "readout only" and "over the applied 0023 columns" — packet is explicitly scoped to alternate entry points and reuses the existing readout DOM contract (`[data-testid="portfolio-targets"]`). No scoring, no ranking, no recommendation language (UWP-R2 two-organisms law honored — file's leading comment block states this explicitly).

## Plain-language findings

Tool: `terminal/scripts/check_plain_language.mjs --json` against merge commit `7f81c55` with diff base `dafc016e` (master tip pre-merge). Run on the full repo census (252 scanned files under `terminal/app`, `terminal/components`, plus `terminal/lib/i18n.tsx`). Overlay `terminal/lib/plainLabels.ts` present on this tree (36 overlay terms; declared vocabulary 83 terms).

**Verdict: PASS (0 blocking).**

```json
"counts": { "blocking": 0, "legacyReported": 18, "waived": 0 },
"scannedFiles": 252,
"vocabulary": { "declaredTerms": 83, "overlaySource": "terminal/lib/plainLabels.ts", "overlayPresent": true, "overlayTerms": 36 },
"base": "dafc016e", "baseResolved": true, "mode": "enforce-added",
"nulls": [
  { "axis": "zh_translation", "path": "terminal/components/settings/SettingsProvider.tsx", "value": "not evaluable — no new user-visible strings added" },
  { "axis": "zh_translation", "path": "terminal/components/settings/icons.tsx", "value": "not evaluable — no new user-visible strings added" }
]
```

Manual spot-check of new code paths:
- `SectionPortfolioTargets.tsx` (159 lines): every visible string routes through `t("acsPortfolioTargets" | "acsPortfolioTargetsSub" | "acsPortfolioTargetsLoading" | "acsPortfolioTargetsUnreadable" | "acsPortfolioTargetsEmptyTitle" | "acsPortfolioTargetsEmptyBody" | "acsPortfolioTargetsOpenHoldings" | "acsClose")`. No raw enum, no slug, no `kind` token leaked into JSX. Internal `LoadState.kind` discriminated union is hidden from the rendered tree — only its `data-testid` reaches the DOM.
- `lib/i18n.tsx` (lines 2856–2865) adds 7 LEX keys, each a real `[en, zh]` pair. ZH uses real Chinese with CJK punctuation (`，。、……`): "组合目标权重", "针对你实际持有的仓位，查看你设定的目标权重与偏离度。", "正在读取你的目标权重……", "目前无法读取你的目标权重。下次成功读取后会重新显示。", "尚未设定目标权重", "目标权重由你自行设定。任一持仓都可以添加，偏离度将同时显示在此处和持仓页。", "打开持仓页". No English-only leaks.
- `SectionPortfolioTargets.test.tsx` (282 lines) uses `acsPortfolioTargets` accessible-name selectors in both EN and ZH — matches the existing pattern across `SectionAccount`, `SectionApiKeys`, etc.

Legacy findings (18 — all reported but NOT blocking because they sit on pre-existing lines the diff did not add):
- 6× `missing_zh` in `terminal/components/{alerts,flowdesk,gexdesk,heatmap}` — pre-existing.
- 11× `raw_slug_interpolation` (`verdict`/`status`/`state`/`type`/`kind` fields) in `AlertTimeline`, `AlertsCockpit`, `WatchingList`, `CompanyIntelligencePage`, `ForecastPage` (×2), `TechnicalsPage`, `FlowDeskView`, `ExposureMatrix`, `SectionAccount` — pre-existing.
- 1× `raw_state_enum` `DELAYED_15M` in `terminal/lib/visualIntelligenceCopy.ts:64`, **waived** by author: "transport basis is compared here, never rendered; the returned key selects localized copy." — line 64 sits outside the diff's footprint; waiver is documented.

Conclusion: this PR adds no new plain-language debt. The blocking count is the floor; the legacy pile is unchanged from before this PR landed. Two PR-touched files (`SettingsProvider.tsx`, `icons.tsx`) return `not evaluable` nulls — both are structural/icon additions, no strings added.

## Theme findings

Laws in force (project standing):
- TP-0 theme art-direction (dark + light, dark × light × EN/ZH × 1440/390 evidence matrix) — applies to Macro site.
- `DEC:TERMINAL-SHELL-IS-DARK-ONLY-EVIDENCE-MATRIX-2026-09-06` — exempts Terminal-shell packets from the light half. Required: dark × EN/ZH × 1440/390 + explicit PR-body sentence naming this DEC.

**Verdict: PASS — Terminal dark-only matrix complete.**

Evidence matrix shipped (`terminal/docs/pr-crops/w9t-f08-13-targets-readout/`):
```
PortfolioTargetsSettings-empty-1440-en.png       desktop EN, empty state
PortfolioTargetsSettings-empty-1440-zh.png       desktop ZH, empty state
PortfolioTargetsSettings-empty-390-en.png        mobile  EN, empty state
PortfolioTargetsSettings-empty-390-zh.png        mobile  ZH, empty state
PortfolioTargetsSettings-populated-1440-en.png   desktop EN, NVDA drift row
PortfolioTargetsSettings-populated-1440-zh.png   desktop ZH, NVDA drift row
PortfolioTargetsSettings-populated-390-en.png    mobile  EN, NVDA drift row
PortfolioTargetsSettings-populated-390-zh.png    mobile  ZH, NVDA drift row
```
8 PNGs × {empty, populated} × {1440, 390} × {en, zh} = full dark × EN/ZH × 1440/390 coverage. `EVIDENCE.yml` records `theme: dark` and the PR body's "Evidence crops" section explicitly cites `DEC:TERMINAL-SHELL-IS-DARK-ONLY-EVIDENCE-MATRIX-2026-09-06`. No light crops owed; none invented.

One open item carried in the file (`# recapture: NEEDED`) — the populated crops still paint the pre-heal LONG basis sentence because `SectionPortfolioTargets.tsx` was changed again at the `h_t586` heal to pass `shapeReadoutVisible={false}` (`T_BASIS_SHORT` instead of `T_BASIS`). Body says: "crops `recapture: NEEDED`; live readout proof owed after merge + deploy; B-F08-13 stays `BUILT_NOT_PROVEN`." This is a documented known recapture-debt, not a dark/light gap, and the gate explicitly classifies the packet `BUILT_NOT_PROVEN` rather than `PROVEN_LIVE` until recapture + deploy verify the corrected sentence. **PASS, with one owed recapture that the merge itself did not skip.**

Substantive styling via governed CSS (not runtime JS): `SectionPortfolioTargets.tsx` uses `acs-body`, `acs-note`, `acs-empty-card`, `acs-empty-t`, `acs-empty-s`, `acs-link` — all pre-existing class names from the settings chrome. No `style.textContent`, no parallel token family, no JS-injected inline geometry. The settings panel's NAV was extended with one new row (`portfolioTargets`); `SettingsPanel.tsx` `NAV` count went 12 → 13. No third-header or local material fork.

CSS-delta audit: `git diff --name-only dafc016e...HEAD | grep -iE '\.css$|\.scss$'` returned empty — no CSS files touched by this PR. Theme tokens are inherited from the existing shell.

## Validated-claims findings

Laws in force:
- `scripts/check_validated_claims.py` (Macro-side gate; Terminal has no equivalent — the law is repo-bound but the convention of not using "validated" without backing evidence is repo-wide per the standing theme / TP-0 / CLAUDE.md §House laws).
- Front-facing: never use "validated / 已验证 / 经验证 / 经过验证" to describe platform signals/rank/gate/scoring claims without a backing artifact.

**Verdict: PASS — no new affirmative "validated" claim introduced.**

Spot-check of all 9 PR-touched files (`SectionPortfolioTargets.tsx`, `SettingsPanel.tsx`, `SettingsProvider.tsx`, `icons.tsx`, `SectionPortfolioTargets.test.tsx`, `i18n.tsx`, `api-keys-settings.spec.ts`, `webhooks-settings.spec.ts`, `capture_w9t_f08_13_targets.cjs`) for `validated`/`验证`/`经验证`/`已验证`/`经过验证`:

Hits:
- `lib/i18n.tsx` (3 lines, all pre-existing): "verified" appears in code comments and one pre-existing LEX key `ciQaStructure` — "Structure is verified. Topic labels are not available yet." / "结构已验证。主题标签暂不可用。" This is honest hedged phrasing — "structure is verified, topic labels not available yet" is a transparency disclosure (it admits partial coverage), not a platform-claim of pre-registration or gauntlet passage. The CLAUDE.md `check_validated_claims.py` gate does not flag self-disclosed `not yet` claims.
- `SettingsPanel.tsx:202` — code comment "very page — so it is verified on Usage entry and re-entry, not cached…" — not user-visible; pre-existing line not touched by diff.

None of the new PR additions contain "validated" or its zh equivalents. The packet only displays the user's own typed targets and drift; drift is reported as percentage-point differences (a mathematical fact from the user's own numbers), never as a signal/rank/gate/scoring claim. UWP-R2 (two-organisms law) is explicitly honored in the file's leading comment block.

The `acsPortfolioTargetsUnreadable` copy ("Your targets could not be read just now. They will reappear when the read lands.") is honest failure framing, not a validated-claim — the gate's negation/disclosure rules apply.

## Overall verdict

**PASS** — all three gates satisfied; packet is lawful under the plain-language / theme-art-direction / validated-claims stack.

| gate | result | evidence |
| --- | --- | --- |
| plain-language | PASS | `check_plain_language.mjs --json --since dafc016e` → `counts.blocking: 0`, 18 pre-existing legacy findings unchanged, 2 honest-nulls for non-string files |
| theme (TP-0 + Terminal dark-only DEC) | PASS | 8 PNGs = dark × EN/ZH × 1440/390; DEC cited; no light invention; one documented recapture owed (`BUILT_NOT_PROVEN`, not silently greened); zero CSS files in diff |
| validated-claims | PASS | no new affirmative "validated/已验证/经验证/经过验证" claim; pre-existing hits are negated/hedged comments and `ciQaStructure` transparency disclosure |

Notes for the commissioning seat:
- Plain-language check ran cleanly. The gate's full-census scan flags 18 lines of pre-existing debt across `alerts/`, `fin/`, `flowdesk/`, `gexdesk/`, `heatmap/`, `settings/SectionAccount.tsx`. Those predate this PR — surface as a separate cleanup lane, not part of this audit.
- The `# recapture: NEEDED` flag on `w9t-f08-13-targets-readout/EVIDENCE.yml` is a known owed proof step post-merge — B-F08-13 is `BUILT_NOT_PROVEN` by the body's own classification; the live capture must happen on the deployed artifact before the packet can be flipped to PROVEN_LIVE. This is correctly disclosed, not hidden.
- The Settings NAV went 12 → 13 (`developer` from master + `portfolioTargets`). Two pre-existing e2e specs (`api-keys-settings.spec.ts`, `webhooks-settings.spec.ts`) were made order-independent rather than asserting `Sharing` is `last()` — those changes are bounded by `getByRole("tab", { name: ... })` lookups in both EN and ZH.

## Audit commands and inputs

- Plain-language: `cd /tmp/t586-audit/wt && git sparse-checkout add terminal/scripts terminal/app terminal/components terminal/lib && npm install typescript@5 --no-save --silent && node terminal/scripts/check_plain_language.mjs --json --since dafc016e` (exit 0; ran on detached HEAD `7f81c55`, base `dafc016e`).
- Theme: `terminal/docs/pr-crops/w9t-f08-13-targets-readout/EVIDENCE.yml` parsed; PR body "Evidence crops" section; `git diff --name-only dafc016e...HEAD | grep -iE '\.css$|\.scss$'` = empty.
- Validated-claims: `grep -in 'validated\|验证\|经验证\|已验证\|经过验证'` over the 9 PR-touched files.
- PR metadata: `gh pr view 586 --repo mastermindx-market-intelligence/mastermind-terminal --json number,title,body,mergedAt,mergeCommit,headRefName,baseRefName,files`.
- Worktree: `git worktree add /tmp/t586-audit/wt 7f81c551d459478a8b5264c74e226670e3608336 --detach` (fetched `origin/master` first; `origin/pr/586` ref is gone — branch was deleted after merge, so audit ran on the merge commit directly).

SESSION END: PROVEN_OUTCOME — single merged PR audited; three gates returned concrete verdicts (plain-language PASS / theme PASS / validated-claims PASS); report written to `orch/audits/mastermind-terminal_pr586.mm.md`; no durable state outside the audit file.