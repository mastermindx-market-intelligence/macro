---
key: SWEEPER-RELEASE-BINDS-TO-COMMENT-ORDER-NOT-HEAD-SHA
claim: "A HOLD-RELEASED comment releases a recorded hold for as long as it stays the newest non-Bot comment; it is not invalidated by later head moves (#8283's release 5956060280 survived two sweeper update-branch head changes), per scripts/merge_on_green.py recorded_hold (:5407) and HOLD_RELEASE_RE (:5196)."
falsifier: "A merge-on-green.yml sweep log (`gh run view <id> --log`) refusing a merge because the HOLD-RELEASED comment predates the current head sha; scripts/merge_on_green.py:5407 comparing against a head."
so_what: "Release once, after checks conclude, and post nothing human afterwards: ANY later human comment re-arms a body hold; a head move alone does not."
kind: runtime
verified_at: 2026-10-02
verified_by: "#8283: release 5956060280 posted 16:0xZ, heads 2ee6e5d5 -> d4c68cb2fb72 via two update-branches, merged 831fc14d41c6 17:45:59Z without a second release; merge_on_green.py:5196/:5407"
scope:
  - "macro"
  - "WS:MARKET-OS"
  - "scripts/merge_on_green.py"
confidence: verified
---

Companion to `DSC:MERGE-ON-GREEN-RELEASE-IS-HOLD-RELEASED-NEWEST-HUMAN-COMMENT`: that record fixes the grammar, this one fixes the binding — comment ORDER, not head identity.
