---
workstream: "WS:OPTIONS-ALPHA-INTELLIGENCE-RECOVERY"
session: options-alpha-product-20261003-root-delivery-checkpoint
model: codex
ended_because: ci_handoff
mission_complete: false
mission: >
  Finish the existing Options Alpha product through its established Macro data,
  research and runtime owners and the Terminal experience. This is a recoverable
  active-work checkpoint, not a claim that the parent session or product is done.
state_before: >
  The existing measured-source, episode/campaign, candidate, FS5 and exact-option
  systems were reused. Candidate activation and statistical promotion remained
  separately gated. Terminal production was at 863f678658e2211b5a48daa99404686dfaa117f2.
changed:
  - path: agentos/workstreams/WS-OPTIONS-ALPHA-INTELLIGENCE-RECOVERY.md
    what: Reconcile accepted source, production release, runtime installation and remaining evidence gates.
  - path: agentos/discoveries/DSC-M1-STORAGE-GUARD-HELP-MUTATES-20261003.md
    what: Record the version-bound inspection mistake and unresolved deletion effect.
prs: [7306, 7417, 8201, 8313, 8318, 8322, 8345, 8346, 8350, 8358, 8359, 8360, 8361, 8370, 703, 723, 788, 789, 791, 793]
verified:
  - claim: The combined Terminal release is deployed at the accepted merged SHA.
    command: "Canonical ops/terminal-build.sh --target-sha 8fc1d1a038932c20dbb3d677a614f79445f90d0e through M2; fresh VPS Git/marker/service and HTTP readback."
    result: >
      PR793 merged at22:35:17Z after all protected checks and independent review.
      All11 merged blobs equal accepted head3c627f70. Deployment returned0 at22:51:18Z.
      At22:53:14Z canonicalHEAD and deployment marker equal8fc1d1a038932c20dbb3d677a614f79445f90d0e,
      checkout is clean, service active, and local/public Options responses are200 with that deployment ID.
  - claim: Candidate transport boundaries and the authenticated unavailable state work on the deployed release.
    command: "GET /api/flow?f=options_alpha_candidate_feed and /api/flow/stream?f=options_alpha_candidate_feed; fresh authenticated Chrome reload."
    result: >
      At22:54:35Z unauthenticated candidate request403 pro_required/no-store;
      unsupported candidate SSE400 bad f param/no-store. Browser shows6 of2000
      measured events with explicit Sep25 source timestamps/staleness and unavailable
      candidate history, without an invented feed/receipt pair.
  - claim: Chain Heat corrected source is installed in the existing M1 job.
    command: "M1 cutover receipt at22:10:40Z; independent hash/mode, plist semantic and launchctl/process verification."
    result: >
      Exact five-file source artifact from Macro7084e176a8d510f96082d4195ee4117e08002890
      is installed at /Users/chriswong/chainheat-ops-wt. Only wrapper, working directory
      and PYTHONPATH changed. Label com.macro.chainheat, all415 ordered schedules,
      original environment and interpreter are preserved. Loaded/not running; no manual publication.
  - claim: FS5 C2 forward-admission source is independently reviewed, CI-qualified and merged.
    command: "PR8360 review5403040900; logs under M2 /private/tmp/fs5-c2-recovery-20261003/; CI37157875969 pack11 semantic fragment."
    result: >
      Approved head bfe2c663480055814a12184c4858b07ba98b1918 merged as
      d87d00a46e6a4cdffba667079615e2a4b437aea8 at 23:08:08Z.
      Local109 FS5,116 FS4,168 candidate/exact-outcome,43 flow,266 real-fixture
      episode cases and the separate required114 candidate/publisher/build/enrichment
      cases passed. All 12 hosted CI packs, ci-gate and the active main authority
      passed. No unresolved review threads remain. This is source acceptance only.
  - claim: Raw-event R2 retention metadata does not configure object expiration.
    command: "M1 normal owner environment and R2 factory, metadata-only lifecycle and HEAD audit at20:34:03.324010Z."
    result: >
      One enabled DefaultMultipartAbortRule; no object or noncurrent-version
      expiration. Sep17 dated event object exists,1141823 bytes. No raw body or credential was copied.
  - claim: The existing sweep/package semantics carrier is merged.
    command: "PR7417 exact-head approval5364699564, complete CI35442237113, current-main blob comparison and normal expected-head squash merge."
    result: >
      Exact accepted head f3335f8e0cc2aada62445159643a80d207d0e402 merged as
      1be595c12072b1566b2acd11ccd0561a3a799420 at23:32:42Z. Root reran all69
      exact merged-source enrichment tests successfully. The existing M1 job
      received the exact engine/builder pair at23:42:39Z, original plist and
      interpreter unchanged, with hash-bound rollback and import-only PASS.
      Its next scheduled cycle ran at23:47:40Z, exited0 and uploaded at23:47:43Z.
      Local and owner-authenticated R2 outputs match SHA
      8eabd08b10aa0fa437e9c2afe3f6131f0619a04f6ff933d1a1fbc0ad9686b1d9.
      All26 sweep flags remain; unsupported MULTI_LEG/direction discounts are0.
      Source/asof stays2026-09-25T20:09:25.764815Z, distinct from built_at
      2026-10-03T23:47:41.724556Z. This natural derivative publication supplies
      no fresh-market, candidate, calibration or predictive evidence.
unverified:
  - claim: B1 corrected gamma source is installed in all persistent consumers.
    what_would_verify: "Reviewed source-root/input-root changes, protected merge, exact runtime acquisition and existing-job binding receipts for index history, matrix and hub. B1 source merged15af4b7fc1d5216542a4e0970e34f40233975c3d; runtime remains held for the exact four-parquet publisher floor repair."
  - claim: FS5 pre-fit methods are complete or an empirical study is eligible.
    what_would_verify: "Root source integration, bounded test-leaf return and independent review of true15-path CPCV, variants and native-session support; then separately frozen eligible prospective data. No actual study or fit is authorized by this checkpoint."
  - claim: Natural runtime, candidate activation or statistical promotion is accepted.
    what_would_verify: "The existing natural publisher, durability, campaign, correction, AD1, activation and science receipts; source merges and screenshots do not supply them."
decisions: []
discoveries: ["DSC:M1-STORAGE-GUARD-HELP-MUTATES-20261003"]
unresolved:
  - "Independent live UI acceptance failed mobile title geometry and first-load candidate copy on release8fc; Fable is repairing the existing Terminal703 carrier."
  - "Both earlier FS5 workers terminated with cleanup proven and zero residuals. Root integrates trainer/admission in the same archived custody workspace; bounded helper/test leaves support it."
  - "The Oct3 22:30Z qualifying daily run had not appeared at the bounded observation. Delayed scheduling remains possible;23:30Z is an off-regime skip."
  - "AD1 remains INSTALLED_CANARY_ACCEPTED_PRODUCTION_HOLD; required runner-group selected-workflow admission is not available to the current identities, and M1 free space remains below200GiB."
  - "The interrupted M1 storage-guard apply has unresolved deletion effect; preserve its canonical evidence and old runtime/rollback trees."
next_actions:
  - "Complete the methods repairs, integrate the merged parent onto main without rewriting history, and obtain independent exact-head review and protected CI."
  - "Complete independent review and CI for the root-integrated FS5 methods branch and the B1 publisher-count follow-up; preserve each custody workspace and owned-process receipt."
  - "For index history, use separate clean code and physical artifact roots; its five tracked outputs cannot be replaced by a symlink in a clean clone. Reconcile the existing publisher checkout separately."
  - "Consume the qualified Terminal703 merge, deploy its exact merged SHA through the sole root executor, and repeat independent EN/ZH desktop/tablet/mobile acceptance."
  - "Fable owns703 pending desktop CI,7306 updated-base head47ef463e36768cac0b6f49c7946f35351a308ba6 pending checks, and8201 current-main raw-clock compatibility integration/review. No merged release is inferred; preserve Terminal723 custody."
  - "Observe the required natural runs and resolve the exact AD1 admission/capacity dependency without replay, new collectors or lowered evidence floors."
do_not_redo:
  - "Reuse the existing collector, event/campaign/outcome owners, sole candidate feed/receipt publisher, journal, score controls and Issue Desk."
  - "The user authorizes revival; historical closed-owner labels alone are not a prohibition. Preserve actual live writers, pending effects and required scientific evidence."
  - "Sep17/18 measured-source to Flow evidence is already established; do not commission another event hunt or reconstruct historical availability."
  - "Do not infer activation, calibrated probability, ranking, sizing, trading or profitability from source tests, UI availability or installation."
danger_areas:
  - "Terminal first adoption requires the complete exact merged ops archive because the installed executor selects its preflight policy before fetching."
  - "M1 flow-ops Git metadata and the old index publisher checkout point at stalled external storage; metadata readability is not payload or Git health."
  - "The local storage-guard incident is unrelated to the R2 retention audit. An absent final reaper report does not prove no deletion."
  - "M1 launchd calendars use PDT, verified UTC-07:00; do not silently interpret their hours as Eastern Time."
---

## §0 State — what is true right now

The combined Terminal source is live at `8fc1d1a038932c20dbb3d677a614f79445f90d0e`.
Chain Heat is installed and awaits its natural publication. FS5 methods and three
gamma runtime consumers still require completion; the broader product remains
active, with candidate activation and empirical acceptance unearned.

## §1 What is LEFT — in order

The root remains the active orchestrator on Terminal issue599, operation
`options-alpha-product-integration-20260917-sol-001`. Fable owns independent live
UI acceptance. Source work uses the existing M2 fabric, not a new scheduler:

- `options_product_20261003_fs5_prefit_methods`, branch
  `codex/options-alpha-fs5-prefit-methods-20261003`, began on exact8360 headbfe2c663.
  The initial worker reached its turn limit at 23:13:47Z; owned-process cleanup is
  proven with zero residuals. Root archived all eight dirty source paths at
  `/private/tmp/fs5-prefit-recovery-20261003-2325` on M2, archive SHA
  `d8718f63aa155e48b5215f86506a16d581172a78977d2c480fcc64fe8f301890`.
  Hard review blocks closure on weighted calibration, incomplete-gauntlet
  deployability, canonical era identity, frozen configuration and actual fit
  receipts, purge indexing and pre-freeze feasibility. The second worker timed out
  at23:59:33Z; owned-process cleanup again proved zero residuals. The second archive,
  /private/tmp/fs5-prefit-recovery-20261004-0004, has SHA256
  98fb67ce0786fa8b959927a0e216e65453bd39c8bcba60057684f0b413409565.
  Root directly integrates trainer/admission in that same workspace. A bounded
  helper leaf returned and a test-only fabric leaf remains active. Independent
  review corrections were applied;165 focused synthetic cases passed, with the
  full integrated trainer suite and exact committed review still owed. Weighted bin/tie rules and a numerical
  per-bin floor are not invented: unresolved calibration stays explicitly
  unavailable and non-deployable. All tests are synthetic; no real study or fit.
- `options_product_20261003_b1_runtime_roots`, branch
  `codex/options-alpha-b1-runtime-roots-20261003`, preserves the three existing
  jobs and their physical inputs. PR8370 returned at head
  `418f43ce700093d976c37da6b9e952d33e489a38` after a bounded same-workspace
  amendment. Worker returned0 at23:53:03Z with cleanup proven and zero residuals.
  Immutable code review passed; the initially stale PR body was rewritten.
  Focused selection204 passed,3 existing boto3 skips; root separately ran the
  publisher suite with M1's exact boto3 1.43.56 in an isolated dependency target:
  71 passed, no skips. Both prior missing-fixture failures now pass. All12 CI
  packs, ci-gate and the active main authority passed; approved source merged
  as15af4b7fc1d5216542a4e0970e34f40233975c3d. Runtime remains HELD:
  carrier599 comment5974835583 exposed the exact four-parquet-plus-manifest
  boundary. The publisher excludes the manifest before checking a five-file
  floor. M1 has stale SPX/SPXW extra parquets that mask this defect. A narrow
  same-workspace source-fix fabric leaf changes only the index uploadable count
  to four and adds four/three-file tests, preserving byte and append-only guards.
  No job binding, production floor change or stale-file cleanup occurred.
  Hub reads stay under `hub-ops-wt`; index history
  needs an explicit artifact root because its five outputs are tracked. Its
  publisher's last observed cycle rebuilt and uploaded to R2 but failed the Git
  layout check; no current index process was observed.

The existing M1 machine-Git helper prepared an internal replacement publisher
checkout at23:00:43Z:
`/Users/chriswong/indexgex-push-repo-private.b1-prepared-20261003`,
head `0b093a83e08a1ac903b0b80cde7cc9c277b5aea9`. Its strict sparse configuration,
standalone identity, five tracked artifacts and clean diff passed. It is
**PREPARED_UNBOUND**; the old logical symlink inode335253995 is unchanged, and
no publisher or Git push ran. Receipt:
`/private/tmp/options-alpha-index-publisher-prepare-20261003/receipt.json` on M1.

One full-blob shallow runtime acquisition completed PREPARED_UNBOUND on M1 at
`/Users/chriswong/options-runtime-b1-prepared-20261003`, through the existing
LIVE_FLOW acquisition route and existing M1-local key. The receipt finished at
00:07:24Z with clean standalone HEAD9ee1d9e702de1add7c5e6bd804aaf3f835053db7,
exact f307 engine and free disk183121199104 bytes. No final job is bound; no
runtime data or .env was copied. The canonical M1 receipt is
/private/tmp/b1-runtime-acquisition-20261003/receipt.json.
Independent review permits later same-volume APFS clonefile copies
for the other two standalone roots, with separate git directories, no alternates
or hardlinks, exact commit/clean status and measured disk use. This is one Git
acquisition plus independent filesystem copies, not a shared Git object store.

Recover their exact assigned workspace and writer state through the existing
fabric receipts before any continuation. Source review and protected CI precede
runtime deployment. Keep the already installed live-flow and Chain Heat receipts
separate from natural RTH proof. Durability owner7265 still requires two normal
post-repair engine survivals; publisher7263, correction/broad-writer7193,
campaign integrity and AD1 remain independent gates.

## §2 What will bite you

The enrichment pair's canonical M1 receipt and source rollback are under
`/private/tmp/flow-enrich-cutover-1be595c1-20261003/`; `natural-readback-1.json`
records the first scheduled post-install cycle and authenticated R2 comparison.
Copies are at M2 `/private/tmp/flow-enrich-release-1be595c1/`. The initial public
fallback probe returned403 and is explicitly not acceptance evidence. Accepted
R2 reads used the existing M1 owner environment/client with read-only operation
checks. No credentials or raw event bodies were transferred between hosts.

The Terminal archive on M2 is
`/private/tmp/options-alpha-terminal-ops-8fc1d1a03893/`: archiveSHA
`df8e0de23fb55eb2c87f6e3327b76ef66701e2afbcb56d119aa77c720940d4a9`,
canonical policy digest
`1f2e1bdcc9b72561afe15a5cd79ed6550162498a43f3b2427da5e0e64d6123d5`.
The canonical deploy log is `/private/tmp/options-alpha-terminal-deploy-8fc1d1a0.log`.
Its initial guessed API probes are not contract evidence; use the corrected
`api-contract-readback.json`. The prior789 release stopped before effect on an
unknown ignored bundle;793 fixed that exact allowance without broad exclusions.

Chain Heat's M1 receipt is
`/private/tmp/chainheat-release-7084e176-20261003/cutover-receipt.json`.
Its manifestSHA is `cae122d81e19b001071ab56e8f3f3e5f9dbacef3170c3fe51835314ee8f14685`;
installed plistSHA is `dd9fe923e1a0e87923c414989557c35c2a32f7e52258806597211923d02dfb66`.
That five-file artifact excludes `gex_engine.py`; it proves no B1 installation.

Do not discard the live-flow internal or external rollback locations. The M1
storage-guard incident below preserves a real uncertainty, not a no-deletion claim.
The200GiB full-runner floor and separate fabric/storage guard floors are different
contracts. Small cache inventories did not establish a sufficient safe cleanup.

## §3 What was decided and found

`DSC:M1-STORAGE-GUARD-HELP-MUTATES-20261003` records the actual inspected version,
observed apply launch, process containment and unresolved deletion effect.
The source/runtime boundary and tracked-index-output correction reuse existing
owners. This checkpoint grants no new runtime or statistical authority.

## §4 Not in scope — do not adopt

No new control plane, credentials copied between hosts, fake candidate pair,
manual natural-run substitute, historical restamping, reduced statistical floor,
or hidden partial CPCV success. The completed exact-option evaluator and historical
research package retain their own limited evidence scope; neither proves executable
option economics or promoted alpha in production.
