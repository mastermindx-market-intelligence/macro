---
key: POLICY-WATCH-CURRENT-RECOVERY
title: Policy Watch current-source recovery R1
objective: >
  Researcher opens Policy Watch and sees dated Fed facts, next official decision,
  and a clear split between current observations and July-13 background research.
  Done when Sol reviews, publishes, merges, and verifies the live public page.
status: active
program: policy-transmission-intelligence
repos: [macro]
owner: sol
class: build
blast_radius: user_facing
ambiguity: specified
owns_paths:
  - engine/policy_watch_current.py
  - scripts/build_policy_watch.py
  - templates/policy_watch.html.j2
  - templates/_policy_watch_current.html.j2
  - tests/test_policy_watch_ui.py
  - research/POLICY_WATCH_CURRENT_R1_IMPLEMENTATION_2026-09-08.md
waves:
  - id: R1
    title: Current-source composer + page wire + focused tests (local builder)
    status: in_progress
    next_action: Sol independent review then push/PR/CI; browser evidence if Chrome available
next_action: >
  Sol reviews local head, then publishes same branch; builder waits for same-session ruling.
discoveries:
  - DSC:POLICY-WATCH-CURRENT-R1-CACHE-ITEMS-JINJA
do_not_redo:
  - Do not edit #6928 UK branch or take its same-file collision
  - Do not call us_macro_events from build_current
  - Do not restore VIEW_COPY ticker thesis overrides
artifacts:
  - research/POLICY_WATCH_CURRENT_R1_IMPLEMENTATION_2026-09-08.md
  - engine/policy_watch_current.py
---

## Notes

Bounded R1 only. Full Now/Policy/Communications/World/Influence/Exposure
verticals remain later. #6900 lifecycle preserved.
---
