"""Portfolio brief snapshot context — the opt-in ``snapshot-v1`` witness producer.

The producer half of the accepted Portfolio brief snapshot contract
(``docs/verification/portfolio-brief-snapshot-20261102/PLAN.md``). The Terminal
is the sole canonical normalizer and book-key owner; this module supplies the
EVIDENCE it needs and refuses to supply evidence it cannot prove.

WHAT THIS IS
------------
One bounded, owner-filtered, count-proved read of ``portfolio_positions``
supplies BOTH the rows the unchanged composer is called with AND the witness
that describes them. There is no second positions read, no legacy loader call,
no cached brief and no caller-supplied key anywhere in the bound path: the
witness and the composed brief come from the same captured rows, frozen for the
request.

WHAT THIS IS NOT
----------------
It is not a second book identity. There is no Python canonical hash here — the
Terminal derives its own ``portfolioBookKey`` from its own canonical read. This
module refuses to EMIT a witness it cannot prove, and it never rewrites a value
into a reading of its own.

THE PROJECTION-COMPATIBILITY GATE
----------------------------------
Terminal's ``rowToPosition`` and the Python composer's ``_normalize_holdings``
read the same row. Where they disagree, the two surfaces would describe
different books from the same database, and a witness that hid the difference
would be worse than no witness. So this module computes BOTH readings and
refuses any row whose two readings differ (see :func:`check_row_compatible`).

The Terminal reading is a faithful reproduction of Terminal's own projection
(read-only contract reference: ``terminal/lib/portfolio.ts`` at commit
``70ebc639e0a6795f8bc100008fa609406db72f3f``). It is used ONLY to COMPARE. The
currency receipt is deliberately NOT interpreted here: Terminal owns the
currency projection, so the receipt is preserved verbatim and the Terminal
derives the same currency from the same bytes.

THE SHARED FIXTURE
------------------
``tests/fixtures/portfolio_brief_context/projection_cases.json`` pins the
agreement from the other side. Its ``terminal`` block is the Terminal's real
``rowToPosition`` output and its ``composer`` block is the frozen composer's
own reading, so the fixture is a contract between two independent
authorities rather than a restatement of this module.
"""
from __future__ import annotations

import copy
import math
import re
import urllib.parse
from dataclasses import dataclass
from typing import Any, Callable, NoReturn

# ── contract constants ────────────────────────────────────────────────────────

#: The opt-in header. Its presence selects a response contract; it grants no
#: authority, carries no owner, and changes nothing about authentication.
SNAPSHOT_CONTEXT_HEADER = "X-Mastermind-Portfolio-Context"

#: The only supported contract version.
SNAPSHOT_CONTEXT_VALUE = "snapshot-v1"

#: The witness schema carried in the response's ``portfolio_context``.
WITNESS_SCHEMA = "portfolio_snapshot_witness.v1"

#: The hard cap on one snapshot read. A book larger than this cannot be read
#: completely, so it is refused rather than partially witnessed.
MAX_SNAPSHOT_ROWS = 1000

#: The exact columns the witness carries — Terminal's ``POSITION_FIELDS``, so
#: the witness and the Terminal's canonical read describe the same row.
POSITION_FIELDS = (
    "id,ticker,shares,entry_price,entry_currency,entry_currency_basis,"
    "entry_date,notes,status,created_at"
)

#: The population names. ``positions`` and ``watchlist_union`` are distinct
#: books; a watchlist union can never qualify as a positions book.
POPULATION_POSITIONS = "positions"
POPULATION_WATCHLIST_UNION = "watchlist_union"

#: The reasons a bound request cannot produce a witness. They are part of the
#: wire contract: the consumer must be able to tell "unknown" from "empty".
REASON_TRANSPORT = "transport_failure"
REASON_STORE_NOT_CONFIGURED = "store_not_configured"
REASON_MISSING_COUNT = "missing_count"
REASON_OVER_LIMIT = "over_limit"
REASON_COUNT_MISMATCH = "count_mismatch"
REASON_INVALID_RANGE = "invalid_range"
REASON_NONZERO_START = "nonzero_start_range"
REASON_DUPLICATE_IDS = "duplicate_ids"
REASON_NOT_JSON_SAFE = "not_json_safe"
REASON_UNSUPPORTED_MAGNITUDE = "unsupported_numeric_magnitude"
REASON_NON_FINITE = "non_finite_numeric"
REASON_TICKER_MISMATCH = "ticker_mismatch"
REASON_SHARES_MISMATCH = "shares_mismatch"
REASON_ENTRY_PRICE_MISMATCH = "entry_price_mismatch"
REASON_DROPPED_BY_TERMINAL = "row_dropped_by_terminal"
REASON_WATCHLIST_PREFIX = "watchlist_"
#: The watchlist union's own reasons are the same vocabulary under a prefix
#: ("watchlist_transport_failure", "watchlist_count_mismatch", ...), so the
#: consumer can tell WHICH read failed without parsing prose.
REASON_WATCHLIST_UNAVAILABLE = "watchlist_unavailable"


class SnapshotUnavailable(Exception):
    """A bound request could not be witnessed. Carries a stable reason code.

    The reason is a CONTRACT, not a log string: it is returned to the caller
    so the consumer can tell "the book is unknown" from "the book is empty".
    The exception never carries a row, a holding or an owner id.
    """

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


# ── Terminal projection (read-only contract reference) ───────────────────────
#
# Reproduced from terminal/lib/portfolio.ts @ 70ebc639e0a6795f8bc100008fa609406db72f3f:
#
#   normalizeTicker  value.trim().toUpperCase(), refused when blank, longer
#                    than MAX_TICKER_LEN (128), or holding a C0/DEL character
#   normalizeNumeric undefined -> absent, null -> null, number -> finite or
#                    invalid, string -> trim, blank -> null, Number(raw) ->
#                    finite or invalid, anything else -> invalid
#   normalizeStatus  "closed" ONLY for a trimmed+lowercased "closed"
#   rowToPosition    null when the id or the ticker is unusable
#
# Used only to COMPARE against the Python composer. Nothing here rewrites a
# value that reaches the wire.

_TERMINAL_MAX_TICKER_LEN = 128
_TERMINAL_CONTROL_CHARS = re.compile(r"[\u0000-\u001f\u007f]")

# ECMAScript's String.prototype.trim removes exactly WhiteSpace + LineTerminator.
# It is NOT the same set as Python's str.strip(): JS also strips U+FEFF, and
# Python also strips U+001C-U+001F and U+0085. A ticker that differs between
# the two is a genuine divergence between the readers, and is refused.
_JS_TRIM_CHARS = (
    "\u0009\u000a\u000b\u000c\u000d\u0020\u00a0\u1680"
    "\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a"
    "\u2028\u2029\u202f\u205f\u3000\ufeff"
)

# ECMAScript StringToNumber: the literal forms Number() accepts.
_JS_HEX_LITERAL = re.compile(r"0[xX][0-9a-fA-F]+")
_JS_OCTAL_LITERAL = re.compile(r"0[oO][0-7]+")
_JS_BINARY_LITERAL = re.compile(r"0[bB][01]+")
_JS_DECIMAL_LITERAL = re.compile(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")


def _js_trim(value: str) -> str:
    """ECMAScript String.prototype.trim."""
    return value.strip(_JS_TRIM_CHARS)


def _js_number(raw: str) -> float | None:
    """ECMAScript StringToNumber for the literal forms ``Number()`` accepts.

    Returns None for the forms JS turns into NaN. Note the asymmetry that
    matters here: JS accepts ``0x``/``0o``/``0b`` integer literals, which
    Python's ``float()`` rejects, and Python accepts PEP 515 underscores
    (``"1_0"``), which JS turns into NaN. Both are divergences between the two
    readers and both are refused by the gate.
    """
    if raw == "":
        return 0.0
    if raw in ("Infinity", "+Infinity"):
        return math.inf
    if raw == "-Infinity":
        return -math.inf
    for pattern, base in ((_JS_HEX_LITERAL, 16), (_JS_OCTAL_LITERAL, 8),
                          (_JS_BINARY_LITERAL, 2)):
        if pattern.fullmatch(raw):
            try:
                return float(int(raw, base))
            except OverflowError:
                return math.inf
    if _JS_DECIMAL_LITERAL.fullmatch(raw):
        return float(raw)
    return None


def terminal_ticker(value: Any) -> str | None:
    """Terminal's ``normalizeTicker`` — the canonical ticker reading."""
    ticker = _js_trim(value).upper() if isinstance(value, str) else ""
    if (not ticker or len(ticker) > _TERMINAL_MAX_TICKER_LEN
            or _TERMINAL_CONTROL_CHARS.search(ticker)):
        return None
    return ticker


def terminal_text(value: Any) -> str | None:
    """Terminal's ``text()`` — a non-empty string, or null. Never trimmed."""
    return value if isinstance(value, str) and value else None


def terminal_numeric(value: Any) -> float | None:
    """Terminal's ``normalizeNumeric`` collapsed through ``rowToPosition``.

    ``rowToPosition`` maps every non-"value" outcome to null, so a boolean, a
    non-finite number, an unparseable string and an object all read as null
    here — while Python's ``float(True)`` is 1.0 and ``float("1_0")`` is 10.0.
    The gate compares the two readings; it does not pick one.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        # typeof "boolean" -> invalid -> null.
        return None
    if isinstance(value, (int, float)):
        try:
            number = float(value)
        except OverflowError:
            return None
        return number if math.isfinite(number) else None
    if isinstance(value, str):
        raw = _js_trim(value)
        if not raw:
            return None
        parsed = _js_number(raw)
        return parsed if (parsed is not None and math.isfinite(parsed)) else None
    return None


def terminal_status(value: Any) -> str:
    """Terminal's ``normalizeStatus``: closed ONLY for trimmed+lowercased closed."""
    if isinstance(value, str) and _js_trim(value).lower() == "closed":
        return "closed"
    return "open"


def terminal_position(row: dict) -> dict | None:
    """Terminal's ``rowToPosition`` — the canonical read-side projection.

    ``entryCurrency`` is deliberately ABSENT. Terminal owns the currency
    projection (it needs the exact ISO code list and the receipt rule); this
    module preserves the receipt verbatim instead of re-deriving a currency it
    could only get wrong. The composer never reads a currency, so nothing the
    composer consumes depends on it.
    """
    position_id = terminal_text(row.get("id"))
    ticker = terminal_ticker(row.get("ticker"))
    if position_id is None or ticker is None:
        return None
    return {
        "id": position_id,
        "ticker": ticker,
        "shares": terminal_numeric(row.get("shares")),
        "entryPrice": terminal_numeric(row.get("entry_price")),
        "entryDate": terminal_text(row.get("entry_date")),
        "notes": terminal_text(row.get("notes")),
        "status": terminal_status(row.get("status")),
        "createdAt": terminal_text(row.get("created_at")),
    }


# ── Python composer reading (frozen engine/portfolio_brief.py) ───────────────
#
# Reproduced from engine/portfolio_brief.py::_normalize_holdings:
#
#   t = str(raw or "").strip().upper()
#   sh = float(shares) if shares is not None else None
#   ep = float(entry) if entry is not None else None
#   except (TypeError, ValueError): sh = ep = None
#
# OverflowError is NOT caught by the composer, so a value that overflows would
# make it raise rather than degrade. It is reported separately so the gate can
# refuse the row instead of handing the composer a value that explodes.

_OVERFLOW = object()


def composer_ticker(value: Any) -> str:
    """The frozen composer's own ticker reading."""
    return str(value or "").strip().upper()


def composer_numeric(value: Any) -> Any:
    """The frozen composer's own numeric reading.

    Returns None for "absent", the float for a usable value, and the
    ``_OVERFLOW`` sentinel for a magnitude the composer cannot represent.
    """
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
    except OverflowError:
        return _OVERFLOW


def composer_row(row: dict) -> dict:
    """The reading the composer would take of one row.

    ``ticker`` is the name the composer would keep (empty means it keeps
    none); ``shares``/``entry_price`` are the values it would coerce.
    """
    return {
        "ticker": composer_ticker(row.get("ticker")),
        "shares": composer_numeric(row.get("shares")),
        "entry_price": composer_numeric(row.get("entry_price")),
    }


# ── the gate ──────────────────────────────────────────────────────────────────


def check_row_compatible(row: dict) -> None:
    """Raise :class:`SnapshotUnavailable` unless the two readers agree.

    A row is compatible when the Python composer and the Terminal's
    ``rowToPosition`` would describe the SAME holding from it:

    * the composer keeps a name only when the ticker is non-blank after
      ``str().strip().upper()``; the Terminal keeps a position only when the
      id and the ticker are both usable. A name the composer counts and the
      Terminal cannot see is a disagreement about the book, so it is refused;
    * a row both readers drop (a blank ticker) is compatible — neither claims
      a holding;
    * the ticker strings must be identical;
    * each numeric column must read the SAME finite number on both sides, or
      be absent on both sides.

    The gate never repairs a row. It refuses it.
    """
    reading = composer_row(row)
    name = reading["ticker"]
    for value in (reading["shares"], reading["entry_price"]):
        if value is _OVERFLOW:
            raise SnapshotUnavailable(REASON_UNSUPPORTED_MAGNITUDE)
        if value is not None and isinstance(value, float) and not math.isfinite(value):
            raise SnapshotUnavailable(REASON_NON_FINITE)

    position = terminal_position(row)
    if position is None:
        if name:
            raise SnapshotUnavailable(REASON_DROPPED_BY_TERMINAL)
        return

    if name != position["ticker"]:
        raise SnapshotUnavailable(REASON_TICKER_MISMATCH)
    for value, projected, reason in (
        (reading["shares"], position["shares"], REASON_SHARES_MISMATCH),
        (reading["entry_price"], position["entryPrice"], REASON_ENTRY_PRICE_MISMATCH),
    ):
        if value is None and projected is None:
            continue
        if value is None or projected is None:
            raise SnapshotUnavailable(reason)
        if float(value) != float(projected):
            raise SnapshotUnavailable(reason)


def is_json_safe(value: Any) -> bool:
    """True when the value can be serialised as strict JSON.

    A non-finite float would be written as ``Infinity``/``NaN``, which is not
    JSON and which the Terminal's ``JSON.parse`` refuses. A witness that
    cannot be parsed is not a witness.
    """
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(is_json_safe(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return all(is_json_safe(v) for v in value)
    return True


# ── the capture ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PortfolioSnapshot:
    """One witnessed, owner-scoped book capture.

    ``rows`` holds the raw captured rows verbatim (including the currency
    receipt); ``composer_inputs`` holds the exact rows the unchanged composer
    is called with. Both come from the SAME capture — that is the whole point.
    """

    owner_id: str
    population: str
    rows: tuple[dict, ...]
    selected_position_ids: tuple[str, ...]
    composer_inputs: tuple[dict, ...]
    composer_input_source: str
    completeness: dict


CountAwareReader = Callable[..., dict]


def _default_reader(path: str, *, limit: int) -> dict:
    """The gateway's count-aware read, on the gateway's own transport config."""
    from engine.neuralweb.brain_gateway import _sb_get_count_aware  # noqa: PLC0415
    return _sb_get_count_aware(path, limit=limit)


def _positions_path(uid: str) -> str:
    quoted = urllib.parse.quote(str(uid))
    return (f"portfolio_positions?user_id=eq.{quoted}"
            f"&select={POSITION_FIELDS}&order=created_at")


def _watchlists_path(uid: str) -> str:
    quoted = urllib.parse.quote(str(uid))
    return f"watchlists?user_id=eq.{quoted}&select=id&order=position"


def _watchlist_symbols_path(list_ids: list[str]) -> str:
    return (f"watchlist_symbols?watchlist_id=in.({','.join(list_ids)})"
            f"&select=symbol,position&order=position")


def _validated_read(read: Any, limit: int, *, reason_prefix: str = "") -> tuple[list[dict], dict]:
    """Turn one count-aware read into (rows, completeness) or refuse it.

    The proof is entirely inside ONE response: the exact count and the
    returned range must both be present, the range must start at zero and
    must describe exactly the rows that came back, and the count must equal
    the number of rows returned. A response that fails any of these is not a
    complete read and is not witnessed — it is not patched up from a second
    query, because two separately timed reads are not one snapshot.
    """
    def refuse(reason: str) -> NoReturn:
        raise SnapshotUnavailable(f"{reason_prefix}{reason}")

    if not isinstance(read, dict) or not read.get("ok"):
        error = (read or {}).get("error") if isinstance(read, dict) else None
        if error == "store_not_configured":
            # A global condition, not a property of this one read.
            raise SnapshotUnavailable(REASON_STORE_NOT_CONFIGURED)
        refuse(REASON_TRANSPORT)
    rows = read.get("rows")
    if not isinstance(rows, list):
        refuse(REASON_TRANSPORT)
    count = read.get("count")
    first = read.get("range_first")
    last = read.get("range_last")
    returned = len(rows)

    if count is None:
        # No Content-Range: the response never stated how many rows exist, so
        # completeness cannot be proved. An absent count is NOT zero.
        refuse(REASON_MISSING_COUNT)
    if returned > limit or count > limit:
        refuse(REASON_OVER_LIMIT)
    if count != returned:
        # More rows exist than came back: the read was truncated.
        refuse(REASON_COUNT_MISMATCH)
    if returned == 0:
        if first is not None or last is not None:
            refuse(REASON_INVALID_RANGE)
    else:
        if first is None or last is None:
            refuse(REASON_INVALID_RANGE)
        if first != 0:
            refuse(REASON_NONZERO_START)
        if last != returned - 1:
            refuse(REASON_INVALID_RANGE)

    for row in rows:
        if not isinstance(row, dict):
            refuse(REASON_TRANSPORT)
        if not is_json_safe(row):
            refuse(REASON_NOT_JSON_SAFE)

    completeness = {
        "exact_count": count,
        "range_first": first,
        "range_last": last,
        "returned_count": returned,
        "max_rows": limit,
        "complete": True,
    }
    return rows, completeness


def _select_open_positions(rows: list[dict]) -> tuple[list[dict], list[str]]:
    """The open, positionable rows — Terminal's canonical membership.

    Terminal separates open from closed with ``normalizeStatus``: ``closed``
    ONLY for a trimmed+lowercased "closed"; everything else — including a null
    or an absent status — reads as OPEN. The composer only ever sees the
    open rows, exactly as the legacy loader only ever fed it open rows.
    """
    selected: list[dict] = []
    ids: list[str] = []
    for row in rows:
        if terminal_status(row.get("status")) == "closed":
            continue
        position = terminal_position(row)
        if position is None:
            # A row the Terminal cannot turn into a position contributes no
            # holding. The gate has already refused every row where that
            # would DISAGREE with the composer (a name the composer counts
            # and the Terminal cannot see), so reaching here means both
            # readers drop the row and neither claims a holding.
            continue
        selected.append(row)
        ids.append(position["id"])
    return selected, ids


def _watchlist_union(uid: str, *, limit: int, reader: CountAwareReader) -> tuple[list[dict], dict]:
    """The watchlist union, read only AFTER a proven zero-open result.

    This never re-reads positions: the zero-open fact came from the same
    complete capture that produced the witness. The union is explicitly its
    own population and can never qualify as a positions book.
    """
    lists, lists_completeness = _validated_read(
        reader(_watchlists_path(uid), limit=limit), limit,
        reason_prefix=REASON_WATCHLIST_PREFIX)
    list_ids = [str(row.get("id")) for row in lists
                if isinstance(row, dict) and row.get("id") is not None]
    symbols: list[dict] = []
    symbols_completeness = {"exact_count": 0, "range_first": None, "range_last": None,
                            "returned_count": 0, "max_rows": limit, "complete": True}
    if list_ids:
        symbols, symbols_completeness = _validated_read(
            reader(_watchlist_symbols_path(list_ids), limit=limit), limit,
            reason_prefix=REASON_WATCHLIST_PREFIX)
    seen: set[str] = set()
    union: list[dict] = []
    for row in symbols:
        symbol = row.get("symbol") if isinstance(row, dict) else None
        if symbol and symbol not in seen:
            seen.add(symbol)
            union.append({"ticker": symbol, "shares": None, "entry_price": None})
    completeness = {"lists": lists_completeness, "symbols": symbols_completeness,
                    "reads": 2 if list_ids else 1}
    return union, completeness


def capture_snapshot(uid: str, *, limit: int = MAX_SNAPSHOT_ROWS,
                     reader: CountAwareReader | None = None) -> PortfolioSnapshot:
    """Capture ONE complete owner-filtered book and derive the witness inputs.

    Raises :class:`SnapshotUnavailable` when the capture cannot be proved
    complete, when a row would be read differently by the two readers, or when
    the store did not answer. The caller turns that into an explicit
    unavailable response — never an empty book.
    """
    read = reader or _default_reader

    # The ONE positions read. It supplies the witness rows AND the composer
    # rows; nothing else reads positions in this path.
    rows, completeness = _validated_read(read(_positions_path(uid), limit=limit), limit)

    seen_ids: set[str] = set()
    for row in rows:
        position_id = terminal_text(row.get("id"))
        if position_id is not None:
            if position_id in seen_ids:
                raise SnapshotUnavailable(REASON_DUPLICATE_IDS)
            seen_ids.add(position_id)

    for row in rows:
        # The gate covers the rows the composer is called with: the OPEN ones.
        # A closed row never reaches the composer, so the two readers cannot
        # disagree about it — Terminal's own projection of it is deterministic,
        # and the raw row is carried in the witness unchanged.
        if terminal_status(row.get("status")) == "closed":
            continue
        check_row_compatible(row)

    selected, selected_ids = _select_open_positions(rows)
    completeness["open_count"] = sum(
        1 for row in rows if terminal_status(row.get("status")) != "closed")
    completeness["selected_count"] = len(selected_ids)
    completeness["positions_reads"] = 1
    completeness["source"] = "portfolio_positions"

    if selected:
        composer_inputs = [{"ticker": row.get("ticker"),
                            "shares": row.get("shares"),
                            "entry_price": row.get("entry_price")}
                           for row in selected]
        population = POPULATION_POSITIONS
        composer_input_source = POPULATION_POSITIONS
        completeness["watchlist"] = None
    else:
        # PROVEN zero open positions — from the same complete capture, with no
        # second positions query. The union is a DIFFERENT population and says
        # so; it never claims a positions book.
        union, watchlist_completeness = _watchlist_union(uid, limit=limit, reader=read)
        composer_inputs = union
        population = POPULATION_WATCHLIST_UNION
        composer_input_source = POPULATION_WATCHLIST_UNION
        completeness["watchlist"] = watchlist_completeness
        completeness["watchlist_reads"] = watchlist_completeness["reads"]

    return PortfolioSnapshot(
        owner_id=str(uid),
        population=population,
        rows=tuple(copy.deepcopy(rows)),
        selected_position_ids=tuple(selected_ids),
        composer_inputs=tuple(copy.deepcopy(composer_inputs)),
        composer_input_source=composer_input_source,
        completeness=completeness,
    )


def composer_inputs(snapshot: PortfolioSnapshot) -> list[dict]:
    """A fresh, mutable copy of the rows the composer is called with.

    A copy, so that anything the composer does to the rows it is handed can
    never reach the witness: the witness describes the CAPTURED rows, not the
    rows after they were handed to a function.
    """
    return [copy.deepcopy(row) for row in snapshot.composer_inputs]


def build_witness(snapshot: PortfolioSnapshot) -> dict:
    """The ``portfolio_context`` block carried by an opted-in response.

    Server-to-server only: it holds the owner's private rows, so it is never
    logged and never placed in a URL.
    """
    return {
        "schema": WITNESS_SCHEMA,
        "owner_id": snapshot.owner_id,
        "population": snapshot.population,
        "rows": [copy.deepcopy(row) for row in snapshot.rows],
        "selected_position_ids": list(snapshot.selected_position_ids),
        "composer_input_source": snapshot.composer_input_source,
        "composer_inputs": [copy.deepcopy(row) for row in snapshot.composer_inputs],
        "completeness": copy.deepcopy(snapshot.completeness),
    }


# ── header handling ───────────────────────────────────────────────────────────


def snapshot_requested(header_value: str | None) -> bool:
    """True when the caller opted into the snapshot contract.

    An absent header is an ordinary request: the legacy loader, the legacy
    cache and the legacy response are untouched.
    """
    return isinstance(header_value, str) and header_value.strip() == SNAPSHOT_CONTEXT_VALUE


def snapshot_header_unsupported(header_value: str | None) -> bool:
    """True when the header carries a contract this build does not implement.

    A caller that asks for a witness it cannot get must be told, rather than
    quietly handed an ordinary response it would read as a witness.
    """
    if not isinstance(header_value, str):
        return False
    text = header_value.strip()
    return bool(text) and text != SNAPSHOT_CONTEXT_VALUE
