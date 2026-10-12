# Contribution for the existing Brain owner

Owner carrier: Macro PR #8526, branch `claude/iw2-brain-mobile-targets-20261006`, exact tested head `53a1fc4cc47b4b9240fad828d0ef2161346aaacc`. This directory holds a reviewed contribution; it reserves no product source and does not mutate that branch.

`owner-8526.patch` fixes the paired widget freshness vocabulary and updates the existing theme loader digest. The incumbent mobile target and delayed-focus changes are preserved. Only canonical `fresh` displays current; absent, malformed and inherited object keys display unknown.

The parent ran 20 asset/source cases with zero skips, both widget syntax checks, and five complete-widget browser cases against this exact head: original counterexample, repaired desktop EN/ZH, tablet EN, mobile EN. The browser used a declared synthetic Brain SSE/account fixture, not live customer/model/backend calls. The fixture stopped its own server. `review.json` pins exact hashes; full synthetic output and screenshots remain at the evidence path in the review snapshot.

Before integration, the incumbent owner must reconcile the current head and apply `git apply --check` to the patch in its existing authorized carrier. If the head changed, rebase the contribution and rerun affected evidence rather than treating these hashes as current. The supplied source regression belongs at `tests/test_mm_brain_inspector_freshness_source.py`; the supplied fixture belongs at `tests/harness/inspector_freshness_fixture.cjs`. It expects the paired candidate widget at the repository root, and an exact53a preimage at `artifacts/owner-preimage/mm_brain.js`. Its Playwright/Chromium bindings are explicit Ubuntu2 paths, so another host requires a grounded equivalent binding.

Observed command: `/home/ubuntu2/.cache/mm-7870-venv/bin/pytest -q tests/test_mm_brain_asset.py tests/test_mm_brain_inspector_freshness_source.py` followed by `node --check site/mm_brain.js`, `node --check templates/mm_brain.js`, and `node tests/harness/inspector_freshness_fixture.cjs`. Results: 20 passed, 5 browser cases passed, 0 skipped.

Owner incorporation, owning CI, production integration and the broader original A08 GEX/truncation contracts remain outstanding. No exact active chat binding for PR8526 was recovered; this contribution is available through the canonical records PR, not a claim that an owner was notified or accepted it.
