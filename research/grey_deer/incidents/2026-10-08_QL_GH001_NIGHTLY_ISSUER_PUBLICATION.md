# Grey Deer incident: QLedger GH001 blocked the October 8 US nightly publication

**Date observed:** 2026-10-08 UTC.  
**Status:** VERIFIED PUBLICATION FAILURE / NO SHIPPED REPAIR.  
**Organizational owner:** Existing `WS:GREY-DEER-RISK-INTELLIGENCE` / MAS-258, with QLedger and GitHub delivery/source owners retaining their native authority.  
**Protected procedure pin:** Mastermind `732cf7be88e7159b4995a8885fbd381cd1484e3e` (Skillpack v1.0.1 / bootstrap major 1).  
**Macro investigation pin:** `e80339cb921ac6851ae972775f7e2d784bf62007`.  
**Parent research and masterplan:** Macro #8648, `research/grey_deer/ALERTFUL_RISK_RADAR_MASTERPLAN_2026-10-08.md`.

## What is proven

1. The actual EDT daily scheduled workflow run **37716729584** (`2026-10-08T02:12:30Z`) completed FAILURE. Within the `engine` job **113158877653**, “run regime engine + build dashboard + daily brief” reported SUCCESS. The earlier **step 46, “checkpoint core engine outputs to main,” displayed SUCCESS only because the workflow sets `continue-on-error: true`**: that step's own logs at 13:11–13:21 UTC contain **six** GH001 rejected pushes, exit code 1 and the explicit runner-only lost-on-checkout warning. Later **step 151, “commit engine outputs,” FAILED** with the same GH001. Neither checkpoint demonstrated durable publication. This is not proof of a complete/published nightly merely because earlier calculation steps succeeded.
2. The failed job's own GitHub push output repeatedly reported:
   `remote: error: File data/qledger/claims.jsonl is 101.92 MB; this exceeds GitHub's file size limit of 100.00 MB`
   and `GH001: Large files detected`. First checkpoint: **six** failed push attempts exhausted its 600-second retry budget at 13:21:02 UTC, but the surrounding step appeared SUCCESS due its `continue-on-error` wrapper. Final checkpoint: **five** additional failed push attempts exhausted 600 seconds at 14:29:53 UTC, and the step was FAILURE. Both printed the runner-only forward-ledger/site loss warning. There is no accepted publication receipt for either. This is an especially dangerous **false-green step-status** failure mode. The later OIP PIT fail-closed step also failed. This is a **hard, non-contention publication failure**; rebasing/retrying an unchanged oversized blob cannot repair it.
3. The same date's alternate EST cron invocation **37719685481** appeared SUCCESS at the workflow level, but its `et_gate` succeeded by **skipping the collect and engine jobs** (expected DST disambiguation). It is *not* independent proof that a second US nightly succeeded.
4. At pinned Macro main, `data/qledger/claims.jsonl` is 103,453,992 bytes, Git blob `c2564bd5d2a9157a21b2da2160498d9c5469cc47` (near GitHub's maximum permitted blob size). Its file is multi-writer. `.gitattributes` uses `merge=union` expressly to avoid dropping concurrent QLedger claims; hourly White House, regional and nightly lanes can all append. A simple `git reset`, blind exclusion from the broad commit, truncate, force-push or replacement rewrite would risk losing first-writer evidence and is **not authorized**.
5. At the same pin, `data/regime/latest.json` has Risk Radar as-of **2026-10-07**, state `caution`, pre-gate state `risk-off`, pressure score **77.1**, and no `forecast_issue` receipt in its latest snapshot. `site/rr_banner.json` has as-of **2026-10-07** and `alert:null`. The append-only `data/risk_radar/forward_log.jsonl` inspected at this pin ends at **2026-10-06**, with issue receipt at `2026-10-07T05:22:40+00:00`. Therefore **no matching first-issued Oct 7 forward row is present in this pinned Git snapshot**.
6. That mismatch does NOT independently prove the Oct 7 result was never computed, that the GH001 was the sole reason for an absent issuer row, that it was never published on any other storage surface, or that no user received an alert on a different delivery channel. The workflow explicitly shows calculation success and final publication failure; the required continuity and clock forensic work remains a separate requirement.

## Why this is risk-system critical

A live quote or off-lane re-render can show a newer **settled** Risk Radar state than the first-write nightly issuer ledger has durably recorded. The legacy banner only triggers for a *gated* risk-off state; thus it remains null while this Oct 7 radar reports severe ungated pressure. The system's financial claim and its delivery/accountability proof are on different clocks, and a shared oversized QLedger blob can strand their nightly publication.

This is a **cross-workstream blocker**. It must be resolved through the existing QLedger + nightly delivery owners, not by creating a new risk ledger, notification service or publishing queue.

## Additional VERIFIED finding: repeated same-day heartbeat erases a stalled alert

Existing `scripts/check_ledger_advance.py` is *already* the risk-forward-ledger liveness detector. Its `run_check` compares newest ledger as-of with its prior committed checkpoint and records `stalled_since`. It deduplicates alerts when `last_check_date == today`. But the same-day no-alert branch **unconditionally assigns `stalled_since=None`**, even when the ledger has not advanced and the prior state contains a genuine stall. This is a source and actual-state problem, not a proposal for a new watcher.

Immutable Git snapshots demonstrate the defect on the real risk ledger path:

| Heartbeat source commit | Actual UTC update | Risk forward ledger as-of | last_check_date | stalled_since |
|---|---|---|---|---|
| `f2e831e534c3` | 2026-10-07 10:30:14Z | 2026-10-06 | Oct 7 | null |
| `49418b034729` | 2026-10-08 15:05:48Z | 2026-10-06 | Oct 8 | **2026-10-07** |
| `e65335239332` | 2026-10-08 16:17:04Z | 2026-10-06 | Oct 8 | **null** |

The **same as-of was unchanged**, and the second heartbeat reset the existing stall evidence. Independent temporary-root execution of the shipped `run_check` with the previous checked state reproduced `old_stalled_since=2026-10-07`, `new_stalled_since=None`, `same_day_result_count=0`. Its unit suite documents same-day no-duplicate alerts but does not exercise preservation of an already open `stalled_since`.

**Narrow repair proposal for the existing heartbeat owner**: preserve the earlier `stalled_since` on same-day unchanged or regressed `curr_asof`; clear it only on a genuine forward advance or explicitly qualified resolution. Keep no-duplicate emission behavior. Red-first regression: a first run on Oct 8 detects a frozen Oct6 risk ledger; a second same-day run must not send a duplicate alert **and** must preserve the first stall's age; a genuine newer as-of must clear it. Add an out-of-order and missing-file case and confirm the existing Ops Alert Command Center semantic path remains unchanged.

**Wider proof gap**: the heartbeat only compares to *prior as-of*, not authoritative expected completed NYSE session, and its workflow passes `--render-happened` unconditionally, rather than validating an exact successful git push receipt. It is also fail-open by contract. An outdated-but-advancing ledger may therefore look healthy without proving today's intended issue, and a complete publication failure can be mistaken for a republish. These are proposed consumer-liveness repairs, not grounds to add a new monitoring service or change alert architecture without the relevant owner.

The heartbeat incident is **independent** of QLedger GH001: correcting heartbeat state does not make an oversized QLedger blob publishable, and partitioning QLedger alone does not cure the same-day stall-erasure. Both must be acceptance-tested.

## Existing contracts and collision boundaries

- `engine/qledger.py::register` and `register_batch` both append to one `data/qledger/claims.jsonl`; `load_claims` reads the same file. The grade/control/evidence-clock/read paths and other consumers use the same logical ledger.
- More than twenty non-test files have direct QLedger path references, including `engine/neuralweb/query.py`, `engine/intelligence_registry.py`, `scripts/build_intelligence_registry.py`, auditing, graders and nightly scripts. There are at least several concurrent writer workflows. **Do not assume a one-file rename makes the fleet shard-aware.**
- Existing Macro PR **#8042** (head `eed26eac59fdc375504d8bcd32b403e40ee30a2f`, open) addresses *quadratic per-row ledger scans* via `register_batch`; its documented observation already placed the file around 95 MB. That improves cost, **not GitHub's hard per-file limit**. Do not mislabel it as a completed size migration or displace its incumbent writer.
- The closed source-law prohibits duplicate event/forecast/episode stores. Any segmentation must be versioned **inside the existing QLedger owner** and preserve first-claim wins, claims/grading identity, source clocks, append-only semantics, multiwriter union and every existing consumer.

## Recommended technical work, subject to QLedger-owner admission

**R0 — contain loss and inspect outstanding effects (read-only first).** Reconcile run 37716729584 exact commits/checkpoint receipts and whether any runner-only data is still available under the original CI owner. Do not re-run the failed workflow, recover a runner by force, or fabricate missing first-issue records. Record Oct 7 as `ISSUE_NOT_FOUND_IN_PINNED_GIT` until a legitimate first-writer receipt is recovered. Inspect all active QLedger source carriers/leases before assigning a storage modifier.

**R1 — freeze ledger continuity.** Inventory every direct reader/writer/validator of `claims.jsonl`, with tests and `.gitattributes` merge semantics. Choose one QLedger-native versioned partition/manifest representation that preserves the whole historical ledger; define effective cutover, deterministic per-claim partition routing, dedupe on union across shards, late/out-of-order rows, idempotent interrupted jobs, multiwriter races, downstream exports, rollback and reconstruction checks. No new parallel authoritative store. Do not silently drop claims or rely on a GitHub-LFS pointer without entitlement, runner/consumer and ongoing-cost proof.

**R2 — write migration tests before live cutover.** A complete frozen baseline fingerprint (ordered normalized claim_ids, first-known identities, row counts, rejected/open status, grade linking, family control start clocks) must match the partitioned reader's output. Test duplicate claims across old/new shards, concurrent two-writer merge, missing/corrupt shard, reader mixed-version, old-runner append after cutover, git publish >100 MB guard, and replay effects. Ship read-compatible consumers before modifying writers; coordinate all admitted writer job versions.

**R3 — safely restore publication.** Use existing nightly/GitHub owner with a preflight refusing to stage an oversized file; classify a literal GH001 oversize as non-retryable instead of consuming an unchanged 600-second push loop. Crucially, **the early checkpoint's `continue-on-error` status must not be treated as publication success**: preserve a separate exact pushed-SHA / required-artifact acknowledgment or explicit nonterminal publication-defect result under the incumbent workflow owner. Restore nightly issuer and relevant site output only after the canonical QLedger writer has a durable safe path. Preserve broad renderer/index safety and no alternate publish plane. A narrow risk-artifact checkpoint may be studied only if it composes the accepted existing owner without bypassing first-write, QLedger, or source-custody rules.

**R4 — real release proof.** Demonstrate exact merged source and named live runner: ordinary QLedger claim registration/grading across old and new partitions; successfully completed, *non-skipped* daily collect+engine; a genuine new Risk Radar first-writer receipt for the correct settled session; corresponding published artifact and explicit banner/suppression decision; authenticated actual Macro/Terminal delivery when #8132/GD-8A safety and source gates clear. Control alarms must fire on later issuer/publisher clock mismatch. A green schedule `et_gate` alone is not acceptance.

## Bounded independent artifact created in this continuation

A **read-only** script `scripts/research/risk_warning_issue_artifact_audit.py` and regression `tests/test_risk_warning_issue_artifact_audit.py` were developed **only in the already admitted native Macro workspace**:

- Operation: `gd-issued-warning-artifact-audit-20261008`, lane `web`.
- Exact base: `e80339cb921ac6851ae972775f7e2d784bf62007`.
- Workspace: `/Volumes/Mastermind/agent-workspaces/macro/web/gd-issued-warning-artifact-audit-20261008`.
- Source blob `3bd56b3097041ff09751e137d31a632d15237049`; regression blob `175a0fb3cfba2882151530f6393afd73fad78929`.
- **38 native tests passed**; red-first tests reproduced original absence/overflow/mismatch defects before isolated fixes. Script compile and diff check passed.
- Source-pinned read-only audit: Oct 5/6 both `ISSUED_PRECONFIRMATION_CONFLICT` (with different-session latest banner, so **no historic-delivery claim**); Oct 7 `ISSUE_NOT_FOUND` and `SAME_SESSION_ALERT_NULL`, with `delivery_evidence=NOT_EXAMINED`.
- The script never executes the existing warning publisher, collects quotes, sends notifications, writes the ledgers, promotes an ungated state or grants trading permissions.
- The managed workspace owner reports `PRESERVED_DIRTY` and `WORKSPACE_ONLY_CHANGES_PRESENT`. The available Studio typed publication status refused with `TYPED_GIT_PRECHECK_REFUSED / NOT_APPLIED`. **Code is not canonically published**; do not switch carriers/tools/accounts to force its publication or claim a PR exists. Preserve and reconcile this exact workspace before any later source publication under approved original-carrier admission.

## Effects, decision, next action

**Confirmed effects:** read-only source investigation; the two diagnostic files in one preserved local managed workspace; this records-only incident artifact on existing Grey Deer PR #8648. No QLedger source/ledger mutation, no workflow rerun, no forced Git push, no new alert, no new provider worker, no live release, no market action, and no predictive/policy promotion.

**Current critical frontier:** QLedger/nightly delivery owner reconciles the GH001 noncontention push failure and incumbent source custody, then admits one small safe continuity repair/migration plan without compromising first-writer history; parallel #8132 warning source/permission holds and #849/#852 Terminal release holds remain independently binding.

**DO_NOT_REDO:** retry GH001 as if contention; truncate or silently exclude QLedger claims; alternate source/store/publisher; replay denied #852 publication / #849 job-log read / #8132 warning-module execution; synthetic forward-issue backfill; universal exit; unqualified probability/capital sizing.

Parent Grey Deer mission remains **PARTIAL / not proven live**.
