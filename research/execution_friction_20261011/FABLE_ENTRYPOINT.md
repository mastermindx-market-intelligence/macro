# Fable instruction-entrypoint repair — October 11, 2026

Parent: `execution-friction-repair-20261011-astra-001`, Mastermind #1341.
Source operation: `execution-friction-fable-entrypoint-20261011-astra-001`.
Macro base: `6ba70f04ecbc5d9e91316baae44f9e2247956a28`.

## Measured defect and repair

The canonical Fable SKILL.md was 39,110 bytes, advertised for almost every
substantial task, and additionally required the complete engineering reference.
The M2 home copy was 38,677 bytes. Native Codex Macro prompt construction advertised
that broad trigger. These are instruction-volume/discovery observations, not a
measured model-latency, quality or billing penalty.

The normal source entrypoint is now **5,773 bytes, an 85.24% reduction**. It keeps
assignment, continuation, evidence, custody, effect, native-policy, budget, consent
and release boundaries explicit, and routes to only the relevant existing section.
A current source pin and accepted evidence are reused across phases. Simple answers
and unchanged status checks do not need a new full skill load.

The complete original SKILL.md is preserved verbatim in
`.claude/skills/fable-mode/references/seat-doctrine.md`, including S.1–S.8,
O.1–O.17, L.1–L.14 and A.1–A.7. One-time byte comparison matched all 39,110 bytes and
SHA256 `0a1c9dac17ea7c0a564586d56b897ee74ab10934861c525a6d4a4d929bc6a064`.
Its `references/...` paths remain package-root relative, explicitly explained by
the new entrypoint. This hash is migration evidence, not a permanent prose freeze.

The `.agents/skills/fable-mode/SKILL.md` pointer retains same-checkout identity and
refuses silent home/revision substitution. Existing R31 tests still verify every
numbered rule and all six references at their retained location; no guidance check
was deleted. The new entrypoint is not another policy/lifecycle owner.

## Verification

Seven red source-transport cases produced six failures and one missing-reference
error. After the split, the new tests and existing grader/source contracts passed:

`python3.11 -m pytest tests/test_fable_entrypoint_budget.py tests/test_grader_manifest.py -q -o addopts='' --tb=short`

**26 passed, zero failed.** Logs are `/tmp/execution-fable-entry-red-20261011.log`
and `/tmp/execution-fable-entry-green-20261011.log`. `git diff --check` passed.

A fresh `codex debug prompt-input` in the candidate exited0. The rendered prompt
contains the new short trigger, not the former `Load it at the start of ANY session
that orchestrates` trigger. Output: 73,334 bytes, SHA256
`cbd08d35d22d4990e0fe6554e977a238f24c461aeea3e42092b00aa7b37ce816`.
No model request was sent. This proves native CLI discovery/rendering, not behavior,
existing-session reload or all-account installation. Raw prompt content is private.

## Scope and remaining delivery

Immutable runtime distillation `config/fable_mode_core.md`, grader manifest,
runtime injection, Stop/routing hooks, auth/permission settings, source leases,
active workers, provider budgets and native memory are unchanged. No previously
platform-denied hook or memory effect was replayed. Detailed historical text stays
subordinate to current governing procedure; this split does not bypass a real gate.

Adjacent PR #8413 was inspected at `7c541a2dc416bb9c56ffb4efa7c2e4aecf4d7562`, last
updated October4. A historical PR is not a live writer claim. This operation owns an
isolated current-source checkout; the active Macro #8795 paths are disjoint.

Independent review, current-head CI, ordinary release and actual source-owner
installation remain required. No unrelated application deployment, automatic Web
session wake or fleet-wide completion is claimed.
