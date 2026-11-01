# Marketing X Catalyst — SEC source cycle writer (A3-W-r2) runbook

Status: writer and reader merged to main in PR #10379 (`636abe2a66d2`); the
production deploy installs and arms the writer timer; the public flags stay OFF.
This file is the only runbook home for the cycle.

## What the cycle does

`scripts/run_catalyst_source_cycle.py` (module: `engine/marketing/catalyst_source_cycle.py`)
is a bounded, scheduled, off-render job. For a fixed pilot universe of at most
100 issuers it:

1. reads the issuer's SEC EDGAR submissions JSON;
2. finds 8-K / 8-K/A filings carrying Item 2.02 accepted in the last 7 days;
3. retrieves the filing's EX-99.1 earnings release **in memory**, hashes it
   (sha256) and projects its figures with the incumbent Earnings Release
   binder (`bind_release_document` + `replay_receipt`, mirroring
   `catalyst_packets.py` exactly);
4. drops the document bytes immediately and publishes exactly ONE canonical
   index JSON as an immutable `source_sync` snapshot.

A later cycle re-verifies an already-published filing by re-fetching the
document and comparing the sha (carried filing: one document GET, no
filing-index GET, no re-parse), keeping the FIRST retrieval identity
(`first_retained_at`, `first_retained_receipt_id`) stable across cycles.

### D4 retention rule (rights decision)

SEC document bytes are NEVER persisted — not to the store, not to a file, not
to a log, not to an exception message. The index keeps only: URL, sha256,
projected figures, filing clocks and the first-retrieval receipt id. The
writer calls no incumbent SEC-byte persistence function; its only store write
is the index snapshot itself.

## Store namespace

Everything the cycle writes lives under

    marketing/catalyst-sec-source/v1/

through `NamespacedSourceStore` (`engine/marketing/catalyst_source_store.py`).
The production Filing Forensics pointer
(`fundamental_forensics/sec-source/v1/latest.json`) is UNTOUCHED: the
namespaced wrapper prefixes every key, so the incumbent pipeline's latest
pointer does not move and its namespace is never written.

## Index schema

    marketing.catalyst_sec_cycle_index/v1

at `catalyst/cycle_index.json` inside each snapshot (canonical JSON:
sort_keys, `(",", ":")` separators, `ensure_ascii`, no trailing newline).

## Exit codes

| Code | Meaning |
|---|---|
| 0 | COMPLETE — every issuer processed ok |
| 2 | REFUSED — refusal before any SEC request (invalid user agent / universe / budget / store / prior index); nothing published |
| 3 | TRUNCATED — the request budget ran out, or SEC refused access (403) or rate-limited (429 after retries); later issuers are `not_checked` and carry their prior events; the index is still published |
| 4 | PARTIAL — at least one issuer ended not ok |
| 5 | PUBLISH_FAILED — the snapshot publish failed; the prior pointer stays as it was |
| 6 | FAILED — no issuer was swept, or none was verified (only deferred/failed work, including a halt before anything was verified); nothing published and the prior pointer is left unchanged, but the reader serves it only until 10 minutes after that snapshot's `cycle_started_at` (`MAX_SNAPSHOT_AGE`), so FAILED on two consecutive runs means the catalyst surface is dark; reason `no_issuer_swept` / `no_issuer_verified` / the halt reason; systemd records a failure |

## Request budget and rate

- Budget: 150 SEC GETs per cycle (`--max-requests`, hard ceiling 150).
- Rate: one shared `SecRequestPacer` at 0.2 s minimum interval (5 requests per
  second ceiling), retries included in the budget; retryable statuses
  (429/500/502/503/504) retry at most 4 attempts with exponential backoff
  capped at 8 s.
- Shape: a bootstrap cycle costs 1 submissions GET per issuer plus 2 GETs per
  NEW in-window Item 2.02 filing (index + document); a later cycle costs
  1 + 1 per carried filing. With the 20-issuer pilot and a 5-minute timer that
  is roughly `20 + 1 per carried filing` GETs every 5 minutes in steady state.

## Install (performed by the deploy)

`app/deploy/update.sh` installs both units from the checkout when the reviewed
bytes differ from `/etc/systemd/system/`, verifies them with
`systemd-analyze verify`, reloads systemd, restarts the timer when a unit
changed, and runs `systemctl enable --now macro-catalyst-source-cycle.timer`
on every deploy. Arming the writer publishes only the namespaced index; it does
not turn on `CATALYST_PUBLIC_ENABLED` and restarts no other unit.

## Environment variable NAMES (values never recorded here)

- `R2_RESEARCH_BUCKET`, `R2_RESEARCH_ENDPOINT`, `R2_RESEARCH_ACCESS_KEY_ID`,
  `R2_RESEARCH_SECRET_ACCESS_KEY` — production store credentials (presence on
  the host UNKNOWN; `open_production_store` refuses with a reason code when
  they do not yield an available R2Store).
- `SEC_USER_AGENT` — REQUIRED SEC contact agent (precedence: `--user-agent`
  CLI flag, then this env; there is NO fallback to `config.yml` or any other
  collector's config). When neither is set the writer refuses with exit 2,
  reason `user_agent_unresolved`. Its value is never printed or logged.
- `CATALYST_PUBLIC_ENABLED` — reader wiring flag, NOT used by this lane.
- `RESEARCH_LOCAL_STORE` — when set, the production opener refuses
  (`research_local_store_set`); local dry-runs use `--local-store` instead.

## Verifying with --local-store

    python3 -m scripts.run_catalyst_source_cycle \
        --local-store /tmp/catalyst-dryrun \
        --universe config/catalyst_pilot_universe.json

prints exactly one JSON line (`outcome`, `exit_code`, `requests_used`, ...).
The local store root then contains the namespaced snapshot tree only; reading
it back is `engine.marketing.catalyst_source_store.read_latest_index(open_local_store(dir))`.

## Rollback

    systemctl disable --now macro-catalyst-source-cycle.timer

The `marketing/catalyst-sec-source/v1/` namespace can simply be left in place
(snapshots are immutable and nothing production reads them yet); deleting the
namespace prefix is also safe once the timer is off.

## GAPS

- Snapshot accumulation: the timer publishes a new immutable snapshot every
  5 minutes (~288 per day) with NO pruning policy; an owner decision on
  retention/pruning is still needed.
- RESOLVED 2026-11-01: SEC `acceptanceDateTime` timezone. Checked against
  live EDGAR for MSFT 0001193125-26-436122 and KO 0001628280-26-067403: the
  submissions-JSON value (`...Z`) equals the filing index page's "Accepted"
  time (US Eastern) plus 4 hours under EDT, so the `Z` is true UTC and the
  writer's UTC parse (`_parse_clock`) is correct. No code change.
- 8-K/A attestation is rare in submissions data: `amendsAccessionNumber` is
  often absent, so most 8-K/A filings surface as `unattested_amendment`
  skips rather than corrections.
- Nothing public consumes this index until the operator turns on
  `CATALYST_PUBLIC_ENABLED` and restarts macro-api (see "Reader and wiring").
## Reader and wiring (A3-R)

The reader half lives in `engine/marketing/catalyst_source_adapter.py`
(`build_admitted_source`) plus `app/catalyst_source_wiring.py`
(`configure_from_environment`), mounted from `app/main.py` at import time.

- What the adapter serves and its fail-closed rules: the five read callables
  `catalyst_admission` consumes (`issuer_universe`, `recent_events`,
  `public_grant`, `document_observation`, `source_coverage`), all derived from
  the single published cycle index under `marketing/catalyst-sec-source/v1/`.
  The snapshot must be structurally valid and no older than 10 minutes
  (`MAX_SNAPSHOT_AGE`); a loaded state is cached for 60 s
  (`CACHE_TTL_SECONDS`) so a down store is not hit per request and a failing
  load yields an empty fail-closed state; F4 — a public grant is minted only
  for an issuer's own EX-99.1 under an 8-K / 8-K/A Item 2.02 whose archive URL
  carries the universe CIK; D4 — no SEC document bytes are persisted anywhere
  and the observation is built from the index record alone.
- Production rights family (F1): admission asserts
  `sec_issuer_earnings_release_facts`, never a bare sec_edgar family. The
  anonymous scan refuses (empty read) until that registry row is on main.
- Wiring runs at app import: after setting `CATALYST_PUBLIC_ENABLED=1` the
  macro-api process must be restarted for the source to be configured.
- Enabling order: steps (1)–(3) are done — the
  `sec_issuer_earnings_release_facts` rights row is on main, the deploy armed
  the writer timer, and the first production cycles are recorded below. The
  operator still acts for (4) setting the flag and (5) restarting macro-api.
- Rollback: unset `CATALYST_PUBLIC_ENABLED` and restart macro-api — the scan
  returns its existing disabled status and admission stays unconfigured.
- Environment variable NAMES only: `CATALYST_PUBLIC_ENABLED`,
  `RESEARCH_LOCAL_STORE`.

## Production writer proof (636abe2a66d2)

Observed 2026-11-01 on the macro-api host (counts and states only; no env values):

- Deploy: macro-api restarted 22:00:34Z on 636abe2a66d (`/healthz` commit and checkout both 636abe2a66d). The cron deploy tick installed both catalyst units (reviewed bytes) and armed the timer.
- Flags OFF in production: `CATALYST_PUBLIC_ENABLED`, `CATALYST_OPTIN_ENABLED`, `CATALYST_UX_ENABLED`, `MAIL_CATALYST_ENABLED` all absent from the service env. `/api/catalyst` 503; `/api/catalyst/scan` GET (`?tickers=AAPL`) and POST both 503 "Catalyst scan is not publicly enabled"; `/api/catalyst/nojs` 503.
- Writer env names present: `SEC_USER_AGENT` and the four `R2_RESEARCH_*` names; `RESEARCH_LOCAL_STORE` absent.
- Timer at 22:09:06Z: `macro-catalyst-source-cycle.timer` enabled + active; last trigger 22:08:28Z, next 22:13:28Z (5-minute cadence). Service is a timer-driven oneshot (inactive between runs): Result=success, ExecMainStatus=0, NRestarts=0.
- First two cycles (22:03:59Z and 22:08:41Z finished): both COMPLETE exit 0; issuers ok 20 / incomplete 0 / failed 0 / not_checked 0; events 6; snapshot published both runs. SEC GETs 32 on the bootstrap cycle, 26 on the next (inside the 150 budget).

## Production reader proof (in-process, flags OFF)

Observed 2026-11-01 ~22:25Z on the macro-api host, checkout `7bc879e90cf5`
(counts and public status names only). Admission was configured inside a
probe process only; the running macro-api, its flags and the timer were not
touched.

- `production_store=True`; the `sec_issuer_earnings_release_facts` emission
  is allowed by the rights registry.
- `read_qualified_event_context(now)`: 6 qualified packets, 20 issuers, and
  a source-coverage receipt covering all 20 tickers (complete-current).
- `scan_tickers([t])` across the 20 pilot names: 14 NO_QUALIFIED_EVENT
  (COMPLETE_EMPTY), 1 SUPPORTED (V, PUBLIC_QUALIFIED), 5
  TEMPORARILY_UNAVAILABLE (PARTIAL: AMZN, MA, MSFT, GOOGL, KO).
- The five unavailable results all carry `missing_or_invalid_eps_actual`,
  `missing_or_invalid_rev_actual` and `no_supported_material_facts`: the
  incumbent `engine/earnings_release/figures.py` binder extracts no EPS or
  revenue actuals from those EX-99.1 releases. Failing closed is correct,
  but it limits usefulness until the figure-yield follow-up lands. V binds
  revenue but not EPS.
- The public HTTP surface stays 503 until the operator's flags-ON decision.

## Figure binding yield (follow-up g)

The census lives at
[MARKETING_X_CATALYST_BINDER_CENSUS_20261101.md](MARKETING_X_CATALYST_BINDER_CENSUS_20261101.md).
It covers 40 releases: the 20 pilot issuers, 2 latest Item 2.02 EX-99.1 each,
bound in memory under D4 and recorded as hashes and URLs only.

- **Yield.** `parsed` rose from 10 to 31 of 40 and projected public figures
  from 14 to 54 (`eps_actual` 8 → 29, `rev_actual` 6 → 25). Nothing bound at
  the base was lost or changed value.
- **Binder changes.** Failure classes A–E, G, the span rule S, segment
  footing T and share-class EPS K, each with a test in
  `tests/test_earnings_release_binding.py`. The first independent review's
  findings are closed as fail-closed rules with tests (census page,
  "Fail-closed hardening").
- **Live six.** AMZN, MA, MSFT, GOOGL, KO and V, which production showed
  UNAVAILABLE on the `main` binder (reader proof above; V lacked EPS), all project `eps_actual` and
  `rev_actual` on this branch (re-fetched in memory via the writer's path).
- **Silent breaks are visible.** `ReleaseFigureSet.outcome` names why a
  release bound nothing. The cycle index carries it as `figure_outcome`,
  validated against `parse_status`, and packets name it as
  `source_figure_outcome_<code>`. A binder error (`parse_failed`:
  `binder_exception` / `replay_failed` / `document_not_utf8`) now reads
  differently from a release with nothing to project.
- **Flags.** All stay OFF. No producer-file semantics of Filing Forensics
  changed.

Open follow-ups, each needing its own evidence:

1. TSLA and UNH exhibits with no tables (`no_tables` / `no_candidate_rows`):
   the figures need a non-table source.
2. JPM: headline metrics outside dated tables (`no_period_columns`).
3. JNJ: roster rows under undated headers (`no_period_columns`).
4. PG fiscal-year vs Q4 tables refused as `value_ambiguous` (`all_refused`).
