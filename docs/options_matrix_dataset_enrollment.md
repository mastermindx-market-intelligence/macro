# Options Matrix dataset enrollment

`config/dataset_registry.yml` declares four native contracts for the existing
Matrix display path. These records describe verified data and its static lineage;
they do not install data or enable an authenticated action policy.

| Internal dataset ID | Layer | Produced qualification |
| --- | --- | --- |
| `options.thetadata.oi.normalized` | L1 | Observed SPY/2026 OI Parquet, 2,562,317 rows, 10,284,056 bytes |
| `options.thetadata.eod.normalized` | L1 | Observed SPY/2026 EOD Parquet, 2,598,198 rows, 38,765,944 bytes |
| `options.thetadata.greeks.normalized` | L1 | Observed SPY/2026 Greeks Parquet, 2,598,198 rows, 191,187,297 bytes |
| `options.matrix.thetadata.derived` | L3 | Accepted exact SPY Matrix artifact for source session 2026-10-15 |

Each ID and schema-contract version `1.0.0` is a new internal technical
declaration. Neither is a vendor contract identifier, historical source version,
or input digest. The composite has exactly the three named input edges. The
whole-output schema includes cells, levels, heat seeker, reliability and build
metadata; selecting a metric does not narrow the delivered payload.

## Producer and store evidence

The input metadata observation at `2026-10-24T06:14:36.281781+00:00` found all three
SPY/2026 Parquets stable and nonempty under the actual root
`/Users/chriswong/theta-ops-wt/data/thetadata_eod`. The retained receipt is identified
by SHA256 `41175e2eb115745a1564f2c7899f1a90898787ee81d63003820aa97ba67a82b9`.
Its Arrow physical schemas are declared directly in the registry: 6 OI columns,
13 EOD columns and 26 Greeks columns. Registry storage paths use the existing
`THETADATA_STORE` convention consumed by `engine/thetadata_store.py`; they are
scoped to the observed SPY/2026 stores and do not assert another host installation.

The source chain is `collectors/thetadata.py` normalization through the existing
backfill/top-up writers, then `engine/thetadata_store.py` reads and
`engine/options_matrix.py::build_matrix`, published/retained by
`scripts/build_options_matrix.py`. The normalizers retain only available response
columns. In particular, current optional OI `timestamp`/acquisition and Greeks
`timestamp`/`underlying_timestamp`/acquisition fields were absent from the observed
Parquets, so the physical contracts do not claim them.

The metadata receipt explicitly reports `historical_input_bytes_bound=false`,
`data_known_at_claim=null` and `runtime_writes=false`. It does not demonstrate that
the observed mutable source stores reconstruct the Oct15 output. Source-date
labels, build time, file mtime and observation time are not historical
first-availability clocks. Input contracts therefore declare no invented
`published_at` or `ingested_at` clock. The derived composite declares `derived`.

## Accepted historical composite

The accepted observation `options3d-oct15-identity-selection-20261019` reports:

- Source session `2026-10-15`, SPY SHA256
  `801db740f30aa95aa3613f26962d33cf4e7ccc240c38ddef554a110b2b699e8e`,
  643598 bytes, 2795 cells, equal local head/history and remote head/history.
- Native identity and selection both `RESOLVED`, matching that exact
  session/hash/version, vendor `thetadata` and security `SEC:US-ARCX-SPY`.
- Exact selection SHA256
  `b6e05074c09c86a5e014360a528b98324b3e8c3f8c18180563445ab5478c8228`:
  primary expiry Oct15, strike 620, call; chain/volume/all/all/3d view.

This accepted historical artifact supports the bounded composite `PRODUCED`
qualification. It does not assert current producer health or API deployment.
No daily host re-proof is required merely to reuse accepted unchanged evidence.
The intended initial action-policy source session is Oct15 only; the static
registry does not itself enforce action-session coverage.

## Commercial provenance and executable policy are separate

Chairman ruling
`DEC:COMMERCIAL-DATA-RIGHTS-CHAIRMAN-ATTESTATION-20261023`, issued directly in
Research Factory root `01a1333c-a475-7052-95a8-72a88eb8c17b`, approves commercial
rights for ThetaData options. The assigned Matrix ruling explicitly applies it
to acquisition, internal computation and distribution of the complete derived
Matrix to the assigned authenticated customer. All four rows declare each of
`purchase_access`, `internal_computation` and `redistribution` independently;
the composite inherits no grant from its inputs. No vendor contract ID is claimed,
and no contract upload or repeat commercial approval is required.

The registry permits DEC evidence pointers. The stricter
`options_source_use._shared_evidence_pointer` intentionally cannot resolve
DEC/DSC pointers and refuses `evidence_unresolvable`. This remains expected after
contract enrollment. A configured `evidence_sha256` alone cannot activate these
DEC-only rows.

For a later authorized action, complete the existing closed JSON policy with the
actual named principal, issuer, token session ID/auth epoch, customer identity,
Oct15 source-session scope, deliberately authored policy issue/knowledge time,
finite evaluation window and full-payload rights rationale. Then explicitly bind
each required composite-right evidence pointer to that same exact JSON policy
file under an allowed repository root, retaining the Chairman ruling as its
evidence provenance. Compute the policy digest and the registry digest **after**
that pointer change and supply them through the existing runtime config.
This pointer-binding step is still outstanding; it is not a new commercial
approval. No incomplete policy/config template or principal/session is installed
by this source change.

The real runtime still needs the exact immutable Matrix bytes and applicable
canonical identity files at the intended installation. Contract/DAG validation
is not action admission, deployment, independent review, Save authorization,
or live authenticated display proof. Existing review and effect holds remain.

## Regression scope

The existing `tests/test_options_matrix_context.py` suite exercises tracked
contracts against synthetic captured metadata, malformed/missing input refusal,
and DEC-only evidence refusal. These tests read repository configuration only;
they do not open raw stores, reconstruct the accepted artifact or authenticate a
user. Global registry and registry-consumer tests validate additive compatibility.
