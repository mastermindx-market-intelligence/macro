"""FIF P2 fixture-backed browser evidence capture wrapper.

WHY THIS EXISTS
---------------
The P2 UI PR must carry POPULATED-state crops, but the product's populated
states live behind authenticated private APIs. This wrapper wraps the
repository's existing page-evidence capture tool (``scripts/capture_page_evidence.py``)
so a real Chromium, pointed at the capture tool's own local static server for
``site/``, receives its ``/api/forensics/*`` answers from the REAL FIF kernel
running in-process in golden mode (AAPL golden) through ``app.forensics.router``
— never from hand-written JSON.

HOW IT WORKS
------------
* The page is loaded from ``http://fif-evidence.localhost:<port>/`` instead of
  ``http://127.0.0.1:<port>/``. Same scheme, port, path and query — only the
  host is rewritten, so the page's ``IS_LOOPBACK`` regex is false and the page
  takes its PRODUCTION data path (``/api/forensics/state``, health,
  attested-history, financial query/statements POSTs). Chromium resolves
  ``*.localhost`` to the loopback interface, so the capture tool's static
  server still serves the document and assets.
* A Playwright ``context.route("**/*", ...)`` handler installed by this wrapper
  (through proxies around the real driver) classifies every request:
  local ``/api/forensics/*`` is forwarded to an in-process
  ``fastapi.testclient.TestClient`` over ``FastAPI()`` with
  ``app.forensics.router`` included; other local ``/api/*`` is aborted; other
  local paths continue to the static server; every other host is aborted
  (``blockedbyclient``) and its name recorded.
* Populated mode satisfies the entitlement with the repository's existing
  router-test dependency override
  (``app.dependency_overrides[forensics_api.require_site_full_user]``). No
  browser cookie, localStorage session, token or Authorization header is ever
  synthesized. Anonymous mode runs the REAL ``require_site_full_user`` with no
  Authorization header and records the real 401.
* Populated mode first builds the private state into a TEMP root (outside the
  repo) that symlinks ONLY the five read-only kernel inputs, calls
  ``scripts.build_fundamental_forensics.compose_state``, and copies the
  produced gzip object to the tree's gitignored
  ``data/fundamental_forensics/private/state.json.gz``.
* Every exchange is appended to ``network_log.json`` (metadata + digests only;
  response bodies are never stored), and ``--fold-selector`` measures named
  selectors' fold position at screenshot time into ``fold_measurement.json``.

USAGE
-----
    python3 -m tests.tools.fif_p2_evidence_capture --mode populated \
        --out-dir /tmp/fif-evidence --as-of 2026-10-12T00:00:00Z \
        --generated-at 2026-10-12T00:00:00Z \
        --fold-selector nav=nav.site-nav --fold-selector lead=.ff-context-card

This module lives under ``tests/tools/`` on purpose: it is evidence tooling,
never product code. It originates no signal, score or escalation (A7).

SEAT FENCES (P2 evidence ruling, 2026-10-12)
--------------------------------------------
1. Every target origin must be loopback or ``*.localhost``: a non-local
   ``--base-url`` or absolute ``--route`` makes ``main`` exit non-zero BEFORE the
   env scrub, the kernel build or any capture (``refuse_non_local_targets``).
2. ``app/`` and ``engine/`` never import this module (asserted by its unit test).
3. The ``require_site_full_user`` override is installed only on the
   ``FastAPI()`` instance ``build_router_app`` creates for this run's TestClient,
   never on a module-level app a real server could share.
4. Populated manifests state ``ENTITLED_CROPS_FENCE`` verbatim; the PR body and
   DEVIATIONS repeat it. A45 entitled-browser proof stays with A0.
5. Environment variables are recorded by NAME only, never by value.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import shlex
import shutil
import sys
import tempfile
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlparse, urlunparse

TOOL_MODULE_REF = "tests/tools/fif_p2_evidence_capture.py"
WRAPPED_MODULE_REF = "scripts/capture_page_evidence.py"
KERNEL_BUILDER_REF = "scripts.build_fundamental_forensics.compose_state"

# The page must NOT see a loopback hostname, or it reads the builder artifact
# instead of the production API. *.localhost resolves to loopback in Chromium
# while failing the page's IS_LOOPBACK regex.
EVIDENCE_HOST = "fif-evidence.localhost"
SOURCE_HOST = "127.0.0.1"
LOCAL_HOSTS = frozenset({EVIDENCE_HOST, SOURCE_HOST})
HOST_REWRITE = "127.0.0.1 -> fif-evidence.localhost"
# Seat fence 4: stated verbatim in every populated manifest, the PR body and DEVIATIONS.
ENTITLED_CROPS_FENCE = (
    "entitled crops = fixture-backed golden, local, entitlement satisfied by test "
    "dependency override; not production entitlement proof"
)

FORENSICS_PREFIX = "/api/forensics/"
FINANCIAL_POST_PREFIX = "/api/forensics/v1/financial/"
FORWARDED_REQUEST_HEADERS = ("content-type", "accept", "authorization")
DROPPED_RESPONSE_HEADERS = ("content-length", "content-encoding", "transfer-encoding")

CATEGORY_FORENSICS_FORWARDED = "forensics_forwarded"
CATEGORY_OTHER_LOCAL_API_ABORTED = "other_local_api_aborted"
CATEGORY_STATIC_CONTINUED = "static_continued"
CATEGORY_EXTERNAL_ABORTED = "external_aborted"
CATEGORY_FORENSICS_FORWARD_FAILED = "forensics_forward_failed"

# Names only, never values: the scrub exists so the in-process kernel answers
# from the golden corpus and the local state copy, not from any live store.
SCRUB_ENV_PREFIXES = ("R2_", "FF_ATTESTED_", "AWS_")
SCRUB_ENV_NAMES = ("RESEARCH_LOCAL_STORE", "FIF_FINANCIAL_DATASET_MODE")

# Exactly the five read-only kernel inputs symlinked into the temp build root.
KERNEL_INPUTS: tuple[str, ...] = (
    "data/edgar/statements_quarterly.parquet",
    "data/edgar/statements.parquet",
    "data/edgar/fundamentals.parquet",
    "data/universe/membership.parquet",
    "data/breadth/ticker_sectors.parquet",
)
# A REAL directory in the temp root (never a symlink): the builder writes the
# public summary + private state under here, and none of that may reach through
# a symlink into the tree's tracked files.
KERNEL_OUTPUT_DIR = "data/fundamental_forensics"
LOCAL_STATE_RELATIVE = "data/fundamental_forensics/private/state.json.gz"

MODE_POPULATED = "populated"
MODE_ANONYMOUS = "anonymous"

POPULATED_LABEL = "fixture-backed (golden), local"
ANONYMOUS_LABEL = "anonymous-unavailable, local (real 401 from require_site_full_user)"
POPULATED_ACCESS = "fixture_backed_golden_local"
POPULATED_HONESTY = (
    "fixture-backed (golden), local: private-API responses produced in-process by the "
    "real FIF kernel in golden mode (AAPL golden) through app.forensics.router; "
    "entitlement satisfied by the repository's router-test dependency override, no "
    "credential entered, stored or synthesized; not a production capture"
)
POPULATED_ENTITLEMENT = (
    'app.dependency_overrides[app.forensics.require_site_full_user] = lambda: {"id": '
    '"fif-evidence-local"} — the repository router-test convention; no credential'
)
ANONYMOUS_ENTITLEMENT = (
    "none: the real app.forensics.require_site_full_user ran with no Authorization "
    "header and produced the real 401"
)

EVIDENCE_RECEIPT_SCHEMA = "mastermind.page_evidence_receipt.v1"

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_PARTIAL = 3
EXIT_MODE_UNAVAILABLE = 4


class FifEvidenceError(RuntimeError):
    """A typed wrapper failure. Never downgraded into a fake capture."""


class ModeUnavailable(FifEvidenceError):
    """The requested mode cannot run honestly (e.g. the real 401 path broke)."""


# ---------------------------------------------------------------------------
# URL host rewrite
# ---------------------------------------------------------------------------


def rewrite_evidence_host(url: str) -> str:
    """Rewrite ``127.0.0.1`` -> ``fif-evidence.localhost``, keeping everything else."""
    parsed = urlparse(url)
    if (parsed.hostname or "").lower() != SOURCE_HOST:
        return url
    netloc = EVIDENCE_HOST if parsed.port is None else f"{EVIDENCE_HOST}:{parsed.port}"
    return urlunparse(parsed._replace(netloc=netloc))


def is_local_origin_host(host: str) -> bool:
    """Seat fence 1: ``localhost``, ``*.localhost`` or a loopback IP literal only."""
    name = (host or "").strip().lower().rstrip(".")
    if not name:
        return False
    if name == "localhost" or name.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(name.strip("[]")).is_loopback
    except ValueError:
        return False


def refuse_non_local_targets(*, base_url: str | None, route: str) -> list[str]:
    """Seat fence 1: every origin this run could load; a non-empty answer = refuse to start.

    The default origin is the wrapped tool's own ``127.0.0.1`` static server
    (rewritten to ``fif-evidence.localhost``), which is local by construction; an
    explicit ``--base-url`` and an absolute ``--route`` are the only other origins
    the wrapped tool would navigate to, so both are checked here.
    """
    targets: list[tuple[str, str]] = []
    if base_url is not None:
        targets.append(("--base-url", base_url))
    if "://" in route:
        targets.append(("--route", route))
    refusals: list[str] = []
    for flag, url in targets:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not is_local_origin_host(parsed.hostname or ""):
            refusals.append(f"{flag} {url!r} is not a loopback or *.localhost origin")
    return refusals


# ---------------------------------------------------------------------------
# env scrub (names recorded, values never)
# ---------------------------------------------------------------------------


@dataclass
class EnvScrub:
    scrubbed_names: list[str]
    saved: dict[str, str] = field(default_factory=dict)


def scrub_process_env() -> EnvScrub:
    """Remove store/mode env vars so the kernel answers golden + local only."""
    saved: dict[str, str] = {}
    names: list[str] = []
    for name in sorted(os.environ):
        if name.startswith(SCRUB_ENV_PREFIXES) or name in SCRUB_ENV_NAMES:
            saved[name] = os.environ.pop(name)
            names.append(name)
    return EnvScrub(scrubbed_names=names, saved=saved)


def restore_process_env(scrub: EnvScrub) -> None:
    for name, value in scrub.saved.items():
        os.environ[name] = value


# ---------------------------------------------------------------------------
# network log
# ---------------------------------------------------------------------------


@dataclass
class NetworkLog:
    """Metadata + digests for every exchange. Response bodies are never stored."""

    entries: list[dict[str, Any]] = field(default_factory=list)
    aborted_hosts: set[str] = field(default_factory=set)

    def _next_seq(self) -> int:
        return len(self.entries) + 1

    def record(
        self,
        *,
        cell_id: str | None,
        method: str,
        path: str,
        query: str,
        category: str,
        status: int | None = None,
        request_body: bytes | None = None,
        response_content: bytes | None = None,
        response_content_type: str | None = None,
    ) -> dict[str, Any]:
        body = request_body if request_body is not None else b""
        request_body_json: Any = None
        if method == "POST" and path.startswith(FINANCIAL_POST_PREFIX) and request_body:
            try:
                request_body_json = json.loads(request_body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                request_body_json = None
        entry = {
            "seq": self._next_seq(),
            "cell_id": cell_id,
            "method": method,
            "path": path,
            "query": query,
            "category": category,
            "status": status,
            "request_body_bytes": len(request_body) if request_body is not None else None,
            "request_body_sha256": (
                hashlib.sha256(request_body).hexdigest() if request_body is not None else None
            ),
            "request_body_json": request_body_json,
            "response_bytes": len(response_content) if response_content is not None else None,
            "response_sha256": (
                hashlib.sha256(response_content).hexdigest() if response_content is not None else None
            ),
            "response_content_type": response_content_type,
        }
        self.entries.append(entry)
        return entry

    def as_payload(self) -> list[dict[str, Any]]:
        return [dict(entry) for entry in self.entries]


# ---------------------------------------------------------------------------
# route handler (one function, unit-testable with fake route/request objects)
# ---------------------------------------------------------------------------


def handle_exchange(
    route: Any,
    request: Any,
    *,
    client: Any,
    network_log: NetworkLog,
    cell_id: str | None,
) -> None:
    """Classify one intercepted request and answer it."""
    parsed = urlparse(request.url)
    host = (parsed.hostname or "").lower()
    path = parsed.path or "/"
    query = parsed.query or ""
    method = str(request.method or "GET").upper()

    if host in LOCAL_HOSTS:
        if path.startswith(FORENSICS_PREFIX):
            _forward_to_kernel(
                route,
                request,
                client=client,
                network_log=network_log,
                cell_id=cell_id,
                method=method,
                path=path,
                query=query,
            )
            return
        if path.startswith("/api/"):
            route.abort()
            network_log.record(
                cell_id=cell_id,
                method=method,
                path=path,
                query=query,
                category=CATEGORY_OTHER_LOCAL_API_ABORTED,
            )
            return
        route.continue_()
        network_log.record(
            cell_id=cell_id,
            method=method,
            path=path,
            query=query,
            category=CATEGORY_STATIC_CONTINUED,
        )
        return

    route.abort("blockedbyclient")
    network_log.aborted_hosts.add(host)
    network_log.record(
        cell_id=cell_id,
        method=method,
        path=path,
        query=query,
        category=CATEGORY_EXTERNAL_ABORTED,
    )


def _forward_to_kernel(
    route: Any,
    request: Any,
    *,
    client: Any,
    network_log: NetworkLog,
    cell_id: str | None,
    method: str,
    path: str,
    query: str,
) -> None:
    body = getattr(request, "post_data_buffer", None)
    forwarded_headers = {
        str(name): str(value)
        for name, value in dict(request.headers or {}).items()
        if str(name).lower() in FORWARDED_REQUEST_HEADERS
    }
    url = path + (f"?{query}" if query else "")
    try:
        response = client.request(
            method,
            url,
            content=body if body else None,
            headers=forwarded_headers,
        )
    except Exception as exc:  # noqa: BLE001 - typed, names-only refusal
        route.abort()
        network_log.record(
            cell_id=cell_id,
            method=method,
            path=path,
            query=query,
            category=CATEGORY_FORENSICS_FORWARD_FAILED,
        )
        raise FifEvidenceError(
            f"forwarding {method} {path} to the in-process kernel failed: {type(exc).__name__}"
        ) from exc
    out_headers = {
        str(name): str(value)
        for name, value in response.headers.items()
        if str(name).lower() not in DROPPED_RESPONSE_HEADERS
    }
    route.fulfill(status=response.status_code, headers=out_headers, body=response.content)
    network_log.record(
        cell_id=cell_id,
        method=method,
        path=path,
        query=query,
        category=CATEGORY_FORENSICS_FORWARDED,
        status=int(response.status_code),
        request_body=body,
        response_content=response.content,
        response_content_type=response.headers.get("content-type"),
    )


def make_route_handler(
    client: Any,
    network_log: NetworkLog,
    get_cell: Callable[[], Any],
) -> Callable[[Any, Any], None]:
    """Bind the handler to a cell slot so every exchange carries its cell_id."""

    def handler(route: Any, request: Any) -> None:
        cell = get_cell()
        handle_exchange(
            route,
            request,
            client=client,
            network_log=network_log,
            cell_id=None if cell is None else cell.cell_id,
        )

    return handler


# ---------------------------------------------------------------------------
# fold measurement (AM5) — measurement only, no judgement field
# ---------------------------------------------------------------------------

_FOLD_MEASURE_SCRIPT = """
(selectors) => {
  const scrollY = window.scrollY || 0;
  const viewportHeight = window.innerHeight;
  const measurements = [];
  for (const item of selectors) {
    const entry = {
      name: item.name,
      selector: item.selector,
      found: false,
      top: null,
      bottom: null,
      height: null,
      viewport_height: viewportHeight,
      within_first_viewport: false
    };
    try {
      const el = document.querySelector(item.selector);
      if (el) {
        const rect = el.getBoundingClientRect();
        entry.found = true;
        entry.top = rect.top + scrollY;
        entry.bottom = rect.bottom + scrollY;
        entry.height = rect.height;
        entry.within_first_viewport = entry.bottom <= viewportHeight;
      }
    } catch (e) {}
    measurements.push(entry);
  }
  return { viewport_height: viewportHeight, measurements: measurements };
}
"""


def measure_fold(
    page: Any,
    cell: Any,
    *,
    selectors: Sequence[tuple[str, str]],
    mode: str,
    sink: list[dict[str, Any]],
) -> None:
    """Record the fold position of each named selector at screenshot time."""
    row: dict[str, Any] = {
        "cell_id": cell.cell_id,
        "viewport": cell.viewport,
        "locale": cell.locale,
        "theme": cell.theme,
        "force_state": None if cell.force_state is None else cell.force_state.name,
        "mode": mode,
        "measurements": [
            {
                "name": name,
                "selector": selector,
                "found": False,
                "top": None,
                "bottom": None,
                "height": None,
                "viewport_height": None,
                "within_first_viewport": False,
            }
            for name, selector in selectors
        ],
    }
    if selectors:
        try:
            result = page.evaluate(
                _FOLD_MEASURE_SCRIPT,
                [{"name": name, "selector": selector} for name, selector in selectors],
            ) or {}
            measurements = result.get("measurements")
            if isinstance(measurements, list) and len(measurements) == len(selectors):
                row["measurements"] = measurements
        except Exception as exc:  # noqa: BLE001 - the shot still happens
            row["measure_error"] = f"{type(exc).__name__}: {exc}"
    sink.append(row)


# ---------------------------------------------------------------------------
# driver proxies
# ---------------------------------------------------------------------------


class DriverProxy:
    """Wrap the real playwright driver: rewrite the host, install routing.

    Everything the capture tool calls (``capture``/``close``) delegates to the
    real driver; only the URL host is rewritten and, before the first capture,
    the real driver's ``_browser`` is swapped for a :class:`BrowserProxy`.
    """

    def __init__(
        self,
        real_driver: Any,
        *,
        route_handler_factory: Callable[[], Callable[[Any, Any], None]],
        fold_recorder: Callable[[Any, Any], None],
    ) -> None:
        self._real = real_driver
        self._route_handler_factory = route_handler_factory
        self._fold_recorder = fold_recorder
        self._current_cell: Any = None
        self._wrapped = False

    @property
    def current_cell(self) -> Any:
        return self._current_cell

    def capture(self, *, url: str, cell: Any, timeout_s: float) -> Any:
        self._current_cell = cell
        if not self._wrapped:
            self._real._browser = BrowserProxy(
                self._real._browser,
                handler=self._route_handler_factory(),
                fold_recorder=self._fold_recorder,
                get_cell=lambda: self._current_cell,
            )
            self._wrapped = True
        return self._real.capture(url=rewrite_evidence_host(url), cell=cell, timeout_s=timeout_s)

    def close(self) -> None:
        self._real.close()


class BrowserProxy:
    """Install the route handler on every context the real browser mints."""

    def __init__(
        self,
        real_browser: Any,
        *,
        handler: Callable[[Any, Any], None],
        fold_recorder: Callable[[Any, Any], None],
        get_cell: Callable[[], Any],
    ) -> None:
        self._real = real_browser
        self._handler = handler
        self._fold_recorder = fold_recorder
        self._get_cell = get_cell

    def new_context(self, **kwargs: Any) -> Any:
        real_context = self._real.new_context(**kwargs)
        real_context.route("**/*", self._handler)
        return ContextProxy(
            real_context, fold_recorder=self._fold_recorder, get_cell=self._get_cell
        )

    def close(self) -> None:
        self._real.close()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real, name)


class ContextProxy:
    """Attribute delegation; ``new_page`` returns a measuring PageProxy."""

    def __init__(
        self,
        real_context: Any,
        *,
        fold_recorder: Callable[[Any, Any], None],
        get_cell: Callable[[], Any],
    ) -> None:
        self._real = real_context
        self._fold_recorder = fold_recorder
        self._get_cell = get_cell

    def new_page(self) -> Any:
        return PageProxy(
            self._real.new_page(),
            fold_recorder=self._fold_recorder,
            get_cell=self._get_cell,
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real, name)


class PageProxy:
    """Measure the fold first, then delegate the screenshot. All else delegates."""

    def __init__(
        self,
        real_page: Any,
        *,
        fold_recorder: Callable[[Any, Any], None],
        get_cell: Callable[[], Any],
    ) -> None:
        self._real = real_page
        self._fold_recorder = fold_recorder
        self._get_cell = get_cell

    def screenshot(self, **kwargs: Any) -> Any:
        cell = self._get_cell()
        if cell is not None:
            try:
                self._fold_recorder(self._real, cell)
            except Exception:  # noqa: BLE001 - measurement must never kill the shot
                pass
        return self._real.screenshot(**kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real, name)


# ---------------------------------------------------------------------------
# kernel state (populated mode)
# ---------------------------------------------------------------------------


@dataclass
class KernelStateReceipt:
    generated_at: str
    sha256: str
    bytes: int
    input_symlinks: tuple[str, ...]
    state_path: Path


def prepare_kernel_temp_root(tree_root: Path, temp_root: Path) -> list[str]:
    """Symlink ONLY the five read-only inputs; make the output dir a real dir."""
    created: list[str] = []
    for relative in KERNEL_INPUTS:
        source = tree_root / relative
        if not source.is_file():
            raise FifEvidenceError(f"kernel input missing from tree: {relative}")
        destination = temp_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.symlink_to(source.resolve())
        created.append(relative)
    output_dir = temp_root / KERNEL_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    if output_dir.is_symlink():
        raise FifEvidenceError(f"temp kernel output dir must be a real directory: {output_dir}")
    return created


def build_kernel_state(tree_root: Path, *, generated_at: str) -> KernelStateReceipt:
    """Build the private state into a temp root; copy the gzip object into the tree."""
    import scripts.build_fundamental_forensics as builder  # noqa: PLC0415 - heavy (pandas)

    temp_root = Path(tempfile.mkdtemp(prefix="fif-evidence-kernel-"))
    try:
        created = prepare_kernel_temp_root(tree_root, temp_root)
        state = builder.compose_state(temp_root, generated_at=generated_at)
        blob_path = temp_root / LOCAL_STATE_RELATIVE
        builder._write_state_atomic(blob_path, state)
        blob = blob_path.read_bytes()
        destination = tree_root / LOCAL_STATE_RELATIVE
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(blob_path, destination)
        return KernelStateReceipt(
            generated_at=str(generated_at),
            sha256=hashlib.sha256(blob).hexdigest(),
            bytes=len(blob),
            input_symlinks=tuple(created),
            state_path=destination,
        )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


# ---------------------------------------------------------------------------
# router app + mode verification
# ---------------------------------------------------------------------------


def load_forensics_module() -> Any:
    """Import app.forensics AFTER the env scrub, so REPO reads the scrubbed env."""
    import app.forensics as forensics_api  # noqa: PLC0415

    return forensics_api


def build_router_app(forensics_api: Any, *, populated: bool) -> Any:
    """FastAPI() with app.forensics.router; populated adds the router-test override.

    Seat fence 3: the override lands on the fresh instance created HERE for this
    run's in-process TestClient, never on ``app.main.app`` or any other
    module-level app a real server could share.
    """
    from fastapi import FastAPI  # noqa: PLC0415

    app = FastAPI()
    app.include_router(forensics_api.router)
    if populated:
        app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {
            "id": "fif-evidence-local"
        }
    return app


def verify_real_anonymous_denial(forensics_api: Any) -> None:
    """Anonymous mode requires the REAL dependency to produce the REAL 401.

    If importing/running it fails, the exception text is reported verbatim and
    the mode stops — a hand-made 401 is never substituted.
    """
    from fastapi import HTTPException  # noqa: PLC0415

    try:
        forensics_api.require_site_full_user(None)
    except HTTPException as exc:
        if exc.status_code != 401:
            raise ModeUnavailable(
                f"real require_site_full_user denied with HTTP {exc.status_code}, not 401: "
                f"{exc.detail!r}"
            ) from exc
        return
    except Exception as exc:  # noqa: BLE001 - verbatim report, never a substitute
        raise ModeUnavailable(
            "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        ) from exc
    raise ModeUnavailable(
        "real require_site_full_user returned success without a credential; refusing to "
        "continue anonymous mode"
    )


# ---------------------------------------------------------------------------
# manifest post-process
# ---------------------------------------------------------------------------


def postprocess_manifest(
    manifest: dict[str, Any],
    *,
    mode: str,
    generator_command: str,
    wrapper_module_sha256: str,
    scrubbed_env_names: Sequence[str],
    aborted_hosts: Sequence[str],
    state_receipt: KernelStateReceipt | None,
) -> None:
    """Keep everything the capture tool wrote; add the fixture-backed provenance."""
    populated = mode == MODE_POPULATED
    label = POPULATED_LABEL if populated else ANONYMOUS_LABEL
    for page in manifest.get("pages", []):
        for state_row in page.get("states", []):
            state_row["evidence_label"] = label
    if populated:
        manifest.setdefault("axes", {})["access"] = [POPULATED_ACCESS]
        manifest.setdefault("honesty", {})["access"] = POPULATED_HONESTY
        manifest["honesty"]["entitlement"] = ENTITLED_CROPS_FENCE
    evidence_source: dict[str, Any] = {
        "label": label,
        "mode": mode,
        "generator_command": generator_command,
        "wrapper_module": TOOL_MODULE_REF,
        "wrapper_module_sha256": wrapper_module_sha256,
        "entitlement": POPULATED_ENTITLEMENT if populated else ANONYMOUS_ENTITLEMENT,
        "host_rewrite": HOST_REWRITE,
    }
    if populated and state_receipt is not None:
        evidence_source["state"] = {
            "builder": KERNEL_BUILDER_REF,
            "generated_at": state_receipt.generated_at,
            "sha256": state_receipt.sha256,
            "bytes": state_receipt.bytes,
        }
    if populated:
        evidence_source["entitlement_fence"] = ENTITLED_CROPS_FENCE
    evidence_source["financial_dataset_mode"] = "golden"
    evidence_source["scrubbed_env_names"] = sorted(scrubbed_env_names)
    evidence_source["aborted_hosts"] = sorted(set(aborted_hosts))
    evidence_source["network_log"] = "network_log.json"
    evidence_source["fold_measurement"] = "fold_measurement.json"
    manifest["evidence_source"] = evidence_source


def rest_cell_misses(manifest: Mapping[str, Any]) -> list[str]:
    """Every rest (unforced) state row that did not capture, by cell."""
    misses: list[str] = []
    for page in manifest.get("pages", []):
        for state_row in page.get("states", []):
            if state_row.get("force_state") is not None:
                continue
            if not state_row.get("captured"):
                misses.append(str(state_row.get("reason") or "captured: false"))
    return misses


# ---------------------------------------------------------------------------
# EVIDENCE.yml receipt
# ---------------------------------------------------------------------------


def write_evidence_yml(
    path: Path,
    *,
    changed_paths: Sequence[str],
    manifest_relative: str,
) -> None:
    """Exactly three keys: schema, changed_paths, manifest."""
    lines = [f"schema: {EVIDENCE_RECEIPT_SCHEMA}", "changed_paths:"]
    for changed in changed_paths:
        lines.append(f"  - {json.dumps(changed)}")
    lines.append(f"manifest: {json.dumps(manifest_relative)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_fold_selectors(raw_values: Sequence[str]) -> list[tuple[str, str]]:
    selectors: list[tuple[str, str]] = []
    for raw in raw_values:
        if "=" not in raw:
            raise argparse.ArgumentTypeError(
                f"--fold-selector expects NAME=CSS, got {raw!r}"
            )
        name, selector = raw.split("=", 1)
        name, selector = name.strip(), selector.strip()
        if not name or not selector:
            raise argparse.ArgumentTypeError(
                f"--fold-selector expects NAME=CSS, got {raw!r}"
            )
        selectors.append((name, selector))
    return selectors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--mode", required=True, choices=(MODE_POPULATED, MODE_ANONYMOUS))
    parser.add_argument("--route", default="/fundamental_forensics.html?symbol=AAPL")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument(
        "--base-url",
        default=None,
        help="optional LOCAL origin already serving site/ (loopback or *.localhost only; "
        "anything else is refused before capture). Default: the wrapped tool's own "
        "127.0.0.1 server for site/",
    )
    parser.add_argument("--as-of", help="pin the capture tool's generated_at (ISO)")
    parser.add_argument("--generated-at", help="kernel state clock for compose_state (ISO)")
    parser.add_argument(
        "--force-state",
        action="append",
        default=[],
        metavar="NAME:TARGET",
        dest="force_state",
        help="repeatable; passed through to the wrapped capture tool",
    )
    parser.add_argument(
        "--fold-selector",
        action="append",
        default=[],
        metavar="NAME=CSS",
        dest="fold_selector",
        help="repeatable; measure this selector's fold position at screenshot time",
    )
    parser.add_argument(
        "--changed-path",
        action="append",
        default=[],
        metavar="P",
        dest="changed_path",
        help="repeatable; emit EVIDENCE.yml naming these paths",
    )
    parser.add_argument("--viewports", default="desktop,mobile")
    parser.add_argument("--locales", default="en,zh")
    parser.add_argument("--themes", default="dark,light")
    return parser


def _wrapped_driver_factory(
    *,
    client: Any,
    network_log: NetworkLog,
    fold_rows: list[dict[str, Any]],
    fold_selectors: Sequence[tuple[str, str]],
    mode: str,
) -> Callable[..., DriverProxy]:
    from scripts.capture_page_evidence import playwright_page_driver  # noqa: PLC0415

    # The route handler must read the CURRENT cell off the exact proxy this
    # factory returns, so the proxy registers itself through this slot.
    slot: list[DriverProxy | None] = [None]

    def factory(**kwargs: Any) -> DriverProxy:
        real_driver = playwright_page_driver(**kwargs)
        proxy = DriverProxy(
            real_driver,
            route_handler_factory=lambda: make_route_handler(
                client,
                network_log,
                lambda: slot[0].current_cell if slot[0] is not None else None,
            ),
            fold_recorder=lambda page, cell: measure_fold(
                page, cell, selectors=fold_selectors, mode=mode, sink=fold_rows
            ),
        )
        slot[0] = proxy
        return proxy

    return factory


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    refusals = refuse_non_local_targets(base_url=args.base_url, route=args.route)
    if refusals:
        for refusal in refusals:
            print(f"error: refusing to start (seat fence 1): {refusal}", file=sys.stderr)
        return EXIT_USAGE
    invoked = list(sys.argv[1:] if argv is None else argv)
    generator_command = shlex.join(
        ["python3", "-m", "tests.tools.fif_p2_evidence_capture", *invoked]
    )

    tree_root = Path(__file__).resolve().parents[2]
    out_dir = Path(args.out_dir).expanduser().resolve()
    populated = args.mode == MODE_POPULATED
    if populated and not args.generated_at:
        print(
            "error: --generated-at is required in populated mode (kernel state clock)",
            file=sys.stderr,
        )
        return EXIT_USAGE

    try:
        fold_selectors = parse_fold_selectors(args.fold_selector)
    except argparse.ArgumentTypeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE

    scrub = scrub_process_env()
    prior_macro_repo = os.environ.get("MACRO_REPO")
    try:
        os.environ["MACRO_REPO"] = str(tree_root)
        forensics_api = load_forensics_module()
        prior_repo = forensics_api.REPO
        forensics_api.REPO = tree_root
        try:
            state_receipt: KernelStateReceipt | None = None
            if populated:
                state_receipt = build_kernel_state(tree_root, generated_at=args.generated_at)
                print(
                    f"kernel state: {state_receipt.bytes} bytes sha256={state_receipt.sha256[:16]} "
                    f"-> {LOCAL_STATE_RELATIVE}"
                )
            else:
                verify_real_anonymous_denial(forensics_api)

            network_log = NetworkLog()
            fold_rows: list[dict[str, Any]] = []
            router_app = build_router_app(forensics_api, populated=populated)
            from fastapi.testclient import TestClient  # noqa: PLC0415

            with TestClient(router_app, raise_server_exceptions=False) as client:
                capture_rc = _run_wrapped_capture(
                    args,
                    tree_root=tree_root,
                    out_dir=out_dir,
                    client=client,
                    network_log=network_log,
                    fold_rows=fold_rows,
                    fold_selectors=fold_selectors,
                )
        finally:
            forensics_api.REPO = prior_repo
    except ModeUnavailable as exc:
        print(
            f"::error title=fif-p2-evidence::{args.mode} mode unavailable; reporting the "
            "failure verbatim (never substituting a hand-made answer)",
            flush=True,
        )
        print(str(exc), file=sys.stderr)
        return EXIT_MODE_UNAVAILABLE
    except FifEvidenceError as exc:
        print(f"::error title=fif-p2-evidence::{type(exc).__name__}: {exc}", flush=True)
        return EXIT_MODE_UNAVAILABLE
    finally:
        if prior_macro_repo is None:
            os.environ.pop("MACRO_REPO", None)
        else:
            os.environ["MACRO_REPO"] = prior_macro_repo
        restore_process_env(scrub)

    if capture_rc != 0 and not (out_dir / "manifest.json").is_file():
        print(f"error: wrapped capture failed with exit {capture_rc}; no manifest written")
        return capture_rc or EXIT_PARTIAL

    from scripts.capture_page_evidence import canonical_json_bytes  # noqa: PLC0415

    manifest_path = out_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    wrapper_sha256 = hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest()
    postprocess_manifest(
        manifest,
        mode=args.mode,
        generator_command=generator_command,
        wrapper_module_sha256=wrapper_sha256,
        scrubbed_env_names=scrub.scrubbed_names,
        aborted_hosts=sorted(network_log.aborted_hosts),
        state_receipt=state_receipt,
    )
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    (out_dir / "network_log.json").write_bytes(canonical_json_bytes(network_log.as_payload()))
    (out_dir / "fold_measurement.json").write_bytes(canonical_json_bytes(fold_rows))

    if args.changed_path:
        manifest_relative = (
            Path(os.path.relpath(out_dir, tree_root)) / "manifest.json"
        ).as_posix()
        write_evidence_yml(
            out_dir / "EVIDENCE.yml",
            changed_paths=args.changed_path,
            manifest_relative=manifest_relative,
        )

    misses = rest_cell_misses(manifest)
    totals = manifest.get("totals", {})
    print(f"mode: {args.mode}")
    print(
        f"rest cells: {totals.get('states_captured', 0)}/{totals.get('states_attempted', 0)} "
        f"captured (forced cells included in totals)"
    )
    print(f"forensics exchanges: {sum(1 for e in network_log.entries if e['category'] == CATEGORY_FORENSICS_FORWARDED)}")
    print(f"aborted hosts: {sorted(network_log.aborted_hosts)}")
    print(f"manifest: {manifest_path}")
    if misses:
        print(
            "::warning title=fif-p2-evidence::rest cells not captured: "
            + "; ".join(misses[:5]),
            flush=True,
        )
        return EXIT_PARTIAL
    return EXIT_OK


def _run_wrapped_capture(
    args: argparse.Namespace,
    *,
    tree_root: Path,
    out_dir: Path,
    client: Any,
    network_log: NetworkLog,
    fold_rows: list[dict[str, Any]],
    fold_selectors: Sequence[tuple[str, str]],
) -> int:
    from scripts.capture_page_evidence import main as capture_main  # noqa: PLC0415

    base_url = getattr(args, "base_url", None)
    origin_argv = ["--base-url", base_url] if base_url else ["--site-dir", str(tree_root / "site")]
    capture_argv: list[str] = [
        *origin_argv,
        "--routes",
        args.route,
        "--output-dir",
        str(out_dir),
        "--manifest",
        str(out_dir / "manifest.json"),
        "--smells",
        str(out_dir / "smells.json"),
        "--viewports",
        args.viewports,
        "--locales",
        args.locales,
        "--themes",
        args.themes,
    ]
    if args.as_of:
        capture_argv += ["--as-of", args.as_of]
    for force_state in args.force_state:
        capture_argv += ["--force-state", force_state]

    factory = _wrapped_driver_factory(
        client=client,
        network_log=network_log,
        fold_rows=fold_rows,
        fold_selectors=fold_selectors,
        mode=args.mode,
    )
    return capture_main(capture_argv, driver_factory=factory)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
