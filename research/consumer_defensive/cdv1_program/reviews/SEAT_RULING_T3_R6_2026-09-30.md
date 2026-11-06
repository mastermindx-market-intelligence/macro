# Seat ruling — CDV-1 Task 3, round 6 (R6): one boundary for every value, 2026-09-30

Seat: CDV-1 Meta-CEO, session `251f88c8`. This record covers the seat's answer to the third review of PR #8232 (`reviews/OPUS_T3_PR_REVIEW_R3_2026-09-30.md`): rulings R6.1–R6.10, the two seat commits that implement them, and one defect the seat found in its own first commit. It changes no grant, no placement and no Task 1 freeze.

## What the review returned

The third review rejected head `38e4e71b` on seven blocking findings, F1–F7, and recorded six notes.

- F2, F3 and F4 are three instances of one class: an exception that is not the typed one leaves a public function.
- Note 4 is an instance of a second class: the build accepts a value, and validation then cannot replay the payload it returned.
- F1 is a contract item (R5.7 (1), the mixed case).
- F5, F6 and F7 are tests that cannot fail.

The second review found the first class at `e8666eed`. Round 5 was commissioned to close it with one parsing boundary. Round 5 closed it for the scalars its packet named and left it open for every value the packet did not name.

## Why the seat wrote this round itself

The program's default is that lanes do the labor and the seat makes only small commits that a ruling dictates. The first commit of this round is not small: two files, 1,093 insertions and 116 deletions. The seat records that as a departure from the default, for three reasons.

- Rounds 4 and 5 were lane rounds against this class. Each closed the instances its packet listed. A sixth packet that listed more instances would repeat the failure.
- The operating brief says: "If the same semantic defect class survives again, propose a bounded design correction rather than another literal special case." The correction is a design, and specifying it completely is most of writing it.
- Task 1 already solved the same problem for the workspace (R193, R195, R196). The design is Task 1's boundary, applied to the values Task 1 does not walk.

The cost of that choice is that the seat cannot accept this work. The independent check is a bounded Opus re-review of the pushed head. The suite's own sweeps and the mutant specification are the parts of the evidence anyone can re-run from the repository; the seat's probes below are outside it and are testimony.

## The properties R6 is held to

The rulings are judged against four properties, not against a list of cases.

- **P1.** For any value at any position of any argument, a public entry returns or raises `EconomicInterpretationError` (or its subclass `UnsupportedInterpretationVersion`). The one deliberate exception is R6.3: an exception outside the converted set propagates.
- **P2.** Validation accepts no substituted value at any position of a stored payload.
- **P3.** Whatever a build returns is bounded exact JSON.
- **P4.** Whatever a build returns as supported replays through validation on the same inputs, in both forms of `workspaces`.

The public entries are `build_economic_interpretation`, `validate_economic_interpretation` and `compare_eps`.

## Task 1 precedent

R6 adopts three frozen Task 1 rulings. It does not edit Task 1.

- **R193.** The walk admits a closed set of types by exact type. For Task 1 that set is `dict`, `list`, `str`, `int`, `float`, `bool`, `None`, plus `tuple` and `Fraction`, and dict keys are walked as values. A workspace Task 1 admits can therefore carry a key that is not a string.
- **R195.** Type tests decide by identity alone.
- **R196.** The entry converts `TypeError`, `ValueError`, `ArithmeticError`, `LookupError` and `AttributeError`. Every other exception propagates.

Task 1's bounds are 32 levels, 100,000 values and integers of magnitude below 10**640. Task 1 walks the workspace and the source texts before any lookup on them.

## Rulings R6.1–R6.10 (binding on PR #8232)

**R6.1 — one walk.** One function decides whether a value is bounded exact JSON: an exact `dict` with exact `str` keys, an exact `list`, `str`, `int` of magnitude below 10**640, finite `float`, `bool` or `None`, within 32 levels and 100,000 values. A tuple is refused. The walk runs on:
- the caller's `selection`, before anything reads it;
- a stored payload, before validation reads anything but its type;
- the payload a build is about to return.

The workspace and the source texts are Task 1's to walk. Task 3 calls Task 1 before it looks anything up in either. `fiscal_scope` keeps its own rule: an exact tuple or list of exactly four canonical dates.

**R6.2 — identity tests only.** Every type test in the module is `type(x) is T` or `type(x) is not T`, containers included. The module uses no `isinstance`, no `issubclass` and no `__class__`. One test parses the module and enforces that, with a floor of 50 identity tests so the rule cannot be met by deleting them. The module has 55.

**R6.3 — the entry converts what a built-in raises.** Each public entry converts `TypeError`, `ValueError`, `ArithmeticError`, `LookupError` and `AttributeError` into `EconomicInterpretationError` with the message `a value has the wrong type or range where the interpretation reads it (<exception class>)`. `EconomicInterpretationError` and `UnsupportedInterpretationVersion` pass through unchanged. Every other exception propagates. The conversion only raises; it never returns a payload, so it accepts nothing the body refuses.

**R6.4 — replay compares text.** Validation compares `interpretation_id`, then the canonical JSON text of the stored and the rebuilt payload (sorted keys, compact separators, `ensure_ascii=False`). A value of another type that compares equal, such as `True` for `1` or `1.0` for `1`, is refused. Nested key order is not compared. The top-level key order is, as before.

**R6.5 — what a build requires beyond Task 1's walk.**
- `generation_id` and `event_id` are exact `str`. Otherwise: `workspace generation or event identity is malformed`.
- `lifecycle`, when present, is an exact `dict` whose `state` is a `str` or `None`. Otherwise: `workspace lifecycle is malformed`.
- A selected handle's `fact_id` and `metric`, when present, are exact `str`. Otherwise: `selected fact handle is malformed`.
- `selection.facts` is `None` or an exact list, and the selection selects at least one observation. Otherwise: `selection selects no observation`.

**R6.6 — `workspaces` is one workspace or a mapping.**
- A mapping from generation id to workspace has only exact `str` keys and only exact `dict` values.
- Anything else is one workspace. It is found under its own `generation_id`, which must be an exact `str`. Task 3 puts no other rule on a single workspace's keys; the rebuild decides what else it may carry.
- The argument is read by iteration and never by lookup, so no key that is not a string is hashed or compared.
- An empty dict, a value that is not an exact dict, and one workspace without a string generation id are refused with `workspaces must map generation ids to workspaces`.

**R6.7 — R5.7 (1), the mixed case.** A declined EPS comparison reports Task 1's reason and detail for the first selected side that is typed-absent, current side first. It reports `not_selected` only when no selected side is typed-absent.

**R6.8 — the EPS interval is decided by comparison.** `compare_eps` declines when `uncertainty >= prior`. It does not subtract them, so extreme exponents cannot overflow.

**R6.9 — the unavailable payload.** It echoes a revision only when that revision is an exact `str`. Otherwise the field is `None`.

**R6.10 — the three lookups.** `family_lookup`, `format_value_and_unit` and `owner_lookup` test the type by identity before they read the value.

## What R6 amends

- **R5.1's allowance for `isinstance` on containers** (r5 packet, the NOT DONE UNLESS item on `isinstance` lines). R6.2 replaces it. A container whose own type is hostile was outside round 5's review bar; it is inside R6's.
- **r4 packet, `facts`** ("`None` (all native rows) or a list/tuple of native handles"). Under R6.5 a tuple is refused, and a list that selects nothing is refused. The 24-item cap is unchanged.

Everything else in the r3, r4 and r5 packets and in ruling R5a still binds.

## The seat's own finding after the first commit

Every check the seat then had was green on the first commit, `be277281`: the harness, the probes, the sweeps, 89 of 89 mutants and hosted CI. The seat then probed a position its sweeps did not cover: dict keys of the types Task 1 admits.

- **Finding.** R6.6 as first written refused, in the single-workspace form, any workspace with a key that is not a string. Task 1 admits such keys. A build could therefore return a supported payload that validation refused for the same workspace. That breaks P4.
- **Measurement at `be277281`.** The key probe made 15,954 calls: 8,270 built and replayed, 7,444 were refused with the typed error, and 240 built and did not replay. All 240 were at the workspace root in the single-workspace form. None was in the mapping form, none at a nested mapping, and no call broke P1 or P3.
- **Why the suite missed it.** Its sweeps substituted values and never added keys, and its replay test validated the single-workspace form only.
- **Repair.** The second commit, `47441f3b`, rewrites `_workspaces` as R6.6 now reads, and the suite gains the cases that would have caught it (below).

The first commit's text of R6.6 was the seat's error. The seat records it here because the same review standard applies to the seat's work as to a lane's.

## Dispositions

| Item | Disposition |
|---|---|
| F1 | Fixed (R6.7). The reviewer's mutation, reading the prior side first, is now a seat mutant and is killed. |
| F2 | Fixed (R6.8), and the class is closed by R6.3. |
| F3 | Fixed (R6.5, handle fields), and the class is closed by R6.3. |
| F4 | Fixed (R6.5, lifecycle), and the class is closed by R6.3. |
| F5 | Fixed. The segment labels are compared with literal labels, and those literals are checked against the owner's `segment_scope`. The constant-label mutation is killed. |
| F6 | Fixed. A five-entry fiscal scope is passed and refused. The `len(value) < 4` mutation is killed. |
| F7 | Fixed. The token parser is tested with a `str` subclass and with one whose type raises when hashed or compared. The membership-only mutation is killed. |
| Note 1 | Fixed. The clock-rules test now builds one payload for each refusal it pairs with. |
| Note 2 | Fixed (R6.5, lifecycle state). |
| Note 4 | Fixed (R6.5, a selection selects at least one observation). |
| Note 6 | Fixed with F5. The test compares the build's metrics and the module's display table with two literal sets, and no longer sorts metrics by the build's own `group`. |
| Note 3 | Not carried. `_parse_decimal` accepts what `Decimal` accepts for a string. Each spelling it admits denotes one number, and no ruling sets a narrower grammar. |
| Note 5 | Not carried. `_decimal` and `_definitions()` are style. |

## Known limits

None of these produces a wrong payload for a well-formed input. The seat lists them so the next reader does not have to find them.

- No shape rule on `issuer`. A value there that is not exact JSON is refused by the output walk (R6.1).
- No exact key set for a selection item.
- `clocks.correction` is `lifecycle.state` as a `str` or `None`. It is not a closed vocabulary.
- `compare_eps` with `precision=None` returns the quotient at the decimal context's precision.
- Task 3 has no rule of its own on lone surrogates. The digest's encoding error is converted at the entry (R6.3).
- Task 3 requires an exact `str` event id whatever path Task 1 took to admit the workspace.
- A stored copy must keep the top-level key order the build returns. A plain JSON round trip replays. A copy written with sorted top-level keys is refused. This goes into the Task 4 packet.
- The canonical-form check for instants and dates round-trips through `strftime`. For a year before 1000 that depends on the platform's C library. The seat measured it only on macOS with CPython 3.12.13, where such a value is accepted. No source clock or fiscal date is that old.

## The commits

Both are on `claude/cdv1-t3-economic-interpretation`, author Sol CEO, on top of `38e4e71b`.

| Commit | Files | Size | Content |
|---|---|---|---|
| `be27728111867392e6098ad37baa2ee3503dc2eb` | module, suite | 1,093 insertions, 116 deletions | R6.1–R6.10 as first written, and the suite's sweeps |
| `47441f3b5cdd85f8bf2a308b5e346a48347f2f1f` | module, suite | 78 insertions, 23 deletions | R6.6 as it now reads, and the key cases |

The fixtures file and the CI hunk are unchanged since `38e4e71b`. The module's `CODE_REVISION` is the sha256 of its own file, so the interpretation identity changes with each commit.

What the suite gained, 225 tests to 402:

- **Sweeps.** A hostile value, a look-alike and an exact substitute at every position of the workspace, the selection and a stored payload, for build and for validation.
- **Replay.** Every substituted workspace that builds must validate, as one workspace and as a mapping. The substitutes include the value types and key types Task 1 admits beyond JSON.
- **Keys.** One workspace with a key of each non-string type Task 1 admits builds and validates in both forms. A key that hashes like a real key and raises when compared is refused with the typed error.
- **The entries.** Each entry converts each of the five exception classes, and lets a `RuntimeError` through.
- **Bounds.** A value at each bound is read, and one past it is refused.
- **The reviewer's cases.** F1–F7 and notes 1, 2, 4 and 6, as listed above.

## Verification on the pushed head `47441f3b`

Suite and RED:
- The suite: 402 passed.
- The same suite against the module at `38e4e71b`: 139 failed, 263 passed.
- The same suite against the module at `be277281`: 7 failed, 395 passed. The seven are the replay sweep and the six key cases.

Mutants, each run against the whole suite:
- 63 seat mutants for R6, including the reviewer's mutations for F1, F5, F6 and F7 and ten for `_workspaces`: 63 of 63 killed.
- 23 packet mutants (r5 and r4): 23 of 23 killed.
- 7 seat mutants for R5a: 7 of 7 killed.

Seat harness on the pushed head: every check passed. The file grants hold and the Task 1 freeze diff is empty. The suite: 402 passed. With the implementation removed, as at the merge base, the suite fails at collection. The dossier job's exact `run:` line: 2717 passed, 174 skipped in 543.20 s. `tests/test_ci_pack.py`: 143 passed, 2 skipped. Contract-delta and pyflakes are clean. `git merge-tree` against main at `a7e00a9af0f4` merges cleanly.

Seat probes, run on a copy of the commit's tree:
- Round-5 checks: 306 of 306. Round-4 checks: 155 of 155.
- The independent sweep from before R6, full mode: 0 untyped exceptions.
- The extended sweep: 27,030 cases, 0 violations.
- Hostile keys, 4,700 calls: 0 untyped exceptions.
- Keys Task 1 admits, at every mapping of the workspace and of the selection: typed-absent fixture case 6,267 calls, 0 violations; valued fixture case 10,299 calls, 0 violations.
- Value types Task 1 admits, 18 of them at each workspace position: typed-absent fixture case, 489 positions and 8,803 calls, 0 violations; valued fixture case, 849 positions and 15,283 calls, 0 violations.

Hosted CI on `47441f3b`: 21 checks passed, 4 were skipped and 1 failed. The failure is `ci-authority/codex/merge-queue-pilot`, the merge-queue pilot's known red; it was red on `be277281` as well. The dossier job's test line: 2715 passed, 176 skipped in 990.20 s.

## The dossier job's time

The suite joins the `earnings-economic-dossier` job, whose timeout is 20 minutes. Hosted, that job's test line took 1,006.68 s at `38e4e71b`, 967.95 s at `be277281` and 990.20 s at `47441f3b`. Locally the same line took 543.20 s on this head, of which the Task 3 suite is about 36 s. The headroom is thin for reasons that predate this PR, and this PR does not touch `timeout-minutes`.

Two consequences:
- Task 4's suites do not join this job.
- Giving the job headroom is a program follow-up under its own ruling.

## What follows

A bounded Opus re-review of `47441f3b`, held to P1–P4, R6.1–R6.10 and the rulings that still bind. On ACCEPT and concluded CI the seat merges PR #8232. There is no Sol hold on Task 3 (Sol `5902318060`).
