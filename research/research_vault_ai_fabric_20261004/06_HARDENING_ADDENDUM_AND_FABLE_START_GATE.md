# 06 — Hardening addendum and Fable start gate

**Status:** canonical clarification to the 2026-10-04 Research Vault AI Fabric packet.  
**Observed compatibility pin:** Macro `a8bde76b2642e01e374089b1a759f3ac8e3e3b26`; protected Mastermind `28be2ce2d481fd542ec869344e178e5cec4d7d75`.  
**Carrier:** PR #8438 / `sol/research-vault-ai-fabric-masterplan-20261004`.  
**Effect:** this file clarifies execution semantics only. It does not START Fable, deploy an MCP, mutate R2, change rights, or transfer source custody.

This addendum is the controlling clarification when an older sentence in the packet is less precise.

## 1. Why this addendum exists

Additional source review after the first packet publication found two details that materially affect the first implementation wave:

1. the current private-store risk is narrower and more precise than the old Agent OS discovery wording; and
2. the existing Research Vault ID-set census can prove row identity while still missing a severe **body/text-health collapse**.

Both must be corrected before Fable begins effects.

## 2. Corrected private-R2 finding

Current `engine/research_vault/r2_store.py` does **not** silently fall back to the generic shared bucket name when `R2_RESEARCH_BUCKET` is absent. `build_store()` currently requires an explicit non-empty `R2_RESEARCH_BUCKET`.

However, isolation is still not structurally proven:

```text
R2_RESEARCH_ENDPOINT       or R2_ENDPOINT
R2_RESEARCH_ACCESS_KEY_ID  or R2_ACCESS_KEY_ID
R2_RESEARCH_SECRET_ACCESS_KEY or R2_SECRET_ACCESS_KEY
```

and current construction does not itself prove:

```text
R2_RESEARCH_BUCKET != R2_BUCKET
```

when both are configured.

Therefore the security defect should be stated as:

> The research bucket name is explicit today, but the canonical private Research Vault factory still permits generic endpoint/credential inheritance and lacks a fail-closed anti-alias assertion against the shared/public delivery bucket. A configuration mistake can therefore erase the intended private-plane separation even though the normal deployed path currently supplies the dedicated research secret family.

### F1 implementation law

For production/private Research Vault use:

- require an explicit research bucket;
- require an explicit reviewed research endpoint/credential family, unless the security owner deliberately qualifies same-account shared credentials as acceptable;
- reject partial research configuration;
- reject `R2_RESEARCH_BUCKET == R2_BUCKET` when the shared/public bucket is configured;
- never infer a private guarantee merely because an environment variable name contains `RESEARCH`;
- preserve explicit `LocalStore` and hermetic test modes;
- keep RIO strict CAS semantics unchanged;
- never print effective credentials.

The implementation owner should not blindly encode "dedicated credentials are always mandatory" before reconciling current deployment/security policy. The invariant is **provable private-plane isolation**, not a particular secret-management aesthetic.

The old discovery remains valuable historical evidence, but current code is the source of implementation truth.

## 3. Corpus identity is not corpus health

The incumbent `scripts/research_vault_census.py` measures:

```text
CATALOG_IDS
VAULT_PDF_IDS
CORPUS_IDS
RECEIPTED_IDS
```

That is necessary but no longer sufficient.

A corpus can contain a `documents` row for a report while its body is empty, truncated unexpectedly, bound to incomplete measured facts, or otherwise unable to support the retrieval contract.

The October 4 production evidence is the reason this distinction is now P0:

```text
catalog rows                  2778
committed public excerpts     1497
current excerpt derivation     351
bodies_reextracted               0
reextract candidates checked     0
```

The excerpt guard correctly preserved the known-better snapshot. It did not diagnose the body state.

## 4. F2 must add a body-health census

Extend the read-only integrity measurement, or create a companion read-only report under the same Research Vault owner, to measure at minimum:

```text
corpus_rows
corpus_distinct_doc_ids

body_nonempty_rows
body_empty_rows
body_chars_total
body_chars_p50/p90/p95/p99

text_layer.full
text_layer.thin
text_layer.none
text_layer.unavailable
text_layer.null_or_unknown

valid_pdf_content_sha256_rows
missing_or_invalid_pdf_content_sha256_rows

source_char_count_present_rows
stored_body_chars_eq_source_rows
stored_body_chars_lt_source_rows
stored_body_chars_gt_source_rows_or_inconsistent

excerpt_derivable_rows
catalog_rows_with_corpus_row_but_no_usable_body

page_separator_coverage
page_count_present_rows
```

Where a measurement would require re-extracting PDFs, keep the census read-only and distinguish:

- exact whole-estate facts from the existing corpus;
- reproducible stratified estimates;
- facts that require a later canonical extraction pass.

Do not turn measurement into repair.

### Required invariant

A green identity census is **not** a green retrieval census.

The acceptance report must carry both:

```text
identity_completeness
text_retrieval_completeness
```

with typed exclusions.

## 5. F3 repair must cover two defect shapes

F3 previously emphasized `catalog_ids - corpus_ids`.

It must repair or classify both:

### Shape A — missing row

```text
catalog ID exists
canonical PDF exists
corpus row absent
```

Use the bounded self-quiescing promoted-PDF backfill already designed in the 2026-08-19 handoff.

### Shape B — row exists, usable text absent or invalid

```text
catalog ID exists
canonical PDF exists
corpus row exists
body unusable / measured text state inconsistent
```

Repair from the canonical promoted PDF under explicit candidate rules. Do not delete receipts or replay the inbox.

The existing `_reextract_bodies` only selects `text_layer='unavailable'` or NULL. If the live collapse is caused by another row state, broadening or complementing that repair requires evidence from F2, not guesswork.

### Repair acceptance

Before publishing a repaired corpus:

- compare pre/post ID sets;
- compare pre/post body-health distributions;
- prove no catalog/PDF/receipt regression;
- prove repaired rows become searchable;
- prove the public excerpt derivative no longer collapses unexpectedly;
- retain typed scan/no-text exclusions;
- report remaining backlog and failures explicitly.

Do not weaken or delete the excerpt-collapse guard to make the symptom disappear.

## 6. Full-text materialization is separate from historical corpus repair

F3 restores the incumbent search baseline.

F5/F7 then build the new full-tail architecture.

Do not combine these into one risky migration.

Sequence:

```text
repair incumbent corpus truth
    ->
freeze PDF/text identity
    ->
materialize canonical full text
    ->
derive deterministic replayable segments
    ->
build full-tail retrieval
```

This lets Fable prove the old system is sane before replacing its known 60k-prefix ceiling.

## 7. Hash-domain freeze

Current source review confirms:

- Research Vault measured `content_sha256` = SHA-256 of canonical PDF bytes;
- Research Intelligence v1 `document.content_sha256` = SHA-256 of extracted UTF-8 body text.

No consumer may emit one unqualified `content_sha256` in the new Research Read contract.

Use explicit outer names:

```text
source_pdf_sha256
extracted_text_sha256
extractor_name
extractor_version
segmenter_version
```

Compatibility law:

```text
mastermind.research_intelligence.v1.document.content_sha256
    == extracted_text_sha256
```

until a separately versioned RIO schema changes that field name.

Never reinterpret RIO v1 in place.

## 8. Metadata truth gate

Current catalog evidence remains:

```text
desk       10 / 2778
tags       10 / 2778
tickers     0 / 2778
```

Therefore the initial MCP may expose only filters backed by real indexed metadata.

A field may become searchable after a provenance-bearing derived metadata contract lands, but the tool schema must not imply that a zero-coverage source field already exists.

Exact security identity stays with Data OS / `VendorAliasTable`.

Model-derived entities/tickers are candidate context unless deterministically resolved through the exact identity owner.

## 9. OpenAI product seam revalidated

As of 2026-10-04 current OpenAI product documentation still supports the intended first canary:

- Pro developer mode can connect custom MCPs with read/fetch permissions;
- Deep Research can use custom apps for read/fetch, not write;
- local-only MCP servers are not directly reachable by ChatGPT;
- Secure MCP Tunnel is an outbound private-network path and does not itself publish the MCP publicly;
- public plugin distribution is a separate release class;
- app/tool changes require explicit refresh/review rather than implying automatic adoption.

Fable must recheck these contracts immediately before real installation/canary because product behavior can change.

The Research MVP remains read-only regardless of broader plan capabilities.

## 10. Planning-carrier collision ruling

Three documentation carriers exist for this same project:

```text
#8389 older Research Vault -> ChatGPT packet
#8430 later institutional Research -> ChatGPT packet
#8438 newest Research Vault AI Fabric packet
```

Use **#8438** as the canonical planning candidate.

Do not merge three overlapping plans into main.

Do not interpret the older PRs as separate projects or active workers.

Before final publication/merge, close or explicitly supersede the older documentation carriers under normal GitHub custody after confirming they contain no unique accepted evidence absent from #8438.

The four implementation salvage PRs remain separate:

```text
#7461 claim identity
#7354 institutional deep-read
#7522 Brain RIO consumer
#8090 longitudinal predecessor
```

They are implementation evidence, not duplicate masterplans.

## 11. Fable START gate

A receiving Fable session should not begin by recensusing the entire company.

It should:

1. pin current protected Mastermind and Macro;
2. read #8438 packet + this addendum;
3. verify no live writer/effect collision on F1/F2/F8 paths;
4. preserve #8438 as planning evidence rather than source authority;
5. execute one first capability increment:
   - F1 private-plane isolation contract and tests;
   - F2 live ID-set **plus body-health** census;
   - read-only F4 producer diagnosis where path-disjoint;
   - tiny #7461 salvage only when writer custody is disjoint;
6. checkpoint accepted findings to existing GitHub/Agent OS owners;
7. immediately continue into F3 when F2 establishes the repair class.

### WHY FABLE remains satisfied

This is still a C3 principal assignment because the first decision boundary spans:

- storage/privacy;
- corrupted/incomplete retrieval state;
- provenance identity;
- rights;
- stale PR salvage;
- cross-repo auth/MCP ownership.

After those boundaries freeze, Fable should delegate routine implementation rather than monopolize it.

## 12. First-wave decision table

| Finding | Action |
|---|---|
| research bucket aliases shared/public bucket | refuse private deployment; repair F1 |
| bucket differs but endpoint/credentials inherit generic plane | security-owner adjudication; make effective isolation explicit |
| `catalog-corpus > 0` | bounded missing-row F3 repair |
| IDs match but usable-body coverage is collapsed | diagnose Shape B and repair from canonical PDFs |
| PDFs missing for catalog rows | classify dead-report integrity issue before corpus repair |
| producer still stale | advance F4; do not weaken freshness guard |
| #7461 path disjoint | salvage structural fix early |
| source/text hash contract unresolved | block durable segment/citation API, not independent integrity work |
| full-tail benchmark passes without vectors | do not add vector infrastructure |
| private ChatGPT canary works | proceed to Deep Research proof before public distribution |

## 13. Program DONE_WHEN is unchanged

The packet is not complete when F1-F3 finish.

The parent mission closes only after the real-path acceptance in `04_ACCEPTANCE_SECURITY_AND_EVAL.md`, including:

- authorized ChatGPT;
- denied caller;
- Deep Research;
- tail evidence;
- replayable provenance;
- stale/partial disclosure;
- correction invalidation;
- rights-safe RIO distinction;
- one canonical Research Read contract shared by Brain and MCP.

This addendum strengthens the start gate; it does not narrow the end state.
