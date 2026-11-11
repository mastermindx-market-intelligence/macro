# China coverage: current-main integration proof

This evidence belongs to PR #7592, original head `a1c0b55efc88c9850134196f694cc5ca14a14220`, integrated with main `3a14c93979e780e5f880643efc88b3e1f1625f74`. The native GitHub publication receipt binds the final commit. Capture manifest Git HEAD records the checkout base; `build-proof.json` records the actual candidate bytes.

## Verified result

- 85 original branch paths reconciled: 83 exact-head reuses, two composed paths. All 75 historical or receipt-related additions are preserved.
- All 401 CI catalog owners survive; 400 sibling owner blocks are unchanged. Only China's two run lines compose onto current main.
- Canonical offline China build succeeds using unchanged current-main source inputs. The scoped CSS/JS/page normalization reaches an exact fixed point.
- 147 affected renderer, country wiring and packing tests pass, with no failures, errors or skips. These overlap the earlier 312 tests; the counts are not combined.
- Eight actual page captures cover desktop/mobile, English/Chinese and dark/light. Eight separate synthetic interaction cases pass. Browser and local server processes close, and source/input/output fingerprints remain unchanged.
- Board coherence, inline JavaScript, China asset references, added-line design checks and visual evidence checks pass.

## Evidence and scope

`manifest.json`, `smells.json`, and the eight PNGs are produced through the canonical page evidence owner. `interaction-proof.json` records the declared synthetic fixtures. `build-proof.json` retains exact source/input/output identities, native process outcomes, logs and the actual helper sources.

The page is `fa3fc88f9970e94aedf6a1009645eab2a142a819`; its new CSS is `94d6c6015718cdf9e0131dcfc40a1de79d0a3dc3`. Twenty-six incidental builder outputs were restored exactly to the receiving main snapshot. No historical assets are pruned.

This is offline build and loopback browser proof. It does not claim provider refresh, production deployment, authenticated access, manual screenshot review, or native CI acceptance of the new commit. The original W3C source-family/capture-rights boundary remains recorded and was not retried.
