"""Private fixed-reference consumer for conditional Plan expiry math.

No provider request, source registry, persistence or automatic refresh. Browser
snapshots supply identity and authored assumptions; the server reads separately
qualified original capture bytes under private, fixed installation custody.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from engine.options_nbbo_cohort import canonical_occ_symbol, validate_contract

MAX_BYTES = 64 * 1024


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






def read_private_reference(path, expected_sha256):
    """Read one installed original observation; no index, upload or acquisition.

    The accepted original-source custody + private installation qualifies this
    artifact. Its configured hash checks installed bytes, never provider identity.
    Path/hash come solely from service configuration and are not browser inputs.
    """
    import hashlib
    import json
    import os
    from pathlib import Path
    import re
    import stat

    if (not isinstance(path, Path) or not path.is_absolute() or ".." in path.parts
            or not isinstance(expected_sha256, str) or not re.fullmatch("[a-f0-9]{64}", expected_sha256)):
        raise PlanSourceUnavailable("contract_terms_unavailable")
    directory = file_fd = None
    try:
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        directory = os.open("/", flags)
        for part in path.parts[1:-1]:
            following = os.open(part, flags, dir_fd=directory)
            os.close(directory); directory = following
        parent = os.fstat(directory)
        if parent.st_uid != os.getuid() or stat.S_IMODE(parent.st_mode) != 0o700:
            raise ValueError("unqualified private directory")
        file_fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        before = os.fstat(file_fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid()
                or stat.S_IMODE(before.st_mode) != 0o600 or before.st_nlink != 1
                or not 0 < before.st_size <= 262144):
            raise ValueError("unqualified private artifact")
        parts, size = [], 0
        while True:
            chunk = os.read(file_fd, min(65536, 262145 - size))
            if not chunk:
                break
            size += len(chunk)
            if size > 262144:
                raise ValueError("artifact byte bound")
            parts.append(chunk)
        raw = b"".join(parts)
        after = os.fstat(file_fd)
        named = os.stat(path.name, dir_fd=directory, follow_symlinks=False)
        identity = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
                                  info.st_ctime_ns, info.st_uid, info.st_mode, info.st_nlink)
        if (identity(before) != identity(after) or identity(after) != identity(named)
                or len(raw) != before.st_size or hashlib.sha256(raw).hexdigest() != expected_sha256):
            raise ValueError("installed artifact changed")
        def unique(pairs):
            out = {}
            for key, value in pairs:
                if key in out:
                    raise ValueError("duplicate observation key")
                out[key] = value
            return out
        observed = json.loads(raw, object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite observation")))
        if (type(observed) is not dict or observed.get("schema") != "options_reference_capability_observation/v1"
                or observed.get("origin") != "https://api.polygon.io"
                or observed.get("path") != "/v3/reference/options/contracts"
                and not str(observed.get("path", "")).startswith("/v3/reference/options/contracts/O:")
                or observed.get("state") != "response_observed"
                or observed.get("capability", {}).get("http_status") != 200
                or observed.get("capability", {}).get("verdict") != "entitled"
                or not re.fullmatch("[a-f0-9]{64}", str(observed.get("payload_sha256", "")))):
            raise ValueError("unqualified observation")
        from lib.options_source_receipts import instant
        if instant(observed.get("completed_at")) > datetime.now(timezone.utc):
            raise ValueError("future observation")
        return observed, hashlib.sha256(raw).hexdigest()
    except Exception:
        raise PlanSourceUnavailable("contract_terms_unavailable") from None
    finally:
        if file_fd is not None:
            os.close(file_fd)
        if directory is not None:
            os.close(directory)


def prepare_retained_plan(payload, *, reference_path, expected_sha256, now=None):
    """Use a qualified dated reference exactly as retained, with no current claim."""
    from copy import deepcopy
    from datetime import date
    from engine.options_plan_expiry import prepare_plan_draft_expiry

    known_by = (now or datetime.now(timezone.utc)).isoformat()
    contexts = plan_inputs(payload, known_by=known_by)
    observation, installed_sha = read_private_reference(reference_path, expected_sha256)
    as_of = observation.get("params", {}).get("as_of")
    try:
        if date.fromisoformat(as_of).isoformat() != as_of:
            raise ValueError("unknown reference basis")
    except (ValueError, TypeError):
        raise PlanSourceUnavailable("contract_terms_unavailable") from None
    rows = observation.get("contracts") if "contracts" in observation else [observation.get("contract")]
    try:
        if (not isinstance(rows, list) or not 1 <= len(rows) <= 100
                or any(not isinstance(row, dict) for row in rows)):
            raise ValueError("coverage absent")
        roots = {row["underlying_ticker"] for row in rows}
        tickers = [row["ticker"] for row in rows]
        expirations = sorted({row["expiration_date"] for row in rows})
        if (len(roots) != 1 or not roots <= {"SPY", "QQQ"}
                or len(set(tickers)) != len(tickers) or any(not isinstance(ticker, str) for ticker in tickers)
                or any(date.fromisoformat(expiry).isoformat() != expiry for expiry in expirations)):
            raise ValueError("coverage invalid")
    except (ValueError, TypeError, KeyError):
        raise PlanSourceUnavailable("contract_terms_unavailable") from None
    for context in contexts:
        context["reference_observation"] = deepcopy(observation)
    result = prepare_plan_draft_expiry(payload["draft"], contexts, payload["spots"],
        known_by=known_by, payoff_basis=payload["payoff_basis"])
    result["source_boundary"] = dict(selection="caller_authored_plan_identity",
        terms="server_held_qualified_reference", terms_temporal_basis="dated_reference",
        reference_as_of=as_of, reference_observed_at=observation["completed_at"],
        reference_root=next(iter(roots)), reference_contract_count=len(rows), reference_expirations=expirations,
        reference_sha256=observation["payload_sha256"], installed_observation_sha256=installed_sha,
        original_response_bytes_replayed=False, discovery_snapshot_authenticated=False,
        historical_first_availability_established=False, current_terms_qualified=False,
        current_quote_eligible=False, reference_request_count=0)
    return result
