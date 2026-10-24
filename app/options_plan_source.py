"""One bounded, server-owned reference read for conditional Plan expiry math.

No quote request, source registry, persistence, retry, or broad chain crawl. The
incumbent bounded reference adapter owns HTTPS/credential/response constraints.
Browser snapshots supply an identity and authored assumptions, never source proof.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import threading
from zoneinfo import ZoneInfo

from engine.options_nbbo_cohort import canonical_occ_symbol, validate_contract
from lib.options_source_receipts import BoundedRequestBudget
from scripts.massive_entitlement_probe import RestProber

MAX_BYTES = 64 * 1024
_SOURCE_LOCK = threading.Lock()
# A refusal/uncertain provider response closes this process's source lane. There
# is deliberately no request/API reset or automatic alternate-origin fallback.
_SOURCE_STOPPED = False


class PlanSourceUnavailable(ValueError):
    pass


def plan_inputs(payload, *, known_by):
    """Validate the mathematical request before a provider attempt is possible."""
    from engine.options_plan_expiry import prepare_plan_draft_expiry

    if (type(payload) is not dict or set(payload) != {"schema", "draft", "spots", "payoff_basis"}
            or payload["schema"] != "options.plan_expiry_request/v1"):
        raise ValueError("invalid_plan_request")
    draft = payload["draft"]
    if (type(draft) is not dict or set(draft) != {"schema", "legs", "research"}
            or draft.get("schema") != "options_plan_draft.v1"
            or type(draft.get("legs")) is not list or not 1 <= len(draft["legs"]) <= 4):
        raise ValueError("invalid_plan_request")
    research = draft["research"]
    if (type(research) is not dict or set(research) != {"thesis", "invalidation", "horizon"}
            or any(type(research[k]) is not str or len(research[k]) > size
                   for k, size in (("thesis", 4000), ("invalidation", 4000), ("horizon", 160)))):
        raise ValueError("invalid_plan_request")
    contexts, seen = [], set()
    for leg in draft["legs"]:
        if type(leg) is not dict or set(leg) != {"snapshot", "assumptions"}:
            raise ValueError("invalid_plan_request")
        identity = leg["snapshot"]["identity"]
        root, expiry, strike, right = (identity[k] for k in ("root", "exp", "strike", "right"))
        if (root not in {"SPY", "QQQ"} or right not in {"C", "P"}
                or type(strike) not in (int, float)):
            raise ValueError("invalid_plan_request")
        mills = Decimal(str(strike)) * 1000
        if not mills.is_finite() or mills != mills.to_integral_value():
            raise ValueError("invalid_plan_request")
        strike_text = format(Decimal(str(strike)).normalize(), "f")
        contract = validate_contract(dict(root=root, expiration=expiry,
            right={"C": "call", "P": "put"}[right], strike=strike_text,
            strike_millis=int(mills), occ_symbol=canonical_occ_symbol(root=root,
                expiration=expiry, right={"C": "call", "P": "put"}[right], strike_millis=int(mills))))
        if contract["occ_symbol"] in seen:
            raise ValueError("invalid_plan_request")
        seen.add(contract["occ_symbol"])
        contexts.append(dict(contract=contract, reference_observation=None))
    expiries = {context["contract"]["expiration"] for context in contexts}
    basis = payload["payoff_basis"]
    if (type(basis) is not dict or set(basis) != {"kind", "expiration"}
            or basis["kind"] != "hold_to_expiry_intrinsic" or expiries != {basis["expiration"]}):
        raise ValueError("invalid_plan_request")
    # The pure bridge checks all assumptions/basis/spots and exact pin/contract
    # compatibility. Only absent terms may remain before this one reference read.
    result = prepare_plan_draft_expiry(draft, contexts, payload["spots"],
        known_by=known_by, payoff_basis=payload["payoff_basis"])
    if (not result["reasons"] or any(r["code"] != "TERMS_UNQUALIFIED" for r in result["reasons"])):
        raise ValueError("invalid_plan_request")
    return contexts


def read_plan_reference(contexts, *, key, known_by, session=None):
    """Use the existing selected-expiry adapter once; never a snapshot route.

    The caller supplies the server's provisioned key, never a browser credential.
    Returned digest/observed clocks come only from the actual bounded HTTPS read.
    """
    global _SOURCE_STOPPED
    if not key or not _SOURCE_LOCK.acquire(blocking=False):
        raise PlanSourceUnavailable("contract_terms_unavailable")
    try:
        if _SOURCE_STOPPED:
            raise PlanSourceUnavailable("contract_terms_unavailable")
        contracts = [context["contract"] for context in contexts]
        roots = {c["root"] for c in contracts}; expiries = {c["expiration"] for c in contracts}
        if len(roots) != 1 or len(expiries) != 1:
            raise ValueError("invalid_plan_request")
        root, expiry = next(iter(roots)), next(iter(expiries))
        today = datetime.fromisoformat(known_by.replace("Z", "+00:00")).astimezone(ZoneInfo("America/New_York")).date().isoformat()
        params = dict(underlying_ticker=root, expiration_date=expiry, as_of=min(today, expiry),
            **{"strike_price.gte": min(float(c["strike"]) for c in contracts),
               "strike_price.lte": max(float(c["strike"]) for c in contracts)}, limit=100)
        budget = BoundedRequestBudget(max_gets=1)
        prober = RestProber(key, timeout=8, request_budget=budget, session=session)
        path = "/v3/reference/options/contracts"
        payload = prober.probe("plan_selected_terms", path, params=params)
        capability = prober.results["plan_selected_terms"]
        if (capability.get("http_status") != 200 or capability.get("verdict") != "entitled"
                or type(payload) is not dict or payload.get("status") != "OK"
                or type(payload.get("results")) is not list):
            _SOURCE_STOPPED = True
            raise PlanSourceUnavailable("contract_terms_unavailable")
        evidence = capability["evidence"]
        observation = dict(schema="options_reference_capability_observation/v1",
            state="response_observed", origin=prober.base_url, path=path, params=params,
            capability=dict(http_status=200, verdict="entitled"), contracts=payload["results"],
            payload_sha256=evidence["response_sha256"], completed_at=evidence["completed_at"],
            historical_first_availability_established=False)
        return observation
    except PlanSourceUnavailable:
        raise
    except Exception:
        _SOURCE_STOPPED = True
        raise PlanSourceUnavailable("contract_terms_unavailable") from None
    finally:
        _SOURCE_LOCK.release()


def prepare_authenticated_plan(payload, *, key, session=None, now=None):
    """Compose trusted in-process source acquisition with the incumbent pure math."""
    from engine.options_plan_expiry import prepare_plan_draft_expiry

    known_by = (now or datetime.now(timezone.utc)).isoformat()
    contexts = plan_inputs(payload, known_by=known_by)
    observation = read_plan_reference(contexts, key=key, known_by=known_by, session=session)
    for context in contexts:
        context["reference_observation"] = observation
    # Source completed_at may be later than request start; use that actual clock.
    result = prepare_plan_draft_expiry(payload["draft"], contexts, payload["spots"],
        known_by=observation["completed_at"], payoff_basis=payload["payoff_basis"])
    result["source_boundary"] = dict(selection="caller_authored_plan_identity",
        terms="server_observed_bounded_https_reference", discovery_snapshot_authenticated=False,
        historical_first_availability_established=False, current_quote_eligible=False,
        reference_request_count=1, reference_sha256=observation["payload_sha256"],
        reference_observed_at=observation["completed_at"])
    return result
