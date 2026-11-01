# Marketing X Catalyst — SEC source cycle writer (A3-W-r2) runbook

Status: writer shipped (this lane); the READER lane that turns the index into
the `AdmittedEdgarSource` consumed by `/api/catalyst/scan` is still to come.
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
| 3 | TRUNCATED — the request budget ran out; later issuers are `not_checked`; the index is still published |
| 4 | PARTIAL — at least one issuer ended not ok |
| 5 | PUBLISH_FAILED — the snapshot publish failed; the prior pointer stays as it was |

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

## Install steps NOT performed here (operator acts, explicit owner decision)

The units ship dormant. After merge, on the macro-api host:

    cp app/deploy/macro-catalyst-source-cycle.service /etc/systemd/system/
    cp app/deploy/macro-catalyst-source-cycle.timer /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable --now macro-catalyst-source-cycle.timer

Installation/enablement is an operator decision; this lane performed none of it.

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
- SEC `acceptanceDateTime` timezone handling is not verified against real
  EDGAR data (the writer parses the ISO value as UTC); a witness run against
  live EDGAR was out of scope for this lane (no network in tests by design).
- 8-K/A attestation is rare in submissions data: `amendsAccessionNumber` is
  often absent, so most 8-K/A filings surface as `unattested_amendment`
  skips rather than corrections.
- The reader lane (index -> `AdmittedEdgarSource` -> `/api/catalyst/scan`) is
  still to come; until it exists nothing public consumes this index.
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
- Enabling order (the operator acts; NOT performed by code): (1) merge the
  `sec_issuer_earnings_release_facts` rights row; (2) install the units and
  run the macro-catalyst-source-cycle timer; (3) observe the first COMPLETE
  cycle in the namespaced store; (4) set the flag; (5) restart macro-api.
- Rollback: unset `CATALYST_PUBLIC_ENABLED` and restart macro-api — the scan
  returns its existing disabled status and admission stays unconfigured.
- Environment variable NAMES only: `CATALYST_PUBLIC_ENABLED`,
  `RESEARCH_LOCAL_STORE`.
