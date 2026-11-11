# China release: reconcile the actual publication pipeline

The previous candidate266bc included a verified raw production-builder page.
Main3aab373c9f6bbcff3c890a5035362dc7828fb3ae then ran the normal public-page
postprocessors, producing a real one-file merge conflict in site/china.html.
The checked China producer/dependency source and input directories did not change.
A merge-tree reproduced the conflict before the repair; only the page conflicted.

The resolution preserves the original raw-page fingerprint and passes its bytes
through the existing owners: lib.pages injection, CSS/opt-in-JS externalization,
and scripts.optimize_assets stamping/preload. No market value, score, threshold,
probability, input or historical ledger was edited. No orphan asset was pruned.
The new stylesheet is the original CSS content, addressed by its content hash.
This is a publication-format repair, not a replacement render or design.

Raw HTML:443300 bytes. Normalized HTML:259001 bytes. Normalized SHA-256:
9ef807c46f503da0a7f125a4ce7cfa4c5d20335cddfe49acd15ed071f41d3451.
Stylesheet:site/assets/css/fea32970.css. Asset optimization reaches a fixed point.
The smaller HTML is not a total first-load transfer claim; CSS is now separately
cacheable using the existing publishing mechanism.

Five affected normalization/China suites pass247 tests. Five warnings remain,
including shared pytest temporary-directory cleanup permission warnings; they are
not suppressed or represented as a warning-free run. Future temporary tests use
an operation-local basetemp. Inline-JavaScript and China board-coherence guards pass.
The release browser proof uses an isolated copy of the integrated site; its page
hash is checked before and after capture. Production and fresh collection remain
unproven here; this does not certify the94 risk score's predictive calibration.

Current release authority remains Sol under the Chairman's takeover and bounded
independent-review waiver. Existing GitHub CI, merge controller and VPS publisher
retain their gates; no immediate native auto-merge or new release service is used.

Browser verification of the final normalized artifact passed eight cases across
EN/ZH, dark/light and desktop/mobile. The isolated page fingerprint was unchanged
before/after capture; no console errors, failed responses or page overflow were
recorded. Desktop dark/light and mobile Chinese-light captures were visually read;
the rich dashboard and corrected Economic slowdown row remain intact.
Evidence:mockups/evidence/china-normalized-release-7592/build-proof.json.

Release progression is delegated only to the existing merge-on-green controller,
whose source requires completed CI/proof and rechecks the candidate before merge.
This is not GitHub native --auto (which can merge immediately on this repository).
A final HOLD-RELEASED receipt and ready/label readback on PR7592 establish arming;
this document by itself does not assert those effects. The existing VPS publisher
is reachable and read-only baseline matched the older public page, so actual
post-merge publication/digest/browser verification remains a separate next gate.
