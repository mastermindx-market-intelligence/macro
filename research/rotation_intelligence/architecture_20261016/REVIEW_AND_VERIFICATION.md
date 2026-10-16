# Review and verification record

Date: 2026-10-16. Scope: PR #9507 architecture/research package, not production implementation or investment qualification. This record distinguishes performed checks from proposed later tests.

## 1. Original assessment publication

The uploaded ASSESSMENT.md at commit `62a35f7376630c5bb21f048136c8ed49846ae11c` was read back from GitHub and matched the supplied artifact exactly: 44,909 UTF-8 bytes; SHA-256 `4ba6241675c3f3528706f7c859019dd8e6f2ce390bd31199e7a4254bf1e26c4c`. The original assessment was not rewritten to manufacture a new historical conclusion.

Native GitHub owns the new branch publication. The separate local managed-workspace acquisition returned `NOT_APPLIED / REPOSITORY_SOURCE_UNAVAILABLE`; a bounded read-only diagnostic isolated an unavailable commit observation. No local source workspace was created, no shared checkout was changed and no uncertain source mutation was retried.

## 2. Executed standalone mathematical research

`synthetic_design_checks.py` uses Python's standard library, a fixed seed and declared synthetic inputs. It imports no product module, makes no network request and reads no market-data file. The only file it reads is its own source for a provenance hash. Its output goes to standard output.

Execution on Python 3.13.5 produced twelve passing deterministic witnesses and three Gaussian panel-mean scenarios, each with 20,000 replications. A second execution produced byte-identical JSON. These are mathematical/design checks, not unit tests of the existing engines, a market backtest or native LR statistical qualification.

Executed script: 7,729 bytes, SHA-256 `d0b889817438e7126b1c9b046bbb6c053c499c5f32817beeee9d5debe681b286`.

Executed result: 6,090 bytes, SHA-256 `dbb8aaecc0731cfe8e5edb525aa6d43b72ae87e5625a8e1d60584b3ee96338f7`.

### Declared dependence experiment

Panel dimensions are 11 sectors × 60 dates. Marginal variance is one. Same-date cross-sector correlation and temporal AR(1) covariance are specified, not estimated. The script samples the exact Gaussian distribution of the mean, not a historical panel. The oracle comparator knows the covariance; a practical estimator is not being validated.

| Declared cross-sector correlation | Declared temporal AR(1) | IID variance understatement factor | Naive nominal-5% rejection under the null | Known-covariance rejection |
|---|---|---|---|---|
| 0 | 0 | 1.00 | 5.150% | 5.150% |
| 0.6 | 0 | 7.00 | 26.835% | 5.150% |
| 0.6 | 0.5 | 20.5333 | 35.920% | 5.150% |

Each Monte Carlo rate is checked against its declared closed-form probability within a fixed tolerance. The oracle's Monte Carlo 95% Wilson interval is approximately [4.852%, 5.465%]. The same normal draws are reused across scenarios for comparability; these are not independent empirical studies. Power examples are in unit-standard-deviation effects, not basis points of market alpha.

The consequence is narrow but important: pretending dependent sector/date observations are IID can grossly inflate apparent significance. This does not say the real market has these exact correlations or that the native test fails at these rates. The native estimator, selection process, nuisance fits and generator still need their own size/power evidence.

A separate principal-side arithmetic check explicitly summed all 435,600 covariance entries of the 660-observation panel in each declared world. Dividing the covariance sum by the squared panel size reproduced the variance-inflation factors 1, 7 and 20.53333333333333 within 1e-12. This is an independent calculation method, not independent reviewer approval or a fitted-market result.

### Deterministic witnesses

The checks cover: asynchronous member extrema; defensive beta without alpha; relative wealth versus return difference; rolling-window carry without new leadership; mechanical confirmation lead; missing-breadth identification bounds; stock splits versus fund creation; duplicate thematic exposures; future labels versus future features; non-monotonic horizon effects; success-only selection changing the estimand; and common-terminal policy accounting in which delayed entry legitimately wins.

The illustrative cost and bill values are synthetic assumptions, not current spreads, market returns or a recommended trading policy. A passing counterexample proves the mathematical possibility, not its frequency in production.

## 3. Bounded research-child review

All three children used the installed M2 shell Fabric adapter under the original Web task-local root/parent `rotation-intelligence-census-20261016-sol-c1`. That label is not represented as a native provider thread or Runtime Job. They are terminal; no watcher or follow-on child is active. Exit status and quality acceptance remain distinct.

| Child | Retained result SHA-256 | Principal disposition |
|---|---|---|
| `rotation-arch-20261016-c1-contracts` | `6b54cec7c310bedd6253744da02759576122e468b944ec455e9fe5a05fb9744e` | Useful source map; independently verified selected symbols. No blanket acceptance: the return miscounted the ResearchEstimate identity fields |
| `rotation-arch-20261016-c1-science` | `69796366003fcb58bf7d1f5bfa1a657b6bc091c5bf332043b32469eed22ae37b` | Consultation partially useful; several claims rejected. Its two optional document fetches failed, so it did not establish native-source review |
| `rotation-arch-20261016-c1-final-review` | `238a484d368bcbed31e21a59cd6a69d9d39a3373b8d93c6f82aaa934fa97a122` | Terminal rc=1; provider reported HTTP 403 / final response unconfirmed. No substantive review verdict exists; not accepted, not replayed or moved to another provider |

The direct source check confirmed **eleven**, not ten, ResearchEstimate identity fields and confirmed the causal/smoothed/uniform fallback distinctions in `quad_vector.build` at the design pin. The principal also read native V1 and V2.1 protocol sections; their existing family, verdict, source, size, power and look rules remain unchanged.

### Accepted methodological insights

Retain all eligible origins rather than only eventual successful rotations; compare early/waiting/no-action policies at the same terminal date; fit nuisance parameters inside chronological training; and preserve common-factor and overlapping-event dependence.

### Rejected or narrowed claims

- Future outcome labels are not inherently leakage. Future predictors, immature training labels and hindsight-selected eligibility are the actual problems.
- Monotonic predictive performance across horizons is not a universal requirement; a genuine horizon-specific effect can change sign or decay non-monotonically.
- Same-day differencing does not eliminate a shared factor when betas differ.
- A rank metric is not mandatory as the primary statistic for an economic policy claim; the statistic must match the declared estimand.
- Unsupported numerical spread/cost estimates and universal power/sample-size claims were not adopted.
- Arbitrary lead/lag shuffling is not a universal valid placebo for persistent financial series.
- Trade costs are charged once per actual trade; long-only baselines do not acquire fictional borrow or duplicate round trips.
- Native A2's fixed five-session delay is not proof that all native economic comparisons are unfair: V1 already specifies common-origin and initial-origin policy comparisons. The exact statistic must be examined.

A completed worker process is not a quality verdict or independent release approval. The raw returns remain in M2 evidence storage at `/Volumes/Mastermind/research/rotation-intelligence-census-20261016-sol-c1`. Only reviewed conclusions are incorporated into this package. The final provider refusal is preserved; a later review needs a genuinely resolved admission boundary, not a new ID used to evade it.

## 4. Published-package verification

The ten-file package at `bef72353eb1b8085cb04f34c9ffe78acee778ecd` was fetched from exact GitHub content references into M2 evidence storage. The original assessment, scientific script and scientific result hashes matched the independently retained local originals. All ten files were present; all 17 relative Markdown links resolved, including the existing programme workstream. No production paths were changed.

The **published** script was executed on M2 Python 3.14.7. Every scientific output matched the Python 3.13.5 result to 1e-12; only interpreter metadata was excluded from numerical equality. The script hash remained exact. AST inspection confirmed only the declared standard-library imports and no product imports. This is remote execution of actual published bytes, not a claim based solely on local files.

The M2 receipt is `published-package-verification/publication-verification.json` beneath the evidence path above. It records exact blobs, sizes, SHA-256 digests, link checks and reproduction. Later documentation-only changes do not invalidate the unchanged scientific execution evidence; they require their own source/diff/link readback.

The added [NATIVE_PROTOCOL_CROSSWALK.md](NATIVE_PROTOCOL_CROSSWALK.md) then reconciled the broader allocation proposal against native V1/V2.1. The native study covers seven fixed pairs, not an all-sector allocator; price-only arms and excluded economic-simulation scope cannot be silently widened. Native P2 is falsification-only, and a new split inside inspected history is not fresh confirmatory evidence. This is a material architecture clarification, not a canonical protocol amendment. The crosswalk governs interpretation of the earlier supplement's shorthand about submitting broader work through LR-W6.

Final document-delta readback and final-head CI observations are recorded in the PR receipt after this commit, avoiding a self-referential claim that a document has verified its own future commit.

## 5. Repository and release state

At the observed `bef723...` head, grader-manifest, capability-broker, self-mod-fence, fence-pack and active `ci-authority/main` had passed; ci-plan and contract-delta were still running. The red `ci-authority/codex/merge-queue-pilot` check was inspected once. Its own output reported **zero authority hits**, `allowed=true`, `reason=ordinary_change`, and `context_active=false` / `context_reason=inactive_base_context`. The PR targets main, not that pilot branch. This explains the observed context-specific rejection; it does not authorize suppressing the check or declare all required CI green.

The branch remains DRAFT/HOLD. There is no complete independent final design review, formal approval, accepted full CI conclusion, merge or automatic merge instruction. No release settings, branch protection or shared workflows were changed to remove a gate. The actual new-head check state must be read at the next release decision; earlier checks are not copied onto later commits.

## 6. Remaining gates and recovery frontier

The architecture/research documents, protocol crosswalk and synthetic results are the current published deliverable. There are two complementary research tracks under incumbent owners: **finish native LR-W6 statistical repair without changing its question**, and **qualify the broader sector/industry/theme/cash allocation proposal with its own explicit target, population and accounting through the existing evaluation/registry owners**. The latter is not an alternate route to open native held outcomes.

Source/identity metadata qualification and mechanism specification can proceed independently. Product implementation remains deferred. The broader allocation project is not complete: native and broader-study qualification, data-source readiness, natural-consumption, conditional-issuance, operator/visual proof and release obligations remain distinct. No trade, credential change, live engine edit or market-outcome read is reported.

Before extending source scope, read the exact current branch/PR and writer state once. Preserve original immutable evidence and negative results. Do not rerun the initial census merely because an unrelated protected file changes. Research publication and recovery belong to PR #9507 and the existing programme discussion, not another memory or task store.
