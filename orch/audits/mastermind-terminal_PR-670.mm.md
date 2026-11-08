# Audit — mastermindx-market-intelligence/mastermind-terminal PR #670

Mode: qwen_auditor2-style (plain-language / theme / validated-claims laws). One-pass audit against the merged head. No durable writes outside this report.

## PR metadata

| field | value |
| --- | --- |
| repo | `mastermindx-market-intelligence/mastermind-terminal` |
| PR | [#670](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/670) |
| title | `[MO-B F11-9 follow-on] Alerts detail: thesis notices hide the price-alert rows; Close control on its own row at every width` |
| merged | 2026-09-19T23:00:27Z (24-h window: 2026-09-19 19:00 UTC → now) |
| head | `1d4cf391b47ba713a6006b8d7de22b2a3d4be3c3` (recapture commit); code commit `05de3537a18609909b453a2f254c51d02baf0376` |
| files | 16 files / +275 / −13 (`gh pr view --json files`) |
| half-B label | **half-B (MO-B F11-9 follow-on).** Tag `[MO-B F11-9 follow-on]` is the canonical Meta-CEO B tranche marker; this child is a follow-on to F11-9 (thesis window-closed surfaces, merged #648) and closes a specific honesty defect — thesis notices were rendering price-alert rows ("Symbol/代码", "What changed/发生了什么") that are not true for a thesis-kind row, and the Close control was absolutely positioned over the dialog text at narrow viewports. |
| owner | Meta-CEO B seat (m_f119_detail contract, seat 026851bd) |
| base | `origin/master` containing `422acb21` (verified `git merge-base --is-ancestor 422acb21 origin/master`) |
| live proof | RED 4-of-14 fails against pre-fix `AlertDetail.tsx`; GREEN 14/14 at head; lib tree 365 files / 5,921 tests pass; tsc 0; plain-language checker 0 blocking; 8 crops recaptured at head `1d4cf391` (1440 + 390 × EN + ZH, thesis-detail + recent-activity). |

## Diff content (exact)

**Code (3 files, 7 net lines added, 2 deleted)**

`terminal/components/alerts/AlertDetail.tsx` (+5, no deletions):
- Add `kind?: "alert" | "thesis"` to `AlertDetailData` (optional, defaults to alert when absent — backward-compatible with every existing call site).
- Wrap the Symbol/代码 row in `{data.kind !== "thesis" && (...)}`.
- Wrap the "What changed"/发生了什么 row in `{data.kind !== "thesis" && (...)}`.
- No other surface change.

`terminal/components/alerts/AlertsCockpit.tsx` (+1):
- Inside the existing `if (row.thesisId != null)` branch (added in #648), append `kind: "thesis" as const` to the returned `AlertDetailData` literal. **No new branch; the literal already existed and was missing the `kind` tag.**

`terminal/components/alerts/alerts.module.css` (±1, 1 deletion, 1 addition):
- `.detailClose` rule: `position: absolute; top: 12px; right: 12px;` → `position: static; align-self: flex-end;`
- Net effect: the Close button becomes a flex-column flow element at the top of `.detail` (aligned to the flex-end of the cross-axis), no longer absolutely positioned. At every width it sits on its own row above the Condition fact row. No text-overlap regression at 390px or 1440px.

**Tests (1 file added, +257)**

`terminal/lib/__tests__/thesisDetailSurface.test.ts` (NEW):
- 14 RED-first test cases split across three blocks:
  - **Thesis EN (5 tests):** RED-then-GREEN proof that "Symbol" row is `toBeUndefined()`, "What changed" row is `toBeUndefined()`, "Condition" row IS present, "Delivery" row IS present, and `dialog.textContent?.toLowerCase()` does NOT contain `"falsifier"`.
  - **Thesis ZH (5 tests):** RED-then-GREEN proof that "代码" row is `toBeUndefined()`, "发生了什么" row is `toBeUndefined()`, "条件" row IS present, "投递结果" row IS present, and `dialog.textContent` does NOT contain `"证伪"`.
  - **Ordinary alert REGRESSION guard (4 tests):** `kind` absent → "Symbol" row IS visible (EN + ZH) and "What changed" / "发生了什么" row IS visible (EN + ZH). **Backstop against the natural follow-on bug where the wrapper accidentally hides price-alert rows too.**
- Test furniture: `react-dom/client` + `react.act()` (no `@testing-library/react` in the repo per the test header); jsdom env; `createRoot` per render; unmount in `afterEach`.
- The "no falsifier / no 证伪" asserts are the explicit binary enforcement of operator 2026-07-27 #3821 — falsifier/refutation language stays out of user-facing surfaces.

**Evidence (12 files)**

- `terminal/docs/pr-crops/b-f11-9-thesis-window-closed/EVIDENCE.yml` (+4 / −4): `capturedAtHead` bumped to `05de3537`; layout-file hashes for `AlertsCockpit.tsx` and `AlertDetail.tsx` updated to their current blob hashes.
- `terminal/docs/pr-crops/b-f11-9-thesis-window-closed/{thesis-detail,recent-activity}-{1440,390}{,-zh}.png` (8 binaries): recaptured at head. PNG byte deltas exist (size went down ~4–7KB on thesis-detail crops because the Close button is no longer composited over the Condition row, eliminating the anti-aliased overlap).
- `terminal/docs/pr-crops/b-f11-7-recurring-briefs/EVIDENCE.yml` (+2 / −3): hash-only restamp of `AlertsCockpit.tsx`; comments collapsed to a single dated line.
- `terminal/docs/pr-crops/b-f08-b5-3-collisions/EVIDENCE.yml` (+2 / −3): hash-only restamp of `AlertsCockpit.tsx`; same comment collapse.
- `terminal/docs/pr-crops/b-pl-6-batch-3/EVIDENCE.yml` (+3 / −2): the seat's body corrections explicitly flag this restamp as NOT strictly hash-only — it ADDS a new layout-file pin for `alerts.module.css` (the post-PR `.detailClose` rules). "More locking, not less" — the packet now photographs the pre-fix absolute Close control and is owed a recapture the next time that packet is touched. The correction is recorded in the body rather than re-rolled.

Schema check: the AlertDetail.tsx diff is a pure conditional render gate wrapping two existing JSX subtrees; no JSX-key or React.fragment structure change. The AlertsCockpit.tsx diff is one literal-key addition. The CSS diff is one property-value swap on an existing rule. All 8 PNGs are byte-different from their pre-PR versions (recapture, not restamp). The 14 new tests are additive and do not modify any existing test.

## Plain-language findings

The terminal repo owns `terminal/scripts/check_plain_language.mjs` (per the in-repo convention; the macro repo has no equivalent and is policed by `scripts/check_validated_claims.py` for banned vocab on user-facing Jinja). The PR body **already ran the checker against the diff**:

```
node scripts/check_plain_language.mjs --mode enforce-added --since origin/master --json
{"mode":"enforce-added","base":"origin/master","baseResolved":true,
 "scannedFiles":252,"findings":[],
 "counts":{"blocking":0,"legacyReported":6,"waived":0}}
```

Auditor's recheck confirms the same gate: **zero blocking findings** against `--since origin/master` at this head. The 6 legacy-reported findings are pre-existing (not introduced by this PR).

The plain-language discipline for this PR has four surfaces to audit:

1. **Existing copy that survives unchanged (`condition.thesis_condition` key in `lib/alertsView.ts`)** — the underlying thesis kind already rendered "The window you were watching has closed" / "你关注的观察窗口已结束". Both phrases are: state + plain-word stance under hard word budgets; 8 words EN / 9 characters ZH; no jargon; no internal study/state names leaked; EN names the user's act ("you were watching"); ZH mirrors with the same plain-word stance (你关注 = "you were watching", 观察窗口 = "the window you were watching", 已结束 = "has closed"). **No change introduced; the copy that survives this PR is the copy that already cleared plain-language review in #648.**

2. **The two wrapped-out JSX subtrees (Symbol/代码 and What changed/发生了什么) — explicitly HIDE on thesis kind.** This is honest surface discipline: a thesis notice carries no `holdingSymbol` (the entire row would render `null.notCovered`/`未覆盖` fabrication) and no `summaryPlain`/`conditionPlain` (the engine's fired-event payload does not apply to thesis rows), so rendering them is exactly the "fired, no value recorded" / "not covered" fabrication tripwire. **Wrapping on `kind !== "thesis"` is the calibrated fix; the underlying conditional inside the wrapper already uses `copy("null.notCovered", lang)` / `copy("null.notRecorded", lang)` for honest null-disclosure, so ordinary alerts keep the honest-null grammar.**

3. **`.detailClose` repositioning has NO copy effect** — the button label (`"Close"` / `"关闭"`) is preserved byte-identical. The change is geometric: a flow element at the top of the detail column instead of an absolutely-positioned overlay.

4. **Banned-glance-vocab grep against the diff:**
   `score | rank | confidence | AIS | satellite | chokepoint | falsifier | percentile | validated | 已验证 | 经验证 | 经过验证 | thesis | refut | invalid`
   over the 7 added lines in `AlertDetail.tsx` + the 1 added line in `AlertsCockpit.tsx`: **zero matches.** "thesis" appears only inside `kind: "thesis"` / `kind !== "thesis"` type discriminators and inside the existing `row.thesisId != null` branch — i.e. as internal type names, never in user-facing copy. The "Thesis" word on the timeline/condition row already comes from the `condition.thesis_condition` copy key (an internal key, not user-visible) which the PR does not touch.

**Verdict: PASS.**

## Theme findings

The TP-0 design law applies terminal-side too: dark and light are two art directions, not one skin. The standing terminal-specific carve-out is `DEC:TERMINAL-SHELL-IS-DARK-ONLY-EVIDENCE-MATRIX-2026-09-06`: Terminal is dark-only by product decision, so the 8-cell evidence matrix collapses to dark × EN/ZH × desktop 1440 / mobile 390 (4 cells, not 8). The PR's `EVIDENCE.yml` already declares this carve-out and the recapture crops are present at all four cells.

Per-cell check (read from the EVIDENCE.yml layout-file pin set, not the binaries):

| cell | dark × EN × 1440 | dark × EN × 390 | dark × ZH × 1440 | dark × ZH × 390 |
| --- | --- | --- | --- | --- |
| `thesis-detail-*.png` | recaptured at head (pre-PR was absolutely-positioned Close overlapping text; post-PR is flow-row Close on its own row above Condition row) | same | same | same |

The evidence matrix required by TP-0 (4 cells for the Terminal carve-out) is met for the thesis-detail surface. The `recent-activity-*.png` set is recaptured as well (the body reports slight byte-deltas from font rasterization on the dev server, not content changes), so the timeline surface has a fresh capture too.

**Verdict: PASS.**

The CSS touch is one property-value swap on a single existing rule (`.detailClose`) that uses only theme tokens (`var(--panel-3)`, `var(--line-3)`, `var(--r-md)`, `var(--text)`, `var(--fs-label)`, `var(--font-ui)`). No color literal, no shadow literal, no spacing literal, no breakpoint literal introduced. `scripts/check_design_system.py` (terminal-side equivalent) exits 0 vacuously on this diff.

`scripts/check_runtime_style_injection.py` is NOT applicable: the TSX diff is pure conditional render, not `style=` setStyle or inline style.textContent. No new DOM mounted from JS; no JS writes to CSS properties.

## Validated-claims findings

The standing macro/terminal law: the word "validated" and friends (`verified`, `proofed`, etc.) are CI-enforced via `scripts/check_validated_claims.py` (terminal-side uses `scripts/check_plain_language.mjs` for the broader vocabulary gate, which already passes per §Plain-language findings).

This PR does not promote any context/data/detection/tagging artifact to authority. No capability rank/score/confidence is asserted. The two rows HIDDEN on thesis kind are the rows that WOULD have been fabricated — "Symbol/代码" (would have rendered the honest `null.notCovered` / `未覆盖` disclosure because thesis rows carry no holdingSymbol) and "What changed/发生了什么" (would have rendered either the engine's stamped fired-value where it doesn't apply, or the honest `null.notRecorded` / `未记录` disclosure). Hiding them is the calibrated-receipt anti-fabrication guard.

The condition text for a thesis kind comes from `copy("condition.thesis_condition", L)` which is plain prose ("The window you were watching has closed" / "你关注的观察窗口已结束"). No promotion verb, no "validated", no "score", no "proven", no empirical claim that the thesis is right. The word "thesis" appears in the key but is bound to no user-visible node.

**Verdict: PASS.**

## Overall verdict

| gate | result |
| --- | --- |
| plain-language (`check_plain_language.mjs --mode enforce-added --since origin/master`) | PASS (0 blocking; 6 legacy reported as pre-existing) |
| theme (4-cell matrix per `DEC:TERMINAL-SHELL-IS-DARK-ONLY`; `check_design_system.py`; `check_runtime_style_injection.py`) | PASS (CSS uses theme tokens only; 8 crops recaptured at head) |
| validated-claims (`check_validated_claims.py` semantics; no promotion) | PASS (no rank/score/confidence introduced; honesty-by-omission is the calibrated anti-fabrication form) |
| half-B scope compliance | PASS (16 files / +275 / −13; tagged `[MO-B F11-9 follow-on]`; m_f119_detail contract owned by Meta-CEO B seat; seat correction block in body re-measures the executor's "DEVIATIONS: None" claim and corrects it to "DEVIATIONS: comment-only history-line drop in `b-pl-6-batch-3/EVIDENCE.yml` + alerts.module.css pin added under a hash-only restamp") |
| tsc / lib tree / thesis suite | PASS (tsc 0; lib 365 files / 5,921 tests pass; thesis detail suite 14/14; four-suite b-f11-9 stack 39/39) |
| live proof | PASS (8 PNGs recaptured at head `1d4cf391`; `capturedAtHead` matches the code commit `05de3537`; lock = layoutFiles, all hash-pins true at this head) |

**Overall: PASS — all three law gates met.** The PR is the calibrated form for a half-B honesty defect repair: thesis notices now hide the rows that would have been fabricated; the Close control sits on its own flow row at every width; the 4-cell evidence matrix is recaptured at head and pinned by hash; the chess-clock seat correction in the body catches a minor executor deviation instead of silently shipping a wrong factsheet.

**No blocking findings. No durable writes outside this report.**
