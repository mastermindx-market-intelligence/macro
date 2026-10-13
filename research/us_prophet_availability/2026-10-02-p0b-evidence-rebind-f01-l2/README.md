# Prophet P0B current-source evidence rebind (2026-10-02 — F01 O27 lane 2)

PR #8291 split the F01 live-chip work into two: lane 1 (merged as #8293, the freshness-chip language invariant
test + KNOWN_OFFENDERS baseline) and lane 2 (this slice). Lane 2 lands the theme.css token pair (`--ink-ok`,
`--wash-ok`, `--ring-ok`), the two `.dtp-chip--live` / `.dtp-token.live` swaps to `var(--ink-ok)`, and the
`templates/hk.html.j2` `.tm-state-tag.is-live` swap to `var(--ink-ok, var(--ok))` on a `var(--wash-ok)` background.
Those are the exact bytes preserved from the lane-2 head `44c52ce67480831beea42a0d596497fc7ec5ae63` — six token
lines inserted after `--ink-orange:` in `:root` ≈:372-378, the two chip swaps under `.dtp-*` ≈:1942/:1946, and
hk ≈:196. Without a same-diff re-mint of the P0B browser receipts the closure gate `scripts/check_p0b_receipt_closure.py`
trips and pure main reverts to a red `tests/test_stock_dashboard_first_frame.py`.

This slice re-binds only the closed downstream chain — rendered fixture → two mobile-layout receipts (+16 owner-empty
screenshots) → `manifest.json::repair_extension` — with the canonical remint command the closure gate prints. The
historical P0B baseline (candidate head `3fb76ea8…`, its two pinned screenshots) is carried forward unchanged; no
product runtime changed; production proof: none. Full receipt: `receipt.json`.

Verification: `tests/test_research_screener.py -k fresh_bake` after screener re-pin = 0 failed; `tests/test_freshness_chips_language_invariant.py` = 0 failed; closure gate rc 0 (closed); template/site sync kept. Gate (c) `tests/test_stock_dashboard_first_frame.py` not executed locally — `bs4` not installed on this host; relies on closure gate + CI.