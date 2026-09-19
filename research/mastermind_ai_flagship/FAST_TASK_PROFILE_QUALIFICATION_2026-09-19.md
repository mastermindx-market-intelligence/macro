# Mastermind AI — Fast task-profile qualification

Date: 2026-09-19.
Operation: `mastermind-ai-fast-task-profiles-20260919-sol-001`.
Parent: Macro #7151 / `macro-mastermind-ai`.
Procedure pin: protected Mastermind `ac6180d0ca9107daae54f9eea6bd4b8aef92d630`,
Skillpack 1.0.1 / bootstrap1.
State: **BUILT_NOT_PROVEN / QUALIFICATION_ONLY**.

## Problem

The current Macro Fast Brain exposes all currently authorized tool schemas to the
model on every turn. At this source vintage that is 54 tools / 34,481 compact JSON
characters before the model has chosen evidence. Production measurements in the
parent programme show tool execution itself is fast; model selection/reasoning rounds
dominate latency.

The existing `ask_brain._classify_question` already classifies many questions for
tool-call budgets and seed guidance. It does **not** control model visibility, and this
wave does not change that.

## Capability built

`engine/neuralweb/ask_brain.py` now has an additive
`brain.task_profile.v1` qualification projection beside the unchanged legacy
classifier.

Qualified conservative profiles:

| Profile | Candidate tools | Grounding scope |
| --- | ---: | --- |
| self_contained | 0 | none |
| single_name_current | 10 | single_name_current |
| macro_rates | 7 | market_current |
| options_single_name | 7 | single_name_current |
| portfolio | 7 | portfolio_current |
| theme | 9 | market_current |
| ambiguous | full authorized surface | ambiguous |

This is candidate **model visibility only**. It grants no dispatcher authorization,
entitlement, provider, source, grounding, signal, ranking, sizing, trading or release
authority.

A future gateway consumer must first build the full currently authorized/page/tier-
gated schema exactly as today, then intersect model visibility with the candidate
tool names. A profile can therefore narrow what the model sees but cannot resurrect a
tool the existing schema builder withheld.

## Fail-open safety

Unknown or cross-domain questions return `ambiguous / full_authorized`.

The qualification deliberately refuses to narrow specialist single-name questions
whose required tool is outside the first profile families, including institutional
research/street views, insiders/Congress/smart-money, historical analogues, backtests,
stage peers/analysis, charts/drawing, factor intelligence and special situations.

Portfolio+options and single-name+macro mixtures likewise remain full visibility until
an explicit multi-family profile is qualified.

This is why the slice fixes the known legacy ordering problem ("options setup" with a
context ticker) without changing `_classify_question` itself: the new projection can
select options tools while every existing caller still receives the historical
budget/seed tuple unchanged.

## Real machine consumer

`scripts/probe_brain_task_profiles.py --strict` is a no-network/no-model qualification
consumer. It reads the existing full gateway schema and measures the exact schema that
each candidate family would expose.

Current measured result:

| Profile | Tools | Schema chars | Reduction vs 54-tool baseline |
| --- | ---: | ---: | ---: |
| self_contained | 0 | 2 | 100.0% |
| single_name_current | 10 | 6,115 | 82.3% |
| macro_rates | 7 | 4,534 | 86.9% |
| options_single_name | 7 | 3,503 | 89.8% |
| portfolio | 7 | 3,738 | 89.2% |
| theme | 9 | 5,455 | 84.2% |
| ambiguous | 54 | 34,481 | 0.0% |

Strict qualification fails if a named profile tool is absent from the current
authorized schema, any filtered profile saves less than 70%, or ambiguous is not
byte-equivalent to the full schema.

The direct CLI pins the repository root before importing `engine`, which was caught
by an actual direct-execution failure during TDD.

## TDD and compatibility

Initial focused RED: 15 failures because the task-profile/probe capability was absent.

First GREEN exposed two test-harness name errors only; after harness repair the direct
CLI then exposed its real import-root defect and that was repaired.

Adversarial RED then reproduced nine meaningful false-narrowing defects:
- eight specialist single-name shapes would have hidden their specialist tools;
- liquidity-plumbing was not admitted to the macro family.

Those defects were repaired by failing specialist shapes open to ambiguous/full
visibility and by composing the existing inflation/liquidity owners into macro/rates.
The macro family includes `read_inflation_intelligence` rather than hiding the
dedicated release-intelligence tool.

Final evidence:
- focused profile/probe cases: 15 pass before hostile expansion;
- hostile false-narrowing cases: 11 pass after repair;
- full `tests/test_ask_brain.py + tests/test_brain_seed_router.py`: **215 passed**;
- `py_compile`: pass;
- `git diff --check`: pass;
- direct `probe_brain_task_profiles.py --strict`: exit 0 and
  `strict_passed=true`.

No model, provider, network, customer request, entitlement or production state was
used by the probe.

## What this does not prove

- Gateway model visibility is unchanged in this wave.
- Fast latency is unchanged in this wave.
- The candidate profiles have not yet been served to real customers.
- Profile selection precision/recall outside the frozen/adversarial cases is not
  production-calibrated.
- The incumbent financial calculator #7217 is not yet in protected main, so
  self-contained supplied scenarios intentionally expose zero tools in this current
  qualification rather than naming an unavailable calculator.
- Tool prefetch is not implemented and remains a later experiment only if visibility
  reduction is insufficient.
- Current cumulative multi-round usage accounting remains a separate defect.

## Exact continuation

Keep this slice separate from shared-gateway source custody.

After the incumbent calculator/scope/gateway carriers are accepted and current source
ownership is clean:

1. the existing gateway builds the full authorized schema first;
2. Fast/chat/non-Terminal turns consume this task profile;
3. ambiguous remains byte-identical full visibility;
4. unknown-tool recovery may reveal only tools offered for that turn;
5. self-contained tasks suppress unrelated ambient market grounding;
6. run the frozen Fast bakeoff and #7441 natural-vs-coached reasoning evaluator;
7. claim a latency/quality win only from real served-model receipts.

Do not create another router, planner model call, tool registry, provider owner, memory
store or authorization plane.
