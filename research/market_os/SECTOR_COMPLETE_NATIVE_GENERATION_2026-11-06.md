# Complete native Sector generation: core, history, Brief and board

Status: parent source qualification in PR10780; no runtime or beta activation. Base: `f1023db10c4a0851a9d76a249470be5e856aeb29`. Governing mission: https://github.com/mastermindx-market-intelligence/macro/issues/10779.

## One authorized representation

`engine/sector_native_view.py::project_sector_view` now adds `data.core` and `data.history` to the existing `sector_native_view.v1` representation. The existing authorized-content hash covers all four sections. The five captured source artifacts, one selected-generation facade, receipt, auth gates and 4MiB whole-response encoder remain the owners of coherence and access. There is no extra resolver, cache, calculation, timer or publication pointer.

Core preserves `as_of`, ordered sector rows and the optional measured-read presentation. History preserves `meta.asOf`, the existing reconstructed RS-history declaration and ordered sector trails/turns. Both source dates must equal the receipt source session. Brief and action board retain their explicit common baseline; an older declared baseline stays visible and does not become current because core advances.

## Public allowlists

Core sector fields: id, ticker, kind, name, name_zh, accent. Nested subsets are momentum (rs_21d, rs_63d, rs_21d_rank, rs_rank, above_200d, lead), heat (heat_1M, breadth_pct, adv, dec), rotation (state, state_plain_en, state_plain_zh), conviction (label_en), and cycle (phaseLabel). Optional nulls and missing metrics remain null/missing; rotation may legitimately be null. No ranking, score, intelligence, entry decision or membership is regenerated.

Measured-read preserves its schema/status/reason, generation session and benchmark, cohort expected/measured counts, and group identity/names/current status/rank/RS/reason. It omits z-scores, private generation identity, research estimates and extra source objects. A missing measured-read remains absent. The canonical `unavailable/projection_error` stub remains valid. A full object must have consistent counts, status, unique ranks, source session and benchmark. Selected-horizon availability is checked using the source cohort horizon; the other horizon may independently be missing. Measured groups include expected-but-absent sectors and are not equated with present core membership.

History exposes only id/ticker/kind, rs_history date/rs_21d/rs_63d, and turns date/k/major/provisional/mag_pct. Raw price, oscillator, projection, current-cycle internals and private source metadata are excluded. Turns are retrospective price-cycle pivots, independent of the shorter RS trail; magnitudes may exceed100%, the first magnitude may be null, and provisional flags remain explicit.

## Completeness and bounds

Both core/history sector arrays must be present and nonempty, with unique IDs and tickers and identical id-to-ticker mappings. Their respective orders are preserved. This follows the current central producer, which carries every cycle sector and only reorders it. It does not require eleven present sectors: legitimate producer degradation remains possible and is distinct from complete cohort coverage.

The native representation explicitly caps each array at100 sectors. RS history uses the producer's existing252-point limit; its schema, mode, horizons and limit now live in import-light `lib/sector_history_contract.py`, imported/re-exported by the cycle producer without changing calculations. Turns use the existing native consumer's256-record bound. Oversized content is rejected, never silently truncated.

History/turn dates must be real ISO dates, strictly increasing and no later than the source session. Empty/short trails and an earlier final observation stay explicit; no fill from another generation. Required turn/history containers cannot disappear into an empty default. Numbers must be finite and correctly typed; booleans cannot become numbers. Core ranks are positive integral values and population counts nonnegative integral values. Matching identities establish coherence, not freshness or full cohort coverage.

## Qualification evidence

Final projector/reader/API run:196 passed,70 warnings, exit0; `git diff --check` exit0. Log: `/tmp/mmx-core-history-final-20261106.log`. Warnings are existing framework/per-request-cookie deprecations and temporary-directory cleanup warnings. The earlier combined producer/metric/history regression run passed280 with3 skips and70 warnings before the final projection-only validation strengthening; these counts overlap and must not be added. Cycle calculation/metric source did not change after that run.

Tests exercise same-generation allowlisting and content hashes, detached inputs, preserved nulls, actual date/identity/shape/count/rank failures, native bounds, optional measured outage, prior-series dates, separate owner orders, and rejection of corrupt core/history before selection changes. Existing tier splits, older Brief baseline, whole-body size, source clocks, private errors and API gates remain covered.

A separate source interoperability proof used the actual committed central/cycles JSON at the base above (retrieved through Git objects because the sparse worktree omits site artifacts), projected them, and executed the existing Terminal `sectorRows`, `sectorMeasuredRead`, and `sectorRotationHistory` decoders at head `847af34df5f811fa4a9152936e42d199b8a45b08`. Accepted:11 core rows,11 measured ranks,11 histories,2772 RS points and183 turns. Projected fixture body:182141 bytes. Receipt: `SECTOR_COMPLETE_NATIVE_GENERATION_PROOF_2026-11-06.json`.

The interoperability proof uses real committed core/history outputs and controlled Brief/board fixtures. It is not live provider, authenticated browser, current-data, deployment or full generation publication proof. The frozen Terminal source carrier was read only.

## Remaining integration

The bound Terminal consumer must require the complete core/history shape and atomically adopt all four sections. Independent sector/history feed results must have no rendering fallback path while this binding is active. Other feeds (company/confluence, heatmap, risk, events, relative trend, holdings, intraday) retain their existing owners and separate clocks; they do not inherit this generation's freshness.

Private Yahoo input publication, runtime producer assembly with broad/member/board inputs, process bindings, source-update/drain/anti-downgrade fencing, CI capability resolution, protected merge/release and authenticated source-to-screen beta acceptance remain open. Global ownership stays legacy and this checkpoint does not authorize activation by itself.
