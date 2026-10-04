# MarketDesk API contract (live-verified 2026-07-07)

This file is the ground truth for how `marketdesk_paper_extractor` talks to MarketDesk.
Everything here was verified against the live site (`marketdesk.ai`) with an authenticated
session. The original project brief assumed DOM-scraping + "listen to network for the blob
URL"; in reality MarketDesk is a **Vue 3 SPA backed by a clean JSON API**. We therefore
discover via the API (through Playwright's *authenticated browser context*, not raw
`requests`), which is deterministic and needs no fragile CSS selectors. A config-driven DOM
fallback is retained for resilience.

## Base
- `MARKETDESK_BASE_URL = https://marketdesk.ai`
- Auth = a normal logged-in browser session (cookies on `marketdesk.ai`). We reuse a Playwright
  **persistent profile** (headed `auth` once; headless thereafter).
- All API calls are `GET`/`POST` under `/api/mobile/...` and return JSON.
- Item IDs (a.k.a. `pathId`) look like `yRoSHLwPSzj` (11-char base62). Everything in MarketDesk
  is a "path node"; leaf nodes with `type == "application/pdf"` are the papers.

## Feeds (each returns an ordered array of item IDs)
- `POST /api/mobile/latest/latest`  body `{}`               → 25 newest item IDs ("Latest" tab).
  - Accepts `{"institutions": ["JPM", ...]}` to filter. Ignores count/offset (fixed 25 window).
- `GET  /api/mobile/latest/picks`                            → "Top Picks" IDs.
- `GET  /api/mobile/latest/saved`                            → "Saved" IDs.
- `GET  /api/mobile/latest/viewed`                           → already-viewed IDs.
- `GET  /api/mobile/count`                                   → unread/counts.

## Browse tree (comprehensive discovery; supports --limit / --since-hours / --backfill)
- `GET /api/mobile/library/browse/current` → `[year_id]` (root children, e.g. one "2026").
- `GET /api/mobile/library/browse/{id}`    → child IDs of a folder node.
- Tree depth: **current → year → month → day → broker(folder) → paper(application/pdf)**.
  - year  children  = months (index 0 = newest month).
  - month children  = days   (index 0 = newest day, e.g. "Jul 7").
  - day   children  = broker folders (e.g. "TME", "SocGen", "Goldman"), `type == "folder"`.
  - broker children = papers, `type == "application/pdf"`.
- Folder vs paper is disambiguated by `type` from `provision`/item detail (`"folder"` vs
  `"application/pdf"`).

## Item metadata
- `POST /api/mobile/items/provision` body `{"pathIds": ["id1","id2",...]}` → **batch**:
  `[{ pathId, parent, name, size, type, t, institution, summary, pages, images }]`
  - `name`        = title (may contain doubled spaces; normalize whitespace).
  - `size`        = PDF size in bytes.
  - `type`        = "application/pdf" for papers, "folder" for folders.
  - `t`           = **publish time, unix seconds** (e.g. 1783422736). This is our `published_at`.
  - `institution` = broker/source abbrev ("JPM","MS","GS","S&T","TME","RBC","CACIB",...).
  - `summary`     = usually "" here (the AI summary lives in `/extra`).
  Use `provision` for bulk hydration — do NOT fetch items one-by-one (be polite to MarketDesk).
- `GET /api/mobile/items/{id}`        → single item, same fields as provision element.
- `GET /api/mobile/items/{id}/extra`  → `{ summary, pages, images }` where `summary` is the
  **MarketDesk AI summary** (markdown, ~600 chars typical) and `images` are chart PNGs.
  Fetch `/extra` only for items we actually decide to process (1 call per new item).
- `GET /api/mobile/items/{id}/path`   → breadcrumb `[{pathId,name}, ...]`
  e.g. `Current > 2026 > July > Jul 7 > Goldman > S&T`. Optional (date derivable from `t`).

## PDF download (the "blob")
- **URL:** `GET https://marketdesk.ai/files/{id}/blob`  (id == item pathId == `blob_id`).
- Behavior: session-authenticated `/blob` → **302** to a signed
  `https://ts{1..5}.marketdesk.ai/files/{id}/preview` → serves `application/pdf` bytes.
  (`ts{n}` is the user's assigned tile/storage host, set via `/api/user/preferences/ts/tsN`.)
- Fetch with the **Playwright browser context request API** (`context.request.get`, which
  carries the session cookies and follows redirects). In-page `fetch()` fails CORS on the final
  cross-origin hop — irrelevant to an HTTP client, which does not enforce CORS.
- `.../blob` exists **only** on the `marketdesk.ai` apex (404 on `ts{n}` directly). Always
  request the apex `/blob` and let it redirect.

## Field → SQLite `papers` column mapping
| papers column          | source                                                            |
|------------------------|-------------------------------------------------------------------|
| blob_id                | item `pathId`                                                     |
| blob_url               | `{BASE_URL}/files/{pathId}/blob`                                  |
| article_url            | canonical deep link `{BASE_URL}/library/browse?item={pathId}`     |
| title                  | item `name` (whitespace-normalized)                              |
| institution           | item `institution`                                                |
| published_at           | ISO-8601 UTC from item `t` (unix seconds)                        |
| marketdesk_age_text    | humanized age from `t` at discovery ("2 hr", "Jul 6")            |
| marketdesk_summary     | `/extra`.summary (markdown)                                       |
| sha256                 | SHA-256 of downloaded PDF bytes                                   |
| pdf_filename           | `{pub_or_disc_date}_{institution}_{slug(title)}_{blob_id}.pdf`   |

## Notes / gotchas
- Titles have doubled internal spaces — collapse to single spaces before slugifying.
- `t` is seconds, not ms.
- Discovery order for "newest": sort candidate papers by `t` desc; the tree's index-0 children
  are already newest-first but always re-sort by `t` to be safe.
- Rate limits: prefer `provision` batches (chunk ~50 IDs) and the browse tree over N single
  GETs; add small jitter between folder walks; cap concurrency (default 5).
