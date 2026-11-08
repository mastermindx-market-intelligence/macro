"""GMI -> Data OS identity resolution bridge (V4-D2A frozen contract).

Contract: ``research/prophet_v4/d2/D2A_FROZEN_CONTRACT_2026-08-18.md``. Sol's D2A
ruling makes the Data OS identity spine (``data/reference/security_master.parquet`` +
``vendor_aliases.parquet``, read through ``lib.dataos.identity``) the estate's ONLY
exact issuer/security/listing identity authority. The GMI theme graph keeps its own
topology node ids (``co:<market>:<SYMBOL>[#epoch]`` — a graph-topology concern, never
recycled, per ``engine/theme_graph/identity.py``). This module is the BRIDGE between
the two: a re-derived side-car, ``data/theme_graph/identity_resolution.parquet``, that
answers "which Data OS security does this GMI company node name" — never a second
allocator, never a rewrite of either spine.

ONE ROW PER COMPANY-KIND NODE (``kind == "company"``), including refusals. `etf`/other
kinds carry no rows in v1. The row is re-derived on EVERY build (the capability-rule
pattern, never a node column — node rows are keep-first write-once, and an identity
resolution written once would be a one-way ratchet the master's own coverage growth
could never repair).

THE ALGORITHM (§4, ordered, first match wins) is deterministic and carries NO ticker
equality fallback: a symbol absent from the master AND every vendor alias space is
structurally incapable of becoming RESOLVED. Alias resolution goes ONLY through
``lib.dataos.identity.VendorAliasTable.from_records(...).resolve(vendor, symbol,
on=resolution_asof)``, queried across EVERY vendor space the committed alias table
carries — this module is the FIRST real consumer of that reader (Scout A finding 1).

``source_native_symbol`` is PARSE PROVENANCE ONLY — the symbol segment as split out of
the node id — and is NEVER a join key. The only sanctioned resolution path is this
module's reader API (``read_identity_resolution`` / ``resolve_graph_node_identity``);
nothing downstream may re-derive or re-match on ``source_native_symbol`` directly.

TWO READ PATHS (§5): ``read_identity_resolution()`` for the bulk latest-generation
view (the ``read_capability`` pattern — max ``computed_at`` per node), and
``resolve_graph_node_identity(node_id, asof=...)`` for one node, either from the
persisted sidecar (``asof=None``) or re-run PURELY over the committed inputs at an
explicit historical date (no store write, no second store). Both raise
``UnknownGraphNodeError`` for a node_id the graph itself does not carry — a known node
never returns an untyped/None resolution.

TWO-CLOCK LAW, CURRENT vs HISTORICAL mode (§4 amendment, post-adversarial-review
2026-08-18 — see D2A_FROZEN_CONTRACT_2026-08-18.md AMENDMENTS): the materialization
path (``derive_rows``, driven by a generation's ``belief_time``) resolves in CURRENT
mode — rule 6 may consult every vendor alias space, including the unconditionally-open
current-catalog rows (``store``/``yahoo_fetch``) that answer "what string do I use
TODAY for a bar of any date" (``AliasRow`` docstring, ``lib/dataos/identity.py``).
``resolve_graph_node_identity(node_id, asof=...)`` with an EXPLICIT ``asof`` instead
resolves in HISTORICAL mode: rule 6 may consult ONLY DATED alias rows (``valid_from``
or ``valid_to`` non-null) of the HISTORICAL vendor spaces as historical-naming
evidence — a current-catalog SPACE (``store``/``yahoo_fetch``) is never allowed to
answer a historical-naming question, because it was never given one; since 2026-08-28
those spaces may carry dated rows across a ratified key migration, so the exclusion
is by vendor identity (``_CURRENT_CATALOG_VENDORS``), not row shape.
Rule 5 (exact inception-code match) is asof-invariant in BOTH modes: the master's
``inception_code`` is the security's own canonical symbol, minted once and stored, so
it never depends on the query date.

ISSUER AXIS (V4-D2B1, 2026-08-19; FIX 8 / m3 amendment).  ``issuer_id`` is copied from
the master's own issuer axis ONLY WHEN the master row's ``issuer_state`` is
``RESOLVED`` — this module allocates nothing and repoints nothing, and never smuggles
an unevidenced or disputed value into the graph bridge as if it were confirmed
identity.  A RESOLVED sidecar row's ``issuer_id`` may be SHARED by more than one
company node's security (``co:us:GOOG`` and ``co:us:GOOGL`` both resolve to the same
``ISS:US-XNAS-GOOG``, per the master's CIK-evidenced grouping), while
``security_id``/``listing_key`` stay per-node distinct.  A RESOLVED sidecar row's
``issuer_id`` is null whenever the master's issuer_state for that security is
anything OTHER than ``RESOLVED`` — ``NO_ISSUER_EVIDENCE`` (a legacy/new master row
with no CIK evidence yet), ``AMBIGUOUS``, ``EVIDENCE_CONFLICT``, or
``DEFERRED_IDENTITY_EXCEPTION`` all null the sidecar issuer_id the same way.
``security_id``/``listing_key`` stay non-null regardless of the issuer axis, because
exact security/listing identity is unaffected by whether an economic issuer has been
evidenced.  ``scripts/check_theme_graph_contracts.py``'s state<->ids biconditional
(F3a) is amended accordingly: RESOLVED requires ``security_id``/``listing_key``
ALWAYS, and requires ``issuer_id`` iff the master's own issuer_state for that
security is ``RESOLVED`` (a non-null issuer_id on any other master state is a
breach — the bridge would be disagreeing with its own source of truth).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from lib import config
from lib.dataos.identity import VendorAliasTable

from . import identity as graph_identity
from . import store

log = logging.getLogger(__name__)

#: Contract id — the ``schema`` column's constant value.
SCHEMA_ID = "gmi.identity_resolution/v1"

#: Closed vocabulary, §4/§3.
RESOLUTION_STATES: tuple[str, ...] = (
    "RESOLVED", "INVALID_SOURCE_ID", "UNSUPPORTED_MARKET",
    "DEFERRED_IDENTITY_EXCEPTION", "ENTITY_TYPE_CONFLICT", "AMBIGUOUS", "NOT_IN_MASTER",
)
JOIN_METHODS: tuple[str, ...] = ("master_inception_exact", "vendor_alias", "refused")

#: Where the Data OS spine lives, relative to the theme graph's own ``data_dir``
#: (``lib.config.data_dir()`` in production; a fixture root in tests) — see
#: ``scripts/build_security_master.py`` for the producer.
REFERENCE_SUBDIR = "reference"
MASTER_FILE = "security_master.parquet"
ALIASES_FILE = "vendor_aliases.parquet"
RECEIPT_FILE = "_receipt.json"


class UnknownGraphNodeError(KeyError):
    """``node_id`` is not a node the theme graph carries at all.

    Deliberately NOT raised for a company node the sidecar has not yet resolved
    (that is a resolution_state, e.g. ``NOT_IN_MASTER``) — only for a node_id the
    graph's own ``nodes.parquet`` has no row for.
    """


# ---------------------------------------------------------------------------
# Master inputs — loaded once per materialization (§4)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MasterInputs:
    """The Data OS spine, read once and indexed for repeated per-node lookups."""

    master_by_code: dict[str, dict] = field(default_factory=dict)
    master_by_security: dict[str, dict] = field(default_factory=dict)
    alias_table: VendorAliasTable = field(default_factory=VendorAliasTable)
    vendors: frozenset[str] = frozenset()
    identity_exceptions: dict[str, dict] = field(default_factory=dict)
    generated_at: str | None = None
    symbol_directory_snapshot: str | None = None
    code_version: str | None = None


def _as_bound(value: object) -> date | None:
    """A stored alias valid_from/valid_to bound as a plain ``date``, or None (open).

    ``data/reference/vendor_aliases.parquet`` stores these as plain ``datetime.date``
    objects or None (verified against the committed artifact); this also tolerates a
    ``pandas.Timestamp``/NaT/NaN, which a re-read through a different pandas path can
    hand back, so the normalisation is defensive rather than assumed.
    """
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        return None if pd.isna(value) else value.date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text or text.lower() in {"nat", "nan", "none", "<na>"}:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _as_date(value: str | date) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])


def load_master_inputs(data_dir: Path | None = None) -> MasterInputs | None:
    """Load the committed Data OS spine ONCE. None if ``data/reference/`` is absent
    or unreadable — a sparse checkout or a pre-DOS-1.1 state, never fatal (the theme
    graph is a display-tier plane; §9 of the module docstring)."""
    root = Path(data_dir) if data_dir is not None else config.data_dir()
    ref_dir = root / REFERENCE_SUBDIR
    master_path = ref_dir / MASTER_FILE
    aliases_path = ref_dir / ALIASES_FILE
    receipt_path = ref_dir / RECEIPT_FILE
    if not (master_path.exists() and aliases_path.exists() and receipt_path.exists()):
        return None
    try:
        master = pd.read_parquet(master_path)
        aliases = pd.read_parquet(aliases_path)
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 — an unreadable master degrades, never fatal
        log.warning("identity_resolution: security master unreadable (%s)", exc)
        return None

    records = []
    for r in aliases.to_dict("records"):
        if r.get("alias_kind") == "occ_root":
            records.append(r)  # preserve the exact forward relation and its clocks
            continue
        records.append({
            "alias_kind": r.get("alias_kind"),
            "attempt_id": r.get("attempt_id"),
            "alias_family_id": r.get("alias_family_id"),
            "alias_revision_id": r.get("alias_revision_id"),
            "vendor": str(r["vendor"]),
            "vendor_symbol": str(r["vendor_symbol"]),
            "security_id": str(r["security_id"]),
            "valid_from": _as_bound(r.get("valid_from")),
            "valid_to": _as_bound(r.get("valid_to")),
            # Preserve native evidence fields when loading the complete table;
            # this does not enable date-only native lookups in the graph.
            "known_at": r.get("known_at"),
            "evidence_sha256": r.get("evidence_sha256"),
            "binding_sha256": r.get("binding_sha256"),
        })
    table = VendorAliasTable.from_records(records)

    master_by_code: dict[str, dict] = {}
    master_by_security: dict[str, dict] = {}
    for r in master.to_dict("records"):
        # V4-D2B1-R1 §6.1: a security-axis-superseded row (a tombstone —
        # security_state non-null, e.g. SUPERSEDED_DUPLICATE_MINT) is excluded from
        # BOTH join indices entirely — every join index excludes superseded master
        # rows. It never becomes rule 5's inception-code hit and never becomes rule
        # 6's vendor-alias resolution target (the alias table itself never emits a
        # row pointing at a superseded id post-repair, but this is belt-and-suspenders
        # against any committed row this builder has not yet re-derived). `pd.isna`
        # catches both the missing-column (pre-repair master) and the NaN-cell shapes.
        security_state = r.get("security_state")
        if not pd.isna(security_state) and str(security_state).strip():
            continue
        # V4-D2B1 FIX 8 (m3): issuer_id is copied into the sidecar ONLY when the
        # master row's OWN issuer_state is RESOLVED — CIK evidence actually backs the
        # link. Any other state (NO_ISSUER_EVIDENCE, AMBIGUOUS, EVIDENCE_CONFLICT,
        # DEFERRED_IDENTITY_EXCEPTION, or a pre-D2B1 row with no issuer_state column
        # at all) means the sidecar's own issuer_id is null — a legacy/unevidenced/
        # disputed VALUE must never leak into the graph bridge as if it were
        # confirmed identity. security_id/listing_key are UNAFFECTED — exact
        # security/listing identity never depended on the issuer axis.
        # ``pd.isna`` catches both the missing-cell shapes pandas can hand back
        # (``None`` and a genuine ``float('nan')``) for a nullable string column that
        # also carries real strings.
        raw_issuer = r.get("issuer_id")
        issuer_state = r.get("issuer_state")
        issuer_is_resolved = not pd.isna(issuer_state) and str(issuer_state) == "RESOLVED"
        issuer_evidenced = (
            issuer_is_resolved and raw_issuer is not None and not pd.isna(raw_issuer)
        )
        row = {
            "security_id": str(r["security_id"]),
            "issuer_id": str(raw_issuer) if issuer_evidenced else None,
            "listing_key": str(r["listing_key"]),
        }
        code = str(r.get("inception_code") or "").strip().upper()
        if code:
            master_by_code[code] = row
        master_by_security[row["security_id"]] = row

    exceptions: dict[str, dict] = {}
    for exc_row in receipt.get("identity_exceptions") or []:
        key = str(exc_row.get("key") or "").strip().upper()
        if key:
            exceptions[key] = dict(exc_row)

    return MasterInputs(
        master_by_code=master_by_code,
        master_by_security=master_by_security,
        alias_table=table,
        vendors=frozenset(row.vendor for row in table.rows),
        identity_exceptions=exceptions,
        generated_at=receipt.get("generated_at"),
        symbol_directory_snapshot=receipt.get("symbol_directory_snapshot"),
        code_version=receipt.get("code_version"),
    )


def _master_meta(inputs: MasterInputs | None) -> dict:
    if inputs is None:
        return {"master_generated_at": None, "master_symbol_directory_snapshot": None,
                "master_code_version": None}
    return {
        "master_generated_at": inputs.generated_at,
        "master_symbol_directory_snapshot": inputs.symbol_directory_snapshot,
        "master_code_version": inputs.code_version,
    }


# ---------------------------------------------------------------------------
# ETF entity-type conflicts (§4 rule 4) — same-generation company/etf symbol clash
# ---------------------------------------------------------------------------

def _etf_symbols(nodes: list[dict]) -> frozenset[str]:
    """Every ``etf``-kind node's symbol, from the SAME generation's node list."""
    out: set[str] = set()
    for n in nodes:
        if str(n.get("kind")) != "etf":
            continue
        try:
            ext = json.loads(n.get("external_ids") or "{}")
        except Exception:  # noqa: BLE001 — malformed external_ids is not fatal here
            continue
        sym = ext.get("symbol")
        if sym:
            out.add(str(sym).strip().upper())
    return frozenset(out)


# ---------------------------------------------------------------------------
# Node-id parsing — ONE clean split (§3: no shared parser exists; do not copy the
# hand-rolled ones at check_theme_graph_contracts.py:542-544 / capability.py:144)
# ---------------------------------------------------------------------------

def _best_effort_market(node_id: str) -> str | None:
    parts = str(node_id or "").split(":")
    if len(parts) >= 2 and parts[1] in graph_identity.MARKETS:
        return parts[1]
    return None


def _best_effort_symbol(node_id: str) -> str | None:
    parts = str(node_id or "").split(":", 2)
    if len(parts) >= 3:
        sym = parts[2].split("#", 1)[0].strip().upper()
        return sym or None
    return None


# ---------------------------------------------------------------------------
# F1 (post-adversarial-review) — cross-market equality guard. A rule 5/6 hit is
# refused, never resolved or marked AMBIGUOUS, if the master row's own listing
# country disagrees with the node's market_scope: the master row is definitively
# another market's security, not a coincidental symbol collision.
# ---------------------------------------------------------------------------

_MARKET_SCOPE_TO_COUNTRY: dict[str, str] = {"us": "US", "cn": "CN", "hk": "HK", "ca": "CA"}


def _cross_market_mismatch_reason(market_scope: str, listing_key: str | None) -> str | None:
    """None if the master row's listing country agrees with ``market_scope``; else the
    refusal_reason text disclosing the collision."""
    expected = _MARKET_SCOPE_TO_COUNTRY.get(market_scope)
    if expected is None or not listing_key:
        return None
    country = str(listing_key).split("-", 1)[0]
    if country == expected:
        return None
    return (
        f"master row listing_key={listing_key!r} belongs to country {country!r}, which "
        f"disagrees with the node's market_scope={market_scope!r} (expected {expected!r}) "
        "— refusing a cross-market identity collision rather than resolving into another "
        "market's security (contract F1 amendment)")


# ---------------------------------------------------------------------------
# F2 (post-adversarial-review) — HISTORICAL-mode alias lookup, two-clock law. Only
# DATED alias rows (at least one of valid_from/valid_to non-null) are historical-naming
# evidence; a fully open row (both bounds null) is a CURRENT-CATALOG space answering
# "what string do I use today for a bar of any date" and is structurally excluded —
# and so is EVERY row of a current-catalog VENDOR, dated or not. The exclusion used
# to be shape-only ("both bounds null"), which was equivalent while current-catalog
# spaces could only emit open rows; since 2026-08-28 the `store` space emits DATED
# rows across a ratified key migration (EQR->VMRK, AMENDMENT ruling 9 / m3), so the
# vendor-identity test below is the law's real boundary: a current-catalog space
# answers "what key does the REPO use", never the market's historical naming, no
# matter how its rows are bounded.
# ---------------------------------------------------------------------------

#: Vendor spaces that model the repo's own current catalog (see
#: scripts/build_security_master.py VENDOR_YAHOO_FETCH / VENDOR_STORE). Their rows
#: are never historical-naming evidence, dated or not.
_CURRENT_CATALOG_VENDORS = frozenset({"store", "yahoo_fetch"})


def _historical_alias_resolve(table: VendorAliasTable, vendor: str, vendor_symbol: str,
                              on: date) -> str | None:
    if vendor in _CURRENT_CATALOG_VENDORS or vendor == "polygon":
        return None  # a current-catalog space was never asked a historical question
    for r in table.rows:
        if r.vendor != vendor or r.vendor_symbol != vendor_symbol:
            continue
        if r.valid_from is None and r.valid_to is None:
            continue  # current-catalog-shaped row — not historical-naming evidence
        if r.covers(on):
            return r.security_id
    return None


# ---------------------------------------------------------------------------
# The algorithm (§4) — one node in, one row out. Deterministic, no fallback.
# ---------------------------------------------------------------------------

def _resolve_node_row(*, node_id: str, resolution_asof: str, inputs: MasterInputs | None,
                      etf_symbols: frozenset[str], computed_at: str,
                      engine_version: str, historical: bool = False) -> dict:
    base = {
        "schema": SCHEMA_ID, "node_id": node_id, "graph_kind": "company",
        "resolution_asof": resolution_asof, "computed_at": computed_at,
        "engine_version": engine_version,
    }
    meta = _master_meta(inputs)
    null_ids = {"issuer_id": None, "security_id": None, "listing_key": None}

    # rule 1 — the node id itself must satisfy the permanent-identity grammar.
    m = graph_identity.COMPANY_ID_RE.match(str(node_id))
    if not m:
        return {
            **base, **null_ids,
            "market_scope": _best_effort_market(node_id),
            "graph_identity_epoch": None,
            "source_native_symbol": _best_effort_symbol(node_id),
            "resolution_state": "INVALID_SOURCE_ID",
            "join_method": "refused",
            **meta,
            "refusal_reason": (
                f"node_id does not match {graph_identity.COMPANY_ID_RE.pattern!r}"),
            "source_receipts": json.dumps({"node_id": str(node_id)},
                                          ensure_ascii=False, sort_keys=True),
        }

    market_scope = m.group(1)
    tail = str(node_id).split(":", 2)[2]
    symbol_part, _, epoch_s = tail.partition("#")
    symbol = symbol_part.upper()
    epoch = int(epoch_s) if epoch_s else 1

    row = {**base, "market_scope": market_scope, "graph_identity_epoch": epoch,
          "source_native_symbol": symbol, **meta}

    # rule 2 — no country/MIC mapping exists for intl.
    if market_scope == "intl":
        return {**row, **null_ids, "resolution_state": "UNSUPPORTED_MARKET",
                "join_method": "refused",
                "refusal_reason": ("market_scope=intl has no country/MIC mapping in the "
                                   "Data OS spine (contract §4 rule 2)"),
                "source_receipts": json.dumps({"market_scope": market_scope},
                                              sort_keys=True)}

    # rule 3 — the master's own operator-ratified fail-closed identity exceptions.
    exc = (inputs.identity_exceptions if inputs else {}).get(symbol)
    if exc:
        status = exc.get("status", "")
        reason = exc.get("reason", "")
        return {**row, **null_ids, "resolution_state": "DEFERRED_IDENTITY_EXCEPTION",
                "join_method": "refused",
                "refusal_reason": f"{status}: {reason}",
                "source_receipts": json.dumps({"identity_exception": exc},
                                              ensure_ascii=False, sort_keys=True)}

    # rule 4 — an etf-kind node in the SAME generation with the same symbol.
    if symbol in etf_symbols:
        conflict_master = (inputs.master_by_code.get(symbol) if inputs else None)
        receipts: dict = {"conflicting_etf_node": f"etf:{symbol}"}
        if conflict_master is not None:
            receipts["master_row_would_otherwise_resolve_to"] = conflict_master["security_id"]
        return {**row, **null_ids, "resolution_state": "ENTITY_TYPE_CONFLICT",
                "join_method": "refused",
                "refusal_reason": (
                    f"etf:{symbol} coexists as an etf-kind node in the same generation "
                    "— machine-visible, no kind rewrite, no pick"),
                "source_receipts": json.dumps(receipts, ensure_ascii=False, sort_keys=True)}

    if inputs is None:
        return {**row, **null_ids, "resolution_state": "NOT_IN_MASTER",
                "join_method": "refused",
                "refusal_reason": ("data/reference/ security master is not present in "
                                   "this checkout"),
                "source_receipts": json.dumps({"master_present": False}, sort_keys=True)}

    # rule 5 — exact: source_native_symbol == inception_code in the master. Asof-
    # invariant in BOTH modes — the master's inception_code is the security's own
    # canonical symbol, minted once and stored (module docstring, two-clock law).
    exact = inputs.master_by_code.get(symbol)
    if exact is not None:
        mismatch = _cross_market_mismatch_reason(market_scope, exact["listing_key"])
        if mismatch is not None:
            return {**row, **null_ids, "resolution_state": "NOT_IN_MASTER",
                    "join_method": "refused", "refusal_reason": mismatch,
                    "source_receipts": json.dumps(
                        {"master_inception_code": symbol,
                         "would_resolve_to": exact["security_id"],
                         "cross_market_collision": True}, sort_keys=True)}
        return {**row, "resolution_state": "RESOLVED",
                "join_method": "master_inception_exact",
                "issuer_id": exact["issuer_id"], "security_id": exact["security_id"],
                "listing_key": exact["listing_key"], "refusal_reason": None,
                "source_receipts": json.dumps(
                    {"master_inception_code": symbol, "security_id": exact["security_id"]},
                    sort_keys=True)}

    # rule 6 — alias: query each eligible date-only vendor, collect the SET of
    # distinct security_ids. Never a ticker-equality fallback — a symbol absent from
    # every vendor space here falls straight through to rule 7. HISTORICAL mode (an
    # explicit asof from resolve_graph_node_identity) restricts evidence to DATED alias
    # rows only (F2 amendment, two-clock law) — a current-catalog row can never answer a
    # historical-naming question.
    asof_date = _as_date(resolution_asof)
    matches: dict[str, set[str]] = {}
    for vendor in sorted(inputs.vendors):
        # This graph has only a date, not the native source/consumer receipt
        # cutoff contract. Keep timestamp-gated reference observations ineligible.
        if vendor == "polygon":
            continue
        if historical:
            sec = _historical_alias_resolve(inputs.alias_table, vendor, symbol, asof_date)
        else:
            sec = inputs.alias_table.resolve(vendor, symbol, on=asof_date)
        if sec:
            matches.setdefault(sec, set()).add(vendor)

    if len(matches) == 1:
        [(sec_id, vendors_hit)] = matches.items()
        m_row = inputs.master_by_security.get(sec_id)
        mismatch = (_cross_market_mismatch_reason(market_scope, m_row["listing_key"])
                    if m_row else None)
        if mismatch is not None:
            return {**row, **null_ids, "resolution_state": "NOT_IN_MASTER",
                    "join_method": "refused", "refusal_reason": mismatch,
                    "source_receipts": json.dumps(
                        {"matched_vendors": sorted(vendors_hit),
                         "would_resolve_to": sec_id, "cross_market_collision": True},
                        sort_keys=True)}
        return {**row, "resolution_state": "RESOLVED", "join_method": "vendor_alias",
                "issuer_id": m_row["issuer_id"] if m_row else None,
                "security_id": sec_id,
                "listing_key": m_row["listing_key"] if m_row else None,
                "refusal_reason": None,
                "source_receipts": json.dumps(
                    {"matched_vendors": sorted(vendors_hit), "security_id": sec_id},
                    sort_keys=True)}
    if len(matches) > 1:
        return {**row, **null_ids, "resolution_state": "AMBIGUOUS", "join_method": "refused",
                "refusal_reason": (
                    f"{len(matches)} distinct security_ids returned by vendor alias "
                    "resolution — never picked by precedence/cap/name"),
                "source_receipts": json.dumps(
                    {"candidates": {k: sorted(v) for k, v in matches.items()}},
                    sort_keys=True)}

    # rule 7 — nothing matched. First-class honest state, never a guard failure. In
    # HISTORICAL mode, disclose separately when a current-catalog (fully open) row
    # WOULD have matched — that row exists but is not historical-naming evidence (F2
    # amendment); the two-clock law makes that a materially different "no" from a
    # symbol absent everywhere.
    refusal_reason = "no security-master or vendor-alias row resolves this symbol"
    receipts: dict = {"checked_vendors": sorted(v for v in inputs.vendors if v != "polygon")}
    if historical:
        open_hit = any(
            inputs.alias_table.resolve(vendor, symbol, on=asof_date) is not None
            for vendor in inputs.vendors if vendor != "polygon")
        if open_hit:
            refusal_reason = (
                "no dated alias evidence at asof; current-catalog rows exist but are "
                "not historical-naming evidence")
            receipts["current_catalog_rows_excluded_as_historical_evidence"] = True
    return {**row, **null_ids, "resolution_state": "NOT_IN_MASTER", "join_method": "refused",
            "refusal_reason": refusal_reason,
            "source_receipts": json.dumps(receipts, sort_keys=True)}


# ---------------------------------------------------------------------------
# Derivation — one row per company-kind node, every build (§2, §9.3-style side-car)
# ---------------------------------------------------------------------------

def derive_rows(nodes: list[dict], *, resolution_asof: str, computed_at: str,
                engine_version: str, data_dir: Path | None = None) -> list[dict]:
    """One ``identity_resolution`` row per company-kind node in ``nodes``.

    Re-derived from scratch every call, exactly like ``capability.derive_rows``: the
    master's own coverage can only grow (DOS-1.1/1.2 are still display_only authority),
    so a node ``NOT_IN_MASTER`` tonight may resolve tomorrow, and a write-once row would
    make that improvement invisible.
    """
    inputs = load_master_inputs(data_dir)
    etf_syms = _etf_symbols(nodes)
    rows: list[dict] = []
    for node in nodes:
        if str(node.get("kind")) != "company":
            continue
        rows.append(_resolve_node_row(
            node_id=str(node.get("node_id")), resolution_asof=resolution_asof,
            inputs=inputs, etf_symbols=etf_syms, computed_at=computed_at,
            engine_version=engine_version))
    rows.sort(key=lambda r: r["node_id"])
    return rows


# ---------------------------------------------------------------------------
# Reader API (§5)
# ---------------------------------------------------------------------------

def read_identity_resolution(*, latest: bool = True) -> pd.DataFrame:
    """Bulk read — the ``read_capability`` pattern, current view = max ``computed_at``
    per node_id."""
    return store.read_identity_resolution(latest=latest)


def _utc_now_stamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z")


def resolve_graph_node_identity(node_id: str, asof: str | date | None = None) -> dict:
    """One node's typed resolution row.

    ``asof=None`` — the node's row from the latest persisted sidecar generation
    (falling back to a live computation only if the graph carries the node but the
    sidecar has never resolved it yet, e.g. a pre-first-run checkout — a known node
    NEVER returns an untyped/None resolution). This is CURRENT mode, exactly like the
    materialization path: every vendor alias space is eligible evidence.

    An explicit ``asof`` re-runs the §4 algorithm as a PURE function over the
    committed Data OS inputs at that date — no store write, no second store — in
    HISTORICAL mode (two-clock law, F2 amendment): rule 6 may consult only DATED
    alias rows of the historical vendor spaces as historical-naming evidence; the
    current-catalog spaces (``store``/``yahoo_fetch``) are excluded by vendor
    identity, whether their rows are open or dated. Rule 5 is unaffected either
    way — it is asof-invariant.

    Raises :class:`UnknownGraphNodeError` only for a ``node_id`` absent from the graph
    itself (or present under a non-company kind — v1's row scope is company nodes
    only).
    """
    nid = str(node_id)
    nodes_df = store.read_nodes()
    hit = nodes_df[nodes_df["node_id"].astype(str) == nid] if not nodes_df.empty \
        else nodes_df
    if hit.empty:
        raise UnknownGraphNodeError(
            f"{nid!r} is not a node in the theme graph (nodes.parquet)")
    if str(hit.iloc[0].get("kind")) != "company":
        raise UnknownGraphNodeError(
            f"{nid!r} is kind={hit.iloc[0].get('kind')!r} — identity_resolution v1 "
            "covers company-kind nodes only")

    etf_syms = _etf_symbols(nodes_df.to_dict("records"))

    if asof is not None:
        asof_str = asof if isinstance(asof, str) else asof.isoformat()
        inputs = load_master_inputs()
        return _resolve_node_row(node_id=nid, resolution_asof=asof_str, inputs=inputs,
                                 etf_symbols=etf_syms, computed_at=_utc_now_stamp(),
                                 engine_version=store.ENGINE_VERSION, historical=True)

    cached = read_identity_resolution(latest=True)
    if not cached.empty:
        row = cached[cached["node_id"].astype(str) == nid]
        if not row.empty:
            return row.iloc[0].to_dict()

    # No persisted row yet (pre-first-run) but the node genuinely exists in the graph —
    # compute live rather than returning an untyped/None resolution for a known node.
    inputs = load_master_inputs()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return _resolve_node_row(node_id=nid, resolution_asof=today, inputs=inputs,
                             etf_symbols=etf_syms, computed_at=_utc_now_stamp(),
                             engine_version=store.ENGINE_VERSION)


def adopt_etf_references(nodes, lifecycle, node_ids, sources, *, now: datetime) -> dict[str, dict]:
    """Read-only current ETF adoption, separate from company-only sidecar v1.

    Data OS vendor aliases supply canonical identity. A byte-qualified listing
    observation supplies instrument TYPE only, never a listing/security binding.
    Nothing is minted, persisted, retyped or resolved through ticker equality.
    """
    import hashlib
    import io
    from lib.dataos.identity import parse_id, parse_listing_key, security_id
    from lib.symbol_directory_receipts import validate_symbol_directory_completion_receipt_bytes
    from engine.theme_graph.ontology import _clock_instant, _json_object, _nodes_as_known
    from scripts.build_security_master import EXCHANGE_MIC

    ids = sorted(set(node_ids))
    if len(ids) > 128:
        raise ValueError('ETF identity reference bound')
    result = {nid: dict(status='unavailable', reason='ETF_IDENTITY_INPUTS_UNAVAILABLE') for nid in ids}
    try:
        receipt = json.loads(sources['data/reference/_receipt.json'])
        day = receipt['symbol_directory_snapshot']
        observed = date.fromisoformat(day)
        if day != observed.isoformat() or observed > now.date():
            raise ValueError('listing clock')
        listing_path = f'data/symbol_directory/snapshots/{day}.parquet'
        listing_receipt_path = f'data/symbol_directory/receipts/snapshots/{day}.json'
        listing_raw, lr_raw = sources[listing_path], sources[listing_receipt_path]
        import pyarrow.parquet as parquet
        for raw in (listing_raw, sources['data/reference/security_master.parquet'],
                    sources['data/reference/vendor_aliases.parquet']):
            if len(raw) > 32 * 1024 * 1024 or parquet.ParquetFile(io.BytesIO(raw)).metadata.num_rows > 250000:
                raise ValueError('ETF identity source bound')
        listing = validate_symbol_directory_completion_receipt_bytes(
            json.loads(lr_raw), lr_raw, listing_raw, expected_kind='listing_snapshot')
        master_raw = sources['data/reference/security_master.parquet']
        aliases_raw = sources['data/reference/vendor_aliases.parquet']
        if (receipt['producer'] != 'scripts/build_security_master.py'
                or receipt['authority']['identity_authority'] != 'canonical_exact_identity'
                or not {'reference.security_master','reference.vendor_aliases'} <= set(receipt['dataset_ids'])
                or receipt['inputs']['data/symbol_directory/snapshots'] != hashlib.sha256(listing_raw).hexdigest()
                or _clock_instant(receipt['generated_at'], 'generated_at') > now
                or _clock_instant(listing['clocks']['collector_completed_at'], 'collector_completed_at') > now):
            raise ValueError('owner binding')
        master_rows = pd.read_parquet(io.BytesIO(master_raw)).to_dict('records')
        alias_rows = pd.read_parquet(io.BytesIO(aliases_raw)).to_dict('records')
        listings = pd.read_parquet(io.BytesIO(listing_raw)).to_dict('records')
        if len(master_rows) != receipt['row_counts']['security_master']:
            raise ValueError('master count')
        by_id = {r['security_id']:r for r in master_rows}
        if len(by_id) != len(master_rows):
            raise ValueError('duplicate canonical identity')
        table = VendorAliasTable.from_records(alias_rows)
        if len(table.rows) != receipt['row_counts']['vendor_alias_rows_readable']:
            raise ValueError('alias count')
        visible = _nodes_as_known(nodes, lifecycle, asof=now.date(), knowledge_cutoff=now)
        counts = {}
        for row in nodes:
            counts[row['node_id']] = counts.get(row['node_id'], 0) + 1
        from engine.theme_graph.store import RETIRED_LIKE_STATUSES
        for nid in ids:
            node = visible.get(nid)
            symbol = (_json_object(node.get('external_ids')) or {}).get('symbol') if node else None
            if (not node or counts[nid] != 1 or node.get('kind') != 'etf'
                    or node.get('market_scope') != 'us' or node.get('status') in RETIRED_LIKE_STATUSES
                    or not isinstance(symbol, str) or not symbol
                    or node.get('provenance') != 'membership_doc:baskets'):
                result[nid] = dict(status='unavailable', reason='ETF_GRAPH_IDENTITY_UNQUALIFIED')
                continue
            wrappers = [r for r in visible.values() if r.get('kind') == 'company'
                and (_json_object(r.get('external_ids')) or {}).get('symbol') == symbol
                and r.get('status') not in RETIRED_LIKE_STATUSES]
            if wrappers:
                result[nid] = dict(status='unavailable', reason='AMBIGUOUS_ACTIVE_COMPANY_WRAPPER')
                continue
            # The node's membership-document namespace is explicit. No inception
            # code or etf:<symbol> construction is used to obtain a security ID.
            sid = table.resolve('membership', symbol, now.date(), decision_at=now)
            answers = {x for vendor in {r.vendor for r in table.rows}
                       if (x := table.resolve(vendor, symbol, now.date(), decision_at=now)) is not None}
            if len(answers) > 1:
                result[nid] = dict(status='unavailable', reason='AMBIGUOUS_CANONICAL_ALIAS')
                continue
            if not sid or answers != {sid} or table.vendor_symbol_for('membership',sid,now.date(),decision_at=now) != symbol:
                result[nid] = dict(status='unavailable', reason='ETF_CANONICAL_ALIAS_UNAVAILABLE')
                continue
            row = by_id.get(sid)
            if not row or (not pd.isna(row.get('security_state')) and str(row.get('security_state')).strip()):
                result[nid] = dict(status='unavailable', reason='ETF_CANONICAL_SECURITY_UNAVAILABLE')
                continue
            kind, key = parse_id(sid)
            if kind != 'security' or security_id(key) != sid or row['listing_key'] != key.render() or row['country'] != 'US' or row['mic'] != key.mic:
                raise ValueError('canonical listing inconsistent')
            typed = [r for r in listings if r['symbol'] == symbol]
            if (len(typed) != 1 or typed[0].get('etf') is not True
                    or typed[0].get('test_issue') is not False or typed[0].get('is_preferred') is not False
                    or EXCHANGE_MIC.get(typed[0].get('exchange')) != key.mic):
                result[nid] = dict(status='unavailable', reason='ETF_INSTRUMENT_TYPE_UNQUALIFIED')
                continue
            result[nid] = dict(status='available', reason=None, security_id=sid, listing_key=row['listing_key'],
                identity_basis='LATEST_PUBLISHED_DATAOS_VENDOR_ALIAS', historical_identity_claim=False,
                instrument_type='ETF', instrument_type_basis='NATIVE_LISTING_OBSERVATION_ONLY',
                master_generated_at=receipt['generated_at'], listing_observed_on=day,
                listing_known_at=listing['clocks']['collector_completed_at'])
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return {nid: dict(status='unavailable', reason='ETF_IDENTITY_INPUTS_UNAVAILABLE') for nid in ids}
    return result
