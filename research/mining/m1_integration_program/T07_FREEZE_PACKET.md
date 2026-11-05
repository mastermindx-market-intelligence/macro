# T07 `mining updates / revisions` — seat-authored freeze packet (pre-dispatch)

Authored 2026-09-27 alongside the T03 packet. **Uncommitted** — lands with the T07 wave.
Mandated by R-MIN-31 (every Mining task carries a seat-authored exact truth table, frozen
before the lane runs). T07 is ordered after T04b (R-MIN-05), so this is preparation, not a
dispatch. MGD obligations covered: **MGD-24/26/27/28/35** (R-MIN-28).

## 1. Scope (binding, R-MIN-20)

T07 owns **only** `tests/test_mining_updates.py` and its fixtures. It adds its suite to the
existing `mining-economic-dossier` job's `run:` line and `paths:` — never a second job
(R-MIN-19/R-MIN-26). Consumed owners: `event_workspace_build.py:118-145`,
`documents.py:236-303`.

## 2. The seven proofs, as an exact oracle

R-MIN-20 enumerates the proofs; below each becomes an assertion with a pinned expected value
rather than a shape check.

| # | proof | exact assertion |
|---|---|---|
| 1 | A→B→A keeps three revisions | revision count `== 3`, and the two A revisions are **distinct records** with distinct generations — not deduplicated back to one. Pin the ordered tuple of `(version, generation)`. |
| 2 | unchanged A mints no generation | generation `==` the prior generation (unchanged), AND `prior_lifecycle_state` is **re-applied**, pinned by value. A test that only asserts "no new revision" cannot see a dropped lifecycle state. |
| 3 | unknown version refuses | a typed refusal, pinned by its exact reason word from the closed vocabulary (R-MIN-15); assert the refusal **and** that no partial record was emitted. |
| 4 | unchanged v1 replay is byte-equal | `==` on **bytes**, not on a parsed structure. A structural compare cannot see a re-serialization change. |
| 5 | changed source + stale interpretation | refuses **or** tags — pin WHICH, and the exact tag. `interpretation_stale` is a T04 limitation string, never an absence reason (R-MIN-15); if the revision path emits it as an absence reason that is a defect. |
| 6 | later mapping gated by system-recorded cutoff | the gate reads the **system-recorded** cutoff, never wall clock. Pin that a date-only label stays date-only: `"2026-09-24"` must NOT become `"2026-09-24Z"`. Assert the exact string. |
| 7 | incumbent outputs frozen | homebuilder/Apple outputs and public discovery captured BEFORE Mining registration and byte-equal after. |

Per R-MIN-30 the omission→limitation mapping is frozen and T07 touches two entries:
`source_revision → changed_source` and `page_generation → page_generation_change`. Pin both
by name; an undeclared account-generation mismatch in a revision tuple is **refused as
malformed**, not coerced.

## 3. The gate that must not be gamed — proof 7

> *"expected outputs are never regenerated from the candidate."*

This is the highest-risk line in the whole task, because the cheapest way to make proof 7 pass
is to regenerate the incumbent expectations from the candidate build and then compare — which
passes **by construction** and proves nothing. It is the same defect class as running a
freshness test on a file you just regenerated.

Therefore: the incumbent expectations are **committed fixtures captured before Mining
registration exists**, and the suite compares the candidate against those committed bytes. If
the lane's diff contains any regeneration of the expected files, that is an automatic
rejection regardless of a green suite. Freeze the fixtures in their own commit, before the
suite, and check the commit order.

## 4. Anti-letter-gaming rules (same six as T03, with T07's instances named)

1. Literal pins, never derived from a neighbouring field of the same fixture.
2. Every ordering/sign pin carries a **reversed** case — proof 1's A→B→A needs B→A→B too.
3. Every boolean pin asserts **both** states — proof 2 needs both "generation minted" and
   "generation not minted" cases, or a hardcoded answer satisfies it.
4. Absence/limitation sets compared with `== sorted(...)`, never `in` or subset.
5. Byte-equality where bytes are the claim (proofs 4 and 7) — never a parsed compare.
6. A field accepted but never read is a live defect, not a later task. The revision tuple's
   account-generation field is the one to watch here.

## 5. Delivery gates — "not done unless"

- Incumbent fixtures committed **first**, in their own commit; then probes RED; then repair.
  The receipt is commit order.
- Clean-venv run from the job's own install line; every previously passing Mining test still
  passing (no frozen oracle moved).
- `test_ci_pack.py -k 'curated or exclusive or mining'` green; every test in `run:` also in
  `paths:`; `paths:` covers the import closure.
- Mutation run over the revision decision path; each survivor killed or argued **equivalent on
  the code path**, with the guard that makes it unreachable itself pinned by a killed mutant.
- Review commissioned per **R-MIN-33e**: code excerpt + measured outputs + numbered candidates
  INLINE. Naming an artifact by path spends the reviewer's whole budget on discovery — measured
  twice at 166k and 150k tokens for zero verdicts.
- Before waiting on any check: assert `mergeable != false` (R-MIN-33f), and watch with the
  canonical `scratchpad/watch_pr.sh`, never a fresh per-PR script.
