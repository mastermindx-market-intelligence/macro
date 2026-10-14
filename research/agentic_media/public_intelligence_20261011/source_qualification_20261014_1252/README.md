# Public Research intake acceptance, October14 12:52 wake

The existing ingestion and planner now have a real-public-PDF consumer proof:
19 checks plus2 refusal controls pass. No application source changed. This evidence
does not admit the PDF to the canonical inbox, authorize a Press draft or prove a
live Research page. The `slot` inside local_intake_result.json is a fixture result.

Reproduce with the original retained PDF, this exact repository revision and a NEW
output directory (existing output deliberately refuses):

```sh
python3 -B research/agentic_media/public_intelligence_20261011/source_qualification_20261014_1252/verify_eia_local_intake.py REPOSITORY RETAINED_PDF NEW_OUTPUT_DIR
```

Retained original: `/Users/chriswong/agent-evidence/mmx-public-intelligence-20261011/recovery-20261014-1252/eia-intake/steo_text.pdf`.
The probe checks its exact SHA before any writes, uses only LocalStore, prohibits
Python network connections, keeps all corpus/store/fixture writes in NEW_OUTPUT_DIR,
and verifies source/sidecar inputs stay unchanged. It does not copy or reset runtime
accounting. It uses the normal configured Research window/cadence and preserves
cutover false. The existing dependency fallback reported datasketch unavailable;
this is not near-duplicate production proof or mixed-desk acceptance.

`source_qualification.json` owns source-specific limits; `worker_adjudication.json`
retains PARTIAL_NOT_ACCEPTED without replay. The six sidecar bullets were authored
and cross-checked by the parent against PDF physical page4, publication date onpage5.
No held Press draft was edited. Original PDF/images stay outside Git. EIA's cover
photo prevents blanket whole-PDF rights admission despite qualified textual facts.
The CBO PDF403 is a distinct stopped acquisition, not a reason to change carriers.

`canonical_research_read.json` proves four strict READS of the existing dedicated
Research store, not write authority, publication or a tested upload. The service
credential file is named by the existing unit. Credential values never leave the VPS.
The actual catalog is2896rows and the incumbent ingest workflow remains untouched.

The release snapshot is one wake read only. CI38553111016 green on a18ec982 is stale
for landing; controller38566348871 owns refresh/landing under cap8. No PRsource,
CIdefinition, packing ceiling, publication gate or original effect was changed.
