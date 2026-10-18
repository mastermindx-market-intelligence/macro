"""C19 WP32 P6 — integrated-answer denial / cache / latency pins (tests only).

BASE: ``origin/main`` 4f52d22596545cbd67b5143e188baf5660237024.

Rung P6 of the WP32 rollout ladder for ``GET /api/integrated-answer/v1/{ticker}``:
a 401 or 403 served AFTER an entitled 200 in the same process — with the
module-level K3E / expectation-chip caches warm (``app/integrated_answer.py:156-162``)
— must carry no leg evidence, no page SHA header and no consumed-receipts header;
the flag-off 404 must leak nothing; and the compose wall time must be measured
and reported.

Denials are driven through the REAL entitlement wrapper (the WP19 idiom:
``tests/test_c19_wp19_integrated_answer_entitlement_pins.py``) with stubbed
``app.main`` / ``app.paywall`` modules, so nothing here is a dependency override.
Fixtures are synthetic (ZZWP only) and live in ``tmp_path`` behind
``MACRO_CTE_DIR``; nothing under ``data/`` is opened, no network, no sleep.
"""
from __future__ import annotations

import json
import time

from fastapi import HTTPException

import app.integrated_answer as integrated_answer
from app.forensics import _PRIVATE_HEADERS
from app.integrated_answer import CONSUMED_RECEIPTS_HEADER
from tests.test_c19_wp19_integrated_answer_entitlement_pins import (
    _allowing_stubs,
    _forbid_compose,
    _real_client,
    _stub_auth,
)
from tests.test_c19_wp32_correction import (
    NOW,
    PATH,
    SUMMARY_G1,
    TICKER,
    _exposed_generation_ids,
    _publish,
)
from tests.test_integrated_answer_v0 import _patch_all_seams

TOKEN = {"Authorization": "Bearer wp32-token"}
CANARY = "WP32-CACHE-CANARY"
_SHA_NEEDLES = ('"legs"', '"ref"', '"consumed_receipt"')


def _warm_root(monkeypatch, tmp_path) -> str:
    """Publish one synthetic CTE generation into ``tmp_path`` and return its generation id."""
    marker = _publish(tmp_path, source_dir=tmp_path / "src-g1", summary=SUMMARY_G1)
    monkeypatch.setenv("MACRO_CTE_DIR", str(tmp_path))
    return str(marker["generation_id"])


def _poison_caches(monkeypatch) -> str:
    """Warm the module-level caches with values shaped like the real ones but carrying a canary.

    ``_k3e_cached_bundle`` is the ``(obs, attempts, provenance)`` tuple ``_k3e_source`` caches
    (``app/integrated_answer.py:307-329``) and ``_chip_cached_value`` the ``{ticker: chip}`` map
    ``_expectation_chips`` caches keyed by ``day.isoformat()`` (``:332-343``).  The chip day is set
    to the frozen compose day, so a compose that ran during a denial would serve the canary chip
    into the earnings_expectation leg and the leakage assertions would have real power.
    """
    monkeypatch.setattr(integrated_answer, "_k3e_cached_rev", f"{CANARY}-{'0' * 40}")
    monkeypatch.setattr(
        integrated_answer,
        "_k3e_cached_bundle",
        ([], [], {"source_revision": CANARY, "inputs": {CANARY: CANARY}}),
    )
    monkeypatch.setattr(integrated_answer, "_chip_cached_day", NOW[:10])
    monkeypatch.setattr(
        integrated_answer,
        "_chip_cached_value",
        {TICKER: {"schema": "expectation_chip.v0", "ticker": TICKER, "label": CANARY}},
    )
    return CANARY


def _deny_stubs(monkeypatch, *, status_code: int, detail: str) -> list[str]:
    """Install real-wrapper stubs whose ``require_user`` denies with ``status_code``."""
    calls: list[str] = []

    def _require_user(authorization=None, *_args, **_kwargs):
        calls.append("require_user")
        headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
        raise HTTPException(status_code=status_code, detail=detail, headers=headers)

    def _enforce_site_full(user, *, always=False) -> dict:
        calls.append("enforce_site_full")
        return user

    _stub_auth(monkeypatch, require_user=_require_user, enforce_site_full=_enforce_site_full)
    return calls


def _entitle_then_deny_403(monkeypatch) -> None:
    """Stub that authenticates, then has ``enforce_site_full`` raise 403 (the WP13/WP19 idiom)."""
    def _require_user(authorization=None, *_args, **_kwargs) -> dict:
        return {"id": "u-wp32"}

    def _enforce_site_full(user, *, always=False) -> dict:
        raise HTTPException(status_code=403, detail="site_full required")

    _stub_auth(monkeypatch, require_user=_require_user, enforce_site_full=_enforce_site_full)


def _assert_denial_is_silent(response, gid: str, *, canary: str | None = None) -> None:
    """Every P6 denial assertion: no leg evidence, no page SHA, no receipts header, all private headers."""
    text = response.text
    needles = [*_SHA_NEEDLES, gid, TICKER, SUMMARY_G1]
    if canary is not None:
        needles.append(canary)
    for needle in needles:
        assert needle not in text, needle
    assert "X-Integrated-Answer-SHA256" not in response.headers
    assert CONSUMED_RECEIPTS_HEADER not in response.headers
    for name, value in _PRIVATE_HEADERS.items():
        assert response.headers[name] == value


def test_p6_401_after_a_warm_entitled_200_carries_no_leg_evidence(monkeypatch, tmp_path) -> None:
    """P6 DENIAL (T4a): served after an entitled 200 in the same process, a 401 from the real
    wrapper carries no leg evidence (no "legs"/"ref"/"consumed_receipt", no generation id, no
    ticker, no exposure summary text), no X-Integrated-Answer-SHA256 and no consumed-receipts
    header, while every private header is present."""
    gid = _warm_root(monkeypatch, tmp_path)
    _allowing_stubs(monkeypatch)
    _patch_all_seams(monkeypatch, ticker=TICKER)
    monkeypatch.setattr(integrated_answer, "_utc_now", lambda: NOW)
    client = _real_client(monkeypatch)

    warm = client.get(PATH, headers=TOKEN)
    assert warm.status_code == 200
    assert _exposed_generation_ids(warm) == {gid}

    _forbid_compose(monkeypatch)
    calls = _deny_stubs(monkeypatch, status_code=401, detail="missing bearer token")
    denied = client.get(PATH, headers=TOKEN)
    assert denied.status_code == 401
    assert denied.json() == {"detail": "missing bearer token"}
    assert calls == ["require_user"]  # authentication short-circuits before the entitlement check
    _assert_denial_is_silent(denied, gid)
    assert denied.headers["WWW-Authenticate"] == "Bearer"


def test_p6_403_after_a_warm_entitled_200_carries_no_leg_evidence(monkeypatch, tmp_path) -> None:
    """P6 DENIAL (T4a): the entitled-auth / denied-entitlement boundary — a 403 raised by
    ``enforce_site_full`` after a warm entitled 200 is equally evidence-free and equally private."""
    gid = _warm_root(monkeypatch, tmp_path)
    _allowing_stubs(monkeypatch)
    _patch_all_seams(monkeypatch, ticker=TICKER)
    monkeypatch.setattr(integrated_answer, "_utc_now", lambda: NOW)
    client = _real_client(monkeypatch)

    warm = client.get(PATH, headers=TOKEN)
    assert warm.status_code == 200

    _forbid_compose(monkeypatch)
    _entitle_then_deny_403(monkeypatch)
    denied = client.get(PATH, headers=TOKEN)
    assert denied.status_code == 403
    assert denied.json() == {"detail": "site_full required"}
    _assert_denial_is_silent(denied, gid)


def test_p6_poisoned_module_caches_never_surface_in_a_401(monkeypatch, tmp_path) -> None:
    """P6 CACHE (T4b): the K3E and chip caches are warm with a canary; a 401 denial surfaces the
    canary in neither body nor any header — and the denial does not drain or rewrite them."""
    gid = _warm_root(monkeypatch, tmp_path)
    canary = _poison_caches(monkeypatch)
    monkeypatch.setattr(integrated_answer, "_utc_now", lambda: NOW)
    monkeypatch.setattr(
        integrated_answer, "_k3e_source", lambda: (_ for _ in ()).throw(RuntimeError("no k3e during denial"))
    )
    _forbid_compose(monkeypatch)
    client = _real_client(monkeypatch)
    calls = _deny_stubs(monkeypatch, status_code=401, detail="missing bearer token")
    denied = client.get(PATH, headers=TOKEN)
    assert denied.status_code == 401
    assert calls == ["require_user"]
    _assert_denial_is_silent(denied, gid, canary=canary)
    assert all(canary not in value for value in denied.headers.values())
    assert integrated_answer._chip_cached_day == NOW[:10]
    assert integrated_answer._chip_cached_value[TICKER]["label"] == canary
    assert canary in str(integrated_answer._k3e_cached_bundle)


def test_p6_poisoned_module_caches_never_surface_in_a_403(monkeypatch, tmp_path) -> None:
    """P6 CACHE (T4b): the same warm-canary caches behind a 403 — the entitlement denial leaks no
    cached compose input either."""
    gid = _warm_root(monkeypatch, tmp_path)
    canary = _poison_caches(monkeypatch)
    monkeypatch.setattr(integrated_answer, "_utc_now", lambda: NOW)
    monkeypatch.setattr(
        integrated_answer, "_k3e_source", lambda: (_ for _ in ()).throw(RuntimeError("no k3e during denial"))
    )
    _forbid_compose(monkeypatch)
    client = _real_client(monkeypatch)
    _entitle_then_deny_403(monkeypatch)

    denied = client.get(PATH, headers=TOKEN)
    assert denied.status_code == 403
    _assert_denial_is_silent(denied, gid, canary=canary)
    assert all(canary not in value for value in denied.headers.values())
    assert integrated_answer._k3e_cached_rev == f"{CANARY}-{'0' * 40}"


def test_p6_flag_off_404_leaks_no_evidence_and_no_cache_canary(monkeypatch, tmp_path) -> None:
    """P6 DENIAL/CACHE (T4c): with the flag off, a G1 root present and the canary caches warm, the
    404 carries no leg evidence, no page SHA, no receipts header and no canary.  The response's
    Cache-Control / Vary are printed for the record: this test asserts only the no-evidence
    property, because the 404 is raised by ``_require_enabled`` (``app/integrated_answer.py:165``),
    not by the private error boundary."""
    gid = _warm_root(monkeypatch, tmp_path)
    canary = _poison_caches(monkeypatch)
    _forbid_compose(monkeypatch)
    auth_calls, entitlement_calls = _allowing_stubs(monkeypatch)
    client = _real_client(monkeypatch, flag_on=False)

    response = client.get(PATH, headers=TOKEN)
    assert response.status_code == 404
    for needle in (*_SHA_NEEDLES, gid, TICKER, SUMMARY_G1, canary):
        assert needle not in response.text, needle
    assert "X-Integrated-Answer-SHA256" not in response.headers
    assert CONSUMED_RECEIPTS_HEADER not in response.headers
    assert auth_calls == []
    assert entitlement_calls == []
    print("WP32-404-HEADERS " + json.dumps(dict(response.headers), sort_keys=True))


def test_p6_compose_wall_time_is_measured_and_reported(monkeypatch, tmp_path) -> None:
    """P6 (T4d): compose latency is measured and reported — 20 sequential
    ``_compose_page_with_receipts`` calls against a G1 root with every seam patched.  The only
    assertion is a generous 5000 ms ceiling: this is a measurement lane, not a performance gate."""
    _warm_root(monkeypatch, tmp_path)
    _patch_all_seams(monkeypatch, ticker=TICKER)
    monkeypatch.setattr(integrated_answer, "_utc_now", lambda: NOW)

    samples_ms: list[float] = []
    for _ in range(20):
        start = time.perf_counter()
        page, entries = integrated_answer._compose_page_with_receipts(TICKER)
        samples_ms.append((time.perf_counter() - start) * 1000.0)
        assert page["ticker"] == TICKER
        assert len(entries) == 6

    ordered = sorted(samples_ms)
    median_ms = ordered[len(ordered) // 2]
    p95_ms = ordered[min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))]
    max_ms = ordered[-1]
    print(
        f"WP32-COMPOSE-LATENCY n={len(samples_ms)} median_ms={median_ms:.3f} "
        f"p95_ms={p95_ms:.3f} max_ms={max_ms:.3f}"
    )
    assert max_ms < 5000.0
