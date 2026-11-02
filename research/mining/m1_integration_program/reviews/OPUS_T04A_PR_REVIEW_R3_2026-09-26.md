# T04a (PR #7950) — round-3 independent review and seat repair

**Artifact reviewed:** PR #7950, head `94e74dd8fd167124d38009b8ef3844bac4b3fe94`
**Verdict:** `ACCEPT_AFTER_NAMED_FIXES` — did not merge as delivered; merges after the named subset.
**Repaired at:** head `7c81baed306d51d90d3fca1ee501456d1f9b990b`
**Rulings tabled:** R-MIN-33, 33a, 33b, 33c, 33d, 33e.

## How this round was reviewed, and why the shape changed

Rounds 1 and 2 were rejected by an independent Opus red-team under the freeze-then-repair
law. Round 3's review was attempted the same way **twice, and returned no verdict either
time**:

| Attempt | Cost | Outcome |
|---|---|---|
| 1 | ~166k tokens, 24-turn limit | No verdict. Isolated from the artifact worktree by a guard (the seat's own sequencing error — it entered a second worktree *after* spawning the reviewer, which retroactively isolated the running child). Last words: "Heredocs are blocked by the worktree guard". |
| 2 | 150k tokens, 29 tool calls, 11 min | No verdict, with the tooling solved and handed over pre-tested. Produced three sentences, all of them "now I'll read X". |
| 3 | 65k tokens, **0 tool calls**, 3.7 min | Complete rulings on every question asked, three seat severities upgraded, two defects the seat had missed. |

The diagnosis (R-MIN-33e) is that a commission naming an artifact by path is a
**discovery** task with a review attached, and the turn budget is spent in the order the
work is done — so judgment is always the half that gets cut. Under the change-tactic
invariant the answer was not a third identical spawn. The **seat** ran the adversarial
battery itself against the live module, then delegated only the scoping and severity
judgment with the code excerpt, the measured outputs and numbered candidates **inline**.
That is also the half that genuinely needs independence, because the finder was going to
be the repairer.

The reviewer was `MODE: READ_ONLY` and ran nothing; every ruling rests on the inline code,
the seat's measured probe outputs, and the frozen domain law.

## What round 3 got right

The letter-gaming class that sank rounds 1 and 2 is dead, verified behaviourally rather
than by assertion. Leg identity (`metric`/`basis`/`source_label`) comes from the domain
yaml; only `value` comes from the packet; polarity is computed from the numbers and
**flips correctly when the values are reversed**, so no per-pair lookup table is hiding in
it. String legs, bool legs, range-shaped legs, equal legs, unknown pair names and a usable
case with no packet all withhold with `omitted:expectations`. Round 2's synthesis of every
leg from the string `"quarter"` cannot recur.

## Findings and their disposition

| # | Finding | Severity | Disposition |
|---|---|---|---|
| S1 | Two packets naming the same `pair` published two rows identical in identity and differing only in value, `limitations: []` — the same metric asserted as both 1700 and 9999 with nothing on the wire able to disambiguate. | BLOCKER | **FIXED.** Every row for a duplicated pair is withheld, scoped to that pair (R-MIN-33a). |
| S2 | `is_range`/`is_consensus` hardcoded `False`, so a source-declared range shipped as a point estimate — beside `comparison_kind: earlier_point_estimate_vs_later_actual`. The schema pins both `const: false`, so the truth is unrepresentable. | BLOCKER (auditor upgraded from the seat's MAJOR) | **FIXED.** The flags are now read on the packet and on both legs; a truthy declaration refuses the row (R-MIN-33b). |
| S3-unit | `1700 Mlbs` vs `1680 kt` → `below_estimate`. 1680 kt ≈ 3,700 Mlbs, so the polarity was arithmetically **inverted**, not merely unverified. | BLOCKER (upgraded) | **FIXED** by cross-leg equality. Conversion is the producer task's. |
| S3-perimeter | `consolidated` estimate vs `proportionate` actual → `below_estimate`, and the proportionate figure was *labelled* `consolidated_copper_sales` from the domain yaml. Two falsehoods, one of them false even to a reader who ignores the comparison. | BLOCKER (upgraded) | **FIXED** by cross-leg equality. |
| S3-period | `Q1 2026` estimate vs `Q4 2025` actual → `below_estimate`, while the row asserted a temporal relation the input contradicts. | MAJOR (auditor declined BLOCKER: the exact predicate needs a domain ruling, since FY guidance against a quarterly actual is legitimate) | **FIXED** by equality, which is the right M1 predicate (both legs are `period_kind: quarter`). A real comparator is the producer task's. |
| S3-basis | The packet's declared `basis` is discarded and replaced by the domain label. | Auditor ruled: compare cross-leg like unit/perimeter. | **SEAT DEPARTED, on evidence.** The domain yaml gives the two legs *different* bases by design (`fictional point estimate` vs `fictional reported measure`), so cross-leg equality would forbid the only comparison this slice exists to make. `basis` stays a presence token; the domain owns the published label. Pinned as NOT-A-DEFECT in `test_probe_r3_basis_may_differ_between_the_two_legs_by_design` so it cannot be silently reversed. Rejecting a producer's divergent basis at intake is the producer task's work. |
| Extra | `_value_is_numeric` admitted `nan`/`inf`; NaN also slips the equality withhold (`nan == nan` is False) and drives the polarity ternary's else branch, publishing `below_estimate` with `nan` as an economic value — including for `nan` vs `nan`. | MAJOR | **FIXED.** Hoisted to module scope and now requires `math.isfinite` (R-MIN-33c). **Auditor's find, not the seat's.** |
| F2 | The seat's own R-MIN-32 probe amendment pins one value pair per pair name with one expected polarity, satisfiable by `{"sales": "below_estimate", ...}[pair]` without ever comparing numbers — round-2's defect class surviving the round-3 oracle. | MAJOR (oracle) | **FIXED.** Reversed cases per pair make the expected polarity flip (R-MIN-33d). No current exploitation: the live module already computes correctly. **Auditor's find, in the seat's own work.** |
| F1 | The same amendment cannot distinguish a `False` that was read from a `False` that is constant. | MAJOR (oracle) | **FIXED.** Paired assertions: an absent declaration composes, a present one refuses. |
| Independence | Did amending the frozen R1 probe weaken the oracle? | — | **STRENGTHENED.** The original demanded two rows from a fixture holding one reported measure, so it was unsatisfiable except by fabricating both legs — it did not merely permit round 2's letter-gaming, it *mandated* it. The amendment kept every original assertion and added value, type, inequality and polarity pins. |
| Minor | `omitted:expectations` dedupe; a packet both non-numeric and missing required fields loses its `definition_unqualified:<f>` diagnostics. | MINOR | Dedupe already present (`if ... not in limitations`) — the auditor could not see it. The diagnostic-ordering note is accepted and not fixed: the withhold is the truthful outcome either way. |

The auditor also **denied the T04b deferral argument** for every candidate, on the
module's own evidence: it already validates packet content (`_value_is_numeric`, the
equality withhold, `missing_fields`) and had simply skipped the four fields carrying the
domain law. Selective validation is not a scope boundary.

## Evidence at the repaired head

- Probes committed **RED before the repair** (9 of 13 failing at that commit), per
  freeze-then-repair: `tests/test_mining_composition_probes_r3.py`.
- Seven mining suites: **173 passed / 0 failed**. The 160 that passed before the change
  still pass, so no frozen oracle moved.
- Frozen-oracle integrity: the only post-freeze commit touching
  `test_mining_composition_probes.py`, `_probes_r2.py`, the truth table or the fixtures is
  the declared R-MIN-32 amendment, which this review ruled strengthening.
- `pyflakes` clean on both changed files.
- `check_contract_delta.py --base origin/main`: **0 introduced, 0 inherited**.
- `tests/test_ci_pack.py` curated/exclusive/mining assertions: 7 passed.
- The new suite is wired into the `mining-economic-dossier` gate block's `paths:` and
  `run:` line.
