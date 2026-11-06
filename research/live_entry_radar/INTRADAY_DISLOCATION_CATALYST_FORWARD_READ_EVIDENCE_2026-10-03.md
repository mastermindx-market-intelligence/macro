# Intraday Dislocation Catalyst Forward-Read Evidence — 2026-10-03 UTC

**Program:** Live Entry Radar / Terminal Tactical Intelligence — Dislocation + Reclaim  
**Authority:** research-only; no ranking, gating, sizing, execution, alert, or production activation  
**Protected procedure pin:** Mastermind `bdf2a972e68a70270c24d4b5d61a4d60edc4f288`  
**Implementation branch before this evidence commit:** `claude/intraday-dislocation-catalyst-r0-20261003@5b32431a7d91ec5265d444b6bc65b86a09afe44a`

## 1. Question

Can the existing Company Intelligence owner read path provide a real, verified **current**
issuer-event workspace that the R0 catalyst context can safely treat as event-presence
evidence, while preserving the opposite case as unknown coverage rather than "no news"?

This evidence pass is deliberately read-only. It creates no market-data reader, source index,
event store, Radar episode, spool, scheduler, daemon, source-coverage receipt, or trade authority.

## 2. Exact owner path used

The bounded probe used the incumbent owner reader:

`engine.neuralweb.company_intelligence_reader.read_current_event_workspace`

That reader already owns:

1. current published marker resolution;
2. immutable generation selection;
3. ticker alias selection;
4. immutable workspace fetch;
5. hash/byte receipt verification;
6. `event_workspace.v1` validation;
7. fail-closed separation of "ticker not covered" from other read failures.

R0 did not issue its own HTTP request or bypass this owner.

The read was executed from the exact R0 verification worktree after resetting to the published
branch head. Only compact receipt fields were printed; no licensed/raw workspace body was copied
into this evidence file.

## 3. Positive real-source observation — AAPL

Read interval:

- started: `2026-10-03T03:56:53.482202Z`
- consumer observed: `2026-10-03T03:56:55.237010Z`

Owner result:

| Field | Observed value |
|---|---|
| ticker | `AAPL` |
| available | `true` |
| authority | `context_only` |
| is_context_only | `true` |
| event alias | `AAPL/2026Q3` |
| event id | `evt_cik0000320193_2026q3_results` |
| generation id | `fd49872ccee947fe4bc95b3e` |
| generated_at | `2026-07-31T00:30:28Z` |
| lifecycle state | `corrected` |
| lifecycle source_available_at | `2026-07-31T00:30:28Z` |
| lifecycle observed_at | `2026-10-02T00:52:47Z` |
| verified workspace SHA-256 | `c4b5754e6ab3f746356ba38940f04c4d778648f3b757696f3c774179967e4e63` |

### Interpretation

This is direct evidence that the incumbent Company Intelligence publication/read chain can
produce the exact ingredients required by the R0 pure adapter:

- canonical owner event identity;
- immutable owner generation identity;
- source availability clock;
- owner observation clock;
- generation clock;
- a later consumer observation clock;
- a verified immutable workspace receipt;
- context-only authority.

For a Radar decision at or after the prospective consumer observation clock, an admitted
post-release earnings workspace can therefore become **blocking event-presence evidence**.

This does **not** establish historical point-in-time availability at the SEC/source time. The
consumer did not observe this exact read until 2026-10-03 UTC, so this probe cannot be backdated
into an earlier tactical decision.

## 4. Negative-coverage observation — NVDA

Read interval:

- started: `2026-10-03T03:56:55.237047Z`
- consumer observed: `2026-10-03T03:56:55.239161Z`

Owner result:

| Field | Observed value |
|---|---|
| ticker | `NVDA` |
| available | `false` |
| authority | `context_only` |
| is_context_only | `true` |
| note | `Event workspace does not cover this ticker` |
| event id | unavailable |
| generation id | unavailable |
| workspace receipt | unavailable |

### Interpretation

This is **not** evidence that NVDA had no catalyst. It is evidence that this owner read surface
does not cover NVDA at this current marker.

R0's correct result is therefore:

`coverage_unknown`

The following are forbidden interpretations:

- "no news";
- "no material catalyst";
- "safe technical flush";
- "mean reversion allowed";
- any positive reversal inference.

This real observation validates the R0 fail-closed asymmetry: **presence may be proven by a
verified owner event; absence may not be inferred from owner non-coverage.**

## 5. Radar episode-source reality

The current checked-out canonical Radar state was inspected read-only at
`data/entry_radar/ledger_state.json`:

| Field | Current value |
|---|---|
| schema | `entry_radar.w5_ledger_state/v1` |
| session | `2026-10-02` |
| state | `WAITING_FOR_LIVE_SOURCE` |
| spool_dir | `null` |
| observed_spool_events | `0` |
| live_forward_rows | `0` |
| forward_rows_total | `0` |
| qledger registered/rejected/failed | `0 / 0 / 0` |
| updated_at | `2026-10-02T11:04:37.851267+00:00` |

The local `data/entry_radar/` directory contains `ledger_state.json` but no live
`episodes.json` to bind.

This is a real upstream gate, not permission to synthesize an episode. Existing Radar law
explicitly preregisters this state while no lawful private live spool is visible.

## 6. Incumbent owner blocker

The active owner carrier for the private Radar evidence transport is:

- Macro PR **#6625**
- `[HOLD-FOR-SOL] radar(w4.2): private evidence-spool boundary — dedicated store + shared-bucket refusal (LER-C1)`

That carrier is explicitly held pending Sol security acceptance and says **do not merge**.
It owns the dedicated private spool boundary and the remediation for the previously public
Radar evidence path.

The Dislocation + Reclaim program therefore does **not**:

- modify PR #6625;
- create another spool;
- create another Radar episode producer;
- enable `ENTRY_RADAR_LIVE_ENABLE`;
- fabricate forward rows;
- reinterpret Prophet/B1 episodes as Radar live episodes.

## 7. What is now proven

1. The fail-closed R0 catalyst context and source-specific adapters are executable.
2. The incumbent Company Intelligence current reader can supply a real verified earnings
   workspace suitable for prospective **presence** evidence.
3. Real owner non-coverage is preserved as `coverage_unknown`, not negative catalyst truth.
4. Current Radar live-forward input is genuinely disconnected in the canonical state.
5. The missing Radar source already has a separate held owner carrier; no duplicate control
   plane is needed.

## 8. What remains unproven / blocked

- a non-empty real Radar `LiveEpisode` available to bind to catalyst context;
- accepted private Radar spool transport and W5 production rebind;
- accepted live exhaustion/reclaim owner construction;
- a canonical live halt/LULD owner source;
- universe-wide catalyst coverage capable of supporting a strong negative event assertion;
- historical PIT catalyst absence;
- any improvement in timing, MAE, return, hit rate, or profitability;
- Terminal production UI/API activation.

## 9. Capability state

`OWNER_EVENT_READ_PROVEN__RADAR_LIVE_EPISODE_SOURCE_BLOCKED`

The next end-to-end forward-shadow proof is gated on the incumbent Radar owner producing a real
lawful live episode through its accepted private transport. Until then, independent work may
continue on contracts, source-specific presence adapters, and Terminal consumer semantics, but
not on fabricated live episodes or historical "no news" inference.


## 10. Repair-head real cache proof and source-clock refusal (07:16 UTC)

Code: `255aba127c1dfed34f334bcc516623ba1d64ed50`. The bounded existing-owner
AAPL read was repeated because the warm-cache receipt behavior changed, not to
repeat the earlier inventory. The cold read made three owner fetches; the warm
read made zero. Both carried the same verified payload SHA-256:
`5085d887a416f214deb829062d398add0e0312f4fb904e45cc1e6ae63e6bc62d`.
Generation: `0e7c62ee74f5b256a21fd9d4`.

The source payload passed owner hash validation but the catalyst adapter REFUSED
both reads: `Company Intelligence generated_at precedes lifecycle observed_at`.
An exact-payload diagnostic confirmed `generated_at=2026-07-31T00:30:28Z` and
`lifecycle.observed_at=2026-10-03T05:23:48Z`. Source availability is also the July
clock. The consumer observed the cold read at `2026-10-03T07:16:01.544293+00:00`.

This narrows the earlier section 3/7 interpretation: a successful owner read is
not successful catalyst admission. The cache repair is real-source proven;
this generation is NOT admitted to the catalyst layer. The published source
clock order is a concrete additional dependency, separate from source coverage,
relevance and the missing accepted Radar episode.

At this code revision, `scripts/refresh_event_workspaces.py:1838,1896` passes
`generated_at=source_clock` to the existing workspace publisher. That is a
source-owner reconciliation target, not proof of the exact running publisher
revision. Do not rewrite old generations or weaken the adapter's refusal. The
owner must reconcile truthful publication/observation clocks before a later
admitted generation can supply this consumer. No publisher, source clock,
live detector, configuration, or production artifact was modified by this probe.

Machine receipt: `CATALYST_R0_HARDENING_EVIDENCE_2026-10-03.json`, including exact
cold/warm read windows, payload identity, clock diagnosis and source-code pin.
