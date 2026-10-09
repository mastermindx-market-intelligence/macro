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
