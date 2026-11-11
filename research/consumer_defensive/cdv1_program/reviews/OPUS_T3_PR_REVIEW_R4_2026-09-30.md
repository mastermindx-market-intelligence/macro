# Opus review — CDV-1 Task 3, PR #8232, fourth review, 2026-09-30

- **Artifact:** PR #8232, head `47441f3b5cdd85f8bf2a308b5e346a48347f2f1f`, branch `claude/cdv1-t3-economic-interpretation`. The head is the round-5 work through `38e4e71b` plus the two seat commits of round 6, `be277281` and `47441f3b` (`reviews/SEAT_RULING_T3_R6_2026-09-30.md`).
- **Reviewer:** an independent, read-only Opus reviewer commissioned by the CDV-1 seat (session `251f88c8`). Its scope was bounded to properties P1–P4, rulings R6.1–R6.10, findings F1–F7 of the third review, and regressions against rulings that still bind. It was allowed twelve probes of its own and used eight.
- **Verdict:** **ACCEPT.** No blocking finding. Eight notes.
- **Recorded by:** the seat, from the reviewer's return. The seat wrote round 6, so this verdict is the acceptance the seat could not give itself.

## What the reviewer re-ran

On the head, in the CI venv (CPython 3.12.13, macOS), under `ulimit -s hard`:

- the suite: `402 passed in 31.94s`;
- the dossier job's exact `run:` line: `2717 passed, 174 skipped in 484.95s`, rc 0;
- `git rev-parse HEAD` equal to the head and an empty `git status --porcelain`, before and after;
- `git diff --name-only origin/main...HEAD`: the four owned files only. The diff of the frozen Task 1 paths against `cdce3023` is empty. The fixtures file and the CI hunk are unchanged since `38e4e71b`.

## Dispositions

| Item | Reviewer's disposition |
|---|---|
| R6.1 | Met. The walk runs on the selection, the stored payload and the built payload, and nothing is looked up in the workspace or the source texts before Task 1. Removing any one of the three walks fails the sweeps. |
| R6.2 | Met. No `isinstance`, `issubclass` or `__class__`. The reviewer's own count is 55 identity tests. |
| R6.3 | Met. Exactly the five classes are converted and `RuntimeError` propagates. |
| R6.4 | Met. Replay compares the id, then the canonical text. |
| R6.5 | Met. Generation and event identity, lifecycle, handle fields and the empty selection each refuse with the ruled message. |
| R6.6 | Met as the second commit leaves it, attacked in both forms. |
| R6.7 | Met. A typed-absent side reports Task 1's reason and detail in each of the three cases; a valued prior alone reports `not_selected`. |
| R6.8 | Met. The `>` mutant and the subtraction mutant are both killed. |
| R6.9 | Met. With both revisions hostile the unavailable payload is still exact JSON. |
| R6.10 | Met in the code. Its test has a gap (note 1). |
| F1–F4 | Closed. Each reproducer of the third review is clean at the head. |
| F5–F7 | Closed. Each of the third review's three mutations is now killed. |

## The properties, under the reviewer's own probes

- **P1.** 212,549 calls, with about 58 substitutes at every position of every argument. No exception outside the typed pair, and no case in which foreign code ran at all. The substitutes were the reviewer's, not the suite's: types with a hostile metaclass, subclasses of the built-in containers and scalars with raising methods, objects that lie about `__class__`, an object that raises the module's own typed error, cycles, depth 5,000, a 200,001-wide list, 2 MB strings, surrogates, and hostile or hash-twin keys for every key of every mapping.
- **P2.** 36,400 single-position substitutions into stored payloads. The reviewer reports 40 acceptances, all cross-splices from another honest payload, and showed with a second probe that every accepted splice is byte-equal to an honest build on the same inputs. No substituted payload that differs from an honest build was accepted. A JSON round trip validates; a swapped or sorted top-level key order is refused.
- **P3.** Every return in the P1 and P4 probes passed an exact-JSON checker the reviewer wrote.
- **P4.** 4,364 supported builds and 52,368 replays (one workspace, a mapping, a mapping with unrelated entries; tuple and list fiscal scope; as built and after a JSON round trip). No refusal.
- **`_workspaces`.** 33 shapes across 5 generation ids, 165 calls, none escaped. Keys of 12 non-string kinds at 6 places, no violation. A key that hashes like `generation_id`, and one that hashes like the generation id itself, are refused with the typed error. A workspace whose values are all dicts, and a mapping that carries `"generation_id": g`, are refused with the typed error. A mapping with a hostile unrelated entry validates, because that entry is never read.
- **`compare_eps`.** 60,000 fuzzed calls, none escaped, slowest 6 ms. The grid of two-decimal EPS pairs matches a `Fraction` oracle exactly (notes 6 and 7 cover the other inputs).

## The entry conversion (R6.3)

The reviewer's analysis, which the seat asked for:

- The conversion cannot hide a wrong result, because it only raises.
- It can turn a defect in the module itself (a stray `KeyError` or `AttributeError`) into a typed refusal of an input that should have built. The suite's positive controls catch that for the fixture inputs.
- No argument reached foreign code in the probes, so nothing the conversion converts should have propagated.
- The sweeps do not depend on it. With the conversion removed from the build entry or the validate entry, all seven sweep tests still pass. The identity tests carry P1; the conversion is a backstop.

## Can the sweeps fail?

Yes. Mutations of the module that the seven sweep tests alone kill: dropping the selection walk, dropping the stored-payload walk, dropping the output walk, replay by value instead of text, a walk that admits non-string keys, a walk that admits tuples, and a single workspace that refuses a non-string key. Against the whole suite the reviewer's other mutations were killed (the `>=` boundary, the `generation_id` key found by `==` alone, the identity compare, a mapping holding a non-dict value, the last typed-absent side, a depth bound of 33, a lifecycle state of any type), except the four in notes 1–4 and one equivalent mutant (walking the selection after Task 1: nothing reads the selection earlier).

## Notes (none blocks)

1. **R6.10 test gap.** `owner_lookup`'s type test on `metric` can be deleted and all 402 tests pass. The lookup test passes a bad value for `group` only. The parameter cannot receive a non-string from any of the three entries.
2. **R6.9 test gap.** The test varies one revision at a time. A mutant that echoes a non-string `code_revision` when `semantic_revision` is also bad survives.
3. **R6.4 clause not pinned.** "Nested key order is not compared" has no test. A mutant that compares nested order survives.
4. **R6.6 message not pinned.** Without the empty-dict check, an empty dict is refused with the "do not resolve" message instead of the ruled one. That mutant survives.
5. **R6.6 wording.** "Never by lookup" is not literally true in the mapping form, which reads `available[...]`. Every key is an exact string by then.
6. **Ambient decimal context.** Under a caller's context of `prec=5, ROUND_DOWN`, `compare_eps('3.07', '2.93', precision=2)` returns `4.77` and is still labelled `ROUND_HALF_EVEN`. No code in `engine/`, `lib/`, `scripts/` or `app/` changes the context. It predates round 6.
7. **28-digit double rounding.** 3 of about 6,500 fuzzed comparable results differ from exact half-even rounding, all with operands of 28 to 30 digits.
8. **The identity-test floor.** It is 50 against 55 present, so up to five identity tests can be deleted without failing the test that counts them.

## What the reviewer did not check

- Hosted CI on this head. (The seat did: it concluded with 21 checks passed, 4 skipped and 1 failed, the merge-queue pilot's known red.)
- The `strftime` limit for years before 1000 on Linux. It ran on macOS only.
- Validation at every workspace position: it ran at depth 0 and 1 and at a one-in-six sample of deeper positions. Build ran at every position.
- `tests/test_ci_pack.py`, contract-delta, pyflakes and `git merge-tree`. The CI hunk is unchanged since the head the third review checked, and the seat's harness covers all four.
- The seat's 93 mutants and its probes. It ran its own.
- The round 3–5 packets line by line. Regression against them rests on the 402-test suite, which carries their tests, and on the probes above.

It wrote nothing inside the reviewed worktree, the seat's scratch or the staged records. Its mutants ran against a copy.

## Seat dispositions

The verdict stands. PR #8232 merges at `47441f3b` on concluded CI.

**Note 1, and why it does not block when the third review's F7 did.** F7 was a test that could not fail: the membership-only mutation of the token parser survived the very test written for that rule. Here the R6.10 test does fail when the `group` test is removed; one parameter of one lookup is not covered, and no entry can pass a non-string there. That is a gap in coverage of a ruled clause, not a test that cannot fail. It is carried, not waived.

**Notes 1–4 and 8** are five pins the suite should have. **Notes 6 and 7** are two limits of one kind: a result that depends on the caller's decimal context. **The `strftime` gap** is the platform limit the R6 ruling already lists. None of the eight produces a wrong payload for a well-formed input under the default context, and no code in the repository changes the context.

They are carried together as one bounded follow-up, **T3 R6a**, under its own ruling and its own review:

- pin `metric` for `owner_lookup` and every parameter of the other two lookups (note 1);
- pin the unavailable payload with both revisions bad (note 2);
- pin that nested key order is not compared (note 3);
- pin the empty-dict message (note 4);
- raise the identity-test floor to the number present (note 8);
- compute `compare_eps` under an explicit local decimal context with a fixed precision and `ROUND_HALF_EVEN` (notes 6 and 7);
- replace the `strftime` round trip with a form check that does not depend on the C library.

The last two change the module, so they change `CODE_REVISION`. They should land before Task 4 stores any payload. The Task 4 packet therefore also says: build a stored payload inside the test that uses it, and never commit one as a literal fixture.

**Note 5 — erratum to R6.6.** The sentence "The argument is read by iteration and never by lookup, so no key that is not a string is hashed or compared" is replaced by: "The argument is read by iteration until every key is known to be an exact `str`. Only then is it read by lookup. No key that is not an exact `str` is ever hashed or compared." The code already does this. Nothing else in R6.6 changes.

## What follows

The seat merges PR #8232 by exact head. Task 3 has no Sol hold (Sol `5902318060`). Task 4 stays behind Task 2.
