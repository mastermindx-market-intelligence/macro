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
