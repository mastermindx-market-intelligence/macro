---
key: DARKPOOL-PARTICIPATION-DENOMINATOR-20260924
claim: Dark Pool participation can become physically impossible when an early same-day consolidated-volume bar is incomplete; values above 100% were entering the historical baseline, z-score and standout ordering.
falsifier: Run `python3 -m pytest -q tests/test_darkpool_signals.py tests/test_darkpool_desk.py -k participation` against the original engine/builder and show that every FINRA-facility-volume / consolidated-volume observation is already in (0,1], or that the later same-day basket OHLCV denominator does not remove the reproduced current-session violations.
so_what: Prefer the later same-day basket OHLCV volume with exact-date Yahoo fallback, and fail closed on any participation outside (0,1] before history, scoring or ranking. Never clip an impossible value or substitute a prior day for an invalid current observation.
kind: landmine
verified_at: '2026-09-24'
verified_by: python3 -m pytest -q tests/test_darkpool_signals.py tests/test_darkpool_desk.py
scope:
- mastermindx-market-intelligence/macro
- engine/darkpool_signals.py
- scripts/build_darkpool_desk.py
- site/darkpool.html
confidence: verified
---

The repair and reproducible evidence are in `research/evidence/uiux-darkpool-participation-trust-20260924/README.md`. The prospective forward ledger remains nightly-owned and was not advanced by this repair session.
