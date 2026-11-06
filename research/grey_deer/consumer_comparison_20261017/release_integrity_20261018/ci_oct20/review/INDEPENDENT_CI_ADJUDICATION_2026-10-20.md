# Independent review — Macro #9595 CI adjudication

Date: 20 October 2026. Reviewer: `/root/ci_reference_adjudication_oct20`, advisory only.

**Verdict: accept the operational ruling; request two documentary corrections before calling the entire report independently verified.** Keep the ac08 failure, do not invent a RIG approval or competing repair lane, and require the next substantive candidate to obtain its own actual integrated CI result. This review grants no CI waiver, merge approval, production acceptance or source-writer transfer.

## Scope and exact evidence

This was a new cloud-only review of four completed root observations. No Studio, GitHub, browser, provider, source-runtime, test or workflow action was invoked. The earlier 3,677.2-second unreturned read remains a separate failed investigation and supplies no evidence here.

| Reviewed file | Bytes | SHA256 |
|---|---:|---|
| `CI_CURRENT_HEAD_ADJUDICATION_2026-10-20.md` | 4,644 | `79265ffbadcba89d861b2e1f51fecdad586dc92acfdf4f21a5947e0b25e902e8` |
| `AC08_FAILED_CI_PACK_1_117650324539.log` | 92,453 | `3f026febcbb0447ed844ddd86fc4ddf46747d473b220f2b98fc0b43f55d46b4d` |
| `CI_AND_CURRENT_SOURCE_METADATA_2026-10-20.json` | 36,036 | `2936834f82ad9e343e5237f6281bc0ed19cf774db245e57c502b995440cf112d` |
| `CURRENT_RELOCATION_NATIVE_READ_2026-10-20.json` | 31,148 | `c170c7d2b097d1f8949d548dcd00bcd6b17e61c306f96c338414cf7ac1784cc8` |

Paths in this table are relative to this review's parent directory. The report was read in full; the complete retained log was searched locally and decisive checkout, gate and failure sections were inspected. Metadata and the current L8 implementation excerpt were inspected directly. Only Python standard-library parsing, hashing and local text inspection were used.

## Confirmed findings

1. The retained run metadata identifies CI **39118765804** as failed and fences **39118765782** as successful. All twelve pack outcomes are present: eleven passed; **ci-pack-1**, job **117650324539**, failed. Contract-delta passed. Downstream **ci-gate** failed its semantic-verdict step. These facts do not constitute a passing whole CI result.
2. The failed-pack log explicitly binds subject head **`ac08d5bd630d480a97fcbd0d9814946724250011`**, tested integration **`3d1a4e0df8faa6719edd8a59c467646516faf1c7`**, and tested base **`b912fd97827cca925a7123aa2012e9765077f3f7`**. The checkout message and `SUBJECT_HEAD_SHA` / `TESTED_TREE_SHA` / `TESTED_BASE_SHA` agree.
3. At 10:28:53 UTC the integrated checkout reports exactly the three named Sector Central `packet-without-rig-receipt` failures. The final pack failure list contains only `reference-integrity`. The reported archived-code contract-delta/import failures are absent from this current CI result; this supports the narrower conclusion that the packaging repair removed those observed failures.
4. Current source metadata is bound to **`247677efade31ea32d6b6ef5b701de61c47392cd`**. It records the three old-path 404 responses and the three current documents under `research/design_candidates/sector_central_20261018/`. Their captured content explicitly retains design/prepared/integration-candidate status and pending production/Paper acceptance.
5. The captured current L8 source still scans `research/migration_packets/*.md`, requires `RIG-RECEIPT`, and rejects any cited reference whose status is not `approved`. Moving an unapproved design to the design-candidate namespace does not approve it. This review neither adds a receipt nor alters a guard or exemption.
6. The native history record binds **`b91514a3a4301edff33ced2644e4cea7cdfef716` / #7100**, committed 19 October 2026 at 08:21:41 UTC, to deletion of the three old namespace paths. Its commit message explicitly says to retain unapproved sector plans as design drafts. Current draft locations are separately recorded.

## Required documentary corrections

### F1 — name the second execution as the base comparison

The report calls the 10:34:12 UTC failure the pack's "second attempt." The log instead shows checkout of **b912fd** immediately beforehand (lines 957–958), followed by the same three failures (lines 1014–1017). This is the base comparison, not another test of the integrated 3d1a4e checkout. State that both the integrated candidate and its tested base produced the same three findings. This correction strengthens the base-existing diagnosis while preserving exact attribution. It is not evidence of a new user-requested rerun.

### F2 — distinguish root-observed lineage from reproduced byte proof

The four assigned files do not retain the underlying **ac08 old-path absence**, **b912 old-blob** or **addition commit 2cca92/#9592** reads. The native relocation record contains commit/name-status output, not a full rename or old/new blob comparison. Those exact claims therefore remain root-attributed observations rather than independently reproduced lineage within this review packet.

The captured `current_draft_files[].content` strings also do **not** reproduce their advertised Git blob SHA1 values when hashed as Git blobs; adding one final newline does not resolve any of the three mismatches. This may reflect bounded or transformed connector text. It does not prove repository corruption, but those strings must not be presented as byte-exact source copies. The advertised Git blob IDs are metadata evidence, distinct from the captured text bytes.

Before claiming independently verified byte-preserving relocation, either attach the already-completed exact old/new Git-object comparison and ac08/addition lineage receipt, or narrow the wording to the current metadata and explicitly attribute the fuller comparison to root. No remote reread or new test is required by this advisory review. Current guard behavior is directly visible; equality to a historical guard revision is not independently established by the supplied current-only excerpt.

## Root's next action

Correct F1 and preserve the F2 evidence limits or attach the existing completed receipt. Continue the substantive evidence update on the existing draft #9595 carrier. Its next integrated CI must bind and test its actual new head, enclosing revision and integration base. Keep the prior ac08 red visible, keep required gates intact, and keep the PR unarmed while required evidence is pending or red.

The current draft relocation is consistent with leaving unapproved work outside the migration-packet namespace. It supplies no numerical-policy, reference, Paper, release or production approval. This review cannot predict that the next whole pack will pass and does not authorize an ancestry-only merge, unchanged-head rerun or competing repair.

This finite child review is complete. No live tool, pending PID, modifying effect or follow-up investigation was created. **STOP.**
