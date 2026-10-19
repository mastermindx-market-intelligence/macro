#!/usr/bin/env python3
"""One bounded installed-administrator E0 CONTROL inspection; no activation.

Only a study identity is accepted. The protected installed module supplies the
fixed private selection and source checks. No caller path, clock, permission,
provider, registration writer or study-admission action is exposed.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import resource
import signal
import sys

sys.dont_write_bytecode = True
_INSTALLED = Path("/opt/macro/scripts/inspect_market_memory_e0_control.py")
_OUTPUT_LIMIT = 32768


class _InvocationRefused(Exception):
    pass


def _expired(_signum, _frame):
    raise _InvocationRefused


def _failure(reason):
    return {"schema": "research_factory.market_memory_e0_control_inspection_failure.v1",
            "failure": reason, "operational_admission": False}


def main(argv=None):
    result = None
    rc = 78
    if (__spec__ is not None or __package__ not in (None, "")
            or sys.platform != "linux" or os.geteuid() != 0
            or Path(__file__).resolve() != _INSTALLED
            or not sys.argv or Path(sys.argv[0]).resolve() != _INSTALLED):
        result = _failure("installed_administrator_entry_required")
    else:
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (30, 32))
            signal.signal(signal.SIGALRM, _expired)
            signal.alarm(60)

            class Parser(argparse.ArgumentParser):
                def error(self, _message):
                    raise _InvocationRefused

            parser = Parser(add_help=False, allow_abbrev=False)
            parser.add_argument("--study-id", required=True)
            args = parser.parse_args(sys.argv[1:] if argv is None else argv)
            sys.path.insert(0, "/opt/macro")
            from engine.research_factory.market_memory_e0_installed_control import inspect_selected_control
            result = inspect_selected_control(args.study_id)
            rc = 0
        except (Exception, SystemExit):
            # No raw parser input, filesystem path, private body or traceback.
            result = _failure("selected_control_refused")
        finally:
            signal.alarm(0)
    body = json.dumps(result, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode() + b"\n"
    if len(body) > _OUTPUT_LIMIT:
        body = json.dumps(_failure("inspection_output_limit"), sort_keys=True,
                          separators=(",", ":")).encode() + b"\n"
        rc = 78
    sys.stdout.buffer.write(body)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
