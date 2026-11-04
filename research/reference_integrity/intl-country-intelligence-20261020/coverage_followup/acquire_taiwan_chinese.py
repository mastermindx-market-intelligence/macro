"""Fetch the already identified official Chinese version of the same TW release."""
import json
from pathlib import Path
import acquire_primary

if __name__ == "__main__":
    acquire_primary.ROOT = Path(__file__).resolve().parent / "primary_artifacts" / "tw_chinese"
    acquire_primary.ROOT.mkdir(exist_ok=False)
    result = acquire_primary.acquire((
        "TW",
        "https://www.stat.gov.tw/News_Content.aspx?n=2677&s=236591",
        "stat_2026q2_20260814_zh.html",
    ))
    print(json.dumps(result, ensure_ascii=False, indent=2))
