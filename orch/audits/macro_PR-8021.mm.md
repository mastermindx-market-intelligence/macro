---
audit_id: macro_PR-8021
audit_date: 2026-09-26
pr: 8021
pr_title: "fix(risk): keep missing evidence out of calm and recovery"
repo: mastermindx-market-intelligence/macro
merged_at: 2026-09-26T17:36:37Z
head_sha: f2cf0e8cd1432ab5a57ade2b742f5c6fb30b7a84
merge_commit: c948edc0ada1ac81c94636ef0c2c003f49f1b4d6
half_b_class: user-facing-half-B (Risk Detail template + Risk Radar engine)
auditor: qwen_auditor2-equivalent (idle audit pass)
audit_mode: REMOTE USEFUL-IDLE (one pass, no retries, recorded disk-only)
---

## PR metadata

- **Number / title:** #8021 — `fix(risk): keep missing evidence out of calm and recovery`
- **Branch:** `claude/risk-radar-reading-integrity-extract-20260925`
- **Head SHA:** `f2cf0e8cd1432ab5a57ade2b742f5c6fb30b7a84`
- **Merge commit:** `c948edc0ada1ac81c94636ef0c2c003f49f1b4d6`
- **Merged at:** 2026-09-26T17:36:37Z (within last 24h window at audit time)
- **Capability:** Fresh current-main extraction of two still-valid safety semantics from closed/superseded legacy PR #7236 — (1) missing eligible evidence is not Calm; (2) missing-current evidence is not recovery. Explicitly **not** a port of #7236's `risk_presentation.py` / hero / live-copy / generated-page history.
- **Owned files (6):**
  - `engine/risk_radar.py` (+38 / −5) — `compute()` adds presentation-only `reading_state`, `display_score`, `display_band`; `trajectory()` and `_deescalation()` accept `unavailable_scares` and skip ineligible scares from warm/faded/receding narration.
  - `templates/dashboard.html.j2` (+15 / −7) — scare-ladder rendering, plus new `.sc-band-unavailable` CSS rule.
  - `tests/test_risk_radar_review.py` (+80 / −0) — 3 RED-first falsifiers.
  - `tests/test_macro_risk_dialog.py` (+64 / −0) — 2 RED-first falsifiers (template layer).
  - `agentos/discoveries/DSC-US-RISK-MISSING-EVIDENCE-IS-NOT-CALM-OR-RECOVERY.md` (new, +30).
  - `research/grey_deer/US_RISK_READING_INTEGRITY_EXTRACT_2026-09-25.md` (new, +67).
- **Owning run:** `tests/test_risk_radar.py + tests/test_risk_radar_review.py + tests/test_risk_radar_scorecard.py + tests/test_macro_risk_dialog.py` → **187 passed** (PR body) on the candidate head.
- **Browser acceptance (per PR body + repair comment):** Chromium 8/8 PASS — desktop 1440 + mobile 390, EN/ZH, dark/light. Receipt SHA-256 `fd5d1e837cc309c5e9db497519d5bebc668ec944c2b0f7e94b3685173c4381f9`.
- **Numerical equivalence proof:** Base SHA-256 == Candidate SHA-256 (`0baf91860d26dbd4cb508d5c6acc5795a8ef46fe57b7806e704c62e23d8e5c6c`) on a synthetic missing-evidence frame — **byte-identical** for state/state_ungated/alert, Market-State authority payload, dominant scare / top score, conjunction, drawdown-probability payload, context gate, gross factor / cap_leadership, every legacy scare arithmetic field.
- **Pre-merge repair trail:** a Sol continuation/repair receipt at `f2cf0e8cd1…` flagged a `design-governance` regression — `templates/dashboard.html.j2:3917` originally used `color-mix(...)` in `.sc-band-unavailable`. Repaired to existing governed `var(--panel2)` token; arithmetic, availability semantics, trajectory/de-escalation logic, tests, evidence contract unchanged. A second comment re-ran browser evidence on the repaired head and reports the same 8/8 matrix.
- **Does NOT include:** any other-template edits, no model/provider routing, no model-arithmetic change, no state-band rename, no Market-State authority change, no calibration/review/ranking/sizing/capital-policy change.

## Plain-language findings

The user-facing surface diff is **two** strings:

1. Band chip EN copy: `"UNAVAILABLE"` → **"Unavailable"** in EN.
2. New ZH band chip label: **"不可用"**.

Plus the existing em-dash (`—`) already used in the template for missing scores is now reached via the new UNAVAILABLE branch (the prior `{% if _sc_s2 is not none %}` path still emits `—` for any other missing-numeric case; UNAVAILABLE no longer relies on the legacy `score=None` path).

- **No banned vocabulary** (spec §5 plain-word list — "accepted print", "axis", etc.): the new copy is neutral, descriptive, state-of-the-data, and intentionally a non-jargon noun phrase. ✓
- **No raw state names** in the rendered band chip: the template maps `UNAVAILABLE → 'Unavailable'` for EN (was already mapping `WATCH/ELEVATED/CALM/HIGH/CAUTION/RISK-OFF` to mixed case and ZH). ✓
- **No instrument-internal names** (study/slug names like `nh_contraction`, `growth_cyc_def`, `ai_breadth_divergence`) appear in user-facing copy. ✓
- **ZH parity:** "不可用" added symmetrically to the existing `{WATCH,ELEVATED,CALM,HIGH,CAUTION,RISK-OFF}` lookup, used via `l-zh` swap so EN/ZH remain twin-rendered. ✓
- **Pre-existing internal term on the page**: "Scare ladder / 压力梯度" header and "small=`highest first / 由高到低`" are **unchanged** by this PR — they predate #8021. Flagging as ambient debt only, not as a defect of this PR.
- **Glance-tier posture:** the new UNAVAILABLE row is intentionally muted (no number, no bar, neutral chip color), which is the correct "we don't have a read" posture rather than a false reassurance. Aligns with the "nulls printed, not hidden" doctrine. ✓
- **No thesis refutation language** (per operator ruling, banned user-facing phrases include "falsifier fired / thesis refuted / 证伪"). No such string in this diff. ✓

**Plain-language verdict: PASS** — 0 blocking findings, 0 minor findings on PR-introduced strings. The two strings added are plain, paired EN/ZH, and avoid every banned category.

## Theme findings

The PR adds exactly one new CSS rule and one new EN/ZH render branch:

```css
body.page-macro .sc-band-unavailable{
  color:var(--ink-3,var(--muted));
  background:var(--panel2);
  border:1px solid var(--line)
}
```

Plus a dialog-level data-attribute hook:

```css
#dlg-risk .riskdlg-scare[data-band="sc-band-unavailable"]{--rkc-c:var(--muted);}
```

- **Token substitution, not color baking:** every value is a governed theme token (`--ink-3`, `--muted`, `--panel2`, `--line`). No hex literals, no `color-mix(...)`, no rgba. ✓
- **Dark/light parity:** post-repair evidence (per second browser-evidence comment, receipt `fd5d1e8…`) reports the chip background as `rgb(27, 31, 40)` in dark and `rgb(238, 241, 246)` in light — both quiet/neutral, neither calm-green. The two themes do not collapse into one skin because the `--panel2` token is the one the dark and light themes already differ on. ✓
- **Mobile layout:** dialog horizontal overflow = 0 across all 8 matrix cells; mobile ZH layout intact. ✓
- **No runtime style.textContent injection:** the only new styling is the two CSS rules above. The Jinja template sets `data-band` and `data-reading-state` attributes, never `style.textContent`. ✓
- **EN/ZH parity:** EN copy via `<span class="l-en">Unavailable</span>`, ZH copy via `<span class="l-zh">不可用</span>`, swap path governed by `theme.js` / `nav_market.js` per the standing family contract. ✓
- **Pre-existing CSS kept:** the prior scare-band rules (`.sc-band-watch`, `.sc-band-elev`, `.sc-band-calm`, `.sc-band-high`) are untouched. The new rule only adds, never modifies, the existing band palette. ✓
- **Opacity / hierarchy discipline:** the new chip uses `var(--muted)` (not `--down`/`--warn`), explicitly signaling "we don't have a read" without borrowing the warmth of caution or the alarm of high — semantically correct per the operator's instrument-verdicts-are-not-market-verdicts law. ✓
- **No `color-mix(...)` regression at the committed head** (per repair comment: design-governance refused once; repaired to a pure-`var()` rule before merge). ✓
- **Design-system enforcement:** the PR body's qualification report asserts `scripts/check_design_system.py --mode enforce-added` = 0 blocking findings and `scripts/check_ui_visual_evidence.py` = PASS over the full PR diff. ✓

**Theme verdict: PASS** — 0 blocking findings. One mild latent observation: the new `.sc-band-unavailable` chip uses `--panel2` (a panel surface token) for the *fill*, which is materially different from the other band chips that use translucent rgba over the panel. That is the intended hierarchy (unavailable should not glow), but worth re-checking visually against the rest of the scare-ladder rhythm in a real Opus review pass — recorded as advisory, not as a defect.

## Validated-claims findings

- **No `validated` keyword in user-facing strings:** grep over the new user-visible diff (band chip label "Unavailable", ZH "不可用", score `—`, no `sc-bar-fill`) returns 0 hits. ✓
- **No `VALIDATED` prefix/stamp/banner introduced** on the scare-ladder row, the dialog, or the page chrome. ✓
- **No instrument verdict surfaced as a market verdict:** the UNAVAILABLE row says "we have no read" rather than "the risk is low". This is the textbook compliant posture for the instrument-verdicts-are-not-market-verdicts law. ✓
- **DSC record schema:** `agentos/discoveries/DSC-US-RISK-MISSING-EVIDENCE-IS-NOT-CALM-OR-RECOVERY.md` is well-formed — frontmatter includes `key`, `claim`, `falsifier`, `so_what`, `kind: data`, `verified_at`, `verified_by`, `scope`, `confidence: verified`. Both `falsifier` and `so_what` present (required by the schema). ✓
- **Research record:** `research/grey_deer/US_RISK_READING_INTEGRITY_EXTRACT_2026-09-25.md` documents the extraction provenance from closed legacy #7236, the unchanged semantics, the red-first proof, and the numerical equivalence SHA. ✓
- **Capability framing:** the PR body and the DSC's `so_what` both explicitly frame this as an *extract from a closed legacy*, not a fresh claim of analytical correctness. No new marketing-style claim is introduced. ✓
- **No `check_validated_claims.py` CI failure surface introduced:** the only new user-facing strings ("Unavailable", "不可用") are both single-word / two-character descriptive state names that the validator's banned-phrase list does not touch. ✓

**Validated-claims verdict: PASS** — 0 blocking findings, 0 minor findings. The PR adds no new "validated" surface; it actively shrinks the false-reassurance surface that a viewer might have inferred from a numeric `0.0 / calm` row that had no real underlying evidence.

## Overall verdict

**PASS** on all three dimensions (plain-language, theme, validated-claims).

- PR-introduced user-facing copy is plain, paired EN/ZH, and avoids every banned category.
- Theme additions are pure-`var()` CSS, dual-theme tested 8/8 in Chromium with quantified dark/light backgrounds, no runtime style injection.
- Validated-claims posture is improved by the change: an ineligible scare no longer presents as a calm numeric `0.0`.

**Advisory (non-blocking) for the seat owning the merge:**

1. The "Scare ladder / 压力梯度" header term predates this PR but remains internal jargon on the page. Not #8021's debt to fix, but worth a glance-tier re-pass on a future risk-detail polish PR.
2. A canonical Opus reviewer pass on the dark/light rhythm of the four band chips (watch / elev / calm / high) plus the new unavailable chip would close the visual-evidence gap acknowledged in the PR's second comment ("A canonical Opus reviewer was attempted on exact head but the reviewer runtime is quota-blocked until its account reset; no reviewer PASS is claimed"). Not a defect of this PR — a known gap in the gate, worth re-running on the post-merge head.

**Live-closure receipt chain (post-merge):** semantic head `f2cf0e8cd1432ab5a57ade2b742f5c6fb30b7a84`, repair trail head `5e094bf19d1b0141286a7b7152449ba2e8d5579b` (the actual merge candidate after the `color-mix(...)` repair); merge commit `c948edc0ada1ac81c94636ef0c2c003f49f1b4d6`. Browser-evidence receipt SHA `fd5d1e837cc309c5e9db497519d5bebc668ec944c2b0f7e94b3685173c4381f9`.

**Reminder of REMOTE USEFUL-IDLE constraint:** this audit is recorded disk-only at `orch/audits/macro_PR-8021.mm.md`. No PR is opened for the audit itself (per the standing rule for one-pass remote audits). The merged half-B #8021 was already squash-merged at audit time; the audit is a post-merge evidence record, not a ship chain gate.
