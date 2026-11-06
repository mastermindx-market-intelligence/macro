"""Browser-free unit tests for the FIF P2 fixture-backed evidence wrapper.

No browser, no network. The route handler is exercised directly with fake
route/request objects; the router behind it is the REAL ``app.forensics.router``
in-process. The only monkeypatch anywhere in this file is the state-blob source
for the GET /api/forensics/state forwarding test (the kernel state itself is
built for real from the tree's six parquet inputs in the temp-root tests).
"""
from __future__ import annotations

import gzip
import hashlib
import json
import ast
import contextlib
import io
import os
import re
import subprocess
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.forensics as forensics_api
import tests.tools.fif_p2_evidence_capture as tool
from scripts.capture_page_evidence import CaptureCell

ROOT = Path(__file__).resolve().parents[1]

STATE_PATH = "/api/forensics/state"
QUERY_PATH = "/api/forensics/v1/financial/query"

# The golden AAPL request body used by tests/test_fundamental_forensics_financial_query_api.py
# (the ``_p1_aapl_body`` shape: ISS:US-XNAS-AAPL, latest_known_as_of, FY2023 revenue).
GOLDEN_AAPL_QUERY_BODY = json.dumps(
    {
        "schema": "fundamental_forensics.financial_query_request/v1",
        "entity_id": "ISS:US-XNAS-AAPL",
        "policy": {
            "selection": "latest_known_as_of",
            "source_snapshot_at": "2025-12-31T23:59:59Z",
            "recorded_at": "2026-10-05T00:00:00Z",
        },
        "metric_ids": ["revenue"],
        "periods": [
            {"kind": "duration", "start": "2023-01-01", "end": "2023-12-31", "label": "FY2023"}
        ],
    },
    separators=(",", ":"),
).encode("utf-8")

# The Data OS issuer binding the golden kernel resolves needs two tracked
# reference parquets this lane's sparse cone leaves on the floor. Materializing
# them byte-identically from the repo's own git objects is git-invisible
# (skip-worktree entries, identical content => clean status); the fixture
# restores the mint state afterwards.
GIT_REFERENCE_PATHS = (
    "data/reference/security_master.parquet",
    "data/reference/issuer_master.parquet",
)


@pytest.fixture
def golden_reference_rows():
    created: list[Path] = []
    for relative in GIT_REFERENCE_PATHS:
        path = ROOT / relative
        if path.exists():
            continue
        blob = subprocess.run(
            ["git", "show", f"HEAD:{relative}"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        ).stdout
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
        created.append(path)
    try:
        yield
    finally:
        for path in created:
            path.unlink()
            # Writing the file cleared the sparse mint's skip-worktree bit; put
            # the mint state back so the deletion is not read as a change.
            subprocess.run(
                ["git", "update-index", "--skip-worktree", path.relative_to(ROOT).as_posix()],
                cwd=ROOT,
                capture_output=True,
                check=True,
            )


# ---------------------------------------------------------------------------
# fakes
# ---------------------------------------------------------------------------


class FakeRoute:
    def __init__(self) -> None:
        self.fulfilled: dict[str, Any] | None = None
        self.aborted: str | None = None
        self.continued = False

    def fulfill(self, *, status=None, headers=None, body=None) -> None:
        self.fulfilled = {
            "status": status,
            "headers": {str(k): str(v) for k, v in dict(headers or {}).items()},
            "body": body,
        }

    def abort(self, error: str | None = None) -> None:
        self.aborted = error or "default"

    def continue_(self) -> None:
        self.continued = True


class FakeRequest:
    def __init__(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
    ) -> None:
        self.method = method
        self.url = url
        self.headers = {k.lower(): v for k, v in (headers or {}).items()}
        self.post_data_buffer = body


def _populated_client() -> TestClient:
    app = tool.build_router_app(forensics_api, populated=True)
    return TestClient(app, raise_server_exceptions=False)


def _anonymous_client() -> TestClient:
    app = tool.build_router_app(forensics_api, populated=False)
    return TestClient(app, raise_server_exceptions=False)


def _state_blob() -> bytes:
    document = {
        "schema": "fundamental_forensics_state.v1",
        "generated_at": "2026-10-12T00:00:00Z",
        "companies": {"AAPL": {"ticker": "AAPL", "findings": []}},
    }
    return gzip.compress(
        json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        mtime=0,
    )


def _cell(**overrides: Any) -> CaptureCell:
    kwargs: dict[str, Any] = {
        "page_id": "fundamental_forensics.html",
        "route": "/fundamental_forensics.html",
        "viewport": "desktop",
        "width": 1440,
        "height": 900,
        "locale": "en",
        "theme": "dark",
    }
    kwargs.update(overrides)
    return CaptureCell(**kwargs)


# ---------------------------------------------------------------------------
# populated forwarding through the real router
# ---------------------------------------------------------------------------


def test_populated_get_state_forwards_200_gzip(monkeypatch) -> None:
    blob = _state_blob()
    monkeypatch.setattr(forensics_api, "REPO", ROOT)
    monkeypatch.setattr(forensics_api, "load_state_blob", lambda _root: blob)
    with _populated_client() as client:
        route = FakeRoute()
        log = tool.NetworkLog()
        tool.handle_exchange(
            route,
            FakeRequest(
                "GET",
                "http://fif-evidence.localhost:8000/api/forensics/state",
                headers={"accept": "application/gzip"},
            ),
            client=client,
            network_log=log,
            cell_id="cell-1",
        )
    assert route.aborted is None and not route.continued
    assert route.fulfilled is not None
    assert route.fulfilled["status"] == 200
    assert route.fulfilled["body"] == blob
    header_names = {name.lower() for name in route.fulfilled["headers"]}
    assert "content-length" not in header_names
    assert "content-encoding" not in header_names
    assert "transfer-encoding" not in header_names
    assert route.fulfilled["headers"]["content-type"].startswith("application/gzip")
    entry = log.entries[0]
    assert entry["category"] == tool.CATEGORY_FORENSICS_FORWARDED
    assert entry["status"] == 200
    assert entry["cell_id"] == "cell-1"
    assert entry["path"] == STATE_PATH
    assert entry["response_bytes"] == len(blob)
    assert entry["response_sha256"] == hashlib.sha256(blob).hexdigest()
    assert entry["request_body_bytes"] is None
    assert entry["request_body_json"] is None


@pytest.mark.data_gate
def test_populated_post_financial_query_golden_200(golden_reference_rows, monkeypatch) -> None:
    monkeypatch.setattr(forensics_api, "REPO", ROOT)
    with _populated_client() as client:
        route = FakeRoute()
        log = tool.NetworkLog()
        tool.handle_exchange(
            route,
            FakeRequest(
                "POST",
                f"http://fif-evidence.localhost:8000{QUERY_PATH}",
                headers={"content-type": "application/json", "accept": "application/json"},
                body=GOLDEN_AAPL_QUERY_BODY,
            ),
            client=client,
            network_log=log,
            cell_id="cell-2",
        )
    assert route.fulfilled is not None
    assert route.fulfilled["status"] == 200, route.fulfilled["body"][:200]
    entry = log.entries[0]
    assert entry["status"] == 200
    assert entry["request_body_bytes"] == len(GOLDEN_AAPL_QUERY_BODY)
    assert entry["request_body_sha256"] == hashlib.sha256(GOLDEN_AAPL_QUERY_BODY).hexdigest()
    assert entry["request_body_json"] == json.loads(GOLDEN_AAPL_QUERY_BODY)
    assert entry["response_bytes"] == len(route.fulfilled["body"])
    assert entry["response_sha256"] == hashlib.sha256(route.fulfilled["body"]).hexdigest()
    assert entry["response_content_type"] == "application/json"


def test_anonymous_get_state_real_401() -> None:
    with _anonymous_client() as client:
        route = FakeRoute()
        log = tool.NetworkLog()
        tool.handle_exchange(
            route,
            FakeRequest("GET", "http://fif-evidence.localhost:8000/api/forensics/state"),
            client=client,
            network_log=log,
            cell_id="cell-3",
        )
    assert route.fulfilled is not None
    assert route.fulfilled["status"] == 401
    assert json.loads(route.fulfilled["body"]) == {"detail": "missing bearer token"}
    assert log.entries[0]["status"] == 401
    assert log.entries[0]["category"] == tool.CATEGORY_FORENSICS_FORWARDED


# ---------------------------------------------------------------------------
# request classification
# ---------------------------------------------------------------------------


def test_external_host_aborted_and_logged() -> None:
    route = FakeRoute()
    log = tool.NetworkLog()
    tool.handle_exchange(
        route,
        FakeRequest("GET", "https://app.mastermind-x.com/api/forensics/state"),
        client=None,
        network_log=log,
        cell_id=None,
    )
    assert route.aborted == "blockedbyclient"
    assert route.fulfilled is None and not route.continued
    assert "app.mastermind-x.com" in log.aborted_hosts
    assert log.entries[0]["category"] == tool.CATEGORY_EXTERNAL_ABORTED
    assert log.entries[0]["status"] is None


def test_other_local_api_aborted() -> None:
    route = FakeRoute()
    log = tool.NetworkLog()
    tool.handle_exchange(
        route,
        FakeRequest("GET", "http://fif-evidence.localhost:8000/api/other"),
        client=None,
        network_log=log,
        cell_id="cell-4",
    )
    assert route.aborted == "default"
    assert log.entries[0]["category"] == tool.CATEGORY_OTHER_LOCAL_API_ABORTED
    assert log.entries[0]["path"] == "/api/other"


def test_static_paths_continued_for_both_local_hosts() -> None:
    for url in (
        "http://fif-evidence.localhost:8000/fundamental_forensics.html?symbol=AAPL",
        "http://127.0.0.1:8000/theme.css",
    ):
        route = FakeRoute()
        log = tool.NetworkLog()
        tool.handle_exchange(
            route,
            FakeRequest("GET", url),
            client=None,
            network_log=log,
            cell_id="cell-5",
        )
        assert route.continued
        assert route.fulfilled is None and route.aborted is None
        assert log.entries[0]["category"] == tool.CATEGORY_STATIC_CONTINUED


def test_financial_body_json_only_for_financial_posts() -> None:
    log = tool.NetworkLog()
    log.record(
        cell_id="c",
        method="POST",
        path="/api/forensics/v1/attested-history/x",
        query="",
        category=tool.CATEGORY_FORENSICS_FORWARDED,
        request_body=b'{"a": 1}',
    )
    assert log.entries[0]["request_body_json"] is None


# ---------------------------------------------------------------------------
# host rewrite
# ---------------------------------------------------------------------------


def test_host_rewrite() -> None:
    assert (
        tool.rewrite_evidence_host("http://127.0.0.1:4567/a?b=c")
        == "http://fif-evidence.localhost:4567/a?b=c"
    )
    assert (
        tool.rewrite_evidence_host("http://127.0.0.1/fundamental_forensics.html")
        == "http://fif-evidence.localhost/fundamental_forensics.html"
    )
    assert tool.rewrite_evidence_host("https://www.mastermind-x.com/x") == (
        "https://www.mastermind-x.com/x"
    )


# ---------------------------------------------------------------------------
# env scrub: names recorded, values never
# ---------------------------------------------------------------------------


def test_env_scrub_records_names_never_values(monkeypatch) -> None:
    monkeypatch.setenv("R2_SECRET_ENDPOINT", "https://secret.example")
    monkeypatch.setenv("AWS_SECRET_KEY", "AKIAVALUE")
    monkeypatch.setenv("FF_ATTESTED_R2_READONLY_BUCKET", "bucket-name")
    monkeypatch.setenv("RESEARCH_LOCAL_STORE", "store-value")
    monkeypatch.setenv("FIF_FINANCIAL_DATASET_MODE", "production")
    monkeypatch.setenv("UNRELATED_VAR", "stays")
    scrub = tool.scrub_process_env()
    assert sorted(scrub.scrubbed_names) == [
        "AWS_SECRET_KEY",
        "FF_ATTESTED_R2_READONLY_BUCKET",
        "FIF_FINANCIAL_DATASET_MODE",
        "R2_SECRET_ENDPOINT",
        "RESEARCH_LOCAL_STORE",
    ]
    recorded = json.dumps(scrub.scrubbed_names)
    for value in ("secret.example", "AKIAVALUE", "bucket-name", "store-value", "production"):
        assert value not in recorded
    assert os.environ.get("FIF_FINANCIAL_DATASET_MODE") is None
    assert os.environ.get("UNRELATED_VAR") == "stays"
    tool.restore_process_env(scrub)
    assert os.environ.get("FIF_FINANCIAL_DATASET_MODE") == "production"
    assert os.environ.get("R2_SECRET_ENDPOINT") == "https://secret.example"


# ---------------------------------------------------------------------------
# manifest post-process
# ---------------------------------------------------------------------------


def _fake_manifest() -> dict[str, Any]:
    return {
        "schema": "mastermind.p0_evidence.v2",
        "axes": {"viewports": {}, "locales": ["en"], "themes": ["dark"], "access": ["anonymous"]},
        "honesty": {
            "access": "anonymous only; no credential is entered, stored, or synthesized",
            "gaps": "states that were not captured are recorded with a reason",
            "authority": "measures and screenshots; judges nothing",
        },
        "pages": [
            {
                "page_id": "p",
                "states": [
                    {"viewport": "desktop", "captured": True, "force_state": None},
                    {"viewport": "mobile", "captured": True, "force_state": None},
                    {"viewport": "desktop", "captured": True, "force_state": "empty"},
                ],
            }
        ],
    }


def test_manifest_postprocess_populated() -> None:
    manifest = _fake_manifest()
    receipt = tool.KernelStateReceipt(
        generated_at="2026-10-12T00:00:00Z",
        sha256="a" * 64,
        bytes=123456,
        input_symlinks=tool.KERNEL_INPUTS,
        state_path=Path("/tmp/x"),
    )
    tool.postprocess_manifest(
        manifest,
        mode=tool.MODE_POPULATED,
        generator_command="python3 -m tests.tools.fif_p2_evidence_capture --mode populated",
        wrapper_module_sha256="b" * 64,
        scrubbed_env_names=["R2_X", "AWS_Y"],
        aborted_hosts=["logo.dev", "supabase"],
        state_receipt=receipt,
    )
    states = manifest["pages"][0]["states"]
    assert all(row["evidence_label"] == tool.POPULATED_LABEL for row in states)
    assert manifest["axes"]["access"] == [tool.POPULATED_ACCESS]
    assert manifest["honesty"]["access"] == tool.POPULATED_HONESTY
    assert manifest["honesty"]["gaps"] == (
        "states that were not captured are recorded with a reason"
    )
    source = manifest["evidence_source"]
    assert set(source) == {
        "label",
        "mode",
        "generator_command",
        "wrapper_module",
        "wrapper_module_sha256",
        "entitlement",
        "host_rewrite",
        "state",
        "financial_dataset_mode",
        "scrubbed_env_names",
        "aborted_hosts",
        "network_log",
        "fold_measurement",
        "entitlement_fence",
    }
    assert source["state"] == {
        "builder": "scripts.build_fundamental_forensics.compose_state",
        "generated_at": "2026-10-12T00:00:00Z",
        "sha256": "a" * 64,
        "bytes": 123456,
    }
    assert source["financial_dataset_mode"] == "golden"
    assert source["aborted_hosts"] == ["logo.dev", "supabase"]
    assert source["scrubbed_env_names"] == ["AWS_Y", "R2_X"]
    assert source["network_log"] == "network_log.json"
    assert source["fold_measurement"] == "fold_measurement.json"
    assert source["host_rewrite"] == tool.HOST_REWRITE


def test_manifest_postprocess_anonymous() -> None:
    manifest = _fake_manifest()
    original_access = manifest["honesty"]["access"]
    tool.postprocess_manifest(
        manifest,
        mode=tool.MODE_ANONYMOUS,
        generator_command="python3 -m tests.tools.fif_p2_evidence_capture --mode anonymous",
        wrapper_module_sha256="b" * 64,
        scrubbed_env_names=[],
        aborted_hosts=[],
        state_receipt=None,
    )
    states = manifest["pages"][0]["states"]
    assert all(row["evidence_label"] == tool.ANONYMOUS_LABEL for row in states)
    assert manifest["axes"]["access"] == ["anonymous"]
    assert manifest["honesty"]["access"] == original_access
    source = manifest["evidence_source"]
    assert "state" not in source
    assert source["label"] == tool.ANONYMOUS_LABEL
    assert source["mode"] == tool.MODE_ANONYMOUS


def test_rest_cell_misses_ignores_forced_rows() -> None:
    manifest = {
        "pages": [
            {
                "states": [
                    {"captured": True, "force_state": None},
                    {"captured": False, "force_state": "empty", "reason": "nope"},
                    {"captured": False, "force_state": None, "reason": "HTTP 500"},
                ]
            }
        ]
    }
    misses = tool.rest_cell_misses(manifest)
    assert misses == ["HTTP 500"]


# ---------------------------------------------------------------------------
# EVIDENCE.yml receipt
# ---------------------------------------------------------------------------


def test_evidence_yml_exactly_three_keys(tmp_path: Path) -> None:
    import yaml

    path = tmp_path / "EVIDENCE.yml"
    tool.write_evidence_yml(
        path,
        # ci-trigger-closure: data — receipt entries are file NAMES, never opened
        changed_paths=["site/fundamental_forensics.js", "site/fundamental_forensics.css"],
        manifest_relative="out/manifest.json",
    )
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert set(loaded) == {"schema", "changed_paths", "manifest"}
    assert loaded["schema"] == "mastermind.page_evidence_receipt.v1"
    assert loaded["changed_paths"] == [
        # ci-trigger-closure: data — the same file NAMES read back from the receipt
        "site/fundamental_forensics.js",
        "site/fundamental_forensics.css",
    ]
    assert loaded["manifest"] == "out/manifest.json"


# ---------------------------------------------------------------------------
# kernel temp-root build: the six inputs, nothing writes through
# ---------------------------------------------------------------------------


def test_prepare_kernel_temp_root_symlinks_exactly_six_inputs(tmp_path: Path) -> None:
    created = tool.prepare_kernel_temp_root(ROOT, tmp_path)
    assert tuple(created) == tool.KERNEL_INPUTS
    for relative in tool.KERNEL_INPUTS:
        link = tmp_path / relative
        assert link.is_symlink(), relative
        assert link.resolve() == (ROOT / relative).resolve()
    output_dir = tmp_path / tool.KERNEL_OUTPUT_DIR
    assert output_dir.is_dir() and not output_dir.is_symlink()
    # No other path under the temp root exists yet.
    assert sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_symlink()) == sorted(
        tool.KERNEL_INPUTS
    )


@pytest.mark.data_gate
def test_kernel_build_never_writes_through_to_tracked_files(tmp_path: Path) -> None:
    tracked_summary = ROOT / "data" / "fundamental_forensics" / "public_summary.json"
    inputs_before = {
        relative: (ROOT / relative).read_bytes() for relative in tool.KERNEL_INPUTS
    }
    summary_before = tracked_summary.read_bytes()
    receipt = tool.build_kernel_state(ROOT, generated_at="2026-10-12T00:00:00Z")
    try:
        assert receipt.input_symlinks == tool.KERNEL_INPUTS
        produced = (ROOT / tool.LOCAL_STATE_RELATIVE).read_bytes()
        assert receipt.bytes == len(produced)
        assert receipt.sha256 == hashlib.sha256(produced).hexdigest()
        import gzip as gzip_mod

        document = json.loads(gzip_mod.decompress(produced))
        assert document["generated_at"] == "2026-10-12T00:00:00Z"
        assert "companies" in document
        # The temp-root build left every tracked input and the tracked summary
        # byte-identical: nothing wrote through a symlink.
        assert tracked_summary.read_bytes() == summary_before
        assert all((ROOT / relative).read_bytes() == blob for relative, blob in inputs_before.items())
    finally:
        # The copied private state is gitignored, but restore the mint state.
        produced_path = ROOT / tool.LOCAL_STATE_RELATIVE
        if produced_path.exists():
            produced_path.unlink()


# ---------------------------------------------------------------------------
# driver proxies + fold measurement (fakes, no browser)
# ---------------------------------------------------------------------------


class FakeRealDriver:
    def __init__(self, browser: Any) -> None:
        self._browser = browser
        self.calls: list[dict[str, Any]] = []
        self.closed = False

    def capture(self, *, url: str, cell: Any, timeout_s: float) -> str:
        self.calls.append({"url": url, "cell": cell, "timeout_s": timeout_s})
        return "observation"

    def close(self) -> None:
        self.closed = True


class FakeBrowser:
    def __init__(self) -> None:
        self.contexts: list[FakeContext] = []
        self.closed = False

    def new_context(self, **kwargs: Any) -> "FakeContext":
        context = FakeContext()
        self.contexts.append(context)
        return context

    def close(self) -> None:
        self.closed = True


class FakeContext:
    def __init__(self) -> None:
        self.routes: list[tuple[str, Any]] = []
        self.init_scripts: list[str] = []
        self.pages: list[FakePage] = []
        self.closed = False

    def route(self, pattern: str, handler: Any) -> None:
        self.routes.append((pattern, handler))

    def add_init_script(self, script: str) -> None:
        self.init_scripts.append(script)

    def new_page(self) -> "FakePage":
        page = FakePage()
        self.pages.append(page)
        return page

    def close(self) -> None:
        self.closed = True


class FakePage:
    def __init__(self) -> None:
        self.evaluated: list[tuple[str, Any]] = []
        self.shots = 0

    def evaluate(self, script: str, arg: Any = None) -> Any:
        self.evaluated.append((script, arg))
        return {
            "viewport_height": 900,
            "measurements": [
                {
                    "name": "nav",
                    "selector": "nav.site-nav",
                    "found": True,
                    "top": 0,
                    "bottom": 64,
                    "height": 64,
                    "viewport_height": 900,
                    "within_first_viewport": True,
                }
            ],
        }

    def screenshot(self, **kwargs: Any) -> bytes:
        self.shots += 1
        return b"png-bytes"


def test_driver_proxy_rewrites_host_and_installs_routing() -> None:
    real_driver = FakeRealDriver(FakeBrowser())
    fold_rows: list[dict[str, Any]] = []
    handler_calls: list[Any] = []

    def handler(route: Any, request: Any) -> None:
        handler_calls.append(request)

    proxy = tool.DriverProxy(
        real_driver,
        route_handler_factory=lambda: handler,
        fold_recorder=lambda page, cell: tool.measure_fold(
            page, cell, selectors=[("nav", "nav.site-nav")], mode="populated", sink=fold_rows
        ),
    )
    cell = _cell()
    result = proxy.capture(
        url="http://127.0.0.1:4567/fundamental_forensics.html?symbol=AAPL",
        cell=cell,
        timeout_s=5,
    )
    assert result == "observation"
    assert real_driver.calls[0]["url"] == "http://fif-evidence.localhost:4567/fundamental_forensics.html?symbol=AAPL"
    assert real_driver.calls[0]["cell"] is cell
    assert isinstance(real_driver._browser, tool.BrowserProxy)

    context = real_driver._browser.new_context(viewport={"width": 1440, "height": 900})
    assert isinstance(context, tool.ContextProxy)
    assert [pattern for pattern, _ in context.routes] == ["**/*"]
    context.add_init_script("seed")
    assert context.init_scripts == ["seed"]

    page = context.new_page()
    assert isinstance(page, tool.PageProxy)
    assert page.screenshot(full_page=True) == b"png-bytes"
    assert page.shots == 1
    # The fold measurement ran through the real page's evaluate BEFORE the shot.
    assert len(page.evaluated) == 1
    assert fold_rows and fold_rows[0]["cell_id"] == cell.cell_id
    assert fold_rows[0]["mode"] == "populated"
    assert fold_rows[0]["measurements"][0]["found"] is True

    proxy.close()
    assert real_driver.closed
    context.close()
    assert context.closed


def test_measure_fold_records_row_without_judgement() -> None:
    page = FakePage()
    rows: list[dict[str, Any]] = []
    cell = _cell(viewport="mobile", width=390, height=844, locale="en", theme="dark")
    tool.measure_fold(
        page,
        cell,
        selectors=[("nav", "nav.site-nav"), ("lead", ".ff-context-card")],
        mode="anonymous",
        sink=rows,
    )
    row = rows[0]
    assert set(row) == {
        "cell_id",
        "viewport",
        "locale",
        "theme",
        "force_state",
        "mode",
        "measurements",
    }
    assert row["viewport"] == "mobile"
    assert row["force_state"] is None
    # The fake page returns one measurement for two selectors: the defensive
    # mismatch keeps the pre-seeded not-found rows instead of inventing data.
    assert len(row["measurements"]) == 2
    assert row["measurements"][0]["name"] == "nav"
    assert row["measurements"][1]["found"] is False
    assert page.evaluated and page.evaluated[0][1] == [
        {"name": "nav", "selector": "nav.site-nav"},
        {"name": "lead", "selector": ".ff-context-card"},
    ]


def test_measure_fold_evaluate_failure_still_records() -> None:
    class BrokenPage:
        def evaluate(self, script: str, arg: Any = None) -> Any:
            raise RuntimeError("page gone")

    rows: list[dict[str, Any]] = []
    tool.measure_fold(
        BrokenPage(),
        _cell(),
        selectors=[("nav", "nav.site-nav")],
        mode="populated",
        sink=rows,
    )
    row = rows[0]
    assert row["measure_error"].startswith("RuntimeError: page gone")
    assert row["measurements"][0]["found"] is False
    assert row["measurements"][0]["rendered"] is False
    assert row["measurements"][0]["within_first_viewport"] is False


def test_fold_script_never_counts_an_unrendered_element_as_above_the_fold() -> None:
    # display:none yields a zero rect at y=0; the fold verdict must require a box.
    script = tool._FOLD_MEASURE_SCRIPT
    assert "entry.rendered = el.getClientRects().length > 0;" in script
    assert "entry.within_first_viewport = entry.rendered && entry.bottom <= viewportHeight;" in script


def test_route_handler_binds_cell_id() -> None:
    log = tool.NetworkLog()
    holder: dict[str, Any] = {"cell": _cell()}

    class TrackingClient:
        def request(self, method: str, url: str, **kwargs: Any) -> Any:
            from types import SimpleNamespace

            return SimpleNamespace(
                status_code=200,
                headers={"content-type": "application/json", "content-length": "2"},
                content=b"{}",
            )

    handler = tool.make_route_handler(TrackingClient(), log, lambda: holder["cell"])
    route = FakeRoute()
    handler(route, FakeRequest("GET", "http://fif-evidence.localhost:1/api/forensics/state"))
    assert log.entries[0]["cell_id"] == holder["cell"].cell_id

    holder["cell"] = None
    route2 = FakeRoute()
    handler(route2, FakeRequest("GET", "http://fif-evidence.localhost:1/api/forensics/state"))
    assert log.entries[1]["cell_id"] is None


# ---------------------------------------------------------------------------
# anonymous mode verification (real dependency, no browser)
# ---------------------------------------------------------------------------


def test_verify_real_anonymous_denial_accepts_real_401() -> None:
    tool.verify_real_anonymous_denial(forensics_api)


def test_verify_real_anonymous_denial_refuses_success(monkeypatch) -> None:
    monkeypatch.setattr(forensics_api, "require_site_full_user", lambda _auth: {"id": "x"})
    with pytest.raises(tool.ModeUnavailable, match="returned success"):
        tool.verify_real_anonymous_denial(forensics_api)


def test_verify_real_anonymous_denial_reports_failure_verbatim(monkeypatch) -> None:
    def _boom(_auth: str | None) -> None:
        raise ImportError("app.main import error: no module named 'x'")

    monkeypatch.setattr(forensics_api, "require_site_full_user", _boom)
    with pytest.raises(tool.ModeUnavailable) as excinfo:
        tool.verify_real_anonymous_denial(forensics_api)
    assert "ImportError" in str(excinfo.value)
    assert "app.main import error: no module named 'x'" in str(excinfo.value)


# ---------------------------------------------------------------------------
# CLI parsing
# ---------------------------------------------------------------------------


def test_parse_fold_selectors() -> None:
    assert tool.parse_fold_selectors(["nav=nav.site-nav", "lead=.ff-hero"]) == [
        ("nav", "nav.site-nav"),
        ("lead", ".ff-hero"),
    ]
    with pytest.raises(Exception):
        tool.parse_fold_selectors(["no-equals-sign"])
    with pytest.raises(Exception):
        tool.parse_fold_selectors(["=x"])


# ---------------------------------------------------------------------------
# render guard (P2 r3 repair d): refuse an unrendered or stale served page
# ---------------------------------------------------------------------------

GUARD_TEMPLATE = (
    '<div id="ff-desk-header">{{ t("As of", "As of") }}</div>'
    '<button id="ff-asof-latest">{{ t("Latest", "Latest") }}</button>'
)
GUARD_CLEAN_HTML = (
    '<div id="ff-desk-header">As of</div>'
    '<button id="ff-asof-latest">Latest</button>'
)


def test_render_guard_pins_the_commands_and_a_distinct_exit_code() -> None:
    assert tool.RENDER_COMMAND == (
        "python3 -c \"from pathlib import Path; "
        "from scripts.build_fundamental_forensics import render_shell; "
        "render_shell(Path('.').resolve())\""
    )
    assert tool.RESTORE_COMMAND == "git checkout -- site/fundamental_forensics.html"
    assert tool.EXIT_STALE_PAGE == 5
    assert tool.EXIT_STALE_PAGE not in {
        tool.EXIT_OK,
        tool.EXIT_USAGE,
        tool.EXIT_PARTIAL,
        tool.EXIT_MODE_UNAVAILABLE,
    }


def test_render_guard_help_epilog_prints_both_commands() -> None:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        tool.build_parser().print_help()
    text = buffer.getvalue()
    assert f"render first with: {tool.RENDER_COMMAND}" in text
    assert f"restore afterwards with: {tool.RESTORE_COMMAND}" in text


def test_render_guard_refuses_unrendered_jinja_markers() -> None:
    html = (
        '<main>{{ company.name }}</main>'
        '<div id="ff-desk-header">x</div><button id="ff-asof-latest">x</button>'
    )
    problems = tool.served_page_problems(html, GUARD_TEMPLATE)
    assert len(problems) == 1
    assert problems[0].startswith("unrendered Jinja marker {{ at byte")
    assert "company.name" in problems[0]


def test_render_guard_reports_only_the_first_offending_marker() -> None:
    html = (
        'a {% if x %} b {{ y }} c '
        '<div id="ff-desk-header">x</div><button id="ff-asof-latest">x</button>'
    )
    problems = tool.served_page_problems(html, GUARD_TEMPLATE)
    assert len(problems) == 1
    assert "marker {% at byte" in problems[0]


def test_render_guard_refuses_a_stale_render_by_template_id_census() -> None:
    # Zero Jinja markers, both literal template ids present except one: only
    # the id census separates this stale page from a fresh render.
    html = '<html><body><div id="ff-desk-header">As of</div></body></html>'
    assert tool.served_page_problems(html, GUARD_TEMPLATE) == [
        "stale render: 1 template id(s) missing from the served page: ff-asof-latest"
    ]


def test_render_guard_caps_the_missing_id_list_at_ten() -> None:
    template = "".join(f'<i id="ff-i{i:02d}"></i>' for i in range(12))
    problems = tool.served_page_problems("<html></html>", template)
    assert len(problems) == 1
    assert "12 template id(s) missing from the served page: " in problems[0]
    assert "(+2 more)" in problems[0]
    assert "ff-i11" not in problems[0].split("(+2 more)", 1)[0]


def test_render_guard_clean_pass() -> None:
    assert tool.served_page_problems(GUARD_CLEAN_HTML, GUARD_TEMPLATE) == []


def _forbid_browser(monkeypatch) -> None:
    def _forbidden(name: str):
        def _boom(*_args: Any, **_kwargs: Any) -> Any:
            raise AssertionError(f"{name} ran although the served page is stale")

        return _boom

    # The wrapped capture import is what pulls in Playwright; the forensics
    # import and the env scrub both precede it in main(), so guarding all
    # three proves the refusal happened before any browser could launch.
    monkeypatch.setattr(tool, "_run_wrapped_capture", _forbidden("_run_wrapped_capture"))
    monkeypatch.setattr(tool, "load_forensics_module", _forbidden("load_forensics_module"))
    monkeypatch.setattr(tool, "scrub_process_env", _forbidden("scrub_process_env"))


def test_main_refuses_a_stale_site_dir_before_any_browser(monkeypatch, tmp_path: Path) -> None:
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "fundamental_forensics.html").write_text(
        "<html><body>stale, no ff ids</body></html>", encoding="utf-8"
    )
    out_dir = tmp_path / "out"
    _forbid_browser(monkeypatch)
    rc = tool.main(
        [
            "--mode",
            tool.MODE_ANONYMOUS,
            "--out-dir",
            str(out_dir),
            "--site-dir",
            str(site_dir),
        ]
    )
    assert rc == tool.EXIT_STALE_PAGE
    assert not out_dir.exists()


def test_main_refusal_names_the_render_and_restore_commands(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "fundamental_forensics.html").write_text(
        "<html><body>stale, no ff ids</body></html>", encoding="utf-8"
    )
    _forbid_browser(monkeypatch)
    rc = tool.main(
        [
            "--mode",
            tool.MODE_ANONYMOUS,
            "--out-dir",
            str(tmp_path / "out"),
            "--site-dir",
            str(site_dir),
        ]
    )
    assert rc == tool.EXIT_STALE_PAGE
    err = capsys.readouterr().err
    assert err.startswith("refusing to capture:")
    assert "stale render:" in err
    assert f"render first with: {tool.RENDER_COMMAND}" in err
    assert f"restore afterwards with: {tool.RESTORE_COMMAND}" in err


def test_main_refuses_a_stale_base_url_page_through_the_fetch_hook(
    monkeypatch, tmp_path: Path
) -> None:
    fetched: list[str] = []

    def fake_fetch(base_url: str, route: str) -> str:
        fetched.append(base_url + route)
        return "<html>no ff ids here</html>"

    monkeypatch.setattr(tool, "fetch_served_page", fake_fetch)
    _forbid_browser(monkeypatch)
    rc = tool.main(
        [
            "--mode",
            tool.MODE_ANONYMOUS,
            "--out-dir",
            str(tmp_path / "out"),
            "--base-url",
            "http://127.0.0.1:8123",
        ]
    )
    assert rc == tool.EXIT_STALE_PAGE
    # Fetched exactly once, from the already loopback-checked origin.
    assert fetched == ["http://127.0.0.1:8123/fundamental_forensics.html?symbol=AAPL"]


def test_main_render_guard_reads_the_committed_template(tmp_path: Path) -> None:
    # The census compares against THIS tree's template, not a passed-in one:
    # an html holding the synthetic guard ids is still stale against the real
    # template (which has 90+ more literal ids, so the report cap engages too).
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "fundamental_forensics.html").write_text(GUARD_CLEAN_HTML, encoding="utf-8")
    refusals = tool.render_guard_refusals(
        tree_root=ROOT,
        site_dir=site_dir,
        base_url=None,
        route="/fundamental_forensics.html?symbol=AAPL",
    )
    assert len(refusals) == 1
    match = re.match(r"stale render: (\d+) template id\(s\) missing", refusals[0])
    assert match and int(match.group(1)) > tool.STALE_ID_REPORT_CAP
    assert "(+" in refusals[0] and "more)" in refusals[0]


def test_render_guard_missing_served_page_is_a_refusal(tmp_path: Path) -> None:
    refusals = tool.render_guard_refusals(
        tree_root=ROOT,
        site_dir=tmp_path,
        base_url=None,
        route="/fundamental_forensics.html?symbol=AAPL",
    )
    assert len(refusals) == 1
    assert refusals[0].startswith("served page missing:")


def test_fold_measurement_records_left_and_right_geometry() -> None:
    script = tool._FOLD_MEASURE_SCRIPT
    assert "const scrollX = window.scrollX || 0;" in script
    assert "entry.left = rect.left + scrollX;" in script
    assert "entry.right = rect.right + scrollX;" in script

    class Gone:
        def evaluate(self, script: str, arg: Any = None) -> Any:
            raise RuntimeError("no page")

    rows: list[dict[str, Any]] = []
    tool.measure_fold(Gone(), _cell(), selectors=[("fab", "#mmb-boot")], mode="populated", sink=rows)
    assert rows[0]["measurements"][0]["left"] is None
    assert rows[0]["measurements"][0]["right"] is None


# ---------------------------------------------------------------------------
# seat fences (P2 evidence ruling, 2026-10-12)
# ---------------------------------------------------------------------------

FENCE_SENTENCE = (
    "entitled crops = fixture-backed golden, local, entitlement satisfied by test "
    "dependency override; not production entitlement proof"
)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8000",
        "http://127.0.0.2:8000/",
        "http://localhost:8000",
        "http://fif-evidence.localhost:41234",
        "http://[::1]:8000",
    ],
)
def test_fence1_local_origins_accepted(url: str) -> None:
    assert tool.refuse_non_local_targets(base_url=url, route="/fundamental_forensics.html") == []
    assert tool.refuse_non_local_targets(base_url=None, route=url + "/fundamental_forensics.html") == []


@pytest.mark.parametrize(
    "url",
    [
        "https://macro.example.com",
        "http://10.0.0.5:8000",
        "http://0.0.0.0:8000",
        "http://localhost.example.com",
        "http://fif-evidence.localhost.example.com",
        "file:///etc/hosts",
    ],
)
def test_fence1_non_local_origins_refused(url: str) -> None:
    assert tool.refuse_non_local_targets(base_url=url, route="/fundamental_forensics.html")


def _forbid_any_capture(monkeypatch) -> list[str]:
    calls: list[str] = []

    def _guard(name: str):
        def _boom(*_args: Any, **_kwargs: Any) -> Any:
            calls.append(name)
            raise AssertionError(f"{name} ran although the target origin is not local")

        return _boom

    for name in ("scrub_process_env", "load_forensics_module", "build_kernel_state", "_run_wrapped_capture"):
        monkeypatch.setattr(tool, name, _guard(name))
    return calls


def test_fence1_non_local_base_url_exits_nonzero_before_capture(monkeypatch, tmp_path: Path) -> None:
    calls = _forbid_any_capture(monkeypatch)
    out_dir = tmp_path / "out"
    rc = tool.main(
        ["--mode", tool.MODE_ANONYMOUS, "--out-dir", str(out_dir), "--base-url", "https://macro.example.com"]
    )
    assert rc != 0 and rc == tool.EXIT_USAGE
    assert calls == []
    assert not out_dir.exists()


def test_fence1_non_local_absolute_route_exits_nonzero_before_capture(monkeypatch, tmp_path: Path) -> None:
    calls = _forbid_any_capture(monkeypatch)
    out_dir = tmp_path / "out"
    rc = tool.main(
        [
            "--mode",
            tool.MODE_POPULATED,
            "--generated-at",
            "2026-10-12T00:00:00Z",
            "--out-dir",
            str(out_dir),
            "--route",
            "https://macro.example.com/fundamental_forensics.html?symbol=AAPL",
        ]
    )
    assert rc != 0
    assert calls == []
    assert not out_dir.exists()


def test_fence1_cli_refuses_non_local_base_url_in_a_subprocess(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "tests.tools.fif_p2_evidence_capture",
            "--mode",
            "anonymous",
            "--out-dir",
            str(out_dir),
            "--base-url",
            "https://macro.example.com",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert proc.returncode != 0
    assert "refusing to start" in proc.stderr
    assert not out_dir.exists()


def test_fence2_app_and_engine_never_import_the_tool() -> None:
    offenders: list[str] = []
    for top in ("app", "engine"):
        for path in sorted((ROOT / top).rglob("*.py")):
            text = path.read_text(encoding="utf-8", errors="replace")
            if "fif_p2_evidence_capture" in text or "tests.tools" in text or "tests/tools" in text:
                offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == []


def test_fence3_override_assigned_only_on_the_tool_created_app() -> None:
    tree = ast.parse(Path(tool.__file__).read_text(encoding="utf-8"))
    owners: list[str] = []
    for func in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        created = {
            target.id
            for node in ast.walk(func)
            if isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "FastAPI"
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        for node in ast.walk(func):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if (
                    isinstance(target, ast.Subscript)
                    and isinstance(target.value, ast.Attribute)
                    and target.value.attr == "dependency_overrides"
                ):
                    holder = target.value.value
                    assert isinstance(holder, ast.Name) and holder.id in created, ast.dump(target)
                    owners.append(func.name)
    module_level = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(t, ast.Subscript) and isinstance(t.value, ast.Attribute) and t.value.attr == "dependency_overrides"
            for t in node.targets
        )
    ]
    assert owners == ["build_router_app"]
    assert module_level == []


def test_fence3_runtime_override_never_reaches_a_shared_app() -> None:
    from fastapi import FastAPI

    first = tool.build_router_app(forensics_api, populated=True)
    second = tool.build_router_app(forensics_api, populated=True)
    anonymous = tool.build_router_app(forensics_api, populated=False)
    assert first is not second
    assert forensics_api.require_site_full_user in first.dependency_overrides
    assert anonymous.dependency_overrides == {}
    mine = {id(first), id(second), id(anonymous)}
    for module_name, module in list(sys.modules.items()):
        for attr, value in list(getattr(module, "__dict__", {}).items()):
            if isinstance(value, FastAPI) and id(value) not in mine:
                assert forensics_api.require_site_full_user not in value.dependency_overrides, (
                    f"{module_name}.{attr}"
                )


def test_fence4_entitled_crops_sentence_verbatim() -> None:
    assert tool.ENTITLED_CROPS_FENCE == FENCE_SENTENCE
    manifest = _fake_manifest()
    tool.postprocess_manifest(
        manifest,
        mode=tool.MODE_POPULATED,
        generator_command="python3 -m tests.tools.fif_p2_evidence_capture --mode populated",
        wrapper_module_sha256="c" * 64,
        scrubbed_env_names=[],
        aborted_hosts=[],
        state_receipt=None,
    )
    assert manifest["evidence_source"]["entitlement_fence"] == FENCE_SENTENCE
    assert manifest["honesty"]["entitlement"] == FENCE_SENTENCE
    anonymous = _fake_manifest()
    tool.postprocess_manifest(
        anonymous,
        mode=tool.MODE_ANONYMOUS,
        generator_command="python3 -m tests.tools.fif_p2_evidence_capture --mode anonymous",
        wrapper_module_sha256="c" * 64,
        scrubbed_env_names=[],
        aborted_hosts=[],
        state_receipt=None,
    )
    assert "entitlement_fence" not in anonymous["evidence_source"]


def test_fence5_manifest_carries_env_names_never_values(monkeypatch) -> None:
    monkeypatch.setenv("R2_FENCE_PROBE", "fence-value-must-not-leak")
    scrub = tool.scrub_process_env()
    try:
        manifest = _fake_manifest()
        tool.postprocess_manifest(
            manifest,
            mode=tool.MODE_POPULATED,
            generator_command="python3 -m tests.tools.fif_p2_evidence_capture --mode populated",
            wrapper_module_sha256="d" * 64,
            scrubbed_env_names=scrub.scrubbed_names,
            aborted_hosts=[],
            state_receipt=None,
        )
    finally:
        tool.restore_process_env(scrub)
    blob = json.dumps(manifest)
    assert "R2_FENCE_PROBE" in manifest["evidence_source"]["scrubbed_env_names"]
    assert "fence-value-must-not-leak" not in blob


# ---------------------------------------------------------------------------
# real browser interactions: interception + scripted DOM probes (no browser)
# ---------------------------------------------------------------------------


def _interaction_payload(name: str) -> dict[str, Any]:
    from scripts.capture_page_evidence import parse_force_state

    return parse_force_state(f"{name}:[{tool.INTERACTION_ATTRIBUTE}={name}]").as_payload()


class _ScriptedLocator:
    def __init__(self, page: "_ScriptedPage", selector: str) -> None:
        self._page = page
        self._selector = selector

    @property
    def first(self) -> "_ScriptedLocator":
        return self

    def click(self, **kwargs: Any) -> None:
        self._page.clicks.append(self._selector)
        if self._page.click_error is not None:
            raise self._page.click_error


class _ScriptedKeyboard:
    def __init__(self, page: "_ScriptedPage") -> None:
        self._page = page

    def press(self, key: str) -> None:
        self._page.keys.append(key)


class _ScriptedPage:
    """Answers each DOM probe from its own queue; records every real input."""

    def __init__(self, *, drawer: Any = (), active: Any = (), tablist: Any = ()) -> None:
        self.queues = {"drawer": list(drawer), "active": list(active), "tablist": list(tablist)}
        self.keys: list[str] = []
        self.clicks: list[str] = []
        self.waits: list[int] = []
        self.resets = 0
        self.click_error: Exception | None = None
        self.keyboard = _ScriptedKeyboard(self)
        self.moves: list[tuple[int, int]] = []
        self.mouse = types.SimpleNamespace(move=lambda x, y: self.moves.append((x, y)))
        # A43 Z1 repair: the disabled-controls probe answer (the same list back
        # every call; each keyboard interaction probes it once per receipt).
        self.disabled_answers: list[Any] = []
        self.evaluate_calls = 0
        self.disabled_probe_at = 0

    def locator(self, selector: str) -> _ScriptedLocator:
        return _ScriptedLocator(self, selector)

    def wait_for_timeout(self, ms: int) -> None:
        self.waits.append(ms)

    def evaluate(self, script: str, arg: Any = None) -> Any:
        self.evaluate_calls += 1
        if script == tool._FOCUS_RESET_SCRIPT.strip():
            self.resets += 1
            return None
        if script == tool._DISABLED_CONTROLS_SCRIPT.strip():
            self.disabled_probe_at = self.evaluate_calls
            return list(self.disabled_answers)
        queue = {
            tool._DRAWER_PROBE_SCRIPT.strip(): "drawer",
            tool._ACTIVE_PROBE_SCRIPT.strip(): "active",
            tool._TABLIST_PROBE_SCRIPT.strip(): "tablist",
        }[script]
        return self.queues[queue].pop(0)


def _trap_probe(index: int | None, *, inside: bool = True, count: int = 3) -> dict[str, Any]:
    return {
        "present": True,
        "open": True,
        "modal": True,
        "focus_inside": inside,
        "focus_index": index if inside else None,
        "focusable": count,
    }


def _raising_runner(*_args: Any) -> Any:
    raise RuntimeError("interaction runner failed")


def _proxy_page(runner: Any) -> tuple[FakePage, Any]:
    real = FakePage()
    page = tool.PageProxy(
        real,
        fold_recorder=lambda page, cell: None,
        get_cell=lambda: _cell(),
        interaction_runner=runner,
    )
    return real, page


def test_interaction_force_spec_parses_to_the_intercepted_payload_shape() -> None:
    for name in tool.INTERACTION_INPUTS:
        payload = _interaction_payload(name)
        assert payload["kind"] == "attribute"
        assert payload["attribute"] == tool.INTERACTION_ATTRIBUTE
        assert payload["name"] == name and payload["value"] == name
        assert tool.is_interaction_payload(payload)
    assert set(tool.INTERACTION_INPUTS) == {
        tool.INTERACTION_DRAWER_OPEN,
        tool.INTERACTION_TAB_KEYS,
        tool.INTERACTION_DRAWER_TRAP,
        tool.INTERACTION_SAVED_RESTORE_PINNED,
        tool.INTERACTION_SAVED_OPEN_UNAVAILABLE,
        tool.INTERACTION_SAVED_WRITE_FAILURE,
    }
    # X2-s r1 (H4): both saved-views interactions carry input text and are
    # registered on the dispatch table under their own handler.
    for name in (tool.INTERACTION_SAVED_RESTORE_PINNED, tool.INTERACTION_SAVED_OPEN_UNAVAILABLE):
        assert tool.INTERACTION_INPUTS[name], name + " has input text"
        assert name in tool._INTERACTIONS, name + " is registered"
    assert tool._INTERACTIONS[tool.INTERACTION_SAVED_RESTORE_PINNED] is tool._interact_saved_restore_pinned
    assert tool._INTERACTIONS[tool.INTERACTION_SAVED_OPEN_UNAVAILABLE] is tool._interact_saved_open_unavailable
    # X2-s r2 (C3): the write-failure interaction names the browser refusal
    # (QuotaExceededError) in its input text and is registered too.
    assert tool.INTERACTION_INPUTS[tool.INTERACTION_SAVED_WRITE_FAILURE]
    assert "QuotaExceededError" in tool.INTERACTION_INPUTS[tool.INTERACTION_SAVED_WRITE_FAILURE]
    # X2-s r2 (C4): the capture page never enables Save, so the write is driven
    # through Rename on the restored row; the input text says so.
    assert "click Rename" in tool.INTERACTION_INPUTS[tool.INTERACTION_SAVED_WRITE_FAILURE]
    assert "Save this view" not in tool.INTERACTION_INPUTS[tool.INTERACTION_SAVED_WRITE_FAILURE]
    assert tool.SAVED_RENAME_SELECTOR == "#ff-saved-rename"
    assert (
        tool._INTERACTIONS[tool.INTERACTION_SAVED_WRITE_FAILURE]
        is tool._interact_saved_write_failure
    )
    assert not tool.is_interaction_payload(
        {"name": "empty", "kind": "attribute", "value": "", "attribute": "data-empty"}
    )
    assert not tool.is_interaction_payload(None)


def test_saved_write_failure_setitem_patch_is_key_scoped() -> None:
    """X2-s r2 (C3): the write-failure patch refuses ONLY the passed key.

    Hermetic (no browser): the patch is a fixed script string whose refusal
    branch is guarded by ``k === key`` — the argument handed in by the
    interaction — and whose every other write is delegated verbatim to the
    original ``setItem``, so the refusal can never leak to another key.
    """
    patch = tool._SAVED_WRITE_FAILURE_SETITEM_PATCH
    assert patch.startswith("(key) =>")
    assert "Storage.prototype.setItem" in patch
    refuse_at = patch.index("if (k === key)")
    throw_at = patch.index("throw new DOMException")
    delegate_at = patch.index("return original.call(this, k, v)")
    assert refuse_at < throw_at < delegate_at, "the throw sits inside the key guard"
    assert "QuotaExceededError" in patch
    # No other throw site and no concrete key literal: the one refusal names
    # only the key passed in (the stored-bytes reader is key-parameterised
    # too).
    assert patch.count("throw ") == 1
    assert "localStorage" not in patch
    assert tool._SAVED_STORED_BYTES_SCRIPT == "(key) => localStorage.getItem(key)"


def test_page_proxy_reports_applied_only_for_a_verified_interaction() -> None:
    seen: list[tuple[Any, str, str]] = []

    def runner(page: Any, payload: Any, cell: Any) -> dict[str, Any]:
        seen.append((page, payload["value"], cell.cell_id))
        return {"verified": True}

    real, page = _proxy_page(runner)
    assert page.evaluate("FORCE", _interaction_payload("drawer_open")) == {"applied": "drawer_open"}
    # The attribute is never written: the real page saw no evaluate at all.
    assert real.evaluated == []
    assert seen == [(real, "drawer_open", _cell().cell_id)]


@pytest.mark.parametrize(
    "runner",
    [lambda *_: {"verified": False}, lambda *_: None, _raising_runner, None],
    ids=["unverified", "no-receipt", "raises", "no-runner"],
)
def test_page_proxy_fails_closed_on_an_unverified_interaction(runner: Any) -> None:
    real, page = _proxy_page(runner)
    assert page.evaluate("FORCE", _interaction_payload("drawer_trap")) == {"applied": None}
    assert real.evaluated == []


def test_page_proxy_delegates_every_other_evaluate() -> None:
    real, page = _proxy_page(lambda *_: {"verified": True})
    other = {"name": "empty", "kind": "attribute", "value": "", "attribute": "data-empty"}
    page.evaluate("FORCE", other)
    page.evaluate("1 + 1")
    assert real.evaluated == [("FORCE", other), ("1 + 1", None)]


class _ModalShotPage(FakePage):
    def __init__(self, *, modal: Any) -> None:
        super().__init__()
        self.modal = modal
        self.shot_kwargs: list[dict[str, Any]] = []

    def evaluate(self, script: str, arg: Any = None) -> Any:
        self.evaluated.append((script, arg))
        if script == tool._MODAL_OPEN_PROBE_SCRIPT:
            if isinstance(self.modal, Exception):
                raise self.modal
            return self.modal
        return None

    def screenshot(self, **kwargs: Any) -> bytes:
        self.shot_kwargs.append(dict(kwargs))
        return super().screenshot(**kwargs)


def _modal_proxy(modal: Any) -> tuple[_ModalShotPage, Any]:
    real = _ModalShotPage(modal=modal)
    cell = _cell()
    page = tool.PageProxy(
        real,
        fold_recorder=lambda page, cell: None,
        get_cell=lambda: cell,
        interaction_runner=lambda *_: {"verified": True, "facts": {}},
    )
    return real, page


def test_page_proxy_captures_the_viewport_while_an_interaction_modal_is_open() -> None:
    real, page = _modal_proxy(True)
    page.evaluate("FORCE", _interaction_payload("drawer_open"))
    page.screenshot(full_page=True)
    assert real.shot_kwargs == [{"full_page": False}]
    receipt = page._last_receipt[1]
    assert receipt["capture"] == tool.CAPTURE_SCOPE_MODAL_VIEWPORT
    assert receipt["capture"].startswith("viewport: modal open")


@pytest.mark.parametrize("modal", [False, None, {"open": True}, RuntimeError("probe died")])
def test_page_proxy_keeps_the_full_page_shot_unless_the_modal_probe_says_true(modal: Any) -> None:
    real, page = _modal_proxy(modal)
    page.evaluate("FORCE", _interaction_payload("drawer_trap"))
    page.screenshot(full_page=True)
    assert real.shot_kwargs == [{"full_page": True}]
    assert page._last_receipt[1]["capture"] == tool.CAPTURE_SCOPE_FULL_PAGE


def test_page_proxy_never_probes_the_modal_on_a_cell_without_an_interaction() -> None:
    real, page = _modal_proxy(True)
    page.screenshot(full_page=True)
    assert real.shot_kwargs == [{"full_page": True}]
    assert all(script != tool._MODAL_OPEN_PROBE_SCRIPT for script, _ in real.evaluated)


def test_page_proxy_never_carries_a_receipt_into_another_cell() -> None:
    first = _cell()
    second = _cell(theme="light")
    assert first.cell_id != second.cell_id
    real = _ModalShotPage(modal=True)
    current = [first]
    page = tool.PageProxy(
        real,
        fold_recorder=lambda page, cell: None,
        get_cell=lambda: current[0],
        interaction_runner=lambda *_: {"verified": True, "facts": {}},
    )
    page.evaluate("FORCE", _interaction_payload("drawer_open"))
    current[0] = second
    page.screenshot(full_page=True)
    assert real.shot_kwargs == [{"full_page": True}]
    assert "capture" not in page._last_receipt[1]


def test_driver_proxy_plumbs_the_interaction_runner_to_every_page() -> None:
    calls: list[tuple[Any, str, Any]] = []

    def runner(page: Any, payload: Any, cell: Any) -> dict[str, Any]:
        calls.append((page, payload["value"], cell))
        return {"verified": True}

    real_driver = FakeRealDriver(FakeBrowser())
    proxy = tool.DriverProxy(
        real_driver,
        route_handler_factory=lambda: (lambda route, request: None),
        fold_recorder=lambda page, cell: None,
        interaction_runner=runner,
    )
    cell = _cell()
    proxy.capture(url="http://127.0.0.1:4567/fundamental_forensics.html", cell=cell, timeout_s=5)
    page = real_driver._browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
    assert isinstance(page, tool.PageProxy)
    assert page.evaluate("FORCE", _interaction_payload("tab_keys")) == {"applied": "tab_keys"}
    assert len(calls) == 1
    assert isinstance(calls[0][0], FakePage) and calls[0][1] == "tab_keys" and calls[0][2] is cell


def test_run_interaction_drawer_open_is_a_real_click_verified_by_the_dom() -> None:
    page = _ScriptedPage(drawer=[{"open": False}, {"open": True, "modal": True, "focus_inside": True}])
    receipt = tool.run_interaction(page, _interaction_payload("drawer_open"), _cell())
    assert receipt["verified"] is True
    assert page.clicks == [tool.PRIMARY_FINDING_SELECTOR]
    assert receipt["input"] == tool.INTERACTION_INPUTS["drawer_open"]
    assert receipt["cell_id"] == _cell().cell_id
    assert receipt["force_state"] == "drawer_open" and receipt["interaction"] == "drawer_open"
    assert receipt["facts"]["after"]["modal"] is True
    # The pointer leaves the click point so no drawer row is captured hovered.
    assert page.moves == [tool.POINTER_PARK]
    assert receipt["facts"]["pointer_parked"] == list(tool.POINTER_PARK)


def test_run_interaction_drawer_open_unverified_when_the_drawer_stays_shut() -> None:
    page = _ScriptedPage(drawer=[{"open": False}, {"open": False}])
    receipt = tool.run_interaction(page, _interaction_payload("drawer_open"), _cell())
    assert receipt["verified"] is False and "error" not in receipt


def test_run_interaction_tab_keys_requires_selection_to_follow_keyboard_focus() -> None:
    page = _ScriptedPage(
        active=[{"matches": False}, {"matches": True, "tab": "overview"}],
        tablist=[
            {"focus_is_tab": True, "focus_tab": "overview", "selected": ["overview"]},
            {"focus_is_tab": True, "focus_tab": "accounting", "selected": ["accounting"]},
        ],
    )
    receipt = tool.run_interaction(page, _interaction_payload("tab_keys"), _cell())
    assert receipt["verified"] is True
    assert page.keys == ["Tab", "Tab", "ArrowRight"]
    assert page.resets == 1
    assert receipt["facts"]["walk"]["tab_presses"] == 2

    stuck = _ScriptedPage(
        active=[{"matches": True}],
        tablist=[
            {"focus_is_tab": True, "focus_tab": "overview", "selected": ["overview"]},
            {"focus_is_tab": True, "focus_tab": "accounting", "selected": ["overview"]},
        ],
    )
    assert tool.run_interaction(stuck, _interaction_payload("tab_keys"), _cell())["verified"] is False


def test_tab_walk_cap_is_a_recorded_gap() -> None:
    page = _ScriptedPage(active=[{"matches": False}] * 3)
    walk = tool.tab_walk_to(page, tool.SELECTED_TAB_SELECTOR, cap=3)
    assert walk["reached"] is False and walk["tab_presses"] == 3
    assert page.keys == ["Tab"] * 3


def test_run_interaction_drawer_trap_wraps_inside_and_never_escapes() -> None:
    page = _ScriptedPage(
        active=[{"matches": True}],
        drawer=[_trap_probe(0)] + [_trap_probe(index) for index in (1, 2, 0, 1, 2)],
    )
    receipt = tool.run_interaction(page, _interaction_payload("drawer_trap"), _cell())
    assert receipt["verified"] is True
    assert page.keys == ["Tab", "Enter"] + ["Tab"] * 5
    facts = receipt["facts"]
    assert facts["wrapped"] is True and facts["escaped"] == 0
    assert facts["visited"] == 3 and facts["focusable"] == 3
    assert [step["focus_index"] for step in facts["trail"]] == [1, 2, 0, 1, 2]


def test_run_interaction_drawer_trap_escape_is_not_verified() -> None:
    page = _ScriptedPage(
        active=[{"matches": True}],
        drawer=[_trap_probe(0), _trap_probe(1), _trap_probe(2), _trap_probe(None, inside=False)]
        + [_trap_probe(0), _trap_probe(1)],
    )
    receipt = tool.run_interaction(page, _interaction_payload("drawer_trap"), _cell())
    assert receipt["verified"] is False
    assert receipt["facts"]["escaped"] == 1


def test_run_interaction_drawer_trap_needs_the_keyboard_to_open_the_drawer() -> None:
    page = _ScriptedPage(active=[{"matches": True}], drawer=[{"open": False}])
    receipt = tool.run_interaction(page, _interaction_payload("drawer_trap"), _cell())
    assert receipt["verified"] is False
    assert page.keys == ["Tab", "Enter"]


def test_run_interaction_unknown_or_raising_is_a_recorded_gap() -> None:
    unknown = dict(_interaction_payload("drawer_open"), value="bogus")
    receipt = tool.run_interaction(_ScriptedPage(), unknown, _cell())
    assert receipt["verified"] is False and "unknown interaction" in receipt["error"]

    page = _ScriptedPage(drawer=[{"open": False}])
    page.click_error = TimeoutError("no primary finding")
    receipt = tool.run_interaction(page, _interaction_payload("drawer_open"), _cell())
    assert receipt["verified"] is False
    assert receipt["error"].startswith("TimeoutError")


# ---------------------------------------------------------------------------
# A43 Z1 repair: the closed fact, the disabled-controls record, the rest-cell
# receipt kind, and the gates that keep keyboard interactions.json at 24 rows.
# ---------------------------------------------------------------------------


def test_fold_closed_into_verified_loses_a_lost_focus_restore() -> None:
    receipt = {"verified": True, "facts": {"wrapped": True, "escaped": 0}}
    tool.fold_closed_into_verified(
        receipt,
        {
            "open": True,
            "modal": True,
            "focus_restored": False,
            "focus_matches_trigger": False,
            "focus_on_finding_button": False,
            "focus_id": None,
            "focus_tag": "body",
        },
    )
    assert receipt["verified"] is False
    assert receipt["facts"]["closed"]["focus_restored"] is False


def test_fold_closed_into_verified_is_fail_closed_only() -> None:
    # The measured product behavior: focus lands on the selected finding's
    # button (openAnalysisDrawer -> selectedEvidenceButton()), not the CTA.
    restored = {
        "open": False,
        "focus_restored": True,
        "focus_matches_trigger": False,
        "focus_on_finding_button": True,
        "focus_id": None,
        "focus_tag": "button",
    }
    kept = {"verified": True, "facts": {}}
    tool.fold_closed_into_verified(kept, restored)
    assert kept["verified"] is True
    # A restored close never un-fails a receipt whose trap already failed.
    failed = {"verified": False, "facts": {}}
    tool.fold_closed_into_verified(failed, restored)
    assert failed["verified"] is False


class _CloseProbePage(FakePage):
    """Answers the closed probe; records key presses, waits, and shots."""

    def __init__(self, answer: Any) -> None:
        super().__init__()
        self.answer = answer
        self.seen_config: Any = None
        self.pressed: list[str] = []
        self.waits: list[int] = []
        self.keyboard = types.SimpleNamespace(press=self.pressed.append)

    def wait_for_timeout(self, ms: int) -> None:
        self.waits.append(ms)

    def evaluate(self, script: str, arg: Any = None) -> Any:
        self.evaluated.append((script, arg))
        if script == tool._DRAWER_CLOSED_PROBE_SCRIPT.strip():
            self.seen_config = arg
            return self.answer
        return None


def test_close_drawer_and_probe_restore_presses_escape_then_settles() -> None:
    page = _CloseProbePage(
        {"open": False, "modal": False, "focus_restored": True, "focus_matches_trigger": False, "focus_on_finding_button": True, "focus_id": None, "focus_tag": "button"}
    )
    closed = tool.close_drawer_and_probe_restore(page)
    assert closed["focus_restored"] is True and closed["open"] is False
    assert page.pressed == ["Escape"]
    assert page.waits == [tool.INTERACTION_SETTLE_MS]
    assert page.seen_config == {
        "evidence": tool.EVIDENCE_SELECTOR,
        "trigger": tool.PRIMARY_FINDING_SELECTOR,
    }


def _disabled_entries(locale: str) -> list[dict[str, Any]]:
    labels = {
        "en": ("Export unavailable", "Save this view"),
        "zh": ("导出不可用", "保存当前视图"),
    }
    tips = {
        "en": "Export is unavailable until this issuer, cutoff and policy can be queried.",
        "zh": "在可查询该发行人、截止日和策略之前，导出不可用。",
    }
    return [
        {
            "selector": selector,
            "present": True,
            "disabled": True,
            "visible_text": text,
            "label_en": "Export unavailable" if selector == "#ff-export-btn" else "Save this view",
            "label_zh": "导出不可用" if selector == "#ff-export-btn" else "保存当前视图",
            "tip": tips[locale],
            "aria_disabled": None,
        }
        for selector, text in zip(tool.DISABLED_CONTROL_SELECTORS, labels[locale])
    ]


class _DisabledProbePage(FakePage):
    def __init__(self, answer: Any) -> None:
        super().__init__()
        self.answer = answer
        self.seen_config: Any = None

    def evaluate(self, script: str, arg: Any = None) -> Any:
        self.evaluated.append((script, arg))
        if script == tool._DISABLED_CONTROLS_SCRIPT.strip():
            self.seen_config = arg
            return self.answer
        return None


@pytest.mark.parametrize("locale", ["en", "zh"])
def test_disabled_controls_record_shape_and_locale_selection(locale: str) -> None:
    page = _DisabledProbePage(_disabled_entries(locale))
    entries = tool.probe_disabled_controls(page, locale)
    assert page.seen_config == {
        "selectors": list(tool.DISABLED_CONTROL_SELECTORS),
        "locale": locale,
    }
    assert [entry["selector"] for entry in entries] == list(tool.DISABLED_CONTROL_SELECTORS)
    for entry in entries:
        assert set(entry) == {
            "selector",
            "present",
            "disabled",
            "visible_text",
            "label_en",
            "label_zh",
            "tip",
            "aria_disabled",
        }
    receipt = tool.record_disabled_controls(page, _cell(locale=locale))
    assert receipt["interaction"] == "disabled_controls"
    assert receipt["force_state"] is None
    assert receipt["verified"] is True
    assert receipt["input"] is tool.DISABLED_CONTROLS_PROBE_INPUT
    assert receipt["facts"]["controls"] == entries
    assert receipt["cell_id"] == _cell(locale=locale).cell_id


def test_disabled_controls_receipt_unverified_when_a_control_is_not_disabled() -> None:
    entries = _disabled_entries("en")
    entries[0]["disabled"] = False
    receipt = tool.record_disabled_controls(_DisabledProbePage(entries), _cell())
    assert receipt["verified"] is False

    gone = [entry for entry in _disabled_entries("en") if entry["selector"] != "#ff-saved-save"]
    receipt = tool.record_disabled_controls(_DisabledProbePage(gone), _cell())
    assert receipt["verified"] is False


def test_disabled_controls_probe_failure_is_a_recorded_gap() -> None:
    class _Broken:
        def evaluate(self, script: str, arg: Any = None) -> Any:
            raise RuntimeError("page gone")

    receipt = tool.record_disabled_controls(_Broken(), _cell())
    assert receipt["verified"] is False
    assert receipt["error"].startswith("RuntimeError")
    assert receipt["facts"]["controls"] == []


def test_rest_disabled_controls_probe_gate() -> None:
    assert (
        tool.rest_disabled_controls_probe_wanted(
            "populated",
            [
                "drawer_open:[data-ff-evidence-interaction=drawer_open]",
                "source_hover:hover(.ff-source-control)",
            ],
        )
        is True
    )
    for keyboard_force in (
        "tab_keys:[data-ff-evidence-interaction=tab_keys]",
        "drawer_trap:[data-ff-evidence-interaction=drawer_trap]",
    ):
        assert tool.rest_disabled_controls_probe_wanted("populated", [keyboard_force]) is False
    for mode in ("anonymous", "unavailable", "degraded"):
        assert tool.rest_disabled_controls_probe_wanted(mode, []) is False


def test_keyboard_receipts_carry_the_none_state_disabled_controls() -> None:
    entries = _disabled_entries("en")
    page = _ScriptedPage(
        active=[{"matches": True}],
        tablist=[
            {"focus_is_tab": True, "focus_tab": "overview", "selected": ["overview"]},
            {"focus_is_tab": True, "focus_tab": "accounting", "selected": ["accounting"]},
        ],
    )
    page.disabled_answers = entries
    receipt = tool.run_interaction(page, _interaction_payload("tab_keys"), _cell())
    assert receipt["verified"] is True
    assert receipt["facts"]["disabled_controls"] == entries
    # The probe ran BEFORE the walk moved focus (it was the first evaluate).
    assert page.disabled_probe_at == 1


def test_page_proxy_runs_the_rest_probe_on_rest_cells_only() -> None:
    probed: list[Any] = []
    rest_cell = _cell()
    forced_cell = _cell(force_state=types.SimpleNamespace(name="drawer_open"))
    current = {"cell": rest_cell}
    page = tool.PageProxy(
        FakePage(),
        fold_recorder=lambda page, cell: None,
        get_cell=lambda: current["cell"],
        rest_probe=lambda page_, cell_: probed.append(cell_),
    )
    page.screenshot(full_page=True)
    assert probed == [rest_cell]
    current["cell"] = forced_cell
    page.screenshot(full_page=True)
    assert probed == [rest_cell], "a forced cell never produces a disabled_controls receipt"


class _TrapShotPage(_CloseProbePage):
    """Records the shot/Escape order for the drawer_trap post-shot close."""

    def __init__(self, answer: Any) -> None:
        super().__init__(answer)
        self.events: list[str] = []

    def screenshot(self, **kwargs: Any) -> bytes:
        self.events.append("shot")
        return super().screenshot(**kwargs)


def _trap_proxy(closed_answer: Any) -> tuple[_TrapShotPage, Any]:
    real = _TrapShotPage(closed_answer)
    cell = _cell()
    page = tool.PageProxy(
        real,
        fold_recorder=lambda page, cell: None,
        get_cell=lambda: cell,
        interaction_runner=lambda *_args, **_kwargs: {
            "cell_id": cell.cell_id,
            "interaction": "drawer_trap",
            "verified": True,
            "facts": {},
        },
    )
    return real, page


def test_page_proxy_closes_the_drawer_after_the_drawer_trap_shot() -> None:
    real, page = _trap_proxy(
        {"open": False, "modal": False, "focus_restored": True, "focus_matches_trigger": False, "focus_on_finding_button": True, "focus_id": None, "focus_tag": "button"}
    )
    page.evaluate("FORCE", _interaction_payload("drawer_trap"))
    assert page.screenshot(full_page=True) == b"png-bytes"
    # The shot happened FIRST — it must still show the open, trapped drawer.
    assert real.events == ["shot"]
    assert real.pressed == ["Escape"]
    receipt = page._last_receipt[1]
    assert receipt["facts"]["closed"]["focus_restored"] is True
    assert receipt["verified"] is True


def test_page_proxy_a_failed_focus_restore_voids_the_trap_receipt() -> None:
    real, page = _trap_proxy(
        {"open": True, "modal": True, "focus_restored": False, "focus_matches_trigger": False, "focus_on_finding_button": False, "focus_id": "ff-evidence-close", "focus_tag": "button"}
    )
    page.evaluate("FORCE", _interaction_payload("drawer_trap"))
    page.screenshot(full_page=True)
    receipt = page._last_receipt[1]
    assert receipt["facts"]["closed"]["focus_restored"] is False
    assert receipt["verified"] is False


def test_page_proxy_a_probe_failure_fails_closed_without_killing_the_shot() -> None:
    class _NoKeyboardPage(FakePage):
        pass

    real = _NoKeyboardPage()
    cell = _cell()
    page = tool.PageProxy(
        real,
        fold_recorder=lambda page, cell: None,
        get_cell=lambda: cell,
        interaction_runner=lambda *_args, **_kwargs: {
            "cell_id": cell.cell_id,
            "interaction": "drawer_trap",
            "verified": True,
            "facts": {},
        },
    )
    page.evaluate("FORCE", _interaction_payload("drawer_trap"))
    assert page.screenshot(full_page=True) == b"png-bytes"
    receipt = page._last_receipt[1]
    assert receipt["verified"] is False
    assert "probe_error" in receipt["facts"]["closed"]
    assert receipt["facts"]["closed"]["focus_restored"] is False


def test_page_proxy_skips_the_close_on_every_other_interaction() -> None:
    real = _TrapShotPage(None)
    cell = _cell()
    page = tool.PageProxy(
        real,
        fold_recorder=lambda page, cell: None,
        get_cell=lambda: cell,
        interaction_runner=lambda *_args, **_kwargs: {
            "cell_id": cell.cell_id,
            "interaction": "drawer_open",
            "verified": True,
            "facts": {},
        },
    )
    page.evaluate("FORCE", _interaction_payload("drawer_open"))
    page.screenshot(full_page=True)
    assert real.pressed == []
    assert "closed" not in page._last_receipt[1]["facts"]


# ---------------------------------------------------------------------------
# manifest post-process: entitled modes + per-state access
# ---------------------------------------------------------------------------


def _postprocess(mode: str, **kwargs: Any) -> dict[str, Any]:
    manifest = _fake_manifest()
    manifest["pages"][0]["metrics"] = {"measured_in": {"viewport": "desktop", "access": "anonymous"}}
    kwargs.setdefault("state_receipt", None)
    tool.postprocess_manifest(
        manifest,
        mode=mode,
        generator_command=f"python3 -m tests.tools.fif_p2_evidence_capture --mode {mode}",
        wrapper_module_sha256="e" * 64,
        scrubbed_env_names=[],
        aborted_hosts=[],
        **kwargs,
    )
    return manifest


def _receipt() -> Any:
    return tool.KernelStateReceipt(
        generated_at="2026-10-01T00:00:00Z",
        sha256="c" * 64,
        bytes=4321,
        input_symlinks=tool.KERNEL_INPUTS,
        state_path=None,
    )


def test_manifest_postprocess_entitled_modes_correct_the_per_state_access() -> None:
    manifest = _postprocess(tool.MODE_POPULATED, state_receipt=_receipt())
    states = manifest["pages"][0]["states"]
    assert {row["access"] for row in states} == {tool.POPULATED_ACCESS}
    assert manifest["pages"][0]["metrics"]["measured_in"]["access"] == tool.POPULATED_ACCESS
    assert manifest["honesty"]["cell_id_access"] == tool.CELL_ID_ACCESS_NOTE
    source = manifest["evidence_source"]
    assert "interactions" not in source and "mode_verification" not in source
    assert "delivery" not in source["state"]


def test_manifest_postprocess_anonymous_keeps_the_capture_tool_access() -> None:
    manifest = _postprocess(tool.MODE_ANONYMOUS)
    assert all("access" not in row for row in manifest["pages"][0]["states"])
    assert manifest["pages"][0]["metrics"]["measured_in"]["access"] == "anonymous"
    assert "cell_id_access" not in manifest["honesty"]


def test_manifest_postprocess_unavailable() -> None:
    verification = {"routes": {"state_status": 503, "health_state": "unavailable"}}
    manifest = _postprocess(tool.MODE_UNAVAILABLE, mode_verification=verification)
    states = manifest["pages"][0]["states"]
    assert all(row["evidence_label"] == tool.UNAVAILABLE_LABEL for row in states)
    assert {row["access"] for row in states} == {tool.UNAVAILABLE_ACCESS}
    assert manifest["axes"]["access"] == [tool.UNAVAILABLE_ACCESS]
    assert manifest["honesty"]["access"] == tool.UNAVAILABLE_HONESTY
    assert manifest["honesty"]["entitlement"] == tool.ENTITLED_CROPS_FENCE
    source = manifest["evidence_source"]
    assert source["mode"] == tool.MODE_UNAVAILABLE and source["label"] == tool.UNAVAILABLE_LABEL
    assert source["entitlement"] == tool.POPULATED_ENTITLEMENT
    assert source["entitlement_fence"] == tool.ENTITLED_CROPS_FENCE
    assert source["mode_verification"] == verification
    assert "state" not in source


def test_manifest_postprocess_degraded_names_the_last_good_delivery() -> None:
    manifest = _postprocess(
        tool.MODE_DEGRADED,
        state_receipt=_receipt(),
        interactions="interactions.json",
        mode_verification={"routes": {"health_state": "degraded"}},
    )
    source = manifest["evidence_source"]
    assert manifest["axes"]["access"] == [tool.DEGRADED_ACCESS]
    assert manifest["honesty"]["access"] == tool.DEGRADED_HONESTY
    assert source["state"]["delivery"] == tool.DEGRADED_STATE_DELIVERY
    assert source["state"]["sha256"] == "c" * 64
    assert source["interactions"] == "interactions.json"
    assert source["label"] == tool.DEGRADED_LABEL


# ---------------------------------------------------------------------------
# unavailable / degraded: set-aside, real loader prime, real routes
# ---------------------------------------------------------------------------


def _install_local_state(root: Path, blob: bytes = b"state-bytes") -> Path:
    path = root / tool.LOCAL_STATE_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(blob)
    return path


def _stale_state_blob() -> bytes:
    document = {
        "schema": "fundamental_forensics_state.v1",
        "generated_at": "2020-01-01T00:00:00Z",
        "companies": {"AAPL": {"ticker": "AAPL", "findings": []}},
    }
    return gzip.compress(
        json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        mtime=0,
    )


@pytest.fixture
def isolated_loader(monkeypatch):
    for name in list(os.environ):
        if name.startswith(tool.SCRUB_ENV_PREFIXES) or name in tool.SCRUB_ENV_NAMES:
            monkeypatch.delenv(name, raising=False)
    tool.clear_private_state_cache()
    yield
    tool.clear_private_state_cache()


def test_local_state_set_aside_restores_the_object(tmp_path: Path) -> None:
    path = _install_local_state(tmp_path)
    with tool.local_state_set_aside(tmp_path) as facts:
        assert not path.exists()
        assert facts == {"set_aside": True, "sha256": hashlib.sha256(b"state-bytes").hexdigest()}
        holding = [p for p in path.parent.iterdir() if p.name.startswith(".fif-evidence-setaside-")]
        assert len(holding) == 1
    assert path.read_bytes() == b"state-bytes"
    assert [p.name for p in path.parent.iterdir()] == [path.name]


def test_local_state_set_aside_restores_on_error(tmp_path: Path) -> None:
    path = _install_local_state(tmp_path)
    with pytest.raises(RuntimeError):
        with tool.local_state_set_aside(tmp_path):
            raise RuntimeError("capture failed")
    assert path.read_bytes() == b"state-bytes"
    assert [p.name for p in path.parent.iterdir()] == [path.name]


def test_local_state_set_aside_refuses_a_symlink(tmp_path: Path) -> None:
    target = tmp_path / "elsewhere.gz"
    target.write_bytes(b"x")
    path = tmp_path / tool.LOCAL_STATE_RELATIVE
    path.parent.mkdir(parents=True)
    path.symlink_to(target)
    with pytest.raises(tool.FifEvidenceError):
        with tool.local_state_set_aside(tmp_path):
            pass
    assert path.is_symlink() and target.read_bytes() == b"x"


def test_local_state_set_aside_absent_is_a_recorded_fact(tmp_path: Path) -> None:
    with tool.local_state_set_aside(tmp_path) as facts:
        assert facts == {"set_aside": False, "sha256": None}


def test_prime_last_good_state_drives_the_real_loader(isolated_loader, tmp_path: Path) -> None:
    from engine.fundamental_forensics import private_state

    blob = _stale_state_blob()
    facts = tool.prime_last_good_state(tmp_path, blob)
    assert facts["primed_origin"] == private_state.ORIGIN_R2
    assert facts["served_origin"] == private_state.ORIGIN_LAST_GOOD
    assert facts["sha256"] == hashlib.sha256(blob).hexdigest()
    assert "RESEARCH_LOCAL_STORE" not in os.environ
    again = private_state.load_state_record(tmp_path)
    assert again.origin == private_state.ORIGIN_LAST_GOOD and again.blob == blob


def test_prime_last_good_state_refuses_unusable_inputs(isolated_loader, tmp_path: Path) -> None:
    with pytest.raises(tool.FifEvidenceError):
        tool.prime_last_good_state(tmp_path, b"")
    _install_local_state(tmp_path)
    with pytest.raises(tool.FifEvidenceError):
        tool.prime_last_good_state(tmp_path, _stale_state_blob())
    assert "RESEARCH_LOCAL_STORE" not in os.environ


def test_verify_real_state_unavailable_reads_the_real_routes(
    isolated_loader, monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(forensics_api, "REPO", tmp_path)
    facts = tool.verify_real_state_unavailable(_populated_client())
    assert facts["state_status"] == 503 and facts["health_status"] == 200
    assert facts["health_state"] == "unavailable"
    assert facts["health_reason_code"] == "STATE_MISSING"


def test_verify_real_state_unavailable_refuses_a_served_state(
    isolated_loader, monkeypatch, tmp_path: Path
) -> None:
    _install_local_state(tmp_path, _state_blob())
    monkeypatch.setattr(forensics_api, "REPO", tmp_path)
    with pytest.raises(tool.ModeUnavailable):
        tool.verify_real_state_unavailable(_populated_client())


def test_verify_real_degraded_health_reads_the_real_routes(
    isolated_loader, monkeypatch, tmp_path: Path
) -> None:
    blob = _stale_state_blob()
    tool.prime_last_good_state(tmp_path, blob)
    monkeypatch.setattr(forensics_api, "REPO", tmp_path)
    client = _populated_client()
    facts = tool.verify_real_degraded_health(client, expected_sha256=hashlib.sha256(blob).hexdigest())
    assert facts["state_status"] == 200
    assert facts["health_state"] == "degraded"
    assert facts["health_reason_code"] == "LAST_GOOD_STALE"
    assert facts["private_object_origin"] == "last_good"
    assert facts["age_seconds"] > tool.FRESHNESS_BUDGET_SECONDS
    with pytest.raises(tool.ModeUnavailable):
        tool.verify_real_degraded_health(client, expected_sha256="0" * 64)


@pytest.mark.data_gate
def test_kernel_build_without_install_leaves_the_tree_untouched() -> None:
    local = ROOT / tool.LOCAL_STATE_RELATIVE
    before = local.read_bytes() if local.exists() else None
    receipt = tool.build_kernel_state(ROOT, generated_at="2026-10-01T00:00:00Z", install=False)
    assert receipt.state_path is None
    assert receipt.blob and receipt.sha256 == hashlib.sha256(receipt.blob).hexdigest()
    assert receipt.bytes == len(receipt.blob)
    after = local.read_bytes() if local.exists() else None
    assert after == before


def test_freshness_budget_matches_the_engine() -> None:
    from engine.fundamental_forensics.health import FRESHNESS_BUDGET_SECONDS

    assert tool.FRESHNESS_BUDGET_SECONDS == FRESHNESS_BUDGET_SECONDS


def test_degraded_clock_problem() -> None:
    now = datetime(2026, 10, 12, tzinfo=timezone.utc)
    assert tool.degraded_clock_problem("2026-10-01T00:00:00Z", now=now) is None
    assert tool.degraded_clock_problem("2026-10-01T00:00:00", now=now) is None
    assert "older than" in tool.degraded_clock_problem("2026-10-11T00:00:00Z", now=now)
    assert "ISO-8601" in tool.degraded_clock_problem("yesterday", now=now)
    assert "required" in tool.degraded_clock_problem(None, now=now)


def test_cli_offers_exactly_the_four_modes() -> None:
    parser = tool.build_parser()
    for mode in tool.ALL_MODES:
        assert parser.parse_args(["--mode", mode, "--out-dir", "x"]).mode == mode
    with pytest.raises(SystemExit):
        parser.parse_args(["--mode", "bogus", "--out-dir", "x"])


def test_degraded_needs_a_stale_kernel_clock_before_any_capture(monkeypatch, tmp_path: Path) -> None:
    calls = _forbid_any_capture(monkeypatch)
    out_dir = tmp_path / "out"
    assert tool.main(["--mode", tool.MODE_DEGRADED, "--out-dir", str(out_dir)]) == tool.EXIT_USAGE
    fresh = datetime.now(timezone.utc).isoformat()
    rc = tool.main(["--mode", tool.MODE_DEGRADED, "--out-dir", str(out_dir), "--generated-at", fresh])
    assert rc == tool.EXIT_USAGE
    assert calls == []
    assert not out_dir.exists()


# ---------------------------------------------------------------------------
# briefcase seed (X2-s r1, H1/H4) — hermetic, no browser
# ---------------------------------------------------------------------------

_EVIDENCE_SEED = (
    ROOT / "tests" / "fixtures" / "fundamental_forensics" / "fif_saved_research"
    / "evidence_briefcase_seed.json"
)


def test_briefcase_seed_init_script_writes_only_that_one_key() -> None:
    raw = _EVIDENCE_SEED.read_text(encoding="utf-8")
    info = tool.resolve_briefcase_seed(str(_EVIDENCE_SEED), ROOT)
    expected = (
        '(()=>{try{window.localStorage.setItem("' + tool.BRIEFCASE_STORAGE_KEY + '", '
        + json.dumps(raw) + ')}catch(e){}})();'
    )
    assert info["init_script"] == expected
    assert info["init_script"].count("setItem") == 1, "exactly one write"
    assert "removeItem" not in info["init_script"]
    assert ".clear(" not in info["init_script"]
    # The embedded literal decodes back to the exact fixture bytes, and the
    # script ends exactly as frozen.
    decoder = json.JSONDecoder()
    payload_start = info["init_script"].index(", ") + 2
    literal, consumed = decoder.raw_decode(info["init_script"][payload_start:])
    assert literal == raw
    assert info["init_script"][payload_start + consumed :] == ")}catch(e){}})();"


def test_briefcase_seed_refuses_paths_outside_fixtures_and_non_objects(tmp_path: Path) -> None:
    outside = tmp_path / "seed.json"
    outside.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="tests/fixtures"):
        tool.resolve_briefcase_seed(str(outside), ROOT)

    fixtures_tmp = tmp_path / "tests" / "fixtures"
    fixtures_tmp.mkdir(parents=True)
    not_object = fixtures_tmp / "seed.json"
    not_object.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON object"):
        tool.resolve_briefcase_seed(str(not_object), tmp_path)
    unparseable = fixtures_tmp / "broken.json"
    unparseable.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="parseable JSON"):
        tool.resolve_briefcase_seed(str(unparseable), tmp_path)


def test_main_refuses_a_bad_briefcase_seed_with_exit_usage_before_any_capture(
    monkeypatch, tmp_path: Path
) -> None:
    calls = _forbid_any_capture(monkeypatch)
    outside = tmp_path / "seed.json"
    outside.write_text("{}", encoding="utf-8")
    out_dir = tmp_path / "out"
    assert (
        tool.main(
            [
                "--mode", tool.MODE_ANONYMOUS,
                "--out-dir", str(out_dir),
                "--briefcase-seed", str(outside),
            ]
        )
        == tool.EXIT_USAGE
    )
    fixtures_tmp = tmp_path / "tests" / "fixtures"
    fixtures_tmp.mkdir(parents=True)
    not_object = fixtures_tmp / "seed.json"
    not_object.write_text('"just a string"', encoding="utf-8")
    assert (
        tool.main(
            [
                "--mode", tool.MODE_ANONYMOUS,
                "--out-dir", str(out_dir),
                "--briefcase-seed", str(not_object),
            ]
        )
        == tool.EXIT_USAGE
    )
    assert calls == [], "no browser/kernel work ran for a refused seed"
    assert not out_dir.exists()


def test_briefcase_seed_sidecar_shape_and_manifest_reference() -> None:
    info = tool.resolve_briefcase_seed(str(_EVIDENCE_SEED), ROOT)
    assert set(info) == {"path", "sha256", "storage_key", "init_script"}
    assert info["path"] == (
        "tests/fixtures/fundamental_forensics/fif_saved_research/evidence_briefcase_seed.json"
    )
    assert info["sha256"] == hashlib.sha256(_EVIDENCE_SEED.read_bytes()).hexdigest()
    assert info["storage_key"] == tool.BRIEFCASE_STORAGE_KEY

    manifest: dict[str, Any] = {"pages": []}
    tool.postprocess_manifest(
        manifest,
        mode=tool.MODE_ANONYMOUS,
        generator_command="cmd",
        wrapper_module_sha256="0" * 64,
        scrubbed_env_names=(),
        aborted_hosts=(),
        state_receipt=None,
        briefcase_seed="briefcase_seed.json",
    )
    assert manifest["evidence_source"]["briefcase_seed"] == "briefcase_seed.json"

    without: dict[str, Any] = {"pages": []}
    tool.postprocess_manifest(
        without,
        mode=tool.MODE_ANONYMOUS,
        generator_command="cmd",
        wrapper_module_sha256="0" * 64,
        scrubbed_env_names=(),
        aborted_hosts=(),
        state_receipt=None,
    )
    assert "briefcase_seed" not in without["evidence_source"], "no flag, no reference"


# ---------------------------------------------------------------------------
# A0-SE SAFE-ENV production-capture hook (--dataset-store / --state-store)
# ---------------------------------------------------------------------------


def test_production_capture_flags_parse_and_default_off() -> None:
    parser = tool.build_parser()
    plain = parser.parse_args(["--mode", tool.MODE_POPULATED, "--out-dir", "x"])
    assert plain.dataset_store is None
    assert plain.state_store is None
    hooked = parser.parse_args(
        [
            "--mode", tool.MODE_POPULATED, "--out-dir", "x",
            "--dataset-store", "/tmp/ds", "--state-store", "/tmp/ss",
        ]
    )
    assert hooked.dataset_store == "/tmp/ds"
    assert hooked.state_store == "/tmp/ss"


def test_install_state_into_local_store_writes_the_loaders_key(
    tmp_path: Path
) -> None:
    from engine.fundamental_forensics import private_state
    from engine.research_vault.r2_store import LocalStore

    blob = gzip.compress(b'{"schema": "fundamental_forensics.state/v1"}')
    served = tool.install_state_into_local_store(tmp_path, blob)
    assert served == tmp_path / private_state.STATE_KEY
    # The exact store adapter the loader's RESEARCH_LOCAL_STORE path uses
    # reads the object back at the same key, byte for byte.
    assert LocalStore(tmp_path).get_bytes(private_state.STATE_KEY) == blob


def test_production_capture_flags_do_not_bypass_the_render_guard(
    monkeypatch, tmp_path: Path
) -> None:
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "fundamental_forensics.html").write_text(
        "<html><body>stale, no ff ids</body></html>", encoding="utf-8"
    )
    _forbid_browser(monkeypatch)
    rc = tool.main(
        [
            "--mode", tool.MODE_POPULATED,
            "--out-dir", str(tmp_path / "out"),
            "--generated-at", "2026-10-13T02:05:00Z",
            "--site-dir", str(site_dir),
            "--dataset-store", str(tmp_path / "ds"),
            "--state-store", str(tmp_path / "ss"),
        ]
    )
    assert rc == tool.EXIT_STALE_PAGE
    assert not (tmp_path / "out").exists()
