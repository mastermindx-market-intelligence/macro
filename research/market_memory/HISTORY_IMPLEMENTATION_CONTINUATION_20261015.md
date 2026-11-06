# Market Time Machine integration implementation plan

Goal: make existing source-bound historical daily dossiers usable through the installed, authenticated Data & Lab command, retain an independently verified offline browser, and preserve exact scientific limitations.
Architecture: reuse Market Memory archive/dossier producers, DataWorkspace descriptor-confined roots, existing Studio transport, accepted immutable releases and the existing workflow plugin. No new dataset, scheduler, authentication, live signal ledger or provider call.
Spec: HISTORY_VIEW_DESIGN_20261015.md and docs/data/WEB_DATA_WORKSPACE.md.

## Recovery
Original operation and root/parent: market-time-machine-20261015. PR9445 at c174507305bdb8170665fd535263805e59e6e4ce. Recovered unpublished second-phase changes remain in the original managed workspace; no relevant active host writer was observed. The original review has a terminal retained response, consciously not accepted after adjudication; it is not rerun.

## Execution sequence
1. Qualify recovered integration: existing 155 focused tests passed on Python3.14/Arrow25. Run all affected Data & Lab regressions and inspect the real dossier through scripts/data_workspace.py with existing host binding. Add failing tests for any actual defect before repair.
2. Review two frozen, independent surfaces through the original-root Fabric: archive/transport confinement; numerical/macro/dossier/browser semantics. Require concrete reproducers, source hashes and a bounded verdict. No edits delegated.
3. Extend the existing Data & Lab workflow source and usage guide with exact history_dossier fields, discovery of retained manifest hashes, and outcome isolation. Keep source references and digests explicit. Add request-contract tests before changes.
4. Publish all verified owned source changes to the original branch; integrate current protected-base compatibility, canonical CI enrollment and required independent review. Do not weaken other checks or overwrite shared checkout state.
5. Once accepted and merged, export an immutable release using the existing verified runtime mechanism; verify capabilities and real historical/legacy consumers before selecting the launcher. Use compare-and-swap preimages and preserve prior release for rollback.
6. Advance the broader capability with retained data only: exact source coverage and separately scoped stock/catalyst history where evidence permits, without representing a proxy pilot as complete all-market history.

## Critical checks
Unknown dates stay empty; default dossiers never read outcome files; root/path/descriptor boundaries hold during replacement; macro first prints never become full vintages or invented consensus; all response and decoded-byte bounds are enforced; current-rule retrospective output never becomes historical published truth.

## Completion
A real installed command must consume a retained manifest and macro chronology to answer an exact date, with matching hashes, explicit gaps, no source writes and an unchanged legacy Data & Lab path. Source publication, installation, workflow enrollment and user-visible product acceptance are separate evidence. Broader coverage, strict PIT and predictive efficacy remain independently qualified obligations.
