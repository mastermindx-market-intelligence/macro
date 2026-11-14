# Provenance — #6988 shared-public logo hover evidence

Run `2026-11-05T11:07:26Z` (capture time is `2026-11-05T11:02:41Z` from the capture tool's own manifest).

## Candidate source under test

| item | value |
| --- | --- |
| repository | `mastermindx-market-intelligence/Macro` |
| branch (root-owned) | `claude/ssd-homepage-product-logo-294c61b96b6d37ba` |
| candidate head | `e559fed9941635fe4932ac41ddd75a6ca0070738` |
| candidate tree | `a590bb6210c392ad3a165ba1b712ba6e820dcf88` |
| tested base | `80136935b4d28caeda6c6a50eb385797190fdc32` |
| material change owned by this receipt | `templates/_public_chrome_css.html.j2` |

The captured page was rendered from that exact head: the capture manifest's `target.resolved_sha_or_none` is `e559fed9941635fe4932ac41ddd75a6ca0070738` (HEAD of the worktree that served `--site-dir`, at capture time).

## Rendered page (candidate source, not the committed cache)

| item | value |
| --- | --- |
| renderer | `scripts.build_site.build_support_page` (the candidate's own function) |
| template | `templates/support.html.j2` |
| Jinja loader root | `<worktree>/templates` |
| output | `<worktree>/site/support.html` |
| bytes | 86994 |
| sha256 | `dafe41751872ca577d4e19e656144eca96017181eb619a85565822bcc6082fdd` |
| committed `site/support.html` blob at candidate head | `2700920844f95daa5fe5db65ddadaa9e28d2a096` (sha256 `ffb33de406cd5104657f6868ad6fc7dfa25408d349cb0f534bb256f86dac704e` — the stale cached build, still carrying `<span class="m">M</span>`) |

The render was **uncommitted output**: it modified the tracked `site/support.html` in the worktree only, was served from there during capture, and was restored with `git checkout -- site/support.html` afterwards. It is not part of this PR. The rendered bytes are returned as an artifact (`rendered-support.html`) so the capture can be re-checked against the same source identity.

## Capture

| item | value |
| --- | --- |
| tool | `scripts/capture_page_evidence.py` v1.4.0 |
| tool module sha256 | `9b6e643c1c784eb81b584be4cb063092ae71c4a16fe01498130891e84cd0de42` |
| route | `/support.html` (`page_id` `support.html`, `route_kind` `explicit_override`) |
| target | `--site-dir /home/ubuntu0/lanes/wt/macro-pr6988-hover-20261105-c3/site` (local static server, loopback only) |
| outcome | `captured` — 16/16 states |
| axes | viewports {'desktop': [1440, 900], 'mobile': [390, 844]} × locales ['en', 'zh'] × themes ['dark', 'light'] × access ['anonymous'] |
| force state | `public-brand-hover:hover(.public-brand)` (kind `hover`, target `.public-brand`) |

Exact command:

```
python3 scripts/capture_page_evidence.py \
  --site-dir site --routes /support.html \
  --viewports desktop,mobile --locales en,zh --themes dark,light \
  --force-state "public-brand-hover:hover(.public-brand)" \
  --output-dir mockups/evidence/homepage-product-logo-public-hover-20261105 \
  --manifest mockups/evidence/homepage-product-logo-public-hover-20261105/manifest.json \
  --smells mockups/evidence/homepage-product-logo-public-hover-20261105/smells.json \
  --settle-ms 1400
```

The stock tool expands one force state across every cell, so the single capture is the 16-cell result (8 REST cells + 8 force-state cells).

## Cells

| viewport | locale | theme | force_state | applied_force_state | captured | file | bytes | px | sha256 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| desktop | en | dark | — | — | True | `0b00f5342b30c5a3.png` | 248723 | 1440×1276 | `0b00f5342b30c5a312c47d5a9c9f0692cbca0159a07dee5bbac8f92a62bc65fe` |
| desktop | en | dark | public-brand-hover | public-brand-hover | True | `5ac800f92a84d67f--public-brand-hover.png` | 248989 | 1440×1276 | `5ac800f92a84d67f9b4bcd6b08d81f58cd0486ed10a0f1668fec878a16ff3bdd` |
| desktop | en | light | — | — | True | `dd90989e5496c21e.png` | 234920 | 1440×1276 | `dd90989e5496c21e84915a7ea49bb051b9a3756d2d5f722c52be7fa3a3ec5af3` |
| desktop | en | light | public-brand-hover | public-brand-hover | True | `7aae4cf484de2087--public-brand-hover.png` | 235127 | 1440×1276 | `7aae4cf484de2087a8855245ca7cec37dcb68bfeb9080d0398cdf7ad32217bd7` |
| desktop | zh | dark | — | — | True | `58c69e86ca4aaeac.png` | 265966 | 1440×1228 | `58c69e86ca4aaeacf108d9b9be05e8b2dc3db6f4d98932b5bde217b16e059c47` |
| desktop | zh | dark | public-brand-hover | public-brand-hover | True | `8c1014f8ad8f2ff5--public-brand-hover.png` | 265707 | 1440×1228 | `8c1014f8ad8f2ff52c7e6ae4e769122ccab24e1559d101896800273655f47928` |
| desktop | zh | light | — | — | True | `d063cb07f7c900be.png` | 252076 | 1440×1228 | `d063cb07f7c900bea919eef3db6808defe8333172fad10785f62ac38df8909fc` |
| desktop | zh | light | public-brand-hover | public-brand-hover | True | `55d1679b6001eeb5--public-brand-hover.png` | 252239 | 1440×1228 | `55d1679b6001eeb5a0fa87e12a6a4409f58891f6203566d72d8ea6fd42cfed36` |
| mobile | en | dark | — | — | True | `b20c59296c87605b.png` | 159957 | 390×1856 | `b20c59296c87605bf1e7570dda8e31b40734675e272846e48e7ff1fbce019f40` |
| mobile | en | dark | public-brand-hover | public-brand-hover | True | `d1f2ad3f042eeb04--public-brand-hover.png` | 159993 | 390×1856 | `d1f2ad3f042eeb04e745f534809ce72debbaf20fad9a4fa94b5df56a40033ed9` |
| mobile | en | light | — | — | True | `65f876e4c132ced1.png` | 158670 | 390×1856 | `65f876e4c132ced1dbc0f6115e4c1ea7445db2b06410137ab229d2871de26572` |
| mobile | en | light | public-brand-hover | public-brand-hover | True | `6aa4b47d9b095881--public-brand-hover.png` | 158777 | 390×1856 | `6aa4b47d9b095881b1dcb3dd731f518f5466eb0d2d164065b7e7475a127767d2` |
| mobile | zh | dark | — | — | True | `80495d5e33e4c18d.png` | 160404 | 390×1785 | `80495d5e33e4c18dce2baea671bc70199d539358a50780702333d4f6ce87da3c` |
| mobile | zh | dark | public-brand-hover | public-brand-hover | True | `94e0f06e9fdc8fc7--public-brand-hover.png` | 160493 | 390×1785 | `94e0f06e9fdc8fc7ee71dbdb37149c21b28f2cb5eee8878827ebc277b5adb8b7` |
| mobile | zh | light | — | — | True | `a5b6d60e54c9d516.png` | 160600 | 390×1785 | `a5b6d60e54c9d516c2f999321061c45825909526d92d138e275fa93bb3126687` |
| mobile | zh | light | public-brand-hover | public-brand-hover | True | `79085c0afbb02aa3--public-brand-hover.png` | 160665 | 390×1785 | `79085c0afbb02aa3e25f95432e945451d3cbd9f8fa2983687de98b67d233f6ca` |

Every force-state cell records `applied_force_state: public-brand-hover`, i.e. the browser reported that the real `:hover` state actually took on `.public-brand` before the shot. The guard's required interaction proof (desktop/en, dark **and** light) is present.

## Focused public-chrome probe (same rendered page, live browser)

| viewport | theme | favicon.svg loaded | rendered px | home link aria-label | wordmark text | wordmark colour (rest / hover) | brand hovered | chrome bg (dark theme) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| desktop | dark | 512×512 natural | 27×27 | `MastermindX home` | `MASTERMINDX` | rgb(28, 36, 48) / rgb(28, 36, 48) | True | rgba(247, 248, 250, 0.85) |
| desktop | light | 512×512 natural | 27×27 | `MastermindX home` | `MASTERMINDX` | rgb(28, 36, 48) / rgb(28, 36, 48) | True | rgba(247, 248, 250, 0.85) |
| mobile | dark | 512×512 natural | 27×27 | `MastermindX home` | `MASTERMINDX` | rgb(28, 36, 48) / rgb(28, 36, 48) | True | rgba(247, 248, 250, 0.85) |
| mobile | light | 512×512 natural | 27×27 | `MastermindX home` | `MASTERMINDX` | rgb(28, 36, 48) / rgb(28, 36, 48) | True | rgba(247, 248, 250, 0.85) |

Read from the live DOM, not inferred: the SVG really loads (natural size 512×512, painted at exactly 27×27 CSS px), the home link keeps `aria-label="MastermindX home"` and `href="index.html"`, the wordmark is still real text (`MASTERMINDX`), and its colour is the same navy `rgb(28, 36, 48)` (`#1c2430`) at rest and under hover in **both** themes. The public chrome bar stays light (`rgba(247, 248, 250, 0.85)`) while the page body is dark in the dark theme — the intended public-chrome behaviour. Mobile geometry is unchanged (brand box 136×27 at x=20 with the 13px wordmark, versus 152×27 at x=140 on desktop).

## Observations reported honestly

- Console/response errors on this page: `http://127.0.0.1:48841/api/billing/offers/founding_pro` → `404` (one request, `/api/billing/offers/founding_pro`). This is the **same** billing-404 observation the pre-existing `mockups/evidence/homepage-product-logo/manifest.json` already records for the index page; it is an artifact of serving a static site directory with no API behind it, it is not new, and it is not caused by this change.
- Horizontal overflow on this page: `False` (desktop and mobile), `elements_wider_than_viewport` = 0. The historical mobile-overflow observation was recorded against a different, taller page and is **not** re-asserted here as a fresh whole-page pass of that page.
- No new defect was observed on the shared-public page at desktop 1440 and mobile 390, EN and ZH, dark and light.

## Preservation

`mockups/evidence/homepage-product-logo/` — all 17 pre-existing files — are byte-for-byte unchanged (verified blob-by-blob against the candidate head; see the return manifest). This receipt adds one new directory and changes no CSS, template, navigation behaviour or gate.
