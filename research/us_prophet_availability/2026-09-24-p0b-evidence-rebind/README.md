# Prophet P0B current-source evidence rebind (2026-09-24)

#6872 (F04-X1) merged the explorer nav item into `templates/_navlinks.html.j2` and committed the re-rendered
`mockups/evidence/prophet-p0b-zero-fouc/rendered-fixture.json` (byte-identical to a fresh deterministic render at
`3e2e81d3fe73`), but did not re-mint the two mobile-layout browser receipts that pin that fixture. Pure main then failed
`tests/test_stock_dashboard_first_frame.py` (ci-pack-9) and every fresh merge-ref inherited it.

This slice re-binds only the closed downstream chain — rendered fixture → two mobile-layout receipts (+16 owner-empty
screenshots) → `manifest.json::repair_extension` — with the canonical remint command the closure gate prints. The
historical P0B baseline (candidate head `3fb76ea8…`, its two pinned screenshots) is carried forward unchanged; no
product runtime changed; production proof: none. Full receipt: `receipt.json`.

Verification: `115 passed, 89 warnings in 56.77s`; closure gate closed; `git diff --check` clean.
