# Mastermind AI Fast Harness — latency, tool visibility and truthful usage

Date: 2026-09-19. Owner: Sol / `macro-mastermind-ai`. Procedure pin:
Mastermind protected `733389933e605e508517732fb6c69b6c18b7fef6`,
Skillpack 1.0.1/bootstrap1.

Status: architecture/performance ruling and measured diagnosis. **No gateway implementation,
provider/model swap or production release is made by this document.**

## 1. User outcome

Fast should feel like an intelligent analyst, not a slow retrieval wrapper. For a question whose
evidence family is recognizable, the model should receive the smallest authorized tool surface that
can answer and challenge the question. Ambiguous questions retain the full capability set. The user
should not pay one expensive model round merely to decide which obvious baseline evidence to inspect.

This is not a new router. The existing `ask_brain._classify_question`, gateway entitlement/schema
builder, dispatcher, Analyst Doctrine and run lifecycle remain the owners. The change is progressive
disclosure and better use of those owners.

## 2. Real production evidence

Production health during this diagnosis reported deployed commit/checkout `dfcab92360`.

### Clean supplied valuation case

Real `/api/brain/stream` Fast run
`b0f915de059046e1a46d698d7c609d40`, reported model `deepseek-v4-pro`, no tools.

Supplied EPS 5→6 and multiple 20x→15x. The answer correctly derived price 100→90 and return −10%,
explained earnings growth versus multiple compression, gave plausible discount-rate/earnings-quality
mechanisms and named forward revisions versus rates as discriminating evidence.

Observed receipt: one model round ~18.8s; total ~18.96s; final-response usage reported
12,440 input / 1,160 output tokens. This proves the Fast model can perform useful financial reasoning
on a clean task. It does not prove all financial tasks work; the deployed prompt still contains the
broad “hypotheticals — decline” instruction and an earlier production task was refused.

### Current NVDA explanation case

Real Fast SSE run `eeaae8751b774e6d9dbef5555b123699`, reported `deepseek-v4-pro`.
The initial client socket timed out at 60s, but the same durable server run was reconciled through
the existing run-status/resume API: `done=true`, `cancelled=false`, `truncated=false`.

The model called `get_market_events` (~85ms) and `get_symbol_context` (~164ms), then produced two
competing explanations with supporting and contradicting observations. It rejected after-close and
low-grade items as causes and named the missing intraday/sector-relative evidence instead of claiming
certainty.

Observed latency: model rounds ~30.998s + ~33.558s; tool execution under 250ms combined; first visible
answer ~54.98s; total 66.127s. Tool latency is not the dominant bottleneck.

## 3. Current prompt/tool payload

Measured from the deployed-generation source shape on Macro page:

- base Brain system prompt: 6,862 chars;
- Fast assembled system prompt before analyst block: 9,058 chars;
- routed Fast analyst doctrine for a current-move question: ~7,057 chars;
- **54 disclosed Macro tools: ~34,966 compact-JSON chars**;
- Terminal: 62 tools / ~41,082 chars.

The top schema alone, `search_research`, is ~2,420 chars. Many unrelated domains travel on every
Fast question even when the existing classifier already knows a much narrower seed family.

The system prompt and full tool list already carry provider cache breakpoints, and the last user
message is also cache-marked. Caching helps repeated-prefix economics but does not remove first-round
schema parsing/reasoning. The NVDA second model round was not observably faster.

## 4. Usage-accounting defect

Both nonstreaming and streaming loops currently overwrite `usage_dict` from the **last/final model
response**. Earlier tool-selection/model rounds are not summed into the returned turn usage. Cache
creation/read fields are also not consistently surfaced by the streaming final path.

Therefore a turn receipt such as NVDA's 1,880 input tokens is not a truthful total-turn token count.
Do not use current `done.usage` to compare total token cost across one-round versus multi-round
investigations until this is repaired.

The existing usage/cost owners remain authoritative; repair their accumulation. Do not create a new
cost ledger.

## 5. Existing classifier is advisory, not visibility enforcement

`ask_brain._classify_question` returns a budget and seed tool list. Gateway
`_seed_tool_plan` turns that into prompt advice only. `_all_brain_tool_schemas` still discloses
all authorized tools.

The classifier also carries historical ordering gaps:
- a clean supplied valuation question defaults to `read_world_state`;
- “why did NVDA move?” seeds `query_spine/read_world_state/read_kernel` while the successful model
  actually chose `get_market_events/get_symbol_context`;
- “options setup for NVDA” can hit the generic “setup for” branch before options-specific routing;
- portfolio analysis defaults to world state rather than portfolio-first evidence.

Do not enforce visibility directly from the current seed tuple without closing these regressions.

## 6. First implementation: progressive tool visibility

Extend the **existing classifier owner** with an internal task profile; do not create a second router,
planner database or model call. The gateway first builds the full entitled schema exactly as today,
then filters **only model visibility** to the profile's permitted tool names. Dispatcher authorization
remains independent and fail-closed.

Detected profiles receive bounded relevant families. Ambiguous/unknown queries retain the current
full schema until coverage is proven.

Measured candidate profiles against current 54-tool / 34,966-char Macro baseline:

| Profile | Candidate tools | Schema chars | Reduction |
|---|---:|---:|---:|
| current single-name | 10 | 6,130 | 82.5% |
| macro/rates | 6 | 3,898 | 88.9% |
| options single-name | 7 | 3,518 | 89.9% |
| portfolio | 7 | 3,778 | 89.2% |
| theme | 9 | 5,505 | 84.3% |

These are static payload estimates, **not latency claims**.

Initial family contents:

- current single-name: market events, symbol context/quote/intel, company intelligence,
  fundamentals/earnings/house view, spine, contradictions;
- macro/rates: world state, curve detail, mechanism pathways, contradictions, market events,
  liquidity plumbing;
- options single-name: quote/context/events + existing options entry/context/confluence/contradiction;
- portfolio: portfolio brief, watchlist, world state, factor state/conflicts, events, contradictions;
- theme: existing theme tools + events + world state;
- supplied financial scenario after #7217 integration: `calculate_financial_bridge` plus no
  current-market tools unless the question separately requests current evidence.

Entitlement/page/Research/Terminal gating always occurs before/with visibility. A profile cannot
resurrect a tool the existing schema builder withheld.

The unknown-tool recovery path must disclose only the tools offered for **that turn**, not the full
registry, otherwise one hallucinated call defeats progressive disclosure.

## 7. Grounding scope

Do not prepend today's entire market grounding to a self-contained supplied scenario merely because
Fast historically needed defensive grounding. The task profile should distinguish:

- `self_contained`: no ambient market digest;
- `market_current`: market packet;
- `single_name_current`: market + symbol grounding;
- `portfolio_current`: portfolio + market context;
- `ambiguous`: current behavior until qualified.

This is context selection, not removal of evidence the task needs.

## 8. Second implementation only if needed: deterministic baseline prefetch

Do **not** start here. First measure progressive disclosure on real SSE canaries.

If common current questions still spend an expensive first model round choosing obvious reads,
extend the same existing classifier/gateway path to prefetch only deterministic baseline evidence
whose parameters the server already resolves safely.

Candidate examples:
- current single-name move: `get_market_events` + `get_symbol_context` concurrently;
- rates question: `read_world_state` + `get_curve_detail`;
- portfolio question: own `get_portfolio_brief` + world state when authorized.

The prefetched results must use existing dispatcher/result/provenance semantics and remain visible in
turn evidence. The model still owns extra discriminating tool requests. Never prefetch a write,
private memory search, public-web query or source with unresolved parameters merely to save a round.

## 9. Truthful cumulative usage

Accumulate usage for **every** model round and final synthesis under the existing turn usage owner:
input, output, cache creation/read and per-provider/model identity where already available. Cost and
quota settlement must consume the same accumulated values or explicitly retain their existing policy
with a named distinction.

Tests must prove a two-round turn reports the sum of both model rounds and that cached tokens do not
disappear from observability merely because the final response is small.

## 10. Acceptance

Static/contract:
1. every currently authorized tool remains reachable in at least one qualified profile or the
   ambiguous fallback;
2. entitlement/page/Research boundaries remain unchanged;
3. current classifier regressions above are test-first repaired;
4. known profiles reduce schema bytes materially while ambiguous remains byte-equivalent to current;
5. unknown-tool recovery cannot disclose hidden turn tools;
6. supplied scenarios do not receive unrelated market grounding;
7. cumulative multi-round usage is truthful.

Real SSE bakeoff on frozen prompts:
- clean supplied financial scenario;
- current single-name move/catalyst;
- rates/curve;
- options single-name;
- portfolio;
- theme;
- ambiguous control;
with English and Chinese representatives.

Compare exact model/provider and evidence conditions before/after. Measure time to first meaningful
answer, total time, model rounds, tool execution time, full cumulative input/output/cache tokens,
tool calls, answer correctness, unsupported claims and missing-evidence honesty.

The first release target is **quality noninferiority plus a material reduction in tool-schema bytes
and observed latency on the qualified profiles**. Do not claim a latency win from static payload
reduction alone.

## 10A. 2026-09-19 anonymous Fast/Pro bakeoff gate

A fresh matched-case attempt used the same supplied valuation/thesis question on the
current production endpoint while health reported process commit `dfcab92360` and
checkout `7babc6c17d`.

Fast request: HTTP524 after ~15.47s with an empty body and no returned run identity.
Backend effect/completion is unknown. It was **not retried** and is not counted as a
model-quality failure or latency sample.

Distinct Pro arm: HTTP402 after ~0.55s with
`{"quota_exhausted":true,"lane":"pro","tier":"guest"}`. No Pro model, route, usage
or answer was returned. This is an entitlement/identity gate, not evidence about
GPT-5.6 Sol quality.

Therefore the anonymous endpoint cannot currently produce a valid matched Fast/Pro
comparison. Do not infer DeepSeek superiority/inferiority from these two outcomes and
do not reroute the Fast 524 through another account. A valid model bakeoff requires a
server-authenticated entitled customer identity (or an existing sanctioned evaluation
harness) and exact served-model receipts for both arms. No credential was read or
reused by this observation.

## 11. Current ownership / sequence

Do not edit shared gateway/classifier paths while the current calculator/scope/Research/vision source
writers remain held. PR #7217 owns the incumbent calculator integration; #7152 scope; #7100 bounded
Research; #7144 provider/vision; #7374 public research.

This latency wave may keep collecting read-only evidence and tests/specs. Start source implementation
only after current writer/collision reconciliation establishes one lawful carrier for the relevant
shared paths.

The purpose is not “make DeepSeek smarter.” Production evidence already shows it can reason. The
purpose is to make Mastermind consistently give the model the right evidence and tools with far less
selection overhead, while measuring the full turn honestly.