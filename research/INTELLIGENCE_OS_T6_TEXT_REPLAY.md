# T6 adjudicated text replay tranche

The existing `engine.neuralweb.response_eval.run_benchmark` now accepts two additional frozen cases: `benchmark_gold_real_rate_2026-08-09.json` and `benchmark_capex_bind_2026-07-22.json`. The original bear-steepener case is unchanged.

Gold supplies only driver and chain diagnostics from the ratified gold/real-rate case study: the real-yield high, a lagging chain gate, and the declining 22-day changes. The expected reading distinguishes instrument failure from falsification of a market thesis and keeps a forming peak conditional. No Prophet ledger or outcome input is included.

Capex supplies the adjudicated July 22 after-hours text about short-horizon bullish crosses, the hostile weekly regime, dispersion and the capex-guidance reaction. The expected reading reconciles horizons and member hypotheses without inferring a certain cause or a monolithic trade. July 23 is outside the input.

These are supplied-text cases replayed under current doctrine. Their historical source availability is explicitly unverified. A date cutoff is not an invented intraday publication time. Per-fact date guards validate the declared chronology; the main-loop adjudication remains responsible for the text's meaning and expected reading.

Before any callback, each case must bind its admitted canonical research document's full bytes, exact source and adjudication excerpts, hashes, declared dates and the assembled input packet. Reads are bounded to 64KiB regular files at the two explicit research paths. Missing, moving, oversized or special files fail closed. Both answer and judge must be explicit callables; these cases never fall back to the legacy paid/live model defaults, including when their metadata is absent or malformed. The old bear case retains its existing behavior.

The final affected suite passes96tests with no failures/errors/skips, and an independent scientific review accepted the sources and limits. Injected answer/judge tests prove the runner and fixture plumbing, not model reasoning performance. Output remains internal QA telemetry under the incumbent prohibition on publishing scores, pass rates or validation badges.

This is a two-case tranche, not completion of the original twenty-case / at-least-fifteen-seeded requirement or a reconstruction of actually served historical PIT inputs. Source review, hosted CI coverage, protected delivery, semantic model acceptance and actual consumer use remain distinct. See `research/evidence/eval-os-tier-query-20261014/t6-acceptance.json`.
