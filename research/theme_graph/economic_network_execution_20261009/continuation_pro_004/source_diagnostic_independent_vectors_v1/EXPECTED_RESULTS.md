# Independent WP02 kernel adversarial vectors

## Scope and independence

The semantic expectations were derived and frozen before reading any implementation source. This package prepares review inputs; it does not report execution or approval of the kernel. The builder supplied the planned byte interface:

```python
diagnose(request_bytes: bytes, *, policy_bytes: bytes, adoption_bytes: bytes) -> dict
canonical_bytes(result) -> bytes
```

The exact policy and adoption bytes must remain bound to SHA-256 `d41422d76219b1c5d3a3c9cbb19a1bc3124433031200b09499033bd4dc30d522` and `645a20a39842d9c5a03b4ff39a37280d1aa02c32ef545c061d0aa959f06e0016`. Changing whitespace in one of those files is a different raw-byte binding, even when its parsed JSON is equal.

The first requested API schema is `research.gmi.wp02.source_diagnostic_request/v1`, with required `sources`, `records`, `history`, `fx`, `counts`, `stress_cases` and `claims`. Mode defaults to `REAL_SOURCE`; the only alternative is `SYNTHETIC_MODEL`. The complete draft interface is now pinned in `DRAFT_INPUT_CONTRACT.md`, 17,726 bytes, SHA-256 `940da98f5edc9fab650d04ad69c79dc761e2b4a9559c0419d2dbf434a2cd9bbe`. The author supplied an artificial seed request; its exact 385,563 original bytes are retained in `DRAFT_BASELINE.json.gz`, with uncompressed SHA-256 `b9272931831e1cce8834911b0ec1e321cd2de7dc8c622b01038bc8242fc605cf`. These are draft interface/data snapshots, not implementation-source review or execution proof.

All issuer labels, source labels, values, histories and graphs in these vectors are artificial. A complete model input does not establish a real population, source rights or historical coverage. The earlier 729-matrix check was not rerun. No application, native, Git, provider or source-acquisition effect occurred.

## Main selection challenge: complete marginals, impossible joint INT quota

`HALL_18_CAPACITY_VECTOR.json` specifies all 18 activity/size cells. UK has eight equal-cap semiconductor/cloud issuers, all in that pool's L band, and five explicitly empty artificial activity pools. Japan and EU each have four distinct-cap issuers in every activity, yielding 2L/1M/1S per pool. The four non-INT strata use normal four-issuer pools. The full artificial frame has 42 pools and 152 records.

Every country has at least eight candidates, and every aggregate activity/size cell has enough candidates for its demand. Nevertheless, UK can fill only the semiconductor/cloud L cell's two slots. The source-side cut containing source, UK and that one cell has capacity:

`8 (source→JP) + 8 (source→EU) + 2 (semiconductor/cloud L→sink) = 18`.

The file also gives an explicit feasible 18-unit flow respecting every edge and demand. The matching upper and lower bounds prove artificial maxflow18, without running another solver. Expected outcome: a typed INT infeasibility, a valid deficient cut and no completed 120-issuer model cohort. Returning120 based on marginals, moving UK issuers to other jurisdictions, or splitting equal caps into artificial bands fails this challenge.

The complete positive control uses four distinct-cap issuers in every one of the 42 pools, for 168 artificial records. Its expected modeled selection satisfies all120/24/4/2L1M1S and INT8/8/8 constraints. Any real result fields and authority remain held. Real difficult-case requirements cannot be satisfied by these artificial fixtures.

## Compact challenges and falsifiers

| Cases | Independent input | Required outcome |
|---|---|---|
| V03–V04: ties | One non-INT pool `[400m,300m,300m,100m]`, then four identical400m values | L3/M0/S1 or L4/M0/S0, with truthful missing quota cells; no hash-based splitting of equal values |
| V05: identity | Reuse one exact canonical model ID in two pool positions | Duplicate issuer/identity refusal before aggregation; no overwrite or double count |
| V06–V07: history | A removal and an admission keep count2 but change `{a,b}` to `{b,c}`; repeat in reverse and with an incorrect after-state | Exact set/state mismatch holds history; count equality is insufficient |
| V08–V10: assertions | Same-date190m/210m competing counts; older measurement published later; correcting relation public afterK | No publication-recency winner; latest applicable measurement is distinct from revision; postK evidence cannot remove or rewrite the K-vintage fact |
| V11: persistent states | Independent ratio states1 and2 overlap atD without proved transition | Conflict or explicit unsupported-state/basis hold; newest start date alone cannot choose a state |
| V12: signed/zero action |100m shares at20 with −10m,0,+10m deltas; then remove zero's no-change evidence | Modeled caps1.8b,2.0b,2.2b when supported; retain sign and explicit zero-evidence requirement |
| V13: split basis |100m shares, raw price10 before a2-for-1 split and doubled D-equivalent shares | Correct compatible-unit cap1b or explicit basis hold; no unbridged2b |
| V14: incomplete class | Priced classA plus unpriced classB without proved proxy | Full issuer cap null; no partial-class positive cap |
| V15–V16: authority | Forged approval claims in real mode; identical assertions with a synthetic label | Real source authority/rights/history always held; caps, quantiles, population and cohort remain null; modeled results do not authenticate their inputs |
| V17–V18: parser/bounds | Duplicate JSON keys, invalid UTF-8, nonfinite JSON, wrong argument types, boundary budgets, bool/noninteger counts and invalid numeric roles | Stable typed refusal/hold, correct resource and count accounting; no permissive parse or traceback/source disclosure |
| V19: policy binding | Same parsed policy with altered raw bytes; extra override or arbitrary supplied policy | Exact binding refusal; no self-adoption of untrusted policy |

The frozen `INDEPENDENT_EXPECTATIONS.json` records all19 cases and prohibited outcomes in detail. `HISTORY_SET_VECTORS.json` and `NUMERIC_VECTORS.json` provide small exact inputs. Their dates and membership labels are model coordinates, not observations of an exchange cutoff or actual issuer event.

## Scope holds are valid outcomes where support is absent

The tests must respect the first kernel's declared scope. Persistent-state reconciliation, price-factor bridging or class-rights proxy verification must not be invented just to make an artificial example positive. If the closed first contract cannot represent the necessary evidence or mechanism, it must return an explicit typed unsupported/basis/history hold and expose the scope limit. A silent winner, partial cap or fabricated proof is not a permissible shortcut.

The later frozen-code review will distinguish an implemented mechanism with a wrong result from a clearly declared unsupported mechanism. This package does not request an unrelated generic source verifier.

## Real-source and parser proof obligations

An otherwise valid `REAL_SOURCE` request, including the default when mode is omitted, must remain `STRUCTURAL_ONLY` and `NOT_READY`. Authority/rights/history receipt flags cannot change that behavior. A changed mode can permit explicitly artificial arithmetic, but cannot authenticate the content or classify it as truthful. Unknown rights must stay unverified, not become a proved lack of a license.

Byte-budget checks should isolate the advertised boundary with a known-valid request padded by legal trailing JSON whitespace; maximum+1 then changes only size. A malformed document cannot supply an honest parsed record count, so unavailable counts must remain unknown rather than becoming a claim that zero records were requested. Counts from parsed arrays must not be overwritten by self-declared totals. Repeated calls and a fresh process should produce the same canonical result for the same bytes and options, without wall-clock truth selection.

## Exact wire material and bounded remaining recipes

`WIRE_INDEX.json` binds **41 exact compressed request variants**, totaling 474,729 compressed bytes. Each entry contains its uncompressed request length/SHA, compressed length/SHA, intended semantic fault and expected outcome. `ENCODE_VECTORS.py` reproduces those requests from the pinned artificial seed without importing or invoking the kernel. These are fixture transformations, not another selector implementation.

The independent positive control changes all share quantities to100million and updates their exact supplied-token spans; prices4/3/2/1 then realize the first-derived400m/300m/200m/100m pool design. The Hall case rebuilds the membership arrays, their exact supplied source bytes and all affected declared counts for152 records. History-error cases likewise rebind the supplied arrays and offsetting admission/removal counts, so the intended fault is reconstruction rather than a stale payload digest. Every authority claim remains unverified.

| Wire control | Uncompressed bytes | SHA-256 |
|---|---:|---|
| V01 complete artificial model | 386,280 | `7fcaae7be2dd0668ce4819c6a1bde38dcc0d347ac03aaec10d5a246380b8bee1` |
| V02 full INT Hall deficiency | 388,044 | `c3ca743b616bcb0515c00aaefd0b03b4d64a54f2b7a61fa0729d0581224b6915` |
| V18 request at2MiB | 2,097,152 | `8ec2d145f4bf3d811752ad103d6486941081a98fd0cffb91dcede4110164b6cf` |
| V18 request at2MiB+1 | 2,097,153 | `40f8b3ea973e3c43f4818e690dfcfc818042307d1c43ba1595c787bd1d6ff280` |

The two request-size controls differ only by legal trailing JSON whitespace. Source-content boundary controls similarly use exact256KiB and256KiB+1 source bodies while keeping the entire request below2MiB. The parser vectors include top-level and nested duplicate keys, invalid UTF-8, an unpaired escaped surrogate, NaN/Infinity constants, boolean/negative/float/13-digit cardinalities, invalid numeric roles and17 otherwise equivalent assertions against a16-assertion limit. Expected domain errors must be checked for the relevant reason, not counted as a success merely because some unrelated later evidence check refuses.

The draft contract recognizes `ZERO_OR_CEASED` and richer class kinds but holds them as `RICHER_CLASS_RIGHTS_OR_CEASED_FACT_NOT_IMPLEMENTED`; that is the intended V14 scope result. It requires POINT bundles at the public shares/price/FX paths. V11 therefore tests the public POINT-required/persistent-state hold. It does not test a private persistent helper or claim persistent-overlap semantics are reachable through the public byte API. V10 forbids any post-K replacement; its precise prior-value-versus-typed-hold behavior must be reconciled with the final declared implementation without treating a210m post-K correction as acceptable.

`WIRE_RECIPES.json` keeps six additional invocation or boundary cases explicit: wrong nonbytes argument, changed raw policy bytes, changed raw adoption bytes, a513-record case, exact depth/token boundaries and output-budget reachability. The first three are simple argument transformations of a bound request. The last three are **not encoded or executed** here. Exact depth/token counting requires the final parser convention, and no supported input reaching8MiB output has been established. This preparation does not turn those limits into claimed coverage.

All outputs, including malformed-input results, must retain `status=STRUCTURAL_ONLY`, `readiness=NOT_READY`, `admission=NOT_ADMITTED`, null real inputs and false/unverified real authority. Gzip is only transport for the review fixtures: a later harness verifies both bindings, decompresses the known bounded request and passes the resulting exact bytes to `diagnose` with the fixed policy/adoption inputs. No filesystem path or hash is an authority receipt.

## Observed preparation, not kernel validation

The fixture encoder completed with exit0 and empty stderr. All41 compressed and uncompressed wire bindings were checked. A separate bounded inspection verified the positive control's168 records, Hall's152 records and exact UK L8/JP–EU2L1M1S realization, plus source-byte/history-array consistency in the four principal model/history controls. No complete kernel-schema validator, actual API or selector was run. The exact18-flow/cut witness remains the independent mathematical oracle; no729-matrix rerun occurred.

The original `INDEPENDENT_EXPECTATIONS.json` remains byte-exact with its historical pre-interface status. `INTERFACE_SNAPSHOT.json` and this later wire index record the subsequent mapping. Final frozen-code review must bind its actual implementation and reconcile any interface revision before using these vectors as execution evidence. This package's state is **READY_FOR_FROZEN_CODE_REVIEW**, with the recipe-only limits above, and its actual kernel-call count is zero.

STOP.
