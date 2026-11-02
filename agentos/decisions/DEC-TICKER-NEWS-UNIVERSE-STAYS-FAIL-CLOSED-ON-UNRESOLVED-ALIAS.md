---
key: TICKER-NEWS-UNIVERSE-STAYS-FAIL-CLOSED-ON-UNRESOLVED-ALIAS
question: >
  The ticker-news writer's universe build (scripts/build_qbus_news_universe.py) refuses
  with rc 2 {"error": "membership_alias_unresolved"} because the membership collect carries
  SKYD and the security master only knows PSKY, which blocks Package N's P2 VPS activation.
  Does the seat relax the refusal (warn-and-skip, drop the unresolved symbol, or special-case
  SKYD in the writer) to unblock activation, or keep the builder fail-closed and date the
  rename in the security master?
answer: >
  Keep the builder fail-closed exactly as built (rc 2, membership_alias_unresolved) and fix
  the DATA: one dated RenameEvent(PSKY -> SKYD, on=2026-10-06, vendors membership+yahoo,
  SEC 8-K 0001104659-26-113913 as evidence) in scripts/build_security_master.py, in the
  EQR->VMRK style, so the company keeps one security id across the half-open boundary
  (PSKY valid_to=2026-10-06 exclusive, SKYD valid_from=2026-10-06 inclusive). The consumer
  gate is main rc 2 -> fixed head rc 0 on the same committed constituents artifact, and the
  artifact row-diff must be limited to the PSKY/SKYD rows plus receipt bookkeeping. P2 waits
  for that merge; it is not activated around the refusal.
rationale: >
  The refusal did its job: a universe built through it would have served Benzinga headlines
  for a constituent set with a silently missing S&P member, and nothing downstream (Terminal
  rail, dedupe, rights receipt) can detect a missing symbol. Relaxing it converts a loud,
  attributable rc 2 into a quiet data defect in every later rename. Special-casing SKYD in
  the writer moves identity knowledge out of the one owner that has it (the security master)
  and would have to be repeated for every future rename. The dated RenameEvent is the
  smallest change, is the established idiom (EQR->VMRK, dated because two aliases coexist
  across the boundary), and keeps the fix where the next rename will look for it. The
  Chairman's 2026-10-11 directive assigns the seat to clear the blocker, and the lawful
  clearing is the data fix, not a weaker gate.
alternatives:
  - option: Downgrade membership_alias_unresolved to a warning and build the universe without the unresolved symbol
    why_not: >
      Silent omission of an index constituent from the news universe; the instrument that
      caught this gap would never fire again, and no downstream surface can notice the hole.
  - option: Special-case SKYD (or a PSKY->SKYD alias map) inside scripts/run_qbus_news.py or the universe builder
    why_not: >
      Duplicates identity knowledge outside the security master, must be repeated per rename,
      and leaves the committed security-master artifacts wrong for every other consumer.
  - option: Mint a new stable security id for SKYD and leave PSKY's history on the old id
    why_not: >
      Same CIK, same security; a second id breaks continuity for every history-keyed
      consumer (holdings, breadth, news dedupe) and contradicts the EQR->VMRK precedent.
  - option: Activate P2 on the VPS with the writer pointed at a hand-edited universe file
    why_not: >
      An operator-side artifact outside the committed pipeline; fails the next nightly
      regeneration and is exactly the "work around the refusal" path this decision forbids.
evidence:
  - "ORCH-N lane census 2026-10-11: production host `python3 scripts/build_qbus_news_universe.py` rc=2 {\"error\": \"membership_alias_unresolved\"}; data/breadth/constituents.parquet carries SKYD"
  - "SEC EDGAR 8-K accession 0001104659-26-113913, CIK 0002041610, filed 2026-10-06: ticker PSKY -> SKYD, Nasdaq -> NYSE, effective 2026-10-06"
  - "scripts/build_security_master.py: RenameEvent / RENAME_EVENTS with the EQR->VMRK dated-membership template and SECURITY_SUPERSESSIONS"
  - "DSC:PSKY-SKYD-RENAME-IS-ONE-CIK-DATED-BOUNDARY"
  - "Fix lane claude/mi-skyd-identity-rename-20261011 (ORCH-N SKYD-IDENTITY, ubuntu3, watcher bjwwbonx8) commissioned 2026-10-11 with gates: one id across the boundary, row-diff limited to PSKY/SKYD, main rc 2 -> head rc 0, new test red on main"
affects:
  - WS:MARKET-INTELLIGENCE-INSTITUTIONAL-BUILDOUT
  - scripts/build_security_master.py
  - scripts/build_qbus_news_universe.py
  - scripts/run_qbus_news.py
  - data/breadth/constituents.parquet
confidence: high
reversibility: easy
decided_by: coo-fable (seat fd47d431, Chairman 2026-10-11 autonomy directive)
decided_at: 2026-10-11
---

F-a (date the rename) is the fix; F-b (keep fail-closed) is this record; F-c (other
consumers of the security master that may have cached the PSKY-only resolution) stays with
those consumers' owners and is listed, not performed, by this seat. The P2 VPS activation
of Package N resumes only after the rename PR is MERGED and the VPS has pulled it.
