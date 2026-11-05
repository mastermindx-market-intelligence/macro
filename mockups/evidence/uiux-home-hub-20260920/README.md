# Home hub release evidence — PR #7346

## Bounded capability
The signed-in home hub gives a truthful snapshot cue rather than a ticking viewer-local clock. It uses plain feature labels and an accessible Markets / Explore mobile switch. Technical scores remain on their detail pages. This continuation also closes two real source/artifact Chinese CTA mismatches and removes one-day market-state assumptions from the artifact regression.

The source carrier remains `sol/uiux-hub-sweep-20260918`; its reviewed incoming head was `9aecd6f2edabce9cde900ede73420eff3ad59c07`. No source branch reset/rebase or replacement PR was used. No chart values, regime formulas, data payload, destinations, authentication or membership logic were changed.

## Dark treatment
Retain the existing dark command-centre globe, deep panels and restrained highlight. The snapshot cue is a static information-colored point, not the previous pulsing green live claim. Card hierarchy, geometry and focus behavior remain with the existing hub.

## Light treatment
Retain the existing light research canvas and white/glass surfaces. The snapshot cue uses the existing semantic information color and remains legible on the light background. This is not a new palette or a global light-mode patch. Mobile cards deliberately keep short titles; longer destination copy remains on desktop. The EN/ZH captions match the producer.

## Evidence and limits
The canonical page-capture tool produced all eight rest states: dark/light × EN/ZH × desktop 1440/mobile 390. `verify_interactions.py` separately used real keyboard Enter/Space to switch mobile sections, checked `aria-pressed`, the visible snapshot, no animated clock, card-local EN/ZH CTA parity, zero document overflow and zero page exceptions. It never manufactured data or member access. Normal remote/API/network limitations from a locally served snapshot remain disclosed in the canonical manifest.

Generated page SHA-256: `5ba5dc6af3a0f15209d40cf9b86f644ce07de92d9508e31bb077d5c8f1bdcede`. CSS: `c5fc2df4`, filename hash verified. Targeted tests: 64 passed. The new card-scoped parity assertion distinguishes the inherited `中国查看行业轮动` artifact from the actual producer; raw numerical states are tested through controlled producer inputs, not frozen into a daily snapshot assertion.

## Release
Current Chairman instruction is VPS-only, not Vercel. Use concluded exact-head repository checks, current-base integration proof, expected-head merge, the existing locked `/usr/local/bin/macro-update`, and a public-browser run of this verifier. Local evidence is BUILT_NOT_PROVEN until that public release check passes. Do not mint a second deployment or merge queue.

The preceding Government Revenue batch #7450 is already live via merge `e3329833b29be7d2d8b9b0889acf5aadd8bcc686`; its public eight-cell interaction proof and exact served-byte match are recorded on that PR. Do not repeat that source repair.

## Reproduce
```sh
python3 mockups/evidence/uiux-home-hub-20260920/verify_interactions.py
python3 mockups/evidence/uiux-home-hub-20260920/verify_interactions.py --base-url https://www.mastermind-x.com --output-dir /tmp/home-hub-live-proof
```
