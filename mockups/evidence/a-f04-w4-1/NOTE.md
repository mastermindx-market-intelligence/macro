# A-F04-W4-1 Theme Tracker reading-order section — theme treatments

Anonymous fixture render of `templates/state_of_themes.html.j2`, not the live VPS page. Theme and language were set on `<html>` via `localStorage` + `add_init_script` **before** load. `prefers-reduced-motion: reduce`. No mid-toggle. Frames are full-page captures of the Theme Tracker fixture (desktop 1440×900, mobile 390×844). Recaptured at git HEAD `70cc5c00ca50` (the heal-round code commit the frames depict). The fixture files that produced these frames are committed under `fixtures/` (`ok.html`, `no_order.html`, `empty.html`, `unavailable.html`, `theme.css`, `theme.js`) so the capture reproduces.

The populated `/ok.html` frames use a **constructed** theme population: fifteen dated themes with staggered last-recorded dates (8 September 2026 down to 25 August 2026) plus three undated names. That is not the live store. Production currently records one evidence date (2026-07-09) across all 18 theme nodes, so clause 1 of the ordering rule does not separate those rows in production — the visible live sequence comes from the within-day count and then the name. These frames show the dated-slice, truncation sentence, and undated block the round-3 ruling requires, not a nightly snapshot.

What the fixture server did NOT serve (read `failed_responses` in the manifest for the
authoritative list): all five Inter weights (`Inter-400/500/600/700/800.woff2`),
`navigation-refresh.css`, `product-nav-icons.css`, `account.js`, `live.js`, `live_config.js`,
`logo_config.js` and `stock-logos.js` all 404 against the fixture. **So every frame below renders
in the fallback system stack, not the shipped Inter faces** — read the weight relationships in the
mechanism table as relative, not as a specimen of the shipped typography. `theme.css` and
`theme.js` ARE served from `fixtures/`, so `--panel` / `--line` / `--text` / `--muted` / `--card-shadow` resolve and
the enclosure, rule-weight and ink mechanisms described below are the real ones.

Which frames are which:

- `/ok.html` — constructed populated list (eight cells: desktop/mobile × en/zh × dark/light). Twelve numbered dated rows, truncation sentence naming the first 12 of 15 dated themes in this order, three undated names with no ordinal. Per-row ZH recorded-on has no ASCII space between the date and the text.
- `/empty.html` — honest empty state: title plus “We have not recorded new evidence for any theme yet.” / “目前还没有记录到任何主题的新证据。” No list, no dash, no zero.
- `/no_order.html` — the fourth honest null (seat round-4 ruling R2, heal-round REQUIRED 1): state `ok` with zero dated themes. Title plus “No tracked theme carries a dated entry yet, so there is no reading order to show.” / “目前没有任何主题带有日期记录，因此暂时没有可显示的阅读顺序。”, then the visible refusal “When an order is shown, it is a reading order, not a score.” / “显示顺序时，那只是阅读顺序，不是评分。”, then the three undated names. The undated note does not point at an order. The details summary is “How a reading order is made” / “阅读顺序是怎么排的”. No stance, no tie-break sentence, no `<ol class="rp-list">` above the undated block, no ordinal, no dash.
- `/unavailable.html` — honest unavailable state: title plus “The evidence record could not be read, so this list is not shown.” / “无法读取证据记录，因此这份清单暂不显示。” No list, no dash, no zero.

## DARK TREATMENT

Command-center card on the page surface. `.rp` sits on `var(--panel)` with a `var(--line)` border and an inset ring (`box-shadow: var(--card-shadow), inset 0 0 0 1px color-mix(in srgb, var(--line) 55%, transparent)`). No glow. Row rules are a softened `--line` mix. The ordinal is muted ink (`var(--muted)`, weight 600) so the names, not the place numbers, carry the hierarchy. The rule sentence is regular weight.

## LIGHT TREATMENT

Research-workspace card. `html[data-theme="light"] .rp` keeps `var(--panel)` (white material) and a `--line` hairline, then rests on a tokenized shadow (`var(--card-shadow), 0 8px 24px color-mix(in srgb, var(--text) 6%, transparent)`) instead of an inset ring. Row rules are a full `--line` hairline. The ordinal is `--text` at weight 700 — ink, not a muted afterthought. The rule sentence is weight 600 so it reads as a stated method, not a caption.

## Which mechanisms differ

| Mechanism | Dark | Light |
|---|---|---|
| Enclosure | inset `--line` ring + `--card-shadow` highlight; no drop shadow | `--card-shadow` plus a soft tokenized rest shadow |
| Rule weight | row dividers are a 70% `--line` mix; rule sentence at 500 | full `--line` hairline; rule sentence at 600 |
| Ink | ordinal `--muted` / 600 | ordinal `--text` / 700 |

Shared: information architecture, list semantics, EN/ZH copy, no JS styling, no new colour literal, no badge, bar, percentage or arrow on the place number.

## Degraded states

- `ok` (8-cell matrix on `/ok.html`): ordered list, rule sentence and not-a-score sentence visible without opening `<details>`.
- `empty` (`/empty.html`): title + empty sentence only. No list.
- `no_order` (`/no_order.html`): state `ok`, zero dated themes. Title + the honest sentence + the undated names. No stance, no ordered list, no ordinal.
- `unavailable` (`/unavailable.html`): title + unavailable sentence only. No list.
