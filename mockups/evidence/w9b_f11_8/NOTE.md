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
  sha256 `e19ac70224a3b716800ed05592e258d7611407980f56ff43781c3fff084ff913`
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

## Commit binding (self-contained, not note-only)

Both manifest pages carry `page_tree_sha` = `27e5886faf9208efd4e54aac48ec256318cfdd7e`,
the git BLOB content address of `templates/mm_brain.js` (`site/mm_brain.js` is
byte-identical) at the head these crops were captured from — i.e. the content
address of the exact bytes the harness served as `mm_brain.js`. A blob sha stays
reachable as long as any commit references it, so the binding survives the
squash-merge that would orphan a commit sha; `scripts/check_ui_visual_evidence.py`
validates its shape (`_validate_optional_page_tree_sha`). The harness's own
`index.html` is not committed — it is reproduced in full above — so the asset
blob is the only committable content address these cells can carry.

## Second capture (review round 2)

The first capture predates two head-side changes: the row-collapse rule
(`.mmb-rrow:has(> .mmb-rpill.mmb-off){display:none}`, which only ever applies to
the entitlement-hidden state) and the provenance comments that now name PR 7100
where they used to imply the gateway already stamps the sentence. The capture
above re-runs the same command against the new asset bytes, so the crops depict
this head. 15 of the 16 cells came back byte-identical to the first capture; the
one that did not (armed / mobile / zh / light) re-rendered at the same 390x844
with identical overflow metrics — the only metric that moved anywhere is
`payload_bytes_total`, +897 bytes of bundle — so the new PNG is the same layout
at antialiasing resolution. Superseded PNGs were deleted from this directory as
each capture replaced them, so the folder equals the manifest. The entitlement-hidden state shows no cell by design (the capture
stubs Pro so the control is visible); the rule that keeps that state from
leaving a 2px band is pinned instead by
`tests/test_mm_brain_asset.py::test_entitlement_hidden_toggle_takes_its_row_with_it`.

## Reproducing

    python3 scripts/capture_page_evidence.py \
      --site-dir /private/tmp/f118-harness \   # throwaway; the files above are its whole content\
      --registry <any absent path> \
      --routes "/index.html,/index.html?armed=1" \
      --viewports desktop,mobile --locales en,zh --themes dark,light \
      --output-dir mockups/evidence/w9b_f11_8 \
      --manifest mockups/evidence/w9b_f11_8/manifest.json \
      --smells mockups/evidence/w9b_f11_8/smells.json \
      --settle-ms 1500 --repo macro
