---
workstream: WS:PROPHET-US-V4-RECOVERY
session: sol/event-workspace-clock-index-k4g-20260918
model: sol
ended_because: complete
prs: [7426]
mission: >
  Prove the K4-G event-workspace v3 index against real current Company Intelligence
  source history without mutating production, then preserve the exact remaining release gates.
state_before: >
  PR 7426 implemented manifest v3, clock repair, indexed reads and incumbent publication,
  but real five-issuer parity and a real AAPL D5 read inside the client budget were unproven.
changed:
  - path: research/company_intelligence/2026-09-19-k4g-v3-real-source-canary.json
    what: Real-source v1/v2-to-v3 migration, five-issuer parity, bounded D5 canary and receipts.
  - path: engine/company_intelligence/event_workspace.py
    what: Fail closed on consecutive duplicate semantic source rows in an authenticated index.
  - path: tests/test_company_intelligence_workspace_v3.py
    what: RED/GREEN discriminator for duplicate adjacent source rows; preserve earlier dropped-middle refusal.
verified:
  - claim: Real current source can be migrated without losing semantic revisions.
    command: Parallel receipt-verified walk of 178 manifests and 890 workspaces, then local v3 construction.
    result: Five of five current issuers match legacy semantic sequences; seven index rows total.
  - claim: The indexed path meets the existing interactive budget on real source bytes.
    command: Native v3 reader with local current envelope and unchanged remote historical objects.
    result: All five issuers in 1.954s; real AAPL D5 in 0.747s, COVERED, later correction PROJECTED.
  - claim: The current post-review source still accepts the same real v3 packet.
    command: verify-current-source.py using current file hashes after the duplicate-row validator change.
    result: Five issuers in 2.081s; AAPL D5 in 0.789s; all authority false.
  - claim: Corrupt adjacent duplicate semantic rows fail closed.
    command: pytest discriminator then complete tests/test_company_intelligence_workspace_v3.py.
    result: RED before validator; GREEN after; 25 passed.
  - claim: The final source and current-main integrated candidate preserve the owning capability.
    command: 11-suite native owner/Prophet battery on source and conflict-free merge tree against main 03f297b6301e7728651baf399acf53d3938ff0cf.
    result: 596 passed, zero failures, 10 existing warnings on each tree; merge tree f61eeaaff13365653705cb8a36ce055b5243566d.
  - claim: Durable records are structurally valid.
    command: python3 scripts/agentos.py validate; Python compile; git diff --check.
    result: 1139 records, zero errors, 88 existing warnings; compile and whitespace pass.
unverified:
  - claim: The incumbent R2 publisher can promote v3 on the real publication path.
    what_would_verify: Normal owner-controlled publication after merge plus marker/index/workspace readback.
  - claim: A real entitled paid user completes covered and typed-unavailable paths in production.
    what_would_verify: Existing #6797 authenticated browser acceptance after deployment.
  - claim: Independent review accepts the exact final head.
    what_would_verify: MastermindX1 review return on PR 7426 after the final source commit.
unresolved:
  - PR remains DRAFT / HOLD-FOR-SOL, unmerged and undeployed.
  - The first real v3 publication and paid-user proof are still separate gates.
  - Quality Earnings +1y identity/B-17/rights and 21-session evaluation remain separate.
next_actions:
  - Consume independent exact-head review on PR 7426; repair only a demonstrated source regression.
  - Preserve DRAFT / HOLD-FOR-SOL until review and source-owner publication gates clear.
  - After accepted review and ordinary merge, prove incumbent R2 v3 publication/readback.
  - Then return to #6797 for real entitled covered and typed-unavailable browser proof.
do_not_redo:
  - Do not repeat the 178-generation real-source census unless source generation changes materially.
  - Do not rebuild v3 schema, B1, D5, auth, candidate population or the +1y compiler.
  - Do not relabel this local-source canary as production authentication or deployment.
danger_areas:
  - The canary used a local v3 current envelope plus unchanged remote historical objects; it did not publish to R2.
  - The B1/security snapshot is real and receipt-bound but is not a complete B-17 population receipt.
  - CI traffic-jam state is deliberately excluded from this continuation and grants no release acceptance.
---

# K4-G v3 real-source canary

The source-serving vertical is now development-proven against current real Company Intelligence bytes. Production publication, independent review and entitled browser proof remain distinct.
