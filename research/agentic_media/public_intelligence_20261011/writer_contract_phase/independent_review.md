**PASS** for the bounded writer-contract review at exact head `558ca0a6cdeddf48fbbedc9f0d7f178882ef68e8`, limited to the diff `0b401a21a622..558ca0a6cded` in:

- [engine/press/writer.py](/Volumes/Mastermind%202/agent-workspaces/claude/14851c4656838a3b/mmx-press-validator-followon-20261014-c1dc27962b7d07c4/engine/press/writer.py:155)
- [tests/test_press_writer.py](/Volumes/Mastermind%202/agent-workspaces/claude/14851c4656838a3b/mmx-press-validator-followon-20261014-c1dc27962b7d07c4/tests/test_press_writer.py:149)

The patch accurately aligns the writer’s trusted prompt contract with the already-accepted validator behavior:

- The own-value instruction now correctly says that only sentences carrying a number anchored to a `[first_party]` fact receive share credit. It also correctly explains that `[third_party]` facts remain usable only when anchored, while receiving no share or receipt-floor credit. This matches [check_our_value](/Volumes/Mastermind%202/agent-workspaces/claude/14851c4656838a3b/mmx-press-validator-followon-20261014-c1dc27962b7d07c4/engine/press/validators.py:940) and [check_receipts](/Volumes/Mastermind%202/agent-workspaces/claude/14851c4656838a3b/mmx-press-validator-followon-20261014-c1dc27962b7d07c4/engine/press/validators.py:1005).
- The prompt renders the effective configured `our_value_min` rather than retaining a hard-coded 40% claim; the reviewed `37.5%` configuration case is covered.
- The new banned-language section uses the existing validator-owned copywriter lexicon import rather than forking terms. It accurately describes substring matching for phrase lists and boundary matching for word lists, includes the configured AI-tell phrases and pattern rules, and stays in the system prompt above the untrusted-evidence fence.
- Graceful prompt degradation is proportionate: if `validators._copywriter_lexicons()` cannot load, [writer._banned_language_lines](/Volumes/Mastermind%202/agent-workspaces/claude/14851c4656838a3b/mmx-press-validator-followon-20261014-c1dc27962b7d07c4/engine/press/writer.py:267) logs and omits only the unavailable rendered terms. It does not falsely treat the gate as passed. The downstream [check_banned_lexicon](/Volumes/Mastermind%202/agent-workspaces/claude/14851c4656838a3b/mmx-press-validator-followon-20261014-c1dc27962b7d07c4/engine/press/validators.py:1079) and [check_cheese_test](/Volumes/Mastermind%202/agent-workspaces/claude/14851c4656838a3b/mmx-press-validator-followon-20261014-c1dc27962b7d07c4/engine/press/validators.py:1120) remain fail-closed on that same import failure.
- The diff changes prompt construction only. The `RunState`, provider selection, single-provider attempt behavior, admitted token-cap path, budgets, and routing logic were not altered. The local diff contains no changes to those mechanisms.

Independent local verification completed:

```text
pytest -q tests/test_press_writer.py
64 passed in 7.32s
```

I also ran a local pure-Python boundary probe that verified all of the following:

- First-party share and receipt wording appears in the prompt.
- The banned-language block is in the trusted system prompt and absent from the untrusted evidence payload.
- The previously omitted enforced phrase `the backdrop` is rendered.
- Simulated copywriter-lexicon import failure still lets prompt construction complete with configured AI-tell phrases, while both affected validators return failure with `lexicon import failed`.

`git diff --check 0b401a21a622 558ca0a6cded` was clean. No remaining reproducible issue appeared in this bounded scope.

Limits: this review confirms prompt/validator contract alignment and preservation of local writer controls. It does not establish a provider call, staging effect, publication authorization, CI status, protected merge, installation, or live behavior. I made no edits, provider/CI/GitHub calls, staging actions, or worker creation.
