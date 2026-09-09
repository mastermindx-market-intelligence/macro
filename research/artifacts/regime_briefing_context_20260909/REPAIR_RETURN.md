Implemented the bounded R1 repair only. No commit, push, PR, merge, network operation, model call, production-data generation, ledger write, watcher, or W0 change was made.

Changed paths:

- [engine/master_brain.py](/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/hmm-briefing-context-20260909/engine/master_brain.py)
- [templates/_aibrief_body.html.j2](/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/hmm-briefing-context-20260909/templates/_aibrief_body.html.j2)
- [tests/test_master_brain.py](/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/hmm-briefing-context-20260909/tests/test_master_brain.py)
- [tests/test_regime_label_honesty.py](/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/hmm-briefing-context-20260909/tests/test_regime_label_honesty.py)
- [research/artifacts/regime_briefing_context_20260909/RED.md](/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/hmm-briefing-context-20260909/research/artifacts/regime_briefing_context_20260909/RED.md)
- [research/artifacts/regime_briefing_context_20260909/GREEN.md](/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/hmm-briefing-context-20260909/research/artifacts/regime_briefing_context_20260909/GREEN.md)

The six R1 findings are repaired:

- Oversized positive and negative integers now yield an explicit unavailable probability context; `float()` overflow cannot silently remove the context.
- `transition_momentum.basis` now preserves `tm.basis`; it no longer substitutes `qv.source`.
- A present malformed, future, or source-inconsistent `model_fit_asof` makes the context unavailable. An absent cutoff remains explicitly unknown and does not by itself invalidate a valid current estimate.
- Date-only values require canonical `YYYY-MM-DD`; ISO week dates are rejected. Timezone-aware ISO timestamps remain supported.
- Deterministic evidence now names the most-supported house-labelled state, reports confirmed-label agreement/disagreement, preserves ties rather than selecting an arbitrary winner, and places exact four-state percentages plus fit/basis caveats in escaped bilingual `data-tip-*` tooltip content. It is written after both synthesis and translation, before persistence, so no model-owned key can replace it.
- Freshness SLA loading now calls the canonical `engine.neuralweb.synapse.load_registry()` owner. Registry/clock/SLA uncertainty stays unavailable rather than becoming fresh.
- The shared renderer ignores a missing or non-mapping optional `regime_evidence`, preserving older briefs and other lenses.

RED evidence:

```text
8 failed, 73 passed in 5.57s
```

The failure set reproduced all six R1 findings, with separate tests for visible state/agreement behavior and tied maxima. An additional focused RED confirmed that pre-translation placement let translated/model content overwrite deterministic evidence.

GREEN evidence:

```text
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  pytest --basetemp=/private/tmp/regime-hmm-w1-consumer-repair-20260909-sol-001 \
  tests/test_master_brain.py tests/test_regime_label_honesty.py -q

83 passed in 3.10s
```

Also verified:

```text
git diff --check
# clean

scripts/check_design_system.py --mode enforce-added …
# 0 blocking findings; 19,015 pre-existing non-blocking estate findings
```

Caveat: the required task-specific external basetemp under `/Volumes/Mastermind/agent-evidence/regime-hmm-w1-consumer-repair-20260909-sol-001` did not exist, and managed sandbox permissions rejected its creation with `Operation not permitted`. The RED/GREEN receipts record this precisely; the test run used the only available isolated task-specific fallback under `/private/tmp`, so it is not external-SSD evidence.