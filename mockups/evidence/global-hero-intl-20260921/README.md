# International regime overview — route and responsive proof

Operation: `macro-global-hero-intl-relocation-20260921-sol-001`.
Destination carrier: `sol/global-hero-intl-20260921`; removal remains macro PR #7503.

The current Chairman instruction is relocation from `macro.html` to `intl.html`,
not substitution with `markets.html`. The existing US dashboard and International
stock boards remain outside this destination change. Routing supersession was
recorded on #7503 in comment 5760403790.

## Evidence

`manifest.json` is emitted by the existing `scripts/capture_page_evidence.py`.
It contains 24 actual Chromium captures: desktop/mobile × EN/ZH × dark/light,
with rest, real link hover, and real keyboard focus. `EVIDENCE.yml` binds the
changed presentation sources to that manifest; it does not declare acceptance.

Additional 320/390/1440 layout checks found zero page-width overflow and zero
JavaScript page errors in all 12 theme/language/viewport combinations.
The inherited International Contagion-board automatic grid minimum, 340px event
track, narrow control row, risk-label row, and reference-fold wrapping were
repaired without clipping dashboard content or changing any financial reading.

Focused route/mobile/component pack: 72 passed, 1 pre-existing conditional skip.
The mobile/projection regressions were observed failing before their fixes.
The final implementation leaves shared `theme.css` byte-identical to current main:
International derives its hero CSS from the governed Macro block and ships that
bridge inside the existing snapshot, so unrelated P0B theme receipts are untouched.

These are local implementation proofs, not deployment or public-route acceptance.
Final acceptance requires public Macro `ud=0/radar=1` and International `ud=1`,
with the US reference scope, preserved observation dates, and working navigation.
