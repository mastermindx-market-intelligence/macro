---
workstream: WS:FUTURES-MARKET-TAPE-PLANE
session: sol/futures-tape-plane-20261005
model: sol
ended_because: ci_handoff
mission: >
  Initiate and carry the ES-first futures tape plane end to end: ownership, storage,
  source qualification, ingest/normalize/derive/audit implementation, and a perpetual
  accrual path without duplicating Data OS or granting signal authority.
state_before: >
  No futures_tape workstream or owned implementation existed. Mastermind had a Yahoo
  futures display relay, Data OS futures identity primitives, ThetaData options tape,
  Massive stock data and several research consumers, but no governed deep futures tape
  store. Current internal Massive records did not establish Futures entitlement.
changed:
  - path: lib/dataos/futures_tape.py
    what: >
      Added provider-neutral storage roles, partition states, path safety, external-root
      resolution, capacity fencing, checksums, atomic manifests and read-only audit.
  - path: scripts/futures_tape_ingest.py
    what: >
      Added storage/probe/backfill/normalize/derive/audit CLI for the first LSE ES.F lane.
      LSE source effects require LSE_API_KEY and the official SDK; no credential is created.
  - path: scripts/probe_massive_futures.py
    what: >
      Added a read-only ES Futures entitlement probe reusing the existing Massive probe's
      RestProber/key/scrubbing owner; it writes no competing capability manifest.
  - path: config/dataset_registry.yml
    what: >
      Registered raw LSE tape, normalized LSE ticks and derived bars as PROPOSED Data OS
      datasets. They stay PROPOSED until real source-bearing production receipts exist.
  - path: tests/test_futures_tape_ingest.py
    what: >
      Added no-network coverage for storage paths, immutability receipts, capacity fence,
      LSE normalization, row bounds and atomic export behavior.
  - path: tests/test_probe_massive_futures.py
    what: >
      Added no-network entitlement-probe logic coverage.
  - path: research/futures_tape/FUTURES_MARKET_TAPE_PLANE_MASTERPLAN_2026-10-05.md
    what: >
      Frozen source roles, storage policy, consumers, wave sequence and acceptance gates.
  - path: agentos/workstreams/WS-FUTURES-MARKET-TAPE-PLANE.md
    what: >
      Created the durable workstream under the registered market-timing-intelligence program
      while preserving Data OS as physical data owner.
  - path: agentos/decisions/DEC-FUTURES-TAPE-OWNERSHIP-AND-SOURCE-ROLES.md
    what: >
      Ruled Data OS as physical owner; LSE as secondary vendor-continuous history; Massive
      Futures as preferred exact-contract source when entitlement is measured; ThetaData
      remains options owner.
verified:
  - claim: Protected execution procedure was loaded atomically.
    command: >
      Read Mastermind protected master at
      5b244a2bbe4c2a94ec25a887eb4a0d8fafe1ea2f; load INDEX, COLD_START,
      ACTIVE_EXECUTION and SESSION_RELIABILITY from that exact commit.
    result: >
      schema mastermind.sol_skillpack.v1, skillpack_version 1.0.1,
      minimum_bootstrap_major 1; bootstrap major 1 compatible.
  - claim: No existing futures_tape workstream or open same-name implementation carrier was found.
    command: >
      Search current Macro GitHub for FUTURES-TAPE, futures_tape and WS:FUTURES plus open
      pull requests matching futures, dataos and dataset_registry before branch creation.
    result: >
      No prior FUTURES-TAPE/futures_tape workstream or same-name open carrier was found.
  - claim: The attended physical host has capacity for an ES-first pilot but not an
      unbounded multi-terabyte quote crawl.
    command: >
      Read mounted-volume capacity on the attended Mac host before any data write.
    result: >
      /Volumes/Mastermind had about 673 GiB free, WD 5TB about 323 GiB and Worktrees
      about 105 GiB. The producer therefore defaults to preserving 100 GiB free.
  - claim: Core manifest/hash behavior is executable.
    command: >
      Compile lib/dataos/futures_tape.py in an isolated container smoke and create one
      receipted sample partition; audit it clean, mutate the bytes, then audit again.
    result: >
      Compilation and clean audit passed; the post-write mutation was detected by
      byte-count/hash verification.
unverified:
  - claim: LSE ES.F catalog row, history span and roll/adjustment semantics.
    what_would_verify: >
      On an ops host with LSE_API_KEY and lse-data[frames], run
      python -m scripts.futures_tape_ingest probe-lse --symbol ES.F and preserve the receipt.
  - claim: Existing Massive enterprise credential is Futures-entitled.
    what_would_verify: >
      Run python -m scripts.probe_massive_futures with the existing secret-bearing environment.
  - claim: End-to-end source backfill works against live LSE.
    what_would_verify: >
      F0 source probe passes, then one bounded backfill-lse window writes a Parquet export,
      checksum manifest, normalized daily partitions and a clean audit.
  - claim: Full branch CI is green.
    what_would_verify: >
      GitHub PR #8451 exact-head fences and CI complete successfully after the Agent OS
      record-contract repair.
unresolved:
  - LSE credential is not available to this repository-only carrier.
  - Massive Futures entitlement is unknown and must not be inferred from Stocks rights.
  - ES.F vendor roll/adjustment semantics remain unproven.
  - No raw tape has been acquired; registry entries intentionally remain PROPOSED.
next_actions:
  - Re-run/consume PR #8451 exact-head CI after this Agent OS repair.
  - If green, mark the PR ready and merge under the normal release gates.
  - Then on the existing secret-bearing ops host run storage, LSE catalog and Massive Futures probes.
  - On accepted receipts, start one bounded ES.F backfill window and audit it before full-history work.
do_not_redo:
  - Do not create another Futures OS/Data OS/scheduler/entitlement ledger.
  - Do not call ES.F an exchange contract.
  - Do not download full CME quote history before a named microstructure need.
  - Do not buy storage or a Futures plan before measured capacity/entitlement results.
  - Do not grant raw tape any trading authority.
danger_areas:
  - LSE ES.F roll/adjustment semantics are still unknown.
  - Current Massive Stocks rights do not prove a Futures entitlement.
  - Raw source bytes are rights-sensitive and must remain private/outside Git.
  - Session-aware 4H/8H/12H bars must not be inferred from naive wall-clock resampling.
  - A trade tape does not prove continuous order-book state or OFI.
---
