---
key: A-SYNTHETIC-FIXTURES-NEVER-REACHED-THE-BRANCH-THE-LIVE-FEED-TAKES
claim: >
  A consumer surface can be exhaustively probed, red-teamed six rounds, ACCEPTed at an exact
  head, and still render a false sentence the first time it meets the real feed — because
  every fixture author picks the SAME representative combination and nobody runs the
  committed production artifact through the code. Measured 2026-09-26 on macro PR #7930
  (Healthcare D1). `engine.fda_scarcity.summarize_supply` selects MIXED_REPORTED for
  `current and (resolved or discontinued)`, but the label template and the rationale both
  hard-coded "resolved" as the second component:
  `"FDA: mixed — current {current} / resolved {resolved}"` and "The FDA reports both current
  and resolved shortages." Every MIXED test across the eight gated suites — 40 seat-frozen
  probes plus test_foresight_cascade.py and test_fda_shortages_generation.py — built its
  mixture from current + resolved, so the `discontinued` half of that `or` was never
  exercised. The live openFDA feed at origin/main 5e921b1c was current=9, resolved=0,
  discontinued=5, which renders
  "FDA: mixed — current 9 / resolved 0" / title "The FDA reports both current and resolved
  shortages." — asserting records that do not exist, printing "resolved 0" beside the word
  "mixed", and hiding five formulation discontinuations, on a program whose own semantics law
  is "discontinuation is not resolution". The code was never right here; it was only ever
  green.
falsifier: >
  Reproducible without a network and without a full checkout, from any sparse macro worktree:
  `git show origin/main:data/fda/shortages.parquet > /tmp/s.parquet`, then in python
  `from collectors import fda_shortages as C; C._shortages_path = lambda: Path("/tmp/s.parquet")`
  (no sidecar beside it = the legacy state main is in right after a D1 merge), then
  `from engine import fda_scarcity as F; F.compute_fda_scarcity()["glp1_obesity"]["summary"]`
  and read `label` / `label_zh` / `_chip_rationale(...)`. At PR #7930 head 871b6d36 that
  prints the false sentence above; at 5f7ae25c it prints
  "FDA: mixed — current 9 / discontinued 5". Disproved if a synthetic-fixture suite ever
  covers a live composition it was not explicitly pointed at.
so_what: >
  Two reusable things. (1) TECHNIQUE: for any surface driven by a committed data artifact, you
  can render the REAL production state locally in about ten lines — extract the artifact from
  `git show origin/main:<path>` (works in a sparse worktree, where the file is not on disk),
  monkeypatch the collector's path accessor, and call the engine entry point. Do this BEFORE
  merging a consumer change, not after: it is cheaper than a CI round and it is the only check
  that exercises the branch the live data actually takes. Reproduce the post-merge state
  specifically — for a sidecar-backed collector that means the artifact WITHOUT its sidecar,
  because the first render after the merge runs before the nightly writes one. (2) REVIEW RULE:
  when a status is selected by a disjunction (`A and (B or C)`), the copy for that status must
  be checked against EVERY disjunct, and a fixture census is the way to find the gap — grep the
  suites for the status name and look at which combination each fixture builds. Identical
  fixtures across six review rounds are evidence of a shared blind spot, not of coverage. This
  is the Adjudication coverage gate ("run the rule against the motivating live exemplars")
  applied to a data-driven UI surface, and it is the check that six adversarial Opus rounds and
  an exact-head ACCEPT all missed.
kind: landmine
verified_at: 2026-09-26
verified_by: >
  direct observation — the real feed rendered through the engine at both heads (commands in
  `falsifier`); new seat-frozen probe tests/test_fda_supply_probes_mixed.py is red 3/5 at
  871b6d36 and green 5/5 at 5f7ae25c; the job's suites go 127 -> 132 passed; seat ruling
  R-D1-MERGE-03 in research/healthcare/hc_program/reviews/SEAT_RULINGS_D1_MERGE_2026-09-26.md
scope:
  - mastermindx-market-intelligence/macro
  - engine/fda_scarcity.py
  - collectors/fda_shortages.py
  - tests/**
confidence: verified
---
