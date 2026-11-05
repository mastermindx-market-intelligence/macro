# F02 native repair review packet

## Review purpose and identity

Independently assess the supplied, immutable repaired native reference set. The candidate identity is the exact `manifest.json` artifact-set SHA256 together with the immutable Git freeze commit supplied separately by root after persistence. A working branch head, mutable Paper URL or author completion label does not identify the reviewed final set.

This is an advisory repair review. No verdict is requested in advance. A successful packaging check establishes file integrity and declared native completeness; it does not establish design quality, functional acceptance, reviewer qualification or approval. The packager and author do not approve their own work.

The prior closed first-pass packet supplies the unchanged user job and T01–T12. `TASK_MANIFEST.json` extracts them without changing their meaning. This repair packet changes the evidence/review procedure, not the user's job.

## User / business job

The shared product kit must let an investor read dense comparisons, understand direction and units, distinguish unknown from zero and partial/stale data, inspect the underlying evidence, and return to the same context. It must support Macro, Company, Options and a public editorial page in light/dark, EN/ZH and narrow/wide presentations. It must preserve current domain capabilities and meaningful chart/table density. Keyboard, touch and 400% zoom are part of the intended journey.

This assignment concerns common component patterns and their consumer integration. The four proposed consumer slices must not imply deletion of the remaining existing product functions. Assess whether the supplied artifacts actually support the claimed shared tasks, what became harder or missing, and whether a reasonable user would prefer the current product for an important task. Do not assume behavior from a static image.

## Integrity and closed evidence boundary

Read the supplied freeze directory, this packet and only your own prior frozen findings supplied separately by the coordinator. Keep the other critic's first-pass, rationale-pass and repair reports quarantined until both independent repair reports are frozen. Do not read working-tree changes, unselected screenshots, other critics' notes or later author edits. Do not call Paper, Browser, external websites or mutate design/product files.

Before judging, verify every manifest member's byte length and SHA256 and recompute the artifact-set aggregate. The aggregate is SHA256 over all members sorted by relative path, with each member contributing UTF-8 relative path, one NUL byte, lowercase ASCII file SHA256 and one LF. The enclosing `manifest.json` excludes itself from membership and this aggregate. Check that the directory contains no missing, unexpected or symlinked members. Verify the manifest against the separately supplied immutable Git commit; never infer or invent that commit from the digest.

The included local verifier can perform the byte-level check:

```bash
python3 <freeze>/paper/prepare_final_native_freeze.py --verify-freeze <freeze>
```

If integrity verification fails, report the precise mismatch and stop the substantive review until the evidence identity is reconciled. A later repaired freeze is a different candidate. Do not modify a frozen manifest to add its own containing Git commit.

## Required visual examination

Inspect every actual final JPEG listed in `CAPTURE_SELECTION.json`, including all **32 full-board images**, and inspect the relevant actual JSX exports for native identity, structure, editable content and source bindings. JSX inspection does not substitute for viewing images. Inspect all seven original before images and compare the supplied after artifacts against the same tasks. Use the manifest and current native index to establish actual file, page, board and step identities; do not infer missing IDs from names, diagrams or prepared input packets.

| Expected group | Full boards |
| --- | ---: |
| Foundation/readme/control/grammar/builder source group | 6 |
| Macro, Company, Options and editorial light/dark consumers | 8 |
| Mobile and state source group | 6 |
| Supplemental evidence/width group | 4 |
| Core variant/evidence companions | 2 |
| Fault compositions | 1 |
| Company/editorial/density repair companions | 4 |
| Observed metrics light clone | 1 |
| **Total** | **32** |

`EXPECTED_BOARDS.json` contains the exact keys derived from the canonical packets and their current precedence. The 32 bare-key JPEG/JSX pairs are the final full-board set. If selected, final section captures and complete closed-table width captures are supplementary evidence with their recorded scope. A closed table before an overlay may show table width and complete row content; it is not the final overlay screen. An incremental `rows3`, `rows6`, header-only or in-progress image cannot stand in for a completed board. The package's optional-capture selection must never be silently widened during review.

The original before images are:

- `evidence/macro-before.png`
- `evidence/company-before.png`
- `evidence/options-before.png`
- `evidence/editorial-before.png`
- `evidence/paper-metric-before.jpg`
- `evidence/paper-state-before.jpg`
- `evidence/paper-pattern-before.jpg`

## Contracts, source evidence and rationale

Read the current system, source/data and interaction contracts, retention ledger, native role/predecessor bindings, selected repair/arithmetic receipts and supplied final live retention/native verification receipts. An absent final receipt remains absent proof; do not substitute an old checkpoint or infer live retention from a mapping. The four retained domain/source roles remain subject to their recorded qualification boundaries.

Use the supplied author rationale as an explanation to test against the visible artifacts and source evidence. It cannot close a finding by assertion. Current construction precedence is recorded in `paper/CURRENT_DESIGN_AUTHORITY.md`: fixture coherence and readable spacing, exact observation identity/Company clocks, Company annual-growth **v2**, consumer evidence/reading/density companions and observed native corrections. The superseded Company v1 packet is not a build choice. Preparation-time `PREPARED_NOT_APPLIED` fields remain honest historical provenance; observed application is established by current writer operations, native bindings and captures.

Review your own prior findings by stable ID. For each, state **resolved**, **partly resolved**, **unresolved**, **regressed** or **not assessable from supplied evidence**, with the exact current artifact and visual/source reason. Preserve the original finding and severity history. Identify any new defects or regressions under new IDs. Do not read the peer report or mirror a peer verdict.

## Capability / task manifest

| Task | Critical | Required retained capability |
| --- | --- | --- |
| T01 Compare dense numeric rows | yes | Aligned raw-value comparison; meaningful units, coverage and source access; no hidden feature deletion |
| T02 Interpret a metric and its change | yes | Observation and comparator periods; percent versus pp/bps/currency; missing versus reported zero |
| T03 Inspect exact evidence and return | yes | Correct field/row/entity/source identity and clocks; reversible inspector; focus/scroll return |
| T04 Understand stale/partial/connected states | yes | Separate source freshness, coverage, transport and market session; retained useful data |
| T05 Use keyboard/touch/400% zoom | yes | Tabs, table scrolling, controls, overlays and virtualized-list semantics; no hover-only essential path |
| T06 Preserve Company depth | yes | Annual/quarterly statements, earlier periods, definitions, citations, route/entity identity and unknown fields |
| T07 Preserve Options depth and meaning | yes | Existing workflow tabs/filters/saved screens/share/export, side classification, exposure, coverage and exact contract identity |
| T08 Preserve Macro capabilities | yes | Regime/risk/calendar/linked desks and existing domain logic; useful chart compression remains |
| T09 Read and navigate public editorial | yes | Readable body, TOC/anchors, calculation, assumptions, publication dates and continuation destinations |
| T10 Handle exceptional read/write/access states | yes | Loading distinct from empty; clear recovery; guest/denied/expired; pending/failed/uncertain/saved with correct authority |
| T11 Switch theme/locale/density | yes | Retained meaning, legibility and hierarchy; long labels; no conflation of language, market region or trading semantics |
| T12 Use domain-owned verdict/count/lifecycle and focused charts | yes | Preserve existing meanings, partitions, transitions and chart/replay capabilities; common style must not redefine them |

## Evidence distinctions

Keep each conclusion within the evidence that supports it:

| Evidence or gate | What this review may establish | What remains separate |
| --- | --- | --- |
| Actual native images and exports | Visible hierarchy, content, density, alignment, narrow/wide compositions, apparent state distinctions and native bindings | Real interactions, rendered browser accessibility and production behavior |
| Source/arithmetic/identity receipts | Supplied fixture arithmetic, units, clocks, record identity and declared owner boundaries | Real producer data, source rights/availability, domain authority and connected integration |
| Final live retention receipt, if supplied | Recorded observation of originals, locations and shared-token retention at its observation time | Design approval or proof of later canvas state |
| Browser evidence | Only actual supplied executed browser outcomes | Keyboard/touch/focus restoration, 400% zoom, scrolling and real reflow remain unverified when no such evidence is supplied |
| F01 and consumer/domain integration | Contracted responsibilities and any explicitly supplied owner receipt | Joint release, shell/route/preference integration, entitlement, save confirmation, domain lifecycle/count/verdict qualification |
| Formal RIG and release | The existence and exact scope of any separately admitted artifact-bound record | This advisory report is not an Opus reviewer-class RIG receipt, designated authority verdict, product release or production acceptance |

An annotation describes intended behavior. A synthetic fixture explains a state. Neither demonstrates that an actual browser, source owner or save/access owner executed it. Equally, absent runtime proof is not by itself evidence that an observed native composition has a visual defect. Keep observed defects and absent proof distinct.

## Required independent output

Return your own **PASS**, **PASS_WITH_CONDITIONS** or **BLOCK** for the supplied native proposed reference set, explaining the scope of the verdict. Do not treat successful packaging or author local checks as a desired verdict.

Include:

1. Actual agent identity and model if known; review start and final UTC timestamps; exact artifact-set SHA256; separately supplied immutable freeze commit; successful hash/aggregate verification; examined-image/export list; and peer-report quarantine attestation.
2. A disposition for every one of your own prior `NPRC-nnn` Product Regression or `NVTC-nnn` Visual Taste findings, retaining IDs and recording concrete before/current-after evidence.
3. New findings with stable new IDs, blocker/major/minor severity, exact board/section and evidence, affected T01–T12 tasks, user consequence and the smallest material correction or proof needed.
4. **BETTER / EQUIVALENT / WORSE / UNKNOWN** judgments for each of T01–T12, comparing the same user task against the original before evidence. Explain any important task for which a reasonable user would prefer the current product.
5. Separate conclusions for native design defects, source/identity/arithmetic issues, and missing browser/F01/domain/formal RIG evidence. Carry unresolved conditions explicitly without approving or inventing their closure.

Save the independent repair report outside the immutable freeze and stop. The coordinator may reconcile reports only after both are frozen. Any subsequent artifact change requires a new evidence identity and affected review.
