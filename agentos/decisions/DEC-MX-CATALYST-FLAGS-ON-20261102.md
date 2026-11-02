---
key: MX-CATALYST-FLAGS-ON-20261102
question: "Should the Catalyst public surface be switched on in production now, and which of the four catalyst switches go on?"
answer: >
  Yes. CATALYST_PUBLIC_ENABLED=1 in production with a freshly generated on-host
  CATALYST_SCAN_RECEIPT_SECRET; CATALYST_UX_ENABLED=0 until the state-accurate banner (PR #10522)
  deploys, then 1; CATALYST_OPTIN_ENABLED=0 until the B1 wiring seam is merged, the consent RPCs
  are provisioned under their own review and one real OTP request is witnessed;
  MAIL_CATALYST_ENABLED untouched (OFF) while the B04 strict xfail stands.
rationale: >
  The Chairman delegated the end-to-end completion to the CEO seat on 2026-11-02 with full
  authority and asked not to be consulted. The public reader and scan are read-only, rights-gated
  and rate-limited; the only effects they add are public GETs of an already-published index. The
  opt-in and mail switches carry identity, consent and delivery effects whose owner gates are
  recorded separately, so they stay off until those gates are met.
alternatives:
  - option: "Keep every switch off until the whole B-tree (opt-in, consent, delivery) is ready."
    why_not: "It leaves the proven A2 journey unobservable on the host and defers the only hosted proof the docket ladder needs next; the public surface carries no new effect."
  - option: "Turn all four switches on at once."
    why_not: "The opt-in route would answer 503 (no configured funnel on main) while the UI invited an email, and the mail path is held by the B04 xfail; neither gate is met."
  - option: "Ask the Chairman to confirm the production switch."
    why_not: "The delegation was explicit and standing; re-asking violates it."
evidence:
  - "Chairman message 2026-11-02: 'Resume in Fable to get this project finished autonomously end to end without requiring me to do anything, u have full authority'."
  - "Host readback 2026-11-02T06:12Z (names only): CATALYST_PUBLIC_ENABLED, CATALYST_UX_ENABLED, CATALYST_OPTIN_ENABLED, CATALYST_SCAN_RECEIPT_SECRET present; MAIL_CATALYST_ENABLED absent; macro-api active after restart."
  - "Hosted proof: /api/catalyst?tickers=V,ZZZQ 200; scan GET/POST 200 PARTIAL; no-JS page served with hidden opt-in section (handoff MARKETING-X-CATALYST-LOOP-2026-11-02-FLAGS-ON)."
  - "PR #10522 independent review rounds 1 and 2 (PASS); PR #10532 B1 wiring review PASS."
affects:
  - "WS:MARKETING-X-CATALYST-LOOP"
  - "app/catalyst_integration.py"
  - "app/catalyst_optin.py"
  - "research/marketing_dockets/catalyst_fable_20261031/README.md"
confidence: high
reversibility: easy
decided_by: "ceo-seat ce215fa3 (Fable) under the Chairman's 2026-11-02 delegation"
decided_at: 2026-11-02
---

# Catalyst flags ON in production

Rollback is one host edit: restore `/etc/macro-api.env` from its dated backup and restart
`macro-api`; the public route then answers 503 again. The opt-in and mail switches each have
their own recorded gate and are not covered by this decision beyond "stay off until met".
