---
key: FABRIC-OPERATOR-ROOT-GRANT-IMMUTABLE
claim: >
  A fabric operator root grant (`fabric_operator_owner.py authorize_root`) is issued once per
  mission root and cannot be re-issued, extended or replaced: a second authorize_root for the same
  root is refused with `root_grant_exists`, the TTL is capped at 7200 s, and once `now >= expires`
  every operator-tier issue for pools that use the capability issuer (grok, glm, glm-frontier)
  is refused with `root_grant_unavailable` (rc=78). Pools that do not use the issuer (cursor,
  bailian, minimax) are unaffected.
falsifier: >
  Run `python3 ext/fabric_operator_owner.py authorize_root --root <existing mission root> --ttl 3600`
  from the meta-ceo-b kit for a root that already holds a grant and have it succeed, or run
  `python3 ext/fabric_operator_issue.py --pool grok --root <root>` after the recorded `expires`
  and have it issue; either disproves the claim. A cursor/bailian/minimax lane refused with
  `root_grant_unavailable` would disprove the pool scoping.
so_what: >
  Issue the root grant only when the operator-tier lanes are about to launch, size its TTL to the
  whole operator window (max 7200 s), and plan the operator-tier (grok/glm) commissions to start
  before `expires`; after expiry route operator work to cursor and executor work to
  bailian/minimax instead of trying to mint a new root (conserving the original root is a
  standing rule). Record `expires` in the orchestrator's progress file at issue time.
confidence: verified
kind: constraint
verified_at: 2026-10-13
verified_by: >
  the meta-ceo-b handoff kit (handoff_kits/meta-ceo-b-2026-09-08) ext/fabric_operator_owner.py (authorize_root: `root_grant_exists` refusal, ttl cap
  7200); the meta-ceo-b handoff kit (handoff_kits/meta-ceo-b-2026-09-08) ext/fabric_operator_issue.py (issue: `root_grant_unavailable` when
  now >= expires); broker row in the meta-ceo-b handoff kit (handoff_kits/meta-ceo-b-2026-09-08) ext/broker/leases.sqlite table operator_root_grants
  (issued ~03:41Z, expires 05:41:45Z 2026-10-13, child_limit 16) read with a read-only SELECT;
  re-issue attempt refused OPERATOR_CAPABILITY_ISSUE_REFUSED/root_grant_exists at ~04:50Z.
scope:
  - fabric
  - orchestration
---

Observed during the Native Chart Engine P2–P4 programme (seat 6dfa7fe4). The grant row is
mission-scoped and immutable by design (the owner refuses replacement to keep one root
identity per mission). Operator-tier grok/glm lanes ce-integrate3b-1013 and ce-kinetic-1013
were launched at 04:55Z/04:59Z, inside the window; the migration master-merge lane was
re-planned onto the seat instead of a post-expiry cursor lane.
