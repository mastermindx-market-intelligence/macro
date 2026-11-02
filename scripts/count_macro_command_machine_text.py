"""Count machine-text tokens in Macro Command site pages (P5 E-m1 / E-m2).

Precedence rule ACTUALLY applied (drawer-priority, not innermost-ancestor):
  drawer wins when present (aside.mq-drawer), else innermost of details.mc-details,
  else top.

Run from repo root:
  python3 scripts/count_macro_command_machine_text.py

Stdout is the receipt — paste it verbatim into the claims comment.
"""
from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"

P5_PAGES = [
    "macro_monetary.html",
    "macro_rates_curves.html",
    "macro_liquidity_regime.html",
    "macro_growth_real_economy.html",
    "macro_business_activity.html",
    "macro_financial_conditions.html",
    "macro_housing_real_estate.html",
    "macro_labor_markets.html",
    "macro_monetary_policy.html",
    "macro_inflation_system.html",
    "macro_consumer_payments.html",
    "macro_capital_structure.html",
    "macro_liquidity_central_banks.html",
    "macro_national_debt_liabilities.html",
    "macro_trade_flows.html",
]

STRICT_SNAKE = re.compile(
    r"(?<![\w.])[a-z][a-z0-9]*(?:_[a-z0-9]+)+(?![\w])"
)
LOOSE_SNAKE = re.compile(r"[A-Za-z0-9]+_[A-Za-z0-9_]+")
PARQUET = re.compile(r"\.parquet\b")
RULEID = re.compile(r"\b[A-Z]{2,}-[A-Z0-9]{2,}(?:-[A-Z0-9]+)*\b")


class _TextWalker(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.nodes: list[tuple[str, str]] = []  # (bucket, text)
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        attrs_d = {k: (v or "") for k, v in attrs}
        classes = set((attrs_d.get("class") or "").split())
        if tag in {"script", "style"}:
            self._skip += 1
            self.stack.append(tag)
            return
        role = "top"
        if tag == "aside" and "mq-drawer" in classes:
            role = "drawer"
        elif tag == "details" and "mc-details" in classes:
            role = "details"
        self.stack.append(role if role != "top" else tag)
        if self._skip:
            return

    def handle_endtag(self, tag):
        if self.stack:
            self.stack.pop()
        if tag in {"script", "style"} and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if self._skip or not data or not data.strip():
            return
        # Drawer-priority: scan stack bottom-up for drawer, else details.
        bucket = "top"
        for item in self.stack:
            if item == "drawer":
                bucket = "drawer"
                break
        if bucket == "top":
            for item in reversed(self.stack):
                if item == "details":
                    bucket = "details"
                    break
        self.nodes.append((bucket, data))


def count_file(path: Path) -> dict[str, dict[str, int]]:
    html = path.read_text(encoding="utf-8")
    walker = _TextWalker()
    walker.feed(html)
    out = {
        "drawer": {"strict": 0, "loose": 0, "parquet": 0, "ruleid": 0},
        "details": {"strict": 0, "loose": 0, "parquet": 0, "ruleid": 0},
        "top": {"strict": 0, "loose": 0, "parquet": 0, "ruleid": 0},
    }
    for bucket, text in walker.nodes:
        out[bucket]["strict"] += len(STRICT_SNAKE.findall(text))
        out[bucket]["loose"] += len(LOOSE_SNAKE.findall(text))
        out[bucket]["parquet"] += len(PARQUET.findall(text))
        out[bucket]["ruleid"] += len(RULEID.findall(text))
    return out


def main() -> int:
    totals = {
        "drawer": {"strict": 0, "loose": 0, "parquet": 0, "ruleid": 0},
        "details": {"strict": 0, "loose": 0, "parquet": 0, "ruleid": 0},
        "top": {"strict": 0, "loose": 0, "parquet": 0, "ruleid": 0},
    }
    print("RULE: drawer wins when present, else innermost of details/…, else top")
    print(f"PAGES: {len(P5_PAGES)}")
    for name in P5_PAGES:
        path = SITE / name
        if not path.is_file():
            print(f"MISSING {name}", file=sys.stderr)
            return 1
        row = count_file(path)
        for bucket in totals:
            for key in totals[bucket]:
                totals[bucket][key] += row[bucket][key]
    for bucket in ("drawer", "details", "top"):
        t = totals[bucket]
        print(
            f"{bucket}: strict={t['strict']} loose={t['loose']} "
            f"parquet={t['parquet']} ruleid={t['ruleid']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
