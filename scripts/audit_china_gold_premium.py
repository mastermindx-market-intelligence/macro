"""Audit the production China-gold premium source -> VM -> rendered-page path.

The checker is READ-ONLY over market/source stores and the rendered site.  It writes
one observability receipt under the existing data/quality plane:

    data/quality/china_gold_premium.json

An unavailable source is an honest product state, not an audit failure.  The strict
exit only fails when the rendered Gold panel disagrees with the current engine
view-model (or the panel/page is absent), which is a product-path break rather than
a market-data outage.

Usage:
    python -m scripts.audit_china_gold_premium
    python -m scripts.audit_china_gold_premium --strict-render
    python -m scripts.audit_china_gold_premium --strict-render --require-live-ready
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine import china_gold_premium  # noqa: E402
from lib import config  # noqa: E402


log = logging.getLogger("china_gold_premium_audit")
SCHEMA = "commodity.china_gold_premium_quality.v1"


class _PremiumPanelParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.attrs: dict[str, str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        if self.attrs is not None:
            return
        pairs = {str(k): "" if v is None else str(v) for k, v in attrs}
        if pairs.get("id") == "gold-china-premium":
            self.attrs = pairs


def _panel_attrs(html: str) -> dict[str, str] | None:
    parser = _PremiumPanelParser()
    parser.feed(html or "")
    parser.close()
    return parser.attrs


def _method_meta(vm: dict) -> dict:
    method = vm.get("current_method")
    if method == "close_proxy":
        return vm.get("close_proxy") or {}
    if method == "intraday":
        return vm.get("intraday") or {}
    if method == "canonical":
        return vm.get("canonical") or {}
    return {}


def evaluate(vm: dict, html: str, *, checked_at: str | None = None) -> dict:
    checked_at = checked_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    attrs = _panel_attrs(html)
    available = bool(vm.get("available"))
    violations: list[str] = []

    if attrs is None:
        violations.append("panel_missing")
        rendered_state = rendered_source = rendered_currency = None
        rendered_asof = rendered_premium_raw = None
    else:
        rendered_state = attrs.get("data-cgp-state")
        rendered_source = attrs.get("data-cgp-display-source")
        rendered_currency = attrs.get("data-cgp-currency")
        rendered_asof = attrs.get("data-cgp-source-asof")
        rendered_premium_raw = attrs.get("data-cgp-premium")

    expected_state = str(vm.get("state") or ("unavailable" if not available else ""))
    if rendered_state is not None and rendered_state != expected_state:
        violations.append(
            f"state: expected {expected_state}, rendered {rendered_state}"
        )

    expected_source = None
    expected_currency = None
    expected_asof = None
    expected_premium = None
    meta = _method_meta(vm)
    if available:
        expected_source = (vm.get("chart") or {}).get("display_source") or "canonical"
        expected_currency = vm.get("price_currency") or "USD"
        expected_asof = meta.get("asof")
        expected_premium = vm.get("premium_pct")
        if rendered_source is not None and rendered_source != expected_source:
            violations.append(
                f"display_source: expected {expected_source}, rendered {rendered_source}"
            )
        if rendered_currency is not None and rendered_currency != expected_currency:
            violations.append(
                f"currency: expected {expected_currency}, rendered {rendered_currency}"
            )
        if rendered_asof != (expected_asof or ""):
            violations.append(
                f"source_asof: expected {expected_asof or ''}, rendered {rendered_asof or ''}"
            )
        try:
            rendered_premium = float(rendered_premium_raw) if rendered_premium_raw not in (None, "") else None
        except (TypeError, ValueError):
            rendered_premium = None
        if (
            expected_premium is None
            or rendered_premium is None
            or abs(float(expected_premium) - rendered_premium) > 5e-7
        ):
            violations.append(
                f"premium_pct: expected {expected_premium}, rendered {rendered_premium}"
            )
    else:
        rendered_premium = None

    source_fresh = bool(meta.get("fresh")) if available else False
    if violations:
        status = "render_mismatch"
    elif not available:
        status = "honest_unavailable"
    elif source_fresh:
        status = "available_fresh"
    else:
        status = "available_stale"

    methods = {}
    for method_name in ("canonical", "intraday", "close_proxy"):
        method = vm.get(method_name) or {}
        methods[method_name] = {
            "available": bool(method.get("available")),
            "fresh": bool(method.get("fresh")),
            "asof": method.get("asof"),
        }

    chart = vm.get("chart") or {}
    if expected_source == "proxy":
        history_points = len(chart.get("proxy") or [])
    elif expected_source == "canonical":
        history_points = len(chart.get("canonical") or [])
    else:
        history_points = 1 if chart.get("intraday") else 0
    stats = vm.get("stats") or {}

    return {
        "schema": SCHEMA,
        "checked_at": checked_at,
        "status": status,
        "render_consistent": not violations,
        "available": available,
        "headline_method": vm.get("current_method"),
        "headline_state": vm.get("state"),
        "premium_pct": vm.get("premium_pct"),
        "expected_display_source": expected_source,
        "rendered_display_source": rendered_source,
        "expected_currency": expected_currency,
        "rendered_currency": rendered_currency,
        "rendered_state": rendered_state,
        "rendered_source_asof": rendered_asof,
        "rendered_premium_pct": rendered_premium,
        "source_fresh": source_fresh,
        "source_asof": meta.get("asof"),
        "sources": list(meta.get("sources") or []),
        "reason_code": vm.get("reason_code"),
        "official_canonical_available": methods["canonical"]["available"],
        "methods": methods,
        "history_points": history_points,
        "stats_5_ready": stats.get("avg_5") is not None,
        "stats_30_ready": stats.get("range_30") is not None,
        "violations": violations,
    }


def write_receipt(
    vm: dict,
    html: str,
    *,
    out_path: Path | str | None = None,
    checked_at: str | None = None,
) -> dict:
    doc = evaluate(vm, html, checked_at=checked_at)
    path = Path(out_path) if out_path is not None else (
        config.data_dir() / "quality" / "china_gold_premium.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    return doc


def live_ready_violations(doc: dict) -> list[str]:
    """Return blockers for the post-merge live-product acceptance gate."""
    blockers: list[str] = []
    if not doc.get("render_consistent"):
        blockers.append("render contract is not consistent")
    status = str(doc.get("status") or "unknown")
    if status != "available_fresh":
        blockers.append(f"status is {status}, not available_fresh")
    if not doc.get("stats_5_ready"):
        blockers.append("5-session average is not ready")
    if not doc.get("stats_30_ready"):
        blockers.append("30-session range is not ready")
    return blockers


def run(*, strict_render: bool = False, require_live_ready: bool = False) -> int:
    cfg = config.load()
    premium_cfg = (cfg.get("commodities") or {}).get("china_gold_premium") or {}
    vm = china_gold_premium.build_view_model(premium_cfg)

    site = config.ROOT / cfg["storage"]["site_dir"] / "commodities.html"
    try:
        html = site.read_text()
    except OSError:
        html = ""

    doc = write_receipt(vm, html)

    if doc["status"] == "render_mismatch":
        detail = "; ".join(doc["violations"]) or "unknown render mismatch"
        print(
            f"::error title=China gold premium render mismatch::{detail}; "
            "see data/quality/china_gold_premium.json"
        )
        return 2 if strict_render or require_live_ready else 0

    if require_live_ready:
        blockers = live_ready_violations(doc)
        if blockers:
            print(
                "::error title=China gold premium live proof incomplete::"
                + "; ".join(blockers)
                + "; see data/quality/china_gold_premium.json"
            )
            return 3

    if doc["status"] == "honest_unavailable":
        print(
            "China gold premium: honest unavailable "
            f"({doc.get('reason_code') or 'no current source'}); "
            "receipt=data/quality/china_gold_premium.json"
        )
        return 0

    freshness = "fresh" if doc["source_fresh"] else "stale"
    print(
        "China gold premium: "
        f"{doc['headline_method']} {freshness} asof={doc.get('source_asof') or '—'} "
        f"premium={doc.get('premium_pct')}%; "
        "receipt=data/quality/china_gold_premium.json"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--strict-render",
        action="store_true",
        help="exit 2 when the rendered Gold panel disagrees with the engine VM",
    )
    ap.add_argument(
        "--require-live-ready",
        action="store_true",
        help=(
            "exit 3 unless the source is fresh, the render is consistent, and "
            "both the 5- and 30-session statistics are ready"
        ),
    )
    args = ap.parse_args(argv)
    try:
        return run(
            strict_render=args.strict_render,
            require_live_ready=args.require_live_ready,
        )
    except Exception as exc:  # noqa: BLE001 — audit crashes must be visible
        log.error("China gold premium audit crashed: %s", exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
