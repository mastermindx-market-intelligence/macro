# Independent acceptance of the repaired integration contract

**Decision: ACCEPTED_AS_BOUNDED_OFFLINE_RESEARCH_CONTRACT.** The exact candidate passed 80 independently authored checks, including native evaluator/parser execution and genuine Parquet persistence. No blocker remains in the reviewed seams. This decision accepts the research contract as input to implementation; it does not certify a deployed or naturally observed production roundtrip.

## Exact reviewed version

| Artifact | SHA-256 |
|---|---|
| Candidate `repairs/integration_contract/MANIFEST.json` | `371fd67d4ea85307e460772f8aa353609d176ff779f07811a0a42f8ea36c0309` |
| Candidate `contract_prototype.py` | `3518cc9f408534cccbe60419b8de8d7143ad42f406c7d9ee262068ef1c5fe2e0` |
| Independent `ACCEPTANCE_RESULTS.json` | `ee33a08cce51a8ca5322eca0033543c452ad86ea3a15a6742c8ca5ab3a96acdf` |
| Independent `independent_fixture.json` | `b3c137cb844aa54d82445af738ee2f2ed63f370d65ee5e192df43c2509ee79b6` |
| Independent native `PARQUET_RECEIPT.json` | `e998f198656dfde1a424d718efdd836973c5ce7a084fff78cf05a66dc45fed3f` |

Study source remains `3d90aad6d83152dfeeaf8345bc995826ac9d3139`. The independently retained nine-module native bundle is `2c139c0fef2c83296374069aed3338ccc28802bbf535d75054176384ec9ec829`. The pinned quote parser source is `bd8bfd85bf4ff1279d564220b7f3f8b8b4e5f7263323252ae6489ed5163d1074`, Git blob `f7ad6ebc550811708a20aaf259b30dd1df0a3699`.

The producer reported 136 native checks and a 59-check retained-fixture replay. Those are separate evidence sets. The 80 checks reported here include adversarial behavior, positive compatibility, byte custody and receipt verification; the count is not 80 distinct market scenarios.

## Independence and the accepted positive path

`accept_repair.py` does not import the producer runner. `independent_fixture.py` independently builds exact synthetic UTF-8 quote payloads, a compact canonical artifact and a matching settlement pack. It reuses the original lab's three-name armed fixture and synthetic prices. The exact native source bodies are compiled from the retained bundle; quote parsing executes the pinned adapter body. Network connections are disabled.

Four native passes produce event counts `[3, 1, 0, 0]` and four daily rows, because a daily key includes the event kind. Current-pack rollover does not remove the archived prior generation. The prior-session pack supplies the armed generation and frozen first-observation fields; the same-session settlement pack supplies the technical verdict; the exact same-session canonical bytes supply the membership receipt. These remain three distinct authorities. Settlement approves the technical gate for `002460.SZ` and `300750.SZ`, and declines `603799.SS`; the synthetic canonical membership includes the first two. Close/fill values remain unavailable. No execution or return is manufactured.

## Original findings resolved

| Finding | Independent discriminating evidence | Accepted behavior |
|---|---|---|
| F1: entire previously consumed daily key can vanish from the spool | Remove the first transition object, every transition object, or part of an existing event-ID set while retaining valid close evidence. | Each regression refuses with `spool_regression`. A genuinely new empty session with valid close evidence remains supported. |
| F2: conflicting equal-time close membership can depend on object-key order | Preserve conflicting economics and vary only an inert nonce so the alternative object sorts before or after the fixed object. Also reverse equivalent rows and vary display metadata. | Both conflicting orders refuse with `conflicting_equal_time_close_evidence`. Equivalent observations coalesce while retaining both source object identities. |
| F3: copied quotes acquire unsupported adjustment provenance | Test missing, adjusted and bare raw declarations; a caller qualification Boolean; changed source text; copied price changes; and a rehashed event with a changed price. | Unsupported inputs remain unavailable or take typed refusals. Price binds to replay of the retained exact source bytes. Whitespace variants retain distinct byte identities even when the parsed record is equal. The positive basis is explicitly `unadjusted_research_fixture`. |
| F4: readable duplicate Parquet keys silently lose history | Write real Parquet containing conflicting duplicate keys in both orders, exact duplicate keys, and a readable unrelated schema. | All four cases refuse before a native writer call. Before/after bytes are identical. |
| F5: standalone frozen-score validation misses its domain | Supply rehashed scores `-1` and `100.01`; use `0` and `100` as controls. | Out-of-range values refuse; both boundaries remain valid. |
| F6: huge integer overflows a whole evaluation | Exercise `10**400` in the numeric predicate, a copied quote and the source payload. | No unhandled overflow. Invalid quotes are rejected per name while valid peers continue; invalid source payload magnitude takes a typed refusal. |
| F7: immutable copied first-observation fields can change | Alter first price, quote time, source payload/record hashes, source definition, cross basis, quote age or prior state. Recompute the local first-projection digest after a price change. | All first-observation conflicts refuse. Rehashing does not grant authority. A genuine later native transition still updates last/count fields while preserving the first projection. |

The executable inputs and outcomes are retained in `ACCEPTANCE_RESULTS.json`, `independent_fixture.json` and the Parquet files. These hostile mutations demonstrate contract failure handling; they are not evidence that the corresponding mutations occurred in natural production.

## Additional boundaries established during review

The sealed `draft_challenges` package preserves two earlier accepted-but-invalid draft inputs: a source receipt after its event time, and an archived pack built after its event time. A later envelope build did not authorize either backdate. The final candidate refuses these exact temporal claims with `future_quote_source_receipt` and `future_pack_build`. The acceptance adapts the source evidence to the repaired codec before testing, so a schema refusal cannot be mistaken for temporal correctness.

Distinct authentic events with the same daily key and exact event time cannot use a digest as first-observation ordering authority. They now refuse with `ambiguous_equal_time_events`. Exact event-ID replay is deduplicated first and remains idempotent; a genuinely later repeat remains supported.

The intermediate `d633f0ba` candidate exposed a different, normal-path precision issue: native second truncation made an authentic synthetic source receipt at `02:00:00.250000` appear later than its unchanged emitted event at `02:00:00`. `development/d633f0ba/PRECISION_EVIDENCE.json` retains this independently executed case. No event or envelope timestamp was mutated in that counterexample. The final candidate preserves the supplied evaluation instant in the existing event and artifact timestamp fields. Independent acceptance confirms that the +250 ms observation is admitted and persisted, while an event genuinely backdated by 50 ms still refuses. The strict availability boundary remains intact.

## Actual persistence evidence

The independent host helper executed the pinned `scripts/reconcile_cn_live.py::_write_parquet` in a review-owned temporary directory, with Python 3.14.7, pandas 3.0.5 and network connections disabled. Five native writes cover initial persistence, idempotent replay, a valid older legacy row, a legitimate later repeat, and fractional event time. Four hostile readable input files produce zero writer calls. All 12 resulting/before Parquet files are retained and their hashes were checked against the returned receipt.

Older valid noncolliding native history is carried without invented research provenance. An unbound row for the target session remains an explicit migration conflict. `HOST_EXECUTION_RECEIPT.json` retains the exact command, terminal exit-zero result, isolated path and transfer identity. It is evidence of this bounded test execution, not scheduled production operation.

## Preservation and replay

The original integration lab manifest `d755a012d80469c241a554252e61bee88e604eb445ce7ca03ec1e2eecfdbc8b6`, original seven-finding review manifest `78fcfa3c271d214c751a40220dc92e44cec67409eb49fbe7421b9c22a32698b6`, and their payloads were verified unchanged before and after acceptance. The draft timing challenge remains sealed at `b04d23d56ca26889aa99890f559385d52aa3fbc08403ed9603c27fae16579347`. Earlier development successes and the subsequent precision failure are retained separately; final acceptance does not relabel those versions.

From the repository root, the exact completed final invocation was:

```bash
python -B deliverable/research/cn_prophet_audit/census_20261009/deepening_20261009/reviews/integration_repair_review/accept_repair.py \
  --manifest deliverable/research/cn_prophet_audit/census_20261009/deepening_20261009/repairs/integration_contract/MANIFEST.json \
  --manifest-sha 371fd67d4ea85307e460772f8aa353609d176ff779f07811a0a42f8ea36c0309 \
  --parquet-receipt deliverable/research/cn_prophet_audit/census_20261009/deepening_20261009/reviews/integration_repair_review/PARQUET_RECEIPT.json
```

The script regenerates its fixture and result beside itself. Replay in a disposable copy preserving the relative study tree if the sealed package must remain physically untouched. The retained Parquet receipt verifies the already completed native host execution; a new native writer run uses `parquet_acceptance.py` with explicit subject, adapter, fixture, bundle and isolated output paths as retained in the host receipt.

## Implementation boundaries

Natural quote adjustment evidence is still unavailable under the pinned adapters. The synthetic basis/source contract is a test adapter, and cannot qualify natural provider data by renaming its origin or adding a Boolean. Exact source-byte custody, source availability, and genuine basis authority remain prerequisites for natural qualified events.

Implementation should retain the existing event spool/archive, pack, Asia-close consumer and daily ledger owners. It must demonstrate their actual scheduled producer-to-spool-to-consumer roundtrip, durable storage permissions and retention, replay/migration policy and observable refusals before claiming production readiness. Synthetic canonical bytes do not certify what was served to a user; source receipts do not certify market execution; ledger observations do not certify fills or returns. No production or vendor operation was performed by this review.
