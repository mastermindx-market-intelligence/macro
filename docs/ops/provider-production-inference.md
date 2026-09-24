# Metered Production Inference — MiniMax First Canary

## Purpose

Qualify the merged `minimax_payg_api` transport without enabling normal traffic
or borrowing Claude/Codex developer subscriptions. The checked-in production modes
remain `enabled=false`; GLM stays unqualified.

## Credential custody

The existing `.github/workflows/deploy-api-secrets.yml` remains the sole VPS
secret-delivery owner. Add the repository secret `MINIMAX_API_KEY` for the standard
MiniMax pay-as-you-go API key, then run that existing workflow. `ZAI_API_KEY` is
optional and should remain absent until the GLM request contract is separately
qualified. Both names are delivered only to `/etc/macro-api.env`; the admin service
receives neither.

The workflow strips the two production-key names before appending current repository
secret values. Removing a repository secret and rerunning the same workflow is the
rollback; developer/OAuth keys are unaffected.

## Bounded canary

Run the canary only from the approved VPS operator environment after the MiniMax
PAYG key is present. The process requires both `--execute` and
`MM_PROVIDER_CANARY_MODE=minimax_payg_api`:

```bash
MM_PROVIDER_CANARY_MODE=minimax_payg_api \
  python -m engine.provider_production_modes --canary --execute
```

Acceptance requires the secret-free JSON receipt to report:

- `schema=mastermind.provider_production_canary.v1`;
- `accepted=true` and `acceptance_reason=accepted`;
- exact `minimax_payg_api` / `MiniMax-M3` / `prod_api:minimax` identity;
- `fallback=none`, `response_match=true`, `request_count_ceiling=1`;
- exact token counts plus `price_state=known` from the canonical pricing owner;
- `telemetry_lane=provider_production_modes_canary`;
- `source_mode_enabled=false`, `qualification_effect=false`, and
  `production_activation=false`.

The receipt never contains model response text or credential material. A transport
success with unknown pricing is explicitly rejected as `pricing_unknown`: it proves
reachability, not economical activation readiness. A passing canary qualifies only
this bounded transport; consumer migration and normal traffic activation require a
later reviewed wave.
