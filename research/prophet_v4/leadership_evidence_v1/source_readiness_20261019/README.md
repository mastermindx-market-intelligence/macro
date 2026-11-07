# Outcome-blind peer-source readiness audit

Frozen main snapshot3091c8895028db57c06809593079896f85e3efc1; observation date
2026-10-19. Exactly three already-committed roster/reference artifacts were read
(490237 bytes). No price, return, outcome or strategy-label file was read by the
audit. The canonical Data OS alias/issuer readers were reused through
engine.us_candidate_episode_intake.load_identity_spine; no identity fallback.

## Actual findings

49 baskets contain1020 eligible membership slots and702 unique tickers. The native
reader resolves697; ANGPY, B, IMPUY, PSKY and RHHBY remain unresolved.45 baskets have
complete identity coverage;4 do not: obesity_glp1(13/14), gold_miners(11/12),
pgm_miners(2/4), us_sector_comm(22/23). These fractions count resolved ticker rows,
not distinct issuers, statistically independent observations or research admission.
The communications basket contains FOX/FOXA, GOOG/GOOGL and NWS/NWSA pairs under
three shared native issuers.254 tickers appear in more than one basket; the maximum
is5 baskets. Across complete-identity groups, energy_complex and us_sector_energy
share18 issuers out of25 in their union. Similar group labels must not be counted
as independent confirmations merely because they appear as different panels.

The source explicitly labels35 of49 basket histories back-projected.780 source
member records have an index-inclusion date earlier than their curation date.
The index mask `added` is not a historical availability timestamp; use the distinct
`curated_added` semantics and the appropriate accepted source-vintage owner.
This current-roster audit does NOT qualify a historical replay.

There are zero malformed exact keys, duplicate ticker keys, unknown membership
dates or native identity-reader errors in this audited snapshot. PR9714 therefore
repairs a proven synthetic invalid-input hazard; it is NOT an assertion that this
snapshot exhibited that malformed-key failure.

## Source reconciliation, not native reference edits

identity-correction-evidence.json records first-party evidence for the five unknown
symbols. B is a documented dated symbol change; PSKY also has a successor accounting
boundary. RHHBY and IMPUY require ADR-specific instruments, not naïve common-share
substitution. ANGPY's issuer page has mixed/legacy wording and remains partial.
The existing Data OS owner must decide canonical mappings, temporal intervals and
admission. No native security IDs, alias records, source rights or price histories
were changed. The full resolution map is intentionally not published as another
identity registry; this package retains aggregate evidence and the existing inputs.

## Reproduction and provenance

inputs.json pins the three Git blobs and SHA256 values. audit_executed.py.txt is the
verbatim code of the completed, source-only diagnostic, not an installed production
builder or new serving API. It uses the original registered peer workspace's native
reader and the exact retained input copies in its stated scratch directory. The
original full local report hash is recorded in source-readiness.json. Published
aggregates remove the per-ticker resolution map and raw per-group issuer lists;
counts and the narrow duplicate-listing witnesses are unchanged. All denominator
sums, completeness counts and exact input hashes were independently recomputed in
a separate readback step. No outcome or forward-return trial was opened.

Next: submit these exact five source gaps to the incumbent identity owner, preserve
unknowns until its references qualify, and make Q05 group-conditioning designs
explicit about overlapping rosters, issuer versus listing units and source curation.
Do not modify current group weights or add a new peer score on this audit's authority.


## Root causes reconciled with the actual incumbent owner

The initial five-unknown census remains numerically correct, but it must NOT be read
as five missing alias rows. A second native namespace read now pins their causes:

- PSKY resolves in membership through2026-10-05, then is deliberately absent. SKYD
  resolves from2026-10-06 to the same SEC:US-XNAS-PSKY. Store/yahoo_fetch intentionally
  remain PSKY. This accepted #8828 behavior is described by existing issue9571. The
  basket snapshot still presents the old membership key; neither a new issuer nor a
  fictitious store migration is the fix. The October6 issuer/SEC release confirms
  the current SKYD spelling; the2025 merger/accounting source is historical context.
- B is named in DEFERRED_IDENTITY_KEYS in the existing security-master builder. Its
  absence is deliberate: Barnes previously used NYSE B; Barrick changed GOLD to B;
  Gold.com later reused GOLD. Existing issue8478 already names this required negative
  case. A bare symbol-pair rename would merge different issuers. Keep it refused
  pending the owner's scoped continuation/reuse amendment.
- The three ADR symbols remain absent across the four inspected namespaces. Current
  first-party instrument facts are supplied as qualification inputs, not adoption.

namespace-reconciliation.json records this bounded exact-source differential. No
alias, data file or publisher was modified, and the original report hashes/counts
remain unchanged. Identity completeness alone does not qualify current listing,
tradability, financial comparability or historical availability; each requires its
own declared source and effective-time contract. The canonical Data OS programme
remains the receiving owner; its #9617 publisher hold is preserved.
