# ROR-1 — Terminal's actual Neural Web consumer and split committed market-plane versions

**Research date:** October 15, 2026. **Status:** pinned-source contract analysis, no authenticated deployment receipt. **Parent:** [Mastermind #1478](https://github.com/mastermindx-market-intelligence/Mastermind/issues/1478). This is a bounded investigation of one ROR-1 user journey; not a new context store, risk/alert engine, entitlement path or capital authority.

## Current source identities and the selected user journey

**Terminal protected master:** `mastermindx-market-intelligence/mastermind-terminal@6159475696f460ca7921bf82cb27b79553c5763f`.

- `terminal/components/NeuralWebStrip.tsx` blob `796489acba56bf196400a4db3c5ed2827f091dd7` polls `/api/nw?f=market_plane`, uses `plane.verdict` to render the chip and calls `isStalePlane(plane,Date.now())`; it links to Macro for detail.
- `terminal/app/api/nw/route.ts` blob `93fe099574b67fb7a8bc4834e4504c3e96f78f38` maps that feed to `market_plane.json`, authenticates by forwarding the requesting user's **own** Supabase cookie, has no shared cache/credential, refuses requests without a cookie at **401**, and relays upstream 401/403 or network errors rather than serving a cached all-clear. This is source design, not authenticated live proof.
- `terminal/lib/upstreams.ts` blob `b682a4afc80e6f34c82345addd5642d4c7574e4b` sets `NW_BASE` to `NW_DATA_BASE` or, by default, `https://www.mastermind-x.com/neuralwebdata`. Current production override selection is **unverified**.
- `terminal/lib/nwPlane.ts` blob `c48d1b6ce4f2213534bdf6a12e8669f72ba73b99` types a verdict with label/score but **no native source session**. Its 4-calendar-day `isStalePlane` derives age from **top-level plane.asof**, not verdict.asof; `stale=true` forces stale. Four days may be an acceptable context-strip grace interval, but cannot serve as acute risk-warning latency.

Thus the route is source-designed as:

```text
Macro engine/neuralweb/mastermind_context.py
  → site/neuralwebdata/market_plane.json
  → authenticated Terminal GET /api/nw?f=market_plane
  → NeuralWebStrip [context-only; 5-minute poll]
```

This does **not** prove the currently deployed Terminal commit, `NW_DATA_BASE` override, same-origin response or any particular subscriber's rendered content. Anonymous 401 is a protected boundary, not proof of a broken service.

## Two different market-plane artifacts already coexist on Macro main

At exact Macro main observation `1b12af09222df183ac61ed5bcabb1ecc6bf5c735`:

| Artifact | Git blob | Display asof | Verdict | Produced at UTC |
|---|---|---|---|---|
| `data/neuralweb/market_plane.json` | `c229bb14f6a1bdabb8c1151bd517a456cfb9c6e1` | 2026-10-14 | 50 / Mixed | 2026-10-14 19:35:57 |
| `site/neuralwebdata/market_plane.json` | `0b45dc27cde5d30de398fc9cfc365d242c7699a8` | 2026-10-15 | 44 / Mixed | 2026-10-15 02:44:17 |

Both report `stale=false`, though they came from **different source-generation times**. The code `build_and_write_market_plane()` promises byte-identical canonical/site copies **at the instant one build runs**, but subsequent automation commits can update the public site variant without advancing the canonical data pointer. Published Git history confirms the site's most recent writer `2f7f702ed60b32cf7971c0b00609eeb715e62f14` at 2026-10-15 07:55:40Z, versus the canonical data pointer's last writer `89d49943bc0fdfd49e9367e287a3632375b432bc` at 2026-10-14 19:37:17Z.

It is **not correct** to assert that every Terminal user saw 50: the default Terminal source targets the *public site* variant, while a Brain or research consumer might read the canonical data pointer. The discrepancy is a version-lineage and user trust issue requiring explicit endpoint/installed-consumer binding.

## Additional actual field-level provenance loss

The canonical `data/neuralweb/world_state.json` (blob `5a79f3a14b90bad891d0fdba808c5176ea9fe51d`) has `verdict.score=50`, `verdict.asof=2026-10-13` and `produced_at=2026-10-14T19:32:19Z`. `build_market_plane()` copies verdict score and labels but drops `verdict.asof`. Because world state lacks top-level `asof`/`as_of`, `_asof_of(world_state)` selects the **processing date**, which becomes plane.asof=2026-10-14 and governs its `stale` field. The Terminal types/staleness helper cannot recover the native verdict clock. The October 13 settled reading may have been entirely legitimate when produced before the October 14 close; this is **a source-clock omission**, not a claim that the prediction was invalid.

The separate six-source audit fixture/receipt under `evidence/plane_provenance_*` proves `VERDICT_SOURCE_SESSION_LOST` at the exact pinned Macro SHA without changing forecast probabilities or alert authority. This file supplies the actual Terminal consumer binding that the earlier five-source comparison lacked.

## Required owner-level acceptance, without unauthorized takeover

1. Existing Neural Web source owner adds a **backwards-compatible native verdict observation session** and source input-health qualifier to the existing plane, without overwriting its processing clock or inventing a universal risk score.
2. Terminal's existing proxy/type/component owner preserves that field through `/api/nw` and displays a truthful date and unavailable/stale qualifier when needed; assess 4-day generic plane staleness separately from acute user-attention SLA.
3. In the actual entitled production/browser path, record `served_at`, returned payload digest, source session, page/Terminal render timestamp and applied freshness law. Check the configured `NW_DATA_BASE` **without exposing credentials**.
4. Prove site/canonical twin provenance and establish which snapshot consumers actually read, rather than asserting byte identity from build-time source alone. Compare expected native market session *at the time of the observation*.
5. This context strip remains display-only and **is not** the owner of crisis notifications or portfolio de-risk. Grey Deer #8132 and Macro #9428 own the alert/foreground integration under their existing Draft/review/permission holds. A correct context strip does not satisfy the original customer-notification acceptance.

**No source edit, worker dispatch, settings toggle, authenticated account access, deployment, release or alert occurred in this evidence pass.**
