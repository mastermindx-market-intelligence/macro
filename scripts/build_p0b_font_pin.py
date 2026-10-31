#!/usr/bin/env python3
"""Build the pinned font set the Prophet P0B browser verifier serves.

scripts/verify_stock_dashboard_mobile_layout.cjs measures layout numbers and
screenshot digests. Both move whenever a host's system fonts differ, so the
verifier injects ``p0b-font-pin/pin.css`` as the first stylesheet of the page
under test. That stylesheet shadows every named font family the page asks for
with committed webfont subsets, so no glyph the page renders can come from a
platform font. The verifier's CDP audit refuses a receipt if one still does.

This tool regenerates the committed subsets and the stylesheet. It needs
fontTools with brotli (``pip install fonttools brotli``); the repository's
tests and the verifier never import it. Run it when the served text gains a
codepoint the pinned subsets lack (the verifier names the leak), then re-mint
both receipts:

    python3.11 scripts/build_p0b_font_pin.py \\
        --cjk-font NotoSansSC-Variable.ttf \\
        --symbol-font DejaVuSans.ttf --symbol-bold-font DejaVuSans-Bold.ttf \\
        --emoji-font Twemoji.ttf --text-dir DIR

DIR holds the rendered fixture pages from render_stock_dashboard_fixture.py.
The receipts' loaded assets are scanned automatically.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "mockups/evidence/prophet-p0b-zero-fouc"
RECEIPTS = ("mobile-layout.json", "mobile-layout-canada.json")
OUT_DIR = EVIDENCE / "inputs/browser-data/p0b-font-pin"
ROUTE = "/p0b-font-pin"
WEIGHTS = (400, 500, 600, 700, 800, 900)

# Named families the P0B pages request (computed font-family of every element
# and pseudo-element, both markets). A generic keyword cannot be shadowed, but
# it is never reached while an earlier named family covers every glyph.
UI_FAMILIES = (
    "-apple-system", "system-ui", "SF Pro Text", "SF Pro Display",
    "Segoe UI", "Roboto", "Helvetica Neue", "Arial", "Helvetica", "Times",
)
CJK_FAMILIES = ("PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC")
# theme.css owns the Inter faces; the pin adds fallback pieces only.
INTER = "Inter"

BASE_TEXT = [range(0x20, 0x7F), range(0xA0, 0x100), range(0x2010, 0x2028),
             range(0x2030, 0x205F), range(0x3000, 0x3040), range(0xFF01, 0xFF5F)]
EMOJI_JOINERS = {0x200D, 0xFE0E, 0xFE0F, 0x20E3}
CSS_ESCAPE = re.compile(r"\\([0-9a-fA-F]{1,6})\s?")
JS_ESCAPE = re.compile(r"\\u(?:\{([0-9a-fA-F]{1,6})\}|([0-9a-fA-F]{4}))")
TEXT_SUFFIXES = {".html", ".js", ".json", ".css"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decoded_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    parts = [raw, html.unescape(raw)]
    parts.extend(chr(int(m.group(1), 16)) for m in CSS_ESCAPE.finditer(raw)
                 if int(m.group(1), 16) < 0x110000)
    for m in JS_ESCAPE.finditer(raw):
        cp = int(m.group(1) or m.group(2), 16)
        if cp < 0x110000:
            parts.append(chr(cp))
    return "".join(parts)


def text_sources(text_dir: Path | None) -> list[Path]:
    paths: set[Path] = set()
    for name in RECEIPTS:
        payload = json.loads((EVIDENCE / name).read_text(encoding="utf-8"))
        for rel in payload.get("loaded_assets", {}):
            if rel.startswith(OUT_DIR.relative_to(ROOT).as_posix()):
                continue
            path = ROOT / rel
            if path.suffix in TEXT_SUFFIXES and path.is_file():
                paths.add(path)
    if text_dir:
        paths.update(p for p in text_dir.iterdir() if p.suffix == ".html")
    return sorted(paths)


def wanted_codepoints(sources: list[Path]) -> tuple[set[int], set[int]]:
    """Return (codepoints, codepoints seen before U+FE0F)."""
    cps: set[int] = set()
    for block in BASE_TEXT:
        cps.update(block)
    emoji_form: set[int] = set()
    for path in sources:
        text = decoded_text(path)
        for index, char in enumerate(text):
            cp = ord(char)
            if cp < 0x20 or unicodedata.category(char) in {"Cc", "Cs", "Co", "Cn"}:
                continue
            cps.add(cp)
            if index + 1 < len(text) and text[index + 1] == "\ufe0f":
                emoji_form.add(cp)
    return cps, emoji_form


def cmap(path: Path) -> set[int]:
    from fontTools.ttLib import TTFont

    font = TTFont(path, lazy=True)
    return set(font.getBestCmap())


def subset(source: Path, out: Path, unicodes: set[int], weight: int | None = None) -> None:
    from fontTools import subset as ft_subset
    from fontTools.varLib import instancer

    options = ft_subset.Options()
    options.flavor = "woff2"
    options.layout_features = ["*"]
    options.name_IDs = ["*"]
    options.name_languages = ["*"]
    options.notdef_outline = True
    options.recalc_timestamp = False
    font = ft_subset.load_font(str(source), options)
    if "fvar" in font:
        # A static instance: the rendered weight must not depend on how a
        # browser build applies variation axes to a single-weight face.
        font = instancer.instantiateVariableFont(font, {"wght": weight or 400},
                                                 updateFontNames=True)
    subsetter = ft_subset.Subsetter(options)
    subsetter.populate(unicodes=sorted(unicodes))
    subsetter.subset(font)
    ft_subset.save_font(font, str(out), options)


def unicode_range(cps: set[int]) -> str:
    ranges: list[str] = []
    ordered = sorted(cps)
    start = prev = ordered[0]
    for cp in ordered[1:] + [None]:
        if cp is not None and cp == prev + 1:
            prev = cp
            continue
        ranges.append(f"U+{start:X}" if start == prev else f"U+{start:X}-{prev:X}")
        if cp is not None:
            start = prev = cp
    return ",".join(ranges)


def face(family: str, url: str, weight: int, cps: set[int] | None = None) -> str:
    rng = f";unicode-range:{unicode_range(cps)}" if cps else ""
    return (f'@font-face{{font-family:"{family}";src:url("{url}") format("woff2");'
            f"font-weight:{weight};font-style:normal;font-display:block{rng}}}")


def build(args: argparse.Namespace) -> dict:
    sources = text_sources(args.text_dir)
    wanted, emoji_form = wanted_codepoints(sources)
    cover = {
        "cjk": cmap(args.cjk_font),
        "symbol": cmap(args.symbol_font) & cmap(args.symbol_bold_font),
        "emoji": cmap(args.emoji_font),
    }
    # One owner per codepoint, so the pieces' unicode ranges never overlap.
    piece: dict[str, set[int]] = {"emoji": set(), "cjk": set(), "symbol": set()}
    uncovered: set[int] = set()
    for cp in sorted(wanted):
        if cp in EMOJI_JOINERS or 0x1F1E6 <= cp <= 0x1F1FF:
            owner = "emoji" if cp in cover["emoji"] else None
        elif (cp in emoji_form or cp >= 0x1F000) and cp in cover["emoji"]:
            owner = "emoji"
        elif cp in cover["cjk"]:
            owner = "cjk"
        elif cp in cover["symbol"]:
            owner = "symbol"
        elif cp in cover["emoji"]:
            owner = "emoji"
        else:
            owner = None
        if owner:
            piece[owner].add(cp)
        else:
            uncovered.add(cp)

    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    files = {
        "cjk-400.woff2": (args.cjk_font, piece["cjk"], 400),
        "cjk-700.woff2": (args.cjk_font, piece["cjk"], 700),
        "symbol-400.woff2": (args.symbol_font, piece["symbol"], None),
        "symbol-700.woff2": (args.symbol_bold_font, piece["symbol"], None),
        "emoji.woff2": (args.emoji_font, piece["emoji"], None),
    }
    for name, (source, cps, weight) in files.items():
        subset(source, out / name, cps, weight)

    def pieces(family: str, weight: int) -> list[str]:
        bucket = 700 if weight >= 600 else 400
        return [
            face(family, f"{ROUTE}/cjk-{bucket}.woff2", weight),
            face(family, f"{ROUTE}/symbol-{bucket}.woff2", weight, piece["symbol"]),
            face(family, f"{ROUTE}/emoji.woff2", weight, piece["emoji"]),
        ]

    rules: list[str] = []
    # Faces sharing a family and weight form one segmented face, consulted
    # most recently declared first: the Inter base, then the emoji and symbol
    # pieces (disjoint ranges), then the unranged CJK face. This sheet loads
    # before theme.css, whose own Inter faces therefore outrank its pieces.
    for family in (INTER,) + UI_FAMILIES:
        for weight in WEIGHTS:
            rules.extend(pieces(family, weight))
            if family != INTER:
                rules.append(face(family, f"/fonts/Inter-{weight}.woff2", weight))
    for family in CJK_FAMILIES:
        for weight in WEIGHTS:
            rules.extend(pieces(family, weight))
    header = ("/* Generated by scripts/build_p0b_font_pin.py; do not edit. Shadows every "
              "named family the P0B pages request with pinned faces. */")
    (out / "pin.css").write_text(header + "\n" + "\n".join(rules) + "\n", encoding="utf-8")

    manifest = {
        "schema": "mastermind.p0b_font_pin.v1",
        "generator": "scripts/build_p0b_font_pin.py",
        "stylesheet": f"{ROUTE}/pin.css",
        "shadowed_families": [INTER, *UI_FAMILIES, *CJK_FAMILIES],
        "weights": list(WEIGHTS),
        "files": {name: sha256(out / name) for name in sorted([*files, "pin.css"])},
        "site_faces": {f"fonts/Inter-{w}.woff2": sha256(ROOT / "site/fonts" / f"Inter-{w}.woff2")
                       for w in WEIGHTS},
        "sources": {
            **{f"cjk-{w}.woff2": {"family": f"Noto Sans SC (variable, wght={w} instance)",
                                  "license": "SIL OFL 1.1", "sha256": sha256(args.cjk_font),
                                  "codepoints": len(piece["cjk"])} for w in (400, 700)},
            "symbol-400.woff2": {"family": "DejaVu Sans", "license": "Bitstream Vera / DejaVu",
                                 "sha256": sha256(args.symbol_font), "codepoints": len(piece["symbol"])},
            "symbol-700.woff2": {"family": "DejaVu Sans Bold", "license": "Bitstream Vera / DejaVu",
                                 "sha256": sha256(args.symbol_bold_font), "codepoints": len(piece["symbol"])},
            "emoji.woff2": {"family": "Twemoji Mozilla", "license": "CC-BY 4.0 (graphics), Twitter Inc. and contributors",
                            "sha256": sha256(args.emoji_font), "codepoints": len(piece["emoji"])},
        },
        "uncovered_codepoints": [f"U+{cp:04X}" for cp in sorted(uncovered)],
    }
    (out / "font-pin.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--cjk-font", type=Path, required=True)
    parser.add_argument("--symbol-font", type=Path, required=True)
    parser.add_argument("--symbol-bold-font", type=Path, required=True)
    parser.add_argument("--emoji-font", type=Path, required=True)
    parser.add_argument("--text-dir", type=Path, help="rendered fixture pages to scan")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    manifest = build(parser.parse_args(argv))
    print(json.dumps({k: manifest[k] for k in ("files", "uncovered_codepoints")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
