# P2 source-interface audit — sector/theme/name regime inputs (2026-10-30)

STATUS: **SOURCE-BASED READ-ONLY AUDIT / NOT ADMITTED FOR LIVE CUSTOMER USE**.
Owner programme `WS:LEADERSHIP-ROTATION-INTELLIGENCE` with
`WS:GMI-THEME-GRAPH` responsible for graph identity, historical membership,
rights and ThemeState. Source census of Macro
`fbe51cd8f734851409104d35d65d724ed5d78c38`, plus P1/P1a Draft
#10213 on `sol/sector-theme-factor-intelligence-20261030`; protected
Mastermind `bb85b429f2ffffd38408080ce4df7d6378c34100`.
No live stores/collectors/market data/accounts/hosts were read or modified
by this document. Source inspection is **not** a rights or runtime receipt.

## Source owner and what it ACTUALLY establishes

| Existing source | Usable factual content | Not proven; exact gate |
| --- | --- | --- |
| `engine/leadership_rotation_context.py` | Pure `relative_wealth`, `breadth`, `breadth_change`, coverage bounds, and as-known/cohort guards. | No original raw quotes, member rights, vendor availability or issuer weights. |
| `engine/basket_membership_pit.py` | Append-only, keep-first per (snapshot_date,basket_id,ticker); `members_asof` explicitly returns `pit`, basis and source_shape. US suite `baskets` is 49 hand-curated baskets, advanced by US nightly; CN suites by Asia lane. | PIT history is **forward-only**; before first snapshot the reader can return **CURRENT** roster marked `pit=False`. Existing historical membership DOES NOT establish original intraday knowledge, universe completeness or customer display rights. Do NOT use `pit=False` fallback for PIT studies. |
| `engine/theme_graph/theme_state_owner_readers.py` | Consistency receipts reread incumbents: basket membership, Graph identity and rights; no new identity store. | Eligibility NOT emitted; date-only membership clock cannot prove same-day or intraday known-at; production custody/authentication explicitly owed; selected role receipts are not end-to-end ThemeState admission. |
| `engine/theme_graph/micro_rs_proxy_display.py` | Display-tier ancestor-theme ETF/basket instrument projection for sub-/micro-themes. | Explicit law disallows direct sub/micro `EXPRESSES/MEMBER_OF`; no direct true ticker member count, price return, RS, weights or breadth. Mark `proxy_not_micro_membership`, never promote inferred child stock population. |
| `engine/theme_graph/hierarchy_breadth_display.py` | Graph node descendants and taxonomy adjacency, counts of nodes. | Node-count breadth is not advancing/declining stock breadth and cannot be used in its numerator. |
| `engine/group_flow.py` | Incumbent display-tier `fingerprint_at` family with causal trailing RS acceleration (`accel_z`), fraction above 50DMA/broadening, cohesion, persistence. Its default windows include 20d RS, 50d MA, 40d pairwise correlation, 20d persistence and trailing 252d z-reference. | Existing flow-stage 'EMERGING/CONFIRMED/COOLING' descriptive only; Phase-0 predictive edge unresolved. The doc calls this a flow *fingerprint*, NOT measured institutional money flow. Underlying close tape is source/basis/rights qualified separately. Reuse its measurements through approved adapter, no second computation/score. |
| `engine/theme_scoring.py` | Existing theme score/labels/entry verbs and transparent components. The code records earlier phase-0 approximately zero forward IC for some theme momentum and vol-hole legs. | Do not silently replace weights/gates or claim score predicts future returns. Current-roster hindsight-curated baskets are not independent PIT historical themes. |
| `engine/sector_cycles.py` | 11 sector ETF cycle phases/oscillator, own price history and SPY RS; its 'next-turn' timing is based on median historical half-cycle. | Sector ETF price is not proof of constituent ticker participation. The median half-cycle date is NOT a calibrated turning-point probability. |
| `engine/live_breadth.py` | Existing display-tier market-wide live/delayed participation with source age and universe. | A market-wide aggregate cannot be redistributed as any particular theme's members; a 15-min delayed feed cannot be labeled instantaneous. |
| `engine/regime_vector.py`, `engine/regime_hmm.py`, `engine/rates_command_outlook.py` | Macro owner context, historical soft quadrants (HMM), nine overlapping path readings. | Full-sample HMM smoothed history uses future data; never feature-engineer causal forecasts from it. GRI path readings are not probabilities or independent votes. |

## P2 exact adapter data contract (new read-only consumer, NOT a store)

At one explicit, authorized `decision_cutoff`, an existing source owner must
supply for **each member observation**:
- canonical identity and issuer `member_id`/mapping revision; group node and
  hierarchy tier with verified parent/child relationship;
- membership history `snapshot_date`, `effective_at`, **original available_at**
  and PIT boolean, source_shape, explicit correction/revision, eligible `N`;
- market period start/end and RTH/overnight/session basis, exchange calendar,
  adjustment/close price basis, actual original observation/availability time;
- source-use/rights verdict for the exact display/research purpose, entitlements
  and execution generation, along with source/data revision hashes;
- contemporaneous finite return fractions, same-bar-basis close and
  MA20/50/200/previous50, if available. A basis mismatch nulls only the
  affected technical metric, never silently recomputes it from a different
  adjustment or interval.
- lagged complete issuer weights only if weighted group/HHI features are
  intended, and explicit source qualifications for 'credit OAS' daily vintage
  vs liquid intraday traded ETF **proxies**.

`project_factor_frame` and `compose_regime_fingerprint` consume those
**after** admission by the native rights/identity owner. Their synthetic
`decision_at` fields are not authenticated original receipts; at P1a the
returned `eligible_for_customer_publication` stays **false**, and most
cross-asset/extension/acceleration legs remain `unmeasured`. No new collector,
topology writer, graph resolution override, scheduler, cache, publication plane,
LLM interpolation, data retention or capital-policy authority is permitted.

## Eligibility logic for the FIRST real vertical

Pick **one permitted US curated theme with a verified current known roster**,
not a micro-theme ancestor proxy. Only claim `CURRENT_ROSTER` display mode
if source rights permit and original intraday knowledge is unprovable.
If the owner can supply fully qualified historical PIT membership and quote
observation/availability at decision cutoff, enable `PIT_AS_KNOWN` for
that specific cohort/period, never the entire backfilled history by default.

Fail closed and expose explicit reasons when: `pit=False` before first
snapshot; membership known after snapshot; ambiguous/merged issuer; wrong
suite/source_shape; incomplete population; stale vendor bar; rights/use withheld;
price basis disagreement; no quote first-seen; absent parent benchmark or
lagged weights; source correction altered historical inputs. These must
be independent UI states, not generic 0/50 'neutral' scores.

P2 acceptance must include actual **same-source producer** -> qualified owner
receipt -> P1 factor frame -> P1a read-only fingerprint on a reproducible
real-market date, then an authorized signed-in Macro/Terminal consumer. Unit
tests, engine availability and sector ETF charts are not this proof.
Without qualified historical vintages, the retrospective analog/forecast
branch remains `NOT_EXECUTABLE` while descriptive present-day work can proceed.

## Exact anti-duplication / next step

Consume `group_flow`'s already-owned acceleration/broadening/cohesion and
the existing `basket_membership_pit.members_asof` with native GMI identity/rights
rather than build a second source. Verify the real owner field names and active
release permissions at implementation time; this audit is source-only.
No source branch head, owner, Executive Job, worker START, or actual entitlement
is established by this note. Frozen W1–W5 sector, GMI D2C/D2D, Granular Regime
Intelligence and Leadership W6 science results are not redone.
