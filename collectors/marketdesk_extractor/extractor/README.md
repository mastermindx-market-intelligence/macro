# MarketDesk Paper Extractor

A deterministic, config-driven Python pipeline that authenticates to MarketDesk, discovers new research PDFs via the MarketDesk JSON API, downloads them through an authenticated Playwright browser context, parses them to Markdown, and archives everything to Cloudflare R2 (and optionally Dropbox). A daily JSONL manifest is emitted for local-LLM hand-off.

## How it works

MarketDesk is a Vue 3 SPA backed by a clean REST API (`/api/mobile/...`). Rather than DOM-scraping, this pipeline calls those JSON endpoints directly through a Playwright persistent browser context that carries the user's session cookies. This approach is deterministic — no fragile CSS selectors, no XHR interception needed. A config-driven DOM selector fallback (`config.py` `SELECTORS`) is retained for resilience if the API path ever becomes unavailable.

PDF bytes are fetched via `GET https://marketdesk.ai/files/{item_id}/blob`, which issues a 302 redirect to a signed `ts{n}.marketdesk.ai` preview host. The request is made through Playwright's `context.request.get` (which carries session cookies and follows redirects automatically), not a bare `requests` call.

The pipeline stages are: **discover → download → parse → upload → manifest**, all idempotent and resumable via a local SQLite database.

---

## Install

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -e .
playwright install chromium
```

### Optional extras

Install only the extras you need — heavy ML deps are isolated so importing the package always works with just stdlib + pydantic.

```bash
# PDF -> Markdown via Marker (recommended)
pip install -e '.[marker]'

# PDF -> Markdown via MinerU (alternative)
pip install -e '.[mineru]'

# Dropbox secondary upload target
pip install -e '.[dropbox]'

# Test suite
pip install -e '.[dev]'
```

Only one of `marker` or `mineru` is needed. If neither is installed, the parser backend falls back to `none` (PDF is stored as-is; Markdown output is empty).

---

## First-time authentication

The pipeline reuses a Playwright **persistent browser profile** so you only log in once. The `auth` command opens a headed (visible) browser window:

```bash
marketdesk auth
```

Log in to your MarketDesk account in the browser window. When the page settles the session is saved to `MARKETDESK_PROFILE_DIR` (default `./browser_profile`). All subsequent runs use this profile headlessly.

If downloads start failing with 401/403 errors or empty responses, re-run `marketdesk auth` — the session has likely expired.

---

## Configuration

Copy `.env.example` to `.env` and fill in the blanks:

```bash
cp .env.example .env
```

### Required for R2 upload

```dotenv
R2_ENABLED=true
R2_ACCOUNT_ID=<your Cloudflare account ID>
R2_ACCESS_KEY_ID=<R2 API token key>
R2_SECRET_ACCESS_KEY=<R2 API token secret>
R2_BUCKET=<bucket name>
R2_PREFIX=marketdesk          # key prefix inside the bucket
```

### Optional Dropbox (secondary / fallback)

```dotenv
DROPBOX_ENABLED=true
DROPBOX_ACCESS_TOKEN=<long-lived access token>
DROPBOX_PREFIX=/marketdesk
```

### Priority scoring and watchlist

```dotenv
# Boost papers mentioning these tickers (comma-separated)
WATCHLIST=NVDA,MSFT,AAPL,META

# Skip download of papers below this score (0 = download everything)
DOWNLOAD_ONLY_ABOVE_PRIORITY=false
PRIORITY_THRESHOLD=60
```

### Parser backend

```dotenv
PARSER_BACKEND=marker    # marker | mineru | none
```

Scores combine institution weight (e.g. JPM/GS/MS = 25 pts), keyword hits against title and AI summary, watchlist ticker matches, and a penalty for low-actionability content (recap, morning note, etc.). The score is not just a display field: the trickle allocator drains each tier **by score first** (see below), so it decides what the daily cap actually buys.

### Exclusion filter

Low-value papers are marked `SKIPPED_EXCLUDED` at discovery so they never enter the download queue. `marketdesk filter --dry-run` previews the effect against the existing DB; `marketdesk filter` applies it (and restores rows that no longer match). Reason tags:

| Tag | Meaning |
|---|---|
| `institution` | Publisher is on the exclude set — blogs/newsletters, plus German-language desks such as Zürcher Kantonalbank (`ZKB`), whose notes are Swiss single-name pieces we cannot read. |
| `fx_daily` | A daily FX snapshot/wrap. Real "FX Strategy" / "FX Insights" research is **not** excluded. |
| `minor_geo` | A single-country note on a minor economy. Vetoed when the title also names a major economy ("China–Australia iron ore" stays). |
| `language` | The title is **German** — unreadable to us, so never worth a download slot. Detected purely from the title: an `ß`, or one unambiguously-German finance word (`Ersteinschätzung`, `Wochenausblick`, `Konjunktur`, …, matched in native/ASCII-folded/transliterated spellings), or an umlaut plus a stopword, or two distinct German stopwords. Deliberately **not** under the major-economy veto — a German note about the Fed is still unreadable. Tuned so a single incidental hit ("Zurich Insurance", "Munich Re", "Über-bullish", "rates und …") stays downloadable. |

Title-based reasons (including `language`) ride with `EXCLUDE_TITLE_PATTERNS_ENABLED`; setting it false disables them all.

---

## Daily run

Full pipeline — discover papers from the last 24 hours, download, parse, upload, and write the manifest:

```bash
marketdesk run --since-hours 24
```

Common flags for `run`:

| Flag | Effect |
|---|---|
| `--since-hours N` | Only consider papers published within the last N hours |
| `--limit N` | Cap total papers processed this run |
| `--backfill` | Walk the full browse tree (ignores `--since-hours` filter) |
| `--no-parse` | Skip PDF-to-Markdown parsing stage |
| `--no-upload` | Skip R2/Dropbox upload stage |
| `--no-manifest` | Skip manifest write |

---

## Individual stage commands

Run stages independently when you need to retry or inspect a specific step.

### discover

Find and score new papers; does not download anything:

```bash
marketdesk discover --since-hours 48
marketdesk discover --backfill --limit 500
```

### download

Download pending blobs (papers in `DISCOVERED` state):

```bash
marketdesk download
marketdesk download --force    # also retry FAILED papers
marketdesk download --limit 50
```

### parse

Convert downloaded PDFs to Markdown using the configured backend:

```bash
marketdesk parse
marketdesk parse --limit 20
```

### upload

Upload artifacts to R2 and (if enabled) Dropbox:

```bash
marketdesk upload
marketdesk upload --force      # re-upload even if the R2 key already exists
```

### manifest

Write (and upload) the daily JSONL manifest:

```bash
marketdesk manifest               # today's date
marketdesk manifest --date 2026-07-06
marketdesk manifest --no-upload   # local file only
```

### backlog

Report the **deferred-papers ledger** — everything the download cap left behind
(`DISCOVERED` + `BLOB_FOUND`), which is the backfill plan for when more accounts
are added. Read-only.

```bash
marketdesk backlog                          # top 30 by score, then newest
marketdesk backlog --top 100
marketdesk backlog --json data/backlog.json # full ledger for backfill tooling
```

Prints total candidates split new-window vs backfill, counts by published day
(last 14), counts by institution (top 15), and the top N candidates with
score / institution / date / title. `--json` writes **every** candidate
(`blob_id`, `title`, `institution`, `published_at`, `score`, `status`) — not just
the printed top N.

### status

Show a summary of paper counts by pipeline status:

```bash
marketdesk status
```

Output:

```
papers total: 347
  COMPLETE       218
  DISCOVERED       5
  DOWNLOADED      12
  FAILED           3
  PARSED          89
  SKIPPED_SEEN    20
last_successful_run: 2026-07-07T09:31:05Z
```

### retry-failed

Reset all FAILED papers back to DISCOVERED so they are retried on the next run:

```bash
marketdesk retry-failed
marketdesk run --since-hours 36
```

---

## The trickle daemon (production puller)

`marketdesk trickle` is the **sole production puller**. MarketDesk caps PDF
downloads to a rolling 24h window per account (~75; we configure 70) while the
read/discovery API is uncapped, and ~200 papers/day are published — so a queue is
unavoidable and *selection* is the whole game. `feed.sh` on the M1 is a
**discovery trigger only**; it never downloads.

```bash
marketdesk trickle              # run forever (launchd / KeepAlive)
marketdesk trickle --dry-run    # print the per-account plan, download NOTHING
marketdesk trickle --once
```

What it does each tick:

| Behaviour | Detail |
|---|---|
| **Priority within tier** | New-window papers drain first, and *within* each tier the order is `local_priority_score DESC, published_at DESC` — most valuable first, recency only as the tiebreak. A new-window paper still beats a higher-scored backfill paper. |
| **Reserve** | Backfill only runs when remaining quota exceeds the papers expected to arrive in the next `BACKFILL_RESERVE_HOURS`. |
| **Pacing** | A per-account token bucket refilling at cap/24h spreads the daily budget instead of bursting it in minutes. |
| **Cap bounce** | An over-cap HTML bounce cools the account down until its oldest in-window download ages out (self-calibrating). |
| **Wide self-heal pass** | The periodic refresh is narrow (`NEW_WINDOW_HOURS + 24`), and healing only touches papers inside the window it walks. Every `TRICKLE_WIDE_DISCOVER_EVERY_SEC` (and always on the first refresh after start) the refresh instead walks `TRICKLE_WIDE_DISCOVER_HOURS` back with `TRICKLE_WIDE_HEAL_LIMIT` heals and resets `FAILED` rows to `DISCOVERED`. This replaces the manual wide `marketdesk discover`. |
| **Dead-driver watchdog** | After 3 consecutive ticks where every download died on the Playwright transport ("Connection closed while reading from the driver"), that account's session is closed and re-opened; two consecutive failed re-opens `exit(1)` so launchd's `KeepAlive` restarts the process. Papers hit by a transport failure go back to `DISCOVERED`, never `FAILED`. |

### Fail-closed external storage

For an always-on Mac, put the database, browser profile, outputs, and rotating logs
under one external-volume root and configure the guard:

```dotenv
MARKETDESK_STORAGE_VOLUME=/Volumes/STORAGE
MARKETDESK_STORAGE_ROOT=/Volumes/STORAGE/MastermindX/marketdesk
MARKETDESK_STORAGE_VOLUME_UUID=<diskutil Volume UUID>
MARKETDESK_STORAGE_MIN_FREE_GIB=100
MARKETDESK_PROFILE_DIR=/Volumes/STORAGE/MastermindX/marketdesk/browser_profile
DATABASE_URL=/Volumes/STORAGE/MastermindX/marketdesk/db/marketdesk.sqlite
OUTPUT_DIR=/Volumes/STORAGE/MastermindX/marketdesk/data
RAW_PDF_DIR=/Volumes/STORAGE/MastermindX/marketdesk/data/raw_pdfs
MARKDOWN_DIR=/Volumes/STORAGE/MastermindX/marketdesk/data/markdown
METADATA_DIR=/Volumes/STORAGE/MastermindX/marketdesk/data/metadata
MANIFEST_DIR=/Volumes/STORAGE/MastermindX/marketdesk/data/manifests
LOG_DIR=/Volumes/STORAGE/MastermindX/marketdesk/logs
```

`marketdesk storage-check` proves the exact volume identity, external/writable
status, path containment, and free-space floor. The same check runs before every
trickle tick and immediately before each provider request/write. If the drive is
missing, swapped, read-only, or below the floor, the daemon exits without marking
the paper failed; launchd retries after storage recovers. PDF writes use a sibling
`.part` followed by atomic rename, so a crash cannot leave a completed-looking
partial PDF. The mount point and storage root must already exist—the application
will never create a fallback path on the internal disk.

---

## Cron / systemd schedule

Add to your crontab (`crontab -e`). The working directory must be the project root:

```cron
# Run every 30 minutes during market hours (Mon-Fri, 05:00-18:59 UTC)
*/30 5-18 * * 1-5  cd /path/to/marketdesk_paper_extractor && .venv/bin/marketdesk run --since-hours 36

# Write the final daily manifest at 07:00 UTC each weekday
0 7 * * 1-5        cd /path/to/marketdesk_paper_extractor && .venv/bin/marketdesk manifest --date today
```

For systemd, create a `marketdesk-run.service` + `marketdesk-run.timer` pair. The service `WorkingDirectory` must be the project root so relative paths in `.env` resolve correctly.

---

## Output layout

### Local filesystem

```
data/
  raw_pdfs/
    2026-07-07_GS_st-morning-notes-xyz123.pdf
    ...
  markdown/
    2026-07-07/
      2026-07-07_GS_st-morning-notes-xyz123.md
      ...
  metadata/
    2026-07-07/
      2026-07-07_GS_st-morning-notes-xyz123.json
      ...
  manifests/
    2026-07-07.jsonl
```

### Cloudflare R2 key layout

```
{R2_PREFIX}/raw_pdfs/{YYYY-MM-DD}/{filename}.pdf
{R2_PREFIX}/markdown/{YYYY-MM-DD}/{filename}.md
{R2_PREFIX}/metadata/{YYYY-MM-DD}/{filename}.json
{R2_PREFIX}/manifests/{YYYY-MM-DD}.jsonl
```

With the default `R2_PREFIX=marketdesk`:

```
marketdesk/raw_pdfs/2026-07-07/2026-07-07_GS_st-morning-notes-xyz123.pdf
marketdesk/markdown/2026-07-07/2026-07-07_GS_st-morning-notes-xyz123.md
marketdesk/metadata/2026-07-07/2026-07-07_GS_st-morning-notes-xyz123.json
marketdesk/manifests/2026-07-07.jsonl
```

Dropbox paths follow the same structure under `DROPBOX_PREFIX` (default `/marketdesk`).

---

## Troubleshooting blob downloads

The PDF download flow is:

```
GET https://marketdesk.ai/files/{item_id}/blob
  -> 302 -> https://ts{n}.marketdesk.ai/files/{item_id}/preview
  -> 200  application/pdf bytes
```

`ts{n}` is the user's assigned tile/storage host (set by MarketDesk via `/api/user/preferences/ts/tsN`). The `/blob` endpoint exists **only** on the `marketdesk.ai` apex — always request the apex URL and let it redirect; requests directly to `ts{n}` return 404.

Common failure modes:

| Symptom | Cause | Fix |
|---|---|---|
| All downloads return empty or 403 | Session expired | `marketdesk auth` |
| `ts{n}` returns 404 | Direct request to storage host | Always use `/files/{id}/blob` on apex |
| Papers discovered but not downloaded | Score below threshold | Set `DOWNLOAD_ONLY_ABOVE_PRIORITY=false` or lower `PRIORITY_THRESHOLD` |
| Parse stage produces empty Markdown | Backend not installed | `pip install -e '.[marker]'` or set `PARSER_BACKEND=none` |
| Upload silently skips files | Key already exists | `marketdesk upload --force` |

---

## Tuning DOM fallback selectors

The primary discovery path uses the JSON API and requires no selectors. If the API path becomes unavailable, `discover.py` falls back to DOM scraping using the selector lists in `config.py` `SELECTORS`:

```python
SELECTORS: dict[str, list[str]] = {
    "article_card": ["[data-testid=report-card]", ".report-card", ...],
    "card_title":   [".report-title", ".title", "h3", ...],
    ...
}
```

Each key maps to an ordered list of candidate CSS selectors tried in sequence. Edit `config.py` directly to add new candidates at the top of the list — changes take effect on the next run without restarting.

---

## Local-LLM hand-off

The daily manifest (`data/manifests/YYYY-MM-DD.jsonl` or `{R2_PREFIX}/manifests/YYYY-MM-DD.jsonl`) is a JSONL file where each line is a `ManifestEntry` with the full hand-off contract for downstream LLM pipelines:

```jsonc
{
  "title": "S&T Morning Note — July 7",
  "institution": "GS",
  "blob_url": "https://marketdesk.ai/files/yRoSHLwPSzj/blob",
  "blob_id": "yRoSHLwPSzj",
  "article_url": "https://marketdesk.ai/library/browse?item=yRoSHLwPSzj",
  "published_at": "2026-07-07T06:12:16+00:00",
  "marketdesk_age_text": "3 hr",
  "marketdesk_summary": "Goldman S&T covers overnight flow, positioning divergence in semis...",
  "local_priority_score": 87,
  "sha256": "a3f1...",
  "page_count": 4,
  "parser": "marker",
  "local_pdf_path": "/abs/path/data/raw_pdfs/2026-07-07_GS_st-morning-notes-yRoSHLwPSzj.pdf",
  "local_markdown_path": "/abs/path/data/markdown/2026-07-07/2026-07-07_GS_st-morning-notes-yRoSHLwPSzj.md",
  "r2_pdf_key": "marketdesk/raw_pdfs/2026-07-07/2026-07-07_GS_st-morning-notes-yRoSHLwPSzj.pdf",
  "r2_markdown_key": "marketdesk/markdown/2026-07-07/2026-07-07_GS_st-morning-notes-yRoSHLwPSzj.md",
  "r2_metadata_key": "marketdesk/metadata/2026-07-07/2026-07-07_GS_st-morning-notes-yRoSHLwPSzj.json",
  "status": "COMPLETE"
}
```

Suggested downstream pipeline:

1. Read `data/manifests/YYYY-MM-DD.jsonl` (or fetch from R2/Dropbox).
2. Sort by `local_priority_score` descending; filter by institution, watchlist tickers, or keyword patterns.
3. For each entry, read `local_markdown_path` (or fetch `r2_markdown_key` from R2).
4. Chunk the Markdown, run a second-pass CIO summary prompt, produce a structured signal score.
5. Aggregate across all papers into a daily digest.

`marketdesk_summary` (the MarketDesk AI summary, ~600 chars Markdown) is a cheap pre-filter; read the full Markdown only for papers that pass your first-stage screen.

---

## Safety and compliance

- It does not bypass authentication, paywalls, or DRM — it reuses your own logged-in browser session in the same way a normal browser would.
- Store all credentials (R2 keys, Dropbox tokens) in `.env` only. The `.env` file is `.gitignore`d by default — never commit it.
- Respect MarketDesk's terms of service and rate limits. The default concurrency limits (`MAX_CONCURRENT_PAGES=5`, `MAX_CONCURRENT_DOWNLOADS=5`) and `provision` batching are set conservatively; do not raise them aggressively.

---

## Research Vault hand-off (`publish-vault`)

Each COMPLETE paper can be republished as `<id>.pdf` + `<id>.json`
(`research_vault.sidecar.v1`) into `research_inbox/` of the PRIVATE vault R2
bucket, where the dashboard's hourly ingest consumes it (catalog + full-text
search + the gated viewer).

Config (`.env`): `VAULT_ENABLED=true`, `VAULT_R2_ACCOUNT_ID/_ACCESS_KEY_ID/_SECRET_ACCESS_KEY`
(own Cloudflare account; blank = fall back to the main `R2_*`), `VAULT_R2_BUCKET`,
`VAULT_R2_PREFIX=research_inbox`, `VAULT_TOP_PICK_MIN_SCORE=85`.

Run standalone or as part of `run` (auto when enabled):

```bash
marketdesk publish-vault --limit 200   # resumable; marks papers vaulted in the DB
```

`top_pick` = MarketDesk's own Top-Picks flag OR `local_priority_score >= threshold`.
Institution codes map to display names (GS → Goldman Sachs); `"Bernstein (Data
Centers)"` splits into institution + desk; ids are case-safe (`marketdesk-<id>-<hash6>`).
