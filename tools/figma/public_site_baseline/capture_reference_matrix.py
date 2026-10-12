#!/usr/bin/env python3
"""Capture the frozen four-page public-site matrix with deterministic browser state."""

from __future__ import annotations

import argparse
import base64
import functools
import hashlib
import json
import struct
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from playwright.sync_api import Browser, sync_playwright

from tools.figma.public_site_baseline.reference_matrix import (
    MOTION_PHASES,
    STATIC_VARIANTS,
    SURFACES,
    build_reference_matrix,
)

FROZEN_SOURCE = "15c01bd991f35d0bb2185ee1e608a05df0805803"
OPERATION = "public-site-figma-baseline-20260915-sol-001"
ROUTES = {
    "homepage": "/index.html",
    "market-terminal": "/products/market-terminal.html",
    "mastermind-ai": "/products/mastermind-ai.html",
    "market-dashboards": "/products/market-dashboards.html",
}
BLOB_SHAS = {
    "site/index.html": "83dc2cdef25f2869465f8492f45aab28a736dd67",
    "site/products/market-terminal.html": "422d942ad5f8a0d785fd790ddeaab1028cf2845b",
    "site/products/mastermind-ai.html": "62bb247e3b381e5fa1f250653f37c510afdc1e19",
    "site/products/market-dashboards.html": "2e190241ab91a87be145bdad398f534c28dbe85e",
    "site/landing.css": "4866885b4abd7fe2da059392c7bc46a703892970",
    "site/scene-motion.js": "ea9d810805393ce4d241a28534ee5526f7f9ddda",
    "site/scene-motion.css": "4731bb71ef7caba99a3ec9b7905c35c5fbe439e0",
}
RELEVANT_PATHS = (
    "site/index.html",
    "site/landing.css",
    "site/onboard.css",
    "site/onboard.js",
    "site/scene-motion.css",
    "site/scene-motion.js",
    "site/adtest.js",
    "site/mm_brain.js",
    "site/products",
    "site/fonts",
    "site/assets/landing",
)


@dataclass(frozen=True)
class CaptureJob:
    index: int
    kind: str
    page: str
    state: str
    route: str
    width: int
    height: int
    language: str
    wait_ms: int
    full_page: bool

    @property
    def filename(self) -> str:
        if self.kind == "static":
            return f"{self.page}-{self.state}.png"
        return f"{self.page}-hero-{self.state}.png"

    @property
    def query(self) -> dict[str, str]:
        if self.kind == "static":
            return {"still": "1", "lang": self.language}
        return {"lang": self.language}


def build_capture_jobs() -> tuple[CaptureJob, ...]:
    jobs: list[CaptureJob] = []
    for page in SURFACES:
        for variant in STATIC_VARIANTS:
            width_text, language = variant.split("-", 1)
            width = int(width_text)
            jobs.append(CaptureJob(
                index=len(jobs), kind="static", page=page, state=variant,
                route=ROUTES[page], width=width,
                height=844 if width == 390 else 900,
                language=language, wait_ms=1400, full_page=True,
            ))
    waits = dict(zip(MOTION_PHASES, (900, 2200, 4000, 6500), strict=True))
    for page in SURFACES:
        for phase in MOTION_PHASES:
            jobs.append(CaptureJob(
                index=len(jobs), kind="motion", page=page, state=phase,
                route=ROUTES[page], width=1440, height=900,
                language="en", wait_ms=waits[phase], full_page=False,
            ))
    return tuple(jobs)


def _git(source_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(source_root), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def preflight_source(
    source_root: Path,
    *,
    frozen_source: str = FROZEN_SOURCE,
) -> dict[str, str]:
    commit = _git(source_root, "cat-file", "-t", frozen_source)
    if commit.returncode != 0 or commit.stdout.strip() != "commit":
        raise RuntimeError(f"frozen source commit unavailable: {frozen_source}")
    if _git(source_root, "diff", "--quiet", "HEAD", frozen_source, "--", *RELEVANT_PATHS).returncode:
        raise RuntimeError("local committed source differs from frozen source on capture paths")
    if _git(source_root, "diff", "--quiet", "--", *RELEVANT_PATHS).returncode:
        raise RuntimeError("working tree modifies capture paths")
    for relative, expected in BLOB_SHAS.items():
        path = source_root / relative
        actual = _git(source_root, "hash-object", str(path))
        if actual.returncode or actual.stdout.strip() != expected:
            raise RuntimeError(
                f"source blob mismatch: {relative} expected={expected} "
                f"actual={actual.stdout.strip()}"
            )
    head = _git(source_root, "rev-parse", "HEAD")
    if head.returncode:
        raise RuntimeError(f"cannot resolve local head: {head.stderr.strip()}")
    return {"local_head": head.stdout.strip(), "frozen_source": frozen_source}


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        return


def _png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a PNG: {path}")
    return struct.unpack(">II", header[16:24])


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _capture_job(
    browser: Browser,
    *,
    base_url: str,
    output_dir: Path,
    job: CaptureJob,
) -> dict[str, Any]:
    context = browser.new_context(
        viewport={"width": job.width, "height": job.height},
        device_scale_factor=1,
        is_mobile=False,
    )
    context.route(
        "**/api/billing/offers/founding_pro",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"active": True, "claimed": None, "cap": 2000}),
        ),
    )
    page = context.new_page()
    page.set_default_timeout(20_000)
    console_errors: list[str] = []
    page.on(
        "console",
        lambda message: console_errors.append(message.text)
        if message.type == "error"
        else None,
    )
    url = f"{base_url}{job.route}?{urlencode(job.query)}"
    page.goto(url, wait_until="domcontentloaded", timeout=45_000)
    try:
        page.wait_for_load_state("networkidle", timeout=12_000)
    except Exception:
        pass
    page.wait_for_timeout(job.wait_ms)
    scroll = page.evaluate(
        "() => ({w: document.documentElement.scrollWidth, h: document.documentElement.scrollHeight})"
    )
    destination = output_dir / job.kind / job.filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    if job.full_page:
        cdp = context.new_cdp_session(page)
        try:
            result = cdp.send(
                "Page.captureScreenshot",
                {
                    "format": "png",
                    "captureBeyondViewport": True,
                    "fromSurface": True,
                    "clip": {
                        "x": 0,
                        "y": 0,
                        "width": job.width,
                        "height": scroll["h"],
                        "scale": 1,
                    },
                },
            )
            destination.write_bytes(base64.b64decode(result["data"]))
        finally:
            cdp.detach()
    else:
        page.screenshot(path=str(destination), full_page=False)
    context.close()

    image_width, image_height = _png_size(destination)
    record: dict[str, Any] = {
        "kind": job.kind,
        "page": job.page,
        "file": str(destination),
        "sha256": _sha256(destination),
        "bytes": destination.stat().st_size,
        "image_width": image_width,
        "image_height": image_height,
        "viewport_width": job.width,
        "viewport_height": job.height,
        "document_width": int(scroll["w"]),
        "document_height": int(scroll["h"]),
        "full_page": job.full_page,
        "wait_ms": job.wait_ms,
        "url": url,
        "console_errors": console_errors[:20],
    }
    if job.kind == "static":
        record["variant"] = job.state
    else:
        record["phase"] = job.state
    return record


def capture_reference_matrix(
    source_root: Path,
    output_dir: Path,
    *,
    frozen_source: str = FROZEN_SOURCE,
    browser_channel: str = "chrome",
    port: int = 0,
) -> dict[str, Any]:
    source = preflight_source(source_root, frozen_source=frozen_source)
    handler = functools.partial(QuietHandler, directory=str(source_root / "site"))
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.4)
    base_url = f"http://127.0.0.1:{server.server_port}"
    records: list[dict[str, Any]] = []
    captured_at = datetime.now(timezone.utc).isoformat()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                channel=browser_channel,
                headless=True,
                args=["--disable-dev-shm-usage"],
            )
            try:
                for job in build_capture_jobs():
                    print(
                        f"CAPTURE index={job.index} kind={job.kind} "
                        f"page={job.page} state={job.state}",
                        flush=True,
                    )
                    records.append(
                        _capture_job(
                            browser,
                            base_url=base_url,
                            output_dir=output_dir,
                            job=job,
                        )
                    )
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    output_dir.mkdir(parents=True, exist_ok=True)
    raw_manifest = {
        "schema": "mastermindx.public_site_figma_capture_run.v1",
        "operation": OPERATION,
        "captured_at": captured_at,
        "source": source,
        "browser": {
            "engine": "chromium",
            "channel": browser_channel,
            "headless": True,
            "device_scale_factor": 1,
        },
        "records": records,
    }
    (output_dir / "capture-manifest.json").write_text(
        json.dumps(raw_manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    matrix = build_reference_matrix(
        records,
        operation=OPERATION,
        source=source,
        built_at=captured_at,
        browser=raw_manifest["browser"],
    )
    (output_dir / "reference-matrix.json").write_text(
        json.dumps(matrix, indent=2) + "\n",
        encoding="utf-8",
    )
    return matrix


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-commit", default=FROZEN_SOURCE)
    parser.add_argument("--browser-channel", default="chrome")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--preflight-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.preflight_only:
        source = preflight_source(args.source_root, frozen_source=args.source_commit)
        print(json.dumps({"status": "SOURCE_VERIFIED", "source": source}, sort_keys=True))
        return 0
    matrix = capture_reference_matrix(
        args.source_root,
        args.output_dir,
        frozen_source=args.source_commit,
        browser_channel=args.browser_channel,
        port=args.port,
    )
    print(
        "REFERENCE_MATRIX_CAPTURED "
        f"static={matrix['counts']['static']} "
        f"motion={matrix['counts']['motion']} "
        f"output={args.output_dir}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
