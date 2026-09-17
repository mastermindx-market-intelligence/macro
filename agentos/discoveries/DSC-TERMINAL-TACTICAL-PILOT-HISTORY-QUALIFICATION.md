---
key: TERMINAL-TACTICAL-PILOT-HISTORY-QUALIFICATION
claim: In the 2026-09-17 archived pilot inspection, all 22 readable non-INTC 5m/1h static histories
  last observe the regular session on 2026-09-11, lack per-bar historical availability receipts,
  and all eleven inspected 1m static paths returned HTTP 404.
falsifier: 'From Terminal #601 source run python3 scripts/qualify_intraday_research.py --input-dir
  "$HOME/agent-evidence/terminal-tactical-d0-20260917-sol-002/inputs" --start 2026-08-17 --end 2026-09-16
  --cutoff 2026-09-16T20:00:00Z --mode as_observed. A later regular date or genuine historical availability
  receipt in the captured input bytes would refute the corresponding claim; inspect pilot-static-inventory.json
  for a successful inspected 1m path. New digests require requalification, not rewriting the old
  receipt.'
so_what: 'Keep static freshness separate from live-tail freshness and vendor entitlement. Refresh
  through #595 rather than add an updater; investigate one-minute input ownership separately. Legacy
  corrected bars cannot be admitted as as-observed observations by substituting asof, mtime or serving
  time.'
kind: data
verified_at: '2026-09-17'
verified_by: 'Terminal #601 commit 773b16f8e825ab4b39ce3c7a5fa5caf32868d55f, terminal:docs/research/TERMINAL_TACTICAL_D0_EVIDENCE_2026-09-17.md;
  real scripts/qualify_intraday_research.py corrected_history/as_observed runs.'
scope:
- WS:TERMINAL-TACTICAL-INTELLIGENCE
- WS:LIVE-ENTRY-RADAR
- WS:TECHNICAL-OPPORTUNITY-INTELLIGENCE
- terminal:ingest/
- terminal:terminal/public/data/intraday/
confidence: verified
---

The capture inventory distinguishes 22 retrieved static files, eleven static HTTP 404 results and three deliberately unrequested INTC cells. It is not an entitlement census or evidence of a full-provider outage. Raw inputs are private; public evidence contains counts and digests only.
