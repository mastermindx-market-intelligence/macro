# mi-v1-followups-20261007 — measurement.html evidence note

## DARK TREATMENT

No new material treatment. Dark command-center tokens (`--panel`, `--line`, `--text`) on the Calibration Lab page are unchanged. The IMCE prospective footnote and preserved-verdict receipts keep their existing card/footnote hierarchy; only long path tokens wrap inside `.eg-footnote`.

## LIGHT TREATMENT

No new material treatment. Light research-workspace canvas and hairline discipline are unchanged. Wrapping uses the same inherited `overflow-wrap: anywhere` rule as dark.

## Mechanisms that differ by theme

None introduced by this change (wrap rule is theme-agnostic).

## DESIGN_DOCTRINE rule relied on

From `docs/DESIGN_DOCTRINE.md` §3 (Self-labeling chip strip): **"full display names (wrap, never truncate)"** — long file paths in footnotes must wrap rather than forcing horizontal page scroll at narrow viewports.

## Degraded states (both themes)

Invalid `owner_ref` (empty, prose, or non-colon-form) fails closed in `engine/verdict_preservation.py`; `build_verdict_preservation` returns `{"available": False}` and the entire `#vp-section` is omitted with no placeholder.

## Overflow probe (390×844 and 1440×900, local render after S4)

```
theme=dark lang=en viewport=390x844 scrollWidth=390 vw=390 unclipped_offenders=0 scrollX=0
theme=dark lang=en viewport=1440x900 scrollWidth=1440 vw=1440 unclipped_offenders=0 scrollX=0
theme=dark lang=zh viewport=390x844 scrollWidth=390 vw=390 unclipped_offenders=0 scrollX=0
theme=dark lang=zh viewport=1440x900 scrollWidth=1440 vw=1440 unclipped_offenders=0 scrollX=0
theme=light lang=en viewport=390x844 scrollWidth=390 vw=390 unclipped_offenders=0 scrollX=0
theme=light lang=en viewport=1440x900 scrollWidth=1440 vw=1440 unclipped_offenders=0 scrollX=0
theme=light lang=zh viewport=390x844 scrollWidth=390 vw=390 unclipped_offenders=0 scrollX=0
theme=light lang=zh viewport=1440x900 scrollWidth=1440 vw=1440 unclipped_offenders=0 scrollX=0
```

## Crop paths

Manifest PNGs under `mockups/evidence/mi-v1-followups-20261007/` (from `capture_page_evidence.py`).

Element crops under `mockups/evidence/mi-v1-followups-20261007/crops/`:

- `imce-dark-en-desktop.png`, `imce-dark-en-mobile.png`, `imce-dark-zh-desktop.png`, `imce-dark-zh-mobile.png`
- `imce-light-en-desktop.png`, `imce-light-en-mobile.png`, `imce-light-zh-desktop.png`, `imce-light-zh-mobile.png`
- `gate-dark-en-mobile.png`, `gate-dark-zh-mobile.png`, `gate-light-en-mobile.png`, `gate-light-zh-mobile.png`
- `vp-receipt-dark-en-desktop.png`, `vp-receipt-light-en-desktop.png`
- `viewport-dark-en-mobile.png`, `viewport-dark-zh-mobile.png`, `viewport-light-en-mobile.png`, `viewport-light-zh-mobile.png`

Mobile IMCE crops: the `data/cycle_pattern/imce_prospective_observation_v1.jsonl` footnote `<code>` wraps onto multiple lines inside the card at 390px (no horizontal bleed past the viewport).
