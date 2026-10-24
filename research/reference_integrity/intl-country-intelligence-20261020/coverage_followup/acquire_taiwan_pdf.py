"""Fetch the official release PDF discovered in the publisher's indexed result."""
import json
from pathlib import Path
import acquire_primary

if __name__ == "__main__":
    acquire_primary.ROOT = Path(__file__).resolve().parent / "primary_artifacts" / "tw_pdf"
    acquire_primary.ROOT.mkdir(exist_ok=False)
    result = acquire_primary.acquire((
        "TW",
        "https://ws.dgbas.gov.tw/001/Upload/463/relfile/10980/236591/news11508.pdf",
        "dgbas_2026q2_20260814_zh.pdf",
    ))
    print(json.dumps(result, ensure_ascii=False, indent=2))
