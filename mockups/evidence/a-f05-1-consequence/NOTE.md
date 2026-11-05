# A-F05-1 News consequence panel — dual-theme evidence

Recaptured 2026-09-08 after the r5 code commit
`b2bec2a51a19f5bde35d6200fef84a4a222ec7e5`. Host page is a local Jinja
render of this branch's `templates/news.html.j2` over
`origin/main:data/chronicle/events.jsonl` (`git show` into
`/tmp/r6896-r5/events.jsonl`; no `data/` write). Fixture pages are the
HTML under `fixtures/`. Playwright screenshots `#nxConsequence` with
16px side/top and 28px bottom padding so the heading, card bottoms, and
drop shadows sit inside the frame — not a viewport crop.
`generated_at` is the UTC clock at capture start (`2026-09-08T09:45:39Z`).
`manifest.target.resolved_sha_or_none` and `capture_sha` are that code
commit. `site/news.html` was not written.

Proof that the frames commit does not rewrite the selector: after the
frames land,
`git diff b2bec2a51a19 HEAD -- templates/news.html.j2 engine/chronicle/impact.py scripts lib`
is empty.

**Real window (shipped selector).** `glance_consequence_surface` on the
11,087-event spine returns `window_mode=last_7_days`, as-of 2026-09-07,
header EN `Events from 31 Aug to 7 Sep 2026` /
ZH `2026年8月31日至9月7日的事件`, `event_count=97`, **0 rows**,
`empty_kind=no_named_exposure`. The panel prints the designed empty
state: leading rule + “No event with a named market exposure in the last
7 days.” / “近7天没有带明确市场敞口的事件。” + “Cards appear when an
event maps to a named exposure.” / “当事件对应到明确标的时，卡片会在此显示。”
Cause: the ticker-bearing eligible families are `earnings` (5,548,
newest 2026-08-20) and `earnings_call` (3,504, newest 2026-08-28); both
stop before the 7-day cutoff of 2026-08-31. The in-window ticker-bearing
family is only `prophet_ledger` (29), which this selector excludes.
Cards reappear when the earnings / earnings-call enrichment feed catches
up inside the window. That is a data-availability fact, not a selector
bug.

**Second-order path.** `project_events_impact` + the glance selector on
this corpus yield **0** second-order-only projections before the title
gate and **0** after it (window and full spine). No second-order-only
rows reach this surface in the current corpus; the branch is live but
unexercised. Visual evidence is the fixture-route frames from
`fixtures/second-order-only.html` (Also watching NVDA + AMD; no Named
label; no “No named ticker”).

**Populated cards (fixture).** `fixtures/named-exposure-earnings.html`
from three real `earnings` events (FISV, HLX, KO). Dark/light × EN/ZH at
1440 and 390. No size slot.

**Also-watching branches (fixture).** Dark/light × EN/ZH at 1440 for
present / truncated / dropped; truncated also at 390 (4-chip wrap).

**DARK TREATMENT:** command center — deep charcoal sheet, blue accent
bar on the section head. Cards and the empty plane use
`box-shadow: var(--card-shadow)` (dark token is the 1px top highlight)
plus an inset ring
`inset 0 0 0 1px color-mix(in srgb, var(--line) 55%, transparent)`.
No drop shadow. No glow.

**LIGHT TREATMENT:** research workspace — white `var(--panel)` plane,
hairline `var(--line)`, elevation from the light `--card-shadow` token
plus one ambient layer
`0 8px 24px color-mix(in srgb, var(--text) 6%, transparent)`. Hover on
cards uses `var(--popover-shadow)`. The light *page canvas* around the
cards is the inherited `theme.css` wash: a cool lavender / periwinkle
tint, strongest toward the top of fixture frames such as
`58ee1533148f82cf` and `0f64a00d1facef74`. That wash is not authored by
this panel's CSS; the panel's own light material is the white plane.

**Which mechanisms differ:** dark depth is highlight + inset `--line`
ring; light depth is a white plane + hairline + a real drop shadow.
Shared: `#nxConsequence` markup, 280px auto-fill grid, section copy.

**Degraded states:** ZERO named-exposure events prints the designed
empty plane (not a bare centred paragraph). An empty input still prints
“Not available yet” / “暂不可用” with a typed reason. The newest-200
fallback is labelled “Latest 200 recorded events” /
“最近记录的200个事件”.

**Layout:** `#nxConsequence` is a single-column `.nx-consequence`
wrapper. Specified grid is `repeat(auto-fill,minmax(280px,1fr))` /
`gap:14px`. Crop column below is PNG IHDR
(`struct.unpack('>II', data[16:24])`).

**Rest-cell frames (shipped selector, real corpus — designed empty):**

| file | theme | locale | viewport | crop (IHDR) |
|---|---|---|---|---|
| `3650abc7e529c530.png` | dark | en | desktop 1440 | 1039×197 |
| `40a99d21924b4fce.png` | light | en | desktop 1440 | 1039×199 |
| `fd207bcb4e2f7b0a.png` | dark | zh | desktop 1440 | 1039×197 |
| `0631bd7e412a8e61.png` | light | zh | desktop 1440 | 1039×199 |
| `a738d7f65db5f6cd.png` | dark | en | mobile 390 | 352×233 |
| `0d154ceac06f2421.png` | light | en | mobile 390 | 352×235 |
| `9f67852016984139.png` | dark | zh | mobile 390 | 352×197 |
| `a0fef6ad533bde2a.png` | light | zh | mobile 390 | 352×199 |

**Named-exposure earnings fixtures (dark/light × EN/ZH × 1440 + 390):**

| file | theme | locale | viewport | crop (IHDR) |
|---|---|---|---|---|
| `b9e63faa3f936762.png` | dark | en | desktop 1440 | 1436×262 |
| `58ee1533148f82cf.png` | light | en | desktop 1440 | 1436×262 |
| `15ec07874799ddc1.png` | dark | zh | desktop 1440 | 1436×242 |
| `ced17fca6a42dce3.png` | light | zh | desktop 1440 | 1436×242 |
| `cc76357a59af5923.png` | dark | en | mobile 390 | 386×446 |
| `9425a29fa9ffca49.png` | light | en | mobile 390 | 386×446 |
| `2c40ba8396243aab.png` | dark | zh | mobile 390 | 386×446 |
| `f1edd25d1b4519ca.png` | light | zh | mobile 390 | 386×446 |

**Also-watching + second-order-only fixtures:** see `manifest.json`
(40 captured states; 40/40 sha256 and IHDR match).
