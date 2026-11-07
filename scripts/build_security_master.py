#!/usr/bin/env python3
"""Materialize the security master + the time-scoped vendor alias table (Data OS DOS-1.1).

WHAT THIS PRODUCES, AND WHY IT IS TWO FILES
-------------------------------------------
``data/reference/security_master.parquet``  one row per SECURITY — the stored,
authoritative ``security_id``.  ``lib/dataos/identity.py`` is the ALLOCATOR (a pure
derivation, no counter, no hash); this artifact is the AUTHORITY (the value that was
minted and stored).  ``research/MASTERMIND_SECURITY_MASTER_SPEC.md`` §4 states the
rule this script implements as code: **mint once and store** — a later correction to
inception facts appends an ALIAS, it never re-mints a stable id, because two ids for
one thing is the exact defect the spine exists to end.

``data/reference/vendor_aliases.parquet``  one row per
``(vendor, vendor_symbol, security_id, valid_from, valid_to)``, half-open in time:
``valid_from`` INCLUSIVE, ``valid_to`` EXCLUSIVE (spec §6;
``lib/dataos/identity.py::AliasRow``).  An inclusive end would make the changeover day
ambiguous, and 2026-01-14 is exactly the day the MMC/MRSH answer has to be
unambiguous.  It carries FIVE vendor spaces in TWO FAMILIES — three that answer "what
was it called THEN" and two that answer "what do I call it TODAY, for a bar of any
date".  Confusing those two is the seven-month MMC outage in a new costume, so the
families have different names and a test pins them apart; see the vendor block below.

``data/reference/_receipt.json``  ``code_version`` (git sha), per-input sha256, row
counts, ``generated_at``, and the coverage numbers.  Coverage is a REPORTED NUMBER,
never an asserted completeness: DOS-1.1's acceptance bullet is "N of M members
resolved, K unresolved, listed by name".

THE TWO RENAMES THIS EXISTS TO ANSWER
-------------------------------------
**MMC -> MRSH, 2026-01-14.**  Marsh McLennan changed its NYSE symbol; same listing,
same CUSIP (``lib/ticker_aliases.py`` module docstring).  Yahoo migrated the whole
history onto MRSH while ``scripts/fetch_basket_ohlcv`` carried only the FI->FISV
entry, so ``data/baskets/ohlcv/MMC.parquet`` came to never exist and the ``insurance``
basket rendered 18/19 members and ``us_sector_financials`` 75/76 for SEVEN MONTHS.
Nothing went red; the site simply drew one fewer line.  A timeless two-entry dict can
say "MMC means MRSH" but cannot say "MMC MEANT MMC before 2026-01-14", so a backfill
through it silently re-labels the past.  Both symbols resolve here to ONE id,
``SEC:US-XNYS-MMC``, and the table answers DIFFERENTLY either side of the boundary.

**SATS -> ECHO, 2026-06-24.**  EchoStar.  ``engine/ledger_identity.py`` module
docstring measures the live defect: ``data/signal_archive/track_record.parquet``
carries SATS 128 rows and ECHO 128 rows with IDENTICAL ``(date, type)`` key sets and
all 39 identity/entry columns byte-identical — one physical fire logged twice — so
every hit-rate, forward-return and drawdown statistic over that ledger DOUBLE-WEIGHTS
one name.  A table that knew MMC and not SATS would have reproduced the exact
fragmentation being fixed, so SATS is not optional here.

WHAT THIS SCRIPT DOES NOT DO
----------------------------
* It does not become an authority.  Nothing reads these artifacts yet except
  ``tests/test_dataos_security_master.py``; DOS-1.2 declares the seams, and the master
  becomes authority only at spec §11.4.  Display-tier accrual needs no gauntlet.
* It does not invent an inception DATE.  Spec §4: there is **no in-repo US listing-date
  source**, and back-dating one from a store's earliest bar would be a fabricated fact
  (``lib/symbol_directory_receipts.py`` forbids that class of synthesis outright).
  ``effective_at`` is therefore the earliest DATED OBSERVATION in this repo's committed
  seeds that the security existed — see :func:`_effective_at`.  It is NOT a listing date
  and must never be read as one.
* It does not resolve a venue by guessing.  ``KNOWN_MICS`` in
  ``lib/dataos/identity.py`` is closed on purpose; a symbol whose venue has no MIC
  there is reported UNRESOLVED by name rather than minted onto a guessed venue.
  Getting a MIC wrong mints a different, stable, wrong id — spec §5: "the one mistake
  this scheme cannot self-heal".
* It creates no new store, no control plane and no second identity reader
  (gate G4).  ``lib/dataos/identity.VendorAliasTable`` is the only reader, and this
  builder round-trips every alias row through it before writing, so an ambiguous table
  fails HERE rather than in a consumer.

Usage::

    python3 scripts/build_security_master.py              # build + write
    python3 scripts/build_security_master.py --report     # build + write + full census
    python3 scripts/build_security_master.py --dry-run    # build, print, write NOTHING
    python3 scripts/build_security_master.py --out DIR    # default: data/reference
"""
from __future__ import annotations

import argparse
import os
import errno
import stat
import threading
from contextlib import contextmanager
import hashlib
import json
import subprocess
import sys
import time
import io
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.entry_radar.replay.identity_observation_snapshot import IdentitySnapshotRead
    from engine.neuralweb.market_memory_identity_candidate import ParquetBoundInitialCandidate

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import config, ticker_aliases  # noqa: E402
from lib.dataos.identity import (  # noqa: E402
    BATS,
    XASE,
    ARCX,
    TXSE,
    alias_binding_sha256,
    XNAS,
    XNYS,
    AliasRow,
    IdentityError,
    ListingKey,
    VendorAliasTable,
    issuer_id,
    normalize_cn_symbol,
    normalize_hk_symbol,
    parse_listing_key,
    security_id,
)

# ── Paths ─────────────────────────────────────────────────────────────────────
# Resolved against THIS FILE, never the cwd: the nightly, the CI packs and a
# developer shell all run from different directories (same reasoning as
# lib/dataos/registry.REGISTRY_PATH).
DEFAULT_OUT = ROOT / "data" / "reference"
MASTER_NAME = "security_master.parquet"
ALIASES_NAME = "vendor_aliases.parquet"
RECEIPT_NAME = "_receipt.json"
ISSUER_MASTER_NAME = "issuer_master.parquet"
ISSUER_MIGRATIONS_NAME = "issuer_migrations.parquet"
#: V4-D2B1-R1 — the durable security-axis correction receipt (parallel to
#: ISSUER_MIGRATIONS_NAME, one axis over).
SECURITY_MIGRATIONS_NAME = "security_migrations.parquet"

CONSTITUENTS = ROOT / "data" / "breadth" / "constituents.parquet"
#: ITP A8 (DEC-ITP-ISSUER-UNIVERSE-ADMITS-R1-CONSTITUENTS-2026-10-07): the mid- and
#: small-cap breadth constituents join the identity universe, read exactly like
#: CONSTITUENTS (forward-only: no valid_from backdating, ingested_at = build time).
MIDCAP_CONSTITUENTS = ROOT / "data" / "midcap_breadth" / "constituents.parquet"
SMALLCAP_CONSTITUENTS = ROOT / "data" / "smallcap_breadth" / "constituents.parquet"
MEMBERSHIP = ROOT / "data" / "baskets" / "membership.json"
DELISTED_LEDGER = ROOT / "config" / "delisted_symbols.yml"
CONFIG_YML = ROOT / "config.yml"
TICKER_ALIASES_PY = ROOT / "lib" / "ticker_aliases.py"
SYMBOL_DIR_SNAPSHOTS = ROOT / "data" / "symbol_directory" / "snapshots"
#: Weekly SEC registrant map (V4-D2B1 §1) — read-only, collector-owned
#: (``data/symbol_directory/**`` is never written by this script).
CIK_MAP_DIR = ROOT / "data" / "symbol_directory" / "cik_map"
#: Operator-ratified CIKs allowed to form a NEW multi-member issuer group (V4-D2B1
#: FIX 5 / M3) — see :func:`_load_issuer_group_allowlist`.
ISSUER_GROUP_ALLOWLIST_PATH = ROOT / "config" / "issuer_group_allowlist.yml"

#: V4-D2B2-CN-HK — the China/HK company-node TARGET POPULATION.  Read-only, upstream
#: graph truth (never `data/theme_graph/identity_resolution.parquet`, the DERIVED
#: sidecar — the master must stay upstream of that sidecar, and reading it here would
#: invert the dependency).  See :func:`load_cn_hk_seeds`.
THEME_GRAPH_NODES_PATH = ROOT / "data" / "theme_graph" / "nodes.parquet"
#: China A-share primary-source EXISTENCE evidence — CNInfo (巨潮资讯网), the
#: CSRC/exchange-designated official disclosure platform for SSE+SZSE
#: (`collectors/china_filings.py`).  See :func:`load_cninfo_evidence`.
CHINA_FILINGS_PATH = ROOT / "data" / "china_filings" / "filings.parquet"
#: HK primary-source EXISTENCE evidence — SFC (Securities and Futures Commission,
#: HK's statutory regulator) official Short Position Reports, and HKEX's own
#: published turnover statistics (`collectors/hk_shorts.py`).  See
#: :func:`load_hk_shorts_evidence`.
HK_SHORTS_POSITIONS_PATH = ROOT / "data" / "hk_shorts" / "positions.parquet"
HK_SHORTS_TURNOVER_PATH = ROOT / "data" / "hk_shorts" / "turnover.parquet"

#: The exact column order written to each artifact.  These are the ``schema:`` keys of
#: ``reference.security_master`` / ``reference.vendor_aliases`` in
#: ``config/dataset_registry.yml``, in declaration order, and
#: ``tests/test_dataos_security_master.py`` pins the equality both ways — the registry
#: is the contract, not a description of whatever this script happened to emit.
#:
#: The issuer axis (``issuer_state``/``issuer_cik``/``issuer_evidence_snapshot``) is
#: V4-D2B1: it sits next to ``issuer_id`` because the four columns together are one
#: semantic unit (the value, its evidentiary status, the evidence CIK, and the
#: snapshot it was observed in).
#: V4-D2B1-R1 §3.1: the security-axis correction columns sit at the END of the
#: declared order (they are the newest addition, era-seamed exactly like
#: ISSUER_AXIS_COLUMNS) — never a re-mint, never a deletion, a CORRECTION recorded
#: in place on the row it corrects.
MASTER_COLUMNS = (
    "security_id",
    "issuer_id",
    "issuer_state",
    "issuer_cik",
    "issuer_evidence_snapshot",
    "listing_key",
    "country",
    "mic",
    "inception_code",
    "effective_at",
    "ingested_at",
    "security_state",
    "superseded_by",
)
ALIAS_COLUMNS = (
    "vendor",
    "vendor_symbol",
    "security_id",
    "valid_from",
    "valid_to",
    "ingested_at",
    "known_at",
    "evidence_sha256",
    "binding_sha256",
    "alias_kind",
)
#: ``reference.issuer_master`` — one row per distinct non-null issuer_id (spec §3).
ISSUER_MASTER_COLUMNS = (
    "issuer_id",
    "cik",
    "legal_name",
    "n_securities",
    "evidence_source",
    "evidence_snapshot",
    "status",
    "era",
)
#: ``reference.issuer_migrations`` — append-only, one row per security whose issuer_id
#: VALUE changed in an era (spec §3).
ISSUER_MIGRATIONS_COLUMNS = (
    "security_id",
    "listing_key",
    "old_issuer_id",
    "new_issuer_id",
    "reason",
    "evidence_cik",
    "evidence_snapshot",
    "migrated_at",
)
#: ``reference.security_migrations`` (V4-D2B1-R1 §3.5) — append-only, one row per
#: security-axis correction: a security wrongly minted as an independent row for a
#: rename's NEW symbol before this builder modelled the rename, corrected onto the
#: pre-existing continuing security rather than deleted. Mirrors
#: ISSUER_MIGRATIONS_COLUMNS one axis over — durable old->new mapping, never the
#: live join (the live join is `security_master.superseded_by`).
SECURITY_MIGRATIONS_COLUMNS = (
    "security_id",
    "superseded_by",
    "reason",
    "evidence",
    "migrated_at",
)

#: Non-string column kinds, from the same ``schema:`` blocks.  Rows are carried in
#: memory as ISO STRINGS and cast only at write, so a re-read of a committed artifact
#: compares byte-for-byte against a freshly derived row instead of "Timestamp vs str".
#: That equality is what makes the builder idempotent rather than merely deterministic.
MASTER_DTYPES = {"effective_at": "datetime", "ingested_at": "datetime",
                 "issuer_evidence_snapshot": "date"}
REFERENCE_ALIAS_COLUMNS = frozenset({"known_at", "evidence_sha256", "binding_sha256"})
OPTIONAL_ALIAS_COLUMNS = REFERENCE_ALIAS_COLUMNS | {"alias_kind"}
ALIAS_DTYPES = {"valid_from": "date", "valid_to": "date", "ingested_at": "datetime"}
ISSUER_MASTER_DTYPES = {"evidence_snapshot": "date", "n_securities": "int"}
ISSUER_MIGRATIONS_DTYPES = {"evidence_snapshot": "date", "migrated_at": "datetime"}
SECURITY_MIGRATIONS_DTYPES = {"migrated_at": "datetime"}

#: Columns a PRE-D2B1 committed ``security_master.parquet`` will not carry yet.
#: ``_read_existing`` fills these with ``None`` instead of refusing, which is what
#: makes ``issuer_state is None`` the "not yet migrated by this era" marker the D2B1
#: era stage (:func:`apply_issuer_correction`) reads (spec §4 "era-inside-the-builder
#: idempotent migration").
ISSUER_AXIS_COLUMNS = frozenset({"issuer_state", "issuer_cik", "issuer_evidence_snapshot"})

#: Columns a PRE-D2B1-R1 committed ``security_master.parquet`` will not carry yet —
#: same era-seam pattern as :data:`ISSUER_AXIS_COLUMNS`, one axis over (V4-D2B1-R1
#: §3.1).  ``security_state is None`` means "active, never corrected"; the closed
#: enum's one value this era is ``SUPERSEDED_DUPLICATE_MINT``.
SECURITY_AXIS_COLUMNS = frozenset({"security_state", "superseded_by"})

#: The one authorized issuer-identity correction era (spec §4).
ERA_ISSUER_CORRECTION = "issuer_semantic_correction_v1"

#: The one authorized security-identity correction era (V4-D2B1-R1 §3.5) — a
#: security minted as an independent row for a rename's NEW symbol before this
#: builder modelled the rename, corrected onto the pre-existing continuing security.
ERA_SECURITY_SUPERSESSION = "security_supersession_duplicate_mint_v1"

#: Closed enum, one value today (V4-D2B1-R1 §3.1).
SECURITY_STATE_SUPERSEDED_DUPLICATE_MINT = "SUPERSEDED_DUPLICATE_MINT"

# ── Vendors (symbol SPACES) — TWO CLOCKS, never one ───────────────────────────
# A "vendor" here is a symbol space, which is why several of them are this repo.
# Spec §6's column note lists `yahoo` … `nasdaq_symdir` … `exchange` as vendors; the
# repo's own stable key is the space every site surface, page slug and ledger row is
# written in, so it needs a name in the same table or the translation has no LHS.
#
# THE DISTINCTION THIS TABLE MUST NOT COLLAPSE (adversarial review, 2026-08-13).  A
# rename gives a security two names, and there are two DIFFERENT questions about them:
#
#   HISTORICAL NAMING — "what did this space call the security ON 2020-01-02?"  Answered
#     by a DATED pair straddling the changeover.  This is the question a backfill of a
#     dated archive asks, and the one a timeless dict cannot answer at all.
#   CURRENT CATALOG — "what string do I use TODAY to fetch or store this security's
#     series, for data of ANY date?"  Answered by ONE OPEN-BOUNDED row at today's
#     symbol, because the vendor and the store both migrated the WHOLE history onto the
#     new name — Yahoo serves Marsh's entire tape under MRSH and `data/stocks/ECHO.parquet`
#     holds EchoStar's spliced history back to 2008.
#
# Reading the historical answer as if it were the current one is the seven-month MMC
# outage in a new costume: a §11.4 backfill that requested "MMC" for 2020 because the
# table said Yahoo called it MMC then would get "possibly delisted, no price data found".
# So the two families are SEPARATE VENDOR SPACES with names that say which clock they
# run on, and `tests/test_dataos_security_master.py` pins them apart.

# ── historical-naming spaces (dated across a rename) ──
VENDOR_YAHOO = "yahoo"            # what Yahoo CALLED the security on a given day
VENDOR_MEMBERSHIP = "membership"  # what THIS REPO keyed it on that day (universe seeds)
VENDOR_LEDGER = "ledger"          # the per-ticker signal-archive key space on that day

# ── current-catalog spaces (one open-bounded row at today's symbol) ──
#: The string to REQUEST from Yahoo today, for a bar of ANY date.  Reproduces
#: `lib.ticker_aliases.fetch_symbol` exactly — the row family that lets this dataset
#: claim `supersedes: lib/ticker_aliases.py` without lying.
VENDOR_YAHOO_FETCH = "yahoo_fetch"
#: The key this repo's per-ticker stores and ledger rows carry today, for data of ANY
#: date — `lib.ticker_aliases.store_key`'s side of the same seam.  `data/stocks/`,
#: `data/baskets/ohlcv/` and `data/signal_archive/` rows written after a rename are all
#: keyed here, which is why a dedup over the archive has to ask THIS space, not `ledger`.
VENDOR_STORE = "store"

#: V4-D2B2-CN-HK — current-catalog space carrying the GMI node's OWN suffix-qualified
#: symbol spelling (``"000001.SZ"``, ``"1398.HK"``) exactly as ``source_native_symbol``
#: carries it (``engine/theme_graph/identity_resolution.py::_best_effort_symbol``).
#: The master's ``inception_code`` for CN/HK is always the BARE code (spec §3.1: CN 6
#: digits no suffix, HK 5 digits zero-padded), which never string-equals the suffixed
#: spelling — so every CN/HK resolution in ``gmi.identity_resolution/v1`` goes through
#: D2A rule 6 (``join_method=vendor_alias``), never rule 5's exact inception-code
#: match.  See :func:`mint_cn_hk_rows`.
VENDOR_THEME_GRAPH_NATIVE = "theme_graph_native"

# ── Venue authority ───────────────────────────────────────────────────────────
#: otherlisted.txt single-character exchange codes, per the legend the collector that
#: fetches the file records at ``collectors/symbol_directory.py:184-185``:
#: "A=NYSE MKT (AMEX), N=NYSE, P=NYSE Arca, Z=BATS, V=Investors Exchange".
#: ``F`` = Texas Stock Exchange (MIC TXSE) is newer than that legend: the CTS Pillar
#: participant id ``F`` is assigned to TXSE (txse.com alert TXSE-2026-002 / CTA
#: "CTS Pillar Output Specification"), and the 2026-10-15 otherlisted.txt snapshot
#: carries ``F`` on exactly the TXSE-listed names (ET, TXS, OILT, ILS, ...).
#: Only venues with an evidence-backed MIC in ``lib/dataos/identity.KNOWN_MICS`` are mapped.
#: Arca / IEX remain deliberately ABSENT rather than approximated: a name listed
#: there is reported unresolved by name, because widening the closed MIC list is a
#: decision a human makes once, in a diff — not something a seed loader guesses.
EXCHANGE_MIC = {
    "NASDAQ": XNAS,
    "N": XNYS,
    "A": XASE,
    "Z": BATS,
    "F": TXSE,
}

#: `exchange:` values used by the exit ledger (`config/delisted_symbols.yml`), which
#: spells venues out because it is hand-written from SEC filings.  The exit ledger is
#: consulted FIRST for a delisted name: the symbol directory is a CURRENT listing set
#: (`scripts/check_symbol_rename_drift.py:36-42`), so it structurally cannot carry a
#: security whose tape has ended.
DELISTED_EXCHANGE_MIC = {
    "NYSE": XNYS,
    "NYSE AMERICAN": XASE,
    "NASDAQ": XNAS,
}

DEFAULT_COUNTRY = "US"


# ── The curated rename events ─────────────────────────────────────────────────
@dataclass(frozen=True)
class RenameEvent:
    """One DATED symbol change inside one symbol space.

    The repo's machine-readable maps (`lib.ticker_aliases.YAHOO_FETCH_ALIASES`,
    `breadth.ticker_fixups`, `quality.ticker_key_migrations`) are all TIMELESS — they
    carry the pair but not the day.  The days live in prose beside them, so they are
    lifted here with a `file:LINE`-grade citation each.  This is the ONLY authored data
    in this builder; everything else is derived from a committed seed.
    """

    old: str
    new: str
    on: date
    vendors: tuple[str, ...]
    evidence: str


RENAME_EVENTS: tuple[RenameEvent, ...] = (
    RenameEvent(
        old="MMC",
        new="MRSH",
        on=date(2026, 1, 14),
        # Yahoo LED this rename — it migrated the whole history onto MRSH, which is why
        # lib/ticker_aliases fetches under MRSH and the membership's MMC started 404-ing.
        # The membership space did NOT move: breadth.ticker_fixups pins MRSH back to MMC
        # ("MMC stays the stored key — 13 open qledger claims and the baskets membership
        # are keyed on it", config.yml), so no `membership` row is dated here.
        vendors=(VENDOR_YAHOO,),
        evidence=(
            "lib/ticker_aliases.py module docstring (MMC->MRSH 2026-01-14, symbol change "
            "only: same listing, same CUSIP; Yahoo serves the NEW symbol); "
            "config.yml breadth.ticker_fixups MRSH->MMC"
        ),
    ),
    RenameEvent(
        old="EQR",
        new="VMRK",
        on=date(2026, 8, 18),
        # V4-D2B1-R1 §1 E1: SEC EDGAR, CIK 0000906107, Form 8-K filed 2026-08-17
        # (accession 0001140361-26-033377), Item 5.03 — corporate name changed from
        # Equity Residential to Vivmark Residential effective 2026-08-17; NYSE ticker
        # changed EQR->VMRK effective 2026-08-18 (open of trading). Corroborated by
        # live EDGAR submissions (data.sec.gov/submissions/CIK0000906107.json: name
        # VIVMARK RESIDENTIAL, ticker VMRK, formerNames chain unbroken under one CIK)
        # and www.sec.gov/files/company_tickers.json (CIK 906107 -> VMRK). `yahoo`
        # moved (the exchange-side rename is real and Yahoo follows the exchange
        # spelling, same as MMC/SATS). `membership` is DATED here — unlike MMC, where
        # breadth.ticker_fixups pins the vendor-led rename straight back to the repo
        # key so only ONE `membership`-space observation ever exists — this security's
        # two universe seeds (data/baskets/membership.json still keyed EQR;
        # data/breadth/constituents.parquet already re-fetched as VMRK) are BOTH left
        # live on purpose (§2.3 — the dedup onto one master row is exactly what this
        # repair tests), so `membership` genuinely carries two simultaneous
        # observations that need the same date boundary to stay unambiguous.
        #
        # `store` IS dated here since 2026-08-28 (AMENDMENT ruling 9 / m3, completed
        # alongside the owed breadth-lane retirement — the EQR->VMRK store-key
        # migration under the #4622 protocol). The ruling conflict that deferred it
        # (dating the store answer required closing the pre-existing committed
        # open-bounded `(store, EQR, ...)` row, which AMENDMENT ruling 6 / M5's
        # fail-closed prune law forbids the builder to do) was resolved via the
        # comment's own option 2: an explicit ONE-TIME HAND-MIGRATION of the
        # committed row (data/reference/vendor_aliases.parquet: `(store, EQR,
        # SEC:US-XNYS-EQR, None, None)` -> valid_to=2026-08-18, plus the dated
        # `(store, VMRK, ..., 2026-08-18, None)` row), receipted in that change's PR
        # body. The general AMENDMENT §2 same-id-refinement carve-out remains a
        # follow-up with its own review; until it lands, the NEXT dated rename on a
        # current-catalog space still fail-closes at VendorAliasPruneConflict and
        # needs the same one-time hand-migration.
        vendors=(VENDOR_YAHOO, VENDOR_MEMBERSHIP, VENDOR_STORE),
        evidence=(
            "SEC EDGAR CIK 0000906107 Form 8-K filed 2026-08-17, accession "
            "0001140361-26-033377, Item 5.03: name changed Equity Residential -> "
            "Vivmark Residential eff. 2026-08-17; NYSE ticker EQR->VMRK eff. "
            "2026-08-18 (open of trading). Corroborated by "
            "data.sec.gov/submissions/CIK0000906107.json (name VIVMARK RESIDENTIAL, "
            "ticker VMRK, unbroken formerNames chain) and "
            "www.sec.gov/files/company_tickers.json (CIK 906107 -> VMRK)."
        ),
    ),
    RenameEvent(
        old="SATS",
        new="ECHO",
        on=date(2026, 6, 24),
        # The vendor space AND both of this repo's own key spaces moved on this one:
        # data/stocks/SATS.parquet no longer exists, data/stocks/ECHO.parquet holds the
        # full spliced history, and quality.ticker_key_migrations ratifies SATS->ECHO as
        # the key the stack now stores.  That double move is what produced the
        # double-logged ledger this table exists to make visible.
        #
        # `membership` is DATED here and open at MMC above, and the asymmetry is the
        # fact, not an inconsistency: `breadth.ticker_fixups` pins MRSH back to MMC (the
        # repo key deliberately did NOT move), while `quality.ticker_key_migrations`
        # ratifies SATS->ECHO (it DID).  Leaving membership open at today's ECHO would
        # re-label EchoStar's whole repo-side past — the exact timeless-map defect the
        # time-scoping exists to end, shipped inside the artifact that ends it.
        vendors=(VENDOR_YAHOO, VENDOR_LEDGER, VENDOR_MEMBERSHIP),
        evidence=(
            "engine/ledger_identity.py module docstring (EchoStar renamed SATS->ECHO "
            "effective 2026-06-24; SATS 128 rows and ECHO 128 rows with identical "
            "(date,type) key sets and 39 byte-identical identity columns); "
            "config.yml quality.ticker_key_migrations SATS: ECHO"
        ),
    ),
    RenameEvent(
        old="PSKY",
        new="SKYD",
        on=date(2026, 10, 6),
        # Skydance Corporation (formerly Paramount Skydance, CIK 0002041610) transferred
        # its Class B listing Nasdaq->NYSE and renamed PSKY->SKYD the SAME day, so unlike
        # EQR->VMRK (NYSE->NYSE) this rename MOVES THE VENUE: the renamed key re-derives
        # today's MIC plus the chain's inception code (US-XNYS-PSKY) while the committed
        # master row carries the inception venue (US-XNAS-PSKY). The exact-listing-key
        # SECURITY_SUPERSESSIONS entry below is the operator ratification that joins the
        # two — one stable id before and after 2026-10-06, never a second mint (and the
        # pending-transition fence is never consulted for a join, only for a mint).
        #
        # `membership` is DATED for the same reason EQR->VMRK's is: two simultaneous
        # membership observations exist (the PIT/stored side still keyed PSKY;
        # data/breadth/constituents.parquet re-fetched as SKYD), so the space needs the
        # date boundary to stay unambiguous — the roster resolve that fail-closed as
        # membership_alias_unresolved is exactly this consumer.
        #
        # `store` is NOT dated and no (store, SKYD) row is minted: data/stocks/ and the
        # per-ticker stores still key PSKY (the #4622-protocol key migration is a
        # separate act, out of scope here), so the committed open (store, PSKY, ...) row
        # stays the one true answer and the builder's current-catalog gate leaves it
        # alone. `yahoo_fetch` likewise stays at the committed PSKY row for the same
        # reason — the repo's fetch/store seam has not moved.
        #
        # `yahoo` is dated because Yahoo follows the exchange spelling (same as
        # MMC/SATS): finance.yahoo.com serves the renamed symbol today.
        vendors=(VENDOR_YAHOO, VENDOR_MEMBERSHIP),
        evidence=(
            "SEC EDGAR CIK 0002041610 Form 8-K filed 2026-10-06, accession "
            "0001104659-26-113913, Items 2.01/5.03: on 2026-10-06 the Company "
            "transferred the listing of its Class B Common Stock from The Nasdaq "
            "Stock Market LLC to the New York Stock Exchange and changed the ticker "
            "symbol from PSKY to SKYD. Corroborated by "
            "data.sec.gov/submissions/CIK0002041610.json (name Skydance Corp, "
            "ticker SKYD, exchange NYSE, unbroken formerNames chain Paramount "
            "Skydance Corp 2025-08-07 -> 2026-10-06 under one CIK), Form 8-K filed "
            "2026-09-25 accession 0001104659-26-111034 Item 3.01 (listing-transfer "
            "notice), Form 8-A12B filed 2026-10-05 accession 0001104659-26-113569, "
            "and finance.yahoo.com/quote/SKYD (Yahoo serves the new symbol)."
        ),
    ),
    RenameEvent(
        old="DOMO",
        new="HUCK",
        on=date(2026, 9, 24),
        # Same shape as PSKY->SKYD minus the venue move: Nasdaq->Nasdaq, so no
        # supersession entry is needed (same as EQR->VMRK). `yahoo` + `membership`
        # dated exactly as PSKY's are; `store`/`yahoo_fetch` stay at the committed
        # DOMO rows until a #4622-protocol store-key migration moves them (out of
        # scope here). Until then the committed build still reports US-XNAS-DOMO
        # in resolved_not_rederivable and HUCK in listing_continuity: this event
        # dates and attributes the rename, it does not by itself clear those rows.
        vendors=(VENDOR_YAHOO, VENDOR_MEMBERSHIP),
        evidence=(
            "SEC EDGAR CIK 0001505952 Form 8-K accession 0001104659-26-109635 "
            "(www.sec.gov/Archives/edgar/data/1505952/000110465926109635/"
            "tm2625825d1_8k.htm): Nasdaq ticker DOMO -> HUCK effective 2026-09-24, "
            "same registrant/CIK. Corroborated by the 2026-10-15 nasdaqlisted.txt "
            "snapshot (HUCK listed, DOMO absent)."
        ),
    ),
    RenameEvent(
        old="YYGH",
        new="YFOR",
        on=date(2026, 9, 2),
        # Nasdaq->Nasdaq symbol change with a name change (YY Group Holding Ltd. is
        # the formerName under the same CIK). Vendors dated as DOMO->HUCK above.
        vendors=(VENDOR_YAHOO, VENDOR_MEMBERSHIP),
        evidence=(
            "SEC EDGAR CIK 0001985337 Form 6-K accession 0001185185-26-003874 "
            "(www.sec.gov/Archives/edgar/data/1985337/000118518526003874/"
            "yfor6k090726.htm): Nasdaq ticker YYGH -> YFOR effective 2026-09-02, "
            "same registrant/CIK (formerName YY Group Holding Ltd.). Corroborated by "
            "the 2026-10-15 nasdaqlisted.txt snapshot (YFOR listed, YYGH absent)."
        ),
    ),
)


# ── The curated venue-transfer registry ───────────────────────────────────────
@dataclass(frozen=True)
class VenueTransfer:
    """One SAME-SYMBOL primary-listing transfer between venues (no rename).

    A transfer leaves the symbol directory carrying the security only under its NEW
    venue, so the resolution re-derives ``US-{to_mic}-{symbol}`` while the committed
    master row keeps its inception venue ``US-{from_mic}-{symbol}`` — structurally
    the PSKY->SKYD cross-venue case without a :class:`RenameEvent`. Each entry is
    paired with an EXACT-listing-key :data:`SECURITY_SUPERSESSIONS` entry (checked
    by :func:`_venue_transfer_covered_keys`); together they ratify the join onto the
    one canonical row, never a second mint. Authored data, same evidence law.
    """

    symbol: str
    from_mic: str
    to_mic: str
    on: date
    evidence: str


VENUE_TRANSFERS: tuple[VenueTransfer, ...] = (
    VenueTransfer(
        symbol="KHC",
        from_mic=XNAS,
        to_mic=XNYS,
        on=date(2026, 9, 14),
        evidence=(
            "SEC EDGAR CIK 0001637459: Form 8-K accession 0001637459-26-000057 "
            "(listing-transfer notice, Nasdaq -> NYSE), Form 25 accession "
            "0001637459-26-000062 (voluntary removal from Nasdaq) and Form 8-A12B "
            "accession 0001637459-26-000061 (NYSE registration); KHC trades on NYSE "
            "from 2026-09-14 under the unchanged symbol."
        ),
    ),
    VenueTransfer(
        symbol="ET",
        from_mic=XNYS,
        to_mic=TXSE,
        on=date(2026, 10, 5),
        evidence=(
            "SEC EDGAR CIK 0001276187: Form 8-K accession 0001276187-26-000044 "
            "(listing-transfer notice, NYSE -> Texas Stock Exchange), Form 25 "
            "accession 0001276187-26-000058 (voluntary removal from NYSE) and Form "
            "8-A12B accession 0001276187-26-000056 (TXSE registration); ET trades "
            "on TXSE from 2026-10-05 under the unchanged symbol (txse.com press "
            "release; otherlisted.txt exchange code F)."
        ),
    ),
)


# ── The curated security-supersession registry (AMENDMENT ruling 4 / M3) ──────
@dataclass(frozen=True)
class SecuritySupersession:
    """One EXACT-listing-key correction: a security wrongly minted as an independent
    row is corrected onto an existing, different, canonical row.

    NEVER a bare inception-code match on ANY venue — that was the pre-amendment
    defect: :func:`apply_security_supersession` matched any row whose inception code
    equalled a :data:`RenameEvent` ``.new`` on ANY venue, so a hostile cross-MIC
    scenario (a genuinely independent listing that happens to share the new symbol's
    bare code on a DIFFERENT exchange) got auto-tombstoned onto the wrong row. This
    registry is authored data (same evidence-string law as :data:`RENAME_EVENTS`) —
    curation ratifies each correction by its EXACT ``listing_key``, never a pattern
    the builder infers on its own.
    """

    listing_key: str
    canonical_id: str
    evidence: str
    on: date


SECURITY_SUPERSESSIONS: tuple[SecuritySupersession, ...] = (
    SecuritySupersession(
        listing_key="US-XNYS-VMRK",
        canonical_id="SEC:US-XNYS-EQR",
        on=date(2026, 8, 18),
        # V4-D2B1-R1 §1 E1 (verbatim, same evidence as the EQR->VMRK RenameEvent
        # above): SEC EDGAR CIK 0000906107 Form 8-K filed 2026-08-17, accession
        # 0001140361-26-033377, Item 5.03 — Equity Residential -> Vivmark Residential
        # eff. 2026-08-17; NYSE ticker EQR->VMRK eff. 2026-08-18. Corroborated by
        # data.sec.gov/submissions/CIK0000906107.json and
        # www.sec.gov/files/company_tickers.json (CIK 906107 -> VMRK).
        evidence=(
            "SEC EDGAR CIK 0000906107 Form 8-K filed 2026-08-17, accession "
            "0001140361-26-033377, Item 5.03: name changed Equity Residential -> "
            "Vivmark Residential eff. 2026-08-17; NYSE ticker EQR->VMRK eff. "
            "2026-08-18 (open of trading). Corroborated by "
            "data.sec.gov/submissions/CIK0000906107.json (name VIVMARK RESIDENTIAL, "
            "ticker VMRK, unbroken formerNames chain) and "
            "www.sec.gov/files/company_tickers.json (CIK 906107 -> VMRK)."
        ),
    ),
    SecuritySupersession(
        listing_key="US-XNYS-PSKY",
        canonical_id="SEC:US-XNAS-PSKY",
        on=date(2026, 10, 6),
        # Same evidence as the PSKY->SKYD RenameEvent above (verbatim, E1-style). This
        # entry is the CROSS-VENUE half of that rename: EQR->VMRK never needed one
        # because NYSE->NYSE re-derives the committed listing key exactly, while the
        # PSKY->SKYD Nasdaq->NYSE transfer re-derives US-XNYS-PSKY (today's venue plus
        # the chain's inception code) against a committed US-XNAS-PSKY (the inception
        # venue). The entry ratifies BOTH directions of the same fact by EXACT listing
        # key, never a bare inception-code match: mint_master_rows joins a resolution
        # that renders this key onto the canonical ACTIVE row (no second stable id, no
        # fence consult — the join resolves to an existing row), and
        # apply_security_supersession would tombstone a US-XNYS-PSKY row minted as an
        # independent duplicate exactly as the VMRK one was.
        evidence=(
            "SEC EDGAR CIK 0002041610 Form 8-K filed 2026-10-06, accession "
            "0001104659-26-113913, Items 2.01/5.03: on 2026-10-06 the Company "
            "transferred the listing of its Class B Common Stock from The Nasdaq "
            "Stock Market LLC to the New York Stock Exchange and changed the ticker "
            "symbol from PSKY to SKYD. Corroborated by "
            "data.sec.gov/submissions/CIK0002041610.json (name Skydance Corp, "
            "ticker SKYD, exchange NYSE, unbroken formerNames chain Paramount "
            "Skydance Corp 2025-08-07 -> 2026-10-06 under one CIK), Form 8-K filed "
            "2026-09-25 accession 0001104659-26-111034 Item 3.01 (listing-transfer "
            "notice), Form 8-A12B filed 2026-10-05 accession 0001104659-26-113569, "
            "and finance.yahoo.com/quote/SKYD (Yahoo serves the new symbol)."
        ),
    ),
    SecuritySupersession(
        listing_key="US-XNYS-KHC",
        canonical_id="SEC:US-XNAS-KHC",
        on=date(2026, 9, 14),
        # The cross-venue half of the KHC VenueTransfer above (same evidence).
        evidence=VENUE_TRANSFERS[0].evidence,
    ),
    SecuritySupersession(
        listing_key="US-TXSE-ET",
        canonical_id="SEC:US-XNYS-ET",
        on=date(2026, 10, 5),
        # The cross-venue half of the ET VenueTransfer above (same evidence).
        evidence=VENUE_TRANSFERS[1].evidence,
    ),
)


def _venue_transfer_covered_keys() -> frozenset[str]:
    """Symbols a :data:`VENUE_TRANSFERS` entry ratifies for a cross-venue join.

    Fail-closed pairing check: every transfer must have EXACTLY the matching
    :data:`SECURITY_SUPERSESSIONS` entry (``US-{to}-{sym}`` -> ``SEC:US-{from}-{sym}``)
    — a transfer without its exact-key supersession, or with a mismatched canonical
    id, is a curation defect raised here, never a silent join.
    """
    by_lk = {e.listing_key: e for e in SECURITY_SUPERSESSIONS}
    covered: set[str] = set()
    for t in VENUE_TRANSFERS:
        lk = f"US-{t.to_mic}-{t.symbol}"
        want = f"SEC:US-{t.from_mic}-{t.symbol}"
        entry = by_lk.get(lk)
        if entry is None or entry.canonical_id != want or t.from_mic == t.to_mic:
            raise ValueError(
                f"VENUE_TRANSFERS entry {t!r} lacks its exact SECURITY_SUPERSESSIONS "
                f"pair {lk} -> {want}"
            )
        covered.add(t.symbol)
    return frozenset(covered)

#: Renames the repo records WITHOUT a citable date.  Fiserv renamed FISV->FI in 2023
#: and the vendor LAGS it: Yahoo still serves the series under FISV
#: (`lib/ticker_aliases.YAHOO_FETCH_ALIASES["FI"] == "FISV"`), and so does the exchange
#: symbol directory (the 2026-08-10 snapshot carries FISV, "Fiserv, Inc. - Common
#: Stock", and carries no FI at all).  There is therefore NO vendor-side changeover day
#: to scope, and no in-repo source for the 2023 date, so both rows stay OPEN-BOUNDED.
#: An open bound is the ABSENCE of a claim about the boundary; inventing 2023-07-01 to
#: make the table look complete would be exactly the fabricated fact §4 forbids.
UNDATED_RENAMES: tuple[tuple[str, str, str], ...] = (
    (
        "FISV",
        "FI",
        "lib/ticker_aliases.py YAHOO_FETCH_ALIASES FI->FISV (vendor LAGS the rename); "
        "config.yml breadth.ticker_fixups FISV->FI; no in-repo date for the 2023 change",
    ),
)

#: Identity cases whose current symbol is verified but whose historical alias cannot be
#: represented by the builder's symbol-pair-only ``RenameEvent`` yet.  Fail closed:
#: minting an open-bounded row would answer a known prior issuer as the current one.
#:
#: ``B`` is not a plain ``GOLD -> B`` rename.  Barrick changed NYSE GOLD to B on
#: 2025-05-09, while Gold.com (formerly NASDAQ AMRK) reused NYSE GOLD on 2025-12-02.
#: A global GOLD/B pair would therefore collapse Barrick and Gold.com into one security.
#: Moreover, Barnes Group was the prior NYSE B holder until its 2025-01-27 delisting, so
#: an open historical B alias is independently false.  The full repair needs one
#: identity-scoped continuation plus one ratified reuse break; until that registered DOS
#: amendment exists, B remains named in coverage as unresolved and mints no row.
DEFERRED_IDENTITY_KEYS: dict[str, dict[str, str]] = {
    "B": {
        "reason": (
            "verified identity-scoped event required: NYSE B belonged to Barnes Group "
            "through 2025-01-27; Barrick Mining changed NYSE GOLD->B effective "
            "2025-05-09; Gold.com then reused NYSE GOLD effective 2025-12-02. A bare "
            "RenameEvent would collapse different issuers, so B is fail-closed pending "
            "a registered identity-scoped continuation+reuse amendment"
        ),
        "evidence": (
            "SEC Barnes Group 2025-01-27 8-K/Form 25; Barrick Mining 2025-05-07 "
            "Form 6-K Exhibit 99.2; Gold.com 2025-11-12 AMRK->NYSE GOLD transfer "
            "announcement; config/theme_graph_identity_breaks.yml GOLD"
        ),
    },
}

#: Already-materialized exception that this narrow roster repair only discloses.  The
#: committed GOLD alias predates the ratified break and is open-bounded across it.  The
#: append-only alias builder cannot close that row without producing an overlap, so the
#: same future identity-scoped DOS amendment must supersede it atomically.  Keeping this
#: in the receipt prevents a consumer from mistaking current coverage for temporal
#: authority in the interim.
DISCLOSED_IDENTITY_EXCEPTIONS: dict[str, dict[str, str]] = {
    "GOLD": {
        "reason": (
            "existing historical alias is not issuer-safe across 2025-12-02: the "
            "open GOLD row predates the ratified Gold.com reuse break and must not be "
            "treated as Barrick/miner history; replacement requires the same registered "
            "identity-scoped continuation+reuse amendment"
        ),
        "evidence": (
            "config/theme_graph_identity_breaks.yml GOLD; config.yml "
            "quality.reused_ticker_acks.GOLD"
        ),
    },
}


# ── Small helpers ─────────────────────────────────────────────────────────────
def unmodelled_renames(fixups: dict[str, str], migrations: dict[str, str]) -> list[str]:
    """Rename pairs the repo's own maps carry that this builder does not model.

    The failure mode this closes is the one the whole task exists to end: a rename gets
    added to ``breadth.ticker_fixups`` or ``quality.ticker_key_migrations`` — both
    TIMELESS, both one line — and the time-scoped table silently keeps answering with
    the old pairing, because nothing asks it to notice.  The reader still has to supply
    the DATE and the evidence by hand, which is the curation step (``detectors propose,
    curation ratifies``) and not something a seed loader may guess.

    A returned line is a FAILURE, not a hint: :func:`main` exits non-zero while this is
    non-empty, and both maps live in root ``config.yml``, which ``house-law-registry``
    declares in its manifest scope so a one-line rename PR actually reaches this check.
    Both halves are load-bearing — an advisory detector nothing can reach is two ways of
    being decoration.
    """
    modelled = {frozenset((e.old, e.new)) for e in RENAME_EVENTS}
    modelled |= {frozenset((old, new)) for old, new, _ in UNDATED_RENAMES}
    missing: list[str] = []
    for label, mapping in (("breadth.ticker_fixups", fixups),
                           ("quality.ticker_key_migrations", migrations)):
        for left, right in mapping.items():
            if frozenset((left, right)) not in modelled:
                missing.append(
                    f"{label} carries {left}->{right}, which scripts/build_security_master.py "
                    "does not model — add a RenameEvent (with its date and evidence) or an "
                    "UNDATED_RENAMES row, or the alias table answers the old pairing forever"
                )
    return missing


def _sha256(path: Path) -> str | None:
    """sha256 of a file, or None when it is absent (a missing seed is REPORTED)."""
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_sha() -> str | None:
    """HEAD sha, or None outside a git checkout.  Receipt provenance only.

    A run clock never enters an IDENTITY here (``DNR:LAW-RUN-CLOCK-IN-CONTENT-IDENTITY``)
    — ``code_version`` and ``generated_at`` live in the receipt, and the parquet bodies
    are byte-stable across re-runs on unchanged seeds.
    """
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=30, check=False,
        )
    except Exception:  # noqa: BLE001 — provenance is best-effort, never fatal
        return None
    sha = (out.stdout or "").strip()
    return sha or None


def _as_iso(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def _relpath(path: Path) -> str:
    """``path`` relative to :data:`ROOT` as a string, or the absolute path unchanged
    when it is not under ROOT at all (a test monkeypatching e.g. ``CIK_MAP_DIR`` at a
    ``tmp_path`` outside the checkout) — same guard as :func:`run_nightly_refresh`'s
    ``missing`` list, so a receipt key never raises on a path outside the repo."""
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


def _class_notation_variants(symbol: str) -> tuple[str, ...]:
    """``BRK-B`` -> ``('BRK-B', 'BRK.B')``.

    Spec §6 names this seam explicitly: "``BRK-B``/``BRK.B`` become ``class_notation``".
    The two spellings are one security on one venue; only the vendor differs on the
    separator, so the directory lookup tries both before a name is called unresolved.
    """
    out = [symbol]
    if "-" in symbol:
        out.append(symbol.replace("-", "."))
    if "." in symbol:
        out.append(symbol.replace(".", "-"))
    seen: list[str] = []
    for item in out:
        if item not in seen:
            seen.append(item)
    return tuple(seen)


# ── Seed loading ──────────────────────────────────────────────────────────────
def load_universe() -> dict[str, dict]:
    """``{membership key: {'sources': [...], 'first_seen': date|None}}``.

    The membership key is the repo's STABLE join key by charter — ``lib/ticker_aliases``
    says it outright: "Site copy, page slugs and ledger keys keep the membership
    ticker; this only ever decides what string goes to the vendor."
    """
    import pandas as pd  # local: keeps the module importable without pandas

    universe: dict[str, dict] = {}

    def note(ticker: str, source: str, seen: date | None) -> None:
        row = universe.setdefault(ticker, {"sources": [], "first_seen": None})
        if source not in row["sources"]:
            row["sources"].append(source)
        if seen is not None and (row["first_seen"] is None or seen < row["first_seen"]):
            row["first_seen"] = seen

    if CONSTITUENTS.exists():
        frame = pd.read_parquet(CONSTITUENTS)
        for ticker in frame.index.astype(str):
            note(ticker.strip().upper(), "breadth.constituents", None)

    if MIDCAP_CONSTITUENTS.exists():
        frame = pd.read_parquet(MIDCAP_CONSTITUENTS)
        for ticker in frame.index.astype(str):
            note(ticker.strip().upper(), "midcap_breadth.constituents", None)

    if SMALLCAP_CONSTITUENTS.exists():
        frame = pd.read_parquet(SMALLCAP_CONSTITUENTS)
        for ticker in frame.index.astype(str):
            note(ticker.strip().upper(), "smallcap_breadth.constituents", None)

    if MEMBERSHIP.exists():
        payload = json.loads(MEMBERSHIP.read_text())
        for basket_id, basket in (payload.get("baskets") or {}).items():
            for member in basket.get("members") or []:
                ticker = str(member.get("ticker") or "").strip().upper()
                if not ticker:
                    continue
                added = member.get("added")
                seen: date | None = None
                if added:
                    try:
                        seen = date.fromisoformat(str(added))
                    except ValueError:
                        seen = None
                note(ticker, f"baskets.membership:{basket_id}", seen)

    return universe


def load_delisted() -> dict[str, dict]:
    """``{ticker: row}`` from the exit ledger, via its own reader (never re-parsed here)."""
    from lib import delisted_symbols

    delisted_symbols.ledger.cache_clear()
    return dict(delisted_symbols.ledger())


def load_directory() -> tuple[dict[str, str], dict[str, dict], str | None, Path | None]:
    """``({symbol: exchange code}, {symbol: structural flags}, snapshot date, path)``
    from the NEWEST snapshot.

    Newest by FILENAME stem, never by mtime: file mtimes in this repo are
    observer-stamped (a status sweep or a reflog expiry restamps whole trees), so an
    mtime-ordered "latest" is not a fact about the data.

    V4-D2B2-US §3: the second dict carries the snapshot's own STRUCTURAL flags
    (``etf``/``test_issue``/``is_preferred`` — the schema columns
    ``collectors/symbol_directory.py`` already writes) per symbol, consulted ONLY by
    the GMI-US common-equity eligibility gate (:func:`_gmi_us_eligibility_refusal`).
    The legacy curated universe never reads this dict — its own eligibility behavior
    is unchanged this wave (§3).
    """
    import pandas as pd

    if not SYMBOL_DIR_SNAPSHOTS.is_dir():
        return {}, {}, None, None
    files = sorted(p for p in SYMBOL_DIR_SNAPSHOTS.glob("*.parquet"))
    if not files:
        return {}, {}, None, None
    newest = files[-1]
    frame = pd.read_parquet(newest)
    mapping = {
        str(sym).strip().upper(): str(exch).strip().upper()
        for sym, exch in zip(frame["symbol"], frame["exchange"])
    }
    flags = {
        str(sym).strip().upper(): {
            "etf": bool(etf), "test_issue": bool(test_issue),
            "is_preferred": bool(is_preferred),
        }
        for sym, etf, test_issue, is_preferred in zip(
            frame["symbol"], frame["etf"], frame["test_issue"], frame["is_preferred"]
        )
    }
    return mapping, flags, newest.stem, newest


def load_cik_map() -> tuple[dict[str, tuple[str, str]], str | None, Path | None, frozenset[str]]:
    """``({current symbol: (zero-padded 10-digit CIK, SEC registrant title)}, snapshot
    date, path, ambiguous_tickers)`` from the NEWEST weekly
    ``data/symbol_directory/cik_map/*.parquet`` (V4-D2B1 §1).  Newest by FILENAME
    stem, never by mtime — same reasoning as :func:`load_directory`: this repo's
    file mtimes are observer-stamped.

    Ticker is a unique key on the MEASURED source (2026-08-18: 10,398 rows, 7,998
    CIKs, zero ticker->multi-CIK), but V4-D2B1 FIX 7 (m1) stops trusting that as an
    invariant: a ticker seen with MORE THAN ONE DISTINCT CIK in the same snapshot is
    REMOVED from ``mapping`` entirely (never a silent first-wins pick) and named in
    ``ambiguous_tickers`` instead, so a security whose evidence join hits it can be
    typed ``AMBIGUOUS`` — reserved, fail-closed, spec §3 — rather than silently
    resolving (or missing evidence) on whichever row happened to be read first.
    """
    import pandas as pd

    if not CIK_MAP_DIR.is_dir():
        return {}, None, None, frozenset()
    files = sorted(p for p in CIK_MAP_DIR.glob("*.parquet"))
    if not files:
        return {}, None, None, frozenset()
    newest = files[-1]
    frame = pd.read_parquet(newest)
    mapping: dict[str, tuple[str, str]] = {}
    ambiguous: set[str] = set()
    for ticker, cik, title in zip(frame["ticker"], frame["cik"], frame["title"]):
        t = str(ticker).strip().upper()
        c = f"{int(cik):010d}"
        if t in ambiguous:
            continue
        existing = mapping.get(t)
        if existing is None:
            mapping[t] = (c, str(title))
        elif existing[0] != c:
            # A SECOND, DIFFERENT CIK for a ticker already seen — the ticker is
            # ambiguous on this snapshot; remove it rather than keep the first CIK.
            ambiguous.add(t)
            del mapping[t]
    return mapping, newest.stem, newest, frozenset(ambiguous)


def load_config_maps() -> tuple[dict[str, str], dict[str, str]]:
    """``(breadth.ticker_fixups, quality.ticker_key_migrations)`` — both TIMELESS maps."""
    raw = config.load()
    fixups = dict((raw.get("breadth") or {}).get("ticker_fixups") or {})
    migrations = dict((raw.get("quality") or {}).get("ticker_key_migrations") or {})
    return (
        {str(k).strip().upper(): str(v).strip().upper() for k, v in fixups.items()},
        {str(k).strip().upper(): str(v).strip().upper() for k, v in migrations.items()},
    )


# ── V4-D2B2-US — GMI-U.S. seed intake ───────────────────────────────────────────
# `research/prophet_v4/d2/D2B2_US_FROZEN_CONTRACT_2026-08-21.md` — Sol's bounded
# child of V4-D2 admitting the current source-supported U.S. GMI company population
# into the canonical Data OS security master through the EXISTING US
# resolve_universe()/mint_master_rows() pipeline (§0: NOT a separate mint stage like
# D2B2-CN-HK — US targets carry BOTH evidence rails, so a reused/renamed ticker must
# hit the R1 supersession/fence machinery structurally, exactly like any legacy key).


def _parse_us_company_node_id(node_id: str) -> str | None:
    """``"co:us:AAPL"`` -> ``"AAPL"``; ``None`` if not a US company node id.

    Mirrors, but deliberately does NOT import, :func:`_parse_cn_hk_company_node_id`
    (same "no shared parser exists, write ONE clean split" discipline the D2B2-CN-HK
    block above already states — this builder is UPSTREAM of the sidecar's own
    ``engine/theme_graph/identity_resolution.py::_best_effort_symbol`` parser).
    """
    parts = str(node_id or "").split(":", 2)
    if len(parts) != 3 or parts[0] != "co" or parts[1] != "us":
        return None
    symbol = parts[2].split("#", 1)[0].strip().upper()
    return symbol or None


def load_gmi_us_seeds() -> list[dict]:
    """The U.S. GMI company-node TARGET POPULATION (§2.1): distinct normalized codes
    from ``data/theme_graph/nodes.parquet`` where ``kind == "company"`` and
    ``market_scope == "us"``.

    Reads the upstream graph truth ONLY — never
    ``data/theme_graph/identity_resolution.parquet`` (the DERIVED sidecar; reading it
    here would invert the master/sidecar dependency, exactly the discipline
    :func:`load_cn_hk_seeds` already states for CN/HK).  Returns every US company
    node REGARDLESS of current resolution state (mint-once idempotency downstream
    makes it safe to pass the full population on every run rather than re-deriving
    "still unresolved" here — same reasoning as the CN/HK stage).

    Returns ``[{"symbol": <normalized code>, "node_id": <node id>}, ...]`` sorted by
    symbol, one row per distinct symbol (the theme graph carries one US company node
    per symbol at the D2B2-US pin — verified 1,238/1,238 distinct).
    """
    if not THEME_GRAPH_NODES_PATH.exists():
        return []
    import pandas as pd  # local import — this module otherwise has no pandas dep

    df = pd.read_parquet(THEME_GRAPH_NODES_PATH, columns=["node_id", "kind", "market_scope"])
    out: dict[str, str] = {}
    for node_id, kind, market_scope in zip(df["node_id"], df["kind"], df["market_scope"]):
        if str(kind) != "company":
            continue
        symbol = _parse_us_company_node_id(str(node_id))
        if symbol is None:
            continue
        if str(market_scope) != "us":
            continue  # defensive: node's own declared market_scope must agree
        out.setdefault(symbol, str(node_id))
    return [{"symbol": sym, "node_id": out[sym]} for sym in sorted(out)]


# ── Resolution ────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Resolution:
    """One membership key resolved (or not) to a venue and an inception code."""

    key: str
    listing_key: ListingKey | None
    inception_code: str | None
    exchange_symbol: str | None
    venue_source: str | None
    effective_at: date | None
    reason: str | None = None
    #: AMENDMENT R15 — True iff a venue MIC was found and successfully mapped
    #: (``mic is not None`` at the point this Resolution was built in
    #: :func:`resolve_universe`), regardless of whether the candidate ultimately
    #: resolved.  Set explicitly at every construction site so downstream typed-
    #: refusal classification (:func:`_gmi_us_unresolved_refusal`) discriminates
    #: `unsupported_venue` (mic never mapped) from `unrenderable_code` (mic
    #: mapped, but ``ListingKey`` construction itself failed) STRUCTURALLY —
    #: never by substring-matching the human-readable ``reason`` text.
    venue_mapped: bool = False


def _inception_code(key: str, directory_symbol: str | None) -> str:
    """The code the listing carried at INCEPTION — never today's symbol.

    Walks the rename chains BACKWARDS to their ROOT: a dated event (MMC->MRSH,
    SATS->ECHO) or an undated one (FISV->FI) whose NEW side is this key means the OLD
    side is the earlier code this repo can evidence.

    The membership key can sit on EITHER side of a chain, and that asymmetry is the
    whole MMC case: the repo's key is the OLD symbol (``MMC``, pinned by
    ``breadth.ticker_fixups``) while the venue's current spelling is the NEW one
    (``MRSH``).  Reaching for the directory spelling there would mint
    ``SEC:US-XNYS-MRSH`` — a stable id built on today's symbol, which is exactly the
    defect §D2 forbids.  So a key that appears anywhere in a chain resolves through the
    chain; only a key no rename mentions falls back to the exchange spelling
    (``BRK.B``, not the vendor's ``BRK-B``), because the venue is the authority on its
    own code.
    """
    backwards: dict[str, str] = {}
    forwards: dict[str, str] = {}
    for event in RENAME_EVENTS:
        backwards[event.new] = event.old
        forwards[event.old] = event.new
    for old, new, _ in UNDATED_RENAMES:
        backwards[new] = old
        forwards[old] = new

    if key not in backwards and key not in forwards:
        return (directory_symbol or key).upper()

    seen = {key}
    current = key
    while current in backwards:
        nxt = backwards[current]
        if nxt in seen:  # a cycle is a config defect, never a loop here
            break
        seen.add(nxt)
        current = nxt
    return current


def _current_symbol(inception_code: str) -> str:
    """Inception code -> this repo's own CURRENT symbol for the listing (V4-D2B1 §1
    evidence join law), walking the SAME rename records :func:`_inception_code` walks
    BACKWARD (``RENAME_EVENTS`` + ``UNDATED_RENAMES``) but FORWARDS to the chain's tip.

    This is deliberately this repo's OWN rename record, not "whatever Yahoo currently
    serves" — the two disagree for exactly the case the FI/FISV row exists to carry:
    Yahoo still serves the pre-rename ``FISV`` (the vendor lags), but this repo's own
    ``UNDATED_RENAMES`` records the venue-current name as ``FI``, and ``FI`` is the
    join key spec §1 asks for (the SEC registrant map is an independent, current
    observation of the same real-world fact — it does not follow Yahoo's lag).  For
    MMC/SATS, where the vendor LED the rename, this walk and Yahoo's current symbol
    agree (``MMC``->``MRSH``, ``SATS``->``ECHO``) because both ``RENAME_EVENTS`` rows
    were sourced from the same real-world change.

    A name no chain mentions returns itself unchanged — the venue is the authority on
    its own current spelling when this repo has recorded no rename for it.
    """
    forwards: dict[str, str] = {}
    for event in RENAME_EVENTS:
        forwards[event.old] = event.new
    for old, new, _ in UNDATED_RENAMES:
        forwards[old] = new

    seen = {inception_code}
    current = inception_code
    while current in forwards:
        nxt = forwards[current]
        if nxt in seen:  # a cycle is a config defect, never a loop here
            break
        seen.add(nxt)
        current = nxt
    return current


def _evidence_join_key(inception_code: str) -> str:
    """The CIK-map join key for one master row (V4-D2B1 §1): the security's current
    symbol (:func:`_current_symbol`), dot->dash normalized — the CIK map spells class
    suffixes with a dash (``BRK-B``) while the master spells them with a dot
    (``BRK.B``).  NEVER joins a historical/dated alias symbol against the CURRENT
    observation CIK map — that would be the two-clock violation spec §1 names (a
    reused ticker binding the wrong registrant); this function only ever answers
    "what is this security called today".
    """
    return _current_symbol(inception_code).replace(".", "-")


def _effective_at(universe_row: dict | None, delisted_row: dict | None,
                  snapshot_date: str | None) -> date | None:
    """The earliest DATED OBSERVATION in the committed seeds that this security existed.

    NOT an inception/listing date.  Spec §4 is explicit that no in-repo US listing-date
    source exists and that back-dating one from a store's earliest bar is fabrication,
    so this column carries the weaker, TRUE fact instead: the oldest day a committed
    seed in this repo says the name was there.  Candidates, earliest wins:

      * a basket member's ``added`` date (``data/baskets/membership.json``);
      * the exit ledger's ``last_session`` — the security demonstrably traded that day;
      * the symbol-directory snapshot date — a dated observation of a CURRENT listing.
    """
    candidates: list[date] = []
    if universe_row and universe_row.get("first_seen"):
        candidates.append(universe_row["first_seen"])
    if delisted_row and delisted_row.get("last_session"):
        try:
            candidates.append(date.fromisoformat(str(delisted_row["last_session"])))
        except ValueError:
            pass
    if snapshot_date:
        try:
            candidates.append(date.fromisoformat(snapshot_date))
        except ValueError:
            pass
    return min(candidates) if candidates else None


def resolve_universe(
    universe: dict[str, dict],
    delisted: dict[str, dict],
    directory: dict[str, str],
    snapshot_date: str | None,
    *, reference_probe_keys: frozenset[str] = frozenset(),
) -> list[Resolution]:
    """Resolve every seed key to a venue + inception code, or say why it could not be.

    Venue precedence, and the reason for it:
      1. the EXIT LEDGER, for a delisted name — the symbol directory is a *current*
         listing set and structurally cannot carry a finished tape;
      2. the SYMBOL DIRECTORY, under the vendor symbol this repo actually fetches
         (``lib.ticker_aliases.fetch_symbol``) and under both class-notation spellings;
      3. UNRESOLVED, named in the report.
    """
    keys = sorted(set(universe) | set(delisted))
    out: list[Resolution] = []
    for key in keys:
        delisted_row = delisted.get(key)
        universe_row = universe.get(key)
        effective = _effective_at(universe_row, delisted_row, snapshot_date)

        deferred = DEFERRED_IDENTITY_KEYS.get(key)
        if deferred is not None:
            out.append(
                Resolution(
                    key,
                    None,
                    None,
                    None,
                    "operator-ratified fail-closed identity exception",
                    effective,
                    deferred["reason"],
                )
            )
            continue

        mic: str | None = None
        venue_source: str | None = None
        directory_symbol: str | None = None
        reason: str | None = None

        if delisted_row:
            exchange = str(delisted_row.get("exchange") or "").strip().upper()
            mic = DELISTED_EXCHANGE_MIC.get(exchange)
            venue_source = f"config/delisted_symbols.yml:{key}.exchange={exchange or '<none>'}"
            if mic is None:
                reason = (
                    f"exit-ledger exchange {exchange or '<none>'!r} has no MIC in "
                    "lib/dataos/identity.KNOWN_MICS"
                )

        if mic is None and reason is None:
            fetch_symbol = ticker_aliases.fetch_symbol(key)
            for candidate in (
                *_class_notation_variants(fetch_symbol),
                *_class_notation_variants(key),
            ):
                exchange = directory.get(candidate)
                if exchange is None:
                    continue
                directory_symbol = candidate
                mic = EXCHANGE_MIC.get(exchange)
                if key in reference_probe_keys and key == "SPY" and exchange == "P":
                    mic = ARCX
                venue_source = (
                    f"data/symbol_directory/snapshots/{snapshot_date}.parquet:"
                    f"{candidate}.exchange={exchange}"
                )
                if mic is None:
                    reason = (
                        f"listed on exchange code {exchange!r} "
                        "(collectors/symbol_directory.py:184-185: P=NYSE Arca, Z=BATS, "
                        "V=Investors Exchange) which has no MIC in "
                        "lib/dataos/identity.KNOWN_MICS"
                    )
                break
            else:
                reason = (
                    "absent from the newest symbol-directory snapshot under "
                    f"{fetch_symbol!r} or {key!r} (and from the exit ledger) — venue unknown"
                )

        if mic is None:
            # AMENDMENT R15 — venue_mapped=False: the mic itself was never found or
            # never mapped, structurally the `unsupported_venue` class.
            out.append(
                Resolution(key, None, None, None, venue_source, effective, reason,
                          venue_mapped=False)
            )
            continue

        code = _inception_code(key, directory_symbol)
        try:
            listing_key = ListingKey(DEFAULT_COUNTRY, mic, code)
        except IdentityError as exc:
            # AMENDMENT R15 — venue_mapped=True: the mic WAS found and mapped; only
            # the CODE failed to render into the closed listing-key grammar —
            # structurally the `unrenderable_code` class, never conflated with an
            # unmapped venue.
            out.append(
                Resolution(key, None, None, directory_symbol, venue_source, effective, str(exc),
                          venue_mapped=True)
            )
            continue
        out.append(
            Resolution(key, listing_key, code, directory_symbol, venue_source, effective, None,
                      venue_mapped=True)
        )
    return out


# ── Alias construction ────────────────────────────────────────────────────────
def build_alias_rows(resolutions: list[Resolution], ids: dict[str, str]) -> list[AliasRow]:
    """Every ``(vendor, vendor_symbol, security_id, valid_from, valid_to)`` this seed set supports.

    TWO FAMILIES, per the clock each answers (see the vendor block at the top):

    * HISTORICAL-NAMING spaces (``yahoo``, ``membership``, ``ledger``) get either ONE
      open-bounded row (the space never moved, or the day it moved is not citable) or a
      DATED PAIR straddling the rename.  The pair is what makes the table answer
      differently either side of the boundary, which is the whole deliverable.
    * CURRENT-CATALOG spaces (``yahoo_fetch``, ``store``) get ONE OPEN-BOUNDED row at
      today's symbol per security — or, since 2026-08-28 (AMENDMENT ruling 9 / m3), a
      DATED PAIR when a RenameEvent names the space in ``vendors`` AND the security is
      the renamed one (inception-code gate below): the repo's own stored key genuinely
      changed on a day (EQR->VMRK), and "what key did the repo file this under on date
      D" needs the boundary. Either way exactly ONE row is open-bounded per security,
      which is what ``VendorAliasTable`` requires (the constructor refuses two rows
      overlapping on ``(vendor, security_id)``) — "what do I call it today" still has
      exactly one answer. Dated or not, current-catalog rows are NEVER historical-
      naming evidence: ``engine/theme_graph/identity_resolution.py`` excludes these
      spaces by VENDOR IDENTITY in HISTORICAL mode (``_CURRENT_CATALOG_VENDORS``).

      V4-D2B1-R1: a dedup-onto-one-master-row rename (§2.3 — e.g. EQR/VMRK, where BOTH
      the pre-rename and post-rename symbol stay live universe keys on purpose, unlike
      MMC/SATS where a config fixup collapses the pair to one key upstream) means MORE
      THAN ONE resolution can share one ``sec``.  Only the ROOT resolution — the one
      whose OWN key equals its OWN ``inception_code``, i.e. the key this repo's stores
      actually carry — contributes a current-catalog row for that security; a chain
      member reached only via the rename (``res.key != res.inception_code``) never
      does, because "what do I call it today" cannot have two simultaneously-open
      answers in one vendor space.
    """
    dated: dict[tuple[str, str], RenameEvent] = {}
    for event in RENAME_EVENTS:
        for vendor in event.vendors:
            dated[(vendor, event.old)] = event
            dated[(vendor, event.new)] = event

    # The store-key ratification map for the chain-member gate below (config's own
    # record of "the repo's stored key moved on a ratified day").
    _, store_key_migrations = load_config_maps()

    rows: list[AliasRow] = []
    current_by_sec: dict[tuple[str, str], tuple[str, bool]] = {}
    for res in resolutions:
        if res.listing_key is None:
            continue
        if res.key not in ids:
            # V4-D2B1-R1 AMENDMENT ruling 1 (B1): a REFUSED resolution — the
            # pending-transition fence or a resurrection refusal — never reaches
            # `ids` (mint_master_rows deliberately does not assign one). Before this
            # fix, `ids[res.key]` below raised KeyError for exactly this shape,
            # which meant a real refusal crashed build() instead of merely being
            # disclosed. A refused resolution contributes NO alias row of any kind
            # (historical or current-catalog) — there is no security to alias it to.
            continue
        sec = ids[res.key]

        historical = {
            VENDOR_MEMBERSHIP: res.key,
            VENDOR_YAHOO: ticker_aliases.fetch_symbol(res.key),
        }
        # The ledger space only gets a row where its own ratified map has something to
        # say; inventing a `ledger` row for every name would claim a key space this
        # builder has not read.  quality.ticker_key_migrations is that map.
        for event in RENAME_EVENTS:
            if VENDOR_LEDGER in event.vendors and res.key in (event.old, event.new):
                historical[VENDOR_LEDGER] = res.key

        # `res.key` IS the current store key: the universe seeds carry today's key
        # (ECHO, not SATS) and `breadth.ticker_fixups` pins a vendor-led rename back to
        # it (MRSH -> MMC), which is why data/baskets/ohlcv/MMC.parquet is the file that
        # exists while Yahoo is fetched under MRSH.
        #
        # `store` (like `yahoo_fetch`) is a current-catalog space: the is_root-gated
        # winner per security is emitted below, dated through RENAME_EVENTS since
        # 2026-08-28 (AMENDMENT ruling 9 / m3, completed — the ruling-6 conflict that
        # deferred it was resolved by the one-time hand-migration of the committed
        # open `(store, EQR, ...)` row; see the RenameEvent comment at the top).
        current = {
            VENDOR_YAHOO_FETCH: ticker_aliases.fetch_symbol(res.key),
            VENDOR_STORE: res.key,
        }
        is_root = res.key == res.inception_code
        # A CHAIN MEMBER (res.key != its inception_code) may speak for the
        # current-catalog spaces ONLY when the repo's own records ratify its key as
        # the one stored/fetched today: `quality.ticker_key_migrations` (SATS->ECHO —
        # data/stocks/ECHO.parquet is the file that exists) or a RenameEvent that
        # dates the store space (EQR->VMRK, post-#4622 migration). PSKY->SKYD carries
        # NEITHER (the store-key migration is a separate #4622-protocol act), so the
        # stores still key PSKY and a fresh open (store, SKYD, ...) row would assert
        # a falsehood AND overlap the committed open (store, PSKY, ...) row — the
        # exact undated-replacement shape `_prune_stale_aliases` fails closed on.
        chain_member_ratified = (
            any(
                res.key in (event.old, event.new) and VENDOR_STORE in event.vendors
                for event in RENAME_EVENTS
            )
            or store_key_migrations.get(res.inception_code) == res.key
        )
        dated_rename_member = any(res.key in (event.old, event.new) for event in RENAME_EVENTS)
        unratified_rename_member = dated_rename_member and not is_root and not chain_member_ratified

        for vendor, symbol in historical.items():
            event = dated.get((vendor, symbol))
            if event is None:
                rows.append(AliasRow(vendor, symbol, sec, None, None))
                continue
            # valid_from INCLUSIVE / valid_to EXCLUSIVE: on the boundary day itself the
            # NEW symbol is the answer and the OLD one is already out of scope.
            rows.append(AliasRow(vendor, event.old, sec, None, event.on))
            rows.append(AliasRow(vendor, event.new, sec, event.on, None))

        for vendor, symbol in current.items():
            key = (vendor, sec)
            prior = current_by_sec.get(key)
            # The gate covers exactly ONE shape: a NON-ROOT key that a DATED
            # RenameEvent names, whose store key no RenameEvent-with-store and no
            # `ticker_key_migration` ratifies (today: SKYD — the comment above). A
            # notation variant that no rename mentions (MOG-A/MOG.A, BRK-B, BF-B —
            # `_inception_code` falls back to the directory's DOT spelling for any
            # key no rename mentions, so `res.key != res.inception_code` alone
            # cannot tell a chain member from a dot/dash notation variant) and an
            # UNDATED_RENAMES key (FI) keep origin/main's
            # `prior is None or is_root` behaviour: their fresh open store/
            # yahoo_fetch rows are TRUE rows, and suppressing them (#8828 review F1)
            # drops live current-catalog rows nothing reports and leaves committed
            # carry-over as the only survivor.
            if is_root or (prior is None and not unratified_rename_member):
                current_by_sec[key] = (symbol, is_root)

    for (vendor, sec), (symbol, _is_root) in current_by_sec.items():
        # AMENDMENT ruling 9 (m3): a current-catalog space whose symbol a RenameEvent
        # dates (event.vendors naming this vendor) emits the dated old/new pair per
        # the same derivation rules as the historical spaces above, so `store` can
        # answer "what key did the repo file this under on date D" across a ratified
        # key migration (EQR->VMRK). A symbol no event dates keeps the single
        # open-bounded row. The `dated` map is keyed by SYMBOL and carries no
        # security identity, and this repo tracks live ticker reuse — so the pair is
        # emitted ONLY for the security the event actually renamed (the one whose id
        # the event's own keys resolve to); a stranger security that merely reuses
        # one of the event's symbol strings keeps its plain open-bounded row.
        event = dated.get((vendor, symbol))
        renamed_sec = (ids.get(event.new) or ids.get(event.old)) if event else None
        if event is None or sec != renamed_sec:
            rows.append(AliasRow(vendor, symbol, sec, None, None))
        else:
            rows.append(AliasRow(vendor, event.old, sec, None, event.on))
            rows.append(AliasRow(vendor, event.new, sec, event.on, None))

    # Dedup on the full grain — a security reached through two spaces that happen to
    # agree must not produce two identical rows (which would also read as an overlap).
    unique: dict[tuple, AliasRow] = {}
    for row in rows:
        unique[(row.vendor, row.vendor_symbol, row.security_id, row.valid_from, row.valid_to)] = row
    return [unique[k] for k in sorted(unique, key=lambda k: (k[0], k[1], k[2], str(k[3]), str(k[4])))]


# ── V4-D2B2-CN-HK — China/HK canonical identity admission ──────────────────────
# Sol (AI CEO) authorized exactly this one bounded child of V4-D2 (Data OS identity):
# admit the current source-supported China/HK listing population into THIS canonical
# builder, or return a typed refusal for every targeted object.
# `research/prophet_v4/d2/D2B2_CN_HK_FROZEN_CONTRACT_2026-08-20.md` is the binding
# spec.  Deliberately a SEPARATE, additive stage rather than an extension of the
# US-shaped `resolve_universe`/`mint_master_rows` pipeline above: CN/HK has no
# membership.json-shaped universe seed, no rename-event history modelled (current-
# identity semantics only, boundary 7) and — this era — no issuer-evidence class
# (boundary 4/6: every new row mints `issuer_state=None`, exactly like a brand-new US
# row, and is settled to `NO_ISSUER_EVIDENCE` by the EXISTING `apply_issuer_correction`
# pass the caller already runs over the full row set; no CN/HK issuer-grouping
# evidence is introduced, so A/H pairs and SOE siblings never get grouped absent
# deterministic evidence — there is none here, by design).


def _parse_cn_hk_company_node_id(node_id: str) -> tuple[str, str] | None:
    """``"co:cn:000001.SZ"`` -> ``("cn", "000001.SZ")``; ``None`` if not a cn/hk
    company node id.

    Mirrors, but deliberately does NOT import, the D2A sidecar's own node-id split
    (``engine/theme_graph/identity_resolution.py::_best_effort_market`` /
    ``::_best_effort_symbol``, ``co:<market>:<SYMBOL>[#<epoch>]``): this builder is
    UPSTREAM of that sidecar (master -> sidecar, never the reverse), so importing
    from ``engine/theme_graph`` here would invert the dependency.  Same "no shared
    parser exists, write ONE clean split" discipline the D2A spec itself states.
    """
    parts = str(node_id or "").split(":", 2)
    if len(parts) != 3 or parts[0] != "co" or parts[1] not in ("cn", "hk"):
        return None
    symbol = parts[2].split("#", 1)[0].strip().upper()
    return (parts[1], symbol) if symbol else None


def load_cn_hk_seeds() -> list[dict]:
    """The China/HK company-node TARGET POPULATION (V4-D2B2-CN-HK boundary 1: the
    child's target N is its own start-pin census, not the 1,868-total observation).

    Reads ``data/theme_graph/nodes.parquet`` — upstream graph truth, never
    ``data/theme_graph/identity_resolution.parquet`` (the DERIVED sidecar; reading it
    here would invert the master/sidecar dependency).  This is this stage's SEEDS,
    parallel in role to :func:`load_universe` for the US stage, but sourced from the
    graph's own company population: no CN/HK-shaped ``membership.json`` /
    ``constituents.parquet`` universe seed exists in this repo.

    Returns every ``kind == "company"`` node whose market is cn/hk, REGARDLESS of
    current resolution state — mint-once idempotency in :func:`mint_cn_hk_rows`
    (an already-minted listing key is skipped) makes it safe to pass the full
    population on every run rather than re-deriving "still unresolved" here.
    """
    if not THEME_GRAPH_NODES_PATH.exists():
        return []
    import pandas as pd  # local import — this module otherwise has no pandas dep

    df = pd.read_parquet(THEME_GRAPH_NODES_PATH, columns=["node_id", "kind", "market_scope"])
    out: list[dict] = []
    for node_id, kind, market_scope in zip(df["node_id"], df["kind"], df["market_scope"]):
        if str(kind) != "company":
            continue
        parsed = _parse_cn_hk_company_node_id(str(node_id))
        if parsed is None:
            continue
        market, symbol = parsed
        if str(market_scope) != market:
            continue  # defensive: node's own declared market_scope must agree
        out.append({"node_id": str(node_id), "market": market, "symbol": symbol})
    return sorted(out, key=lambda r: r["node_id"])


def load_cninfo_evidence() -> tuple[dict[str, dict], str | None]:
    """China A-share primary-source EXISTENCE evidence (boundary 5: primary sources
    only — exchanges, CNInfo/HKEX, GLEIF, lawful official registries; explicitly no
    Tushare/Qichacha/Tianyancha/Wind/purchased resolver, CN-B #5947 NO-BUY).

    ``data/china_filings/filings.parquet`` is ``collectors/china_filings.py``'s
    committed accrual of CNInfo (巨潮资讯网 — the CSRC/exchange-designated official
    disclosure platform for SSE+SZSE) announcement metadata: ``sec_code``,
    ``sec_name``, ``org_id`` (CNInfo's own stable registrant id; VERIFIED zero
    multi-org_id codes in the committed data at the D2B2 pin) per announcement,
    accruing forward since first collection.

    This returns ONLY an EXISTENCE + observation-date fact per code — "CNInfo
    carries at least one disclosure naming this code as of <date>" — NEVER a name.
    ``security_master.parquet`` has no name column (:data:`MASTER_COLUMNS`) and this
    builder mints no name/legal_name surface for CN/HK: CNInfo's ``sec_name`` is the
    disclosure SHORT name, not a verified legal name, and it demonstrably changes
    over time in this exact committed data (sec_code 000430: "ST张家界" through
    2026-05-15, "张家界" from 2026-07-10 — a real ST-flag removal) — exactly why
    current-identity-only semantics (boundary 7) keep it out of any stored identity
    column rather than fabricating a historical name lineage.

    The ``exchange`` column (``collectors/china_filings.py::_parse_announcement``)
    records which CNInfo QUERY BATCH (``column=sse|szse``) returned the row, not a
    verified venue — sampled at the D2B2 pin, SZSE-range codes (300xxx, 002xxx) were
    filed under ``exchange="sse"``.  This function never reads it; venue (SH/SZ/BJ
    board) is derived deterministically from the CODE ITSELF via
    ``lib.dataos.identity.normalize_cn_symbol``/``cn_board`` (already spec-mandated,
    never trusted from this collector's own labelling).

    Returns ``({6-digit code: {"effective_at": "YYYY-MM-DD"}}, newest publish date
    seen)``.  ``effective_at`` is the EARLIEST dated observation in this committed
    window — the same "not a listing date" convention :func:`_effective_at` states
    for the US stage — and the window itself is a forward-accruing recent slice
    (the collector's own docstring: "forward-only"), so a code absent here is
    "no evidence YET", never "not a real listing" (a coverage limitation, disclosed
    in the receipt, never asserted as completeness — this module's own "Coverage is
    a REPORTED NUMBER, never an asserted completeness").
    """
    if not CHINA_FILINGS_PATH.exists():
        return {}, None
    import pandas as pd

    df = pd.read_parquet(CHINA_FILINGS_PATH, columns=["sec_code", "publish_ts"])
    if df.empty:
        return {}, None
    df = df.dropna(subset=["sec_code", "publish_ts"])
    df = df.assign(sec_code=df["sec_code"].astype(str).str.strip().str.zfill(6))
    df = df.assign(publish_date=pd.to_datetime(df["publish_ts"], errors="coerce", utc=True).dt.date)
    df = df.dropna(subset=["publish_date"])
    evidence: dict[str, dict] = {}
    newest = None
    for code, group in df.groupby("sec_code"):
        earliest = group["publish_date"].min()
        latest = group["publish_date"].max()
        evidence[code] = {"effective_at": earliest.isoformat()}
        if newest is None or latest > newest:
            newest = latest
    return evidence, (newest.isoformat() if newest is not None else None)


def load_hk_shorts_evidence() -> tuple[dict[str, dict], str | None]:
    """HK primary-source EXISTENCE evidence (boundary 5) — SFC (Securities and
    Futures Commission, HK's statutory regulator) official Short Position Reports
    (``data/hk_shorts/positions.parquet``) and HKEX's OWN published turnover
    statistics (``data/hk_shorts/turnover.parquet``,
    ``collectors/hk_shorts.py::_HKEX_TURNOVER_URL`` = ``www.hkex.com.hk``) — both
    lawful official sources.  Same existence-only, no-name-stored discipline as
    :func:`load_cninfo_evidence`; see that docstring for the reasoning (this
    builder's ``security_master.parquet`` schema has no name column at all).

    5-digit zero-padded HK codes (the canonical form,
    ``lib.dataos.identity.normalize_hk_symbol``).  Returns the same
    ``({code: {"effective_at": ...}}, newest date seen)`` shape.
    """
    import pandas as pd

    frames = []
    for path, code_col, date_col in (
        (HK_SHORTS_POSITIONS_PATH, "stock_code", "date"),
        (HK_SHORTS_TURNOVER_PATH, "stock_code", "date"),
    ):
        if not path.exists():
            continue
        frame = pd.read_parquet(path, columns=[code_col, date_col])
        frame = frame.rename(columns={code_col: "code", date_col: "date"})
        frames.append(frame)
    if not frames:
        return {}, None
    df = pd.concat(frames, ignore_index=True)
    df = df.dropna(subset=["code", "date"])
    df = df.assign(code=df["code"].astype(str).str.strip().str.zfill(5))
    df = df.assign(date=pd.to_datetime(df["date"], errors="coerce").dt.date)
    df = df.dropna(subset=["date"])
    evidence: dict[str, dict] = {}
    newest = None
    for code, group in df.groupby("code"):
        earliest = group["date"].min()
        latest = group["date"].max()
        evidence[code] = {"effective_at": earliest.isoformat()}
        if newest is None or latest > newest:
            newest = latest
    return evidence, (newest.isoformat() if newest is not None else None)


def mint_cn_hk_rows(
    master_rows: list[dict],
    seeds: list[dict],
    cninfo_evidence: dict[str, dict],
    hk_evidence: dict[str, dict],
    now: str,
) -> tuple[list[dict], list[AliasRow], dict]:
    """V4-D2B2-CN-HK — admit China/HK company-node targets whose numeric code has
    committed primary-source evidence (CNInfo for CN; SFC/HKEX for HK) into the
    canonical master, via the SAME mint-once-by-listing-key law as
    :func:`mint_master_rows` (boundary 3: canonical builder only, no parallel
    allocator, no hand-written master rows).  Every target finishes RESOLVED (a new
    master row + a current-catalog vendor-alias row) or a NAMED typed refusal
    (``no_committed_primary_source_evidence`` / ``unparseable_symbol``) — boundary 8,
    no silent drop.

    ``listing_key``/``security_id`` are minted via ``lib.dataos.identity``'s
    EXISTING, already-spec'd CN/HK grammars (``normalize_cn_symbol``,
    ``normalize_hk_symbol``) — no new allocator, no new grammar (boundary 3).

    Conservative by design (boundary 4, D2B1 issuer law preserved): every new row
    mints with ``issuer_state=None`` (unstamped), exactly like a brand-new US row in
    :func:`mint_master_rows`.  The CALLER's subsequent ``apply_issuer_correction``
    pass (run unmodified, over the full accumulated row set) settles it to
    ``NO_ISSUER_EVIDENCE`` — the US SEC CIK map has no CN/HK entries, so every one of
    these rows lands there this era.  NO issuer-grouping evidence class is
    introduced for CN/HK: CNInfo's ``org_id`` / HK's ``stock_name`` are consulted
    only as EXISTENCE evidence to decide whether to mint at all, never for issuer
    identity.  This trivially satisfies boundary 6 (A/H pairs — e.g. ICBC
    ``SEC:CN-XSHG-601398`` / ``SEC:HK-XHKG-01398`` — stay separate securities,
    sharing an issuer only on deterministic evidence; there is none here, so none is
    ever inferred) and keeps boundary 4 fully intact (no foreign identifier —
    USCC/org_id/exchange code — is ever promoted to canonical identity; Mastermind
    ids remain canonical).

    A vendor-alias row (``vendor=VENDOR_THEME_GRAPH_NATIVE``, open-bounded
    current-catalog) is emitted for every minted row, carrying the GMI node's OWN
    suffix-qualified symbol spelling — see :data:`VENDOR_THEME_GRAPH_NATIVE`'s
    docstring for why this makes vendor-alias resolution (D2A rule 6) the ordinary
    path for every admission here, not a special "alias-only" case.

    Mint-once/idempotent: a seed whose rendered listing key already has a row in
    ``master_rows`` (a prior run's mint, present via ``_read_existing``) is skipped
    outright — this stage never touches, corrects or re-derives a previously-minted
    CN/HK row (current-identity semantics only, boundary 7).

    Returns ``(master_rows + new rows, new alias rows, coverage dict)``.
    """
    already_minted = {str(r["listing_key"]) for r in master_rows}
    new_rows: list[dict] = []
    alias_rows: list[AliasRow] = []
    refusals: dict[str, list[dict]] = {"cn": [], "hk": []}
    resolved_this_run: dict[str, int] = {"cn": 0, "hk": 0}

    for seed in seeds:
        market = seed["market"]
        symbol = seed["symbol"]
        node_id = seed["node_id"]
        try:
            listing_key = (
                normalize_cn_symbol(symbol) if market == "cn" else normalize_hk_symbol(symbol)
            )
        except IdentityError as exc:
            refusals[market].append({
                "node_id": node_id, "symbol": symbol,
                "reason": f"unparseable_symbol: {exc}",
            })
            continue
        rendered = listing_key.render()
        if rendered in already_minted:
            continue  # already minted a prior run — mint-once, never re-touch
        evidence_table = cninfo_evidence if market == "cn" else hk_evidence
        evidence = evidence_table.get(listing_key.code)
        if evidence is None:
            refusals[market].append({
                "node_id": node_id, "symbol": symbol, "listing_key": rendered,
                "reason": "no_committed_primary_source_evidence",
            })
            continue
        sec = security_id(listing_key)
        new_rows.append({
            "security_id": sec,
            "issuer_id": None,
            "issuer_state": None,
            "issuer_cik": None,
            "issuer_evidence_snapshot": None,
            "listing_key": rendered,
            "country": listing_key.country,
            "mic": listing_key.mic,
            "inception_code": listing_key.code,
            "effective_at": f"{evidence['effective_at']}T00:00:00",
            "ingested_at": now,
            "security_state": None,
            "superseded_by": None,
        })
        already_minted.add(rendered)
        alias_rows.append(AliasRow(VENDOR_THEME_GRAPH_NATIVE, symbol, sec, None, None))
        resolved_this_run[market] += 1

    coverage = {
        "target_n": {
            "cn": sum(1 for s in seeds if s["market"] == "cn"),
            "hk": sum(1 for s in seeds if s["market"] == "hk"),
        },
        "resolved_this_run": resolved_this_run,
        "refused_this_run": {m: len(v) for m, v in refusals.items()},
        "refusals_this_run": refusals,
    }
    return master_rows + new_rows, alias_rows, coverage


# ── Mint-once-and-store ───────────────────────────────────────────────────────
def _read_existing(path: Path, columns: tuple[str, ...],
                   dtypes: dict[str, str],
                   allow_missing: frozenset[str] = frozenset()) -> list[dict]:
    """Committed rows as plain dicts of ISO strings / None.  The stored value is the AUTHORITY.

    ``allow_missing`` names declared columns a COMMITTED file is allowed to lack —
    filled with ``None`` rather than raising.  This is the era-migration seam
    (V4-D2B1 §4): a pre-D2B1 ``security_master.parquet`` has no issuer-axis columns
    at all, and reading it should mean "not yet migrated by this era"
    (``issuer_state is None``), not a schema-mismatch refusal.  Every OTHER declared
    column absent from a committed file is still a hard failure — this does not widen
    the refusal to genuine schema drift.
    """
    import pandas as pd

    if not path.exists():
        return []
    frame = pd.read_parquet(path)
    if "alias_kind" in columns and any(
        name in frame.columns and frame[name].notna().any()
        for name in ("attempt_id", "alias_family_id", "alias_revision_id")
    ):
        raise IdentityError("revisioned alias requires observation history writer; refusing projection")
    missing = [c for c in columns if c not in frame.columns]
    hard_missing = [c for c in missing if c not in allow_missing]
    if hard_missing:
        raise SystemExit(
            f"{path} is missing declared column(s) {hard_missing} — refusing to append to an "
            "artifact whose schema does not match config/dataset_registry.yml"
        )
    present = [c for c in columns if c not in missing]
    rows: list[dict] = []
    for record in frame[present].to_dict("records"):
        if "alias_kind" in columns and pd.notna(record.get("alias_kind")):
            # Validate the new namespace BEFORE legacy date/string coercion can
            # turn a malformed stored value into the tuple its seal describes.
            raw_alias = {k: None if pd.isna(v) else v for k, v in record.items()}
            VendorAliasTable.from_records([raw_alias])
        row: dict = {}
        for column in columns:
            if column in missing:
                row[column] = None
                continue
            value = record[column]
            kind = dtypes.get(column)
            if kind == "date":
                row[column] = _normalize_bound(value)
            elif kind == "datetime":
                row[column] = _normalize_datetime(value)
            else:
                # A nullable STRING column (e.g. issuer_id/issuer_cik) round-trips a
                # missing cell as a bare `value is None` check would miss: measured on
                # this stack (pandas 3.0.3), pd.read_parquet(...).to_dict("records")
                # hands back a genuine `float('nan')` for a null cell in a column that
                # also carries real strings, not `None` and not `pd.NA`. `is None`
                # alone let that NaN fall through to `str(value)` == the LITERAL
                # STRING "nan", silently corrupting every null issuer_id/issuer_cik on
                # the very next read. `pd.isna` catches None/NaN/NaT uniformly.
                row[column] = None if (value is None or pd.isna(value)) else str(value)
        rows.append(row)
    return rows


def _iso_now() -> str:
    """UTC, second precision, NAIVE.

    CI runs UTC and a local-time stamp is a different fact, so the instant is UTC.  The
    offset is dropped because the registry declares ``datetime64[ns]`` with
    ``timezone: UTC`` — carrying "+00:00" in the in-memory string and losing it in the
    parquet would make a re-read differ from the row that wrote it, which is exactly the
    difference that would make an idempotent re-run look like a change.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0).isoformat()


def _current_symbol_of_row(row: dict) -> str:
    """A committed master row's CURRENT symbol — :func:`_current_symbol` walked from
    its OWN stored ``inception_code`` (V4-D2B1-R1 §5.1 "lost" predicate)."""
    return _current_symbol(str(row.get("inception_code") or "").upper())


def _compute_lost(existing: list[dict], resolutions: list[Resolution],
                  delisted: dict[str, dict], *,
                  registry_joined_ids: frozenset[str] = frozenset(),
                  ) -> tuple[list[dict], list[dict]]:
    """The pending-transition fence predicate (V4-D2B1-R1 §5.1, AMENDMENT ruling 3 /
    M1): ``(fence_lost, exception_lost)`` — committed master rows that are ACTIVE
    (``security_state`` null), whose CURRENT symbol is NOT exit-ledgered, and whose
    ``listing_key`` is re-derived by NO resolution in THIS build — a row this run's
    evidence went quiet on, distinct from a genuine exit (which the ledger already
    accounts for) and from a correction (already excluded by the state check).  A
    snapshot flip that silently drops a name's evidence (the VMRK-before-the-
    RenameEvent race, H1) is exactly what this catches; §5.4's ``listing_continuity``
    census is built from BOTH lists, disclosed.

    ``fence_lost`` gates minting (:func:`mint_master_rows`'s independence check) and
    EXCLUDES rows whose inception code is a REGISTERED identity exception
    (:data:`DEFERRED_IDENTITY_KEYS` / :data:`DISCLOSED_IDENTITY_EXCEPTIONS`, e.g.
    GOLD) — those identities are already quarantined fail-closed at their own layer,
    and their permanently-null CIKs would otherwise jam ALL future minting under the
    ruling-2 fail-closed independence check (a lost row with no CIK can never be
    proven independent of anything).

    ``exception_lost`` carries exactly those excluded rows — NEVER silently dropped:
    the receipt's ``listing_continuity`` discloses them as typed, explained entries
    (AMENDMENT ruling 3) rather than folding them into the plain "unexplained loss"
    list a future nightly's ``::warning`` fires on.

    AMENDMENT ruling 3 REMOVES the prior ``rename_new_symbols`` exclusion (a bare
    inception-code match on :data:`RENAME_EVENTS` ``.new``, on ANY venue): a
    security-axis-superseded row is now excluded ENTIRELY via the ``security_state``
    check above, once :func:`apply_security_supersession` has tombstoned it (which,
    in steady state, is true on every run AFTER the one that performed the
    correction) — no separate bare-code shortcut is needed, and the shortcut itself
    was capable of masking a genuine cross-venue collision (AMENDMENT ruling 4).
    """
    rederived = {
        res.listing_key.render() for res in resolutions if res.listing_key is not None
    }
    exceptions = _exception_by_inception_code()
    fence_lost: list[dict] = []
    exception_lost: list[dict] = []
    for row in existing:
        if row.get("security_state"):
            continue
        if _current_symbol_of_row(row) in delisted:
            continue
        if str(row["listing_key"]) in rederived:
            continue
        if str(row["security_id"]) in registry_joined_ids:
            # A SECURITY_SUPERSESSIONS-ratified cross-venue join re-derived this
            # row's SECURITY under the renamed key this run (its own listing key —
            # minted at the inception venue — is structurally unreachable once the
            # venue moves): the row is accounted for, not lost, exactly like a
            # same-venue rename's re-derivation heals its row.
            continue
        code = str(row.get("inception_code") or "").upper()
        if code in exceptions:
            exception_lost.append(row)
            continue
        fence_lost.append(row)
    return fence_lost, exception_lost


# ── V4-D2B2-US — GMI-U.S. admission typed refusals (§3/§4) ─────────────────────
def _gmi_us_unresolved_refusal(
    res: Resolution, cik_map: dict[str, tuple[str, str]],
) -> dict:
    """§4 — classify an UNRESOLVED (``listing_key is None``) GMI-US admission target
    into exactly one typed refusal class.  Every admission target :func:`build`
    fails to resolve lands here; the accounting invariant (§6) is total by
    construction — see :func:`build`'s ``us_gmi_missing`` fail-closed check.

    Never called for a candidate ``resolve_universe`` DID resolve to a venue — that
    path's structural/CIK gate is :func:`_gmi_us_eligibility_refusal`, consulted only
    at the actual mint decision inside :func:`mint_master_rows`.
    """
    if res.venue_source is not None:
        # A venue WAS found — directory match or exit-ledger row (``venue_source`` is
        # set whenever either matched; ``exchange_symbol`` is NOT a reliable signal
        # here, because ``resolve_universe``'s own unresolved-Resolution construction
        # hardcodes it None on the unmapped-MIC path — verified against the real
        # historical pre-BATS-support CBOE/Z case). AMENDMENT R15 — the two DISTINCT venue-shaped
        # refusals sharing this branch are discriminated STRUCTURALLY via
        # ``res.venue_mapped`` (set explicitly at every construction site in
        # :func:`resolve_universe`), never by substring-matching the human-readable
        # ``reason`` text: ``venue_mapped=False`` means the mic itself was never
        # found/mapped (the closed EXCHANGE_MIC list stays closed, §4) —
        # `unsupported_venue`; ``venue_mapped=True`` means the mic WAS found+mapped
        # and only the CODE failed ``ListingKey`` construction (a malformed
        # inception code) — the venue WAS supported, the CODE could not be
        # rendered into the closed listing-key grammar, typed `unrenderable_code`.
        if not res.venue_mapped:
            return {
                "code": "unsupported_venue",
                "reason": res.reason or (
                    f"venue found ({res.venue_source}) but has no MIC in the "
                    "closed EXCHANGE_MIC list (D2B2-US §4)"
                ),
            }
        return {
            "code": "unrenderable_code",
            "reason": res.reason or (
                f"ListingKey construction failed for {res.key!r} (D2B2-US §4/R12)"
            ),
        }
    evidence_key = _evidence_join_key(_inception_code(res.key, None))
    if evidence_key in cik_map:
        return {
            "code": "not_listed_cik_present",
            "reason": res.reason or (
                "absent from the current symbol-directory snapshot and the exit "
                f"ledger, but {evidence_key!r} has a current SEC CIK-map row "
                "(D2B2-US §4)"
            ),
        }
    return {
        "code": "not_listed_no_cik",
        "reason": res.reason or (
            "absent from the current symbol-directory snapshot and the exit "
            f"ledger, and no CIK-map row for {evidence_key!r} (D2B2-US §4)"
        ),
    }


def _gmi_us_eligibility_refusal(
    res: Resolution, directory_flags: dict[str, dict],
    cik_map: dict[str, tuple[str, str]], ambiguous_tickers: frozenset[str],
) -> dict | None:
    """§3 (structural common-equity flags) + §4 (registrant CIK mandatory for
    minting) — consulted ONLY inside :func:`mint_master_rows`, and ONLY at a genuine
    NEW-mint decision (``stored is None``) for a candidate already known to be a GMI
    admission target: a candidate with an existing committed master row is never
    re-examined here (mint-once) — this is the fail-closed gate the CURATED universe
    never needed and does not get this wave (§3's closing line).

    Returns a typed refusal dict (``code``, ``reason``) or ``None`` when eligible.
    Name-substring/keyword screening is FORBIDDEN as a refusal basis (§3 RULING) —
    every check here reads a STRUCTURAL directory flag or a registrant evidence
    rail, never a name; the six LP common-unit issuers (ARLP/BEP/CQP/ET/UAN/XIFR)
    carry all-false structural flags and pass through unchanged.
    """
    if res.exchange_symbol is not None:
        # AMENDMENT R5 — a DIRECTORY-resolved candidate is ALWAYS flag-checked: a
        # missing flags entry is a hard fail-closed error, never a silent skip.
        # `directory` and `directory_flags` are built from the SAME snapshot row in
        # the SAME `load_directory()` call, so a directory-resolved symbol absent
        # from `directory_flags` means the two dicts have desynced — a bug worth
        # crashing the build on, not quietly minting through blind.
        if res.exchange_symbol not in directory_flags:
            raise IdentityError(
                f"D2B2-US §3/R5: {res.exchange_symbol!r} resolved via the symbol "
                "directory but carries no structural-flags entry in "
                "directory_flags — refusing to mint blind rather than silently "
                "skip the eligibility check (directory/directory_flags desync)"
            )
        flags = directory_flags[res.exchange_symbol]
        if flags.get("etf"):
            return {
                "code": "not_common_equity_etf",
                "reason": f"{res.exchange_symbol!r} directory flag etf=True (D2B2-US §3)",
            }
        if flags.get("test_issue"):
            return {
                "code": "not_common_equity_test_issue",
                "reason": (
                    f"{res.exchange_symbol!r} directory flag test_issue=True "
                    "(D2B2-US §3)"
                ),
            }
        if flags.get("is_preferred"):
            return {
                "code": "not_common_equity_preferred",
                "reason": (
                    f"{res.exchange_symbol!r} directory flag is_preferred=True "
                    "(D2B2-US §3)"
                ),
            }
    # else: AMENDMENT R5 — a candidate resolved via the EXIT LEDGER
    # (`exchange_symbol` is None with a resolved `listing_key`) is eligibility-
    # EXEMPT BY LAW: the hand-curated ledger (`config/delisted_symbols.yml`,
    # authored from SEC filings) IS the human-verified security-type evidence —
    # there is no directory row to check, and none is required. Disclosed in the
    # receipt as `structural_check_exempt_exit_ledger` (see :func:`build`).

    evidence_key = _evidence_join_key(res.inception_code or res.key)
    if evidence_key in ambiguous_tickers:
        return {
            "code": "ambiguous_registrant",
            "reason": (
                f"{evidence_key!r} has >=2 distinct CIKs in the current cik_map "
                "snapshot (D2B2-US §4)"
            ),
        }
    if evidence_key not in cik_map:
        return {
            "code": "no_registrant_cik",
            "reason": (
                f"{evidence_key!r} absent from the current SEC CIK-map snapshot — "
                "registrant CIK mandatory for minting (D2B2-US §4)"
            ),
        }
    return None


def _collapse_duplicate_claims(
    resolutions: list[Resolution], legacy_keys: frozenset[str],
) -> tuple[list[Resolution], list[dict]]:
    """AMENDMENT R3 — when >=2 resolutions render the SAME listing key, exactly ONE
    claimant survives into the mint/alias pipeline; every other is dropped from
    ``resolutions`` entirely and returned as a typed, disclosed exclusion (R2's
    third accounting bucket).  Generalized beyond keys that were already ACTIVE
    pre-run (the D2B2-US v1 shape, which only caught a stale duplicate graph node
    under an old ticker spelling next to the current one — ``co:us:FISV`` beside
    ``co:us:FI``): a reviewer counterexample showed two codes sharing a root can
    ALSO collide on a brand-NEW key (a from-scratch NEWA/NEWAOLD pair), which the
    v1 guard never saw because it only inspected pre-run-active keys.  Left
    uncollapsed, ``build_alias_rows`` would independently contribute an
    open-bounded historical alias row for EACH claimant, which
    ``VendorAliasTable``'s own uniqueness law correctly refuses at construction
    (AMENDMENT ruling 6, D2B1-R1) — this function makes that state structurally
    unreachable rather than catching it after the fact.

    AMENDMENT R14 (fix pass 2, finding 13) — this mechanism must NEVER drop a
    LEGACY resolution: when >=2 LEGACY-universe claimants render one key (the
    D2B1-R1 dated-alias EQR/VMRK shape is exactly this — BOTH the pre-rename and
    post-rename symbol stay live universe keys ON PURPOSE), this function does
    NOT collapse them at all — every claimant flows through unchanged, exactly
    as it did pre-D2B2-US, and ``mint_master_rows``'s OWN existing collision
    handling (the ``minted_by``/``prior`` current-symbol-agreement check, H2)
    is what dedups them.  Collapsing here would itself become the "silently
    dropping a legacy resolution" violation R1's absolute law forbids.

    Collapse applies ONLY when at least one claimant is GMI-only.  Winner
    selection, in priority order:
      1. a LEGACY-universe claimant ALWAYS wins over a GMI-only one when
         exactly one legacy claimant is present — R1's "legacy mint law is
         untouched, regardless of master state" is an absolute law this NEW
         mechanism must not itself violate by dropping the legacy claimant.
      2. among GMI-only claimants only (no legacy claimant present), the one
         whose OWN key equals the resolved row's CURRENT symbol
         (:func:`_current_symbol` of the shared inception code) — "what do we
         call this today" is the natural winner.
      3. otherwise the lexicographically smallest GMI-only key, deterministic.

    Returns ``(kept_resolutions, disclosures)``.  Every disclosure names the
    dropped symbol, its rendered listing key, and the winning symbol — never a
    silent drop.  A dropped claimant is ALWAYS GMI-only; a legacy claimant is
    never named in ``disclosures``.
    """
    by_rendered: dict[str, list[Resolution]] = {}
    for res in resolutions:
        if res.listing_key is None:
            continue
        by_rendered.setdefault(res.listing_key.render(), []).append(res)

    dropped: set[str] = set()
    disclosures: list[dict] = []
    for rendered in sorted(by_rendered):
        claimants = by_rendered[rendered]
        if len(claimants) <= 1:
            continue
        legacy_claimants = sorted(
            (c for c in claimants if c.key in legacy_keys), key=lambda c: c.key
        )
        gmi_only_claimants = sorted(
            (c for c in claimants if c.key not in legacy_keys), key=lambda c: c.key
        )
        if len(legacy_claimants) >= 2:
            # R14 — >=2 legacy claimants: NOT this mechanism's problem. Leave
            # every claimant untouched (mint_master_rows' own existing
            # collision handling owns this shape, exactly as pre-D2B2-US).
            continue
        if not gmi_only_claimants:
            continue  # a single legacy claimant alone — nothing to collapse
        if legacy_claimants:
            winner = legacy_claimants[0]
            losers = gmi_only_claimants
        else:
            current_symbol = _current_symbol(claimants[0].inception_code)
            matching = [c for c in gmi_only_claimants if c.key == current_symbol]
            winner = matching[0] if matching else gmi_only_claimants[0]
            losers = [c for c in gmi_only_claimants if c.key != winner.key]
        for c in losers:
            dropped.add(c.key)
            disclosures.append({
                "symbol": c.key,
                "listing_key": rendered,
                "winning_symbol": winner.key,
                "reason": (
                    f"{c.key!r} renders the same listing key {rendered!r} as "
                    f"{winner.key!r} — a duplicate graph-topology reference to one "
                    "security, collapsed to the winning claimant; never a second "
                    "mint or a second alias-row set (D2B2-US §2, AMENDMENT R3/R14)"
                ),
            })
    kept = [r for r in resolutions if r.key not in dropped]
    return kept, disclosures


def mint_master_rows(
    resolutions: list[Resolution], existing: list[dict], now: str,
    cik_map: dict[str, tuple[str, str]] | None = None,
    delisted: dict[str, dict] | None = None,
    snapshot_date: str | None = None,
    gmi_admission_targets: frozenset[str] = frozenset(),
    directory_flags: dict[str, dict] | None = None,
    ambiguous_tickers: frozenset[str] = frozenset(),
    direct_registrant_inputs: tuple[dict, ...] | list[dict] = (),
) -> tuple[list[dict], dict[str, str], list[str], list[dict], list[dict], list[dict],
           list[dict], list[dict]]:
    """``(master rows, {membership key: security_id}, notes, resurrection_refusals,
    pending_transition_refusals, lost_rows, exception_lost_rows,
    gmi_eligibility_refusals)`` — existing ids never move.  ``lost_rows``/
    ``exception_lost_rows`` are :func:`_compute_lost`'s ``(fence_lost,
    exception_lost)`` pair (AMENDMENT ruling 3 / M1) — the fence gates on
    ``lost_rows`` only; ``exception_lost_rows`` is disclosed by the caller as typed
    ``listing_continuity`` entries, never silently dropped.

    V4-D2B2-US §3/§4 — ``gmi_admission_targets``/``directory_flags`` gate a genuine
    NEW mint (below) for a GMI-seeded candidate through
    :func:`_gmi_us_eligibility_refusal` (structural common-equity flags + registrant-
    CIK-mandatory-for-minting).  Both default to empty, so a caller that never passes
    them (every pre-D2B2-US call site) sees byte-identical behavior — this gate is
    consulted ONLY for a key present in ``gmi_admission_targets``, never for a
    legacy-universe candidate (§3's "legacy universe seed behavior is unchanged").

    The join back into a committed master is by ``listing_key``: the master's grain is
    the security, and it deliberately carries no membership-key column (that belongs to
    the alias table).  A stored row therefore wins on EVERY column, including a
    ``security_id`` that no longer matches what the derivation would produce today —
    that is precisely "mint once and store", and re-deriving it would be a re-mint.

    A correction that changes the INCEPTION CODE cannot be detected here (it changes the
    listing key, so it reads as a new security).  Per §D2 that correction is expressed
    by APPENDING an alias, never by rewriting a master row — and this builder never
    deletes a row it did not re-derive, so nothing is silently dropped either.

    ``issuer_id`` is deliberately NOT minted here (V4-D2B1 §2/§3): a brand-new row
    starts with ``issuer_id=None`` and no issuer axis — the abolished per-listing
    mint fallback.  :func:`apply_issuer_correction`, run once over the FULL returned
    row set, is the only place an issuer_id is ever assigned or repointed.  Every row
    read from ``existing`` is tagged ``_existed_before`` (an in-memory marker only —
    never a declared column, never written to parquet) so the era stage can tell a
    genuine issuer_id VALUE CHANGE (migration-worthy) from a brand-new mint's first
    assignment (not a migration: there was no prior stored value to migrate from).

    V4-D2B1-R1 §3.4 + §5 — TWO new refusal classes, both non-fatal and disclosed,
    never a silent mint:

    * **resurrection refusal (H8).**  A resolution whose rendered listing key hits an
      EXISTING row that is ``security_state``-superseded (a tombstone) never resolves
      to that superseded id — reuse of a superseded listing key needs a future
      ratified identity-break record (GOLD precedent), not an automatic rejoin.
    * **pending-transition fence (§5.2).**  A would-be NEW mint (a listing-key MISS)
      is refused when the committed master has unaccounted-for active rows this run
      (``lost``, §5.1) AND the candidate lacks independent registrant evidence (a
      current CIK map entry for the candidate whose CIK differs from every lost row's
      ``issuer_cik``).  A rename covered by :data:`RENAME_EVENTS` never reaches this
      branch at all — it already resolved to an existing row above.  An empty ``lost``
      set, or independent CIK evidence, lets the mint proceed (H7: IPOs are not
      collateral damage).
    """
    # Explicit new captured observations supplement the independence test only.
    # They never mutate the collector-owned CIK map or feed issuer grouping.
    direct_ciks = {}
    if type(direct_registrant_inputs) not in (tuple, list) or len(direct_registrant_inputs) > 3:
        raise IdentityError("direct registrant intake exceeds the bounded probe set")
    for source in direct_registrant_inputs:
        if not _direct_registrant_source_shape(source):
            raise IdentityError("invalid direct registrant input shape")
        # Existing writer now is UTC with the offset omitted by _iso_now().
        clock = datetime.fromisoformat(now.replace("Z", "+00:00"))
        if clock.tzinfo is None:
            clock = clock.replace(tzinfo=timezone.utc)
        prepared = prepare_direct_registrant(**source, decision_at=clock.isoformat())
        observed = prepared["registrant"]
        key = observed["symbol"]
        matching = [res for res in resolutions if res.key == key]
        if len(matching) != 1 or matching[0] != prepared["resolution"] or key in direct_ciks:
            raise IdentityError("direct registrant observation does not bind one exact fresh resolution")
        ordinary = (cik_map or {}).get(key)
        if key in ambiguous_tickers or (ordinary is not None and ordinary[0] != observed["cik"]):
            raise IdentityError("direct registrant conflicts with ordinary CIK evidence")
        direct_ciks[key] = (observed["cik"], observed["title"])
    by_listing_key = {str(row["listing_key"]): dict(row) for row in existing}
    out: dict[str, dict] = {}
    for k, v in by_listing_key.items():
        row = dict(v)
        row["_existed_before"] = True
        out[k] = row
    ids: dict[str, str] = {}
    notes: list[str] = []
    resurrection_refusals: list[dict] = []
    pending_transition_refusals: list[dict] = []
    gmi_eligibility_refusals: list[dict] = []
    directory_flags = directory_flags or {}

    # Cross-venue rename join (2026-10-11, the PSKY->SKYD Nasdaq->NYSE transfer): a
    # would-be NEW mint whose EXACT rendered listing key a
    # :data:`SECURITY_SUPERSESSIONS` entry names, with that entry's canonical row
    # ACTIVE in this build, is a CURATED-RATIFIED join onto that existing canonical
    # row, not a mint. A rename that moves the venue re-derives today's MIC plus the
    # chain's inception code (US-XNYS-PSKY) while the committed row carries the
    # inception venue (US-XNAS-PSKY), so the stored listing-key join a same-venue
    # rename gets for free (VMRK -> US-XNYS-EQR) is a MISS here — without this
    # bridge the candidate falls to the pending-transition fence below, which
    # refuses it exactly as designed (same registrant, never independent evidence),
    # and the renamed key never reaches ``ids`` at all. The registry entry is the
    # operator ratification (exact listing key + evidence law, the same standard
    # :func:`apply_security_supersession` holds itself to); the join MINTS NOTHING —
    # ``ids`` gains the canonical id, the fence is consulted only for genuine mints,
    # and a second stable id for the same company can never appear.
    active_by_security_id = {
        str(row["security_id"]): row for row in existing if not row.get("security_state")
    }
    supersession_joins: dict[str, str] = {}
    _rename_covered_keys = {
        sym for event in RENAME_EVENTS for sym in (event.old, event.new)
    } | _venue_transfer_covered_keys()  # same-symbol transfers: exact-pair checked
    for entry in SECURITY_SUPERSESSIONS:
        if entry.listing_key in by_listing_key:
            continue  # a committed row already owns this key: the stored join below
            # (or the H8 resurrection refusal, when that row is a tombstone) governs
        canonical = active_by_security_id.get(entry.canonical_id)
        if canonical is None:
            continue
        # The join serves a RENAME-COVERED key only: the dated alias family the join
        # exists to feed is derived from the RenameEvent (date + evidence law), so a
        # key no event covers never joins — it keeps falling to the fence below
        # exactly as before this bridge existed (the H1/H7 race replays pin that).
        # A VENUE_TRANSFERS symbol is covered too: a same-symbol transfer has no
        # dated alias family to feed (the symbol never changes), and its exact
        # supersession pairing is enforced by _venue_transfer_covered_keys.
        covered = any(
            res.listing_key is not None
            and res.listing_key.render() == entry.listing_key
            and res.key in _rename_covered_keys
            for res in resolutions
        )
        if covered:
            supersession_joins[entry.listing_key] = entry.canonical_id
    _rederived_rendered = {
        res.listing_key.render() for res in resolutions if res.listing_key is not None
    }
    registry_joined_ids = frozenset(
        cid for lk, cid in supersession_joins.items() if lk in _rederived_rendered
    )

    lost_rows, exception_lost_rows = _compute_lost(
        existing, resolutions, delisted or {}, registry_joined_ids=registry_joined_ids
    )
    # AMENDMENT ruling 2 (M2, null-CIK fail-open): a CIK-less lost row makes
    # independence UNPROVABLE, not vacuously true. The prior code dropped null CIKs
    # from `lost_ciks` entirely (`if r.get("issuer_cik")`), which meant a lost row
    # with no evidenced CIK could never disqualify ANY candidate — exactly the
    # reviewer's reproduced defect (a lost row with a null issuer_cik let a fresh
    # candidate mint with zero refusals). `lost_ciks` still names the non-null CIKs
    # (for the "candidate shares a lost row's own CIK" comparison); `_lost_has_null_cik`
    # additionally fails EVERY candidate closed when ANY lost row's CIK is unproven.
    lost_ciks = {r.get("issuer_cik") for r in lost_rows if r.get("issuer_cik")}
    _lost_has_null_cik = any(not r.get("issuer_cik") for r in lost_rows)
    cik_map = cik_map or {}

    minted_by: dict[str, tuple[str, str]] = {}  # rendered -> (first res.key, current_symbol)
    for res in resolutions:
        if res.listing_key is None:
            continue
        rendered = res.listing_key.render()
        stored = by_listing_key.get(rendered)
        if stored is not None:
            if stored.get("security_state"):
                # H8 — never a silent resurrection of a superseded listing key.
                resurrection_refusals.append({
                    "key": res.key,
                    "listing_key": rendered,
                    "security_id": stored["security_id"],
                    "security_state": stored["security_state"],
                    "superseded_by": stored.get("superseded_by"),
                    "reason": (
                        "resolution hit a superseded listing key — refusing to "
                        "resurrect; reuse requires a future ratified identity-break "
                        "record (GOLD precedent)"
                    ),
                })
                print(
                    f"::warning title=security-master-resurrection-refusal::"
                    f"{res.key!r} resolved to superseded listing key {rendered!r} "
                    f"({stored['security_id']}, superseded_by="
                    f"{stored.get('superseded_by')}) — refusing, no resurrection",
                    flush=True,
                )
                continue
            ids[res.key] = str(stored["security_id"])
        else:
            ratified_join = supersession_joins.get(rendered)
            if ratified_join is not None:
                # The cross-venue bridge above: this resolution already "resolved to
                # an existing row" — the canonical one — so no mint, no fence
                # consult, and no second stable id.
                ids[res.key] = ratified_join
                continue
            if lost_rows:
                evidence_key = _evidence_join_key(res.inception_code or res.key)
                candidate_evidence = cik_map.get(evidence_key) or direct_ciks.get(res.key)
                # AMENDMENT ruling 2 (M2): independent iff the candidate HAS a CIK,
                # EVERY fence-scoped lost row has a NON-NULL CIK, AND the candidate's
                # CIK differs from all of them. A null anywhere makes independence
                # unprovable -> refuse (fail-closed; the incident's own row class was
                # null-CIK).
                independent = (
                    candidate_evidence is not None
                    and not _lost_has_null_cik
                    and candidate_evidence[0] not in lost_ciks
                )
                if not independent:
                    refusal = {
                        "symbol": res.key,
                        "listing_key": rendered,
                        "lost_rows": sorted(r["security_id"] for r in lost_rows),
                        "snapshot_date": snapshot_date,
                        "reason": (
                            f"pending-transition fence: {len(lost_rows)} committed "
                            "row(s) unaccounted for this build and no independent "
                            "registrant evidence for the candidate symbol (§5.2)"
                        ),
                    }
                    pending_transition_refusals.append(refusal)
                    print(
                        f"::warning title=security-master-pending-transition::"
                        f"refusing to mint {res.key!r} ({rendered}) while "
                        f"{len(lost_rows)} committed row(s) are unaccounted for this "
                        "build and no independent registrant evidence backs the "
                        "candidate — pending-transition fence (§5.2)",
                        flush=True,
                    )
                    continue
            # V4-D2B2-US §3/§4 — a GMI-seeded admission target gets ONE more gate
            # before a genuine new mint: structural common-equity flags + registrant-
            # CIK-mandatory-for-minting. Never consulted for a legacy-universe key
            # (empty `gmi_admission_targets` on every pre-D2B2-US call site).
            if res.key in gmi_admission_targets:
                gmi_refusal = _gmi_us_eligibility_refusal(
                    res, directory_flags, cik_map, ambiguous_tickers,
                )
                if gmi_refusal is not None:
                    gmi_eligibility_refusals.append({
                        "symbol": res.key, "listing_key": rendered, **gmi_refusal,
                    })
                    print(
                        f"::warning title=security-master-gmi-us-eligibility-refusal::"
                        f"refusing to mint {res.key!r} ({rendered}) — "
                        f"{gmi_refusal['reason']} [{gmi_refusal['code']}] (D2B2-US)",
                        flush=True,
                    )
                    continue
            sec = security_id(res.listing_key)
            current_symbol = _current_symbol(res.key)
            prior = minted_by.get(rendered)
            if prior is not None:
                # AMENDMENT ruling 5 (M4): `rendered` is structurally
                # `<country>-<mic>-<inception_code>`, so two resolutions can only
                # ever REACH this branch by already sharing the same inception_code —
                # comparing `res.inception_code` here (the prior code) was therefore
                # ALWAYS true and the collision `notes.append` below it was dead
                # (reviewer: 0 resolutions where rendered != country-mic-inception).
                # The lawful discriminator is each seed's OWN CURRENT symbol
                # (:func:`_current_symbol` of the RAW seed key, not the shared
                # inception_code): two resolutions dedup lawfully (the EQR/VMRK
                # shape, H2) iff their seeds' current symbols AGREE; a genuine ticker
                # REUSE collision (spec §5) would differ here even though the
                # rendered listing key and inception_code are forced equal.
                if prior[1] == current_symbol:
                    ids[res.key] = sec
                    continue
                notes.append(
                    f"collision: {prior[0]!r} and {res.key!r} both mint "
                    f"{sec} — spec §5 resolves a genuine ticker REUSE with an explicit "
                    "'.2' disambiguator, which is an operator ratification, not a guess"
                )
                ids[res.key] = sec
                continue
            minted_by[rendered] = (res.key, current_symbol)
            out[rendered] = {
                "security_id": sec,
                "issuer_id": None,
                "issuer_state": None,
                "issuer_cik": None,
                "issuer_evidence_snapshot": None,
                "listing_key": rendered,
                "country": res.listing_key.country,
                "mic": res.listing_key.mic,
                "inception_code": res.inception_code,
                # midnight UTC: the registry declares datetime64[ns] and the evidence is
                # day-grained, so the time-of-day is a padding artefact, never a claim.
                "effective_at": (
                    None if res.effective_at is None
                    else f"{res.effective_at.isoformat()}T00:00:00"
                ),
                "ingested_at": now,
                "security_state": None,
                "superseded_by": None,
            }
            ids[res.key] = sec

    rows = [out[k] for k in sorted(out)]
    return (rows, ids, notes, resurrection_refusals, pending_transition_refusals,
            lost_rows, exception_lost_rows, gmi_eligibility_refusals)


def apply_security_supersession(
    rows: list[dict], ids: dict[str, str]
) -> tuple[list[dict], list[dict]]:
    """V4-D2B1-R1 §3, AMENDMENT ruling 4 (M3) — correct a security wrongly minted as
    an independent row: the curated :data:`SECURITY_SUPERSESSIONS` registry now
    proves it is the same security as an existing, different, canonical row.

    Returns ``(rows, freshly_superseded)`` — ``freshly_superseded`` names ONLY the
    rows THIS call transitioned from active to superseded (never a row that already
    carried a non-null ``security_state`` on entry), which is what makes
    :func:`build_security_migration_rows` emit exactly one migration row per
    correction rather than one every run forever.

    CORRECTION, NEVER DELETION (§3.2): the duplicate row is tombstoned in place —
    ``security_state=SUPERSEDED_DUPLICATE_MINT``, ``superseded_by=<canonical id>`` —
    and every OTHER field stays byte-frozen exactly as committed (H9).  MINT-ONCE for
    this axis too: a row already carrying a non-null ``security_state`` is left
    untouched on a later run (idempotent, H6) — this only ever CLAIMS an active row,
    never re-examines one already corrected.

    AMENDMENT ruling 4: a row is recognised as the duplicate mint for a
    :data:`SecuritySupersession` entry ONLY when its OWN ``listing_key`` matches the
    entry's ``listing_key`` EXACTLY (same country, same MIC, same code) — never a
    bare inception-code match on ANY venue.  The prior code matched any row whose
    inception code equalled a :data:`RenameEvent` ``.new`` regardless of venue, which
    let a hostile cross-MIC row (a genuinely independent listing that happens to
    share the new symbol's bare code on a DIFFERENT exchange) get auto-tombstoned
    onto the wrong canonical row.  ``ids`` is unused here (the registry names its own
    ``canonical_id`` literally, per curation, never derived from this run's mint
    output) — kept as a parameter for call-site stability and because a future
    registry entry may want it; the canonical row must still actually exist in
    ``rows`` for a correction to apply.
    """
    del ids  # AMENDMENT ruling 4: canonical id comes from the curated registry, not
    #  from this run's mint output — see docstring.
    freshly_superseded: list[dict] = []
    for entry in SECURITY_SUPERSESSIONS:
        if not any(r["security_id"] == entry.canonical_id for r in rows):
            continue  # the canonical row must exist in THIS build's row set
        for row in rows:
            if row.get("security_state"):
                continue  # already superseded (or otherwise non-null) — mint-once
            if row["security_id"] == entry.canonical_id:
                continue
            if str(row["listing_key"]) != entry.listing_key:
                continue  # EXACT listing-key match only — never a bare-code match
            row["security_state"] = SECURITY_STATE_SUPERSEDED_DUPLICATE_MINT
            row["superseded_by"] = entry.canonical_id
            freshly_superseded.append(row)
    return rows, freshly_superseded


def detect_unregistered_rename_duplicates(rows: list[dict]) -> list[dict]:
    """V4-D2B1-R1 AMENDMENT ruling 4 (M3) — a row whose ``inception_code`` matches a
    :data:`RENAME_EVENTS` ``.new`` (the shape a duplicate mint takes, on ANY venue),
    but whose EXACT ``listing_key`` has no matching entry in
    :data:`SECURITY_SUPERSESSIONS`: a receipt DISCLOSURE, never an execution.

    This is the guard against the M3 defect resurfacing quietly: a genuine future
    duplicate-mint incident must be RATIFIED (an authored registry entry, per
    curation) before this builder ever tombstones it — a bare rename-implied
    cross-venue match is not sufficient evidence on its own, exactly like the
    reviewer's cross-MIC scenario (a row sharing a rename's ``.new`` bare code on a
    DIFFERENT venue must yield NO supersession, only this disclosure).
    """
    registered_keys = {entry.listing_key for entry in SECURITY_SUPERSESSIONS}
    rename_new_codes = {e.new for e in RENAME_EVENTS}
    out: list[dict] = []
    for row in rows:
        if row.get("security_state"):
            continue  # already corrected (or otherwise non-active) — not a duplicate
        code = str(row.get("inception_code") or "").upper()
        if code not in rename_new_codes:
            continue
        if str(row["listing_key"]) in registered_keys:
            continue  # a ratified registry entry already covers this exact key
        out.append({
            "security_id": row["security_id"],
            "listing_key": row["listing_key"],
            "inception_code": code,
            "reason": (
                "inception code matches a RenameEvent .new but no exact-listing-key "
                "SECURITY_SUPERSESSIONS entry names this listing key — disclosed, "
                "never auto-corrected (V4-D2B1-R1 AMENDMENT ruling 4 / M3)"
            ),
        })
    return out


def build_security_migration_rows(freshly_superseded: list[dict], now: str) -> list[dict]:
    """Fresh ``reference.security_migrations`` rows (V4-D2B1-R1 §3.5) — one per row
    THIS run's :func:`apply_security_supersession` newly tombstoned (never one for a
    row that was already superseded coming in — that would re-emit the same
    correction every run forever). :func:`_merge_security_migrations` is the
    append-only, idempotent merge with whatever is already committed."""
    out: list[dict] = []
    for row in freshly_superseded:
        out.append({
            "security_id": row["security_id"],
            "superseded_by": row["superseded_by"],
            "reason": ERA_SECURITY_SUPERSESSION,
            "evidence": _supersession_evidence_for(row),
            "migrated_at": now,
        })
    return out


def _supersession_evidence_for(row: dict) -> str:
    """The E1-cited evidence string for the RenameEvent that produced this
    supersession (V4-D2B1-R1 §3.5 — "this era writes exactly one row" cites the
    ratified evidence verbatim, never a hand-restamped summary)."""
    code = str(row.get("inception_code") or "").upper()
    for event in RENAME_EVENTS:
        if event.new == code:
            return event.evidence
    return "scripts/build_security_master.py RENAME_EVENTS (evidence not found by inception_code)"


# ── Issuer axis (V4-D2B1) — the one authorized correction era ─────────────────
def _exception_by_inception_code() -> dict[str, dict]:
    """``{inception code -> exception info}`` for both fail-closed families.

    Keyed the way a master row's own ``inception_code`` spells them: neither ``B``
    nor ``GOLD`` is inside any rename chain (:data:`RENAME_EVENTS` /
    :data:`UNDATED_RENAMES`), so their inception_code IS their own bare name.
    """
    out: dict[str, dict] = {}
    for key, info in DEFERRED_IDENTITY_KEYS.items():
        out[key.upper()] = {"status": "deferred_no_mint", **info}
    for key, info in DISCLOSED_IDENTITY_EXCEPTIONS.items():
        out[key.upper()] = {"status": "disclosed_existing_alias", **info}
    return out


def _pick_canonical_member(members: list[dict]) -> dict:
    """Canonical member of a CIK group — spec §2 tie-break, rules 1-4.

    Rules 1 (earliest ``list_date``) and 2 (venue in the issuer's country of
    incorporation) have NO in-repo data source: this repo carries no per-security
    listing-date or country-of-incorporation table, so per spec ("skip when
    unsourced, never guess") they can never fire here and are not attempted — only
    rules 3 (lowest MIC) and 4 (the D2B1 extension: lowest full listing key) are ever
    operative.  Rule 4 is what discriminates GOOG from GOOGL (same venue, same
    country): ``US-XNAS-GOOG`` < ``US-XNAS-GOOGL`` lexicographically.
    """
    if len(members) == 1:
        return members[0]
    lowest_mic = min(m["mic"] for m in members)
    candidates = [m for m in members if m["mic"] == lowest_mic]
    return min(candidates, key=lambda m: m["listing_key"])


def _load_issuer_group_allowlist(path: Path = ISSUER_GROUP_ALLOWLIST_PATH) -> frozenset[str]:
    """CIKs ratified to form a NEW multi-member issuer group (V4-D2B1 FIX 5 / M3).

    A shared SEC registrant CIK is NECESSARY evidence for grouping (spec §1) but not
    SUFFICIENT on its own to form a group for the FIRST time: the registrant may be a
    sponsor/trust rather than the fund for an ETP, so blind CIK-grouping risks
    collapsing unrelated products under one issuer.  :data:`ISSUER_GROUP_ALLOWLIST_PATH`
    is the operator ratification — only a CIK listed there may form a brand-new
    multi-member group in :func:`apply_issuer_correction`.  Adoption of an ALREADY
    established group (mint-once, spec §2) is unaffected: the review happened when
    that group first formed.  Missing/empty file -> no CIK is pre-ratified (fail
    closed, matching every other identity-authority default in this module).
    """
    if not path.exists():
        return frozenset()
    import yaml  # local: this module stays importable without a yaml dependency otherwise

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return frozenset(
        str(g["cik"]).strip() for g in (payload.get("groups") or []) if g.get("cik")
    )


def apply_issuer_correction(
    rows: list[dict], cik_map: dict[str, tuple[str, str]], snapshot_date: str | None,
    now: str, allowlist: frozenset[str] | None = None,
    ambiguous_tickers: frozenset[str] = frozenset(),
) -> tuple[list[dict], list[dict]]:
    """The one authorized issuer-identity correction era (spec §4), run over the FULL
    accumulated master row set (existing + freshly minted this run) EVERY build.

    IDEMPOTENT BY CONSTRUCTION — mint-once for the issuer axis, the same law as
    ``security_id`` itself, EXTENDED (V4-D2B1 FIX 1 / B1) to also RE-EXAMINE a row
    whose ``issuer_state`` is already ``NO_ISSUER_EVIDENCE``: without this, a row
    stamped unevidenced on one run could never self-heal when a LATER weekly CIK map
    finally covers its ticker — the contract's own promised self-heal (spec §11 "FI/
    FISV ... self-heals on a later map") was unreachable.  ``RESOLVED``,
    ``DEFERRED_IDENTITY_EXCEPTION`` and ``EVIDENCE_CONFLICT`` rows stay mint-once —
    never revisited (sole exception: an allowlist-refused EVIDENCE_CONFLICT whose
    issuer_id is still NULL and whose stamped CIK has since been ratified in
    config/issuer_group_allowlist.yml, and no same-CIK conflicted sibling carries a
    committed issuer_id — see the reopen below): a later run whose seeds are
    unchanged sees the SAME pending set (the unstamped, NO_ISSUER_EVIDENCE and
    AMBIGUOUS rows plus any ratified-reopen rows) and, if none of them can change
    outcome, returns byte-stable rows.  A CIK group that later grows to include an
    already-RESOLVED member ADOPTS that member's existing ``issuer_id`` rather than
    re-running the tie-break ("the id is never re-derived because membership grew",
    spec §2).

    Per-row outcome (spec §3 state semantics, FIX 1 evidence-hit split):
      * inception_code names a fail-closed identity exception (``B``/``GOLD`` today)
        -> ``DEFERRED_IDENTITY_EXCEPTION``, excluded from grouping entirely, issuer_id
        UNCHANGED (the legacy value, if any, is retained — never cleared).
      * the evidence join (:func:`_evidence_join_key`) misses the CIK map -> state
        stays/becomes ``NO_ISSUER_EVIDENCE``, issuer_id UNCHANGED (legacy value
        retained for a pre-era row; stays ``None`` for a brand-new row — never a fresh
        per-listing mint, the abolished fallback).  Byte-stable when nothing changed.
      * the join hits and the row's OWN committed issuer_id (if any) agrees with, or
        is silent on (null), the CIK group's canonical id -> ``RESOLVED``, issuer_id
        set to the group's canonical id (adopted from an existing evidenced group, or
        freshly tie-broken — gated by the allowlist below when the group is BRAND NEW
        and has more than one member).  For the vast majority of rows the group has
        exactly one member, so the canonical id IS the row's own pre-existing value —
        no visible change, only the evidentiary status becomes explicit (spec §2).
      * the join hits but DISAGREES with a row's own already-committed non-null
        issuer_id (a re-examined ``NO_ISSUER_EVIDENCE`` row whose legacy value points
        at a different group than the fresh evidence would) -> ``EVIDENCE_CONFLICT``,
        issuer_id left UNCHANGED — recorded, never executed (frozen contract §2: a
        committed assignment never rewrites; only a future authorized era executes).
      * the join would form a BRAND-NEW multi-member group (no member already carries
        a committed canonical id for this CIK) whose CIK is NOT in
        :func:`_load_issuer_group_allowlist` (V4-D2B1 FIX 5 / M3: a shared CIK is
        necessary but not sufficient evidence — an SEC registrant may be a
        sponsor/trust for an ETP) -> every would-be member ``EVIDENCE_CONFLICT``
        instead of a group, issuer_id UNCHANGED, and a bare ``::warning`` names the
        CIK and members.  Adoption of an ALREADY-established group and every
        single-member group are UNGATED — the review already happened, or there was
        never a grouping decision to make.

    Returns ``(rows, migration_rows)``.  ``rows`` is the SAME objects, mutated in
    place (every element is also referenced by the caller's ``out`` dict).
    ``migration_rows`` covers ONLY securities that EXISTED before this run
    (``_existed_before``) whose issuer_id VALUE changed — a brand-new mint's first
    assignment is not a migration, because there was no prior stored value to migrate
    from (spec §3: "one row per security whose issuer_id VALUE changed in the era").
    """
    existed_before = {r["listing_key"] for r in rows if r.get("_existed_before")}
    exceptions = _exception_by_inception_code()
    allowed_ciks = allowlist if allowlist is not None else _load_issuer_group_allowlist()

    # FIX 1 (B1) + N1: re-examine unstamped rows, rows already NO_ISSUER_EVIDENCE,
    # and rows typed AMBIGUOUS — AMBIGUOUS is a pure source-snapshot artifact with no
    # committed assignment at stake, so a clean later map must be allowed to settle it
    # (RESOLVED/DEFERRED/EVIDENCE_CONFLICT stay mint-once).  Captured BEFORE either
    # loop below mutates issuer_state, so a row's PRIOR state is still readable here.
    # V4-D2B1-R1 §3.3: a security-axis-superseded row (a tombstone) is excluded from
    # this re-examination selection entirely — it never enters `pending`, never joins
    # a CIK group, and a future CIK map carrying its old symbol can never trip it into
    # EVIDENCE_CONFLICT (H4).  Its issuer columns stay exactly as committed, frozen.
    _REOPENABLE = (None, "", "NO_ISSUER_EVIDENCE", "AMBIGUOUS")
    # ALLOWLIST RATIFICATION REOPEN (#9570): a row the FIX 5 gate refused — typed
    # EVIDENCE_CONFLICT with its stamped issuer_cik — whose CIK has SINCE been
    # ratified in config/issuer_group_allowlist.yml is re-examined, but ONLY while
    # its issuer_id is still NULL.  With no committed value there is nothing for
    # mint-once to protect, and the ratification row IS the review the gate asked
    # for.  A conflict that carries a committed issuer_id (FIX 1(b), or a refused
    # legacy row) stays terminal: reopening it would rewrite an assignment.  The
    # reopen is also ALL-OR-NOTHING per CIK: when any conflicted sibling sharing the
    # stamped CIK carries a committed issuer_id, NO null member of that CIK reopens —
    # a partial reopen would tie-break over the null members alone and mint a second
    # issuer_id for one registrant (the committed sibling is not RESOLVED, so the
    # adoption index below never sees it).  Such a CIK stays terminal for a human.
    _committed_conflict_ciks = {
        r.get("issuer_cik")
        for r in rows
        if not r.get("security_state")
        and r.get("issuer_state") == "EVIDENCE_CONFLICT"
        and r.get("issuer_id") is not None
        and r.get("issuer_cik")
    }
    pending = [
        r for r in rows
        if not r.get("security_state") and (
            r.get("issuer_state") in _REOPENABLE
            or (r.get("issuer_state") == "EVIDENCE_CONFLICT"
                and r.get("issuer_id") is None
                and r.get("issuer_cik") in allowed_ciks
                and r.get("issuer_cik") not in _committed_conflict_ciks)
        )
    ]
    if not pending:
        return rows, []
    reexamined_ids = {
        r["security_id"]
        for r in pending
        if r.get("issuer_state") in ("NO_ISSUER_EVIDENCE", "AMBIGUOUS")
    }

    # Adoption index: a CIK already carrying a RESOLVED canonical id (from an earlier
    # era run, or from a different pending group processed earlier in THIS loop —
    # groups are keyed by CIK so this only matters across runs, not within one).
    cik_to_existing_issuer: dict[str, str] = {}
    for r in rows:
        if r.get("issuer_state") == "RESOLVED" and r.get("issuer_cik"):
            cik_to_existing_issuer.setdefault(r["issuer_cik"], r["issuer_id"])

    groups: dict[str, list[dict]] = {}
    for r in pending:
        code = str(r["inception_code"]).upper()
        exc = exceptions.get(code)
        if exc is not None:
            r["issuer_state"] = "DEFERRED_IDENTITY_EXCEPTION"
            r["issuer_cik"] = None
            r["issuer_evidence_snapshot"] = None
            continue
        join_key = _evidence_join_key(code)
        if join_key in ambiguous_tickers:
            # FIX 7 (m1): the ticker maps to MORE THAN ONE distinct CIK on the
            # source snapshot — load_cik_map() already removed it from cik_map, so
            # this must be checked explicitly rather than read as a plain miss
            # (NO_ISSUER_EVIDENCE would silently misreport "no evidence" for a
            # ticker that has TOO MUCH, conflicting evidence).
            r["issuer_state"] = "AMBIGUOUS"
            r["issuer_cik"] = None
            r["issuer_evidence_snapshot"] = None
            continue
        evidence = cik_map.get(join_key)
        if evidence is None:
            r["issuer_state"] = "NO_ISSUER_EVIDENCE"
            r["issuer_cik"] = None
            r["issuer_evidence_snapshot"] = None
            continue
        cik, _title = evidence
        groups.setdefault(cik, []).append(r)

    migrations: list[dict] = []
    for cik, members in sorted(groups.items()):
        existing_issuer = cik_to_existing_issuer.get(cik)
        is_new_multi_member_group = existing_issuer is None and len(members) > 1
        if is_new_multi_member_group and cik not in allowed_ciks:
            # FIX 5 (M3, latent): refuse to form the group — record, never execute.
            member_ids = sorted(r["security_id"] for r in members)
            print(
                f"::warning title=security-master-issuer-allowlist::CIK {cik} would "
                f"form a new {len(members)}-member issuer group "
                f"({', '.join(member_ids)}) not in config/issuer_group_allowlist.yml "
                "— refusing to group; recording EVIDENCE_CONFLICT for review",
                flush=True,
            )
            for r in members:
                r["issuer_state"] = "EVIDENCE_CONFLICT"
                r["issuer_cik"] = cik
                r["issuer_evidence_snapshot"] = snapshot_date
                # issuer_id UNCHANGED — recorded, never executed (frozen contract §2).
            continue
        canonical_issuer_id = existing_issuer or issuer_id(
            parse_listing_key(_pick_canonical_member(members)["listing_key"])
        )
        for r in members:
            old_issuer = r["issuer_id"]
            if (r["security_id"] in reexamined_ids and old_issuer is not None
                    and old_issuer != canonical_issuer_id):
                # FIX 1(b): a re-examined row's own committed value disagrees with
                # where fresh evidence would group it — recorded, never executed.
                r["issuer_state"] = "EVIDENCE_CONFLICT"
                r["issuer_cik"] = cik
                r["issuer_evidence_snapshot"] = snapshot_date
                continue
            r["issuer_state"] = "RESOLVED"
            r["issuer_cik"] = cik
            r["issuer_evidence_snapshot"] = snapshot_date
            r["issuer_id"] = canonical_issuer_id
            if r["listing_key"] in existed_before and old_issuer != canonical_issuer_id:
                migrations.append({
                    "security_id": r["security_id"],
                    "listing_key": r["listing_key"],
                    "old_issuer_id": old_issuer,
                    "new_issuer_id": canonical_issuer_id,
                    "reason": ERA_ISSUER_CORRECTION,
                    "evidence_cik": cik,
                    "evidence_snapshot": snapshot_date,
                    "migrated_at": now,
                })

    return rows, sorted(migrations, key=lambda m: m["security_id"])


def _merge_issuer_migrations(existing: list[dict], fresh: list[dict]) -> list[dict]:
    """Append-only on ``(security_id, old_issuer_id, new_issuer_id, reason)`` — the
    same shape as :func:`merge_alias_rows`.  Mint-once means a security migrates at
    most once per reason in practice; the dedup is defensive, not load-bearing."""
    merged: dict[tuple, dict] = {}
    for row in existing:
        key = (str(row["security_id"]), str(row["old_issuer_id"]), str(row["new_issuer_id"]),
               str(row["reason"]))
        merged[key] = dict(row)
    for row in fresh:
        key = (row["security_id"], row["old_issuer_id"], row["new_issuer_id"], row["reason"])
        if key in merged:
            continue
        merged[key] = row
    return [merged[k] for k in sorted(merged, key=lambda k: (k[0], k[3]))]


def _merge_security_migrations(existing: list[dict], fresh: list[dict]) -> list[dict]:
    """Append-only on ``(security_id, superseded_by, reason)`` — the security-axis
    mirror of :func:`_merge_issuer_migrations`.  Mint-once means a security is
    superseded at most once per reason in practice; the dedup is defensive, not
    load-bearing (V4-D2B1-R1 §3.5)."""
    merged: dict[tuple, dict] = {}
    for row in existing:
        key = (str(row["security_id"]), str(row["superseded_by"]), str(row["reason"]))
        merged[key] = dict(row)
    for row in fresh:
        key = (row["security_id"], row["superseded_by"], row["reason"])
        if key in merged:
            continue
        merged[key] = row
    return [merged[k] for k in sorted(merged, key=lambda k: (k[0], k[2]))]


def _build_issuer_master_rows(master_rows: list[dict],
                              cik_to_title: dict[str, str]) -> list[dict]:
    """``reference.issuer_master`` — one row per distinct non-null ``issuer_id`` in the
    master (spec §3 minimal cut).  NOT a second identity system: minted only via
    ``lib.dataos.identity.issuer_id`` (inside :func:`apply_issuer_correction`),
    pointed into by ``security_master.issuer_id`` — this is a CENSUS over that column,
    never an independent allocator.

    V4-D2B1-R1 §3.3: a security-axis-superseded row never contributes to this census —
    excluded from issuer aggregation and issuer_master membership, same as it is
    excluded from re-examination in :func:`apply_issuer_correction`.
    """
    groups: dict[str, list[dict]] = {}
    for r in master_rows:
        if r.get("security_state"):
            continue
        iid = r.get("issuer_id")
        if iid:
            groups.setdefault(iid, []).append(r)

    out: list[dict] = []
    for issuer, members in groups.items():
        resolved = [m for m in members if m.get("issuer_state") == "RESOLVED"]
        if resolved:
            cik = resolved[0].get("issuer_cik")
            out.append({
                "issuer_id": issuer,
                "cik": cik,
                "legal_name": cik_to_title.get(cik) if cik else None,
                "n_securities": len(members),
                "evidence_source": "sec_company_tickers",
                "evidence_snapshot": resolved[0].get("issuer_evidence_snapshot"),
                "status": "active",
                "era": ERA_ISSUER_CORRECTION,
            })
        else:
            out.append({
                "issuer_id": issuer,
                "cik": None,
                "legal_name": None,
                "n_securities": len(members),
                "evidence_source": "legacy_mint",
                "evidence_snapshot": None,
                "status": "active",
                "era": "legacy",
            })
    return sorted(out, key=lambda r: r["issuer_id"])


class VendorAliasPruneConflict(Exception):
    """Raised by :func:`_prune_stale_aliases` (AMENDMENT ruling 6 / M5) when a fresh
    alias row overlaps a committed row that points at an ACTIVE (non-superseded)
    ``security_id`` and the overlap is not excused by the AMENDMENT §2 same-id-
    refinement carve-out (see below). Fail-closed by design: the pre-amendment code
    silently dropped ANY overlapping committed row (whether it pointed at a
    superseded id or not), which is an undisclosed last-write-wins replacement on an
    append-only dataset — exactly the M5 defect. A genuine correction to an ACTIVE
    row's alias history that does NOT qualify for the carve-out is a curation act (a
    new RENAME_EVENTS/SECURITY_SUPERSESSIONS entry, or an operator resolving the
    conflict by hand), never something this builder silently resolves.

    TWO lawful deletion classes now exist (:func:`_prune_stale_aliases` documents
    both in full): the original superseded-``security_id`` tombstone prune, and the
    AMENDMENT §2 same-id-refinement carve-out (implemented 2026-08-29) — a fresh
    DATED family pointing at the SAME still-active ``security_id`` that exactly
    tiles the full time axis, with the family row COVERING the committed row's own
    start date carrying its ``vendor_symbol`` (start-anchored, see
    :func:`_is_lawful_same_id_refinement`), is a lawful REFINEMENT of a committed
    open-bounded row rather than a conflict. Every other overlap — an undated
    replacement row, a zero/negative-width row, a gap or double-cover in the
    tiling, a fully dated committed row, a family whose start-covering leg names a
    different symbol, or a fresh row naming a DIFFERENT security_id — still raises
    exactly as before, and the raised message names the SPECIFIC failed condition
    (or the specific different-``security_id`` row).

    AMENDMENT ruling 11 (§3): a plain ``Exception``, NEVER ``SystemExit`` — the
    pre-amendment class subclassed ``SystemExit``, which is a ``BaseException``
    sibling to ``Exception`` and therefore escaped :func:`run_nightly_refresh`'s
    ``except Exception`` handler entirely (a real MAJOR regression: the nightly seam's
    "always returns 0" invariant broke, ``_restore_artifacts`` never ran, and NOT ONE
    ``::warning`` was emitted — silent process-exit-1 on exactly the future
    dated-rename path AMENDMENT §2 documents will fire). :func:`run_nightly_refresh`
    catches this class EXPLICITLY, before its generic handler (see there); the CLI
    path (:func:`main`) still stays fail-closed because nothing there catches it at
    all — an uncaught ``Exception`` propagating out of ``main()`` is still a non-zero
    exit, exactly like before this rebase.
    """


def _covering_family_row(ordered: list[AliasRow], point: date | None) -> AliasRow | None:
    """The unique row in an already tiling-validated ``ordered`` family that covers
    ``point`` — ``point=None`` means -infinity, which under a lawful gapless,
    overlap-free tiling is covered ONLY by the row open at the start
    (``valid_from is None``); a real date is covered by whichever row's
    ``[valid_from, valid_to)`` half-open interval contains it. Callers must
    validate the tiling FIRST (see :func:`_is_lawful_same_id_refinement`) — over an
    unvalidated family this can return ``None`` (a gap) or an arbitrary row among
    several genuine candidates (an overlap).
    """
    if point is None:
        for f in ordered:
            if f.valid_from is None:
                return f
        return None
    for f in ordered:
        lo_ok = f.valid_from is None or f.valid_from <= point
        hi_ok = f.valid_to is None or point < f.valid_to
        if lo_ok and hi_ok:
            return f
    return None


def _is_lawful_same_id_refinement(ex_row: AliasRow, family: list[AliasRow]) -> str | None:
    """AMENDMENT §2 same-id-refinement carve-out predicate (implemented 2026-08-29;
    start-anchored symbol rule + deterministic tiling added in the same-day fix
    packet). Returns ``None`` when ``ex_row`` IS a lawful refinement, else a short
    string naming the FIRST failed condition — checked in this fixed order,
    because the start-anchored symbol check (d) is only meaningful once the tiling
    itself (e) is known to be well-formed.

    ``family`` is every FRESH row sharing ``ex_row``'s ``(vendor, security_id)``.

    a. ``ex_row`` is OPEN-ENDED (``valid_to is None``) — a fully dated committed row
       contradicted by fresh evidence is a history rewrite, never a refinement.
    b. (same id) — enforced by the CALLER: every fresh row that overlaps ``ex_row``
       must share ``ex_row.security_id`` before this predicate even runs (a
       different-id overlap is reported by name, never folded into this reason);
       ``family`` is already scoped to ``ex_row.security_id`` by construction.
    c. DATED — no row in ``family`` may be fully open (``valid_from is None and
       valid_to is None``); a single undated replacement row is not a citable
       refinement.
    (width) — no row in ``family`` may have zero or negative width
       (``valid_from is not None and valid_to is not None and valid_from >= valid_to``);
       a degenerate row can neither tile the axis nor meaningfully "cover" a point,
       and admitting one would make the tiling check below order-dependent.
    e. Full-axis tiling — sorted DETERMINISTICALLY (``valid_from`` ascending with
       ``None`` first, THEN ``valid_to`` ascending with ``None`` last as the
       tie-break — two rows sharing one ``valid_from`` never depend on input
       order), exactly one row is open at the start, exactly one is open at the
       end, and every consecutive pair meets EXACTLY (``prev.valid_to ==
       next.valid_from``): gapless and overlap-free across the whole axis.
       (Implies ``len(family) >= 2`` given (c).)
    d. Start-anchored symbol continuity — REPLACES the original era-blind rule
       ("some row, ANYWHERE in the family, carries the committed symbol"), which
       let a family whose EARLY leg happened to share the committed row's symbol
       excuse pruning a row that, at ITS OWN start date, the family actually maps
       to a DIFFERENT live symbol (the reviewer's PROBE A: a committed
       ``(yahoo, ABC, sec, 2020-01-01, None)`` against a family whose current
       (post-2010) leg is ``DEF`` must still raise, even though an ``ABC`` leg
       exists earlier in the same family). The family row COVERING
       ``ex_row.valid_from`` (``None`` == -infinity; see
       :func:`_covering_family_row` — under the now-validated tiling exactly one
       row covers any point) must carry ``ex_row``'s own ``vendor_symbol``.
    """
    if ex_row.valid_to is not None:
        return "the committed row is fully dated (valid_to is not None), not open-ended"
    if not family:
        return "no fresh row shares this row's (vendor, security_id)"
    if any(f.valid_from is None and f.valid_to is None for f in family):
        return "the family contains an undated (fully open) row"
    if any(
        f.valid_from is not None and f.valid_to is not None and f.valid_from >= f.valid_to
        for f in family
    ):
        return "the family contains a zero-or-negative-width row"
    ordered = sorted(
        family,
        key=lambda f: (f.valid_from is not None, f.valid_from, f.valid_to is None, f.valid_to),
    )
    if sum(1 for f in ordered if f.valid_from is None) != 1:
        return "the family does not have exactly one open-start row"
    if sum(1 for f in ordered if f.valid_to is None) != 1:
        return "the family does not have exactly one open-end row"
    for prev, nxt in zip(ordered, ordered[1:]):
        if prev.valid_to != nxt.valid_from:
            return "the family does not exactly tile the time axis (a gap or overlap)"
    covering = _covering_family_row(ordered, ex_row.valid_from)
    if covering is None or covering.vendor_symbol != ex_row.vendor_symbol:
        return (
            "the family row covering the committed row's start must carry its "
            "vendor_symbol"
        )
    return None


def _prune_stale_aliases(
    existing: list[dict], fresh: list[AliasRow], superseded_ids: frozenset[str]
) -> tuple[list[dict], list[dict]]:
    """``(kept, pruned)`` — existing alias rows that a FRESH build's own evidence now
    proves wrong (V4-D2B1-R1 §3.7, AMENDMENT ruling 6 / M5), dropped from the merge
    input rather than kept as append-only garbage. "No alias row hand-deleted" (§3.7)
    means no HAND edit; a row the SAME canonical builder's own fresh derivation
    contradicts is not append-only history, it is a stale artifact of a mint this
    repair corrects.

    TWO deletion classes, narrowly scoped (AMENDMENT ruling 6 REMOVES the prior
    "ambiguity-conflicting" class 2, which silently dropped ANY committed row
    overlapping a fresh one — including rows pointing at a perfectly ACTIVE id, an
    undisclosed last-write-wins replacement on an append-only dataset):

    * **Superseded security_id** (``prune_class="superseded_tombstone"``).  Any row
      minted for a security this run tombstoned (V4-D2B1-R1 §3) is categorically
      wrong — VMRK's alias rows must converge onto EQR's family (§3.7), never keep
      pointing at the corrected id.

    * **Same-id refinement** (``prune_class="same_id_refinement"``, AMENDMENT §2
      carve-out, implemented 2026-08-29).  A fresh candidate that overlaps a
      committed row pointing at a still-ACTIVE ``security_id`` is not automatically a
      conflict: when EVERY overlapping fresh row shares the committed row's OWN
      ``security_id`` and belongs to a DATED same-id family that exactly tiles the
      full time axis (no gaps, no overlaps) with the family row COVERING the
      committed row's own start date carrying its ``vendor_symbol`` (the
      start-anchored rule — see :func:`_is_lawful_same_id_refinement` for the full
      ordered condition list), the committed open-bounded row is a stale
      pre-refinement artifact, not a genuine ambiguity: it is pruned, not raised.
      EVERY open-ended committed row that the SAME lawful family refines is pruned
      (plural) — a family can legitimately extend past more than one prior
      committed link in one run (see the chained-refinement unit test). A single
      UNDATED replacement row, a zero/negative-width row, a gapped/overlapping
      tiling, a fully DATED committed row, a family whose start-covering leg names
      a different symbol, or ANY overlapping fresh row naming a DIFFERENT
      ``security_id`` still falls through to the fail-closed raise below exactly
      as before this carve-out.

    Every deletion in EITHER class is named in ``pruned`` (tagged with its
    ``prune_class``) — the caller receipts it (``vendor_alias_prunes`` + a dedicated
    ``::warning`` per class), never a silent drop.

    A fresh row that overlaps a committed row pointing at an ACTIVE id, and is not
    excused by the carve-out above, is a fail-closed :class:`VendorAliasPruneConflict`
    naming the specific failed condition (or the specific different-``security_id``
    row, when that is what disqualified it). Two rows that are BYTE-IDENTICAL are
    not a conflict (ordinary merge dedup in :func:`merge_alias_rows` already
    handles those), and this never touches a fresh row's own side.
    """
    # Root relations are immutable additions, not ordinary symbol refinements.
    # Validate before the tombstone branch so no malformed/unknown kind disappears.
    if any(r.get("alias_kind") is not None for r in existing) or any(r.alias_kind is not None for r in fresh):
        prior = VendorAliasTable.from_records(existing)
        VendorAliasTable(fresh)
        roots = [r for r in prior.rows if r.alias_kind == "occ_root"]
        new_roots = [r for r in fresh if r.alias_kind == "occ_root"]
        for row in roots:
            if row.security_id in superseded_ids:
                raise VendorAliasPruneConflict("option-root tombstone requires explicit evidence curation")
        # Merge enforces unchanged seals; the table enforces forward uniqueness.
        root_records = [r for r in existing if r.get("alias_kind") == "occ_root"]
        VendorAliasTable.from_records(merge_alias_rows(new_roots, root_records, "unused"))
        ordinary, pruned = _prune_stale_aliases(
            [r for r in existing if r.get("alias_kind") is None],
            [r for r in fresh if r.alias_kind is None], superseded_ids)
        return ordinary + root_records, pruned

    fresh_by_vendor_symbol: dict[tuple[str, str], list[AliasRow]] = {}
    fresh_by_vendor_sec: dict[tuple[str, str], list[AliasRow]] = {}
    for row in fresh:
        fresh_by_vendor_symbol.setdefault((row.vendor, row.vendor_symbol), []).append(row)
        fresh_by_vendor_sec.setdefault((row.vendor, row.security_id), []).append(row)

    out: list[dict] = []
    pruned: list[dict] = []
    for ex in existing:
        if str(ex["security_id"]) in superseded_ids:
            pruned.append({**ex, "prune_class": "superseded_tombstone"})
            continue
        ex_row = AliasRow(
            str(ex["vendor"]), str(ex["vendor_symbol"]), str(ex["security_id"]),
            _as_bound_date(ex["valid_from"]), _as_bound_date(ex["valid_to"]),
            ex.get("known_at"), ex.get("evidence_sha256"), ex.get("binding_sha256"),
        )
        candidates = (
            fresh_by_vendor_symbol.get((ex_row.vendor, ex_row.vendor_symbol), [])
            + fresh_by_vendor_sec.get((ex_row.vendor, ex_row.security_id), [])
        )
        family = fresh_by_vendor_sec.get((ex_row.vendor, ex_row.security_id), [])
        overlaps: list[AliasRow] = []
        for fr in candidates:
            if (fr.vendor_symbol, fr.security_id, fr.valid_from, fr.valid_to) == (
                ex_row.vendor_symbol, ex_row.security_id, ex_row.valid_from, ex_row.valid_to
            ):
                continue  # identical — ordinary dedup, not a conflict
            if ex_row.overlaps(fr):
                overlaps.append(fr)

        if not overlaps:
            out.append(ex)
            continue

        if ex_row.vendor == "polygon":
            raise VendorAliasPruneConflict("prospective native alias revision is not admitted")

        # A different-security_id overlap is disqualifying on its own and is named
        # explicitly — it is never folded into the same-id predicate's reason.
        foreign = next((fr for fr in overlaps if fr.security_id != ex_row.security_id), None)
        if foreign is not None:
            raise VendorAliasPruneConflict(
                f"fresh alias row {foreign!r} overlaps a COMMITTED row pointing "
                f"at an ACTIVE security_id ({ex_row!r}) but names a DIFFERENT "
                "security_id — refusing to silently prune or replace it. A "
                "committed alias row may be pruned ONLY when it points at a "
                "superseded security_id (AMENDMENT ruling 6 / M5), or when it is "
                "a lawful AMENDMENT §2 same-id-refinement, which requires EVERY "
                "overlapping fresh row to share this row's OWN security_id — a "
                "different security_id among the overlapping rows never "
                "qualifies. Resolve this by curation (a registered "
                "RENAME_EVENTS/SECURITY_SUPERSESSIONS entry) or by hand, never "
                "by silent last-write-wins."
            )

        reason = _is_lawful_same_id_refinement(ex_row, family)
        if reason is None:
            # AMENDMENT §2 carve-out: prune the committed row, receipted — never a
            # silent last-write-wins replacement, but no longer a raise either.
            # EVERY open-ended committed row this SAME lawful family refines is
            # pruned in its own loop iteration (plural), not just the first.
            pruned.append({**ex, "prune_class": "same_id_refinement"})
            continue

        # AMENDMENT ruling 6 (M5): fail-closed — never a silent replacement.
        raise VendorAliasPruneConflict(
            f"fresh alias row {overlaps[0]!r} overlaps a COMMITTED row pointing "
            f"at an ACTIVE security_id ({ex_row!r}) — refusing to silently prune "
            "or replace it. A committed alias row may be pruned ONLY when it "
            "points at a superseded security_id (AMENDMENT ruling 6 / M5), or "
            "when it is a lawful AMENDMENT §2 same-id-refinement — this family "
            f"did not qualify: {reason}. Resolve this by curation (a registered "
            "RENAME_EVENTS/SECURITY_SUPERSESSIONS entry) or by hand, never by "
            "silent last-write-wins."
        )
    return out, pruned


def _as_bound_date(value: str | None) -> date | None:
    """A ``_read_existing``-normalized ISO date string (or None) as a ``date``."""
    return date.fromisoformat(value) if value else None


def merge_alias_rows(fresh: list[AliasRow], existing: list[dict], now: str) -> list[dict]:
    """Append-only on the declared grain; a committed row keeps its ``ingested_at``."""
    # Check raw root record bounds/types before legacy date normalization.
    VendorAliasTable.from_records([r for r in existing if r.get("alias_kind") is not None])
    merged: dict[tuple, dict] = {}
    for row in existing:
        key = (
            str(row["vendor"]),
            str(row["vendor_symbol"]),
            str(row["security_id"]),
            _normalize_bound(row["valid_from"]),
            _normalize_bound(row["valid_to"]),
            row.get("alias_kind"),
        )
        if key in merged and row.get("alias_kind") == "occ_root":
            raise IdentityError("duplicate committed option-root relation")
        merged[key] = {
            "vendor": key[0],
            "vendor_symbol": key[1],
            "security_id": key[2],
            "valid_from": key[3],
            "valid_to": key[4],
            "ingested_at": str(row["ingested_at"]),
            **{c: row.get(c) for c in OPTIONAL_ALIAS_COLUMNS},
        }
    for row in fresh:
        key = (row.vendor, row.vendor_symbol, row.security_id,
               _as_iso(row.valid_from), _as_iso(row.valid_to), row.alias_kind)
        if key in merged:
            if (row.vendor == "polygon" or row.alias_kind == "occ_root") and merged[key].get("binding_sha256") != row.binding_sha256:
                raise IdentityError("conflicting prospective native alias; revisions not admitted")
            continue
        merged[key] = {
            "vendor": key[0],
            "vendor_symbol": key[1],
            "security_id": key[2],
            "valid_from": key[3],
            "valid_to": key[4],
            "ingested_at": now,
            "known_at": row.known_at.isoformat() if isinstance(row.known_at, datetime) else row.known_at,
            "evidence_sha256": row.evidence_sha256,
            "binding_sha256": row.binding_sha256,
            "alias_kind": row.alias_kind,
        }
    rows = [merged[k] for k in sorted(merged, key=lambda k: (k[0], k[1], k[2], str(k[3]), str(k[4]), str(k[5])))]
    # New root relations never rely on the main caller to catch forward conflicts.
    VendorAliasTable.from_records([r for r in rows if r.get("alias_kind") is not None])
    return rows


def _normalize_bound(value) -> str | None:
    """A stored date bound as an ISO date string, or None.

    ``NaT``/``NaN``/``''`` all mean OPEN BOUND, and every one of them is a shape pandas
    can hand back for a parquet null depending on the column's inferred dtype — so all
    three collapse here rather than in each caller.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    if not text or text.lower() in {"nat", "nan", "none", "<na>"}:
        return None
    return text[:10]


def _normalize_datetime(value) -> str | None:
    """A stored timestamp as a naive-UTC ISO string, or None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        stamp = value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value
        return stamp.replace(microsecond=0).isoformat()
    if isinstance(value, date):
        return f"{value.isoformat()}T00:00:00"
    text = str(value).strip()
    if not text or text.lower() in {"nat", "nan", "none", "<na>"}:
        return None
    return text.replace(" ", "T")[:19]


# ── Writing ───────────────────────────────────────────────────────────────────
def _write_parquet(rows: list[dict], columns: tuple[str, ...], path: Path,
                   dtypes: dict[str, str]) -> None:
    """Write the declared columns in the declared order, with the declared dtypes."""
    import pandas as pd

    if "alias_kind" in columns:
        VendorAliasTable.from_records(rows)
    data: dict[str, object] = {}
    for column in columns:
        values = [row.get(column) for row in rows]
        kind = dtypes.get(column)
        if kind == "datetime":
            data[column] = pd.to_datetime(pd.Series(values, dtype="object"), errors="coerce")
        elif kind == "date":
            data[column] = pd.Series(
                [None if v is None else date.fromisoformat(str(v)[:10]) for v in values],
                dtype="object",
            )
        elif kind == "int":
            data[column] = pd.Series(
                [None if v is None else int(v) for v in values], dtype="Int64"
            )
        else:
            # Same NaN-is-not-None trap as _read_existing: a caller that assigns
            # `frame.loc[..., col] = None` onto a pandas "str"-dtype column can hand
            # this a `float('nan')`, not a Python `None` — `v is None` alone would
            # stringify it into the LITERAL STRING "nan" and corrupt the column.
            data[column] = pd.Series(
                [None if (v is None or pd.isna(v)) else str(v) for v in values],
                dtype="object",
            )
    frame = pd.DataFrame(data, columns=list(columns))
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)


def _issuer_state_counts(master_rows: list[dict]) -> dict[str, int]:
    """Issuer-state census over ACTIVE rows only (V4-D2B1-R1 §8: "states split by
    security_state") — a security-axis-superseded row's issuer_state stays whatever it
    was byte-frozen at (§3.2) and must not inflate an active-row census with a
    tombstone; see :func:`_security_state_counts` for the axis this excludes."""
    counts: dict[str, int] = {}
    for r in master_rows:
        if r.get("security_state"):
            continue
        state = r.get("issuer_state") or "UNMIGRATED"
        counts[state] = counts.get(state, 0) + 1
    return counts


def _security_state_counts(master_rows: list[dict]) -> dict[str, int]:
    """Security-axis census (V4-D2B1-R1 §3.1) — ``ACTIVE`` (``security_state`` null)
    alongside every closed-enum non-null value actually present."""
    counts: dict[str, int] = {}
    for r in master_rows:
        state = r.get("security_state") or "ACTIVE"
        counts[state] = counts.get(state, 0) + 1
    return counts


def _multi_security_issuer_groups(master_rows: list[dict]) -> list[dict]:
    """Every issuer_id carried by >1 security — the multi-security group census
    (spec §6): machine-visible confirmation of what the era actually grouped."""
    groups: dict[str, list[str]] = {}
    for r in master_rows:
        iid = r.get("issuer_id")
        if iid:
            groups.setdefault(iid, []).append(r["security_id"])
    return [
        {"issuer_id": iid, "security_ids": sorted(secs)}
        for iid, secs in sorted(groups.items())
        if len(secs) > 1
    ]


# Prospective reference-only intake. These four probes are neither a collection
# cohort nor a scientific population. Receipt evidence stays with the existing
# canonical writer; this function performs no network or credential operation.
REFERENCE_PROBES = {
    "MU": ("NASDAQ", XNAS, "CS", False),
    "SPY": ("P", ARCX, "ETF", True),
    "QQQ": ("NASDAQ", XNAS, "ETF", True),
    "SMH": ("NASDAQ", XNAS, "ETF", True),
}
REFERENCE_SCHEMA = "mastermind.prospective_reference.v1"
_REFERENCE_MAX_BYTES = 2 * 1024 * 1024


def _reference_digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def _reference_json(path: Path) -> tuple[dict, str]:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise IdentityError("duplicate reference JSON key")
            result[key] = value
        return result
    with path.open("rb") as source:
        raw = source.read(_REFERENCE_MAX_BYTES + 1)
    if len(raw) > _REFERENCE_MAX_BYTES:
        raise IdentityError("reference evidence exceeds byte bound")
    try:
        value = json.loads(raw, object_pairs_hook=pairs,
                           parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
    except (ValueError, UnicodeError) as exc:
        raise IdentityError("invalid reference evidence JSON") from exc
    if not isinstance(value, dict):
        raise IdentityError("reference evidence must be an object")
    return value, hashlib.sha256(raw).hexdigest()


# Scoped reentrancy bookkeeping only; fcntl/OS owns exclusion. This is not
# source authority, a durable lock registry, lease, retry queue or daemon.
_reference_writer_local = threading.local()


def _writer_path(out_dir: Path) -> str:
    return os.path.abspath(os.fspath(out_dir))


def _assert_reference_writer_target(out_dir: Path) -> None:
    """Detect directory substitution inside our currently held writer scope."""
    token = getattr(_reference_writer_local, "active", {}).get(_writer_path(out_dir))
    if token is None or token[0] != os.getpid():
        return  # Pure read-only legacy guard calls are allowed outside writers.
    _pid, fd, device, inode = token
    try:
        now = os.stat(out_dir, follow_symlinks=False)
        held = os.fstat(fd)
    except OSError as exc:
        raise IdentityError("reference writer target changed or unavailable") from exc
    if (not stat.S_ISDIR(now.st_mode) or
            (now.st_dev, now.st_ino) != (device, inode) or
            (held.st_dev, held.st_ino) != (device, inode)):
        raise IdentityError("reference writer target changed during transaction")


@contextmanager
def _reference_writer_scope(out_dir: Path):
    """One nonblocking, cooperative POSIX directory lock for all local writers.

    Manual build and the ENTIRE nightly snapshot/build/rollback hold this same
    scope. Nested calls in the same process/thread reuse its descriptor; other
    processes/threads refuse immediately. No lockfile or new data schema.
    This requires a local filesystem with working flock semantics. It does not
    coordinate Git pushes, unrelated hosts, old code, or non-cooperating actors.
    Creating an initial empty output directory is not generation publication.
    """
    try:
        import fcntl
    except ImportError as exc:
        raise IdentityError("reference writer locking unsupported on this host") from exc
    out_dir = Path(out_dir)
    key = _writer_path(out_dir)
    active = getattr(_reference_writer_local, "active", None)
    if active is None:
        active = {}
        _reference_writer_local.active = active
    previous = active.get(key)
    owner_pid = os.getpid()
    if previous is not None and previous[0] == owner_pid:
        _assert_reference_writer_target(out_dir)
        yield
        return
    fd = None
    acquired = False
    primary_error: BaseException | None = None
    try:
        if out_dir.is_symlink():
            raise IdentityError("reference writer target is a symlink")
        out_dir.mkdir(parents=True, exist_ok=True)
        fd = os.open(out_dir, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
                     | getattr(os, "O_NOFOLLOW", 0))
        held = os.fstat(fd)
        if not stat.S_ISDIR(held.st_mode):
            raise IdentityError("reference writer target is not a directory")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno in (errno.EACCES, errno.EAGAIN):
                raise IdentityError("reference writer busy; no files changed") from exc
            raise IdentityError("reference writer locking unavailable") from exc
        acquired = True
        active[key] = (owner_pid, fd, held.st_dev, held.st_ino)
        _assert_reference_writer_target(out_dir)
        yield
    except OSError as exc:
        if acquired:
            primary_error = exc
            raise  # Preserve the original builder/rollback exception contract.
        primary_error = IdentityError("reference writer target unavailable")
        raise primary_error from exc
    except BaseException as exc:
        primary_error = exc
        raise
    finally:
        cleanup_errors: list[OSError] = []
        try:
            if acquired:
                if previous is None:
                    active.pop(key, None)
                else:
                    active[key] = previous
                # A forked child must never unlock the parent's open description.
                if os.getpid() == owner_pid:
                    try:
                        fcntl.flock(fd, fcntl.LOCK_UN)
                    except OSError as exc:
                        cleanup_errors.append(exc)
        finally:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError as exc:
                    # Do not retry close: the descriptor may already be released.
                    cleanup_errors.append(exc)
        if cleanup_errors:
            # Preserve this scope's original failure, including its errno and
            # identity. An exception already handled by our caller is unrelated.
            if primary_error is not None:
                for error in cleanup_errors:
                    primary_error.add_note(f"reference writer cleanup: {error}")
            else:
                first, *additional = cleanup_errors
                for error in additional:
                    first.add_note(f"additional reference writer cleanup: {error}")
                raise first


@dataclass(frozen=True, slots=True)
class InitialReferencePromotion:
    """A receipt replacement, directory flush, and actual native read completed.

    The retained preparation's conservative admission/authenticity markers are
    unchanged. This result is not source qualification or a trading admission.
    """
    prepared: "ParquetBoundInitialCandidate"
    read: "IdentitySnapshotRead"
    directory_synced: bool


class InitialReferencePromotionError(IdentityError):
    """An attempted rename needs observation, never an automatic second write."""

    def __init__(self, *, prepared, effect_state: str, directory_synced: bool):
        self.prepared = prepared
        self.effect_state = effect_state
        self.directory_synced = directory_synced
        super().__init__(
            f"initial reference promotion interrupted: effect_state={effect_state}; "
            f"directory_synced={directory_synced}; reconcile exact receipt/artifact bytes"
        )


def _initial_reference_path(directory: str | Path) -> Path:
    if not isinstance(directory, (str, Path)):
        raise IdentityError("initial reference requires an absolute existing directory")
    root = Path(directory)
    if not root.is_absolute() or ".." in root.parts:
        raise IdentityError("initial reference requires an absolute existing directory")
    return root


def _initial_reference_expected(receipt_sha256: str, artifact_sha256: dict) -> tuple:
    from engine.entry_radar.replay.identity_observation_snapshot import REFERENCE_ARTIFACTS

    if (type(receipt_sha256) is not str
            or re.fullmatch(r"[0-9a-f]{64}", receipt_sha256) is None
            or type(artifact_sha256) is not dict
            or set(artifact_sha256) != set(REFERENCE_ARTIFACTS)
            or any(type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None
                   for value in artifact_sha256.values())):
        raise IdentityError("initial reference requires exact six SHA-256 preimages")
    return tuple((name, artifact_sha256[name]) for name in REFERENCE_ARTIFACTS)


def _initial_reference_files(directory_fd: int) -> tuple[bytes, dict[str, bytes]]:
    # Reuse the actual bounded, no-follow reader. This is not another decoder.
    from engine.entry_radar.replay.identity_observation_snapshot import (
        REFERENCE_ARTIFACTS, _read_file,
    )

    before = _read_file(directory_fd, RECEIPT_NAME, 9 * 1024 * 1024)
    artifacts = {name: _read_file(directory_fd, name, 64 * 1024 * 1024)
                 for name in REFERENCE_ARTIFACTS}
    after = _read_file(directory_fd, RECEIPT_NAME, 9 * 1024 * 1024)
    if before != after:
        raise IdentityError("initial reference receipt preimage changed during read")
    return before, artifacts


def _initial_reference_vector(artifacts: dict[str, bytes]) -> tuple:
    return tuple((name, hashlib.sha256(raw).hexdigest()) for name, raw in artifacts.items())


def _inspect_initial_reference_publication(
    root: Path, original_sha: str, candidate_sha: str, artifacts: tuple,
    *, expected_directory_identity: tuple | None = None,
) -> str:
    """Observe one stable path/byte vector; no locks, writes, retries or repairs."""
    fd = None
    state = "EFFECT_UNKNOWN"
    try:
        fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
                     | getattr(os, "O_CLOEXEC", 0))
        held = os.fstat(fd)
        identity = (held.st_dev, held.st_ino)
        if (not stat.S_ISDIR(held.st_mode)
                or (expected_directory_identity is not None
                    and identity != expected_directory_identity)):
            return state
        raw, observed_artifacts = _initial_reference_files(fd)
        now = os.stat(root, follow_symlinks=False)
        if (stat.S_ISDIR(now.st_mode) and (now.st_dev, now.st_ino) == identity
                and _initial_reference_vector(observed_artifacts) == artifacts):
            digest = hashlib.sha256(raw).hexdigest()
            if digest == candidate_sha:
                state = "APPLIED"
            elif digest == original_sha:
                state = "NOT_APPLIED"
    except (OSError, IdentityError):
        state = "EFFECT_UNKNOWN"
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                state = "EFFECT_UNKNOWN"  # A close failure is not retried.
    return state


def inspect_initial_reference_publication(
    out_dir: str | Path, *, original_receipt_sha256: str,
    candidate_receipt_sha256: str, artifact_sha256: dict[str, str],
) -> str:
    """Read-only reconciliation of a possibly interrupted initial promotion.

    APPLIED/NOT_APPLIED mean that the exact candidate/original receipt and all
    five expected artifact bytes were observed at this path. They do not prove
    the cause of those bytes, crash durability, source authenticity, or admission.
    Missing files, a directory change during inspection, torn reads, or
    unexpected bytes remain EFFECT_UNKNOWN.
    """
    root = _initial_reference_path(out_dir)
    vector = _initial_reference_expected(original_receipt_sha256, artifact_sha256)
    _initial_reference_expected(candidate_receipt_sha256, artifact_sha256)
    if candidate_receipt_sha256 == original_receipt_sha256:
        raise IdentityError("initial reference reconciliation requires distinct receipts")
    return _inspect_initial_reference_publication(
        root, original_receipt_sha256, candidate_receipt_sha256, vector)


@contextmanager
def _staged_initial_receipt(directory_fd: int, raw: bytes, mode: int):
    """Own only a new temporary receipt on the held directory descriptor."""
    import uuid

    name = f".initial-reference-{uuid.uuid4().hex}.tmp"
    fd = None
    created = False
    primary_error = None
    try:
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
                     | getattr(os, "O_CLOEXEC", 0), 0o600, dir_fd=directory_fd)
        created = True
        offset = 0
        while offset < len(raw):
            written = os.write(fd, raw[offset:])
            if written <= 0:
                raise OSError(errno.EIO, "initial reference staged write made no progress")
            offset += written
        os.fchmod(fd, mode & 0o777)
        os.fsync(fd)
        closing, fd = fd, None  # Never retry a failed close on a possibly reused fd.
        os.close(closing)
        yield name
    except BaseException as exc:
        primary_error = exc
        raise
    finally:
        cleanup_errors = []
        if fd is not None:
            try:
                os.close(fd)
            except OSError as exc:
                cleanup_errors.append(exc)
        if created:
            try:
                os.unlink(name, dir_fd=directory_fd)
            except FileNotFoundError:
                pass  # The successful rename consumed our temporary name.
            except OSError as exc:
                cleanup_errors.append(exc)
        if cleanup_errors:
            if primary_error is not None:
                for error in cleanup_errors:
                    primary_error.add_note(f"initial reference stage cleanup: {error}")
            else:
                first, *additional = cleanup_errors
                for error in additional:
                    first.add_note(f"additional initial reference stage cleanup: {error}")
                raise first


def promote_initial_reference_generation(
    out_dir: str | Path, *, expected_receipt_sha256: str,
    expected_artifact_sha256: dict[str, str],
) -> InitialReferencePromotion:
    """Explicit initial-only receipt promotion inside the existing Data OS owner.

    The caller must qualify the actual source set and installed writer before
    canonical invocation. Hashes and the normal code identity do not authenticate
    its market evidence. There is no caller clock, attestation flag, CLI or nightly
    activation. All five Parquets remain byte-identical; the accepted R23 decoder
    and native validator determine the candidate from those physical bytes.

    Hold R25's cooperative local writer lock through preparation, exact preimage
    recheck, same-directory receipt rename, directory fsync and actual readback.
    This does not coordinate other hosts or noncooperating filesystem writers.
    After the native receipt exists, legacy refresh deliberately refuses; this
    is not a history-preserving successor-generation or rollback publisher.
    """
    from engine.entry_radar.replay.identity_observation_snapshot import (
        _read_file, read_identity_snapshot,
    )
    from engine.neuralweb.market_memory_identity_candidate import (
        build_parquet_bound_initial_candidate,
    )

    root = _initial_reference_path(out_dir)
    vector = _initial_reference_expected(expected_receipt_sha256, expected_artifact_sha256)
    try:
        existing = os.stat(root, follow_symlinks=False)
    except OSError as exc:
        raise IdentityError("initial reference requires an existing directory") from exc
    if not stat.S_ISDIR(existing.st_mode):
        raise IdentityError("initial reference target must be an existing directory")
    directory_identity = (existing.st_dev, existing.st_ino)
    replace_attempted = False
    directory_synced = False
    prepared = None
    try:
        with _reference_writer_scope(root):
            _pid, directory_fd, device, inode = _reference_writer_local.active[_writer_path(root)]
            if (device, inode) != directory_identity:
                raise IdentityError("initial reference target changed before writer acquisition")
            before, artifacts = _initial_reference_files(directory_fd)
            if (hashlib.sha256(before).hexdigest() != expected_receipt_sha256
                    or _initial_reference_vector(artifacts) != vector):
                raise IdentityError("initial reference preimage mismatch")
            code_version = _git_sha()
            prepared = build_parquet_bound_initial_candidate(
                before, artifacts, code_version=code_version)
            del artifacts
            _assert_reference_writer_target(root)
            receipt_stat = os.stat(RECEIPT_NAME, dir_fd=directory_fd, follow_symlinks=False)
            if not stat.S_ISREG(receipt_stat.st_mode):
                raise IdentityError("initial reference receipt preimage is no longer regular")
            raw = prepared.candidate.candidate_receipt_bytes
            with _staged_initial_receipt(directory_fd, raw, receipt_stat.st_mode) as staged:
                _assert_reference_writer_target(root)
                current, current_artifacts = _initial_reference_files(directory_fd)
                if (current != before or _initial_reference_vector(current_artifacts) != vector):
                    raise IdentityError("initial reference preimage changed before commit")
                del current_artifacts
                if _git_sha() != code_version:
                    raise IdentityError("initial reference code identity changed before commit")
                if _read_file(directory_fd, staged, 9 * 1024 * 1024) != raw:
                    raise IdentityError("initial reference staged receipt changed before commit")
                _assert_reference_writer_target(root)
                replace_attempted = True
                os.replace(staged, RECEIPT_NAME, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
                os.fsync(directory_fd)
                directory_synced = True
                observed = read_identity_snapshot(root)
                _assert_reference_writer_target(root)
                if (observed.snapshot.receipt_bytes != raw
                        or observed.receipt.receipt_sha256 != prepared.candidate.candidate_receipt_sha256
                        or observed.receipt.generation_id != prepared.candidate.generation_id
                        or observed.receipt.artifact_sha256 != vector):
                    raise IdentityError("initial reference actual readback does not match candidate")
                result = InitialReferencePromotion(prepared, observed, directory_synced=True)
        return result
    except BaseException as exc:
        if not replace_attempted:
            raise
        try:
            effect = _inspect_initial_reference_publication(
                root, expected_receipt_sha256, prepared.candidate.candidate_receipt_sha256,
                vector, expected_directory_identity=directory_identity)
        except Exception as reconciliation_error:
            effect = "EFFECT_UNKNOWN"
            exc.add_note(f"initial reference reconciliation failed: {reconciliation_error}")
        if isinstance(exc, Exception):
            raise InitialReferencePromotionError(
                prepared=prepared, effect_state=effect, directory_synced=directory_synced) from exc
        # Preserve KeyboardInterrupt/SystemExit, with exact recovery identities.
        exc.add_note(
            f"initial reference promotion: effect_state={effect}; directory_synced={directory_synced}; "
            f"original_receipt_sha256={expected_receipt_sha256}; "
            f"candidate_receipt_sha256={prepared.candidate.candidate_receipt_sha256}; "
            f"artifact_sha256={dict(vector)}"
        )
        raise


def _assert_no_unpreserved_native_generation(out_dir: Path) -> None:
    """Fail closed before legacy builder rewrites any native identity history.

    The ordinary security-master builder still emits legacy receipt structure;
    it cannot append authenticated native publication/observation history.
    Any existing native key, including a partial or malformed one, is a
    potential generation boundary and MUST NOT be stripped by a successful
    rebuild. The only lawful remedy is a separate source-owner writer that
    retains and validates the complete native context. This is not that writer.
    """
    _assert_reference_writer_target(out_dir)
    receipt_path = out_dir / RECEIPT_NAME
    if not receipt_path.exists():
        return
    receipt, _ = _reference_json(receipt_path)
    if "publication" in receipt or "identity_observations" in receipt:
        raise IdentityError(
            "native identity publication/history cannot be preserved by legacy "
            "security-master builder; refusing regeneration before source writes"
        )


def _reference_ns(value: object, name: str) -> int:
    if type(value) is not int or value <= 0:
        raise IdentityError(f"invalid reference {name}")
    return value


def _reference_clock_ns(value: object) -> int:
    try:
        clock = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if clock.tzinfo is None or clock.utcoffset() is None:
            raise ValueError("naive")
        delta = clock.astimezone(timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)
        return ((delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds) * 1000
    except (TypeError, ValueError, OverflowError) as exc:
        raise IdentityError("invalid reference UTC clock") from exc


def _reference_clock_iso(ns: int) -> str:
    # Ceiling, never float rounding or truncation that advances availability.
    return (datetime(1970, 1, 1, tzinfo=timezone.utc)
            + timedelta(microseconds=(ns + 999) // 1000)).isoformat()


_DIRECT_REGISTRANT_KEYS = frozenset({
    "symbol", "response_body", "capture", "listing_body", "listing_receipt_body",
})
_FUND_REFERENCE_KEYS = frozenset({"fund_reference_body", "fund_reference_capture"})
_FUND_REFERENCE_URL = "https://www.sec.gov/files/company_tickers_mf.json"


def _direct_registrant_source_shape(source) -> bool:
    return (isinstance(source, dict) and set(source) in
            (_DIRECT_REGISTRANT_KEYS, _DIRECT_REGISTRANT_KEYS | _FUND_REFERENCE_KEYS))


def _fund_reference_capture(capture: dict, *, on: date, latest: int) -> int:
    """Validate one retained official HTTP observation, never invent its clock."""
    keys = {"url", "final_url", "status", "bytes", "sha256",
            "request_started_at", "read_completed_at"}
    if (not isinstance(capture, dict) or set(capture) != keys
            or capture["url"] != _FUND_REFERENCE_URL
            or capture["final_url"] != _FUND_REFERENCE_URL
            or type(capture["status"]) is not int or capture["status"] != 200
            or type(capture["bytes"]) is not int
            or not 0 < capture["bytes"] <= _REFERENCE_MAX_BYTES
            or not isinstance(capture["sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", capture["sha256"]) is None):
        raise IdentityError("invalid SEC fund-reference capture")
    started = _reference_clock_ns(capture["request_started_at"])
    completed = _reference_clock_ns(capture["read_completed_at"])
    if (not 0 < started <= completed <= latest
            or _reference_clock_iso(started)[:10] != on.isoformat()
            or _reference_clock_iso(completed)[:10] != on.isoformat()):
        raise IdentityError("SEC fund-reference observation clocks disagree")
    return completed


def _validate_fund_reference(link: dict, *, symbol: str, cik: str,
                             on: date, latest: int) -> int:
    """Check retained selection/provenance consistency, not HTTP authenticity."""
    keys = {"schema", "symbol", "cik", "series_id", "class_id",
            "selection_sha256", "capture"}
    if (symbol not in {"QQQ", "SMH"} or not isinstance(link, dict)
            or set(link) != keys or link["schema"] != "mastermind.sec_fund_reference.v1"
            or link["symbol"] != symbol or link["cik"] != cik
            or not isinstance(link["series_id"], str)
            or re.fullmatch(r"S[0-9]{9}", link["series_id"]) is None
            or not isinstance(link["class_id"], str)
            or re.fullmatch(r"C[0-9]{9}", link["class_id"]) is None):
        raise IdentityError("invalid retained SEC fund-reference selection")
    selected = {k: link[k] for k in ("symbol", "cik", "series_id", "class_id")}
    if link["selection_sha256"] != _reference_digest(selected):
        raise IdentityError("SEC fund-reference selection changed")
    return _fund_reference_capture(link["capture"], on=on, latest=latest)


def _prepare_fund_reference(body: bytes, capture: dict, *, symbol: str,
                            cik: str, on: date, decision: int) -> tuple[dict, int]:
    """Bind an explicitly captured search-association row to SEC and listing evidence.

    SEC does not guarantee this search file's accuracy/scope. This is one
    corroborating input to the existing independence fence, not a canonical
    security, issuer group, vendor alias, or historical identity observation.
    """
    if type(body) is not bytes or not 0 < len(body) <= _REFERENCE_MAX_BYTES:
        raise IdentityError("SEC fund-reference byte bound")
    completed = _fund_reference_capture(capture, on=on, latest=decision)
    if capture["bytes"] != len(body) or capture["sha256"] != hashlib.sha256(body).hexdigest():
        raise IdentityError("SEC fund-reference capture does not bind exact bytes")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate SEC fund-reference JSON key")
            result[key] = value
        return result

    try:
        value = json.loads(body.decode("utf-8"), object_pairs_hook=pairs,
            parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)),
            parse_float=lambda v: (_ for _ in ()).throw(ValueError(v)))
        if (not isinstance(value, dict) or set(value) != {"fields", "data"}
                or value["fields"] != ["cik", "seriesId", "classId", "symbol"]
                or not isinstance(value["data"], list) or not 0 < len(value["data"]) <= 100000):
            raise ValueError("unsupported SEC fund-reference table")
        matches = []
        for row in value["data"]:
            if (not isinstance(row, list) or len(row) != 4
                    or type(row[0]) is not int or not 0 < row[0] < 10**10
                    or not isinstance(row[1], str) or re.fullmatch(r"S[0-9]{9}", row[1]) is None
                    or not isinstance(row[2], str) or re.fullmatch(r"C[0-9]{9}", row[2]) is None
                    or not isinstance(row[3], str) or len(row[3]) > 32):
                raise ValueError("invalid SEC fund-reference row")
            # SEC can retain an unassigned class with an empty ticker. It is
            # not a match; conflicting or duplicate requested-symbol rows refuse.
            if row[3] == symbol:
                matches.append(row)
        if len(matches) != 1 or f"{matches[0][0]:010d}" != cik:
            raise ValueError("fund symbol/registrant missing, ambiguous or conflicting")
    except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
        raise IdentityError("invalid SEC fund-reference evidence") from exc
    selected = dict(symbol=symbol, cik=cik, series_id=matches[0][1], class_id=matches[0][2])
    link = {"schema": "mastermind.sec_fund_reference.v1", **selected,
            "selection_sha256": _reference_digest(selected), "capture": dict(capture)}
    _validate_fund_reference(link, symbol=symbol, cik=cik, on=on, latest=decision)
    return link, completed


def prepare_direct_registrant(*, symbol: str, response_body: bytes, capture: dict,
                             listing_body: bytes, listing_receipt_body: bytes,
                             decision_at: str, fund_reference_body: bytes | None = None,
                             fund_reference_capture: dict | None = None) -> dict:
    """Prepare a *new* dated ETF observation for the existing mint fence.

    The SEC supplies registrant identity, not a precise venue or issuer grouping.
    The existing collector receipt supplies the current listing observation, not
    a SEC binding. Neither ticker equality nor this result is a canonical ID.
    Only the existing canonical mint may decide independence against its actual
    lost rows. No old reference disposition is read, replaced or retried here.
    The caller owns capture provenance; hashes detect changes, not authenticate
    an HTTP sender. This function reads supplied bytes and publishes nothing.
    """
    from lib.symbol_directory_receipts import (
        ReceiptValidationError, validate_symbol_directory_completion_receipt_bytes,
    )
    import pandas as pd
    import pyarrow.parquet as pq
    import math

    if not isinstance(symbol, str) or symbol not in {"SPY", "QQQ", "SMH"}:
        raise IdentityError("direct registrant intake supports only existing ETF probes")
    if (type(response_body) is not bytes or not response_body
            or len(response_body) > _REFERENCE_MAX_BYTES
            or type(listing_body) is not bytes or not listing_body
            or len(listing_body) > 8 * 1024 * 1024
            or type(listing_receipt_body) is not bytes or not listing_receipt_body
            or len(listing_receipt_body) > 512 * 1024):
        raise IdentityError("direct registrant evidence exceeds its byte bounds")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def finite(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("nonfinite JSON number")
        return number

    try:
        sec = json.loads(response_body.decode("utf-8"), object_pairs_hook=pairs,
                         parse_float=finite,
                         parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
        receipt = json.loads(listing_receipt_body.decode("utf-8"), object_pairs_hook=pairs)
        # Bound decoded row count before the canonical validator reads Parquet.
        if pq.ParquetFile(io.BytesIO(listing_body)).metadata.num_rows > 200000:
            raise ValueError("too many listing rows")
        receipt = validate_symbol_directory_completion_receipt_bytes(
            receipt, listing_receipt_body, listing_body, expected_kind="listing_snapshot")
    except (ValueError, TypeError, RecursionError, UnicodeError, ReceiptValidationError) as exc:
        raise IdentityError("invalid direct registrant or listing evidence") from exc
    if not isinstance(sec, dict) or not isinstance(capture, dict):
        raise IdentityError("direct registrant evidence must be objects")
    cik = sec.get("cik")
    tickers = sec.get("tickers")
    title = sec.get("name")
    if (not isinstance(cik, str) or not re.fullmatch(r"[0-9]{10}", cik) or int(cik) == 0
            or not isinstance(title, str) or not title.strip() or len(title) > 512
            or not isinstance(tickers, list)
            or any(not isinstance(t, str) or not t for t in tickers)
            or len(tickers) != len(set(tickers))):
        raise IdentityError("SEC response does not identify the requested registrant")
    supplied_fund = fund_reference_body is not None or fund_reference_capture is not None
    if symbol not in tickers:
        if tickers or symbol not in {"QQQ", "SMH"} or not supplied_fund:
            raise IdentityError("SEC response does not identify the requested registrant")
    elif supplied_fund:
        raise IdentityError("fund-reference extension is only for empty QQQ/SMH ticker arrays")
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    digest = hashlib.sha256(response_body).hexdigest()
    if (capture.get("url") != url or capture.get("final_url") != url
            or type(capture.get("status")) is not int or capture["status"] != 200
            or type(capture.get("bytes")) is not int or capture["bytes"] != len(response_body)
            or capture.get("sha256") != digest):
        raise IdentityError("SEC capture does not bind the exact response")
    started = _reference_clock_ns(capture.get("request_started_at"))
    completed = _reference_clock_ns(capture.get("read_completed_at"))
    decision = _reference_clock_ns(decision_at)
    listing_completed = _reference_clock_ns(receipt["clocks"]["collector_completed_at"])
    on = date.fromisoformat(receipt["observation_date"])
    if (not 0 < started <= completed <= decision or listing_completed > decision
            or _reference_clock_iso(started)[:10] != on.isoformat()
            or _reference_clock_iso(completed)[:10] != on.isoformat()):
        raise IdentityError("direct registrant observation clocks disagree")
    if receipt["authority"]["listing_identity_observation_eligible"] is not True:
        raise IdentityError("listing observation is ineligible")
    frame = pd.read_parquet(io.BytesIO(listing_body))
    rows = frame.loc[frame["symbol"] == symbol]
    exchange, venue, _, _ = REFERENCE_PROBES[symbol]
    if len(rows) != 1:
        raise IdentityError("listing observation is missing or ambiguous")
    row = rows.iloc[0]
    if (row["exchange"] != exchange or not bool(row["etf"])
            or bool(row["test_issue"]) or bool(row["is_preferred"])):
        raise IdentityError("listing observation conflicts with the ETF probe")
    # Reuse the scoped resolver, including rename/venue law. SEC's broad
    # 'NYSE' label is never translated into XNYS or another MIC here.
    resolutions = resolve_universe(
        {symbol: {"sources": ["direct_registrant_observation"], "first_seen": on}},
        {}, {symbol: exchange}, on.isoformat(), reference_probe_keys=frozenset({symbol}))
    if (len(resolutions) != 1 or resolutions[0].listing_key is None
            or resolutions[0].listing_key.mic != venue):
        raise IdentityError("canonical resolver did not establish the listing")
    resolution = resolutions[0]
    fund, fund_completed = None, 0
    if supplied_fund:
        fund, fund_completed = _prepare_fund_reference(
            fund_reference_body, fund_reference_capture, symbol=symbol,
            cik=cik, on=on, decision=decision)
    return {"resolution": resolution, "registrant": {
        "symbol": symbol, "cik": cik, "title": title,
        "listing_key": resolution.listing_key.render(), "observed_on": on.isoformat(),
        "known_at": _reference_clock_iso(max(completed, listing_completed, fund_completed)),
        "response_sha256": digest,
        "listing_snapshot_sha256": receipt["artifact"]["sha256"],
        "listing_receipt_sha256": hashlib.sha256(listing_receipt_body).hexdigest(),
        "capture": {key: capture[key] for key in (
            "url", "final_url", "status", "bytes", "sha256",
            "request_started_at", "read_completed_at")},
        "scope": "pending_transition_independence_only",
        **({"fund_reference": fund} if fund is not None else {}),
    }}


def _load_reference_input(out_dir: Path, path: Path | None) -> dict | None:
    previous = None
    receipt_path = out_dir / RECEIPT_NAME
    if receipt_path.exists():
        previous = _reference_json(receipt_path)[0].get("prospective_reference")
    if path is None and previous is None:
        return None
    if previous is not None and not isinstance(previous, dict):
        raise IdentityError("invalid retained prospective reference receipt")
    if path is not None:
        bundle, file_sha = _reference_json(path)
        if previous is not None and bundle != previous.get("input"):
            raise IdentityError("conflicting prospective reference input; revisions not admitted")
    else:
        bundle = previous.get("input")
        file_sha = previous.get("input_file_sha256")
    if not isinstance(bundle, dict) or bundle.get("schema") != REFERENCE_SCHEMA:
        raise IdentityError("unsupported prospective reference schema")
    probes = bundle.get("probes")
    if not isinstance(probes, dict) or set(probes) != set(REFERENCE_PROBES):
        raise IdentityError("reference intake requires exactly MU/SPY/QQQ/SMH probes")
    dates = {r.get("requested_date") for r in probes.values() if isinstance(r, dict)}
    if len(dates) != 1 or len(probes) != sum(isinstance(r, dict) for r in probes.values()):
        raise IdentityError("reference probes require one explicit observation date")
    requested_date = next(iter(dates))
    try:
        on = date.fromisoformat(requested_date)
    except (ValueError, TypeError) as exc:
        raise IdentityError("invalid reference observation date") from exc
    if on.isoformat() != requested_date:
        raise IdentityError("noncanonical reference date")
    snapshot = SYMBOL_DIR_SNAPSHOTS / f"{requested_date}.parquet"
    receipt_file = SYMBOL_DIR_SNAPSHOTS.parent / "receipts" / "snapshots" / f"{requested_date}.json"
    listing_receipt, listing_receipt_sha = _reference_json(receipt_file)
    with snapshot.open("rb") as source:
        snapshot_bytes = source.read(8 * 1024 * 1024 + 1)
    if len(snapshot_bytes) > 8 * 1024 * 1024:
        raise IdentityError("listing snapshot exceeds reference read bound")
    snapshot_sha = hashlib.sha256(snapshot_bytes).hexdigest()
    artifact = listing_receipt.get("artifact", {})
    if (artifact.get("sha256") != snapshot_sha or artifact.get("bytes") != len(snapshot_bytes)
            or artifact.get("key") != f"snapshots/{requested_date}.parquet"
            or listing_receipt.get("observation_date") != requested_date
            or listing_receipt.get("completeness", {}).get("status") != "complete"
            or listing_receipt.get("completeness", {}).get("duplicate_key_count") != 0
            or listing_receipt.get("authority", {}).get("listing_identity_observation_eligible") is not True):
        raise IdentityError("listing source receipt does not bind a complete eligible snapshot")
    import pandas as pd
    listing_frame = pd.read_parquet(io.BytesIO(snapshot_bytes))
    if len(listing_frame) != artifact.get("rows"):
        raise IdentityError("listing source receipt row count mismatch")
    listing_started = _reference_clock_ns(listing_receipt.get("clocks", {}).get("collector_started_at"))
    listing_completed = _reference_clock_ns(listing_receipt.get("clocks", {}).get("collector_completed_at"))
    mic = bundle.get("mic_evidence", {})
    selected = mic.get("selected_row", {})
    if (mic.get("http_status") != 200
            or selected.get("MIC") != ARCX or selected.get("OPERATING MIC") != XNYS
            or selected.get("STATUS") != "ACTIVE" or selected.get("OPRT/SGMT") != "SGMT"
            or selected.get("ISO COUNTRY CODE (ISO 3166)") != "US"
            or mic.get("source_url") != "https://www.iso20022.org/sites/default/files/ISO10383_MIC/ISO10383_MIC.csv"
            or not re.fullmatch(r"[0-9a-f]{64}", str(mic.get("response_sha256", "")))):
        raise IdentityError("invalid official ARCX MIC evidence")
    mic_started = _reference_clock_ns(mic.get("request_started_at_utc"))
    mic_completed = _reference_clock_ns(mic.get("response_read_completed_at_utc"))
    read_completed = time.time_ns()
    if previous is not None:
        prior_clock = _reference_ns(previous.get("source_read_completed_at_utc_ns"), "retained read clock")
        if prior_clock > read_completed:
            raise IdentityError("retained reference read is in the future")
        read_completed = prior_clock
        if previous.get("input_sha256") != _reference_digest(bundle):
            raise IdentityError("retained reference input seal mismatch")
    if not (0 < listing_started <= listing_completed <= read_completed
            and 0 < mic_started <= mic_completed <= read_completed):
        raise IdentityError("inconsistent reference source clocks")
    common = {
        "listing_snapshot_sha256": snapshot_sha,
        "listing_receipt_sha256": listing_receipt_sha,
        "mic_evidence_sha256": _reference_digest(mic),
        "source_read_completed_at_utc_ns": read_completed,
    }
    if previous is not None and previous.get("evidence") != common:
        raise IdentityError("retained reference source evidence changed")
    states = {}
    for symbol, (exchange, venue, kind, etf) in REFERENCE_PROBES.items():
        record = probes[symbol]
        if (record.get("request_path") != f"/v3/reference/tickers/{symbol}"
                or record.get("request_params") != {"date": requested_date}):
            raise IdentityError("native reference request metadata mismatch")
        started = _reference_ns(record.get("request_started_at_utc_ns"), "request clock")
        observed = _reference_ns(record.get("decoded_payload_observed_at_utc_ns"), "decoded observation clock")
        if not 0 < started <= observed <= read_completed:
            raise IdentityError("inconsistent native reference observation clocks")
        if _reference_clock_iso(started)[:10] != requested_date:
            raise IdentityError("prospective request date must be the actual request UTC date")
        payload = record.get("decoded_payload")
        if record.get("decoded_payload_sha256") != _reference_digest(payload):
            raise IdentityError("decoded native payload seal mismatch")
        rows = listing_frame.loc[listing_frame["symbol"] == symbol]
        reason = None
        if len(rows) != 1:
            reason = "official_listing_not_unique"
        else:
            row = rows.iloc[0]
            if (str(row["exchange"]) != exchange or bool(row["etf"]) != etf
                    or bool(row["test_issue"]) or bool(row["is_preferred"])):
                reason = "official_listing_identity_conflict"
        native = payload.get("results") if isinstance(payload, dict) else None
        if reason is None and (not isinstance(payload, dict) or payload.get("status") != "OK"
                               or not isinstance(native, dict)):
            reason = "native_reference_unavailable"
        expected = {"ticker": symbol, "market": "stocks", "locale": "us",
                    "primary_exchange": venue, "type": kind, "active": True}
        if reason is None and (native.get("active") is not True
                               or any(native.get(k) != v for k, v in expected.items())):
            reason = "native_reference_identity_conflict"
        if reason is None and not re.fullmatch(r"BBG[A-Z0-9]{9}", str(native.get("composite_figi", ""))):
            reason = "native_stable_identifier_missing"
        known_at = _reference_clock_iso(max(observed, listing_completed, mic_completed, read_completed))
        states[symbol] = {
            "symbol": symbol, "status": "REFUSED" if reason else "EVIDENCE_READY",
            "code": reason, "known_at": known_at,
            "evidence_sha256": _reference_digest({"record": record, **common}),
            "native_identity": ({k: native[k] for k in (*expected, "composite_figi")} if reason is None else None),
        }
        if previous is not None:
            prior = previous.get("probes", {}).get(symbol)
            if not isinstance(prior, dict) or prior.get("status") not in {"BOUND", "REFUSED"}:
                raise IdentityError("invalid retained reference disposition")
            for field in ("symbol", "known_at", "evidence_sha256", "native_identity"):
                if prior.get(field) != states[symbol][field]:
                    raise IdentityError("retained reference binding evidence changed")
            if prior["status"] == "REFUSED":
                owner_refusal = prior.get("code") in {
                    "canonical_identity_refused", "canonical_listing_identity_conflict"}
                if not ((owner_refusal and reason is None) or prior.get("code") == reason):
                    raise IdentityError("invalid retained reference refusal")
                # This is the original dated disposition, not a new mint attempt.
                # A later owner change cannot upgrade old evidence at its old clock.
                states[symbol] = dict(prior)
    return {
        "schema": REFERENCE_SCHEMA, "input": bundle, "input_sha256": _reference_digest(bundle),
        "input_file_sha256": file_sha, "source_read_completed_at_utc_ns": read_completed,
        "evidence": common, "probes": states,
        "clock_semantics": "known_at observes binding evidence; not publication or Radar read availability",
        "provider_date_semantics": "request date is not first-seen proof; filing-derived fields can include later-submitted filings and are unused",
        "provider_reference_documentation": "https://massive.com/docs/rest/stocks/tickers/ticker-overview",
        "consumer_requirement": "candidate input additionally requires actual native snapshot read receipt by cutoff",
        "authority": {"research_admitted": False, "trading_authority": False},
    }


def _reference_aliases(state: dict | None, ids: dict, master_rows: list[dict],
                       pending: list[dict], resurrection: list[dict]) -> list[AliasRow]:
    if state is None:
        return []
    master = {r["security_id"]: r for r in master_rows}
    aliases = []
    for symbol, evidence in state["probes"].items():
        if evidence["status"] == "REFUSED":
            continue
        sec = ids.get(symbol)
        if sec is None or sec not in master or master[sec].get("security_state"):
            refusals = [r for r in pending if r.get("symbol") == symbol]
            refusals += [r for r in resurrection if r.get("key") == symbol]
            evidence.update(status="REFUSED", code="canonical_identity_refused", owner_refusals=refusals)
            continue
        row = master[sec]
        listing = parse_listing_key(row["listing_key"])
        native = evidence["native_identity"]
        # Compare the canonical owner row and its established current-symbol
        # relationship, never the immutable security_id spelling. No venue
        # continuity authority is introduced by this prospective source slice.
        if (row.get("country") != "US" or row.get("mic") != native["primary_exchange"]
                or listing.country != row.get("country") or listing.mic != row.get("mic")
                or listing.code != row.get("inception_code")
                or _current_symbol_of_row(row) != native["ticker"]):
            evidence.update(status="REFUSED", code="canonical_listing_identity_conflict",
                            canonical_listing_identity={k: row.get(k) for k in
                                ("security_id", "listing_key", "country", "mic", "inception_code")})
            continue
        start = date.fromisoformat(state["input"]["probes"][symbol]["requested_date"])
        seal = alias_binding_sha256("polygon", symbol, sec, start, None,
                                    evidence["known_at"], evidence["evidence_sha256"])
        aliases.append(AliasRow("polygon", symbol, sec, start, None,
                                evidence["known_at"], evidence["evidence_sha256"], seal))
        evidence.update(status="BOUND", code=None, security_id=sec,
                        listing_key=master[sec]["listing_key"], binding_sha256=seal)
    return aliases


def read_direct_registrant_inputs(path: Path) -> list[dict]:
    """Read one explicit local capture bundle; no network or credential access."""
    from lib.symbol_directory_receipts import ReceiptValidationError, _read_regular_file

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate input JSON key")
            result[key] = value
        return result

    try:
        body = _read_regular_file(path, label="direct registrant manifest", limit=512 * 1024)
        manifest = json.loads(body, object_pairs_hook=pairs,
                              parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
        if (not isinstance(manifest, dict) or set(manifest) != {"schema", "sources"}
                or manifest["schema"] not in {"mastermind.direct_registrant_input.v1",
                                               "mastermind.direct_registrant_input.v2"}
                or not isinstance(manifest["sources"], list) or not 1 <= len(manifest["sources"]) <= 3):
            raise ValueError("invalid direct registrant manifest")
        inputs = []
        for record in manifest["sources"]:
            if (not _direct_registrant_source_shape(record)
                    or (manifest["schema"] == "mastermind.direct_registrant_input.v1"
                        and set(record) != _DIRECT_REGISTRANT_KEYS)):
                raise ValueError("invalid direct registrant source")
            source = dict(record)
            files = [("response_body", _REFERENCE_MAX_BYTES),
                     ("listing_body", 8 * 1024 * 1024),
                     ("listing_receipt_body", 512 * 1024)]
            if "fund_reference_body" in source:
                files.append(("fund_reference_body", _REFERENCE_MAX_BYTES))
            for key, limit in files:
                name = source[key]
                if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", name):
                    raise ValueError("source must be a sibling filename")
                source[key] = _read_regular_file(path.parent / name, label=key, limit=limit)
            inputs.append(source)
        return inputs
    except (OSError, ValueError, TypeError, RecursionError, ReceiptValidationError) as exc:
        raise IdentityError("invalid direct registrant input files") from exc


def _direct_registrant_state(out_dir: Path, inputs: tuple[dict, ...] | list[dict],
                             now: str) -> tuple[dict | None, list[Resolution]]:
    """Carry decisions inside the existing receipt; never replay retained inputs."""
    previous = None
    if (out_dir / RECEIPT_NAME).exists():
        previous = _reference_json(out_dir / RECEIPT_NAME)[0].get("direct_registrant_intake")
    if type(inputs) not in (tuple, list) or len(inputs) > 3:
        raise IdentityError("direct registrant intake exceeds the bounded probe set")
    if previous is None and not inputs:
        return None, []
    clock = datetime.fromisoformat(now.replace("Z", "+00:00"))
    if clock.tzinfo is None:
        clock = clock.replace(tzinfo=timezone.utc)
    state = {"schema": "mastermind.direct_registrant_intake.v1", "observations": {}}
    if previous is not None:
        if (not isinstance(previous, dict) or set(previous) != {"schema", "observations", "sha256"}
                or previous.get("schema") != state["schema"]
                or not isinstance(previous.get("observations"), dict)
                or len(previous["observations"]) > 3
                or previous["sha256"] != _reference_digest({k: previous[k] for k in ("schema", "observations")})):
            raise IdentityError("invalid retained direct registrant receipt")
        for key, row in previous["observations"].items():
            if (key not in {"SPY", "QQQ", "SMH"} or not isinstance(row, dict)
                    or row.get("symbol") != key or not isinstance(row.get("status"), str)
                    or row["status"] not in {"BOUND", "REFUSED"}
                    or row.get("scope") != "pending_transition_independence_only"
                    or _reference_clock_ns(row.get("known_at")) > _reference_clock_ns(clock.isoformat())):
                raise IdentityError("invalid retained direct registrant disposition")
            try:
                on = date.fromisoformat(row["observed_on"])
                capture = row["capture"]
                expected_url = f'https://data.sec.gov/submissions/CIK{row["cik"]}.json'
                started = _reference_clock_ns(capture["request_started_at"])
                completed = _reference_clock_ns(capture["read_completed_at"])
                known = _reference_clock_ns(row["known_at"])
                listing = parse_listing_key(row["listing_key"])
                valid = (
                    on.isoformat() == row["observed_on"]
                    and isinstance(row["cik"], str)
                    and re.fullmatch(r"[0-9]{10}", row["cik"]) is not None
                    and int(row["cik"]) > 0
                    and isinstance(row["title"], str) and 0 < len(row["title"].strip()) <= 512
                    and listing.country == DEFAULT_COUNTRY
                    and listing.mic == REFERENCE_PROBES[key][1]
                    and listing.code == _inception_code(key, key)
                    and all(isinstance(row.get(field), str)
                            and re.fullmatch(r"[0-9a-f]{64}", row[field]) is not None
                            for field in ("response_sha256", "listing_snapshot_sha256", "listing_receipt_sha256"))
                    and set(capture) == {"url", "final_url", "status", "bytes", "sha256",
                                         "request_started_at", "read_completed_at"}
                    and capture["url"] == capture["final_url"] == expected_url
                    and type(capture["status"]) is int and capture["status"] == 200
                    and type(capture["bytes"]) is int and 0 < capture["bytes"] <= _REFERENCE_MAX_BYTES
                    and capture["sha256"] == row["response_sha256"]
                    and 0 < started <= completed <= known
                    and _reference_clock_iso(started)[:10] == on.isoformat()
                    and _reference_clock_iso(completed)[:10] == on.isoformat()
                )
                if row["status"] == "BOUND":
                    valid = valid and isinstance(row.get("security_id"), str) and bool(row["security_id"])
                else:
                    causes = row.get("owner_refusals")
                    valid = (valid and row.get("code") == "canonical_identity_refused"
                             and isinstance(causes, list) and bool(causes)
                             and all(isinstance(cause, dict) and cause.get("symbol") == key
                                     and isinstance(cause.get("reason"), str) and cause["reason"]
                                     for cause in causes))
                if "fund_reference" in row:
                    _validate_fund_reference(row["fund_reference"], symbol=key,
                                             cik=row["cik"], on=on, latest=known)
                if not valid:
                    raise IdentityError("invalid retained direct registrant fields")
            except (KeyError, TypeError, ValueError, OverflowError) as exc:
                raise IdentityError("invalid retained direct registrant fields") from exc
            state["observations"][key] = dict(row)
    prepared_resolutions = []
    for source in inputs:
        if not _direct_registrant_source_shape(source):
            raise IdentityError("invalid direct registrant input shape")
        if not isinstance(source["symbol"], str):
            raise IdentityError("invalid direct registrant symbol")
        if source["symbol"] in state["observations"]:
            raise IdentityError("direct registrant observation already retained; no replay")
        result = prepare_direct_registrant(**source, decision_at=clock.isoformat())
        row = result["registrant"]
        state["observations"][row["symbol"]] = dict(row, status="PENDING")
        prepared_resolutions.append(result["resolution"])
    return state, prepared_resolutions


def _current_direct_resolution(symbol: str, row: dict, directory: dict, flags: dict,
                               delisted: dict, snapshot_date: str | None) -> Resolution | None:
    """Use the current listing rail, never a retained observation as today's venue."""
    if (snapshot_date is None or snapshot_date < row["observed_on"] or symbol in delisted
            or directory.get(symbol) != REFERENCE_PROBES[symbol][0]
            or flags.get(symbol) != {"etf": True, "test_issue": False, "is_preferred": False}):
        return None
    resolved = resolve_universe(
        {symbol: {"sources": [], "first_seen": date.fromisoformat(row["observed_on"])}},
        delisted, directory, snapshot_date, reference_probe_keys=frozenset({symbol}))
    # The resolver also emits every exit-ledger key, including unrelated symbols.
    current = next(r for r in resolved if r.key == symbol)
    if current.listing_key is None or current.listing_key.render() != row["listing_key"]:
        return None
    return current


def _retained_direct_resolutions(state: dict | None, existing: list[dict], *,
                                 directory: dict, directory_flags: dict, delisted: dict,
                                 snapshot_date: str | None) -> list[Resolution]:
    """Re-derive stored active IDs only while the current rail still supports them."""
    results = []
    for symbol, row in (state["observations"].items() if state else ()):
        if row["status"] != "BOUND":
            continue
        matches = [r for r in existing if r["security_id"] == row.get("security_id")]
        if len(matches) != 1 or matches[0]["listing_key"] != row["listing_key"]:
            raise IdentityError("retained direct registrant canonical row is missing or conflicting")
        stored = matches[0]
        if stored.get("security_state"):
            continue  # historical observation retained; never resurrect a tombstone
        listing = parse_listing_key(stored["listing_key"])
        if (stored["country"] != listing.country or stored["mic"] != listing.mic
                or stored["inception_code"] != listing.code):
            raise IdentityError("retained direct registrant listing fields conflict")
        current = _current_direct_resolution(symbol, row, directory, directory_flags,
                                             delisted, snapshot_date)
        if current is not None:
            results.append(current)
    return results


def prepare_spy_option_root(sources: dict, *, decision_at: str) -> tuple[AliasRow, dict]:
    """Prepare one observed-day source inference; no network or publication.

    This profile is deliberately SPY-specific. Capture metadata belongs to the
    admitted caller and is not authentication. Cboe identifies the actual option
    product; Theta's v3 contract supplies the namespace semantics; SEC plus the
    native listing receipt identify the underlying. No name or ticker matching
    fallback, historical effective date, index admission or source-use grant.
    """
    import csv
    from html.parser import HTMLParser
    from lib.dataos.identity import option_root_binding_sha256

    urls = {
        "cboe_reference": "https://cdn.cboe.com/data/us/options/market_statistics/symbol_reference/cone-underlying.csv",
        "cboe_product": "https://www.cboe.com/tradable_products/sp_500/spx_weekly_options/specifications",
        "theta_contract": "https://thetadata.net/docs/operations/option_history_eod.html",
        "registrant": "https://data.sec.gov/submissions/CIK0000884394.json",
    }
    if type(sources) is not dict or set(sources) != set(urls) | {"listing_body", "listing_receipt_body"}:
        raise IdentityError("invalid option-root source bundle")
    decision = _reference_clock_ns(decision_at)
    bodies, observations, clocks = {}, {}, []
    for role, url in urls.items():
        source = sources[role]
        if type(source) is not dict or set(source) != {"body", "capture"}:
            raise IdentityError("invalid option-root source record")
        body, capture = source["body"], source["capture"]
        if (type(body) is not bytes or not 0 < len(body) <= _REFERENCE_MAX_BYTES
                or type(capture) is not dict
                or set(capture) != {"url", "final_url", "status", "bytes", "sha256",
                                    "request_started_at", "read_completed_at"}
                or capture.get("url") != url
                or capture.get("final_url") != url or type(capture.get("status")) is not int
                or capture["status"] != 200 or type(capture.get("bytes")) is not int
                or capture["bytes"] != len(body)
                or capture.get("sha256") != hashlib.sha256(body).hexdigest()):
            raise IdentityError("option-root capture does not bind the exact source")
        started = _reference_clock_ns(capture.get("request_started_at"))
        completed = _reference_clock_ns(capture.get("read_completed_at"))
        if not 0 < started <= completed <= decision:
            raise IdentityError("invalid option-root source clocks")
        clocks.extend((started, completed))
        observations[role] = {"url": url, "bytes": len(body), "sha256": capture["sha256"],
                              "request_started_at": _reference_clock_iso(started),
                              "read_completed_at": _reference_clock_iso(completed)}
        bodies[role] = body
    on = date.fromisoformat(_reference_clock_iso(max(clocks))[:10])
    if any(_reference_clock_iso(clock)[:10] != on.isoformat() for clock in clocks):
        raise IdentityError("option-root sources must be observed on one date")
    if _reference_clock_iso(decision)[:10] != on.isoformat():
        raise IdentityError("new option-root admission must occur on its observed date")

    class Tables(HTMLParser):
        def __init__(self):
            super().__init__()
            self.text, self.tables = [], []
            self.hidden = 0
            self.rows = self.cells = self.cell = None

        def handle_starttag(self, tag, attrs):
            if tag in ("script", "style", "template"):
                self.hidden += 1
            if self.hidden:
                return
            if tag == "table":
                if self.rows is not None:
                    raise ValueError("nested source table")
                self.rows = []
            if tag == "tr" and self.rows is not None:
                self.cells = []
            if tag in ("td", "th") and self.cells is not None:
                self.cell = []

        def handle_data(self, value):
            if self.hidden:
                return
            self.text.append(value)
            if self.cell is not None:
                self.cell.append(value)

        def handle_endtag(self, tag):
            if self.hidden:
                if tag in ("script", "style", "template"):
                    self.hidden -= 1
                return
            if tag in ("td", "th") and self.cell is not None:
                self.cells.append(" ".join(" ".join(self.cell).split()))
                self.cell = None
            if tag == "tr" and self.cells is not None:
                self.rows.append(self.cells)
                self.cells = None
            if tag == "table" and self.rows is not None:
                self.tables.append(self.rows)
                self.rows = None

    try:
        reader = csv.DictReader(io.StringIO(bodies["cboe_reference"].decode("utf-8-sig")))
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("duplicate reference columns")
        rows = list(reader)
        if len(rows) > 20000 or any(None in row or any(v is None for v in row.values()) for row in rows):
            raise ValueError("invalid reference rows")
        selected = [r for r in rows if r.get("Symbol") == "SPY"]
        if len(selected) != 1 or {k: selected[0].get(k) for k in
                ("Company", "Symbol Type", "Options Type", "Clearing")} != {
                "Company": "STATE STR SPDR S&P 500 ETF TR TR UNIT", "Symbol Type": "ETF",
                "Options Type": "Standard", "Clearing": "OCC"}:
            raise ValueError("SPY reference does not identify the standard ETF product")
        product = Tables()
        product.feed(bodies["cboe_product"].decode("utf-8"))
        matches = [(table, row.index("SPDR ® S&P 500 ® ETF Options")) for table in product.tables
                   for row in table if row.count("SPDR ® S&P 500 ® ETF Options") == 1]
        if len(matches) != 1:
            raise ValueError("ambiguous SPY product column")
        table, column = matches[0]
        for label, expected in (("Root Ticker Symbol", "SPY"), ("Options Chain", "SPY"),
                                ("Settlement Type", "Physical Shares of ETF"), ("Exercise Style", "American")):
            cells = [r for r in table if r and r[0] == label]
            if len(cells) != 1 or len(cells[0]) <= column or cells[0][column] != expected:
                raise ValueError("SPY root/product semantics conflict")
            if label == "Root Ticker Symbol" and cells[0].count("SPY") != 1:
                raise ValueError("SPY option root appears in multiple product columns")
        theta = Tables()
        theta.feed(bodies["theta_contract"].decode("utf-8"))
        text = " ".join(" ".join(theta.text).split())
        if ("/v3/option/history/eod" not in text or
                "symbol Required - The stock or index symbol, or underlying symbol for options. Type: string" not in text):
            raise ValueError("Theta v3 symbol contract unavailable")
    except (UnicodeError, ValueError, TypeError, csv.Error) as exc:
        raise IdentityError("option-root source semantics invalid") from exc

    direct = prepare_direct_registrant(symbol="SPY", response_body=bodies["registrant"],
        capture=sources["registrant"]["capture"], listing_body=sources["listing_body"],
        listing_receipt_body=sources["listing_receipt_body"], decision_at=decision_at)
    registrant = direct["registrant"]
    if (registrant["cik"] != "0000884394" or registrant["title"] != "SPDR S&P 500 ETF TRUST"
            or registrant["observed_on"] != on.isoformat()
            or registrant["listing_key"] != "US-ARCX-SPY"):
        raise IdentityError("option-root canonical source identity conflicts")
    known = _reference_clock_iso(max(*clocks, _reference_clock_ns(registrant["known_at"])))
    end = on + timedelta(days=1)
    evidence = {"schema": "mastermind.spy_option_root_sources.v1", "vendor": "thetadata", "root": "SPY",
        "underlying_id": "SEC:US-ARCX-SPY", "valid_from": on.isoformat(), "valid_to": end.isoformat(),
        "known_at": known, "sources": observations, "listing": registrant,
        "scope": "source-specific SPY inference; observed day only; no live Theta or rights assertion",
        "limits": ["No verified Matrix session for this observed date; root lookup is identity preparation only",
                   "Consumption uses the Options root/Matrix path; ordinary us_equity excludes ARCX"]}
    body = (json.dumps(evidence, indent=2, sort_keys=True) + "\n").encode()
    sha = hashlib.sha256(body).hexdigest()
    seal = option_root_binding_sha256("thetadata", "SPY", "SEC:US-ARCX-SPY", on, end, known, sha)
    return AliasRow("thetadata", "SPY", "SEC:US-ARCX-SPY", on, end, known, sha, seal,
                    alias_kind="occ_root"), evidence


def admit_spy_option_root(sources: dict, master_rows: list[dict], *, decision_at: str):
    """Prepare against exactly one existing active canonical target, before writes."""
    row, evidence = prepare_spy_option_root(sources, decision_at=decision_at)
    matches = [r for r in master_rows if r.get("security_id") == row.security_id]
    if len(matches) != 1:
        raise IdentityError("option underlying canonical target missing or duplicated")
    master = matches[0]
    if (master.get("security_state") is not None or master.get("superseded_by") is not None
            or [master.get(k) for k in ("listing_key", "country", "mic", "inception_code")] !=
               ["US-ARCX-SPY", "US", "ARCX", "SPY"]):
        raise IdentityError("option underlying is inactive or conflicting")
    def stored_clock(name):
        # The existing writer reader returns ISO strings from typed UTC Parquet.
        try:
            value = datetime.fromisoformat(str(master.get(name)).replace("Z", "+00:00"))
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return _reference_clock_ns(value.isoformat())
        except (ValueError, TypeError) as exc:
            raise IdentityError("invalid canonical target clock") from exc
    effective, ingested = stored_clock("effective_at"), stored_clock("ingested_at")
    if not 0 < effective <= ingested <= _reference_clock_ns(decision_at) or _reference_clock_iso(effective)[:10] > str(row.valid_from):
        raise IdentityError("option underlying canonical clocks conflict")
    # Seal the exact canonical record fields used for admission. Consumers also
    # bind the independently captured master bytes and their availability clock.
    evidence["canonical_target"] = {key: master.get(key) for key in MASTER_COLUMNS}
    body = (json.dumps(evidence, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    digest = hashlib.sha256(body).hexdigest()
    from lib.dataos.identity import option_root_binding_sha256
    seal = option_root_binding_sha256(row.vendor, row.vendor_symbol, row.security_id,
        row.valid_from, row.valid_to, row.known_at, digest)
    return AliasRow(row.vendor, row.vendor_symbol, row.security_id, row.valid_from, row.valid_to,
                    row.known_at, digest, seal, alias_kind="occ_root"), evidence


def read_spy_option_root_input(path: Path) -> dict:
    """Read the explicit local source bundle with the incumbent bounded reader."""
    from lib.symbol_directory_receipts import ReceiptValidationError, _read_regular_file

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate source manifest key")
            result[key] = value
        return result

    def read(name, limit):
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", name):
            raise ValueError("source must be a sibling filename")
        return _read_regular_file(path.parent / name, label="option-root source", limit=limit)

    try:
        raw = _read_regular_file(path, label="option-root manifest", limit=512 * 1024)
        manifest = json.loads(raw, object_pairs_hook=pairs,
                              parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
        roles = {"cboe_reference", "cboe_product", "theta_contract", "registrant"}
        if (type(manifest) is not dict or set(manifest) != {"schema", "sources"}
                or manifest["schema"] != "mastermind.spy_option_root_input.v1"
                or type(manifest["sources"]) is not dict
                or set(manifest["sources"]) != roles | {"listing_body", "listing_receipt_body"}):
            raise ValueError("invalid option-root manifest")
        sources = manifest["sources"]
        for role in roles:
            if type(sources[role]) is not dict or set(sources[role]) != {"body", "capture"}:
                raise ValueError("invalid option-root source")
            sources[role]["body"] = read(sources[role]["body"], _REFERENCE_MAX_BYTES)
        sources["listing_body"] = read(sources["listing_body"], 8 * 1024 * 1024)
        sources["listing_receipt_body"] = read(sources["listing_receipt_body"], 512 * 1024)
        return sources
    except (OSError, ValueError, TypeError, RecursionError, ReceiptValidationError) as exc:
        raise IdentityError("invalid option-root input files") from exc


def _spy_option_root_state(out_dir: Path, sources: dict | None, master_rows: list[dict], now: str):
    """Retain one bounded admission in the existing writer receipt, without replay."""
    previous = (_reference_json(out_dir / RECEIPT_NAME)[0].get("spy_option_root")
                if (out_dir / RECEIPT_NAME).exists() else None)
    if sources is not None and previous is not None:
        raise IdentityError("SPY option-root admission already retained; no replay")
    if sources is not None:
        row, evidence = admit_spy_option_root(sources, master_rows, decision_at=now + "Z")
        return evidence, [row]
    if previous is not None:
        if (type(previous) is not dict or previous.get("schema") != "mastermind.spy_option_root_sources.v1"
                or previous.get("vendor") != "thetadata" or previous.get("root") != "SPY"
                or previous.get("underlying_id") != "SEC:US-ARCX-SPY"):
            raise IdentityError("invalid retained SPY root evidence")
        # Its sealed alias binds the whole retained document below. No source
        # observation is resubmitted and its historical clock is never refreshed.
        if _reference_clock_ns(previous.get("known_at")) > _reference_clock_ns(now + "Z"):
            raise IdentityError("retained SPY source evidence is not yet known")
    return previous, []


def _validate_spy_option_root_retention(evidence: dict | None, alias_rows: list[dict], now: str):
    roots = [r for r in alias_rows if r.get("alias_kind") == "occ_root"
             and r["vendor"] == "thetadata" and r["vendor_symbol"] == "SPY"]
    if evidence is None:
        if roots:
            raise IdentityError("SPY root lacks its retained source evidence")
        return
    try:
        start, end = date.fromisoformat(evidence["valid_from"]), date.fromisoformat(evidence["valid_to"])
        body = (json.dumps(evidence, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
        table = VendorAliasTable.from_records(roots)
        binding = table.resolve_option_underlying("thetadata", "SPY", start,
                    decision_at=now + "Z", evidence_bytes=body)
        if (len(roots) != 1 or end != start + timedelta(days=1) or binding is None
                or binding.security_id != evidence["underlying_id"]
                or binding.valid_to != end or binding.known_at.isoformat() != evidence["known_at"]):
            raise IdentityError("retained SPY source/alias mismatch")
    except (KeyError, ValueError, TypeError, OverflowError) as exc:
        raise IdentityError("invalid retained SPY root binding") from exc


def build(out_dir: Path, dry_run: bool = False, allow_missing_evidence: bool = False,
          reference_evidence_path: Path | None = None,
          direct_registrant_inputs: tuple[dict, ...] | list[dict] = (),
          spy_option_root_input: dict | None = None) -> dict:
    """Preserve the existing API; serialize all actual local writer effects."""
    kwargs = dict(dry_run=dry_run, allow_missing_evidence=allow_missing_evidence,
                  reference_evidence_path=reference_evidence_path,
                  direct_registrant_inputs=direct_registrant_inputs,
                  spy_option_root_input=spy_option_root_input)
    if dry_run:
        return _build_reference_unlocked(out_dir, **kwargs)
    with _reference_writer_scope(out_dir):
        return _build_reference_unlocked(out_dir, **kwargs)


def _build_reference_unlocked(out_dir: Path, dry_run: bool = False,
          allow_missing_evidence: bool = False,
          reference_evidence_path: Path | None = None,
          direct_registrant_inputs: tuple[dict, ...] | list[dict] = (),
          spy_option_root_input: dict | None = None) -> dict:
    """Do the whole build and return the receipt payload (written unless ``dry_run``).

    ``allow_missing_evidence`` (V4-D2B1 FIX 2 / B2 manual-path hardening): a missing or
    empty ``CIK_MAP_DIR`` — no weekly evidence snapshot has ever landed — refuses with
    :class:`IdentityError` UNLESS this is set.  Without this guard, a manual run on a
    bare checkout (no ``data/symbol_directory/cik_map/`` at all) would silently mint
    EVERY row ``NO_ISSUER_EVIDENCE``, which is exactly the false-freshness escape §7
    law (a) already closes for the nightly seam — the CLI path needed the same fence,
    because a human blind to the missing rail could commit that output as if it were a
    normal build.  Passing this flag is an explicit, printed (see :func:`main`)
    admission that no CIK evidence exists yet — the correct state on a genuinely bare
    checkout before the first weekly map lands.
    """
    # Protect native publication/history BEFORE any input reads or writes.
    # An older builder cannot safely produce a new generation after native
    # history appears, even when its ordinary data sources have advanced.
    _assert_no_unpreserved_native_generation(out_dir)
    if spy_option_root_input is not None and (reference_evidence_path is not None or direct_registrant_inputs):
        raise IdentityError("option-root intake cannot combine with security admission")
    now = _iso_now()
    direct_state, direct_resolutions = _direct_registrant_state(out_dir, direct_registrant_inputs, now)
    direct_keys = frozenset(direct_state["observations"]) if direct_state else frozenset()
    reference = _load_reference_input(out_dir, reference_evidence_path)
    for symbol, observation in (direct_state["observations"].items() if direct_state else ()):
        if observation["status"] != "PENDING" or reference is None:
            continue
        prior = reference["probes"].get(symbol)
        if prior is not None and prior["status"] == "EVIDENCE_READY":
            raise IdentityError("direct intake cannot supply identity to an unsettled older reference")
        if prior is not None and _reference_clock_ns(observation["known_at"]) <= _reference_clock_ns(prior["known_at"]):
            raise IdentityError("direct intake must be newer than the retained reference disposition")
    reference_keys = frozenset(
        symbol for symbol, row in (reference["probes"].items() if reference else ())
        if row["status"] == "EVIDENCE_READY"
    )
    reference_only_keys = (frozenset({"SPY", "QQQ", "SMH"}) if reference else frozenset()) | direct_keys
    universe = load_universe()
    delisted = load_delisted()
    directory, directory_flags, snapshot_date, snapshot_path = load_directory()
    for incoming in direct_resolutions:
        observation = direct_state["observations"][incoming.key]
        if (observation["observed_on"] != snapshot_date or snapshot_path is None
                or _current_direct_resolution(incoming.key, observation, directory,
                                               directory_flags, delisted, snapshot_date) != incoming):
            raise IdentityError("direct registrant does not bind the current listing rail")
        from lib.symbol_directory_receipts import ReceiptValidationError, _read_regular_file
        try:
            current_bytes = _read_regular_file(snapshot_path, label="current listing", limit=8 * 1024 * 1024)
        except (OSError, ReceiptValidationError) as exc:
            raise IdentityError("current listing snapshot unavailable") from exc
        if hashlib.sha256(current_bytes).hexdigest() != observation["listing_snapshot_sha256"]:
            raise IdentityError("direct registrant does not bind the current listing bytes")
    fixups, migrations = load_config_maps()
    cik_map, cik_snapshot_date, cik_map_path, ambiguous_tickers = load_cik_map()
    if cik_map_path is None and not allow_missing_evidence:
        raise IdentityError(
            "data/symbol_directory/cik_map has no snapshot — refusing to mint issuer "
            "evidence blind (every row would silently become NO_ISSUER_EVIDENCE). "
            "Pass allow_missing_evidence=True (CLI: --allow-missing-evidence) to build "
            "anyway, e.g. on a bare checkout before the first weekly CIK map lands."
        )

    # ETF trust CIKs are not an admitted ETF issuer grouping. This reference lane
    # must not populate or merge their issuer axis, including on later reruns.
    # Compare independent evidence BEFORE removing ETF keys from the issuer map.
    for symbol, observation in (direct_state["observations"].items() if direct_state else ()):
        if observation["status"] not in {"PENDING", "BOUND"}:
            continue
        ordinary = cik_map.get(symbol)
        if symbol in ambiguous_tickers or (ordinary is not None and ordinary[0] != observation["cik"]):
            raise IdentityError("direct registrant conflicts with ordinary CIK evidence")
    cik_map = {k: v for k, v in cik_map.items() if k not in reference_only_keys}
    master_path = out_dir / MASTER_NAME
    aliases_path = out_dir / ALIASES_NAME
    issuer_master_path = out_dir / ISSUER_MASTER_NAME
    issuer_migrations_path = out_dir / ISSUER_MIGRATIONS_NAME
    security_migrations_path = out_dir / SECURITY_MIGRATIONS_NAME

    seed_notes = unmodelled_renames(fixups, migrations)

    # V4-D2B2-CN-HK: split the committed master BEFORE it reaches `mint_master_rows`.
    # That function's `_compute_lost` (the pending-transition fence, V4-D2B1-R1 §5)
    # treats every EXISTING active row not re-derived by a US `resolutions` entry as
    # "lost" — correct for the US-only universe it was built for, but a CN/HK row is
    # NEVER re-derived by a US resolution (there is no such thing), so feeding it
    # `existing` rows from other markets would flag the ENTIRE CN/HK population as
    # spuriously "lost" on every run after the first (VERIFIED while building this
    # stage: a second run printed a 1,131-symbol `listing_continuity` ::warning with
    # zero genuine US losses).  CN/HK rows are carried past this US-only pipeline
    # unmodified and re-attached in :func:`mint_cn_hk_rows` below, which has its own
    # market-scoped mint-once law.  V4-D2B2-US reuses this SAME split (see below) to
    # compute the GMI-US admission target set BEFORE `resolve_universe` runs.
    existing_master_rows = _read_existing(
        master_path, MASTER_COLUMNS, MASTER_DTYPES,
        allow_missing=ISSUER_AXIS_COLUMNS | SECURITY_AXIS_COLUMNS,
    )
    spy_root_evidence, spy_root_aliases = _spy_option_root_state(
        out_dir, spy_option_root_input, existing_master_rows, now)
    if spy_option_root_input is not None:
        observed = spy_root_evidence["listing"]
        if (snapshot_date != observed["observed_on"] or snapshot_path is None
                or _current_direct_resolution("SPY", observed, directory, directory_flags,
                                              delisted, snapshot_date) is None
                or hashlib.sha256(spy_option_root_input["listing_body"]).hexdigest() != observed["listing_snapshot_sha256"]):
            raise IdentityError("option-root evidence does not bind the current listing")
        from lib.symbol_directory_receipts import ReceiptValidationError, _read_regular_file
        try:
            current_listing = _read_regular_file(snapshot_path, label="current listing", limit=8 * 1024 * 1024)
        except (OSError, ReceiptValidationError) as exc:
            raise IdentityError("current listing unavailable") from exc
        if current_listing != spy_option_root_input["listing_body"]:
            raise IdentityError("option-root evidence does not bind the current listing bytes")
    existing_us_rows = [r for r in existing_master_rows if r.get("country") == "US"]
    existing_cn_hk_rows = [r for r in existing_master_rows if r.get("country") in ("CN", "HK")]
    direct_resolutions += _retained_direct_resolutions(
        direct_state, existing_master_rows, directory=directory, directory_flags=directory_flags,
        delisted=delisted, snapshot_date=snapshot_date)
    direct_resolution_keys = frozenset(r.key for r in direct_resolutions)

    # ── V4-D2B2-US — GMI seed intake + full-population admission accounting ────────
    # AMENDMENT §1 (post-review fix pass) — R1 (blocker), R2, R3, R5, R6, R11.
    # `load_gmi_us_seeds()` is upstream graph truth (never the derived sidecar, §2.1).
    # `legacy_keys`/`_original_universe_len` are captured BEFORE the merge below so
    # the pre-existing `coverage` receipt block (DOS-1.1's original curated-universe
    # acceptance bullet) AND `seed_counts.universe_keys` (R11) stay scoped to
    # exactly the curated 710-key set they always were — the GMI expansion must not
    # silently inflate a report a downstream reader already interprets as "the
    # curated breadth/basket universe" (§9 item 15).
    legacy_keys = frozenset(universe) | frozenset(delisted)
    _original_universe_len = len(universe)
    gmi_us_seeds = load_gmi_us_seeds()
    gmi_us_seed_codes = frozenset(s["symbol"] for s in gmi_us_seeds)
    _identity_exception_keys = frozenset(DEFERRED_IDENTITY_KEYS) | frozenset(
        DISCLOSED_IDENTITY_EXCEPTIONS
    )
    gmi_us_identity_exception_excluded = sorted(
        gmi_us_seed_codes & _identity_exception_keys
    )
    # R2 — `target_n` is the FULL GMI-U.S. company population net of ONLY the
    # registered identity exceptions: the true `china_hk_admission` mirror.  It
    # deliberately does NOT subtract legacy-curated overlap (708 of the 710 legacy
    # keys are ALSO graph nodes) — the accounting must be able to see a future
    # LOST US row re-enter as a refusal, which a legacy-scoped target set could
    # never show.
    gmi_us_all_targets = frozenset(gmi_us_seed_codes - _identity_exception_keys)
    # R1 (BLOCKER FIX) — the §3/§4 eligibility+CIK gate applies ONLY to a GMI
    # target that is NOT ALSO a legacy-curated key: legacy mint law is untouched,
    # regardless of master state.  The v1 gate's "already resolved, exclude from
    # gating" heuristic was measurably wrong — ETHA/IBIT are curated seeds AND
    # ETFs AND already-committed rows, and a from-EMPTY rebuild (no pre-run master
    # to match against) wrongly refused them, along with AEP/CTRA/EQR/FI/FISV.
    gmi_us_only_targets = frozenset(gmi_us_all_targets - legacy_keys)
    # Every GMI-US target — legacy-overlapping ones too, merging an already-legacy
    # key is a harmless no-op via `setdefault` — is merged into `universe`
    # (key-level dedup, §2.1) so it flows through the EXISTING
    # resolve_universe()/mint_master_rows() pipeline unmodified — no parallel
    # resolution logic, no second mint path (§2.3).  An identity-exception code
    # (B) is never merged — "not targets and not touched" (§2.2) means it must
    # never even reach `resolve_universe`.
    for _code in sorted(gmi_us_all_targets):
        _row = universe.setdefault(_code, {"sources": [], "first_seen": None})
        if "gmi_us_seed" not in _row["sources"]:
            _row["sources"].append("gmi_us_seed")

    for code in sorted(reference_keys):
        row = universe.setdefault(code, {"sources": [], "first_seen": None})
        if "prospective_reference_probe" not in row["sources"]:
            row["sources"].append("prospective_reference_probe")
        if code in reference_only_keys:
            row["first_seen"] = date.fromisoformat(reference["input"]["probes"][code]["requested_date"])
    reference_directory = dict(directory)
    for code in reference_keys:
        reference_directory[code] = REFERENCE_PROBES[code][0]
    resolutions = resolve_universe(universe, delisted, reference_directory, snapshot_date,
                                   reference_probe_keys=reference_keys | direct_resolution_keys)
    for incoming in direct_resolutions:
        conflicts = [r for r in resolutions if r.key == incoming.key and r.listing_key != incoming.listing_key]
        if conflicts:
            raise IdentityError("direct registrant conflicts with the current listing resolution")
    resolutions = [r for r in resolutions if r.key not in direct_resolution_keys] + direct_resolutions
    legacy_resolutions = [r for r in resolutions if r.key in legacy_keys]
    resolved = [r for r in legacy_resolutions if r.listing_key is not None]
    unresolved = [r for r in legacy_resolutions if r.listing_key is None]

    # R3 — generalized duplicate-claim collapse across ALL rendered listing keys,
    # not only ones already active pre-run (the reviewer's NEWA/NEWAOLD
    # counterexample: two codes sharing a root can ALSO collide on a brand-NEW
    # key).  Exactly one claimant survives into the mint/alias pipeline; every
    # other is a typed, disclosed exclusion (R2's third accounting bucket) —
    # `build()` is now structurally UNABLE to hand `VendorAliasTable.from_records`
    # duplicate coverage from this path (see :func:`_collapse_duplicate_claims`).
    resolutions, duplicate_claim_disclosures = _collapse_duplicate_claims(
        resolutions, legacy_keys
    )
    disclosed_exclusion_keys = frozenset(
        d["symbol"] for d in duplicate_claim_disclosures
    )

    (master_rows, ids, notes, resurrection_refusals, pending_transition_refusals,
     lost_rows, exception_lost_rows, gmi_us_eligibility_refusals) = mint_master_rows(
        resolutions,
        existing_us_rows,
        now,
        cik_map=cik_map,
        delisted=delisted,
        snapshot_date=cik_snapshot_date,
        gmi_admission_targets=gmi_us_only_targets - (reference_only_keys & (reference_keys | direct_resolution_keys)),
        directory_flags=directory_flags,
        ambiguous_tickers=ambiguous_tickers,
        direct_registrant_inputs=direct_registrant_inputs,
    )

    # ── V4-D2B2-US — complete per-target accounting (R2, corrected R13) ────────────
    # Every one of the `target_n` GMI targets lands in EXACTLY ONE of three
    # buckets: resolved (`ids` carries its key OR an ACTIVE master row already
    # covers its identity, R13), a disclosed duplicate-claim exclusion (R3,
    # computed above), or a single named typed refusal — never two, never zero.
    # `resolved_total + refused_this_run + len(disclosed_exclusions) ==
    # target_n` is enforced fail-closed, in-build, below.
    resolutions_by_key = {r.key: r for r in resolutions}
    _master_rows_by_security_for_gmi = {r["security_id"]: r for r in master_rows}
    # AMENDMENT R13 — a target is RESOLVED when an ACTIVE master row covers its
    # identity post-run (the sidecar's own rule-5 answer: does this code's OWN
    # pure rename-chain root, :func:`_inception_code` with no directory context,
    # match an active row's inception_code?) — NOT only when THIS run's rail
    # join re-derived it via `ids`.  A rail that cannot currently re-derive an
    # EXISTING row (WBS: a pre-existing, unrelated symbol-directory staleness
    # gap; SATS: the old pre-rename ticker, no longer listed under that name —
    # both already disclosed via `listing_continuity`) is a STALENESS fact,
    # never a refusal: the identity is not missing, only this run's evidence
    # for THIS SPELLING is quiet.  Named in `resolved_not_rederivable` so a
    # receipt reader can see exactly which admissions relied on this path.
    _active_us_security_by_root: dict[str, str] = {
        str(r.get("inception_code") or "").strip().upper(): r["security_id"]
        for r in master_rows
        if r.get("country") == "US" and not r.get("security_state")
    }
    us_gmi_resolved_not_rederivable: list[dict] = []
    _resolved_not_rederivable_codes: set[str] = set()
    us_gmi_refusals_by_code: dict[str, dict] = {}
    for _code in gmi_us_all_targets:
        if _code in reference_only_keys:
            us_gmi_refusals_by_code[_code] = {
                "code": "structural_etf",
                "reason": "reference-only ETF identity is not GMI common-equity admission",
            }
            continue
        if _code in disclosed_exclusion_keys or _code in ids:
            continue
        _covering_sec = _active_us_security_by_root.get(_inception_code(_code, None))
        if _covering_sec is not None:
            us_gmi_resolved_not_rederivable.append(
                {"code": _code, "security_id": _covering_sec}
            )
            _resolved_not_rederivable_codes.add(_code)
            continue
        _res = resolutions_by_key.get(_code)
        if _res is not None and _res.listing_key is None:
            us_gmi_refusals_by_code[_code] = _gmi_us_unresolved_refusal(_res, cik_map)
    for _rr in resurrection_refusals:
        if _rr["key"] in gmi_us_all_targets and _rr["key"] not in disclosed_exclusion_keys:
            us_gmi_refusals_by_code[_rr["key"]] = {
                "code": "resurrection_refusal", "reason": _rr["reason"],
            }
    for _pr in pending_transition_refusals:
        if (_pr["symbol"] in gmi_us_all_targets
                and _pr["symbol"] not in disclosed_exclusion_keys):
            us_gmi_refusals_by_code[_pr["symbol"]] = {
                "code": "pending_transition_fence", "reason": _pr["reason"],
            }
    for _er in gmi_us_eligibility_refusals:
        us_gmi_refusals_by_code[_er["symbol"]] = {
            "code": _er["code"], "reason": _er["reason"],
        }
    # A code resolved via the fence/eligibility/resurrection loops above is, by
    # construction, never ALSO a resolved_not_rederivable code (those loops only
    # ever fire for a resolution whose OWN listing_key resolved, which — had its
    # root matched an active row — would already be `ids`-resolved via the
    # ordinary `stored is not None` join, never reaching a fence/eligibility
    # decision at all). Defensive: never let a later refusal overwrite an
    # earlier resolved_not_rederivable classification.
    for _dup in list(us_gmi_refusals_by_code):
        if _dup in _resolved_not_rederivable_codes:
            del us_gmi_refusals_by_code[_dup]

    us_gmi_resolved_codes = sorted(
        (c for c in gmi_us_all_targets if c not in reference_only_keys
         and (c in ids or c in _resolved_not_rederivable_codes))
    )
    us_gmi_missing = sorted(
        c for c in gmi_us_all_targets
        if c not in ids and c not in disclosed_exclusion_keys
        and c not in _resolved_not_rederivable_codes
        and c not in us_gmi_refusals_by_code
    )
    if us_gmi_missing:
        raise IdentityError(
            "V4-D2B2-US accounting invariant violated (R2): "
            f"{len(us_gmi_missing)} GMI target(s) landed in none of resolved / "
            f"disclosed-exclusion / refused — first 10: {us_gmi_missing[:10]}"
        )
    if (len(us_gmi_resolved_codes) + len(us_gmi_refusals_by_code)
            + len(disclosed_exclusion_keys)) != len(gmi_us_all_targets):
        raise IdentityError(
            "V4-D2B2-US accounting invariant violated (R2): "
            f"resolved_total ({len(us_gmi_resolved_codes)}) + refusals "
            f"({len(us_gmi_refusals_by_code)}) + disclosed_exclusions "
            f"({len(disclosed_exclusion_keys)}) != target_n "
            f"({len(gmi_us_all_targets)})"
        )
    us_gmi_resolved_this_run = sum(
        1 for c in us_gmi_resolved_codes
        if c in ids
        and not _master_rows_by_security_for_gmi.get(ids[c], {}).get("_existed_before")
    )
    # R5 disclosure — a GMI-only target minted THIS run via the exit-ledger path
    # (`exchange_symbol` is None on its resolution) never went through the
    # directory structural-flag check at all: eligibility-EXEMPT BY LAW, named
    # here so a receipt reader can see which admissions relied on the exemption.
    us_gmi_exit_ledger_exempt = sorted(
        c for c in gmi_us_only_targets
        if c in ids and c not in reference_only_keys
        and not _master_rows_by_security_for_gmi.get(ids[c], {}).get("_existed_before")
        and (_er2 := resolutions_by_key.get(c)) is not None
        and _er2.exchange_symbol is None
    )
    us_gmi_disclosed_exclusions = [
        {
            "symbol": d["symbol"],
            "listing_key": d["listing_key"],
            "code": "duplicate_claim_collapsed",
            "winning_symbol": d["winning_symbol"],
            "winning_security_id": ids.get(d["winning_symbol"]),
            "reason": d["reason"],
        }
        for d in sorted(duplicate_claim_disclosures, key=lambda d: d["symbol"])
    ]
    us_gmi_resolved_not_rederivable = sorted(
        us_gmi_resolved_not_rederivable, key=lambda d: d["code"]
    )

    # V4-D2B2-CN-HK — a SEPARATE, additive admission stage (see the module block
    # above :func:`mint_cn_hk_rows`), folded into ``master_rows`` BEFORE the security-
    # supersession / issuer-correction passes below so a freshly-minted CN/HK row is
    # processed by the SAME idempotent pipeline as every US row from that point on
    # (harmlessly: the US-only ``SECURITY_SUPERSESSIONS``/``RENAME_EVENTS`` registries
    # never match a numeric CN/HK inception code, and the US CIK map never carries
    # one, so these rows settle at ``issuer_state=NO_ISSUER_EVIDENCE`` exactly as
    # designed).
    cn_hk_seeds = load_cn_hk_seeds()
    cninfo_evidence, cninfo_newest = load_cninfo_evidence()
    hk_evidence, hk_newest = load_hk_shorts_evidence()
    master_rows, cn_hk_alias_rows, cn_hk_coverage = mint_cn_hk_rows(
        master_rows + existing_cn_hk_rows, cn_hk_seeds, cninfo_evidence, hk_evidence, now,
    )

    # V4-D2B1-R1 §3 — correct any security minted as an independent row for a rename's
    # NEW symbol before this builder modelled the rename, BEFORE the issuer era stage
    # runs (so a freshly-tombstoned row is excluded from re-examination this same run,
    # §3.3 / H4).
    master_rows, freshly_superseded = apply_security_supersession(master_rows, ids)
    superseded_ids = frozenset(r["security_id"] for r in master_rows if r.get("security_state"))
    # AMENDMENT ruling 4 (M3) — a rename-implied duplicate NOT covered by an exact
    # SECURITY_SUPERSESSIONS entry is disclosed, never auto-corrected.
    unregistered_rename_duplicates = detect_unregistered_rename_duplicates(master_rows)
    if unregistered_rename_duplicates:
        print(
            f"::warning title=security-master-unregistered-rename-duplicate::"
            f"{len(unregistered_rename_duplicates)} active row(s) share a RenameEvent "
            ".new inception code with no exact-listing-key SECURITY_SUPERSESSIONS "
            "entry naming them — disclosed, never auto-corrected: "
            f"{', '.join(sorted(r['security_id'] for r in unregistered_rename_duplicates))}",
            flush=True,
        )

    master_rows, fresh_issuer_migrations = apply_issuer_correction(
        master_rows, cik_map, cik_snapshot_date, now, ambiguous_tickers=ambiguous_tickers
    )

    native_aliases = _reference_aliases(reference, ids, master_rows,
                                        pending_transition_refusals, resurrection_refusals)
    if direct_state is not None:
        for symbol, observed in direct_state["observations"].items():
            if observed["status"] != "PENDING":
                continue
            matches = [r for r in master_rows if r["security_id"] == ids.get(symbol)
                       and r["listing_key"] == observed["listing_key"] and not r.get("security_state")]
            if len(matches) == 1:
                observed.update(status="BOUND", security_id=matches[0]["security_id"])
            else:
                causes = [r for r in pending_transition_refusals + resurrection_refusals
                          if r.get("symbol") == symbol]
                if not causes:
                    causes = [{"symbol": symbol, "reason": "canonical writer returned no unique active identity"}]
                observed.update(status="REFUSED", code="canonical_identity_refused", owner_refusals=causes)
        direct_state["sha256"] = _reference_digest(direct_state)
    fresh_aliases = build_alias_rows(
        [r for r in resolutions if r.key not in reference_only_keys], ids
    ) + cn_hk_alias_rows + native_aliases + spy_root_aliases
    existing_aliases, alias_prunes = _prune_stale_aliases(
        _read_existing(aliases_path, ALIAS_COLUMNS, ALIAS_DTYPES,
                       allow_missing=OPTIONAL_ALIAS_COLUMNS),
        fresh_aliases, superseded_ids,
    )
    # AMENDMENT ruling 6 (M5) / AMENDMENT §2 — every prune is receipted + a
    # ::warning, never a silent drop; the two lawful deletion classes get their OWN
    # named annotation so the nightly log tells the operator WHICH kind fired.
    tombstone_prunes = [r for r in alias_prunes if r.get("prune_class") == "superseded_tombstone"]
    refinement_prunes = [r for r in alias_prunes if r.get("prune_class") == "same_id_refinement"]
    if tombstone_prunes:
        print(
            f"::warning title=security-master-vendor-alias-prune::{len(tombstone_prunes)} "
            "committed vendor alias row(s) pruned (pointed at a security_id this "
            "run tombstoned): "
            + ", ".join(
                f"{r['vendor']}/{r['vendor_symbol']}->{r['security_id']}"
                for r in tombstone_prunes
            ),
            flush=True,
        )
    if refinement_prunes:
        print(
            f"::warning title=security-master-vendor-alias-refinement-prune::"
            f"{len(refinement_prunes)} committed vendor alias row(s) pruned (a "
            "fresh DATED same-id family refined a committed open-bounded row, "
            "AMENDMENT §2 carve-out): "
            + ", ".join(
                f"{r['vendor']}/{r['vendor_symbol']}->{r['security_id']}"
                for r in refinement_prunes
            ),
            flush=True,
        )
    alias_rows = merge_alias_rows(fresh_aliases, existing_aliases, now)

    issuer_migration_rows = _merge_issuer_migrations(
        _read_existing(issuer_migrations_path, ISSUER_MIGRATIONS_COLUMNS,
                       ISSUER_MIGRATIONS_DTYPES),
        fresh_issuer_migrations,
    )
    security_migration_rows = _merge_security_migrations(
        _read_existing(security_migrations_path, SECURITY_MIGRATIONS_COLUMNS,
                       SECURITY_MIGRATIONS_DTYPES),
        build_security_migration_rows(freshly_superseded, now),
    )
    cik_to_title = {cik: title for cik, title in cik_map.values()}
    issuer_master_rows = _build_issuer_master_rows(master_rows, cik_to_title)

    # THE ONLY READER, used as the validator: an ambiguous table must fail HERE, at
    # write time, not in whatever consumer first asks it a question.
    table = VendorAliasTable.from_records(alias_rows)

    # V4-D2B1-R1 §5.4 — the standing pending-transition instrument: a non-empty
    # `lost` set is a visible ::warning on EVERY build, not only the one that first
    # produced it, so a killed or missing signal can never again be silent for a week.
    if lost_rows:
        print(
            f"::warning title=security-master-listing-continuity::{len(lost_rows)} "
            "committed row(s) unaccounted for this build: "
            f"{', '.join(sorted(_current_symbol_of_row(r) for r in lost_rows))}",
            flush=True,
        )

    receipt = {
        "dataset_ids": [
            "reference.security_master", "reference.vendor_aliases",
            "reference.issuer_master", "reference.issuer_migrations",
            "reference.security_migrations",
        ],
        "producer": "scripts/build_security_master.py",
        "code_version": _git_sha(),
        "generated_at": now,
        # V4-D2B1 FIX 2 (B2 n2): every identity rail is ALWAYS named here, even when
        # absent (value null) — a dropped key silently reads as "not an input", which
        # is exactly the shape that let the listing-snapshots rail go uncovered by the
        # nightly preflight (only the 5 seed files + the CIK rail were named/checked).
        # Keyed on the RAIL'S OWN DIRECTORY (stable across which file is newest), not
        # the newest file's path, so the key never depends on which snapshot exists.
        "inputs": {
            **{
                str(path.relative_to(ROOT)): _sha256(path)
                for path in (CONSTITUENTS, MIDCAP_CONSTITUENTS, SMALLCAP_CONSTITUENTS,
                            MEMBERSHIP, DELISTED_LEDGER, CONFIG_YML, TICKER_ALIASES_PY)
            },
            _relpath(SYMBOL_DIR_SNAPSHOTS): (
                _sha256(snapshot_path) if snapshot_path is not None else None
            ),
            _relpath(CIK_MAP_DIR): (
                _sha256(cik_map_path) if cik_map_path is not None else None
            ),
            # V4-D2B2-CN-HK — the target-population seed + the two primary-source
            # evidence inputs, named the same way every other rail is (present ->
            # hash, absent -> null, never a dropped key).
            **{
                str(path.relative_to(ROOT)): _sha256(path)
                for path in (THEME_GRAPH_NODES_PATH, CHINA_FILINGS_PATH,
                            HK_SHORTS_POSITIONS_PATH, HK_SHORTS_TURNOVER_PATH)
            },
        },
        "symbol_directory_snapshot": snapshot_date,
        "cik_map_snapshot": cik_snapshot_date,
        "row_counts": {
            "security_master": len(master_rows),
            "vendor_aliases": len(alias_rows),
            "vendor_alias_rows_readable": len(table.rows),
            "issuer_master": len(issuer_master_rows),
            "issuer_migrations": len(issuer_migration_rows),
            "security_migrations": len(security_migration_rows),
        },
        # AMENDMENT ruling 6 (M5) / AMENDMENT §2 — every committed vendor alias row
        # this run pruned, receipted rather than silently dropped: either it points
        # at a security_id this SAME run tombstoned (`prune_class="superseded_
        # tombstone"`) or a fresh DATED same-id family lawfully refined it
        # (`prune_class="same_id_refinement"`).
        "vendor_alias_prunes": [
            {
                "vendor": r["vendor"], "vendor_symbol": r["vendor_symbol"],
                "security_id": r["security_id"], "valid_from": r["valid_from"],
                "valid_to": r["valid_to"], "prune_class": r["prune_class"],
                "ingested_at": r["ingested_at"],
            }
            for r in sorted(alias_prunes, key=lambda r: (r["vendor"], r["vendor_symbol"]))
        ],
        # AMENDMENT ruling 4 (M3) — a rename-implied duplicate mint with no exact
        # SECURITY_SUPERSESSIONS registry entry naming it: disclosed, never executed.
        "unregistered_rename_duplicates": sorted(
            unregistered_rename_duplicates, key=lambda r: r["security_id"]
        ),
        "coverage": {
            "total": len(legacy_resolutions),
            "resolved": len(resolved),
            "unresolved": len(unresolved),
            "unresolved_names": [r.key for r in unresolved],
        },
        # V4-D2B1-R1 §5 — the general pending-transition fence, disclosed every build
        # (never merged/accumulated across runs — refusals are RE-EXAMINED every
        # build, §5.3, and clear naturally when evidence arrives).
        "pending_transition_refusals": pending_transition_refusals,
        # V4-D2B1-R1 §5.4, AMENDMENT ruling 3 (M1) — the standing "lost" census, by
        # current symbol name, PLUS registered-identity-exception losses as typed,
        # EXPLAINED entries (never silently dropped, unlike the fence-scoped
        # `lost_rows` these exceptions are excluded from). Post-repair this is
        # exactly ONE explained GOLD entry (the exception row's own current answer is
        # orphaned — nothing this build re-derives it — but it is quarantined at its
        # own layer, not a genuine loss the fence should ever gate on). The PLAIN
        # STRING half is empty after this repair (EQR heals via the rename chain, AVB
        # via the exit ledger, CTRA/TPH already exit-ledgered); a non-empty plain
        # entry on any FUTURE nightly is the visible ::warning above (exception
        # entries never re-trigger it — already alarmed via `identity_exceptions`).
        "listing_continuity": (
            sorted(_current_symbol_of_row(r) for r in lost_rows)
            + [
                {"code": _current_symbol_of_row(r), "explained": "identity_exception"}
                for r in sorted(exception_lost_rows, key=_current_symbol_of_row)
            ]
        ),
        # V4-D2B1-R1 §3.4/H8 — typed refusals for a resolution that hit a superseded
        # (tombstoned) listing key; never a silent resurrection.
        "resurrection_refusals": resurrection_refusals,
        # AMENDMENT R11 — `universe_keys` reverts to the legacy-curated count only
        # (captured BEFORE the D2B2-US merge as `_original_universe_len`); the GMI
        # population gets its OWN named field so no existing reader's meaning of
        # `universe_keys` changes.
        "seed_counts": {
            "universe_keys": _original_universe_len,
            "gmi_seed_keys": len(gmi_us_seed_codes),
            "delisted_keys": len(delisted),
            "directory_symbols": len(directory),
            "ticker_fixups": len(fixups),
            "ticker_key_migrations": len(migrations),
        },
        "rename_events": [
            {"old": e.old, "new": e.new, "on": e.on.isoformat(),
             "vendors": list(e.vendors), "evidence": e.evidence}
            for e in RENAME_EVENTS
        ],
        "undated_renames": [
            {"old": old, "new": new, "evidence": why} for old, new, why in UNDATED_RENAMES
        ],
        "identity_exceptions": [
            {
                "key": key,
                "status": "deferred_no_mint",
                **DEFERRED_IDENTITY_KEYS[key],
            }
            for key in sorted(DEFERRED_IDENTITY_KEYS)
        ] + [
            {
                "key": key,
                "status": "disclosed_existing_alias",
                **DISCLOSED_IDENTITY_EXCEPTIONS[key],
            }
            for key in sorted(DISCLOSED_IDENTITY_EXCEPTIONS)
        ],
        "notes": seed_notes + notes,
        # V4-D2B1 §12: authority is semantically DECOMPOSED — identity is canonical
        # for CURRENT exact issuer/security/listing identity (Sol's D2A ruling); the
        # spine never gates/ranks/trades on its own account. `consumers` names every
        # real reader so the next session does not have to re-discover D2A by grep.
        "authority": {
            "identity_authority": "canonical_exact_identity",
            "signal_authority": "none",
            "ranking_authority": "none",
            "trade_authority": "none",
            "consumers": ["gmi.identity_resolution/v1"],
        },
        "issuer": {
            "era": ERA_ISSUER_CORRECTION,
            "state_counts": _issuer_state_counts(master_rows),
            "multi_security_groups": _multi_security_issuer_groups(master_rows),
            "migrations_this_run": len(fresh_issuer_migrations),
            # V4-D2B1 FIX 9 (n3): the ALL-TIME count, alongside the per-run count —
            # "migrations_this_run: 0" alone reads as "no migrations ever happened",
            # which is false on every run after the era's first.
            "era_migrations_total": len(issuer_migration_rows),
            "evidence_snapshot": cik_snapshot_date,
        },
        # V4-D2B1-R1 §3 — the security-axis mirror of the "issuer" block above: one
        # correction era, ACTIVE/superseded split, this-run and all-time migration
        # counts.
        "security": {
            "era": ERA_SECURITY_SUPERSESSION,
            "state_counts": _security_state_counts(master_rows),
            "migrations_this_run": len(freshly_superseded),
            "era_migrations_total": len(security_migration_rows),
        },
        # V4-D2B2-CN-HK — complete accounting (frozen contract boundary 8: every
        # target finishes RESOLVED or a named typed refusal, no silent drop).
        # `target_n` is THIS RUN's own start-pin census (boundary 1) — the child's
        # target, never the historical 1,868-total observation. `resolved_total` is
        # the CUMULATIVE count of CN/HK rows now in the master (mint-once across
        # runs); `resolved_this_run`/`refused_this_run` are this build's own delta.
        "china_hk_admission": {
            "contract": "research/prophet_v4/d2/D2B2_CN_HK_FROZEN_CONTRACT_2026-08-20.md",
            "target_population_source": _relpath(THEME_GRAPH_NODES_PATH)
                + " (kind=company, market_scope in cn/hk)",
            "evidence_sources": {
                "cn": {
                    "dataset": _relpath(CHINA_FILINGS_PATH),
                    "provenance": "CNInfo (巨潮资讯网) SSE+SZSE disclosure metadata "
                                  "(collectors/china_filings.py)",
                    "newest_observation": cninfo_newest,
                },
                "hk": {
                    "dataset": f"{_relpath(HK_SHORTS_POSITIONS_PATH)} + "
                               f"{_relpath(HK_SHORTS_TURNOVER_PATH)}",
                    "provenance": "SFC official Short Position Reports + HKEX "
                                  "official turnover statistics "
                                  "(collectors/hk_shorts.py)",
                    "newest_observation": hk_newest,
                },
            },
            "target_n": cn_hk_coverage["target_n"],
            "resolved_this_run": cn_hk_coverage["resolved_this_run"],
            "refused_this_run": cn_hk_coverage["refused_this_run"],
            "resolved_total": {
                market: sum(
                    1 for r in master_rows
                    if r["country"] == country and not r.get("security_state")
                )
                for market, country in (("cn", "CN"), ("hk", "HK"))
            },
            "refusals_this_run": cn_hk_coverage["refusals_this_run"],
        },
        # V4-D2B2-US, AMENDMENT R2 — the TRUE `china_hk_admission` mirror: every one
        # of the `target_n` GMI-U.S. targets (the FULL population net of the
        # registered identity exceptions, legacy-overlap INCLUDED) finishes
        # resolved, a disclosed duplicate-claim exclusion (R3), or a single named
        # typed refusal.  `resolved_total + refused_this_run +
        # len(disclosed_exclusions) == target_n` is enforced ABOVE, fail-closed
        # (IdentityError), before this block is even assembled — a mismatch here
        # would mean the invariant check itself has a bug, not that this block may
        # disagree with it.  This is a STANDING partition: a future lost US row
        # re-enters as a refusal and the invariant still holds (R2).
        "us_gmi_admission": {
            "contract": "research/prophet_v4/d2/D2B2_US_FROZEN_CONTRACT_2026-08-21.md",
            "target_population_source": _relpath(THEME_GRAPH_NODES_PATH)
                + " (kind=company, market_scope=us)",
            "target_n": len(gmi_us_all_targets),
            "resolved_total": len(us_gmi_resolved_codes),
            "resolved_this_run": us_gmi_resolved_this_run,
            "refused_this_run": len(us_gmi_refusals_by_code),
            "refusals_this_run": [
                {"symbol": code, **us_gmi_refusals_by_code[code]}
                for code in sorted(us_gmi_refusals_by_code)
            ],
            "disclosed_exclusions": us_gmi_disclosed_exclusions,
            # AMENDMENT R13 — resolved targets whose IDENTITY is covered by an
            # ACTIVE master row post-run but whose OWN rail join could not
            # re-derive it THIS run (a staleness fact, already disclosed via
            # `listing_continuity` — never a refusal).
            "resolved_not_rederivable": us_gmi_resolved_not_rederivable,
            # AMENDMENT R5 — GMI-only targets minted this run via the exit-ledger
            # path, exempt BY LAW from the directory structural-flag check.
            "structural_check_exempt_exit_ledger": us_gmi_exit_ledger_exempt,
            "identity_exception_excluded": [
                {
                    "code": code,
                    "reason": (
                        DEFERRED_IDENTITY_KEYS.get(code)
                        or DISCLOSED_IDENTITY_EXCEPTIONS.get(code)
                        or {}
                    ).get("reason"),
                }
                for code in gmi_us_identity_exception_excluded
            ],
        },
    }

    if reference is not None:
        receipt["prospective_reference"] = reference
    elif any(r.get("vendor") == "polygon" for r in alias_rows):
        raise IdentityError("native aliases require retained prospective evidence")

    if direct_state is not None:
        receipt["direct_registrant_intake"] = direct_state
        # Historical admission is immutable; disclose this build's re-derivation separately.
        current_direct_ids = {r.key for r in direct_resolutions}
        receipt["direct_registrant_rederivation"] = {
            symbol: ("REFUSED" if row["status"] == "REFUSED" else
                     "RETIRED" if any(r["security_id"] == row.get("security_id") and r.get("security_state")
                                      for r in master_rows) else
                     "CURRENT" if symbol in current_direct_ids else "LISTING_UNAVAILABLE")
            for symbol, row in direct_state["observations"].items()
        }
    _validate_spy_option_root_retention(spy_root_evidence, alias_rows, now)
    if spy_root_evidence is not None:
        receipt["spy_option_root"] = spy_root_evidence
    if reference_evidence_path is not None or direct_registrant_inputs or spy_option_root_input is not None:
        def semantic(rows, columns):
            return sorted(_reference_digest({
                c: (int(row[c]) if c == "n_securities" and row.get(c) is not None else row.get(c))
                for c in columns
            }) for row in rows)
        old_by_id = {r["security_id"]: r for r in existing_master_rows}
        projected_existing = [r for r in master_rows if r["security_id"] in old_by_id]
        if semantic(projected_existing, MASTER_COLUMNS) != semantic(existing_master_rows, MASTER_COLUMNS):
            raise IdentityError("bounded reference intake would change an existing security row")
        extras = [r for r in master_rows if r["security_id"] not in old_by_id]
        if (spy_option_root_input is not None and extras) or any(r["inception_code"] not in reference_only_keys for r in extras):
            raise IdentityError("bounded reference intake would mint a non-probe security")
        old_aliases = _read_existing(aliases_path, ALIAS_COLUMNS, ALIAS_DTYPES,
                                     allow_missing=OPTIONAL_ALIAS_COLUMNS)
        old_native = [r for r in old_aliases if r["vendor"] == "polygon"]
        new_legacy = [r for r in alias_rows if r["vendor"] != "polygon"
                      and not (spy_option_root_input is not None and r.get("alias_kind") == "occ_root"
                               and r["vendor"] == "thetadata" and r["vendor_symbol"] == "SPY")]
        if spy_option_root_input is not None and len(alias_rows) != len(old_aliases) + 1:
            raise IdentityError("option-root intake must add exactly one new relation")
        old_legacy = [r for r in old_aliases if r["vendor"] != "polygon"]
        if semantic(new_legacy, ALIAS_COLUMNS) != semantic(old_legacy, ALIAS_COLUMNS):
            raise IdentityError("bounded reference intake would change non-native aliases")
        for old_native_row in old_native:
            if old_native_row not in alias_rows:
                raise IdentityError("bounded reference intake would replace a native alias")
        for path_, columns_, dtypes_, rows_ in (
            (issuer_master_path, ISSUER_MASTER_COLUMNS, ISSUER_MASTER_DTYPES, issuer_master_rows),
            (issuer_migrations_path, ISSUER_MIGRATIONS_COLUMNS, ISSUER_MIGRATIONS_DTYPES, issuer_migration_rows),
            (security_migrations_path, SECURITY_MIGRATIONS_COLUMNS, SECURITY_MIGRATIONS_DTYPES, security_migration_rows),
        ):
            if semantic(_read_existing(path_, columns_, dtypes_), columns_) != semantic(rows_, columns_):
                raise IdentityError("bounded reference intake would change issuer or migration rows")

    if not dry_run:
        # Recheck immediately before the first write: a native source owner may
        # have published history while this legacy builder computed its rows.
        # This is a narrow additional refusal, NOT an atomic writer lock.
        _assert_no_unpreserved_native_generation(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        _write_parquet(master_rows, MASTER_COLUMNS, master_path, MASTER_DTYPES)
        _write_parquet(alias_rows, ALIAS_COLUMNS, aliases_path, ALIAS_DTYPES)
        _write_parquet(issuer_master_rows, ISSUER_MASTER_COLUMNS, issuer_master_path,
                       ISSUER_MASTER_DTYPES)
        _write_parquet(issuer_migration_rows, ISSUER_MIGRATIONS_COLUMNS,
                       issuer_migrations_path, ISSUER_MIGRATIONS_DTYPES)
        _write_parquet(security_migration_rows, SECURITY_MIGRATIONS_COLUMNS,
                       security_migrations_path, SECURITY_MIGRATIONS_DTYPES)
        (out_dir / RECEIPT_NAME).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")

    receipt["_resolutions"] = resolutions  # in-process only; never serialized
    return receipt


# ── Nightly fail-closed refresh seam (V4-D2B1 §7) ──────────────────────────────
#: The artifacts a nightly refresh compares byte-for-byte to decide "did anything
#: actually change" (RECEIPT_NAME is handled separately — see :func:`run_nightly_refresh`).
_NIGHTLY_ARTIFACT_NAMES = (MASTER_NAME, ALIASES_NAME, ISSUER_MASTER_NAME, ISSUER_MIGRATIONS_NAME,
                           SECURITY_MIGRATIONS_NAME)

#: DSC falsifier escalation sidecar (AMENDMENT §3-adjacent, added 2026-08-29) — a
#: per-``out_dir`` streak of :class:`VendorAliasPruneConflict` nightly refusals with
#: no intervening SUCCESSFUL refresh (see :func:`run_nightly_refresh`'s handler for
#: the restart-on-different-conflict rule). Deliberately NOT in
#: ``_NIGHTLY_ARTIFACT_NAMES``: it is bookkeeping about refusals, not a produced
#: identity artifact, and must never be touched by :func:`_restore_artifacts`.
#: TWO counters live in this sidecar, both int-validated on every read (see
#: :func:`_valid_streak_count`):
#:
#: * ``consecutive`` / ``first_conflict_at`` — the MATCHING-TEXT streak: resets to
#:   1 (and ``first_conflict_at`` to now) whenever the fresh conflict's message
#:   text differs from the prior refusal's — a different conflict is a fresh clock,
#:   not a continuation of the old one.
#: * ``refusals_since_last_success`` / ``first_refusal_at`` — a MONOTONIC counter:
#:   incremented on EVERY :class:`VendorAliasPruneConflict` refusal regardless of
#:   whether the conflict text matches the prior one, and reset ONLY by
#:   :func:`_clear_prune_conflict_streak` (i.e. only a SUCCESSFUL refresh clears
#:   it). This exists because two or more DIFFERENT standing conflicts, each
#:   recurring in alternation (A, B, A, B, ...), would otherwise hold
#:   ``consecutive`` at 1 forever — genuinely wedged, but never escalating.
#:
#: PERSISTENCE (undeclared on purpose, like ``_receipt.json``): this sidecar rides
#: the SAME nightly data commit as every other ``out_dir`` artifact — ``daily.yml``'s
#: ``git add data/`` step commits it alongside ``_receipt.json``, which is likewise
#: not a ``config/dataset_registry.yml`` row (it is process bookkeeping, not a
#: dataset). No registry entry is added for it and it is never ``.gitignore``'d. If a
#: commit is ever lost or the sidecar otherwise fails to persist across nights, the
#: worst case is FAIL-DEGRADED, never fail-silent: BOTH counters simply restart at 1
#: (see :func:`_read_prune_conflict_streak` — missing/corrupt reads as "no prior
#: streak"), which only DELAYS the ``::error`` escalation by however many nights were
#: lost. The per-night ``::warning`` (the primary disclosure) is unconditional and
#: fires on every refusal regardless of the sidecar's state.
_NIGHTLY_PRUNE_STREAK_NAME = "_nightly_prune_conflict_streak.json"


def _read_prune_conflict_streak(out_dir: Path) -> dict:
    """Prior streak state, or ``{}`` on missing/corrupt/unreadable/non-dict — NEVER
    raises. A parsed JSON payload that is not itself an object (``null``, a list, a
    bare number, a bare string — all valid JSON, none of them usable state) is
    exactly as unusable as a missing file: treated as "no prior streak", never
    propagated to the caller's ``.get`` calls, which would otherwise raise
    ``AttributeError`` and break AMENDMENT §3's pinned always-return-0 invariant.
    Individual COUNTER fields inside a dict payload are validated separately by the
    caller via :func:`_valid_streak_count` (a dict is not proof its ``consecutive``/
    ``refusals_since_last_success`` values are themselves usable ints)."""
    path = out_dir / _NIGHTLY_PRUNE_STREAK_NAME
    try:
        payload = json.loads(path.read_text())
    except Exception:  # noqa: BLE001 — a corrupt sidecar restarts the streak, never crashes
        return {}
    return payload if isinstance(payload, dict) else {}


def _valid_streak_count(value: object) -> bool:
    """True iff ``value`` is a usable prior streak count: a real (non-``bool``)
    ``int`` that is ``>= 1``. ``bool`` is a subclass of ``int`` in Python
    (``isinstance(True, int)`` is ``True``, and ``True + 1 == 2``), so a naive
    ``isinstance(x, int)`` check would silently accept a JSON ``true``/``false``
    sidecar value as a real count — excluded explicitly. Zero and negative values
    are likewise never a legitimate PRIOR count (every real streak starts at 1),
    so they are treated the same as "no prior streak", not propagated forward."""
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _clear_prune_conflict_streak(out_dir: Path) -> None:
    path = out_dir / _NIGHTLY_PRUNE_STREAK_NAME
    if path.exists():
        path.unlink()


def _read_bytes_if_exists(path: Path) -> bytes | None:
    return path.read_bytes() if path.exists() else None


def _identity_rail_unreadable(directory: Path) -> bool:
    """True iff ``directory`` cannot supply a readable newest-snapshot parquet.

    Shared preflight test for BOTH silently-degrading identity rails
    (:data:`CIK_MAP_DIR`, :data:`SYMBOL_DIR_SNAPSHOTS`) — see :func:`run_nightly_refresh`.
    """
    if not directory.is_dir():
        return True
    files = sorted(p for p in directory.glob("*.parquet"))
    if not files:
        return True
    try:
        import pandas as pd
        pd.read_parquet(files[-1])
    except Exception:  # noqa: BLE001 — an unreadable snapshot refuses, never half-runs
        return True
    return False


def _legacy_rollback_cannot_replace_native(out_dir: Path) -> bool:
    """Refuse a stale rollback if current receipt became native or unreadable.

    A newer native publisher may have committed its receipt while this older
    nightly builder was still processing. Restoring an older legacy receipt
    would erase genuine owner history. This is fail-closed observed-state
    protection, NOT a shared interprocess lock or atomic transaction.
    """
    try:
        _assert_no_unpreserved_native_generation(out_dir)
    except IdentityError as exc:
        print(
            "::error title=security-master-native-history-race::"
            f"{exc} — refusing stale legacy rollback; preserving current "
            "reference files for canonical source-owner reconciliation",
            flush=True,
        )
        return True
    return False


def _restore_artifacts(out_dir: Path, before: dict[str, bytes | None],
                       before_receipt: bytes | None) -> bool:
    if _legacy_rollback_cannot_replace_native(out_dir):
        return False
    for name, content in before.items():
        path = out_dir / name
        if content is None:
            if path.exists():
                path.unlink()
        else:
            path.write_bytes(content)
    receipt_path = out_dir / RECEIPT_NAME
    if before_receipt is None:
        if receipt_path.exists():
            receipt_path.unlink()
    else:
        receipt_path.write_bytes(before_receipt)
    return True


def run_nightly_refresh(out_dir: Path) -> int:
    """Keep one writer lock across old snapshot, build, rollback and cleanup."""
    try:
        with _reference_writer_scope(out_dir):
            return _run_nightly_reference_unlocked(out_dir)
    except IdentityError as exc:
        print("::error title=security-master-writer-refusal::"
              f"{exc} — nightly did not acquire a valid writer transaction", flush=True)
        return 0


def _run_nightly_reference_unlocked(out_dir: Path) -> int:
    """The ``daily.yml`` collect-job seam (spec §7).  Fail-closed refresh laws:

      (a) a missing/unreadable identity input -> REFUSE, keep last-good artifacts,
          ``::warning``, exit 0, ``generated_at`` NOT re-stamped;
      (b) inputs unchanged since the last generation -> byte-stable no-op,
          ``generated_at`` NOT re-stamped;
      (c) inputs advanced -> regenerate, stamp, receipt pins the exact snapshot ids
          consumed.

    A source failure can never produce a falsely fresh identity generation (§23.24):
    the real (writing) build always runs first into ``out_dir``, and its output is
    then compared byte-for-byte against what was there before — if nothing besides
    the receipt's own wall-clock stamp changed, or if the run surfaced a config
    defect (an unmodelled rename / listing-key collision, the two things
    ``receipt['notes']`` ever carries), every artifact including the receipt is
    restored to its prior bytes.  Non-fatal throughout: this function always returns
    0 — a nightly step must never fail the collect job over an identity refresh.

    Law (a) covers THREE distinct identity inputs, all refused pre-flight (never left
    to ``build()``): the ``required`` seed/config files above, the ``CIK_MAP_DIR``
    evidence rail (escape #11), and the ``SYMBOL_DIR_SNAPSHOTS`` listing rail (V4-D2B1
    FIX 2 / B2/n2).  ``load_cik_map()``/``load_directory()`` both silently degrade to
    an empty mapping when their directory is missing/empty/unreadable (correct for the
    one-shot ``build()``/``main()`` CLI path, where "no evidence yet" is a valid state
    to mint from — hardened for THAT path too, see ``allow_missing_evidence`` on
    :func:`build`), which would otherwise let the nightly regenerate a falsely fresh
    artifact: an empty CIK map mints every row ``NO_ISSUER_EVIDENCE``, and an empty
    listing-snapshots dir starves ``resolve_universe`` of any venue evidence at all,
    collapsing coverage toward zero while still returning a clean receipt with no
    ``notes`` and a success ``::notice`` — the false-freshness escape this law exists
    to close, on either rail.
    """
    required = (CONSTITUENTS, MIDCAP_CONSTITUENTS, SMALLCAP_CONSTITUENTS, MEMBERSHIP,
                DELISTED_LEDGER, CONFIG_YML, TICKER_ALIASES_PY)
    missing = [
        str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)
        for p in required if not p.exists()
    ]
    if missing:
        print(
            f"::warning title=security-master-nightly::missing identity input(s) "
            f"{missing} — refusing, keeping last-good artifacts, generated_at not "
            "re-stamped", flush=True,
        )
        return 0

    # V4-D2B1 FIX 2 (B2/n2): the listing-snapshots rail was not covered by the
    # cik_map fence commit ed49d19083d0 landed — an empty/missing snapshots dir made
    # load_directory() silently return ({}, None, None), so a nightly run over it
    # would resolve almost nothing (coverage collapses toward zero) yet still stamp a
    # fresh generation and a success ::notice. Same law as the cik_map rail below.
    if _identity_rail_unreadable(SYMBOL_DIR_SNAPSHOTS):
        print(
            "::warning title=security-master-nightly::identity input missing: "
            "symbol_directory snapshots — refusing to regenerate; last-good "
            "artifacts retained", flush=True,
        )
        return 0

    # V4-D2B1 escape #11: load_cik_map() silently degrades to an empty mapping when
    # CIK_MAP_DIR is missing/empty/unreadable (the manual `build()` path treats that
    # as "no CIK evidence yet", not a failure — every row just mints NO_ISSUER_EVIDENCE
    # and the run still returns a clean receipt with no `notes`). Nightly is the ONLY
    # lane this widens into an escape: the same silent degrade there was a fail-CLOSED
    # violation of law (a) — a missing evidence rail must refuse, never regenerate a
    # falsely-fresh artifact where every issuer axis value quietly goes NO_ISSUER_EVIDENCE.
    if _identity_rail_unreadable(CIK_MAP_DIR):
        print(
            "::warning title=security-master-nightly::identity input missing: "
            "cik_map — refusing to regenerate; last-good artifacts retained",
            flush=True,
        )
        return 0

    before = {name: _read_bytes_if_exists(out_dir / name) for name in _NIGHTLY_ARTIFACT_NAMES}
    before_receipt = _read_bytes_if_exists(out_dir / RECEIPT_NAME)

    try:
        receipt = build(out_dir, dry_run=False)
    except VendorAliasPruneConflict as exc:
        # AMENDMENT ruling 11 (§3) — a DEDICATED handler, BEFORE the generic one
        # below: a fresh alias row conflicting with a committed ACTIVE-id row
        # (ruling 6 / M5) that the AMENDMENT §2 same-id-refinement carve-out did
        # NOT excuse is a curation-required refusal, not a build defect. Same
        # restore-and-continue shape as the generic handler, but its own named
        # ::warning so the nightly log says WHAT needs curating rather than a bare
        # "read/parse failure".
        if not _restore_artifacts(out_dir, before, before_receipt):
            return 0
        print(
            f"::warning title=security-master-nightly-prune-conflict::{exc} — "
            "curation required (a new RENAME_EVENTS/SECURITY_SUPERSESSIONS entry, "
            "or an operator resolving the conflict by hand); keeping last-good "
            "artifacts, generated_at not re-stamped", flush=True,
        )
        # DSC falsifier escalation — a STANDING conflict silently wedges the
        # nightly artifact refresh indefinitely (measured 8 days, 2026-08-20 ->
        # 08-28). The seam still ALWAYS returns 0 (AMENDMENT §3's invariant is
        # unconditional — the escalation is the annotation, never the exit code),
        # but a THIRD+ refusal with no intervening SUCCESSFUL refresh also raises
        # its voice with a loud ::error naming how long the artifact set has been
        # frozen and the curation cure. TWO counters, both fed by every refusal
        # here: ``consecutive`` (the MATCHING-TEXT streak — restarts at 1 whenever
        # the conflict text changes, a different conflict being a fresh clock) and
        # ``refusals_since_last_success`` (MONOTONIC — every refusal here
        # increments it regardless of text, reset ONLY on a success). The monotonic
        # counter exists because two or more DIFFERENT conflicts recurring in
        # ALTERNATION (A, B, A, B, ...) would otherwise hold ``consecutive`` at 1
        # forever — genuinely wedged, yet never escalating under the text-matching
        # counter alone.
        streak_path = out_dir / _NIGHTLY_PRUNE_STREAK_NAME
        prior = _read_prune_conflict_streak(out_dir)
        now_stamp = _iso_now()
        conflict_text = str(exc)[:1000]

        prior_consecutive = prior.get("consecutive")
        same_conflict = (
            prior.get("conflict") == conflict_text and _valid_streak_count(prior_consecutive)
        )
        if same_conflict:
            consecutive = prior_consecutive + 1
            first_conflict_at = prior.get("first_conflict_at") or now_stamp
        else:
            consecutive = 1
            first_conflict_at = now_stamp

        prior_refusals = prior.get("refusals_since_last_success")
        if _valid_streak_count(prior_refusals):
            refusals_since_last_success = prior_refusals + 1
            first_refusal_at = prior.get("first_refusal_at") or now_stamp
        else:
            refusals_since_last_success = 1
            first_refusal_at = now_stamp

        streak_path.write_text(json.dumps({
            "consecutive": consecutive,
            "first_conflict_at": first_conflict_at,
            "refusals_since_last_success": refusals_since_last_success,
            "first_refusal_at": first_refusal_at,
            "last_conflict_at": now_stamp,
            "conflict": conflict_text,
        }, indent=2, sort_keys=True) + "\n")

        # Escalate on EITHER trigger. A same-text streak (consecutive >= 3) is
        # checked FIRST and, when it fires, is always also true of the monotonic
        # counter (every matching-text refusal is also a refusal) — so preferring
        # it keeps the message from claiming "conflict text has varied" when it
        # has not. Only when consecutive stays under 3 (the text changed
        # recently) but the monotonic count has still reached 3 do we escalate on
        # alternating/varying conflicts, with wording that says so.
        if consecutive >= 3:
            escalate_n, escalate_since, varied = consecutive, first_conflict_at, False
        elif refusals_since_last_success >= 3:
            escalate_n, escalate_since, varied = (
                refusals_since_last_success, first_refusal_at, True
            )
        else:
            escalate_n = None
        if escalate_n is not None:
            varied_note = " (conflict text has varied)" if varied else ""
            print(
                f"::error title=security-master-nightly-prune-conflict-stuck::"
                f"{escalate_n} nightly prune-conflict refusals{varied_note} with no "
                f"intervening successful refresh since {escalate_since}; cure "
                "with a curation act (a new RENAME_EVENTS/SECURITY_SUPERSESSIONS "
                "entry) or an operator hand migration.", flush=True,
            )
        return 0
    except Exception as exc:  # noqa: BLE001 — any read/parse failure refuses, never half-writes
        # FIX 4 (M2): a mid-build failure can leave PARTIAL writes on disk (build()
        # writes master -> aliases -> issuer_master -> issuer_migrations -> receipt in
        # sequence, and any of those can raise) — restore ALL artifacts to last-good
        # rather than leaving a torn mix of new-and-old bytes.
        if not _restore_artifacts(out_dir, before, before_receipt):
            return 0
        print(
            f"::warning title=security-master-nightly::build failed reading identity "
            f"inputs ({exc}) — keeping last-good artifacts, generated_at not "
            "re-stamped", flush=True,
        )
        return 0

    if receipt.get("notes"):
        if not _restore_artifacts(out_dir, before, before_receipt):
            return 0
        print(
            f"::warning title=security-master-nightly::{'; '.join(receipt['notes'])} — "
            "unmodelled rename or listing-key collision; keeping last-good artifacts, "
            "generated_at not re-stamped", flush=True,
        )
        return 0

    after = {name: _read_bytes_if_exists(out_dir / name) for name in _NIGHTLY_ARTIFACT_NAMES}
    if after == before:
        if before_receipt is not None:
            # Even a byte-stable legacy build must not reset a newer native
            # receipt that appeared while its unchanged inputs were checked.
            if _legacy_rollback_cannot_replace_native(out_dir):
                return 0
            (out_dir / RECEIPT_NAME).write_bytes(before_receipt)
        _clear_prune_conflict_streak(out_dir)
        print(
            "::notice title=security-master-nightly::inputs unchanged since the last "
            "generation — byte-stable no-op, generated_at not re-stamped", flush=True,
        )
        return 0

    _clear_prune_conflict_streak(out_dir)
    print(
        f"::notice title=security-master-nightly::identity inputs advanced — "
        f"regenerated ({coverage_line(receipt)})", flush=True,
    )
    return 0


# ── Reporting ─────────────────────────────────────────────────────────────────
def coverage_line(receipt: dict) -> str:
    """``N/M resolved, K unresolved`` — the number DOS-1.1 asks to be REPORTED."""
    cov = receipt["coverage"]
    return f"{cov['resolved']}/{cov['total']} resolved, {cov['unresolved']} unresolved"


def _report(receipt: dict, verbose: bool) -> None:
    resolutions = receipt.get("_resolutions") or []
    print(coverage_line(receipt))
    unresolved = [r for r in resolutions if r.listing_key is None]
    for res in unresolved:
        print(f"  UNRESOLVED {res.key}: {res.reason}")
    if unresolved:
        # Bare print at column 0, never through a logger: a prefixing formatter emits
        # "WARNING ::warning …" and GitHub silently drops it
        # (tests/test_gh_annotation_line_start.py).
        print(
            f"::warning title=security-master-coverage::{coverage_line(receipt)} — "
            f"unresolved: {', '.join(r.key for r in unresolved)}",
            flush=True,
        )
    for note in receipt.get("notes") or []:
        print(f"::warning title=security-master-note::{note}", flush=True)

    if not verbose:
        return
    print(f"  security_master rows: {receipt['row_counts']['security_master']}")
    print(f"  vendor_aliases rows:  {receipt['row_counts']['vendor_aliases']}")
    print(f"  symbol directory:     {receipt['symbol_directory_snapshot']}")
    for event in receipt["rename_events"]:
        print(
            f"  dated rename {event['old']}->{event['new']} on {event['on']} "
            f"in {','.join(event['vendors'])}"
        )
    for undated in receipt["undated_renames"]:
        print(f"  undated rename {undated['old']}->{undated['new']} (open-bounded rows)")
    for name, digest in sorted(receipt["inputs"].items()):
        print(f"  input {name} sha256={digest}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(DEFAULT_OUT),
                        help="output directory (default: data/reference)")
    parser.add_argument("--dry-run", action="store_true",
                        help="build and report, write nothing")
    parser.add_argument("--reference-evidence", type=Path,
                        help="bounded prospective reference observations; no network calls")
    parser.add_argument("--direct-registrant-evidence", type=Path,
                        help="new captured SEC/listing observation; no old-input replay or network calls")
    parser.add_argument("--spy-option-root-evidence", type=Path,
                        help="bounded captured SPY option sources; existing canonical target required")
    parser.add_argument("--report", action="store_true",
                        help="full census: row counts, rename events, input hashes")
    parser.add_argument(
        "--nightly", action="store_true",
        help=(
            "daily.yml collect-job seam (spec §7): fail-closed refresh — refuses "
            "non-fatally on a missing/unreadable identity input, is a byte-stable "
            "no-op when nothing advanced, and only re-stamps generated_at when "
            "inputs genuinely changed. Always exits 0. Ignores --dry-run/--report."
        ),
    )
    parser.add_argument(
        "--allow-missing-evidence", action="store_true",
        help=(
            "V4-D2B1 FIX 2 (B2 manual-path hardening): opt out of the refusal that "
            "otherwise raises when data/symbol_directory/cik_map has no snapshot — "
            "build anyway, minting every row NO_ISSUER_EVIDENCE. Prints a warning. "
            "Ignored under --nightly (the nightly seam has its own, always-refusing "
            "preflight and never reaches this flag)."
        ),
    )
    args = parser.parse_args(argv)

    if args.nightly and (args.reference_evidence is not None or args.direct_registrant_evidence is not None or args.spy_option_root_evidence is not None):
        parser.error("evidence intake is explicit, not a nightly fetch")
    if args.nightly:
        return run_nightly_refresh(Path(args.out))

    if args.allow_missing_evidence:
        print(
            "::warning title=security-master-manual::--allow-missing-evidence set — "
            "building without CIK issuer evidence; every row will mint "
            "NO_ISSUER_EVIDENCE", flush=True,
        )
    receipt = build(Path(args.out), dry_run=args.dry_run,
                    allow_missing_evidence=args.allow_missing_evidence,
                    reference_evidence_path=args.reference_evidence,
                    direct_registrant_inputs=(read_direct_registrant_inputs(args.direct_registrant_evidence)
                                              if args.direct_registrant_evidence is not None else ()),
                    spy_option_root_input=(read_spy_option_root_input(args.spy_option_root_evidence)
                                           if args.spy_option_root_evidence is not None else None))
    _report(receipt, verbose=args.report)
    # A NOTE IS A FAILURE, not a warning (adversarial review, 2026-08-13).  `notes`
    # carries exactly two things, and neither may pass: a rename the repo's own maps
    # record that this builder does not model (the alias table would answer the OLD
    # pairing forever — the seven-month MMC loss, one layer up), and a listing-key
    # COLLISION, which spec §5 says takes an operator-ratified `.2` disambiguator and
    # never a guess.  Emitting a `::warning` and exiting 0 makes the detector advisory,
    # and an advisory detector on a silent-loss defect is decoration.  Coverage is NOT
    # in this set on purpose: DOS-1.1 asks for it to be REPORTED, not asserted complete.
    if receipt.get("notes"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
