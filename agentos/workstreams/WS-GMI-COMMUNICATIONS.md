---
key: GMI-COMMUNICATIONS
title: Communications A1 — live company routes proven; source enrollment held
objective: >
  Serve the Communications vertical's company routes on the shared foundation with
  admitted sources. Done = #8039's proven routes landed on the accepted base, source
  enrollment admitted through the existing source owner, reviewed, merged, browser proof.
status: active
program: gmi-theme-graph
repos: [macro]
owner: fable-meta-ceo
class: build
blast_radius: user_facing
ambiguity: scoped
depends_on:
  - WS:GMI-SEMICONDUCTORS
decisions:
  - DEC:CHAIRMAN-INDUSTRY-INTELLIGENCE-META-CEO-CONSOLIDATION-2026-10-11
landmines:
  - "#8039 touches legacy-jobs.yml, as do #7870 and #8404; land order matters and the last one in rebases."
waves:
  - id: COM-W1
    title: "A1 carrier #8039 (Draft/HOLD @c79aaca04948): routes proven, enrollment held"
    status: in_progress
    pr: 8039
    wait:
      kind: external_dependency
      review_after: 2026-10-18
      condition: "#7870 released AND the source owner admits Communications enrollment"
    next_action: >
      Exact-head probe of #8039 against current main (packet #8039-probe): what still
      applies, what conflicts in legacy-jobs.yml, and whether the enrollment hold has a
      named owner reply. No code until the probe returns.
next_action: >
  Hold; run the probe packet once SB-W1 releases. The carrier has been stalled since
  2026-09-24 and nothing here assumes its tree still applies.
---

## Carrier

- PR #8039, branch `claude/communications-a1-measures-20260924`, head `c79aaca04948`,
  Draft/HOLD.
- Record created at consolidation (2026-10-11); no prior WS record existed.
