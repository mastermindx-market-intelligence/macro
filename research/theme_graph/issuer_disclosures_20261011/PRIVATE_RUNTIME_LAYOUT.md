# Native Company Intelligence runtime layout

This is the GMI source owner's bounded installation contract for the incumbent
Macro API deployment owner. It authorizes no alternative updater, service,
bucket, credentials or publication replay. Ordinary release and source
reconciliation precede installation of this implementation.

The fixed production root is `/var/lib/macro-company-intelligence`.

| Relative path | Contents | Serving API | Attended producer |
| --- | --- | --- | --- |
| `state/current.json` | Canonical versioned current manifest reference | Read only, after authentication and entitlement | Exact-predecessor CAS |
| `state/generations/<sha256>.json` | Immutable DERIVED owner manifest, decision/member references and original clocks | Bounded read only | Conditional create |
| `artifacts/company_intelligence/issuer_disclosures/v1/` | Native edition/fact objects and winning revision bindings | Bounded read only, after source admission | Existing LocalStore conditional writes |
| `publisher/source/<source-sha256>.html` | Exact retained original source, never redistributed | Inaccessible | Bounded no-follow read after publication admission |
| `publisher/operations/<operation-id>.json` | Immutable single-invocation intent; separate `<operation-id>.result.json` outcome | Inaccessible | Exclusive reservation before effects; no blind retry |

All roots are real directories, not symlinks, owned by the existing approved
privileged deployment/producer account. Roots and directories use 0700, regular
files 0600, and producer umask 0077. The existing API currently runs as root; that
does not supply write separation. Its existing systemd unit must mount `state`
and `artifacts` **nonoptional read-only** and make `publisher` **inaccessible**.
The attended producer runs outside the API mount namespace. Provision required
empty roots before the existing unit's verification/restart sequence; do not
create a current pointer, manifest or fact as a provisioning shortcut. Preserve
all existing unit hardening and other owner paths.

`state` is bounded decision/current-selection metadata, not raw source or private
artifact bodies. Authentication and actual feature qualification precede access
to it. Source preflight may read it and committed authority records, but must not
retrieve retained source, reviewer material or native artifacts or construct the
artifact Store. The API gets `ReadOnlyLocalObjects` capabilities with no mkdir or
write methods; OS mount restrictions must independently enforce this boundary.

The source-owner provider reads installed protected Macro decision records and
the incumbent current identity owner on every resolution. The pointer can select
only exact manifest/member/decision bindings. Source, purpose, identity or
correction changes revoke serving even while old files remain. Historical
requests refuse. This metadata projection does not create a new rights registry.

The existing source owner publishes through `publish_generation`, using the exact
retained source only after admission. It verifies native winning bindings and
final authority, creates the immutable manifest, then CAS-promotes `current.json` only for a
source-owned PRODUCED dataset. PROPOSED staging returns verified members/manifest
without a pointer; its actual receipt must justify the protected adoption amendment
before a fresh adoption-bound serving intent.
Lost acknowledgements are reconciled by readback of the same write. Unknown
effects and CAS conflicts prohibit automatic retries. No public R2 fallback,
Research/FF credential inheritance or source-body HTTP capability is present.

Installation acceptance requires exact released source, provisioned modes and
mount separation, one retained-source publication receipt, immutable member and
current-pointer readback, fresh authenticated v2 positive/refusal, and matching
F04 browser/machine references. Local fixtures or this contract do not satisfy
that acceptance.
