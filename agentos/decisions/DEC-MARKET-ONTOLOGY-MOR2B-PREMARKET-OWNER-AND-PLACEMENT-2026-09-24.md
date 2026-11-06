---
key: MARKET-ONTOLOGY-MOR2B-PREMARKET-OWNER-AND-PLACEMENT-2026-09-24
question: >
  Who is the lawful scheduled owner of the Morning Orientation premarket build (DEC §6 "existing
  workflow/schedule owner"; MO-PAID-011 closes only on an untouched natural premarket run), and
  where does the edition live now that a standalone public `am_edition.html` exists next to the
  `aibrief.html` placement the projection DEC named?
answer: >
  (1) OWNER. The premarket build runs on the VPS live plane as one more unit of the existing
  `macro-*` systemd family (`app/deploy/macro-am-edition.timer` + `.service`, every 30 minutes
  across the ET premarket, self-installed by `app/deploy/update.sh` exactly like the entry-radar
  pair). It writes `/var/lib/macro-live/public/am_edition.{json,html}`; Caddy overlays the two
  exact legacy paths from the live store with existence matchers — `/am_edition.html` inside the
  open-HTML handle (public today, public after) and `/am_edition.json` through `@vps_external`
  inside `@reg_asset` (registered today, registered after). The nightly `daily.yml` and
  `render.yml` bakes remain the writers of the tracked `site/am_edition.*` and become the
  recovery/fallback copy; the VPS service deletes its overlay whenever the pulled bake is newer,
  so the freshest honest clock always wins. No GitHub `schedule:` cron is added or relied on.
  (2) PLACEMENT. The standalone public page `am_edition.html` (built by MO-B F01-1, never rebuilt
  by A) IS the Morning Orientation edition. `aibrief.html` hosts a Morning Orientation band over
  the same `site/am_edition.json` (session state, built-at clock, one-line tape read, deep link);
  that band is the "edition or mode inside aibrief.html" the projection DEC asked for. One
  producer (`scripts/build_am_edition.py`), one artifact, two views.
  (3) CONTENT. The producer is extended to the projection DEC's items 3 (rates/dollar/credit/
  commodity/international context), 6 (research watch conditions, never orders) and 8 (links to
  owning products and Reference entries) using the existing typed-state `_block()` helper; items
  1, 2, 4, 5 and 7 already exist as `session_clock`, `tape_since_prior_close`,
  `todays_calendar`, `cross_asset_plane` and `prior_close_brief_ref`.
rationale: >
  The MOR-2a archaeology (PR #7876) measured that no GitHub `schedule:` lane on this repository
  can guarantee a premarket slot: asia-close crons landed 4–6 h late on every measured day,
  live-quotes delivered ~2.4 % of ticks, intraday-fastpath is skipped under `VPS_LIVE_PRIMARY`,
  and the render lane needs a self-hosted runner that is frequently offline. The one scheduler
  in the estate that fires on time is the VPS live plane: `docs/VPS_LIVE_ORCHESTRATION.md`
  already records the hybrid model "VPS primary / nightly recovery" for display quotes, the live
  overlay, breadth and the S&P heatmap splice, and `macro-entry-radar-pack.timer` already runs a
  "before the US open" evaluation pack on a `Mon..Fri 10..13:20 UTC` calendar. Reusing that
  plane adds one row to an existing ownership table instead of a second schedule plane. The
  tracked `site/am_edition.*` cannot be written on the VPS in place — `update.sh` runs
  `git reset --hard` and an rsync into `site.served` every three minutes — so the overlay must
  live in the external live store, which is precisely what the heatmap's exact-legacy-path
  overlay already does. The producer reads only files that are already on the box: the pulled
  `data/*/latest.json` owners and the VPS's own `/live/quotes.json` (fresher than the committed
  copy, which last changed 2026-08-23). Placement follows the do-not-redo law: B built a working
  public page; A adds the aibrief band and the missing blocks rather than a rival page.
alternatives:
  - option: workflow_dispatch of render.yml from a host clock (census §5 option B).
    why_not: >
      Rejected as the primary. It still depends on a self-hosted render runner being online and
      on a 30+ minute render; the sector-intelligence lane has zero scheduled successes for the
      same reason. Kept only as the manual recovery lever it already is.
  - option: A new GitHub schedule cron (e.g. in daily.yml or a new workflow).
    why_not: >
      Rejected. Measured schedule starvation on this repository makes "premarket" unenforceable,
      and the projection DEC forbids a new workflow family.
  - option: Nightly bake only, with honest clocks (the status quo).
    why_not: >
      Rejected as closure. It is exactly MO-PAID-011's PARTIAL: the page is honest about being
      hours old, but it is not a premarket build from current owner artifacts.
  - option: Client-side refresh from a `/live/am_edition.json` sidecar.
    why_not: >
      Rejected. It re-implements eight typed blocks in page JavaScript, the JSON is a registered
      (401) asset so the sidecar could not be public, and the design law forbids substantive
      runtime-styled surfaces.
  - option: Rebuild the edition inside aibrief.html and retire the standalone page.
    why_not: >
      Rejected. The standalone page is accepted B work (MO-B F01-1); rebuilding it violates
      do-not-redo and would fork one artifact into two producers.
evidence:
  - "PR #7876 (MOR-2a census, head abae3898) §0–§5: NO-LAWFUL-OWNER among schedule lanes; delivery measurements; option (B) host clock."
  - "docs/VPS_LIVE_ORCHESTRATION.md §Decision table (hybrid VPS-primary / nightly-recovery rows) and §Runtime layout (`/var/lib/macro-live/public`, Caddy `no-store`, existence-matcher fallback)."
  - "app/deploy/macro-entry-radar-pack.timer `OnCalendar=Mon..Fri *-*-* 10..13:20:00 UTC`; app/deploy/update.sh:1957-1999 self-install/disarm idiom for a timer+service pair."
  - "app/deploy/update.sh:292-296 `git reset --hard` + `rsync -a --delete site/ site.served/` (why a VPS write into the checkout cannot survive)."
  - "app/deploy/Caddyfile:225-231 `@vps_external` exact-legacy-path overlay (`/marketdata/sp500_heatmap.json`), :344-380 `@reg_asset` (json gated), :424-440 `@open_html` (html public, noindex)."
  - "scripts/build_am_edition.py:233 `_block` typed states, :367-376 tape reads `site/live/quotes.json`, :751 `build_payload(site, data_dir, *, now)`, :815-860 `main()` writes `site/am_edition.json` and renders `templates/am_edition.html.j2` through `lib.pages.write_page`."
  - "git ls-tree origin/main site/am_edition.json site/am_edition.html: both tracked (nightly-committed) artifacts; .github/workflows/daily.yml:4053-4056 and render.yml:824 run the producer."
  - "engine/neuralweb/market_packet.py:86-101 `MACRO_LIVE_DIR` ladder (env → /var/lib/macro-live/public/live → site/live)."
  - "templates/am_edition.html.j2 (323 lines): blocks session_clock/tape_since_prior_close/market_state/cross_asset_plane/todays_calendar/prior_close_brief_ref; includes `_site_nav.html.j2`; public nav card `_public_nav.html.j2:37`."
  - "Live check 2026-09-24: anonymous GET /am_edition.html → 200 (59,542 B); anonymous GET /am_edition.json → 401."
  - "DEC-MARKET-ONTOLOGY-MARKET-ORIENTATION-PROJECTION-2026-08-30.md:135 (edition or mode inside aibrief.html), :140-147 (items 1–8), :198-227 (typed states), :274-285 (candidate paths; closure rule), :335-347 (acceptance)."
affects:
  - "WS:MARKET-OS"
  - "marketontology-complete-parity-fanout-20260826-sol-001"
  - "scripts/build_am_edition.py"
  - "scripts/am_edition_live.py"
  - "templates/am_edition.html.j2"
  - "templates/aibrief.html.j2"
  - "templates/_navlinks.html.j2"
  - "app/deploy/macro-am-edition.timer"
  - "app/deploy/macro-am-edition.service"
  - "app/deploy/update.sh"
  - "app/deploy/Caddyfile"
  - "docs/VPS_LIVE_ORCHESTRATION.md"
confidence: high
reversibility: easy
decided_by: "seat: meta-ceo-a (Claude5 successor, Chairman override 2026-09-06), session 2bb0da13"
decided_at: 2026-09-24
---

# MOR-2b: premarket owner and placement

## The fork

MO-PAID-011 (AM Edition) is PARTIAL: a standalone public page exists and is honest about its age,
but nothing in the estate builds it before the US open. The projection DEC delegated the schedule to
"the existing workflow/schedule owner" and the MOR-2a census proved that no GitHub `schedule:` lane
on this repository is such an owner. The seat had to choose an owner that exists, fires on time, and
does not create a second plane.

## The ruling in one table

| Concern | Ruling |
|---|---|
| Premarket writer | VPS `macro-am-edition.timer/.service` (new members of the existing `macro-*` family), ET premarket window, every 30 min |
| Fallback writer | Nightly `daily.yml` + `render.yml` bakes of the tracked `site/am_edition.*` (unchanged) |
| Served bytes | Caddy existence-matcher overlay of `/am_edition.html` (public, inside `@open_html`) and `/am_edition.json` (registered, via `@vps_external`) |
| Freshest-wins | The service removes its overlay when the pulled bake's `generated_at` is newer |
| Placement | `am_edition.html` is the edition; `aibrief.html` carries a Morning Orientation band over the same JSON |
| Content | Producer gains DEC items 3, 6, 8 as typed blocks; items 1, 2, 4, 5, 7 already exist |
| Closure | MO-PAID-011 → BUILT only after an untouched natural VPS premarket run plus deployed browser proof (8 PNGs) |

## What this does not do

- No new GitHub workflow, cron, or `schedule:` entry. No `data/` writes anywhere. No second producer.
- No change to the static-access boundary: the html stays public and `noindex`, the json stays
  registered. No top-level `/live/*` file_server.
- No rebuild of B's page. No orders, scores or model prose in the edition (A7).

## Reversal

Delete the two units and the `update.sh` block, drop the two Caddy matcher lines, and the page falls
back to the nightly bake on the next three-minute pull. The producer flags default to today's
behaviour, so reverting the VPS lane never touches the nightly.

Build packet: `research/market_intelligence_productization/MARKET_ONTOLOGY_F01_MOR2B_BUILD_PACKET_2026-09-24.md`.
