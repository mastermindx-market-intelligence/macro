"""V0-1 CI serving test (SPEC_V0 §1): a small bench in-process, zero fan-out.

The suite runs the bench's own library entrypoint in fixture mode at a small
N and asserts the properties CI can assert: zero outbound connect attempts, no
model/LLM client module reachable from the ``app.capital_structure`` import,
every served route echoing the served ``generation_id``, the branch-bound
request meeting the typed refusal, and the record validating against the
bench's own ``RECORD_SCHEMA``.  NO timing assertion: the shared runner is
noisy, the proposal targets are recorded in the bench JSON and never asserted
here (SPEC_V0 §1).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("fastapi", reason="capital structure API tests need fastapi")
pytest.importorskip("httpx", reason="FastAPI TestClient needs httpx")

import scripts.bench_capital_structure_serving as bench  # noqa: E402
from scripts.bench_capital_structure_serving import (  # noqa: E402
    RECORD_SCHEMA,
    run_bench,
)

#: The forbidden cast, assembled so this source never spells it itself.
FLOAT_CAST = "float" + "("

#: The served routes the bench measures, in its own order.
_ROUTES = ("state", "registration", "coverage", "evaluate")


@pytest.fixture(scope="module")
def record(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """The small bench run every test in this module reads from."""
    out = tmp_path_factory.mktemp("v0-serving") / "v0_serving_record.json"
    return run_bench(
        data_root=None,
        fixture=True,
        readers=3,
        requests_per_reader=2,
        out=out,
    )


# ---------------------------------------------------------------------------
# Zero outbound connections (A45: no request-time fan-out)
# ---------------------------------------------------------------------------


def test_v0_serving_makes_zero_outbound_connections(record: dict[str, Any]) -> None:
    fan_out = record["no_request_time_fan_out"]
    assert fan_out["outbound_connect_attempts"] == 0, (
        "the V0 bench made outbound socket attempts while serving the corpus: "
        f"{fan_out['outbound_connect_attempts']}"
    )
    assert fan_out["app_module_pre_imported"] is False or isinstance(
        fan_out["app_module_pre_imported"], bool
    )


# ---------------------------------------------------------------------------
# No model/LLM client import is reachable from app.capital_structure
# ---------------------------------------------------------------------------


def test_v0_serving_imports_no_model_client(record: dict[str, Any]) -> None:
    probe = record["no_request_time_fan_out"]
    assert probe["llm_client_modules_reachable"] == [], (
        "importing app.capital_structure pulled in model client modules: "
        f"{probe['llm_client_modules_reachable']}"
    )
    assert set(probe["watched_roots"]) == {
        "anthropic",
        "openai",
        "litellm",
        "google.generativeai",
    }


# ---------------------------------------------------------------------------
# Every route echoes the served generation id, asserted per response
# ---------------------------------------------------------------------------


def _echoing_routes(record: dict[str, Any]) -> tuple[str, ...]:
    return tuple(sorted(record["load"]["cold"]["routes"]))


def test_v0_every_route_echoes_the_served_generation_id(
    record: dict[str, Any], tmp_path: Path
) -> None:
    served_generation = record["corpus"]["generation_id"]
    assert _echoing_routes(record) == tuple(sorted(_ROUTES)), (
        f"the bench measured {_echoing_routes(record)}, expected {sorted(_ROUTES)}"
    )
    for cache_state in ("cold", "warm"):
        routes = record["load"][cache_state]["routes"]
        for route, block in sorted(routes.items()):
            assert block["generation_id_echo_all_responses"] is True, (
                f"{cache_state} {route}: a response did not echo the served "
                f"generation id {served_generation!r}"
            )
            assert block["last_echoed_generation_id"] == served_generation, (
                f"{cache_state} {route}: last echo {block['last_echoed_generation_id']!r}"
            )

    # An independent pass, one response per route, asserted directly: the bench's
    # own bookkeeping is not the assertion.
    with bench.serving_world(data_root=None, fixture=True, work=tmp_path / "world") as world:
        served_generation = world.generation_id
        with world.new_client() as client:
            checks = (
                (
                    f"{bench._PREFIX}/issuers/{world.issuer_id}/state",
                    client.get(f"{bench._PREFIX}/issuers/{world.issuer_id}/state"),
                    lambda body: body["view"]["generation_id"],
                ),
                (
                    f"{bench._PREFIX}/issuers/{world.issuer_id}/state/registration",
                    client.get(
                        f"{bench._PREFIX}/issuers/{world.issuer_id}/state/registration"
                    ),
                    lambda body: body["view"]["generation_id"],
                ),
                (
                    f"{bench._PREFIX}/coverage",
                    client.get(f"{bench._PREFIX}/coverage"),
                    lambda body: body["state"]["generation_id"],
                ),
            )
            for url, response, read_generation in checks:
                assert response.status_code == 200, (url, response.status_code)
                body = response.json()
                assert read_generation(body) == served_generation, (
                    f"{url} echoed {read_generation(body)!r}, served {served_generation!r}"
                )
            evaluate = client.post(world.evaluate_path, json=world.evaluate_body)
            assert evaluate.status_code == 200, (world.evaluate_path, evaluate.status_code)
            evaluate_body = evaluate.json()
            assert evaluate_body["view"]["generation_id"] == served_generation, (
                f"{world.evaluate_path} echoed "
                f"{evaluate_body['view']['generation_id']!r}, served {served_generation!r}"
            )


# ---------------------------------------------------------------------------
# The branch bound returns the typed refusal
# ---------------------------------------------------------------------------


def test_v0_branch_bound_returns_the_typed_refusal(record: dict[str, Any]) -> None:
    probe = record["branch_bound_probe"]
    kernel = probe["kernel_refusal"]
    # (a) The kernel's typed refusal, exactly the shape solve_joint returns
    # past the declared bound (capacity_joint.py:302-309).
    assert kernel["determined"] is False
    assert kernel["branches_evaluated"] == 0
    assert kernel["value"] is None and kernel["witness"] is None
    assert kernel["blockers"] == [
        "exclusive choices give 2 branches, above the 1 enumeration limit"
    ]
    assert probe["monkeypatched_limit"] == 0
    assert probe["declared_limit"] == 4096

    # (b) The served evaluate request driven over that bound must carry the
    # same typed refusal, never a silent approximation (SPEC_V0 §1).
    served = probe["served_request"]
    assert served["over_bound_status"] == 200, served
    assert served["served_view_generation_id"] == record["corpus"]["generation_id"]
    assert served["served_body_names_the_refusal"] is True, (
        "the served evaluate response over the exceeded branch bound carries no "
        "typed refusal: the answer is byte-identical to the under-bound answer "
        "outside the identity mints "
        f"(under_bound sha256 {served['under_bound_canonical_sha256']}, over_bound "
        f"sha256 {served['over_bound_canonical_sha256']}, "
        f"identical_after_identity_strip="
        f"{served['over_bound_equals_under_bound_after_identity_strip']}, "
        f"aggregate_status={served['served_aggregate_status']!r}, "
        f"joint_check_status={served['served_joint_check_status']!r}); the kernel "
        f"refusal was {json.dumps(kernel, sort_keys=True)}"
    )


# ---------------------------------------------------------------------------
# The record validates against the bench's own schema
# ---------------------------------------------------------------------------


def test_v0_bench_record_validates_against_schema(record: dict[str, Any]) -> None:
    bench.validate_record(record)
    for key, kind in RECORD_SCHEMA.items():
        assert isinstance(record[key], kind), (key, type(record[key]).__name__)
    assert record["schema"] == bench.RECORD_SCHEMA_NAME
    assert record["mode"] == "fixture"
    corpus = record["corpus"]
    assert corpus["generation_id"]
    assert len(corpus["bundle_bytes_sha256"]) == 64
    assert corpus["issuer_count"] >= 1
    assert corpus["reference_set"]["denominator"].startswith(
        f"{corpus['reference_set']['reference_issuers_present']} of "
        f"{len(corpus['reference_set']['issuers'])} reference issuers present"
    )
    # The load block names both cache states and integer-µs percentiles only.
    for cache_state in ("cold", "warm"):
        for block in record["load"][cache_state]["routes"].values():
            for field in ("p50_us", "p95_us", "max_us"):
                assert isinstance(block[field], int), (cache_state, field)


# ---------------------------------------------------------------------------
# No float cast in either new file
# ---------------------------------------------------------------------------


def test_v0_serving_files_contain_no_float_cast() -> None:
    sources = (
        Path(bench.__file__).read_text(encoding="utf-8"),
        Path(__file__).read_text(encoding="utf-8"),
    )
    for source in sources:
        assert FLOAT_CAST not in source, "a forbidden cast is present in a V0 file"
