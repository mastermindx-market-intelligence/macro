# Research Vault — R22 Brain Discovery Boundary

**Status: DESIGN_ONLY.** This document narrows a remaining product dependency. It changes no Brain/Vault code and does not widen any entitlement.

## Ruling

W3 (latest lawful RIO consumed inside the existing Brain report path) is necessary but **not sufficient** for the primary institutional-research user job.

Current Brain search mode still discovers reports from committed catalog:
- title;
- summary_points;
- institution;
- recency/top-pick tie terms.

It does not call `research_vault.corpus.search`, does not consume W2 entity mentions, and does not require a company subject. Current catalog ticker fields are empty.

Current report mode can read one known report ID. #7079 improves source-bound evidence inside that selected report. W3 will enrich that known report with rights-safe RIO state.

Therefore a W3 merge alone does **not** prove:
> user asks a company/research question without knowing the PDF -> Brain finds the decisive report -> useful answer -> source inspection.

## Preserve existing paths

- Default metadata search remains compatible.
- #7079 retains selected-report evidence ownership.
- W3 remains per-report RIO consumption.
- Existing Research Vault corpus remains the only full-text search corpus.
- Existing gateway/tier/source-use owners decide whether body-conditioned discovery is allowed.

No new search/vector service, entity index, permission mirror or chatbot.

## Proposed discovery extension after incumbent releases

An explicit deeper search scope inside the existing Brain tool may reuse the existing Research Vault corpus.

Conceptual modes:
- `metadata` — current behavior.
- `source_text` — separately admitted body-conditioned discovery; only after existing gateway/source-use permission.

The model may request deeper discovery; the gateway decides admission. Metadata no-match must not silently auto-escalate across a rights boundary.

### Body-conditioned result

Return only permitted real report IDs plus bounded reason/support sufficient to choose the next report. Then use the existing #7079 report reader for literal evidence, locator/hash and existing accounting.

Do not use discovery as a free unmetered substitute for the report reader.

### Eligibility before final result budget

The candidate set must apply the request's actual permitted/catalog scope before the final search limit. Otherwise ineligible high-ranked rows can consume the limit and hide eligible evidence.

Reuse/adapt the already researched scoped-search contract; no duplicate corpus.

### Honest states

Preserve:
- healthy no-match;
- unavailable corpus/index;
- partial/prefix-only search coverage;
- access denied;
- budget exhausted;
- current catalog/corpus generation incompatibility.

A no-match in the 60k stored prefix is not proof the original PDF lacks the evidence.

## Company relevance

Current literal metadata probe proves the archive already contains many references to several high-interest companies, but it also proves why ad-hoc alias matching is not identity.

Company-qualified discovery eventually uses the existing Data OS issuer/security/listing owner.

Required roles:
- `about`;
- `compares`;
- `mentions`.

An extracted W1 entity string is a source mention, not a canonical issuer mapping.

Do not append generated tickers/company names to the institutional summary/body to make FTS work.

### First bounded company behavior

Before canonical company associations are broad:
1. preserve the user's explicit company term in the search;
2. prefer a resolved Data OS alias set when available;
3. require a supported company term/association separately from generic topic terms for a company-scoped answer;
4. refuse or broaden honestly when subject resolution is unavailable.

The earlier counterexample `ACMEQ margin` matching an OtherCo report on `margin` alone remains a valid design discriminator.

## Relation to RIO

RIO does not replace discovery.

After a report ID is discovered and gates pass:
- W3 may read safe RIO summary/state;
- #7079 verifies literal evidence;
- W1 entity mentions may explain why the report is relevant;
- later W5/W6 provide longitudinal/source synthesis.

Do not scan every W2 private artifact during every search to simulate an entity index.

## Product acceptance

The first institutional-AI journey is not complete until at least one permitted real case proves:

1. user asks a company/topic question without report ID;
2. metadata or approved source-text search discovers the relevant report;
3. wrong-company/shared-word negative does not outrank it;
4. access is checked before source-text-derived disclosure;
5. report ID reaches #7079 reader;
6. current W3 RIO is available or honestly missing/stale;
7. answer distinguishes source claim, Mastermind synthesis and calculation;
8. matching original opens under the same source identity;
9. prefix-only/unknown coverage remains visible;
10. Prophet rank/signal/sizing/execution are unchanged.

W3 source release without this journey is `BUILT_NOT_PROVEN / PARTIAL`, not completion of the parent product.

## Exact dependency order

- #7287 shared baseline repair release.
- fresh same-head #7079 current-base qualification/release.
- #7230 W2 release independently.
- W3 current-report RIO integration.
- this existing-search discovery extension.
- W1→W2 operational producer canary.
- one real permitted company question through the entire chain.

Discovery and producer may be developed against accepted interfaces when source custody allows, but production proof waits for their dependencies.
