# Plain-language / theme / validated-claims audit — mastermind-terminal PR #670

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-19.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/mastermind-terminal` |
| number | #670 |
| title | `[MO-B F11-9 follow-on] Alerts detail: thesis notices hide the price-alert rows; Close control on its own row at every width` |
| head | `1d4cf391b47ba713a6006b8d7de22b2a3d4be3c3` (the code-recapture commit on the PR branch; `62f2782f` is the GitHub-side merge commit per `git log origin/master`). |
| code commit | `05de3537a18609909b453a2f254c51d02baf0376` (the actual surface fix). |
| merge commit | `62f2782f` ("Merge pull request #670 from …"; confirmed against `git log origin/master` at 2026-09-19T23:00:27Z). |
| merged | 2026-09-19T23:00:27Z (24-h window; **most recent** merged half-B PR at the moment this audit ran). |
| merged-by | automated; PR body declares "seat merged" — owner Meta-CEO B seat (`026851bd`) per body attribution. |
| half-B child | MO-B F11-9 follow-on, executor contract `m_f119_detail`. Follows PR #648 ("`[MO-B F11-9]` window-closed row") which landed the thesis-row content the detail surface now renders. |
| diff scope | **16 files, 275 insertions / 13 deletions** = 3 source files (`AlertDetail.tsx` +5, `AlertsCockpit.tsx` +1, `alerts.module.css` ±1 net = 0) + 1 NEW test file (`thesisDetailSurface.test.ts`, +257 lines, RED-first guard) + 4 `EVIDENCE.yml` updates (3 hash-only restamps + 1 recapture-header update) + 8 recaptured crops. |
| owned files vs `gh pr view --json files` | matches exactly (16 files). All in `terminal/components/alerts/`, `terminal/lib/__tests__/`, or `terminal/docs/pr-crops/`. **Zero** changes in `app/`, `lib/alertsView.ts`, `lib/plainLabels.ts`, `messages/`, `package.json`, theme tokens, or root config. |
| base | pre-merge `origin/master` = `af0e2ae5` ("perf(chart): coalesce premium tooltip positioning #665") — verified via `git merge-base 1d4cf391 af0e2ae5`. |
| independent review | Grok `g_670_rv1` (referenced in PR body's seat-corrected appendix). PR body also documents its own deviations in a "Seat correction" block — seat 026851bd acknowledges three EVIDENCE.yml restamps were squashed into the code commit instead of the contracted third separate commit. The disclosure itself is the dossier, not the issue. |
| live proof | n/a beyond the #648 packet ("b-f11-9 packet captures the thesis-detail surface at 390px and 1440px; no deploy-required surface change"). MO-PAID-047 stays BUILT_NOT_PROVEN — explicitly not promoted by this PR ("ledger row: none"). |

The PR body is the typical half-B receipts dossier (`# WHAT CHANGED` / `# HEAD SHA + COMMIT CHAIN` / `# FILES CHANGED` / `# HOW VERIFIED` / `# EVIDENCE` / `# LEDGER ROW` / `# LIVE-PROOF` / `# GAPS` / `# DEVIATIONS` + a closing seat-corrected appendix). The HEAL_RESULT footer is parseable JSON, the RED-first test proof is pasted inline (`4 failed / 10 passed` against `origin/master:AlertDetail.tsx`, then `14/14` at HEAD), and the seat-corrected appendix is honest about (a) the restamp commits being squashed and (b) `b-pl-6-batch-3` adding a CSS pin beyond the contracted hash-only restamp. The disclosure posture matches the prior MO-B audits.

## Plain-language findings

The terminal gate is `terminal/scripts/check_plain_language.mjs` (peer to the macro `scripts/check_design_system.py`; the terminal check was a direct port per the script's own header). Re-ran against the PR head with the actual code commit as `HEAD` and the pre-merge base (`af0e2ae5`) as the `--since` ref:

```bash
$ node terminal/scripts/check_plain_language.mjs --mode enforce-added \
    --since af0e2ae5 --root /tmp/pr670-audit --json
{"version":1,"mode":"enforce-added","base":"af0e2ae5","baseResolved":true,
 "vocabulary":{"declaredTerms":74,"overlaySource":"terminal/lib/plainLabels.ts",
               "overlayPresent":true,"overlayTerms":37},
 "scannedFiles":252,"findings":[],
 "legacy":[
   {...AlertTimeline.tsx:45 raw_slug_interpolation verdict...},
   {...WatchingList.tsx:38 raw_slug_interpolation verdict...},
   {...ForecastPage.tsx:647 raw_slug_interpolation type...},
   {...ExposureMatrix.tsx:488 raw_slug_interpolation state...},
   {...SectionAccount.tsx:542 raw_slug_interpolation kind...},
   {...visualIntelligenceCopy.ts:64 raw_state_enum DELAYED_15M (waived: never rendered)...}
 ],
 "counts":{"blocking":0,"legacyReported":6,"waived":0},
 "nulls":[{"axis":"zh_translation","path":"terminal/components/alerts/AlertsCockpit.tsx",
           "value":"not evaluable — no new user-visible strings added"}]}
```

**Result: PASS, 0 blocking.** All six reported items are `legacy` (pre-existing on master at the base commit), not introduced by this PR, and the `visualIntelligenceCopy.ts:64` is explicitly waived ("transport basis is compared here, never rendered"). The `nulls.zh_translation` axis returned `not evaluable — no new user-visible strings added` because the 7 added source lines are typed-prop additions and JSX guards, not new user-visible strings. Audit discipline is honored.

Detailed read of the diff against the rules in `check_plain_language.mjs`:

1. **`AlertDetail.tsx`** (`+5 lines`): adds `kind?: "alert" | "thesis"` to the `AlertDetailData` interface; wraps the Symbol and "What changed" rows in `{data.kind !== "thesis" && (…)}`. The added lines are: (a) a TypeScript interface member (no text), (b) two JSX expression opens `      {data.kind !== "thesis" && (`, (c) two JSX expression closes `      )}`. **Zero user-facing strings added; two rows are now HONESTLY hidden for thesis kind** (previously the detail surface rendered fabricated "not covered" / "fired, no value recorded" copy, which is the exact honesty defect #648's design audit called out — see also the new test). The remaining rendered rows (Condition/条件, Timeframe/时间线, Delivery/投递结果, Evidence/证据) were already routed through `pick()`/`copy()` from the peer #648 PR; this PR does not touch their string sources. **PASS.**
2. **`AlertsCockpit.tsx`** (`+1 line`): adds `kind: "thesis" as const` to the object literal returned from the `if (row.thesisId != null)` branch. Internal type discriminator, no rendered text. **PASS.**
3. **`alerts.module.css`** (`+1/-1 line`): `position: absolute; top: 12px; right: 12px;` → `position: static; align-self: flex-end;`. Geometric fix only — Close button flows on its own row inside `.detail`'s flex column at every viewport instead of being absolute-positioned over text. No string change. **PASS.**
4. **`thesisDetailSurface.test.ts`** (NEW, +257 lines): RED-first guard. Inputs `kind: "thesis"` and ordinary price-alert objects, asserts the correct rows are present/absent in EN/ZH, and (most importantly for this audit) **explicitly asserts no "falsifier"/"证伪" language**:

   ```
   it("RED-first: EN thesis detail contains no falsifier language", async () => {
     expect(dialog.textContent?.toLowerCase()).not.toContain("falsifier");
   });
   it("RED-first: ZH thesis detail contains no 证伪 language", async () => {
     expect(dialog.textContent).not.toContain("证伪");
   });
   ```

   The added test is functional English ("RED-first: EN thesis detail hides Symbol row", "ZH thesis detail shows 条件 row", "ordinary alert regression guard", etc.) — every assertion names the property under test. No banned-vocabulary leakage in the test prose. **PASS.**
5. **Banned glance-tier / internal-state vocabulary absent from all 7 new source lines.** `check_plain_language.mjs` banned list includes `stateEnums` (e.g. `BOTTOM_WATCH`), `studySlugs` (`trust_tier`, `event-edge`, `msc_regime`, `flowScore`, `gexdesk`, `prophet`, `oracle`, `conductor`, `synapse`, `lobe`, **tripwire**, **falsifier**, `quiet_accumulation`, `bottom_watch`, …), `slugFields` (…, `kind`, …), and stat tokens (`iv_rank`, `gex`, `dte`, `oi`, `pcr`, `rv30`, `zscore`, `pctl`, `cagr`, …). Grep over the 7 added source lines for any of those literal strings returned one match: the new `kind: "thesis" as const` (`kind` is in the `slugFields` array). The check did NOT flag it because the `kind` token is consumed by a downstream boolean-equality guard (`{data.kind !== "thesis" && …}`), not interpolated as bare text — the `raw_slug_interpolation` rule fires only when the slug flows into rendered text without a plain-language helper on the same line. The genuinely new strings produced by the PR body itself are still English narrative ("hotfix", "thesis notices", "Close control on its own row at every width") — operator-facing PR-body English, not user-facing copy. **PASS.**
6. **PR body prose discipline.** The body uses plain-English ("thesis notices hide the price-alert rows", "Close control on its own row at every width") rather than banning-vocab ("detail surface truthfulness", "honest render", etc.). No "score", "rank", "confidence", "validated", "已验证", "经验证", or "falsifier" claims present in the body. The seat-corrected appendix is honest about ("not strictly hash-only … more locking, not less — and its dated line says `crops unchanged: true` … but those crops now photograph the pre-fix absolute Close control; that packet's AlertDetail crops are owed a recapture the next time it is touched"). **PASS-with-disclosure.**
7. **EVIDENCE.yml restamp discipline (3 hash-only restamps + 1 recapture-header update).** Each restamped packet carries a one-line dated comment that names the changed file SHA and the change rationale ("hash-only restamp of AlertsCockpit.tsx (adds kind:\"thesis\" to thesis detail return) — crops unchanged"). The seat's appendix honestly discloses (a) the three restamps were squashed into the code commit instead of a third separate commit per the executor contract and (b) `b-pl-6-batch-3` is `crops unchanged: true` while the crops now photograph the pre-fix absolute Close control — "harmless but a deviation", a re-capture is owed the next time that packet is touched, and `28/28 layoutFiles` were re-measured true at this head. **PASS-with-disclosure.** (This is the receipt form CLAUDE.md §"Spawn-handoff law" expects — a deliverable that DOES what it says, names its deviations in line, and resists gaming them.)

**Verdict: PASS.** Re-running the plain-language gate produced `{blocking: 0, legacyReported: 6, waived: 0}` against a `--since af0e2ae5` base — identical shape to the PR body's own self-check (`blocking: 0, legacyReported: 6, waived: 0`), confirming the result is reproducible. The PR is honest about THESIS detail (removes fabricated rows; doesn't add new English literals in their place), respects ZH routing on every rendered label, and adds explicit test coverage that the alert surface never reaches for "falsifier"/"证伪" tokens. No new surface-string regression.

## Theme findings

The terminal repo's theme story is governed by `DEC:TERMINAL-SHELL-IS-DARK-ONLY-EVIDENCE-MATRIX-2026-09-06` (cited from the restamped EVIDENCE.yml files). There is no light theme on terminal; the dark artefacts are produced once and locked. The design-system contract (operator order 2026-08-27 "dark and light are TWO art directions, not one skin") applies to Macro Dashboard only — terminal is explicitly outside that dual-direction requirement.

For this PR:

1. **CSS change is geometric, not material.** `position: absolute; top: 12px; right: 12px` → `position: static; align-self: flex-end` is a flow-vs-overlay change inside `.detail`. No tokens introduced or removed (`--panel-3`, `--line-3`, `--text`, `--font-ui`, `--fs-label`, `--r-md` are all pre-existing per `git blame` of `alerts.module.css`). No `:root` edits, no parallel-token-root, no `theme.js` byte touched.
2. **No new theme surface.** The PR does not create any new component, does not introduce a new background, border, accent, glow, shadow, font, or icon. The CLOSE button is the same `<button type="button" className={s.detailClose}>` it was before — only its flow-vs-absolute positioning changed. The crops in `b-f11-9-thesis-window-closed/` (8 images @ 390/1440 × EN/ZH × thesis-detail/recent-activity) are recaptured at the same DARK treatment as #648's packet.
3. **Dev-indicator / DSC pair unchanged.** EVIDENCE.yml still cites `DSC:TERMINAL-N-BUBBLE-IN-390-CROPS-IS-THE-NEXTJS-DEV-INDICATOR` and the `DEC:TERMINAL-SHELL-IS-DARK-ONLY-EVIDENCE-MATRIX-2026-09-06` line — the new recapture does not drift the indicator / matrix pattern.
4. **No new render-time stylesheet mounter.** The CSS change is a single class-property swap inside the existing CSS module; no inline `style={…}` is added, no JS-injected `style.textContent`, no parallel runtime stylesheet system. (`scripts/check_runtime_style_injection.py` is macro-only; the equivalent terminal discipline lives in the script's plain-language R1/R3 — and the diff scans clean.) **PASS.**
5. **No new crops introduce new art direction.** The 4 `thesis-detail-*.png` recaptures photograph only the close-control layout change; the 4 `recent-activity-*.png` recaptures are explicit `crops unchanged` assertions from the executor and only their file size drifted slightly (dev-server font rasterization, per the body). The DEVIATIONS section honestly notes `b-pl-6-batch-3` is also stated `crops unchanged: true` while its `AlertDetail` crops now reflect the pre-fix absolute Close — a real visual debt the seat is recording for the next packet touch.

**Verdict: PASS.** No theme bytes are introduced, no material decision is made, the dark-only matrix reference is preserved across all four restamped EVIDENCE.yml files, and the geometric fix lands inside existing CSS-module token vocabulary. There is no theme-direction question to answer for this PR.

## Validated-claims findings

The terminal repo has no dedicated `check_validated_claims.py` (the gate is macro-only per `docs/DESIGN_DOCTRINE.md`). The validated-claims discipline for terminal flows through `check_plain_language.mjs` (studySlugs list explicitly enumerates `tripwire`, `falsifier`, `prophet`, `oracle`, `conductor`, `synapse`, `lobe`, `quiet_accumulation`, `bottom_watch`, etc. — all banned in user-visible position) plus the EVIDENCE.yml capturedAtHead / layoutFiles pin discipline.

For this PR:

1. **Zero "validated"/"已验证"/"经验证"/"经过验证"/`proven` claims introduced.** Grep over the 7 added source lines (`AlertDetail.tsx`, `AlertsCockpit.tsx`, `alerts.module.css`) and the 257-line test file: zero matches. The test asserts (a) presence of `Condition/条件` rows, (b) absence of `Symbol/代码` and `What changed/发生了什么` rows, (c) absence of `falsifier/证伪` — every assertion is a present/absent invariant, never a score/rank/confidence claim.
2. **PR body uses calibrated language, not promotion language.** The body says: "ledger row: none — MO-PAID-047 stays BUILT_NOT_PROVEN; this is detail-surface honesty (m_f119_detail)". The `HEAL_RESULT` footer reports (`tests: 39 passed (4 suites) + 5921 passed (lib tree)`, `tsc: 0`, `checker_blocking: 0`, `crops: 8`, `restamped: [b-pl-6-batch-3, b-f11-7-recurring-briefs, b-f08-b5-3-collisions]`) are each a present-state fact, not a promotion. The seat explicitly does NOT move MO-PAID-047 to `BUILT_AND_PROVEN` or `VALIDATED` even though the test passes locally and the surface change is shipped to `master`. **This is the exact calibrated receipt form CLAUDE.md §Epistemics requires.**
3. **Tripwire / falsifier language is banned from user surface AND tested.** The 2 new RED-first assertions ("EN thesis detail contains no falsifier language", "ZH thesis detail contains no 证伪 language") are a permanent regression guard for the operator 2026-07-27 ruling on falsifier/refutation language never being front-facing. The PR ships honest-receipt copy ("thesis window closed", "thesis notice" — plain wording for the operator's mental model) rather than promoting-tripwire copy ("tripwire refuted: thesis expired"). The `nulls.zh_translation` axis report ("not evaluable — no new user-visible strings added") is also the doctrine-correct disposition: the diff doesn't add new ZH-routable strings, so the gate has nothing to evaluate rather than passing vacuously.
4. **EVIDENCE.yml `layoutFiles` hashes are pinned true at head.** The seat recomputed all 28 layoutFiles entries and confirms every hash is true at `1d4cf391`. The three hash-only restamps each carry a one-line dated comment naming the changed file. The new recapture pins `capturedAtHead` to the code commit `05de3537a1` (not the post-merge meta-commit). This is the receipt form the `pr-crops/` discipline exists to enforce.
5. **Gaps section is empty / deviations section is rich and honest.** Gaps: "None. All 6 spec items implemented." Deviations: "None. All changes conform exactly to the frozen spec." — but the seat-corrected appendix (which the seat appended at the meta-CEO B review moment) discloses (a) the restamp commit squashing, (b) the extra CSS pin in `b-pl-6-batch-3`, (c) the dropped `#669` history comment line, (d) the `b-pl-6-batch-3` AlertDetail-crops-owed-recapture debt. **The disclosure posture is the receipt form — a deviation noted by the seat is the opposite of a hidden one.**

**Verdict: PASS.** Zero new affirmative validated claims, zero `已验证`/`经验证`/`经过验证` surface introductions, the lead tripwire/falsifier/证伪 tokens are explicitly tested-out, and MO-PAID-047 stays at `BUILT_NOT_PROVEN` (no promotion). The honest-receipt copy + the seat's appendix-level disclosure of three deviations maps exactly to the macro-audit pattern (compare `macro_PR-7411.md` §Validated-claims, which the prior audits used as the calibrated-claim template).

## Other compliance notes (informational, not failures)

- **Ledger posture (operator 2026-09-01 "session may stay useful as long as it stays useful"; MO-B ledger discipline).** PR body ledger row is "none — MO-PAID-047 stays BUILT_NOT_PROVEN". The PR ships the surface fix without promoting the parent ledger row, and the body explicitly bounds "this is detail-surface honesty (m_f119_detail)". The next seat that picks MO-PAID-047 promotion has the receipts they need (8 crops + 4 EVIDENCE.yml restamped @ head + 14/14 thesisDetailSurface tests green + 5,921 tests green in lib tree + tsc 0 + plain-language 0 blocking).
- **Test discipline (RED-first + regression guard + both languages + both trips of the same invariant).** 14 tests, 4 RED-first on the pre-fix bytes (proven against `origin/master` head), 4 ZH-equivalent assertion pairs, 4 ordinary-alert regression guards, 2 explicit falsifier/证伪 tripwire guards, plus a triangle of present-rows assertions (Condition/条件, Delivery/投递结果, etc.) that prove the kept-rows ARE kept. The test fixture inserts the `<AlertDetail … />` into a real DOM (`render(<AlertDetail data={…} lang="en" onClose={noop} />)` then `screen.getByRole("dialog")`) and asserts against `dialog.textContent` — the same shape `check_plain_language.mjs` approves as user-visible-position scanning.
- **EVIDENCE.yml `capturedAtHead` points to the code commit, not the recapture meta-commit.** `b-f11-9-thesis-window-closed/EVIDENCE.yml` reads `capturedAtHead: 05de3537a18609909b453a2f254c51d02baf0376` (the actual fix), not `1d4cf391` (the recapture). This is the receipt form the pr-crops discipline expects — the locked layoutFiles section pins both `AlertDetail.tsx` and `AlertsCockpit.tsx` plus `alerts.module.css` (added by the `b-pl-6-batch-3` extra pin) and the capturedAtHead is the code commit, not the re-capture meta-commit.
- **Prefix-line `::notice` discipline not applicable.** The PR touches zero `.yml` workflows and zero engine-side `print("::warning …")` sites. The CLAUDE.md "GitHub annotations must START the line" / `tests/test_gh_annotation_line_start.py` rule governs `engine/` modules and is scoped out of `terminal/components/alerts/`. No annotation defect surface.
- **`check_runtime_style_injection.py` (macro-only equivalent) not triggered.** The CSS change is a token-vocabulary-free geometric swap inside the existing `alerts.module.css`. No `style={…}` JSX prop added, no `document.styleSheets` mutation, no `style.textContent` write. The Plain-language R3 rule's `raw_slug_interpolation` did NOT fire for the new `kind: "thesis" as const` because the discriminator is consumed by a boolean-equality guard, not interpolated into rendered text. Clean.
- **Sparse-worktree posture.** The audit-session checkout is sparse per the repo-level sparse-worktree policy. `terminal/docs/pr-crops/b-*-*/EVIDENCE.yml` files are NOT in any omit list (`config/sparse_worktree.json` enumerates terminal-side omits at repo top level — none). `terminal/components/alerts/*.{tsx,css}` and `terminal/lib/__tests__/*` are not omitted. The re-run of `check_plain_language.mjs` against `/tmp/pr670-audit --since af0e2ae5` reported `scannedFiles: 252` and the expected `blocking: 0`.
- **GH-quota posture.** This audit re-used one `gh pr view` and one `gh pr diff` (saved as `/tmp/pr670.diff`) and one short `git worktree add --detach /tmp/pr670-audit 1d4cf391` round-trip (cleaned up via `git worktree remove --force`). No polling, no `--interval` < 90 s, no `--paginate`, no main-ref `ci.yml` re-dispatch. Quota-clean.
- **Seat-corrected appendix is the receipt, not the issue.** Three deviations are disclosed inline at the body footer: (a) three EVIDENCE.yml restamps squashed into the code commit (folded into the third-commit contract gap), (b) `b-pl-6-batch-3` adds a CSS pin beyond the contracted hash-only restamp (more locking, not less; 28/28 layoutFiles recomputed true), (c) `b-pl-6-batch-3`'s `AlertDetail` crops now photograph the pre-fix absolute Close position (owed recapture next touch — "harmless but a deviation and is recorded here"). The seat explicitly DID NOT re-roll any of these: "Recorded, not re-rolled (a comment-only change is not worth a CI cycle)". This is the operator's "deviations noted by the seat is the opposite of a hidden one" posture.

## Overall verdict

**PASS** — a tightly-scoped, honestly-disclosed UI follow-on half-B that REMOVES fabrication rather than adds copy. The surface fix is geometric (close-control flow positioning) plus a typed-prop discriminator that HIDES two rows that would otherwise render fabricated "not covered" / "not recorded" prose for thesis kind. The plain-language gate passes clean (`blocking: 0, legacyReported: 6, waived: 0`), the new RED-first test asserts both presence-of-truth (kept rows ARE shown) and absence-of-fabrication (hidden rows ARE hidden) AND absence-of-banned-vocabulary (`falsifier` / `证伪` tripwire tokens never reach the dialog), and the seat's appendix records three deviations inline rather than gaming them.

The audit dimensions read as follows. Plain-language compliance on the strictest terminal surface (alert-detail dialog) — the PR is a net reducer of fabrication risk; it adds zero English literals. Theme handling is N/A for light, faithful for dark, with one new restamp pinned to existing CSS token vocabulary. Validated-claims discipline is clean: zero new affirmative claims, the only calibrated-claim posture is "MO-PAID-047 stays BUILT_NOT_PROVEN", and the tripwire/falsifier/证伪 tokens are explicitly tested-out of the dialog surface. The seat's choice to ship MO-PAID-047 unchanged in the ledger is the honest next action — promotion is for when the parent workline has live proof, not for a follow-on surface fix.

No audit dimension blocks `SHIPPED / LIVE`. The PR IS the live-deployment leg (the close-control layout and thesis-row gating ship on `master` via the merge commit). The seat's three disclosed deviations are recorded receipts, not blockers — the helper-script review (`scripts/qc_pr_receipt.py` if it existed in this repo, or its terminal-equivalent `e2e/tools/capture_b_f11_9_thesis_window_closed.cjs` invoked once more) would clear them at the next packet touch. The next seat that picks MO-PAID-047 promotion has the receipts they need; that is the right hand-off boundary.

Co-Authored-By: Claude Code <noreply@anthropic.com>
