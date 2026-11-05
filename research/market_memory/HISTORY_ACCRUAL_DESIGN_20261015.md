# Immutable historical extension — design and implementation plan

Goal: add genuinely new observed market dates to an existing source-bound history without replacing a historical state, discarding a capture, confusing new outcomes with old knowledge, or installing another collector/scheduler.

Architecture: one new `market_memory_history_extend.py` composition module calls the existing Data OS reader via `assemble_history`, validates the original archive with existing hash/semantic checks, and publishes through the existing no-clobber `write_archive`. A CLI `extend` command accepts the old archive/digest, explicit next input request and a new destination. The read-only Data & Lab API remains unchanged and consumes the resulting v2 archive as before.

Frozen append contract: same basis, benchmark, selection, start, warmup, ordered exact vendor universe and hindsight/admission flags; capture cutoff/end may only advance; every old source reference must remain. The candidate must preserve every old state row exactly, in canonical date/symbol order, and must not insert an old missing observation at or before the parent's last actual date. Corrections or universe changes are new studies, not append operations. Current feature version must match the parent. A streaming hash recomputed from retained Parquet state rows must match the parent's states digest. Outcomes are not read from the parent; they may mature only in a new generation. All original bytes remain untouched.

No progress: if no new actual state rows exist, return `NO_NEW_OBSERVATIONS` and create no destination. A later requested end or later capture time alone is not new data. Retain explicit first/last actual date and row counts. Successful v2 manifests include a semantic-hash-bound parent extension record. Default day/dossier readers never open future-outcome tables.

Implementation order: (1) write and observe failure of synthetic append/corruption/authority/zero-progress tests; (2) implement the bounded composition and CLI tests; (3) verify actual retained prefix hashing, new source-bound generation and installed read-only consumer; (4) publish one source change with existing CI owner scopes and concise Agent OS state. A real current EOD capture, if admitted, uses existing collector only, one bounded original operation, exact request scope, and no retry of uncertain/denied attempts.

Persistent scheduling remains HELD under the original Tiingo scheduling refusal. This feature does not clear that hold. No auth, relay, public redistribution, credentials, forward ledger, prediction or source authority is changed. A separate install/selection proof is required for source changes; currently installed history reads at c223bd38 are already proven.

Direct principal work: consequential append-vs-revision semantics and reader compatibility are tightly coupled; no generic worker review or fabricated hierarchy is needed. Delegate a frozen independent test/review only when it lowers total completion cost.

## Reproducible operation

The CLI is source implementation until its PR merges; the existing installed read-only Data & Lab already consumes the verified v2 output. It accepts no network or privileged producer action.

```sh
python3 scripts/market_memory_history.py extend \
  --archive /Volumes/Mastermind/data/web-lab-runs/market-time-machine-20261015-v2 \
  --manifest-sha256 31f61ea6dc152265d3e9ed2d955068e8d914b1f82b990804ad5efb0b68b5ecd0 \
  --input <exact-next-request.json> --output <new-nonexistent-directory>
```

All updates to `symbols[].refs` are exact existing capture date/digest pairs; source scope and old captures remain bound. On any failed publication, inspect the original destination rather than rerunning the command on a new path to conceal the failed attempt. A completed new generation is selected by its receipt digest, not by directory ordering or a new latest-state registry.

The first real extension added75state rows across Oct12–14 after25finite EOD requests totaling22,723bytes. The old152,980states and all68originalfiles were verified unchanged, and the already installed reader returned eachnewdate with25rows. The extension is a bounded full-snapshot recomposition: it does not yet provide zero-copy history retention or unlimited daily reference compaction. The existing per-symbol32reference bound remains enforced. Do not describe this pilot as an unattended perpetual archive.

Primary provider references checked2026-10-15: https://www.tiingo.com/documentation/end-of-day and https://www.tiingo.com/kb/article/the-fastest-method-to-ingest-tiingo-end-of-day-stock-api-data/. They distinguish historical/daily deltas and corporate-action adjustment changes. This append path preserves the incumbent conflict refusal instead of silently replacing adjusted history when an overlap disagrees. New economic-vintage corrections require an explicitly separate study, not a last-write-wins patch.
