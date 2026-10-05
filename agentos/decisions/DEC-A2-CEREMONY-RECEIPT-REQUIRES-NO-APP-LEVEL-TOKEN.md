---
key: A2-CEREMONY-RECEIPT-REQUIRES-NO-APP-LEVEL-TOKEN
question: >
  When the Slack-admin ceremony for the A2 Agent Relay finds an existing app object
  (A0BUDHZ137A) that already requests the two protected bot scopes but carries an inactive
  connections:write app-level token, what must the secret-free ceremony receipt prove before the
  host operator may enrol the bot token through the installed A2 owner?
answer: >
  The app's credential surfaces must equal the protected manifest, and the receipt must say so
  explicitly. The Slack admin deletes the inactive app-level token before the two-scope
  install/reinstall (never activates or regenerates it), does not create a duplicate app, and does
  not reuse the separate Executive Relay identity. The receipt carries: workspace T0BRD2AQXQV; app
  A0BUDHZ137A; bot display Mastermind Relay with its exact bot user ID; bot scopes exactly
  channels:history and chat:write; app-level tokens: none; Socket Mode off; #agent-dispatch
  (C0BSBM78V1N) membership true for that bot user. Only then does the host operator pass the bot
  token through native stdin/TTY to the installed enroll --enable-w3c; the token never appears on
  any carrier.
rationale: >
  The installed enrollment owner (ops/executive_os/a2_agent_relay_enrollment.py at 5b244a2b,
  qualify_token) proves only the team, the supplied bot user ID, the bot scopes against
  REQUIRED_SCOPES and one channel-history read. It cannot observe app-level tokens, so an
  app-level credential would survive enrollment unverified as a latent Socket Mode surface the
  protected manifest (Socket Mode off, token rotation off) does not include. Removing it narrows
  the app to exactly what verify --enable-w3c can prove; no authority is granted, so the ruling is
  integration/acceptance judgment, not a model-authored widening.
alternatives:
  - option: Leave the inactive app-level token in place and proceed with the two-scope reinstall
    why_not: >
      The enrollment owner would attest a least-privilege bot while an unverified app-level
      credential object remained on the same app; the receipt could not state the manifest holds.
  - option: Create a fresh app from the manifest beside A0BUDHZ137A
    why_not: >
      Two app objects for one protected identity is a duplicate carrier; the existing app already
      matches the manifest's bot scopes and only needs cleanup and install.
  - option: Reuse the existing Executive Relay (@mastermind_executive_) bot
    why_not: >
      The protected A2 ceremony explicitly forbids reusing that separate principal; identity
      conflation between the Executive Relay and the Agent Relay is exactly what A2 prevents.
evidence:
  - "Mastermind #1143 issuecomment-5985368514 — Slack admin reconciliation (app exists; inactive connections:write app-level token; no bot identity; not in channel)"
  - "Mastermind #1143 issuecomment-5985262783 — XH-3 pre-credential host gate complete; ceremony steps 1-5"
  - "Mastermind #1143 issuecomment-5985445813 — the integrator ruling this record preserves"
  - "Mastermind ops/executive_os/a2_agent_relay_enrollment.py at 5b244a2b — REQUIRED_SCOPES, qualify_token (team, bot user ID, scopes, one channel read)"
  - "Mastermind config/slack_agent_relay_app_manifest.yaml at 5b244a2b — Socket Mode off, token rotation off, two bot scopes"
affects:
  - WS:EXECUTIVE-AUTONOMY-V1-CLOSURE
  - WS:CHAIRMAN-CONTROL-ROOM
  - A2 Agent Relay enrollment and W3C activation
confidence: high
reversibility: easy
decided_by: coo-fable
decided_at: 2026-10-04
---

## Operating law

The ceremony receipt is accepted only when it states the app's full credential surface, not just
the bot scopes the enrollment owner can see. A later manifest change that adds a surface (for
example Socket Mode) re-opens this decision; until then, any app-level token on the Agent Relay
app is a ceremony defect, and its removal is a Slack-admin act that no session performs or
routes around.
