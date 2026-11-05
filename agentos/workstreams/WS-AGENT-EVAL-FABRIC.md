---
key: AGENT-EVAL-FABRIC
title: Mastermind Agent Evaluation & Organizational Learning Fabric (Fable COO program)
objective: Produce provenance-bound evaluation and bounded organizational learning through the existing Agent OS,
  OHF, and Executive owners. No ranking, routing, trading, promotion, or execution authority follows from evaluation
  evidence. Completion requires real paired evidence, one lawful OL-V1 episode, and owner-accepted forward value.
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
  next_action: Protected; placeholder holdouts are not E1 cases.
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
  next_action: Protected source only; it does not execute E1.
- id: C1
  title: 'EVAL-S1 scorers — Mastermind #333'
  status: done
  depends_on:
  - B1
  next_action: Protected; execution must still match E1's sealed configuration.
- id: C2
  title: EVAL-E1 real paired experiment (preregistration protected; execution unproven)
  status: todo
  depends_on:
  - B2
  - B3
  - B4
  - C1
  next_action: 'EXECUTION HELD. Preserve E1 digest sha256:91cb16860ee9e140d28052e5981b7c8f94aac4ecd42e788d3c7a75e3415e5cf8;
    await the incumbent Fable ruling on sealed anthropic/claude-sonnet-5 versus the #162 gpt-5.6-sol runner.'
- id: D1
  title: 'OL-V1 existing implementation and mechanism proof — Mastermind #398'
  status: in_progress
  depends_on:
  - A2
  next_action: 'Keep Mastermind #398 at d79d2ec3537d8eb060055731a7c3cebee0c543eb. Source gates and Macro grounding
    are green; no directive exists. Continue Executive incident #386''s credential/readiness/ARM sequence, then
    admit one untouched READ/A0 compose-only directive. Agent Eval must not read the credential or start the global
    service.'
- id: F1
  title: Experience distillation candidates and read-only evidence experience
  status: todo
  depends_on:
  - C2
- id: G1
  title: Prospective proof, owner-accepted improvement and program closeout
  status: todo
  depends_on:
  - C2
  - D1
  - F1
next_action: 'Await the incumbent Fable C2 ruling without adopting draft #687/#692 or changing historical E1. For
  D1 keep #398 frozen, consume Executive incident #386 through readiness/ARM, refresh Macro grounding, then submit/reconcile
  exactly one READ/A0 compose-only directive.'
decisions:
- DEC:AGENT-EVAL-FABLE-COO-DELEGATION
artifacts:
- agentos/workstreams/WS-AGENT-EVAL-FABRIC.md
- agentos/decisions/DEC-AGENT-EVAL-FABLE-COO-DELEGATION.md
- agentos/handoffs/AGENT-EVAL-FABRIC-2026-09-19.md
- research/AGENT_EVAL_CONTINUITY_PROOF_2026-09-08.md
landmines:
- '#162 and #841 are source/substrate releases, not E1 execution or provider authority.'
- 'E1 seals anthropic/claude-sonnet-5 while #162 requires gpt-5.6-sol; never substitute provider/model.'
- OL-V1 d79 approval is source-only; Agent OS prose never authorizes an effect.
- 'D1 waits on Executive incident #386 credential/readiness/ARM; Agent Eval never reads the token or starts the
  global service.'
- WS-EVAL-OS-* is separate; never cross-wire its carriers or authority.
do_not_redo:
- '#162 d6eccb0d81c9db3d009eafa7b37ea97a4dc99bc8, #841 96c9ab97aa64bce65fe0da140c9d6c5bbf2c778e, #760 d57d793b588fc7819559bdc2b408977dd01691e6,
  and Macro #7344 2834f2531f145ede66d5639b4a149633147beac7 are merged/do-not-redo; preserve #398 on its existing
  carrier.'
- '#6699/#6711 are superseded; R0/C0/S1/OHF2/E1 preregistration foundations are protected.'
- 'EFFECT_UNKNOWN stays on its original operation: no replay, account switch, failover, or inferred release.'
- No universal leaderboard, automatic promotion, or second lifecycle, memory, queue, router, evaluator, or control
  plane.
- Never mutate historical E1 or revive terminal children; successors require prospective authority.
---
# Agent Evaluation & Organizational Learning Fabric

The existing `coo-fable` program remains the owner. C2 is held at the sealed provider/runner mismatch. D1 remains on Mastermind #398 at `d79d2ec3537d8eb060055731a7c3cebee0c543eb`; its next gate is Executive incident #386 readiness followed by one untouched READ/A0 directive. No E1 or OL-V1 effect has run.
