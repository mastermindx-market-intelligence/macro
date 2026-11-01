# Private dated-reference Plan consumer

`POST /api/options/plan/expiry` accepts only `options.plan_expiry_request/v1`:
`schema`, the existing `options_plan_draft.v1` `draft`, `spots` (1–1001 bounded
hypothetical expiry prices), and exact `payoff_basis` `{kind:
"hold_to_expiry_intrinsic", expiration: "YYYY-MM-DD"}`. The server derives the
incumbent six-field exact contract identity from each pin and never accepts
source contexts, observations, endpoint URLs, credentials, hashes, clocks or
source grants from the browser.

The explicitly private endpoint nests in the existing hub router, with its own
bearer dependency. `app.options_auth.resolve_entitled_options_principal` reuses
the same uncached configured Supabase authentication and billing read as the
existing Options use consumer. `_fresh_product_allowed` contains that existing
predicate once: `terminal_live_options`, unlimited tier, or the established
operator overlay. Anonymous, missing/invalid subject, expired session, denied
entitlement and billing outage remain closed. No matrix OptionUseRequest,
admission or source-use receipt is fabricated. Explicit HTTP success/error
responses use private, no-store headers.

The API performs **zero provider requests**. The intended API process has no
provisioned reference key. Its first source is one exact, privately installed,
principal-qualified original reference observation. `OPTIONS_PLAN_REFERENCE_PATH`
and `OPTIONS_PLAN_REFERENCE_SHA256` come only from service configuration; they
are not an upload API or source registry. `read_private_reference` holds each
parent directory without following symlinks, checks an owned 0700 receiving
leaf and owned single-link 0600 regular file, bounds reads to 256 KiB, rechecks
inode/size/times/ownership against the named file, verifies the installation
hash, and rejects duplicate/nonfinite JSON, unqualified provenance and future
capture clocks. The hash proves consistency; the accepted original-source
custody and private installation qualify the artifact. A parsed observation
never becomes a replay of original provider response bytes.

The bridge selects each exact leg uniquely from the genuine original list
receipt, or validates the original exact-single response. No missing leg,
expiry, adjustment, query scope or contract may borrow a latest/best match.
`reference_as_of`, original `reference_observed_at`, and calculation `known_by`
remain separate. Source pin clocks remain unchanged. No arbitrary wall-clock
age rule invalidates an explicitly dated hypothetical; a future expiry can use
matched dated terms while current-term qualification remains false. The reader
claims neither current chain coverage nor historical first availability.

`scripts.install_options_plan_reference.py` is a separately bounded installer
for `/var/lib/macro-api/options_plan/reference.json` under the already existing
API state namespace. It leaves the GEX-specific P052 descriptor and installer
unchanged, reusing only its incumbent bounded SSH pipe utility. The receiving
account/namespace must match current qualified facts; the first authorized
install creates the leaf 0700 and exact file 0600, follows no symlink component,
uses create-only link plus fsync, verifies the held receiving inode, and refuses
overwrite. No daemon, source registry, store, Save or runtime flag is added.
The local original operation receipt is exclusively created and fsynced before
transport; TRANSPORT_STARTED is durable before one arrival call. A missing or
bad return becomes EFFECT_UNKNOWN, including a failure recording final success.
An existing receipt is never replayed. `inspect` only reads the same destination
and does not self-clear the original receipt's custody.

Runtime activation requires the exact principal-accepted artifact/source and
installation proof, ordinary configured path/hash/enable flag, and independent
review of this auth/private-install risk. A boolean flag alone authorizes no
acquisition or unbounded request budget. Source tests use only fixtures/private
temporary directories and perform no provider, SSH, payload, config or restart
effect. Named-provider commercial rights are approved by Chairman attestation;
this is not a new licensing gate. Real endpoint denial, unsettled acquisition
and human consent remain on their original carriers.

The result uses `engine.options_payoff.expiry_payoff`, authored side/quantity/
premium, qualified ordinary SPY/QQQ terms, one root and one expiry. It is a dated
conditional intrinsic curve over hypothetical underlying prices. Early exercise,
assignment and fees are excluded. It is not mark-to-market, fixing/settlement,
a fill, trading authority or an actual outcome. The Investigation owner keeps
the unchanged Plan payload for durable Save/reopen; no storage is added here.

The private result also reports the exact retained reference root, contract count and
expiry set. This bounded metadata remains available when an exact selection is
unpriced, so the consumer can explain the dated pilot coverage without exporting
paid contract rows or substituting another identity. It is not current-chain coverage.
