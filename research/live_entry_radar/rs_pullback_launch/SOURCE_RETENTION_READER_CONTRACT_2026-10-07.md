# RS Pullback Launch: retained-minute reader contract

Workstream: `WS:LIVE-ENTRY-RADAR`  
Operations: original `rs-pullback-launch-source-retention-20261007-sol-002`; correction `rs-pullback-launch-basis-binding-20261007-sol-005`; v3 companion `rs-pullback-launch-unadjusted-capture-20261007-sol-007`
Date: 2026-10-07  
Scope: source retention, v1/v2/v3 acquisition provenance and basis-unavailable input conformance

## Result and evidence boundary

Terminal can retain bounded one-minute source observations in its existing per-symbol store. The Macro bridge can turn an actual owner read of those bytes into decision-scoped inputs for the existing RS input selector. The producer and consumer remain within their current ownership boundaries.

[Phase 1](PHASE1_ADMISSION_2026-10-07.json) remains **NOT_ADMITTED** with 29 refusals; H1, H2 and H3 remain **NOT_TESTED**. The admission artifact SHA-256 remains `a4e00a5c191917dc8c64fb74ca3348827ab9bd47d9ad8a03a1130a50fde36e9f`. Retention code, synthetic conformance, hosted CI and deployment are separate evidence classes.

The unchanged [original joint conformance receipt](SOURCE_RETENTION_CONFORMANCE_2026-10-07.json) and [v2 declaration and basis-refusal receipt](SOURCE_BASIS_DECLARATION_CONFORMANCE_2026-10-07.json) remain historical evidence for their exact source revisions. The distinct [v3 role and unadjusted-capture receipt](SOURCE_UNADJUSTED_CAPTURE_CONFORMANCE_2026-10-07.json) binds its recorded pre-R27 implementation by exact file SHA-256 values; it is historical evidence and does not bind the later decoder-output extension below. All three use injected transport and synthetic clocks; none is a real market observation. The original producer was delivered through [Terminal PR #840](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/840); this source packet does not assert v3 delivery or activation.

## R27 decoder output v2 — 2026-10-20

R27 adds an explicit **decode-output version**, independent of Terminal capture
v1/v2/v3. The default `DECODE_SCHEMA` remains output v1, with its existing
serialization and row seals unchanged. Callers opt in with
`output_schema=DECODE_SCHEMA_V2`; unknown or malformed modes refuse.

After a capture is enrolled, visible at the actual decision cutoff and validated
against the explicit expected symbol, every emitted v2 row carries:

```python
source_observation = {
    # Existing capture, page, row and owner-read provenance stays intact.
    "decode_schema": "mastermind.entry_radar.terminal_minute_observations.v2",
    "source_vendor": payload["source"],
    "source_symbol": payload["symbol"],
}
```

The provider and symbol come from the validated retained payload. Caller stream
metadata, a security-ID suffix, an option root or an attestation boolean cannot
supply or replace them. The fields are inside the existing full-row receipt
digest, and the envelope carries the selected output schema. Keeping the version
on each row preserves its meaning when callers extract only `minutes`.

No usable source query is created for an incomplete, failed, empty, suppressed,
unenrolled or not-yet-visible observation. Future capture semantics remain
uninterpreted until the existing enrolled-prefix visibility boundary permits them.

Choosing v2 changes serialization and its row digest. It does **not** create a new
capture, market revision, reader receipt or availability clock. Use one output
representation per observation in a candidate. Combining v1/v2 representations
of the same observation remains a conflicting revision in the existing selector.
Historic reconstruction requires the retained raw snapshot and genuine original
owner-read receipts; running the new decoder now is not evidence that v2 output
was issued historically. A current reread supplies current availability only.

The fields support a future native identity query. They do not authenticate
custody, prove a security binding or admit a market source. A caller can recompute
a JSON checksum; consumers must invoke the owner decoder from custodied reader
inputs instead of recognizing an arbitrary decorated JSON row as owner proof.
`basis_id=None`, `TERMINAL_BASIS_UNPROVEN`, all other owner requirements, and false
admission/trading authority remain intact.

The new synthetic suite is
`tests/test_entry_radar_terminal_native_query.py`. It binds complete pre-R27 v1
outputs for legacy capture v1/v2 and both v3 roles to the exact prior decoder,
then proves the explicit output-version delta, original read-clock boundary,
query provenance, unchanged revision identities, and preserved selector refusals.
It does not replace or refresh the historical joint conformance receipts.

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

The bounded reader immediately verifies the outer envelope type/version, complete JSON and size bounds, capture IDs and contiguous sequence, and every payload/record/prefix seal. It retains intact payloads without deciding whether their versions are supported. The decoder then verifies reader-receipt consistency and applies explicit enrollment and the decision cutoff. Only the visible prefix determines supported payload versions, envelope compatibility, nondecreasing v1-to-v2-to-v3 ordering, declared acquisition role/request consistency and event/value semantics. A well-sealed later unsupported, null, object-valued or downgraded payload version cannot disrupt an earlier frame or an old-only enrolled prefix. It is refused once enrolled and visible. A later broken seal, sequence or ID still refuses the whole file immediately.

The output uses the existing minute-input vocabulary: stream, security identity where supplied, revision identity, event start/end, `known_at`, OHLCV and immutable source/reader references. Every Terminal source row carries `basis_id: null` and `basis_refusals: ["TERMINAL_BASIS_UNPROVEN"]`. Caller metadata cannot label or admit that occurrence. The existing selector resolves revisions; this module does not pick a winner.

## Versioned declarations and the basis boundary

The reader accepts `mastermind.intraday_minute_capture.v1`, `.v2` and `.v3`. Versioned payloads carry `mastermind.intraday_minute_capture_payload.v2` or `.v3` and Boolean `chart_eligible`; v1 has no payload schema. An upgraded envelope preserves exact ordered v1/v2 prefixes followed by v3 records. Every new candidate-producer capture is v3, including ordinary chart captures. Old prefix seals and owner-read receipts stay valid. A payload version downgrade or a payload version newer than its envelope refuses only when enrolled and visible; intact future semantics cannot invalidate an earlier visible prefix.

V3 requires the closed `acquisition_role` values `chart_adjusted` and `research_unadjusted`, with actual Boolean `request.adjusted` true and false respectively. Nulls, missing roles, unknown labels, objects, strings or numeric substitutes refuse. This role/request relationship is validated for visible incomplete captures too, before their nonrevision diagnostic return. Legacy v1/v2 requests derive the chart role internally and cannot declare a v3 role.

V1/v2 output rows retain their exact prior shape and row-receipt hashes. Only v3 rows gain `acquisition_role` and `capture_payload_schema` inside their existing `source_observation`; `request_adjusted` records the actual exact Boolean. Source capture/page/body identity and the independent actual read receipt remain attached to each occurrence. Omitted v3 metadata on a legacy row is a derived legacy chart role, never evidence of an unadjusted acquisition.

Each v2/v3 page contains only the normalized declaration object `response_adjusted: {state: ...}`. An observation resolves its exact page by `page_index`; the decoder retains that page index, row index, capture hash, response body hash, response declaration and actual owner-read receipt hash. None is inferred from another response or from the request parameter.

| State | Retained meaning |
|---|---|
| `TRUE` / `FALSE` | The unique top-level response field is an actual JSON boolean |
| `MISSING` | No top-level response field |
| `NULL` | Explicit JSON null |
| `INVALID_TYPE` | A nonboolean, nonnull value; arbitrary raw content is not retained |
| `AMBIGUOUS` | Duplicate top-level declaration keys, even when their values agree |
| `UNPARSED` | A malformed or nonobject response that could not be interpreted |
| `UNRECORDED` | Derived legacy v1 state only; it is never written into an old seal |

`chart_eligible` reports the chart role, a true request, complete transport and nonempty successful pages all declaring `TRUE`. Every research-unadjusted payload is chart-ineligible, even when its returned declaration is TRUE. Raw request compliance requires the raw role, an actual false request and complete successful pages all declaring FALSE; it is not full basis admission. It does not prove split factors, dividend treatment, volume convention or an adjustment vintage. Complete captures with incompatible declarations remain source observations while the existing chart projection is preserved. Equal raw bars under FALSE → TRUE → FALSE remain three episodes. A later equal declaration and equal values can be suppressed, and a suppressed capture cannot manufacture another revision or relabel an older occurrence.

At this source baseline, the existing `engine/close_pass/massive_close.py` corporate-actions owner returns affected tickers and counts. It does not retain a reconstructable factor table, factor observation clocks or a factor receipt bound to an aggregate-response vintage. A caller label, self-sealed hash, `adjusted=true` declaration or separately fetched latest split table does not supply that missing evidence. Accordingly this slice deliberately implements no basis-admission schema, basis-file reader, trusted method allowlist or synthetic production bypass.

The next dependent phase must extend that existing action/basis owner first. It must produce either evidence intrinsically bound to the exact capture/page/response vintage or reconstructable raw-plus-factors evidence, including explicit price and volume conventions and action evidence. A future consumer may attach its own actual read custody; the source artifact should not depend on knowing that downstream read receipt in advance. Stable compatible basis classification and immutable occurrence evidence are separate identities. This declaration slice closes neither requirement.

The v3 conformance receipt demonstrates exact v1/v2 replay, both acquisition roles, A/B/A retention, no suppression re-expansion, original first-seen preservation and basis refusal through the actual producer/store/reader/selector. Its independent synthetic selector control does not establish positive end-to-end market basis. The historical receipts remain unchanged and cannot be used to reinstate scalar basis inheritance.

## Corrections, nulls and failures

- Consecutive equal finalized observations can be suppressed only within the same acquisition role, requested adjustment Boolean and event start, when both raw values and the exact referenced page declaration agree. The sealed date window is provenance, not a new compaction partition. A/B/A remains three observation episodes per role; cross-role interleaving cannot suppress a real correction or re-expand a previously suppressed observation. Partial/failed/empty/suppressed attempts preserve the inherited latest-complete observation baseline.
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

The receipt's PASS is a local synthetic conformance result. The new joint scenario additionally interleaves eight chart/raw acquisitions, retaining counts `[30,30,1,0,1,1,1,0]`: 32 occurrences in each role. Raw acquisitions preserve all noncapture chart fields, and a later raw partial attempt creates no reader revision. Original v1 and v2 rows, row receipts and earlier frames replay exactly after the real writer upgrades each legacy fixture. Phase-1, source census, calendar, both historical conformance artifacts and the selector are hash-checked unchanged. Exact-head review, hosted checks, merged blob identity and deployment evidence belong in the delivery PRs.

A compatible Macro reader must be installed before the v3 writer is released. The raw producer flag is `--capture-unadjusted-minutes --symbols EXPLICIT --tf 1m`, mutually exclusive with `--capture-minutes`. It rejects chart refresh/force/expect-advance controls, uses one request chain per explicit symbol and always downloads the existing 40-day profile. Raw mode bypasses chart refresh, basis-ratio/rebuild/merge and chart watermarks. There is no automatic second provider request, new watermark, overlap optimization, live cadence authorization or approved runtime cohort in this source slice. Compaction reduces retained observations, not provider traffic.

## Retention and next admission frontier

Operational bounds are 16 symbols per capture invocation, 4096 capture attempts per file, 16 pages per capture, 8 MiB per response and 32 MiB per file. Limits produce explicit refusal; they do not silently prune evidence. These are capacity bounds, not a promised study horizon. For example, 78 attempts per session would consume 4096 records in about 52 sessions before counting additional failed attempts.

The committed [entitlement record](../../licenses/MASSIVE_ENTITLEMENT_RECORD.md) closes the global licensing gate and covers minute aggregates, research/non-display use and archival retention. Bind that existing operator-confirmed record to the source intake; do not invent a renewed global licensing approval requirement. A specifically designated provider/feed condition or an actual technical entitlement failure remains separately checkable.

Before real accrual is enrolled, the existing source owner must bind the cohort, request coverage, cadence, finality and capacity horizon. The current 900-second finality rule cannot satisfy a contemporaneous latest-15m input merely by waiting for more sessions. A different source/finality contract would require its own owner-backed evidence and review.

Source admission also still requires stable listing identity, adjustment/corporate-action basis, exceptional-session calendar law, actual daily leader/pullback receipts, faithful incumbent assessment inputs and the complete eligible population including nonfires and failures. Natural first-seen history must accrue through real owner observations; historical display files cannot reconstruct it.

Outcome access, feature tuning, H1/H2/H3 experiments and any product or decision promotion remain behind the existing admission gate. The next implementation slice must name its current owner and preserve these refusals until its particular evidence requirement is met.


## V3 companion verification

The source-only companion is based on Macro
`a57a4527176f89e461219803df538de4571f78b9`. The focused affected gate passed
**237 tests and 85 subtests**, with eight inherited pytest cleanup warnings for
unrelated older Chromium temporary directories:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest \
  tests/test_entry_radar_terminal_minute_observations.py \
  tests/test_entry_radar_rs_pullback_phase1.py \
  tests/test_entry_radar_rs_pullback_calendar.py \
  -q -p no:cacheprovider
```

The 154 reader cases include both v3 roles and every parsed declaration state;
exact request booleans; fractional/null/missing volume; immutable capture/page/body
and reader custody references; exact v1/v2 rows and earlier frames after v3 role
interleaving; unsupported future roles, requests and versions across complete,
partial and failed attempts; visible downgrade refusal; immediate broken-seal,
sequence, ID and outer-envelope rejection; partial/failed/empty/suppressed attempts
that create no new revision; malformed status primitives; and scalar-relabel refusal
through the unchanged selector.

A separate compatibility control loaded the exact decoder from the pinned v2 commit
and the candidate decoder against identical actual bounded-read snapshots and
receipts. Their complete canonical outputs matched for 30 v1 and 30 v2 rows. The
Phase-1, source census, calendar, original retention and v2 conformance JSON files
and the selector also matched their pinned source bytes exactly.

The distinct v3 joint artifact binds the final exercised producer/reader/harness/test/
contract source hashes. It must be regenerated if any bound source changes, including
an independently reviewed Terminal transport repair. Its synthetic clocks and local
PASS do not establish source admission, hosted delivery, installed compatibility or
a live collection budget.


## R28: explicit native owner-read consumer join

`engine/entry_radar/replay/rs_pullback_native_identity.py` adds
`build_input_panel_from_owner_reads`. It is an opt-in research entry point above
the existing R27 Terminal decoder and R12 identity selector. The public
`build_input_panel` JSON v1/v2 entry point retains its prior behavior; its complete
pre-change synthetic panel hashes remain pinned by the R28 compatibility tests.

| Contract | Schema |
| --- | --- |
| Native input description | `mastermind.rs_pullback_launch.phase1_owner_input.v1` |
| Native panel | `mastermind.rs_pullback_launch.phase1_owner_panel.v1` |
| Per-candidate, per-role identity binding report | `mastermind.rs_pullback_launch.native_identity_binding.v1` |

The native input description carries an explicit `window_policy_schema` equal to
the existing phase1 input v1 or v2 schema, the same fixed candidate population,
calendar and context contracts, and `required_symbols` for stock, SPY, QQQ and
sector roles. Symbols constrain decoding; they never supply a missing source
query. Stream metadata can still carry basis and availability evidence. Caller
`minutes`, JSON Terminal read receipts, and legacy stream `identity` or
`security_id` metadata are rejected by this entry point.

### Actual objects and explicit enrollment

Callers retain the actual immutable objects returned by
`read_terminal_minute_snapshot` and `read_identity_snapshot`. A
`NativeRoleReads` value contains:

- `terminal_read`: the retained current Terminal snapshot, or `None`.
- `enrolled_terminal_reads`: a tuple of actual Terminal read objects whose
  receipts explicitly enroll the current snapshot's retained prefixes.
- `identity_read`: the actual identity generation read for this candidate and
  role, or `None`.

Supply these values through `owner_reads[candidate_id][role]` and pass the
configured `reader_identity` separately. The current Terminal snapshot is not
implicitly enrolled. Missing candidates or roles in this mapping remain in the
predeclared population with unavailable inputs. Unknown candidate/role mappings
and arbitrary dictionaries presented as native read objects are contract errors.

This shape allows an earlier candidate to retain its original read while a later
candidate uses a genuinely later read. It creates neither an identity revision
store nor a second selector. Python types and checksums do not authenticate a
caller; trusted reader call-path custody and retention of the original source
objects are still required. Creating or reading an object today does not grant
it historical availability.

### Decision order and retained evidence

The existing calendar and window-policy guards run first. Once a candidate is
inside its visible owner session and passes those guards, each role proceeds as
follows:

1. Decode the actual retained Terminal snapshot through R27 output v2, with
   `stream_metadata=None`, explicit enrolled receipts, the frozen role symbol,
   and actual `decision_at`. Only visible decoded rows whose event starts are in
   the owner's `[open, close)` session can supply a query.
2. Derive one exact provider/symbol pair from those rows' source observations.
   Display bars, a capture header without retained observations, incomplete or
   failed captures, another session's rows, and caller metadata cannot supply a
   substitute query. No visible source query means no identity-owner call.
3. Inspect only the identity consumer-read completion clock needed to establish
   visibility. A valid clock strictly after the decision withholds the input
   before `alias_table()` parses its identity payload. An invalid clock cannot
   establish future invisibility and produces a retained source refusal.
4. For an eligible read, invoke the existing
   `alias_table().resolve_binding(vendor, vendor_symbol, owner_session_date,
   decision_at=actual_cutoff, snapshot_receipts=(actual_receipt,))`.
   R12 continues to own validity intervals, semantic validation, history
   selection, refusal and binding. The adapter invents no interval or security
   identity.
5. Run the original minute, revision, price/volume basis, first-seen and context
   checks using the resolved effective identity. Native identity replaces only
   the legacy identity-metadata check.

The cutoff follows the existing panel's conservative microsecond representation:
a finer instant is never rounded forward to admit later evidence. The v2 feature
anchor determines window geometry only; it never substitutes for the actual
decision cutoff used for Terminal, identity, basis or context visibility.

The original decoded row is copied without filling its `security_id`, changing
its revision or recalculating its seal. Its effective native identity travels
separately through the private aggregation path. The binding report commits the
unchanged row-set digest, each original row receipt/revision, and the actually
selected Terminal read receipts.

The report preserves the complete native `AliasResolution`, including intentional
null fields. In particular, a native `REFUSED` result may leave `vendor_symbol`
and `security_id` null; the visible query is retained separately. The full identity
consumer-read receipt is included only when the actual native result names that
read's matching snapshot `receipt_sha256`. This applies to `BOUND`, `REFUSED`,
and `UNAVAILABLE / NO_BINDING_AT_EVENT_DATE`. A native result with no selected
receipt contributes no supplied generation, artifact vector, history prefix or
read clocks. An adapter-level future-read unavailability has no fabricated native
resolution.

Each binding report has its own digest and enters the candidate snapshot digest.
Full supplied-read diagnostics and opaque input hashes remain at panel level;
future-only provenance is excluded from candidate digests. With valid availability
clocks still strictly after cutoff, changing future payloads or receipt semantics
cannot change the earlier candidate. Once malformed source bytes become visible,
typed identity/JSON/encoding errors retain a refused candidate. Unexpected
implementation errors remain errors instead of being disguised as missing data.

### Remaining limits and verification scope

R28 does not admit Terminal's adjustment basis. `TERMINAL_BASIS_UNPROVEN` still
blocks an aggregate even when native identity is `BOUND`. Same-clock revision
conflicts, missing minutes, first-seen failures, calendar/window guards, daily
context and incumbent assessment requirements remain effective. All candidates
remain present; no outcome, firing state, score, registered detector or trading
authority is created.

The new synthetic suite exercises real temporary file/Parquet reader paths,
native MU binding and ETF refusals, exact source-row preservation, actual
decision versus feature-anchor visibility, per-candidate retained reads,
future-payload invariance, nanosecond availability exclusion, typed refusal
retention, revision conflicts and both legacy full-output goldens. It is included
in the existing `entry-radar-rs-pullback-calendar` CI job with the existing identity
reader's dependency closure and PyArrow dependency. These fixtures and source
checks are not authentic market-data availability or identity-publication proof.

No canonical identity generation is promoted by this consumer API. Source
publication, independent review, production-host qualification, canonical
generation authority, missing authentic ETF bindings and market-data admission
remain distinct requirements. Historical conformance receipts earlier in this
document retain their original source binding; they are not silently rebound to
R28 or presented as a new joint execution.
