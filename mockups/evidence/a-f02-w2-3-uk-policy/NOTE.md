# A-F02-W2-3 UK policy desk — theme treatments

Captured at committed sha `060e5b6795daf9b566ac24e4e66b6d050377de8b`. Theme and language were set on `<html>` via `localStorage` + `add_init_script` **before** load. `prefers-reduced-motion: reduce`. No mid-toggle. Frames are element clips of `.uk-desk` (1440: element clip; 390: content-box crop). Official GOV.UK headline in the fixture is English in both locales — that is the source title, not a missing ZH string.

## DARK TREATMENT

Command-center card on the page surface. The desk keeps `var(--panel)` from `.pw-surface` and overrides the page drop-shadow with `box-shadow: var(--card-shadow), inset 0 0 0 1px color-mix(in srgb, var(--line) 55%, transparent)` — highlight plus inset ring, no glow. A 3px left rail uses semantic tokens only: `--ink-ok` (supportive), `--warn` (restrictive), `--act` (mixed), `--muted` (routine). Stance chips use the same set. Degraded null rows (`source_outage`, `stale`, `model_unavailable`) print `--warn` ink on a `--warn` tint of `--panel`.

## LIGHT TREATMENT

Research-workspace card. `html[data-theme="light"] .uk-desk` sets `background: var(--panel)`, a `--line` hairline (the existing `.pw-surface` border), and `box-shadow: var(--card-shadow), 0 8px 24px color-mix(in srgb, var(--text) 6%, transparent)`. That color-mix stands in for the ruled `rgba(20,30,50,.06)` so the design-system checker stays `blocking=0`. Hover uses `var(--popover-shadow)`. The dark accent wash is not paled: the left rail becomes a 1px `--line` rule. `model_unavailable` and the other null rows drop the warn tint and print muted ink on `--panel2`.

## Which mechanisms differ

| Mechanism | Dark | Light |
|---|---|---|
| Enclosure | inset `--line` ring + `--card-shadow` highlight; no drop shadow | `--card-shadow` plus a soft tokenized rest shadow; hover `--popover-shadow` |
| Accent | 3px semantic-token rail | 1px `--line` hairline, same for every stance |
| Degraded null | `--warn` ink and tint | muted ink, `--panel2`, no hue |

Shared: information architecture, chip semantics, EN/ZH copy, no JS styling.

## Degraded states

- `ok` (8-cell matrix): no status row; headline + stance chip.
- `model_unavailable` (dark + light, EN 1440): "The plain-word read is not ready." / "平实解读尚未完成。" Status row in dark is `--warn`; in light it is muted with no colour. No stance chip. Official title still prints.
- `gate_off`, `no_new`, `source_outage`, `stale` share the same template rows as `model_unavailable` (typed `UK_STATE`); they were not recaptured as extra frames this pass.
