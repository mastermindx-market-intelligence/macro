# Sector producer foundation — November 6 implementation evidence

Mission: [pinned always-on Macro migration #10779](https://github.com/mastermindx-market-intelligence/macro/issues/10779).
Plan: [master plan](ALWAYS_ON_MACRO_MIGRATION_2026-11-05.md).
Status: source implementation and focused tests qualified; hosted release, installation and independent daily production remain open.
Managed carrier: `macro-always-on-sector-core-20261105-c3`.
Source base: Macro `86e8da1ff4c316affe402ae480cde0002550762b`, incorporating the published monitor/CI repair.
Protected law pin: Mastermind `49c2e1d93e5e080b1671c98087a845e5beb09dd5`.

## 1. Explicit Sector fusion

`engine/sector_central.py` now exposes `compute_from_inputs(SectorCentralInputs, evaluation_date=...)`.
Existing `compute()` keeps its caller signature, acquires the established sources, resolves calibration through the established helpers, and delegates to the same calculation.

The declared inputs are the already computed cycle spine and market context, close panel, narrative rotation, membership document and source availability, raw rotation artifact, published rotation events, and resolved fusion calibration. The evaluation day is explicit. Calibration identity uses the original beta lookup key plus risk family and timing state, not row order or an ambiguous record index. Missing or invalid calibration fails without falling back to configuration.

The core uses the selected pre-gate rotation document to distinguish stale from absent data. It does not re-read a mutable file on that branch. Empty rotation events and an available empty membership document remain distinct from unavailable inputs. Mutable output documents do not alias the supplied cycle, market or event documents.

This is an input boundary for **fusion**, not a claim that `sector_cycles.compute()`, market context or the entire daily research pipeline is already independent. Their source selection and writer transfer are the next required work. Calibration meaning and `CONVICTION_SCORE_VERSION` are unchanged.

## 2. Preserve the action-board envelope

The bare action-board write in `scripts/build_site.py` now delegates to the existing `scripts/build_sector_action_board.py::write_action_board` publisher. The already assembled rows are preserved; the repair does not recompute the sector view model.

The existing atomic JSON writer is reused. One basket byte snapshot supplies both validation and the published SHA-256. Invalid/missing basket data, unusable source dates and empty action lanes are rejected before the previous output is replaced. The generated timestamp does not become the source date.

The hash identifies the basket generation observed at publication. It does **not** prove common provenance for every other action-board input or make the entire legacy Sector bundle atomic. In particular, the legacy engine-render ordering can subsequently rebuild baskets. Coherent runtime generation promotion and producer fencing remain required; the independent monitor continues to expose inconsistent legacy bundles.

### Worker return and parent integration

Original Fabric run: `macro-always-on-20261105-c3-action-writer-01`.
Returned response: 5,207 bytes; SHA-256 `cada66fd8773b8b1a1cf1b4864535fd5ee9e106f17ee855f130b70ff7cb5cf9d`.
The wrapper ended rc1 with an unrecognized-model provider error after returning a claimed committed result. It is not recorded as a successfully accepted Fabric execution.

The parent verified immutable worker commit `f590538e86de39fa847bc7280b520b73579a5199` directly on its original host: parent `0c4c28e4a3e1ba0b1dde3ebdd9774355822f1527`, exactly three changed files and a clean worker tree. The transferred diff SHA-256 is `0777cff1c4e1f5b66311cc70e8622dd4edf55190b882f0ba8073e502da6aff11`.

Parent review consolidated the proposed extra wrapper into the existing writer, removed the redundant basket-file read, strengthened invalid-date handling, and narrowed the publication claims. The code and test evidence below are parent-verified; the worker's original completion label is not used as release proof.

## 3. Validation

The final combined command passed **210 tests**:

```text
python3 -m pytest tests/test_sector_central.py tests/test_sector_generation_guard.py tests/test_sector_central_score_version.py tests/test_sector_central_measured_panel.py tests/test_sector_intelligence_page.py -q --tb=short
```

The meaningful new checks include:

- An explicit-input calculation with data/configuration readers, filesystem access, network calls, evaluation-clock acquisition, legacy calibration and grader/ledger functions trapped. The trap derives from `BaseException` so an existing fail-soft `except Exception` cannot hide a forbidden call.
- Repeated calculation equality, input immutability and non-aliasing of returned nested documents.
- Supplied zero beta and changed risk calibration affecting the established arithmetic; absent calibration cannot silently load a default.
- Explicit future-session rejection, stale versus absent rotation, mismatched event generations, and missing versus empty membership.
- Canonical action-board metadata, reproduction of the old bare-envelope failure against the actual generation gate, one basket-file read, and preservation of the prior artifact on invalid sources or empty boards.
- Execution of the existing redirect JavaScript with and without the shared-shell bridge. This replaces obsolete literal `location.replace("target")` assertions while proving the actual target and replacement mode. Templates are unchanged. The existing 4 KB template-content and 12 KB rendered-stub budgets remain; non-rendered Jinja comments are excluded from the former.

Six unrelated pytest temporary-directory cleanup warnings were reported. No unrelated shared temporary files were removed.

### Full-output parity

The unchanged source implementation at `0c4c28e4a3e1ba0b1dde3ebdd9774355822f1527`, the compatibility adapter, and the explicit-input entry point produced identical complete payloads in **16 deterministic cases**: absent/aligned/stale/future rotation crossed with normal/empty/missing/malformed membership. Twelve distinct output digests demonstrate that the cases do not all reduce to one constant result.

- [Parity receipt](ALWAYS_ON_SECTOR_FUSION_PARITY_2026-11-06.json)
- [Reproduction script](verify_sector_fusion_parity.py), run from the repository root with the pinned base object available.

These are constructed source-parity cases, not production data, forecasting validation or authenticated browser acceptance.

### CI dependency closure

The new canonical-writer import makes `scripts/build_sector_action_board.py` reachable from nine existing exclusive jobs. Nine exact path entries were added to their existing path lists. No scope mode, job, test, gate, packing ceiling or wildcard was changed. Both focused CI checks passed (2 tests, 255.84 seconds): `test_curated_exclusive_scopes_cover_their_own_import_closure` and `test_exclusive_curation_narrows_ordinary_code_prs`. The six existing shared temporary-directory cleanup warnings were unchanged.

## 4. Concurrent source work

Read-only, complete paginated file inspection found PR #10703 (`9fc460ff36345387c3a2c5435b079852e8488da0`, draft) overlaps only the CI manifest in this change. PR #10777 (`937009aea2b533dd7bab7cdcd3eabf465429e0cf`) overlaps the CI manifest, `scripts/build_site.py`, and `tests/test_sector_intelligence_page.py`. Its latter two patches add sector dossier assets/members and adjust Cycles view assertions; this change repairs action-board persistence and redirect execution assertions in separate sections. Neither external carrier was modified or armed. Reconcile their actual resulting source state before release if they advance.

## 5. Remaining acceptance

No collector, scheduler, runtime unit, entitlement rule or live publication pointer is enabled by this source change. No full builder is repurposed as a frequent runtime job.

The next independent daily slice must transfer the selected close lineage through the existing store/orchestrator, fence its old collection writers, supply explicit versioned dependencies, promote a coherent accepted generation, and show the changed values in an already-open authenticated beta view with unchanged frontend code. Full research freshness and original Brief/Explore/Research/Watches parity remain required by the master plan.

A separate bounded source census, `macro-always-on-20261105-c3-close-owner-01`, is tracing the exact Yahoo writer/consumer transfer. A controller creation or polling observation is not worker-start or durable-execution proof. Its original run is preserved.