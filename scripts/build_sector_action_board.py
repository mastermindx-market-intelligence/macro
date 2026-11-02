"""Build the source-bound action board consumed by US Sector Intelligence."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from jinja2 import Environment, FileSystemLoader  # noqa: E402
log = logging.getLogger("build_sector_action_board")


def _basket_as_of(payload: dict[str, Any]) -> str:
    top = payload.get("as_of")
    theme = (payload.get("theme_intel") or {}).get("as_of") \
        if isinstance(payload.get("theme_intel"), dict) else None
    if not isinstance(top, str) or not top:
        raise ValueError("baskets.json carries no usable top-level as_of")
    if not isinstance(theme, str) or not theme:
        raise ValueError("baskets.json carries no usable theme_intel.as_of")
    if top != theme:
        raise ValueError(
            f"baskets.json vintage split: as_of={top}, theme_intel.as_of={theme}"
        )
    return top


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def write_action_board(
    output: Path,
    *,
    baskets_path: Path,
    action_board: dict[str, Any],
    generated_utc: str,
) -> dict[str, Any]:
    """Write a self-describing board bound to the exact basket bytes."""
    basket_raw = baskets_path.read_bytes()
    basket_payload = json.loads(basket_raw)
    if not isinstance(basket_payload, dict):
        raise ValueError("baskets.json must contain a JSON object")
    if not isinstance(action_board, dict):
        raise ValueError("action_board must be a dictionary")
    as_of = _basket_as_of(basket_payload)
    payload = {
        "schema": "sector_intelligence_action_board.v1",
        "as_of": as_of,
        "generated_utc": generated_utc,
        "baskets_sha256": hashlib.sha256(basket_raw).hexdigest(),
        "action_board": action_board,
    }
    _atomic_json_write(output, payload)
    return payload


def _environment(root: Path) -> Environment:
    env = Environment(loader=FileSystemLoader(root / "templates"), autoescape=True)
    env.filters["min"] = lambda seq: min(seq)
    try:
        from engine import i18n
        from lib.seo import SITE_BASE

        env.globals.update(
            td=i18n.td,
            tr=i18n.tr,
            t_pctile=i18n.t_pctile,
            zip=zip,
            SITE_BASE=SITE_BASE,
        )
    except Exception:  # noqa: BLE001 - tests and degraded builders can use English
        env.globals.update(
            td=lambda en: en,
            tr=lambda en: en,
            t_pctile=lambda value: value,
            zip=zip,
            SITE_BASE="https://www.mastermind-x.com",
        )
    return env


def _canonical_module():
    from scripts import build_site

    return build_site


def build_action_board(
    *,
    root: Path = ROOT,
    canonical=None,
    generated_utc: str | None = None,
) -> dict[str, Any]:
    """Build the canonical board after the basket producer has refreshed."""
    root = Path(root)
    site = root / "site"
    canonical = canonical or _canonical_module()
    generated_utc = generated_utc or datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    latest_path = root / "data" / "regime" / "latest.json"
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    if not isinstance(latest, dict):
        raise ValueError("data/regime/latest.json must contain a JSON object")

    env = _environment(root)
    alpha_data = None
    try:
        alpha_data = canonical.build_alpha_data(site)
    except Exception as exc:  # noqa: BLE001 - mirrors the existing additive path
        log.warning("alpha data failed: %s", exc)
    try:
        canonical.build_insider_data(site)
    except Exception as exc:  # noqa: BLE001 - confirmer context is additive
        log.warning("insider data failed: %s", exc)

    put_absent = (latest.get("dislocation") or {}).get("put_state") == "put-absent"
    rate_infl = {
        stage["ticker"]: stage.get("rate_inflation")
        for stage in ((latest.get("playbook") or {}).get("stages") or [])
        if isinstance(stage, dict) and stage.get("ticker") and stage.get("rate_inflation")
    }
    sector_timing, notable = canonical.build_sector_pages(
        env,
        site,
        generated_utc,
        alpha=alpha_data,
        put_absent=put_absent,
        rate_infl=rate_infl,
    )

    sector_setups = canonical.sector_setup_view(latest, sector_timing)
    setup_lookup: dict[str, dict[str, Any]] = {}
    two_reads: dict[str, dict[str, Any]] = {}
    if isinstance(sector_setups, dict):
        for row in sector_setups.get("sectors") or []:
            if not isinstance(row, dict) or not row.get("ticker"):
                continue
            setup_lookup[row["ticker"]] = row
            if isinstance(row.get("two_reads_chip"), dict):
                two_reads[row["ticker"]] = row["two_reads_chip"]

    board = canonical.action_board(
        sector_timing,
        notable,
        canonical.basket_action_items(site),
        sector_setup_lookup=setup_lookup,
    )
    if not isinstance(board, dict):
        raise ValueError("canonical action_board returned a non-dictionary")
    if two_reads:
        for lane in (*_ACTION_LANES, "notable"):
            for item in board.get(lane) or []:
                if not isinstance(item, dict):
                    continue
                ticker = item.get("ticker")
                if item.get("kind") == "sector" and ticker in two_reads:
                    item["two_reads_chip"] = two_reads[ticker]

    output = site / "basketdata" / "action_board.json"
    payload = write_action_board(
        output,
        baskets_path=site / "basketdata" / "baskets.json",
        action_board=board,
        generated_utc=generated_utc,
    )
    log.info(
        "built %s (as_of=%s, total=%s)",
        output,
        payload["as_of"],
        board.get("total"),
    )
    return payload


_ACTION_LANES = (
    "buy_now", "buy_soon", "on_the_run", "take_profits", "hold", "avoid",
)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        build_action_board()
    except Exception as exc:  # noqa: BLE001 - workflow needs a typed nonzero boundary
        log.exception("Sector Intelligence action-board build failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
