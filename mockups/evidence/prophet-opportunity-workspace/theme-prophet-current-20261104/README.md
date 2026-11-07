# Current Prophet theme and interaction evidence

Source head: `50cf9d22425587c04ce85c4c2774443abc500a16`.

This package closes the need to adopt the old uncommitted M1 v2 evidence from `e5c2880`. It is a fresh capture from the actual current public page; prior screenshots were retained. No old source binding was restamped.

## Capture and integrity

The unchanged canonical `scripts/capture_page_evidence.py` producer created a `mastermind.p0_evidence.v2` manifest:

- **24/24** attempted states captured.
- Eight rest cells: desktop 1440px / mobile 390px × EN/ZH × light/dark.
- Eight actual browser hover cells and eight actual focus cells on the preflighted visible `a.terminal-link`.
- **16/16** interaction states applied; no missing interaction state.
- All 24 original PNG digests and byte lengths verified.
- Manifest resolves the exact source head above. Independent wrapper provenance verifies the staged public HTML bytes and hashes all seven owned source/artifact paths.
- The full material-UI diff gate against recorded PR base `52abe2e183833a216267942a99513e6c9cbe062f` passes with this receipt.

See [canonical/manifest.json](canonical/manifest.json), [capture provenance](canonical/capture-provenance.json), [local gate receipt](gate-check.json) and [EVIDENCE.yml](EVIDENCE.yml).

## Visual self-check

Actual captures were opened for desktop focused light English and dark Chinese, and mobile hovered light English and dark Chinese. The review examined their top-of-page regions at readable scale; the original full-page PNGs remain intact. Header focus rings, theme treatment, mobile navigation, content hierarchy, Chinese wrapping and the public Featured access-empty presentation remain legible and unclipped in those regions.

The native Screener Cautions repair has separate actual interaction, expanded-content and 320/390/768/1440 checks in [T48 evidence](../t48-caution-touch-20261104/README.md). Its 16-cell proof complements this canonical default-Today capture.

## Honest environment scope

These are anonymous, offline lab captures. Public HTML and static assets are copied byte-for-byte from the committed source; premium data is absent from the staging directory. The outer context policy blocks non-loopback requests, JSON feeds and protected paths. Canonical console records therefore retain intentional network-abort errors, and the page truthfully shows unavailable live/full-board data. Those errors are not hidden or counted as a clean live network result. No account data, authenticated Save, Plan navigation, served installation, production performance or user acceptance is established.

The schema's loading/empty/stale/error/authenticated gaps remain as recorded. Source, local evidence and hosted CI are separate.
