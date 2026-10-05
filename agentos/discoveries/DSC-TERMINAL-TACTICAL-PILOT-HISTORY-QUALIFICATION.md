---
key: TERMINAL-TACTICAL-PILOT-HISTORY-QUALIFICATION
claim: In the 2026-09-17 archived pilot inspection, all 22 readable non-INTC 5m/1h static histories last
  observe the regular session on 2026-09-11, lack per-bar historical availability receipts, and all eleven
  inspected 1m static paths returned HTTP 404.
falsifier: 'From Terminal #601 source run python3 scripts/qualify_intraday_research.py --input-dir "$HOME/agent-evidence/terminal-tactical-d0-20260917-sol-002/inputs"
  --start 2026-08-17 --end 2026-09-16 --cutoff 2026-09-16T20:00:00Z --mode as_observed. A later regular
  date or genuine historical availability receipt in the captured input bytes would refute the corresponding
  claim; inspect pilot-static-inventory.json for a successful inspected 1m path. New digests require requalification,
  not rewriting the old receipt. For the chain result, run the same scripts/qualify_intraday_research.py
  consumer with --start 2025-06-16 --end 2026-09-16 --mode corrected_history over the original hashes;
  a different chain count on those bytes refutes the corresponding dated count.'
so_what: 'Keep static freshness separate from live-tail freshness and vendor entitlement. Refresh through
  #595 rather than add an updater; investigate one-minute input ownership separately. Legacy corrected
  bars cannot be admitted as as-observed observations by substituting asof, mtime or serving time. The
  new chain census shows that universal full extended-hours grid filtering would erase the all-name pilot
  and select on observation density. Retain missingness diagnostics and sparse controls; do not manufacture
  steady bidding by forward-fill or call 11 names on the same dates independent episodes.'
kind: data
verified_at: '2026-09-17'
verified_by: 'Terminal #601 commit 773b16f8e825ab4b39ce3c7a5fa5caf32868d55f, terminal:docs/research/TERMINAL_TACTICAL_D0_EVIDENCE_2026-09-17.md;
  real scripts/qualify_intraday_research.py corrected_history/as_observed runs. Continuation at Terminal
  c0f36cb16fadd190ad747fc47a28405d9ec0fca4: session-chain consumer over unchanged original hashes, 2025-06-16
  through 2026-09-16; terminal:docs/research/TERMINAL_TACTICAL_SESSION_CHAIN_EVIDENCE_2026-09-17.md.'
scope:
- WS:TERMINAL-TACTICAL-INTELLIGENCE
- WS:LIVE-ENTRY-RADAR
- WS:TECHNICAL-OPPORTUNITY-INTELLIGENCE
- terminal:ingest/
- terminal:terminal/public/data/intraday/
confidence: verified
---

The capture inventory distinguishes 22 retrieved static files, eleven static HTTP 404 results and three deliberately unrequested INTC cells. It is not an entitlement census or evidence of a full-provider outage. Raw inputs are private; public evidence contains counts and digests only.

## Session-chain continuation, September 17

The same archived files provide 315 scheduled decision dates per name. There are 308 dates per name with some observations in each of prior RTH, prior AH and current PRE. Full nominal five-minute chains: AMD 110, NVDA 308, MU 171, AVGO 80, QCOM 13, SMH 2, QQQ 261, SPY 216, AAPL 71, JPM 0, XOM 0. Three early-close predecessor AH windows remain schedule-unqualified, the first predecessor is outside the request, and the three current missing-tail dates remain explicit. These are input windows, not trades or accuracy. As-observed full chains are zero. Report identities and population limits are in the Terminal evidence document; raw licensed bars remain private.
