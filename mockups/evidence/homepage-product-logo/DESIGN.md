# Public header product logo

Replace the placeholder text-M tile with the existing favicon.svg artwork, which is the same crafted product mark used by start.html. Keep the wordmark as real text.

LIGHT TREATMENT: existing cool light header, dark navy (#1c2430) wordmark, crisp blue-violet SVG, no external glow.

DARK TREATMENT: public navigation intentionally retains its established light-only art direction even when data-theme=dark is selected. Keep dark navy text on that actual light background. The dark product navigation and its light wordmark are unchanged.

The artwork and header geometry stay consistent. Text color follows the actual public header material, rather than borrowing white lettering from the dark product lockup. Existing mobile icon-only layout is preserved. Retain the legacy text-M CSS for About and other unchanged consumers of landing.css.

Baseline: product artwork in templates/favicon.svg and templates/_navlinks.html.j2; existing homepage and shared public headers. If the image cannot load, the home link keeps its accessible name and desktop wordmark.

Evidence: manifest.json captures dark/light x EN/ZH x desktop 1440/mobile 390. The four header crops and header-checks.json additionally verify both public header families load the SVG at 27px and keep rgb(28, 36, 48) text in both theme settings. The local static server cannot serve the unrelated billing API; that recorded 404 is outside this logo change. Whole-page mobile overflow reported by the general capture is outside the header change and is not presented as a whole-page layout pass.
