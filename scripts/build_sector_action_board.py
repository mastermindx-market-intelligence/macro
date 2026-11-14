"""Build the source-bound action board consumed by US Sector Intelligence."""
from __future__ import annotations

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
from engine.sector_action_board import (  # noqa: E402
    ACTION_LANES as _ACTION_LANES, ActionBoardContractError,
    _basket_as_of, _board_has_rows, action_board_envelope,
    attach_two_reads, sector_setup_lookups,
)
log = logging.getLogger("build_sector_action_board")


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Strict JSON at the producer: a non-finite upstream value is *missing*
    # (null), never a bare NaN literal that a strict reader must reject, and
    # allow_nan=False makes anything the normalization misses fail the write
    # (leaving the previous artifact) instead of publishing it.
    from lib.numeric import finite_json_value
    raw = json.dumps(finite_json_value(payload), separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False).encode()
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
    """Bind the board to one observed basket byte snapshot and publish atomically.

    The basket date/hash identify the associated basket generation. They do not
    establish freshness or common provenance for every other board input.
    Invalid source/board content leaves the previous artifact untouched.
    """
    if not isinstance(action_board, dict):
        raise ActionBoardContractError("action_board must be a dictionary")
    if not _board_has_rows(action_board):
        raise ActionBoardContractError("action_board carries no actionable rows")
    try:
        basket_raw = baskets_path.read_bytes()
    except OSError as exc:
        raise ActionBoardContractError(f"basket source is unusable: {exc}") from exc
    payload = action_board_envelope(
        basket_raw=basket_raw, action_board=action_board,
        generated_utc=generated_utc,
    )
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
    setup_lookup, two_reads = sector_setup_lookups(sector_setups)

    board = canonical.action_board(
        sector_timing,
        notable,
        canonical.basket_action_items(site),
        sector_setup_lookup=setup_lookup,
    )
    if not isinstance(board, dict):
        raise ValueError("canonical action_board returned a non-dictionary")
    attach_two_reads(board, two_reads)

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
