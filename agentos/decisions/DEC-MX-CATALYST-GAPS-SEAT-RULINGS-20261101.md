---
key: MX-CATALYST-GAPS-SEAT-RULINGS-20261101
question: >
  The 2026-11-01 gaps lane (G1–G7) closed eight items and returned three questions that are
  product semantics, not mechanics: (1) should the public scan name the SEC acceptance clock
  (G2-scan); (2) who calls write_partner_pack in production (G5-F4); (3) should one
  event+generation that spans two tickers a reader follows send one email or two (B04-DEDUP)?
answer: >
  (1) G2-scan: the A04 acceptance row is met on the reader path today — a source with no
  official publication renders "First verified available", is not rejected and is not
  relabeled with another clock (tests/test_catalyst_scan_frontend.py::test_a04_*). Naming the
  packet's event_time_utc as "SEC acceptance (UTC)" on the scan is an addition: it needs
  catalyst_scan._public_result to allowlist the field and the HTTP bridge to pass it. The seat
  implemented both ahead of A3 (aae0a47c scan, 827cc5ba bridge): the clock must be named
  SEC_ACCEPTANCE, never lie in the future or after the evidence clock, and renders in whole
  seconds; an unnamed or impossible clock fails closed.
  (2) G5-F4: there is no production caller and none is added now. A partner pack is an
  editorial asset for a named partner (C2 needs a partner editor); scripts/build_catalyst_partner_pack.py
  stays the operator-run, fixture-only builder. A production caller lands with the C2 owner
  gate and must take its route grant from catalyst_source_adapter, never mint one itself.
  (3) B04-DEDUP: carried as a binding precondition of any catalyst sender. The producer
  deliberately keys deliveries per ticker (test_same_event_different_ticker_delivery_keys_do_not_collide),
  and simply dropping the ticker from the idempotency key would make which copy a reader gets
  (DIRECT vs EVIDENCED_INDIRECT) depend on call order. The fix is one consolidated message per
  (user, event, generation) and belongs to the B2 sender wave; the strict xfail
  test_b04_one_dispatch_per_user_per_event_generation_across_tickers keeps it visible, and
  MAIL_CATALYST_ENABLED must not be turned on until that test passes.
rationale: >
  None of the three can produce a wrong public effect today: the flags are off, no sender
  exists, and no partner pack is published. Each ruling keeps the honest fail-closed state,
  names the exact precondition, and avoids changing exactly-once semantics without the
  consolidated-message design that makes the change correct.
alternatives:
  - option: Drop the ticker from the idempotency key now (B04)
    why_not: >
      Order-dependent copy selection and a contradiction with the producer's per-ticker
      contract; no sender exists, so there is no live duplicate to stop.
  - option: Schedule a nightly partner-pack writer (G5-F4)
    why_not: >
      No partner is approved and no editor exists; a scheduled writer would publish an asset
      with no reader and no rights owner.
  - option: Relabel the scan's "Published" source clock as "SEC acceptance" in the frontend only (G2-scan)
    why_not: >
      The frontend cannot know a source's clock basis without the field; guessing from the URL
      would risk the exact relabeling failure A04 forbids.
evidence:
  - "lane/mx-cat-d-final 704a66cb (gaps lane), integrated into PR #10379 at e3ed8103"
  - "engine/marketing/catalyst_lifecycle.py:800 (idempotency key)"
  - "tests/test_catalyst_lifecycle.py::test_same_event_different_ticker_delivery_keys_do_not_collide and ::test_b04_one_dispatch_per_user_per_event_generation_across_tickers (strict xfail)"
  - "tests/test_catalyst_scan_frontend.py::test_a04_first_verified_without_publication_reader_path"
  - "research/marketing_dockets/catalyst_fable_20261031/DESIGN.md rows A04, B04, C01–C03"
affects:
  - WS:MARKETING-X-CATALYST-LOOP
  - engine/marketing/catalyst_lifecycle.py
  - engine/marketing/catalyst_partner_pack.py
  - engine/marketing/catalyst_scan.py
confidence: high
reversibility: easy
decided_by: "fable-meta-ceo (MX Catalyst CEO seat ce215fa3)"
decided_at: 2026-11-01
---

These are seat rulings inside the docket's delegated scope. They grant no flag, sender,
partner or rights effect.
