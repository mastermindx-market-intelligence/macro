---
key: AUTONOMY-V1-CLOSURE-SOURCE-ESTATE-DISPOSITION
question: >
  Which inherited Autonomy V1 carriers (Mastermind #811, #1145, #1041, #1157, #1166, #1169, #1204
  and the adjacent #1219, #1178, #1176, #1175) belong in the successor release train for operation
  executive-os-autonomy-v1-closure-20261003-fable-001, and which should close unmerged?
answer: >
  Successor train = protected master a2646f45 (installed as Control on 2026-10-04) plus a
  current-base repair of #811, optionally plus a repaired #1219 only if its MCP generation producer
  lands with it. #811 needs_current_base_repair; #1145 still_required but V1-inert (merge on its
  own gates, never V1 proof); #1041 should_close_unmerged; #1157/#1166/#1169 still_required for the
  dormant in-band release-owner lane only and parked pending a Sol ruling on install.sh versus
  release-owner exclusivity; #1204 should_close_unmerged; #1219 needs_current_base_repair; #1178
  already_superseded; #1176 conflicts_with_newer_source; #1175 V1.x non-goal. Nothing from the
  install set enters the train and no second release controller is created.
rationale: >
  Three independent read-only Opus audits plus seat spot-checks against 84df2980 and a2646f45.
  Master lacks launch-time immutable-commission verification (executive_supervisor.py:1155-1204,
  :1548-1574) and leaves CommissionDependencyPlan unwired, so #811 fills a real V1 gap but
  conflicts in tests/test_executive_supervisor.py and must be repaired by its writer or through a
  recorded custody transfer. #1145 wires the attempt-bound remote adapter with no fallback host and
  no behaviour until a host passes remote_worker_binding_source; multi-host is a V1.x non-goal.
  #1041 fills no V1 gap and carries live-on-merge effects: SCHEMA_VERSION 5→6 colliding with the
  reserved M2 v6 slot, COO policy max_depth 1→2, custody refusals on _dispatch_job/reconcile and a
  second provider-charge ledger. install.sh is the live out-of-band installer and ran both the
  03f7ca04 and a2646f45 cycles; the release-owner library writers have no root caller, activation
  publisher or CONFIGURED policy, and #1204 would add a second writer of the MCP LaunchDaemon
  plist. The packet forbids merging carriers because they exist and forbids duplicating a carrier
  whose effect/source ownership is unresolved.
alternatives:
  - option: Merge the whole inherited set into one successor release.
    why_not: >
      It would ship #1041's schema v6 collision and policy widening and #1204's duplicate plist
      writer with no V1 proof behind them, against the packet's "do not merge everything merely
      because it exists".
  - option: Open duplicate repair PRs for #811 and #1219 from the principal seat.
    why_not: >
      Each carrier keeps its incumbent writer; a duplicate carrier while effect/source ownership
      is unresolved is the collision the packet forbids. A custody transfer is recorded on the
      carrier first, after the tripwire.
  - option: Make the dormant in-band release owner the live installer now.
    why_not: >
      It has no root caller, activation publisher or CONFIGURED policy; activating it beside
      install.sh would be a second release controller.
evidence:
  - "Mastermind research/EXECUTIVE_AUTONOMY_V1_CLOSURE_CONTINUATION_HANDOFF_2026-10-03.md §4b and §5 on branch claude/ssd-executive-autonomy-v1-closure-fable-001-fb6072752abe8e13 (commit c1923145 and successors)"
  - "git merge-tree --write-tree against 84df2980/a2646f45: #811 cb8f1586 conflicts only in tests/test_executive_supervisor.py; #1145 e1fe799b, #1041 b3816bb7, #1157 b0e652a7, #1166 0c71c0c3, #1169 ce784ba5, #1204 ad606750, #1219 2f5bbaae clean; #1178 61a93096, #1176 0d58270d, #1175 c60c6673 conflict"
  - "Mastermind #811 issuecomment-5976714641 (7-step repair spec, custody tripwire 2026-10-04T06:30Z); #1041 issuecomment-5976714813; #1145 issuecomment-5976788858; #1204 issuecomment-5976759865; #1219 issuecomment-5976760078; #1178 issuecomment-5976760291; #1176 issuecomment-5976760470; #1175 issuecomment-5976760682; #1157 issuecomment-5976760960; #1166 issuecomment-5976761189; #1169 issuecomment-5976761418"
  - "Mastermind #1143 issuecomment-5976776241 and Slack C0BSBM78V1N thread 1791083562.416539 reply 1791090270.115769 (ruling as posted 2026-10-04)"
  - "Mastermind #1218 merged 2026-10-04T04:14:27Z as a2646f458f9ff41ddcedd89b338be4a4349e6cd6; /Library/LaunchDaemons/com.mastermind.executive.control.plist → releases/a2646f45; acceptance-maintenance/a2646f45/carry-forward.json passed=true at 2026-10-04T04:32Z"
affects:
  - WS:EXECUTIVE-AUTONOMY-V1-CLOSURE
  - WS:EXECUTIVE-CAPACITY-FABRIC
  - mastermind:ops/executive_os/install.sh
  - mastermind:control_plane/executive_supervisor.py
confidence: high
reversibility: easy
decided_by: "coo-fable (Fable 5.1 principal, session 527c6117-df75-4c91-83ef-98b36e39227c, operation executive-os-autonomy-v1-closure-20261003-fable-001)"
decided_at: 2026-10-04
---

## Why this is recorded

Seven inherited carriers plus four adjacent ones were open against a master that had moved
40–44 commits past most of them. Without a disposition record the next session would re-audit
them from the diffs or, worse, merge them because they exist. The load-bearing fact is the train
shape: a2646f45 is already installed, #811 is the only V1-train source item, and the install set
contributes nothing to the next host cycle.

## What it does not decide

It does not decide install.sh versus release-owner exclusivity (a Sol ruling), does not transfer
custody of #811 (that happens on the carrier after the tripwire), and does not touch the
CEO-submit/operator-harness coexistence question
(DSC:CEO-SUBMIT-SINK-AND-ARMED-HARNESS-ARE-MUTUALLY-EXCLUSIVE-ON-MASTER).
