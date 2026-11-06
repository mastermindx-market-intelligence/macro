# docs/pr-crops/9271 — Sector Central measured-read panel evidence (LR-FIX-B2)

SYNTHETIC LOCAL — not production. Every artifact in this directory was produced by rendering the template at the pinned head against a LOCAL Python http.server, with the two data files (sector_central_data.js, sector_cycles_data.js) replaced per the VARIANTS table. No request ever left 127.0.0.1. The browser context blocked every non-127.0.0.1 URL.

## Lane / head
- Lane: `LR-FIX-B2-1` (LEADERSHIP-ROTATION · ORCH-FIX T23 · parent 0D30D · carrier fabric lane)
- Pinned commit (the commit whose `templates/sector_central.html.j2` was rendered): `b7694dc2b764edf60785816404efc6cf6bf03b31`
- `template_blob`: `e7d4f76a56c8fc8dbb703c62e0d8cc3084bf1fd9`
- `site_assets_from` (origin/main, read-only via `git show`): `4d9d8b731d201be466264266c28e71d41444ad4a`
- Evidence class: `synthetic (LOCAL render + LOCAL injected data)`
- The crop commit itself adds only `docs/pr-crops/9271/**`; the diff against the pinned head is verified below.

## R4 — ZH fix (LR-FIX-B2)
The prior receipt's `matrix-390-zh-*` crops were byte-identical to their EN twins because `setPrefs` in `smoke.cjs` and `cap.cjs` called Playwright's `addInitScript(script, T, L)` with TWO positional args; Playwright's signature is `addInitScript(script, arg?)`, so the script's `L` parameter was `undefined`, `localStorage.setItem('lang', undefined)` coerced to the STRING `'undefined'`, the boot inline script stamped `data-lang='undefined'` on `<html>`, and the panel's `isZh()` returned false. The fix is a one-liner in both files: pass a single object and destructure inside. Acceptance, recorded per ZH crop in `RECEIPT.json#pngs[].lang_facts`:

| File | data-lang="zh" | CJK present in `#si-measured` | sha256 differs from EN twin |
|---|---|---|---|
| `matrix-1440-zh-dark.png` | True | True | True |
| `matrix-1440-zh-light.png` | True | True | True |
| `matrix-390-zh-dark.png` | True | True | True |
| `matrix-390-zh-light.png` | True | True | True |

## What each crop shows

### A. Matrix — `matrix-<vp>-<L>-<T>.png` (8 crops)
Two art directions (dark / light) at 1440 and 390, EN and ZH. The same variant (`ok`) and the same `?g=XLE#map` deep link. The dark/light pair differ in `background-color` of `#si-measured .mr-detail` (measured live: dark `rgb(27,31,40)`, light `rgb(255,255,255)`); the box-shadow differs too.

### B. States — `state-<name>-<T>.png`
Desktop 1440. Each row is one of: the 15 EN states from the prior receipt (each × dark/light = 30), the 4 B2 NEW ZH state crops (absent-zh, invalid-zh, each × dark/light = 4), and the 5 B2 NEW synthetic state crops (groupsnull × 2, estimate × 2, estimate-zh × 1, basisunknown × 1). Total 30 + 4 + 6 = 40.

| State name | Variant | Notes |
|---|---|---|
| `ok-hnotpub` | `ok` | Partial chip; recon view shows "Reconstructed history is not published yet." (expected — main has not published rs_history) |
| `hrecon-synth` | `hrecon (SYNTH)` | Synthesised `rs_history` per CYR formula; recon chart draws |
| `full` | `full` | `status=available`; partial chip gone |
| `partialstale` | `stale` | `as_of > H`; stale chip rendered |
| `absent` | `absent` | `measured_read` key removed; `mx-empty` |
| `outage` | `outage` | `status=unavailable, reason=source_missing`; `mx-error` |
| `invalid` | `invalid` | schema=v0 (mismatched); `mr-invalid` |
| `nodata` | `nodata` | `sector_central_data.js` is a comment; `mx-error` "Data for this page did not load." |
| `hloading` | `hloading` | `sector_cycles_data.js` is a comment; skeleton in #mr-hist (captured ≤5s) |
| `hfailed` | `hfailed` | `sector_cycles_data.js` is 404; `mx-error` in #mr-hist; ranked list still usable (A42) |
| `genmis-synth` | `genmis (SYNTH)` | history dates stale; CYR used; `mrGen` shown (SYNTH) |
| `obsnone` | `ok, g=XLE, obs` | No recorded event for XLE; `mx-empty` "No recorded events for this sector." |
| `obsevent` | `ok, g=XLK, obs` | XLK has 1 recorded event; facts dl + "See it in What's moving →" link |
| `obsincompat` | `obsincompat, g=XLK, obs` | `status=incompatible_generation`; `mrGen` |
| `unmeasured` | `ok, g=XLRE` | XLRE row in `mr-row-na`; "not measured — missing_input" |
| `absent-zh` | `absent, L=zh` | Same as `absent` rendered in Chinese; verifies the EN/ZH bilingual coverage of the empty-state copy. |
| `invalid-zh` | `invalid, L=zh` | Same as `invalid` rendered in Chinese; verifies the ZH translation of "This read could not be checked, so it is not shown." |
| `groupsnull` | `groupsnull (SYNTH)` | Hostile `measured_read.groups=[null]` triggers render()'s groupsOk guard; panel falls into the mr-invalid state, same surface as the schema=v0 variant. |
| `estimate` | `estimate (SYNTH)` | `measured_read.research_estimate={status:estimate, probability:0.62, horizon_sessions:21}` renders the admitted-estimate line in #si-measured; the `Forecast: none —` default is suppressed. |
| `estimate-zh` | `estimate (SYNTH), L=zh` | Same as `estimate` rendered in Chinese. |
| `basisunknown` | `basisunknown (SYNTH)` | `measured_read.generation.price_basis="unknown"` makes basis() return "basis not stated" / "未注明价格口径" in the sub-line. |

### C. Extras
- `zh-detail-<T>.png` — ok, ZH, g=XLK, 1440, dark+light. Chinese labels render in detail.
- `m390-selected-<T>.png` — ok, 390 mobile, tap `.mr-row[data-g="XLF"]`; full-viewport screenshot, dark+light.

## `-synth` meaning
Crops whose variant is marked `(SYNTH)` in `RECEIPT.json#variants` are synthetic — they use hand-built payloads per the B2 spec: `hrecon-synth` and `genmis-synth` use CYR (a deterministic 120-point `rs_history` series generated by `build_variants.py`); `groupsnull` injects a hostile `[null]` groups array; `estimate` injects a valid `research_estimate`; `basisunknown` injects `price_basis="unknown"`. Every other crop uses the committed CY0 and SC0 with targeted mutations.

## A44 distinctness
See `RECEIPT.json#a44`. Every state has a distinct container class or distinct copy. Verdict reported in `a44.verdict`.

## §4 + A44 assertions
See `RECEIPT.json#section4`. All 9 entries (4a..4g, setThemeLang) PASS at this change.

## How to reproduce
1. `cd ~/lanes/wt/lr-fix-b2-1 && git sparse-checkout set --no-cone '/templates/' '/engine/i18n.py' '/engine/__init__.py' '/tests/fixtures/leadership_rotation/' '/docs/pr-crops/README*' && git checkout`
2. Render the template at `b7694dc2b764edf60785816404efc6cf6bf03b31` with the kwargs in `scripts/build_sector_central.py:env.get_template(...).render(...)`. The lane's renderer uses an empty `pgate/bottoming/theme_context/factor_season/flow/basket_member_syms/action_board/source_as_of/baskets_sha256/action_board_sha256/accumulation/accumulation_universe_n/theme_tape/generated_utc` and `flows_html=None` (the panel renders without those organs; the IIFE is the part under test).
3. Materialise the 29 base assets from `origin/main:site/<path>` (read-only via `git show`; never write into the worktree's `site/`).
4. `python3 build_variants.py` writes `VARIANTS.json` and 15 variant dirs under `~/lanes/scratch/lr-fix-b2/sites/`.
5. `python3 -m http.server 8767 --bind 127.0.0.1 --directory ~/lanes/scratch/lr-fix-b2/sites &` — record the PID; kill it by PID at the end.
6. `node smoke.cjs` produces 52 PNGs + `trace.json` + `lang_facts.json` into this directory.
7. `node assertions.cjs` writes `trace_assertions.json` with the §4 + A44 results.
8. `python3 build_receipt.py` writes `RECEIPT.json` and this README.

## Crop index
- `matrix-1440-en-dark.png` — variant `ok`, viewport 1440x900, locale en, theme dark, 245034 bytes, data_lang='en', cjk=False
- `matrix-1440-en-light.png` — variant `ok`, viewport 1440x900, locale en, theme light, 256451 bytes, data_lang='en', cjk=False
- `matrix-1440-zh-dark.png` — variant `ok`, viewport 1440x900, locale zh, theme dark, 233740 bytes, data_lang='zh', cjk=True, differs_from_en_twin=True
- `matrix-1440-zh-light.png` — variant `ok`, viewport 1440x900, locale zh, theme light, 246260 bytes, data_lang='zh', cjk=True, differs_from_en_twin=True
- `matrix-390-en-dark.png` — variant `ok`, viewport 390x844, locale en, theme dark, 117983 bytes, data_lang='en', cjk=False
- `matrix-390-en-light.png` — variant `ok`, viewport 390x844, locale en, theme light, 118521 bytes, data_lang='en', cjk=False
- `matrix-390-zh-dark.png` — variant `ok`, viewport 390x844, locale zh, theme dark, 107194 bytes, data_lang='zh', cjk=True, differs_from_en_twin=True
- `matrix-390-zh-light.png` — variant `ok`, viewport 390x844, locale zh, theme light, 109034 bytes, data_lang='zh', cjk=True, differs_from_en_twin=True
- `state-ok-hnotpub-dark.png` — variant `ok`, viewport 1440x900, locale en, theme dark, 245001 bytes, data_lang='en', cjk=False
- `state-ok-hnotpub-light.png` — variant `ok`, viewport 1440x900, locale en, theme light, 256431 bytes, data_lang='en', cjk=False
- `state-hrecon-synth-dark.png` — variant `hrecon` (SYNTH), viewport 1440x900, locale en, theme dark, 241910 bytes, data_lang='en', cjk=False
- `state-hrecon-synth-light.png` — variant `hrecon` (SYNTH), viewport 1440x900, locale en, theme light, 253329 bytes, data_lang='en', cjk=False
- `state-full-dark.png` — variant `full`, viewport 1440x900, locale en, theme dark, 239693 bytes, data_lang='en', cjk=False
- `state-full-light.png` — variant `full`, viewport 1440x900, locale en, theme light, 250313 bytes, data_lang='en', cjk=False
- `state-partialstale-dark.png` — variant `stale`, viewport 1440x900, locale en, theme dark, 249231 bytes, data_lang='en', cjk=False
- `state-partialstale-light.png` — variant `stale`, viewport 1440x900, locale en, theme light, 261035 bytes, data_lang='en', cjk=False
- `state-absent-dark.png` — variant `absent`, viewport 1440x900, locale en, theme dark, 34620 bytes, data_lang='en', cjk=False
- `state-absent-light.png` — variant `absent`, viewport 1440x900, locale en, theme light, 35564 bytes, data_lang='en', cjk=False
- `state-outage-dark.png` — variant `outage`, viewport 1440x900, locale en, theme dark, 26901 bytes, data_lang='en', cjk=False
- `state-outage-light.png` — variant `outage`, viewport 1440x900, locale en, theme light, 27746 bytes, data_lang='en', cjk=False
- `state-invalid-dark.png` — variant `invalid`, viewport 1440x900, locale en, theme dark, 28443 bytes, data_lang='en', cjk=False
- `state-invalid-light.png` — variant `invalid`, viewport 1440x900, locale en, theme light, 29534 bytes, data_lang='en', cjk=False
- `state-nodata-dark.png` — variant `nodata`, viewport 1440x900, locale en, theme dark, 25802 bytes, data_lang='en', cjk=False
- `state-nodata-light.png` — variant `nodata`, viewport 1440x900, locale en, theme light, 26632 bytes, data_lang='en', cjk=False
- `state-hloading-dark.png` — variant `hloading`, viewport 1440x900, locale en, theme dark, 260601 bytes, data_lang='en', cjk=False
- `state-hloading-light.png` — variant `hloading`, viewport 1440x900, locale en, theme light, 273079 bytes, data_lang='en', cjk=False
- `state-hfailed-dark.png` — variant `hfailed`, viewport 1440x900, locale en, theme dark, 237915 bytes, data_lang='en', cjk=False
- `state-hfailed-light.png` — variant `hfailed`, viewport 1440x900, locale en, theme light, 249716 bytes, data_lang='en', cjk=False
- `state-genmis-synth-dark.png` — variant `genmis` (SYNTH), viewport 1440x900, locale en, theme dark, 244574 bytes, data_lang='en', cjk=False
- `state-genmis-synth-light.png` — variant `genmis` (SYNTH), viewport 1440x900, locale en, theme light, 256224 bytes, data_lang='en', cjk=False
- `state-obsnone-dark.png` — variant `ok`, viewport 1440x900, locale en, theme dark, 234713 bytes, data_lang='en', cjk=False
- `state-obsnone-light.png` — variant `ok`, viewport 1440x900, locale en, theme light, 245750 bytes, data_lang='en', cjk=False
- `state-obsevent-dark.png` — variant `ok`, viewport 1440x900, locale en, theme dark, 245676 bytes, data_lang='en', cjk=False
- `state-obsevent-light.png` — variant `ok`, viewport 1440x900, locale en, theme light, 256133 bytes, data_lang='en', cjk=False
- `state-obsincompat-dark.png` — variant `obsincompat`, viewport 1440x900, locale en, theme dark, 241681 bytes, data_lang='en', cjk=False
- `state-obsincompat-light.png` — variant `obsincompat`, viewport 1440x900, locale en, theme light, 252823 bytes, data_lang='en', cjk=False
- `state-unmeasured-dark.png` — variant `ok`, viewport 1440x900, locale en, theme dark, 243882 bytes, data_lang='en', cjk=False
- `state-unmeasured-light.png` — variant `ok`, viewport 1440x900, locale en, theme light, 255680 bytes, data_lang='en', cjk=False
- `state-absent-zh-dark.png` — variant `absent`, viewport 1440x900, locale zh, theme dark, 32777 bytes, data_lang='zh', cjk=True, differs_from_en_twin=True
- `state-absent-zh-light.png` — variant `absent`, viewport 1440x900, locale zh, theme light, 34109 bytes, data_lang='zh', cjk=True, differs_from_en_twin=True
- `state-invalid-zh-dark.png` — variant `invalid`, viewport 1440x900, locale zh, theme dark, 26584 bytes, data_lang='zh', cjk=True, differs_from_en_twin=True
- `state-invalid-zh-light.png` — variant `invalid`, viewport 1440x900, locale zh, theme light, 27750 bytes, data_lang='zh', cjk=True, differs_from_en_twin=True
- `state-groupsnull-dark.png` — variant `groupsnull` (SYNTH), viewport 1440x900, locale en, theme dark, 28460 bytes, data_lang='en', cjk=False
- `state-groupsnull-light.png` — variant `groupsnull` (SYNTH), viewport 1440x900, locale en, theme light, 29666 bytes, data_lang='en', cjk=False
- `state-estimate-dark.png` — variant `estimate` (SYNTH), viewport 1440x900, locale en, theme dark, 246266 bytes, data_lang='en', cjk=False
- `state-estimate-light.png` — variant `estimate` (SYNTH), viewport 1440x900, locale en, theme light, 257690 bytes, data_lang='en', cjk=False
- `state-estimate-zh-dark.png` — variant `estimate` (SYNTH), viewport 1440x900, locale zh, theme dark, 236426 bytes, data_lang='zh', cjk=True, differs_from_en_twin=True
- `state-basisunknown-dark.png` — variant `basisunknown` (SYNTH), viewport 1440x900, locale en, theme dark, 241588 bytes, data_lang='en', cjk=False
- `zh-detail-dark.png` — variant `ok`, viewport 1440x900, locale zh, theme dark, 235027 bytes, data_lang='zh', cjk=True
- `zh-detail-light.png` — variant `ok`, viewport 1440x900, locale zh, theme light, 247408 bytes, data_lang='zh', cjk=True
- `m390-selected-dark.png` — variant `ok`, viewport 390x844, locale en, theme dark, 676088 bytes, data_lang='en', cjk=False
- `m390-selected-light.png` — variant `ok`, viewport 390x844, locale en, theme light, 680233 bytes, data_lang='en', cjk=False
