# GitHub Issue Repair Sweep — Sol Continuation Handoff — 2026-09-26

## Identity / authority

- Chairman mission: continue the GitHub issue backlog repair sweep one issue at a time; fix actionable defects, retire stale incident carriers only with evidence, preserve active owners, and do not duplicate implementation carriers.
- Sol role: current CEO/integration owner for this sweep.
- Protected procedure: `mastermindx-market-intelligence/Mastermind@763ec8f920177fdf48b18df1b8e37b61ab482ef0`.
- Skillpack at that exact protected SHA: `mastermind.sol_skillpack.v1` / 1.0.1 / bootstrap-major 1 compatible.
- IMPORTANT bootstrap correction: do **not** discover protected Mastermind state with repository-wide “latest commit” search. During this session that returned newer non-`master` branch commits. Resolve `refs/heads/master` explicitly, then load INDEX + required skills from that same SHA.
- Handoff carrier base: Macro `main@bd23cfbd3f192389166bef37e490003fadd6d453`.
- Handoff branch: `sol/github-issue-repair-sweep-checkpoint-20260926`.

## Mission frontier

Continue reducing the open issue backlog through bounded vertical repairs. Prefer:
1. a current production or CI defect with one clear incumbent owner/carrier;
2. a stale-open issue whose acceptance is already proven and can be closed truthfully;
3. one unowned source defect at a time.

Do not turn this into a broad “close old issues” sweep without evidence. GitHub remains implementation/evidence truth; Agent OS is continuity; issue comments preserve incident receipts.

## Proven outcomes / DO NOT REDO

### Mastermind #549 — listener inspection false-zero
- Incumbent PR #711 was independently semantically accepted and current-base integration-proven.
- Current merge-queue runs:
  - CI `36233284428`: SUCCESS.
  - Mastermind OS `36233284462`: SUCCESS.
- PR #711 merged through the required merge queue at **2026-09-26T09:57:21Z**.
- Protected merge SHA: `763ec8f920177fdf48b18df1b8e37b61ab482ef0`.
- Issue #549 auto-closed completed at the merge.
- Capability change is source-only/read-only truthfulness: failed/malformed/insufficient listener observation can no longer be reported as a proven zero. This does **not** prove installed Executive host readiness.
- DO NOT rebuild or reopen #711/#549 absent a new source/behavior regression.

### Mastermind #318 — Web-Sol F2 crypto-pool harness flake
- Repair PR #351 merged previously as `2bf0266d5476c8e75dae4afa87cca67a8f12a838`.
- Historical final PR head had successful CI run `34214966508`.
- Current protected Mastermind still carries the event-bound probe Promise, PBKDF2 saturation regression, bounded 5s failure deadline, and `clearTimeout` cleanup.
- Issue #318 was closed with corrected protected-branch receipt in comment `5845036810`.
- No production `content.js` behavior changed. DO NOT redo.

### Macro #6902 — VPS pull loop
- Closed completed.
- Explicit disk-triage hold was lawfully released after disk recovered and Market Memory technicals owner replay was healthy.
- Canonical `/usr/local/bin/macro-update` completed successfully.
- Root crontab was restored exactly after an intermediate malformed sed command temporarily emptied it; that effect was detected and fully reconciled on the same VPS.
- Natural cron at 08:12Z independently advanced production to current main, proving the pull loop remained armed.
- Durable issue receipt is on #6902. DO NOT create a second updater/scheduler.

### Macro #7169 — release-publication watcher/parser
- Closed completed.
- Source repair #7241 and CI authority repair #7693 are merged.
- Production had `release_publications.v2`, `due=0`, `unparsed_publications=0`, `verified_publications=18`, live checker exit 0, and repeated natural heartbeat successes.
- DO NOT reopen from the historical Sep-16 FOMC record unless the live contract regresses.

### Macro #6881 — Earnings public wire P0
- Closed completed; closeout comment `5844955470`.
- #7166 merged incremental bounded publication; #7171 merged release-path hardening.
- Natural scheduled run `36228430077` / job `108366906428`: SUCCESS.
- Real source catalog handled **29,672 packets**; bounded selection **5,616**; public articles **5,616**; private records **5,616**.
- Strict freshness audit: published 2026-09-17 == upstream 2026-09-17, lag 0d, backlog 0.
- Live archive index, Agilent Q3 FY2026 article, and Weekly Earnings Intelligence route all returned HTTP 200.
- DO NOT redo the stale same-generation / 10k lifetime-replay repair.

### Macro #6950 — wh_banner.js “MIME bug”
- Closed `not_planned`; closeout comment `5845023471`.
- Current accepted access law explicitly keeps `wh_banner.js` member-only. Anonymous 401 JSON + `x-regwall: deny` is intentional auth behavior, not a broken JS MIME mapping.
- Research Vault no longer references this asset.
- Other public shells that still reference a member-only banner are a current shell/access-composition concern; do **not** “fix” #6950 by making the graded banner client public.

### Prophet historical incidents
- All older open `prophet-outage` dated incidents were retired with supersession receipts.
- Current search returns only Macro #8025 as the live Prophet outage/acceptance carrier.
- DO NOT reopen the old dated issues merely because #8025 remains open.

## Unfinished lanes

### 1. Macro #6783 — MacStudio daily-runner disk recovery
State: **HOST RECOVERY PROVEN / TOP-LEVEL DAILY NONTERMINAL / NEW NON-HOST BLOCKER**

Latest durable issue receipt: comment `5845904363`.

Current facts:
- Disk pressure is resolved. Fresh post-engine read: `/System/Volumes/Data` has **261,461,552 KiB (~249 GiB) free**, well above the immutable 80 GiB / 83,886,080 KiB floor.
- Runner 28 `mac-builder-light` and runner 30 `mac-builder-5` are both online and naturally executing work.
- Natural daily run `36206135675`:
  - collect SUCCESS on runner 28;
  - active_build_map SUCCESS;
  - capital_structure SUCCESS on runner 30;
  - factor_series SUCCESS;
  - factor_panel SUCCESS;
  - engine job `108339204111` completed FAILURE.
- Engine terminal cause is **not host/disk**:
  - OIP PIT episode accrual timed out after 10 minutes;
  - `OIP_EPISODE_BUILD_OUTCOME=failure`;
  - integrity gate: `episode/campaign build or narrow publication failed`;
  - R2 publish immediately before it completed 10,125 uploaded / 1,605 unchanged / 0 failed and `audit_r2 --strict` said `R2 data plane OK`.
- Engine consumed 288.7m / 300m (96%); timing pressure is real.
- Other independent degradations in the same run: options-flow auth/entitlement 403 with old artifact retained, silver-miners truncation guard, Government Revenue projection failure, collect_tail cancellation.
- At checkpoint, GitHub top-level run `36206135675` still says `in_progress` even though engine is terminal failed.

DO NOT:
- restart either Mac runner;
- clean disk;
- dispatch/rerun/cancel the daily;
- lower the disk floor.

Exact next action:
1. Read run `36206135675` once after it terminalizes.
2. If no host/disk/listener regression appears, close #6783: its acceptance allows the daily path to surface a new truthful **non-host** blocker.
3. Route the OIP PIT failure to the existing Options Intelligence owner; do not widen #6783 into Options source redesign.

### 2. Macro #8025 — Prophet US post-#7180 production acceptance
State: **FIX MERGED / POST-MERGE NATURAL PROOF STILL OWED**

- #7180 merged to Macro main as `312d3b450da2b1017c9f8497c99d15d2e79df779`.
- Issue stays open until the next **ordinary post-merge generation** proves completed-session source binding through candidate/no-entry accounting and the served consumer.
- Latest independent Packet3 reconciliation is issue comment `5845536184`.
- That Packet3 result proves the latest inspected failed book is **pre-fix** even though the repository already contains the merge:
  - observed book was byte-identical to pre-merge checkpoint;
  - 28 eligible / 28 clock-provenance failures / 0 originated;
  - no new frozen-source snapshot fields;
  - therefore it is not evidence that #7180 failed after merge.
- The natural daily `36206135675` also began its engine before #7180 merged and its Prophet section used the old generation; do not use it as post-merge acceptance.
- No manual rescue dispatch merely to manufacture a cohort.
- Truthful zero candidates are allowed.

Exact next action:
- consume the first ordinary Prophet generation whose actual producer source includes #7180, then verify exact bound source bytes -> candidate/no-entry accounting -> served/entitled consumer. Close #8025 only on that proof.

### 3. Macro #6693 — pc-ci-1..3 listener liveness
State: **LISTENERS ONLINE / NATURAL ONE-JOB TURNOVER PROOF OWED**

Current facts:
- old exact `winpc-wsl` endpoint remains offline;
- authorized native-Linux device `mastermind-pc` carries existing runner listeners;
- GitHub org roster:
  - pc-ci-1 runner 12 online idle, `ci-linux-canary,ci-linux`;
  - pc-ci-2 runner 13 online idle, `ci-linux`;
  - pc-ci-3 runner 14 online idle, `ci-linux`;
- current listener processes are bound to the expected runner systemd units and resources are healthy;
- last reconciliation found the same long-lived `--once` listener PIDs, so issue acceptance still lacks a natural one-job exit -> systemd restart -> re-registration witness.

DO NOT dispatch/rerun CI just to manufacture turnover.

Exact next action:
- when a naturally admitted trusted CI job lands on one of pc-ci-1..3, capture its job/runner receipt, then prove the consumed `--once` listener exited and systemd returned a fresh online listener. Repeat only as needed to satisfy the issue’s exact acceptance ruler.

### 4. Macro #5979 — data-health aggregate red
State: **OPEN / AGGREGATE REGRESSION / NOT ONE SAFE PATCH**

Receipts:
- latest failing data-health run: `36209570462`, head `d20b347fbbd2fb39a89e915174262f610f33c9d0`;
- immediately preceding green run: `36199856787`, head `d4ee42e88cac60e8abcfb960af89051bc1f2606d`.
- The green->red interval spans generated data/site changes plus CI-manifest movement; this is not one atomic defect.
- One failure is already owned by active PR #8033. Preserve that carrier.
- Theme Graph’s frozen `2806` company-node assertion explicitly guards identity law; do **not** “fix” it by blindly changing the constant to 2807.
- Earlier probes showed some failing tests are generated-artifact/contract drift rather than a clean source bug.

Exact next action:
- decompose one currently failing pack at a time, select an **unowned** contract with a discriminating current-source reproducer, and repair only that owner. Do not convert #5979 into a catch-all implementation PR.

## Effect / uncertainty ledger

- `EFFECT_UNKNOWN`: **NONE** at checkpoint.
- The temporary empty root crontab during #6902 recovery was detected and reconciled; full nine-line preflight crontab was restored and natural cron proof followed.
- The historical bulk Prophet-close operation hit a connector call ceiling after partial execution; every target was explicitly reconciled before closing the untouched remainder. No uncertain issue writes remain.
- The attempted direct merge of Mastermind #711 was refused 405 by the active merge-queue ruleset; no merge effect occurred from that attempt. The PR was then submitted through the canonical queue, whose CI and Mastermind OS checks passed, and it merged as `763ec8f...`.

## Other important current truth

- Mastermind default-branch ruleset: `Mastermind Default Branch Merge Queue`, squash, one entry, ALLGREEN, no bypass actors.
- Do not treat Vercel Hobby deployment quota statuses as repository source acceptance for production-inert Mastermind test/source changes when the governing repository CI/queue rules do not require that external deployment.
- Macro main moves rapidly through generated-data commits. Re-pin immediately before any modification.
- Fable remains unnecessary for this issue sweep; use the least-scarce capable worker/connector and existing carriers.

## Successor first turn

1. Resolve protected Mastermind with `refs/heads/master`; load same-SHA Skillpack.
2. Resolve current Macro `refs/heads/main`.
3. Read this handoff only, then refresh material invalidators:
   - #6783 / run `36206135675`;
   - #8025 latest comment + first post-#7180 ordinary generation;
   - #6693 natural runner turnover;
   - #5979 latest data-health run / active owner PRs.
4. Close #6783 if the top-level run has terminalized and host invariants remain healthy; do not fix its OIP blocker in the host carrier.
5. Continue one actionable issue at a time.

## Lifecycle classification

`CHECKPOINTED_CONTINUATION`

Reason: substantial proven outcomes are durable, several issue lanes remain independently actionable, and the exact next actions are evidence-gated rather than blocked by a human control. No operation is abandoned and no uncertain effect is being handed off.
