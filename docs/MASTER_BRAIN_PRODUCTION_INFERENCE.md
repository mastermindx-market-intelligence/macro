# Master Brain production inference selection

Status: source implementation, disabled by default. Programme: [Mastermind #983](https://github.com/mastermindx-market-intelligence/Mastermind/issues/983).

## What this connects

`engine.master_brain.synthesize` can explicitly use the existing `engine.provider_production_modes.call_mode` owner for upstream AI Brief synthesis. The owner retains qualification, credentials, pinned destinations/models, health records and usage accounting.

This does not connect the native Fabric subscription pools or replace the web Brain gateway's streaming/tool contract. MiniMax PAYG and GLM PaaS are distinct products and billing identities from subscription accounts.

## Configuration contract

In the server-owned configuration read by `lib.config`:

```yaml
master_brain:
  production_mode: minimax_payg_api
  max_tokens: 4000
```

Omission of `production_mode` preserves the existing legacy route. Presence selects the exclusive production route: empty, null, malformed and unknown selections fail closed. The output budget must be an integer from 1 to 32768.

Selection does not enable a mode. `config/provider_production_modes.v1.json` remains authoritative and both modes ship disabled. The GLM profile additionally remains unqualified pending its required canary. This change installs no credentials and does not grant a provider profile, pool claim or production entitlement.

For the separate Mastermind Brain dispatcher, the paired consumer selects `BOT_LLM_BACKEND=production_mode` and `BOT_LLM_PRODUCTION_MODE=minimax_payg_api`. Its compatible owner must include this PR's MiniMax `max_retries=0` transport fix. [Full cross-repository implementation notes](https://github.com/mastermindx-market-intelligence/Mastermind/blob/389efa1f0f0d61f7bdfeda077e112029563ed6ea/docs/brain/production_inference.md).

## Failure, accounting and cache behavior

A selected production request reaches the owner once. It does not enter the legacy subscription waterfall, custom endpoint, empty-reply loop, or TypeError signature retry. A timeout may follow dispatch; it is not permission to replay elsewhere.

The actual receipt supplies model/provider attribution. The owner alone records provider health and usage. A cache hit creates no new usage charge.

Production cache identity includes mode, resolved provider/model, output budget and both existing prompts. It never aliases the legacy model cache. Eligibility is resolved before cache lookup, so disabled, unqualified or unconfigured modes cannot appear healthy by returning old output. A result whose receipt identity differs from the identity resolved before dispatch is not written under that cache key.

JSON parsing and style validation remain in the synthesis consumer. A style rewrite after a valid draft is a distinct intentional call through the same selected mode and receives its own accounting. If that rewrite fails, the original draft and its style flags are retained. Invalid initial JSON or a failed initial request is not automatically replayed.

## Qualification

From this Macro checkout:

```sh
PYTHONPATH=. python -m unittest discover -s tests -p test_master_brain_production_composition.py -v
```

Fourteen local composition tests passed through actual synthesis, the owner and temporary incumbent ledgers; only the SDK/network boundary is substituted during normal execution tests. The suite is also registered in the existing `unrun-brain-desks` packed CI job. The paired Mastermind CIO composition has fourteen additional passing local tests and a required composition step within existing Mastermind CI shard zero, pinned to compatible Macro source.

These results are source proof. They do not establish deployed configuration, live credentials, native shared admission, production inference, browser behavior or release acceptance. Full Fabric integration and retirement of existing bypasses remain open in the parent programme.
