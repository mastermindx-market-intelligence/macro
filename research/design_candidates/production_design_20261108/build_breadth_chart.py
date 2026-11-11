"""Generate deterministic Paper chart specimens from one ILLUSTRATIVE fixture.

These values are authored design data, not retained market observations.
The selected Sep 24 values (108.7/106.2) preserve the existing Paper numeric
fixture. Other points are explicit synthetic context, introduced to replace
hand-positioned line segments whose marker contradicted the numeric readout.
No network, data collector, production renderer, or calculation owner changes.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from xml.etree import ElementTree as ET

OUT = Path(__file__).resolve().parent
ROWS = [
    ("2026-07-02", 100.0, 100.0),
    ("2026-07-16", 100.6, 101.0),
    ("2026-07-30", 99.8, 100.3),
    ("2026-08-13", 102.7, 102.1),
    ("2026-08-27", 101.9, 102.7),
    ("2026-09-10", 106.1, 103.8),
    ("2026-09-24", 108.7, 106.2),
    ("2026-09-29", 109.6, 107.5),
]


def svg(width: int, height: int, *, selected: bool = False, labels: bool = True) -> str:
    left, right, top, bottom = (38 if labels else 10), 16, 18, (32 if labels else 12)
    pw, ph = width - left - right, height - top - bottom
    first, last = date.fromisoformat(ROWS[0][0]), date.fromisoformat(ROWS[-1][0])

    def x(day: str) -> float:
        return left + (date.fromisoformat(day) - first).days / (last - first).days * pw

    def y(value: float) -> float:
        return top + (110 - value) / 15 * ph

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Illustrative breadth and price indices; synthetic design data">']
    parts.append(f'<rect width="{width}" height="{height}" fill="#0D0E10"/>')
    for value in (95, 100, 105, 110):
        yy = y(value)
        parts.append(f'<path d="M{left} {yy:.3f}H{width-right}" fill="none" stroke="#292929" stroke-width="1"/>')
        if labels:
            parts.append(f'<text x="{left-8}" y="{yy+3:.3f}" text-anchor="end" font-family="Inter, sans-serif" font-size="10" fill="#949494">{value}</text>')
    for col, color in ((2, "#A7B4C2"), (1, "#A8C2AD")):
        points = " ".join(f'{x(row[0]):.3f},{y(row[col]):.3f}' for row in ROWS)
        parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>')
    if labels:
        for day, label in (("2026-07-02", "Jul 02"), ("2026-07-30", "Jul 30"), ("2026-08-27", "Aug 27"), ("2026-09-29", "Sep 29")):
            anchor = "start" if day == ROWS[0][0] else "end" if day == ROWS[-1][0] else "middle"
            parts.append(f'<text x="{x(day):.3f}" y="{height-8}" text-anchor="{anchor}" font-family="Inter, sans-serif" font-size="10" fill="#949494">{label}</text>')
    if selected:
        row = ROWS[-2]
        xx = x(row[0])
        parts.append(f'<path d="M{xx:.3f} {top}V{height-bottom}" stroke="#949494" stroke-width="1" stroke-dasharray="3 4"/>')
        for col, color in ((1, "#A8C2AD"), (2, "#A7B4C2")):
            yy = y(row[col])
            parts.append(f'<circle cx="{xx:.3f}" cy="{yy:.3f}" r="4" fill="{color}" stroke="#0D0E10" stroke-width="2"/>')
            parts.append(f'<text x="{xx-12:.3f}" y="{yy+4:.3f}" text-anchor="end" font-family="Inter, sans-serif" font-size="12" font-weight="600" fill="{color}">{row[col]:.1f}</text>')
        parts.append(f'<rect x="{xx-34:.3f}" y="{height-bottom-22}" width="68" height="20" rx="4" fill="#292929"/>')
        parts.append(f'<text x="{xx:.3f}" y="{height-bottom-8}" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="#F3F3F3">SEP 24</text>')
        assert abs((y(row[2]) - y(row[1])) / ph * 15 - 2.5) < 1e-10
    parts.append("</svg>")
    result = "".join(parts)
    ET.fromstring(result)
    return result


def main() -> None:
    evidence = OUT / "evidence"
    evidence.mkdir(exist_ok=True)
    variants = {
        "breadth-chart-desktop.svg": svg(688, 260),
        "breadth-chart-mobile.svg": svg(326, 150, labels=False),
        "breadth-chart-inspector.svg": svg(704, 340, selected=True),
    }
    for name, content in variants.items():
        (evidence / name).write_text(content + "\n")
    fixture = {
        "status": "ILLUSTRATIVE_DESIGN_DATA_NOT_MARKET_OBSERVATIONS",
        "source": "Authored design fixture; selected values retained from Paper XZ-0",
        "selected_session": "2026-09-24",
        "baseline": 100,
        "series": [{"session": d, "ad_index": a, "price_index": p} for d, a, p in ROWS],
        "selected_counts": {"advancers": 1327, "decliners": 741, "unchanged": 104, "new_highs": 121, "new_lows": 52},
        "overview_counts": {"new_highs": 128, "new_lows": 67},
        "arithmetic_checks": {
            "selected_classified_moves": 1327 + 741 + 104,
            "selected_ad_ratio": round(1327 / 741, 2),
            "selected_raw_record_high_share": round(100 * 121 / (121 + 52), 1),
            "overview_raw_record_high_share": round(100 * 128 / (128 + 67), 1),
            "selected_index_spread": round(108.7 - 106.2, 1),
            "zero_extremes_result": None,
        },
        "verification": "Three SVGs XML-parse; selected marker geometry matches 2.5 index points; one fixture drives all chart paths. No browser or live-product proof.",
    }
    (OUT / "BREADTH_CHART_FIXTURE.json").write_text(json.dumps(fixture, indent=2) + "\n")
    print(json.dumps({"generated": list(variants), "checks": fixture["arithmetic_checks"]}))


if __name__ == "__main__":
    main()
