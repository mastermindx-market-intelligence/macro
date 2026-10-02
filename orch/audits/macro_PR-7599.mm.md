---
key: orch-audit-macro-pr-7599-2026-09-21
title: 'orch(audit): record macro PR #7599 plain-language/theme/validated-claims audit (2026-09-21)'
pr: 7599
repo: mastermindx-market-intelligence/macro
merge_commit: 8a6cd146708e0f831c090786af4cc270e0e055cf
author: chriswong6031-creator
merged_at: 2026-09-21T10:33:29Z
branch: claude/risk-radar-gate-latency-20260921
base: main
files_changed: 10
additions: 2438
deletions: 0
kind: research_descriptive_only
verdict: PASS
date: 2026-09-21
---

# Macro PR #7599 — plain-language / theme / validated-claims audit

Audit scope: plain-language compliance, theme compliance, and validated-claims
compliance of merged macro PR #7599 (`research(risk): quantify gate selectivity
versus warning latency`), per the qwen_auditor2 audit template.

This PR is **research-only / descriptive** — the body explicitly states no live
probability, weight, band, gate threshold, policy, ledger, ranking, or capital
authority changes. Scope of plain-language gating is therefore the body and
the two user-visible research docs (preregistration + results); theme
compliance is N/A (no user-facing UI surface).

## PR metadata

| Field | Value |
|---|---|
| Repo | `mastermindx-market-intelligence/macro` |
| PR | [#7599](https://github.com/mastermindx-market-intelligence/macro/pull/7599) |
| Title | `research(risk): quantify gate selectivity versus warning latency` |
| Author | `chriswong6031-creator` |
| Base → Head | `main` ← `claude/risk-radar-gate-latency-20260921` |
| Merge commit | `8a6cd146708e0f831c090786af4cc270e0e055cf` |
| Merged at | 2026-09-21T10:33:29Z |
| Files changed | 10 (2 in-tree added; 1 test modified; 7 research artifacts added) |
| Additions / Deletions | +2,438 / -0 |
| Kind | Descriptive research (no live authority changes) |

**Files added or modified (per `git show --stat 8a6cd14`):**

- `agentos/discoveries/DSC-RISK-RADAR-GATE-SELECTIVITY-VS-LATENCY.md` (new, +26)
- `research/grey_deer/RISK_RADAR_GATE_LATENCY_PREREG_2026-09-21.md` (new, +89)
- `research/grey_deer/RISK_RADAR_GATE_LATENCY_RESULTS_2026-09-21.md` (new, +38)
- `research/grey_deer/evidence/gate-latency-20260921/agentos.log` (new, +190)
- `research/grey_deer/evidence/gate-latency-20260921/result.json` (new, +1,293)
- `research/grey_deer/evidence/gate-latency-20260921/run.log` (new, +1)
- `research/grey_deer/evidence/gate-latency-20260921/tests.log` (new, +30)
- `research/grey_deer/evidence/gate-latency-20260921/verification.json` (new, +101)
- `scripts/research/risk_radar_gate_latency.py` (new, +534)
- `tests/test_risk_radar.py` (modified, +136 — main-joined with #7586)

## PR body — capability, result, and integrity

The body is structured cleanly into **Capability / Main result / Method /
Interpretation ceiling / Integration / source** and is built around three
explicit, falsifiable numerical claims:

1. **Full usable history:** precision `20.6% → 41.0%`, recall `70.9% → 28.7%`,
   fire rate `60.6% → 12.3%`. Gate removes 3,344 FP / loses 610 TP, ratio
   **5.48**.
2. **2020+ slice:** precision `23.2% → 39.3%`, recall `90.8% → 36.7%`, fire
   rate `69.0% → 16.5%`. 716 FP removed vs 159 TP lost.
3. **Distinct-event view:** 110 complete `5% / 21-observation` anchors; 103
   had raw loud by T0, but only 42 had gated loud confirmation by T0.
   Among raw-pre-T0: 10 confirm after T0 before the breach, 11 after the
   breach, 40 never confirm through T+21. Median first-gated minus first-raw
   latency = 3 sessions; p75 = 27.5 (where both exist).

The body is honest about scope: "Descriptive research only: no live
probability, weight, band, gate threshold, policy, ledger, ranking, or
capital authority changes." It also reports the methodological repair
(unknown-state masking applied after a canonical `state_accuracy` parity
check exposed a full-history warmup denominator defect; no threshold,
target, horizon, or gate rule changed) and the main-join resolution
(`#7586` had to land first; this carrier resolved the one real conflict in
`tests/test_risk_radar.py` by retaining both test families; the research
result hash stayed unchanged across the join).

## Plain-language findings

**Scope decision:** the standalone `terminal/scripts/check_plain_language.mjs`
gate is a Terminal-repo instrument for user-facing surfaces; macro does not
maintain an equivalent mjs script (the macro `engine/neuralweb/chat_plain_words.py`
governs chat LLM output, not docs). For macro research PRs the operative
plain-language law is the doctrine in `docs/DESIGN_DOCTRINE.md` and
`CLAUDE.md` §Design — "plain-word null disclosure + Tier-2 receipt" and the
banned internal-state/study-name vocabulary **on user-facing surfaces**.
This PR does **not** touch `templates/`, `site/`, `engine/` display-copy
fields, or any consumer-facing surface — the script, the test additions,
the prereg/results markdown, and the evidence JSON are all researcher- and
reviewer-facing. Plain-language gating therefore applies to the **research
markdown and PR body only**; the script, the test, and the JSON are
inherently technical and carry no plain-language exposure.

| Surface | Plain-language exposure | Verdict |
|---|---|---|
| PR body | High — operator/methodologist reader | PASS (jargon acceptable for research audience; key terms defined inline) |
| Preregistration markdown | High — internal protocol readers | PASS (each frozen definition named; ambiguous term `gate_open` disambiguated; `raw_loud` / `gated_loud` defined) |
| Results markdown | High — internal research audience | PASS (numbers paired with interpretation; explicit ceiling printed) |
| `scripts/research/risk_radar_gate_latency.py` | None — code | N/A |
| `tests/test_risk_radar.py` diff | None — code | N/A |
| `evidence/.../result.json`, `verification.json` | None — machine artifacts | N/A |

**Notes on prose quality (research-audience standard, not user-facing):**

- The prereg defines `raw_loud`, `gate_open`, `gated_loud` explicitly and
  prints the FP_removed / TP_lost / FP_removed_per_TP_lost null-handling
  rule. No silent hidden denominator.
- The results table is paired with a "Paired interpretation" paragraph and
  an explicit "Evidence ceiling" callout — daily overlap, event anchors as
  algorithmic labels, descriptive-only.
- One mild readability concern: the body uses the slug
  `5%-within-21-observation` inline without the parenthetical
  "(= close-relative max loss ≥5% within the next 21 SPY closing
  observations)" that the prereg carries. A reader landing on the PR body
  alone has to consult the prereg to confirm what "5%/21-native" means. Not
  a fail — the cross-reference is one click away — but a follow-up edit
  could inline the definition.
- No banned-vocab hits: "validated" is not asserted anywhere in the PR body
  or in any user-facing research doc (see validated-claims below); no
  "ships with", "production-ready", or other user-trust language; no
  per-exemplar `quote → inference` pattern that would route to a falsifier
  ("the gate delays alerts does not by itself justify loosening it" is
  itself the right framing).

**Verdict:** PASS. No plain-language remediation required.

## Theme findings

**Scope decision:** the macro theme-check instruments
(`scripts/check_design_system.py --mode enforce-added`,
`scripts/check_runtime_style_injection.py`,
`scripts/check_ui_visual_evidence.py`) govern user-facing design surfaces —
templates, site HTML/JS, runtime style injection. The PR diff is:

- 0 `templates/*.j2` files
- 0 `site/*.js` or `site/*.html` files
- 0 CSS files
- 0 runtime style injection in `.py`
- 0 visual-evidence artifacts

All ten files are either (a) research markdown / agentos discovery markdown,
(b) Python source under `scripts/research/` and `tests/`, or (c) JSON
receipts under `research/grey_deer/evidence/`. **No theme-bearing surface
is touched.**

| Theme-check surface | Touched in this PR? | Verdict |
|---|---|---|
| `templates/*.j2` | No | N/A |
| `site/*.js`, `site/*.html` | No | N/A |
| Generated `*_data.js` | No | N/A |
| `engine/` display-copy fields | No | N/A |
| Substantive JS style injection | No | N/A |
| Light/dark dual-evidence matrix | No | N/A |

**Verdict:** N/A → PASS. No theme remediation required.

## Validated-claims findings

The macro `scripts/check_validated_claims.py` gate (BC-2 / `PREREGISTRATION.md
§4` / `D2 §4.3`) scans user-facing surfaces in EN + zh for the word
`validated` (and the zh cognates `已验证` / `经验证` / `经过验证`) and refuses
to ship any affirmative claim that is not (a) backed by a justified entry in
`data/regime/validated_claims_allowlist.json` covering the claiming surface,
or (b) referencing an artifact whose top-level `validated == true`.

**Direct textual scan of every prose-bearing file in the PR:**

```
$ git show 8a6cd14 -- <md files> | grep -iE "validated|已验证|经验证|经过验证"
(no hits)
```

- PR body — no `validated` usage.
- Preregistration markdown — no `validated` usage.
- Results markdown — no `validated` usage.
- DSC discovery — uses `verified_at` / `verified_by` (allowed — these are
  DSC schema fields, not the user-facing word). `confidence: verified` is
  the discovery-document own status convention, again not the user-facing
  word. Both are out of scope of the gate per its allowlist schema.
- `scripts/research/risk_radar_gate_latency.py` — no `validated` usage.
- `tests/test_risk_radar.py` diff — no `validated` usage.
- All `evidence/.../*.json` files — no `validated` usage in keys or values.

**Verdict:** N/A → PASS. The PR does not introduce any affirmative
`validated` claim on a scanned surface; nothing to back, nothing to fail.

**Companion claim-integrity check (this audit, not the existing gate):**

Numerical claims in the PR body were verified against
`research/grey_deer/evidence/gate-latency-20260921/result.json`:

| Body claim | result.json value | Body quote | Match? |
|---|---|---|---|
| Full raw precision 20.6% | 0.206445 | "20.6%" | ✓ rounded |
| Full gated precision 41.0% | 0.410485 | "41.0%" | ✓ rounded |
| Full raw recall 70.9% | 0.708852 | "70.9%" | ✓ rounded |
| Full gated recall 28.7% | 0.286999 | "28.7%" | ✓ rounded |
| Full raw fire rate 60.6% | 0.605857 | "60.6%" | ✓ rounded |
| Full gated fire rate 12.3% | 0.123368 | "12.3%" | ✓ rounded |
| Full FP_removed = 3,344 | raw.fp(3940) − gated.fp(596) = 3344 | "3,344" | ✓ exact |
| Full TP_lost = 610 | raw.tp(1025) − gated.tp(415) = 610 | "610" | ✓ exact |
| Full 5.48 removed FP per lost TP | 3344 / 610 = 5.481967… | "5.48" | ✓ rounded |
| 2020+ raw precision 23.2% | 0.232174 | "23.2%" | ✓ rounded |
| 2020+ gated precision 39.3% | 0.392727 | "39.3%" | ✓ rounded |
| 2020+ raw recall 90.8% | 0.908163 | "90.8%" | ✓ rounded |
| 2020+ gated recall 36.7% | 0.367347 | "36.7%" | ✓ rounded |
| 2020+ raw fire rate 69.0% | 0.690276 | "69.0%" | ✓ rounded |
| 2020+ gated fire rate 16.5% | 0.165066 | "16.5%" | ✓ rounded |
| 2020+ FP_removed = 716 | 883 − 167 = 716 | "716" | ✓ exact |
| 2020+ TP_lost = 159 | 267 − 108 = 159 | "159" | ✓ exact |
| 110 complete event anchors | `event_latency.n_events = 110` | "110" | ✓ exact |
| 103 raw loud by T0 | `n_raw_pre_t0 = 103` | "103" | ✓ exact |
| 42 gated loud by T0 | `timing_counts_among_raw_pre_t0.by_t0 = 42` | "42" | ✓ exact |
| 10 confirm after T0 before breach | `after_t0_before_breach = 10` | "10" | ✓ exact |
| 11 confirm after breach | `after_breach = 11` | "11" | ✓ exact |
| 40 never through T+21 | `never_through_t21 = 40` | "40" | ✓ exact |
| Median latency 3.0 sessions | `latency_median_sessions = 3.0` | "3" | ✓ exact |
| p75 latency 27.5 sessions | `latency_p75_sessions = 27.5` | "27.5" | ✓ exact |
| Price-only 1077 closed | `attribution.price_only = 1077` | "1,077" | ✓ exact |
| Breadth-only 179 closed | `attribution.breadth_only = 179` | "179" | ✓ exact |
| Both 2700 closed | `attribution.both_closed = 2700` | "2,700" | ✓ exact |
| Suppressed known raw-loud 3956 days | `suppressed_known_total = 3956` (= 1077+179+2700) | (Results doc) | ✓ exact |

**Sanity tie-out:**

- `n_raw_pre_t0 = by_t0 + after_t0_before_breach + after_breach + never_through_t21`
  → `42 + 10 + 11 + 40 = 103` ✓
- `raw_event_recall = n_raw_pre_t0 / n_events = 103 / 110 = 0.9364` ✓ matches
  `raw_event_recall = 0.936364` in result.json.
- `gated_event_recall_by_t0 = 42 / 110 = 0.3818` ✓ matches
  `gated_event_recall_by_t0 = 0.381818` in result.json.
- Canonical cross-check confusion-matrix fingerprints (full:
  `68f48021c4ef9e1a4f07207775ff4701818770c78f9a111f9a7b3d91aeb5346c`;
  2020+: `7c04d5ee085c01bb5c514fc2602141cd01b83cf4745da745ad2dca6fa9ee73ec`)
  are present in both `result.json.canonical_gated_crosscheck` and
  `verification.json.method.canonical_population_crosscheck` and match
  the gated-population `outcomes_sha256` in `daily.full` /
  `daily.since_2020` — **internal consistency verified**.

**Methodological-integrity receipts (from verification.json):**

- `authority.gate_changed = false`, `live_model_changed = false`,
  `policy_changed = false`, `probability_changed = false`,
  `status = descriptive_only` — matches body claim of no live change.
- `corrections[1]` records the warmup denominator defect and the
  `modern_2020_plus_changed = false` flag — matches the body's
  "no target, horizon, gate, threshold, or result-selection rule changed;
  the 2020+ result was unchanged" sentence.
- `integration.required_parent = 1dc11fb3eb326393c803bc2eff408db89bb91bc1`
  (= #7586 merge commit) and `result_sha_unchanged_across_join: true` —
  matches the body's main-join reconciliation paragraph.
- `verification.owning_suites = "129 passed after required PR 7586
  integration"`, `focused_method_tests = "7 passed"`, `py_compile = pass`,
  `agentos = "0 errors"` — matches the body's method/integrity paragraph.

## Overall verdict

**PASS.** PR #7599 is a clean descriptive-research delivery:

1. **Plain-language** — PASS. Body and research docs are readable to the
   intended internal audience, define every key term inline, and do not
   carry banned-vocab hits on any scanned surface. No user-facing surface
   was touched.
2. **Theme** — N/A → PASS. Zero theme-bearing files in the diff.
3. **Validated-claims** — N/A → PASS. Zero `validated` (or zh cognate)
   usage anywhere in the PR. Internal claim-integrity cross-check (body
   numbers vs `result.json`) ties out exactly on all 28 numerical claims
   tested, including the canonical cross-check SHA fingerprints, the
   event-latency partition sum (`42+10+11+40 = 103 = n_raw_pre_t0`), and
   the attribution sum (`1077+179+2700 = 3956 = suppressed_known_total`).
4. **Methodological integrity** — verified. The two methodological
   corrections (repo-root import shim; unknown-state warmup masking) are
   recorded in `verification.json` with explicit `outcome_read` /
   `modern_2020_plus_changed` flags that match the body's narrative, and
   the `authority` block confirms `descriptive_only` (no live change).

**Optional follow-up (non-blocking):** the PR body references the
"5%/21-native-observation target" without inlining the parenthetical
definition that the prereg carries; adding one inline parenthetical would
make the body self-contained for an external reviewer landing without the
prereg open. Not a fail.

**No remediation required for plain-language, theme, or validated-claims.**
Audit recorded per the qwen_auditor2 template; safe to merge.
