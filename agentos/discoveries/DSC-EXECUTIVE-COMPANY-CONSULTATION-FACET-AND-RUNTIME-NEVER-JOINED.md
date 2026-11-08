---
key: EXECUTIVE-COMPANY-CONSULTATION-FACET-AND-RUNTIME-NEVER-JOINED
claim: >
  At Mastermind protected master 1a7d4002 the two halves of inter-agent consultation are both
  merged, both hermetically tested, and never joined in production. The Company MCP facet
  (integrations/mastermind_company_mcp/consultation.py, CompanyConsultationGateway, four frozen
  tools company.peers/consult/read/reply onto ONE injected async dispatcher; PRs #611/#719/#738)
  is instantiated only in tests/test_company_consultation_mcp.py. The durable half
  (control_plane/consultation_runtime.py, ConsultationRuntime: INTENT mints a
  DIALOGUE_TURN_PENDING Wake obligation, ANSWER_AVAILABLE requires canonical TARGET_ACKNOWLEDGED
  Wake evidence, CONSUMED_BY_REQUESTER closes the loop; PRs #615/#681) is instantiated only in
  tests/test_w6c2_consultation_runtime.py. No module constructs a dispatcher that lands a
  company.consult request on ConsultationRuntime.intent, and no actor-scoped inbox read exists;
  consultation_projection renders all consultations for whoever holds the Runtime. There is also
  no already-started consultation or live-dispatch child to recover: no open PR, lane marker or
  Runtime job carries one.
falsifier: >
  grep -rn "CompanyConsultationGateway(\|ConsultationRuntime(" --include=*.py . outside tests/
  returning a production constructor; or a merged PR whose diff adds a dispatcher joining
  integrations/mastermind_company_mcp/consultation.py to control_plane/consultation_runtime.py;
  or a Runtime event of aggregate_type consultation on any installed Executive runtime.
so_what: >
  IAC-1 (Company Inbox, Sol ruling on Mastermind #600 comment 5810506587) is exactly the join,
  not a new communications plane: one production dispatcher plus one actor-scoped read
  projection over existing Runtime consultation events and Wake lineage. The frozen tool schemas
  and the Wake TARGET_ACKNOWLEDGED rule must not be widened to make the join work; the reserved
  #836 wake_* writers are not needed for it. Bounded child commissioned on branch
  claude/iac1-company-inbox-20260924 from 1a7d4002.
kind: architecture
verified_at: 2026-09-24
verified_by: >
  Fable delivery principal, 2026-09-24 08:3xZ, census on protected master 1a7d4002:
  integrations/mastermind_company_mcp/consultation.py:634-720 (gateway, dispatcher seam);
  control_plane/consultation_runtime.py:163-300, 428, 519, 738, 811-823, 940 (runtime, Wake
  minting and gate, projection); grep of constructors across the repo (tests only); open-PR
  writer census on the consultation, wake_*, session_targets and company_mcp paths; lane markers
  on both admitted hosts; Mastermind #600 comment 5810785658 records the census.
scope:
  - Mastermind
  - agent-fabric-end-to-end-fable-integration-20260913-sol-001
  - integrations/mastermind_company_mcp/consultation.py
  - control_plane/consultation_runtime.py
confidence: verified
---

# The consultation facet and the consultation Runtime were built as two hermetic halves and never joined

Both halves are merged and green, and each test suite injects a fake for the other side.
Nothing in production constructs the dispatcher that would turn a `company.consult` call into
`ConsultationRuntime.intent`, so no real agent-to-agent question has ever produced a Wake
obligation. IAC-1 is that join plus an actor-scoped inbox read; it needs no schema change, no
new store and none of the files reserved by #836.
