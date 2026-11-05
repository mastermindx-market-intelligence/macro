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

## Separate follow-on consumers

The follow-on has a different source identity and delivery obligation. After its final
source passes the applicable checks, `bind_followon_adoption_probe.py --repo REPO
--source-commit FULL_SHA --destination NEW_BINDING_JSON` binds twelve direct files from
that commit. It does not substitute for the A1 seventeen-file or served-asset bindings.
The new destination must not exist. A symbolic revision or Git symlink is refused.

After lawful follow-on landing and normal installation, the original parent can run
`followon_adoption_probe.py --root INSTALLED_ROOT --binding BINDING_JSON
--producer EXACT_REGISTERED_PRODUCER_PATH --python INSTALLED_PYTHON`. Repeat `--producer`
for the actual planned change being assessed. This invokes only the existing T12
required-tier CLI and T5 source-findings CLI, without overrides of clocks or artifacts.
It records the twelve file hashes and installed HEAD before and after observation.
The installed HEAD may differ from the qualified branch SHA because of squash merge;
direct file hashes, not commit-name equality, are the stated identity check.

Both child streams are drained within16MiB/180seconds each. The probe reaps its own
process group on failure, retains output hashes/counts, and prints only allowlisted
contract summaries. It refuses wrong query identity, malformed contracts, observed
source changes, nonzero execution, special/symlink files and excessive output. Null
requirements remain null and all evaluation states remain `not_assessed`. It does not
export raw observations, source reports, errors or credentials. Test consumers are
local fakes only; they do not run the actual product or create production evidence.

This is a bounded observation of two real command consumers when actually run after
release. It is not full dependency closure, an atomic data snapshot, empirical model
acceptance, earned tiers, natural owner progression or a complete adoption verdict.
The rights-qualified QLedger packet, real Agent OS Discovery admission and subsequent
consumer use remain separate obligations; this probe cannot fabricate them. Its three
completion/adoption flags always remain false.

The twelve-file binding includes the native checker, executor, gateway, internal
log writer and `app/deploy/update.sh`. A stale updater or an older binding that omits
it is refused before either CLI runs. Create a new binding from the final qualified
follow-on revision; do not reuse the earlier eleven-file binding. This observes the
updater source in the installed checkout, not the separately installed updater copy
or loaded services. Compare that actual updater copy to the bound hash as well.
Native answers execute in `macro-api.service`; the operator reader executes
in `admin.service`. After the normal updater installs the qualified follow-on, verify
both actual service processes and the native API process's source directory/start time.
The admin PID alone cannot establish that the native caller loaded the new source.
The follow-on also adds `response_eval.py` to the existing exact API restart trigger:
its native caller caches that module after the first numeric request. Verify the normal
updater installed that qualified rule; the earlier pre-release observation correctly
reported that the old installed trigger did not cover checker-only changes. The two CLI invocations do not execute that numeric path. After release,
use the authenticated native numeric request and preserve its actual request ID.
Both gateway modes write that ID as the response-log row ID. Observe the corresponding
row through the existing operator log reader and its
`/api/mastermind_ai/response_logs` route after normal ingestion. Correlate the
request, rendered answer, native receipt and internal `native_numeric_verification`;
do not substitute a different successful row or infer a verdict from the public
receipt. A missing row or non-verified verdict remains an unproved obligation.
The internal verdict must remain absent from public responses and stream events.
The list route only reads its host's local ledger; it does not ingest R2 objects.
The weekly `brain-eval` workflow refreshes a ledger on its own Mac Studio runner,
which does not establish ingestion on the admin host. Verify the actual ingestion
path and host before relying on the list route. Keep sink publication and operator
consumption separate if that path is absent. Do not dispatch a model judge, force
the normal owner or reset source clocks to manufacture this evidence.
The existing operator “Refresh from R2” action ingests response rows without a
model judge. If used for the operator-consumption leg, record it as manual
ingestion; it cannot satisfy the separate natural QLedger owner-progression leg.
