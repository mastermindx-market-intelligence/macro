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
  routes. Order is install, then C1 rebind, then the Slack scope edit (amended 2026-10-07). First,
  the host owner installs one release at or after 6a85e0d6, with services initially stopped. Second,
  the owner runs C1 rebind-release to that generation, the transactional owner in Mastermind #784.
  Only then does the Slack admin add bot scope channels:history to the existing Mastermind Executive
  Relay app (keeping chat:write and groups:history) and reinstall it, without creating an app or
  removing a Dot app. C1 verify follows the scope edit. The receipt carries: workspace T0BRD2AQXQV; the existing
  Executive Relay app ID; bot user U0BT71H4FQE (action-time verified); bot scopes exactly
  channels:history, chat:write and groups:history; app-level tokens: none; Socket Mode off;
  membership true in #sol-runtime (C0BSGABKBFY) and #agent-dispatch (C0BSBM78V1N). Only then does
  the host operator run enroll-shared --expected-bot-user-id U0BT71H4FQE --enable-w3c, which reads
  the enrolled C1 credential locally, so no token is typed, pasted or put on any carrier. If the
  Chairman deliberately re-selects the dedicated app, the receipt of the superseded record (app
  A0BUDHZ137A, scopes exactly channels:history and chat:write, app-level tokens none, Socket Mode
  off, #agent-dispatch membership) is the criterion instead.
rationale: >
  The live C1 relay runs its own generation, 4c148709, not the installed Executive generation:
  launchctl print system/com.mastermind.executive.sol-state-relay shows
  releases/4c148709.../scripts/c1_sol_state_relay.py. install.sh only disables and boots out that
  relay across a generation change and never rebinds its plist or config. C1 at 4c148709
  (c1_runtime.py:33 and :331) accepts only the exact set chat:write + groups:history, and its
  entrypoint (scripts/c1_sol_state_relay.py:49) runs verify_slack_identity on every start. Adding
  channels:history before C1 is rebound to a release containing #1265 therefore makes the next C1
  start fail with C1_SLACK_IDENTITY_REFUSED, and SOL_STATE publication stops. #1265's C1 accepts both
  closed sets during migration, and enroll-shared exists only from 6a85e0d6 (absent at 5b244a2b and
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
  - option: Edit the Executive Relay scopes first, or right after the install but before the C1 rebind
    why_not: >
      The C1 relay keeps running its 4c148709 generation, which refuses the three-scope set at start,
      so its next start fails until it is rebound.
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
  - "Mastermind #1143 issuecomment-6028181298 — the integrator note this record preserves (ordering bullet amended in place 2026-10-07T01:13Z)"
  - "Mastermind #1143 issuecomment-6028474958 — packet-01 checkpoint that found the C1 rebind dependency (#784)"
  - "m2studio read-only launchctl print system/com.mastermind.executive.sol-state-relay — program releases/4c148709.../scripts/c1_sol_state_relay.py (2026-10-07T01:10Z)"
  - "Mastermind ops/executive_os/install.sh at 6a85e0d6 — the C1 relay label is only disabled and booted out; scripts/c1_sol_state_relay.py:49 at 4c148709 verifies identity on start"
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
scopes `enroll-shared` can see. The Slack scope edit is a Slack-admin act. It comes after the host
owner's install of a release at or after 6a85e0d6 and after the C1 rebind to that generation, never
before. No session performs either act or
routes around it. Choosing between the shared and dedicated paths belongs to the packet-03 owner
under the recorded Chairman intent. Only a Chairman reversal of #1265 re-opens the dedicated path.

## Amendment (2026-10-07) — the precondition for the scope edit

The 2026-10-07 00:34Z version said the install alone satisfies the precondition for the Slack scope
edit. That is refuted. The packet-01 checkpoint (Mastermind #1143 issuecomment-6028474958) found it,
and this seat confirmed it read-only on m2studio: C1 runs its own 4c148709 generation, which a
standard install does not rebind. The precondition is now the install plus the C1 rebind (#784). The
receipt fields, the one-path rule and the supersession are unchanged.
