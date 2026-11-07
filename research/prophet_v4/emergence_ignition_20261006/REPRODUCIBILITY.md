# Reproduction, provenance and output dictionary

## What was executed

The three parallel research lanes and the root operational lane read immutable Git objects and wrote isolated research outputs. They did not execute collectors, ranking, plan, alert, entry, or publication producers. The source estate was inspected at fixed commits rather than using whichever version happened to be in a working tree.

The evidence census completed its final run with exit 0 and 764 immutable source identities. Its expected result digest is `005aed6029bb17b14449834fee1ada5ac766ceb54e93db9b9b9891d9b422e6af`. The emergence extraction recovered 394 variants and 30 v3 dates; the final statistical run used seed 20261006 and 10,000 date-cluster bootstrap draws per comparison. The ignition reproduction verified the 327/143/5 denominator, fixed H5 cohort across later horizons, same-date treated coverage, and zero tier/flag/entry drift across all 134 H5/H10 and 58 H5/H21 pairs. Its source manifest contains 592 immutable objects. The raw-board companion directly verified seven selected original board blobs. The operational census completed over 27 receipt objects and exact inherited alert/plan checkpoints.

A separate bounded reviewer independently reproduced the ignition issuer-weighted gap +4.24798 pp, date-weighted gap +4.73981 pp and the four nearest-control identities/distances, and checked incremental return algebra. A source reviewer checked the R6 contract and identified corrections to missing-B1 enrollment, evidence-class admission and cross-block disclosure dependence; the final handoff incorporates them. These are research reviews, not production acceptance or an external model-validation audit.

The local integration checks parse every JSON with non-finite values rejected, parse all Python scripts, check required reports and relative links, and verify package digests. The emergence focused check covers missing observations, right censoring, provisional exclusion and missing eligibility. Run the package verifier from any location:

```bash
python3 scripts/verify_research_package.py
```

## Runtime and source prerequisites

Use Python 3 with pandas, NumPy, SciPy and a pandas Parquet reader such as pyarrow. The source reproduction runtime was Python 3.12.4, pandas 3.0.3, NumPy 2.4.6, SciPy 1.18.0 and pyarrow 24.0.0; `results/runtime_versions.json` records the observed source and integration runtimes. The emergence statistics and operational census use the Python standard library; the source/price studies need the listed data libraries. Install dependencies in an isolated environment if necessary. No production environment installation is required.

The source object repository must contain:

* Macro main pin `731a23fb64b9f6f1a321c77618f927f1a58d2d41` and the relevant board history back through August 2026;
* parent PR head `770918cb266b5d884978e31d61670b4efd789eaf` with frozen grade and price objects;
* the exact earlier operational checkpoints and selected board commits named in the result manifests.

An incomplete shallow clone cannot reproduce the history extraction. Supply a separately obtained, authorized source-object repository with the needed ancestry. Do not deepen, reset, switch or otherwise mutate a shared production checkout to reproduce this research. In a promisor repository Git may fetch missing objects according to its existing configuration; with all objects present the calculations require no market-data network calls.

Set `SOURCE_REPO` to that read-only object repository and `RESEARCH_RUN` to a fresh directory outside it. The commands below are run from this research directory. Do not point outputs at production directories. Some scripts refuse an existing result; use a new run directory instead of overwriting a prior experiment.

```bash
SOURCE_REPO=/absolute/path/to/isolated/macro-source-objects
RESEARCH_RUN=/absolute/path/to/fresh/prophet-ei-reproduction
mkdir -p "$RESEARCH_RUN"
```

## Reproduction order

### 1. Evidence-family source inventory

```bash
python3 scripts/census_evidence_sources.py \
  --repo "$SOURCE_REPO" \
  --ref 731a23fb64b9f6f1a321c77618f927f1a58d2d41 \
  --out "$RESEARCH_RUN/evidence_source_census.json"
```

The family readiness matrix and source-owner recommendations are authored judgments grounded in this output and cited code/contracts. The script is a census, not an automatic source-admission or independence classifier. Its selected-case UTC-date filters are diagnostic bounds, not proof of a market decision-cut source join. Generic clock ranges preserve raw lexical endpoints; critical selected clocks are parsed separately.

### 2. Board history and emergence outcomes

```bash
python3 scripts/extract_boards.py \
  --repo "$SOURCE_REPO" \
  --pin 731a23fb64b9f6f1a321c77618f927f1a58d2d41 \
  --out "$RESEARCH_RUN/boards"

python3 scripts/analyse_emergence.py --self-test

python3 scripts/analyse_emergence.py \
  --latest "$RESEARCH_RUN/boards/boards_latest.json" \
  --first "$RESEARCH_RUN/boards/boards_first.json" \
  --out "$RESEARCH_RUN/emergence"

python3 scripts/audit_b1_rp1_coverage.py \
  --repo "$SOURCE_REPO" \
  --pin 731a23fb64b9f6f1a321c77618f927f1a58d2d41 \
  --boards "$RESEARCH_RUN/boards/boards_latest.json" \
  --baselines "$RESEARCH_RUN/emergence/extended_window_latest_exposed_baselines.csv" \
  --out "$RESEARCH_RUN/emergence"
```

Expected full-array digests: latest `599a96d4ba23e2aabe81caa9fb434fabd2652d700d0c48093ffee12c3478d889`; first `060d56804c96601ac8f86f4f5c826105a2509c7e584673b5b0b4dbddc3240289`. These large intermediate arrays are intentionally omitted from the delivered package. The Git source manifest is preserved.

### 3. Ignition, covariates and source-clock sensitivity

```bash
python3 scripts/reproduce_ignition_study.py \
  --repo "$SOURCE_REPO" \
  --out "$RESEARCH_RUN/ignition" \
  --control-keys results/price_controls_2026-10-06.csv

python3 scripts/reconcile_ignition_board_clocks.py \
  --repo "$SOURCE_REPO" \
  --history-repo "$SOURCE_REPO" \
  --boards-first "$RESEARCH_RUN/boards/boards_first.json" \
  --boards-latest "$RESEARCH_RUN/boards/boards_latest.json" \
  --out "$RESEARCH_RUN/ignition-clocks"
```

The published price-control CSV supplies **only the fixed `(as_of,ticker)` key inventory** to `--control-keys`; its computed values are ignored and recomputed from pinned source prices. Omitting this argument still reproduces the ignition cohort but does not reproduce the full supplemental emergence covariate inventory. The frozen ledger SHA-256 is `61bb8cc6ff0f1cfd14f33ba50fc5ce17db4c93e800f74e307c70c5606ae4f9d7`.

The code keeps the first H5 ticker/date fixed across H10/H21. The broad pooled retrospective covariate scaling is a disclosed sensitivity, not a live as-of matching policy. The historical next-close-plus-H convention remains distinct from the prospective decision-cut endpoint. Missing benchmark opens do not become a guessed next-open excess return. Full prereg-shaped event keys remain observation-key diagnostics, because changing observed date can split the same technical event.

### 4. Supplemental emergence RS/liquidity controls and publication subset

```bash
python3 scripts/emergence_price_sensitivity.py \
  --boards "$RESEARCH_RUN/boards/boards_latest.json" \
  --baselines "$RESEARCH_RUN/emergence/extended_window_latest_exposed_baselines.csv" \
  --controls "$RESEARCH_RUN/emergence/extended_window_latest_control_baselines.csv" \
  --price-controls "$RESEARCH_RUN/ignition/price_controls_2026-10-06.csv" \
  --out "$RESEARCH_RUN/emergence"

python3 scripts/compact_emergence_outputs.py \
  --source "$RESEARCH_RUN/emergence" \
  --boards-source "$RESEARCH_RUN/boards" \
  --out "$RESEARCH_RUN/emergence-publication"
```

The compact output removes repeated record arrays from summary JSON and retains every exposed baseline/outcome plus primary H12 control/pair evidence. It does not change the estimand or replace missing outcomes. Files that record local input paths can differ textually when reproduced elsewhere; compare source digests and numerical/state results rather than interpreting a changed temporary directory as a scientific discrepancy.

### 5. Operational clocks

```bash
python3 scripts/lead_time_census.py \
  --repo "$SOURCE_REPO" \
  --ref 731a23fb64b9f6f1a321c77618f927f1a58d2d41 \
  --output "$RESEARCH_RUN/operational"

python3 scripts/publication_price_context.py \
  --repo "$SOURCE_REPO" \
  --expected results/NVDA_PUBLICATION_PRICE_CONTEXT_2026-10-06.json \
  --out "$RESEARCH_RUN/operational/NVDA_PUBLICATION_PRICE_CONTEXT_2026-10-06.json"
```

The clock script discloses the inherited alert timestamp and exact checkpoint commits. It verifies source objects and commit times without restarting the full NVDA forensic. The bounded publication-price script reads the final plan's exact source levels, its inherited Git publication commit and the current pinned NVDA OHLC object. It reconstructs all six rows and checks semantic equality with the published result. It is a retained-price diagnostic, not an execution simulator.

## Output dictionary

| Output family | Meaning / limit |
| --- | --- |
| `evidence_family_matrix.*` | Authored source owner, direction, clock, age, independence, coverage and conditional eligibility judgments; not a fitted score |
| `evidence_source_census.json` | Current pinned source inventory, selected native filings and 764 source identities; historical event dates do not prove historical capture |
| `parent_window_latest_*` | Parent through-Sep-25 discovery reconstruction, with raw and guarded technical endpoints |
| `extended_window_latest_*` | Extended through-Oct-5 discovery using latest retained daily versions |
| `extended_window_first_*` | Same broad extension rebuilt from first preserved daily versions; population and fields can both change |
| `observed_capture_*` | Preserved qualifying state divided by the explicitly defined mature/index population; not imputed population conversion risk |
| `true_conversion_*_bounds` | Partial-identification ranges allowing unobserved trajectories either outcome; not ordinary sampling CIs |
| `*_bootstrap_*` | Seeded empirical date-block uncertainty of observed contrasts; tiny/degenerate results are labeled and do not establish precise nulls |
| `b1_*`, `b03_*` | Exact retrospective owner relations and source coverage; unknown does not imply not-yet-anchored or original-time availability |
| `IGNITION_RESULTS_*`, `first_t2_*` | Frozen-ledger diagnostic and separate retained-price sensitivity, with first-ticker population held fixed |
| `IGNITION_BOARD_CLOCKS_*`, `raw_board_clock_covariates_*` | First/latest joins, actual C1-score control, source clocks and key sensitivity; no new canonical episode |
| `SOURCE_MANIFEST_*` | 592 exact ignition source-object identities |
| `operational_*` | Receipt inventory, selected plan origins, source hashes and interval decomposition; missing reader/fill clocks remain null |
| `decision_summary.json` | Curated D1–D8 and principal findings with explicit research authority limits |
| `ARTIFACTS_SHA256.json` | Exact package-file bytes; distinct from source-data digests and Git publication identity |

No file in this package is a production telemetry store, trading plan, score or runtime contract. Future implementers must consume the existing owner contracts and close their stated source/identity/acceptance gates.
