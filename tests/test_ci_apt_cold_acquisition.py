"""Offline orchestration/falsification models, never APT or network execution.

The per-connection model is a hypothesis, not attribution of the hosted rate.
Shared-rate and largest-archive cases explicitly refute universal improvement.
"""
from dataclasses import replace
import hashlib

import pytest

from scripts import ci_apt_cold_acquisition as CORE


def archive(index, size=100):
    name = f"font-fixture-{index}"
    filename = f"{name}_1.0_all.deb"
    return CORE.Archive(name, "1.0", "amd64", "all", filename, size,
                        hashlib.sha256(b"x" * size).hexdigest(),
                        f"http://azure.archive.ubuntu.com/ubuntu/pool/main/f/{name}/{filename}")


class ModelBackend:
    def __init__(self, records, *, rate=100, shared_rate=None, faults=None, elapsed=0):
        self.records = records
        self.rate, self.shared_rate = rate, shared_rate
        self.faults = faults or {}
        self.time = elapsed
        self.remaining = {}
        self.events = []
        self.verified = set()

    def now(self):
        return self.time

    def launch(self, index, argv, deadline):
        assert argv == CORE.download_argv(self.records[index])
        assert self.time < deadline
        self.events.append(("launch", index))
        self.remaining[index] = self.records[index].size
        if self.faults.get(index) == "launch_response_loss":
            raise OSError("effect may already exist")
        return index

    def collect(self, children, deadline):
        self.events.append(("collect", tuple(children)))
        if "collect" in self.faults:
            raise OSError("observer unavailable")
        if any(self.faults.get(i) == "response_loss" for i in children):
            return {i: CORE.ChildResult("failed", "unknown") for i in children}
        speed = min(self.rate, self.shared_rate / len(children)) if self.shared_rate else self.rate
        required = min(self.remaining[i] / speed for i in children)
        interval = min(required, deadline - self.time)
        self.time += interval
        for i in children:
            self.remaining[i] -= speed * interval
        done = {i for i in children if self.remaining[i] <= 0.00001}
        if not done:
            return {i: CORE.ChildResult("timed_out", "unknown") for i in children}
        return {i: CORE.ChildResult("failed" if self.faults.get(i) == "download_failure" else "passed", "settled") for i in done}

    def verify_archive(self, index, expected):
        self.events.append(("verify", index))
        assert expected == self.records[index]
        if self.faults.get(index) in {"hash", "partial", "conflict"}:
            raise CORE.AcquisitionRefused("ARCHIVE_BYTES_CHANGED")
        self.verified.add(index)

    def install_frozen(self, original, deadline):
        self.events.append(("install", original))
        assert tuple(original) == self.records
        assert self.verified == set(range(len(self.records)))
        assert self.time < deadline
        if "transaction" in self.faults:
            raise CORE.AcquisitionRefused("TRANSACTION_CHANGED")
        if "install_response_loss" in self.faults:
            raise OSError("original native install outcome unknown")
        if "install_timeout" in self.faults:
            self.time = deadline
            return CORE.ChildResult("timed_out", "unknown")
        self.time += self.faults.get("install_seconds", 0)
        return CORE.ChildResult("passed", "settled")

    def cleanup_success(self):
        self.events.append(("cleanup",))
        if "cleanup" in self.faults:
            raise OSError("cleanup response lost after install")


def test_empty_cache_miss_downloads_every_archive_without_subset_or_warm_adoption():
    records = tuple(archive(i, 100 + i) for i in range(18))
    plan = CORE.make_download_plan(records)
    backend = ModelBackend(records)
    result = CORE.acquire_and_install(plan, backend, deadline=600)
    assert result.outcome == "passed" and result.installation == "passed"
    launched = [e[1] for e in backend.events if e[0] == "launch"]
    assert set(launched) == set(range(18)) and len(launched) == 18
    assert launched == list(plan.schedule)
    assert [e for e in backend.events if e[0] == "install"] == [("install", records)]
    assert backend.events[-1] == ("cleanup",)
    active = set()
    maximum = 0
    for event in backend.events:
        if event[0] == "launch": active.add(event[1])
        if event[0] == "verify": active.remove(event[1])
        maximum = max(maximum, len(active))
    assert maximum == 4


def test_cold_independent_slow_connections_are_a_falsifiable_improvement_not_a_forecast():
    # Synthetic 25.9MB inventory, including a7.472MB largest archive. This rate
    # model is explicitly conditional, NOT inferred from aggregate hosted rates.
    sizes = [7_472_000, 5_641_000, 3_513_000, 2_993_000, 1_444_000] + [372_076] * 13
    records = tuple(archive(i, n) for i, n in enumerate(sizes))
    serial, parallel = ModelBackend(records, rate=51_800), ModelBackend(records, rate=51_800)
    first = CORE.acquire_and_install(CORE.make_download_plan(records, concurrency=1), serial, deadline=600)
    second = CORE.acquire_and_install(CORE.make_download_plan(records), parallel, deadline=600)
    assert first.installation == second.installation == "passed"
    semantic_seconds = 268
    assert serial.now() + semantic_seconds > 600
    assert parallel.now() + semantic_seconds < 600
    assert len([e for e in parallel.events if e[0] == "launch"]) == len(records)


def test_shared_payload_cap_refutes_parallelism_as_a_universal_rate_fix():
    records = tuple(archive(i, 1_000_000) for i in range(26))
    serial = ModelBackend(records, rate=1_000_000, shared_rate=51_800)
    parallel = ModelBackend(records, rate=1_000_000, shared_rate=51_800)
    CORE.acquire_and_install(CORE.make_download_plan(records, concurrency=1), serial, deadline=600)
    CORE.acquire_and_install(CORE.make_download_plan(records), parallel, deadline=600)
    assert parallel.now() == pytest.approx(serial.now())
    assert parallel.now() + 268 > 600


def test_one_slow_largest_archive_can_exhaust_original_total_without_installation():
    records = (archive(0, 8_000_000), archive(1, 100), archive(2, 100))
    backend = ModelBackend(records, rate=10_000)
    result = CORE.acquire_and_install(CORE.make_download_plan(records), backend, deadline=600)
    assert result.outcome == "timed_out" and result.settlement == "unknown"
    assert result.installation == "never_started"
    assert any(row[1] == "timed_out" for row in result.observations)
    assert not any(e[0] in {"install", "cleanup"} for e in backend.events)


@pytest.mark.parametrize("fault", ["download_failure", "hash", "partial", "conflict", "response_loss", "launch_response_loss"])
def test_download_failure_or_ambiguity_blocks_install_cleanup_and_later_launches(fault):
    records = tuple(archive(i) for i in range(9))
    backend = ModelBackend(records, faults={0: fault})
    result = CORE.acquire_and_install(CORE.make_download_plan(records), backend, deadline=600)
    assert result.outcome == "failed" and result.installation == "never_started"
    assert not any(e[0] in {"install", "cleanup"} for e in backend.events)
    assert len([e for e in backend.events if e[0] == "launch"]) <= 4
    if fault in {"response_loss", "launch_response_loss"}:
        assert result.settlement == "unknown"
    else:
        assert result.settlement == "settled"


def test_planning_elapsed_time_is_charged_to_the_same_deadline():
    records = (archive(0, 10_000),)
    backend = ModelBackend(records, rate=100, elapsed=550)
    result = CORE.acquire_and_install(CORE.make_download_plan(records), backend, deadline=600)
    assert result.outcome == "timed_out" and result.installation == "never_started"
    assert backend.now() == 600


@pytest.mark.parametrize("fault", ["transaction", "install_response_loss", "install_timeout"])
def test_download_completion_cannot_substitute_for_native_installation(fault):
    records = (archive(0),)
    backend = ModelBackend(records, faults={fault: True})
    result = CORE.acquire_and_install(CORE.make_download_plan(records), backend, deadline=600)
    assert result.outcome == ("timed_out" if fault == "install_timeout" else "failed") and result.installation != "passed"
    assert not any(e[0] == "cleanup" for e in backend.events)


def test_cleanup_response_loss_does_not_rewrite_applied_native_installation():
    records = (archive(0),)
    backend = ModelBackend(records, faults={"cleanup": True})
    result = CORE.acquire_and_install(CORE.make_download_plan(records), backend, deadline=600)
    assert result.outcome == "failed" and result.settlement == "unknown"
    assert result.installation == "passed" and result.reason == "CLEANUP_RESPONSE_UNKNOWN"


def test_expired_budget_after_native_install_preserves_applied_outcome_without_cleanup():
    records = (archive(0),)
    backend = ModelBackend(records, faults={"install_seconds": 600})
    result = CORE.acquire_and_install(CORE.make_download_plan(records), backend, deadline=600)
    assert result.outcome == "timed_out" and result.installation == "passed"
    assert not any(e[0] == "cleanup" for e in backend.events)


@pytest.mark.parametrize("change", [
    {"uri": "https://foreign.invalid/ubuntu/pool/font.deb"},
    {"uri": "http://user:SECRET@azure.archive.ubuntu.com/ubuntu/pool/font.deb"},
    {"filename": "../font.deb"}, {"size": 0}, {"sha256": "bad"},
    {"version": "1.0;command"}, {"package_architecture": "amd64 --unsafe"},
])
def test_archive_plan_refuses_malformed_foreign_or_unbounded_inputs_without_echo(change):
    with pytest.raises(CORE.AcquisitionRefused) as caught:
        CORE.make_download_plan((replace(archive(0), **change),))
    assert "SECRET" not in str(caught.value)


def test_duplicate_archives_and_modified_scheduling_plan_are_rejected():
    item = archive(0)
    with pytest.raises(CORE.AcquisitionRefused):
        CORE.make_download_plan((item, item))
    records = (item, archive(1, 200))
    plan = CORE.make_download_plan(records)
    with pytest.raises(CORE.AcquisitionRefused):
        CORE.acquire_and_install(replace(plan, schedule=(0,)), ModelBackend(records), deadline=600)


def test_download_command_keeps_native_authentication_and_exact_version_architecture():
    argv = CORE.download_argv(archive(0))
    assert argv == ("/usr/bin/apt-get", "-o", "APT::Get::AllowUnauthenticated=false", "download", "font-fixture-0:amd64=1.0")
    assert not any(value in argv for value in ("--allow-unauthenticated", "--fix-missing", "--ignore-missing"))


def test_synthetic_payload_verification_refuses_partial_or_replaced_bytes():
    item = archive(0, 100)
    CORE.verify_payload(item, b"x" * 100)
    for payload in (b"x" * 99, b"y" * 100):
        with pytest.raises(CORE.AcquisitionRefused):
            CORE.verify_payload(item, payload)


def test_retained_censored_largest_archive_retry_is_not_a_completion_rate_or_manual_retry():
    # Original A39851544472:7.472MB font Get21:04:01, Ign21:07:07,
    # native retry21:08:41, original deadline21:08:58. No completed archive.
    # Rebase these observed events to one existing acquisition interval; this
    # models censored progress only, never extrapolates a known transfer rate.
    records = (archive(0, 7_472_000), archive(1, 3_513_000), archive(2, 5_641_000), archive(3, 2_993_000))
    class Censored(ModelBackend):
        def collect(self, children, deadline):
            self.events += [("native_get", 0, 303), ("native_ign", 0, 489), ("native_retry", 0, 583)]
            self.time = deadline
            return {i: CORE.ChildResult("timed_out", "unknown") for i in children}
    backend = Censored(records, elapsed=303)
    result = CORE.acquire_and_install(CORE.make_download_plan(records), backend, deadline=600)
    assert [event for event in backend.events if event == ("launch", 0)] == [("launch", 0)]
    assert result.outcome == "timed_out" and result.settlement == "unknown"
    assert result.installation == "never_started" and 0 in result.pending
    assert not any(event[0] in {"install", "cleanup"} for event in backend.events)


class CompletionBackend(ModelBackend):
    def complete_native_transaction(self, original, attempt, deadline):
        self.events.append(('complete-native',attempt,deadline))
        assert attempt.installation=='never_started' and attempt.settlement=='settled' and not attempt.pending
        assert tuple(original)==self.records and self.time<deadline
        fault=self.faults.get('completion')
        if fault=='not-admitted':return None
        if fault=='response-loss':raise OSError('original completion may exist')
        if fault=='unknown':return CORE.ChildResult('failed','unknown')
        if fault=='deadline':self.time=deadline;return CORE.ChildResult('timed_out','unknown')
        self.verified=set(range(len(self.records)))
        return CORE.ChildResult('passed','settled')


def test_settled_native_completion_preserves_verified_progress_and_original_failure():
    records=tuple(archive(i) for i in range(6))
    backend=CompletionBackend(records,faults={0:'download_failure'})
    result=CORE.acquire_and_install(CORE.make_download_plan(records),backend,deadline=600)
    assert result.outcome=='passed' and result.installation=='passed'
    assert result.initial_download_failure=='NATIVE_DOWNLOAD_FAILED'
    assert result.completion==CORE.ChildResult('passed','settled')
    event=next(e for e in backend.events if e[0]=='complete-native')
    assert set(event[1].completed)=={1,2,3} and event[2]==600
    assert (0,'failed','settled') in result.observations
    assert len([e for e in backend.events if e[0]=='complete-native'])==1
    assert len([e for e in backend.events if e[0]=='launch'])==4  # queued payloads go to native transaction, not selector retries


@pytest.mark.parametrize('fault',['response_loss','hash','partial','conflict','launch_response_loss'])
def test_native_completion_never_follows_unknown_or_validation_failure(fault):
    records=tuple(archive(i) for i in range(6));backend=CompletionBackend(records,faults={0:'download_failure',1:fault})
    result=CORE.acquire_and_install(CORE.make_download_plan(records),backend,deadline=600)
    assert result.outcome!='passed'
    assert not any(e[0] in {'complete-native','install','cleanup'} for e in backend.events)


@pytest.mark.parametrize('fault',['not-admitted','response-loss','unknown','deadline'])
def test_native_completion_refusal_loss_and_deadline_never_install_or_cleanup(fault):
    records=tuple(archive(i) for i in range(6));backend=CompletionBackend(records,faults={0:'download_failure','completion':fault})
    result=CORE.acquire_and_install(CORE.make_download_plan(records),backend,deadline=600)
    assert result.outcome!='passed' and result.installation=='never_started'
    assert not any(e[0] in {'install','cleanup'} for e in backend.events)
    assert len([e for e in backend.events if e[0]=='complete-native'])==1
    if fault!='not-admitted':assert result.settlement=='unknown' and result.initial_download_failure=='NATIVE_DOWNLOAD_FAILED'
