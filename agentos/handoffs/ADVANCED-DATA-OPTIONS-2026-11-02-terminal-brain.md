---
workstream: "WS:ADVANCED-DATA-OPTIONS"
session: brain-terminal-options-freshness-20261102
model: sol
ended_because: ci_handoff
mission_complete: false
mission: Restore dated and correctly scoped Terminal and Brain options data across supported tickers.
state_before: GOOG's August skew was the only options field in the production Brain reader. The Terminal stock rail loaded a separate July snapshot.
changed:
  - path: scripts/topup_thetadata_day.py
    what: The existing daily T1 writer preserves its original priority, maintains receipt-backed partitions and uses remaining normal capacity for the exact Terminal and vendor catalog intersection after the baseline consumer.
  - path: engine/neuralweb/brain_gateway.py
    what: Enrich existing ticker reads from the Options Hub behind the existing options-product feature, with matching ticker, session, expiry, strike and side where present.
  - path: engine/neuralweb/cortex.py
    what: Qualify each family of entry fields on its own source session before returning current market context or contradictions.
verified:
  - claim: GOOG data was absent at more than one production boundary.
    command: "Read production Macro's explain_options_context, the served Hub vol route, the Terminal IV files' internal clocks, and M1's parquet row group date maxima."
    result: "Brain GOOG August 21, IV30 null. All 297 Terminal IV files July 3. Hub GOOG empty on October 29; GOOGL had 24 expiries. 376 of 384 EOD/Greek partitions reached October 30."
  - claim: Daily root selection excluded six previously enrolled names.
    command: "Compare installed _daily_universe() against the canonical store's existing 2026 partitions and _backfill_state.json, then evaluate the candidate roster read-only."
    result: "382 configured roots. Candidate roster 707, with the old 382 in their original order. All six restored to scope: BABA, GOOG, INTC, NFLX, SPCX and UBER; 323 candidate names had no current-year EOD partition."
  - claim: A separate scheduled source failure preceded any pull.
    command: "Read M1 daily_refresh manifest, launchctl state, and response code of the existing symbols health probe."
    result: "01:00 UTC November 3 receipt for D November 2 and S October 30 failed before pulls. Listener was running. Subsequent health probe returned HTTP 429."
  - claim: Focused backend tests passed on the candidate.
    command: "python -m pytest -q tests/test_brain_options_freshness.py tests/test_options_nw_wiring.py tests/test_topup_thetadata_daily.py tests/test_brain_seed_router.py tests/test_brain_tool_economics.py tests/test_ask_brain.py"
    result: "512 passed at the first source checkpoint. The expanded cohort and publisher test group subsequently passed 603 cases, and the gateway and authorization group passed another 529."
  - claim: The full Terminal US candidate list can be measured from production source catalogs.
    command: "Match the served Terminal security manifest, filtered by US equity/fund venue and exact security symbol, to the subscribed local symbol catalog."
    result: "3,445 matches among 3,805 Terminal US equities and funds; 360 unmatched. Catalog hash 967f1d47f589cbd2306dbceb9c0d4640c3e82f06cd7909f3e681de8b9e7ab2f8. The vendor catalog includes historical symbols; only a session-specific observation proves coverage."
  - claim: The vendor terminal recovered and the six original ticker stores now have the October 30 session.
    command: "Inspect the enrolled launchd and listener ownership, record a stalled local HTTP 429 with no established clients, use the documented window-stall restart, verify HTTP 200, run the installed locked one-day writer and read exact session partitions."
    result: "200 with 107555 bytes; all six EOD/Greek/OI root partitions restored through October 30. GOOG November 27 280 put bid 9.40, ask 10.10, IV 30.13%, OI 878 on October 30. The same-day November 2 historical wildcard returned no rows. An additional 311/318 roots completed all three tiers; seven returned no rows."
unverified:
  - claim: Production options quotes for the requested GOOG contract.
    what_would_verify: "A signed-in Brain replay after release with a matching option root, strike, side, expiry, field timestamps and a separately qualified bid/ask source."
  - claim: All optionable symbols visible in Terminal receive fresh observations.
    what_would_verify: "Join the entitled, current optionable listing to the Terminal security manifest. Count current, partial, stale, missing and unsupported separately over two natural updates. The 9,758-name multi-asset manifest is not the optionable denominator."
unresolved:
  - The Hub publishes an empty volatility shell under a common session label for roots without observations. Source values and last good receipts determine what is known.
  - The original local vendor stall was recovered. Full-catalog source reads, Hub publication throughput and next-cycle freshness still require measurement. On a natural scheduled run, remaining capacity follows the normal baseline refresh and records its separate Terminal coverage counts.
  - The signed-in end-of-November GOOG 280 put premium remains unverified. An end-of-day smile point or an ATM tenor is not a bid/ask.
next_actions:
  - Review and land the Macro and Terminal source through their independent release paths. Install the accepted T1 change in the existing M1 daily owner.
  - Read the next scheduled T1 receipt and distinguish rate-limited from offline. Compare per-root Greeks and EOD dates, then the Hub's valued term and smile rows.
  - Verify GOOG separately from GOOGL, SPY, a thinner optionable equity, and a genuine absent symbol in the stock rail and signed-in Brain in Chinese. Record results on Terminal issue 599.
do_not_redo:
  - Retain one T1 writer, the existing Hub publisher, existing product entitlement and the original two operation branches.
  - Never promote an old skew, another share class, an ATM tenor, or a different expiry into an exact option premium.
danger_areas:
  - A 200 response, a current file modification date, and a newer sibling field do not establish an observation for the requested instrument.
  - This change supplies volatility evidence. A non-executable EOD observation must not be represented as a current executable contract quote.
---

Original incident and measured production census are recorded on [Terminal issue 599](https://github.com/mastermindx-market-intelligence/mastermind-terminal/issues/599#issuecomment-6593741630). The companion Terminal operation is `terminal-options-volatility-source-20261102` at base `b79b1e136290978ff7675087de979bb1b42b3713`.
