# Audit — mastermindx-market-intelligence/mastermind-terminal PR #586

Mode: qwen_auditor2-style (plain-language / theme / validated-claims laws). One-pass audit against the merged head. No durable writes outside this report.

## PR metadata

| field | value |
| --- | --- |
| repo | `mastermindx-market-intelligence/mastermind-terminal` |
| PR | [#586](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/586) |
| title | [MO-B F08-13] Your own weight targets and drift, readout only, over the applied 0023 columns (MO-DELTA-003) |
| workplan | Mastermind O-B (MO-B), packet B-F08-13 / MO-DELTA-003 |
| mergedAt | 2026-09-19T13:11:28Z |
| merge commit | `270b7e3f7b19e47652e0aff6f878554223d55d5c` (merge onto master; merge-author = review-bot, post-merge C2 stamp) |
| head ref (audit) | `origin/pr/586` = `270b7e3f…d55d5c` |
| files | 34 changed (911 +, 46 −); 5 component files (1 new + 4 modified), 1 i18n file, 2 e2e specs (1 new + 1 modified), 1 capture script (new), 17 EVIDENCE.yml restamps, 8 PNG crops |
| program surface | Terminal Settings panel — new "Portfolio targets" section. Reuses existing `PortfolioTargetsReadout` already mounted on the holdings page (`#552`, B-F08-B5-1); no new column, no new BFF route (0023 columns already `applied_in_production`) |
| half-B label | "half-B" = MO-B user-facing-readout half. Backend already shipped (migration 0023 + `/api/portfolio/targets`); this PR is the Settings entry-point half, not a new contract |

The PR title says "readout only" and "over the applied 0023 columns" — the packet is explicitly scoped to alternate entry points and reuses the existing readout DOM contract (`[data-testid="portfolio-targets"]`). No scoring, no ranking, no recommendation language (UWP-R2: two-organisms law honored).

## Plain-language findings

Tool: `terminal/scripts/check_plain_language.mjs --json` against PR head `origin/pr/586`. Run on the full repo census (252 scanned files under `terminal/app`, `terminal/components`, plus `terminal/lib/i18n.tsx`). Diff base = `origin/master` resolved clean.

**Verdict: PASS (0 blocking).**

```json
"counts": { "blocking": 0, "legacyReported": 18, "waived": 0 },
"scannedFiles": 252,
"vocabulary": { "declaredTerms": 83, "overlaySource": "terminal/lib/plainLabels.ts", "overlayPresent": true, "overlayTerms": 36 }
```

Manual spot-check of the new code paths:
- `SectionPortfolioTargets.tsx` (158 lines): every visible string routes through `t("acsPortfolioTargets" | "acsPortfolioTargetsSub" | "acsPortfolioTargetsLoading" | "acsPortfolioTargetsUnreadable" | "acsPortfolioTargetsEmptyTitle" | "acsPortfolioTargetsEmptyBody" | "acsPortfolioTargetsOpenHoldings" | "acsClose")`. No raw enum, no slug, no `kind` token leaked into JSX. The internal `LoadState.kind` discriminated union is correctly hidden from the rendered tree — only its `data-testid` reaches the DOM.
- `lib/i18n.tsx` lines 2859–2865 add 7 LEX keys, each a real `[en, zh]` pair. ZH uses real Chinese with CJK punctuation (`，。、——`): "组合目标权重", "针对你实际持有的仓位，查看你设定的目标权重与偏离度。", "正在读取你的目标权重……", "目前无法读取你的目标权重。下次成功读取后会重新显示。", "尚未设定目标权重", "目标权重由你自行设定。任一持仓都可以添加，偏离度将同时显示在此处和持仓页。", "打开持仓页". No English-only leaks.
- Test (`SectionPortfolioTargets.test.tsx`, 281 lines) uses `acsPortfolioTargets` accessible-name selectors in both EN and ZH — matches the existing pattern across `SectionAccount`, `SectionApiKeys`, etc.

Legacy findings (18 — all reported but NOT blocking because they sit on pre-existing lines the diff did not add):
- 7× `missing_zh` in `terminal/components/{alerts,flowdesk,gexdesk,heatmap,fin}` — pre-existing.
- 10× `raw_slug_interpolation` (`verdict`/`status`/`state`/`type`/`kind` fields) in `AlertTimeline`, `AlertsCockpit`, `WatchingList`, `CompanyIntelligencePage`, `ForecastPage`, `TechnicalsPage`, `FlowDeskView`, `ExposureMatrix`, `SectionAccount` — pre-existing.
- 1× `raw_state_enum` `DELAYED_15M` in `terminal/lib/visualIntelligenceCopy.ts:64`, **waived** by author: "transport basis is compared here, never rendered; the returned key selects localized copy." — line 64 sits outside the diff's footprint; waiver is documented.

Conclusion: this PR adds no new plain-language debt. The blocking count is the floor; the legacy pile is unchanged from before this PR landed.

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
8 PNGs × {empty, populated} × {1440, 390} × {en, zh} = full dark × EN/ZH × 1440/390 coverage. `EVIDENCE.yml` records `theme: dark` and explicitly cites `DEC:TERMINAL-SHELL-IS-DARK-ONLY-EVIDENCE-MATRIX-2026-09-06` in the PR body's "Evidence crops" section. No light crops owed; none invented.

One open item carried in the file (`# recapture: NEEDED`) — the populated crops still paint the pre-heal LONG basis sentence because `SectionPortfolioTargets.tsx` was changed again at the `h_t586` heal to pass `shapeReadoutVisible={false}` (`T_BASIS_SHORT` instead of `T_BASIS`). Body says: "crops `recapture: NEEDED`; live readout proof owed after merge + deploy; B-F08-13 stays `BUILT_NOT_PROVEN`." This is documented as a known recapture-debt, not a dark/light gap, and the gate explicitly classifies the packet `BUILT_NOT_PROVEN` rather than `PROVEN_LIVE` until recapture + deploy verify the corrected sentence. **PASS, with one owed recapture that the merge itself did not skip.**

Substantive styling via governed CSS (not runtime JS): `SectionPortfolioTargets.tsx` uses `acs-body`, `acs-note`, `acs-empty-card`, `acs-empty-t`, `acs-empty-s`, `acs-link` — all pre-existing class names from the settings chrome. No `style.textContent`, no parallel token family, no JS-injected inline geometry. The settings panel's NAV was extended with one new row (`portfolioTargets`); `SettingsPanel.tsx` `NAV` count went 12 → 13. No third-header or local material fork.

## Validated-claims findings

Laws in force:
- `scripts/check_validated_claims.py` (Macro-side gate; Terminal has no equivalent — the law is repo-bound but the *convention* of not using "validated" without backing evidence is repo-wide).
- Front-facing: never use "validated / 已验证 / 经验证 / 经过验证" to describe platform signals/rank/gate/scoring claims without a backing artifact.

**Verdict: PASS — no new affirmative "validated" claim introduced.**

Spot-check of all 9 PR-touched files (`SectionPortfolioTargets.tsx`, `SettingsPanel.tsx`, `SettingsProvider.tsx`, `icons.tsx`, `SectionPortfolioTargets.test.tsx`, `i18n.tsx`, `api-keys-settings.spec.ts`, `webhooks-settings.spec.ts`, `capture_w9t_f08_13_targets.cjs`) for `validated`/`验证`/`经验证`/`已验证`/`经过验证`:
- `lib/i18n.tsx:1265` — pre-existing "验证门槛" (verification threshold) in a different unrelated LEX key (Exchange-code context). Untouched by this PR.
- `lib/i18n.tsx:2543` — pre-existing `ciQaStructure: ["Structure is verified. Topic labels are not available yet.", "结构已验证。主题标签暂不可用。"]`. This is honest hedged phrasing — "structure is verified, topic labels not available yet" is a transparency disclosure, not a platform-claim of pre-registration or gauntlet passage.
- `lib/i18n.tsx:2613` — pre-existing `admAuthorityUnavailable: ["Couldn't verify admin access — this is an outage, not a denial.", ...]`. Negated framing, exempt by the gate's negation rule.

None of the new PR additions contain "validated" or its zh equivalents. The packet only displays the user's own typed targets and drift; drift is reported as percentage-point differences (a mathematical fact from the user's own numbers), never as a signal/rank/gate/scoring claim. UWP-R2 (two-organisms law) is explicitly honored in the file's leading comment block.

## Overall verdict

**PASS** — all three gates satisfied; packet is lawful under the user-first/plain-language/theme-art-direction/validated-claims stack.

| gate | result | evidence |
| --- | --- | --- |
| plain-language | PASS | `check_plain_language.mjs --json` → `counts.blocking: 0`, 18 pre-existing legacy findings unchanged |
| theme (TP-0 + Terminal dark-only DEC) | PASS | 8 PNGs = dark × EN/ZH × 1440/390; DEC cited; no light invention; one documented recapture owed (`BUILT_NOT_PROVEN`, not silently greened) |
| validated-claims | PASS | no new affirmative "validated/已验证/经验证/经过验证" claim; pre-existing hits are negated/hedged and unchanged |

Notes for the commissioning seat (one line each):
- Plain-language check ran cleanly; the gate's full-census scan flags 18 lines of pre-existing debt across `alerts/`, `fin/`, `flowdesk/`, `gexdesk/`, `heatmap/`, `settings/SectionAccount.tsx`. Those are unrelated to F08-#106 and predate this PR — surface as a separate cleanup lane, not part of this audit.
- The `# recapture: NEEDED` flag on `w9t-f08-13-targets-readout/EVIDENCE.yml` is a known owed proof step post-merge — B-F08-13 is `BUILT_NOT_PROVEN` by the body's own classification; the live capture must happen on the deployed artifact before the packet can be flipped to PROVEN_LIVE. This is correctly disclosed, not hidden.
- The merge commit (`270b7e3f…`) is a post-merge C2 stamp — the squash/merge landed earlier and `270b7e3f` only restamped `capturedAtHead` to the merge SHA. The substantive code changes are at the parent commits on the branch, all of which are reachable from `origin/pr/586`.

## Audit commands and inputs

- Plain-language: `cd /tmp/audit-t586/wt-full && node terminal/scripts/check_plain_language.mjs --json > /tmp/audit-t586/plain-lang.json 2>/tmp/audit-t586/plain-lang.err` (exit 0).
- Theme: `terminal/docs/pr-crops/w9t-f08-13-targets-readout/EVIDENCE.yml` parsed; PR body "Evidence crops" section; `terminal/app/globals.css:1253` and `terminal/app/settings.css:32` dark-only comments confirmed in place (cross-checked against DEC evidence).
- Validated-claims: `grep -in 'validated\|验证\|经验证\|已验证\|经过验证'` over the 9 PR-touched files in `/tmp/audit-t586/wt-full/`.
- PR metadata: `gh pr view 586 --repo chriswong6031-creator/mastermind-terminal` (local mirror = bare clone of the public repo; PR head fetched as `origin/pr/586`).
- Audit head: `270b7e3f7b19e47652e0aff6f878554223d55d5c` (= `refs/pull/586/head`).

SESSION END: PROVEN_OUTCOME — single merged PR audited; three gates returned concrete verdicts; report written to `orch/audits/mastermind-terminal_pr586.mm.md`; no durable state outside the audit file.