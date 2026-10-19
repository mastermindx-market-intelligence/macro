"""V0 serving bench (SPEC_V0 §1): one declared corpus, measured load, no fan-out.

The bench MEASURES the existing served paths and writes ONE JSON record.  It
adds no queue, monitor, scheduler, daemon, cache or new source plane: the
corpus is one state bundle built by the existing builders, the load is N
concurrent ``TestClient`` threads over four served routes, and every refusal
the routes already define is recorded as the route answered it.

Modes
-----
``--fixture`` builds the small in-test corpus the U1a state-API suite uses
(``tests.test_capital_structure_state_api`` fixture helpers, imported by name —
never copied); ``--data-root <dir>`` copies a committed capital-structure data
directory into a fresh temp dir and builds the state bundle over the COPY with
the existing ``scripts.build_capital_structure_state.build_from_disk``.  The
repository's ``data/`` tree is never written; the temp dir is removed at exit.

Percentiles
-----------
Latency is measurement, not a capital-structure number.  Every duration is a
``time.perf_counter_ns()`` integer; percentiles use the exact integer
nearest-rank method: for ``n`` sorted samples and percentile ``p``,
``index = (p * n + 99) // 100 - 1`` (ceil(p·n/100), one-based, minus one), so
no binary approximation ever enters the reported numbers.  Reported latencies
are integer microseconds (integer division of the nanosecond deltas).

Proposals, never thresholds
---------------------------
The masterplan's p95 numbers (cached dossier p95 ≤ 1 s, bounded scenario
evaluation p95 ≤ 2 s at 10 concurrent readers) are PROPOSALS.  The record
reports the measured warm value against them with ``pass``/``miss``; it never
edits a threshold and CI never asserts a timing.

No request-time fan-out
-----------------------
Before any request the bench installs a socket guard that makes every outbound
``socket.socket.connect`` / ``connect_ex`` / ``socket.create_connection`` raise
and counts the attempts, and diffs ``sys.modules`` for model/LLM client modules
around the ``app.capital_structure`` import.  Both are recorded; zero is
expected.

Branch bound
------------
One evaluate request whose exclusive choices exceed
``engine.capital_structure.capacity_joint.MAX_BRANCHES`` must meet the typed
refusal, never a silent approximation.  No fixture on this base can exceed
4096 exclusive-choice branches through the API, so the bench monkeypatches
``MAX_BRANCHES`` for that ONE request only (the production constant is never
edited) and records ``branch_bound_probe.monkeypatched_limit``; the kernel's
own refusal shape (``capacity_joint`` lines 302-309) is recorded alongside
what the served body actually carried.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import platform
import shutil
import socket
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, NamedTuple

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

RECORD_SCHEMA: dict[str, type] = {
    "schema": str,
    "wall_clock_utc": str,
    "mode": str,
    "hardware": dict,
    "corpus": dict,
    "load": dict,
    "proposal_targets": dict,
    "source_age": dict,
    "no_request_time_fan_out": dict,
    "branch_bound_probe": dict,
}

#: The one record schema name this bench writes.
RECORD_SCHEMA_NAME = "capital_structure.v0_serving_bench.v1"

#: The model/LLM client root modules the no-import check watches (SPEC_V0 §1).
_LLM_CLIENT_ROOTS = ("anthropic", "openai", "litellm", "google.generativeai")

_PREFIX = "/api/capital-structure/v1"
_BENCH_USER = {"id": "paid-user"}

#: The proposal targets, verbatim from SPEC_V0 §1, in integer microseconds.
_PROPOSAL_CACHED_DOSSIER_P95_US = 1_000_000
_PROPOSAL_BOUND_EVALUATE_P95_US = 2_000_000
_PROPOSAL_STATED_READERS = 10

_ROUTES = ("state", "registration", "coverage", "evaluate")


# ---------------------------------------------------------------------------
# Exact integer percentiles (the docstring's nearest-rank method)
# ---------------------------------------------------------------------------


def nearest_rank(sorted_durations_ns: list[int], percentile: int) -> int:
    """Exact integer nearest-rank percentile of sorted nanosecond integers.

    ``index = (p * n + 99) // 100 - 1`` is ceil(p·n/100) one-based, minus one:
    the smallest value covering at least p percent of the samples.  Integer
    arithmetic only, so the reported number is exact.
    """
    if not sorted_durations_ns:
        raise ValueError("nearest_rank: no samples")
    if not 1 <= percentile <= 100:
        raise ValueError("nearest_rank: percentile out of range")
    index = (percentile * len(sorted_durations_ns) + 99) // 100 - 1
    return sorted_durations_ns[index]


def _route_latency_block(durations_ns: list[int], statuses: list[int]) -> dict[str, Any]:
    """One route's measured block: counts, status counts, integer-µs percentiles."""
    ordered = sorted(durations_ns)
    status_counts: dict[str, int] = {}
    for status in statuses:
        status_counts[str(status)] = status_counts.get(str(status), 0) + 1
    return {
        "request_count": len(ordered),
        "status_counts": status_counts,
        "p50_us": nearest_rank(ordered, 50) // 1_000,
        "p95_us": nearest_rank(ordered, 95) // 1_000,
        "max_us": ordered[-1] // 1_000,
    }


# ---------------------------------------------------------------------------
# The socket guard and the LLM import probe (no request-time fan-out)
# ---------------------------------------------------------------------------


class _SocketGuard:
    """Makes every outbound connect raise and counts the attempts.

    Installed before any request and restored afterwards; the counter is
    shared by every reader thread, so concurrent waves are all covered.
    """

    def __init__(self) -> None:
        self.attempts = 0
        self._saved: dict[str, Any] = {}

    def install(self) -> None:
        guard = self

        def refused_connect(sock: socket.socket, address: Any) -> None:
            guard.attempts += 1
            raise AssertionError(
                f"outbound socket connect attempted during the V0 bench: {address!r}"
            )

        def refused_connect_ex(sock: socket.socket, address: Any) -> int:
            guard.attempts += 1
            raise AssertionError(
                f"outbound socket connect_ex attempted during the V0 bench: {address!r}"
            )

        def refused_create_connection(address: Any, *args: Any, **kwargs: Any) -> Any:
            guard.attempts += 1
            raise AssertionError(
                "outbound socket.create_connection attempted during the V0 bench: "
                f"{address!r}"
            )

        self._saved = {
            "connect": socket.socket.connect,
            "connect_ex": socket.socket.connect_ex,
            "create_connection": socket.create_connection,
        }
        socket.socket.connect = refused_connect  # type: ignore[method-assign]
        socket.socket.connect_ex = refused_connect_ex  # type: ignore[method-assign]
        socket.create_connection = refused_create_connection  # type: ignore[assignment]

    def restore(self) -> None:
        if self._saved:
            socket.socket.connect = self._saved["connect"]  # type: ignore[method-assign]
            socket.socket.connect_ex = self._saved["connect_ex"]  # type: ignore[method-assign]
            socket.create_connection = self._saved["create_connection"]  # type: ignore[assignment]
            self._saved = {}


def _llm_import_probe() -> dict[str, Any]:
    """Diff ``sys.modules`` for model/LLM client roots around the app import.

    The bench imports ``app.capital_structure`` here — and only here — so the
    diff names exactly what the import itself pulled in.  When the module was
    already imported by the caller (an in-process test reuse), the diff is
    honestly empty and ``app_module_pre_imported`` says so.
    """
    before = {
        name
        for name in sys.modules
        if name.split(".")[0] in _LLM_CLIENT_ROOTS
    }
    pre_imported = "app.capital_structure" in sys.modules
    import app.capital_structure  # noqa: PLC0415 — the probe IS this import

    after = {
        name
        for name in sys.modules
        if name.split(".")[0] in _LLM_CLIENT_ROOTS
    }
    return {
        "llm_client_modules_reachable": sorted(after - before),
        "llm_client_modules_loaded_before": sorted(before),
        "app_module_pre_imported": pre_imported,
        "watched_roots": list(_LLM_CLIENT_ROOTS),
    }


def _api() -> Any:
    """The app module, already imported by ``_llm_import_probe``."""
    return sys.modules["app.capital_structure"]


def _reset_api_caches() -> None:
    api = _api()
    api._reset_cache()
    api._reset_state_cache()
    api._reset_inputs_cache()


def _point_api_at(state_path: Path, projection_path: Path, generation: Any) -> dict[str, Any]:
    """Point the app at one corpus the way the U1a ``served`` fixture does."""
    api = _api()
    saved = {
        "PROJECTION_PATH": api.PROJECTION_PATH,
        "STATE_PATH": api.STATE_PATH,
        "_load_generation": api._load_generation,
    }
    api.PROJECTION_PATH = projection_path
    api.STATE_PATH = state_path
    if generation is not None:
        api._load_generation = lambda: generation
    _reset_api_caches()
    return saved


def _restore_api(saved: dict[str, Any]) -> None:
    api = _api()
    api.PROJECTION_PATH = saved["PROJECTION_PATH"]
    api.STATE_PATH = saved["STATE_PATH"]
    api._load_generation = saved["_load_generation"]
    _reset_api_caches()


# ---------------------------------------------------------------------------
# The two corpus worlds (fixture corpus, copied committed data root)
# ---------------------------------------------------------------------------


class ServingWorld(NamedTuple):
    """One built corpus pointed at the served router, the way the U1a suite
    points its ``served`` fixture at it."""

    mode: str
    app: Any
    generation_id: str
    bundle_bytes_sha256: str
    bundle_byte_length: int
    issuer_count: int
    event_count: int | None
    event_count_source: str
    as_of: str
    issuer_id: str
    issuer_ids: tuple[str, ...]
    state_path: Path
    projection_path: Path
    health_path: Path | None
    evaluate_path: str
    evaluate_body: dict[str, Any]
    bundle: dict[str, Any]

    def new_client(self) -> Any:
        """One entitled TestClient; each reader thread builds its own."""
        from fastapi import FastAPI  # noqa: PLC0415 — lazy, like the served suites
        from fastapi.testclient import TestClient  # noqa: PLC0415

        application = FastAPI()
        application.include_router(_api().router)
        application.dependency_overrides[_api().require_site_full_user] = lambda: dict(
            _BENCH_USER
        )
        return TestClient(application)


def _fixture_corpus(work: Path) -> dict[str, Any]:
    """Build the U1a fixture generation, projection, state bundle and inputs.

    Built through the state-API suite's own fixture helpers, imported by name
    (never copied): the same event rows, the same builders, the same stamps.
    """
    import tests.test_capital_structure_state_api as state_suite  # noqa: PLC0415

    events, edges = state_suite._fixture_rows()
    telemetry = state_suite._telemetry(events, edges)
    telemetry["counts"] = {
        "event_versions": len(events),
        "event_edges": len(edges),
        "review_queue": 0,
    }
    generation = state_suite.VerifiedProjectionGeneration(
        tuple(events), tuple(edges), (), telemetry
    )
    projection = state_suite.build_projection_bundle(
        list(events),
        list(edges),
        (),
        telemetry,
        as_of=state_suite.AS_OF,
        generated_at=state_suite.GENERATED_AT,
    )
    projection_body = state_suite._write_json(work / "projection.json", projection)
    first = events[0]["evidence"][0]
    row = state_suite._manifest(role="primary")
    resolved_row = {
        **row,
        "manifest_id": first["manifest_id"],
        "spans": [
            {
                **row["spans"][0],
                "span_id": first["span_id"],
                "text_sha256": first["text_sha256"],
            }
        ],
    }
    pack = state_suite.load_rule_applicability_pack()
    bundle = state_suite.build_state_bundle(
        generation=generation,
        projection=projection,
        health=state_suite.HEALTH,
        rule_pack=pack,
        as_of=state_suite.AS_OF,
        generated_at=state_suite.STATE_GENERATED_AT,
        projection_sha256=hashlib.sha256(projection_body.encode("utf-8")).hexdigest(),
        source_manifests=(resolved_row,),
    )
    state_suite.validate_state_bundle(bundle)
    state_body = state_suite._write_json(work / "state_bundle.json", bundle)
    inputs_record = state_suite._inputs_bundle_record(
        state_suite._Built(
            events=events,
            edges=edges,
            generation=generation,
            projection=projection,
            bundle=bundle,
            projection_body=projection_body,
            state_body=state_body,
            manifest_id=str(first["manifest_id"]),
            span_id=str(first["span_id"]),
        )
    )
    (work / state_suite.CAPACITY_INPUTS_FILENAME).write_text(
        json.dumps(inputs_record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "generation": generation,
        "bundle": bundle,
        "issuer_ids": (state_suite.ISSUER_ONE, state_suite.ISSUER_TWO),
        "issuer_id": state_suite.ISSUER_ONE,
        "evaluate_body": state_suite._scenario_body(),
        "event_count": len(events),
        "event_count_source": "fixture event rows (len(events))",
        "state_path": work / "state_bundle.json",
        "projection_path": work / "projection.json",
        "health_path": None,
        "health_note": "the fixture corpus binds HEALTH in memory; the temp dir holds no health.json",
    }


def _real_corpus(work: Path, data_root: Path) -> dict[str, Any]:
    """Build the state bundle over a COPY of a committed data root.

    The existing nightly builder does the whole job over the copy; the
    repository's data tree is never written.
    """
    import scripts.build_capital_structure_state as state_builder  # noqa: PLC0415
    from engine.capital_structure.verified_projection_generation import (  # noqa: PLC0415
        read_verified_projection_generation,
    )

    copy = work / "data-root-copy"
    shutil.copytree(data_root, copy)
    state_builder.build_from_disk(root=copy)
    bundle = json.loads((copy / "state_bundle.json").read_text(encoding="utf-8"))
    issuer_rows = tuple(
        str(state["request"]["issuer_id"]) for state in bundle["issuers"]
    )
    event_count: int | None = None
    event_count_source = "issuer_index event_count sums (the verified generation is gone)"
    try:
        generation = read_verified_projection_generation(copy)
        counts = (generation.telemetry or {}).get("counts") or {}
        event_count = counts.get("event_versions")
        event_count_source = "verified generation telemetry counts.event_versions"
    except Exception:  # noqa: BLE001 — a named fallback, never a guessed count
        pass
    if event_count is None:
        event_count = sum(
            int(row.get("event_count") or 0)
            for row in (bundle["issuer_index"] or {}).values()
        )
    import tests.test_capital_structure_state_api as state_suite  # noqa: PLC0415

    return {
        "generation": None,
        "bundle": bundle,
        "issuer_ids": issuer_rows,
        "issuer_id": issuer_rows[0],
        "evaluate_body": state_suite._scenario_body(),
        "event_count": event_count,
        "event_count_source": event_count_source,
        "state_path": copy / "state_bundle.json",
        "projection_path": copy / "projection.json",
        "health_path": copy / "health.json",
        "health_note": None,
    }


@contextlib.contextmanager
def serving_world(
    *, data_root: Path | None, fixture: bool, work: Path
) -> Iterator[ServingWorld]:
    """Build ONE corpus in ``work``, point the app at it, and clean up."""
    if fixture == (data_root is not None):
        raise ValueError("serving_world: exactly one of fixture / data_root is required")
    work.mkdir(parents=True, exist_ok=True)
    _llm_import_probe()  # guarantees app.capital_structure is imported first
    if fixture:
        built = _fixture_corpus(work)
    else:
        assert data_root is not None
        built = _real_corpus(work, data_root)
    state_path: Path = built["state_path"]
    projection_path: Path = built["projection_path"]
    raw = state_path.read_bytes()
    saved = _point_api_at(state_path, projection_path, built.get("generation"))
    api = _api()
    from fastapi import FastAPI  # noqa: PLC0415

    application = FastAPI()
    application.include_router(api.router)
    application.dependency_overrides[api.require_site_full_user] = lambda: dict(_BENCH_USER)
    bundle = built["bundle"]
    world = ServingWorld(
        mode="fixture" if fixture else "data_root",
        app=application,
        generation_id=str(bundle["generation_id"]),
        bundle_bytes_sha256=hashlib.sha256(raw).hexdigest(),
        bundle_byte_length=len(raw),
        issuer_count=len(built["issuer_ids"]),
        event_count=built.get("event_count"),
        event_count_source=str(built["event_count_source"]),
        as_of=str(bundle["as_of"]),
        issuer_id=str(built["issuer_id"]),
        issuer_ids=tuple(built["issuer_ids"]),
        state_path=state_path,
        projection_path=projection_path,
        health_path=built.get("health_path"),
        evaluate_path=f"{_PREFIX}/issuers/{built['issuer_id']}/scenarios/evaluate",
        evaluate_body=built["evaluate_body"],
        bundle=bundle,
    )
    try:
        yield world
    finally:
        _restore_api(saved)


# ---------------------------------------------------------------------------
# The reference corpus statement (A45: a declared corpus, honestly denominated)
# ---------------------------------------------------------------------------

#: The A0 archetypes (research/capital_structure/e2e_20261013/reference/*.md).
REFERENCE_TICKERS = ("AIR", "CLNN", "EDBL", "LPTH", "QNCX", "WHK")

#: The G0 cases under tests/fixtures/capital_structure/reference/g0/.
_G0_CASE_DIR = _ROOT / "tests" / "fixtures" / "capital_structure" / "reference" / "g0"


def _corpus_statement(world: ServingWorld) -> dict[str, Any]:
    """Name the corpus: generation, bytes, issuers, events, reference presence.

    The denominator is stated honestly: reference issuers present in the bundle
    over ALL issuers in the bundle.  A reference issuer the bundle does not
    carry is listed as absent, never substituted.  Event records are never
    called supported dossiers.
    """
    from engine.capital_structure.reference_qualification import (  # noqa: PLC0415
        identity_for,
        load_reference_pack,
    )

    pack = load_reference_pack()
    covered = set(world.issuer_ids)
    entries = []
    present = 0
    for ticker in REFERENCE_TICKERS:
        issuer_id = str(identity_for(pack, ticker).issuer_id)
        is_present = issuer_id in covered
        present += 1 if is_present else 0
        entries.append(
            {"archetype": ticker, "issuer_id": issuer_id, "present": is_present}
        )
    g0_cases = (
        [
            {"case": path.name, "present_as_bundle_issuer": False}
            for path in sorted(_G0_CASE_DIR.iterdir())
        ]
        if _G0_CASE_DIR.is_dir()
        else []
    )
    issuer_count = int(
        (world.bundle.get("coverage") or {}).get("issuer_count") or world.issuer_count
    )
    return {
        "state_bundle_path": str(world.state_path),
        "generation_id": world.generation_id,
        "bundle_bytes_sha256": world.bundle_bytes_sha256,
        "bundle_byte_length": world.bundle_byte_length,
        "issuer_count": issuer_count,
        "event_count": world.event_count,
        "event_count_source": world.event_count_source,
        "as_of": world.as_of,
        "reference_set": {
            "definition": (
                "the A0 six archetypes (research/capital_structure/e2e_20261013/reference/"
                "AIR.md CLNN.md EDBL.md LPTH.md QNCX.md WHK.md) plus the G0 cases under "
                "tests/fixtures/capital_structure/reference/g0/"
            ),
            "issuers": entries,
            "g0_cases": g0_cases,
            "reference_issuers_present": present,
            "issuers_in_bundle": issuer_count,
            "denominator": (
                f"{present} of {len(REFERENCE_TICKERS)} reference issuers present in the "
                f"bundle, over {issuer_count} issuers in the bundle"
            ),
            "statement": (
                "The bundle carries event records and evidence spans; this record never "
                "calls them supported dossiers."
            ),
        },
        "evaluate_price_grid": _price_grid_of(world.evaluate_body),
    }


def _price_grid_of(evaluate_body: dict[str, Any]) -> dict[str, Any]:
    """The declared price grid the evaluate requests carry."""
    price = evaluate_body.get("price") or {}
    return {
        "kind": price.get("kind"),
        "currency": price.get("currency"),
        "fixed_price": price.get("fixed_price"),
        "note": "every evaluate request in both waves POSTs exactly this price grid",
    }


# ---------------------------------------------------------------------------
# The load waves (cold and warm), measured in-process
# ---------------------------------------------------------------------------


def _check_echo(route: str, status: int, body: Any, generation_id: str) -> bool:
    """Whether one served response echoes the served generation id."""
    if status != 200 or not isinstance(body, dict):
        return False
    if route == "coverage":
        return (body.get("state") or {}).get("generation_id") == generation_id
    return (body.get("view") or {}).get("generation_id") == generation_id


def _request_route(world: ServingWorld, client: Any, route: str) -> Any:
    """One request against one measured route."""
    if route == "state":
        return client.get(f"{_PREFIX}/issuers/{world.issuer_id}/state")
    if route == "registration":
        return client.get(f"{_PREFIX}/issuers/{world.issuer_id}/state/registration")
    if route == "coverage":
        return client.get(f"{_PREFIX}/coverage")
    return client.post(world.evaluate_path, json=world.evaluate_body)


def _run_wave(
    world: ServingWorld, readers: int, requests_per_reader: int, *, cold: bool
) -> dict[str, Any]:
    """One load wave: N concurrent reader threads, in-process, no network."""
    if cold:
        _reset_api_caches()
    guard = _SocketGuard()
    guard.install()
    durations: dict[str, list[int]] = {route: [] for route in _ROUTES}
    statuses: dict[str, list[int]] = {route: [] for route in _ROUTES}
    echo_all: dict[str, bool] = {route: True for route in _ROUTES}
    last_generation: dict[str, str | None] = {route: None for route in _ROUTES}
    lock = threading.Lock()
    barrier = threading.Barrier(readers)

    def reader(position: int) -> None:
        try:
            with world.new_client() as client:
                barrier.wait(timeout=120)
                for step in range(requests_per_reader):
                    route = _ROUTES[(position + step) % len(_ROUTES)]
                    started_ns = time.perf_counter_ns()
                    response = _request_route(world, client, route)
                    elapsed_ns = time.perf_counter_ns() - started_ns
                    status = int(response.status_code)
                    try:
                        body = response.json()
                    except ValueError:
                        body = None
                    echoed = _check_echo(route, status, body, world.generation_id)
                    with lock:
                        statuses[route].append(status)
                        durations[route].append(elapsed_ns)
                        if echoed:
                            last_generation[route] = world.generation_id
                        else:
                            echo_all[route] = False
        except BaseException:  # noqa: BLE001 — release the barrier, then re-raise
            barrier.abort()
            raise

    threads = [
        threading.Thread(target=reader, args=(position,), daemon=True)
        for position in range(readers)
    ]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=600)
        for thread in threads:
            if thread.is_alive():
                raise RuntimeError("a V0 bench reader thread did not finish")
    finally:
        guard.restore()
    return {
        "request_count": sum(len(values) for values in statuses.values()),
        "routes": {
            route: {
                **_route_latency_block(durations[route], statuses[route]),
                "generation_id_echo_all_responses": echo_all[route],
                "last_echoed_generation_id": last_generation[route],
            }
            for route in _ROUTES
            if statuses[route]
        },
    }


def _against_proposal(route: str, warm_block: dict[str, Any], readers: int) -> str:
    """The measured warm p95 against the SPEC_V0 §1 proposal, honestly named.

    A run at fewer than the proposal's 10 readers is labelled with the reader
    count it actually used; the proposal itself is never edited.
    """
    target = (
        _PROPOSAL_BOUND_EVALUATE_P95_US
        if route == "evaluate"
        else _PROPOSAL_CACHED_DOSSIER_P95_US
    )
    if warm_block["request_count"] == 0:
        return "not_measured"
    if set(warm_block["status_counts"]) != {"200"}:
        return "not_measured_route_never_answered_200"
    verdict = "pass" if warm_block["p95_us"] <= target else "miss"
    if readers != _PROPOSAL_STATED_READERS:
        verdict = (
            f"{verdict}_at_{readers}_readers"
            f"_proposal_stated_at_{_PROPOSAL_STATED_READERS}"
        )
    return verdict


# ---------------------------------------------------------------------------
# Source age (values, never adjectives)
# ---------------------------------------------------------------------------


def _source_age(world: ServingWorld) -> dict[str, Any]:
    """Per-issuer source age as integer day values against the named clocks."""
    newest: dict[str, str] = {}
    for entry in (world.bundle.get("evidence_index") or {}).values():
        issuer_id = entry.get("issuer_id")
        available = entry.get("available_at")
        if isinstance(available, dict):
            available = available.get("system")
        if issuer_id and isinstance(available, str) and available:
            if str(available) > newest.get(str(issuer_id), ""):
                newest[str(issuer_id)] = str(available)
    as_of_day = datetime.fromisoformat(world.as_of.replace("Z", "+00:00")).date()
    per_issuer = []
    for issuer_id in sorted(newest)[:50]:
        newest_day = datetime.fromisoformat(newest[issuer_id].replace("Z", "+00:00")).date()
        per_issuer.append(
            {
                "issuer_id": issuer_id,
                "newest_evidence_available_at": newest[issuer_id],
                "bundle_as_of_lag_days": (as_of_day - newest_day).days,
            }
        )
    return {
        "bundle_as_of": world.as_of,
        "clock_definition": (
            "per-issuer lag in whole days between the bundle as_of date and the "
            "issuer's newest evidence_index available_at; the root's ingestion "
            "health watermark and the discovery clock's expected daily index date "
            "are recorded beside them"
        ),
        "per_issuer_sample": per_issuer,
        "per_issuer_sample_note": (
            f"the {len(per_issuer)} alphabetically-first issuers carrying evidence, "
            f"of {len(newest)} issuers with evidence in the bundle"
        ),
        "ingestion_health_source_high_watermark": _root_watermark(world),
        "expected_daily_index_date": _expected_index_horizon(),
    }


def _root_watermark(world: ServingWorld) -> dict[str, Any]:
    """The health artifact's source watermark, or a named null with the reason."""
    if world.health_path is None:
        return {
            "latest_retrieved_at": None,
            "latest_filing_date": None,
            "reason": (
                "the fixture corpus binds HEALTH in memory and publishes no "
                "health.json in the temp dir"
            ),
        }
    try:
        health = json.loads(world.health_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {
            "latest_retrieved_at": None,
            "latest_filing_date": None,
            "reason": f"health.json unreadable: {type(exc).__name__}",
        }
    mark = health.get("source_high_watermark_after") or {}
    return {
        "latest_retrieved_at": mark.get("latest_retrieved_at"),
        "latest_filing_date": mark.get("latest_filing_date"),
        "source_manifest_count": mark.get("source_manifest_count"),
    }


def _expected_index_horizon() -> dict[str, Any]:
    """The discovery clock's expected complete daily index date for now."""
    try:
        from engine.capital_structure.sec_discovery_clock import (  # noqa: PLC0415
            latest_expected_daily_index_date,
        )

        observed = datetime.now(timezone.utc)
        return {
            "date": latest_expected_daily_index_date(observed).isoformat(),
            "observed_at": observed.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    except Exception as exc:  # noqa: BLE001 — a named null, never a guessed date
        return {"date": None, "reason": f"{type(exc).__name__}: {exc}"}


# ---------------------------------------------------------------------------
# The branch-bound probe
# ---------------------------------------------------------------------------


def _canonical_digest(payload: Any) -> str | None:
    """The canonical-JSON sha256 of one decoded served body, or None."""
    if payload is None:
        return None
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


#: The identity keys two served bodies of the SAME request may differ in:
#: every response mints its own receipts and digests, so only a difference
#: outside these keys is a visible change in the served answer.
_IDENTITY_KEYS = frozenset(
    {
        "result_id",
        "scenario_id",
        "state_id",
        "receipt",
        "input_digest",
        "digest",
        "computed_at",
    }
)


def _strip_identity(node: Any) -> Any:
    """Drop the identity keys at every depth (the bodies' own mint)."""
    if isinstance(node, dict):
        return {
            key: _strip_identity(value)
            for key, value in node.items()
            if key not in _IDENTITY_KEYS
        }
    if isinstance(node, list):
        return [_strip_identity(item) for item in node]
    return node


def _branch_bound_probe(world: ServingWorld) -> dict[str, Any]:
    """One served evaluate request over the declared branch bound.

    No fixture on this base can exceed 4096 exclusive-choice branches through
    the API, so ``MAX_BRANCHES`` is monkeypatched for this ONE request only;
    the production constant is restored in ``finally`` and the substitution is
    recorded.  The SAME body is posted twice — once under the declared bound,
    once over it — so the two served answers differ by nothing but the bound.
    The kernel's own refusal shape (``solve_joint``, lines 302-309) is recorded
    beside what the served body actually carried.
    """
    from engine.capital_structure import capacity_joint  # noqa: PLC0415

    probe: dict[str, Any] = {
        "declared_limit": capacity_joint.MAX_BRANCHES,
        "monkeypatched_limit": None,
        "kernel_refusal": None,
        "served_request": None,
    }
    real = capacity_joint.MAX_BRANCHES
    capacity_joint.MAX_BRANCHES = 1
    try:
        kernel = capacity_joint.solve_joint(
            [
                capacity_joint.JointRoute("route:a", 8),
                capacity_joint.JointRoute("route:b", 7),
            ],
            exclusive=[("route:a", "route:b")],
        )
        probe["kernel_refusal"] = kernel.as_record()
    finally:
        capacity_joint.MAX_BRANCHES = real
    kernel_blockers = (probe["kernel_refusal"] or {}).get("blockers") or ()

    with world.new_client() as client:
        plain = client.post(world.evaluate_path, json=world.evaluate_body)
        try:
            plain_body = plain.json()
        except ValueError:
            plain_body = None
        route_ids = [
            str(route.get("route_id"))
            for route in (
                (plain_body or {}).get("result", {}).get("capacity_envelope", {}).get("routes")
                or []
            )
        ]
        probe_body = dict(world.evaluate_body)
        exclusivity_declared = len(route_ids) >= 2
        if exclusivity_declared:
            kept = tuple(
                (str(key), str(value))
                for key, value in (world.evaluate_body.get("other_assumptions") or ())
                if str(key) != "route_exclusivity"
            )
            probe_body["other_assumptions"] = list(
                kept + (("route_exclusivity", "|".join(route_ids[:2])),)
            )
        under_bound = client.post(world.evaluate_path, json=probe_body)
        under_bound_status = int(under_bound.status_code)
        try:
            under_bound_body = under_bound.json()
        except ValueError:
            under_bound_body = None
        capacity_joint.MAX_BRANCHES = 0
        probe["monkeypatched_limit"] = 0
        try:
            over_bound = client.post(world.evaluate_path, json=probe_body)
        finally:
            capacity_joint.MAX_BRANCHES = real
        over_bound_status = int(over_bound.status_code)
        try:
            over_bound_body = over_bound.json()
        except ValueError:
            over_bound_body = None
        over_text = (
            json.dumps(over_bound_body, sort_keys=True, separators=(",", ":"))
            if over_bound_body is not None
            else ""
        )
        probe["served_request"] = {
            "plain_status": int(plain.status_code),
            "under_bound_status": under_bound_status,
            "over_bound_status": over_bound_status,
            "exclusivity_declared": exclusivity_declared,
            "served_view_generation_id": ((over_bound_body or {}).get("view") or {}).get(
                "generation_id"
            ),
            "served_aggregate_status": (
                (over_bound_body or {})
                .get("result", {})
                .get("capacity_envelope", {})
                .get("aggregate_bound", {})
                .get("status")
            ),
            "served_joint_check_status": (over_bound_body or {}).get("result", {}).get(
                "joint_check", {}
            ).get("status"),
            "under_bound_canonical_sha256": _canonical_digest(under_bound_body),
            "over_bound_canonical_sha256": _canonical_digest(over_bound_body),
            "over_bound_equals_under_bound_after_identity_strip": (
                _strip_identity(under_bound_body) == _strip_identity(over_bound_body)
            ),
            "served_body_names_the_refusal": (
                any(blocker in over_text for blocker in kernel_blockers)
                if kernel_blockers
                else False
            ),
        }
    probe["note"] = (
        "MAX_BRANCHES was monkeypatched to 0 for the one over-bound request only; "
        "the production constant 4096 is never edited"
    )
    return probe


# ---------------------------------------------------------------------------
# The bench entry point
# ---------------------------------------------------------------------------


def run_bench(
    *,
    data_root: Path | str | None = None,
    fixture: bool = False,
    readers: int = 10,
    requests_per_reader: int = 20,
    out: Path | str | None = None,
) -> dict[str, Any]:
    """Run the whole bench once and return the record (writing it if ``out``)."""
    if readers < 1 or requests_per_reader < 1:
        raise ValueError("readers and requests_per_reader must be positive")
    record: dict[str, Any] = {}
    probe = _llm_import_probe()
    guard = _SocketGuard()
    guard.install()
    try:
        with tempfile.TemporaryDirectory(prefix="v0-serving-bench-") as tmp:
            work = Path(tmp)
            with serving_world(
                data_root=Path(data_root) if data_root is not None else None,
                fixture=fixture,
                work=work,
            ) as world:
                record["schema"] = RECORD_SCHEMA_NAME
                record["wall_clock_utc"] = datetime.now(timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                )
                record["mode"] = world.mode
                record["hardware"] = {
                    "machine": platform.machine(),
                    "cpu_count": os.cpu_count(),
                    "python_version": platform.python_version(),
                }
                record["corpus"] = _corpus_statement(world)
                cold = _run_wave(world, readers, requests_per_reader, cold=True)
                warm = _run_wave(world, readers, requests_per_reader, cold=False)
                for route, block in warm["routes"].items():
                    block["route"] = route
                    block["against_proposal"] = _against_proposal(route, block, readers)
                record["load"] = {
                    "readers": readers,
                    "requests_per_reader": requests_per_reader,
                    "cold": cold,
                    "warm": warm,
                    "cache_state_note": (
                        "cold: the served caches are reset immediately before the "
                        "wave; warm: the same wave runs again over the hot caches"
                    ),
                }
                record["proposal_targets"] = {
                    "cached_dossier_p95_max_us": _PROPOSAL_CACHED_DOSSIER_P95_US,
                    "bounded_evaluate_p95_max_us": _PROPOSAL_BOUND_EVALUATE_P95_US,
                    "stated_at_readers": _PROPOSAL_STATED_READERS,
                    "status": (
                        "proposals, never thresholds; the bench never edits one and "
                        "CI never asserts one"
                    ),
                }
                record["source_age"] = _source_age(world)
                record["branch_bound_probe"] = _branch_bound_probe(world)
                record["no_request_time_fan_out"] = {
                    "outbound_connect_attempts": guard.attempts,
                    "guard": (
                        "socket.socket.connect / connect_ex / socket.create_connection "
                        "raised and counted across both waves and the probe"
                    ),
                    **probe,
                }
    finally:
        guard.restore()
    validate_record(record)
    if out is not None:
        Path(out).write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    return record


def validate_record(record: dict[str, Any], schema: dict[str, type] | None = None) -> None:
    """Validate the record against ``RECORD_SCHEMA`` (required keys to types)."""
    active = RECORD_SCHEMA if schema is None else schema
    missing = sorted(key for key in active if key not in record)
    if missing:
        raise ValueError(f"bench record is missing required keys: {missing}")
    for key, kind in active.items():
        if not isinstance(record[key], kind):
            raise ValueError(
                f"bench record key {key!r} must be {kind.__name__}, "
                f"got {type(record[key]).__name__}"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=None)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--readers", type=int, default=10)
    parser.add_argument("--requests-per-reader", type=int, default=20)
    parser.add_argument(
        "--fixture",
        action="store_true",
        help="build the small in-test fixture corpus instead of a data root",
    )
    args = parser.parse_args(argv)
    if args.fixture == (args.data_root is not None):
        parser.error("exactly one of --fixture / --data-root is required")
    record = run_bench(
        data_root=args.data_root,
        fixture=args.fixture,
        readers=args.readers,
        requests_per_reader=args.requests_per_reader,
        out=args.out,
    )
    print(
        json.dumps(
            {
                "out": str(args.out),
                "generation_id": record["corpus"]["generation_id"],
                "outbound_connect_attempts": record["no_request_time_fan_out"][
                    "outbound_connect_attempts"
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
