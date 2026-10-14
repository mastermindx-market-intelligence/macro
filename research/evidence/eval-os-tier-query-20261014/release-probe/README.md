# Eval OS final-source release verification tools

These tools bind expected bytes. They do not decide source qualification or claim deployment.

The incumbent merge controller alone refreshes and merges A1 PR6651. After its current checks qualify the actual candidate, record that complete commit SHA as `EVAL_QUALIFIED_A1_SHA`. Do not substitute the separate follow-on or an arbitrary current-main revision. Use new output directories for each binding so earlier evidence remains intact.

From a Macro repository containing the qualified objects:

```sh
python3 research/evidence/eval-os-tier-query-20261014/release-probe/bind_production_identity_probe.py --repo . --source-commit "$EVAL_QUALIFIED_A1_SHA" --destination "$EVAL_NEW_PROBE_DIRECTORY"
python3 research/evidence/eval-os-tier-query-20261014/release-probe/project_served_asset_identity.py --repo . --source-commit "$EVAL_QUALIFIED_A1_SHA" --destination "$EVAL_NEW_ASSET_DIRECTORY"
```

The first tool rebinds the existing read-only 17-file production probe. The second reads seven regular Git blobs (at most 4 MiB each) and reproduces the actual public bundle versions, pure theme-token projection and server HTML rewrite. It never imports the server. Reviewed projector bytes and server AST contracts are pinned; a change requires source review before updating those pins. A symbolic revision or existing output destination is refused. Expected hashes are not an observation of served bytes.

The asset-projector selfcheck reproduces all four assets and rewritten HTML for original A1 `05a75a4131f5e695a1d31616ac9e2ecca6059c67` and follow-on `f095dfe19364e8ba3f3d9251c9765a6491e996d4`, and verifies refusal before writing for a symbolic revision, existing output and unreviewed rewrite contract. These are offline checks only.

After actual A1 landing, verify the normal updater, installation identity and admin process with the bound read-only probe. Independently compare observed public response bodies against the asset manifest. Then bind authenticated overview/detail API responses to rendered DOM, required dark/light and EN/ZH states at desktop/mobile widths, performance/degraded states, and genuine subsequent normal owner progression. Preserve content-generation clocks, null/unknown results and unresolved effects. Neither tool launches a producer, writes a grade, changes a clock, restarts a service, handles credentials or grants acceptance.

The canonical execution frontier remains `/Volumes/Mastermind/evidence/intelligence-evaluation-os-20261012-01a1333d/EXECUTION_FRONTIER.md`. It records exact source, installed/served observations, original Fabric operations and remaining gates. All completion flags remain false until the assigned evidence is actually established.
