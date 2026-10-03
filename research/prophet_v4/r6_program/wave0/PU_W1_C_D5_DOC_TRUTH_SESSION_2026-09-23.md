# PU W1 C D5 Doc Truth Session — 2026-09-23

STATUS: COMPLETE

## RESULT

- **A13 clause 1 — resolved.** `research/prophet_v4/flagship_cells/CELL_F_D5_CONTRACT_AMENDMENTS_2026-08-26.md:369` names `IssuerMaster.cik_of_issuer`, its current-registrant/conflict-refusal behavior, and the D5 consumption path; the dated resolution note is at `:373`.
- **A7 clause 2 — current-body seams.** `load_current_workspace` and `load_workspace_with_disposition` are forbidden at `:54-58`; production callers and the none-feeds-D5 statement are at `:63-65`.
- **A14 — two earnings planes.** The new clause begins at `:413`; it separates PR #7294's EquityDesk plane from the D5 company-intelligence plane and records the typed consensus absence at `:415-425`.
- **Registry row — refreshed.** `research/prophet_v4/SOURCE_RIGHTS_AND_COVERAGE_REGISTRY.md:50` quotes WS-EIO `status: done`, removes the stale E0/E1/E2 and `ACCRUING` wording, keeps the Wire/CI divergence citation, and states the permanent typed beat/miss absence.
- The PR carries only these two ruling-owned research documents plus this mandated session skeleton.

## EVIDENCE

- Citation checks used `git show origin/main:<path> | nl -ba | sed -n '<range>p'` on every newly cited source, including `lib/dataos/identity.py:929-946`, `engine/prophet_lab/intelligence_vector.py:1055-1057`, `engine/neuralweb/company_intelligence_reader.py:1006,1022`, the three production callers, `engine/prophet_bridge.py:3918-3931`, `engine/company_intelligence/event_workspace_build.py:355-400`, and `agentos/workstreams/WS-EARNINGS-INTELLIGENCE-OS.md:9,63-81`.
- `python3 scripts/check_validated_claims.py 2>&1 | tail -2`: exit 1; final receipts reported existing otherwise-unearned claims in unscanned/generated templates, ending `templates/macro_labor_markets.html.j2:6` and `... and 26 more`.
- `python3 -m pytest tests/ -q -p no:cacheprovider -k "validated_claims or prophet_v4_doc or registry" 2>&1 | tail -3`: `13 skipped, 54 errors in 27.64s`; collection raised `INTERNALERROR> SystemExit: The stripe SDK is required`, an unrelated missing environment dependency.
- Narrow fallback `python3 -m pytest tests/test_validated_claims_registry_source.py -q -p no:cacheprovider`: `14 passed in 1.10s`.
- Narrow fallback `python3 -m pytest tests/test_validated_claims_engine.py -q -p no:cacheprovider`: `1 failed, 32 passed in 37.45s`. The sole failure is the live engine scan finding an unrelated unearned claim at `engine/market_os/macro_workspaces/consumer.py:108`.
- Before base refresh: `git diff --stat $(git merge-base HEAD origin/main) HEAD` showed 3 files, 46 insertions, 15 deletions. After the normal origin/main merge, `git diff --stat origin/main...HEAD` showed the same 3 files, 46 insertions, 15 deletions. Per-file additions were preserved: registry 1/1, amendments 34/34, session skeleton 11/11.

## GAPS

- The prescribed broad pytest selector remains blocked by the missing unrelated `stripe` dependency; installing it would have violated the package-lock law.
- The unrelated pre-existing validated-claims findings remain untouched by this doc-only lane.

## DEVIATIONS

- The broad pytest selector could not execute to completion because of the pre-existing missing `stripe` dependency; narrow real validated-claims tests were run instead. This is an evidence limitation, not a scope change.
- `origin/main` advanced during work, so it was merged with a normal merge commit; all pre-merge PR additions were verified intact afterward.
