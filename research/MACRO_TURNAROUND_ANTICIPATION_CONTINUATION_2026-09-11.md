# Macro Turnaround Anticipation — Source and Replay Continuation

**Updated:** 2026-09-16
**Operation:** `anticipate-macro-turnarounds-continuation-20260909-sol-001`
**Authority:** current Chairman continuation direction; Sol direct ownership
**Protected Skillpack:** `mastermindx-market-intelligence/Mastermind@bf843961c0e1b5bd45fa481f0138c71f2a87d4e2`
**Draft PR:** `mastermindx-market-intelligence/macro#7165`
**Latest accepted independent-review head:** `64e76b8471989190a123dd837ccc34d1e415a95d`
**Latest accepted independent-review tree:** `72f9b7a00c73ee1252e630168f1ee114089b8172`
**Semantic repair commit:** `527e619c009ddf2034382f9704c92e5217ce1890`
**Semantic repair tree:** `48db807c089efeb7b6496a9f03b2cb0943700441`
**Exact integrated source head:** `bd8f56c66d7d1ca2e124285874dfac0af9802a37`
**Exact integrated source tree:** `91b4deb832b3d412689a2ada81c512d20a45e4c4`
**Latest protected `main` inspected:** `90009cc588115a3f5b5e511844ba95e9ddbb4e2b`
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


## Superseding exact-head release checkpoint — 2026-09-16

This section supersedes the earlier release coordinates while preserving their
historical evidence. It does not strengthen the capability claim.

### Immutable identities and review classification

- Accepted independent rereview: head `64e76b8471989190a123dd837ccc34d1e415a95d`,
  tree `72f9b7a00c73ee1252e630168f1ee114089b8172`, verdict `PASS`,
  with no merge, Ready, deployment, production, or authority grant.
- Exact integrated source head before this records-only closeout:
  `bd8f56c66d7d1ca2e124285874dfac0af9802a37`, tree
  `91b4deb832b3d412689a2ada81c512d20a45e4c4`.
- The descendant adds the reviewer-requested nested/traversal fence tests, the
  replay-root symlink fence repair, family-cap lower-bound tests, and one bounded
  latest-base CI curation repair. Candidate-owned blobs therefore changed after
  the accepted rereview: classification is **FULL_REREVIEW_REQUIRED**, not review
  reuse.
- At checkpoint capture, Draft PR `#7165` pointed to
  `64e76b8471989190a123dd837ccc34d1e415a95d`; the publication step must verify
  the new immutable remote head. No replacement PR or carrier exists.

### Exact integrated proof

Evidence root:
`/Volumes/Mastermind/agent-evidence/macro-turnaround-release-20260916-sol/20260916T194011Z-exact-head-release-bd8f56c`

- Five focused engine/replay/CLI suites: **259 passed**.
- Exact executable import-pin module: **11 passed**.
- CI ownership, declared closure, exclusive curation, fallback tier, and fanout
  ceilings: **5 passed**; no ceiling was raised.
- Python compile, AST compile, Git diff check: PASS.
- Agent OS validation: **1,116 records, zero errors**; warnings are inherited.
- Unrun census: exit 0; no new strictly dark Macro Turnaround suite.
- Semantic CI plan: all **142 jobs** placed into 12 packs; plan SHA-256
  `8002b139473e413e44dd0ada191a9be5c4e1682892fae27aa3b08c0d26a6e9ce`.
- Expanded mutation campaign: **35/35 killed**, zero survivors, zero invalid
  executions, bound to exact head `bd8f56c66d7d1ca2e124285874dfac0af9802a37`.

### Current canonical replay proof

Protected `main` was frozen at `90009cc588115a3f5b5e511844ba95e9ddbb4e2b`.
Movement after the integrated parent changed only the canonical release-target
manifest within the declared material set; engine, replay, CI, tests, and PPIFIS
bytes remained unchanged. The replay was therefore regenerated rather than
calling the old manifest-bound request current.

- Manifest blob: `2524e4fcdf350bdf4a061a9f009a09ca02bd2274`.
- Manifest SHA-256:
  `6d64a7fb739c33bc5e7248ba72645905876160e740dfe8a361fd76c9e8be815d`.
- PPIFIS blob: `42aab3b388c61e5c0e960a65cd883892870c13c1`.
- PPIFIS SHA-256:
  `616d4930b5c071e13b78a59aa7660577a7e9670af5b54fe3c7d424e0554e4592`.
- Native Arrow/Pandas input: **19,828 rows**, **202 economic periods**,
  **157 release cutoffs**.
- Output SHA-256:
  `d5542e10f3473844d0fa34a7e4223ae110d78e1982a36d041b0608eee28a945e`.
- Replay hash:
  `21d0bd36936b809973d63ac8c48585231baa92959e39c21dfef55c0e54a5ce63`.
- Existing normalizer and strict-adapter semantics match on columns, rows, series,
  period/release/end dates, values, and output-type markers.
- An identical same-path rerun preserved bytes, digest, inode, and mtime. A
  156-cutoff conflicting replacement exited 2 and left the artifact unchanged.
- Forecast accuracy and historical production availability remain explicitly
  false; calibrated forecast, ranking, gating, and trade authority remain false.

### Exact remaining release sequence

1. Commit these records as a docs-only descendant of the exact integrated source.
2. Refresh the open-PR collision census, then push this same branch without force
   and verify the remote ref and Draft PR head exactly.
3. Obtain a fresh independent review of the new immutable head. Do not reuse the
   `64e76b8` PASS across changed owned blobs.
4. Run every binding hosted check to conclusion for that same head. Queued,
   canceled, or old-head checks are not acceptance.
5. Refresh protected Source Continuity. Any typed refusal remains a release block.
6. Mark Ready or merge only after independent PASS, exact-head hosted green,
   current-base material compatibility, no source collision, and accepted
   continuity. Post-merge readback still yields only
   `BUILT_NOT_PROVEN / RESEARCH_ONLY / PRODUCTION_INERT`.

## Current-main qualification checkpoint — 2026-09-17

This checkpoint supersedes the release coordinates above without changing the
capability or authority classification. The source remains
`BUILT_NOT_PROVEN / RESEARCH_ONLY / PRODUCTION_INERT`.

### Exact integration identity

- Candidate parent: `71dec51a54b96bd3cebe333069f59ed8b3b9c13b`.
- Protected `main` parent: `12b655150582d9be39bfd2779b33338d154c565f`.
- Integrated source head: `ca93ecd56b5c763e5557d36231fa502fc5fd2571`.
- Integrated tree: `bb9be83e4331a17defb3c7d9a3bc69657aa844b6`.
- A detached synthetic merge was first qualified at commit
  `35817c3f3753eb4af267aeef346a8d0c700d712d`; the real merge produced the
  identical tree byte-for-byte. Protected `main` remained at the pinned parent
  through the final bounded fetch/reconciliation.

### CI fanout root cause and repair ownership

The pre-integration candidate reproduced the ratchet RED exactly:
`templates/index.html` selected **133 jobs** against the unchanged ceiling of
**132**. Four neighboring declaration, import-closure, fallback-tier, and Macro
owner contracts passed. The excess job was not a Macro Turnaround scope defect:
Research Vault source-lineage curation had already merged independently to
protected `main` as `ebaa524756d7` / PR `#7207`, so the duplicate branch-local
curation was correctly reverted rather than carried twice.

On the exact synthetic/current-main tree, all five CI contracts passed, including
the same 132-job ceiling. No fanout ceiling, weight ceiling, pack ceiling, test
coverage, or fallback rule was weakened.

### Post-merge bounded proof

Evidence root:
`/Volumes/Mastermind/agent-evidence/macro-turnaround-release-20260916-sol/20260917T023957Z-postmerge-ca93ecd5`

- Five focused Macro Turnaround suites: **259 passed**.
- Canonical entry-script import-pin module: **11 passed**.
- CI declaration, import-closure, exclusive curation, fallback-tier, fanout, and
  dedicated Macro owner contracts: **5 passed**.
- Python compile and `git diff --check`: PASS.
- Correct workflow-shaped semantic planner: **142/142 jobs** placed into all
  **12/12 packs**, zero omitted; plan SHA-256
  `e1628b9960c3cde272f851b84962f7913b96d2f7a3bf9b41f9470e54a6a6eabe`.
  Full-suite selection is expected because this PR changes the global legacy-job
  manifest. An earlier unsupported local `--all --dry-run` invocation exited 2
  before planning because `--workflow` is mandatory; it was an invocation error,
  not a repository verdict.
- Whole-tree unrun gate: **2,806 suites**, **910 unrun**, **0 strictly dark**,
  exit 0. Two stale baseline warnings are inherited cleanup, not new darkness.
- Agent OS validation: **1,118 records**, **0 errors**, **98 inherited warnings**.

### Replay and correction identity remains current

Current protected `main`, the exact merge, and the latest immutable replay proof
share the same canonical release-target material:

- manifest blob `2524e4fcdf350bdf4a061a9f009a09ca02bd2274`;
- manifest SHA-256
  `6d64a7fb739c33bc5e7248ba72645905876160e740dfe8a361fd76c9e8be815d`;
- PPIFIS blob `42aab3b388c61e5c0e960a65cd883892870c13c1`;
- PPIFIS SHA-256
  `616d4930b5c071e13b78a59aa7660577a7e9670af5b54fe3c7d424e0554e4592`.

Therefore the prior exact native replay, immutable rerun/conflict proof, and
35/35 mutation campaign remain materially applicable; no revised source data is
being granted an old receipt. This still proves mechanics only, not forecast
accuracy, historical production availability, ranking, sizing, gating,
profitability, alerting, or trading authority.

### Collision and release state

A fully paginated diagnostic census reconciled **274/274 open PRs**, including
all 16 file lists requiring expansion. Excluding this PR, 92 PRs overlap only on
shared CI integration surfaces: `.github/ci/legacy-jobs.yml` (92) and
`tests/test_ci_pack.py` (5). There are **zero exact engine, replay, CLI, research,
or focused-test collisions**. This diagnostic does not replace the protected
Source Continuity receipt.

The prior independent PASS at `64e76b847198...` cannot be reused: the path-fence
repair and tests changed owned semantic blobs after that review. The final
published descendant therefore remains **FULL_REREVIEW_REQUIRED**. Hosted CI and
protected Source Continuity must also bind the same remote head; queued,
canceled, old-head, manually enumerated, or local-only evidence is not release
acceptance.

### Exact remaining release sequence

1. Commit this records-only checkpoint as a normal descendant of the exact
   integrated source, then push the existing branch once without force and verify
   the remote ref and Draft PR head byte-for-byte.
2. Run protected Source Continuity on that published head. Preserve any typed
   refusal as a release block; do not substitute the diagnostic census.
3. Obtain fresh independent adversarial review of the exact published head.
4. Require every binding hosted check to finish green on that same head.
5. Only after review PASS, hosted exact-head green, accepted continuity, and a
   final current-base compatibility check may Sol consider Ready/merge. Even a
   merge would leave the feature research-only and production-inert.

Do not redo the completed engine/replay implementation, 35-mutation campaign, or
native replay unless a material source, configuration, manifest, PPIFIS, or
owned-blob invalidator appears.
