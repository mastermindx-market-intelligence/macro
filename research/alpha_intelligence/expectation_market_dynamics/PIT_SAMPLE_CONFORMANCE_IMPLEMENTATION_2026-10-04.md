# Commission 2 PIT Sample Conformance — bounded implementation receipt

**Operation:** `information-to-price-pit-conformance-20261004-sol-001`  
**Base:** `8cf8f73296e2b5465048606016a0c49a8886b8aa`  
**Authority:** research diagnostic only  
**Production/model/portfolio authority:** none

## Purpose

This is the smallest implementation slice behind Commission 2 Phase 2. It turns the vendor-neutral point-in-time rules into executable deterministic diagnostics before any vendor sample is obtained.

It deliberately does not fetch a provider, select a vendor, create a second estimates warehouse, grant source rights from row metadata, infer missing clocks, normalize into a production expectation baseline, inspect EVAL outcomes, or affect Prophet/portfolio/ranking/sizing/trading.

The incumbent revisions/K3E system remains the source owner.

## Implemented surface

`pit_sample_conformance.py` reads an explicit local JSON list, or an object containing `observations`, and returns a canonical diagnostic receipt.

The row contract is the Commission 2 `expectation_observation` field set. Unknown source/vendor/snapshot clocks remain explicit `null`; their absence is never silently replaced by a later clock.

The validator enforces:

1. required field presence and typed missingness;
2. offset-aware clocks;
3. `known_at <= ingested_at` and no source/vendor/snapshot clock later than `known_at`;
4. immutable ISO fiscal-period identity;
5. finite values and non-boolean numerics;
6. append/supersede correction generations;
7. no correction forks or cycles;
8. immutable correction grain, including contributor/broker/analyst identity;
9. replay at an explicit cutoff using only `known_at <= cutoff`;
10. fiscal roll, basis change, composition-only change, withdrawal/staleness and true value revision as separate transition classes;
11. deterministic canonical input/replay/receipt digests.

## Commission 2 invariant mapping

| Rule | Harness state | Meaning |
|---|---|---|
| T1 knowledge cutoff | PASS/FAIL | Future-known rows are excluded from replay. |
| T2 no retroactive correction | PASS/FAIL | A later generation cannot rewrite the earlier cutoff view. |
| T3 no timestamp invention | PARTIAL | Explicit nulls are preserved; vendor/source clock semantics still require owner evidence. |
| T4 fiscal identity | structural PASS/FAIL | Period end is explicit ISO date and fiscal rolls are not revisions. |
| T5 composition decomposition | structural PASS | Contributor-only changes are separate from value revisions. |
| T6 rights | always PARTIAL | A `rights_class` string is evidence only; it never grants rights. |
| T7 intraday honesty | UNKNOWN | Vendor timestamp granularity/market availability requires sample documentation. |
| T8 receipt separation | PASS/FAIL | Distinct clock fields must be present; they are not aliases. |
| T9 corporate-action lineage | PASS only with explicit receipt lineage, otherwise UNKNOWN | Per-share action treatment is never guessed. |
| T10 reproducibility | PASS | Canonical deterministic receipt/replay digests. |

`structural_pass` means only that the supplied sample is internally conformant to observable checks. It does not mean the sample is licensed, vendor-complete, historically correct, production-ready, or predictive.

Every receipt hard-codes `rights_granted=false`, `model_use_granted=false`, `redistribution_granted=false`, `financial_influence=false`, `rights_ready=false`, and `production_ready=false`.

## Verification

Focused suite:

`python3 -m pytest --noconftest research/alpha_intelligence/expectation_market_dynamics/test_pit_sample_conformance.py -q`

Result: **24 passed**. Four inherited pytest cleanup warnings reference unrelated old Chromium temporary directories and do not belong to this change.

The first real run correctly failed one malformed synthetic fixture whose `known_at` had been moved later than its unchanged `ingested_at`. The fixture was repaired; the production check was not weakened.

Additional validation:

- `python3 -m py_compile` on implementation and tests — PASS.
- `git diff --check` — PASS.
- Two-cutoff synthetic CLI replay:
  - cutoff `2025-01-10T16:00:00Z` -> visible `obs-1`, replay digest `092e47627ce40abfe428aa9058c85c5b66015f093bc36398e4584009843b4181`;
  - cutoff `2025-01-10T18:00:00Z` -> visible corrected `obs-2`, replay digest `0e4bd0872de483066a20ff55745df52112aeda20aefa61202f011e616db448ef`;
  - both structural PASS; rights/production remain false.

Adversarial cases include future leakage, malformed fiscal period, boolean fiscal year/value, source clock after `known_at`, correction generation gap, immutable-grain mutation, contributor identity mutation, correction fork, correction cycle, missing required clocks, naive timestamps, rights-string self-assertion, and corporate-action evidence absence.

## CI ownership gate

Current code-gate scope validation reports 172 code jobs, 110 unscoped always-on jobs selected, and **both new paths unowned**. The new paths therefore do not widen selection.

The natural repair is to enroll the harness under an existing code-gated research owner in `.github/ci/legacy-jobs.yml`. That shared manifest is currently part of the fenced SRC-A1 PR #8312 carrier, whose common object-store tree effect remains unresolved. This operation therefore does not modify the manifest.

Publication may proceed only as a held draft carrier until legitimate CI ownership is available. Always-on jobs are not execution proof of this suite unless a named hosted step actually runs it.

## Next evidence

Once CI-manifest custody is clear:

1. add the two paths and focused command to the existing appropriate code-gated research owner;
2. require the planner to report zero unowned paths;
3. require named hosted execution of the 24-case suite on the exact merge candidate;
4. obtain independent semantic review of the immutable implementation head;
5. require a real rights-permitted vendor sample before any vendor-specific PASS;
6. preserve research-only authority unless separate accepted evidence promotes it.
