"""AI Brief publication/read contract. No inference, credentials or scheduling.

The one atomic envelope keeps a last successful AI read separate from the most
recent input snapshot and attempt. Timestamps never turn a failed attempt into
an AI success. Date-only evidence is displayed as a date, not a market session.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCHEMA = "aibrief.live.v1"
FILES = {"macro": "master_brief.json", "china": "china_brief.json", "btc": "btc_brief.json"}
MAX_BYTES = 2 * 1024 * 1024
SCALARS = ("summary", "regime_read", "rotation_check", "forward_read")
LISTS = ("tldr", "conflicts", "transmission", "watch_items")


def utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        # A missing zone is not a qualified generation clock.
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (ValueError, OverflowError):
        return None


def evidence_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value) if len(value) == 10 else None
    except ValueError:
        return None


def interval(value: Any, *, lens: str) -> int:
    return value if type(value) is int and 1 <= value <= 7 else (3 if lens == "btc" else 1)


def evidence_deadline(value: Any, *, lens: str) -> datetime | None:
    day = evidence_date(value)
    if day is None:
        return None
    # Explicit elapsed-age policy; no invented trading-day/holiday calendar.
    # Date-only sources can be as old as the start of their stamped UTC date.
    return datetime.combine(day, datetime.min.time(), timezone.utc) + timedelta(
        hours=48 if lens == "btc" else 96)


def evidence_usable(value: Any, *, lens: str, now: datetime) -> bool:
    day, deadline = evidence_date(value), evidence_deadline(value, lens=lens)
    return bool(day and day <= now.date() and deadline and now < deadline)


def content_id(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def read_json(path: Path) -> dict | None:
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            return None
        result = json.loads(raw, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        return result if isinstance(result, dict) else None
    except (OSError, ValueError, TypeError, RecursionError):
        return None


def validate_brief(value: Any, *, lens: str) -> bool:
    """Do not publish truncated, empty, mistyped or falsely dated model output."""
    if not isinstance(value, dict) or value.get("lens", lens) != lens:
        return False
    if not utc(value.get("generated_at")) or not evidence_date(value.get("state_asof")):
        return False
    if value.get("degraded_reason") or not any(value.get(k) for k in ("summary", "regime_read", "tldr")):
        return False
    if any(value.get(k) is not None and (not isinstance(value[k], str) or len(value[k]) > 16000) for k in SCALARS):
        return False
    for key in LISTS:
        rows = value.get(key, [])
        if not isinstance(rows, list) or len(rows) > 32 or any(
                not isinstance(row, str) or len(row) > 4000 for row in rows):
            return False
    if value.get("confidence") not in (None, "low", "medium", "high"):
        return False
    catalysts = value.get("forward_watch", [])
    if not isinstance(catalysts, list) or len(catalysts) > 32:
        return False
    for catalyst in catalysts:
        if (not isinstance(catalyst, dict) or not evidence_date(catalyst.get("date"))
                or not isinstance(catalyst.get("label"), str) or not catalyst["label"].strip()
                or any(not isinstance(catalyst.get(k, ""), str) or len(catalyst.get(k, "")) > 1600
                       for k in ("label", "kind", "note"))):
            return False
    zh = value.get("zh")
    if zh is not None:
        if not isinstance(zh, dict):
            return False
        for key in SCALARS:
            if zh.get(key) is not None and (not isinstance(zh[key], str) or len(zh[key]) > 16000):
                return False
        for key in LISTS:
            rows = zh.get(key, [])
            if not isinstance(rows, list) or len(rows) > 32 or any(
                    not isinstance(row, str) or len(row) > 4000 for row in rows):
                return False
    return True


def safe_facts(value: Any) -> list[dict]:
    out = []
    if not isinstance(value, list):
        return out
    for row in value[:12]:
        if not isinstance(row, dict):
            continue
        keys = ("label_en", "label_zh", "value_en", "value_zh")
        if not all(isinstance(row.get(k, ""), str) and len(row.get(k, "")) <= 240 for k in keys):
            continue
        if not row.get("label_en") or not row.get("value_en"):
            continue
        out.append({**{k: row.get(k, "") for k in keys}, "tone": "neutral"})
    return out


def qualify_inputs(state: dict, *, lens: str, now: datetime) -> tuple[dict, list[dict]]:
    """Bind precisely the observations the AI may consume, including exclusions.

    Secondary blocks without an explicit observation date are not qualified by
    a fresh primary date. This is a projection of Master Brain's original state,
    not a replacement source/cache. No values or dates are recomputed here.
    """
    selected, manifest = {}, []
    for key, block in state.items():
        stamp = block.get("date") if isinstance(block, dict) else None
        if stamp is None and isinstance(block, dict):
            stamp = block.get("as_of") or block.get("asof")
            if isinstance(stamp, str) and utc(stamp):
                stamp = utc(stamp).date().isoformat()
        source_lens = key if key in FILES else lens
        usable = evidence_usable(stamp, lens=source_lens, now=now)
        status = "included" if usable else "undated" if not evidence_date(stamp) else "outside_age_budget"
        manifest.append({"source": key, "date": stamp if evidence_date(stamp) else None,
                         "status": status, "required": key == lens})
        if usable:
            selected[key] = block
    # The exact exclusion list is part of the prompt's provenance. It cannot be
    # mistaken for affirmative evidence or quietly disappear from the UI status.
    selected["_evidence_manifest"] = manifest
    return selected, manifest


def read_publication(root: Path, state_dir: Path, lens: str) -> tuple[dict | None, dict | None]:
    filename = FILES[lens]  # Fixed allow-list; never a request-derived path.
    publication = read_json(state_dir / f"aibrief-{lens}.json")
    if not (publication and publication.get("schema") == SCHEMA
            and publication.get("lens") == lens
            and type(publication.get("sequence")) is int and publication["sequence"] >= 1):
        publication = None
    fallback = read_json(root / "data" / "regime" / filename)
    if not validate_brief(fallback, lens=lens):
        fallback = read_json(root / "site" / filename)
    return publication, fallback if validate_brief(fallback, lens=lens) else None


def view(publication: dict | None, fallback: dict | None, *, lens: str,
         now: datetime | None = None) -> dict:
    """A read-time projection: expiry keeps advancing even if every writer stops."""
    now = now or datetime.now(timezone.utc)
    p = publication or {}
    candidate = p.get("last_good")
    brief = candidate if validate_brief(candidate, lens=lens) else fallback
    brief = brief if validate_brief(brief, lens=lens) else None
    attempt = p.get("attempt") if isinstance(p.get("attempt"), dict) else {}
    facts = p.get("facts") if isinstance(p.get("facts"), dict) else {}
    facts_day = facts.get("state_asof")
    facts_ok = evidence_usable(facts_day, lens=lens, now=now)
    generated = utc((brief or {}).get("generated_at"))
    source_day = (brief or {}).get("state_asof")
    cadence = interval((brief or {}).get("refresh_days"), lens=lens)
    draft_deadline = generated + timedelta(days=cadence) if generated else None
    source_deadline = evidence_deadline(source_day, lens=lens)
    valid_until = min(draft_deadline, source_deadline) if draft_deadline and source_deadline else None
    newer_inputs = bool((evidence_date(facts_day) and evidence_date(source_day) and facts_day > source_day)
                        or facts.get("input_digest") and facts.get("input_digest") != (brief or {}).get("input_digest"))
    current = bool(brief and generated and generated <= now + timedelta(minutes=5)
                   and valid_until and now < valid_until
                   and evidence_usable(source_day, lens=lens, now=now) and not newer_inputs)
    state = (p.get("hold") or {}).get("state", attempt.get("state", "not_scheduled"))
    if current:
        status = "available" if state in ("succeeded", "not_due") else "degraded"
    elif brief:
        status = "stale"
    else:
        status = "facts_only" if facts_ok and safe_facts(facts.get("key_facts")) else "unavailable"
    # Never include raw exceptions, provider transport, operation IDs or paths in
    # a browser response. Operational detail remains in the private envelope.
    messages = {
        "available": ("AI read available. Check the evidence date below.", "AI 解读已更新，请核对下方数据日期。"),
        "degraded": ("The latest AI refresh is unavailable. The last valid read is retained below.", "最新 AI 更新暂不可用。下方保留最近一次有效解读。"),
        "stale": ("AI update overdue. The previous read is archived below; it is not a current market view.", "AI 更新已逾期。下方旧解读仅供存档参考，不代表当前市场。"),
        "facts_only": ("AI synthesis is unavailable. These are existing dashboard readings, without a new AI interpretation.", "AI 综合解读暂不可用。以下仅为现有看板读数，未加入新的 AI 判断。"),
        "unavailable": ("A current AI brief is unavailable. Check the underlying dashboards and their dates.", "当前 AI 简报暂不可用，请核对底层看板及其数据日期。"),
    }
    en, zh = messages[status]
    if state in ("running", "effect_unknown"):
        en += " A previous refresh has not been confirmed complete."
        zh += " 上次更新尚未确认完成。"
    elif state == "source_stale":
        en += " The source data also needs to refresh."
        zh += " 源数据也需要更新。"
    excluded = sum(1 for source in facts.get("sources", []) if isinstance(source, dict)
                   and source.get("status") != "included")
    if excluded:
        en += f" {excluded} older or undated background inputs were excluded from the new read."
        zh += f" 新解读排除了 {excluded} 项过时或无日期的背景数据。"
    return {
        "schema": SCHEMA, "lens": lens, "sequence": p.get("sequence", 0),
        "revision": content_id(p or brief or {"lens": lens}),
        "server_time": now.isoformat(), "status": status, "current": current,
        "message_en": en, "message_zh": zh, "brief": brief,
        "generated_at": (brief or {}).get("generated_at"), "state_asof": source_day,
        "valid_until": valid_until.isoformat() if valid_until else None,
        "facts": {"state_asof": facts_day, "current": facts_ok,
                  "key_facts": safe_facts(facts.get("key_facts"))},
    }


def health(root: Path, state_dir: Path, *, now: datetime | None = None) -> dict:
    """Public health metadata only; never brief text, operations or credentials."""
    now = now or datetime.now(timezone.utc)
    lenses = {}
    for lens in FILES:
        try:
            publication, fallback = read_publication(root, state_dir, lens)
            result = view(publication, fallback, lens=lens, now=now)
        except Exception:
            result = {"status": "unavailable", "current": False, "state_asof": None,
                      "generated_at": None, "valid_until": None}
        lenses[lens] = {key: result[key] for key in
                        ("status", "current", "state_asof", "generated_at", "valid_until")}
    return {"schema": "aibrief.health.v1", "checked_at": now.isoformat(),
            "ok": all(row["status"] == "available" for row in lenses.values()), "lenses": lenses}


def health_verdict(body: str | None, *, now: datetime) -> tuple[str, str]:
    """Existing freshness sentinel evaluates the actual reader contract clocks."""
    try:
        data = json.loads(body or "{}")["checks"]["ai_brief"]
        checked = utc(data.get("checked_at"))
        if data.get("schema") != "aibrief.health.v1" or not checked or not (
                now - timedelta(minutes=5) <= checked <= now + timedelta(minutes=1)):
            return "indeterminate", "AI Brief health is missing or its check clock is stale"
        rows = data["lenses"]
        if set(rows) != set(FILES):
            return "indeterminate", "AI Brief lens health is incomplete"
        stale = []
        for lens, row in rows.items():
            deadline = utc(row.get("valid_until"))
            if row.get("status") != "available" or row.get("current") is not True or not deadline or now >= deadline:
                stale.append(lens)
        return ("stale", "AI Brief requires attention: " + ", ".join(sorted(stale))) if stale else ("ok", "AI Brief content and evidence clocks are within budget")
    except (KeyError, ValueError, TypeError, AttributeError):
        return "indeterminate", "AI Brief health contract is unreadable"
