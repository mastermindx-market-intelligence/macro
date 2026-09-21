---
key: CRYPTO-MARKET-BOARD-CLIPPING-20260921
claim: >
  The public Crypto Market Board clips compact quote text inside an overflow-hidden shelf despite zero document overflow; its fixed desktop symbol column also overlaps long tickers with names.
falsifier: >
  Run python3 -m pytest tests/test_crypto_house_style.py -q and the committed research/evidence/uiux-crypto-market-board-20260921/verify_board.py against the pinned pre-fix snapshot. If its original quote cells all fit at 320 pixels and WSTETH fits without overlapping its name, this claim is false. The preserved before JSON and first browser failure identify those exact counterexamples.
so_what: >
  Check per-row and per-cell geometry, not only the document. Keep the existing source order and live-quote hooks while using a compact identity stack and native table relationships.
kind: landmine
verified_at: 2026-09-21
verified_by: 'python3 -m pytest tests/test_crypto_house_style.py -q'
scope:
  - 'mastermindx-market-intelligence/macro'
  - 'templates/crypto.html.j2'
  - 'tests/test_crypto_house_style.py'
confidence: verified
---

Candidate is source/browser verified, not production-accepted. Current carrier, authority, fixture limits, copied-source identities and exact next action are in research/evidence/uiux-crypto-market-board-20260921/README.md. No prices, signals, allocation, source data or network behavior changed.
