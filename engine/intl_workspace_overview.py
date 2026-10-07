"""Deterministic projection from accepted international records to overview data."""

from copy import deepcopy
from datetime import datetime
from fractions import Fraction
from math import isfinite
import re


_BASIS_TO_LEG = {"local": "local", "usd_unhedged": "usd"}
_LEG_UNITS = {
    "local": "percent",
    "usd": "percent",
    "fx_contribution": "percentage_points",
}
_QUALITIES = {"qualified", "stale", "missing", "denied", "failed", "unsupported", "unknown"}
_DISCLOSURES = {"allowed", "denied", "unknown"}
_EMPTY_REASONS = {"no_markets", "no_numerical_coverage", "invalid_geometry"}


class _InvalidRecords(ValueError):
    pass


class _InvalidContext(ValueError):
    pass


class _InvalidQualification(ValueError):
    pass


def _plain_json(value, numeric=False):
    if value is None:
        return not numeric
    if type(value) is bool:
        return not numeric
    if type(value) is str:
        return not numeric
    if type(value) is int:
        return True
    if type(value) is float:
        return isfinite(value)
    if type(value) is dict:
        return not numeric and all(type(key) is str and _plain_json(item) for key, item in value.items())
    if type(value) is list:
        return not numeric and all(_plain_json(item) for item in value)
    return False


def _require_plain(value, error, message, numeric=False):
    try:
        valid = _plain_json(value, numeric=numeric)
    except RecursionError:
        valid = False
    if not valid:
        raise error(message)


def _member(value, allowed):
    return type(value) is str and value in allowed


def _is_number(value):
    return type(value) is int or (type(value) is float and isfinite(value))


def _is_text(value):
    return type(value) is str and bool(value) and not any(
        ord(char) <= 0x1F or 0x7F <= ord(char) <= 0x9F for char in value
    )


def _closed(value, keys, error, exact=True):
    message = (
        "invalid_request" if error is ValueError
        else "invalid_records" if error is _InvalidRecords
        else "invalid_qualification"
    )
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise error(message)
    if (exact and len(value) != len(keys)) or not all(key in value for key in keys):
        raise error(message)


class _Stamp:
    __slots__ = ("tzinfo", "_key")

    def __init__(self, tzinfo, seconds, fraction):
        extra = fraction // 1
        self.tzinfo = tzinfo
        self._key = (seconds + int(extra), fraction - extra)

    def __gt__(self, other):
        return self._key > other._key


def _ascii_fraction(digits):
    if not digits.isascii() or not digits.isdigit():
        raise ValueError("invalid_fraction")
    return Fraction(int(digits), 10 ** len(digits))


def _component_fraction(component):
    for index, char in enumerate(component):
        if char in ".,":
            return _ascii_fraction(component[index + 1:])
    return Fraction(0)


def _parse_hh_mm_ss_fraction(tstr):
    fraction = _component_fraction(tstr)
    tstr = tstr.split(".", 1)[0].split(",", 1)[0]
    length = len(tstr)
    comps = [0, 0, 0]
    pos = 0
    has_sep = False
    for comp in range(3):
        if length - pos < 2:
            raise ValueError("Incomplete time component")
        comps[comp] = int(tstr[pos:pos + 2])
        pos += 2
        next_char = tstr[pos:pos + 1]
        if comp == 0:
            has_sep = next_char == ":"
        if not next_char or comp >= 2:
            break
        if has_sep and next_char != ":":
            raise ValueError("Invalid time separator: %c" % next_char)
        pos += has_sep
    return comps[0], comps[1], comps[2], fraction


def _chronology(value):
    tstr = value.split("T", 1)[1]
    tz_pos = tstr.find("-") + 1 or tstr.find("+") + 1 or tstr.find("Z") + 1
    validation_value = value
    if tz_pos and tstr[tz_pos - 1] in "+-":
        # Python3.12 accepted short fractional offsets as fractional SECONDS;
        # Python3.14 requires an explicit seconds component. Normalize only the
        # validator input; chronology and disclosed strings retain exact input.
        match = re.fullmatch(r"([0-9]{2})(?::?([0-9]{2}))?([.,][0-9]+)", tstr[tz_pos:])
        if match:
            prefix = value[:len(value) - len(tstr) + tz_pos]
            validation_value = prefix + match[1] + ":" + (match[2] or "00") + ":00" + match[3]
    parsed = datetime.fromisoformat(validation_value)
    timestr = tstr[:tz_pos - 1] if tz_pos > 0 else tstr
    time_frac = _component_fraction(timestr)
    seconds = parsed.toordinal() * 86400 + parsed.hour * 3600 + parsed.minute * 60 + parsed.second
    if parsed.tzinfo is None:
        return _Stamp(None, seconds, time_frac)
    if tz_pos == len(tstr) and tstr.endswith("Z"):
        offset_s, offset_f = 0, Fraction(0)
    else:
        sign = -1 if tstr[tz_pos - 1] == "-" else 1
        hour, minute, second, frac = _parse_hh_mm_ss_fraction(tstr[tz_pos:])
        offset_s = sign * (hour * 3600 + minute * 60 + second)
        offset_f = sign * frac
    return _Stamp(parsed.tzinfo, seconds - offset_s, time_frac - offset_f)


def _parse_datetime(value, error):
    if not isinstance(value, str) or "T" not in value:
        raise error("invalid_records" if error is _InvalidRecords else "invalid_qualification")
    try:
        return _chronology(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise error("invalid_records" if error is _InvalidRecords else "invalid_qualification") from exc


def _validate_window(window, required=True, error=_InvalidRecords):
    if window is None:
        if required:
            raise error("invalid_records" if error is _InvalidRecords else "invalid_qualification")
        return
    _closed(
        window,
        ["start", "end", "calendar_policy", "endpoint_observations"],
        error,
        exact=True,
    )
    if not _is_text(window["calendar_policy"]):
        raise error("invalid_records" if error is _InvalidRecords else "invalid_qualification")
    observations = window["endpoint_observations"]
    _closed(
        observations,
        ["price_start", "price_end", "fx_start", "fx_end"],
        error,
    )
    start = _parse_datetime(window["start"], error)
    end = _parse_datetime(window["end"], error)
    if (start.tzinfo is None) != (end.tzinfo is None) or start > end:
        raise error("invalid_records" if error is _InvalidRecords else "invalid_qualification")
    for key in ("price_start", "price_end", "fx_start", "fx_end"):
        if observations[key] is None:
            continue
        contributor = _parse_datetime(observations[key], error)
        endpoint = start if key.endswith("_start") else end
        if (contributor.tzinfo is None) != (endpoint.tzinfo is None) or contributor > endpoint:
            raise error("invalid_records" if error is _InvalidRecords else "invalid_qualification")


def _validate_leg(leg, expected_unit):
    _closed(leg, ["value", "unit", "numerical_status", "reason", "window"], _InvalidRecords)
    if leg["unit"] != expected_unit or not _member(leg["numerical_status"], {"available", "unavailable"}):
        raise _InvalidRecords("invalid_records")
    value = leg["value"]
    if leg["numerical_status"] == "available":
        if not _is_number(value) or leg["reason"] is not None:
            raise _InvalidRecords("invalid_records")
        _validate_window(leg["window"], required=True)
        return
    if value is not None or not _is_text(leg["reason"]):
        raise _InvalidRecords("invalid_records")
    _validate_window(leg["window"], required=False)


def _validate_raw(records, roster_ids):
    _closed(
        records,
        ["source_reference", "source_reference_reason", "numerical_status", "reason", "records"],
        _InvalidRecords,
        exact=False,
    )
    if records["source_reference"] is not None and not _is_text(records["source_reference"]):
        raise _InvalidRecords("invalid_records")
    if records["source_reference_reason"] is not None and not _is_text(records["source_reference_reason"]):
        raise _InvalidRecords("invalid_records")
    if not _member(records["numerical_status"], {"available", "partial", "unavailable"}):
        raise _InvalidRecords("invalid_records")
    if records["reason"] is not None and not _is_text(records["reason"]):
        raise _InvalidRecords("invalid_records")
    if not isinstance(records["records"], list):
        raise _InvalidRecords("invalid_records")
    identities = {}
    seen = set()
    horizons = set()
    for record in records["records"]:
        _closed(
            record,
            [
                "market_id", "index_id", "index_label", "fx_id", "fx_quote_orientation",
                "horizon", "requested_observations", "return_basis", "qualification",
                "local", "usd", "fx_contribution",
            ],
            _InvalidRecords,
            exact=False,
        )
        identity_fields = ["market_id", "index_id", "index_label", "fx_id", "horizon"]
        if not all(_is_text(record[field]) for field in identity_fields):
            raise _InvalidRecords("invalid_records")
        if record["market_id"] not in roster_ids:
            raise _InvalidRecords("invalid_records")
        pair = (record["market_id"], record["horizon"])
        if pair in seen:
            raise _InvalidRecords("invalid_records")
        seen.add(pair)
        horizons.add(record["horizon"])
        if not _member(record["fx_quote_orientation"], {"local_per_USD", "USD_per_local"}):
            raise _InvalidRecords("invalid_records")
        if record["requested_observations"] is not None and not (
            type(record["requested_observations"]) is int and record["requested_observations"] > 0
        ):
            raise _InvalidRecords("invalid_records")
        if record["return_basis"] != "price" or record["qualification"] != "not_evaluated":
            raise _InvalidRecords("invalid_records")
        identity = tuple(record[field] for field in ["index_id", "index_label", "fx_id", "fx_quote_orientation"])
        if identities.setdefault(record["market_id"], identity) != identity:
            raise _InvalidRecords("invalid_records")
        _validate_leg(record["local"], "percent")
        _validate_leg(record["usd"], "percent")
        _validate_leg(record["fx_contribution"], "percentage_points")
    if not records["records"] and (
        records["numerical_status"] != "unavailable" or records["reason"] not in _EMPTY_REASONS
    ):
        raise _InvalidRecords("invalid_records")
    return horizons


def _validate_inputs(records, roster, context, qualifications):
    _require_plain(records, _InvalidRecords, "invalid_records")
    if type(roster) is not list or len(roster) > 32:
        raise ValueError("invalid_request")
    roster_ids = set()
    for item in roster:
        _require_plain(item, ValueError, "invalid_request")
        _closed(item, ["market_id", "name_en", "name_zh"], ValueError)
        if not all(_is_text(item[key]) for key in ("market_id", "name_en", "name_zh")):
            raise ValueError("invalid_request")
        if item["market_id"] in roster_ids:
            raise ValueError("invalid_request")
        roster_ids.add(item["market_id"])
    _require_plain(context, ValueError, "invalid_request")
    _closed(context, ["horizon", "currency_basis", "return_basis", "source_reference"], ValueError)
    if not _is_text(context["horizon"]) or not _member(context["currency_basis"], _BASIS_TO_LEG) or context["return_basis"] != "price":
        raise ValueError("invalid_context")
    if context["source_reference"] is not None and not _is_text(context["source_reference"]):
        raise ValueError("invalid_context")
    horizons = _validate_raw(records, roster_ids)
    if records["records"] and context["horizon"] not in horizons:
        raise _InvalidContext("invalid_context")
    if context["source_reference"] != records["source_reference"]:
        raise _InvalidContext("invalid_context")
    if qualifications is not None:
        if type(qualifications) is not list:
            raise ValueError("invalid_qualification")
        for receipt in qualifications:
            _require_plain(receipt, _InvalidQualification, "invalid_qualification")
            _validate_receipt(receipt)
    return roster_ids


def _validate_receipt(receipt):
    _closed(receipt, ["binding", "owner_ref", "policy_ref", "decision_ref", "quality", "reason", "disclosure"], _InvalidQualification)
    if not all(_is_text(receipt[field]) for field in ("owner_ref", "policy_ref", "decision_ref")):
        raise _InvalidQualification("invalid_qualification")
    if not _member(receipt["quality"], _QUALITIES):
        raise _InvalidQualification("invalid_qualification")
    if receipt["quality"] == "qualified" and receipt["reason"] is not None:
        raise _InvalidQualification("invalid_qualification")
    if receipt["quality"] != "qualified" and not _is_text(receipt["reason"]):
        raise _InvalidQualification("invalid_qualification")
    _closed(receipt["disclosure"], ["metadata", "value"], _InvalidQualification)
    if not _member(receipt["disclosure"]["metadata"], _DISCLOSURES) or not _member(receipt["disclosure"]["value"], _DISCLOSURES):
        raise _InvalidQualification("invalid_qualification")
    binding = receipt["binding"]
    _closed(
        binding,
        [
            "source_reference", "market_id", "index_id", "fx_id", "horizon",
            "currency_basis", "return_basis", "leg", "value", "unit", "window",
        ],
        _InvalidQualification,
    )
    if binding["source_reference"] is not None and not _is_text(binding["source_reference"]):
        raise _InvalidQualification("invalid_qualification")
    if (not _member(binding["currency_basis"], _BASIS_TO_LEG)
            or binding["return_basis"] != "price"
            or not _is_text(binding["unit"])):
        raise _InvalidQualification("invalid_qualification")
    if not _member(binding["leg"], _LEG_UNITS) or binding["unit"] != _LEG_UNITS[binding["leg"]]:
        raise _InvalidQualification("invalid_qualification")
    if not all(_is_text(binding[field]) for field in ("market_id", "index_id", "fx_id", "horizon")):
        raise _InvalidQualification("invalid_qualification")
    if binding["value"] is not None and not _is_number(binding["value"]):
        raise _InvalidQualification("invalid_qualification")
    _validate_window(binding["window"], required=False, error=_InvalidQualification)


def _same(left, right):
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return set(left) == set(right) and all(_same(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(_same(a, b) for a, b in zip(left, right))
    return left == right


def _candidate_receipt(receipts, record, leg):
    for receipt in receipts:
        binding = receipt["binding"]
        if (
            binding["leg"] == leg
            and binding["market_id"] == record["market_id"]
            and binding["horizon"] == record["horizon"]
        ):
            return receipt
    return None


def _binding_matches(receipt, record, leg, context, source_reference):
    binding_values = {
        "source_reference": source_reference,
        "market_id": record["market_id"],
        "index_id": record["index_id"],
        "fx_id": record["fx_id"],
        "horizon": record["horizon"],
        "currency_basis": context["currency_basis"],
        "return_basis": context["return_basis"],
        "leg": leg,
        "value": record[leg]["value"],
        "unit": record[leg]["unit"],
        "window": record[leg]["window"],
    }
    return all(_same(receipt["binding"][field], expected) for field, expected in binding_values.items())


def _matched_receipt(receipts, record, leg, context, source_reference):
    receipt = _candidate_receipt(receipts, record, leg)
    if receipt is not None and _binding_matches(receipt, record, leg, context, source_reference):
        return receipt
    return None


def _metric_result(receipt, leg, raw_leg, source_reference):
    if receipt is None:
        return {"value": None, "unit": _LEG_UNITS[leg], "quality": "unknown", "reason": "qualification_unknown", "window": None}
    if receipt["disclosure"]["metadata"] == "denied":
        return {"value": None, "unit": _LEG_UNITS[leg], "quality": "denied", "reason": "not_disclosed", "window": None}
    if receipt["disclosure"]["metadata"] == "unknown":
        return {"value": None, "unit": _LEG_UNITS[leg], "quality": "unknown", "reason": "qualification_unknown", "window": None}
    window = deepcopy(receipt["binding"]["window"])
    if receipt["quality"] != "qualified":
        return {"value": None, "unit": _LEG_UNITS[leg], "quality": receipt["quality"], "reason": f"quality_{receipt['quality']}", "window": window}
    if receipt["disclosure"]["value"] == "denied":
        return {"value": None, "unit": _LEG_UNITS[leg], "quality": "denied", "reason": "value_denied", "window": window}
    if receipt["disclosure"]["value"] == "unknown":
        return {"value": None, "unit": _LEG_UNITS[leg], "quality": "unknown", "reason": "value_unknown", "window": window}
    if source_reference is None or receipt["binding"]["source_reference"] is None:
        return {"value": None, "unit": _LEG_UNITS[leg], "quality": "unknown", "reason": "source_unknown", "window": window}
    if raw_leg["numerical_status"] != "available" or not _is_number(receipt["binding"]["value"]) or window is None:
        return {"value": None, "unit": _LEG_UNITS[leg], "quality": "unknown", "reason": "numerical_unavailable", "window": window}
    return {"value": deepcopy(receipt["binding"]["value"]), "unit": _LEG_UNITS[leg], "quality": "qualified", "reason": None, "window": window}


def _duplicate_receipts(receipts):
    seen = set()
    for receipt in receipts:
        binding = receipt["binding"]
        key = (binding["market_id"], binding["horizon"], binding["leg"])
        if key in seen:
            raise ValueError("invalid_qualification")
        seen.add(key)


def _calculation_window(window, return_basis, currency_basis):
    if window is None:
        return None
    return (window["start"], window["end"], window["calendar_policy"], return_basis, currency_basis)


def build_overview(records, *, roster, context, qualifications=None):
    """Build a detached overview projection without invoking any producer."""
    _validate_inputs(records, roster, context, qualifications)
    if qualifications:
        _duplicate_receipts(qualifications)
    selected_leg = _BASIS_TO_LEG[context["currency_basis"]]
    horizon = context["horizon"]
    rows = []
    eligible = []
    source_disclosed = False
    selected_by_market = {}
    source_reference = records["source_reference"]
    for record in records["records"]:
        if record["horizon"] == horizon:
            selected_by_market[record["market_id"]] = record

    for slot, roster_item in enumerate(roster):
        market_id = roster_item["market_id"]
        record = selected_by_market.get(market_id)
        candidate = None if record is None or qualifications is None else _candidate_receipt(qualifications, record, selected_leg)
        selected_receipt = None
        if candidate is not None and _binding_matches(candidate, record, selected_leg, context, source_reference):
            selected_receipt = candidate
        if (
            selected_receipt is not None
            and source_reference is not None
            and selected_receipt["disclosure"]["metadata"] == "allowed"
        ):
            source_disclosed = True
        if selected_receipt is not None and selected_receipt["disclosure"]["metadata"] == "denied":
            rows.append({"slot": slot, "quality": "denied", "reason": "metadata_denied"})
            continue
        if record is None or selected_receipt is None or selected_receipt["disclosure"]["metadata"] != "allowed":
            if record is None:
                reason = "missing_record"
            elif candidate is not None and selected_receipt is None:
                reason = "binding_mismatch"
            else:
                reason = "qualification_unknown"
            rows.append({
                "slot": slot,
                "market_id": market_id,
                "name_en": roster_item["name_en"],
                "name_zh": roster_item["name_zh"],
                "quality": "unknown",
                "reason": reason,
                "metric": {"value": None, "unit": _LEG_UNITS[selected_leg],
                           "quality": "unknown", "reason": reason},
            })
            continue

        selected_metric = _metric_result(selected_receipt, selected_leg, record[selected_leg], source_reference)
        secondary = {}
        for leg in ("local", "usd", "fx_contribution"):
            receipt = _matched_receipt(qualifications or [], record, leg, context, source_reference)
            secondary[leg] = _metric_result(receipt, leg, record[leg], source_reference)
            if receipt is None and _candidate_receipt(qualifications or [], record, leg) is not None:
                secondary[leg]["reason"] = "binding_mismatch"
        row = {
            "slot": slot,
            "market_id": market_id,
            "name_en": roster_item["name_en"],
            "name_zh": roster_item["name_zh"],
            "index_id": record["index_id"],
            "index_label": record["index_label"],
            "metric": selected_metric,
            "local": secondary["local"],
            "usd": secondary["usd"],
            "fx_contribution": secondary["fx_contribution"],
        }
        rows.append(row)
        if selected_metric["quality"] == "qualified":
            eligible.append(row)

    comparable = bool(eligible) and all(
        row["metric"]["window"] is not None
        for row in eligible
    ) and len({
        _calculation_window(row["metric"]["window"], context["return_basis"], context["currency_basis"])
        for row in eligible
    }) == 1
    ordered = sorted(
        eligible,
        key=lambda row: (
            -row["metric"]["value"],
            row["market_id"],
        ),
    )
    if not eligible:
        ranking_count = 0
        focus_ids = []
        ranking_status = "unavailable"
        ranking_reason = "no_qualified_returns"
    elif not comparable:
        ranking_count = 0
        focus_ids = []
        ranking_status = "unavailable"
        ranking_reason = "unequal_windows"
    else:
        ranking_count = len(ordered)
        focus_ids = [row["market_id"] for row in (ordered if len(ordered) <= 4 else ordered[:3] + ordered[-1:])]
        ranking_status = "available"
        ranking_reason = None

    if comparable and eligible:
        positive_count = sum(row["metric"]["value"] > 0 for row in eligible)
        contribution_rows = []
        for row in eligible:
            record = selected_by_market[row["market_id"]]
            receipt = _matched_receipt(qualifications or [], record, "fx_contribution", context, source_reference)
            selected_window = _calculation_window(
                row["metric"]["window"], context["return_basis"], context["currency_basis"]
            )
            if (
                row["fx_contribution"]["quality"] == "qualified"
                and _calculation_window(
                    row["fx_contribution"]["window"], context["return_basis"], context["currency_basis"]
                ) == selected_window
            ):
                contribution_rows.append((row, receipt))
        fx_eligible_count = len(contribution_rows)
        selected_window = _calculation_window(eligible[0]["metric"]["window"], context["return_basis"], context["currency_basis"])
        detracted = [
            item for item in contribution_rows
            if item[0]["fx_contribution"]["window"] is not None
            and _calculation_window(item[0]["fx_contribution"]["window"], context["return_basis"], context["currency_basis"]) == selected_window
            and item[1]["binding"]["value"] < 0
        ]
        summary = {
            "kind": "highest_lowest_returns",
            "highest_market_id": ordered[0]["market_id"],
            "lowest_market_id": ordered[-1]["market_id"],
            "positive_count": positive_count,
            "fx_detracted_count": len(detracted) if contribution_rows else None,
            "fx_eligible_count": fx_eligible_count,
            "reason": None,
        }
    else:
        summary = {
            "kind": "unavailable",
            "highest_market_id": None,
            "lowest_market_id": None,
            "positive_count": None,
            "fx_detracted_count": None,
            "fx_eligible_count": 0,
            "reason": ranking_reason,
        }

    return {
        "context": {
            "horizon": context["horizon"],
            "currency_basis": context["currency_basis"],
            "return_basis": context["return_basis"],
            "source_reference": records["source_reference"] if source_disclosed else None,
            "source_reference_reason": None if source_disclosed else "not_disclosed_or_unknown",
        },
        "configured_count": len(roster),
        "eligible_count": len(eligible),
        "ranking_count": ranking_count,
        "ranking_status": ranking_status,
        "ranking_reason": ranking_reason,
        "focus_ids": focus_ids,
        "rows": rows,
        "summary": summary,
    }


def build_workspace_overviews(closes, *, production_inputs=None,
                              workspace_generation=None) -> dict | None:
    """Compose the new read-only view from supplied owner inputs, without a fetch.

    The legacy call retains unknown qualifications. Supplied evidence is evaluated
    only by the existing input owner. Version 2 keeps its caller-issued publication
    generation separate from each panel's nullable numerical source disclosure.
    The caller must replace its nonce on any content or disclosure change; this
    pure function owns no cross-call publication ledger. V2 requires a matching
    version-aware consumer before the builder can opt in.
    """
    import pandas as pd
    from engine import intl_inputs
    from engine.intl_performance_records import build_return_records

    supplied = production_inputs is not None
    if supplied:
        import uuid
        _require_plain(production_inputs, ValueError, 'invalid_production_inputs')
        _closed(production_inputs, ['adjustment_bases', 'source_evidence',
                                   'disclosure_decisions', 'policy_id'], ValueError)
        prefix = 'im-workspace-generation:'
        if type(workspace_generation) is not str or not workspace_generation.startswith(prefix):
            raise ValueError('invalid_workspace_generation')
        token = workspace_generation[len(prefix):]
        try:
            parsed = uuid.UUID(token)
        except (ValueError, AttributeError) as exc:
            raise ValueError('invalid_workspace_generation') from exc
        if parsed.version != 4 or str(parsed) != token:
            raise ValueError('invalid_workspace_generation')
    elif workspace_generation is not None:
        raise ValueError('generation_without_production_inputs')

    countries = intl_inputs.countries()
    roster = [{"market_id": cc, "name_en": row["name"], "name_zh": row["name_zh"]}
              for cc, row in countries.items()]
    if not roster:
        return None
    if closes is None:
        closes = pd.DataFrame(index=pd.DatetimeIndex([]))
    source_reference = None
    snapshot = None
    if supplied:
        snapshot = intl_inputs.source_snapshot(
            closes, source_reference='intl-supplied-close:pending',
            adjustment_bases=production_inputs['adjustment_bases'])
        source_reference = 'intl-supplied-close:sha256:' + snapshot['content_sha256']
        snapshot = intl_inputs.source_snapshot(
            closes, source_reference=source_reference,
            adjustment_bases=production_inputs['adjustment_bases'])
    raw = build_return_records(closes, market_ids=list(countries), source_reference=source_reference)
    horizons = list(dict.fromkeys(row["horizon"] for row in raw["records"]))
    if not horizons:
        return None  # Invalid source geometry: retain the complete legacy page.
    bases = ["usd_unhedged", "local"]
    qualifications = {basis: None for basis in bases}
    if supplied:
        for basis in bases:
            result = intl_inputs.qualify_return_records(
                raw, snapshot=snapshot,
                source_evidence=production_inputs['source_evidence'],
                disclosure_decisions=production_inputs['disclosure_decisions'],
                policy_id=production_inputs['policy_id'], currency_basis=basis)
            qualifications[basis] = result['qualifications']
    panels = []
    for horizon in horizons:
        for basis in bases:
            context = {"horizon": horizon, "currency_basis": basis,
                       "return_basis": "price", "source_reference": source_reference}
            panels.append({"context_id": "im-overview-" + str(len(panels)),
                           "overview": build_overview(raw, roster=roster,
                                                       context=context, qualifications=qualifications[basis])})
            if supplied:
                panels[-1]['generation'] = workspace_generation
    workspace = {"config": {"markets": list(countries), "horizons": horizons, "bases": bases,
                       "default_horizon": "1m" if "1m" in horizons else horizons[0],
                       "default_basis": "usd_unhedged", "source_reference": workspace_generation,
                       "anchor_ids": ["intl-legacy-research"], "library_group_ids": []},
            "panels": panels}
    if supplied:
        workspace['binding_version'] = 2
    return workspace
