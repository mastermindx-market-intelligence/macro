# Press public-source route — bounded static audit (supplied source only; nothing executed, nothing modified)

## Verdict

The route is genuinely planning-only and fails closed correctly (`plan_whitehouse_candidate` returns `allow_stage: False, allow_emit: False, publication_approved: False` unconditionally). It cannot produce a current story today for two independent reasons: **one implementation defect** (the validation context is 100% third-party, so it is structurally unfalsifiable-by-draft), and **one honest input gate** (no current source names a rendered-dossier company inside the window). The smallest safe step fixes the first without touching the second.

## Decisive finding F1 — the plan cannot pass its own validators, by construction

Every fact the planner emits is `tier: "third_party"` (`external_candidate.py`, claim loop and the derived-share fact). The context carries no first-party facts — no `engine_stat_facts`, no `mover_facts`. But:

- `validators.check_receipts` builds its pool as `[val for val, tier in fact_tier_index(slot) if tier == "first_party"]` → empty pool → 0 receipts; fails whenever `desk["min_anchored_receipts"] > 0` (and the context explicitly copies that desk value in).
- `validators.check_our_value` sets `tier = "first_party"` only when a number anchors a first-party value; with an empty first-party pool every numbered sentence is `"other"`, `our_words = 0`, share 0.0 < floor `our_value_min` (0.40). **Fails regardless of receipts minimum, draft quality, or source quality.**

`desk_planner._plan_brief` solved exactly this for chronicle slots: `facts = [lead] + stats + movers`, with the W1 comment "every slot carries the day's first-party engine context alongside the event so the our-value floor is reachable without padding." The external planner — which copies the same desk's `min_anchored_receipts`, `min_words`, `publication`, `byline` into its context, i.e. is built to be judged by the same validators — never got that side of the mix. `check_our_value`'s own honest note says the first_party/third_party split is what makes the number mean *our value* "once PRESS-FEEDS supplies external facts"; the planner never supplied the first-party half.

## Hardcoded example-specific assumptions blocking arbitrary-source qualification (F2/F3)

All in `external_candidate.py`:

- **F2 — `_value`: `words = {"eleven": Decimal(11)}`.** A single spelled-out numeral from the original example. Any other word-quantity in a future source ("half", "twenty") is rejected; "eleven" alone parses. The atom guard `(?<![\w.$])atom(?![\w.])` plus the `\$?` in the numeric grammar shows atoms like `"$500 million"` are supported — the word map is the only example-specific leak.
- **F3 — derived-fact prose is hardcoded:** `"Reviewed commitments represent approximately {share_text}% of the stated package."` This asserts a commitments/package interpretation the source may not make — the planner manufactures editorial framing. Combined with `derived_share` being mandatory in the exact `external_planning` key set and `_dollars` requiring B/M operands, the planner presumes *every* market event is a currency-magnitude package-share story. Percent- or count-based sources cannot qualify at all. Note: keeping `derived_share` mandatory is a deliberate gate — relaxing it is out of scope; the repair is to stop embedding the interpretation, not to widen the story class.

## First-party evidence: relevant or not?

- **Relevant as the desk's own read and the anchoring substrate:** `engine_stat_facts` (market state, GEX, breadth, fear/greed, risk radar) and `mover_facts` are current, dated, `_pit_filter`-ed, and lexicon-filtered. They are necessary for the our-value/receipts floors and add real relevance when a mover row matches a name the source itself cites.
- **Not sufficient as event evidence:** they say nothing about the external event. Event claims must remain third-party reviewed literals bound to the body (`literal in body`, atom regex guard). The honest story shape is: reviewed external event + our dated positioning read + rendered dossier links via `planner._allowed_links`.

## Honest gates that are *not* defects (do not touch)

- **Window/freshness:** `(now.date() - event_date).days > desk["window_days"]` anchors to the *event*, not publication — the inline comment "A later publication must not move the reviewed event into a newer window" is exactly why the Oct13 release recapping older events fails and why Oct8 is unrecoverable. Clocks additionally require `published ≤ now`, `observed ≥ published`, `event_date ≤ published.date()`. Never backdate — these checks already enforce it.
- **Ticker binding:** `reviewed_tickers` non-empty, `source_name in body`, `ticker in rendered_ticker_pages(site)`. Oct13 and Oct10 name no public companies → legitimate failure. Manufacturing tickers is prohibited and would fail here anyway.
- **Routing/canonicality:** `_CANONICAL_PATH` + `_AGGREGATE_ROUTES` + `_slug_id` + `FEEDS` identity — "routes fixed" is consistent; `research` is already admitted, so routing is not the Oct10 blocker.
- **Provenance:** exact `external_planning` key set, body ≤ 12 000 chars, triple body-hash pinning, `policy_file_sha256` bound read. literals must be transcribed from the retained feed-normalized body, not the rendered page.
- Minor observation, not urgent: `rights.get("publication_approval") is not False` (likewise `allow_stage`/`allow_emit`) accepts absent/None — "not explicitly forbidden" rather than "present." Harmless today only because the return hard-pins all three to False.

## Ranked next steps (by useful consumer outcome)

1. **F1 repair — add point-in-time first-party context to the external plan:** in `plan_whitehouse_candidate`, append `planner.engine_stat_facts(root, as_of=now.date())` + `planner.mover_facts(root, as_of=now.date())` to `validation_context["facts"]`, mirroring `_plan_brief`'s `facts = [lead] + stats + movers`. Both functions already apply `_pit_filter` and `_press_safe` internally. Controls: tier labels unchanged, gate set unchanged, output authority unchanged. **This is the smallest safe next implementation step** — it is the only purely-additive change that makes the route real for *any* future source.
2. **F3 repair — replace the hardcoded share prose with a body-anchored reviewed literal:** require a new exact-substring-of-body field containing both operand atoms and a ratio assertion; emit that literal as the fact text with the computed share as its value; keep the `share_text != derivation["percent"]` arithmetic equality unchanged. New required key = strictly tighter; stale qualifications fail closed. Failing sources now fail with an explicit reviewed-input error instead of printing manufactured framing.
3. **F2 cleanup — remove the `eleven` word map** (tightens the grammar) or replace with a complete closed word-numeral list. Tiny, hygiene-grade.
4. **Optional hardening:** require `publication_approval is True` in the rights check — editorial-gate semantics; coordinate with the editorial authority, zero consumer effect today.
5. **Non-implementation prerequisite (the real-world bottleneck):** a current, in-window White House document that names a rendered-dossier company. Monitor and qualify through the *repaired* planner when one appears. Until then the route correctly yields nothing; the ordinary brief desk remains the live non-earnings path, and the earnings route stays closed (`_SHA256_RECEIPT_RE` fail-closed in `_plan_brief`, credentials unavailable).

## Explicit non-actions

No loosening of `_CANONICAL_PATH`/`_AGGREGATE_ROUTES`, the window check, the exact key sets, or `reviewed_tickers` non-emptiness. No invented tickers, re-dated events, provider calls, rights assertions, or staging/emit authority — the return's three False flags stay False throughout every step above.
