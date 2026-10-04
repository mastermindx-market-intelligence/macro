---
key: AGENT-EVAL-FABRIC
title: Mastermind Agent Evaluation & Organizational Learning Fabric (Fable COO program)
objective: Produce provenance-bound evaluation and bounded organizational learning through the existing Agent OS, OHF, and
  Executive owners. No ranking, routing, trading, promotion, or execution authority follows from evaluation evidence. Completion
  requires real paired evidence, one lawful OL-V1 episode, and owner-accepted forward value.
status: active
program: project-active-build-control
repos:
- macro
- mastermind
owner: coo-fable
class: adjudication
blast_radius: reversible
ambiguity: scoped
p0: null
waves:
- id: A1
  title: 'EVAL-F0 architecture — Mastermind #299'
  status: done
  next_action: Protected; do not reopen.
- id: A2
  title: 'OL-0 architecture — Macro #6760'
  status: done
  pr: 6760
  next_action: '#6760 is protected; #6699/#6711 are superseded; D1 owns OL-V1.'
- id: B1
  title: 'EVAL-R0 evidence core — Mastermind #330'
  status: done
  depends_on:
  - A1
  next_action: Protected; synthetic proof is not live learning.
- id: B2
  title: 'EVAL-C0 corpus — Mastermind #332'
  status: done
  depends_on:
  - B1
  next_action: Protected; placeholder holdouts are not live confirmation cases.
- id: B3
  title: 'OHF1 fresh runner — Mastermind #162'
  status: done
  depends_on:
  - A1
  next_action: Merged as d6eccb0d81c9db3d009eafa7b37ea97a4dc99bc8; do not reopen.
- id: B4
  title: 'OHF2 bridge — Mastermind #336'
  status: done
  depends_on:
  - B1
  - B3
  next_action: Protected source only; it does not execute historical E1.
- id: C1
  title: 'EVAL-S1 scorers — Mastermind #333'
  status: done
  depends_on:
  - B1
  next_action: Protected; provider execution still requires a compatible prospective experiment.
- id: C2
  title: Historical E1 experiment-design adjudication
  status: done
  depends_on:
  - B2
  - B3
  - B4
  - C1
  next_action: 'Chairman ruling recorded by DEC:AGENT-EVAL-C2-CHAIRMAN-RULING. Preserve immutable E1 digest sha256:91cb16860ee9e140d28052e5981b7c8f94aac4ecd42e788d3c7a75e3415e5cf8
    unchanged and unexecuted; historical anthropic/claude-sonnet-5 E1 is retired as an executable experiment because accepted
    #162 requires gpt-5.6-sol. Never substitute provider/model or rewrite the seal.'
- id: C3
  title: 'Provider-free H1/H2 convergence contracts — Mastermind #871'
  status: in_progress
  depends_on:
  - C2
  pr: 871
  next_action: 'Mastermind #871 exact head 33d77c3fa94b9b8127d5a08974da9033091c6137 merged as db4ef921c1e9a1abd790197d2719ba5316fbf99e
    and is protected under Mastermind master 3e66e43258f34db240d5bff76f54148c7af84ee4; all five changed files were read
    back. Treat the contracts as BUILT_NOT_PROVEN and produce one real provider-free H1/H2 episode. C3 must remain in_progress
    until private holdout commitment, FACTOR_LOCKED versus SYSTEM_REALISTIC environment evidence, bound configuration, owner-proven
    grader/execution provenance, scorer-input evidence, fresh runs, and accepted paired evidence exist. The merge grants
    no provider, ranking, routing, promotion, or execution authority.'
- id: D1
  title: 'OL-V1 existing implementation and mechanism proof — Mastermind #398'
  status: in_progress
  depends_on:
  - A2
  next_action: 'Keep Mastermind #398 at d79d2ec3537d8eb060055731a7c3cebee0c543eb. Source gates and Macro grounding are green;
    no directive exists. Continue Executive incident #386 credential/readiness/ARM sequence, then admit one untouched READ/A0
    compose-only directive. Agent Eval must not read the credential or start/re-home the global service.'
- id: F1
  title: Experience distillation candidates and read-only evidence experience
  status: todo
  depends_on:
  - C3
- id: G1
  title: Prospective proof, owner-accepted improvement and program closeout
  status: todo
  depends_on:
  - C3
  - D1
  - F1
next_action: 'Use the protected #871 contracts at merge db4ef921c1e9a1abd790197d2719ba5316fbf99e / Mastermind 3e66e43258f34db240d5bff76f54148c7af84ee4
  to produce the first real provider-free H1/H2 episode; do not mark C3 done on contract presence alone. In parallel, keep
  #398 frozen and consume Executive incident #386 through readiness/ARM before exactly one READ/A0 compose-only directive.
  Historical E1 remains immutable, unexecuted, and retired.'
decisions:
- DEC:AGENT-EVAL-FABLE-COO-DELEGATION
- DEC:AGENT-EVAL-C2-CHAIRMAN-RULING
artifacts:
- agentos/workstreams/WS-AGENT-EVAL-FABRIC.md
- agentos/decisions/DEC-AGENT-EVAL-FABLE-COO-DELEGATION.md
- agentos/decisions/DEC-AGENT-EVAL-C2-CHAIRMAN-RULING.md
- agentos/handoffs/AGENT-EVAL-FABRIC-2026-09-19.md
- research/AGENT_EVAL_CONTINUITY_PROOF_2026-09-08.md
landmines:
- '#162 and #841 are source/substrate releases, not historical E1 execution or provider authority.'
- 'Historical E1 seals anthropic/claude-sonnet-5 while #162 requires gpt-5.6-sol; never substitute provider/model, rewrite
  the seal, or claim E1 ran.'
- '#871 is merged as db4ef921c1e9a1abd790197d2719ba5316fbf99e, but remains a bounded contracts release. It does not create
  a real holdout, paired run, provider experiment, automatic promotion, or execution authority.'
- OL-V1 d79 approval is source-only; Agent OS prose never authorizes an effect.
- 'D1 waits on Executive incident #386 credential/readiness/ARM; Agent Eval never reads the token or starts/re-homes the
  global service.'
- WS-EVAL-OS-* is separate; never cross-wire its carriers or authority.
do_not_redo:
- '#162 d6eccb0d81c9db3d009eafa7b37ea97a4dc99bc8, #692 9e796168b467c17d9853f139c4e4a6ccdf3a3a87, #841 96c9ab97aa64bce65fe0da140c9d6c5bbf2c778e,
  #760 d57d793b588fc7819559bdc2b408977dd01691e6, and Macro #7344 2834f2531f145ede66d5639b4a149633147beac7 are merged/do-not-redo;
  preserve #398 on its existing carrier.'
- '#6699/#6711 are superseded; R0/C0/S1/OHF2/E1 preregistration foundations are protected.'
- 'Mastermind #871 exact head 33d77c3fa94b9b8127d5a08974da9033091c6137 is merged as db4ef921c1e9a1abd790197d2719ba5316fbf99e;
  do not create a replacement C3 PR, rewrite the protected contracts, or broaden the R0 prefix fence.'
- 'EFFECT_UNKNOWN stays on its original operation: no replay, account switch, failover, or inferred release.'
- No universal leaderboard, automatic promotion, or second lifecycle, memory, queue, router, evaluator, or control plane.
- Never mutate historical E1 or revive terminal children; any future provider experiment requires a new prospective preregistration
  and fresh authority.
---
# Agent Evaluation & Organizational Learning Fabric

The existing `coo-fable` program remains the durable owner. C2 is a completed experiment-design ruling, not a completed experiment: historical E1 remains immutable and unexecuted. Mastermind #871 exact head `33d77c3fa94b9b8127d5a08974da9033091c6137` merged as `db4ef921c1e9a1abd790197d2719ba5316fbf99e` and is protected under master `3e66e43258f34db240d5bff76f54148c7af84ee4`; its five contract paths were read back. C3 therefore advances from merge recovery to the first real provider-free H1/H2 episode and remains `in_progress` / `BUILT_NOT_PROVEN` until accepted paired evidence exists. D1 remains on Mastermind #398 at `d79d2ec3537d8eb060055731a7c3cebee0c543eb`; its next gate is Executive incident #386 readiness followed by one untouched READ/A0 directive. No E1, provider, ranking, routing, promotion, OL-V1, or autonomous effect has run.
