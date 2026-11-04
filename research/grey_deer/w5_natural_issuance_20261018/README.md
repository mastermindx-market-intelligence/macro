# W5 issuance observation — 18 October 2026

**Disposition: a new W5 ledger is present; natural producer/run/publication attribution remains pending.** The inspected source contains **30 declared issuance rows for one SPY source session and one issuance timestamp**. This advances the prior observation that the ledger was absent. It does not establish 30 warnings, independent origins, or episodes, and it is not a passing forecast/calibration result.

This report preserves completed responses after the subsequent Studio lineage request stalled. Preservation used only retained responses and local file operations. No native or network request was repeated.

## Source identity and completed reads

The completed GitHub commit read bound Macro main to **`3e31f5dc8b770d371eb859e2de3df0362fc7fa57`**, with committer time **2026-10-18 09:06:52Z**, tree `e9aca1d228451b2315fc5d0ffb99bac804801a5a`, and parent `e76e7804fff0d567e42fc9bfc8ccea47b0552dee`. That tip time is not the W5 publication time. Individual acquisition timestamps were not captured.

Exactly two natural artifacts were read, both at that immutable pin:

| Existing artifact | Received bytes / rows | Preserved copy SHA256 |
|---|---:|---|
| `data/grey_deer_pullback/forward_log.jsonl` | 34,474 / 30 | `a5a6bd895926aad829c1c09cc6a01f95949744f58e85388fd1c73d38cf679f9e` |
| `data/grey_deer_pullback/forward_log_refusals.jsonl` | 2,059 / 7 | `ebbded69d2383ff77a40dbd7f8f653d70d8bc234fefa5222edc2687d2e296f70` |

Both parse completely and end with a newline. The exact received JSONL is preserved under `evidence/`; these are frozen evidence copies, not a replacement publication ledger. [OBSERVATION_METADATA.json](OBSERVATION_METADATA.json) contains the bounded counts, row identities, clocks and refusal history. [FILE_IDENTITIES.json](FILE_IDENTITIES.json) binds all captured source/evidence bytes. Computed Git blob SHA1s are explicitly distinguished from the separate Git-object metadata query that never returned.

## What the rows actually establish

All 30 rows share:

- `ticker: SPY`, `asof: 2026-10-16`, and `issued_at: 2026-10-18T06:24:18+00:00`.
- `evidence_class: GENUINELY_ISSUED`, `population: P-all`, nightly writer/collection lanes, and `writer_identity: daily.yml:engine`.
- `backfill: false`, `rerun: false`, and `intraday: false`.
- Declared code SHA `5e3e1e9d2d97439d0546072b89e9f94d3e84f2fa`, prereg blob `49a68b5e9c6543d662044b0aa391c4b6e6e6052e`, and recipe fingerprint `9c8b7fe2f572b06b9253affd9a3ca7fb02b8f4d20e7723dd76b46538d235bb8c`.
- Null `Y`, `realized_A`, `graded_at`, and `grader_sha`.

There are 30 distinct `(asof, ticker, horizon, config_id)` keys and no duplicates in the captured file.

| Horizon, sessions | Rows | Training-end date declared |
|---|---:|---|
| 5 | 10 | 2026-10-05 |
| 10 | 10 | 2026-09-28 |
| 21 | 10 | 2026-09-11 |

Each horizon contains `B0`, `B1-20`, `B1-63`, `B2-21`, `B2-63`, `M3-ALL@C=1.0`, `M3-ALL@C=0.1`, `Q0`, `Q1`, and `Q3-ALL`. These are configuration/horizon forecast records in the prospective research lane. Counting them does not establish that a public risk alert fired.

**Declared source-session count: 1. Declared issuance-batch count: 1. Independently qualified natural-origin count: null pending lineage. Independent episode N: null.** Probability and quantile values are preserved in the original bytes but were not scored, calibrated, compared with outcomes, or promoted into action guidance.

## Clocks and refusal history

The source date is Friday, October 16; the declared issuance is Sunday, October 18. Preserve that delay. The rows have no independent `source_available_at`, `build_at`, or publication timestamp. Therefore **actual source-availability-to-issuance latency and first-publication latency remain unknown**. Neither source-date midnight, a nominal exchange close, nor the current main tip time has been substituted for a missing clock.

The captured writer rejects an asof older than `expected_last_session(issued_dt)` and requires issuance from 17:00 ET on the source session until the next session's open. Its UTC clock is read after scoring, immediately before the issuance/refusal append sequence. Sunday issuance for a Friday source session is not automatically a backfill violation under that design. Actual producing checkout, runtime calendar, clock execution and natural-run identity still require attribution; the row's declaration alone is insufficient.

The seven refusal rows remain separate from issuance:

| Source asof | Refused at UTC | Reason |
|---|---|---|
| 2026-10-13 | 2026-10-14 18:35:18 | CLOCK |
| 2026-10-13 | 2026-10-15 07:54:07 | BACKFILL_ASOF |
| 2026-10-14 | 2026-10-16 06:33:55 | BACKFILL_ASOF |
| 2026-10-15 | 2026-10-16 17:15:20 | CLOCK |
| 2026-10-15 | 2026-10-17 06:19:30 | BACKFILL_ASOF |
| 2026-10-15 | 2026-10-17 18:08:39 | BACKFILL_ASOF |
| 2026-10-16 | 2026-10-18 06:24:18 | OBSERVER_NOT_ON_MAIN, P-active |

The final refusal is the writer's expected unissued P-active observer record. It does not convert earlier refusals into issuance or prove all other runtime annotations were absent.

## Existing path and source proof

Recovered lineage is the existing W5 path:

`scripts/ci/daily_engine_regional_desk_builders.sh` → `scripts.grey_deer_pullback_nightly` → `engine.grey_deer_pullback_forward.issue` → `data/grey_deer_pullback/forward_log.jsonl` / refusals.

The nightly wrapper loads the SPY close store, invokes the existing writer, then invokes the existing grader; this review invoked none of those operations. The shell enrollment and wrapper are source evidence, not proof that a particular workflow reached them. The wrapper reports problems through annotations while normally returning zero, so a green workflow alone would also be insufficient.

Exact captured source bytes under `source/` compute to the same Git blob identities returned by the earlier completed #9128 files metadata read:

| Source | Computed blob SHA1 |
|---|---|
| Writer | `bbb7ce83113bdbe6c65147beec4ca4fd896cfdbd` |
| Nightly wrapper | `0460443c1a756627535a2d0026cf0d5db0d3d499` |
| Regional builder enrollment | `c46ded27a832c0d3052342bc12e126978cef1858` |

This supports source continuity with the earlier W5 proposal. It does not verify the rows' claimed producing commit or its ancestry to merge `af468522ab6e…`; the targeted metadata request for that attribution did not return. The programme's existing production-proof requirement still asks for a natural nightly descending from that source, SPY issuance, and absence of relevant error annotations.

## Interrupted request and remaining gate

[INTERRUPTED_REQUEST.json](INTERRUPTED_REQUEST.json) preserves the exact request family and endpoints. The sole pending native request was `mcp__codex_apps__studio_direct_start_process`, `/bin/bash`, `timeout_ms: 15000`, beginning `python3 -I -S <<'W5_READ_ONLY_METADATA'`. It requested five read-only `gh api` metadata operations: exact blob identities/sizes; producer commit; two-entry forward-log publication history; daily workflow runs at the claimed producer SHA; and #9128 merge identity.

No stdout, stderr, PID, call ID or completion status was received. The client returned **“aborted by user after 2571.4s.”** Backend completion is unresolved; interruption does not prove non-execution or termination. Parent-observed PID 80180 / RemoteCall1 is recorded only as a possible process, not attributed to this request. Root owns reconciliation. **Do not replay it.**

The next evidence needed is that existing request's result or an explicit unresolved lineage gate: actual producing run/event/checkout, applicable annotations, first commit/publication record and available clocks. No new provider/store acquisition is needed to preserve this observation. Historical `CLOCK` and `BACKFILL_ASOF` refusals, the absent-log finding at prior `3ab3382…`, legacy Radar's unrelated session counts, and accepted GD3/#9517 proof remain intact.

No manual nightly, backfill, model/grade/trial action, data join, browser action, native source/index/HEAD write, publication write, or policy change was performed. Source-writer holds and numerical policy ownership are unchanged. W5 natural-production acceptance and forecast competence remain separate unresolved questions.
