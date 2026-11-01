"""EVAL-1 partition clock receipt builder tests."""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "research" / "alpha_intelligence" / "expectation_market_dynamics"
BUILDER = HERE / "eval1_partition_clock.py"
CHECK = HERE / "eval1_partition_clock_check.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


builder = _load("eval1_partition_clock", BUILDER)
check = _load("eval1_partition_clock_check", CHECK)
r4 = _load("r4_v2_admission_test", HERE / "r4_v2_admission.py")


@pytest.fixture(scope="module")
def make_repo(tmp_path_factory):
    def _factory(obs_rows):
        base = tmp_path_factory.mktemp("repo")
        env = {
            **os.environ,
            "GIT_CONFIG_NOSYSTEM": "1",
            "HOME": str(base / "home"),
        }
        (base / "home").mkdir()
        git = [
            "git",
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@t",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "core.hooksPath=/dev/null",
        ]

        def run(cmd, *, cwd=base, extra_env=None):
            subprocess.run(
                git + cmd,
                cwd=cwd,
                env={**env, **(extra_env or {})},
                check=True,
                capture_output=True,
            )

        run(["init"])
        sm = pd.DataFrame(
            {
                "security_id": [],
                "issuer_id": [],
                "issuer_state": [],
                "country": [],
                "security_state": [],
            }
        )
        va = pd.DataFrame(
            {
                "vendor": [],
                "vendor_symbol": [],
                "security_id": [],
                "ingested_at": [],
                "valid_from": [],
                "valid_to": [],
            }
        )

        def series(ticker, metric, horizon, period_end, points, revenue=False):
            rows = []
            for i, (d, val) in enumerate(points):
                oid = f"{ticker}-{metric}-{horizon}-{d}-{i}"
                clk = f"{d}T15:00:00Z"
                rows.append(
                    {
                        "observation_id": oid,
                        "ticker_compat": ticker,
                        "metric": metric,
                        "horizon_label_raw": horizon,
                        "period_end": period_end,
                        "observation_type": "average",
                        "value": float(val),
                        "system_observed_at": clk,
                        "provider_observed_at": clk,
                        "issuer_ref": None,
                        "security_ref": None,
                    }
                )
            return rows

        def add_issuer(iss_code, ticker):
            sid = f"SEC-{iss_code}"
            iid = f"ISS-{iss_code}"
            sm_rows = pd.DataFrame(
                {
                    "security_id": [sid],
                    "issuer_id": [iid],
                    "issuer_state": ["RESOLVED"],
                    "country": ["US"],
                    "security_state": [None],
                }
            )
            va_rows = pd.DataFrame(
                {
                    "vendor": ["yahoo"],
                    "vendor_symbol": [ticker],
                    "security_id": [sid],
                    "ingested_at": [pd.Timestamp("2026-04-01T00:00:00Z")],
                    "valid_from": [date(2026, 1, 1)],
                    "valid_to": [None],
                }
            )
            return sm_rows, va_rows, iid

        all_obs = []
        sm_parts = [sm]
        va_parts = [va]
        issuers_added: set[str] = set()

        for call in obs_rows:
            if call[0] == "series":
                _, ticker, metric, horizon, period_end, points = call
                all_obs.extend(series(ticker, metric, horizon, period_end, points))
            elif call[0] == "issuer_series":
                _, iss_code, ticker, metric, horizon, period_end, points = call
                if iss_code not in issuers_added:
                    smr, var, _ = add_issuer(iss_code, ticker)
                    sm_parts.append(smr)
                    va_parts.append(var)
                    issuers_added.add(iss_code)
                rows = []
                for pt in points:
                    if len(pt) == 3:
                        d, val, clk = pt
                    else:
                        d, val = pt
                        clk = f"{d}T15:00:00Z"
                    rows.append(
                        {
                            "observation_id": f"{ticker}-{metric}-{horizon}-{d}",
                            "ticker_compat": ticker,
                            "metric": metric,
                            "horizon_label_raw": horizon,
                            "period_end": period_end,
                            "observation_type": "average",
                            "value": float(val),
                            "system_observed_at": clk,
                            "provider_observed_at": clk,
                            "issuer_ref": None,
                            "security_ref": None,
                        }
                    )
                all_obs.extend(rows)
            elif call[0] == "clock_series":
                _, ticker, metric, horizon, period_end, points = call
                rows = []
                for i, (d, val, clk) in enumerate(points):
                    oid = f"{ticker}-{d}-{i}"
                    rows.append(
                        {
                            "observation_id": oid,
                            "ticker_compat": ticker,
                            "metric": metric,
                            "horizon_label_raw": horizon,
                            "period_end": period_end,
                            "observation_type": "average",
                            "value": float(val),
                            "system_observed_at": clk,
                            "provider_observed_at": clk,
                            "issuer_ref": None,
                            "security_ref": None,
                        }
                    )
                all_obs.extend(rows)

        sm_all = pd.concat(sm_parts, ignore_index=True)
        va_all = pd.concat(va_parts, ignore_index=True)
        obs_df = pd.DataFrame(all_obs)
        att_df = pd.DataFrame(
            {
                "status": ["ok", "ok", "ok"],
                "attempted_at": ["2026-10-01T12:00:00Z"] * 3,
                "completed_at": ["2026-10-01T13:00:00Z"] * 3,
            }
        )
        for col in obs_df.columns:
            if col != "value":
                obs_df[col] = obs_df[col].astype("string")
        att_df = att_df.astype("string")
        for col in ("attempted_at", "completed_at"):
            att_df[col] = att_df[col].astype("string")

        paths = r4.PATHS
        (base / "data/reference").mkdir(parents=True)
        (base / "data/revisions").mkdir(parents=True)
        sm_all.astype({c: "string" for c in sm_all.columns}).to_parquet(base / paths["security_master"])
        va_all.to_parquet(base / paths["vendor_aliases"])
        run(
            ["add", paths["security_master"], paths["vendor_aliases"]],
            extra_env={
                "GIT_AUTHOR_DATE": "2026-05-01T12:00:00Z",
                "GIT_COMMITTER_DATE": "2026-05-01T12:00:00Z",
            },
        )
        run(
            ["commit", "-m", "ref"],
            extra_env={
                "GIT_AUTHOR_DATE": "2026-05-01T12:00:00Z",
                "GIT_COMMITTER_DATE": "2026-05-01T12:00:00Z",
            },
        )
        obs_df.to_parquet(base / paths["observations"])
        att_df.to_parquet(base / paths["attempts"])
        run(["add", paths["observations"], paths["attempts"]])
        run(
            ["commit", "-m", "obs"],
            extra_env={
                "GIT_AUTHOR_DATE": "2026-11-25T23:00:00Z",
                "GIT_COMMITTER_DATE": "2026-11-25T23:00:00Z",
            },
        )
        head = subprocess.check_output(
            git + ["rev-parse", "HEAD"], cwd=base, env=env, text=True
        ).strip()
        return base, head

    return _factory


def admitted(repo, head):
    return {
        "admitted": True,
        "reasons": [],
        "source_main_commit": head,
        "registration_digest": "d" * 64,
        "introduction_commit": "c" * 40,
        "boundary": "2026-10-07",
        "main_freshness": {"proven": True},
    }


def test_refuses_when_not_admitted(make_repo):
    repo, head = make_repo([])
    doc = builder.build(
        repo,
        "HEAD",
        admission={"admitted": False, "reasons": ["EVAL1_ACTIVATION_MISSING"], "source_main_commit": head},
    )
    assert doc["verdict"] == "EVAL1_NOT_ADMITTED"
    assert doc["admission"]["refusal_codes"] == ["EVAL1_ACTIVATION_MISSING"]
    assert "partitions" not in doc
    assert check.violations(doc, raw_bytes=builder.canonical(doc).encode()) == []


def test_refuses_when_rev_is_not_admission_source(make_repo):
    repo, head = make_repo([])
    doc = builder.build(repo, "HEAD", admission=admitted(repo, "0" * 40))
    assert doc["admission"]["refusal_codes"] == ["REV_NOT_ADMISSION_SOURCE_MAIN"]


def test_cli_refusal_exits_3_and_writes_nothing(make_repo, tmp_path, monkeypatch):
    repo, head = make_repo([])

    def refuse(_r):
        return {"admitted": False, "reasons": ["X"], "source_main_commit": head}

    monkeypatch.setattr(builder.k3e_eval_admission, "inspect_eval1_admission", refuse)
    out = tmp_path / "out"
    rc = builder.main(["--repo", str(repo), "--rev", "HEAD", "--out", str(out)])
    assert rc == 3
    assert not out.exists()


def test_pre_boundary_cutoffs_are_excluded(make_repo):
    repo, head = make_repo(
        [
            ("issuer_series", "A", "AAA", "EPS", "0q", "2026-12-31", [("2026-08-31", 1.0), ("2026-10-02", 2.0)]),
            (
                "issuer_series",
                "B",
                "BBB",
                "EPS",
                "0q",
                "2026-12-31",
                [("2026-09-01", 1.0, "2026-09-01T15:00:00Z"), ("2026-10-06", 2.0, "2026-10-06T21:00:00Z")],
            ),
            ("issuer_series", "E", "EEE", "EPS", "0q", "2026-12-31", [("2026-09-30", 1.0), ("2026-10-29", 2.0)]),
        ]
    )
    doc = builder.build(repo, "HEAD", admission=admitted(repo, head))
    assert doc["episode_starts"]["starts_excluded_by_reason"] == [
        ["START_BEFORE_PARTITION", 1],
        ["START_OBSERVED_BEFORE_BOUNDARY", 1],
    ]
    assert doc["count_unit"]["clusters_excluded_by_reason"] == [
        ["CLUSTER_ANCHORED_BEFORE_PARTITION", 1],
        ["CLUSTER_ANCHOR_OBSERVED_BEFORE_BOUNDARY", 1],
    ]
    assert doc["partitions"]["F_DEV"]["primary_n"] == 1


def test_twenty_quiet_session_law(make_repo):
    repo, head = make_repo(
        [
            ("issuer_series", "D", "DDD", "EPS", "0q", "2026-12-31", [("2026-09-30", 1.0), ("2026-10-28", 2.0)]),
            ("issuer_series", "E", "EEE", "EPS", "0q", "2026-12-31", [("2026-09-30", 1.0), ("2026-10-29", 2.0)]),
        ]
    )
    doc = builder.build(repo, "HEAD", admission=admitted(repo, head))
    assert doc["partitions"]["F_DEV"]["primary_n"] == 1
    assert doc["partitions"]["F_DEV"]["secondary_n"] == 1
    assert doc["episode_starts"]["variant_s_starts_total"] == 1


def test_cluster_collapse(make_repo):
    calls = [
        ("issuer_series", "F", "FFF", "EPS", "0q", "2026-12-31", [("2026-09-30", 1.0), ("2026-10-29", 2.0)]),
        ("issuer_series", "F", "FFF", "revenue", "0q", "2026-12-31", [("2026-09-30", 1.0), ("2026-10-29", 2.0)]),
    ]
    for h, pe in (("+1q", "2027-03-31"), ("0y", "2026-12-31"), ("+1y", "2027-12-31")):
        calls.append(("issuer_series", "F", "FFF", "EPS", h, pe, [("2026-09-30", 1.0), ("2026-10-29", 2.0)]))
        calls.append(("issuer_series", "F", "FFF", "revenue", h, pe, [("2026-09-30", 1.0), ("2026-10-29", 2.0)]))
    repo, head = make_repo(calls)
    doc = builder.build(repo, "HEAD", admission=admitted(repo, head))
    assert doc["episode_starts"]["variant_s_starts_total"] == 8
    assert doc["partitions"]["F_DEV"]["primary_n"] == 1
    assert doc["partitions"]["F_DEV"]["secondary_n"] == 8
    assert doc["count_unit"]["clusters_total"] == 1


def test_base_fixture_counts(make_repo):
    repo, head = make_repo(
        [
            ("issuer_series", "A", "AAA", "EPS", "0q", "2026-12-31", [("2026-08-31", 1.0), ("2026-10-02", 2.0)]),
            (
                "issuer_series",
                "B",
                "BBB",
                "EPS",
                "0q",
                "2026-12-31",
                [("2026-09-01", 1.0, "2026-09-01T15:00:00Z"), ("2026-10-06", 2.0, "2026-10-06T21:00:00Z")],
            ),
            ("issuer_series", "D", "DDD", "EPS", "0q", "2026-12-31", [("2026-09-30", 1.0), ("2026-10-28", 2.0)]),
            ("issuer_series", "E", "EEE", "EPS", "0q", "2026-12-31", [("2026-09-30", 1.0), ("2026-10-29", 2.0)]),
            ("issuer_series", "F", "FFF", "EPS", "0q", "2026-12-31", [("2026-09-30", 1.0), ("2026-10-29", 2.0)]),
            ("issuer_series", "F", "FFF", "EPS", "+1q", "2027-03-31", [("2026-09-30", 1.0), ("2026-10-29", 2.0)]),
            ("issuer_series", "F", "FFF", "EPS", "0y", "2026-12-31", [("2026-09-30", 1.0), ("2026-10-29", 2.0)]),
            ("issuer_series", "F", "FFF", "EPS", "+1y", "2027-12-31", [("2026-09-30", 1.0), ("2026-10-29", 2.0)]),
            ("issuer_series", "F", "FFF", "revenue", "0q", "2026-12-31", [("2026-09-30", 1.0), ("2026-10-29", 2.0)]),
            ("issuer_series", "F", "FFF", "revenue", "+1q", "2027-03-31", [("2026-09-30", 1.0), ("2026-10-29", 2.0)]),
            ("issuer_series", "F", "FFF", "revenue", "0y", "2026-12-31", [("2026-09-30", 1.0), ("2026-10-29", 2.0)]),
            ("issuer_series", "F", "FFF", "revenue", "+1y", "2027-12-31", [("2026-09-30", 1.0), ("2026-10-29", 2.0)]),
            ("issuer_series", "G", "GGG", "revenue", "0q", "2026-12-31", [("2026-09-30", 1.0), ("2026-10-29", 2.0)]),
            ("series", "ZZZ", "EPS", "0q", "2026-12-31", [("2026-09-30", 1.0), ("2026-10-29", 2.0)]),
        ]
    )
    doc = builder.build(repo, "HEAD", admission=admitted(repo, head))
    assert doc["verdict"] == "F_DEV_OPEN"
    fd = doc["partitions"]["F_DEV"]
    assert fd["state"] == "OPEN" and fd["status"] == "INSUFFICIENT_EPISODE_N"
    assert fd["primary_n"] == 3 and fd["primary_n_of_floor"] == "3/100" and fd["secondary_n"] == 10
    assert fd["close_session"] is None
    assert doc["episode_starts"]["variant_s_starts_total"] == 12
    assert doc["episode_starts"]["starts_eligible"] == 10
    assert doc["count_unit"]["clusters_total"] == 5
    assert ["NO_YAHOO_ALIAS_ROW", 2] in doc["identity"]["rows_without_issuer_by_reason"]
    assert doc["corpus"]["data_horizon_session"] == "2026-10-29"
    assert doc["partitions"]["PURGE_1"]["state"] == "NOT_STARTED"
    assert doc["partitions"]["F_VAL"]["start_session"] is None
    assert doc["prospective_shadow_after_session"] is None
    assert check.violations(doc, raw_bytes=builder.canonical(doc).encode()) == []


def test_closure_across_holiday(make_repo):
    calls = []
    for i in range(1, 100):
        code = f"I{i:03d}"
        calls.append(
            (
                "issuer_series",
                code,
                f"T{i:03d}",
                "EPS",
                "0q",
                "2026-12-31",
                [("2026-10-07", 1.0), ("2026-11-20", 2.0)],
            )
        )
    calls.append(("issuer_series", "I100", "T100", "EPS", "0q", "2026-12-31", [("2026-10-07", 1.0), ("2026-11-23", 2.0)]))
    calls.append(("issuer_series", "I101", "T101", "EPS", "0q", "2026-12-31", [("2026-10-07", 1.0), ("2026-11-24", 2.0)]))
    repo, head = make_repo(calls)
    doc = builder.build(repo, "HEAD", admission=admitted(repo, head))
    assert doc["partitions"]["F_DEV"]["state"] == "CLOSED"
    assert doc["partitions"]["F_DEV"]["close_session"] == "2026-11-23"
    assert doc["partitions"]["F_DEV"]["primary_n"] == 100
    p1 = doc["partitions"]["PURGE_1"]
    assert p1["state"] == "OPEN"
    assert p1["start_session"] == "2026-11-24" and p1["end_session"] == "2027-02-25"
    assert p1["sessions"] == 63
    fv = doc["partitions"]["F_VAL"]
    assert fv["state"] == "NOT_STARTED" and fv["start_session"] == "2027-02-26"
    assert doc["count_unit"]["clusters_excluded_by_reason"] == [["CLUSTER_ANCHORED_IN_PURGE_1", 1]]
    assert doc["verdict"] == "PURGE_1"
    import lib.nyse_calendar as nyse_calendar

    assert nyse_calendar.is_session(date(2026, 11, 26)) is False
    assert check.violations(doc, raw_bytes=builder.canonical(doc).encode()) == []


def test_check_rejects_forbidden_keys_and_values(make_repo):
    repo, head = make_repo(
        [("issuer_series", "E", "EEE", "EPS", "0q", "2026-12-31", [("2026-09-30", 1.0), ("2026-10-29", 2.0)])]
    )
    doc = builder.build(repo, "HEAD", admission=admitted(repo, head))
    clean = builder.canonical(doc).encode()
    assert check.violations(doc, raw_bytes=clean) == []
    cases = [
        lambda d: d["count_unit"].update({"anchor_direction": "x"}),
        lambda d: d["gaps"].append("UP"),
        lambda d: d["corpus"].update({"groups": []}),
        lambda d: d["labels"].update({"score": 0.5}),
        lambda d: d["identity"].update({"labels": {}}),
        lambda d: d["labels"].update({"financial_influence": 0}),
        lambda d: d["partitions"]["F_DEV"].update({"loss": 1}),
    ]
    for mut in cases:
        d = copy.deepcopy(doc)
        mut(d)
        assert check.violations(d, raw_bytes=clean) != []


def test_determinism(make_repo, tmp_path):
    repo, head = make_repo(
        [("issuer_series", "E", "EEE", "EPS", "0q", "2026-12-31", [("2026-09-30", 1.0), ("2026-10-29", 2.0)])]
    )
    a = builder.canonical(builder.build(repo, "HEAD", admission=admitted(repo, head)))
    b = builder.canonical(builder.build(repo, "HEAD", admission=admitted(repo, head)))
    assert a == b
    d1 = builder.build(repo, "HEAD", admission=admitted(repo, head))
    o1 = tmp_path / "o1"
    o2 = tmp_path / "o2"
    j1, m1 = builder.write(d1, o1)
    j2, m2 = builder.write(d1, o2)
    assert j1.read_bytes() == j2.read_bytes()
    assert m1.read_bytes() == m2.read_bytes()
    assert check.main(["--check", str(j1), "--md", str(m1)]) == 0


def test_cli_admitted_writes_receipt_and_check_passes(make_repo, tmp_path, monkeypatch):
    repo, head = make_repo(
        [("issuer_series", "E", "EEE", "EPS", "0q", "2026-12-31", [("2026-09-30", 1.0), ("2026-10-29", 2.0)])]
    )
    monkeypatch.setattr(
        builder.k3e_eval_admission,
        "inspect_eval1_admission",
        lambda _r: admitted(repo, head),
    )
    out = tmp_path / "out"
    assert builder.main(["--repo", str(repo), "--rev", "HEAD", "--out", str(out)]) == 0
    files = list(out.iterdir())
    assert len(files) == 2
    jp = next(p for p in files if p.suffix == ".json")
    mp = next(p for p in files if p.suffix == ".md")
    assert check.main(["--check", str(jp), "--md", str(mp)]) == 0


@pytest.mark.parametrize("path", sorted(HERE.glob("EVAL1_PARTITION_CLOCK_*.json")))
def test_committed_receipts_pass_check(path):
    md = path.with_suffix(".md")
    raw = path.read_bytes()
    doc = json.loads(raw.decode("utf-8"))
    assert check.violations(doc, raw_bytes=raw, md_text=md.read_text(encoding="utf-8")) == []
