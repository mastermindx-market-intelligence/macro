# QLedger continuity implementation — 2026-10-09

## Status and purpose

This source change implements the inactive continuity design commissioned during the rotation/risk investigation. It also hardens the existing publisher's terminal-failure handling. **Production still selects the legacy JSONL claims implementation unconditionally.** No migration, historical issuer recovery, new financial-data capture or new warning publication is claimed by this document.

The original design remains a historical proposal in [QLEDGER_CONTINUITY_SOURCE_PLAN_2026-10-09.md](QLEDGER_CONTINUITY_SOURCE_PLAN_2026-10-09.md). The main rotation/risk integration was separately merged and deployed through Macro #8662, Terminal #856 and Mastermind #1285; its publication evidence is in [ROTATION_RISK_CONFLUENCE_DELIVERY_2026-10-09.md](ROTATION_RISK_CONFLUENCE_DELIVERY_2026-10-09.md). This change addresses evidence-storage continuity and publication failure behavior. It adds no capital-policy or trading authority.

Historical nightly publishers encountered a GitHub oversized-file rejection for claims. A successful calculation or local append is not proof that a warning reached the published system. The existing claims owner must preserve that distinction, retain original histories and surface incomplete or corrupt storage explicitly.

## Architecture and integration

| Component | Resulting behavior |
| --- | --- |
| Existing claims entry points | Legacy preparation, deduplication, row order, serializer timing and backfill behavior are retained. A private strategy seam supports explicit native bindings in synthetic tests. |
| Protocol and restart planner | Bounded immutable base/parts/catalog/root records; complete history verification; capacity validation before effects; exact authorized transaction suffix reconstruction for rebase and restart. |
| Snapshot sources | Explicit full Git tree identity or a local shared/exclusive lease. Complete referenced history and logical bytes are verified before data is returned; a separate bounded namespace inventory supports publication checks. No implicit HEAD, network fetch or alternate-format discovery. |
| Native materializer | Fresh exclusive snapshot for writes, immutable member installation, whole-candidate verification and expected-root comparison before atomic root replacement. Outcomes distinguish visibility, durability, clock uncertainty and publication. |
| Read scope | Related calculations reuse one verified immutable claims snapshot. Scope is task-local and root-specific; writers use fresh exclusive state. The grader captures its scope after backfill. |
| Existing consumers | At the reviewed claims callsites, storage-integrity failures propagate or use explicit unavailable/error output before claims-derived success. They cannot become ordinary zero coverage, empty seen IDs, normal empty-history closure or a fresh green status. |
| Publication validation | Explicit frozen tree/candidate, target and accepted baseline; complete newly reachable object inventory includes oversized files deleted in later commits. Literal commit ancestry ignores replacement refs and graft overrides. Shallow or incomplete history fails closed. |
| Existing publisher hooks | Preflight before index/ref installation, rebase preparation and push. The first terminal rejection retains its classification and original status and stops retries or mutation cleanup. |
| Index lock | Lock identity is captured from the same descriptor that exclusively creates it. An uncertain or replaced lock is preserved rather than adopted. |
| CI | The new suites are registered with the existing QLedger and push-retry owners. The final static closure validates all 253 job definitions and reports no uncovered dependency paths. Existing gates and binding CI remain authoritative. |

The fixed production selector returns `LegacyClaimsBinding` without checking the filesystem for a root manifest and without an activation environment flag. The production publication CLI likewise reports legacy selection; any future nonlegacy selection refuses until a separately admitted explicit publisher binding is supplied. The pure native publication and rebase APIs are implemented, but switching one selector would not constitute a completed production cutover.

All ten identified bypass readers now use the central storage seam with their existing parser and duplicate policies preserved. The affected consumers include grading, accountability, NeuralWeb, evidence clocks, TIL fitness, metric validity, grading closure, US backfill's seen-ID decision and the intelligence registry. Unrelated grades and other sidecar files do not become one atomic transaction.

## Verification and corrections

The retained evidence distinguishes an author's execution from an independent execution of the same cases. Repeated populations must not be added into a larger unique-test count.

| Accepted unit | Independent evidence population |
| --- | --- |
| Initial reader seam | 33 reader cases plus four existing batch controls |
| Eight bypass adapters | 89 new cases plus the same 33 reader and four batch controls |
| Remaining two readers | 35 focused cases |
| Protocol/restart support | 166 focused cases |
| Explicit snapshot transports | 74 focused cases |
| Native materializer | 60 suite cases plus three retained independent defect probes |
| Core native binding | 31 binding cases plus the same 33 reader and four batch controls |
| Consumer integrity | 118 focused cases |
| Publication and publisher integration | 110 passed independently: 64 publication cases plus the same 46 accepted retry controls; root accepted D1/D2. |

Independent review produced real corrections before acceptance:

- Planning failures and final descriptor cleanup now retain structured storage outcomes; an already-visible root is not relabeled as a pre-effect failure.
- Native serialization is completed during bounded planning before materialization. An ordinary serialization failure retains a structured pre-root outcome.
- A foreign empty index-lock inode cannot be adopted during initial identity capture.
- A nested rebase-preparation rejection preserves the first terminal status and error class.
- Git graft metadata cannot hide an oversized intermediate commit from publication validation. The original independent probe is replayed unchanged; ordinary successful and rejected candidate controls remain covered.
- Git's graft deprecation advice is disabled for the child command that explicitly supplies the null graft file, so advice text cannot contaminate the bounded object-ID stream. No repository hook, data guard or module guard is disabled.

The 64-case author publication execution passed, and the subsequent independent run passed those 64 cases together with 46 existing retry controls: 110 passed in 18.68 seconds. Root accepted the publication and publisher integration. The earlier author run and retry population are not added again. The final static dependency closure is also complete. Hosted CI, merge and deployment are separate release evidence; all test roots were synthetic.

## Boundaries that remain

1. **Custody and failed tails.** The historical native issuer operation/lane and unresolved failed-run tails remain unestablished. An absent registration is not proof of expired custody. Source acceptance does not authorize adopting another writer's tail, lock or transaction identity.
2. **Production format activation.** Actual base qualification, mixed-version writer exclusion, migration, rollback and the explicit publisher binding require a separate owner-bound admission. No live root manifest was installed.
3. **Resource qualification.** Operational byte, count, depth and I/O limits are finite. Complete verified bytes are retained in memory; these synthetic tests do not qualify the actual financial history or the production machine's capacity.
4. **Crash recovery.** A crash between immutable hardlink installation and owned temporary-alias removal can leave a multi-link member that the verifier rejects. That preserved state requires reconciliation; automatic recovery and universal exactly-once behavior are not claimed.
5. **Clock and publication effects.** A newly materialized append may have uncertain clock persistence. Dedupe and rebase do not restart historical clocks. Local materialization, candidate validation and remote publication are distinct facts.
6. **Cooperating writers.** The lease protocol governs cooperating readers and writers. It is not a fence against an old binary that ignores the protocol.
7. **Financial validation.** Neither this source change nor a green CI run proves a historically issued rotation warning, live warning freshness, beneficial-owner transfer, full order-book observability, predictive accuracy or incremental options-flow value.

The alternative #8685 proposal remains a separate draft/hold carrier. Its format autodiscovery and incompatible reader semantics were not adopted; its branch, files and hold were left unchanged. Other specifically held or refused operations remain outside this release.

## Release record

This document accompanies the canonical `rotation-risk-qledger-reader-compatibility-20261009` source carrier. This record establishes source acceptance before publication. The publishing PR supplies its accepted head, concluded binding CI and actual merge identity; installation requires a separately observed deployment receipt. A source merge or a healthy service must not be promoted into proof of native-format activation or a fresh financial warning.

The integrated manifest preserves all 253 main job definitions and their unrelated steps and gates. It adds the four claims-store module paths to twelve curated jobs and registers the new suites with two existing execution owners. Final static closure at integrated main `cdab62686e79c76b6d431b02dec49c41a290f4c2`, manifest SHA-256 `be375822f46b82fad6b88f42740f319038dd19bd5db4731dc19f4a97ed433a06`, returned no findings (PID 35774, exit 0; 103.100 seconds). All 32 bound source/test/manifest hashes and HEAD remained unchanged. This counts job definitions and dependency coverage, not 253 passing tests. The final twelve added paths also received an independent byte/semantic preservation review (PID 38773, exit 0).

## Hosted integration corrections and protected-reader compatibility

The first hosted run on PR #8693 at head `3afa900b403ebbdd37b93a99ddeb264a4173db1d` exposed three concrete integration findings. Their failing logs were retained before correction.

1. **Job selection.** The new publisher's bounded Git subprocess caused conservative fallback inference to select `push-retry-policy` for an unrelated template change: 136 jobs against the existing 135-job ceiling. The existing owner now has an explicit exclusive scope covering its measured 17-file concrete closure and real workflow, shell and registry-driven data families. Every test, step, gate, job definition and packing ceiling remains. Four existing curation checks passed (PID 15354: 4 passed in 147.14 seconds). The shared packing measurements are 135/133/128 jobs, respectively, for the template, free-content and plan-book probes, each within its unchanged ceiling. This narrows only opaque fallback selection.
2. **Script import ownership.** The two claims audits and the publication helper now pin their own repository root before repository imports. The change is confined to their module preambles. Every function/class source segment and the remaining module AST are identical. The three previously failing cases and the existing no-call-time-path-mutation control passed (PID 38894: 4 passed in 14.82 seconds), with default guards active and source identities stable. The existing complete hosted import-hygiene gate remains required; no test, baseline, waiver or guard is weakened.
3. **Protected falsifier registration.** The only falsifier edit routes `_read_jsonl` through the compatibility helper. Every byte before and after that function is identical to the registered source. The manifest registration is a hand edit to this file's existing hash and note, preserving all other entries and policies.

### Scoped acceptance of the protected reader

The current user expressly delegated Meta-CEO ownership to assess, architect, implement and integrate this rotation/risk program end to end. Under that live instruction and the scoped-delegation rule in `AGENTS.md`, root accepts this required storage-compatibility maintenance and its exact manifest registration. This is a human-directed program decision within that delegation, not an autonomous Metabolism proposal, a newly authored operator-grant row, permission inferred from the shared GitHub account, or a claim that the user personally inspected the replay. The existing F2 check classified the unchanged canonical branch as a human/operator branch; no namespace, trailer, tier rule or fence was changed to obtain that result.

The registered OLD falsifier SHA-256 is `3306d374655bc8a2c2f5311c7718ddcb5e96bb3610aebefc8112dabe9e24975f`; the accepted NEW hash is `b13aaa95bf2fa7c39172eb9aca3893b99ed5f837802d2d11069b184eeb24bd59`. Evaluation math, outcomes, thresholds, cap/duplicate behavior, timestamps and the real write gate are unchanged. Production still selects the legacy reader unconditionally.

A corpus of 23 files / 30,445 bytes and its expected results was frozen before comparison. The independent replay ran the actual OLD and NEW evaluators, current compatibility helper and real nightly write gate: 12 cases passed (PID 6245, 2.33 seconds), with 15 evaluator calls and four direct relative-return probes per version. Each version appended 29 rows: 7 CONFIRMED, 3 FALSIFIER_TRIPPED and 19 UNVERIFIABLE. Complete tape bytes, ordered rows, expected exceptions and summaries were identical; observed changes were zero. Default data and module guards remained active with no hits or leaks. Root reviewed the actual source comparison, harness, result receipt, log and archive identities before accepting the registration.

Replay receipt SHA-256: `5210ec748da0318693b52967fafb4eff31a0e5db23a0582c281f2e516ff2a297`. Frozen manifest: `46d052546e5f497c6dca911cdff5865dd1fd94013c80c850a95e09643393e94b`. Complete evidence archive: `7a5bb6e3f7054977562ec4485bd0fa53923d1367e4cc72d6581e695dabf93f35`.

**Evidence class remains FROZEN_SYNTHETIC_ONLY.** This is compatibility evidence for those inputs, not a sealed or historical performance replay, an accuracy estimate, or proof of an issued warning. The supplemental Python audit hook is not an OS sandbox. No grading criteria, grant ledger, authority map, capability broker, immune policy or native financial admission was changed. Concluded hosted CI, merge and actual installation remain separately observed release facts.

## Complete tracked-tree dependency correction

The second hosted CI run, `37898963129`, on head `7b9f15d94ad59fe05f16cf35a709a8a962a78660` passed all three packing probes and the protected-source fences. Its `contract-delta` job, `113716783777`, nevertheless found three uncovered paths referenced by the incumbent retry tests: `site/index.html`, `site/premiumdata/special_situations.json` and `site/qledger/track_record.json`. The original failure remains retained.

The earlier four local curation cases ran the same closure check, but used physical file presence without the hosted tracked-tree inventory. These three Git-tracked site files were absent from the sparse checkout. The previous 17-file count is therefore a materialized-checkout observation; the complete tracked-tree closure contains 20 concrete files. No difference in the analyzer's filtering policy is claimed. The path literals originate in synthetic fixtures and assertions in `tests/test_push_retry.py`, not the append-only artifact registry.

The correction adds exactly those three explicit paths to the existing `push-retry-policy` scope. The analyzer, test harness, all 253 job definitions, other 252 definitions' contents, execution steps, owner weight, gates, probes and packing ceilings are preserved. Verification of the actual edited manifest ran in a fresh process with the standard validated exact-HEAD inventory active before selector analysis (PID 10007, exit 0; 3.614 seconds measured). The inventory contained 117,373 paths, payload SHA-256 `27b0e9eb2bb7a04415798f74713d2d020e5ae57e7fd44d5083c457a320b6f55c`. All 20 concrete dependencies are covered; each of the three site paths selects the owner, while the template, free-content and plan-book packing inputs still do not. The exact byte/semantic inverse recovers the previous manifest; 23 fenced source hashes and HEAD stayed stable.

This is source-only static verification, not another pytest population or a new whole-manifest packing execution. No financial artifact bodies or publisher runtime were opened or invoked; default guard settings remained. The corrected manifest SHA-256 is `7898cbc454aff17ca308782c2c9e705d2e1d51f529d847907b8fb8e234c8a160`. Final hosted CI, merge and source installation remain separate release facts supplied by the PR and deployment receipts.


## Conditional dashboard-copy correction

The third hosted CI run, `37902661848`, at head `83d4d9dbd613f965eac0b387952f1e05ef3b26aa` passed the corrected dependency contract, protected-source fences and eleven of twelve packs. Pack 10 failed because the committed-page test required “ready to review” in every nightly population, even when no entry qualified. The exact-base replay reached the same assertion, but its failure signature differed. The final gate correctly retained that step as `unknown` and its subsequent unrun step as `unknown`: 358 of 360 semantic steps passed across 106 logical jobs, with no infrastructure findings. No inherited-failure waiver or gate change was used.

The correction is confined to `tests/test_intelligence_hub_glance_copy.py`. Conditional positive labels now run through the actual complete Jinja template with an explicit buyable entry and all three QLedger states. Three absent/nonbuyable controls require no readiness badge; five planted forbidden-copy probes require the existing committed-page function to reject misleading text. The committed-page function still uses its normal site path in hosted CI and preserves its exact forbidden-copy loop. The template, product logic, all ten unrelated original test functions and CI owners remain unchanged.

The original test failed on a valid zero-ready synthetic render (PID 15172: one expected failure in 1.96 seconds). The corrected complete test file passed all 20 cases (PID 16532: 2.89 seconds), with the same 98,643-byte zero-ready render, SHA-256 `f74d70fda92de4c622bafc4a402d1811f4d1d023fd1a24840a65a96072db6ae5`. Both local executions explicitly substituted that owned synthetic site path; the committed-page case was selected and no case was skipped. Default data/module guards stayed active, with no guard hits or additional audit-boundary attempts. No generated financial page or network source was opened. The final one-file scope check (PID 18769, exit 0) preserved all 35 earlier source hashes and the template.

Root reviewed the original failure, actual patch, full-template fixture, guard behavior and corrected results, and accepts the bounded test correction. Its test SHA-256 is `b7b92803a6a0103ed63addb4c74fe729fb804c63f78ef1df0851d94dcb50e26b`. A subsequent complete hosted CI run, merge and installation remain separate release requirements.
