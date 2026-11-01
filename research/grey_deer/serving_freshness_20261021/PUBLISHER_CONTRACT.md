# Natural perception publisher restoration — source contract

Status updated on October21: the original writer has published [Mastermind #1667](https://github.com/mastermindx-market-intelligence/Mastermind/pull/1667), observed head `65c071d9d4820135a54d6d2f7af861bb5e7cebc1`. The owner reports 472 passed / 1 skipped and two source review acceptances at its application predecessor dd44a6b; exact-head hosted CI/security and production activation remain separate. Root did not edit or independently retest that publisher. Earlier candidate hashes and test results do not certify later bytes. See [the continuation](CONTINUATION.md) for source, actual-input refusal and custody. Reader [Mastermind #1660](https://github.com/mastermindx-market-intelligence/Mastermind/pull/1660) is merged at3960aefcf4724a88812d79d97c1b370dc9f951c4; no production installation follows from source merge. The original contract below was inspected at law pin d3537d6dd1cf63178a1493eb70fa2eccc6c01fe0 and reader predecessor fd4a5dc553dabaebc67baeebf2a1cf57b4b6565d.

## Inspected cause and candidate owner

The sole installed Market View publisher is bot/phase2.py, in the archived Flagship path. The active autonomous job does not publish its replacement. Re-running that portfolio path is not an admissible publication repair.

The existing app/scheduler.py::_macro_refresh_job, registered every three hours, is the smallest plausible lifecycle owner for a dedicated perception publication operation. The job currently calls data_layer.macro_refresh.refresh_and_check() and discards its result. A wrapper returning without exception is not evidence of a successful refresh: refresh() deliberately returns None on failure, and refresh_and_check() continues against cached data.

The authoritative VPS can use MASTERMIND_MACRO_MANAGED_EXTERNALLY. In that mode refresh_and_check() deliberately skips a Git/data pull and applies the freshness tripwire to the separately supervised Macro data plane; refreshed_to remains None by design. A proposed publisher must distinguish this valid externally managed mode from an owned refresh failure. It must never reset or sparse-convert the shared live Macro checkout.

Source references at the reader candidate:

- [Existing refresh owner](https://github.com/mastermindx-market-intelligence/Mastermind/blob/fd4a5dc553dabaebc67baeebf2a1cf57b4b6565d/app/scheduler.py#L856).
- [Refresh success/failure contract](https://github.com/mastermindx-market-intelligence/Mastermind/blob/fd4a5dc553dabaebc67baeebf2a1cf57b4b6565d/data_layer/macro_refresh.py#L427).
- [Externally managed mode](https://github.com/mastermindx-market-intelligence/Mastermind/blob/fd4a5dc553dabaebc67baeebf2a1cf57b4b6565d/data_layer/macro_refresh.py#L726).
- [Retired publication block](https://github.com/mastermindx-market-intelligence/Mastermind/blob/fd4a5dc553dabaebc67baeebf2a1cf57b4b6565d/bot/phase2.py#L1030).

## Required publication invariants

1. One canonical writer, one existing lifecycle owner, and the existing Market View/decision-context artifact paths. Do not add another schedule, risk score, event registry or parallel store.
2. Never invoke phase2.run, portfolio build, settlement, sizing, strategy execution or a nightly merely to publish perception.
3. New sequence means new source evidence. A timer, deployment, unchanged fetch or changed age counter is not a new observation. Compare stable source identity/content and preserve every input's own asof. built_at remains a publication clock.
4. Assemble the two contracts from the same captured observation. A reader must reject a mixed generation. A builder return is insufficient proof because the existing builders swallow write errors; publication requires explicit results and bounded readback.
5. Serialize sequence allocation and writes. Retained legacy entry points cannot race an active publisher. Failure must not report success or trigger a portfolio retry.
6. Establish which source snapshot is complete enough to publish. Failed/partial refresh must preserve the last complete publication. Unknown, old, missing and future dates cannot become validated because a publisher ran.
7. Book-specific distribution_tells cannot be silently reinterpreted as market-wide evidence. The old helper reads position_log.open_positions() when no holdings are supplied; the new owner needs an explicit absence/provenance contract or the already authorized correct book source. Do not borrow retired holdings or invent empty holdings as evidence of low risk.
8. Retain forward-evaluation cohort identities and the publication activation boundary. Fresh inputs can change active reasoning even when no trading implementation is edited.

## Active-input and historical boundaries

The source-confirmed active readers are the autonomous regime brief, strategist payload and get_regime MCP path through the shared PM helpers. They also consume decision_context.prompt_summary(). The reader correction in #1660 withdraws unsupported current claims on these paths; it does not create a fresh publication.

Repository search found gate.should_run only in bot/phase2.py. The independently inspected gate reads raw dissent counts, but no active autonomous use was established. Do not convert expired/unavailable dissent to the gate's zero-dissent token or use expiry as a new evidence-change event.

Historical journal readers need a separate point-in-time treatment. journal._regime_context(asof) currently ignores its asof argument and reads latest. _planes_at_entry uses a dated file first and a date-matched latest fallback, but the existing producer overwrites a same-day dated file. A later refresh/correction could therefore be attributed to an earlier decision. Before publisher activation, bind historical entry evidence to the publication actually available at decision time using the existing Chronicle/Reflex/QLedger custody. A date-only replacement file is not a correction receipt, and today's freshness projection must not rewrite recorded history.

## Acceptance before activation

Use synthetic/local inputs, deterministic clocks and isolated artifact paths. Prove:

- One successful new source generation publishes one observation; unchanged sources publish no additional observation.
- Owned refresh failure and externally managed freshness checking are distinguished.
- Failed/partial source capture and write failure retain the last complete publication and emit truthful failure.
- Concurrent triggers cannot duplicate/regress sequence; paired reader mismatch is unavailable.
- Old, missing, malformed and future dates remain ineligible.
- Market View and typed context identify the same generation and source clocks.
- Later same-day refreshes/corrections do not change the evidence attributed to an earlier decision.
- No portfolio, model, sizing, settlement or strategy-run function is called; isolated account/cohort files remain byte-identical.
- Actual current-consumer paths cannot reintroduce stale confirmation during a later outage.

The first publisher consultation returned only metadata because its M2 request was aborted without source. Its proposal remains a conditional architecture recommendation, not inspected implementation approval. The subsequent GitHub-only consultation independently inspected the consumer paths and returned the activation and historical-custody concerns recorded here. Neither consultation grants production execution.

Complete and qualify the source operation, normal checks and review before presenting an exact production activation decision. The existing strategic prohibition on autonomous production deployment remains in force.
