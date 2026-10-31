# Data OS completion — acceptance matrix status (ORCH-4 owned rows)

Programme: Canonical Market Data & Corporate-Action Integrity — Data OS completion (2026-10-13).
Owner of these rows: ORCH-4 (verification + acceptance packages F01, Q01–Q03, A01–A03, R01–R03;
objectives O5–O7). Rows are copied verbatim (abridged in the table) from the masterplan's work
packages; the assessment status there was `NOT_EXECUTED_BY_ASSESSMENT` for every row.

Base: `origin/main` ac86ae56d900. Verification evidence ships in PR #9273 (branch
`claude/dataos-verify-2026-10-13`); acceptance evidence and this file ship in the acceptance PR (branch
`claude/dataos-accept-2026-10-13`).

## How to read a row

- **PASS** — the row's statement holds under the cited test/record at the cited head.
- **PASS-WITH-GAPS** — the statement holds for what was exercised; the open item names what was not.
- **FINDING** — a defect or contract ambiguity on main was reproduced; the open item names it, and the
  suite carries a strict-xfail reproducer where one exists. Nothing under `lib/`, `engine/`,
  `scripts/` or `data/` was changed to make a row pass.
- **UNFINISHED** — not executed; the open item says why. A row is never marked PASS on a plan, a
  status note or a sibling's receipt.

Evidence classes: SYNTHETIC hermetic fixtures driven through the real code seams (Q01–Q03, F01,
A02, A03); A01 adds a known-answer corpus; R01 is a source review of MERGED pull requests; R02 and
R03 are plans only (running them is a seat act). No row asserts anything about trading alpha,
model quality or allocation.

Summary: PASS 16, PASS-WITH-GAPS 12, FINDING 4, UNFINISHED 9.


### F01 (O5)

| Row | Statement (abridged) | Status | Evidence | Open item |
| --- | --- | --- | --- | --- |
| F01.01 | The three consumers agree on values and identifiers for the same requested view, and the difference between... | **PASS-WITH-GAPS** | research/data_os_completion/2026-10-13/F01_JOURNEY.md Journey + Identity join + Distinct views; `tests/verification/test_journey_f01.py` J1-J8 (PR #9273) | UNFINISHED: Terminal JSON leg awaits C04 LANDED; frontend leg = Terminal #996 cited, not re-verified; synthetic corpus only |
| F01.02 | Raw and total-return numbers need not be equal; forced visual equality is not acceptance. | **PASS-WITH-GAPS** | research/data_os_completion/2026-10-13/F01_JOURNEY.md Distinct views (`close` vs `close_raw` named, never forced equal) (PR #9273) | UNFINISHED: raw-vs-adjusted on the real committed store - no raw column on data/stocks |
| F01.03 | Inspection cannot trigger a model call, market trade, data acquisition or canonical source mutation. | **PASS-WITH-GAPS** | research/data_os_completion/2026-10-13/F01_JOURNEY.md Census; `tests/verification/journey_f01_census.py` (PR #9273) | GAP: the census is in-process; the CLI subprocess leg is outside it |
| F01.04 | Broken/unauthorized evidence links cannot reveal hidden paths or substitute current data under an old selec... | **PASS** | research/data_os_completion/2026-10-13/F01_JOURNEY.md Broken links (7 codes, both transports, leak sweep empty) (PR #9273) | - |

### Q01 (O6)

| Row | Statement (abridged) | Status | Evidence | Open item |
| --- | --- | --- | --- | --- |
| Q01.01 | The independent oracle validates share/cash wealth, view transformations, eligible revisions and exact reta... | **PASS-WITH-GAPS** | research/data_os_completion/2026-10-13/Q01_ORACLE.md Vector table + Refusal oracle; `tests/verification/test_oracle_q01.py` (PR #9273) | GAP Q01-F1 (strict xfail): an INFERRED split is refused NOT_CONFIRMED where the oracle leaves the factor at 1; D00.D3 text does not select between them |
| Q01.02 | Uniform scaling of both return endpoints cannot be mislabeled as a return error. | **PASS** | research/data_os_completion/2026-10-13/Q01_ORACLE.md Q01.02 uniform scaling (PR #9273) | - |
| Q01.03 | A future dependency mutation must not alter an earlier qualified result. | **PASS** | research/data_os_completion/2026-10-13/Q01_ORACLE.md Q01.03 future-mutation immunity (PR #9273) | - |
| Q01.04 | Tests that copy the implementation formula or reuse its identity-selection branch are not the only oracle. | **PASS** | research/data_os_completion/2026-10-13/Q01_ORACLE.md Independence + Q01.04 exactness; judge n-gram vs price_views 1.4% (PR #9273) | - |
| Q01.05 | No conclusions about trading alpha, model quality or allocation follow from these data tests. | **PASS** | research/data_os_completion/2026-10-13/Q01_ORACLE.md No alpha conclusion (PR #9273) | - |

### Q02 (O6)

| Row | Statement (abridged) | Status | Evidence | Open item |
| --- | --- | --- | --- | --- |
| Q02.01 | A permitted end-to-end read succeeds while mismatched/revoked/old-generation variants refuse at the actual... | **PASS-WITH-GAPS** | research/data_os_completion/2026-10-13/Q02_ACCESS.md cases A1-A6; `tests/verification/test_access_q02.py` (PR #9273) | UNFINISHED: no authenticated Studio/MCP principal reached the dispatcher (Remaining real-principal gates) |
| Q02.02 | Receipt-only refusal, disappeared artifact and A→B→A changes cannot silently resurrect invalid current evid... | **PASS** | research/data_os_completion/2026-10-13/Q02_ACCESS.md cases B1-B6 (PR #9273); RESOLVED 2026-10-19 by PR #9654 (claude/dataos-q02f1-2026-10-19): unreadable history now answers basis=membership_unreadable and the basket read refuses MEMBERSHIP_UNREADABLE; strict-xfail removed. | FINDING Q02-F1: an unreadable basket-history parquet is answered as basis=current_membership ('no PIT history yet') - a read failure looks like absence |
| Q02.03 | Authorized-then-guest cache sequences cannot replay private results. | **PASS-WITH-GAPS** | research/data_os_completion/2026-10-13/Q02_ACCESS.md cases C1-C4 (PR #9273) | UNFINISHED: same sequence under two real authenticated principals |
| Q02.04 | Simulated responses alone do not substitute for the real handler/browser composition or real source-byte ve... | **PASS-WITH-GAPS** | research/data_os_completion/2026-10-13/Q02_ACCESS.md D1-D2, L1-L3, Source-byte verification (PR #9273) | GAP: a successful read carries content_sha256=None (stat-identity `statv1`, not byte-verified); browser composition not exercised |

### Q03 (O6)

| Row | Statement (abridged) | Status | Evidence | Open item |
| --- | --- | --- | --- | --- |
| Q03.01 | The new path meets the frozen accepted workload targets and all unchanged source/response/job bounds, with... | **FINDING** | research/data_os_completion/2026-10-13/Q03_WORKLOAD.md sections 5-10 + q03_results.json; `tests/verification/test_bench_q03_contract.py` (PR #9273) | FINDING Q03 GAP 1: A_cli +~26 ms/call on 12/12 requests (eager lib/dataos/__init__ imports), reported not waived; GAP 2: R3 describe +92 B, digest changes; UNFINISHED: U03/U04, C04, Terminal route, concurrency >1 |
| Q03.02 | No performance improvement is obtained by removing members, series fields, evidence or difficult requests. | **PASS** | research/data_os_completion/2026-10-13/Q03_WORKLOAD.md section 10 (all rows/columns identical; R8 3700 = 3700) (PR #9273) | - |
| Q03.03 | Existing 128 KiB workspace output bound and host/root limits are not silently widened. | **PASS** | research/data_os_completion/2026-10-13/Q03_WORKLOAD.md section 8 limits (PR #9273) | - |
| Q03.04 | Background work, expensive repeated object listing or uncontrolled worker fan-out cannot hide latency or cost. | **PASS** | research/data_os_completion/2026-10-13/Q03_WORKLOAD.md section 9 background work (PR #9273) | - |

### A01 (O7)

| Row | Statement (abridged) | Status | Evidence | Open item |
| --- | --- | --- | --- | --- |
| A01.01 | A known-answer corpus and a rights-allowed real retained corpus each complete the three-consumer positive w... | **UNFINISHED** | research/data_os_completion/2026-10-13/A01_VERTICAL.md §Acceptance map; synthetic exact-number KAC through the real entrypoints PASS: `test_known_answer_three_consumers`, `test_current_returns_b`, `test_replay_returns_exact_a` (`tests/verification/test_journey_a01.py`, SYNTHETIC) | UNFINISHED: rights-allowed retained real corpus not established (`test_registry_rights_row_real_corpus_unfinished` pins purchase_access/internal_computation unverified, redistribution not_granted); consumer legs await C04 (Terminal JSON), U03 (canonical reads in Data Workspace) and U04 (basket on one price basis); Terminal UI cited from Terminal #996, not re-run |
| A01.02 | A successful JSON function alone is not user workflow acceptance. | **PASS** | research/data_os_completion/2026-10-13/A01_VERTICAL.md; `test_a_passing_call_is_not_workflow_acceptance`, `test_inspectable_explanation` (SYNTHETIC) | - |
| A01.03 | A reused ticker or incompatible basis control must not pass just because the happy path works. | **FINDING** | research/data_os_completion/2026-10-13/A01_VERTICAL.md §Identity controls; PASS: `test_reused_ticker_two_securities`, `test_reused_ticker_overlap_refused`, `test_rename_boundary_exact`, `test_incompatible_refuses_compatible_serves`; strict xfail `test_rename_without_evidence_is_a_finding` | FINDING A01-F1: `VendorAliasTable` binds rename continuity from an alias row with no `evidence_sha256` (fix belongs to the identity owner; reproducer = the strict xfail). UNFINISHED: the ticker-keyed C01 seam serves n=60 rows across the 2026-03-02 reuse boundary under one key (`test_reused_ticker_join_unfinished_not_passed`), recorded not passed — awaits U03/U04 security-keyed reads |
| A01.04 | Missing member/source evidence cannot be hidden or silently filled from current data. | **PASS-WITH-GAPS** | research/data_os_completion/2026-10-13/A01_VERTICAL.md §Revocation mapping; `test_missing_member_stays_in_account`, `test_coverage_denominator_before_and_after_b`, six typed revocations (ROOT_NOT_BOUND, SOURCE_NOT_FOUND, SOURCE_INACCESSIBLE, SOURCE_VERSION_MISMATCH, UNBOUND_DEPENDENCY, NO_RETAINED_OUTPUT; values never served) | GAP: principal revocation is K01 GAP 1 (owner transport); no literal UNAVAILABLE/DENIED code — the closed typed sets are the refusal |

### A02 (O7)

| Row | Statement (abridged) | Status | Evidence | Open item |
| --- | --- | --- | --- | --- |
| A02.01 | A new eligible current view B is visible while exact retained A reopens unchanged, with correct mode/source... | **PASS-WITH-GAPS** | research/data_os_completion/2026-10-13/A02_UPDATE_CORRECTION.md; `tests/verification/test_a02_corrections.py::test_a02_01_*` (SYNTHETIC) | UNFINISHED: natural new-day update through the original owner (hermetic lane; R03 cycle plan); GAP: no CURRENT-mode price-view composition (`price_views.py` has no ReadMode.CURRENT path) |
| A02.02 | Synthetic or manually injected correction is not called a natural vendor event. | **PASS-WITH-GAPS** | research/data_os_completion/2026-10-13/A02_UPDATE_CORRECTION.md; `test_a02_02_*` (SYNTHETIC) | UNFINISHED: actual recorded vendor revisions (hermetic lane, no data/ reads) |
| A02.03 | An unchanged data body with a new refusal/rights generation cannot keep an invalid current view active. | **PASS-WITH-GAPS** | research/data_os_completion/2026-10-13/A02_UPDATE_CORRECTION.md; `test_a02_03_*` SYN-G1/G2/G3, SYN-AG1/AG2 | GAP: no refusal/rights generation field on GenerationRef or ViewVintage - tested as a receipt-only superseding generation (D5.3) |
| A02.04 | No wait for a future corporate action is used to postpone otherwise ready deterministic or rollback tests. | **PASS** | research/data_os_completion/2026-10-13/A02_UPDATE_CORRECTION.md; `test_a02_04_no_wall_clock_and_no_future_event` | - |

### A03 (O7)

| Row | Statement (abridged) | Status | Evidence | Open item |
| --- | --- | --- | --- | --- |
| A03.01 | After an isolated interrupted publication or lost response, original-target reconciliation establishes effe... | **FINDING** | research/data_os_completion/2026-10-13/A03_RECOVERY.md; `tests/verification/test_a03_recovery.py` restore k=0..5 + hard-kill matrix (SYNTHETIC) | FINDING A03-F1 (strict xfail): a process-level crash mid-publish leaves a torn visible set (B/B/A/A/A) under A's receipt and daily.yml commits it; FINDING A03-F3 (strict xfail): a later refusal certifies the tear as last-good |
| A03.02 | Rollback cannot erase failed-generation evidence or relabel legacy data as historically qualified. | **FINDING** | research/data_os_completion/2026-10-13/A03_RECOVERY.md; `test_a03_02_*` | FINDING A03-F2 (strict xfail): generic/notes refusals leave no durable failed-generation record; UNFINISHED: no generation id, current pointer or rollback receipt for data/reference (rollback = operator git revert) |
| A03.03 | Source data, prior reads, membership history, drawings and excluded intelligence ledgers stay unchanged. | **PASS-WITH-GAPS** | research/data_os_completion/2026-10-13/A03_RECOVERY.md; `test_a03_03_*` | UNFINISHED: real-inputs leg (hermetic lane, no data/ reads) |
| A03.04 | No independent writer or transport is used to replay an unresolved/denied effect. | **PASS** | research/data_os_completion/2026-10-13/A03_RECOVERY.md; `test_a03_04_only_the_owner_seam_writes_the_receipt` (writer census = build, _restore_artifacts, run_nightly_refresh) | - |

### R01 (O7)

| Row | Statement (abridged) | Status | Evidence | Open item |
| --- | --- | --- | --- | --- |
| R01.01 | Exact reviewed blobs and all required integrated checks correspond to the candidate actually released. | **PASS** | research/data_os_completion/2026-10-13/R01_SOURCE_REVIEW.md §Landed-blob trace + §Orchestrator-filled remote evidence (22 PRs: checks on each merged head, only non-pass = known-spurious merge-queue-pilot; 14/22 squash blob-identical, 8/8 remaining SAME_HUNK on `.github/ci/legacy-jobs.yml`); `tests/verification/test_r01_prior_findings.py` (16 prior-finding pins) | - |
| R01.02 | Old green CI, an unrelated standalone workflow or a sibling release waiver cannot qualify a changed candidate. | **PASS** | research/data_os_completion/2026-10-13/R01_SOURCE_REVIEW.md §Gate closure R01.02 (every check attributed to the merged head; no old-green, unrelated-workflow or sibling-waiver qualification) | - |
| R01.03 | No auto-merge/label change on another owner’s held PR or hidden broad conflict resolution. | **PASS** | research/data_os_completion/2026-10-13/R01_SOURCE_REVIEW.md §Gate closure R01.03 (current state + one GraphQL timelineItems history read since 2026-10-12: zero label/arming/draft/review events on #8637/#7299/#9121/#8076; #9147 = this programme's own P02 PR closed as included in #9152). Note: Terminal #955 merged under its own programme's arming; the shared fleet token makes the actor unattributable | - |
| R01.04 | Document-package checks are not counted as product test or independent code review. | **PASS** | research/data_os_completion/2026-10-13/R01_SOURCE_REVIEW.md per-PR table (DOCS-ONLY / TESTS-ONLY / CI-ONLY rows classed "not product proof"); this matrix counts doc-package checks as neither product test nor review | - |

### R02 (O7)

| Row | Statement (abridged) | Status | Evidence | Open item |
| --- | --- | --- | --- | --- |
| R02.01 | Each of the three required consumers and every claimed enrolled market has source-bound actual production e... | **UNFINISHED** | research/data_os_completion/2026-10-13/R02_INSTALL_PLAN.md §2 per-consumer receipt tables + §3 enrolled-market matrix (plan only, NOT EXECUTED) | UNFINISHED: the production read-back is a seat act after R01, A02 and M01 (M01 not landed). A: Terminal runtime is cited from Terminal #996 (ACCEPTED-RECEIPT), and its PRODUCTION_PROOF is recorded in no repo file. B: the `scripts/data_workspace.py` CLI read is PLANNED, with no executed read. C: the basket is BLOCKED-ON-C03/C04. US: planned reads. HK/CN: identity-only (D00:117-119). |
| R02.02 | Installed code, published data, selected settings and real runtime execution are separate receipts. | **UNFINISHED** | research/data_os_completion/2026-10-13/R02_INSTALL_PLAN.md §2 — installed code, published data, selected setting and runtime execution are separate receipt rows, each with its own owner, command, expected observation and check id | UNFINISHED: the receipts exist only when the seat runs R02. The B generation id is UNFINISHED: there is no `GenerationRef` producer (R02 appendix A4). |
| R02.03 | One user or sample does not prove all-account or all-universe adoption. | **UNFINISHED** | research/data_os_completion/2026-10-13/R02_INSTALL_PLAN.md §4 adoption statement (one sample is never all-account or all-universe) | UNFINISHED: the adoption census across accounts and the universe requires the R02 run. HK/CN are identity-only. |
| R02.04 | Unqualified/missing historical coverage is not advertised as complete or silently made current. | **UNFINISHED** | research/data_os_completion/2026-10-13/R02_INSTALL_PLAN.md §5 coverage honesty. The B envelope keeps `production_qualification: NOT_ESTABLISHED_BY_THIS_ADAPTER` (web_workspace.py:126). Roots carry `evidence_kind`, and unqualified roots are never presented as current. | UNFINISHED: the coverage-honesty read-back requires the R02 run. Consumer A's missing-history carrier is not yet identified (P23 GAP). |

### R03 (O7)

| Row | Statement (abridged) | Status | Evidence | Open item |
| --- | --- | --- | --- | --- |
| R03.01 | A second actual cycle preserves historical views and produces correct new/unchanged dispositions without du... | **UNFINISHED** | research/data_os_completion/2026-10-13/R03_CYCLE_PLAN.md §2 cycle definition; §3 invariants. Cycle 2 = the next scheduled `daily` run that concludes after the R02 receipts. | UNFINISHED: no second actual cycle has run (R02 comes first). Generation-forward-once and zero-duplicate at the generation level stay UNFINISHED: no `GenerationRef` producer exists. The owner-level duplicate check (one `data: daily collection` commit and one concluded run per date) is PLANNED. C (dispositions/population) is BLOCKED-ON-C03/C04. |
| R03.02 | An already-running capture is not duplicated to obtain a faster receipt. | **UNFINISHED** | research/data_os_completion/2026-10-13/R03_CYCLE_PLAN.md §4 — the seat waits for a running capture, reads its retained return, and never dispatches another. `prophet-rescue` is the only redispatcher of `daily`. | UNFINISHED: the rule is stated, not yet exercised on a live cycle (needs the R03 run). |
| R03.03 | No scheduling or background reasoning is claimed without an actual existing/created owner and return. | **UNFINISHED** | research/data_os_completion/2026-10-13/R03_CYCLE_PLAN.md §1, §5 (ORCH-4-corrected). The existing owner is `.github/workflows/daily.yml` job `collect`; its return path is the concluded run record plus the `data: daily collection <date>` commit on origin/main. FINDING P23-F1: the lane's sparse-tree census missed `.github/`, so it reported no owner. ORCH-4 corrected this with file:line evidence. | UNFINISHED: owner and return path are identified, but nothing has been read back yet (seat act after two concluded `daily` runs following R02). No schedule, daemon or publisher is created or claimed. |
| R03.04 | Source failure must surface as data failure, not market direction or a silently fresh fallback. | **UNFINISHED** | research/data_os_completion/2026-10-13/R03_CYCLE_PLAN.md §6. B: a typed CLI error with exit 2 (scripts/data_workspace.py:81-89) and no fallback path. C: `FALLBACK_NOT_DECLARED` (read_contract.py:99, :1155, :1281). | UNFINISHED: source-failure surfacing on a live cycle requires the R03 run. C is BLOCKED-ON-C04. |
