# Risk Radar issued-probability diagnostic publication

The diagnostic introduced in PR7492 was present in the deployed source but absent
from the published scorecard. This slice runs the existing producer once on the
canonical committed input ledgers and commits its normal data/site outputs.
No new template, table, model, scheduler, collector or ledger writer is introduced.

Source base: `78ef3b7b9d50deb02ac06ec7e655b7e892bfd40c`.
Protected procedure: Mastermind`23061ab70a7fb79636b7962d9b440a3de23fe016`.
Authority: continuing Chairman Risk Radar/research improvement instruction.
Direct execution rationale: LOWER_TOTAL_OVERHEAD / CRITICAL_PATH_SHORTCUT.

## Real producer and consumer
`engine.risk_radar_scorecard.write(root=worktree)` wrote identical paired outputs:
`data/risk_radar/scorecard.json` and `site/riskdata/scorecard.json`.
`engine.market_state._rr_scorecard_track('us')` preserved the diagnostic unchanged.
All previous market-window result blocks are byte-equivalent as parsed objects.
Only generated time, normal clock-relative monitoring and the additive US diagnostic
change. Every input-ledger digest was checked before and after; none changed.

82 existing scorecard/reader tests passed. Output SHA256:
`f652d941f873ade54efa1b6c298a2951da3eaf3ad7eab23477a9d9ff35ea9ce6`.
Evidence: `evidence/scorecard-publication-20260920/publication-receipt.json`.

The diagnostic still has33 eligible dates and zero qualifying downside events.
Matched baseline counts29/29/33 and unknown-baseline exclusions are unchanged.
This closes a derived-artifact gap, not a scientific validation or new UI-table gap.
CI, merge and public-artifact verification remain separate publication requirements.
