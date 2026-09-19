"""Audit the production China-gold premium source -> VM -> rendered-page path.

The checker is READ-ONLY over market/source stores, the rendered site, and the
incumbent commodity machine projection. It writes one observability receipt under the
existing data/quality plane:

    data/quality/china_gold_premium.json

An unavailable source is an honest product state, not an audit failure.  The strict
exit only fails when the rendered Gold panel disagrees with the current engine
view-model (or the panel/page is absent), which is a product-path break rather than
a market-data outage.

Usage:
    python -m scripts.audit_china_gold_premium
    python -m scripts.audit_china_gold_premium --strict-render
    python -m scripts.audit_china_gold_premium --strict-render --require-live-ready
    python -m scripts.audit_china_gold_premium --strict-render --require-live-ready --require-method close_proxy
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine import china_gold_premium  # noqa: E402
from lib import config, store  # noqa: E402
from lib.dataos.registry import load_registry  # noqa: E402


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


def _iso_utc(value) -> str | None:
    if value is None:
        return None
    try:
        ts = pd.Timestamp(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if pd.isna(ts):
        return None
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return ts.isoformat()


def _close_proxy_source_artifacts(
    premium_cfg: dict,
    *,
    selected_asof: str | None = None,
) -> list[dict]:
    """Bind the configured close-proxy raw stores to the production receipt."""
    close_cfg = (
        premium_cfg.get("close_proxy")
        if isinstance(premium_cfg, dict)
        else None
    )
    close_cfg = close_cfg if isinstance(close_cfg, dict) else {}
    try:
        registry = load_registry()
        dataset_ids = {
            str(contract.storage): str(contract.dataset_id)
            for contract in registry.all()
            if getattr(contract, "storage", None) and getattr(contract, "dataset_id", None)
        }
    except Exception:
        dataset_ids = {}
    artifacts: list[dict] = []

    for role in ("sge", "global"):
        spec = close_cfg.get(role)
        spec = spec if isinstance(spec, dict) else {}
        group = str(spec.get("group") or "")
        name = str(spec.get("name") or "")
        column = str(spec.get("column") or "")
        path = (
            config.data_dir() / group / f"{name}.parquet"
            if group and name
            else None
        )
        exists = bool(path and path.exists())
        try:
            display_path = (
                str(path.relative_to(config.ROOT))
                if path is not None
                else None
            )
        except ValueError:
            display_path = str(path) if path is not None else None

        try:
            frame = store.read(group, name) if group and name else None
        except Exception:
            frame = None
        rows = int(len(frame)) if frame is not None else 0
        asof = (
            _iso_utc(frame.index[-1])
            if frame is not None and not frame.empty
            else None
        )
        selected_asof_present = None
        if selected_asof is not None:
            selected_asof_present = False
            if frame is not None and not frame.empty:
                try:
                    target = pd.Timestamp(selected_asof)
                    if target.tzinfo is None:
                        target = target.tz_localize("UTC")
                    else:
                        target = target.tz_convert("UTC")
                    observed = pd.DatetimeIndex(
                        pd.to_datetime(frame.index, errors="coerce", utc=True)
                    )
                    selected_asof_present = bool(target in observed)
                except (TypeError, ValueError, OverflowError):
                    selected_asof_present = False
        digest = None
        if exists and path is not None:
            try:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:
                digest = None

        storage = f"data/{group}/{name}.parquet" if group and name else ""
        artifacts.append(
            {
                "role": role,
                "dataset_id": dataset_ids.get(storage),
                "group": group or None,
                "name": name or None,
                "column": column or None,
                "path": display_path,
                "exists": exists,
                "rows": rows,
                "sha256": digest,
                "asof": asof,
                "selected_asof_present": selected_asof_present,
            }
        )
    return artifacts


def evaluate(
    vm: dict,
    html: str,
    *,
    machine_projection: dict | None = None,
    checked_at: str | None = None,
) -> dict:
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

    render_violations = list(violations)
    machine_violations: list[str] = []
    if machine_projection is not None:
        expected_machine = {
            "available": available,
            "method": vm.get("current_method"),
            "state": vm.get("state"),
            "source_asof": meta.get("asof"),
            "source_fresh": bool(meta.get("fresh")) if available else False,
            "official_canonical_available": bool(
                (vm.get("canonical") or {}).get("available")
            ),
            "context_only": True,
        }
        for key, expected in expected_machine.items():
            actual = machine_projection.get(key)
            if actual != expected:
                machine_violations.append(
                    f"machine.{key}: expected {expected}, rendered {actual}"
                )

        expected_machine_premium = vm.get("premium_pct")
        actual_machine_premium = machine_projection.get("premium_pct")
        try:
            premium_matches = (
                expected_machine_premium is None
                and actual_machine_premium is None
            ) or (
                expected_machine_premium is not None
                and actual_machine_premium is not None
                and abs(
                    float(expected_machine_premium)
                    - float(actual_machine_premium)
                )
                <= 5e-7
            )
        except (TypeError, ValueError):
            premium_matches = False
        if not premium_matches:
            machine_violations.append(
                "machine.premium_pct: expected "
                f"{expected_machine_premium}, rendered {actual_machine_premium}"
            )
        violations.extend(machine_violations)

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
        "render_consistent": not render_violations,
        "machine_projection_consistent": (
            None if machine_projection is None else not machine_violations
        ),
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
    machine_projection: dict | None = None,
    source_artifacts: list[dict] | None = None,
    out_path: Path | str | None = None,
    checked_at: str | None = None,
) -> dict:
    doc = evaluate(
        vm,
        html,
        machine_projection=machine_projection,
        checked_at=checked_at,
    )
    doc["source_artifacts"] = list(source_artifacts or [])
    promotion_blockers = live_ready_violations(
        doc,
        required_method="close_proxy",
        require_machine_projection=True,
        require_source_artifacts=True,
    )
    doc["close_proxy_dataos_promotion_ready"] = not promotion_blockers
    doc["close_proxy_dataos_promotion_blockers"] = promotion_blockers
    path = Path(out_path) if out_path is not None else (
        config.data_dir() / "quality" / "china_gold_premium.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    return doc


def live_ready_violations(
    doc: dict,
    *,
    required_method: str | None = None,
    require_machine_projection: bool = False,
    require_source_artifacts: bool = False,
) -> list[str]:
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
    if (
        require_machine_projection
        and doc.get("machine_projection_consistent") is not True
    ):
        blockers.append("machine projection was not proven consistent")
    if require_source_artifacts:
        artifacts = doc.get("source_artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            blockers.append("source artifacts were not proven")
        else:
            by_role = {
                str(item.get("role")): item
                for item in artifacts
                if isinstance(item, dict) and item.get("role")
            }
            source_asof = str(doc.get("source_asof") or "")
            for role in ("sge", "global"):
                item = by_role.get(role)
                if not isinstance(item, dict) or item.get("exists") is not True:
                    blockers.append(f"source artifact {role} was not proven")
                    continue
                dataset_id = str(item.get("dataset_id") or "")
                if not dataset_id:
                    blockers.append(
                        f"source artifact {role} Data OS id is not bound"
                    )
                try:
                    rows = int(item.get("rows") or 0)
                except (TypeError, ValueError):
                    rows = 0
                if rows < 1:
                    blockers.append(f"source artifact {role} has no rows")
                digest = str(item.get("sha256") or "")
                if len(digest) != 64 or any(
                    ch not in "0123456789abcdef" for ch in digest.lower()
                ):
                    blockers.append(f"source artifact {role} sha256 is not bound")
                if item.get("selected_asof_present") is not True:
                    blockers.append(
                        f"source artifact {role} does not contain headline "
                        f"asof {source_asof or 'none'}"
                    )
    if required_method is not None:
        method = str(doc.get("headline_method") or "none")
        if method != required_method:
            blockers.append(
                f"headline method is {method}, required {required_method}"
            )
    return blockers


def run(
    *,
    strict_render: bool = False,
    require_live_ready: bool = False,
    required_method: str | None = None,
) -> int:
    cfg = config.load()
    premium_cfg = (cfg.get("commodities") or {}).get("china_gold_premium") or {}
    vm = china_gold_premium.build_view_model(premium_cfg)

    site = config.ROOT / cfg["storage"]["site_dir"] / "commodities.html"
    try:
        html = site.read_text()
    except OSError:
        html = ""

    # The page and the incumbent machine feed are sibling projections of the
    # same display-tier VM. Treat a missing/corrupt machine projection as an
    # empty object so the strict audit fails closed rather than silently
    # downgrading to a page-only proof.
    machine_projection: dict = {}
    machine_path = config.data_dir() / "commodity" / "latest.json"
    try:
        payload = json.loads(machine_path.read_text())
        candidate = (
            (payload.get("gold_context") or {}).get("china_physical_premium")
            if isinstance(payload, dict)
            else None
        )
        if isinstance(candidate, dict):
            machine_projection = candidate
    except (OSError, ValueError, TypeError):
        pass

    doc = write_receipt(
        vm,
        html,
        machine_projection=machine_projection,
        source_artifacts=_close_proxy_source_artifacts(
            premium_cfg,
            selected_asof=(vm.get("close_proxy") or {}).get("asof"),
        ),
    )

    if doc["status"] == "render_mismatch":
        detail = "; ".join(doc["violations"]) or "unknown render mismatch"
        print(
            f"::error title=China gold premium render mismatch::{detail}; "
            "see data/quality/china_gold_premium.json"
        )
        return 2 if strict_render or require_live_ready else 0

    if require_live_ready:
        blockers = live_ready_violations(
            doc,
            required_method=required_method,
            require_machine_projection=True,
            require_source_artifacts=(
                required_method == "close_proxy"
                or doc.get("headline_method") == "close_proxy"
            ),
        )
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
            "exit 3 unless the source is fresh, the render and machine projection "
            "are consistent, both 5-/30-session statistics are ready, and a selected "
            "close-proxy method has both raw source artifacts bound"
        ),
    )
    ap.add_argument(
        "--require-method",
        choices=("canonical", "close_proxy", "intraday"),
        default=None,
        help="with --require-live-ready, require this exact headline method",
    )
    args = ap.parse_args(argv)
    try:
        return run(
            strict_render=args.strict_render,
            require_live_ready=args.require_live_ready,
            required_method=args.require_method,
        )
    except Exception as exc:  # noqa: BLE001 — audit crashes must be visible
        log.error("China gold premium audit crashed: %s", exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
