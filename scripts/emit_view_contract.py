"""Emit the Terminal daily-OHLC view-contract sidecar (C04, DATA-OS-COMPLETION).

Decision of record:
``agentos/decisions/DEC-DATAOS-VIEW-CONTRACT-SIDECAR-IS-A-NIGHTLY-EMITTER.md``
— the nightly is the sole writer of ``data/stocks/_view_contract.json``, and this
module is that writer.  It serialises C01's ``terminal_daily_ohlc_contract_v1``
mapping VERBATIM and adds only the three fields the Terminal reader also
requires: ``coverage`` (counts only), ``listings`` (store symbol -> open US
listing, resolved through ``vendor_aliases`` -> ``security_master``) and
``refusal_reasons``.  The output is byte-stable — no clock, no randomness — so
an unchanged store and reference leave the file untouched.  It never decides
basis, venue scope or units: those belong to the factory (C01), and a venue
outside the reader's scope is copied as-is (refusing it is the reader's job).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))   # unconditional: the strong pin the import-pinning test requires

import pandas as pd  # noqa: E402
from engine.price_ladder import terminal_daily_ohlc_contract_v1  # noqa: E402

ALIAS_SPACE = "store"                      # == scripts/build_security_master.py VENDOR_STORE (pinned by a test)
SIDECAR_NAME = "_view_contract.json"
LISTINGS_SOURCE_UNAVAILABLE = "LISTINGS_SOURCE_UNAVAILABLE"
DEFAULT_STORE = "data/stocks"
DEFAULT_REFERENCE = "data/reference"
ALIASES_FILE = "vendor_aliases.parquet"
MASTER_FILE = "security_master.parquet"
US_COUNTRY = "US"
_ALIAS_COLUMNS = ["vendor", "vendor_symbol", "security_id", "valid_to"]
_MASTER_COLUMNS = ["security_id", "listing_key", "country", "mic", "superseded_by"]
_REQUIRED_READER_KEYS = ("schema", "purpose", "identity_namespace", "field_units", "adjustment_reference",
                         "evidence_mode", "coverage", "listings", "refusal_reasons")


def store_symbols(store_dir: Path) -> list[str]:
    """Sorted stems of the store's ``<symbol>.parquet`` files — names only, never a read.

    One ``os.scandir`` pass: keep an entry only when its name is not private
    (``_``-prefixed) or hidden (``.``-prefixed), ends with ``.parquet``, and is a
    regular file.  Directories such as ``sub.parquet/`` are skipped by the
    ``is_file()`` check.
    """
    with os.scandir(store_dir) as entries:
        stems = [
            entry.name[: -len(".parquet")]
            for entry in entries
            if not entry.name.startswith(("_", "."))
            and entry.name.endswith(".parquet")
            and entry.is_file()
        ]
    return sorted(stems)


def load_reference(reference_dir: Path) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    """Read the two committed reference parquets, projecting only the needed columns.

    Each read is independent: when ``vendor_aliases.parquet`` or
    ``security_master.parquet`` is missing or unreadable, THAT frame is ``None``
    and the caller refuses listings rather than guessing.  No other failure is
    swallowed.
    """
    try:
        aliases = pd.read_parquet(reference_dir / ALIASES_FILE, columns=_ALIAS_COLUMNS)
    except (OSError, ValueError, KeyError):
        aliases = None
    try:
        master = pd.read_parquet(reference_dir / MASTER_FILE, columns=_MASTER_COLUMNS)
    except (OSError, ValueError, KeyError):
        master = None
    return aliases, master


def resolve_listings(symbols: list[str], aliases: pd.DataFrame, master: pd.DataFrame) -> dict[str, dict[str, str]]:
    """Resolve each store symbol to its single open US listing — pure, no IO, no print.

    The identity comes from the security master through the alias table, never
    from the file name (D00.D2).  A symbol is resolved ONLY when exactly one open
    ``store`` alias row carries it to exactly one security AND that security has
    exactly one open US listing; every other symbol is omitted (never a first
    row).  Lookups are built once, vectorised — no per-symbol frame filtering.
    """
    wanted = set(symbols)
    alias_mask = (
        (aliases["vendor"] == ALIAS_SPACE)
        & aliases["valid_to"].isna()
        & aliases["security_id"].notna()
        & aliases["vendor_symbol"].isin(wanted)
    )
    ids_by_symbol: dict[str, set[str]] = {}
    for symbol, security_id in zip(aliases.loc[alias_mask, "vendor_symbol"], aliases.loc[alias_mask, "security_id"]):
        ids_by_symbol.setdefault(str(symbol), set()).add(str(security_id))

    master_mask = (
        master["superseded_by"].isna()
        & (master["country"] == US_COUNTRY)
        & master["mic"].notna()
        & master["listing_key"].notna()
    )
    pairs_by_security: dict[str, set[tuple[str, str]]] = {}
    open_us = master.loc[master_mask]
    for security_id, mic, listing_key in zip(open_us["security_id"], open_us["mic"], open_us["listing_key"]):
        pairs_by_security.setdefault(str(security_id), set()).add((str(mic), str(listing_key)))

    listings: dict[str, dict[str, str]] = {}
    for symbol in sorted(ids_by_symbol):
        security_ids = ids_by_symbol[symbol]
        if len(security_ids) != 1:
            continue
        security_id = next(iter(security_ids))
        pairs = pairs_by_security.get(security_id, set())
        if len(pairs) != 1:
            continue
        mic, listing_key = next(iter(pairs))
        listings[symbol] = {"mic": str(mic), "listing_key": str(listing_key), "security_id": str(security_id)}
    return listings


def build_contract(store_label: str, symbols: list[str], listings: dict, refusal_reasons: list[str]) -> dict:
    """C01's factory dict plus coverage, listings and refusal reasons — nothing re-derived.

    ``coverage``, ``listings`` and ``refusal_reasons`` belong to this emitter: if
    the factory ever starts carrying one of them the two contracts have diverged
    and the collision is raised, never merged.  A listing key outside the store
    symbol set is likewise a caller bug and is raised.  No clock, no path beyond
    the label, no symbol names.
    """
    contract = terminal_daily_ohlc_contract_v1()
    for emitter_key in ("coverage", "listings", "refusal_reasons"):
        if emitter_key in contract:
            raise ValueError(f"factory contract already carries '{emitter_key}' — the view contracts have diverged")
    stray = [k for k in sorted(listings) if k not in set(symbols)]
    if stray:
        raise ValueError(f"listings carry {len(stray)} key(s) outside the store symbol set")
    contract["coverage"] = {
        "store": store_label,
        "symbols": len(symbols),
        "listings_resolved": len(listings),
        "listings_unresolved": len(symbols) - len(listings),
    }
    contract["listings"] = {k: listings[k] for k in sorted(listings)}
    contract["refusal_reasons"] = sorted(set(refusal_reasons))
    missing = [key for key in _REQUIRED_READER_KEYS if key not in contract]
    if missing:
        raise ValueError(f"contract is missing required reader keys: {missing}")
    return contract


def render(contract: dict) -> bytes:
    """Serialise the contract byte-stably: sorted keys, 2-space indent, trailing newline.

    ``ensure_ascii`` stays at its default so the factory's em dash reads the same
    under any locale.
    """
    return (json.dumps(contract, sort_keys=True, indent=2) + "\n").encode("utf-8")


def emit(store_dir: Path, reference_dir: Path, *, store_label: str = DEFAULT_STORE, dry_run: bool = False) -> dict:
    """Write ``store_dir/_view_contract.json`` atomically; non-fatal and honest by design.

    A missing store writes nothing (warning only).  A missing or unreadable
    reference source still writes the file, with empty ``listings`` and
    ``LISTINGS_SOURCE_UNAVAILABLE``, so the reader refuses every symbol as
    ``LISTING_ABSENT`` instead of being served a guess.  An unchanged byte image
    is a no-op (the file is not rewritten).  Annotations are bare ``::`` lines;
    exactly one counts-only summary line is printed.
    """
    if not store_dir.is_dir():
        print("::warning title=emit_view_contract::store directory absent (" + store_label + "); no sidecar written", flush=True)
        return {
            "status": "store_absent",
            "path": None,
            "symbols": 0,
            "listings_resolved": 0,
            "listings_unresolved": 0,
            "refusal_reasons": [],
        }

    symbols = store_symbols(store_dir)
    aliases, master = load_reference(reference_dir)
    if aliases is None or master is None:
        listings = {}
        refusals = [LISTINGS_SOURCE_UNAVAILABLE]
        print("::warning title=emit_view_contract::listing source unavailable (" + ALIASES_FILE + " or " + MASTER_FILE + "); every symbol will read LISTING_ABSENT", flush=True)
    else:
        listings = resolve_listings(symbols, aliases, master)
        refusals = []

    contract = build_contract(store_label, symbols, listings, refusals)
    data = render(contract)
    path = store_dir / SIDECAR_NAME
    symbol_count = contract["coverage"]["symbols"]
    unresolved_count = contract["coverage"]["listings_unresolved"]
    if unresolved_count > 0:
        print("::notice title=emit_view_contract::" + f"{unresolved_count} of {symbol_count} store symbols have no single open US listing; the reader serves them as LISTING_ABSENT", flush=True)

    if dry_run:
        status = "dry_run"
    elif path.is_file() and path.read_bytes() == data:
        status = "unchanged"
    else:
        fd, tmp = tempfile.mkstemp(prefix="._view_contract.", suffix=".tmp", dir=store_dir)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
            os.chmod(tmp, 0o644)
            os.replace(tmp, path)
        except BaseException:
            try:
                os.remove(tmp)
            except FileNotFoundError:
                pass
            raise
        status = "written"

    print(
        "emit_view_contract: " + status + " store=" + store_label
        + " symbols=" + str(contract["coverage"]["symbols"])
        + " listings_resolved=" + str(contract["coverage"]["listings_resolved"])
        + " listings_unresolved=" + str(contract["coverage"]["listings_unresolved"])
        + " refusals=" + str(len(contract["refusal_reasons"])),
        flush=True,
    )
    return {
        "status": status,
        "path": str(path),
        "symbols": contract["coverage"]["symbols"],
        "listings_resolved": contract["coverage"]["listings_resolved"],
        "listings_unresolved": contract["coverage"]["listings_unresolved"],
        "refusal_reasons": contract["refusal_reasons"],
    }


def main(argv: list[str] | None = None) -> int:
    """CLI: ``--store``, ``--reference`` (both relative to the repo root) and ``--dry-run``."""
    parser = argparse.ArgumentParser(description="Write the Terminal daily-OHLC view-contract sidecar (C04).")
    parser.add_argument("--store", default=DEFAULT_STORE, help="store directory to describe and write beside")
    parser.add_argument("--reference", default=DEFAULT_REFERENCE, help="directory holding the committed reference parquets")
    parser.add_argument("--dry-run", action="store_true", help="report the status without writing anything")
    args = parser.parse_args(argv)

    store = Path(args.store)
    if not store.is_absolute():
        store = ROOT / store
    reference = Path(args.reference)
    if not reference.is_absolute():
        reference = ROOT / reference
    emit(store, reference, store_label=args.store, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
