---
key: A-DECLARED-BASIS-IS-A-LABEL-UNTIL-SOMETHING-READS-IT
claim: >
  A parameter a function RECEIVES and never READS turns the thing it names into a label
  applied after the fact, and the resulting document asserts a relationship its own data
  refutes at `availability: ready` with zero schema errors. Measured on merged Consumer
  Cyclical V1-CORE (`edf7f0add1b1`): `_select_pair` takes `comparison_basis` and never
  reads it (AST-verified — the name appears in the signature and nowhere in the body). It
  pairs on five equalities plus `older.period_end < newest.period_end`, and the basis is
  then stamped on by result key. So with the case declaring
  `explicit_same_quarter_prior_year`, a prior side moved to Q1 2019 (seven years off), a
  prior period whose end precedes its own start, and a 30-day "quarter" each published a
  full set of `same_quarter_prior_year_change` values — declared ready, `degraded_dependencies: []`,
  contract-valid. The refusal reason for this exact case already existed and was already
  named `no_compatible_pair_for_comparison_basis`; nothing could ever reach it. Separately
  and in the same family, three of the four result definitions end "in USD thousands" —
  a CLAIM about the envelope, not decoration — while the envelope was whatever the source
  carried, so a pair in EUR at 10**6 published `unit: EUR, scale_power10: 6` beside that
  sentence, schema-valid and self-contradicting.
falsifier: >
  On `origin/main` before this wave's successor, run
  `python3 -c "import ast,inspect; from engine.sector_intelligence import
  consumer_cyclical_projection as m; src=inspect.getsource(m._select_pair);
  print('comparison_basis' in ast.dump(ast.parse(src).body[0].body))"` — if it prints
  True, the parameter is read and the claim is refuted. Behaviourally: take `_plnt_case()`,
  move every `*_prior` fact to `period_start 2019-01-01 / period_end 2019-03-31`, project,
  and read `[r for r in document["results"] if not r.get("withheld_reason") and
  r["basis"] == "same_quarter_prior_year_change"]`. A non-empty list on the unfixed module
  confirms it; an empty one refutes it.
so_what: >
  Treat a declared basis, label, or mode as UNENFORCED until you can name the line that
  reads it — receiving it as an argument is not reading it, and neither is stamping it on
  the output. When a module both declares a relationship and derives one, add the check
  that the derived thing can actually BE the declared thing, and express it as generous
  BANDS, never equalities: Consumer Cyclical is retail, so a 4-5-4 quarter is 13 or 14
  weeks and a fiscal year is 52 or 53 of them — a calendar-exact rule is wrong here for
  the same reason `_envelope_period_start` refuses to snap a start out of an end. The same
  rule covers prose: a definition sentence that names a unit, scale or precision is a claim
  the envelope must satisfy, and the honest move when it cannot is to withhold with a named
  reason rather than to derive new display vocabulary the module does not own. Every sector
  vertical copying this projector inherits the unread parameter.
kind: landmine
verified_at: 2026-09-27
verified_by: >
  `origin/main` at `edf7f0add1b1`, re-extracted with `git archive` and sha256-confirmed.
  Three refusal arms and the definition-contradiction arm each reproduced before repair
  and pinned after. Mutation round, 13 mutants each guarded by a `MUTATION WAS A NO-OP`
  assert: 12 killed, 1 equivalent. Both live cases unchanged after repair — 0 schema
  errors, `availability: ready`, `degraded_dependencies: []`, oracle exact
  (`total_revenue_change 24344`, `advertising_share_of_revenue_change_pct 41.66`) — so the
  bands admit the real quarters they must. Owned suite 102 -> 111 passed.
scope:
  - macro
  - engine/sector_intelligence/
  - contracts/sector_intelligence/
  - research/consumer_cyclical/v1/
confidence: verified
---

The module was not missing a check; it was missing a READER. `comparison_basis` travelled
all the way into `_select_pair`'s signature, which is exactly why the defect survives
review — the parameter list reads like the check is there.

Two warnings for whoever extends this.

**The mutation round is not optional here.** The test written for the period-kind binding
PASSED while a mutant that deleted the binding entirely also passed — twice, for two
different reasons (`_select_pair` already required both sides to agree on `period_kind`,
so relabelling one side collapsed the pair for a pre-existing reason; and the corrected
test filtered on `comparison_basis`, which `_emit_result` strips as an internal carrier —
the contract field is `basis`). Neither error was visible from a green run.

**Refuse, do not derive.** When the envelope contradicts the stated definition the answer
is `withheld_reason: result_envelope_contradicts_stated_definition`, not a converted value
and not a rewritten sentence: V1's frozen scope is a PLNT USD-thousands projector, and
minting a new quantum word or new prose would be inventing display vocabulary this module
does not own. That is the same boundary [[a-minting-default-is-invisible-to-an-emptiness-gate]]
draws — refuse a default that ASSERTS, leave one that is the contract's own "unknown".

Found alongside [[an-enumerated-guard-is-blind-outside-its-enumeration]]; that record
carries the guard-shape half of the same wave.
