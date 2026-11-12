# Marketing publisher: canonical checkout before queued publication

## Outcome and scope

This change fixes the stale-dispatch checkout boundary documented on [issue #7479](https://github.com/mastermindx-market-intelligence/macro/issues/7479). The publish job now resolves `refs/heads/main` when its checkout runs, after the existing workflow concurrency wait. A receipt persisted by the preceding run is therefore present before the next publisher folds the outbox.

The write-capable job uses `github.ref == 'refs/heads/main'` as a coarse filter, followed by an actual case-sensitive POSIX comparison of the event ref before checkout. GitHub expression equality ignores case: qualification demonstrated that the expression alone also admits `refs/heads/Main` and `refs/heads/MAIN`. Only the exact ref emits `canonical_main=true`. Both existing `always()` steps additionally require that output and a successful `publisher_checkout` outcome, preventing commit-back or liveness from using an unqualified reused workspace while retaining commit-back after a later publisher failure. The existing push guard tests the actual local Git branch. Without this admission condition, changing checkout to main would let a feature-branch or tag dispatch acquire main and pass a guard that previously refused its commit-back. Main schedule, ordinary dispatch, post-now and recall routing are preserved. The separate read-only delivery job is byte-identical.

Native source pin: `8d6a5e115a72ef93cfa779e15c1689957c27cc9e`. Publication parent: `dce366adcf109daa9a2f0bf99ed68120da6b7957`. Complete root-tree comparison confirms all ten root entries covering the 382 input files are identical; only `data` and `site` changed. No fixture or production code proof was displaced by that data-only advancement. Protected Mastermind law pin: `c42e812e4a754d7a95efd954441d3f01607a7fb5`. Source pickup: [6807635012](https://github.com/mastermindx-market-intelligence/macro/issues/7479#issuecomment-6807635012).

Only three source/test files change: the workflow, the existing social-publisher regression suite, and the existing forward-booking shallow-checkout check. Two validation reports accompany them. Publisher, outbox, approval, media, ledger fold, carryover, cap, runner-routing and bootstrap implementation remain at the source pin.

## Attributed incident

The [November 11 acceptance](https://github.com/mastermindx-market-intelligence/macro/issues/7479#issuecomment-6807065541) and [its verification](https://github.com/mastermindx-market-intelligence/macro/issues/7479#issuecomment-6807259429) identify the historical pair:

| Event | Evidence |
|---|---|
| Accepted item | `ob-2026-11-11-fa18d8bab3` |
| First run | `43098323577`; accepted provider receipt `6af4d6b938da815779d362c4` |
| Receipt persistence | Commit `6faa635fc88781f30aeb225dd6846ee07be2b135`, 20:57:31 UTC |
| Later run | `43098822704`; dispatched from older head `406f2d9f…` before that persistence |
| Duplicate attempt | Provider rejected the later attempt at 20:58:16 UTC |
| Existing fold | Canonical state remains posted with the first receipt; late illegal transitions do not erase it |

Concurrency serialized those runs but did not refresh the second run's default checkout. The old workflow fetched/rebased main only in commit-back, after the provider attempt. Its incident workflow blob `36b3f42c32f939e2ddec7bf1d3bb9e350abff908` was still current at the source pin.

These are historical references. Qualification did not replay either run, invoke a production provider, change the item's identity, or rewrite any historical ledger.

## Native consumer proof

**274 passed, zero skipped**, in 12.93 seconds (13.337 seconds process elapsed). Python 3.14.7, Git 2.46.1, pytest 9.1.1, PyYAML 6.0.3.

The new `TestQueuedPublishCheckout` uses actual temporary bare Git origins and independent shallow checkouts. Both jobs retain the same dispatch SHA. Job A runs the actual `scripts.marketing_publisher.main`, replacing only its provider factory with the existing recording fake. Its actual outbox transition and publication files are committed and pushed to the local origin. Job B starts its own checkout afterward, using the actual checkout ref/depth inputs read from the changed workflow, then runs the actual publisher.

No ledger is copied directly between A and B. Git performs the checkout. The production publisher implementation is unchanged at the pinned source. New fixtures block Python DNS/socket connections, prohibit Git network protocols, and use only local-file origins. They contain synthetic items and provider receipts; they do not claim to reproduce admission of the original incident's unavailable post copy.

| New case family | Cases | Required outcome |
|---|---:|---|
| A ordinary/post-now × B ordinary/post-now | 4 | A sends once, persists acceptance; B makes zero provider calls |
| Fresh posting, quarantined or recalled × ordinary/post-now | 6 | B respects the newly persisted in-flight or terminal state |
| New operator HOLD × ordinary/post-now | 2 | Queued item remains held; no send |
| New explicit failure without a new approval | 1 | Ordinary B does not retry; one failure attempt is preserved |
| Actual admission shell: main, Main, MAIN, main-fix, tag main | 5 | Exact main passes; all four other refs fail without a successful output |

The accepted-post cases additionally check the first external ID, terminal status, zero attempts, one posting slot, and byte equality of status/decision/publication receipts. Publisher activity rows are deliberately outside that equality check because the existing runner appends run activity even when no item sends.

A queued item is the first run's positive control in all four accepted-post cases. It still clears the existing auto-approval/post-now policy and sends once; the fix does not remove legitimate carryover. Terminal-only post-now retains its existing exit code 3, despite correctly making no provider call. Ordinary no-send sweeps retain exit 0.

**Counterexample:** with the same expanded regression suite and the original workflow, **17 fail and one passes** in 8.33 seconds. All 13 delayed-checkout cases and all four non-main admission cases fail; the exact-main positive control passes. In the accepted-post cases, the second fake provider receives another publish call from the old dispatch checkout. The failure is observable at the provider seam, not inferred only from a YAML string.

### Focused suites and ownership

The native command exercised:

- Full `tests/test_marketing_social_publisher.py`
- Full `tests/test_marketing_publisher_autoapprove.py`
- Full `tests/test_marketing_outbox.py`
- Two shallow-checkout parameters and the rebase-depth check in `TestPublishLaneCheckout`
- Three `TestDeliveryReadbackWorkflowIsolation` checks in `tests/test_marketing_metrics_poll.py`

The new executable regression is inside existing CODE owner `marketing-social-publisher`. That owner also runs the metrics suite, whose checkout-rooted workflow reference already supplies the relevant inferred dependency. No CI owner, catalog, baseline, cap or command changes are needed. The owner's existing 5 commands / 28 test mentions / weight 62 remain unchanged.

The forward-booking suite belongs to DATA owner `marketing-engine`. Its three native checks are not a claim of PR CODE execution. The shallow check previously inspected the first YAML job, now delivery-readback; it now explicitly inspects the publisher job for this workflow. The published total is native proof across the listed suites, not a claim that all 274 tests have already run in hosted CODE CI.

The first isolated run had six failures caused by two omitted input files: the publication-receipt schema and the actuator script invoked by existing subprocess tests. Both were restored verbatim from the same source pin. No production or fixture logic was changed to suppress those failures. The completed input manifest contains 382 hash-verified source/support files; all non-owned source bytes remain unchanged.

## Job admission and routing proof

The actual changed YAML expressions were evaluated using GitHub's official `@actions/expressions` package, version **0.3.61**, on Node **v26.5.0**. The package tarball integrity is:

`sha512-Ig+tXELvTjlqxQAWBQnLNn2dPpNraLMdSnT+vDzDPmJtbNUhIAH/Z9kVT8pZ8UtJi9vUGs8hwHE8JFJmbOnLEA==`

**All 21 contexts passed**, combining the actual extracted admission shell with the actual YAML expressions. Main schedule, ordinary dispatch and post-now admit the sender. Main recall admits recall only. Main delivery-readback, including recall plus readback, admits only the separate read-only job. Feature-branch ordinary/recall and both tag-write contexts exclude the write-capable job. Feature/tag delivery-readback retains the original read-only behavior. All seven tested non-main write contexts are excluded and every tested readback result is unchanged. This includes case-variant ordinary and recall dispatches that pass the coarse expression but fail the real shell. Failed or skipped checkout blocks both finalizers. Successful admission/checkout still permits the authorized commit-back after a later publisher failure. A disarmed main recall retains its commit-back exception; a dark ordinary sweep cannot commit its activity row.

The accompanying JSON contains the actual expressions, contexts, evaluator harness and results. This uses the official expression implementation; it is not a hosted Actions execution. The harness initially used the README's array constructor example; the installed declaration requires variadic dictionary pairs. The harness was corrected against that declaration before the accepted expression results. No workflow behavior was changed for that harness correction.

Official source pins verified by Git blob hash:

- [Checkout input resolution](https://github.com/actions/checkout/blob/11d5960a326750d5838078e36cf38b85af677262/src/input-helper.ts), blob `2ded955533070ad5a1cd5fd4b3f29e0b15e13833`.
- [Checkout ref mapping](https://github.com/actions/checkout/blob/11d5960a326750d5838078e36cf38b85af677262/src/ref-helper.ts), blob `925be86614ded8ed4057bbbed4b3d15170f6e445`.
- [Checkout fetch and working-tree execution](https://github.com/actions/checkout/blob/11d5960a326750d5838078e36cf38b85af677262/src/git-source-provider.ts), blob `2d3513897655e0ea2eb4efc2b2c9d6132a69549f`.
- [Official expressions package](https://github.com/actions/languageservices/blob/4043eda158e16579cc5fb1b0b07a4bce2a76f0b5/expressions/package.json).

The checkout action's omitted-ref path binds the event SHA; its explicit branch-ref path resolves the branch during fetch. This is the boundary exercised by the real-Git regression. The proof pin does not change the workflow's existing action version.

## Custody and composition

The current-source repair preserves the other relevant carriers:

- Original Lane A #7487 is already merged.
- #7489 at `c1a18f3dd3f193c63a00b2c237f96ff53ae499c7` owns media/payload/HOLD work and retains its own evidence boundaries.
- #11026 at `2286f6fdd83f0c71d09895e9a31a03115aafe9a1` changes routing/Python-bootstrap lines in the same workflow. Its current hunk does not change the checkout ref or main admission. Those contributions and its original descendant uncertainty remain there.

Retained complete inventories plus the 21:34:04 UTC frontier were checked for the workflow, social-publisher suite, forward-booking suite and a proposed new checkout-test filename (the new file was not needed). The latest 100 PRs reused 86 exact heads and refreshed 14 complete inventories, covering 681 file entries including rename origins; those 14 had zero target hits. All seven retained large partial inventories were freshly head-confirmed and qualified by 28 merge-base/head path comparisons. The only recorded workflow overlap was #11026's separate hunk. A final five-PR update delta reused two unchanged heads and qualified three additional stable native inventories: #10851 at `d0f2b7fbb9fccb703544687a8f9266bb7e33607d` (10 files), #7466 at `d31d31f56b27448f08fe6ff385e86143224417c3` (64), and #10221 at `7c042f544f7de662cb442d3edf85be2bd469b724` (9). All 83 filename/rename entries had zero hits on the three final source/test paths. This is bounded path/custody evidence, not a claim about every later estate update.

## Evidence identities

| Evidence | SHA-256 |
|---|---|
| Final green log, 341 bytes | `50053309a3731622c56ac2f029ffa21dd7cc19c2edaeb9185d432f521d330f82` |
| Original-workflow counterexample log, 46,085 bytes | `6a2545a279e79922b972eee4b189a5f5436373686da026e8dc7cbfa2bfd9c65e` |
| Official-expression results | `2fa6ff404b3102a346c3a51f0078f1c4374b080c22c025fcec3b2e953d8485c4` |

The JSON report contains complete input/candidate manifests, native test receipts, source-diff hashes, official source identities and expression results. It accompanies executable regression source in this PR.

## Release and remaining proof

This is a source-ready correction with native consumer proof. Exact-head hosted CI and the repository's binding release controls still govern merge-on-green enrollment and merging; native GitHub auto-merge and direct self-merge are not used.

A natural post-merge workflow execution should confirm the workflow revision and actual checkout commit before its publisher step. The Actions run's `head_sha` alone is the dispatch identity and is not proof of the checkout's ledger freshness. Already-created runs may retain the old workflow definition; this change does not rewrite or replay them.

The correction closes the demonstrated case where A has persisted acceptance before B begins. It does not promise exactly-once delivery when a provider accepts but persistence never reaches main. Job-start freshness also does not make later independent HOLD/media updates atomic with a provider call during setup or jitter. Those remain separate boundaries, including #7489's work. No live provider post, recall, workflow dispatch, historical-ledger edit or production acceptance is claimed by this report.
