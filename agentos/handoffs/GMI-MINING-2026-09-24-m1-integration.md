---
workstream: "WS:GMI-MINING-M1-INTEGRATION"
session: claude/mining-seat-wave1
model: fable
ended_because: blocked
mission: >
  Live seat checkpoint for gmi-mining-fable-ceo-m1-integration-20260924-chairman-001: deliver
  the first Mining release (real signed-in Freeport W-C and MP Materials W-R economic dossiers)
  on the Semiconductor-led shared foundation by shipping plan tasks T01'-T08 as fabric-built PRs
  in dependency order. Effects behind held gates G1 (exact shared profile/callable), G2 (native
  source bytes), G5/G6 (private route, mount) stay frozen while source-independent synthetic and
  incumbent-owner lanes continue; the seat session is still running.
state_before: >
  Research/design/plan/packet prepared on #7795 @ eb6f05c0 (PREPARED_FOR_REVIEW_AND_PLACEMENT,
  BUILD_READY false, no receiver). Semiconductor B #7870 DRAFT @ dd5076fa: mount + theme-research
  UI landed after the packet pin c6c67c87, composition schema still semiconductor-only, no reply
  to Mining request 5809893850. CDV-1 T1 #7905 open on the issuer_profiles seam (accepted
  pg_profile idiom). No app/theme_research.py route on main.
changed:
  - path: agentos/workstreams/WS-GMI-MINING-M1-INTEGRATION.md
    what: "Workstream minted: objective, owned paths, five waves, do_not_redo, landmines."
  - path: agentos/handoffs/GMI-MINING-2026-09-24-m1-integration.md
    what: "Seat pickup checkpoint: state, gates, fabric/hosts, wave plan."
  - path: research/mining/m1_integration_program/rulings/R-MIN-2026-09-24-wave1.md
    what: "R-MIN-00..09 wave-1 rulings plus seam rulings R-MIN-10..28 consumed from the two Opus read-only seam audits (A: Company/receipts -> T02/T03/T07; B: shared-base/ontology -> T01'/T04/T06)."
  - path: research/mining/m1_integration_program/reviews/
    what: "OPUS_SEAM_AUDIT_A_COMPANY, OPUS_SEAM_AUDIT_B_ONTOLOGY (26 findings; 4 blockers) and OPUS_T04A_CONTENT_REVIEW_R1 (ACCEPT-WITH-FIXES on #7922)."
verified:
  - claim: "Every packet member byte-matches the research carrier; README blobs (master packet, addendum, plan, design, canonical P05) resolve on origin/sol/mining-principal-research-20260923 @ eb6f05c0."
    command: "git hash-object <member> vs git rev-parse origin/sol/mining-principal-research-20260923:<path> for all 11 members"
    result: "match=11 mismatch=0; five README blobs OK."
  - claim: "The packet's own handoff checker runs clean from the extracted root."
    command: "python3 research/mining/check_mining_handoff.py"
    result: "receipt written; checker_blob 6b815443 as stated in README."
  - claim: "Semiconductor B has no shared POST route on main and its composition schema is still semiconductor-only."
    command: "git ls-tree -r --name-only refs/remotes/pr/7870 | grep -E 'app/theme_research|theme_research.*schema'"
    result: "only contracts/market_ontology/semiconductor_theme_research.v1.schema.json and engine/market_ontology/semiconductor_theme_research.py."
  - claim: "No shared-owner return to Mining request 5809893850 exists on #7870."
    command: "gh api repos/.../issues/7870/comments | select(.id > 5809893850)"
    result: "seven later comments, all sibling-sector notices (Finance, Industrials, Energy, Robotics, Consumer, GMI Wave1, Tech ex-Semis)."
unverified:
  - "Runtime liveness of any shared candidate component; deployed privacy; native source capture clocks."
unresolved:
  - "G1: exact Mining profile/callable/reported-economic-context interface unreturned by the shared owner."
  - "G2/G3/G4: native FCX/MP bytes, spans, identities and governed economic objects unqualified."
  - "G5/G6: private route/client/mount not on main; source custody with incumbents."
next_actions:
  - "Lanes: min_t01_harness queued on mini2 (T01' harness + CI job); min_t04a_content_r2 repairing #7922 per the Opus R1 review; merge #7922 after seat grep-verification of the verbatim repairs."
  - "Shared-owner answer to the T06 mount/entry questions (#7870 comment 5811889498) gates T06; never re-ask."
  - "T02 after #7905 merges; T04a in parallel; then T03 -> T04b -> T07; hold T05/T06/T08 for the shared route/mount and G2 admission."
do_not_redo:
  - "Never re-ACK #7795 (pickup = comment 5811520293); never repeat 5809893850 on #7870."
  - "Never put implementation on #7795; never edit #7870's branch or any file it owns."
danger_areas:
  - "legacy-jobs.yml / test_ci_pack.py are contested by many open PRs - append at END, rebase before push."
  - "A lane returning STATUS: PASS with tests it wrote itself is not proof; the Opus red-team + frozen probes are."
prs: [7795, 7921, 7922]
decisions: []
discoveries: []
---

# Mining M1 integration — seat checkpoint 2026-09-24

Pickup by deliberate Chairman delivery; Stage A reconciliation complete; Stage B synthetic units admitted
under addendum IR-06. This file is rewritten at every wave boundary.
