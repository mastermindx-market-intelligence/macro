# Crypto T20 assistant-context census — 2026-10-12

Read-only census of the Ask Mastermind entry on the crypto and Bitcoin Vector pages, plus the packet the brain actually grounds on. Tree: `claude/cx-t20p-20261012` after candidate base `#8050` `fd8095012e91` applied onto `origin/main` `eaec265515a`. The Ask buttons, the failure copy, and the vector source table are in that R2 template delta (`git diff origin/main -- templates/crypto.html.j2 templates/vector.html.j2` shows them as additions). `engine/neuralweb/brain_gateway.py`, `engine/neuralweb/market_packet.py`, `templates/mm_brain.js`, and `templates/theme.js` are main's, not the R2 delta.

No template, gateway, or packet file was edited. No patch file: a page-only `MM_BRAIN_CFG.page` still cannot carry source identity, the shown as-of, or the time-machine cursor. `compile_envelope` copies ambient `symbol` / `timeframe` / `page` / `panel` only (`engine/intelligence_workspace/context_compiler.py:423-440`), and `page` is capped at 32 characters (`context_compiler.py:51`).

## Findings

| Claim | Where | Result |
| --- | --- | --- |
| Crypto mounts Ask Mastermind as a dialog button, not a navigation link | `templates/crypto.html.j2:289` `data-crypto-brain`, `aria-controls="mmb-panel"` | Button calls `MMBrain.open()` with no arguments (`:497`) |
| Vector mounts the same widget from its section bar | `templates/vector.html.j2:348-351` | `MMBrain.open()` with no arguments (`:782`) |
| The widget script is not on the page; theme.js loads it on intent | `templates/crypto.html.j2:471`, `templates/vector.html.j2:763` load `theme.js`. Loader: `templates/theme.js:5226-5238` | First click of `#mmb-boot` fetches `mm_brain.js` |
| Page context is the string `dashboard` for both pages | `templates/theme.js:5422-5428` sets `MM_BRAIN_CFG` with `anchor: 'br'` and a symbol hook, no `page`. `templates/mm_brain.js:3611` and `:3624` then use `dashboard` whenever anchor is not `top` | Crypto and vector are not named |
| The file header's "page default derived from location" is not what the code does | `templates/mm_brain.js:14` | Search of `templates/mm_brain.js` for `pathname`, `crypto.html`, and `vector.html`: no matches |
| Neither page sets `MM_BRAIN_CFG` or `getAiContext` | Search of both templates for `MM_BRAIN_CFG` and `getAiContext`: no matches | The shown page is not passed |
| Shown as-of stays in the HTML | Crypto hero `templates/crypto.html.j2:300` and footer `:468`. Vector chip `:363` and footer `:759` | Not an argument to `open()` |
| Vector source identity stays in the source table | `templates/vector.html.j2:443-445` `chart_contract.meta.fields.{price,risk,allocation}.source_id`; observed_at `:448` | Not passed. Crypto's budget source is the literal `btc.decision/v1` (`templates/crypto.html.j2:431`) and is also not passed |
| The historical scrubber is DOM state | `templates/vector.html.j2:573-607` `#vtm-range`, `#vtm-date`, `data-vtm-jump` including `now` and `2022-11-09` | No reader in the brain click handler `:775-792` |
| Live packet crypto slice is BTC and ETH quotes only | `engine/neuralweb/market_packet.py:132`, `:559` | No vector decision, no `source_id`, no scrubber cursor |
| Quote clock is not the eval clock | `market_packet.py:565` stores `quotes.asof`. `build_packet(..., now=)` is staleness only (`:1211-1223`) | Row has `basis`, not its own `asof` (`:539-540`) |
| A missing quote is omitted | `market_packet.py:528-534` returns `None` when price and change are both absent. Doc `:31-33` | Not rendered as zero. An explicit `0` change renders `0%` (`:387-388`) |
| Stale tape is labeled last-known on that line only | `market_packet.py:285`, `:1515-1516` | Header still says `CURRENT DASHBOARD STATE` (`:287-290`) even when `stale_warn` is true |
| Protected ontology/rotation context fails closed for guests | `brain_gateway.py:1662-1673`, `:4776-4777` | Empty, `unknown`, and `guest:` ids return before the paywall read |
| The live tape digest is not user-gated | `brain_gateway.py:4786-4802`, prepended at `:6816-6818` | Every turn that reaches the loop, guest included, can see the quote tape. That tape is not the cockpit's protected context, because the cockpit context is not sent |
| Client cannot forge the server block | `brain_gateway.py:8405-8412` strips `_server` | Forged `effective_context` inside `ai_context` is `rejected_fields` (`context_compiler.py:258-262`) |
| Auth for `/api/brain/stream` is verify-or-401, guest only if the operator flag is on | `app/main.py:1366-1392`, route `:1483-1533` | A 502 from identity is not turned into a guest (`:1386-1388`) |
| A loopback script 404 is not `MMBrain.open()` | `theme.js:5238` `onerror` flushes `false`. `:5347-5351` clears `aria-busy` and does not open | Crypto then shows the status (`crypto.html.j2:507`). Vector sets `data-state="error"` (`vector.html.j2:791`) |
| An API run 404 is not a finished reply | `app/main.py:1601-1602` and `:1617-1620` raise 404 for unknown, expired, or not owned. Client `templates/mm_brain.js:2703` does not take the success path; `:2793` `!res.ok` calls `failTurn` | Error card text is "The reply didn't make it through." (`:2967`). `announceDone` (`:2975`) runs on the persisted-tail success path (`:2736`), not on `failTurn` |

## What the click does

Crypto (`templates/crypto.html.j2:500-508`): hide the status, disable the button, set `aria-busy`, call `open()` if `MMBrain.open` exists, otherwise click `#mmb-boot` and poll every 50 ms up to 60 tries (3 s). On timeout, re-enable the button and unhide `.desk-brain-status` (`:291`): "The assistant is not ready. Market research remains available." The desk nav (`:292-294`) is never disabled. `crypto-desk-ready` is added immediately (`:510`), which hides `#mmb-boot` and `#mmb-launch` (`:73`) whether or not the script loaded.

Vector (`templates/vector.html.j2:775-792`): same 3 s poll. Timeout sets `data-state="error"`, which swaps the label to "Mastermind unavailable" (`:58-60`, `:351`). The section tabs (`:340-347`) stay ordinary links. The button is not disabled, only `aria-busy`. There is no `role="status"` on the error label. `#mmb-boot` and `#mmb-launch` are hidden for the whole page (`:61`), not only after a successful open.

`MMBrain.open` (`templates/mm_brain.js:3095`) refreshes the symbol chip and opens `#mmb-panel`. It does not accept a page payload. `buildTurnContext` (`:3619-3626`) sends `page`, `lang`, `ai_context`, and maybe `symbol` / `panel` / `timeframe`. With theme's config, `ai_context.ambient.page` is `dashboard` (`:3611`).

## Failure, focus, 404

Research and navigation stay in the page. The assistant failure does not remove shelves, tabs, or the vector link.

Focus return is only coded on crypto, and only after a panel that this button opened then closes (`templates/crypto.html.j2:483-488`): if `activeElement` is `body` or inside `#mmb-panel`, focus the Ask button. The widget's own `close` (`templates/mm_brain.js:3159-3169`) first tries `CFG.onClose` (unset on these pages) and then focuses `#mmb-launch`. That launcher is `display:none` on both pages. Whether `focus()` on a `display:none` node leaves `activeElement` on `body` — so the crypto observer can catch it — was not run in a browser. **UNVERIFIED.** Vector has no focus return. The crypto timeout path re-enables the button and does not call `focus()` (`:507`).

A script 404 is not counted as a live open: `loadBrain` treats `onerror` as `ok=false` and does not call `open`. The page surfaces that only by the 3 s timeout, not by the word 404, because the click handler does not receive the loader's `ok` flag. A 200 response that does not set `MMBrain.mounted` is the same `ok=false` (`theme.js:5233-5236`). The hidden boot pill itself shows no error string (`:5348-5351`).

`GET /api/brain/runs/{id}` and `.../stream` 404 when the run is missing, expired, cancelled, or not the caller's (`app/main.py:1594-1620`). `brain_runs.get` is owner-scoped; this census did not re-execute that lookup. The client does not paint `announceDone` for that 404 unless `threadTail` finds a persisted assistant row whose previous user row matches this question (`mm_brain.js:2724-2736`). Otherwise it shows the error card.

## Gaps against the T20 list

1. Shown source identity is not in the turn. Vector prints three `source_id`s; crypto prints `btc.decision/v1` and universe source lines. The turn's page label is `dashboard`.
2. Shown as-of is not in the turn. Hero, chip, and footer dates are render-time template variables.
3. Historical cursor is not separated from current state in the turn, because the cursor is not sent. The packet's only related split is quote `asof` versus injected `now`, and the tape line's `STALE — treat as last known, not current` prefix. The header remains `CURRENT DASHBOARD STATE`.
4. Unavailable cockpit metrics are honest in HTML (`—`, "Unavailable", "Not calculated"; a real `0%` target is not called unavailable — `templates/crypto.html.j2:444`). The brain does not see those states. A missing BTC/ETH quote is omitted from the tape rather than named unavailable.
5. Crypto announces failure (`role="status"`). Vector changes the button text with no status role. Neither names a 404.
6. Focus restore on close and on the timeout path is **UNVERIFIED** in a browser. Vector has no restore code.
7. No test in this lane drives a browser, sends a customer message, or calls `/api/brain/stream`.

## Fixture proposal

`crypto_page_context.v1`, carried beside `ai_context`, not stuffed into `ambient.page`.

```json
{
  "schema": "crypto_page_context.v1",
  "page": "vector",
  "shown": {
    "source_ids": {
      "price": "<chart_contract.meta.fields.price.source_id>",
      "risk": "<chart_contract.meta.fields.risk.source_id>",
      "allocation": "<chart_contract.meta.fields.allocation.source_id>"
    },
    "budget_source": "btc.decision/v1",
    "as_of": "<page as_of>",
    "observed_at": "<chart_contract.meta.observed_at or null>"
  },
  "current": {
    "as_of": "<page as_of>",
    "decision_as_of": "<allocation.decision_as_of or null>"
  },
  "cursor": {
    "kind": "time_machine",
    "as_of": "<#vtm-date or null>",
    "is_current": false
  }
}
```

Proof fields: each `shown.source_ids` value equals the string in the source table, not a display label. `shown.as_of` equals the hero/chip date. `cursor.as_of` differs from `current.as_of` whenever the scrubber is not on Now, and `cursor.is_current` is false. On crypto, `cursor.kind` is `none` and `cursor.as_of` is null — not a copy of `current.as_of`. A missing source id is null, not `""` and not `0`. `observed_at` stays null when the page says the availability clock is not asserted (`templates/vector.html.j2:448`).

`compile_envelope` will not preserve this block today. Top-level unknown keys become `ignored_fields` (`context_compiler.py:257-264`). Keys inside `ambient` other than the four echoed names are dropped with no flag.

## T20 test plan

No case sends a real customer message. No case uses a live provider.

1. Loopback static server. Stub `mm_brain.js` as HTTP 404. Click Ask on crypto and on vector. Assert the panel does not gain `open`, the crypto status is visible, vector `data-state` is `error`, and Overview / Assets / the crypto↔vector links still activate. Repeat with HTTP 200 whose body is an HTML 404 page and assert the same, because `onload` without `MMBrain.mounted` must not count as success (`theme.js:5233-5236`).
2. Keyboard: Tab to Ask, Enter, then Escape after a successful stub open. Assert focus is on the Ask button, not on `body` and not on the hidden `#mmb-launch`. Cover the timeout path the same way.
3. Once `crypto_page_context.v1` exists, compile a vector fixture whose `cursor.as_of` is `2022-11-09` and whose `current.as_of` is the page date. Assert both survive, they are not equal, and the effective read used for "what is on screen now" is `current`. A second fixture with the scrubber on Now has `cursor.is_current` true and equal dates.
4. Unauthorized: guest and `unknown` stay outside protected evidence (covered below). A run id owned by another user stays HTTP 404 (`app/main.py:1602`). Do not assert that by calling the live API.
5. Unavailable: a quote row with null price and null change stays out of the tape; a row with `changePct: 0` stays `0%`. An unavailable native fact renders `unavailable`, and the value `0` is not printed.

## What this lane ran

`python -m pytest tests/test_crypto_assistant_context.py -q -p no:cacheprovider -x` → `8 passed in 0.55s`.

The file pins functions that already exist: tape `basis` and `asof` stay on the quote clock while `now` only decides `stale_warn`; a null ETH row is omitted and an explicit zero is kept; a closed session is `last session's tape`, not live; `_render_fact` prints `source=` and `as_of=` and prints `unavailable` instead of a zero value; `plan_native_facts("what is the BTC price as of 2022-11-09")` is `None` while the same question without the date plans `BTC` / `market.price.last`; `compile_envelope` keeps `ambient.page` of `vector`/`crypto`, does not rewrite `captured_at` to `now`, marks a capture older than 900 s `stale` (`context_compiler.py:44`), and rejects a client-forged `effective_context`; `_ontology_evidence_allowed` and `_rotation_risk_grounding_digest` return false/empty for `""`, `unknown`, and `guest:not-a-customer`.

Absence searches: `MM_BRAIN_CFG` / `getAiContext` in the two page templates; `pathname` / `crypto.html` / `vector.html` in `templates/mm_brain.js`. Browser focus and a real loopback 404 response were not executed.
