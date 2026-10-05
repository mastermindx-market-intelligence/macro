"""Bounded presentation adapter: deterministic SVG, never synthesizes chart data."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from html import escape
import math

DEFAULT_CHART = {"policy": "financing_growth", "property": "home_net", "flows": "southbound_20", "sentiment": "margin_ratio"}


def chart_svg(metric: dict, maximum: int = 252) -> str:
    """SVG first paint; missing observations break paths, including interior gaps.

    X is elapsed calendar time, not array position. A history with only one known
    point is explicitly unplottable, not extrapolated into a line.
    """
    data = metric.get("chart") or {}
    dates, values = data.get("dates", []), data.get("vals", [])
    if len(dates) != len(values) or maximum < 1:
        return ""
    pairs = list(zip(dates, values))[-maximum:]
    valid = [(d, v) for d, v in pairs if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)]
    if len(valid) < 2:
        return ""
    width, height, left, right, top, bottom = 640, 204, 12, 72, 20, 30
    try:
        times = [datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() for d, _ in pairs]
    except (ValueError, TypeError):
        return ""
    if any(a >= b for a, b in zip(times, times[1:])):
        return ""
    lo, hi = min(v for _, v in valid), max(v for _, v in valid)
    ref = metric.get("reference")
    if not isinstance(ref, (int, float)) or isinstance(ref, bool) or not math.isfinite(ref):
        ref = 0 if metric.get("chart_kind") == "bars" else None
    if ref is not None:
        lo, hi = min(lo, ref), max(hi, ref)
    pad = (hi-lo)*.12 or max(abs(hi)*.05, 1)
    lo, hi = lo-pad, hi+pad
    dx = times[-1]-times[0] or 1
    xx = lambda t: left+(t-times[0])/dx*(width-left-right)
    yy = lambda v: top+(hi-v)/(hi-lo)*(height-top-bottom)
    out = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{escape(metric["label_en"])}; {escape(metric["unit"])}" class="cnm-svg">']
    for j in range(3):
        y = top + j*(height-top-bottom)/2
        value = hi-j*(hi-lo)/2
        out.append(f'<line class="cnm-gridline" x1="{left}" y1="{y:.2f}" x2="{width-right}" y2="{y:.2f}"/>')
        out.append(f'<text class="cnm-axis" x="{width-right+8}" y="{y+4:.2f}">{value:,.2f}</text>')
    if ref is not None and isinstance(ref, (int, float)) and math.isfinite(ref):
        out.append(f'<line class="cnm-zero" x1="{left}" y1="{yy(ref):.2f}" x2="{width-right}" y2="{yy(ref):.2f}"/>')
    segment = []
    for (date, value), timestamp in zip(pairs, times):
        good = isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
        if not good:
            if segment:
                out.append('<path class="cnm-line" d="'+ ' '.join(segment)+'"/>')
                segment = []
            continue
        x, y = xx(timestamp), yy(value)
        if metric.get("chart_kind") == "bars":
            zero = yy(ref if isinstance(ref, (int, float)) else 0)
            # Cap bar thickness; irregular dates are never assigned a fake cadence.
            out.append(f'<line class="cnm-bar {"negative" if value < 0 else "positive"}" x1="{x:.2f}" x2="{x:.2f}" y1="{zero:.2f}" y2="{y:.2f}"/>')
        else:
            segment.append(f'{"M" if not segment else "L"}{x:.2f},{y:.2f}')
    if segment:
        out.append('<path class="cnm-line" d="'+' '.join(segment)+'"/>')
    out.append(f'<text class="cnm-axis" x="{left}" y="{height-5}">{escape(pairs[0][0])}</text>')
    out.append(f'<text class="cnm-axis" text-anchor="end" x="{width-right}" y="{height-5}">{escape(pairs[-1][0])}</text>')
    out.append('</svg>')
    return ''.join(out)


def prepare_view(snapshot: dict) -> dict:
    """Deep-copy the API contract so no SVG/HTML ever leaks into machine outputs."""
    view = deepcopy(snapshot)
    for panel in view.get("panels", {}).values():
        metrics = panel["metrics"]
        panel["primary"] = [m for m in metrics if m.get("primary")][:3]
        panel["chart_metrics"] = [m for m in metrics if len(m.get("chart", {}).get("dates", [])) >= 2 and m["status"] != "quality_hold" and sum(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in m.get("chart", {}).get("vals", [])) >= 2]
        default = next((m for m in panel["chart_metrics"] if m["id"] == DEFAULT_CHART[panel["id"]]), None)
        panel["selected_chart"] = default or next(iter(panel["chart_metrics"]), None)
        if panel["selected_chart"]:
            panel["chart_svg"] = chart_svg(panel["selected_chart"])
        else:
            panel["chart_svg"] = ""
        # Scoped numeric-only configuration. Labels remain Jinja-escaped or textContent.
        panel["chart_config"] = [{k: m[k] for k in ["id", "label_en", "label_zh", "unit", "chart", "chart_kind", "reference", "status"]} for m in panel["chart_metrics"]]
    return view
