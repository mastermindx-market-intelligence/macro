# Sector and theme allocation intelligence — architecture and research

Existing programme: `sector-rotation-intelligence`. Existing workstream: `LEADERSHIP-ROTATION-INTELLIGENCE`. Accountable principal for this supplement: Sol under the current Chairman commission. Carrier: Macro PR #9507, branch `sol/rotation-intelligence-architecture-20261016-c1`.

## Latest source finding: reuse existing archives before acquiring again

**Read [EXISTING_ARCHIVE_REUSE_R3.md](EXISTING_ARCHIVE_REUSE_R3.md) first.** A bounded investigation of the already-produced Tiingo/Data OS source found **37 original receipts and 37 materialized views covering all thirteen required instruments**. All original receipts passed native receipt-identity validation; manifest references and Parquet-footer row counts agree. Only metadata, schemas and date statistics were read. No raw payload or numeric price/return/volume column was decoded.

The eleven sectors and SPY have captured slices extending through October 15, 2026; BIL's inspected history ends October 9. Deep histories are already present for every required instrument. This does not establish uninterrupted coverage, correct market values, full output-byte integrity or compatible adjustment vintages. It does establish that a new whole-history acquisition must not be the automatic next action.

Current `config/dataset_registry.yml`, blob `ce492d349d91e73cdf962de8dc110aec96a2bfd5`, records `vendor.tiingo.raw.equity_eod` and `vendor.tiingo.research.eod` as PRODUCED. The research views retain research-only/noncanonical status; current source rules do not permit them to displace canonical Yahoo/Massive or become PIT evidence by flipping a local flag. Existing source records affirm Chairman-reported special Tiingo commercial/public rights, but actual product/use enrollment and source identity still need their proper existing-owner mapping. Do not restart generic contract procurement merely because provisional metadata says unverified.

**Refined next source action:** qualify the retained thirteen-series evidence through the existing `read_research_view` / `read_research_history` boundary, resolve actual EOD consumer use, revision/coverage and the BIL gap, then acquire only an identified missing dependency if necessary. Never relabel Tiingo rows as Yahoo receipts or treat capture time as original historical release. This supersedes only the earlier assumption that a new bounded Yahoo warmup must come first; the study's completeness, timing and scientific restrictions remain.

## R3 executable source-reader and baseline rehearsal

The proposed study has a working **synthetic reference sequence from source availability through all five baseline choices to continuous post-cost wealth**. The existing reader's own targeted tests were also executed. No live reader, capture activation, trained predictor or investment permission is claimed.

[SOURCE_READER_REHEARSAL_R3.md](SOURCE_READER_REHEARSAL_R3.md) records the tests, bounded source contract and limits. Executable references: [allocation_rehearsal.py](allocation_rehearsal.py), [test_allocation_rehearsal.py](test_allocation_rehearsal.py), [check_rehearsal_mutations.py](check_rehearsal_mutations.py). Exact evidence: [rehearsal_verification_r3.json](rehearsal_verification_r3.json).

- **35 reference tests pass**, locally and from published source on M2: thirteen-input completeness, 253-price warmup, 64-price return windows, late/ambiguous snapshots, no silent rewind, strict cash hurdle, missing decisions, drifted holdings, self-financing costs and liquidation.
- **Eight deliberately broken variants are caught** by intended assertions, not unrelated import failures. This is author verification, not independent review or complete formal proof.
- **46 original reader tests pass** on the unchanged source closure. The first isolated snapshot omitted the existing metric dependency; restoring that file resolved the failure without source/assertion edits.
- **Twelve calendar/cutoff assertions pass** using the incumbent calendar and timezone conversion. Official holiday/early-close metadata was checked separately. The helper does not certify actual early-close times, and the synthetic clock fixtures are not UTC.
- **Forty invented policy paths** cover two scenarios, five baselines and four costs. An adverse reversal is retained: the backward-looking bill hurdle can keep former leaders. No empirical performance is inferred.

The three new source files matched their executed hashes. Mutation results were byte-identical across observed Python versions. Raw path JSON was not byte-identical; a defined twelve-decimal semantic comparison matched schedules, choices and results. Numerical tolerance cannot weaken actual-source identity requirements.

## R2 specification and evidence — retained

1. [TARGET_SCOPE_AND_BASELINES_R1.md](TARGET_SCOPE_AND_BASELINES_R1.md): eleven sector ETFs plus SPY/BIL; distinct from native seven-pair and failed member-stock constructions; as-known cutoff, next-close proxy, twenty-session blocks and five comparator definitions.
2. [SOURCE_READINESS_AUDIT_R2.md](SOURCE_READINESS_AUDIT_R2.md): metadata-only inspection of 25 local Yahoo/flow files; short flow history and differing tails; default-off nine-sector capture. Its local-source findings stand, while R3 adds the previously uninspected existing Tiingo option.
3. [POLICY_ACCOUNTING_SPEC_R1.md](POLICY_ACCOUNTING_SPEC_R1.md), [policy_accounting_witness.py](policy_accounting_witness.py), [policy_accounting_results.json](policy_accounting_results.json): self-financing cost equation, seven closed-form cases, 512 algebraic comparisons, 128 cost-monotonicity checks and eight invalid-input refusals. Reused unchanged in R3.
4. [probe_broad_flow_contract.py](probe_broad_flow_contract.py), [broad_flow_probe_results.json](broad_flow_probe_results.json): fake-provider reproduction of market-price-in-NAV and retrieval/weekend indexing. A market-price timestamp is not a NAV date; actual downstream incidence remains unmeasured.
5. [EXISTING_READER_INTEGRATION_R1.md](EXISTING_READER_INTEGRATION_R1.md): exact immutable/causal preparation interface and cohort/cadence/cutoff/lookback differences. One-month provider-return capture cannot supply the long prefix; full-cache substitution changes provenance.

R2 published scripts/results were reproduced on M2. Their unaffected evidence was not rerun to inflate counts.

## Original foundation — retained, not rewritten

- [ASSESSMENT.md](ASSESSMENT.md): original 44,909-byte report, 35-source register, unchanged SHA-256 `4ba6241675c3f3528706f7c859019dd8e6f2ce390bd31199e7a4254bf1e26c4c`.
- [ARCHITECTURE.md](ARCHITECTURE.md): measurement, forecast, policy and stock/instrument expression; existing system boundaries and model ladder.
- [DATA_CONTRACTS.md](DATA_CONTRACTS.md): availability, revisions, identities, group indices, return basis and allowed use.
- [RESEARCH_DESIGN.md](RESEARCH_DESIGN.md): candidate economic targets, selection/dependence/multiplicity and qualification. Not canonical V3.
- [NATIVE_PROTOCOL_CROSSWALK.md](NATIVE_PROTOCOL_CROSSWALK.md): seven-pair native H1/H2/H3 versus the broader allocation question; governs shorthand in earlier documents.
- [LITERATURE.md](LITERATURE.md): sixteen primary-method entries with actual review depth and transfer limits.
- [READINESS_AND_DELEGATION.md](READINESS_AND_DELEGATION.md): mechanism research, dependency sequence and six future implementation packets, not dispatches.
- [REVIEW_AND_VERIFICATION.md](REVIEW_AND_VERIFICATION.md): original review dispositions, supplemented by R2/R3 evidence.
- [synthetic_design_checks.py](synthetic_design_checks.py), [synthetic_design_results.json](synthetic_design_results.json): original mathematical/known-covariance examples, not native statistical or market qualification.

## Preserved scope and current boundary

Track A is the original native Leadership Rotation repair with existing hypotheses, cohort, negative evidence and LR-W6/read gates. Track B is broader sector/industry/theme/cash research and needs its explicit population, information set, accounting and error budget through existing owners. Neither is a new evaluator or a way around held outcomes.

The existing [workstream](../../../agentos/workstreams/WS-LEADERSHIP-ROTATION-INTELLIGENCE.md), Mastermind #1194, Macro #7646/#9035/#9134 and source writers remain intact. There is no replacement graph, dataset store, regime owner, publisher, registry, queue, watcher or memory plane. Existing bans on rotation×cycle-position confluence, RS-dispersion gating, connect-flow gating and LLM detection are not revoked.

The native Tiingo reader permits qualified inspection/explicitly acknowledged retrospective research but refuses PIT_BACKTEST for its unadmitted hindsight views. That limitation remains; access to retained metadata is not an outcome-read or source-use permission. Do not open the native held partitions, silently extend current price authority, or backdate observations. Vendor-specific identity must remain explicit in the future adapter.

The old nine-node, 26-session, 09:00 and 63-price experiment stays unchanged. The proposed study's eleven assets/thirteen inputs, twenty-session schedule, 08:00 cutoff and correct 64-price return window remain specified. Source rights, actual session clocks, coverage and input identity—not another generic architecture—are the remaining qualification work before the empirical study.

## Release and recovery

**Published research candidate, DRAFT/HOLD for Sol; not merged or independently approved.** The original final-review provider403/no-verdict result was not retried or routed through another provider. No new worker/watcher was launched in R3. Prior children are terminal.

No market-return dataset or numeric vendor column was opened in this continuation; no provider acquisition, archive activation, production collector/reader edit, Trial/Vault act, native outcome read, trade, credential change or deployment occurred. Original isolated source tests did execute against invented fixtures; metadata checks executed the existing receipt validator, not an acquisition function.

Current-head required CI and a valid independent review remain release gates. Do not ready, auto-merge or merge based on old checks or synthetic pass counts. Source-only publication requires no production deployment.

Compatible procedure: Mastermind `50107c31531d3b4ab5a18b5acf5e77954a0549e3`. R3 source: Macro `ab5156a4b2c336181f3c5256e7c0766f04f99598`. Same GitHub branch/carrier. Full R3 and archive-metadata receipts remain under `/Volumes/Mastermind/research/rotation-intelligence-census-20261016-sol-c1/`; published source is the recoverable evidence, not a new lifecycle store. The broader predictive allocation programme remains incomplete.
