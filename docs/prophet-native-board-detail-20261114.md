# Native Prophet published setup read

## Purpose and custody

Chairman's native Prophet implementation assignment requires the existing published entry, price and technical detail to be available in the beta shell. Terminal PR1505 owns the native consumer. Its complete-pool read depends on Macro PR11248; this is a genuine successor of that read, not a replacement candidate producer or alternate daily-brief lifecycle.

Source parent: PR11248, initially `8a45c12ee4d9379beefda8c18552847a0a45371e`, reconciled forward to `ffd95ec212dbffb7144e87df995e9a063cc68d89` without changing its writer or branch. The parent adds candidate-projector restart coverage; its API contract is unchanged. New source carrier: `sol/web-prophet-native-board-detail-20261114-c2`, GitHub-native branch/commit/ref operations with exact-head lease from its known `8a45c12` preimage. Governing protected Mastermind pin: `576d70957cd5c02f65e04785111665f2bd6153a1`. Paid Fabric adapter admission is unavailable; principal implements within the direct source grant, with native advisers confined to architecture/product judgment. No worker effect is duplicated.

New paths are the pure `engine/us_prophet_board_view.py`, transport `app/prophet_board_detail.py`, two focused test files and this note. The shared edits append the child router to `app/prophet_daily_brief.py` and add only `us_prophet_board_view` to the incumbent exact API-restart predicate. These are real dependencies on #11248, not an independent zero-overlap claim. `app/main.py` and its live Sector owner remain untouched. Do not merge into or write the live parent branch. Qualify the parent, then integrate the successor through the existing protected path. The successor PR targets `main` because Macro's required semantic CI and normal arming predicate require that base; its inherited parent commits remain explicit.

Held Macro #9495 owns a different rich legacy presenter/template/price-clock restoration. This implementation imports none of that held code and adopts none of its unresolved browser/Paper/Plan effects. Preserve #10674's unknown effects and all recorded holds. Legacy /us_stocks.html remains until actual feature/access/source/deep-link parity and production acceptance.

## Exact read contract

`GET /api/prophet/board-detail/v1?ticker=SYMBOL&source_sha256=sha256:<64-lowercase-hex>`

Both query keys are required exactly once; all extra keys fail after the incumbent site-full authentication and before source work. The only source is the existing fixed bounded `site/factordata/us_standouts.json` reader. Candidate, Daily Brief and detail reads share the same nonqueuing `_READ_ADMISSION` permit. No new cache, watcher, root configuration, retry, auth owner, source path, model computation or publication machinery is introduced.

The supplied hash is the complete candidate envelope's `source.sha256`, not its normalized display digest or Git blob hash. The route hashes the initial bounded raw bytes, requires exact equality, strictly parses JSON (duplicate keys/non-finite values rejected), projects one row, serializes, then repeats the bounded raw read before releasing the permit. Any final raw-byte change withdraws the serialized result.

| Condition | Result |
| --- | --- |
| Exact source, one valid selected buy[] row | 200 ready |
| Exact valid source, no selected buy[] row | 200 not_on_main_list, row:null |
| Stale caller hash | 409 SOURCE_BINDING_MISMATCH |
| Invalid query | 400 INVALID_QUERY |
| Unavailable/malformed/ambiguous/racing source, busy permit, projection/serialization failure | Private sanitized 503 BOARD_DETAIL_UNAVAILABLE |
| Existing authentication/entitlement denial | Existing private 401/403 |

The v1 envelope identifies schema, US market, display_only:true, ticker, board as_of, raw source path/hash/bytes, status and row. The row allowlist carries name/sector, row price and its optional price_as_of, row signal_asof, entry status/headlines/zone/stop/chase boundary, optional missing-entry reason, base invalidation, the source reason/above200/weekly_bull/provisional/tier_observed_date/tier_observation_provisional fields, and lane/stage. Unknown source additions, SVG, sizing and plan-shaped objects do not cross the allowlist. No watch/leader/plan fallback is used.

## Semantic boundaries verified against the pinned publication

The pinned source contains 98 eligible candidates and 62 main-list rows, dated 2026-11-12. The new pure projector successfully read all 62 actual main-list rows. Every signal_asof is 2026-11-11; every price_as_of is absent. These are actual source observations, not proof of a served or deployed API.

- Signal session is not entry-assessment time. No assessment timestamp is supplied or fabricated.
- Board session dates the published snapshot. It cannot populate a missing quote clock.
- Row price is retained independently of the rounded entry_signal.spot field.
- Zero-width zones and stops inside zones are valid published output; this read adds no trading-geometry rule.
- Method stop and base invalidation remain distinct; a chase boundary is not a target.
- Missing values, numeric zero and boolean false remain distinct.
- `signal.provisional` describes the T3 projection only; it does not summarize `tier_observation_provisional` or imply general confirmation.
- `bounce_wait` describes a rebound already observed with turn unconfirmed. The native label is Rebound unconfirmed, not a forecast of a future rebound.
- A main-list absence does not establish eligibility, a missing setup elsewhere or a matching model plan.

The Terminal consumer additionally requires agreement with the candidate row's main-list membership and its byte count/session. It clears the private candidate subtree on an explicit detail access denial. These checks compose existing owners without adding a candidate-pool import to this read-only backend adapter.

## Qualification and remaining acceptance

The 61 focused projection/route tests cover strict source/hash/query behavior, false/zero/null, independent clocks, allowlist, final source race, shared permit through final read, and recovery after final-read/projection/serialization failure. Five of these tests exercise the assembled app or the real shared auth chain with controlled underlying authentication/entitlement answers. Earlier isolated tests used an explicitly marked auth import stand-in; after materializing the real source/config/schema closure and installing the existing serving-tier `requests` dependency, the final qualification uses actual application imports with no import stand-in.

Both unchanged deployment guards pass: `test_api_load_time_import_closure_is_covered_by_restart_regex` and `test_load_time_closure_probe_is_not_vacuous`. All 4,107 tracked Python files in the guard's top-level app and engine/lib/scripts source frontier are present; sparse missing modules cannot produce a false pass. The new projector has only standard-library imports. Shell syntax and diff checks pass. These are local source/runtime-fixture results, not deployment receipts.

Architecture review found a Python/TypeScript offset-minute mismatch; the Python clock grammar now rejects overflowing minutes such as +01:99. The consumer membership, access-withdrawal and rebound-label findings were repaired in the owned Terminal branch. Author self-review plus these actual read-only adviser findings do not constitute a non-author GitHub APPROVED event.

Normal required CI, backend source-to-served proof, actual entitled native consumer proof and responsive light/dark EN/ZH browser inspection remain open. Browser attempts in the current session were blocked before useful page inspection; no screenshots, deployment, merge or production acceptance are claimed. Backend deployment must precede release of the matching Terminal consumer. A green source test suite does not retire the iframe or finish the parent Prophet outcome.

Terminal source reconciliation: live PR1500 at `dc8039571b40a0d0ce3765b92560f4cbf7d195d5` is the parent PR1495 writer's complete-candidate stack. Its immutable P4 packet explicitly acknowledges concurrent PR1505. The latter's unique setup/research/comparison work will compose onto that single candidate population, shared transport and account lifetime while preserving PR1500's actual 320px Chinese layout fix. No candidate-reader duplication or parent branch takeover is intended. A bounded published-PR census found no other new native board-detail projector/route carrier; unpublished branch state remains outside that evidence.
