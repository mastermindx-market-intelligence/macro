# Compact risk context — 2026-09-08 canonical regeneration

Local proof for the integrated artifact after the 20edb97 merge. Not production
and not Sol release. The accepted compact-risk design is unchanged: HTML partial
blob `b8d427b0eeae2a457e6f7377641a4add54950715`.

## Why this directory exists

The merge-healed `site/macro.html` at head 20edb97 (Git blob
`1be7ac3c431faa3d0e2174e9cd807e852402c4bc`) was a conflict resolution, not a
canonical builder receipt. Sol hold 5580065094 required the real builder/VM/
renderer/writer plus normal asset processing for the current candidate.

## Identities

| Stage | SHA256 / Git blob |
|---|---|
| Builder raw write | `1490abc9546659d6ab03013bd271521ec779ecde6719d2687ae7b9e0f29defe1` |
| After official externalize | `a059a8b44b29666ec4755096d267028a0091e934a53f583f327ef2765ec3c1fc` |
| Final page (optimize + write_page) | SHA256 `057628471cac5296d781a8e711ecc9ad9a53839cd34d3d047ada7318fb8e5cf7` / blob `40ce682d4c95ed5dc14b7bc0b06140413ae5c863` |
| Risk CSS | reused existing `site/assets/css/033cfde9.css` (no new sheet minted) |

Source hashes are in `pre-regen-identities.json` and `identity-binding.json`.
The September 6 page SHA256 `b63e24b1…` remains historical.

## Commands

```
python3 mockups/refs/grey-deer-compact/sol-20260906/build_macro_target.py
python3 mockups/refs/grey-deer-compact/sol-20260908/postprocess_macro_target.py
python3 -m pytest tests/test_risk_envelope_presentation.py tests/test_risk_envelope.py tests/test_live_risk_envelope.py tests/test_risk_state_live_session_floor.py tests/test_synapse_read_gate.py tests/test_horizon_firewall.py tests/test_delivery_waterfall.py tests/test_pricing_power_monitor.py -q
python3 mockups/refs/grey-deer-compact/sol-20260908/verify_browser.py
python3 mockups/refs/grey-deer-compact/sol-20260908/verify_live_context.py
python3 mockups/refs/grey-deer-compact/sol-20260908/verify_settled_states.py
```

Unrelated builder outputs written before the macro-target stop were restored
and are not in this candidate. Not a full-site success claim.

## Local results — not production

- 302 owning/adjacent tests passed, 0 skips.
- 12 anonymous canonical-page cases: dark/light × EN/ZH × 1440/768/390. Public
  explanation/evidence opens from the keyboard; member Risk Detail stays gated;
  settled clock 2026-09-04 remains visible; no page errors or document overflow.
  Light hazard contrast 5.25:1.
- 7 live-feed fixtures PASS, including pending in both themes/languages at 390.
  Settled clock remains visible; largest pending rail 130.375px.
- 16 settled-state fixtures PASS (absent, missing-source, stale, active policy).
- Playwright Target-closed teardown diagnostics appear in driver logs; they are
  not page errors.

HOLD-FOR-SOL remains: do not merge until explicit Sol release of this new head.
