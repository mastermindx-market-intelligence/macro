---
key: A2-SHARED-RELAY-RECEIPT-AND-INSTALL-FIRST
question: >
  Mastermind #1265 (merged 2026-10-06T23:57:06Z, protected master 6a85e0d6) records Chairman intent
  to carry A2 Agent Dialogue on the existing Mastermind Executive Relay Slack app instead of a
  dedicated Agent Relay app (A0BUDHZ137A), so no Slack app slot reserved for the Dot estate is
  spent. What must the secret-free Slack-admin receipt prove before the host operator runs
  enroll-shared, and in what order may the Slack scope edit and the release install happen?
answer: >
  One A2 path only: the shared Executive Relay path is current, and A2 is never enrolled by both
  routes. Order is install first, Slack scope edit second: the host owner installs a release at or
  after 6a85e0d6, and only then does the Slack admin add bot scope channels:history to the existing
  Mastermind Executive Relay app (keeping chat:write and groups:history) and reinstall it, without
  creating an app or removing a Dot app. The receipt carries: workspace T0BRD2AQXQV; the existing
  Executive Relay app ID; bot user U0BT71H4FQE (action-time verified); bot scopes exactly
  channels:history, chat:write and groups:history; app-level tokens: none; Socket Mode off;
  membership true in #sol-runtime (C0BSGABKBFY) and #agent-dispatch (C0BSBM78V1N). Only then does
  the host operator run enroll-shared --expected-bot-user-id U0BT71H4FQE --enable-w3c, which reads
  the enrolled C1 credential locally, so no token is typed, pasted or put on any carrier. If the
  Chairman deliberately re-selects the dedicated app, the receipt of the superseded record (app
  A0BUDHZ137A, scopes exactly channels:history and chat:write, app-level tokens none, Socket Mode
  off, #agent-dispatch membership) is the criterion instead.
rationale: >
  The installed C1 at 5b244a2b (integrations/slack_executive/c1_runtime.py, REQUIRED_SLACK_SCOPES
  and _parse_scope_header) accepts only the exact set chat:write + groups:history and raises
  C1_SLACK_IDENTITY_REFUSED on any other set. Adding channels:history before a release containing
  #1265 is installed would therefore fail live SOL_STATE publication. #1265's C1 accepts both closed
  sets during migration, and enroll-shared exists only from 6a85e0d6 (absent at 5b244a2b and
  6e82f9af). On master, qualify_token and _existing_c1_shared_token prove the team, the bot user ID
  (equal to the C1 config's), the exact scope set and one #agent-dispatch history read. They cannot
  observe app-level tokens or Socket Mode, so the receipt must state the full credential surface
  for the same reason as the superseded record. The ruling grants no authority: it is
  integration/acceptance judgment over merged protected source and recorded Chairman intent.
alternatives:
  - option: Keep the dedicated A0BUDHZ137A ceremony as the current path
    why_not: >
      #1265's amendment (research/SHARED_EXECUTIVE_SLACK_RELAY_CONSOLIDATION_2026-10-06.md)
      supersedes the dedicated-app wording for the current execution path by Chairman intent, and
      the dedicated app spends a Slack app slot reserved for the Dot estate.
  - option: Edit the Executive Relay scopes first and install afterwards
    why_not: >
      The installed 5b244a2b C1 refuses the three-scope set, so live SOL_STATE publication would
      fail between the Slack edit and the install.
  - option: Enroll A2 by both routes, or keep both apps installed for A2
    why_not: >
      Two A2 credentials for one dialogue transport is a duplicate carrier. Keeping or removing
      A0BUDHZ137A is a Slack-admin/Chairman decision, not a session act.
evidence:
  - "Mastermind #1265 — merged 2026-10-06T23:57:06Z as 6a85e0d6; mastermindx-3 APPROVED at head e0661dd3"
  - "Mastermind docs/runbooks/shared-executive-slack-relay.md at 6a85e0d6 — fixed Slack contract, safe sequencing, migration compatibility"
  - "Mastermind research/SHARED_EXECUTIVE_SLACK_RELAY_CONSOLIDATION_2026-10-06.md at 6a85e0d6 — Chairman intent; supersedes the dedicated-app wording for the current path"
  - "Mastermind integrations/slack_executive/c1_runtime.py at 5b244a2b (exact two-scope set) and at 6a85e0d6 (ALLOWED_SLACK_SCOPE_SETS)"
  - "Mastermind ops/executive_os/a2_agent_relay_enrollment.py at 6a85e0d6 — qualify_token, _existing_c1_shared_token, _enroll_shared"
  - "Mastermind #1143 issuecomment-6028181298 — the integrator note this record preserves"
supersedes: [DEC:A2-CEREMONY-RECEIPT-REQUIRES-NO-APP-LEVEL-TOKEN]
affects:
  - WS:EXECUTIVE-AUTONOMY-V1-CLOSURE
  - WS:CHAIRMAN-CONTROL-ROOM
  - A2 Agent Relay enrollment and W3C activation
  - C1 SOL_STATE publication during the Slack scope migration
confidence: high
reversibility: easy
decided_by: coo-fable
decided_at: 2026-10-07
---

## Operating law

The receipt is accepted only when it states the app's full credential surface, not just the bot
scopes `enroll-shared` can see. The Slack scope edit is a Slack-admin act that comes after the host
owner's install of a release at or after 6a85e0d6, never before. No session performs either act or
routes around it. Choosing between the shared and dedicated paths belongs to the packet-03 owner
under the recorded Chairman intent. Only a Chairman reversal of #1265 re-opens the dedicated path.
