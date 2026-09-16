# Prophet US Completed-Session and Immutable-Source Design

**Status:** Chairman-approved outcome; architecture corrected during adversarial implementation review on 2026-09-15.

**Outcome:** Restore lawful US Prophet origination on weekday pre-close runs without weakening mixed-vintage safety, and make every Prophet index recoverable to the exact ranked-board bytes it used without taking ownership of the independently current customer board.

## User and machine jobs

The user must receive fresh Prophet plans when valid candidates exist, rather than a zero-pick surface caused by provisional daily bars or a publication-date clock error. The live US candidate board must also remain current across its existing daily, render, and closing-bell publishers.

The machine must score one coherent completed-session US equity cross-section, preserve raw vendor reach for diagnostics, validate entry-price clocks against the actual observation instant, and bind each Prophet publication to an immutable exact source snapshot.

## Confirmed failure chain

On 2026-09-15 the US board combined 3,038 members ending on the completed 2026-09-14 session with 198 members already carrying provisional 2026-09-15 daily bars. Ranking occurred before the existing mixed-vintage guard correctly refused all eligible candidates.

A second defect treated the date-only publication stamp `2026-09-15` as though that session were already complete. During the 2026-09-15 trading day, that rejected the valid 2026-09-14 price basis.

A third defect let `site/prophet/index.json` reach `main` while the exact source board used for that build remained runner-local. Production consequently carried a Prophet index whose `source_board_asof` was 2026-09-14 beside a canonical live board still stamped 2026-09-11.

## Architecture

### One completed-session scoring plane

`build_site` captures one UTC observation timestamp and derives one `lib.nyse_calendar.expected_last_session(observed_at_utc)`. The same cutoff is passed into residual alpha and the stock-library producer.

Before any US-equity ranking, extension, dispersion, lottery, technical, entry, or per-name scoring read, close/high/OHLC inputs are sliced to dates at or before that completed session. Crypto remains on its continuous calendar. Raw maximum dates and provisional-name counts remain in the receipt, so normalization changes scoring authority without deleting evidence.

The existing mixed-vintage gate remains unchanged. After normalization it judges differences among completed session dates, so a genuinely torn Monday/Friday panel still fails closed.

### Observation-aware origination clocks

Live and Arena origination read `staleness.observed_at_utc` when present. Timestamp-aware validation uses `expected_last_session(observed_at_utc)`. Date-only historical fixtures and replay inputs retain the existing `last_session_on_or_before(date)` compatibility path.

Thus:

- Tuesday before the settlement cutoff accepts Monday as the price basis.
- Tuesday after the settlement cutoff requires Tuesday.
- Weekend publication accepts Friday.
- A genuinely stale completed-session board remains refused.

### Immutable source provenance, not mutable-board ownership

`site/factordata/us_standouts.json` is a first-class product and machine-context artifact. Daily, render, closing-bell, engine-render, weekly, and early-close lanes lawfully refresh it. Prophet must not make that live file exclusive to its narrow checkpoint or restore an older accepted board over a newer customer board.

Instead, `scripts.build_prophet` freezes the exact input bytes under the existing Prophet provenance root:

```text
data/prophet/origination_sources/<sha256>.json.gz
```

The snapshot is content-addressed, immutable, and gzip-compressed with `mtime=0`. Its filename is keyed by the SHA-256 of the uncompressed board bytes, so decompression recovers the exact source while materially reducing raw working-tree growth; raw-byte identity also tolerates harmless gzip-header variation across runtimes. Reusing identical raw bytes is idempotent; a different payload at the same hash path is a fail-closed collision. `site/prophet/index.json` records:

```text
source_board_sha256
source_board_snapshot_path
source_board_snapshot_encoding = gzip
```

The nightly's already-existing temporary source freeze verifies that:

1. the live board does not change across the build;
2. the temporary byte copy has the expected hash;
3. decompressing the durable immutable snapshot recovers exactly those bytes.

The parsed object from that one freeze is also the sole board input for live origination,
Arena, the legacy shadow ledger, and the index's gate disclosure. Each consumer receives
an isolated deep copy where mutation is possible. No production consumer re-opens the
mutable live board after the freeze, so an ABA rewrite cannot produce plans from bytes
that differ from the recorded snapshot even when the path ends with its original hash.

This verification occurs before the zero-new-plan return, so an honestly empty origination night still preserves its exact source.

### Checkpoint and restore boundaries

The immutable snapshot, not the mutable live board, participates in the Prophet publication boundary:

- both pre/post build-owned snapshots include `data/prophet/origination_sources/*.json.gz`;
- the checkpoint's closed path allowlist accepts only those content-addressed JSON files;
- `data/prophet` remains protected against races and supersession;
- accepted-source restore carries current accepted Prophet plans, ledgers, Arena state, and source snapshots;
- broad-engine refusal cleanup removes only uncheckpointed source snapshots while leaving correction ledgers untouched.

The live `us_standouts.json` board remains outside Prophet checkpoint, R2 supersession, accepted-source restore, and broad-commit refusal ownership. Its existing product publishers remain intact.

## Failure and null behavior

A missing or malformed observation timestamp does not authorize freshness. Clock resolution first parses an exact date-only value; every other valid ISO datetime form, including lowercase `t`, uses timestamp semantics. Date-only fallback applies only to a true date-only input.

An empty candidate night is valid. A non-empty eligible population with zero originations remains an acceptance alarm, not permission to weaken chronology or mixed-vintage gates.

A missing, unreadable, malformed, or non-object source board fails closed before origination; no degraded index may claim provenance without exact source bytes. The nightly preflight withholds the build non-fatally, and the prior accepted Prophet projection remains authoritative. Source-byte drift, a missing durable snapshot, symlink, hash-path collision, checkpoint race, or same-path conflict likewise withholds the entire checkpoint. The independently current customer board is never rolled back as a side effect.

Snapshot publication uses a randomized temporary file in the provenance directory, `fsync`, and a hard link to the content-addressed final path. Orphaned PID-shaped temp files from prior killed processes therefore cannot block a later run.

The public R2 payload remains the minimal health projection. The full plan book and immutable source snapshot remain private; the unconditional public-index tombstone remains separate.

## Non-goals

- Do not disable or soften mixed-vintage refusal.
- Do not create a new clock, event, publication, retry, or health authority.
- Do not change Prophet admission, ranking, scoring weights, plan identity, geometry, or trade authority.
- Do not use provisional same-day daily bars as completed-session evidence.
- Do not make the live US board Prophet-exclusive or stale another product to prove provenance.
- Do not combine China effect reconciliation into this US modifying carrier.
- Do not replace PR #7161's market-session cohort repair; integrate that separate control-plane slice after this producer repair is accepted.

## Acceptance

The implementation is accepted on one immutable candidate head only when:

1. A pre-close Tuesday observation scores every US equity through Monday while retaining raw Tuesday reach.
2. Crypto retains its continuous-calendar row.
3. A genuine completed-session tear still reports `mixed_vintage=true` and is refused.
4. Pre-close Monday price basis validates; the same board after Tuesday settlement fails stale.
5. Live origination and Arena use the same observation clock.
6. Residual alpha and stock-library scoring use the same completed-session cutoff.
7. The index hash/path resolves to byte-identical immutable source data.
8. A zero-origin night still adds the immutable source snapshot to the checkpoint manifest.
9. The live customer board is absent from Prophet checkpoint and accepted-source restore ownership.
10. Existing Prophet chronology, staleness, extension, R2-boundary, workflow, and checkpoint contracts remain green, apart from independently reproduced baseline failures outside this delta.
11. A real nightly-path run originates from a coherent current board, or truthfully reports no valid candidates for reasons other than the repaired defects.

Merging establishes `BUILT_NOT_PROVEN`. Only a real production nightly proves `PROVEN_LIVE`.
