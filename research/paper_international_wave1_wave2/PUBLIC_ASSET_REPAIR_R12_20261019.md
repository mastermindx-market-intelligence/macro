# International R12 — public presentation asset repair

Recorded 2026-10-19. Original operation: `intl-country-cockpit-20261018`. Carrier: [Macro PR #9596](https://github.com/mastermindx-market-intelligence/macro/pull/9596).

## Result and custody

The source repair and regression coverage are prepared in the existing working tree, after frozen local HEAD `11c83bb5dfb0c8199a0fb0cb2c6e70452c724984`. They have not been committed or pushed. The current remote PR head remains `88b6f192c3e2a7a94f5cf7ff4d9d06bc225324a4`.

The original push action `d07df7c6e45d35c54338808701350ece97c605401ad69a0fd28bb415d05a5a56` remains EFFECT_UNKNOWN. These working-tree edits do not alter its frozen commit object, replay the push, or establish a deployment. Preserve the earlier R12 and CI-integration evidence as dated records.

## Production defect established

The real anonymous page at https://www.mastermind-x.com/intl.html displayed the old International Economies page dated 2026-10-15, visibly unstyled workspace content and disabled workspace controls.

Two exact asset URLs referenced by that delivered HTML returned HTTP 401 during this resumed session:

- https://www.mastermind-x.com/intl_workspace.css?v=e321de56
- https://www.mastermind-x.com/intl_workspace_state.js?v=54575d37

The shared https://www.mastermind-x.com/theme.css?v=2e861147 loaded successfully. This establishes a presentation delivery defect independently of the dissatisfaction with the old design. The other seven dependencies were found missing from the source serving rules; no individual live HTTP result is claimed for those seven.

This is distinct from the disproved earlier hypothesis about a separate R12 country controller file. The new country controller remains correctly inline through the normal HTML publication path.

## Narrow source change

`templates/intl.html.j2` actually references these four CSS and five JavaScript files:

- `intl_workspace.css`
- `intl_workspace_macro.css`
- `intl_workspace_risk.css`
- `intl_workspace_history.css`
- `intl_workspace_state.js`
- `intl_library_search.js`
- `intl_workspace_scenario.js`
- `intl_workspace.js`
- `intl_workspace_entry.js`

The repair adds those nine exact paths to `config/site_access.yml` public.exact and to the existing `@reg_asset`, `@reg_asset_err`, `@public_static`, and `@public_versioned` path lists in `app/deploy/Caddyfile`.

No prefix, wildcard, account category, denial rule, premium rule, API handler, or cache query/header directive changes. The source/served copies of all nine files are byte-identical. Their hashes are recorded in the companion receipt.

A bounded independent source review found presentation, local state/search, manual scenario arithmetic, and existing-DOM interaction in these files, with no customer records, credential handling, embedded financial dataset, or network transport. That review is advisory. It does not qualify every value already serialized into public HTML or grant access to data/API responses.

## Verification

The new test reads the real page dependencies, requires the reviewed exact paths in all four matchers, qualifies emitted copies, and rejects both actual internal-artifact names and synthetic neighboring payload/map/suffix paths. API routing exclusions remain separate from public cache policy. The existing registered-only macrodata category is preserved.

- Before the repair: the new regression failed on the nine missing public entries.
- After the repair: all **28 tests in tests/test_site_access_boundary.py passed** in 73.69 seconds.
- Parsed policy comparison: the only semantic policy delta is the nine exact additions.
- Source Caddy comparison: the only textual delta is appending those nine paths to the four existing path lists.
- Real installed Caddy adapter: baseline and candidate both parse successfully. A controlled comparison using the same config input path finds nine additions in each of eight expanded HTTP/HTTPS path lists and **zero other adapted JSON differences**.
- An initial adapter comparison using differently named input files failed its whole-JSON equality assertion. The controlled same-input-path comparison resolved the discrepancy; no live server operation was involved.
- `git diff --check` passes. HEAD remains `11c83bb`.

The pre-repair pytest invocation also emitted two host temporary-directory cleanup warnings; the complete passing run used its own temporary directory and emitted no warnings. Logs and the controlled adapter comparison are preserved under `public_asset_repair/`. Trailing spaces on two pytest diagnostic separator lines were normalized in the readable before-fix log; its exact original bytes are retained in `boundary_before.log.gz`.

## Accepted rollout and remaining evidence

Source ownership was verified at Macro main `73d8e2fb35b98ab3e24e5d4532832545ccf87fe5`:

- [setup.sh](https://github.com/mastermindx-market-intelligence/macro/blob/73d8e2fb35b98ab3e24e5d4532832545ccf87fe5/app/deploy/setup.sh) installs the existing macro-update owner and schedules its three-minute cron.
- [update.sh](https://github.com/mastermindx-market-intelligence/macro/blob/73d8e2fb35b98ab3e24e5d4532832545ccf87fe5/app/deploy/update.sh) publishes site.served and compares, validates, installs, and reloads the Caddyfile. Configuration reconciliation also runs when Git is already current.
- The updater includes config/site_access.yml in its existing macro-api restart trigger.

After the original push is reconciled, this repair must pass through the existing PR's publication, actual-head CI/review, and normal merge. The same installed updater owns the Caddy and API-policy adoption. The broader R12 template/builder change additionally needs a successful covering render.

Acceptance still requires installed configuration identity, successful Caddy reload and healthy service, API-policy adoption, and anonymous HTTP/body/cache checks against the exact asset versions referenced by the served HTML. A successful repository pull alone does not establish those outcomes. Country-first R12 rendering and actual production journeys also remain required.

No commit, push retry, merge, deployment, service restart/reload, or production repair is claimed by this record.
