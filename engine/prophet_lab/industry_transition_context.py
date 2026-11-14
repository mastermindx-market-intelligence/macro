"""Read-only Prophet consumer for versioned industry research artifacts.

No source reconstruction, model fitting, provider calls, ranking mutation or live
trade action occurs in this reader. Historical and stale outputs stay visible as
research, never as current trading instructions.
"""
from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any

SCHEMA = "prophet.industry_research_snapshot.v1"
MAX_BYTES = 2_000_000


def _finite(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def validate_snapshot(snapshot: dict) -> None:
    if not isinstance(snapshot, dict) or snapshot.get("schema") != SCHEMA:
        raise ValueError("unsupported snapshot schema")
    if snapshot.get("financial_influence") is not False or snapshot.get("authority") != "research_only":
        raise ValueError("research authority boundary violated")
    if snapshot.get("evidence_mode") not in {"RECONSTRUCTED_DISCOVERY", "OBSERVED_SHADOW"}:
        raise ValueError("explicit evidence mode required")
    asof = datetime.fromisoformat(snapshot["as_of"].replace("Z", "+00:00"))
    if asof.tzinfo is None: raise ValueError("timezone-aware as_of required")
    if not isinstance(snapshot.get("source_refs"), list) or not snapshot["source_refs"]:
        raise ValueError("source references required")
    if not isinstance(snapshot.get("forecasts"), list) or not snapshot["forecasts"]:
        raise ValueError("nonempty forecast list required")
    seen = set()
    for row in snapshot["forecasts"]:
        if not isinstance(row, dict): raise ValueError("invalid forecast object")
        if row.get("schema") != "prophet.industry_transition.v1" or row.get("financial_influence") is not False:
            raise ValueError("invalid forecast boundary")
        if row.get("authority") != "research_only" or row.get("evidence_mode") != snapshot["evidence_mode"]:
            raise ValueError("forecast evidence mismatch")
        industry = row.get("industry")
        if not isinstance(industry, str) or not industry or industry in seen:
            raise ValueError("duplicate or missing industry")
        seen.add(industry)
        dt = datetime.fromisoformat(row["decision_date"]).date()
        if dt != asof.date(): raise ValueError("mixed forecast decision dates")
        p = row.get("probabilities", {})
        if not isinstance(p, dict) or set(p) != {"upside_first", "downside_first", "timeout"}:
            raise ValueError("invalid outcome partition")
        if not all(_finite(v) and 0 <= v <= 1 for v in p.values()) or abs(sum(p.values()) - 1) > 1e-8:
            raise ValueError("invalid probabilities")
        if not _finite(row.get("p_bad_loss")) or not 0 <= row["p_bad_loss"] <= 1:
            raise ValueError("invalid bad-loss probability")
        if not _finite(row.get("expected_excess_net")):
            raise ValueError("invalid expected return")
        if not _finite(row.get("outside_support_share")) or not 0 <= row["outside_support_share"] <= 1:
            raise ValueError("invalid support diagnostic")
        model = row.get("model", {})
        if not isinstance(model, dict): raise ValueError("invalid model metadata")
        label = model.get("label_contract", {})
        if not isinstance(label, dict): raise ValueError("missing outcome contract")
        for name in ("horizon", "entry_delay"):
            if type(label.get(name)) is not int or label[name] < 1:
                raise ValueError("invalid outcome horizon")
        for name in ("target", "loss"):
            if not _finite(label.get(name)) or not 0 < label[name] < 1:
                raise ValueError("invalid outcome boundary")
        if not _finite(label.get("cost")) or not 0 <= label["cost"] < 1:
            raise ValueError("invalid cost contract")
        if datetime.fromisoformat(model["calibration_label_end"]).date() >= dt:
            raise ValueError("model calibration has future outcomes")
        if datetime.fromisoformat(model["prediction_start"]).date() > dt:
            raise ValueError("forecast predates model boundary")
        if row.get("context_changes_forecast", False) is not False:
            raise ValueError("unvalidated context cannot alter forecasts")
        if "k3e" in row and (not isinstance(row["k3e"], dict) or row["k3e"].get("financial_influence") is not False):
            raise ValueError("K3E authority mismatch")


def read_industry_context(path: Path, *, now: datetime | None = None) -> dict:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None: raise ValueError("timezone-aware now required")
    base = {"schema": "prophet.industry_research_response.v1", "state": "UNAVAILABLE",
            "financial_influence": False, "live_signal": False, "snapshot": None,
            "reason": None, "content_sha256": None}
    try:
        if path.stat().st_size > MAX_BYTES: raise ValueError("snapshot exceeds bounded reader size")
        raw = path.read_bytes()
        if len(raw) > MAX_BYTES: raise ValueError("snapshot grew beyond reader limit")
        payload = json.loads(raw)
        validate_snapshot(payload)
        asof = datetime.fromisoformat(payload["as_of"].replace("Z", "+00:00"))
        if asof > current: raise ValueError("snapshot is in the future")
    except FileNotFoundError:
        return base | {"reason": "RESEARCH_ARTIFACT_NOT_PRESENT"}
    except (ValueError, KeyError, TypeError, OSError, OverflowError):
        return base | {"reason": "RESEARCH_ARTIFACT_INVALID"}
    return base | {"state": "HISTORICAL_RESEARCH" if (current - asof).days > 7 else "RESEARCH_SHADOW",
                   "reason": "NOT_A_LIVE_VALIDATED_SIGNAL", "snapshot": payload,
                   "content_sha256": sha256(raw).hexdigest()}
