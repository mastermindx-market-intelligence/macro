# A-F04-W4-1 Theme Tracker reading-order section — theme treatments

Anonymous fixture render of `templates/state_of_themes.html.j2`, not the live VPS page. Theme and language were set on `<html>` via `localStorage` + `add_init_script` **before** load. `prefers-reduced-motion: reduce`. No mid-toggle. Frames are full-page captures of the Theme Tracker fixture (desktop 1440×900, mobile 390×844).

What the fixture server did NOT serve (read `failed_responses` in the manifest for the
authoritative list): all five Inter weights (`Inter-400/500/600/700/800.woff2`),
`navigation-refresh.css`, `product-nav-icons.css`, `account.js`, `live.js`, `live_config.js`,
`logo_config.js` and `stock-logos.js` all 404 against the fixture. **So every frame below renders
in the fallback system stack, not the shipped Inter faces** — read the weight relationships in the
mechanism table as relative, not as a specimen of the shipped typography. `theme.css` and
`theme.js` ARE served, so `--panel` / `--line` / `--text` / `--muted` / `--card-shadow` resolve and
the enclosure, rule-weight and ink mechanisms described below are the real ones.

Which frames are which:

- `/ok.html` — populated reading-order list (the eight REST cells: desktop/mobile × en/zh × dark/light).
- `/empty.html` — honest empty state: title plus “We have not recorded new evidence for any theme yet.” / “目前还没有记录到任何主题的新证据。” No list, no dash, no zero.
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
- `unavailable` (`/unavailable.html`): title + unavailable sentence only. No list.
