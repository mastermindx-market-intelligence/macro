"""Build the Finviz *themes* treemap data feed (offline-safe).

Reads the committed Finviz snapshot (``data/themes_heatmap/themes_tree.json`` +
``perf_snapshot.json``, refreshed by ``scripts/fetch_finviz_themes.py``) and
writes ``site/marketdata/themes_heatmap.json``, consumed by the themes map-type
of ``site/sector_heatmap.html``. No network: the snapshot is the source of
record, so CI/offline builds always render.

Usage
-----
    python -m scripts.build_themes_heatmap
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import theme_rerating_durability as trd  # noqa: E402
from engine import theme_revisions as tr  # noqa: E402
from engine import themes_heatmap as th  # noqa: E402
from lib import config  # noqa: E402

log = logging.getLogger("build_themes_heatmap")


def _data(*parts: str) -> Path:
    return config.data_dir().joinpath(*parts)


_AUTO = object()


def _attach_revision_durability(payload: dict, tree: list, *, latest=_AUTO, hist=_AUTO) -> bool:
    """Attach named revision confirmation to the EXISTING owner heatmap payload.

    Missing revision stores are an honest no-op; the heatmap keeps its price context.
    Tests can inject frames directly without touching the data plane.
    """
    if latest is _AUTO:
        latest = tr._latest()
    if latest is None:
        return False
    if hist is _AUTO:
        hist = tr._history()
    price_context = {
        "subthemes": [tile["repricing"] for tile in payload.get("tiles", [])
                      if isinstance(tile.get("repricing"), dict)]
    }
    durability = trd.build_durability(tree, price_context, latest, hist)
    by_key = {row["key"]: row for row in durability["subthemes"]}
    for tile in payload.get("tiles", []):
        tile["durability"] = by_key.get(tile.get("t"))
    payload["durability"] = {
        key: value for key, value in durability.items() if key != "subthemes"
    }
    return True


def build(site: Path | None = None, *, generated_utc: str | None = None) -> dict:
    """Assemble + write the themes heatmap JSON. Returns the payload."""
    site = site or (config.ROOT / config.load()["storage"]["site_dir"])

    tree_path = _data("themes_heatmap", "themes_tree.json")
    perf_path = _data("themes_heatmap", "perf_snapshot.json")
    tree = json.loads(tree_path.read_text())
    snap = json.loads(perf_path.read_text())

    # as-of = the snapshot's embedded capture date. Never trust file mtime here:
    # on CI runners a checkout rewrites files with mtime = checkout time, so a
    # frozen snapshot would display today's date (#2690 class). mtime remains
    # only as an offline-safe fallback for legacy snapshots without the field.
    asof = snap.get("asof") or datetime.fromtimestamp(
        perf_path.stat().st_mtime, timezone.utc).strftime("%Y-%m-%d")
    generated_utc = generated_utc or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    payload = th.build_themes_heatmap(
        tree,
        snap.get("subsector_perf") or {},
        snap.get("member_perf") or {},
        generated_utc=generated_utc,
        asof=asof,
        source=snap.get("source") or "finviz-themes",
    )
    try:
        _attach_revision_durability(payload, tree)
    except Exception as exc:  # noqa: BLE001 — optional named leg, never kills price map
        log.warning("theme repricing revision durability unavailable: %s", exc)

    outdir = site / "marketdata"
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / "themes_heatmap.json"
    out.write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False))
    log.info("wrote %s — %d themes, %d subsector tiles, %d members, asof %s",
             out, len(payload["sectors"]), payload["n_tiles"],
             payload.get("n_members", 0), asof)
    return payload


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    argparse.ArgumentParser(description="Build the Finviz themes heatmap feed").parse_args(argv)
    build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
