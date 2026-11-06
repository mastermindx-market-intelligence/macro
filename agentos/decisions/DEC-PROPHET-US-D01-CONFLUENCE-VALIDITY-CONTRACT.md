---
key: PROPHET-US-D01-CONFLUENCE-VALIDITY-CONTRACT
question: >
  How does the Prophet US B4 entry-availability vertical obtain an honest owner_confluence
  fact when the sole confluence producer (build_stock_library → site/factordata/signal_gate.json)
  stamps as_of from the last COMPLETED daily close and therefore can never emit a receipt whose
  session equals the decision session before that session's close? (R6 decision D01)
answer: >
  Composition (a) of the wave-0 receipt census: an additive, versioned validity contract
  `signal_gate.validity/v1` on the last-completed-session receipt — source_session == as_of
  (never relabelled), emitted_at == emit.at_utc, expected_last_session and a SIGNED lag with a
  `settled` flag, a next-session-only window (`valid_for_decision_sessions` = the single next
  NYSE session, `expiry_session`), a `lineage_token` = emit.pair_id (v1 carries no revocation),
  and an additive per-verdict `asof`. The B4 consumer returns PASS only when it RECOMPUTES
  freshness from lib.nyse_calendar (source_session == expected_last_session(emitted_at)),
  the decision session is the single next session, emission precedes the decision clock,
  writer/lineage match, and verdict.asof == source_session; every other artifact condition
  degrades to UNKNOWN with a typed reason — the adapter never raises on artifact content.
  The accepted rule is a versioned field inside the hashed strategy identity
  (owner_confluence_source_session_rule = next_session_only/v1).
rationale: >
  The census proved (13/13 committed samples, cron and writer citations) that a same-session
  receipt before a 14:00Z decision is unreachable from the writer's inputs, and that the
  incumbent consumer raises on session mismatch instead of failing closed. Intraday
  re-emission was rejected because engine/signal_gate.py is a close-only, validated statistic:
  run on a partial bar it is a different statistic. Binding from the Prophet Live armed pack
  was deferred because it changes WHICH statistic gates the entry and owes its own validation.
  The Opus red-team of the first draft found two blocking gaps — per-verdict tape staleness
  hidden behind a fresh document date, and an unsettled/ahead source bar reading as fresh —
  which the 01a amendment closes with verdict.asof and consumer-side recomputation; expiry_utc
  was removed because lib.nyse_calendar models no early closes and the close instant already
  belongs to the B4 session policy.
alternatives:
  - option: Intraday re-emission of the gate by the existing producer.
    why_not: Changes the validated close-only statistic; ~15-20 min per full pass; second writer of the pair artifact.
  - option: Bind owner_confluence from the Prophet Live armed pack (provisional-close verdicts).
    why_not: A different statistic never validated as an entry gate; coverage holes in the pack; deferred to a later wave with its own study.
  - option: Leave owner_confluence UNKNOWN (status quo).
    why_not: owner_confluence_gate_may_be_waived is False, so the whole B4 vertical stays inert.
  - option: Date-relabel as_of or delete the session equality check.
    why_not: Forbidden by the census must-nots and by the _PAIR_EMIT_STAMP lineage law; a stale tape would become a legitimate entry signal.
evidence:
  - research/prophet_v4/r6_program/wave0/A_CONFLUENCE_RECEIPT_CENSUS_2026-09-23.md
  - research/prophet_v4/r6_program/rulings/SEAT_RULING_R6-D01-01_2026-09-23.md
  - Macro PR 7581 comment 5789777976 (R3 finding) and the seat custody comment of 2026-09-23 12:41Z
  - Macro PR 7811 (merged 5d8c71c5) carrying the census and the ruling
affects:
  - WS:PROPHET-US-V4-RECOVERY
  - WS:PROPHET-US-ENTRY-TIMING
  - WS:PROPHET-US-AVAILABILITY
confidence: high
reversibility: costly
decided_by: coo-fable
decided_at: 2026-09-23
---

## Scope

Resolves R6 decision D01 for the US flagship. Build units: A1 (producer, new PR off main)
and A2 (consumer, on the incumbent carrier #7581 under the seat's custody notice). Both run
on the external fabric; the seat adjudicates their independent reviews before any ready/arm act.

## What this decision does not do

It does not promote any signal, change rank/gate/size, or make ENTRY_OPEN reachable by itself
(risk_ceiling, liquidity_fillability and gap_velocity stay UNKNOWN through the adapter by
design). It does not authorise a second writer of `signal_gate.json`, a second session oracle,
or any edit of the R5 baseline. Supersession of an artifact within one session is an accepted
v1 residual bounded by the next-session-only window.
