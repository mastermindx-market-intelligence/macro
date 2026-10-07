"""Package I v0 — default-off integrated answer composer (display-only, read-only)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response

from app.forensics import (
    _PRIVATE_HEADERS,
    _financial_query_provider,
    _latest_payload,
    _load_receipt_index,
    require_site_full_user,
)
from engine.company_intelligence.contracts import ContractError, safe_ticker

REPO = Path(__file__).resolve().parents[1]

router = APIRouter()

STALE_DAYS = 4

_FY2025_REV = {
    "kind": "duration",
    "start": "2024-09-29",
    "end": "2025-09-27",
    "label": "FY2025",
}
_Q3_REV = {
    "kind": "duration",
    "start": "2026-03-29",
    "end": "2026-06-27",
    "label": "FY2026Q3",
}
_YTD_REV = {
    "kind": "duration",
    "start": "2025-09-28",
    "end": "2026-06-27",
    "label": "FY2026YTD",
}
_A2_ASSETS = {
    "kind": "instant",
    "start": None,
    "end": "2026-06-27",
    "label": "2026-06-27",
}

_COPY: dict[str, dict[str, dict[str, str]]] = {
    "financial_facts": {
        "absent": {
            "en": "Financial detail isn't available for this company yet.",
            "zh": "该公司财务明细暂不可用。",
        },
        "stale": {
            "en": "Financial facts are older than this page stamp — check the receipt.",
            "zh": "财务事实早于本页时间戳，请查看来源说明。",
        },
        "refused": {
            "en": "Financial detail isn't available on this view.",
            "zh": "此视图无法提供财务明细。",
        },
    },
    "earnings_expectation": {
        "absent": {
            "en": "Earnings expectation detail isn't wired here yet.",
            "zh": "盈利预期细节尚未接入。",
        },
        "stale": {
            "en": "Earnings expectation chips may be from an older build — check the receipt.",
            "zh": "盈利预期标签可能来自较早构建，请查看来源说明。",
        },
        "refused": {
            "en": "Earnings expectation detail isn't available on this view.",
            "zh": "此视图无法提供盈利预期细节。",
        },
    },
    "publication_seam": {
        "absent": {
            "en": "Account publication rules aren't loaded for this answer.",
            "zh": "本答复尚未加载账户发布规则。",
        },
        "stale": {
            "en": "Publication rules may be older than this page — check the receipt.",
            "zh": "发布规则可能早于本页，请查看来源说明。",
        },
        "refused": {
            "en": "Some financial material is restricted on your account tier.",
            "zh": "部分财务内容受账户权限限制。",
        },
    },
    "event_workspace": {
        "absent": {
            "en": "No current event workspace for this company.",
            "zh": "该公司暂无活动事件工作区。",
        },
        "refused": {
            "en": "Event workspace isn't available on this view.",
            "zh": "此视图无法提供事件工作区。",
        },
    },
    "theme_tape": {
        "absent": {
            "en": "Theme tape context isn't available right now.",
            "zh": "主题盘面背景暂不可用。",
        },
        "stale": {
            "en": "Theme tape context may be dated — watch, don't chase.",
            "zh": "主题盘面背景可能已过期，宜观望。",
        },
        "refused": {
            "en": "Theme tape context isn't available on this view.",
            "zh": "此视图无法提供主题盘面背景。",
        },
    },
    "company_theme_exposure": {
        "absent": {
            "en": "Theme membership for this company isn't available right now.",
            "zh": "该公司主题归属暂不可用。",
        },
        "stale": {
            "en": "Theme membership may be dated — watch, don't chase.",
            "zh": "主题归属可能已过期，宜观望。",
        },
        "refused": {
            "en": "Theme membership isn't available on this view.",
            "zh": "此视图无法提供主题归属。",
        },
    },
    "basket_labels": {
        "absent": {
            "en": "Basket labels aren't available right now.",
            "zh": "篮子标签暂不可用。",
        },
    },
    "theme_membership_file": {
        "absent": {
            "en": "Theme membership file isn't available right now.",
            "zh": "主题归属文件暂不可用。",
        },
    },
}

_k3e_lock = threading.Lock()
_k3e_cached_rev: str | None = None
_k3e_cached_bundle: tuple[Any, Any, Any] | None = None

_chip_lock = threading.Lock()
_chip_cached_day: str | None = None
_chip_cached_value: dict[str, dict[str, Any]] | None = None


def _require_enabled() -> None:
    if os.environ.get("MACRO_INTEGRATED_ANSWER_ENABLED") != "1":
        raise HTTPException(status_code=404, detail="Not Found")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_clock(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        return None
    text = value.strip()
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        return f"{text}T00:00:00Z"
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")


def _content_hash(payload: object) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def _make_ref(
    *,
    route: str,
    as_of: str,
    payload: object,
    generation_id: str | None = None,
    owner_hash: str | None = None,
) -> dict[str, Any]:
    return {
        "route": route,
        "as_of": as_of,
        "generation_id": generation_id,
        "owner_hash": owner_hash,
        "content_hash": _content_hash(payload),
    }


def _leg_shell(leg_id: str) -> dict[str, Any]:
    return {
        "leg": leg_id,
        "status": "absent",
        "ref": None,
        "payload": None,
        "degraded_reason": None,
        "copy": None,
    }


def _apply_copy(leg: dict[str, Any]) -> None:
    status = leg["status"]
    if status == "ok":
        leg["copy"] = None
        leg["degraded_reason"] = None
        return
    table = _COPY.get(leg["leg"], {})
    leg["copy"] = table.get(status)


def _financial_provider():
    return _financial_query_provider()


def _k3e_source() -> tuple[Any, Any, Any]:
    global _k3e_cached_rev, _k3e_cached_bundle
    proc = subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError("git_rev_failed")
    rev = proc.stdout.strip()
    if len(rev) != 40 or not all(c in "0123456789abcdef" for c in rev):
        raise RuntimeError("git_rev_invalid")
    with _k3e_lock:
        if _k3e_cached_rev == rev and _k3e_cached_bundle is not None:
            return _k3e_cached_bundle
        from scripts.query_k3e_expectation_surface import load_frozen_source

        bundle = load_frozen_source(REPO, rev)
        _k3e_cached_rev = rev
        _k3e_cached_bundle = bundle
        return bundle


def _expectation_chips(day: datetime.date) -> dict[str, dict[str, Any]]:
    global _chip_cached_day, _chip_cached_value
    key = day.isoformat()
    with _chip_lock:
        if _chip_cached_day == key and _chip_cached_value is not None:
            return _chip_cached_value
        from engine.expectation_state import expectation_states

        value = expectation_states(today=day)
        _chip_cached_day = key
        _chip_cached_value = value
        return value


def _receipt_identity() -> dict[str, Any]:
    from app import forensics as forensics_mod

    index = _load_receipt_index()
    _latest_payload(index)
    return forensics_mod._receipt_identity(index)


def _event_result(ticker: str) -> dict[str, Any]:
    from engine.neuralweb.company_intelligence_reader import read_current_event_workspace

    return read_current_event_workspace({"ticker": ticker})


def _theme_context() -> dict[str, Any] | None:
    from engine.theme_context import read_context

    return read_context("us")


def _cte_dir() -> Path:
    return Path(os.environ.get("MACRO_CTE_DIR") or REPO / "data" / "company_theme_exposure")


def _leg_financial_facts(ticker: str) -> dict[str, Any]:
    leg = _leg_shell("financial_facts")
    if ticker != "AAPL":
        leg["status"] = "absent"
        leg["degraded_reason"] = "not_covered:golden_corpus_is_aapl_only"
        _apply_copy(leg)
        return leg
    req = {
        "schema": "fundamental_forensics.financial_query_request/v1",
        "entity_id": "ISS:US-XNAS-AAPL",
        "policy": {
            "selection": "latest_known_as_of",
            "source_snapshot_at": "2026-08-01T00:00:00Z",
            "recorded_at": "2026-08-23T12:00:00Z",
        },
        "metric_ids": [
            "revenue",
            "total_assets",
            "net_cash_from_operating_activities",
        ],
        "periods": [_FY2025_REV, _Q3_REV, _YTD_REV, _A2_ASSETS],
    }
    body = json.dumps(req, separators=(",", ":")).encode()
    try:
        from engine.fundamental_forensics.query_service import (
            FinancialQueryAdmissionError,
            FinancialQueryUnavailableError,
            execute_financial_query,
        )

        result = execute_financial_query(body=body, provider=_financial_provider())
        payload = {
            "request": req,
            "query_hash": result.envelope.get("receipt", {}).get("query_hash"),
            "response_sha256": result.sha256,
            "replay_route": "/api/forensics/v1/financial/query",
        }
        as_of = _normalize_clock(req["policy"]["recorded_at"]) or "2026-08-23T12:00:00Z"
        leg["status"] = "ok"
        leg["payload"] = payload
        leg["ref"] = _make_ref(
            route="/api/forensics/v1/financial/query",
            as_of=as_of,
            payload=payload,
            generation_id=None,
            owner_hash=result.sha256,
        )
        _apply_copy(leg)
        return leg
    except FinancialQueryAdmissionError as exc:
        leg["status"] = "refused"
        leg["degraded_reason"] = f"admission:{exc.status_code}"
        _apply_copy(leg)
        return leg
    except FinancialQueryUnavailableError as exc:
        leg["status"] = "absent"
        leg["degraded_reason"] = f"unavailable:{type(exc).__name__}"
        _apply_copy(leg)
        return leg
    except Exception as exc:  # noqa: BLE001
        leg["status"] = "absent"
        leg["degraded_reason"] = f"unavailable:{type(exc).__name__}"
        _apply_copy(leg)
        return leg


def _leg_earnings_expectation(ticker: str, composed_at: str) -> dict[str, Any]:
    from engine.k3e_expectation_surface import QueryRefusal, inspect_expectation_surface

    leg = _leg_shell("earnings_expectation")
    k3e_reason = "missing"
    chip_reason = "missing"
    capture_inspection: dict[str, Any] | None = None
    expectation_chip: dict[str, Any] | None = None

    try:
        obs, attempts, provenance = _k3e_source()
        capture_inspection = inspect_expectation_surface(
            obs,
            attempts,
            source_provenance=provenance,
            ticker=ticker,
            metric="EPS",
            horizon="+1q",
            as_of=composed_at,
            provider="yfinance",
            composed_at=composed_at,
        )
        k3e_reason = "ok"
    except QueryRefusal as exc:
        k3e_reason = str(exc.reason)
    except Exception as exc:  # noqa: BLE001
        k3e_reason = f"unavailable:{type(exc).__name__}"

    try:
        day = datetime.fromisoformat(composed_at.replace("Z", "+00:00")).date()
        chips = _expectation_chips(day)
        expectation_chip = chips.get(ticker)
        chip_reason = "ok" if expectation_chip is not None else "missing_ticker"
    except Exception as exc:  # noqa: BLE001
        chip_reason = f"unavailable:{type(exc).__name__}"

    if capture_inspection is None and expectation_chip is None:
        leg["status"] = "absent"
        leg["degraded_reason"] = f"k3e:{k3e_reason};chip:{chip_reason}"
        _apply_copy(leg)
        return leg

    payload = {
        "capture_inspection": capture_inspection,
        "expectation_chip": expectation_chip,
    }
    leg["status"] = "ok"
    leg["payload"] = payload
    owner_clock = (
        (capture_inspection or {})
        .get("latest_captured_snapshot", {})
        .get("derived_capture_available_at")
    )
    as_of_norm = _normalize_clock(owner_clock)
    owner_hash = (capture_inspection or {}).get("query_identity")
    if as_of_norm is None:
        leg["status"] = "stale"
        leg["degraded_reason"] = "no_owner_clock"
        as_of_norm = composed_at
    leg["ref"] = _make_ref(
        route="k3e:inspect_expectation_surface+expectation_state:expectation_states",
        as_of=as_of_norm,
        payload=payload,
        generation_id=None,
        owner_hash=owner_hash if isinstance(owner_hash, str) else None,
    )
    _apply_copy(leg)
    return leg


def _leg_capital_structure() -> dict[str, Any]:
    leg = _leg_shell("capital_structure")
    leg["status"] = "held_unavailable"
    leg["degraded_reason"] = "held:W4/W6 preserved (Mastermind #1258 F4; WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2)"
    leg["copy"] = {
        "en": "Capital-structure context is on hold for this answer.",
        "zh": "本答复的资本结构背景暂缓提供。",
    }
    return leg


def _leg_publication_seam() -> dict[str, Any]:
    leg = _leg_shell("publication_seam")
    try:
        identity = _receipt_identity()
        payload = {key: identity.get(key) for key in ("snapshot_id", "base_snapshot_id", "query_hash", "published_at")}
        as_of = _normalize_clock(payload.get("published_at"))
        if as_of is None:
            raise ValueError("missing published_at")
        leg["status"] = "ok"
        leg["payload"] = payload
        leg["ref"] = _make_ref(
            route="/api/forensics/v1/attested-history/latest",
            as_of=as_of,
            payload=payload,
            generation_id=payload.get("snapshot_id"),
            owner_hash=payload.get("query_hash"),
        )
        _apply_copy(leg)
        return leg
    except Exception:  # noqa: BLE001
        leg["status"] = "absent"
        leg["degraded_reason"] = "attested_store_off_or_unavailable"
        _apply_copy(leg)
        return leg


def _leg_event_workspace(ticker: str, composed_at: str) -> dict[str, Any]:
    from app.company_intelligence import _public_workspace_glance

    leg = _leg_shell("event_workspace")
    try:
        result = _event_result(ticker)
        if result.get("available"):
            payload = _public_workspace_glance(result)
            workspace = result.get("workspace") or {}
            as_of_raw = workspace.get("generated_at") or payload.get("event_date")
            as_of = _normalize_clock(as_of_raw)
            if as_of is None:
                as_of = composed_at
            leg["status"] = "ok"
            leg["payload"] = payload
            leg["ref"] = _make_ref(
                route=f"/api/event-workspace/{ticker}",
                as_of=as_of if as_of else _utc_now(),
                payload=payload,
                generation_id=payload.get("generation_id") if isinstance(payload.get("generation_id"), str) else None,
                owner_hash=None,
            )
            _apply_copy(leg)
            return leg
        note = str(result.get("note") or "event_workspace_unavailable")
        leg["status"] = "absent"
        leg["degraded_reason"] = note
        _apply_copy(leg)
        return leg
    except Exception as exc:  # noqa: BLE001
        leg["status"] = "absent"
        leg["degraded_reason"] = f"unavailable:{type(exc).__name__}"
        _apply_copy(leg)
        return leg


def _leg_theme_tape() -> dict[str, Any]:
    leg = _leg_shell("theme_tape")
    try:
        ctx = _theme_context()
        if ctx is None:
            leg["status"] = "absent"
            leg["degraded_reason"] = "theme_context_absent"
            _apply_copy(leg)
            return leg
        payload = {key: ctx.get(key) for key in ("schema", "as_of", "region", "display_only", "leadership")}
        as_of = _normalize_clock(ctx.get("as_of"))
        if as_of is None:
            leg["status"] = "stale"
            leg["degraded_reason"] = "no_owner_clock"
            as_of = _utc_now()
        else:
            leg["status"] = "ok"
        leg["payload"] = payload
        leg["ref"] = _make_ref(
            route="theme_context:read_context",
            as_of=as_of,
            payload=payload,
            generation_id=None,
            owner_hash=None,
        )
        _apply_copy(leg)
        return leg
    except Exception as exc:  # noqa: BLE001
        leg["status"] = "absent"
        leg["degraded_reason"] = f"unavailable:{type(exc).__name__}"
        _apply_copy(leg)
        return leg


def _leg_company_theme_exposure(ticker: str, composed_at: str) -> dict[str, Any]:
    from engine.company_theme_exposure import contracts

    leg = _leg_shell("company_theme_exposure")
    try:
        base = _cte_dir()
        marker_path = base / "manifest.json"
        if not marker_path.is_file():
            leg["status"] = "absent"
            leg["degraded_reason"] = "generation_absent"
            _apply_copy(leg)
            return leg
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        contracts.validate_manifest(marker)
        gid = marker["generation_id"]
        immutable_path = base / "generations" / gid / "manifest.json"
        if not immutable_path.is_file():
            leg["status"] = "absent"
            leg["degraded_reason"] = "generation_absent"
            _apply_copy(leg)
            return leg
        immutable = json.loads(immutable_path.read_text(encoding="utf-8"))
        if immutable.get("generation_id") != gid:
            leg["status"] = "absent"
            leg["degraded_reason"] = "generation_mismatch"
            _apply_copy(leg)
            return leg
        rel = contracts.company_filename(ticker)
        entry = marker.get("files", {}).get(rel)
        if entry is None:
            leg["status"] = "absent"
            leg["degraded_reason"] = "ticker_not_in_generation"
            _apply_copy(leg)
            return leg
        raw_path = base / "generations" / gid / rel
        raw = raw_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry["sha256"] or len(raw) != entry["bytes"]:
            leg["status"] = "absent"
            leg["degraded_reason"] = "generation_mismatch"
            _apply_copy(leg)
            return leg
        payload = json.loads(raw.decode("utf-8"))
        contracts.validate_exposure(payload)
        owner_clock = (payload.get("theme_state") or {}).get("as_of")
        as_of = _normalize_clock(owner_clock)
        leg["status"] = "ok"
        leg["payload"] = payload
        if as_of is None:
            leg["status"] = "stale"
            leg["degraded_reason"] = "no_owner_clock"
            as_of = composed_at
        leg["ref"] = _make_ref(
            route="company_theme_exposure:published_generation",
            as_of=as_of,
            payload=payload,
            generation_id=gid,
            owner_hash=entry.get("sha256"),
        )
        _apply_copy(leg)
        return leg
    except ContractError:
        leg["status"] = "absent"
        leg["degraded_reason"] = "contract_invalid"
        _apply_copy(leg)
        return leg
    except Exception as exc:  # noqa: BLE001
        leg["status"] = "absent"
        leg["degraded_reason"] = f"unavailable:{type(exc).__name__}"
        _apply_copy(leg)
        return leg


def _leg_fixed_absent(leg_id: str, degraded_reason: str) -> dict[str, Any]:
    leg = _leg_shell(leg_id)
    leg["status"] = "absent"
    leg["degraded_reason"] = degraded_reason
    _apply_copy(leg)
    return leg


def _compose_page(ticker: str) -> dict[str, Any]:
    composed_at = _utc_now()
    legs = [
        _leg_financial_facts(ticker),
        _leg_earnings_expectation(ticker, composed_at),
        _leg_capital_structure(),
        _leg_publication_seam(),
        _leg_event_workspace(ticker, composed_at),
        _leg_theme_tape(),
        _leg_company_theme_exposure(ticker, composed_at),
        _leg_fixed_absent(
            "basket_labels",
            "not_read_in_v0:owner_not_recorded;direct_site_json_reads_forbidden(I-R2)",
        ),
        _leg_fixed_absent(
            "theme_membership_file",
            "not_read_in_v0:owner_not_recorded;direct_site_json_reads_forbidden(I-R2)",
        ),
    ]

    surfaced = [item for item in legs if item["status"] in {"ok", "stale"}]
    if surfaced:
        page_as_of = max(item["ref"]["as_of"] for item in surfaced if item.get("ref"))
    else:
        page_as_of = composed_at

    cutoff = datetime.fromisoformat(page_as_of.replace("Z", "+00:00"))
    stale_before = cutoff - timedelta(days=STALE_DAYS)
    for item in legs:
        if item["leg"] == "event_workspace":
            continue
        if item["status"] not in {"ok", "stale"}:
            continue
        ref = item.get("ref")
        if not ref:
            continue
        leg_clock = datetime.fromisoformat(ref["as_of"].replace("Z", "+00:00"))
        if leg_clock < stale_before:
            item["status"] = "stale"
            item["degraded_reason"] = "older_than_page_stamp"
            _apply_copy(item)

    coverage_note = None
    if any(item["status"] != "ok" for item in legs):
        coverage_note = {
            "en": "Not everything below is published for every market.",
            "zh": "以下内容并非在所有市场均有发布。",
        }

    return {
        "schema": "integrated_answer.v0",
        "ticker": ticker,
        "as_of": page_as_of,
        "composed_at": composed_at,
        "display_only": True,
        "stance": {"en": "Watch — don't chase", "zh": "观望，勿追"},
        "footer": {"en": "Heads-up only, not a buy signal.", "zh": "仅为提示，非买入信号。"},
        "coverage_note": coverage_note,
        "legs": legs,
    }


@router.get(
    "/api/integrated-answer/v1/{ticker}",
    dependencies=[Depends(_require_enabled)],
)
def integrated_answer_v1(
    ticker: str,
    _user: dict = Depends(require_site_full_user),
) -> Response:
    try:
        normalized = safe_ticker(ticker)
    except ContractError:
        raise HTTPException(status_code=400, detail="invalid ticker") from None

    page = _compose_page(normalized)
    body_bytes = json.dumps(page, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    digest = hashlib.sha256(body_bytes).hexdigest()
    return Response(
        content=body_bytes,
        media_type="application/json",
        headers={**_PRIVATE_HEADERS, "X-Integrated-Answer-SHA256": digest},
    )
