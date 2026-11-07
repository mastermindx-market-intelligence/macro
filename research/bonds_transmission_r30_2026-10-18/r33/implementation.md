# R33 — source inspection built on the accepted Bonds × Transmission journey

## Capability and scope

R32 completed the requested light design, eight product workspaces, fifteen tool families and progressive analytical tools. R33 adds a working source inspector and an additive publication in the existing Macro builder. The 19 October delta mounts the strict adapter and inspector in the existing Bonds template and publishes an exact-byte mirror behind the existing site access boundary. The result remains **BUILT_NOT_PROVEN** for production: 54 new actual-template HTTP browser checks and the earlier 176 existing Bonds owner pytest checks are retained, while release and deployed-origin proof remain gated.

Read [PRODUCTION_INTEGRATION_2026-10-19.md](PRODUCTION_INTEGRATION_2026-10-19.md) and the [current cumulative handoff](SESSION_HANDOFF_2026-10-18.md) for the current source path, receipts, source dates and existing-owner next actions. The reference journey below is retained baseline documentation; its 65+26 offline journeys were not rerun.

Before R33, the offline reference could explain source requirements but had no working route from the existing decision-workspace projection to inspectable field origins. After R33, the user can inspect a pinned captured publication, trace 22 displayed fields, compare component dates, identify the next missing evidence, and test a local publication without changing the surrounding research case.

The full current reference is [reference/index.html](reference/index.html). Its build checks the immutable R32 HTML digest before applying the extension. R32 source and analytic contracts remain controlling for all unchanged tools.

## User journey

1. Open **Sources** in the existing reference header. The first view contains three readings, concise health/duration context, dates, and one next action.
2. Select a reading to see its selected file and field, component date, missing observation/availability clocks and any scope-specific limitation. Candidate paths and the raw value open only on demand.
3. Use **Fields** to search all 22 fields. Back restores both the search and keyboard focus.
4. Use **Dates** to compare the six supplied clock definitions; the primary screen shows the five relevant component summaries. Related regime-series vintages and declared publication identity are expandable.
5. Use **Missing evidence** to see the three unresolved input groups for the Treasury-relief test: the exact Treasury observation, matched credit peers and current qualified funding evidence.
6. Choose a local JSON publication to inspect it in this tab. Pending validation clears sourced values. A failed file stays unavailable until an explicit restore or successful new import. An older asynchronous import cannot overwrite an explicit restore.

The inspector reuses I01/I03 and the existing dialog family. It adds no product route or tool family. Mobile uses a scrolling sheet, two-by-two tabs, compact metric rows and visible close controls. English and Simplified Chinese labels, keyboard focus, Escape, dark-theme compatibility and 44 px controls are covered by the reference.

## Existing publisher integration

Repository change: `scripts/build_macro_context.py`.

The existing `_build_view_model` remains the sole projection builder. The main function still writes the exact five-key `data/macro_context/latest.json` hub. It passes that same view model and the already-loaded inputs to `_build_decision_publication`, serializes once, and writes identical bytes to `data/macro_context/decision_workspaces.json` and `site/macro-context-data/decision_workspaces.json`.

The companion adds display provenance; it does not introduce a market selector, event engine, signal policy, persistence service or monitoring service. The existing Bonds template now includes the strict adapter and scoped presentation/controller sources. The existing Bonds CI owner registers both relevant test suites. No new CI job, waiver, render DAG, access policy, Forex template or CDI change is introduced.

The loaded inputs are the Macro snapshot, NeuralWeb world state, regime data and the existing loader's last 60 parsed transition rows. Hashes describe those loaded values, including nonfinite-value diagnostics. They do not reread files after the view model was selected.

See [data_contract.md](data_contract.md) for the exact meaning and limits of clocks, hashes and field lineage.

## Consumer boundaries

`source-adapter.js` accepts the exact v1 schema and display-only markers. It allowlists the existing field mappings and selected origins, checks dates and types, preserves zero, and leaves an invalid number unavailable. It never substitutes a synthetic fixture after a rejected import.

The inspector keeps separate state from the accepted case, rule, observation and evaluation state. Its capabilities to evaluate, forecast, retain or monitor remain false. Imported strings are escaped before rendering. Known descriptive enum labels are translated for readability; their original values remain inspectable.

The browser consumer displays the publisher-declared content digest. It does not claim to authenticate the publisher or recompute Python's canonical JSON hash. Import is local and tab-scoped. The retained offline reference makes no HTTP request; the production-template port uses only an on-demand same-origin GET of `/macro-context-data/decision_workspaces.json`, with no captured fallback or backend write.

## Native Paper

The existing S01 atlas contains desktop and Chinese mobile source specimens plus field-origin, unavailable-import and missing-evidence states. S05 contains six compact implementation cards for overview/detail, dates, import, publisher, adapter and accessibility. C04 now distinguishes the built companion from unresolved qualified observations. Both START guides point to R33.

The changed native exports in [native/](native/) supersede the matching S01, S05 and START exports in the R32 package. S04's only change is canvas position, clearing the expanded S01 atlas. All other R32 native exports remain applicable. The cumulative current set remains 21 owned artboards; the two CDI boards from the concurrent credit session are excluded.

## Reproduce the reference

From this package's parent directory:

```sh
node r33/build-reference.cjs
node r33/test-source-adapter.cjs
MMX_CHROMIUM_PATH=/path/to/chromium node r33/test-source-journeys.cjs
MMX_CHROMIUM_PATH=/path/to/chromium node r33/test-core-journeys.cjs
```

The browser harness requires Playwright in the developer environment. It opens the local HTML and aborts/counts HTTP(S) requests. The HTML itself requires neither a server nor external assets.

From the repository root, the bounded publisher regression is:

```sh
python3 -m pytest tests/test_macro_decision_publication.py tests/test_macro_context_authority.py -k 'publication or r25 or r26' -q --disable-warnings --maxfail=2
```

The font asset uses a renamed, openly licensed Noto CJK subset. Its provenance and reproducible subset script are in [assets/](assets/); the self-contained HTML includes the license.

## Exact integration continuation

The additive companion is connected to the existing Bonds source template. Complete independent exact-source review and required checks, then follow the actual existing release gate and prove the deployed generator, protected publication and production Bonds browser behavior. Preserve the five-key hub and v1 display-only limits. The existing draft PR #9578 and original branch remain the carrier.

Qualified instrument/quote/availability evidence remains the prerequisite for actual event evaluation. Terminal Investigation v2 remains the owner for admitted retained research and exact reads. Terminal Alerts remains the owner for compound-rule admission, evaluation, dry runs and receipts. Calibrated likelihood requires a defined target, horizon, point-in-time history, out-of-time performance and abstention. These capabilities are not made live by this source inspector.
