"""Resource readings must distinguish utilization, queueing and retained swap."""
from __future__ import annotations

import io
import json
import subprocess
from types import SimpleNamespace

import pytest

from admin import services, system


@pytest.fixture(autouse=True)
def reset_sampling(monkeypatch):
    monkeypatch.setattr(system, "_PREVIOUS", None)
    monkeypatch.setattr(system, "_LAST_ACTIVITY", None)


def samples(monkeypatch, clocks, cpus, swaps):
    clock, cpu, swap = iter(clocks), iter(cpus), iter(swaps)
    monkeypatch.setattr(system.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(system, "_cpu_counters", lambda: next(cpu))
    monkeypatch.setattr(system, "_swap_counters", lambda: next(swap))
    monkeypatch.setattr(system.os, "sysconf", lambda name: 4096)


def test_first_sample_is_unknown_not_idle(monkeypatch):
    samples(monkeypatch, [1.0], [(1, 2, 3, 4, 5, 6, 7, 8)], [(10, 20)])
    assert all(value is None for value in system._activity().values())


def test_cpu_busy_excludes_io_wait_and_steal(monkeypatch):
    baseline = (100, 20, 30, 800, 20, 5, 5, 20)
    delta = (20, 5, 10, 45, 10, 3, 2, 5)
    samples(monkeypatch, [10.0, 12.0], [baseline, tuple(a + b for a, b in zip(baseline, delta))],
            [(100, 200), (102, 204)])
    system._activity()
    result = system._activity()
    assert result == {"utilization_pct": 40.0, "iowait_pct": 10.0, "steal_pct": 5.0,
                      "sample_seconds": 2.0, "swap_in_bytes_per_second": 4096.0,
                      "swap_out_bytes_per_second": 8192.0}


def test_fast_callers_do_not_destroy_interval(monkeypatch):
    samples(monkeypatch, [1, 1.1, 2], [(10,) * 8, (11,) * 8, (20,) * 8], [(1, 1)] * 3)
    system._activity()
    assert system._activity()["sample_seconds"] is None
    assert system._activity()["sample_seconds"] == 1


def test_cached_activity_is_not_mutable_by_caller(monkeypatch):
    samples(monkeypatch, [1, 2, 2.1], [(10,) * 8, (20,) * 8, (21,) * 8], [(0, 0)] * 3)
    system._activity()
    result = system._activity()
    result["utilization_pct"] = 999
    assert system._activity()["utilization_pct"] == 62.5


@pytest.mark.parametrize("last_clock,last_cpu", [(0, (20,) * 8), (2, (1,) * 8), (2, (10,) * 8)])
def test_counter_or_clock_resets_never_fabricate_usage(monkeypatch, last_clock, last_cpu):
    samples(monkeypatch, [1, last_clock], [(10,) * 8, last_cpu], [(10, 10), (20, 20)])
    system._activity()
    assert all(value is None for value in system._activity().values())


def test_swap_reset_does_not_destroy_valid_cpu(monkeypatch):
    samples(monkeypatch, [1, 2], [(10,) * 8, (20,) * 8], [(100, 200), (1, 2)])
    system._activity()
    result = system._activity()
    assert result["utilization_pct"] == 62.5
    assert result["swap_in_bytes_per_second"] is None


def test_unavailable_proc_does_not_reuse_stale_usage(monkeypatch):
    samples(monkeypatch, [1, 2, 3, 4], [(10,) * 8, (20,) * 8, None, (40,) * 8], [(1, 1)] * 4)
    system._activity(); assert system._activity()["utilization_pct"] is not None
    assert system._activity()["utilization_pct"] is None
    assert system._activity()["utilization_pct"] is None


def test_cpu_guest_counters_are_not_double_counted(monkeypatch):
    monkeypatch.setattr("builtins.open", lambda *args, **kwargs: io.StringIO("cpu 1 2 3 4 5 6 7 8 900 901\n"))
    assert system._cpu_counters() == (1, 2, 3, 4, 5, 6, 7, 8)


@pytest.mark.parametrize("text", ["", "cpu bad\n", "cpu 1 2 3\n", "cpu 1 2 3 4 5 6 7 -1\n"])
def test_bad_cpu_counters_are_unknown(monkeypatch, text):
    monkeypatch.setattr("builtins.open", lambda *args, **kwargs: io.StringIO(text))
    assert system._cpu_counters() is None


def test_pressure_reading_and_nonfinite_refusal(monkeypatch):
    def source(path):
        return io.StringIO("some avg10=1.25 avg60=2.50 avg300=3.75 total=123\n" if path.endswith("/cpu")
                           else "some avg10=nan avg60=0 avg300=0 total=0\n")
    monkeypatch.setattr("builtins.open", source)
    value = system._pressure()
    assert value["cpu"]["some"]["avg10"] == 1.25
    assert value["memory"] is None and value["io"] is None


def test_load_above_core_count_is_not_cpu_percentage(monkeypatch):
    monkeypatch.setattr(system.os.path, "exists", lambda p: True)
    monkeypatch.setattr(system.os, "cpu_count", lambda: 2)
    monkeypatch.setattr(system.os, "getloadavg", lambda: (4.73, 4.16, 2.95))
    monkeypatch.setattr(system, "_activity", lambda: dict(system._unknown_activity(), utilization_pct=32.5))
    monkeypatch.setattr(system, "_pressure", lambda: {})
    monkeypatch.setattr(system, "_meminfo", lambda: {"MemTotal": 100, "MemAvailable": 30, "SwapTotal": 50, "SwapFree": 10})
    monkeypatch.setattr(system, "_uptime_s", lambda: 42)
    monkeypatch.setattr(system.shutil, "disk_usage", lambda p: SimpleNamespace(total=100, used=80, free=20))
    result = system.snapshot()
    assert result["cpu"]["load1_pct"] == 236.5
    assert result["cpu"]["utilization_pct"] == 32.5
    assert result["swap"]["used"] == 40
    assert result["swap"]["in_bytes_per_second"] is None


def service_ready(**overrides):
    return {"LoadState": "loaded", "ActiveState": "active", "SubState": "running",
            "MemoryCurrent": "300", "MemorySwapCurrent": "1000", "MemoryPeak": "500",
            "NRestarts": "0", "Result": "success", **overrides}


def arrange_services(monkeypatch, failed=None, response=None):
    monkeypatch.setattr(services.shutil, "which", lambda name: "/bin/systemctl")
    monkeypatch.setattr(services, "_show", lambda unit: service_ready() if response is None else response)
    monkeypatch.setattr(services, "_failed_units", lambda: failed if failed is not None else
                        {"available": True, "count": 0, "units": [], "truncated": False})


def test_service_memory_includes_swap_and_scan_is_explicit(monkeypatch):
    arrange_services(monkeypatch)
    result = services.status()
    assert result["healthy"] is True and result["core_healthy"] is True
    assert result["services"][0]["memory_including_swap"] == 1300
    assert result["services"][0]["swap_memory"] == 1000
    assert result["failed_jobs"]["count"] == 0


def test_core_green_does_not_hide_failed_scheduled_jobs(monkeypatch):
    arrange_services(monkeypatch, failed={"available": True, "count": 4, "units": [], "truncated": False})
    result = services.status()
    assert result["ok_count"] == 5 and result["core_healthy"] is True
    assert result["healthy"] is False


def test_failed_scan_is_unknown_not_all_clear(monkeypatch):
    arrange_services(monkeypatch, failed={"available": False, "count": None, "units": [], "truncated": False})
    result = services.status()
    assert result["core_healthy"] is True and result["healthy"] is None


def test_known_failure_wins_over_partial_inspection(monkeypatch):
    arrange_services(monkeypatch, failed={"available": True, "count": 1, "units": [], "truncated": False}, response={"_error": "unavailable"})
    assert services.status()["healthy"] is False


def test_missing_configured_core_is_unhealthy(monkeypatch):
    arrange_services(monkeypatch, response=service_ready(LoadState="not-found", ActiveState="inactive"))
    assert services.status()["healthy"] is False


@pytest.mark.parametrize("value", [None, "[not set]", "infinity", "18446744073709551615", "-1"])
def test_unset_memory_is_not_zero_or_exabytes(value):
    assert services._uint(value) is None


def test_failed_unit_inventory_is_bounded_without_losing_count(monkeypatch):
    rows = [{"unit": f"job-{i:02}.service", "active": "failed", "sub": "failed", "description": "job"} for i in range(30)]
    monkeypatch.setattr(services.subprocess, "run", lambda *a, **kw: SimpleNamespace(returncode=0, stdout=json.dumps(rows)))
    result = services._failed_units()
    assert result["count"] == 30 and len(result["units"]) == 25 and result["truncated"] is True


@pytest.mark.parametrize("data", ["not JSON", "{}", "[{}]", '[{"unit":"job.service","active":"active"}]'])
def test_malformed_failed_inventory_is_unknown(monkeypatch, data):
    monkeypatch.setattr(services.subprocess, "run", lambda *a, **kw: SimpleNamespace(returncode=0, stdout=data))
    assert services._failed_units()["available"] is False


def test_service_show_nonzero_cannot_be_healthy(monkeypatch):
    monkeypatch.setattr(services.subprocess, "run", lambda *a, **kw: SimpleNamespace(returncode=1, stdout="ActiveState=active\n"))
    assert services._show("example.service").get("_error")


def test_missing_systemctl_is_explicit(monkeypatch):
    monkeypatch.setattr(services.shutil, "which", lambda name: None)
    assert services.status()["available"] is False


def test_failed_inventory_timeout_is_explicit(monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("systemctl", 5)
    monkeypatch.setattr(services.subprocess, "run", timeout)
    assert services._failed_units()["count"] is None


def test_partial_core_scan_cannot_hide_known_failure(monkeypatch):
    arrange_services(monkeypatch)
    monkeypatch.setattr(services, "_show", lambda unit: service_ready(ActiveState="failed")
                        if unit == "macro-api.service" else {"_error": "unavailable"})
    assert services.status()["healthy"] is False


def test_non_ascii_digit_is_not_a_systemd_number():
    assert services._uint("\u00b2") is None


def test_zero_usage_remains_a_real_measurement(monkeypatch):
    samples(monkeypatch, [1, 2], [(0, 0, 0, 100, 0, 0, 0, 0),
                                (0, 0, 0, 200, 0, 0, 0, 0)], [(2, 3), (2, 3)])
    system._activity()
    result = system._activity()
    assert result["utilization_pct"] == 0
    assert result["swap_in_bytes_per_second"] == 0


def test_api_memory_bounds_keep_existing_recovery_and_isolation():
    from pathlib import Path
    text = (Path(__file__).resolve().parents[1] / "app/deploy/macro-api.service").read_text()
    for line in ("MemoryAccounting=yes", "MemoryHigh=1536M", "MemoryMax=3G", "MemorySwapMax=4G",
                 "Restart=always", "ProtectSystem=full", "ProtectHome=true",
                 "InaccessiblePaths=/var/lib/macro-market-memory/state"):
        assert line in text.splitlines()
    assert "RuntimeMaxSec=" not in text  # no timer-driven service churn


@pytest.mark.parametrize("lane,quota,timeout", [("fast", "100%", "150"), ("snapshot", "50%", "420")])
def test_cpu_burst_limits_preserve_lane_owner_and_deadline(lane, quota, timeout):
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    text = (root / f"app/deploy/macro-live-{lane}.service").read_text()
    assert f"CPUQuota={quota}" in text.splitlines()
    assert f"TimeoutStartSec={timeout}" in text.splitlines()
    assert f"ExecStart=/opt/macro/.venv/bin/python -m scripts.vps_live_orchestrator --lane {lane}" in text.splitlines()
    assert "Type=oneshot" in text.splitlines()


def test_system_ui_keeps_load_usage_swap_and_failed_jobs_distinct():
    from pathlib import Path
    import shutil
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for source-backed admin renderer validation")
    source = (Path(__file__).resolve().parents[1] / "admin/static/app.js").read_text()
    start = source.index("/* ---- SYSTEM + SERVICES + UPTIME ")
    end = source.index("/* ---- FEATURES ", start)
    harness = r'''const assert = require('node:assert/strict'); const RENDER={}; let SUMMARY={}; let meters=[];
const nodes={}; const $=id=>nodes[id] || (nodes[id]={innerHTML:'',children:[],appendChild(x){this.children.push(x);}});
const esc=x=>String(x ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
const fmtBytes=x=>String(x ?? '?')+' B'; const h=x=>x;
const meter=(name,pct,value)=>{meters.push({name,pct});return name+': '+value;};
const api=async()=>({targets:[{label:'web',ok:true,status:200,ms:20}]});
'''
    assertions = r'''(async()=>{
 SUMMARY={system:{available:true,cpu:{count:2,load1:4.73,load5:4.16,load15:2.95,load1_ratio:2.365},swap:{used:120,total:160,used_pct:75}},services:{available:true,ok_count:5,total:5,services:[{label:'API',unit:'macro-api.service',ok:true,active:'active',memory:300,swap_memory:1000}],failed_jobs:{available:true,count:1,units:[{unit:'sentinel.service',description:'<script>bad</script>'}]}}};
 await RENDER.system(); let html=$('#view').innerHTML;
 assert.match(html,/awaiting two kernel samples/);assert(!meters.some(x=>x.name==='CPU utilization'));
 assert.match(html,/4\.73 \/ 4\.16 \/ 2\.95/);assert.match(html,/2\.37/);assert.match(html,/not CPU percent/);
 assert.match(html,/1 failed unit/);assert(!html.includes('<script>'));assert.match(html,/&lt;script&gt;/);
 assert.match($('#svcs').children.join(''),/RAM 300 B.*swap 1000 B/);
 SUMMARY.system.cpu.utilization_pct=32.5;SUMMARY.system.cpu.sample_seconds=2;
 SUMMARY.system.swap.in_bytes_per_second=0;SUMMARY.system.swap.out_bytes_per_second=4096;
 await RENDER.system();assert.deepEqual(meters.filter(x=>x.name==='CPU utilization').pop(),{name:'CPU utilization',pct:32.5});
 assert.match($('#view').innerHTML,/Swap I\/O: in 0 B\/s/);
 SUMMARY.services.failed_jobs={available:false};await RENDER.system();assert.match($('#view').innerHTML,/not an all-clear/);
 SUMMARY.services.failed_jobs={available:true,count:0,units:[]};await RENDER.system();assert.match($('#view').innerHTML,/does not certify data freshness/);
 SUMMARY={};await RENDER.system();assert.match($('#view').innerHTML,/Server stats are only available/);
 await $('#upBtn').onclick();assert.match($('#upBoard').innerHTML,/200/);
})().catch(e=>{console.error(e);process.exit(1);});'''
    run = subprocess.run([node, "-"], input=harness + source[start:end] + assertions,
                         text=True, capture_output=True, timeout=15)
    assert run.returncode == 0, run.stderr
