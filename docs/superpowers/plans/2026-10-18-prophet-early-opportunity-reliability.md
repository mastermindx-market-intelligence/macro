# Prophet Early Opportunity Reliability — implementation plan

Goal: stop silently excluding liquid stocks such as WM, make early observations visible independently of slow confirmation, and prevent stale evidence from appearing current. This is the existing Prophet pipeline, not a new signal/lifecycle/ranker. Current Chairman direction on 2026-10-18 authorizes implementation and end-to-end verification; no repeated design approval is required by protected ACTIVE_EXECUTION.

Source: Macro 047ab5a950e59f4bdca180129a4dd84086a6d064. Protected procedure: Mastermind d5cce731a23588ddbf4df806bd9e8dcfa5eecf24. Existing owners: WS:PROPHET-US-V4-RECOVERY, #6817, #6805. Diagnostic record #6817/6247452059. Prior worker's never-confirmed-KO and healthy-missing-weekdays claims are rejected. KO is T2 on Oct16, already 9.63% above its Oct2 adjusted closing low. B03 already supplies a lossless authenticated observation API: extend it, do not rebuild it.

## Source/effect boundary

Operation prophet-wmko-coverage-20261018 owns only its new branch sol/web-prophet-wmko-coverage-20261018. Studio acquire returned WORKSPACE_ACQUISITION_UNQUALIFIED. Same installed owner `mmx-workspace status --repository macro --operation-id prophet-wmko-coverage-20261018 --lane web` then verified exact registered RELEASABLE/dirty=false workspace, branch, acquired base and locked operation marker. Independent Git readback verified clean exact HEAD/common directory. Acquisition is reconciled to that single existing worktree; no retry or re-home. The Studio publisher projection still reports inconsistent clean=false; do not assume publication readiness from that wrapper. Reconcile exact publication operation before any retry.

#7227 remains the incumbent sidecar protocol/intake writer; do not modify scripts/build_turn_watch.py or engine/us_candidate_episode_intake.py here. #9495/#8444 stale-card/B4 source and other live writers remain separate. Root prophet-wmko-miss-20261018 is conserved. No production data/history, credential, broker, order, rank/gate/sizing or global notification mutation.

## Architecture

1. Keep frozen v1 membership and all historical v1 source bytes unchanged. Add a prospective versioned Turn Watch universe through the SAME engine, based on an existing canonical outcome-independent US membership roster, not raw price-directory discovery or a WM-specific whitelist. New selection era may activate only on a genuinely new completed session after existing v1 inputs. Earliest intended boundary is 2026-10-19. Before then, v1 build results must remain byte-compatible. Missing/malformed future contract fails closed at its activation, never silently falls back. Record roster source and exact hashes. Preserve detector formulas, completed-bar semantics and old RS ruler; new cross-sectional population is a new disclosed selection era.
2. Extend existing engine.prophet_early_observations / app.prophet_observations instead of adding a new service or candidate store. Exact-source coverage explains IN_UNIVERSE versus NOT_IN_UNIVERSE versus UNAVAILABLE. An absent trigger is not proof of a completed evaluation. A per-name stale/missing source is not neutral/no setup. Public partition hash must bind membership disclosure; mismatch withholds the claim. New universe audit data must not alter historical v1 publication bytes.
3. Existing authenticated complete observation population is the consumer source, not the 40-card public preview or plan book. Preserve auth-before-read, private/no-store headers, snapshot pagination, exact B1 relation and all authority=false semantics. Display timing context (price/reset, off-low, native confirmation, row/source clocks) as source facts only, never automatic BUY. Maintain actual clock UNKNOWN when publication/ingestion was not recorded.
4. Terminal and Macro consumer work is a subsequent disjoint integration task against this exact API; reuse existing navigation, symbol identity, auth proxy, alert subscriptions and components. No second drawer, watchlist owner, notification queue or independent score. Early WATCH/REVIEW and explicit B4 entry-open remain distinct. Native source-owner stale-board repair must retain historical assessments as historical.

## Task A — coverage and deterministic source disclosure

Allowed paths: engine/us_turn_watch.py; optional small pure helper under the same engine owner; new config/us_turn_watch_universe.v2.json; new focused tests; plan/evidence/Agent OS records. Do not edit frozen v1 contract, sidecar writer or B1 intake.

- Write and run RED tests for WM inclusion by canonical roster rule, v1 frozen parity, date-bound v2 activation, invalid/missing/tampered v2, excluded non-equities, and no inference from an uncontracted file.
- Implement minimal versioned selection in the same engine. Thread the selected contract consistently into universe loading, RS population and source-contract qualification. No global mutable mode/hidden fallback.
- Prove byte-compatible v1 row/public result and full B1-relevant semantics before the cut; counterfactual replay never writes ordinary history.

## Task B — real observation API

Allowed paths: engine/prophet_early_observations.py; app/prophet_observations.py; their existing/new tests; same evidence/Agent OS records.

- RED tests: KO beyond-cap remains queryable; queried WM outside v1 returns explicit non-coverage; in-universe absent event is not a fabricated failed evaluation; missing/mismatched public proof returns unavailable coverage; stale per-name asof cannot inherit fresh document clock; pagination and snapshot invalidation stay exact.
- Extend existing response additively with source-bound coverage and timing context needed by a user to understand the event. Preserve all authoritative B1 IDs and BUY/ALERT/ENTRY authority false. No LLM inference.
- Auth, malformed parameters, latest corrupt sidecar, future data, snapshot conflicts and sign-out retain existing failure behavior. No expensive new startup imports.

## Task C — integration and acceptance

- Independent paid Fabric review of actual diff and discriminating tests; address real findings on same source carrier.
- Focused unit/integration tests and original owner battery; exact-head hosted checks before source merge. No unrelated main repair or admin bypass.
- Normal production deployment/readback, real authenticated API and consumer proof where access allows. Prospective v2 cannot be called PROVEN_LIVE before the first real new-session producer/reconciler/consumer cycle. Record any actual external boundary, not a fabricated completion.
- Separate research worker produces truncated-history WM/KO and fixed-peer counterfactuals with prices/basis and negative cases. No retrospective fit, no return claims from two winners, no indicator substitution. Optional earlier detector admission requires its own accepted validation, never a shortcut to make these cases green.

## Review focus

Definition-clock mismatch; future or stale per-name bars hidden by a current majority; selection change colliding with immutable ordinary source keys; missing identity mistaken for no opportunity; consumer turning a research WATCH into buy/alert authority. Every one requires a negative regression, not just a WM/KO happy-path test.

## Resumed delivery integration — 2026-10-18

Custody was reconciled at the preserved e19053d7 backend and c3dd159e Terminal
carriers. The original inaccessible Fabric assignment remains terminal; it was
not retried. The predecessor's blocked checkpoint write was not replayed.

The paid read-only review of e19053d7 found two delivery dependencies beyond
the original patch: incidental legacy callers of the shared universe helper
must keep their v1 ruler, and the canonical v2 roster contains 70 names without
committed Yahoo stores. The existing Yahoo backfill/refresh owner already owns
the required schema, dual price bases, bounded retries, budgets and publication.
Its planner therefore also consumes the immutable v2 roster. This extends the
source integration to scripts/backfill_yahoo_universe.py and its existing tests,
plus exact CI registration; it introduces no new store writer, raw-directory
universe, direct production data/history mutation, or change to the held sidecar
and B1 intake. Its existing --refresh-all mode continues to maintain the files.
Parked failures remain parked and are disclosed, never treated as evaluations.

The v2 source floor is measured from immutable committed price blobs using the
unchanged native close loader. Membership still derives exclusively from the
bound canonical issuer roster. Source completeness stays fail-closed. The
prospective contract does not claim that a future completed session exists.

B03 observation rows remain genuine source events; exact ticker coverage is
additive subject_coverage outside rows. Membership requires the same hashed
public artifact and its existing source_contract. Missing per-stock dates stay
unknown. The additive payload changes snapshot identity once at deployment;
in-flight old snapshot requests receive the existing 409 fence and must reread.
Historical source event IDs, B1 relations, v1 publication bytes and authority
flags remain governed by their existing owners.
