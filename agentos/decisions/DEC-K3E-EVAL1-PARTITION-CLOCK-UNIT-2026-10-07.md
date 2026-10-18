---
key: K3E-EVAL1-PARTITION-CLOCK-UNIT-2026-10-07
question: >
  The frozen EVAL-1 preregistration (eval1_preregistration.v1.json, #8584) closes F_DEV, F_VAL and F_HOLD at "at
  least 100 distinct issuer episodes". It defines episode identity as sha256(issuer_ref, metric,
  horizon_or_fiscal_period, episode_start_nyse_session) and also says "Overlapping owner-native events for one issuer
  collapse to one event cluster". Read literally, those two sentences give two different counters. Distinct episode
  ids count one per (issuer, metric, period, start). Event clusters collapse an issuer's overlapping episodes across
  metrics and periods into one. Which counter does the partition clock use? The choice moves every partition boundary,
  and it must be fixed before any F_DEV label is read.
answer: >
  PRIMARY (binding for partition closure): issuer overlap clusters. These are the same unit the R4 v2 admission floor
  counts (DEC:ITP-R4-ISSUER-AXIS-AS-KNOWN-VERSION-CLOCK-2026-10-07, r4_v2_admission.clusters). A partition closes at
  the first NYSE session at which its eligible episode starts form at least 100 distinct issuer overlap clusters.
  SECONDARY (descriptive only, never closes a partition): the count of distinct episode_ids, reported beside the
  primary in every partition-clock receipt.
  Both counts come from episode starts alone. They read no label, direction, loss, comparison or post-outcome calendar
  choice. The clock receipt proves this structurally: the computation imports and reads no label or price-outcome
  input (the recursive label-free check in the A9 tests).
  Ties and edges:
  - A cluster counts toward the partition that contains its anchor, its earliest start session (anchor at or after the partition start and at or before its close). Confirmed against eval1_partition_clock.py PRIMARY_RULE and the CLUSTER_ANCHORED_* exclusion reasons (#8805).
  - An episode that started before its partition began is excluded and counted by reason, verbatim from the prereg
    effective_n_rule.
  - Purges are exactly 63 NYSE sessions on the canonical is_session calendar.
rationale: >
  The prereg's inference unit is the issuer episode after collapse. The collapse sentence sits inside the
  effective_n_rule, so overlapping owner-native events for one issuer are one unit of evidence, not several.
  Counting raw episode_ids would let one issuer's simultaneous multi-metric revision day count as several
  independent observations. That inflates effective N and closes partitions early on correlated evidence, which is
  exactly the failure the clustering rule exists to prevent. Counting clusters is the conservative choice: partitions
  close later, never earlier.
  Using the R4 v2 cluster function gives EVAL-1 and the R4 floor one counting unit, not two divergent ones (no new
  vocabulary).
  Reporting the episode_id count as a secondary keeps the literal reading visible and auditable, without letting it
  move a boundary.
alternatives:
  - option: "PRIMARY = distinct episode_ids (literal identity hash)"
    why_not: "It ignores the prereg's own collapse sentence, inflates N on correlated multi-metric issuer days, and closes partitions earlier on less independent evidence."
  - option: "PRIMARY = distinct issuers"
    why_not: "The prereg counts episodes, which re-occur after twenty quiet sessions, not issuers. Counting issuers would make F_VAL and F_HOLD unreachable for a fixed universe and departs from the frozen text."
  - option: "Defer the choice until F_DEV labels are visible"
    why_not: "A partition clock chosen after outcome access violates the prereg ('never from ... a calendar date chosen after outcome access'). The unit must be fixed now, before boundary-forward labels exist."
evidence:
  - "eval1_preregistration.v1.json effective_n_rule and time law (#8584, squash 01fcaf74): '100 distinct issuer episodes'; 'Overlapping owner-native events for one issuer collapse to one event cluster'; 'A partition closes on episode counts alone. Those counts come from episode starts'."
  - "r4_v2_admission.py clusters() at #8619 (aeb37c78): issuer overlap clustering used by the R4 v2 floor."
  - "PR #8805 (lane head 6a9a2df8ad6a, healed head 3576087d70b2, squash 413e253a): eval1_partition_clock.py applies PRIMARY_RULE and SECONDARY_RULE verbatim; tests/test_eval1_partition_clock.py carries the recursive label-free check; first reading at origin/main 413e253a: F_DEV_OPEN, 56/100 clusters (204 total, 128 anchored before the partition, 20 anchor observed before the boundary), 215 episode_ids, cross-check with engine.k3e_eval1_forward.assign_partitions AGREES, checker OK, receipt sha256 e04da67a7d74fe2de20f58b9c3698d56b454a4320a5c4ab981e4dbb3c4943efc (kept outside the repository)"
affects:
  - "WS:ALPHA-INTELLIGENCE-INTEGRATION"
  - "DEC:K3E-EVAL1-CUSTODY-UNDER-CHAIRMAN-DIRECTIVE-2026-10-07"
  - "DEC:ITP-R4-ISSUER-AXIS-AS-KNOWN-VERSION-CLOCK-2026-10-07"
  - "engine/k3e_eval1_forward.py"
  - "research/alpha_intelligence/expectation_market_dynamics/eval1_preregistration.v1.json"
confidence: high
reversibility: costly
decided_by: "seat: program-ceo session 2fc05761 (WS:ALPHA-INTELLIGENCE-INTEGRATION owner, EVAL-1 custodian per DEC:K3E-EVAL1-CUSTODY-UNDER-CHAIRMAN-DIRECTIVE-2026-10-07), under Chairman directive 2026-10-06/07; ruled 2026-10-07 before boundary_at labels exist; implementation by orchestrator A (A9)"
decided_at: 2026-10-07
review_by: 2027-01-07
---

# EVAL-1 partitions close on issuer overlap clusters

The prereg's "100 distinct issuer episodes" is read through its own collapse rule:
- An issuer's overlapping owner-native events are one unit.
- Partition closure counts issuer overlap clusters, the same unit R4 v2 floors on.
- Distinct episode_ids are reported beside them and never move a boundary.

The ruling was fixed before any F_DEV label existed. The clock that applies it reads no labels.
