---
key: PROPHET-ABS-RISK-CAN-HIDE-BREACHED-PROTECTION
claim: >
  An absolute entry-to-stop distance can create positive targets for a newly
  emitted bullish plan whose protective stop is already above its entry and
  waiting band. Schema validity and lossless intake do not prove usable protection.
falsifier: >
  python -m pytest tests/test_prophet_bridge.py -k protective_geometry -q;
  compare research/us_prophet_availability/2026-09-17-protective-geometry/actual-board-receipt.json. Any returned HON/RBA/TRN counterexample, non-finite or equal rounded
  loss-side level, waiting band beyond protection, changed valid comparison output,
  or missing refusal accounting falsifies the scoped repair.
so_what: >
  Validate signed protective risk before targets and validate the waiting band
  through the existing geometry failure path. Refuse bad geometry rather than
  fabricate a different stop or rewrite an immutable plan.
kind: constraint
verified_at: 2026-09-17
verified_by: python -m pytest -q tests/test_prophet_bridge.py tests/test_prophet_arena.py tests/test_prophet_integrity.py tests/test_prophet_arena_clock_parity.py
scope:
  - WS:PROPHET-US-ENTRY-TIMING
  - WS:PROPHET-US-AVAILABILITY
  - engine/prophet_bridge.py
confidence: verified
---

The original full real-data experiment is recorded on #7180 comment 5709547215. This source repair continues its original direct geometry operation, not #7180's date scope. Exact preimage, candidate, integrated tree and preserved real-board identities are in `research/us_prophet_availability/2026-09-17-protective-geometry/`. Source code is built; production recovery remains unproven.
