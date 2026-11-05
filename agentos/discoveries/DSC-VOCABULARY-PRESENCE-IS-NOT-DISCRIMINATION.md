---
key: VOCABULARY-PRESENCE-IS-NOT-DISCRIMINATION
claim: >
  Deciding whether a requirement is testable against existing code by grepping for
  the requirement's vocabulary is wrong in BOTH directions, because the requirement
  and the code choose their words independently. Code implements a distinction
  without ever naming it: GMI Industrials' merged result-cash module contains the
  word "optional" ZERO times and implements IND-R215's required-versus-optional
  distinction exactly - `cash_rollforward`'s optional `closing_cash` absent yields
  status `limited` with `rollforward_residual` and the total still computed, while
  any of its five mandatory components absent yields `refused` with `value` and
  `computed_total` both None and a limitation naming the exact operand. And code
  carries a requirement's vocabulary while making no claim the requirement could
  constrain: the same module's `refused`/`limited`/`ready` statuses read as though
  IND-R218 ("withhold mispricing/probability/trade conclusion") were testable,
  while `mispricing`, `probability` and trade-conclusion vocabulary appear ZERO
  times across the whole package - there is no surface that could violate it, so a
  test would be a green guard over nothing. Measured 2026-09-29: of five
  obligations this seat published as "reachable without any held seam" on the basis
  of status vocabulary, TWO survived measurement of their actual pairs.
falsifier: >
  Before claiming a requirement is testable against existing code, construct its
  compliant input and its violating input as a throwaway probe and RUN both against
  the real module - no mocks of the code under test. Put the compliant CONTROL
  first and assert it: if the control does not produce the compliant outcome, every
  row below it is void. If the two inputs produce the same observable outcome, the
  distinction is not made here whatever the vocabulary says, and that is the
  reportable verdict. The probe is not wasted work - it is the same evidence the
  test will encode, so a surviving probe becomes the test body. This record is
  refuted for a given requirement if a vocabulary grep and a measured pair reach
  the same verdict across a program's whole requirement set.
so_what: >
  It changes what a seat PUBLISHES to a commissioning authority about which work is
  next, and an over-count there directs the next increment at an obligation no test
  can honestly enforce - the exact fabrication an anchor-basis guard exists to
  prevent, arriving through the front door as a sincere plan. It also changes what
  a seat parks: the under-count nearly withdrew IND-R215, which was fully
  measurable, because the module never says the word. Concretely, for any program
  whose requirements carry a declared `anchor_basis`
  (DSC:A-VENDORED-TRACEABILITY-MAP-STILL-HAS-NO-REQUIREMENT-TEXT), the probe is the
  admission gate for migrating a row off NO_SOURCE - and it distinguishes the two
  kinds of increment that follow, which must never be reported as one: a row whose
  pair the code already separates yields a GUARD (IND-D23, IND-R215 - merged code
  compliant, 5/5 mutants caught, no defect found), while a row whose pair the code
  collapses yields a FIX (IND-R214 - a real defect in merged code, two methods
  sharing one derived identity). Claiming guard work as defect work inflates a
  program's apparent progress precisely where an authority cannot check it.
kind: landmine
verified_at: 2026-09-29
verified_by: >
  Claude Opus 5 seat c6467452 (GMI Industrials first vertical, operation
  gmi-industrials-fable-ceo-e2e-20260924-chairman-001). Five recovered obligations
  probed against merged
  engine/fundamental_forensics/industrials_result_cash.py - 12 measured cases for
  IND-R215 (5 mandatory components x typed-absent and omitted, plus the optional
  operand omitted and typed-absent) and 11 for IND-D23. Verdicts: IND-D23 and
  IND-R215 reachable (2 passed, and 5/5 mutants caught - refusal substituting zero,
  refusal publishing the partial total, refusal going anonymous, mandatory absence
  downgraded to limited, optional absence escalated to refused); IND-R201 gated on
  another owner's theme graph; IND-R218 and IND-SF04 not discriminable here,
  confirmed by `grep -ric` returning 0 for mispricing/probability and for
  BOM/wafer/stage across engine/fundamental_forensics/. The first probe run was
  itself void - wrong metric names made all 12 rows report `refused`, control
  included, and the uniformity was the only tell.
scope: [macro, agentos, all-programs]
confidence: verified
---

## The two failure directions, measured

| requirement | what the vocabulary said | what the pair said |
|---|---|---|
| `IND-R215` "distinct required refusal versus optional limitation" | `optional` occurs **0** times → looks unreachable | **reachable**; the distinction is structural (required = a metric a formula picks), so no word marks it |
| `IND-R218` "withhold mispricing/probability/trade conclusion" | `refused`/`limited`/`ready` all present → looks reachable | **not discriminable**; `mispricing`/`probability` occur **0** times in the package, so nothing could violate it |

Both errors come from the same mistake: treating a lexical query as an answer about
behaviour. Reachability is a property of the *discrimination* — does a compliant input and a
violating input exist, reachable from here, that the code separates — and that question has
exactly one cheap answer.

## Why a dead control is the failure mode to design against

The first probe of the mandatory/optional pair used metric names the module does not use
(`cash_opening` instead of `opening_cash`). Every one of twelve rows came back `refused`,
which reads as a strong, consistent finding. The only signal that it was void is that the
CONTROL came back `refused` too — which is why the control belongs in the same run and
belongs asserted, not eyeballed. The identical shape had already cost this program once: the
first positive control for IND-R214 died on a `KeyError` before reaching the identity
comparison, proving only that the test errors.

## The increment classes this separates

A measured pair does not only say whether to write a test — it says what the test IS:

- **The code collapses the pair** → the obligation names a real defect. `IND-R214`: the
  comparison receipt's digest omitted `FORMULA_VERSION`, so the same operands under two
  methods produced the byte-identical derived identity
  `synthetic:comparison:548c66766cdec8a4`, and a consumer cache keyed on it would serve a v1
  summary for a v2 request.
- **The code separates the pair** → the obligation yields a regression guard. `IND-D23` and
  `IND-R215`: merged code already complies; the value is stopping a future change from
  collapsing distinctions nothing else pins.

Both are worth shipping. Reporting the second as the first is the dishonesty this record
exists to prevent, and the mutation count is the evidence that separates them: a guard whose
mutants all survive is guarding nothing.

Related: `DSC:A-PATH-LOOKUP-IS-NOT-AN-OBJECT-LOOKUP` is the same family from the same day — a
cheap lexical or positional query answered confidently for a question it cannot reach;
`DSC:A-BLOCKLIST-ENUMERATES-THE-RULES-NOUNS-NOT-THE-VIOLATIONS-VOCABULARY` and
`DSC:FINANCE-WEIGHT-VOCABULARY-GUARD-EVADED-BY-RUNTIME-STRING-COMPOSITION` are the two prior
records of a vocabulary check standing in for a behavioural one.
