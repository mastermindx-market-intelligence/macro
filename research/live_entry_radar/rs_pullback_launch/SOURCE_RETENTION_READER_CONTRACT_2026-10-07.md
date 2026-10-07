# RS Pullback Launch: retained-minute reader contract

Workstream: `WS:LIVE-ENTRY-RADAR`  
Operations: original `rs-pullback-launch-source-retention-20261007-sol-002`; correction `rs-pullback-launch-basis-binding-20261007-sol-005`
Date: 2026-10-07  
Scope: source retention, versioned response declarations and basis-unavailable input conformance

## Result and evidence boundary

Terminal can retain bounded one-minute source observations in its existing per-symbol store. The Macro bridge can turn an actual owner read of those bytes into decision-scoped inputs for the existing RS input selector. The producer and consumer remain within their current ownership boundaries.

[Phase 1](PHASE1_ADMISSION_2026-10-07.json) remains **NOT_ADMITTED** with 29 refusals; H1, H2 and H3 remain **NOT_TESTED**. The admission artifact SHA-256 remains `a4e00a5c191917dc8c64fb74ca3348827ab9bd47d9ad8a03a1130a50fde36e9f`. Retention code, synthetic conformance, hosted CI and deployment are separate evidence classes.

The unchanged [original joint conformance receipt](SOURCE_RETENTION_CONFORMANCE_2026-10-07.json) is historical evidence for its exact source revisions. The distinct [declaration and basis-refusal receipt](SOURCE_BASIS_DECLARATION_CONFORMANCE_2026-10-07.json) binds the corrected implementation by exact file SHA-256 values. It uses injected transport and synthetic clocks. The producer implementation and wire contract are delivered through [Terminal PR #840](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/840).

## Owner and storage boundaries

| Responsibility | Existing owner and implementation |
|---|---|
| Source request, response receipt and per-symbol atomic store | Terminal `ingest/backfill_intraday.py`, with `ingest/intraday_capture.py` |
| Actual downstream observation of retained source bytes | Macro `engine/entry_radar/replay/terminal_minute_observations.py` |
| Custody of enrolled reader receipts and input population | Existing research input-bundle owner |
| Canonical revision selection, complete 15m/30m aggregation and unavailable frames | Existing `engine/entry_radar/replay/rs_pullback_launch_data.py` |
| Security identity, adjustment basis, session calendar, daily context and incumbent inputs | Their existing canonical owners; labels supplied to this bridge are not independent proof |

The producer adds a versioned `minute_capture` envelope inside the existing symbol JSON. The existing chart `bars` projection remains available to its current consumers. No second event store, episode ledger, experiment ledger, scheduler, publication owner or decision authority is introduced.

An explicit producer invocation enables retention for 1–16 validated symbols and true 1m requests. A valid enabled file remains enabled on an ordinary owner refresh. This delivery does not enroll a runtime cohort or alter an existing schedule.

## Three clocks

| Clock | Meaning | Permitted use |
|---|---|---|
| `event_start_utc_ms` / `event_end_utc_ms` | Source minute interval in true UTC; one-minute duration | Event placement and complete-bar aggregation |
| Source response receipt in UTC nanoseconds | When Terminal received the bounded response bytes | Source provenance and clock validation |
| Actual owner read completion in UTC nanoseconds | When the named Macro reader had read and hashed the exact bytes | Earliest eligible downstream `known_at` for the covered capture prefix |

The reader opens and reads the file once, bounds its size, hashes those exact bytes and samples its own completion clock. There is no public argument for supplying or backdating that clock. Replacing the pathname after its descriptor opens cannot cause the receipt to bind a different file version.

Serialized read receipts contain the reader identity, read identity, actual read clocks, byte count, whole-file hash and sealed capture-prefix hash/sequence. The reader's current receipt is not silently enrolled into the input history. The owning caller must retain and explicitly supply the receipts it is entitled to use.

A receipt binds a prefix. A later chart projection or appended capture changes the current whole-file hash without changing an earlier immutable capture's identity. Hashes detect inconsistent bindings; they are not signatures, remote attestation or a substitute for custody.

Nanosecond read times are rounded upward to the supported microsecond representation. They are never rounded backward. Equal resulting availability times remain equal and may produce a canonical revision conflict.

## Required decision-scoped API

```python
snapshot = read_terminal_minute_snapshot(
    symbol_path,
    reader_identity=reader_id,
)
enrolled_receipts = [*previous_owner_receipts, snapshot.receipt]

observations = decode_terminal_minute_observations(
    snapshot,
    enrolled_receipts,
    reader_identity=reader_id,
    symbol=symbol,
    stream=stream,
    stream_metadata=existing_owner_metadata,
    cutoff=decision_at,
)["minutes"]
```

The caller retains the enrolled receipts through the existing input bundle. This example does not establish identity, source rights or a new persistence owner.

`cutoff` is required, keyword-only and non-null. Omission raises `TypeError`; explicit null raises `InputContractError` before snapshot semantics are parsed. Decode separately for every candidate decision, including a replay of an earlier decision using a later source snapshot.

The bounded reader immediately verifies the outer envelope type/version, complete JSON and size bounds, capture IDs and contiguous sequence, and every payload/record/prefix seal. It retains intact payloads without deciding whether their versions are supported. The decoder then verifies reader-receipt consistency and applies explicit enrollment and the decision cutoff. Only the visible prefix determines supported payload versions, envelope compatibility, v1-to-v2 ordering and event/value semantics. A well-sealed later unsupported, null, object-valued or downgraded payload version cannot disrupt an earlier frame or an old-only enrolled prefix. It is refused once enrolled and visible. A later broken seal, sequence or ID still refuses the whole file immediately.

The output uses the existing minute-input vocabulary: stream, security identity where supplied, revision identity, event start/end, `known_at`, OHLCV and immutable source/reader references. Every Terminal source row carries `basis_id: null` and `basis_refusals: ["TERMINAL_BASIS_UNPROVEN"]`. Caller metadata cannot label or admit that occurrence. The existing selector resolves revisions; this module does not pick a winner.

## Versioned declarations and the basis boundary

The reader accepts `mastermind.intraday_minute_capture.v1` and `.v2`. New v2 payloads carry `schema: mastermind.intraday_minute_capture_payload.v2` and boolean `chart_eligible`. An upgraded envelope preserves an exact ordered prefix of v1 records followed only by v2 records. Old prefix seals and owner-read receipts stay valid; a v1 record after a v2 record is refused when that record enters the enrolled visible prefix.

Each v2 page contains only the normalized declaration object `response_adjusted: {state: ...}`. An observation resolves its exact page by `page_index`; the decoder retains that page index, row index, capture hash, response body hash, response declaration and actual owner-read receipt hash. None is inferred from another response or from the request parameter.

| State | Retained meaning |
|---|---|
| `TRUE` / `FALSE` | The unique top-level response field is an actual JSON boolean |
| `MISSING` | No top-level response field |
| `NULL` | Explicit JSON null |
| `INVALID_TYPE` | A nonboolean, nonnull value; arbitrary raw content is not retained |
| `AMBIGUOUS` | Duplicate top-level declaration keys, even when their values agree |
| `UNPARSED` | A malformed or nonobject response that could not be interpreted |
| `UNRECORDED` | Derived legacy v1 state only; it is never written into an old seal |

`chart_eligible` reports complete transport with nonempty pages all declaring `TRUE`. It does not prove split factors, dividend treatment, volume convention or an adjustment vintage. Complete captures with incompatible declarations remain source observations while the existing chart projection is preserved. Equal raw bars under FALSE → TRUE → FALSE remain three episodes. A later equal declaration and equal values can be suppressed, and a suppressed capture cannot manufacture another revision or relabel an older occurrence.

The current existing `engine/close_pass/massive_close.py` corporate-actions owner returns affected tickers and counts. It does not retain a reconstructable factor table, factor observation clocks or a factor receipt bound to an aggregate-response vintage. A caller label, self-sealed hash, `adjusted=true` declaration or separately fetched latest split table does not supply that missing evidence. Accordingly this slice deliberately implements no basis-admission schema, basis-file reader, trusted method allowlist or synthetic production bypass.

The next dependent phase must extend that existing action/basis owner first. It must produce either evidence intrinsically bound to the exact capture/page/response vintage or reconstructable raw-plus-factors evidence, including explicit price and volume conventions and action evidence. A future consumer may attach its own actual read custody; the source artifact should not depend on knowing that downstream read receipt in advance. Stable compatible basis classification and immutable occurrence evidence are separate identities. This declaration slice closes neither requirement.

The new conformance receipt demonstrates v1 replay, v2 declarations, A/B/A retention, no suppression re-expansion, raw first-seen preservation and basis refusal through the actual producer/store/reader/selector. Its independent synthetic selector control does not establish positive end-to-end market basis. The earlier receipt remains unchanged and cannot be used to reinstate scalar basis inheritance.

## Corrections, nulls and failures

- Consecutive equal finalized observations can be suppressed relative to the last complete capture only when both raw values and the exact referenced page declaration agree. A/B/A remains three observation episodes; equality with an older nonadjacent version does not erase a correction.
- An actual reader that first sees A/B/A together assigns the same first-seen time to those versions. The existing selector returns `CONFLICTING_MINUTE_REVISION`, an unavailable bar and null OHLCV where required. It does not invent the missing intermediate read history.
- Only complete capture attempts contribute model-input observations. A later failed or partial attempt preserves its source receipt and does not advance the complete-capture compaction base.
- Partial failure leaves the existing chart projection unchanged. Empty, forming-only and failed captures are retained. An already enabled, valid empty store can recover through ordinary existing-only refresh while preserving the old prefix.
- Raw fractional volume survives. Missing volume and explicit null volume both remain unavailable as model values, with distinct source-state provenance; neither is converted to zero.
- Provider pagination must preserve the original aggregate path and supplied invariant query values. Contradictory response tickers are refused before row retention. Capture-mode HTTP redirects are refused so they cannot bypass that request boundary.
- Exact sealed-record replay is idempotent. Reusing a capture identity with changed bytes is a conflict. Capacity refusal preserves the prior file byte for byte.

All authority flags remain false. An `adjusted=true` request records the request's declared behavior; it does not prove a stable corporate-action basis. An absent response ticker is not newly minted listing-identity evidence.

## Joint conformance

Run from the Macro checkout with the supported Terminal source available:

```bash
python3 scripts/entry_radar_rs_pullback_source_retention_check.py \
  --terminal-source /absolute/path/to/mastermind-terminal
```

The harness invokes the actual producer, atomic temporary-file store, bounded Macro reader and existing selector. It injects the capture transport and refuses accidental use of the legacy transport. It performs no provider request and reads no market outcomes.

The scenarios retain 30 synthetic original minutes plus two corrections across three complete captures. Their final raw minute closes are 100.39 → 100.44 → 100.39 and the initial raw-volume sum is 517.5. Source-derived 30m bars remain unavailable because basis evidence is absent. The earlier unavailable frame and raw input rows remain byte-identical after later corrections, a later partial failure and a well-sealed future malformed semantic append. A first read after all three versions preserves the same-clock conflict.

The unchanged 900-second finality rule leaves the contemporaneous latest 15m input unavailable. A separate direct-input synthetic selector fixture proves complete-window aggregation without using Terminal rows or conferring source-basis admission. The harness does not backdate the reader clock to manufacture a fresh full frame.

The focused independent reviews required and checked four repairs:

| Counterexample | Required behavior |
|---|---|
| Decoder invoked without a candidate cutoff | Require an explicit non-null cutoff and isolate the complete earlier frame |
| Empty enabled file followed by ordinary existing-only refresh | Recover without deleting its existing sealed prefix |
| JSON pagination switches ticker, grain or range | Refuse before the contradictory request; reject a conflicting response ticker before rows |
| HTTP redirect switches the request identity | Refuse capture-mode redirects through the actual redirect machinery |

The receipt's PASS is a local synthetic conformance result. Exact-head review, hosted checks, merged blob identity and deployment evidence belong in the linked delivery PRs.

## Retention and next admission frontier

Operational bounds are 16 symbols per capture invocation, 4096 capture attempts per file, 16 pages per capture, 8 MiB per response and 32 MiB per file. Limits produce explicit refusal; they do not silently prune evidence. These are capacity bounds, not a promised study horizon. For example, 78 attempts per session would consume 4096 records in about 52 sessions before counting additional failed attempts.

The committed [entitlement record](../../licenses/MASSIVE_ENTITLEMENT_RECORD.md) closes the global licensing gate and covers minute aggregates, research/non-display use and archival retention. Bind that existing operator-confirmed record to the source intake; do not invent a renewed global licensing approval requirement. A specifically designated provider/feed condition or an actual technical entitlement failure remains separately checkable.

Before real accrual is enrolled, the existing source owner must bind the cohort, request coverage, cadence, finality and capacity horizon. The current 900-second finality rule cannot satisfy a contemporaneous latest-15m input merely by waiting for more sessions. A different source/finality contract would require its own owner-backed evidence and review.

Source admission also still requires stable listing identity, adjustment/corporate-action basis, exceptional-session calendar law, actual daily leader/pullback receipts, faithful incumbent assessment inputs and the complete eligible population including nonfires and failures. Natural first-seen history must accrue through real owner observations; historical display files cannot reconstruct it.

Outcome access, feature tuning, H1/H2/H3 experiments and any product or decision promotion remain behind the existing admission gate. The next implementation slice must name its current owner and preserve these refusals until its particular evidence requirement is met.
