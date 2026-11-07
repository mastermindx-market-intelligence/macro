"""Operator CLI for the child harness (§26.2, §26.9). JSON out, exit code in.

    python3 -m tools.xguerrilla.cli status --db state.db
    python3 -m tools.xguerrilla.cli shadow --handle kid01 --steps steps.json \
        --screenshots /tmp/shadow --dry-run

Every subcommand prints exactly one JSON document to stdout. Exit 0 means the
operation succeeded (for ``shadow``: no drift); 1 means it ran and found a
problem; 2 is argparse usage; 3 means the requested runtime binding is unavailable.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from pathlib import Path

import yaml  # only third-party import allowed here

try:
    from . import net, persona, profiles, selector_shadow
    from .supervisor import Supervisor
    from .runtime_boundary import RuntimeBindingUnavailable, refuse_runtime
except ImportError:  # python3 tools/xguerrilla/cli.py
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import net  # type: ignore
    import persona  # type: ignore
    import profiles  # type: ignore
    import selector_shadow  # type: ignore
    from supervisor import Supervisor  # type: ignore
    from runtime_boundary import RuntimeBindingUnavailable, refuse_runtime  # type: ignore

DEFAULT_STORE = os.environ.get("XG_PROFILE_STORE", "~/.xguerrilla/profiles")
DEFAULT_DB = os.environ.get("XG_STATE_DB", "~/.xguerrilla/state.db")
DEFAULT_PERSONAS = os.environ.get("XG_PERSONAS", str(Path(__file__).with_name("personas")))
DEFAULT_PROXIES = os.environ.get("XG_PROXIES", str(Path(__file__).with_name("proxies.yml")))


def _emit(obj) -> None:
    print(json.dumps(obj, indent=2, sort_keys=True, default=str))


def _fail(exc: Exception) -> int:
    _emit({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
    return 1


def _common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--store", default=DEFAULT_STORE, help="profile store base dir")
    p.add_argument("--db", default=DEFAULT_DB, help="supervisor sqlite path")


def cmd_status(args) -> int:
    refuse_runtime("status")


def cmd_personas(args) -> int:
    rows = persona.load_dir(args.personas or DEFAULT_PERSONAS)
    _emit({"ok": True, "count": len(rows),
           "personas": [{"handle": h, **vars(p)} for h, p in sorted(rows.items())]})
    return 0


def cmd_net_check(args) -> int:
    slots = net.load(args.proxies or DEFAULT_PROXIES)
    _emit({"ok": True, "count": len(slots),
           "slots": [s.public() for s in slots]})
    return 0


def cmd_shadow(args) -> int:
    if not args.dry_run:
        refuse_runtime("shadow")
    raw = json.loads(Path(args.steps).read_text())
    steps = [selector_shadow.Step(name=s["name"], locate=s["locate"]) for s in raw]
    _emit({"ok": True, "dry_run": True, "checked": 0,
           "runtime_binding_available": False,
           "steps": [s.name for s in steps]})
    return 0


def cmd_snapshot(args) -> int:
    refuse_runtime("snapshot")


def cmd_restore(args) -> int:
    refuse_runtime("restore")


def cmd_verify(args) -> int:
    refuse_runtime("verify")


def cmd_degrade(args) -> int:
    refuse_runtime("degrade")


def cmd_recover(args) -> int:
    refuse_runtime("recover")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="xguerrilla",
                                 description=(__doc__ or "").splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("status", help="supervisor state and health")
    _common(p)
    p.add_argument("--personas", default=DEFAULT_PERSONAS)
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("personas", help="list persona rows")
    p.add_argument("--personas", default=DEFAULT_PERSONAS)
    p.set_defaults(func=cmd_personas)

    p = sub.add_parser("net-check", help="validate and list proxy slots")
    p.add_argument("--proxies", default=DEFAULT_PROXIES)
    p.set_defaults(func=cmd_net_check)

    p = sub.add_parser("shadow", help="resolve write steps against a live driver")
    _common(p)
    p.add_argument("--handle", required=True)
    p.add_argument("--steps", required=True, help="JSON list of {name, locate}")
    p.add_argument("--screenshots", default="./shadow-shots")
    p.add_argument("--driver", default=os.environ.get("XG_DRIVER_FACTORY", ""),
                   help="module:factory returning a driver")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_shadow)

    p = sub.add_parser("snapshot", help="tar.gz the profile and record its sha256")
    p.add_argument("handle")
    p.add_argument("--store", default=DEFAULT_STORE)
    p.set_defaults(func=cmd_snapshot)

    p = sub.add_parser("restore", help="restore a profile snapshot")
    p.add_argument("handle")
    p.add_argument("archive")
    p.add_argument("--store", default=DEFAULT_STORE)
    p.set_defaults(func=cmd_restore)

    p = sub.add_parser("verify", help="compare live tree to the manifest")
    p.add_argument("handle")
    p.add_argument("--store", default=DEFAULT_STORE)
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("degrade", help="unavailable without incumbent health binding")
    _common(p)
    p.add_argument("--reason", default="worker outage")
    p.add_argument("--personas", default=DEFAULT_PERSONAS)
    p.set_defaults(func=cmd_degrade)

    p = sub.add_parser("recover", help="unavailable without incumbent recovery binding")
    _common(p)
    p.add_argument("--personas", default=DEFAULT_PERSONAS)
    p.set_defaults(func=cmd_recover)
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except RuntimeBindingUnavailable as exc:
        _emit({"ok": False, "status": exc.code, "operation": exc.operation,
               "runtime_binding_available": False, "error": str(exc)})
        return 3
    except Exception as exc:
        return _fail(exc)


if __name__ == "__main__":
    raise SystemExit(main())
