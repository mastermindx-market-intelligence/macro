---
title: MARKET ONTOLOGY F01 — MOR-2b build packet (Morning Orientation premarket edition)
status: FROZEN 2026-09-24 (seat: Meta-CEO A, Claude5 successor; Chairman override 2026-09-06)
ruling: DEC:MARKET-ONTOLOGY-MOR2B-PREMARKET-OWNER-AND-PLACEMENT-2026-09-24
input: research/market_intelligence_productization/MARKET_ONTOLOGY_F01_MOR2_PREMARKET_ARCHAEOLOGY_2026-09-24.md (PR #7876)
program_row: MO-PAID-011 (AM Edition) — PARTIAL → BUILT only on §0 proof
---

# §0 Acceptance gates (not done unless — every gate, no exceptions)

1. **Natural premarket run.** One untouched `macro-am-edition.service` run on the VPS inside the ET premarket
   window, receipted by `journalctl -u macro-am-edition.service` and `/var/lib/macro-live/state/am_edition/last_run.json`
   (`decision: build`, `generated_at` inside the window, `sources` with per-block typed states). A manual fixture,
   a `systemctl start` by hand, or a midday build is NOT proof (DEC :284-285).
2. **Served bytes are the overlay.** During the window `curl -sI https://www.mastermind-x.com/am_edition.html` returns
   `Cache-Control: no-store` and the page's "Built at" equals the receipt's `generated_at`; anonymous
   `GET /am_edition.json` stays **401** before and after (registered asset, unchanged); anonymous html stays **200**
   with `X-Robots-Tag: noindex, noarchive`.
3. **Freshest-wins proven.** After the next nightly bake lands (`generated_at` newer than the overlay), a later timer tick
   removes the overlay: `Cache-Control` returns to `public, max-age=60, must-revalidate` and "Built at" equals the bake.
4. **Typed-state falsifiers rendered, not asserted.** Weekend, NYSE holiday, missing owner file, stale owner file
   (`STALE_WITH_LAST_KNOWN` with last-known value + reason), `NOT_COVERED`, `NOT_YET_OPEN` — each a test with a
   fixture AND one rendered example in the PR body.
5. **Design evidence matrix.** 8 PNGs in the PR body: {dark, light} × {EN, ZH} × {desktop 1440, mobile 390}, both
   themes judged as designs (DESIGN_DOCTRINE §5; MASTER_PRODUCT_DESIGN_SYSTEM_V1 §12/§13). Missing light direction or
   missing ZH = PARTIAL, never PASS.
6. **Guards green at exact head.** `scripts/check_design_system.py --mode enforce-added` (no radius/colour literals in
   added lines), `scripts/check_runtime_style_injection.py`, `scripts/check_ui_visual_evidence.py`,
   `python3 scripts/agentos.py validate` → 0, `pytest tests/test_am_edition*.py tests/test_caddy_hub_boundary.py`.
7. **No second plane.** Diff proves: no new workflow/cron, no `data/` writes, no new palette/token family, no second
   producer, no `/live/*` top-level file_server, no change to which paths are public.
8. **Plain words.** Every new block carries EN+ZH copy with no internal state names, study names, raw slugs or
   untranslated stats (glance tier); nulls are disclosed with `.mx-empty` + `.mx-empty-why`.

# §1 Scope and sequence (three lanes, strictly sequential)

| Lane | Label | Owns | Depends on |
|---|---|---|---|
| A | `mo_a3_mor2b_a_producer` | `scripts/build_am_edition.py`, `tests/test_am_edition_producer.py` | — |
| B | `mo_a3_mor2b_b_vps` | `scripts/am_edition_live.py`, `app/deploy/macro-am-edition.{timer,service}`, `app/deploy/update.sh` (one block), `app/deploy/Caddyfile` (two matchers), `docs/VPS_LIVE_ORCHESTRATION.md` (one row + one section), `tests/test_am_edition_live.py`, `tests/test_caddy_hub_boundary.py` (extend) | A merged |
| C | `mo_a3_mor2b_c_surface` | `templates/am_edition.html.j2` (new blocks only), `templates/aibrief.html.j2` (band), `templates/_navlinks.html.j2` (one entry), `tests/test_am_edition_page.py` | A merged |

Each lane = one PR, MiniMax fix / qwen review on the external lane fabric, seat adjudicates, `merge-on-green`.
Lane B is the closure lane: its natural run is §0.1–§0.3. Lane C may run in parallel with B once A is merged.

# §2 Lane A — producer extension (frozen spec)

Keep every existing block, key, state and byte of default behaviour. Add:

**A1. Inputs.** `build_payload(site, data_dir, *, now=None, live_dir=None)`. When `live_dir` is None the tape block reads
`site/live/quotes.json` exactly as today (:367-376); when given, it reads `live_dir/quotes.json` and `source_ref`
says `live/quotes.json (vps)`. `main()` gains `--out-dir PATH` (default: `cfg["storage"]["site_dir"]`) and
`--live-dir PATH` (default: none). Refactor the Jinja render in `main()` (:829-843) into `render_html(payload) -> str`
so the VPS wrapper can render without writing; `main()` keeps calling `lib.pages.write_page` for the nightly path.

**A2. Block `context_planes` (DEC item 3).** One block, rows in this order, each row `{plane, label_en, label_zh,
read_en, read_zh, as_of, source_ref, state}`:
- `rates` ← `data/transmission/latest.json` `state.rates` (regime words + `turn_watch` when non-null, rendered as a
  plain-word "watch" phrase, never the percentile), `yield_curve`;
- `dollar` ← `state.dollar_channel.state.{en,zh}` from the same file;
- `credit` ← the credit state in the same file if a keyed field exists (verify by reading the artifact; if absent →
  row state `NOT_COVERED`, reason "credit is not projected by the transmission owner yet");
- `commodity` ← `data/commodity/latest.json` `regime`, `favored`, `breadth` (plain words, no index level);
- `international` ← china and hk `market_state` (`label_en/zh`, `posture_en/zh`, `headline_en/zh`, `asof`) at the
  paths recorded in the MOR-2a census §2 table.
Block state = worst row state; per-row `as_of` drives `CURRENT` (≤ 1 US session old) vs `STALE_WITH_LAST_KNOWN`.

**A3. Block `research_watch` (DEC item 6).** Rows from the track-record and theses artifacts named in the census §2
table: at most 5 open watch conditions, each `{condition_en, condition_zh, since, as_of, source_ref}`; words only —
no direction, size, order, target or "buy/sell". If the newest row is older than 10 US sessions the block is
`STALE_WITH_LAST_KNOWN` with the plain reason "research watch last updated <date>". No LLM, no ranking.

**A4. Block `owner_links` (DEC item 8).** Rows `{label_en, label_zh, href, kind}` where `kind ∈ {owner, reference}`:
one owner page per plane rendered above (`macro.html`, `rates_curves.html` or the route the transmission owner
renders to — verify in `templates/_navlinks.html.j2`, commodities page, china page) and Reference deep links resolved
through the MOR-1 registry loader used by the Reference builder (`mastermind.market_reference/v1`; verify the
module name with `git grep -n market_reference scripts/`). A test asserts every `href` resolves to an existing
template route or registry anchor; an unresolvable link is dropped, never guessed.

**A5. Tests** (`tests/test_am_edition_producer.py`): default byte-identity (payload with `live_dir=None` equals today's
for a frozen fixture dir); `live_dir` redirect; each new block in all five typed states via fixtures; A7 guard (no
row text contains `buy|sell|long|short|target|size|做多|做空|买入|卖出`); `owner_links` resolution.

# §3 Lane B — VPS premarket owner (frozen spec)

**B1. `scripts/am_edition_live.py`** (oneshot, never raises, exit 0 unless the box is misconfigured):
1. root = cwd (`/opt/macro`); live_dir via the three-rung ladder copied verbatim from
   `engine/neuralweb/market_packet.py:86-101` (env `MACRO_LIVE_DIR` → `/var/lib/macro-live/public/live` → `site/live`);
   public_dir = `/var/lib/macro-live/public`; state_dir = `/var/lib/macro-live/state/am_edition`.
2. `now` = UTC; phase = `build_am_edition._session_phase(now)`; bake = `site/am_edition.json` `generated_at`;
   overlay = `public_dir/am_edition.json` `generated_at` if present.
3. Decision, in order: (a) overlay exists and bake newer → **expire** (remove both overlay files); (b) phase == `preopen`
   on a NYSE session date → **build**: `payload = build_payload(site, data_dir, now=now, live_dir=live_dir)`,
   `html = render_html(payload)`, write both files atomically (temp file in `public_dir` + `os.replace`, the live plane's
   idiom); (c) otherwise **skip**.
4. Receipt `state_dir/last_run.json`: `{decision, generated_at, phase, bake_generated_at, overlay_generated_at,
   block_states: {key: state}}`. State dir is not web-addressable (docs §Runtime layout).

**B2. Units.** `app/deploy/macro-am-edition.service`: `Type=oneshot`, `WorkingDirectory=/opt/macro`,
`EnvironmentFile=-/etc/macro-live.env`, `ExecStart=/opt/macro/.venv/bin/python -m scripts.am_edition_live`, `Nice=10`,
description "Build the Morning Orientation edition overlay in the ET premarket; expire it when the nightly bake is newer".
`app/deploy/macro-am-edition.timer`: `OnCalendar=*-*-* 08..14:07,37:00 UTC`, `RandomizedDelaySec=60`, `Persistent=false`,
`Unit=macro-am-edition.service`, `WantedBy=timers.target`. (08–14 UTC covers ET 05:00–09:30 under EDT and EST; the
service's own phase check decides build/expire/skip, so weekends and holidays are skips.)

**B3. `app/deploy/update.sh`.** One block modelled line-for-line on the entry-radar block (:1957-1999): trigger when
`CHANGED` matches `^(app/deploy/macro-am-edition\.(service|timer)|scripts/am_edition_live\.py|scripts/build_am_edition\.py)$`
or the timer file is absent; `systemd-analyze verify`; `install -m 0644`; `daemon-reload`; `enable --now`. **No arm
flag** (the lane reads only files already on the box and writes only under the live store); symmetric stand-down flag
`AM_EDITION_LIVE_DISABLE=1` in `/etc/macro-live.env` → `disable --now` and remove the overlay files.

**B4. `app/deploy/Caddyfile`.** Two matchers, nothing else: (i) inside `handle @open_html`'s `route` block, AFTER the two
`header` lines and BEFORE `file_server` (:424-440), add `@am_edition_live { path /am_edition.html  file { root
/var/lib/macro-live/public } }` + `handle @am_edition_live { root * /var/lib/macro-live/public  header Cache-Control
"no-store"  file_server }`; (ii) add `/am_edition.json` to the `@vps_external` path list (:225-231), which already serves
only from inside `handle @reg_asset` (:371-374). Never add `/am_edition.json` to `@vps_public_live`.

**B5. Docs.** `docs/VPS_LIVE_ORCHESTRATION.md`: one row in the §Decision table — "Morning Orientation premarket edition
(`/am_edition.html`, `/am_edition.json`) | VPS, every 30 min in the ET premarket | Nightly `daily.yml`/`render.yml`
bake (writer of `site/am_edition.*`, unchanged)" — and one short section stating the overlay + freshest-wins rule.

**B6. Tests.** `tests/test_am_edition_live.py` (decision table with a fake clock and temp dirs: expire / build / skip,
atomic write, receipt shape, never raises on a missing owner file); extend `tests/test_caddy_hub_boundary.py`: the
json is in `@vps_external` and NOT in `@vps_public_live`; the html overlay handle sits inside `handle @open_html`;
no new top-level `/live/*` file_server.

# §4 Lane C — surface (seat-pinned design; builder implements, does not choose)

**C1. Template blocks** (`templates/am_edition.html.j2`, after `cross_asset_plane` and before `todays_calendar`):
`context_planes`, `research_watch`; `owner_links` after `prior_close_brief_ref`. Every block is a `.panel` with an
`.eyebrow` label, an `<h2>`, a state chip and `.dtp-asof` clock in the header row, then rows. Typed state → chip:
`CURRENT`→`.dtp-chip.dtp-chip--live`, `NOT_YET_OPEN`→`--pre`, `STALE_WITH_LAST_KNOWN`→`--stale`,
`UNAVAILABLE`→`--warn`, `NOT_COVERED`→`--behind`; chip text is the plain-word EN/ZH state, never the enum.
A block whose state is not `CURRENT`/`STALE_WITH_LAST_KNOWN` renders `.mx-empty` + `.mx-empty-line` + `.mx-empty-why`
(the reason), no rows. `context_planes` rows use the existing `.ctx-row`/`.ctx-label` idiom; `owner_links` rows reuse
`.brief-link`. All new CSS in token form only (`var(--r-card)`, `var(--line)`, `var(--panel)`, `var(--muted)`,
`var(--ink-up|--ink-warn|--ink-link)`, `var(--sp-*)`, `var(--fs-*)`); no fallback literals in added lines.

**C2. Art direction.** DARK (command center): depth from the `--panel` over `--bg` luminance step; chips are tinted
text on transparent fill with the `.dtp-dot` pulse only on `--live`; hairline `--line` borders; no shadows.
LIGHT (research workspace): white `--panel` material on the cool canvas, 1 px `--line` hairlines, chips gain a soft
token-only fill `color-mix(in srgb, currentColor 10%, transparent)` and no pulse, section `.eyebrow` in `--muted`;
the tooltip keeps `--popover-shadow`. Mechanisms that intentionally differ: chip fill, pulse, depth device
(luminance vs hairline+material). Baseline reference: the existing six panels of the same page in each theme.
Degraded states per theme: the `.mx-empty` block must remain legible on both canvases (test both).

**C3. aibrief band** (`templates/aibrief.html.j2`, directly under the page h1 :99): one `.panel` "Morning Orientation /
盘前导读" reading `site/am_edition.json` via the same loader `build_aibrief.py` uses for its siblings: session-state
chip, "Built at" `.dtp-asof`, the tape block's first row as one sentence, and a `.brief-link` to `am_edition.html`.
When the JSON is absent the band renders `.mx-empty` with the reason; it never blocks the brief.

**C4. Nav.** `templates/_navlinks.html.j2` "Core Research" grid (:221-279): one `mega-item nm-feat` entry for
`am_edition.html` next to `reference.html` (:276), EN "Morning Edition" / ZH "早间版", with a new 48×48 line-icon in
the same drawing idiom (a sunrise line over a horizon bar; not a clock — the session clock owns that glyph).

**C5. Tests** (`tests/test_am_edition_page.py`): renders each new block in every typed state from fixtures; ZH parity
(every EN string has a ZH twin via `t()`); no `title=` translated text; `enforce-added` clean.

# §5 Evidence matrix (PR body of lanes B and C)

| # | Theme | Lang | Viewport | Page |
|---|---|---|---|---|
| 1–4 | dark, light | EN, ZH | 1440 | `am_edition.html` (all blocks, one in a non-CURRENT state) |
| 5–8 | dark, light | EN, ZH | 390 | `am_edition.html` |
| 9–10 | dark, light | EN | 1440 | `aibrief.html` band (lane C) |

Lane B adds the three curl receipts of §0.2–§0.3 and the `last_run.json` of the natural run.

# §6 DO-NOT (binding)

- Do not rebuild, restyle or restructure the six existing blocks or B's page header; extend only.
- Do not add a GitHub workflow, cron, or `schedule:`; do not touch `daily.yml`/`render.yml`.
- Do not write under `data/`; do not commit `site/` re-bakes; the nightly remains the only writer of `site/am_edition.*`.
- Do not widen the static boundary: json stays 401 anonymous; html stays `noindex`.
- Do not originate signals, scores, orders or escalations (A7); research watch = conditions in words.
- Do not author styling in JavaScript; no new palette or token family; no colour/radius literals in added lines.
- Do not add a second producer, a second JSON, or a client-side re-render of the blocks.
