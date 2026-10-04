---
key: orch-audit-macro-pr-7608-2026-09-21
title: 'orch(audit): record macro PR #7608 plain-language/theme/validated-claims audit (2026-09-21)'
pr: 7608
repo: mastermindx-market-intelligence/macro
merge_commit: f5fd0e7e8e6d8ef55fa3b9c9d8e7e6d8ef55fa3b
author: chriswong6031-creator
merged_at: 2026-09-21T11:23:11Z
branch: claude/risk-radar-caution-persistence-20260921
base: main
files_changed: 10
additions: 2335
deletions: 0
kind: research_descriptive_only
verdict: PASS
date: 2026-09-21
---

# Macro PR #7608 — plain-language / theme / validated-claims audit

Audit scope: plain-language compliance, theme compliance, and validated-claims
compliance of merged macro PR #7608 (`research(risk): classify five-session
caution persistence as context`), per the qwen_auditor2 audit template.

This PR is **research-only / descriptive** — the body and the DSC entry
explicitly state no live probability, weight, band, gate threshold, policy,
ledger, ranking, or capital-authority change. Scope of plain-language gating
is therefore the body and the two user-visible research docs (preregistration
+ results); theme compliance is N/A (no user-facing UI surface); validated-
claims compliance is N/A (no user-facing surface touched).

## PR metadata

| Field | Value |
|---|---|
| Repo | `mastermindx-market-intelligence/macro` |
| PR | [#7608](https://github.com/mastermindx-market-intelligence/macro/pull/7608) |
| Title | `research(risk): classify five-session caution persistence as context` |
| Author | `chriswong6031-creator` |
| Base → Head | `main` ← `claude/risk-radar-caution-persistence-20260921` |
| Merge commit | `f5fd0e7e8e6d8ef55fa3b9c9d8e7e6d8ef55fa3b` |
| Merged at | 2026-09-21T11:23:11Z |
| Files changed | 10 (1 DSC + 2 research md + 5 evidence JSON/log + 1 script + 1 test) |
| Additions / Deletions | +2,335 / -0 |
| Kind | Descriptive research (no live authority changes) |

**Files added or modified (per `gh pr view 7608 --json files`):**

- `agentos/discoveries/DSC-RISK-RADAR-CAUTION-PERSISTENCE-IS-CONTEXT-NOT-ALERT.md` (new, +25)
- `research/grey_deer/RISK_RADAR_CAUTION_PERSISTENCE_PREREG_2026-09-21.md` (new, +78)
- `research/grey_deer/RISK_RADAR_CAUTION_PERSISTENCE_RESULTS_2026-09-21.md` (new, +35)
- `research/grey_deer/evidence/caution-persistence-20260921/agentos.log` (new, +190)
- `research/grey_deer/evidence/caution-persistence-20260921/result.json` (new, +1,317)
- `research/grey_deer/evidence/caution-persistence-20260921/run.log` (new, +126)
- `research/grey_deer/evidence/caution-persistence-20260921/tests.log` (new, +30)
- `research/grey_deer/evidence/caution-persistence-20260921/verification.json` (new, +134)
- `scripts/research/risk_radar_caution_persistence.py` (new, +309)
- `tests/test_risk_radar_scorecard.py` (modified, +91)

## PR body — capability, result, and integrity

The body is structured cleanly into **Capability / Result / Integrity /
Evidence ceiling / source base** and is built around three explicit,
falsifiable numerical claims:

1. **Full usable history:** base rate 17.7%, persistent-five event rate 20.3%
   (1.15× lift), persistent condition active 63.4% of eligible sessions.
2. **2020+ slice:** base rate 17.6%, persistent-five event rate 22.7%
   (1.29× lift), persistent condition active 73.3% of eligible sessions.
3. **Distinct-event view:** 110 complete anchors; caution-or-higher existed
   by T0 for 106, persistent-five for 99. 77 persistence rows are
   left-censored at the T-21 window edge; among the 22 exact
   first-persistence leads, median lead is 11.5 sessions.

The body is honest about scope: "**five-session persistence is too common
for a new prominent warning badge. If used, it should be neutral duration
context inside Risk Radar (e.g. 'risk building has persisted'), never state
escalation or probability adjustment.**" It also reports the methodological
repair (the first successful event view exposed left-censoring at T-21; the
accepted result records that explicitly and reports a separate uncensored
median — "no streak length, target, state definition, or outcome rule
changed"). Integrity receipts listed: 6 focused method tests pass, 128
owning tests pass, script compiles, diff check passes, Agent OS
validation 0 errors (inherited warnings only), receipt hashes bind
script/tests/result/logs/inputs.

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
| PR body | High — operator/methodologist reader | PASS (jargon acceptable for research audience; key terms `caution_plus`, `persistent_caution_5`, `base rate`, `lift`, `fire rate` defined inline) |
| Preregistration markdown | High — internal protocol readers | PASS (each frozen definition named; "5% / 21-native-observation target" defined; `caution_plus`/`persistent_caution_5` defined; unknown/missing-state handling explicit) |
| Results markdown | High — internal research audience | PASS (numbers paired with interpretation; explicit "Evidence ceiling" callout — reconstructed historical, not issued forecast) |
| DSC discovery markdown | High — cross-session researchers | PASS (claim/falsifier/so_what triplets; honest scope language) |
| `scripts/research/risk_radar_caution_persistence.py` | None — code | N/A |
| `tests/test_risk_radar_scorecard.py` diff | None — code | N/A |
| `evidence/.../result.json`, `verification.json` | None — machine artifacts | N/A |

**Notes on prose quality (research-audience standard, not user-facing):**

- The prereg defines `caution_plus`, `persistent_caution_5`, the primary
  target (SPY close-relative max loss ≥5% within 21 native SPY closing
  observations), and the eligible-population construction explicitly. The
  five-session rule is frozen as "one trading week for product
  readability, not selected from a performance sweep" — a clear honest
  framing that pre-empts a cherry-picking accusation. Unknown/missing state
  handling is documented ("breaks the streak and is excluded from the
  eligible denominator for the affected date").
- The results doc pairs every table value with a "Product implication"
  paragraph and an explicit "Evidence ceiling" callout — "reconstructed
  historical display research, not genuinely issued forecast history.
  A favorable result can support duration copy only; it cannot escalate
  the state or alter odds, gates, or capital authority." That ceiling
  language mirrors the body verbatim and is the right framing for a
  display-tier study.
- The DSC schema uses `confidence: verified` and `verified_by: ...` —
  these are DSC's own status convention (out-of-scope of the user-facing
  `validated` gate per its allowlist schema), not an affirmative user-
  facing claim. Same convention as #7599 (already audited).
- Mild readability note (non-blocking): the body uses the slug
  "5%-within-21-native-observation" inline without the parenthetical
  "(= close-relative max loss ≥5% within the next 21 SPY closing
  observations)" that the prereg carries. Same minor pattern as #7599
  — a reader landing on the PR body alone has to consult the prereg for
  the definition. Not a fail.
- No banned-vocab hits: "validated" is not asserted anywhere in the PR
  body or in any user-facing research doc (see validated-claims below);
  no "ships with", "production-ready", or other user-trust language; no
  per-exemplar `quote → inference` pattern that would route to a
  falsifier ("persistent-five caution is too common to serve as a new
  prominent alert" is itself the right framing — the study *is* the
  refutation of the alert interpretation).
- **One nuance worth flagging:** the body says "**Product implication:**
  five-session persistence is too common for a new prominent warning
  badge." This is an operator-facing research conclusion, NOT a user-
  facing product statement, and it is internally consistent with the
  63.4% / 73.3% fire rates (a badge that fires ~2/3 of the time is
  noise, not signal). The framing honors the standing rule that
  "tripwires keep evaluating in the background" and avoids the banned
  "thesis refuted / falsifier fired" surface language.

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
(b) Python source under `scripts/research/` and `tests/`, or (c) JSON/log
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

The gate's scanned surface set is `templates/`, `site/*.js`, generated
`*_data.js`, `engine/` display-copy fields, and `engine/` source copy. This
PR touches **none of those directories** — the 10 files are in
`agentos/discoveries/`, `research/grey_deer/`, `research/grey_deer/evidence/`,
`scripts/research/`, and `tests/`. Out-of-scope by construction.

**Direct textual scan of every prose-bearing file in the PR:**

```
$ gh pr diff 7608 --repo mastermindx-market-intelligence/macro | grep -iE "validated|已验证|经验证|经过验证"
(no hits)
```

- PR body — no `validated` usage.
- Preregistration markdown — no `validated` usage.
- Results markdown — no `validated` usage.
- DSC discovery — uses `verified_at` / `verified_by` / `confidence: verified`
  (allowed — these are DSC schema fields, not the user-facing word).
- `scripts/research/risk_radar_caution_persistence.py` — no `validated` usage.
- `tests/test_risk_radar_scorecard.py` diff — no `validated` usage.
- All `evidence/.../*.json` files — no `validated` usage in keys or values.

**Verdict:** N/A → PASS. The PR does not introduce any affirmative
`validated` claim on a scanned surface; nothing to back, nothing to fail.

**Companion claim-integrity check (this audit, not the existing gate):**

Numerical claims in the PR body were verified against
`research/grey_deer/evidence/caution-persistence-20260921/result.json` and
`verification.json`:

| Body claim | result.json value | Body quote | Match? |
|---|---|---|---|
| Full base rate 17.7% | 0.176535 | "17.7%" | ✓ rounded |
| Full persistent-5 event rate 20.3% | 0.202541 | "20.3%" | ✓ rounded |
| Full lift 1.15× | 1.147314 | "1.15x" | ✓ rounded |
| Full persistent-5 fire rate 63.4% | 0.634110 | "63.4%" | ✓ rounded |
| 2020+ base rate 17.6% | 0.176470 | "17.6%" | ✓ rounded |
| 2020+ persistent-5 event rate 22.7% | 0.227495 | "22.7%" | ✓ rounded |
| 2020+ lift 1.29× | 1.289143 | "1.29x" | ✓ rounded |
| 2020+ persistent-5 fire rate 73.3% | 0.733493 | "73.3%" | ✓ rounded |
| 110 complete event anchors | `event_view.n_events = 110` | "110" | ✓ exact |
| Caution-or-higher by T0 = 106 | `caution_by_t0 = 106` | "106" | ✓ exact |
| Persistent-five by T0 = 99 | `persistent_by_t0 = 99` | "99" | ✓ exact |
| 77 left-censored at T-21 | `persistent_left_censored_n = 77` | "77" | ✓ exact |
| 22 exact first-persistence leads | `persistent_exact_lead_n = 22` | "22" | ✓ exact |
| Median exact-persistence lead 11.5 sessions | `persistent_median_lead_uncensored_sessions = 11.5` | "11.5" | ✓ exact |
| Window-bounded median 21.0 sessions (uncensored, flagged in DSC) | `persistent_median_lead_sessions_window_bounded = 21.0` | (results doc, explicit ceiling note) | ✓ exact |
| Persistent-five appeared before first 5% breach in 99 event rows | `persistent_before_breach_n = 99` | "99" (results doc) | ✓ exact |

**Sanity tie-out:**

- `caution_event_recall = 106/110 = 0.9636…` ✓ matches
  `event_view.caution_event_recall = 0.963636`.
- `persistent_event_recall = 99/110 = 0.9000` ✓ matches
  `event_view.persistent_event_recall = 0.900000`.
- `caution_by_t0 + persistent_left_censored_n = 106 + 77 = 183` is NOT
  expected to equal anything (overlapping categories, by design — caution
  need not be persistent, persistent need not be left-censored); sanity
  check is on the individual counts only, all match.
- `since_2020.population_sha256 = 7c04d5ee085c01bb5c514fc2602141cd01b83cf4745da745ad2dca6fa9ee73ec`
  equals
  `canonical_crosscheck.since_2020.outcomes_sha256 = 7c04d5ee085c01bb5c514fc2602141cd01b83cf4745da745ad2dca6fa9ee73ec`
  — **internal consistency verified for the 2020+ slice**.
- For the full slice the two SHAs differ by design
  (`population_sha256` hashes daily state fingerprints;
  `outcomes_sha256` hashes the canonical 5%-breach outcomes of the
  different population — `n_days = 8195` for canonical vs `n = 8191` for
  the daily full set; 4 days excluded for missing prices per prereg
  rule). Both are present and consistent with their stated population
  sizes.

**Methodological-integrity receipts (from verification.json):**

- `authority.gate_changed = false`, `live_model_changed = false`,
  `policy_changed = false`, `probability_changed = false`,
  `status = descriptive_only` — matches body claim of no live change.
- `corrections[0]` records the missing-pandas import repair (pre-outcome
  test stage); `corrections[1]` records the T-21 left-censoring repair
  with `outcome_read: true` flag and an explicit "no target/streak/state
  rule changed" note — matches the body's methodological-integrity
  paragraph.
- `protected_skillpack = mastermindx-market-intelligence/Mastermind@0f4aeae4d25f3770474a7ac70e0ce12af6e2d075`,
  v1.0.1/bootstrap 1 — matches body.
- `protocol_commit = 1882492ee09ef9baefbf0412aed175388c23c631`,
  `source_base = 1dc11fb3eb326393c803bc2eff408db89bb91bc1` — match body.
- `verification.owning_suites = "128 passed"`,
  `focused_method_tests = "6 passed"`, `py_compile = pass`,
  `diff_check = pass`, `agentos = "0 errors; inherited warnings only"` —
  matches the body's method/integrity paragraph.
- `verification.result_sha256 = 858b61f9446fabebdfadb8a7dde10c2cdc407a4e347c48d4be0bdd03a4318521`
  — binds result.json to the accepted run.
- `threshold_sweep = false` — confirms the five-session streak was frozen
  before outcome inspection, not selected from a performance sweep (the
  honest framing already stated in the prereg).

## Overall verdict

**PASS.** PR #7608 is a clean descriptive-research delivery, sister to
PR #7599:

1. **Plain-language** — PASS. Body and research docs are readable to the
   intended internal audience, define every key term inline, and do not
   carry banned-vocab hits on any scanned surface. No user-facing surface
   was touched.
2. **Theme** — N/A → PASS. Zero theme-bearing files in the diff.
3. **Validated-claims** — N/A → PASS. Zero `validated` (or zh cognate)
   usage anywhere in the PR. Internal claim-integrity cross-check (body
   numbers vs `result.json`) ties out exactly on all 16 numerical claims
   tested, including the canonical cross-check SHA fingerprint for
   2020+, the event-latency partition (`caution_event_recall =
   106/110 = 0.9636`), and the left-censor accounting
   (`persistent_left_censored_n = 77`, `persistent_exact_lead_n = 22`,
   with the window-bounded median 21.0 explicitly flagged as censored
   and the uncensored median 11.5 reported separately).
4. **Methodological integrity** — verified. Both methodological
   corrections (missing pandas import; T-21 left-censoring) are recorded
   in `verification.json.corrections` with explicit `outcome_read` /
   `stage` flags that match the body's narrative, the `authority` block
   confirms `descriptive_only` (no live change), and `threshold_sweep =
   false` confirms the five-session rule was frozen before outcome
   inspection.

**Optional follow-up (non-blocking, same as #7599):** the PR body
references the "5%-within-21-native-observation target" without inlining
the parenthetical definition that the prereg carries; adding one inline
parenthetical would make the body self-contained for an external reviewer
landing without the prereg open. Not a fail.

**No remediation required for plain-language, theme, or validated-claims.**
Audit recorded per the qwen_auditor2 template; safe to merge.
