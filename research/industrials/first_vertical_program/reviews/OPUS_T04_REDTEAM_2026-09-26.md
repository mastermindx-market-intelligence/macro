<!--
Provenance: commissioned by the GMI Industrials first-vertical Fable Meta-CEO seat
(Claude Code session c6467452-92b1-436b-9999-ee2ae3d2b14b, account claude8) as part of
operation gmi-industrials-fable-ceo-e2e-20260924-chairman-001.

Two independent Opus `reviewer` children were spawned on ROUTE: review / MODE: READ_ONLY
against PR #8062 head 365c2666b88a8e0afdae5f294aef3f9553e44ea0. Reviewer A (arithmetic
truth + fabrication) and an earlier single-reviewer attempt BOTH exhausted their 24-turn
budgets on discovery and returned no verdict; SendMessage is unavailable in this session,
so neither could be resumed. Reviewer B (receipt/test causality + ownership) returned a
complete receipted verdict. The seat itself then executed the unfinished arithmetic and
fabrication probes, since the seat is independent of the builder (the lane wrote the code)
and the program's quality law makes the independent adversarial pass — not the lane's own
reviewer — the real gate. The lane's round-1 self-verdict was PASS with 0 blockers; that
verdict was wrong.
-->

# T04 result-to-cash — round-1 adversarial adjudication (PR #8062)

Head reviewed: `365c2666b88a8e0afdae5f294aef3f9553e44ea0`
Measured against `origin/main` `1c85f27bfe7e3bcbbb7ce323a2bdab0839527c59`, merge-base `c5e6f0bb5d395d0aeb5fc4c54e31e297376e6d5a`.
Verdict: **FIX_REQUIRED** — 5 blockers, 2 majors, 1 minor. Round-2 repair ruling: `packets/rulings_t04_r2.md`; lane `ind_t04_r2` dispatched on mb 2026-09-27 03:02Z.

## What is sound (do not re-open)

- **Ownership is clean.** Exactly three files versus the merge-base: `+engine/fundamental_forensics/industrials_result_cash.py`, `+tests/test_industrials_result_cash.py`, `M .github/ci/legacy-jobs.yml` (1939 insertions, 1 deletion). No T01 file, nothing under `data/` or `site/`, one CI job.
- **Consumption of T01's merged surface is honest.** `cell` (118 refs), `comparison` (43), `typed_absence` (2) all by import at `tests/test_industrials_result_cash.py:27`; no local re-declaration or shadowing of any T01 name; no `harness.get(slug)` (R9's deleted stub is unreachable); no `example.invalid` in product code; no real Exponent/Pentair figure. Module imports are stdlib-only.
- **The arithmetic core is clean and causally bound.** No `float(` anywhere, no `round()`, and `Decimal` is only ever constructed from validated decimal *text* — a transformation `factor` must be a `str`, an operand `value` must be a non-bool `str`, non-finite tokens are rejected, so `Decimal(<float>)` is unreachable. Mutations that flipped a sign, dropped a rollforward leg, weakened a refusal boundary and changed `formula_version` were all caught by the suite.
- **`formula_version` rides every result** (`:665`, `:691`, `:1107`) and that binding is tested; it deliberately does not ride the receipt, matching spec §1.

## Blockers

**B1 — the production receipt constructor is never fed to the consumer it exists for.** `qualify_operands` decides `required_basis_unknown` / `perimeter_mismatch` / `duration_mismatch` / `scale_mismatch` / `currency_mismatch` from the receipt's `checked` block and `transformations` (`:402-431`), but all 41 derivation/qualification tests build their receipt from T01's *test* helper `comparison(...)`. Only three test bodies touch `build_comparison_receipt` (`tests/test_industrials_result_cash.py:54`, `:66`, `:79`) and none passes its output into `derive_result_cash`/`qualify_operands`. Measured: making `build_comparison_receipt` emit `checked` all-True regardless of caller — a blanket false certification of every comparability gate — leaves the suite at `48 passed`.

**B2 — receipt identity is asserted nowhere.** `receipt_id` is derived at `:197-200`; the suite's only claim is shape membership (`:56`). Freezing `receipt_id` to a constant, dropping `checked` from `digest_input`, and echoing a constant `purpose` each survive at `48 passed`.

**B3 — `receipt_ref` on results is never bound to the receipt.** Set at `:673`/`:697`; the suite asserts only `"receipt_ref" in r` (`:708`) and key-set membership (`:717`). Freezing it to a constant on all three result constructors survives at `48 passed`.

**B4 — a `segment_change_bridge` with ZERO segment legs fabricates a certified number** (seat probe). `_derive_segment_change_bridge` seeds `total = Decimal("0")` (`:952`) then validates only the segment operands that are present, so a caller supplying no `segment_*_change` operand at all gets corporate + eliminations certified as a segment bridge:

```
cells = [cell("40", metric="corporate_change"), cell("-10", metric="eliminations")]
derive_result_cash("segment_change_bridge", cells, comparison_receipt=comparison("segment_bridge", cells))
-> {"status": "ready", "value": "30", "label": "reported", "limitations": [], ...}
```

There is no defence in depth: `qualify_operands(..., formula="segment_change_bridge")` returns `status="ready"`, `limitations: []` on the same input. A sweep of all seven formulas with a single irrelevant operand found no other instance, so the hole is specific to this path. This is the same family that got the sibling Mining program's T04a rejected twice for fabricated derivation legs its own suite asserted happily.

**B5 — a typed-absent unallocated leg is silently zeroed, contradicting an invariant this suite tests elsewhere** (seat probe). The unallocated loop `continue`s an operand without a value (`:983`), so a declared absence disappears from both value and limitations:

```
no unallocated leg at all                 status=ready    value=180  residual=0  lim=[]
unallocated valued 7                      status=ready    value=187  residual=7  lim=['bridge_residual_disclosed']
unallocated TYPED-ABSENT (correct shape)   status=ready    value=180  residual=0  lim=[]      <-- identical to "no leg"
segment leg TYPED-ABSENT (control)         status=refused  value=None             lim=['operand_missing:segment_c_change']
```

The caller cannot distinguish "the issuer disclosed no unallocated amount" from "the issuer disclosed one we could not read", while `test_cash_after_capital_payments_refuses_typed_absence_operand` (`:163-185`) asserts the opposite invariant for a sibling formula and the comment at `:984` claims the residual is "disclosed, NOT silently allocated".

## Majors

**M1 — `operand_refs` order and content unasserted.** Spec §1 requires owner_ref/revision/digest of every operand in order; `test_ind_sf01` (`:128-141`) asserts only `len(...) == 2`. Reversing `operand_refs` on every result survives `48 passed`; sorting `refs` inside `build_comparison_receipt` survives `48 passed`.

**M2 — `unknowns` neither round-tripped nor in identity.** `build_comparison_receipt(..., unknowns=('basis',))` returns the same `receipt_id` as the base receipt (`ddd195368d303246`) because `digest_input` covers only `purpose`, `refs` and `checked` — so two receipts disclosing different unknowns, or different conversion factors, share one identity. The suite's only claim, `unknowns == []` (`:60`), is satisfied by a mutation hardcoding `[]`.

**m1 (minor, no change needed)** — `formula_version` is absent from receipt keys but present on all results, consistent with spec §1.

## Mutation table (reviewer B; 13 mutations on a scratch copy of `engine/`, suite re-run per mutation)

| # | Mutation | Outcome | Suite |
|---|---|---|---|
| M1 | sign flip: `cash_after_capital_payments` `-` → `+` | CAUGHT | 4 failed, 44 passed |
| M2 | drop leg: rollforward drops `exchange_movement` | CAUGHT | 3 failed, 45 passed |
| M3 | freeze `receipt_id` to a constant | SURVIVED | 48 passed |
| M4 | weaken refusal: `prior_dec <= 0` → `== 0` | CAUGHT | 1 failed, 47 passed |
| M5 | `checked` all-True, ignores caller | SURVIVED | 48 passed |
| M6 | `unknowns` always `[]` | SURVIVED | 48 passed |
| M7 | `transformations` always `[]` | CAUGHT | 1 failed, 47 passed |
| M8 | freeze `receipt_ref` on all 3 result constructors | SURVIVED | 48 passed |
| M9 | result `formula_version` → `"v0"` | CAUGHT | 7 failed, 41 passed |
| M10 | `refs = sorted(refs)` in `build_comparison_receipt` | SURVIVED | 48 passed |
| M11 | `operand_refs` reversed on results | SURVIVED | 48 passed |
| M12 | `receipt_id` digest drops `checked` | SURVIVED | 48 passed |
| M13 | constant `purpose` echoed | SURVIVED | 48 passed |

8 of 13 survived; every survivor lives in the receipt plane.

## Consequence for dependents

T03 and T05 may branch off this head's **API surface** — it is stable and stdlib-pure, and every receipt-plane repair is test-side except M2's optional digest widening. But no dependent may pin a `receipt_id` literal, a receipt snapshot, or a golden receipt file until B2/M2 land, because widening the digest changes `receipt_id` values. A consumer reading only `status` / `value` / `limitations` / `operand_refs` is safe today. Recorded in `packets/rulings_t05.md` R6 and `packets/rulings_t06.md` R7.

## Gaps

- `pyflakes` is not installed under this host's Python 3.14, so the packet's lint receipt was checked by grep instead.
- No mutation was applied inside `qualify_operands`' own `checked` consumption; B1 rests on the coupling gap plus the M5 measurement.
- The CI transitive-closure gate was verified twice (truncated reviewer, then the seat: `2 passed, 133 deselected in 220.34s`) and deliberately not re-run.

---

# Round 2 — repair, re-verification, and a sixth blocker (seat, 2026-09-27)

Lane `ind_t04_r2` (mb, MiniMax-M3, 1213 s) returned `PASS 0B/0M/0m` at
`05ad9c8da01960c25ba0e5f3855d2da09eb711af` — seven commits, one per ruled item, a
descendant of the reviewed head, diff still the three owned files. Per the program's
quality law the lane's own verdict decides nothing, so every cure was re-verified by
mutation and probe rather than by the presence of a test.

## Cures verified

| Item | Round-1 evidence | Round-2 re-verification |
|---|---|---|
| B1 receipt constructor unbound from its consumer | `checked` all-True survived (`48 passed`) | mutation now **CAUGHT** (3 failed, 68 passed) |
| B2 `receipt_id` identity unasserted | frozen id survived; digest-drops-`checked` survived | both now **CAUGHT** (4 failed / 1 failed) |
| B3 `receipt_ref` unbound | frozen ref survived | single frozen site now fails **7 tests** |
| B4 zero-segment bridge fabricates | `ready, value="30"`, no limitations | probe now **refused** `operand_missing:segments` at BOTH `derive_result_cash` and the formula-aware `qualify_operands` branch |
| B5 typed-absent unallocated silently zeroed | byte-identical to "no leg at all" | probe now **refused** `operand_missing:unallocated_change`, distinct from the no-leg case |
| M1 `operand_refs` order/content unasserted | reversed refs and sorted refs both survived | both now **CAUGHT** (1 failed each) |
| M2 `unknowns` outside identity | `unknowns=[]` survived | **CAUGHT**; digest now covers purpose + refs + checked + unknowns + transformations |

Suites at the lane head: **93 passed** (T04 + T01), up from 48 + 22.

## B6 — a sixth blocker neither reviewer saw (BLOCKER, seat-cured)

An **omitted** `checked` argument to `build_comparison_receipt` defaulted to all-True,
so a caller who said nothing about comparability was recorded as having verified every
gate — and that suppressed a real refusal:

```
checked OMITTED (defaults all-True)    duration_checked=True  -> ready    []
checked={} (nothing verified)          duration_checked=False -> refused  ['duration_mismatch']
checked={'duration': True} only        duration_checked=True  -> ready    []
```

A quarter compared against a year qualified `ready` with no limitations. The omitted
argument was strictly more permissive than explicitly asserting nothing — an inverted
refuse-by-default contract, undocumented in the docstring, and untested at both poles
(flipping the default to all-False broke no existing test).

**A first hypothesis was disproved by probe and is recorded because it corrects the
round-1 report.** I expected the all-True default to launder *any* comparability gate,
which is also what round 1's B1 asserted ("a blanket false certification of every
comparability gate"). It does not: with `checked` forced all-True, `qualify_operands`
still refuses `currency_mismatch`, because that gate is decided by inspecting the
operands. Only gates where the receipt is the sole evidence of comparability — duration,
and the perimeter/definition class — consult it. B1's defect was real (the field was
unasserted); its stated consequence was wrong in mechanism and scope.

Seat-cured at **`0e3344a9071f`** (precedent: T01 round 6 — three fully prescribed
one-liners cost less at the seat than a fabric round): gates default False, `checked=None`
and `checked={}` are now the same receipt, plus four tests — the quarter-vs-year
suppression probe, an over-refusal guard proving compatible operands still qualify, the
`None`=={} identity, and the receipt `purpose` round-trip that a constant-purpose mutation
had survived. Revert mutations for both cures are now **CAUGHT** (2 failed / 1 failed).

## Final verification at `0e3344a9071f`

- `python3 -m pytest tests/test_industrials_result_cash.py tests/test_industrials_dependency_binding.py -q` → **97 passed in 2.87s**
- `python3 -m pytest tests/test_ci_pack.py -k curated_exclusive -q` → **2 passed, 133 deselected in 205.34s**
- name-status diff against `origin/main` → the three owned files only; no `data/`/`site/` write, no T01 file touched
- ancestry check against the reviewed head `365c2666b88a` → DESCENDANT_OK

## Binding on dependents

B2/M2 widened the `receipt_id` digest, so **`receipt_id` values changed**: T03/T05/T06 may
consume the API surface but must pin no `receipt_id` literal, receipt snapshot or golden
receipt file. `qualify_operands` enforces a formula's own operand requirements only when
`formula=` is passed — omit it and the empty-collection guard is inert. An omitted `checked`
now certifies nothing, so a caller must declare each gate it actually verified. Recorded as
`rulings_t05.md` R6+R7 and `rulings_t06.md` R7+R8.

## Method note for future rounds

Three reviewer commissions on this artifact produced one verdict. Two exhausted their
24-turn budgets on discovery (no resume channel was available, so neither could be
continued), and the one that returned a verdict overstated its headline finding's
consequence. The seat's own probes found two of the six blockers (B4, B5) and the sixth
(B6) outright. For the remaining tasks: inline the code excerpt and measured probe output
in the commission so the worker's budget goes to judgment, and expect the seat to run the
decisive probes itself.
