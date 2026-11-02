"""Build the options payoff lab artifact.

  1. ACCRUE — store host only. Read the ThetaData store, write
     data/options_payoff_lab/latest.json (replaced each session) and
     data/options_payoff_lab/history/<asof>.json (kept).
  2. EMIT — render hosts. Read data/options_payoff_lab/latest.json only.
     Never open the store. Write site/options_payoff_lab/latest.json.

No flag runs both legs. `--accrue` and `--emit` run one leg. When the store
does not resolve, ACCRUE prints a warning and writes nothing. A missing
input does not fail the lane.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import engine.options_skew as options_skew  # noqa: E402
import engine.thetadata_store as thetadata_store  # noqa: E402
from engine.options_payoff_lab import (  # noqa: E402
    SCHEMA,
    SOURCE,
    _json_safe,
    _state,
    _utc_now,
    build_payoff_lab,
)
from lib import config  # noqa: E402

log = logging.getLogger("build_options_payoff_lab")

_WARNING = (
    "::warning title=options-payoff-lab-source::"
    "The ThetaData store is not available, so this run did not write a payoff lab file."
)


def _parse(argv: list[str] | None):
    ap = argparse.ArgumentParser(prog="scripts.build_options_payoff_lab")
    ap.add_argument("--accrue", action="store_true",
                    help="read the store and write the data artifact; do not write the site file")
    ap.add_argument("--emit", action="store_true",
                    help="read the data artifact and write the site file; do not open the store")
    ap.add_argument("--data-dir", default=None,
                    help="override data/options_payoff_lab (the directory that holds latest.json)")
    ap.add_argument("--site-dir", default=None,
                    help="override the site root; the file lands in <site-dir>/options_payoff_lab/")
    args = ap.parse_args(argv)
    if args.accrue and not args.emit:
        do_accrue, do_emit = True, False
    elif args.emit and not args.accrue:
        do_accrue, do_emit = False, True
    else:
        do_accrue, do_emit = True, True
    return args, do_accrue, do_emit


def _data_dir(override: str | None) -> Path:
    if override:
        return Path(override)
    return config.data_dir() / "options_payoff_lab"


def _site_dir(override: str | None) -> Path:
    if override:
        return Path(override)
    return config.site_dir()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(_json_safe(payload), indent=2, allow_nan=False) + "\n"
    tmp = path.parent / f".{path.name}.{Path(str(id(path))).name}.tmp"
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _absent_payload() -> dict:
    return {
        "schema": SCHEMA,
        "asof": None,
        "generated_utc": _utc_now(),
        "source": SOURCE,
        "roots": [],
        "counts": {
            "roots_priced": 0,
            "structures_built": 0,
            "structures_null": 0,
        },
        "states": [_state(
            "ABSENT",
            "artifact",
            "No payoff lab file is on this host yet.",
            {"path": "data/options_payoff_lab/latest.json"},
        )],
        "ledger_asof": None,
        "accrual_state": "absent",
        "n": 0,
    }


def accrue(data_dir: Path) -> str:
    """Write the data artifact. Returns 'wrote', 'unresolved', or 'no_date'.

    An unresolved store prints the lane warning and does not touch the files.
    """
    store = thetadata_store.resolve_thetadata_store(
        required=False, purpose="options_payoff_lab")
    if store is None:
        print(_WARNING, flush=True)
        return "unresolved"
    asof = options_skew._latest_store_date(Path(store))
    if not asof:
        print(_WARNING, flush=True)
        return "no_date"
    payload = build_payoff_lab(asof, store=store)
    _write_json(data_dir / "latest.json", payload)
    _write_json(data_dir / "history" / f"{asof}.json", payload)
    log.info(
        "options_payoff_lab: wrote asof=%s roots_priced=%s structures_built=%s structures_null=%s",
        asof,
        payload["counts"]["roots_priced"],
        payload["counts"]["structures_built"],
        payload["counts"]["structures_null"],
    )
    return "wrote"


def emit(data_dir: Path, site_dir: Path, accrual_state: str = "ledger_only") -> dict:
    """Write the site file from the data artifact. Does not open the store."""
    if accrual_state not in ("accrued_today", "ledger_only"):
        raise ValueError(
            f"accrual_state must be accrued_today or ledger_only, got {accrual_state!r}"
        )
    src = data_dir / "latest.json"
    if not src.is_file():
        payload = _absent_payload()
    else:
        payload = json.loads(src.read_text(encoding="utf-8"))
        payload["ledger_asof"] = payload.get("asof")
        payload["accrual_state"] = accrual_state
        payload["n"] = int((payload.get("counts") or {}).get("structures_built") or 0)
    out = site_dir / "options_payoff_lab" / "latest.json"
    _write_json(out, payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args, do_accrue, do_emit = _parse(argv)
    data_dir = _data_dir(args.data_dir)
    site_dir = _site_dir(args.site_dir)
    wrote = False
    if do_accrue:
        status = accrue(data_dir)
        if status == "wrote":
            wrote = True
        elif status not in ("unresolved", "no_date"):
            return 1
    if do_emit:
        state = "accrued_today" if wrote else "ledger_only"
        payload = emit(data_dir, site_dir, accrual_state=state)
        log.info(
            "options_payoff_lab: emitted accrual_state=%s n=%s ledger_asof=%s",
            payload.get("accrual_state"), payload.get("n"), payload.get("ledger_asof"),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
