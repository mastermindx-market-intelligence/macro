#!/usr/bin/env python3
"""Reflow the supplied rounded Paper geometry; this is not a market-data source."""
from pathlib import Path
import json
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent
fixture = json.loads((ROOT / "RETURNS_CHART_FIXTURE.json").read_text())
proof = {"status": fixture["status"], "outputs": [], "series_points": {s["name"]: len(s["points"]) for s in fixture["series"]}}
for spec in fixture["outputs"]:
    width, height = spec["width"], spec["height"]
    left, right, top, zero = 38, width - 10, 12, 106
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" style="width:100%;height:{height}px;" role="img" aria-labelledby="returns-title returns-desc">',
             '<title id="returns-title">Illustrative NVDA and SPY paths</title>',
             '<desc id="returns-desc">Same supplied 127-point illustration, reflowed for the chart width. The baseline and 126 return intervals are retained. This is not live or verified historical market data.</desc>']
    for value, y in [(0, zero), (20, (top + zero) / 2), (40, top)]:
        label = "0%" if value == 0 else f"+{value}%"
        parts += [f'<line x1="{left}" y1="{y}" x2="{right}" y2="{y}" stroke="#2D333E"/>',
                  f'<text x="0" y="{y+4}" fill="#8B93A1" font-family="Inter, sans-serif" font-size="11">{label}</text>']
    max_error = 0.0
    for series in fixture["series"]:
        points = series["points"]
        assert len(points) == 127 and all(a[0] < b[0] for a, b in zip(points, points[1:]))
        mapped = [(left + (x-30)/282*(right-left), top + (y-8)/110*(zero-top)) for x,y in points]
        assert abs(mapped[0][0]-left)<1e-9 and abs(mapped[-1][0]-right)<1e-9
        assert all(left-1e-9 <= x <= right+1e-9 and top-1e-9 <= y <= zero+1e-9 for x,y in mapped)
        d = " ".join(("M" if i == 0 else "L")+f"{x:.4f},{y:.4f}" for i,(x,y) in enumerate(mapped))
        dash = ' stroke-dasharray="4 3"' if series["dashed"] else ""
        stroke_width = 1.6 if series["dashed"] else 2
        parts.append(f'<path d="{d}" fill="none" stroke="{series["stroke"]}" stroke-width="{stroke_width}"{dash}/>')
        endx, endy = mapped[-1]
        parts.append(f'<circle cx="{endx:.4f}" cy="{endy:.4f}" r="2.3" fill="{series["stroke"]}"/>')
        # Inverse geometry check proves the reflow kept the original illustration's scale.
        for (_x, source_y), (_mx, mapped_y) in zip(points, mapped):
            source_pct = (118-source_y)/110*40
            mapped_pct = (zero-mapped_y)/(zero-top)*40
            max_error = max(max_error, abs(source_pct-mapped_pct))
    parts += [f'<text x="{left}" y="132" fill="#8B93A1" font-family="Inter, sans-serif" font-size="11">126 sessions ago</text>',
              f'<text x="{right}" y="132" text-anchor="end" fill="#8B93A1" font-family="Inter, sans-serif" font-size="11">Oct 16</text>', '</svg>']
    svg = "\n".join(parts)+"\n"
    ET.fromstring(svg)
    assert max_error < 1e-10
    target = ROOT / "evidence" / spec["name"]
    target.write_text(svg)
    proof["outputs"].append({"file": "evidence/"+spec["name"], "width": width, "height": height,
                             "axis_font_px": 11, "date_end_anchored": True, "max_scale_error_pp": max_error})
(ROOT / "RETURNS_CHART_REFLOW_VERIFICATION.json").write_text(json.dumps(proof, indent=2)+"\n")
print(json.dumps(proof, indent=2))
