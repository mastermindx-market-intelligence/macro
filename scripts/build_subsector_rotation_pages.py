"""Per-subsector DETAIL pages for the Subsector Rotation desk.

Renders one ``site/rotation/<key>.html`` per subsector from
``templates/subsector_rotation_detail.html.j2``, driven entirely by the committed
``site/marketdata/subsector_rotation.json`` (no per-stock data dependency — these are
broad-universe tickers). Each page tracks that subsector's rotation state, the VELOCITY
of its standardized relative-strength trend plus raw return-rate acceleration, its multi-horizon performance, and its
member stocks (linked to the single-stock analyzer). Regenerated on every build so the
pages stay live with the nightly rotation refresh.

    python -m scripts.build_subsector_rotation_pages
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from lib import config  # noqa: E402
from lib.pages import write_page  # noqa: E402

log = logging.getLogger("build_subsector_rotation_pages")

# mirror the map's QUAD / QUADX (keep the detail page and the map in lock-step).
QUAD = {
    "leading":   ("Leading",   "领先", "q-lead"),
    "weakening": ("Weakening", "走弱", "q-weak"),
    "improving": ("Improving", "改善", "q-impr"),
    "lagging":   ("Lagging",   "落后", "q-lag"),
}
QUADX = {
    "leading":   ("strong & rising",   "强且上行"),
    "weakening": ("strong but fading", "强但转弱"),
    "improving": ("turning up",        "触底回升"),
    "lagging":   ("weak & falling",    "弱且下行"),
}
PERF_ROWS = [
    ("1D", "1D", "1天"), ("1W", "1W", "1周"), ("1M", "1M", "1月"),
    ("MTD", "MTD", "月初至今"), ("3M", "3M", "3月"), ("6M", "6M", "6月"), ("1Y", "1Y", "1年"), ("YTD", "YTD", "年初至今"),
]


def _fmt_pc(v) -> str:
    if v is None:
        return "—"
    a = abs(v)
    d = 0 if a >= 100 else 1
    sign = "+" if v > 0 else ("−" if v < 0 else "")
    return f"{sign}{a:.{d}f}%"


def _lede(sub: dict) -> tuple[str, str]:
    """Plain-language 'where it sits' sentence, per quadrant + acceleration."""
    name, q = sub["name"], sub["quadrant"]
    name_zh = sub.get("name_zh") or name
    accel = sub.get("accel")
    en = {
        "leading":   f"{name} is a market leader that is still strengthening — it sits strong versus the median subsector and its relative strength is still rising.",
        "weakening": f"{name} is a former leader rolling over — still strong versus the market on level, but its relative strength has turned down (leaders rotate out from here).",
        "improving": f"{name} is turning up from behind — weaker than the median on level, but its relative strength is improving (this is where early rotation-in shows up).",
        "lagging":   f"{name} is lagging — weaker than the median subsector and its relative strength is still falling.",
    }[q]
    zh = {
        "leading":   f"{name_zh} 是仍在走强的市场领先者——相对中位数子行业偏强，且其相对强度仍在上升。",
        "weakening": f"{name_zh} 是正在走弱的昔日龙头——绝对水平仍强于大盘，但相对强度已掉头向下（资金常从这里轮出）。",
        "improving": f"{name_zh} 正从落后中触底回升——水平弱于中位数，但相对强度正在改善（早期轮入常在此显现）。",
        "lagging":   f"{name_zh} 处于落后——弱于中位数子行业，且相对强度仍在下行。",
    }[q]
    if accel is None:
        tail_en, tail_zh = " Acceleration is unavailable.", "加速度不可用。"
    elif accel > 0:
        tail_en, tail_zh = " Acceleration is positive: the latest weekly return rate is higher.", "加速度为正：最近一周的收益速率更高。"
    elif accel < 0:
        tail_en, tail_zh = " Acceleration is negative: the latest weekly return rate is lower.", "加速度为负：最近一周的收益速率更低。"
    else:
        tail_en, tail_zh = " Acceleration is zero: the compared weekly return rates are equal.", "加速度为零：所比较的每周收益速率相等。"
    return en + tail_en, zh + tail_zh


def build(site: Path | None = None) -> int:
    site = site or (config.ROOT / config.load()["storage"]["site_dir"])
    src = site / "marketdata" / "subsector_rotation.json"
    if not src.exists():
        log.warning("subsector_rotation.json missing — skipped detail pages")
        return 0
    data = json.loads(src.read_text())
    subs = data.get("subsectors") or []
    n_total = len(subs)

    env = Environment(loader=FileSystemLoader(str(config.ROOT / "templates")), autoescape=True)
    env.globals["fmt_pc"] = _fmt_pc
    tmpl = env.get_template("subsector_rotation_detail.html.j2")

    out_dir = site / "rotation"
    out_dir.mkdir(parents=True, exist_ok=True)

    n = 0
    for sub in subs:
        q = sub.get("quadrant") or "lagging"
        qd, qx = QUAD.get(q, QUAD["lagging"]), QUADX.get(q, QUADX["lagging"])
        available_members = sub.get("members") or []
        members = sorted(available_members,
                         key=lambda m: (m.get("1M") if m.get("1M") is not None else -1e9), reverse=True)[:30]
        lede_en, lede_zh = _lede(sub)
        html = tmpl.render(
            sub=sub, n_total=n_total, members=members, perf_rows=PERF_ROWS,
            asof=data.get('asof'), members_available=len(available_members), member_limit=30,
            q_cls=qd[2], q_en=qd[0], q_zh=qd[1], qx_en=qx[0], qx_zh=qx[1],
            lede_en=lede_en, lede_zh=lede_zh,
        )
        write_page(out_dir / f"{sub['key']}.html", html)
        n += 1
    log.info("wrote %d subsector detail pages -> %s", n, out_dir)
    return n


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
