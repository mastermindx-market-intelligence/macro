---
key: PRODUCTION-RECORDS-ROW-BOUND-STAYS-FAIL-CLOSED-UNTIL-PREREG-V2
question: >
  The market-memory production-records capture refuses on the live options episode corpus
  ("owner source artifact exceeds its row bound": MAX_SOURCE_ROWS = 25_000 in
  engine/neuralweb/market_memory_production_records.py:76 against 29,509 episode rows, and
  the auditor's historical 48 MiB read ceiling against a 50,889,496-byte h60 outcomes
  artifact), observed on the production host on 2026-10-10 and 2026-10-11. Under the
  Chairman's 2026-10-11 "take ownership, clear the blockers" directive, does the seat raise
  the bound (or window the source) to make the capture run, or keep it fail-closed?
answer: >
  Keep it fail-closed at MAX_SOURCE_ROWS = 25_000 and the pinned byte ceiling. The bound is
  re-sized only by the Options Context Audit preregistration v2 (WS:OPTIONS-CONTEXT-AUDIT-PREREG-V2),
  which must size it from LIVE measurement with stated headroom — the charter's own capacity
  refresh (research/options_estate/OPTIONS_CONTEXT_AUDIT_PREREG_V2_CHARTER_2026-09-22.md,
  "Capacity refresh at current main (2026-10-11)") already shows the live corpus exceeding
  the ~25k-row / 48 MiB figures the charter had been asked to size to. Sol's acceptance of
  that preregistration remains the implementation gate; the seat records the live numbers,
  does not pick a new constant, and does not window, evict, or truncate owners.
rationale: >
  The row bound is a preregistered capacity claim, not a tunable: it was reviewed by the
  independent auditor against a corpus that has since roughly tripled, and the refusal is
  the honest statement that the reviewed claim no longer covers production. A constant
  chosen by this seat to "just clear" today's 29,509 rows would be exceeded again within
  weeks at the observed ~2,200-5,600 rows per session, would carry no review, and would be
  precisely the self-excuse the gauntlet exists to stop. Windowing or evicting owners is a
  standing kill (DNR:KILL-OPTIONS-CONTEXT-AUDIT-OWNER-EVICTION). The Chairman's directive
  clears bureaucratic blocks; it does not convert a measured data-capacity limit into one,
  and an authority override cannot cure a data-availability blocker. The lawful move is
  to put the live measurement in front of the v2 charter so the bound is sized once, with
  headroom, under review.
alternatives:
  - option: Raise MAX_SOURCE_ROWS to a value above today's corpus (e.g. 50_000) and widen the byte cap to match
    why_not: >
      An unreviewed capacity claim that the observed production rate overruns again within
      weeks; it would also silently invalidate the auditor's historical read ceiling without
      a successor preregistration.
  - option: Window the source to the newest 25,000 episode rows so the capture runs
    why_not: >
      Owner eviction/truncation is a standing kill (DNR:KILL-OPTIONS-CONTEXT-AUDIT-OWNER-EVICTION)
      and would publish production records that silently omit older episodes.
  - option: Implement preregistration v2 inside this program's W8 recovery work
    why_not: >
      Out of scope and out of custody: WS:OPTIONS-CONTEXT-AUDIT-PREREG-V2 owns the charter,
      do_not_redo forbids implementing v2 inside a recovery PR, and implementation requires
      a separately keyed child after Sol accepts the preregistration.
evidence:
  - "engine/neuralweb/market_memory_production_records.py:76 MAX_SOURCE_ROWS = 25_000 (also :369, :520, :702, :1230)"
  - "research/options_estate/OPTIONS_CONTEXT_AUDIT_PREREG_V2_CHARTER_2026-09-22.md §Capacity refresh at current main (2026-10-11): episodes 29,509 rows / 45,982,874 B; outcomes_h60 25,338 rows / 50,889,496 B > 48 MiB (50,331,648 B); last five sessions 5,598 / 2,161 / 2,280 / 2,319 / 2,544 rows"
  - "PR #7711 MERGED 2026-10-11 as d1b93722ec41 (charter edits recording the live capacity; blob-verified on origin/main)"
  - "Production host journal 2026-10-10 and 2026-10-11: production-records capture refuses with 'owner source artifact exceeds its row bound' (ORCH-OPS read-only census)"
  - "DNR:KILL-OPTIONS-CONTEXT-AUDIT-OWNER-EVICTION; WS:OPTIONS-CONTEXT-AUDIT-PREREG-V2 do_not_redo"
affects:
  - WS:MARKET-INTELLIGENCE-INSTITUTIONAL-BUILDOUT
  - WS:OPTIONS-CONTEXT-AUDIT-PREREG-V2
  - engine/neuralweb/market_memory_production_records.py
  - research/options_estate/OPTIONS_CONTEXT_AUDIT_PREREG_V2_CHARTER_2026-09-22.md
confidence: high
reversibility: easy
decided_by: coo-fable (seat fd47d431, Chairman 2026-10-11 autonomy directive)
decided_at: 2026-10-11
review_by: 2026-11-11
---

Reversal condition: an accepted preregistration v2 that states the new bound, its
measurement basis, and its headroom. Until then the production-records capture's refusal
is correct behaviour and is reported as a scoped limitation (D-prod in the program's lane
matrix), never as a defect to route around.
