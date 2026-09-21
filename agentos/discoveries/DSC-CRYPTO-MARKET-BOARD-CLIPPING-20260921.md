---
key: CRYPTO-MARKET-BOARD-CLIPPING-20260921
claim: >
  The public Crypto Market Board clips compact quote text inside an overflow-hidden shelf despite zero document overflow; its fixed desktop symbol column also overlaps long tickers with names.
falsifier: >
  At 320 pixels every original market row and quote must fit within its client width, and WSTETH must fit the original 48-pixel symbol column. The preserved public and native before evidence contradict those predicates.
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
