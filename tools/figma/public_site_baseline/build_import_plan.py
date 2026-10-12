#!/usr/bin/env python3
"""Build deterministic Figma import targets from a verified reference matrix."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

from tools.figma.public_site_baseline.reference_matrix import (
    MOTION_PHASES as PHASES,
    STATIC_VARIANTS,
    SURFACES,
)
PAGE_LABELS = {
    "homepage": "Homepage",
    "market-terminal": "Market Terminal",
    "mastermind-ai": "Mastermind AI",
    "market-dashboards": "Market Dashboards",
}
FORBIDDEN_FIGMA_APIS = (
    "loadAllPagesAsync",
    "setPluginData",
    "createImageAsync",
    "figma.currentPage =",
)


def _record_key(record: dict[str, Any], kind: str) -> tuple[str, str]:
    axis = "variant" if kind == "static" else "phase"
    try:
        return str(record["page"]), str(record[axis])
    except KeyError as exc:
        raise ValueError(f"{kind} record missing {exc.args[0]}") from exc


def _expected_keys(kind: str) -> tuple[tuple[str, str], ...]:
    axis_values: Iterable[str] = STATIC_VARIANTS if kind == "static" else PHASES
    return tuple((surface, value) for surface in SURFACES for value in axis_values)


def _validated_lookup(matrix: dict[str, Any], kind: str) -> dict[tuple[str, str], dict[str, Any]]:
    records = matrix.get(kind)
    if not isinstance(records, list):
        raise ValueError(f"reference matrix missing {kind} records")

    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError(f"{kind} record must be an object")
        key = _record_key(record, kind)
        if key in lookup:
            raise ValueError(f"duplicate {kind} record: {key[0]}/{key[1]}")
        if record.get("verified") is not True:
            raise ValueError(f"{kind} evidence not verified: {key[0]}/{key[1]}")
        if record.get("console_errors"):
            raise ValueError(f"{kind} evidence has console errors: {key[0]}/{key[1]}")
        for field in ("file", "sha256", "image_width", "image_height"):
            if not record.get(field):
                raise ValueError(f"{kind} record missing {field}: {key[0]}/{key[1]}")
        lookup[key] = record

    expected = set(_expected_keys(kind))
    actual = set(lookup)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        parts = []
        if missing:
            parts.append(
                f"missing {kind}=" + ",".join(f"{page}/{state}" for page, state in missing)
            )
        if extra:
            parts.append(
                f"extra {kind}=" + ",".join(f"{page}/{state}" for page, state in extra)
            )
        raise ValueError("reference matrix mismatch: " + "; ".join(parts))
    return lookup


def _asset_path(record: dict[str, Any], kind: str, asset_root: Path | None) -> str:
    source = Path(str(record["file"]))
    if asset_root is None:
        return str(source)
    return str(asset_root / kind / source.name)


def build_upload_order(
    matrix: dict[str, Any],
    *,
    asset_root: Path | None = None,
) -> dict[str, Any]:
    """Return a canonical 20-static + 16-motion Figma upload order."""
    operation = matrix.get("operation")
    source = matrix.get("source")
    if not operation or not isinstance(source, dict):
        raise ValueError("reference matrix must include operation and source")

    static_lookup = _validated_lookup(matrix, "static")
    motion_lookup = _validated_lookup(matrix, "motion")
    items: list[dict[str, Any]] = []
    for surface in SURFACES:
        for variant in STATIC_VARIANTS:
            record = static_lookup[(surface, variant)]
            items.append({
                "index": len(items),
                "kind": "static",
                "page": surface,
                "variant": variant,
                "page_name": "90 — Reference Captures",
                "target_name": f"MMX/RefTarget/{surface}/{variant}",
                "file": _asset_path(record, "static", asset_root),
                "width": int(record["image_width"]),
                "height": int(record["image_height"]),
                "scale_mode": "FIT",
                "sha256": str(record["sha256"]),
            })

    for surface in SURFACES:
        for phase in PHASES:
            record = motion_lookup[(surface, phase)]
            items.append({
                "index": len(items),
                "kind": "motion",
                "page": surface,
                "phase": phase,
                "page_name": "20 — Motion & Interaction",
                "target_name": f"MMX/MotionTarget/{surface}/{phase}",
                "file": _asset_path(record, "motion", asset_root),
                "width": int(record["image_width"]),
                "height": int(record["image_height"]),
                "scale_mode": "FIT",
                "sha256": str(record["sha256"]),
            })

    return {
        "schema": "mastermindx.figma_upload_order.v1",
        "operation": operation,
        "source": source,
        "items": items,
    }


def render_prepare_script(order: dict[str, Any]) -> str:
    """Render an idempotent Figma Plugin API script for exact-size targets."""
    targets = json.dumps(order["items"], ensure_ascii=False, separators=(",", ":"))
    labels = json.dumps(PAGE_LABELS, ensure_ascii=False, separators=(",", ":"))
    header = f'''(async () => {{
  const TARGETS = {targets};
  const LABELS = {labels};
  const fontRegular = {{ family: "Inter", style: "Regular" }};
  const fontSemi = {{ family: "Inter", style: "Semi Bold" }};
  await Promise.all([figma.loadFontAsync(fontRegular), figma.loadFontAsync(fontSemi)]);

  function pageByName(name) {{
    const page = figma.root.children.find(node => node.type === "PAGE" && node.name === name);
    if (!page) throw new Error(`Missing page ${{name}}; run bootstrap first.`);
    return page;
  }}
  function clearOwned(page, name) {{
    for (const node of [...page.children]) if (node.name === name) node.remove();
  }}
  function textNode(parent, characters, x, y, size, fontName) {{
    const node = figma.createText();
    node.fontName = fontName; node.fontSize = size; node.characters = characters;
    node.fills = [{{ type: "SOLID", color: {{ r: 0.11, g: 0.15, b: 0.21 }} }}];
    node.x = x; node.y = y; parent.appendChild(node); return node;
  }}
'''
    body = r'''
  function targetRect(parent, item, x, y) {
    const node = figma.createRectangle();
    node.name = item.target_name; node.resize(item.width, item.height);
    node.x = x; node.y = y; node.cornerRadius = 4;
    node.fills = [{ type: "SOLID", color: { r: 0.965, g: 0.972, b: 0.982 } }];
    node.strokes = [{ type: "SOLID", color: { r: 0.82, g: 0.85, b: 0.89 } }];
    node.strokeWeight = 1; parent.appendChild(node); return node;
  }
  async function buildBoard(pageName, rootName, kind, startY) {
    const page = pageByName(pageName);
    await figma.setCurrentPageAsync(page);
    clearOwned(page, rootName);
    const root = figma.createFrame();
    root.name = rootName; root.x = 0; root.y = startY;
    root.fills = []; root.clipsContent = false; page.appendChild(root);
    const created = [];
    let y = 0, maxWidth = 0;
    for (const pageKey of Object.keys(LABELS)) {
      textNode(root, LABELS[pageKey], 0, y, kind === "static" ? 32 : 28, fontSemi);
      let x = 0, maxHeight = 0;
      const items = TARGETS.filter(item => item.kind === kind && item.page === pageKey);
      for (const item of items) {
        const state = item.variant || item.phase;
        textNode(root, state.toUpperCase(), x, y + 54, 12, fontSemi);
        const node = targetRect(root, item, x, y + 82);
        created.push({ index: item.index, name: node.name, id: node.id, file: item.file });
        x += item.width + 80; maxHeight = Math.max(maxHeight, item.height);
      }
      maxWidth = Math.max(maxWidth, x);
      y += maxHeight + (kind === "static" ? 300 : 240);
    }
    root.resize(Math.max(100, maxWidth), Math.max(100, y));
    return created;
  }

  const created = [
    ...await buildBoard("90 — Reference Captures", "MMX/Reference Import Targets", "static", 1900),
    ...await buildBoard("20 — Motion & Interaction", "MMX/Motion Reference Targets", "motion", 2100),
  ].sort((a, b) => a.index - b.index);
  console.log("MMX_FIGMA_UPLOAD_TARGETS " + JSON.stringify(created));
  figma.notify(`Prepared ${created.length} exact-size reference targets.`, { timeout: 8000 });
})();
'''
    script = header + body
    if any(term in script for term in FORBIDDEN_FIGMA_APIS):
        raise ValueError("generated prepare script uses a forbidden Figma API")
    return script


def render_finalize_script(*, expected_count: int) -> str:
    """Render a Figma script that refuses to lock incomplete upload targets."""
    if expected_count <= 0:
        raise ValueError("expected_count must be positive")
    script = f'''(async () => {{
  const pageNames = ["90 — Reference Captures", "20 — Motion & Interaction"];
  const roots = [];
  const targets = [];
  for (const pageName of pageNames) {{
    const page = figma.root.children.find(node => node.type === "PAGE" && node.name === pageName);
    if (!page) throw new Error(`Missing page ${{pageName}}`);
    await figma.setCurrentPageAsync(page);
    for (const node of page.findAll(node =>
      node.name.startsWith("MMX/RefTarget/") || node.name.startsWith("MMX/MotionTarget/"))) {{
      targets.push(node);
    }}
    for (const node of page.children) {{
      if (node.name === "MMX/Reference Import Targets" ||
          node.name === "MMX/Motion Reference Targets") roots.push(node);
    }}
  }}

  if (targets.length !== {expected_count}) {{
    throw new Error(`Expected {expected_count} upload targets, found ${{targets.length}}`);
  }}
  const missing = [];
'''
    script += r'''
  for (const node of targets) {
    const fills = Array.isArray(node.fills) ? node.fills : [];
    if (!fills.some(fill => fill.type === "IMAGE")) missing.push(node.name);
  }
  if (missing.length) throw new Error(`Reference assets missing: ${missing.join(", ")}`);
  for (const node of targets) {
    node.strokes = [];
    node.locked = true;
  }
  for (const root of roots) root.locked = true;
  console.log("MMX_FIGMA_REFERENCE_LOCK " + JSON.stringify(
    targets.map(node => ({ id: node.id, name: node.name }))
  ));
  figma.notify(`All ${targets.length} reference captures are present and locked.`, { timeout: 8000 });
})();
'''
    if any(term in script for term in FORBIDDEN_FIGMA_APIS):
        raise ValueError("generated finalize script uses a forbidden Figma API")
    return script


def write_import_plan(
    matrix_path: Path,
    output_dir: Path,
    *,
    asset_root: Path | None = None,
) -> dict[str, Any]:
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    order = build_upload_order(matrix, asset_root=asset_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    order_path = output_dir / "figma_upload_order.json"
    prepare_path = output_dir / "figma_prepare_import_targets.js"
    finalize_path = output_dir / "figma_finalize_import_targets.js"
    order_path.write_text(
        json.dumps(order, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    prepare_path.write_text(render_prepare_script(order), encoding="utf-8")
    finalize_path.write_text(
        render_finalize_script(expected_count=len(order["items"])),
        encoding="utf-8",
    )
    return {
        "schema": "mastermindx.figma_import_plan_receipt.v1",
        "operation": order["operation"],
        "target_count": len(order["items"]),
        "static_count": sum(item["kind"] == "static" for item in order["items"]),
        "motion_count": sum(item["kind"] == "motion" for item in order["items"]),
        "order_path": str(order_path),
        "prepare_path": str(prepare_path),
        "finalize_path": str(finalize_path),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--asset-root", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    receipt = write_import_plan(
        args.matrix,
        args.output_dir,
        asset_root=args.asset_root,
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
