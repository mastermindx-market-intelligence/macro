# Macro Turnaround Anticipation — Source and Replay Continuation

**Updated:** 2026-09-15
**Operation:** `anticipate-macro-turnarounds-continuation-20260909-sol-001`
**Authority:** current Chairman continuation direction; Sol direct ownership
**Protected Skillpack:** `mastermindx-market-intelligence/Mastermind@a9e6e1667abecdff500bced40c9816c1611c3dd7`
**Draft PR:** `mastermindx-market-intelligence/macro#7165`
**Independent-review head:** `ef92df252e80618bba8fe7c42b1a8e86afaf9354`
**Independent-review tree:** `a2ce3af050309ded804a066e08de0c2d4528865f`
**Semantic repair commit:** `527e619c009ddf2034382f9704c92e5217ce1890`
**Semantic repair tree:** `48db807c089efeb7b6496a9f03b2cb0943700441`
**Latest protected `main` inspected:** `52f6ca950b55ee3a248a51c61dbe48079b3d6ac8`
**Capability state:** **BUILT_NOT_PROVEN / RESEARCH_ONLY / PRODUCTION_INERT**

## Mission and outcome boundary

Deliver a correction-safe source capability that can expose forming macro turns
before consensus without converting revised history, correlated proxies, stale
or future economic periods, malformed inputs, or uncalibrated output into false
authority. The source must reconstruct what was knowable at each historical
cutoff, preserve nulls and contradictions, and remain deterministic after source
corrections.

This wave supplies the deterministic engine, full-vintage adapter, point-in-time
replay, immutable machine artifact, and pre-merge CI owner. It does **not**
supply broad independent-family coverage, a frozen target/evaluation contract,
validated forecast skill, a production scheduler, a premium user workflow, or
ranking, sizing, gating, alert, execution, or trade authority.

## Authority precedence and canonical owners

1. Current live Chairman continuation direction.
2. The protected Skillpack commit named above.
3. Current Macro repository law, CI authority, and canonical release-target
   source/publication boundaries.
4. The exact branch, Draft PR, commits, and external proof receipts named here.

`engine/release_target_truth.py` remains the canonical full-vintage normalizer.
This wave consumes it read-only. It creates no second observation, identity,
queue, scheduler, publication, lifecycle, or authority plane.

## Reconciled carrier

- Worktree:
  `/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/anticipate-macro-turnarounds-continuation-20260909`
- Branch: `sol/anticipate-macro-turnarounds-continuation-20260909`
- Draft PR: `#7165`, still Draft/HOLD.
- The first published review head was `ef92df252e80618bba8fe7c42b1a8e86afaf9354`.
- The accepted same-carrier repair is frozen in semantic commit
  `527e619c009ddf2034382f9704c92e5217ce1890`.
- The final review head is intentionally a docs-only descendant of that semantic
  repair. A reviewer must verify that the descendant changes only this record
  and the sibling architecture record; any code/test/blob movement requires a
  fresh semantic classification.
- No replacement branch, PR, operation, queue, publication plane, or release
  carrier was created.

## Exact owned scope

1. `.github/ci/legacy-jobs.yml`
2. `engine/macro_turnaround.py`
3. `engine/macro_turnaround_replay.py`
4. `research/MACRO_TURNAROUND_ANTICIPATION_ARCHITECTURE_2026-09-09.md`
5. this continuation record
6. `scripts/build_macro_turnaround_research.py`
7. `scripts/replay_macro_turnaround.py`
8. `tests/test_ci_pack.py`
9. `tests/test_macro_turnaround_evidence_change.py`
10. `tests/test_macro_turnaround_feature_honesty.py`
11. `tests/test_macro_turnaround_replay.py`
12. `tests/test_macro_turnaround_replay_cli.py`
13. `tests/test_macro_turnaround_research.py`

`engine/release_target_truth.py`, `scripts/run_ci_pack.py`,
`scripts/ci_scope_dependencies.py`, and
`tests/test_check_script_import_pinning.py` are governing read-only dependencies.
No canonical `data/`, generated `site/`, scheduler, alert, ranker, or product
surface is modified.

## Capability delivered by the source candidate

The deterministic engine:

- separates economic period from first-known release time;
- requires both period and release availability to be at or before a historical
  daily cutoff;
- selects the latest eligible vintage for each period;
- rejects conflicting values for one period/release identity;
- measures evidence age as the greater of period age and release age;
- measures coverage through independent-family budgets rather than surviving
  indicator count;
- constrains `family_weight_cap` to `(0, 0.5]`, so one family cannot configure
  itself into complete breadth;
- preserves typed exclusions for malformed, nonfinite, stale, short-history,
  zero-scale, undefined-percentage-change, and unknown-series evidence; and
- emits research scores, quality, drivers, phase, and hysteresis behind a fixed,
  zero-argument authority boundary.

The replay and machine-consumer path:

- verifies the canonical manifest and every selected Parquet digest before
  decode;
- reuses the existing full-vintage normalizer after strict input validation;
- discloses whether the native Pandas/Arrow parser executed;
- preserves missing-source disclosure and refuses an all-missing request;
- separates active-value changes from source-vintage identity changes;
- writes through one create-only hard-link publisher;
- rejects symlink, conflicting, repository `data/`, and generated `site/`
  destinations;
- preserves byte identity, inode, and mtime on an identical rerun; and
- keeps causal, calibrated-forecast, ranking, gating, and trade authority false.

Both executable scripts use the repository's unconditional file-derived import
pin before their first repository import. They are therefore not dependent on
the caller's working directory or a hostile earlier `PYTHONPATH` package.

## Independent review and repair disposition

A read-only Opus review completed against exact head `ef92df252e80618bba8fe7c42b1a8e86afaf9354`
and returned `REQUEST_CHANGES`. Its output SHA-256 is
`9e322d2961647934872a4df72439d2039cc08aa8c77187072978ba1b74beaed6`.
The review child was then terminally stopped; it granted no merge, Ready,
deployment, production, or successor authority.

The three blocking P2 findings are closed in semantic repair commit
`527e619c009ddf2034382f9704c92e5217ce1890`:

1. **Canonical-output fence:** the build CLI now reaches the same shared
   repository `data/` / generated `site/` fence as the replay publisher.
2. **Future-period mutation gap:** explicit engine and replay tests construct a
   future economic period with an artificially early release date and prove it
   remains invisible.
3. **Defeasible family breadth:** callers can no longer set
   `family_weight_cap > 0.5`.

The P3 dispositions are:

- missing-source disclosure and the all-missing refusal are now directly tested;
- the 156/157 evidence mismatch is corrected to 157 cutoffs;
- direct engine inputs using `LEVEL`, `DIFF`, or `PCT_CHANGE` still assume
  caller-supplied regular spacing, while the canonical replay adapter enforces
  complete monthly active history; a typed frequency contract is a bounded
  follow-up, not a capability silently claimed here; and
- the replay engine still imports shared JSON/publication helpers from the build
  script; a future layering cleanup must preserve the same publisher/parser
  owners rather than creating a duplicate plane.

A fresh independent review is required because semantic blobs changed after the
first review. Review reuse is **not** claimed for the repaired head.

## Exact local verification of the semantic repair

The evidence roots are external, immutable proof directories under
`/Volumes/Mastermind/agent-evidence/macro-turnaround-release-20260915-sol/`.
They are not product publication paths.

### Source, import, and CI contracts

Evidence root:
`20260915T202620Z-review-repair-verification`

- focused engine/replay/CLI battery: **253 passed**;
- full executable import-pin module: **11 passed**;
- dedicated CI ownership, curated import closure, fallback-tier, fanout ceiling,
  and Macro owner contract: **5 passed in 207.06 seconds**;
- Python compile, AST compile, and Git diff checks: PASS.

### Expanded mutation campaign

Evidence root:
`20260915T203645Z-expanded-31-mutations-v3`

- Macro baseline: **253 passed**, zero failures/errors/skips;
- exact import-pin mutation baseline: **1 passed**;
- valid mutations: **31/31 killed**;
- survivors: **0**;
- invalid executions: **0**;
- receipt SHA-256:
  `5e27d18447a66bd340e9dc0a40f4bd028b61c062a00a0f26fbf2052d4200e5d5`.

The campaign includes all prior 23 mutations plus future-period guards in both
selectors, shared publication fencing, the family-cap upper bound,
missing-source disclosure, all-missing refusal, and both executable import pins.
Two predecessor harnesses stopped before any valid mutation: one minimal tree
omitted unrelated dependencies required by three full import-module tests, and
one receipt builder treated a pytest node ID as a path. Both are recorded as
harness-invalid/effect-none and confer no proof.

### Governance and unrun census

Evidence root:
`20260915T203242Z-governance-census`

- Agent OS: **1,116 records, zero errors, 97 inherited warnings**;
- unrun gate: exit 0;
- whole-tree pytest census: **2,781 suites**;
- strictly dark/untriggerable suites: **0**;
- 910 inherited unrun suites remain triggerable, ledger-oriented, remainder, or
  explicitly waived; this PR introduces no new dark suite.

## Real bounded replay proof after repair

Evidence root:
`20260915T203209Z-review-repair-real-replay`

The source root was reconstructed from exact Git objects at Macro commit
`22f6759fe6529b4768309332309d52a8ee20526a`:

- manifest blob: `5927e55bad598c880e604db9483bf4d6de648e18`;
- manifest SHA-256:
  `cf6bf6da11738e64f5c8c75c788c8939b706244d00bd3a4740ea25985e38f33e`;
- PPIFIS blob: `42aab3b388c61e5c0e960a65cd883892870c13c1`;
- PPIFIS SHA-256:
  `616d4930b5c071e13b78a59aa7660577a7e9670af5b54fe3c7d424e0554e4592`;
- request SHA-256:
  `e4e8586c20fbb201bbd77e180d9be99ebb9a2308349ca1ccc1ac78ea630d7ce9`.

The repaired candidate produced **157 historical assessments** from 19,828
full-vintage rows and 202 economic periods. The result is byte-for-byte identical
to the prior accepted artifact:

- bytes: `2,249,617`;
- SHA-256:
  `df541eab54683459c01b0b60e1845d3dea3e2eaaacf4cc22eee54117490ff657`;
- replay hash:
  `05c7b5ab2a8779bb25e31ace13729a1f4f1964fae782c4e32b3e0344c7ac5b81`.

An identical same-path rerun preserved byte count, digest, inode, and mtime. A
156-cutoff conflicting request exited 2 and left the 157-cutoff artifact
unchanged. Receipt SHA-256:
`8b3a15693f4fab716a2ecef2c440a2311216940149f6c3fe179fa88278f3bb14`.

This proves deterministic point-in-time mechanics on one inflation series. It
does not prove forecast accuracy, broad macro coverage, historical production
availability, profitability, or product utility.

## Hosted CI state and the repaired failure

The first published review head did **not** achieve hosted acceptance:

- its dedicated Macro Turnaround pack passed;
- hosted pack 3 failed
  `tests/test_check_script_import_pinning.py::test_unpinned_entry_scripts_only_shrink`
  because both new entry scripts used a conditional, non-strong path insertion;
- the final CI gate then failed because the pack-3 semantic fragment was absent;
- Vercel separately reported an external build-rate quota failure, not a
  repository or product-test verdict.

Semantic repair commit `527e619c009ddf2034382f9704c92e5217ce1890`
uses the canonical unconditional pin in both scripts. The exact hosted failure
is reproduced RED and repaired GREEN locally, and each pin is mutation-killed.
This does **not** substitute for hosted exact-head CI. A new push must rerun every
binding check to conclusion.

## Current protected-base compatibility

The semantic repair commit was compared with protected `main`
`52f6ca950b55ee3a248a51c61dbe48079b3d6ac8`, 106 commits after the branch merge
base `ea0283dfd192ad759c6f49a3b7b32b8ff0db4ccd`.

Only `.github/ci/legacy-jobs.yml` moved in the declared material dependency set.
Those additions affect unrelated cycle, credit, market-structure, and template
jobs. Git's conflict-free merge-tree is
`862f1be46bea40299615ed4a9e376a32133feaf2`; it preserves the exact
`macro-turnaround-research` job, its five suites, `gate: code`,
`scope: exclusive`, and its curated-owner contract.

This is integration movement, not permission to rewrite semantic source merely
to reach `behind_by=0`. The final docs-only descendant must refresh the merge
observation and hosted integration proof before acceptance.

## Source Continuity state

The earlier protected Source Continuity checkpoint returned
`REMOTE_CENSUS_INCOMPLETE` while the repository carried more than 200 open PRs.
It created no receipt and no source or GitHub effect. A manual collision scan is
useful evidence but cannot replace the protected command-backed receipt.

The new semantic head and future published docs-only head are materially new, so
a fresh checkpoint/remote-complete attempt is eligible after push. Any new typed
refusal remains a release blocker; it is not authority for a replacement branch,
PR, retry carrier, receiver transfer, Ready transition, or merge.

## Failure, null, correction, and authority behavior

- Evidence not known by the cutoff is invisible rather than backfilled.
- A future economic period remains invisible even if malformed source metadata
  gives it an early release date.
- Missing or invalid evidence stays unavailable with a typed reason.
- A missing independent family reduces coverage; correlated siblings do not
  restore it.
- Duplicate identical vintages are idempotent; conflicting same-vintage values
  fail closed.
- A fresh revision cannot make an old economic period economically fresh.
- Source corrections mint new identity; prior artifacts are never rewritten.
- Publication never falls back to overwrite, rename, symlink traversal,
  canonical data/product paths, or another output plane.
- Descriptive context and research priority are the only enabled authority
  fields. Forecast, ranking, gating, sizing, and trade authority remain false.

## Non-goals and prohibited claims

This wave does not establish a recession label, canonical turning-point target,
causal attribution, predictive skill, calibrated probability, profitable
strategy, production alerting, portfolio sizing, execution, or trade permission.
It does not prove the historical source was available in production at every
cutoff. A merge remains **BUILT_NOT_PROVEN**, not a live premium product.

## Exact continuation

1. Commit the two durable research records as the only descendant of semantic
   repair commit `527e619c009ddf2034382f9704c92e5217ce1890`.
2. Re-run final tree/diff/static identity checks and current-main merge-tree
   compatibility.
3. Push the same branch without force; verify the remote ref equals the exact
   local head and PR #7165 remains Draft.
4. Build a fresh read-only reviewer packet that includes the exact patch,
   source manifest, local proof receipts, and immutable final head/tree.
5. Obtain independent exact-head review. All blockers must close; semantic
   change requires full rereview rather than reuse of the old result.
6. Run every binding hosted check to conclusion. Local tests, a plan, queued
   packs, or green CI on the old head are not acceptance.
7. Refresh Source Continuity against the exact published head and current base.
8. Mark Ready or merge only after independent PASS, binding exact-head hosted
   green, current-base compatibility, no unresolved blocker/thread, and an
   accepted source-continuity result.
9. After merge, read back the exact source from current `origin/main`. The merge
   still establishes only `BUILT_NOT_PROVEN / RESEARCH_ONLY / PRODUCTION_INERT`.

## Stop condition

Stop modification on an owned-path writer collision, ambiguous source/GitHub
effect, material dependency movement without compatibility proof, surviving or
invalid mutation, changed real-replay bytes under unchanged inputs, independent
review blocker, Source Continuity refusal, or binding hosted red. Do not create a
replacement carrier, raise CI ceilings, rewrite history, auto-fail over an
uncertain effect, or promote research scores while any gate remains open.
