---
workstream: "WS:MARKET-MEMORY-W2C"
session: claude/ssd-market-memory-certified-lineage-01a1333c-2fe5c2551fd4604b
model: codex
ended_because: ci_handoff
mission: >
  Deliver the exact-owner certified-lineage successor within the full Market
  Memory program on PR 6528, preserving original captures and existing readers.
state_before: >
  Online ancestry walks have fixed byte and row ceilings. The public owner
  census exceeds the online byte ceiling; neither a size census nor a worker
  proposal proves the complete original append-one chain.
changed:
  - path: engine/neuralweb/market_memory_lineage.py
    what: Separate bounded offline full-chain qualification from exact online certificate and original-capture reads, with current permissions before use and disclosure.
  - path: engine/neuralweb/market_memory_pit.py
    what: Add explicit qualification delegation on the existing concrete PIT reader without altering its original full-ancestry read contract.
  - path: engine/neuralweb/market_memory_trusted.py
    what: Add the same explicit qualification delegation for the existing trusted owner.
  - path: contracts/market_memory/lineage_certificate.v1.schema.json
    what: Pin complete ordered append-one links, qualification batches, source HEAD, producer and operation identities, bounded budgets and false external-authentication claims.
  - path: contracts/market_memory/lineage_head.v1.schema.json
    what: Pin the exact same-owner published certificate and qualified generation pointer.
  - path: scripts/qualify_market_memory_lineage.py
    what: Add a read-only verify command requiring an exact source HEAD, operation reference and explicit offline ceilings; it publishes nothing.
  - path: tests/test_market_memory_lineage.py
    what: Exercise real owner fixtures, corruption, gaps, source identity, actual subject permissions, certificate admission, timestamp and complete batch accounting.
  - path: .github/ci/legacy-jobs.yml
    what: Add lineage to the existing CODE research-price-panel command and consolidate five EDGAR suites plus the WRI and DAG CODE commands with all test files, options and inferred scopes preserved.
verified:
  - claim: Independent source review accepts the repaired seven-file core with explicit production adoption gates.
    command: Independent science review of the exact repaired source manifest.
    result: PASS_SOURCE_CORE_WITH_EXPLICIT_PRODUCTION_ADOPTION_GATES; all seven reviewed SHA256 values preserved through the backend and main unions. The later CLI-only standard import-pin repair is separately independently accepted; the six non-CLI core files remain unchanged.
  - claim: The expanded actual CODE research command includes all prior suites and the new lineage suite.
    command: The exact research-price-panel pytest command from the committed CI manifest.
    result: 882 passed and 409 subtests passed in 177.43 seconds; three existing environment deprecation warnings.
  - claim: The five consolidated EDGAR suites retain their coverage.
    command: python3 -m pytest tests/test_edgar_8k_items.py tests/test_edgar_8k_counterparty.py tests/test_edgar_quarterly_tags.py tests/test_edgar_universe_widening.py tests/test_edgar_fts_confirmed_absent_first_request.py -q
    result: 145 passed in 4.89 seconds; no inventory, dependency or selector removal.
  - claim: The existing packing budgets remain satisfied.
    command: Full selected-job set comparisons across the three canonical packing probes.
    result: 134 jobs at weight5792, 134 at5597, 129 at5559; ten packs each and zero breaches. Reused actual full-tree measurement with exact equality of changed-job inferred scopes and all other definitions. Research55 to57 is balanced by EDGAR50 to48. WRI48 to34 and DAG28 to21 recover an inherited main packing breach; no ceiling increase.
  - claim: Consolidated CODE commands retain complete owning coverage.
    command: Exact WRI and DAG grouped commands; Node20.20.2 for existing JS contracts.
    result: WRI415 passed, two inherited absent-nightly-library skips; DAG217 passed. Nine missing sparse fixtures hydrated from exact HEAD, with no content edits.
  - claim: Hosted import-closure and CLI-pin failures are repaired without waivers or omitted tests.
    command: test_check_script_import_pinning.py plus test_market_memory_lineage.py; test_ci_pack.py::test_curated_exclusive_scopes_cover_their_own_import_closure.
    result: 75 CLI-pin/lineage cases passed; corrected full exclusive closure test passed. Independent review848a3c5a confirms exactly five added dependency paths across three existing jobs and standard unconditional root pin. All other job fields and old paths are unchanged.
  - claim: The fresh-main union satisfies newly enforced exact import scopes without changing reviewed lineage source.
    command: Complete exclusive import closure, three canonical job packing probes and independent C1_FRESH_MAIN_CI_REVIEW.json.
    result: Zero closure findings and packing breaches; 133/133/128 jobs, weights5659/5464/5426 and ten packs under unchanged ceilings. Exactly four paths added across three existing jobs; all seven accepted source hashes preserved. Independent receipt075a3d15634c01cadc915089c72add6208640d2867f085cff0ae3649c17842d0.
  - claim: Existing owner regression failures remain distinct from the new source acceptance.
    command: Exact owner tests against the original committed data fixtures.
    result: 100 passed; two inherited options-ledger row and byte cap refusals retained. No cap increase or data pruning.
unverified:
  - claim: Production lineage is qualified and admitted.
    what_would_verify: Exact installed producer, actual full-chain bounded qualification, current exact-publication admission and real owner reads.
  - claim: A durable production certificate publisher is delivered.
    what_would_verify: A separately reviewed same-owner publisher with exact source HEAD and prior-pointer checks, interruption reconciliation and existing owner lock.
  - claim: Hosted checks and normal installation prove this final source.
    what_would_verify: Exact current-head CODE checks, normal protected merge and installed-byte verification on the original delivery chain.
unresolved:
  - The original Fabric patch was rejected and remains NOT_ACCEPTED; this independently repaired successor is a distinct source artifact.
  - Offline ceilings512MiB total,64MiB batch,30CPU seconds and60wall seconds are implementation bounds, not a production execution grant or permission to raise online limits.
  - Source ownership and file custody alone do not grant certificate use, retention, comparison, training or promotion.
  - Actual 401/auth callback, signout and naturally ordered late-response browser cases remain open on the otherwise merged and live-verified UI8694.
next_actions:
  - Backend9098 is merged and installed; publish and qualify this same lineage carrier through ordinary CI and merge.
  - Implement and review the bounded same-owner publisher and actual installed qualification without rerunning old captures.
  - Continue current source-purpose policy, real consumers, three-mode inspection and independent scientific acceptance.
do_not_redo:
  - Preserve the terminal August MM-G0 result, existing v1 and v2 opportunities, source clocks and original data bytes.
  - Preserve original full-ancestry online readers and their64MiB and4096 bounds.
  - Preserve the root01a1333c-a475-7052-95a8-72c623fb12e1 and all retained Fabric operations; no replacement or root-budget reset.
danger_areas:
  - A certificate proves qualified same-owner publication lineage, not external origin or clock authenticity.
  - A newer source HEAD yields proof_pending and must not silently substitute another certificate or generation.
prs: [6528, 8694, 9078, 9098, 9140]
---

All28 tasks and49 acceptance cases remain assigned. This source checkpoint is not
whole-program completion, production qualification or operational admission.
