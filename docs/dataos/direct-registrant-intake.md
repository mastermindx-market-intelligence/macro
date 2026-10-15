# Direct registrant intake for existing ETF probes

The security-master writer can use a newly captured SEC submissions observation when the weekly company-ticker map lacks an ETF trust. This explicit lane supports SPY, QQQ and SMH. It supplies registrant independence evidence to the existing pending-transition fence; it does not create an Options-root alias or assign an ETF issuer group.

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

## Retention and current support

The existing `_receipt.json` retains the admission decision, source digests, capture clocks and, for a refusal, the canonical writer's actual cause. Explicit resubmission of a retained symbol refuses. Older prospective-reference decisions are immutable; an unsettled older request cannot borrow the new observation.

A retained BOUND decision is historical. `direct_registrant_rederivation` separately reports CURRENT, LISTING_UNAVAILABLE, RETIRED or REFUSED for this build. Later runs preserve the stored ID and require current listing support to rederive it; a missing listing therefore reaches ordinary loss detection and the pending-transition fence. Missing or conflicting stored IDs cannot be re-minted, and tombstones cannot be revived.

The file loader rejects static symlinks/nonregular files and checks sizes, but does not provide descriptor-bound protection against hostile concurrent local replacement. Publication retains the incumbent sequential multi-file behavior; this lane does not introduce atomic transactions or a parallel registry. An actual source-supported Options-root relation, current rights and entitlement, exact saved-snapshot reopening and the consumer integration remain separate requirements. IDX identity is separate from SEC identity.
