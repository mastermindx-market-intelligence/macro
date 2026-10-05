# 09 - F6 identity boundary clarification

Status: architecture clarification only; no Data OS or metadata source code modified.

## Existing owner law

`engine/entity_resolver.py` is explicitly CONTEXT-ONLY. It may produce deterministic candidate tickers from free text, but it is not exact security identity authority.

`lib/dataos/identity.py::VendorAliasTable` plus the committed Data OS security/issuer master remains the sole exact listing/security/issuer identity owner.

## Research Vault F6 consequence

A derived Research Vault metadata row must preserve at least three distinct layers:

1. source_declared: literal ticker/security metadata supplied by the institutional source/sidecar;
2. observed_candidates: deterministic symbols/entities extracted from title/summary/full text, including entity_resolver method/confidence;
3. exact_identity: Data OS security/listing/issuer ids only after canonical Data OS resolution.

Candidate symbols are never silently upgraded into exact ids.

## Time law

Research reports are historical observations. Exact resolution must use the report observation/published date.

The existing theme-graph Data OS consumer already proves an important two-clock rule: current-catalog vendor spaces such as `store` and `yahoo_fetch` answer current repository-key questions and must not be used as historical naming evidence merely because their rows can cover a date.

F6 must therefore either:
- resolve an exact canonical inception-code match owned by the master; or
- query historical-capable VendorAliasTable spaces at the report date and require one unambiguous security id; or
- abstain with a typed unresolved/ambiguous state.

It must not invent a Research-Vault-specific ticker allocator, map by ticker equality alone, or project today's current-catalog symbol backward.

## Required projection states

At minimum:
- RESOLVED
- CANDIDATE_ONLY
- AMBIGUOUS
- NOT_IN_MASTER
- IDENTITY_UNAVAILABLE

Every non-RESOLVED row keeps the observed candidate/context so text search remains useful without fabricating exact identity.

## Implementation sequencing

F6 candidate extraction can proceed before F5 publication because title/summary already exist, but full-text-derived candidates must bind to exact `source_pdf_sha256` + `extracted_text_sha256` once F5 materializes.

Exact identity publication should wait until the Research Vault adapter has a tested report-date Data OS resolution seam. Reusing the theme-graph private helper directly is not acceptable; either consume VendorAliasTable through a Research-owned adapter or promote the general historical-symbol resolution seam under the Data OS owner.

This clarification narrows F6 and does not block F1/F2/F4/F5.