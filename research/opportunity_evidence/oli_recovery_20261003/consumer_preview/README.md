# C0/P0 synthetic consumer preview — executable, not production-admitted

This is the first implementation unit of OLI recovery, under Macro issue 8328 and the existing Alpha/TOI/Prophet/Market OS owners. It translates the supplied handoff's consumer boundaries into executable hostile cases and a functional HTML reference. It does not replace the existing OEV composer, Security State schema, producer, gateway, renderer, Plan owner, or scientific registry.

## What works in this candidate

`preview_contract.py` validates only explicitly synthetic fixture inputs and returns an ephemeral view. `render_preview.py` produces the HTML reference and the corresponding machine-view examples from exactly those views. The reference provides scenario selection, public/private-fixture selection, dark/light appearance, an evidence/clock/correction drawer and a machine-payload drawer.

Ten scenarios exercise confirmed-but-no-fresh-entry, existing-position/no-new-entry, expired permission with a fresh quote, mixed generations, missing optional context, failed transport, future knowledge, explicit correction, rights blocking, and native EXTENDED without inferring a sale.

The boundary keeps these facts distinct:

- Phase, new-entry verdict and private Plan/position are separate. A saved Plan does not establish a fill; an existing position does not change the entry verdict.
- Entry dependencies bind full reference tuples, not ticker/date. Stale or mismatched source/quote/geometry generations withhold the preview verdict. No replacement permission is inferred.
- Source observation, knowledge, validity, geometry basis and opportunity expiry are separate. A fresh quote cannot refresh permission or reprice a forecast.
- Optional absence is not zero or a neutral vote. Source dependence groups are disclosed, not added into a score.
- Public composition does not inspect or serialize its private argument. The private exercise checks the synthetic viewer and subject identity independently.
- Forecasts stay null. All authority flags stay false. Native-shaped schemas and non-synthetic inputs are explicitly refused.

## Deliberate limits

The `fixture.*` schemas, `fixture:` IDs and role labels are **test-wrapper vocabulary**, not newly registered native contracts or proven production adapters. There is no new canonical coarse lifecycle. The preview preserves supplied phase text; it does not translate EXTENDED into SELL or assign a global rank.

No real market data, scientific outcome, private account, position, entry permission, repository-global source-writer lease, production source, or deployed service was accessed by this implementation. No source admission, native-owner signoff, API/gateway, entitlement, save, alert or production behavior is claimed. The preview's private examples are fabricated and bundled only because every input is synthetic; production must never embed private audience variants in a public HTML payload.

The known #7963 Prophet-outlook integration remains the incumbent product implementation. #7107 and #7094 retain their source-custody/data/acceptance gates. This prototype neither changes their paths nor retries the earlier refused OEV source-context/test command or the later refused composite current-source query.

## Reproduce the permitted local unit checks

From this directory:

```sh
python3 -m unittest -v test_preview_contract
python3 render_preview.py
```

The implementation was tested in the conversation's isolated Linux container. Current result: **55 tests passed**. The initial 42-test run caught one actual bug: geometry with a basis time later than its stated observation was accepted. The boundary was repaired; the discriminator now passes. A further seven tests cover input bounds, future-payload noninspection, immutable output authority and script-data escaping/reproducibility. The generated JavaScript parsed successfully with `node --check`.

These are new preview tests, not a rerun or repaired result for the historical OEV suite. They do not establish native schema/fixture equivalence, scientific replay prefix invariance, independent review or current-base repository integration.

The browser script attempted a `file://` navigation in container Chromium. The browser returned **ERR_BLOCKED_BY_ADMINISTRATOR before rendering**. No matrix cases or screenshots completed; no visual/browser acceptance is claimed. This session did not weaken that policy or reroute the denied browser test. `verification_receipt.json` preserves the boundary. A permitted browser lane must still execute the interaction/responsive matrix; source inspection and JavaScript parsing are not substitutes.

The reference can be inspected as source in `preview.html`. The generator and template are the editable artifacts; do not hand-edit the generated view examples.

## Existing-owner decisions still required before native wiring

1. **Version and placement:** adopt the exact relation/profile through existing Alpha and Market OS contracts. Security State v1's closed/null-only fields cannot be silently widened. The preview adds no field to that production payload.
2. **Native entry binding:** bind the accepted OEV entry-role mapping to the exact native B4 schema/receipt and dependency clocks. Plan/admission/management status is not entry actionability.
3. **Identity:** use the exact source owner identity/schema/generation and the existing B1 allowlist. The prototype creates no `pe:` ID, admission origin or ticker/date surrogate.
4. **Denominator and landmark:** explicitly name the existing nomination/suppression and Evaluation/QLedger owners for full-resolution first-forming retention and prediction-to-landmark relations. No second ledger is introduced by this exercise.
5. **Real-path acceptance:** reconcile #7963 custody and release debt, then prove the admitted producer → existing gateway/access → machine/UI journey with real source receipts. Authenticated private composition, EN/ZH, no-JavaScript degradation, keyboard/responsive behavior and deployment identity remain acceptance work.

Scientific data admission, preregistration, validation, prospective evidence and consumer promotion are separate later gates. The original report archive is input, not approval to bypass those gates.

## Strategy and causal-reference hardening

The second test-first pass exposed a missing full strategy relation in the synthetic exercise. Strategy-scoped phase, entry, geometry, next-condition and private Plan references now bind the exact strategy owner, ID and version in addition to security/identity epoch/schema/native ID/generation. A security-scoped quote deliberately does not gain fictitious strategy ownership.

Matching generation alone also did not prove that the entry could have read its dependencies. The consumer now withholds a verdict as `DEPENDENCY_NOT_KNOWN_AT_ENTRY` when any bound phase, quote or geometry source became known after the entry's own knowledge clock. This does not mint a replacement verdict. Six added test methods cover these relations; the pre-fix run had seven assertion failures across five methods (including three dependency subcases) and one passing method. The complete repaired suite passes 55/55.

This is author testing, not independent acceptance. The first 49-test receipt remains historical. No native production schema was broadened, no protected market outcome was read, and the previously denied browser navigation was not retried. Hosted test collection and real-source/gateway/browser acceptance remain separate obligations.
