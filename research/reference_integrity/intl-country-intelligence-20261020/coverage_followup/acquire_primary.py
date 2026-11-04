"""Bounded public-source acquisition into scratch; never admits product data."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parent / "primary_artifacts"
MAX_BYTES = 4_000_000
SOURCES = (
    ("TW", "https://eng.dgbas.gov.tw/News_Content.aspx?n=4438&s=236587", "dgbas_2026q2_20260814.html"),
    ("IN", "https://www.mospi.gov.in/uploads/latestReleases/latest_release_1788172583113_d65a77cf-240e-4491-82ee-59f78618fa41_Press_Note_on_GDP_Estimates_for_Q1_2026-27.pdf", "mospi_q1_fy2026_27_20260831.pdf"),
)
HEADERS = ("Content-Type", "Content-Length", "Content-Encoding", "Date", "ETag", "Last-Modified", "Location", "Cache-Control", "Server")


def utcnow():
    return datetime.now(timezone.utc).isoformat()


class OfficialRedirects(HTTPRedirectHandler):
    def __init__(self):
        self.chain = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        hostname = (urlparse(newurl).hostname or "").lower()
        if not any(hostname == domain or hostname.endswith("." + domain) for domain in ("dgbas.gov.tw", "mospi.gov.in", "stat.gov.tw")):
            raise ValueError("redirect_outside_registered_publisher_domains")
        self.chain.append({"from_url": req.full_url, "status": code, "to_url": newurl})
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def acquire(item):
    cc, url, filename = item
    handler = OfficialRedirects()
    request_headers = {"Accept-Encoding": "identity", "User-Agent": "InternationalMarketsSourceResearch/1.0"}
    receipt = {"cc": cc, "requested_url": url, "request_method": "GET", "request_headers": request_headers,
               "started_at": utcnow(), "status": "attempted", "source_artifact": None,
               "source_sha256": None, "source_bytes": None, "production_admitted": False}
    began = time.monotonic()
    try:
        try:
            response = build_opener(handler).open(Request(url, headers=request_headers), timeout=20)
        except HTTPError as response_error:
            response = response_error
        with response:
            receipt["http_status"] = response.status
            receipt["final_url"] = response.geturl()
            receipt["response_headers"] = {key: response.headers[key] for key in HEADERS if key in response.headers}
            chunks, size = [], 0
            while True:
                block = response.read(65536)
                if not block:
                    break
                size += len(block)
                if size > MAX_BYTES or time.monotonic() - began > 35:
                    raise ValueError("bounded_download_budget_exceeded")
                chunks.append(block)
        blob = b"".join(chunks)
        receipt["retrieved_at"] = utcnow()
        receipt["response_body_sha256"] = sha256(blob).hexdigest()
        receipt["response_body_bytes"] = len(blob)
        if response.status != 200:
            target = ROOT / (cc.lower() + "_http_error_response.bin")
            receipt["status"] = "http_error"
            receipt["error_artifact"] = str(target)
        elif filename.lower().endswith(".pdf") and not blob.startswith(b"%PDF-"):
            target = ROOT / (cc.lower() + "_non_pdf_response.bin")
            receipt["status"] = "unexpected_document_type"
            receipt["error_artifact"] = str(target)
        else:
            target = ROOT / filename
            receipt.update(status="acquired_unqualified", source_artifact=str(target),
                           source_sha256=sha256(blob).hexdigest(), source_bytes=len(blob))
        target.write_bytes(blob)
    except (OSError, URLError, ValueError, TimeoutError) as error:
        receipt.update(status="download_failed", error_type=type(error).__name__, error=str(error)[:400])
    receipt["redirect_chain"] = handler.chain
    receipt["completed_at"] = utcnow()
    receipt["elapsed_seconds"] = round(time.monotonic() - began, 3)
    path = ROOT / (cc.lower() + "_acquisition_receipt.json")
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt


if __name__ == "__main__":
    ROOT.mkdir(exist_ok=True)
    if any((ROOT / (cc.lower() + "_acquisition_receipt.json")).exists() for cc, _, _ in SOURCES):
        raise SystemExit("Existing acquisition receipts found; inspect before any repeat request.")
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(acquire, SOURCES))
    print(json.dumps(results, ensure_ascii=False, indent=2))
