"""Pure adapters for evidence consumed by the incumbent Options Hub producer.

No requests, store, rights decision, contract defaults or Greek calculations.
Acquisition time is this collector's known-by observation, never first publication.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
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
THETA_SNAPSHOT_ENDPOINTS = {
    "first": "/v3/option/snapshot/greeks/first_order",
    "second": "/v3/option/snapshot/greeks/second_order",
    "oi": "/v3/option/snapshot/open_interest",
}
# Persist explicit request parameters only, never credentials or inferred defaults.
THETA_PARAMETERS = frozenset({"symbol", "expiration", "strike", "right", "start_date",
    "end_date", "format", "version", "annual_dividend", "annual_dividend_amount",
    "rate_type", "rate_value", "underlyer_use_nbbo", "option_use_nbbo", "max_dte", "strike_range"})
THETA_SNAPSHOT_PARAMETERS = frozenset({"symbol", "expiration", "strike", "right", "format",
    "version", "annual_dividend", "annual_dividend_amount", "rate_type", "rate_value",
    "stock_price", "max_dte", "strike_range", "min_time", "use_market_value", "current_day_only"})


def dated_greek_request_options(root: str) -> dict:
    """Explicit shared writer opt-in; never upgrade existing rows or source rights.

    Daily and backfill writers must use the same requested version: whichever
    supplies a new day first can otherwise leave its requested version unknown.
    Empty configuration preserves all incumbent acquisition defaults.
    """
    import os
    selected = {r.strip().upper() for r in os.environ.get(
        "THETADATA_DATED_GREEKS_V1_ROOTS", "").split(",") if r.strip()}
    if selected - {"SPY", "QQQ"}:
        raise ValueError("Dated Greek version opt-in supports only SPY/QQQ")
    return {"version": "1"} if root.upper() in selected else {}


def _snapshot_calculation_provenance(path, parameters):
    if path == THETA_SNAPSHOT_ENDPOINTS["oi"]:
        return None
    version = parameters.get("version")
    if version is not None and version not in ("1", "latest"):
        raise ValueError("Unsupported requested snapshot version")
    return {"schema": "thetadata.snapshot_calculation_provenance/v1",
        "basis": "requested_parameters_and_endpoint_documentation",
        "requested_version": version, "serving_build": None,
        "tenor_policy": {"1": "provider_snapshot_fixed_0dte_0.15",
                         "latest": "provider_snapshot_latest_min_1h"}.get(version),
        "methodology_ref": "https://www.thetadata.net/docs/operations/option_snapshot_greeks_"
                           + ("first_order" if path == THETA_SNAPSHOT_ENDPOINTS["first"] else "second_order") + ".html"}


def instant(value):
    if not isinstance(value, str) or not re.search(r"(?:Z|[+-]\d\d:\d\d)$", value):
        raise ValueError("Receipt needs an aware observation clock")
    out = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if out.tzinfo is None:
        raise ValueError("Receipt needs an aware observation clock")
    return out


def theta_acquisition(path, parameters, raw, *, origin, received_at=None):
    """Called after a complete successful CSV parse. No request is made here."""
    snapshot = path in THETA_SNAPSHOT_ENDPOINTS.values()
    allowed = THETA_SNAPSHOT_PARAMETERS if snapshot else THETA_PARAMETERS
    if (path not in (*THETA_ENDPOINTS.values(), *THETA_SNAPSHOT_ENDPOINTS.values())
            or set(parameters) - allowed
            or (path in (THETA_ENDPOINTS["oi"], THETA_SNAPSHOT_ENDPOINTS["oi"]) and "version" in parameters)):
        raise ValueError("Unsupported native acquisition parameters")
    source = urlsplit(origin)
    if (source.scheme not in ("http", "https") or not source.hostname or source.username
            or source.password or source.query or source.fragment or source.path not in ("", "/")):
        raise ValueError("Invalid acquisition origin")
    observed = received_at or datetime.now(timezone.utc).isoformat()
    instant(observed)
    evidence = {"schema": "thetadata.acquisition/v1", "origin": origin, "endpoint": path,
        "parameters": deepcopy(parameters), "received_at": observed,
        "response_sha256": hashlib.sha256(raw).hexdigest(),
        "availability_basis": "collector_observed_known_by",
        "historical_first_availability_established": False}
    if snapshot:
        # A documented explicit floor remains a floor. Omitted version stays
        # unknown; this receipt never asserts an actual model/build or no-floor T.
        evidence["calculation_provenance"] = _snapshot_calculation_provenance(path, parameters)
    return json.dumps(evidence, sort_keys=True, separators=(",", ":"), allow_nan=False)


def native_snapshot_acquisitions(frame, root, kind, *, now=None):
    """Validate captured snapshot requests without promoting Greek/model semantics.

    Raw vendor clocks remain separate from collector known-by time. This adapter
    supplies no source session, economic expiry, availability before capture,
    serving model identity, rights or numerical qualification.
    """
    import pandas as pd
    if (kind not in THETA_SNAPSHOT_ENDPOINTS or frame is None or frame.empty
            or ACQUISITION_COLUMN not in frame or "root" not in frame):
        return None
    column = frame[ACQUISITION_COLUMN]
    if (column.isna().any() or not column.map(lambda v: isinstance(v, str)).all()
            or frame["root"].isna().any() or not frame["root"].eq(root).all()
            or len(column.unique()) > 1000):
        return None
    records = []
    current = instant(now) if now is not None else datetime.now(timezone.utc)
    def unique_keys(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError("Ambiguous acquisition receipt field")
            out[key] = value
        return out
    for raw in column.unique():
        if len(raw.encode("utf-8")) > 16384:
            return None
        try:
            rec = json.loads(raw, object_pairs_hook=unique_keys); path = THETA_SNAPSHOT_ENDPOINTS[kind]
            if (not isinstance(rec, dict) or rec.get("schema") != "thetadata.acquisition/v1"
                    or rec.get("endpoint") != path
                    or rec.get("availability_basis") != "collector_observed_known_by"
                    or rec.get("historical_first_availability_established") is not False
                    or not re.fullmatch(r"[a-f0-9]{64}", str(rec.get("response_sha256", "")))
                    or instant(rec.get("received_at")) > current):
                return None
            source = urlsplit(rec.get("origin", ""))
            if (source.scheme not in ("http", "https") or not source.hostname or source.username
                    or source.password or source.query or source.fragment or source.path not in ("", "/")):
                return None
            params = rec.get("parameters")
            if (not isinstance(params, dict) or set(params) - THETA_SNAPSHOT_PARAMETERS
                    or not {"symbol", "expiration", "strike"} <= set(params)
                    or params["symbol"] != root or params.get("format") != "csv"
                    or any(type(v) not in (str, int, float, bool) or
                           (type(v) is float and not math.isfinite(v)) for v in params.values())
                    or (kind == "oi" and "version" in params)
                    or rec.get("calculation_provenance") != _snapshot_calculation_provenance(path, params)):
                return None
            selected = frame.loc[column == raw]
            expiration = str(params["expiration"]).replace("-", "")
            if expiration != "*":
                if "expiration" not in selected or any(pd.Timestamp(v).strftime("%Y%m%d") != expiration for v in selected["expiration"]):
                    return None
            if params["strike"] != "*":
                if (type(params["strike"]) is bool or "strike" not in selected
                        or not selected["strike"].map(lambda v: float(v) == float(params["strike"])).all()):
                    return None
            right = params.get("right", "both")
            if right != "both" and (str(right).lower() not in ("call", "put", "c", "p")
                    or "right" not in selected or not selected["right"].astype(str).str.upper().str[0].eq(str(right).upper()[0]).all()):
                return None
            records.append(rec)
        except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
            return None
    return sorted(records, key=lambda r: json.dumps(r, sort_keys=True))


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
            if (not isinstance(params, dict) or set(params) - THETA_PARAMETERS or params.get("symbol") != root
                    or (kind == "oi" and "version" in params)):
                return None
            start = str(params["start_date"]).replace("-", "")
            end = str(params["end_date"]).replace("-", "")
            if not (re.fullmatch(r"\d{8}", start) and re.fullmatch(r"\d{8}", end)
                    and start <= session.replace("-", "") <= end):
                return None
            datetime.strptime(start, "%Y%m%d")
            datetime.strptime(end, "%Y%m%d")
            selected = frame.loc[column == raw]
            expiration = str(params.get("expiration", "*")).replace("-", "")
            if expiration != "*" and "expiration" in selected:
                if any((value.strftime("%Y%m%d") if isinstance(value, (date, datetime))
                        else str(value).replace("-", "")) != expiration for value in selected["expiration"]):
                    return None
            right = params.get("right", "both")
            if right != "both" and "right" in selected:
                if any(str(value).upper()[0] != str(right).upper()[0] for value in selected["right"]):
                    return None
            if params.get("strike", "*") != "*" and "strike" in selected:
                if any(float(value) != float(params["strike"]) for value in selected["strike"]):
                    return None
            if observed > current:
                return None
            records.append(rec)
        except (ValueError, TypeError, KeyError):
            return None
    return sorted(records, key=lambda r: json.dumps(r, sort_keys=True))


def massive_reference_terms(observation, root, security_id=None, *, contract=None, selection_params=None):
    """Map one exact retained reference response. Omissions remain omissions.

    Shares delivered do NOT establish a quotation multiplier or an all-share
    deliverable. An as_of query does NOT establish historical availability.
    """
    if not isinstance(observation, dict):
        raise ValueError("Invalid reference observation")
    cap = observation.get("capability") or {}
    if (observation.get("schema") not in ("options_reference_capability_observation/v1", "options_reference_page_observation/v1")
            or observation.get("state") != "response_observed"
            or cap.get("http_status") != 200 or cap.get("verdict") != "entitled"
            or observation.get("origin") not in ("https://api.polygon.io", "https://api.massive.com")
            or not re.fullmatch(r"[a-f0-9]{64}", str(observation.get("payload_sha256", "")))):
        raise ValueError("Reference response was not observed successfully")
    acquired = observation.get("completed_at")
    if instant(acquired) > datetime.now(timezone.utc):
        raise ValueError("Future reference observation")
    c = observation.get("contract") if contract is None else contract
    if not isinstance(c, dict):
        raise ValueError("Invalid reference contract")
    listed = contract is not None
    scope = observation.get("params", {}) if selection_params is None else selection_params
    if selection_params is not None and observation.get("schema") != "options_reference_page_observation/v1":
        raise ValueError("Selection scope is only supplied by the paged observation adapter")
    if listed and (observation.get("path") != "/v3/reference/options/contracts"
            or not isinstance(observation.get("contracts"), list) or c not in observation["contracts"]
            or scope.get("underlying_ticker") != root
            or not (scope.get("expiration_date") == c.get("expiration_date") or
                    (selection_params is not None and scope.get("expiration_date.gte") <= c.get("expiration_date", "")))):
        raise ValueError("Reference list scope mismatch")
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
    if c.get("ticker") != ticker or (not listed and observation.get("path") != "/v3/reference/options/contracts/" + ticker):
        raise ValueError("Reference ticker/key mismatch")
    presence = {k: True for k in c} if listed else observation.get("field_presence")
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


def reference_population_terms(observation, root, security_id=None):
    """Validate a complete bounded cursor chain, preserving actual page parameters.

    A page cursor carries the original filter selection. Selection scope is
    separate from each actual request query; neither is rewritten as the other.
    Digests prove consistency, not HTTP authentication or historical possession.
    """
    if (not isinstance(observation, dict) or observation.get("schema") != "options_reference_population_observation/v1"
            or observation.get("state") != "COMPLETE" or observation.get("root") != root
            or root not in {"SPY", "QQQ"} or observation.get("historical_first_availability_established") is not False
            or observation.get("origin") not in {"https://api.polygon.io", "https://api.massive.com"}
            or observation.get("path") != "/v3/reference/options/contracts"):
        raise ValueError("Reference population observation is not complete")
    session = observation.get("source_session")
    date.fromisoformat(session)
    scope = observation.get("initial_params")
    expected = dict(underlying_ticker=root, as_of=session, **{"expiration_date.gte": session},
                    expired="false", order="asc", sort="ticker", limit=1000)
    if scope != expected:
        raise ValueError("Reference population selection scope mismatch")
    pages = observation.get("pages")
    if not isinstance(pages, list) or not 0 < len(pages) <= 20:
        raise ValueError("Reference page count outside bound")
    query, seen, cursors, total_bytes, count, terms, refs = scope, set(), set(), 0, 0, [], []
    for index, page in enumerate(pages):
        if not isinstance(page, dict) or page.get("params") != query:
            raise ValueError("Reference page chain mismatch")
        marker = json.dumps(query, sort_keys=True, separators=(",", ":"))
        if marker in seen:
            raise ValueError("Reference cursor cycle")
        seen.add(marker)
        if index:
            if query['cursor'] in cursors:raise ValueError("Reference cursor cycle")
            cursors.add(query['cursor'])
        cap = page.get("capability") or {}
        evidence = cap.get("evidence") or {}
        size = evidence.get("response_bytes")
        if (type(size) is not int or not 0 < size <= 1024*1024
                or page.get("schema") != "options_reference_page_observation/v1"
                or page.get("origin") != observation["origin"] or page.get("path") != observation["path"]
                or page.get("state") != "response_observed"
                or page.get("payload_sha256") != evidence.get("response_sha256")
                or page.get("completed_at") != evidence.get("completed_at")
                or not isinstance(page.get("contracts"), list) or len(page["contracts"]) > 1000):
            raise ValueError("Reference page evidence invalid")
        instant(page["completed_at"])
        if instant(page["completed_at"]) > datetime.now(timezone.utc):
            raise ValueError("Future reference page")
        total_bytes += size;count += len(page["contracts"])
        if total_bytes > 8*1024*1024 or count > 20000:
            raise ValueError("Reference population exceeds response bounds")
        # Validate even an empty final page's capability/digest.
        if (cap.get("http_status") != 200 or cap.get("verdict") != "entitled"
                or not re.fullmatch(r"[a-f0-9]{64}", str(page.get("payload_sha256", "")))):
            raise ValueError("Reference page not admitted")
        for contract in page["contracts"]:
            terms.append(massive_reference_terms(page, root, security_id, contract=contract, selection_params=scope))
        refs.append(dict(params=deepcopy(page["params"]), response_sha256=page["payload_sha256"],
                         completed_at=page["completed_at"], response_bytes=size, contracts=len(page["contracts"])))
        query = page.get("next_params")
        if index == len(pages)-1:
            if query is not None:
                raise ValueError("Truncated reference page chain")
        elif (not isinstance(query, dict) or not isinstance(query.get("cursor"), str)
                or not 0 < len(query["cursor"]) <= 8192 or set(query)-set(scope)-{"cursor"}
                or any(str(v) != str(scope[k]) for k,v in query.items() if k != "cursor")):
            raise ValueError("Reference next-page selection widened")
    return terms, refs


MASSIVE_REFERENCE_METHODOLOGY = "https://massive.com/docs/rest/options/contracts/contract-overview"
OCC_ETF_SPEC = "https://www.theocc.com/clearance-and-settlement/clearing/etf-options"


def ordinary_spy_terms(term):
    """Compatibility wrapper for the existing explicit SPY interpretation."""
    return ordinary_etf_terms(term, root='SPY')


def ordinary_etf_terms(term, *, root):
    """Rule-backed interpretation of an exact ordinary supported ETF reference observation.

    Raw absence remains absent. The provider promises to report extra deliverables;
    no such report plus100shares supports this narrow standard-ETF interpretation.
    Correction omission remains unknown. No expiry instant or Greek model is inferred.
    """
    out = deepcopy(term)
    try:
        reference = urlsplit(str(term.get("terms_ref", "")))
    except ValueError:
        return out
    endpoint = "/v3/reference/options/contracts"
    # The mapper builds this exact origin/path/hash from the observed chain.
    # A prefix lookalike or conflicting explicit economics is not a rule-backed
    # ordinary contract. Preserve the evidence and let qualification withhold it.
    series = term.get("series_id")
    paths = {endpoint}
    if (isinstance(series, str) and re.fullmatch(r"O:(?:SPY|QQQ)\d{6}[CP]\d{8}", series)
            and series.startswith("O:" + str(root))):
        paths.add(endpoint + "/" + series)
    reference_valid = (reference.scheme == "https"
        and reference.netloc in {"api.polygon.io", "api.massive.com"}
        and reference.path in paths
        and not reference.query and re.fullmatch(r"sha256=[a-f0-9]{64}", reference.fragment))
    standard = dict(currency="USD", multiplier=100, deliverable="100_underlying_shares")
    if (root not in {"SPY", "QQQ"} or term.get("root") != root
            or term.get("shares_per_contract") != 100
            or term.get("exercise_style") != "american"
            or ("additional_underlyings" in term and term["additional_underlyings"] != [])
            or not reference_valid
            or any(field in term and term[field] != value for field, value in standard.items())):
        return out
    for field, value in standard.items():
        out.setdefault(field, value)
    out.update(deliverable_ref=term["terms_ref"] + "|" + OCC_ETF_SPEC,
        term_interpretation={"policy": {"SPY":"occ_standard_spy_etf/v1", "QQQ":"occ_standard_qqq_etf/v1"}[root],
            "additional_underlyings_field_present": "additional_underlyings" in term,
            "additional_deliverables": "none_reported",
            "reference_methodology": MASSIVE_REFERENCE_METHODOLOGY,
            "quotation_rule": OCC_ETF_SPEC})
    return out


class BoundedRequestBudget:
    """One in-process three-GET ceiling shared by the incumbent source adapters.

    This is a request bound, not a scheduler, entitlement grant or retry route.
    Failure/uncertainty closes the budget; consumed attempts cannot be reset.
    """
    def __init__(self, max_gets=3, *, profile="selected_expiry"):
        cap = {"selected_expiry": 3, "reference_population": 40, "eod_catchup": 4}.get(profile)
        if cap is None or type(max_gets) is not int or not 1 <= max_gets <= cap:
            raise ValueError("Bounded acquisition permits1–3GETs")
        self.profile = profile
        self.max_gets = max_gets
        self.attempts = 0
        self.stopped = False

    def begin(self, session, url):
        if self.stopped or self.attempts >= self.max_gets:
            raise RuntimeError("Bounded acquisition closed")
        # requests' default adapter has no retries. Reject a retry-enabled carrier.
        if hasattr(session, "get_adapter"):
            retries = session.get_adapter(url).max_retries
            if retries.total not in (0, False):
                raise ValueError("Retry-enabled carrier cannot satisfy bounded acquisition")
        self.attempts += 1

    def stop(self):
        self.stopped = True
