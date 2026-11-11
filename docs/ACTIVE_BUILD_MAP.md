<!-- GENERATED — do not edit by hand; regenerate with `python scripts/build_active_build_map.py`. Advisory only: this map informs sessions; it gates nothing. -->

# Active Build Map

Generated: 2026-11-11T07:32:13.442068+00:00  |  Open PRs: 100  |  Merged (window): 500  |  base: `81deaaaaecabf7c8407b438cfa04adc716b59d2c`

## Open PRs

| PR | Title | Branch | Updated | Flags |
|----|-------|--------|---------|-------|
| #11008 | fix(journal): show missing risk coverage and unavailable ratios | `sol/c2-journal-metric-coverage-20261111` | 2026-11-11 | DRAFT |
| #11006 | ci: run boundary CI jobs on the ubuntu-24.04 hosted image | `ci/pin-hosted-ubuntu-24-04` | 2026-11-11 | DRAFT / ⚠ protected:12 |
| #11001 | fix(grading): expose signed Brier binning residual | `c3/brier-residual-10999-20261111` | 2026-11-11 | DRAFT |
| #10998 | fix(lab): stop characterize() counting immature formation dates (#10996) | `fix/10996-characterize-maturity` | 2026-11-11 | — |
| #10995 | ci(pack): recalibrate gate:code pack weights from measured baselines | `ci/recalibrate-pack-weights` | 2026-11-11 | — |
| #10994 | fix(us-board): bind snapshot parts to the selected base file | `fix/us-board-snapshot-file-identity-20261110` | 2026-11-11 | — |
| #10991 | test(gdelt): virtual clock for the throttle spacing test | `test/gdelt-throttle-virtual-clock` | 2026-11-11 | — |
| #10989 | fix(options-profit): preserve exact decimal expiration payoff | `claude/options-profit-decimal-20261111-c2` | 2026-11-11 | DRAFT |
| #10988 | fix(inflation): keep copy feedback truthful and current | `c2/inflation-copy-feedback-20261111` | 2026-11-11 | DRAFT |
| #10987 | fix(forex-pip): refuse nonfinite derived pip values | `c2/forex-pip-finite-range-20261111` | 2026-11-11 | DRAFT |
| #10986 | fix(stop-target): retain sub-cent prices in display and copy | `c2/stop-price-precision-20261111` | 2026-11-11 | DRAFT |
| #10985 | fix(compounding): preserve deposits at near-zero rates | `claude/c2-compounding-stability-20261110` | 2026-11-11 | DRAFT |
| #10984 | fix(sharpe): use annualized basis for quality interpretation | `claude/c2-sharpe-reporting-basis-20261110` | 2026-11-10 | DRAFT |
| #10983 | fix(rule72): preserve near-zero precision and refuse overflow | `claude/c2-rule72-numeric-range-20261110` | 2026-11-10 | DRAFT |
| #10982 | fix(kelly): classify exact decimal zero without a tolerance band | `claude/c2-kelly-exact-zero-20261110` | 2026-11-10 | DRAFT |
| #10980 | fix(margin): label fully paid positions without a call threshold | `claude/c2-margin-no-borrowing-20261110` | 2026-11-10 | DRAFT |
| #10979 | fix(cagr): respect complete date ranges before numeric years | `claude/c2-cagr-date-precedence-20261110` | 2026-11-10 | DRAFT |
| #10978 | fix(drawdown): disclose the actual recovery input source | `c2/drawdown-input-provenance-20261110` | 2026-11-10 | DRAFT |
| #10976 | fix(roi): withhold nonfinite annualized returns | `c2/roi-finite-range-10934-20261110` | 2026-11-10 | DRAFT |
| #10975 | fix(calculators): withhold out-of-range Stock Average arithmetic | `claude/stock-average-range-c2-20261110` | 2026-11-10 | DRAFT |
| #10974 | fix(bonds): preserve missing weeks and unavailable cross-asset statistics | `sol/c2-bonds-missing-data-20261110` | 2026-11-10 | DRAFT |
| #10973 | sector: lane 1 rows increment — four confluence universe blocks, theme rows, group name_zh (v1.1) | `claude/si-lane1-rows-20261110` | 2026-11-10 | ⚠ protected:1 |
| #10972 | fix(glossary): restrict area filtering to explicit controls | `claude/c2-glossary-filter-controls-20261110` | 2026-11-10 | DRAFT |
| #10970 | fix(flows): use common dated sector ETF windows | `c2/sector-flow-common-windows-20261110` | 2026-11-10 | DRAFT |
| #10969 | fix(rlt): bind quarterly rebalance events to exchange sessions | `c2/rebalance-calendar-sessions-20261110` | 2026-11-10 | DRAFT |
| #10966 | fix(insider): correct filing windows and rebalance exits | `sol/insider-window-rebalance-10955-20261110` | 2026-11-11 | — |
| #10965 | feat(sector-generation): R4 notes + PIT membership facts (lane 1 v1.1, Part B) | `claude/si-lane1-pit-fields-20261110` | 2026-11-10 | — |
| #10960 | Restore Initiative compiler and expose bounded strategic source context | `sol/web-estate-initiative-context-qualification-20261110-c4` | 2026-11-11 | — |
| #10956 | sector_intelligence.issuer_economics.v1 on the v2 query envelope (lane 5 v1.1, stacked on #10931) | `claude/si-research-v11-issuer-econ-20261110` | 2026-11-10 | ⚠ CONFLICTING |
| #10954 | fix(sector-generation): close round-3 review findings (R3-S1 + notes) | `claude/si-lane1-r3-followup-20261110` | 2026-11-10 | — |
| #10953 | fix(agentos): Stop hook HANDOFF_UNAVAILABLE store-poison repair | `claude/agentos-stop-hook-store-poison` | 2026-11-11 | — |
| #10952 | fix(admin): keep Capacity Router usage, lineage and filters truthful | `fix/capacity-router-observation-integrity-20261110` | 2026-11-11 | — |
| #10949 | fix(stocks): join S&P sector aliases before hub aggregation | `c3/stocks-sector-identity-20261110` | 2026-11-10 | DRAFT |
| #10944 | fix(caddy): cache only successful Terminal public data responses | `claude/ssd-ss-terminal-public-data-qualified-20261110-581dcfb5f9028d76` | 2026-11-10 | DRAFT |
| #10940 | fix(macro): publish canonical Market State score and guard settlement parity | `sol/macro-marketstate-canonical-live-20261109` | 2026-11-10 | ⚠ CONFLICTING / ⚠ protected:3 |
| #10938 | fix(calculators): guard unavailable annualized value in covered-call render and copy | `fix/covered-call-unavailable-annualized-20261110` | 2026-11-10 | — |
| #10937 | fix(access): serve the trading journal xlsx as one exact public asset (#10936) | `codex/tools-journal-public-download-20261110` | 2026-11-10 | — |
| #10933 | ci: freeze pack dependencies with ci/constraints.txt and one Playwright pin (F3-lite) | `ci/f3-lite-constraints` | 2026-11-10 | ⚠ protected:1 |
| #10932 | fix(merge-on-green): F7 — lease-serialized refresh floor under the repo-wide brake; rotation-owned window; fail-closed repair slot | `fix/mog-refresh-admission-f7` | 2026-11-11 | — |
| #10931 | feat(sector-intelligence): lane 5 theme_research request/v2 union + real industry evidence | `claude/si-research-v2-20261109` | 2026-11-11 | ⚠ CONFLICTING |
| #10930 | fix: recover CPI live analysis and remove stale detection cards | `claude/ssd-t3-4a5c5a78-4511ebb22558e9b4` | 2026-11-11 | — |
| #10929 | HOLD-FOR-SOL: feat(sector-intelligence): macro sector generation — publisher, reader, API and native projection | `claude/si-macro-generation-20261109` | 2026-11-11 | DRAFT / ⚠ CONFLICTING / ⚠ protected:2 |
| #10928 | fix(country-cycles): describe local and USD price series accurately | `claude/ssd-country-cycles-basis-copy-p12t48-20261104-bc436ca8bc466c94` | 2026-11-10 | — |
| #10926 | Restore the exact Forensics source drawer on return | `claude/ssd-shared-shell-forensics-source-return-20261103-d59c4575f1f5545a` | 2026-11-10 | — |
| #10924 | feat(sector-intelligence): lane 8 analytics and history — definitions, turn/history knowledge, B12 dispositions | `claude/ssd-t3-bc9ff67e-78688517a78d520a` | 2026-11-11 | — |
| #10919 | perf(ci): stop unrelated CI packs on authored Sector briefs | `sol/ci-passive-authoring-json-10915-20261109-web-c2` | 2026-11-10 | — |
| #10918 | aibrief: truthful freshness — freshest brief copy, stale chip, receipt | `claude/aibrief-truthful-display-20261110` | 2026-11-11 | — |
| #10916 | ci: verify workflow event checkout identity | `fix/queue-shadow-checkout-macro` | 2026-11-11 | ⚠ protected:2 |
| #10915 | docs(sector): finalize Shared Shell masterplan and Fable T3 packet | `sol/sector-shared-shell-masterplan-20261109-c3` | 2026-11-10 | ⚠ CONFLICTING |
| #10908 | fix(xguerrilla): wire registry + admission gates into run_pilot() — the one runtime call site (t_397488ab) | `xg/pilot-sim-runtime-wiring` | 2026-11-11 | — |
| #10905 | fix(shell): publish content-addressed theme and onboarding scripts | `claude/ssd-shared-shell-public-bundles-qualified-20261109-84bce01ff454f6ce` | 2026-11-10 | ⚠ CONFLICTING / ⚠ protected:4 |
| #10904 | fix(f00c): reconcile surviving alert and research dependency records | `sol/f00c-surviving-records-20261109` | 2026-11-10 | — |
| #10903 | feat(macro): build a coherent responsive intelligence workspace | `sol/web-macro-experience-redesign-20261109-astra-02` | 2026-11-11 | ⚠ CONFLICTING / files-truncated |
| #10902 | liveness: brief-age check F + engine-job verdict for check B (AI Brief freeze 2026-10-19→11-09) | `claude/ssd-t3-4f13be30-c4747f2c70fdfd15` | 2026-11-11 | ⚠ protected:2 |
| #10901 | Crypto R4: reliable cases, asset readings and navigation | `design/crypto-snapshot-safety-20261109` | 2026-11-10 | DRAFT / files-truncated |
| #10900 | Qualify attended www automatic TLS adoption | `claude/ssd-shared-shell-www-tls-t15s4-20261109-a0dcf77baaec7161` | 2026-11-09 | — |
| #10899 | Balance CI packs on measured seconds, not mixed heuristic units | `ci/measured-pack-cost-model` | 2026-11-10 | ⚠ CONFLICTING / ⚠ protected:1 |
| #10898 | docs(options): complete Terminal and Shared Shell consolidation masterplan | `claude/options-suite-production-plan-20261109` | 2026-11-10 | DRAFT |
| #10896 | Polish Macro search and dialog interactions | `sol/web-macro-saas-polish-20261109-astra-01` | 2026-11-11 | ⚠ CONFLICTING / files-truncated |
| #10895 | fix: bounded pagination for active build map PR listings | `fix/abm-bounded-untruncated` | 2026-11-10 | — |
| #10894 | Improve Paper workflows, source contracts and design navigation | `design/paper-breadth-navigation-20261109-c2` | 2026-11-09 | files-truncated |
| #10893 | feat(confluence): clarify evidence cards and protect cached readers | `claude/confluence-compatibility-paper-20261109` | 2026-11-09 | DRAFT / ⚠ CONFLICTING |
| #10892 | fix(baskets): disclose the Canadian price panel date | `claude/ssd-shared-shell-canada-clock-t32s4-20261109-2a90fbf3e81bd99a` | 2026-11-09 | — |
| #10890 | P12.T60: keep IPO lock-up dates explicitly modeled across Start and detail | `claude/ssd-shared-shell-ipo-modeled-date-20261109-6fc79aa6f0ad8684` | 2026-11-11 | — |
| #10889 | fix(crypto): localize the product continuation action | `claude/ssd-shared-shell-crypto-entry-20261109-1a72aaff5e302d7d` | 2026-11-09 | — |
| #10888 | fix(shared-shell): show the Mainland sector ETF close date | `claude/ssd-shared-shell-china-sector-date-20261109-b0e43b12bae8d37d` | 2026-11-09 | — |
| #10887 | fix(shared-shell): preserve Nasdaq and Russell desk on detail return | `claude/ssd-shared-shell-index-desk-return-20261109-9dd44e3733759ef7` | 2026-11-10 | — |
| #10882 | design(expectations): period geometry handoff and editable Paper proof | `sol/expectation-period-geometry-20261109` | 2026-11-09 | DRAFT |
| #10880 | fix(expectations): keep fiscal comparisons and restored chart selection accurate | `sol/expectation-readout-period-20261109` | 2026-11-11 | ⚠ CONFLICTING |
| #10879 | feat(navigation): add mobile All Tools category chooser | `design/paper-tools-mobile-chooser-20261109` | 2026-11-09 | DRAFT |
| #10878 | ci: publish optional hosted pack timing observations | `sol/web-ci-overhaul-hosted-timing-20261108-c3` | 2026-11-11 | ⚠ protected:1 |
| #10876 | docs(paper): clarify count scope, Dossier opening and risk horizons | `sol/paper-count-scope-and-evidence-20261109` | 2026-11-10 | — |
| #10874 | Complete Paper clarity workflows and preserve implementation contracts | `sol/paper-workflow-depth-20261108-c3-2335` | 2026-11-10 | — |
| #10873 | fix(agentos): full PR coverage in active_builds.v1 — no more TRUNCATED joins | `lane/agentos-full-pr-coverage` | 2026-11-10 | ⚠ protected:1 |
| #10872 | docs(paper): reconcile evidence and improve ten product workflows | `sol/paper-audit-clarity-20261108-c3-followup` | 2026-11-10 | files-truncated |
| #10866 | Options: preserve exact retained selection provenance for Lab | `claude/ssd-exposure-retained-selection-20261108-efeed331ebe2d34b` | 2026-11-10 | ⚠ CONFLICTING |
| #10861 | Refresh reviewed public brand facts and data-date wording | `claude/ssd-portfolio-network-continuity-20261108-4e80eefe3bf426eb` | 2026-11-10 | — |
| #10854 | fix(news): distinguish policy effective dates from comment deadlines | `sol/web-news-policy-effective-20261108-c4` | 2026-11-10 | — |
| #10853 | fix(brain): preserve news provenance and disclose unknown health | `sol/web-news-brain-provenance-20261108-c4` | 2026-11-10 | ⚠ protected:1 |
| #10852 | fix(policy-intent): retain input vintage in briefs and new ledger rows | `dot/policy-intent-intel-asof-20261108` | 2026-11-08 | DRAFT |
| #10851 | fix(news): retain source provenance in unified intelligence | `sol/web-news-unified-provenance-20261108-c4` | 2026-11-10 | ⚠ CONFLICTING |
| #10850 | fix(news): carry delivery health into private AI evidence | `sol/web-news-estate-ai-health-20261108-c4` | 2026-11-11 | — |
| #10846 | feat(deploy): wake existing VPS updater immediately after accepted main pushes | `sol/web-fast-vps-sync-20261107` | 2026-11-11 | ⚠ protected:1 |
| #10845 | fix(sector): make Act-Now Show more buttons expand their rows | `fix/sector-act-now-expand-20261107` | 2026-11-08 | — |
| #10840 | fix(business-activity): separate monthly periods from observation clocks | `claude/ssd-business-clock-current-p12t2s13s3-20261107-eae6ff5c737aa309` | 2026-11-11 | — |
| #10839 | feat(sectors): integrate persistent leadership evidence and dated context | `sol/web-persistent-sector-leadership-adoption-20261107-c4` | 2026-11-07 | — |
| #10838 | feat(shared-shell): deliver source-bound Intl journeys and current consumer fixes | `codex/s8-participant-current-protected-20261106` | 2026-11-10 | ⚠ CONFLICTING / ⚠ protected:2 / files-truncated |
| #10826 | fix(nightly): move the analyst-revision drip off the engine render path into collect_tail (#7646) | `claude/ssd-macro-nightly-revisions-drip-offrender-20261107` | 2026-11-11 | ⚠ protected:2 |
| #10824 | fix(prophet): bound native source reads and bind nightly Python | `sol/web-prophet-today-session-input-20261107` | 2026-11-10 | ⚠ protected:1 |
| #10809 | fix(prophet): remove growing revision-history cost before nightly generation | `sol/prophet-outage-revisions-history-20261107` | 2026-11-11 | — |
| #10806 | feat(sectors): persistent leadership plan and evidence dossier | `sol/web-persistent-sector-leadership-20261106-c4` | 2026-11-07 | — |
| #10805 | ci: prevent two unsettled exact-base diagnostic replays | `claude/ssd-ci-exact-base-unknown-safety-20261105-93782fd5e8c55e87` | 2026-11-11 | — |
| #10802 | fix(txi): stamp completion after native input capture | `claude/ssd-mo-t005-s8-txi-clock-20261106-47e29b87385e0113` | 2026-11-06 | DRAFT |
| #10801 | fix(ci): extend bounded exact-parent fence history for stale PRs | `codex/c3-fence-exact-ancestry-20261106` | 2026-11-07 | DRAFT / ⚠ protected:1 |
| #10797 | fix(calculators): make Dividend copy feedback truthful and current | `dot/dividend-copy-feedback-20261106` | 2026-11-10 | — |
| #10796 | Market Memory: open exact saved readings from the same source session | `codex/market-memory-saved-session-navigation-20261106` | 2026-11-11 | ⚠ protected:1 |
| #10795 | feat(risk): qualified multi-asset context inside Risk Radar (display-only) | `sol/web-multiasset-risk-20261105-sol` | 2026-11-09 | ⚠ CONFLICTING / files-truncated |
| #10794 | feat(market-tide): point-in-time event and stock response context | `sol/web-market-tide-event-response-20261105` | 2026-11-09 | ⚠ CONFLICTING |
| #10793 | merge-on-green: reserve one refresh per sweep for the main-red repair under a red baseline (S8) | `claude/ssd-macro-s8-repair-refresh-reserve-20261106-1883fd9cdc3b2de3` | 2026-11-11 | — |
| #10788 | ci(pack): split the 1,630 s fif-kernel-guards job into three measured siblings (S6) | `claude/ssd-macro-s6-fif-kernel-split-20261105-e967ef249d20f730` | 2026-11-08 | ⚠ CONFLICTING |

> ⚠ CONFLICTING means mergeStateStatus=DIRTY — pull_request CI is suppressed on conflicting PRs (known repo failure mode).

## File Collisions

| PR A | PR B | Shared files | Files |
|------|------|-------------|-------|
| #10956 | #10931 | 14 | `.github/ci/legacy-jobs.yml`, `agentos/handoffs/WS-SECTOR-INTELLIGENCE-COMPLETION-2026-11-09-LANE5-RESEARCH-V2.md`, `app/theme_research.py`, `contracts/market_ontology/technology_economic_change.evidence.v2.schema.json`, `engine/market_ontology/technology_research_registration.py`, `engine/market_ontology/theme_research_binding.py`, `engine/market_ontology/theme_research_registry.py`, `engine/sector_intelligence/finance_research_registration.py` +6 more |
| #10929 | #10839 | 14 | `collectors/sector_holdings.py`, `engine/leadership_rotation_context.py`, `engine/sector_central.py`, `engine/sector_dated_context.py`, `scripts/build_sector_holdings_coverage.py`, `templates/sector_central.html.j2`, `tests/fixtures/leadership_rotation/sector_window_measurements.complete.v1.json`, `tests/fixtures/leadership_rotation/sector_window_measurements.unavailable.v1.json` +6 more |
| #10973 | #10929 | 8 ⚠ | `app/sector_generation.py`, `config/dag.yml`, `engine/sector_native_view.py`, `lib/sector_central_carry.py`, `scripts/build_sector_central.py`, `tests/test_sector_central_carry.py`, `tests/test_sector_native_view_typed_blocks.py`, `tests/test_sector_population.py` |
| #10839 | #10806 | 8 | `agentos/handoffs/LEADERSHIP-ROTATION-INTELLIGENCE-2026-11-06-persistent-sector-c4.md`, `agentos/workstreams/WS-LEADERSHIP-ROTATION-INTELLIGENCE.md`, `engine/leadership_rotation_context.py`, `research/LEADERSHIP_ROTATION_PERSISTENT_SECTOR_MASTERPLAN_2026-11-06.md`, `research/LEADERSHIP_ROTATION_PERSISTENT_SECTOR_NATIVE_READ_2026-11-06.json`, `research/LEADERSHIP_ROTATION_PERSISTENT_SECTOR_SOURCE_AUDIT_2026-11-06.md`, `research/LEADERSHIP_ROTATION_PERSISTENT_SECTOR_TRANSPORT_PROBE_2026-11-06.json`, `tests/test_leadership_measured_read.py` |
| #10965 | #10929 | 5 | `.github/ci/legacy-jobs.yml`, `lib/sector_central_carry.py`, `lib/sector_population.py`, `tests/test_sector_central_carry.py`, `tests/test_sector_population.py` |
| #10954 | #10929 | 5 | `app/sector_generation.py`, `lib/sector_central_carry.py`, `lib/sector_population.py`, `tests/test_sector_central_carry.py`, `tests/test_sector_population.py` |
| #10903 | #10896 | 5 | `.github/ci/legacy-jobs.yml`, `mockups/evidence/macro-w9/cells/2bc845930ffdfa50.png`, `mockups/evidence/macro-w9/cells/alerts-face-dark-en-desktop.png`, `mockups/evidence/macro-w9/cells/alerts-face-dark-zh-desktop.png`, `mockups/evidence/macro-w9/cells/alerts-face-light-en-desktop.png` |
| #10973 | #10954 | 4 | `app/sector_generation.py`, `lib/sector_central_carry.py`, `tests/test_sector_central_carry.py`, `tests/test_sector_population.py` |
| #10965 | #10954 | 4 | `lib/sector_central_carry.py`, `lib/sector_population.py`, `tests/test_sector_central_carry.py`, `tests/test_sector_population.py` |
| #10940 | #10838 | 4 ⚠ | `.github/ci/legacy-jobs.yml`, `.github/workflows/render.yml`, `templates/dashboard.html.j2`, `tests/test_ci_pack.py` |
| #10918 | #10905 | 4 | `.github/ci/legacy-jobs.yml`, `mockups/evidence/prophet-p0b-zero-fouc/manifest.json`, `mockups/evidence/prophet-p0b-zero-fouc/mobile-layout-canada.json`, `mockups/evidence/prophet-p0b-zero-fouc/mobile-layout.json` |
| #10973 | #10965 | 3 | `lib/sector_central_carry.py`, `tests/test_sector_central_carry.py`, `tests/test_sector_population.py` |
| #10966 | #10854 | 3 | `.github/ci/legacy-jobs.yml`, `config/unrun_test_baseline.json`, `tests/test_ci_pack.py` |
| #10966 | #10851 | 3 | `.github/ci/legacy-jobs.yml`, `config/unrun_test_baseline.json`, `tests/test_ci_pack.py` |
| #10940 | #10929 | 3 | `.github/ci/legacy-jobs.yml`, `scripts/build_site.py`, `tests/test_ci_pack.py` |
| #10933 | #10905 | 3 | `.github/ci/legacy-jobs.yml`, `scripts/ci_apt_native_plan.py`, `tests/test_ci_browser_native_setup.py` |
| #10929 | #10924 | 3 | `.github/ci/legacy-jobs.yml`, `research/sector_completion_20261021/B04_METRIC_DEFINITIONS.md`, `tests/test_ci_pack.py` |
| #10929 | #10838 | 3 ⚠ | `.github/ci/legacy-jobs.yml`, `config/dag.yml`, `tests/test_ci_pack.py` |
| #10929 | #10826 | 3 ⚠ | `.github/ci/legacy-jobs.yml`, `config/dag.yml`, `tests/test_ci_pack.py` |
| #10905 | #10838 | 3 | `.github/ci/legacy-jobs.yml`, `tests/test_check_ui_visual_evidence.py`, `tests/test_ci_pack_semantic.py` |
| #10899 | #10788 | 3 | `.github/ci/legacy-jobs.yml`, `scripts/run_ci_pack.py`, `tests/test_ci_pack.py` |
| #10854 | #10851 | 3 | `.github/ci/legacy-jobs.yml`, `config/unrun_test_baseline.json`, `tests/test_ci_pack.py` |
| #10838 | #10826 | 3 ⚠ | `.github/ci/legacy-jobs.yml`, `config/dag.yml`, `tests/test_ci_pack.py` |
| #11006 | #10929 | 2 | `tests/test_ci_pack.py`, `tests/test_vps_live_orchestration.py` |
| #11006 | #10916 | 2 ⚠ | `.github/workflows/fences.yml`, `.github/workflows/medtech-contracts.yml` |
| #11006 | #10899 | 2 | `tests/test_ci_pack.py`, `tests/test_contract_delta.py` |
| #11006 | #10878 | 2 ⚠ | `.github/workflows/ci.yml`, `tests/test_ci_plan_workflow.py` |
| #10995 | #10919 | 2 | `scripts/run_ci_pack.py`, `tests/test_ci_pack.py` |
| #10995 | #10899 | 2 | `scripts/run_ci_pack.py`, `tests/test_ci_pack.py` |
| #10995 | #10788 | 2 | `scripts/run_ci_pack.py`, `tests/test_ci_pack.py` |
| #10966 | #10952 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10966 | #10940 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10966 | #10929 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10966 | #10924 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10966 | #10899 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10966 | #10838 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10966 | #10826 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10966 | #10797 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10966 | #10794 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10966 | #10788 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10960 | #10953 | 2 | `.github/ci/legacy-jobs.yml`, `scripts/agentos.py` |
| #10956 | #10937 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_browser_native_setup.py` |
| #10956 | #10933 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_browser_native_setup.py` |
| #10956 | #10905 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_browser_native_setup.py` |
| #10956 | #10853 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_browser_native_setup.py` |
| #10952 | #10940 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10952 | #10929 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10952 | #10924 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10952 | #10899 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10952 | #10854 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10952 | #10851 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10952 | #10838 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10952 | #10826 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10952 | #10797 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10952 | #10794 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10952 | #10788 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10940 | #10924 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10940 | #10899 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10940 | #10854 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10940 | #10851 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10940 | #10826 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10940 | #10797 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10940 | #10794 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10940 | #10788 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10937 | #10933 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_browser_native_setup.py` |
| #10937 | #10931 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_browser_native_setup.py` |
| #10937 | #10905 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_browser_native_setup.py` |
| #10937 | #10853 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_browser_native_setup.py` |
| #10933 | #10931 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_browser_native_setup.py` |
| #10933 | #10853 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_browser_native_setup.py` |
| #10932 | #10793 | 2 | `scripts/merge_on_green.py`, `tests/test_merge_on_green.py` |
| #10931 | #10905 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_browser_native_setup.py` |
| #10931 | #10853 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_browser_native_setup.py` |
| #10929 | #10899 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10929 | #10896 | 2 | `.github/ci/legacy-jobs.yml`, `design_refs/sector-paper-20261021/copy_deck.json` |
| #10929 | #10854 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10929 | #10851 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10929 | #10806 | 2 | `engine/leadership_rotation_context.py`, `tests/test_leadership_measured_read.py` |
| #10929 | #10797 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10929 | #10794 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10929 | #10788 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10928 | #10838 | 2 | `research/market_os/evidence/country-cycles-p12t48-20261104/COUNTRY_CYCLES_JOURNEY.md`, `templates/country_cycles.html.j2` |
| #10924 | #10899 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10924 | #10854 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10924 | #10851 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10924 | #10838 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10924 | #10826 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10924 | #10797 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10924 | #10794 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10924 | #10788 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10919 | #10899 | 2 | `scripts/run_ci_pack.py`, `tests/test_ci_pack.py` |
| #10919 | #10788 | 2 | `scripts/run_ci_pack.py`, `tests/test_ci_pack.py` |
| #10905 | #10899 | 2 | `.github/ci/legacy-jobs.yml`, `scripts/run_ci_pack.py` |
| #10905 | #10853 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_browser_native_setup.py` |
| #10905 | #10845 | 2 | `site/theme.js`, `templates/theme.js` |
| #10905 | #10805 | 2 | `scripts/run_ci_pack.py`, `tests/test_ci_pack_semantic.py` |
| #10905 | #10788 | 2 | `.github/ci/legacy-jobs.yml`, `scripts/run_ci_pack.py` |
| #10899 | #10854 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10899 | #10851 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10899 | #10838 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10899 | #10826 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10899 | #10797 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10899 | #10794 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10895 | #10873 | 2 | `scripts/build_active_build_map.py`, `tests/test_build_active_build_map.py` |
| #10887 | #10838 | 2 | `.github/ci/legacy-jobs.yml`, `scripts/build_subsector_confluence.py` |
| #10854 | #10838 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10854 | #10826 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10854 | #10797 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10854 | #10794 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10854 | #10788 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10851 | #10838 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10851 | #10826 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10851 | #10797 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10851 | #10794 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10851 | #10788 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10838 | #10797 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10838 | #10794 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10838 | #10788 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10826 | #10824 | 2 ⚠ | `.github/workflows/daily.yml`, `scripts/build_stock_library.py` |
| #10826 | #10797 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10826 | #10794 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10826 | #10788 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10797 | #10794 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10797 | #10788 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #10794 | #10788 | 2 | `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py` |
| #11006 | #10995 | 1 | `tests/test_ci_pack.py` |
| #11006 | #10966 | 1 | `tests/test_ci_pack.py` |
| #11006 | #10952 | 1 | `tests/test_ci_pack.py` |
| #11006 | #10940 | 1 | `tests/test_ci_pack.py` |
| #11006 | #10933 | 1 ⚠ | `.github/workflows/ci.yml` |
| #11006 | #10932 | 1 | `tests/test_merge_on_green.py` |
| #11006 | #10924 | 1 | `tests/test_ci_pack.py` |
| #11006 | #10919 | 1 | `tests/test_ci_pack.py` |
| #11006 | #10854 | 1 | `tests/test_ci_pack.py` |
| #11006 | #10851 | 1 | `tests/test_ci_pack.py` |
| #11006 | #10838 | 1 | `tests/test_ci_pack.py` |
| #11006 | #10826 | 1 | `tests/test_ci_pack.py` |
| #11006 | #10801 | 1 ⚠ | `.github/workflows/fences.yml` |
| #11006 | #10797 | 1 | `tests/test_ci_pack.py` |
| #11006 | #10794 | 1 | `tests/test_ci_pack.py` |
| #11006 | #10793 | 1 | `tests/test_merge_on_green.py` |
| #11006 | #10788 | 1 | `tests/test_ci_pack.py` |
| #10995 | #10966 | 1 | `tests/test_ci_pack.py` |
| #10995 | #10952 | 1 | `tests/test_ci_pack.py` |
| #10995 | #10940 | 1 | `tests/test_ci_pack.py` |
| #10995 | #10929 | 1 | `tests/test_ci_pack.py` |
| #10995 | #10924 | 1 | `tests/test_ci_pack.py` |
| #10995 | #10905 | 1 | `scripts/run_ci_pack.py` |
| #10995 | #10854 | 1 | `tests/test_ci_pack.py` |
| #10995 | #10851 | 1 | `tests/test_ci_pack.py` |
| #10995 | #10838 | 1 | `tests/test_ci_pack.py` |
| #10995 | #10826 | 1 | `tests/test_ci_pack.py` |
| #10995 | #10805 | 1 | `scripts/run_ci_pack.py` |
| #10995 | #10797 | 1 | `tests/test_ci_pack.py` |
| #10995 | #10794 | 1 | `tests/test_ci_pack.py` |
| #10984 | #10975 | 1 | `tests/js/calculator_input_integrity.test.mjs` |
| #10973 | #10838 | 1 ⚠ | `config/dag.yml` |
| #10973 | #10826 | 1 ⚠ | `config/dag.yml` |
| #10966 | #10965 | 1 | `.github/ci/legacy-jobs.yml` |
| #10966 | #10960 | 1 | `.github/ci/legacy-jobs.yml` |
| #10966 | #10956 | 1 | `.github/ci/legacy-jobs.yml` |
| #10966 | #10953 | 1 | `.github/ci/legacy-jobs.yml` |
| #10966 | #10938 | 1 | `.github/ci/legacy-jobs.yml` |
| #10966 | #10937 | 1 | `.github/ci/legacy-jobs.yml` |
| #10966 | #10933 | 1 | `.github/ci/legacy-jobs.yml` |
| #10966 | #10931 | 1 | `.github/ci/legacy-jobs.yml` |
| #10966 | #10919 | 1 | `tests/test_ci_pack.py` |
| #10966 | #10918 | 1 | `.github/ci/legacy-jobs.yml` |
| #10966 | #10905 | 1 | `.github/ci/legacy-jobs.yml` |
| #10966 | #10903 | 1 | `.github/ci/legacy-jobs.yml` |
| #10966 | #10896 | 1 | `.github/ci/legacy-jobs.yml` |
| #10966 | #10887 | 1 | `.github/ci/legacy-jobs.yml` |
| #10966 | #10880 | 1 | `.github/ci/legacy-jobs.yml` |
| #10966 | #10866 | 1 | `.github/ci/legacy-jobs.yml` |
| #10966 | #10853 | 1 | `.github/ci/legacy-jobs.yml` |
| #10966 | #10796 | 1 | `.github/ci/legacy-jobs.yml` |
| #10966 | #10795 | 1 | `.github/ci/legacy-jobs.yml` |
| #10965 | #10960 | 1 | `.github/ci/legacy-jobs.yml` |
| #10965 | #10956 | 1 | `.github/ci/legacy-jobs.yml` |
| #10965 | #10953 | 1 | `.github/ci/legacy-jobs.yml` |
| #10965 | #10952 | 1 | `.github/ci/legacy-jobs.yml` |
| #10965 | #10940 | 1 | `.github/ci/legacy-jobs.yml` |
| #10965 | #10938 | 1 | `.github/ci/legacy-jobs.yml` |
| #10965 | #10937 | 1 | `.github/ci/legacy-jobs.yml` |
| #10965 | #10933 | 1 | `.github/ci/legacy-jobs.yml` |
| #10965 | #10931 | 1 | `.github/ci/legacy-jobs.yml` |
| #10965 | #10924 | 1 | `.github/ci/legacy-jobs.yml` |
| #10965 | #10918 | 1 | `.github/ci/legacy-jobs.yml` |
| #10965 | #10905 | 1 | `.github/ci/legacy-jobs.yml` |
| #10965 | #10903 | 1 | `.github/ci/legacy-jobs.yml` |
| #10965 | #10899 | 1 | `.github/ci/legacy-jobs.yml` |
| #10965 | #10896 | 1 | `.github/ci/legacy-jobs.yml` |
| #10965 | #10887 | 1 | `.github/ci/legacy-jobs.yml` |
| #10965 | #10880 | 1 | `.github/ci/legacy-jobs.yml` |
| #10965 | #10866 | 1 | `.github/ci/legacy-jobs.yml` |
| #10965 | #10854 | 1 | `.github/ci/legacy-jobs.yml` |
| #10965 | #10853 | 1 | `.github/ci/legacy-jobs.yml` |
| #10965 | #10851 | 1 | `.github/ci/legacy-jobs.yml` |
| #10965 | #10838 | 1 | `.github/ci/legacy-jobs.yml` |
| #10965 | #10826 | 1 | `.github/ci/legacy-jobs.yml` |
| #10965 | #10797 | 1 | `.github/ci/legacy-jobs.yml` |
| #10965 | #10796 | 1 | `.github/ci/legacy-jobs.yml` |
| #10965 | #10795 | 1 | `.github/ci/legacy-jobs.yml` |
| #10965 | #10794 | 1 | `.github/ci/legacy-jobs.yml` |
| #10965 | #10788 | 1 | `.github/ci/legacy-jobs.yml` |
| #10960 | #10956 | 1 | `.github/ci/legacy-jobs.yml` |
| #10960 | #10952 | 1 | `.github/ci/legacy-jobs.yml` |
| #10960 | #10940 | 1 | `.github/ci/legacy-jobs.yml` |
| #10960 | #10938 | 1 | `.github/ci/legacy-jobs.yml` |
| #10960 | #10937 | 1 | `.github/ci/legacy-jobs.yml` |
| #10960 | #10933 | 1 | `.github/ci/legacy-jobs.yml` |
| #10960 | #10931 | 1 | `.github/ci/legacy-jobs.yml` |
| #10960 | #10929 | 1 | `.github/ci/legacy-jobs.yml` |
| #10960 | #10924 | 1 | `.github/ci/legacy-jobs.yml` |
| #10960 | #10918 | 1 | `.github/ci/legacy-jobs.yml` |
| #10960 | #10905 | 1 | `.github/ci/legacy-jobs.yml` |
| #10960 | #10903 | 1 | `.github/ci/legacy-jobs.yml` |
| #10960 | #10899 | 1 | `.github/ci/legacy-jobs.yml` |
| #10960 | #10896 | 1 | `.github/ci/legacy-jobs.yml` |
| #10960 | #10887 | 1 | `.github/ci/legacy-jobs.yml` |
| #10960 | #10880 | 1 | `.github/ci/legacy-jobs.yml` |
| #10960 | #10873 | 1 | `scripts/agentos.py` |
| #10960 | #10866 | 1 | `.github/ci/legacy-jobs.yml` |
| #10960 | #10854 | 1 | `.github/ci/legacy-jobs.yml` |
| #10960 | #10853 | 1 | `.github/ci/legacy-jobs.yml` |
| #10960 | #10851 | 1 | `.github/ci/legacy-jobs.yml` |
| #10960 | #10838 | 1 | `.github/ci/legacy-jobs.yml` |
| #10960 | #10826 | 1 | `.github/ci/legacy-jobs.yml` |
| #10960 | #10797 | 1 | `.github/ci/legacy-jobs.yml` |
| #10960 | #10796 | 1 | `.github/ci/legacy-jobs.yml` |
| #10960 | #10795 | 1 | `.github/ci/legacy-jobs.yml` |
| #10960 | #10794 | 1 | `.github/ci/legacy-jobs.yml` |
| #10960 | #10788 | 1 | `.github/ci/legacy-jobs.yml` |
| #10956 | #10953 | 1 | `.github/ci/legacy-jobs.yml` |
| #10956 | #10952 | 1 | `.github/ci/legacy-jobs.yml` |
| #10956 | #10940 | 1 | `.github/ci/legacy-jobs.yml` |
| #10956 | #10938 | 1 | `.github/ci/legacy-jobs.yml` |
| #10956 | #10929 | 1 | `.github/ci/legacy-jobs.yml` |
| #10956 | #10924 | 1 | `.github/ci/legacy-jobs.yml` |
| #10956 | #10918 | 1 | `.github/ci/legacy-jobs.yml` |
| #10956 | #10903 | 1 | `.github/ci/legacy-jobs.yml` |
| #10956 | #10899 | 1 | `.github/ci/legacy-jobs.yml` |
| #10956 | #10896 | 1 | `.github/ci/legacy-jobs.yml` |
| #10956 | #10887 | 1 | `.github/ci/legacy-jobs.yml` |
| #10956 | #10880 | 1 | `.github/ci/legacy-jobs.yml` |
| #10956 | #10866 | 1 | `.github/ci/legacy-jobs.yml` |
| #10956 | #10854 | 1 | `.github/ci/legacy-jobs.yml` |
| #10956 | #10851 | 1 | `.github/ci/legacy-jobs.yml` |
| #10956 | #10838 | 1 | `.github/ci/legacy-jobs.yml` |
| #10956 | #10826 | 1 | `.github/ci/legacy-jobs.yml` |
| #10956 | #10797 | 1 | `.github/ci/legacy-jobs.yml` |
| #10956 | #10796 | 1 | `.github/ci/legacy-jobs.yml` |
| #10956 | #10795 | 1 | `.github/ci/legacy-jobs.yml` |
| #10956 | #10794 | 1 | `.github/ci/legacy-jobs.yml` |
| #10956 | #10788 | 1 | `.github/ci/legacy-jobs.yml` |
| #10953 | #10952 | 1 | `.github/ci/legacy-jobs.yml` |
| #10953 | #10940 | 1 | `.github/ci/legacy-jobs.yml` |
| #10953 | #10938 | 1 | `.github/ci/legacy-jobs.yml` |
| #10953 | #10937 | 1 | `.github/ci/legacy-jobs.yml` |
| #10953 | #10933 | 1 | `.github/ci/legacy-jobs.yml` |
| #10953 | #10931 | 1 | `.github/ci/legacy-jobs.yml` |
| #10953 | #10929 | 1 | `.github/ci/legacy-jobs.yml` |
| #10953 | #10924 | 1 | `.github/ci/legacy-jobs.yml` |
| #10953 | #10918 | 1 | `.github/ci/legacy-jobs.yml` |
| #10953 | #10905 | 1 | `.github/ci/legacy-jobs.yml` |
| #10953 | #10903 | 1 | `.github/ci/legacy-jobs.yml` |
| #10953 | #10899 | 1 | `.github/ci/legacy-jobs.yml` |
| #10953 | #10896 | 1 | `.github/ci/legacy-jobs.yml` |
| #10953 | #10887 | 1 | `.github/ci/legacy-jobs.yml` |
| #10953 | #10880 | 1 | `.github/ci/legacy-jobs.yml` |
| #10953 | #10873 | 1 | `scripts/agentos.py` |
| #10953 | #10866 | 1 | `.github/ci/legacy-jobs.yml` |
| #10953 | #10854 | 1 | `.github/ci/legacy-jobs.yml` |
| #10953 | #10853 | 1 | `.github/ci/legacy-jobs.yml` |
| #10953 | #10851 | 1 | `.github/ci/legacy-jobs.yml` |
| #10953 | #10838 | 1 | `.github/ci/legacy-jobs.yml` |
| #10953 | #10826 | 1 | `.github/ci/legacy-jobs.yml` |
| #10953 | #10797 | 1 | `.github/ci/legacy-jobs.yml` |
| #10953 | #10796 | 1 | `.github/ci/legacy-jobs.yml` |
| #10953 | #10795 | 1 | `.github/ci/legacy-jobs.yml` |
| #10953 | #10794 | 1 | `.github/ci/legacy-jobs.yml` |
| #10953 | #10788 | 1 | `.github/ci/legacy-jobs.yml` |
| #10952 | #10938 | 1 | `.github/ci/legacy-jobs.yml` |
| #10952 | #10937 | 1 | `.github/ci/legacy-jobs.yml` |
| #10952 | #10933 | 1 | `.github/ci/legacy-jobs.yml` |
| #10952 | #10931 | 1 | `.github/ci/legacy-jobs.yml` |
| #10952 | #10919 | 1 | `tests/test_ci_pack.py` |
| #10952 | #10918 | 1 | `.github/ci/legacy-jobs.yml` |
| #10952 | #10905 | 1 | `.github/ci/legacy-jobs.yml` |
| #10952 | #10903 | 1 | `.github/ci/legacy-jobs.yml` |
| #10952 | #10896 | 1 | `.github/ci/legacy-jobs.yml` |
| #10952 | #10887 | 1 | `.github/ci/legacy-jobs.yml` |
| #10952 | #10880 | 1 | `.github/ci/legacy-jobs.yml` |
| #10952 | #10866 | 1 | `.github/ci/legacy-jobs.yml` |
| #10952 | #10853 | 1 | `.github/ci/legacy-jobs.yml` |
| #10952 | #10796 | 1 | `.github/ci/legacy-jobs.yml` |
| #10952 | #10795 | 1 | `.github/ci/legacy-jobs.yml` |
| #10944 | #10937 | 1 | `app/deploy/Caddyfile` |
| #10940 | #10938 | 1 | `.github/ci/legacy-jobs.yml` |
| #10940 | #10937 | 1 | `.github/ci/legacy-jobs.yml` |
| #10940 | #10933 | 1 | `.github/ci/legacy-jobs.yml` |
| #10940 | #10931 | 1 | `.github/ci/legacy-jobs.yml` |
| #10940 | #10919 | 1 | `tests/test_ci_pack.py` |
| #10940 | #10918 | 1 | `.github/ci/legacy-jobs.yml` |
| #10940 | #10905 | 1 | `.github/ci/legacy-jobs.yml` |
| #10940 | #10903 | 1 | `.github/ci/legacy-jobs.yml` |
| #10940 | #10896 | 1 | `.github/ci/legacy-jobs.yml` |
| #10940 | #10887 | 1 | `.github/ci/legacy-jobs.yml` |
| #10940 | #10880 | 1 | `.github/ci/legacy-jobs.yml` |
| #10940 | #10866 | 1 | `.github/ci/legacy-jobs.yml` |
| #10940 | #10853 | 1 | `.github/ci/legacy-jobs.yml` |
| #10940 | #10796 | 1 | `.github/ci/legacy-jobs.yml` |
| #10940 | #10795 | 1 | `.github/ci/legacy-jobs.yml` |
| #10938 | #10937 | 1 | `.github/ci/legacy-jobs.yml` |
| #10938 | #10933 | 1 | `.github/ci/legacy-jobs.yml` |
| #10938 | #10931 | 1 | `.github/ci/legacy-jobs.yml` |
| #10938 | #10929 | 1 | `.github/ci/legacy-jobs.yml` |
| #10938 | #10924 | 1 | `.github/ci/legacy-jobs.yml` |
| #10938 | #10918 | 1 | `.github/ci/legacy-jobs.yml` |
| #10938 | #10905 | 1 | `.github/ci/legacy-jobs.yml` |
| #10938 | #10903 | 1 | `.github/ci/legacy-jobs.yml` |
| #10938 | #10899 | 1 | `.github/ci/legacy-jobs.yml` |
| #10938 | #10896 | 1 | `.github/ci/legacy-jobs.yml` |
| #10938 | #10887 | 1 | `.github/ci/legacy-jobs.yml` |
| #10938 | #10880 | 1 | `.github/ci/legacy-jobs.yml` |
| #10938 | #10866 | 1 | `.github/ci/legacy-jobs.yml` |
| #10938 | #10854 | 1 | `.github/ci/legacy-jobs.yml` |
| #10938 | #10853 | 1 | `.github/ci/legacy-jobs.yml` |
| #10938 | #10851 | 1 | `.github/ci/legacy-jobs.yml` |
| #10938 | #10838 | 1 | `.github/ci/legacy-jobs.yml` |
| #10938 | #10826 | 1 | `.github/ci/legacy-jobs.yml` |
| #10938 | #10797 | 1 | `.github/ci/legacy-jobs.yml` |
| #10938 | #10796 | 1 | `.github/ci/legacy-jobs.yml` |
| #10938 | #10795 | 1 | `.github/ci/legacy-jobs.yml` |
| #10938 | #10794 | 1 | `.github/ci/legacy-jobs.yml` |
| #10938 | #10788 | 1 | `.github/ci/legacy-jobs.yml` |
| #10937 | #10929 | 1 | `.github/ci/legacy-jobs.yml` |
| #10937 | #10924 | 1 | `.github/ci/legacy-jobs.yml` |
| #10937 | #10918 | 1 | `.github/ci/legacy-jobs.yml` |
| #10937 | #10903 | 1 | `.github/ci/legacy-jobs.yml` |
| #10937 | #10899 | 1 | `.github/ci/legacy-jobs.yml` |
| #10937 | #10896 | 1 | `.github/ci/legacy-jobs.yml` |
| #10937 | #10887 | 1 | `.github/ci/legacy-jobs.yml` |
| #10937 | #10880 | 1 | `.github/ci/legacy-jobs.yml` |
| #10937 | #10866 | 1 | `.github/ci/legacy-jobs.yml` |
| #10937 | #10854 | 1 | `.github/ci/legacy-jobs.yml` |
| #10937 | #10851 | 1 | `.github/ci/legacy-jobs.yml` |
| #10937 | #10838 | 1 | `.github/ci/legacy-jobs.yml` |
| #10937 | #10826 | 1 | `.github/ci/legacy-jobs.yml` |
| #10937 | #10797 | 1 | `.github/ci/legacy-jobs.yml` |
| #10937 | #10796 | 1 | `.github/ci/legacy-jobs.yml` |
| #10937 | #10795 | 1 | `.github/ci/legacy-jobs.yml` |
| #10937 | #10794 | 1 | `.github/ci/legacy-jobs.yml` |
| #10937 | #10788 | 1 | `.github/ci/legacy-jobs.yml` |
| #10933 | #10929 | 1 | `.github/ci/legacy-jobs.yml` |
| #10933 | #10924 | 1 | `.github/ci/legacy-jobs.yml` |
| #10933 | #10918 | 1 | `.github/ci/legacy-jobs.yml` |
| #10933 | #10903 | 1 | `.github/ci/legacy-jobs.yml` |
| #10933 | #10899 | 1 | `.github/ci/legacy-jobs.yml` |
| #10933 | #10896 | 1 | `.github/ci/legacy-jobs.yml` |
| #10933 | #10887 | 1 | `.github/ci/legacy-jobs.yml` |
| #10933 | #10880 | 1 | `.github/ci/legacy-jobs.yml` |
| #10933 | #10878 | 1 ⚠ | `.github/workflows/ci.yml` |
| #10933 | #10866 | 1 | `.github/ci/legacy-jobs.yml` |
| #10933 | #10854 | 1 | `.github/ci/legacy-jobs.yml` |
| #10933 | #10851 | 1 | `.github/ci/legacy-jobs.yml` |
| #10933 | #10838 | 1 | `.github/ci/legacy-jobs.yml` |
| #10933 | #10826 | 1 | `.github/ci/legacy-jobs.yml` |
| #10933 | #10797 | 1 | `.github/ci/legacy-jobs.yml` |
| #10933 | #10796 | 1 | `.github/ci/legacy-jobs.yml` |
| #10933 | #10795 | 1 | `.github/ci/legacy-jobs.yml` |
| #10933 | #10794 | 1 | `.github/ci/legacy-jobs.yml` |
| #10933 | #10788 | 1 | `.github/ci/legacy-jobs.yml` |
| #10931 | #10929 | 1 | `.github/ci/legacy-jobs.yml` |
| #10931 | #10924 | 1 | `.github/ci/legacy-jobs.yml` |
| #10931 | #10918 | 1 | `.github/ci/legacy-jobs.yml` |
| #10931 | #10903 | 1 | `.github/ci/legacy-jobs.yml` |
| #10931 | #10899 | 1 | `.github/ci/legacy-jobs.yml` |
| #10931 | #10896 | 1 | `.github/ci/legacy-jobs.yml` |
| #10931 | #10887 | 1 | `.github/ci/legacy-jobs.yml` |
| #10931 | #10880 | 1 | `.github/ci/legacy-jobs.yml` |
| #10931 | #10866 | 1 | `.github/ci/legacy-jobs.yml` |
| #10931 | #10854 | 1 | `.github/ci/legacy-jobs.yml` |
| #10931 | #10851 | 1 | `.github/ci/legacy-jobs.yml` |
| #10931 | #10838 | 1 | `.github/ci/legacy-jobs.yml` |
| #10931 | #10826 | 1 | `.github/ci/legacy-jobs.yml` |
| #10931 | #10797 | 1 | `.github/ci/legacy-jobs.yml` |
| #10931 | #10796 | 1 | `.github/ci/legacy-jobs.yml` |
| #10931 | #10795 | 1 | `.github/ci/legacy-jobs.yml` |
| #10931 | #10794 | 1 | `.github/ci/legacy-jobs.yml` |
| #10931 | #10788 | 1 | `.github/ci/legacy-jobs.yml` |
| #10930 | #10879 | 1 | `site/macro.html` |
| #10930 | #10845 | 1 | `site/us_stocks.html` |
| #10929 | #10919 | 1 | `tests/test_ci_pack.py` |
| #10929 | #10918 | 1 | `.github/ci/legacy-jobs.yml` |
| #10929 | #10905 | 1 | `.github/ci/legacy-jobs.yml` |
| #10929 | #10903 | 1 | `.github/ci/legacy-jobs.yml` |
| #10929 | #10900 | 1 | `app/deploy/update.sh` |
| #10929 | #10887 | 1 | `.github/ci/legacy-jobs.yml` |
| #10929 | #10880 | 1 | `.github/ci/legacy-jobs.yml` |
| #10929 | #10866 | 1 | `.github/ci/legacy-jobs.yml` |
| #10929 | #10853 | 1 | `.github/ci/legacy-jobs.yml` |
| #10929 | #10796 | 1 | `.github/ci/legacy-jobs.yml` |
| #10929 | #10795 | 1 | `.github/ci/legacy-jobs.yml` |
| #10924 | #10919 | 1 | `tests/test_ci_pack.py` |
| #10924 | #10918 | 1 | `.github/ci/legacy-jobs.yml` |
| #10924 | #10905 | 1 | `.github/ci/legacy-jobs.yml` |
| #10924 | #10903 | 1 | `.github/ci/legacy-jobs.yml` |
| #10924 | #10896 | 1 | `.github/ci/legacy-jobs.yml` |
| #10924 | #10887 | 1 | `.github/ci/legacy-jobs.yml` |
| #10924 | #10880 | 1 | `.github/ci/legacy-jobs.yml` |
| #10924 | #10866 | 1 | `.github/ci/legacy-jobs.yml` |
| #10924 | #10853 | 1 | `.github/ci/legacy-jobs.yml` |
| #10924 | #10796 | 1 | `.github/ci/legacy-jobs.yml` |
| #10924 | #10795 | 1 | `.github/ci/legacy-jobs.yml` |
| #10919 | #10905 | 1 | `scripts/run_ci_pack.py` |
| #10919 | #10854 | 1 | `tests/test_ci_pack.py` |
| #10919 | #10851 | 1 | `tests/test_ci_pack.py` |
| #10919 | #10838 | 1 | `tests/test_ci_pack.py` |
| #10919 | #10826 | 1 | `tests/test_ci_pack.py` |
| #10919 | #10805 | 1 | `scripts/run_ci_pack.py` |
| #10919 | #10797 | 1 | `tests/test_ci_pack.py` |
| #10919 | #10794 | 1 | `tests/test_ci_pack.py` |
| #10918 | #10903 | 1 | `.github/ci/legacy-jobs.yml` |
| #10918 | #10899 | 1 | `.github/ci/legacy-jobs.yml` |
| #10918 | #10896 | 1 | `.github/ci/legacy-jobs.yml` |
| #10918 | #10887 | 1 | `.github/ci/legacy-jobs.yml` |
| #10918 | #10880 | 1 | `.github/ci/legacy-jobs.yml` |
| #10918 | #10866 | 1 | `.github/ci/legacy-jobs.yml` |
| #10918 | #10854 | 1 | `.github/ci/legacy-jobs.yml` |
| #10918 | #10853 | 1 | `.github/ci/legacy-jobs.yml` |
| #10918 | #10851 | 1 | `.github/ci/legacy-jobs.yml` |
| #10918 | #10838 | 1 | `.github/ci/legacy-jobs.yml` |
| #10918 | #10826 | 1 | `.github/ci/legacy-jobs.yml` |
| #10918 | #10797 | 1 | `.github/ci/legacy-jobs.yml` |
| #10918 | #10796 | 1 | `.github/ci/legacy-jobs.yml` |
| #10918 | #10795 | 1 | `.github/ci/legacy-jobs.yml` |
| #10918 | #10794 | 1 | `.github/ci/legacy-jobs.yml` |
| #10918 | #10788 | 1 | `.github/ci/legacy-jobs.yml` |
| #10916 | #10801 | 1 ⚠ | `.github/workflows/fences.yml` |
| #10905 | #10903 | 1 | `.github/ci/legacy-jobs.yml` |
| #10905 | #10896 | 1 | `.github/ci/legacy-jobs.yml` |
| #10905 | #10887 | 1 | `.github/ci/legacy-jobs.yml` |
| #10905 | #10880 | 1 | `.github/ci/legacy-jobs.yml` |
| #10905 | #10866 | 1 | `.github/ci/legacy-jobs.yml` |
| #10905 | #10854 | 1 | `.github/ci/legacy-jobs.yml` |
| #10905 | #10851 | 1 | `.github/ci/legacy-jobs.yml` |
| #10905 | #10826 | 1 | `.github/ci/legacy-jobs.yml` |
| #10905 | #10797 | 1 | `.github/ci/legacy-jobs.yml` |
| #10905 | #10796 | 1 | `.github/ci/legacy-jobs.yml` |
| #10905 | #10795 | 1 | `.github/ci/legacy-jobs.yml` |
| #10905 | #10794 | 1 | `.github/ci/legacy-jobs.yml` |
| #10903 | #10899 | 1 | `.github/ci/legacy-jobs.yml` |
| #10903 | #10887 | 1 | `.github/ci/legacy-jobs.yml` |
| #10903 | #10880 | 1 | `.github/ci/legacy-jobs.yml` |
| #10903 | #10866 | 1 | `.github/ci/legacy-jobs.yml` |
| #10903 | #10854 | 1 | `.github/ci/legacy-jobs.yml` |
| #10903 | #10853 | 1 | `.github/ci/legacy-jobs.yml` |
| #10903 | #10851 | 1 | `.github/ci/legacy-jobs.yml` |
| #10903 | #10838 | 1 | `.github/ci/legacy-jobs.yml` |
| #10903 | #10826 | 1 | `.github/ci/legacy-jobs.yml` |
| #10903 | #10797 | 1 | `.github/ci/legacy-jobs.yml` |
| #10903 | #10796 | 1 | `.github/ci/legacy-jobs.yml` |
| #10903 | #10795 | 1 | `.github/ci/legacy-jobs.yml` |
| #10903 | #10794 | 1 | `.github/ci/legacy-jobs.yml` |
| #10903 | #10788 | 1 | `.github/ci/legacy-jobs.yml` |
| #10899 | #10896 | 1 | `.github/ci/legacy-jobs.yml` |
| #10899 | #10887 | 1 | `.github/ci/legacy-jobs.yml` |
| #10899 | #10880 | 1 | `.github/ci/legacy-jobs.yml` |
| #10899 | #10866 | 1 | `.github/ci/legacy-jobs.yml` |
| #10899 | #10853 | 1 | `.github/ci/legacy-jobs.yml` |
| #10899 | #10805 | 1 | `scripts/run_ci_pack.py` |
| #10899 | #10796 | 1 | `.github/ci/legacy-jobs.yml` |
| #10899 | #10795 | 1 | `.github/ci/legacy-jobs.yml` |
| #10896 | #10887 | 1 | `.github/ci/legacy-jobs.yml` |
| #10896 | #10880 | 1 | `.github/ci/legacy-jobs.yml` |
| #10896 | #10866 | 1 | `.github/ci/legacy-jobs.yml` |
| #10896 | #10854 | 1 | `.github/ci/legacy-jobs.yml` |
| #10896 | #10853 | 1 | `.github/ci/legacy-jobs.yml` |
| #10896 | #10851 | 1 | `.github/ci/legacy-jobs.yml` |
| #10896 | #10838 | 1 | `.github/ci/legacy-jobs.yml` |
| #10896 | #10826 | 1 | `.github/ci/legacy-jobs.yml` |
| #10896 | #10797 | 1 | `.github/ci/legacy-jobs.yml` |
| #10896 | #10796 | 1 | `.github/ci/legacy-jobs.yml` |
| #10896 | #10795 | 1 | `.github/ci/legacy-jobs.yml` |
| #10896 | #10794 | 1 | `.github/ci/legacy-jobs.yml` |
| #10896 | #10788 | 1 | `.github/ci/legacy-jobs.yml` |
| #10892 | #10838 | 1 | `templates/basket_detail.html.j2` |
| #10887 | #10880 | 1 | `.github/ci/legacy-jobs.yml` |
| #10887 | #10866 | 1 | `.github/ci/legacy-jobs.yml` |
| #10887 | #10854 | 1 | `.github/ci/legacy-jobs.yml` |
| #10887 | #10853 | 1 | `.github/ci/legacy-jobs.yml` |
| #10887 | #10851 | 1 | `.github/ci/legacy-jobs.yml` |
| #10887 | #10826 | 1 | `.github/ci/legacy-jobs.yml` |
| #10887 | #10797 | 1 | `.github/ci/legacy-jobs.yml` |
| #10887 | #10796 | 1 | `.github/ci/legacy-jobs.yml` |
| #10887 | #10795 | 1 | `.github/ci/legacy-jobs.yml` |
| #10887 | #10794 | 1 | `.github/ci/legacy-jobs.yml` |
| #10887 | #10788 | 1 | `.github/ci/legacy-jobs.yml` |
| #10880 | #10866 | 1 | `.github/ci/legacy-jobs.yml` |
| #10880 | #10854 | 1 | `.github/ci/legacy-jobs.yml` |
| #10880 | #10853 | 1 | `.github/ci/legacy-jobs.yml` |
| #10880 | #10851 | 1 | `.github/ci/legacy-jobs.yml` |
| #10880 | #10838 | 1 | `.github/ci/legacy-jobs.yml` |
| #10880 | #10826 | 1 | `.github/ci/legacy-jobs.yml` |
| #10880 | #10797 | 1 | `.github/ci/legacy-jobs.yml` |
| #10880 | #10796 | 1 | `.github/ci/legacy-jobs.yml` |
| #10880 | #10795 | 1 | `.github/ci/legacy-jobs.yml` |
| #10880 | #10794 | 1 | `.github/ci/legacy-jobs.yml` |
| #10880 | #10788 | 1 | `.github/ci/legacy-jobs.yml` |
| #10879 | #10845 | 1 | `site/sector_central.html` |
| #10873 | #10826 | 1 ⚠ | `.github/workflows/daily.yml` |
| #10873 | #10824 | 1 ⚠ | `.github/workflows/daily.yml` |
| #10866 | #10854 | 1 | `.github/ci/legacy-jobs.yml` |
| #10866 | #10853 | 1 | `.github/ci/legacy-jobs.yml` |
| #10866 | #10851 | 1 | `.github/ci/legacy-jobs.yml` |
| #10866 | #10838 | 1 | `.github/ci/legacy-jobs.yml` |
| #10866 | #10826 | 1 | `.github/ci/legacy-jobs.yml` |
| #10866 | #10797 | 1 | `.github/ci/legacy-jobs.yml` |
| #10866 | #10796 | 1 | `.github/ci/legacy-jobs.yml` |
| #10866 | #10795 | 1 | `.github/ci/legacy-jobs.yml` |
| #10866 | #10794 | 1 | `.github/ci/legacy-jobs.yml` |
| #10866 | #10788 | 1 | `.github/ci/legacy-jobs.yml` |
| #10854 | #10853 | 1 | `.github/ci/legacy-jobs.yml` |
| #10854 | #10796 | 1 | `.github/ci/legacy-jobs.yml` |
| #10854 | #10795 | 1 | `.github/ci/legacy-jobs.yml` |
| #10853 | #10851 | 1 | `.github/ci/legacy-jobs.yml` |
| #10853 | #10838 | 1 | `.github/ci/legacy-jobs.yml` |
| #10853 | #10826 | 1 | `.github/ci/legacy-jobs.yml` |
| #10853 | #10797 | 1 | `.github/ci/legacy-jobs.yml` |
| #10853 | #10796 | 1 | `.github/ci/legacy-jobs.yml` |
| #10853 | #10795 | 1 | `.github/ci/legacy-jobs.yml` |
| #10853 | #10794 | 1 | `.github/ci/legacy-jobs.yml` |
| #10853 | #10788 | 1 | `.github/ci/legacy-jobs.yml` |
| #10851 | #10796 | 1 | `.github/ci/legacy-jobs.yml` |
| #10851 | #10795 | 1 | `.github/ci/legacy-jobs.yml` |
| #10838 | #10805 | 1 | `tests/test_ci_pack_semantic.py` |
| #10838 | #10796 | 1 | `.github/ci/legacy-jobs.yml` |
| #10838 | #10795 | 1 | `.github/ci/legacy-jobs.yml` |
| #10826 | #10809 | 1 | `collectors/equity_revisions.py` |
| #10826 | #10796 | 1 | `.github/ci/legacy-jobs.yml` |
| #10826 | #10795 | 1 | `.github/ci/legacy-jobs.yml` |
| #10805 | #10788 | 1 | `scripts/run_ci_pack.py` |
| #10797 | #10796 | 1 | `.github/ci/legacy-jobs.yml` |
| #10797 | #10795 | 1 | `.github/ci/legacy-jobs.yml` |
| #10796 | #10795 | 1 | `.github/ci/legacy-jobs.yml` |
| #10796 | #10794 | 1 | `.github/ci/legacy-jobs.yml` |
| #10796 | #10788 | 1 | `.github/ci/legacy-jobs.yml` |
| #10795 | #10794 | 1 | `.github/ci/legacy-jobs.yml` |
| #10795 | #10788 | 1 | `.github/ci/legacy-jobs.yml` |

## Recently Merged (last 14 days) (showing most recent 500; window truncated)

| PR | Title | Merged |
|----|-------|--------|
| #11000 | fix(baseline): sa-w4 seed read from committed blob — lift main-red circuit breaker | 2026-11-11 |
| #10997 | docs(sector): v1.1 status at 03:04Z on 2026-11-11 — section 27 | 2026-11-11 |
| #10977 | docs(sector): v1.1 status at 21:50Z — section 26: lane 3 armed, lane 1 rows and lane 7 consumer reviewed, three Terminal follow-ups merged | 2026-11-11 |
| #10971 | docs(sector): v1.1 status at 19:22Z — section 25: three Terminal lanes merged, three follow-ups armed, lane 1 fix checked, lane 3 landing round | 2026-11-10 |
| #10968 | docs(sector): v1.1 status at 16:50Z — section 24 | 2026-11-10 |
| #10967 | fix(admin): keep the Visitors and Sessions panels inside the panel budget | 2026-11-10 |
| #10964 | fix(forex): stop reusing stale transmission estimates | 2026-11-10 |
| #10963 | DEC: HERMES-UPSTREAM-CONTRIBUTION-AUTHORIZED | 2026-11-10 |
| #10959 | docs(sector): v1.1 adoption status record — sections 1 to 22 (superset of #10945) | 2026-11-10 |
| #10951 | fix(ci): cover the capacity router's import closure in eval-os-a1 (main red) | 2026-11-10 |
| #10950 | feat(admin): live Capacity Fabric router observatory | 2026-11-10 |
| #10948 | fix(xg): refuse github token values in the registry credential scan | 2026-11-11 |
| #10947 | feat(xg): identity registry v1 content for the five live personas (t_e305794e) | 2026-11-10 |
| #10946 | docs(agentos): retain estate graph owner and requester custody | 2026-11-10 |
| #10942 | docs(sector): v1.1 amendment adoption return from the active v1.0 build team | 2026-11-10 |
| #10941 | docs(agentos): retain T3 Agent Bus source and activation frontier | 2026-11-10 |
| #10939 | docs(sector): align active v1.0 build and Paper with Prophet v5.1 | 2026-11-10 |
| #10935 | fix(ci): pin playwright==1.64.1 in the two drifted native-acquisition jobs | 2026-11-10 |
| #10927 | Attribute Treasury reports to the Treasury source | 2026-11-10 |
| #10925 | research(memory): specify cross-engine predictive learning and prove PIT contracts | 2026-11-10 |
| #10923 | feat(sector-intelligence): design-r5 — five missing Paper design groups + guide amendment | 2026-11-10 |
| #10922 | docs(sector): execution charter and frontier for the Sector Intelligence build-out | 2026-11-10 |
| #10920 | docs(agents): expose shared graph skill and M2 continuity evidence | 2026-11-10 |
| #10917 | fix(smart-money): show the Fade qualification on ownership-desk hero cards | 2026-11-10 |
| #10914 | ci: pin Playwright for the remaining native browser jobs | 2026-11-10 |
| #10910 | Fix Calendar Clock rapid selection and stabilize its CI inputs | 2026-11-10 |
| #10909 | Resolve exact Research Vault selections and pin the Brain CI browser dependency | 2026-11-09 |
| #10906 | fix(agentos): add required metadata to CI consumer mapping discovery | 2026-11-09 |
| #10897 | admin: analytics panels — index identity/seed classifiers, honest budget timeouts | 2026-11-10 |
| #10891 | P12.T8.S2: preserve Theme Tree branch context through proxy return | 2026-11-11 |
| #10885 | fix(intl): disclose the price date without inferring ingestion delay | 2026-11-09 |
| #10884 | fix(xguerrilla): registry rework — scheme-less link gate, fail-closed --personas default, real tests, honest wiring doc (#10875 follow-up) | 2026-11-09 |
| #10883 | fix(agentos): restore merge-arm decision schema metadata | 2026-11-09 |
| #10881 | docs(ci): correct hosted release and author enrollment guidance | 2026-11-10 |
| #10877 | fix(wire): raise wire job timeout-minutes 10 -> 30 | 2026-11-09 |
| #10875 | feat(xg): identity registry schema v1 + fail-closed validator (t_da720ee4) | 2026-11-09 |
| #10871 | agentos: DEC press-wire disposition — keep marketing-press-wire active, fix timeout in place | 2026-11-09 |
| #10870 | feat(xguerrilla): admission chain — six ordered fail-closed refusals before a browser is spent | 2026-11-09 |
| #10869 | fix(xguerrilla): widen bio-path id class to dotted registry handles | 2026-11-09 |
| #10868 | test(imports): classify sealed D06 historical dependencies explicitly | 2026-11-08 |
| #10867 | design: enforce human-first Paper clarity and preserve build contracts | 2026-11-08 |
| #10865 | design(paper): clarify five product journeys and source contracts | 2026-11-08 |
| #10864 | design: clarify Paper journeys and implementation contracts | 2026-11-10 |
| #10862 | docs: preserve D06 historical source and evidence | 2026-11-08 |
| #10859 | T08.S2: skip oversized Git bodies before prewarm transfer | 2026-11-08 |
| #10858 | fix(sentinel): measure entry_radar_live on its ISO-8601 instant stamps | 2026-11-08 |
| #10856 | docs(news): verified delivery and consumer continuation handoff | 2026-11-08 |
| #10855 | fix(news): preserve per-share precision in evidence display | 2026-11-09 |
| #10849 | fix(screener): distinguish unavailable input from empty lenses | 2026-11-08 |
| #10848 | Record child model routing as the model_map backend (DEC) | 2026-11-08 |
| #10847 | docs(xguerrilla): split identity/domain/bio-link policy + two masterplan corrections out of the harness draft | 2026-11-08 |
| #10844 | docs(agentos): reconcile Hermes knowledge and original release frontier | 2026-11-08 |
| #10842 | policy(agent): adopt/extend existing OSS before rebuilding commodity infrastructure | 2026-11-07 |
| #10837 | feat(xguerrilla): add X network harness with bounded drift checks | 2026-11-08 |
| #10836 | Reconcile Hermes teammate v4 source frontier and original acceptance gates | 2026-11-07 |
| #10835 | fix(research-screener): never publish example fixtures as production data | 2026-11-07 |
| #10834 | test(commodities): make company-return coverage independent of published cohorts | 2026-11-07 |
| #10832 | Qualify the original attended Hermes APPLICATION service | 2026-11-07 |
| #10831 | Add scoped discovery corrections with preserved canonical history | 2026-11-07 |
| #10829 | docs(x-cohort): qualify programme proposal and acceptance evidence | 2026-11-07 |
| #10828 | ci: allow the sealed sector-cycles evidence pack to import cycles_page_ctx until #10777 lands (main red from #10822) | 2026-11-07 |
| #10823 | Agent OS: retain the Hermes native-memory implementation frontier | 2026-11-07 |
| #10822 | Sector Intelligence: Cycles wave visual-evidence packs land first, byte-identical to #10777 head 46214464 (#7646) | 2026-11-07 |
| #10821 | docs(agentos): preserve organization experience source and integration work | 2026-11-07 |
| #10820 | ci(options): run scenario regressions for ordinary code changes | 2026-11-07 |
| #10819 | fix(ci): S9 saturation floor — one lease-serialized refresh when the census zeroes the sweep | 2026-11-07 |
| #10816 | DEC: Meta-CEO org authority granted (chairman directive 2026-11-07) | 2026-11-07 |
| #10814 | docs(agentos): record qualified M2 Hermes gateway integration | 2026-11-07 |
| #10813 | Record Hermes teammate implementation and runtime continuation | 2026-11-07 |
| #10812 | docs(prophet): record outage repair and remaining production gates | 2026-11-07 |
| #10811 | DEC: HERMES-BOT-MIGRATION-AUTHORIZED — Hermes role migration, evidence-gated | 2026-11-07 |
| #10810 | docs(agentos): reconcile Hermes Secretary proposal and evidence boundaries | 2026-11-07 |
| #10804 | P13.T3 Preserve theme context through issuer research and return | 2026-11-10 |
| #10803 | ci: bound provided-action history to exact tested commits | 2026-11-10 |
| #10798 | feat(risk): paired early-warning inference and synthetic power diagnostic | 2026-11-08 |
| #10791 | docs(m2): align Claude instructions with protected review and publishing routes | 2026-11-06 |
| #10790 | fix(government-revenue): preserve issuer context across Back and Forward | 2026-11-08 |
| #10789 | fix(ci): preserve live authorization failure diagnostics | 2026-11-06 |
| #10784 | sweeper(S2a): every refused refresh-lease claim names its reason | 2026-11-06 |
| #10782 | fix(risk-state): withdraw stale guidance and misbound claims | 2026-11-10 |
| #10781 | ci(S1): copy-law scanners over nightly-rendered pages move to the data gate | 2026-11-07 |
| #10778 | Compose Press claims, retained GSC observations and bounded Pages classification | 2026-11-07 |
| #10773 | Inflation calculator: reject nonfinite derived results (Draft / source-only) | 2026-11-07 |
| #10770 | sweeper(X2): adaptive in-flight proof cap clamp(8+headroom, 8, 16) from a live run census | 2026-11-05 |
| #10769 | fix(calculators): keep the same-side target warning in the Risk-to-Reward copy | 2026-11-08 |
| #10767 | fix(retirement): correct near-zero-return annuity projection (source-only candidate; CI enrollment unresolved) | 2026-11-11 |
| #10766 | docs(agentos): CI acceleration checkpoint 7 (canary proven at one worker; X1 delivered) | 2026-11-05 |
| #10765 | Fix repeated page-readership membership scans | 2026-11-05 |
| #10762 | SEO: aggregate retained GSC rows only within the reporting window | 2026-11-05 |
| #10761 | fix(stockdata): accept a rich ticker payload only when it is this ticker (S3-05) | 2026-11-06 |
| #10760 | Admin SEO: show retained Search Console results without live-auth claims | 2026-11-05 |
| #10755 | fix(live-quotes): raise DISPLAY_BOARD_CAP 480 -> 640 (main washout-turn-organ red) | 2026-11-05 |
| #10753 | [D04][HOLD] Preserve Top Picks controls and native return | 2026-11-10 |
| #10752 | ci: compact narrowed PR packs while preserving baseline check coverage | 2026-11-08 |
| #10749 | docs(agentos): preserve Web Fabric autonomy owner decision | 2026-11-06 |
| #10747 | docs(agentos): CI acceleration checkpoint 6 (reconciliation, three open lanes) | 2026-11-05 |
| #10745 | ci(pack): keep CI in the exact-base replay env so failure reasons match | 2026-11-08 |
| #10739 | Implement Paper Risk Radar in Macro and shared shell | 2026-11-09 |
| #10735 | ci(legacy-jobs): split ci-control-plane-contracts three ways for the pack critical path (#917 acceleration) | 2026-11-08 |
| #10733 | Add canonical project authoring, direction and continuity contracts | 2026-11-04 |
| #10728 | glt views: O8 note wording + R1 review nits (comments, O2 test depth, mixed/empty cells) | 2026-11-08 |
| #10724 | agentos(GLT): final records — O3/O4 closed, O1/O2 landed, T27 release identity proven, rows pending nightly | 2026-11-04 |
| #10716 | Preserve actual persisted brief delivery observations | 2026-11-08 |
| #10714 | fix(govrev): keep missing headline counts unknown | 2026-11-04 |
| #10712 | Options: repair Context Audit v2 charter determinism and recovery | 2026-11-04 |
| #10710 | feat(options): bind exact-selection questions to fresh source authorization | 2026-11-07 |
| #10706 | agentos(CI-MERGE-CONTROL-PLANE): 2026-11-04 acceleration checkpoint (records only) | 2026-11-04 |
| #10702 | fix(rotation): make explicit notification consent survive stale preference saves | 2026-11-08 |
| #10701 | docs(market-memory): restore full programme continuity and recovery | 2026-11-06 |
| #10700 | fix(prophet): preserve admission metadata and model outcome provenance | 2026-11-08 |
| #10699 | docs(agentos): preserve the full Fable programme across four workstreams | 2026-11-04 |
| #10697 | docs(agentos): restore original Options Lab A-G programme mapping | 2026-11-04 |
| #10695 | P12.T32 Preserve regional basket identity and qualify current packing | 2026-11-04 |
| #10694 | glt views: forecast section disposition (O1) + rule-c refused-key test (O2) | 2026-11-04 |
| #10693 | agentos(GLT): 2026-11-04 scoped-commission closure handoff + workstream result | 2026-11-04 |
| #10692 | fix(ci): enforce maximum authority for oversized PR inventories | 2026-11-05 |
| #10691 | fix(agentos): correct Tiingo handoff ended_because enum | 2026-11-04 |
| #10690 | docs(tiingo): record live BOATS publication and three loaded schedules | 2026-11-04 |
| #10689 | docs(agentos): reconcile Sector Intelligence partial landing and Cycles continuation | 2026-11-05 |
| #10687 | design(D08C): options plan, compare and review candidate | 2026-11-08 |
| #10686 | D08B: Exposure, Volatility & 3D design and verified implementation return | 2026-11-08 |
| #10685 | design(D08D): futures and equity replay specification and evidence | 2026-11-08 |
| #10684 | docs(agentos): record session-owned reviews for Web, Codex and Claude | 2026-11-04 |
| #10681 | ci(glt): declare the LCB page's runtime Jinja templates in the exclusive GLT job (T25 AUDIT-N3 A1) | 2026-11-04 |
| #10675 | prophet: select <template> bodies on the template element (soupsieve 4.0) | 2026-11-03 |
| #10673 | docs(research): specify Terminal Rotation & Pivot Intelligence | 2026-11-07 |
| #10672 | agentos(grey-deer): records r7 — EW-P1 PRODUCTION_PROOF (two natural sessions), FU2 render coverage | 2026-11-03 |
| #10671 | fix: restore bilingual tooltip and page-title contracts | 2026-11-04 |
| #10667 | test(basket): skip the +1/-0 diff claim once the include is integrated | 2026-11-03 |
| #10666 | test(risk-radar): select inert-shell hooks on the template (soupsieve 4.0) | 2026-11-03 |
| #10664 | FIF statement graph: bare-year displayed columns take the filing's document period end (DEC:FIF-DISPLAYED-BARE-YEAR-COLUMNS-FROM-DOCUMENT-PERIOD-END-20261103) | 2026-11-03 |
| #10663 | FIF statement graph: fold the displayed table title when the exact pass finds no rows (331 served, 0 regressions) | 2026-11-03 |
| #10662 | docs(agentos): restore Executive programme continuity frontier | 2026-11-03 |
| #10661 | docs(agentos): retain Ubuntu4 Fabric integration gates and task tree | 2026-11-07 |
| #10660 | FIF member capture: name 10-K/10-Q taxonomy members by the stem the archive index lists (DEC:FIF-TAXONOMY-STEM-FROM-INDEX-20261102) | 2026-11-03 |
| #10659 | test(watchlist): judge ?v= stamps against the branch point, not live main; bump watchlist.js to v17 | 2026-11-07 |
| #10652 | perf(ci): cover 110 armed PRs with the existing quota-guarded sweeper | 2026-11-04 |
| #10651 | feat(radar): connect optional research cases to the native entrypoint | 2026-11-06 |
| #10650 | FIF statement graph: compose same-row, blank-gap and caption-led annual header periods (DEC:FIF-DISPLAYED-HEADER-PERIOD-COMPOSITION-20261103) | 2026-11-03 |
| #10646 | docs(design): D02 Macro Phase 2A product, UX and data specification | 2026-11-07 |
| #10644 | Research Factory: bind private reviewer source links to retained diagnostics | 2026-11-03 |
| #10641 | research(theme_graph): GMI CN historical identity census + gap (237 themes / 919 nodes NOT_IN_MASTER) | 2026-11-05 |
| #10640 | Fix dossier observation dates and isolate issuer source clocks | 2026-11-04 |
| #10639 | Register first-class beta intelligence without broadening unrelated route admission | 2026-11-05 |
| #10638 | gmi: bind activity-history fold to bridge receipts at the I/O layer (+ tier gate, idempotent reruns, repo-relative rulings) | 2026-11-08 |
| #10637 | FIF statement graph: code the displayed-parse refusal family (layout, column-period, presentation-absent) | 2026-11-03 |
| #10636 | gmi(rel m2): owner precision review report, blind non-authoring reviewer (E5/O1) | 2026-11-03 |
| #10635 | [authority] gmi(explorer): plain company display names from the symbol directory (G-UI-7) | 2026-11-03 |
| #10633 | fix(gmi-e3): attribute each judging dir's parse outcomes to its own domain | 2026-11-03 |
| #10629 | gmi(O5 record): withdraw the G-UI-5 copy packet, already fixed by #10306 | 2026-11-03 |
| #10628 | gmi(m1): first activity-history fold — MU → hbm_packaging under delegated C01 ruling | 2026-11-03 |
| #10627 | gmi(W3B T-03): bind THS local themes to their PIT basket through the graph EXPRESSES edge | 2026-11-03 |
| #10624 | GMI taxonomy owner review: 68 frozen-micro dispositions (64 KEEP, 4 RENAME) — Taxonomy gate PASS | 2026-11-03 |
| #10623 | Fix sector-breadth import-closure CI coverage in curated jobs | 2026-11-07 |
| #10621 | Make China Explore theme names, charts and signals readable on desktop and mobile | 2026-11-07 |
| #10620 | fix(spr): retain unavailable weekly comparisons and partial evidence | 2026-11-04 |
| #10618 | gmi: C01 graph_membership_use revision ruling + delegated curator A/B/C decision | 2026-11-03 |
| #10616 | ui-visual-evidence: give required rest cells the force_state byte-integrity floor | 2026-11-04 |
| #10613 | FIF member capture: bind issuer statement-title wording on the deep route, with a plain-income gate | 2026-11-03 |
| #10612 | fix(funds): retain original filing sources and holding drill paths | 2026-11-04 |
| #10610 | fix(news): disclose failed refresh while retaining source evidence | 2026-11-05 |
| #10607 | Restore retained Learning, Forex, Gold and Bio consumer workflows | 2026-11-03 |
| #10606 | agentos(mi-buildout): records 2026-11-02 — #9527/#9025 production proofs, #976 classified | 2026-11-02 |
| #10605 | P16.T1: preserve source identity clocks and evidence-cut links | 2026-11-02 |
| #10603 | fix(bonds): keep unavailable health scores distinct from zero | 2026-11-03 |
| #10601 | test(macro-command): heal ci-pack-6 — pin #policy freshness for M6 stance tests | 2026-11-02 |
| #10600 | P12: Close Shared Shell publication gates and source-owned catalog metadata | 2026-11-04 |
| #10599 | agentos(mi-buildout): records 2026-11-02 — W8 and W12 closed, NFLX live multi-report proof, listener self-cancel recurrence | 2026-11-02 |
| #10595 | FIF Q1: fourth held-out generation with the split-3 PK12 labels (A37, g4) | 2026-11-03 |
| #10594 | FIF publish: code R7 as a refusal and opt-in per-issuer exclusion of unpinned first-publication refusals | 2026-11-02 |
| #10593 | FIF A36: manifest journey cell from the A1 journey ledger and contract SIC basis (both optional) | 2026-11-03 |
| #10592 | Bind F06 screener valuations to the right listing and require stated, finite inputs | 2026-11-06 |
| #10591 | test(markets): model render-sync's CSS externalization in the byte guard | 2026-11-02 |
| #10590 | F06 screener: keep the next catalyst when an expired window is present | 2026-11-05 |
| #10589 | agentos(gmi): record PRODUCTION_PROOF of the GMI pages and the #10583 heal | 2026-11-02 |
| #10588 | FIF A36 deep: coverage writer strict and deep verdicts mirror the prover | 2026-11-02 |
| #10587 | FIF Q0: widen the pack quality report issuer enum to the split-decision-3 held-out issuers | 2026-11-02 |
| #10586 | FIF parser: iXBRL 1.1 spec-conformance widening (hidden footnotes, unreferenced footnotes, 256-link continuation chains) | 2026-11-02 |
| #10585 | reader fixes: Chinese early-reversal signals; CAGR-behind sentence names the trade | 2026-11-02 |
| #10583 | deploy(gmi): make gmi.css and gmi.js public so the open GMI shell renders styled | 2026-11-02 |
| #10581 | FIF A36: record the 2026-11-02 coverage remeasure on a fresh companyfacts pull (target not met) | 2026-11-02 |
| #10580 | ci-main-heartbeat: say what the heartbeat actually checks | 2026-11-08 |
| #10578 | agentos(grey-deer): records r6 — EW-P4-ACT #10394 and EW-P5 FU2 #10401 merged; EW-P1 first natural session | 2026-11-02 |
| #10577 | FIF packs: ship the PK10 and PK09 repairs with the A34 re-review record | 2026-11-02 |
| #10576 | fix(capital-structure): resolve each issuer from its own decisions | 2026-11-02 |
| #10575 | fix(capital-structure): candidates not yet visible at as_of are a typed unavailability, not a whole-run refusal | 2026-11-02 |
| #10574 | perf(capital-structure): read each candidate/term parquet once per nightly, not once per issuer | 2026-11-02 |
| #10573 | docs(capital-structure): Z0 closure map for V2 (masterplan #9115 §13 Z0) | 2026-11-02 |
| #10572 | FIF specialist packs: ship six reviewed repairs (PK03, PK04, PK07, PK08, PK11, PK12) | 2026-11-02 |
| #10571 | us_board ledger: roll snapshots.jsonl over to snapshots_parts/ before the 100 MiB limit | 2026-11-11 |
| #10570 | agentos(gmi): 2026-11-02 completion-ship checkpoint | 2026-11-02 |
| #10569 | feat(capital-structure): select FIF production datasets for the nightly inputs step (F0c) | 2026-11-02 |
| #10566 | FIF A36: record the 2026-11-02 coverage remeasure (target not met) | 2026-11-02 |
| #10564 | feat(capital-structure): bind financials from the existing FIF query service (F0b) | 2026-11-02 |
| #10563 | gmi coverage proof: owner-disposition contract (zero rows, owner null) | 2026-11-02 |
| #10558 | FIF PK02: enforce R-F1 unit equivalence on the axes resolver | 2026-11-02 |
| #10557 | fix(spr): date the US reserve figure and stop calling a weekly series live | 2026-11-02 |
| #10556 | gmi: S3 reads the relationship_edges/v1 envelope at display tier (248 proposed edges + page receipt) | 2026-11-02 |
| #10555 | fix(capital-structure): give the candidate compiler its source-store env | 2026-11-02 |
| #10554 | capital_structure P130: Exhibit 107 parser 1.3.0 closes the measured B/C/D refusals (45→62 of 99), reseal 315 | 2026-11-02 |
| #10552 | test(data-health): realign four suites with merged contracts (16 of 17 new reds) | 2026-11-02 |
| #10548 | fix(capital-structure): validate a published inputs bundle once, bind it per request (V0) | 2026-11-02 |
| #10547 | agentos(mi-buildout): records 2026-11-02 — R3 P2 polish shipped (terminal #1211) + spec §6 .change grant | 2026-11-02 |
| #10546 | capital_structure: shed rows to fit the section budget; withheld page is a loud ::error | 2026-11-02 |
| #10545 | FIF A36: wire governed not-presented rules into the coverage writer (--np-linkbases) | 2026-11-02 |
| #10543 | feat(cs-v2-n0): typed capital-structure context leg in the integrated answer | 2026-11-02 |
| #10541 | fix(gmi-explorer): read the v1 relationship-edges envelope as no edges; clear main's CI baseline | 2026-11-02 |
| #10536 | agentos(news-estate): ninth handoff write — S15 and the seven §9.1 proof PRs reviewed and armed | 2026-11-03 |
| #10535 | capital_structure A1-1: served active pair + branch-bound boundary; monitor records only outbox-proven firings | 2026-11-02 |
| #10534 | fix(sector-cycles): stop calling a projected month already gone the next turn | 2026-11-02 |
| #10533 | fix(cycle-pages): tell a reader without access that the page is for members | 2026-11-02 |
| #10531 | FIF held-out wave 3: PK12 labels for the 18 admitted split-decision-3 filings (independent labeler) | 2026-11-02 |
| #10530 | gmi: O5 verification verdicts + --activity-proposals double-count fix (G-UI-8) | 2026-11-02 |
| #10529 | FIF: filing-catalog client follow-up (failed-request retry, prime reset guard, transition reports) | 2026-11-02 |
| #10527 | feat(cs-v2-u1c): real Exhibit 107 fee terms sealed into served state | 2026-11-02 |
| #10524 | agentos: record the VPS Macro git store kept tier, nightly repack and pull guard | 2026-11-02 |
| #10523 | FIF FF: contract issuers CIK dedupe + limited-check action copy (#10404 contract follow-up) | 2026-11-02 |
| #10520 | feat(nav): GMI Explorer joins the Research mega-menu (Find the Edge) | 2026-11-02 |
| #10519 | fix(releases): honor report cooldowns and retain the CPI archive after a feed-only detection | 2026-11-02 |
| #10518 | crypto(p0b): accept P0B on live 2026-10-31 as-of; OI percentile uses the canonical ordinal twin | 2026-11-02 |
| #10517 | docs(dataos): R03 second-cycle read-back — sidecar on main, history price-identical, findings routed | 2026-11-02 |
| #10516 | GLT T22: progressive views (conditional outlook, statistical forecast disposition, transmission, repricing evidence, source-known replay) on the liquidity and central banks workspace | 2026-11-03 |
| #10514 | agentos(mi-buildout): records 2026-11-02 (R3 rail merged, deployed and proven live) | 2026-11-02 |
| #10506 | V91 V6: offline proof of the user research workflow row, signed-in step at HUMAN_GATE (masterplan 9.1) | 2026-11-04 |
| #10505 | V91 V4: committed-artifact proof of the policy or supply-chain event row (masterplan 9.1) | 2026-11-04 |
| #10504 | V91 V1: committed-artifact proof of the macro release and revision row (masterplan 9.1) | 2026-11-04 |
| #10502 | FIF PK01: covenant span repairs after independent dev-corpus reviews | 2026-11-02 |
| #10500 | research(news-r3): spec §1 amendment — light --warn carve-out not shipped (D-W1), step-only ladder underline | 2026-11-02 |
| #10499 | Products and Learn hubs: count the records, date them, drop the real-time claim | 2026-11-02 |
| #10497 | News V91 V7: quiet source, outage and rights-loss proof (offline fixture) | 2026-11-04 |
| #10495 | V91 V2: earnings and guidance vertical proof (offline fixture) | 2026-11-04 |
| #10492 | fix(market-memory): say available now and prediction, not live and forecast | 2026-11-02 |
| #10491 | V91 V3: offline proof of masterplan 9.1 row (Capital allocation or major contract) | 2026-11-04 |
| #10490 | Design the Dark Pool session research desk and verify the interactive reference | 2026-11-08 |
| #10488 | V91 V5: offline proof of the rumor, denial and confirmation row (masterplan 9.1) | 2026-11-04 |
| #10487 | docs(agentos): preserve current-source News continuation decision | 2026-11-02 |
| #10484 | fix(access): suppress paywall flash while account session restores | 2026-11-07 |
| #10482 | company-intelligence: register the relationship suites (A25), registry rows (A26), F-03 envelope DEC — GMI ORCH-REL integration | 2026-11-02 |
| #10481 | qledger carve restore: never destroy surviving bytes on a failed snapshot read (#9556 post-merge findings) | 2026-11-02 |
| #10480 | F2 M07b: validator rule S15 — a quantity period must be able to evidence its claim slot | 2026-11-02 |
| #10479 | agentos(mi-buildout): records 2026-11-01 (R2 rail shipped and proven, L4 unblocked, R3 spec frozen) | 2026-11-02 |
| #10478 | agentos: news estate records r7 — eighth write + seat e3d62d36 takeover | 2026-11-02 |
| #10477 | fix(sector-cycles): say when the turn hazard is withheld and why | 2026-11-02 |
| #10476 | FIF PK04: value rpo_total from a single period-adjacent typed-axis aggregate | 2026-11-02 |
| #10474 | fix(sector-cycles): on a phone, keep every cycle view on screen and every card readable | 2026-11-02 |
| #10473 | FIF Q0 conformance: admit pack-scoped split cohorts from the held-out contract | 2026-11-02 |
| #10472 | FIF PK09: repair auditor-opinion, auditor-firm and ICFR conclusion resolution (dev corpora) | 2026-11-02 |
| #10470 | fix(landing): Prophet tag says winners only and stops promising two weeks | 2026-11-02 |
| #10469 | agentos: FIF 2026-11-01 dev-corpus repair wave, split decision 3, pin re-record ruling | 2026-11-01 |
| #10467 | FIF PK02: take the cash-flow share-based compensation total first (dev corpora diversified_v1, litigation_v1) | 2026-11-02 |
| #10466 | docs(agentos): record catalyst A3 merge and production writer proof | 2026-11-01 |
| #10465 | FIF PK01: value covenant_term_observation from the debt note text span (dev corpus diversified_v1) | 2026-11-02 |
| #10464 | FIF held-out: split decision 3 predeclared rows + wave-3 digest-only packages (18 of 24 admitted) | 2026-11-02 |
| #10463 | FIF PK07: repair business-combination consideration and acquisition-date resolution (dev corpus diversified_v1) | 2026-11-01 |
| #10462 | fix(start): say on each market card how the read is moving, as of when, and name the page clock | 2026-11-02 |
| #10461 | FIF PK05: pin the verified uncertain-tax-position rollforward resolution (dev corpus diversified_v1) | 2026-11-02 |
| #10460 | ci(admin): a public link to an admin-only page fails before merge | 2026-11-02 |
| #10459 | fix(research-vault): say when the saved copy was written and how new its newest report is | 2026-11-01 |
| #10458 | FIF PK12: resolve stock-plan equity issuance in biotech financing (dev corpus biotech_v1) | 2026-11-01 |
| #10456 | fix(heatmap): the China pulse says which line is the whole board and which is this map | 2026-11-01 |
| #10455 | fix(special-situations): the heading names the list's date and the count says what it compares | 2026-11-01 |
| #10454 | fix(etfs): each fund chip names its last holdings date, and the clock says page built | 2026-11-01 |
| #10453 | Agent OS: FIF Q0 split decision 3 — predeclared PK12 biotech held-out cohort | 2026-11-01 |
| #10451 | FIF PK03: repair segment, geographic and product revenue resolution (dev corpus diversified_v1) | 2026-11-01 |
| #10450 | ci(boundary): the site access boundary suite runs on the merge gate | 2026-11-01 |
| #10449 | fix(sector): XLY and XLB open their basket pages, and a basket's fund opens its sector page | 2026-11-01 |
| #10448 | fix(sector-cycles): one dated sentence on the turn record under the US cards, not a count per card | 2026-11-02 |
| #10447 | fix(sector-cycles): the hazard tooltip says what the figure is in the reader's language | 2026-11-01 |
| #10446 | fix(prophet): a free reader is told a locked plan record exists, not its id and dates | 2026-11-01 |
| #10445 | FIF PK11: resolve disclosed capital ratios and credit-loss aliases (dev corpus banks_v1) | 2026-11-01 |
| #10444 | fix(sector-central): a tape file past 12 hours names the day it stopped | 2026-11-01 |
| #10443 | feat(themes): let a theme card open the companies behind it | 2026-11-01 |
| #10442 | fix(macro-suite): stop calling a later reference period a republication | 2026-11-01 |
| #10441 | fix(macro-suite): print the claims cards' previous reading | 2026-11-01 |
| #10440 | FIF dev corpus: disjoint-issuer bank corpus instrument + digest-only manifest (banks_v1) | 2026-11-01 |
| #10439 | fix(macro-suite): name the trade page's drivers for what they hold | 2026-11-01 |
| #10438 | fix(macro-suite): say which way Treasury cash moves bank reserves | 2026-11-01 |
| #10437 | fix(sector-cycles): print the as-of date, say the RS rank is rebuilt | 2026-11-01 |
| #10436 | FIF Q0: counts-only label-conformance gate for held-out splits (pre-seal) | 2026-11-01 |
| #10435 | FIF data: append companyfacts period_start to statements_quarterly (A44 exact-start binding) | 2026-11-01 |
| #10434 | fix(capital-structure): link the featured deal's company, drop a banned word | 2026-11-01 |
| #10433 | fix(fundamental-forensics): date the coverage sentence | 2026-11-01 |
| #10431 | fix(international-macro): give each country page a door to its own names | 2026-11-01 |
| #10430 | FIF A37: g3 family diagnosis — PK11 recall defect, PK12 non-conforming label set | 2026-11-01 |
| #10429 | fix(btc-alerts): print a leg the radar's re-check has not passed as background, not act | 2026-11-01 |
| #10428 | fix(cycle): stop calling the measured cards live | 2026-11-01 |
| #10427 | fix(subsectors): stop calling a dated board realtime in Chinese | 2026-11-01 |
| #10426 | fix(subsectors-china): print the two stored break checks with their dates | 2026-11-01 |
| #10425 | fix(leader-radar): name the clocks older than the price date | 2026-11-01 |
| #10424 | ci(heartbeat): stop guard jobs being cancelled by their own checkout | 2026-11-01 |
| #10423 | fix(us-board): stop the grader dying on a stored value the fresh column cannot hold | 2026-11-01 |
| #10422 | FIF A34: count a held-out proof only when Q1 measured it | 2026-11-01 |
| #10421 | fix(macro-suite): say how few recessions the catch rate rests on | 2026-11-01 |
| #10420 | ci(data-health): say when no data test ran, and let two jobs finish | 2026-11-02 |
| #10419 | fix(commodities): call the price lamps last, not live | 2026-11-01 |
| #10418 | ci(qledger): carve the ledger from the White House sentinel, weekly and backfill | 2026-11-01 |
| #10417 | chore(contracts): regenerate artifact_manifest.json from the generator | 2026-11-01 |
| #10416 | fix(test): pin the XLU price-basis test at a cut date | 2026-11-01 |
| #10415 | FIF page: bind compare and finding source links to their own period | 2026-11-01 |
| #10414 | fix(ci): compile the dashboard once in the EW-P4 suite so the render job fits its limit | 2026-11-01 |
| #10413 | fix(macro-suite): name a late source apart from a broken one | 2026-11-01 |
| #10412 | fix(ci): fund the two tier-gate split jobs on the packing probes (main red since #10294) | 2026-11-01 |
| #10411 | F2 M04: the producer grounds every stated quantity in its cited source bytes | 2026-11-01 |
| #10410 | FIF page: show negated-label statement lines with the filing's sign | 2026-11-01 |
| #10408 | FIF Z0 matrix: close A23 (saved research) and A21 (live observation) | 2026-11-01 |
| #10407 | FIF (d): list coverage-contract issuers missing from the broad panel (SNOW) | 2026-11-02 |
| #10406 | fix(site-shim): clear the four data-base shim guard reds | 2026-11-01 |
| #10405 | news-impact: validator refuses fold-split role markers and control-split schemes (F2 NOTE-A) | 2026-11-01 |
| #10404 | FIF: generation statement catalog route + served-filing page fixes (a/b/e/f) | 2026-11-02 |
| #10403 | fix(tests): point the paywall denial test at a page that is still premium | 2026-11-01 |
| #10402 | fix(btc-alerts): drop "Holdout-validated"/"经验证" from the impulse alert copy | 2026-11-01 |
| #10401 | fix(rotation): EW-P5 FU2 — design review repairs for the rotation observation glance | 2026-11-02 |
| #10400 | FIF Q1: third held-out generation (A37, g3 reports) | 2026-11-01 |
| #10392 | FIF Z0 A23: saved research cannot alter canonical facts | 2026-11-01 |
| #10399 | docs(intl-gs): records r11 — r10 merged, §14 row 19 DONE on the unrelated render (18/3/0), dislocation job re-measure | 2026-11-01 |
| #10391 | test(institutional-census): pin the Atom acceptance-clock refusal and enrol the 13F ingestion suites | 2026-11-08 |
| #10390 | research(options-intelligence): sealed OIF P1-P6 family preregistration (S0, AC28-AC35) [DRAFT] | 2026-11-03 |
| #10388 | docs(intl-gs): records r10 — F10 / hygiene / R2-01 merged, served row-21 pack, §14 17/4/0 | 2026-11-01 |
| #10398 | news-impact(thesis): fingerprint carries quantity terms so a unit change is a revision (F2 B2 / M05) | 2026-11-01 |
| #10387 | FIF Z0 records: close A24, A38, A52, A49 and A50; narrow A23 | 2026-11-01 |
| #10386 | news contract: flag provider stamps that postdate their own receipt (F2 T15) | 2026-11-01 |
| #10385 | prophet(us): word a candidate's "Why it is here" exactly as its row does (J11 journey law) + R7 US journey trace | 2026-11-02 |
| #10397 | research(options-intelligence): ORCH-2 product/integration census + Journey A entitled-render checklist | 2026-11-03 |
| #10396 | FIF Z0 A21: pin the two untested withheld rows; record the live cycles | 2026-11-01 |
| #10395 | research(options-intelligence): source/research census + Theta coverage + AC24 attrition receipts (records) | 2026-11-01 |
| #10384 | evidence(intl-gs): R2-01 — scanner-abstain focus-state cells (W2A review NIT closed) | 2026-11-01 |
| #10394 | feat(rotation): EW-P4-ACT gated latest-observation producer, point-in-time envelope lift and O06 receipt rule | 2026-11-02 |
| #10383 | docs(agentos): record tested Fabric graph candidate and review gate | 2026-11-05 |
| #10382 | FIF held-out wave 2: labeler batch four (PK09) — independent lane commit carried unchanged | 2026-11-01 |
| #10393 | news(F2 B4/R15): source_count counts information origins, not publishers | 2026-11-01 |
| #10380 | FIF Z0 records: close A12, A33, A47 and A53 on evidence already on main | 2026-11-01 |
| #10379 | Marketing X Catalyst: SEC rights decision D1–D5, live SEC source (A3), carried gaps | 2026-11-01 |
| #10378 | news velocity F2 B3: count a report only once the store held it (T04 possession bound) | 2026-11-01 |
| #10377 | fix(ci): use exact tested base for ruling-graph without redundant Git refetch | 2026-11-02 |
| #10376 | test(ci-pack): F10 AUDIT-2 nits N5/N6 — isolate TESTED_TREE_SHA between tests; prove execute_pack publishes the plan tree (re-home of #10370) | 2026-11-01 |
| #10375 | agentos: record the 10-31 VPS root-disk refill, the shallow-root pin and the quote-hub syslog flood | 2026-11-01 |
| #10374 | agentos(market-os): signed-in beta proof for Today since-last-visit (r7) | 2026-11-02 |
| #10373 | records(grey-deer): EW records r5 - EW-P4-FU merged, first EW-P5 pack census | 2026-11-01 |
| #10372 | news-impact: F2 repairs — one-sign amounts, no unit scale inference, NFKC injection guard, rating-phrase refusal (M06a/M06b/M01c/M11) | 2026-11-01 |
| #10371 | fix(risk-envelope): a same-session settled copy must qualify before it suppresses the live overlay (EW-P5 S02/S12) | 2026-11-01 |
| #10369 | research(news-estate): §9.1 vertical proof readiness map (seven verticals, evidence only) | 2026-11-01 |
| #10368 | docs(intl-gs): records r9 — pin1 served (row 4 production proof in full), r8 merge, review nits, F10 state | 2026-11-01 |
| #10367 | ci(legacy-jobs): F10 — international-dislocation-explorer acquires canonical main through prepare_canonical_main | 2026-11-01 |
| #10366 | research(news-estate): F2 negative controls — 7 BROKEN, 5 NO_MECHANISM across time, rights and model context | 2026-11-01 |
| #10364 | ui(risk-radar): EW-P4-FU — the UI validator rejects what the lib validator rejects | 2026-11-01 |
| #10362 | docs(intl-gs): records r8 (§14 closure + gb1/pin1 + Agent OS) | 2026-11-01 |
| #10361 | agentos(news-estate): records r6 — #10351 merged; W3 F2 negative-control lanes commissioned | 2026-11-01 |
| #10360 | agentos(fif): wave-two labels, generation-pin repair and the PK09 capacity wait | 2026-11-01 |
| #10359 | fix(f07): keep invalid valuation inputs out of scenario outputs | 2026-11-07 |
| #10358 | agentos(market-os): slice 1 merged (Terminal db6168c2); beta release by receiver seat (r6) | 2026-11-01 |
| #10357 | agentos(grey-deer-ew): records r4 - EW-P4 #10350 merged, EW-P4-FU, EW-P5 receipts | 2026-11-01 |
| #10356 | fix(forex): fail closed on malformed and duplicated R4 currency rows | 2026-11-03 |
| #10355 | feat(intl-gs): pin1 polish — chip in head row, W2A CSS pin, specimen-scan defaults | 2026-11-01 |
| #10354 | feat(intl-gs): W2B dossier graph-boundary label (gb1) | 2026-11-01 |
| #10353 | docs(intl-gs): records r7 (census + checkpoints + Agent OS) | 2026-10-31 |
| #10352 | agentos(news-estate): records r5 — F1 merged (#10348), E4 census repaired and re-reviewed (#10351 open) | 2026-11-01 |
| #10351 | research(news-estate): W4 E4 Brief binding census (B1-B6 mechanism inventory; all four P1-B bindings PARTIAL at HEAD; no design) | 2026-11-01 |
| #10350 | ui(risk-radar): EW-P4 — comprehensible descriptive early-warning observation in the Radar inset and Sector Central (product A; no forecast, no delivery) | 2026-11-01 |
| #10349 | agentos(marketing-x): Catalyst Loop records after #10257 merge — waves done, SHIP rung, seat handoff | 2026-11-01 |
| #10348 | research(news-estate): W3 F1 claim/evidence denominator matrix (18 segments x 5 rungs; honest negatives) | 2026-10-31 |
| #10347 | agentos(news-estate): W3 Section C censuses merged (#10344); review chain + capacity facts | 2026-10-31 |
| #10346 | records(grey-deer): EW-P3 prereg dated + registered (merge 2026-10-31, start 2026-11-02), budgets 3+3 appended, EW-P1 superseded by #10255, wave states | 2026-10-31 |
| #10345 | FIF Q1: generation pins fail closed when a report records no evaluated_at | 2026-11-01 |
| #10344 | research(news-estate): W3 Section C censuses — C1 exposure joins, C3 F05 consequence delivery | 2026-10-31 |
| #10343 | FIF held-out wave 2: labeler batch three (PK07, PK08, PK11, PK12) — independent lane commits carried unchanged | 2026-10-31 |
| #10342 | FIF Q1: generation report pins account the label universe the generation recorded (later labeling waves no longer red earlier generations) | 2026-10-31 |
| #10341 | ci(legacy-jobs): raise international-dislocation-explorer budget 8 -> 15 min (PR-side canonical-base fetch; unblocks full-suite packs) | 2026-10-31 |
| #10340 | research(grey-deer): EW-P3 — claim-to-evidence contract v1 and one preregistered candidate (product B; no outcomes read) | 2026-10-31 |
| #10339 | agentos(news-estate): ORCH-3 reviewed + #10338, ORCH-4 Journey 6 merged (#1196), Chairman disk law recorded | 2026-10-31 |
| #10338 | [news-estate ORCH-3] B4 gated_v3 adjudication: quant claim matrix (DEFENSIBLE_NEGATIVE), sampler startup pin, 40 NEW-case routing, provenance (RECONSTRUCTION) | 2026-10-31 |
| #10337 | FIF held-out wave 2: labels batch two (PK04, PK05, PK06) from independent labeler lanes | 2026-11-01 |
| #10336 | FIF held-out wave 2: labels batch one (PK01, PK02, PK03) from independent labeler lanes | 2026-10-31 |
| #10335 | Agent OS: FIF wave-two capture + envelope-repair handoff and post-wave-two ladder | 2026-10-31 |
| #10334 | agentos(news-estate): Wave 1 landed, D2 producer merged, ORCH-3 seat-direct on the fabric | 2026-10-31 |
| #10332 | FIF Q1: second held-out generation after the SIC-binding and nil-fact kernel repairs (A37, reports q1_held_out_20261031_g2) | 2026-10-31 |
| #10331 | research(options): compose synthetic American-put scenarios without production adoption | 2026-11-04 |
| #10330 | fix(seasonality): let the now chip wrap on a phone so its caveat stays visible | 2026-11-01 |
| #10329 | fix(strategies): say why the book weight differs from the score's band | 2026-11-01 |
| #10328 | docs(grey-deer): EW records r2 — EW-P0 merged, EW-P2 draft #10325 awaiting CI, EW-P3 contract in flight, run 41156792292 engine CANCELLED | 2026-10-31 |
| #10327 | fix(sector): say how many holdings the panel shows and their share of the fund | 2026-11-02 |
| #10326 | fix(strategies): make the strategy note agree with the page's own tiles | 2026-11-02 |
| #10325 | rotation: EW-P2 — rotation observation continuity: successor of #10104 rebased onto main (dormant, default-off) | 2026-10-31 |
| #10324 | fix(cycles): name the session a same-day cross printed on | 2026-11-02 |
| #10323 | fix(foresight): name the rule behind a theme's next comment close | 2026-11-01 |
| #10322 | FIF held-out: wave-2 digest-only packages for the 45 split-decision-2 accessions (DEC:FIF-Q0-SPLIT-DECISION-2-SECOND-LABELING-WAVE-20261031) | 2026-10-31 |
| #10321 | fix(commodities): name what the oil strategies actually use | 2026-11-01 |
| #10320 | fix(ai-desk): show directional accuracy beside each call type's holding rate | 2026-11-01 |
| #10319 | fix(cycles): drop the unmeasured failed-cycle rate | 2026-11-02 |
| #10318 | fix(help): send scorecard links to the page readers can open | 2026-11-01 |
| #10317 | fix(china): replace "validated" with what the study measured | 2026-11-01 |
| #10316 | FIF Q1 evaluator: envelope sic_source follows the production resolver vocabulary; binding route stays in the report note | 2026-10-31 |
| #10315 | fix(macro-suite): date the What changed comparison | 2026-11-01 |
| #10314 | FIF A34: regenerate the pack-proof ledger on current main (PK09 gold calibration tests 41 -> 45) | 2026-10-31 |
| #10313 | Agent OS: FIF Q1 held-out wave — six decisions, workstream update and the 2026-10-31 handoff | 2026-10-31 |
| #10312 | FIF held-out: predeclared split-row admission for the capture script and the split-decision-2 contract rows | 2026-10-31 |
| #10311 | FIF kernel: tolerate inert attributes on nil numeric facts in the SEC filing parser (DEC:FIF-PARSER-NIL-FACT-INERT-ATTRIBUTES-TOLERATED-20261031) | 2026-10-31 |
| #10310 | FIF Q1: evaluator binds issuer SIC from the held-out contract and surfaces duplicate targets (E1-3) | 2026-10-31 |
| #10309 | fix(contracts): declare the new board and plan-book fields | 2026-10-31 |
| #10308 | fix(ci): fetch the commit the red-first proof reads | 2026-11-01 |
| #10306 | fix(copy): drop the unearned word from the commodity name stamp | 2026-10-31 |
| #10305 | fix(tests): count the two ways a sheet is reached without a link | 2026-10-31 |
| #10304 | fix(tests): re-pin the US tech merge order after #8708 | 2026-10-31 |
| #10303 | fix(ci): give the heartbeat template-site-sync lane jinja2 | 2026-10-31 |
| #10302 | c19(wp31): prereg §10 A5 — the submissions clock is true UTC | 2026-11-01 |
| #10301 | fix(us-board): print no paid name on the free shell | 2026-10-31 |
| #10300 | fix(sector-holdings): publish JSON atomically so interrupted writes preserve last good feed | 2026-11-02 |
| #10299 | FIF A37: Q1 held-out re-adjudication record — all twelve packs unavailable_research_only (2026-10-31) | 2026-10-31 |
| #10298 | FIF PK09: follow-up bundle — mapping_rule_id parity, cap re-enforcement, anaphoric/fiscal tests (reviews F5-3/F5-4/F6-1..3) | 2026-10-31 |
| #10297 | agentos(c19): record the 2026-10-31 seat takeover and W15 wave | 2026-10-31 |
| #10296 | intl-gs W5 hardening: kill surviving review mutants (test-only, DEFERRED F7) | 2026-10-31 |
| #10294 | CI: give the paywall boundary suites their own jobs so a tier-preview red can't hide them | 2026-11-01 |
| #10293 | FIF Q1: independent held-out evaluation of the labelled specialist packs (A37, reports q1_held_out_20261031) | 2026-10-31 |
| #10292 | fix(tests): count locked China names, not rows, in the shell check | 2026-10-31 |
| #10291 | fix(site): stop public pages sending readers to admin-only pages | 2026-10-31 |
| #10290 | Sector Central: say what orders the board when fast ranks are stale | 2026-10-31 |
| #10288 | feat(intl-gs): IM13 global scanner + coverage view (Wave 2) | 2026-10-31 |
| #10286 | intl-gs §14 closures: graph-boundary label rule, cross-surface identity test, legacy continuity evidence | 2026-10-31 |
| #10285 | fix(options): report archive outcomes and guard dated corrections | 2026-11-02 |
| #10284 | c19(wp31): report the cause behind NOT_EVALUABLE counts; close #10074 review notes | 2026-11-01 |
| #10283 | entry-timing-w2: frozen discovery vs curated-admission timing design (pre-outcome) | 2026-11-01 |
| #10281 | agentos(news-estate): D2 consumer ruling + ORCH-2 return consumed | 2026-10-31 |
| #10280 | feat(news): stamp source_asof and the retained flag on by_ticker.json (News D2 producer) | 2026-10-31 |
| #10279 | fix(radar): make the open-checks copy match the record and the grader | 2026-10-31 |
| #10278 | feat(intl-gs): IM14 market dossier (Wave 2) | 2026-10-31 |
| #10276 | intl-gs W5 E3: correction receipts and dependent invalidation engine (§14 row 16) | 2026-10-31 |
| #10275 | intl-gs W5 E1: point-in-time replay builder engine (IM18 engine half) | 2026-10-31 |
| #10274 | intl-gs W5 E2: GS-local watch-condition evaluator engine (IM18 engine half) | 2026-10-31 |
| #10273 | test(c19): WP28 capital-structure leg identity pins (offline, code-gated) | 2026-11-01 |
| #10272 | FIF PK09: remediation-timing semantics for material_weakness_present (B.3 v6, review F4-1..F4-4) | 2026-10-31 |
| #10271 | FIF PK08: word-boundary span for determine-losses + arm comment correction (F3-2) | 2026-10-31 |
| #10270 | fix(research): escape the hub date, say no summary exists, strict top_pick | 2026-10-31 |
| #10269 | Commodities: show world production and US import sources for critical minerals | 2026-10-31 |
| #10268 | Clear stale PLNT registry and SEO rows; one ruling label | 2026-10-31 |
| #10267 | prophet-b4: bind the capture's alias seam to the Data OS identity reader | 2026-10-31 |
| #10266 | agentos(prophet-v4): Fable CEO checkpoint 2026-10-31 — curated-tier outage, PR #10255, B4 seam census | 2026-11-05 |
| #10265 | feat(intl): dislocation explorer UI from the IM15 contract (W3U) | 2026-10-31 |
| #10264 | Bind synthetic codegen observations and prospective evidence proposals | 2026-11-08 |
| #10263 | FIF A37: held-out labels L-B (PK02, PK03, PK04, PK05) sealed by an independent labeler lane | 2026-10-31 |
| #10262 | Leader Radar: ticker links open the stock page; recovery rows show prior runs | 2026-10-31 |
| #10260 | FIF A37: held-out labels L-C (PK07, PK08, PK12) sealed by an independent labeler lane | 2026-10-31 |
| #10259 | fix(commodities): refuse a zero US aggregate stock instead of publishing 0.0 Mb (C19 WP26) | 2026-10-31 |
| #10258 | feat(intl): transmission board UI from the IM17 contract (IM17 W4B) | 2026-10-31 |
| #10257 | Marketing X: Catalyst Loop engine — A1 integration, A2/B witnesses, C1 asset factory, rights request | 2026-10-31 |
| #10256 | [V4-A2] Consume public settlement evidence in existing nightly Check E | 2026-11-08 |
| #10255 | fix(daily): carve the oversize qledger ledger out of every wholesale nightly commit (engine, collect_tail, stock_briefs) | 2026-11-01 |
| #10254 | agentos(news-estate): Fable takeover 2026-10-31 + DEC:NEWS-ESTATE-B1-JOINS | 2026-10-31 |
| #10253 | FIF records: 2026-10-31 resumption wave handoff + two durable seat rulings | 2026-10-31 |
| #10252 | White House: link names to the stock page; calibration hub copy | 2026-10-31 |
| #10251 | agentos: DSC an offloaded self-updating clone freezes silently under launchd | 2026-10-31 |
| #10250 | agentos(chart-engine): Q03b v4 official receipt PASS lifts the P03 hold | 2026-10-31 |
| #10249 | docs(grey-deer): EW-P0 — adopt the 2026-10-31 Chairman early-warning packet as an amendment to #10219; Fable CEO takeover record | 2026-10-31 |
| #10248 | feat(options): options_capability_manifest/v0 pure read-time adapter (OPT-011 v0) | 2026-10-31 |
| #10247 | fix(ontology): distinguish hidden observations from native verdicts | 2026-10-31 |
| #10246 | FIF PK08: object-bound not-possible-to-determine form (review note F3-1) | 2026-10-31 |
| #10245 | docs(alpha): census and flexible Fable integration masterplan | 2026-11-08 |
| #10244 | docs: news intelligence completion census and Fable design continuation | 2026-11-08 |
| #10243 | Finance Intelligence: an honest unbuilt page, no synthetic constants (Ruling F-5) | 2026-10-31 |
| #10242 | Prophet US V4 / Entry Timing — October 31 completion plan and Fable source census | 2026-11-08 |
| #10239 | agentos: Market OS flagship receiver takeover and first vertical wave | 2026-10-31 |
| #10238 | fix(p0b): pin Chromium and fonts so the browser receipts reproduce across hosts | 2026-10-31 |
| #10237 | Hold the synthetic PLNT card from the public site | 2026-10-31 |
| #10234 | feat(ai-desk): split the track record by regime and put the badge in words (W35-LB) | 2026-10-31 |
| #10233 | agentos(exec-ecosystem): 80f384b8 canary overtaken — host on f572, handed to root 01a15741 | 2026-10-31 |
| #10232 | feat(radar): show what would break each of today's reads (W35-LA) | 2026-10-31 |
| #10231 | docs(grey-deer): close GD-PB-W5 (#9128) at PRODUCTION_PROOF in the workstream record | 2026-10-31 |
| #10230 | docs(market-os): flagship audit and open Fable delivery charter | 2026-10-31 |
| #10228 | agentos: close WS-TERMINAL-ENHANCEMENTS20 (trains 5-6, E11 lineage pass, review folded) | 2026-10-31 |
| #10227 | Breadth: qualify intraday source observations per cohort member | 2026-11-07 |
| #10226 | fix(F09): compose filer-state truth with protected ledger persistence | 2026-11-09 |
| #10225 | feat(entry-radar): RS Leadership Suite v2.2 and native first-green comparisons | 2026-11-08 |
| #10222 | docs(agentos): preserve Secretary convergence history in existing R2 record | 2026-11-08 |
| #10219 | [CEO] Grey Deer × Rotation early-warning recovery and delivery increment | 2026-11-08 |
| #10218 | research(rotation): preserve the October pre-event signal audit | 2026-11-06 |
| #10217 | fix(F11): qualify finite thesis-condition inputs [P17.T15] | 2026-11-07 |
| #10216 | research: preregister 2H/3H RS-leader oscillator swing hypotheses (no outcome reveal) | 2026-11-08 |
| #10210 | fix(calculators): fence compounding copy feedback to result lifetime | 2026-11-04 |
| #10209 | [PROPHET V4-A2] Genuine UTC compute clock at private index writer | 2026-11-08 |
| #10207 | fix(alerts): preserve unavailable watchlist and store-probe truth | 2026-11-07 |
| #10206 | docs(ontology): reconcile two F04 consumers without capability promotion | 2026-11-07 |
| #10205 | fix(ontology): bind event research to its captured cutoff | 2026-11-06 |
| #10201 | [DRAFT] Measure Options Flow per-expiration latency without changing acquisition | 2026-11-06 |
| #10194 | fix(aibrief): recompute upcoming-release countdown at render date | 2026-10-31 |
| #10193 | fix(sector-holdings): guard weight contract before replacing feed | 2026-10-31 |
| #10192 | F09: require known filer identity for ownership flips | 2026-11-09 |
| #10191 | fix(ontology): accept native UTC company master timestamps | 2026-10-29 |
| #10190 | docs(agentos): correct Research Factory completed receipt frontier | 2026-11-06 |
| #10188 | fix(stock-identity): project inputs before reads and honor prior-bar registration | 2026-11-08 |
| #10184 | P1.T5 retain safe selected SEC publication metadata | 2026-10-30 |
| #10183 | Preserve prospective WTI adapter temporal context | 2026-10-29 |
| #10181 | fix(agentos): deliver complete compact recovery context and reconcile continuity | 2026-11-03 |
| #10180 | Prophet B2: recover B-17 frozen inputs and bounded cutoff replay | 2026-11-08 |
| #10174 | Prophet V4 recovery: wave census and B17 frozen-input handoff | 2026-11-08 |
| #10168 | docs(eval-os): audit canonical waves, separate R1 and record A1 execution | 2026-11-08 |
| #10166 | fix(metabolism-gc): fail closed on uncertain worktree deletion | 2026-11-08 |
| #10151 | Restore bounded active-build collection for oversized PRs | 2026-11-02 |
| #10099 | GMI explorer: S1–S5 pages (map, index, issuer, relationships, coverage, states) | 2026-11-02 |
| #10096 | docs(systematic): end-to-end strategy research masterplan, contracts and real-data qualification | 2026-11-06 |
| #10095 | systematic input qualification bridge (Macro #10089 P3) | 2026-11-08 |
| #10094 | fix(signals): fail before output writes on ticker computation errors | 2026-11-08 |
| #10077 | feat(nav): Expectation Surface row in the Research mega-menu | 2026-11-02 |

---

Before proposing or adjudicating new work: check your topic against the open-PR lanes above AND against `research/DO_NOT_REBUILD.md` (standing kills/forbidden designs).
