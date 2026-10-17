# Options Alpha actual-data census and recovery findings

Date: 2026-09-10. Parent: WS:OPTIONS-ALPHA-INTELLIGENCE-RECOVERY. Carrier: existing research draft #7027. Records-only research continuation; no runtime, model or trading promotion.

## Capability delta

The prior Nightglass durability study supplied a tested auditor but had not inspected the complete original Parquet population. This continuation ran that auditor against actual committed data and joined the existing episode/grade records. The next action is no longer to prepare or run the initial census: it is to identify and repair the first demonstrated information-loss boundary under the existing source owner.

The analytical Macro pin is `d675bbece0848e8587e4070b576e7585e02b5a19`. Protected Mastermind Skillpack INDEX/COLD_START/RECONCILE_STATE/CLOSEOUT were atomically read at `dd553d1b0b8eed9511da2d3d5ec02cc9cd8edca1`, compatible v1.0.1/bootstrap1. Prior Nightglass model proposals remain SPEC_ONLY/unadmitted.

## Source identity and method

GitHub directory metadata supplied path, size and blob identity. The authorized Mini's checked-out worktree was older, but its local object database already contained the current objects. Read-only `git cat-file blob` retrieved them; Git SHA-1 and SHA-256 were independently verified. No fetch/reset/checkout, canonical data mutation, provider request, model fit or runtime restart was used for the successful census.

| Source at analytical pin | Git blob | Bytes | Rows |
|---|---|---:|---:|
| data/flow_signals/ledger.parquet | e8dc48d53519cf1cae40c3a48f9f06c71e943055 | 3574019 | 74589 |
| data/flow_signals/grades.parquet | b8798f058459e0b8f892168cc521fc55ab9b872e | 2357318 | 74589 |
| data/options_signal_episode/episodes.jsonl | 79277635aeb5578a346727e9e2cb34be6d19bcfe | 15013207 | 9641 |

SHA-256, respectively:

- ledger: `072ee2031cf2c1f75d94abee51f2ddb45ac0f32918f985868a1f32f7471459e9`;
- grades: `137eaeb0d151c1d9dcfdfc72a58a8b1152c5fdbdab02cb8fe26a69761698d772`;
- episodes: `20120ddeff5983248ec404afaa65d3414c36ed1011936638c84e4ada52f50940`.

The compact host aggregate receipt was read back at 2026-09-10T21:08:26.668709Z. The successful Mini REPLs and both auditor processes exited zero. No source binaries or individual market rows are published in this document or the research packet.

## 1. The current learner has zero measured-microstructure rows

The ledger contains 74589 unique, nonempty event IDs, 47 columns and 33 sessions through September9. Every microstructure schema value and every one of the 18 measured count/premium/coverage/location/spread/quote-age/quote-size fields is null. `vol_gt_oi_ratio` and `premium_z` are also all null. This includes 4375 rows dated August31–September9, after OA-1T's August30 implementation merge.

All trade and ingestion timestamps parse timezone-aware and no ingestion precedes the stored trade timestamp. There are no duplicate/conflicting IDs. Those successes do not establish usable measurements: the auditor examines zero recognized measurement rows, so zero relation errors is not a healthy-measurements result.

The prior working-copy ledger held72880 rows throughSeptember4 (blob `6a83873c1c3eb72dbb1f84e818819643bb09e5f4`, SHA-256 `941b57297f30ad5671e3cca935b7dd9033f942c1caed2232992ad014326194cf`). All72880 rows remained equal across shared columns after ID alignment to the current object. The additional1709 rows are September8's898 and September9's811. This proves append-preservation for those compared snapshots, not the current live emitter's health.

The trainer's `_assert_live_feed_measured_features` in `scripts/ops_train_flow_score.py`, blob `3b05edb11778be70e060d2a20c351202a06c172e`, explicitly refuses declared measured fields that are missing/all-null. The observed ledger cannot satisfy that presence guard for its measured features. No trainer was run, and removing the guard or imputing fabricated values is not a repair.

The destination condition is established. The exact first failing boundary among installed runtime revision, runtime path, measurement, event staging, publication, schema recognition and harvesting is NOT established. A code merge is not a natural-session measurement receipt.

## 2. Existing episodes recover original provenance for8711 rows

The9641 episode source IDs are unique. Every episode declares `live_flow.event_stage/v1`, exact availability and no option-quote-outcome eligibility. Independently checked causal clock ordering `event_time <= observed_at <= decision_at <= available_at` has zero violations.

An exact one-to-one source_event_id/event_id join matches8711 ML records. Root, session, right, expiry, strike, normalized event time, premium and contract quantity all agree. Raw string differences from equivalent Z/+00:00 formatting were normalized before judging clock equality; they are not8711 timestamp defects.

All8711 matches have observed/decision/available clocks and selection rule/floor/root-class values. OI vintage is present for7868 and absent for843. The flattened learner omitted these fields; they were not necessarily destroyed everywhere.

A reviewed derived join can preserve that evidence without rewriting the immutable keep-first ML rows. It cannot reconstruct missing NBBO, prove opening intent, or grant training/trading authority. All these episode proxy-outcome restrictions remain controlling.

## 3. The consumer frontiers differ

There are930 episode IDs absent from ML:384 onAugust10,7 onAugust20 and539 onSeptember1. These are bounded reconciliation candidates, not automatically930 eligible lost training examples. Declared populations/source versions must be reconciled before any addition to a frozen cohort.

Conversely,65878 current ML IDs have no episode match. Much of that history predates the episode program; do not mislabel the entire unmatched population as an outage. The episode artifact at this same current Git pin endsSeptember4 while the ML artifact reachesSeptember9.

The campaign checkpoint consumes8872 episode rows. SHA-256 of those exact newline-preserved bytes matches its declared `577173f25929afeb245e9a432d69fb7d8e204ccd4d4028ad6273eca3addacab5`. The unconsumed769-row suffix is exactlySeptember4. This is a coherent older prefix, not detected corruption. The checkpoint declares8385 campaign rows and28423 outcomes, but this audit did not independently validate every output byte.

Thus the committed frontiers are ML throughSeptember9, episodes throughSeptember4, and the campaign's consumed episode prefix throughSeptember3. A recent broad repository commit cannot make all constituent evidence families current.

The current `ops/LIVE_FLOW_RUNBOOK.md`, blob `2352cbc5fbac9b9a1e7f22cc8fe6c39c8432cd15`, specifies date-keyed decision/availability stages, exact publication/prefix receipts and64-session discovery/catch-up. The older FS harvester uses capped feed/archive projections and a48-hour harvest window. These are distinct source contracts. Recovery through the existing stage/episode owner is a concrete hypothesis, not permission to replace the frozen FS population or create another collector.

## 4. A documented legacy clock cohort survives in stored history

The50969 rows throughJuly29 have UTC-labeled session ranges around09:30–16:00. FromJuly30 onward the observed summer ranges shift to approximately13:30–20:00. Merely checking timezone-aware types cannot catch the earlier semantic defect.

Macro PR#4017 merged as `f8f5a90af90e6d7830cf53e1c222298fd9db966e` at2026-07-30T06:07:06Z. Its exact receipt documents the old event path appending Z directly to naive New York wall time and explicitly leaves historical archives unchanged. The actual stored-data transition agrees with that source history.

The pre-fix cohort is68.33% of this ledger. Intraday reuse needs source-version-bound clock adjudication, not a blind fixed-hour shift, in-place rewrite, or an assumption that constant harvested detector_version=live_feed_v1 proves identical emission semantics. Preserve original and adjudicated views and mark ambiguity.

This does not automatically invalidate the underlying daily-reference grades: the existing grader uses session_date and a subsequent daily bar, not the event's intraday clock. Eligibility is task-specific; retain useful evidence without presenting it as a valid intraday decision receipt.

## 5. The recurring54 missing-price grades all belong to SLV

The current grade table matches every ML ID with no duplicates:67473 rows are `ok`,7062 `not_yet_matured`, and54 `no_price_data`. Every missing-price row is SLV. A successful pinned `git ls-tree` found no `data/yahoo/SLV.parquet` entry. The grader's `_load_close` reads that Yahoo close-store family (`engine/flow_signals_grade.py`, blob `14afdd90e11f5d22f60ce3ed376fe70c5013db4c`). This localizes the committed source gap; it does not establish what an uninspected runtime cache holds.

The follow-up is source-owner reconciliation of SLV availability/mapping and lawful retry through the existing grader, not a broad grader rewrite, invented zero returns, silent exclusions or an unreviewed provider/price-basis substitution.

A separate target-completeness gap:440 `ok` rows lack their primary SPY-relative result. Five-day underlying returns number39596 versus39492 excess values;21-day returns number27877 versus27541 excess values. The completed underlying count67473 is not a guarantee that every downstream target component exists.

`prem_touch_50` is null for all74589 records. These are direction-agnostic underlying daily references, not exact-option P&L, subscriber fills or evidence of a profitable options strategy. No predictive evaluation was performed.

## Capability and model implications

Use a task-specific eligibility view rather than one dataset-size boast. The basic event history, declared daily labels, exact episode provenance, current measured microstructure and executable option outcomes have different denominators. For this ledger the measured-model entrance population is zero, while some history remains useful for its declared descriptive/daily purposes.

M1 must first receive real measurements and eligible calibration labels. M2 must bind original availability, entry geometry and explicit deadline/outcome semantics. M3 needs the actual option/quantity/quote path, not a substituted equity return. The prior three-model blueprint remains a research proposal; current OA/DNR restrictions are unchanged.

## One bounded next capability

Under the current sole-writer source/runtime owner, identify the installed revision and trace one naturally occurring qualifying event through source frame, measurement output, immutable decision/availability stage, publication receipt, harvester and intended candidate consumer. Record the same identity/schema/clocks at every boundary and repair only the first demonstrated loss in a separately authorized bounded wave.

No artificial event, lowered premium floor, retired-fleet rearm, historical replay relabeled live, NaN filling or silent population change can satisfy that proof. No new event/campaign ledger, generic super-score, scheduler, Issue Desk or control plane is needed.

In parallel, research-only scope can reconcile the8711 provenance joins,930 unmatched episode IDs,769 valid-prefix suffix, legacy clock cohort and SLV/440 target-coverage gaps under their existing owners. A permissioned exchange-labeled panel can improve measurement evaluation later; buying competitor access is not a prerequisite for fixing these measured gaps.

After the existing OA gates clear, the first visible vertical should show one real campaign with understandable evidence, uncertainty, original availability, legitimate structural planning and clear entry-expired/quote-unavailable states. A fabricated probability is unnecessary for that product capability.

## Verification and limitations

The unchanged auditor SHA-256 is `cb9eff21caec93094868e25d347aa45b2657d9ad53662f39cef8d9f8a03b6151`. Its current-object run exited0 in4.21 seconds. The73 existing research tests were rerun and passed. A repackaging attempt initially omitted the detached own-source helper directory; the failure and subsequent complete passing run are retained. These are not73 new production tests or an alpha backtest.

The separate user-delivered research packet contains the full aggregate census JSON, reproduced host receipt, read-only audit recipe, existing auditor/tests and fuller recovery report. Raw market rows/binaries, credentials, vendor code and font files are excluded. The successful Mini temporary files are isolated outside the checkout with restricted raw-data permissions. An earlier MacStudio REPL produced no accepted result, became unresponsive, and its exit request timed out; shutdown remains unconfirmed.

This continuation changes no live source, checkpoint, model, execution permission or statistical gate. It establishes the pinned committed-data census, not current production health or the exact runtime cause. Repository-wide AgentOS validation, independent review and hosted CI success are not claimed. Keep this carrier draft; completion of research does not complete Options Alpha.
