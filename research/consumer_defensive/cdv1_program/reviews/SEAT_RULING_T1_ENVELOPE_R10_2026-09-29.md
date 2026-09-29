# Seat ruling — T1 envelope, audit round 10 (R195–R197)

Adjudicator: the CDV-1 Meta-CEO seat (session 251f88c8, running Opus 5.5 under the fable-mode doctrine).

Source: the independent Opus acceptance audit of the exact head `6caa2ffc1a95` (PR #7905), which R194 required. The audit was READ_ONLY and ran as two independent groups. Group A returned **ACCEPT** and group B **REJECT**. The report is committed beside this record as `OPUS_T1_ENVELOPE_AUDIT_R10_2026-09-29.md`, with each group's report verbatim.
- The findings:
  - two blockers, both group B's: B-R10-B1 and B-R10-B2;
  - the non-blocking notes n-A1 and n-A2 (group A) and n-B1, n-B2 and n-B3 (group B).
- Both blockers are inherited. Group B re-ran its probes on the round-9 head `11bd3dea8879`, and they fail there the same way.
- Both sit inside R193's class, which R193 claimed to close: a value the validator's entry admits raises where the validator reads it, instead of being refused.
  - B-R10-B1: R193 admits a `Fraction` by its exact type, but a `Fraction`'s two parts are writable slots, and the walk never checked what they hold.
  - B-R10-B2: an exact `list` or `dict`, both admitted, is used as a dictionary key one line before the test of its type.
- While testing its first draft of the repair, the seat found a third construction in the same class: an argument, or a value inside the workspace, whose class or metaclass carries code, which R193's own tests of type ran.
- This is the second time the class has survived a ruling meant to close it (R189, then R193). The operating brief of 2026-09-29 requires a bounded design correction when a class survives, not another literal special case. Sol's direction on the carrier (comment 5894879516) asks for the exact blocking constructions and the smallest ruled repair. So the class is corrected in its two halves, not at the sites the audit named:
  - **R195** completes the closed set. A number is admitted only in the form Python builds, and the walk and the entry decide every type by identity, so no argument runs code of its own.
  - **R196** makes the public entry's contract total. After R193 and R195 every value the body reads is a built-in, so an exception a built-in operation raises about a value's type or range, wherever the body reads it, leaves the entry as the refusal it stands for.
- **R197** disposes of the notes, freezes the round-10 witness and sets round 11.

## Severity

The bars are the commission's review standard: (a) wrong bind, (b) present fact outside F1-Q, (c) validator acceptance of a tampered workspace, (d) integrity, (e) positional or literal admission, and (f) loose literal parse.

| finding | audit | seat | ruling |
|---|---|---|---|
| B-R10-B1, a `Fraction` of exact type whose part is not an exact `int` raises `TypeError` in the walk itself; with a zero denominator it passes the walk and raises `ZeroDivisionError` in `_finite`; with an `int` subclass part that has a hostile `__str__`, it passes the walk and raises where the fiscal period is printed | BLOCKER (d) | BLOCKER (d); R193's class | R195 |
| B-R10-B2, an exact `list` or `dict` as a present row's `source_span.document_id`, on the non-envelope route, raises `TypeError` (unhashable) at `source_texts.get(document_id)`, before the test of its type | BLOCKER (d) | BLOCKER (d); R193's class | R196 |
| the seat's: at `6caa2ffc1a95`, eight of its sixteen constructions whose class or metaclass carries code raise that code's exception out of the validator: a value whose metaclass defines `__hash__` or `__eq__`, nested in the workspace; the workspace as a value whose metaclass defines `__hash__` or `__class__`; `source_texts` as one whose metaclass defines `__hash__`, `__eq__` or `__class__`; and `fiscal_scope` as a value with a `__class__` property | — | BLOCKER (d); R193's class | R195 |
| n-A1, n-A2; n-B1, n-B2, n-B3 | notes | disposed of below | R197 |

- **All three are integrity (d).** An exception escaping the validator is not a refusal. That is R176's rule, R183's, R189's and R193's.
- None of them binds a wrong value. Each needs a tampered workspace or a tampered argument. Group B's walk accepted no tamper of a fact row: on the non-envelope route 0 of 45,074 runs were accepted, and on the envelope route no `facts[*]` path accepted a tamper that changes the workspace's JSON.

## Rulings

- **R195 (B-R10-B1 and the seat's construction; amends R193). The closed set admits a number only in the form Python builds, and the walk and the entry decide every type by identity.**
  - **The class.** R193 closed the set of types. But an exact type promises a value's behaviour only while the value holds what the type's constructor put there.
    - A `Fraction`'s `_numerator` and `_denominator` are ordinary slots that can be assigned anything after construction. The walk read them with `abs()` and `>=` without checking them (B-R10-B1 (i)). What passed the walk was then divided by `float()` (ii) and printed by `str()` (iii).
    - R193's own tests of type asked the value's class questions. The walk tested its leaves by membership in `frozenset({float, bool, type(None)})`. That hashes the value's class and, on a collision, compares it. The entry tested `workspace` and `source_texts` with `isinstance(..., Mapping)` against `typing.Mapping`, which asks the argument's class for its `__class__` and hashes it. `_fiscal_scope` tested `isinstance(value, tuple)`, which asks the argument for its `__class__`.
    - A metaclass can define `__hash__`, `__eq__` and `__class__`, and an instance can define a `__class__` property. So each of those tests ran code that the argument supplied.
    - The seat's first draft of R195 still used the set lookup. The seat's probe of it raised the metaclass's own exception from three constructions, and the draft was corrected before this ruling.
  - **The repair.**
    - An `int` or a `Fraction` passes the walk only in the form `int` and `Fraction()` construct:
      - its numerator and denominator are exact `int`s;
      - the denominator is positive;
      - the value is in lowest terms;
      - both parts are within R189's bound.
      Any other `int` or `Fraction` is refused under the walk's message, "workspace holds a value it cannot print".
    - Every test of type in the walk and at the entry is `type(value) is T`. That is an identity comparison, and it asks the value nothing. The walk's leaf set is written as three identity tests, and the set lookup is gone.
    - The entry reads `workspace` as a `dict` or a refusal:
      - a value the walk admits that is not a `dict` (a list, text, `None`) is refused as "workspace must be a mapping", as before;
      - any other value is refused by the walk, as R193 already refuses a `dict` subclass.
    - `source_texts` is read only by R193's exact-type test. Every value that is not a `dict` of `str` to `str` is refused as "source_texts must map document ids to text". R193 kept a separate `isinstance(source_texts, Mapping)` test before it. That test and its message, "source_texts must be a mapping", are retired, and no frozen test pins them.
    - `fiscal_scope` must be an exact `tuple` of four exact `str`s. A named tuple, a list or a `str` subclass is refused as "fiscal_scope must contain four ISO dates".
  - **What it refuses that R193 did not.**
    - An `int` or `Fraction` not in the form Python builds.
    - A `tuple` subclass as `fiscal_scope`, or a `str` subclass among its dates.
    - None of the product's values. The six originals' workspaces hold only JSON's seven types (R193's census). Their `source_texts` are a `dict` of `str` to `str`. Every caller passes `fiscal_scope` as a tuple of four ISO strings. The real-release demonstration's output is unchanged.
  - **What changes its message.** A value that the walk does not admit, passed as the workspace, is now refused under the walk's message rather than "workspace must be a mapping", and a non-`dict` `source_texts` under "source_texts must map document ids to text". Both were refusals before, and remain refusals.
  - **The boundary.** The entry now runs no code that its arguments supply. It does not defend against code elsewhere in the process, such as a class defined before the call that alters a standard class. Code that can define classes can also replace this module.
  - **Rejected.**
    - Checking a `Fraction`'s parts at each site that reads them. That is three site patches, and the fourth read would be the next finding.
    - Removing `Fraction` from the set. R134 and R183 read it as a real number, and R183's frozen case requires a present row's too-large `Fraction` to meet the value check's own refusal.
    - Hardening each `isinstance` against a hostile class, for example by catching its exception. The test would still run the argument's code.

- **R196 (B-R10-B2). The public entry returns the facts it accepts or raises `EconomicObservationError`, and nothing else.**
  - **The class.** B-R10-B2 is a read of an admitted value where it has the wrong type: a present row's `source_span.document_id` used as a key, one line before the test that it is text.
    - After R193 and R195 every value the body reads is one of nine built-in types and holds what that type promises. What remains of the class is exactly this: a built-in operation applied to a built-in value of the wrong type or range.
    - The body reads the workspace in hundreds of places. Testing each value before each read is the literal special-case loop the brief forbids: each round would find the next read.
  - **The repair.** `validate_selected_facts` becomes a wrapper around the body, which is renamed `_validate_selected_facts`.
    - An `EconomicObservationError` leaves it unchanged.
    - Five kinds of exception leave it as `EconomicObservationError("a value has the wrong type or range where the validator reads it (<name>)")`, chained to the original: `TypeError`, `ValueError` (with its `UnicodeError` subclasses), `ArithmeticError` (`ZeroDivisionError`, `OverflowError`), `LookupError` (`KeyError`, `IndexError`) and `AttributeError`.
    - Every other exception propagates unchanged, among them `RuntimeError`, `RecursionError`, `NameError`, `StopIteration`, `MemoryError` and `KeyboardInterrupt`.
  - **Why this is not the catch R193 rejected.** R193 rejected catching exceptions at `str()`, `_fact_id` and the comparisons. Those were patches at sites while the entry still admitted types whose behaviour it could not bound, so each exception was the symptom of a value the entry should have refused.
    - After R193 and R195 the entry admits nothing whose behaviour is not the built-in's.
    - So one of the five exceptions can only mean that a built-in value was read where its type or range does not fit, and the refusal is the verdict the contract owes that input.
    - The conversion is in one place, the public boundary, for that one reason.
  - **What it does not do.** It accepts nothing: every converted exception is a refusal, and the body's return value is unchanged. No frozen test changes, and the frozen suites' refusal messages all still hold.
  - **Its cost, stated.** A programming error in the body that raises one of the five would read as a refusal of the workspace. That fails closed, and the untampered controls, which must validate, catch it. A `NameError` or a `RuntimeError` still propagates.
  - **Rejected.**
    - A `str` test before `source_texts.get`. That is the site patch, and the next unguarded read would be the next finding.
    - Catching `Exception`. That would turn a `RecursionError` or a bug's `NameError` into a verdict on the workspace.

- **R197 (the notes, the freeze and round 11).**
  - **n-A1**, a relocation onto a whole token that follows other printed text in the same element is refused by the gap rule. That is a fail-closed coverage limit under R155, recorded.
  - **n-A2**, `_print_matches` refuses a misaligned fragment. No public-path caller can produce one (R192). Recorded.
  - **n-B1**, `fiscal_period.quarter` and `year` compare by `str()`, so `3`, `"3"` and `Fraction(3)` all pass. The comparison predates this round, and the fields are not bound into any fact. The seat returns it to Sol as a residual; it is not ruled here.
  - **n-B2**, extra keys in `fiscal_period` and in the release source entry are accepted, and the validator does not read them.
    - The seat's sweep finds the same for the entry's `filing_key`, `source_sha256`, `form` and `url`. Each fact's receipt is bound to the source bytes, but the entry's own metadata is not read. None of it changes a bound fact.
    - The seat returns it to Sol with n-B1 as a contract question; it is not ruled here.
  - **n-B3**, an instance `__class__` property at the root of the workspace or `source_texts` is refused, not raised. Group B's probe is right, and the seat's probes extend it. A metaclass `__class__`, `__hash__` or `__eq__` on those two arguments, and an instance `__class__` on `fiscal_scope`, raised at `6caa2ffc1a95`. R195 closes them.
  - **Freeze.** `tests/test_pg_envelope_f1_probes_r10.py` holds 224 cases:
    - group B's 57 findings and 15 controls. The seat sharpened the controls to the refusal each one meets, without changing their constructions, and folded B's untampered control into the seat's, which also validates each workspace after `json.dumps` and `json.loads`;
    - the seat's 114 R195 cases:
      - the other parts a `Fraction` can be given (`bool`, `float`, a NaN, an `int` subclass);
      - the forms Python never builds (a negative denominator, a value not in lowest terms);
      - values and arguments whose class or metaclass carries code;
      - `fiscal_scope`'s forms and `source_texts` that are not a `dict`;
    - R196's 14 contract cases. They raise eight exceptions of the five converted kinds, four that propagate, and a refusal, inside the body, through the `pg_profile` helper it calls once the entry's checks pass. One more checks that a malformed call is not converted;
    - the seat's 24 further controls: `Fraction`s Python builds pass the entry and meet the row's own refusal, and a workspace of an admitted type other than `dict` keeps its message.
    - It joins the `earnings-economic-dossier` gate.
  - **Round 11.** One independent READ_ONLY acceptance audit of the exact head that carries R195–R197, judged on release-blocking findings only:
    - R195's class: every value the entry takes, at every path, including values whose class or metaclass carries code;
    - R196's contract: no exception but `EconomicObservationError` leaves `validate_selected_facts` from a tampered input, and nothing the body refuses is accepted;
    - the frozen suites' and fixtures' drift, the gate and the real-release demonstration on that head;
    - hosted CI concluded on that same head.
    - Nits, observations and fail-closed coverage limits are recorded, not ruled. A blocker in R195's or R196's class goes back to Sol with this record, not into a third literal repair.
  - **Hold.** #7905 stays Draft under Sol's HOLD (comment 5894879516; R114). This record asks for no Ready, merge or deployment.
    - After an independent ACCEPT and concluded hosted CI on the same head, the seat returns the candidate to Sol for the hold decision.

## Evidence

Each line names the command or script that produced it. The scratch scripts are the seat's and are not part of the product. "Both interpreters" means Python 3.12.13 with only pytest and pyyaml, as CI runs it, and 3.14.7.

- The group probe files: the auditors' files, run unchanged from a scratch copy of the tree, `python -m pytest -q -p no:cacheprovider <file>`, on both interpreters.
  - Group B's file, 72 cases: at `6caa2ffc1a95`, 57 failed and 15 passed. With R195 alone, 12 failed; with R196 alone, 6 failed; with both, 72 passed.
  - Group A's file, 305 cases: 305 passed at `6caa2ffc1a95`, with each ruling alone, and with both.
- The R10 witness, `python -m pytest -q -p no:cacheprovider tests/test_pg_envelope_f1_probes_r10.py`, on both interpreters, with each ruling reverted alone in a scratch tree. The failing cases are the same, case for case, on the two interpreters.
  - At `6caa2ffc1a95`, 155 failed and 69 passed.
  - With R195 alone, 20 failed: every R196 case that fails at `6caa2ffc1a95` (the 12 `document_id` cases and the 8 conversions), and no R195 case.
  - With R196 alone, 135 failed: every R195 case that fails at `6caa2ffc1a95`, and no R196 case.
  - With both, 224 passed.
  - The two failing sets are disjoint, and together they are exactly the 155.
  - The 69 that pass at `6caa2ffc1a95` are of three kinds:
    - the 39 controls;
    - the six R196 cases whose outcome the wrapper must leave alone: the four propagations, the refusal raised inside, and the malformed call;
    - 24 R195 cases the head already refused with the message R195 keeps: a nested value whose class or metaclass defines `__class__`; `fiscal_scope` as a value whose metaclass defines `__hash__`, `__eq__` or `__class__`, as a list, or as three dates; and `source_texts` as a `mappingproxy`.
  - Each case runs on Q1, Q2 and Q3.
- The sixteen constructions whose class or metaclass carries code, `outcomes.py` on Q3, on both interpreters, with identical output on the two:
  - at `6caa2ffc1a95`, eight raised the construction's own exception, as the severity table lists. The other eight were refused: two under the walk's message, three under "fiscal_scope must contain four ISO dates", two under "workspace must be a mapping" and one under "source_texts must be a mapping";
  - with R195 and R196, all sixteen are refused and none raises: the workspace and nested values under the walk's message, `source_texts` under "source_texts must map document ids to text", and `fiscal_scope` under "fiscal_scope must contain four ISO dates".
- The seat's sweep, `seat_walk.py`, group B's walker with the seat's additions. It sets each of 73 values at every path of the event id, the fiscal period, the release source entry and the `pg_` fact rows, and adds and renames keys in each mapping. Q1, Q2 and Q3, on both routes and both interpreters, with R195 and R196:
  - the non-envelope route: 50,482 runs for each quarter on each interpreter, and every one refused;
  - the envelope route: 50,482 runs for each quarter on each interpreter, and none raised. 50,183 on Q1 and 50,185 on Q2 and Q3 were refused. Of the rest, 83, 81 and 80 left the workspace's JSON unchanged, and 216, 216 and 217 changed it.
    - Every change that was accepted is outside the facts. It is one of three kinds: an added key in the fiscal period or the release source entry (n-B2); the entry's `filing_key`, `source_sha256`, `form` or `url`, which the validator does not read (each fact's receipt carries its own `source_sha256`, and that one is checked against the bytes); and, on Q3, a quarter that compares equal by `str()` (n-B1).
    - No tamper of a `pg_` fact row was accepted.
  - The counts are identical on the two interpreters.
- The census of the product's workspace types holds as R193 recorded it. This round changes no code that builds a workspace: `git diff --stat 6caa2ffc1a95 -- engine/ app/ scripts/` names only `engine/company_intelligence/economic_observations.py`.
- No caller of `validate_selected_facts` outside `tests/` and the demonstration: `git grep -n validate_selected_facts -- ':!tests'` names the definition, the demonstration's script and records.
- The runs below are on the worktree of #7905 with this round's files in place and nothing else changed, before the three commits were cut. The commits reproduce that tree byte for byte, except this record, whose evidence lines were written from these runs.
  - The gate, the `earnings-economic-dossier` job's 27 test files with the R10 witness: 2315 passed and 174 skipped on each interpreter; none failed.
  - `tests/test_ci_pack.py -k curated_exclusive`: 2 passed on each interpreter.
  - The six release-parser neighbours, under `/opt/homebrew/bin/python3.12` with pandas and jsonschema: 287 passed and 2 failed. These are the same 289 outcomes, test for test, as round 9's run on the tree of `6caa2ffc1a95`, and as at `11bd3dea8879`. The two are `test_clean_preimport_forged_html_helper_imports_but_parser_fails_closed` and `test_clean_preimport_forged_stdlib_method_imports_but_parser_fails_closed` for the host's python.org 3.12.2 interpreter.
  - The real-release demonstration, the script in `release/T1_REAL_RELEASE_DEMONSTRATION_2026-09-29.md`, on each interpreter:
    - 6 of 6 sources match their `SOURCES.md` pins;
    - Q1, Q2 and Q3 each bind 20 of 20 facts, and the validator accepts each workspace;
    - the four refused documents bind none, and the validator accepts their typed absences;
    - 9 of 9 tampered workspaces are refused;
    - 0 failures.
    - The two interpreters' JSON outputs differ only in the line that names the interpreter. Each is identical to round 9's on the same interpreter once the tree's path is normalised.
  - The worktree's `git status` is the same before and after the runs.
  - Frozen drift: `git diff --name-status 6caa2ffc1a95 -- tests/` is empty: no suite or fixture under `tests/` changed. The R10 witness is the one new file there.
