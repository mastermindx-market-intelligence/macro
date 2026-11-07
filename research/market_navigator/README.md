# Market Navigator foundation

A research-and-implementation package for a conditional market decision experience.
This is **not a shipped product, validated trading strategy or native Paper design**.
The initial source is a read-only consumer with every signal/trade/alert authority false.

## Start here

- [Master plan](MASTERPLAN.md): product outcome, reuse map, engine contracts,
  infrastructure, design, research boundaries and delivery waves.
- [Research protocol](RESEARCH_PROTOCOL.md): falsifiable questions, prior negative
  findings, data requirements and executed numerical/measurement audits.
- [Interactive design study](preview.html): desktop/mobile, English/Chinese,
  dark/light, unavailable-state behavior; explicitly not applied to Paper.
- [Integration contract](INTEGRATION_CONTRACT.md): clock semantics, source verification,
  product integration and save/restore boundaries.
- [Verification](VERIFICATION.md): exact checks and what each does not prove.
- [Continuation](CONTINUATION.md): source custody, unfinished obligations and next action.
- [Agent OS workstream](../../agentos/workstreams/WS-MARKET-NAVIGATOR.md).

## Implementation

`engine/market_navigator.py` is a pure deterministic compositor. It preserves input
identity, availability, units and horizon; evaluates explicit conditions; keeps
counterevidence; and consumes, rather than recomputes, the canonical market verdict.
A condition being met is not a forecast probability or trade permission.

`engine/market_navigator_sources.py` is the read-only SPY canary adapter to the existing
market-state loader/calendar. A real owner-issued receipt and application-bound
verifier are still required for production. The adapter never substitutes file mtime
for source availability and does not self-certify a production binding.

## Reproduce bounded checks

From the repository root:

```sh
python -m pytest tests/test_market_navigator.py tests/test_market_navigator_sources.py \
  tests/test_market_navigator_model_audit.py tests/test_market_navigator_daily_audit.py \
  tests/test_market_navigator_preview.py -q

PYTHONPATH=. python scripts/research/market_navigator_model_audit.py \
  --output research/market_navigator/MODEL_AUDIT.json

PYTHONPATH=. python scripts/research/market_navigator_browser_check.py \
  --output-dir research/market_navigator/evidence
```

The browser study requires an installed Playwright Chromium. It does not install a
browser, authenticate, connect market data, save to an account, or create alerts.
The optional daily-data audit has an explicit network flag; it is not run in CI.
Do not acquire, retain or redistribute additional data without the existing rights
and budget owners. No raw analyst corpus or uploaded chart is included.


## Additional implemented consumer seams

- `engine/market_navigator_memory.py`: lossless incumbent historical evidence and
  typed comparison; `scripts/research/market_navigator_memory_inspect.py` uses the
  existing trusted reader without creating a store.
- `engine/market_navigator_measurement.py`: VIX1D measurement-phase annotation and
  declared study-coverage gaps; no directional rule.
- `engine/market_navigator_research.py`: completeness/timing audit over the existing
  grounded extractor; no model call, corpus writer, trial or forecast score.
- `engine/market_navigator_response.py` and `templates/market_navigator_client.js`:
  request-bound closed projection and inert browser consumer; no endpoint or style.
- [Research update](RESEARCH_UPDATE_2026-10-22.md) and
  [client browser report](CLIENT_BROWSER_REPORT.json) record the bounded evidence.

No new consumer is activated in production by this package. Existing authentication,
source rights, native Paper design and real-path acceptance remain required.
