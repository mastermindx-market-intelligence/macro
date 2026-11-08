# Direct registrant intake for existing ETF probes

The security-master writer can use a newly captured SEC submissions observation when the weekly company-ticker map lacks an ETF trust. This explicit lane supports SPY, QQQ and SMH. It supplies registrant independence evidence to the existing pending-transition fence; it does not create an Options-root alias or assign an ETF issuer group. A separate explicit SPY root intake, described below, requires that canonical security to exist first.

## Inputs and clocks

Each observation combines the exact SEC response and capture metadata with an official listing snapshot and its completion receipt. The existing receipt validator checks the listing bytes. The requested ticker must be present in the SEC response; its ten-digit CIK must match the exact SEC submissions URL. The listing supplies the precise venue through the existing resolver. The SEC's generic exchange label is not a MIC.

The capture request/read times must fall on the listing observation date. The decision follows both the SEC read and collector completion; `known_at` is the later availability clock. Fresh intake must match the current writer's listing date, exact snapshot bytes, ETF flags and venue. Missing, conflicting, delisted or older evidence refuses before publication. These checks bind supplied evidence; they do not authenticate the person who captured it.

## Explicit invocation

Use the existing canonical writer's serialized publication path after checking the current writer, inputs and outputs. Supply a local manifest containing one to three source records:

```json
{
  "schema": "mastermind.direct_registrant_input.v1",
  "sources": [{
    "symbol": "SPY",
    "response_body": "sec-response.json",
    "listing_body": "listing.parquet",
    "listing_receipt_body": "listing-receipt.json",
    "capture": {
      "url": "https://data.sec.gov/submissions/CIK0000884394.json",
      "final_url": "https://data.sec.gov/submissions/CIK0000884394.json",
      "status": 200,
      "bytes": 123,
      "sha256": "replace-with-the-actual-response-digest",
      "request_started_at": "replace-with-the-actual-UTC-capture-clock",
      "read_completed_at": "replace-with-the-actual-UTC-read-clock"
    }
  }]
}
```

The example contains deliberately invalid placeholders, not an admissible capture. File references must be sibling basenames. No network or credential operation is added. First run:

```sh
python3 scripts/build_security_master.py --direct-registrant-evidence /path/to/input.json --dry-run
```

The explicit flag cannot be combined with `--nightly`. A successful dry run publishes nothing and is not a production acceptance. Publication uses the ordinary admitted writer and preserves existing security, issuer, migration and non-native alias rows. Do not repeat a refused or uncertain operation merely because new source is available.

If the ordinary current inputs would add another security, bounded intake refuses that unrelated change. Reconcile it through the ordinary writer first, checking its actual row changes and preserving existing transitions/refusals; do not filter the inputs or relax the intake guard. Then check the new canonical preimage before a distinct explicit intake. This prerequisite is a current canonical refresh, not permission to replay an old refused request.

## Retention and current support

The existing `_receipt.json` retains the admission decision, source digests, capture clocks and, for a refusal, the canonical writer's actual cause. Explicit resubmission of a retained symbol refuses. Older prospective-reference decisions are immutable; an unsettled older request cannot borrow the new observation.

A retained BOUND decision is historical. `direct_registrant_rederivation` separately reports CURRENT, LISTING_UNAVAILABLE, RETIRED or REFUSED for this build. Later runs preserve the stored ID and require current listing support to rederive it; a missing listing therefore reaches ordinary loss detection and the pending-transition fence. Missing or conflicting stored IDs cannot be re-minted, and tombstones cannot be revived.

The file loader rejects static symlinks/nonregular files and checks sizes, but does not provide descriptor-bound protection against hostile concurrent local replacement. Publication retains the incumbent sequential multi-file behavior; this lane does not introduce atomic transactions or a parallel registry. An actual source-supported Options-root relation, current rights and entitlement, exact saved-snapshot reopening and the consumer integration remain separate requirements. IDX identity is separate from SEC identity.

## Explicit SPY Options-root intake

`--spy-option-root-evidence` adds one forward-only `occ_root` relation through the same writer, alias merger and receipt. The bounded profile is `thetadata/SPY -> SEC:US-ARCX-SPY`. It requires four retained source bodies: Cboe's underlying reference CSV, Cboe's SPY product comparison, Theta's v3 option-history symbol contract, and SEC submissions for CIK0000884394. The native listing snapshot and validated completion receipt supply ARCX. This is a source-specific inference from those documents, not a ticker-equality rule or an observed Theta response.

The input schema is `mastermind.spy_option_root_input.v1`. Its `sources` object has exactly `cboe_reference`, `cboe_product`, `theta_contract`, and `registrant`, each with a sibling `body` filename and the seven-field `capture` object shown above, plus sibling filenames `listing_body` and `listing_receipt_body`. The implementation fixes the admitted source URLs and validates the required product facts, response lengths, hashes and clocks. It makes no network request.

All request and completion clocks must fall on one UTC date, and new admission must occur on that date. The relation covers only that date, with an exclusive next-day end; `known_at` is the latest source availability. It cannot support earlier or future Matrix sessions. The existing canonical SEC record must be unique, active, exactly US/ARCX/SPY, and available by the decision cutoff. The sealed retained evidence includes its record fields and the validated listing provenance. Current listing bytes must match the input exactly.

After source landing and a current writer/input collision check, first inspect:

```sh
python3 scripts/build_security_master.py --spy-option-root-evidence /path/to/input.json --dry-run
```

Publication uses the same command without `--dry-run`. It must add exactly one relation, preserve existing aliases, and leave the other four Parquet tables unchanged. The root flag cannot combine with security admission or `--nightly`. An existing `spy_option_root` admission refuses explicit resubmission; ordinary future builds retain the sealed historical row and clocks rather than extending its window.

Consumer readback uses `resolve_option_underlying_security` with captured canonical master, alias and source-evidence bytes, retaining their digests and read-availability clock. End-to-end Matrix identity additionally requires `resolve_option_matrix_security` with a verified snapshot whose session drives the event date. A root lookup alone establishes no Matrix session. Ordinary `us_equity` deliberately continues to exclude ARCX, and ordinary forward/reverse aliases exclude `occ_root`. This profile supplies no IDX reader, rights, fresh entitlement or Save admission. The file-reader and sequential-publication limitations above also apply here.


## Captured fund reference for empty QQQ/SMH ticker arrays (R19 candidate)

The SEC submissions responses for CIK0001067839 (QQQ) and CIK0001137360
(VanEck ETF Trust/SMH), captured on October15,2026, both contained empty
`tickers` arrays. Do not insert a ticker into those responses or use title matching.
An explicitly supplied second SEC source can corroborate the fund relationship:
`https://www.sec.gov/files/company_tickers_mf.json`, whose fields are
`cik, seriesId, classId, symbol`. The SEC describes this as an EDGAR search
association file and does not guarantee its accuracy or scope. It is not itself
canonical identity, an exchange observation, issuer grouping or historical truth.

The existing `prepare_direct_registrant` accepts optional **paired**
`fund_reference_body` (exact captured bytes) and `fund_reference_capture`
(the same seven HTTP-provenance fields as the submissions response). This path
is confined to QQQ/SMH and an actually empty submissions `tickers` list. A
nonempty contradictory list is refused. SPY's original top-level-ticker path
is unchanged; extraneous fund-reference evidence does not silently override it.

The additional table must be strict bounded JSON from the exact official URL,
with one and only one requested-symbol row, a matching ten-digit CIK after
integer normalization, and well-formed SEC series/class identifiers. Duplicate
or conflicting requested-symbol rows, invalid schemas, mismatched hashes,
non-success statuses, future clocks and different observation dates refuse.
An unassigned empty symbol on an otherwise valid *unrelated* SEC class row is
not a match; it must not discard a legitimate unique requested-symbol row.
This exception does not fill, alias or normalize any ticker.

The observations must share the existing listing snapshot's day. `known_at`
is the maximum of submissions read completion, fund-file read completion and
listing collector completion. Returned `fund_reference` metadata records the
selected CIK/series/class/symbol, selection digest and complete capture metadata.
Retention revalidates those fields and clocks. Hashes prove internal byte and
selection consistency, not HTTP sender authenticity or permission to publish.

Explicit file manifests using this additional source use
`mastermind.direct_registrant_input.v2`. Each affected `sources` row retains
all five v1 fields and adds `fund_reference_body` as a bounded sibling filename
plus `fund_reference_capture` as the capture object. Existing v1 manifests are
unchanged and reject these additional fields. Paths remain bounded sibling
regular files; the CLI still requires explicit input and refuses nightly
activation. No network call was added to the canonical writer.

The original pending-transition, current-listing, canonical mint, issuer-axis,
old-reference no-replay and historical-refusal rules still apply. A prepared
record is not a mint or publication. Do not replay an existing observation or
retroactively turn the October7 refusal or October13 minute intake into
qualified evidence. No real canonical output or complete reference generation
was produced by the R19 code/test work. Authentic publication/history and
price/share/volume basis remain separate requirements.

### Reproduced source example (not an instruction to publish)

The captured file was1,235,418bytes, SHA256
`0d929faefd93374ec3f39a7650b51ff4c1e115f3ab1244f3b17b312819c91298`,
read complete at2026-10-15T18:03:09.974981Z. It had unique rows:

| Symbol | Registrant CIK | Series | Class |
|---|---|---|---|
| QQQ |0001067839|S000101292|C000271435|
| SMH |0001137360|S000034411|C000105869|

The repaired pure preparation accepted these rows against the captured
submissions and existing October15 listing bytes, retaining18:03:09.974981Z as
the latest required source knowledge, not the earlier filing date. Canonical
mint/publication and real market evaluation were not invoked. Native tests use
synthetic source bodies and isolated fixture directories, not these real data
as fabricated historic test inputs.

Primary source reference: SEC Accessing EDGAR Data, section “CIK, ticker, and
exchange associations”,
https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data.
The actual captured bytes/metadata remain in private operation evidence; do not
substitute this document's scalar examples for those bytes.

## Selected historical Options contracts (pure consumer adapter)

`engine/intelligence_workspace/options_contract_identity.py` adds a bounded
selected-contract identity composition alongside the existing root/Matrix
consumer. It is not another intake flag, registry or root-alias publisher.
The original observed-day root admission and its replay prohibition are unchanged.

For one SPY expiry/session, the admitted reader supplies exact captured native
master/listing/completion-receipt bytes, a captured parsed Massive historical
reference response with explicit `as_of`, and matching actual Theta contract
acquisitions. The adapter validates the existing canonical target, standard
series terms, exact selected keys and all known-by clocks. Its effective session
may precede acquisition, while `known_at` follows every actual evidence read.
A cutoff before that knowledge refuses; the result makes no historical first-
availability or source-use claim.

`DatedContractIdentity` exposes a selected-key receipt, with no `AliasRow` and no
root lookup capability. The existing Options producer binds that receipt to its
actual input digest and rechecks scope at consumption. A valid20contract book
cannot authorize a21st contract, another expiry/root/session, an adjusted series
or instantaneous model use. Broader identity publication must continue through
the existing native producer and its own evidence/retention rules.
