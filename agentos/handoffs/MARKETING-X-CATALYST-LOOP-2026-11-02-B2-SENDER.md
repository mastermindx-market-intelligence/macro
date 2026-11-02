---
workstream: WS:MARKETING-X-CATALYST-LOOP
session: claude/ssd-mx-catalyst-b2-sender-0934aa6d20e78b47
model: fable
ended_because: ci_handoff
mission: >
  CEO seat ce215fa3 building the B2 sender wave the 2026-11-01 gaps ruling deferred: one
  consolidated message per (user, event, generation) so that a reader following several
  tickers of one event is mailed once (docket B04), without the order-dependent copy that
  dropping the ticker from the key alone would have caused.
state_before: >
  FunnelService.deliver took one per-ticker PublicRevision and keyed the ledger claim
  catalyst:<event>:<generation>:<ticker>:<user>; the strict xfail
  test_b04_one_dispatch_per_user_per_event_generation_across_tickers pinned the duplicate;
  MAIL_CATALYST_ENABLED OFF on the host under that precondition; the host has no SMTP.
changed:
  - path: engine/marketing/catalyst_lifecycle.py
    what: ConsolidatedRevision + consolidate (set validation), FunnelService.deliver_generation (per-item rights before roster and per reader; bundle = followed tickers with evidence newer than the consent; key catalyst:<event>:<generation>:<user>), deliver() kept as the one-ticker wrapper, format_generation (one block per ticker, one unsubscribe link)
  - path: app/catalyst_optin.py
    what: ExistingMailerDelivery.deliver formats a bundle; deliver_update loads the whole generation through load_public_revisions (single-revision loader as the one-ticker case) and calls deliver_generation
  - path: tests/test_catalyst_lifecycle.py
    what: B04 xfail removed (passes); per-ticker drip test rewritten to the claimed-once contract; keys without ticker; test_b2_* block (consolidated dispatch, unfollowed/already-seen items, NOT_SECOND_VALUE, SUPPRESSED, refused sets, rights before roster and per reader, formatter)
  - path: tests/test_catalyst_optin.py
    what: seam stubs take deliver_generation; whole-generation seam test with protocol-mismatch shapes; one consolidated mailer.send per user
  - path: tests/test_catalyst_integration.py
    what: sender stub records revision.tickers; the composed-journey key assertion drops the ticker
  - path: docs/ops/catalyst-sender.md
    what: sender contract, producer contract, gates and the single human gate
  - path: agentos/decisions/DEC-MX-CATALYST-B2-CONSOLIDATED-SENDER-20261102.md
    what: the seat decision
  - path: agentos/workstreams/WS-MARKETING-X-CATALYST-LOOP.md
    what: lane B2-SENDER; OWNER-GATES next_action updated
verified:
  - claim: one event+generation across two followed tickers mails a reader once, and a repeat is ALREADY_CLAIMED
    command: pytest tests/test_catalyst_lifecycle.py -k "b04 or b2_ or drip"
    result: 20 passed (the former strict xfail now passes without its marker)
  - claim: the owner, lifecycle and integration suites hold on the lane head
    command: pytest tests/test_catalyst_lifecycle.py tests/test_catalyst_optin.py; pytest tests/test_catalyst_*.py
    result: 157 passed; 745 passed with the one pre-existing sparse-tree failure (test_staged_session03_primary_ui_and_fallback, 503 under pytest on a sparse tree; a direct TestClient probe returns 200)
unverified:
  - claim: the lane head is green on CI and independently reviewed
    what_would_verify: the PR's ci-authority rollup and a READ_ONLY reviewer verdict recorded on the PR
  - claim: docket B2 acceptance (one permitted update to a designated consenting test recipient, inbox observed, revoke, next dispatch suppressed)
    what_would_verify: an SMTP provider on the macro-api host plus that recipient (Chairman spend; named once, never re-asked), then MAIL_CATALYST_ENABLED=1 under a recorded decision
unresolved:
  - No production producer implements load_public_revisions yet; deliver_update stays the frozen private seam with no caller
  - MAIL_CATALYST_ENABLED stays OFF (no SMTP on the host)
next_actions:
  - Merge after CI + review; then update OWNER-GATES in the workstream to "B2 needs SMTP + recipient" only
  - When the identity/consent RPCs (PR #10538) and the B1 wiring (PR #10532) are live, the sender is reachable through deliver_update for a producer that supplies a generation
do_not_redo:
  - The consolidated sender contract and the B04 test — DEC:MX-CATALYST-B2-CONSOLIDATED-SENDER-20261102
  - The per-ticker drip is not a supported producer contract; do not reintroduce a ticker in the ledger key
danger_areas:
  - A sender return the lifecycle cannot classify is EFFECT_UNKNOWN and freezes the batch; never retry it
  - format_generation must never let producer copy into the subject beyond the ticker list (the subject names tickers only)
prs: []
decisions: [DEC:MX-CATALYST-B2-CONSOLIDATED-SENDER-20261102, DEC:MX-CATALYST-GAPS-SEAT-RULINGS-20261101]
---

# B2 sender wave — one consolidated message per (user, event, generation)

The lane branch is `claude/ssd-mx-catalyst-b2-sender-0934aa6d20e78b47` on main `8e52c8e7efa6`.
Rung reached: DELIVERED (lane head, tests green locally); CI and review are the next two rungs.
