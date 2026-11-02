# Contracts source custody after an unresolved Fabric operation

Chris explicitly answered **“Authorize quarantine and fresh implementation”** to
the reviewed quarantine/source-release proposal on this programme's original
native root `01a1333c-a475-7052-95a8-72a88eb8c17b`. This is the provenance of the
narrow decision; this document is not itself a new authorization.

The original operation `rf-codegen-contracts-impl-01a1333c-v1` remains
**EFFECT_UNKNOWN**, unaccepted and without proven outer-process termination. Its
original assigning native parent was `01a1333e-742d-7c80-8dbb-db42109f06ce`.
One recorded child completed, but that does not prove the outer operator stopped.
The original shell handle is unavailable. The recovery owner found no retained
original process-generation anchor sufficient to prove termination. Neither
elapsed time nor lease expiry supplies that proof.

One qualified original-artifact read was refused with
`original_file_owner_mode_type_or_size`; its receipt SHA256 is
`c9efd84e4e742a4ce768edddb9eb5f916191602fae492ba7b2b1d358de12255f`.
That read remains closed. There is no retry, alternate reader, permission change,
forced termination, lease manipulation or original-operation acceptance.

Chris's decision accepts the risk of duplicate private labour and releases only:

- `engine/research_codegen/__init__.py`
- `engine/research_codegen/contracts.py`
- `engine/research_codegen/input_contract.py`
- `engine/research_codegen/output_contract.py`
- `engine/research_codegen/admission.py`
- `tests/test_research_codegen_contracts.py`
- `tests/test_research_codegen_input_contract.py`

Any eventual original output is quarantined as historical evidence. It cannot be
automatically integrated, reclaim source custody or replace the newly reviewed
source. Preserve the original operation and its evidence unchanged.

The distinct fresh implementation is `rf-contracts-fresh-01a1333c-v1`, commissioned
through the installed M2 adapter by the current verified Sol parent
`01a137c8-ddd0-7e82-8df5-6d3d2d15b0f1`, preserving the original root. It starts from
Macro `ee3b1907497c4d5179d76626777b007e0da93d18` and the existing accepted accounting,
evaluation and transport interfaces. The worker returns a private patch; root
retains repository writes, integration, review and release. A launch receipt is
not proof that its result or source has been accepted.

Its scope is inert, bounded JSON validation. Candidate generation or execution,
historical/holdout evaluation, canonical TrialLedger/HoldoutVault writes and
production activation remain separate acceptance gates. No additional operator
child allowance is granted.

The local decision receipt is retained under the programme evidence directory as
`CONTRACTS_QUARANTINE_SOURCE_RELEASE_DECISION.json`, SHA256
`fdf02888f6e99728b4a4c740c04c3576bb27e7d6daf8450d92cd24a5ef12ed66`.
It records the direct user reply to question call
`call_f30712edf7cd47ddb17fb4f806f5550c`. The existing Fabric Integration recovery
owner was informed through the previously authorized same-operation chat path.
