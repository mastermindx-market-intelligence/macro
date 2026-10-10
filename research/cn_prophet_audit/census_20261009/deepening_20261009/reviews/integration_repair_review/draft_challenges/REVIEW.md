# Pre-seal event-time authority challenge

The retained repair draft `a0c26607448a7f57f296393508f3b0a92c8a1eea9ee44bf4a053464dcb76a335` accepts two internally inconsistent first-observation claims. Both failures concern a later envelope timestamp being used as authority for an earlier event.

| Case | Controlled input | Draft outcome | Required rule |
|---|---|---|---|
| R-C1: source receipt after event | The pinned native evaluator emits an event at 02:01 from a source receipt recorded at 02:01, containing a quoted 02:00 print. The independent probe changes the event timestamp to 02:00 and recomputes event/envelope identities, while the envelope remains 02:01. | Ingestion returns `first_ts=02:00`, earlier than the source receipt. | Resolve source availability against the event timestamp, while retaining the separate envelope publication check. |
| R-C2: archived generation built after event | The source receipt is genuinely declared available at 02:00 in the synthetic scenario. A separately resealed pack is built at 02:01; the event claims 02:00 inside a 02:01 envelope. | Ingestion accepts the later-built generation as authority for the earlier event. | Require the archived pack build to be known by the event timestamp as well. |

The valid control restores the native event timestamp to 02:01 and succeeds. These cases do not show the native evaluator naturally generating an early event. They are deliberate persisted-input mutations challenging the proposed replay trust boundary. Recomputed hashes establish content identity; they do not excuse contradictory clock relationships.

Run `python probe_source_clock.py`. It uses the byte-retained draft, the exact nine-module native bundle from the sealed original independent review, and the SHA-256-checked pinned quote parser. It writes deterministic `CLOCK_EVIDENCE.json`, which includes complete pack and envelope inputs, returned first-observation projections, the positive control and exact source hashes. `source_clock_input.json` preserves the initial single-case terminal experiment before the paired oracle was added.

The producer acknowledged both findings and accepted event-time source and pack checks before sealing the final candidate. This directory preserves the challenged version and is not acceptance of the later repaired version. No production source, ledger, collector, object store, vendor or natural execution was involved.
