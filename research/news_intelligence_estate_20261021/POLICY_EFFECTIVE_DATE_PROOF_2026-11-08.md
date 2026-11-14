# Policy effective-date proof — 2026-11-08

## Scope and source

Parent assignment: [News Intelligence end-to-end completion, Macro #10244](https://github.com/mastermindx-market-intelligence/macro/pull/10244#issuecomment-6718847852).

Product and proof base: `8251e41bcb67cfd045b67501c47cf27fe06b1af2`.
Protected law pin: Mastermind `1981aea5122943ce59d7ebe9706ddf5a658b377d`.

This corrects the accepted V4 P1 defect in the existing Federal Register collector and policy calendar. The collector now requests and stores `effective_on`. The calendar selects the earliest valid future-or-today effective date from its existing `final_rule` population, independently of comment deadlines. The existing rationale chip includes the effective date and preserves both labels when deadlines fall on the same day.

## Discriminating evidence

With a fixed reference date of **2026-11-02**, the synthetic final rule's source values are:

| Fact | Source date | Calendar interval |
|---|---|---|
| Comment deadline | 2026-11-20 | 18 days |
| Rule effective date | 2026-12-15 | 43 days |

The regression exercises the actual mocked HTTP request, collector `fetch()`, Parquet write/read, calendar and chip. It proves both source fields survive, retain separate meanings and produce the two labels. It is synthetic offline evidence, not a live Federal Register response or authenticated production proof.

- **22 new regression cases fail against the original product source.**
- **All 64 tests** in `tests/test_federal_register.py` and `tests/test_policy_calendar.py` pass on the candidate (**1.71s**, local Python 3.12).
- V4 `p1_stage_states()` ran twice with both writer lanes unset. The identical output is **PROVEN**, with effective date `2026-12-15`, `proxy=False`, and visible countdown **43d**.
- The P1 predicate now also requires the displayed countdown to match the effective date. Its expected file changes only P1 and the V4 tally to **1 PROVEN / 3 PARTIAL / 1 ABSENT / 0 HUMAN_GATE**. The remaining V4 properties were not replayed locally; the existing hosted V91 job owns their full replay.
- The two existing unit modules previously belonged to the unrun backlog. The existing `news-v91-vertical-proofs` job now names both in its path scope and pytest command, and only their two grandfather-list entries are removed. No second test workflow is introduced.
- The incumbent CI weight calculation changes this logical job from **4 to 8**. No global packing ceiling is relaxed.

Two existing tests needed explicit isolation when enrolled: the ledger assertion enables the nightly lane only after redirecting its data directory; the cascade-stage test redirects its data directory and clears writer lanes.

## Review and limits

The active principal self-reviewed the product diff. A distinct native reasoning child reviewed the same local source, tests and P1 change and found no blocking correctness defect. That child did not run tests, mutate source, or submit a GitHub approval.

Historical tape rows remain first-write-wins. A newly fetched duplicate does not backfill an old missing effective date or rewrite `_first_seen`, `significant`, title or an existing effective date. Missing, malformed, wrong-type, compact, week-form and timestamp values remain unknown. The new date does not promote a proposal or interim-final row into `final_rule`.

Stage taxonomy, weights, latency, inflow, comment-only upcoming events and the nightly ledger gate are unchanged. This is a factual date correction; it changes no predictive score or trading authority.

Generated production artifacts require the normal collector/build path to refresh. No release, production output refresh, live effective-date coverage, authenticated consumer proof or complete V4 journey is claimed by this receipt.


## Exact-head CI scope repair

Run `42468185819` at source head `64834d49c0c9c522adc4142de09d84e5f06e748a` had two distinct failures. The planner could not download Python (HTTP 504 before execution). Its contract-delta job also found three introduced packing violations in tested merge `e0b4f97a8e26f73d9a7ac22db5d8a62dcf3428e3` against base `904aa7effb7abc29e6b3c7bbba349b5a27c5e997`. The new test enrollment caused the News job to join ordinary free-content and plan-book probes through a dynamic-import fallback, adding eight weight units and, for plan-book, one extra job. Retrying that unchanged head would not repair the deterministic failure.

The repair curates the existing job without removing a suite or raising a budget. The original pre-enrollment job is read from parent `8251e41bcb67cfd045b67501c47cf27fe06b1af2`, manifest blob `1d084e2a811d8f1d4182116a20f66fed803b4724`. Every original explicit/inferred path and every original fallback pattern, including the research subprocess coverage, is retained. The new scope includes the complete 47-file source/read closure of the three enrolled suites, the exact optional `engine.healthcare_molecule_gap` and `engine.healthcare_observation_split` targets hidden behind constant string concatenation, their closure, and all tracked ancestor initializers. Artifact-only parquet fallbacks are retained. Only the newly introduced unexplained all-code fallback is removed.

The source-head analysis uses the actual production scope functions with an exact tracked-path inventory: 147,337 paths, payload SHA-256 `f8b427731418232a5cb07521fad24cc9c5c1b7986ca023a8376f60e243316481`. Its Git commit and 3,865 tree objects were reconstructed from authorized immutable object reads and individually hash-verified; the faithful index matches `git ls-tree`. The official `write_tracked_path_inventory`/`planner_tracked_path_inventory` checks pass. Required Python source bytes were materialized and Git-blob-verified; omitted files were never replaced with placeholders.

The shared `curated_exclusive_closure_findings` function reports no missing dependency for the candidate job. All tracked ancestor initializer checks pass. Its 84 declared patterns preserve the complete old scope, select all added dependencies, and restore both free-content and plan-book selection to their pre-enrollment false result. Job weight stays eight. Full manifest exclusivity matches `CURATED_EXCLUSIVE` for all 193 curated jobs. The registration-set edit adds only this job; packing ceilings and other limits are unchanged.

The machine-readable receipt is `POLICY_CI_SCOPE_PROOF_2026-11-08.json`. This is bounded job-selection evidence at the source head, not a claim to have reproduced the failed merge tree's whole-repository packing census or reexecuted all seven journeys. The normal exact-head CI contract gate and full CI remain the release authority. Product/test bytes for the 64 passing policy regressions are unchanged by this CI-only repair.
