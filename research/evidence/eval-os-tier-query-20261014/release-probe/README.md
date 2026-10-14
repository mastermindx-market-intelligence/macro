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
source is independently qualified, `bind_followon_adoption_probe.py --repo REPO
--source-commit FULL_SHA --destination NEW_BINDING_JSON` binds seven direct files from
that commit. It does not substitute for the A1 seventeen-file or served-asset bindings.
The new destination must not exist. A symbolic revision or Git symlink is refused.

After lawful follow-on landing and normal installation, the original parent can run
`followon_adoption_probe.py --root INSTALLED_ROOT --binding BINDING_JSON
--producer EXACT_REGISTERED_PRODUCER_PATH --python INSTALLED_PYTHON`. Repeat `--producer`
for the actual planned change being assessed. This invokes only the existing T12
required-tier CLI and T5 source-findings CLI, without overrides of clocks or artifacts.
It records the seven file hashes and installed HEAD before and after observation.
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
