# CN integration laboratory: interface decisions for implementation

## Result and scope

The offline experiment passes **63 discriminating checks: 31 positive/interface checks and 32 hostile-input refusals**. It executes the pinned native pack builder, a real three-name gate/probe, the native CN evaluator driver, native reconciliation functions and the native atomic parquet writer. It carries the real October 9 canonical board's score and published rank into a recorded synthetic event and a temporary ledger, then reads that parquet back and repeats reconciliation without changing the rows.

This is executable research, not a deployed repair. All quotes and the October 12 settlement board are explicitly synthetic. No natural market event, executed order, realized return or production write is claimed. The source/data pin remains **`3d90aad6d83152dfeeaf8345bc995826ac9d3139`**. The parent owns the sole research carrier, #8714. Existing R0 #6871 is unchanged.

The important design decision is that the repaired process needs **three separate joins**:

| Evidence being established | Correct authority | What must not substitute for it |
|---|---|---|
| Which thresholds, frozen score and frozen rank produced an intraday event on session N? | The archived armed pack built from N−1, identified by its exact generation | The new N pack that asia-close has just published |
| Did the technical signal qualify on the settled N data? | The N settlement pack's `center_buyable`, only when its as-of and generation qualify | A name merely appearing in the provisional close snapshot |
| How did the provisional close membership compare with the published N board? | The same-session canonical board bytes, with the native membership receipt | The N−1 board, a mismatched same-date artifact, or the technical verdict alone |

The workflow already passes the new N pack after publishing it. That argument is useful for the **settled verdict**, but is the wrong generation for the **intraday event provenance**. The prototype proves the old generation can still be resolved after the current pack key has rolled over.

## What was run

The actual 5,870,788-byte `site/factordata/china_standouts.json` is read through immutable Git. Its SHA256 is `b4dfdb31c07be7610dde7178d6fe665094b85208730e41642214be7219552f72`. The four primary arrays contain 180 distinct names. The 156-name `watch` alias is deliberately ignored.

All 180 source scores and board ranks pass through the actual `cn_pack.assemble` / `attach_frozen` functions after the proposed loader maps the canonical fields. This is a field-projection test, not a claim that 180 names were re-probed.

The genuine probe is bounded to **002460.SZ, 603799.SS and 300750.SZ**, using their exact price files, the exact CN T2 latch with `record=False`, and the exact CN session reference. The pack build makes **60 native gate calls and checks six edges**; three additional centre preflight calls establish that the isolated runtime has no `engine error` verdict. There is no gate stub. The two featured names and one forming name provide both an existing-board observation and a prospective-cross state.

Six native driver passes use synthetic quotes at 10:00, 10:05, 11:35, 13:00, 15:01 and 15:06 China time on the simulated next session. The passes cover debounce, the lunch freeze, afternoon continuation and two close observations. They produce four distinct events in two transition-bearing objects, plus two close snapshots with **zero new transitions**. The recording adapter uses only an in-memory S3-shaped store. Both production no-publish switches remain set, and network connections are disabled during the experiment.

The final synthetic ledger contains:

| Name | Event kind | Native entry class | Frozen score | Frozen board rank | Synthetic settled gate verdict |
|---|---|---|---:|---:|---|
| 002460.SZ | forming | board | 90.0 | 1 | true |
| 300750.SZ | crossing_unconfirmed | cross | 54.0 | 162 | true |
| 300750.SZ | forming | cross | 54.0 | 162 | true |
| 603799.SS | forming | board | 88.0 | 2 | false |

The last row is deliberately dropped from the synthetic settled canonical board. The native membership receipt correctly reports two confirmed memberships and one dropped membership, separately from the ledger's technical `confirmed` field. These values describe the fixture only. They are not October 12 market results.

See [integration_results.json](integration_results.json) for every assertion, native control, input hash and loaded-source hash. [integration_fixture.json](integration_fixture.json) retains the synthetic packs, exact event envelopes and complete resulting ledger rows. Its compact settlement-board subset is for receipt inspection; `run_lab.py` reconstructs the complete synthetic settlement board from the pinned original before checking its byte identity.

## Native failures reproduced

### 1. The frozen-board reader fails at path and schema

`build_cn_live_pack.load_frozen` returns zero names on the real canonical document. Moving that same document to the old expected path still returns zero. The document uses top-level `buy`, `more_actionable`, `late_or_unfillable` and `forming` arrays; the reader expects `lanes`, `names` or `rows`.

Direct native `attach_frozen` on the actual first featured row also omits score and rank. It expects flat `prophet_score` / `prophet_rank`, while the canonical row carries `prophet.score` and `board_rank`.

**Decision:** change the existing loader to the canonical path and four primary arrays, validate duplicate identities and row/board dates, and map the values once. Do not reconstruct rank from array position or `score_rank`. `score_rank` is an optional separately named frozen field; a counterfactual fixture with `score_rank=999` and score `0.0` proves both that a measured zero survives and that board rank remains authoritative.

### 2. The native evaluator's event price is lost

`live_states.transitions` emits **`price`**. `cn_reconcile.events_to_rows` reads **`px`**, `first_px` or `cross_px`. All five events from the unmodified first evaluator pass produce null native first/cross prices.

**Decision:** consume the producer's existing `price` field. The research adapter maps it to the legacy reconciler's `px` input immediately before calling that native function. The production repair should read `price` directly, with an explicit legacy branch if needed. If both aliases appear with different values, refuse the ambiguity. Do not guess which is correct.

### 3. Shared US clock fields leak into CN events

At simulated 10:00 China time, the unmodified CN evaluator produces events with `session_phase="rth"` and emits **`confirming_into_close`** for the two existing-board names. The shared state helper evaluates that flag against the US afternoon clock; the same UTC instant is the preceding US evening.

**Decision:** retain the shared interval/debounce math but set event phase through `cn_clock`. Remove the accidentally inherited US close marker from the CN wrapper. The existing CN close-observation / `close_board` path supplies the close evidence. The prototype does not invent a new pre-close CN window. If the product later needs such a marker, its timing semantics must be specified and tested explicitly.

### 4. Provisional presence is incorrectly used as a settled verdict

The unmodified driver collects every ticker in the provisional close-board lanes into `confirmed`. It labels the deliberately dropped synthetic name true even though the membership receipt later calls the same name dropped.

**Decision:** technical confirmation comes from the same-session settlement pack's `center_buyable`. Missing settlement evidence remains null. Membership confirmation remains the native confirmed/adjusted/dropped receipt against the same-session canonical board. Preserve these separate meanings in the API and UI.

### 5. The spool exists, but the scheduled consumer does not read it

The evaluator already writes under `live_flow/cn_prophet_live_events/<session>/`. `r2io` already provides authenticated reads and paginated listings. The current CN reconciler does not use those helpers. Its scheduled invocation supplies only `--pack`; its events and close-board paths remain absent.

The event envelope also lacks the source pack generation. The current pack key is overwritten by the next nightly build, and the latest live artifact does not provide a durable per-session close archive after later sessions overwrite it.

**Decision:** extend the existing object plane and existing writer. Archive one immutable armed generation, carry its ID in the existing event spool, and persist close snapshots in that same spool even when a close pass creates no transition. No second forward ledger, event service or runtime owner is required.

### 6. Unreadable ledger input can erase prior history

The native `_read_parquet` catches read failure and returns an empty list. The native driver then writes a new parquet at the same path. An intentionally corrupt temporary file is replaced by the five native control rows, proving the behavior without touching production history.

**Decision:** absence and unreadability must be separate. An absent file can start an empty ledger; an unreadable existing file must stop before any write. The research `reconcile_file` function exercises that order using the native atomic writer. A failed read preserves the original bytes.

### 7. Dictionary-only tests miss persisted representation and event classification

The actual parquet roundtrip returns wholly null columns as NaN and can return Arrow list columns as arrays. Those values need normalization before null/keep-first and event-set comparisons. The initial full-file replay exposed this and the prototype now handles it.

The native event's `entered="board"|"cross"` also needs to survive reconciliation. Without it, a featured name's first observation can be counted as a newly discovered intraday cross. The prototype preserves the value and checks it against the source pack class, along with first quote time, phase and raw-price adjustment vocabulary.

## Smallest compatible evidence extension

These are **proposed fields**, not claims that the current producer already emits them. The research schema names deliberately include `research`; implementation must register the final version through the existing owner.

| Existing artifact | Additive extension or corrected read | Purpose |
|---|---|---|
| Armed pack | `source_board` containing board as-of, definition, exact artifact SHA256, source path and effective ordering basis | Bind frozen values to the document actually read. |
| Armed pack | `pack_id`, SHA256 of canonical JSON excluding that field | Identify the exact threshold/frozen-field generation. Build timestamps and telemetry remain part of this generation identity. |
| Existing R2 armed-pack writer | An immutable copy at `live_flow/cn_prophet_live_armed/<as_of>/<pack_id>.json`, plus the unchanged current key | Resolve yesterday's actual thresholds after tonight publishes a new current pack. This is one artifact copy under the existing writer, not a new store authority. |
| Live artifact and close snapshot | Carry `pack_id` and source-board identity; close snapshot carries its observed session | Reset debounce on a changed generation and reject mixed-generation close evidence. |
| Existing event-spool envelope | Schema, session, built-at, pack ID/as-of, source-board identity, quote-age policy and optional close snapshot | Make each pass interpretable without whichever pack happens to be current later. |
| Existing event row | Preserve native `price`, `entered`, phase, state transition fields; add quote timestamp, price-adjustment family and deterministic `event_id` | Keep first observations, distinguish board/cross populations and deduplicate retries. |
| Existing event object name | Existing session prefix plus pass time and complete envelope-content digest | Same-second different payloads cannot overwrite each other; an identical payload has an identical key. |
| Existing forward parquet | Add source/pack/event identity, frozen score/rank/lane, quote clock, entry class, source basis and confirmation generation columns | Preserve evidence without changing `(date,ticker,kind)` or moving the writer. |

There is intentionally **no manufactured rank for a prospective cross absent from the prior canonical board**. Such a pack entry has `frozen_status="not_in_source_board"`; score/rank remain unavailable. Mapping the four canonical arrays does not imply restricting the probe universe to those arrays.

The new input validator refuses legacy envelopes without generation evidence. Existing historical rows remain unchanged; an unbound row colliding with a new bound daily key is quarantined for the existing owner's adjudication. It must not acquire a plausible current pack ID retroactively.

For a same-day key with two genuine pack generations, this prototype also refuses the conflict. It preserves the existing daily-key law instead of silently changing ledger granularity. The raw immutable objects preserve both inputs for a separately adjudicated correction. This is a concrete migration boundary, not an instruction to create another ledger.

## Reconciliation order and failure semantics

1. Read the current ledger strictly, distinguishing absent from unreadable. Normalize persisted null and list representations.
2. Choose a bounded set of completed CN sessions through the existing calendar. The fixture targets one explicit session; implementation can expose the existing owner's bounded catch-up selection and explicit historical replay.
3. List every object in each selected session prefix and finish pagination. An error or missing page token stops the ingest. The existing `r2io.list_keys` can return a partial list after failure, so its CN consumer needs a strict mode or a checked listing wrapper.
4. Fetch every listed envelope over the authenticated object API. No public-cache fallback belongs in this stateful reconciliation path. A missing/unreadable object stops that session before writing.
5. Resolve each envelope's archived prior-session pack. Validate its bytes/ID, source-board identity, quote/event clocks, ticker, kind, phase and price vocabulary. Sort by event time, then event identity, and deduplicate exact event IDs.
6. Obtain the same-session settlement verdict and canonical membership receipt separately. A same-date canonical body with a different hash from the settlement pack's source is refused. A behind canonical board cannot confirm the new session.
7. Compare immutable first-observation identities against existing rows. A changed source identity, changed first-event identity, disappearing previously consumed event or changed confirmed verdict is a conflict, not a normal overwrite.
8. Call the existing native merge and atomic writer. Publish the existing confirmation receipt only after a successful committed write. Keep operational success/failure distinct from the workflow's nonfatal exit policy.

The quote-age check retains the native CN lunch-aware age calculation. The fixture uses a **60-second future-clock allowance** and records the evaluated age policy in the envelope. That allowance is an explicit experiment setting; it needs production ratification. Large future dates and previous-session quotes cannot become fresh observations through the native zero-clamped age calculation.

## Minimal production patch map

| Existing component | Concrete bounded change | Acceptance supplied here / proof still owed |
|---|---|---|
| `scripts/build_cn_live_pack.py::load_frozen` | Canonical path, four arrays, strict identity/date validation and correct score/rank mapping | Real document and all 180 mappings exercised. |
| `engine/prophet_live/cn_pack.py` | Bind source-board and pack identities; preserve board rank versus score rank; show only actually present frozen fields in repaint disclosure | Exact mapping and zero-score fixture exercised. Disclosure wording remains a small implementation edit. |
| Existing pack publisher / `r2io` | Write content-addressed immutable pack copy before updating current key; retain the existing publisher and namespace owner | In-memory rollover and lookup exercised; real R2 permissions/retention and write receipts still owed. |
| `engine/prophet_live/cn_states.py` | Generation-aware predecessor reset; CN phase stamping; remove US close marker; retain CN close evidence | Actual native state machine exercised behind these proposed checks. |
| `scripts/cn_live_evaluator.py` | Preserve native event price/class; add event provenance and source clocks; persist zero-transition close snapshots in the existing spool | Six actual driver passes with injected transport exercised. Native host timer and natural object writes still owed. |
| `engine/prophet_live/cn_reconcile.py` | Native price alias correction; carry first-observation metadata; canonical technical-confirmation source; immutable identity conflict checks | Actual merge/receipt functions exercised with strict adapter and persisted replay. |
| `scripts/reconcile_cn_live.py` | Strict existing-ledger read; authenticated complete spool loader; resolve archived prior packs; use new `--pack` only as same-session verdict authority; publish receipt after success | Actual file write/read/replay exercised in temporary files. Scheduled production arguments and durable sink delivery still owed. |
| `.github/workflows/asia-close.yml` and existing DAG module entry | Invoke the repaired default spool consumer with bounded session context and N settlement pack; preserve `CN_LANE=asia`; expose nonfatal refusal counts | Current actual invocation read. No workflow edit or real scheduled run performed. |
| Existing nightly tradability owner and pack caller | Supply the same current broad stock-quality/tradability metadata before probing; missing required metadata must have an explicit policy | This lab uses three named price series and therefore does **not** establish full-universe ST/ADV/suspension-screen parity. The existing missing caller argument still needs its focused production fixture. |

## Remaining production proof gates

The interface choices above are settled enough for bounded implementation. Production acceptance still needs the exact installed evaluator source/release, one natural armed generation, a natural intraday event, a persisted zero-transition close snapshot, the actual scheduled consumer, and an idempotent write/read of the existing durable ledger. The real object API must prove complete listing, archive retention and failure reporting; the fake transport cannot establish those properties.

Full-universe tradability metadata and its missing-data policy need verification in the owning pack caller. Source-board publication receipts remain the existing W0/R0 responsibility. Raw/adjusted execution prices, legal fills and delayed outcome grading remain W1 responsibilities. This experiment deliberately leaves `close_same_day` and `next_close_fill` unresolved rather than dividing unrelated price bases or inventing a trade.

The pack's price-adjustment string is the current producer's declaration. The laboratory does not independently certify the underlying files' original price basis or corporate-action vintage. Preserving that declaration and the contemporaneous anchor prevents silent field loss; it does not by itself validate a return calculation.

No rank promotion or candidate-quality improvement follows from this pass. The result establishes a much more concrete implementation contract and a reproducible fixture battery for the known data path.

## Reproduce

```bash
python3 run_lab.py \
  --repo /path/to/macro \
  --sha 3d90aad6d83152dfeeaf8345bc995826ac9d3139 \
  --out /tmp/cn-integration-results
```

The runner exports pinned engine/lib/scripts into its own temporary directory and reads all prices, latch, board and session reference through immutable Git objects. It refuses an output directory inside the source repository and refuses importing from that shared worktree. Python, pandas, a parquet engine and PyYAML are required. The recorded execution used Python 3.14.7 and pandas 3.0.5.

The first incomplete isolated export lacked the CN session-anchor file. The gate correctly reported `engine error`; the laboratory stopped, added the exact pinned `data/china/000001.SS.parquet`, and added an explicit gate-dependency check. This was a harness setup correction, not a claimed production outage. Later file-backed replay exposed the nullable-column normalization issue described above and was corrected before the final PASS.

Measured pack build duration is included in the content hash, so a fresh run may produce different pack/event IDs while preserving all assertions and the same mathematical values. The saved fixtures are exact records of the recorded run. Their source hashes and the two laboratory code hashes are included in the result; the delivery manifest binds the retained files.
