# Portfolio brief snapshot producer — accepted implementation plan

Owner: Sol / WS:MARKET-OS. Date: 2026-11-02.
App base: f125051fdb37cad7758a18833b76223146fed9d4.
Branch: sol/web-portfolio-brief-snapshot-20261102.
Status: IMPLEMENTATION AUTHORIZED; draft and unarmed until independent exact-head review, source custody, CI and parent release.

## Problem and outcome

Terminal's brief currently has no canonical book identity. Removing the proxy token cache (Terminal #1214) closes one stale-response path but does not bind a composed brief to the accepted portfolio snapshot. A same-count ticker, shares, price, status or note edit can leave older facts displayed as current.

This producer supplies a same-read witness. Terminal remains the sole owner of rowToPosition and portfolioBookKey; it will validate the witness, derive the canonical key with the existing TypeScript implementation, strip private rows, and render only when the resulting context matches its accepted canonical positions read. This PR is the producer half, not a claim that the complete user journey is delivered.

## Fixed contract and authority

Add the opt-in header `X-Mastermind-Portfolio-Context: snapshot-v1` to the existing authenticated GET /api/portfolio/brief. Authentication and Pro entitlement remain before any private read. The header selects a response contract; it grants no authority. No client-supplied owner, holdings, book key, credentials or alternate authentication path is added.

The opt-in response adds `portfolio_context`, schema `portfolio_snapshot_witness.v1`, containing authenticated `owner_id`, explicit `population`, the complete captured raw `rows`, `selected_position_ids`, and completeness metadata. Record the exact final wire fields in the evidence. No Python canonical book hash is permitted.

Capture one bounded owner-filtered portfolio_positions response, including open and closed rows and:
id, ticker, shares, entry_price, entry_currency, entry_currency_basis, entry_date, notes, status, created_at.
An exact count and returned range from that same response must prove completeness. Missing count, invalid/nonzero-start range, truncation, duplicates, over-limit response or transport failure is unavailable. Do not assemble separately timed pagination into an asserted atomic snapshot. Do not infer zero holdings from a failed or incomplete read.

Freeze that captured result for this request. The exact selected source rows feed the unchanged composer and are identified in the witness. No later positions query, legacy loader call, cached legacy brief or caller-supplied key may supply or replace either side. Preserve original row values and currency/receipt fields. The witness stays server-to-server and must never be logged or placed in URLs.

Terminal remains the sole canonical normalizer and key owner. Selected IDs alone do not prove compatible inputs: before a brief is accepted, Terminal's proxy must establish that the witnessed selection and composition inputs agree with rowToPosition. This producer must reject unsupported or ambiguous raw values that would be interpreted differently by the existing Python composer. Examples include boolean numerics and unsupported numeric syntax; demonstrate the boundary with shared adversarial fixtures. Do not silently create a competing Python normalization policy. Open membership must respect Terminal's canonical status coercion; malformed or dropped rows cannot quietly become different holdings.

Bound mode bypasses both reads and writes of the legacy brief cache. Ordinary requests retain the exact legacy loader, cache and response behavior. Never attach a fresh witness to a previously cached brief or mutate an existing cached object. Market state_digest remains a market-context cursor, not a portfolio identity.

A watchlist fallback may follow a proven zero-open result without re-reading positions. It remains explicitly watchlist_union and can never receive a positions qualification. If safe fallback cannot be produced within this isolated scope, return an explicit unavailable result and report that bounded behavior for parent adjudication rather than inventing positions.

## Source scope and collision ruling

Owned paths:
- app/main.py: only the existing brief endpoint's optional bound-mode integration and narrow import/signature wiring.
- engine/neuralweb/brain_gateway.py: an additive count-aware private read helper beside _sb_get, using its existing authenticated transport configuration and failure posture.
- app/portfolio_brief_context.py: new snapshot validation/projection and witness helper.
- tests/test_portfolio_brief_context.py plus a narrowly named shared JSON fixture under tests/fixtures/portfolio_brief_context/.
- docs/verification/portfolio-brief-snapshot-20261102/ for exact evidence.

Freeze _sb_get, _portfolio_load_holdings, _holdings_fingerprint, _tool_get_portfolio_brief, engine/portfolio_brief.py, engine/portfolio_changes.py and the changes endpoint. No auth, entitlement, schema, DDL, migration, store, dependency, public shell or unrelated feature change.

Foreign open PRs are not abandoned: #8687 head4df6828f4c5b9aa94088f8439c805e0ee7542a30 changes legacy currency projection/fingerprint and the gateway tool; #7658 head4005b0c24080d377315957b93248d135c001c22b changes _sb_get failure narrowing; #10203 touches composer/changes. Parent authorizes only the isolated additive helper and current endpoint integration, with those foreign hunks preserved byte-for-byte. This is a separate semantic feature branch, not takeover or release of any foreign writer. Reconcile fresh PR/file/hunk and actual source lease state before editing; stop for material overlap or a live conflicting lease. Do not import unmerged foreign source.

## Discriminating validation

1. Test the real endpoint with authenticated/entitled fixtures and capture actual compose_brief arguments. Prove one complete positions read supplies both composer rows and witness; a later changed read cannot be stamped onto the earlier brief.
2. Prime the legacy cache and prove opted-in requests never consume or mutate it. Repeated bound requests capture fresh same-count changes; ordinary request behavior remains unchanged.
3. Fail closed for 1000 returned rows with a larger exact count, missing count, invalid range, duplicate IDs, malformed rows, over-limit rows and transport failures.
4. Prove owner filtering, auth/entitlement-before-read, all closed rows retained in the witness, canonical open status selection, explicit population, and no fallback on unknown positions.
5. Shared adversarial fixtures cover decimal numeric strings, integers/1.0, negative zero, small/large exponents, nulls, boolean and unsupported numeric syntax, Unicode, timestamps, shuffled row order, dropped rows, and valid/invalid currency receipts. Record unsupported cases honestly; do not change hash/normalizer owners.
6. Prove no witness appears in logs/URLs and no credentials or raw real-account holdings appear in artifacts.
7. Run relevant existing portfolio-brief/changes/auth tests and required lint/typecheck/CI. Avoid unrelated full-data suites unless a concrete risk or repository gate requires them.

Capture baseline absence/failures before implementation, then exact passing commands/counts. Fixtures must be synthetic. Tests must discriminate original intent, not just mirror a helper.

## Delivery and custody

Read current repository and nested instructions plus protected Mastermind procedures at ae3fc6fce8f704b32b01664f1b0d1c0d52a1c8ed. Use an admitted isolated workspace; no shared primary mutations. Commit/push ordinary non-force changes to this branch and keep the PR draft/unarmed. Report exact source head/tree, complete changed paths, tests, honest gaps, remote/local parity, external-effect and source-custody receipts. Retain or reversibly quarantine only this run's generated artifacts outside the audited source workspace; canonical verification includes ignored files. No broad clean or ownership expansion.

Independent review is required before parent acceptance. No self-approval, Ready, merge, deployment, database mutation, production-account mutation, worker spawning or watcher registration is included in this worker assignment.

Rollout order is producer first, then Terminal consumer. An old/missing producer witness must be handled as unavailable by the future consumer. Parent retains final integrated and authenticated live-path acceptance.
