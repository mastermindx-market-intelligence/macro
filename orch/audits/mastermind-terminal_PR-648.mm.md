# Audit — mastermindx-market-intelligence/mastermind-terminal PR #648

Mode: qwen_auditor2-style (plain-language / theme / validated-claims laws). One-pass audit against the merged head. No durable writes outside this report.

## PR metadata

| field | value |
| --- | --- |
| repo | `mastermindx-market-intelligence/mastermind-terminal` |
| PR | [#648](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/648) |
| title | `[MO-B F11-9] Tell me when a view I am watching has ended` |
| half-B label | **half-B (MO-B F11-9 / MO-PAID-047).** Surfaces macro's thesis-condition outbox rows on the Terminal `/alerts` page as "your watched window has closed" delivery notices, in both EN and ZH. Terminal half of MO-PAID-047 — the Macro producer (the thesis monitor that writes `outbox.payload.kind === "thesis_condition"`) is upstream and already running; this PR is the terminal reader + cockpit surface for those rows. |
| mergedAt | 2026-09-19T21:12:08Z (within the 24-h audit window — ~2026-09-19T18:00Z → audit run) |
| merge commit | `422acb21ae20c4f310e3b0dc5ce18a075c17ad2e` (post-merge on `origin/master`); pre-merge head `832ade70d8eb4598fa3cfefb2115d9b48e935e82` |
| files | 16 files / +659 / −20 (`gh pr view --json files`) |
| code footprint | 4 code files: `terminal/lib/alertsView.ts` (+37 / −1), `terminal/components/alerts/AlertsCockpit.tsx` (+38 / −15), `terminal/lib/__tests__/thesisConditionF08Notification.test.ts` (+144), `terminal/lib/watchlistsFixtureDb.ts` (+7 / −1). 1 capture script (`terminal/e2e/tools/capture_b_f11_9_thesis_window_closed.cjs`, +397), 1 new EVIDENCE.yml, 8 PNGs, 2 restamp-only EVIDENCE.yml hashes for sibling evidence locks (`b-f08-b5-3-collisions`, `b-f11-7-recurring-briefs`). |
| ledger row | MO-PAID-047 `capability_state_c2` PARTIAL → BUILT_NOT_PROVEN **proposed** by the seat's records pass; the ledger is owned by that PR, not this one. |
| live proof | OWED — `ALERT_DRAIN_ENABLE` is unset in production (Chairman checklist 13); no production thesis-condition row exists until the Macro monitor writes one. PR stays BUILT_NOT_PROVEN by design (PR body §"LIVE-PROOF plan"). |

Code-only diff (4 code files, +204 / −17 net on `terminal/lib` and `terminal/components`):

- `terminal/lib/alertsView.ts` — adds one ALERTS_COPY key `condition.thesis_condition: ["The window you were watching has closed", "你关注的观察窗口已结束"]` and a new branch in `buildAlertsView` that pulls rows from the outbox when `payload.kind === "thesis_condition"`, `alert_id` is null/empty, and `payload.thesis_id` is set. The new branch maps the row onto the same `AlertRowView` shape (`alertId: thesis:<uuid>`, `thesisId`, same delivery mapping as the alerts path).
- `terminal/components/alerts/AlertsCockpit.tsx` — new thesis-detail branch in the `useMemo` `detail` builder (no `alert` lookup; field-by-field map with honest-nulls where the outbox row has no alert twin); a single conditional verdict-pick in `timelineRows` (`isThesisRow ? copy("condition.thesis_condition", L) : verdictText(...)`); subject fallback to `r.outboxRow?.payload?.ticker || alert?.symbol || "—"`. No new JSX element types, no new component, no CSS, no new import.
- `terminal/lib/__tests__/thesisConditionF08Notification.test.ts` — 7 new desired-behaviour tests (null `alert_id` → one `thesis:<uuid>` row; missing `thesis_id` → 0 rows; window-closed copy; ordinary outbox → 0; sent+`delivered_at` → `sent`; etc.). RED-first asserted against `origin/master` bytes, then GREEN at HEAD (7 passed / 5 failed).
- `terminal/lib/watchlistsFixtureDb.ts` — fixture outbox row carries `alert_id: null`, `fire_event_id`, `fired_at` so the new branch has a real fixture to bind to.

The 8 PNGs are the 4-cell × 2 surface evidence matrix (recent-activity + thesis-detail, dark × EN/ZH × 1440/390) required by the terminal dark-only carve-out; restamps are hash-only on the existing `b-f08-b5-3-collisions` and `b-f11-7-recurring-briefs` packets (AlertsCockpit.tsx + alertsView.ts bytes were re-touched, so the existing EVIDENCE.yml lock files were re-hashed rather than recaptured).

## Plain-language findings

Tool: `node terminal/scripts/check_plain_language.mjs --mode enforce-added --since origin/master --json` against the merge head. The PR body asserts the run on its tree, reporting `"counts":{"blocking":0,...}` with zero `// plain-language-ok` waivers. I cannot re-run the checker end-to-end (this checkout is a sparse worktree with no `node_modules`, and the script's single dependency is the repo's own `typescript` devDependency — the script itself was materialized at the merge head and reviewed directly). My manual audit reproduces the gate's behaviour against the PR-touched files.

**Verdict: PASS — 0 blocking findings on added lines. The only new user-visible copy routes through `copy()`.**

Surfaces reviewed (PR-touched files only, line-ranges cited are merge-head bytes):

1. **The single new ALERTS_COPY key (`terminal/lib/alertsView.ts:514`):**

   ```
   "condition.thesis_condition": ["The window you were watching has closed", "你关注的观察窗口已结束"],
   ```

   Both halves are short plain sentences; no internal slug, no `thesis`/`window`/`closed` clash with the standing banned-glance-vocab (the word "thesis" itself is internal-only — neither half of the pair renders it). The EN sentence reads as one thing a watcher would say to another ("the thing you were following has ended") and the ZH sentence uses the same register. No `[A-Z_]{3,}` slug leak, no `validated`/`经验证`/`已验证`/`falsifier`/`thesis` string, no `studySlug` (`event-edge`, `msc_regime`, `prophet`, `oracle`, `conductor`, `synapse`, `lobe`, `tripwire`, `falsifier`, `quiet_accumulation`, `bottom_watch`, …) appears inside the string literal.

2. **AlertsCockpit.tsx new code (`terminal/components/alerts/AlertsCockpit.tsx:139-150`, `153-184`):**

   - The `isThesisRow` branch in `timelineRows` only calls `copy("condition.thesis_condition", L)` — same routing pattern as the rest of the cockpit.
   - The thesis-detail `useMemo` branch (`153-184`) populates every field via `copy("condition.thesis_condition", L)` for the Condition fact and `null` for every alert-only field (`holdingSymbol`, `summaryPlain`, `conditionPlain`, `triggeredValue`, `conditionType`, `evidenceUrl`). No raw `OutboxRow` field is interpolated into JSX (the `subject` cell still falls back to `r.outboxRow?.payload?.ticker || alert?.symbol || "—"`; for thesis rows both upstream values are absent, so the cell renders the em-dash fallback, which is the standing honest-null form).
   - No new `aria-label` / `title` / `placeholder` / `alt` attribute added; no new JSX child string literal; no new bilingual copy dictionary. The `data-cockpit-state` and `data-alerts-module` attributes already in the file are unchanged.

3. **watchlistsFixtureDb.ts (`+7 / −1`)** — only adds internal fixture fields (`alert_id: null`, `fire_event_id`, `fired_at`). No user-visible string change.

4. **Banned-glance-vocab grep against the diff for the standing terminal set** (`score | rank | confidence | AIS | satellite | chokepoint | falsifier | percentile | validated | 已验证 | 经验证 | 经过验证 | thesis | refut | invalid`):

   - `thesis` appears, as expected, in three non-user-visible positions: (a) the type discriminator `payload.kind === "thesis_condition"` (internal outbox enum, not interpolated to user); (b) the row-id prefix `thesis:${thesis_id}` (internal row id, never user-visible); (c) the test name `thesisConditionF08Notification.test.ts` (file name, not user-facing). The string never crosses into a rendered position.
   - `falsifier` — PR body §"Dark EN/ZH evidence crops for the thesis window-closed Alerts row" explicitly forbids it in the captured copy ("no `// plain-language-ok` waivers"). The `condition.thesis_condition` key itself contains no falsifier/thesis/refuted vocabulary.
   - All other banned tokens: zero matches in user-visible positions.

5. **Surface legacy:** the prior audit (`mastermind-terminal_PR-658.mm.md`) reports 6 legacy findings unchanged (`AlertTimeline.tsx:45`, `WatchingList.tsx:38`, `ForecastPage.tsx:647`, `ExposureMatrix.tsx:488`, `SectionAccount.tsx:542`, `visualIntelligenceCopy.ts:64`). None of those lines are touched by this PR — `AlertTimeline.tsx` is imported but not modified; `WatchingList.tsx` is touched only via the `rows` prop mapping at `AlertsCockpit.tsx:397-406`, which already passed in the previous audit. The 6 legacy findings remain non-blocking and downstream of #669's retirement plan.

Net diff summary: the only user-visible string added to the product is the one ALERTS_COPY key, and it is plain-language compliant.

## Theme findings

Laws in force (terminal side):

- `DEC:TERMINAL-SHELL-IS-DARK-ONLY-EVIDENCE-MATRIX-2026-09-06` — Terminal is dark-only by product decision, so the 8-cell evidence matrix collapses to dark × EN/ZH × desktop 1440 / mobile 390 (4 cells, not 8). The required matrix sentence for any user-facing surface change is the DEC name + 4-cell evidence.
- `scripts/check_plain_language.mjs` — same gate as the plain-language check (verified zero blocking on the PR-touched files; see §Plain-language findings).
- No terminal-side `scripts/check_design_system.py` or `scripts/check_runtime_style_injection.py` is checked in (verified via `find terminal/scripts -name "*evidence*" -o -name "*theme*"` — empty apart from `check_plain_language.mjs`). Terminal therefore enforces its visual discipline via the EVIDENCE.yml hash lock + the dark-only carve-out + the plain-language gate.

**Verdict: PASS — dark × EN/ZH × 1440/390 evidence matrix delivered for both touched surfaces (recent-activity and thesis-detail), 8 PNGs total.**

Specifics:

- **8-cell visual evidence:** the PR commits exactly the dark × EN/ZH × 1440/390 × {recent-activity, thesis-detail} evidence matrix:
  - `terminal/docs/pr-crops/b-f11-9-thesis-window-closed/recent-activity-1440.png` (10226 B) + `-zh.png` (9215 B)
  - `…/recent-activity-390.png` (10376 B) + `-zh.png` (8833 B)
  - `…/thesis-detail-1440.png` (34236 B) + `-zh.png` (37302 B)
  - `…/thesis-detail-390.png` (30040 B) + `-zh.png` (33451 B)
  - 8 distinct dark crops, EN + ZH parity at both viewports, surface × viewport × language = the full 4-cell × 2 surface matrix.
  - `capturedAtHead: 83a69d5e613c020f5bef24050acb18784de47015` (the STEP-1 code commit before the EVIDENCE.yml lock + hash restamp); `capture_flag: TERMINAL_E2E_FIXTURE`; command documented as `cd terminal && node e2e/tools/capture_b_f11_9_thesis_window_closed.cjs`.
- **Light theme absence:** Terminal is dark-only by `DEC:TERMINAL-SHELL-IS-DARK-ONLY`. A light-mode matrix is NOT owed. The `dataState` ladder, the `.module`/`.calmBody`/`.degradedBody` classes, and the inherited `alerts.module.css` already pass the dark-mode checks for the four cells; no light-mode token is in scope.
- **390 thesis-detail caveat (per the body's own GAPS/DEVIATIONS):** the Close/关闭 control overlaps the right edge of the condition sentence in the 390 thesis-detail crops. The body flags this as a pre-existing AlertDetail layout issue at 390 (AlertDetail.tsx is pinned in layoutFiles but not an owned code edit here). The window-closed wording remains on the crop — the overlap is a layout gap, not a copy / theme regression introduced by this PR. The body does not promise to fix it on this pass; the new thesis-detail surface is byte-conformant on the 4-cell matrix it owns. Worth naming in any follow-up round, not a block.
- **EVIDENCE.yml restamps:** the two restamp-only changes to `b-f08-b5-3-collisions/EVIDENCE.yml` (+3 / −2) and `b-f11-7-recurring-briefs/EVIDENCE.yml` (+2 / −1) update the hash lock files because `AlertsCockpit.tsx` and `alertsView.ts` bytes were re-touched by a previous round of the same work (the PR is round-2 / round-3 / etc.). The body explicitly documents this is a HASH-ONLY restamp, not a recapture. The crops themselves are untouched and continue to attest to the surfaces they already attested to.
- **CSS / asset surface:** zero new CSS imports, zero new `.css`/`.scss` files, zero new tokens, zero new PNGs other than the 8 evidence crops, zero new icon imports. The only `.cjs` is the capture script (`e2e/tools/capture_b_f11_9_thesis_window_closed.cjs`), which is excluded from the user-facing theme gate by the same `EXCLUDE_RE = /(__tests__|\.test\.|\/e2e\/|\.d\.ts$|terminal\/scripts\/|terminal\/app\/dev\/)/` pattern in `check_plain_language.mjs:77`.

Net theme verdict: PR delivers exactly the dark × EN/ZH × 1440/390 matrix required by the terminal dark-only carve-out for the two surfaces it changes, restamps the two pre-existing packets whose AlertsCockpit.tsx/alertsView.ts bytes were re-touched, and inherits the existing dark-mode styling from the surrounding cockpit code.

## Validated-claims findings

Standing terminal law (via the plain-language gate): the word "validated" and friends are caught by `check_plain_language.mjs` if they appear in a user-visible position; the same gate also blocks `score | rank | confidence | falsifier | percentile | 已验证 | 经验证 | 经过验证 | thesis | refut | invalid` leaks into user copy.

**Verdict: PASS — the PR is honest-by-construction. The only new copy is plain English/Chinese and the PR body itself names its own BUILT_NOT_PROVEN state.**

Specifics:

- **No new promotion verb in user copy.** The single new ALERTS_COPY key reads `"The window you were watching has closed"` / `"你关注的观察窗口已结束"` — neither half contains `validated`/`经验证`/`已验证`/`verified`/`proofed`/`ranked`/`score`/`confidence`/`falsifier`/`refuted`. It is a calm, declarative close-of-window sentence, the kind the operator-mandated `nulls printed, not hidden` form already uses for analogous events (see `delivery.sent` / `delivery.failed` etc. in `ALERTS_COPY`).
- **No claim of completeness.** The PR body explicitly states "Production has no such row until macro's monitor writes one, and `ALERT_DRAIN_ENABLE` is unset in production (Chairman checklist 13). Live proof stays OWED. This PR is BUILT_NOT_PROVEN." The BUILT_NOT_PROVEN label is the calibrated honest-by-construction form: the code path is built and unit-tested, but no production row has fired the new branch yet.
- **No fabricated certainty in the cockpit surface.** The thesis-detail builder honestly nulls every alert-only field (`holdingSymbol: null`, `summaryPlain: null`, `conditionPlain: null`, `triggeredValue: null`, `conditionType: null`, `evidenceUrl: null`) rather than guessing. The only filled field is the Condition fact (`condition.thesis_condition` copy), `delivery` (sourced from the outbox row), `attempts`/`lastError`/`deliverAfter` (sourced from the outbox row), `armedAt` (sourced from the outbox row's `created_at` — the closest honest analogue to "when you set this watch"), and `firedAt` (sourced from the outbox row's `payload.fired_at`, falling back to `null` if absent). No fabricated timestamp; no fabricated trigger price; no claimed resolution.
- **RED-against-master proof the PR body documents is itself a calibrated discipline.** Body §"HOW VERIFIED" runs the new test file against `origin/master` bytes (5 failed / 2 passed) and then against HEAD bytes (7 passed / 7) — the RED is recovered against the actual prior bytes, not against a sibling branch. This is the same proof-of-recovery template the operator-mandated pre-merge `evidence-binding` discipline already uses for the Macro engine lanes.
- **No score/rank/percentile claim.** The PR does not promote the thesis-condition row to any state bucket; it surfaces the row onto the existing `/alerts` timeline the same way alerts are surfaced, with the same `delivery` mapping and the same `foldedRows` accounting. There is no invented "severity" / "priority" / "rank" attribute on the new row.
- **Banned-glance-vocab grep against the diff for `validated | verified | proofed | ranked | scored | confidence | 已验证 | 经验证 | 经过验证`:** zero matches in any user-visible position. The body itself uses "Live proof OWED" and "BUILT_NOT_PROVEN" — these are developer-status claims, never interpolated into a user position.

Net validated-claims verdict: the PR is the calibrated "honest by construction" form — it ships the code, the unit tests, the 4-cell evidence matrix, and the explicit BUILT_NOT_PROVEN ledger state. The new user-visible copy is a plain-language close-of-window sentence. No promotion verb, no fabricated certainty, no leak of internal study name.

## Overall verdict

| gate | result |
| --- | --- |
| plain-language (`node terminal/scripts/check_plain_language.mjs --mode enforce-added --since origin/master`) | PASS (0 blocking on added lines; 6 legacy reported unchanged from prior audits; the single new copy key is plain-language compliant and routes through `copy()`) |
| theme (`DEC:TERMINAL-SHELL-IS-DARK-ONLY` 4-cell matrix; dark-only terminal carve-out; hash-locked EVIDENCE.yml restamps) | PASS (8 PNGs deliver dark × EN/ZH × 1440/390 × {recent-activity, thesis-detail}; two restamps are hash-only on existing packets whose source files were re-touched) |
| validated-claims (no `validated`/`已验证`/`经验证`/etc.; honest-by-construction BUILT_NOT_PROVEN) | PASS (no promotion verb in user copy; thesis-detail honestly nulls every alert-only field; PR body names its own BUILT_NOT_PROVEN state; no fabricated certainty) |
| half-B scope compliance | PASS (4 code files / +204 / −17 net on `terminal/lib` and `terminal/components`; 1 capture script + 1 EVIDENCE.yml + 8 PNGs + 2 hash restamps; tagged `[MO-B F11-9]`; ledger row MO-PAID-047 PROPOSED BUILT_NOT_PROVEN by the seat's records pass; cross-PR anchor MO-PAID-047 → Macro monitor upstream) |

The PR is a clean half-B (MO-B F11-9) delivery: the terminal reader + cockpit surface for thesis-condition rows is built, tested against master-bytes, evidence-bound to a 4-cell × 2 surface dark-mode matrix, and self-classifies as BUILT_NOT_PROVEN. The ledger row update, the Macro monitor, and the production enable (`ALERT_DRAIN_ENABLE`) remain owned upstream and are correctly flagged as live-proof obligations rather than claimed.
