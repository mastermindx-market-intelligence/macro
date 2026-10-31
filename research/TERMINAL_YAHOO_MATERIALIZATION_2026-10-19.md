# Terminal direct-Yahoo materialization — Data OS clarification, 2026-10-19

Status: implementation contract for the Returns Intelligence source integration.
Declared before judging the new binder's test or production results.
Owner baseline: Macro `97261c2a319e62faec05690c04e6fae180540235`.
Consumer baseline: Terminal `4a418f530ff0482b6e518ec98a6d12dc3dee42b8`.

## Reference evidence: what the adapter records and what the leaf refuses

The leaf has no clock and no I/O. The adapter reads the exact two reference
files once per snapshot, records their actual current ``read_at`` (an
ISO-8601 instant in UTC, passed verbatim), hashes the bytes, and re-reads the
same files; a byte-different second read during one snapshot returns
``MATERIALIZATION_REFERENCE_CHANGED`` and prevents binding. This detects a
change during the read; it does not prove an atomic publication generation.
The leaf never derives a reference age, a stale/fresh verdict, or an identity
publication generation. The reference dict carries only
``files_sha256`` (hashes of the two files actually read), ``read_at`` (the
adapter's recorded instant, verbatim), ``generation_id=None``,
``generation_attested=False``, and ``historical_availability="UNATTESTED"``.
No upstream registry row, no historical availability window, no action
revision set, and no point-in-time universe are admitted here. Reference read
time is recorded; upstream freshness and history are unavailable.

## Decision and scope

D00.D3 already admits Yahoo `auto_adjust` history as a TRADJ vendor total-return
proxy for clearly labeled performance and attribution. D00.A1 includes the
mixed-source Terminal output. The missing contract is the binding of Terminal's
own fresh Yahoo observation to its actual per-symbol output. This addition
implements that existing purpose; it does not change adjustment or admission law.

The Data OS-owned pure function in `lib/dataos/terminal_materialization.py`
defines the direct-Yahoo variant. Terminal's existing nightly invokes that
function for its own observed source and writes its returned view alongside the
same bars. Terminal does not infer basis from a vendor label, price shape, or
Macro's unrelated parquet contract.

C04 remains the sole writer of Macro's `data/stocks/_view_contract.json`.
The existing `terminal_daily_ohlc_contract_v1()` Macro-store factory is unchanged.
The direct observation has no invented upstream registry row and no self-lineage
edge. Its output remains `terminal.bars.daily.ohlc_json`; the registry retains
its cross-repository PROPOSED rule and existing rights fields.

## Required binding

A fresh observation must name the actual producer, source request including the
requested Yahoo symbol, daily interval, auto-adjust setting, adapter version,
observation time and provider-local session-date convention. The binder checks
the complete six-column rows and the observation's content/coverage claim.

Resolve the output symbol in the canonical `store` namespace and the actual
request symbol in `yahoo_fetch`, using the existing VendorAliasTable reader.
Both must resolve to one same stored security with one active US listing in
XNYS/XNAS/XASE/ARCX. The historical `yahoo` namespace is not the fetch namespace;
same-spelled strings do not establish identity. Missing, ambiguous, superseded,
out-of-scope or conflicting identity evidence refuses. The injected
listing-key parser must expose ``country`` and ``mic``; a malformed or
non-object return is a typed ``MATERIALIZATION_IDENTITY_UNRESOLVED``.

Record the actual producing source version, the loaded owner module version,
the exact reference files read, and their content hashes. A hash describes
content identity, not independent production acceptance. Do not invent an
identity generation, corporate-action revision set, historical availability or
point-in-time universe. CURRENT, non-executable TRADJ proxy semantics and
unattested generations remain explicit.

## Portable content identity: dataos.terminal_ohlc.rows.v1

The normalized numeric row codec is normative in the owner leaf:

1. ASCII bytes `dataos.terminal_ohlc.rows.v1\n`.
2. An unsigned 32-bit big-endian row count, bounded to 30,000.
3. In original order, each row's ten ASCII ISO-date bytes followed by five
   IEEE-754 binary64 big-endian values: open, high, low, close, volume.

Rows must contain exactly six fields, strictly increasing well-formed ISO
calendar dates (the codec enforces ISO calendar shape and order, not
exchange-calendar membership), finite positive OHLC with valid bounds, and
nonnegative integral volume no larger than 2^53-1. Negative-zero volume
normalizes to positive zero. Reject Boolean/string numeric coercions,
duplicate or reordered dates, non-finite values and unsupported row shapes.
The digest is SHA-256 of these bytes.

This binds the exact normalized row values consumed by Terminal; it does not
claim to be a hash of the original Yahoo response. Python compact JSON and
JavaScript JSON.stringify are not interchangeable canonical encodings. Keep
the earlier observation JSON digest distinctly versioned when retained.

## Consumer and refresh rules

Verify the whole published row array before filtering, sorting or transforming
it for returns. Browser and server use the same codec golden fixtures. A
missing, unsupported, mismatched or unverified binding cannot enable qualified
direction/acceleration states. Content and refusal evidence participate in
cache validity; no serialized verified Boolean is accepted as verification.

A no-change reuse preserves the original observation and view, without
restamping their time. Any append, replacement, trim, correction or reorder
invalidates the direct-Yahoo binding until the authorized full materializer
binds the resulting output. Polygon overlap tolerance is not permission to
extend a Yahoo content binding. The old provenance may be inspected but cannot
remain an active qualification. Refusal evidence must survive later refreshes.

## Direct readout divergence and evidence_mode differences

The direct-Yahoo binder agrees with ``engine.price_ladder.terminal_daily_ohlc_contract_v1()``
on the shared invariants the owner agreement test pins: ``schema``,
``purpose``, ``identity_namespace``, ``venues``, ``field_units``,
``store_vendor``, and the five ``adjustment_reference`` fields except the
deliberately specific ``readout``. The direct variant intentionally diverges
on three ``evidence_mode`` fields and on the adjustment ``readout``:

| field                     | engine factory (Macro-store)            | direct-Yahoo binder                     |
| ------------------------- | --------------------------------------- | --------------------------------------- |
| ``adjustment_reference.readout`` | ``vendor-adjusted — not a printed price`` | ``vendor total-return proxy — not a printed price`` |
| ``evidence_mode.clock``        | ``"ingested_at"``                    | ``"observed_at"``                       |
| ``evidence_mode.registry_row`` | ``"equity.bars.daily.stocks"``       | ``null``                                |
| ``evidence_mode.code_version`` | ``null``                             | passes through ``owner.code_version``   |

The ``output_registry_row`` (``terminal.bars.daily.ohlc_json``),
``dependency_generation_ids`` (empty list), ``generation_attested``
(``False``) and ``mode`` (``CURRENT``) keys are shared. The factory stays
the Macro-store view-contract source of truth; the direct variant is a
separate observation source for the same dataset row and never widens the
factory's meaning. The direct binder rejects missing or malformed reference
inputs; the existing factory and C04 emitter retain their separate contracts.

## Codec ownership and existing regression coverage

This leaf at ``lib/dataos/terminal_materialization.py`` owns the canonical
``dataos.terminal_ohlc.rows.v1`` codec and its SHA-256 digest. The same
bytes and digest are pinned as regression goldens against the consumer
implementations already present in Terminal at the pinned commit
``0b3c47df56d5063884e9f542e21f8ca5976f2f6f``:

- JavaScript regression guard:
  ``terminal/lib/__tests__/terminalMaterialization.test.ts`` — uses
  ``lib/__tests__/terminalMaterialization.fixture.json`` and asserts the
  portable ``encoded_hex`` / ``bars_sha256`` / ``portable_encoded_hex`` /
  ``portable_sha256`` values produced by this leaf.
- Browser end-to-end guard:
  ``terminal/e2e/returns-intelligence.spec.ts`` — installs the same golden
  via ``lib/__tests__/terminalMaterialization.fixture.json`` and verifies
  the owner golden rows before qualifying the history, then rejects a
  changed content variant.

The normative golden remains ``tests/terminal_materialization_golden.json``
in Macro. Terminal retains its matching fixture and consumer guards; no
additional JavaScript implementation or CI plane is added to Macro.

## Acceptance and remaining product boundary

Hermetic evidence must cover the accepted fresh source, namespace mismatch,
unknown/ambiguous/superseded listing, unsupported request, wrong digest,
changed non-close OHLC, append, malformed row, missing reference pair,
changed reference pair, malformed parser return, tzdata absent
(``MATERIALIZATION_CLOCK_INVALID``), verbatim ``read_at`` round-trip, the
owner agreement test, and preserved reuse. Include portable Python/JavaScript
byte and digest golden fixtures.

Delivery additionally requires merged owner code, its installed consumer,
an actual artifact emitted through the existing nightly, and a live Returns
read whose binding matches that artifact. This document alone proves none of
those effects.

Descriptive qualification does not admit predictions. The frozen first NVDA
research candidate lost to the class-prior baseline at all three horizons;
independent canonical model admission remains absent. Probability output stays
withheld. No collector, data store, identity allocator, registry, publisher,
evaluation plane or production scheduler is added.
