#!/usr/bin/env python3
"""FIF coverage step 6 (b3): write the served-only draft coverage manifest.

Reads the coverage tiers file, the five-issuer-style coverage contract (the
``security_master_binding.issuer_id`` binding), and a LOCAL production
dataset store directory, and writes one canonical
``fundamental_forensics.coverage_manifest/v1`` document to ``--out``.  The
manifest is what the coverage proof (``scripts/fif_coverage_proof.py``)
recomputes; it is always ``draft: true`` and ``attested: false``.

Exit codes:
  * 0 — the manifest was written;
  * 2 — an input refusal (``CoverageManifestError``; its code is printed).

No network: ``--store-dir`` must be an existing local directory, so the
store never falls back to an environment-configured remote.  No wall clock:
``--as-of`` is the only clock and the same inputs give the same bytes.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from engine.fundamental_forensics.coverage_manifest import (  # noqa: E402
    DEFAULT_CATALOG,
    DEFAULT_FORMULAS,
    DEFAULT_THRESHOLDS,
    CoverageManifestError,
    build_coverage_manifest,
    render_manifest,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fif_coverage_manifest.py",
        description="Write the served-only draft FIF coverage manifest.",
    )
    parser.add_argument("--tiers-file", required=True, help="coverage tiers JSON")
    parser.add_argument(
        "--coverage-file",
        required=True,
        help="coverage contract JSON carrying security_master_binding.issuer_id",
    )
    parser.add_argument(
        "--store-dir",
        required=True,
        help="LOCAL production dataset store directory (never a remote)",
    )
    parser.add_argument(
        "--as-of",
        required=True,
        help="timezone-aware UTC cutoff; the only clock the manifest uses",
    )
    parser.add_argument("--out", required=True, help="manifest output path")
    parser.add_argument(
        "--thresholds",
        default=str(DEFAULT_THRESHOLDS),
        help="frozen C2 thresholds (defaults to the repository config path)",
    )
    parser.add_argument(
        "--catalog",
        default=str(DEFAULT_CATALOG),
        help="metric catalog YAML (defaults to the repository path)",
    )
    parser.add_argument(
        "--formulas",
        default=str(DEFAULT_FORMULAS),
        help="metric formulas YAML (defaults to the repository path)",
    )
    args = parser.parse_args(argv)
    try:
        manifest = build_coverage_manifest(
            tiers_file=args.tiers_file,
            coverage_file=args.coverage_file,
            store_dir=args.store_dir,
            as_of=args.as_of,
            thresholds_file=args.thresholds,
            catalog_file=args.catalog,
            formulas_file=args.formulas,
        )
    except CoverageManifestError as exc:
        print(f"coverage manifest refused: {exc.code}: {exc.message}", file=sys.stderr)
        return 2
    payload = render_manifest(manifest)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(payload)
    issuers = manifest["issuers"]
    served = sum(1 for issuer in issuers if issuer["serve_state"] == "served")
    print(
        f"coverage manifest: {len(issuers)} issuers, {served} served, "
        f"{len(manifest['cells'])} cells -> {out}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
