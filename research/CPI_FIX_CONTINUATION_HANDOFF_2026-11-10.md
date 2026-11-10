# CPI fix — continuation handoff (2026-11-10)

Program: fix the "CPI detected before its release" defect on mastermind-x.com/macro.html.
Authoring session: Claude (T3), branch `claude/ssd-t3-4a5c5a78-4511ebb22558e9b4`, commit `e3371a5ba69b`.

## Ship state at handoff

- **PR #10930** (https://github.com/mastermindx-market-intelligence/macro/pull/10930) — OPEN, `merge-on-green` ARMED.
  The merge-on-green controller owns the squash-merge; `ci-authority/codex/merge-queue-pilot` failing is a
  universal non-blocking signature (see memory `macro-merge-queue-pilot-check-signature`); `ci-pack-*` were running.
- Independent reviewer subagent (session-owned review law) was resumed to return its verdict; adjudicate any
  BLOCKER/MAJOR before trusting the merge (CI green does not substitute for the review verdict).

## Root cause (proven)

The card was NOT a premature detection of the Nov 10 CPI. It was `cpi:2026-10-14` stuck in
`published_unparsed` for 26 days: BLS's October 2026 release reordered two sentences
("Over the last 12 months, the all items index increased 3.7 percent before seasonal adjustment" and
"The all items less food and energy index rose 2.6 percent over the year"), both YoY regexes in
`parse_cpi_actual` missed, the all-four-values contract failed closed, and the client rendered the
stuck row indefinitely with a dateless "Detected 08:31 ET".

## Fix shipped in the PR

1. `scripts/official_release_parsers.py` — fallback regexes for the new phrasings; parser stays `cpi` v1
   (receipts stay valid); legacy phrasings pinned by tests.
2. `templates/release_publications_live.js` (+ byte-identical site copy, `?v=3a0da984` stamped in
   `macro.html`/`us_stocks.html`) — `published_unparsed` display bounded by
   `poll_window.unresolved_retention_min` (live value 10080 min); dated detection stamps for non-same-day
   rows; >24h unparsed cards relabel "unresolved".

## Post-merge verification checklist (NOT yet done)

Baseline banked pre-merge (2026-11-10 ~04:1xZ):
`cpi:2026-10-14` = `published_unparsed`, `detected_at 2026-10-14T12:31:17Z`,
`source_url https://www.bls.gov/news.release/archives/cpi_10142026.htm`, retention 10080 min declared for CPI.

1. After controller merge: VPS `macro-update` cron (`/usr/local/bin/n`) pulls within ~3 min →
   `macro-live-fast.timer` (~60s cadence) re-runs `scripts/watch_release_publications.py`, whose
   15-min unresolved retry re-fetches without validators.
2. Verify https://www.mastermind-x.com/live/release_publications.json: `cpi:2026-10-14` flips to
   `published` with actual headline 0.6 m/m / 3.7 y/y, core 0.3 m/m / 2.6 y/y (September 2026 data —
   matches Table A of the real release). If the feed entry has rolled off the BLS feed, the row will
   stay unparsed but the CLIENT fix already stops it rendering (26d > 7d retention); that is acceptable.
3. Verify macro.html no longer renders the stale "extracting" card once either (a) the row heals, or
   (b) the static site picks up the new client JS (next render).
4. **Real test: 2026-11-10 08:30 ET (13:30Z) November CPI** — must parse on first detection
   (watch the same JSON ~08:31–08:35 ET).

## Known non-blockers

- 5 pre-existing test failures at pristine HEAD (2 × `test_release_actuals.py`, 3 ×
  `test_vps_live_orchestration.py` — PCE binding-defect quarantine suites, untouched modules);
  verified via tagged stash before authoring, noted in the PR body.
