# F02 line-gap component browser evidence

This receipt qualifies the changed shared illustration component on synthetic
inputs. It owns `templates/illus.css`, its identical `site/illus.css` copy, and
`lib/illus.py`. It does not qualify a live producer or the full F02 product.

## Source and capture

- Renderer/style source: `2b1593acd1b1d4e36014f20363ef11cfc71e8634`, original
  implementation PR #10698, branch `sol/web-f02-illus-gap-20261104-c2`.
- `fixture-manifest.json` binds the exact renderer, CSS, JS, canonical theme,
  icon stylesheet, six existing Inter font files, generator and four generated
  HTML inputs by SHA-256. Template/site illustration CSS remains byte-identical.
- Actual isolated Chromium on m2studio; browser version `151.0.7922.34`,
  macOS 26.5 arm64. The preview was bound to loopback `127.0.0.1:50475`.
- Unchanged repository capture tool `scripts/capture_page_evidence.py`, v1.4.0,
  SHA-256 `9b6e643c1c784eb81b584be4cb063092ae71c4a16fe01498130891e84cd0de42`.
- Canonical capture generated `2026-11-04T08:30:58Z`; **8/8 required cells**
  captured: 1440/390 × EN/ZH × dark/light. `manifest.json` and all eight PNGs
  retain their actual capture bytes, dimensions and SHA-256 values.
- The canonical tool cannot infer a commit from an HTTP origin; its null
  `resolved_sha_or_none` is retained. Source binding is supplied separately by
  the fixture input hashes, not a fabricated capture-tool resolution.

The specimen calls the production `ilxReveal(document)` API on load to show
all figures in their settled state, including those below the initial viewport.
This preparation does not alter production CSS or JS. `?natural=1` omits that
preparation and was used for the separate normal-scroll checks below. An initial
capture that omitted below-fold reveals and failed to load two font files was
rejected during visual QA; none of those initial PNGs is included in this receipt.

## Observed result

All eight final screenshots were visually inspected. Missing observations leave
real breaks in the line; a short value array retains the date window and an empty
tail. The last-observed value/date receipt stays outside the ink. Isolated values,
real zero and downsampled extrema stay visible. The honest-null state is explicit.
Compact 42px figures at 96/140/240px widths retain a separate status row without
covering the plot. The visible messages switch correctly between English and
Chinese. No clipping or overlap was observed in the changed component.

`smells.json` records zero console errors, zero elements wider than the viewport
and no horizontal overflow. The canonical manifest records no failed responses.
These metrics describe this synthetic specimen; they are not production telemetry.

`browser-checks.json` records **24/24 passed** real-browser cases: widths
1440/390/320 × dark/light × EN/ZH × normal/reduced motion. The checks exercise
natural scrolling rather than pre-revealing figures. They verify positive path
lengths and settled ink, reduced-motion ink without animation, loaded fonts,
non-overlapping historical/status geometry, accessible names, retained compact
date windows, actual final zero, localized visible status and no browser errors.
Verifier SHA-256:
`24d44c8526c722a82f45f9bd393613df11c5bdb14d144755d67c3c245394417e`.

| State | Exact PNG |
| --- | --- |
| Desktop / EN / dark | [534547eeed5336a4.png](evidence/534547eeed5336a4.png) |
| Desktop / EN / light | [fb24addda1e25071.png](evidence/fb24addda1e25071.png) |
| Desktop / ZH / dark | [34dbe4460f6eda85.png](evidence/34dbe4460f6eda85.png) |
| Desktop / ZH / light | [bd0a5bf266fca550.png](evidence/bd0a5bf266fca550.png) |
| Mobile / EN / dark | [00392e60c56ca68a.png](evidence/00392e60c56ca68a.png) |
| Mobile / EN / light | [c9fba4922474ed3c.png](evidence/c9fba4922474ed3c.png) |
| Mobile / ZH / dark | [ac513ea48320006d.png](evidence/ac513ea48320006d.png) |
| Mobile / ZH / light | [b72e80c7c4262048.png](evidence/b72e80c7c4262048.png) |

## Reproduce

From the source checkout (with Python Playwright and Chromium available):

```bash
python scripts/render_illus_gap_fixture.py --output-dir /tmp/f02-illus-fixture \
  --source-head 2b1593acd1b1d4e36014f20363ef11cfc71e8634
python -m http.server 50475 --bind 127.0.0.1 --directory /tmp/f02-illus-fixture
```

In another terminal, retain the actual result even if a check fails:

```bash
python scripts/capture_page_evidence.py --base-url http://127.0.0.1:50475 \
  --routes /dark-en.html --viewports desktop,mobile --themes dark,light \
  --locales en,zh --max-pages 1 --settle-ms 1800 --delay-ms 0 \
  --output-dir /tmp/f02-capture/evidence --manifest /tmp/f02-capture/manifest.json \
  --smells /tmp/f02-capture/smells.json
python scripts/verify_illus_gap_fixture.py --base-url http://127.0.0.1:50475 \
  --output /tmp/f02-capture/browser-checks.json
```

Stop the temporary server after inspection. For a different renderer revision,
pass that actual source revision and retain the newly generated input hashes.
Reruns can differ in timing metrics or platform rendering; never relabel old PNGs
as captures of changed renderer/style bytes.

## Qualification limits

- The shared API remains line-only for gap handling. A producer that deletes dates
  or observations before rendering still loses information; the crypto producer
  currently filters invalid observations. This is not live crypto-gap acceptance.
- The existing API emits English accessible names. Visible labels are bilingual;
  this receipt does not claim translated screen-reader output or full WCAG audit.
- This fixture has no authentication, save, streaming data, inspector lifecycle,
  Brain integration, touch interaction or production route. It cannot qualify
  those F01/F02/domain journeys, 400% zoom or deployment behavior.
- Existing Paper G15 remains `EFFECT_UNKNOWN`; no dependent Paper edits, full
  32-board acceptance, formal release approval, merge or deployment follow from
  this component evidence. PR #10698 and design PR #10630 remain Draft/HOLD.
