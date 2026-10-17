---
key: EXECUTIVE-ECOSYSTEM-COMPLETION
title: Executive Ecosystem Completion — Executive OS, Subagent Fabric, Mastermind OS app and continuity proven as one multi-level path
objective: >
  Complete Mastermind Executive OS, its Subagent Fabric bindings and the Mastermind OS app so
  that one real Chairman-originated request traverses the full multi-level path — authenticated
  identity, correct source custody, valid admission, economical placement, retained result,
  actual review, original-parent consumption, recoverable continuation and a coherent app
  outcome — and both a successful and an interrupted journey are proven on the live host.
  Census, architecture, merged PRs, green CI, a worker run or a dashboard demo are rungs, not
  the outcome.
status: active
program: executive-os
p0: EXECUTIVE_OS
repos: [macro, mastermind]
owner: fable-meta-ceo
class: build
blast_radius: irreversible
ambiguity: scoped
depends_on: ["WS:EXECUTIVE-AUTONOMY-V1-CLOSURE", "WS:EXECUTIVE-CAPACITY-FABRIC"]
waves:
  - id: A0
    title: Phase A census → canonical capability ledger and integrated programme plan (Mastermind research/)
    status: in_progress
    next_action: >
      Ship research/EXECUTIVE_ECOSYSTEM_COMPLETION_CAPABILITY_LEDGER_2026-10-17.md and
      research/EXECUTIVE_ECOSYSTEM_COMPLETION_PROGRAMME_PLAN_2026-10-17.md to Mastermind master
      behind the `test` check. The ledger holds 46 capability rows, each with owning surface,
      evidence revision, writer/effect risk and a falsifiable completion test.
  - id: C1
    title: Continuity — this workstream, dated handoffs, seat memory, P4 frontier refresh
    status: in_progress
    next_action: >
      Merge this record; then refresh WS:EXECUTIVE-AUTONOMY-V1-CLOSURE P4 with the installed
      91c1cac5 facts (installed; its prepared supersede_unstarted_v1 acceptance, bound to JOB-003, is
      itself superseded by the current-master successor S') in a follow-up PR.
  - id: R1
    title: Restore codex-01 provider readiness (human credential rotation), then supersede the prepared 91c1cac5 acceptance with the current-master successor S' (root JOB-003; terminal JOB-006 carried)
    status: todo
    depends_on: [A0]
    next_action: >
      CORRECTED 2026-10-17 13:5xZ (seat 873aabd3): the live codex-01 readiness receipt is a FAILED
      canary (observed 2026-10-12T07:08Z, refusal provider_turn_failed, provider error terms
      capacity/model, identity refusal none) and every automated requalification route refuses it
      (readiness_receipt_not_passing, requalification_identity_continuity_unproven,
      drift_requalification_credential_changed, no pin-recovery grant). First act is HUMAN-ONLY: the
      Chairman/production owner runs provision-worker-auth.sh --enroll-service-account
      --replace-existing (Keychain item mastermind-executive-codex-access-token, currently ABSENT)
      or the fallback --reauthorize-device --replace-existing in an interactive terminal; codex-01 is
      the default slot. Then the seat runs ONE --verify-ready, a fresh clone at the current master head
      (S'), os_release_assets.py prepare, install-inputs, service-control.sh stop, the supersede
      prepare (--supersede-unstarted-sha 91c1cac5… with the canonical descriptor digest 91695ef2…),
      install.sh S', acceptance.sh once. Never re-prepare by hand, never cancel JOB-003.
  - id: R2
    title: Arm ceo_submit and the COO/operator harness after the S' acceptance receipt
    status: todo
    depends_on: [R1]
    next_action: >
      Foreground-only first: autonomy-control.sh status --expected-sha <S'> (the installed successor,
      not 91c1cac5), arm-quiesce-control-uid, arm --gate-b-receipt …, ceo-submit-arm, ceo-submit-status;
      only once the S' acceptance receipt exists, the read-only review of the arming sequence has
      returned, and all four predicates read true.
  - id: R3
    title: Dispose historical queued roots JOB-002, JOB-003, JOB-013 through their original parents
    status: todo
    depends_on: [R2]
    next_action: >
      JOB-003 is consumed by R1; JOB-013 and JOB-002 are placed once the harness is armed or
      receive a recorded lawful cancel with reason. No replacement root for the same objective.
  - id: F1
    title: codex-01 worker service live; native Claude and Fabric-bridge placements each proven once
    status: todo
    depends_on: [R1]
    next_action: >
      After the readiness receipt passes again (human rotation + one --verify-ready), enable and
      kickstart com.mastermind.executive.worker.codex as the S' acceptance requires;
      one COMPLETED attempt per quota class; Fabric bridge shows a sealed assignment snapshot.
  - id: A1
    title: Install the OS executive transport and the root-sealed Studio opt-in
    status: todo
    depends_on: [A0]
    next_action: >
      Inputs listed 2026-10-17 in the census handoff body (section Lane A inputs). Host census:
      publication file and audit dir ABSENT, gateway profile web_ceo_v3 without the os_executive_*
      keys, tunnel config/auth + chisel PRESENT (relay_port 49152). Publication owner unnamed —
      the Chairman names it before any stage. Then: read-only Opus audit; the production owner runs the stage/upgrade
      with --enable-repository-workspaces --os-commission-config-sha256. Proof: unauthenticated
      POST /os/executive/context answers 401, not 404, locally and through the edge.
  - id: A4
    title: Phase E Meta-CEO journeys in Mastermind OS (web, native, responsive) with authenticated live data
    status: todo
    depends_on: [A1, R2]
    next_action: >
      Journeys E-1 to E-8 captured with network traces; exactly one Job per submit; an
      interrupted connection reconciles to the same Job through ceo_intent_status.
  - id: H
    title: Phase F acceptance campaign H1–H8
    status: todo
    depends_on: [R2, A4, F1]
    next_action: >
      Run each journey once against the armed host (full programme, routine direct-to-worker,
      reviewed return to the original parent, interrupted connection, fail-closed writer
      conflict, failed worker repair, Chairman correction in flight, browser live-data) and
      record the evidence rows in the ledger §2.6.
landmines:
  - The prepared 91c1cac5 acceptance binds JOB-003 (root event 20) and carries terminal JOB-006 / ATT-f036984f…; cancelling, duplicating or re-preparing it invalidates the lineage. It cannot run as prepared (readiness FAILED; master moved); it is superseded lawfully only through acceptance_maintenance.py --supersede-unstarted-sha 91c1cac5… --superseded-descriptor-sha256 91695ef2… (the canonical JSON digest of its descriptor — the file sha256 is NOT the digest) after service-control.sh stop; never by cancel, hand re-prepare or a second root.
  - codex-01 provider readiness is FAILED since 2026-10-12T07:08Z (provider_turn_failed; provider terms capacity/model; identity refusal none; codex 0.159.2, model gpt-5.6-sol). Passing receipts had renewed hourly by device revalidation from 2026-10-03 until that canary. Device revalidation, refresh, terminal-adverse, drift and pin-recovery routes all refuse; only an explicit credential rotation (--replace-existing + an enrollment mode) clears it and that is HUMAN-ONLY. The slot's default credential kind is service-account (workspace binding company-workspace-admin-attested, no Multilogin seat); the Oct 3–12 chain ran on the device-auth fallback; the Keychain token item is absent, so the service-account path needs the workspace admin first. The Oct 12 terms were capacity/model, so a rotation alone may not clear a provider-capacity condition — spend the single fresh canary deliberately.
  - All four autonomy predicates read false and ceo_submit has been disarmed since 2026-10-12 at 25c4b792; a Chairman request submitted today is admitted as a Job but never placed.
  - The installed Executive MCP config lacks os_executive_transport / os_executive_resource / os_commission_port and the sealed Studio opt-in file is absent, so /os/executive/* answers 404 and the app command path is dark. Never emulate it with a mock transport; install it through the runbook.
  - Mixed-release host — control, mcp, privileged and worker plists at 91c1cac5; relays at 326c8469; tunnel at a858ac24; autonomy-state names 1a8698cb. Release coherence is a next install, not a service restart.
  - Sol's open sol/web-* PRs (1570 1569 1568 1566 1553 1542 1536 1515 1477 1473) and codex 1563 are live writers on the gateway, app and fabric surfaces; extend, never compete.
  - Fable is never enrolled with mastermind.executive.intent.submit (rejected by design). Personal-Pro realm re-enrollment is a human/provider ceremony named once, not probed.
  - Fabric kit files pools.yaml, pick.py and RELAUNCH_QUEUE.txt belong to another lane; read-only.
  - Python tests at the pin need the repo root on sys.path and the macro checkout's tests/ package off it (python -P), or tests.test_executive_ceo_ingress resolves into macro.
  - Agent OS records are not liveness — the P4 "PICKED_UP by chat 01a1230a" claim is historical; the S' acceptance path is driven by the current seat after the human rotation, unless a live START is observed first.
do_not_redo:
  - The 2026-10-17 Phase A census (ledger §1 and §5) — reuse until an installed SHA, installed config or runtime DB fact changes.
  - The install of 91c1cac5 and the acceptance receipt for 25c4b792.
  - Mastermind PRs 1283, 1560, 1543, 1534/1537, 1544, 1527, 1509, 1558 and the R2 master plan §17 (accepted work enumerated in the ledger §4).
  - The 213-test transport run at a552a5e5 (plan §6) until the transport source changes.
next_action: >
  Mastermind ledger/plan PR #1571 is MERGED (master ee0f0d9b); correction PR #1581 carries the
  readiness/human-gate facts. Lane R waits on the HUMAN-ONLY codex-01 credential rotation; the seat
  then runs ONE --verify-ready, the fresh S' clone + release assets + install-inputs, service stop,
  supersede prepare, install.sh S', acceptance.sh once, then the arming sequence after its
  read-only review. Meanwhile, with no host mutation: Lane A inputs (publication owner still
  unnamed), Node-side app qualification at a552a5e5, Phase F after arming.
---

## Context

**Brief.** Chairman mission "FABLE CEO META — Executive Ecosystem Completion Mission" (2026-10-17),
held by the Fable Meta-CEO seat (Claude session `873aabd3`). The seat owns programme-level
orchestration; Opus suborchestrators administer independent lanes only where a lane has several
independent packets; execution labour goes through the existing Subagent Fabric; host effects stay
with the seat under sudo and Chairman delegation; the production owner confirms install and
readiness separately.

**Canonical documents (Mastermind repo, `research/`).**
`EXECUTIVE_ECOSYSTEM_COMPLETION_CAPABILITY_LEDGER_2026-10-17.md` — 46 rows across runtime (E1–E12),
fabric (F1–F7), gateway/edge (G1–G8), app (A1–A6), continuity (C1–C5) and journeys (H1–H8), with
states PROVEN_LIVE / BUILT_NOT_PROVEN / PARTIAL / DARK_OR_DISCONNECTED / BROKEN / SPEC_ONLY /
NOT_BUILT / REJECTED_BY_DESIGN. `EXECUTIVE_ECOSYSTEM_COMPLETION_PROGRAMME_PLAN_2026-10-17.md` —
ownership map (no duplicate lifecycle, registry, queue, credential, memory, retry, session,
acceptance or publication authority), programme decisions PD-1…PD-7, lanes R/F/A/C with
scope/identity/acceptance/return/non-goals per commission, critical path, Phase F campaign,
holds, evidence and checkpoints.

**Relationship to incumbents.** This workstream is the delivery vehicle for the DONE_WHEN journey
that `WS:EXECUTIVE-AUTONOMY-V1-CLOSURE` P4/P5 describe (acceptance → arm → routine Job → repair →
closure) and consumes `WS:EXECUTIVE-CAPACITY-FABRIC` placement work as-is. It adds no authority:
Executive OS keeps runtime/admission/lifecycle, Agent OS continuity, GitHub source, Linear
projection, Slack transport, Capacity/Model Router placement, RuntimeBinding/session owners
identity, Mastermind OS the human interface.

**Delivery ladder at record time (2026-10-17).** Runtime lifecycle and typed LOST reconciliation:
PROVEN_LIVE (21 completed Jobs, 11 LOST attempts reconciled). CEO ingress socket: PROVEN_LIVE as a
projection; `ceo_submit` and COO arms: DARK. Installed-release acceptance: PARTIAL (prepared, no
receipt). Gateway v3 and workspace reads: PROVEN_LIVE and auth-gated. OS executive transport,
session transport and Studio commission owner: DARK / not installed. App served: PROVEN_LIVE;
every app journey: BUILT_NOT_PROVEN. Python transport tests at the pin: 213 passed. Node/Rust
qualification of the same app tree on 2026-10-17 (ad125292 = a552a5e5 = ee0f0d9b for
app/mastermind_os): tsc clean, vitest 1574 passed / 1 skipped, web and native builds, cargo 41
passed — source validation only; no signed candidate .app exists on the host.
