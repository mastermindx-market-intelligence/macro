# Reproducing the entry/regime mechanism study

This is the existing Conditional Fusion program's research consumer, not a trading
system, new data writer or live Prophet ranking change. Start with
`ENTRY_REGIME_RESEARCH_PROGRAM_2026-11-14.md`, the immutable
`entry_regime_v1_spec.json`, and `ENTRY_REGIME_FIRST_PRINCIPLES_2026-11-14.md`.

## Source and custody

Use an admitted, isolated repository workspace at the exact research implementation
commit named by the result/verification receipt. Do not run from a moving shared
checkout. The specification pins price inputs and native engine semantics to
`6bbc4b0fc694c847077661ff5bf4c19ea41e4e81`; the research implementation adds the
adapter/consumer without changing those native owners. Original operation:
`entry-regime-confluence-20261113`, branch `sol/web-entry-regime-confluence-20261113`.

A later native-engine change is a different experiment. The verification command
refuses native source drift; it does not silently reinterpret the old trial with a
new gate. Preserve the original results and specification. New hypotheses, inputs,
thresholds, native semantics or inference budgets need a separately frozen protocol
under the existing research/trial owners, not edits to the old result after inspection.

Use the repository's existing qualified Python environment and dependencies. No new
credential, vendor, purchase, service, cron or worker pool is required. Numerical
parallelism is explicitly capped at two local workers; each runs at reduced priority.
Set BLAS/OpenMP to one thread to avoid nested oversubscription.

## 1. Qualification tests

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 -m pytest \
  tests/test_prophet_fusion_mechanisms.py \
  tests/test_prophet_fusion_input_readiness.py \
  tests/test_prophet_fusion_mechanism_verify.py \
  tests/test_prophet_fusion_timing_attribution.py -q
```

The tests use synthetic fixtures and limited native-prefix parity. Passing them is
engineering evidence, not proof of financial performance. Both the ordinary report
consumer and the independent arithmetic implementation are exercised, including
fault injection into returns, fill dates, contexts and source identities.

## 2. Outcome-blind data readiness

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
python3 -m scripts.prophet_fusion_input_readiness \
  --source-sha 6bbc4b0fc694c847077661ff5bf4c19ea41e4e81 \
  --out tmp/entry-regime-confluence-20261113/readiness
```

This selects registered input, availability and identity columns from pinned
candidate files. It does not decode outcomes or read the frozen W3/W2 race stores.
The output reports native-family coverage, date-label discrepancies, native regime
estimability and native chronological-fold readiness. Date checks are not actual
intraday receipt proof or a new admission policy. The existing C1 adoption is not
suspended by the full-family diagnostic.

## 3. Historical mechanism pilot

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
python3 -u -m scripts.prophet_fusion_mechanism_study run \
  --spec research/prophet_fusion/entry_regime_v1_spec.json \
  --out tmp/entry-regime-confluence-20261113/pilot \
  --workers 2
```

The CLI supports separate `qualify`, `collect`, and `report` phases. An existing
matching input/observation cache is reused only after spec, adapter and byte-hash
checks. A cache conflict is a refusal, not a reason to delete evidence and rerun.
An interruption can leave original workers active: reconcile the original process
and cache before any continuation. Do not start a second runner into the same output.

The configured study is deliberately not promotion eligible: a fixed eleven-name
survivor sample, reconstructed vendor history, unaudited adjustment basis, and a
technical-core counterfactual that omits the live context waiver and event latch.
The primary outcome is equal-decision-date mean 21-session net excess versus the
same-window SPY return. A positive-net-return rate is not clean-liftoff accuracy,
stop survival or portfolio CAGR. The 63-session result is descriptive secondary
analysis; it cannot replace an unsuccessful primary result.

## 4. Independent arithmetic and source readback

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
python3 -m scripts.prophet_fusion_mechanism_verify \
  --spec research/prophet_fusion/entry_regime_v1_spec.json \
  --input tmp/entry-regime-confluence-20261113/pilot
```

This separately recomputes each fill, terminal price ratio, benchmark return,
close-basis adverse/favorable excursion, every cost sensitivity, market context,
arm date-weighted summary and contrast point estimate. It checks native source
identity, price Git blobs and SHA256s, observation digests and the report's code
binding. It does not call the original outcome/return/summary builder. It does not
re-estimate bootstrap confidence coverage or constitute a distinct human/model
reviewer. Missing or inconsistent data fails; it never repairs the report silently.

## 5. Read the complete result, including negatives

The operation-local outputs are `input_manifest.json`, per-name observation receipts,
`collection_receipt.json`, `graded_research_events.parquet`, `report.json`,
`report.md`, and `verification.json`. Only aggregate source-linked research evidence
is committed; raw private research caches stay ignored. Output is refused under
runtime `data/` or public `site/` by the existing arena fence.

Before drawing a conclusion, inspect the primary contrast count and adjusted
intervals, independent dates/episodes, retention and rejected-winner metrics,
chronological halves, native/provisional strata and cost sensitivity. Compare
absolute return, benchmark excess and risk attribution rather than selecting the
most flattering metric. A same-calendar benchmark controls some market drift, not
all sector/beta/exposure risk. The beta residual is diagnostic, not a tradable
neutralized portfolio. The result's population/vintage caveats cannot be cured by
more bootstrap replications.

## Promotion and product boundaries

A descriptive survivor-panel result cannot modify live ranking, gating, sizing or
orders. A credible candidate must enter the existing qualified arena with genuinely
point-in-time sources, estimable interactions, honest trials, chronological tests,
name/era robustness and prospective shadow proof. Stage-2 win-gating, the broad
family-reliability grid and other closed constructions are not reopened by a
pleasant-looking row in this report. No public endpoint or production restart is
required merely to read this research evidence.

## Auxiliary timing-attribution control

After a primary report has passed its bound arithmetic verification:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
python3 -m scripts.prophet_fusion_timing_attribution \
  --input tmp/entry-regime-confluence-20261113/pilot
```

This separately saved diagnostic compares each event with the same asset/month's
common-qualified hypothetical entry dates. It neither changes nor replaces the
primary report, and publishes no significance or promotion. Its protocol was added
after the primary freeze and is labeled auxiliary. It helps distinguish timing
from merely owning favorable assets in favorable periods; it is not a complete
portfolio risk or exposure attribution.
