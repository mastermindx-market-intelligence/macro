# R-IND — T02a harness gate: make T02's mandated two-run assertion able to fail

**Task:** the harness half of T02 of the frozen Industrials nine-task plan, operation
`gmi-industrials-fable-ceo-e2e-20260924-chairman-001`.
**Workstream:** `WS:GMI-INDUSTRIALS-FIRST-VERTICAL`.

**T02 itself is still NOT DISPATCHABLE and this increment does not make it so.** The frozen
plan's own dependency-graph line authorizes exactly this much work during a hold:

> Synthetic tests may be authored while a gate is held, but cannot make that gate passed.
> Run tasks concurrently only when grants and changed paths are disjoint.

**Rulings R1–R5 below are scoped to T02/T02a.** They do not renumber `R-IND-01..07` or
`R-IND-10..22` in `R-IND-2026-09-24-wave1.md`.

---

## Why this increment existed to be done

The frozen plan (blob `a5462dc7f36aea08c57ce43a8a230ef00ebae802`, section T02) mandates a
two-run test as the anti-shortcut gate for T02 — the plan says in the same breath that
"Profile enrollment alone must not satisfy this task". Measured against merged `origin/main`,
that mandated test could not grade anything:

| Plan line | State on main before this increment |
|---|---|
| `before = h.members()` … `assert before <= h.members()` | `_PublicationHarness.members()` was `return set()` — an unmarked stub, the only method in the file with no docstring. `set() <= set()` is true in **both** directions, so the assertion could never fail. |
| `h.get('case_a')['edition']` | `_PublicationHarness` had **no `get()` at all**. `_SyntheticClient.get` exists and is a different class. The assertion raises `AttributeError`. |
| `h.run_refresh({'case_b': 'edition_2'}, fail_sources=('case_a',))` | The first parameter was `_changes` — deliberately **unused**. Per-case editions were not modelled, and the fake served `503` for the submissions URL whenever `fail_sources` was non-empty, refusing the **whole** refresh — so `case_b` could not advance while `case_a` carried. |

The two failure modes are not equivalent and the quiet one is the dangerous one. `h.get(...)`
fails loudly, so a lane would notice it. `h.members()` passes silently, so a lane that
repaired only the loud half would ship a green suite whose central assertion still certified
nothing — which is the defect family this program has already measured twice
(`DSC:A-LANE-SELF-VERDICT-IS-NOT-A-CLOSURE-GATE`, and the T04 B4/B6 cures).

## R1 — `members()` reports real state; an empty stub is a defect, not a placeholder

`members()` returns the case keys the harness actually holds. A future edit back to a constant
empty collection is caught by
`tests/test_industrials_dependency_binding.py::test_members_is_not_an_empty_stub_after_enrollment`.
No assertion in this program may be satisfied by an empty container standing in for absent
state.

## R2 — `get()` answers with a deep copy, and typed absence is a `KeyError`

`get(case_key)` returns `{"edition", "stale", "observed_acceptance"}` as a **deep copy**: a
caller that mutates the answer must not be able to rewrite the state its own assertion then
reads. An unenrolled case raises `KeyError` rather than returning `{}` — a blank record reads
as "present but empty", which is the absence-shaped-as-presence trap
(`DSC:AN-OMITTED-OPTIONAL-ARGUMENT…` family).

## R3 — `fail_sources` names CASES and is causal per case

`run_refresh(changes, fail_sources=…)` acquires once per requested case, refusing only the
named ones. Deleting a name flips that case to advancing on the very next call. An unnamed
case in the same call still advances. **The empty-`changes` path is byte-identical to the
landed behaviour** — one acquisition, the owner's `ok`/`unavailable` shape, `source` = the
named fail source — because all three merged `run_refresh` tests take that branch and they
are the T01 round-5 N3 cures. Do not "simplify" that branch away.

## R4 — a source failure carries; it never restamps and never invents

A refused case with a predecessor keeps its `edition` **and** its `observed_acceptance`, and
is marked `stale: True` in place. A refused case with **no** predecessor is not created at
all. `observed_acceptance` is taken from the owner's own result, never from a harness clock,
so a silent re-observation is detectable by inspection rather than by trust.

## R5 — what T02 still owes, and what a dispatching lane must not conclude

This increment is the harness only. **T02 is not started.** It still owes, all behind the
shared seam: `expo_issuer`, `pnr_issuer`, `expo_profile`, `pnr_profile`; their registration
through the incumbent lookup functions in `issuer_profiles.py`, the `event_workspace.py`
registry and `scripts/refresh_event_workspaces.py`; the discovery-population extension that
must not overwrite Semiconductor/homebuilder membership; the fiscal-calendar declaration test;
and `tests/test_industrials_issuer_enrollment.py` carrying `test_ind_d04`, `test_ind_d05`,
`test_ind_r210` per the frozen traceability table. This increment deliberately did **not**
create that file, so its absence stays an honest signal that T02 is unstarted.

**The seam census, re-measured 2026-09-27 rather than inherited** (`git ls-tree` on
`origin/main`, `refs/pull/7870/head` @ `a0d7b054ff23`, `refs/pull/7905/head` @
`b6808dfcc166`):

* `engine/company_intelligence/industrials_profiles.py` — T02's NEW file — is absent from
  **all three** refs. The path itself is **uncontested**; #7870 carries `financial_dossier.py`
  and #7905 carries `pg_profile.py`/`pg_envelope.py`, which is the sibling idiom T02 follows.
* What is contested is only the **registration sites**: `issuer_profiles.py` (main, #7870,
  #7905), `event_workspace.py` (#7870), `scripts/refresh_event_workspaces.py` (#7870),
  `event_workspace_build.py` (#7870, #7905).
* `tests/industrials_result_cash_helpers.py` is **uncontested**: absent from #7905, and
  #7870's copy is byte-identical to main's (inherited through a base merge, not edited), so
  this increment collides with neither.

**Therefore the reason T02's module body is blocked is not path collision — it is idiom
instability.** #7905 is DRAFT under an Opus R7 audit, and the wave-1 ruling binds T02 to
branch after it merges precisely so the sibling profile module is written against a **frozen**
idiom. A lane that reads "T02 edits the seam" and concludes the whole task is path-blocked
will miss that the majority of T02+T03's volume lands in an uncontested new file whose only
real gate is #7905 freezing. When #7905 merges, re-read its landed `pg_profile.py` idiom
first and dispatch T02's module body against that, not against these notes.

---

**Verified 2026-09-27 at branch `claude/ind-t02a-harness-gate`.**
`python -m pytest tests/test_industrials_dependency_binding.py tests/test_industrials_result_cash.py -q`
→ `103 passed` (was `97 passed` at T04's closure; +6 tests, no test changed or removed).
Seven mutations applied to the harness one at a time, each with the registered suite line
re-run and the tree restored — `members()` back to the empty stub; a refused case advancing
its edition; a refused case restamped with a fresh observation; a refused case invented with
no predecessor; `get()` handing out the live record; `fail_sources` back to refusing the whole
refresh; the stale flag never set — **7 CAUGHT, 0 survivors**. Curated-scope closure gate
`python -m pytest tests/test_ci_pack.py -k curated -q` → `5 passed, 130 deselected`, so the
Industrials job's `paths:` still covers its own import closure and **no `.github/ci/**` edit
was needed**: the new tests live in the already-registered `test_industrials_dependency_binding.py`
rather than a new unregistered file that would never have run.

Context: `agentos/handoffs/GMI-INDUSTRIALS-2026-09-24-first-vertical-implementation.md`,
`agentos/workstreams/WS-GMI-INDUSTRIALS-FIRST-VERTICAL.md`,
`research/industrials/first_vertical_program/rulings/R-IND-2026-09-24-wave1.md`.
