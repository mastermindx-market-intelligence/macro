"""Isolated installed-router check; no production producer, auth session, or writes.

After protected landing and normal macro-update installation, send this file to
/opt/macro-api/.venv/bin/python -B - /opt/macro. It proves the installed router's
admission behavior with an in-memory producer, not live authentication or load.
Separately require /api/health's PROCESS commit to contain the actual merge and
the normal updater's successful API PID transition. Checkout parity alone is
insufficient. Use the existing public health/authenticated browser checks; do not
load-test the small VPS with two real candidate materializations.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import sys
import types
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from urllib.parse import urlencode

EXPECTED = "f2abbf35e7da98b8aae8b29c032aad3196c873fe8bdddb5c9f6af513cb382884"


def main(root: Path) -> dict:
    source = root / "app/prophet_daily_brief.py"
    before = source.read_bytes()
    assert hashlib.sha256(before).hexdigest() == EXPECTED, "unreviewed router bytes"
    sys.path.insert(0, str(root))
    from starlette.requests import Request
    from app import prophet_daily_brief as route

    auth = inspect.signature(route.daily_brief_v1).parameters["_user"].default
    assert auth.dependency is route.require_site_full_user
    producer = types.ModuleType("scripts.build_stock_library")
    # This process only: a real native reader is never imported or invoked.
    sys.modules[producer.__name__] = producer
    good = {"source_sha256": "sha256:" + "a" * 64, "pair_id": "b" * 32,
            "selection_receipt": "sha256:" + "c" * 64}
    envelope = {"status": "AVAILABLE", "reason_codes": [], "fixture": True}
    calls = []

    def invoke(query=None):
        request = Request({"type": "http", "method": "GET", "path": "/",
                           "headers": [], "query_string": urlencode(good if query is None else query).encode()})
        return route.daily_brief_v1(request, _user={"sub": "isolated-probe"})

    def check(response, status, body):
        assert response.status_code == status
        assert json.loads(response.body) == body
        for key, value in route._PRIVATE_HEADERS.items():
            assert response.headers[key] == value

    def available(*args, **kwargs):
        calls.append(kwargs)
        return envelope

    entered, release = Event(), Event()

    def held(*args, **kwargs):
        calls.append(kwargs)
        entered.set()
        assert release.wait(5), "probe failed to release fixture"
        return envelope

    unavailable = {"error": "DAILY_BRIEF_UNAVAILABLE"}
    producer.read_today_candidate_projection = held
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(invoke)
        try:
            assert entered.wait(2), "fixture not entered"
            check(pool.submit(invoke).result(timeout=2), 503, unavailable)
            assert len(calls) == 1 and not first.done(), "overlap reached producer"
            check(invoke({**good, "root": "/not-permitted"}), 400, {"error": "INVALID_QUERY"})
        finally:
            release.set()
        check(first.result(timeout=2), 200, envelope)
    producer.read_today_candidate_projection = available
    check(invoke(), 200, envelope)
    assert len(calls) == 2

    def broken(*args, **kwargs):
        raise RuntimeError("fixture failure only")

    failures = {
        "owner": broken,
        "shape": lambda *a, **k: None,
        "serialization": lambda *a, **k: {"status": "AVAILABLE", "bad": float("nan")},
    }
    for kind in ("import", *failures):
        sys.modules[producer.__name__] = None if kind == "import" else producer
        if kind != "import":
            producer.read_today_candidate_projection = failures[kind]
        check(invoke(), 503, unavailable)
        sys.modules[producer.__name__] = producer
        producer.read_today_candidate_projection = available
        check(invoke(), 200, envelope)
    assert source.read_bytes() == before
    return {"status": "PASS", "groups": 8, "router_sha256": EXPECTED,
            "controls": ["auth_dependency_preserved", "overlap_refused", "invalid_query_before_permit",
                         "success_releases", "import_releases", "owner_releases", "shape_releases", "serialization_releases"],
            "scope": "isolated installed router with in-memory producer",
            "native_producer_calls": 0, "production_writes": 0,
            "live_authentication_proven": False, "running_service_proven": False}


if __name__ == "__main__":
    print(json.dumps(main(Path(sys.argv[1]).resolve()), indent=2))
