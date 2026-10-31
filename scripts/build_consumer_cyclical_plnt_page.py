"""Render the Consumer Cyclical PLNT synthetic display card.

One card, mounted from ``display_packet`` over the committed synthetic
fixture ``data/sector_intelligence/fixtures/
consumer_cyclical_intelligence_read_model.v1.valid.json`` — read, never
written. The builder prints the projection lead, the advertising net-change
figure, the document availability, the shared-contract status and the
synthetic provenance exactly as the packet reports them: an ``unavailable``
document prints as unavailable, a withheld or absent advertising row prints
as withheld or absent instead of a bare figure, and ``filing_claim`` stays
false on the card. The Cyclical-owned ``native_admitted`` refusal raised by
``display_packet`` propagates here BEFORE any write, so a refusal leaves no
page at the destination.

No data/ write, no site/ write in the test path (tests pass a tmp root), no
EDGAR, no theme-graph store, no vertical enrollment. Navigation comes from
the existing anonymous public chrome; presentation comes from theme.css
tokens.

Usage:
    python -m scripts.build_consumer_cyclical_plnt_page
    python -m scripts.build_consumer_cyclical_plnt_page --root /path/to/out-repo
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from engine.sector_intelligence.consumer_cyclical_display import display_packet  # noqa: E402

TEMPLATE_NAME = "consumer_cyclical_plnt.html.j2"
PAGE_NAME = "consumer_cyclical_plnt.html"
FIXTURE_PATH = (
    _REPO_ROOT
    / "data"
    / "sector_intelligence"
    / "fixtures"
    / "consumer_cyclical_intelligence_read_model.v1.valid.json"
)


def load_case(fixture_path: Path = FIXTURE_PATH) -> dict[str, Any]:
    """Read the committed synthetic fixture's case fields — read, never written."""
    fixture = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
    return {
        "subject": fixture["subject"],
        "comparison_basis": fixture["comparison_basis"],
        "facts": fixture["facts"],
        "generated_at": fixture["generated_at"],
        "source_records": fixture["source_records"],
    }


def build_packet(fixture_path: Path = FIXTURE_PATH) -> dict[str, Any]:
    """The display packet for the committed fixture, refusal included.

    Raises ``ConsumerCyclicalDisplayRefusal`` (from ``display_packet``) when
    any fact is native-admitted; no packet, hence no page, is produced.
    """
    return display_packet(load_case(fixture_path))


def render(root: Path, *, fixture_path: Path | None = None) -> Path:
    """Write the one-card PLNT display page under ``root/site`` and return it.

    The packet is built first: a native-admitted refusal raises here, before
    any directory or file is created. ``root`` is the output carrier (the
    repository root in the full-site build, a tmp dir in tests); templates
    and the fixture are always read from the code checkout.
    """
    root = Path(root).resolve()
    packet = build_packet(Path(fixture_path) if fixture_path else FIXTURE_PATH)
    env = Environment(
        loader=FileSystemLoader(str(_REPO_ROOT / "templates")),
        autoescape=True,
        undefined=StrictUndefined,
    )
    html = env.get_template(TEMPLATE_NAME).render(packet=packet, rel="")
    # Shared navigation templates contain indentation around conditional
    # blocks; normalize generated-only blank-line whitespace so the page
    # stays diff-clean without modifying global nav output.
    html = "\n".join(line.rstrip() for line in html.splitlines()) + "\n"
    site = root / "site"
    site.mkdir(parents=True, exist_ok=True)
    from lib.pages import write_page  # noqa: PLC0415 — site HTML must go through the shim writer

    return write_page(site / PAGE_NAME, html)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=_REPO_ROOT)
    parser.add_argument("--fixture", type=Path, default=None)
    args = parser.parse_args(argv)
    print(render(args.root, fixture_path=args.fixture))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
