# Publication note — Options Intelligence integration amendment packet (Astra research return, 2026-09-16)

**What this directory is.** The five files beside this note are the Astra research return the Chairman handed
to Fable session `9324e573-b5e8-4e69-b4a8-b3e65d25c731` (Slack seat `U0BT03G58UW` / Claude6, host Mac-Studio,
macro worktree `.claude/worktrees/fable-handoff-4745b5`, branch
`claude/options-intelligence-integration-amendment-packet-20260916`) on 2026-09-16. They are published
**byte-identical** so the fleet reads one copy instead of a Downloads folder. Publishing them is a
**delivery act with effect NONE**: it registers nothing, dispatches nothing, and binds no principal. The packet's
own header is authoritative on that point (`operation_key_status=allocated in this packet only; not registered
or dispatched`, `workers_started=false`, `watchers_started=false`, `source_write_admission=HOLD`).

**Program home.** `options-intelligence` (config/mastermind_programs.yml); records workstream
`WS:ADVANCED-DATA-OPTIONS` (the C0 records landed under that key on 2026-08-28). This is NOT a new workstream,
program, registry, queue, store or authority plane — the packet forbids all of those and so does this note.

## Files and digests (sha256, computed on the seat at publication)

| File | sha256 |
| --- | --- |
| `FABLE_HANDOFF.md` | `a56d17edfa7f074f2f286310d8f5e4f915fc1c2ed5b0f0809ba9b26004a3f5a5` |
| `OPTIONS_INTELLIGENCE_INTEGRATION_AMENDMENT.md` | `f0a29002fb5f49a7a421d87c2b5caaf707988ba6b6ad9699ac0d7604ee652c54` |
| `PROGRAM_LEDGERS.json` | `72d3445db02f373ac46fd3e85c117f1317fc2e06d8ad5f5aa8da5ea86172ce08` |
| `CONDITIONAL_CHILD_PACKETS.md` | `2819863365862a1b3bec76e9bf2eadd672f6b4267ca8e2a06c2fd8baabdd2914` |
| `VERIFICATION_AND_OPEN_GATES.md` | `dd70cec1f775524a5dfe099135487b2ecfeb24bcc5da9d4f7106c8eef108417e` |

**Not delivered to the seat (referenced by the packet, absent from the handoff):** `READ_ME_FIRST.md`,
`SOURCE_REGISTER.md`, `ARTIFACT_VERIFICATION.json`, `MANIFEST.sha256`. Their absence is recorded, not
reconstructed. The packet's read path `research/options_estate/OPTIONS_RUNTIME_ROOT_CAUSES_2026-09-10.md` is
not on `main`; it lives only on the unmerged research draft macro #7027.

## Stale-truth table — packet pins versus the state observed at publication (2026-09-16 ~19:45–20:00Z)

| Item | Packet says | Observed at publication | Consequence |
| --- | --- | --- | --- |
| Macro `main` | analytical `e729d0fd`, last observation `c91daea4` | `2801ae52` (fetched 19:5xZ) | Pins are dated; re-pin at action time as the packet requires. |
| Gate G01 (Options carry-forward `e729`→`main`) | engine/scripts/tests/templates changed; exact Options carry-forward "unqualified after a blocked follow-up" | `git diff --name-only e729d0fd..origin/main -- engine scripts tests templates collectors ops` = 22 files, ALL under `engine/research_vault/`, `engine/research_intelligence/`, `engine/qual_extraction.py`, `scripts/build_research_*`, `scripts/resolve_ci_canary_ref.py`, matching `templates/research_*` and `tests/test_research_*`/`test_ci_canary_tools.py`/`test_trusted_ci_executor_workflow.py`; zero paths under options / live_flow / thetadata / campaign / outcome / intraday_flow | Read-level G01 is closed: no Options source moved between the packet's analytical pin and current main. The owner collision receipt for ACTIVE leases is still owed (that is a carrier question, not a diff question). |
| C0 carrier macro #6604 | OPEN / unmerged / non-draft; final projection `mergeable=false` at unchanged head; conflict cause not established | OPEN, non-draft, head `55af4ae37b02` unchanged, labels `merge-on-green` + `merge-blocked`, `mergeable=UNKNOWN` (GitHub recomputing at read time; not a green and not a conflict). Checks: 21 pass; FAIL = `ci-gate`, `trusted-ci / trusted-executor-pack-6` (glossary parity test, run 34835967402 job 103951471368), `ci-authority/codex/merge-queue-pilot` (inactive-base receipt, red by design), Vercel (free-tier rate limit, spurious). Last carrier comment 2026-09-14T14:49Z is the sweeper's semantic-proof refusal (`infrastructure_blocked`, pack fragments missing). 2026-09-06 comments: "HOLD-RELEASED — Released under the Chairman override (Meta-CEO A)". | Packet §D holds: the release scope of a Market-Ontology-scoped override over an Options carrier is a ruling for the current Options authority (Sol), not a seat's interpretation. This seat did not edit, arm, disarm, ready, rerun or merge #6604. |
| #6894 (Meta-CEO charter) | "now merged" | MERGED (confirmed) | Fixes the PR body's stale location claim; does not settle scope (packet D3). |
| Related carriers | #6628 / #7125 / #7027 / #6867 open drafts; #7070 open non-draft; #6585 merged | #6628 DRAFT `0378a1de`; #7125 DRAFT `89ec6f2c`; #7027 DRAFT `9f68e8e3`; #6867 DRAFT `1ba8321d`; #7070 OPEN non-draft `2e64a2b5` armed `merge-on-green` + `merge-blocked`; #6585 MERGED `77f40063`, merge `dbd654ed` is an ancestor of `origin/main` | Matches the packet's carrier ledger; #7070 is additionally armed-and-blocked. |
| Slack carrier (`#agent-dispatch` C0BSBM78V1N) | old C0 child TERMINAL (ACCEPTED/STOP 2026-08-28, disarmed); no worker/watcher started; principal placement WAITING_CAPACITY | No Options Intelligence root and no `6604` mention after 2026-09-08/09 (two searches, bots included). Sol is actively ruling on the channel on 2026-09-16 (Fabric root, multiple CONTINUE/STOP rulings). | `architecture_authority=Sol` is current, not historical. The lawful binding act is ONE top-level `DECISION_REQUEST / CUSTODY_DISPOSITION + PACKET_DELIVERY` (effect NONE) — never a post under the terminal C0 root, never a self-issued PICKUP/START. |
| Gate G06 (installed OA-1T scheduled source) | dated 2026-09-10 receipt: producer checkout `edd07d73` lacks the accepted measured helper; fresh Mini inspection blocked for the research agent | Read-only `ssh m1` at 2026-09-16T19:58:40Z (host `admins-Mini-652`): `/Users/chriswong/liveflow-ops-wt` HEAD `edd07d7324534c81341ebcc4683173714c3b8509` (commit date 2026-08-20T16:27Z), branch `main`, 1 dirty status line, last fetch 2026-08-20T09:30Z, `git merge-base --is-ancestor dbd654ed HEAD` = NO, `grep -c -i nbbo engine/live_flow.py` = 1 (pre-#6585 shape); launchd `com.mastermind.liveflow` LIVE pid 9191 = `python -m scripts.live_flow_poller --rth-only` (miniconda python); `/tmp/liveflow.stdout.log` tail empty. | Disposition **ADOPTION_NEEDED** (packet B's second branch), stated as a fact for the owner — NOT performed. Constraints the owner must carry: never touch a running RTH poller (inspection was mid-session); adoption window is after the 16:00 ET close and before the next 09:25 ET launchd fire; rollback is `git checkout edd07d73` of the same worktree plus its untouched state; the miniconda interpreter and `.env` binding must be re-qualified against the #6585 imports before the first scheduled fire; no `--once --date`, replay or synthetic event counts as proof. |

## What this seat did and did not do

Did: fetched and pinned current state; ran the two bounded read-only qualifications above (G01 diff, G06
inspection); published the packet byte-identical; wrote the handoff record beside it; opened ONE docs-only PR;
posted ONE custody DECISION_REQUEST top-level on #agent-dispatch C0BSBM78V1N at ts 1789589027.207419 (delivery PR macro #7221).

Did not: ACK, START, claim or register the allocated operation key; spawn any worker or lane; arm any watcher
or cron; edit, arm, disarm, ready, rerun or merge #6604 or any listed carrier; deploy, pull, reset or restart
anything on M1; touch the ThetaData store; edit any `WS-*` record; create any Options2 / fifth-workstream /
package or candidate store; fit, score, rank, size or promote anything.

## Successor rule

A successor seat must NOT re-publish this bundle, re-post the custody request, post under the terminal C0 root
`C0BSBM78V1N/1787900289.577559`, or execute any conditional packet A–L before Sol's disposition names the
receiver and the exact write allowlist. Read the handoff record first, then fresh-read the carrier for a Sol
reply after ts 1789589027.207419; act only on that edge.
