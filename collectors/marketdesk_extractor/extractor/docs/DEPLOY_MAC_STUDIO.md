# Deploying on a Mac Studio (full pipeline incl. Markdown parsing)

This is the recommended deployment: the Mac Studio runs **everything** — discover, download,
Marker Markdown parsing, R2 upload, and the daily manifest — on a `launchd` schedule.

---

## ⚠️ 0. Location matters (macOS TCC gotcha)

**Do NOT put the project under `~/Documents`, `~/Desktop`, or `~/Downloads`.**
macOS TCC denies `launchd`/`cron` background jobs *read* access to those folders — a scheduled
run there fails with permission errors even though it works when you run it by hand in Terminal.

Put it directly under `$HOME`:

```bash
# on the Mac Studio
cd ~
git clone <your-repo-or-copy> ~/marketdesk_paper_extractor    # or scp/rsync the folder here
cd ~/marketdesk_paper_extractor
```

If you must keep it elsewhere, grant **Full Disk Access** to `/bin/sh` and your venv's `python`
in System Settings → Privacy & Security → Full Disk Access. Using `$HOME` is simpler.

---

## 1. Install

```bash
cd ~/marketdesk_paper_extractor
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e '.[marker,dev]'      # marker = full-text Markdown; dev = tests
playwright install chromium         # downloads the browser (~150 MB, one-time)
```

First `marketdesk run` with `PARSER_BACKEND=marker` also downloads Marker's models
(~1–2 GB, one-time, cached in `~/.cache`).

## 2. Configure `.env`

```bash
cp .env.example .env
```
Edit `.env`:
- `PARSER_BACKEND=marker`
- `R2_ENABLED=true` + `R2_ACCOUNT_ID` / `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` / `R2_BUCKET`
- (optional) `DROPBOX_ENABLED=true` + `DROPBOX_ACCESS_TOKEN` (also `pip install -e '.[dropbox]'`)
- keep `MARKETDESK_HEADLESS=true` (the daily run is headless; only `auth` is headed)

For an external SSD, first create a dedicated root on the mounted volume, then set
the `MARKETDESK_STORAGE_*` guard variables and move **all** mutable paths there as
shown in `.env.example`. Record the exact UUID reported by `diskutil info`; a volume
with the same display name but a different UUID is deliberately rejected.

```bash
mkdir -p /Volumes/STORAGE/MastermindX/marketdesk/{db,data,logs,browser_profile}
marketdesk storage-check
```

Use `MARKETDESK_STORAGE_MIN_FREE_GIB=100` for the production daemon. If the volume
is unplugged or crosses that floor, extraction stops before the provider request and
papers remain queued. Do not point only `RAW_PDF_DIR` at the SSD: SQLite, logs,
manifests, parser outputs, and the persistent browser profile are mutable state too.

## 3. One-time login (needs the Mac's GUI)

```bash
source .venv/bin/activate
marketdesk auth        # a Chromium window opens — log in to MarketDesk once
```
The session is saved to `MARKETDESK_PROFILE_DIR` (`./browser_profile`). All later runs are
headless and reuse it. Re-run `marketdesk auth` only if the session ever expires.

## 4. Verify by hand before scheduling

```bash
marketdesk run --limit 5      # discover + download + parse 5 papers + upload + manifest
marketdesk status
ls data/raw_pdfs data/markdown/* data/manifests
```

---

## 5. Schedule it (launchd — the macOS way)

Two jobs: the pipeline every 30 min on weekday daytime, and a manifest once a day.
Edit the two plists in `deploy/`:
- replace `__HOME__` with your home path (e.g. `/Users/chriswong`),
- replace `__USER__` with your username,
then install:

```bash
cp deploy/ai.marketdesk.run.plist      ~/Library/LaunchAgents/
cp deploy/ai.marketdesk.manifest.plist ~/Library/LaunchAgents/
cp deploy/ai.marketdesk.cleanup.plist  ~/Library/LaunchAgents/   # weekly disk cleanup
cp deploy/ai.marketdesk.trickle.plist  ~/Library/LaunchAgents/   # always-on production puller
launchctl load ~/Library/LaunchAgents/ai.marketdesk.run.plist
launchctl load ~/Library/LaunchAgents/ai.marketdesk.manifest.plist
launchctl load ~/Library/LaunchAgents/ai.marketdesk.cleanup.plist
launchctl load ~/Library/LaunchAgents/ai.marketdesk.trickle.plist
# check:
launchctl list | grep marketdesk
tail -f logs/launchd.run.log
```

To stop: `launchctl unload ~/Library/LaunchAgents/ai.marketdesk.run.plist`.

**Prefer plain cron?** macOS still has it. `crontab -e` and add (adjust the path):
```
*/30 5-18 * * 1-5 cd ~/marketdesk_paper_extractor && ./.venv/bin/marketdesk run --since-hours 36 >> logs/cron.log 2>&1
0 7 * * 1-5       cd ~/marketdesk_paper_extractor && ./.venv/bin/marketdesk manifest --date today >> logs/manifest.log 2>&1
```
(cron on macOS also needs Full Disk Access on `cron` if the project is under `~/Documents` —
another reason to use `$HOME`.)

---

## 6. Resource profile on the Mac Studio

- **Fetch/download/upload/manifest:** ~150–300 MB RAM, seconds–minutes of light CPU. Trivial.
- **Marker parsing:** loads its model set **once per run** (cached across PDFs in that run),
  ~4–8 GB RAM while active, and uses the Mac's GPU via Metal (MPS) when available. Parsing is
  **sequential** (one model set in memory) — comfortable on a Mac Studio. Do **not** raise
  `MAX_CONCURRENT_PARSE_WORKERS` unless you have the RAM for N copies of the model set.
- Disk: PDFs (~0.2–2 MB each) accumulate in `data/raw_pdfs`; they're uploaded to R2, so you can
  prune local copies with the **`cleanup`** command (the SQLite DB keeps the dedup memory, so
  pruned papers are never re-downloaded):
  ```bash
  marketdesk cleanup --older-than-days 14 --dry-run   # preview
  marketdesk cleanup --older-than-days 14             # prune PDFs already in R2
  # add --include-markdown / --include-metadata to also prune those; --no-require-r2 to override
  ```
  Only papers with a confirmed `r2_pdf_key` are pruned by default — a local file is never deleted
  unless its durable copy is already in R2. The `ai.marketdesk.cleanup.plist` runs this weekly.

## 7. Split option (if you later move fetching to the weak VPS)

The stages are decoupled. You can run `marketdesk discover`/`download`/`upload` on the VPS
(`PARSER_BACKEND=none`, ~150–300 MB) and run only `marketdesk parse --pending` on the Mac Studio
against a shared DB + `data/` (or have the Mac pull PDFs from R2). Not needed for the
all-on-Mac-Studio setup above.
