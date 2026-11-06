---
key: PSKY-SKYD-RENAME-IS-ONE-CIK-DATED-BOUNDARY
claim: >
  Paramount Skydance (SEC CIK 0002041610) changed its common-stock ticker from PSKY to
  SKYD and its listing from Nasdaq to NYSE effective 2026-10-06 (8-K accession
  0001104659-26-113913, filed 2026-10-06); it is ONE issuer and ONE security on both sides
  of a half-open boundary (PSKY valid_to=2026-10-06 exclusive, SKYD valid_from=2026-10-06
  inclusive), and because the daily membership collect already carries SKYD while the
  security master resolved only PSKY, the ticker-news writer's fail-closed universe build
  (scripts/build_qbus_news_universe.py) exits 2 with {"error": "membership_alias_unresolved"}
  on the production host — Package N's P2 activation was blocked by an undated rename, not
  by the writer, the rights receipt, or the Alpaca provider adapter.
falsifier: >
  On a checkout where the dated rename has landed, resolve("membership", "SKYD", 2026-10-11)
  and resolve("membership", "PSKY", 2026-10-05) return different security ids, or
  `python3 scripts/build_qbus_news_universe.py` still exits 2 with membership_alias_unresolved
  against a data/breadth/constituents.parquet that carries SKYD. Either observation refutes
  the one-issuer / dated-boundary reading and reopens the diagnosis.
so_what: >
  Date the rename in scripts/build_security_master.py with ONE RenameEvent(PSKY -> SKYD,
  2026-10-06, EQR->VMRK style, SEC citation as evidence) and leave the universe builder
  fail-closed. Never special-case SKYD inside the writer, never mint a second stable id,
  never invent another boundary date, and never relax membership_alias_unresolved to a
  warning: the refusal is the instrument that caught the gap, and a writer that published
  through it would have served a universe with a silently missing constituent.
kind: data
verified_at: 2026-10-11
verified_by: >
  seat fd47d431: SEC EDGAR 8-K accession 0001104659-26-113913 (CIK 0002041610) read
  2026-10-11; ORCH-N lane census on the production host: `python3
  scripts/build_qbus_news_universe.py` rc=2 {"error": "membership_alias_unresolved"} with
  data/breadth/constituents.parquet carrying SKYD; fix lane
  claude/mi-skyd-identity-rename-20261011 (ORCH-N SKYD-IDENTITY, ubuntu3) commissioned
  with the main rc 2 -> head rc 0 consumer proof as its gate.
scope:
  - macro
  - market-memory
  - scripts/build_security_master.py
  - scripts/build_qbus_news_universe.py
  - data/breadth/constituents.parquet
confidence: verified
---

Boundary semantics are the EQR->VMRK precedent in `scripts/build_security_master.py`
(`RenameEvent` / `RENAME_EVENTS`, dated membership because two simultaneous aliases exist
across the boundary). The consumer proof for the fix is `scripts/build_qbus_news_universe.py`
rc 2 on main -> rc 0 on the fixed head against the committed constituents artifact, plus a
test on the committed security-master artifacts asserting the same id on both sides.
Decision on keeping the builder fail-closed: `DEC:TICKER-NEWS-UNIVERSE-STAYS-FAIL-CLOSED-ON-UNRESOLVED-ALIAS`.
