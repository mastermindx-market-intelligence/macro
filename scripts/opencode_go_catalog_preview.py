#!/usr/bin/env python3
"""Read-only OpenCode Go metadata preview. No keys, enrollment or inference."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

# Same repository import root; no arbitrary plugin path or remote execution.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.provider_subscription_catalog_opencode import (
    GoCatalogError, MAX_BYTES, Metadata, acquire_metadata, catalog_preview,
    parse_models, parse_published_terms, parse_terms,
)


def bounded_read(path: Path) -> bytes:
    with path.open('rb') as handle:
        raw = handle.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise GoCatalogError('FIXTURE_TOO_LARGE')
    return raw


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='Read public API and docs; never reads a key.')
    parser.add_argument('--models-file', type=Path)
    parser.add_argument('--terms-file', type=Path)
    parser.add_argument('--published-html', action='store_true')
    parser.add_argument('--observed-at', help='Required timestamp of supplied fixture evidence, not freshness renewal.')
    parser.add_argument('--now', help='Offline proof clock only.')
    args = parser.parse_args(argv)
    if args.live and any((args.models_file, args.terms_file, args.observed_at, args.now, args.published_html)):
        parser.error('live acquisition cannot take fixture arguments or a caller-selected clock')
    if not args.live and not all((args.models_file, args.terms_file, args.observed_at)):
        parser.error('choose --live or supply --models-file, --terms-file and --observed-at')
    try:
        if args.live:
            metadata = acquire_metadata()
            origin = 'public_metadata_not_account_entitlement'
        else:
            data = json.loads(bounded_read(args.models_file))
            raw = bounded_read(args.terms_file)
            terms = parse_published_terms(raw, observed_at=args.observed_at) if args.published_html else parse_terms(raw.decode('utf-8'), observed_at=args.observed_at)
            metadata = Metadata(parse_models(data, observed_at=args.observed_at), terms)
            origin = 'supplied_fixture_not_live_evidence'
        output = catalog_preview(metadata, now=args.now or datetime.now(timezone.utc).isoformat())
        output['acquisition_origin'] = origin
        print(json.dumps(output, sort_keys=True, indent=2))
        return 0
    except Exception:
        print(json.dumps({'error':'GO_METADATA_UNAVAILABLE', 'production_armed':False}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
