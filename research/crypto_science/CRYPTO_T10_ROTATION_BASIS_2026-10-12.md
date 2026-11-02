# T10 rotation basis — 2026-10-12

Display-tier design and pure-function skeleton for one current-cohort descriptive view: each member's same-window USD price return minus Bitcoin's return on that same window. Predictive rotation, horizon search, and any rule that turns the spread into a position stay T14. This view has no score, no forecast, and no allocation. The word for a hole in the inputs is unavailable.

Live snapshot contents were not read. `data/` is omitted from this sparse worktree, and this lane does not run collectors. Dates below are the calendar rule, illustrated for a snapshot dated 2026-10-11. The live `as_of` is UNVERIFIED.

## Dated state that already exists

Class narration is `crypto.class_state/v1`, display tier (`contracts/crypto_class_state.schema.json:6-12`). `scripts/build_crypto.py:495-528` writes it. `as_of` is the latest date among total cap, BTC dominance, fear/greed, stablecoins, and BTC (`engine/crypto_market_state.py:282-287`). `universe_coverage` copies the snapshot `as_of`, listed count, requested count, the exclusion receipt, and the breadth receipt (`scripts/build_crypto.py:500-506`). Per-asset class fields are trend, risk, relative, and a coverage note (`scripts/build_crypto.py:520-527`), not returns.

Asset state is `crypto.asset_states/v1`, display tier, `states_only`, and it requires ETH and SOL (`contracts/crypto_asset_states.schema.json:6-21`). `engine/eth_state.py:176-198` builds only those two names. BTC is the relative benchmark, not an asset-state entry. Coverage there is an observation count against a 30-observation publish floor (`engine/eth_state.py:20`, `engine/eth_state.py:86-101`), not cohort coverage.

The current cohort is one cross-section from `load_universe_snapshot` (`engine/crypto_universe.py:52-150`). `as_of` is the max observation date (`engine/crypto_universe.py:95`). A file whose last date is older is `OLDER_SNAPSHOT` and does not re-enter (`engine/crypto_universe.py:100-101`). An unreadable latest row is not replaced with an older quote (`engine/crypto_universe.py:55-57`). Default requested size is 50 (`engine/crypto_universe.py:52`, called at `scripts/build_crypto.py:470`). Each kept row carries provider `change_24h`, `change_7d`, and `change_30d` (`engine/crypto_universe.py:128-137`).

`breadth_read` (`engine/crypto_universe.py:158-182`) is a different question: the share of listed names with `history_days >= 30` and a numeric reported 30-day change that is positive. A missing change shrinks `eligible` and is counted in `excluded`. The template already says that count is not a Bitcoin-relative measure (`templates/crypto.html.j2:347`). T10 does not reuse that denominator.

## Same-window returns that exist

| Sleeve | Recorded number | Usable as the cohort window? |
| --- | --- | --- |
| BTC, ETH, SOL, and any other name inside the snapshot | Provider `change_24h` / `change_7d` / `change_30d` on the single `as_of` (`engine/crypto_universe.py:128-137`) | Only `change_30d`, and only as the caller-stamped USD price percent for that snapshot. 24h and 7d are other windows. |
| ETH and SOL asset state | `change_30d_pct` is 30 index steps (`engine/eth_state.py:37-42`, `engine/eth_state.py:163`). `relative.change_90d_pct` is 90 index steps of the price ratio versus BTC (`engine/eth_state.py:45-52`, `engine/eth_state.py:168-169`) | No. Session counts on Coinbase, or Yahoo if Coinbase is empty (`engine/eth_state.py:176-188`), are not the snapshot window. Do not fill a missing snapshot return from them. |
| Class | `total_30d_pct` is 30 index steps of total cap (`engine/crypto_market_state.py:39-46`, `engine/crypto_market_state.py:147`). `dominance_30d` is a point change in BTC market-cap share, computed at `engine/crypto_market_state.py:148` and published at `engine/crypto_market_state.py:301`. The altseason meter folds a 90-step ETH/BTC ratio with that share change (`engine/crypto_market_state.py:259-266`) | No per-name cohort return. The dominance change is a share change. |

The snapshot percent is the trailing print stored by the universe collector. CoinGecko is requested with `vs_currency=usd` and `price_change_percentage` including `30d` (`collectors/crypto_misc.py:84-90`). CoinPaprika fallback asks `quotes=USD` and stores `percent_change_30d` (`collectors/crypto_misc.py:109-137`). The row is indexed by the collector's UTC date (`collectors/crypto_misc.py:146`) and saved as `change_30d_pct` (`collectors/crypto_misc.py:171-173`). That print is not a midnight-to-midnight close recomputed from a stored origin bar, and it is not the 30-session asset-state return. The basis names the window; it does not audit the provider clock.

BTC, ETH, and SOL also have deeper daily closes spliced in for sparklines only (`scripts/build_crypto.py:151-173`). That splice must not advance the snapshot date, and it must not replace `change_30d`.

## Fixed basis

Every comparison in one view carries this basis. The constants are enforced by `engine/crypto_rotation.py` (`HORIZON_DAYS`, `QUOTE_CURRENCY`, `WEIGHTING`, `BENCHMARK`). A call that disagrees raises. The function does not substitute another window.

| Field | Rule |
| --- | --- |
| `quote_currency` | `USD` |
| `horizon_days` | `30` calendar days |
| `cohort_snapshot_date` | The one `as_of` of `load_universe_snapshot` for this view |
| `origin_date` | `cohort_snapshot_date` minus 30 calendar days |
| `weighting` | `equal_member` |
| `benchmark` | `BTC` |
| `members` | Optional. When present, the declared cohort, in order. Names outside it are not comparisons. |

Illustration, not a live reading: snapshot `2026-10-11`, origin `2026-09-11`, horizon 30, quote USD, weight equal_member, benchmark BTC. `date(2026, 9, 11) + 30 days = date(2026, 10, 11)`.

Relative return is the arithmetic difference of the two USD price percents: asset minus BTC. It is not a price ratio, not a cap-weighted contribution, and not a share change. BTC versus BTC is 0 when BTC's own price return is usable. That 0 is not a rotation signal (`signal` stays false). No other name gets a relative number unless both legs are usable price returns. A missing BTC return stays unavailable. It is not zero.

`weighting` is declared so a later reader cannot treat the rows as cap-weighted. This skeleton does not emit a weighted sum or a breadth score.

## What cannot become an unqualified signal

Universe turnover. Membership is the explicit `members` list, which the builder must take from the snapshot rows after `OLDER_SNAPSHOT` and the other exclusion reasons (`engine/crypto_universe.py:100-114`). A row whose symbol is outside `members` is ignored, so a name that appears only in an older file or only as an extra input cannot create a comparison. `history_reset` set, including `SOURCE_IDENTITY_CHANGED` (`engine/crypto_universe.py:116-123`, `engine/crypto_universe.py:142`), is `identity_break`: the restarted series is not a full-window return. `history_days` present and below 30, or present and not an int, is `short_history`. Absent `history_days` is not treated as long history and is not treated as short history. The return still has to carry matching `window_origin`, `as_of`, `horizon_days`, `quote_currency`, and `weighting`.

Depeg, wrapper, supply. This repo does not classify those on the universe row. Search bound: `circulating_supply`, `max_supply`, and `total_supply` under `*.py` and `*.json`. The only hit is `max_supply * price` used to fill fully diluted valuation (`collectors/crypto_misc.py:127-129`). The skeleton does not infer WBTC, stETH, or a depeg from the ticker. A comparison is withheld when `instrument_kind` is `wrapper` or `depeg`, or when `wrapper`, `depeg`, or `supply_change` is true. Withheld rows stay in `comparisons` with `asset_return_pct` and `relative_return_pct` null, and they are absent from `signals`. They also sit in `coverage().missing`, so they lower coverage. They are not dropped from the declared list, and they are not dropped because the price move was large.

Unclassified identity. `instrument_kind` must be `spot` and `return_kind` must be `price`. Anything else, including a missing kind, is `unclassified` and unavailable. Assuming spot would be a guess.

Share change is not a return. `return_kind == "market_cap_share"` withholds the row even if `return_pct` is filled with the same number. `market_cap_share_change_pct` is copied only onto `market_cap_share_change_pct`. It is never assigned to `asset_return_pct` or `relative_return_pct`. `dominance_30d` (`engine/crypto_market_state.py:148`, `engine/crypto_market_state.py:301`, labeled market share at `templates/crypto.html.j2:309`) stays class context and is not an input here. A market-cap level change is not a price return either: `return_kind` other than `price` does not signal.

Unavailable members lower coverage and stay listed. `coverage(rows, cohort)` returns `declared` = length of the cohort, `available` = members with a usable fixed-window USD price return, and `missing` = every other declared symbol, in cohort order. A null return, an absent row, a withheld identity, a broken history, or a non-finite return (including bool and NaN) moves the symbol into `missing` and reduces `available / declared`. A negative price return stays available and still produces a relative number. Two usable rows whose fixed windows disagree raise `ValueError`. The function will not pick the better date or the better return. Duplicate symbols raise. A blank symbol raises.

A null does not block the rest of the view. Other members are still returned. Missing relatives are null, not 0, except BTC versus itself when BTC's price return is usable.

## Module

`engine/crypto_rotation.py` is stdlib only.

`relative_returns(rows, *, basis)` returns `basis`, `benchmark_return_pct`, `comparisons`, and `signals`. Each comparison carries `symbol`, the same `basis` object, `asset_return_pct`, `benchmark_return_pct`, `relative_return_pct`, `market_cap_share_change_pct`, `status` (`available`, `unavailable`, or `withheld`), `reason`, and `signal`. `signals` is the subset of comparison objects with `signal` true: non-benchmark names with a finite relative return. No threshold and no label.

`coverage(rows, cohort)` returns `declared`, `available`, `missing`, and `window` (the agreed origin and snapshot, or null when nobody is available).

Row fields the caller must stamp, and that this module will not invent: `symbol`, `as_of`, `window_origin`, `horizon_days`, `quote_currency`, `weighting`, `instrument_kind`, `return_kind`, `return_pct`. Optional: `history_days`, `history_reset`, `supply_change`, `depeg`, `wrapper`, `market_cap_share_change_pct`.

## Where the view mounts

Mount a descriptive block `#rotation-basis` after the universe-snapshot receipt ends (`templates/crypto.html.j2:365`) and before the Market Board section opens (`templates/crypto.html.j2:367`). The cohort date is the date already on that receipt (`templates/crypto.html.j2:339`, `data-universe-as-of`). The H1 prompt at `templates/crypto.html.j2:333` already separates market share, returns, and breadth, and it currently links to `#market-board`. This block is the return half of that prompt. It does not replace the positive-30-day breadth receipt at `templates/crypto.html.j2:347`. It does not mount on the H4 altseason meter (`templates/crypto.html.j2:404`), which mixes the 90-session ETH/BTC ratio with dominance. A desk-nav link, when the page is wired, belongs on the existing nav row (`templates/crypto.html.j2:293`).

The view model key belongs beside `breadth` in `scripts/build_crypto.py:561-591` (the `breadth` assignment is `scripts/build_crypto.py:581`). It must be the return value of `relative_returns` / `coverage`, not a remap of `change_30d` inside the template. Copy for a missing relative is unavailable, never `0`. Do not describe the block as a forecast or as authority.

## Not wired in this lane

No patch is applied to `crypto_universe.py`, `crypto_market_state.py`, `build_crypto.py`, or either template. A builder patch that copied `change_30d` into `return_pct` and defaulted `instrument_kind` to spot would present a provider trailing print as a classified fixed-origin price return. Those stamps are caller obligations. Until they exist, `relative_returns` marks the row unclassified or window-unavailable, lists it, and lowers coverage. The view can render that receipt. It must not invent the missing classification.

Out of scope for T10: T14 predictive rotation, a new options engine, a new aggregate risk or flow score, trade size, execution, and any signal whose source is an LLM.
