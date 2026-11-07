---
key: MX-CATALYST-B2-CONSOLIDATED-SENDER-20261102
question: >
  DEC:MX-CATALYST-GAPS-SEAT-RULINGS-20261101 carried B04-DEDUP as a binding precondition of
  any catalyst sender: one event+generation spanning two tickers a reader follows mailed that
  reader twice, because the idempotency key embedded the ticker, and simply dropping the
  ticker would have made the copy a reader gets depend on call order. What is the sender
  contract that mails each reader once per (event, generation) without that defect?
answer: >
  One consolidated message per (user, event, generation). The producer hands the lifecycle
  EVERY per-ticker revision of a generation at once (FunnelService.deliver_generation; the
  private seam deliver_update loads them through load_public_revisions, falling back to the
  single-revision loader only as the one-ticker special case). The lifecycle validates the set
  (same event and generation, distinct tickers, at most 12 items, each revision approved),
  reads live rights for every item before the roster and again per reader before the sender,
  and builds each reader's bundle deterministically: the followed tickers whose evidence is
  newer than that reader's consent. The idempotency key is catalyst:<event>:<generation>:<user>;
  the incumbent email_log unique key stays the only delivery claim. ExistingMailerDelivery
  formats the bundle with format_generation: one item renders exactly as before, several keep
  each ticker's own rights-qualified block under a subject that names only the tickers, with one
  unsubscribe link. The single-revision deliver() remains as a wrapper, so a producer that drips
  one generation ticker by ticker gets ALREADY_CLAIMED from the second call on and nobody is
  mailed twice; that drip is no longer a supported producer contract. The strict xfail B04 test
  passes unchanged. MAIL_CATALYST_ENABLED stays OFF: the host has no SMTP, and the docket's B2
  acceptance (one permitted update to a designated consenting test recipient, inbox observed,
  revoke, next dispatch suppressed) needs an SMTP provider and that recipient, which is the
  Chairman's spend and the one human gate this program names.
rationale: >
  The ruling's objection was order-dependent copy, not the key itself. Handing over the whole
  generation removes the order: the bundle is a pure function of (generation set, reader's
  consent at the send boundary). Keeping the ledger key per user is what makes one dispatch per
  user per generation a property of the sender, not of the caller's discipline. Excluding items
  the reader already saw when consenting preserves "an unchanged thesis creates no email
  obligation" per ticker, and holding the whole message when any followed item loses rights at
  the per-reader read keeps the existing fail-closed rights boundary.
alternatives:
  - option: Keep the per-ticker key and send one email per ticker
    why_not: >
      Fails docket B04 (a reader following two tickers of one event is mailed twice) and the
      strict xfail test that pins it.
  - option: Drop the ticker from the key but keep the per-ticker deliver() as the only entrypoint
    why_not: >
      The rejected 2026-11-01 option: which copy a reader gets would depend on which ticker the
      producer happened to deliver first.
  - option: Let the lifecycle discover the generation's ticker set itself from the revision authority
    why_not: >
      The RevisionAuthority port exposes is_current and read_public_rights only; inventing a
      listing contract there widens the producer boundary the adoption rulings froze.
evidence:
  - "engine/marketing/catalyst_lifecycle.py: ConsolidatedRevision, consolidate, FunnelService.deliver_generation, format_generation"
  - "app/catalyst_optin.py: ExistingMailerDelivery.deliver (bundle), deliver_update (load_public_revisions)"
  - "tests/test_catalyst_lifecycle.py::test_b04_one_dispatch_per_user_per_event_generation_across_tickers (xfail removed, passes) and the test_b2_* block"
  - "tests/test_catalyst_optin.py::test_b2_private_seam_hands_the_whole_generation_to_the_lifecycle, ::test_b2_canonical_mailer_sends_one_consolidated_message_per_user"
  - "tests/test_catalyst_lifecycle.py + tests/test_catalyst_optin.py: 157 passed (no xfail left); tests/test_catalyst_*.py: 745 passed, 1 pre-existing sparse-tree staged-UI failure"
affects:
  - WS:MARKETING-X-CATALYST-LOOP
  - engine/marketing/catalyst_lifecycle.py
  - app/catalyst_optin.py
confidence: high
reversibility: easy
decided_by: "fable-meta-ceo (MX Catalyst CEO seat ce215fa3)"
decided_at: 2026-11-02
---

A seat ruling inside the docket's delegated scope. It changes the sender contract in source
only: no flag, SMTP, scheduler, DB or OTP effect, and MAIL_CATALYST_ENABLED stays OFF on the
host. Docket B2 acceptance still needs an SMTP provider and a designated consenting test
recipient (Chairman spend; named once here, never re-asked).
