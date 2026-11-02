# Seat ruling — CDV-1 Task 3, round 5 seat commit (R5a), 2026-09-30

Seat: CDV-1 Meta-CEO, session `251f88c8`. This record covers one seat commit on PR #8232, made after the round-5 lane returned. It changes no grant, no placement and no Task 1 freeze.

## What the lane returned

- Lane `cdv1_t3_interpretation_r5` (glm-codex / glm-5.3, on mini2) returned `COMPLETE` at head `f4a167ff9688e28b25ffe1488fa5cbbe6545e1ca`, with "GAPS: none" and "DEVIATIONS: none".
- The seat's probes of that head:
  - `check_t3_r4.py`: 155 PASS, 0 FAIL;
  - `check_t3_r5.py`: 298 PASS, 8 FAIL;
  - all 23 mutants (r5 m1–m12, r4 m1–m11) killed in the seat's own run.
- The eight failures are one item: four type tests that R5.1 requires to be identity tests.

## The finding

R5.1 says each parse function "tests the type by identity first (`type(value) is str`, never `isinstance`, never set membership on an unchecked value)", and that `_validate_payload_shape` "uses `type(x) is str`, not `isinstance`". The packet's NOT DONE UNLESS list requires that no `isinstance` line tests a scalar value.

At `f4a167ff`, four lines did not meet that:

| Site | Line at `f4a167ff` | Behaviour the seat observed |
|---|---|---|
| `_parse_decimal` | `type(value) not in {str, int, float, Decimal}` | A value whose type raises when hashed escapes `compare_eps` as `RuntimeError`, not the typed error. |
| `_parse_fiscal_scope` | `type(value) not in {tuple, list}` | The same, from build and from validate. |
| `_validate_payload_shape` | `isinstance(value, str)` on handle values | A stored payload whose handle value is a `str` subclass validates. |
| build, release source text | `isinstance(source_text, str)` | No difference found. Task 1 refuses a non-exact text first in every case the seat probed. The line breaches the packet's letter only. |

The lane's "GAPS: none" was wrong for this item. None of the four produces a wrong payload. Two raise an untyped error, and one admits a value that compares equal to the exact string.

## Ruling R5a

The seat fixes the four lines itself and does not dispatch a sixth lane round.

- Each fix is one line and is dictated by R5.1's text. There is no design choice to make.
- A lane round costs about forty minutes.
- The operating brief asks for a bounded design correction when one defect class survives, not another literal special case. The class here is "a type test that is not an identity test". The commit therefore adds a test that closes the class for this module: it parses the module and requires that every `isinstance` tests a container (`Mapping`, `list`, `tuple`) and that every comparison whose left side is `type(...)` uses `is` or `is not`.

## The commit

`38e4e71bc02c0230a1b732629736cfb30157dc98`, parent `f4a167ff`, author Sol CEO. Two files:

- `engine/earnings_narrative/economic_interpretation.py`: the four lines.
- `tests/test_earnings_economic_interpretation.py`: four tests (13 cases) and one import.

The module's `CODE_REVISION` is the sha256 of its own file, so the interpretation identity changes with this commit. That is the round-4 ruling working as designed.

## Verification on the commit

- RED then GREEN. Against the unfixed module the 13 new cases failed: 11 with `RuntimeError`, one with "DID NOT RAISE", one on the AST assertion naming `type(value) not in {str, int, float, Decimal}`. Against the fixed module: 13 passed, and the suite is 225 passed.
- Probes: `check_t3_r5.py` 306 PASS, 0 FAIL; `check_t3_r4.py` 155 PASS, 0 FAIL.
- Seat mutants, each re-admitting a non-identity test: 7 of 7 killed. Three of them admit a subclass (for a number, for the scope container, for a handle value); the AST test cannot see those, and the behaviour tests kill them. The source-text mutant is killed by the AST test alone, because that line cannot be reached with a non-exact text.
- The 23 packet mutants on this head: 23 of 23 killed.
- Seat harness (grants, Task 1 freeze, the dossier job's exact `run:` line, ci_pack, contract-delta, pyflakes, merge-tree): all green. Grants PASS and the Task 1 freeze diff is empty. RED is rc 2 at the merge base, then 225 passed. The dossier job's exact `run:` line gives rc 0 with 2,540 passed and 174 skipped. `tests/test_ci_pack.py` gives 143 passed and 2 skipped. Contract-delta is rc 0, pyflakes is clean, and `git merge-tree` against main `1e2244d5514c` is clean.

## What follows

A bounded Opus re-review of the pushed head, limited to R5.1–R5.7 and this commit. On ACCEPT and concluded CI the seat merges PR #8232. There is no Sol hold on Task 3 (Sol `5902318060`).
