# Options Alpha runtime root causes and bounded recovery

Date: 2026-09-10. Parent: WS:OPTIONS-ALPHA-INTELLIGENCE-RECOVERY. Same research carrier #7027; records only. No deployment, production code repair, canonical data mutation, model fitting or trading promotion.

## Capability delta

The previous census established 74589 learning events with zero measured microstructure, but did not locate the first absent boundary. This continuation locates an upstream installed-source gap and independently diagnoses the nightly publication/backlog failures. The next action is no longer another initial census or generic trace proposal: it is existing-owner controlled adoption of the accepted measured implementation, with the separate source-integrity and publication holds below.

Protected Mastermind Skillpack INDEX/COLD_START/RECONCILE_STATE/CLOSEOUT: `964bd8e7b30c91e5e83caee0ba37513ba7d07e70`, compatible1.0.1/bootstrap1. Analytical Macro: `6e1fb2ab35f68bbaf3695ffee5fe5ba268e46bae`. Current OA/DNR/source-writer laws remain controlling. This record is not a worker commission or runtime admission.

## 1. Scheduled source predates the accepted measurement code

Native read on authorized `admins-Mini-652.ts.net lan` found `com.mastermind.liveflow` bound to `~/liveflow-ops-wt`, using its existing wrapper/interpreter and `scripts.live_flow_poller --rth-only`. The checkout is branch main at `edd07d7324534c81341ebcc4683173714c3b8509`, an August20 revision. Relevant tracked producer/poller/collector source paths have no local differences from that checkout.

Its `engine/live_flow.py` is70934bytes, Git blob `89138ed09ad9e16bc0963dcd02dc592d6ca5b231`, SHA256 `d1db3d21d70ba9898d564927a2e960a9a67e6755198ca89b43f81ab5aec8dfe0`. The measured helper `_coalesce_nbbo_microstructure` is absent. An independent GitHub read of the same revision returned the matching blob.

Accepted measurement PR6585 merged2026-08-30T00:58:45Z as `dbd654edb0fb47449b969b7dcb4fbafc2e0fe3ef`, with source acceptance BUILT_NOT_PROVEN and natural-RTH proof owed. Its feature is not in this scheduled checkout. Do not reimplement it or assume a merge installed it.

The September10 local stage contains545703bytes/1140records:570decisions and570availability receipts. SHA256 `7fcf4764d0694680cfddc4fdb2975f58dab1f16438aa089d8a3a492ea2810ed9`. None of570events carries the microstructure block. The local `published.json` objects entry for this date records the same size/digest. Thus the absence is already present before ML flattening.

This is scheduled-binding/source/today's-artifact evidence. The read was after regular hours, not a live-process imported-module attestation, and no fresh remote-object GET was performed. It does not characterize every possible fleet producer or establish that one installation will fix all downstream faults.

## 2. Actual event age is material to entry quality

Across the570events, latest coalesced print to durable availability is:

| Statistic | Seconds |
|---|---:|
| minimum |59.867984|
| median |336.423454|
| p90 |939.5985552|
| p95 |1679.30462485|
| maximum |4295.176975|

368events exceed300seconds;93exceed600seconds. All checked clock components are nonnegative. There are65distinct decision timestamps; these are correlated event/batch observations from one session, not independent latency trials.

Separate medians: print-to-observed59.577793seconds; observed-to-decision208.087371; decision-to-available26.7210325. Quantiles do not add. This is event age, not quote age, pure network delay or subscriber/browser delivery. A coalesced event can contain earlier prints. No particular CPU, provider or fsync cause was independently profiled.

An informative event can arrive after the original entry window expires. Preserve event, availability, publication and display clocks; assess any entry on available information, not the old print. Do not weaken fsync/replay safeguards to improve an unexplained timing component. No universal stale threshold or trading rule is selected here.

## 3. Episode creation succeeds; publication hits a physical limit

GitHub run34421411115, enginejob102735434183, concluded failure. Workflow-trigger head is `61cb600c966a7762fcfbe9ea77bfcf48ce017e5c`. Engine logs record checkout `2c9a2d35ba0dd38618f59a2fadc80b6815ec5281`, followed by an already-up-to-date pull. The relevant campaign and narrow-publisher blobs match at that checkout, workflow head and analytical pin: `b61ea1d1ba20df00c247e0d99829c20af1be30aa` and `f06f1eac16434403818da3a53021b70e95ca3427`.

The decoded gh-log text is39090lines, SHA256 `1f0b778f3e1234f40bce588d36c50741a6fd2ec62ffc4c8463a8cd8d2e11f7e7`. Whole logs/environment/credentials are not copied into this record.

At09:13:56Z the episode builder reports `ok=true`,1709new episodes,11350valid total,1283new H+60 outcomes and5314new session outcomes. At09:24:39Z, GitHub rejects `data/options_signal_episode/outcomes_session.jsonl` as112.71MB against its logged100.00MB threshold, errorGH001. Official ordinary-Git policy blocks files over100MiB; retain the log's display units rather than inventing a precise unmeasured byte count.

The publisher retries the unchanged size rejection12times, exhausting its attempt budget at09:31:08Z. This cannot solve an oversized blob. It is not observed branch contention or a cherry-pick conflict.

The terminal integrity gate correctly records episode-build success, episode-publication failure, campaign-build failure and campaign-publication skipped, then fails. Narrow candidate isolation and the broad-publisher exclusion remain valuable safeguards and must survive the repair.

A bounded immediate change is size preflight and permanent-rejection handling under the existing publisher/retry owners. That removes wasted retries but does not publish the backlog. The growing logical store needs an approved physical representation capable of growth, preserving the same owner, ordered bytes, IDs and prefix law. Compare immutable bounded segments in the existing classified object store plus compact manifest/checkpoint with properly supported alternatives. Do not truncate history, rewrite expected hashes, force-push, or treat LFS as a no-review drop-in migration. This remains a proposal, not an installed new store.

## 4. Campaign timeout and repeated prefix hashing

The same run starts campaign accrual at09:13:56Z and times out after10minutes at09:24:08Z. Parsing/semantic-validation versus hashing costs have not been separated by a full runtime profile.

Source `engine/options_signal_campaign.py` caches prefix snapshot objects but recomputes their digest through `LedgerSnapshot.sha256` and `_receipt`. Historical campaign and outcome checks verify a receipt and construct an expected payload, repeating the hash. `_plan` performs historical semantic validation before `_verify_checkpoint`.

Actual pinned histories:8385campaign records with10distinct episode prefixes;28423campaign outcomes with24distinct outcome prefixes;36808historical receipt references but34distinct path/prefix pairs.

A complete traversal doing the two identified hashes per reference would process2045035581388bytes (about2.045TB). Hashing once per distinct prefix processes607741148bytes; a single ordered scan of the three source files processes131370914bytes plus digest-state copies. This is a static work model, NOT a measured full-run speedup or proof that the failing invocation hashed that entire volume. A mismatch/timeout can stop it earlier; parsing, schema validation, I/O, new rows and checkpoint work are excluded.

Invocation-local digest reuse bound to exact immutable snapshot/count, or a one-pass prefix-digest calculation, can eliminate repeated byte work without weakening validation. Preserve every schema, economic, chronology, source-membership, duplication and authority check. A persistent trust cache or a path/count-only cache is not equivalent.

## 5. Broader validation exposes two real source-prefix disagreements

The one-pass diagnostic checked all34distinct commitments:32match and2do not. Direct prefix hashing independently reproduced both. All three current source files have terminal LF and zero byte differences under canonical JSON re-encoding (episodes9641rows; H+60 7843; session30327), so the discrepancy is not resolved by silently normalizing equivalent JSON.

| Source | Prefix rows | Expected SHA256 | Observed SHA256 |
|---|---:|---|---|
| outcomes_h60.jsonl |6525|129b56d4c457dbc2789a33e901367f84735d461a8f67790c6661bc2189ccb96c|73eaf4b68cffb8239b1c9f7d5b7331ca4d5dc9a83169a1c80bf0062457d2968c|
| outcomes_session.jsonl |23771|6b95148d169de919bfb9cfa5e11bcb4fc842e8bc4e9fce0584cae827aa3c604e|ed8be51f82f488caeb826a1a7e6f6f6cd43eeca3af6e377dd01325cd3f489bf3|

The earlier8872episode-prefix match remains true; that narrow check never established every outcome prefix. All10episode prefixes match. Do not upgrade the prior valid episode-prefix observation to whole-checkpoint integrity.

The correct response is preserve current bytes and expected claims, investigate the first authoritative divergence under the existing source owner, and keep advancement held. Do not rewrite the expected hash merely to pass. The cause of the historical disagreement is not established; a bounded historical-source read was platform-blocked and not rerouted.

Move inexpensive checkpoint/prefix refusal earlier where accepted behavior is unchanged. Faster validation should surface these mismatches sooner, not accept them. A successful optimization must retain these exact negative cases as well as output equivalence on valid inputs.

## 6. Correct interpretation of green status

Separate DST-paired run34424807677 has a successful time gate and skipped engine. That is legitimate scheduler behavior, not evidence accrual. A continued step can also have raw outcome failure but conclusion success; official GitHub documentation distinguishes them. The inspected final integrity gate fails correctly. Do not report the whole failed run as green or use a successful skipped run as its replacement evidence.

Operational status should bind installed source, last real measured event, accepted publication, consumed prefix and visible consumer state. A fresh outer repository commit or workflow badge is not equivalent to those capabilities.

## 7. Bounded recovery sequence

A. Existing deployment/source owner qualifies controlled adoption of a compatible immutable release containing6585 on the observed checkout, retains original state/rollback and proves one natural new event through the intended consumer. No blind latest pull, old-event augmentation, artificial event, lowered floor or scoring change. State version5 already exists in the inspected deployment; do not reset it by assumption.

B. Existing episode/campaign owners reconcile the two outcome-prefix disagreements. Preserve original/expected evidence and establish the lawful restoration or explicit reviewed amendment before advancing. No expected-hash overwrite or indiscriminate corruption claim.

C. Existing campaign source owner introduces exact-snapshot digest reuse and early cheap integrity preflight with unchanged full semantic validation. Require accepted-byte equivalence, both actual mismatch refusals, and realistic full-run resource proof; the static cost ratio is not performance acceptance.

D. Existing publication owners stop retrying permanent size rejection and qualify a scalable physical representation under the same logical authority. Require exact legacy-prefix round-trip, missing/corrupt segment refusal, coherent publication, crash recovery, consumer restore and natural acceptance. Upload success is not consumer proof.

These are separately bounded capabilities, not one giant PR or a new control plane. Independent read/source work can proceed only with genuinely disjoint ownership and changed paths. AD-1T2, OA-1C, OA-3/4/5 and DNR gates remain intact.

The first product vertical remains one real campaign with understandable measured evidence, uncertainty, original availability, source-backed planning and explicit entry-expired/quote-unavailable states in the existing Terminal mount. The M1/M2/M3 model proposals remain SPEC_ONLY; deployment and data recovery do not establish an economic edge.

## Verification, artifacts and limits

Native aggregate receipt observed2026-09-10T23:05:09.993099Z, SHA256 `6b6496f459b93bf8f389f3fc0b7b55311f3d2991547a0703666c3381ff584d60`, is reproduced byte-identically in the delivered research packet. Full analysis, bounded acceptance, selected log events and original read-only prefix helper/tests are retained there; raw source market rows, fonts, credentials and complete logs are excluded.

18 diagnostic tests passed, including a synthetic Git CLI test with unchanged HEAD/tree. Helper SHA256 `5eaee3b740d9764272ab6d965b63725a5b2a4e357f066212ae44c37761549185`; test source `4674402afa113dee8b4a8a790df489e8d23e7632992cfe7a5014b3db7f17b70e`. The equivalent one-pass algorithm ran on actual native source bytes with direct-hash confirmation. The packaged CLI itself did NOT run on actual native data: its native transfer append was blocked after the first30lines, and was neither retried nor executed. Do not conflate the two proofs.

No whole-repository AgentOS validation, independent release review, deployment, provider invocation, workflow retry/cancel, canonical data change, model fit or trade is claimed. This research does not close the full Options Alpha program.

Primary external references: GitHub ordinary-file limits at https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github and outcome/conclusion semantics at https://docs.github.com/en/actions/reference/workflows-and-actions/contexts. Own evidence is bound to the exact source/PR/run identities above, not to mutable status descriptions.
