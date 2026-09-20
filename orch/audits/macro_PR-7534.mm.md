# Audit — mastermindx-market-intelligence/macro PR #7534

Mode: qwen_auditor2-style (plain-language / theme / validated-claims laws). One-pass audit against the merged head. No durable writes outside this report.

## PR metadata

| field | value |
| --- | --- |
| repo | `mastermindx-market-intelligence/macro` |
| PR | [#7534](https://github.com/mastermindx-market-intelligence/macro/pull/7534) |
| title | `Record China selective-synthesis design threshold` |
| merged | 2026-09-20T22:05:57Z via squash-merge to `main` |
| head | merge of `claude/record-china-selective-synthesis-design-threshold` (single commit `ac60c36a81`) — landed between the orch(audit) record PR #7544 (17:03Z) and the next orch(audit) sweep; this is the latest merged half-B PR in the 24-h window whose own audit-record PR (#7560, 22:12Z) merged BEFORE its audit file landed — the slot already-mapped to `macro_PR-7534.mm.md` is exactly this PR. |
| author / merger | `chriswong6031-creator` (operator, META-CEO A). |
| base | `origin/main` at the head immediately preceding the PR's only commit (the prior DEC file landed at `74b976a7b1 tighten China dashboard design-wipe gate` — see `git log --oneline --all -- agentos/decisions/DEC-CHINA-DEEP-DASHBOARD-IS-CANONICAL-ARCHETYPE-D-IS-INCUBATION.md`). |
| files | **1 changed (21 +, 1 −)**, all in `agentos/decisions/DEC-CHINA-DEEP-DASHBOARD-IS-CANONICAL-ARCHETYPE-D-IS-INCUBATION.md`. |
| half-B label | **half-B (Chairman ruling durable-memory half — the companion to the user-facing half-A waves that actually refactored the China surface; this is the Agent OS decision-record side that records the synthesis rule so a future B or C wave cannot re-propose a design wipe on a "cleaner/newer" basis alone).** |
| scope | Durable Agent OS update for the Chairman's 2026-09-20 China dashboard ruling: preserve the restored deep dashboard as the product skeleton, selectively transplant bounded improvements from incubation concepts, and require **substantial end-to-end product improvement** before any future wholesale design wipe. Explicitly rejects "cleaner/newer/fewer modules" as sufficient replacement evidence and points to PR #7485 as the current synthesis approach. Per PR body: "Records-only; no runtime/product bytes changed." |
| checks | `merge-on-green` label armed, all standard packs concluded green (`2f94539c` head's packs all `success` per the orch(audit) sweep that this PR sits within). PR body declares records-only — no `templates/`, no `site/`, no `engine/`, no `scripts/` (other than documentation helper bytes), no `tests/` touched. |
| gating scripts | `scripts/check_plain_language.mjs` — DOES NOT EXIST in macro (terminal-side only). Plain-language discipline on this records-only PR is read against the standing design-doctrine rules AND the DEC schema contract. `scripts/check_validated_claims.py` — exists; `--list` mode was run for this repo and surfaced the PR's surface (no matches in this file). `scripts/check_design_system.py` and `scripts/check_runtime_style_injection.py` — exist but apply only to material UI packets, and this PR carries zero UI bytes. |

## Diff content (full)

**`agentos/decisions/DEC-CHINA-DEEP-DASHBOARD-IS-CANONICAL-ARCHETYPE-D-IS-INCUBATION.md` (+21 / −1)**

Three logical hunks, all records-only:

1. **Evidence bullet added** (after the existing headless-Chrome DOM proof bullet, line 32 of the new file):
   > "Chairman live direction, 2026-09-20: preserve the old design as the skeleton and selectively integrate what the newer design does better; a wholesale design wipe is acceptable only when the replacement is substantially better overall, not merely cleaner or newer."

2. **`affects:` list extended** with one new PR reference: `macro PR #7485` (joining the existing `macro PR #7054` / `macro PR #7456` / `macro PR #7463`). PR #7485 is named in the PR body as "the current synthesis approach".

3. **Re-entry gate item 1 rewritten** (line 91 of the new file): from "parity or improvement on the user jobs currently served by the deep dashboard" → "substantial overall improvement on the user jobs currently served by the deep dashboard, not merely visual simplification or parity". The other 4 re-entry gate items (no silent loss of major intelligence surfaces or drill-down workflows; current-data correctness and null/degradation behavior; production-path browser evidence in both supported themes/languages and key viewport classes; migration plan that preserves the old production surface) are UNCHANGED.

4. **NEW section appended** (lines 103–119, 17 lines): `## Selective synthesis rule`. Three paragraphs:
   - Para 1 names the **default evolution path as synthesis, not replacement** and lists the kinds of bounded UX upgrades that may be transplanted (clearer glance copy, better action framing, loading/null states, navigation, accessibility, mobile behavior, "or other bounded UX upgrades") while the accepted deep dashboard "remains the information-architecture skeleton".
   - Para 2 elevates wholesale design wipe to **a separate product decision** with explicit gate criteria (substantial end-to-end improvement; depth / decision usefulness / drill-down / current-data truth / mobile-desktop / production proof listed by name) and explicitly names the failure mode the rule is designed to prevent: "Cleaner", "more modern", fewer modules, or a successful screenshot review is not sufficient evidence.
   - Para 3 names the **transplant-instead-of-replace principle** by name: "When a bounded idea from an incubation design is useful, transplant that capability into the canonical surface first. Do not use the presence of a promising component as justification to delete unrelated accepted capability."

No template bytes, no site bytes, no engine bytes, no script bytes, no test bytes, no CSS bytes, no JS bytes, no `.j2` byte, no plain-copy asset byte. The bytes that did change are pure markdown (frontmatter YAML addition to `evidence:` and `affects:`, and a body-section append).

## Plain-language findings

Macro repo does not host `terminal/scripts/check_plain_language.mjs` (Terminal-only). Plain-language discipline on macro is read against the standing design-doctrine rules. PR #7534 carries zero user-visible strings (records-only — no template, no site, no engine, no script, no test bytes touched). The doctrine's user-facing copy rules therefore do not apply to this PR's surface; the relevant gate is the **DEC schema contract** (frontmatter YAML keys + body section headings), which is the canonical internal-doc plain-language discipline for Agent OS records.

**Verdict: PASS.**

1. **Frontmatter schema is well-formed.** The diff adds one bullet to `evidence:` and one bullet to `affects:`, both list-form, both quoted-string values matching the existing pattern. No malformed YAML, no missing required keys, no orphan keys. Word-boundary grep on the diff hunks for the banned-vocab set in DEC files (`validated | verified | certified | approved | proofed | gauntlet | proven`) returns **0 hits in the PR-introduced hunks**. The single "approved" occurrence on line 9 of the resulting file ("is not approved to replace the production composition") is **PRE-EXISTING** from the original DEC (round 1 — `decide` epoch 2026-09-19), NOT introduced by this PR; the PR's `--` and `++` lines do not touch that sentence (verified by `git show ac60c36a81 -- agentos/decisions/DEC-CHINA-DEEP-DASHBOARD-IS-CANONICAL-ARCHETYPE-D-IS-INCUBATION.md`).
2. **The new "Selective synthesis rule" section is doctrine-consistent plain prose.** Each sentence is a short clause naming the principle ("The default evolution path is synthesis, not replacement"; "A wholesale design wipe is a separate product decision"; "When a bounded idea from an incubation design is useful, transplant that capability into the canonical surface first"). No legalese, no defined-term jargon, no acronym without spell-out on first use. Bilingual parity is not required for Agent OS records (those are AI-agent-facing, not user-facing); no ZH copy is needed or expected.
3. **The "substantial overall improvement" rewrite does not weaken the gate.** The original text "parity or improvement" allowed a wholesale replacement that merely matched the existing depth; the new wording explicitly excludes "visual simplification or parity" as sufficient. The rewrite tightens, not loosens. Conforming.
4. **No internal-state names leak into user-jargon.** The new section lists "clearer glance copy, better action framing, loading/null states, navigation, accessibility, mobile behavior" — these are the doctrine-prescribed UX upgrade classes (not study names, not internal cycle names, not raw slugs). "Glance copy" / "action framing" / "loading/null states" are the same vocabulary the design-doctrine "Glance tier = state + plain-word stance under hard word budgets" rule uses, so the DEC's wording stays inside the vocabulary the operator already approved.
5. **No translated text added.** The DEC file is a single-language markdown record; neither EN→ZH nor ZH→EN parity applies.
6. **No new frontmatter fields.** `decided_by: chairman`, `decided_at: 2026-09-19`, `review_by: 2026-10-19`, `confidence: high`, `reversibility: easy` — all preserved UNCHANGED. The PR did NOT mint a new DEC epoch (that would require `decided_at` to advance, plus a `superseded_by`/`supersedes` pair); the existing epoch simply accumulated one more evidence bullet and one more "affects" reference. This is the schema-correct way to record a follow-on ruling on the same DEC, per the agentos DEC contract (`agentos/schema/DEC.schema`).

Net new plain-language debt introduced by this PR: **0**.

## Theme findings

TP-0 art-direction law in force (operator 2026-08-27). The TP-0 gate explicitly scopes itself to "every material UI packet". PR #7534 carries **zero UI bytes** — no template, no CSS, no JS, no render. The `templates/china.html.j2` and `site/china.html` bytes are NOT touched; the existing rendered China surface is unchanged.

**Verdict: PASS (N/A — PR adds zero UI bytes; TP-0 carries no obligation on records-only markdown).**

1. **No template, site, engine, CSS, or JS bytes touched.** Verified by `gh pr view 7534 --repo mastermindx-market-intelligence/macro --json files --jq '.files[].path'` → exactly one path: `agentos/decisions/DEC-CHINA-DEEP-DASHBOARD-IS-CANONICAL-ARCHETYPE-D-IS-INCUBATION.md`. The PR body itself declares "Records-only; no runtime/product bytes changed", and the actual file list confirms it. `scripts/check_design_system.py --mode enforce-added` has nothing to check on this PR.
2. **`scripts/check_runtime_style_injection.py` — N/A.** No JavaScript bytes added; no inline `style=` attributes added to any HTML; no runtime stylesheet system authored or extended. The marker that would otherwise fail this check (`style.textContent = …`, parallel palette/token families, opaque runtime stylesheets) is structurally absent from the PR.
3. **Paired G6 wire sync preserved.** `python3 -m scripts.check_template_site_sync` governs `templates/<name>` ↔ `site/<name>` for non-`.j2` plain-copy pairs. PR #7534 touches neither a paired template nor a paired site copy, so the sync invariant holds by irrelevance (no pair to drift).
4. **Dark + light treatment language appears in the DEC body — but only as a reference to the existing TP-0 surface.** The new "Selective synthesis rule" paragraph names "mobile/desktop behavior" and "production-path browser evidence in both supported themes/languages" as evidence classes — both phrases reference the existing TP-0 dark/light evidence matrix without redefining it. Compliant referencing, not new UI authorship.

Net new theme debt introduced by this PR: **0**.

## Validated-claims findings

The standing rule is that the word "validated" (and its near-synonyms `verified | certified | approved | proofed | gauntlet | proven`) is CI-enforced in user-facing text (`scripts/check_validated_claims.py`). PR #7534 is not user-facing; it is internal Agent OS markdown, but the discipline should still hold at the source-of-truth layer (a DEC is how future agents reason — and the DEC schema already moves "approved" into allowed internal vocabulary once, see point 1 below).

`scripts/check_validated_claims.py --list` was run; **zero hits in this PR's file** (the only file touched by the PR). The pre-existing "is not approved to replace the production composition" line 9 of the resulting file is NOT introduced by PR #7534 — `git show ac60c36a81 -- agentos/decisions/DEC-CHINA-DEEP-DASHBOARD-IS-CANONICAL-ARCHETYPE-D-IS-INCUBATION.md` confirms the diff does not include that line.

**Verdict: PASS.**

1. **Zero banned-vocab occurrences in the PR-introduced hunks.** Word-boundary grep on the diff for `validated|verified|certified|proofed|gauntlet|proven` returns 0 hits; for `approved` returns 0 hits in the new evidence bullet, the new `affects:` line, the rewritten re-entry gate item 1, and the new "Selective synthesis rule" section. The single "approved" occurrence on line 9 of the resulting file pre-dates this PR (it is from the original round-1 DEC text authored 2026-09-19).
2. **The new "Selective synthesis rule" body uses no banned vocabulary.** Spot-check: "The default evolution path is synthesis, not replacement…A wholesale design wipe is a separate product decision…When a bounded idea from an incubation design is useful, transplant that capability into the canonical surface first. Do not use the presence of a promising component as justification to delete unrelated accepted capability." None of `validated | verified | certified | approved | proofed | gauntlet | proven` appears in those three paragraphs.
3. **The new evidence bullet uses no banned vocabulary.** "Chairman live direction, 2026-09-20: preserve the old design as the skeleton and selectively integrate what the newer design does better; a wholesale design wipe is acceptable only when the replacement is substantially better overall, not merely cleaner or newer." None of the banned-vocab tokens appear.
4. **No claim-of-fact is being asserted that isn't already in the DEC contract.** PR #7534 records a Chairman live direction (which is the authority `decided_by: chairman` already admits), adds PR #7485 to the `affects:` list (which is itself a reference, not an evaluation), and tightens the re-entry gate item 1. None of those four operations is a "validated X" claim in the standing rule's sense — they are durable-state appends under the DEC schema.
5. **No new "validated" claim introduced on a display tier.** The PR carries no user-visible copy, so the display-tier gauntlet rule (epistemics §"AT PROMOTION only: display-only until gauntleted") is structurally not triggered. The gauntlet itself (prereg/held-out/CIs) and its display-tier null-disclosure regime are unchanged by this PR.

Net new validated-claim debt introduced by this PR: **0**.

## Overall verdict

**PASS — records-only DEC update; no runtime/product bytes touched; plain-language / theme / validated-claims laws all carry no obligation on Agent OS markdown, and the PR honors each of them by not introducing banned vocabulary, not touching UI bytes, and staying inside the DEC schema.**

Key receipts:

- PR #7534 = pure Agent OS DEC append (`agentos/decisions/DEC-CHINA-DEEP-DASHBOARD-IS-CANONICAL-ARCHETYPE-D-IS-INCUBATION.md`; 21 +/1 −) — single file, single commit `ac60c36a81`.
- Plain-language: PR-introduced hunks carry zero banned-vocab occurrences; new section uses doctrine-aligned plain prose; DEC schema preserved (`decided_at` UNCHANGED → no new epoch mintage).
- Theme (TP-0): zero UI bytes; `scripts/check_design_system.py` and `scripts/check_runtime_style_injection.py` have nothing to enforce on records-only markdown; `scripts/check_template_site_sync` carries nothing to pair.
- Validated-claims: `--list` over the changed file returns zero matches in this PR's surface; the pre-existing "approved" on line 9 of the resulting file predates this PR and is unchanged by it.
- The PR records a **selective-synthesis default** for future China dashboard evolution: bounded UX upgrades transplant into the canonical deep surface; wholesale design wipe requires substantial end-to-end improvement (depth / decision usefulness / drill-down / current-data truth / mobile-desktop / production proof), not "cleaner / newer / fewer modules". PR #7485 is named as the current synthesis approach.

If a follow-on B/C wave on China re-proposes a wholesale wipe, the standing DEC + this ruling make the gate conditions explicit and the failure modes ("cleaner screenshot" / "fewer modules" / "modern aesthetic") named as insufficient evidence.
