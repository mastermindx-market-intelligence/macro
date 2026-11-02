"""Hermetic tests for the Prophet B23 latency report generator (BU5).

No browser, no socket, no clock: manifest and journal fixtures are built in
these files to the exact shape ``scripts/capture_page_evidence.py`` (B23 BU1)
and ``scripts/prophet_journey_lab_serve.py`` emit, and every FROZEN SPEC item
of the BU5 packet maps to one named test. The committed spec
``config/prophet_journey_latency.yml`` is the matrix under test, so its budgets
and required N are pinned, not paraphrased.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "prophet_journey_latency_report.py"
COMMITTED_SPEC = ROOT / "config" / "prophet_journey_latency.yml"


def _load_module():
    spec = importlib.util.spec_from_file_location("prophet_journey_latency_report_under_test", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


pjr = _load_module()
SPEC = pjr.load_spec(COMMITTED_SPEC)

RUN_TIME = "2026-10-21T09:00:00Z"
ROUTE = "/index.html"  # journey step "landing"
CLOSED_VERDICTS = {"PASS", "FAIL", "INSUFFICIENT_SAMPLES", "GAP"}


# ---------------------------------------------------------------------------
# fixtures: BU1-shaped manifests and BU4-shaped journals
# ---------------------------------------------------------------------------


def _timing(
    *,
    lcp_ms=None,
    cls=None,
    inp_proxy_ms=None,
    resource_count=None,
    transfer_bytes=None,
    server_timing=None,
):
    return {
        "lcp_ms": lcp_ms,
        "cls": cls,
        "inp_proxy_ms": inp_proxy_ms,
        "resource_count": resource_count,
        "transfer_bytes": transfer_bytes,
        "server_timing": server_timing,
    }


def _state(width, locale, theme, timing=None, *, captured=True, reason=None, force_state=None):
    state = {
        "viewport": "mobile",
        "locale": locale,
        "theme": theme,
        "access": "anonymous",
        "viewport_width": width,
        "viewport_height": 844,
        "force_state": force_state,
        "timing": timing if timing is not None else _timing(),
    }
    if captured:
        state.update(
            {
                "captured": True,
                "file": "evidence/0000.png",
                "sha256": "0" * 64,
                "bytes": 100,
                "width": 10,
                "height": 10,
                "applied_theme": theme,
                "applied_locale": locale,
            }
        )
    else:
        state.update({"captured": False, "reason": reason or "page did not load"})
    return state


def _page(route, states, *, console_errors=(), failed_responses=(), gaps=()):
    return {
        "page_id": "p0-1",
        "route": route,
        "registry_route": route,
        "route_kind": "",
        "states": list(states),
        "metrics": {},
        "console_errors": list(console_errors),
        "failed_responses": list(failed_responses),
        "gaps": list(gaps),
    }


def _write_manifest(
    tmp_path: Path,
    name: str,
    pages,
    *,
    timing_basis: str = "lab",
    schema: str = pjr.MANIFEST_SCHEMA,
) -> Path:
    manifest = {
        "schema": schema,
        "generated_at": "2026-10-21T08:00:00Z",
        "tool": {"module_ref": "scripts/capture_page_evidence.py", "version": "1.4.0"},
        "target": {},
        "axes": {
            "viewports": {"mobile": [390, 844]},
            "locales": ["en", "zh"],
            "themes": ["light", "dark"],
            "access": ["anonymous"],
            "force_states": [],
        },
        "timing_basis": timing_basis,
        "selection": {},
        "excluded": [],
        "outcome": "captured",
        "totals": {"pages": len(pages), "states_attempted": 0, "states_captured": 0},
        "honesty": {},
        "pages": list(pages),
    }
    path = tmp_path / name
    path.write_text(json.dumps(manifest, sort_keys=True, indent=2), encoding="utf-8")
    return path


def _write_journal(tmp_path: Path, name: str, rows) -> Path:
    path = tmp_path / name
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    return path


def _journal_row(seq, path, *, status=200, elapsed_ms=1.0, method="GET", size=100):
    return {
        "seq": seq,
        "method": method,
        "path": path,
        "status": status,
        "bytes": size,
        "elapsed_ms": elapsed_ms,
        "sha256": "0" * 64,
    }


def _cold_loads(tmp_path, count, *, route=ROUTE, width=320, locale="en", theme="light", timing_fn=None):
    """`count` manifests, each one cold load of one cell — the real run shape."""

    timing_fn = timing_fn or (lambda i: _timing(
        lcp_ms=100 + i, cls=0.01, inp_proxy_ms=50 + i,
        resource_count=10 + (i % 3), transfer_bytes=50_000 + 100 * i,
    ))
    paths = []
    for i in range(count):
        path = _write_manifest(
            tmp_path,
            f"run-{i:03d}.json",
            [_page(route, [_state(width, locale, theme, timing_fn(i))])],
        )
        paths.append(path)
    return paths


def _build(tmp_path, manifests, journals=(), run_time=RUN_TIME):
    return pjr.build_report(
        spec=SPEC,
        spec_path=COMMITTED_SPEC,
        manifest_paths=list(manifests),
        journal_paths=list(journals),
        run_time=run_time,
    )


def _cell(report, *, step="landing", width=320, locale="en", theme="light"):
    for cell in report["cells"]:
        if (
            cell["step"] == step
            and cell["width"] == width
            and cell["locale"] == locale
            and cell["theme"] == theme
        ):
            return cell
    raise AssertionError(f"cell {step}/{width}/{locale}/{theme} missing from report")


# ---------------------------------------------------------------------------
# FROZEN SPEC items
# ---------------------------------------------------------------------------


def test_spec1_every_metric_carries_basis_and_n_insufficient_never_p75(tmp_path):
    """FROZEN SPEC 1: basis + N on every metric; short cells never emit a p75."""

    report = _build(tmp_path, _cold_loads(tmp_path, 24))
    cell = _cell(report)
    for label, block in cell["metrics"].items():
        assert block["basis"] == "lab", label
        assert isinstance(block["n"], int), label
    lcp = cell["metrics"]["lab_p75_lcp_ms"]
    assert lcp["verdict"] == "INSUFFICIENT_SAMPLES"
    assert lcp["n"] == 24 and lcp["required_n"] == 25 and lcp["null_count"] == 0
    assert lcp["p75"] is None, "an insufficient cell must never report a p75"
    assert cell["verdict"] == "INSUFFICIENT_SAMPLES"

    # The 25th cold load is what the design's N=25 asks for; then a p75 exists.
    report25 = _build(tmp_path, _cold_loads(tmp_path, 25))
    lcp25 = _cell(report25)["metrics"]["lab_p75_lcp_ms"]
    assert lcp25["verdict"] == "PASS"
    assert lcp25["n"] == 25
    assert lcp25["p75"] == pjr.p75_nearest_rank([100 + i for i in range(25)])


def test_spec2_p75_nearest_rank_known_vectors_n1_4_25_30():
    """FROZEN SPEC 2: nearest rank ceil(0.75*n), 1-based, on sorted values."""

    # Ascending vectors 1..n: rank is 1, 3, 19, 23 for n = 1, 4, 25, 30.
    assert pjr.p75_nearest_rank([5]) == 5
    assert pjr.p75_nearest_rank([1, 2, 3, 4]) == 3
    assert pjr.p75_nearest_rank(list(range(1, 26))) == 19
    assert pjr.p75_nearest_rank(list(range(1, 31))) == 23
    # Unsorted input is sorted first; the rank still indexes ascending values.
    assert pjr.p75_nearest_rank([10, 1, 7, 4]) == 7
    with pytest.raises(ValueError):
        pjr.p75_nearest_rank([])


def test_spec3_null_timing_excluded_and_counted_never_zero(tmp_path):
    """FROZEN SPEC 3: a null is excluded and counted, never treated as 0."""

    def timing_fn(i):
        # Loads 0..4 report no LCP; the rest carry 100..124.
        return _timing(
            lcp_ms=None if i < 5 else 100 + i,
            cls=0.01,
            inp_proxy_ms=50 + i,
            resource_count=10 if i >= 5 else None,
            transfer_bytes=1000 if i >= 5 else None,
        )

    report = _build(tmp_path, _cold_loads(tmp_path, 30, timing_fn=timing_fn))
    cell = _cell(report)
    lcp = cell["metrics"]["lab_p75_lcp_ms"]
    assert lcp["null_count"] == 5
    assert lcp["n"] == 25
    # p75 of the 25 non-null values 105..129: rank ceil(0.75*25)=19 -> 123.
    assert lcp["p75"] == 123
    # Were the 5 nulls smuggled in as zeros, the rank-19 value would be 118.
    assert lcp["p75"] != pjr.p75_nearest_rank([0] * 5 + [100 + i for i in range(5, 30)])
    rc = cell["metrics"]["resource_count_per_load"]
    assert rc["n"] == 25 and len(rc["values"]) == 25
    assert 0 not in rc["values"]


def test_spec5_report_bytes_deterministic_no_wall_clock(tmp_path):
    """FROZEN SPEC 5: same inputs -> identical bytes; run time is an argument."""

    manifests = _cold_loads(tmp_path, 3)
    first = _build(tmp_path, manifests)
    second = _build(tmp_path, manifests)
    assert pjr.report_bytes(first) == pjr.report_bytes(second)

    # Manifest argument order cannot leak into the bytes.
    reordered = _build(tmp_path, list(reversed(manifests)))
    assert pjr.report_bytes(reordered) == pjr.report_bytes(first)

    # The run time is exactly the argument, and changing only it changes only
    # that field's rendering — never a hidden wall-clock read.
    assert first["run_time"] == RUN_TIME
    other = _build(tmp_path, manifests, run_time="2026-10-22T09:00:00Z")
    assert other["run_time"] == "2026-10-22T09:00:00Z"
    assert pjr.report_bytes(first) != pjr.report_bytes(other)
    assert other["cells"] == first["cells"]

    # Canonical form: the bytes round-trip through sorted-keys serialization.
    raw = pjr.report_bytes(first)
    assert raw.endswith(b"\n")
    assert (
        json.dumps(json.loads(raw), sort_keys=True, indent=2) + "\n"
    ).encode("utf-8") == raw

    # The report path owns no clock: the module never imports one.
    source = MODULE_PATH.read_text(encoding="utf-8")
    for clock in ("import time", "datetime", "time.time", "utcnow", "Date.now"):
        assert clock not in source, clock


def test_spec6_verdicts_closed_set_gap_cell_never_pass(tmp_path):
    """FROZEN SPEC 6: PASS/FAIL/INSUFFICIENT_SAMPLES/GAP; a gap is never PASS."""

    axis_gap = {
        "dimension": "locale",
        "value": "zh",
        "captured": False,
        "reason": "registry declares locales ['en'] for this page",
    }
    manifests = _cold_loads(tmp_path, 25) + [
        _write_manifest(
            tmp_path,
            "run-gap.json",
            [_page(ROUTE, [_state(320, "zh", "light", _timing(lcp_ms=100, cls=0.01, inp_proxy_ms=40))], gaps=[axis_gap])],
        )
    ]
    report = _build(tmp_path, manifests)

    gap_cell = _cell(report, locale="zh")
    assert gap_cell["verdict"] == "GAP"
    assert gap_cell["gap_reasons"], "a gap cell carries the recorded reason"
    for label, block in gap_cell["metrics"].items():
        if block["verdict"] is not None:
            assert block["verdict"] == "GAP", label
        assert block["p75"] is None, label
    # The design's exact words: a recorded gap stays a gap even with a load.
    assert gap_cell["metrics"]["lab_p75_lcp_ms"]["n"] == 1

    verdicts = {cell["verdict"] for cell in report["cells"]}
    assert verdicts <= CLOSED_VERDICTS
    assert report["totals"]["by_verdict"]["GAP"] > 0
    for verdict, count in report["totals"]["by_verdict"].items():
        assert verdict in CLOSED_VERDICTS
        assert isinstance(count, int)


def test_budget_fail_when_p75_exceeds_the_declared_number(tmp_path):
    """A p75 over the spec's budget is FAIL, not averaged away."""

    report = _build(
        tmp_path,
        _cold_loads(tmp_path, 30, timing_fn=lambda i: _timing(
            lcp_ms=3000 + i,  # p75 3019 > 2500
            cls=0.2,          # p75 0.2 > 0.1
            inp_proxy_ms=250 + i,  # p75 269 > 200
            resource_count=10,
            transfer_bytes=1000,
        )),
    )
    cell = _cell(report)
    for label in ("lab_p75_lcp_ms", "lab_p75_cls", "lab_p75_inp_proxy_ms"):
        assert cell["metrics"][label]["verdict"] == "FAIL", label
    assert cell["verdict"] == "FAIL"
    assert report["overall_verdict"] == "FAIL"


def test_field_reported_blocked_on_d11_and_labels_are_lab(tmp_path):
    """Field metrics are blocked, said aloud, and never faked or omitted."""

    report = _build(tmp_path, _cold_loads(tmp_path, 1))
    assert report["field"] == "BLOCKED_ON_D11"
    assert report["basis"] == "lab"
    budgeted_labels = [SPEC["statistics"][s]["label"] for s in pjr.BUDGETED_STATISTICS]
    assert budgeted_labels == ["lab_p75_lcp_ms", "lab_p75_cls", "lab_p75_inp_proxy_ms"]
    for cell in report["cells"]:
        assert set(cell["metrics"]) >= set(budgeted_labels)
        for label in budgeted_labels:
            assert label.startswith("lab_p75_")
            assert "field" not in label
    assert "BLOCKED_ON_D11" in pjr.render_markdown(report)


def test_server_held_time_distribution_and_edge_timeout_risk(tmp_path):
    """Per-route server-held time is a distribution; >30 s is EDGE_TIMEOUT_RISK."""

    rows = [_journal_row(i, ROUTE, elapsed_ms=float(i)) for i in range(1, 11)]
    rows.append(_journal_row(11, ROUTE, elapsed_ms=31_000.5))
    rows.append(_journal_row(12, "/boom.css", status=500, elapsed_ms=2.0))
    journal = _write_journal(tmp_path, "lab.jsonl", rows)
    report = _build(tmp_path, _cold_loads(tmp_path, 1), journals=[journal])

    route = next(r for r in report["server"]["routes"] if r["route"] == ROUTE)
    assert route["n"] == 11
    assert route["edge_timeout_risk"] is True
    assert route["over_timeout_count"] == 1
    # Nearest-rank distribution over 1..10 + 31000.5.
    assert route["elapsed_ms"]["min"] == 1.0
    assert route["elapsed_ms"]["p50"] == 6.0
    assert route["elapsed_ms"]["p75"] == 9.0
    assert route["elapsed_ms"]["max"] == 31_000.5
    assert route["statuses"] == {"200": 11}

    boom = next(r for r in report["server"]["routes"] if r["route"] == "/boom.css")
    assert boom["status_5xx_count"] == 1 and boom["edge_timeout_risk"] is False
    assert report["server"]["tool_timeout_s"] == 30
    assert "capture_page_evidence.py" in report["server"]["tool_timeout_source"]

    klass = next(k for k in report["failure_classes"] if k["id"] == "server_error_or_over_timeout")
    assert klass["count"] == 2  # one over-timeout + one 5xx
    assert klass["breakdown"] == {
        "journal_status_5xx": 1,
        "journal_over_timeout": 1,
        "manifest_failed_responses_5xx": 0,
    }

    # A journal with no slow route carries no risk flag.
    calm = _write_journal(tmp_path, "calm.jsonl", [_journal_row(1, ROUTE, elapsed_ms=5.0)])
    calm_report = _build(tmp_path, _cold_loads(tmp_path, 1), journals=[calm])
    assert calm_report["server"]["routes"][0]["edge_timeout_risk"] is False


def test_failure_classes_counted_with_budget_zero(tmp_path):
    """The eight failure classes count against a budget of zero, always."""

    manifest = _write_manifest(
        tmp_path,
        "run-err.json",
        [
            _page(
                ROUTE,
                [
                    _state(320, "en", "light", _timing(lcp_ms=100, cls=0.01)),
                    dict(_state(320, "en", "dark"), captured=False, reason="Timeout 30000ms exceeded"),
                ],
                console_errors=[
                    {"text": "Uncaught TypeError", "source_url": "http://127.0.0.1:1/app.js"},
                    {"text": "401", "source_url": "http://127.0.0.1:1/api.json"},
                ],
                failed_responses=[
                    {"url": "http://127.0.0.1:1/api.json", "status": 404},
                    {"url": "http://127.0.0.1:1/entitled.json", "status": 401},
                ],
            )
        ],
    )
    report = _build(tmp_path, [manifest])
    classes = {entry["id"]: entry for entry in report["failure_classes"]}
    assert set(classes) == {
        "server_error_or_over_timeout",
        "auth_plane_leak_or_denial",
        "console_errors_or_failed_responses",
        "interaction_never_settled",
        "capture_fidelity_failures",
        "gated_asset_without_no_store",
        "resource_envelope_exceeded",
        "recorded_gap_cells",
    }
    for entry in classes.values():
        assert entry["budget"] == 0
    assert classes["console_errors_or_failed_responses"]["count"] == 4  # 2 + 2
    assert classes["auth_plane_leak_or_denial"]["count"] == 1  # the 401
    assert classes["capture_fidelity_failures"]["count"] == 1  # the dark-theme state
    settled = classes["interaction_never_settled"]
    assert settled["count"] == 0 and "journey-runner" in settled["note"]
    envelope = classes["resource_envelope_exceeded"]
    assert envelope["count"] == 0 and "baseline" in envelope["note"]
    assert report["overall_verdict"] == "FAIL"


def test_resources_reported_without_invented_budget(tmp_path):
    """resource_count / transfer_bytes: per-load values + max, no budget, no verdict."""

    report = _build(tmp_path, _cold_loads(tmp_path, 3))
    cell = _cell(report)
    rc = cell["metrics"]["resource_count_per_load"]
    tb = cell["metrics"]["transfer_bytes_per_load"]
    assert rc["values"] == [10, 11, 12] and rc["max"] == 12
    assert tb["values"] == [50_000, 50_100, 50_200] and tb["max"] == 50_200
    for block in (rc, tb):
        assert block["verdict"] is None
        assert block["budget"] is None
        assert block["required_n"] is None
        assert block["basis"] == "lab"
    assert set(report["spec"]["budgets"]) == {"lcp", "cls", "inp"}


def test_non_lab_manifest_or_wrong_schema_refused(tmp_path):
    """A non-lab manifest never feeds lab_p75_* labels; a bad schema is refused."""

    bad_basis = _write_manifest(tmp_path, "field.json", [_page(ROUTE, [])], timing_basis="field")
    with pytest.raises(pjr.SpecError, match="timing_basis"):
        _build(tmp_path, [bad_basis])

    bad_schema = _write_manifest(tmp_path, "old.json", [_page(ROUTE, [])], schema="mastermind.p0_evidence.v1")
    with pytest.raises(pjr.SpecError, match="schema"):
        _build(tmp_path, [bad_schema])

    missing = tmp_path / "absent.json"
    with pytest.raises(pjr.SpecError, match="not found"):
        _build(tmp_path, [missing])


def test_forced_state_loads_excluded_from_samples_but_counted(tmp_path):
    """Forced shots are presentation evidence: never samples, always visible."""

    manifest = _write_manifest(
        tmp_path,
        "run-forced.json",
        [
            _page(
                ROUTE,
                [
                    _state(320, "en", "light", _timing(lcp_ms=100, cls=0.01, inp_proxy_ms=40, resource_count=5, transfer_bytes=500)),
                    _state(
                        320, "en", "light",
                        _timing(lcp_ms=4000, cls=0.5, inp_proxy_ms=900, resource_count=99, transfer_bytes=99_999),
                        force_state="empty:.is-empty",
                    ),
                ],
            )
        ],
    )
    report = _build(tmp_path, [manifest])
    cell = _cell(report)
    # One rest load: n=1 is honest, INSUFFICIENT against required N, and the
    # forced shot's 4000 ms never enters the values.
    lcp = cell["metrics"]["lab_p75_lcp_ms"]
    assert lcp["n"] == 1
    assert lcp["verdict"] == "INSUFFICIENT_SAMPLES"
    assert lcp["p75"] is None
    assert cell["metrics"]["resource_count_per_load"]["values"] == [5]
    assert report["inputs"]["forced_state_loads_excluded"] == 1


def test_out_of_journey_routes_reported_not_silently_dropped(tmp_path):
    manifest = _write_manifest(
        tmp_path,
        "run-extra.json",
        [
            _page(ROUTE, [_state(320, "en", "light", _timing(lcp_ms=100, cls=0.01))]),
            _page("/glossary.html", [_state(320, "en", "light", _timing(lcp_ms=100, cls=0.01))]),
        ],
    )
    report = _build(tmp_path, [manifest])
    assert report["inputs"]["out_of_journey_routes"] == ["/glossary.html"]


def test_cli_writes_report_and_summary(tmp_path, capsys):
    manifests = _cold_loads(tmp_path, 2)
    journal = _write_journal(tmp_path, "lab.jsonl", [_journal_row(1, ROUTE, elapsed_ms=3.0)])
    out_report = tmp_path / "out" / "b23_latency_report.json"
    out_summary = tmp_path / "out" / "b23_latency_report.md"
    rc = pjr.main(
        [
            "--spec", str(COMMITTED_SPEC),
            "--manifest", str(manifests[0]),
            "--manifest", str(manifests[1]),
            "--journal", str(journal),
            "--run-time", RUN_TIME,
            "--out-report", str(out_report),
            "--out-summary", str(out_summary),
        ]
    )
    assert rc == 0
    report = json.loads(out_report.read_text(encoding="utf-8"))
    assert report["schema"] == "mastermind.b23_latency_report.v1"
    assert report["run_time"] == RUN_TIME
    # The CLI writes only to the output paths it was given.
    summary = out_summary.read_text(encoding="utf-8")
    assert "Prophet B23 latency report" in summary
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == [
        "b23_latency_report.json",
        "b23_latency_report.md",
    ]


def test_markdown_summary_is_honest(tmp_path):
    report = _build(tmp_path, _cold_loads(tmp_path, 2))
    markdown = pjr.render_markdown(report)
    assert f"**{report['overall_verdict']}**" in markdown
    assert "field: **BLOCKED_ON_D11**" in markdown
    assert "nearest_rank" in markdown
    assert "p75 <= 2500 ms" in markdown
    assert "p75 <= 0.1" in markdown
    assert "p75 <= 200 ms" in markdown
    # Cells with too few loads say so with their observed n; gaps say GAP.
    assert "INSUFFICIENT (n=2," in markdown
    assert " | GAP |" in markdown
    assert "No journal was supplied" in markdown
    assert "budget zero on every class" in markdown
