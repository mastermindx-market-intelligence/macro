# Macro instruction loading repair — October 11, 2026

Parent mission: execution-friction-repair-20261011-astra-001, Mastermind PR #1341.
Macro operation: execution-friction-macro-entrypoint-20261011-astra-001.
Source base: 395e5d6089e95aa907c48fae811ecb918fb26f95.

## Confirmed defect and delivered scope

The original root AGENTS.md is 81,628 bytes. Its context-economy section began at
byte 33,836 and execution-continuation section at byte 36,684. Both are beyond
Codex's documented default 32 KiB project-instruction budget. The inspected M2
user config did not set project_doc_max_bytes, and this protected Macro root had
neither AGENTS.override.md nor .codex/config.toml. At the default cap, the original
root ends mid-sentence in historical model routing, before the continuation laws.

This is a concrete instruction-transport defect. It is not proof of what every
account, profile or already-running conversation actually loaded. A session may
also read later instructions explicitly, at additional context and tool cost.

This patch moves the EXISTING execution-continuation and context-economy sections
to the first two operating sections, after the original introduction. Together
with that introduction they occupy 12,412 bytes and fit fully inside the default
project-document budget. Every original section remains byte-identical. Restoring
the original order reproduces SHA256
e2b2e6b95408bf3d83ceb76058fab0f73527165aa348182760ac917916518f00.
The reordered AGENTS.md is still 81,628 bytes, now SHA256
ead286d37639dd82771d18f20bb37c701a4a92db29f2e72bcd8f347f98ce3098.

No hook, settings, source lease, permissions, memory or capacity rule was changed.
This patch does not implement any platform-denied hook or policy-retirement edit
from the parent mission. It repairs ordering only, not the entire policy system.

## Verification

New instruction transport tests: five cases; three failed on original ordering,
then all five passed on the reordered source. They verify first/second sections,
full-prefix budget, exact byte preservation, and navigation/release controls.
Existing tests/test_execution_continuation_law.py: 19 passed in 5.50 seconds.
git diff --check returned no errors. No full sparse-worktree suite was run.

## Important remaining source contradictions

CLAUDE.md remains 88,920 bytes over 143 very long lines. It and AGENTS.md repeat
historical delivery/role rules and currently prescribe reading CLAUDE.md in full
at each task entry. This patch does NOT reduce total instruction size or resolve
those semantics. The parent candidate repairs the Mastermind entrypoints and two
M2 user profiles, but not all Macro, Cursor, plugin or memory sources.

Examples verified at this base, not modified here:
- CLAUDE.md line 11 says one session owns the complete chain and permits only a
  ratified HOLD-FOR-SOL as the non-merge terminal state; that does not establish
  an archived Web conversation as an available receiver.
- CLAUDE.md line 23 calls permission prompts administrative and says a permissive
  local setting means a prompt is never a blocker, then later says an explicit
  safety/permission refusal ends retry. The contradictory blanket sentence must
  not be used to bypass a real prompt or refusal.
- CLAUDE.md line 32 and corresponding AGENTS section forbid ALL_SCOPED_LANES_BLOCKED
  as terminal even while prescribing a closed set of real external exit states.
  Existing tests assert those words across four surfaces and the Stop hook has
  separate behavior. A root-only wording rewrite would not repair enforcement.

A deeper consolidation must distinguish current protected canonical procedure,
applicable engineering instructions and historical incidents; preserve real
permission/effect/release gates; and verify the actual instruction chain. Merely
raising the byte cap or importing the entire old guide would preserve the bloat.

## Platform sources checked October 11, 2026

- OpenAI AGENTS.md loading guide:
  https://developers.openai.com/codex/guides/agents-md
- OpenAI agent-loop explanation (default 32 KiB project instruction budget):
  https://openai.com/index/unrolling-the-codex-agent-loop/
- OpenAI September 11 guidance on overly broad skills and repeated instruction loading:
  https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra
- Anthropic project-memory and instruction loading:
  https://code.claude.com/docs/en/memory

Source publication, protected merge, local checkout update, fresh-session loading
and observed execution behavior are distinct. No running conversation reload,
company-wide adoption or completed parent mission is claimed by this patch.

## Resumed parent review — remove the permanent prose freeze

The active parent commission recovered this existing operation at head
`7d07168a08db2e9fb84cff56455114a944451385`, verified a clean Git working tree and no
open handles on the two scoped files, and continued the test-only repair. The
workspace status wrapper reported PRESERVED_DIRTY while direct Git status was clean;
that discrepancy was retained rather than treated as permission or source liveness.

The original migration equality check was appropriate as one-time evidence, but
running it permanently in CI would reject every later authorized instruction edit.
Two discriminating regressions reproduced that defect: appending a harmless
clarification or adding a unique domain section failed the old test. The ongoing
contract now allows those changes while retaining the original required sections,
uniqueness, ordering, loaded-prefix budget, navigation and release/effect controls.
Explicit negative tests still reject missing or duplicate operating sections.

Verification: `python3.11 -m unittest discover -s tests -p test_instruction_budget_order.py -v`
went from 7 cases with 2 failures to **9 passed, 0 failed**. Logs:
`/tmp/execution-macro-hash-red-20261011.log` and
`/tmp/execution-macro-hash-green-20261011.log`. The original baseline digest remains
unchanged in instruction_order_baseline.json. No AGENTS.md, CLAUDE.md, hook,
permission, settings, runtime, worker or memory bytes changed during this repair.

Review comment `5483271673` on PR #8795 records both the now-repaired permanent-hash
trap and the separate unresolved contradiction that describes real permission
prompts as administrative. The GitHub connector was the PR author's account, so
this comment is not an independent approval or a formal change-request gate. The
attempted formal change request returned GitHub 422 with no review effect; it was
not resubmitted under another account.

The instruction-order fix still requires its actual review/release conditions and
fresh-loading proof. The unsafe blanket permission wording remains a distinct held
policy issue; no blocked policy-retirement action was replayed by this test repair.
