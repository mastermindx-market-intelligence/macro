> Deferred prototype: this directory describes application commit `1989dd890273164b728e462a49121fe74a0bf3c1`. It is excluded from the upcoming release. `deferred_issuer_context.patch` preserves the exact four-file implementation against reviewed source `70d9b7e08337`; later reinstatement requires lawful independent review and fresh integration. Its 28-source manifest and issuer probe do not apply to the narrowed release. The active 24-source bundle is `../../validator_integrity_phase/postlanding/`.

# Current-source portable acceptance preparation

Application frontier: `1989dd890273164b728e462a49121fe74a0bf3c1`.
`candidate-source-hashes.json` binds 28 local source files. It extends the older
24-file inventory with issuer_baseline and the three incumbent pure financial
engines; it changes only the expected official-feed planner and staging-entrypoint
hashes in that older inventory. It does **not** supersede independent source review
or constitute release acceptance. The three reviewed UI pages remain unchanged.

The standalone `installed_doj_context_probe.py` needs Python and the repository's
normal runtime dependencies, not pytest. Its fixtures are isolated temporary
files, its publisher clock is explicitly historical, and its single attempted
consumer admission must refuse before the mocked provider guard. Both module
and integration behavior are exercised without a producer or public write.
Eight control groups pass locally; the earlier installed_integrity_probe.py's
ten groups also pass against this same candidate manifest. Wrong manifest bytes
are rejected before importing product code. Evidence JSON is beside this file.

After independent review of the later source, actual protected follow-on landing,
and source-hash reconciliation, bind the accepted manifest to the actual merge
SHA and stable installed HEAD via the existing acceptance/ancestry mechanism.
Use the normal VPS updater. Transfer the probe through the existing SSH transport
and run `/opt/macro/.venv/bin/python -B` against `/opt/macro` and the bound manifest.
Do not install pytest, run a provider, reset accounting, change publication/cutover,
or substitute a candidate SHA for the actual protected merge. Run read-only staging
inspection and HTTP checks afterward. Identical page hashes permit reuse of the
scoped prior browser proof; they confer no new article or acquisition-write claim.

The local results are reproducible from this checkout using:

```sh
python3 -B research/agentic_media/public_intelligence_20261011/doj_source_phase/issuer_context/installed_doj_context_probe.py . research/agentic_media/public_intelligence_20261011/doj_source_phase/issuer_context/candidate-source-hashes.json
python3 -B research/agentic_media/public_intelligence_20261011/validator_integrity_phase/installed_integrity_probe.py . research/agentic_media/public_intelligence_20261011/doj_source_phase/issuer_context/candidate-source-hashes.json
```
