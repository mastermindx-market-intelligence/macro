# W9B F11-8 — Research toggle reads the ceiling sentence: capture note

The changed surface is one control inside the shared Brain widget
(`templates/mm_brain.js`, paired copy `site/mm_brain.js`). It cannot be captured
on a production page for two structural reasons, both named here rather than
papered over:

1. **The control is entitlement-gated.** `proEligible` comes from
   `GET /api/brain/me` (`quotas.pro.limit !== 0`), and `capture_page_evidence.py`
   is anonymous-only by contract — it never enters, synthesizes or reads a
   credential. Anonymous, the toggle carries `mmb-off` (display:none), so no
   production page shows it at all.
2. **The control lives inside a panel that opens on interaction.** The eight
   rest cells of a production page would show the launcher orb, not the row.

So the capture runs the house tool (`scripts/capture_page_evidence.py`, schema
`mastermind.p0_evidence.v2`, tool sha recorded in the manifest) against a
minimal harness that serves the REAL asset bytes from this head and implements
only the host half of the widget's documented contract.

## What the harness is

Served from a throwaway directory (not committed; reproduced below in full) by
the tool's own `--site-dir` static server:

- `mm_brain.js` — byte-for-byte copy of `templates/mm_brain.js` at this head,
  sha256 `274107f35d43700be9d8f66d810e3c47390d770e2b47cfa3302763f11aa4f503`
  (first 8 hex = the `MM_BRAIN_VER` baked into `site/theme.js` by this PR).
- `api/brain/me` — a static stub: `{"tier":"pro","quotas":{"fast":{"lane":"fast",
  "limit":40,"remaining":31,"period":"day"},"pro":{"lane":"pro","limit":20,
  "remaining":14,"period":"day"}}}`. This is the ONE synthetic input: a Pro
  entitlement, because the capture contract forbids a real one. It shows the
  control's copy and material, not a real session.
- `api/brain/threads` — `{"threads":[]}`.
- `index.html` — empty page (no scenery that could be mistaken for product
  copy) that (a) honours the tool's pre-load `localStorage` seed so the first
  paint is already in the requested theme/locale, and (b) provides the minimal
  `window.setTheme` / `window.setLang` the production host (`templates/theme.js`)
  owns, firing the `themechange` / `langchange` events the widget listens for,
  so the tool's own state application reaches the widget down the same path a
  user's click does.
- Route `?armed=1` arms the mode by clicking `.mmb-rpill` through the widget's
  own delegated handler — a real interaction, not a forced class.

## What the cells show

`/index.html` — the row at rest, in the composer, between the textarea and the
depth control. `/index.html?armed=1` — the same row armed.

- **DARK** (command center): rest is a faint ink field with no edge; armed is a
  violet field under a violet hairline ring with the widget's restrained glow,
  near-white type, and the Pro stop lighting blue below — the "which bucket is
  being spent" half of the old pairing, unchanged.
- **LIGHT** (research workspace): rest is a near-opaque white row on the cool
  box, edged by the hairline this theme draws heavier; armed keeps the white
  material under a violet hairline plus a soft lift — shadow, not glow. No
  violet field: over white it reads as a bruise.
- **EN / ZH**: the sentence is the frozen F11 contract copy verbatim; the ZH
  twin is real Chinese with CJK punctuation and wraps to three lines at 390.
- **1440 / 390**: the sentence wraps at both; nothing collapses to a mark. The
  old compact pill's disclosure was a hover tip this sheet hides below 560px,
  which is exactly why the 390 cells matter.

## Reproducing

    python3 scripts/capture_page_evidence.py \
      --site-dir <harness dir above> \
      --registry <any absent path> \
      --routes "/index.html,/index.html?armed=1" \
      --viewports desktop,mobile --locales en,zh --themes dark,light \
      --output-dir mockups/evidence/w9b_f11_8 \
      --manifest mockups/evidence/w9b_f11_8/manifest.json \
      --smells mockups/evidence/w9b_f11_8/smells.json \
      --settle-ms 1500 --repo macro
