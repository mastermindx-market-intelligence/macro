"""Stdout-only research consumer for the existing options surface store.

R1 exposes only the installed audit capability, not the unqualified baseline.
Findings exit 0; invalid invocation/input exits 2 with a machine-readable error.
No input files, runtime artifacts, ledgers or model-promotion state are written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from engine.exposure_outlook_data import audit_surface_session
from engine.exposure_outlook_prices import audit_terminal_intraday


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    audit = commands.add_parser('audit-surface')
    audit.add_argument('--surface-dir', required=True, type=Path)
    audit.add_argument('--root', required=True)
    audit.add_argument('--session', required=True)
    audit.add_argument('--as-of', required=True)
    audit.add_argument('--layout', choices=('dated', 'current'), default='dated')
    audit.add_argument('--max-gap-seconds', type=int, default=300)
    price = commands.add_parser('audit-price')
    price.add_argument('--input', required=True, type=Path)
    price.add_argument('--root', required=True)
    price.add_argument('--session', required=True)
    price.add_argument('--as-of', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'audit-surface':
            out = audit_surface_session(args.surface_dir, args.root, args.session,
                                        as_of=args.as_of, layout=args.layout,
                                        max_gap_seconds=args.max_gap_seconds)
        else:
            with args.input.open('rb') as stream:
                raw = stream.read(16 * 1024 * 1024 + 1)
            if len(raw) > 16 * 1024 * 1024:
                raise ValueError('input exceeds 16 MiB read budget')
            out = audit_terminal_intraday(json.loads(raw), root=args.root, session=args.session,
                                          as_of=args.as_of)
            out['input_sha256'] = hashlib.sha256(raw).hexdigest()
        print(json.dumps(out, sort_keys=True, allow_nan=False))
        return 0
    except (ValueError, TypeError, OSError, OverflowError) as exc:
        print(json.dumps({'schema': 'options.exposure_outlook.research_error/v1',
                          'error': 'INVALID_RESEARCH_INPUT', 'detail': str(exc),
                          'authority_tier': 'research', 'can_publish': False}, sort_keys=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
