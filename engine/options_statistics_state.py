"""Prospective descriptive counts carried by the incumbent Flow transaction.

No acquisition, persistence, publication or cross-cycle deduplication lives here.
The caller supplies novel canonical rows BEFORE quote/sign/notability filtering
and must commit the returned state atomically with its sequence highwater.
The producer integration is opt-in and disabled by default. Source integration
does not authorize installation or activation.
"""

from copy import deepcopy
from datetime import date, timezone
from decimal import (Context, Decimal, DivisionByZero, InvalidOperation, Overflow,
                     ROUND_HALF_EVEN, localcontext)
import re

from engine import options_statistics as measurement


SCHEMA = "options.observed_statistics_state/v1"
_COUNTERS = ("input_row_count", "rejected_row_count", "duplicate_row_count",
             "conflicting_identity_count", "ambiguous_row_count",
             "source_input_row_count", "source_rejected_row_count",
             "source_non_novel_row_count")
_ARITHMETIC = Context(prec=1000, rounding=ROUND_HALF_EVEN,
                      Emin=-999999, Emax=999999, capitals=1, clamp=0,
                      flags=[], traps=[InvalidOperation, DivisionByZero, Overflow])


def _clock(value):
    parsed = measurement._clock(value)
    if parsed is None:
        raise ValueError("observation clock must be timezone aware")
    return parsed.astimezone(timezone.utc).isoformat()


def _bucket():
    return {"print_count": 0, "contract_volume": 0,
            "premium_qualified_print_count": 0, "premium_decimal": "0"}


def _root(clock):
    return {"first_observed_at": clock, "last_observed_at": clock,
            "first_trade_at": None, "last_trade_at": None,
            **{key: 0 for key in _COUNTERS}, "totals": _bucket(),
            "rights": {key: _bucket() for key in ("C", "P")},
            "locations": {key: _bucket() for key in measurement.LOCATIONS},
            "venues": {}}


def _validate_bucket(bucket):
    if type(bucket) is not dict or set(bucket) != set(_bucket()):
        raise ValueError("invalid statistics bucket")
    for key in ("print_count", "contract_volume", "premium_qualified_print_count"):
        if type(bucket[key]) is not int or bucket[key] < 0:
            raise ValueError("invalid statistics count")
    count = bucket["print_count"]
    qualified = bucket["premium_qualified_print_count"]
    if qualified > count or bucket["contract_volume"] < count:
        raise ValueError("inconsistent statistics count")
    raw = bucket["premium_decimal"]
    if type(raw) is not str or len(raw) > 2048:
        raise ValueError("invalid premium decimal")
    try:
        value = Decimal(raw)
    except Exception as exc:
        raise ValueError("invalid premium decimal") from exc
    if not value.is_finite() or value < 0 or (qualified == 0) != (value == 0):
        raise ValueError("inconsistent premium subtotal")
    if not count and bucket["contract_volume"]:
        raise ValueError("volume without prints")


def _validate(state):
    if type(state) is not dict or set(state) != {
        "schema", "session_date", "first_observed_at", "last_observed_at", "roots"
    } or state["schema"] != SCHEMA:
        raise ValueError("invalid statistics state")
    session = state["session_date"]
    if type(session) is not str or date.fromisoformat(session).isoformat() != session:
        raise ValueError("invalid session")
    start, end = _clock(state["first_observed_at"]), _clock(state["last_observed_at"])
    if start > end or type(state["roots"]) is not dict or not state["roots"]:
        raise ValueError("invalid coverage")
    for name, root in state["roots"].items():
        if type(name) is not str or re.fullmatch(r"[A-Z0-9.^=-]+", name) is None:
            raise ValueError("invalid root")
        if type(root) is not dict or set(root) != set(_root(start)):
            raise ValueError("invalid root state")
        first, last = _clock(root["first_observed_at"]), _clock(root["last_observed_at"])
        if not start <= first <= last <= end:
            raise ValueError("inconsistent root coverage")
        for key in _COUNTERS:
            if type(root[key]) is not int or root[key] < 0:
                raise ValueError("invalid population counter")
        _validate_bucket(root["totals"])
        count = root["totals"]["print_count"]
        if root["input_row_count"] != sum((count, root["rejected_row_count"],
                root["duplicate_row_count"], root["ambiguous_row_count"])):
            raise ValueError("population does not reconcile")
        if root["source_input_row_count"] != sum((root["input_row_count"],
                root["source_rejected_row_count"], root["source_non_novel_row_count"])):
            raise ValueError("source acquisition counts do not reconcile")
        if root["ambiguous_row_count"] < 2 * root["conflicting_identity_count"]:
            raise ValueError("inconsistent ambiguity counter")
        if count:
            if not _clock(root["first_trade_at"]) <= _clock(root["last_trade_at"]) <= last:
                raise ValueError("invalid source clock range")
        elif root["first_trade_at"] is not None or root["last_trade_at"] is not None:
            raise ValueError("source clock without prints")
        for dimension, keys in (("rights", {"C", "P"}),
                                ("locations", set(measurement.LOCATIONS)),
                                ("venues", None)):
            partition = root[dimension]
            if type(partition) is not dict or (keys is not None and set(partition) != keys):
                raise ValueError("invalid partition")
            if dimension == "venues" and any(type(k) is not str or not (
                k == "UNKNOWN" or k.startswith("int:") or k.startswith("str:")
            ) for k in partition):
                raise ValueError("invalid opaque venue")
            for bucket in partition.values():
                _validate_bucket(bucket)
            for key in ("print_count", "contract_volume", "premium_qualified_print_count"):
                if sum(bucket[key] for bucket in partition.values()) != root["totals"][key]:
                    raise ValueError("partition does not reconcile")
            if sum((Decimal(v["premium_decimal"]) for v in partition.values()), Decimal(0)) != Decimal(root["totals"]["premium_decimal"]):
                raise ValueError("premium partition does not reconcile")


def _fingerprint(row):
    # Compare relevant semantic payload, including quotes/terms. An identity with
    # conflicting payload is unavailable, never an arbitrary first-wins print.
    values = [measurement._number(row["price"]), row["size"],
              _clock(row["trade_timestamp"]), measurement._venue(row.get("exchange"))]
    for key in ("bid", "ask", "premium_multiplier"):
        number = measurement._number(row.get(key))
        values.append(number)
    quote = measurement._clock(row.get("quote_timestamp"))
    values.extend((quote.astimezone(timezone.utc).isoformat() if quote else None,
                   row.get("premium_basis") == "qualified_contract_terms"))
    return tuple(values)


def _add(bucket, row, premium):
    bucket["print_count"] += 1
    bucket["contract_volume"] += row["size"]
    if premium is not None:
        bucket["premium_qualified_print_count"] += 1
        bucket["premium_decimal"] = str(Decimal(bucket["premium_decimal"]) + premium)


def advance_statistics(prior, rows, *, session_date, root, observed_at,
                       source_rejected_row_count=0, source_non_novel_row_count=0):
    """Advance a copy on caller-deduplicated rows; exclude in-batch ambiguities.

    A missing statistics key starts prospective coverage without resetting the
    caller's prior sequence state. Observation time never becomes a source date.
    Identical duplicate rows count once within this call; across calls the
    incumbent producer MUST supply only novel rows. No second dedup store exists.
    Source acquisition counters count received rows across poll batches (including
    repeat observations), not unique prints. They preserve prefilter failures
    and prior-highwater exclusions separately from the admitted population.
    """
    if type(rows) is not list:
        raise TypeError("rows must be a list")
    for value in (source_rejected_row_count, source_non_novel_row_count):
        if type(value) is not int or value < 0:
            raise ValueError("invalid source acquisition counter")
    if type(root) is not str or re.fullmatch(r"[A-Z0-9.^=-]+", root) is None:
        raise ValueError("invalid root")
    if type(session_date) is not str or date.fromisoformat(session_date).isoformat() != session_date:
        raise ValueError("invalid session")
    clock = _clock(observed_at)
    with localcontext(_ARITHMETIC):
        if prior is None:
            state = {"schema": SCHEMA, "session_date": session_date,
                     "first_observed_at": clock, "last_observed_at": clock, "roots": {}}
        else:
            _validate(prior)
            if prior["session_date"] != session_date:
                raise ValueError("session mismatch")
            previous_root = prior["roots"].get(root)
            if previous_root is not None and clock < _clock(previous_root["last_observed_at"]):
                raise ValueError("backward root observation clock")
            state = deepcopy(prior)
        # Concurrent root fetches can complete out of requested processing order.
        # Root clocks stay monotonic; global bounds describe actual observations.
        state["first_observed_at"] = min(state["first_observed_at"], clock)
        state["last_observed_at"] = max(state["last_observed_at"], clock)
        target = state["roots"].setdefault(root, _root(clock))
        target["last_observed_at"] = clock
        target["input_row_count"] += len(rows)
        target["source_input_row_count"] += len(rows) + source_rejected_row_count + source_non_novel_row_count
        target["source_rejected_row_count"] += source_rejected_row_count
        target["source_non_novel_row_count"] += source_non_novel_row_count
        groups = {}
        for row in rows:
            try:
                valid = measurement._valid(row)
            except (ValueError, OverflowError, InvalidOperation):
                valid = False
            if not valid or row["root"] != root or _clock(row["trade_timestamp"]) > clock:
                target["rejected_row_count"] += 1
                continue
            identity = (row["root"], row["expiration"], measurement._number(row["strike"]), row["right"], row["sequence"])
            groups.setdefault(identity, []).append(row)
        for group in groups.values():
            if len({_fingerprint(row) for row in group}) != 1:
                target["conflicting_identity_count"] += 1
                target["ambiguous_row_count"] += len(group)
                continue
            row = group[0]
            target["duplicate_row_count"] += len(group) - 1
            premium, location, venue = (measurement._premium(row), measurement._location(row),
                                        measurement._venue(row.get("exchange")))
            for bucket in (target["totals"], target["rights"][row["right"]],
                           target["locations"][location], target["venues"].setdefault(venue, _bucket())):
                _add(bucket, row, premium)
            trade = _clock(row["trade_timestamp"])
            target["first_trade_at"] = min(target["first_trade_at"] or trade, trade)
            target["last_trade_at"] = max(target["last_trade_at"] or trade, trade)
        _validate(state)
        return state


def statistics_snapshot(state):
    """Project measured roots only. No whole-session, market-share or intent claim."""
    if state is None:
        return {"schema": "options.observed_statistics_snapshot/v1", "status": "UNAVAILABLE", "roots": None}
    with localcontext(_ARITHMETIC):
        _validate(state)
        out = deepcopy(state)
        out["schema"] = "options.observed_statistics_snapshot/v1"
        out["status"] = "OBSERVED"
        out["population"] = "prospective_observed_source_valid_novel_prints"
        out["coverage"] = "caller_selected_roots_not_whole_market_or_whole_session"
        out["continuity"] = "observed_poll_batches_continuous_session_coverage_not_established"
        out["source_counter_basis"] = "received_rows_across_poll_batches_including_repeated_observations"
        for root in out["roots"].values():
            for bucket in [root["totals"], *root["rights"].values(), *root["locations"].values(), *root["venues"].values()]:
                premium = Decimal(bucket.pop("premium_decimal"))
                bucket.update(measurement._finish({**bucket, "_premium": premium}))
            count = root["totals"]["print_count"]
            root["nbbo_print_coverage"] = (count - root["locations"]["UNKNOWN"]["print_count"]) / count if count else None
            root["venue_print_coverage"] = (count - root["venues"].get("UNKNOWN", {"print_count": 0})["print_count"]) / count if count else None
            root["status"] = (
                "OBSERVED" if count else
                "OBSERVED_EMPTY" if not root["source_input_row_count"] else
                "NO_VALID_SOURCE_ROWS" if root["source_rejected_row_count"] == root["source_input_row_count"] else
                "NO_NEW_VALID_ROWS" if not root["input_row_count"] else
                "NO_UNAMBIGUOUS_VALID_ROWS"
            )
        return out
