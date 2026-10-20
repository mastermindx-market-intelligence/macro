"""Pure adapters for evidence consumed by the incumbent Options Hub producer.

No requests, store, rights decision, contract defaults or Greek calculations.
Acquisition time is this collector's known-by observation, never first publication.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
import re
from urllib.parse import urlsplit

ACQUISITION_COLUMN = "_theta_acquisition"
THETA_ENDPOINTS = {
    "greeks": "/v3/option/history/greeks/eod",
    "oi": "/v3/option/history/open_interest",
}
# Persist explicit request parameters only, never credentials or inferred defaults.
THETA_PARAMETERS = frozenset({"symbol", "expiration", "strike", "right", "start_date",
    "end_date", "format", "version", "annual_dividend", "annual_dividend_amount",
    "rate_type", "rate_value", "underlyer_use_nbbo", "option_use_nbbo", "max_dte", "strike_range"})


def instant(value):
    if not isinstance(value, str) or not re.search(r"(?:Z|[+-]\d\d:\d\d)$", value):
        raise ValueError("Receipt needs an aware observation clock")
    out = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if out.tzinfo is None:
        raise ValueError("Receipt needs an aware observation clock")
    return out


def theta_acquisition(path, parameters, raw, *, origin, received_at=None):
    """Called after a complete successful CSV parse. No request is made here."""
    if path not in THETA_ENDPOINTS.values() or set(parameters) - THETA_PARAMETERS:
        raise ValueError("Unsupported native acquisition parameters")
    source = urlsplit(origin)
    if (source.scheme not in ("http", "https") or not source.hostname or source.username
            or source.password or source.query or source.fragment or source.path not in ("", "/")):
        raise ValueError("Invalid acquisition origin")
    observed = received_at or datetime.now(timezone.utc).isoformat()
    instant(observed)
    return json.dumps({"schema": "thetadata.acquisition/v1", "origin": origin, "endpoint": path,
        "parameters": deepcopy(parameters), "received_at": observed,
        "response_sha256": hashlib.sha256(raw).hexdigest(),
        "availability_basis": "collector_observed_known_by",
        "historical_first_availability_established": False}, sort_keys=True, separators=(",", ":"), allow_nan=False)


def native_acquisitions(frame, root, session, kind, *, now=None):
    """Decode each repeated receipt once, requiring evidence on EVERY selected row.

    Missing/old rows or an endpoint/root/date mismatch refuse automatic composition.
    The caller still binds all selected rows and receipt text in its input digest.
    """
    if frame is None or frame.empty or ACQUISITION_COLUMN not in frame:
        return None
    column = frame[ACQUISITION_COLUMN]
    if column.isna().any() or not column.map(lambda v: isinstance(v, str)).all():
        return None
    unique = column.unique()
    if len(unique) > 1000:
        return None
    records = []
    current = instant(now) if now is not None else datetime.now(timezone.utc)
    for raw in unique:
        try:
            rec = json.loads(raw)
            if (not isinstance(rec, dict) or rec.get("schema") != "thetadata.acquisition/v1"
                    or rec.get("endpoint") != THETA_ENDPOINTS[kind]
                    or rec.get("availability_basis") != "collector_observed_known_by"
                    or rec.get("historical_first_availability_established") is not False
                    or not re.fullmatch(r"[a-f0-9]{64}", str(rec.get("response_sha256", "")))):
                return None
            observed = instant(rec.get("received_at"))
            source = urlsplit(rec.get("origin", ""))
            if (source.scheme not in ("http", "https") or not source.hostname or source.username
                    or source.password or source.query or source.fragment or source.path not in ("", "/")):
                return None
            params = rec.get("parameters")
            if not isinstance(params, dict) or set(params) - THETA_PARAMETERS or params.get("symbol") != root:
                return None
            start = str(params["start_date"]).replace("-", "")
            end = str(params["end_date"]).replace("-", "")
            if not (re.fullmatch(r"\d{8}", start) and re.fullmatch(r"\d{8}", end)
                    and start <= session.replace("-", "") <= end):
                return None
            datetime.strptime(start, "%Y%m%d")
            datetime.strptime(end, "%Y%m%d")
            if observed > current:
                return None
            records.append(rec)
        except (ValueError, TypeError, KeyError):
            return None
    return sorted(records, key=lambda r: json.dumps(r, sort_keys=True))


def massive_reference_terms(observation, root, security_id=None):
    """Map one exact retained reference response. Omissions remain omissions.

    Shares delivered do NOT establish a quotation multiplier or an all-share
    deliverable. An as_of query does NOT establish historical availability.
    """
    if not isinstance(observation, dict):
        raise ValueError("Invalid reference observation")
    cap = observation.get("capability") or {}
    if (observation.get("schema") != "options_reference_capability_observation/v1"
            or observation.get("state") != "response_observed"
            or cap.get("http_status") != 200 or cap.get("verdict") != "entitled"
            or observation.get("origin") not in ("https://api.polygon.io", "https://api.massive.com")
            or not re.fullmatch(r"[a-f0-9]{64}", str(observation.get("payload_sha256", "")))):
        raise ValueError("Reference response was not observed successfully")
    acquired = observation.get("completed_at")
    if instant(acquired) > datetime.now(timezone.utc):
        raise ValueError("Future reference observation")
    c = observation.get("contract")
    if not isinstance(c, dict) or c.get("underlying_ticker") != root:
        raise ValueError("Reference underlying mismatch")
    expiry = c.get("expiration_date")
    parsed = datetime.strptime(str(expiry), "%Y-%m-%d")
    if parsed.date().isoformat() != expiry:
        raise ValueError("Invalid reference expiry")
    right = {"call": "C", "put": "P"}.get(c.get("contract_type"))
    strike = c.get("strike_price")
    if isinstance(strike, bool) or not isinstance(strike, (float, int)) or not math.isfinite(strike) or strike <= 0 or right is None:
        raise ValueError("Invalid reference contract key")
    mills = Decimal(str(strike)) * 1000
    if mills != mills.to_integral_value() or not (0 < mills < 100_000_000):
        raise ValueError("Invalid reference strike precision")
    ticker = f"O:{root}{parsed:%y%m%d}{right}{int(mills):08d}"
    if c.get("ticker") != ticker or observation.get("path") != "/v3/reference/options/contracts/" + ticker:
        raise ValueError("Reference ticker/key mismatch")
    presence = observation.get("field_presence")
    if not isinstance(presence, dict) or any(presence.get(k) is not True for k in c):
        raise ValueError("Reference field presence mismatch")
    term = {"root": root, "expiration": expiry, "strike": strike, "right": right,
        "series_id": ticker, "terms_ref": observation["origin"] + observation["path"] + "#sha256=" + observation["payload_sha256"],
        "available_at": acquired, "availability_basis": "collector_observed_known_by"}
    if security_id:
        term["security_id"] = security_id
    for field in ("exercise_style", "shares_per_contract", "additional_underlyings", "correction", "cfi", "primary_exchange"):
        if field in c:
            term[field] = deepcopy(c[field])
    if "exercise_style" in term and term["exercise_style"] not in ("american", "bermudan", "european"):
        raise ValueError("Invalid reference exercise style")
    if "shares_per_contract" in term:
        shares = term["shares_per_contract"]
        if isinstance(shares, bool) or not isinstance(shares, (int, float)) or not math.isfinite(shares) or shares <= 0:
            raise ValueError("Invalid reference shares")
    if "additional_underlyings" in term and not isinstance(term["additional_underlyings"], list):
        raise ValueError("Invalid reference additional deliverables")
    return term
