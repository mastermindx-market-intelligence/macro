# V0: Capital Structure serving, measured on the real corpus

Status: measurement record (masterplan §13 task V0). Written by the Capital Structure V2 Meta-CEO seat, 2026-11-02.

The masterplan proposes one V0 target: evaluation p95 ≤ 2 s at 10 concurrent readers. That target is a **proposal, not an acceptance criterion**. This note records what was measured against it, how it was measured, and what remains unmeasured. It does not accept V0.

## 1. What was wrong before the fix

Each `POST /issuers/{id}/scenarios/evaluate` request on the real corpus took 17–19 s. Profiling put all of that time in `_load_inputs`.

A capacity-inputs bundle that passed validation but pointed at another state generation was never cached. The cache was only written after the binding check succeeded. So every request re-ran full-bundle validation, and it did so while holding `_LOCK`, which also blocks the state, registration and coverage routes.

The real-corpus bench hid this in two ways:

- It rebuilt the state over its copy but never rebuilt the capacity inputs, so evaluate only ever measured the 503 refusal.
- It reused the fixture scenario, which is dated for the fixture's cutoff, so even bound inputs were refused with 422 `scenario.as_of must equal the state cutoff`.

PR #10548 fixes all three:

- Validity is cached by exact file stat.
- Binding is re-checked on every call.
- The bench builds the inputs after the state, and re-dates its scenario to the evaluated issuer's cutoff.

## 2. Measurement

One run on the Mac Studio, 2026-11-02, over a copy of the real corpus: 3258 issuers, state generation `state_bundle:cs:220d74bd583f5e5efa423730d181b08b`. The client is in-process (see §3).

| Step | Result |
| --- | --- |
| Build the state and capacity inputs over the copy | 168.5 s (offline; not on the request path) |
| First `state` request (cold state load) | 200 in 19.76 s |
| First `registration` and `coverage` requests | 200, under 10 ms each |
| First `evaluate` request (cold inputs validation) | 409 in 4.12 s |
| Next five `evaluate` requests | 409, 3–4 ms each |

A warm wave of 10 readers × 8 requests (80 requests, 20 per route):

| Route | Status | p50 | p95 | max |
| --- | --- | --- | --- | --- |
| state | 200 × 20 | 28 ms | 138 ms | 140 ms |
| registration | 200 × 20 | 29 ms | 135 ms | 140 ms |
| coverage | 200 × 20 | 27 ms | 134 ms | 138 ms |
| evaluate | 409 × 20 | 19 ms | 117 ms | 127 ms |

Every response from the state, registration and coverage routes echoed the same generation id.

**The evaluate figures time a typed refusal, not an evaluation.** Every real-corpus evaluate returns 409 `scenario_inputs_unavailable`, because no served issuer has the capacity inputs an evaluation needs. A census of the built `capacity_inputs.json`:

| Input family | Supported | Partial | Unavailable |
| --- | --- | --- | --- |
| financials | 0 | 0 | 3258 |
| instruments | 0 | 0 | 3258 |
| share_basis | 0 | 0 | 3258 |
| commitments | 0 | 1452 | 1806 |

The file's `capabilities_proven` is empty. **0 of 3258 issuers are evaluable.** The refusal names each missing family and its reason code (for example `candidate_terms_not_materialized` and `share_observations_not_admitted`). This is the correct product answer: the route says what is missing instead of producing a number.

So, against the V0 proposal:

- **Evaluation p95 at 10 readers: not measured.** No real issuer can be evaluated yet. The 117 ms p95 shows that the warm refusal path is cheap, which is all it shows.
- **Fixture evaluation.** The fixture world, which is evaluable by construction, is exercised by `tests/test_capital_structure_v0_serving.py` for correctness. Its timings are not evidence about the real corpus.

The bench now records this in the report. `evaluate_outcome` states whether evaluate answered 200 or the typed inputs refusal, with the components, before any wave is timed. The bench also picks an evaluable issuer whenever the corpus has one. It stops with a named error on any other refusal (a 422, a 503 or another 409), so a misdated or unbound request can no longer be timed silently.

Measuring evaluation p95 needs the input families filled: candidate instrument terms (U1C fee terms and the I1b/I2b extractors), admitted share observations, and admitted financials (X0b). When the census shows at least one evaluable issuer, rerun the bench. It will select that issuer and time real evaluations.

## 3. Not measured, and residual costs

- **Cold start.** The first request after a publish pays for one state load and one inputs validation, both under `_LOCK`. The measured costs are in §2. Concurrent requests queue behind that load.
- **Invalid files.** A contract-invalid inputs file is revalidated on every request. Failures are deliberately never cached, so a bad publish costs one validation per request until it is replaced.
- **In-process client.** The bench drives the router through an in-process client on the Mac Studio. It does not measure the production server, its worker count, TLS or the network path. Production timing is a separate proof.
- **One evaluated issuer.** Each run evaluates a single issuer. The cost of an evaluation depends on how many facts and routes that issuer has.
- **No real evaluation yet.** As §2 shows, the real corpus has no evaluable issuer, so the evaluation path itself has never been timed on real data. The first real evaluable issuer may cost more than the fixture suggests.

## 4. Rerunning

```bash
PYTHONPATH=. python3.12 scripts/bench_capital_structure_serving.py --data-root <data/capital_structure> --out <report.json>
```

The bench copies the data root, rebuilds the state and inputs over the copy, and never writes to the source. If the inputs build refuses, it stops with a named error rather than measuring a corpus that can only refuse.
