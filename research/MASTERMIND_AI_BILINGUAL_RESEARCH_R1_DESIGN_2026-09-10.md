# Mastermind AI — Bilingual Research Search R1 Design

**Status:** APPROVED implementation wave under the Chairman’s live 2026-09-10 Mastermind AI upgrade directive  
**Operation:** `mastermind-ai-r1-lexical-retrieval-20260911-sol-001`  
**Program owner:** `macro-mastermind-ai`  
**Product authority:** `research/MASTERMIND_SUPERINTELLIGENCE_MASTERPLAN.md`  
**Implementation base:** `mastermindx-market-intelligence/macro@1f8eeab603fc37def47e1cfc6f7f3788c0300ad3`  
**Protected procedure:** `mastermindx-market-intelligence/Mastermind@068dcc1533776672844b36ffcde30fad68a4317f`, Skillpack 1.0.1 / bootstrap major 1

## 0. Observable outcome

A meaningful Chinese, English, or exchange-qualified single-term query can reach the existing `search_research` catalog reader and return relevant permitted research summaries. Exact identifiers remain atomic, natural-language hyphenated phrases retain their previous word-search behavior, and an input with no meaningful search atom still fails honestly as `query too short`.

This is the first complete source repair in the larger Mastermind AI upgrade. It does not by itself complete multilingual semantic retrieval, full-text passage search, answer citation, or the full research workspace.

## 1. User and machine jobs

**User job:** Ask for research in the language and identifier form naturally available to the user—for example `中国流动性`, `semiconductors`, `AAPL`, `BRK-B`, or `600036.SH`—without padding the query with a second irrelevant word.

**Machine job:** Normalize harmless width/case differences, preserve exact security-like identifiers, derive bounded lexical atoms, score the existing permitted catalog exactly as before, and disclose genuinely unusable input without manufacturing a search result.

## 2. Verified current defect

At the pinned base, `_WORD_RE = re.compile(r"[a-z0-9]{2,}")` excludes Han text. `search_research` then refuses every query with fewer than two tokens. A pure Chinese query yields zero tokens, while a meaningful single English word or ticker yields one and is rejected. The existing fallback for dotted identifiers also uses substring matching, so `600036.SH` can match a larger atom that merely contains it.

The existing ranking weights, recency decay, result projection, Research Vault tier gate, report mode, clusters mode, view quota, and full-report corpus path are separate working contracts and remain unchanged.

## 3. Architecture

Extend the private lexical helpers inside `engine/neuralweb/brain_market_intel.py`; do not add a service, index, cache, embedding store, query database, or second research owner.

### 3.1 Normalization

`_search_normalize(text: str) -> str` applies Unicode NFKC and `casefold()`. NFKC makes full-width Latin letters, digits, dots, and hyphens searchable in the same form without translating or semantically rewriting the user’s query.

Normalization applies identically to query and catalog text. The returned `query` field remains the original user input, not the normalized internal form.

### 3.2 Atom classes

`_tokenize(query: str) -> tuple[str, ...]` returns ordered, de-duplicated strings in one of three forms:

1. **Han span:** a contiguous CJK unified-ideograph run of at least two code points. It matches as a literal normalized substring so `半导体` can match `半导体行业`.
2. **Qualified identifier:** an ASCII atom containing a dot, or a two-segment share-class hyphen whose suffix is one letter (for example `BRK-B` or lowercase `brk-b`). It matches only a complete normalized atom. `600036.SH` must not match `600036.SZ`, `1600036.SH`, or `600036.SH.A`; `BRK-B` must not match `BRK-A`. Other hyphenated forms remain ordinary prose because numeric ranges and phrases such as `10-yr`, `risk-off`, and `AI-driven` are common in the catalog.
3. **Plain word:** an ASCII alphanumeric word of at least two characters. It matches a complete word. `AI` must not match `paid`; `AAPL` must not match `pineapple`.

A natural-language hyphen compound such as `near-term`, `long-term`, `risk-off`, or `AI-driven` is split into its ordinary word components unless it meets the qualified-identifier rule. This preserves the previous catalog-search behavior for common research prose rather than turning every hyphenated phrase into an exact identifier.

### 3.3 Search admission and scoring

A search is admitted when `_tokenize` returns at least one meaningful atom. Empty, whitespace-only, punctuation-only, one-character plain-ASCII, and one-character Han inputs return the existing envelope with `note: query too short` and `count_scanned: 0`.

The scoring formula remains byte-for-byte equivalent:

- title hit: 3.0 per distinct atom;
- summary hit: 1.5 per distinct atom;
- institution hit: 2.0 per distinct atom;
- top-pick tie-break: 1.0 only after textual relevance;
- existing recency factor and stable tie-breaks unchanged.

No atom repetition can buy additional weight.

## 4. Data, time, null, rights, and correction law

- The existing `data/research_vault/catalog.json` owner remains the only search input for this wave.
- Missing/corrupt catalog behavior remains `research vault unavailable`.
- A healthy catalog with no match remains a healthy empty result, not an unavailable vault.
- Publication timestamps, recency decay, institution attribution, result limits, report identities, Pro gating, view metering, and redistribution wording remain unchanged.
- NFKC/casefold is normalization, not translation. Simplified and Traditional Chinese are not silently equated; cross-language expansion is a later bounded wave.
- A corrected catalog is read through the existing request-time reader. This wave adds no retained search result and no correction store.
- Retrieved report text remains data, never instruction or authority.

## 5. Explicit non-goals

- No embeddings, vector database, reranker, FTS schema change, corpus rebuild, OCR, or web search.
- No model-generated query translation or bilingual semantic expansion.
- No change to `engine/research_vault/*`, `app/research.py`, Research Vault quota, entitlements, or source-opening behavior.
- No new provider, license, subscription, or commercial commitment.
- No prompt, model, gateway, chat UI, Terminal, memory, signal, forecast, rank, size, gate, or trade-authority change.
- No CI job or workflow edit unless the existing owner manifest proves the suite is unregistered; current inspection shows it already runs in the neural-web core job.
- No claim that Chinese retrieval is complete merely because literal Chinese matching works.

## 6. Collision and ownership boundary

A fresh 177-open-PR census found no open PR touching `engine/neuralweb/brain_market_intel.py` or `tests/test_brain_market_intel.py`. PR #7045 owns adjacent Research Vault catalog/ingest/sidecar/app paths and must remain untouched. Many PRs touch `.github/ci/legacy-jobs.yml`; this wave does not.

Before push and before merge, refresh `origin/main` and repeat the exact two-path collision census. If either primary path gains another active writer, stop and reconcile rather than force, rebase over, or duplicate the change.

## 7. Acceptance

The implementation is not accepted unless all of the following hold:

1. RED-first tests prove the base rejects Chinese-only, single-word, ticker-only, full-width, and exact-identifier cases.
2. The candidate passes those cases plus hostile decoys for `AAPL`, `AI`, `BRK-B`, and `600036.SH`.
3. Common hyphenated research prose still matches by words.
4. Existing two-word ranking, recency, top-pick, summary truncation, report, clusters, wire, rights, and fail-soft tests remain green.
5. The tool schema no longer tells the model to pad every search to two words and accurately describes meaningful single terms.
6. `git diff --check`, the owning test file, relevant gateway/schema tests, contract-delta, CI-manifest selection, and exact-head independent review pass.
7. The branch is pushed and reviewed through the normal source chain. Merge occurs only after concluded binding checks.
8. Production proof establishes the deployed commit, a restarted `macro-api` PID when the changed path triggers the existing restart gate, and at minimum a real deployed-module/catalog read for Chinese, English one-term, and exact-identifier inputs. An authenticated user-facing source-opening proof remains a separate explicit residual if no authorized browser identity is available.

## 8. Routing receipt

**ROUTE:** Codex CLI on the authorized Mac, bounded build worker using an economical engineering model; independent exact-head review by a separate high-capability reviewer.  
**WHY:** This is a specified two-file deterministic Python repair with clear tests, no architecture choice, and no cross-repository write.  
**WHY NOT FABLE:** Principal capacity is unnecessary; product thesis, boundaries, and acceptance are already frozen by Sol.

## 9. Stop condition

This wave stops after the lexical repair is merged, deployed, and honestly proven at its available production boundary. It does not absorb bilingual semantic planning, FTS/corpus integration, passage citations, company financial workflows, workspace UX, or artifact generation. Those require separately bounded successor waves under the same major Mastermind AI program.
