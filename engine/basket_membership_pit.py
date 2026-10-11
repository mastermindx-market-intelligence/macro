"""Point-in-time (PIT) membership history for the two CN basket suites.

WHY THIS EXISTS
---------------
``research/CHINA_PROPHET_LOSER_INTELLIGENCE_MASTERPLAN_BY_FABLE.md`` §2.12 names
this the **weakest joint** of the whole relay program: the THS concept-board
membership used by the 12-month ignition/chase study was a single 2026-07-08
snapshot applied BACKWARD over the entire window, and the two PIT snapshots that
do exist differ by 7.7% of member-slots across 8 days.  Any theme/relay
construction measured on back-applied membership is look-ahead-contaminated, so
§5 W-C charters this store as the prerequisite for ANY future relay-construction
promotion.  It ships display/infrastructure tier and grades nothing.

WHAT IT IS
----------
An append-only parquet per suite — ``data/<suite>/membership_history.parquet`` —
with one row per ``(snapshot_date, basket_id, ticker)``, keep-FIRST on that key
so a re-run on the same day can never duplicate or rewrite a stamped day.  The
curated suite (``baskets_china``) is snapshotted the same way as the machine
suite (``baskets_china_ths``): same columns, same semantics, so a consumer needs
one reader, not two.

CONTENT DEDUP (why every calendar day is not a row set)
------------------------------------------------------
A full THS snapshot is ~3,500 member rows.  Stamping one every night would add
~1.3M rows/year that say nothing — membership moves on the vendor's schedule,
not the trading calendar.  So a snapshot_date is stamped only when the
membership set DIFFERS from the newest one already stored (``members_sha`` over
the normalized ``(basket_id, ticker, added, removed)`` tuples, so a cosmetic
re-serialization of membership.json is not mistaken for a membership change).
This is the same content-dedup the sibling JSON side-car in
``scripts/build_baskets_china_ths.py`` already uses, and it leaves the PIT read
identical: **the membership in force at date D is the newest snapshot ≤ D.**

LANE DISCIPLINE
---------------
House law (CLAUDE.md): nightly/asia is the sole advancer of ledgers; render
lanes discard ``data/`` writes.  Every writer here goes through ``_lane_ok``,
which is FAIL-CLOSED and PER-SUITE: each suite names the ONE collection lane
allowed to advance it (``SUITE_LANE``) and everything else — a foreign lane, an
unrecognised lane, an unknown suite, or no lane at all — is refused before any
write.  It does NOT mirror ``engine.china_standout_track.append_board``'s
permissive ``lane is not None`` form; see ``_lane_ok`` for why keep-FIRST makes
that default unsafe here.

THREE SUITES, TWO LANES (GMI W1a)
---------------------------------
The two CN suites are advanced by the asia collection lane (asia-close.yml,
``CN_LANE=asia``).  The US suite ``baskets`` — the 49 hand-curated US thematic
baskets in ``data/baskets/membership.json`` — is advanced by the US nightly
(daily.yml, ``COLLECT_LANE=nightly``), which is the only lane that collects and
commits US ``data/``.  The gate is per-suite precisely because "asia" is the
wrong answer for a US store and "nightly" is the wrong answer for a CN one: a
single global lane name would have to be permissive enough to admit both, and
this store cannot afford a permissive gate (keep-FIRST, below).  US rows carry
the same COLUMNS; ``name_zh`` is simply empty for them — one reader, not two.

TWO SIDE-CAR SHAPES (and why the store says which one it used)
--------------------------------------------------------------
The dated JSON side-cars are not uniform.  ``2026-06-30.json`` predates the
byte-copy the seeder writes today: it is the RAW vendor concept dump keyed by
the Chinese board name, ~9,069 member-slots.  ``2026-07-08.json`` is a
membership.json copy — the SEEDED, capped subset the engine actually tracks,
~3,532 slots.  Both are true about their own population; they are not the same
population.  Differencing naively across that boundary reports ~61% "drift",
which is mostly the seeding cap.  So every row records ``source_shape`` and
``members_asof`` returns it with an explicit note when the resolved snapshot's
shape is not the store's newest.  The alternative — dropping the older file —
would delete half of the only real PIT evidence the program has.

THE READER'S CONTRACT (the load-bearing half)
---------------------------------------------
``members_asof`` ALWAYS reports which basis it answered on.  When the history
predates the requested date — the store's birth is forward-only, so every date
before its first snapshot is uncovered — it falls back to the CURRENT
membership.json and stamps ``pit=False``.  A consumer that silently treats a
fallback answer as point-in-time is exactly the look-ahead bug this store was
built to end, so the flag is not optional metadata: it is the answer.  The same
goes for ``source_shape``: a caveat that does not travel with the answer is a
caveat nobody reads.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from lib import config

log = logging.getLogger(__name__)

SUITE_THS = "baskets_china_ths"
SUITE_CURATED = "baskets_china"
SUITE_US = "baskets"

#: The CN pair.  Kept as ``SUITES`` because it is the default of ``append_all``
#: and the set every existing caller and test means by "both suites".
SUITES: tuple[str, ...] = (SUITE_THS, SUITE_CURATED)
#: The US suite, advanced by a DIFFERENT lane — hence its own tuple.
SUITES_US: tuple[str, ...] = (SUITE_US,)
ALL_SUITES: tuple[str, ...] = (*SUITES, *SUITES_US)

#: The ONE collection lane permitted to advance each suite's PIT store.
#: Fail-closed by construction: a suite absent from this map has NO lane that
#: may write it, so a typo'd or newly-added suite refuses until it is declared.
SUITE_LANE: dict[str, str] = {
    SUITE_THS: "asia",       # asia-close.yml band A, CN_LANE=asia
    SUITE_CURATED: "asia",   # ditto
    SUITE_US: "nightly",     # daily.yml engine job, COLLECT_LANE=nightly
}

MEMBERSHIP_FILE = "membership.json"
HISTORY_FILE = "membership_history.parquet"
SNAPSHOT_DIR = "snapshots"

#: Mutable cadence stamp inside each suite's snapshot dir — deliberately NOT part
#: of the append-only history.  See ``write_cadence_stamp``.  The leading
#: underscore keeps it out of the ``????-??-??.json`` dated-side-car namespace.
CADENCE_FILE = "_cadence.json"

#: Parquet column order.  ``added``/``removed`` are the source's own PIT dates and
#: are carried through so a reader can resolve membership BETWEEN two snapshots.
COLUMNS: tuple[str, ...] = (
    "snapshot_date", "suite", "basket_id", "ticker",
    "added", "removed", "name_zh", "members_sha", "source_shape",
    "record_kind", "collection_id", "collection_receipt",
)

#: Which document shape a row was read from — the honest bound on how PIT it is.
#: ``membership`` = a membership.json (baskets + per-member added/removed dates).
#: ``ths_concept_dump`` = the raw vendor concept dump the earliest side-car uses:
#: members are point-in-time, but the concept -> basket_id mapping is today's.
SHAPE_MEMBERSHIP = "membership"
SHAPE_CONCEPT_DUMP = "ths_concept_dump"

#: Keep-first key (masterplan §5 W-C: "append-only store, keep-first per date").
KEY: tuple[str, ...] = ("snapshot_date", "basket_id", "ticker")

_BASIS_PIT = "pit_snapshot"
_BASIS_CURRENT = "current_membership"
_BASIS_UNKNOWN = "unknown_basket"


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def membership_path(suite: str) -> Path:
    """Live membership document for ``suite``."""
    return config.data_dir() / suite / MEMBERSHIP_FILE


def history_path(suite: str) -> Path:
    """Append-only PIT history parquet for ``suite``."""
    return config.data_dir() / suite / HISTORY_FILE


def snapshot_dir(suite: str) -> Path:
    """Dated JSON side-car directory for ``suite``."""
    return config.data_dir() / suite / SNAPSHOT_DIR


def cadence_path(suite: str) -> Path:
    """The suite's mutable cadence stamp (see ``write_cadence_stamp``)."""
    return snapshot_dir(suite) / CADENCE_FILE


def dated_snapshots(suite: str) -> list[Path]:
    """The suite's dated side-cars, oldest→newest.

    The ONE place the dated-side-car namespace is defined.  ``????-??-??.json``
    excludes the ``_cadence.json`` stamp and any other underscore-prefixed
    working file — an important exclusion rather than a cosmetic one, because
    ``_`` sorts AFTER every digit in ASCII, so a plain ``*.json`` glob taking a
    max/last would resolve the stamp as the NEWEST snapshot.
    """
    d = snapshot_dir(suite)
    try:
        return sorted(p for p in d.glob("????-??-??.json")) if d.is_dir() else []
    except Exception as exc:  # noqa: BLE001
        log.warning("basket_membership_pit: snapshot scan failed for %s (%s)", suite, exc)
        return []


# ---------------------------------------------------------------------------
# Small pure helpers
# ---------------------------------------------------------------------------

def _text(v: object) -> str | None:
    """Trimmed string, or None for null/blank/NaN. Never raises.

    A parquet round-trip turns a missing ``removed`` date into NaN, not None, and
    ``str(nan)`` is the truthy string "nan" — so the NaN check has to come first
    or every never-removed member reads as removed on a date called "nan".
    """
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    s = str(v).strip()
    if not s or s.lower() in ("none", "nan", "nat", "null"):
        return None
    return s


def _baskets(doc: object) -> dict:
    """The ``baskets`` mapping of a membership document, or {}."""
    if not isinstance(doc, dict):
        return {}
    b = doc.get("baskets")
    return b if isinstance(b, dict) else {}


#: One normalized member slot: (basket_id, ticker, added, removed, name_zh).
_Member = tuple[str, str, str, str, str]


def _members_from_membership(doc: object) -> list[_Member]:
    """Member slots from a membership.json-shaped document."""
    out: list[_Member] = []
    for basket_id, basket in _baskets(doc).items():
        if not isinstance(basket, dict):
            continue
        for m in basket.get("members") or []:
            if not isinstance(m, dict):
                continue
            ticker = _text(m.get("ticker")) or _text(m.get("code"))
            if not ticker:
                continue
            out.append((str(basket_id), ticker,
                        _text(m.get("added")) or "", _text(m.get("removed")) or "",
                        _text(m.get("name_zh")) or ""))
    return out


def _concept_index(suite: str) -> dict[str, str]:
    """``ths_concept`` (raw 同花顺 board name) -> basket_id, from live membership."""
    out: dict[str, str] = {}
    for basket_id, basket in _baskets(_read_json(membership_path(suite))).items():
        if not isinstance(basket, dict):
            continue
        concept = _text(basket.get("ths_concept"))
        if concept:
            out[concept] = str(basket_id)
    return out


def _members_from_concept_dump(doc: object, concept_to_basket: dict[str, str]) -> list[_Member]:
    """Member slots from the RAW THS concept dump shape ``{concept: [{ticker,name}]}``.

    The earliest side-car (2026-06-30) predates the membership.json byte-copy the
    seeder writes today, so it is keyed by the vendor's Chinese concept name.  It
    is also HALF of the program's only real PIT evidence — the pair whose 7.7%
    member-slot drift is §2.12's receipt — so it is read rather than skipped.

    HONEST BOUND, recorded in the ``source_shape`` column: the MEMBERS are
    point-in-time, but the concept -> basket_id mapping is today's, so which
    concepts we track is a current-basis choice.  A concept we do not track today
    contributes nothing; the caller logs how many were dropped.
    """
    out: list[_Member] = []
    if not isinstance(doc, dict):
        return out
    for concept, members in doc.items():
        basket_id = concept_to_basket.get(str(concept).strip())
        if not basket_id or not isinstance(members, list):
            continue
        for m in members:
            if not isinstance(m, dict):
                continue
            ticker = _text(m.get("ticker")) or _text(m.get("code"))
            if not ticker:
                continue
            # No added/removed in this shape — absent, not "unknown-as-a-date".
            out.append((basket_id, ticker, "", "", _text(m.get("name")) or ""))
    return out


def _sha_of(members: list[_Member]) -> str:
    """sha256 over the SORTED (basket_id, ticker, added, removed) slots.

    The dedup basis.  Sorting + normalizing is what makes the hash describe the
    MEMBERSHIP rather than the file's byte layout: a re-ordered or re-indented
    membership.json hashes identically and is correctly not stamped as a new
    snapshot.  ``name_zh`` is excluded — a vendor renaming a company is not a
    membership change.
    """
    payload = json.dumps(sorted({m[:4] for m in members}), ensure_ascii=False,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def members_sha(doc: object) -> str:
    """sha256 of a membership.json-shaped document's member set."""
    return _sha_of(_members_from_membership(doc))


def _rows_from_members(members: list[_Member], snapshot_date: str, suite: str,
                       source_shape: str) -> list[dict]:
    """Flatten normalized member slots into PIT rows for one snapshot_date."""
    sha = _sha_of(members)
    return [{
        "snapshot_date": str(snapshot_date),
        "suite": suite,
        "basket_id": basket_id,
        "ticker": ticker,
        "added": added or None,
        "removed": removed or None,
        "name_zh": name_zh or None,
        "members_sha": sha,
        "source_shape": source_shape,
    } for basket_id, ticker, added, removed, name_zh in members]


def _rows_from_doc(doc: object, snapshot_date: str, suite: str) -> list[dict]:
    """Flatten a membership.json-shaped document into PIT rows."""
    return _rows_from_members(_members_from_membership(doc), snapshot_date, suite,
                              SHAPE_MEMBERSHIP)


def _read_json(path: Path) -> object | None:
    """Parse a JSON file, or None. Never raises."""
    try:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 — a bad file degrades to "no snapshot"
        log.warning("basket_membership_pit: unreadable %s (%s)", path, exc)
        return None


class HistoryIntegrityError(ValueError):
    """Existing PIT history is unsafe to advance."""


class HistoryWriteError(ValueError):
    """A staged PIT append failed; the prior destination is preserved."""


def _validate_history(df: pd.DataFrame, suite: str) -> None:
    # The owner's legacy schema-union rule remains valid for optional metadata.
    # A missing membership key or suite cannot be repaired by inventing identity.
    missing = set((*KEY, "suite")) - set(df.columns)
    if missing:
        raise HistoryIntegrityError(f"PIT history missing required columns: {sorted(missing)}")
    markers = _collection_records(df)
    members = _member_records(df)
    for field in KEY:
        checked = members[field] if field == "ticker" else df[field]
        if not checked.map(lambda value: isinstance(value, str) and bool(value.strip())).all():
            raise HistoryIntegrityError(f"PIT history invalid key: {field}")
    if not markers.empty and not markers["ticker"].isna().all():
        raise HistoryIntegrityError("collection record cannot carry a ticker")
    if "record_kind" in df:
        kinds = df["record_kind"].dropna()
        if not kinds.isin(["member.v2", "collection.v2"]).all():
            raise HistoryIntegrityError("unknown PIT record kind")
    _validate_collection_groups(df, suite)
    if "record_kind" in members:
        for row in members[members["record_kind"].eq("member.v2")].to_dict("records"):
            linked = _text(row.get("collection_id"))
            if linked is not None:
                matches = markers[(markers["snapshot_date"] == row["snapshot_date"])
                                  & (markers["basket_id"] == row["basket_id"])]
                if matches.empty or not matches["collection_id"].eq(linked).all():
                    raise HistoryIntegrityError("orphan member collection reference")
            for field in ("added", "removed"):
                value = row.get(field)
                if _text(value) is None:
                    continue
                if not isinstance(value, str) or len(value) != 10:
                    raise HistoryIntegrityError("invalid member.v2 source window")
                try:
                    datetime.strptime(value, "%Y-%m-%d")
                except ValueError as exc:
                    raise HistoryIntegrityError("invalid member.v2 source date") from exc
    if not df["suite"].eq(suite).all():
        raise HistoryIntegrityError(f"PIT history contains rows from another suite: {suite}")
    if df.duplicated(subset=list(KEY)).any():
        raise HistoryIntegrityError("PIT history duplicate snapshot/member key")



def collection_generation_sha(doc: object) -> str:
    """Exact canonical input-generation scope, separate from member-set digest."""
    payload = json.dumps(doc, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def collection_id(receipt: dict) -> str:
    """Identity binds scope, source/generation, clocks, completeness and all members."""
    payload = {key: value for key, value in receipt.items() if key != "collection_id"}
    return "collection:" + collection_generation_sha(payload)


def _collection_clock(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z") or "T" not in value:
        raise HistoryIntegrityError("collection clock must be a precise UTC instant")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise HistoryIntegrityError("invalid collection clock") from exc


def validate_collection(receipt: object, *, suite: str, basket_id: str,
                        snapshot_date: str, members: list[_Member],
                        doc: object | None = None, now: datetime | None = None) -> dict:
    """Owner admission, not a collector-completeness inference from present rows."""
    import jsonschema

    path = Path(__file__).resolve().parent.parent / (
        "contracts/theme_graph/membership_collection.v2.schema.json")
    try:
        jsonschema.Draft202012Validator(json.loads(path.read_text())).validate(receipt)
    except (jsonschema.ValidationError, TypeError) as exc:
        raise HistoryIntegrityError("invalid collection receipt schema") from exc
    if receipt["suite"] != suite or receipt["basket_id"] != basket_id:
        raise HistoryIntegrityError("collection scope mismatch")
    if receipt["source_ref"] != f"data/{suite}/membership.json":
        raise HistoryIntegrityError("collection source mismatch")
    if receipt["generation_id"] != receipt["generation_sha256"][:16]:
        raise HistoryIntegrityError("collection generation mismatch")
    if receipt["collection_id"] != collection_id(receipt):
        raise HistoryIntegrityError("collection identity mismatch")
    observed = _collection_clock(receipt["observed_at"])
    known = _collection_clock(receipt["known_at"])
    if observed > known or known.date().isoformat() != snapshot_date:
        raise HistoryIntegrityError("collection chronology/snapshot mismatch")
    if now is not None and known > now:
        raise HistoryIntegrityError("future collection clock")
    scoped = sorted(set(m for m in members if m[0] == basket_id))
    if receipt["members_sha"] != _sha_of(scoped) or receipt["member_count"] != len(scoped):
        raise HistoryIntegrityError("collection full member set mismatch")
    if receipt["collection_state"] == "RETIRED" and scoped:
        raise HistoryIntegrityError("retired collection must be empty")
    if doc is not None and receipt["generation_sha256"] != collection_generation_sha(doc):
        raise HistoryIntegrityError("collection input generation mismatch")
    return receipt


def _collection_records(df: pd.DataFrame) -> pd.DataFrame:
    if "record_kind" not in df:
        return df.iloc[:0]
    return df[df["record_kind"].eq("collection.v2")]


def _member_records(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(index=_collection_records(df).index)



def _strict_collection_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise HistoryIntegrityError("duplicate collection JSON key")
        result[key] = value
    return result


def _validate_new_member_doc(doc: dict) -> None:
    for basket, source in _baskets(doc).items():
        if not isinstance(basket, str) or not basket.strip() or not isinstance(source, dict):
            raise HistoryIntegrityError("invalid member basket identity")
        members = source.get("members")
        if not isinstance(members, list):
            raise HistoryIntegrityError("member collection unavailable/malformed")
        seen = set()
        for member in members:
            if not isinstance(member, dict):
                raise HistoryIntegrityError("member must be an object")
            ticker = member.get("ticker") or member.get("code")
            if not isinstance(ticker, str) or not ticker.strip() or ticker in seen:
                raise HistoryIntegrityError("invalid/duplicate member identity")
            seen.add(ticker)
            for field in ("added", "removed"):
                value = member.get(field)
                if value is None or value == "":
                    continue
                if not isinstance(value, str) or len(value) != 10:
                    raise HistoryIntegrityError("member window must be date or null")
                try:
                    datetime.strptime(value, "%Y-%m-%d")
                except ValueError as exc:
                    raise HistoryIntegrityError("invalid member source window") from exc


def _validate_collection_groups(df: pd.DataFrame, suite: str) -> None:
    for _index, marker in _collection_records(df).iterrows():
        try:
            receipt = json.loads(marker["collection_receipt"], object_pairs_hook=_strict_collection_object)
        except (TypeError, ValueError) as exc:
            raise HistoryIntegrityError("malformed collection record") from exc
        peers = df[(df["snapshot_date"] == marker["snapshot_date"])
                   & (df["basket_id"] == marker["basket_id"])]
        members = _member_records(peers)
        slots = [(str(r["basket_id"]), str(r["ticker"]),
                  _text(r.get("added")) or "", _text(r.get("removed")) or "",
                  _text(r.get("name_zh")) or "")
                 for r in members.to_dict("records")]
        validate_collection(receipt, suite=suite, basket_id=marker["basket_id"],
                            snapshot_date=marker["snapshot_date"], members=slots)
        if (marker.get("collection_id") != receipt["collection_id"]
                or marker.get("members_sha") != receipt["members_sha"]
                or marker.get("source_shape") != SHAPE_MEMBERSHIP):
            raise HistoryIntegrityError("collection marker identity/shape/hash mismatch")
        if not members.empty and not members["collection_id"].eq(receipt["collection_id"]).all():
            raise HistoryIntegrityError("collection/member linkage mismatch")


def _qualified_rows(doc: dict, date: str, suite: str, receipts: list[dict]) -> list[dict]:
    _validate_new_member_doc(doc)
    members = _members_from_membership(doc)
    rows = _rows_from_doc(doc, date, suite)
    for row in rows:
        row.update(record_kind="member.v2", collection_id=None, collection_receipt=None)
    seen = set()
    for receipt in receipts:
        if not isinstance(receipt, dict) or not isinstance(receipt.get("basket_id"), str):
            raise HistoryIntegrityError("invalid collection subject")
        basket = receipt["basket_id"]
        if basket in seen:
            raise HistoryIntegrityError("duplicate collection scope")
        seen.add(basket)
        # Empty/retired baskets still need an explicit source slot; a missing key
        # cannot masquerade as an empty successful fetch.
        source = _baskets(doc).get(basket)
        if not isinstance(source, dict) or not isinstance(source.get("members"), list):
            raise HistoryIntegrityError("collection source slot unavailable")
        if any(not isinstance(m, dict) or not (_text(m.get("ticker")) or _text(m.get("code")))
               for m in source["members"]):
            raise HistoryIntegrityError("malformed collection member")
        validate_collection(receipt, suite=suite, basket_id=basket,
                            snapshot_date=date, members=members, doc=doc,
                            now=datetime.now(timezone.utc))
        for row in rows:
            if row["basket_id"] == basket:
                row["collection_id"] = receipt["collection_id"]
        marker = {col: None for col in COLUMNS}
        marker.update(snapshot_date=date, suite=suite, basket_id=basket,
                      source_shape=SHAPE_MEMBERSHIP, record_kind="collection.v2",
                      members_sha=receipt["members_sha"], collection_id=receipt["collection_id"],
                      collection_receipt=json.dumps(receipt, sort_keys=True, allow_nan=False))
        rows.append(marker)
    return rows


def _failed_result(result: dict, exc: ValueError) -> dict:
    result.update(status="failed", error=type(exc).__name__, reason=str(exc), rows_added=0)
    if "written" in result:
        result["written"] = False
    if "dates" in result:
        result["dates"] = []
    return result


def read_history(suite: str, *, strict: bool = False,
                 include_collection_records: bool = False) -> pd.DataFrame:
    """The PIT history frame for ``suite``.

    An absent owner store is an honest empty-history boundary.  An existing but
    unreadable store is different: callers on a publication path may request
    ``strict=True`` so corruption fails closed instead of masquerading as absence.
    """
    p = history_path(suite)
    try:
        if not p.exists():
            return pd.DataFrame(columns=list(COLUMNS))
        df = pd.read_parquet(p)
        if strict:
            _validate_history(df, suite)
        for col in COLUMNS:                       # schema union with older writes
            if col not in df.columns:
                df[col] = None
        if not _collection_records(df).empty:
            _validate_history(df, suite)
        return df if include_collection_records else _member_records(df)
    except Exception as exc:  # noqa: BLE001
        log.warning("basket_membership_pit: history read failed for %s (%s)", suite, exc)
        if strict:
            if isinstance(exc, HistoryIntegrityError):
                raise
            raise HistoryIntegrityError(f"unreadable PIT history for {suite}") from exc
        return pd.DataFrame(columns=list(COLUMNS))


def _latest_sha(df: pd.DataFrame) -> tuple[str | None, str | None]:
    """(snapshot_date, members_sha) of the NEWEST stored snapshot, or (None, None)."""
    if df.empty or "snapshot_date" not in df.columns:
        return None, None
    dates = df["snapshot_date"].astype(str)
    newest = dates.max()
    row = df[dates == newest]
    if row.empty:
        return None, None
    return str(newest), _text(row.iloc[0].get("members_sha"))


# ---------------------------------------------------------------------------
# Cadence stamp (mutable, deliberately outside the append-only history)
# ---------------------------------------------------------------------------

def write_cadence_stamp(suite: str, *, writer: str, membership_sha: str | None,
                        now: str | None = None) -> Path | None:
    """Rewrite ``<suite>/snapshots/_cadence.json`` — "this writer ran, and here is what it saw".

    WHY A SEPARATE STAMP.  Both snapshot writers are content-deduped: when
    membership has not changed they write nothing and log a dedup skip.  That is
    correct for the history and catastrophic for monitoring, because a writer that
    is deduping and a writer that has been UNWIRED FOR A MONTH leave the identical
    trace on disk — nothing.  That is precisely how the THS side-car store sat at
    two snapshots while its nightly step ran green ~35 nights in a row: the step
    hashed today's membership.json against the last side-car, matched, and skipped,
    every night, because nothing upstream was refreshing membership.json at all.

    So liveness gets its own artifact.  It is MUTABLE (rewritten every run) and
    therefore explicitly NOT part of the append-only history: it records the last
    time the writer ran, never what membership was on some past date.  It lives
    inside the snapshots dir so a reader needs one path, and is named with a
    leading ``_`` so it can never collide with — or be globbed as — a dated
    side-car (``dated_snapshots`` is the one enumerator, and it is date-shaped).

    ``membership_sha`` is the writer's own dedup basis (sha256 of the membership
    document it just hashed), so a stale ``last_snapshot_date`` next to a moving
    ``membership_sha`` says "membership is churning but nothing is being stamped",
    which is a different fault from "nothing is running".  Never raises.
    """
    try:
        p = cadence_path(suite)
        p.parent.mkdir(parents=True, exist_ok=True)
        dated = dated_snapshots(suite)
        payload = {
            "schema": "basket_membership_cadence.v1",
            "suite": suite,
            "writer": writer,
            "checked_at": now or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "membership_sha": membership_sha,
            "last_snapshot_date": dated[-1].stem if dated else None,
        }
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return p
    except Exception as exc:  # noqa: BLE001 — a liveness stamp never breaks a build
        log.warning("basket_membership_pit: cadence stamp failed for %s (%s)", suite, exc)
        return None


def read_cadence(suite: str) -> dict | None:
    """The suite's cadence stamp, or None when absent/unreadable."""
    blob = _read_json(cadence_path(suite))
    return blob if isinstance(blob, dict) else None


# ---------------------------------------------------------------------------
# Writers (one collection lane per suite)
# ---------------------------------------------------------------------------

def _lane_ok(lane: str | None, what: str, *, suite: str) -> bool:
    """The per-suite collection-lane gate for every writer here — FAIL-CLOSED.

    ``lane == SUITE_LANE[suite]`` writes.  EVERYTHING else refuses: a FOREIGN lane
    (the US nightly reaching for a CN suite, or asia reaching for the US one), an
    unrecognised lane, a suite with no declared lane, and — the case that matters —
    no lane at all.  This deliberately does NOT mirror
    ``china_standout_track.append_board``'s permissive ``lane is not None`` form.
    append_board can afford that default because a board row is re-derivable and a
    second lane rewriting it changes nothing.  This store cannot: it is append-only
    and keep-FIRST on ``(snapshot_date, basket_id, ticker)`` (masterplan §5 W-C), and
    it is content-deduped, so the FIRST lane to stamp a date owns that snapshot
    FOREVER — a later lane's view of the same day is silently discarded, and the
    published PIT answer for every date from then on is whatever the first writer saw.

    Which is why the permissive form was not merely loose but dead: the one production
    caller resolved its lane as ``os.environ.get("CN_LANE", "asia")``, so every context
    that leaves ``CN_LANE`` unset — a hand-run, a future render-lane adopter — arrived
    here as the asia lane itself and the gate never fired.

    The lane NAMES come from what the workflows already pass, and each resolver is
    itself defaultless: ``.github/workflows/asia-close.yml`` (band A) sets
    ``CN_LANE: asia``, read by ``scripts.build_baskets_china_ths._membership_pit_lane``;
    ``.github/workflows/daily.yml`` (engine job) sets ``COLLECT_LANE: nightly``, read by
    ``scripts.build_baskets._membership_pit_lane``.  Every other context resolves None
    and lands on the refusal below.
    """
    want = SUITE_LANE.get(suite)
    if want is not None and lane == want:
        return True
    log.info("basket_membership_pit: %s REFUSED (lane=%r, suite %s is advanced only by "
             "lane %r) — one collection lane per suite is the sole advancer of the PIT "
             "store", what, lane, suite, want)
    return False


def _append_rows(suite: str, rows: list[dict]) -> int:
    """Append keep-FIRST; zero means a real no-op, failures are typed exceptions."""
    prior = read_history(suite, strict=True, include_collection_records=True)
    if not rows:
        return 0
    new = pd.DataFrame(rows, columns=list(COLUMNS))
    # Incoming repetitions retain the established keep-FIRST append convention;
    # duplicate keys already stored are refused because their custody is ambiguous.
    _validate_history(new.drop_duplicates(subset=list(KEY), keep="first"), suite)
    before = len(prior)
    cols = list(dict.fromkeys([*COLUMNS, *prior.columns]))
    combined = pd.concat(
        [prior.reindex(columns=cols), new.reindex(columns=cols)], ignore_index=True,
    ).drop_duplicates(subset=list(KEY), keep="first")
    combined = combined.sort_values(list(KEY), kind="stable").reset_index(drop=True)
    _validate_history(combined, suite)
    added = int(len(combined) - before)
    if not added:
        return 0
    p = history_path(suite)
    tmp = None
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=p.parent, prefix=p.name + ".", suffix=".tmp",
                                         delete=False) as staged:
            tmp = Path(staged.name)
        combined.to_parquet(tmp, index=False)
        os.replace(tmp, p)
    except Exception as exc:  # noqa: BLE001 — preserve the previous destination
        raise HistoryWriteError(f"PIT append failed for {suite}: {exc}") from exc
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
    return added


def append_snapshot(suite: str, *, asof: str | None = None,
                    lane: str | None = None,
                    collection_receipts: list[dict] | None = None) -> dict:
    """Stamp today's membership of ``suite`` into the PIT history.

    Content-deduped: a snapshot_date is stamped only when the membership set
    differs from the newest one stored.  Keep-first on
    ``(snapshot_date, basket_id, ticker)`` makes a same-day re-run a no-op even
    when the content check is bypassed.  Never raises.
    """
    result = {"suite": suite, "written": False, "rows_added": 0,
              "snapshot_date": None, "reason": None}
    if not _lane_ok(lane, f"{suite} snapshot", suite=suite):
        result["reason"] = f"lane={lane}"
        return result
    try:
        prior = read_history(suite, strict=True, include_collection_records=True)
    except HistoryIntegrityError as exc:
        return _failed_result(result, exc)
    doc = _read_json(membership_path(suite))
    if not _baskets(doc):
        result["reason"] = "membership.json missing or empty"
        log.warning("basket_membership_pit: %s — %s", suite, result["reason"])
        return result

    date = _text(asof) or pd.Timestamp.utcnow().strftime("%Y-%m-%d")
    result["snapshot_date"] = date
    if not prior.empty and (prior["snapshot_date"].astype(str) == date).any():
        result["reason"] = "date already stamped"
        return result
    try:
        if collection_receipts is not None and not isinstance(collection_receipts, list):
            raise HistoryIntegrityError("collection receipts must be a list or null")
        rows = _qualified_rows(doc, date, suite, collection_receipts or [])
    except (HistoryIntegrityError, TypeError, ValueError) as exc:
        return _failed_result(result, HistoryIntegrityError(str(exc)))
    if not rows:
        result["reason"] = "empty membership has no qualified collection receipt"
        return result
    last_date, last_sha = _latest_sha(prior)
    sha = members_sha(doc)
    if collection_receipts is None and last_sha is not None and last_sha == sha:
        result["reason"] = f"membership unchanged since {last_date}"
        log.info("basket_membership_pit: %s — %s (dedup skip)", suite, result["reason"])
        return result

    try:
        added = _append_rows(suite, rows)
    except (HistoryIntegrityError, HistoryWriteError) as exc:
        return _failed_result(result, exc)
    result["written"] = added > 0
    result["rows_added"] = added
    log.info("basket_membership_pit: %s stamped %s (+%d rows)", suite, date, added)
    return result


def backfill_from_json_snapshots(suite: str, *, lane: str | None = None) -> dict:
    """Seed the history from the dated JSON side-cars already on disk.

    ``data/baskets_china_ths/snapshots/YYYY-MM-DD.json`` predates this store and
    holds the only two real PIT snapshots the program has (the 2026-06-30 /
    2026-07-08 pair whose 7.7% member-slot drift is §2.12's evidence).  Reading
    them in costs one pass and is what lets the store answer PIT questions from
    its first night instead of from its birth date.  Keep-first, so this is
    idempotent and can never overwrite a stamped day.
    """
    result = {"suite": suite, "dates": [], "rows_added": 0,
              "unparsed": [], "reason": None}
    if not _lane_ok(lane, f"{suite} backfill", suite=suite):
        result["reason"] = f"lane={lane}"
        return result
    try:
        prior = read_history(suite, strict=True, include_collection_records=True)
    except HistoryIntegrityError as exc:
        return _failed_result(result, exc)
    files = dated_snapshots(suite)
    if not files:
        result["reason"] = "no dated JSON snapshots"
        return result
    have = set(prior["snapshot_date"].astype(str))
    concepts = _concept_index(suite)
    rows: list[dict] = []
    for f in files:
        if f.stem in have:
            continue
        doc = _read_json(f)
        members = _members_from_membership(doc)
        shape = SHAPE_MEMBERSHIP
        if not members:
            # Older side-cars are the raw vendor concept dump, not a
            # membership.json copy. Read them rather than dropping half the
            # evidence pair — see _members_from_concept_dump for the bound.
            members = _members_from_concept_dump(doc, concepts)
            shape = SHAPE_CONCEPT_DUMP
        if not members:
            # A dated file we could not read is a HOLE in the record. It must
            # never vanish silently — a store that quietly covers less than it
            # appears to is worse than one that covers nothing.
            result["unparsed"].append(f.name)
            log.warning("basket_membership_pit: %s snapshot %s matched no known "
                        "shape — NOT backfilled", suite, f.name)
            continue
        rows.extend(_rows_from_members(members, f.stem, suite, shape))
        result["dates"].append(f.stem)
    if not rows:
        result["reason"] = "already covered" if not result["unparsed"] else "no readable snapshot"
        return result
    try:
        result["rows_added"] = _append_rows(suite, rows)
    except (HistoryIntegrityError, HistoryWriteError) as exc:
        return _failed_result(result, exc)
    log.info("basket_membership_pit: %s backfilled %s (+%d rows%s)",
             suite, ",".join(result["dates"]), result["rows_added"],
             f", {len(result['unparsed'])} unparsed" if result["unparsed"] else "")
    return result


def append_all(*, asof: str | None = None, lane: str | None = None,
               suites: tuple[str, ...] = SUITES) -> dict:
    """Backfill + stamp each suite in ``suites``. The single nightly entry point.

    ``lane`` is threaded straight through to both writers and is FAIL-CLOSED there
    (see ``_lane_ok``): omit it and nothing is written, in any suite.

    ``suites`` defaults to the CN pair — the asia lane's call, unchanged.  The US
    nightly passes ``SUITES_US``.  It is a parameter rather than a global sweep
    because the lane gate is per-suite: a single call naming one lane can only
    ever advance the suites that lane owns, so sweeping all three from either
    nightly would log two guaranteed refusals every run and train the reader to
    ignore the refusal line that matters.
    """
    out: dict = {}
    for suite in suites:
        try:
            backfill = backfill_from_json_snapshots(suite, lane=lane)
            if backfill.get("error"):
                out[suite] = {"error": backfill["error"], "backfill": backfill}
                continue
            snap = append_snapshot(suite, asof=asof, lane=lane)
            out[suite] = {"backfill": backfill, "snapshot": snap}
            if snap.get("error"):
                out[suite]["error"] = snap["error"]
        except Exception as exc:  # noqa: BLE001 — one suite never breaks the other
            log.warning("basket_membership_pit: %s failed (%s)", suite, exc)
            out[suite] = {"error": f"{type(exc).__name__}"}
    return out


# ---------------------------------------------------------------------------
# Reader
# ---------------------------------------------------------------------------

def _active_at(row: pd.Series, date: str) -> bool:
    """Was this member row in force on ``date``?

    Uses the source's OWN ``added``/``removed`` dates, which is what makes a
    read BETWEEN two snapshots correct rather than merely nearest-neighbour.
    A blank/absent date is treated as "no constraint" — never as an exclusion.
    """
    added = _text(row.get("added"))
    removed = _text(row.get("removed"))
    if added and added > date:
        return False
    return not (removed and removed <= date)



def membership_intervals_from_history(history, *, suite: str = SUITE_THS,
                                     include_receipt_refs: bool = False) -> list[dict]:
    """Single PIT-owner interpretation shared by its public and graph readers.

    Legacy rows keep their per-basket observed-snapshot meaning. Versioned positive
    rows prove presence only; only a qualified collection marker can prove absence.
    removed/added retain source windows, with opening never earlier than observation.
    """
    frame = history.copy() if isinstance(history, pd.DataFrame) else pd.DataFrame(list(history))
    if "suite" not in frame:
        frame["suite"] = suite
    if frame.empty:
        return []
    for col in COLUMNS:
        if col not in frame:
            frame[col] = None
    _validate_history(frame, suite)
    result = []
    for basket, group in frame.groupby("basket_id", sort=True):
        active = {}
        for day, peers in group.groupby("snapshot_date", sort=True):
            markers = _collection_records(peers)
            members = _member_records(peers)
            legacy = members["record_kind"].isna().all() and not members.empty
            complete = not markers.empty or legacy
            closure_id = None if markers.empty else markers.iloc[0]["collection_id"]
            current = {r["ticker"]: r for r in members.to_dict("records")}
            for ticker, interval in list(active.items()):
                # A previously known prospective end remains historical truth.
                # Once elapsed, a later positive opens its own observed interval;
                # it never cancels the old end or invents presence across the gap.
                if interval["valid_to"] is not None and interval["valid_to"] <= day:
                    active.pop(ticker)
                    continue
                observed = current.get(ticker)
                removed = _text(observed.get("removed")) if observed else None
                if removed and removed <= day:
                    end = max(interval["valid_from"], removed)
                elif ticker not in current and complete:
                    end = day
                else:
                    continue
                interval.update(valid_to=end, closed_by=day)
                if include_receipt_refs:
                    interval["closing_collection_id"] = closure_id
                    interval["closure_basis"] = "removed" if removed else (
                        "complete_collection" if closure_id else "legacy_snapshot")
                active.pop(ticker)
            for ticker, row in current.items():
                if ticker in active:
                    continue
                removed = _text(row.get("removed"))
                added = _text(row.get("added"))
                start = max(day, added) if added else day
                if removed and removed <= start:
                    continue
                interval = dict(basket_id=basket, ticker=ticker, valid_from=start,
                                valid_to=removed, source_shape=row["source_shape"],
                                closed_by=day if removed else None)
                if include_receipt_refs:
                    interval.update(opening_collection_id=_text(row.get("collection_id")),
                                    closing_collection_id=_text(row.get("collection_id")) if removed else None,
                                    closure_basis="removed" if removed else None)
                result.append(interval)
                # A future removed date is a known source window. It stays in
                # active state until a later receipt passes or changes that window.
                active[ticker] = interval
    return sorted(result, key=lambda iv: (iv["valid_from"], iv["basket_id"], iv["ticker"]))


def _members_asof_versioned(out: dict, covered: pd.DataFrame, date: str) -> dict:
    basket = out["basket_id"]
    out.update(collection_state="UNAVAILABLE", collection_receipt=None,
               last_qualified_collection=None, collection_observation_scope="UNAVAILABLE")
    rows = covered[covered["basket_id"] == basket]
    if rows.empty:
        out.update(basis=_BASIS_UNKNOWN, note="no basket-scoped observation")
        return out
    intervals = membership_intervals_from_history(covered, suite=out["suite"])
    out.update(pit=True, basis=_BASIS_PIT,
               snapshot_date=str(rows["snapshot_date"].max()),
               source_shape=SHAPE_MEMBERSHIP)
    out["members"] = sorted({iv["ticker"] for iv in intervals
                              if iv["basket_id"] == basket
                              and iv["valid_from"] <= date
                              and (iv["valid_to"] is None or iv["valid_to"] > date)})
    markers = _collection_records(rows)
    latest = str(rows["snapshot_date"].max())
    current_markers = markers[markers["snapshot_date"].astype(str).eq(latest)]
    current_receipt = (json.loads(current_markers.iloc[0]["collection_receipt"])
                       if not current_markers.empty else None)
    previous_receipt = (json.loads(markers.sort_values("snapshot_date").iloc[-1]["collection_receipt"])
                        if not markers.empty else None)
    out["collection_state"] = (current_receipt["collection_state"]
                               if current_receipt is not None else "UNAVAILABLE")
    out["collection_receipt"] = current_receipt
    out["last_qualified_collection"] = previous_receipt
    out["collection_observation_scope"] = (
        "LATEST_SOURCE_OBSERVATION" if latest == str(covered["snapshot_date"].max())
        else "PRIOR_BASKET_OBSERVATION")
    out["note"] = ("qualified collection for the exact disclosed basket observation; daily effective query"
                   if current_receipt is not None else "carried positive observations; latest completeness unavailable")
    return out


def members_asof(basket_id: str, date: str, *, suite: str = SUITE_THS) -> dict:
    """Members of ``basket_id`` in force on ``date`` — WITH its membership basis.

    Returns ``{basket_id, suite, asof, members, pit, basis, snapshot_date,
    source_shape, note}``.

    ``pit`` is the contract.  ``True`` means the answer came from a stored
    snapshot dated ≤ ``date`` (point-in-time, safe to measure on).  ``False``
    means the store does not cover ``date`` — the history is forward-only from
    its birth — and the answer is the CURRENT membership applied backward, which
    is exactly the look-ahead basis §2.12 flagged.  A caller that measures on a
    ``pit=False`` answer is contaminating its own study; the flag exists so that
    is a decision, never an accident.

    ``source_shape`` is the SECOND basis, and it matters for the same reason.
    The earliest side-car is the raw vendor concept dump (every name on the
    board); every later one is the seeded membership (the capped subset the
    engine actually tracks).  Both are true about their own population, but they
    are not the same population, so differencing across the boundary measures
    the seeding cap as well as real membership churn.  ``note`` says so
    explicitly whenever the resolved snapshot's shape is not the store's newest.
    Never raises.
    """
    date = str(date)
    out = {"basket_id": str(basket_id), "suite": suite, "asof": date,
           "members": [], "pit": False, "basis": _BASIS_CURRENT,
           "snapshot_date": None, "source_shape": None, "note": ""}
    try:
        df = read_history(suite, include_collection_records=True)
        covered = df[df["snapshot_date"].astype(str) <= date] if not df.empty else df
        # Collection records are basket-scoped. A newer collection of A says
        # nothing about uncollected B; never use a global date as deletion proof.
        if not covered.empty and covered["record_kind"].notna().any():
            return _members_asof_versioned(out, covered, date)
        if not covered.empty:
            snap = str(covered["snapshot_date"].astype(str).max())
            rows = covered[
                (covered["snapshot_date"].astype(str) == snap)
                & (covered["basket_id"].astype(str) == str(basket_id))
            ]
            out.update(snapshot_date=snap, basis=_BASIS_PIT, pit=True)
            if rows.empty:
                # The snapshot is real and does NOT contain this basket. Say which
                # of the two very different things that means.
                if str(basket_id) in _baskets(_read_json(membership_path(suite))):
                    out["note"] = f"basket not present in the {snap} snapshot"
                else:
                    out.update(pit=False, basis=_BASIS_UNKNOWN,
                               note=f"unknown basket_id for suite {suite}")
                return out
            shape = _text(rows.iloc[0].get("source_shape")) or SHAPE_MEMBERSHIP
            out["source_shape"] = shape
            newest = _text(
                df.sort_values("snapshot_date").iloc[-1].get("source_shape")
            ) or SHAPE_MEMBERSHIP
            if shape != newest:
                out["note"] = (
                    f"snapshot {snap} is the {shape} population, the store's newest "
                    f"is {newest} — differencing across that boundary also measures "
                    "the seeding cap, not membership churn alone"
                )
            out["members"] = sorted({
                str(r["ticker"]) for _i, r in rows.iterrows() if _active_at(r, date)
            })
            return out

        # ---- uncovered: fall back to CURRENT membership, flagged ----
        doc = _read_json(membership_path(suite))
        basket = _baskets(doc).get(str(basket_id))
        first = str(df["snapshot_date"].astype(str).min()) if not df.empty else None
        if not isinstance(basket, dict):
            out.update(basis=_BASIS_UNKNOWN,
                       note=f"unknown basket_id for suite {suite}")
            return out
        out["members"] = sorted({
            t for t in (
                _text(m.get("ticker")) or _text(m.get("code"))
                for m in (basket.get("members") or []) if isinstance(m, dict)
            ) if t
        })
        out["note"] = (
            f"PIT history starts {first}; {date} predates coverage — current "
            "membership applied backward (look-ahead basis)"
            if first else
            "no PIT history yet — current membership applied backward "
            "(look-ahead basis)"
        )
        return out
    except Exception as exc:  # noqa: BLE001 — a reader never raises into a build
        log.warning("basket_membership_pit: members_asof failed (%s)", exc)
        out["note"] = f"read failed ({type(exc).__name__})"
        return out


def coverage(suite: str = SUITE_THS) -> dict:
    """Compact store description: {suite, snapshots, first, last, rows}."""
    df = read_history(suite)
    if df.empty:
        return {"suite": suite, "snapshots": 0, "first": None, "last": None, "rows": 0}
    dates = sorted(set(df["snapshot_date"].astype(str)))
    return {"suite": suite, "snapshots": len(dates), "first": dates[0],
            "last": dates[-1], "rows": len(df)}
