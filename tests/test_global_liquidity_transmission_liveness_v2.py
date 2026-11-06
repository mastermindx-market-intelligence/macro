"""GLT T06 liveness discriminators (v2 namespace) — C11 + C12.

The W-LIQ.1 producer (#6296) and the Mastermind reader (#914) are frozen. This
file adds NO producer or reader behaviour: it pins three facts about the path
between them, reading the TRACKED artifact and never writing any v1 output.

* C11 — a tracked artifact whose ``freshness.clocks.evidence_available_at`` is
  older than the staleness window evaluates STALE under the reader ageing law,
  on both readers that consume it: the Mastermind consumer law (mirrored here,
  see ``_consumer_verdict``) and the Macro workspace reader
  (``liquidity_central_banks.compose``), which is imported and run for real.
  A future-dated evidence clock is rejected by both.
* C12 — a wrapper, or a new ``meta.generated_at`` (or any non-evidence clock),
  cannot certify freshness. Neither can the producer's own ``status: fresh``
  frozen into a checked-in file: that status was judged when the file was made.
* Liveness root cause — no workflow ever ran the producer (its only .github
  reference was a CI test lane's ``paths:`` filter); the nightly engine job now
  runs it, non-fatally, after its inputs exist, and the engine commit step
  stages its outputs.

Every age is computed RELATIVE to the tracked artifact's own clocks, so the
nightly advancing the artifact never breaks these tests.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
import yaml

from engine.market_os.macro_workspaces import liquidity_central_banks as lcb

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "site" / "liquiditydata" / "global_liquidity_transmission.json"
DAILY = ROOT / ".github" / "workflows" / "daily.yml"
ENGINE_COMMIT = ROOT / "scripts" / "ci" / "daily_engine_commit_outputs.sh"

# Mirror of the frozen Mastermind consumer law: brain/liquidity_transmission.py
# (_freshness_verdict; _STALE_DAYS / _OBSERVED_AT_FIELD / _KNOWN_AT_FIELD) at
# Mastermind master 08597860f (2026-09-22). Macro cannot import Mastermind, so
# the law is restated here; the artifact itself names the same two fields
# (pinned by test_producer_names_the_evidence_clock_as_the_ageing_field).
CONSUMER_STALE_DAYS = 10
OBSERVED_AT_FIELD = "evidence_available_at"
KNOWN_AT_FIELD = "first_known_at"

pytestmark = pytest.mark.needs_full_checkout("site")


def _parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _consumer_verdict(raw: dict[str, Any], now: datetime) -> tuple[bool, str]:
    """(stale, reason) under the mirrored consumer law — fail-closed."""
    clocks = (raw.get("freshness") or {}).get("clocks") or {}
    observed = _parse_ts(clocks.get(OBSERVED_AT_FIELD))
    known = _parse_ts(clocks.get(KNOWN_AT_FIELD))
    if observed is None:
        return True, "unparseable evidence clock"
    age = (now - observed).total_seconds() / 86400.0
    if age < 0:
        return True, "future-dated evidence clock"
    if age > CONSUMER_STALE_DAYS:
        return True, f"age {age:.2f}d > {CONSUMER_STALE_DAYS}d"
    if known is not None and observed > known:
        return True, "evidence clock postdates known clock"
    if (raw.get("freshness") or {}).get("status") != "fresh":
        return True, "producer not fresh"
    return False, "ok"


def _workspace_verdict(raw: dict[str, Any], built_at: datetime) -> str:
    """The real Macro reader: compose() and read its glt_state source row."""
    body = lcb.compose(raw, {}, built_at=built_at.date().isoformat())
    rows = {row.get("source_id"): row for row in body["sources"]["items"]}
    return rows["glt_state"]["freshness"]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def tracked() -> dict[str, Any]:
    before = _sha(ARTIFACT)
    raw = json.loads(ARTIFACT.read_text())
    yield raw
    assert _sha(ARTIFACT) == before, "a liveness test mutated the tracked v1 artifact"


def _evidence(raw: dict[str, Any]) -> datetime:
    ts = _parse_ts(raw["freshness"]["clocks"][OBSERVED_AT_FIELD])
    assert ts is not None
    return ts


def _owner_fresh_copy(raw: dict[str, Any]) -> dict[str, Any]:
    """In-memory copy whose producer status is fresh, so an in-window verdict
    tests ageing alone (a degraded nightly must not flake the positive case)."""
    out = copy.deepcopy(raw)
    out["freshness"]["status"] = "fresh"
    out["freshness"]["degraded"] = False
    return out


def _august_copy(raw: dict[str, Any]) -> dict[str, Any]:
    """The artifact as it stood from 2026-09-04 to this fix: evidence frozen at
    2026-08-28 by the manual regeneration at 7fb785ee07b8."""
    out = _owner_fresh_copy(raw)
    clocks = out["freshness"]["clocks"]
    clocks[OBSERVED_AT_FIELD] = "2026-08-28T00:00:00Z"
    clocks[KNOWN_AT_FIELD] = "2026-09-04T11:03:41.497178Z"
    out["state"]["asof"] = "2026-08-28"
    out["meta"]["generated_at"] = "2026-09-04T11:03:41.497178+00:00"
    return out


def test_producer_names_the_evidence_clock_as_the_ageing_field(tracked) -> None:
    clocks = tracked["freshness"]["clocks"]
    assert clocks["adapter_observed_at_field"] == OBSERVED_AT_FIELD
    assert clocks["adapter_known_at_field"] == KNOWN_AT_FIELD
    assert OBSERVED_AT_FIELD in clocks and KNOWN_AT_FIELD in clocks
    # generated_at is a meta stamp, never the ageing clock.
    assert "generated_at" not in clocks
    assert clocks["adapter_observed_at_field"] != "generated_at"


def test_c11_tracked_artifact_past_the_window_is_stale_on_the_consumer_law(tracked) -> None:
    evidence = _evidence(tracked)
    fresh = _owner_fresh_copy(tracked)
    assert _consumer_verdict(fresh, evidence + timedelta(days=1)) == (False, "ok")
    stale, reason = _consumer_verdict(
        tracked, evidence + timedelta(days=CONSUMER_STALE_DAYS, hours=1)
    )
    assert stale and reason.startswith("age ")
    stale, reason = _consumer_verdict(tracked, evidence - timedelta(days=1))
    assert stale and reason == "future-dated evidence clock"


def test_c11_tracked_artifact_past_the_window_is_stale_on_the_workspace_reader(tracked) -> None:
    asof = datetime.fromisoformat(tracked["state"]["asof"]).replace(tzinfo=timezone.utc)
    fresh = _owner_fresh_copy(tracked)
    assert _workspace_verdict(fresh, asof) == "CURRENT"
    window = lcb._GLT_CADENCE_DAYS + lcb._GLT_RELEASE_GRACE_DAYS
    assert _workspace_verdict(tracked, asof + timedelta(days=window + 1)) == "STALE_SOURCE"
    assert _workspace_verdict(tracked, asof - timedelta(days=1)) == "SOURCE_FAILED"


def test_c11_the_august_artifact_is_not_current_proof(tracked) -> None:
    august = _august_copy(tracked)
    t06 = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)
    stale, reason = _consumer_verdict(august, t06)
    assert stale and reason.startswith("age ")
    assert _workspace_verdict(august, t06) == "STALE_SOURCE"
    # Its own frozen status still reads fresh — that is the trap C12 closes.
    assert august["freshness"]["status"] == "fresh"


def test_c12_a_new_generated_at_cannot_certify_freshness(tracked) -> None:
    evidence = _evidence(tracked)
    now = evidence + timedelta(days=30)
    restamped = _owner_fresh_copy(tracked)
    stamp = now.isoformat().replace("+00:00", "Z")
    restamped["meta"]["generated_at"] = now.isoformat()
    clocks = restamped["freshness"]["clocks"]
    for non_evidence in ("monetary_release_at", "latest_component_observed_at", "state_asof"):
        clocks[non_evidence] = stamp
    clocks[KNOWN_AT_FIELD] = stamp
    assert _consumer_verdict(restamped, now)[0] is True
    assert _workspace_verdict(restamped, now) == "STALE_SOURCE"


def test_c12_a_wrapper_cannot_certify_freshness(tracked) -> None:
    now = _evidence(tracked) + timedelta(days=1)
    wrapper = {
        "schema": "glt_freshness_wrapper.v0",
        "generated_at": now.isoformat(),
        "status": "fresh",
        "payload": copy.deepcopy(tracked),
    }
    stale, reason = _consumer_verdict(wrapper, now)
    assert stale and reason == "unparseable evidence clock"
    assert _workspace_verdict(wrapper, now) == "SOURCE_FAILED"


def _engine_steps() -> list[dict[str, Any]]:
    wf = yaml.safe_load(DAILY.read_text())
    return wf["jobs"]["engine"]["steps"]


def test_nightly_engine_job_runs_the_producer_after_its_inputs_non_fatally() -> None:
    steps = _engine_steps()
    runs = [str(step.get("run") or "") for step in steps]
    glt = [i for i, run in enumerate(runs) if "scripts.build_global_liquidity_transmission" in run]
    assert len(glt) == 1, "exactly one nightly invocation of the GLT producer"
    i = glt[0]
    step = steps[i]
    assert "if" not in step, "the producer step must not be gated off"
    assert re.search(
        r"python -m scripts\.build_global_liquidity_transmission \|\| echo \"::warning::", runs[i]
    ), "non-fatal sibling idiom: last committed artifact stands on failure"
    plumbing = [j for j, run in enumerate(runs) if "scripts.build_liquidity_plumbing" in run]
    assert plumbing and plumbing[0] < i, "runs after the step that already needs regime/latest.json"


def test_engine_commit_step_stages_the_producer_outputs() -> None:
    text = ENGINE_COMMIT.read_text()
    assert re.search(r"^\s*git add data/ site/", text, re.M)
    for path in ("data/global_liquidity_transmission", "site/liquiditydata"):
        assert not re.search(rf"git (checkout|reset|rm)[^\n]*{re.escape(path)}", text)
