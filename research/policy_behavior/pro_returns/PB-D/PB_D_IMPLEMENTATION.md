# PB-D event quality implementation

Research design: [PR #8574](https://github.com/mastermindx-market-intelligence/macro/pull/8574), immutable commit `df2091915159dab94f316718caa9b2662098eae4`. Implementation carrier: [PR #8576](https://github.com/mastermindx-market-intelligence/macro/pull/8576). The cumulative checkpoint and verification receipt in this directory distinguish executed local verification from CI and release status.

**To run the example on M2 Studio, start with [the operator quickstart](PB_D_OPERATOR_QUICKSTART.md).** It names the computer and macOS Terminal app, supplies one complete command, and explains the output. No repository selection, `cd`, Python activation, or installation is required in the prepared M2 environment.

## What this implements

PB-D can now be replayed as an offline research pipeline: reviewed source evidence becomes a quality receipt; published-board inputs become immutable first-T2 observations and exact matched pairs; separately supplied outcomes become the preregistered primary analysis and fixed secondary family. The source and research adapters perform no enrollment, scheduling, trading or signal changes. The integrated `run` command always returns `FROZEN_DESIGN_NOT_ENROLLED`; the other commands return their own unenrolled receipt schemas.

| Component | Interface | Responsibility |
|---|---|---|
| Company Intelligence quality | `engine.company_intelligence.pb_d_quality.build_quality_receipt` | Existing document/span validation, review and coverage clocks, focal evidence, nine tri-state labels and conservative issuer Q |
| First-T2 and matching | `engine.pb_d_cohort.freeze_cohort` | Consume the first emitted T2 before exposure exclusions, retain missingness, freeze exact matched pairs and session clocks |
| Corrections and omissions | `append_correction`, `rematch_omission` in the cohort module | Preserve the original manifest; append correction receipts; derive full eligible-pool rematches |
| Evaluation | `engine.pb_d_evaluation.evaluate_pb_d` | Equal-date H5 increments, the fixed calendar-block bootstrap, inferential gates, secondary family and descriptive sensitivity reports |
| OHLC paths | `engine.pb_d_evaluation.compute_ohlc_path` | Calendar-positioned ATR20/B20, post-entry excursions, drawdown, clean liftoff and failed breakout labels |
| Executable consumer | `.venv/bin/python -m scripts.query_pb_d_event_quality` | Validate JSON, run quality → cohort → outcomes in that order, and write an immutable report |

The existing Company Intelligence document/event identities and Evidence Foundation contracts remain the owners. The adapter does not create a competing event store, independence ontology or registration ledger. Its hash receipts establish byte integrity and replay identity; they do not authenticate the producer, prove a reviewer was human, or prove that an asserted clock was independently captured.

## Run the supplied example

This code belongs to `mastermindx-market-intelligence/macro`. “Macro checkout” means a local folder containing this repository's `engine/`, `scripts/`, and `tests/` directories. The GitHub website stores the code; macOS Terminal on M2 Studio runs it. See the operator quickstart above for the prepared machine's complete absolute command.

For developers already inside a Macro checkout with its `.venv` Python 3.12 environment:

```bash
bash scripts/run_pb_d_example.sh
```

The launcher derives its own checkout, checks the exact Python interpreter, creates a fresh output directory, invokes the existing consumer, and prints a short summary derived from the saved report. An absolute launcher path works from any working directory. Use `--python` only to select an explicit absolute Python 3.12 executable; it never falls back to a bare `python` or installs dependencies. `--output-dir` selects an existing parent folder; each run still gets a new child folder. Setup and troubleshooting are in the operator quickstart.

For direct machine-consumer calls, choose a new output pathname on every run. The consumer refuses to overwrite an existing file or replace its input; omitting `--output` prints JSON to stdout. Invalid JSON, unsupported fields, contradictory supplied outcome clocks and attempted activation return exit code 2 with a `REFUSED` reason. Direct-file calls are also supported when both the Python 3.12 executable and script use absolute paths. The entry script locates its own checkout before importing repository code.

The example is wholly fictional. It contains one Q1 issuer, two Q0 issuers, one unknown-exposure issuer, one original matched pair and an unused control. Its weekday schedule is explicitly labeled **not a real exchange calendar**. Its board, source bytes, reviewer receipts, prices, future outcomes and validation references are synthetic. The numeric primary increment is +4 percentage points; this is a known-number integration check, not a market observation or evidence for the investment hypothesis. Coverage is 3/4, and the study is not enrolled.

When the matched control is omitted, the other original eligible control can enter the rematched sensitivity. Removing a control's outcome instead drops the original pair from the primary estimate without rematching. Those two cases deliberately exercise different rules.

The four stages are also available independently:

```bash
.venv/bin/python -m scripts.query_pb_d_event_quality quality --input reviewed-evidence.json
.venv/bin/python -m scripts.query_pb_d_event_quality freeze --input cohort-input.json
.venv/bin/python -m scripts.query_pb_d_event_quality evaluate --input frozen-cohort-and-outcomes.json
.venv/bin/python -m scripts.query_pb_d_event_quality run --input complete-research-packet.json
```

`quality` accepts the keyword arguments to `build_quality_receipt`. `freeze` accepts the cohort module's documented payload. `evaluate` accepts `cohort` (the hash envelope), `outcomes` (an array) and optional `dataset_kind`. `run` accepts exactly `schema: pb_d_research_input.v1`, `dataset_kind`, `cohort`, `quality_requests` keyed by observation ID, and `outcomes`. The consumer accepts only `SYNTHETIC_DRY_RUN` and `OFFLINE_OBSERVATION`.

## Evidence, clocks and unknowns

The primary exposure is known only after coverage and every candidate's primary materiality/root state have been resolved. A positive candidate cannot override another unresolved primary candidate. Missing evidence is `UNKNOWN`, rather than a negative label. An omitted or unknown secondary label, including `EXPECTATION_CHANGE`, affects that label and does not independently invalidate resolved primary fields. Extra structured label or outcome fields are refused.

Source documents use the existing `SourceDocument` payload, and cited spans use `SourceSpan`. The first adapter verifies exact UTF-8 body spans at segment zero. A supplied segment cannot borrow another body's digest. Unsupported extraction/segmentation stays unknown. Document/body/segment maps may contain only explicitly referenced objects; arbitrary unused future context is rejected. Free prose cannot be made outcome-blind by a schema: actual reviewer access and provenance remain external facts.

Materiality is tied to a focal proposition and a specified mechanism, direction, significance rationale, alternative explanation and falsifier. Two publishers are insufficient for E2. Reidentified copies of a claim, the same originating document, identical source bodies or shared evidentiary dependencies cannot certify independent originating roots. Incidental issuer mentions and undated public clocks do not establish a qualifying new event.

Freshness is `(cut[d−3], cut[d]]` over the supplied exchange schedule. Both genuinely new public information and its observation must be usable by the cut. Late ingestion of an old fact does not make it fresh. Window-scoped materiality, attention-only and no-material-event labels are kept consistent. The displayed anchor is tied to the qualifying materiality and root evidence, not a later incidental item.

Two independent, outcome-blind reviewer receipts must bind the exact packet digest and be complete by the cut. An adjudicator must be a distinct third reviewer, act after both reviews, resolve their identified receipts and also finish by the cut. These are checked assertions, not external attestations generated by the adapter.

Coverage records the issuer, candidate set, source/classifier versions, provider receipts, missing sources and explicit coverage/availability/observation clocks. The coverage interval must reach the decision cut; its final watermark and review are required by that same cut. This makes the accepted final watermark/review instant the cut itself. The implementation **does not establish that a live provider and human-review workflow can satisfy that boundary**. A future activation must resolve that real workflow with the source and review owners. A fabricated or retrospectively dated receipt is not an implementation workaround.

## Firstness, matching and price windows

The cohort consumes the existing published `us_prophet_v3` buy board and its emitted T2. It does not recompute T2 from a later complete price tape. Native ages are 0/1/2 `native_2D_ticks`; they are not calendar days. Each canonical issuer's first emitted T2 consumes its slot before quality, attention, benchmark or matching exclusions. A later favorable row cannot replace it.

Every requested cut must be represented. A missing or quarantined earlier board makes firstness uncertain for later newly observed issuers unless a by-cut owner history receipt covers the entire missing prefix and establishes no previous T2. That proof cannot retroactively replace an already consumed observation.

The schedule supplies actual session opens and closes, including early closes. Each decision cut is 09:15 America/New_York, with the prior completed board received by the cut. Entry is the first scheduled regular close after the cut. H1, H5, H10 and H21 refer to entry session index +1, +5, +10 and +21. No nightly-ledger registration date is substituted for this morning clock.

Q1 and Q0 are matched 1:1 without replacement on decision date, sector, frozen legacy raw attention (`n_recent >= 3`) and native T2 age. Both pools are ordered by `SHA256(operation_key|cohort_id|canonical_issuer_id)`. The quality request's issuer, ticker and raw attention are bound to the board observation. Incomplete pairs are omitted whole at evaluation; the original pairing remains unchanged.

Observed outcome values require an explicit filled entry, an owner price receipt reference, exact frozen entry and exit session/close values, and observation/availability clocks after the relevant exit. Every supplied outcome is checked, including unused controls. When absolute, SPY-relative and sector-relative paired mean increments are supplied together, they must agree under the shared benchmark windows. These checks do not download prices or authenticate the referenced owner receipt.

`compute_ohlc_path` requires a separate explicit pre-cut session calendar to establish the last 20 true ranges and B20. Twenty-one observed bars cannot bridge a missing expected session. It excludes entry-session and pre-fill highs/lows from future excursions. Same-bar first upper/lower barrier crossings have unknown intraday order; missing paths or a missing price-basis receipt retain unknown labels. The price owner must establish compatible corporate-action adjustments: this function checks receipt presence and bar consistency, and does not authenticate an adjustment convention from the reference string.

## Analysis and audit outputs

The primary statistic is the equal-date mean of within-pair H5 SPY-excess differences. The equal-pair mean is reported separately. Returns and effects are percentage points. The bootstrap samples the fixed 252-session calendar, including inactive dates, with circular blocks of length 21, 10 and 42, 10,000 draws, PCG64 seed 2601007 restarted for each length, and linear 2.5%/97.5% quantiles. Empty sampled dates do not become zero-effect observations. Each interval exposes its actual valid-draw count.

The fixed four-member secondary family is H5 SPY-positive rate, H10 mean increment, H21 mean increment and H5 clean-liftoff rate. A member without its prespecified breadth, completeness, context and valid-bootstrap requirements remains descriptive and receives p=1 in the four-member Holm family. Synthetic/offline consumer runs cannot obtain prospective inferential admission.

The evaluator reports the 200-complete-pair, 50-active-date, four fixed 63-session-quarter, 70% matched-support, 80% quality-coverage and 95% H5-completeness gates, plus version/timing/integrity and robustness requirements. The pair floor is not a power guarantee. Unknown owner attestations remain unknown gates. A research-positive mathematical classification, where supported through the lower-level evaluator, grants no trading or promotion authority.

The integrated report includes the full original eligible-pool rematches for every issuer, INTC, each matched date and each matched sector. Newly matched controls and changed support are exposed. Coverage is tabulated across all retained first-T2 observations by date, sector, attention and Q, including unknown and unused records.

Fixed round-trip deductions of 10/25/50 basis points report individual net mean and hit-rate sensitivity at H1/H5/H10/H21. Equal deductions cancel in the paired mean increment. They are scenarios, not measured trading costs. H5 SPY-responder persistence uses separate mature H10 and H21 denominators; unknown later returns never become reversals. Later cumulative-excess changes use the same known responders on both dates.

Corrections append to the cohort envelope while its original manifest, Q states and pairs remain byte-identical. The evaluation binds the full correction chain and outcome packet digests. A data-integrity exception fails the integrity gate and adds a descriptive whole-pair deletion sensitivity. A correction digest alone cannot supply a corrected-truth analysis: corrected labels and the corresponding complete pools must actually be available.

## Scope that still needs separate inputs or implementation

This release supplies the primary research mechanics and explicit interfaces; it does not claim the entire prospective research program has been conducted.

| Required research surface | Present boundary |
|---|---|
| Prospective collection and enrollment | No collector, scheduler or enrollment switch; the same-day morning clock is not admitted by the existing nightly registration adapter |
| Calendar, source/reviewer and price authenticity | Supplied identities and clocks are checked structurally; independently captured owner receipts are still required |
| Expectations normalization | Missing comparable, rights-admissible, by-cut baseline remains unknown; no vendor average is promoted |
| Same-type corporate events within one issuer-quarter | Existing canonical identity limitations are retained; no invented replacement IDs |
| Root-connected-component deduplication | The evaluator can consume explicit descriptive omission analyses, but this CLI does not manufacture a frozen cross-issuer root graph from outcome metadata |
| Relaxed matching, first-T1 interaction, repeated native episodes | Not generated by the first-T2 consumer; these need their own frozen populations, support and dependence accounting and cannot rescue the primary result |
| Technical-era comparison | A cohort freezes one version set and refuses changes within it; separate eras remain separate cohorts |
| Corrected truth | Original-as-known and exception-exclusion reports exist; a corrected receipt hash alone leaves corrected-truth results unknown |
| Missing-outcome scenarios | Lower-level evaluation accepts an observed-cohort range and evidence-backed ruling; the CLI does not invent a complete-range attestation from partial supplied prices |
| Post-H5 drawdown | Requires the relevant price path; cumulative return fields alone leave it unknown |

## Verification

The targeted CI job is `pb-d-event-quality` in `.github/ci/legacy-jobs.yml`; its explicit path scope includes the new implementation, tests, synthetic input and imported owner contracts. Its command is:

```bash
python -m pytest tests/test_pb_d_quality.py tests/test_pb_d_cohort.py \
  tests/test_pb_d_evaluation.py tests/test_pb_d_consumer.py -q
```

The cumulative checkpoint records executed native-owner regressions, reviewer findings and repairs, exact source hashes and integrated example output. CI and merge evidence is added when each action concludes; a pending release entry is not proof of shipping. Test assertions and a draft PR are not substitutes for those release receipts.
