# `site/news/by_ticker.json` — per-ticker news-flow contract

Status: **LIVE ARTIFACT · CONTEXT-ONLY**. Written by `scripts/build_news.py` on
every news build, next to `financial.json`, and consumed by stock pages, the
Mastermind `news_flow` lens and the unified intelligence bundle. Nothing in it
is ever a scoring or trade input.

Companion docs: [ticker-news.md](ticker-news.md) (the low-latency R1 activation
runbook) and [ticker-news-editorial-quality.md](ticker-news-editorial-quality.md)
(the keep/drop quality rules). This file documents only the published JSON
contract of `by_ticker.json`.

## Top-level keys (existing)

| Key | Type | Meaning |
| --- | --- | --- |
| `schema` | `str` | `"news_flow.v1"` — unchanged. |
| `is_context_only` | `bool` | Always `True`; the artifact is narrative context, never a signal input. |
| `asof` | `str` | **The build date** (`YYYY-MM-DD`, UTC). This is *when the artifact was rendered*, not when the underlying news was fetched. |
| `tickers` | `dict[ticker → per-ticker object]` | The compact per-ticker index (below). |

## Per-ticker keys (existing)

| Key | Type | Meaning |
| --- | --- | --- |
| `n_recent` | `int` | Headlines kept for the ticker in this feed. |
| `sentiment_lean` | `str` | `"pos"` / `"neg"` / `"neutral"` — aggregate of Polygon per-ticker insights; context-only. |
| `n_pos` | `int` | Headlines with positive per-ticker sentiment. |
| `n_neg` | `int` | Headlines with negative per-ticker sentiment. |
| `sentiment_score` | `float` | Net polarity in `[-1, 1]` (`(pos−neg)/total`, `0.0` when none). |
| `sentiment_strength` | `float` | Volume-based magnitude `min(1, total/6)`, rounded to 2 dp. |
| `baskets` | `list[str]` | Thematic baskets the ticker belongs to. |
| `sectors` | `list[str]` | GICS sector ETFs the ticker belongs to. |
| `is_mag7` | `bool` | Whether the ticker is one of the Mag-7 megacaps. |
| `top` | `list[row]` | The top few headline rows (below). |
| `note` | `str` | Standing disclaimer: public-record news flow, informs narrative, never sizes alone. |

## `top[]` row keys (existing)

| Key | Type | Meaning |
| --- | --- | --- |
| `title` | `str` | Headline text. |
| `url` | `str` | Article URL. |
| `source` | `str` | Publisher / feed label. |
| `published` | `str` | `seendate` — the feed's seen/publish timestamp as stored on the headline row. |
| `sentiment` | `str \| null` | Per-ticker sentiment when the provider gave one, else the row sentiment. |
| `summary` | `str` | One-line summary (AI-compressed from the headline only), possibly empty. |

## Added fields (freshness honesty, additive and optional)

| Name | Type | Meaning | Where set |
| --- | --- | --- | --- |
| `source_asof` | `str \| null` | The `fetched_at` stamp of the financial feed **actually written** to `financial.json` this build — i.e. when the news was fetched. `null` only when the written feed itself carries no `fetched_at`; the value is never invented. | `scripts/build_news.py` `build()` |
| `source_asof_basis` | `str` | Always `"financial_news.fetched_at"` — names the clock `source_asof` comes from, so consumers can refuse payloads whose basis they do not understand. | `scripts/build_news.py` `build()` |
| `retained_from_previous_build` | `bool` | `True` only when the never-darken guard kept the previous build's `financial.json` (existing feed was fresh <36 h and strictly healthier) instead of writing the candidate feed. | `scripts/build_news.py` `build()` |
| `retained_reason` | `str` | Present **only when** `retained_from_previous_build` is `True`; omitted entirely on the fresh path. Identical to the `refresh_skipped_reason` stamped into `financial.json` by the same guard. | `scripts/build_news.py` `build()` |
| `top[].item_id` | `str` | The canonical R1 report key `source:source_item_id` — for Polygon/Massive rows `massive:<publisher-domain>:<polygon-id>`, read off the revision `engine.qbus_news_contract.normalize_massive_news` mints for the same payload. Present only where that contract accepts the payload; absent on any contract refusal and for every other provider. | `engine/financial_news.py` `_polygon_articles` → `mastermind_by_ticker` |
| `top[].published_utc` | `str` | The **provider's own publish clock** as an aware-UTC ISO string: Polygon `published_utc`, or the Finnhub epoch. Absent when the provider states none or states a timestamp with no timezone (a timezone is never assumed). | `engine/financial_news.py` `_polygon_articles` / `_finnhub_news` → `mastermind_by_ticker` |

## Reading rules (plain statements)

- `asof` is the **build date**; `source_asof` is the **fetch stamp of the feed
  written**. A keyless re-render that the never-darken guard parks on the
  previous build's feed keeps an old `source_asof` under a new `asof` — that is
  the honest state, and `retained_from_previous_build: true` is the flag for it.
- `top[].item_id` is the R1 report key `source:source_item_id` (Polygon/Massive
  rows only, and only where `normalize_massive_news` accepts the payload — so
  presence means the contract would mint that same identity). It is **NOT** the qbus `item_id` column — that column is the
  `_id` event hash minted by `news_common.event_id(title, domain)`. The two
  namespaces never join; treat any join between them as a defect.
- `published_utc` is the provider clock (Polygon `published_utc`, Finnhub
  epoch). It is absent when unknown; do not fall back to `published`
  (`seendate`) as if it were provider-stated.
- Quiver, GDELT, RSS and AI-feed rows carry **neither** `item_id` nor
  `published_utc`: those providers have no canonical R1 namespace and minting
  one would create a new identity namespace.
- Every added field is optional-additive: consumers must tolerate its absence,
  and no existing key's meaning changed.
