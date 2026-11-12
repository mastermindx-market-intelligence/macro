# Data-health dependency declaration repair

Tracking issue: [#5979](https://github.com/mastermindx-market-intelligence/macro/issues/5979). Original failure: [run 43095023859](https://github.com/mastermindx-market-intelligence/macro/actions/runs/43095023859).

Five existing DATA owners omit dependencies imported by their own tests. This change appends only those missing packages to the five existing installers. Product source, tests, selectors, data and CI budgets remain unchanged.

| Owner | Dependency appended | Existing cases passed | Planning weight before and after |
|---|---|---:|---:|
| `paywall-contracts` | `jsonschema==4.26.0` | 1 | 20 |
| `neural-web` | `jsonschema==4.26.0` | 1 | 37 |
| `capital-structure-intelligence` | `plotly` | 52 | 247 |
| `unrun-market-plumbing` | `html5lib` | 1 | 114 |
| `unrun-picks-boards` | `html5lib` | 22 | 245 |

## Validation

The 77 exact cases from the original failure ran unchanged in five independent normal pytest sessions: **77 passed, zero failures, errors or skips**. The actual health route, frozen neural benchmark, builder import paths and HTML5 parser/render tests ran with the original conftest and default data/module guards. No test was replaced by a helper-only invocation. Network guards recorded zero attempts. The isolated source had a real local Git index for the normal data/site write guard; the driver verified every staged input hash and clean data/site status after each session.

The five complete owners retain their prior planning weights; all other 396 complete owners are identical. This patch changes five installer lines only.

Native proof source: `0b26ae364676069354a53d1d84be21ee94cd78a0`. Publication base: `27bdebdbdc973398c0caa509498c568816871bf5`. Every selected test, actual first-party top-level import closure and explicit fixture remains the same blob at the publication base. The optional filing cache retains its verified absence.

## Limits and exclusions

This qualifies the selected missing-package failures using native Python 3.14.7 with the target packages already installed; it does not claim a hosted Python 3.12 clean install, a successful full DATA workflow, or repair of the 23 other failures in these five owners. The auxiliary dynamic read/import audit had a /tmp versus /private/tmp path-normalization defect and its empty path arrays are not used as proof. Independent input hashes and the real conftest/data guard establish the recorded immutability result.

The existing cycle consistency writer, all other live owners, the explicit template/site synchronization refusal, and original uncertain effects remain fenced. No run was replayed, cancelled or dispatched. Ordinary PR CI and the installed release controller must supply their own exact-head evidence.

Full evidence: [data-health-dependencies-validation-2026-11-12.json](data-health-dependencies-validation-2026-11-12.json), SHA-256 `2b24d700ecf48860a49e72ca5ba357cba0d6e50104056b71c14a897f2087dbe5`. It includes all 77 exact node IDs, original decisive failure excerpts, the 23 excluded failures, dependency preimages, finite custody qualification, source bindings and native records.
