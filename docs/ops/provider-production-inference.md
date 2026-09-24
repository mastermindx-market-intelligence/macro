# Metered Production Inference — MiniMax First Canary

## Purpose

Qualify the merged `minimax_payg_api` transport without enabling normal traffic
or borrowing Claude/Codex developer subscriptions. The checked-in production modes
remain `enabled=false`; GLM stays unqualified.

## Credential custody

The existing `.github/workflows/deploy-api-secrets.yml` remains the sole VPS
secret-delivery owner. It has three explicit scopes:

- `developer` (default): reconcile the existing OAuth/developer estate only;
- `production`: reconcile only `MINIMAX_API_KEY` / `ZAI_API_KEY`;
- `all`: perform both independently.

A `production` run never reads, strips, or rewrites the Claude/Codex OAuth pool and
never touches the admin-service environment. Add repository secret
`MINIMAX_API_KEY` for the standard MiniMax pay-as-you-go API key. `ZAI_API_KEY`
should remain absent until the GLM request contract is separately qualified.

Provision or refresh production credentials without invoking the provider:

```bash
gh workflow run deploy-api-secrets.yml \
  -f scope=production \
  -f run_minimax_canary=false
```

Rollback is the same owner and the same scope: remove the repository production key,
then rerun `scope=production` with the canary false. The workflow removes the stale
VPS production-key line while preserving every developer/OAuth line.

## Bounded canary

After the canary source and Provider Economics predecessor are protected, run the
production scope with the one-shot canary explicitly armed:

```bash
gh workflow run deploy-api-secrets.yml \
  -f scope=production \
  -f run_minimax_canary=true
```

The workflow verifies the MiniMax repository secret is present, syncs only the
production credential names, restarts `macro-api`, then runs the canary from the
deployed `/opt/macro` checkout with `/opt/macro/.venv/bin/python`.
Mutable provider-health and cost telemetry is redirected to
`AI_COSTS_STATE_ROOT=/var/lib/macro-api`; the Git checkout must remain clean.

The CLI itself still requires both `--execute` and
`MM_PROVIDER_CANARY_MODE=minimax_payg_api`. It refuses before provider I/O when
canonical MiniMax pricing is unavailable.

Acceptance requires the secret-free JSON receipt to report:

- `schema=mastermind.provider_production_canary.v1`;
- `accepted=true` and `acceptance_reason=accepted`;
- exact `minimax_payg_api` / `MiniMax-M3` / `prod_api:minimax` identity;
- `fallback=none`, `response_match=true`, `request_count_ceiling=1`;
- exact token counts plus `price_state=known` from the canonical pricing owner;
- `telemetry_lane=provider_production_modes_canary`;
- `source_mode_enabled=false`, `qualification_effect=false`, and
  `production_activation=false`.

The receipt never contains model response text or credential material. Price truth is
a pre-call gate, so an unpriced canary spends zero provider tokens. A successful call
records `effect_state=EFFECT_CONFIRMED`; a timeout/connection/ambiguous transport
failure records `EFFECT_UNKNOWN`. Automatic retry and same-operation replay are
always false. **Do not rerun an EFFECT_UNKNOWN canary.** Reconcile that exact provider
attempt/telemetry first.

A passing canary qualifies only this bounded transport. It does not enable the
checked-in production mode, does not qualify GLM, and does not route AI Brief,
Mastermind AI, Cortex, self-heal, or any other consumer. Those are later reviewed
consumer migrations.
