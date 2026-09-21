"""Build the Mastermind snapshot page -> site/mastermind.html.

ONE static page that renders a governed point-in-time snapshot of the Portfolio/Mastermind
paper desk. The data (site/mastermind/mastermind_snapshot.json) is NOT produced here; it is
owned by the cross-repository publication lane. templates/mastermind.js fetches and renders
that tier-gated JSON client-side, bilingually, with explicit sign-in, upgrade, stale, archived,
and unavailable states.

This builder therefore does NO data work and is order-independent. Returns 0 on ANY error
so it can never break the rest of the site build.

Usage: python -m scripts.build_mastermind
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import config, site_assets  # noqa: E402
from lib.pages import write_page  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("build_mastermind")

# Shared nav/theme assets + the page's own renderer. The tier-gated snapshot JSON is
# produced by the governed cross-repository publication lane, not here.
ASSETS = ("theme.css", "theme.js", "mastermind.js")


def main() -> int:
    try:
        site = Path(config.load()["storage"]["site_dir"])
        site.mkdir(parents=True, exist_ok=True)

        env = Environment(loader=FileSystemLoader(
            str(Path(__file__).resolve().parent.parent / "templates")), autoescape=False)
        from engine import i18n
        env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)

        as_of = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        html = env.get_template("mastermind.html.j2").render(as_of=as_of)
        write_page(site / "mastermind.html", html)

        for a in ASSETS:
            src = Path(config.ROOT) / "templates" / a
            if src.exists():
                site_assets.copy_asset(a, src, site)
        log.info("wrote %s/mastermind.html (%d KB)", site, len(html) // 1024)
    except Exception as e:  # noqa: BLE001 — additive, must never break the site build
        log.error("Mastermind page build failed (%s); skipping", e)
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
