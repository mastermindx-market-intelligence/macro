"""Browser-free unit tests for the FIF P2 fixture-backed evidence wrapper.

No browser, no network. The route handler is exercised directly with fake
route/request objects; the router behind it is the REAL ``app.forensics.router``
in-process. The only monkeypatch anywhere in this file is the state-blob source
for the GET /api/forensics/state forwarding test (the kernel state itself is
built for real from the tree's five parquet inputs in the temp-root tests).
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import subprocess
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
        changed_paths=["site/fundamental_forensics.js", "site/fundamental_forensics.css"],
        manifest_relative="out/manifest.json",
    )
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert set(loaded) == {"schema", "changed_paths", "manifest"}
    assert loaded["schema"] == "mastermind.page_evidence_receipt.v1"
    assert loaded["changed_paths"] == [
        "site/fundamental_forensics.js",
        "site/fundamental_forensics.css",
    ]
    assert loaded["manifest"] == "out/manifest.json"


# ---------------------------------------------------------------------------
# kernel temp-root build: the five inputs, nothing writes through
# ---------------------------------------------------------------------------


def test_prepare_kernel_temp_root_symlinks_exactly_five_inputs(tmp_path: Path) -> None:
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
