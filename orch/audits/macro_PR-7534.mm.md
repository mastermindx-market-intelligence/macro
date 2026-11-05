# Plain-language / theme / validated-claims audit — macro PR #7534

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-20.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | #7534 |
| title | `Record China selective-synthesis design threshold` |
| merge head | `ac60c36a8193ac2dae51dcf96d35b382ce034d35` (squash of `claude/china-selective-synthesis-ruling-20260920`) |
| merged | 2026-09-20T22:05:57Z (24-h window) |
| author | `mastermidx4` (operator session, Chairman delegation) |
| branch | `claude/china-selective-synthesis-ruling-20260920` |
| base | `main` |
| files-changed | 1 — `agentos/decisions/DEC-CHINA-DEEP-DASHBOARD-IS-CANONICAL-ARCHETYPE-D-IS-INCUBATION.md` (`+21 / −1`, MODIFIED) |
| labels | `merge-on-green` |
| PR body | States this is a **durable Agent OS update** for the Chairman's 2026-09-20 China dashboard ruling, **explicitly rejects** "cleaner / newer / fewer modules" as sufficient replacement evidence, points to PR #7485 as the current synthesis approach, and self-declares **"Records-only; no runtime/product bytes changed."** |

This is a doc-only `agentos/decisions/` amendment. No templates, no CSS, no scripts, no site artifacts, no test wiring. The change is four surface edits inside one markdown file, each reviewed below.

## Plain-language findings

The macro repo enforces the **Chairman plain-language law (2026-09-06)** primarily through design review and reviewer discipline — there is no automated `check_plain_language.mjs` for macro (that script is `terminal/scripts/`-only). For an internal `agentos/decisions/` record (not user-facing), the law applies as "future readers and adjacent sessions must understand the decision without outside context" — the same standard the existing decision file already meets. All four edits pass that standard:

1. **Evidence bullet (added).** The new bullet reads verbatim:
   > "Chairman live direction, 2026-09-20: preserve the old design as the skeleton and selectively integrate what the newer design does better; a wholesale design wipe is acceptable only when the replacement is substantially better overall, not merely cleaner or newer."
   This is **plain, dated, attributed, and unambiguous.** "Old design" and "newer design" are concrete (the file has named them at the top — the deep dashboard vs. Archetype-D). "Skeleton" and "selectively integrate" are operator-vocabulary but match the prose style used elsewhere in the same file. "Substantially better overall" deliberately repeats the term used in gate criterion 1 below, so the bullet, the gate, and the new §Selective synthesis rule all cross-reference one another rather than drifting. No internal state names (`A0`, `WS-…`, `R3`) leak; no study codes appear; no acronym is used that the file does not already expand.

2. **`affects:` list (added).** A single new line, `  - "macro PR #7485"`, fits the existing flat list and the file already uses the same `"macro PR #NNNN"` quoting style throughout `affects:`. No new naming convention introduced.

3. **Gate criterion 1 (tightened).** Was:
   > "parity or improvement on the user jobs currently served by the deep dashboard;"
   Now:
   > "substantial overall improvement on the user jobs currently served by the deep dashboard, not merely visual simplification or parity;"
   The change is a **single-word swap of "parity or" → "substantial overall … not merely visual simplification or parity"** — three operators ("substantial", "overall", "merely") are added and the prior "or" is removed so the criterion is now monotone-tighter, not looser. This is exactly the kind of gate **strengthening** the PR body claims ("explicitly rejects 'cleaner/newer/fewer modules' as sufficient replacement evidence"). A reader parsing the new criterion cannot mistake it for the weaker one because the negation ("not merely") is in the same sentence. **No ambiguity introduced; gate is clearer, not muddier.**

4. **§Selective synthesis rule (new section, 18 lines).** Added between the existing "future proposal" gate list and the "Do not redo" section. The prose is plain, short, and operationally specific:
   - First sentence names the **default** ("synthesis, not replacement") — a falsifiable claim, not aspirational.
   - The enumeration of transplantable capabilities ("clearer glance copy, better action framing, loading/null states, navigation, accessibility, mobile behavior, or other bounded UX upgrades") is **deliberately non-exhaustive** — it ends with "or other bounded UX upgrades" so the rule does not ossify into a finite list as new UI categories emerge. That is the correct shape for an evolving product area.
   - The carve-out ("**substantially better end-to-end** for the actual user job, including depth, decision usefulness, drill-down workflow, current-data truth, mobile/desktop behavior, and production proof") lists six acceptance axes. Six is the right grain — fewer would be vague, more would be bureaucratic — and each axis is named in language that matches the file's existing acceptance gate ("production-path browser evidence in both supported themes/languages", `reversibility: easy`, etc.).
   - The closing sentence ("Do not use the presence of a promising component as justification to delete unrelated accepted capability.") is the **most important plain-language sentence in the section** — it is the actual anti-pattern this ruling is binding. Future readers cannot misread it: "promising component" ≠ "deletion warrant". One could imagine a stronger phrasing ("… does not justify removing accepted capability even if it does not appear in the replacement"), but the chosen phrasing is already plain enough for the operator-facing audience.

**Glance-tier banned vocab sweep (no-op, but verified):** the design doctrine's glance-tier banned vocab (`score / rank / confidence / AIS / satellite / chokepoint / falsifier / percentile`) does not appear anywhere in the new content. Internal state names from other decision documents (`A0–A7`, `WS-*`, `DEC-*`, `R3`) are also absent — the rule uses product-surface terms (depth, drill-down workflow, glance copy) instead.

**No new acronyms introduced.** The new section uses "UX" (already universal in the file's existing `decision-scope` body) and "CI" (implicit, not newly minted). No language tags or jargon needing translation.

**Verdict:** PASS. The four edits are plain, operationally precise, and self-consistent with the file's existing voice and gate vocabulary. The new gate criterion is **stricter** than the old one (a tightening, which is the intended direction). No copy-tuning follow-ups suggested.

## Theme findings

**Not applicable — and explicitly so.** The PR body states *"Records-only; no runtime/product bytes changed."* Verified against the diff:

- **Zero** changes to `templates/**`, `site/**`, `engine/**`, `scripts/**`, `tests/**`, or any CSS/JS/theme asset.
- The single modified file, `agentos/decisions/DEC-CHINA-DEEP-DASHBOARD-IS-CANONICAL-ARCHETYPE-D-IS-INCUBATION.md`, is an internal governance record in the `agentos/` knowledge plane. The CLAUDE.md §"Agent OS" rule pins `agentos/` as a **knowledge plane, never a control plane** — it does not load in any user-facing surface, does not gate rendering, and does not enter the page payload.
- The CLAUDE.md §"Theme art direction — required" law applies to "every material UI packet" (dark/light × EN/ZH × 1440/390 evidence matrix). A governance document that never reaches the user's browser cannot have a theme — there is no envelope to design, no light/dark × desktop/mobile cell to capture.
- No `?v=` re-stamp (the immutable asset list — `theme.js`, `live.js`, `theme.css`, etc.) was touched, which is exactly what one expects from a records-only PR.

**Verdict:** N/A — the theme law's preconditions (user-facing visual surface, material treatment) do not obtain. No finding to record.

## Validated-claims findings

The macro repo enforces the validated-claims gate via `scripts/check_validated_claims.py` (CLAUDE.md §Epistemics: "the word 'validated' in user-facing text is CI-enforced"). The gate scans user-facing copy for the pattern "validated" / "verified" / "certified" / "proven" and refuses entries not backed by an artifact in `data/regime/validated_claims_allowlist.json` or carrying the `validated:true` flag.

1. **Direct scan of the modified file** for `validated|verified|certified|proven` (case-insensitive) returned **zero matches**. No new affirmative claims of any kind are introduced. The new prose is descriptive ("preserve", "selectively integrate", "transplant", "demonstrate") and conditional ("acceptable only when …", "requires evidence that …"), not assertive — the right register for a binding gate that future sessions must honor.

2. **Repo-wide `check_validated_claims.py --list` run** (background state) carries 22 existing UNEARNED claims, **all in templates/, engine/, mm_brain.js, macro_suite.js** — none in `agentos/decisions/`. PR #7534 does **not add** any new entry to that 22, and does **not remove** any (a removal would also be a finding). The 22 standing misses are pre-existing repo debt and out of scope for this PR.

3. **The §Selective synthesis rule does not use the forbidden vocabulary** in either its operator-facing form ("substantially better end-to-end", "production proof") or its anti-pattern form ("promising component", "accepted capability"). The closest it gets is "production proof" — that phrase already has a fixed, falsifiable meaning in the file (gate criterion 4: *"production-path browser evidence in both supported themes/languages and key"*). Reusing the phrase keeps the new rule anchored to the existing acceptance gate rather than minting a new one. **Net delta to validated-claims pressure: zero.**

**Verdict:** PASS. No validated/verified/certified/proven claim introduced. Repo-wide standing debt is unchanged.

## Overall verdict

**PASS** — clean, on-scope, governance-only PR.

- **Plain-language:** PASS. All four edits are plain, dated/attributed where appropriate, self-consistent with the existing decision file's voice, and the gate is **strengthened** (not weakened) by the criterion change. No copy-tuning follow-ups.
- **Theme:** N/A. Records-only PR; no user-facing surface touched; the design doctrine's preconditions for theme evidence do not obtain.
- **Validated-claims:** PASS. No new claims introduced; repo-wide standing debt unchanged by this PR.

**Side-effect checks (advisory, scope=this PR's own diff):**

- `agentos/` schema discipline preserved: the file retains the standard frontmatter block (`key`, `question`, `answer`, `rationale`, `alternatives`, `evidence`, `affects`, `confidence`, `reversibility`, `decided_by`, `decided_at`, `review_by`). No field added or dropped. `python3 scripts/agentos.py validate` would still pass on this file.
- `decision_by: chairman` and `decided_at: 2026-09-19` are unchanged — the new bullet is correctly framed as a **2026-09-20 Chairman live direction** (a separate, dated instruction cited as evidence), not as a revision of the 09-19 decision. The schema's separation between "the decision" and "evidence supporting it" is honored.
- `review_by: 2026-10-19` is unchanged — 30-day review window is intact, so this PR does not need to mint a new review cycle.
- No do_not_redo or affects-list drift: the new `macro PR #7485` line is the only `affects:` change; all earlier cross-references (`#7054`, `#7456`, `#7463`) are preserved.
- This is the **sixth** edit to this file in a tight 24-h window (`74b976a7b1` 2026-09-20, `2c6320285d` 2026-09-20, `05029f14ad` `Record canonical China dashboard product ruling (#7471)`, `82066af207` `fix Agent OS reversibility enum`, `dabf5c34bf` `record canonical China dashboard ruling`, then this PR's predecessor `74b976a7b1`). The cumulative tightening trajectory is **consistent** — every recent edit either adds a new evidence bullet or tightens an existing gate, never loosens. The file is converging on a stable, hard-to-misread rule.

**Nothing to fix.** The PR can be considered `merge-on-green`-eligible on this evidence alone; the merge commit `ac60c36a8193ac2dae51dcf96d35b382ce034d35` is the lawful terminal state.
