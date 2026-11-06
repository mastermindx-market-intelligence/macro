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
prs: [7306, 7417, 8201, 8313, 8318, 8322, 8345, 8346, 8350, 8358, 8359, 8360, 8361, 8370, 8374, 8377, 703, 723, 788, 789, 791, 793]
verified:
  - claim: The latest Terminal release is deployed at the accepted merged SHA.
    command: "Canonical terminal-build.sh --target-sha c298fa1b831509dd3dcb7553aa34c03d69dd0084 through M2; fresh VPS Git/marker and HTTP readback."
    result: >
      PR703 merged after all required checks. Deployment returned0; canonical Git
      HEAD and deployment marker equalc298fa1b831509dd3dcb7553aa34c03d69dd0084,
      checkout is clean, and local/public Options responses are200 with that SHA.
      BUILD_ID text matches the prior release and is not a unique release identity.
      Independent authenticated EN/ZH responsive acceptance remains pending.
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
  - claim: B1 corrected gamma source is installed in all three persistent consumers.
    command: "M1 reviewed cutover201064395fff; independent post-install exact-head/hash/plist/input-root/launchctl readback."
    result: >
      At00:53:43.832214Z, indexgex-ops-wt, optionsmatrix-ops-wt and
      optionshub-ops-wt are clean independent roots at201064395fff8e16e958619bf1343eea6d7aca9c.
      Existing labels, schedules, interpreters, inputs and resource settings remain.
      Independent readback passed. No job was manually run or published.
      M1 receipt: /private/tmp/b1-runtime-cutover-201064395fff-20261004/receipt.json.
unverified:
  - claim: The installed B1 consumers have accepted natural publications.
    what_would_verify: "Existing scheduled index, matrix and hub cycles with source-bound artifact/publication receipts. The separate Hub ThetaData EINTR remains unresolved."
  - claim: An FS5 empirical study is eligible or calibration is available.
    what_would_verify: "Separately frozen eligible prospective data and the full scientific admission law; weighted-bin/tie methodology remains unresolved. Source tests and method implementation supply no empirical eligibility."
  - claim: Natural runtime, candidate activation or statistical promotion is accepted.
    what_would_verify: "The existing natural publisher, durability, campaign, correction, AD1, activation and science receipts; source merges and screenshots do not supply them."
decisions: []
discoveries: ["DSC:M1-STORAGE-GUARD-HELP-MUTATES-20261003"]
unresolved:
  - "Prior live acceptance failed on8fc. Terminal703 is now deployed atc298; independent live re-acceptance remains pending."
  - "FS5 methods8377 merged41768751 after299 tests, independent review and required CI. Empirical eligibility and calibration methodology remain separate unresolved gates."
  - "The Oct3 22:30Z qualifying daily run had not appeared at the bounded observation. Delayed scheduling remains possible;23:30Z is an off-regime skip."
  - "AD1 remains INSTALLED_CANARY_ACCEPTED_PRODUCTION_HOLD; required runner-group selected-workflow admission is not available to the current identities, and M1 free space remains below200GiB."
  - "The interrupted M1 storage-guard apply has unresolved deletion effect; preserve its canonical evidence and old runtime/rollback trees."
next_actions:
  - "Preserve source-accepted FS5 methods8377 and its no-artifact guard; no study/calibration/scoring activation is implied."
  - "Observe B1 existing natural cycles after independent installed-source readback PASS; preserve the separate ThetaData EINTR evidence."
  - "Preserve the installed separate index code/artifact roots and internal publisher checkout; retain the old external symlink rollback without traversing it."
  - "Finish independent EN/ZH desktop/tablet/mobile acceptance on deployed Terminal c298fa1b831509dd3dcb7553aa34c03d69dd0084."
  - "Fable owns703 live acceptance,7306 merged-source readback, and8201 current-main raw-clock compatibility at481c0598. Preserve Terminal723 custody; no new numerical or runtime proof is inferred."
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

Updated through 2026-10-04T01:14Z. The earlier observations below remain
historical receipts; this paragraph and the following release updates supersede
older pending-work wording in this checkpoint.

Terminal #703 merged as c298fa1b831509dd3dcb7553aa34c03d69dd0084 after all required
checks. The root canonical M2/VPS executor completed its deployment with rc0;
fresh VPS Git HEAD, clean checkout and deployment marker match that exact SHA.
Both local and public Options responses are HTTP200, and public HTML contains
the release SHA. The executor's own root-path health response was307, which its
contract accepts. BUILD_ID is build-TfctsWXpff2fKS, unchanged textually from the
prior release; use the SHA to discriminate releases. M2 log:
/private/tmp/options-alpha-terminal-deploy-c298fa1b.log. Fable's independent
post-deploy EN/ZH desktop/tablet/mobile acceptance remains pending.

B1 source #8370 merged15af4b7fc1d5216542a4e0970e34f40233975c3d. The discovered
four-parquet-plus-manifest count defect was repaired in #8374, independently
approved5403603041 with74 publisher tests and no skips, then merged normally as
201064395fff8e16e958619bf1343eea6d7aca9c after the required CI gate passed. The
reviewed one-shot M1 cutover completed at00:53:43.832214Z on that exact commit.
All three existing jobs now use independent clean source roots: indexgex-ops-wt,
optionsmatrix-ops-wt and optionshub-ops-wt. No job was manually run or published.
The authoritative M1 receipt is
/private/tmp/b1-runtime-cutover-201064395fff-20261004/receipt.json; independent
post-install readback passed: exact source/hash/clean roots, reviewed plist bytes,
separate Git identities, preserved input/output paths and inactive loaded labels. Original labels, schedules, interpreters and
input authorities remain; index has a separate physical artifact directory,
and only Matrix/Hub ignored outputs use symlinks. The old index-publisher
symlink is preserved as indexgex-push-repo-private.b1-rollback-20261004, without
traversing its external payload. Two APFS copies cost212897792 additional bytes
in the measured preparation interval, with distinct Git directory identities
and no shared Git alternates/hardlinks. This is installed-awaiting-natural-cycles,
not runtime publication acceptance. Before cutover, Hub's17:30PDT cycle exited4
when its existing ThetaData eod path raised EINTR. That path resolves to the
writable external APFS /dev/disk7s1 store; metadata readability does not prove
payload health, and no repair/reroute or corruption inference was made.

FS5 methods #8377 merged as4176875142889a3c650f041f067d1cb954fedf7e at01:12:44Z,
after299 integrated tests, independent exact-source review5403638013, all12 hosted
CI packs, ci-gate and the active main authority passed on reviewed head
e3de558fb9ed24c18b08c0a30d8dbe6598e22278. Normal expected-head squash merge used no
admin override. All nine scoped source/test blobs match the reviewed head;
the CI manifest only picked up other current-main changes and retains the FS5
suites. Both bounded helper/test leaves returned with cleanup proven and zero
residuals. The code executes frozen CPCV, uses native weights, preserves actual
work receipts and fails calibration closed without an FS5 artifact. It creates
no empirical study or scoring activation; unresolved weighted-bin methodology
remains unavailable.

The #7306 source-clock repair at47ef463e36768cac0b6f49c7946f35351a308ba6 received
formal approval5403639706 after independent verification of the original
review's prescribed repair. Historical review5399568840 was normally dismissed
as implemented/superseded, with proof retained. Fable completed the protected
merge as98c67b7d2c5b89670b5e915c34dbc17d899e6df7; source acceptance supplies no
new endpoint repricing, per-cell Greek completeness or production proof.

#8201 current-main integration advanced from7e2779b9 to
481c059818de0e48895c5f38c29ca99c2bf44891 by a non-rewriting merge. Independent
native read-only review passed; both scoped files are unchanged and raw
source_event_* diagnostics remain separate from scientific stage fields.
Fable's owner pack passed431 tests. The root's attempted formal approval through
the current M2 identity was rejected as self-approval; no review was created
and no alternate identity was used to bypass it. Root returned review evidence
to carrier599 comment5975264414. Fable retains ordinary review/CI/merge ownership.
Direct user authorization for native assistance applies to this root session;
it does not require Fable to change its own delegation constraints.

## §1 Remaining work and recoverable source history

The root remains the active orchestrator on Terminal issue599, operation
options-alpha-product-integration-20260917-sol-001. Fable owns independent live
UI acceptance and its existing source carriers. Natural evidence and scientific
admission are separate from implementation and installation.

- Preserve the merged FS5 source and unresolved data/calibration admission gates.
- Finish independent live EN/ZH desktop/tablet/mobile acceptance on Terminal703.
- Observe the already scheduled B1, Chain Heat and live-flow cycles.
- Reconcile campaign runtime/effective quarantine, candidate preconditions and
  actual feed/receipt publication through their existing owners.
- Retain two normal post-repair engine survivals7265, publisher7263 and
  correction/broad-writer7193 durability, plus AD1 admission/capacity as separate
  unearned gates. No manual run may stand in for natural-run acceptance.

The latest failed qualifying scheduled daily run37085692173 (head564c4107)
timed out in options_signal_episode session derivation at its10-minute cap.
Integrity recorded episode failure and skipped episode/campaign publication.
This is addressed in source by #8346 /7fdca240e1cfc9263458d9cd8670d06634806ded,
which reuses validated per-ticker snapshots across receipt validation and both
outcome phases. Its synthetic normalization-count tests are not latency proof.
The cap remains10 minutes. The paired run37088900201 was an off-regime
engine-skipped no-op, not natural acceptance. The Oct3 qualifying22:30Z run had
not appeared at the bounded observation and can still arrive late; Oct4 22:30Z
is the next nominal EDT slot, not proof the overdue slot is cancelled.

For each of the next two real scheduled cycles, select event=schedule with the
ET gate run=true, verify the run head contains7fdca240, and inspect engine success
plus options_signal_episode, options_signal_campaign, options_signal_episode_publish,
options_signal_campaign_publish, options_alpha_candidate_feed and the existing
scripts/ci/options_signal_nightly.sh assert-integrity result. Then read the
source-bound campaign campaigns.jsonl, outcomes.jsonl and checkpoint.json through
their existing publication owner. The candidate builder is already in daily.yml
and config/dag.yml; the sole writer is scripts/publish_options_alpha_candidate_r2.py
to fixed keys options_alpha/candidate_feed.json and
options_alpha/candidate_feed.receipt.json. Without an eligible activation receipt,
inactive-success and no R2/journal work are the expected outcome. Do not invent
a second runtime installation, replay the historical event or dispatch a manual
run as evidence.

The FS5 source workspace remains owned by
options_product_20261003_fs5_prefit_methods, branch
codex/options-alpha-fs5-prefit-methods-20261003. The first worker reached its
turn limit at23:13:47Z and the second timed out at23:59:33Z. Both were reconciled
with cleanup proven and zero residuals; root integrated in the same custody.
The first recovery archive is /private/tmp/fs5-prefit-recovery-20261003-2325,
SHA256d8718f63aa155e48b5215f86506a16d581172a78977d2c480fcc64fe8f301890;
the second is /private/tmp/fs5-prefit-recovery-20261004-0004,
SHA25698fb67ce0786fa8b959927a0e216e65453bd39c8bcba60057684f0b413409565.
Bounded helper and test fabric leaves both returned with cleanup proven.
The final integrated suite passed299 tests before and after the main merge.
Frozen calibration methodology is not invented; unavailable calibration and
absence of an FS5 model artifact are deliberate source behavior.

B1 used the existing source-root acquisition route with M1-local credentials.
The original prepared acquisition was head9ee1d9e702de1add7c5e6bd804aaf3f835053db7
at00:07:24Z; its preparation receipt is
/private/tmp/b1-runtime-acquisition-20261003/receipt.json. The cutover later
fetched exact qualified201064 and installed the three independent roots;
the cutover receipt supersedes PREPARED_UNBOUND claims. The internal publisher
prepared at23:00:43Z was atomically bound at its existing logical path. Its old
external symlink is preserved as indexgex-push-repo-private.b1-rollback-20261004.
No publisher push or job kickstart was performed.

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
