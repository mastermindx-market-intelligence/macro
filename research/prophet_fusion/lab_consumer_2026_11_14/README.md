# Technical Lab consumer proof — 2026-11-14

This folder records local proof of the actual existing builder and page. It is not a deployed-site acceptance or a new research result.

## Evidence

- `qualification.json`: exact source hashes, 55 passing affected tests (52 unit/render plus three Chromium browser cases), successful actual builder and diff hygiene.
- `browser_proof.json`: actual generated HTML identity, Chromium version, desktop/mobile viewports, all 12 arms at each horizon, 11 primary contrasts, primary/secondary visibility, layout bounds and zero page errors.
- `desktop.png`, `mobile.png`: actual first-view screenshots with original cohort evidence first.
- `desktop-secondary.png`, `mobile-secondary.png`: actual 63-session secondary view. Wide tables scroll within their focusable regions; the phone page itself does not overflow.
- `contract_delta.json`: canonical differential gate against source parent; this is a local working-tree preflight, not hosted exact-head CI.

The final source and screenshots were visually reviewed. ANY/A4 wording distinguishes all-false gates from an unfiltered population. Metric-denominator wording distinguishes date-weighted returns/frequency from event-count retention. No sample research statistics, unregistered outcomes, first-seen claims or strategy promotion are added.

## Reproduce

From the repository root with its declared Python/browser dependencies:

```sh
python3 -m pytest tests/test_tech_lab_entry_evidence.py tests/test_tech_lab_entry_evidence_browser.py -q
python3 scripts/build_tech_lab.py
python3 scripts/check_contract_delta.py --base 745478c52ca86df4be1f1aec910a38287ba8a7fc
```

The browser tests serve the real builder output and local assets hermetically. Their pending live-data requests prove static evidence does not depend on the screener finishing. The separate screenshot proof served the materialized `site/` output over a temporary loopback HTTP server, aborted external requests, and closed the server and browsers after verification. Its real native inputs contained 195 signals and no sample fallback.

## Binding

Source parent: `745478c52ca86df4be1f1aec910a38287ba8a7fc`.
Rendered HTML SHA-256: `02d0df0ff1680fdc11c6acfa4cd245548a2d7a9d148719749cfd416dd7ef17e3`.
Production acceptance remains due after normal controller merge and covering render; use the PR's native receipts for that later state.
