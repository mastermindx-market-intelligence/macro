# International R12 — production path and release gates

## Candidate and scope

Original operation: `intl-country-cockpit-20261018`. Original branch: `sol/web-intl-country-cockpit-20261018`. Delivery carrier: [Macro PR #9596](https://github.com/mastermindx-market-intelligence/macro/pull/9596). Published R12 semantic parent: `88b6f192c3e2a7a94f5cf7ff4d9d06bc225324a4`. The CI integration follow-up remains on this same carrier; its accompanying verification receipt binds the exact changed file bytes.

The primary experience is World Brief → seven country assessments → global connections. Each country separates its sourced national thesis, official growth/inflation path, market observations, transmission channel and conditions that would change the interpretation. Existing comparison, history and research tools remain subordinate. The earlier PR #8754 and its independent Saved, source/access and release obligations are preserved.

## Actual production input chain

`IntlMacroAdapter.fetch()` calls its existing `_refresh_country_inputs()` method. That method acquires the bounded country sources through the adapter's existing HTTP owner, merges each source independently with last-good records and atomically replaces `data/intl_macro/country_inputs.json`. Source failure retains the dated prior evidence; it does not manufacture a current observation. The new WEO publication archive and national decision records belong to that same refresh path.

`lib.intl_country_inputs.load_country_inputs()` reads the reviewed initial snapshot in `config/intl_country_baseline.json`, merges the collector's last successful `data/intl_macro/country_inputs.json`, and reads the editorial national commentary configuration. Its read limit is 1.5 MB. It does no network acquisition and writes no data.

`scripts.build_intl.main()` gets incumbent market/regime records from `engine.intl_run.run()`. It passes those records and the independently loaded official observations, forecast archive, commentary and policy decisions into `build_country_assessments()`. The normal `render_international_pages()` composition then renders the existing macro/stocks template. No research-preview market fixture is selected by this production call chain.

The builder writes `site/intl.html` and `site/intl_stocks.html` through `lib.pages.write_page`, plus the existing per-stock shell. Its configured asset loop uses `lib.site_assets.copy_asset`. The reviewed forecast/policy seed can supply a dated baseline before the first collector refresh; that does not prove a live refresh has executed.

## Country-controller delivery: confirmed inline

`templates/intl.html.j2` includes `intl_country_cockpit.js` inside an ordinary inline `<script>` when the country analysis is present. It does not request a separate `intl_country_cockpit.js` URL. The initial external-asset hypothesis was disproved by this final-template trace and is not a product defect or a reason to widen access policy.

The canonical page writer retains the controller. The ordinary post-render JS externalizer lifts only scripts marked `data-externalize`; the country controller has no such marker and remains inline. The new regression in `tests/test_intl_build.py` exercises the actual rendered template, page writer and externalizer and verifies exactly one intact controller, an actual country target, and its absence from stock mode. The fresh build/public-HTML selection passed 10 tests.

The existing Caddy configuration serves HTML documents publicly; its tests confirm the paired static policy. Neither `config/site_access.yml` nor `app/deploy/Caddyfile` is changed by this increment. Signed-in access, protected data delivery and the nine pre-existing legacy workspace assets remain separate acceptance questions.

The shared color-token source and its paired `site/theme.css` were emitted through `lib.site_assets.copy_asset` and are byte-identical. Their SHA-256 is `61428c7d20e6b4a47450def2301d1f087eac354d1db4ec04be001e39a74d2eb7`.

## Browser and design evidence

The published R12 semantic receipt preserves 160 passing Python cases in nine files. Its integrated Chrome verification passed 12 viewport/theme/language states and ten country/navigation/degradation journeys. These are dated, isolated fixtures, not live-market acquisition or signed-in production evidence.

The CI follow-up adds the repository's canonical `mastermind.p0_evidence.v2` receipt at `mockups/evidence/intl-country-r12/manifest.json`: 24 of 24 actual captures, with eight desktop/phone × EN/ZH × dark/light rest states and 16 actual hover/focus states. PNG hashes, byte counts, dimensions and applied states pass the normal evidence validator. The three material paths in the complete original-base-to-candidate diff are owned by its three-key `EVIDENCE.yml`.

The color blends were moved unchanged into shared-theme variables. A real Chrome comparison of the original and new source/assets found identical computed colors, backgrounds, borders, outlines, shadows and background images for all 3,168 International elements in both themes at rest, hover and focus. Full screenshots are not claimed pixel-identical: their raw comparison is preserved and includes shared-chrome changes.

The canonical capture reports a missing fixture-only `live_config.js` and the deliberately aborted external analytics script. It preserves its access/degraded-state gaps. Its two H1 nodes are the primary country heading and the retained workspace heading inside subordinate tools. No document horizontal overflow was observed. These facts do not constitute a blanket accessibility or formal taste approval.

Paper R12 remains the editable build reference: https://app.paper.design/file/01M3P1TW5Y3XWQC37ADDS8K5AG/p-G-0. The six boards and all 67 observed effects are bound in `paper_r12_receipt.json`. This CI follow-up changes no Paper board or country-analysis semantics.

## Normal release path

1. Conclude the exact current PR head's binding CI and required independent release review. A draft, local pass or inherited-base classification is not a release waiver.
2. Use the ordinary expected-head protected merge on the original PR. Verify the intended source bytes on fresh main.
3. Observe the normal `.github/workflows/render.yml` run. It accepts `scope=intl` for an explicit narrow render; ordinary main-branch template/builder changes trigger its existing scope resolution. The shared-theme/other template changes may resolve to a wider scope. Do not dispatch a candidate branch into production as a substitute for merge.
4. The render lane builds from committed inputs, runs the standard publication transforms and commits the resulting `site/` output to main. Bind the actual render commit and its `from=` source identity; a successful process exit alone does not prove the requested HTML was regenerated.
5. Obtain the actual existing VPS publication receipt. The Caddy origin serves `/opt/macro/site.served`, not this development worktree. The repository's older comments refer to `pages.yml`, which is absent from this checkout; that comment is not proof of a current deploy workflow. Resolve the actual current deployment owner before claiming this edge complete.
6. Verify https://www.mastermind-x.com/intl.html on the served path: country markup and source dates, emitted shared/CSS assets, inline controller behavior, desktop/phone, both themes/languages, keyboard/history, denied-data behavior and the incumbent assistant. Compare actual served bytes to the real render, not the synthetic preview. The earlier web lookup timed out and supplies no production-content proof.

## Unresolved release dependencies

The published parent CI run `39185847530` found 67 introduced contract findings (63 missing declared dependency paths across six jobs and four unwired country test suites) and six page-local color-blend findings. This follow-up repairs those owned causes, supplies canonical browser evidence and pairs the shared-theme output. Fresh hosted CI on the follow-up remains authoritative.

The same run also failed reference integrity on three pre-existing Sector Central migration packets. The exact-base replay fails on the same files. The source owner's existing recovery record is [PR #9592 comment 6248814344](https://github.com/mastermindx-market-intelligence/macro/pull/9592#issuecomment-6248814344), updated 2026-10-19 04:40:45Z, under parent issue #7646. It explicitly requires Full RIG on the actual frozen before/after artifacts, independent product/visual reviews and the designated authority's genuine verdict before adding approved receipts to all three packets. It also records that inherited-base classification does not release dependent gates. This International operation does not approve, rewrite or exempt those packets.

The existing session-discovery action returned `backend_unavailable` with “installed Session Bridge owner is unavailable.” No reviewer was dispatched through that failed discovery. The native principals' bounded economic/design judgments remain useful advice; they are not relabelled as the missing formal release review. No speculative alternative publisher, reviewer, session registry or deployment path is created.

Coverage limits remain explicit: fiscal/debt paths are not admitted for KR/TW/IN/AU; a newer RBI decision lacks adequate primary admission; CBC's official page was read but its host download failed certificate validation, so there is no claimed raw-byte hash for that response. Required source/rights and actual served acceptance remain independent of code and screenshot completeness.

**State: built and reviewable; release not accepted; production delivery not proven.** The precise continuation is to consume the original dependency repairs, conclude the same-head hosted checks and independent review, then complete the normal render, deployment and served acceptance chain.
