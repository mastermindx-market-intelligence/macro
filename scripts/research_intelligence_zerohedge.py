"""One-shot ZeroHedge deep-read operator for the existing Research Intelligence path."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Sequence
from urllib.request import Request, urlopen

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine import qbus
from engine.research_intelligence.projection import summary_points
from engine.research_intelligence.store import ResearchIntelligenceStoreError, persist_analysis
from engine.research_intelligence.zerohedge_adapter import (
    ZEROHEDGE_SOURCE_KEY,
    analyze_candidate,
    parse_zerohedge_feed,
    qbus_projection,
    select_candidates,
)
from engine.research_vault.r2_store import StrictConditionalWriteStore, build_store

_MAX_FEED_BYTES = 10 * 1024 * 1024
_TIMEOUT_S = 10


def _emit(value: dict[str, Any], *, stream=sys.stdout) -> None:
    print(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        file=stream,
        flush=True,
    )


def _load_source(config_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    import yaml

    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    breaking = cfg.get("breaking")
    if not isinstance(breaking, dict):
        raise ValueError("marketing config has no breaking section")
    for source in breaking.get("sources") or []:
        if isinstance(source, dict) and source.get("key") == ZEROHEDGE_SOURCE_KEY:
            selected = dict(source)
            selected.setdefault("poll_interval_s", breaking.get("poll_interval_s", 300))
            selected.setdefault(
                "user_agent",
                breaking.get("user_agent", "MastermindBreakingBot/1.0"),
            )
            return breaking, selected
    raise ValueError("zerohedge_feed is not configured")


def _fetch(source: dict[str, Any]) -> str:
    url = str(source.get("url") or "")
    if not url.lower().startswith(("https://", "http://")):
        raise ValueError("ZeroHedge feed URL must be http(s)")
    req = Request(url, headers={"User-Agent": str(source.get("user_agent") or "")})
    with urlopen(req, timeout=_TIMEOUT_S) as response:  # noqa: S310
        payload = response.read(_MAX_FEED_BYTES + 1)
    if len(payload) > _MAX_FEED_BYTES:
        raise ValueError("ZeroHedge feed exceeds bounded input size")
    return payload.decode("utf-8", errors="replace")


def _store(local_dir: str | None) -> StrictConditionalWriteStore:
    store = build_store(local_dir=local_dir)
    if not isinstance(store, StrictConditionalWriteStore):
        raise ResearchIntelligenceStoreError(
            "store_unavailable", "Research Vault strict store is not configured"
        )
    return store


def _existing_qbus_rows() -> list[dict[str, Any]]:
    frame = qbus.read_items()
    if frame is None:
        return []
    return frame.to_dict("records")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deep-read the deterministic head of the configured ZeroHedge RSS feed"
    )
    parser.add_argument("--model", required=True, help="requested model id routed by llm_auth")
    parser.add_argument("--limit", type=int, default=5, help="maximum deep-read candidates")
    parser.add_argument("--config", default=str(_ROOT / "config" / "marketing.yml"))
    parser.add_argument("--feed-file", help="offline RSS payload instead of a network fetch")
    parser.add_argument("--local", metavar="DIR", help="local Research Vault store for proof/testing")
    parser.add_argument(
        "--append-qbus",
        action="store_true",
        help="append the quote-free metadata projection to the canonical qbus",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        breaking_cfg, source = _load_source(Path(args.config).expanduser())
        xml_text = (
            Path(args.feed_file).expanduser().read_text(encoding="utf-8")
            if args.feed_file
            else _fetch(source)
        )
        now = datetime.now(tz=timezone.utc)
        articles = parse_zerohedge_feed(xml_text, source)
        candidates = select_candidates(
            articles,
            now=now,
            breaking_cfg=breaking_cfg,
            limit=max(0, args.limit),
            root=_ROOT,
        )
        if not candidates:
            _emit({"state": "no_candidates", "source": ZEROHEDGE_SOURCE_KEY})
            return 3

        store = _store(args.local)
        existing_rows = _existing_qbus_rows() if args.append_qbus else []
        failures = 0
        for candidate in candidates:
            item = candidate["feed_item"]
            analysis = analyze_candidate(candidate, model_id=args.model)
            if analysis.get("state") != "ok":
                failures += 1
                _emit(
                    {
                        "state": "analysis_failed",
                        "document_id": item.get("id"),
                        "analysis_state": analysis.get("state"),
                    },
                    stream=sys.stderr,
                )
                continue
            receipt = persist_analysis(
                store,
                analysis,
                source_body=candidate["research_body"],
            )
            qbus_state = "not_requested"
            event_key = ""
            if args.append_qbus:
                row = qbus_projection(
                    candidate,
                    observed_at=now.isoformat(),
                    existing_rows=existing_rows,
                )
                appended = qbus.append_items([row], assign_keys=False)
                if appended is None:
                    qbus_state = "failed"
                    failures += 1
                else:
                    qbus_state = "appended"
                    event_key = row["event_key"]
                    existing_rows.append(row)
            _emit(
                {
                    "state": "ok",
                    "source": ZEROHEDGE_SOURCE_KEY,
                    "document_id": item.get("id"),
                    "url": item.get("url"),
                    "salience": item.get("salience"),
                    "artifact": receipt.to_dict(),
                    "summary_points": summary_points(analysis["rio"]),
                    "qbus_state": qbus_state,
                    "event_key": event_key,
                }
            )
        return 2 if failures else 0
    except (OSError, ValueError, TypeError, ResearchIntelligenceStoreError) as exc:
        code = getattr(exc, "code", type(exc).__name__)
        _emit({"state": "error", "code": code}, stream=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
