# Decision Desk R4 — current owner source compatibility

**Original PR #9611 · Draft/HOLD · BUILT_NOT_PROVEN.** Source parent `32fdf32aeca4607c5fee1b51e26ef42d8c633ce4`; the containing commit identifies this test/evidence increment. It changes no production frontend, API, native publication, identity source, entitlement or release control.

## The capability gap closed

The retained Company evidence fixtures were generated from owner head `430234957531693b6b13f026a161e28542086a82`, before the R10 and native-adapter integration now published on #9662 at `902465f702a30abb943b08e792d670827a68650b`. Passing the old fixtures did not prove the current owner still emits a wire the Decision Desk can consume.

This increment captures **nine exact HTTP response bodies** from that current, clean owner checkout using its existing synthetic source/identity fixtures and TestClient harness. The actual unchanged Decision Desk consumes all eight list/query responses and the one selected detail. The eight current list/query responses each add the third `dataos_vendor_aliases.current` member in their input cut, alongside the Company event and issuer master; this is their only decoded-data difference in the captured case. The selected detail decodes identically to the historical detail. All nine raw response hashes differ, so the new exact-byte capture is retained separately rather than relabeling the old corpus; no old response or receipt was overwritten.

The current-source case also runs through the actual rendered Bio page with the existing account, direct-link, correction-unavailable, recovery, mobile and language behavior checks. The result names the exact fixture owner and receipt digest, rather than using a generic label that could conceal a replay of the old fixture.

## Ownership and evidence boundaries

The separate R10/#9662/#6712 and Codex native-adoption source remains **read-only**. Its HEAD and clean tracked/untracked status were checked before and after capture. Python bytecode writes are disabled during the imports. No owner branch, worktree, inputs, source rights, publisher, admission ticket, lock, credential or deployment was modified.

The existing native `_app` test harness overrides authentication and `_read_bundle`, and replaces the final `_recheck_wmn_current` with a no-op for this pure handler/composer test. That limitation is explicit in the new capture receipt. **This is not disk-admission, current-publication, native DataOS qualification, actual entitlement or production proof.** The synthetic issuer and source document must not be presented as a real security, current news, trade recommendation or qualified forecast. Optional estimate slots remain `NOT_ESTIMABLE` and source excerpts remain null.

## Changes on the original frontend carrier

`generate_company_evidence_fixtures.py` now accepts an explicit immutable owner SHA and a separate fresh output path. A read-only preflight refuses moving refs, wrong HEAD, dirty or untracked source, output inside the owner (including symlink aliases), an existing output and the historical corpus target. The original default remains tied to its original immutable head. The CLI verifies that the loaded API module is actually from the owner root and that returned responses retain private/no-store and Authorization-Vary headers. Partial output is not silently retried or overwritten; an existing target must be reconciled.

The new `fixtures/company_evidence_r10/` holds exact bytes plus the capture receipt. Its name describes the retained source family, not independent release approval. Existing JavaScript tests verify current-owner source identity, all response hashes/headers, complete query acceptance, selected detail, the additional alias member, withheld estimates, and fail-closed revision/generation mismatch behavior.

The existing browser harness selects only the two named retained corpora using `DECISION_DESK_OWNER_FIXTURES`. Historical R2 remains the default. Before launching the browser, it validates the selected owner pin, the complete nine-file set, hashes, private headers and false admission/entitlement claims. Unapproved names and traversal values refuse before creating output. Browser evidence records `fixture_corpus`, `fixture_owner_head`, the capture-receipt digest and the unproved final disk recheck explicitly.

## Executed verification

- The nine new source/output preflight cases first failed for the missing behavior, then passed with the two existing wrappers. A later entrypoint regression exposed that the legacy default destination also needed the owner-boundary check before imports; that was repaired without changing the explicit current-owner path. The final tests also prove restoration of Python import/bytecode context after a failed owner fixture import, with no output created.
- The actual component suite now passes **93 JavaScript checks** (89 retained plus four current-owner checks). The existing host suite remains 23 checks. Wrapper counts overlap these checks.
- The final page/component/hydration selection passed **50 pytest checks**, including all eleven new capture-boundary/cleanup cases.
- The first requested-current browser run demonstrated that the old harness still replayed R2: its behavior checks passed, but the expected current-owner receipt assertion failed. After the selection/receipt repair, both current R10 and historical R2 corpora passed **15 browser behaviors, 16 viewport/theme/language layouts and eight CJK font inspections**, with zero page errors. These two runs are separate compatibility cases, not thirty distinct product features.
- An unapproved corpus name was refused before output creation. There is no new runtime selection control or public input path; the option is confined to the existing test harness.

The structured R4 verification receipt contains the exact completed broader tests and source hashes. The full repository suite is not represented as locally executed. Local Node 26.5.0 and controlled Chromium are distinct from hosted Node 20 and deployed entitled acceptance.

Reproduce the ordinary checks through the existing dedicated CI owner:

```sh
python3.12 -m pytest -q tests/test_biocatalyst_decision_desk.py
DECISION_DESK_OWNER_FIXTURES=company_evidence_r10 \
  python3.12 tests/verify_biocatalyst_decision_desk_host.py
```

The browser additionally needs the existing Playwright/Chromium and `rjsmin` dependencies. A capture from another source revision is a new explicitly pinned evidence operation with a fresh output path; do not overwrite either retained corpus merely because a branch moved.

## Remaining source-to-user acceptance

| Consumer requirement | What is now established | What remains required from the existing owner/path |
|---|---|---|
| Current list and detail interpretation | Current #9662 handlers emit bytes accepted by the actual frontend across all supported query windows. | Qualified native Company/DataOS cut and an independently admitted current publication. |
| Identity and source context | Current test wire carries the Company/issuer/alias cut and preserves source-link and estimate limits. | Actual issuer-master/vendor-alias history and rights, correctly bound to the native Company case; synthetic test identity cannot stand in for them. |
| Corrections and invalidation | Existing consumer revision/generation checks and browser unavailable/recovery behavior still pass with current wire. | Real R10 admission/pointer/lock behavior through a later accepted correction, including a failed newer build and a delayed older response. |
| Access and account safety | Existing sign-in/plans action and controlled account/logout behavior pass in both retained corpora. | A genuine authenticated and entitled deployed user session. Browser connection must originate from the connected extension context. |
| Product usefulness beyond milestone triage | The existing shell preserves space for evidence-led issuer/peer/entry/scenario interpretation without inventing estimates. | Qualified Company/NewsImpact, same-subtheme and Prophet outputs under their existing owners; no new forecast or trade authority is created here. |
| Release | Source and reproducible tests/evidence are reviewable on original #9611. | Exact-head CI, independent source/visual review, lawful native adoption and explicit release-hold clearance. |

The existing GitHub reviewer request remains pending, not approval. Session Bridge returned backend_unavailable and the original review reply was unavailable; no alternate worker was silently launched. The current Browser tool reported that the originating connected-extension context is required. Those are exact external gates, not reasons to falsify a live screenshot or source receipt. All Draft/HOLD boundaries remain.

## Scope for the existing independent review request

This is a reading guide for the existing #9611 review request, not a new worker commission, admission, lease or approval. The reviewer must bind findings to the containing exact commit and distinguish the unchanged production host from this additional test/capture code.

| Inspection | Required judgment or falsifier |
|---|---|
| R2/R3 host and user path | Read `templates/biocatalyst_decision_desk_host.js`, the component and host insertion against their tests. Try logout/account replacement with ignored abort, direct URL/Back restoration, and a mismatched detail revision/generation. Confirm no old private case can return after a boundary. |
| Access and source meaning | Confirm the access action only delegates to existing sign-in/plans; private API enforcement is not moved to the client. Source-context links must not become clinical-outcome confirmation, materiality, return forecasts or trade authority. |
| R4 capture custody | Inspect both explicit and legacy-default source/output branches, the exact-head/clean-root checks, bytecode/import cleanup and independent output location. A changed or untracked owner, an ambiguous reference, an existing current-output target or a path into the owner must refuse rather than overwrite or publish. |
| Current-wire and browser evidence | Check the nine raw hashes, current owner pin and alias-cut delta. Reproduce the existing tests. Read the selected corpus/receipt digest in each browser result; a visually identical replay of R2 is not R10-source proof. Inspect the current dark-English and light-Chinese captures without calling them live account proof. |
| Native/release limits | Explicitly state that `_app` authentication, bundle and final publication recheck are test overrides. No independent DataOS admission, live fence or actual entitled journey can be approved from these fixtures. CI green and source concurrence remain separate from release hold. |

A useful return is either concrete findings with affected paths and reproduction, or scoped source/visual concurrence with uninspected areas listed. Do not approve the native producer, release or missing production evidence merely because the consumer tests pass. Leave all existing holds in place unless the separate authorized release decision supplies the required evidence.
