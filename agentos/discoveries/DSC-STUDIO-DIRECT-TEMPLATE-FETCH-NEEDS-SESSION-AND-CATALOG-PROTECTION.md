---
key: STUDIO-DIRECT-TEMPLATE-FETCH-NEEDS-SESSION-AND-CATALOG-PROTECTION
claim: >
  The 2026-09-16 Studio Direct `Failed to fetch template` incident had two independently
  evidenced reliability hazards on the MCP app bootstrap path: frontend session capacity
  reclaim could invalidate the session between `initialize` and `resources/read`, and
  ordinary shared-backend work could head-of-line block catalog/template traffic. On the
  live C2/chatgpt2 gateway after v0.1.4 deployment, the repaired path uses a 30-second
  `lastActive` reclaim grace plus a bounded reserved catalog/template limiter lane while
  keeping total shared-backend concurrency at four and ordinary active work capped at
  three. After the 2026-09-16 13:02:46 -07:00 restart, production logs showed nine
  `resources/read` HTTP 200 responses and zero non-200 resource reads; one real
  `resources/read` completed in 14 ms while log-derived request intervals showed five
  ordinary backend tool requests overlapping its window.
falsifier: >
  Reproduce the same template-fetch failure on the current protected design while proving
  that the affected frontend session remained younger than the configured `lastActive`
  reclaim grace, was not reclaimed, and the catalog/template request was admitted through
  the reserved priority lane; or produce production logs showing a non-200
  `resources/read` after the C2 v0.1.4 restart under those same invariants.
so_what: >
  Future Studio Direct template/app reliability work must test both bootstrap-session
  retention and bounded catalog/template progress under ordinary-tool contention. Do not
  treat a larger `maxSessions` value, healthy generic tools/call traffic, or a successful
  `initialize` as sufficient proof. Keep the shared backend bounded rather than solving
  catalog starvation by unconstrained concurrency, and require a native
  initialize -> notifications/initialized -> resources/read production proof before
  calling the app/template path repaired.
kind: landmine
verified_at: 2026-09-16
verified_by: >
  mastermindx-market-intelligence/Mastermind issue #701 comment 5704400686; live C2
  `/Users/chriswong/.local/share/studio-direct-mcp/private/chatgpt2/logs/err.log` census
  after the 2026-09-16T20:02:46Z gateway restart; live C2 gateway SHA256
  `eb0a3dbd14172e97f1494ec353d7bccbfcffae29b25f4943a30d75223aae3b79`;
  protected Mastermind Skillpack pin `e8803ba3d3ee928d150d7dcac1a1e2bad2dc0d48`
scope:
  - mastermindx-market-intelligence/Mastermind
  - integrations/studio_direct_mcp
  - Studio Direct private C2/chatgpt2 runtime
confidence: verified
---

The user-visible red template card was not evidence that the whole MCP transport was down.
The ordinary tool path remained capable of successful calls while the resource/template
path had its own lifecycle and scheduling failure modes. That distinction is operationally
important because a generic health check can stay green while ChatGPT still cannot render
the app resource it was told to fetch.

The first discriminator came from production logs around capacity churn: frontend sessions
were reclaimed under pressure and later `resources/read` calls could hit a missing session.
The durable repair measures reclaim eligibility from the most recent admitted activity and
holds a 30-second bootstrap grace instead of using a near-immediate creation-age threshold.

The second discriminator was shared-backend queueing. Catalog/template traffic must not sit
behind every ordinary file/process request merely because all traffic shares one backend
owner. C2 v0.1.4 therefore reserves one bounded limiter lane for catalog/template traffic;
it does not create a second backend, a second queueing authority, or unlimited concurrency.

Production proof covered both sides. After restart, the C2 log census contained nine
successful resource reads and no non-200 resource reads. At `2026-09-16T20:03:16.998Z`, a
resource read returned 200 in 14 ms while five ordinary request intervals overlapped that
window. A fresh native bootstrap at `2026-09-16T20:52:43Z` then completed `initialize` 200,
`notifications/initialized` 202, and `resources/read` 200 in sequence, with the resource
read closing in 32 ms.

This discovery does not claim every future ChatGPT template error has these two causes.
It records the two causes proven for this incident and the discriminating acceptance test
future maintainers must preserve. Canonical source integration for the reliability delta
remains separate from the live-runtime proof because Mastermind PR #696 still owns the
incumbent Studio Direct source worktree and was `PRESERVED_DIRTY` at reconciliation time.