---
key: PROPHET-P0B-CURRENT-SOURCE-REBIND-MUST-CLOSE-DOWNSTREAM-RECEIPTS
claim: >
  The committed Prophet P0B rendered-fixture receipt can drift even when every
  rendered HK/Canada output byte remains identical, because it binds current
  integrated source inputs such as engine/i18n.py. Updating only that leaf is
  incomplete: both mobile-layout receipts bind the rendered-fixture bytes, and
  the bounded repair-extension manifest binds the fixture plus those two
  browser receipts. A lawful current-source maintenance repair must therefore
  close the entire existing receipt chain while preserving the historical P0B
  baseline/target and all screenshot/output claims byte-for-byte.
falsifier: >
  Run tests/test_stock_dashboard_first_frame.py against current protected main.
  This discovery is falsified if the generator output differs semantically or
  visually beyond current-source hashes, if the complete self-binding owner can
  pass after changing only rendered-fixture.json, or if historical baseline,
  target, screenshot, population, route, output or browser-case evidence must
  change to bind the current i18n source.
so_what: >
  Do not weaken the deterministic equality test or repair a consumer PR such as
  protective geometry with unrelated fixture bytes. Maintain the one existing
  P0B evidence chain on a bounded shared-source carrier. Current-source drift is
  a repository evidence defect, not evidence that the old historical browser
  proof occurred on newer source.
kind: constraint
verified_at: 2026-09-18
verified_by: >
  Operation prophet-p0b-evidence-rebind-20260918-sol-001 on protected Macro
  7233b2cd182976c8d1707cc2cba13725c358bf37. RED reproduced the deterministic
  equality failure. The generator differed only in the two HK/Canada i18n SHA
  leaves. Updating the closed downstream chain yielded 114/114 PASS; output
  hashes stayed identical. Exact receipt: research/us_prophet_availability/
  2026-09-18-p0b-evidence-rebind/receipt.json.
scope:
  - macro
  - WS:PROPHET-US-AVAILABILITY
  - mockups/evidence/prophet-p0b-zero-fouc
  - tests/test_stock_dashboard_first_frame.py
confidence: verified
---
