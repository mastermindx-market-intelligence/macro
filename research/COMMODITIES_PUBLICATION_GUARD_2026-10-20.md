# Commodities publication guard — 2026-10-20

## Purpose and status

Dashboard PR #9878 merged as `14799f153a16b4b570e0f294aa2e5d3df5c416e1`. Its R3 projection is accepted source. Express, normal and nightly site publishers can replay an older generated page through their existing rebase strategy; ordinary template-copy guards do not rebuild this Jinja page. This follow-up preserves an already-qualified Commodities workspace through that publication boundary.

Status: implementation and local qualification complete as of 2026-10-21; original-branch publication and hosted CI remain pending. Publication and CI receipts will be added after they exist. Adoption requires the accepted main page to contain the qualified R3 projection and the pre-R3 publishers to have drained. M1 Paper remains parked and is unrelated to this Git change.

## Bounded contract

`scripts/check_commodity_publication.py` qualifies exactly one workspace mount and one closed JSON payload, the source-owned schema/revision, display-only/non-live state, export-only research with inactive monitoring, an asset collection and a valid fingerprint. Empty or unavailable observations remain valid; this guard does not create economic evidence or certify freshness.

Recovery copies only the complete accepted `site/commodities.html` blob from one resolved commit. Missing/invalid/regressed candidate pages can be restored only when that accepted page satisfies the required revision. An unknown schema or a newer unsupported revision is refused, never downgraded. An invalid accepted baseline requires reconciliation, even if a candidate looks valid.

The worktree destination must use the real `site/` directory and a regular, contained page path. Referenced CSS/JS must already exist in the candidate. Missing assets refuse before writing; no builder, collector, canonical data mutation or asset restoration runs inside the retry loop.

The exact Git-candidate mode reads the page and assets from the proposed commit, separately from the worktree. It cannot heal. This prevents a successful working-tree repair from certifying a failed or skipped repair commit.

## Publisher integration

| Path | Admission and final proof |
| --- | --- |
| Normal render metadata replay | Pin fetched main, inspect the private-index `PUBLISH_COMMIT`; delete its temporary ref and stop on refusal. |
| Normal render rebase | Heal from the same pinned accepted commit before normalizers; validate committed HEAD immediately before push. |
| Express engine render | Use the existing explicit-ref fetch/collision-containment helper; pin and rebase onto that exact accepted SHA, heal before normalizers, then validate committed HEAD. |
| Nightly engine output | Heal after rebase; validate the explicit `qledger_push_candidate` used by the push refspec. |

Existing asset checks, conflict guards, qledger custody, CI authority and retry budgets remain in force. Every new check is a hard stop. Failed optional render-sync commits cannot publish an older invalid candidate.

## Evidence

- A real temporary Git repository recreates `rebase -X theirs` replaying a stale renderer over an accepted R3 page; recovery preserves the unrelated page and canonical data.
- The 35 guard cases cover malformed/duplicate JSON, nonfinite values, display/research invariants, version transitions, missing accepted refs, pinned-source identity, missing CSS/JS, worktree vs committed candidate separation, and internal/external symlinked site directories.
- Combined local projection, physical-context and publication suites: **77 passed plus 35 subtests**, with no failures.
- All four curated CI registration, scope and import-closure checks passed (295.95s).
- Six Node state/import/company-return contracts passed.
- Read-only qualification of the actual accepted merge commit and its committed assets passed with the original page hash and projection fingerprint.
- Bash syntax checks of the two publication workflow steps and the nightly helper passed.
- Independent source review found and prompted the site-directory custody repair. Workflow review found and prompted the express publisher's stale remote-tracking-ref repair.
- The existing required Commodities CI pack now includes the guard suite and named import/read dependencies. No new packing exception, threshold increase or disabled assertion is introduced.

Freshness is explicitly `false` in guard receipts. Normal render source ancestry, positive builder logs and the real served workspace still need separate release verification.


## Resumed qualification — 2026-10-21

Resumed from Macro #9878 comment 6306865883 in the original operation `commodities-publication-guard-20261020`, branch `sol/web-commodities-publication-guard-20261020`, base `14799f153a16b4b570e0f294aa2e5d3df5c416e1`. Protected procedural source pin: Mastermind `d3537d6dd1cf63178a1493eb70fa2eccc6c01fe0`. The inherited guard, publisher, DAG and test bytes were frozen before qualification and rechecked unchanged before this evidence update. Accepted R3 source and product qualification were not rewritten or rerun.

| Check | Observed result | Log SHA256 |
| --- | --- | --- |
| `tests/test_push_retry.py` | 123 passed, exit 0 | `78ea12bd7765b0ce44b72e065641b07cbf922d012d7adfc3d777427c08bd9342` |
| DAG checker self-test | Passed, exit 0 | `f6aa4f2dbcfc5c0046012af960643e78ab1965be5c2262fdecf3b60fb383f352` |
| Actual DAG conformance | 27 lanes checked, exit 0; two declared existing suspect drifts | Process 46792 output |
| Four curated CI registration/scope/import-closure tests | 4 passed, exit 0 | `1cf42347d7e6d61b8dc83ae683754bebe9020aa46b4b6efaca88b6094f4ea584` |
| Contract delta against exact base | 0 introduced, 0 inherited, exit 0 | `f736cc67725bffd03e86051566c507e80be02d14bf86d39adfdce21a63795377` |

Local logs: `/tmp/commodities-guard-qualification-20261021-r1-{push-retry,dag,ci-scope,contract-delta}.log`. The six pytest cleanup warnings concern pre-existing temporary browser framework directories; they are not failed assertions. Both staged and unstaged `git diff --check` passed. Contract-delta probe ceilings remain unchanged. The `commodities-research-workspace` job on fetched main `a9c9a04bacee52565b5e03fec31193e6a19cef9d` is byte-identical to the base job; other owned implementation files had no upstream changes at the comparison boundary.

The principal directly reviewed the inherited guard, committed-candidate checks and all publisher integrations, including the previously reviewed site-directory and pinned-ref repairs. Existing independent source-review acceptance remains applicable to unchanged core files. A new bounded Fabric review attempt did **not** start a worker: run `commodities-guard-review-20261021-r1`, controller 40272, terminated pre-lease with rc 78 (`PLAIN_PACKET_RETENTION_REFUSED`, retained request packet already exists). It supplies no new review pass; no deletion, native-labor substitution or alternate run was used to bypass it.

### Separate release observations

Terminal #1092's exact head `718f1f181bda2ef694c2d4bce153b576a8583636` had successful CI run 39495589078 and all current required contexts. Its obsolete `merge-blocked` label was removed and ordinary squash merge succeeded as `5e342dd15d19e49bce8e2f7d8fce720fe58d1bd3`. The attempted explanatory PR-body update failed and was confirmed unapplied; the label and merge were separately read back. No formal GitHub approval or deployment is inferred from those actions.

The documented VPS read-only inspection returned SSH `Permission denied (publickey)` before any deploy. No deployment action or alternative credential route was attempted. A current authenticated browser session independently opened AAPL Intelligence from the real Commodities company link, retained all five `mo_*` context fields and nested `ret`, then the actual Dashboard button restored the exact original URL:

`https://www.mastermind-x.com/commodities.html#cw/relationships/oil?window=1m&compare=oil%2Cgold%2Ccopper%2Csilver&hypothesis=unresolved`

The returned UI selected Relationships and WTI crude. This is existing-session navigation proof, not a fresh Google OAuth round trip or proof that the newly merged Terminal generation is deployed. Normal covering render, served source identity, guard hosted CI and publication remain separately open at this timestamp.


## Publication CSS invalidator and bounded repair — 2026-10-21

The first guard candidate was published on the original branch as `71555cbb094b2aeb6e677c7e3a10b704c65f04d7`, PR #9926. A separate production-source check then found a real invalidator: current main/public Commodities HTML (`f77ba615bac1e4b8892c50ad5092c6b79ea3fcf8dec09164f9dfd3c83b1cfd18`) references `assets/css/product-nav-icons.css`, which is absent in Git and returns HTTP 404 publicly. The guard correctly refused that candidate. The public HTML matched main `1fbe8fc7f6f19ba4ccdd93e1b7ac29b40d9cb2e5` exactly; the embedded R3 payload also matched the accepted source exactly. These equalities do not make the broken asset acceptable.

The accepted review page inlined canonical `theme.css`. Publication externalized that style into `assets/css/52302c47.css` without relocating its relative import, then optimization added the invalid preload. The normal production template also omitted this canonical theme. The bounded repair loads the existing root `theme.css` at the same cascade position in the production template and committed page. Canonical theme bytes remain SHA256 `2e8611477fd3499877721f9ce9386b1c3a55e00a2ed87c4187387845775ae64a`; no shared optimizer rewrite or duplicate asset is introduced.

A discriminating regression renders the actual production head, runs the real externalizer and optimizer, checks the preserved canonical theme and its imported files, and proves a second normalization pass is stable. It failed against the prior template (missing canonical theme) and passed after the repair. All 36 publication tests passed (7.29s). Red log SHA256: `e9f7eaf79cbd99ea641aae78f20763506eb5a055b2accfef8e68b216afeaae3e`; green log SHA256: `dfc5e3fba26d32bcd330e0dad483b8928ae585377f018163f2ab7e46850044b3`. The initial scope audit then detected four additional transitive imports; the existing Commodities CI job was widened to cover them. No ceiling or assertion changed.

The page repair preserves the exact `cw-data` bytes, SHA256 `c38e6d7bbd707462ca43f73f4fea6e389e6906b82c0e6ef1ca9845481c9a0190`, revision 6 and fingerprint `2d3d68280a023930ac7cf9a8c2ece1cfeda609ea9b297c3b954a56fa34c88d47`. Its pre-integration page SHA256 is `e8314469583d32f0da497b2ce2bf27fcf77fcd9579993ac269df0c6875a305d1`; the guard keeps it with `freshness_verified=false`. Accepted R3 JS, data interpretation, research export and monitoring semantics are unchanged.

A distinct Fabric review request for this newly discovered CSS defect (`commodities-css-publication-review-20261021`, controller 13813) terminated before worker start, rc 78, `PLAIN_PACKET_RETENTION_REFUSED`, retained request packet already exists. It supplies no review acceptance and was not retried through another identity or carrier. The principal performed this bounded critical-path source repair under `CRITICAL_PATH_SHORTCUT` and `NO_ELIGIBLE_PRE_EFFECT_WORKER`, preserving original workspace/branch custody. Native delegation supplied coordination judgment only, not substitute implementation or leaf review.

Current main was fetched and pinned at `a580ce7e780f46775fcacec282be590ed14ee802` for integration. A read-only three-way probe predicts one owned page conflict because main already externalized the accepted inline CSS. Integration must preserve current generated-page changes and only replace the broken canonical-theme reference and preload. Fresh integration qualification and exact-head hosted CI are still required; prior-head CI is not transferred to the repair.

Pre-integration scope requalification passed: four curated registration/scope/import-closure checks, exit 0, 142.40s, log `/tmp/commodities-theme-qualification-20261021-r2-ci-scope.log`, SHA256 `25cb6f563112f059787cb0e5e5acc7a15cfe7fb1b3ddf11252743a3056cdd166`. This closes the four newly detected named import dependencies.

### Same-branch integration qualification

Prepared the history-preserving merge of main `a580ce7e780f46775fcacec282be590ed14ee802` into repair commit `a45b2795a848668a45316b29f1b71e7e3dccaf31` on the original branch. The sole conflict was the canonical-theme link. The resolved page is byte-for-byte current main except for the root-theme URL correction and removal of its invalid preload; all concurrent generated markup and asset stamps survive. The exact R3 payload is unchanged. Final page SHA256: `0679961ea7f55eda7d80372f051b65c6d3451260351b5f6ac5c9e851762510ec`.

The real integrated page plus its 12 referenced/imported CSS/JS assets passed the guard and both publication normalizers in an isolated artifact fixture. Externalization changed zero files, optimization left the page unchanged, and a second pass was also stable. Every local CSS import existed. Log `/tmp/commodities-integrated-page-qualification-20261021-r2.log`, SHA256 `c1f7330aca21f7a2651783816f7e25ed5fbe5c5c20a4cb88654db48ff86734bb`, exit 0. This proves the local publication transformation, not deployment.

The implementation whitespace check passed. The successor checkpoint retains its original 12,401-byte prefix exactly, including two intentional Markdown hard breaks; its appended text is whitespace-clean. The first broad whitespace probe stopped on those preserved hard breaks before running normalization, and was not reported as a pass. Exact committed-candidate verification, contract-delta results and hosted CI are to be attached to PR #9926 after the merge commit exists.


## Hosted-CI causal repairs — 2026-10-21

The first published head's hosted run 39541411759 (head `71555cbb094b2aeb6e677c7e3a10b704c65f04d7`, tested merge tree `ee47274d5d30bb140c78e54ed6a02859280ef592`, Python 3.12.13 on a GitHub-hosted Linux runner) completed with five affected legacy-job failures. These were not treated as inherited reds or waived:

| Job ID / group | First relevant failure | Causal repair |
| --- | --- | --- |
| 119030108200 / unrun-import-hygiene | New check script has no strong repository-root pin; bare invocation may import a foreign tree | Pin this script's own root before repository imports, following the existing guard-family contract. |
| 119030108220 / dag-conformance | Government Revenue lane test cannot find the old express pull/rebase literal | Locate the actual pinned rebase and assert fetch precedes accepted-ref pin, which precedes rebase; retain every downstream projection/normalization assertion. |
| 119030108240 / commodities-research-workspace | Real rebase fixture exits 128 | Supply identity in the temporary repository, covering rebase as well as direct commits. |
| 119030108324 / house-law-registry-code | New check is absent from the hard-law census | Register `ui.commodity_publication_integrity` as hard on normal, express and nightly publishers, with truthful fixture coverage and limits; regenerate registry docs. |
| 119030108335 / workflow-yaml | Dead-asset contract cannot find the old express pull/rebase literal | Assert the same stronger fetch/pin/rebase sequence and preserve both committed-head asset fences. |

The identity hypothesis was reproduced at head `ab1d4375b8235c183f8f0ad7b86ec10f3759c1de` before editing: suppressing host Git configuration and identity variables made the existing real-rebase fixture fail with `Committer identity unknown` and rc 128. The repaired full Commodities group then passed under that same isolated Git environment. No global Git identity was changed.

| Affected qualification | Result | Log SHA256 |
| --- | --- | --- |
| Full Commodities projection / physical / publication group with host Git identity disabled | 78 passed, 35 subtests passed, exit 0 | `99dc4bd5430a04040aeacb122196ea6f4505b51ac3e134518dcaa79dd2518f94` |
| Import-side-effect and repository-pinning group | 15 passed, exit 0 | `45f0e3c38f7bc599022ef47dc535e34f74ee931633c03b22d767f168b918d808` |
| Complete existing DAG contract group | 236 passed, exit 0 | `49c21cae91c9259586fdd98f359033d0aa8876cb7fb3ba69474021fbee1694ba` |
| Existing code-gated dead-asset command | 6 passed, 1 existing data-gate deselection, exit 0 | `8380e2d5f1262a593d533fd0cdff3fa2d632783420049fac2c024a06ce63101e` |
| House-law selftest, live census/wiring and focused suite | selftest/live pass; 20 tests passed, exit 0 | `4d4815f04d5ef9b1324c6c617609be306e0d96221aed2134600b6684a6e9ff6a` |

Logs are `/tmp/commodities-ci-repair-20261021-{publication-sterile,import-pinning,dag-contracts,dead-asset,house-law}.log`. The three existing registry ratchet warnings and host pytest temporary-directory cleanup warnings are not newly introduced failures. All production guard predicates, publisher behavior, retry budgets and test assertions remain enforced; only the executable import boundary, test environment, obsolete command recognition and required registry metadata changed. The principal performed these bounded causal repairs under `CRITICAL_PATH_SHORTCUT` / `LOWER_TOTAL_OVERHEAD`; no failed Fabric request was replayed and no new worker review is claimed.

The preceding content-qualified tree (`29bdaf11b4e8316e311c453c878a61ddc760dcf0`) passed contract delta against pinned main with 0 introduced / 0 inherited (log SHA256 `a338bf032c66e60bf05df3c81808aa3dd1c33c1b154e15cd9690dfd2b02a3bb7`). The new causal repair requires its own committed-candidate and differential qualification; the final exact-head receipts belong in PR #9926. Page SHA256 remains `0679961ea7f55eda7d80372f051b65c6d3451260351b5f6ac5c9e851762510ec`, and the accepted R3 payload remains byte-identical.
