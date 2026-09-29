---
key: orch-audit-macro-pr-7586-2026-09-21
title: 'orch(audit): record macro PR #7586 plain-language/theme/validated-claims audit (2026-09-21)'
pr: 7586
repo: mastermindx-market-intelligence/macro
merge_commit: 1dc11fb3eb326393c803bc2eff408db89bb91bc1
author: chriswong6031-creator
merged_at: 2026-09-21T08:50:20Z
branch: claude/risk-radar-episode-warning-path-20260920
base: main
files_changed: 10
additions: 1349
deletions: 552
kind: research_descriptive_only
verdict: PASS
date: 2026-09-21
---

# Macro PR #7586 — plain-language / theme / validated-claims audit

Audit scope: plain-language compliance, theme compliance, and validated-claims
compliance of merged macro PR #7586 (`research(risk): measure warning
persistence at fixed episodes`), per the qwen_auditor2 audit template.

This PR is **research-only / descriptive** — the body and the DSC entry
explicitly state "descriptive research only; no live model, score, probability,
threshold, context-gate rule, policy or ledger changes" and the result is
display-tier context only. Scope of plain-language gating is therefore the
body, the preregistration + results markdown, the research report
(`reports/risk-radar-episode-atlas.md`), and the DSC discovery; theme
compliance is N/A (no user-facing UI surface touched); validated-claims
compliance is N/A (no user-facing surface touched).

This PR is structurally a sibling of PR #7608 (also audited today) and
PR #7599: same `research(risk)` lane, same descriptive-only posture, same
absence of live authority change, same evidence-receipt discipline.

## PR metadata

| Field | Value |
|---|---|
| Repo | `mastermindx-market-intelligence/macro` |
| PR | [#7586](https://github.com/mastermindx-market-intelligence/macro/pull/7586) |
| Title | `research(risk): measure warning persistence at fixed episodes` |
| Author | `chriswong6031-creator` |
| Base → Head | `main` ← `claude/risk-radar-episode-warning-path-20260920` |
| Merge commit | `1dc11fb3eb326393c803bc2eff408db89bb91bc1` |
| Merged at | 2026-09-21T08:50:20Z |
| Files changed | 10 (1 DSC + 2 research md + 1 report md + 1 data JSON + 3 evidence files + 1 script + 1 test) |
| Additions / Deletions | +1,349 / -552 |
| Kind | Descriptive research (no live authority changes) |

**Files added or modified (per `gh pr view 7586 --json files`):**

- `agentos/discoveries/DSC-RISK-RADAR-WARNING-PERSISTENCE-GATE.md` (new, +25)
- `reports/risk-radar-episode-atlas.md` (modified, +52/-63 net approx)
- `reports/risk_radar_episode_atlas.json` (modified, +620/-463)
- `research/grey_deer/RISK_RADAR_EPISODE_WARNING_PATH_PREREG_2026-09-21.md` (new, +25)
- `research/grey_deer/RISK_RADAR_EPISODE_WARNING_PATH_RESULTS_2026-09-21.md` (new, +35)
- `research/grey_deer/evidence/episode-warning-path-20260921/atlas-run.log` (new, +93)
- `research/grey_deer/evidence/episode-warning-path-20260921/tests.log` (new, +29)
- `research/grey_deer/evidence/episode-warning-path-20260921/verification.json` (new, +144)
- `scripts/research/risk_radar_episode_atlas.py` (modified, +217/-26)
- `tests/test_risk_radar.py` (modified, +46/-0)

## PR body — capability, result, and integrity

The body is structured cleanly into **Outcome / Protocol and result /
Verification / Evidence ceiling** and is built around a single explicit
falsifiable claim:

> "the broad-market confirmation gate was closed at all five fixed T0s, so
> none had an elevated-or-higher gated headline at T0" + "On the five
> preregistered Risk Radar reference anchors, old EARLY component
> classifications do not imply a warning persisted into the peak."

The body is honest about scope: "**This does not prove the gate is wrong. It
identifies the next falsifiable question: whether the gate predominantly
filters false positives or delays useful escalation into selloffs.**"
Per-episode findings are reported plainly:

- 2018-09-20: caution at T-21, then calm/calm/watch at T-5/T-1/T0; 0/6
  caution+ sessions in the final five-session window.
- COVID, 2022, and Aug-2024: caution persisted across all 22 sessions
  into T0.
- SVB-era 2023-02-02: 18/22 caution+, 2/22 elevated+, then a 10-session
  caution run into T0.

Integrity receipts listed: protocol commit `31b05b7dda4b` froze the five
dates before generating the warning-path metrics; 51 owning tests pass;
`py_compile` passes; `git diff --check` passes; evidence receipt binds 17
stored inputs + output hashes + protocol commit + five-row result summary.
The body explicitly disclaims "**five episodes are selected historical
exemplars, not an unbiased population**" — the right ceiling for a
display-tier study.

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
the prereg/results markdown, the report markdown, the DSC discovery, and
the evidence JSON are all researcher- and reviewer-facing.
`reports/risk-radar-episode-atlas.md` is **not referenced by any template,
site page, or build script** (`grep -rln "risk-radar-episode-atlas"
templates/ site/ scripts/build_*.py` returned zero hits), so it does not
cross into the user-facing surface set either. Plain-language gating
therefore applies to the **research markdown, the report markdown, and PR
body only**; the script, the test, and the JSON are inherently technical
and carry no plain-language exposure.

| Surface | Plain-language exposure | Verdict |
|---|---|---|
| PR body | High — operator/methodologist reader | PASS (jargon acceptable for research audience; key terms `detect_events()`, `gated headline`, `caution+`, `elevated+`, `context gate`, `T-21..T0` defined inline or via the prereg/results link) |
| Preregistration markdown | High — internal protocol readers | PASS (frozen rule set: "The five dates are frozen; the new analysis never substitutes the nearest `detect_events()` peak" is stated twice — once in the body, once in the results doc. `caution+`, `elevated+`, `signal coverage`, `Tier-A subscore coverage`, gate open/closed/unknown, and `canonical h5/h10/h21 forward losses` are named and used consistently) |
| Results markdown | High — internal research audience | PASS (numbers paired with interpretation; explicit "Evidence ceiling" callout — reconstructed historical, not issued forecast; explicit "**This does not prove the gate is wrong**" caveat) |
| DSC discovery markdown | High — cross-session researchers | PASS (claim/falsifier/so_what triplets; honest scope language; `confidence: verified` is DSC schema, not user-facing `validated`) |
| `reports/risk-radar-episode-atlas.md` | High — internal reviewer/researcher audience (not referenced by any user-facing surface) | PASS (every value paired with its definition; `*Pctile values are 0-1 causal trailing-504d percentiles. Asterisk (*) = elevated` footnote; "Generated: ... reconstructed historical states under the committed engine and historical inputs, not genuinely issued forecasts") |
| `reports/risk_radar_episode_atlas.json` | None — machine artifact | N/A |
| `scripts/research/risk_radar_episode_atlas.py` | None — code | N/A |
| `tests/test_risk_radar.py` diff | None — code | N/A |
| `evidence/.../*.json`, `*.log` | None — machine artifacts | N/A |

**Notes on prose quality (research-audience standard, not user-facing):**

- The prereg defines the protocol precisely: "The new analysis never
  substitutes the nearest `detect_events()` peak" — explicit guard against
  post-hoc peak fitting. The T-21/T-5/T-1/T0/T+5 offsets, gate
  open/closed/unknown, signal/subscore coverage, caution/elevated
  persistence, and canonical h5/h10/h21 forward losses are all named and
  used consistently between the prereg, the script, the results doc, the
  report, and the JSON.
- The results doc pairs every table value with an interpretation paragraph
  and an explicit "Evidence ceiling" callout — "reconstructed historical
  display research, not genuinely issued forecast history. ... No authority-
  bearing model change follows." That ceiling language is mirrored in the
  DSC (`so_what: ... no gate/model retune follows until false-positive
  suppression versus escalation delay is tested on a broader population`)
  and is the right framing for a display-tier study.
- The DSC schema uses `confidence: verified` and `verified_by: "PR #7586;
  protocol 31b05b7dda4b; 51 tests passed"` — these are DSC's own status
  convention (out-of-scope of the user-facing `validated` gate per its
  allowlist schema), not an affirmative user-facing claim. Same convention
  as #7599 and #7608 (both already audited today).
- No banned-vocab hits: "validated" is not asserted anywhere in the PR
  body or in any user-facing research doc (see validated-claims below);
  no "ships with", "production-ready", "this is the answer", or other
  user-trust language; no per-exemplar `quote → inference` pattern that
  would route to a falsifier — the study *is* itself the falsifier of
  the EARLY-implies-persisted hypothesis, and it says so plainly.
- **One nuance worth flagging:** the body uses the slug `EARLY` inline in
  the results table without re-defining it as "first-elevated-within-T-63
  per leg"; a reader landing on the PR body without the prereg or the
  report open would need to consult one of those for the full definition.
  This is the same minor pattern as #7599 and #7608 — a one-line
  parenthetical would make the body self-contained for an external
  reviewer. Not a fail.
- **One scope-honesty note:** the body states "**5 selected historical
  exemplars, not an unbiased population**" — this is exactly the
  population-validity ceiling the audit coverage gate (operator 2026-08-10)
  asks for, and the DSC `so_what` carries the falsifiable next-step
  ("tested on a broader population"). The framing honors the standing rule
  that "tripwires keep evaluating in the background" and avoids the banned
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

All ten files are either (a) research markdown / agentos discovery
markdown / report markdown, (b) Python source under `scripts/research/`
and `tests/`, or (c) JSON/log receipts under
`research/grey_deer/evidence/`. **No theme-bearing surface is touched.**

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
`agentos/discoveries/`, `reports/`, `research/grey_deer/`,
`research/grey_deer/evidence/`, `scripts/research/`, and `tests/`.
Out-of-scope by construction.

**Direct textual scan of every prose-bearing file in the PR:**

```
$ gh pr diff 7586 --repo mastermindx-market-intelligence/macro \
    | grep -iE "validated|已验证|经验证|经过验证"
  (matches are JSON keys in reports/risk_radar_episode_atlas.json:        \
   "is_validated_tier": false,   — these are removed/restructured        \
   lines in the JSON data file, not the word "validated" in user-         \
   facing prose; the diff shows only removed lines, no additions)
```

The `is_validated_tier` matches are an existing JSON schema field that
records per-leg "is this leg a validated tier?" status — all values are
`false` and the diff is removing redundant repetitions (the field was
being repeated for each leg, and the change consolidates it). **No new
`validated: true` claim is added**; the field is a per-leg boolean and
none of the legs flip to `true` in this PR. This is consistent with the
descriptive-only scope of the study.

- PR body — no `validated` usage.
- Preregistration markdown — no `validated` usage.
- Results markdown — no `validated` usage.
- DSC discovery — uses `verified_at` / `verified_by` / `confidence: verified`
  (allowed — these are DSC schema fields, not the user-facing word).
- `reports/risk-radar-episode-atlas.md` — no `validated` usage.
- `reports/risk_radar_episode_atlas.json` — uses `is_validated_tier`
  (boolean per-leg data field; no value flips to `true`).
- `scripts/research/risk_radar_episode_atlas.py` — no `validated` usage.
- `tests/test_risk_radar.py` diff — no `validated` usage.
- All `evidence/.../*.json` files — no `validated` usage in keys or values.

**Verdict:** N/A → PASS. The PR does not introduce any affirmative
`validated` claim on a scanned surface; nothing to back, nothing to fail.

**Companion claim-integrity check (this audit, not the existing gate):**

Numerical claims in the PR body were verified against
`research/grey_deer/evidence/episode-warning-path-20260921/verification.json`
and the table content in `reports/risk-radar-episode-atlas.md`:

| Body claim | report.md / verification.json value | Body quote | Match? |
|---|---|---|---|
| 2018Q4 T-21..T0 caution+ | 8/22 (36.4%) | "8/22" | ✓ exact |
| 2018Q4 T-21..T0 elevated+ | 0/22 (0.0%) | "0/22" | ✓ exact |
| 2018Q4 caution+ run into T0 | 0 | "0" | ✓ exact |
| 2018Q4 h21 max loss | -6.9% | "-6.9%" | ✓ exact |
| 2018Q4 T-5..T0 caution+ | 0/6 (0.0%) | "0/6" | ✓ exact |
| COVID T-21..T0 caution+ | 22/22 (100.0%) | "22/22" | ✓ exact |
| COVID h21 max loss | -29.1% | "-29.1%" | ✓ exact |
| 2022 T-21..T0 caution+ | 22/22 (100.0%) | "22/22" | ✓ exact |
| 2022 h21 max loss | -9.7% | "-9.7%" | ✓ exact |
| SVB T-21..T0 caution+ | 18/22 | "18/22" | ✓ exact |
| SVB T-21..T0 elevated+ | 2/22 | "2/22" | ✓ exact |
| SVB caution+ run into T0 | 10 | "10" | ✓ exact |
| SVB h21 max loss | -5.3% | "-5.3%" | ✓ exact |
| Aug-2024 T-21..T0 caution+ | 22/22 (100.0%) | "22/22" | ✓ exact |
| Aug-2024 h21 max loss | -8.4% | "-8.4%" | ✓ exact |
| Broad-market gate T0 | closed at all five fixed T0s | "the broad-market confirmation gate was closed at all five fixed T0s" | ✓ exact |

**Sanity tie-out (from verification.json):**

- `protocol_commit = 31b05b7dda4be22be2ee55217aecfd475d2ed569` is stated
  in the body and present in verification.json.
- `source_base` and the five fixed reference dates (2018-09-20,
  2020-02-19, 2022 peak reference, 2023-02-02 SVB, 2024-08 yen-carry) all
  reconcile between the body, the report, the results doc, and
  verification.json.
- `signal coverage = 11/11` and `Tier-A subscore coverage = 4/4` at T-21,
  T-5, T-1, T0 for all five episodes match the per-episode headline-path
  tables in the report.
- The `verification.fixed_named_anchor` field replaces the previous
  `detect_events()` onset source for all five episodes, consistent with the
  body's "never substitutes the nearest `detect_events()` peak" rule.

**Methodological-integrity receipts (from verification.json):**

- The body claims `descriptive_only` research — verification.json
  `status: descriptive_only` (matches).
- The body claims `51 passed` for the owning suite — verification.json
  `owning_suites = "51 passed"` (matches the body verbatim).
- The body claims `python3 -m py_compile scripts/research/risk_radar_episode_atlas.py`
  passes — verification.json `py_compile = pass` (matches).
- The body claims `git diff --check` passes — verification.json `diff_check
  = pass` (matches).
- The body explicitly disclaims model/score/policy/probability changes —
  DSC `so_what` carries the falsifiable next-step and explicitly states
  "no gate/model retune follows until ... tested on a broader population".

## Overall verdict

**PASS.** PR #7586 is a clean descriptive-research delivery, sister to
PR #7608 and PR #7599 (both audited earlier today):

1. **Plain-language** — PASS. Body, prereg, results, report, and DSC are
   readable to the intended internal audience, define every key term
   inline (or via consistent cross-reference), and do not carry banned-
   vocab hits on any scanned surface. No user-facing surface was touched
   (the report markdown is not referenced by any template or site page).
2. **Theme** — N/A → PASS. Zero theme-bearing files in the diff.
3. **Validated-claims** — N/A → PASS. Zero `validated` (or zh cognate)
   usage anywhere in the PR prose. The `is_validated_tier` JSON-key hits
   are existing per-leg data fields, all `false`, and none flip to
   `true`. Internal claim-integrity cross-check (body numbers vs the
   report and verification.json) ties out exactly on all 16 numerical
   claims tested, including the closed-gate finding at all five fixed T0s
   and the per-episode caution+ counts.
4. **Methodological integrity** — verified. The protocol commit is named
   in both the body and verification.json, the `fixed_named_anchor`
   source replaces `detect_events()` onset consistently across all five
   episodes (the "never substitutes the nearest peak" rule is honored),
   and the DSC `so_what` correctly identifies the next falsifiable
   question (false-positive suppression vs escalation delay on a broader
   population) without claiming authority-bearing model change.

**Optional follow-up (non-blocking, same pattern as #7599 and #7608):**
the PR body uses the `EARLY` slug inline in the results table without a
parenthetical re-definition tying it to the prereg rule ("first elevated
within T-63, with explicit left-censoring marks"); adding one inline
parenthetical would make the body self-contained for an external reviewer
landing without the prereg or report open. Not a fail.

**No remediation required for plain-language, theme, or validated-claims.**
Audit recorded per the qwen_auditor2 template; safe to merge (already
merged at `1dc11fb3` on 2026-09-21T08:50:20Z).
